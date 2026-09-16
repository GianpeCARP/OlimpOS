"""
models.py
---------
Modelos SQLAlchemy que MAPEAN el esquema de `db/schema.sql`.
No lo definen: si acá y allá dicen cosas distintas, manda el .sql (ver el
docstring largo de database.py).

Por eso todos los defaults se declaran como `server_default` y no como
`default`: `default` lo aplica Python antes de mandar el INSERT y no dice
nada sobre lo que realmente hace la base, mientras que `server_default`
documenta el DEFAULT que ya está escrito en el DDL. Si alguien inserta una
fila por fuera de la app (el SQL Editor de Neon, un script), el resultado es
el mismo — que es justamente lo que se quiere.

ALCANCE: las 41 tablas del esquema definitivo están mapeadas. (Este archivo
nació cubriendo sólo la rebanada de autenticación y se fue completando; hoy
espeja el DDL entero de `db/schema.sql`.)
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
    `Roles` en `Proyecto - PWA/src/frontend/src/config.ts` (minúsculas, sin tildes),
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
    # El Profesor SÍ inicia sesión, desde el 2026-09-16. Antes no, y la nota
    # vieja lo defendía así: "da clases, no usa el sistema". El resultado real
    # era que el profesor no tenía dónde ver su horario ni quién se anotó a su
    # clase — se lo pasaba alguien por WhatsApp o un papel en la pared.
    #
    # Es un rol de PANTALLA PROPIA, como el Socio: no entra a ninguna sección
    # de gestión, sólo a "Mis clases", y ahí ve únicamente los turnos que dicta
    # él (Turno.id_profesor). No configura el catálogo ni toca a nadie más.
    PROFESOR = "profesor"


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
    # Los contactos de emergencia YA NO son columnas de Persona: son
    # multivaluados (una persona puede declarar más de uno) y por eso viven en
    # Contacto_Emergencia, igual que los teléfonos viven en Telefono. Ver la
    # tabla Contacto_Emergencia del schema. Antes eran tres columnas inline
    # (emergencia_nombre/telefono/parentesco); el schema definitivo las movió.
    fecha_alta = Column(DateTime, server_default=func.now())
    activo = Column(Boolean, server_default=text("true"))

    # uselist=False en las tres: una Persona tiene como mucho UNA cuenta, UNA
    # ficha de socio y UNA de empleado (las FK son UNIQUE en el esquema).
    # Los teléfonos y contactos de emergencia sí son varios: por eso son 1:N.
    usuario = relationship("Usuario", back_populates="persona", uselist=False)
    socio = relationship("Socio", back_populates="persona", uselist=False)
    empleado = relationship("Empleado", back_populates="persona", uselist=False)
    dueno = relationship("Dueno", back_populates="persona", uselist=False)
    telefonos = relationship("Telefono", back_populates="persona")
    contactos_emergencia = relationship("ContactoEmergencia", back_populates="persona")

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


class ContactoEmergencia(Base):
    """
    A quién avisar si al socio le pasa algo. Es multivaluado (puede tener más
    de uno), así que va en tabla propia y no como columnas de Persona.

    Asimetría deliberada con Telefono: acá el teléfono va inline, porque el
    contacto de emergencia NO es una Persona del sistema —es un dato de
    contacto externo, no un actor con ficha propia—.
    """
    __tablename__ = "Contacto_Emergencia"

    id_contacto_emergencia = Column(Integer, primary_key=True)
    id_persona = Column(Integer, ForeignKey("Persona.id_persona"), nullable=False)
    nombre = Column(String(150), nullable=False)
    telefono = Column(String(30), nullable=False)
    parentesco = Column(String(50))
    principal = Column(Boolean, server_default=text("false"))

    persona = relationship("Persona", back_populates="contactos_emergencia")


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


class FranjaLaboral(Base):
    """
    Catálogo de turnos de trabajo (Mañana / Tarde / Noche). Lo usa sólo
    Recepcionista: los demás subtipos derivan su horario de Turno y
    Horario_Actividad, así que no lo necesitan. Reemplaza al viejo varchar
    `turno_laboral` que vivía inline en Recepcionista.
    """
    __tablename__ = "Franja_Laboral"

    id_franja_laboral = Column(Integer, primary_key=True)
    nombre = Column(String(40), unique=True, nullable=False)
    hora_desde = Column(Time)
    hora_hasta = Column(Time)
    activo = Column(Boolean, server_default=text("true"))


class Recepcionista(Base):
    __tablename__ = "Recepcionista"

    id_recepcionista = Column(Integer, primary_key=True)
    id_empleado = Column(Integer, ForeignKey("Empleado.id_empleado"), unique=True, nullable=False)
    # El turno de trabajo ahora es una FK al catálogo Franja_Laboral, no un
    # varchar libre: así 'Tarde' es una sola cosa y no 'tarde'/'Tarde'/'T'.
    id_franja_laboral = Column(Integer, ForeignKey("Franja_Laboral.id_franja_laboral"))

    empleado = relationship("Empleado", back_populates="recepcionista")
    franja = relationship("FranjaLaboral")


class Profesor(Base):
    """
    Cuarto tipo de empleado, para las Actividades: dicta las clases grupales
    con horario fijo (yoga, boxeo).

    Tiene rol de sesión desde el 2026-09-16, pero es un rol de pantalla propia
    y no de gestión: entra a "Mis clases" y ve los turnos que dicta él. Ver
    Rol.PROFESOR.
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
    Descuento SIEMPRE porcentual. El monto fijo se eliminó por decisión
    comercial (ver schema): antes había una segunda columna
    `monto_fijo_descuento` y las dos eran nullables porque se usaba una u otra.
    Los pesos efectivamente descontados en un cobro se guardan en
    Pago.monto_descuento, no acá.
    """
    __tablename__ = "Promocion"

    id_promocion = Column(Integer, primary_key=True)
    id_dueno = Column(Integer, ForeignKey("Dueno.id_dueno"), nullable=False)
    id_sede = Column(Integer, ForeignKey("Sede.id_sede"))
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text)
    porcentaje_descuento = Column(Numeric(5, 2), nullable=False)
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
    # NO hay `id_promocion` acá: la promoción aplicada y los pesos descontados
    # viven en el Pago (Pago.id_promocion / Pago.monto_descuento), que es el
    # hecho contable. La membresía sólo guarda el precio_pactado ya resultante.
    precio_pactado = Column(Numeric(10, 2), nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_vencimiento = Column(Date)
    estado = Column(ENUM("ACTIVA", "VENCIDA", "SUSPENDIDA", "CANCELADA",
                          name="estado_membresia", create_type=False),
                     nullable=False, server_default=text("'ACTIVA'"))

    socio = relationship("Socio")
    tipo = relationship("TipoMembresia")


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
    id_inscripcion = Column(Integer, ForeignKey("Inscripcion_Actividad.id_inscripcion"))
    id_sede = Column(Integer, ForeignKey("Sede.id_sede"))
    metodo = Column(ENUM("EFECTIVO", "DEBITO", "CREDITO", "TRANSFERENCIA",
                          "BILLETERA_VIRTUAL", name="metodo_pago", create_type=False),
                     nullable=False)
    monto = Column(Numeric(10, 2), nullable=False)
    fecha_pago = Column(DateTime, nullable=False, server_default=func.now())
    periodo_desde = Column(Date)
    periodo_hasta = Column(Date)
    es_adelanto = Column(Boolean, nullable=False, server_default=text("false"))
    estado = Column(ENUM("CONFIRMADO", "PENDIENTE", "CANCELADO", "REEMBOLSADO",
                          name="estado_pago", create_type=False),
                     nullable=False, server_default=text("'CONFIRMADO'"))
    fecha_cancelacion = Column(DateTime)
    numero_comprobante = Column(String(50), unique=True)
    # La promoción aplicada a este cobro y los pesos que descontó. Se GUARDAN
    # (no se recalculan): la promo puede vencer o cambiar después, y hay que
    # poder reconstruir qué se cobró ese día. Movidos desde Membresia.
    id_promocion = Column(Integer, ForeignKey("Promocion.id_promocion"))
    monto_descuento = Column(Numeric(10, 2))

    socio = relationship("Socio")
    membresia = relationship("Membresia")
    promocion = relationship("Promocion")


# NO existe un modelo Deuda: el esquema definitivo eliminó la tabla. La política
# es prepago —sin membresía activa no hay acceso— y el estado "debe" es
# DERIVABLE (una membresía vencida sin renovar), así que no necesita fila
# propia. Todo el subsistema de deudas (router y generador) se retiró.


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

    EXCEPCIÓN — id_entrenador NULL = RUTINA PROPIA de un socio: se la arma él
    mismo, sin entrenador. El dueño se DERIVA de la Asignacion_Rutina (una
    rutina propia se asigna sólo a su autor). Es invisible para el personal: los
    endpoints del staff tratan id_entrenador NULL como inexistente, así que
    nunca aparece en el catálogo de rutinas a asignar.
    """
    __tablename__ = "Rutina"

    id_rutina = Column(Integer, primary_key=True)
    id_entrenador = Column(Integer, ForeignKey("Entrenador.id_entrenador"), nullable=True)
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
    # NO hay `id_entrenador` acá: el entrenador que la escribió sale de
    # Rutina.id_entrenador. Guardarlo también en la asignación sería una
    # segunda fuente de verdad. El schema definitivo lo quitó.
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date)
    estado = Column(ENUM("ACTIVA", "FINALIZADA", "CANCELADA",
                          name="estado_asignacion", create_type=False),
                     nullable=False, server_default=text("'ACTIVA'"))

    socio = relationship("Socio")
    rutina = relationship("Rutina", back_populates="asignaciones")


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

class CatalogoComida(Base):
    """
    Catálogo de platos. Las calorías, el nombre y la descripción viven ACÁ
    porque dependen del PLATO, no de la dieta ni del día en que aparece. Es
    exactamente la razón por la que Comida.calorias y Comida.descripcion se
    eliminaron: eran redundancia una vez que el catálogo se volvió obligatorio.
    """
    __tablename__ = "Catalogo_Comida"

    id_catalogo_comida = Column(Integer, primary_key=True)
    nombre = Column(String(120), unique=True, nullable=False)
    descripcion = Column(Text)
    calorias = Column(Integer)
    activo = Column(Boolean, server_default=text("true"))


class Dieta(Base):
    """
    Plantilla que arma un nutricionista. Mismo patrón que Rutina.

    id_nutricionista NULL = DIETA PROPIA del socio (se la arma él, sin
    nutricionista). El dueño se deriva de Asignacion_Dieta; invisible para el
    staff. Espejo de Rutina.id_entrenador NULL.
    """
    __tablename__ = "Dieta"

    id_dieta = Column(Integer, primary_key=True)
    id_nutricionista = Column(Integer, ForeignKey("Nutricionista.id_nutricionista"),
                               nullable=True)
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
    """
    Una comida de la dieta. El equivalente de RutinaEjercicio.

    El plato sale del catálogo (id_catalogo_comida) O, en una dieta propia con el
    catálogo vacío, de `descripcion` (texto libre). Al menos una de las dos
    (CHECK chk_comida_plato). `descripcion` NO son calorías: el contenido real de
    lo comido va en Registro_Comida.
    """
    __tablename__ = "Comida"

    id_comida = Column(Integer, primary_key=True)
    id_dieta = Column(Integer, ForeignKey("Dieta.id_dieta"), nullable=False)
    dia = Column(Integer)
    momento = Column(String(30))          # Desayuno, Almuerzo, Merienda, Cena
    id_catalogo_comida = Column(Integer, ForeignKey("Catalogo_Comida.id_catalogo_comida"),
                                 nullable=True)
    descripcion = Column(String(200))

    dieta = relationship("Dieta", back_populates="comidas")
    catalogo = relationship("CatalogoComida")


class AsignacionDieta(Base):
    __tablename__ = "Asignacion_Dieta"

    id_asignacion_dieta = Column(Integer, primary_key=True)
    id_socio = Column(Integer, ForeignKey("Socio.id_socio"), nullable=False)
    id_dieta = Column(Integer, ForeignKey("Dieta.id_dieta"), nullable=False)
    # NO hay `id_nutricionista` acá: sale de Dieta.id_nutricionista. Mismo
    # criterio que AsignacionRutina con el entrenador. El schema lo quitó.
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date)
    estado = Column(ENUM("ACTIVA", "FINALIZADA", "CANCELADA",
                          name="estado_asignacion", create_type=False),
                     nullable=False, server_default=text("'ACTIVA'"))
    observaciones = Column(Text)

    socio = relationship("Socio")
    dieta = relationship("Dieta", back_populates="asignaciones")


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
    # NO hay `precio_clase_suelta`: la clase suelta es ahora un Plan_Actividad
    # más (tipo_limite = CLASE_SUELTA, cantidad = 1), no una columna aparte.
    # Así el sistema de inscripciones la trata igual que a cualquier otro plan.
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
    tipo_limite = Column(ENUM("POR_SEMANA", "POR_MES", "CLASE_SUELTA",
                               name="tipo_limite", create_type=False), nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio = Column(Numeric(10, 2), nullable=False)
    activo = Column(Boolean, server_default=text("true"))

    actividad = relationship("Actividad", back_populates="planes")


class InscripcionActividad(Base):
    """
    Un socio anotado a un plan, con su período.

    `clases_restantes` fue ELIMINADA: el consumo se calcula al vuelo contando
    Reserva (reservas activas de esta inscripción). Guardarlo materializado
    creaba una segunda fuente de verdad, y dejaba dos criterios opuestos en la
    misma columna (POR_MES lo guardaba, POR_SEMANA lo calculaba).

    Tampoco cuelga ya de una Membresia (`id_membresia` se eliminó): la
    inscripción es del socio, y el pago que la respalda se ata por Pago.

    `precio_pactado` congela el precio del plan al momento de contratarlo, por
    la misma razón que `Membresia.precio_pactado`.
    """
    __tablename__ = "Inscripcion_Actividad"

    id_inscripcion = Column(Integer, primary_key=True)
    id_socio = Column(Integer, ForeignKey("Socio.id_socio"), nullable=False)
    id_plan_actividad = Column(Integer, ForeignKey("Plan_Actividad.id_plan_actividad"),
                                nullable=False)
    precio_pactado = Column(Numeric(10, 2), nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_vencimiento = Column(Date, nullable=False)
    estado = Column(ENUM("ACTIVA", "VENCIDA", "CANCELADA",
                          name="estado_inscripcion", create_type=False),
                     nullable=False, server_default=text("'ACTIVA'"))

    socio = relationship("Socio")
    plan = relationship("PlanActividad")


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
    # Excluyente con id_profesor, igual que en Turno (CHECK en la base). Que
    # los dos sean None es válido: es la sala abierta, sin nadie a cargo.
    id_entrenador_a_cargo = Column(Integer, ForeignKey("Entrenador.id_entrenador"))
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

    Quien pagó una clase individual se distingue de quien usa su abono por
    `id_inscripcion`: NULL = clase suelta (no descuenta de ningún abono),
    no-NULL = usa esa inscripción.
    """
    __tablename__ = "Reserva"

    id_reserva = Column(Integer, primary_key=True)
    id_turno = Column(Integer, ForeignKey("Turno.id_turno"), nullable=False)
    id_socio = Column(Integer, ForeignKey("Socio.id_socio"), nullable=False)
    # id_inscripcion NULL = clase suelta. Reemplaza al viejo booleano
    # `es_clase_suelta`, que repetía este mismo dato: si hay inscripción, usa
    # el abono; si no la hay, es una clase suelta pagada aparte.
    id_inscripcion = Column(Integer, ForeignKey("Inscripcion_Actividad.id_inscripcion"))
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
    sesión. El login tiene que rechazarla: una cuenta sin roles no puede ver
    ninguna sección, y dejarla entrar a un sistema donde no puede hacer nada
    solo genera confusión. (El caso que este comentario daba de ejemplo era el
    Profesor, que desde el 2026-09-16 SÍ tiene rol — ver Rol.PROFESOR.)

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
        if empleado.profesor is not None:
            roles.append(Rol.PROFESOR)

    return roles


class Congelamiento(Base):
    """
    Una pausa de la membresía: viaje, lesión, lo que sea.

    Es una tabla y no dos columnas en Membresia por lo mismo que Baja es una
    tabla: un socio congela más de una vez a lo largo del tiempo, cada
    congelamiento tiene su motivo y sus fechas, y con dos columnas el segundo
    pisaría al primero. Ese historial es justamente lo que permite aplicar un
    tope anual.

    `fecha_fin` es un TOPE y no una promesa: se puede reanudar antes, y sólo
    se extiende el vencimiento por los días realmente congelados. Por eso la
    extensión se aplica al REANUDAR y no al congelar — al congelar todavía no
    se sabe cuántos días van a ser en serio.
    """
    __tablename__ = "Congelamiento"

    id_congelamiento = Column(Integer, primary_key=True)
    # NO hay `id_socio`: el socio sale de Membresia.id_socio. El congelamiento
    # cuelga de la MEMBRESIA, que es lo que se extiende al reanudar.
    id_membresia = Column(Integer, ForeignKey("Membresia.id_membresia"), nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)
    fecha_reanudacion = Column(Date)
    motivo = Column(String(200))
    estado = Column(ENUM("ACTIVO", "FINALIZADO", "CANCELADO",
                          name="estado_congelamiento", create_type=False),
                     nullable=False, server_default=text("'ACTIVO'"))
    fecha_solicitud = Column(DateTime, nullable=False, server_default=func.now())
    # SOCIO (viaje, lesión) vs GIMNASIO (cierre, refacción). Los días impuestos
    # por el gimnasio NO cuentan contra el tope anual de congelamiento
    # voluntario. `dias_aplicados` se eliminó: los días reales se derivan de
    # (fecha_reanudacion - fecha_inicio).
    origen = Column(ENUM("SOCIO", "GIMNASIO", name="origen_congelamiento",
                          create_type=False),
                    nullable=False, server_default=text("'SOCIO'"))

    membresia = relationship("Membresia")


class Patologia(Base):
    """
    El catálogo de condiciones médicas: asma, diabetes, hernia de disco.

    Es una tabla y no un varchar en Socio por 1FN: "asma, rodilla operada,
    hipertensión" en un solo campo no se puede consultar ni contar, y cada
    quien lo escribe distinto ("asma" / "Asma" / "asmatico"). Con el catálogo,
    preguntar cuántos socios tienen asma es una consulta y no una búsqueda de
    texto con suerte.
    """
    __tablename__ = "Patologia"

    id_patologia = Column(Integer, primary_key=True)
    nombre = Column(String(100), unique=True, nullable=False)
    descripcion = Column(Text)


class SocioPatologia(Base):
    """
    Qué condiciones tiene cada socio.

    Clave primaria COMPUESTA (id_socio, id_patologia): un socio no puede tener
    la misma patología dos veces, y eso lo impide el esquema, no un `if`.

    `observaciones` es donde va lo que el catálogo no puede saber: "rodilla
    derecha", "controlada con medicación", "evitar impacto". Es el campo que
    de verdad le sirve al entrenador cuando arma la rutina.
    """
    __tablename__ = "Socio_Patologia"

    id_socio = Column(Integer, ForeignKey("Socio.id_socio"), primary_key=True)
    id_patologia = Column(Integer, ForeignKey("Patologia.id_patologia"),
                           primary_key=True)
    fecha_diagnostico = Column(Date)
    observaciones = Column(Text)

    socio = relationship("Socio")
    patologia = relationship("Patologia")


class RegistroEjercicio(Base):
    """
    El peso que el socio EFECTIVAMENTE levantó, cargado por él. Es la mitad
    REAL del par plantilla/realidad: Rutina_Ejercicio dice qué debería hacer,
    esto dice qué hizo. Record = MAX(peso_hecho). Grano (socio, ejercicio, fecha).
    """
    __tablename__ = "Registro_Ejercicio"

    id_registro_ejercicio = Column(Integer, primary_key=True)
    id_socio = Column(Integer, ForeignKey("Socio.id_socio"), nullable=False)
    id_ejercicio = Column(Integer, ForeignKey("Ejercicio.id_ejercicio"), nullable=False)
    fecha = Column(Date, nullable=False, server_default=func.now())
    peso_hecho = Column(Numeric(6, 2), nullable=False)
    series_hechas = Column(Integer)
    repeticiones_hechas = Column(String(20))
    observaciones = Column(String(200))

    socio = relationship("Socio")
    ejercicio = relationship("Ejercicio")


class RegistroComida(Base):
    """
    Lo que el socio REALMENTE comió un día, cargado por él. Es a Comida lo que
    Registro_Ejercicio es a Rutina_Ejercicio: plantilla contra realidad.

    `id_comida` = qué comida de la dieta CORRESPONDÍA (opcional).
    `comida_ingerida` = qué comió DE VERDAD (texto libre, NOT NULL): a
    propósito no apunta al catálogo, para que anote cualquier cosa.

    Los macros (calorías/proteínas/carbos/grasas) los carga el socio a mano o
    los completa el coach IA a partir del texto. Todos opcionales: sin ellos el
    registro vale igual por el texto.
    """
    __tablename__ = "Registro_Comida"

    id_registro_comida = Column(Integer, primary_key=True)
    id_socio = Column(Integer, ForeignKey("Socio.id_socio"), nullable=False)
    id_comida = Column(Integer, ForeignKey("Comida.id_comida"))
    fecha = Column(Date, nullable=False, server_default=func.now())
    comida_ingerida = Column(Text, nullable=False)
    momento = Column(String(30))          # Desayuno, Almuerzo, Merienda, Cena, Snack
    calorias_estimadas = Column(Integer)
    proteinas_g = Column(Numeric(6, 2))
    carbohidratos_g = Column(Numeric(6, 2))
    grasas_g = Column(Numeric(6, 2))

    socio = relationship("Socio")
    comida = relationship("Comida")
