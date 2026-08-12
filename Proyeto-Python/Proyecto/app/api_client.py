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


# =============================================================================
# SOCIOS
# =============================================================================

def obtener_socios() -> dict:
    return _get("/socios")


def obtener_socio(id_socio: int) -> dict:
    return _get(f"/socios/{id_socio}")


def alta_socio(datos: dict) -> dict:
    return _post("/socios", datos)


def editar_socio(id_socio: int, datos: dict) -> dict:
    return _put(f"/socios/{id_socio}", datos)


def dar_de_baja_socio(id_socio: int, tipo: str = "VOLUNTARIA", motivo: str | None = None) -> dict:
    return _post(f"/socios/{id_socio}/baja", {"tipo": tipo, "motivo": motivo})


def reactivar_socio(id_socio: int) -> dict:
    return _post(f"/socios/{id_socio}/reactivar")


# =============================================================================
# PERSONAL
# =============================================================================

def obtener_personal() -> dict:
    return _get("/personal")


def obtener_entrenadores() -> dict:
    return _get("/personal/entrenadores")


def obtener_nutricionistas() -> dict:
    return _get("/personal/nutricionistas")


def editar_empleado(id_empleado: int, datos: dict) -> dict:
    return _put(f"/personal/{id_empleado}", datos)


def alta_empleado(datos: dict) -> dict:
    return _post("/personal", datos)


# =============================================================================
# RUTINAS
# =============================================================================

def obtener_rutinas() -> dict:
    return _get("/rutinas")


def obtener_rutina(id_rutina: int) -> dict:
    return _get(f"/rutinas/{id_rutina}")


def obtener_ejercicios() -> dict:
    return _get("/rutinas/ejercicios")


def crear_rutina(datos: dict) -> dict:
    return _post("/rutinas", datos)


def asignar_rutina(id_rutina: int, id_socio: int) -> dict:
    return _post(f"/rutinas/{id_rutina}/asignar", {"id_socio": id_socio})


# =============================================================================
# NUTRICIÓN
# =============================================================================

def obtener_dietas() -> dict:
    return _get("/nutricion")


def obtener_dieta(id_dieta: int) -> dict:
    return _get(f"/nutricion/{id_dieta}")


def crear_dieta(datos: dict) -> dict:
    return _post("/nutricion", datos)


def asignar_dieta(id_dieta: int, id_socio: int) -> dict:
    return _post(f"/nutricion/{id_dieta}/asignar", {"id_socio": id_socio})


# =============================================================================
# COBROS
# =============================================================================

def obtener_tipos_membresia() -> dict:
    return _get("/cobros/tipos-membresia")


def obtener_estado_cuenta(id_socio: int) -> dict:
    return _get(f"/cobros/socio/{id_socio}")


def obtener_deudas() -> dict:
    return _get("/cobros/deudas")


def cobrar(datos: dict) -> dict:
    return _post("/cobros", datos)


def anular_pago(id_pago: int) -> dict:
    return _post(f"/cobros/pagos/{id_pago}/anular")


# =============================================================================
# ASISTENCIA
# =============================================================================

def obtener_asistencias_hoy() -> dict:
    return _get("/asistencia/hoy")


def fichar_rfid(codigo_rfid: str) -> dict:
    return _post("/asistencia/fichar", {"codigo_rfid": codigo_rfid})


def fichar_manual(id_socio: int) -> dict:
    return _post("/asistencia/fichar", {"id_socio": id_socio})


# =============================================================================
# ACTIVIDADES
# =============================================================================

def obtener_actividades() -> dict:
    return _get("/actividades")


def obtener_todos_los_profesores() -> dict:
    return _get("/actividades/profesores")


def obtener_profesores_de_actividad(id_actividad: int) -> dict:
    return _get(f"/actividades/{id_actividad}/profesores")


def crear_actividad(datos: dict) -> dict:
    return _post("/actividades", datos)


def editar_actividad(id_actividad: int, datos: dict) -> dict:
    return _put(f"/actividades/{id_actividad}", datos)


def cambiar_estado_actividad(id_actividad: int, activo: bool) -> dict:
    # El estado destino va explícito y no como toggle: con una pantalla
    # desactualizada, "dar de baja" sobre algo ya dado de baja lo reactivaría.
    return _post(f"/actividades/{id_actividad}/toggle-estado?activo={str(activo).lower()}")


def crear_plan_actividad(id_actividad: int, datos: dict) -> dict:
    return _post(f"/actividades/{id_actividad}/planes", datos)


def editar_plan_actividad(id_plan: int, datos: dict) -> dict:
    return _put(f"/actividades/planes/{id_plan}", datos)


def cambiar_estado_plan(id_plan: int, activo: bool) -> dict:
    return _post(f"/actividades/planes/{id_plan}/toggle-estado?activo={str(activo).lower()}")


def asignar_profesor(id_actividad: int, id_profesor: int) -> dict:
    return _post(f"/actividades/{id_actividad}/profesores/{id_profesor}")


def desasignar_profesor(id_actividad: int, id_profesor: int) -> dict:
    return _delete(f"/actividades/{id_actividad}/profesores/{id_profesor}")


def obtener_turnos(desde: str | None = None, hasta: str | None = None) -> dict:
    """Turnos de la grilla. Sin rango, el backend devuelve la semana que viene."""
    consulta = ""
    if desde and hasta:
        consulta = f"?desde={desde}&hasta={hasta}"
    return _get(f"/actividades/turnos{consulta}")


def puede_comprar(id_socio: int) -> dict:
    return _get(f"/actividades/socio/{id_socio}/puede-comprar")


def comprar_plan_actividad(id_plan: int, datos: dict) -> dict:
    return _post(f"/actividades/planes/{id_plan}/comprar", datos)


def comprar_clase_suelta(id_turno: int, datos: dict) -> dict:
    return _post(f"/actividades/turnos/{id_turno}/clase-suelta", datos)


# =============================================================================
# USUARIOS
# =============================================================================

def obtener_usuarios() -> dict:
    return _get("/usuarios")


def obtener_personas_sin_cuenta() -> dict:
    return _get("/usuarios/personas-sin-cuenta")


def crear_cuenta(id_persona: int) -> dict:
    return _post("/usuarios", {"id_persona": id_persona})


def resetear_password(id_usuario: int) -> dict:
    return _post(f"/usuarios/{id_usuario}/resetear-password")


def desbloquear_usuario(id_usuario: int) -> dict:
    return _post(f"/usuarios/{id_usuario}/desbloquear")


def cambiar_estado_usuario(id_usuario: int, activo: bool) -> dict:
    # Se manda siempre el destino, nunca "invertí lo que haya". La pantalla ya
    # sabe si está activando o desactivando; mandarlo hace que el resultado no
    # dependa de si la lista que se ve en pantalla sigue estando al día.
    return _post(f"/usuarios/{id_usuario}/toggle-estado?activo={str(activo).lower()}")


# =============================================================================
# DASHBOARD
# =============================================================================

def obtener_dashboard_stats() -> dict:
    return _get("/dashboard/stats")


def obtener_actividad_reciente() -> dict:
    return _get("/dashboard/actividad")


def obtener_socios_recientes() -> dict:
    return _get("/dashboard/socios-recientes")
