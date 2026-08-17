"""
routers/patologias.py
---------------------
El historial médico del socio: qué condiciones tiene y qué hay que tener en
cuenta al armarle una rutina o una dieta.

POR QUÉ ES UN ROUTER APARTE Y NO PARTE DE /socios
=================================================
Porque el permiso es distinto, y eso es exactamente lo que justifica separar.

Todo /socios lo protege la sección SOCIOS, que el Recepcionista tiene en
TOTAL. Acá el guard es `Accion.VER_HISTORIAL_MEDICO`, que el Recepcionista NO
tiene: es la única acción donde queda por debajo del Entrenador y del
Nutricionista.

El mostrador maneja plata, turnos e ingresos. Ninguna tarea suya requiere
saber quién tiene diabetes, epilepsia o una lesión de rodilla, y ese dato no
se vuelve inofensivo porque el sistema sea chico. Para una emergencia lo que
hace falta es el contacto de emergencia, que vive en Persona y sí ve.

El Entrenador y el Nutricionista sí lo necesitan: una rodilla operada cambia
la rutina y una celiaquía cambia la dieta. Ese es todo el motivo por el que
el gimnasio guarda esto.

Mezclar estos endpoints entre los de /socios habría significado que cada uno
lleve su propio guard distinto al del resto del archivo — y ese es el tipo de
excepción que a los seis meses alguien copia y pega mal.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import Patologia, Socio, SocioPatologia
from permisos import Accion
from schemas import (
    AsignarPatologiaRequest, PatologiaCrearRequest, PatologiaDeSocioOut,
    PatologiaOut,
)
from security import Sesion, requiere_accion

router = APIRouter(tags=["Historial médico"])


# =============================================================================
# EL CATÁLOGO
# =============================================================================

@router.get("/patologias", response_model=list[PatologiaOut])
def listar_patologias(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.VER_HISTORIAL_MEDICO)),
):
    """
    El catálogo de condiciones que el gimnasio registra.

    Es un catálogo y no texto libre por 1FN: "asma, rodilla operada,
    hipertensión" en un solo campo no se puede consultar ni contar, y cada
    quien lo escribe distinto. Con el catálogo, "cuántos socios tienen asma"
    es una consulta y no una búsqueda de texto con suerte.
    """
    patologias = db.query(Patologia).order_by(Patologia.nombre).all()
    return [PatologiaOut(id_patologia=p.id_patologia, nombre=p.nombre,
                          descripcion=p.descripcion)
            for p in patologias]


@router.post("/patologias", response_model=PatologiaOut,
             status_code=status.HTTP_201_CREATED)
def crear_patologia(
    datos: PatologiaCrearRequest,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.VER_HISTORIAL_MEDICO)),
):
    """
    Suma una condición al catálogo.

    Se compara el nombre SIN distinguir mayúsculas: "Asma" y "asma" son la
    misma cosa, y dejar que convivan haría que la mitad de los socios
    asmáticos no aparezca al filtrar por una de las dos. El UNIQUE del esquema
    no alcanza para esto porque para Postgres son strings distintos.
    """
    nombre = datos.nombre.strip()
    choca = (db.query(Patologia)
             .filter(func.lower(Patologia.nombre) == nombre.lower())
             .first())
    if choca:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"«{choca.nombre}» ya está en el catálogo.",
        )

    patologia = Patologia(nombre=nombre, descripcion=datos.descripcion)
    db.add(patologia)
    db.commit()
    db.refresh(patologia)
    return PatologiaOut(id_patologia=patologia.id_patologia,
                         nombre=patologia.nombre,
                         descripcion=patologia.descripcion)


# =============================================================================
# LAS DE UN SOCIO
# =============================================================================

def _a_salida(sp: SocioPatologia) -> PatologiaDeSocioOut:
    return PatologiaDeSocioOut(
        id_patologia=sp.id_patologia,
        nombre=sp.patologia.nombre if sp.patologia else "?",
        descripcion=sp.patologia.descripcion if sp.patologia else None,
        fecha_diagnostico=sp.fecha_diagnostico,
        observaciones=sp.observaciones,
    )


@router.get("/socios/{id_socio}/patologias", response_model=list[PatologiaDeSocioOut])
def patologias_del_socio(
    id_socio: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.VER_HISTORIAL_MEDICO)),
):
    """Qué condiciones tiene, con las observaciones de cada una."""
    if db.get(Socio, id_socio) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="El socio no existe.")

    filas = (db.query(SocioPatologia)
             .filter(SocioPatologia.id_socio == id_socio)
             .all())
    return sorted((_a_salida(f) for f in filas), key=lambda x: x.nombre)


@router.post("/socios/{id_socio}/patologias", response_model=PatologiaDeSocioOut,
             status_code=status.HTTP_201_CREATED)
def asignar_patologia(
    id_socio: int,
    datos: AsignarPatologiaRequest,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.VER_HISTORIAL_MEDICO)),
):
    """
    Le registra una condición.

    `observaciones` es lo que más le sirve al entrenador y no lo puede saber
    el catálogo: "rodilla derecha", "controlada con medicación", "evitar
    impacto". El nombre de la patología dice QUÉ tiene; esto dice qué hacer.
    """
    if db.get(Socio, id_socio) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="El socio no existe.")

    patologia = db.get(Patologia, datos.id_patologia)
    if patologia is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Esa patología no está en el catálogo.")

    # La clave primaria compuesta ya lo impide, pero un IntegrityError le
    # llegaría a la pantalla como un error genérico de servidor en vez de
    # explicar que ya la tenía registrada.
    ya = db.get(SocioPatologia, (id_socio, datos.id_patologia))
    if ya:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(f"Ese socio ya tiene «{patologia.nombre}» registrada. "
                    f"Editala si querés cambiar las observaciones."),
        )

    sp = SocioPatologia(
        id_socio=id_socio,
        id_patologia=datos.id_patologia,
        fecha_diagnostico=datos.fecha_diagnostico,
        observaciones=datos.observaciones,
    )
    db.add(sp)
    db.commit()
    db.refresh(sp)
    return _a_salida(sp)


@router.put("/socios/{id_socio}/patologias/{id_patologia}",
            response_model=PatologiaDeSocioOut)
def editar_patologia_del_socio(
    id_socio: int,
    id_patologia: int,
    datos: AsignarPatologiaRequest,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.VER_HISTORIAL_MEDICO)),
):
    """
    Cambia la fecha o las observaciones.

    Existe porque las observaciones cambian más que el diagnóstico: una lesión
    que mejora, una medicación que se ajusta. Sin esto habría que borrar y
    volver a cargar, que además perdería la fecha original.
    """
    sp = db.get(SocioPatologia, (id_socio, id_patologia))
    if sp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Ese socio no tiene esa patología registrada.")

    sp.fecha_diagnostico = datos.fecha_diagnostico
    sp.observaciones = datos.observaciones
    db.commit()
    db.refresh(sp)
    return _a_salida(sp)


@router.delete("/socios/{id_socio}/patologias/{id_patologia}",
               status_code=status.HTTP_204_NO_CONTENT)
def quitar_patologia(
    id_socio: int,
    id_patologia: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.VER_HISTORIAL_MEDICO)),
):
    """
    Le saca una condición.

    Acá SÍ se borra la fila, a diferencia de casi todo el resto del sistema
    —socios, rutinas, actividades— que usa baja lógica. El motivo es que esto
    NO es un hecho histórico: es el estado de salud ACTUAL del socio. Una
    lesión que se curó no es "una lesión finalizada" que convenga arrastrar,
    es una lesión que ya no tiene; y guardar condiciones médicas viejas de
    alguien es exactamente el tipo de dato que no conviene acumular sin
    motivo.

    Si hace falta el historial clínico completo, eso es otra cosa y necesita
    su propia tabla con fechas de inicio y fin.
    """
    sp = db.get(SocioPatologia, (id_socio, id_patologia))
    if sp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Ese socio no tiene esa patología registrada.")
    db.delete(sp)
    db.commit()
