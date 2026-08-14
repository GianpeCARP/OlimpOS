"""
routers/recepcion.py
--------------------
El panel del mostrador: próximos turnos y búsqueda por DNI.

POR QUÉ ES UN ROUTER APARTE Y NO PARTE DE /actividades O /asistencia:

Los endpoints de esos dos routers están organizados por ENTIDAD (esto es un
turno, esto es una asistencia), que es lo correcto para una API. Este router
está organizado por PANTALLA: devuelve, en un solo pedido, todo lo que el
recepcionista necesita ver al mismo tiempo.

Esa diferencia importa porque el panel se refresca solo cada pocos segundos.
Armarlo con los endpoints por entidad serían cuatro o cinco pedidos por
refresco, cada uno con su latencia, y —peor— con la posibilidad de que la
lista de turnos llegue de un instante y la de asistencias de otro, mostrando
a alguien como ausente en un turno que ya se le acreditó.

La regla que guía todo lo de acá: el recepcionista no debería tener que
BUSCAR nada. La información llega ordenada por urgencia, con la acción al
lado, y las advertencias (cuota vencida, deuda) ya resueltas del lado del
servidor para que no tenga que abrir otra pantalla a confirmarlas.
"""

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Actividad, Asistencia, Deuda, Membresia, Persona, Reserva, Socio, Turno,
)
from permisos import Acceso, Seccion
from schemas import (
    InscriptoEnTurno, PanelRecepcion, ResultadoBusqueda, TurnoDePanel,
)
from security import Sesion, requiere_seccion
from turnos import (
    EstadoAsistencia, estado_de_reserva, reservas_con_asistencia, vence_a,
)

router = APIRouter(prefix="/recepcion", tags=["Recepción"])


# Ventana del panel. Se muestran los turnos que empiezan dentro de las
# próximas HORAS_ADELANTE horas: más que eso llena la pantalla de cosas que no
# van a pasar en este rato, y el mostrador deja de mirarla.
HORAS_ADELANTE = 6

# Cuánto rato sigue apareciendo un turno ya vencido en la solapa de vencidos.
# Existe para que el mostrador pueda explicar por qué alguien reclama una
# clase que ya no figura arriba, no para poder marcarla: eso ya no se puede.
MINUTOS_MOSTRAR_VENCIDOS = 60

# A partir de este cupo, y sin profesor, un turno se considera "sala abierta"
# y el panel lo colapsa en una línea con el contador en vez de listar a todos.
#
# El umbral es por cupo y no por un flag en la tabla a propósito: no hace
# falta que nadie marque nada, y una clase de 15 nunca se confunde con la sala
# de 40. Si algún día hace falta distinguirlo con precisión, se agrega la
# columna; hoy sería configuración que nadie va a tocar.
CUPO_SALA_ABIERTA = 25


# =============================================================================
# AYUDANTES
# =============================================================================

def _alerta_de_socio(db: Session, socio: Socio) -> str | None:
    """
    Lo que el mostrador tiene que decirle a esta persona cuando aparezca.

    Se resuelve del lado del servidor porque implica mirar membresía y deudas:
    hacerlo por fila en el cliente serían dos consultas por cada persona
    anotada en el turno.
    """
    if not socio.activo:
        return "Socio dado de baja."

    membresia = (db.query(Membresia)
                 .filter(Membresia.id_socio == socio.id_socio,
                         Membresia.estado == "ACTIVA")
                 .order_by(Membresia.fecha_vencimiento.desc())
                 .first())

    if membresia is None:
        return "Sin membresía activa."

    if membresia.fecha_vencimiento and membresia.fecha_vencimiento < date.today():
        dias = (date.today() - membresia.fecha_vencimiento).days
        return f"Cuota vencida hace {dias} día(s)."

    deuda = (db.query(func.coalesce(func.sum(Deuda.monto), 0))
             .filter(Deuda.id_socio == socio.id_socio,
                     Deuda.estado == "PENDIENTE")
             .scalar()) or 0
    if deuda > 0:
        return f"Debe ${deuda:,.0f}."

    # Aviso temprano: es el único momento en que se tiene la atención de la
    # persona, y avisarle tres días antes evita el corte en seco del día que
    # vence. Cobrarlo acá es un click; perseguirlo después, una llamada.
    if membresia.fecha_vencimiento:
        faltan = (membresia.fecha_vencimiento - date.today()).days
        if faltan <= 3:
            return f"La cuota le vence en {faltan} día(s)."

    return None


def _a_turno_de_panel(db: Session, turno: Turno, actividad: Actividad,
                       ahora: datetime, con_inscriptos: bool) -> TurnoDePanel:
    inicio = datetime.combine(turno.fecha, turno.hora)
    reservas = (db.query(Reserva)
                .filter(Reserva.id_turno == turno.id_turno)
                .order_by(Reserva.fecha_reserva)
                .all())

    acreditadas = reservas_con_asistencia(db, [turno.id_turno])

    ocupados = sum(1 for r in reservas if r.estado == "RESERVADA")
    en_espera = sum(1 for r in reservas if r.estado == "EN_ESPERA")

    es_sala = turno.id_profesor is None and turno.cupo_maximo >= CUPO_SALA_ABIERTA

    inscriptos: list[InscriptoEnTurno] = []
    # La sala abierta se colapsa: 40 nombres taparían las clases de 15, que
    # son donde el cupo importa de verdad. Los contadores igual se calculan,
    # así la línea muestra "Musculación 18:00 — 23 anotados" y se puede
    # expandir pidiendo ese turno puntual.
    if con_inscriptos and not es_sala:
        for r in reservas:
            if r.estado in ("CANCELADA_SOCIO", "CANCELADA_GIMNASIO"):
                continue
            socio = r.socio
            inscriptos.append(InscriptoEnTurno(
                id_reserva=r.id_reserva,
                id_socio=r.id_socio,
                nombre=socio.persona.nombre_completo,
                dni=socio.persona.dni,
                estado=estado_de_reserva(
                    r, turno, actividad, r.id_reserva in acreditadas, ahora),
                es_clase_suelta=bool(r.es_clase_suelta),
                alerta=_alerta_de_socio(db, socio),
            ))
        # Los que faltan llegar primero: son sobre los que el mostrador puede
        # hacer algo. Los que ya asistieron y los ausentes van al final.
        orden = {EstadoAsistencia.PENDIENTE: 0, EstadoAsistencia.EN_ESPERA: 1,
                 EstadoAsistencia.ASISTIO: 2, EstadoAsistencia.AUSENTE: 3}
        inscriptos.sort(key=lambda i: (orden.get(i.estado, 9), i.nombre))

    return TurnoDePanel(
        id_turno=turno.id_turno,
        actividad=actividad.nombre,
        fecha=turno.fecha,
        hora=turno.hora,
        minutos_para_empezar=int((inicio - ahora).total_seconds() // 60),
        vence_a=vence_a(turno, actividad),
        cupo_maximo=turno.cupo_maximo,
        ocupados=ocupados,
        en_espera=en_espera,
        profesor=(turno.profesor.empleado.persona.nombre_completo
                  if turno.profesor else None),
        estado_turno=turno.estado,
        es_sala_abierta=es_sala,
        inscriptos=inscriptos,
    )


# =============================================================================
# EL PANEL
# =============================================================================

@router.get("/panel", response_model=PanelRecepcion)
def panel(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.ASISTENCIA)),
):
    """
    Los próximos turnos, del más cercano al más lejano.

    Es lo primero que ve el recepcionista al entrar y lo único que necesita
    mirar durante el día: quién está por llegar, quién ya llegó, y a quién hay
    que decirle algo cuando aparezca.

    Los turnos ya vencidos NO van en la lista principal: van en
    `vencidos_recientes`, que existe sólo para poder explicar el reclamo de
    alguien que llegó tarde. Desde ahí no se puede marcar a nadie — el turno
    venció y ya está.
    """
    ahora = datetime.now()
    hoy = ahora.date()

    # Se traen los de hoy y ayer: un turno de las 23:30 con tolerancia sigue
    # vivo pasada la medianoche, y filtrar sólo por hoy lo perdería justo en
    # el momento en que el mostrador más lo necesita.
    filas = (
        db.query(Turno, Actividad)
        .join(Actividad, Actividad.id_actividad == Turno.id_actividad)
        .filter(Turno.fecha.in_([hoy, hoy - timedelta(days=1)]),
                Turno.estado == "HABILITADO")
        .order_by(Turno.fecha, Turno.hora)
        .all()
    )

    proximos: list[TurnoDePanel] = []
    vencidos: list[TurnoDePanel] = []

    for turno, actividad in filas:
        inicio = datetime.combine(turno.fecha, turno.hora)
        limite = vence_a(turno, actividad)

        if ahora <= limite:
            # Todavía se puede llegar. Sólo si empieza dentro de la ventana:
            # más allá llena la pantalla de cosas que no van a pasar en este
            # rato y el mostrador deja de mirarla.
            if inicio <= ahora + timedelta(hours=HORAS_ADELANTE):
                proximos.append(_a_turno_de_panel(db, turno, actividad, ahora, True))
        elif ahora <= limite + timedelta(minutes=MINUTOS_MOSTRAR_VENCIDOS):
            vencidos.append(_a_turno_de_panel(db, turno, actividad, ahora, True))

    proximos.sort(key=lambda t: t.minutos_para_empezar)
    vencidos.sort(key=lambda t: t.minutos_para_empezar, reverse=True)

    # Los totales del día miran SÓLO hoy, aunque arriba se hayan traído los de
    # ayer: son el resumen de la jornada, y sumarle la cola de anoche haría
    # que el número no cierre con lo que el mostrador vio pasar.
    inicio_dia = datetime.combine(hoy, datetime.min.time())
    anotados = (db.query(func.count(Reserva.id_reserva))
                .join(Turno, Turno.id_turno == Reserva.id_turno)
                .filter(Turno.fecha == hoy, Reserva.estado == "RESERVADA")
                .scalar()) or 0
    presentes = (db.query(func.count(Asistencia.id_asistencia))
                 .filter(Asistencia.fecha_hora_ingreso >= inicio_dia)
                 .scalar()) or 0

    return PanelRecepcion(
        ahora=ahora,
        turnos=proximos,
        vencidos_recientes=vencidos,
        total_anotados_hoy=anotados,
        total_presentes_hoy=presentes,
    )


@router.get("/turnos/{id_turno}", response_model=TurnoDePanel)
def detalle_de_turno(
    id_turno: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.ASISTENCIA)),
):
    """
    Un turno con toda su lista, incluida la sala abierta.

    Es lo que se pide al expandir la línea colapsada del panel: ahí sí se
    quieren ver los 40 nombres, porque el recepcionista fue a buscar a alguien
    puntual.
    """
    fila = (db.query(Turno, Actividad)
            .join(Actividad, Actividad.id_actividad == Turno.id_actividad)
            .filter(Turno.id_turno == id_turno)
            .first())
    if fila is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="El turno no existe.")
    turno, actividad = fila
    ahora = datetime.now()

    panel_turno = _a_turno_de_panel(db, turno, actividad, ahora, True)
    # La regla de colapso de sala abierta no aplica acá: se pidió este turno
    # explícitamente, o sea que alguien quiere ver la lista completa.
    if panel_turno.es_sala_abierta:
        panel_turno.inscriptos = _inscriptos_de(db, turno, actividad, ahora)
    return panel_turno


def _inscriptos_de(db: Session, turno: Turno, actividad: Actividad,
                    ahora: datetime) -> list[InscriptoEnTurno]:
    """La lista completa de un turno, sin la regla de colapso de sala abierta."""
    reservas = (db.query(Reserva)
                .filter(Reserva.id_turno == turno.id_turno)
                .order_by(Reserva.fecha_reserva)
                .all())
    acreditadas = reservas_con_asistencia(db, [turno.id_turno])
    salida = []
    for r in reservas:
        if r.estado in ("CANCELADA_SOCIO", "CANCELADA_GIMNASIO"):
            continue
        salida.append(InscriptoEnTurno(
            id_reserva=r.id_reserva,
            id_socio=r.id_socio,
            nombre=r.socio.persona.nombre_completo,
            dni=r.socio.persona.dni,
            estado=estado_de_reserva(
                r, turno, actividad, r.id_reserva in acreditadas, ahora),
            es_clase_suelta=bool(r.es_clase_suelta),
            alerta=_alerta_de_socio(db, r.socio),
        ))
    return salida


# =============================================================================
# BÚSQUEDA POR DNI
# =============================================================================

@router.get("/buscar", response_model=list[ResultadoBusqueda])
def buscar(
    dni: str = Query(min_length=2, description="DNI o parte de él"),
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.ASISTENCIA)),
):
    """
    Busca socios por DNI.

    Por DNI y no por nombre porque en el mostrador la persona TIENE el
    documento en la mano: se tipea sin ambigüedad, no tiene acentos, y no hay
    dos socios con el mismo. Buscar "gonzalez" devuelve cuatro personas y
    obliga a preguntar cuál; buscar el DNI devuelve una.

    Se aceptan coincidencias parciales para poder tipear los últimos dígitos,
    que es como la gente los dicta.

    Devuelve de una todo lo que el recepcionista iba a preguntar después: si
    está al día, cuánto debe, y cuál es su próximo turno. Una sola búsqueda
    cierra la conversación en vez de abrir tres pantallas más.
    """
    patron = f"%{dni.strip()}%"
    socios = (db.query(Socio)
              .join(Persona, Persona.id_persona == Socio.id_persona)
              .filter(Persona.dni.like(patron))
              .order_by(Persona.apellido, Persona.nombre)
              .limit(10)
              .all())

    ahora = datetime.now()
    salida: list[ResultadoBusqueda] = []

    for socio in socios:
        membresia = (db.query(Membresia)
                     .filter(Membresia.id_socio == socio.id_socio,
                             Membresia.estado == "ACTIVA")
                     .order_by(Membresia.fecha_vencimiento.desc())
                     .first())

        if membresia is None:
            estado = "Sin membresía"
        elif membresia.fecha_vencimiento and membresia.fecha_vencimiento < date.today():
            estado = "Vencida"
        else:
            estado = "Activa"

        deuda = (db.query(func.coalesce(func.sum(Deuda.monto), 0))
                 .filter(Deuda.id_socio == socio.id_socio,
                         Deuda.estado == "PENDIENTE")
                 .scalar()) or 0

        # Su próximo turno, para poder decirle "tenés Yoga a las 19" sin que
        # el recepcionista abra la agenda.
        proximo = None
        fila = (db.query(Turno, Actividad)
                .join(Actividad, Actividad.id_actividad == Turno.id_actividad)
                .join(Reserva, Reserva.id_turno == Turno.id_turno)
                .filter(Reserva.id_socio == socio.id_socio,
                        Reserva.estado == "RESERVADA",
                        Turno.estado == "HABILITADO",
                        Turno.fecha >= ahora.date())
                .order_by(Turno.fecha, Turno.hora)
                .first())
        if fila:
            proximo = _a_turno_de_panel(db, fila[0], fila[1], ahora, False)

        salida.append(ResultadoBusqueda(
            id_socio=socio.id_socio,
            nombre=socio.persona.nombre_completo,
            dni=socio.persona.dni,
            numero_socio=socio.numero_socio,
            tiene_rfid=bool(socio.codigo_rfid),
            activo=bool(socio.activo),
            estado_membresia=estado,
            vencimiento=membresia.fecha_vencimiento if membresia else None,
            deuda_total=float(deuda),
            proximo_turno=proximo,
            alerta=_alerta_de_socio(db, socio),
        ))

    return salida
