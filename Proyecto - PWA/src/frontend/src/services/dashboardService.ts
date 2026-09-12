// Dashboard, conectado a la API real (routers/dashboard.py).
//
// POR QUÉ ESTAS TRES CONSULTAS LAS HACE EL SERVIDOR
// Cada métrica resume una tabla ENTERA: "ingresos del mes" es la suma de
// todos los pagos confirmados, "socios activos" cuenta todos los socios.
// Calcularlo en el cliente obligaría a bajarse la tabla completa para mostrar
// un número — con cien socios ya es absurdo, con mil es inviable.
//
// Y el delta compara contra el mes anterior, que son datos que el navegador
// directamente no tiene: nadie se baja el historial completo para pintar una
// flechita verde.

import type { EstadoSocioValue } from '../config';
import { pedir } from './api';

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

/**
 * Las cuatro métricas de la portada.
 *
 * `ingresosMes` viene en CERO para quien no tiene el permiso de ver ingresos
 * —hoy, todos menos el Dueño—. El backend devuelve cero en vez de omitir el
 * campo para no romper el contrato: la vista espera las cuatro métricas
 * siempre, y así no hay que dibujar un caso especial.
 */
export async function obtenerEstadisticas(): Promise<DashboardStats> {
  return pedir<DashboardStats>('/dashboard/stats');
}

export type TipoActividad = 'nuevo_socio' | 'pago' | 'rutina' | 'vencimiento';

export interface EventoActividad {
  /** Clave estable para React: tipo + id de la fila que originó el evento. */
  id: string;
  tipo: TipoActividad;
  descripcion: string;
  /** Timestamp ISO. La vista lo muestra como "hace 2 horas". */
  fecha: string;
}

/**
 * El feed de la portada.
 *
 * Es UN endpoint y no tres porque mezcla orígenes distintos (pagos, altas,
 * vencimientos próximos) en una sola lista ordenada entre sí. Con tres
 * listas separadas, la vista tendría que intercalarlas a mano.
 *
 * Los vencimientos son eventos FUTUROS y aparecen igual: "vence en 3 días" es
 * lo más accionable del panel, porque es lo único sobre lo que el mostrador
 * puede hacer algo antes de que pase.
 */
export async function obtenerActividadReciente(): Promise<EventoActividad[]> {
  return pedir<EventoActividad[]>('/dashboard/actividad');
}

export interface SocioResumen {
  idSocio: number;
  nombre: string;
  iniciales: string;
  plan: string;
  estado: EstadoSocioValue;
}

/**
 * Las últimas altas con su estado de cuota.
 *
 * El `estado` no es una columna: sale de la membresía vigente (Activo, Por
 * vencer, Vencido). Lo deriva el backend con el mismo criterio que usa la
 * sección Socios — si lo hiciera cada pantalla, la misma regla viviría en
 * varios lugares y el día que cambien los 7 días de aviso, alguno se olvida.
 */
export async function obtenerSociosRecientes(): Promise<SocioResumen[]> {
  return pedir<SocioResumen[]>('/dashboard/socios-recientes');
}
