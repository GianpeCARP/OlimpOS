"""
seeder.py
---------
Bootstrapping: deja el sistema en condiciones de recibir su primer login sin
que nadie tenga que tocar la base a mano.

La consigna lo pide así: "el sistema debe ser lo suficientemente inteligente
para configurarse a sí mismo de forma segura y permitir la entrada del
propietario del gimnasio sin intervención de un programador".

Es IDEMPOTENTE: se ejecuta en cada arranque de la API y no hace nada si ya
encontró un dueño con cuenta. Eso es lo que permite llamarlo desde el lifespan
sin condicionales ni banderas de "primera vez".

Reparto de trabajo con db/seed.sql, que conviene tener claro:

    seed.sql   crea la Persona del dueño, su fila en Dueno y la Sede Central.
               Son datos de negocio, y viven con el resto del DDL.
    seeder.py  le crea la CUENTA DE ACCESO a esa persona. Es lo único que
               seed.sql no puede hacer, porque necesita hashear una
               contraseña que sale del .env — un archivo que no se versiona.

Por eso este seeder busca la Persona por DNI en vez de crearla de una: si
seed.sql ya corrió, la reutiliza. Si no corrió, la crea igual, así el arranque
funciona sobre una base recién creada con solo el schema.
"""

import os

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from auth import hashear_password
from models import Dueno, Persona, Sede, Usuario

load_dotenv()


def _leer_config() -> dict | None:
    """
    Lee las variables del dueño inicial. Devuelve None (y avisa) si faltan las
    dos imprescindibles, en vez de reventar: un .env incompleto tiene que
    impedir el seeding, no impedir que la API arranque. El resto de los
    endpoints puede funcionar perfectamente sin que exista el dueño.
    """
    username = os.getenv("DUENO_INICIAL_USERNAME")
    password = os.getenv("DUENO_INICIAL_PASSWORD")

    if not username or not password:
        print(
            "  Seeder: faltan DUENO_INICIAL_USERNAME y/o DUENO_INICIAL_PASSWORD\n"
            "          en el .env. No se creó ninguna cuenta."
        )
        return None

    return {
        "username": username,
        "password": password,
        "dni": os.getenv("DUENO_INICIAL_DNI", "00000000"),
        "nombre": os.getenv("DUENO_INICIAL_NOMBRE", "Dueño"),
        "apellido": os.getenv("DUENO_INICIAL_APELLIDO", "Admin"),
        "email": os.getenv("DUENO_INICIAL_EMAIL"),
    }


def ejecutar_seeder(db: Session) -> None:
    """
    Garantiza que exista al menos un dueño con cuenta de acceso.

    Los pasos siguen el mismo orden que impone el esquema, que no es
    arbitrario: Persona primero (todo cuelga de ella), después el rol, y el
    acceso al final. Es el mismo orden que va a seguir el alta de un socio o
    un empleado desde el mostrador.
    """
    # --- ¿Ya está hecho? -----------------------------------------------------
    # La pregunta correcta no es "¿hay algún usuario?" sino "¿hay algún dueño
    # CON CUENTA?". Podría haber cuentas de recepcionistas y seguir sin haber
    # nadie capaz de administrar el sistema.
    ya_existe = (
        db.query(Usuario)
        .join(Persona, Usuario.id_persona == Persona.id_persona)
        .join(Dueno, Dueno.id_persona == Persona.id_persona)
        .first()
    )
    if ya_existe:
        print(f"  Seeder: ya existe un dueño con cuenta ('{ya_existe.username}'). Nada que hacer.")
        return

    config = _leer_config()
    if not config:
        return

    # --- 1. La Persona -------------------------------------------------------
    persona = db.query(Persona).filter(Persona.dni == config["dni"]).first()

    if persona:
        print(f"  Seeder: encontré la Persona del DNI {config['dni']} ({persona.nombre_completo}).")
    else:
        persona = Persona(
            dni=config["dni"],
            nombre=config["nombre"],
            apellido=config["apellido"],
            email=config["email"],
        )
        db.add(persona)
        # flush y no commit: manda el INSERT para que la base asigne el
        # id_persona (que hace falta abajo), pero deja la transacción abierta.
        # Si algo falla después, no queda una Persona suelta sin rol ni cuenta.
        db.flush()
        print(f"  Seeder: creé la Persona {persona.nombre_completo} (DNI {config['dni']}).")

    # --- 2. El rol -----------------------------------------------------------
    # Sin fila en Dueno, roles_de_persona() devuelve [] y el login rechaza la
    # cuenta por no tener ningún rol. Es el paso más fácil de olvidar y el que
    # deja el sistema inutilizable.
    if persona.dueno is None:
        db.add(Dueno(id_persona=persona.id_persona, porcentaje_participacion=100))
        db.flush()
        print("  Seeder: le agregué la fila en Dueno (rol 'dueno').")

    # --- 3. La cuenta --------------------------------------------------------
    if persona.usuario is not None:
        # Persona con cuenta pero sin rol de dueño: el chequeo de arriba no lo
        # detectó. No se pisa la contraseña — puede ser una cuenta en uso.
        print(f"  Seeder: '{persona.usuario.username}' ya tenía cuenta; solo se corrigió el rol.")
        db.commit()
        return

    if db.query(Usuario).filter(Usuario.username == config["username"]).first():
        print(
            f"  Seeder: el username '{config['username']}' ya está tomado por otra\n"
            "          persona. Cambiá DUENO_INICIAL_USERNAME en el .env."
        )
        db.rollback()
        return

    db.add(Usuario(
        id_persona=persona.id_persona,
        username=config["username"],
        password_hash=hashear_password(config["password"]),
        # El punto central de todo el flujo: la cuenta nace exigiendo el
        # cambio. El dueño entra con la clave del .env, el login le verifica
        # la contraseña pero NO le da token, lo manda a cambiarla, y recién
        # el segundo ingreso le abre el sistema.
        debe_cambiar_password=True,
        activo=True,
    ))
    db.commit()

    print(f"  Seeder: cuenta creada -> usuario '{config['username']}'")
    print("          (contraseña: la de DUENO_INICIAL_PASSWORD en el .env)")
    print("          En el primer ingreso el sistema le va a exigir cambiarla.")

    # --- Aviso, no error -----------------------------------------------------
    # Empleado y Socio tienen id_sede NOT NULL: sin una sede cargada no se
    # puede dar de alta a nadie. No es problema del seeder resolverlo, pero sí
    # avisarlo ahora y no cuando falle el primer alta con un error de FK.
    if db.query(Sede).count() == 0:
        print("\n  AVISO: no hay ninguna Sede cargada. Empleado y Socio la necesitan")
        print("         (id_sede NOT NULL). Corré db/seed.sql para crear la Sede Central.")
