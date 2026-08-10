"""
routers/personas.py
---------------------
CRUD de Personas: el primer paso del alta unificada. Además de los
datos personales, devuelve tres flags (tiene_usuario, tiene_socio,
tiene_empleado) para que la pantalla de "Nueva Persona" del frontend
sepa qué funciones ya tiene cada DNI y no ofrezca crearlas de nuevo.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Persona, Usuario
from schemas import PersonaCreate, PersonaUpdate, PersonaOut
from security import obtener_usuario_actual

router = APIRouter(prefix="/personas", tags=["Personas"])


def _a_persona_out(persona: Persona) -> PersonaOut:
    salida = PersonaOut.model_validate(persona)
    salida.tiene_usuario = persona.usuario is not None
    salida.tiene_socio = persona.socio is not None
    salida.tiene_empleado = persona.empleado is not None
    return salida


@router.get("", response_model=List[PersonaOut])
def listar_personas(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    personas = db.query(Persona).order_by(Persona.creado_en.desc()).all()
    return [_a_persona_out(p) for p in personas]


@router.get("/{dni}", response_model=PersonaOut)
def obtener_persona(
    dni: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    persona = db.query(Persona).filter(Persona.dni == dni).first()
    if not persona:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No existe una persona con ese DNI.")
    return _a_persona_out(persona)


@router.post("", response_model=PersonaOut, status_code=status.HTTP_201_CREATED)
def crear_persona(
    datos: PersonaCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    ya_existe = db.query(Persona).filter(Persona.dni == datos.dni).first()
    if ya_existe:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una persona registrada con ese DNI.",
        )

    nueva_persona = Persona(**datos.model_dump())
    db.add(nueva_persona)
    db.commit()
    db.refresh(nueva_persona)
    return _a_persona_out(nueva_persona)


@router.put("/{dni}", response_model=PersonaOut)
def actualizar_persona(
    dni: str,
    datos: PersonaUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    persona = db.query(Persona).filter(Persona.dni == dni).first()
    if not persona:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No existe una persona con ese DNI.")

    for campo, valor in datos.model_dump().items():
        if campo == "dni":
            continue
        setattr(persona, campo, valor)

    db.commit()
    db.refresh(persona)
    return _a_persona_out(persona)
