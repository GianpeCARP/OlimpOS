"""
seeder.py
---------
Crea la Persona + Usuario PROPIETARIO inicial si todavía no existe ningún
usuario con ese rol. Las credenciales se leen del archivo .env para no
hardcodear contraseñas en el código fuente.
"""

import os
from sqlalchemy.orm import Session

from models import Usuario, Persona, RolEnum
from auth import hashear_password


def ejecutar_seeder(db: Session) -> None:
    """
    Verifica si existe un Usuario con rol PROPIETARIO. Si no existe:
    1. Crea su Persona (con el DNI leído del .env, o uno de relleno).
    2. Crea su Usuario vinculado a esa Persona, con
       debe_cambiar_password=True para forzar que defina su propia
       contraseña en el primer ingreso.
    """
    ya_existe_propietario = db.query(Usuario).filter(Usuario.rol == RolEnum.PROPIETARIO).first()
    if ya_existe_propietario:
        print("Seeder: ya existe un usuario PROPIETARIO, no se crea ninguno nuevo.")
        return

    email_inicial = os.getenv("ADMIN_INICIAL_EMAIL")
    password_inicial = os.getenv("ADMIN_INICIAL_PASSWORD")
    dni_inicial = os.getenv("ADMIN_INICIAL_DNI", "00000000")

    if not email_inicial or not password_inicial:
        print(
            "Seeder: no se definieron ADMIN_INICIAL_EMAIL / ADMIN_INICIAL_PASSWORD "
            "en el .env. No se creó ningún usuario PROPIETARIO."
        )
        return

    persona = db.query(Persona).filter(Persona.dni == dni_inicial).first()
    if not persona:
        persona = Persona(dni=dni_inicial, nombre="Propietario", apellido="Inicial")
        db.add(persona)
        db.flush()  # asigna el DNI a la transacción sin cerrarla, para usarlo abajo

    nuevo_propietario = Usuario(
        dni=persona.dni,
        email=email_inicial,
        password_hash=hashear_password(password_inicial),
        rol=RolEnum.PROPIETARIO,
        activo=True,
        debe_cambiar_password=True,
    )
    db.add(nuevo_propietario)
    db.commit()
    print(f"Seeder: usuario PROPIETARIO creado con email '{email_inicial}' (DNI {dni_inicial}).")
