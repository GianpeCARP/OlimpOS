// Mock de estructura_usuarios.md: gestión de cuentas de acceso al sistema.
//
// El doc completo gira en torno a un modelo de permisos que no existe en
// el esquema real: 4 roles de sistema ("admin"/"trainer"/"staff"/"nutri"),
// cada uno con una lista fija de secciones visibles, en una lista
// `_MOCK_SYSTEM_USERS` hardcodeada aparte de app_state. En db/schema.sql,
// Usuario no tiene columna de rol — está atado 1:1 a una Persona, y el
// único rol que el login realmente entiende hoy es Roles.SOCIO/Roles.DUENO
// (ver mockDb.ts: "el rol todavía no es una tabla propia... viaja pegado
// al usuario en el mock"). Reproducir admin/trainer/staff/nutri sería
// mostrar una tabla de permisos que no corresponde a nada que la app
// realmente aplique — peor que los casos de "duración"/"macros" de rutinas
// y nutrición, porque ahí solo faltaba un dato, acá se estaría afirmando
// algo falso sobre cómo funciona el sistema.
//
// En su lugar:
// - La lista de usuarios son filas reales de Usuario (join con Persona),
//   con su rol real (Socio/Dueño) y sus columnas reales: activo, bloqueado,
//   intentos_fallidos, ultimo_acceso.
// - El panel de permisos (en la vista) usa `puedeVerRuta` de config.ts —
//   la misma función que ya usa el Sidebar para ocultar el link — así que
//   lo que se muestra acá es exactamente lo que el guard aplica de verdad,
//   no una tabla aparte que puede desincronizarse.
// - "Nuevo Usuario" otorga acceso a una Persona que todavía no tiene login
//   (Usuario.id_persona es NOT NULL — no se puede crear un Usuario sin
//   Persona). Incluye socios Y empleados: el rol de la cuenta NO se elige
//   en un dropdown, se DERIVA de lo que la persona ya es en el esquema
//   (personalService.rolDeSesionDeEmpleado lee las tablas hijas de
//   Empleado). Así el rol de sesión nunca puede contradecir la ficha.

import type { Persona } from '../types';
import { EstadoUsuario, Roles, RolLabel, type EstadoUsuarioValue, type RolValue } from '../config';
import { nombreCompleto } from '../utils/personas';
import { ServiceError, delay } from './api';
import { registrarAuditoria } from './auditoriaService';
import { rolDeSesionDeEmpleado } from './personalService';
import { esEmailValido, limpiar } from './validacion';
import { empleados, personas, socios, usuarios, siguienteId, type UsuarioMock } from './mockDb';

// --- Listado ---

export interface UsuarioListado {
  idUsuario: number;
  idPersona: number;
  nombre: string;
  username: string;
  email?: string;
  rol: RolValue;
  rolLabel: string;
  ultimoAcceso?: string;
  intentosFallidos: number;
  bloqueado: boolean;
  activo: boolean;
  estado: EstadoUsuarioValue;
}

function estadoDe(usuario: UsuarioMock): EstadoUsuarioValue {
  if (!usuario.activo) return EstadoUsuario.INACTIVO;
  if (usuario.bloqueado) return EstadoUsuario.BLOQUEADO;
  return EstadoUsuario.ACTIVO;
}

function aUsuarioListado(usuario: UsuarioMock, persona: Persona): UsuarioListado {
  return {
    idUsuario: usuario.id_usuario,
    idPersona: persona.id_persona,
    nombre: nombreCompleto(persona),
    username: usuario.username,
    email: persona.email,
    rol: usuario.rol,
    rolLabel: RolLabel[usuario.rol],
    ultimoAcceso: usuario.ultimo_acceso,
    intentosFallidos: usuario.intentos_fallidos,
    bloqueado: usuario.bloqueado,
    activo: usuario.activo,
    estado: estadoDe(usuario),
  };
}

export async function listarUsuarios(): Promise<UsuarioListado[]> {
  await delay();
  return usuarios
    .map((usuario) => {
      const persona = personas.find((p) => p.id_persona === usuario.id_persona);
      return persona ? aUsuarioListado(usuario, persona) : null;
    })
    .filter((u): u is UsuarioListado => u !== null);
}

// --- Candidatos para otorgar acceso nuevo ---

export interface PersonaSinUsuario {
  idPersona: number;
  nombre: string;
  dni: string;
  /** Rol que va a tener la cuenta, derivado de lo que la persona ya es. */
  rol: RolValue;
  rolLabel: string;
}

/**
 * Rol de sesión que le corresponde a una Persona según lo que ya es en el
 * esquema. Empleado tiene prioridad sobre Socio: si alguien del staff
 * además entrena en el gimnasio, su cuenta es la de trabajo — darle rol
 * `socio` la dejaría sin acceso a su propio panel. Devuelve null si la
 * persona no es ni empleado con rol ni socio (no puede tener cuenta).
 */
function rolDeSesionDePersona(idPersona: number): RolValue | null {
  const empleado = empleados.find((e) => e.id_persona === idPersona && e.activo);
  if (empleado) return rolDeSesionDeEmpleado(empleado.id_empleado);
  const socio = socios.find((s) => s.id_persona === idPersona && s.activo);
  return socio ? Roles.SOCIO : null;
}

export async function listarPersonasSinUsuario(): Promise<PersonaSinUsuario[]> {
  await delay();
  return personas
    .filter((p) => p.activo && !usuarios.some((u) => u.id_persona === p.id_persona))
    .map((persona) => {
      const rol = rolDeSesionDePersona(persona.id_persona);
      return rol
        ? {
            idPersona: persona.id_persona,
            nombre: nombreCompleto(persona),
            dni: persona.dni,
            rol,
            rolLabel: RolLabel[rol],
          }
        : null;
    })
    .filter((p): p is PersonaSinUsuario => p !== null);
}

// --- Alta ---

export interface CrearUsuarioInput {
  idPersona: number;
  username: string;
  password: string;
}

const LARGO_MINIMO_PASSWORD = 8;

export async function crearUsuario(
  input: CrearUsuarioInput,
  idUsuarioActor?: number,
): Promise<UsuarioListado> {
  await delay();

  const username = limpiar(input.username);
  if (username === '') {
    throw new ServiceError(400, 'El usuario es obligatorio');
  }
  if (input.password.length < LARGO_MINIMO_PASSWORD) {
    throw new ServiceError(400, `La contraseña debe tener al menos ${LARGO_MINIMO_PASSWORD} caracteres`);
  }
  if (usuarios.some((u) => u.username === username)) {
    throw new ServiceError(409, 'Ese nombre de usuario no está disponible');
  }
  const persona = personas.find((p) => p.id_persona === input.idPersona);
  if (!persona) {
    throw new ServiceError(400, 'La persona indicada no existe');
  }
  if (usuarios.some((u) => u.id_persona === input.idPersona)) {
    throw new ServiceError(409, 'Esa persona ya tiene una cuenta de acceso');
  }
  const rol = rolDeSesionDePersona(input.idPersona);
  if (!rol) {
    throw new ServiceError(400, 'Esa persona no es socio ni empleado activo');
  }

  const usuario: UsuarioMock = {
    id_usuario: siguienteId.usuario(),
    id_persona: input.idPersona,
    username,
    password_hash: input.password,
    intentos_fallidos: 0,
    bloqueado: false,
    activo: true,
    rol,
  };
  usuarios.push(usuario);

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Usuario',
    id_entidad: usuario.id_usuario,
    accion: 'ALTA',
  });

  return aUsuarioListado(usuario, persona);
}

// --- Edición ---
//
// Solo username (columna propia de Usuario) y email (columna de Persona,
// pero es un dato de "cómo te contacto para tu cuenta", tiene sentido
// tratarlo acá). El nombre de la persona y su rol no se editan desde este
// formulario: el nombre es responsabilidad de la ficha de Socio/Empleado,
// y el rol no es una columna, se deriva — no hay nada que pisar.

export interface EditarUsuarioInput {
  username: string;
  email?: string;
}

export async function actualizarUsuario(
  idUsuario: number,
  input: EditarUsuarioInput,
  idUsuarioActor?: number,
): Promise<UsuarioListado> {
  await delay();

  const usuario = usuarios.find((u) => u.id_usuario === idUsuario);
  if (!usuario) {
    throw new ServiceError(404, 'El usuario no existe');
  }
  const persona = personas.find((p) => p.id_persona === usuario.id_persona);
  if (!persona) {
    throw new ServiceError(404, 'El usuario no existe');
  }

  const username = limpiar(input.username);
  if (username === '') {
    throw new ServiceError(400, 'El usuario es obligatorio');
  }
  if (usuarios.some((u) => u.id_usuario !== idUsuario && u.username === username)) {
    throw new ServiceError(409, 'Ese nombre de usuario no está disponible');
  }
  const email = limpiar(input.email).toLowerCase();
  if (email && !esEmailValido(email)) {
    throw new ServiceError(400, 'El email no tiene un formato válido');
  }
  if (email && personas.some((p) => p.id_persona !== persona.id_persona && p.email?.toLowerCase() === email)) {
    throw new ServiceError(409, 'Ese email ya está en uso');
  }

  usuario.username = username;
  persona.email = email || undefined;

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Usuario',
    id_entidad: idUsuario,
    accion: 'MODIFICACION',
  });

  return aUsuarioListado(usuario, persona);
}

// --- Desbloqueo ---
//
// Usuario.bloqueado se prende solo, en authService.login, al quinto intento
// fallido seguido (auth.spec.md 3.2). El camino de vuelta es manual: lo
// hace el staff desde acá.
export async function desbloquearUsuario(
  idUsuario: number,
  idUsuarioActor?: number,
): Promise<UsuarioListado> {
  await delay();

  const usuario = usuarios.find((u) => u.id_usuario === idUsuario);
  if (!usuario) {
    throw new ServiceError(404, 'El usuario no existe');
  }
  if (!usuario.bloqueado) {
    throw new ServiceError(400, 'El usuario no está bloqueado');
  }

  usuario.bloqueado = false;
  usuario.intentos_fallidos = 0;

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Usuario',
    id_entidad: idUsuario,
    accion: 'MODIFICACION',
    detalle: 'Desbloqueo',
  });

  const persona = personas.find((p) => p.id_persona === usuario.id_persona);
  if (!persona) {
    throw new ServiceError(404, 'El usuario no existe');
  }
  return aUsuarioListado(usuario, persona);
}

// --- Reseteo de contraseña ---
//
// El doc simula un flujo por email ("se enviará un enlace de reseteo") que
// no existe en este mock — no hay backend de correo al que mandarle nada.
// En vez de fingir un envío que no pasa, se genera una contraseña temporal
// real y se devuelve para que la vista se la muestre al staff (que es quien
// se la va a comunicar al socio) — más honesto que simular un email al
// vacío. También limpia el bloqueo: un reseteo es, en la práctica, una
// segunda forma de recuperar acceso.

function generarPasswordTemporal(): string {
  // 8 caracteres alfanuméricos en mayúsculas — fácil de dictar por teléfono.
  return crypto.randomUUID().replace(/-/g, '').slice(0, 8).toUpperCase();
}

export interface ResultadoReseteo {
  usuario: UsuarioListado;
  passwordTemporal: string;
}

export async function resetearPassword(
  idUsuario: number,
  idUsuarioActor?: number,
): Promise<ResultadoReseteo> {
  await delay();

  const usuario = usuarios.find((u) => u.id_usuario === idUsuario);
  if (!usuario) {
    throw new ServiceError(404, 'El usuario no existe');
  }
  const persona = personas.find((p) => p.id_persona === usuario.id_persona);
  if (!persona) {
    throw new ServiceError(404, 'El usuario no existe');
  }

  const passwordTemporal = generarPasswordTemporal();
  usuario.password_hash = passwordTemporal;
  usuario.bloqueado = false;
  usuario.intentos_fallidos = 0;

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Usuario',
    id_entidad: idUsuario,
    accion: 'MODIFICACION',
    detalle: 'Reseteo de contraseña',
  });

  return { usuario: aUsuarioListado(usuario, persona), passwordTemporal };
}

// --- Baja y reactivación ---
//
// Usuario.activo es una columna propia, distinta de Socio.activo o
// Empleado.activo: una persona puede seguir siendo socia del gimnasio con
// su acceso a la app desactivado. Los dos caminos se construyen juntos
// desde el principio (ver feedback-soft-delete-dos-caminos).

export async function darDeBajaUsuario(idUsuario: number, idUsuarioActor?: number): Promise<void> {
  await delay();

  const usuario = usuarios.find((u) => u.id_usuario === idUsuario);
  if (!usuario || !usuario.activo) {
    throw new ServiceError(400, 'El usuario no está activo');
  }

  usuario.activo = false;

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Usuario',
    id_entidad: idUsuario,
    accion: 'BAJA',
  });
}

export async function activarUsuario(
  idUsuario: number,
  idUsuarioActor?: number,
): Promise<UsuarioListado> {
  await delay();

  const usuario = usuarios.find((u) => u.id_usuario === idUsuario);
  if (!usuario) {
    throw new ServiceError(404, 'El usuario no existe');
  }
  if (usuario.activo) {
    throw new ServiceError(400, 'El usuario ya está activo');
  }

  // Una cuenta desactivada por la baja del socio/empleado NO se puede
  // revivir desde acá sola: rolDeSesionDePersona sólo devuelve rol si la
  // persona sigue siendo socio o empleado ACTIVO. Sin este chequeo se podía
  // dar de baja a un socio (que apagaba su cuenta en cascada) y devolverle
  // el acceso con un click desde Usuarios, dejándolo "Dado de baja" en la
  // ficha y entrando a la app al mismo tiempo. El acceso se recupera
  // reactivando a la persona en su panel, no salteando ese paso.
  if (!rolDeSesionDePersona(usuario.id_persona)) {
    throw new ServiceError(
      409,
      'Esa persona está dada de baja como socio o empleado. Reactivala primero en su panel.',
    );
  }

  usuario.activo = true;

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Usuario',
    id_entidad: idUsuario,
    accion: 'MODIFICACION',
    detalle: 'Reactivación',
  });

  const persona = personas.find((p) => p.id_persona === usuario.id_persona);
  if (!persona) {
    throw new ServiceError(404, 'El usuario no existe');
  }
  return aUsuarioListado(usuario, persona);
}
