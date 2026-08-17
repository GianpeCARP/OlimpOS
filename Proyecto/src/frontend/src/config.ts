// Config global — equivalente React de config.py (docs/config.md).
// Paleta tomada de docs/DESIGN.md "OlimpOS Kinetic Carbon" v2.0.
// No usar los nombres/valores de la versión vieja en Flet (verde).

import {
  LayoutDashboard,
  Users,
  UserCog,
  Dumbbell,
  Apple,
  ShieldCheck,
  UserRound,
  TrendingUp,
  CreditCard,
  CalendarCheck,
  CalendarClock,
  Fingerprint,
  Wallet,
  type LucideIcon,
} from 'lucide-react';

export const APP_NAME = 'OlimpOS';
export const APP_VERSION = '0.1.0';

// Locale y moneda para todo formateo de números, fechas e importes. El
// gimnasio es de Moreno (Buenos Aires) — ver Sede en el mock. Centralizado
// acá para no repartir 'es-AR' ni '$' por las vistas.
export const LOCALE = 'es-AR';
export const MONEDA = 'ARS';

export const colors = {
  // Superficies
  surfaceBase: '#15171C',
  surfaceCard: '#1C1F26',
  surfaceHover: '#242832',

  // Acentos de energía
  primaryVolt: '#C6F135',
  primaryDim: '#9BBE22',
  accentCoral: '#FF6B3D',
  accentDim: '#D2542C',

  // Bordes vivos
  borderIdle: '#2A3324',
  borderActive: '#586A36',
  borderGlow: 'rgba(198, 241, 53, 0.25)',

  // Tipografía
  textMain: '#F2F3F5',
  textSecondary: '#A4A9B4',
  textMuted: '#6C7280',

  // Semántica de estados
  statusOk: '#3DDC97',
  statusWarn: '#FFC24B',
  statusDanger: '#FF5C5C',
} as const;

export const fonts = {
  heading: "'Barlow Semi Condensed', sans-serif",
  body: "'Archivo', sans-serif",
  // Exclusiva para métricas/telemetría (DESIGN.md §6) — no usar en texto general.
  mono: "'JetBrains Mono', monospace",
} as const;

export const rounded = {
  sm: '6px',
  md: '10px',
  lg: '14px',
  full: '9999px',
} as const;

export type ColorToken = keyof typeof colors;

// Dimensiones. NO están definidas en layout.md/ui.md (son estructurales, sin
// valores de diseño) — placeholders razonables hasta tener los reales.
export const SIDEBAR_WIDTH = 260;
export const TOPBAR_HEIGHT = 64;

// Identificadores de ruta (router.md / state.md). 'login' es el único valor
// literal confirmado (state.md: self.current_route por defecto = "login");
// el resto sigue el mismo patrón (minúsculas, sin prefijo).
export const Routes = {
  LOGIN: 'login',
  // Acá vivía REGISTRO (auth.spec.md 3.1, registro de socio). Se eliminó: la
  // consigna prohíbe el auto-registro en un sistema interno de gestión. El
  // alta de un socio la hace el personal y el backend genera una contraseña
  // temporal.
  //
  // Esa contraseña temporal es lo que hace falta cambiar acá. Es la segunda
  // ruta pública, y tiene que serlo: quien llega no tiene sesión —el backend
  // se la negó justamente por tener la clave temporal— así que exigir token
  // dejaría la cuenta en un punto muerto del que no se puede salir.
  CAMBIAR_PASSWORD: 'cambiar-password',
  DASHBOARD: 'dashboard',
  SOCIOS: 'socios',
  PERSONAL: 'personal',
  RUTINAS: 'rutinas',
  NUTRICION: 'nutricion',
  USUARIOS: 'usuarios',
  // Panel de recepción: fichajes del día (RFID + carga manual). Sección de
  // gestión como las de arriba, no del portal del socio — el socio ficha
  // pasando su tarjeta, no entrando a una pantalla.
  ASISTENCIA: 'asistencia',
  // ABM del catálogo (Actividad + Plan_Actividad): cupo, precio, ventana de
  // cancelación. Exclusiva del Dueño en el .md, igual criterio que
  // Alta/Baja de Personal — es configuración de negocio, no operativa del
  // día a día como Asistencia o Socios.
  ACTIVIDADES: 'actividades',
  // Cobrar membresía, deudas, planes de actividad y clases sueltas. Mismo
  // par de roles que Asistencia (Dueño + Recepcionista): es operativo del
  // día a día, no configuración de negocio como Actividades.
  COBROS: 'cobros',

  // --- Portal del socio ---
  //
  // Rutas propias, no un subconjunto filtrado de las de arriba: el socio es
  // un CLIENTE, no personal. "socios" lista a todo el mundo; "mi-perfil"
  // muestra una sola ficha, la suya. Son dos pantallas distintas con dos
  // consultas distintas, no la misma con un filtro — por eso rutas
  // separadas y no /socios/:id.
  //
  // El prefijo "mi-" no es decorativo: hace evidente en la URL, en el
  // router y en cualquier log que ese endpoint devuelve datos de UNA
  // persona. Si alguna vez aparece una ruta de socio sin ese prefijo, es
  // señal de que se coló una consulta global donde no va.
  MI_PERFIL: 'mi-perfil',
  MI_RUTINA: 'mi-rutina',
  // Actividades con horario (yoga, boxeo, etc.) — distinto de MI_RUTINA
  // (musculación) y de MIS_TURNOS (que sigue sin construirse, ver
  // project-olimpos-modelo-turnos). Comprar un plan no necesita elegir
  // turno; sólo "comprar clase suelta" sí, y esa parte puntual vive DENTRO
  // de esta vista con un selector acotado — no es la vista Mis Turnos.
  MIS_ACTIVIDADES: 'mis-actividades',
  MI_PROGRESO: 'mi-progreso',
  MI_DIETA: 'mi-dieta',
  MI_CUOTA: 'mi-cuota',
  MIS_TURNOS: 'mis-turnos',
} as const;

export type RouteValue = (typeof Routes)[keyof typeof Routes];

/**
 * Intentos fallidos antes de que el backend bloquee una cuenta.
 *
 * ⚠️ Espejo de MAX_INTENTOS_FALLIDOS en backend/routers/auth_router.py, que es
 * quien REALMENTE cuenta y bloquea. Acá se usa sólo para avisarlo en la
 * pantalla de login. Si divergen, el aviso miente pero nada se rompe.
 *
 * El aviso es genérico a propósito: se muestra ante cualquier error de
 * credenciales, sin decir cuántos intentos quedan. Decir "te quedan 2" sería
 * confirmarle a un atacante que ese usuario existe, que es justo lo que evita
 * el mensaje único de auth.spec.md 3.2.
 */
export const MAX_INTENTOS_FALLIDOS = 5;

// Roles del sistema. Única fuente de verdad del nombre de cada rol: lo usan
// el guard de ruta (ProtectedRoute), el filtro del sidebar y el mock de
// authService. Si el string vive suelto en cada archivo, cambiarlo en uno
// solo rompe de forma silenciosa y asimétrica (link oculto pero ruta
// abierta, o al revés).
export const Roles = {
  SOCIO: 'socio',
  DUENO: 'dueno',
  // Roles de personal. No son una columna del esquema: se derivan de en cuál
  // de las tablas hijas de Empleado está la persona (ver personalService.
  // rolDeSesionDeEmpleado), igual que RolEmpleado más abajo — este enum es
  // la versión "de sesión" de esos mismos roles.
  RECEPCIONISTA: 'recepcionista',
  ENTRENADOR: 'entrenador',
  NUTRICIONISTA: 'nutricionista',
} as const;

export type RolValue = (typeof Roles)[keyof typeof Roles];

// Etiqueta para mostrar cada rol en pantalla — los valores de Roles son los
// de login (minúsculas, usados en checks de código), esto es solo el texto
// que ve el usuario.
export const RolLabel: Record<RolValue, string> = {
  [Roles.SOCIO]: 'Socio',
  [Roles.DUENO]: 'Dueño',
  [Roles.RECEPCIONISTA]: 'Recepcionista',
  [Roles.ENTRENADOR]: 'Entrenador',
  [Roles.NUTRICIONISTA]: 'Nutricionista',
};

// =========================================================================
// PERMISOS POR ROL
// =========================================================================
//
// ⚠️ ESTO ES UX, NO SEGURIDAD. Todo lo de acá abajo decide qué VE y qué
// puede CLICKEAR cada rol en el frontend. Cualquiera con las devtools
// abiertas puede alterar el estado del store y saltearse todos estos
// chequeos. Cuando se conecte el backend en Python (FastAPI), CADA UNA de
// estas acciones tiene que revalidarse del lado del servidor contra esta
// misma matriz — si no, la app es abierta de par en par. Esta tabla puede
// servir como especificación para escribir esos guards del backend, pero no
// los reemplaza.
//
// Matriz derivada del DFD (docs/prompt_permisos_personal.md), con una
// excepción confirmada por el usuario: la matriz original marcaba al Dueño
// como "No" en gestión de rutinas y dietas; se cambió a control total por
// pedido explícito ("el dueño puede hacer todo").

/**
 * Tres niveles y no dos, porque hacen falta los tres: un Entrenador tiene
 * que poder CONSULTAR la dieta de un socio (para saber de quién es) sin
 * poder gestionarla — eso no es ni acceso total ni acceso nulo.
 */
export const Acceso = {
  /** No aparece en el sidebar y entrar por URL redirige. */
  NINGUNO: 'ninguno',
  /** Ve los datos, sin ningún botón de acción. */
  LECTURA: 'lectura',
  /** Ve y gestiona. */
  TOTAL: 'total',
} as const;

export type AccesoValue = (typeof Acceso)[keyof typeof Acceso];

/** Las secciones con permisos. Las dos rutas públicas quedan afuera. */
export type SeccionPrivada = Exclude<
  RouteValue,
  typeof Routes.LOGIN | typeof Routes.CAMBIAR_PASSWORD
>;

/**
 * Acciones puntuales, separadas del acceso a la sección: no alcanza con
 * proteger la ruta, el botón concreto también se valida (punto 2 del
 * prompt). Las cuatro últimas todavía no tienen panel donde aplicarse
 * (pagos, promociones, deudas y turnos no tienen vista construida) — se
 * declaran igual para que la matriz esté completa y esos paneles nazcan ya
 * con el permiso correcto en vez de tener que acordarse después.
 */
export interface AccionesRol {
  altaBajaSocios: boolean;
  altaBajaPersonal: boolean;
  gestionRutinas: boolean;
  gestionDietas: boolean;
  gestionUsuarios: boolean;
  /** Consultas globales de negocio (ingresos). El operativo va aparte. */
  verIngresos: boolean;
  cobrarPagos: boolean;
  gestionPromociones: boolean;
  gestionDeudas: boolean;
  gestionTurnos: boolean;
}

export interface PermisosRol {
  secciones: Record<SeccionPrivada, AccesoValue>;
  acciones: AccionesRol;
}

/**
 * Las 6 secciones del portal del socio, apagadas de una. Todo rol de staff
 * las tiene en NINGUNO: "Mi rutina" es la rutina DE UNO, no tiene sentido
 * que la abra un entrenador (para eso tiene /rutinas, que las lista todas).
 * Se arma como constante para no repetir seis líneas idénticas en los
 * cuatro roles de staff y que agregar una séptima vista de socio no obligue
 * a acordarse de apagarla en cada uno.
 */
const SIN_ACCESO_A_PORTAL_SOCIO = {
  [Routes.MI_PERFIL]: Acceso.NINGUNO,
  [Routes.MI_RUTINA]: Acceso.NINGUNO,
  [Routes.MIS_ACTIVIDADES]: Acceso.NINGUNO,
  [Routes.MI_PROGRESO]: Acceso.NINGUNO,
  [Routes.MI_DIETA]: Acceso.NINGUNO,
  [Routes.MI_CUOTA]: Acceso.NINGUNO,
  [Routes.MIS_TURNOS]: Acceso.NINGUNO,
} as const;

/** Espejo del anterior: el socio no entra a NINGUNA pantalla de gestión. */
const SIN_ACCESO_A_ADMIN = {
  [Routes.DASHBOARD]: Acceso.NINGUNO,
  [Routes.SOCIOS]: Acceso.NINGUNO,
  [Routes.PERSONAL]: Acceso.NINGUNO,
  [Routes.RUTINAS]: Acceso.NINGUNO,
  [Routes.NUTRICION]: Acceso.NINGUNO,
  [Routes.USUARIOS]: Acceso.NINGUNO,
  [Routes.ASISTENCIA]: Acceso.NINGUNO,
  [Routes.ACTIVIDADES]: Acceso.NINGUNO,
  [Routes.COBROS]: Acceso.NINGUNO,
} as const;

export const PERMISOS: Record<RolValue, PermisosRol> = {
  // Control total en todo (decisión del usuario por sobre la matriz).
  [Roles.DUENO]: {
    secciones: {
      [Routes.DASHBOARD]: Acceso.TOTAL,
      [Routes.SOCIOS]: Acceso.TOTAL,
      [Routes.PERSONAL]: Acceso.TOTAL,
      [Routes.RUTINAS]: Acceso.TOTAL,
      [Routes.NUTRICION]: Acceso.TOTAL,
      [Routes.USUARIOS]: Acceso.TOTAL,
      [Routes.ASISTENCIA]: Acceso.TOTAL,
      [Routes.ACTIVIDADES]: Acceso.TOTAL,
      [Routes.COBROS]: Acceso.TOTAL,
      ...SIN_ACCESO_A_PORTAL_SOCIO,
    },
    acciones: {
      altaBajaSocios: true,
      altaBajaPersonal: true,
      gestionRutinas: true,
      gestionDietas: true,
      gestionUsuarios: true,
      verIngresos: true,
      cobrarPagos: true,
      gestionPromociones: true,
      gestionDeudas: true,
      gestionTurnos: true,
    },
  },

  // "Puede hacer casi todo lo operativo". Ve Personal pero no puede dar de
  // alta ni de baja a nadie (eso es exclusivo del Dueño) — de ahí que la
  // sección quede en LECTURA. Su Dashboard es "parcial (operativo)": ve las
  // métricas de gestión pero no los ingresos, que son dato de negocio.
  //
  // Gestión de Usuarios, Rutinas y Dietas (2026-08-03, corrección del
  // usuario en dos pasos): en la práctica el Recepcionista es el respaldo
  // operativo de todo el gimnasio, no sólo de las cuentas de acceso — si un
  // Entrenador no puede entrar a su cuenta, es el Recepcionista quien le
  // gestiona la rutina o se la asigna a un socio en su lugar. Por eso tiene
  // control total en Usuarios, Rutinas Y Nutrición, igual que el Dueño. La
  // única excepción real es su propia cuenta de acceso: no puede editarla
  // ni desactivarla (regla de fila, no de sección — ver
  // esCuentaPropiaRestringida más abajo, mismo criterio que "nadie se da de
  // baja a sí mismo" en Personal).
  [Roles.RECEPCIONISTA]: {
    secciones: {
      [Routes.DASHBOARD]: Acceso.TOTAL,
      [Routes.SOCIOS]: Acceso.TOTAL,
      [Routes.PERSONAL]: Acceso.LECTURA,
      [Routes.RUTINAS]: Acceso.TOTAL,
      [Routes.NUTRICION]: Acceso.TOTAL,
      [Routes.USUARIOS]: Acceso.TOTAL,
      [Routes.ASISTENCIA]: Acceso.TOTAL,
      [Routes.ACTIVIDADES]: Acceso.NINGUNO,
      [Routes.COBROS]: Acceso.TOTAL,
      ...SIN_ACCESO_A_PORTAL_SOCIO,
    },
    acciones: {
      altaBajaSocios: true,
      altaBajaPersonal: false,
      gestionRutinas: true,
      gestionDietas: true,
      gestionUsuarios: true,
      verIngresos: false,
      cobrarPagos: true,
      gestionPromociones: false,
      gestionDeudas: false,
      gestionTurnos: true,
    },
  },

  // Gestiona rutinas y nada más. Lee Socios (necesita saber a quién le
  // asigna) y lee Nutrición (pedido explícito del usuario: "puede
  // consultarlas para ver a qué socio le pertenece, pero no puede
  // desligarla ni darle de alta otra").
  [Roles.ENTRENADOR]: {
    secciones: {
      [Routes.DASHBOARD]: Acceso.NINGUNO,
      [Routes.SOCIOS]: Acceso.LECTURA,
      [Routes.PERSONAL]: Acceso.NINGUNO,
      [Routes.RUTINAS]: Acceso.TOTAL,
      [Routes.NUTRICION]: Acceso.LECTURA,
      [Routes.USUARIOS]: Acceso.NINGUNO,
      [Routes.ASISTENCIA]: Acceso.NINGUNO,
      [Routes.ACTIVIDADES]: Acceso.NINGUNO,
      [Routes.COBROS]: Acceso.NINGUNO,
      ...SIN_ACCESO_A_PORTAL_SOCIO,
    },
    acciones: {
      altaBajaSocios: false,
      altaBajaPersonal: false,
      gestionRutinas: true,
      gestionDietas: false,
      gestionUsuarios: false,
      verIngresos: false,
      cobrarPagos: false,
      gestionPromociones: false,
      gestionDeudas: false,
      gestionTurnos: false,
    },
  },

  // Espejo del Entrenador: gestiona dietas, lee rutinas y socios.
  [Roles.NUTRICIONISTA]: {
    secciones: {
      [Routes.DASHBOARD]: Acceso.NINGUNO,
      [Routes.SOCIOS]: Acceso.LECTURA,
      [Routes.PERSONAL]: Acceso.NINGUNO,
      [Routes.RUTINAS]: Acceso.LECTURA,
      [Routes.NUTRICION]: Acceso.TOTAL,
      [Routes.USUARIOS]: Acceso.NINGUNO,
      [Routes.ASISTENCIA]: Acceso.NINGUNO,
      [Routes.ACTIVIDADES]: Acceso.NINGUNO,
      [Routes.COBROS]: Acceso.NINGUNO,
      ...SIN_ACCESO_A_PORTAL_SOCIO,
    },
    acciones: {
      altaBajaSocios: false,
      altaBajaPersonal: false,
      gestionRutinas: false,
      gestionDietas: true,
      gestionUsuarios: false,
      verIngresos: false,
      cobrarPagos: false,
      gestionPromociones: false,
      gestionDeudas: false,
      gestionTurnos: false,
    },
  },

  // El Socio es un CLIENTE, no personal: cero acceso a pantallas de
  // gestión, acceso total a las seis pantallas que son SUYAS.
  //
  // Hasta que existió el portal, este rol tenía TOTAL en Dashboard, Socios,
  // Personal, Rutinas y Nutrición como parche temporal, con todas las
  // acciones en true. En la auditoría del 2026-08-03 se verificó lo que eso
  // significaba en la práctica: un socio —incluso uno DADO DE BAJA— entraba
  // y veía el DNI de todos los demás socios, el legajo del personal, y
  // tenía botones para dar de alta y de baja gente. Eso se termina acá.
  //
  // Las acciones de la matriz quedan TODAS en false a propósito, y no es un
  // olvido: son acciones sobre el gimnasio (dar de baja socios, cobrar,
  // gestionar promociones). Lo que el socio sí puede hacer —editar su
  // contacto, cargar su peso, reservar y cancelar SU turno— no vive en esta
  // lista porque no son permisos sobre terceros: son operaciones sobre su
  // propia ficha, y el permiso para hacerlas es, exactamente, tener acceso
  // a su propia sección. Meterlas en AccionesRol agregaría cuatro flags que
  // serían false para los otros cuatro roles y no aportarían ninguna
  // decisión: la sección ya es la frontera.
  [Roles.SOCIO]: {
    secciones: {
      ...SIN_ACCESO_A_ADMIN,
      [Routes.MI_PERFIL]: Acceso.TOTAL,
      [Routes.MI_RUTINA]: Acceso.TOTAL,
      [Routes.MIS_ACTIVIDADES]: Acceso.TOTAL,
      [Routes.MI_PROGRESO]: Acceso.TOTAL,
      [Routes.MI_DIETA]: Acceso.TOTAL,
      [Routes.MI_CUOTA]: Acceso.TOTAL,
      [Routes.MIS_TURNOS]: Acceso.TOTAL,
    },
    acciones: {
      altaBajaSocios: false,
      altaBajaPersonal: false,
      gestionRutinas: false,
      gestionDietas: false,
      gestionUsuarios: false,
      verIngresos: false,
      cobrarPagos: false,
      gestionPromociones: false,
      gestionDeudas: false,
      gestionTurnos: false,
    },
  },
};

/**
 * Secciones de gestión, en el orden en que se muestran. Es la lista que
 * recorre el panel de permisos de /usuarios: ahí sólo tienen sentido las
 * pantallas de staff, porque el portal del socio no es un permiso que se
 * reparta entre roles (lo tiene el socio y nadie más).
 */
export const SECCIONES_ADMIN: SeccionPrivada[] = [
  Routes.DASHBOARD,
  Routes.SOCIOS,
  Routes.PERSONAL,
  Routes.RUTINAS,
  Routes.NUTRICION,
  Routes.USUARIOS,
  Routes.ASISTENCIA,
  Routes.ACTIVIDADES,
  Routes.COBROS,
];

/** Secciones del portal del socio, en el orden del sidebar. */
export const SECCIONES_SOCIO: SeccionPrivada[] = [
  Routes.MI_PERFIL,
  Routes.MI_RUTINA,
  Routes.MI_PROGRESO,
  Routes.MI_DIETA,
  Routes.MI_CUOTA,
  Routes.MIS_TURNOS,
];

/**
 * Todas las secciones con permiso. La usan el type guard de ruta y
 * accesoASeccion; el panel de permisos usa SECCIONES_ADMIN, que es un
 * subconjunto.
 */
export const SECCIONES_PRIVADAS: SeccionPrivada[] = [
  ...SECCIONES_ADMIN,
  ...SECCIONES_SOCIO,
];

function esSeccionPrivada(route: RouteValue): route is SeccionPrivada {
  return (SECCIONES_PRIVADAS as RouteValue[]).includes(route);
}

const ORDEN_ACCESO: Record<AccesoValue, number> = {
  [Acceso.NINGUNO]: 0,
  [Acceso.LECTURA]: 1,
  [Acceso.TOTAL]: 2,
};

/**
 * Nivel de acceso de un usuario a una sección. `roles` es un array porque
 * así viaja en el store (authStore.roles), aunque hoy siempre traiga uno
 * solo: si alguna vez alguien acumula roles, gana el más permisivo.
 */
export function accesoASeccion(roles: string[], seccion: SeccionPrivada): AccesoValue {
  let maximo: AccesoValue = Acceso.NINGUNO;
  for (const rol of roles) {
    const permisos = PERMISOS[rol as RolValue];
    if (!permisos) continue;
    const acceso = permisos.secciones[seccion];
    if (ORDEN_ACCESO[acceso] > ORDEN_ACCESO[maximo]) maximo = acceso;
  }
  return maximo;
}

/**
 * Única fuente de verdad de qué rutas ve cada rol — la usan el Sidebar
 * (para ocultar el link), ProtectedRoute (para bloquear la URL directa) y
 * el panel de permisos de /usuarios (para mostrarlos). Vive acá y no
 * repetida en los tres lugares para que no puedan divergir.
 */
export function puedeVerRuta(roles: string[], route: RouteValue): boolean {
  if (!esSeccionPrivada(route)) return true; // login/registro son públicas
  return accesoASeccion(roles, route) !== Acceso.NINGUNO;
}

/** True si además de ver la sección puede ejecutar acciones en ella. */
export function puedeGestionarSeccion(roles: string[], seccion: SeccionPrivada): boolean {
  return accesoASeccion(roles, seccion) === Acceso.TOTAL;
}

/** True si alguno de los roles habilita esa acción puntual. */
export function puedeAccion(roles: string[], accion: keyof AccionesRol): boolean {
  return roles.some((rol) => PERMISOS[rol as RolValue]?.acciones[accion] === true);
}

/**
 * Regla de fila del panel de Usuarios: nadie fuera del Dueño puede editar
 * ni dar de baja/reactivar SU PROPIA cuenta desde acá — se banearía o se
 * cambiaría el usuario a sí mismo sin que nadie más lo viera venir. El
 * Dueño queda exento porque es la autoridad última del sistema, no tiene
 * sentido restringirlo a él también.
 *
 * "Resetear contraseña" no pasa por esta regla a propósito: no hay riesgo
 * en resetearse la propia (es, de hecho, lo único que casi cualquier
 * sistema real deja hacer sobre la cuenta propia) — la restricción es
 * específicamente sobre editar y sobre eliminar/desactivar.
 */
export function esCuentaPropiaRestringida(
  rolesActor: string[],
  idUsuarioFila: number,
  idUsuarioActor: number | undefined,
): boolean {
  if (rolesActor.includes(Roles.DUENO)) return false;
  return idUsuarioFila === idUsuarioActor;
}

/**
 * Segunda regla de fila del panel de Usuarios, y la más importante: sólo un
 * Dueño puede operar sobre la cuenta de un Dueño.
 *
 * `gestionUsuarios` estaba en true para el Recepcionista sin ninguna noción
 * de jerarquía, así que la tabla le dibujaba los tres botones sobre la fila
 * del Dueño. El peor de los tres no es "desactivar" (que ya sería dejar al
 * dueño afuera de su propio gimnasio) sino "resetear contraseña": genera una
 * clave temporal y la MUESTRA en pantalla a quien apretó el botón, así que
 * cualquier recepcionista podía reseteársela al Dueño, leer la clave nueva y
 * entrar con control total. Escalación de privilegios completa, sin devtools
 * ni nada raro: tres clicks en la propia UI.
 *
 * A diferencia de esCuentaPropiaRestringida, acá el reseteo SÍ entra en la
 * restricción — es justamente el vector.
 *
 * ⚠️ Recordatorio de siempre: esto oculta botones, no cierra la puerta. El
 * backend tiene que rechazar la misma operación cuando exista.
 */
export function esCuentaDeMayorJerarquia(rolesActor: string[], rolFila: RolValue): boolean {
  if (rolFila !== Roles.DUENO) return false;
  return !rolesActor.includes(Roles.DUENO);
}

// Estados de socio que se muestran al usuario. Son etiquetas derivadas del
// estado de la Membresía (no una columna del esquema): el service las
// calcula y StatusBadge las pinta, así que el literal tiene que ser el
// mismo de los dos lados o el badge cae al color neutro sin avisar.
export const EstadoSocio = {
  ACTIVO: 'Activo',
  POR_VENCER: 'Por vencer',
  VENCIDO: 'Vencido',
  SUSPENDIDO: 'Suspendido',
  SIN_MEMBRESIA: 'Sin membresía',
  DE_BAJA: 'Dado de baja',
} as const;

export type EstadoSocioValue = (typeof EstadoSocio)[keyof typeof EstadoSocio];

// Cuántos días antes del vencimiento una membresía pasa a "Por vencer".
// PROVISIONAL: ningún doc define el umbral, es un default razonable.
export const DIAS_AVISO_VENCIMIENTO = 7;

// Roles de empleado. NO son una columna del esquema: se derivan de en cuál
// de las tablas hijas (Entrenador/Nutricionista/Recepcionista) existe la
// fila. Estos son los rótulos que se muestran, y la clave con la que la
// vista elige ícono y campo específico de cada rol.
//
// estructura_personal.md lista un cuarto rol, "Administrativo", que no tiene
// tabla en db/schema.sql — se omite hasta que exista.
export const RolEmpleado = {
  ENTRENADOR: 'Entrenador',
  NUTRICIONISTA: 'Nutricionista',
  RECEPCIONISTA: 'Recepcionista',
  // Cuarto tipo de empleado (especificacion_definitiva_actividades.md, Fase
  // 4). A diferencia de los otros tres, un Profesor NO tiene rol de sesión:
  // da clases, no inicia sesión en el sistema — por eso no tiene entrada en
  // Roles ni en ROL_SESION_POR_ROL_EMPLEADO (personalService.ts).
  PROFESOR: 'Profesor',
} as const;

export type RolEmpleadoValue = (typeof RolEmpleado)[keyof typeof RolEmpleado];

// Turnos laborales (TURNO_COLORS de estructura_personal.md). En el esquema
// es Recepcionista.turno_laboral, un varchar(20) libre: solo los
// recepcionistas tienen turno asignado.
export const TurnoLaboral = {
  MANANA: 'Mañana',
  TARDE: 'Tarde',
  NOCHE: 'Noche',
} as const;

export type TurnoLaboralValue = (typeof TurnoLaboral)[keyof typeof TurnoLaboral];

// Estado de un empleado. ACTIVO comparte literal con EstadoSocio.ACTIVO a
// propósito: es la misma palabra y el mismo color en el badge.
export const EstadoEmpleado = {
  ACTIVO: 'Activo',
  INACTIVO: 'Inactivo',
} as const;

export type EstadoEmpleadoValue = (typeof EstadoEmpleado)[keyof typeof EstadoEmpleado];

// Niveles de rutina (estructura_rutinas.md: dropdown Principiante/
// Intermedio/Avanzado). Rutina.nivel es un varchar(20) libre en el esquema
// — estos son los tres valores que el formulario deja elegir.
export const NivelRutina = {
  PRINCIPIANTE: 'Principiante',
  INTERMEDIO: 'Intermedio',
  AVANZADO: 'Avanzado',
} as const;

export type NivelRutinaValue = (typeof NivelRutina)[keyof typeof NivelRutina];

// Estado de una rutina. Binario a diferencia de EstadoSocio/EstadoEmpleado
// — Rutina.activo es el único campo de baja que tiene en el esquema, no
// hay fecha_baja ni motivo.
export const EstadoRutina = {
  ACTIVA: 'Activa',
  INACTIVA: 'Inactiva',
} as const;

export type EstadoRutinaValue = (typeof EstadoRutina)[keyof typeof EstadoRutina];

// Tope de socios asignados que se considera "rutina llena" para la barra de
// progreso (estructura_rutinas.md: `min(asignados / 35, 1.0)`). Es un
// literal del doc, no un valor propio inventado — no hay columna de
// capacidad en Rutina, así que se toma tal cual lo definía el .py original.
export const CAPACIDAD_MAXIMA_RUTINA = 35;

// Objetivos de plan nutricional (estructura_nutricion.md: OBJETIVO_CONFIG).
// Dieta.objetivo es un varchar(100) libre en el esquema — estos son los 4
// valores que el dropdown del formulario deja elegir, igual que NivelRutina
// con Rutina.nivel.
export const ObjetivoDieta = {
  MASA_MUSCULAR: 'Masa muscular',
  BAJAR_PESO: 'Bajar peso',
  MANTENIMIENTO: 'Mantenimiento',
  ALTO_RENDIMIENTO: 'Alto rendimiento',
} as const;

export type ObjetivoDietaValue = (typeof ObjetivoDieta)[keyof typeof ObjetivoDieta];

// Mismo criterio binario que EstadoRutina — Dieta.activo es el único campo
// de baja que tiene en el esquema.
export const EstadoDieta = {
  ACTIVA: 'Activa',
  INACTIVA: 'Inactiva',
} as const;

export type EstadoDietaValue = (typeof EstadoDieta)[keyof typeof EstadoDieta];

// Estado de una Inscripcion_Actividad (especificacion_definitiva_
// actividades.md). A diferencia de EstadoRutina/EstadoDieta, acá sí hay
// tres valores — la inscripción vence sola por fecha (REGLA 6) además de
// poder cancelarse a mano. Las claves son los mismos literales que guarda
// el mock (actividadService.InscripcionListada.estado); esto es sólo la
// traducción para mostrar, igual que EstadoSocio con 'Activo'/'Vencido'.
export const EstadoInscripcionActividad = {
  ACTIVA: 'Activa',
  VENCIDA: 'Vencida',
  CANCELADA: 'Cancelada',
} as const;

export type EstadoInscripcionActividadValue =
  (typeof EstadoInscripcionActividad)[keyof typeof EstadoInscripcionActividad];

// Estado de un Pago (Cobros, especificacion_definitiva_actividades.md).
// Mismo criterio que EstadoInscripcionActividad: las claves son el enum
// crudo de Postgres, los valores el label en español para StatusBadge.
export const EstadoPago = {
  CONFIRMADO: 'Confirmado',
  PENDIENTE: 'Pendiente',
  CANCELADO: 'Cancelado',
  REEMBOLSADO: 'Reembolsado',
} as const;

export type EstadoPagoValue = (typeof EstadoPago)[keyof typeof EstadoPago];

// Estado de una cuenta de acceso (Usuario). A diferencia de EstadoSocio/
// EstadoEmpleado/EstadoRutina/EstadoDieta, acá hay tres valores posibles
// porque Usuario tiene dos columnas booleanas independientes: `activo`
// (¿existe la cuenta?) y `bloqueado` (¿se pasó de intentos fallidos de
// login?). Un usuario puede estar activo y bloqueado a la vez — BLOQUEADO
// se prioriza sobre ACTIVO al mostrar el badge porque es el estado que
// necesita acción del staff.
export const EstadoUsuario = {
  ACTIVO: 'Activo',
  INACTIVO: 'Inactivo',
  BLOQUEADO: 'Bloqueado',
} as const;

export type EstadoUsuarioValue = (typeof EstadoUsuario)[keyof typeof EstadoUsuario];

export interface NavItem {
  label: string;
  icon: LucideIcon;
  route: RouteValue;
}

// label/icon NO están en ui.md (solo confirma que build_sidebar itera esta
// lista) — placeholders provisorios, fáciles de ajustar cuando haya
// contenido real. Qué ítems ve cada rol lo decide PERMISOS vía
// puedeVerRuta, no se filtra acá.
export const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', icon: LayoutDashboard, route: Routes.DASHBOARD },
  { label: 'Socios', icon: Users, route: Routes.SOCIOS },
  { label: 'Cobros', icon: Wallet, route: Routes.COBROS },
  { label: 'Asistencia', icon: Fingerprint, route: Routes.ASISTENCIA },
  { label: 'Personal', icon: UserCog, route: Routes.PERSONAL },
  { label: 'Rutinas', icon: Dumbbell, route: Routes.RUTINAS },
  { label: 'Nutrición', icon: Apple, route: Routes.NUTRICION },
  { label: 'Actividades', icon: CalendarCheck, route: Routes.ACTIVIDADES },
  { label: 'Usuarios', icon: ShieldCheck, route: Routes.USUARIOS },
];

/**
 * Navegación del portal del socio. Lista aparte y no un filtro de
 * NAV_ITEMS: no comparten ni una sola entrada, y las etiquetas son en
 * primera persona a propósito ("Mi rutina", no "Rutinas") — es la señal más
 * barata de que lo que está viendo es suyo y de nadie más.
 *
 * El orden sigue el del prompt: primero quién sos, después lo que hacés en
 * el gimnasio (rutina, progreso, dieta), y al final lo administrativo
 * (cuota, turnos).
 */
export const SOCIO_NAV_ITEMS: NavItem[] = [
  { label: 'Mi perfil', icon: UserRound, route: Routes.MI_PERFIL },
  { label: 'Mi rutina', icon: Dumbbell, route: Routes.MI_RUTINA },
  { label: 'Mis actividades', icon: CalendarCheck, route: Routes.MIS_ACTIVIDADES },
  { label: 'Mi progreso', icon: TrendingUp, route: Routes.MI_PROGRESO },
  { label: 'Mi dieta', icon: Apple, route: Routes.MI_DIETA },
  // "Mis turnos" estuvo FUERA de esta lista un tiempo, y conviene dejar
  // asentado por qué volvió.
  //
  // La nota anterior decía que la vista estaba congelada porque el gimnasio
  // iba a pasar a un modelo MIXTO —musculación y cardio de acceso libre, más
  // actividades con horario fijo, cupo y profesional asignado— y no tenía
  // sentido escribir la pantalla antes de que ese modelo existiera. Era
  // correcto.
  //
  // Ese modelo YA EXISTE: Actividad tiene cupo, profesor y tolerancia,
  // Horario_Actividad declara el horario semanal y el backend genera los
  // turnos solo, y la sala abierta se distingue de una clase por su cupo. La
  // precondición está cumplida, así que la vista se escribió y el ítem
  // vuelve.
  //
  // (El motivo por el que no podía quedar en el menú sin la vista sigue
  // valiendo si alguna vez se saca de nuevo: sin ruta registrada en App.tsx
  // caía en el comodín `path="*"` y rebotaba al socio a /mi-perfil, y un link
  // que no lleva a ningún lado se lee como app rota, no como "todavía no
  // está".)
  { label: 'Mis turnos', icon: CalendarClock, route: Routes.MIS_TURNOS },
  { label: 'Mi cuota', icon: CreditCard, route: Routes.MI_CUOTA },
];

/**
 * Los ítems de navegación que le corresponden a un rol. El Socio tiene su
 * propio set completo; todo lo demás es staff y va al de gestión. Vive acá
 * y no en el Sidebar porque rutaInicialPara necesita exactamente la misma
 * decisión: si divergen, el login manda a alguien a una ruta que su sidebar
 * no muestra.
 */
export function navItemsPara(roles: string[]): NavItem[] {
  return roles.includes(Roles.SOCIO) ? SOCIO_NAV_ITEMS : NAV_ITEMS;
}

const TODOS_LOS_NAV_ITEMS = [...NAV_ITEMS, ...SOCIO_NAV_ITEMS];

/** Etiqueta de una sección, para mostrarla en el panel de permisos. */
export function etiquetaSeccion(seccion: SeccionPrivada): string {
  return TODOS_LOS_NAV_ITEMS.find((item) => item.route === seccion)?.label ?? seccion;
}

/**
 * A dónde mandar a alguien recién logueado, o a quien entró por URL a una
 * sección que no puede ver: la primera de SU sidebar que tenga acceso.
 * Antes esto era `/dashboard` fijo, pero un Entrenador no ve el Dashboard
 * (las consultas globales son del Dueño) y lo dejaba en un redirect
 * infinito.
 *
 * Ojo con el detalle de por qué esto recorre navItemsPara y no NAV_ITEMS:
 * el comentario viejo advertía que "va a pasar en cuanto el Socio deje de
 * ver los paneles de administración". Eso es exactamente lo que acaba de
 * pasar. Buscando sólo en NAV_ITEMS, un socio no encontraría ninguna ruta
 * permitida y caería en LOGIN — pero como está autenticado, el guard lo
 * mandaría de vuelta, y de vuelta: pantalla en blanco y el CPU al palo.
 */
export function rutaInicialPara(roles: string[]): RouteValue {
  const primera = navItemsPara(roles).find((item) => puedeVerRuta(roles, item.route));
  // Sin ninguna sección visible sí o sí hay que cortar el ciclo: al login.
  return primera?.route ?? Routes.LOGIN;
}
