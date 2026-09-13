// Tipos derivados del esquema real (v4, Postgres).
// Se van agregando a medida que se implementa cada spec — no declarar
// las 33 tablas de una, solo las que la spec en curso necesita.

// --- auth.spec.md ---

export interface Persona {
  id_persona: number;
  dni: string; // varchar(20), unique, not null
  apellido: string; // varchar(100), not null
  nombre: string; // varchar(100), not null
  sexo?: string; // varchar(20)
  email?: string; // varchar(150), unique
  calle?: string;
  numero_calle?: string;
  localidad?: string;
  fecha_nacimiento?: string; // date
  url_foto?: string;
  emergencia_nombre?: string;
  emergencia_telefono?: string;
  emergencia_parentesco?: string;
  fecha_alta: string; // timestamp, default now()
  activo: boolean; // default true
}

export interface Usuario {
  id_usuario: number;
  id_persona: number; // FK -> Persona, unique, not null
  username: string; // varchar(50), unique, not null
  // NUNCA debería viajar en una respuesta del backend al frontend.
  password_hash: string;
  ultimo_acceso?: string; // timestamp
  intentos_fallidos: number; // default 0
  bloqueado: boolean; // default false
  activo: boolean; // default true
}

export interface Telefono {
  id_telefono: number;
  id_persona: number; // FK -> Persona
  numero: string; // varchar(30), not null
  tipo: 'CELULAR' | 'FIJO'; // default CELULAR
  principal: boolean; // default false
}

export interface Socio {
  id_socio: number;
  id_persona: number; // FK -> Persona, unique, not null
  id_sede: number; // FK -> Sede, not null
  // NO hay `id_entrenador_a_cargo`. La tenia, y la migracion 003 la saco:
  // era un campo de valor unico para un hecho que en la realidad es
  // MULTIPLE (uno de musculacion y otro de funcional a la vez) y
  // CAMBIANTE (reasignar pisaba el anterior y se perdia el historial).
  // Hoy vive en Asignacion_Entrenador; se lee con listarEntrenadoresDeSocio
  // de sociosService. Mismo comentario que models.py del backend.
  numero_socio?: string; // varchar(20), unique
  codigo_rfid?: string; // varchar(50), unique — nullable: no todo gimnasio usa RFID (ver Asistencia.metodo_registro)
  fecha_alta: string; // date, not null
  objetivo?: string;
  observaciones?: string;
  activo: boolean; // default true
}

export interface Baja {
  id_baja: number;
  id_socio: number; // FK -> Socio, not null
  fecha_baja: string; // date, not null
  tipo?: 'VOLUNTARIA' | 'MORA' | 'ADMINISTRATIVA';
  motivo?: string;
  id_registrado_por?: number; // FK -> Usuario
}

export interface Auditoria {
  id_auditoria: number;
  id_usuario?: number; // FK -> Usuario
  entidad: string; // varchar(50), not null
  id_entidad?: number;
  accion: 'ALTA' | 'MODIFICACION' | 'BAJA' | 'CONSULTA' | 'LOGIN';
  fecha: string; // timestamp, default now()
  detalle?: string;
  ip?: string;
}

// --- personal (Empleado + subtipos) ---
//
// Ojo: el esquema NO tiene una columna `rol` en Empleado. El rol se deriva
// de en cuál de las tres tablas hijas (Entrenador / Nutricionista /
// Recepcionista) existe una fila para ese empleado — cada una 1:1 con
// Empleado y con sus propios campos. Por eso el service calcula el rol en
// vez de leerlo, y por eso `turno_laboral` solo existe en Recepcionista.

export interface Empleado {
  id_empleado: number;
  id_persona: number; // FK -> Persona, not null
  id_sede: number; // FK -> Sede, not null
  legajo?: string; // varchar(20)
  fecha_ingreso: string; // date, not null
  fecha_egreso?: string; // date
  activo: boolean; // default true
}

export interface Entrenador {
  id_entrenador: number;
  id_empleado: number; // FK -> Empleado, not null
  titulo?: string; // varchar(100)
  especialidad?: string; // varchar(100)
  matricula?: string; // varchar(50)
}

export interface Nutricionista {
  id_nutricionista: number;
  id_empleado: number; // FK -> Empleado, not null
  titulo?: string; // varchar(100)
  matricula?: string; // varchar(50)
}

export interface Recepcionista {
  id_recepcionista: number;
  id_empleado: number; // FK -> Empleado, not null
  id_franja_laboral?: number; // FK -> Franja_Laboral (antes: turno_laboral varchar)
}

export interface FranjaLaboral {
  id_franja_laboral: number;
  nombre: string;
  hora_desde?: string;
  hora_hasta?: string;
  activo: boolean;
}

// --- rutinas (Rutina + Asignacion_Rutina) ---
//
// Ojo: Rutina NO tiene columna `duracion` ni `descripcion` — estructura_
// rutinas.md pide esos dos campos, pero en el esquema real lo único de
// texto libre es `objetivo`. rutinasService.ts usa objetivo para las dos
// cosas (pill de la tarjeta y campo del formulario) en vez de inventar
// columnas que no existen. Ver comentario largo en rutinasService.ts.

export interface Rutina {
  id_rutina: number;
  id_entrenador: number; // FK -> Entrenador, not null
  nombre: string; // varchar(100), not null
  objetivo?: string; // varchar(100)
  nivel?: string; // varchar(20)
  dias_por_semana?: number;
  fecha_creacion: string; // date, default now()
  activo: boolean; // default true
}

export interface AsignacionRutina {
  id_asignacion_rutina: number;
  id_socio: number; // FK -> Socio, not null
  id_rutina: number; // FK -> Rutina, not null
  id_entrenador?: number; // FK -> Entrenador
  fecha_inicio: string; // date, not null
  fecha_fin?: string; // date
  estado: 'ACTIVA' | 'FINALIZADA' | 'CANCELADA'; // default ACTIVA
}

// --- nutrición (Dieta + Comida + Asignacion_Dieta) ---
//
// A diferencia de Rutina, Dieta sí tiene `descripcion` como columna propia
// (text) además de `objetivo` — no hace falta la gimnasia de reusar un
// campo para dos cosas. Lo que NO existe en ningún lado del esquema son
// columnas de macros (proteínas/carbohidratos/grasas); el 30/50/20 fijo que
// describe estructura_nutricion.md no tiene respaldo real, así que no se
// replica — ver el comentario grande en nutricionService.ts.

export interface Dieta {
  id_dieta: number;
  id_nutricionista: number; // FK -> Nutricionista, not null
  nombre: string; // varchar(100), not null
  objetivo?: string; // varchar(100)
  calorias_diarias?: number;
  descripcion?: string;
  fecha_creacion: string; // date, default now()
  activo: boolean; // default true
}

/** Catálogo de platos: el nombre y las calorías dependen del PLATO, no de la dieta. */
export interface CatalogoComida {
  id_catalogo_comida: number;
  nombre: string;
  descripcion?: string;
  calorias?: number;
  activo: boolean;
}

export interface Comida {
  id_comida: number;
  id_dieta: number; // FK -> Dieta, not null
  dia?: number;
  momento?: string; // varchar(30), p. ej. "Desayuno"
  // El plato SIEMPRE sale de Catalogo_Comida (id_catalogo_comida obligatorio).
  // nombre/descripcion/calorias vienen del catálogo, no de la fila Comida.
  id_catalogo_comida: number;
  nombre?: string;
  descripcion?: string;
  calorias?: number;
}

export interface AsignacionDieta {
  id_asignacion_dieta: number;
  id_socio: number; // FK -> Socio, not null
  id_dieta: number; // FK -> Dieta, not null
  id_nutricionista?: number; // FK -> Nutricionista
  fecha_inicio: string; // date, not null
  fecha_fin?: string; // date
  estado: 'ACTIVA' | 'FINALIZADA' | 'CANCELADA'; // default ACTIVA
  observaciones?: string;
}

// --- dashboard (Membresia / Pago / Turno) ---

export interface TipoMembresia {
  id_tipo_membresia: number;
  nombre: string; // varchar(50), not null
  descripcion?: string;
  duracion_dias: number; // not null
  precio_actual: number; // numeric(10,2), not null
  activo: boolean; // default true
}

export interface Membresia {
  id_membresia: number;
  id_socio: number; // FK -> Socio, not null
  id_tipo_membresia: number; // FK -> Tipo_Membresia, not null
  id_promocion?: number; // FK -> Promocion
  precio_pactado: number; // numeric(10,2), not null
  fecha_inicio: string; // date, not null
  // Nullable desde la extensión de actividades: sin vencimiento = cubre
  // siempre. Antes era NOT NULL — ver REGLA 1 (cobertura) en actividadService.ts,
  // que depende de este campo para decidir si una Inscripcion_Actividad es válida.
  fecha_vencimiento?: string; // date
  estado: 'ACTIVA' | 'VENCIDA' | 'SUSPENDIDA' | 'CANCELADA'; // default ACTIVA
}

export interface Pago {
  id_pago: number;
  id_socio: number; // FK -> Socio, not null
  id_membresia?: number; // FK -> Membresia
  // Agregado en la extensión de actividades: a qué Inscripcion_Actividad
  // corresponde este pago, si es que es de un plan y no de una membresía.
  // Mutuamente excluyente con id_membresia en la práctica, aunque el
  // esquema no tiene un CHECK que lo obligue.
  id_inscripcion?: number; // FK -> Inscripcion_Actividad
  id_sede?: number; // FK -> Sede
  metodo: 'EFECTIVO' | 'DEBITO' | 'CREDITO' | 'TRANSFERENCIA' | 'BILLETERA_VIRTUAL'; // not null
  monto: number; // numeric(10,2), not null
  fecha_pago: string; // timestamp, default now(), not null
  periodo_desde?: string; // date
  periodo_hasta?: string; // date
  es_adelanto: boolean; // default false
  estado: 'CONFIRMADO' | 'PENDIENTE' | 'CANCELADO' | 'REEMBOLSADO'; // default CONFIRMADO
  fecha_cancelacion?: string; // timestamp
  numero_comprobante?: string; // varchar(50)
  id_registrado_por?: number; // FK -> Usuario
}

/**
 * Un turno es una actividad con horario, en una fecha y sede — musculación
 * incluida, que también es una fila de Actividad (acceso libre: sus turnos
 * quedan con id_profesor en NULL). id_entrenador_a_cargo es para
 * musculación/rutinas; id_profesor para el resto (yoga, boxeo, etc.).
 * `hora` es SOLO de llegada, no hay hora de fin.
 */
export interface Turno {
  id_turno: number;
  id_sede: number; // FK -> Sede, not null
  id_actividad: number; // FK -> Actividad, not null
  fecha: string; // date, not null
  hora: string; // time, not null
  cupo_maximo: number; // not null
  estado: 'HABILITADO' | 'CANCELADO'; // default HABILITADO
  id_entrenador_a_cargo?: number; // FK -> Entrenador
  id_profesor?: number; // FK -> Profesor
  motivo_cancelacion?: string; // varchar(200)
  observaciones?: string; // varchar(200)
}

// --- portal del socio ---
//
// A diferencia de rutinas y nutrición —donde los docs pedían campos que el
// esquema no tenía (duración, macros) y hubo que resolver el hueco—, acá
// las seis vistas del portal caen sobre tablas que existen tal cual. No se
// inventa ninguna columna.

/**
 * Historial de peso y composición corporal. Es 1:N con unique
 * (id_socio, fecha): el socio no puede tener dos mediciones el mismo día,
 * pero se conserva toda la progresión — el esquema es explícito en que
 * borrar la fila anterior al cargar una nueva sería una anomalía de
 * borrado. "Peso actual" no es una columna: es la fila de fecha más alta.
 */
export interface RegistroSalud {
  id_registro_salud: number;
  id_socio: number; // FK -> Socio, not null
  fecha: string; // date, not null
  peso?: number; // numeric(5,2)
  altura?: number; // numeric(3,2)
  grasa_corporal?: number; // numeric(4,2)
  masa_muscular?: number; // numeric(5,2)
  observaciones?: string;
  id_registrado_por?: number; // FK -> Usuario
}

/**
 * Reserva de un Turno. El unique de Reserva es (id_turno, id_socio): no se
 * puede reservar dos veces el MISMO turno (misma actividad+fecha+hora). Eso
 * no impide reservar Yoga a las 9 y Boxeo a las 20 el mismo día: son dos
 * Turno distintos, así que son dos Reserva distintas sin conflicto.
 *
 * `id_inscripcion` y `es_clase_suelta` son mutuamente excluyentes en la
 * práctica (no hay CHECK en el esquema, pero la regla de negocio es esa):
 * o la reserva sale de un plan comprado, o se pagó suelta.
 */
export interface Reserva {
  id_reserva: number;
  id_turno: number; // FK -> Turno, not null
  id_socio: number; // FK -> Socio, not null
  id_inscripcion?: number; // FK -> Inscripcion_Actividad — con qué plan se reservó; sin valor si es clase suelta
  es_clase_suelta: boolean; // default false
  id_pago?: number; // FK -> Pago — el pago de la clase suelta; sin valor si vino de un plan
  fecha_reserva: string; // timestamp, default now()
  /** CANCELADA_SOCIO y CANCELADA_GIMNASIO son estados distintos: importa quién canceló. */
  estado: 'RESERVADA' | 'CANCELADA_SOCIO' | 'CANCELADA_GIMNASIO';
  fecha_cancelacion?: string; // timestamp
  id_cancelado_por?: number; // FK -> Usuario
}

/**
 * Ingreso al gimnasio. 1:N con Reserva y SIN unique: el socio puede entrar
 * y salir varias veces el mismo día. id_reserva es nullable porque se
 * admite el ingreso sin reserva previa — de ahí que id_sede viva acá y no
 * se derive de la Reserva.
 */
export interface Asistencia {
  id_asistencia: number;
  id_socio: number; // FK -> Socio, not null
  id_sede: number; // FK -> Sede, not null
  id_reserva?: number; // FK -> Reserva, nullable (ingreso libre)
  fecha_hora_ingreso: string; // timestamp, not null
  fecha_hora_egreso?: string; // timestamp
  metodo_registro: 'RFID' | 'MANUAL'; // default MANUAL
  id_registrado_por?: number; // FK -> Usuario, quién lo cargó si fue MANUAL
}

/**
 * Deuda de un socio. En el sistema real las genera un job diario que busca
 * membresías vencidas sin pago que las cubra; acá vienen del seed. El socio
 * las CONSULTA nada más: cobrar es de recepción (DFD 2.3).
 */
export interface Deuda {
  id_deuda: number;
  id_socio: number; // FK -> Socio, not null
  id_membresia?: number; // FK -> Membresia
  monto: number; // numeric(10,2), not null
  fecha_generacion: string; // date, not null
  fecha_vencimiento?: string; // date
  estado: 'PENDIENTE' | 'PAGADA' | 'CONDONADA';
  generada_automaticamente: boolean; // default true
  id_pago_cancelatorio?: number; // FK -> Pago
  observaciones?: string;
}

/** Catálogo de ejercicios. grupo_muscular vive acá y no en Rutina_Ejercicio (3FN). */
export interface Ejercicio {
  id_ejercicio: number;
  nombre: string; // varchar(100), not null
  grupo_muscular: string; // varchar(50), not null
  descripcion?: string;
  url_video?: string;
  requiere_maquina: boolean; // default false
}

/**
 * Un ejercicio dentro de una rutina, en un día y una posición. `dia` y
 * `orden` son NOT NULL: la rutina se lee ordenada por (id_rutina, dia,
 * orden), que es justo el índice que tiene el esquema.
 *
 * `repeticiones` es varchar(20) y no un número a propósito: en el gimnasio
 * se escribe "10-12", "al fallo" o "30 seg", no siempre un entero.
 */
export interface RutinaEjercicio {
  id_rutina_ejercicio: number;
  id_rutina: number; // FK -> Rutina, not null
  id_ejercicio: number; // FK -> Ejercicio, not null
  dia: number; // not null
  orden: number; // not null
  series?: number;
  repeticiones?: string; // varchar(20)
  peso_sugerido?: number; // numeric(6,2)
  descanso_segundos?: number;
  observaciones?: string;
}

// --- actividades (especificacion_definitiva_actividades.md) ---
//
// Extiende el acceso libre de siempre a actividades con horario fijo (yoga,
// boxeo, masajes, etc.) sin tocar cómo funciona hoy la musculación: es una
// fila más de Actividad, sigue siendo de acceso libre (sus Turno quedan con
// id_profesor en NULL, ver Turno más arriba).

/**
 * Subtipo de Empleado, DISTINTO de Entrenador: Entrenador da rutinas de
 * musculación, Profesor dicta el resto de las actividades. Una persona
 * puede tener las dos filas si cumple los dos roles.
 */
export interface Profesor {
  id_profesor: number;
  id_empleado: number; // FK -> Empleado, unique, not null
  titulo?: string; // varchar(100)
  especialidad?: string; // varchar(100)
}

/** Catálogo de lo que se puede reservar en un Turno. Musculación es una fila más acá, no un caso aparte. */
export interface Actividad {
  id_actividad: number;
  nombre: string; // varchar(80), unique, not null
  descripcion?: string;
  cupo_default: number; // not null — valor de referencia; el Turno puede sobrescribirlo en su propio cupo_maximo
  // La clase suelta ya NO es una columna de Actividad: es un Plan_Actividad con
  // tipo_limite = CLASE_SUELTA. Su precio sale de ese plan.
  /** Con cuánta anticipación se puede cancelar sin perder la clase. 0 = nunca. */
  horas_anticipacion_cancelacion: number; // not null, default 0
  activo: boolean; // default true
}

/**
 * Formato de pago de una Actividad (ej. "2x semana" o "12 clases/mes").
 * tipo_limite = POR_SEMANA -> cantidad = veces por semana.
 * tipo_limite = POR_MES -> cantidad = clases totales del mes.
 */
export interface PlanActividad {
  id_plan_actividad: number;
  id_actividad: number; // FK -> Actividad, not null
  nombre: string; // varchar(80), not null
  tipo_limite: 'POR_SEMANA' | 'POR_MES' | 'CLASE_SUELTA';
  cantidad: number; // not null
  precio: number; // numeric(10,2), not null
  activo: boolean; // default true
}

/**
 * Lo que un socio compró de un Plan_Actividad. `id_membresia` ata la
 * inscripción a la membresía que la cubre: no puede vencer después que la
 * membresía (se valida al comprar, ver REGLA 1 en actividadService.ts).
 * `clases_restantes` sólo se usa si el plan es POR_MES; en POR_SEMANA el
 * consumo se cuenta dinámicamente sobre Reserva, no hay contador guardado.
 */
export interface InscripcionActividad {
  id_inscripcion: number;
  id_socio: number; // FK -> Socio, not null
  id_plan_actividad: number; // FK -> Plan_Actividad, not null
  precio_pactado: number; // numeric(10,2), not null — congelado al comprar, igual que en Membresia
  fecha_inicio: string; // date, not null
  fecha_vencimiento: string; // date, not null
  clases_restantes?: number; // sólo tiene sentido con tipo_limite = POR_MES
  estado: 'ACTIVA' | 'VENCIDA' | 'CANCELADA'; // default ACTIVA
}

/** N:M: qué actividades puede dictar cada profesor. */
export interface ProfesorActividad {
  id_profesor: number; // FK -> Profesor
  id_actividad: number; // FK -> Actividad
}

export interface Sede {
  id_sede: number;
  id_dueno: number; // FK -> Dueno, not null
  nombre: string; // varchar(100), not null
  calle?: string;
  numero_calle?: string;
  localidad?: string;
  telefono?: string;
  capacidad_maxima?: number;
  hora_apertura?: string; // time
  hora_cierre?: string; // time
  abierto_24hs: boolean; // default true
  activo: boolean; // default true
}
