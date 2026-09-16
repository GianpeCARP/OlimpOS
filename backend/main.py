"""
main.py
-------
Punto de entrada de la API de OlimpOS. Una sola API para los dos frontends:
la PWA React que usan los socios y la app Flet que usa el personal.

Arranque:
    cd backend
    .\.venv\Scripts\Activate.ps1
    uvicorn main:app --reload

    API   -> http://127.0.0.1:8000
    Docs  -> http://127.0.0.1:8000/docs
"""

import threading
from datetime import date
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

import mercadopago as mp
from csrf import middleware_csrf
from sqlalchemy import text
from database import Base, SessionLocal, calentar_pool, engine
from seeder import ejecutar_seeder
from bajas import aplicar_bajas_vencidas
from turnos import generar_turnos
from videos import RUTA_HTTP, VIDEOS_DIR

# El import de models tiene que estar aunque no se use ninguno de sus nombres
# acá: es lo que registra las tablas en Base.metadata. Sin él, create_all no
# ve nada y el seeder falla al resolver las relaciones.
import models  # noqa: F401

load_dotenv()


def _origenes_cors() -> list[str]:
    """
    Orígenes permitidos, leídos del .env.

    Diferencia con el proyecto de referencia del profe, que deja
    allow_origins=["*"]: su único frontend es Flet de escritorio, que no es un
    navegador y por lo tanto no aplica CORS. Nuestra PWA sí corre en el
    navegador, así que acá la lista importa de verdad. Con "*" y
    allow_credentials=True cualquier página web podría hacerle pedidos
    autenticados a esta API desde el navegador de un usuario logueado.
    """
    crudo = os.getenv("CORS_ORIGINS", "")
    origenes = [o.strip() for o in crudo.split(",") if o.strip()]
    if not origenes:
        print("  AVISO: CORS_ORIGINS vacío en el .env. La PWA no va a poder")
        print("         llamar a la API desde el navegador.")
    return origenes


# =============================================================================
# LATIDO CONTRA LA SUSPENSIÓN DE NEON
# =============================================================================
#
# Neon (plan gratuito) SUSPENDE el compute tras unos minutos sin consultas, y
# despertarlo cuesta segundos. Sumado a los 825 ms que cuesta abrir una
# conexión nueva, es lo que hacía que la app estuviera rápida mientras se la
# usaba seguido y lenta al volver después de un rato — el sintoma exacto que
# se reportó: "a veces la tardanza aparece de la nada".
#
# Un `SELECT 1` cada dos minutos alcanza para las dos cosas: mantiene el
# compute despierto y hace que las conexiones del pool no queden ociosas el
# tiempo suficiente como para que alguien del otro lado las corte.
#
# POR QUÉ UN HILO Y NO UNA TAREA ASYNC: SQLAlchemy acá es SÍNCRONO. Meterlo en
# el event loop bloquearía el loop entero durante el RTT (~44 ms) cada dos
# minutos. Un hilo daemon no molesta a nadie y muere solo cuando el proceso
# termina, sin necesidad de cancelarlo.
#
# El costo es ridículo comparado con lo que evita: 30 consultas por hora contra
# despertar el compute en medio de un cobro.
SEGUNDOS_ENTRE_LATIDOS = 120

_latido_activo = threading.Event()


def _latido():
    """Mantiene despierto el compute de Neon y vivas las conexiones del pool."""
    ultimo_dia = None
    while not _latido_activo.wait(SEGUNDOS_ENTRE_LATIDOS):
        try:
            with engine.connect() as con:
                con.execute(text("SELECT 1"))
            # Una vez por día, las bajas programadas que ya corren (bajas.py).
            # Un backend que no se reinicia en semanas no puede depender del
            # arranque para aplicarlas.
            if ultimo_dia != date.today():
                db = SessionLocal()
                try:
                    aplicar_bajas_vencidas(db)
                    ultimo_dia = date.today()
                finally:
                    db.close()
        except Exception:  # noqa: BLE001
            # Que falle un latido no es noticia: puede ser un corte de red de
            # un segundo. El próximo lo vuelve a intentar, y si la base está
            # de verdad caída el usuario se entera por la pantalla, que es
            # donde corresponde. Un log acá por cada latido fallido llenaría
            # la consola de ruido durante un corte.
            pass


_DOCS_PUBLICOS = os.getenv("DOCS_PUBLICOS", "true").strip().lower() in ("1", "true", "si", "sí")

# HSTS sólo cuando la sesión ya viaja por HTTPS (COOKIE_SECURE=true): mandarlo
# sobre HTTP no sirve y, en un navegador que lo recuerde, rompería el
# desarrollo en localhost.
_HTTPS = os.getenv("COOKIE_SECURE", "false").strip().lower() == "true"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Se ejecuta una vez al arrancar, antes de atender el primer pedido.

    Los dos pasos son los que pide la consigna: verificar el esquema y
    asegurar que haya alguien que pueda entrar.
    """
    print("\n" + "=" * 68)
    print("OlimpOS API — arrancando")
    print("=" * 68)

    # Red de seguridad, NO el mecanismo de creación del esquema. La fuente de
    # verdad es db/schema.sql (41 tablas normalizadas, parte de la
    # entrega). create_all solo crea tablas que faltan y nunca modifica una
    # existente, así que sobre una base ya cargada esto es un no-op. Está para
    # que un arranque contra una base vacía no explote — y para cumplir la
    # norma del profe de que el sistema se auto-configure al arrancar.
    Base.metadata.create_all(bind=engine)

    # Abrir conexiones AHORA para que el primero que use la app no pague los
    # 825 ms del handshake TLS contra Neon. Ver database.calentar_pool.
    calentar_pool()

    # Y mantenerlas vivas mientras el backend esté arriba.
    threading.Thread(target=_latido, name="latido-neon", daemon=True).start()

    db = SessionLocal()
    try:
        ejecutar_seeder(db)

        # Los turnos de las próximas semanas, a partir de los horarios
        # semanales de cada actividad.
        #
        # Va acá y no en un cron porque el sistema no tiene dónde correr uno,
        # y porque la operación es idempotente: correrla en cada arranque no
        # duplica nada. Un gimnasio reinicia su servidor bastante más seguido
        # que cada cuatro semanas, así que con esto alcanza; y si no, el botón
        # de "Generar turnos" de la pantalla de Actividades hace lo mismo.
        #
        # Lo importante es que nadie tenga que cargar un turno a mano nunca
        # más: si el horario está declarado, las clases existen.
        aplicadas = aplicar_bajas_vencidas(db)
        if aplicadas:
            print(f"Bajas programadas aplicadas: {aplicadas}")

        resultado = generar_turnos(db)
        if resultado["creados"]:
            print(f"Turnos generados: {resultado['creados']} "
                  f"(hasta el {resultado['hasta'].strftime('%d/%m/%Y')})")

        # NO se generan deudas: el esquema definitivo eliminó la tabla Deuda.
        # La política es prepago y el estado "debe" es derivable (una membresía
        # vencida sin renovar), así que no hay nada que materializar acá.
    finally:
        db.close()

    # V-01: con el modo simulado, cualquier socio puede darse por pagada la
    # cuota. Existe para desarrollar sin Mercado Pago; que nadie lo deje
    # prendido sin enterarse.
    if mp.modo_simulado():
        print("  AVISO: MP_MODO_SIMULADO activo — los socios pueden acreditarse")
        print("         pagos sin pagar. NUNCA en producción.")

    print("=" * 68 + "\n")

    yield

    # Corta el latido al apagar: sin esto el hilo sigue consultando
    # mientras uvicorn intenta cerrar.
    _latido_activo.set()
    # (Nada que limpiar al apagar: el engine cierra su pool solo.)


app = FastAPI(
    title="OlimpOS API",
    description=(
        "Sistema de gestión de gimnasios. Una sola API para la PWA de socios "
        "y la app de escritorio del personal."
    ),
    version="0.1.0",
    lifespan=lifespan,
    # /docs, /redoc y /openapi.json exponen el mapa entero de la API a
    # cualquiera. En desarrollo sirven (y las verificaciones cuentan endpoints
    # con /openapi.json); en producción, DOCS_PUBLICOS=false.
    docs_url="/docs" if _DOCS_PUBLICOS else None,
    redoc_url="/redoc" if _DOCS_PUBLICOS else None,
    openapi_url="/openapi.json" if _DOCS_PUBLICOS else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origenes_cors(),
    # Imprescindible con cookies: sin esto el navegador no manda la cookie de
    # sesión en pedidos cross-origin, y la PWA (que corre en :5173 mientras la
    # API está en :8000) quedaría siempre deslogueada.
    #
    # Es también el motivo por el que allow_origins NUNCA puede ser ["*"]: la
    # combinación de comodín y credenciales está prohibida por la spec de CORS
    # justamente porque dejaría a cualquier sitio hacer pedidos autenticados.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# El middleware de CSRF va DESPUÉS del de CORS en el código, lo que en
# Starlette significa que se ejecuta ANTES en el pedido entrante (los
# middlewares se apilan en orden inverso). Es el orden que se quiere: rechazar
# un pedido sin token CSRF antes de que llegue a tocar la base.
app.middleware("http")(middleware_csrf)


@app.exception_handler(RequestValidationError)
async def errores_de_validacion(request, exc: RequestValidationError):
    """
    Los 422 devuelven sólo dónde y qué falló, SIN el valor recibido.

    V-05: FastAPI copia en la respuesta el `input` que no validó. Con
    `Infinity` o `NaN` (que el parser JSON acepta) esa copia no se puede
    serializar y el 422 correcto terminaba en un 500. De paso, no se le
    devuelve al cliente lo que mandó (una contraseña que no cumplía la regla,
    por ejemplo). Las dos apps sólo leen `msg`.
    """
    errores = [{"loc": list(e.get("loc", ())), "msg": e.get("msg", ""), "type": e.get("type", "")}
               for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errores})


@app.middleware("http")
async def cabeceras_de_seguridad(request, call_next):
    """
    Cabeceras de seguridad en TODAS las respuestas (antes no había ninguna).

    Va último en el código, así que envuelve a los demás middlewares y también
    marca los preflight de CORS y los rechazos del CSRF.

    La CSP es `default-src 'none'` porque la API sólo devuelve JSON y videos:
    no hay HTML propio que necesite cargar nada. /docs y /redoc quedan afuera
    porque Swagger trae sus scripts de un CDN (y en producción se apagan).

    `Server: uvicorn` no se puede sacar desde acá (lo agrega uvicorn después):
    en producción se arranca con `--no-server-header`.
    """
    respuesta = await call_next(request)
    h = respuesta.headers
    h.setdefault("X-Content-Type-Options", "nosniff")
    h.setdefault("X-Frame-Options", "DENY")
    h.setdefault("Referrer-Policy", "no-referrer")
    h.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if not request.url.path.startswith(("/docs", "/redoc")):
        h.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
    if _HTTPS:
        h.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return respuesta


# =============================================================================
# ROUTERS
# =============================================================================
# Van acá a medida que se escriben. Cada router se define en su propio archivo
# dentro de routers/ y se conecta con app.include_router(...). Olvidarse de
# esta línea es el error más común: los endpoints existen en el código pero la
# API responde 404, como si no se hubieran escrito nunca.
#
from routers import (  # noqa: E402  (tras crear `app`)
    actividades, asistencia, auth_router, cobros, dashboard, nutricion,
    pagos_online, patologias, personal, portal, promociones, recepcion, rutinas, socios,
    usuarios,
)

app.include_router(auth_router.router)
app.include_router(dashboard.router)
app.include_router(socios.router)
app.include_router(personal.router)
app.include_router(rutinas.router)
app.include_router(nutricion.router)
app.include_router(cobros.router)
app.include_router(asistencia.router)
app.include_router(recepcion.router)
app.include_router(actividades.router)
app.include_router(usuarios.router)
# Aparte de /socios: su guard es VER_HISTORIAL_MEDICO, que el
# Recepcionista NO tiene. Ver el docstring del modulo.
app.include_router(patologias.router)
app.include_router(promociones.router)
# El portal va último: son las rutas del socio, y tenerlas juntas al final de
# /docs deja claro que son un grupo aparte del resto (gestión).
app.include_router(portal.router)
# Fuera del prefijo /portal: el webhook lo llama Mercado Pago sin sesion.
app.include_router(pagos_online.router)


# =============================================================================
# VIDEOS TUTORIALES
# =============================================================================
# La carpeta donde demonio_videos.py deja los videos, servida por HTTP: el
# navegador no reproduce ftp://. StaticFiles responde pedidos por rango, que es
# lo que usa <video> para adelantar sin bajar el archivo entero. Sin sesión a
# propósito: son tutoriales del canal público del gimnasio. Ver videos.py.
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
app.mount(RUTA_HTTP, StaticFiles(directory=VIDEOS_DIR), name="videos")


@app.get("/", tags=["Salud"])
def estado():
    """Chequeo rápido de que la API está viva. No toca la base."""
    return {"status": "ok", "app": "OlimpOS API"}
