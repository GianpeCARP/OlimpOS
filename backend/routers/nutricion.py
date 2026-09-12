"""
routers/nutricion.py
--------------------
Dietas y su asignación a socios.

ESPEJO ESTRUCTURAL DE RUTINAS
-----------------------------
    Dieta             plantilla que arma un nutricionista
    Comida            los platos de esa dieta, por día y momento
    Asignacion_Dieta  qué socio sigue qué dieta, desde cuándo

Vale la misma lógica que en rutinas.py: la dieta es una plantilla reutilizable
y la asignación es lo que la conecta con una persona. Asignar la misma dieta a
diez socios no la duplica diez veces.

La diferencia con Rutina es que Comida NO es un catálogo compartido como
Ejercicio: 'pollo con arroz' descripto en una dieta no es la misma entidad que
en otra, porque cambian las cantidades y el contexto. Por eso Comida cuelga
directo de Dieta y se borra con ella (cascade), mientras que un Ejercicio
sobrevive a las rutinas que lo usaban.

QUIÉN PUEDE QUÉ
---------------
TOTAL para Dueño, Recepcionista y Nutricionista. LECTURA para el Entrenador:
puede consultar la dieta de un socio para ver de quién es y no contradecirla
con la rutina, pero no darla de alta ni desligarla. Es la simetría exacta de
lo que pasa en Rutinas con el Nutricionista.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import (
    AsignacionDieta, CatalogoComida, Comida, Dieta, Empleado, Nutricionista, Socio,
)
from permisos import Acceso, Accion, Seccion
from schemas import (
    AsignacionDietaOut, AsignarDietaRequest, CatalogoComidaOut, ComidaOut,
    DietaCrear, DietaEditarRequest, DietaOut,
)
from security import Sesion, requiere_accion, requiere_seccion

router = APIRouter(prefix="/nutricion", tags=["Nutrición"])


# Orden en que se muestran las comidas de un día. Ordenar alfabéticamente
# pondría Almuerzo antes que Desayuno, que no es como se come.
ORDEN_MOMENTOS = {
    "desayuno": 1, "media mañana": 2, "almuerzo": 3,
    "merienda": 4, "media tarde": 5, "cena": 6, "colación": 7,
}


def _clave_orden_comida(comida: Comida) -> tuple:
    momento = (comida.momento or "").strip().lower()
    return (comida.dia or 0, ORDEN_MOMENTOS.get(momento, 99), comida.id_comida)


def _nombre_nutricionista(nutri: Nutricionista | None) -> str:
    """Nutricionista -> Empleado -> Persona. 'Sin asignar' si falta algo."""
    if nutri is None or nutri.empleado is None:
        return "Sin asignar"
    persona = nutri.empleado.persona
    return persona.nombre_completo if persona else "Sin asignar"


def _nutricionista_de_sesion(db: Session, sesion: Sesion) -> Nutricionista | None:
    empleado = (
        db.query(Empleado)
        .filter(Empleado.id_persona == sesion.id_persona)
        .first()
    )
    return empleado.nutricionista if empleado else None


def _resolver_nutricionista(db: Session, sesion: Sesion, id_pedido: int | None) -> Nutricionista:
    """
    Espejo exacto de _resolver_entrenador en rutinas.py: un nutricionista solo
    crea dietas a su nombre; el Dueño y el Recepcionista tienen que elegir a
    cargo de quién queda.
    """
    propio = _nutricionista_de_sesion(db, sesion)

    if propio is not None:
        if id_pedido is not None and id_pedido != propio.id_nutricionista:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No podés crear dietas a nombre de otro nutricionista.",
            )
        return propio

    if id_pedido is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Elegí el nutricionista que va a quedar a cargo de la dieta.",
        )

    nutri = db.get(Nutricionista, id_pedido)
    if nutri is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="El nutricionista indicado no existe.")
    if nutri.empleado is None or not nutri.empleado.activo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ese nutricionista está dado de baja. Elegí uno activo.",
        )
    return nutri


def _a_comida_out(c) -> ComidaOut:
    """El nombre, la descripción y las calorías salen del catálogo (el plato)."""
    cat = c.catalogo
    return ComidaOut(
        id_comida=c.id_comida,
        dia=c.dia,
        momento=c.momento,
        id_catalogo_comida=c.id_catalogo_comida,
        nombre=cat.nombre if cat else "?",
        descripcion=cat.descripcion if cat else None,
        calorias=cat.calorias if cat else None,
    )


def _a_dieta_out(dieta: Dieta, con_comidas: bool = True) -> DietaOut:
    comidas = []
    if con_comidas:
        comidas = [_a_comida_out(c)
                   for c in sorted(dieta.comidas, key=_clave_orden_comida)]

    return DietaOut(
        id_dieta=dieta.id_dieta,
        id_nutricionista=dieta.id_nutricionista,
        nutricionista=_nombre_nutricionista(dieta.nutricionista),
        nombre=dieta.nombre,
        objetivo=dieta.objetivo,
        calorias_diarias=dieta.calorias_diarias,
        descripcion=dieta.descripcion,
        fecha_creacion=dieta.fecha_creacion,
        activo=bool(dieta.activo),
        asignados=sum(1 for a in dieta.asignaciones if a.estado == "ACTIVA"),
        comidas=comidas,
    )


# =============================================================================
# DIETAS
# =============================================================================

@router.get("/catalogo-comidas", response_model=list[CatalogoComidaOut])
def listar_catalogo_comidas(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.NUTRICION)),
):
    """
    El catálogo de platos con el que el nutricionista arma las dietas. Cada
    Comida de una dieta apunta a uno de estos; el nombre y las calorías salen
    de acá y no se repiten en la Comida.

    Va ANTES de la ruta /{id_dieta} a propósito: FastAPI resuelve por orden de
    declaración, y si estuviera después leería "catalogo-comidas" como un id.
    """
    platos = (db.query(CatalogoComida)
              .filter(CatalogoComida.activo.is_(True))
              .order_by(CatalogoComida.nombre)
              .all())
    return [CatalogoComidaOut.model_validate(p) for p in platos]


@router.get("", response_model=list[DietaOut])
def listar_dietas(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.NUTRICION)),
):
    """Catálogo. Sin las comidas: la grilla muestra tarjetas con macros."""
    dietas = db.query(Dieta).order_by(Dieta.id_dieta.desc()).all()
    return [_a_dieta_out(d, con_comidas=False) for d in dietas]


@router.get("/{id_dieta}", response_model=DietaOut)
def obtener_dieta(
    id_dieta: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.NUTRICION)),
):
    """El detalle trae las comidas ordenadas por día y momento del día."""
    dieta = db.get(Dieta, id_dieta)
    if dieta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La dieta no existe.")
    return _a_dieta_out(dieta)


@router.post("", response_model=DietaOut, status_code=status.HTTP_201_CREATED)
def crear_dieta(
    datos: DietaCrear,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.GESTION_DIETAS)),
):
    """
    Crea una dieta con sus comidas, en una transacción.

    A nombre de quién queda lo decide _resolver_nutricionista: si quien crea
    ES nutricionista, la dieta es suya; si no lo es (Dueño, Recepcionista),
    tiene que elegir a cargo de quién queda.
    """
    nutri = _resolver_nutricionista(db, sesion, datos.id_nutricionista)

    dieta = Dieta(
        id_nutricionista=nutri.id_nutricionista,
        nombre=datos.nombre.strip(),
        objetivo=datos.objetivo,
        calorias_diarias=datos.calorias_diarias,
        descripcion=datos.descripcion,
        activo=True,
    )
    db.add(dieta)
    db.flush()

    for c in datos.comidas:
        db.add(Comida(
            id_dieta=dieta.id_dieta,
            dia=c.dia,
            momento=c.momento,
            id_catalogo_comida=c.id_catalogo_comida,
        ))

    db.commit()
    db.refresh(dieta)
    return _a_dieta_out(dieta)


# =============================================================================
# ASIGNACIÓN A SOCIOS
# =============================================================================

@router.post("/{id_dieta}/asignar", response_model=AsignacionDietaOut,
             status_code=status.HTTP_201_CREATED)
def asignar_dieta(
    id_dieta: int,
    datos: AsignarDietaRequest,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.GESTION_DIETAS)),
):
    """
    Le asigna la dieta a un socio.

    Igual que con las rutinas: si ya tenía una ACTIVA se la finaliza en vez de
    rechazar el pedido. Nadie sigue dos planes alimentarios a la vez, y la
    anterior queda como historial con estado FINALIZADA, no se borra.
    """
    dieta = db.get(Dieta, id_dieta)
    if dieta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La dieta no existe.")

    socio = db.get(Socio, datos.id_socio)
    if socio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El socio no existe.")

    hoy = date.today()

    activas = (
        db.query(AsignacionDieta)
        .filter(AsignacionDieta.id_socio == socio.id_socio,
                AsignacionDieta.estado == "ACTIVA")
        .all()
    )
    for anterior in activas:
        if anterior.id_dieta == id_dieta:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{socio.persona.nombre_completo} ya tiene asignada esa dieta.",
            )
        anterior.estado = "FINALIZADA"
        anterior.fecha_fin = hoy

    # El flush NO es opcional desde la migración 009.
    #
    # Esa migración agregó un índice único parcial que impide dos asignaciones
    # ACTIVA por socio. Un índice parcial no puede ser DEFERRABLE en Postgres,
    # así que se evalúa al terminar cada sentencia — y SQLAlchemy ordena su
    # flush poniendo los INSERT ANTES que los UPDATE. Sin esto, la fila nueva
    # entraría mientras la anterior sigue ACTIVA y la base rechazaría una
    # reasignación que es perfectamente válida.
    #
    # Es el mismo tipo de detalle que ya mordió en promover_de_lista_de_espera:
    # la sesión tiene autoflush=False, así que nada llega a la base hasta que
    # se lo pide explícitamente.
    db.flush()

    asignacion = AsignacionDieta(
        id_socio=socio.id_socio,
        id_dieta=id_dieta,
        # id_nutricionista ya no vive en la asignación: sale de Dieta.
        fecha_inicio=datos.fecha_inicio or hoy,
        fecha_fin=datos.fecha_fin,
        estado="ACTIVA",
        observaciones=datos.observaciones,
    )
    db.add(asignacion)
    db.commit()
    db.refresh(asignacion)

    return AsignacionDietaOut(
        id_asignacion_dieta=asignacion.id_asignacion_dieta,
        id_socio=socio.id_socio,
        socio=socio.persona.nombre_completo,
        id_dieta=id_dieta,
        dieta=dieta.nombre,
        fecha_inicio=asignacion.fecha_inicio,
        fecha_fin=asignacion.fecha_fin,
        estado=asignacion.estado,
        observaciones=asignacion.observaciones,
    )


@router.get("/asignaciones/socio/{id_socio}", response_model=list[AsignacionDietaOut])
def dietas_de_socio(
    id_socio: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.NUTRICION, Acceso.LECTURA)),
):
    """
    Historial de dietas de un socio, la actual primero.

    Endpoint de GESTIÓN. El socio viendo SU dieta va por el portal
    (`mi-dieta`), que filtra por el id_socio firmado en su token en vez de
    aceptar uno por parámetro — si lo aceptara, cualquier socio podría leer la
    dieta de otro cambiando un número en la URL.
    """
    asignaciones = (
        db.query(AsignacionDieta)
        .filter(AsignacionDieta.id_socio == id_socio)
        .order_by(AsignacionDieta.fecha_inicio.desc())
        .all()
    )
    return [
        AsignacionDietaOut(
            id_asignacion_dieta=a.id_asignacion_dieta,
            id_socio=a.id_socio,
            socio=a.socio.persona.nombre_completo if a.socio else "?",
            id_dieta=a.id_dieta,
            dieta=a.dieta.nombre if a.dieta else "?",
            fecha_inicio=a.fecha_inicio,
            fecha_fin=a.fecha_fin,
            estado=a.estado,
            observaciones=a.observaciones,
        )
        for a in asignaciones
    ]


# =============================================================================
# EDICIÓN Y BAJA
# =============================================================================

@router.put("/{id_dieta}", response_model=DietaOut)
def editar_dieta(
    id_dieta: int,
    datos: DietaEditarRequest,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.GESTION_DIETAS)),
):
    """Edita los datos de la dieta. Las comidas se manejan aparte."""
    dieta = db.get(Dieta, id_dieta)
    if dieta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La dieta no existe.")

    if datos.id_nutricionista is not None and datos.id_nutricionista != dieta.id_nutricionista:
        nutri = _resolver_nutricionista(db, sesion, datos.id_nutricionista)
        dieta.id_nutricionista = nutri.id_nutricionista

    dieta.nombre = datos.nombre.strip()
    dieta.objetivo = datos.objetivo
    dieta.calorias_diarias = datos.calorias_diarias
    dieta.descripcion = datos.descripcion

    db.commit()
    db.refresh(dieta)
    return _a_dieta_out(dieta)


@router.post("/{id_dieta}/baja", response_model=DietaOut)
def dar_de_baja_dieta(
    id_dieta: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.GESTION_DIETAS)),
):
    """
    Desactiva una dieta del catálogo. Baja lógica, mismo criterio que rutinas:
    los socios que la están siguiendo la terminan, pero deja de ofrecerse para
    asignaciones nuevas.
    """
    dieta = db.get(Dieta, id_dieta)
    if dieta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La dieta no existe.")
    if not dieta.activo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Esa dieta ya estaba desactivada.")

    dieta.activo = False
    db.commit()
    db.refresh(dieta)
    return _a_dieta_out(dieta)


@router.post("/{id_dieta}/reactivar", response_model=DietaOut)
def reactivar_dieta(
    id_dieta: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.GESTION_DIETAS)),
):
    dieta = db.get(Dieta, id_dieta)
    if dieta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La dieta no existe.")
    if dieta.activo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Esa dieta ya estaba activa.")

    dieta.activo = True
    db.commit()
    db.refresh(dieta)
    return _a_dieta_out(dieta)
