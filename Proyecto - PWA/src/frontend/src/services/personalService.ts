// Sección Personal, conectada a la API real (routers/personal.py).
//
// EL ROL SIGUE SIENDO DERIVADO, PERO AHORA LO DERIVA EL BACKEND
// El tipo de empleado no es una columna: sale de en cuál de las cuatro tablas
// hijas (Entrenador / Nutricionista / Recepcionista / Profesor) existe su
// fila. Esa traversal la hacía este archivo recorriendo arrays; ahora la hace
// el servidor y el rol viaja resuelto en la respuesta.
//
// Y SON VARIOS: LOS ROLES SE ACUMULAN
// Los cuatro subtipos son SOLAPADOS en el esquema, así que la misma persona
// puede ser entrenadora y profesora a la vez. Este archivo hablaba de `rol` en
// singular porque el backend borraba la fila del rol viejo al cambiarlo —y con
// eso se llevaba puesto el trabajo hecho en ese rol, así que cambiar de rol
// respondía 409 a cualquiera con historial—. Desde el 2026-09-29 la fila se
// apaga en vez de borrarse, y la API habla de `roles` y `detalles` en plural.
//
// Por eso la vieja regla "no se puede cambiar el rol de alguien con rutinas o
// dietas a su nombre" ya no existe en ningún lado: no hay nada que romper.

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
  /**
   * Todos los roles que la persona cumple HOY, en el orden en que los devuelve
   * el backend. Puede tener más de uno; vacío sólo si se lo cargó sin función
   * asignada (el alta ya no lo permite).
   */
  roles: RolEmpleadoValue[];
  /**
   * Los datos propios de cada rol, indexados por rol. Cada uno en su casillero
   * porque son columnas distintas en tablas distintas: la especialidad del
   * entrenador y la del profesor no son el mismo dato, y aplanarlas hacía que
   * una pisara a la otra.
   */
  detalles: Partial<Record<RolEmpleadoValue, DetalleRol>>;
  estado: EstadoEmpleadoValue;
  activo: boolean;
  fechaIngreso: string;
  tieneCuenta: boolean;
}

/**
 * Los datos propios de UN rol, tal cual están en la base.
 *
 * `detalle` es para MOSTRAR (elige un campo con fallback); para precargar el
 * formulario hacen falta los campos exactos, o se guardaría la matrícula como
 * si fuera el título.
 */
export interface DetalleRol {
  titulo?: string;
  especialidad?: string;
  matricula?: string;
  /** Solo el recepcionista tiene franja: el nombre, para mostrar. */
  turno?: TurnoLaboralValue;
  /** Y su FK, para preseleccionar en el formulario. */
  idFranjaLaboral?: number;
  /** El campo que se muestra en el chip de la tarjeta, ya elegido. */
  detalle?: string;
}

/** La forma exacta en que responde el backend. */
interface DetalleRolApi {
  rol: string;
  titulo: string | null;
  especialidad: string | null;
  matricula: string | null;
  turno_laboral: string | null;      // nombre de la franja (para mostrar)
  id_franja_laboral: number | null;  // FK, para preseleccionar en el form
}

interface EmpleadoApi {
  id_empleado: number;
  id_persona: number;
  legajo: string | null;
  fecha_ingreso: string;
  fecha_egreso: string | null;
  activo: boolean;
  roles: string[];
  detalles: DetalleRolApi[];
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
 * El dato que la tarjeta muestra al lado de cada rol. Cada rol tiene el suyo, y
 * por eso no se puede resolver con un solo campo: un recepcionista no tiene
 * especialidad y un entrenador no tiene turno.
 */
function detalleDeRol(d: DetalleRolApi): string | undefined {
  switch (d.rol) {
    case RolEmpleado.RECEPCIONISTA:
      return d.turno_laboral ?? undefined;
    case RolEmpleado.ENTRENADOR:
    case RolEmpleado.PROFESOR:
      return d.especialidad ?? d.titulo ?? undefined;
    case RolEmpleado.NUTRICIONISTA:
      return d.titulo ?? d.matricula ?? undefined;
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
    roles: e.roles as RolEmpleadoValue[],
    detalles: Object.fromEntries(
      e.detalles.map((d) => [
        d.rol,
        {
          titulo: d.titulo ?? undefined,
          especialidad: d.especialidad ?? undefined,
          matricula: d.matricula ?? undefined,
          turno: (d.turno_laboral ?? undefined) as TurnoLaboralValue | undefined,
          idFranjaLaboral: d.id_franja_laboral ?? undefined,
          detalle: detalleDeRol(d),
        },
      ]),
    ),
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
  /** Todos los roles que tienen que quedar prendidos. Al menos uno. */
  roles: RolEmpleadoValue[];
  /** Entrenador y Profesor. */
  especialidad?: string;
  /** Nutricionista. */
  titulo?: string;
  /** Recepcionista: el id de la franja, tal como lo da el <select>. */
  idFranjaLaboral?: string;
}

/**
 * Qué campo propio pide cada rol en el formulario.
 *
 * La base guarda más columnas que las que se muestran —un Entrenador tiene
 * título, especialidad y matrícula—, pero acá se pide UNA por rol: la que el
 * mostrador realmente carga. Las otras las edita Flet, y el backend conserva
 * todo campo que no venga en el pedido, así que mostrar menos no borra nada.
 */
const CAMPO_DEL_ROL: Record<RolEmpleadoValue, 'especialidad' | 'titulo' | 'franja'> = {
  [RolEmpleado.ENTRENADOR]: 'especialidad',
  [RolEmpleado.PROFESOR]: 'especialidad',
  [RolEmpleado.NUTRICIONISTA]: 'titulo',
  [RolEmpleado.RECEPCIONISTA]: 'franja',
};

/**
 * Los campos que hay que mostrar para un conjunto de roles: la UNIÓN de los
 * que pide cada uno, sin repetir.
 *
 * Entrenador y Profesor piden los dos "Especialidad", y con dos inputs iguales
 * en pantalla nadie sabría cuál es cuál. Va uno solo y su valor se escribe en
 * las dos filas: es la misma especialidad de la misma persona, guardada dos
 * veces porque son dos tablas.
 */
export function camposDeRoles(roles: RolEmpleadoValue[]): ('especialidad' | 'titulo' | 'franja')[] {
  const orden = ['especialidad', 'titulo', 'franja'] as const;
  const pedidos = new Set(roles.map((r) => CAMPO_DEL_ROL[r]));
  return orden.filter((c) => pedidos.has(c));
}

/**
 * Traduce los campos del formulario a las columnas del pedido, y manda SÓLO
 * los que los roles elegidos usan.
 *
 * Lo que no viaja, el backend lo conserva (editar_empleado). Mandar todo
 * siempre era lo que hacía que editarle el teléfono a un entrenador desde acá
 * le borrara el título y la matrícula cargados desde Flet.
 */
function camposDelPedido(input: EmpleadoInput): Record<string, unknown> {
  const campos = camposDeRoles(input.roles);
  const cuerpo: Record<string, unknown> = {};
  if (campos.includes('especialidad')) cuerpo.especialidad = input.especialidad?.trim() || null;
  if (campos.includes('titulo')) cuerpo.titulo = input.titulo?.trim() || null;
  if (campos.includes('franja')) {
    cuerpo.id_franja_laboral = input.idFranjaLaboral ? Number(input.idFranjaLaboral) : null;
  }
  return cuerpo;
}

/**
 * Con qué precargar cada campo del formulario: el valor que ya tiene el primer
 * rol elegido que lo use.
 *
 * Tiene que salir de la columna EXACTA que se va a guardar y no del `detalle`
 * de la tarjeta, que elige un campo con fallback: a una nutricionista con
 * matrícula y sin título le precargaba la matrícula, y guardar la mudaba al
 * título.
 */
export function valoresDeRoles(
  empleado: EmpleadoListado | null,
  roles: RolEmpleadoValue[],
): { especialidad: string; titulo: string; idFranjaLaboral: string } {
  const de = (campo: 'especialidad' | 'titulo' | 'franja'): string => {
    if (!empleado) return '';
    for (const rol of roles) {
      if (CAMPO_DEL_ROL[rol] !== campo) continue;
      const d = empleado.detalles[rol];
      if (!d) continue;
      if (campo === 'especialidad' && d.especialidad) return d.especialidad;
      if (campo === 'titulo' && d.titulo) return d.titulo;
      if (campo === 'franja' && d.idFranjaLaboral) return String(d.idFranjaLaboral);
    }
    return '';
  };
  return { especialidad: de('especialidad'), titulo: de('titulo'), idFranjaLaboral: de('franja') };
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
      roles: input.roles,
      crear_cuenta: true,
      ...camposDelPedido(input),
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
 * Edita un empleado, incluidos sus roles.
 *
 * `roles` es el conjunto completo que tiene que quedar prendido: el backend
 * prende los que falten y apaga los que no vengan, sin borrar ninguna fila.
 * Ya no hay 409 por cambio de rol —antes lo había para cualquiera con rutinas,
 * socios a cargo u horarios a su nombre, porque el cambio BORRABA la fila del
 * rol viejo y todo ese historial apunta a ella—.
 *
 * Lo que sí cambia, y las pantallas lo avisan: sacarle el rol de Entrenador
 * FINALIZA sus asignaciones activas, así que el socio deja de verlo en "Mi
 * entrenador". La rutina que le armó queda asignada igual.
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
      roles: input.roles,
      ...camposDelPedido(input),
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
