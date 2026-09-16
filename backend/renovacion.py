"""
renovacion.py
-------------
Cuándo se puede cobrar una cuota. Regla del dueño (2026-09-16): NO SE COBRAN
PERÍODOS POR ADELANTADO.

POR QUÉ
=======
El motivo es de plata, no técnico: quien paga ocho meses por adelantado se
queda con el precio de hoy, y si la cuota aumenta en el medio el gimnasio
cobra esos meses a precio viejo. Con el adelanto permitido, lo único que
separaba al socio de congelar su precio era tener la plata junta.

Hubo además un bug que salía del mismo lugar: al renovar con la cuota vigente,
el cobro marcaba VENCIDA la membresía que estaba corriendo y creaba la próxima
ACTIVA con inicio futuro. "Mi cuota" mostraba el plan y las fechas del período
que todavía no había empezado, y con una cuota congelada se creaban períodos
superpuestos. Sin adelantos, la membresía nueva siempre arranca HOY y ese
camino desaparece entero.

LA REGLA
========
Se puede cobrar una cuota sólo si el socio NO tiene un período en curso:
  - sin membresías, o con la última ya vencida  -> se puede;
  - con una ACTIVA que vence hoy o más adelante  -> no (se renueva desde el día
    siguiente al vencimiento);
  - con una SUSPENDIDA (en pausa)                -> no (primero se reanuda).

La usan los tres caminos que cobran una cuota (mostrador, pago online y su
acreditación) y las pantallas, que la reciben ya resuelta para no ofrecer un
botón que el backend va a rechazar. `Pago.es_adelanto` queda en el esquema,
siempre en false.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session

from models import Membresia


@dataclass
class EstadoRenovacion:
    puede: bool
    # Por qué no se puede, listo para mostrar. None si se puede.
    motivo: str | None = None
    # Desde qué día se va a poder (None si ya se puede o si depende de reanudar).
    desde: date | None = None


def _fecha(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def estado_renovacion(db: Session, id_socio: int) -> EstadoRenovacion:
    hoy = date.today()

    # Con la baja programada no se renueva: sería cobrar un período que el
    # socio ya dijo que no va a usar. Si cambió de idea, primero la anula.
    from bajas import baja_pendiente
    pendiente = baja_pendiente(db, id_socio)
    if pendiente is not None:
        return EstadoRenovacion(
            puede=False,
            motivo=(f"Tiene la baja programada para el {_fecha(pendiente.fecha_baja)}. "
                    "Para renovar, primero hay que anularla."),
        )

    en_pausa = (db.query(Membresia)
                .filter(Membresia.id_socio == id_socio,
                        Membresia.estado == "SUSPENDIDA")
                .first())
    if en_pausa is not None:
        return EstadoRenovacion(
            puede=False,
            motivo=("La cuota está en pausa. Primero hay que reanudarla; la "
                    "renovación se cobra cuando venza."),
        )

    vigente = (db.query(Membresia)
               .filter(Membresia.id_socio == id_socio,
                       Membresia.estado == "ACTIVA")
               .order_by(Membresia.fecha_vencimiento.desc().nullsfirst())
               .first())
    if vigente is None:
        return EstadoRenovacion(puede=True)

    if vigente.fecha_vencimiento is None:
        return EstadoRenovacion(
            puede=False,
            motivo="Tiene una membresía que no vence: no hay nada que renovar.",
        )

    if vigente.fecha_vencimiento >= hoy:
        desde = vigente.fecha_vencimiento + timedelta(days=1)
        return EstadoRenovacion(
            puede=False,
            desde=desde,
            motivo=(f"La cuota está paga hasta el {_fecha(vigente.fecha_vencimiento)}. "
                    f"Se puede renovar desde el {_fecha(desde)}: no se cobran "
                    "períodos por adelantado."),
        )

    return EstadoRenovacion(puede=True)
