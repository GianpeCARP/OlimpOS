"""
mercadopago.py
--------------
Cobros con tarjeta desde la app del socio, vía Mercado Pago Checkout Pro.

ESTADO: ESCRITO PERO NO PROBADO CONTRA MERCADO PAGO.

Falta lo que no depende del código y hay que decirlo claro, porque un módulo
de pagos que "parece andar" es peor que uno que avisa que no:

  1. Un ACCESS_TOKEN de una cuenta real (el de sandbox alcanza para
     desarrollar). Va en MP_ACCESS_TOKEN del .env.
  2. Una URL PÚBLICA para el webhook. Mercado Pago no le puede avisar a
     127.0.0.1 que el pago se acreditó, así que sin esto el socio paga y el
     sistema nunca se entera. Para desarrollo, `ngrok http 8000` alcanza.
  3. El secreto del webhook (MP_WEBHOOK_SECRET), que se saca del panel de
     Mercado Pago y es lo que permite verificar que el aviso vino de ellos.

Mientras tanto hay un MODO SIMULADO (MP_MODO_SIMULADO=true) que permite
recorrer el flujo entero sin cuenta: crea la preferencia, devuelve una URL
falsa, y deja que el webhook se dispare a mano. Sirve para desarrollar la
PWA; NUNCA para producción, y el propio módulo se niega a activarlo si
detecta que hay un token real configurado.


LAS TRES REGLAS QUE HACEN QUE UN COBRO NO SE ROMPA
==================================================

1. EL PAGO NACE PENDIENTE, NO CONFIRMADO.

   Que el socio haya apretado "pagar" no significa que la plata llegó.
   Crear el Pago como CONFIRMADO y corregirlo después significa que, entre
   medio, el sistema cree que cobró algo que quizá nunca cobró — y con eso
   ya le extendió la membresía. Se confirma cuando Mercado Pago lo dice.

2. EL MONTO NUNCA VIENE DEL CLIENTE, Y TAMPOCO DEL WEBHOOK.

   Del cliente es obvio: cualquiera con la consola abierta pagaría $1 una
   cuota de $30.000. Pero el webhook TAMPOCO es fuente confiable: llega por
   HTTP y el cuerpo lo puede escribir cualquiera que conozca la URL. Por eso
   el webhook sólo trae un ID, y el monto se relee consultándole a Mercado
   Pago con nuestro token.

3. EL WEBHOOK TIENE QUE SER IDEMPOTENTE.

   Mercado Pago REINTENTA si no contesta 200 rápido, y manda el mismo aviso
   más de una vez por diseño. Sin idempotencia, un pago se acreditaría dos
   veces y la membresía se extendería el doble.

   Acá la idempotencia no depende de que el código se acuerde: se apoya en
   que `Pago.numero_comprobante` es UNIQUE en el esquema. Se guarda ahí el
   id del pago de Mercado Pago, así que el segundo intento choca contra la
   base. Una defensa que vive en el esquema no se puede olvidar de aplicar.
"""

import hashlib
import hmac
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN", "").strip()
MP_WEBHOOK_SECRET = os.getenv("MP_WEBHOOK_SECRET", "").strip()

# A dónde vuelve el socio después de pagar, y a dónde nos avisa Mercado Pago.
# Son distintas: la primera es del NAVEGADOR del socio (puede ser localhost),
# la segunda la llama Mercado Pago desde internet y tiene que ser pública.
MP_URL_RETORNO = os.getenv("MP_URL_RETORNO", "http://localhost:5173/mi-cuota").strip()
MP_URL_WEBHOOK = os.getenv("MP_URL_WEBHOOK", "").strip()

API = "https://api.mercadopago.com"
TIMEOUT = 15


def _simulado_pedido() -> bool:
    return os.getenv("MP_MODO_SIMULADO", "").strip().lower() in ("1", "true", "si", "sí")


def modo_simulado() -> bool:
    """
    Si el flujo corre sin hablar con Mercado Pago.

    Se niega a activarse cuando hay un token real cargado. El escenario que
    esto evita es concreto: alguien deja MP_MODO_SIMULADO=true en el .env de
    producción por olvido, y el sistema empieza a dar por pagadas cuotas que
    nadie pagó. Ante la duda, gana el token.
    """
    return _simulado_pedido() and not MP_ACCESS_TOKEN


def esta_configurado() -> bool:
    return bool(MP_ACCESS_TOKEN) or modo_simulado()


def por_que_no_esta_configurado() -> str:
    """El motivo, en un texto que sirva para arreglarlo."""
    if _simulado_pedido() and MP_ACCESS_TOKEN:
        return ("MP_MODO_SIMULADO está en true pero también hay un "
                "MP_ACCESS_TOKEN cargado. El simulado se ignora a propósito: "
                "vaciá el token para simular, o sacá la bandera para cobrar "
                "de verdad.")
    if not MP_ACCESS_TOKEN:
        return ("Falta MP_ACCESS_TOKEN en el .env. Se saca del panel de "
                "Mercado Pago (Tus integraciones → Credenciales). El de "
                "prueba alcanza para desarrollar.")
    return ""


# =============================================================================
# RESPUESTAS
# =============================================================================

@dataclass
class Preferencia:
    """
    Lo que hay que devolverle a la app para que el socio pueda pagar.

    `init_point` es la URL del checkout: la app redirige ahí y Mercado Pago
    se encarga del formulario de tarjeta. Nosotros NUNCA vemos ni tocamos los
    datos de la tarjeta, y eso no es una comodidad — es lo que evita que el
    sistema tenga que cumplir PCI-DSS.
    """
    id_preferencia: str
    init_point: str
    simulada: bool = False


@dataclass
class PagoExterno:
    """El estado de un pago según Mercado Pago, ya normalizado."""
    id_pago_mp: str
    estado_mp: str
    id_pago_interno: int | None
    monto: float
    detalle: str = ""


# Cómo se traduce el estado de Mercado Pago al enum del esquema.
#
# `in_process` y `pending` NO son CONFIRMADO: son "todavía no se sabe". Un
# pago en revisión puede terminar rechazado, y darlo por bueno mientras tanto
# le extendería la membresía a alguien que no pagó.
ESTADOS = {
    "approved": "CONFIRMADO",
    "authorized": "PENDIENTE",
    "in_process": "PENDIENTE",
    "in_mediation": "PENDIENTE",
    "pending": "PENDIENTE",
    "rejected": "CANCELADO",
    "cancelled": "CANCELADO",
    "refunded": "REEMBOLSADO",
    "charged_back": "REEMBOLSADO",
}


def _llamar(metodo: str, ruta: str, cuerpo: dict | None = None) -> dict:
    """
    Una llamada a la API de Mercado Pago. Nunca lanza: devuelve el error.

    Igual que notificaciones.py: que Mercado Pago esté caído no puede tumbar
    la operación que lo disparó. Quien llama mira `error` y decide.
    """
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    pedido = urllib.request.Request(
        f"{API}{ruta}",
        data=datos,
        method=metodo,
        headers={
            "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(pedido, timeout=TIMEOUT) as r:
            return {"ok": True, "data": json.loads(r.read())}
    except urllib.error.HTTPError as e:
        try:
            detalle = json.loads(e.read()).get("message", str(e))
        except Exception:  # noqa: BLE001
            detalle = str(e)
        return {"ok": False, "error": f"Mercado Pago respondió {e.code}: {detalle}"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"No se pudo contactar a Mercado Pago: {e}"}


# =============================================================================
# CREAR EL CHECKOUT
# =============================================================================

def crear_preferencia(id_pago: int, descripcion: str, monto: float,
                       email_socio: str | None = None) -> dict:
    """
    Arma el checkout para un Pago que YA existe en la base, en PENDIENTE.

    El orden importa: primero se crea el Pago local y recién después la
    preferencia. Así el `external_reference` que viaja a Mercado Pago es
    nuestro id_pago, y cuando el webhook vuelva sabemos exactamente qué fila
    actualizar. Al revés —preferencia primero— habría un instante en que
    Mercado Pago conoce un cobro que nuestra base no, y si el proceso muere
    ahí el socio paga algo que no existe de este lado.
    """
    if modo_simulado():
        return {
            "ok": True,
            "data": Preferencia(
                id_preferencia=f"SIMULADA-{id_pago}",
                # Apunta a nuestro propio endpoint de simulación, no a
                # Mercado Pago: así el flujo se puede recorrer entero sin
                # cuenta y sin internet.
                init_point=f"{MP_URL_RETORNO}?simulado=1&pago={id_pago}",
                simulada=True,
            ),
        }

    if not MP_ACCESS_TOKEN:
        return {"ok": False, "error": por_que_no_esta_configurado()}

    cuerpo = {
        "items": [{
            "title": descripcion,
            "quantity": 1,
            "unit_price": float(monto),
            "currency_id": "ARS",
        }],
        # Nuestro id de Pago. Es lo que ata el aviso de Mercado Pago a la
        # fila que hay que actualizar.
        "external_reference": str(id_pago),
        "back_urls": {
            "success": MP_URL_RETORNO,
            "pending": MP_URL_RETORNO,
            "failure": MP_URL_RETORNO,
        },
        # Sin esto, alguien podría pagar en cuotas una cuota mensual y el
        # gimnasio cobraría con descuento sin saberlo. Se deja explícito.
        "payment_methods": {"installments": 1},
    }
    if MP_URL_WEBHOOK:
        cuerpo["notification_url"] = MP_URL_WEBHOOK
    if email_socio:
        cuerpo["payer"] = {"email": email_socio}

    r = _llamar("POST", "/checkout/preferences", cuerpo)
    if not r["ok"]:
        return r

    d = r["data"]
    return {
        "ok": True,
        "data": Preferencia(
            id_preferencia=d.get("id", ""),
            # `init_point` es producción y `sandbox_init_point` es prueba. Se
            # prefiere el de sandbox cuando existe: si el token es de prueba,
            # el otro no funciona.
            init_point=d.get("sandbox_init_point") or d.get("init_point", ""),
        ),
    }


# =============================================================================
# EL AVISO QUE MANDA MERCADO PAGO
# =============================================================================

def verificar_firma(x_signature: str, x_request_id: str, data_id: str) -> bool:
    """
    ¿El aviso vino realmente de Mercado Pago?

    La URL del webhook es pública: cualquiera que la descubra puede hacerle
    un POST diciendo "el pago 123 está aprobado". Sin esta verificación,
    acreditar cuotas gratis sería cuestión de adivinar un número.

    Mercado Pago manda una cabecera `x-signature: ts=...,v1=...` y la firma
    se calcula sobre un texto armado con el id, el request-id y el timestamp.
    Se compara con compare_digest y no con `==` para no filtrar información
    por el tiempo que tarda la comparación.

    Si no hay secreto configurado devuelve False: preferir rechazar todo
    antes que aceptar todo. Un webhook sin verificar es una puerta abierta.
    """
    if not MP_WEBHOOK_SECRET or not x_signature:
        return False

    partes = dict(
        p.strip().split("=", 1)
        for p in x_signature.split(",")
        if "=" in p
    )
    ts = partes.get("ts", "")
    firma = partes.get("v1", "")
    if not ts or not firma:
        return False

    manifiesto = f"id:{data_id};request-id:{x_request_id};ts:{ts};"
    esperada = hmac.new(
        MP_WEBHOOK_SECRET.encode(),
        manifiesto.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(esperada, firma)


def consultar_pago(id_pago_mp: str) -> dict:
    """
    Le pregunta a Mercado Pago cómo terminó un pago.

    SE CONSULTA aunque el webhook ya traiga el estado en el cuerpo, y esa es
    la parte importante: el cuerpo del webhook llega por HTTP y lo puede
    escribir cualquiera. Lo único que se le cree al aviso es el ID; el resto
    —el estado y sobre todo el MONTO— se relee con nuestro token, que nadie
    más tiene.
    """
    if modo_simulado():
        return {"ok": False, "error": "En modo simulado no se consulta a Mercado Pago."}

    r = _llamar("GET", f"/v1/payments/{id_pago_mp}")
    if not r["ok"]:
        return r

    d = r["data"]
    referencia = d.get("external_reference")
    return {
        "ok": True,
        "data": PagoExterno(
            id_pago_mp=str(d.get("id", id_pago_mp)),
            estado_mp=d.get("status", "pending"),
            id_pago_interno=int(referencia) if referencia and referencia.isdigit() else None,
            monto=float(d.get("transaction_amount") or 0),
            detalle=d.get("status_detail", ""),
        ),
    }


def estado_interno(estado_mp: str) -> str:
    """Traduce el estado de Mercado Pago al enum del esquema."""
    return ESTADOS.get(estado_mp, "PENDIENTE")
