// Sección Usuarios, conectada a la API real (routers/usuarios.py).
//
// EL ROL NO SE ELIGE: SE DERIVA
// El formulario no tiene selector de rol y no es un olvido. El rol sale de las
// tablas donde la persona ya aparece —Socio, Entrenador, Dueno...— así que
// elegirlo a mano permitiría que la cuenta diga una cosa y la realidad otra.
// Para que alguien pase de recepcionista a entrenador se edita su ficha de
// PERSONAL, y su rol de sesión cambia solo.
//
// LA CONTRASEÑA LA GENERA EL SISTEMA
// Ni el alta ni la edición reciben contraseña. La genera el backend y la
// cuenta nace obligada a cambiarla en el primer ingreso. Que un administrador
// pudiera escribirla significaría que la conoce — y para siempre.

import type { RolValue, EstadoUsuarioValue } from '../config';
import { EstadoUsuario, RolLabel } from '../config';
import { pedir } from './api';

// --- Listado ---

export interface UsuarioListado {
  idUsuario: number;
  idPersona: number;
  nombre: string;
  username: string;
  email?: string;
  /** El principal. Para ofrecer las credenciales por WhatsApp si no hay mail. */
  telefono?: string;
  /**
   * El de mayor jerarquía, para las reglas que dependen de uno solo (nadie
   * opera sobre la cuenta de un Dueño salvo otro Dueño).
   */
  rol: RolValue;
  rolLabel: string;
  /** TODOS, que es lo que la tabla muestra: los roles se acumulan. */
  roles: { rol: RolValue; label: string }[];
  ultimoAcceso?: string;
  bloqueado: boolean;
  activo: boolean;
  estado: EstadoUsuarioValue;
  debeCambiarPassword: boolean;
}

interface UsuarioApi {
  id_usuario: number;
  id_persona: number;
  username: string;
  dni: string;
  nombre_completo: string;
  email: string | null;
  telefono: string | null;
  roles: string[];
  activo: boolean;
  bloqueado: boolean;
  debe_cambiar_password: boolean;
  ultimo_acceso: string | null;
}

/**
 * El backend devuelve TODOS los roles de la persona, porque se acumulan: el
 * dueño que además entrena tiene ['dueno', 'socio'], y desde que los roles de
 * empleado dejaron de ser excluyentes, un entrenador que también es profesor
 * tiene los dos. La tabla los muestra todos (ver `rolesDe`); hasta el
 * 2026-09-29 mostraba sólo el primero, así que a un socio contratado como
 * entrenador se lo veía como "Socio" y nada más.
 *
 * Éste sigue existiendo para las reglas que necesitan UNO: el primero es el de
 * mayor jerarquía por el orden en que roles_de_persona los arma (dueño, socio,
 * y después los de empleado).
 */
function rolPrincipal(roles: string[]): RolValue {
  return (roles[0] ?? 'socio') as RolValue;
}

function rolesDe(roles: string[]): { rol: RolValue; label: string }[] {
  return roles.map((r) => ({ rol: r as RolValue, label: RolLabel[r as RolValue] ?? r }));
}

function estadoDe(u: UsuarioApi): EstadoUsuarioValue {
  // El orden importa: una cuenta inactiva Y bloqueada se muestra como
  // inactiva, porque la baja es la decisión más fuerte de las dos.
  if (!u.activo) return EstadoUsuario.INACTIVO;
  if (u.bloqueado) return EstadoUsuario.BLOQUEADO;
  return EstadoUsuario.ACTIVO;
}

function aUsuarioListado(u: UsuarioApi): UsuarioListado {
  const rol = rolPrincipal(u.roles);
  return {
    idUsuario: u.id_usuario,
    idPersona: u.id_persona,
    nombre: u.nombre_completo,
    username: u.username,
    email: u.email ?? undefined,
    telefono: u.telefono ?? undefined,
    rol,
    rolLabel: RolLabel[rol] ?? rol,
    roles: rolesDe(u.roles),
    ultimoAcceso: u.ultimo_acceso ?? undefined,
    bloqueado: u.bloqueado,
    activo: u.activo,
    estado: estadoDe(u),
    debeCambiarPassword: u.debe_cambiar_password,
  };
}

export async function listarUsuarios(): Promise<UsuarioListado[]> {
  const datos = await pedir<UsuarioApi[]>('/usuarios');
  return datos.map(aUsuarioListado);
}

// --- Candidatos para otorgar acceso nuevo ---

export interface PersonaSinUsuario {
  idPersona: number;
  nombre: string;
  dni: string;
  /** Rol que va a tener la cuenta, derivado de lo que la persona ya es. */
  rol: RolValue;
  rolLabel: string;
  /** A dónde mandarle las credenciales apenas se crea la cuenta. */
  email?: string;
  telefono?: string;
}

/**
 * Personas que podrían tener cuenta y todavía no la tienen.
 *
 * El backend filtra por ROL, no solo por "no tiene usuario": alguien sin rol
 * de sesión no podría entrar a ninguna sección aunque se le creara la cuenta.
 * Y deja afuera al empleado dado de baja, cuya vuelta se da desde Personal:
 * crearle una cuenta nueva le devolvía el acceso con los permisos de su rol.
 */
export async function listarPersonasSinUsuario(): Promise<PersonaSinUsuario[]> {
  const datos = await pedir<{
    id_persona: number;
    dni: string;
    nombre_completo: string;
    email: string | null;
    telefono: string | null;
    roles: string[];
  }[]>('/usuarios/personas-sin-cuenta');

  return datos.map((p) => {
    const rol = rolPrincipal(p.roles);
    return {
      idPersona: p.id_persona,
      nombre: p.nombre_completo,
      dni: p.dni,
      rol,
      rolLabel: RolLabel[rol] ?? rol,
      email: p.email ?? undefined,
      telefono: p.telefono ?? undefined,
    };
  });
}

// --- Alta ---

export interface CrearUsuarioInput {
  idPersona: number;
}

export interface ResultadoCredenciales {
  username: string;
  passwordTemporal: string;
  mensaje: string;
  emailEnviado: boolean;
  /** Texto ya armado para mandar por WhatsApp si el mail no salió. */
  textoCredenciales?: string;
}

interface CredencialesApi {
  username: string;
  password_temporal: string;
  mensaje: string;
  email_enviado: boolean;
  texto_credenciales: string | null;
}

function aCredenciales(c: CredencialesApi): ResultadoCredenciales {
  return {
    username: c.username,
    passwordTemporal: c.password_temporal,
    mensaje: c.mensaje,
    emailEnviado: c.email_enviado,
    textoCredenciales: c.texto_credenciales ?? undefined,
  };
}

/**
 * Crea el acceso de una persona ya cargada.
 *
 * Solo recibe el id: los datos personales ya existen en Persona, y pedirlos
 * de nuevo permitiría cargar dos versiones distintas de la misma persona.
 * El username y la contraseña los genera el backend.
 */
export async function crearUsuario(input: CrearUsuarioInput): Promise<ResultadoCredenciales> {
  const datos = await pedir<CredencialesApi>('/usuarios', {
    metodo: 'POST',
    cuerpo: { id_persona: input.idPersona },
  });
  return aCredenciales(datos);
}

// --- Edición ---

export interface EditarUsuarioInput {
  username: string;
  email?: string;
}

export async function actualizarUsuario(
  idUsuario: number,
  input: EditarUsuarioInput,
): Promise<UsuarioListado> {
  const datos = await pedir<UsuarioApi>(`/usuarios/${idUsuario}`, {
    metodo: 'PUT',
    cuerpo: { username: input.username.trim(), email: input.email?.trim() || null },
  });
  return aUsuarioListado(datos);
}

// --- Acciones sobre una cuenta ---

/**
 * Borra la CUENTA de acceso (no a la persona: su ficha e historial quedan y se
 * le puede crear otra). El backend no deja borrar la propia ni la última de un
 * Dueño. Devuelve el mensaje ya redactado.
 */
export async function borrarCuenta(idUsuario: number): Promise<string> {
  const datos = await pedir<{ mensaje: string }>(`/usuarios/${idUsuario}`, { metodo: 'DELETE' });
  return datos.mensaje;
}

/**
 * Levanta el bloqueo por intentos fallidos SIN tocar la contraseña.
 *
 * Es distinto de resetear: acá la persona sí se acuerda su clave y el bloqueo
 * fue un accidente (tecleó mal, tenía el Bloq Mayús). Cambiársela en ese caso
 * sería molestarla al pedo.
 */
export async function desbloquearUsuario(idUsuario: number): Promise<UsuarioListado> {
  const datos = await pedir<UsuarioApi>(`/usuarios/${idUsuario}/desbloquear`, { metodo: 'POST' });
  return aUsuarioListado(datos);
}

export interface ResultadoReseteo {
  /** Hace falta para mostrarlo en el panel de entrega, igual que en el alta. */
  username: string;
  passwordTemporal: string;
  mensaje: string;
  emailEnviado: boolean;
  textoCredenciales?: string;
}

/**
 * Genera una contraseña temporal nueva y obliga a cambiarla en el próximo
 * ingreso. De paso desbloquea: quien llegó a los 5 intentos fallidos casi
 * siempre es porque no se acordaba la clave, que es justo lo que esto
 * resuelve — dejarla bloqueada obligaría a llamar dos veces.
 *
 * ⚠️ Solo un Dueño puede resetearle la contraseña a otro Dueño. Es el vector
 * de escalación de privilegios más directo del sistema: genera una clave y se
 * la MUESTRA a quien apretó el botón, así que sin esa regla cualquier
 * recepcionista podría reseteársela al dueño, leerla y entrar con control
 * total. El backend responde 403.
 */
export async function resetearPassword(idUsuario: number): Promise<ResultadoReseteo> {
  const datos = await pedir<CredencialesApi>(`/usuarios/${idUsuario}/resetear-password`, {
    metodo: 'POST',
  });
  const c = aCredenciales(datos);
  return {
    username: c.username,
    passwordTemporal: c.passwordTemporal,
    mensaje: c.mensaje,
    emailEnviado: c.emailEnviado,
    textoCredenciales: c.textoCredenciales,
  };
}

/**
 * Activa o desactiva una cuenta.
 *
 * Desactivar es la ÚNICA forma de revocar una sesión en el acto: el token no
 * se puede invalidar antes de que expire, pero el backend relee el usuario en
 * cada pedido y corta apenas ve la cuenta inactiva. Ante un problema de
 * seguridad, la herramienta es esta, no el logout.
 */
export async function alternarEstadoUsuario(
  idUsuario: number,
  activo: boolean,
): Promise<UsuarioListado> {
  const datos = await pedir<UsuarioApi>(
    `/usuarios/${idUsuario}/toggle-estado?activo=${activo}`,
    { metodo: 'POST' },
  );
  return aUsuarioListado(datos);
}

/**
 * Los dos nombres que usan las vistas. Antes eran ALIAS de la misma función
 * sin parámetro, y ahí estaba el problema: "dar de baja" y "activar" mandaban
 * exactamente el mismo pedido, y lo que pasaba dependía de en qué estado
 * estuviera la cuenta en el servidor, no de cuál de los dos botones se apretó.
 * Con una pantalla desactualizada —o con dos personas desactivando la misma
 * cuenta comprometida a la vez— el segundo click la reactivaba.
 *
 * Ahora cada una manda su estado destino y el resultado no depende del orden.
 */
export const darDeBajaUsuario = (idUsuario: number) => alternarEstadoUsuario(idUsuario, false);
export const activarUsuario = (idUsuario: number) => alternarEstadoUsuario(idUsuario, true);
