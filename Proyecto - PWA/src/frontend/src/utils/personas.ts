// Helpers de presentación sobre Persona. Viven acá y no en una vista porque
// los van a necesitar todas las pantallas que listen gente (dashboard,
// socios, personal): el criterio de "cómo se arma el nombre" tiene que ser
// uno solo.

import type { Persona } from '../types';

/** "Fernández" + "Lucía" -> "Lucía Fernández" (orden de lectura, no de tabla). */
export function nombreCompleto(persona: Persona): string {
  return `${persona.nombre} ${persona.apellido}`.trim();
}

/**
 * Iniciales para el avatar circular: "LF".
 * Si falta el apellido devuelve una sola letra en vez de romper.
 */
export function iniciales(persona: Persona): string {
  const primera = persona.nombre.trim().charAt(0);
  const segunda = persona.apellido.trim().charAt(0);
  return `${primera}${segunda}`.toUpperCase();
}
