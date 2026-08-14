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
    # NO hay `id_entrenador_a_cargo`. La tenía, y era el mismo error que
    # Telefono ya evitaba para los teléfonos: meter en una columna de valor
    # único un hecho que en la realidad es múltiple (un socio puede tener a la
    # vez uno de musculación y otro de funcional) y cambiante (reasignarlo
    # pisaba el valor anterior y el historial se perdía). Ahora vive en
    # Asignacion_Entrenador, igual que las rutinas y las dietas. Ver la
    # migración 003.
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
    # Los entrenadores a cargo se consultan por Asignacion_Entrenador, que
    # además dice desde cuándo y permite más de uno a la vez. No hay atajo
    # `socio.entrenador_a_cargo` porque ya no hay UN entrenador que devolver.
    entrenadores = relationship("AsignacionEntrenador", viewonly=True)


class RegistroSalud(Base):
    """
    Una medición del socio: peso, grasa, masa muscular.

    Es una fila POR FECHA, y ese es todo el punto: el valor de hoy no
    reemplaza al de la semana pasada. La serie completa es lo que permite
    dibujar la evolución, que es el único motivo por el que alguien carga su
    peso en una app de gimnasio.

    `altura` se repite en cada fila aunque casi nunca cambie. Es redundante a
    propósito: separarla en otra tabla por una columna que se escribe una vez
    complicaría más de lo que ahorra, y así cada medición queda autocontenida
    para calcular el IMC de ese día.
    """
    __tablename__ = "Registro_Salud"

    id_registro_salud = Column(Integer, primary_key=True)
    id_socio = Column(Integer, ForeignKey("Socio.id_socio"), nullable=False)
    fecha = Column(Date, nullable=False)
    peso = Column(Numeric(5, 2))
    altura = Column(Numeric(3, 2))
    grasa_corporal = Column(Numeric(4, 2))
    masa_muscular = Column(Numeric(5, 2))
    observaciones = Column(Text)

    socio = relationship("Socio")


class Baja(Base):
    """
    El registro de por qué y cuándo se dio de baja a un socio.

    Es una tabla aparte y no un par de columnas en Socio por dos razones: un
    socio puede darse de baja y volver más de una vez (y cada baja tiene su
    motivo), y así el historial queda completo aunque hoy esté activo.

    `tipo` distingue la baja voluntaria de la por mora y de la
    administrativa. Importa al analizar: un gimnasio que pierde socios por
    mora tiene un problema distinto al que los pierde porque se mudan.
    """
    __tablename__ = "Baja"

    id_baja = Column(Integer, primary_key=True)
    id_socio = Column(Integer, ForeignKey("Socio.id_socio"), nullable=False)
    fecha_baja = Column(Date, nullable=False)
    tipo = Column(ENUM("VOLUNTARIA", "MORA", "ADMINISTRATIVA",
                        name="tipo_baja", create_type=False))
    motivo = Column(Text)
    # NO hay `id_registrado_por` acá. Lo tuvo un rato porque Asistencia sí lo
    # tiene y parecía razonable guardar también quién dio la baja, pero
    # schema.sql —que es de donde se crea la base— no declara esa columna en
    # Baja, así que el INSERT fallaba con un 500 al primer intento real.
    # Si alguna vez hace falta, se agrega primero en schema.sql y recién
    # después acá; el modelo no puede inventar columnas.

    socio = relationship("Socio")


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


class AsignacionEntrenador(Base):
    """
    Qué entrenador está a cargo de qué socio, con historial.

    Reemplaza a la vieja columna Socio.id_entrenador_a_cargo. Mismo patrón que
    AsignacionRutina y AsignacionDieta, con UNA diferencia deliberada: acá sí
    se admiten varias filas ACTIVA por socio al mismo tiempo. Un socio puede
    tener a la vez un entrenador de musculación y otro de funcional, y eso es
    normal, no un error de datos — por eso el índice único es por
    (socio, entrenador, fecha_inicio) y no por socio.
    """
    __tablename__ = "Asignacion_Entrenador"

    id_asignacion_entrenador = Column(Integer, primary_key=True)
    id_socio = Column(Integer, ForeignKey("Socio.id_socio"), nullable=False)
    id_entrenador = Column(Integer, ForeignKey("Entrenador.id_entrenador"), nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date)
    estado = Column(ENUM("ACTIVA", "FINALIZADA", "CANCELADA",
                          name="estado_asignacion", create_type=False),
                     server_default=text("'ACTIVA'"))

    socio = relationship("Socio")
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
# ACTIVIDADES — clases con horario (yoga, spinning, boxeo)
# =============================================================================

class Actividad(Base):
    """
    El catálogo: qué clases ofrece el gimnasio.

    `horas_anticipacion_cancelacion` es una regla de negocio POR ACTIVIDAD, no
    global: cancelar un spinning con 2 horas de aviso puede estar bien, pero
    una clase personalizada quizás exija 24. Guardarlo acá permite que cada
    una tenga su propia política sin tocar código.
    """
    __tablename__ = "Actividad"

    id_actividad = Column(Integer, primary_key=True)
    nombre = Column(String(80), unique=True, nullable=False)
    descripcion = Column(Text)
    cupo_default = Column(Integer, nullable=False)
    precio_clase_suelta = Column(Numeric(10, 2), nullable=False)
    horas_anticipacion_cancelacion = Column(Integer, nullable=False, server_default=text("0"))
    # Minutos después de la hora del turno en que todavía se acepta la llegada.
    # Pasado ese margen la reserva cuenta como ausente y la tarjeta no valida
    # ese turno. Por actividad y no como constante: a una clase de Yoga llegar
    # 20 tarde es no ir; a la sala de musculación, que está abierta toda la
    # tarde, casi no aplica.
    minutos_tolerancia = Column(Integer, nullable=False, server_default=text("15"))
    activo = Column(Boolean, server_default=text("true"))

    planes = relationship("PlanActividad", back_populates="actividad")


class PlanActividad(Base):
    """
    Un abono para una actividad: 'Yoga 2 veces por semana'.

    `tipo_limite` + `cantidad` es lo que define el plan: POR_SEMANA/2 o
    POR_MES/8. Modelarlo como dos columnas en vez de un texto libre es lo que
    permite CONTAR las clases usadas y frenar al socio cuando se pasa.
    """
    __tablename__ = "Plan_Actividad"

    id_plan_actividad = Column(Integer, primary_key=True)
    id_actividad = Column(Integer, ForeignKey("Actividad.id_actividad"), nullable=False)
    nombre = Column(String(80), nullable=False)
    tipo_limite = Column(ENUM("POR_SEMANA", "POR_MES", name="tipo_limite",
                               create_type=False), nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio = Column(Numeric(10, 2), nullable=False)
    activo = Column(Boolean, server_default=text("true"))

    actividad = relationship("Actividad", back_populates="planes")


class InscripcionActividad(Base):
    """
    Un socio anotado a un plan, con su período y su saldo de clases.

    `clases_restantes` es un contador que se decrementa al reservar. Podría
    calcularse contando reservas, pero tenerlo materializado hace que el
    chequeo de "¿le quedan clases?" sea leer un número en vez de una consulta
    agregada en cada reserva.

    `precio_pactado` congela el precio del plan al momento de contratarlo, por
    la misma razón que `Membresia.precio_pactado`: un aumento no puede
    reescribir lo que alguien ya pagó.
    """
    __tablename__ = "Inscripcion_Actividad"

    id_inscripcion = Column(Integer, primary_key=True)
    id_socio = Column(Integer, ForeignKey("Socio.id_socio"), nullable=False)
    id_plan_actividad = Column(Integer, ForeignKey("Plan_Actividad.id_plan_actividad"),
                                nullable=False)
    id_membresia = Column(Integer, ForeignKey("Membresia.id_membresia"), nullable=False)
    precio_pactado = Column(Numeric(10, 2), nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_vencimiento = Column(Date, nullable=False)
    clases_restantes = Column(Integer)
    estado = Column(ENUM("ACTIVA", "VENCIDA", "CANCELADA",
                          name="estado_inscripcion", create_type=False),
                     server_default=text("'ACTIVA'"))

    socio = relationship("Socio")
    plan = relationship("PlanActividad")
    membresia = relationship("Membresia")


class ProfesorActividad(Base):
    """
    Qué profesor puede dictar qué actividad. Tabla puente pura: su clave
    primaria son las dos FK juntas, así que la misma combinación no se puede
    repetir.
    """
    __tablename__ = "Profesor_Actividad"

    id_profesor = Column(Integer, ForeignKey("Profesor.id_profesor"), primary_key=True)
    id_actividad = Column(Integer, ForeignKey("Actividad.id_actividad"), primary_key=True)

    profesor = relationship("Profesor")
    actividad = relationship("Actividad")


class HorarioActividad(Base):
    """
    El horario semanal de una actividad: 'Yoga, los lunes a las 19:00'.

    Existe para que nadie cargue turnos a mano. Antes Turno era la única
    forma de decir que había clase, y como es una fila POR FECHA, alguien
    tenía que crear dos filas por semana para siempre; el día que se olvidaba,
    la clase no existía y nadie podía reservarla.

    Ahora la actividad declara su horario y el backend genera los turnos de
    las próximas semanas a partir de esto. Los turnos siguen siendo filas
    reales y editables: se puede cancelar el del lunes que viene por feriado
    sin tocar el horario.

    `vigente_hasta` en None significa indefinido. Está para poder decir "Yoga
    pasa a las 20:00 desde marzo" sin borrar el horario viejo ni perder los
    turnos ya generados con el anterior.
    """
    __tablename__ = "Horario_Actividad"

    id_horario_actividad = Column(Integer, primary_key=True)
    id_sede = Column(Integer, ForeignKey("Sede.id_sede"), nullable=False)
    id_actividad = Column(Integer, ForeignKey("Actividad.id_actividad"), nullable=False)
    # ISO: 1 = lunes ... 7 = domingo. ISO y no el DOW nativo de Postgres
    # (0 = domingo) porque acá la semana empieza el lunes, y porque
    # date.isoweekday() de Python devuelve exactamente esto — la generación
    # compara sin convertir nada.
    dia_semana = Column(Integer, nullable=False)
    hora = Column(Time, nullable=False)
    cupo = Column(Integer, nullable=False)
    id_profesor = Column(Integer, ForeignKey("Profesor.id_profesor"))
    vigente_desde = Column(Date, nullable=False)
    vigente_hasta = Column(Date)
    activo = Column(Boolean, server_default=text("true"))

    sede = relationship("Sede")
    actividad = relationship("Actividad")
    profesor = relationship("Profesor")


class Turno(Base):
    """
    Una clase concreta: 'Yoga, el martes 12 a las 18:00'.

    Es una fila POR FECHA, no un horario recurrente. Eso permite cancelar una
    clase puntual (con su motivo), cambiarle el profesor o ampliarle el cupo
    sin afectar al resto de las semanas.

    La mayoría los genera el sistema a partir de HorarioActividad. Los que
    tienen `id_horario_actividad` en None son los cargados a mano —una clase
    extra, un recuperatorio— y la generación automática no los toca nunca.
    """
    __tablename__ = "Turno"

    id_turno = Column(Integer, primary_key=True)
    id_sede = Column(Integer, ForeignKey("Sede.id_sede"), nullable=False)
    id_actividad = Column(Integer, ForeignKey("Actividad.id_actividad"), nullable=False)
    fecha = Column(Date, nullable=False)
    hora = Column(Time, nullable=False)
    cupo_maximo = Column(Integer, nullable=False)
    estado = Column(ENUM("HABILITADO", "CANCELADO", name="estado_turno",
                          create_type=False), server_default=text("'HABILITADO'"))
    id_entrenador_a_cargo = Column(Integer, ForeignKey("Entrenador.id_entrenador"))
    id_profesor = Column(Integer, ForeignKey("Profesor.id_profesor"))
    id_horario_actividad = Column(
        Integer, ForeignKey("Horario_Actividad.id_horario_actividad"))
    motivo_cancelacion = Column(String(200))
    observaciones = Column(String(200))

    sede = relationship("Sede")
    actividad = relationship("Actividad")
    profesor = relationship("Profesor")
    horario = relationship("HorarioActividad")
    reservas = relationship("Reserva", back_populates="turno")


class Reserva(Base):
    """
    Un socio anotado a un turno.

    Cancelar NO borra la fila: le pone CANCELADA_SOCIO o CANCELADA_GIMNASIO.
    La distinción importa para la regla de devolución — si la clase la canceló
    el gimnasio, la clase se le devuelve al socio; si la canceló él fuera de
    término, no.

    `es_clase_suelta` distingue a quien pagó una clase individual de quien usa
    su abono: los primeros no descuentan de ningún saldo.
    """
    __tablename__ = "Reserva"

    id_reserva = Column(Integer, primary_key=True)
    id_turno = Column(Integer, ForeignKey("Turno.id_turno"), nullable=False)
    id_socio = Column(Integer, ForeignKey("Socio.id_socio"), nullable=False)
    id_inscripcion = Column(Integer, ForeignKey("Inscripcion_Actividad.id_inscripcion"))
    es_clase_suelta = Column(Boolean, server_default=text("false"))
    id_pago = Column(Integer, ForeignKey("Pago.id_pago"))
    fecha_reserva = Column(DateTime, server_default=func.now())
    # EN_ESPERA va en la lista aunque el resto del código lo trate aparte: si
    # falta acá, SQLAlchemy no puede LEER las filas que ya lo tienen y
    # cualquier consulta que las toque revienta con un LookupError. Se
    # descubrió así, no leyendo el código.
    estado = Column(ENUM("RESERVADA", "EN_ESPERA",
                          "CANCELADA_SOCIO", "CANCELADA_GIMNASIO",
                          name="estado_reserva", create_type=False),
                     server_default=text("'RESERVADA'"))
    fecha_cancelacion = Column(DateTime)

    turno = relationship("Turno", back_populates="reservas")
    socio = relationship("Socio")
    inscripcion = relationship("InscripcionActividad")


# =============================================================================
# ASISTENCIA
# =============================================================================

class Asistencia(Base):
    """
    Un ingreso al gimnasio.

    `metodo_registro` distingue el fichaje con tarjeta RFID del que carga una
    persona a mano. Importa al auditar: un registro MANUAL es una decisión de
    alguien del mostrador y conviene poder filtrarlos.

    `id_reserva` es opcional: entrar a entrenar por tu cuenta no está asociado
    a ninguna clase. Cuando sí lo está, vincula el ingreso con el turno al que
    vino.
    """
    __tablename__ = "Asistencia"

    id_asistencia = Column(Integer, primary_key=True)
    id_socio = Column(Integer, ForeignKey("Socio.id_socio"), nullable=False)
    id_sede = Column(Integer, ForeignKey("Sede.id_sede"), nullable=False)
    id_reserva = Column(Integer, ForeignKey("Reserva.id_reserva"))
    fecha_hora_ingreso = Column(DateTime, nullable=False)
    fecha_hora_egreso = Column(DateTime)
    metodo_registro = Column(ENUM("RFID", "MANUAL", name="metodo_registro",
                                   create_type=False), nullable=False,
                              server_default=text("'MANUAL'"))
    id_registrado_por = Column(Integer, ForeignKey("Usuario.id_usuario"))

    socio = relationship("Socio")
    sede = relationship("Sede")
    reserva = relationship("Reserva")


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
