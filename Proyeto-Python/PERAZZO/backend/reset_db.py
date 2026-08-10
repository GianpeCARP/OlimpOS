"""
reset_db.py
------------
Herramienta de desarrollo: borra TODAS las tablas y tipos enum del
esquema de OlimpOS en Neon, y los vuelve a crear desde cero según los
modelos actuales de models.py.

Por qué existe: SQLAlchemy's Base.metadata.create_all() SOLO crea
tablas que no existen — nunca modifica ni borra una tabla que ya
existe, aunque el código haya cambiado. Cada vez que se cambia la
estructura de un modelo (una columna, un enum, una clave primaria),
hace falta borrar la tabla vieja para que se recree con la forma
nueva. Hasta ahora esto se venía haciendo a mano en el SQL Editor de
Neon — este script hace exactamente lo mismo con un solo comando.

⚠️ ADVERTENCIA: esto borra TODOS los datos existentes. Usar solo en
desarrollo. Nunca correr esto contra una base con datos reales que se
quieran conservar.

Uso:
    cd backend
    python reset_db.py
"""

from sqlalchemy import text

from database import Base, engine
import models  # noqa: F401 — el import registra todos los modelos en Base.metadata

# Orden de borrado: primero las tablas "puente" y las que dependen de
# otras (por sus ForeignKey), y al final las tablas base. No es
# estrictamente necesario gracias a CASCADE, pero mantiene la intención
# clara si algún día se lee este script.
TABLAS = [
    "turno_inscripciones", "turnos",
    "nutricion_asignaciones", "planes_nutricion",
    "rutina_asignaciones", "rutinas",
    "socios", "empleados",
    "usuarios", "personas",
]

TIPOS_ENUM = [
    "rolenum", "planenum", "estadosocioenum", "turnolaboralenum",
    "estadoempleadoenum", "nivelenum", "objetivoenum", "diasemanaenum",
]


def resetear():
    with engine.connect() as conn:
        for tabla in TABLAS:
            conn.execute(text(f"DROP TABLE IF EXISTS {tabla} CASCADE"))
        for tipo in TIPOS_ENUM:
            conn.execute(text(f"DROP TYPE IF EXISTS {tipo} CASCADE"))
        conn.commit()
    print("✓ Tablas y tipos anteriores eliminados.")

    Base.metadata.create_all(bind=engine)
    print("✓ Esquema recreado desde los modelos actuales de models.py.")
    print()
    print("Ahora podés arrancar el servidor normalmente:")
    print("    uvicorn main:app --reload")
    print("El seeder va a crear de nuevo el usuario PROPIETARIO inicial.")


if __name__ == "__main__":
    respuesta = input(
        "Esto va a BORRAR TODOS los datos existentes en la base configurada "
        "en tu .env. ¿Continuar? (escribí 'si' para confirmar): "
    )
    if respuesta.strip().lower() == "si":
        resetear()
    else:
        print("Cancelado. No se modificó nada.")
