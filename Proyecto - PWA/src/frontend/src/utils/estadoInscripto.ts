import type { EstadoInscripto } from '../services/profesorService';

// Cómo se muestra el estado de una persona anotada a un turno. Compartido por
// "Mis clases" (profesor) y la agenda de turnos (Dueño y Recepcionista): son
// la misma lista vista por distintos roles, y el mismo estado no puede decir
// dos cosas ni verse de dos colores según quién mire. Colores iguales a los
// del panel de Recepción de Flet.

export const ESTADO_INSCRIPTO_LABEL: Record<EstadoInscripto, string> = {
  pendiente: 'Falta llegar',
  asistio: 'Presente',
  ausente: 'No llegó',
  en_espera: 'En espera',
  cancelada: 'Canceló',
};

export const ESTADO_INSCRIPTO_COLOR: Record<EstadoInscripto, string> = {
  pendiente: 'text-text-secondary',
  asistio: 'text-status-ok',
  ausente: 'text-status-danger',
  en_espera: 'text-status-warn',
  cancelada: 'text-text-muted',
};

/** "lun 16/09" a partir de "2026-09-16", en hora local. */
export function fechaCortaConDia(iso: string): string {
  const [anio, mes, dia] = iso.split('-').map(Number);
  const d = new Date(anio, mes - 1, dia);
  const diaSemana = ['dom', 'lun', 'mar', 'mié', 'jue', 'vie', 'sáb'][d.getDay()];
  return `${diaSemana} ${String(dia).padStart(2, '0')}/${String(mes).padStart(2, '0')}`;
}
