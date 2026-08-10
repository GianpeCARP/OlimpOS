"""
cookies.py
----------
Configuración de las cookies de sesión y helpers para setearlas/borrarlas.

POR QUÉ COOKIES Y NO SOLO UN TOKEN EN JAVASCRIPT
------------------------------------------------
Un token que JavaScript puede leer —esté en localStorage, sessionStorage o en
una variable— es robable con un XSS: alcanza con que un script inyectado lo
lea y lo mande a otro lado. Una cookie `httponly` NO es visible para
JavaScript, así que ni siquiera un XSS puede exfiltrarla; el atacante podría
disparar pedidos desde la página de la víctima, pero no llevarse la sesión
para usarla en otro momento y desde otra máquina.

El precio de las cookies es que el navegador las manda SOLAS en cada pedido a
este dominio, incluso cuando el pedido lo originó otro sitio. Eso es
exactamente el ataque CSRF, y por eso las cookies obligan a la defensa que
implementa csrf.py. No es opcional: cookie sin CSRF es peor que token en
localStorage.

MODO DUAL, Y POR QUÉ NO ES UNA INCONSISTENCIA
---------------------------------------------
La API atiende a dos clientes muy distintos:

  - La PWA corre en un navegador. Tiene el problema del XSS y el del CSRF.
    Va con cookie httpOnly + token CSRF.

  - La app Flet es de escritorio. No es un navegador: no hay "otro sitio" que
    pueda hacerle disparar pedidos, y nadie puede inyectarle un script en una
    página que no existe. Sigue con `Authorization: Bearer`.

Darle cookies a Flet no agregaría ninguna seguridad y le sumaría la
complejidad del CSRF sin motivo. Cada cliente usa el mecanismo que resuelve
SUS amenazas — eso es diseño, no inconsistencia.
"""

import os

from dotenv import load_dotenv
from fastapi import Response

load_dotenv()

# Cookie con el JWT. httponly: JavaScript no la ve.
COOKIE_SESION = "olimpos_session"

# Cookie con el token CSRF. Esta SÍ la lee JavaScript a propósito — la PWA
# tiene que poder copiarla al header X-CSRF-Token (ver csrf.py). Que sea
# legible no la debilita: lo que la hace funcionar es que un sitio atacante no
# puede leer cookies de OTRO dominio, así que no puede armar el header.
COOKIE_CSRF = "olimpos_csrf"


def _bool_env(nombre: str, default: bool) -> bool:
    valor = os.getenv(nombre)
    if valor is None:
        return default
    return valor.strip().lower() in ("1", "true", "yes", "si", "sí")


# Secure=True hace que el navegador mande la cookie SOLO por HTTPS. En
# producción es obligatorio: sin eso, la sesión viaja en texto plano por la
# red y cualquiera en el mismo WiFi la lee. En desarrollo sobre http://
# localhost hay que apagarlo o el navegador nunca manda la cookie.
COOKIE_SECURE = _bool_env("COOKIE_SECURE", False)

# SameSite=lax: el navegador NO manda la cookie en pedidos POST originados por
# otro sitio. Ya frena la mayor parte del CSRF por sí solo; el token de
# csrf.py es la segunda capa, para los casos que lax no cubre y para no
# depender de que todos los navegadores se comporten igual.
#
# 'strict' sería más duro pero rompe algo útil: al llegar desde un link
# externo, el primer pedido va sin cookie y el usuario aparece deslogueado.
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax")

# Segundos que vive la cookie. Se alinea con la expiración del JWT: que la
# cookie sobreviva al token solo lograría que el usuario "parezca" logueado
# hasta que el primer pedido falle con 401.
COOKIE_MAX_AGE = int(os.getenv("JWT_EXPIRACION_MINUTOS", "480")) * 60


def setear_cookies_sesion(respuesta: Response, token: str, csrf: str) -> None:
    """Escribe las dos cookies de la sesión en la respuesta del login."""
    respuesta.set_cookie(
        key=COOKIE_SESION,
        value=token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,          # invisible para JavaScript
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
    )
    respuesta.set_cookie(
        key=COOKIE_CSRF,
        value=csrf,
        max_age=COOKIE_MAX_AGE,
        httponly=False,         # la PWA tiene que leerla para armar el header
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
    )


def borrar_cookies_sesion(respuesta: Response) -> None:
    """
    Borra las dos cookies. Los flags tienen que coincidir con los del
    set_cookie o el navegador considera que son cookies distintas y deja la
    vieja viva — un logout que no desloguea.
    """
    for nombre in (COOKIE_SESION, COOKIE_CSRF):
        respuesta.delete_cookie(
            key=nombre,
            path="/",
            secure=COOKIE_SECURE,
            samesite=COOKIE_SAMESITE,
        )
