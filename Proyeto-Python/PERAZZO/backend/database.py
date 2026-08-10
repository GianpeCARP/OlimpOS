"""
database.py
------------
Configuración de la conexión a la base de datos PostgreSQL alojada en Neon.

Neon es un servicio de PostgreSQL serverless. La cadena de conexión (DATABASE_URL)
se obtiene desde el panel de Neon y debe incluir el parámetro `sslmode=require`,
ya que Neon exige conexiones cifradas.

Ejemplo de DATABASE_URL en el archivo .env:
DATABASE_URL=postgresql://usuario:password@ep-xxxx.us-east-2.aws.neon.tech/nombre_db?sslmode=require

SQLAlchemy usa esta URL para crear un "engine" (motor de conexión) y a partir
de él, una fábrica de sesiones (SessionLocal) que se inyecta en cada endpoint
mediante la dependencia get_db().
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Carga las variables definidas en el archivo .env al entorno del proceso
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "No se encontró la variable DATABASE_URL. "
        "Verificá que exista un archivo .env con la cadena de conexión de Neon."
    )

# El engine administra el pool de conexiones a PostgreSQL.
# pool_pre_ping=True evita errores cuando Neon "duerme" la base por inactividad
# (tier gratuito) y la conexión quedó obsoleta: SQLAlchemy la testea antes de usarla.
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# SessionLocal es una fábrica de sesiones: cada request de la API abre y cierra
# su propia sesión, evitando compartir conexiones entre requests concurrentes.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base es la clase de la que heredan todos los modelos ORM (Usuario, Persona, etc.)
Base = declarative_base()


def get_db():
    """
    Dependencia de FastAPI que provee una sesión de base de datos por request.
    Se usa con Depends(get_db) en los endpoints. Garantiza que la sesión
    se cierre siempre, incluso si ocurre una excepción.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
