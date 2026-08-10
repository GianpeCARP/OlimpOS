"""
routers/asistencia.py
---------------------
Registro de ingresos al gimnasio: el panel de recepción.

EL SISTEMA INFORMA, NO JUZGA
----------------------------
Cuando alguien ficha con una deuda o la cuota vencida, el ingreso **se
registra igual** y la respuesta trae una advertencia. No se rechaza.

Es una decisión de negocio, no un descuido: dejar a alguien afuera del
gimnasio es algo que decide una persona en el mostrador mirando el caso —
puede ser un socio de años que se atrasó dos días, o alguien que ya avisó que
paga mañana. Un backend que devuelve 403 obliga a que ese criterio no exista.

Y hay una razón de datos además: si el ingreso no se registrara, el gimnasio
perdería el dato de que esa persona estuvo. Después nadie puede responder
"¿cuánta gente entró en marzo?" ni detectar que un moroso viene todos los
días.

RFID O MANUAL
-------------
`metodo_registro` distingue el fichaje con tarjeta del que carga alguien a
mano. Sirve al auditar: un registro MANUAL es una decisión de una persona
concreta —que queda guardada en `id_registrado_por`— y conviene poder
filtrarlos del total.
"""

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Asistencia, Deuda, Membresia, Socio
from permisos import Acceso, Seccion
from schemas import (
    AsistenciaOut, FicharRequest, FicharResponse, MetodoRegistro,
)
from security import Sesion, requiere_seccion

router = APIRouter(prefix="/asistencia", tags=["Asistencia"])

# Minutos dentro de los cuales un segundo fichaje se considera repetido. Cubre
# el caso real de pasar la tarjeta dos veces porque el lector no sonó.
MINUTOS_ANTI_DUPLICADO = 5


def _a_asistencia_out(a: Asistencia) -> AsistenciaOut:
    socio = a.socio
    persona = socio.persona if socio else None
    return AsistenciaOut(
        id_asistencia=a.id_asistencia,
        id_socio=a.id_socio,
        socio=persona.nombre_completo if persona else "?",
        numero_socio=socio.numero_socio if socio else None,
        fecha_hora_ingreso=a.fecha_hora_ingreso,
        fecha_hora_egreso=a.fecha_hora_egreso,
        metodo_registro=a.metodo_registro,
    )


def _revisar_situacion(db: Session, socio: Socio) -> str | None:
    """
    Devuelve una advertencia si el socio no está en condiciones, o None.

    NUNCA lanza: quien llama registra el ingreso igual. Ver el docstring del
    módulo.
    """
    if not socio.activo:
        return "El socio está dado de baja."

    hoy = date.today()
    vigente = (
        db.query(Membresia)
        .filter(Membresia.id_socio == socio.id_socio, Membresia.estado == "ACTIVA")
        .order_by(Membresia.fecha_inicio.desc())
        .first()
    )

    if vigente is None:
        return "No tiene ninguna membresía activa."

    if vigente.fecha_vencimiento and vigente.fecha_vencimiento < hoy:
        dias = (hoy - vigente.fecha_vencimiento).days
        return f"La cuota venció hace {dias} día(s) ({vigente.fecha_vencimiento})."

    deuda = (
        db.query(Deuda)
        .filter(Deuda.id_socio == socio.id_socio, Deuda.estado == "PENDIENTE")
        .all()
    )
    if deuda:
        total = sum(float(d.monto) for d in deuda)
        return f"Tiene {len(deuda)} deuda(s) pendiente(s) por ${total:,.2f}."

    return None


@router.post("/fichar", response_model=FicharResponse, status_code=status.HTTP_201_CREATED)
def fichar(
    datos: FicharRequest,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.ASISTENCIA, Acceso.TOTAL)),
):
    """
    Registra un ingreso, por tarjeta RFID o a mano.

    Devuelve 201 aunque el socio tenga problemas: el campo `permitido` y la
    `advertencia` son lo que le dice al mostrador que mire el caso.
    """
    # Exactamente una de las dos vías. Aceptar ambas dejaría ambiguo a quién
    # se fichó si discreparan.
    if bool(datos.codigo_rfid) == bool(datos.id_socio):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Indicá el código RFID o el id del socio, pero no los dos.",
        )

    if datos.codigo_rfid:
        socio = (db.query(Socio)
                 .filter(Socio.codigo_rfid == datos.codigo_rfid.strip())
                 .first())
        metodo = MetodoRegistro.RFID
        if socio is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Esa tarjeta no está asignada a ningún socio.",
            )
    else:
        socio = db.get(Socio, datos.id_socio)
        metodo = MetodoRegistro.MANUAL
        if socio is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El socio no existe.",
            )

    ahora = datetime.now()

    # Anti-duplicado: pasar la tarjeta dos veces porque el lector no sonó es
    # lo más común del mostrador. Sin esto, el conteo diario de ingresos
    # quedaría inflado.
    reciente = (
        db.query(Asistencia)
        .filter(Asistencia.id_socio == socio.id_socio,
                Asistencia.fecha_hora_ingreso >= ahora - timedelta(minutes=MINUTOS_ANTI_DUPLICADO))
        .first()
    )
    if reciente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(f"{socio.persona.nombre_completo} ya fichó hace menos de "
                    f"{MINUTOS_ANTI_DUPLICADO} minutos."),
        )

    advertencia = _revisar_situacion(db, socio)

    asistencia = Asistencia(
        id_socio=socio.id_socio,
        id_sede=socio.id_sede,
        fecha_hora_ingreso=ahora,
        metodo_registro=metodo.value,
        # Queda registrado QUIÉN cargó el ingreso. Con RFID no hay una persona
        # detrás, pero sí una sesión abierta en el panel de recepción.
        id_registrado_por=sesion.id_usuario,
    )
    db.add(asistencia)
    db.commit()
    db.refresh(asistencia)

    nombre = socio.persona.nombre_completo
    mensaje = f"Ingreso registrado: {nombre}."
    if advertencia:
        mensaje = f"Ingreso registrado con observaciones: {nombre}. {advertencia}"

    return FicharResponse(
        asistencia=_a_asistencia_out(asistencia),
        permitido=advertencia is None,
        advertencia=advertencia,
        mensaje=mensaje,
    )


@router.get("/hoy", response_model=list[AsistenciaOut])
def ingresos_de_hoy(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.ASISTENCIA)),
):
    """Los ingresos del día, el más reciente primero. Es el feed del panel."""
    inicio = datetime.combine(date.today(), datetime.min.time())
    asistencias = (
        db.query(Asistencia)
        .filter(Asistencia.fecha_hora_ingreso >= inicio)
        .order_by(Asistencia.fecha_hora_ingreso.desc())
        .all()
    )
    return [_a_asistencia_out(a) for a in asistencias]


@router.post("/{id_asistencia}/salida", response_model=AsistenciaOut)
def registrar_salida(
    id_asistencia: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.ASISTENCIA, Acceso.TOTAL)),
):
    """
    Marca el egreso.

    Es opcional: la mayoría de los gimnasios no controla la salida, y un
    ingreso sin egreso es un registro válido —significa "entró"—, no un dato
    incompleto.
    """
    asistencia = db.get(Asistencia, id_asistencia)
    if asistencia is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Ese registro de ingreso no existe.")

    if asistencia.fecha_hora_egreso is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Ese ingreso ya tenía la salida registrada.")

    asistencia.fecha_hora_egreso = datetime.now()
    db.commit()
    db.refresh(asistencia)
    return _a_asistencia_out(asistencia)


@router.get("/socio/{id_socio}", response_model=list[AsistenciaOut])
def historial_socio(
    id_socio: int,
    limite: int = 30,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.ASISTENCIA)),
):
    """Últimos ingresos de un socio. Sirve para ver su regularidad."""
    asistencias = (
        db.query(Asistencia)
        .filter(Asistencia.id_socio == id_socio)
        .order_by(Asistencia.fecha_hora_ingreso.desc())
        .limit(min(limite, 200))
        .all()
    )
    return [_a_asistencia_out(a) for a in asistencias]
