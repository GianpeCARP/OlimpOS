"""
routers/turnos.py
-------------------
CRUD de Turnos (clases con horario fijo dentro de la semana, ej.
"Spinning" los Lunes 08:00-09:00) más un endpoint de inscripción de
socios, igual patrón que rutinas/nutrición.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Turno, TurnoInscripcion, Empleado, Socio, Usuario
from schemas import TurnoCreate, TurnoUpdate, TurnoOut
from security import obtener_usuario_actual

router = APIRouter(prefix="/turnos", tags=["Turnos"])


def _a_turno_out(turno: Turno) -> TurnoOut:
    salida = TurnoOut.model_validate(turno)
    salida.inscriptos = len(turno.inscripciones)
    salida.instructor_nombre = turno.instructor.nombre_completo if turno.instructor else None
    return salida


@router.get("", response_model=List[TurnoOut])
def listar_turnos(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    turnos = db.query(Turno).order_by(Turno.dia_semana, Turno.hora_inicio).all()
    return [_a_turno_out(t) for t in turnos]


@router.post("", response_model=TurnoOut, status_code=status.HTTP_201_CREATED)
def crear_turno(
    datos: TurnoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    if datos.instructor_dni:
        instructor = db.query(Empleado).filter(Empleado.dni == datos.instructor_dni).first()
        if not instructor:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instructor no encontrado.")

    nuevo_turno = Turno(**datos.model_dump())
    db.add(nuevo_turno)
    db.commit()
    db.refresh(nuevo_turno)
    return _a_turno_out(nuevo_turno)


@router.put("/{turno_id}", response_model=TurnoOut)
def actualizar_turno(
    turno_id: int,
    datos: TurnoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    turno = db.query(Turno).filter(Turno.id == turno_id).first()
    if not turno:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turno no encontrado.")

    for campo, valor in datos.model_dump().items():
        setattr(turno, campo, valor)

    db.commit()
    db.refresh(turno)
    return _a_turno_out(turno)


@router.delete("/{turno_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_turno(
    turno_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    turno = db.query(Turno).filter(Turno.id == turno_id).first()
    if not turno:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turno no encontrado.")

    db.delete(turno)
    db.commit()
    return None


@router.post("/{turno_id}/inscribir/{socio_dni}", status_code=status.HTTP_201_CREATED)
def inscribir_socio(
    turno_id: int,
    socio_dni: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    turno = db.query(Turno).filter(Turno.id == turno_id).first()
    if not turno:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turno no encontrado.")

    socio = db.query(Socio).filter(Socio.dni == socio_dni).first()
    if not socio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Socio no encontrado.")

    ya_inscripto = db.query(TurnoInscripcion).filter(
        TurnoInscripcion.turno_id == turno_id,
        TurnoInscripcion.socio_dni == socio_dni,
    ).first()
    if ya_inscripto:
        return {"mensaje": f"{socio.nombre_completo} ya estaba anotado en este turno."}

    if len(turno.inscripciones) >= turno.cupo_maximo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El turno '{turno.nombre}' ya alcanzó su cupo máximo ({turno.cupo_maximo}).",
        )

    inscripcion = TurnoInscripcion(turno_id=turno_id, socio_dni=socio_dni)
    db.add(inscripcion)
    db.commit()
    return {"mensaje": f"{socio.nombre_completo} anotado en '{turno.nombre}' correctamente."}


@router.delete("/{turno_id}/inscribir/{socio_dni}", status_code=status.HTTP_204_NO_CONTENT)
def quitar_inscripcion(
    turno_id: int,
    socio_dni: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    inscripcion = db.query(TurnoInscripcion).filter(
        TurnoInscripcion.turno_id == turno_id,
        TurnoInscripcion.socio_dni == socio_dni,
    ).first()
    if not inscripcion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Esa inscripción no existe.")

    db.delete(inscripcion)
    db.commit()
    return None
