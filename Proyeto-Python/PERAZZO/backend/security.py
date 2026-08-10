"""
security.py
------------
Dependencias de FastAPI para proteger endpoints:
- obtener_usuario_actual: decodifica el JWT del header Authorization y
  devuelve el Usuario de la base. Se usa con Depends() en cualquier
  endpoint que requiera estar logueado.
- requiere_roles: fábrica de dependencias que además exige que el rol
  del usuario esté en una lista permitida (ej. solo PROPIETARIO/ADMIN
  pueden gestionar la sección de Usuarios).
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from database import get_db
from models import Usuario, RolEnum
from auth import SECRET_KEY, ALGORITHM

# tokenUrl es solo informativo para la documentación /docs (Swagger);
# el login real se hace por POST /login, no por este esquema OAuth2 estándar.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)


def obtener_usuario_actual(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    """
    Decodifica el JWT recibido en el header 'Authorization: Bearer <token>'.
    Si el token es inválido, expiró, o el usuario ya no existe/está inactivo,
    corta la request con 401.
    """
    credenciales_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar la sesión. Iniciá sesión nuevamente.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if token is None:
        raise credenciales_invalidas

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credenciales_invalidas
    except JWTError:
        raise credenciales_invalidas

    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if usuario is None or not usuario.activo:
        raise credenciales_invalidas

    return usuario


def requiere_roles(*roles_permitidos: RolEnum):
    """
    Fábrica de dependencias: requiere_roles(RolEnum.PROPIETARIO, RolEnum.ADMIN)
    retorna una dependencia que además de validar el token, exige que el
    rol del usuario esté entre los indicados.

    Uso en un endpoint:
        @router.get("/usuarios")
        def listar(usuario: Usuario = Depends(requiere_roles(RolEnum.PROPIETARIO, RolEnum.ADMIN))):
            ...
    """
    def dependencia(usuario: Usuario = Depends(obtener_usuario_actual)) -> Usuario:
        if usuario.rol not in roles_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tenés permisos suficientes para esta acción.",
            )
        return usuario

    return dependencia
