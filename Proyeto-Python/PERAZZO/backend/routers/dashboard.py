"""
routers/dashboard.py
----------------------
Estadísticas y feed de actividad reciente para la vista Dashboard.

Nota honesta sobre "ingresos_mes": el sistema todavía no tiene un modelo
de Pagos, así que ese valor queda como placeholder ($0) hasta que se
agregue esa tabla. "clases_hoy" en cambio ya sale de datos reales, ahora
que existe el modelo de Turnos.
"""

from datetime import date
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Socio, Turno, RutinaAsignacion, NutricionAsignacion, Usuario,
    EstadoSocioEnum, DiaSemanaEnum,
)
from schemas import DashboardStats, StatItem, ActividadItem
from security import obtener_usuario_actual

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

# date.weekday(): 0=lunes ... 6=domingo — coincide con el orden de DiaSemanaEnum
_DIAS_ORDENADOS = [
    DiaSemanaEnum.LUNES, DiaSemanaEnum.MARTES, DiaSemanaEnum.MIERCOLES,
    DiaSemanaEnum.JUEVES, DiaSemanaEnum.VIERNES, DiaSemanaEnum.SABADO, DiaSemanaEnum.DOMINGO,
]


@router.get("/stats", response_model=DashboardStats)
def obtener_stats(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    hoy = date.today()
    dia_hoy = _DIAS_ORDENADOS[hoy.weekday()]

    socios_activos = db.query(Socio).filter(Socio.estado == EstadoSocioEnum.ACTIVO).count()

    nuevos_mes = db.query(Socio).filter(Socio.fecha_alta >= hoy.replace(day=1)).count()

    clases_hoy = db.query(Turno).filter(Turno.dia_semana == dia_hoy).count()

    return DashboardStats(
        socios_activos=StatItem(valor=str(socios_activos), delta="+0", tendencia="up"),
        # TODO: reemplazar con datos reales cuando exista un modelo de Pagos
        ingresos_mes=StatItem(valor="$0", delta="0%", tendencia="up"),
        clases_hoy=StatItem(valor=str(clases_hoy), delta="+0", tendencia="up"),
        nuevos_mes=StatItem(valor=str(nuevos_mes), delta="+0", tendencia="up"),
    )


@router.get("/actividad", response_model=List[ActividadItem])
def obtener_actividad_reciente(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual),
):
    eventos = []

    ultimos_socios = db.query(Socio).order_by(Socio.fecha_alta.desc()).limit(5).all()
    for s in ultimos_socios:
        eventos.append({
            "tipo": "nuevo_socio",
            "desc": f"{s.nombre_completo} se registró al plan {s.plan.value.title()}",
            "fecha": s.fecha_alta,
        })

    ultimas_rutinas = db.query(RutinaAsignacion).order_by(
        RutinaAsignacion.fecha_asignacion.desc()
    ).limit(5).all()
    for a in ultimas_rutinas:
        eventos.append({
            "tipo": "rutina",
            "desc": f"Rutina '{a.rutina.nombre}' asignada a {a.socio.nombre_completo}",
            "fecha": a.fecha_asignacion,
        })

    ultimos_planes = db.query(NutricionAsignacion).order_by(
        NutricionAsignacion.fecha_asignacion.desc()
    ).limit(5).all()
    for a in ultimos_planes:
        eventos.append({
            "tipo": "nutricion",
            "desc": f"Plan '{a.plan.nombre}' asignado a {a.socio.nombre_completo}",
            "fecha": a.fecha_asignacion,
        })

    eventos.sort(key=lambda e: e["fecha"], reverse=True)
    eventos = eventos[:5]

    return [
        ActividadItem(tipo=e["tipo"], desc=e["desc"], hora=e["fecha"].strftime("%d/%m/%Y"))
        for e in eventos
    ]
