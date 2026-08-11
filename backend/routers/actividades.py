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
    Actividad, Deuda, Empleado, InscripcionActividad, Membresia, Pago, PlanActividad,
    Profesor, ProfesorActividad, Reserva, Sede, Socio, Turno,
)
from permisos import Acceso, Accion, Seccion
from schemas import (
    ActividadCrear, ActividadOut, ComprarPlanRequest, ComprarPlanResponse,
    InscripcionOut, PagoOut, PlanActividadCrear, PlanActividadOut,
    ProfesorActividadOut, PuedeComprarOut, ReservaOut, ReservarRequest,
    TurnoCrear, TurnoOut, ClaseSueltaResponse, ComprarClaseSueltaRequest,
)
from security import Sesion, requiere_accion, requiere_seccion

router = APIRouter(prefix="/actividades", tags=["Actividades"])

# Estados de reserva que ocupan un lugar. Las canceladas liberan el cupo.
RESERVA_OCUPA = ("RESERVADA",)


def _sumar_un_mes(desde: date) -> date:
    """
    Un mes calendario exacto, no 30 días.

    La diferencia importa: una membresía "mensual" de 30 días NO cubre un mes
    calendario de 31, que es la mayoría de los meses. Usar 30 días haría que
    la validación de cobertura pase cuando no debería.

    El 31 de enero + 1 mes da 28 de febrero (o 29): se recorta al último día
    del mes destino, que es lo que hace cualquier calendario.
    """
    anio = desde.year + (1 if desde.month == 12 else 0)
    mes = 1 if desde.month == 12 else desde.month + 1

    # Último día del mes destino: el día 1 del siguiente, menos uno.
    if mes == 12:
        primero_del_siguiente = date(anio + 1, 1, 1)
    else:
        primero_del_siguiente = date(anio, mes + 1, 1)
    ultimo_dia = (primero_del_siguiente - timedelta(days=1)).day

    return date(anio, mes, min(desde.day, ultimo_dia))


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


@router.get("/profesores", response_model=list[ProfesorActividadOut])
def listar_todos_los_profesores(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.ACTIVIDADES)),
):
    """
    Todos los profesores activos del plantel, estén o no asignados.

    Va aparte de `/{id_actividad}/profesores` —que devuelve solo los
    asignados— porque el panel de asignación necesita las DOS listas: los que
    ya están y los que se podrían agregar. Sin este endpoint, el frontend
    tendría que sacarlos de /personal y ahí solo viene `id_empleado`, no
    `id_profesor`, que es lo que la tabla puente necesita.

    Declarado ANTES de /{id_actividad}/profesores: si fuera después, FastAPI
    intentaría leer "profesores" como si fuera un id de actividad.
    """
    profesores = (
        db.query(Profesor)
        .join(Empleado, Profesor.id_empleado == Empleado.id_empleado)
        .filter(Empleado.activo == True)  # noqa: E712
        .all()
    )
    salida = []
    for p in profesores:
        persona = p.empleado.persona if p.empleado else None
        salida.append(ProfesorActividadOut(
            id_profesor=p.id_profesor,
            nombre=persona.nombre_completo if persona else "?",
            titulo=p.titulo,
            especialidad=p.especialidad,
        ))
    return salida


# =============================================================================
# ABM DE ACTIVIDADES Y PLANES
# =============================================================================
# Todo esto es configuración de negocio: qué clases ofrece el gimnasio, con
# qué abonos y a qué precio. Por eso va con Acceso.TOTAL sobre la sección,
# que en la matriz solo tiene el Dueño — el Recepcionista opera el día a día
# (reservar, cancelar) pero no define el catálogo.


def _buscar_actividad(db: Session, id_actividad: int) -> Actividad:
    actividad = db.get(Actividad, id_actividad)
    if actividad is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="La actividad no existe.")
    return actividad


def _buscar_plan(db: Session, id_plan: int) -> PlanActividad:
    plan = db.get(PlanActividad, id_plan)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="El plan no existe.")
    return plan


def _a_plan_out(p: PlanActividad) -> PlanActividadOut:
    return PlanActividadOut(
        id_plan_actividad=p.id_plan_actividad, id_actividad=p.id_actividad,
        nombre=p.nombre, tipo_limite=p.tipo_limite, cantidad=p.cantidad,
        precio=float(p.precio), activo=bool(p.activo),
    )


@router.put("/{id_actividad}", response_model=ActividadOut)
def actualizar_actividad(
    id_actividad: int,
    datos: ActividadCrear,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.ACTIVIDADES, Acceso.TOTAL)),
):
    """
    Edita una actividad.

    Ojo con `cupo_default`: cambiarlo NO toca los turnos ya programados. Cada
    Turno guardó su propio `cupo_maximo` al crearse justamente para esto — si
    el cupo se leyera de la actividad, bajarlo dejaría turnos con más gente
    anotada que lugares.
    """
    actividad = _buscar_actividad(db, id_actividad)
    nombre = datos.nombre.strip()

    choca = (db.query(Actividad)
             .filter(Actividad.nombre.ilike(nombre),
                     Actividad.id_actividad != id_actividad)
             .first())
    if choca:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Ya existe una actividad llamada '{nombre}'.")

    actividad.nombre = nombre
    actividad.descripcion = datos.descripcion
    actividad.cupo_default = datos.cupo_default
    actividad.precio_clase_suelta = datos.precio_clase_suelta
    actividad.horas_anticipacion_cancelacion = datos.horas_anticipacion_cancelacion
    db.commit()
    db.refresh(actividad)
    return _a_actividad_out(actividad)


@router.post("/{id_actividad}/toggle-estado", response_model=ActividadOut)
def alternar_estado_actividad(
    id_actividad: int,
    activo: bool | None = None,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.ACTIVIDADES, Acceso.TOTAL)),
):
    """
    Da de baja o reactiva una actividad. NO la borra.

    Borrarla dejaría huérfanos los turnos, las inscripciones y los pagos que
    la referencian — y esos pagos son historial contable. Con la baja lógica,
    la actividad deja de ofrecerse pero todo lo que ya pasó sigue teniendo
    sentido.

    Al darla de baja se cancelan sus turnos FUTUROS: seguir aceptando reservas
    de una actividad discontinuada sería vender algo que no se va a dictar.
    Los turnos pasados no se tocan, son historial.
    """
    actividad = _buscar_actividad(db, id_actividad)
    #  explicito gana sobre el toggle. El toggle solo es seguro si
    # quien llama conoce el estado actual: con una pantalla desactualizada,
    # "dar de baja" sobre algo ya dado de baja lo REACTIVARIA. El frontend
    # manda el estado que quiere y no depende de lo que crea tener.
    actividad.activo = (not bool(actividad.activo)) if activo is None else activo

    if not actividad.activo:
        hoy = date.today()
        futuros = (db.query(Turno)
                   .filter(Turno.id_actividad == id_actividad,
                           Turno.fecha >= hoy,
                           Turno.estado == "HABILITADO")
                   .all())
        ahora = datetime.now()
        for turno in futuros:
            turno.estado = "CANCELADO"
            turno.motivo_cancelacion = f"Se dio de baja la actividad {actividad.nombre}"
            for reserva in turno.reservas:
                if reserva.estado != "RESERVADA":
                    continue
                reserva.estado = "CANCELADA_GIMNASIO"
                reserva.fecha_cancelacion = ahora
                # Se devuelve la clase: la baja la decidió el gimnasio.
                if reserva.inscripcion and reserva.inscripcion.clases_restantes is not None:
                    reserva.inscripcion.clases_restantes += 1

    db.commit()
    db.refresh(actividad)
    return _a_actividad_out(actividad)


@router.get("/{id_actividad}/planes", response_model=list[PlanActividadOut])
def listar_planes(
    id_actividad: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.ACTIVIDADES)),
):
    _buscar_actividad(db, id_actividad)
    planes = (db.query(PlanActividad)
              .filter(PlanActividad.id_actividad == id_actividad)
              .order_by(PlanActividad.precio)
              .all())
    return [_a_plan_out(p) for p in planes]


@router.post("/{id_actividad}/planes", response_model=PlanActividadOut,
             status_code=status.HTTP_201_CREATED)
def crear_plan(
    id_actividad: int,
    datos: PlanActividadCrear,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.ACTIVIDADES, Acceso.TOTAL)),
):
    actividad = _buscar_actividad(db, id_actividad)

    plan = PlanActividad(
        id_actividad=actividad.id_actividad,
        nombre=datos.nombre.strip(),
        tipo_limite=datos.tipo_limite.value,
        cantidad=datos.cantidad,
        precio=datos.precio,
        activo=True,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return _a_plan_out(plan)


@router.put("/planes/{id_plan}", response_model=PlanActividadOut)
def actualizar_plan(
    id_plan: int,
    datos: PlanActividadCrear,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.ACTIVIDADES, Acceso.TOTAL)),
):
    """
    Edita un plan.

    Cambiar el precio NO afecta a quien ya lo compró: la inscripción guardó su
    `precio_pactado`. Es la misma razón por la que Membresia tiene su copia
    del precio — un aumento no puede reescribir lo que alguien ya pagó.
    """
    plan = _buscar_plan(db, id_plan)
    plan.nombre = datos.nombre.strip()
    plan.tipo_limite = datos.tipo_limite.value
    plan.cantidad = datos.cantidad
    plan.precio = datos.precio
    db.commit()
    db.refresh(plan)
    return _a_plan_out(plan)


@router.post("/planes/{id_plan}/toggle-estado", response_model=PlanActividadOut)
def alternar_estado_plan(
    id_plan: int,
    activo: bool | None = None,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.ACTIVIDADES, Acceso.TOTAL)),
):
    """
    Da de baja o reactiva un plan.

    Las inscripciones YA compradas siguen valiendo hasta su vencimiento: quien
    pagó tres meses de "Yoga 2 por semana" no pierde lo que pagó porque el
    gimnasio deje de ofrecer ese abono. Solo deja de poder comprarse.
    """
    plan = _buscar_plan(db, id_plan)
    # Igual que en actividades: el estado explicito gana sobre el toggle.
    plan.activo = (not bool(plan.activo)) if activo is None else activo
    db.commit()
    db.refresh(plan)
    return _a_plan_out(plan)


# =============================================================================
# PROFESORES POR ACTIVIDAD
# =============================================================================

@router.get("/{id_actividad}/profesores", response_model=list[ProfesorActividadOut])
def listar_profesores(
    id_actividad: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.ACTIVIDADES)),
):
    """Quiénes pueden dictar esta actividad."""
    _buscar_actividad(db, id_actividad)
    filas = (db.query(ProfesorActividad)
             .filter(ProfesorActividad.id_actividad == id_actividad)
             .all())

    salida = []
    for f in filas:
        prof = f.profesor
        persona = prof.empleado.persona if prof and prof.empleado else None
        salida.append(ProfesorActividadOut(
            id_profesor=f.id_profesor,
            nombre=persona.nombre_completo if persona else "?",
            titulo=prof.titulo if prof else None,
            especialidad=prof.especialidad if prof else None,
        ))
    return salida


@router.post("/{id_actividad}/profesores/{id_profesor}",
             status_code=status.HTTP_201_CREATED, response_model=ProfesorActividadOut)
def asignar_profesor(
    id_actividad: int,
    id_profesor: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.ACTIVIDADES, Acceso.TOTAL)),
):
    actividad = _buscar_actividad(db, id_actividad)
    profesor = db.get(Profesor, id_profesor)
    if profesor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="El profesor no existe.")

    ya = db.get(ProfesorActividad, (id_profesor, id_actividad))
    if ya:
        persona = profesor.empleado.persona if profesor.empleado else None
        nombre = persona.nombre_completo if persona else "Ese profesor"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{nombre} ya está asignado a {actividad.nombre}.",
        )

    db.add(ProfesorActividad(id_profesor=id_profesor, id_actividad=id_actividad))
    db.commit()

    persona = profesor.empleado.persona if profesor.empleado else None
    return ProfesorActividadOut(
        id_profesor=id_profesor,
        nombre=persona.nombre_completo if persona else "?",
        titulo=profesor.titulo,
        especialidad=profesor.especialidad,
    )


@router.delete("/{id_actividad}/profesores/{id_profesor}",
               status_code=status.HTTP_204_NO_CONTENT)
def desasignar_profesor(
    id_actividad: int,
    id_profesor: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.ACTIVIDADES, Acceso.TOTAL)),
):
    """
    Saca a un profesor de una actividad.

    Los turnos ya programados con él NO se tocan: el vínculo se guarda en
    Turno.id_profesor, y borrarlo dejaría clases sin responsable. Lo que se
    quita es la habilitación para asignarlo a turnos FUTUROS.
    """
    fila = db.get(ProfesorActividad, (id_profesor, id_actividad))
    if fila is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Ese profesor no está asignado a esta actividad.")
    db.delete(fila)
    db.commit()


# =============================================================================
# INSCRIPCIONES — comprar un abono
# =============================================================================

def _a_inscripcion_out(i: InscripcionActividad) -> InscripcionOut:
    plan = i.plan
    actividad = plan.actividad if plan else None
    persona = i.socio.persona if i.socio else None
    return InscripcionOut(
        id_inscripcion=i.id_inscripcion,
        id_socio=i.id_socio,
        socio=persona.nombre_completo if persona else "?",
        id_plan_actividad=i.id_plan_actividad,
        plan=plan.nombre if plan else "?",
        actividad=actividad.nombre if actividad else "?",
        id_actividad=actividad.id_actividad if actividad else 0,
        tipo_limite=plan.tipo_limite if plan else "POR_MES",
        cantidad=plan.cantidad if plan else 0,
        precio_pactado=float(i.precio_pactado),
        fecha_inicio=i.fecha_inicio,
        fecha_vencimiento=i.fecha_vencimiento,
        clases_restantes=i.clases_restantes,
        estado=i.estado,
    )


@router.get("/inscripciones/socio/{id_socio}", response_model=list[InscripcionOut])
def inscripciones_de_socio(
    id_socio: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.ACTIVIDADES)),
):
    """Abonos de un socio. Endpoint de GESTIÓN — el socio ve los suyos en /portal."""
    inscripciones = (db.query(InscripcionActividad)
                     .filter(InscripcionActividad.id_socio == id_socio)
                     .order_by(InscripcionActividad.fecha_inicio.desc())
                     .all())
    return [_a_inscripcion_out(i) for i in inscripciones]


@router.post("/planes/{id_plan}/comprar", response_model=ComprarPlanResponse,
             status_code=status.HTTP_201_CREATED)
def comprar_plan(
    id_plan: int,
    datos: ComprarPlanRequest,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.COBRAR_PAGOS)),
):
    """
    Un socio compra un abono de actividad. Crea la Inscripción y el Pago.

    EXIGE MEMBRESÍA VIGENTE. `Inscripcion_Actividad.id_membresia` es NOT NULL
    en el esquema, y eso codifica una regla de negocio: los abonos de
    actividad son un adicional sobre la cuota, no un reemplazo. Sin cuota al
    día no se puede comprar yoga.

    El precio sale del plan, no del pedido — misma razón que en el cobro de
    membresía: si viniera del cliente, cualquiera compraría un abono por $1.

    `clases_restantes` arranca en `cantidad` para los planes POR_MES. Para los
    POR_SEMANA queda en None: el límite es semanal y se recalcula, no se
    descuenta de un saldo total.
    """
    plan = _buscar_plan(db, id_plan)
    if not plan.activo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El plan '{plan.nombre}' está dado de baja y no se puede comprar.",
        )

    actividad = plan.actividad
    if actividad is not None and not actividad.activo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La actividad {actividad.nombre} está discontinuada.",
        )

    socio = db.get(Socio, datos.id_socio)
    if socio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="El socio no existe.")

    hoy = date.today()

    membresia = (db.query(Membresia)
                 .filter(Membresia.id_socio == socio.id_socio,
                         Membresia.estado == "ACTIVA")
                 .order_by(Membresia.fecha_vencimiento.desc())
                 .first())
    if membresia is None or (membresia.fecha_vencimiento and membresia.fecha_vencimiento < hoy):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(f"{socio.persona.nombre_completo} no tiene la cuota al día. "
                    "Los abonos de actividad son un adicional sobre la membresía: "
                    "cobrale la cuota primero."),
        )

    # Un abono activo del mismo plan sería cobrarle dos veces lo mismo.
    ya = _inscripcion_vigente(db, socio.id_socio, plan.id_actividad)
    if ya is not None and ya.id_plan_actividad == plan.id_plan_actividad:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(f"{socio.persona.nombre_completo} ya tiene un abono activo de "
                    f"{plan.nombre}, vigente hasta el {ya.fecha_vencimiento}."),
        )

    # --- REGLA 1: cobertura -------------------------------------------------
    # El abono vence UN MES DESPUÉS de comprarse, sea cual sea su tipo_limite:
    # un plan "2 por semana" se factura mensual igual que uno de "12 clases al
    # mes". `tipo_limite` cambia CÓMO se mide el consumo, no cuándo se cobra
    # de nuevo.
    #
    # Y por eso la membresía tiene que cubrir ese mes ENTERO. Si no llega, se
    # rechaza acá en vez de recortar el abono en silencio: recortarlo sería
    # cobrarle un mes y darle veinte días. La alternativa correcta es que el
    # mostrador renueve la cuota primero, y para eso existe /puede-comprar,
    # que deja preguntarlo ANTES de cobrar nada.
    vencimiento = _sumar_un_mes(hoy)

    if membresia.fecha_vencimiento and membresia.fecha_vencimiento < vencimiento:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(f"La membresía de {socio.persona.nombre_completo} vence el "
                    f"{membresia.fecha_vencimiento} y este abono se extendería hasta el "
                    f"{vencimiento}. Renovale la cuota primero."),
        )

    # --- REGLA 8: deudas ----------------------------------------------------
    # Corta cualquier COMPRA nueva. NO aplica al reservar con un abono ya
    # pagado: usar algo que ya se pagó no es comprar. Y tampoco puede aplicar
    # nunca a pagar una deuda — si pagar dependiera de no deber, nadie podría
    # regularizar jamás.
    deuda = (db.query(Deuda)
             .filter(Deuda.id_socio == socio.id_socio, Deuda.estado == "PENDIENTE")
             .first())
    if deuda is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(f"{socio.persona.nombre_completo} tiene una deuda pendiente. "
                    "Regularizala en recepción antes de comprar."),
        )

    precio = float(plan.precio)

    inscripcion = InscripcionActividad(
        id_socio=socio.id_socio,
        id_plan_actividad=plan.id_plan_actividad,
        id_membresia=membresia.id_membresia,
        precio_pactado=precio,
        fecha_inicio=hoy,
        fecha_vencimiento=vencimiento,
        clases_restantes=(plan.cantidad if plan.tipo_limite == "POR_MES" else None),
        estado="ACTIVA",
    )
    db.add(inscripcion)
    db.flush()

    pago = Pago(
        id_socio=socio.id_socio,
        id_inscripcion=inscripcion.id_inscripcion,
        id_sede=socio.id_sede,
        metodo=datos.metodo.value,
        monto=precio,
        fecha_pago=datetime.now(),
        periodo_desde=hoy,
        periodo_hasta=vencimiento,
        estado="CONFIRMADO",
    )
    db.add(pago)
    db.commit()
    db.refresh(inscripcion)
    db.refresh(pago)

    return ComprarPlanResponse(
        inscripcion=_a_inscripcion_out(inscripcion),
        pago=PagoOut(
            id_pago=pago.id_pago, id_socio=pago.id_socio,
            socio=socio.persona.nombre_completo, monto=float(pago.monto),
            metodo=pago.metodo, fecha_pago=pago.fecha_pago,
            periodo_desde=pago.periodo_desde, periodo_hasta=pago.periodo_hasta,
            estado=pago.estado, numero_comprobante=pago.numero_comprobante,
        ),
        mensaje=(f"{socio.persona.nombre_completo} compró {plan.nombre} por "
                 f"${precio:,.2f}. Vigente hasta el {vencimiento}."),
    )


@router.post("/inscripciones/{id_inscripcion}/cancelar", response_model=InscripcionOut)
def cancelar_inscripcion(
    id_inscripcion: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.COBRAR_PAGOS)),
):
    """
    Cancela un abono.

    Cancela también las reservas FUTURAS que se hicieron con él: si el abono
    ya no vale, las clases que habilitaba tampoco. Las pasadas no se tocan —
    el socio efectivamente fue a esas clases.

    El pago NO se anula automáticamente: devolver plata es una decisión aparte
    que se toma en la sección Cobros, y hacerla implícita acá sería reembolsar
    sin que nadie lo haya decidido.
    """
    inscripcion = db.get(InscripcionActividad, id_inscripcion)
    if inscripcion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="La inscripción no existe.")
    if inscripcion.estado == "CANCELADA":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Ese abono ya estaba cancelado.")

    inscripcion.estado = "CANCELADA"

    hoy = date.today()
    ahora = datetime.now()
    reservas = (db.query(Reserva)
                .join(Turno, Reserva.id_turno == Turno.id_turno)
                .filter(Reserva.id_inscripcion == id_inscripcion,
                        Reserva.estado == "RESERVADA",
                        Turno.fecha >= hoy)
                .all())
    for r in reservas:
        r.estado = "CANCELADA_GIMNASIO"
        r.fecha_cancelacion = ahora

    db.commit()
    db.refresh(inscripcion)
    return _a_inscripcion_out(inscripcion)


# =============================================================================
# CHEQUEO PREVIO Y CLASE SUELTA
# =============================================================================

@router.get("/socio/{id_socio}/puede-comprar", response_model=PuedeComprarOut)
def puede_comprar(
    id_socio: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.ACTIVIDADES)),
):
    """
    Si el socio está en condiciones de comprar un abono HOY, sin comprar nada.

    Existe porque la vista de Cobros necesita decidir ANTES de cobrar si
    ofrecer el combo "renovar cuota + comprar abono" en una sola
    confirmación. Sin esto, el flujo cobraba la membresía y recién después
    descubría que el abono no entraba — con la plata ya cobrada.

    Es la misma situación que en un gimnasio real pasa todo el tiempo: la
    cuota vence a mitad de mes y el abono siempre se cobra por mes completo.

    Reusa exactamente las mismas condiciones que `comprar_plan`, así el
    chequeo previo y la compra real no pueden desincronizarse.
    """
    socio = db.get(Socio, id_socio)
    if socio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="El socio no existe.")

    hoy = date.today()
    vencimiento_abono = _sumar_un_mes(hoy)

    membresia = (db.query(Membresia)
                 .filter(Membresia.id_socio == id_socio, Membresia.estado == "ACTIVA")
                 .order_by(Membresia.fecha_vencimiento.desc())
                 .first())

    tiene_deuda = (db.query(Deuda)
                   .filter(Deuda.id_socio == id_socio, Deuda.estado == "PENDIENTE")
                   .first()) is not None

    if membresia is None or (membresia.fecha_vencimiento and membresia.fecha_vencimiento < hoy):
        return PuedeComprarOut(
            puede=False, tiene_deuda=tiene_deuda,
            membresia_cubre=False,
            vencimiento_membresia=membresia.fecha_vencimiento if membresia else None,
            vencimiento_abono=vencimiento_abono,
            motivo="No tiene la cuota al día.",
        )

    cubre = (membresia.fecha_vencimiento is None
             or membresia.fecha_vencimiento >= vencimiento_abono)

    motivo = None
    if tiene_deuda:
        motivo = "Tiene una deuda pendiente. Regularizala antes de comprar."
    elif not cubre:
        motivo = (f"La cuota vence el {membresia.fecha_vencimiento} y el abono llegaría "
                  f"hasta el {vencimiento_abono}. Hay que renovar primero.")

    return PuedeComprarOut(
        puede=cubre and not tiene_deuda,
        tiene_deuda=tiene_deuda,
        membresia_cubre=cubre,
        vencimiento_membresia=membresia.fecha_vencimiento,
        vencimiento_abono=vencimiento_abono,
        motivo=motivo,
    )


@router.post("/turnos/{id_turno}/clase-suelta", response_model=ClaseSueltaResponse,
             status_code=status.HTTP_201_CREATED)
def comprar_clase_suelta(
    id_turno: int,
    datos: ComprarClaseSueltaRequest,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.COBRAR_PAGOS)),
):
    """
    Cobra y reserva una clase individual, sin abono.

    Compite por el MISMO cupo que las reservas hechas con plan: quien paga
    suelto no tiene prioridad ni lugar reservado aparte. Por eso el chequeo de
    cupo es idéntico al de `reservar`.

    Exige membresía activa —hay que ser socio para entrar al gimnasio— pero
    NO exige que la cuota cubra un mes: la clase es de hoy, se agota hoy. Es
    la diferencia con el abono, que se proyecta un mes hacia adelante.

    Sí aplica la regla de deudas: es una compra.
    """
    turno = db.get(Turno, id_turno)
    if turno is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="El turno no existe.")
    if turno.estado == "CANCELADO":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Esa clase está cancelada.")

    socio = db.get(Socio, datos.id_socio)
    if socio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="El socio no existe.")

    hoy = date.today()

    membresia = (db.query(Membresia)
                 .filter(Membresia.id_socio == socio.id_socio,
                         Membresia.estado == "ACTIVA")
                 .order_by(Membresia.fecha_vencimiento.desc())
                 .first())
    if membresia is None or (membresia.fecha_vencimiento and membresia.fecha_vencimiento < hoy):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(f"{socio.persona.nombre_completo} no tiene la cuota al día. "
                    "Hay que ser socio activo para tomar una clase."),
        )

    deuda = (db.query(Deuda)
             .filter(Deuda.id_socio == socio.id_socio, Deuda.estado == "PENDIENTE")
             .first())
    if deuda is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(f"{socio.persona.nombre_completo} tiene una deuda pendiente. "
                    "Regularizala en recepción antes de comprar."),
        )

    ya = next((r for r in turno.reservas
               if r.id_socio == socio.id_socio and r.estado == "RESERVADA"), None)
    if ya:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{socio.persona.nombre_completo} ya está anotado en esa clase.",
        )

    if _reservas_activas(turno) >= turno.cupo_maximo:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(f"La clase de {turno.actividad.nombre} del {turno.fecha} "
                    f"ya está completa ({turno.cupo_maximo} lugares)."),
        )

    precio = float(turno.actividad.precio_clase_suelta) if turno.actividad else 0.0

    pago = Pago(
        id_socio=socio.id_socio,
        id_sede=socio.id_sede,
        metodo=datos.metodo.value,
        monto=precio,
        fecha_pago=datetime.now(),
        periodo_desde=turno.fecha,
        periodo_hasta=turno.fecha,
        estado="CONFIRMADO",
    )
    db.add(pago)
    db.flush()

    reserva = Reserva(
        id_turno=turno.id_turno,
        id_socio=socio.id_socio,
        es_clase_suelta=True,
        id_pago=pago.id_pago,
        fecha_reserva=datetime.now(),
        estado="RESERVADA",
    )
    db.add(reserva)
    db.commit()
    db.refresh(reserva)
    db.refresh(pago)

    return ClaseSueltaResponse(
        reserva=ReservaOut(
            id_reserva=reserva.id_reserva,
            id_turno=turno.id_turno,
            id_socio=socio.id_socio,
            socio=socio.persona.nombre_completo,
            actividad=turno.actividad.nombre if turno.actividad else "?",
            fecha=turno.fecha,
            hora=turno.hora,
            estado=reserva.estado,
            es_clase_suelta=True,
            clases_restantes=None,
        ),
        pago=PagoOut(
            id_pago=pago.id_pago, id_socio=pago.id_socio,
            socio=socio.persona.nombre_completo, monto=float(pago.monto),
            metodo=pago.metodo, fecha_pago=pago.fecha_pago,
            periodo_desde=pago.periodo_desde, periodo_hasta=pago.periodo_hasta,
            estado=pago.estado, numero_comprobante=pago.numero_comprobante,
        ),
        mensaje=(f"{socio.persona.nombre_completo} compró una clase suelta de "
                 f"{turno.actividad.nombre if turno.actividad else '?'} por ${precio:,.2f}."),
    )
