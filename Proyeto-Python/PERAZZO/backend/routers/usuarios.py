"""
routers/usuarios.py
---------------------
Gestión de cuentas de acceso al sistema. Requiere que ya exista una
Persona con ese DNI (creada vía POST /personas) — este endpoint solo
agrega el "acceso" (email + contraseña + rol) sobre una persona que ya
tiene sus datos cargados.

Todos los endpoints acá requieren rol PROPIETARIO o ADMIN — la misma
regla que aplica el guard de roles en el frontend, reforzada también
del lado del servidor.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Usuario, Persona, RolEnum
from schemas import UsuarioCreate, UsuarioUpdate, UsuarioOut
from auth import hashear_password
from security import requiere_roles

router = APIRouter(prefix="/usuarios", tags=["Usuarios del sistema"])

solo_propietario_o_admin = requiere_roles(RolEnum.PROPIETARIO, RolEnum.ADMIN)


def _a_usuario_out(usuario: Usuario) -> UsuarioOut:
    return UsuarioOut(
        id=usuario.id,
        dni=usuario.dni,
        nombre=usuario.nombre,  # property: lee de usuario.persona
        email=usuario.email,
        rol=usuario.rol,
        activo=usuario.activo,
        debe_cambiar_password=usuario.debe_cambiar_password,
    )


@router.get("", response_model=List[UsuarioOut])
def listar_usuarios(
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(solo_propietario_o_admin),
):
    usuarios = db.query(Usuario).order_by(Usuario.id.desc()).all()
    return [_a_usuario_out(u) for u in usuarios]


@router.post("", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
def crear_usuario(
    datos: UsuarioCreate,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(solo_propietario_o_admin),
):
    """
    Crea el acceso al sistema para una Persona que ya existe (ver
    routers/personas.py). Siempre queda con debe_cambiar_password=True:
    la nueva cuenta tiene que definir su propia contraseña la primera
    vez que se loguea.
    """
    persona = db.query(Persona).filter(Persona.dni == datos.dni).first()
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una persona con ese DNI. Cargá primero sus datos personales.",
        )

    if persona.usuario is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esa persona ya tiene una cuenta de acceso creada.",
        )

    ya_existe_email = db.query(Usuario).filter(Usuario.email == datos.email).first()
    if ya_existe_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cuenta con ese email.",
        )

    nuevo_usuario = Usuario(
        dni=datos.dni,
        email=datos.email,
        password_hash=hashear_password(datos.password_inicial),
        rol=datos.rol,
        activo=True,
        debe_cambiar_password=True,
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return _a_usuario_out(nuevo_usuario)


@router.put("/{usuario_id}", response_model=UsuarioOut)
def actualizar_usuario(
    usuario_id: int,
    datos: UsuarioUpdate,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(solo_propietario_o_admin),
):
    """
    Actualiza el rol de la cuenta. El nombre ya no se edita acá: para
    corregir nombre/apellido hay que editar la Persona (PUT /personas/{dni}).
    """
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    usuario.rol = datos.rol
    db.commit()
    db.refresh(usuario)
    return _a_usuario_out(usuario)


@router.post("/{usuario_id}/resetear-password")
def resetear_password(
    usuario_id: int,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(solo_propietario_o_admin),
):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    import secrets
    password_temporal = secrets.token_urlsafe(9)

    usuario.password_hash = hashear_password(password_temporal)
    usuario.debe_cambiar_password = True
    db.commit()

    return {
        "mensaje": f"Contraseña reseteada para {usuario.nombre}.",
        "password_temporal": password_temporal,
    }


@router.post("/{usuario_id}/toggle-estado", response_model=UsuarioOut)
def alternar_estado_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    usuario_actual: Usuario = Depends(solo_propietario_o_admin),
):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    if usuario.id == usuario_actual.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No podés desactivar tu propia cuenta.",
        )

    usuario.activo = not usuario.activo
    db.commit()
    db.refresh(usuario)
    return _a_usuario_out(usuario)
