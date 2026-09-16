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
    if (telefono or "").strip().startswith("+"):
        # Con código de país (app/telefono.py) el número ya dice de dónde es.
        # Único ajuste, Argentina: WhatsApp exige el 9 de celular tras el 54.
        if numero.startswith("54") and not numero.startswith("549"):
            numero = "549" + numero[2:]
    else:
        # Cargado antes del selector de país: es argentino.
        if numero.startswith("0"):
            numero = numero[1:]
        if not numero.startswith("54"):
            numero = PREFIJO_INTERNACIONAL + numero
    texto = f"?text={quote(mensaje)}" if mensaje else ""
    return f"https://wa.me/{numero}{texto}"


# Base del redactor de Gmail en el navegador. `view=cm` es el modo redacción y
# `fs=1` lo abre en ventana completa en vez del recuadro chico de la esquina.
GMAIL_REDACTAR = "https://mail.google.com/mail/?view=cm&fs=1"


def link_mail(email: str, asunto: str | None = None, cuerpo: str | None = None) -> str:
    """
    Link para escribirle un mail a alguien, con asunto y cuerpo ya cargados.

    Va al REDACTOR DE GMAIL, no a un `mailto:`, y es a propósito. Un `mailto:`
    necesita que la máquina tenga un programa de correo asociado, y la PC de
    recepción no lo tiene: el botón no hacía absolutamente nada.

    El precio es que ata el botón a Gmail: quien lo use tiene que estar
    logueado en Google en ese navegador. Es el canje que se eligió — un botón
    que anda siempre contra uno que no andaba nunca.

    `page.launch_url()` con esto abre el navegador por defecto, igual que con
    cualquier otro https.
    """
    partes = [f"to={quote(email or '', safe='')}"]
    if asunto:
        partes.append(f"su={quote(asunto, safe='')}")
    if cuerpo:
        partes.append(f"body={quote(cuerpo, safe='')}")
    return GMAIL_REDACTAR + "&" + "&".join(partes)


def limpiar_telefono(valor: str) -> str:
    """
    Lo que se acepta tipear en un campo de teléfono.

    Espeja `_telefono_valido()` del backend (schemas.py). Filtrar mientras se
    escribe, en vez de avisar al guardar, es lo que evita el caso que reportó
    el gimnasio: el campo aceptaba letras y el error recién aparecía al mandar
    el formulario entero.
    """
    return re.sub(r"[^+()\-\s0-9]", "", valor or "")


# Asunto del mail de credenciales. Lo usan el alta de personal Y el reseteo de
# contraseña en Usuarios: vive acá y no en una de las dos vistas para que no
# haya dos copias que se desincronicen. Gemelo de ASUNTO_CREDENCIALES en
# components/PanelCredenciales.tsx de la PWA.
ASUNTO_CREDENCIALES = "Tus datos de acceso a OlimpOS"
