"""
turnos.py
---------
La lógica de turnos que comparten el panel del recepcionista, el fichaje y el
portal del socio. Vive acá y no dentro de un router porque los tres tienen que
responder EXACTAMENTE lo mismo: si el panel dice que una reserva sigue viva y
el molinete dice que venció, el mostrador deja de confiar en la pantalla.

Dos decisiones de diseño que explican casi todo el archivo:

1. EL ESTADO DE ASISTENCIA NO SE GUARDA, SE DERIVA.

   `estado_reserva` tiene RESERVADA, EN_ESPERA y las dos cancelaciones. NO
   tiene 'ASISTIO' ni 'AUSENTE', y es deliberado:

       asistió  ->  hay una fila en Asistencia con id_reserva = esta reserva
       ausente  ->  ya pasó hora + tolerancia y no hay ninguna

   Guardarlos obligaría a un proceso que corra solo marcando ausentes. Ese
   proceso se cae, se atrasa o corre dos veces, y mientras tanto el panel
   muestra como pendiente un turno que venció hace una hora. Derivándolos no
   hay nada que pueda desincronizarse: si el reloj avanza, la respuesta
   cambia sola.

2. VENCER EL TURNO NO ES LO MISMO QUE NO DEJAR ENTRAR.

   Un socio con la cuota al día que llega tarde a Yoga pierde la clase, pero
   entra al gimnasio igual — su cuota se la paga. Si lo rechazáramos, haber
   reservado lo habría dejado PEOR que no haber reservado, que es exactamente
   al revés de lo que uno espera de un sistema de turnos.
"""

from datetime import date, datetime, time, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import Actividad, Asistencia, HorarioActividad, Reserva, Turno


# Cuántos días hacia adelante se generan turnos a partir de los horarios.
#
# Cuatro semanas es el equilibrio: suficiente para que un socio planifique el
# mes y para que nadie note que los turnos "se crean solos", y poco como para
# que cambiar un horario no obligue a limpiar medio año de turnos futuros.
DIAS_A_GENERAR = 28


# =============================================================================
# ESTADO DERIVADO DE UNA RESERVA
# =============================================================================

class EstadoAsistencia:
    """
    Lo que ve el mostrador. No es `estado_reserva` de la base: eso dice qué
    pidió el socio, esto dice cómo terminó.
    """
    PENDIENTE = "pendiente"      # todavía no llegó, y aún está a tiempo
    ASISTIO = "asistio"          # hay un ingreso registrado contra esta reserva
    AUSENTE = "ausente"          # se pasó la tolerancia y nunca llegó
    EN_ESPERA = "en_espera"      # anotado sin lugar
    CANCELADA = "cancelada"


def vence_a(turno: Turno, actividad: Actividad) -> datetime:
    """
    El instante exacto en que la reserva de ese turno deja de servir.

    Es hora del turno + la tolerancia de la actividad. La tolerancia vive en
    Actividad y no como constante porque a una clase de Yoga llegar 20 minutos
    tarde es no ir, y a la sala de musculación —abierta toda la tarde— casi no
    le aplica.
    """
    inicio = datetime.combine(turno.fecha, turno.hora)
    return inicio + timedelta(minutes=actividad.minutos_tolerancia or 0)


def estado_de_reserva(reserva: Reserva, turno: Turno, actividad: Actividad,
                       asistio: bool, ahora: datetime | None = None) -> str:
    """
    Cómo está esa reserva AHORA.

    `asistio` se pasa como parámetro en vez de consultarse acá adentro a
    propósito: el panel muestra decenas de reservas y resolverlo fila por fila
    sería una consulta por cada una. Quien llama trae el conjunto de una y esta
    función queda pura — sin base de datos, fácil de probar.
    """
    ahora = ahora or datetime.now()

    # El orden importa. Una cancelada sigue cancelada aunque la persona haya
    # entrado al gimnasio ese día por otro motivo, y un turno cancelado por el
    # gimnasio no convierte a nadie en ausente.
    if reserva.estado in ("CANCELADA_SOCIO", "CANCELADA_GIMNASIO"):
        return EstadoAsistencia.CANCELADA
    if turno.estado == "CANCELADO":
        return EstadoAsistencia.CANCELADA
    if reserva.estado == "EN_ESPERA":
        return EstadoAsistencia.EN_ESPERA
    if asistio:
        return EstadoAsistencia.ASISTIO
    if ahora > vence_a(turno, actividad):
        return EstadoAsistencia.AUSENTE
    return EstadoAsistencia.PENDIENTE


def reservas_con_asistencia(db: Session, id_turnos: list[int]) -> set[int]:
    """
    De qué reservas de esos turnos ya hay un ingreso registrado.

    Una sola consulta para todo el panel, en vez de una por fila. Devuelve un
    set de id_reserva para que el llamador pregunte con `in`.
    """
    if not id_turnos:
        return set()
    filas = (
        db.query(Asistencia.id_reserva)
        .join(Reserva, Reserva.id_reserva == Asistencia.id_reserva)
        .filter(Reserva.id_turno.in_(id_turnos),
                Asistencia.id_reserva.isnot(None))
        .all()
    )
    return {f[0] for f in filas}


# =============================================================================
# CUPO Y LISTA DE ESPERA
# =============================================================================

def ocupacion(db: Session, id_turno: int) -> int:
    """
    Cuántos lugares hay tomados.

    Cuenta SOLO las RESERVADA. Los EN_ESPERA no ocupan lugar —esa es la
    definición de estar en espera— y contarlos haría que el turno pareciera
    lleno cuando todavía entra gente, dejando la lista de espera trabada para
    siempre.
    """
    return (db.query(func.count(Reserva.id_reserva))
            .filter(Reserva.id_turno == id_turno,
                    Reserva.estado == "RESERVADA")
            .scalar()) or 0


def hay_lugar(db: Session, turno: Turno) -> bool:
    return ocupacion(db, turno.id_turno) < turno.cupo_maximo


def promover_de_lista_de_espera(db: Session, id_turno: int) -> Reserva | None:
    """
    Pasa a RESERVADA al primero que esté esperando, si quedó lugar.

    Se llama cada vez que una reserva deja de ocupar lugar (una cancelación).
    Sin esto, el lugar liberado queda vacío salvo que otro socio entre justo a
    mirar — que era exactamente el trabajo manual que el sistema tiene que
    evitarle al recepcionista.

    El criterio de orden es `fecha_reserva`: el que se anotó primero entra
    primero. No hay prioridades ni excepciones, y eso es una ventaja — nadie
    tiene que justificar por qué eligió a uno.

    NO hace commit: quien llama ya está dentro de una transacción (la
    cancelación) y las dos cosas tienen que pasar juntas o ninguna. Si esto
    commiteara por su cuenta y después fallara la cancelación, alguien
    quedaría promovido a un lugar que nunca se liberó.
    """
    # OJO: el flush explícito NO es decorativo.
    #
    # La sesión de este proyecto se crea con autoflush=False (ver
    # database.py), así que los cambios que hizo quien llama —típicamente
    # `reserva.estado = 'CANCELADA_SOCIO'`— todavía no llegaron a la base
    # cuando acá se cuenta la ocupación. Sin este flush, `ocupacion` sigue
    # contando como ocupado el lugar que se acaba de liberar, concluye que el
    # turno está lleno, y no promueve a nadie: la lista de espera nunca
    # avanza. Se descubrió probándolo contra la base, no leyendo el código.
    db.flush()

    # Mismo lock que el endpoint de reservar, y por el mismo motivo: dos
    # cancelaciones simultáneas sobre el mismo turno liberarían un lugar cada
    # una, y sin lock las dos promoverían contando el mismo hueco. Con el
    # lock, la segunda espera y ve el estado real.
    turno = (db.query(Turno)
             .filter(Turno.id_turno == id_turno)
             .with_for_update()
             .first())
    if turno is None or turno.estado == "CANCELADO":
        return None
    if not hay_lugar(db, turno):
        return None

    siguiente = (db.query(Reserva)
                 .filter(Reserva.id_turno == id_turno,
                         Reserva.estado == "EN_ESPERA")
                 .order_by(Reserva.fecha_reserva)
                 .first())
    if siguiente is None:
        return None

    siguiente.estado = "RESERVADA"
    db.flush()
    return siguiente


# =============================================================================
# QUÉ TURNO LE CORRESPONDE A QUIEN ACABA DE FICHAR
# =============================================================================

def reserva_a_acreditar(db: Session, id_socio: int,
                         ahora: datetime | None = None) -> tuple[Reserva | None, str | None]:
    """
    Busca a qué turno acreditarle el ingreso que se está registrando.

    Devuelve (reserva, aviso):
      - (reserva, None)    -> llegó a tiempo, se le acredita la clase
      - (None, "texto")    -> tenía una reserva pero se le pasó la hora
      - (None, None)       -> no tenía nada reservado para ahora

    Que esto sea automático es el punto de todo el rediseño: el recepcionista
    no tiene que buscar a la persona, ni la clase, ni tildar nada. Pasa la
    tarjeta y el sistema decide.

    La ventana hacia atrás es la tolerancia de la actividad; hacia adelante se
    aceptan hasta 2 horas antes, porque la gente llega temprano y no tendría
    sentido no acreditarle la clase a quien vino 20 minutos antes.
    """
    ahora = ahora or datetime.now()
    hoy = ahora.date()

    candidatas = (
        db.query(Reserva, Turno, Actividad)
        .join(Turno, Turno.id_turno == Reserva.id_turno)
        .join(Actividad, Actividad.id_actividad == Turno.id_actividad)
        .filter(Reserva.id_socio == id_socio,
                Reserva.estado == "RESERVADA",
                Turno.estado == "HABILITADO",
                # De hoy y de ayer: un turno de las 23:30 con tolerancia sigue
                # vivo pasada la medianoche, y filtrar sólo por hoy lo perdería.
                Turno.fecha.in_([hoy, hoy - timedelta(days=1)]))
        .all()
    )
    if not candidatas:
        return None, None

    # Ya acreditadas: si alguien pasa la tarjeta dos veces no se le puede
    # acreditar la misma clase de nuevo, ni saltar a la siguiente del día.
    ya = reservas_con_asistencia(db, [t.id_turno for _, t, _ in candidatas])

    a_tiempo = []
    vencidas = []
    for reserva, turno, actividad in candidatas:
        if reserva.id_reserva in ya:
            continue
        inicio = datetime.combine(turno.fecha, turno.hora)
        if inicio - timedelta(hours=2) <= ahora <= vence_a(turno, actividad):
            a_tiempo.append((reserva, turno, actividad, inicio))
        elif ahora > vence_a(turno, actividad):
            vencidas.append((reserva, turno, actividad, inicio))

    if a_tiempo:
        # La más cercana a empezar. Si alguien tiene dos clases seguidas y
        # llega entre las dos, se le acredita la que está por empezar.
        a_tiempo.sort(key=lambda x: abs((x[3] - ahora).total_seconds()))
        return a_tiempo[0][0], None

    if vencidas:
        # Se avisa por la más reciente: es la que la persona vino a hacer.
        vencidas.sort(key=lambda x: x[3], reverse=True)
        _, turno, actividad, inicio = vencidas[0]
        return None, (f"Perdiste {actividad.nombre} de las "
                      f"{inicio.strftime('%H:%M')}: la tolerancia era de "
                      f"{actividad.minutos_tolerancia} minutos.")

    return None, None


# =============================================================================
# GENERACIÓN DE TURNOS A PARTIR DE LOS HORARIOS
# =============================================================================

def generar_turnos(db: Session, dias: int = DIAS_A_GENERAR,
                    desde: date | None = None) -> dict:
    """
    Crea los turnos que falten para las próximas semanas, según los horarios.

    Es IDEMPOTENTE y esa es su propiedad más importante: se puede correr todos
    los días, o diez veces seguidas, y el resultado es el mismo. Eso permite
    llamarla sin miedo desde el arranque del backend y desde un botón, sin
    coordinar quién la corrió y cuándo.

    Lo que la hace idempotente es el índice único de Turno
    (id_sede, id_actividad, fecha, hora): si el turno ya está, no se inserta.
    Se consulta primero en vez de confiar en el error de la base porque un
    IntegrityError aborta la transacción entera y se perderían los turnos
    buenos generados antes en la misma pasada.

    NO toca los turnos cargados a mano (id_horario_actividad NULL) ni los
    cancelados: si alguien canceló el turno del lunes por feriado, volver a
    crearlo sería deshacer una decisión humana con un proceso automático.
    """
    desde = desde or date.today()
    hasta = desde + timedelta(days=dias)

    horarios = (db.query(HorarioActividad)
                .filter(HorarioActividad.activo.is_(True))
                .all())
    if not horarios:
        return {"creados": 0, "horarios": 0, "desde": desde, "hasta": hasta}

    # Todo lo que ya existe en la ventana, de una. Con un turno por día por
    # actividad esto es chico, y evita una consulta por fecha candidata.
    existentes = {
        (t.id_sede, t.id_actividad, t.fecha, t.hora)
        for t in db.query(Turno).filter(Turno.fecha >= desde, Turno.fecha <= hasta).all()
    }

    creados = 0
    for horario in horarios:
        dia = desde
        while dia <= hasta:
            # isoweekday(): 1 = lunes ... 7 = domingo. Es exactamente el mismo
            # criterio que guarda dia_semana, así que no hay conversión.
            if dia.isoweekday() != horario.dia_semana:
                dia += timedelta(days=1)
                continue
            if dia < horario.vigente_desde:
                dia += timedelta(days=1)
                continue
            if horario.vigente_hasta and dia > horario.vigente_hasta:
                break

            clave = (horario.id_sede, horario.id_actividad, dia, horario.hora)
            if clave not in existentes:
                db.add(Turno(
                    id_sede=horario.id_sede,
                    id_actividad=horario.id_actividad,
                    fecha=dia,
                    hora=horario.hora,
                    cupo_maximo=horario.cupo,
                    estado="HABILITADO",
                    id_profesor=horario.id_profesor,
                    id_entrenador_a_cargo=horario.id_entrenador_a_cargo,
                    id_horario_actividad=horario.id_horario_actividad,
                ))
                existentes.add(clave)
                creados += 1

            dia += timedelta(days=1)

    if creados:
        db.commit()

    return {"creados": creados, "horarios": len(horarios),
            "desde": desde, "hasta": hasta}
