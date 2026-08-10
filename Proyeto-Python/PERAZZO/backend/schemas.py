"""
schemas.py
----------
Esquemas Pydantic para entrada/salida de la API.
"""

from datetime import date
from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict

from models import (
    RolEnum, PlanEnum, EstadoSocioEnum, TurnoLaboralEnum,
    EstadoEmpleadoEnum, NivelEnum, ObjetivoEnum, DiaSemanaEnum,
)


# =============================================================================
# AUTENTICACIÓN
# =============================================================================

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    debe_cambiar_password: bool
    access_token: Optional[str] = None
    token_type: str = "bearer"
    rol: Optional[RolEnum] = None
    nombre: Optional[str] = None


class CambiarPasswordRequest(BaseModel):
    email: EmailStr
    password_actual: str
    password_nueva: str


# =============================================================================
# PERSONAS — la única fuente de datos personales
# =============================================================================

class PersonaCreate(BaseModel):
    dni: str
    nombre: str
    apellido: str
    telefono: Optional[str] = None
    email: Optional[str] = None
    calle: Optional[str] = None
    numero: Optional[str] = None
    localidad: Optional[str] = None
    fecha_nacimiento: Optional[date] = None


class PersonaUpdate(PersonaCreate):
    pass


class PersonaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    dni: str
    nombre: str
    apellido: str
    telefono: Optional[str] = None
    email: Optional[str] = None
    calle: Optional[str] = None
    numero: Optional[str] = None
    localidad: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    # Flags de conveniencia para la pantalla de alta: le dicen al frontend
    # qué "funciones" ya tiene esta persona, para no ofrecer crearlas de nuevo.
    tiene_usuario: bool = False
    tiene_socio: bool = False
    tiene_empleado: bool = False


# =============================================================================
# USUARIOS (cuentas del sistema)
# =============================================================================

class UsuarioCreate(BaseModel):
    dni: str
    email: EmailStr
    rol: RolEnum
    password_inicial: str


class UsuarioUpdate(BaseModel):
    rol: RolEnum


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    dni: str
    nombre: str
    email: str
    rol: RolEnum
    activo: bool
    debe_cambiar_password: bool


# =============================================================================
# SOCIOS — ya no llevan datos personales propios (ver Persona)
# =============================================================================

class SocioCreate(BaseModel):
    dni: str  # debe corresponder a una Persona ya cargada
    plan: PlanEnum = PlanEnum.BASICO
    estado: EstadoSocioEnum = EstadoSocioEnum.ACTIVO
    fecha_vencimiento: Optional[date] = None


class SocioUpdate(BaseModel):
    plan: PlanEnum = PlanEnum.BASICO
    estado: EstadoSocioEnum = EstadoSocioEnum.ACTIVO
    fecha_vencimiento: Optional[date] = None


class SocioOut(BaseModel):
    dni: str
    nombre: str
    apellido: str
    email: Optional[str] = None
    telefono: Optional[str] = None
    plan: PlanEnum
    estado: EstadoSocioEnum
    fecha_alta: date
    fecha_vencimiento: Optional[date] = None


# =============================================================================
# PERSONAL (empleados) — ya no llevan datos personales propios
# =============================================================================

class EmpleadoCreate(BaseModel):
    dni: str  # debe corresponder a una Persona ya cargada
    rol: RolEnum
    turno: TurnoLaboralEnum = TurnoLaboralEnum.MANANA
    estado: EstadoEmpleadoEnum = EstadoEmpleadoEnum.ACTIVO


class EmpleadoUpdate(BaseModel):
    rol: RolEnum
    turno: TurnoLaboralEnum = TurnoLaboralEnum.MANANA
    estado: EstadoEmpleadoEnum = EstadoEmpleadoEnum.ACTIVO


class EmpleadoOut(BaseModel):
    dni: str
    nombre: str
    apellido: str
    email: Optional[str] = None
    rol: RolEnum
    turno: TurnoLaboralEnum
    estado: EstadoEmpleadoEnum


# =============================================================================
# RUTINAS
# =============================================================================

class RutinaCreate(BaseModel):
    nombre: str
    nivel: NivelEnum = NivelEnum.PRINCIPIANTE
    dias_por_semana: int = 3
    duracion_minutos: int = 60
    descripcion: Optional[str] = None


class RutinaUpdate(RutinaCreate):
    pass


class RutinaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    nivel: NivelEnum
    dias_por_semana: int
    duracion_minutos: int
    descripcion: Optional[str] = None
    asignados: int = 0


# =============================================================================
# PLANES NUTRICIONALES
# =============================================================================

class PlanNutricionCreate(BaseModel):
    nombre: str
    calorias: int
    objetivo: ObjetivoEnum = ObjetivoEnum.MANTENIMIENTO
    proteinas_g: Optional[int] = None
    carbohidratos_g: Optional[int] = None
    grasas_g: Optional[int] = None
    notas: Optional[str] = None


class PlanNutricionUpdate(PlanNutricionCreate):
    pass


class PlanNutricionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    calorias: int
    objetivo: ObjetivoEnum
    proteinas_g: Optional[int] = None
    carbohidratos_g: Optional[int] = None
    grasas_g: Optional[int] = None
    notas: Optional[str] = None
    asignados: int = 0


# =============================================================================
# TURNOS
# =============================================================================

class TurnoCreate(BaseModel):
    nombre: str
    dia_semana: DiaSemanaEnum
    hora_inicio: str
    hora_fin: str
    instructor_dni: Optional[str] = None
    cupo_maximo: int = 15
    color: str = "#FF5722"


class TurnoUpdate(TurnoCreate):
    pass


class TurnoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    dia_semana: DiaSemanaEnum
    hora_inicio: str
    hora_fin: str
    instructor_dni: Optional[str] = None
    instructor_nombre: Optional[str] = None
    cupo_maximo: int
    color: str
    inscriptos: int = 0


# =============================================================================
# DASHBOARD
# =============================================================================

class StatItem(BaseModel):
    valor: str
    delta: str
    tendencia: str


class DashboardStats(BaseModel):
    socios_activos: StatItem
    ingresos_mes: StatItem
    clases_hoy: StatItem
    nuevos_mes: StatItem


class ActividadItem(BaseModel):
    tipo: str
    desc: str
    hora: str
