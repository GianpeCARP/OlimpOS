"""
Deja la base en el estado de ENTREGA: 9 filas y nada mas.

    .venv/Scripts/python.exe pruebas/vaciar_base.py         # muestra que haria
    .venv/Scripts/python.exe pruebas/vaciar_base.py --si    # lo hace

POR QUE EXISTE
==============
El CLAUDE.md dice "entre suite y suite hay que vaciar la base, o la anterior
le deja datos a la siguiente y fallan por el escenario, no por un bug", pero
no decia COMO. Se hacia a mano, y a mano significa que cada vez queda un poco
distinto: una corrida a medias deja tres Patologias y dos Empleados, la
siguiente suite choca contra un DNI repetido y el fallo parece un bug del
codigo que se acaba de escribir.

Las 9 filas que quedan son las que describe el CLAUDE.md:

    Persona + Dueno del titular   (DNI 00000000)
    Sede Central
    2 Tipo_Membresia
    3 Franja_Laboral              (Mañana/Tarde/Noche — ver FRANJAS abajo)
    la cuenta 'dueno'

POR QUE TRUNCATE Y NO DELETE
============================
TRUNCATE ... RESTART IDENTITY reinicia las secuencias. Con DELETE los ids
seguirian creciendo, y las suites imprimen ids en su salida: comparar dos
corridas se vuelve imposible si una arranca en id_socio=1 y la otra en 47.
CASCADE no es opcional: hay 70 foreign keys y borrar en el orden correcto a
mano es justamente lo que este script viene a evitar.

LA CUENTA DEL DUENO
===================
Se recrea aca y no se deja que la haga el seeder del arranque, aunque el
seeder sea idempotente y sepa hacerlo. El motivo es el orden: el seeder corre
en el lifespan de la API, asi que si esto se ejecuta con el backend ya
levantado —que es el caso normal, porque las suites lo necesitan corriendo—
nadie volveria a llamarlo hasta el proximo reinicio, y la suite siguiente se
encontraria sin cuenta con la cual entrar.

Nace con debe_cambiar_password en true, igual que la del seeder: el primer
ingreso obliga a definir una propia. Las suites contemplan ese paso.
"""
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from sqlalchemy import text

from auth import hashear_password
from database import SessionLocal

load_dotenv()

# El titular. Sale del .env para que coincida con lo que espera el seeder: si
# los dos inventaran su propio DNI, arrancar la API despues de vaciar crearia
# una SEGUNDA Persona en vez de reconocer la que quedo.
DNI = os.getenv("DUENO_INICIAL_DNI", "00000000")
NOMBRE = os.getenv("DUENO_INICIAL_NOMBRE", "Dueño")
APELLIDO = os.getenv("DUENO_INICIAL_APELLIDO", "Admin")
EMAIL = os.getenv("DUENO_INICIAL_EMAIL") or "dueno@olimpos.local"
USERNAME = os.getenv("DUENO_INICIAL_USERNAME")
PASSWORD = os.getenv("DUENO_INICIAL_PASSWORD")

# Los dos planes de la base entregada.
PLANES = [
    ("Mensual Full", 30, 30000.00),
    ("Trimestral", 90, 78000.00),
]

# Las franjas laborales. Van en el estado de ENTREGA —no sólo en el demo—
# porque no hay pantalla para crearlas (el backend sólo las lista) y el alta de
# un Recepcionista pide elegir una: sin ellas, una base recién entregada no
# deja dar de alta al mostrador. Mismos valores que db/seed.sql, sección 2.4.
# Se agregaron el 2026-09-16, cuando el dueño vació la base para cargar todo a
# mano y se encontró con el selector vacío.
FRANJAS = [
    ("Mañana", "06:00", "14:00"),
    ("Tarde", "14:00", "22:00"),
    ("Noche", "22:00", "06:00"),
]

# Filas que tiene que dejar: Persona + Dueno + Sede + la cuenta, más los planes
# y las franjas. Se calcula en vez de escribir "9" para que agregar un catálogo
# fijo no deje el chequeo final mintiendo.
FILAS_ESPERADAS = 4 + len(PLANES) + len(FRANJAS)


def main() -> int:
    if not USERNAME or not PASSWORD:
        print("Faltan DUENO_INICIAL_USERNAME / DUENO_INICIAL_PASSWORD en el .env.")
        return 1

    db = SessionLocal()
    try:
        tablas = [r[0] for r in db.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
            "ORDER BY tablename"
        ))]

        con_datos = []
        for t in tablas:
            n = db.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar()
            if n:
                con_datos.append((t, n))

        print(f"Tablas en la base: {len(tablas)}")
        print(f"Con datos ahora:   {len(con_datos)}")
        for t, n in con_datos:
            print(f"   {t:<26} {n}")

        if "--si" not in sys.argv:
            print(f"\nEsto BORRA todo lo de arriba y deja {FILAS_ESPERADAS} filas.")
            print("Volvé a correrlo con --si si es lo que querés.")
            return 0

        # Un solo TRUNCATE con todas las tablas: entre ellas hay ciclos de FK
        # y truncarlas de a una falla aunque se use CASCADE.
        lista = ", ".join(f'"{t}"' for t in tablas)
        db.execute(text(f"TRUNCATE {lista} RESTART IDENTITY CASCADE"))

        db.execute(text(
            'INSERT INTO "Persona" (dni, apellido, nombre, email) '
            "VALUES (:dni, :ape, :nom, :mail)"
        ), {"dni": DNI, "ape": APELLIDO, "nom": NOMBRE, "mail": EMAIL})
        db.execute(text(
            'INSERT INTO "Dueno" (id_persona, porcentaje_participacion) '
            "SELECT id_persona, 100.00 FROM \"Persona\" WHERE dni = :dni"
        ), {"dni": DNI})
        db.execute(text(
            'INSERT INTO "Sede" (id_dueno, nombre, localidad, abierto_24hs, activo) '
            "SELECT id_dueno, 'Sede Central', 'Moreno', true, true FROM \"Dueno\""
        ))
        for nombre, dias, precio in PLANES:
            db.execute(text(
                'INSERT INTO "Tipo_Membresia" (nombre, duracion_dias, precio_actual, activo) '
                "VALUES (:n, :d, :p, true)"
            ), {"n": nombre, "d": dias, "p": precio})
        for nombre, desde, hasta in FRANJAS:
            db.execute(text(
                'INSERT INTO "Franja_Laboral" (nombre, hora_desde, hora_hasta, activo) '
                "VALUES (:n, :d, :h, true)"
            ), {"n": nombre, "d": desde, "h": hasta})
        db.execute(text(
            'INSERT INTO "Usuario" (id_persona, username, password_hash, '
            "debe_cambiar_password, activo) "
            "SELECT id_persona, :u, :h, true, true FROM \"Persona\" WHERE dni = :dni"
        ), {"u": USERNAME, "h": hashear_password(PASSWORD), "dni": DNI})

        db.commit()

        total = sum(
            db.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar() for t in tablas
        )
        print(f"\nListo. Quedaron {total} filas (se esperaban {FILAS_ESPERADAS}).")
        print(f"Cuenta '{USERNAME}' con la contraseña de DUENO_INICIAL_PASSWORD,")
        print("y el primer ingreso va a pedir cambiarla.")
        return 0 if total == FILAS_ESPERADAS else 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
