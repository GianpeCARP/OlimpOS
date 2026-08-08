// Mock del dashboard (docs/estructura_dashboard.md: get_dashboard_stats,
// get_actividad_reciente, get_socios).
//
// Nada acá está escrito a mano: cada número se calcula recorriendo las
// tablas de mockDb, igual que lo haría una query. Eso tiene dos ventajas —
// los datos son coherentes entre tarjetas (los ingresos del mes se
// corresponden con los pagos listados) y un alta hecha desde el registro se
// ve reflejada en el dashboard sin tocar nada.
//
// Se exponen tres funciones y no una sola porque así van a ser los tres
// endpoints; la vista las pide en paralelo con Promise.all.

import type { Persona } from '../types';
import { DIAS_AVISO_VENCIMIENTO, type EstadoSocioValue } from '../config';
import { aFechaISO, claveMes, claveMesRelativa, diasEntre, finDelMesAnterior, parsearFecha } from '../utils/fechas';
import { formatearMoneda } from '../utils/format';
import { iniciales, nombreCompleto } from '../utils/personas';
import { delay } from './api';
import { estadoDeSocio, membresiaVigente, nombrePlan } from './membresiaService';
import { bajas, pagos, personas, socios, turnos } from './mockDb';

// --- Constantes de presentación de datos ---

/** Cuántos eventos trae el feed (estructura_dashboard.md: lista de 5). */
const MAX_EVENTOS_ACTIVIDAD = 5;

/** Cuántos socios recientes trae la lista (estructura_dashboard.md: 4). */
const MAX_SOCIOS_RECIENTES = 4;

// --- Métricas ---

export interface Metrica {
  valor: number;
  /**
   * Variación porcentual contra el período anterior.
   * `null` = no hay base de comparación (el período anterior fue cero y
   * dividir por cero daría Infinity). La vista, en ese caso, no muestra
   * delta en lugar de inventar un "+100%".
   */
  deltaPorcentual: number | null;
}

export interface DashboardStats {
  sociosActivos: Metrica;
  ingresosMes: Metrica;
  clasesHoy: Metrica;
  nuevosMes: Metrica;
}

function variacion(actual: number, anterior: number): number | null {
  if (anterior === 0) return null;
  return ((actual - anterior) / anterior) * 100;
}

/**
 * Cuántos socios estaban activos a una fecha dada: los que ya se habían
 * dado de alta y todavía no tenían baja registrada. Se calcula así, y no
 * con un contador guardado, para que el número del mes pasado sea real y
 * no un valor inventado para que el delta quede lindo.
 */
function sociosActivosAlCierre(fecha: Date): number {
  return socios.filter((socio) => {
    if (parsearFecha(socio.fecha_alta) > fecha) return false;
    const baja = bajas.find((b) => b.id_socio === socio.id_socio);
    return !baja || parsearFecha(baja.fecha_baja) > fecha;
  }).length;
}

/** Solo los pagos CONFIRMADO cuentan como ingreso: los PENDIENTE todavía no entraron y los CANCELADO/REEMBOLSADO no entraron nunca. */
function ingresosDelMes(clave: string): number {
  return pagos
    .filter((pago) => pago.estado === 'CONFIRMADO' && claveMes(pago.fecha_pago) === clave)
    .reduce((total, pago) => total + pago.monto, 0);
}

function turnosHabilitadosEn(fechaISO: string): number {
  return turnos.filter((turno) => turno.fecha === fechaISO && turno.estado === 'HABILITADO').length;
}

function altasDelMes(clave: string): number {
  return socios.filter((socio) => claveMes(socio.fecha_alta) === clave).length;
}

export async function obtenerEstadisticas(): Promise<DashboardStats> {
  await delay();

  const hoy = new Date();
  const ayer = new Date(hoy);
  ayer.setDate(ayer.getDate() - 1);

  const mesActual = claveMesRelativa(0, hoy);
  const mesAnterior = claveMesRelativa(-1, hoy);

  const activosHoy = socios.filter((s) => s.activo).length;
  const activosMesPasado = sociosActivosAlCierre(finDelMesAnterior(hoy));

  const ingresosActual = ingresosDelMes(mesActual);
  const ingresosAnterior = ingresosDelMes(mesAnterior);

  const clasesHoy = turnosHabilitadosEn(aFechaISO(hoy));
  const clasesAyer = turnosHabilitadosEn(aFechaISO(ayer));

  const nuevosActual = altasDelMes(mesActual);
  const nuevosAnterior = altasDelMes(mesAnterior);

  return {
    sociosActivos: {
      valor: activosHoy,
      deltaPorcentual: variacion(activosHoy, activosMesPasado),
    },
    ingresosMes: {
      valor: ingresosActual,
      deltaPorcentual: variacion(ingresosActual, ingresosAnterior),
    },
    clasesHoy: {
      valor: clasesHoy,
      deltaPorcentual: variacion(clasesHoy, clasesAyer),
    },
    nuevosMes: {
      valor: nuevosActual,
      deltaPorcentual: variacion(nuevosActual, nuevosAnterior),
    },
  };
}

// --- Actividad reciente ---

/**
 * Tipos de evento del feed (ACTIVITY_ICONS de estructura_dashboard.md).
 * 'rutina' está declarado pero todavía no se genera: hace falta la spec de
 * rutinas (Asignacion_Rutina) para tener de dónde sacarlo. Se deja el tipo
 * para que el mapa de íconos de la vista ya esté completo.
 */
export type TipoActividad = 'nuevo_socio' | 'pago' | 'rutina' | 'vencimiento';

export interface EventoActividad {
  /** Clave estable para React: tipo + id de la fila que originó el evento. */
  id: string;
  tipo: TipoActividad;
  descripcion: string;
  /** Timestamp ISO. La vista lo muestra como "hace 2 horas". */
  fecha: string;
}

function personaDeSocio(idSocio: number): Persona | undefined {
  const socio = socios.find((s) => s.id_socio === idSocio);
  return socio && personas.find((p) => p.id_persona === socio.id_persona);
}

export async function obtenerActividadReciente(): Promise<EventoActividad[]> {
  await delay();

  const hoy = new Date();
  const eventos: EventoActividad[] = [];

  // Altas de socio. La fecha con hora sale de Persona (fecha_alta de Socio
  // es un date sin hora), así que el "hace X" del feed es preciso.
  for (const socio of socios) {
    const persona = personas.find((p) => p.id_persona === socio.id_persona);
    if (!persona) continue;
    eventos.push({
      id: `nuevo_socio-${socio.id_socio}`,
      tipo: 'nuevo_socio',
      descripcion: `${nombreCompleto(persona)} se dio de alta como socio`,
      fecha: persona.fecha_alta,
    });
  }

  // Pagos confirmados. El monto se formatea acá porque el endpoint real
  // devolvería la descripción ya armada; el formato sale igual de
  // utils/format, no de un '$' escrito a mano.
  for (const pago of pagos) {
    if (pago.estado !== 'CONFIRMADO') continue;
    const persona = personaDeSocio(pago.id_socio);
    if (!persona) continue;
    eventos.push({
      id: `pago-${pago.id_pago}`,
      tipo: 'pago',
      descripcion: `${nombreCompleto(persona)} pagó ${formatearMoneda(pago.monto)}`,
      fecha: pago.fecha_pago,
    });
  }

  // Vencimientos próximos. Son eventos futuros: quedan arriba del feed
  // (está ordenado por fecha descendente) que es justo donde sirven, porque
  // son los que piden una acción.
  //
  // Se recorre SOCIO por socio y se mira sólo su membresía vigente, no
  // todas las filas ACTIVA: renovar no pisa la membresía anterior, crea una
  // nueva que arranca cuando termina la vieja (cobrosService.cobrarMembresia),
  // así que un socio recién renovado tiene DOS ACTIVA a la vez. Iterando
  // `membresias` el feed seguía avisando "vence en 3 días" por la vieja, al
  // lado del pago de la renovación que acababa de entrar.
  for (const socio of socios) {
    const membresia = membresiaVigente(socio.id_socio);
    if (!membresia || membresia.estado !== 'ACTIVA') continue;
    // Sin fecha_vencimiento = cubre siempre (extensión de actividades): no
    // hay "próximo vencimiento" que avisar.
    if (!membresia.fecha_vencimiento) continue;
    const dias = diasEntre(hoy, parsearFecha(membresia.fecha_vencimiento));
    if (dias < 0 || dias > DIAS_AVISO_VENCIMIENTO) continue;
    const persona = personaDeSocio(socio.id_socio);
    if (!persona) continue;
    eventos.push({
      id: `vencimiento-${membresia.id_membresia}`,
      tipo: 'vencimiento',
      descripcion: `Vence la membresía de ${nombreCompleto(persona)}`,
      fecha: `${membresia.fecha_vencimiento}T00:00:00`,
    });
  }

  return eventos
    .sort((a, b) => b.fecha.localeCompare(a.fecha))
    .slice(0, MAX_EVENTOS_ACTIVIDAD);
}

// --- Socios recientes ---
//
// El estado/plan de cada socio se calcula en membresiaService.ts, no acá —
// la vista de socios (sociosService.ts) necesita exactamente el mismo
// criterio, y duplicarlo en los dos services los haría divergir con el
// tiempo.

export interface SocioResumen {
  idSocio: number;
  nombre: string;
  iniciales: string;
  plan: string;
  estado: EstadoSocioValue;
}

export async function obtenerSociosRecientes(): Promise<SocioResumen[]> {
  await delay();

  const hoy = new Date();

  return socios
    .slice()
    .sort((a, b) => b.fecha_alta.localeCompare(a.fecha_alta))
    .slice(0, MAX_SOCIOS_RECIENTES)
    .map((socio) => {
      const persona = personas.find((p) => p.id_persona === socio.id_persona);
      return {
        idSocio: socio.id_socio,
        nombre: persona ? nombreCompleto(persona) : `Socio #${socio.id_socio}`,
        iniciales: persona ? iniciales(persona) : '?',
        plan: nombrePlan(socio.id_socio),
        estado: estadoDeSocio(socio, hoy),
      };
    });
}
