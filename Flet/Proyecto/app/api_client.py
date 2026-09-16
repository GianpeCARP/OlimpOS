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
import threading
import time

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
    """
    Se llama en el logout. Sin esto, la sesión siguiente heredaría el token.

    Tira también el cache de lecturas, y eso NO es opcional: las respuestas
    guardadas se trajeron con los permisos de la sesión que se está cerrando.
    Sin este borrado, un Recepcionista que entrara después del Dueño podría
    leer del cache una respuesta que a él el backend le habría negado.
    """
    global _token
    _token = None
    limpiar_cache()


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
    # El código viaja junto al mensaje porque hay fallos que la pantalla puede
    # OFRECER REINTENTAR y otros no: un 409 al fichar es "ya tiene un ingreso
    # hoy", y quien atiende puede confirmarlo. Sin el número, todos los
    # errores se ven iguales desde la vista y no queda forma de distinguirlos
    # que comparar el texto del mensaje, que cambia.
    return {"ok": False, "error": _mensaje_de_error(respuesta),
            "status": respuesta.status_code}


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


# =============================================================================
# CACHE DE LECTURAS  (servir-y-refrescar)
# =============================================================================
#
# LOS NUMEROS QUE JUSTIFICAN ESTO, medidos contra la base real:
#
#     SELECT 1 en una conexion ya abierta ......  44 ms   <- piso fisico (RTT)
#     Abrir una conexion NUEVA (TLS + auth) .... 825 ms
#     GET /socios completo (6 consultas) ....... 450 ms
#     GET /personal ............................ 570 ms
#
# La base esta en Neon, region sa-east-1. Esos 44 ms son la velocidad de la luz
# hasta Sao Paulo y no se pueden bajar desde el codigo: lo unico que se puede
# hacer es preguntar MENOS veces y NO ESPERAR la respuesta.
#
# POR QUE NO ALCANZABA EL CACHE CON TTL A SECAS
# =============================================
# La primera version guardaba la respuesta 15 segundos y despues la tiraba. El
# sintoma que dejaba es exactamente el que se reporto:
#
#     "si cambias entre paneles rapido cargan al toque, pero si esperas un rato
#      vuelve la tardanza, y a veces aparece de la nada"
#
# Claro: dentro de la ventana habia cache y era instantaneo; pasada la ventana
# se volvia a esperar los 450 ms completos. El cache escondia el problema en
# vez de resolverlo, y encima lo volvia impredecible — la misma accion tardaba
# distinto segun cuanto habias tardado vos en hacerla.
#
# COMO FUNCIONA AHORA
# ===================
# Se sirve SIEMPRE lo que hay en cache, al instante, aunque este vencido. Si
# esta vencido, ademas se dispara un refresco EN SEGUNDO PLANO que actualiza la
# entrada para la proxima vez. La pantalla nunca espera a la red: en el peor
# caso muestra datos de hace un minuto y se corrige sola.
#
#     primera visita  -> se espera (no hay nada que mostrar)
#     resto           -> instantaneo, siempre
#
# Es el patron "stale-while-revalidate" de HTTP, y encaja porque los datos de
# este sistema son de lectura frecuente y escritura rara: la grilla de socios
# se mira cien veces por cada vez que se da de alta a alguien.
#
# LO QUE ESCRIBE, INVALIDA TODO
# =============================
# Cualquier POST/PUT/DELETE borra el cache entero, no solo la ruta que toco. Es
# a proposito: cobrar una membresia cambia /socios (el estado del socio),
# /cobros/socio/{id}, /dashboard/stats y /cobros/deudas a la vez. Invalidar
# "solo lo relacionado" exigiria un mapa de dependencias entre rutas mantenido
# a mano, y el dia que alguien agregue un endpoint y se olvide de anotarlo, la
# pantalla mostraria un dato viejo DESPUES de cobrar — que es el unico momento
# en que un dato viejo es inaceptable. Tirar todo cuesta un pedido de mas y no
# se puede olvidar.
#
# Por eso tambien el refresco en segundo plano NO pisa una entrada si mientras
# tanto hubo una escritura: se compara la "generacion" del cache.

# Cuanto tarda una entrada en considerarse vieja. Pasado esto se sigue
# sirviendo igual, pero se refresca por atras.
FRESCURA = 30

_cache: dict[str, tuple[float, dict]] = {}
_refrescando: set[str] = set()
_candado = threading.Lock()

# Sube en cada escritura y en cada logout. Un refresco en vuelo que termina
# despues de una escritura descarta su resultado en vez de resucitar un dato
# viejo.
_generacion = 0


def limpiar_cache() -> None:
    """
    Tira el cache entero. La llaman todas las escrituras y el logout.

    Sube la generacion para que los refrescos que ya estaban en vuelo no
    escriban su resultado: salieron antes del cambio, asi que traen datos
    anteriores.
    """
    global _generacion
    with _candado:
        _cache.clear()
        _generacion += 1


def _refrescar_en_segundo_plano(path: str, generacion: int) -> None:
    """Vuelve a pedir `path` sin que nadie espere, y actualiza el cache."""
    try:
        respuesta = _pedir("GET", path)
        if not respuesta.get("ok"):
            return
        with _candado:
            # Si hubo una escritura mientras esto viajaba, lo que trae ya es
            # viejo: se descarta.
            if generacion == _generacion:
                _cache[path] = (time.monotonic(), respuesta)
    except Exception:  # noqa: BLE001
        # Un refresco que falla no es noticia: se sigue sirviendo lo que hay y
        # el proximo intento lo arregla. Propagar el error desde un hilo de
        # fondo mataria la app por algo que el usuario no pidio.
        pass
    finally:
        with _candado:
            _refrescando.discard(path)


def _get(path: str, cachear: bool = True, frescura: float | None = None) -> dict:
    """
    GET que devuelve al instante si ya se pidio antes.

    `cachear=False` para lo que no debe guardarse nunca. `frescura` para las
    rutas que envejecen mas rapido que el resto (el panel del mostrador).
    """
    if not cachear:
        return _pedir("GET", path)

    limite = FRESCURA if frescura is None else frescura

    with _candado:
        guardado = _cache.get(path)
        generacion = _generacion

    if guardado is not None:
        cuando, respuesta = guardado
        if time.monotonic() - cuando > limite:
            # Vencido: se devuelve igual y se refresca por atras. Un solo hilo
            # por ruta — sin este control, entrar y salir de un panel diez
            # veces dispararia diez pedidos identicos.
            with _candado:
                if path not in _refrescando:
                    _refrescando.add(path)
                    threading.Thread(
                        target=_refrescar_en_segundo_plano,
                        args=(path, generacion),
                        name=f"refrescar{path}",
                        daemon=True,
                    ).start()
        return respuesta

    # Primera vez: no hay nada que mostrar, hay que esperar.
    respuesta = _pedir("GET", path)
    # Solo se cachean las respuestas OK: cachear un error dejaria la pantalla
    # rota aunque el backend ya se hubiera recuperado.
    if respuesta.get("ok"):
        with _candado:
            if generacion == _generacion:
                _cache[path] = (time.monotonic(), respuesta)
    return respuesta


# Lo que se pide apenas alguien entra, en paralelo y sin que nadie espere.
#
# Con servir-y-refrescar, la unica pantalla que todavia se siente lenta es la
# PRIMERA que se abre de cada seccion: no hay nada en cache y hay que ir a
# buscarlo. Precargar mueve esa espera al momento del login —donde la persona
# ya esta esperando— y hace que la primera visita a cada panel tambien sea
# instantanea.
#
# Van en HILOS PARALELOS y no en serie: son ocho pedidos de ~400ms cada uno.
# En serie serian mas de tres segundos; en paralelo, lo que tarde el mas lento,
# porque el tiempo es de RED y no de CPU (por eso el GIL de Python no molesta
# acá: los hilos estan esperando el socket, no calculando).
#
# La lista es de rutas y no de funciones a proposito: si una ruta cambia de
# nombre, esto deja de precargarla y la app sigue andando igual, solo que un
# poco mas lenta la primera vez. Un error acá nunca debe impedir entrar.
RUTAS_A_PRECARGAR = (
    # Primero el panel del mostrador: es donde aterriza el Recepcionista, o sea
    # la primera pantalla que alguien ve al entrar en el caso mas comun.
    "/recepcion/panel",
    "/socios",
    "/personal",
    "/usuarios",
    "/rutinas",
    "/nutricion",
    "/cobros/tipos-membresia",
    "/dashboard/stats",
    "/dashboard/actividad",
    "/dashboard/socios-recientes",
    "/asistencia/hoy",
    "/promociones?solo_vigentes=true",
)


def precargar(rutas=RUTAS_A_PRECARGAR) -> None:
    """
    Pide en paralelo lo que las pantallas van a necesitar. No bloquea.

    Se llama despues del login. Cada pedido que falle (por permisos, por
    ejemplo: un Entrenador no puede ver /usuarios) simplemente no queda en
    cache — `_get` ya se encarga de no guardar respuestas con error, asi que
    un 403 acá no deja nada roto ni molesta a nadie.
    """
    for ruta in rutas:
        threading.Thread(
            target=_get,
            args=(ruta,),
            name=f"precarga{ruta}",
            daemon=True,
        ).start()


def _post(path: str, body: dict | None = None) -> dict:
    limpiar_cache()
    return _pedir("POST", path, body)


def _put(path: str, body: dict) -> dict:
    limpiar_cache()
    return _pedir("PUT", path, body)


def _delete(path: str) -> dict:
    limpiar_cache()
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


def anular_baja_socio(id_socio: int) -> dict:
    return _post(f"/socios/{id_socio}/anular-baja")


# --- Teléfonos de la ficha ---------------------------------------------------
# Van por endpoints propios y no como un campo más del PUT del socio: agregar
# un número no es editar la ficha, y no tiene por qué arrastrar nombre, email y
# objetivo en el mismo pedido (ver routers/socios.py).

def telefonos_de_socio(id_socio: int) -> dict:
    return _get(f"/socios/{id_socio}/telefonos")


def agregar_telefono(id_socio: int, datos: dict) -> dict:
    return _post(f"/socios/{id_socio}/telefonos", datos)


def editar_telefono(id_socio: int, id_telefono: int, datos: dict) -> dict:
    return _put(f"/socios/{id_socio}/telefonos/{id_telefono}", datos)


def borrar_telefono(id_socio: int, id_telefono: int) -> dict:
    return _delete(f"/socios/{id_socio}/telefonos/{id_telefono}")


# =============================================================================
# PERSONAL
# =============================================================================

def obtener_personal() -> dict:
    return _get("/personal")


def obtener_entrenadores() -> dict:
    return _get("/personal/entrenadores")


def obtener_nutricionistas() -> dict:
    return _get("/personal/nutricionistas")


def obtener_franjas() -> dict:
    # Catálogo de franjas laborales para el selector de turno del recepcionista.
    return _get("/personal/franjas")


def editar_empleado(id_empleado: int, datos: dict) -> dict:
    return _put(f"/personal/{id_empleado}", datos)


def alta_empleado(datos: dict) -> dict:
    return _post("/personal", datos)


def baja_empleado(id_empleado: int, motivo: str | None = None) -> dict:
    return _post(f"/personal/{id_empleado}/baja", {"motivo": motivo})


def reactivar_empleado(id_empleado: int) -> dict:
    return _post(f"/personal/{id_empleado}/reactivar")


# =============================================================================
# RUTINAS
# =============================================================================

def obtener_rutinas() -> dict:
    return _get("/rutinas")


def obtener_rutina(id_rutina: int) -> dict:
    return _get(f"/rutinas/{id_rutina}")


def obtener_ejercicios() -> dict:
    return _get("/rutinas/ejercicios")


def crear_ejercicio(datos: dict) -> dict:
    return _post("/rutinas/ejercicios", datos)


def crear_rutina(datos: dict) -> dict:
    return _post("/rutinas", datos)


def asignar_rutina(id_rutina: int, id_socio: int) -> dict:
    return _post(f"/rutinas/{id_rutina}/asignar", {"id_socio": id_socio})


def editar_rutina(id_rutina: int, datos: dict) -> dict:
    return _put(f"/rutinas/{id_rutina}", datos)


def baja_rutina(id_rutina: int) -> dict:
    return _post(f"/rutinas/{id_rutina}/baja")


def reactivar_rutina(id_rutina: int) -> dict:
    return _post(f"/rutinas/{id_rutina}/reactivar")


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


def editar_dieta(id_dieta: int, datos: dict) -> dict:
    return _put(f"/nutricion/{id_dieta}", datos)


def obtener_catalogo_comidas() -> dict:
    return _get("/nutricion/catalogo-comidas")


def crear_plato(datos: dict) -> dict:
    return _post("/nutricion/catalogo-comidas", datos)


def editar_usuario(id_usuario: int, username: str, email: str | None) -> dict:
    return _put(f"/usuarios/{id_usuario}", {"username": username, "email": email})


def baja_dieta(id_dieta: int) -> dict:
    return _post(f"/nutricion/{id_dieta}/baja")


def reactivar_dieta(id_dieta: int) -> dict:
    return _post(f"/nutricion/{id_dieta}/reactivar")


# =============================================================================
# COBROS
# =============================================================================

def obtener_tipos_membresia() -> dict:
    return _get("/cobros/tipos-membresia")


def obtener_estado_cuenta(id_socio: int) -> dict:
    return _get(f"/cobros/socio/{id_socio}")


def cobrar(datos: dict) -> dict:
    return _post("/cobros", datos)


def anular_pago(id_pago: int) -> dict:
    return _post(f"/cobros/pagos/{id_pago}/anular")


# =============================================================================
# ASISTENCIA
# =============================================================================

def obtener_asistencias_hoy() -> dict:
    return _get("/asistencia/hoy")


# El fichaje por tarjeta se retiró de las dos apps (ver views/asistencia.py):
# el gimnasio no tiene lector. El backend todavía acepta `codigo_rfid` para no
# romper los registros históricos, pero ya no se manda desde acá.

def fichar_manual(id_socio: int) -> dict:
    """
    Registra un ingreso. El backend NO rechaza el repetido: no hay tope diario
    ni anti-duplicado, y la respuesta trae `ingreso_numero` para marcarlo.
    """
    return _post("/asistencia/fichar", {"id_socio": id_socio})


def deshacer_fichaje(id_asistencia: int) -> dict:
    """Borra un ingreso mal cargado. El backend sólo deja los de hoy."""
    return _delete(f"/asistencia/{id_asistencia}")


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


def obtener_ingresos_por_periodo(escala: str = "dia") -> dict:
    """
    Ingresos agrupados por "dia", "mes" o "anio". Sólo para quien tiene
    verIngresos: a los demás el backend les contesta 403.

    No va en RUTAS_A_PRECARGAR a propósito: la precarga corre para cualquier
    rol, y para todos menos el Dueño esto sería un pedido que vuelve 403.
    """
    return _get(f"/dashboard/ingresos?escala={escala}")


# =============================================================================
# PANEL DE RECEPCIÓN
# =============================================================================

def obtener_panel_recepcion() -> dict:
    """
    El panel del mostrador.

    Cachea como el resto, pero con una frescura MUCHO mas corta: es la
    pantalla que se usa para decidir "a este lo dejo entrar", y los proximos
    turnos y quien acaba de fichar cambian mientras alguien la mira.

    La primera version de esto no cacheaba nada, y era el unico panel que
    seguia tardando medio segundo en abrir. Con servir-y-refrescar se abre al
    instante y el refresco de fondo la deja al dia en menos de un segundo, que
    para un mostrador es lo mismo que "en vivo". El boton de refrescar de la
    pantalla sigue estando para cuando alguien quiera forzarlo.
    """
    return _get("/recepcion/panel", frescura=5)


def obtener_turno_detalle(id_turno: int) -> dict:
    return _get(f"/recepcion/turnos/{id_turno}")


def cancelar_turno(id_turno: int, motivo: str) -> dict:
    """Cancela una clase puntual; el backend devuelve la clase a cada anotado."""
    from urllib.parse import quote
    return _post(f"/actividades/turnos/{id_turno}/cancelar?motivo={quote(motivo)}")


def buscar_por_dni(dni: str) -> dict:
    return _get(f"/recepcion/buscar?dni={dni}")


def obtener_horarios() -> dict:
    return _get("/actividades/horarios")


def crear_horario(datos: dict) -> dict:
    return _post("/actividades/horarios", datos)


def cambiar_estado_horario(id_horario: int, activo: bool) -> dict:
    return _post(f"/actividades/horarios/{id_horario}/estado?activo={str(activo).lower()}")


def generar_turnos() -> dict:
    return _post("/actividades/turnos/generar")


# =============================================================================
# ENTRENADOR A CARGO
# =============================================================================

def obtener_entrenadores_de_socio(id_socio: int, solo_activos: bool = False) -> dict:
    sufijo = "?solo_activos=true" if solo_activos else ""
    return _get(f"/socios/{id_socio}/entrenadores{sufijo}")


def asignar_entrenador(id_socio: int, id_entrenador: int) -> dict:
    return _post(f"/socios/{id_socio}/entrenadores", {"id_entrenador": id_entrenador})


def finalizar_asignacion_entrenador(id_asignacion: int) -> dict:
    return _post(f"/socios/entrenadores/asignaciones/{id_asignacion}/finalizar")


# =============================================================================
# HISTORIAL MÉDICO
# =============================================================================
#
# Estos endpoints NO cuelgan de la sección Socios aunque tres de las cinco
# rutas empiecen con /socios. El backend los puso en su propio router porque
# el guard es distinto: `VER_HISTORIAL_MEDICO`, la única acción donde el
# Recepcionista queda por debajo del Entrenador y del Nutricionista.
#
# Importa para la vista: el mostrador entra a Socios con acceso TOTAL, así que
# no alcanza con haber llegado a la pantalla para mostrar el botón. Hay que
# preguntar por la acción, no por la sección.

def obtener_catalogo_patologias() -> dict:
    return _get("/patologias")


def crear_patologia(nombre: str, descripcion: str | None = None) -> dict:
    return _post("/patologias", {"nombre": nombre, "descripcion": descripcion})


def obtener_patologias_de_socio(id_socio: int) -> dict:
    return _get(f"/socios/{id_socio}/patologias")


def asignar_patologia(id_socio: int, datos: dict) -> dict:
    return _post(f"/socios/{id_socio}/patologias", datos)


def editar_patologia_de_socio(id_socio: int, id_patologia: int, datos: dict) -> dict:
    # El PUT pide el cuerpo completo de AsignarPatologiaRequest, `id_patologia`
    # incluido, aunque ya venga en la URL. Mandarlo igual y no armar un cuerpo
    # parcial: Pydantic lo exige y sin él vuelve un 422.
    return _put(f"/socios/{id_socio}/patologias/{id_patologia}", datos)


def quitar_patologia(id_socio: int, id_patologia: int) -> dict:
    return _delete(f"/socios/{id_socio}/patologias/{id_patologia}")


# =============================================================================
# PROMOCIONES
# =============================================================================
#
# Descuentos sobre el precio de lista. Dos permisos distintos y la diferencia
# es el punto:
#
#     crear / editar / dar de baja  ->  Accion.GESTION_PROMOCIONES (solo Dueño)
#     listar                        ->  Seccion.COBROS (+ Recepcionista)
#
# Definir un descuento es una decisión de negocio; aplicarlo al cobrar es
# operativo. El Recepcionista tiene que poder VER las vigentes —si no, no puede
# elegir ninguna en el mostrador— pero no inventarlas.
#
# EL DESCUENTO NO SE CALCULA ACÁ. Para saber cuánto sale un plan con una promo
# se llama a `vista_previa_descuento`, que le pregunta al backend. Hacer la
# multiplicación del lado del cliente dejaría la fórmula —con su piso en cero y
# su redondeo— escrita en tres lugares: acá, en la PWA y en el backend.

def obtener_promociones(solo_vigentes: bool = False) -> dict:
    sufijo = "?solo_vigentes=true" if solo_vigentes else ""
    return _get(f"/promociones{sufijo}")


def crear_promocion(datos: dict) -> dict:
    return _post("/promociones", datos)


def editar_promocion(id_promocion: int, datos: dict) -> dict:
    return _put(f"/promociones/{id_promocion}", datos)


def dar_de_baja_promocion(id_promocion: int) -> dict:
    return _post(f"/promociones/{id_promocion}/baja")


def reactivar_promocion(id_promocion: int) -> dict:
    return _post(f"/promociones/{id_promocion}/reactivar")


def uso_de_promocion(id_promocion: int) -> dict:
    return _get(f"/promociones/{id_promocion}/uso")


def vista_previa_descuento(id_promocion: int, id_tipo_membresia: int) -> dict:
    return _get(f"/promociones/{id_promocion}/vista-previa"
                f"?id_tipo_membresia={id_tipo_membresia}")
