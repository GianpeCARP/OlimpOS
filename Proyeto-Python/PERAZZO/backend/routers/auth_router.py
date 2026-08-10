"""
routers/auth_router.py
-----------------------
Endpoints de autenticación: /login y /cambiar-password.
Son los únicos endpoints públicos de la API (no requieren token).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Usuario
from schemas import LoginRequest, LoginResponse, CambiarPasswordRequest
from auth import verificar_password, hashear_password, crear_token_acceso

router = APIRouter(tags=["Autenticación"])


@router.post("/login", response_model=LoginResponse)
def login(datos: LoginRequest, db: Session = Depends(get_db)):
    """
    Verifica email + password.
    - Si debe_cambiar_password es True, se avisa al frontend para que
      redirija a la pantalla de cambio de contraseña (sin emitir token).
    - Si es False, se devuelve un JWT con el rol del usuario.
    """
    usuario = db.query(Usuario).filter(Usuario.email == datos.email).first()

    credenciales_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Email o contraseña incorrectos.",
    )

    if not usuario or not verificar_password(datos.password, usuario.password_hash):
        raise credenciales_invalidas

    if not usuario.activo:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo.")

    if usuario.debe_cambiar_password:
        return LoginResponse(debe_cambiar_password=True)

    token = crear_token_acceso({"sub": usuario.email, "rol": usuario.rol.value})
    return LoginResponse(
        debe_cambiar_password=False,
        access_token=token,
        rol=usuario.rol,
        nombre=usuario.nombre,
    )


@router.post("/cambiar-password")
def cambiar_password(datos: CambiarPasswordRequest, db: Session = Depends(get_db)):
    """
    Permite establecer una nueva contraseña, validando siempre la
    contraseña actual antes de aplicar el cambio. Desactiva la bandera
    debe_cambiar_password para que el próximo login sea normal.
    """
    usuario = db.query(Usuario).filter(Usuario.email == datos.email).first()

    if not usuario or not verificar_password(datos.password_actual, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña actual incorrectos.",
        )

    usuario.password_hash = hashear_password(datos.password_nueva)
    usuario.debe_cambiar_password = False
    db.commit()

    return {"mensaje": "Contraseña actualizada correctamente. Ya podés iniciar sesión."}
