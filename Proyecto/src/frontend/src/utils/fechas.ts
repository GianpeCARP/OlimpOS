// Helpers de fecha. Existen por un motivo puntual: `new Date('2026-08-03')`
// se interpreta como medianoche UTC, así que en Argentina (UTC-3) esa fecha
// "vuelve" al 2 de agosto a las 21:00. Con date-only del esquema (fecha_alta,
// fecha_vencimiento, Turno.fecha) eso corre los cálculos un día entero.
// Todo lo de acá trabaja en hora local y compara strings cuando puede.

/** Date -> 'YYYY-MM-DD' en hora local (no en UTC, a diferencia de toISOString). */
export function aFechaISO(fecha: Date): string {
  const mes = String(fecha.getMonth() + 1).padStart(2, '0');
  const dia = String(fecha.getDate()).padStart(2, '0');
  return `${fecha.getFullYear()}-${mes}-${dia}`;
}

/**
 * Date -> 'YYYY-MM-DDTHH:mm:ss' en hora local, sin sufijo de zona.
 * Es la representación exacta de un `timestamp without time zone`, que es
 * el tipo que usa el esquema. Con toISOString() un pago del día 1 a las
 * 00:30 se guardaría como del mes anterior (por el pase a UTC).
 */
export function aTimestampISO(fecha: Date): string {
  const hora = String(fecha.getHours()).padStart(2, '0');
  const minuto = String(fecha.getMinutes()).padStart(2, '0');
  const segundo = String(fecha.getSeconds()).padStart(2, '0');
  return `${aFechaISO(fecha)}T${hora}:${minuto}:${segundo}`;
}

/** 'YYYY-MM-DD' (o un timestamp ISO) -> Date a medianoche local. */
export function parsearFecha(fechaISO: string): Date {
  const [anio, mes, dia] = fechaISO.slice(0, 10).split('-').map(Number);
  return new Date(anio, mes - 1, dia);
}

/** Clave de mes 'YYYY-MM'. Comparar por string evita cualquier tema de huso. */
export function claveMes(fechaISO: string): string {
  return fechaISO.slice(0, 7);
}

/** Clave de mes de un Date, desplazada N meses (negativo = hacia atrás). */
export function claveMesRelativa(desplazamiento: number, referencia: Date = new Date()): string {
  const fecha = new Date(referencia.getFullYear(), referencia.getMonth() + desplazamiento, 1);
  return aFechaISO(fecha).slice(0, 7);
}

export function sumarDias(fecha: Date, dias: number): Date {
  const resultado = new Date(fecha);
  resultado.setDate(resultado.getDate() + dias);
  return resultado;
}

/**
 * Días completos entre dos fechas (hasta - desde). Positivo = `hasta` es
 * futuro. Se normaliza a medianoche para que no dependa de la hora del día.
 */
export function diasEntre(desde: Date, hasta: Date): number {
  const MS_POR_DIA = 1000 * 60 * 60 * 24;
  const a = new Date(desde.getFullYear(), desde.getMonth(), desde.getDate());
  const b = new Date(hasta.getFullYear(), hasta.getMonth(), hasta.getDate());
  return Math.round((b.getTime() - a.getTime()) / MS_POR_DIA);
}

/** Último instante del mes anterior al de `referencia`. */
export function finDelMesAnterior(referencia: Date = new Date()): Date {
  return new Date(referencia.getFullYear(), referencia.getMonth(), 0, 23, 59, 59);
}

/**
 * Suma meses con el mismo criterio que usa Postgres para `fecha + interval
 * '1 month'`: si el día no existe en el mes destino (31 de enero + 1 mes),
 * cae al último día de ese mes en vez de desbordar al mes siguiente.
 * `setMonth` de JS por sí solo desborda (31 ene + 1 mes daría 3 mar, no 28/29
 * feb), así que se clampea contra el último día real del mes destino.
 */
export function sumarMeses(fecha: Date, meses: number): Date {
  const anio = fecha.getFullYear();
  const mes = fecha.getMonth();
  // Día 0 del mes siguiente al destino = último día del mes destino.
  const ultimoDiaDestino = new Date(anio, mes + meses + 1, 0).getDate();
  return new Date(anio, mes + meses, Math.min(fecha.getDate(), ultimoDiaDestino), fecha.getHours(), fecha.getMinutes(), fecha.getSeconds());
}

/**
 * Horas completas entre dos instantes (hasta - desde), CON precisión de
 * hora — a diferencia de diasEntre, que trunca a medianoche y por eso no
 * sirve para "¿cancelaste con 24hs de anticipación?": esa regla necesita la
 * hora exacta del turno, no el día calendario.
 */
export function horasEntre(desde: Date, hasta: Date): number {
  const MS_POR_HORA = 1000 * 60 * 60;
  return (hasta.getTime() - desde.getTime()) / MS_POR_HORA;
}

/**
 * Lunes 00:00:00 y domingo 23:59:59 de la semana calendario que contiene
 * `fecha`. Semana = lunes a domingo (uso local), no domingo a sábado.
 * `getDay()` de JS devuelve 0=domingo..6=sábado; se normaliza para que el
 * lunes sea siempre el primer día de la semana.
 */
export function semanaCalendario(fecha: Date): { lunes: Date; domingo: Date } {
  const diaSemana = fecha.getDay(); // 0=domingo, 1=lunes, ..., 6=sábado
  const diasDesdeElLunes = diaSemana === 0 ? 6 : diaSemana - 1;
  const lunes = new Date(fecha.getFullYear(), fecha.getMonth(), fecha.getDate() - diasDesdeElLunes);
  const domingo = new Date(lunes.getFullYear(), lunes.getMonth(), lunes.getDate() + 6, 23, 59, 59, 999);
  return { lunes, domingo };
}
