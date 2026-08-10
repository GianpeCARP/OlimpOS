"""
routers/socios.py
------------------
CRUD de Socios. Ya no incluye datos personales propios (nombre, apellido,
email, teléfono): esos viven exclusivamente en Persona y se leen acá a
través de la relación socio.persona. Para crear un Socio, la Persona con
ese DNI ya tiene que existir (se da de alta desde la pantalla unificada
"Nueva Persona" del frontend, o vía POST /personas).
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Socio, Persona, Usuario
from schemas import SocioCreate, SocioUpdate, SocioOut
from security import obtener_usuario_actual

router = APIRouter(prefix="/socios", tags=["Socios"])


def _a_socio_out(socio: Socio) -> SocioOut:
    return SocioOut(
        dni=socio.dni,
        nombre=socio.persona.nombre if socio.persona else "",
        apellido=socio.persona.apellido if socio.persona else "",
        email=socio.persona.email if socio.persona else None,
        telefono=socio.persona.telefono if socio.persona else None,
        plan=socio.plan,
        estado=socio.estado,
        fecha_alta=socio.fecha_alta,
        fecha_vencimiento=socio.fecha_vencimiento,
    )


@router.get("", response_model=List[SocioOut])
def listar_socios(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    socios = db.query(Socio).order_by(Socio.fecha_alta.desc()).all()
    return [_a_socio_out(s) for s in socios]


@router.post("", response_model=SocioOut, status_code=status.HTTP_201_CREATED)
def crear_socio(
    datos: SocioCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    persona = db.query(Persona).filter(Persona.dni == datos.dni).first()
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una persona con ese DNI. Cargá primero sus datos personales.",
        )

    ya_existe = db.query(Socio).filter(Socio.dni == datos.dni).first()
    if ya_existe:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esa persona ya es socia del gimnasio.",
        )

    nuevo_socio = Socio(
        dni=datos.dni, plan=datos.plan, estado=datos.estado,
        fecha_vencimiento=datos.fecha_vencimiento,
    )
    db.add(nuevo_socio)
    db.commit()
    db.refresh(nuevo_socio)
    return _a_socio_out(nuevo_socio)


@router.put("/{dni}", response_model=SocioOut)
def actualizar_socio(
    dni: str,
    datos: SocioUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    socio = db.query(Socio).filter(Socio.dni == dni).first()
    if not socio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Socio no encontrado.")

    socio.plan = datos.plan
    socio.estado = datos.estado
    socio.fecha_vencimiento = datos.fecha_vencimiento

    db.commit()
    db.refresh(socio)
    return _a_socio_out(socio)


@router.delete("/{dni}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_socio(
    dni: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    """
    Elimina la "función" de Socio, pero NO borra a la Persona (que
    podría seguir existiendo como Empleado o Usuario, o simplemente
    quedar registrada para el futuro).
    """
    socio = db.query(Socio).filter(Socio.dni == dni).first()
    if not socio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Socio no encontrado.")

    db.delete(socio)
    db.commit()
    return None
