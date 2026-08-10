"""
routers/cobros.py
-----------------
Planes, cobros, membresías y deudas. Es la plata del gimnasio, así que las
reglas de acá son las más estrictas del sistema.

EL MONTO LO CALCULA EL BACKEND, NUNCA EL CLIENTE
------------------------------------------------
`CobrarRequest` no acepta un monto libre: recibe el plan y el backend busca su
precio. Si el monto viniera del cliente, cualquiera con la consola del
navegador abierta podría cobrar $1 una membresía de $30.000, y en la base
quedaría un pago perfectamente válido.

`monto_manual` existe para el caso legítimo —un precio pactado distinto, un
ajuste— pero exige el permiso de promociones, que en la matriz solo tiene el
Dueño. Un recepcionista cobra la lista de precios; cambiarla es otra decisión.

NADA SE BORRA
-------------
Anular un pago le pone estado CANCELADO y una fecha de cancelación; la fila
queda. Un registro contable que desaparece es un agujero en la caja: si
alguien cobra y después borra la fila, no queda rastro de que cobró.

Lo mismo con las membresías: renovar CREA una fila nueva en vez de actualizar
la anterior. Así queda el historial de cuándo estuvo al día y cuándo no, que
es lo que permite responder "¿desde cuándo debe?".
"""

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Deuda, InscripcionActividad, Membresia, Pago, PlanActividad, Socio,
    TipoMembresia,
)
from permisos import Acceso, Accion, Seccion
from schemas import (
    CobrarRequest, CobroResponse, DeudaOut, EstadoCuentaOut, InscripcionOut,
    MembresiaOut, PagarDeudaRequest, PagoOut, TipoMembresiaCrear,
    TipoMembresiaOut,
)
from security import Sesion, requiere_accion, requiere_seccion

router = APIRouter(prefix="/cobros", tags=["Cobros"])

# Cuántos pagos se devuelven en el estado de cuenta. El mostrador necesita
# ver los últimos para confirmar que no está cobrando dos veces, no el
# historial completo.
ULTIMOS_PAGOS = 5


# =============================================================================
# HELPERS
# =============================================================================

def _nombre_socio(socio: Socio | None) -> str:
    if socio is None or socio.persona is None:
        return "?"
    return socio.persona.nombre_completo


def _a_pago_out(pago: Pago) -> PagoOut:
    return PagoOut(
        id_pago=pago.id_pago,
        id_socio=pago.id_socio,
        socio=_nombre_socio(pago.socio),
        monto=float(pago.monto),
        metodo=pago.metodo,
        fecha_pago=pago.fecha_pago,
        periodo_desde=pago.periodo_desde,
        periodo_hasta=pago.periodo_hasta,
        estado=pago.estado,
        numero_comprobante=pago.numero_comprobante,
    )


def _a_membresia_out(m: Membresia) -> MembresiaOut:
    dias = None
    if m.fecha_vencimiento:
        # Se calcula contra la fecha del SERVIDOR. Si el frontend lo hiciera
        # con su propio reloj, un navegador con la fecha cambiada podría
        # mostrarse al día estando vencido.
        dias = (m.fecha_vencimiento - date.today()).days

    return MembresiaOut(
        id_membresia=m.id_membresia,
        id_socio=m.id_socio,
        tipo=m.tipo.nombre if m.tipo else "?",
        precio_pactado=float(m.precio_pactado),
        fecha_inicio=m.fecha_inicio,
        fecha_vencimiento=m.fecha_vencimiento,
        estado=m.estado,
        dias_restantes=dias,
    )


def _a_deuda_out(d: Deuda) -> DeudaOut:
    return DeudaOut(
        id_deuda=d.id_deuda,
        id_socio=d.id_socio,
        socio=_nombre_socio(d.socio),
        monto=float(d.monto),
        fecha_generacion=d.fecha_generacion,
        fecha_vencimiento=d.fecha_vencimiento,
        estado=d.estado,
        generada_automaticamente=bool(d.generada_automaticamente),
        observaciones=d.observaciones,
    )


def _membresia_vigente(db: Session, id_socio: int) -> Membresia | None:
    """
    La membresía activa más reciente, o None.

    Marca como VENCIDA sobre la marcha las que pasaron su fecha: sin una tarea
    programada que las revise, el estado en la base se queda viejo, y "activa
    pero vencida hace tres meses" es peor que no tener el campo.
    """
    membresias = (
        db.query(Membresia)
        .filter(Membresia.id_socio == id_socio, Membresia.estado == "ACTIVA")
        .order_by(Membresia.fecha_inicio.desc())
        .all()
    )

    hoy = date.today()
    vigente = None
    for m in membresias:
        if m.fecha_vencimiento and m.fecha_vencimiento < hoy:
            m.estado = "VENCIDA"
        elif vigente is None:
            vigente = m
    return vigente


# =============================================================================
# CATÁLOGO DE PLANES
# =============================================================================

@router.get("/tipos-membresia", response_model=list[TipoMembresiaOut])
def listar_tipos(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.COBROS)),
):
    tipos = db.query(TipoMembresia).order_by(TipoMembresia.precio_actual).all()
    return [
        TipoMembresiaOut(
            id_tipo_membresia=t.id_tipo_membresia, nombre=t.nombre,
            descripcion=t.descripcion, duracion_dias=t.duracion_dias,
            precio_actual=float(t.precio_actual), activo=bool(t.activo),
        )
        for t in tipos
    ]


@router.post("/tipos-membresia", response_model=TipoMembresiaOut,
             status_code=status.HTTP_201_CREATED)
def crear_tipo(
    datos: TipoMembresiaCrear,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.GESTION_PROMOCIONES)),
):
    """
    Crea un plan. Requiere GESTION_PROMOCIONES —solo el Dueño— porque definir
    la lista de precios es una decisión de negocio, no operativa del día.
    """
    nombre = datos.nombre.strip()
    if db.query(TipoMembresia).filter(TipoMembresia.nombre.ilike(nombre)).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un plan llamado '{nombre}'.",
        )

    tipo = TipoMembresia(
        nombre=nombre, descripcion=datos.descripcion,
        duracion_dias=datos.duracion_dias, precio_actual=datos.precio_actual,
        activo=True,
    )
    db.add(tipo)
    db.commit()
    db.refresh(tipo)
    return TipoMembresiaOut(
        id_tipo_membresia=tipo.id_tipo_membresia, nombre=tipo.nombre,
        descripcion=tipo.descripcion, duracion_dias=tipo.duracion_dias,
        precio_actual=float(tipo.precio_actual), activo=bool(tipo.activo),
    )


# =============================================================================
# ESTADO DE CUENTA
# =============================================================================

@router.get("/socio/{id_socio}", response_model=EstadoCuentaOut)
def estado_cuenta(
    id_socio: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.COBROS)),
):
    """Todo lo que el mostrador necesita ver antes de cobrarle a alguien."""
    socio = db.get(Socio, id_socio)
    if socio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El socio no existe.")

    vigente = _membresia_vigente(db, id_socio)

    deudas = (
        db.query(Deuda)
        .filter(Deuda.id_socio == id_socio, Deuda.estado == "PENDIENTE")
        .order_by(Deuda.fecha_generacion)
        .all()
    )

    pagos = (
        db.query(Pago)
        .filter(Pago.id_socio == id_socio)
        .order_by(Pago.fecha_pago.desc())
        .limit(ULTIMOS_PAGOS)
        .all()
    )

    db.commit()   # persiste los VENCIDA que marcó _membresia_vigente

    return EstadoCuentaOut(
        id_socio=socio.id_socio,
        socio=_nombre_socio(socio),
        numero_socio=socio.numero_socio,
        membresia_actual=_a_membresia_out(vigente) if vigente else None,
        # "Al día" es tener membresía vigente Y no deber nada. Las dos
        # condiciones: alguien puede tener la cuota paga del mes y arrastrar
        # una deuda vieja.
        al_dia=bool(vigente) and not deudas,
        deuda_total=float(sum(d.monto for d in deudas)),
        deudas=[_a_deuda_out(d) for d in deudas],
        ultimos_pagos=[_a_pago_out(p) for p in pagos],
    )


@router.get("/deudas", response_model=list[DeudaOut])
def listar_deudas(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.COBROS)),
):
    """Todas las deudas pendientes del gimnasio, la más vieja primero."""
    deudas = (
        db.query(Deuda)
        .filter(Deuda.estado == "PENDIENTE")
        .order_by(Deuda.fecha_generacion)
        .all()
    )
    return [_a_deuda_out(d) for d in deudas]


# =============================================================================
# COBRAR
# =============================================================================

@router.post("", response_model=CobroResponse, status_code=status.HTTP_201_CREATED)
def cobrar(
    datos: CobrarRequest,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.COBRAR_PAGOS)),
):
    """
    Registra un cobro de membresía. Es la operación central del mostrador.

    Hace tres cosas en UNA transacción:
      1. Crea la Membresía nueva (o la renovación).
      2. Registra el Pago.
      3. Si el socio debía, salda las deudas con ese pago.

    Que sea atómico importa más acá que en ningún otro lado: un cobro
    registrado sin membresía deja al socio pagando sin acceso, y una membresía
    sin pago le regala el mes.
    """
    socio = db.get(Socio, datos.id_socio)
    if socio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El socio no existe.")

    tipo = db.get(TipoMembresia, datos.id_tipo_membresia)
    if tipo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El plan no existe.")
    if not tipo.activo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El plan '{tipo.nombre}' está dado de baja y no se puede cobrar.",
        )

    # --- El precio ----------------------------------------------------------
    precio = float(tipo.precio_actual)
    if datos.monto_manual is not None:
        # Cambiar el precio de lista es una decisión de negocio, no del
        # mostrador. Sin este chequeo, el campo sería un agujero por donde
        # cobrar cualquier cosa.
        if not any(r in sesion.roles for r in ("dueno",)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el dueño puede cobrar un monto distinto al del plan.",
            )
        precio = datos.monto_manual

    # --- Comprobante duplicado ---------------------------------------------
    # UNIQUE en el esquema; se chequea antes para dar un mensaje claro. Es lo
    # que evita registrar dos veces el mismo cobro por un doble click.
    if datos.numero_comprobante:
        ya = (db.query(Pago)
              .filter(Pago.numero_comprobante == datos.numero_comprobante)
              .first())
        if ya:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya se registró un pago con el comprobante {datos.numero_comprobante}.",
            )

    hoy = date.today()

    # --- 1. Membresía -------------------------------------------------------
    # Si tenía una vigente, la nueva arranca cuando termina la anterior, no
    # hoy: quien paga el mes que viene por adelantado no pierde los días que
    # le quedaban.
    vigente = _membresia_vigente(db, socio.id_socio)
    inicio = hoy
    es_adelanto = False
    if vigente and vigente.fecha_vencimiento and vigente.fecha_vencimiento >= hoy:
        inicio = vigente.fecha_vencimiento + timedelta(days=1)
        es_adelanto = True
        vigente.estado = "VENCIDA"    # la reemplaza la nueva

    membresia = Membresia(
        id_socio=socio.id_socio,
        id_tipo_membresia=tipo.id_tipo_membresia,
        precio_pactado=precio,
        fecha_inicio=inicio,
        fecha_vencimiento=inicio + timedelta(days=tipo.duracion_dias),
        estado="ACTIVA",
    )
    db.add(membresia)
    db.flush()

    # --- 2. Pago ------------------------------------------------------------
    pago = Pago(
        id_socio=socio.id_socio,
        id_membresia=membresia.id_membresia,
        id_sede=socio.id_sede,
        metodo=datos.metodo.value,
        monto=precio,
        fecha_pago=datetime.now(),
        periodo_desde=membresia.fecha_inicio,
        periodo_hasta=membresia.fecha_vencimiento,
        es_adelanto=es_adelanto,
        estado="CONFIRMADO",
        numero_comprobante=datos.numero_comprobante,
    )
    db.add(pago)
    db.flush()

    # --- 3. Abono de actividad (opcional) -----------------------------------
    # Va en la misma transacción porque Inscripcion_Actividad.id_membresia es
    # NOT NULL: el abono se cuelga de la membresía que se acaba de crear. Si
    # fueran dos pedidos, entre uno y otro habría una ventana donde el plan
    # quedó pago sin membresía a la que atarse.
    inscripcion = None
    inscripcion_out = None
    if datos.id_plan_actividad is not None:
        plan = db.get(PlanActividad, datos.id_plan_actividad)
        if plan is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="El plan de actividad no existe.")
        if not plan.activo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El plan '{plan.nombre}' está dado de baja y no se puede vender.",
            )

        # El abono vence junto con la membresía, no a los 30 días de hoy: si
        # la membresía cubre más, los días de diferencia van sin cargo. Un
        # abono que sobreviva a la membresía dejaría al socio con clases
        # disponibles y sin derecho a entrar al gimnasio.
        inscripcion = InscripcionActividad(
            id_socio=socio.id_socio,
            id_plan_actividad=plan.id_plan_actividad,
            id_membresia=membresia.id_membresia,
            precio_pactado=float(plan.precio),
            fecha_inicio=membresia.fecha_inicio,
            fecha_vencimiento=membresia.fecha_vencimiento,
            clases_restantes=plan.cantidad,
            estado="ACTIVA",
        )
        db.add(inscripcion)
        db.flush()

        precio += float(plan.precio)
        pago.monto = precio
        pago.id_inscripcion = inscripcion.id_inscripcion

        inscripcion_out = InscripcionOut(
            id_inscripcion=inscripcion.id_inscripcion,
            actividad=plan.actividad.nombre if plan.actividad else "?",
            plan=plan.nombre,
            tipo_limite=plan.tipo_limite,
            clases_restantes=inscripcion.clases_restantes,
            fecha_inicio=inscripcion.fecha_inicio,
            fecha_vencimiento=inscripcion.fecha_vencimiento,
            precio_pactado=float(inscripcion.precio_pactado),
        )

    # --- 4. Deudas ----------------------------------------------------------
    saldadas = []
    if datos.saldar_deudas:
        pendientes = (
            db.query(Deuda)
            .filter(Deuda.id_socio == socio.id_socio, Deuda.estado == "PENDIENTE")
            .all()
        )
        for d in pendientes:
            d.estado = "PAGADA"
            d.id_pago_cancelatorio = pago.id_pago
            saldadas.append(d)

    db.commit()
    db.refresh(pago)
    db.refresh(membresia)

    partes = [f"Cobro registrado: ${precio:,.2f} a {_nombre_socio(socio)}."]
    if inscripcion_out:
        partes.append(
            f"Incluye el abono {inscripcion_out.plan} de {inscripcion_out.actividad} "
            f"({inscripcion_out.clases_restantes} clases), vigente hasta el "
            f"{inscripcion_out.fecha_vencimiento}."
        )
    if es_adelanto:
        partes.append(f"Como tenía cuota vigente, el período nuevo arranca el {inicio}.")
    if saldadas:
        total_deudas = sum(float(d.monto) for d in saldadas)
        partes.append(f"Se saldaron {len(saldadas)} deuda(s) por ${total_deudas:,.2f}.")

    return CobroResponse(
        pago=_a_pago_out(pago),
        membresia=_a_membresia_out(membresia),
        inscripcion=inscripcion_out,
        deudas_saldadas=[_a_deuda_out(d) for d in saldadas],
        total=precio,
        mensaje=" ".join(partes),
    )


@router.post("/pagos/{id_pago}/anular", response_model=PagoOut)
def anular_pago(
    id_pago: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.COBROS, Acceso.TOTAL)),
):
    """
    Anula un pago mal registrado. NO lo borra.

    Al anularlo se cancela también la membresía que ese pago habilitó y
    vuelven a quedar pendientes las deudas que había saldado: si no, anular un
    cobro le dejaría al socio el mes pago y las deudas perdonadas de arriba.
    """
    pago = db.get(Pago, id_pago)
    if pago is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El pago no existe.")

    if pago.estado == "CANCELADO":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ese pago ya estaba anulado.",
        )

    pago.estado = "CANCELADO"
    pago.fecha_cancelacion = datetime.now()

    if pago.membresia is not None:
        pago.membresia.estado = "CANCELADA"

    revividas = db.query(Deuda).filter(Deuda.id_pago_cancelatorio == pago.id_pago).all()
    for d in revividas:
        d.estado = "PENDIENTE"
        d.id_pago_cancelatorio = None

    db.commit()
    db.refresh(pago)
    return _a_pago_out(pago)


@router.post("/deudas/{id_deuda}/pagar", response_model=PagoOut,
             status_code=status.HTTP_201_CREATED)
def pagar_deuda(
    id_deuda: int,
    datos: PagarDeudaRequest,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.COBRAR_PAGOS)),
):
    """
    Cobra UNA deuda puntual, sin renovar la membresía.

    Es distinto del cobro normal —que salda todas las deudas de arrastre— y
    hace falta porque el mostrador a veces cobra solo lo adeudado: alguien que
    viene a ponerse al día pero todavía no renueva.

    El monto lo pone la deuda, no el cliente: cobrar $1 una deuda de $30.000
    sería tan grave acá como en el cobro de membresía.

    `id_pago_cancelatorio` deja la relación 1 a 1 entre la deuda y el pago que
    la canceló. Es lo que permite responder después "¿con qué pago se saldó
    esto?" sin cruzar montos y fechas a ojo.
    """
    deuda = db.get(Deuda, id_deuda)
    if deuda is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La deuda no existe.")
    if deuda.estado != "PENDIENTE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Esa deuda ya está {deuda.estado.lower()}.",
        )

    if datos.numero_comprobante:
        ya = (db.query(Pago)
              .filter(Pago.numero_comprobante == datos.numero_comprobante)
              .first())
        if ya:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya se registró un pago con el comprobante {datos.numero_comprobante}.",
            )

    socio = deuda.socio

    pago = Pago(
        id_socio=deuda.id_socio,
        id_membresia=deuda.id_membresia,
        id_sede=socio.id_sede if socio else None,
        metodo=datos.metodo.value,
        monto=deuda.monto,
        fecha_pago=datetime.now(),
        estado="CONFIRMADO",
        numero_comprobante=datos.numero_comprobante,
    )
    db.add(pago)
    db.flush()

    deuda.estado = "PAGADA"
    deuda.id_pago_cancelatorio = pago.id_pago

    db.commit()
    db.refresh(pago)
    return _a_pago_out(pago)
