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
`db/schema.sql` (41 tablas). Ese archivo es la ÚNICA fuente de
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

# =============================================================================
# EL POOL — por qué está configurado así, con los números medidos
# =============================================================================
#
# La base está en Neon, región sa-east-1 (São Paulo). Medido desde acá:
#
#     SELECT 1 en una conexión YA abierta ......  44 ms   <- piso físico (RTT)
#     Abrir una conexión NUEVA (TLS + auth) .... 825 ms   <- 19x más caro
#
# Esos dos números explican todo el comportamiento de la app, y ninguno tiene
# que ver con Python: son la velocidad de la luz hasta São Paulo y el costo de
# un handshake TLS. Lo único que se puede hacer es (a) preguntar MENOS veces y
# (b) no tener que reconectar nunca.
#
# EL SÍNTOMA QUE ESTO ARREGLA
# --------------------------
# "Si cambio de panel rápido carga al toque, pero si espero un rato vuelve la
# tardanza, y a veces aparece de la nada."
#
# Es exactamente el perfil de una conexión que se muere sola. Con
# `pool_recycle=-1` (el default) SQLAlchemy no recicla nunca: deja las
# conexiones en el pool hasta que alguien del otro lado las cierra —Neon por
# inactividad, o el NAT del router por no ver tráfico—. Cuando eso pasa,
# `pool_pre_ping` detecta la conexión muerta y reconecta de forma transparente:
# la app no falla, pero esa request paga los 825 ms. Y como cada conexión del
# pool muere en un momento distinto, la lentitud aparece "de la nada".
#
# Las tres piezas, y qué resuelve cada una:
#
# 1. pool_recycle: se descartan a los 4 minutos, ANTES de que Neon las cierre
#    por su cuenta. Reciclar es barato cuando lo decidimos nosotros (pasa entre
#    requests) y caro cuando lo decide la red (pasa en medio de una).
#
# 2. keepalives de TCP: psycopg2 los pasa a libpq. Mandan un paquete cada 30s
#    sobre la conexión ociosa, que es lo que evita que el NAT la dé por muerta.
#    Sin esto, una conexión puede estar "viva" para nosotros y cortada para el
#    otro extremo — el caso más difícil de diagnosticar porque el error llega
#    recién al usarla.
#
# 3. pool_size más grande: el default (5) alcanza, pero cada conexión que se
#    abre de más cuesta 825 ms. Con 10 fijas y sin overflow, el pool se llena
#    una vez al arrancar y no vuelve a pagar ese precio.
#
# pool_pre_ping SE MANTIENE aunque cueste 1 RTT por checkout: es el seguro de
# que una conexión muerta nunca llegue como un error a la pantalla. Con las
# tres piezas de arriba, casi nunca tiene que hacer nada.
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=240,
    pool_size=10,
    max_overflow=5,
    # Sin esto el pool espera 30s (default) antes de fallar si está lleno.
    # Preferible enterarse rápido: si el pool se agota hay un problema de
    # conexiones que no se devuelven, y esconderlo 30 segundos no ayuda.
    pool_timeout=10,
    connect_args={
        # libpq: mantener viva la conexión ociosa. Los cuatro van juntos —
        # keepalives=1 la habilita y los otros tres definen cada cuánto.
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
        # Nombre de la app: aparece en pg_stat_activity de Neon, así que si
        # alguna vez hay conexiones colgadas se ve de dónde salieron.
        "application_name": "olimpos-backend",
    },
)

# Una sesión por request: nunca compartir una sesión entre requests
# concurrentes, porque no son thread-safe y se pisan las transacciones.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def calentar_pool(cantidad: int = 3) -> None:
    """
    Abre unas conexiones al arrancar, para que el primero que use la app no
    pague los 825 ms del handshake.

    Sin esto, la primera pantalla después de levantar el backend siempre se
    siente lenta — y es la primera impresión de cualquiera que abra el
    sistema. Abrirlas acá mueve ese costo al arranque, donde nadie lo mira.

    Si Neon está dormido o la red está caída NO se propaga el error: el
    backend tiene que poder arrancar igual y fallar cuando alguien pida algo,
    con un mensaje que la pantalla sabe mostrar. Un arranque que revienta por
    esto sería peor que un primer pedido lento.
    """
    from sqlalchemy import text

    abiertas = []
    try:
        for _ in range(cantidad):
            con = engine.connect()
            con.execute(text("SELECT 1"))
            abiertas.append(con)
    except Exception as e:      # noqa: BLE001 — a propósito: nunca frena el arranque
        print(f"  Aviso: no se pudo precalentar el pool ({type(e).__name__}). "
              f"La app arranca igual; el primer pedido va a tardar más.")
    finally:
        # Cerrarlas las DEVUELVE al pool (no las destruye): quedan abiertas
        # contra Neon y listas para el primer request.
        for con in abiertas:
            con.close()


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
