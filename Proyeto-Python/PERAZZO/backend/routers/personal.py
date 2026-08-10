"""
routers/personal.py
---------------------
CRUD de Empleados. Igual que Socios: ya no tiene datos personales
propios, se leen de Persona a través de empleado.persona.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Empleado, Persona, Usuario
from schemas import EmpleadoCreate, EmpleadoUpdate, EmpleadoOut
from security import obtener_usuario_actual

router = APIRouter(prefix="/personal", tags=["Personal"])


def _a_empleado_out(empleado: Empleado) -> EmpleadoOut:
    return EmpleadoOut(
        dni=empleado.dni,
        nombre=empleado.persona.nombre if empleado.persona else "",
        apellido=empleado.persona.apellido if empleado.persona else "",
        email=empleado.persona.email if empleado.persona else None,
        rol=empleado.rol,
        turno=empleado.turno,
        estado=empleado.estado,
    )


@router.get("", response_model=List[EmpleadoOut])
def listar_personal(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    empleados = db.query(Empleado).all()
    return [_a_empleado_out(e) for e in empleados]


@router.post("", response_model=EmpleadoOut, status_code=status.HTTP_201_CREATED)
def crear_empleado(
    datos: EmpleadoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    persona = db.query(Persona).filter(Persona.dni == datos.dni).first()
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una persona con ese DNI. Cargá primero sus datos personales.",
        )

    ya_existe = db.query(Empleado).filter(Empleado.dni == datos.dni).first()
    if ya_existe:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esa persona ya tiene una ficha de empleado.",
        )

    nuevo_empleado = Empleado(dni=datos.dni, rol=datos.rol, turno=datos.turno, estado=datos.estado)
    db.add(nuevo_empleado)
    db.commit()
    db.refresh(nuevo_empleado)
    return _a_empleado_out(nuevo_empleado)


@router.put("/{dni}", response_model=EmpleadoOut)
def actualizar_empleado(
    dni: str,
    datos: EmpleadoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    empleado = db.query(Empleado).filter(Empleado.dni == dni).first()
    if not empleado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado.")

    empleado.rol = datos.rol
    empleado.turno = datos.turno
    empleado.estado = datos.estado

    db.commit()
    db.refresh(empleado)
    return _a_empleado_out(empleado)


@router.delete("/{dni}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_empleado(
    dni: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    empleado = db.query(Empleado).filter(Empleado.dni == dni).first()
    if not empleado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado.")

    db.delete(empleado)
    db.commit()
    return None
