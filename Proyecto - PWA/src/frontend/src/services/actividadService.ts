// Actividades con horario: catálogo, compra de planes y clases sueltas,
// reserva y cancelación de turnos, y fichaje de asistencia.
//
// CABLEADO CONTRA LA API REAL. Las ocho reglas de negocio que antes vivían
// acá —cobertura de membresía, cupo, saldo del abono, anticipación de
// cancelación, deudas— ahora las aplica el backend, y este archivo se limita
// a traducir entre el castellano-camelCase que esperan las vistas y el
// snake_case que devuelve la API.
//
// Que las reglas se hayan ido no es una pérdida: mientras vivían acá eran
// UX, porque cualquiera con la consola abierta podía saltárselas llamando al
// endpoint directo. Ahora son la barrera real. Los mensajes de error que ve
// el usuario son los que redacta el backend, así que dicen exactamente lo
// mismo que decían antes.
//
// Los tipos exportados NO cambiaron: las doce vistas que consumen este
// service siguen compilando sin tocarse.

import { pedir } from './api';

// Varias funciones reciben `_idUsuarioActor` y lo IGNORAN. El parámetro
// sobrevive porque las vistas ya lo pasan, pero el backend deriva el actor
// de la sesión del token — que es lo correcto: si viniera del cliente,
// cualquiera podría auditar una acción a nombre de otro. Se deja para no
// tocar doce vistas por un argumento que no cambia nada.

// =========================================================================
// FORMAS QUE DEVUELVE LA API
// =========================================================================
// Se declaran acá y no en types.ts porque son la forma del TRANSPORTE, no
// del dominio: si el backend algún día renombra un campo, el cambio se
// absorbe en este archivo y ninguna vista se entera.

interface PlanActividadApi {
  id_plan_actividad: number;
  id_actividad: number;
  nombre: string;
  tipo_limite: 'POR_SEMANA' | 'POR_MES' | 'CLASE_SUELTA';
  cantidad: number;
  precio: number;
  activo: boolean;
}

interface ActividadApi {
  id_actividad: number;
  nombre: string;
  descripcion?: string | null;
  cupo_default: number;
  horas_anticipacion_cancelacion: number;
  activo: boolean;
  planes: PlanActividadApi[];
}

interface ProfesorApi {
  id_profesor: number;
  nombre: string;
  titulo?: string | null;
  especialidad?: string | null;
}

interface InscripcionApi {
  id_inscripcion: number;
  id_socio: number;
  socio: string;
  id_plan_actividad: number;
  plan: string;
  actividad: string;
  id_actividad: number;
  tipo_limite: 'POR_SEMANA' | 'POR_MES' | 'CLASE_SUELTA';
  cantidad: number;
  precio_pactado: number;
  fecha_inicio: string;
  fecha_vencimiento: string;
  clases_restantes?: number | null;
  estado: 'ACTIVA' | 'VENCIDA' | 'CANCELADA';
}

interface TurnoApi {
  id_turno: number;
  id_actividad: number;
  actividad: string;
  fecha: string;
  hora: string;
  cupo_maximo: number;
  reservados: number;
  lugares_libres: number;
  estado: 'HABILITADO' | 'CANCELADO';
  profesor?: string | null;
  motivo_cancelacion?: string | null;
}

interface ReservaApi {
  id_reserva: number;
  id_turno: number;
  id_socio: number;
  socio: string;
  actividad: string;
  fecha: string;
  hora: string;
  estado: string;
  es_clase_suelta: boolean;
  clases_restantes?: number | null;
}

interface AsistenciaApi {
  id_asistencia: number;
  id_socio: number;
  socio: string;
  numero_socio?: string | null;
  fecha_hora_ingreso: string;
  fecha_hora_egreso?: string | null;
  metodo_registro: 'RFID' | 'MANUAL';
  // Qué número de ingreso del día es para ese socio (1 = el primero). Lo
  // cuenta el backend al responder; no hay columna. Ver AsistenciaView.tsx.
  ingreso_numero?: number | null;
}

interface PuedeComprarApi {
  puede: boolean;
  tiene_deuda: boolean;
  membresia_cubre: boolean;
  vencimiento_membresia?: string | null;
  vencimiento_abono: string;
  motivo?: string | null;
}

// `null` del JSON a `undefined` de TypeScript. Los tipos de este archivo usan
// campos opcionales, y dejar pasar el null obligaría a las vistas a
// distinguir dos formas de "no hay dato".
function opcional<T>(valor: T | null | undefined): T | undefined {
  return valor ?? undefined;
}

// =========================================================================
// CATÁLOGO — lo que ve el socio (sólo lo activo)
// =========================================================================

export interface ActividadListada {
  idActividad: number;
  nombre: string;
  descripcion?: string;
  cupoDefault: number;
  precioClaseSuelta: number;
  horasAnticipacionCancelacion: number;
}

function aActividadListada(a: ActividadApi): ActividadListada {
  return {
    idActividad: a.id_actividad,
    nombre: a.nombre,
    descripcion: opcional(a.descripcion),
    cupoDefault: a.cupo_default,
    // La clase suelta es un plan (tipo_limite CLASE_SUELTA): su precio sale de ahí.
    precioClaseSuelta:
      a.planes.find((p) => p.tipo_limite === 'CLASE_SUELTA')?.precio ?? 0,
    horasAnticipacionCancelacion: a.horas_anticipacion_cancelacion,
  };
}

export async function getActividades(): Promise<ActividadListada[]> {
  const datos = await pedir<ActividadApi[]>('/actividades');
  return datos.filter((a) => a.activo).map(aActividadListada);
}

export interface PlanActividadListado {
  idPlanActividad: number;
  idActividad: number;
  nombre: string;
  tipoLimite: 'POR_SEMANA' | 'POR_MES' | 'CLASE_SUELTA';
  cantidad: number;
  precio: number;
}

function aPlanListado(p: PlanActividadApi): PlanActividadListado {
  return {
    idPlanActividad: p.id_plan_actividad,
    idActividad: p.id_actividad,
    nombre: p.nombre,
    tipoLimite: p.tipo_limite,
    cantidad: p.cantidad,
    precio: p.precio,
  };
}

export async function getPlanesDeActividad(idActividad: number): Promise<PlanActividadListado[]> {
  const datos = await pedir<PlanActividadApi[]>(`/actividades/${idActividad}/planes`);
  return datos.filter((p) => p.activo).map(aPlanListado);
}

// =========================================================================
// ABM DE CATÁLOGO (Dueño)
// =========================================================================
// A diferencia de los listados de arriba, acá NO se filtra por `activo`: el
// Dueño necesita ver una actividad dada de baja para poder reactivarla.
// Nada se borra, sólo se desactiva — mismo patrón de dos caminos que usan
// rutinasService y nutricionService.

export interface ActividadAdmin {
  idActividad: number;
  nombre: string;
  descripcion?: string;
  cupoDefault: number;
  precioClaseSuelta: number;
  horasAnticipacionCancelacion: number;
  activa: boolean;
}

function aActividadAdmin(a: ActividadApi): ActividadAdmin {
  return { ...aActividadListada(a), activa: a.activo };
}

export async function getActividadesAdmin(): Promise<ActividadAdmin[]> {
  const datos = await pedir<ActividadApi[]>('/actividades');
  return datos.map(aActividadAdmin);
}

export interface ActividadInput {
  nombre: string;
  descripcion?: string;
  cupoDefault: number;
  precioClaseSuelta: number;
  horasAnticipacionCancelacion: number;
}

function cuerpoActividad(input: ActividadInput) {
  return {
    nombre: input.nombre,
    descripcion: input.descripcion || null,
    cupo_default: input.cupoDefault,
    horas_anticipacion_cancelacion: input.horasAnticipacionCancelacion,
  };
}

export async function crearActividad(
  input: ActividadInput,
  _idUsuarioActor?: number,
): Promise<ActividadAdmin> {
  const datos = await pedir<ActividadApi>('/actividades', {
    metodo: 'POST',
    cuerpo: cuerpoActividad(input),
  });
  // La clase suelta ya no es una columna: se materializa como un plan
  // CLASE_SUELTA (cantidad 1) con el precio que puso el formulario.
  if (input.precioClaseSuelta > 0) {
    await pedir(`/actividades/${datos.id_actividad}/planes`, {
      metodo: 'POST',
      cuerpo: { nombre: 'Clase suelta', tipo_limite: 'CLASE_SUELTA', cantidad: 1, precio: input.precioClaseSuelta },
    });
  }
  return { ...aActividadAdmin(datos), precioClaseSuelta: input.precioClaseSuelta };
}

export async function actualizarActividad(
  idActividad: number,
  input: ActividadInput,
  _idUsuarioActor?: number,
): Promise<ActividadAdmin> {
  const datos = await pedir<ActividadApi>(`/actividades/${idActividad}`, {
    metodo: 'PUT',
    cuerpo: cuerpoActividad(input),
  });
  // Upsert del plan de clase suelta con el precio del form.
  const suelta = datos.planes.find((pl) => pl.tipo_limite === 'CLASE_SUELTA');
  if (suelta) {
    await pedir(`/actividades/planes/${suelta.id_plan_actividad}`, {
      metodo: 'PUT',
      cuerpo: { nombre: suelta.nombre, tipo_limite: 'CLASE_SUELTA', cantidad: 1, precio: input.precioClaseSuelta },
    });
  } else if (input.precioClaseSuelta > 0) {
    await pedir(`/actividades/${idActividad}/planes`, {
      metodo: 'POST',
      cuerpo: { nombre: 'Clase suelta', tipo_limite: 'CLASE_SUELTA', cantidad: 1, precio: input.precioClaseSuelta },
    });
  }
  return { ...aActividadAdmin(datos), precioClaseSuelta: input.precioClaseSuelta };
}

/**
 * Baja y reactivación mandan el estado DESTINO explícito, no un toggle.
 *
 * Con un toggle, "dar de baja" sobre una pantalla desactualizada —o un doble
 * click— reactivaría lo que se quería desactivar. Diciendo a qué estado se
 * quiere llegar, el resultado no depende de lo que el cliente creía tener.
 */
export async function darDeBajaActividad(
  idActividad: number,
  _idUsuarioActor?: number,
): Promise<ActividadAdmin> {
  const datos = await pedir<ActividadApi>(
    `/actividades/${idActividad}/toggle-estado?activo=false`,
    { metodo: 'POST' },
  );
  return aActividadAdmin(datos);
}

export async function reactivarActividad(
  idActividad: number,
  _idUsuarioActor?: number,
): Promise<ActividadAdmin> {
  const datos = await pedir<ActividadApi>(
    `/actividades/${idActividad}/toggle-estado?activo=true`,
    { metodo: 'POST' },
  );
  return aActividadAdmin(datos);
}

export interface PlanActividadAdmin {
  idPlanActividad: number;
  idActividad: number;
  nombre: string;
  tipoLimite: 'POR_SEMANA' | 'POR_MES' | 'CLASE_SUELTA';
  cantidad: number;
  precio: number;
  activo: boolean;
}

function aPlanAdmin(p: PlanActividadApi): PlanActividadAdmin {
  return { ...aPlanListado(p), activo: p.activo };
}

export async function getPlanesDeActividadAdmin(
  idActividad: number,
): Promise<PlanActividadAdmin[]> {
  const datos = await pedir<PlanActividadApi[]>(`/actividades/${idActividad}/planes`);
  return datos.map(aPlanAdmin);
}

export interface PlanActividadInput {
  nombre: string;
  tipoLimite: 'POR_SEMANA' | 'POR_MES' | 'CLASE_SUELTA';
  cantidad: number;
  precio: number;
}

function cuerpoPlan(input: PlanActividadInput) {
  return {
    nombre: input.nombre,
    tipo_limite: input.tipoLimite,
    cantidad: input.cantidad,
    precio: input.precio,
  };
}

export async function crearPlanActividad(
  idActividad: number,
  input: PlanActividadInput,
  _idUsuarioActor?: number,
): Promise<PlanActividadAdmin> {
  const datos = await pedir<PlanActividadApi>(`/actividades/${idActividad}/planes`, {
    metodo: 'POST',
    cuerpo: cuerpoPlan(input),
  });
  return aPlanAdmin(datos);
}

export async function actualizarPlanActividad(
  idPlanActividad: number,
  input: PlanActividadInput,
  _idUsuarioActor?: number,
): Promise<PlanActividadAdmin> {
  const datos = await pedir<PlanActividadApi>(`/actividades/planes/${idPlanActividad}`, {
    metodo: 'PUT',
    cuerpo: cuerpoPlan(input),
  });
  return aPlanAdmin(datos);
}

export async function darDeBajaPlanActividad(
  idPlanActividad: number,
  _idUsuarioActor?: number,
): Promise<PlanActividadAdmin> {
  const datos = await pedir<PlanActividadApi>(
    `/actividades/planes/${idPlanActividad}/toggle-estado?activo=false`,
    { metodo: 'POST' },
  );
  return aPlanAdmin(datos);
}

export async function reactivarPlanActividad(
  idPlanActividad: number,
  _idUsuarioActor?: number,
): Promise<PlanActividadAdmin> {
  const datos = await pedir<PlanActividadApi>(
    `/actividades/planes/${idPlanActividad}/toggle-estado?activo=true`,
    { metodo: 'POST' },
  );
  return aPlanAdmin(datos);
}

// =========================================================================
// PROFESORES POR ACTIVIDAD
// =========================================================================

export interface ProfesorAsignable {
  idProfesor: number;
  nombre: string;
  especialidad?: string;
  asignado: boolean;
}

/**
 * Todos los profesores del plantel, marcando cuáles dictan esta actividad.
 *
 * Son dos pedidos porque son dos preguntas distintas: quiénes existen y
 * quiénes están asignados. Se lanzan en paralelo con Promise.all — en serie
 * el panel tardaría el doble sin ninguna razón, porque ninguno depende del
 * otro.
 */
export async function getProfesoresDeActividad(
  idActividad: number,
): Promise<ProfesorAsignable[]> {
  const [todos, asignados] = await Promise.all([
    pedir<ProfesorApi[]>('/actividades/profesores'),
    pedir<ProfesorApi[]>(`/actividades/${idActividad}/profesores`),
  ]);

  const idsAsignados = new Set(asignados.map((p) => p.id_profesor));
  return todos.map((p) => ({
    idProfesor: p.id_profesor,
    nombre: p.nombre,
    especialidad: opcional(p.especialidad),
    asignado: idsAsignados.has(p.id_profesor),
  }));
}

export async function asignarProfesorAActividad(
  idActividad: number,
  idProfesor: number,
  _idUsuarioActor?: number,
): Promise<void> {
  await pedir<ProfesorApi>(`/actividades/${idActividad}/profesores/${idProfesor}`, {
    metodo: 'POST',
  });
}

export async function desasignarProfesorDeActividad(
  idActividad: number,
  idProfesor: number,
  _idUsuarioActor?: number,
): Promise<void> {
  await pedir<void>(`/actividades/${idActividad}/profesores/${idProfesor}`, {
    metodo: 'DELETE',
  });
}

// =========================================================================
// INSCRIPCIONES — comprar y cancelar un abono
// =========================================================================

export interface InscripcionListada {
  idInscripcion: number;
  idActividad: number;
  nombreActividad: string;
  nombrePlan: string;
  tipoLimite: 'POR_SEMANA' | 'POR_MES' | 'CLASE_SUELTA';
  cantidad: number;
  /** Sólo tiene valor con tipoLimite POR_MES. */
  clasesRestantes?: number;
  precioPactado: number;
  fechaInicio: string;
  fechaVencimiento: string;
  estado: 'ACTIVA' | 'VENCIDA' | 'CANCELADA';
}

function aInscripcionListada(i: InscripcionApi): InscripcionListada {
  return {
    idInscripcion: i.id_inscripcion,
    idActividad: i.id_actividad,
    nombreActividad: i.actividad,
    nombrePlan: i.plan,
    tipoLimite: i.tipo_limite,
    cantidad: i.cantidad,
    clasesRestantes: opcional(i.clases_restantes),
    precioPactado: i.precio_pactado,
    fechaInicio: i.fecha_inicio,
    fechaVencimiento: i.fecha_vencimiento,
    estado: i.estado,
  };
}

export async function getMisInscripciones(idSocio: number): Promise<InscripcionListada[]> {
  const datos = await pedir<InscripcionApi[]>(`/actividades/inscripciones/socio/${idSocio}`);
  return datos.map(aInscripcionListada);
}

/**
 * Compra un abono. El backend aplica las tres reglas que antes vivían acá:
 * exige cuota al día, exige que la membresía cubra el mes entero del abono, y
 * rechaza si hay deuda pendiente. El precio sale del plan, no de este pedido.
 *
 * `metodo` mantiene su default para no romper a quien ya llamaba sin él.
 */
export async function comprarPlan(
  idSocio: number,
  idPlanActividad: number,
  _idUsuarioActor?: number,
  metodo: 'EFECTIVO' | 'DEBITO' | 'CREDITO' | 'TRANSFERENCIA' | 'BILLETERA_VIRTUAL' = 'TRANSFERENCIA',
): Promise<InscripcionListada> {
  const datos = await pedir<{ inscripcion: InscripcionApi }>(
    `/actividades/planes/${idPlanActividad}/comprar`,
    { metodo: 'POST', cuerpo: { id_socio: idSocio, metodo } },
  );
  return aInscripcionListada(datos.inscripcion);
}

export async function cancelarInscripcion(
  _idSocio: number,
  idInscripcion: number,
  _idUsuarioActor?: number,
): Promise<void> {
  await pedir<InscripcionApi>(`/actividades/inscripciones/${idInscripcion}/cancelar`, {
    metodo: 'POST',
  });
}

/**
 * Si comprar un abono HOY pasaría la regla de cobertura, sin comprar nada.
 *
 * La usa Cobros para decidir ANTES de cobrar si ofrecer el combo "renovar
 * membresía + comprar abono" en una sola confirmación. Sin esto, el flujo
 * cobraba la cuota y recién después descubría que el abono no entraba, con
 * la plata ya cobrada.
 *
 * El backend responde con el mismo criterio que aplica en la compra real, así
 * que el chequeo previo no puede desincronizarse de lo que va a pasar.
 */
export async function membresiaCubreNuevoPlan(idSocio: number): Promise<boolean> {
  const datos = await pedir<PuedeComprarApi>(`/actividades/socio/${idSocio}/puede-comprar`);
  return datos.puede;
}

// =========================================================================
// TURNOS Y RESERVAS
// =========================================================================

export interface TurnoDisponible {
  idTurno: number;
  idActividad: number;
  nombreActividad: string;
  fecha: string;
  hora: string;
  cupoMaximo: number;
  cupoDisponible: number;
  nombreProfesional?: string;
}

/**
 * Turnos habilitados de la grilla.
 *
 * Ya no recibe `idSede`: el sistema opera una sola sede y el backend devuelve
 * todos los turnos. Se sacó el parámetro en vez de dejarlo ignorado porque
 * obligaba a las vistas a pedir la sede a la API solo para pasar un número
 * que se descartaba — un viaje de red entero para nada.
 */
export async function getTurnosDisponibles(
  idActividad?: number,
  fecha?: string,
): Promise<TurnoDisponible[]> {
  const parametros = new URLSearchParams();
  if (fecha) {
    // Un solo día: desde y hasta iguales.
    parametros.set('desde', fecha);
    parametros.set('hasta', fecha);
  }
  const consulta = parametros.toString();
  const datos = await pedir<TurnoApi[]>(`/actividades/turnos${consulta ? `?${consulta}` : ''}`);

  return datos
    .filter((t) => t.estado === 'HABILITADO')
    .filter((t) => idActividad === undefined || t.id_actividad === idActividad)
    .map((t) => ({
      idTurno: t.id_turno,
      idActividad: t.id_actividad,
      nombreActividad: t.actividad,
      fecha: t.fecha,
      hora: t.hora,
      cupoMaximo: t.cupo_maximo,
      cupoDisponible: t.lugares_libres,
      nombreProfesional: opcional(t.profesor),
    }));
}

export interface ReservaConfirmada {
  idReserva: number;
  idTurno: number;
  fecha: string;
  hora: string;
  nombreActividad: string;
}

function aReservaConfirmada(r: ReservaApi): ReservaConfirmada {
  return {
    idReserva: r.id_reserva,
    idTurno: r.id_turno,
    fecha: r.fecha,
    hora: r.hora,
    nombreActividad: r.actividad,
  };
}

/**
 * Reserva usando un abono ya comprado. El backend verifica el cupo y el saldo
 * de clases.
 *
 * NO pasa por la regla de deudas, y eso es deliberado: usar un abono que ya
 * está pagado no es una compra.
 */
export async function reservarTurno(
  idSocio: number,
  idTurno: number,
): Promise<ReservaConfirmada> {
  const datos = await pedir<ReservaApi>(`/actividades/turnos/${idTurno}/reservar`, {
    metodo: 'POST',
    cuerpo: { id_socio: idSocio, es_clase_suelta: false },
  });
  return aReservaConfirmada(datos);
}

/**
 * Compra y reserva una clase individual, sin abono previo. Compite por el
 * MISMO cupo que las reservas con plan.
 */
export async function comprarClaseSuelta(
  idSocio: number,
  idTurno: number,
  _idUsuarioActor?: number,
  metodo: 'EFECTIVO' | 'DEBITO' | 'CREDITO' | 'TRANSFERENCIA' | 'BILLETERA_VIRTUAL' = 'TRANSFERENCIA',
): Promise<ReservaConfirmada> {
  const datos = await pedir<{ reserva: ReservaApi }>(
    `/actividades/turnos/${idTurno}/clase-suelta`,
    { metodo: 'POST', cuerpo: { id_socio: idSocio, metodo } },
  );
  return aReservaConfirmada(datos.reserva);
}

/**
 * Cancela una reserva. El cupo se libera siempre; que se devuelva o no la
 * clase al abono depende de la anticipación que exija la actividad, y eso lo
 * decide el backend con la hora del servidor — no la del navegador, que se
 * puede cambiar.
 */
export async function cancelarReserva(
  _idSocio: number,
  idReserva: number,
  _idUsuarioActor?: number,
): Promise<void> {
  await pedir<ReservaApi>(`/actividades/reservas/${idReserva}/cancelar`, { metodo: 'POST' });
}

// =========================================================================
// ASISTENCIA — panel de recepción
// =========================================================================

export interface AsistenciaRegistrada {
  idAsistencia: number;
  nombreSocio: string;
  fechaHoraIngreso: string;
  metodoRegistro: 'RFID' | 'MANUAL';
  /** 1 = el primer ingreso del día de ese socio; 2, 3… los repetidos. */
  ingresoNumero: number | null;
}

function aAsistenciaRegistrada(a: AsistenciaApi): AsistenciaRegistrada {
  return {
    idAsistencia: a.id_asistencia,
    nombreSocio: a.socio,
    fechaHoraIngreso: a.fecha_hora_ingreso,
    metodoRegistro: a.metodo_registro,
    ingresoNumero: a.ingreso_numero ?? null,
  };
}

/** Fichajes del día, el más reciente primero. */
export async function getAsistenciasDeHoy(): Promise<AsistenciaRegistrada[]> {
  const datos = await pedir<AsistenciaApi[]>('/asistencia/hoy');
  return datos.map(aAsistenciaRegistrada);
}

/**
 * Registra un ingreso.
 *
 * Es la ÚNICA forma de fichar: el fichaje por tarjeta se retiró de las dos
 * apps (ver el encabezado de AsistenciaView.tsx). El backend todavía acepta
 * `codigo_rfid`, pero ninguna pantalla lo manda.
 *
 * Ojo: el backend registra el ingreso AUNQUE el socio tenga deuda o la cuota
 * vencida, y devuelve una advertencia. Es una decisión de negocio — dejar a
 * alguien afuera lo decide una persona en el mostrador, no un torniquete — y
 * además, si no se registrara, el gimnasio perdería el dato de que esa
 * persona estuvo.
 *
 * Tampoco rechaza el ingreso repetido: no hay tope diario ni anti-duplicado.
 * El repetido se registra igual y vuelve con `ingresoNumero` en 2, 3… para que
 * la pantalla lo marque al lado del nombre. Ver el comentario de
 * routers/asistencia.py.
 */
export async function registrarAsistenciaManual(
  idSocio: number,
  _idUsuarioActor?: number,
): Promise<AsistenciaRegistrada> {
  const datos = await pedir<{ asistencia: AsistenciaApi }>('/asistencia/fichar', {
    metodo: 'POST',
    cuerpo: { id_socio: idSocio },
  });
  return aAsistenciaRegistrada(datos.asistencia);
}

/**
 * Borra un ingreso mal cargado ("desfichar").
 *
 * El backend sólo deja borrar los de HOY: corregir el error del momento es
 * trabajo de mostrador, reescribir la asistencia de la semana pasada no.
 */
export async function deshacerFichaje(idAsistencia: number): Promise<void> {
  await pedir<void>(`/asistencia/${idAsistencia}`, { metodo: 'DELETE' });
}
