"""
auth.py
-------
Utilidades de seguridad: hashing de contraseñas (bcrypt) y generación
de tokens JWT (python-jose).

Nota sobre la elección de bcrypt "directo" en vez de Passlib:
Passlib (la librería que se usaba antes acá) está sin mantenimiento desde
2020 y no es compatible con las versiones nuevas de la librería `bcrypt`
(4.1+), lo que genera errores confusos como "password cannot be longer
than 72 bytes" que no tienen relación real con la contraseña usada. Para
evitar ese problema (y no depender de una librería abandonada), acá se
usa `bcrypt` directamente, que sí está mantenida activamente.
"""

import os
from datetime import datetime, timedelta

import bcrypt
from dotenv import load_dotenv
from jose import jwt

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "clave-de-desarrollo-cambiar-en-produccion")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 horas de sesión

# bcrypt trabaja internamente sobre bytes y tiene un límite duro de 72 bytes
# por contraseña (limitación del propio algoritmo, no de esta librería).
# Si se necesitaran contraseñas más largas, se debería aplicar un hash
# previo (ej. SHA-256) antes de pasarlas a bcrypt. Para este proyecto,
# alcanza con truncar de forma explícita y documentada.
BCRYPT_MAX_BYTES = 72


def _a_bytes_bcrypt(password: str) -> bytes:
    """Codifica el password a UTF-8 y lo recorta a los 72 bytes que soporta bcrypt."""
    return password.encode("utf-8")[:BCRYPT_MAX_BYTES]


def hashear_password(password: str) -> str:
    """Genera el hash bcrypt de una contraseña en texto plano."""
    password_bytes = _a_bytes_bcrypt(password)
    salt = bcrypt.gensalt()
    hash_bytes = bcrypt.hashpw(password_bytes, salt)
    return hash_bytes.decode("utf-8")


def verificar_password(password_plano: str, password_hash: str) -> bool:
    """Compara una contraseña en texto plano contra su hash almacenado."""
    password_bytes = _a_bytes_bcrypt(password_plano)
    hash_bytes = password_hash.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hash_bytes)


def crear_token_acceso(datos: dict) -> str:
    """
    Genera un JWT firmado con los datos indicados (ej: email y rol del usuario).
    El token incluye una fecha de expiración ('exp').
    """
    datos_a_codificar = datos.copy()
    expiracion = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    datos_a_codificar.update({"exp": expiracion})
    return jwt.encode(datos_a_codificar, SECRET_KEY, algorithm=ALGORITHM)
