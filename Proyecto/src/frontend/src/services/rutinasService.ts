// Mock de estructura_rutinas.md: grilla de tarjetas de rutinas, con alta,
// edición y detalle de solo lectura.
//
// Dos diferencias con el doc, las dos porque Rutina no tiene esas columnas
// en db/schema.sql:
//
// 1. El doc pide un campo "duración en min" y otro "descripción" (textarea).
//    Rutina no tiene ninguna de las dos columnas — lo único de texto libre
//    es `objetivo` (varchar(100)). En vez de inventar una columna que no
//    existe, `objetivo` hace las dos cosas: es el pill de la tarjeta que el
//    doc llamaba "duración" y el campo de texto del formulario que el doc
//    llamaba "descripción".
// 2. El doc no tiene selector de entrenador en el alta — pero
//    Rutina.id_entrenador es NOT NULL. Se agregó un campo obligatorio
//    "Entrenador a cargo", con las mismas opciones que ya existen en
//    personalService (los entrenadores activos).
//
// "Asignar" queda como stub, tal cual lo describe el doc ("snack
// próximamente"): asignar una rutina a un socio necesita una pantalla de
// selección de socio que no es parte de esta spec.

import type { Rutina } from '../types';
import {
  CAPACIDAD_MAXIMA_RUTINA,
  EstadoRutina,
  type EstadoRutinaValue,
  type NivelRutinaValue,
} from '../config';
import { aFechaISO } from '../utils/fechas';
import { ServiceError, delay } from './api';
import { registrarAuditoria } from './auditoriaService';
import { nombrePorEmpleado } from './personalService';
import { limpiar } from './validacion';
import { entrenadores, empleados, rutinas, asignacionesRutina, siguienteId } from './mockDb';

// --- Listado ---

export interface RutinaListado {
  idRutina: number;
  nombre: string;
  nivel?: NivelRutinaValue;
  objetivo?: string;
  diasPorSemana?: number;
  asignados: number;
  /** 0..1, ya recortado a 1 — listo para el ancho de la barra de progreso. */
  progreso: number;
  idEntrenador: number;
  entrenador: string;
  fechaCreacion: string;
  activo: boolean;
  estado: EstadoRutinaValue;
}

function nombreEntrenador(idEntrenador: number): string {
  const entrenador = entrenadores.find((e) => e.id_entrenador === idEntrenador);
  return entrenador ? nombrePorEmpleado(entrenador.id_empleado) : 'Sin asignar';
}

/** Cuántas asignaciones ACTIVA tiene la rutina — FINALIZADA/CANCELADA no cuentan como socios asignados hoy. */
function asignadosActivos(idRutina: number): number {
  return asignacionesRutina.filter((a) => a.id_rutina === idRutina && a.estado === 'ACTIVA').length;
}

function aRutinaListado(rutina: Rutina): RutinaListado {
  const asignados = asignadosActivos(rutina.id_rutina);
  return {
    idRutina: rutina.id_rutina,
    nombre: rutina.nombre,
    nivel: rutina.nivel as NivelRutinaValue | undefined,
    objetivo: rutina.objetivo,
    diasPorSemana: rutina.dias_por_semana,
    asignados,
    progreso: Math.min(asignados / CAPACIDAD_MAXIMA_RUTINA, 1),
    idEntrenador: rutina.id_entrenador,
    entrenador: nombreEntrenador(rutina.id_entrenador),
    fechaCreacion: rutina.fecha_creacion,
    activo: rutina.activo,
    estado: rutina.activo ? EstadoRutina.ACTIVA : EstadoRutina.INACTIVA,
  };
}

export async function listarRutinas(): Promise<RutinaListado[]> {
  await delay();
  return rutinas.map(aRutinaListado);
}

// --- Entrenadores para el selector del formulario ---

export interface EntrenadorOpcion {
  idEntrenador: number;
  nombre: string;
}

/** Solo entrenadores con el empleado activo: no tiene sentido asignar una rutina nueva a alguien que ya no trabaja acá. */
export async function listarEntrenadoresActivos(): Promise<EntrenadorOpcion[]> {
  await delay();
  return entrenadores
    .filter((e) => empleados.find((emp) => emp.id_empleado === e.id_empleado)?.activo)
    .map((e) => ({ idEntrenador: e.id_entrenador, nombre: nombreEntrenador(e.id_entrenador) }));
}

// --- Alta y edición ---

export interface RutinaInput {
  nombre: string;
  nivel: NivelRutinaValue;
  diasPorSemana: number;
  objetivo?: string;
  idEntrenador: number;
}

const DIAS_MIN = 1;
const DIAS_MAX = 7;

function validar(input: RutinaInput): void {
  if (limpiar(input.nombre) === '') {
    throw new ServiceError(400, 'El nombre de la rutina es obligatorio');
  }
  if (!Number.isInteger(input.diasPorSemana) || input.diasPorSemana < DIAS_MIN || input.diasPorSemana > DIAS_MAX) {
    throw new ServiceError(400, `Los días por semana deben estar entre ${DIAS_MIN} y ${DIAS_MAX}`);
  }
  if (!entrenadores.some((e) => e.id_entrenador === input.idEntrenador)) {
    throw new ServiceError(400, 'El entrenador a cargo no existe');
  }
}

export async function crearRutina(
  input: RutinaInput,
  idUsuarioActor?: number,
): Promise<RutinaListado> {
  await delay();
  validar(input);

  const idRutina = siguienteId.rutina();
  const rutina: Rutina = {
    id_rutina: idRutina,
    id_entrenador: input.idEntrenador,
    nombre: limpiar(input.nombre),
    objetivo: limpiar(input.objetivo) || undefined,
    nivel: input.nivel,
    dias_por_semana: input.diasPorSemana,
    fecha_creacion: aFechaISO(new Date()),
    activo: true,
  };
  rutinas.push(rutina);

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Rutina',
    id_entidad: idRutina,
    accion: 'ALTA',
  });

  return aRutinaListado(rutina);
}

export async function actualizarRutina(
  idRutina: number,
  input: RutinaInput,
  idUsuarioActor?: number,
): Promise<RutinaListado> {
  await delay();
  validar(input);

  const rutina = rutinas.find((r) => r.id_rutina === idRutina);
  if (!rutina) {
    throw new ServiceError(404, 'La rutina no existe');
  }

  rutina.nombre = limpiar(input.nombre);
  rutina.objetivo = limpiar(input.objetivo) || undefined;
  rutina.nivel = input.nivel;
  rutina.dias_por_semana = input.diasPorSemana;
  rutina.id_entrenador = input.idEntrenador;

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Rutina',
    id_entidad: idRutina,
    accion: 'MODIFICACION',
  });

  return aRutinaListado(rutina);
}

// --- Baja ---
//
// No está en estructura_rutinas.md, pero Rutina sí tiene `activo` en el
// esquema — mismo criterio que socios/personal: se marca inactiva, nunca
// se borra la fila. A diferencia de esos dos, Rutina no tiene fecha_baja ni
// motivo en el esquema, así que acá no hay nada más que guardar.
//
// Las asignaciones (Asignacion_Rutina) existentes no se tocan: dar de baja
// el plan no cancela retroactivamente lo que ya se le asignó a un socio.
export async function darDeBajaRutina(
  idRutina: number,
  idUsuarioActor?: number,
): Promise<void> {
  await delay();

  const rutina = rutinas.find((r) => r.id_rutina === idRutina);
  if (!rutina || !rutina.activo) {
    throw new ServiceError(400, 'La rutina no está activa');
  }

  rutina.activo = false;

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Rutina',
    id_entidad: idRutina,
    accion: 'BAJA',
  });
}

/**
 * Camino de vuelta de darDeBajaRutina: no hay 'REACTIVACION' en
 * Auditoria.accion (el enum del esquema es ALTA/MODIFICACION/BAJA/CONSULTA/
 * LOGIN), así que se audita como MODIFICACION con el detalle aclarando qué
 * cambió — igual que se auditaría cualquier otro cambio de atributo.
 */
export async function activarRutina(
  idRutina: number,
  idUsuarioActor?: number,
): Promise<RutinaListado> {
  await delay();

  const rutina = rutinas.find((r) => r.id_rutina === idRutina);
  if (!rutina) {
    throw new ServiceError(404, 'La rutina no existe');
  }
  if (rutina.activo) {
    throw new ServiceError(400, 'La rutina ya está activa');
  }

  rutina.activo = true;

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Rutina',
    id_entidad: idRutina,
    accion: 'MODIFICACION',
    detalle: 'Reactivación',
  });

  return aRutinaListado(rutina);
}
