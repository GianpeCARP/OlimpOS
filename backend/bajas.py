"""
bajas.py
--------
Dar de baja a un socio SIN quitarle los días que ya pagó. Decisión del dueño
(2026-09-16).

POR QUÉ
=======
Antes la baja era inmediata: la ficha pasaba a inactiva y la membresía vigente
se CANCELABA en el acto. Quien avisaba el día 5 de un mes pago perdía los 25
días restantes, sin devolución. Y como el sistema no renueva solo (cada período
se cobra a mano o con un checkout de pago único), avisar la baja no tenía
ningún beneficio para el socio: le convenía más no decir nada y dejar vencer.

LA REGLA
========
Si el socio tiene un período pago en curso, la baja queda PROGRAMADA para el
día siguiente al vencimiento: una fila de Baja con `pendiente = true` y esa
fecha. Hasta entonces sigue activo y entrenando normalmente. Sin período en
curso, la baja es inmediata, como siempre.

Una pausa (congelamiento) en curso se cierra al pedir la baja con la misma
cuenta que al reanudar: se suman al vencimiento los días que estuvo en pausa y
la baja se programa para después de ese vencimiento.

Mientras esté pendiente, la baja se puede ANULAR (el socio cambió de idea): la
fila se borra, porque una baja que nunca ocurrió no es historial de nada. Y no
se puede renovar la cuota con una baja pendiente (ver renovacion.py): primero se
anula.

CUÁNDO SE APLICA
================
No hay cron. Se aplica sola, con el mismo criterio que el cierre de una pausa
vencida (_congelamiento_vigente en portal.py): al arrancar el backend, una vez
por día desde el latido, y al leer socios (listado del personal y portal del
socio). `aplicar_bajas_vencidas` es idempotente y barata: una consulta.

Al aplicarse: la ficha pasa a inactiva, se cancelan las reservas futuras y, si
la baja NO es voluntaria (mora o administrativa), se desactiva la cuenta de
acceso — la voluntaria deja la cuenta viva para que el socio pueda volver a
entrar a ver su historial, igual que la baja inmediata desde la app.
"""

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from models import Baja, Congelamiento, Membresia, Reserva, Socio, Turno


def baja_pendiente(db: Session, id_socio: int) -> Baja | None:
    return (db.query(Baja)
            .filter(Baja.id_socio == id_socio, Baja.pendiente.is_(True))
            .order_by(Baja.fecha_baja.desc())
            .first())


def pendientes_por_socio(db: Session, ids_socio: list[int]) -> dict[int, date]:
    """Fecha de la baja programada de cada socio, en UNA consulta (listados)."""
    if not ids_socio:
        return {}
    filas = (db.query(Baja.id_socio, Baja.fecha_baja)
             .filter(Baja.id_socio.in_(ids_socio), Baja.pendiente.is_(True))
             .all())
    return {id_socio: fecha for id_socio, fecha in filas}


def _cerrar_pausa(db: Session, id_socio: int) -> None:
    """Cierra una pausa en curso sumando los días usados (como reanudar)."""
    pausa = (db.query(Congelamiento)
             .join(Membresia, Congelamiento.id_membresia == Membresia.id_membresia)
             .filter(Membresia.id_socio == id_socio, Congelamiento.estado == "ACTIVO")
             .first())
    if pausa is None:
        return
    from routers.portal import _reanudar
    _reanudar(db, pausa, hasta=min(date.today(), pausa.fecha_fin))
    db.flush()


def fecha_de_baja(db: Session, id_socio: int) -> date:
    """
    Desde qué día corre la baja: el siguiente al vencimiento si hay un período
    pago en curso, hoy si no. Cierra la pausa en curso antes de calcularlo.
    """
    _cerrar_pausa(db, id_socio)
    hoy = date.today()
    vigente = (db.query(Membresia)
               .filter(Membresia.id_socio == id_socio,
                       Membresia.estado == "ACTIVA",
                       Membresia.fecha_vencimiento >= hoy)
               .order_by(Membresia.fecha_vencimiento.desc())
               .first())
    return vigente.fecha_vencimiento + timedelta(days=1) if vigente else hoy


def aplicar_baja(db: Session, socio: Socio, desactivar_cuenta: bool) -> list[int]:
    """
    Deja al socio de baja HOY. Devuelve los turnos donde se liberó un lugar,
    para que quien llama promueva la lista de espera. No hace commit.
    """
    hoy = date.today()
    socio.activo = False

    for m in (db.query(Membresia)
              .filter(Membresia.id_socio == socio.id_socio,
                      Membresia.estado.in_(["ACTIVA", "SUSPENDIDA"]))
              .all()):
        m.estado = "CANCELADA"

    turnos_liberados = []
    for r in (db.query(Reserva)
              .join(Turno, Turno.id_turno == Reserva.id_turno)
              .filter(Reserva.id_socio == socio.id_socio,
                      Reserva.estado.in_(["RESERVADA", "EN_ESPERA"]),
                      Turno.fecha >= hoy)
              .all()):
        if r.estado == "RESERVADA":
            turnos_liberados.append(r.id_turno)
        r.estado = "CANCELADA_SOCIO"
        r.fecha_cancelacion = datetime.now()

    if desactivar_cuenta and socio.persona and socio.persona.usuario is not None:
        socio.persona.usuario.activo = False
    return turnos_liberados


def aplicar_bajas_vencidas(db: Session) -> int:
    """Aplica las bajas programadas cuya fecha ya llegó. Hace commit si aplicó alguna."""
    vencidas = (db.query(Baja)
                .filter(Baja.pendiente.is_(True), Baja.fecha_baja <= date.today())
                .all())
    if not vencidas:
        return 0

    from turnos import promover_de_lista_de_espera
    liberados = []
    for baja in vencidas:
        socio = db.get(Socio, baja.id_socio)
        baja.pendiente = False
        if socio is not None and socio.activo:
            liberados += aplicar_baja(db, socio,
                                      desactivar_cuenta=baja.tipo != "VOLUNTARIA")
    db.flush()
    for id_turno in liberados:
        promover_de_lista_de_espera(db, id_turno)
    db.commit()
    return len(vencidas)
