"""
models.py
---------
Modelos SQLAlchemy que MAPEAN el esquema de `Proyecto/db/schema.sql`.
No lo definen: si acá y allá dicen cosas distintas, manda el .sql (ver el
docstring largo de database.py).

Por eso todos los defaults se declaran como `server_default` y no como
`default`: `default` lo aplica Python antes de mandar el INSERT y no dice
nada sobre lo que realmente hace la base, mientras que `server_default`
documenta el DEFAULT que ya está escrito en el DDL. Si alguien inserta una
fila por fuera de la app (el SQL Editor de Neon, un script), el resultado es
el mismo — que es justamente lo que se quiere.

ALCANCE: solo las tablas que necesita la rebanada de autenticación —
Persona, Usuario, las de rol y sus dependencias. Las otras 24 se van
agregando cuando les toque su router. Es la misma regla que sigue types.ts
en la PWA ("no declarar las 33 tablas de una, solo las que la spec en curso
necesita"): un modelo declarado y no usado no se prueba nunca, y cuando por
fin se usa suele estar mal.
"""

from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String,
    Text, Time, func, text,
)
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import relationship

from database import Base


# =============================================================================
# ROLES DE SESIÓN
# =============================================================================

class Rol:
    """
    Roles de sesión. Los valores tienen que coincidir EXACTAMENTE con los de
    `Roles` en `Proyecto/src/frontend/src/config.ts` (minúsculas, sin tildes),
    porque son los strings que viajan dentro del JWT y contra los que la PWA
    y Flet evalúan su matriz de permisos. Si divergen, el backend autoriza
    una cosa y el frontend muestra otra.

    Ojo: NO son una columna de la base. Se derivan — ver roles_de_persona().
    """
    DUENO = "dueno"
    SOCIO = "socio"
    ENTRENADOR = "entrenador"
    NUTRICIONISTA = "nutricionista"
    RECEPCIONISTA = "recepcionista"
    # No existe Rol.PROFESOR a propósito: un Profesor da clases pero no inicia
    # sesión. Ver el comentario de RolEmpleado.PROFESOR en config.ts.


# =============================================================================
# SEDE
# =============================================================================

class Sede(Base):
    __tablename__ = "Sede"

    id_sede = Column(Integer, primary_key=True)
    id_dueno = Column(Integer, ForeignKey("Dueno.id_dueno"), nullable=False)
    nombre = Column(String(100), nullable=False)
    calle = Column(String(100))
    numero_calle = Column(String(10))
    localidad = Column(String(80))
    telefono = Column(String(30))
    capacidad_maxima = Column(Integer)
    hora_apertura = Column(Time)
    hora_cierre = Column(Time)
    abierto_24hs = Column(Boolean, server_default=text("true"))
    activo = Column(Boolean, server_default=text("true"))

    dueno = relationship("Dueno", back_populates="sedes")


# =============================================================================
# PERSONA — la única tabla con datos personales
# =============================================================================

class Persona(Base):
    """
    Toda persona del sistema vive acá una sola vez, identificada por DNI.
    Que alguien sea socio, empleado o tenga cuenta de acceso son hechos
    SEPARADOS que cuelgan de esta fila.

    La clave primaria es `id_persona` (sustituta) y no el DNI, aunque el DNI
    sea único: un DNI mal tipeado se corrige con un UPDATE de una columna, y
    no arrastrando el cambio por las diez tablas que lo referenciaban. El
    proyecto de referencia del profe usa el DNI como PK y por eso no puede
    corregirlo sin recrear filas.
    """
    __tablename__ = "Persona"

    id_persona = Column(Integer, primary_key=True)
    dni = Column(String(20), unique=True, nullable=False)
    apellido = Column(String(100), nullable=False)
    nombre = Column(String(100), nullable=False)
    sexo = Column(String(20))
    email = Column(String(150), unique=True)
    calle = Column(String(100))
    numero_calle = Column(String(10))
    localidad = Column(String(80))
    fecha_nacimiento = Column(Date)
    emergencia_nombre = Column(String(150))
    emergencia_telefono = Column(String(30))
    emergencia_parentesco = Column(String(50))
    fecha_alta = Column(DateTime, server_default=func.now())
    activo = Column(Boolean, server_default=text("true"))

    # uselist=False en las tres: una Persona tiene como mucho UNA cuenta, UNA
    # ficha de socio y UNA de empleado (las FK son UNIQUE en el esquema).
    # Los teléfonos sí son varios: por eso Telefono es 1:N y no una columna.
    usuario = relationship("Usuario", back_populates="persona", uselist=False)
    socio = relationship("Socio", back_populates="persona", uselist=False)
    empleado = relationship("Empleado", back_populates="persona", uselist=False)
    dueno = relationship("Dueno", back_populates="persona", uselist=False)
    telefonos = relationship("Telefono", back_populates="persona")

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellido}".strip()


class Telefono(Base):
    __tablename__ = "Telefono"

    id_telefono = Column(Integer, primary_key=True)
    id_persona = Column(Integer, ForeignKey("Persona.id_persona"), nullable=False)
    numero = Column(String(30), nullable=False)
    # create_type=False: el tipo `tipo_telefono` ya existe en la base, lo creó
    # schema.sql. Sin esta bandera, SQLAlchemy intenta crearlo de nuevo y
    # rompe con "type already exists".
    tipo = Column(ENUM("CELULAR", "FIJO", name="tipo_telefono", create_type=False),
                  server_default=text("'CELULAR'"))
    principal = Column(Boolean, server_default=text("false"))

    persona = relationship("Persona", back_populates="telefonos")


# =============================================================================
# USUARIO — SOLO autenticación
# =============================================================================

class Usuario(Base):
    """
    Credenciales y nada más. Sin nombre, sin dirección, sin teléfono: todo eso
    vive en Persona. Es la "Separación de Responsabilidades" que pide la
    consigna, y tiene una consecuencia práctica: se puede ser socio del
    gimnasio sin tener cuenta (pagás en el mostrador y nunca bajás la app), y
    se puede ser empleado sin acceso al sistema.

    Notar que NO hay columna `rol`. El rol se deriva de las tablas de rol
    (ver roles_de_persona) y se resuelve una sola vez, en el login.
    """
    __tablename__ = "Usuario"

    id_usuario = Column(Integer, primary_key=True)
    id_persona = Column(Integer, ForeignKey("Persona.id_persona"), unique=True, nullable=False)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    # Cuando está en True, POST /login verifica la contraseña pero NO emite
    # token. Ver migrations/001 para el razonamiento completo.
    debe_cambiar_password = Column(Boolean, nullable=False, server_default=text("true"))

    ultimo_acceso = Column(DateTime)
    intentos_fallidos = Column(Integer, server_default=text("0"))
    bloqueado = Column(Boolean, server_default=text("false"))
    activo = Column(Boolean, server_default=text("true"))

    persona = relationship("Persona", back_populates="usuario")


# =============================================================================
# TABLAS DE ROL
# =============================================================================

class Dueno(Base):
    __tablename__ = "Dueno"

    id_dueno = Column(Integer, primary_key=True)
    id_persona = Column(Integer, ForeignKey("Persona.id_persona"), unique=True, nullable=False)
    porcentaje_participacion = Column(Numeric(5, 2))

    persona = relationship("Persona", back_populates="dueno")
    sedes = relationship("Sede", back_populates="dueno")


class Empleado(Base):
    """
    Empleado es el tronco común del personal. El tipo concreto sale de cuál de
    las cuatro tablas hijas tiene fila para este empleado — no hay columna
    `tipo` ni `rol`. Un empleado sin ninguna hija es válido: está cargado pero
    todavía sin función asignada.
    """
    __tablename__ = "Empleado"

    id_empleado = Column(Integer, primary_key=True)
    id_persona = Column(Integer, ForeignKey("Persona.id_persona"), unique=True, nullable=False)
    id_sede = Column(Integer, ForeignKey("Sede.id_sede"), nullable=False)
    legajo = Column(String(20), unique=True)
    fecha_ingreso = Column(Date, nullable=False)
    fecha_egreso = Column(Date)
    activo = Column(Boolean, server_default=text("true"))

    persona = relationship("Persona", back_populates="empleado")
    sede = relationship("Sede")

    entrenador = relationship("Entrenador", back_populates="empleado", uselist=False)
    nutricionista = relationship("Nutricionista", back_populates="empleado", uselist=False)
    recepcionista = relationship("Recepcionista", back_populates="empleado", uselist=False)
    profesor = relationship("Profesor", back_populates="empleado", uselist=False)


class Entrenador(Base):
    __tablename__ = "Entrenador"

    id_entrenador = Column(Integer, primary_key=True)
    id_empleado = Column(Integer, ForeignKey("Empleado.id_empleado"), unique=True, nullable=False)
    titulo = Column(String(100))
    especialidad = Column(String(100))
    matricula = Column(String(50))

    empleado = relationship("Empleado", back_populates="entrenador")


class Nutricionista(Base):
    __tablename__ = "Nutricionista"

    id_nutricionista = Column(Integer, primary_key=True)
    id_empleado = Column(Integer, ForeignKey("Empleado.id_empleado"), unique=True, nullable=False)
    titulo = Column(String(100))
    matricula = Column(String(50))

    empleado = relationship("Empleado", back_populates="nutricionista")


class Recepcionista(Base):
    __tablename__ = "Recepcionista"

    id_recepcionista = Column(Integer, primary_key=True)
    id_empleado = Column(Integer, ForeignKey("Empleado.id_empleado"), unique=True, nullable=False)
    # varchar libre, no enum: solo los recepcionistas tienen turno asignado.
    turno_laboral = Column(String(20))

    empleado = relationship("Empleado", back_populates="recepcionista")


class Profesor(Base):
    """
    Cuarto tipo de empleado, para las Actividades. A diferencia de los otros
    tres, NO tiene rol de sesión: da clases, no usa el sistema. Por eso
    roles_de_persona() no devuelve nada para un Profesor "puro".
    """
    __tablename__ = "Profesor"

    id_profesor = Column(Integer, primary_key=True)
    id_empleado = Column(Integer, ForeignKey("Empleado.id_empleado"), unique=True, nullable=False)
    titulo = Column(String(100))
    especialidad = Column(String(100))

    empleado = relationship("Empleado", back_populates="profesor")


class Socio(Base):
    __tablename__ = "Socio"

    id_socio = Column(Integer, primary_key=True)
    id_persona = Column(Integer, ForeignKey("Persona.id_persona"), unique=True, nullable=False)
    id_sede = Column(Integer, ForeignKey("Sede.id_sede"), nullable=False)
    id_entrenador_a_cargo = Column(Integer, ForeignKey("Entrenador.id_entrenador"))
    numero_socio = Column(String(20), unique=True)
    # Nullable a propósito: no todo gimnasio usa tarjeta RFID — la asistencia
    # también se puede registrar a mano (ver Asistencia.metodo_registro).
    codigo_rfid = Column(String(50), unique=True)
    fecha_alta = Column(Date, nullable=False)
    objetivo = Column(String(150))
    observaciones = Column(Text)
    activo = Column(Boolean, server_default=text("true"))

    persona = relationship("Persona", back_populates="socio")
    sede = relationship("Sede")
    entrenador_a_cargo = relationship("Entrenador")


# =============================================================================
# COBROS — membresías, pagos y deudas
# =============================================================================

class TipoMembresia(Base):
    """
    El catálogo de planes: 'Mensual Full', 'Trimestral', etc.

    `precio_actual` es el precio de HOY. El precio al que un socio contrató se
    guarda aparte, en `Membresia.precio_pactado`, y esa duplicación aparente
    es deliberada: si el gimnasio aumenta la cuota, las membresías ya vendidas
    tienen que seguir valiendo lo que se pactó. Sin esa copia, un aumento
    reescribiría el historial de todos los pagos anteriores.
    """
    __tablename__ = "Tipo_Membresia"

    id_tipo_membresia = Column(Integer, primary_key=True)
    nombre = Column(String(50), unique=True, nullable=False)
    descripcion = Column(Text)
    duracion_dias = Column(Integer, nullable=False)
    precio_actual = Column(Numeric(10, 2), nullable=False)
    activo = Column(Boolean, server_default=text("true"))


class Promocion(Base):
    """
    Descuento por porcentaje O por monto fijo. Las dos columnas son nullables
    porque una promoción usa una u otra, no las dos.
    """
    __tablename__ = "Promocion"

    id_promocion = Column(Integer, primary_key=True)
    id_dueno = Column(Integer, ForeignKey("Dueno.id_dueno"), nullable=False)
    id_sede = Column(Integer, ForeignKey("Sede.id_sede"))
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text)
    porcentaje_descuento = Column(Numeric(5, 2))
    monto_fijo_descuento = Column(Numeric(10, 2))
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)
    activo = Column(Boolean, server_default=text("true"))


class Membresia(Base):
    """
    Lo que un socio contrató: qué plan, a qué precio, desde y hasta cuándo.

    Es una fila NUEVA por cada período. Renovar no actualiza la anterior:
    crea otra. Así queda el historial completo de cuándo estuvo al día y
    cuándo no, que es lo que permite responder "¿desde cuándo debe?".
    """
    __tablename__ = "Membresia"

    id_membresia = Column(Integer, primary_key=True)
    id_socio = Column(Integer, ForeignKey("Socio.id_socio"), nullable=False)
    id_tipo_membresia = Column(Integer, ForeignKey("Tipo_Membresia.id_tipo_membresia"),
                                nullable=False)
    id_promocion = Column(Integer, ForeignKey("Promocion.id_promocion"))
    precio_pactado = Column(Numeric(10, 2), nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_vencimiento = Column(Date)
    estado = Column(ENUM("ACTIVA", "VENCIDA", "SUSPENDIDA", "CANCELADA",
                          name="estado_membresia", create_type=False),
                     server_default=text("'ACTIVA'"))

    socio = relationship("Socio")
    tipo = relationship("TipoMembresia")
    promocion = relationship("Promocion")


class Pago(Base):
    """
    Un cobro concreto.

    NO se borra nunca: anular un pago le pone estado CANCELADO y una
    `fecha_cancelacion`. Un registro contable que desaparece es un agujero en
    la caja — si alguien cobra y después borra la fila, no queda rastro.

    `numero_comprobante` es UNIQUE: es lo que impide registrar dos veces el
    mismo pago por un doble click.
    """
    __tablename__ = "Pago"

    id_pago = Column(Integer, primary_key=True)
    id_socio = Column(Integer, ForeignKey("Socio.id_socio"), nullable=False)
    id_membresia = Column(Integer, ForeignKey("Membresia.id_membresia"))
    id_inscripcion = Column(Integer)          # FK a Inscripcion_Actividad (router pendiente)
    id_sede = Column(Integer, ForeignKey("Sede.id_sede"))
    metodo = Column(ENUM("EFECTIVO", "DEBITO", "CREDITO", "TRANSFERENCIA",
                          "BILLETERA_VIRTUAL", name="metodo_pago", create_type=False),
                     nullable=False)
    monto = Column(Numeric(10, 2), nullable=False)
    fecha_pago = Column(DateTime, nullable=False, server_default=func.now())
    periodo_desde = Column(Date)
    periodo_hasta = Column(Date)
    es_adelanto = Column(Boolean, server_default=text("false"))
    estado = Column(ENUM("CONFIRMADO", "PENDIENTE", "CANCELADO", "REEMBOLSADO",
                          name="estado_pago", create_type=False),
                     server_default=text("'CONFIRMADO'"))
    fecha_cancelacion = Column(DateTime)
    numero_comprobante = Column(String(50), unique=True)

    socio = relationship("Socio")
    membresia = relationship("Membresia")


class Deuda(Base):
    """
    Lo que un socio debe.

    `generada_automaticamente` distingue las que nacen de una membresía
    vencida de las que carga alguien a mano. Importa al auditar: una deuda
    manual es una decisión de una persona y conviene poder filtrarlas.

    Se salda con estado PAGADA y `id_pago_cancelatorio` apuntando al pago que
    la canceló. Guardar ese vínculo es lo que permite responder "¿con qué pago
    se saldó esta deuda?" sin cruzar fechas y montos a ojo.
    """
    __tablename__ = "Deuda"

    id_deuda = Column(Integer, primary_key=True)
    id_socio = Column(Integer, ForeignKey("Socio.id_socio"), nullable=False)
    id_membresia = Column(Integer, ForeignKey("Membresia.id_membresia"))
    monto = Column(Numeric(10, 2), nullable=False)
    fecha_generacion = Column(Date, nullable=False)
    fecha_vencimiento = Column(Date)
    estado = Column(ENUM("PENDIENTE", "PAGADA", "CONDONADA",
                          name="estado_deuda", create_type=False),
                     server_default=text("'PENDIENTE'"))
    generada_automaticamente = Column(Boolean, server_default=text("true"))
    id_pago_cancelatorio = Column(Integer, ForeignKey("Pago.id_pago"))
    observaciones = Column(String(250))

    socio = relationship("Socio")
    membresia = relationship("Membresia")
    pago_cancelatorio = relationship("Pago")


# =============================================================================
# RUTINAS
# =============================================================================

class Ejercicio(Base):
    """
    Catálogo compartido. Los ejercicios NO pertenecen a una rutina: 'Press de
    banca' es uno solo en todo el sistema y muchas rutinas lo referencian. Por
    eso `nombre` es UNIQUE — dos filas 'Sentadilla' partirían las estadísticas
    del ejercicio en dos.
    """
    __tablename__ = "Ejercicio"

    id_ejercicio = Column(Integer, primary_key=True)
    nombre = Column(String(100), unique=True, nullable=False)
    grupo_muscular = Column(String(50), nullable=False)
    descripcion = Column(Text)
    url_video = Column(String(255))
    requiere_maquina = Column(Boolean, server_default=text("false"))


class Rutina(Base):
    """
    Una rutina es una PLANTILLA que arma un entrenador, no algo de un socio en
    particular. Que un socio la siga se registra aparte, en Asignacion_Rutina.

    Esa separación es la que permite que una misma rutina se le asigne a
    quince personas sin duplicarla, y que cada una tenga sus propias fechas de
    inicio y fin.
    """
    __tablename__ = "Rutina"

    id_rutina = Column(Integer, primary_key=True)
    id_entrenador = Column(Integer, ForeignKey("Entrenador.id_entrenador"), nullable=False)
    nombre = Column(String(100), nullable=False)
    objetivo = Column(String(100))
    nivel = Column(String(20))
    dias_por_semana = Column(Integer)
    fecha_creacion = Column(Date, server_default=func.now())
    activo = Column(Boolean, server_default=text("true"))

    entrenador = relationship("Entrenador")
    ejercicios = relationship("RutinaEjercicio", back_populates="rutina",
                              cascade="all, delete-orphan")
    asignaciones = relationship("AsignacionRutina", back_populates="rutina")


class RutinaEjercicio(Base):
    """
    Un ejercicio dentro de una rutina, con sus series y repeticiones.

    `repeticiones` es varchar y no int a propósito: en el gimnasio se escribe
    '8-12' o 'al fallo', que no son números. Guardarlo como texto es lo que
    permite anotar lo que el entrenador realmente pone en la planilla.
    """
    __tablename__ = "Rutina_Ejercicio"

    id_rutina_ejercicio = Column(Integer, primary_key=True)
    id_rutina = Column(Integer, ForeignKey("Rutina.id_rutina"), nullable=False)
    id_ejercicio = Column(Integer, ForeignKey("Ejercicio.id_ejercicio"), nullable=False)
    dia = Column(Integer, nullable=False)
    orden = Column(Integer, nullable=False)
    series = Column(Integer)
    repeticiones = Column(String(20))
    peso_sugerido = Column(Numeric(6, 2))
    descanso_segundos = Column(Integer)
    observaciones = Column(String(200))

    rutina = relationship("Rutina", back_populates="ejercicios")
    ejercicio = relationship("Ejercicio")


class AsignacionRutina(Base):
    __tablename__ = "Asignacion_Rutina"

    id_asignacion_rutina = Column(Integer, primary_key=True)
    id_socio = Column(Integer, ForeignKey("Socio.id_socio"), nullable=False)
    id_rutina = Column(Integer, ForeignKey("Rutina.id_rutina"), nullable=False)
    id_entrenador = Column(Integer, ForeignKey("Entrenador.id_entrenador"))
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date)
    estado = Column(ENUM("ACTIVA", "FINALIZADA", "CANCELADA",
                          name="estado_asignacion", create_type=False),
                     server_default=text("'ACTIVA'"))

    socio = relationship("Socio")
    rutina = relationship("Rutina", back_populates="asignaciones")
    entrenador = relationship("Entrenador")


# =============================================================================
# NUTRICIÓN — espejo estructural de Rutinas
# =============================================================================

class Dieta(Base):
    """Plantilla que arma un nutricionista. Mismo patrón que Rutina."""
    __tablename__ = "Dieta"

    id_dieta = Column(Integer, primary_key=True)
    id_nutricionista = Column(Integer, ForeignKey("Nutricionista.id_nutricionista"),
                               nullable=False)
    nombre = Column(String(100), nullable=False)
    objetivo = Column(String(100))
    calorias_diarias = Column(Integer)
    descripcion = Column(Text)
    fecha_creacion = Column(Date, server_default=func.now())
    activo = Column(Boolean, server_default=text("true"))

    nutricionista = relationship("Nutricionista")
    comidas = relationship("Comida", back_populates="dieta", cascade="all, delete-orphan")
    asignaciones = relationship("AsignacionDieta", back_populates="dieta")


class Comida(Base):
    """Una comida de la dieta. El equivalente de RutinaEjercicio."""
    __tablename__ = "Comida"

    id_comida = Column(Integer, primary_key=True)
    id_dieta = Column(Integer, ForeignKey("Dieta.id_dieta"), nullable=False)
    dia = Column(Integer)
    momento = Column(String(30))          # Desayuno, Almuerzo, Merienda, Cena
    descripcion = Column(Text, nullable=False)
    calorias = Column(Integer)

    dieta = relationship("Dieta", back_populates="comidas")


class AsignacionDieta(Base):
    __tablename__ = "Asignacion_Dieta"

    id_asignacion_dieta = Column(Integer, primary_key=True)
    id_socio = Column(Integer, ForeignKey("Socio.id_socio"), nullable=False)
    id_dieta = Column(Integer, ForeignKey("Dieta.id_dieta"), nullable=False)
    id_nutricionista = Column(Integer, ForeignKey("Nutricionista.id_nutricionista"))
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date)
    estado = Column(ENUM("ACTIVA", "FINALIZADA", "CANCELADA",
                          name="estado_asignacion", create_type=False),
                     server_default=text("'ACTIVA'"))
    observaciones = Column(Text)

    socio = relationship("Socio")
    dieta = relationship("Dieta", back_populates="asignaciones")
    nutricionista = relationship("Nutricionista")


# =============================================================================
# DERIVACIÓN DEL ROL
# =============================================================================

def roles_de_persona(persona: Persona) -> list[str]:
    """
    Devuelve los roles de sesión de una Persona, leyéndolos de las tablas de
    rol. Esta función es la ÚNICA autoridad sobre "qué es" alguien.

    Devuelve una lista y no un string porque los roles se acumulan: el dueño
    del gimnasio suele entrenar ahí (dueno + socio), y un entrenador puede ser
    socio también. La PWA ya espera `roles: string[]` en la respuesta del
    login, así que el contrato coincide.

    Lista vacía = la persona existe pero no tiene ningún rol que habilite
    sesión (por ejemplo, un Profesor). El login tiene que rechazarla: una
    cuenta sin roles no puede ver ninguna sección, y dejarla entrar a un
    sistema donde no puede hacer nada solo genera confusión.

    Se llama UNA vez, en el login, y el resultado se firma dentro del JWT.
    Recalcularlo en cada request costaría cinco JOINs por pedido para un dato
    que no cambia durante la sesión.
    """
    roles: list[str] = []

    if persona.dueno is not None:
        roles.append(Rol.DUENO)

    if persona.socio is not None:
        roles.append(Rol.SOCIO)

    empleado = persona.empleado
    if empleado is not None:
        if empleado.entrenador is not None:
            roles.append(Rol.ENTRENADOR)
        if empleado.nutricionista is not None:
            roles.append(Rol.NUTRICIONISTA)
        if empleado.recepcionista is not None:
            roles.append(Rol.RECEPCIONISTA)
        # empleado.profesor no suma rol: ver el docstring de Profesor.

    return roles
