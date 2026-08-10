"""
models.py
---------
Modelos ORM (SQLAlchemy) de todo el sistema OlimpOS.

Cambio clave de esta revisión: unificación del alta de personas.

Antes, Socio y Empleado tenían sus propias columnas nombre/apellido/email,
duplicando datos que ya vivían en Persona (para el caso de los Usuarios
del sistema). Esto permitía inconsistencias: se podía cargar un Empleado
sin que existiera ninguna Persona asociada, y no había forma de saber que
un Socio y un Empleado eran, en realidad, la misma persona real.

Ahora:
- Persona (DNI como clave primaria) es la ÚNICA tabla con datos
  personales (nombre, apellido, teléfono, email, dirección).
- Socio y Empleado ya no tienen columnas de datos personales propias:
  su DNI es a la vez su clave primaria y una clave foránea hacia
  Persona. Es decir, para que exista un Socio o un Empleado, PRIMERO
  tiene que existir la Persona con ese DNI.
- Usuario (la cuenta de acceso) sigue vinculada a Persona de la misma
  forma que antes.

Gracias a esto, una misma Persona (mismo DNI) puede ser al mismo tiempo
Socio, tener una ficha de Empleado, y tener una cuenta de Usuario — sin
repetir sus datos personales en ningún lado. El alta de todo esto se
hace ahora desde una única pantalla en el frontend (Nueva Persona).
"""

import enum
from datetime import datetime, date

from sqlalchemy import (
    Column, Integer, String, Boolean, Enum, ForeignKey, DateTime, Date
)
from sqlalchemy.orm import relationship

from database import Base


# =============================================================================
# ENUMS
# =============================================================================

class RolEnum(str, enum.Enum):
    """
    Roles/funciones dentro del sistema. Se usa tanto para el rol de una
    cuenta de Usuario como para el rol de un Empleado — unificar ambos
    en el mismo enum es lo que permite que la pantalla de alta tenga un
    único selector de "función" en vez de dos conceptos separados.
    """
    PROPIETARIO = "PROPIETARIO"
    ADMIN = "ADMIN"
    ENTRENADOR = "ENTRENADOR"
    NUTRICIONISTA = "NUTRICIONISTA"
    RECEPCION = "RECEPCION"
    SOCIO = "SOCIO"


class PlanEnum(str, enum.Enum):
    BASICO = "BASICO"
    PREMIUM = "PREMIUM"
    ANUAL = "ANUAL"


class EstadoSocioEnum(str, enum.Enum):
    ACTIVO = "ACTIVO"
    VENCIDO = "VENCIDO"
    SUSPENDIDO = "SUSPENDIDO"


class TurnoLaboralEnum(str, enum.Enum):
    """Turno de trabajo de un Empleado (Mañana/Tarde/Noche)."""
    MANANA = "MANANA"
    TARDE = "TARDE"
    NOCHE = "NOCHE"


class EstadoEmpleadoEnum(str, enum.Enum):
    ACTIVO = "ACTIVO"
    INACTIVO = "INACTIVO"


class NivelEnum(str, enum.Enum):
    PRINCIPIANTE = "PRINCIPIANTE"
    INTERMEDIO = "INTERMEDIO"
    AVANZADO = "AVANZADO"


class ObjetivoEnum(str, enum.Enum):
    MASA_MUSCULAR = "MASA_MUSCULAR"
    BAJAR_PESO = "BAJAR_PESO"
    MANTENIMIENTO = "MANTENIMIENTO"
    ALTO_RENDIMIENTO = "ALTO_RENDIMIENTO"


class DiaSemanaEnum(str, enum.Enum):
    LUNES = "LUNES"
    MARTES = "MARTES"
    MIERCOLES = "MIERCOLES"
    JUEVES = "JUEVES"
    VIERNES = "VIERNES"
    SABADO = "SABADO"
    DOMINGO = "DOMINGO"


# =============================================================================
# PERSONA — única fuente de datos personales de todo el sistema
# =============================================================================

class Persona(Base):
    __tablename__ = "personas"

    dni = Column(String(15), primary_key=True)
    nombre = Column(String, nullable=False)
    apellido = Column(String, nullable=False)
    telefono = Column(String, nullable=True)
    email = Column(String, nullable=True)  # email de contacto (no es necesariamente el de login)
    calle = Column(String, nullable=True)
    numero = Column(String, nullable=True)
    localidad = Column(String, nullable=True)
    fecha_nacimiento = Column(Date, nullable=True)

    creado_en = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relaciones 1:1 hacia cada "rol" que esta persona puede tener.
    # uselist=False porque una Persona tiene, como mucho, un Socio, un
    # Empleado y un Usuario asociados (nunca una lista de cada uno).
    usuario = relationship("Usuario", back_populates="persona", uselist=False,
                            cascade="all, delete-orphan")
    socio = relationship("Socio", back_populates="persona", uselist=False,
                          cascade="all, delete-orphan")
    empleado = relationship("Empleado", back_populates="persona", uselist=False,
                             cascade="all, delete-orphan")

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellido}".strip()


# =============================================================================
# USUARIO — cuentas de acceso al sistema
# =============================================================================

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    dni = Column(String(15), ForeignKey("personas.dni"), unique=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)  # email de LOGIN
    password_hash = Column(String, nullable=False)
    rol = Column(Enum(RolEnum), nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
    debe_cambiar_password = Column(Boolean, default=False, nullable=False)

    creado_en = Column(DateTime, default=datetime.utcnow, nullable=False)

    persona = relationship("Persona", back_populates="usuario")

    @property
    def nombre(self) -> str:
        return self.persona.nombre_completo if self.persona else "Usuario"


# =============================================================================
# SOCIO — la "función" de socio de una Persona ya cargada
# =============================================================================

class Socio(Base):
    __tablename__ = "socios"

    # El DNI es a la vez la clave primaria de esta tabla Y una clave
    # foránea hacia Persona: no puede existir un Socio sin que exista
    # antes una Persona con ese mismo DNI.
    dni = Column(String(15), ForeignKey("personas.dni"), primary_key=True)

    plan = Column(Enum(PlanEnum), nullable=False, default=PlanEnum.BASICO)
    estado = Column(Enum(EstadoSocioEnum), nullable=False, default=EstadoSocioEnum.ACTIVO)
    fecha_alta = Column(Date, default=date.today, nullable=False)
    fecha_vencimiento = Column(Date, nullable=True)

    persona = relationship("Persona", back_populates="socio")
    rutinas_asignadas = relationship("RutinaAsignacion", back_populates="socio", cascade="all, delete-orphan")
    planes_asignados = relationship("NutricionAsignacion", back_populates="socio", cascade="all, delete-orphan")
    turnos_inscriptos = relationship("TurnoInscripcion", back_populates="socio", cascade="all, delete-orphan")

    @property
    def nombre_completo(self) -> str:
        return self.persona.nombre_completo if self.persona else ""


# =============================================================================
# EMPLEADO — la "función" de empleado de una Persona ya cargada
# =============================================================================

class Empleado(Base):
    __tablename__ = "empleados"

    dni = Column(String(15), ForeignKey("personas.dni"), primary_key=True)

    rol = Column(Enum(RolEnum), nullable=False)  # mismo enum que Usuario.rol
    turno = Column(Enum(TurnoLaboralEnum), nullable=False, default=TurnoLaboralEnum.MANANA)
    estado = Column(Enum(EstadoEmpleadoEnum), nullable=False, default=EstadoEmpleadoEnum.ACTIVO)

    persona = relationship("Persona", back_populates="empleado")
    turnos_a_cargo = relationship("Turno", back_populates="instructor")

    @property
    def nombre_completo(self) -> str:
        return self.persona.nombre_completo if self.persona else ""


# =============================================================================
# RUTINA — catálogo de rutinas + asignación a socios
# =============================================================================

class Rutina(Base):
    __tablename__ = "rutinas"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    nivel = Column(Enum(NivelEnum), nullable=False, default=NivelEnum.PRINCIPIANTE)
    dias_por_semana = Column(Integer, nullable=False, default=3)
    duracion_minutos = Column(Integer, nullable=False, default=60)
    descripcion = Column(String, nullable=True)

    asignaciones = relationship("RutinaAsignacion", back_populates="rutina", cascade="all, delete-orphan")


class RutinaAsignacion(Base):
    __tablename__ = "rutina_asignaciones"

    id = Column(Integer, primary_key=True, index=True)
    rutina_id = Column(Integer, ForeignKey("rutinas.id"), nullable=False)
    socio_dni = Column(String(15), ForeignKey("socios.dni"), nullable=False)
    fecha_asignacion = Column(Date, default=date.today, nullable=False)

    rutina = relationship("Rutina", back_populates="asignaciones")
    socio = relationship("Socio", back_populates="rutinas_asignadas")


# =============================================================================
# PLAN NUTRICIONAL — catálogo + asignación a socios
# =============================================================================

class PlanNutricion(Base):
    __tablename__ = "planes_nutricion"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    calorias = Column(Integer, nullable=False)
    objetivo = Column(Enum(ObjetivoEnum), nullable=False, default=ObjetivoEnum.MANTENIMIENTO)
    proteinas_g = Column(Integer, nullable=True)
    carbohidratos_g = Column(Integer, nullable=True)
    grasas_g = Column(Integer, nullable=True)
    notas = Column(String, nullable=True)

    asignaciones = relationship("NutricionAsignacion", back_populates="plan", cascade="all, delete-orphan")


class NutricionAsignacion(Base):
    __tablename__ = "nutricion_asignaciones"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("planes_nutricion.id"), nullable=False)
    socio_dni = Column(String(15), ForeignKey("socios.dni"), nullable=False)
    fecha_asignacion = Column(Date, default=date.today, nullable=False)

    plan = relationship("PlanNutricion", back_populates="asignaciones")
    socio = relationship("Socio", back_populates="planes_asignados")


# =============================================================================
# TURNOS — clases/horarios del gimnasio
# =============================================================================

class Turno(Base):
    __tablename__ = "turnos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    dia_semana = Column(Enum(DiaSemanaEnum), nullable=False)
    hora_inicio = Column(String(5), nullable=False)
    hora_fin = Column(String(5), nullable=False)

    instructor_dni = Column(String(15), ForeignKey("empleados.dni"), nullable=True)
    cupo_maximo = Column(Integer, nullable=False, default=15)
    color = Column(String(9), nullable=False, default="#FF5722")

    instructor = relationship("Empleado", back_populates="turnos_a_cargo")
    inscripciones = relationship("TurnoInscripcion", back_populates="turno", cascade="all, delete-orphan")


class TurnoInscripcion(Base):
    __tablename__ = "turno_inscripciones"

    id = Column(Integer, primary_key=True, index=True)
    turno_id = Column(Integer, ForeignKey("turnos.id"), nullable=False)
    socio_dni = Column(String(15), ForeignKey("socios.dni"), nullable=False)
    fecha_inscripcion = Column(Date, default=date.today, nullable=False)

    turno = relationship("Turno", back_populates="inscripciones")
    socio = relationship("Socio", back_populates="turnos_inscriptos")
