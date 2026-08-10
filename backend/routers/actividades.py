"""
routers/actividades.py
----------------------
Clases con horario: catálogo, turnos y reservas.

    Actividad              'Yoga' — qué ofrece el gimnasio
    Plan_Actividad         'Yoga 2 veces por semana' — el abono
    Inscripcion_Actividad  un socio anotado a un plan, con su saldo
    Turno                  'Yoga, martes 12/08 a las 18:00' — la clase concreta
    Reserva                un socio anotado a ese turno

POR QUÉ EL TURNO ES POR FECHA Y NO UN HORARIO RECURRENTE
--------------------------------------------------------
Sería más compacto guardar "Yoga los martes a las 18" una sola vez. El
problema aparece el martes que hay que cancelar la clase porque el profesor
se enfermó: con un horario recurrente no hay dónde anotar esa excepción sin
inventar una tabla de excepciones, que termina siendo más complicada que
tener una fila por fecha.

Con una fila por turno se puede cancelar una clase puntual con su motivo,
cambiarle el profesor o ampliarle el cupo sin tocar el resto de las semanas.

LAS TRES REGLAS QUE VIVEN ACÁ
-----------------------------
1. El cupo no se supera. Se cuentan las reservas activas contra
   `cupo_maximo` en el momento de reservar, del lado del servidor. Si esto
   viviera solo en el frontend, bastaría con llamar al endpoint directamente
   para meter a un socio de más.

2. No se reserva sin saldo. Quien tiene un abono "2 por semana" no puede
   anotarse a la tercera. Se descuenta de `clases_restantes` al reservar.

3. Cancelar a último momento no devuelve la clase. Cada actividad define su
   `horas_anticipacion_cancelacion`: si el socio cancela dentro de esa
   ventana, pierde la clase. Si la cancela el gimnasio, siempre se le
   devuelve — no es su culpa.
"""

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Actividad, InscripcionActividad, PlanActividad, Profesor, Reserva, Sede,
    Socio, Turno,
)
from permisos import Acceso, Accion, Seccion
from schemas import (
    ActividadCrear, ActividadOut, PlanActividadOut, ReservaOut, ReservarRequest,
    TurnoCrear, TurnoOut,
)
from security import Sesion, requiere_accion, requiere_seccion

router = APIRouter(prefix="/actividades", tags=["Actividades"])

# Estados de reserva que ocupan un lugar. Las canceladas liberan el cupo.
RESERVA_OCUPA = ("RESERVADA",)


# =============================================================================
# HELPERS
# =============================================================================

def _reservas_activas(turno: Turno) -> int:
    return sum(1 for r in turno.reservas if r.estado in RESERVA_OCUPA)


def _a_turno_out(turno: Turno) -> TurnoOut:
    ocupados = _reservas_activas(turno)
    profesor = None
    if turno.profesor and turno.profesor.empleado and turno.profesor.empleado.persona:
        profesor = turno.profesor.empleado.persona.nombre_completo

    return TurnoOut(
        id_turno=turno.id_turno,
        id_actividad=turno.id_actividad,
        actividad=turno.actividad.nombre if turno.actividad else "?",
        fecha=turno.fecha,
        hora=turno.hora,
        cupo_maximo=turno.cupo_maximo,
        reservados=ocupados,
        lugares_libres=max(0, turno.cupo_maximo - ocupados),
        estado=turno.estado,
        profesor=profesor,
        motivo_cancelacion=turno.motivo_cancelacion,
    )


def _a_actividad_out(a: Actividad) -> ActividadOut:
    return ActividadOut(
        id_actividad=a.id_actividad,
        nombre=a.nombre,
        descripcion=a.descripcion,
        cupo_default=a.cupo_default,
        precio_clase_suelta=float(a.precio_clase_suelta),
        horas_anticipacion_cancelacion=a.horas_anticipacion_cancelacion,
        activo=bool(a.activo),
        planes=[
            PlanActividadOut(
                id_plan_actividad=p.id_plan_actividad, id_actividad=p.id_actividad,
                nombre=p.nombre, tipo_limite=p.tipo_limite, cantidad=p.cantidad,
                precio=float(p.precio), activo=bool(p.activo),
            )
            for p in a.planes
        ],
    )


def _inscripcion_vigente(db: Session, id_socio: int, id_actividad: int) -> InscripcionActividad | None:
    """
    El abono activo del socio para esa actividad, o None si no tiene.

    Marca como VENCIDA sobre la marcha las que pasaron su fecha: sin una tarea
    programada, el estado en la base se queda viejo y un abono terminado
    seguiría dejando reservar.
    """
    hoy = date.today()
    inscripciones = (
        db.query(InscripcionActividad)
        .join(PlanActividad,
              InscripcionActividad.id_plan_actividad == PlanActividad.id_plan_actividad)
        .filter(InscripcionActividad.id_socio == id_socio,
                PlanActividad.id_actividad == id_actividad,
                InscripcionActividad.estado == "ACTIVA")
        .all()
    )

    for i in inscripciones:
        if i.fecha_vencimiento < hoy:
            i.estado = "VENCIDA"
        else:
            return i
    return None


# =============================================================================
# CATÁLOGO
# =============================================================================

@router.get("", response_model=list[ActividadOut])
def listar_actividades(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.ACTIVIDADES)),
):
    actividades = db.query(Actividad).order_by(Actividad.nombre).all()
    return [_a_actividad_out(a) for a in actividades]


@router.post("", response_model=ActividadOut, status_code=status.HTTP_201_CREATED)
def crear_actividad(
    datos: ActividadCrear,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.ACTIVIDADES, Acceso.TOTAL)),
):
    """
    Crea una actividad. La sección está en TOTAL solo para el Dueño: definir
    qué clases ofrece el gimnasio y a qué precio es configuración de negocio,
    no operativa del día a día.
    """
    nombre = datos.nombre.strip()
    if db.query(Actividad).filter(Actividad.nombre.ilike(nombre)).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Ya existe una actividad llamada '{nombre}'.")

    actividad = Actividad(
        nombre=nombre, descripcion=datos.descripcion,
        cupo_default=datos.cupo_default,
        precio_clase_suelta=datos.precio_clase_suelta,
        horas_anticipacion_cancelacion=datos.horas_anticipacion_cancelacion,
        activo=True,
    )
    db.add(actividad)
    db.commit()
    db.refresh(actividad)
    return _a_actividad_out(actividad)


# =============================================================================
# TURNOS
# =============================================================================

@router.get("/turnos", response_model=list[TurnoOut])
def listar_turnos(
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.ACTIVIDADES)),
):
    """
    Turnos en un rango de fechas. Por defecto, la semana que viene — es lo que
    muestra la grilla, y sin límite se bajaría el historial completo.
    """
    desde = desde or date.today()
    hasta = hasta or (desde + timedelta(days=7))

    turnos = (
        db.query(Turno)
        .filter(Turno.fecha >= desde, Turno.fecha <= hasta)
        .order_by(Turno.fecha, Turno.hora)
        .all()
    )
    return [_a_turno_out(t) for t in turnos]


@router.post("/turnos", response_model=TurnoOut, status_code=status.HTTP_201_CREATED)
def crear_turno(
    datos: TurnoCrear,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.GESTION_TURNOS)),
):
    """Programa una clase concreta."""
    actividad = db.get(Actividad, datos.id_actividad)
    if actividad is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="La actividad no existe.")
    if db.get(Sede, datos.id_sede) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="La sede no existe.")
    if datos.id_profesor and db.get(Profesor, datos.id_profesor) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="El profesor no existe.")

    # Sin turnos en el pasado: reservar algo que ya ocurrió no tiene sentido y
    # ensuciaría la grilla.
    if datos.fecha < date.today():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="No se puede programar una clase en una fecha pasada.")

    turno = Turno(
        id_sede=datos.id_sede,
        id_actividad=datos.id_actividad,
        fecha=datos.fecha,
        hora=datos.hora,
        # El cupo de la actividad como default, con la opción de pisarlo para
        # una clase puntual (un día que se usa un salón más grande).
        cupo_maximo=datos.cupo_maximo or actividad.cupo_default,
        id_profesor=datos.id_profesor,
        estado="HABILITADO",
    )
    db.add(turno)
    db.commit()
    db.refresh(turno)
    return _a_turno_out(turno)


@router.post("/turnos/{id_turno}/cancelar", response_model=TurnoOut)
def cancelar_turno(
    id_turno: int,
    motivo: str = "",
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.GESTION_TURNOS)),
):
    """
    Cancela una clase (se enfermó el profesor, se rompió algo).

    Cancela también todas las reservas como CANCELADA_GIMNASIO y **devuelve la
    clase** a cada socio que tenía abono. La distinción con
    CANCELADA_SOCIO es exactamente para esto: si la clase se cae por culpa del
    gimnasio, nadie pierde su cupo.
    """
    turno = db.get(Turno, id_turno)
    if turno is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El turno no existe.")
    if turno.estado == "CANCELADO":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Esa clase ya estaba cancelada.")

    turno.estado = "CANCELADO"
    turno.motivo_cancelacion = motivo.strip() or "Cancelada por el gimnasio"

    ahora = datetime.now()
    for reserva in turno.reservas:
        if reserva.estado != "RESERVADA":
            continue
        reserva.estado = "CANCELADA_GIMNASIO"
        reserva.fecha_cancelacion = ahora
        if reserva.inscripcion and reserva.inscripcion.clases_restantes is not None:
            reserva.inscripcion.clases_restantes += 1

    db.commit()
    db.refresh(turno)
    return _a_turno_out(turno)


# =============================================================================
# RESERVAS
# =============================================================================

@router.post("/turnos/{id_turno}/reservar", response_model=ReservaOut,
             status_code=status.HTTP_201_CREATED)
def reservar(
    id_turno: int,
    datos: ReservarRequest,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.GESTION_TURNOS)),
):
    """
    Anota a un socio en una clase. Acá viven las reglas 1 y 2.

    El chequeo de cupo se hace del lado del servidor a propósito: si viviera
    solo en el frontend (deshabilitando el botón cuando está lleno), bastaría
    con llamar a este endpoint directamente para meter un socio de más.
    """
    turno = db.get(Turno, id_turno)
    if turno is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El turno no existe.")
    if turno.estado == "CANCELADO":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Esa clase está cancelada.")

    socio = db.get(Socio, datos.id_socio)
    if socio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El socio no existe.")

    # --- Ya anotado ---------------------------------------------------------
    ya = next((r for r in turno.reservas
               if r.id_socio == socio.id_socio and r.estado == "RESERVADA"), None)
    if ya:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{socio.persona.nombre_completo} ya está anotado en esa clase.",
        )

    # --- Regla 1: el cupo ---------------------------------------------------
    if _reservas_activas(turno) >= turno.cupo_maximo:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(f"La clase de {turno.actividad.nombre} del {turno.fecha} "
                    f"ya está completa ({turno.cupo_maximo} lugares)."),
        )

    # --- Regla 2: el saldo --------------------------------------------------
    inscripcion = None
    if not datos.es_clase_suelta:
        inscripcion = _inscripcion_vigente(db, socio.id_socio, turno.id_actividad)
        if inscripcion is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(f"{socio.persona.nombre_completo} no tiene un abono activo de "
                        f"{turno.actividad.nombre}. Cobrale un plan o marcá la reserva "
                        "como clase suelta."),
            )
        if inscripcion.clases_restantes is not None and inscripcion.clases_restantes <= 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(f"{socio.persona.nombre_completo} ya usó todas las clases de su "
                        f"abono ({inscripcion.plan.nombre}). Puede venir como clase suelta."),
            )
        inscripcion.clases_restantes -= 1

    reserva = Reserva(
        id_turno=turno.id_turno,
        id_socio=socio.id_socio,
        id_inscripcion=inscripcion.id_inscripcion if inscripcion else None,
        es_clase_suelta=datos.es_clase_suelta,
        fecha_reserva=datetime.now(),
        estado="RESERVADA",
    )
    db.add(reserva)
    db.commit()
    db.refresh(reserva)

    return ReservaOut(
        id_reserva=reserva.id_reserva,
        id_turno=turno.id_turno,
        id_socio=socio.id_socio,
        socio=socio.persona.nombre_completo,
        actividad=turno.actividad.nombre,
        fecha=turno.fecha,
        hora=turno.hora,
        estado=reserva.estado,
        es_clase_suelta=bool(reserva.es_clase_suelta),
        clases_restantes=inscripcion.clases_restantes if inscripcion else None,
    )


@router.post("/reservas/{id_reserva}/cancelar", response_model=ReservaOut)
def cancelar_reserva(
    id_reserva: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.GESTION_TURNOS)),
):
    """
    Cancela la reserva de un socio. Acá vive la regla 3.

    Si cancela con la anticipación que pide la actividad, se le devuelve la
    clase al abono. Si cancela encima de la hora, la pierde: el lugar quedó
    ocupado hasta último momento y otro socio no pudo usarlo. Esa ventana la
    define cada actividad en `horas_anticipacion_cancelacion`.
    """
    reserva = db.get(Reserva, id_reserva)
    if reserva is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="La reserva no existe.")
    if reserva.estado != "RESERVADA":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Esa reserva ya estaba cancelada.")

    turno = reserva.turno
    actividad = turno.actividad
    inicio_clase = datetime.combine(turno.fecha, turno.hora)
    horas_de_aviso = (inicio_clase - datetime.now()).total_seconds() / 3600

    a_tiempo = horas_de_aviso >= (actividad.horas_anticipacion_cancelacion or 0)

    reserva.estado = "CANCELADA_SOCIO"
    reserva.fecha_cancelacion = datetime.now()

    restantes = None
    if reserva.inscripcion and reserva.inscripcion.clases_restantes is not None:
        if a_tiempo:
            reserva.inscripcion.clases_restantes += 1
        restantes = reserva.inscripcion.clases_restantes

    db.commit()
    db.refresh(reserva)

    return ReservaOut(
        id_reserva=reserva.id_reserva,
        id_turno=turno.id_turno,
        id_socio=reserva.id_socio,
        socio=reserva.socio.persona.nombre_completo,
        actividad=actividad.nombre,
        fecha=turno.fecha,
        hora=turno.hora,
        estado=reserva.estado,
        es_clase_suelta=bool(reserva.es_clase_suelta),
        clases_restantes=restantes,
    )


@router.get("/turnos/{id_turno}/reservas", response_model=list[ReservaOut])
def listar_reservas(
    id_turno: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.ACTIVIDADES)),
):
    """Quiénes están anotados en una clase. Es la lista que usa el profesor."""
    turno = db.get(Turno, id_turno)
    if turno is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El turno no existe.")

    return [
        ReservaOut(
            id_reserva=r.id_reserva, id_turno=turno.id_turno, id_socio=r.id_socio,
            socio=r.socio.persona.nombre_completo if r.socio else "?",
            actividad=turno.actividad.nombre, fecha=turno.fecha, hora=turno.hora,
            estado=r.estado, es_clase_suelta=bool(r.es_clase_suelta),
            clases_restantes=None,
        )
        for r in turno.reservas if r.estado == "RESERVADA"
    ]
