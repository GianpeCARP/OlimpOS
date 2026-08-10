"""
routers/nutricion.py
----------------------
CRUD de Planes Nutricionales más un endpoint de asignación a socios,
igual que en rutinas.py.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import PlanNutricion, NutricionAsignacion, Socio, Usuario
from schemas import PlanNutricionCreate, PlanNutricionUpdate, PlanNutricionOut
from security import obtener_usuario_actual

router = APIRouter(prefix="/nutricion", tags=["Nutrición"])


def _con_conteo_asignados(plan: PlanNutricion) -> PlanNutricionOut:
    salida = PlanNutricionOut.model_validate(plan)
    salida.asignados = len(plan.asignaciones)
    return salida


@router.get("", response_model=List[PlanNutricionOut])
def listar_planes(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    planes = db.query(PlanNutricion).order_by(PlanNutricion.id.desc()).all()
    return [_con_conteo_asignados(p) for p in planes]


@router.post("", response_model=PlanNutricionOut, status_code=status.HTTP_201_CREATED)
def crear_plan(
    datos: PlanNutricionCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    nuevo_plan = PlanNutricion(**datos.model_dump())
    db.add(nuevo_plan)
    db.commit()
    db.refresh(nuevo_plan)
    return _con_conteo_asignados(nuevo_plan)


@router.put("/{plan_id}", response_model=PlanNutricionOut)
def actualizar_plan(
    plan_id: int,
    datos: PlanNutricionUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    plan = db.query(PlanNutricion).filter(PlanNutricion.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan no encontrado.")

    for campo, valor in datos.model_dump().items():
        setattr(plan, campo, valor)

    db.commit()
    db.refresh(plan)
    return _con_conteo_asignados(plan)


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    plan = db.query(PlanNutricion).filter(PlanNutricion.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan no encontrado.")

    db.delete(plan)
    db.commit()
    return None


@router.post("/{plan_id}/asignar/{socio_dni}", status_code=status.HTTP_201_CREATED)
def asignar_plan(
    plan_id: int,
    socio_dni: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    plan = db.query(PlanNutricion).filter(PlanNutricion.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan no encontrado.")

    socio = db.query(Socio).filter(Socio.dni == socio_dni).first()
    if not socio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Socio no encontrado.")

    ya_asignado = db.query(NutricionAsignacion).filter(
        NutricionAsignacion.plan_id == plan_id,
        NutricionAsignacion.socio_dni == socio_dni,
    ).first()
    if ya_asignado:
        return {"mensaje": f"{socio.nombre_completo} ya tenía este plan asignado."}

    asignacion = NutricionAsignacion(plan_id=plan_id, socio_dni=socio_dni)
    db.add(asignacion)
    db.commit()
    return {"mensaje": f"Plan asignado a {socio.nombre_completo} correctamente."}
