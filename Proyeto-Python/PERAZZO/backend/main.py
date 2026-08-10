"""
main.py (Backend)
------------------
Punto de entrada de la API completa de OlimpOS.

Cómo ejecutar:
    1) cd backend
    2) pip install -r requirements.txt
    3) Completar el archivo .env (ver .env.example) con la cadena de Neon
    4) uvicorn main:app --reload
    5) Documentación interactiva en http://127.0.0.1:8000/docs
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine, get_db
from seeder import ejecutar_seeder

from routers import auth_router, personas, socios, personal, rutinas, nutricion, usuarios, turnos, dashboard


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Se ejecuta una vez al arrancar el servidor.
    1. Crea las tablas en Neon si no existen.
    2. Ejecuta el seeder para garantizar que exista un usuario PROPIETARIO.
    """
    Base.metadata.create_all(bind=engine)

    db = next(get_db())
    try:
        ejecutar_seeder(db)
    finally:
        db.close()

    yield


app = FastAPI(title="Sistema de Gestión de Gimnasios — OlimpOS API", lifespan=lifespan)

# ── CORS ──────────────────────────────────────────────────────────────────────
# El frontend Flet corre como aplicación de escritorio (no un navegador), pero
# igual hace requests HTTP normales con la librería `requests`. Habilitar CORS
# no es estrictamente necesario para ese caso, pero se deja abierto para
# facilitar pruebas desde /docs o desde herramientas como Postman/Insomnia
# durante el desarrollo. En producción, conviene restringir `allow_origins`.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Registro de routers ───────────────────────────────────────────────────────
app.include_router(auth_router.router)
app.include_router(personas.router)
app.include_router(socios.router)
app.include_router(personal.router)
app.include_router(rutinas.router)
app.include_router(nutricion.router)
app.include_router(usuarios.router)
app.include_router(turnos.router)
app.include_router(dashboard.router)


@app.get("/", tags=["Salud"])
def estado():
    """Endpoint simple para chequear que la API está viva."""
    return {"status": "ok", "app": "OlimpOS API"}
