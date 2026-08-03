// Mock de estructura_nutricion.md: grilla de planes nutricionales, con
// alta, edición, baja/reactivación y detalle de solo lectura.
//
// Dos diferencias con el doc:
//
// 1. El doc pide una fila triple de macros (proteínas/carbos/grasas en
//    gramos) en el alta, y el detalle muestra una distribución fija de
//    30/50/20 vía _macro_bar — pero Dieta no tiene NINGUNA columna de
//    macros en db/schema.sql, y el 30/50/20 del doc es un valor fijo igual
//    para cualquier plan, no un dato real por plan. Replicarlo sería
//    inventar información. En su lugar, el detalle muestra las Comida
//    reales cargadas para ese plan (tabla que sí existe) — si no hay
//    ninguna cargada todavía (no existe un editor de comidas, tampoco en
//    el doc), se muestra el estado vacío real.
// 2. El doc no tiene selector de nutricionista en el alta — pero
//    Dieta.id_nutricionista es NOT NULL. Se agregó "Nutricionista a cargo",
//    mismo criterio que "Entrenador a cargo" en rutinasService.
//
// A diferencia de Rutina, Dieta sí tiene `descripcion` como columna propia
// — no hace falta reusar `objetivo` para dos cosas.

import type { Dieta } from '../types';
import { EstadoDieta, type EstadoDietaValue, type ObjetivoDietaValue } from '../config';
import { aFechaISO } from '../utils/fechas';
import { ServiceError, delay } from './api';
import { registrarAuditoria } from './auditoriaService';
import { nombrePorEmpleado } from './personalService';
import { limpiar } from './validacion';
import {
  nutricionistas,
  empleados,
  dietas,
  comidas,
  asignacionesDieta,
  siguienteId,
} from './mockDb';

// --- Listado ---

export interface PlanListado {
  idDieta: number;
  nombre: string;
  objetivo?: ObjetivoDietaValue;
  caloriasDiarias?: number;
  descripcion?: string;
  asignados: number;
  idNutricionista: number;
  nutricionista: string;
  fechaCreacion: string;
  activo: boolean;
  estado: EstadoDietaValue;
}

function nombreNutricionista(idNutricionista: number): string {
  const nutricionista = nutricionistas.find((n) => n.id_nutricionista === idNutricionista);
  return nutricionista ? nombrePorEmpleado(nutricionista.id_empleado) : 'Sin asignar';
}

/** Cuántas asignaciones ACTIVA tiene el plan — FINALIZADA/CANCELADA no cuentan como socios asignados hoy. */
function asignadosActivos(idDieta: number): number {
  return asignacionesDieta.filter((a) => a.id_dieta === idDieta && a.estado === 'ACTIVA').length;
}

function aPlanListado(dieta: Dieta): PlanListado {
  return {
    idDieta: dieta.id_dieta,
    nombre: dieta.nombre,
    objetivo: dieta.objetivo as ObjetivoDietaValue | undefined,
    caloriasDiarias: dieta.calorias_diarias,
    descripcion: dieta.descripcion,
    asignados: asignadosActivos(dieta.id_dieta),
    idNutricionista: dieta.id_nutricionista,
    nutricionista: nombreNutricionista(dieta.id_nutricionista),
    fechaCreacion: dieta.fecha_creacion,
    activo: dieta.activo,
    estado: dieta.activo ? EstadoDieta.ACTIVA : EstadoDieta.INACTIVA,
  };
}

export async function listarPlanes(): Promise<PlanListado[]> {
  await delay();
  return dietas.map(aPlanListado);
}

// --- Nutricionistas para el selector del formulario ---

export interface NutricionistaOpcion {
  idNutricionista: number;
  nombre: string;
}

/** Solo nutricionistas con el empleado activo — mismo criterio que listarEntrenadoresActivos. */
export async function listarNutricionistasActivos(): Promise<NutricionistaOpcion[]> {
  await delay();
  return nutricionistas
    .filter((n) => empleados.find((e) => e.id_empleado === n.id_empleado)?.activo)
    .map((n) => ({ idNutricionista: n.id_nutricionista, nombre: nombreNutricionista(n.id_nutricionista) }));
}

// --- Comidas del plan, para el detalle ---

export interface ComidaListada {
  idComida: number;
  dia?: number;
  momento?: string;
  descripcion: string;
  calorias?: number;
}

/** Ordenadas por día y luego por el orden en que aparecen en la tabla (mismo orden de carga = orden del día). */
export async function listarComidasDelPlan(idDieta: number): Promise<ComidaListada[]> {
  await delay();
  return comidas
    .filter((c) => c.id_dieta === idDieta)
    .sort((a, b) => (a.dia ?? 0) - (b.dia ?? 0))
    .map((c) => ({
      idComida: c.id_comida,
      dia: c.dia,
      momento: c.momento,
      descripcion: c.descripcion,
      calorias: c.calorias,
    }));
}

// --- Alta y edición ---

export interface PlanInput {
  nombre: string;
  objetivo: ObjetivoDietaValue;
  caloriasDiarias: number;
  descripcion?: string;
  idNutricionista: number;
}

const CALORIAS_MIN = 800;
const CALORIAS_MAX = 6000;

function validar(input: PlanInput): void {
  if (limpiar(input.nombre) === '') {
    throw new ServiceError(400, 'El nombre del plan es obligatorio');
  }
  if (
    !Number.isFinite(input.caloriasDiarias) ||
    input.caloriasDiarias < CALORIAS_MIN ||
    input.caloriasDiarias > CALORIAS_MAX
  ) {
    throw new ServiceError(400, `Las calorías diarias deben estar entre ${CALORIAS_MIN} y ${CALORIAS_MAX}`);
  }
  if (!nutricionistas.some((n) => n.id_nutricionista === input.idNutricionista)) {
    throw new ServiceError(400, 'El nutricionista a cargo no existe');
  }
}

export async function crearPlan(
  input: PlanInput,
  idUsuarioActor?: number,
): Promise<PlanListado> {
  await delay();
  validar(input);

  const idDieta = siguienteId.dieta();
  const dieta: Dieta = {
    id_dieta: idDieta,
    id_nutricionista: input.idNutricionista,
    nombre: limpiar(input.nombre),
    objetivo: input.objetivo,
    calorias_diarias: input.caloriasDiarias,
    descripcion: limpiar(input.descripcion) || undefined,
    fecha_creacion: aFechaISO(new Date()),
    activo: true,
  };
  dietas.push(dieta);

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Dieta',
    id_entidad: idDieta,
    accion: 'ALTA',
  });

  return aPlanListado(dieta);
}

export async function actualizarPlan(
  idDieta: number,
  input: PlanInput,
  idUsuarioActor?: number,
): Promise<PlanListado> {
  await delay();
  validar(input);

  const dieta = dietas.find((d) => d.id_dieta === idDieta);
  if (!dieta) {
    throw new ServiceError(404, 'El plan no existe');
  }

  dieta.nombre = limpiar(input.nombre);
  dieta.objetivo = input.objetivo;
  dieta.calorias_diarias = input.caloriasDiarias;
  dieta.descripcion = limpiar(input.descripcion) || undefined;
  dieta.id_nutricionista = input.idNutricionista;

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Dieta',
    id_entidad: idDieta,
    accion: 'MODIFICACION',
  });

  return aPlanListado(dieta);
}

// --- Baja y reactivación ---
//
// No está en estructura_nutricion.md, pero Dieta sí tiene `activo` en el
// esquema. Los dos caminos se implementan juntos desde el principio (no
// solo la baja) — el panel de rutinas se hizo primero sin la reactivación y
// hubo que agregarla después; acá se hace bien de una.

export async function darDeBajaPlan(idDieta: number, idUsuarioActor?: number): Promise<void> {
  await delay();

  const dieta = dietas.find((d) => d.id_dieta === idDieta);
  if (!dieta || !dieta.activo) {
    throw new ServiceError(400, 'El plan no está activo');
  }

  dieta.activo = false;

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Dieta',
    id_entidad: idDieta,
    accion: 'BAJA',
  });
}

export async function activarPlan(
  idDieta: number,
  idUsuarioActor?: number,
): Promise<PlanListado> {
  await delay();

  const dieta = dietas.find((d) => d.id_dieta === idDieta);
  if (!dieta) {
    throw new ServiceError(404, 'El plan no existe');
  }
  if (dieta.activo) {
    throw new ServiceError(400, 'El plan ya está activo');
  }

  dieta.activo = true;

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Dieta',
    id_entidad: idDieta,
    accion: 'MODIFICACION',
    detalle: 'Reactivación',
  });

  return aPlanListado(dieta);
}
