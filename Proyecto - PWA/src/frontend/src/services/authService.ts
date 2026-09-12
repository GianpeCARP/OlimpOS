// Sesión y baja de socios, contra la API real.
//
// De las tres partes de auth.spec.md quedan dos:
//
//   3.1 registro  — ELIMINADO. La consigna prohíbe el auto-registro en un
//                   sistema interno; el alta la hace el personal desde
//                   sociosService y el backend genera una clave temporal.
//   3.2 login     — POST /login, con el flujo de contraseña obligatoria.
//   3.3 baja      — POST /socios/{id}/baja y /reactivar.
//
// Las reglas que antes vivían acá —mensaje único para credenciales
// inválidas, bloqueo a los cinco intentos— se mudaron a
// routers/auth_router.py. Duplicarlas sería peor que no tenerlas: el cliente
// podría decir una cosa y el servidor otra.

import type { Persona, Usuario, Baja } from '../types';
import { ServiceError, pedir } from './api';
import { limpiar } from './validacion';

// --- 3.2 Inicio de sesión ---

/**
 * Sesión abierta. Es una de las dos formas que puede tomar LoginResultado.
 */
export interface SesionAbierta {
  debeCambiarPassword: false;
  usuario: Omit<Usuario, 'password_hash'>;
  persona: Persona;
  roles: string[];
  // No hay campo `token`: en el navegador la sesión vive en una cookie
  // httponly que este código no puede leer. Declararlo sería mentir sobre
  // algo que nunca va a tener valor.
  /**
   * Id de Socio de esta persona, si la tiene. Es lo único con lo que trabaja
   * el portal del socio: cada endpoint de /portal filtra por el id_socio
   * FIRMADO en el token, así que ningún socio puede pedir los datos de otro
   * cambiando un número.
   *
   * undefined para el staff que no es socio del gimnasio.
   */
  idSocio?: number;
}

/**
 * Credenciales correctas, pero la cuenta todavía tiene su contraseña
 * temporal. NO hay sesión: el backend verificó la contraseña y aun así se
 * negó a emitir un token hasta que la persona defina una propia.
 *
 * Se llega acá en tres casos, todos el mismo mecanismo: el primer ingreso de
 * una cuenta creada por el personal, el primer ingreso del dueño (cuenta del
 * seeder), y el reingreso después de que un admin resetee la clave.
 */
export interface CambioRequerido {
  debeCambiarPassword: true;
}

/**
 * Unión discriminada, no un objeto con campos opcionales: así TypeScript
 * OBLIGA a chequear `debeCambiarPassword` antes de tocar `roles`. Con campos
 * opcionales, olvidarse del caso compilaría igual y el bug aparecería recién
 * en runtime, con la sesión a medio abrir.
 */
export type LoginResultado = SesionAbierta | CambioRequerido;

/** La forma exacta en que responde POST /login (ver backend/schemas.py). */
interface LoginResponseApi {
  debe_cambiar_password: boolean;
  token: string | null;
  usuario: Omit<Usuario, 'password_hash'>;
  persona: Persona;
  roles: string[];
  idSocio: number | null;
}

export async function login(username: string, password: string): Promise<LoginResultado> {
  // Los campos vacíos se cortan antes de salir a la red. No es una regla de
  // seguridad —el backend la revalida— sino de claridad: un formulario en
  // blanco tiene que decir "faltan datos", no "usuario o contraseña
  // incorrectos", que manda a buscar el problema donde no está.
  if (limpiar(username) === '' || password === '') {
    throw new ServiceError(400, 'Completá usuario y contraseña');
  }

  const datos = await pedir<LoginResponseApi>('/login', {
    metodo: 'POST',
    cuerpo: { username: limpiar(username), password },
  });

  if (datos.debe_cambiar_password) {
    return { debeCambiarPassword: true };
  }

  // `datos.token` viene null a propósito para clientes web: la sesión quedó en
  // una cookie httponly que este código no puede ver ni necesita ver. El
  // campo sigue existiendo en el tipo porque la app Flet, que le dice al
  // backend que es de escritorio, sí lo recibe.
  return {
    debeCambiarPassword: false,
    usuario: datos.usuario,
    persona: datos.persona,
    roles: datos.roles,
    idSocio: datos.idSocio ?? undefined,
  };
}

/**
 * Cierra la sesión en el servidor.
 *
 * Hace falta pedírselo al backend: la cookie de sesión es httponly y
 * JavaScript no puede borrarla. Sin este llamado, "cerrar sesión" limpiaría
 * la pantalla pero dejaría la cookie viva en el navegador — y el próximo que
 * use esa máquina entraría con la sesión abierta.
 */
export async function logout(): Promise<void> {
  await pedir<{ mensaje: string }>('/logout', { metodo: 'POST' });
}

/**
 * Reconstruye la sesión a partir de la cookie. Es lo que hace que un F5 no
 * cierre la sesión.
 *
 * Lanza ServiceError 401 si el token venció, fue alterado, o la cuenta se
 * desactivó desde que se emitió — en cualquiera de esos casos hay que volver
 * al login.
 */
export async function sesionActual(): Promise<SesionAbierta> {
  const datos = await pedir<LoginResponseApi>('/me');
  return {
    debeCambiarPassword: false,
    usuario: datos.usuario,
    persona: datos.persona,
    roles: datos.roles,
    idSocio: datos.idSocio ?? undefined,
  };
}

/**
 * Define la contraseña definitiva de una cuenta con clave temporal.
 *
 * No abre sesión al terminar, a propósito: la persona vuelve al login y entra
 * de nuevo, así el primer uso de la contraseña nueva es un login normal y
 * queda probada antes de que nadie dependa de ella.
 */
export async function cambiarPassword(
  username: string,
  passwordActual: string,
  passwordNueva: string,
): Promise<string> {
  const datos = await pedir<{ mensaje: string }>('/cambiar-password', {
    metodo: 'POST',
    cuerpo: {
      username: limpiar(username),
      password_actual: passwordActual,
      password_nueva: passwordNueva,
    },
  });
  return datos.mensaje;
}

// --- 3.3 Baja y reactivación de socio ---

/**
 * Da de baja a un socio.
 *
 * El backend registra la fila en Baja con su tipo y motivo, desactiva al
 * socio y —si tiene— también a su cuenta de acceso. Esa última parte importa:
 * dejarle la cuenta viva a alguien dado de baja es exactamente el agujero que
 * documentó la auditoría del 2026-08-03, donde un socio de baja entraba y
 * veía los datos de todos los demás.
 *
 * `idUsuarioActor` se ignora: el backend saca quién ejecuta la baja de la
 * sesión del token. Si viniera del cliente, cualquiera podría registrar una
 * baja a nombre de otro.
 */
export async function darDeBaja(
  idSocio: number,
  tipo: NonNullable<Baja['tipo']>,
  motivo?: string,
  _idUsuarioActor?: number,
): Promise<void> {
  await pedir<unknown>(`/socios/${idSocio}/baja`, {
    metodo: 'POST',
    cuerpo: { tipo, motivo: motivo || null },
  });
}

/**
 * Camino de vuelta de darDeBaja: reactiva al socio y, si tiene, a su cuenta.
 *
 * El historial de Baja NO se toca — queda como registro de que esa baja
 * existió. Un socio puede irse y volver más de una vez, y cada baja tuvo su
 * motivo.
 */
export async function reactivarSocio(
  idSocio: number,
  _idUsuarioActor?: number,
): Promise<void> {
  await pedir<unknown>(`/socios/${idSocio}/reactivar`, { metodo: 'POST' });
}
