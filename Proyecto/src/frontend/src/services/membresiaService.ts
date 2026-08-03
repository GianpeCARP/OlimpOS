// Deriva el estado visible de un socio (badge) y su plan actual a partir de
// Socio + Membresia + Tipo_Membresia. No es una columna del esquema — se
// calcula acá y no en cada vista para que dashboard y socios muestren
// siempre el mismo criterio.

import type { Membresia, Socio } from '../types';
import { DIAS_AVISO_VENCIMIENTO, EstadoSocio, type EstadoSocioValue } from '../config';
import { diasEntre, parsearFecha } from '../utils/fechas';
import { membresias, tiposMembresia } from './mockDb';

const SIN_PLAN = 'Sin plan asignado';

/** La membresía vigente de un socio es la de vencimiento más lejano. */
export function membresiaVigente(idSocio: number): Membresia | undefined {
  return membresias
    .filter((m) => m.id_socio === idSocio)
    .sort((a, b) => b.fecha_vencimiento.localeCompare(a.fecha_vencimiento))[0];
}

/**
 * Estado que se muestra en el badge. No es una columna del esquema: sale de
 * cruzar Socio.activo con el estado y el vencimiento de la Membresía.
 */
export function estadoDeSocio(socio: Socio, hoy: Date = new Date()): EstadoSocioValue {
  if (!socio.activo) return EstadoSocio.DE_BAJA;

  const membresia = membresiaVigente(socio.id_socio);
  if (!membresia) return EstadoSocio.SIN_MEMBRESIA;

  switch (membresia.estado) {
    case 'SUSPENDIDA':
      return EstadoSocio.SUSPENDIDO;
    case 'VENCIDA':
    case 'CANCELADA':
      return EstadoSocio.VENCIDO;
    case 'ACTIVA': {
      const dias = diasEntre(hoy, parsearFecha(membresia.fecha_vencimiento));
      if (dias < 0) return EstadoSocio.VENCIDO;
      if (dias <= DIAS_AVISO_VENCIMIENTO) return EstadoSocio.POR_VENCER;
      return EstadoSocio.ACTIVO;
    }
  }
}

/** Nombre del plan vigente, o el texto por defecto si no tiene ninguno. */
export function nombrePlan(idSocio: number): string {
  const membresia = membresiaVigente(idSocio);
  if (!membresia) return SIN_PLAN;
  const tipo = tiposMembresia.find((t) => t.id_tipo_membresia === membresia.id_tipo_membresia);
  return tipo?.nombre ?? SIN_PLAN;
}
