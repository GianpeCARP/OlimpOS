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
    InscripcionActividad, Membresia, Pago, PlanActividad, Promocion,
    Socio, TipoMembresia,
)
from permisos import Acceso, Accion, Seccion
from schemas import (
    CobrarRequest, CobroResponse, EstadoCuentaOut, InscripcionOut, MembresiaOut,
    PagoOut, TipoMembresiaCrear, TipoMembresiaOut,
)
from renovacion import estado_renovacion
from security import Sesion, requiere_accion, requiere_seccion

# El calculo del descuento vive en el router de promociones y se importa: es la
# UNICA definicion de cuanto descuenta una promo. Duplicarla aca haria que el
# dia que cambie una regla, la vista previa muestre un numero y el cobro
# registre otro.
from routers.promociones import esta_vigente, precio_con_promo

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

    pagos = (
        db.query(Pago)
        .filter(Pago.id_socio == id_socio)
        .order_by(Pago.fecha_pago.desc())
        .limit(ULTIMOS_PAGOS)
        .all()
    )

    db.commit()   # persiste los VENCIDA que marcó _membresia_vigente
    renovacion = estado_renovacion(db, id_socio)

    # "Al día" es, sencillamente, tener una membresía vigente. NO existe una
    # tabla de deudas: la política es prepago y el estado "debe" es derivable
    # —no hay una membresía activa sin vencer—, así que no hay monto que sumar
    # ni lista de deudas que devolver. Los campos deudas/deuda_total se
    # mantienen en la respuesta (por compatibilidad con las apps) pero vacíos.
    return EstadoCuentaOut(
        id_socio=socio.id_socio,
        socio=_nombre_socio(socio),
        numero_socio=socio.numero_socio,
        membresia_actual=_a_membresia_out(vigente) if vigente else None,
        al_dia=bool(vigente),
        deuda_total=0.0,
        deudas=[],
        ultimos_pagos=[_a_pago_out(p) for p in pagos],
        puede_renovar=renovacion.puede,
        motivo_no_renovar=renovacion.motivo,
        renovable_desde=renovacion.desde,
    )


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

    Hace dos cosas en UNA transacción:
      1. Crea la Membresía nueva (o la renovación).
      2. Registra el Pago (con la promoción aplicada, si hubo).

    Que sea atómico importa más acá que en ningún otro lado: un cobro
    registrado sin membresía deja al socio pagando sin acceso, y una membresía
    sin pago le regala el mes.

    Ya no hay paso de "saldar deudas": el esquema eliminó la tabla Deuda. El
    estado "debe" es derivable de no tener membresía vigente, y renovar acá lo
    resuelve por definición.
    """
    socio = db.get(Socio, datos.id_socio)
    if socio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El socio no existe.")

    # Sin adelantos (renovacion.py): con un período en curso no se cobra otro.
    # Va antes que todo lo demás porque ningún otro dato cambia la respuesta.
    renovacion = estado_renovacion(db, socio.id_socio)
    if not renovacion.puede:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"{_nombre_socio(socio)}: {renovacion.motivo}")

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

    # --- La promoción -------------------------------------------------------
    # El descuento se recalcula acá con el id que mandó el cliente, nunca con
    # un monto que venga en el pedido. Es la misma regla que rige todo este
    # archivo: el monto lo calcula el backend.
    promocion = None
    precio_lista_original = precio
    descuento_aplicado = 0.0
    if datos.id_promocion is not None:
        if datos.monto_manual is not None:
            # No hay respuesta obvia a "¿el descuento va sobre el monto manual
            # o sobre el de lista?", y elegir una en silencio dejaría cobros
            # que nadie puede explicar seis meses después. Que decida quien
            # cobra.
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=("Elegí una sola cosa: un monto manual o una promoción, "
                        "no las dos."),
            )

        promocion = db.get(Promocion, datos.id_promocion)
        if promocion is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Esa promoción no existe.")
        # La promo tiene que estar vigente cuando arranca el período cobrado.
        # Sin adelantos (renovacion.py) el período arranca siempre hoy.
        inicio_periodo = date.today()

        if not esta_vigente(promocion, inicio_periodo):
            # Un solo mensaje para los dos motivos (apagada o fuera de fecha)
            # sería más corto, pero el mostrador necesita saber cuál es: una se
            # arregla reactivándola y la otra cambiándole las fechas.
            motivo = ("está dada de baja" if not promocion.activo
                      else f"vale del {promocion.fecha_inicio} al {promocion.fecha_fin}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"La promoción «{promocion.nombre}» {motivo}.",
            )
        # Una promo de otra sede no aplica acá. id_sede en None significa que
        # vale en todas.
        if promocion.id_sede is not None and promocion.id_sede != socio.id_sede:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(f"La promoción «{promocion.nombre}» es de otra sede y no "
                        f"se puede aplicar a este socio."),
            )

        precio_lista_original = precio
        descuento_aplicado, precio = precio_con_promo(precio, promocion)

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
    # Arranca HOY, siempre. Antes, con una cuota vigente, la nueva arrancaba al
    # vencer la anterior y la que corría quedaba marcada VENCIDA: eso era el
    # cobro por adelantado que el dueño sacó (ver renovacion.py). El chequeo de
    # arriba garantiza que acá no hay período en curso.
    _membresia_vigente(db, socio.id_socio)   # marca VENCIDA las que ya pasaron
    inicio = hoy

    # Membresia tiene un UNIQUE en (id_socio, fecha_inicio), asi que dos
    # membresias del mismo socio no pueden arrancar el mismo dia. Sin este
    # chequeo, el INSERT explotaba con un IntegrityError y el mostrador veia
    # un 500 con el nombre del constraint de Postgres en pantalla.
    #
    # El caso real que lo dispara: se cobra, se anula el pago por un error, y
    # se vuelve a cobrar el mismo dia. La membresia anulada sigue existiendo
    # con fecha_inicio de hoy, asi que la nueva choca.
    #
    # Se corre al primer dia libre en vez de fallar: el socio esta enfrente
    # pagando, y negarle el cobro por un detalle de indices seria absurdo. Un
    # dia de corrimiento no le quita nada — el vencimiento se calcula desde
    # ahi.
    while (db.query(Membresia)
           .filter(Membresia.id_socio == socio.id_socio,
                   Membresia.fecha_inicio == inicio)
           .first()) is not None:
        inicio = inicio + timedelta(days=1)

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
    # La promoción aplicada y los pesos descontados se guardan en el PAGO (no
    # en la membresía). El precio solo no alcanza: dentro de seis meses,
    # "$24.000 en vez de $30.000" no dice si fue un descuento, un error de
    # tipeo o un precio pactado a mano. Con la FK y monto_descuento, la
    # respuesta está en la fila.
    pago = Pago(
        id_socio=socio.id_socio,
        id_membresia=membresia.id_membresia,
        id_tipo_membresia=tipo.id_tipo_membresia,
        id_sede=socio.id_sede,
        metodo=datos.metodo.value,
        monto=precio,
        fecha_pago=datetime.now(),
        periodo_desde=membresia.fecha_inicio,
        periodo_hasta=membresia.fecha_vencimiento,
        es_adelanto=False,
        estado="CONFIRMADO",
        numero_comprobante=datos.numero_comprobante,
        id_promocion=promocion.id_promocion if promocion else None,
        monto_descuento=descuento_aplicado if promocion else None,
    )
    db.add(pago)
    db.flush()

    # --- 3. Abono de actividad (opcional) -----------------------------------
    # La inscripción ya NO cuelga de la membresía (Inscripcion_Actividad perdió
    # id_membresia): es del socio. Igual se sigue creando en la misma
    # transacción y con la misma vigencia que la membresía, para que un abono
    # nunca sobreviva a la cuota que da acceso al gimnasio.
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

        inscripcion = InscripcionActividad(
            id_socio=socio.id_socio,
            id_plan_actividad=plan.id_plan_actividad,
            precio_pactado=float(plan.precio),
            fecha_inicio=membresia.fecha_inicio,
            fecha_vencimiento=membresia.fecha_vencimiento,
            estado="ACTIVA",
        )
        db.add(inscripcion)
        db.flush()

        precio += float(plan.precio)
        pago.monto = precio
        pago.id_inscripcion = inscripcion.id_inscripcion

        # Recién comprada, no consumió nada: las clases que le quedan son el
        # total del plan (para POR_MES). El consumo se cuenta contando Reserva,
        # no un contador materializado — ver clases_restantes_de en actividades.
        restantes = plan.cantidad if plan.tipo_limite == "POR_MES" else None
        inscripcion_out = InscripcionOut(
            id_inscripcion=inscripcion.id_inscripcion,
            actividad=plan.actividad.nombre if plan.actividad else "?",
            plan=plan.nombre,
            tipo_limite=plan.tipo_limite,
            clases_restantes=restantes,
            fecha_inicio=inscripcion.fecha_inicio,
            fecha_vencimiento=inscripcion.fecha_vencimiento,
            precio_pactado=float(inscripcion.precio_pactado),
        )

    db.commit()
    db.refresh(pago)
    db.refresh(membresia)

    partes = [f"Cobro registrado: ${precio:,.2f} a {_nombre_socio(socio)}."]
    if inscripcion_out:
        partes.append(
            f"Incluye el abono {inscripcion_out.plan} de {inscripcion_out.actividad}, "
            f"vigente hasta el {inscripcion_out.fecha_vencimiento}."
        )

    return CobroResponse(
        pago=_a_pago_out(pago),
        membresia=_a_membresia_out(membresia),
        inscripcion=inscripcion_out,
        deudas_saldadas=[],
        total=precio,
        mensaje=" ".join(partes),
        promocion=promocion.nombre if promocion else None,
        precio_lista=precio_lista_original if promocion else None,
        descuento=descuento_aplicado if promocion else None,
    )


@router.post("/pagos/{id_pago}/anular", response_model=PagoOut)
def anular_pago(
    id_pago: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.COBROS, Acceso.TOTAL)),
):
    """
    Anula un pago mal registrado. NO lo borra.

    Al anularlo se cancela también la membresía que ese pago habilitó: si no,
    anular un cobro le dejaría al socio el mes pago de arriba.
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

    db.commit()
    db.refresh(pago)
    return _a_pago_out(pago)
