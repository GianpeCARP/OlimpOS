"""
database.py
-----------
Conexión a PostgreSQL y fábrica de sesiones por request.

Hoy la base vive en Neon (PostgreSQL serverless) porque es lo que pide la
consigna. Mañana va a vivir en un servidor local del gimnasio. Ese cambio no
toca ni una línea de este archivo: lo único que cambia es DATABASE_URL en el
.env. Por eso la cadena se lee del entorno y no está escrita acá.

IMPORTANTE — quién manda sobre el esquema:
El esquema de OlimpOS ya existe escrito a mano y normalizado hasta 3FN en
`Proyecto/db/schema.sql` (35 tablas). Ese archivo es la ÚNICA fuente de
verdad de la estructura de la base, y es además parte de la entrega académica
(ver Normalización.pdf y olimpos_schema_v5.dbml).

Los modelos SQLAlchemy de models.py MAPEAN ese esquema, no lo definen. Es una
diferencia deliberada respecto del proyecto de referencia del profe, que crea
las tablas desde los modelos con Base.metadata.create_all(). Si acá hiciéramos
lo mismo, los modelos y el DDL entregado podrían divergir sin que nadie se
entere, y la base real dejaría de coincidir con el diagrama presentado.

create_all() se sigue llamando en el lifespan de main.py, pero como red de
seguridad, no como mecanismo de creación: SQLAlchemy solo crea tablas que no
existen y nunca modifica una existente, así que sobre una base ya cargada con
schema.sql es un no-op. La norma del profe (el sistema se auto-configura al
arrancar, sin intervención de un programador) se cumple igual.
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "Falta la variable DATABASE_URL. Copiá backend/.env.example a "
        "backend/.env y completá la cadena de conexión de Neon."
    )

# pool_pre_ping testea la conexión antes de entregarla. Sin esto, el tier
# gratuito de Neon —que duerme la base tras un rato de inactividad— devuelve
# conexiones muertas del pool y la primera request después de una pausa falla
# con un error de red confuso en vez de simplemente tardar un poco más.
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Una sesión por request: nunca compartir una sesión entre requests
# concurrentes, porque no son thread-safe y se pisan las transacciones.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    Dependencia de FastAPI: abre una sesión, la entrega al endpoint y la
    cierra siempre — incluso si el endpoint lanzó una excepción. Se usa como
    `db: Session = Depends(get_db)` y evita que cada endpoint tenga que
    acordarse de cerrarla a mano.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
