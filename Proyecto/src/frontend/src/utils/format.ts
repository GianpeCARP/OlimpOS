// Formateo de valores para mostrar en pantalla. Todo pasa por acá para que
// el locale y la moneda vivan en un solo lugar (config.ts) y no aparezcan
// '$', comas o 'es-AR' sueltos repartidos por las vistas.

import { LOCALE, MONEDA } from '../config';

// Los formatters de Intl son caros de construir, así que se crean una sola
// vez a nivel de módulo en vez de en cada render.
const formatoMoneda = new Intl.NumberFormat(LOCALE, {
  style: 'currency',
  currency: MONEDA,
  maximumFractionDigits: 0,
});

const formatoNumero = new Intl.NumberFormat(LOCALE);

const formatoPorcentaje = new Intl.NumberFormat(LOCALE, {
  maximumFractionDigits: 1,
});

const formatoTiempoRelativo = new Intl.RelativeTimeFormat(LOCALE, {
  numeric: 'auto',
});

const formatoFechaCorta = new Intl.DateTimeFormat(LOCALE, {
  day: '2-digit',
  month: 'short',
});

const formatoFechaConAnio = new Intl.DateTimeFormat(LOCALE, {
  day: '2-digit',
  month: 'short',
  year: 'numeric',
});

/** 128500 -> "$ 128.500" */
export function formatearMoneda(monto: number): string {
  return formatoMoneda.format(monto);
}

/** 1234 -> "1.234" */
export function formatearNumero(valor: number): string {
  return formatoNumero.format(valor);
}

/** 8.34 -> "+8,3%" | -2 -> "-2%" */
export function formatearDelta(porcentaje: number): string {
  const signo = porcentaje > 0 ? '+' : '';
  return `${signo}${formatoPorcentaje.format(porcentaje)}%`;
}

/**
 * Date -> "15 ago". Sin año: sirve para fechas que se leen dentro de un
 * contexto que ya lo deja claro (el eje de un gráfico, el vencimiento de
 * este mes).
 *
 * NO usar para fechas que pueden caer en otro año — ver formatearFecha.
 */
export function formatearFechaCorta(fecha: Date): string {
  return formatoFechaCorta.format(fecha);
}

/** Date -> "15 ago 2025". Siempre con año. */
export function formatearFechaConAnio(fecha: Date): string {
  return formatoFechaConAnio.format(fecha);
}

/**
 * Date -> "15 ago" si es de este año, "15 ago 2025" si no.
 *
 * Existe por un caso concreto que se veía como un error de datos: un Pase
 * Libre Anual arrancado hace 345 días y venciendo en 20 mostraba "Desde el
 * 23-ago" y "Vence 23-ago" — el mismo texto para dos fechas separadas por
 * un año, porque el formato corto no incluye el año. Igual de mal quedaba
 * una fecha de nacimiento de 1995 renderizada como "18-abr".
 *
 * La regla de "sólo cuando no es el año en curso" mantiene las fechas
 * cotidianas cortas (que es el 90% de los casos) y agrega el año
 * exactamente donde su ausencia genera ambigüedad.
 */
export function formatearFecha(fecha: Date, hoy: Date = new Date()): string {
  return fecha.getFullYear() === hoy.getFullYear()
    ? formatoFechaCorta.format(fecha)
    : formatoFechaConAnio.format(fecha);
}

// Unidades de mayor a menor, con su duración en segundos. Se recorre hasta
// encontrar la primera que "entre" en la diferencia.
const UNIDADES: { unidad: Intl.RelativeTimeFormatUnit; segundos: number }[] = [
  { unidad: 'year', segundos: 60 * 60 * 24 * 365 },
  { unidad: 'month', segundos: 60 * 60 * 24 * 30 },
  { unidad: 'day', segundos: 60 * 60 * 24 },
  { unidad: 'hour', segundos: 60 * 60 },
  { unidad: 'minute', segundos: 60 },
];

/**
 * Fecha ISO -> "hace 5 minutos", "ayer", "hace 2 meses".
 * El feed de actividad guarda timestamps reales (que es lo que va a mandar
 * el backend) y el texto relativo se calcula al renderizar, en vez de venir
 * ya escrito desde los datos.
 */
export function formatearTiempoRelativo(iso: string, ahora: Date = new Date()): string {
  const diferenciaSegundos = (new Date(iso).getTime() - ahora.getTime()) / 1000;

  for (const { unidad, segundos } of UNIDADES) {
    if (Math.abs(diferenciaSegundos) >= segundos) {
      return formatoTiempoRelativo.format(Math.round(diferenciaSegundos / segundos), unidad);
    }
  }
  // Menos de un minuto: "hace instantes" en vez de "hace 0 segundos".
  return formatoTiempoRelativo.format(0, 'minute');
}
