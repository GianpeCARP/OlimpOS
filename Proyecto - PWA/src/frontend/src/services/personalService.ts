// Sección Personal, conectada a la API real (routers/personal.py).
//
// EL ROL SIGUE SIENDO DERIVADO, PERO AHORA LO DERIVA EL BACKEND
// El tipo de empleado no es una columna: sale de en cuál de las cuatro tablas
// hijas (Entrenador / Nutricionista / Recepcionista / Profesor) existe su
// fila. Esa traversal la hacía este archivo recorriendo arrays; ahora la hace
// el servidor y el rol viaja resuelto en la respuesta.
//
// Se ganó algo concreto con la mudanza: la regla que impide cambiar el rol de
// alguien que tiene rutinas o dietas a su nombre ahora corre del lado del
// servidor. Antes vivía sólo acá, y su propio comentario advertía que "contra
// el Postgres real el DELETE directamente fallaría por violación de FK" — o
// sea, la regla existía en el mock pero nada la habría hecho valer en
// producción.

import type { RolEmpleadoValue, TurnoLaboralValue, EstadoEmpleadoValue } from '../config';
import { EstadoEmpleado, RolEmpleado } from '../config';
import { pedir } from './api';

// --- Listado ---

export interface EmpleadoListado {
  idEmpleado: number;
  idPersona: number;
  legajo?: string;
  dni: string;
  nombre: string;
  apellido: string;
  nombreCompleto: string;
  iniciales: string;
  email?: string;
  telefono?: string;
  rol: RolEmpleadoValue;
  /**
   * Dato propio del rol, listo para mostrar: el turno del recepcionista, la
   * especialidad del entrenador, el título del nutricionista. Undefined si
   * ese empleado no lo tiene cargado (todas esas columnas son nullable).
   */
  detalle?: string;
  /** Solo los recepcionistas tienen turno — ver comentario de arriba. */
  turno?: TurnoLaboralValue;
  /** FK a la franja del recepcionista, para preseleccionar en el form. */
  idFranjaLaboral?: number;
  /**
   * Los datos del rol tal cual están en la base. `detalle` es para MOSTRAR
   * (elige uno con fallback); para precargar el formulario hace falta el campo
   * exacto, o se guardaría la matrícula como si fuera el título.
   */
  titulo?: string;
  especialidad?: string;
  matricula?: string;
  estado: EstadoEmpleadoValue;
  activo: boolean;
  fechaIngreso: string;
  tieneCuenta: boolean;
}

/** La forma exacta en que responde el backend. */
interface EmpleadoApi {
  id_empleado: number;
  id_persona: number;
  legajo: string | null;
  fecha_ingreso: string;
  fecha_egreso: string | null;
  activo: boolean;
  rol: string | null;
  titulo: string | null;
  especialidad: string | null;
  matricula: string | null;
  turno_laboral: string | null;      // nombre de la franja (para mostrar)
  id_franja_laboral: number | null;  // FK, para preseleccionar en el form
  dni: string;
  nombre: string;
  apellido: string;
  email: string | null;
  // Aplanado por el backend desde la tabla Telefono (el principal). Viene
  // también en el listado: sin él, el botón de contactar no tendría a dónde
  // escribir y editar un empleado le borraba el teléfono al guardar.
  telefono: string | null;
  tiene_cuenta: boolean;
}

/**
 * El dato que la tarjeta muestra debajo del nombre. Cada rol tiene el suyo, y
 * por eso no se puede resolver con un solo campo: un recepcionista no tiene
 * especialidad y un entrenador no tiene turno.
 */
function detalleDeRol(e: EmpleadoApi): string | undefined {
  switch (e.rol) {
    case RolEmpleado.RECEPCIONISTA:
      return e.turno_laboral ?? undefined;
    case RolEmpleado.ENTRENADOR:
    case RolEmpleado.PROFESOR:
      return e.especialidad ?? e.titulo ?? undefined;
    case RolEmpleado.NUTRICIONISTA:
      return e.titulo ?? e.matricula ?? undefined;
    default:
      return undefined;
  }
}

function iniciales(nombre: string, apellido: string): string {
  return ((nombre.trim()[0] ?? '') + (apellido.trim()[0] ?? '')).toUpperCase() || '?';
}

function aEmpleadoListado(e: EmpleadoApi): EmpleadoListado {
  return {
    idEmpleado: e.id_empleado,
    idPersona: e.id_persona,
    legajo: e.legajo ?? undefined,
    dni: e.dni,
    nombre: e.nombre,
    apellido: e.apellido,
    nombreCompleto: `${e.nombre} ${e.apellido}`.trim(),
    iniciales: iniciales(e.nombre, e.apellido),
    email: e.email ?? undefined,
    telefono: e.telefono ?? undefined,
    // Un empleado sin fila en ninguna hija es alguien cargado a quien
    // todavía no se le asignó función. Se lo muestra como Recepcionista
    // —el rol más genérico— en vez de romper la tarjeta con undefined.
    rol: (e.rol ?? RolEmpleado.RECEPCIONISTA) as RolEmpleadoValue,
    detalle: detalleDeRol(e),
    turno: (e.turno_laboral ?? undefined) as TurnoLaboralValue | undefined,
    idFranjaLaboral: e.id_franja_laboral ?? undefined,
    titulo: e.titulo ?? undefined,
    especialidad: e.especialidad ?? undefined,
    matricula: e.matricula ?? undefined,
    estado: e.activo ? EstadoEmpleado.ACTIVO : EstadoEmpleado.INACTIVO,
    activo: e.activo,
    fechaIngreso: e.fecha_ingreso,
    tieneCuenta: e.tiene_cuenta,
  };
}

export async function listarPersonal(): Promise<EmpleadoListado[]> {
  const datos = await pedir<EmpleadoApi[]>('/personal');
  return datos.map(aEmpleadoListado);
}

export async function obtenerEmpleado(idEmpleado: number): Promise<EmpleadoListado> {
  const datos = await pedir<EmpleadoApi>(`/personal/${idEmpleado}`);
  return aEmpleadoListado(datos);
}

// --- Alta y edición ---

export interface EmpleadoInput {
  dni: string;
  nombre: string;
  apellido: string;
  email?: string;
  telefono?: string;
  rol: RolEmpleadoValue;
  /** Turno (recepcionista), especialidad (entrenador) o título (nutricionista). */
  detalle?: string;
}

/**
 * Pone el campo único `detalle` del formulario en la columna que corresponde
 * a cada rol, y SÓLO en esa.
 *
 * El formulario tiene UN campo porque para el usuario es "el dato de este
 * rol", pero en el esquema son columnas distintas en tablas distintas. La
 * traducción vive acá y no en el componente para que el formulario no tenga
 * que saber cómo está modelada la base.
 *
 * Los campos que el formulario no muestra NO viajan: el backend conserva lo
 * que no viene en el pedido (editar_empleado). Antes se mandaban en null, y
 * editarle el teléfono a un entrenador le borraba el título y la matrícula
 * cargados desde Flet.
 */
function repartirDetalle(rol: RolEmpleadoValue, detalle?: string) {
  const valor = detalle?.trim() || null;
  switch (rol) {
    case RolEmpleado.RECEPCIONISTA:
      // El turno del recepcionista ahora es una FK a Franja_Laboral: `detalle`
      // trae el id de la franja elegida (ver listarFranjas y el formulario).
      return { id_franja_laboral: valor ? Number(valor) : null };
    case RolEmpleado.NUTRICIONISTA:
      return { titulo: valor };
    default: // Entrenador y Profesor
      return { especialidad: valor };
  }
}

/**
 * El valor con que el formulario precarga el campo del rol: la columna exacta
 * que `repartirDetalle` va a escribir. No sirve `detalle`, que es el de la
 * tarjeta y cae a otra columna si la primera está vacía —a una nutricionista
 * con matrícula y sin título le precargaba la matrícula, y guardar la mudaba
 * al título—.
 */
export function detalleEditable(e: EmpleadoListado): string {
  switch (e.rol) {
    case RolEmpleado.RECEPCIONISTA:
      return e.idFranjaLaboral ? String(e.idFranjaLaboral) : '';
    case RolEmpleado.NUTRICIONISTA:
      return e.titulo ?? '';
    default: // Entrenador y Profesor
      return e.especialidad ?? '';
  }
}

/**
 * Catálogo de franjas laborales, para el selector de turno del recepcionista.
 * Reemplaza al viejo enum de turnos hardcodeado: ahora son filas reales.
 */
export interface FranjaOpcion {
  idFranjaLaboral: number;
  nombre: string;
}

interface FranjaApi {
  id_franja_laboral: number;
  nombre: string;
}

export async function listarFranjas(): Promise<FranjaOpcion[]> {
  const datos = await pedir<FranjaApi[]>('/personal/franjas');
  return datos.map((f) => ({ idFranjaLaboral: f.id_franja_laboral, nombre: f.nombre }));
}

export interface AltaEmpleadoResultado {
  empleado: EmpleadoListado;
  username?: string;
  passwordTemporal?: string;
  mensaje: string;
  emailEnviado: boolean;
  textoCredenciales?: string;
}

interface AltaEmpleadoApi {
  id_empleado: number;
  legajo: string;
  username: string | null;
  password_temporal: string | null;
  mensaje: string;
  email_enviado: boolean;
  texto_credenciales: string | null;
}

/**
 * Alta de empleado. El backend crea Persona + Empleado + su especialidad en
 * una transacción, y genera las credenciales si se pidió crear cuenta.
 *
 * Los CUATRO roles pueden tenerla. Hasta el 2026-09-16 el Profesor quedaba
 * afuera —"da clases, no usa el sistema"— y el alta ignoraba la casilla
 * avisándolo en el mensaje; el efecto real era que no tenía dónde ver su
 * horario ni quién se anotó a su clase. Ahora tiene cuenta y su propia
 * pantalla ("Mis clases"). Ver Rol.PROFESOR en el backend.
 *
 * `username` y `passwordTemporal` siguen siendo opcionales: vienen en null si
 * no se pidió cuenta.
 */
export async function crearEmpleado(input: EmpleadoInput): Promise<AltaEmpleadoResultado> {
  const datos = await pedir<AltaEmpleadoApi>('/personal', {
    metodo: 'POST',
    cuerpo: {
      dni: input.dni.trim(),
      nombre: input.nombre.trim(),
      apellido: input.apellido.trim(),
      email: input.email?.trim() || null,
      telefono: input.telefono?.trim() || null,
      id_sede: 1,
      rol: input.rol,
      crear_cuenta: true,
      ...repartirDetalle(input.rol, input.detalle),
    },
  });

  const empleado = await obtenerEmpleado(datos.id_empleado);

  return {
    empleado,
    username: datos.username ?? undefined,
    passwordTemporal: datos.password_temporal ?? undefined,
    mensaje: datos.mensaje,
    emailEnviado: datos.email_enviado,
    textoCredenciales: datos.texto_credenciales ?? undefined,
  };
}

/**
 * Edita un empleado, incluido su rol.
 *
 * Si el cambio de rol dejaría rutinas o dietas huérfanas, el backend responde
 * 409 con un mensaje que dice cuántas hay que reasignar. Esa validación tiene
 * que estar del lado del servidor: la fila del rol es destino de claves
 * foráneas NOT NULL, así que sin ella el DELETE fallaría con un error de
 * Postgres incomprensible en pantalla.
 */
export async function actualizarEmpleado(
  idEmpleado: number,
  input: EmpleadoInput,
): Promise<EmpleadoListado> {
  const datos = await pedir<EmpleadoApi>(`/personal/${idEmpleado}`, {
    metodo: 'PUT',
    cuerpo: {
      nombre: input.nombre.trim(),
      apellido: input.apellido.trim(),
      email: input.email?.trim() || null,
      telefono: input.telefono?.trim() ?? null,
      rol: input.rol,
      ...repartirDetalle(input.rol, input.detalle),
    },
  });
  return aEmpleadoListado(datos);
}

// --- Baja ---
//
// Baja lógica, igual que con los socios: se marca inactivo y se guarda la
// fecha de egreso. La fila del rol queda intacta —alguien dado de baja sigue
// habiendo sido entrenador, y sus rutinas siguen atribuidas a él— y la cuenta
// de acceso se desactiva. Sin eso la baja sería cosmética: la ficha diría
// "Inactivo" y la persona seguiría entrando con todos los permisos de su rol.

export async function darDeBajaEmpleado(
  idEmpleado: number,
  motivo?: string,
): Promise<EmpleadoListado> {
  const datos = await pedir<EmpleadoApi>(`/personal/${idEmpleado}/baja`, {
    metodo: 'POST',
    cuerpo: { motivo: motivo?.trim() || null },
  });
  return aEmpleadoListado(datos);
}

export async function reactivarEmpleado(idEmpleado: number): Promise<EmpleadoListado> {
  const datos = await pedir<EmpleadoApi>(`/personal/${idEmpleado}/reactivar`, { metodo: 'POST' });
  return aEmpleadoListado(datos);
}
