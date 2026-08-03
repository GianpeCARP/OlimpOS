// Piezas comunes a todos los services mock: el error tipado y la latencia
// artificial. Están separadas para que cada service nuevo no invente su
// propia clase de error ni su propio setTimeout.

/**
 * Error de servicio con código HTTP. El `status` es el que va a devolver el
 * endpoint real de FastAPI (400 validación, 401 credenciales, 409 conflicto,
 * 500 problema del servidor), así que las vistas ya pueden decidir en base a
 * él y no van a tener que cambiar cuando el mock desaparezca.
 */
export class ServiceError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ServiceError';
    this.status = status;
  }
}

const MENSAJE_ERROR_DESCONOCIDO = 'Ocurrió un error inesperado';

/**
 * Traduce cualquier cosa cazada en un catch a un mensaje mostrable.
 * Un ServiceError trae un mensaje pensado para el usuario; cualquier otra
 * cosa (un TypeError, un fallo de red) no, así que se muestra un genérico
 * en vez de filtrar detalles internos a la pantalla.
 */
export function mensajeDeError(err: unknown): string {
  return err instanceof ServiceError ? err.message : MENSAJE_ERROR_DESCONOCIDO;
}

// Latencia simulada. Sirve para que los estados de carga de las vistas se
// vean de verdad durante el desarrollo: sin esto, todo resuelve en el mismo
// tick y un spinner roto pasaría desapercibido hasta conectar la API real.
const DEMORA_MINIMA_MS = 400;
const DEMORA_VARIABLE_MS = 200;

export function delay(): Promise<void> {
  const ms = DEMORA_MINIMA_MS + Math.random() * DEMORA_VARIABLE_MS;
  return new Promise((resolve) => setTimeout(resolve, ms));
}
