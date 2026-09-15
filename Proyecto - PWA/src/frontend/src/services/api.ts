// Piezas comunes a todos los services: el error tipado y el cliente HTTP.
//
// Acá vivía también `delay()`, una latencia artificial que hacía visibles
// los estados de carga mientras los datos salían de arrays en memoria. Se
// fue con el último mock: ahora la latencia es real.

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

// =========================================================================
// CLIENTE HTTP
// =========================================================================
//
// Todos los services de la PWA pasan por acá. Ninguno guarda datos propios
// ni conoce la URL del backend — eso vive en una sola línea de este archivo.
//
// Gemelo de `app/api_client.py` en la app Flet: mismo rol, mismo contrato de
// errores. Si cambia el manejo de un status acá, mirá el otro.

const API_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000';

/**
 * URL absoluta de un archivo que sirve el backend (p. ej. un video en
 * /videos/...). Para <video src>, que no pasa por `pedir`.
 */
export function urlDelBackend(ruta: string): string {
  return `${API_URL}${ruta}`;
}

// ESTA APP NO GUARDA EL TOKEN. En ningún lado.
//
// La sesión vive en una cookie `httponly` que setea el backend en el login, y
// que JavaScript no puede leer ni escribir. El navegador la manda sola en
// cada pedido; por eso todos los fetch de acá llevan `credentials: 'include'`.
//
// Es un cambio respecto de lo que había antes (token en sessionStorage) y la
// razón es el XSS: cualquier token que JavaScript pueda leer, un script
// inyectado también puede leerlo y mandárselo a otro servidor. Con httponly
// eso es imposible — el atacante podría disparar pedidos desde la página de
// la víctima, pero no llevarse la sesión para usarla después desde otra
// máquina.
//
// El precio de las cookies es que el navegador las manda también cuando el
// pedido lo origina OTRO sitio, que es el ataque CSRF. Por eso existe el
// token CSRF de acá abajo, y por eso el backend tiene csrf.py.
//
// Tampoco se guarda la identidad (usuario, persona, roles): eso se le
// pregunta al backend con GET /me en cada arranque. Si los roles vivieran en
// el navegador, alcanzaría con editarlos desde las devtools para verse
// secciones ajenas.

/** Cookie legible que el backend emite junto con la de sesión. */
const COOKIE_CSRF = 'olimpos_csrf';
const HEADER_CSRF = 'X-CSRF-Token';

/**
 * Lee el token CSRF de su cookie.
 *
 * Que esta cookie SÍ sea legible por JavaScript no es un descuido: es el
 * mecanismo. Un sitio atacante puede hacer que el navegador MANDE nuestras
 * cookies, pero no puede LEERLAS (política de mismo origen), así que no puede
 * copiar este valor al header. El backend exige que header y cookie
 * coincidan, y ahí se corta el ataque.
 */
function tokenCsrf(): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|;\\s*)${COOKIE_CSRF}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

/**
 * ¿Parece haber una sesión abierta?
 *
 * Mira la cookie CSRF porque la de sesión es httponly y no se puede consultar
 * desde acá. Las dos se emiten y se borran juntas, así que una alcanza como
 * indicio. Es solo una PISTA para evitar un GET /me inútil al arrancar: la
 * verdad sobre si la sesión sirve la tiene el backend.
 */
export function haySesion(): boolean {
  return tokenCsrf() !== null;
}

/**
 * Traduce el cuerpo de error de FastAPI a un mensaje mostrable.
 *
 * FastAPI usa dos formas y hay que contemplar las dos:
 *   - Errores normales:    { detail: "Usuario o contraseña incorrectos" }
 *   - Errores de Pydantic: { detail: [{ msg: "...", loc: [...] }, ...] }
 * Sin esto, un 422 mostraría en pantalla el array de objetos en crudo.
 */
function mensajeDelCuerpo(cuerpo: unknown, status: number): string {
  if (typeof cuerpo === 'object' && cuerpo !== null && 'detail' in cuerpo) {
    const detail = (cuerpo as { detail: unknown }).detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const primero = detail[0] as { msg?: string };
      if (primero?.msg) return primero.msg;
    }
  }
  return `El servidor respondió un error (${status}).`;
}

interface OpcionesPedido {
  metodo?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  cuerpo?: unknown;
}

/**
 * Corte por tiempo de cualquier pedido.
 *
 * `fetch` no tiene timeout propio: si el servidor acepta la conexión y después
 * no contesta —está reiniciándose, la base quedó colgada— la promesa nunca se
 * resuelve. Eso dejaba la app clavada en la pantalla de arranque, en negro,
 * sin llegar nunca al login.
 *
 * 15s y no menos porque el tier gratuito de Neon duerme la base y el primer
 * pedido después de un rato tarda varios segundos en despertarla.
 */
const TIMEOUT_MS = 15_000;

/**
 * Ejecuta una request contra la API y devuelve el JSON ya parseado.
 *
 * Lanza `ServiceError` en cualquier caso de fallo — incluida la red caída,
 * que se reporta como 0. Las vistas ya cazan ServiceError y muestran su
 * mensaje, así que no necesitan distinguir entre "el backend dijo que no" y
 * "el backend no contestó".
 */
export async function pedir<T>(ruta: string, opciones: OpcionesPedido = {}): Promise<T> {
  const { metodo = 'GET', cuerpo } = opciones;

  const headers: Record<string, string> = { 'Content-Type': 'application/json' };

  // El token CSRF solo hace falta en los métodos que modifican algo — es
  // exactamente la misma lista que protege el middleware del backend. Se
  // manda siempre que exista, aunque el endpoint sea público: mandarlo de más
  // no rompe nada, y olvidarlo de menos da un 403 difícil de diagnosticar.
  if (metodo !== 'GET') {
    const csrf = tokenCsrf();
    if (csrf) headers[HEADER_CSRF] = csrf;
  }

  let respuesta: Response;
  try {
    respuesta = await fetch(`${API_URL}${ruta}`, {
      method: metodo,
      headers,
      // Sin esto el navegador NO manda la cookie de sesión en pedidos
      // cross-origin, y como la PWA corre en :5173 y la API en :8000, todo
      // pedido saldría sin autenticar. Es el complemento obligatorio de
      // allow_credentials=True del lado del backend.
      credentials: 'include',
      signal: AbortSignal.timeout(TIMEOUT_MS),
      body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
    });
  } catch (err) {
    // fetch solo rechaza por fallo de red, CORS o timeout — nunca por un
    // status 4xx/5xx, que sí llegan como respuesta.
    if (err instanceof DOMException && err.name === 'TimeoutError') {
      throw new ServiceError(0, 'El servidor tardó demasiado en responder.');
    }
    throw new ServiceError(0, `No se pudo conectar con el servidor (${API_URL}).`);
  }

  if (respuesta.status === 204) return undefined as T;

  let datos: unknown = null;
  try {
    datos = await respuesta.json();
  } catch {
    if (respuesta.ok) return undefined as T;
  }

  if (!respuesta.ok) {
    throw new ServiceError(respuesta.status, mensajeDelCuerpo(datos, respuesta.status));
  }

  return datos as T;
}
