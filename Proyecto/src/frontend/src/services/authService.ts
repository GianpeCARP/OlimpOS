// Mock de auth.spec.md (3.1 registro, 3.2 login, 3.3 baja).
//
// Los datos no viven acá: están en mockDb.ts, compartidos con el resto de
// los services. El día que exista la API de FastAPI, estas funciones cambian
// de cuerpo (fetch en vez de arrays) y nada del lado de las vistas o el
// store se toca, porque las firmas ya son las definitivas.

import type { Persona, Usuario, Telefono, Socio, Sede, Baja } from '../types';
import { Roles } from '../config';
import { aFechaISO, aTimestampISO } from '../utils/fechas';
import { ServiceError, delay, pedir } from './api';
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
//
// DESCONECTADO — no lo llama nadie, y no hay que volver a conectarlo.
// La pantalla, la ruta y la acción del store se eliminaron porque la consigna
// prohíbe el auto-registro en un sistema interno (ver config.ts y
// backend/README.md). Se conserva el cuerpo de la función solo como
// referencia de las validaciones y del orden de inserción
// (Persona -> Usuario -> Telefono -> Socio), que es lo que va a tener que
// replicar el endpoint de alta por parte del personal.
//
// Ojo con la diferencia al portarlo: en el alta por invitación el socio NO
// elige su username ni su password — el backend genera una contraseña
// temporal y marca debe_cambiar_password.

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

/**
 * Credenciales correctas, pero la cuenta todavía tiene su contraseña
 * temporal. NO hay sesión: el backend verificó la contraseña y aun así se
 * negó a emitir un token hasta que la persona defina una propia.
 *
 * Se llega acá en tres casos, todos el mismo mecanismo: el primer ingreso de
 * una cuenta recién creada por el personal, el primer ingreso del dueño
 * (cuenta del seeder), y el reingreso después de que un admin resetee la
 * clave.
 */
export interface CambioRequerido {
  debeCambiarPassword: true;
}

/**
 * Unión discriminada, no un objeto con campos opcionales: así TypeScript
 * OBLIGA a chequear `debeCambiarPassword` antes de tocar `token` o `roles`.
 * Con campos opcionales, olvidarse del caso compilaría igual y el bug
 * aparecería recién en runtime, con la sesión a medio abrir.
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

  // Todo lo demás lo decide el backend: el mensaje único para credenciales
  // inválidas (que no revela si el usuario existe) y el bloqueo a los cinco
  // intentos ahora viven en routers/auth_router.py. Estaban acá cuando esta
  // capa hacía de API; ahora duplicarlos sería peor que no tenerlos, porque
  // el mock podría decir una cosa y el servidor otra.
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
 * Reconstruye la sesión a partir del token guardado. Es lo que hace que un F5
 * no cierre la sesión.
 *
 * Devuelve los mismos datos que el login pero SIN token, porque el cliente ya
 * lo tiene. Lanza ServiceError 401 si el token venció, fue alterado, o la
 * cuenta se desactivó desde que se emitió — en cualquiera de esos casos hay
 * que volver al login.
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
