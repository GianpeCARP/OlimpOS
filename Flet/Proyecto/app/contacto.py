# =============================================================================
# contacto.py — cómo se le escribe a una persona desde el sistema
# =============================================================================
# Gemelo de `src/utils/contacto.ts` en la PWA: mismas reglas para armar un
# mailto: o un wa.me. Si cambiás una acá, mirá la otra — el mensaje que recibe
# el empleado tiene que ser el mismo salga de la app que salga.

import re
from urllib.parse import quote

# Prefijo internacional que se asume cuando el teléfono viene sin uno.
#
# El gimnasio está en Argentina y nadie carga "+54" a mano: en la base los
# números están como "3415551234". wa.me EXIGE el formato internacional
# completo y sin símbolos, así que hay que completarlo.
#
# El 9 del medio (54 *9* 341 …) es el que Argentina pide para celulares, y es
# el caso de todos los WhatsApp: una línea fija no tiene cuenta.
PREFIJO_INTERNACIONAL = "549"


def solo_digitos(telefono: str) -> str:
    """Deja sólo los dígitos: wa.me rechaza espacios, guiones y paréntesis."""
    return re.sub(r"\D", "", telefono or "")


def link_whatsapp(telefono: str, mensaje: str | None = None) -> str:
    """
    Link de WhatsApp con el mensaje ya escrito.

    LIMITACIÓN CONOCIDA: un número en notación local con el 15
    ("0341 15 555 1234") no se puede convertir de forma confiable — hay que
    sacar el 15 y poner el 9, y sin saber cuántos dígitos tiene la
    característica no se distingue el 15 del principio del abonado. Se saca el
    0 inicial, que sí es inequívoco; el resto va cargado sin el 15.
    """
    numero = solo_digitos(telefono)
    if numero.startswith("0"):
        numero = numero[1:]
    if not numero.startswith("54"):
        numero = PREFIJO_INTERNACIONAL + numero
    texto = f"?text={quote(mensaje)}" if mensaje else ""
    return f"https://wa.me/{numero}{texto}"


def link_mail(email: str, asunto: str | None = None, cuerpo: str | None = None) -> str:
    """Link de mail con asunto y cuerpo ya cargados."""
    partes = []
    if asunto:
        partes.append(f"subject={quote(asunto)}")
    if cuerpo:
        partes.append(f"body={quote(cuerpo)}")
    return f"mailto:{email}" + (("?" + "&".join(partes)) if partes else "")


def limpiar_telefono(valor: str) -> str:
    """
    Lo que se acepta tipear en un campo de teléfono.

    Espeja `_telefono_valido()` del backend (schemas.py). Filtrar mientras se
    escribe, en vez de avisar al guardar, es lo que evita el caso que reportó
    el gimnasio: el campo aceptaba letras y el error recién aparecía al mandar
    el formulario entero.
    """
    return re.sub(r"[^+()\-\s0-9]", "", valor or "")
