"""
app/api_client.py
-------------------
Funciones puras que encapsulan todas las llamadas HTTP a la API de OlimpOS.
Ningún método de este archivo tiene lógica de negocio propia: solo arma
la request, la ejecuta y devuelve un resultado simple para que la capa
de estado (state.py) decida qué hacer con él.

Formato de retorno estándar de todas las funciones:
    {"ok": True,  "data": <lo que devolvió la API>}
    {"ok": False, "error": "<mensaje legible para mostrar al usuario>"}

El token JWT de la sesión activa se guarda en una variable de módulo
(_token) porque todas las llamadas autenticadas lo necesitan en el
header Authorization, y no tiene sentido pasarlo a mano en cada función
de cada vista.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

_token: str | None = None


# =============================================================================
# MANEJO DE TOKEN / HELPERS INTERNOS
# =============================================================================

def guardar_token(token: str) -> None:
    """Guarda el token JWT de la sesión activa para las próximas requests."""
    global _token
    _token = token


def limpiar_token() -> None:
    """Borra el token guardado. Se llama al hacer logout."""
    global _token
    _token = None


def _headers() -> dict:
    """Arma el header Authorization si hay una sesión activa."""
    if _token:
        return {"Authorization": f"Bearer {_token}"}
    return {}


def _extraer_mensaje_error(respuesta) -> str:
    """
    Convierte el cuerpo de error de FastAPI en un texto legible.
    FastAPI devuelve {"detail": "mensaje"} en errores normales, pero
    {"detail": [{"msg": "...", ...}, ...]} en errores de validación
    (ej. email con formato inválido) — hay que contemplar ambos casos.
    """
    try:
        cuerpo = respuesta.json()
    except ValueError:
        return "Error desconocido del servidor."

    detalle = cuerpo.get("detail", "Error desconocido.")
    if isinstance(detalle, list):
        # Error de validación de Pydantic: toma el primer mensaje
        primer_error = detalle[0] if detalle else {}
        return primer_error.get("msg", "Datos inválidos.")
    return detalle


def _procesar_respuesta(respuesta) -> dict:
    """Convierte una respuesta de requests en el formato {"ok", "data"/"error"} estándar."""
    if respuesta.status_code in (200, 201):
        try:
            return {"ok": True, "data": respuesta.json()}
        except ValueError:
            return {"ok": True, "data": None}
    if respuesta.status_code == 204:
        return {"ok": True, "data": None}

    return {"ok": False, "error": _extraer_mensaje_error(respuesta)}


def _get(path: str) -> dict:
    try:
        r = requests.get(f"{API_URL}{path}", headers=_headers(), timeout=10)
    except requests.exceptions.RequestException:
        return {"ok": False, "error": "No se pudo conectar con el servidor."}
    return _procesar_respuesta(r)


def _post(path: str, json_body: dict | None = None) -> dict:
    try:
        r = requests.post(f"{API_URL}{path}", json=json_body, headers=_headers(), timeout=10)
    except requests.exceptions.RequestException:
        return {"ok": False, "error": "No se pudo conectar con el servidor."}
    return _procesar_respuesta(r)


def _put(path: str, json_body: dict) -> dict:
    try:
        r = requests.put(f"{API_URL}{path}", json=json_body, headers=_headers(), timeout=10)
    except requests.exceptions.RequestException:
        return {"ok": False, "error": "No se pudo conectar con el servidor."}
    return _procesar_respuesta(r)


def _delete(path: str) -> dict:
    try:
        r = requests.delete(f"{API_URL}{path}", headers=_headers(), timeout=10)
    except requests.exceptions.RequestException:
        return {"ok": False, "error": "No se pudo conectar con el servidor."}
    return _procesar_respuesta(r)


# =============================================================================
# AUTENTICACIÓN
# =============================================================================

def login(email: str, password: str) -> dict:
    return _post("/login", {"email": email, "password": password})


def cambiar_password(email: str, password_actual: str, password_nueva: str) -> dict:
    return _post("/cambiar-password", {
        "email": email,
        "password_actual": password_actual,
        "password_nueva": password_nueva,
    })


# =============================================================================
# PERSONAS
# =============================================================================

def obtener_persona(dni: str) -> dict:
    return _get(f"/personas/{dni}")


def crear_persona(datos: dict) -> dict:
    return _post("/personas", datos)


def actualizar_persona(dni: str, datos: dict) -> dict:
    return _put(f"/personas/{dni}", datos)


# =============================================================================
# SOCIOS
# =============================================================================

def obtener_socios() -> dict:
    return _get("/socios")


def crear_socio(datos: dict) -> dict:
    return _post("/socios", datos)


def actualizar_socio(dni: str, datos: dict) -> dict:
    return _put(f"/socios/{dni}", datos)


def eliminar_socio(dni: str) -> dict:
    return _delete(f"/socios/{dni}")


# =============================================================================
# PERSONAL
# =============================================================================

def obtener_personal() -> dict:
    return _get("/personal")


def crear_empleado(datos: dict) -> dict:
    return _post("/personal", datos)


def actualizar_empleado(dni: str, datos: dict) -> dict:
    return _put(f"/personal/{dni}", datos)


# =============================================================================
# RUTINAS
# =============================================================================

def obtener_rutinas() -> dict:
    return _get("/rutinas")


def crear_rutina(datos: dict) -> dict:
    return _post("/rutinas", datos)


def asignar_rutina(rutina_id: int, socio_dni: str) -> dict:
    return _post(f"/rutinas/{rutina_id}/asignar/{socio_dni}")


# =============================================================================
# NUTRICIÓN
# =============================================================================

def obtener_planes_nutricion() -> dict:
    return _get("/nutricion")


def crear_plan_nutricion(datos: dict) -> dict:
    return _post("/nutricion", datos)


def asignar_plan_nutricion(plan_id: int, socio_dni: str) -> dict:
    return _post(f"/nutricion/{plan_id}/asignar/{socio_dni}")


# =============================================================================
# USUARIOS DEL SISTEMA
# =============================================================================

def obtener_usuarios() -> dict:
    return _get("/usuarios")


def crear_usuario(datos: dict) -> dict:
    return _post("/usuarios", datos)


def actualizar_usuario(usuario_id: int, datos: dict) -> dict:
    return _put(f"/usuarios/{usuario_id}", datos)


def resetear_password_usuario(usuario_id: int) -> dict:
    return _post(f"/usuarios/{usuario_id}/resetear-password")


def alternar_estado_usuario(usuario_id: int) -> dict:
    return _post(f"/usuarios/{usuario_id}/toggle-estado")


# =============================================================================
# TURNOS
# =============================================================================

def obtener_turnos() -> dict:
    return _get("/turnos")


def crear_turno(datos: dict) -> dict:
    return _post("/turnos", datos)


def actualizar_turno(turno_id: int, datos: dict) -> dict:
    return _put(f"/turnos/{turno_id}", datos)


def eliminar_turno(turno_id: int) -> dict:
    return _delete(f"/turnos/{turno_id}")


def inscribir_socio_turno(turno_id: int, socio_dni: str) -> dict:
    return _post(f"/turnos/{turno_id}/inscribir/{socio_dni}")


def quitar_inscripcion_turno(turno_id: int, socio_dni: str) -> dict:
    return _delete(f"/turnos/{turno_id}/inscribir/{socio_dni}")


# =============================================================================
# DASHBOARD
# =============================================================================

def obtener_dashboard_stats() -> dict:
    return _get("/dashboard/stats")


def obtener_actividad_reciente() -> dict:
    return _get("/dashboard/actividad")
