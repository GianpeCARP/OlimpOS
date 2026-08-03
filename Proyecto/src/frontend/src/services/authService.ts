// Mock de auth.spec.md (3.1 registro, 3.2 login, 3.3 baja).
//
// Los datos no viven acá: están en mockDb.ts, compartidos con el resto de
// los services. El día que exista la API de FastAPI, estas funciones cambian
// de cuerpo (fetch en vez de arrays) y nada del lado de las vistas o el
// store se toca, porque las firmas ya son las definitivas.

import type { Persona, Usuario, Telefono, Socio, Sede, Baja } from '../types';
import { Roles } from '../config';
import { aFechaISO, aTimestampISO } from '../utils/fechas';
import { ServiceError, delay } from './api';
import { registrarAuditoria } from './auditoriaService';
import { esEmailValido, limpiar } from './validacion';
import {
  personas,
  usuarios,
  telefonos,
  socios,
  sedes,
  bajas,
  siguienteId,
  proximoNumeroSocio,
  type UsuarioMock,
} from './mockDb';

/** Quita del usuario todo lo que no debe salir del backend. */
function sinHash(usuario: UsuarioMock): Omit<Usuario, 'password_hash'> {
  const { password_hash: _password_hash, rol: _rol, ...resto } = usuario;
  return resto;
}

// --- Validación de entrada ---
//
// Vive acá y no en las vistas a propósito: esta capa es la que el día de
// mañana reemplaza la API real, así que es la que tiene que hacer valer las
// reglas. El `required` de los inputs es solo comodidad de UX, no la regla.

// Solo las claves de texto de RegistroSocioInput. Evita que alguien liste
// como "obligatorio" un campo numérico (id_sede), que se valida distinto.
type CampoTextoRegistro = {
  // El -? saca la opcionalidad para que `undefined` no se cuele como clave.
  [K in keyof RegistroSocioInput]-?: RegistroSocioInput[K] extends string | undefined ? K : never;
}[keyof RegistroSocioInput];

// Campos que no pueden llegar vacíos al alta. dni/apellido/nombre son NOT
// NULL en db/schema.sql; email y telefono los exige auth.spec.md 3.1 (paso 4
// y paso 6) aunque la tabla los tolere nulos; username/password son la
// cuenta en sí. La etiqueta es la que ve el usuario en el formulario.
const CAMPOS_OBLIGATORIOS: { campo: CampoTextoRegistro; etiqueta: string }[] = [
  { campo: 'dni', etiqueta: 'DNI' },
  { campo: 'nombre', etiqueta: 'Nombre' },
  { campo: 'apellido', etiqueta: 'Apellido' },
  { campo: 'email', etiqueta: 'Email' },
  { campo: 'telefono', etiqueta: 'Teléfono' },
  { campo: 'username', etiqueta: 'Usuario' },
  { campo: 'password', etiqueta: 'Contraseña' },
];

const LARGO_MINIMO_PASSWORD = 8;

// --- Sedes ---

/**
 * El alta de socio necesita una id_sede y todavía no existe la spec de
 * sedes (no hay pantalla de selección ni endpoint de listado). Hasta que la
 * haya, el registro usa la única sede activa. Es dato, no constante de UI:
 * por eso lo resuelve el service y la vista solo lo muestra.
 */
export async function obtenerSedePorDefecto(): Promise<Sede> {
  await delay();
  const sede = sedes.find((s) => s.activo);
  if (!sede) {
    throw new ServiceError(500, 'No hay ninguna sede activa configurada');
  }
  return sede;
}

// --- 3.1 Registro de socio ---

export interface RegistroSocioInput {
  dni: string;
  apellido: string;
  nombre: string;
  email: string;
  fecha_nacimiento?: string;
  telefono: string;
  id_sede: number;
  username: string;
  password: string;
}

export interface RegistroSocioResultado {
  persona: Persona;
  usuario: Omit<Usuario, 'password_hash'>;
  telefono: Telefono;
  socio: Socio;
}

export async function registrarSocio(
  input: RegistroSocioInput,
): Promise<RegistroSocioResultado> {
  await delay();

  // Paso 4 de la spec — validaciones, en orden: obligatorios, formato,
  // largo de contraseña, duplicados. Primero lo que no depende de los datos
  // ya cargados, para no responder "DNI duplicado" cuando en realidad el
  // problema es que el campo vino vacío.
  for (const { campo, etiqueta } of CAMPOS_OBLIGATORIOS) {
    if (limpiar(input[campo]) === '') {
      throw new ServiceError(400, `El campo ${etiqueta} es obligatorio`);
    }
  }

  // Se normaliza una sola vez y se usa esto de acá en adelante: lo que se
  // compara contra los duplicados tiene que ser lo mismo que se guarda, o
  // " 30111222" entraría como un DNI distinto de "30111222".
  const dni = limpiar(input.dni);
  const apellido = limpiar(input.apellido);
  const nombre = limpiar(input.nombre);
  const email = limpiar(input.email).toLowerCase();
  const telefono = limpiar(input.telefono);
  const username = limpiar(input.username);
  const fechaNacimiento = limpiar(input.fecha_nacimiento) || undefined;
  // La contraseña NO se limpia: los espacios son parte de la contraseña.
  const password = input.password;

  if (!esEmailValido(email)) {
    throw new ServiceError(400, 'El email no tiene un formato válido');
  }
  if (password.length < LARGO_MINIMO_PASSWORD) {
    throw new ServiceError(
      400,
      `La contraseña debe tener al menos ${LARGO_MINIMO_PASSWORD} caracteres`,
    );
  }

  if (personas.some((p) => p.dni === dni)) {
    throw new ServiceError(409, 'Ya existe una persona con ese DNI');
  }
  if (personas.some((p) => p.email?.toLowerCase() === email)) {
    throw new ServiceError(409, 'Ese email ya está en uso');
  }
  if (usuarios.some((u) => u.username === username)) {
    throw new ServiceError(409, 'Ese nombre de usuario no está disponible');
  }
  const sede = sedes.find((s) => s.id_sede === input.id_sede);
  if (!sede) {
    throw new ServiceError(400, 'La sede indicada no existe');
  }

  // Paso 6: el orden de los INSERT es el de la spec —
  // Persona -> Usuario -> Telefono -> Socio (cada uno depende del anterior).
  const id_persona = siguienteId.persona();
  const persona: Persona = {
    id_persona,
    dni,
    apellido,
    nombre,
    email,
    fecha_nacimiento: fechaNacimiento,
    fecha_alta: aTimestampISO(new Date()),
    activo: true,
  };
  personas.push(persona);

  const usuario: UsuarioMock = {
    id_usuario: siguienteId.usuario(),
    id_persona,
    username,
    password_hash: password,
    intentos_fallidos: 0,
    bloqueado: false,
    activo: true,
    rol: Roles.SOCIO,
  };
  usuarios.push(usuario);

  // El formulario pide un solo teléfono, así que es el principal. tipo
  // CELULAR es el default del esquema; cuando haya ABM de teléfonos se
  // podrán cargar varios y elegir cuál es el principal.
  const telefonoFila: Telefono = {
    id_telefono: siguienteId.telefono(),
    id_persona,
    numero: telefono,
    tipo: 'CELULAR',
    principal: true,
  };
  telefonos.push(telefonoFila);

  const id_socio = siguienteId.socio();
  const socio: Socio = {
    id_socio,
    id_persona,
    id_sede: input.id_sede,
    numero_socio: proximoNumeroSocio(id_socio),
    fecha_alta: aFechaISO(new Date()),
    activo: true,
  };
  socios.push(socio);

  // Spec 3.1 paso 7: sin id_usuario porque todavía no hay sesión — la
  // persona/usuario recién se están creando en esta misma llamada.
  registrarAuditoria({ entidad: 'Socio', id_entidad: socio.id_socio, accion: 'ALTA' });

  return { persona, usuario: sinHash(usuario), telefono: telefonoFila, socio };
}

// --- 3.2 Inicio de sesión ---

export interface LoginResultado {
  usuario: Omit<Usuario, 'password_hash'>;
  persona: Persona;
  roles: string[];
  token: string;
  /**
   * Id de la fila Socio de esta persona, si la tiene. Es lo único con lo
   * que trabaja el portal del socio: cada función de socioService lo recibe
   * y devuelve SÓLO datos de ese id.
   *
   * Se resuelve acá, una vez, en el login, y no en cada vista: si cada
   * pantalla hiciera la traversal persona -> socio por su cuenta, alcanzaría
   * con que una sola se olvidara de filtrar para que empiece a mostrar
   * datos de otro. Con el backend real esto sale del token, no de una
   * búsqueda en el cliente.
   *
   * undefined para el staff que no es socio del gimnasio.
   */
  idSocio?: number;
}

// Un único mensaje para usuario inexistente, inactivo, bloqueado o
// contraseña incorrecta: distinguirlos le confirmaría a un atacante qué
// usuarios existen (regla de seguridad de auth.spec.md 3.2).
const CREDENCIALES_INVALIDAS = 'Usuario o contraseña incorrectos';

const MAX_INTENTOS_FALLIDOS = 5;

export async function login(username: string, password: string): Promise<LoginResultado> {
  await delay();

  // Campos vacíos se cortan antes de tocar los datos: sin esto, un login con
  // todo en blanco entra a buscar el username '' y devuelve "usuario o
  // contraseña incorrectos", que es confuso — el problema no son los datos,
  // es que faltan. No revela nada: todavía no se consultó ningún usuario.
  if (limpiar(username) === '' || password === '') {
    throw new ServiceError(400, 'Completá usuario y contraseña');
  }

  const usuario = usuarios.find((u) => u.username === limpiar(username));

  if (!usuario || !usuario.activo || usuario.bloqueado) {
    throw new ServiceError(401, CREDENCIALES_INVALIDAS);
  }

  if (usuario.password_hash !== password) {
    usuario.intentos_fallidos += 1;
    if (usuario.intentos_fallidos >= MAX_INTENTOS_FALLIDOS) {
      usuario.bloqueado = true;
    }
    throw new ServiceError(401, CREDENCIALES_INVALIDAS);
  }

  usuario.intentos_fallidos = 0;
  usuario.ultimo_acceso = aTimestampISO(new Date());

  const persona = personas.find((p) => p.id_persona === usuario.id_persona);
  if (!persona) {
    throw new ServiceError(401, CREDENCIALES_INVALIDAS);
  }

  // Spec 3.2 paso 6: se audita el login recién acá, con el usuario ya
  // validado — nunca se audita un intento fallido como LOGIN.
  registrarAuditoria({
    id_usuario: usuario.id_usuario,
    entidad: 'Usuario',
    id_entidad: usuario.id_usuario,
    accion: 'LOGIN',
  });

  return {
    usuario: sinHash(usuario),
    persona,
    roles: [usuario.rol],
    token: crypto.randomUUID(),
    idSocio: socios.find((s) => s.id_persona === persona.id_persona)?.id_socio,
  };
}

// --- 3.3 Baja de socio ---

export async function darDeBaja(
  idSocio: number,
  tipo: NonNullable<Baja['tipo']>,
  motivo?: string,
  // Quién ejecuta la baja (el usuario logueado que la dispara). Optativo:
  // Baja.id_registrado_por y Auditoria.id_usuario son ambos nullable.
  idUsuarioActor?: number,
): Promise<void> {
  await delay();

  const socio = socios.find((s) => s.id_socio === idSocio);
  if (!socio || !socio.activo) {
    throw new ServiceError(400, 'El socio no está activo');
  }

  bajas.push({
    id_baja: siguienteId.baja(),
    id_socio: idSocio,
    fecha_baja: aFechaISO(new Date()),
    tipo,
    motivo,
    id_registrado_por: idUsuarioActor,
  });

  socio.activo = false;
  const usuario = usuarios.find((u) => u.id_persona === socio.id_persona);
  if (usuario) {
    usuario.activo = false;
  }

  // Spec 3.3 paso 5.
  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Socio',
    id_entidad: idSocio,
    accion: 'BAJA',
  });
}

/**
 * Camino de vuelta de darDeBaja: reactiva al socio y, si tiene, a su
 * Usuario. El historial de Baja no se toca (queda como registro, no se
 * borra). No hay 'REACTIVACION' en Auditoria.accion (el enum del esquema es
 * ALTA/MODIFICACION/BAJA/CONSULTA/LOGIN) — se audita como MODIFICACION con
 * el detalle aclarando qué cambió.
 */
export async function reactivarSocio(idSocio: number, idUsuarioActor?: number): Promise<void> {
  await delay();

  const socio = socios.find((s) => s.id_socio === idSocio);
  if (!socio || socio.activo) {
    throw new ServiceError(400, 'El socio ya está activo');
  }

  socio.activo = true;
  const usuario = usuarios.find((u) => u.id_persona === socio.id_persona);
  if (usuario) {
    usuario.activo = true;
  }

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Socio',
    id_entidad: idSocio,
    accion: 'MODIFICACION',
    detalle: 'Reactivación',
  });
}
