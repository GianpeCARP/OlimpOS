"""
csrf.py
-------
Defensa contra CSRF (Cross-Site Request Forgery), con el patrón de doble
envío de cookie.

QUÉ ATAQUE FRENA
----------------
El navegador manda las cookies de este dominio SOLAS, en cada pedido, sin
importar quién lo originó. Entonces, si el dueño del gimnasio está logueado en
OlimpOS y abre otra pestaña con una página maliciosa, esa página puede hacer:

    <form action="https://olimpos/socios/7/baja" method="POST">
    <script>document.forms[0].submit()</script>

y el navegador adjunta la cookie de sesión. Para el backend es un pedido
perfectamente autenticado del dueño. Se da de baja un socio y nadie apretó
nada.

CÓMO LO FRENA
-------------
Al loguearse se emiten DOS cookies: la de sesión (httponly, invisible para
JavaScript) y una con un token CSRF aleatorio (legible). La PWA lee la
segunda y la copia al header `X-CSRF-Token` en cada pedido que modifica algo.
El backend exige que el header y la cookie coincidan.

El sitio atacante puede lograr que el navegador MANDE las cookies, pero no
puede LEERLAS: la política de mismo origen se lo impide. Sin poder leer el
token, no puede armar el header, y el pedido se rechaza.

POR QUÉ SOLO APLICA A LOS PEDIDOS CON COOKIE
--------------------------------------------
La app Flet se autentica con `Authorization: Bearer`, un header que ella misma
pone en cada pedido. No hay ninguna credencial ambiente que un tercero pueda
hacer viajar sin querer — que es la definición misma del CSRF. Exigirle un
token CSRF sería ceremonia sin beneficio.

Por eso el middleware mira si el pedido trae la cookie de sesión. Si viene por
header, pasa de largo.
"""

import secrets

from fastapi import Request, status
from fastapi.responses import JSONResponse

from cookies import COOKIE_CSRF, COOKIE_SESION

HEADER_CSRF = "X-CSRF-Token"

# GET, HEAD y OPTIONS no deberían modificar nada, así que no necesitan
# protección. Es la misma lista que usa cualquier framework, y descansa en una
# regla que el resto del código tiene que respetar: si algún día un GET
# escribe en la base, este middleware deja de protegerlo.
METODOS_SEGUROS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


def generar_token_csrf() -> str:
    """Token nuevo por sesión. 32 bytes de urandom: imposible de adivinar."""
    return secrets.token_urlsafe(32)


async def middleware_csrf(request: Request, call_next):
    """
    Se ejecuta antes que cualquier endpoint. Que sea middleware y no una
    dependencia es deliberado: una dependencia hay que acordarse de ponerla en
    cada endpoint nuevo, y el día que alguien se olvide, ese endpoint queda
    abierto sin que nada avise. Acá la protección es por defecto y no hay
    forma de saltearla por descuido.
    """
    if request.method in METODOS_SEGUROS:
        return await call_next(request)

    cookie_sesion = request.cookies.get(COOKIE_SESION)
    if not cookie_sesion:
        # Sin cookie de sesión no hay credencial ambiente que robar: o es un
        # cliente con Bearer (Flet), o un pedido sin autenticar como /login.
        # En los dos casos el CSRF no aplica.
        return await call_next(request)

    cookie_csrf = request.cookies.get(COOKIE_CSRF)
    header_csrf = request.headers.get(HEADER_CSRF)

    # compare_digest y no ==: comparar strings con == corta apenas encuentra
    # una diferencia, y ese tiempo distinto permite adivinar el token carácter
    # por carácter. compare_digest tarda lo mismo siempre.
    if not cookie_csrf or not header_csrf or not secrets.compare_digest(cookie_csrf, header_csrf):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "detail": "Token CSRF ausente o inválido. Volvé a iniciar sesión."
            },
        )

    return await call_next(request)
