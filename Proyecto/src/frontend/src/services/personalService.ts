// Mock de estructura_personal.md: grilla de tarjetas del personal, con alta
// y edición.
//
// La diferencia grande con el doc está en el modelo: el .py original tenía
// un dict con una key `rol` y otra `turno`, planas. El esquema real no —
// Empleado guarda lo común y el rol sale de en cuál de las tres tablas
// hijas (Entrenador / Nutricionista / Recepcionista) existe la fila. Este
// service es el que traduce entre las dos formas: hacia afuera expone un
// `rol` cómodo para la vista, y hacia adentro crea/mueve la fila hija que
// corresponda.
//
// Consecuencia importante: `turno` NO es un campo de todo empleado, es
// Recepcionista.turno_laboral. Los entrenadores tienen especialidad y los
// nutricionistas título; la tarjeta muestra el dato que cada rol realmente
// tiene, en vez de inventarle un turno a todos.

import type { Empleado, Persona } from '../types';
import {
  EstadoEmpleado,
  RolEmpleado,
  Roles,
  type EstadoEmpleadoValue,
  type RolEmpleadoValue,
  type RolValue,
  type TurnoLaboralValue,
} from '../config';
import { aFechaISO, aTimestampISO } from '../utils/fechas';
import { iniciales, nombreCompleto } from '../utils/personas';
import { ServiceError, delay } from './api';
import { registrarAuditoria } from './auditoriaService';
import { esEmailValido, limpiar } from './validacion';
import {
  personas,
  telefonos,
  sedes,
  empleados,
  entrenadores,
  nutricionistas,
  recepcionistas,
  rutinas,
  dietas,
  usuarios,
  siguienteId,
  proximoLegajo,
} from './mockDb';

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
  estado: EstadoEmpleadoValue;
  activo: boolean;
  fechaIngreso: string;
}

/**
 * Traduce el rol de empleado (derivado de las tablas hijas) al rol de
 * sesión que usa el login y la matriz de permisos. Son los mismos tres
 * roles vistos desde dos lados: RolEmpleado es la etiqueta de la ficha de
 * personal, Roles.* es el valor que viaja en la sesión.
 */
const ROL_SESION_POR_ROL_EMPLEADO: Record<RolEmpleadoValue, RolValue> = {
  [RolEmpleado.ENTRENADOR]: Roles.ENTRENADOR,
  [RolEmpleado.NUTRICIONISTA]: Roles.NUTRICIONISTA,
  [RolEmpleado.RECEPCIONISTA]: Roles.RECEPCIONISTA,
};

/**
 * Rol de sesión de un empleado, o null si no está en ninguna tabla hija
 * (empleado sin rol asignado). Lo usa usuariosService al crear una cuenta:
 * el rol NO se elige a mano en un dropdown, se deriva de lo que la persona
 * realmente es en el esquema.
 */
export function rolDeSesionDeEmpleado(idEmpleado: number): RolValue | null {
  const rol = resolverRol(idEmpleado);
  return rol ? ROL_SESION_POR_ROL_EMPLEADO[rol.rol] : null;
}

/**
 * Nombre completo de la persona detrás de un Empleado. Vive acá porque
 * personalService es la autoridad sobre Empleado — rutinasService y
 * nutricionService la usan para resolver "Entrenador a cargo" y
 * "Nutricionista a cargo" sin repetir la traversal Entrenador/Nutricionista
 * -> Empleado -> Persona.
 */
export function nombrePorEmpleado(idEmpleado: number): string {
  const empleado = empleados.find((e) => e.id_empleado === idEmpleado);
  const persona = empleado && personas.find((p) => p.id_persona === empleado.id_persona);
  return persona ? nombreCompleto(persona) : 'Sin asignar';
}

function telefonoPrincipal(idPersona: number): string | undefined {
  const propios = telefonos.filter((t) => t.id_persona === idPersona);
  return (propios.find((t) => t.principal) ?? propios[0])?.numero;
}

/**
 * Deriva el rol y su dato específico buscando la fila hija del empleado.
 * Devuelve null si no está en ninguna de las tres tablas: en el esquema eso
 * es un empleado sin rol asignado, que la vista simplemente no lista.
 */
function resolverRol(
  idEmpleado: number,
): { rol: RolEmpleadoValue; detalle?: string; turno?: TurnoLaboralValue } | null {
  const entrenador = entrenadores.find((e) => e.id_empleado === idEmpleado);
  if (entrenador) {
    return {
      rol: RolEmpleado.ENTRENADOR,
      detalle: entrenador.especialidad ?? entrenador.titulo,
    };
  }

  const nutricionista = nutricionistas.find((n) => n.id_empleado === idEmpleado);
  if (nutricionista) {
    return {
      rol: RolEmpleado.NUTRICIONISTA,
      detalle: nutricionista.titulo,
    };
  }

  const recepcionista = recepcionistas.find((r) => r.id_empleado === idEmpleado);
  if (recepcionista) {
    const turno = recepcionista.turno_laboral as TurnoLaboralValue | undefined;
    return {
      rol: RolEmpleado.RECEPCIONISTA,
      detalle: turno ? `Turno ${turno}` : undefined,
      turno,
    };
  }

  return null;
}

function aEmpleadoListado(empleado: Empleado, persona: Persona): EmpleadoListado | null {
  const rol = resolverRol(empleado.id_empleado);
  if (!rol) return null;

  return {
    idEmpleado: empleado.id_empleado,
    idPersona: persona.id_persona,
    legajo: empleado.legajo,
    dni: persona.dni,
    nombre: persona.nombre,
    apellido: persona.apellido,
    nombreCompleto: nombreCompleto(persona),
    iniciales: iniciales(persona),
    email: persona.email,
    telefono: telefonoPrincipal(persona.id_persona),
    rol: rol.rol,
    detalle: rol.detalle,
    turno: rol.turno,
    estado: empleado.activo ? EstadoEmpleado.ACTIVO : EstadoEmpleado.INACTIVO,
    activo: empleado.activo,
    fechaIngreso: empleado.fecha_ingreso,
  };
}

/**
 * Trae todo el personal. Igual que en socios, la búsqueda y el filtro por
 * rol los resuelve la vista en memoria: es un solo fetch por visita.
 */
export async function listarPersonal(): Promise<EmpleadoListado[]> {
  await delay();
  return empleados
    .map((empleado) => {
      const persona = personas.find((p) => p.id_persona === empleado.id_persona);
      return persona ? aEmpleadoListado(empleado, persona) : null;
    })
    .filter((e): e is EmpleadoListado => e !== null);
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
 * Un cambio de rol borra la fila hija anterior (ver asignarRol), pero esa
 * fila es el destino de claves foráneas NOT NULL: Rutina.id_entrenador y
 * Dieta.id_nutricionista. Sacarla dejaba esos registros apuntando a un id
 * que ya no existe — en la vista se veían como "Entrenador: Sin asignar", y
 * contra el Postgres real el DELETE directamente fallaría por violación de
 * FK.
 *
 * Así que se corta antes: si el empleado tiene trabajo a su nombre, el
 * cambio de rol se rechaza con un mensaje que dice qué hay que reasignar
 * primero. Es la misma regla que aplicaría la base.
 */
function validarCambioDeRol(idEmpleado: number, rolNuevo: RolEmpleadoValue): void {
  const rolActual = resolverRol(idEmpleado);
  if (!rolActual || rolActual.rol === rolNuevo) return;

  if (rolActual.rol === RolEmpleado.ENTRENADOR) {
    const entrenador = entrenadores.find((e) => e.id_empleado === idEmpleado);
    const propias = entrenador
      ? rutinas.filter((r) => r.id_entrenador === entrenador.id_entrenador).length
      : 0;
    if (propias > 0) {
      throw new ServiceError(
        409,
        `No se puede cambiar el rol: tiene ${propias} rutina(s) a su nombre. Reasignalas a otro entrenador primero.`,
      );
    }
  }

  if (rolActual.rol === RolEmpleado.NUTRICIONISTA) {
    const nutricionista = nutricionistas.find((n) => n.id_empleado === idEmpleado);
    const propios = nutricionista
      ? dietas.filter((d) => d.id_nutricionista === nutricionista.id_nutricionista).length
      : 0;
    if (propios > 0) {
      throw new ServiceError(
        409,
        `No se puede cambiar el rol: tiene ${propios} plan(es) nutricional(es) a su nombre. Reasignalos a otro nutricionista primero.`,
      );
    }
  }
}

/**
 * El rol de sesión se DERIVA de la tabla hija, pero el mock lo guarda
 * copiado en Usuario.rol (mockDb: "el rol todavía no es una tabla propia").
 * Si esa copia no se refresca al cambiar de rol, la ficha de Personal dice
 * una cosa y los permisos con los que la persona entra son otra: alguien
 * pasado a Recepcionista seguía navegando como Entrenador. Se resincroniza
 * acá, que es el único lugar donde el rol real cambia.
 */
function sincronizarRolDeUsuario(idEmpleado: number): void {
  const empleado = empleados.find((e) => e.id_empleado === idEmpleado);
  if (!empleado) return;
  const rolSesion = rolDeSesionDeEmpleado(idEmpleado);
  if (!rolSesion) return;
  const usuario = usuarios.find((u) => u.id_persona === empleado.id_persona);
  if (usuario) usuario.rol = rolSesion;
}

/**
 * Deja al empleado en la tabla hija que corresponde a `rol`, sacándolo de
 * la anterior si cambió. Es la contracara de resolverRol: un cambio de rol
 * en el esquema real no es actualizar una columna, es mover la fila de
 * tabla.
 */
function asignarRol(idEmpleado: number, rol: RolEmpleadoValue, detalle?: string): void {
  const quitarDe = <T extends { id_empleado: number }>(tabla: T[]): T | undefined => {
    const indice = tabla.findIndex((fila) => fila.id_empleado === idEmpleado);
    return indice >= 0 ? tabla.splice(indice, 1)[0] : undefined;
  };

  const entrenadorPrevio = quitarDe(entrenadores);
  const nutricionistaPrevio = quitarDe(nutricionistas);
  const recepcionistaPrevio = quitarDe(recepcionistas);

  switch (rol) {
    case RolEmpleado.ENTRENADOR:
      entrenadores.push({
        // Si ya era entrenador se conserva su id y su matrícula; solo se
        // reemplaza lo que el formulario edita.
        id_entrenador: entrenadorPrevio?.id_entrenador ?? siguienteId.entrenador(),
        id_empleado: idEmpleado,
        titulo: entrenadorPrevio?.titulo,
        especialidad: detalle,
        matricula: entrenadorPrevio?.matricula,
      });
      break;
    case RolEmpleado.NUTRICIONISTA:
      nutricionistas.push({
        id_nutricionista: nutricionistaPrevio?.id_nutricionista ?? siguienteId.nutricionista(),
        id_empleado: idEmpleado,
        titulo: detalle,
        matricula: nutricionistaPrevio?.matricula,
      });
      break;
    case RolEmpleado.RECEPCIONISTA:
      recepcionistas.push({
        id_recepcionista: recepcionistaPrevio?.id_recepcionista ?? siguienteId.recepcionista(),
        id_empleado: idEmpleado,
        turno_laboral: detalle,
      });
      break;
  }
}

/** Validaciones comunes al alta y a la edición. `idPersonaActual` se excluye de los chequeos de duplicado. */
function validarDatos(input: EmpleadoInput, idPersonaActual?: number): void {
  if (limpiar(input.nombre) === '' || limpiar(input.apellido) === '') {
    throw new ServiceError(400, 'Nombre y apellido son obligatorios');
  }

  const email = limpiar(input.email).toLowerCase();
  if (email && !esEmailValido(email)) {
    throw new ServiceError(400, 'El email no tiene un formato válido');
  }
  if (
    email &&
    personas.some((p) => p.id_persona !== idPersonaActual && p.email?.toLowerCase() === email)
  ) {
    throw new ServiceError(409, 'Ese email ya está en uso');
  }
}

export async function crearEmpleado(
  input: EmpleadoInput,
  idUsuarioActor?: number,
): Promise<EmpleadoListado> {
  await delay();

  const dni = limpiar(input.dni);
  if (dni === '') {
    throw new ServiceError(400, 'El DNI es obligatorio');
  }
  validarDatos(input);

  if (personas.some((p) => p.dni === dni)) {
    throw new ServiceError(409, 'Ya existe una persona con ese DNI');
  }

  const sede = sedes.find((s) => s.activo);
  if (!sede) {
    throw new ServiceError(500, 'No hay ninguna sede activa configurada');
  }

  const persona: Persona = {
    id_persona: siguienteId.persona(),
    dni,
    nombre: limpiar(input.nombre),
    apellido: limpiar(input.apellido),
    email: limpiar(input.email).toLowerCase() || undefined,
    fecha_alta: aTimestampISO(new Date()),
    activo: true,
  };
  personas.push(persona);

  const telefono = limpiar(input.telefono);
  if (telefono) {
    telefonos.push({
      id_telefono: siguienteId.telefono(),
      id_persona: persona.id_persona,
      numero: telefono,
      tipo: 'CELULAR',
      principal: true,
    });
  }

  const idEmpleado = siguienteId.empleado();
  const empleado: Empleado = {
    id_empleado: idEmpleado,
    id_persona: persona.id_persona,
    id_sede: sede.id_sede,
    legajo: proximoLegajo(idEmpleado),
    fecha_ingreso: aFechaISO(new Date()),
    activo: true,
  };
  empleados.push(empleado);

  asignarRol(idEmpleado, input.rol, limpiar(input.detalle) || undefined);

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Empleado',
    id_entidad: idEmpleado,
    accion: 'ALTA',
  });

  const listado = aEmpleadoListado(empleado, persona);
  if (!listado) {
    // Inalcanzable: asignarRol siempre deja al empleado en una tabla hija.
    throw new ServiceError(500, 'No se pudo determinar el rol del empleado');
  }
  return listado;
}

export async function actualizarEmpleado(
  idEmpleado: number,
  input: EmpleadoInput,
  idUsuarioActor?: number,
): Promise<EmpleadoListado> {
  await delay();

  const empleado = empleados.find((e) => e.id_empleado === idEmpleado);
  if (!empleado) {
    throw new ServiceError(404, 'El empleado no existe');
  }
  const persona = personas.find((p) => p.id_persona === empleado.id_persona);
  if (!persona) {
    throw new ServiceError(404, 'El empleado no existe');
  }

  validarDatos(input, persona.id_persona);
  // Antes de tocar nada: si el cambio de rol dejaría rutinas o dietas
  // huérfanas, se corta acá y el empleado queda como estaba.
  validarCambioDeRol(idEmpleado, input.rol);

  persona.nombre = limpiar(input.nombre);
  persona.apellido = limpiar(input.apellido);
  persona.email = limpiar(input.email).toLowerCase() || undefined;

  // Mismo criterio que en sociosService: el teléfono principal es un solo
  // campo del formulario, así que se reemplaza entero.
  const telefono = limpiar(input.telefono);
  const indicePrincipal = telefonos.findIndex(
    (t) => t.id_persona === persona.id_persona && t.principal,
  );
  if (telefono) {
    if (indicePrincipal >= 0) {
      telefonos[indicePrincipal].numero = telefono;
    } else {
      telefonos.push({
        id_telefono: siguienteId.telefono(),
        id_persona: persona.id_persona,
        numero: telefono,
        tipo: 'CELULAR',
        principal: true,
      });
    }
  } else if (indicePrincipal >= 0) {
    telefonos.splice(indicePrincipal, 1);
  }

  asignarRol(idEmpleado, input.rol, limpiar(input.detalle) || undefined);
  // El rol de la ficha y el rol con el que la persona inicia sesión son el
  // mismo dato: si acá cambió, la cuenta tiene que enterarse.
  sincronizarRolDeUsuario(idEmpleado);

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Empleado',
    id_entidad: idEmpleado,
    accion: 'MODIFICACION',
  });

  const listado = aEmpleadoListado(empleado, persona);
  if (!listado) {
    throw new ServiceError(500, 'No se pudo determinar el rol del empleado');
  }
  return listado;
}

// --- Baja ---
//
// No está en estructura_personal.md (el doc solo tiene alta/edición/
// contactar), pero Empleado sí tiene fecha_egreso/activo en el esquema —
// mismo criterio que sociosService: se marca inactivo y se guarda la fecha
// de egreso, nunca se borra la fila (rompería el historial de auditoría).
// La fila del rol (Entrenador/Nutricionista/Recepcionista) queda intacta:
// un empleado dado de baja sigue teniendo el rol que tenía, solo que ya no
// está activo.
export async function darDeBajaEmpleado(
  idEmpleado: number,
  motivo?: string,
  idUsuarioActor?: number,
): Promise<void> {
  await delay();

  const empleado = empleados.find((e) => e.id_empleado === idEmpleado);
  if (!empleado || !empleado.activo) {
    throw new ServiceError(400, 'El empleado no está activo');
  }

  empleado.activo = false;
  empleado.fecha_egreso = aFechaISO(new Date());

  // Igual que la baja de socio (authService.darDeBaja), la baja arrastra el
  // acceso: un empleado que ya no trabaja acá no tiene por qué seguir
  // entrando al panel. Sin esto la baja era puramente cosmética — la ficha
  // decía "Inactivo" y la persona seguía iniciando sesión con todos los
  // permisos de su rol, que es el agujero clásico de offboarding.
  const usuario = usuarios.find((u) => u.id_persona === empleado.id_persona);
  if (usuario) {
    usuario.activo = false;
  }

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Empleado',
    id_entidad: idEmpleado,
    accion: 'BAJA',
    detalle: limpiar(motivo) || undefined,
  });
}

/**
 * Camino de vuelta de darDeBajaEmpleado: reactiva y limpia fecha_egreso (si
 * está activo, no tiene sentido conservar una fecha de egreso). La fila del
 * rol no se toca — igual que en la baja, sigue teniendo el mismo rol que
 * tenía. No hay 'REACTIVACION' en Auditoria.accion, se audita como
 * MODIFICACION con el detalle aclarando qué cambió.
 */
export async function reactivarEmpleado(
  idEmpleado: number,
  idUsuarioActor?: number,
): Promise<void> {
  await delay();

  const empleado = empleados.find((e) => e.id_empleado === idEmpleado);
  if (!empleado || empleado.activo) {
    throw new ServiceError(400, 'El empleado ya está activo');
  }

  empleado.activo = true;
  empleado.fecha_egreso = undefined;

  // Camino de vuelta del acceso, simétrico a la baja.
  const usuario = usuarios.find((u) => u.id_persona === empleado.id_persona);
  if (usuario) {
    usuario.activo = true;
  }

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Empleado',
    id_entidad: idEmpleado,
    accion: 'MODIFICACION',
    detalle: 'Reactivación',
  });
}
