"""
routers/pagos_online.py
-----------------------
Los dos endpoints del cobro con tarjeta: el que arranca el checkout y el que
recibe el aviso de Mercado Pago.

ESTADO: ESCRITO, NO PROBADO CONTRA MERCADO PAGO. Ver el docstring de
mercadopago.py para lo que falta (token, URL pública y secreto del webhook).

POR QUÉ EL WEBHOOK NO ESTÁ EN /portal
=====================================
Todo lo de /portal exige una sesión de socio. El webhook NO tiene sesión:
lo llama Mercado Pago desde sus servidores, sin cookie ni token. Meterlo ahí
obligaría a agujerear el guard de una sección entera para una ruta, y ese
agujero después se olvida.

Va acá, sin autenticación de sesión, y su seguridad es otra: la firma HMAC
que verifica que el aviso vino de Mercado Pago. La URL es pública por
necesidad —tiene que serlo para que la llamen— así que lo que la protege es
que nadie más puede firmar.
"""

from datetime import date, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

import mercadopago as mp
from database import get_db
from models import Membresia, Pago, Socio, TipoMembresia
from permisos import Seccion
from schemas import (
    IniciarPagoRequest, IniciarPagoResponse, MensajeResponse, PlanDisponibleOut,
)
from security import Sesion, requiere_seccion

router = APIRouter(tags=["Pagos online"])


def _mi_socio(db: Session, sesion: Sesion) -> Socio:
    """El socio de la sesión. Mismo criterio que el portal: sale del token."""
    if sesion.id_socio is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Esta sección es para socios.")
    socio = db.get(Socio, sesion.id_socio)
    if socio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="No encontramos tu ficha de socio.")
    return socio


@router.get("/portal/mi-cuota/planes", response_model=list[PlanDisponibleOut])
def planes_disponibles(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.MI_CUOTA)),
):
    """
    Los planes que el socio puede comprar, con su precio.

    Existe porque /cobros/tipos-membresia está protegido con la sección
    COBROS, que el socio tiene en NINGUNO — y con razón: esa pantalla es la
    caja del gimnasio. Pero para elegir qué pagar necesita ver la lista, así
    que se expone acá lo mínimo: nombre, duración y precio. Nada de lo demás
    que trae el endpoint del mostrador.

    Sólo los ACTIVOS: ofrecerle comprar un plan discontinuado terminaría en
    un rechazo que no entendería.
    """
    _mi_socio(db, sesion)  # valida que sea un socio, no sólo alguien con sesión
    tipos = (db.query(TipoMembresia)
             .filter(TipoMembresia.activo.is_(True))
             .order_by(TipoMembresia.duracion_dias)
             .all())
    return [
        PlanDisponibleOut(
            id_tipo_membresia=t.id_tipo_membresia,
            nombre=t.nombre,
            descripcion=t.descripcion,
            duracion_dias=t.duracion_dias,
            precio=float(t.precio_actual),
        )
        for t in tipos
    ]


# =============================================================================
# ARRANCAR EL PAGO
# =============================================================================

@router.post("/portal/mi-cuota/pagar", response_model=IniciarPagoResponse,
             status_code=status.HTTP_201_CREATED)
def iniciar_pago(
    datos: IniciarPagoRequest,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.MI_CUOTA)),
):
    """
    Crea el Pago en PENDIENTE y devuelve la URL del checkout.

    El socio elige el PLAN, no el monto: el precio sale de Tipo_Membresia y
    se lee del lado del servidor. Si el monto viniera del pedido, cualquiera
    con la consola abierta pagaría $1 una cuota de $30.000 y en la base
    quedaría un pago perfectamente válido.

    Y el Pago nace PENDIENTE. Que el socio haya apretado el botón no
    significa que la plata llegó: crearlo CONFIRMADO le extendería la
    membresía antes de que nadie pague. Se confirma en el webhook.
    """
    socio = _mi_socio(db, sesion)

    if not mp.esta_configurado():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=("El pago online todavía no está habilitado. "
                    "Acercate a recepción para pagar tu cuota."),
        )

    tipo = db.get(TipoMembresia, datos.id_tipo_membresia)
    if tipo is None or not tipo.activo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Ese plan no existe o ya no está disponible.")

    monto = float(tipo.precio_actual)

    pago = Pago(
        id_socio=socio.id_socio,
        id_sede=socio.id_sede,
        # BILLETERA_VIRTUAL es lo más cercano en el enum del esquema. No se
        # agrega un valor "MERCADO_PAGO" porque el enum describe CÓMO paga la
        # persona, no con qué proveedor lo procesamos: si mañana se cambia de
        # pasarela, el método de pago del socio sigue siendo el mismo.
        metodo="BILLETERA_VIRTUAL",
        monto=monto,
        fecha_pago=datetime.now(),
        estado="PENDIENTE",
    )
    db.add(pago)
    db.commit()
    db.refresh(pago)

    resultado = mp.crear_preferencia(
        id_pago=pago.id_pago,
        descripcion=f"{tipo.nombre} — {socio.persona.nombre_completo}",
        monto=monto,
        email_socio=socio.persona.email,
    )

    if not resultado["ok"]:
        # El Pago queda en PENDIENTE y no se borra. Un registro contable que
        # desaparece es un agujero: si mañana Mercado Pago avisa que ese pago
        # se aprobó, tiene que haber una fila donde aplicarlo. Se cancela, que
        # deja rastro.
        pago.estado = "CANCELADO"
        pago.fecha_cancelacion = datetime.now()
        db.commit()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY,
                            detail=resultado["error"])

    pref = resultado["data"]
    return IniciarPagoResponse(
        id_pago=pago.id_pago,
        monto=monto,
        plan=tipo.nombre,
        url_checkout=pref.init_point,
        simulado=pref.simulada,
        mensaje=(f"Te vamos a llevar a Mercado Pago para pagar {tipo.nombre} "
                 f"por ${monto:,.2f}."),
    )


# =============================================================================
# EL AVISO DE MERCADO PAGO
# =============================================================================

def _acreditar(db: Session, id_pago: int, id_pago_mp: str, estado: str,
                monto_mp: float) -> str:
    """
    Aplica el resultado a un Pago. Es idempotente.

    La idempotencia se apoya en `Pago.numero_comprobante`, que es UNIQUE en el
    esquema: ahí se guarda el id de Mercado Pago. Un segundo aviso del mismo
    pago encuentra la fila ya marcada y se va sin tocar nada. Que la defensa
    viva en el esquema y no sólo en este `if` importa, porque el `if` se
    puede olvidar de aplicar y el UNIQUE no.

    Hace falta de verdad: Mercado Pago REINTENTA si no contesta 200 rápido, y
    manda el mismo aviso más de una vez por diseño. Sin esto, una cuota se
    acreditaría dos veces y la membresía se extendería el doble.
    """
    pago = db.get(Pago, id_pago)
    if pago is None:
        return f"No existe el pago {id_pago}. Se ignora."

    comprobante = f"MP-{id_pago_mp}"

    if pago.numero_comprobante == comprobante and pago.estado == estado:
        return "Ya estaba aplicado. No se hizo nada."

    # El monto que Mercado Pago dice haber cobrado tiene que coincidir con el
    # que este Pago dice valer. Si no coinciden NO se acredita: puede ser un
    # id reutilizado, un aviso apuntando al pago equivocado, o alguien
    # probando. Se deja PENDIENTE para que una persona lo mire.
    if estado == "CONFIRMADO" and abs(float(pago.monto) - monto_mp) > 0.01:
        return (f"El monto no coincide: el pago {id_pago} vale "
                f"${float(pago.monto):,.2f} y Mercado Pago informó "
                f"${monto_mp:,.2f}. NO se acredita.")

    pago.numero_comprobante = comprobante
    pago.estado = estado
    if estado == "CANCELADO":
        pago.fecha_cancelacion = datetime.now()

    if estado == "CONFIRMADO":
        _extender_membresia(db, pago)

    db.commit()
    return f"Pago {id_pago} -> {estado}."


def _extender_membresia(db: Session, pago: Pago) -> None:
    """
    Le da al socio lo que compró.

    Se hace ACÁ y no al crear el Pago porque hasta este momento no había
    plata. Extender antes sería regalar la cuota a quien abandona el checkout.
    """
    if pago.id_membresia is not None:
        return  # ya se le habia asignado

    tipo = (db.query(TipoMembresia)
            .filter(TipoMembresia.precio_actual == pago.monto,
                    TipoMembresia.activo.is_(True))
            .first())
    if tipo is None:
        return

    hoy = date.today()
    vigente = (db.query(Membresia)
               .filter(Membresia.id_socio == pago.id_socio,
                       Membresia.estado == "ACTIVA")
               .order_by(Membresia.fecha_vencimiento.desc())
               .first())

    # Si todavía le queda cuota, la nueva arranca cuando termina la anterior.
    # Arrancar hoy le comería los días que ya había pagado — es la misma regla
    # que aplica el cobro del mostrador.
    desde = hoy
    if vigente and vigente.fecha_vencimiento and vigente.fecha_vencimiento >= hoy:
        desde = vigente.fecha_vencimiento
        vigente.estado = "VENCIDA"

    from datetime import timedelta

    # Mismo UNIQUE (id_socio, fecha_inicio) que contempla el cobro del
    # mostrador. Acá el caso es más probable todavía: el socio puede apretar
    # "pagar" dos veces en la app y quedar con dos pagos del mismo día.
    while (db.query(Membresia)
           .filter(Membresia.id_socio == pago.id_socio,
                   Membresia.fecha_inicio == desde)
           .first()) is not None:
        desde = desde + timedelta(days=1)

    membresia = Membresia(
        id_socio=pago.id_socio,
        id_tipo_membresia=tipo.id_tipo_membresia,
        precio_pactado=pago.monto,
        fecha_inicio=desde,
        fecha_vencimiento=desde + timedelta(days=tipo.duracion_dias),
        estado="ACTIVA",
    )
    db.add(membresia)
    db.flush()
    pago.id_membresia = membresia.id_membresia


@router.post("/webhooks/mercadopago", response_model=MensajeResponse)
async def webhook_mercadopago(
    request: Request,
    db: Session = Depends(get_db),
    x_signature: str = Header(default=""),
    x_request_id: str = Header(default=""),
):
    """
    Recibe el aviso de Mercado Pago cuando un pago cambia de estado.

    SIN SESIÓN: lo llama Mercado Pago desde sus servidores. Lo que lo protege
    es la firma HMAC, no un token — la URL tiene que ser pública para que la
    puedan llamar.

    SIEMPRE CONTESTA 200, incluso cuando descarta el aviso. Si contestara un
    error, Mercado Pago reintentaría el mismo aviso una y otra vez creyendo
    que no llegó. Lo que pasó queda en el `mensaje` y en el log.

    DEL CUERPO SÓLO SE LEE EL ID. El estado y el monto se releen
    consultándole a Mercado Pago con nuestro token: el cuerpo llega por HTTP
    y lo puede escribir cualquiera que descubra la URL.
    """
    try:
        cuerpo = await request.json()
    except Exception:  # noqa: BLE001
        return MensajeResponse(mensaje="Cuerpo ilegible. Se ignora.")

    # Mercado Pago manda varios tipos de aviso; sólo interesan los de pagos.
    if cuerpo.get("type") not in (None, "payment"):
        return MensajeResponse(mensaje=f"Aviso de tipo '{cuerpo.get('type')}'. No aplica.")

    id_pago_mp = str((cuerpo.get("data") or {}).get("id") or cuerpo.get("id") or "")
    if not id_pago_mp:
        return MensajeResponse(mensaje="El aviso no trae id de pago. Se ignora.")

    if not mp.verificar_firma(x_signature, x_request_id, id_pago_mp):
        # No se acredita nada. Un aviso sin firma válida es, o un error de
        # configuración, o alguien probando: en los dos casos la respuesta es
        # la misma.
        print(f"  [MP] Aviso RECHAZADO por firma inválida (pago {id_pago_mp}).")
        return MensajeResponse(mensaje="Firma inválida. El aviso se descarta.")

    consulta = mp.consultar_pago(id_pago_mp)
    if not consulta["ok"]:
        print(f"  [MP] No se pudo consultar el pago {id_pago_mp}: {consulta['error']}")
        return MensajeResponse(mensaje="No se pudo consultar el pago. Se reintentará.")

    externo = consulta["data"]
    if externo.id_pago_interno is None:
        return MensajeResponse(
            mensaje=f"El pago {id_pago_mp} no tiene referencia nuestra. Se ignora.")

    resultado = _acreditar(
        db,
        id_pago=externo.id_pago_interno,
        id_pago_mp=externo.id_pago_mp,
        estado=mp.estado_interno(externo.estado_mp),
        monto_mp=externo.monto,
    )
    print(f"  [MP] {resultado}")
    return MensajeResponse(mensaje=resultado)


@router.post("/portal/mi-cuota/pagar/{id_pago}/simular", response_model=MensajeResponse)
def simular_acreditacion(
    id_pago: int,
    aprobado: bool = True,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.MI_CUOTA)),
):
    """
    Acredita un pago a mano, para poder desarrollar sin cuenta de Mercado Pago.

    SÓLO existe en modo simulado. Con un token real cargado responde 404 —
    no 403 y no un mensaje explicativo: para quien no debería poder usarlo,
    lo mejor es que la ruta ni parezca existir.

    Es el reemplazo del webhook mientras no haya URL pública. Sin esto, el
    flujo se corta en "te llevamos a Mercado Pago" y no hay forma de probar
    qué pasa después.
    """
    if not mp.modo_simulado():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado.")

    socio = _mi_socio(db, sesion)
    pago = db.get(Pago, id_pago)
    if pago is None or pago.id_socio != socio.id_socio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Ese pago no existe.")

    resultado = _acreditar(
        db,
        id_pago=id_pago,
        id_pago_mp=f"SIM-{id_pago}",
        estado="CONFIRMADO" if aprobado else "CANCELADO",
        monto_mp=float(pago.monto),
    )
    return MensajeResponse(mensaje=f"[SIMULADO] {resultado}")
