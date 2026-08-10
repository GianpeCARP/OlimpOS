"""
check_db.py
-----------
Herramienta de desarrollo: verifica que el backend pueda conectarse a la base
y que el esquema esté cargado. No modifica nada — solo lee.

Existe porque el primer punto de falla de todo el sistema es la conexión, y
cuando falla conviene saber POR QUÉ (credencial mala, base dormida, .env sin
completar) en vez de comerse un traceback de psycopg2 de 40 líneas en medio
del arranque de uvicorn.

Se va a volver a usar cuando la base se mude de Neon a un servidor local: es
la forma más rápida de confirmar que la DATABASE_URL nueva funciona antes de
levantar la API.

Uso (con el venv activo):
    cd backend
    python check_db.py
"""

import sys

from sqlalchemy import text


# --- 1. Configuración -------------------------------------------------------
# El import de database.py es lo que dispara la lectura del .env, así que si
# falta DATABASE_URL el error salta acá y no más adelante.
try:
    from database import engine
except RuntimeError as e:
    print(f"[X] Configuración: {e}")
    sys.exit(1)


# Consultas de verificación. Cada tupla es (etiqueta, SQL, valor esperado).
# El esperado en None significa "mostrar el valor, no compararlo".
CHEQUEOS = [
    ("Tablas", "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'", 35),
    ("Enums", "SELECT count(*) FROM pg_type WHERE typtype='e' AND typnamespace='public'::regnamespace", 12),
    ("Foreign keys",
     "SELECT count(*) FROM information_schema.table_constraints "
     "WHERE constraint_type='FOREIGN KEY' AND table_schema='public'", 61),
    ("Personas", 'SELECT count(*) FROM "Persona"', None),
    ("Sedes", 'SELECT count(*) FROM "Sede"', None),
    ("Dueños", 'SELECT count(*) FROM "Dueno"', None),
    ("Usuarios", 'SELECT count(*) FROM "Usuario"', None),
]


def main() -> int:
    print("Conectando a la base...")
    print("(si es la primera consulta en un rato, Neon tiene que despertarla —")
    print(" puede tardar unos segundos, es normal)\n")

    try:
        with engine.connect() as conn:
            version = conn.execute(text("SELECT version()")).scalar_one()
            base = conn.execute(text("SELECT current_database()")).scalar_one()

            print(f"[OK] Conectado a la base '{base}'")
            print(f"     {version.split(',')[0]}\n")

            problemas = 0
            for etiqueta, sql, esperado in CHEQUEOS:
                valor = conn.execute(text(sql)).scalar_one()
                if esperado is None:
                    print(f"     {etiqueta:<14} {valor}")
                elif valor == esperado:
                    print(f"[OK] {etiqueta:<14} {valor}")
                else:
                    print(f"[X]  {etiqueta:<14} {valor}  (se esperaban {esperado})")
                    problemas += 1

            # El Usuario del dueño todavía no existe: seed.sql crea su Persona
            # pero no su cuenta de acceso. Lo crea el seeder del backend, con
            # debe_cambiar_password=True. Que dé 0 acá es lo correcto por ahora.
            usuarios = conn.execute(text('SELECT count(*) FROM "Usuario"')).scalar_one()
            print()
            if usuarios == 0:
                print("     Nota: 0 usuarios es lo esperado en este punto. La cuenta del")
                print("     dueño la va a crear el seeder cuando exista seeder.py.")

    except Exception as e:  # noqa: BLE001 — acá queremos cazar cualquier fallo de conexión
        print(f"[X] No se pudo conectar.\n\n    {type(e).__name__}: {e}\n")
        texto = str(e).lower()
        if "channel_binding" in texto or "channel binding" in texto:
            print("    Pista: sacá '&channel_binding=require' del final de la")
            print("    DATABASE_URL en el .env y dejá solo '?sslmode=require'.")
        elif "password" in texto or "authentication" in texto:
            print("    Pista: la contraseña de la cadena no coincide. Volvé al modal")
            print("    Connect de Neon y copiá el snippet de nuevo (o 'Reset password').")
        elif "could not translate host" in texto or "name or service not known" in texto:
            print("    Pista: el host está mal escrito, o la cadena quedó cortada en")
            print("    dos líneas dentro del .env. Tiene que ser una sola línea.")
        elif 'relation "' in texto and "does not exist" in texto:
            print("    Pista: la conexión anda pero faltan tablas. Corré schema.sql y")
            print("    seed.sql en el SQL Editor de Neon.")
        return 1

    print("\nListo. La base responde y el esquema está cargado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
