"""
routers/rutinas.py
--------------------
CRUD de Rutinas más un endpoint para asignar una rutina a un socio
(alimenta el botón "Asignar" del frontend, que hasta ahora era decorativo).
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Rutina, RutinaAsignacion, Socio, Usuario
from schemas import RutinaCreate, RutinaUpdate, RutinaOut
from security import obtener_usuario_actual

router = APIRouter(prefix="/rutinas", tags=["Rutinas"])


def _con_conteo_asignados(rutina: Rutina) -> RutinaOut:
    """Arma el RutinaOut agregando la cantidad de socios asignados."""
    salida = RutinaOut.model_validate(rutina)
    salida.asignados = len(rutina.asignaciones)
    return salida


@router.get("", response_model=List[RutinaOut])
def listar_rutinas(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    rutinas = db.query(Rutina).order_by(Rutina.id.desc()).all()
    return [_con_conteo_asignados(r) for r in rutinas]


@router.post("", response_model=RutinaOut, status_code=status.HTTP_201_CREATED)
def crear_rutina(
    datos: RutinaCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    nueva_rutina = Rutina(**datos.model_dump())
    db.add(nueva_rutina)
    db.commit()
    db.refresh(nueva_rutina)
    return _con_conteo_asignados(nueva_rutina)


@router.put("/{rutina_id}", response_model=RutinaOut)
def actualizar_rutina(
    rutina_id: int,
    datos: RutinaUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    rutina = db.query(Rutina).filter(Rutina.id == rutina_id).first()
    if not rutina:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rutina no encontrada.")

    for campo, valor in datos.model_dump().items():
        setattr(rutina, campo, valor)

    db.commit()
    db.refresh(rutina)
    return _con_conteo_asignados(rutina)


@router.delete("/{rutina_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_rutina(
    rutina_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    rutina = db.query(Rutina).filter(Rutina.id == rutina_id).first()
    if not rutina:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rutina no encontrada.")

    db.delete(rutina)
    db.commit()
    return None


@router.post("/{rutina_id}/asignar/{socio_dni}", status_code=status.HTTP_201_CREATED)
def asignar_rutina(
    rutina_id: int,
    socio_dni: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    """Asigna una rutina a un socio. Si ya estaba asignada, no la duplica."""
    rutina = db.query(Rutina).filter(Rutina.id == rutina_id).first()
    if not rutina:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rutina no encontrada.")

    socio = db.query(Socio).filter(Socio.dni == socio_dni).first()
    if not socio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Socio no encontrado.")

    ya_asignada = db.query(RutinaAsignacion).filter(
        RutinaAsignacion.rutina_id == rutina_id,
        RutinaAsignacion.socio_dni == socio_dni,
    ).first()
    if ya_asignada:
        return {"mensaje": f"{socio.nombre_completo} ya tenía esta rutina asignada."}

    asignacion = RutinaAsignacion(rutina_id=rutina_id, socio_dni=socio_dni)
    db.add(asignacion)
    db.commit()
    return {"mensaje": f"Rutina asignada a {socio.nombre_completo} correctamente."}
