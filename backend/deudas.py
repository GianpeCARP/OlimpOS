"""
deudas.py
---------
Genera las deudas de las cuotas vencidas.

POR QUÉ EXISTE ESTE ARCHIVO
===========================
La tabla Deuda estaba, el panel del mostrador mostraba "Debe $X", /mi-cuota
devolvía `deuda_total`, había un endpoint para pagarla y hasta un permiso
`gestionDeudas`... y NADIE creaba nunca una. Todo ese lado del sistema era
decorativo: el contador daba cero siempre, y el gimnasio no tenía forma de
saber quién le debía.

Se descubrió barriendo qué modelos usa cada router: `Deuda(` no aparecía en
ninguno.


POR QUÉ SE GENERA Y NO SE DERIVA
================================
En este proyecto varias cosas se derivan en vez de guardarse —el estado de
una reserva, si un socio asistió— y funciona bien: si el reloj avanza, la
respuesta cambia sola y no hay nada que pueda desincronizarse.

Una deuda NO puede funcionar así, y la diferencia importa:

  - Es un HECHO CONTABLE con fecha propia. "Se generó el 1 de marzo" no se
    puede recalcular después; si el precio del plan cambia en abril, la
    deuda de marzo sigue siendo por el precio de marzo.
  - Se salda con un pago concreto (`id_pago_cancelatorio`), y ese vínculo
    tiene que existir en algún lado.
  - Alguien la puede CONDONAR. Una deuda derivada volvería a aparecer al
    día siguiente, porque la condonación no tendría dónde guardarse.

Así que se generan filas. Lo que sí se toma prestado del otro patrón es la
IDEMPOTENCIA: correr esto dos veces no duplica nada, así que puede correr en
cada arranque sin coordinación — igual que la generación de turnos.


CUÁNDO SE GENERA UNA
====================
Cuando una membresía venció y nadie la renovó. No apenas vence: hay un
período de gracia, porque el socio que paga el día 3 no le debe nada a nadie
—simplemente pagó tarde— y generarle una deuda el día 1 para borrarla el 3
llena el historial de ruido.
"""

from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import Deuda, Membresia, Socio, TipoMembresia


# Días después del vencimiento antes de considerar que hay deuda.
#
# Tres es corto a propósito: más largo y el gimnasio se entera tarde de que
# alguien dejó de pagar; más corto y se le genera deuda a quien simplemente
# paga los primeros días del mes. La cifra es discutible y por eso está acá
# arriba y no enterrada en un `if`.
DIAS_DE_GRACIA = 3


def generar_deudas(db: Session, hoy: date | None = None) -> dict:
    """
    Crea las deudas de las cuotas vencidas que nadie renovó.

    IDEMPOTENTE: correrla dos veces no duplica nada. Lo garantiza el chequeo
    de "¿ya hay una deuda para esta membresía?", que consulta antes de
    insertar. Se hace con una consulta y no confiando en un UNIQUE porque el
    esquema no lo tiene — y agregarlo ahora obligaría a decidir qué pasa con
    una segunda deuda legítima sobre la misma membresía (un recargo, por
    ejemplo), que hoy no está definido.

    NO genera deuda a:
      - socios dados de baja: ya no son socios, cobrarles no tiene sentido
      - membresías CANCELADAS: la baja las cancela, y una baja no deja deuda
      - quien ya renovó: si tiene una membresía posterior, pagó
      - quien está dentro del período de gracia
      - quien ya tiene una deuda por esa misma membresía
    """
    hoy = hoy or date.today()
    limite = hoy - timedelta(days=DIAS_DE_GRACIA)

    # Las membresías vencidas hace más de los días de gracia, de socios que
    # siguen activos. Se traen de una en vez de recorrer socio por socio: con
    # mil socios eso serían mil consultas para un proceso que corre al
    # arrancar.
    candidatas = (
        db.query(Membresia, Socio)
        .join(Socio, Socio.id_socio == Membresia.id_socio)
        .filter(Socio.activo.is_(True),
                Membresia.fecha_vencimiento.isnot(None),
                Membresia.fecha_vencimiento < limite,
                # SUSPENDIDA queda afuera: es una pausa que el socio pidió, y
                # mientras está pausada el reloj no corre. Cobrarle por no
                # venir cuando avisó que no iba a venir sería exactamente al
                # revés de lo que la pausa significa.
                Membresia.estado.in_(["ACTIVA", "VENCIDA"]))
        .all()
    )
    if not candidatas:
        return {"creadas": 0, "revisadas": 0, "monto_total": 0.0}

    ids_membresia = [m.id_membresia for m, _ in candidatas]

    # Las que YA tienen deuda. Una consulta para todas.
    ya_tienen = {
        d[0] for d in
        db.query(Deuda.id_membresia)
        .filter(Deuda.id_membresia.in_(ids_membresia))
        .all()
    }

    # Quién renovó: el vencimiento más lejano de cada socio. Si tiene una
    # membresía que vence después, esta vencida ya fue reemplazada.
    ids_socio = [s.id_socio for _, s in candidatas]
    ultimo_vencimiento = dict(
        db.query(Membresia.id_socio, func.max(Membresia.fecha_vencimiento))
        .filter(Membresia.id_socio.in_(ids_socio),
                Membresia.estado.in_(["ACTIVA", "SUSPENDIDA"]))
        .group_by(Membresia.id_socio)
        .all()
    )

    creadas = 0
    monto_total = 0.0

    for membresia, socio in candidatas:
        if membresia.id_membresia in ya_tienen:
            continue

        renovado = ultimo_vencimiento.get(socio.id_socio)
        if renovado and renovado >= hoy:
            # Ya tiene cuota vigente. La vencida es historia, no una deuda.
            continue

        # El monto es el que se pactó, no el precio de hoy. Si el plan
        # aumentó desde que venció, cobrarle el precio nuevo por un mes viejo
        # sería inventar plata que nunca acordó pagar.
        monto = float(membresia.precio_pactado or 0)
        if monto <= 0:
            tipo = db.get(TipoMembresia, membresia.id_tipo_membresia)
            monto = float(tipo.precio_actual) if tipo else 0.0
        if monto <= 0:
            continue

        db.add(Deuda(
            id_socio=socio.id_socio,
            id_membresia=membresia.id_membresia,
            monto=monto,
            # La fecha en que la deuda EXISTE, no la del vencimiento: es
            # cuando el gimnasio la reconoce como tal.
            fecha_generacion=hoy,
            fecha_vencimiento=membresia.fecha_vencimiento,
            estado="PENDIENTE",
            generada_automaticamente=True,
            observaciones=(f"Cuota vencida el "
                           f"{membresia.fecha_vencimiento.strftime('%d/%m/%Y')} "
                           f"sin renovar."),
        ))

        # La membresía pasa a VENCIDA si todavía figuraba activa. Sin esto,
        # los reportes seguirían contándola como vigente mientras el socio ya
        # tiene una deuda por ella — dos partes del sistema diciendo cosas
        # opuestas sobre la misma fila.
        if membresia.estado == "ACTIVA":
            membresia.estado = "VENCIDA"

        creadas += 1
        monto_total += monto

    if creadas:
        db.commit()

    return {
        "creadas": creadas,
        "revisadas": len(candidatas),
        "monto_total": round(monto_total, 2),
    }
