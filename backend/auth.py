"""
auth.py
-------
Primitivas de seguridad: hashing de contraseñas y firma/verificación de JWT.
Sin dependencias de FastAPI a propósito — acá vive el "cómo" criptográfico, y
en security.py el "quién puede qué". Así estas funciones se pueden probar y
reusar (por ejemplo desde el seeder) sin levantar la API.

Sobre bcrypt directo y no Passlib:
Passlib está sin mantenimiento desde 2020 y es incompatible con bcrypt 4.1+.
La combinación produce un error engañoso — "password cannot be longer than 72
bytes" — que aparece con contraseñas de cualquier largo y manda a depurar en
la dirección equivocada. El proyecto de referencia del profe llegó a la misma
conclusión y lo documenta en su propio auth.py.
"""

import os
import secrets
import unicodedata
from datetime import datetime, timedelta, timezone

import bcrypt
from dotenv import load_dotenv
from jose import JWTError, jwt

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "Falta JWT_SECRET_KEY en el .env. Generá una con: "
        'python -c "import secrets; print(secrets.token_urlsafe(64))"'
    )

ALGORITMO = "HS256"
EXPIRACION_MINUTOS = int(os.getenv("JWT_EXPIRACION_MINUTOS", "480"))

# Límite duro del algoritmo bcrypt, no de esta librería: solo mira los
# primeros 72 bytes de la contraseña. Truncar explícitamente es preferible a
# que la librería lance una excepción con una contraseña larga pero legítima.
# Si alguna vez hiciera falta soportar más, la solución estándar es pasar la
# contraseña por SHA-256 antes de bcrypt, no subir este número.
BCRYPT_MAX_BYTES = 72


def _a_bytes(password: str) -> bytes:
    """Codifica a UTF-8 y recorta a los 72 bytes que bcrypt realmente usa."""
    return password.encode("utf-8")[:BCRYPT_MAX_BYTES]


# =============================================================================
# CONTRASEÑAS
# =============================================================================

def hashear_password(password: str) -> str:
    """Devuelve el hash bcrypt de una contraseña en texto plano."""
    return bcrypt.hashpw(_a_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verificar_password(password_plano: str, password_hash: str) -> bool:
    """
    Compara una contraseña contra su hash. Nunca se "desencripta" el hash
    guardado: se vuelve a hashear lo que la persona escribió (con el mismo
    salt, que viaja dentro del hash) y se comparan los resultados. Por eso ni
    siquiera con acceso directo a la base se pueden leer las contraseñas.

    Devuelve False en vez de propagar si el hash guardado está corrupto o
    tiene un formato que bcrypt no reconoce: para quien llama, un hash
    ilegible y una contraseña incorrecta son el mismo caso — no entra.
    """
    try:
        return bcrypt.checkpw(_a_bytes(password_plano), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# =============================================================================
# CREDENCIALES INICIALES
# =============================================================================
# Las usa el alta por invitación: cuando el personal carga a alguien en el
# mostrador, el sistema le fabrica usuario y contraseña. La persona todavía no
# eligió nada — por eso la cuenta nace con debe_cambiar_password en True.

# 12 caracteres de token_urlsafe ≈ 72 bits de entropía. Es una clave que va a
# durar hasta el primer ingreso y que alguien tiene que poder dictar por
# teléfono, así que no tiene sentido hacerla más larga.
LARGO_PASSWORD_TEMPORAL = 12


def generar_password_temporal() -> str:
    """
    Contraseña provisoria, aleatoria y de un solo uso.

    `secrets` y no `random`: random usa un generador predecible pensado para
    simulaciones, y con unas pocas salidas se puede reconstruir su estado
    interno y adivinar las siguientes. secrets usa la fuente criptográfica del
    sistema operativo.
    """
    return secrets.token_urlsafe(LARGO_PASSWORD_TEMPORAL)


def _sin_tildes(texto: str) -> str:
    """
    'Muñoz' -> 'munoz'. Separa cada letra de su tilde y descarta las tildes.

    Hace falta porque el username se teclea al iniciar sesión: si quedara
    'muñoz', alguien con un teclado que no tiene la ñ no puede entrar a su
    propia cuenta.
    """
    normalizado = unicodedata.normalize("NFKD", texto)
    solo_ascii = "".join(c for c in normalizado if not unicodedata.combining(c))
    return "".join(c for c in solo_ascii.lower() if c.isalnum())


def generar_username(nombre: str, apellido: str, ya_existe) -> str:
    """
    Propone un username a partir del nombre. 'Ana García' -> 'ana.garcia'.

    `ya_existe` es una función que recibe un candidato y devuelve True si ese
    username ya está tomado. Se pasa como parámetro en vez de consultar la
    base acá para que este módulo siga sin saber nada de SQLAlchemy: así se
    puede probar sin levantar una base.

    Ante colisión agrega un número: ana.garcia, ana.garcia2, ana.garcia3...
    Dos personas con el mismo nombre y apellido es raro pero pasa, y el
    esquema tiene username UNIQUE — sin esto, el alta de la segunda fallaría
    con un error de base de datos incomprensible para quien está en el
    mostrador.
    """
    base = f"{_sin_tildes(nombre)}.{_sin_tildes(apellido)}".strip(".")
    if not base:
        # Nombre y apellido sin un solo carácter alfanumérico (todo símbolos).
        # Improbable, pero un username vacío rompería el login para siempre.
        base = f"socio{secrets.randbelow(10000):04d}"

    candidato = base
    sufijo = 2
    while ya_existe(candidato):
        candidato = f"{base}{sufijo}"
        sufijo += 1
    return candidato


# =============================================================================
# TOKENS JWT
# =============================================================================

def crear_token_acceso(
    id_usuario: int,
    username: str,
    roles: list[str],
    id_socio: int | None = None,
) -> str:
    """
    Firma un JWT con la identidad y los roles de la sesión.

    `id_socio` viaja adentro por pedido explícito de la spec del portal del
    socio (ver LoginResultado.idSocio en authService.ts): es el id con el que
    trabajan TODAS las pantallas del socio, y si cada una lo resolviera por su
    cuenta alcanzaría con que una se olvidara de filtrar para que empiece a
    mostrar datos de otra persona. Al venir firmado desde el login, el cliente
    no puede alterarlo. Es None para el staff que no es socio del gimnasio.

    Los roles viajan DENTRO del token, resueltos una sola vez en el login (ver
    models.roles_de_persona). La alternativa —recalcularlos en cada request—
    costaría cinco JOINs por pedido para un dato que no cambia mientras dura
    la sesión. El precio de esta decisión es que un cambio de rol no tiene
    efecto hasta el próximo login; a cambio, desactivar una cuenta SÍ es
    inmediato, porque security.py releé el Usuario en cada request.

    `sub` lleva el id_usuario y no el username: el username se puede llegar a
    editar, el id no. Un token viejo tiene que seguir apuntando a la misma
    cuenta aunque le hayan cambiado el nombre de acceso.
    """
    ahora = datetime.now(timezone.utc)
    payload = {
        "sub": str(id_usuario),   # la spec de JWT pide que `sub` sea string
        "username": username,
        "roles": roles,
        "id_socio": id_socio,
        "iat": ahora,
        "exp": ahora + timedelta(minutes=EXPIRACION_MINUTOS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITMO)


def decodificar_token(token: str) -> dict | None:
    """
    Verifica la firma y la expiración de un token y devuelve su contenido.
    Devuelve None si el token es inválido, fue alterado o venció — quien
    llama no necesita distinguir entre esos casos, y no conviene decirle al
    cliente cuál de los tres fue.
    """
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITMO])
    except JWTError:
        return None
