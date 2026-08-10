"""
schemas.py
----------
Moldes Pydantic: definen la forma exacta de lo que ENTRA y SALE de la API.

Son distintos de los modelos de models.py a propósito. El caso que lo explica
solo: la tabla Usuario tiene `password_hash`, y ese campo no puede salir jamás
en una respuesta. Como UsuarioOut simplemente no lo declara, no hay forma de
que se filtre por olvido — ni siquiera si alguien devuelve el objeto ORM
entero desde un endpoint.

Los nombres de los campos de salida siguen el contrato que la PWA ya espera
(ver LoginResultado en services/authService.ts). Es más barato que el backend
se adapte al contrato existente que reescribir las vistas de los dos
frontends.
"""

from datetime import date, datetime, time  # noqa: F401  (los usan los *Out)
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# =============================================================================
# ENTRADA
# =============================================================================

class LoginRequest(BaseModel):
    # Se loguea por username, no por email: es lo que piden las dos pantallas
    # de login (la PWA dice "Usuario", Flet también) y es el campo UNIQUE que
    # el esquema reserva para eso. El email vive en Persona y es de contacto.
    username: str
    password: str


class CambiarPasswordRequest(BaseModel):
    username: str
    password_actual: str
    # min_length en el schema y no en el cuerpo del endpoint: así el rechazo
    # ocurre antes de ejecutar una sola línea del router, y el mensaje de
    # error lo arma FastAPI solo. 8 caracteres es lo que ya exige la PWA
    # (LARGO_MINIMO_PASSWORD en authService.ts).
    password_nueva: str = Field(min_length=8)


# =============================================================================
# SALIDA
# =============================================================================

class PersonaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_persona: int
    dni: str
    apellido: str
    nombre: str
    email: str | None = None
    fecha_nacimiento: date | None = None
    activo: bool


class UsuarioOut(BaseModel):
    """
    La cuenta, SIN el hash. Que password_hash no esté declarado acá es la
    única razón por la que no puede filtrarse.
    """
    model_config = ConfigDict(from_attributes=True)

    id_usuario: int
    id_persona: int
    username: str
    ultimo_acceso: datetime | None = None
    activo: bool


class LoginResponse(BaseModel):
    """
    Tiene dos formas posibles según el estado de la cuenta, y por eso casi
    todo es opcional:

    1. Cuenta con contraseña temporal:
           {"debe_cambiar_password": true}
       y NADA más. Sin token: el backend verificó la contraseña pero se niega
       a abrir la sesión hasta que la persona defina una propia.

    2. Ingreso normal:
           {"debe_cambiar_password": false, "token": "...", "usuario": {...},
            "persona": {...}, "roles": [...], "idSocio": 3}

    Modelar los dos casos en una sola respuesta (en vez de devolver un 4xx en
    el primero) es lo que permite al frontend distinguir "credenciales mal" de
    "credenciales bien, pero falta un paso" sin inventar códigos de error.
    """
    debe_cambiar_password: bool
    token: str | None = None
    token_type: str = "bearer"
    usuario: UsuarioOut | None = None
    persona: PersonaOut | None = None
    roles: list[str] = []
    # camelCase, no snake_case: es el nombre que ya usa la PWA en
    # LoginResultado.idSocio. Vale la pena la inconsistencia con el resto de
    # los campos para no tener que tocar el portal del socio entero.
    idSocio: int | None = None  # noqa: N815


class MensajeResponse(BaseModel):
    mensaje: str


# =============================================================================
# SOCIOS — alta por invitación
# =============================================================================

class SocioAltaRequest(BaseModel):
    """
    Todo lo que hace falta para dar de alta a un socio en el mostrador, en un
    solo pedido.

    Junta datos de TRES tablas (Persona, Telefono, Socio) más la cuenta de
    acceso. Podrían ser tres endpoints encadenados —así lo hace el proyecto de
    referencia del profe— pero uno solo tiene una ventaja importante: es una
    transacción. Si falla el último paso, no queda una Persona suelta sin
    ficha de socio ni una ficha sin cuenta. En un mostrador con gente
    esperando, media alta a medio hacer es peor que ninguna.
    """
    # --- Persona ---
    dni: str = Field(min_length=6, max_length=20)
    nombre: str = Field(min_length=1, max_length=100)
    apellido: str = Field(min_length=1, max_length=100)
    email: EmailStr | None = None
    sexo: str | None = None
    fecha_nacimiento: date | None = None
    calle: str | None = None
    numero_calle: str | None = None
    localidad: str | None = None
    emergencia_nombre: str | None = None
    emergencia_telefono: str | None = None
    emergencia_parentesco: str | None = None

    # --- Teléfono (tabla aparte: una persona puede tener varios) ---
    telefono: str | None = None

    # --- Socio ---
    id_sede: int
    objetivo: str | None = None
    observaciones: str | None = None

    # --- Cuenta de acceso ---
    # Opcional porque no todo socio quiere o puede usar la app: alguien que
    # paga en el mostrador y viene a entrenar no necesariamente necesita
    # credenciales. El esquema lo permite (Usuario cuelga de Persona, no al
    # revés) y el alta lo respeta.
    crear_cuenta: bool = True


class SocioAltaResponse(BaseModel):
    """
    Resultado del alta. Incluye las credenciales generadas.

    Sobre devolver la contraseña temporal en texto plano: es deliberado y es
    la única vez que existe legible. El sistema la generó, nadie la eligió, y
    alguien tiene que poder dictársela al socio en el mostrador o pegarla en
    un WhatsApp. En la base solo queda su hash, así que si no se muestra acá
    se pierde para siempre y habría que resetearla enseguida.

    Quien la consuma NO debe loguearla ni guardarla: se muestra una vez en
    pantalla y se olvida.
    """
    id_socio: int
    numero_socio: str
    persona: PersonaOut
    username: str | None = None
    password_temporal: str | None = None
    mensaje: str
    # Si el mail salió, el operador no necesita hacer nada más. Si no salió,
    # `texto_credenciales` trae el mensaje ya armado para copiar y mandar por
    # WhatsApp — que es la alternativa que contempla la consigna.
    email_enviado: bool = False
    detalle_envio: str | None = None
    texto_credenciales: str | None = None


class SocioEditarRequest(BaseModel):
    """
    Edición desde el panel. NO incluye el DNI: cambiarlo sería, en la
    práctica, decir que es otra persona. Para eso está el alta.
    """
    nombre: str = Field(min_length=1, max_length=100)
    apellido: str = Field(min_length=1, max_length=100)
    email: EmailStr | None = None
    telefono: str | None = None
    objetivo: str | None = None
    observaciones: str | None = None


class TipoBaja(str, Enum):
    VOLUNTARIA = "VOLUNTARIA"
    MORA = "MORA"
    ADMINISTRATIVA = "ADMINISTRATIVA"


class BajaRequest(BaseModel):
    tipo: TipoBaja = TipoBaja.VOLUNTARIA
    motivo: str | None = None


class SocioOut(BaseModel):
    """
    Una fila de la tabla de socios.

    Trae TODO lo que la grilla muestra, ya resuelto: el plan, el estado y el
    vencimiento salen de la membresía vigente, que vive en otra tabla. La
    alternativa —devolver solo el socio y que el cliente pida las membresías
    aparte— haría una consulta por fila: con cien socios, cien pedidos para
    dibujar una tabla.
    """
    model_config = ConfigDict(from_attributes=True)

    id_socio: int
    id_persona: int
    id_sede: int
    numero_socio: str | None = None
    fecha_alta: date
    objetivo: str | None = None
    activo: bool
    # Datos de la persona, aplanados para que la tabla del frontend no tenga
    # que hacer una segunda consulta ni navegar objetos anidados.
    dni: str
    nombre: str
    apellido: str
    email: str | None = None
    telefono: str | None = None
    tiene_cuenta: bool = False
    # --- Derivados de la membresía vigente ---
    id_tipo_membresia: int | None = None
    plan: str = "Sin plan"
    # Uno de los seis valores de EstadoSocio en config.ts. Se manda ya
    # traducido al castellano porque es exactamente lo que la píldora de la
    # tabla pinta; que el cliente lo derive obligaría a mantener la misma
    # regla en tres lugares (PWA, Flet y acá).
    estado: str = "Sin membresía"
    vencimiento: date | None = None


# =============================================================================
# DASHBOARD
# =============================================================================
# Los nombres son camelCase y no snake_case: coinciden con los que ya espera
# dashboardService.ts en la PWA. Adaptar el backend al contrato existente es
# más barato que reescribir las vistas de los dos frontends.

class Metrica(BaseModel):
    """
    Un número del dashboard con su variación contra el período anterior.

    `deltaPorcentual` es None cuando no hay base de comparación —el período
    anterior fue cero y dividir daría infinito—. La vista, en ese caso, no
    muestra nada en vez de inventar un "+100%".
    """
    valor: float
    deltaPorcentual: float | None = None  # noqa: N815


class DashboardStats(BaseModel):
    sociosActivos: Metrica  # noqa: N815
    ingresosMes: Metrica  # noqa: N815
    clasesHoy: Metrica  # noqa: N815
    nuevosMes: Metrica  # noqa: N815


class EventoActividad(BaseModel):
    """Una línea del feed de actividad reciente."""
    # Clave estable para React: tipo + id de la fila que lo originó. Sin esto
    # la lista usaría el índice y perdería el estado al reordenarse.
    id: str
    tipo: str            # PAGO | ALTA_SOCIO | VENCIMIENTO | ASISTENCIA
    descripcion: str
    fecha: datetime


class SocioResumen(BaseModel):
    idSocio: int  # noqa: N815
    nombre: str
    iniciales: str
    plan: str
    estado: str


# =============================================================================
# ASISTENCIA
# =============================================================================

class MetodoRegistro(str, Enum):
    RFID = "RFID"
    MANUAL = "MANUAL"


class FicharRequest(BaseModel):
    """
    Un ingreso al gimnasio. Se identifica al socio por UNA de dos vías:

      - `codigo_rfid`  → el socio pasó su tarjeta por el lector.
      - `id_socio`     → alguien del mostrador lo cargó a mano.

    Son excluyentes y el router valida que venga exactamente una: aceptar las
    dos abriría la puerta a que discrepen y no quede claro a quién se fichó.
    """
    codigo_rfid: str | None = None
    id_socio: int | None = None


class AsistenciaOut(BaseModel):
    id_asistencia: int
    id_socio: int
    socio: str
    numero_socio: str | None = None
    fecha_hora_ingreso: datetime
    fecha_hora_egreso: datetime | None = None
    metodo_registro: MetodoRegistro


class FicharResponse(BaseModel):
    """
    El resultado del fichaje.

    `permitido` puede ser False y aun así devolver 200: el ingreso se
    REGISTRA igual, pero con una advertencia. Es una decisión de negocio —
    dejar a alguien afuera del gimnasio por una deuda es algo que decide una
    persona en el mostrador, no un torniquete. El sistema informa; no juzga.
    """
    asistencia: AsistenciaOut
    permitido: bool
    advertencia: str | None = None
    mensaje: str


# =============================================================================
# ACTIVIDADES
# =============================================================================

class TipoLimite(str, Enum):
    POR_SEMANA = "POR_SEMANA"
    POR_MES = "POR_MES"


class EstadoTurno(str, Enum):
    HABILITADO = "HABILITADO"
    CANCELADO = "CANCELADO"


class EstadoReserva(str, Enum):
    RESERVADA = "RESERVADA"
    CANCELADA_SOCIO = "CANCELADA_SOCIO"
    CANCELADA_GIMNASIO = "CANCELADA_GIMNASIO"


class PlanActividadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_plan_actividad: int
    id_actividad: int
    nombre: str
    tipo_limite: TipoLimite
    cantidad: int
    precio: float
    activo: bool


class ActividadOut(BaseModel):
    id_actividad: int
    nombre: str
    descripcion: str | None = None
    cupo_default: int
    precio_clase_suelta: float
    horas_anticipacion_cancelacion: int
    activo: bool
    planes: list[PlanActividadOut] = []


class ActividadCrear(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    descripcion: str | None = None
    cupo_default: int = Field(ge=1)
    precio_clase_suelta: float = Field(ge=0)
    horas_anticipacion_cancelacion: int = Field(default=0, ge=0)


class TurnoOut(BaseModel):
    id_turno: int
    id_actividad: int
    actividad: str
    fecha: date
    hora: time
    cupo_maximo: int
    # Calculados: la grilla los necesita para pintar "3/15" y deshabilitar el
    # botón. Contarlos en el cliente obligaría a bajarse todas las reservas.
    reservados: int = 0
    lugares_libres: int = 0
    estado: EstadoTurno
    profesor: str | None = None
    motivo_cancelacion: str | None = None


class TurnoCrear(BaseModel):
    id_actividad: int
    id_sede: int
    fecha: date
    hora: time
    # Si no se indica, se usa el cupo_default de la actividad.
    cupo_maximo: int | None = Field(default=None, ge=1)
    id_profesor: int | None = None


class ReservarRequest(BaseModel):
    id_socio: int
    # True cuando el socio paga la clase individual en vez de usar su abono.
    es_clase_suelta: bool = False


class ReservaOut(BaseModel):
    id_reserva: int
    id_turno: int
    id_socio: int
    socio: str
    actividad: str
    fecha: date
    hora: time
    estado: EstadoReserva
    es_clase_suelta: bool
    clases_restantes: int | None = None


# =============================================================================
# COBROS
# =============================================================================

class MetodoPago(str, Enum):
    EFECTIVO = "EFECTIVO"
    DEBITO = "DEBITO"
    CREDITO = "CREDITO"
    TRANSFERENCIA = "TRANSFERENCIA"
    BILLETERA_VIRTUAL = "BILLETERA_VIRTUAL"


class EstadoMembresia(str, Enum):
    ACTIVA = "ACTIVA"
    VENCIDA = "VENCIDA"
    SUSPENDIDA = "SUSPENDIDA"
    CANCELADA = "CANCELADA"


class EstadoDeuda(str, Enum):
    PENDIENTE = "PENDIENTE"
    PAGADA = "PAGADA"
    CONDONADA = "CONDONADA"


class TipoMembresiaCrear(BaseModel):
    nombre: str = Field(min_length=1, max_length=50)
    descripcion: str | None = None
    duracion_dias: int = Field(ge=1)
    precio_actual: float = Field(gt=0)


class TipoMembresiaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_tipo_membresia: int
    nombre: str
    descripcion: str | None = None
    duracion_dias: int
    precio_actual: float
    activo: bool


class CobrarRequest(BaseModel):
    """
    Un cobro de membresía en el mostrador.

    El monto NO se recibe: lo calcula el backend a partir del precio del plan.
    Si viniera del cliente, cualquiera podría cobrar $1 una membresía de
    $30.000 manipulando el pedido. `monto_manual` existe para el caso legítimo
    de un precio pactado distinto, y requiere el permiso de promociones.
    """
    id_socio: int
    id_tipo_membresia: int
    metodo: MetodoPago
    monto_manual: float | None = Field(default=None, gt=0)
    numero_comprobante: str | None = None
    # Si el socio arrastra deudas, este cobro las salda además de renovar.
    saldar_deudas: bool = True


class PagoOut(BaseModel):
    id_pago: int
    id_socio: int
    socio: str
    monto: float
    metodo: MetodoPago
    fecha_pago: datetime
    periodo_desde: date | None = None
    periodo_hasta: date | None = None
    estado: str
    numero_comprobante: str | None = None


class MembresiaOut(BaseModel):
    id_membresia: int
    id_socio: int
    tipo: str
    precio_pactado: float
    fecha_inicio: date
    fecha_vencimiento: date | None = None
    estado: EstadoMembresia
    # Calculado: negativo si ya venció. Lo hace el backend porque depende de
    # la fecha del servidor, no de la del cliente — un navegador con la fecha
    # cambiada no puede hacerse ver al día.
    dias_restantes: int | None = None


class DeudaOut(BaseModel):
    id_deuda: int
    id_socio: int
    socio: str
    monto: float
    fecha_generacion: date
    fecha_vencimiento: date | None = None
    estado: EstadoDeuda
    generada_automaticamente: bool
    observaciones: str | None = None


class CobroResponse(BaseModel):
    pago: PagoOut
    membresia: MembresiaOut
    deudas_saldadas: list[DeudaOut] = []
    mensaje: str


class EstadoCuentaOut(BaseModel):
    """Todo lo que el mostrador necesita ver de un socio antes de cobrarle."""
    id_socio: int
    socio: str
    numero_socio: str | None = None
    membresia_actual: MembresiaOut | None = None
    al_dia: bool
    deuda_total: float
    deudas: list[DeudaOut] = []
    ultimos_pagos: list[PagoOut] = []


# =============================================================================
# PORTAL DEL SOCIO
# =============================================================================
# Todo lo de acá se filtra por el id_socio FIRMADO en el token, nunca por un
# parámetro de la URL. Es la diferencia entre "mostrame mi rutina" y
# "mostrame la rutina 7": lo segundo permitiría leer la ficha de otro
# cambiando un número.

class MiPerfilOut(BaseModel):
    id_socio: int
    numero_socio: str | None = None
    dni: str
    nombre: str
    apellido: str
    email: str | None = None
    telefono: str | None = None
    fecha_nacimiento: date | None = None
    fecha_alta: date
    objetivo: str | None = None
    sede: str | None = None
    emergencia_nombre: str | None = None
    emergencia_telefono: str | None = None
    emergencia_parentesco: str | None = None


class MiCuotaOut(BaseModel):
    al_dia: bool
    plan: str | None = None
    fecha_vencimiento: date | None = None
    dias_restantes: int | None = None
    deuda_total: float = 0
    ultimos_pagos: list[PagoOut] = []


# =============================================================================
# RUTINAS
# =============================================================================

class EstadoAsignacion(str, Enum):
    """Espejo del enum `estado_asignacion` de la base."""
    ACTIVA = "ACTIVA"
    FINALIZADA = "FINALIZADA"
    CANCELADA = "CANCELADA"


class EjercicioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_ejercicio: int
    nombre: str
    grupo_muscular: str
    descripcion: str | None = None
    url_video: str | None = None
    requiere_maquina: bool = False


class EjercicioCrear(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    grupo_muscular: str = Field(min_length=1, max_length=50)
    descripcion: str | None = None
    url_video: str | None = None
    requiere_maquina: bool = False


class RutinaEjercicioCrear(BaseModel):
    id_ejercicio: int
    dia: int = Field(ge=1, le=7)
    orden: int = Field(ge=1)
    series: int | None = None
    # Texto y no número: en el gimnasio se escribe "8-12" o "al fallo".
    repeticiones: str | None = Field(default=None, max_length=20)
    peso_sugerido: float | None = None
    descanso_segundos: int | None = None
    observaciones: str | None = None


class RutinaEjercicioOut(BaseModel):
    id_rutina_ejercicio: int
    id_ejercicio: int
    nombre_ejercicio: str
    grupo_muscular: str
    dia: int
    orden: int
    series: int | None = None
    repeticiones: str | None = None
    peso_sugerido: float | None = None
    descanso_segundos: int | None = None
    observaciones: str | None = None


class RutinaCrear(BaseModel):
    """
    El entrenador autor NO se recibe: sale de la sesión de quien crea. Si
    viniera en el cuerpo, un entrenador podría crear rutinas a nombre de otro.
    """
    nombre: str = Field(min_length=1, max_length=100)
    objetivo: str | None = None
    nivel: str | None = None
    dias_por_semana: int | None = Field(default=None, ge=1, le=7)
    ejercicios: list[RutinaEjercicioCrear] = []


class RutinaOut(BaseModel):
    id_rutina: int
    id_entrenador: int
    entrenador: str
    nombre: str
    objetivo: str | None = None
    nivel: str | None = None
    dias_por_semana: int | None = None
    fecha_creacion: date | None = None
    activo: bool
    # Cuántos socios la están siguiendo ahora. Lo calcula el backend porque
    # requiere contar asignaciones ACTIVAS, y hacerlo en el cliente obligaría
    # a bajarse todas las asignaciones para mostrar un número.
    asignados: int = 0
    ejercicios: list[RutinaEjercicioOut] = []


class AsignarRutinaRequest(BaseModel):
    id_socio: int
    fecha_inicio: date | None = None       # por defecto, hoy
    fecha_fin: date | None = None


class AsignacionRutinaOut(BaseModel):
    id_asignacion_rutina: int
    id_socio: int
    socio: str
    id_rutina: int
    rutina: str
    fecha_inicio: date
    fecha_fin: date | None = None
    estado: EstadoAsignacion


# =============================================================================
# NUTRICIÓN — espejo de Rutinas
# =============================================================================

class ComidaCrear(BaseModel):
    dia: int | None = Field(default=None, ge=1, le=7)
    momento: str | None = Field(default=None, max_length=30)
    descripcion: str = Field(min_length=1)
    calorias: int | None = None


class ComidaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_comida: int
    dia: int | None = None
    momento: str | None = None
    descripcion: str
    calorias: int | None = None


class DietaCrear(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    objetivo: str | None = None
    calorias_diarias: int | None = None
    descripcion: str | None = None
    comidas: list[ComidaCrear] = []


class DietaOut(BaseModel):
    id_dieta: int
    id_nutricionista: int
    nutricionista: str
    nombre: str
    objetivo: str | None = None
    calorias_diarias: int | None = None
    descripcion: str | None = None
    fecha_creacion: date | None = None
    activo: bool
    asignados: int = 0
    comidas: list[ComidaOut] = []


class AsignarDietaRequest(BaseModel):
    id_socio: int
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    observaciones: str | None = None


class AsignacionDietaOut(BaseModel):
    id_asignacion_dieta: int
    id_socio: int
    socio: str
    id_dieta: int
    dieta: str
    fecha_inicio: date
    fecha_fin: date | None = None
    estado: EstadoAsignacion
    observaciones: str | None = None


# =============================================================================
# PERSONAL — empleados y sus especialidades
# =============================================================================

class RolEmpleado(str, Enum):
    """
    Los cuatro tipos de empleado.

    NO son una columna: en el esquema, el tipo de un empleado está dado por en
    cuál de las cuatro tablas hijas de Empleado existe su fila. Este enum es
    el nombre que usa la API para referirse a esa estructura, y sus valores
    coinciden con RolEmpleado de config.ts.

    PROFESOR está acá pero NO habilita el ingreso al sistema: da clases, no lo
    usa. Por eso `roles_de_persona` no le devuelve ningún rol de sesión y el
    alta no le ofrece crear cuenta.
    """
    ENTRENADOR = "Entrenador"
    NUTRICIONISTA = "Nutricionista"
    RECEPCIONISTA = "Recepcionista"
    PROFESOR = "Profesor"


class EmpleadoAltaRequest(BaseModel):
    """
    Alta de un empleado. Mismo patrón que el alta de socio: crea Persona +
    Empleado + la tabla de su especialidad, todo en una transacción.
    """
    # --- Persona ---
    dni: str = Field(min_length=6, max_length=20)
    nombre: str = Field(min_length=1, max_length=100)
    apellido: str = Field(min_length=1, max_length=100)
    email: EmailStr | None = None
    telefono: str | None = None
    fecha_nacimiento: date | None = None

    # --- Empleado ---
    id_sede: int
    fecha_ingreso: date | None = None      # por defecto, hoy

    # --- Especialidad ---
    rol: RolEmpleado
    # Campos de las tablas hijas. Cada uno aplica solo a algunos roles y el
    # router ignora los que no correspondan, en vez de rechazar el pedido: un
    # formulario que manda todos los campos siempre es más simple de escribir
    # que uno que arma un cuerpo distinto por rol.
    titulo: str | None = None              # Entrenador, Nutricionista, Profesor
    especialidad: str | None = None        # Entrenador, Profesor
    matricula: str | None = None           # Entrenador, Nutricionista
    turno_laboral: str | None = None       # solo Recepcionista

    # --- Cuenta ---
    # Un Profesor no puede tener sesión, así que el router fuerza esto a False
    # para ese rol aunque venga en True.
    crear_cuenta: bool = True


class EmpleadoOut(BaseModel):
    id_empleado: int
    id_persona: int
    id_sede: int
    legajo: str | None = None
    fecha_ingreso: date
    fecha_egreso: date | None = None
    activo: bool
    rol: RolEmpleado | None = None         # None: cargado sin especialidad todavía
    titulo: str | None = None
    especialidad: str | None = None
    matricula: str | None = None
    turno_laboral: str | None = None
    # Aplanados desde Persona, para que la grilla no navegue objetos anidados.
    dni: str
    nombre: str
    apellido: str
    email: str | None = None
    tiene_cuenta: bool = False


class EmpleadoEditarRequest(BaseModel):
    """
    Edición de un empleado. Puede incluir un CAMBIO DE ROL, que no es un
    cambio cualquiera: implica borrar la fila de su especialidad actual y
    crear otra. Ver `validar_cambio_de_rol` en el router.
    """
    nombre: str = Field(min_length=1, max_length=100)
    apellido: str = Field(min_length=1, max_length=100)
    email: EmailStr | None = None
    telefono: str | None = None
    rol: RolEmpleado
    titulo: str | None = None
    especialidad: str | None = None
    matricula: str | None = None
    turno_laboral: str | None = None


class BajaEmpleadoRequest(BaseModel):
    motivo: str | None = None


class EmpleadoAltaResponse(BaseModel):
    id_empleado: int
    legajo: str
    rol: RolEmpleado
    persona: PersonaOut
    username: str | None = None
    password_temporal: str | None = None
    mensaje: str
    email_enviado: bool = False
    detalle_envio: str | None = None
    texto_credenciales: str | None = None


# =============================================================================
# USUARIOS — gestión de cuentas de acceso
# =============================================================================

class UsuarioAdminOut(BaseModel):
    """
    Una cuenta vista desde el panel de administración.

    Incluye `bloqueado` y `debe_cambiar_password`, que la vista normal de
    sesión (UsuarioOut) no expone: acá sí importan, porque son justamente el
    estado sobre el que el panel actúa. Sigue sin incluir `password_hash`.
    """
    id_usuario: int
    id_persona: int
    username: str
    dni: str
    nombre_completo: str
    email: str | None = None
    # Derivados de las tablas de rol, no de una columna. Una persona puede
    # tener más de uno (el dueño que además entrena).
    roles: list[str]
    activo: bool
    bloqueado: bool
    debe_cambiar_password: bool
    ultimo_acceso: datetime | None = None


class PersonaSinCuentaOut(BaseModel):
    """
    Candidata a que se le cree una cuenta: existe como Persona, tiene algún
    rol que justifique el acceso, pero todavía no tiene credenciales.
    """
    id_persona: int
    dni: str
    nombre_completo: str
    email: str | None = None
    roles: list[str]


class UsuarioCrearRequest(BaseModel):
    # Solo el id: los datos personales ya existen en Persona y pedirlos de
    # nuevo permitiría cargar dos versiones distintas de la misma persona.
    id_persona: int


class CredencialesResponse(BaseModel):
    """
    Credenciales recién generadas. Igual que en el alta de socio, la
    contraseña viaja en texto plano porque es la única vez que existe legible
    — en la base solo queda su hash. Se muestra una vez y se olvida.
    """
    username: str
    password_temporal: str
    mensaje: str
    email_enviado: bool = False
    detalle_envio: str | None = None
    texto_credenciales: str | None = None
