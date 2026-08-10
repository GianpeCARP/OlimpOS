"""
api_client.py — el único archivo de la app que habla HTTP
=========================================================
Concentra TODAS las llamadas a la API de OlimpOS. Ningún otro archivo importa
`requests`: las vistas hablan con state.py, y state.py habla con este módulo.

Por qué una capa entera para esto, y no `requests.post(...)` suelto en cada
pantalla: sin ella, las diez vistas repetirían la URL base, el manejo de
errores de red y el header del token. El día que cambie cualquiera de esas
tres cosas —y van a cambiar, la URL sin ir más lejos cuando esto salga de
127.0.0.1— habría que tocar diez archivos en vez de uno.

Todas las funciones devuelven SIEMPRE la misma forma:

    {"ok": True,  "data": <lo que respondió la API>}
    {"ok": False, "error": "<mensaje legible para mostrar en pantalla>"}

Nunca lanzan excepciones. Eso es deliberado: si el backend está apagado,
`requests` tira una excepción, y sin este try/except la app de escritorio se
cerraría de golpe apenas alguien apretara un botón. Convertirlo en un
diccionario hace que el peor caso sea un cartel rojo en pantalla.

Gemelo de `services/api.ts` en la PWA: mismo rol, mismo contrato.
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

# 127.0.0.1 y no localhost: en Windows, "localhost" puede resolver primero a
# ::1 (IPv6) mientras uvicorn escucha en IPv4, y la conexión falla con un
# timeout confuso que parece un backend caído.
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

# Segundos antes de dar por perdida una request. Bajo a propósito: es una app
# de escritorio y la ventana se congela mientras espera, así que es preferible
# un error rápido y accionable a una app trabada 30 segundos.
TIMEOUT = 10

# El token de la sesión vive en una variable de módulo y NO se escribe nunca
# en disco: al cerrar la app la sesión se pierde y hay que volver a entrar.
# Es lo correcto para una app que corre en la máquina compartida del mostrador
# del gimnasio, donde dejar la sesión abierta sería un problema.
_token: str | None = None


# =============================================================================
# TOKEN
# =============================================================================

def guardar_token(token: str) -> None:
    global _token
    _token = token


def limpiar_token() -> None:
    """Se llama en el logout. Sin esto, la sesión siguiente heredaría el token."""
    global _token
    _token = None


def hay_token() -> bool:
    return _token is not None


# Con este header la app le dice al backend que NO es un navegador. La
# consecuencia práctica: el login le devuelve el token en el cuerpo en vez de
# dejarlo en una cookie httponly.
#
# Por qué Flet no usa el esquema de cookies + CSRF que sí usa la PWA: esas dos
# defensas resuelven problemas que solo existen dentro de un navegador. La
# cookie httponly protege el token de un XSS —acá no hay páginas donde
# inyectar scripts— y el token CSRF protege de que otro sitio haga viajar
# nuestras cookies sin querer —acá no hay cookies ambiente ni "otro sitio".
# Sumarle esa maquinaria a una app de escritorio sería ceremonia sin
# beneficio. Cada cliente usa lo que resuelve SUS amenazas.
HEADERS_CLIENTE = {"X-Client-Type": "escritorio"}


def _headers() -> dict:
    cabeceras = dict(HEADERS_CLIENTE)
    if _token:
        cabeceras["Authorization"] = f"Bearer {_token}"
    return cabeceras


# =============================================================================
# INTERNOS
# =============================================================================

def _mensaje_de_error(respuesta) -> str:
    """
    Traduce el cuerpo de error de FastAPI a un texto mostrable.

    FastAPI usa dos formas distintas y hay que contemplar las dos:
      - Errores normales:    {"detail": "Usuario o contraseña incorrectos"}
      - Errores de Pydantic: {"detail": [{"msg": "...", "loc": [...]}, ...]}
    Sin este manejo, un 422 mostraría en pantalla la lista de diccionarios en
    crudo.
    """
    try:
        cuerpo = respuesta.json()
    except ValueError:
        return f"El servidor respondió algo inesperado (código {respuesta.status_code})."

    detalle = cuerpo.get("detail", "Ocurrió un error.")
    if isinstance(detalle, list):
        primero = detalle[0] if detalle else {}
        return primero.get("msg", "Los datos enviados no son válidos.")
    return str(detalle)


def _procesar(respuesta) -> dict:
    if respuesta.status_code in (200, 201):
        try:
            return {"ok": True, "data": respuesta.json()}
        except ValueError:
            return {"ok": True, "data": None}
    if respuesta.status_code == 204:
        return {"ok": True, "data": None}
    return {"ok": False, "error": _mensaje_de_error(respuesta)}


def _pedir(metodo: str, path: str, json_body: dict | None = None) -> dict:
    """
    Ejecuta la request y captura los fallos de red. Un solo lugar para los
    cuatro verbos: antes esto estaba repetido cuatro veces en el proyecto de
    referencia y las cuatro copias había que mantenerlas iguales a mano.
    """
    try:
        respuesta = requests.request(
            metodo, f"{API_URL}{path}",
            json=json_body, headers=_headers(), timeout=TIMEOUT,
        )
    except requests.exceptions.Timeout:
        return {"ok": False, "error": "El servidor tardó demasiado en responder."}
    except requests.exceptions.ConnectionError:
        return {"ok": False,
                "error": f"No se pudo conectar con el servidor ({API_URL}). "
                         "¿Está corriendo el backend?"}
    except requests.exceptions.RequestException:
        return {"ok": False, "error": "Error de red al contactar el servidor."}
    return _procesar(respuesta)


def _get(path: str) -> dict:
    return _pedir("GET", path)


def _post(path: str, body: dict | None = None) -> dict:
    return _pedir("POST", path, body)


def _put(path: str, body: dict) -> dict:
    return _pedir("PUT", path, body)


def _delete(path: str) -> dict:
    return _pedir("DELETE", path)


# =============================================================================
# AUTENTICACIÓN
# =============================================================================

def login(username: str, password: str) -> dict:
    """
    POST /login

    Ojo con la respuesta: un login correcto puede venir SIN token. Si la
    cuenta todavía tiene su contraseña temporal, la API devuelve 200 con
    {"debe_cambiar_password": true} y nada más. Quien llame tiene que mirar
    esa bandera antes de asumir que hay sesión — lo hace state.login().
    """
    return _post("/login", {"username": username, "password": password})


def cambiar_password(username: str, password_actual: str, password_nueva: str) -> dict:
    """
    POST /cambiar-password

    Endpoint público: quien lo necesita todavía no tiene token, porque el
    login se lo negó. Por eso manda el username explícito.
    """
    return _post("/cambiar-password", {
        "username": username,
        "password_actual": password_actual,
        "password_nueva": password_nueva,
    })


def estado_api() -> dict:
    """GET / — chequeo de que el backend está vivo. No requiere token."""
    return _get("/")
