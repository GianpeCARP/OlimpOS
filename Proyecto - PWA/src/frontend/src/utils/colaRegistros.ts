// Cola offline de series hechas, contadas por la cámara del circuito.
//
// POR QUÉ EXISTE
// ==============
// El conteo corre entero en el teléfono y NO necesita internet (el modelo y el
// WASM están bundleados). Lo único que sí lo necesita es GUARDAR la serie en
// Registro_Ejercicio. Y el wifi del gimnasio es justo lo que no hay que dar por
// sentado: es el mismo motivo por el que el cronómetro del circuito es del lado
// del cliente. Así que al terminar una serie NO se pierde si no hay señal: se
// deja en esta cola (localStorage) y se reintenta cuando la red vuelve.
//
// CÓMO DECIDE QUÉ REINTENTAR
// ==========================
// La diferencia clave es entre "no llegué al server" y "el server lo rechazó":
//   · status 0 (sin red / timeout) o 401/403 (sesión vencida): es TRANSITORIO.
//     Se conserva y se corta el barrido —no tiene sentido seguir intentando el
//     resto—; el próximo intento (evento 'online' o reapertura) lo reintenta.
//   · 400 / 404 / 422: el pedido está MAL y nunca va a entrar (ejercicio
//     inexistente, reps inválidas). Es veneno: se descarta para no trabar la
//     cola, avisando por consola.
//   · 5xx: el server está caído un rato. Se conserva pero se cuenta el intento,
//     y tras varios se descarta para no reintentar por siempre.
//
// Todo acceso a localStorage va en try/catch: en modo privado o con el storage
// lleno, leer o escribir puede tirar, y una serie no guardada no debe romper la
// pantalla.

import { ServiceError } from '../services/api';
import {
  guardarRegistroEjercicio,
  type RegistroEjercicioNuevo,
} from '../services/socioService';

const CLAVE = 'olimpos.reps.cola';
// Tras estos intentos contra un server que responde error de servidor (5xx),
// se abandona: algo estructural pasa y no vale la pena guardar la fila para
// siempre. Los errores de red NO cuentan acá (no incrementan intentos).
const MAX_INTENTOS = 6;
// Una serie que no se pudo subir en dos semanas ya no tiene valor de historial.
const VENCE_MS = 14 * 24 * 60 * 60 * 1000;

interface EnCola extends RegistroEjercicioNuevo {
  /** Cuándo se contó, para poder vencerla. */
  ts: number;
  /** Reintentos contra errores 5xx; los de red no cuentan. */
  intentos: number;
}

function leer(): EnCola[] {
  try {
    const crudo = localStorage.getItem(CLAVE);
    if (!crudo) return [];
    const datos = JSON.parse(crudo);
    return Array.isArray(datos) ? (datos as EnCola[]) : [];
  } catch {
    return [];
  }
}

function escribir(items: EnCola[]): void {
  try {
    if (items.length === 0) localStorage.removeItem(CLAVE);
    else localStorage.setItem(CLAVE, JSON.stringify(items));
  } catch {
    // Storage lleno o bloqueado: no hay nada que hacer sin romper la pantalla.
  }
}

/** Cuántas series quedan sin subir (para mostrarlo en la UI si hace falta). */
export function pendientes(): number {
  return leer().length;
}

let sincronizando = false;

/**
 * Intenta subir todo lo pendiente. Devuelve cuántas quedaron sin subir.
 *
 * Es idempotente y reentrante-segura: si ya hay un barrido en curso, no arranca
 * otro (los eventos 'online' pueden dispararse en ráfaga).
 */
export async function sincronizar(): Promise<number> {
  if (sincronizando) return pendientes();
  sincronizando = true;
  try {
    let items = leer();
    if (items.length === 0) return 0;

    // Primero tiro las vencidas: no se intentan siquiera.
    const ahora = Date.now();
    items = items.filter((it) => ahora - it.ts < VENCE_MS);

    const quedan: EnCola[] = [];
    let corto = false;

    for (let i = 0; i < items.length; i++) {
      const it = items[i];
      if (corto) {
        quedan.push(it);
        continue;
      }
      try {
        await guardarRegistroEjercicio(it);
        // subió: no se agrega a quedan.
      } catch (err) {
        const status = err instanceof ServiceError ? err.status : 0;
        if (status === 0 || status === 401 || status === 403) {
          // Transitorio (sin red o sesión vencida): conservar y cortar.
          quedan.push(it);
          corto = true;
        } else if (status >= 500) {
          const intentos = it.intentos + 1;
          if (intentos < MAX_INTENTOS) quedan.push({ ...it, intentos });
          else console.warn('[reps] serie descartada tras varios 5xx', it);
          corto = true; // el server está caído: no seguir con el resto ahora.
        } else {
          // 400 / 404 / 422: nunca va a entrar. Descartar (no push).
          console.warn('[reps] serie descartada (el server la rechazó)', status, it);
        }
      }
    }

    escribir(quedan);
    return quedan.length;
  } finally {
    sincronizando = false;
  }
}

/**
 * Encola una serie y la intenta subir en el acto.
 *
 * Devuelve 'guardado' si entró ya, o 'encolado' si quedó pendiente (sin red,
 * server caído o sesión vencida). En ningún caso tira: guardar una serie es lo
 * de menos comparado con perderla.
 */
export async function encolarRegistro(
  registro: RegistroEjercicioNuevo,
): Promise<'guardado' | 'encolado'> {
  const items = leer();
  items.push({ ...registro, ts: Date.now(), intentos: 0 });
  escribir(items);
  const restantes = await sincronizar();
  return restantes === 0 ? 'guardado' : 'encolado';
}

// La red que vuelve dispara un barrido. Se registra una sola vez por carga de
// la app; sincronizar() ya se protege de correr dos veces a la vez.
let listenerPuesto = false;
export function activarReintentoAutomatico(): void {
  if (listenerPuesto) return;
  listenerPuesto = true;
  window.addEventListener('online', () => void sincronizar());
}
