# =============================================================================
# permisos.py — Qué ve y qué puede hacer cada rol
# =============================================================================
#
# ⚠️ ESTE ARCHIVO ES EL TERCER ESPEJO DE LA MISMA TABLA:
#
#      PWA      → Proyecto/src/frontend/src/config.ts  (Acceso, PERMISOS)
#      Backend  → backend/permisos.py
#      Flet     → este archivo
#
#    Si tocás uno, tocá los tres.
#
# Es la misma duplicación deliberada que la paleta "Kinetic Carbon", y por el
# mismo motivo: los tres consumidores necesitan la tabla en su propio lenguaje
# y no hay forma de compartirla en runtime sin agregar un paso de build.
#
# La diferencia con la paleta es que acá desincronizarse NO SE VE. Un color
# mal copiado salta a la vista; un permiso mal copiado no. Los síntomas son
# silenciosos: el botón aparece pero la API contesta 403, o —peor— la app
# esconde algo que el backend sí deja hacer y nadie se entera de que el
# permiso estaba mal puesto.
#
# ── Y algo que conviene tener claro sobre este archivo en particular ────────
#
# ESTA COPIA NO ES SEGURIDAD. Es UX: decide qué se dibuja y qué se puede
# apretar. Quien decide qué se EJECUTA es backend/permisos.py, del otro lado
# de la red. Esconder un botón acá no protege nada — el archivo está en el
# disco del cliente y cualquiera puede editarlo. Lo que protege es que el
# endpoint rechace.
#
# Sirve igual, y mucho: sin esto, un Entrenador ve nueve secciones de las
# cuales siete le contestan 403 apenas entra. La app se siente rota aunque
# esté funcionando exactamente como debe.

class Routes:
    """
    Los nombres de sección, repetidos de app/config.py.

    Se repiten a propósito, y cuesta explicarlo, así que: config.py hace
    `import flet`. Si este archivo importara de ahí, la matriz de permisos
    quedaría atada a la librería gráfica, y el verificador que la compara
    contra el backend (backend/check_permisos.py) no podría importarla sin
    tener Flet instalado — que es exactamente lo que pasó la primera vez.

    Una tabla de permisos no debería necesitar un toolkit de UI para poder
    leerse. Los valores son idénticos a los de Routes en config.py y
    check_permisos.py verifica que sigan siéndolo, así que la duplicación no
    puede desincronizarse en silencio.
    """
    DASHBOARD = "dashboard"
    RECEPCION = "recepcion"
    SOCIOS = "socios"
    COBROS = "cobros"
    ASISTENCIA = "asistencia"
    PERSONAL = "personal"
    RUTINAS = "rutinas"
    NUTRICION = "nutricion"
    ACTIVIDADES = "actividades"
    USUARIOS = "usuarios"


# =============================================================================
# NIVELES DE ACCESO
# =============================================================================

class Acceso:
    """
    Tres niveles y no dos, porque hacen falta los tres: un Entrenador tiene
    que poder CONSULTAR la dieta de un socio (para saber de quién es) sin
    poder gestionarla. Eso no es ni acceso total ni acceso nulo.
    """
    NINGUNO = "ninguno"
    LECTURA = "lectura"
    TOTAL = "total"


# Orden de menor a mayor, para poder preguntar "¿alcanza este nivel?" sin
# escribir la comparación a mano en cada lugar.
_JERARQUIA = {Acceso.NINGUNO: 0, Acceso.LECTURA: 1, Acceso.TOTAL: 2}


# =============================================================================
# ROLES
# =============================================================================

class Rol:
    """
    Los seis roles que devuelve el backend en el login.

    NO son una columna de Usuario: el backend los deriva de en cuál de las
    tablas de rol está la Persona (Dueno, Socio, Entrenador, ...) y los firma
    dentro del token. Los valores tienen que coincidir exactamente con los de
    models.Rol del backend y con RolUsuario de config.ts.

    El Profesor entró en la lista el 2026-09-16. Antes no iniciaba sesión;
    ahora sí, pero SÓLO en la PWA, donde tiene "Mis clases". En esta app no
    tiene nada que hacer —sus diez secciones quedan en NINGUNO— y por eso
    ROLES_CON_ACCESO lo deja afuera solo y el login le dice que use la web.
    """
    DUENO = "dueno"
    SOCIO = "socio"
    ENTRENADOR = "entrenador"
    NUTRICIONISTA = "nutricionista"
    RECEPCIONISTA = "recepcionista"
    PROFESOR = "profesor"


# =============================================================================
# SECCIONES Y ACCIONES
# =============================================================================
#
# Las secciones son las rutas de Routes. Se referencian desde ahí en vez de
# repetir los strings: si mañana una ruta cambia de nombre, el menú y la
# matriz no pueden quedar apuntando a cosas distintas.
#
# Las siete pantallas del portal del socio (mi-perfil, mi-rutina, ...) que sí
# están en config.ts y en el backend NO figuran acá, y no es un olvido: son
# pantallas de la PWA. Esta app es la del personal del gimnasio y no tiene
# ninguna de ellas. Lo que sí importa del Socio es que no entre — ver
# ROLES_CON_ACCESO al final.

class Accion:
    """
    Acciones puntuales, separadas del acceso a la sección: no alcanza con
    saber si alguien entra a una pantalla, hay que saber si puede ejecutar
    la operación concreta. Un Recepcionista entra a Personal (LECTURA) pero
    no puede dar de alta a nadie — dos permisos distintos sobre la misma
    pantalla.
    """
    ALTA_BAJA_SOCIOS = "altaBajaSocios"
    ALTA_BAJA_PERSONAL = "altaBajaPersonal"
    GESTION_RUTINAS = "gestionRutinas"
    GESTION_DIETAS = "gestionDietas"
    GESTION_USUARIOS = "gestionUsuarios"
    VER_INGRESOS = "verIngresos"
    COBRAR_PAGOS = "cobrarPagos"
    GESTION_PROMOCIONES = "gestionPromociones"
    GESTION_DEUDAS = "gestionDeudas"
    GESTION_TURNOS = "gestionTurnos"
    # Historial medico del socio: patologias, lesiones, condiciones.
    #
    # El RECEPCIONISTA NO la tiene, y es la unica accion donde queda por
    # debajo del Entrenador y del Nutricionista. El mostrador maneja plata,
    # turnos e ingresos; no hay ninguna tarea suya que requiera saber quien
    # tiene diabetes, epilepsia o una lesion de rodilla. Para una emergencia
    # lo que hace falta es el contacto de emergencia, que vive en Persona y
    # si ve.
    #
    # El Entrenador y el Nutricionista SI: una rodilla operada cambia la
    # rutina y una celiaquia cambia la dieta. Ese es todo el motivo por el
    # que el gimnasio guarda este dato.
    VER_HISTORIAL_MEDICO = "verHistorialMedico"


# Todas las acciones declaradas arriba. Se filtra por el NOMBRE del atributo y
# no por su valor: vars() también devuelve __module__, __qualname__ y __doc__,
# cuyos valores son strings normales que se colarían como acciones inventadas
# si se filtrara por el valor. (Mismo detalle que en backend/permisos.py, y
# ahí costó encontrarlo.)
TODAS_LAS_ACCIONES = tuple(
    valor for nombre, valor in vars(Accion).items() if not nombre.startswith("_")
)


def _todas_en(valor: bool) -> dict[str, bool]:
    """Atajo para los roles que tienen todas las acciones en el mismo estado."""
    return {accion: valor for accion in TODAS_LAS_ACCIONES}


# Las nueve secciones apagadas de una. Lo usa el Socio, que no entra a
# ninguna pantalla de gestión.
_SIN_ACCESO = {
    Routes.DASHBOARD: Acceso.NINGUNO,
    Routes.RECEPCION: Acceso.NINGUNO,
    Routes.SOCIOS: Acceso.NINGUNO,
    Routes.PERSONAL: Acceso.NINGUNO,
    Routes.RUTINAS: Acceso.NINGUNO,
    Routes.NUTRICION: Acceso.NINGUNO,
    Routes.USUARIOS: Acceso.NINGUNO,
    Routes.ASISTENCIA: Acceso.NINGUNO,
    Routes.ACTIVIDADES: Acceso.NINGUNO,
    Routes.COBROS: Acceso.NINGUNO,
}


# =============================================================================
# LA MATRIZ
# =============================================================================

PERMISOS: dict[str, dict] = {

    # Control total en todo. Decisión explícita del dueño del proyecto por
    # sobre el DFD original, que lo marcaba como "No" en rutinas y dietas.
    Rol.DUENO: {
        "secciones": {
            Routes.DASHBOARD: Acceso.TOTAL,
            Routes.RECEPCION: Acceso.TOTAL,
            Routes.SOCIOS: Acceso.TOTAL,
            Routes.PERSONAL: Acceso.TOTAL,
            Routes.RUTINAS: Acceso.TOTAL,
            Routes.NUTRICION: Acceso.TOTAL,
            Routes.USUARIOS: Acceso.TOTAL,
            Routes.ASISTENCIA: Acceso.TOTAL,
            Routes.ACTIVIDADES: Acceso.TOTAL,
            Routes.COBROS: Acceso.TOTAL,
        },
        "acciones": _todas_en(True),
    },

    # El respaldo operativo de todo el gimnasio. Ve Personal pero no da de
    # alta ni de baja a nadie (eso es exclusivo del Dueño) — de ahí que la
    # sección quede en LECTURA con la acción en False.
    #
    # Tiene control total en Usuarios, Rutinas y Nutrición: si un Entrenador
    # no puede entrar a su cuenta, es el Recepcionista quien le gestiona la
    # rutina o se la asigna a un socio en su lugar.
    #
    # No ve ingresos (dato de negocio, no operativo). SÍ gestiona Actividades
    # igual que el Dueño (decisión del dueño, 2026-09-16): cargar horarios,
    # profesores y planes es lo que hace que existan turnos, y eso lo resuelve
    # el mostrador en el día a día. Antes quedaba en NINGUNO por ser
    # "configuración" y el que atiende no tenía dónde ver ni armar una clase.
    # Su límite real es su propia cuenta de acceso, pero eso es una
    # regla de FILA y la aplica el backend, no esta tabla.
    Rol.RECEPCIONISTA: {
        "secciones": {
            Routes.DASHBOARD: Acceso.TOTAL,
            Routes.RECEPCION: Acceso.TOTAL,
            Routes.SOCIOS: Acceso.TOTAL,
            Routes.PERSONAL: Acceso.LECTURA,
            Routes.RUTINAS: Acceso.TOTAL,
            Routes.NUTRICION: Acceso.TOTAL,
            Routes.USUARIOS: Acceso.TOTAL,
            Routes.ASISTENCIA: Acceso.TOTAL,
            Routes.ACTIVIDADES: Acceso.TOTAL,
            Routes.COBROS: Acceso.TOTAL,
        },
        "acciones": {
            Accion.ALTA_BAJA_SOCIOS: True,
            Accion.ALTA_BAJA_PERSONAL: False,
            Accion.GESTION_RUTINAS: True,
            Accion.GESTION_DIETAS: True,
            Accion.GESTION_USUARIOS: True,
            Accion.VER_INGRESOS: False,
            Accion.COBRAR_PAGOS: True,
            Accion.GESTION_PROMOCIONES: False,
            Accion.GESTION_DEUDAS: False,
            Accion.GESTION_TURNOS: True,
            Accion.VER_HISTORIAL_MEDICO: False,
        },
    },

    # Gestiona rutinas y nada más. Lee Socios (necesita saber a quién le
    # asigna) y lee Nutrición: puede consultar una dieta para ver de qué socio
    # es, pero no darla de alta ni desligarla.
    Rol.ENTRENADOR: {
        "secciones": {
            Routes.DASHBOARD: Acceso.NINGUNO,
            Routes.RECEPCION: Acceso.NINGUNO,
            Routes.SOCIOS: Acceso.LECTURA,
            Routes.PERSONAL: Acceso.NINGUNO,
            Routes.RUTINAS: Acceso.TOTAL,
            Routes.NUTRICION: Acceso.LECTURA,
            Routes.USUARIOS: Acceso.NINGUNO,
            Routes.ASISTENCIA: Acceso.NINGUNO,
            Routes.ACTIVIDADES: Acceso.NINGUNO,
            Routes.COBROS: Acceso.NINGUNO,
        },
        "acciones": {
            **_todas_en(False),
            Accion.GESTION_RUTINAS: True,
            Accion.VER_HISTORIAL_MEDICO: True,
        },
    },

    # Espejo del Entrenador: gestiona dietas, lee rutinas y socios.
    Rol.NUTRICIONISTA: {
        "secciones": {
            Routes.DASHBOARD: Acceso.NINGUNO,
            Routes.RECEPCION: Acceso.NINGUNO,
            Routes.SOCIOS: Acceso.LECTURA,
            Routes.PERSONAL: Acceso.NINGUNO,
            Routes.RUTINAS: Acceso.LECTURA,
            Routes.NUTRICION: Acceso.TOTAL,
            Routes.USUARIOS: Acceso.NINGUNO,
            Routes.ASISTENCIA: Acceso.NINGUNO,
            Routes.ACTIVIDADES: Acceso.NINGUNO,
            Routes.COBROS: Acceso.NINGUNO,
        },
        "acciones": {
            **_todas_en(False),
            Accion.GESTION_DIETAS: True,
            Accion.VER_HISTORIAL_MEDICO: True,
        },
    },

    # El Socio es un CLIENTE, no personal: cero acceso a todo lo de acá. Sus
    # siete pantallas están en la PWA, que es la app que le corresponde.
    #
    # La auditoría del 2026-08-03 verificó qué pasaba cuando este rol tenía
    # acceso de gestión como parche temporal: un socio —incluso uno dado de
    # baja— veía el DNI de todos los demás socios, el legajo del personal, y
    # tenía botones para dar de alta y de baja gente.
    Rol.SOCIO: {
        "secciones": dict(_SIN_ACCESO),
        "acciones": _todas_en(False),
    },

    # El Profesor dicta las clases grupales y su pantalla ("Mis clases") vive
    # en la PWA, no acá: esta app es la del mostrador. Las diez secciones en
    # NINGUNO no son un olvido — son la forma de que ROLES_CON_ACCESO lo
    # excluya y el login lo mande a la web en vez de dejarlo entrar a un
    # sidebar vacío. Mismo tratamiento que el Socio, y por el mismo motivo.
    Rol.PROFESOR: {
        "secciones": dict(_SIN_ACCESO),
        "acciones": _todas_en(False),
    },
}


# Roles que tienen algo que hacer en ESTA app. Se calcula de la matriz en vez
# de escribirse a mano para que no puedan contradecirse: un rol entra si la
# matriz le da acceso a alguna sección.
ROLES_CON_ACCESO = frozenset(
    rol for rol, permisos in PERMISOS.items()
    if any(nivel != Acceso.NINGUNO for nivel in permisos["secciones"].values())
)


# =============================================================================
# CONSULTAS SOBRE LA MATRIZ
# =============================================================================
#
# Todas reciben una LISTA de roles y no uno solo, porque los roles se acumulan:
# el dueño del gimnasio suele entrenar ahí (dueno + socio). La regla siempre es
# quedarse con el permiso MÁS ALTO entre los roles que tenga la persona —
# tener un rol de más nunca puede quitar permisos.
#
# Eso último importa acá más que en los otros dos espejos: si se tomara el
# primer rol de la lista en vez del mejor, un dueño que además es socio del
# gimnasio podría quedar sin acceso a su propio sistema según en qué orden
# vinieran los roles en el token.

def acceso_a_seccion(roles: list[str], seccion: str) -> str:
    """Nivel de acceso efectivo de una lista de roles sobre una sección."""
    mejor = Acceso.NINGUNO
    for rol in roles:
        permisos = PERMISOS.get(rol)
        if not permisos:
            continue
        nivel = permisos["secciones"].get(seccion, Acceso.NINGUNO)
        if _JERARQUIA[nivel] > _JERARQUIA[mejor]:
            mejor = nivel
    return mejor


def alcanza(nivel: str, minimo: str) -> bool:
    """¿`nivel` es al menos `minimo`? (TOTAL alcanza donde se pide LECTURA.)"""
    return _JERARQUIA.get(nivel, 0) >= _JERARQUIA.get(minimo, 0)


def puede_ver(roles: list[str], seccion: str) -> bool:
    """¿Esta persona puede abrir la sección, aunque sea para mirar?"""
    return acceso_a_seccion(roles, seccion) != Acceso.NINGUNO


def puede_editar(roles: list[str], seccion: str) -> bool:
    """¿Puede además modificar lo que hay en la sección?"""
    return acceso_a_seccion(roles, seccion) == Acceso.TOTAL


def puede_accion(roles: list[str], accion: str) -> bool:
    """True si alguno de los roles habilita la acción."""
    return any(PERMISOS.get(rol, {}).get("acciones", {}).get(accion, False)
               for rol in roles)


def tiene_acceso_a_la_app(roles: list[str]) -> bool:
    """
    ¿Esta persona tiene algo que hacer en la app de escritorio?

    Un Socio se autentica perfectamente contra el backend —su cuenta es
    válida— pero esta app no es la suya. Sin este chequeo entraría y vería un
    sidebar vacío y una pantalla en blanco, sin ninguna explicación de por
    qué. Es mejor no dejarlo pasar y decirle que use la web.
    """
    return any(rol in ROLES_CON_ACCESO for rol in roles)
