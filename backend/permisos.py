"""
permisos.py
-----------
Matriz de permisos por rol: qué secciones ve cada rol y qué acciones puede
ejecutar.

⚠️ ESTE ARCHIVO ES EL ESPEJO DE `Proyecto/src/frontend/src/config.ts`
   (constantes Acceso, AccionesRol y PERMISOS). Si tocás uno, tocá el otro.

Es la misma duplicación deliberada que la paleta "Kinetic Carbon" entre la
PWA y Flet, y por el mismo motivo: los tres consumidores (PWA, Flet, backend)
necesitan la tabla en su propio lenguaje, y no hay forma de compartirla en
tiempo de ejecución sin agregar un paso de build.

La diferencia con la paleta es que acá desincronizarse no se ve: un color mal
copiado salta a la vista, un permiso mal copiado no. Los síntomas son
asimétricos y silenciosos — el botón aparece pero la API responde 403, o
peor, la API deja pasar algo que el frontend creía prohibido. Por eso vale la
pena leer los dos archivos juntos ante cualquier cambio.

Y una aclaración sobre la división de responsabilidades, que es la idea
central de todo el proyecto: la copia de config.ts es UX (decide qué se
dibuja), esta copia es SEGURIDAD (decide qué se ejecuta). El frontend
esconde; el backend rechaza. Alguien con las devtools abiertas puede alterar
el store de la PWA y hacer aparecer cualquier botón — y cuando lo apriete,
esta tabla es la que lo frena.
"""

from models import Rol


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


# Orden de menor a mayor. Sirve para preguntar "¿alcanza este nivel?" sin
# escribir la comparación a mano en cada endpoint.
_JERARQUIA = {Acceso.NINGUNO: 0, Acceso.LECTURA: 1, Acceso.TOTAL: 2}


# =============================================================================
# SECCIONES — los valores coinciden con `Routes` de config.ts
# =============================================================================

class Seccion:
    DASHBOARD = "dashboard"
    SOCIOS = "socios"
    PERSONAL = "personal"
    RUTINAS = "rutinas"
    NUTRICION = "nutricion"
    USUARIOS = "usuarios"
    ASISTENCIA = "asistencia"
    ACTIVIDADES = "actividades"
    COBROS = "cobros"

    # --- Portal del socio ---
    # El prefijo "mi-" no es decorativo: hace evidente en la URL y en
    # cualquier log que ese endpoint devuelve datos de UNA persona. Una ruta
    # de socio sin ese prefijo es señal de que se coló una consulta global.
    MI_PERFIL = "mi-perfil"
    MI_RUTINA = "mi-rutina"
    MIS_ACTIVIDADES = "mis-actividades"
    MI_PROGRESO = "mi-progreso"
    MI_DIETA = "mi-dieta"
    MI_CUOTA = "mi-cuota"
    MIS_TURNOS = "mis-turnos"

    # --- Pantalla propia del profesor ---
    # Mismo criterio que las "mi-" de arriba: devuelve los turnos de UNA
    # persona, los que dicta ella. No es una vista filtrada de ACTIVIDADES —
    # esa es el ABM del catálogo y el profesor no tiene nada que hacer ahí.
    MIS_CLASES = "mis-clases"


class Accion:
    """
    Acciones puntuales, separadas del acceso a la sección: no alcanza con
    proteger la ruta, la operación concreta también se valida. Un
    Recepcionista entra a Personal (LECTURA) pero no puede dar de alta a
    nadie — son dos permisos distintos sobre la misma pantalla.
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


# Las pantallas PERSONALES, apagadas de una: las siete del portal del socio
# más "Mis clases" del profesor. Todo rol de staff las tiene en NINGUNO: "Mi
# rutina" es la rutina DE UNO, no tiene sentido que la abra un entrenador
# (para eso tiene /rutinas, que las lista todas).
_SIN_PANTALLAS_PROPIAS = {
    Seccion.MI_PERFIL: Acceso.NINGUNO,
    Seccion.MI_RUTINA: Acceso.NINGUNO,
    Seccion.MIS_ACTIVIDADES: Acceso.NINGUNO,
    Seccion.MI_PROGRESO: Acceso.NINGUNO,
    Seccion.MI_DIETA: Acceso.NINGUNO,
    Seccion.MI_CUOTA: Acceso.NINGUNO,
    Seccion.MIS_TURNOS: Acceso.NINGUNO,
    Seccion.MIS_CLASES: Acceso.NINGUNO,
}

# Nombre anterior, mantenido por si algo lo importa. El set creció: ya no es
# sólo el portal del socio.
_SIN_PORTAL_SOCIO = _SIN_PANTALLAS_PROPIAS

# Espejo del anterior: el socio no entra a NINGUNA pantalla de gestión.
_SIN_ADMIN = {
    Seccion.DASHBOARD: Acceso.NINGUNO,
    Seccion.SOCIOS: Acceso.NINGUNO,
    Seccion.PERSONAL: Acceso.NINGUNO,
    Seccion.RUTINAS: Acceso.NINGUNO,
    Seccion.NUTRICION: Acceso.NINGUNO,
    Seccion.USUARIOS: Acceso.NINGUNO,
    Seccion.ASISTENCIA: Acceso.NINGUNO,
    Seccion.ACTIVIDADES: Acceso.NINGUNO,
    Seccion.COBROS: Acceso.NINGUNO,
}

# Todas las acciones declaradas en `Accion`, en orden. Se calcula filtrando
# por el NOMBRE del atributo y no por su valor: vars() también devuelve
# __module__, __qualname__ y __doc__, cuyos valores son strings normales que
# se colarían como acciones inventadas si se filtrara por el valor.
TODAS_LAS_ACCIONES = tuple(
    valor for nombre, valor in vars(Accion).items() if not nombre.startswith("_")
)


def _todas_en(valor: bool) -> dict[str, bool]:
    """Atajo para los roles que tienen todas las acciones en el mismo estado."""
    return {accion: valor for accion in TODAS_LAS_ACCIONES}


# =============================================================================
# LA MATRIZ
# =============================================================================

PERMISOS: dict[str, dict] = {

    # Control total en todo. Decisión explícita del dueño del proyecto por
    # sobre el DFD original, que lo marcaba como "No" en rutinas y dietas.
    Rol.DUENO: {
        "secciones": {
            Seccion.DASHBOARD: Acceso.TOTAL,
            Seccion.SOCIOS: Acceso.TOTAL,
            Seccion.PERSONAL: Acceso.TOTAL,
            Seccion.RUTINAS: Acceso.TOTAL,
            Seccion.NUTRICION: Acceso.TOTAL,
            Seccion.USUARIOS: Acceso.TOTAL,
            Seccion.ASISTENCIA: Acceso.TOTAL,
            Seccion.ACTIVIDADES: Acceso.TOTAL,
            Seccion.COBROS: Acceso.TOTAL,
            **_SIN_PORTAL_SOCIO,
        },
        "acciones": _todas_en(True),
    },

    # El respaldo operativo de todo el gimnasio. Ve Personal pero no puede dar
    # de alta ni de baja a nadie (eso es exclusivo del Dueño) — de ahí que la
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
    # Su límite real es su propia cuenta de acceso — no puede editarla
    # ni desactivarla, pero eso es una regla de FILA, no de sección, y se
    # aplica en el router de usuarios, no acá.
    Rol.RECEPCIONISTA: {
        "secciones": {
            Seccion.DASHBOARD: Acceso.TOTAL,
            Seccion.SOCIOS: Acceso.TOTAL,
            Seccion.PERSONAL: Acceso.LECTURA,
            Seccion.RUTINAS: Acceso.TOTAL,
            Seccion.NUTRICION: Acceso.TOTAL,
            Seccion.USUARIOS: Acceso.TOTAL,
            Seccion.ASISTENCIA: Acceso.TOTAL,
            Seccion.ACTIVIDADES: Acceso.TOTAL,
            Seccion.COBROS: Acceso.TOTAL,
            **_SIN_PORTAL_SOCIO,
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
            Seccion.DASHBOARD: Acceso.NINGUNO,
            Seccion.SOCIOS: Acceso.LECTURA,
            Seccion.PERSONAL: Acceso.NINGUNO,
            Seccion.RUTINAS: Acceso.TOTAL,
            Seccion.NUTRICION: Acceso.LECTURA,
            Seccion.USUARIOS: Acceso.NINGUNO,
            Seccion.ASISTENCIA: Acceso.NINGUNO,
            Seccion.ACTIVIDADES: Acceso.NINGUNO,
            Seccion.COBROS: Acceso.NINGUNO,
            **_SIN_PORTAL_SOCIO,
        },
        "acciones": {
            **_todas_en(False),
            Accion.GESTION_RUTINAS: True,
            # Una rodilla operada cambia la rutina. Es el motivo por el que
            # el gimnasio guarda este dato.
            Accion.VER_HISTORIAL_MEDICO: True,
        },
    },

    # Espejo del Entrenador: gestiona dietas, lee rutinas y socios.
    Rol.NUTRICIONISTA: {
        "secciones": {
            Seccion.DASHBOARD: Acceso.NINGUNO,
            Seccion.SOCIOS: Acceso.LECTURA,
            Seccion.PERSONAL: Acceso.NINGUNO,
            Seccion.RUTINAS: Acceso.LECTURA,
            Seccion.NUTRICION: Acceso.TOTAL,
            Seccion.USUARIOS: Acceso.NINGUNO,
            Seccion.ASISTENCIA: Acceso.NINGUNO,
            Seccion.ACTIVIDADES: Acceso.NINGUNO,
            Seccion.COBROS: Acceso.NINGUNO,
            **_SIN_PORTAL_SOCIO,
        },
        "acciones": {
            **_todas_en(False),
            Accion.GESTION_DIETAS: True,
            # Una celiaquía o una diabetes cambian la dieta.
            Accion.VER_HISTORIAL_MEDICO: True,
        },
    },

    # El Socio es un CLIENTE, no personal: cero acceso a pantallas de gestión,
    # acceso total a las siete que son SUYAS.
    #
    # La auditoría del 2026-08-03 verificó qué pasaba cuando este rol tenía
    # acceso de gestión como parche temporal: un socio —incluso uno dado de
    # baja— entraba y veía el DNI de todos los demás socios, el legajo del
    # personal, y tenía botones para dar de alta y de baja gente.
    #
    # Las acciones quedan TODAS en False y no es un olvido: son acciones sobre
    # el gimnasio (dar de baja socios, cobrar, gestionar promociones). Lo que
    # el socio sí puede hacer —editar su contacto, cargar su peso, reservar su
    # turno— no vive en esta lista porque no son permisos sobre terceros: son
    # operaciones sobre su propia ficha, y el permiso para hacerlas es,
    # exactamente, tener acceso a su propia sección.
    Rol.SOCIO: {
        "secciones": {
            **_SIN_ADMIN,
            Seccion.MIS_CLASES: Acceso.NINGUNO,
            Seccion.MI_PERFIL: Acceso.TOTAL,
            Seccion.MI_RUTINA: Acceso.TOTAL,
            Seccion.MIS_ACTIVIDADES: Acceso.TOTAL,
            Seccion.MI_PROGRESO: Acceso.TOTAL,
            Seccion.MI_DIETA: Acceso.TOTAL,
            Seccion.MI_CUOTA: Acceso.TOTAL,
            Seccion.MIS_TURNOS: Acceso.TOTAL,
        },
        "acciones": _todas_en(False),
    },

    # El Profesor dicta las clases grupales. NO es un rol de gestión: no entra
    # a ninguna de las nueve secciones del staff, ni siquiera a ACTIVIDADES —
    # el catálogo (precios, cupos, qué actividades existen) es configuración
    # del Dueño, y el profesor no tiene nada que decidir ahí.
    #
    # Lo único suyo es "Mis clases": los turnos que dicta ÉL, con la lista de
    # quién se anotó. Antes esto no existía y el profesor se enteraba de su
    # horario por WhatsApp.
    #
    # Todas las acciones en False, igual que el Socio, y por el mismo motivo:
    # son acciones sobre el gimnasio (cobrar, dar de baja, gestionar turnos).
    # Mirar su propia clase no es un permiso sobre terceros.
    Rol.PROFESOR: {
        "secciones": {
            **_SIN_ADMIN,
            **_SIN_PANTALLAS_PROPIAS,
            Seccion.MIS_CLASES: Acceso.LECTURA,
        },
        "acciones": _todas_en(False),
    },
}


# =============================================================================
# CONSULTAS SOBRE LA MATRIZ
# =============================================================================
#
# Todas reciben una LISTA de roles, no uno solo, porque los roles se acumulan:
# el dueño del gimnasio suele entrenar ahí (dueno + socio). La regla siempre
# es quedarse con el permiso MÁS ALTO entre los roles que tenga la persona —
# tener un rol extra nunca puede quitar permisos.

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


def puede_accion(roles: list[str], accion: str) -> bool:
    """True si alguno de los roles habilita la acción."""
    return any(PERMISOS.get(rol, {}).get("acciones", {}).get(accion, False)
               for rol in roles)
