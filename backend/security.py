"""
security.py
-----------
Dependencias de FastAPI que protegen los endpoints. Acá vive el "quién puede
qué"; el "cómo" criptográfico está en auth.py y la tabla de permisos en
permisos.py.

Son tres capas, de menos a más estricta:

    obtener_sesion            ¿hay una sesión válida?            -> 401
    requiere_seccion(...)     ¿el rol entra a esta sección?      -> 403
    requiere_accion(...)      ¿el rol puede ejecutar esto?       -> 403

Se declaran como parámetros del endpoint y FastAPI las resuelve ANTES de
ejecutar su cuerpo. Eso significa que un endpoint mal escrito no puede
"olvidarse" de chequear permisos a mitad de camino: si la dependencia está en
la firma, la barrera ya se aplicó.

Esta es la segunda mitad de la idea central del proyecto. La PWA y Flet
esconden lo que un rol no debe ver — eso es experiencia de usuario, y
cualquiera con las devtools abiertas se lo saltea. Lo de acá es lo que
realmente frena la operación, venga del navegador, de la app de escritorio o
de un curl.
"""

from dataclasses import dataclass

from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from auth import decodificar_token
from cookies import COOKIE_SESION
from database import get_db
from models import Usuario
from permisos import Acceso, acceso_a_seccion, alcanza, puede_accion

# auto_error=False para poder devolver nuestro propio mensaje en castellano
# cuando falta el header, en vez del "Not authenticated" de FastAPI.
# tokenUrl es solo informativo, para el botón Authorize de /docs: el login
# real es POST /login con un cuerpo JSON, no el form OAuth2 estándar.
esquema_token = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)


@dataclass
class Sesion:
    """
    La sesión activa, ya resuelta. Es lo que reciben los endpoints.

    `roles` viene del JWT y no de la base a propósito: se calculó una sola vez
    en el login (ver models.roles_de_persona) y viaja firmado. `usuario`, en
    cambio, se relee de la base en cada request — ver obtener_sesion.
    """
    usuario: Usuario
    roles: list[str]
    # El id de Socio de esta persona, o None si no es socio del gimnasio.
    # Viene firmado en el token: las pantallas del portal lo usan para filtrar
    # y el cliente no puede alterarlo. Ver crear_token_acceso.
    id_socio: int | None = None

    @property
    def id_usuario(self) -> int:
        return self.usuario.id_usuario

    @property
    def id_persona(self) -> int:
        return self.usuario.id_persona


_NO_AUTENTICADO = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="No se pudo validar la sesión. Iniciá sesión nuevamente.",
    headers={"WWW-Authenticate": "Bearer"},
)


def obtener_sesion(
    token_header: str | None = Depends(esquema_token),
    token_cookie: str | None = Cookie(default=None, alias=COOKIE_SESION),
    db: Session = Depends(get_db),
) -> Sesion:
    """
    Valida la sesión y la devuelve. Corta con 401 si falta el token, es
    inválido, venció, o si la cuenta ya no está en condiciones de operar.

    Acepta los DOS transportes, según qué cliente esté hablando:

      - `Authorization: Bearer <token>` — la app Flet de escritorio.
      - Cookie `olimpos_session` (httponly) — la PWA en el navegador.

    El header tiene prioridad porque es explícito: si alguien se molestó en
    ponerlo, esa es la sesión que quiere usar. La cookie, en cambio, la manda
    el navegador sola.

    Ojo: aceptar la cookie es lo que abre la puerta al CSRF, y por eso existe
    csrf.py. Los dos archivos son una sola decisión de diseño partida en dos
    lugares — no se puede tocar uno sin mirar el otro.

    Por qué se relee el Usuario de la base en cada request, si el token ya
    trae la identidad: porque el token es inmutable hasta que expira (8 horas)
    y hace falta que desactivar o bloquear una cuenta tenga efecto YA. Sin
    esta consulta, alguien a quien le acaban de dar de baja seguiría operando
    el resto de la jornada. Es una consulta por PK, barata.
    """
    token = token_header or token_cookie
    if not token:
        raise _NO_AUTENTICADO

    payload = decodificar_token(token)
    if not payload:
        raise _NO_AUTENTICADO

    try:
        id_usuario = int(payload.get("sub", ""))
    except (TypeError, ValueError):
        raise _NO_AUTENTICADO

    usuario = db.get(Usuario, id_usuario)
    if usuario is None or not usuario.activo or usuario.bloqueado:
        raise _NO_AUTENTICADO

    # Un token emitido antes de un reseteo de contraseña no debe seguir
    # sirviendo: si la cuenta quedó marcada para cambiar la clave, la única
    # operación permitida es cambiarla (y ese endpoint es público, no pasa
    # por acá).
    if usuario.debe_cambiar_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenés que cambiar tu contraseña antes de seguir usando el sistema.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    roles = payload.get("roles") or []
    if not isinstance(roles, list):
        raise _NO_AUTENTICADO

    return Sesion(usuario=usuario, roles=roles, id_socio=payload.get("id_socio"))


def requiere_seccion(seccion: str, minimo: str = Acceso.LECTURA):
    """
    Fábrica de dependencias: exige acceso a una sección, con un nivel mínimo.

        @router.get("/socios")
        def listar(sesion: Sesion = Depends(requiere_seccion(Seccion.SOCIOS))):
            ...

        @router.post("/socios")
        def crear(sesion: Sesion = Depends(
            requiere_seccion(Seccion.SOCIOS, Acceso.TOTAL))):
            ...

    El default es LECTURA porque es lo que necesita cualquier GET, que son la
    mayoría. Las escrituras piden TOTAL explícitamente — que el pedido más
    permisivo sea el default hace que olvidarse escriba de menos, no de más.
    """
    def dependencia(sesion: Sesion = Depends(obtener_sesion)) -> Sesion:
        nivel = acceso_a_seccion(sesion.roles, seccion)
        if not alcanza(nivel, minimo):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tenés permisos para acceder a esta sección.",
            )
        return sesion

    return dependencia


def requiere_accion(accion: str):
    """
    Fábrica de dependencias: exige una acción puntual de la matriz.

    Va ADEMÁS del permiso de sección, no en lugar de él. El caso que lo
    justifica es el Recepcionista en Personal: entra a la sección (LECTURA)
    pero no puede dar de alta a nadie. Proteger solo la ruta lo dejaría
    crear empleados; proteger solo la acción lo dejaría ver una pantalla que
    no le corresponde.
    """
    def dependencia(sesion: Sesion = Depends(obtener_sesion)) -> Sesion:
        if not puede_accion(sesion.roles, accion):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tenés permisos para realizar esta acción.",
            )
        return sesion

    return dependencia
