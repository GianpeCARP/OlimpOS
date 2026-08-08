// Actividades con horario (especificacion_definitiva_actividades.md, Fase
// 3): catálogo, compra de planes/clases sueltas, reserva y cancelación de
// turnos, y fichaje de asistencia.
//
// Domain-scoped, no actor-scoped: a diferencia de socioService.ts (todo lo
// que un socio ve de sí mismo), acá viven juntas las lecturas de catálogo
// (compartidas por todos los roles) y las acciones del socio sobre ese
// catálogo — mismo criterio que ya usan rutinasService.ts/nutricionService.ts,
// que tampoco son puramente "de admin" ni puramente "de socio". Las
// funciones que sí reciben idSocio devuelven únicamente datos de ESE socio,
// igual regla que en socioService.ts.
//
// Las 8 reglas de negocio del documento están acá, no en los componentes —
// están LEÍDAS y escritas con las convenciones de este proyecto (ServiceError
// compartido, no una clase de error propia; los helpers de fecha ya
// existentes; el patrón "Listado" que ya usan todos los demás services para
// no exponer los tipos crudos de la base a las vistas), no copiadas del
// pseudocódigo del documento.

import type { Actividad, InscripcionActividad, Membresia, Pago, PlanActividad, Turno } from '../types';
import { ServiceError, delay } from './api';
import { registrarAuditoria } from './auditoriaService';
import { membresiaVigente } from './membresiaService';
import { nombrePorEmpleado } from './personalService';
import { nombreCompleto } from '../utils/personas';
import {
  aFechaISO,
  aTimestampISO,
  diasEntre,
  horasEntre,
  parsearFecha,
  semanaCalendario,
  sumarMeses,
} from '../utils/fechas';
import { formatearFechaConAnio } from '../utils/format';
import { limpiar } from './validacion';
import {
  actividades,
  planesActividad,
  profesores,
  profesorActividad,
  empleados,
  entrenadores,
  inscripcionesActividad,
  reservas,
  turnos,
  asistencias,
  socios,
  personas,
  deudas,
  pagos,
  sedes,
  siguienteId,
} from './mockDb';

// --- Helpers internos ---

function resolverSocio(idSocio: number) {
  const socio = socios.find((s) => s.id_socio === idSocio);
  if (!socio) throw new ServiceError(404, 'El socio no existe');
  return socio;
}

function sedeActiva() {
  const sede = sedes.find((s) => s.activo);
  if (!sede) throw new ServiceError(500, 'No hay ninguna sede activa configurada');
  return sede;
}

/**
 * REGLA 8 (deudas): corta cualquier COMPRA nueva si el socio tiene una
 * deuda pendiente — comprar un plan o una clase suelta pasan por acá.
 *
 * A propósito NO se llama desde `reservarTurno`: reservar con un plan que
 * ya está pagado es USAR algo que ya se pagó, no comprar. Tampoco se llama
 * nunca desde una función que pague una deuda (no existe todavía, pero
 * cuando exista tiene que quedar afuera de este chequeo) — si pagar
 * dependiera de no tener deuda, nadie podría regularizar nunca.
 */
function verificarSinDeuda(idSocio: number): void {
  if (tieneDeudaPendiente(idSocio)) {
    throw new ServiceError(403, 'Tenés una deuda pendiente. Regularizala en recepción antes de comprar.');
  }
}

/**
 * REGLA 8 en versión consulta, sin lanzar. La usa Cobros para chequear
 * ANTES de cobrar una membresía en el combo "renovar + plan": si el plan
 * va a rebotar por deuda, no hay que haber cobrado nada todavía.
 * `verificarSinDeuda` la usa también, así la condición vive en un solo
 * lugar y no puede divergir entre el chequeo previo y la compra real.
 */
export function tieneDeudaPendiente(idSocio: number): boolean {
  return deudas.some((d) => d.id_socio === idSocio && d.estado === 'PENDIENTE');
}

/**
 * REGLA 1 (cobertura): toda Inscripcion_Actividad vence al mes de
 * comprarse, sea cual sea su tipo_limite — un plan "2x semana" se factura
 * mensual igual que uno "12 clases al mes"; tipo_limite sólo cambia CÓMO se
 * mide el consumo, no cuándo se cobra de nuevo. Por eso la Membresia tiene
 * que seguir cubriendo ese mes entero: si vence antes, la actividad
 * quedaría viva con la membresía vencida, que es justo lo que esta regla
 * existe para que no pase — se corta ACÁ, al comprar, no se corrige después.
 *
 * `membresia.fecha_vencimiento` undefined (cubre siempre) pasa siempre.
 */
/**
 * Hasta cuándo llega un plan de actividad comprado en `desde` — un mes
 * exacto, sea cual sea su tipo_limite (ver REGLA 1 abajo). Exportada
 * porque Cobros necesita saberlo ANTES de cobrar, para poder garantizar
 * que la renovación de membresía del combo alcance a cubrirlo: sin esto,
 * el combo cobraba la membresía y recién después descubría que el plan no
 * entraba (una membresía "mensual" de 30 días NO cubre un mes calendario
 * de 31 días, que es la mayoría de los meses).
 */
export function vencimientoDePlanComprado(desde: Date = new Date()): Date {
  return sumarMeses(desde, 1);
}

function validarCobertura(fechaInicio: Date, membresiaDelSocio: Membresia): void {
  if (!membresiaDelSocio.fecha_vencimiento) return;
  const vencimientoInscripcion = vencimientoDePlanComprado(fechaInicio);
  const vencimientoMembresia = parsearFecha(membresiaDelSocio.fecha_vencimiento);
  // Comparación por DÍA, no por instante: `sumarMeses` arrastra la hora
  // del momento de la compra (14:35, pongamos) mientras que un
  // fecha_vencimiento leído del "esquema" es siempre medianoche. Comparar
  // los Date crudos rechazaba una membresía que vence EXACTAMENTE el mismo
  // día en que termina el plan — cubre justo, tiene que pasar.
  if (diasEntre(vencimientoMembresia, vencimientoInscripcion) > 0) {
    throw new ServiceError(
      400,
      `Tu membresía vence el ${formatearFechaConAnio(vencimientoMembresia)}. Este plan se ` +
        `extendería hasta el ${formatearFechaConAnio(vencimientoInscripcion)}. Renová la membresía primero.`,
    );
  }
}

/**
 * Sólo lectura: si comprar un plan de actividad HOY pasaría REGLA 1 sin
 * rechazar. La usa Cobros para decidir, ANTES de intentar el cobro, si
 * ofrecer el combo "renovar membresía + cobrar el plan" en una sola
 * confirmación — situación que en un gimnasio real pasa todo el tiempo (la
 * membresía vence a mitad de mes, el plan de actividad siempre se cobra
 * por mes completo). Reusa validarCobertura tal cual — atrapa el rechazo
 * en vez de dejarlo pasar, así la regla nunca puede quedar desincronizada
 * entre el chequeo y la compra real.
 */
export async function membresiaCubreNuevoPlan(idSocio: number): Promise<boolean> {
  await delay();
  const membresia = membresiaVigente(idSocio);
  if (!membresia || membresia.estado !== 'ACTIVA') return false;
  try {
    validarCobertura(new Date(), membresia);
    return true;
  } catch {
    return false;
  }
}

/**
 * REGLA 6 (vencer no genera deuda): si una inscripción sigue ACTIVA pero ya
 * pasó su fecha_vencimiento, o es un plan POR_MES que se quedó en 0 clases,
 * se corrige acá — al leerla o al intentar reservar con ella ("lazy",
 * mismo criterio que el resto del proyecto usa para estados derivados, ver
 * membresiaService.estadoDeSocio). A diferencia de Membresia (que genera
 * Deuda al vencer impaga), acá NO se crea ninguna deuda: la actividad es
 * opcional, perderla no es una mora — el socio simplemente se queda sin
 * plan y puede seguir yendo con clases sueltas.
 */
function sincronizarVencimiento(inscripcion: InscripcionActividad, hoy: Date): void {
  if (inscripcion.estado !== 'ACTIVA') return;
  // No se muta `hoy`: setHours() en el propio parámetro mutaría el Date del
  // llamador (los objetos Date se pasan por referencia), y esta función se
  // llama en un loop con el mismo `hoy` para todas las inscripciones del
  // socio — mutarlo en la primera vuelta correría la fecha para el resto.
  const inicioDeHoy = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate());
  const vencioPorFecha = parsearFecha(inscripcion.fecha_vencimiento) < inicioDeHoy;
  const vencioPorClases = inscripcion.clases_restantes !== undefined && inscripcion.clases_restantes <= 0;
  if (vencioPorFecha || vencioPorClases) {
    inscripcion.estado = 'VENCIDA';
  }
}

/** La inscripción ACTIVA del socio para una actividad, o undefined. Sincroniza vencimientos antes de buscar. */
function inscripcionActivaDe(idSocio: number, idActividad: number, hoy: Date) {
  for (const insc of inscripcionesActividad) {
    if (insc.id_socio === idSocio) sincronizarVencimiento(insc, hoy);
  }
  return inscripcionesActividad.find((i) => {
    if (i.id_socio !== idSocio || i.estado !== 'ACTIVA') return false;
    const plan = planesActividad.find((p) => p.id_plan_actividad === i.id_plan_actividad);
    return plan?.id_actividad === idActividad;
  });
}

/** cupo_maximo del turno menos sus reservas activas — clase suelta y por plan compiten por el mismo cupo. */
function cupoDisponible(turno: Turno): number {
  const ocupadas = reservas.filter((r) => r.id_turno === turno.id_turno && r.estado === 'RESERVADA').length;
  return turno.cupo_maximo - ocupadas;
}

/** Turno.fecha + Turno.hora combinados en un Date, para comparar contra "ahora". */
function fechaHoraDeTurno(turno: Turno): Date {
  const base = parsearFecha(turno.fecha);
  const [horas, minutos] = turno.hora.split(':').map(Number);
  return new Date(base.getFullYear(), base.getMonth(), base.getDate(), horas, minutos);
}

function nombreDelProfesional(turno: Turno): string | undefined {
  if (turno.id_profesor !== undefined) {
    const profesor = profesores.find((p) => p.id_profesor === turno.id_profesor);
    return profesor ? nombrePorEmpleado(profesor.id_empleado) : undefined;
  }
  if (turno.id_entrenador_a_cargo !== undefined) {
    const entrenador = entrenadores.find((e) => e.id_entrenador === turno.id_entrenador_a_cargo);
    return entrenador ? nombrePorEmpleado(entrenador.id_empleado) : undefined;
  }
  return undefined;
}

// --- Catálogo ---

export interface ActividadListada {
  idActividad: number;
  nombre: string;
  descripcion?: string;
  cupoDefault: number;
  precioClaseSuelta: number;
  horasAnticipacionCancelacion: number;
}

export async function getActividades(): Promise<ActividadListada[]> {
  await delay();
  return actividades
    .filter((a) => a.activo)
    .map((a) => ({
      idActividad: a.id_actividad,
      nombre: a.nombre,
      descripcion: a.descripcion,
      cupoDefault: a.cupo_default,
      precioClaseSuelta: a.precio_clase_suelta,
      horasAnticipacionCancelacion: a.horas_anticipacion_cancelacion,
    }));
}

export interface PlanActividadListado {
  idPlanActividad: number;
  idActividad: number;
  nombre: string;
  tipoLimite: 'POR_SEMANA' | 'POR_MES';
  cantidad: number;
  precio: number;
}

export async function getPlanesDeActividad(idActividad: number): Promise<PlanActividadListado[]> {
  await delay();
  return planesActividad
    .filter((p) => p.id_actividad === idActividad && p.activo)
    .map((p) => ({
      idPlanActividad: p.id_plan_actividad,
      idActividad: p.id_actividad,
      nombre: p.nombre,
      tipoLimite: p.tipo_limite,
      cantidad: p.cantidad,
      precio: p.precio,
    }));
}

// --- ABM de catálogo (Dueño) ---
//
// A diferencia de getActividades/getPlanesDeActividad (catálogo que ve el
// socio, sólo lo activo), acá el Dueño necesita ver TODO — incluida una
// actividad dada de baja, para poder reactivarla — así que estos listados
// no filtran por `activo`. Mismo patrón dos-caminos (baja + reactivación)
// que rutinasService/nutricionService: nada se borra, sólo se desactiva.

export interface ActividadAdmin {
  idActividad: number;
  nombre: string;
  descripcion?: string;
  cupoDefault: number;
  precioClaseSuelta: number;
  horasAnticipacionCancelacion: number;
  activa: boolean;
}

function aActividadAdmin(a: Actividad): ActividadAdmin {
  return {
    idActividad: a.id_actividad,
    nombre: a.nombre,
    descripcion: a.descripcion,
    cupoDefault: a.cupo_default,
    precioClaseSuelta: a.precio_clase_suelta,
    horasAnticipacionCancelacion: a.horas_anticipacion_cancelacion,
    activa: a.activo,
  };
}

export async function getActividadesAdmin(): Promise<ActividadAdmin[]> {
  await delay();
  return actividades.map(aActividadAdmin);
}

export interface ActividadInput {
  nombre: string;
  descripcion?: string;
  cupoDefault: number;
  precioClaseSuelta: number;
  horasAnticipacionCancelacion: number;
}

function validarActividadInput(input: ActividadInput, idActividadActual?: number): void {
  const nombre = limpiar(input.nombre);
  if (nombre === '') {
    throw new ServiceError(400, 'El nombre es obligatorio');
  }
  if (
    actividades.some(
      (a) => a.id_actividad !== idActividadActual && a.nombre.toLowerCase() === nombre.toLowerCase(),
    )
  ) {
    throw new ServiceError(409, 'Ya existe una actividad con ese nombre');
  }
  if (!Number.isFinite(input.cupoDefault) || input.cupoDefault <= 0) {
    throw new ServiceError(400, 'El cupo tiene que ser mayor a 0');
  }
  if (!Number.isFinite(input.precioClaseSuelta) || input.precioClaseSuelta < 0) {
    throw new ServiceError(400, 'El precio no puede ser negativo');
  }
  if (!Number.isFinite(input.horasAnticipacionCancelacion) || input.horasAnticipacionCancelacion < 0) {
    throw new ServiceError(400, 'La anticipación no puede ser negativa');
  }
}

export async function crearActividad(input: ActividadInput, idUsuarioActor?: number): Promise<ActividadAdmin> {
  await delay();
  validarActividadInput(input);

  const actividad: Actividad = {
    id_actividad: siguienteId.actividad(),
    nombre: limpiar(input.nombre),
    descripcion: limpiar(input.descripcion) || undefined,
    cupo_default: input.cupoDefault,
    precio_clase_suelta: input.precioClaseSuelta,
    horas_anticipacion_cancelacion: input.horasAnticipacionCancelacion,
    activo: true,
  };
  actividades.push(actividad);

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Actividad',
    id_entidad: actividad.id_actividad,
    accion: 'ALTA',
  });

  return aActividadAdmin(actividad);
}

export async function actualizarActividad(
  idActividad: number,
  input: ActividadInput,
  idUsuarioActor?: number,
): Promise<ActividadAdmin> {
  await delay();
  const actividad = actividades.find((a) => a.id_actividad === idActividad);
  if (!actividad) throw new ServiceError(404, 'La actividad no existe');
  validarActividadInput(input, idActividad);

  actividad.nombre = limpiar(input.nombre);
  actividad.descripcion = limpiar(input.descripcion) || undefined;
  actividad.cupo_default = input.cupoDefault;
  actividad.precio_clase_suelta = input.precioClaseSuelta;
  actividad.horas_anticipacion_cancelacion = input.horasAnticipacionCancelacion;

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Actividad',
    id_entidad: idActividad,
    accion: 'MODIFICACION',
  });

  return aActividadAdmin(actividad);
}

export async function darDeBajaActividad(idActividad: number, idUsuarioActor?: number): Promise<void> {
  await delay();
  const actividad = actividades.find((a) => a.id_actividad === idActividad);
  if (!actividad) throw new ServiceError(404, 'La actividad no existe');
  if (!actividad.activo) throw new ServiceError(400, 'La actividad ya está inactiva');

  actividad.activo = false;

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Actividad',
    id_entidad: idActividad,
    accion: 'BAJA',
  });
}

export async function reactivarActividad(idActividad: number, idUsuarioActor?: number): Promise<ActividadAdmin> {
  await delay();
  const actividad = actividades.find((a) => a.id_actividad === idActividad);
  if (!actividad) throw new ServiceError(404, 'La actividad no existe');
  if (actividad.activo) throw new ServiceError(400, 'La actividad ya está activa');

  actividad.activo = true;

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Actividad',
    id_entidad: idActividad,
    accion: 'MODIFICACION',
    detalle: 'Reactivación',
  });

  return aActividadAdmin(actividad);
}

export interface PlanActividadAdmin {
  idPlanActividad: number;
  idActividad: number;
  nombre: string;
  tipoLimite: 'POR_SEMANA' | 'POR_MES';
  cantidad: number;
  precio: number;
  activo: boolean;
}

function aPlanActividadAdmin(p: PlanActividad): PlanActividadAdmin {
  return {
    idPlanActividad: p.id_plan_actividad,
    idActividad: p.id_actividad,
    nombre: p.nombre,
    tipoLimite: p.tipo_limite,
    cantidad: p.cantidad,
    precio: p.precio,
    activo: p.activo,
  };
}

export async function getPlanesDeActividadAdmin(idActividad: number): Promise<PlanActividadAdmin[]> {
  await delay();
  return planesActividad.filter((p) => p.id_actividad === idActividad).map(aPlanActividadAdmin);
}

export interface PlanActividadInput {
  nombre: string;
  tipoLimite: 'POR_SEMANA' | 'POR_MES';
  cantidad: number;
  precio: number;
}

function validarPlanInput(input: PlanActividadInput): void {
  if (limpiar(input.nombre) === '') {
    throw new ServiceError(400, 'El nombre del plan es obligatorio');
  }
  if (!Number.isFinite(input.cantidad) || input.cantidad <= 0) {
    throw new ServiceError(400, 'La cantidad tiene que ser mayor a 0');
  }
  if (!Number.isFinite(input.precio) || input.precio < 0) {
    throw new ServiceError(400, 'El precio no puede ser negativo');
  }
}

export async function crearPlanActividad(
  idActividad: number,
  input: PlanActividadInput,
  idUsuarioActor?: number,
): Promise<PlanActividadAdmin> {
  await delay();
  const actividad = actividades.find((a) => a.id_actividad === idActividad);
  if (!actividad) throw new ServiceError(404, 'La actividad no existe');
  validarPlanInput(input);

  const plan: PlanActividad = {
    id_plan_actividad: siguienteId.planActividad(),
    id_actividad: idActividad,
    nombre: limpiar(input.nombre),
    tipo_limite: input.tipoLimite,
    cantidad: input.cantidad,
    precio: input.precio,
    activo: true,
  };
  planesActividad.push(plan);

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Plan_Actividad',
    id_entidad: plan.id_plan_actividad,
    accion: 'ALTA',
    detalle: `De ${actividad.nombre}`,
  });

  return aPlanActividadAdmin(plan);
}

export async function actualizarPlanActividad(
  idPlanActividad: number,
  input: PlanActividadInput,
  idUsuarioActor?: number,
): Promise<PlanActividadAdmin> {
  await delay();
  const plan = planesActividad.find((p) => p.id_plan_actividad === idPlanActividad);
  if (!plan) throw new ServiceError(404, 'El plan no existe');
  validarPlanInput(input);

  plan.nombre = limpiar(input.nombre);
  plan.tipo_limite = input.tipoLimite;
  plan.cantidad = input.cantidad;
  plan.precio = input.precio;

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Plan_Actividad',
    id_entidad: idPlanActividad,
    accion: 'MODIFICACION',
  });

  return aPlanActividadAdmin(plan);
}

/**
 * Baja de un plan puntual — no de la actividad entera. A un socio que ya
 * tiene una inscripción activa con este plan no le pasa nada: REGLA 6 sigue
 * gobernando su vencimiento igual, esto sólo saca el plan del catálogo para
 * compras nuevas (mismo criterio que dar de baja una Rutina con socios
 * asignados).
 */
export async function darDeBajaPlanActividad(idPlanActividad: number, idUsuarioActor?: number): Promise<void> {
  await delay();
  const plan = planesActividad.find((p) => p.id_plan_actividad === idPlanActividad);
  if (!plan) throw new ServiceError(404, 'El plan no existe');
  if (!plan.activo) throw new ServiceError(400, 'El plan ya está inactivo');

  plan.activo = false;

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Plan_Actividad',
    id_entidad: idPlanActividad,
    accion: 'BAJA',
  });
}

export async function reactivarPlanActividad(
  idPlanActividad: number,
  idUsuarioActor?: number,
): Promise<PlanActividadAdmin> {
  await delay();
  const plan = planesActividad.find((p) => p.id_plan_actividad === idPlanActividad);
  if (!plan) throw new ServiceError(404, 'El plan no existe');
  if (plan.activo) throw new ServiceError(400, 'El plan ya está activo');

  plan.activo = true;

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Plan_Actividad',
    id_entidad: idPlanActividad,
    accion: 'MODIFICACION',
    detalle: 'Reactivación',
  });

  return aPlanActividadAdmin(plan);
}

// --- Asignación de profesores (Dueño) ---
//
// Profesor_Actividad es N:M puro, sin fila propia (clave compuesta) — no
// hay "editar" una asignación, sólo existe o no existe. Por eso el listado
// no distingue admin/socio como Actividad/Plan_Actividad: siempre devuelve
// TODOS los profesores activos con un flag `asignado`, listo para pintar un
// toggle, en vez de dos funciones separadas (asignados / no asignados).

export interface ProfesorAsignable {
  idProfesor: number;
  nombre: string;
  especialidad?: string;
  asignado: boolean;
}

export async function getProfesoresDeActividad(idActividad: number): Promise<ProfesorAsignable[]> {
  await delay();
  const asignados = new Set(
    profesorActividad.filter((pa) => pa.id_actividad === idActividad).map((pa) => pa.id_profesor),
  );
  return profesores
    .filter((p) => empleados.find((e) => e.id_empleado === p.id_empleado)?.activo)
    .map((p) => ({
      idProfesor: p.id_profesor,
      nombre: nombrePorEmpleado(p.id_empleado),
      especialidad: p.especialidad,
      asignado: asignados.has(p.id_profesor),
    }));
}

export async function asignarProfesorAActividad(
  idProfesor: number,
  idActividad: number,
  idUsuarioActor?: number,
): Promise<void> {
  await delay();
  const profesor = profesores.find((p) => p.id_profesor === idProfesor);
  if (!profesor) throw new ServiceError(404, 'El profesor no existe');
  const actividad = actividades.find((a) => a.id_actividad === idActividad);
  if (!actividad) throw new ServiceError(404, 'La actividad no existe');
  if (profesorActividad.some((pa) => pa.id_profesor === idProfesor && pa.id_actividad === idActividad)) {
    throw new ServiceError(409, 'Ese profesor ya está asignado a esta actividad');
  }

  profesorActividad.push({ id_profesor: idProfesor, id_actividad: idActividad });

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Profesor_Actividad',
    id_entidad: idProfesor,
    accion: 'ALTA',
    detalle: `Asignado a ${actividad.nombre}`,
  });
}

export async function desasignarProfesorDeActividad(
  idProfesor: number,
  idActividad: number,
  idUsuarioActor?: number,
): Promise<void> {
  await delay();
  const indice = profesorActividad.findIndex(
    (pa) => pa.id_profesor === idProfesor && pa.id_actividad === idActividad,
  );
  if (indice < 0) throw new ServiceError(404, 'Ese profesor no está asignado a esta actividad');

  const actividad = actividades.find((a) => a.id_actividad === idActividad);
  profesorActividad.splice(indice, 1);

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Profesor_Actividad',
    id_entidad: idProfesor,
    accion: 'BAJA',
    detalle: actividad ? `Desasignado de ${actividad.nombre}` : undefined,
  });
}

// --- Mis inscripciones (socio) ---

export interface InscripcionListada {
  idInscripcion: number;
  idActividad: number;
  nombreActividad: string;
  nombrePlan: string;
  tipoLimite: 'POR_SEMANA' | 'POR_MES';
  cantidad: number;
  /** Sólo tiene valor con tipoLimite POR_MES. */
  clasesRestantes?: number;
  precioPactado: number;
  fechaInicio: string;
  fechaVencimiento: string;
  estado: 'ACTIVA' | 'VENCIDA' | 'CANCELADA';
}

function aInscripcionListada(insc: (typeof inscripcionesActividad)[number]): InscripcionListada {
  const plan = planesActividad.find((p) => p.id_plan_actividad === insc.id_plan_actividad);
  const actividad = plan && actividades.find((a) => a.id_actividad === plan.id_actividad);
  return {
    idInscripcion: insc.id_inscripcion,
    idActividad: actividad?.id_actividad ?? 0,
    nombreActividad: actividad?.nombre ?? 'Actividad eliminada',
    nombrePlan: plan?.nombre ?? 'Plan eliminado',
    tipoLimite: plan?.tipo_limite ?? 'POR_MES',
    cantidad: plan?.cantidad ?? 0,
    clasesRestantes: insc.clases_restantes,
    precioPactado: insc.precio_pactado,
    fechaInicio: insc.fecha_inicio,
    fechaVencimiento: insc.fecha_vencimiento,
    estado: insc.estado,
  };
}

export async function getMisInscripciones(idSocio: number): Promise<InscripcionListada[]> {
  await delay();
  resolverSocio(idSocio);
  const hoy = new Date();
  const propias = inscripcionesActividad.filter((i) => i.id_socio === idSocio);
  for (const insc of propias) sincronizarVencimiento(insc, hoy);
  return propias
    .sort((a, b) => b.fecha_inicio.localeCompare(a.fecha_inicio))
    .map(aInscripcionListada);
}

// --- Comprar un plan (REGLAS 1, 7, 8) ---

export async function comprarPlan(
  idSocio: number,
  idPlanActividad: number,
  idUsuarioActor?: number,
  metodo: Pago['metodo'] = 'TRANSFERENCIA',
): Promise<InscripcionListada> {
  await delay();
  resolverSocio(idSocio);

  const plan = planesActividad.find((p) => p.id_plan_actividad === idPlanActividad && p.activo);
  if (!plan) throw new ServiceError(404, 'El plan no existe');
  const actividad = actividades.find((a) => a.id_actividad === plan.id_actividad);
  if (!actividad) throw new ServiceError(404, 'La actividad no existe');

  // REGLA 8: comprar está bloqueado con deuda pendiente.
  verificarSinDeuda(idSocio);

  const membresia = membresiaVigente(idSocio);
  if (!membresia || membresia.estado !== 'ACTIVA') {
    throw new ServiceError(400, 'Necesitás una membresía activa para comprar un plan de actividad');
  }

  const hoy = new Date();
  // REGLA 1.
  validarCobertura(hoy, membresia);

  // REGLA 7: un plan ACTIVO previo de la MISMA actividad se cierra sin
  // devolución ni crédito — el nuevo se cobra completo.
  const planViejo = inscripcionActivaDe(idSocio, actividad.id_actividad, hoy);
  if (planViejo) {
    planViejo.estado = 'CANCELADA';
    registrarAuditoria({
      id_usuario: idUsuarioActor,
      entidad: 'Inscripcion_Actividad',
      id_entidad: planViejo.id_inscripcion,
      accion: 'MODIFICACION',
      detalle: `Reemplazada por upgrade a "${plan.nombre}"`,
    });
  }

  const idInscripcion = siguienteId.inscripcionActividad();
  const nuevaInscripcion = {
    id_inscripcion: idInscripcion,
    id_socio: idSocio,
    id_plan_actividad: plan.id_plan_actividad,
    id_membresia: membresia.id_membresia,
    precio_pactado: plan.precio,
    fecha_inicio: aFechaISO(hoy),
    fecha_vencimiento: aFechaISO(sumarMeses(hoy, 1)),
    // clases_restantes sólo existe para POR_MES — ver REGLA 2/3.
    clases_restantes: plan.tipo_limite === 'POR_MES' ? plan.cantidad : undefined,
    estado: 'ACTIVA' as const,
  };
  inscripcionesActividad.push(nuevaInscripcion);

  pagos.push({
    id_pago: siguienteId.pago(),
    id_socio: idSocio,
    id_inscripcion: idInscripcion,
    id_sede: sedeActiva().id_sede,
    metodo,
    monto: plan.precio,
    fecha_pago: aTimestampISO(hoy),
    es_adelanto: false,
    estado: 'CONFIRMADO',
  });

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Inscripcion_Actividad',
    id_entidad: idInscripcion,
    accion: 'ALTA',
  });

  return aInscripcionListada(nuevaInscripcion);
}

export async function cancelarInscripcion(
  idSocio: number,
  idInscripcion: number,
  idUsuarioActor?: number,
): Promise<void> {
  await delay();
  resolverSocio(idSocio);

  const inscripcion = inscripcionesActividad.find((i) => i.id_inscripcion === idInscripcion);
  if (!inscripcion || inscripcion.id_socio !== idSocio) {
    throw new ServiceError(404, 'La inscripción no existe');
  }
  if (inscripcion.estado !== 'ACTIVA') {
    throw new ServiceError(400, 'Esa inscripción ya no está activa');
  }

  inscripcion.estado = 'CANCELADA';

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Inscripcion_Actividad',
    id_entidad: idInscripcion,
    accion: 'BAJA',
  });
}

// --- Turnos y reservas ---

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

export async function getTurnosDisponibles(
  idSede: number,
  idActividad?: number,
  fecha?: string,
): Promise<TurnoDisponible[]> {
  await delay();
  return turnos
    .filter((t) => t.id_sede === idSede && t.estado === 'HABILITADO')
    .filter((t) => idActividad === undefined || t.id_actividad === idActividad)
    .filter((t) => fecha === undefined || t.fecha === fecha)
    .map((t) => {
      const actividad = actividades.find((a) => a.id_actividad === t.id_actividad);
      return {
        idTurno: t.id_turno,
        idActividad: t.id_actividad,
        nombreActividad: actividad?.nombre ?? 'Actividad eliminada',
        fecha: t.fecha,
        hora: t.hora,
        cupoMaximo: t.cupo_maximo,
        cupoDisponible: cupoDisponible(t),
        nombreProfesional: nombreDelProfesional(t),
      };
    })
    .sort((a, b) => a.fecha.localeCompare(b.fecha) || a.hora.localeCompare(b.hora));
}

export interface ReservaConfirmada {
  idReserva: number;
  idTurno: number;
  fecha: string;
  hora: string;
  nombreActividad: string;
}

/**
 * Reserva un turno usando un plan ya comprado (REGLAS 2 y 3, según
 * tipo_limite). NO pasa por REGLA 8 (deudas) — ver el comentario de
 * verificarSinDeuda: usar un plan ya pagado no es una compra.
 */
export async function reservarTurno(
  idSocio: number,
  idTurno: number,
  idUsuarioActor?: number,
): Promise<ReservaConfirmada> {
  await delay();
  resolverSocio(idSocio);

  const turno = turnos.find((t) => t.id_turno === idTurno);
  if (!turno || turno.estado !== 'HABILITADO') {
    throw new ServiceError(400, 'Ese turno no está disponible');
  }
  const actividad = actividades.find((a) => a.id_actividad === turno.id_actividad);
  if (!actividad) throw new ServiceError(404, 'La actividad no existe');

  const hoy = new Date();
  const inscripcion = inscripcionActivaDe(idSocio, actividad.id_actividad, hoy);
  if (!inscripcion) {
    throw new ServiceError(
      400,
      `No tenés un plan activo de ${actividad.nombre}. Comprá uno o reservá como clase suelta.`,
    );
  }
  const plan = planesActividad.find((p) => p.id_plan_actividad === inscripcion.id_plan_actividad);
  if (!plan) throw new ServiceError(500, 'El plan de la inscripción no existe');

  if (reservas.some((r) => r.id_turno === idTurno && r.id_socio === idSocio && r.estado === 'RESERVADA')) {
    throw new ServiceError(409, 'Ya tenés una reserva para ese turno');
  }
  if (cupoDisponible(turno) <= 0) {
    throw new ServiceError(409, 'Ese turno ya no tiene cupo disponible');
  }

  if (plan.tipo_limite === 'POR_SEMANA') {
    // REGLA 2: sin contador guardado — se cuenta en vivo cuántas reservas
    // RESERVADA de esta actividad caen en la semana calendario actual
    // (lunes a domingo). Lo no usado en la semana se pierde: la ventana se
    // corre sola, no hay "arrastre" al lunes siguiente.
    const { lunes, domingo } = semanaCalendario(hoy);
    const usadasEstaSemana = reservas.filter((r) => {
      if (r.id_socio !== idSocio || r.estado !== 'RESERVADA') return false;
      const turnoDeLaReserva = turnos.find((t) => t.id_turno === r.id_turno);
      if (!turnoDeLaReserva || turnoDeLaReserva.id_actividad !== actividad.id_actividad) return false;
      const fechaDelTurno = parsearFecha(turnoDeLaReserva.fecha);
      return fechaDelTurno >= lunes && fechaDelTurno <= domingo;
    }).length;
    if (usadasEstaSemana >= plan.cantidad) {
      throw new ServiceError(
        403,
        `Ya usaste las ${plan.cantidad} clases de ${actividad.nombre} de esta semana. Se renueva el lunes.`,
      );
    }
  } else {
    // REGLA 3: clases_restantes es el contador real, se descuenta abajo.
    if ((inscripcion.clases_restantes ?? 0) <= 0) {
      throw new ServiceError(403, `No te quedan clases de ${actividad.nombre} este mes.`);
    }
  }

  const idReserva = siguienteId.reserva();
  reservas.push({
    id_reserva: idReserva,
    id_turno: idTurno,
    id_socio: idSocio,
    id_inscripcion: inscripcion.id_inscripcion,
    es_clase_suelta: false,
    fecha_reserva: aTimestampISO(hoy),
    estado: 'RESERVADA',
  });

  if (plan.tipo_limite === 'POR_MES') {
    inscripcion.clases_restantes = (inscripcion.clases_restantes ?? 0) - 1;
  }

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Reserva',
    id_entidad: idReserva,
    accion: 'ALTA',
  });

  return { idReserva, idTurno, fecha: turno.fecha, hora: turno.hora, nombreActividad: actividad.nombre };
}

/**
 * Compra y reserva una clase suelta (REGLAS 5 y 8). Disponible con
 * membresía activa, sin necesitar ningún plan previo — compite por el
 * MISMO cupo del turno que las reservas hechas con plan.
 */
export async function comprarClaseSuelta(
  idSocio: number,
  idTurno: number,
  idUsuarioActor?: number,
  metodo: Pago['metodo'] = 'TRANSFERENCIA',
): Promise<ReservaConfirmada> {
  await delay();
  resolverSocio(idSocio);

  const turno = turnos.find((t) => t.id_turno === idTurno);
  if (!turno || turno.estado !== 'HABILITADO') {
    throw new ServiceError(400, 'Ese turno no está disponible');
  }
  const actividad = actividades.find((a) => a.id_actividad === turno.id_actividad);
  if (!actividad) throw new ServiceError(404, 'La actividad no existe');

  const membresia = membresiaVigente(idSocio);
  if (!membresia || membresia.estado !== 'ACTIVA') {
    throw new ServiceError(400, 'Necesitás una membresía activa para comprar una clase suelta');
  }
  // REGLA 8.
  verificarSinDeuda(idSocio);

  if (reservas.some((r) => r.id_turno === idTurno && r.id_socio === idSocio && r.estado === 'RESERVADA')) {
    throw new ServiceError(409, 'Ya tenés una reserva para ese turno');
  }
  if (cupoDisponible(turno) <= 0) {
    throw new ServiceError(409, 'Ese turno ya no tiene cupo disponible');
  }

  const idPago = siguienteId.pago();
  pagos.push({
    id_pago: idPago,
    id_socio: idSocio,
    id_sede: turno.id_sede,
    metodo,
    monto: actividad.precio_clase_suelta,
    fecha_pago: aTimestampISO(new Date()),
    es_adelanto: false,
    estado: 'CONFIRMADO',
  });

  const idReserva = siguienteId.reserva();
  reservas.push({
    id_reserva: idReserva,
    id_turno: idTurno,
    id_socio: idSocio,
    es_clase_suelta: true,
    id_pago: idPago,
    fecha_reserva: aTimestampISO(new Date()),
    estado: 'RESERVADA',
  });

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Reserva',
    id_entidad: idReserva,
    accion: 'ALTA',
    detalle: 'Clase suelta',
  });

  return { idReserva, idTurno, fecha: turno.fecha, hora: turno.hora, nombreActividad: actividad.nombre };
}

/**
 * Cancela una reserva (REGLA 4). El cupo del turno y —si es plan
 * POR_SEMANA— el cupo semanal se liberan siempre, por el simple hecho de
 * que la reserva deja de estar en estado RESERVADA (los dos se cuentan en
 * vivo filtrando por ese estado, no hay nada que "devolver" a mano). Lo
 * único que depende de la anticipación es `clases_restantes` de un plan
 * POR_MES: con la anticipación pedida por la actividad se acredita de
 * vuelta, sin ella se pierde.
 */
export async function cancelarReserva(
  idSocio: number,
  idReserva: number,
  idUsuarioActor?: number,
): Promise<void> {
  await delay();
  resolverSocio(idSocio);

  const reserva = reservas.find((r) => r.id_reserva === idReserva);
  if (!reserva || reserva.id_socio !== idSocio) {
    throw new ServiceError(404, 'La reserva no existe');
  }
  if (reserva.estado !== 'RESERVADA') {
    throw new ServiceError(400, 'Esa reserva ya no está activa');
  }

  const turno = turnos.find((t) => t.id_turno === reserva.id_turno);
  if (!turno) throw new ServiceError(404, 'El turno no existe');
  const actividad = actividades.find((a) => a.id_actividad === turno.id_actividad);
  if (!actividad) throw new ServiceError(404, 'La actividad no existe');

  const hoy = new Date();
  const horasHastaElTurno = horasEntre(hoy, fechaHoraDeTurno(turno));
  const canceloATiempo = horasHastaElTurno >= actividad.horas_anticipacion_cancelacion;

  reserva.estado = 'CANCELADA_SOCIO';
  reserva.fecha_cancelacion = aTimestampISO(hoy);
  reserva.id_cancelado_por = idUsuarioActor;

  if (canceloATiempo && reserva.id_inscripcion !== undefined) {
    const inscripcion = inscripcionesActividad.find((i) => i.id_inscripcion === reserva.id_inscripcion);
    const plan =
      inscripcion && planesActividad.find((p) => p.id_plan_actividad === inscripcion.id_plan_actividad);
    if (inscripcion && plan?.tipo_limite === 'POR_MES') {
      inscripcion.clases_restantes = (inscripcion.clases_restantes ?? 0) + 1;
    }
  }
  // Clase suelta cancelada: el cupo se libera igual (arriba), pero el Pago
  // no se toca acá — reembolsar es una decisión de cobros/recepción, no
  // algo que esta acción del socio dispare sola.

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Reserva',
    id_entidad: idReserva,
    accion: 'MODIFICACION',
    detalle: canceloATiempo ? 'Cancelada a tiempo' : 'Cancelada fuera de término',
  });
}

// --- Asistencia ---

export interface AsistenciaRegistrada {
  idAsistencia: number;
  nombreSocio: string;
  fechaHoraIngreso: string;
  metodoRegistro: 'RFID' | 'MANUAL';
}

function aAsistenciaRegistrada(
  idAsistencia: number,
  idSocio: number,
  fechaHoraIngreso: string,
  metodoRegistro: 'RFID' | 'MANUAL',
): AsistenciaRegistrada {
  const socio = socios.find((s) => s.id_socio === idSocio);
  const persona = socio && personas.find((p) => p.id_persona === socio.id_persona);
  return {
    idAsistencia,
    nombreSocio: persona ? nombreCompleto(persona) : `Socio #${idSocio}`,
    fechaHoraIngreso,
    metodoRegistro,
  };
}

/**
 * Fichajes de hoy en la sede activa, para el panel de recepción — más
 * reciente primero. Sólo lectura: no aplica ninguna de las 8 reglas, es el
 * mismo tipo de listado simple que expone cualquier otro service (ver
 * getMisInscripciones).
 */
export async function getAsistenciasDeHoy(): Promise<AsistenciaRegistrada[]> {
  await delay();
  const hoy = aFechaISO(new Date());
  const idSede = sedeActiva().id_sede;
  return asistencias
    .filter((a) => a.id_sede === idSede && a.fecha_hora_ingreso.slice(0, 10) === hoy)
    .sort((a, b) => b.fecha_hora_ingreso.localeCompare(a.fecha_hora_ingreso))
    .map((a) => aAsistenciaRegistrada(a.id_asistencia, a.id_socio, a.fecha_hora_ingreso, a.metodo_registro));
}

/** Fichaje automático por tarjeta RFID, para el panel de recepción. */
export async function ficharRFID(codigoRfid: string): Promise<AsistenciaRegistrada> {
  await delay();
  const codigo = limpiar(codigoRfid);
  const socio = socios.find((s) => s.codigo_rfid === codigo);
  if (!socio || !socio.activo) {
    throw new ServiceError(404, 'Esa tarjeta no corresponde a ningún socio activo');
  }

  const idAsistencia = siguienteId.asistencia();
  const fechaHoraIngreso = aTimestampISO(new Date());
  asistencias.push({
    id_asistencia: idAsistencia,
    id_socio: socio.id_socio,
    id_sede: sedeActiva().id_sede,
    fecha_hora_ingreso: fechaHoraIngreso,
    metodo_registro: 'RFID',
  });

  return aAsistenciaRegistrada(idAsistencia, socio.id_socio, fechaHoraIngreso, 'RFID');
}

/** Carga manual del recepcionista, para quien se olvidó la tarjeta. */
export async function registrarAsistenciaManual(
  idSocio: number,
  idUsuarioActor: number,
): Promise<AsistenciaRegistrada> {
  await delay();
  const socio = resolverSocio(idSocio);
  if (!socio.activo) {
    throw new ServiceError(400, 'El socio no está activo');
  }

  const idAsistencia = siguienteId.asistencia();
  const fechaHoraIngreso = aTimestampISO(new Date());
  asistencias.push({
    id_asistencia: idAsistencia,
    id_socio: idSocio,
    id_sede: sedeActiva().id_sede,
    fecha_hora_ingreso: fechaHoraIngreso,
    metodo_registro: 'MANUAL',
    id_registrado_por: idUsuarioActor,
  });

  return aAsistenciaRegistrada(idAsistencia, idSocio, fechaHoraIngreso, 'MANUAL');
}
