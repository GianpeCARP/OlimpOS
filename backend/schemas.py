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
    # Viaja aunque la grilla no lo muestre: el formulario de edición lo manda
    # de vuelta siempre, así que si no pudiera precargarse, cada edición lo
    # dejaría en blanco sin que nadie tocara el campo.
    observaciones: str | None = None
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
    # Los valores son minúsculas y coinciden con  de
    # dashboardService.ts: la vista los usa como clave de un Record que mapea
    # cada tipo a su ícono y su color. Mandar "PAGO" en vez de "pago" dejaría
    # esos eventos sin ícono.
    tipo: str            # pago | nuevo_socio | vencimiento
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
    # Qué clase se le acreditó con este mismo ingreso, si tenía una reservada
    # y llegó a tiempo. El recepcionista no tildó nada: pasó la tarjeta y el
    # sistema resolvió a qué turno correspondía.
    clase_acreditada: str | None = None
    # Tenía reserva pero se pasó de la tolerancia. Va aparte de `advertencia`
    # —que es sobre la cuota y la deuda— porque son dos conversaciones
    # distintas en el mostrador: una es "andá a pagar", la otra "perdiste la
    # clase". Mezclarlas hace que se lea una sola y se ignore la otra.
    turno_perdido: str | None = None


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
    # Combo opcional: además de la membresía, un abono de actividad.
    #
    # Va en el MISMO pedido y no en dos porque Inscripcion_Actividad.id_membresia
    # es NOT NULL: el abono no puede existir sin una membresía que lo respalde.
    # Cobrarlos por separado dejaría una ventana en la que el plan quedó pago
    # pero sin membresía a la que colgarse.
    id_plan_actividad: int | None = None


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


class InscripcionOut(BaseModel):
    id_inscripcion: int
    actividad: str
    plan: str
    tipo_limite: str
    clases_restantes: int | None = None
    fecha_inicio: date
    fecha_vencimiento: date
    precio_pactado: float


class CobroResponse(BaseModel):
    pago: PagoOut
    membresia: MembresiaOut
    inscripcion: InscripcionOut | None = None
    deudas_saldadas: list[DeudaOut] = []
    total: float
    mensaje: str


class PagarDeudaRequest(BaseModel):
    metodo: MetodoPago
    numero_comprobante: str | None = None


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
    # Anotado sin lugar. NO ocupa cupo: todo conteo de ocupación filtra por
    # RESERVADA. Si falta este valor acá, la reserva se crea bien en la base
    # pero la RESPUESTA falla al validarse — el socio queda anotado y la
    # pantalla muestra un error. Se descubrió así.
    EN_ESPERA = "EN_ESPERA"
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
    # Minutos de gracia para llegar. Sale en la respuesta porque el panel del
    # mostrador lo muestra ("vence a las 19:15") y la pantalla de Actividades
    # lo edita.
    minutos_tolerancia: int = 15
    activo: bool
    planes: list[PlanActividadOut] = []


class ActividadCrear(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    descripcion: str | None = None
    # Tope de 180 igual que el CHECK de la base: existe para atajar el dedo
    # que escribe 1500 queriendo 15, no para discutir cuanto es razonable.
    minutos_tolerancia: int = Field(default=15, ge=0, le=180)
    # gt=0 y no ge=0: una clase con cupo cero no la puede tomar nadie.
    cupo_default: int = Field(ge=1)
    # El precio SÍ puede ser 0 — una actividad incluida en la cuota.
    precio_clase_suelta: float = Field(ge=0)
    horas_anticipacion_cancelacion: int = Field(default=0, ge=0)


class PlanActividadCrear(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    tipo_limite: TipoLimite
    cantidad: int = Field(ge=1)
    precio: float = Field(ge=0)


class ComprarPlanRequest(BaseModel):
    """
    Un socio compra un abono de actividad.

    Igual que en el cobro de membresía, el precio NO se recibe: sale del plan.
    Y se exige `metodo` porque comprar un abono genera un Pago real — no es
    una inscripción gratuita.
    """
    id_socio: int
    metodo: MetodoPago


class InscripcionOut(BaseModel):
    id_inscripcion: int
    id_socio: int
    socio: str
    id_plan_actividad: int
    plan: str
    actividad: str
    id_actividad: int
    tipo_limite: TipoLimite
    cantidad: int
    precio_pactado: float
    fecha_inicio: date
    fecha_vencimiento: date
    clases_restantes: int | None = None
    estado: str


class ComprarPlanResponse(BaseModel):
    inscripcion: InscripcionOut
    pago: PagoOut
    mensaje: str


class ProfesorActividadOut(BaseModel):
    id_profesor: int
    nombre: str
    titulo: str | None = None
    especialidad: str | None = None




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


class PuedeComprarOut(BaseModel):
    """
    Si un socio está en condiciones de comprar un abono, SIN comprar nada.

    Lo consulta la vista de Cobros antes de cobrar: si el abono no va a
    entrar, hay que ofrecer el combo "renovar cuota + comprar" en vez de
    cobrar la membresía y descubrirlo después, con la plata ya cobrada.
    """
    puede: bool
    tiene_deuda: bool
    membresia_cubre: bool
    vencimiento_membresia: date | None = None
    vencimiento_abono: date
    # None cuando `puede` es True. Es el texto que la vista muestra tal cual.
    motivo: str | None = None


class ComprarClaseSueltaRequest(BaseModel):
    id_socio: int
    metodo: MetodoPago


class ClaseSueltaResponse(BaseModel):
    reserva: ReservaOut
    pago: PagoOut
    mensaje: str


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
    # Domicilio ya armado ("Av. Victorica 1450, Moreno"). Se compone en el
    # servidor porque saltear las partes que faltan sin dejar comas sueltas es
    # la misma cuenta en cada pantalla que lo muestra.
    domicilio: str | None = None
    # Solo lectura, para el encabezado de la pantalla.
    plan: str = "Sin plan"
    estado: str = "Sin membresía"
    vencimiento: date | None = None


class MiComidaOut(BaseModel):
    id_comida: int
    momento: str | None = None
    descripcion: str
    calorias: int | None = None


class MiDiaDeDietaOut(BaseModel):
    dia: int
    comidas: list[MiComidaOut] = []
    # Suma de las calorías del día. La calcula el servidor porque es la misma
    # cuenta para todos y así la vista no suma en cada render.
    calorias_del_dia: int | None = None


class MiDietaOut(BaseModel):
    """
    La dieta vista por el socio.

    Distinta de DietaOut (la de gestión) porque incluye datos de la
    ASIGNACIÓN —desde cuándo la tiene, y las observaciones que le dejó el
    nutricionista— que no viven en la plantilla sino en el vínculo entre ella
    y esta persona.
    """
    id_dieta: int
    nombre: str
    objetivo: str | None = None
    calorias_diarias: int | None = None
    descripcion: str | None = None
    nutricionista: str
    dieta_de_baja: bool = False
    fecha_inicio: date
    observaciones: str | None = None
    dias: list[MiDiaDeDietaOut] = []


class MiPerfilEditarRequest(BaseModel):
    """
    Lo ÚNICO que un socio puede cambiar de su propia ficha: su contacto.

    No están el DNI, el nombre ni la sede — eso lo administra el gimnasio. Y
    tampoco el objetivo ni las observaciones: el objetivo lo acuerda con su
    entrenador y las observaciones son notas internas del personal.
    """
    email: EmailStr | None = None
    telefono: str | None = None
    emergencia_nombre: str | None = None
    emergencia_telefono: str | None = None
    emergencia_parentesco: str | None = None


class MedicionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_registro_salud: int
    fecha: date
    peso: float | None = None
    altura: float | None = None
    grasa_corporal: float | None = None
    masa_muscular: float | None = None
    observaciones: str | None = None


class MedicionCrear(BaseModel):
    # Los rangos NO son reglas del negocio ni están en el esquema (numeric
    # acepta cualquier cosa): son topes para atajar el dedazo evidente —un 8 o
    # un 800 en vez de 80— antes de que ensucie el historial y deje el gráfico
    # ilegible por una sola fila absurda.
    peso: float = Field(ge=30, le=300)
    altura: float | None = Field(default=None, ge=1.2, le=2.5)
    grasa_corporal: float | None = Field(default=None, ge=0, le=99)
    masa_muscular: float | None = Field(default=None, ge=0, le=99)
    observaciones: str | None = None


class MiProgresoOut(BaseModel):
    """Serie de mediciones más los números que el encabezado ya muestra."""
    # De la más vieja a la más nueva: así se lee el gráfico de izquierda a
    # derecha sin que el cliente tenga que reordenar.
    mediciones: list[MedicionOut] = []
    peso_actual: float | None = None
    # Diferencia contra la PRIMERA medición. Negativo = bajó.
    variacion_peso: float | None = None
    grasa_actual: float | None = None
    altura: float | None = None
    # True si ya cargó una medición hoy. Es una fila por fecha: la del día no
    # se pisa en silencio, se rechaza y se explica.
    ya_cargo_hoy: bool = False


class MiDeudaOut(BaseModel):
    """
    Una deuda vista por el propio socio.

    `observaciones` SÍ viaja: en esta tabla no es una nota interna sino la
    DESCRIPCIÓN de la deuda ("cuota de marzo", "clase suelta del 12"), y es
    justo lo que el socio necesita para entender qué se le está reclamando.
    La vista la muestra con "Cuota impaga" como texto por defecto.
    """
    id_deuda: int
    monto: float
    fecha_generacion: date
    fecha_vencimiento: date | None = None
    observaciones: str | None = None
    # Días de atraso respecto de hoy. 0 o negativo = todavía no venció.
    dias_de_atraso: int = 0


class MiCuotaOut(BaseModel):
    # False = no tiene NINGUNA membresía. Hace falta como campo propio porque
    # fecha_vencimiento en null ya no alcanza para distinguir "sin membresía"
    # de "con membresía que no vence nunca": las dos dan null.
    tiene_membresia: bool = False
    al_dia: bool
    plan: str | None = None
    estado: str = "Sin membresía"
    precio_pactado: float | None = None
    fecha_inicio: date | None = None
    fecha_vencimiento: date | None = None
    dias_restantes: int | None = None
    deuda_total: float = 0
    deudas: list[MiDeudaOut] = []
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
    `id_entrenador` es OPCIONAL y quién puede mandarlo depende de quién sea:

      - Un ENTRENADOR no lo manda: la rutina queda a su nombre. Si mandara el
        id de otro, estaría creando rutinas a nombre ajeno y el historial de
        quién armó qué dejaría de significar algo.

      - El DUEÑO o el RECEPCIONISTA SÍ tienen que mandarlo: tienen el permiso
        de gestionar rutinas pero no son entrenadores, y `Rutina.id_entrenador`
        es NOT NULL. Para ellos elegir el entrenador a cargo no es suplantar a
        nadie, es delegar.

    El router hace valer esa distinción.
    """
    nombre: str = Field(min_length=1, max_length=100)
    objetivo: str | None = None
    nivel: str | None = None
    dias_por_semana: int | None = Field(default=None, ge=1, le=7)
    id_entrenador: int | None = None
    ejercicios: list[RutinaEjercicioCrear] = []


class RutinaEditarRequest(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    objetivo: str | None = None
    nivel: str | None = None
    dias_por_semana: int | None = Field(default=None, ge=1, le=7)
    id_entrenador: int | None = None


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
    """`id_nutricionista` sigue la misma regla que RutinaCrear.id_entrenador."""
    nombre: str = Field(min_length=1, max_length=100)
    objetivo: str | None = None
    calorias_diarias: int | None = None
    descripcion: str | None = None
    id_nutricionista: int | None = None
    comidas: list[ComidaCrear] = []


class DietaEditarRequest(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    objetivo: str | None = None
    calorias_diarias: int | None = None
    descripcion: str | None = None
    id_nutricionista: int | None = None


class ProfesionalOpcion(BaseModel):
    """
    Un entrenador o nutricionista para el selector del formulario.

    Solo se ofrecen los que tienen el empleado ACTIVO: no tiene sentido
    asignarle una rutina nueva a alguien que ya no trabaja en el gimnasio.
    """
    id: int
    nombre: str


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


class UsuarioEditarRequest(BaseModel):
    """
    Solo username y email. El ROL no se edita acá: se deriva de las tablas
    donde la persona aparece, así que cambiarlo sería mentir — para eso se
    edita su ficha de personal. Y la CONTRASEÑA tampoco: para eso está
    resetear-password, que genera una temporal en vez de dejar que un admin
    elija (y por lo tanto conozca) la clave de otro.
    """
    username: str = Field(min_length=1, max_length=50)
    email: EmailStr | None = None


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


# =============================================================================
# PORTAL — la rutina del socio
# =============================================================================
# Va al FINAL del archivo y no junto al resto del portal porque usa
# RutinaEjercicioOut, que se define en la sección de Rutinas más arriba.
# Python ejecuta el cuerpo de cada clase al importar, así que un tipo usado
# antes de existir rompe el import — no es un detalle de estilo.

class MiRutinaOut(BaseModel):
    """
    La rutina vista por el socio. Espejo de MiDietaOut: incluye `fecha_inicio`,
    que viene de la ASIGNACIÓN y no de la plantilla — es propio del vínculo
    entre esa rutina y esta persona.
    """
    id_rutina: int
    nombre: str
    nivel: str | None = None
    objetivo: str | None = None
    dias_por_semana: int | None = None
    entrenador: str
    rutina_de_baja: bool = False
    fecha_inicio: date
    ejercicios: list[RutinaEjercicioOut] = []


# =============================================================================
# PANEL DE RECEPCIÓN
# =============================================================================
#
# Lo que ve el recepcionista apenas abre el sistema. El criterio de todo lo de
# abajo es el mismo: que no tenga que buscar nada. La información llega
# ordenada por urgencia y con la acción al lado.

class InscriptoEnTurno(BaseModel):
    """Una persona anotada en un turno, tal como la muestra el panel."""
    id_reserva: int
    id_socio: int
    nombre: str
    dni: str
    # Derivado, no guardado: pendiente / asistio / ausente / en_espera /
    # cancelada. Ver el docstring de turnos.py.
    estado: str
    es_clase_suelta: bool = False
    # Para que el mostrador sepa si además le tiene que cobrar algo cuando
    # esta persona aparezca. Se resuelve del lado del servidor porque implica
    # mirar membresía y deudas, y hacerlo por fila en el cliente serían dos
    # consultas por persona anotada.
    alerta: str | None = None


class TurnoDePanel(BaseModel):
    """
    Un turno en el panel de próximos.

    `minutos_para_empezar` viene calculado del servidor y no del cliente: es
    lo que ordena la lista, y si cada app lo calculara con su propio reloj,
    dos pantallas del mismo mostrador podrían mostrar órdenes distintas.
    Negativo significa que ya empezó.
    """
    id_turno: int
    actividad: str
    fecha: date
    hora: time
    minutos_para_empezar: int
    vence_a: datetime
    cupo_maximo: int
    ocupados: int
    en_espera: int
    profesor: str | None = None
    estado_turno: str
    # True cuando es la sala abierta (sin profesor y de cupo grande). El panel
    # las colapsa en una línea con el contador en vez de listar 40 nombres que
    # taparían las clases de 15, donde el cupo importa de verdad.
    es_sala_abierta: bool = False
    inscriptos: list[InscriptoEnTurno] = []


class PanelRecepcion(BaseModel):
    """
    La pantalla completa, en un solo pedido.

    Va todo junto y no en cuatro endpoints porque el panel se refresca solo
    cada pocos segundos: cuatro pedidos serían cuatro veces la latencia y
    cuatro oportunidades de que una parte quede desfasada de la otra.
    """
    ahora: datetime
    turnos: list[TurnoDePanel]
    # Turnos cuya tolerancia ya venció pero que empezaron hace poco. Se
    # muestran aparte para que el mostrador entienda por qué alguien reclama
    # una clase que ya no figura arriba.
    vencidos_recientes: list[TurnoDePanel] = []
    total_anotados_hoy: int = 0
    total_presentes_hoy: int = 0


class ResultadoBusqueda(BaseModel):
    """
    Lo que devuelve buscar a alguien por DNI en el mostrador.

    Trae de una todo lo que el recepcionista iba a preguntar después: si está
    al día, cuánto debe y cuál es su próximo turno. La idea es que una sola
    búsqueda cierre la conversación en vez de abrir tres pantallas más.
    """
    id_socio: int
    nombre: str
    dni: str
    numero_socio: str | None = None
    tiene_rfid: bool = False
    activo: bool
    estado_membresia: str
    vencimiento: date | None = None
    deuda_total: float = 0
    proximo_turno: TurnoDePanel | None = None
    alerta: str | None = None


# =============================================================================
# HORARIOS DE ACTIVIDAD
# =============================================================================

class HorarioActividadRequest(BaseModel):
    """
    El horario semanal de una actividad. De acá salen los turnos.

    `dia_semana` es ISO: 1 = lunes ... 7 = domingo. Coincide con
    date.isoweekday() de Python, así que la generación no convierte nada.
    """
    id_actividad: int
    id_sede: int = 1
    dia_semana: int = Field(ge=1, le=7)
    hora: time
    cupo: int = Field(gt=0)
    id_profesor: int | None = None
    vigente_desde: date | None = None   # por defecto, hoy
    vigente_hasta: date | None = None   # None = indefinido


class HorarioActividadOut(BaseModel):
    id_horario_actividad: int
    id_actividad: int
    actividad: str
    id_sede: int
    dia_semana: int
    dia_nombre: str
    hora: time
    cupo: int
    id_profesor: int | None = None
    profesor: str | None = None
    vigente_desde: date
    vigente_hasta: date | None = None
    activo: bool
    # Cuántos turnos generó este horario y siguen por venir. Es la forma de
    # ver de un vistazo si la generación automática está corriendo.
    turnos_futuros: int = 0


class GeneracionTurnosOut(BaseModel):
    creados: int
    horarios: int
    desde: date
    hasta: date
    mensaje: str
