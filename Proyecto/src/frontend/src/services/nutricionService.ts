// Sección Nutrición, conectada a la API real (routers/nutricion.py).
//
// Espejo estructural de rutinasService: la dieta es una PLANTILLA que arma un
// nutricionista y la asignación es lo que la conecta con un socio. Asignar la
// misma dieta a diez personas no la duplica diez veces.
//
// El nombre del nutricionista viene resuelto del backend (Nutricionista ->
// Empleado -> Persona), igual que el del entrenador en rutinas.

import type { ObjetivoDietaValue, EstadoDietaValue } from '../config';
import { EstadoDieta } from '../config';
import { pedir } from './api';

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

export interface ComidaListada {
  idComida: number;
  dia?: number;
  momento?: string;
  descripcion: string;
  calorias?: number;
}

interface DietaApi {
  id_dieta: number;
  id_nutricionista: number;
  nutricionista: string;
  nombre: string;
  objetivo: string | null;
  calorias_diarias: number | null;
  descripcion: string | null;
  fecha_creacion: string | null;
  activo: boolean;
  asignados: number;
  comidas: {
    id_comida: number;
    dia: number | null;
    momento: string | null;
    descripcion: string;
    calorias: number | null;
  }[];
}

function aPlanListado(d: DietaApi): PlanListado {
  return {
    idDieta: d.id_dieta,
    nombre: d.nombre,
    objetivo: (d.objetivo ?? undefined) as ObjetivoDietaValue | undefined,
    caloriasDiarias: d.calorias_diarias ?? undefined,
    descripcion: d.descripcion ?? undefined,
    asignados: d.asignados,
    idNutricionista: d.id_nutricionista,
    nutricionista: d.nutricionista,
    fechaCreacion: d.fecha_creacion ?? '',
    activo: d.activo,
    estado: d.activo ? EstadoDieta.ACTIVA : EstadoDieta.INACTIVA,
  };
}

export async function listarPlanes(): Promise<PlanListado[]> {
  const datos = await pedir<DietaApi[]>('/nutricion');
  return datos.map(aPlanListado);
}

// --- Nutricionistas para el selector del formulario ---

export interface NutricionistaOpcion {
  idNutricionista: number;
  nombre: string;
}

/** Solo con el empleado activo — mismo criterio que listarEntrenadoresActivos. */
export async function listarNutricionistasActivos(): Promise<NutricionistaOpcion[]> {
  const datos = await pedir<{ id: number; nombre: string }[]>('/personal/nutricionistas');
  return datos.map((n) => ({ idNutricionista: n.id, nombre: n.nombre }));
}

// --- Comidas del plan ---

/**
 * Las comidas vienen ordenadas por día y por MOMENTO DEL DÍA, no
 * alfabéticamente: ordenar por texto pondría Almuerzo antes que Desayuno.
 * Ese orden lo aplica el backend, que tiene la tabla de momentos.
 */
export async function listarComidasDelPlan(idDieta: number): Promise<ComidaListada[]> {
  const d = await pedir<DietaApi>(`/nutricion/${idDieta}`);
  return d.comidas.map((c) => ({
    idComida: c.id_comida,
    dia: c.dia ?? undefined,
    momento: c.momento ?? undefined,
    descripcion: c.descripcion,
    calorias: c.calorias ?? undefined,
  }));
}

// --- Alta y edición ---

export interface PlanInput {
  nombre: string;
  objetivo: ObjetivoDietaValue;
  caloriasDiarias: number;
  descripcion?: string;
  /**
   * A cargo de quién queda. Misma regla que en rutinas: un NUTRICIONISTA
   * puede omitirlo (la dieta queda a su nombre y mandar el id de otro da
   * 403), pero el Dueño y el Recepcionista tienen que elegir uno.
   */
  idNutricionista?: number;
}

export async function crearPlan(input: PlanInput): Promise<PlanListado> {
  const datos = await pedir<DietaApi>('/nutricion', {
    metodo: 'POST',
    cuerpo: {
      nombre: input.nombre.trim(),
      objetivo: input.objetivo,
      calorias_diarias: input.caloriasDiarias,
      descripcion: input.descripcion?.trim() || null,
      id_nutricionista: input.idNutricionista ?? null,
      comidas: [],
    },
  });
  return aPlanListado(datos);
}

export async function actualizarPlan(idDieta: number, input: PlanInput): Promise<PlanListado> {
  const datos = await pedir<DietaApi>(`/nutricion/${idDieta}`, {
    metodo: 'PUT',
    cuerpo: {
      nombre: input.nombre.trim(),
      objetivo: input.objetivo,
      calorias_diarias: input.caloriasDiarias,
      descripcion: input.descripcion?.trim() || null,
      id_nutricionista: input.idNutricionista ?? null,
    },
  });
  return aPlanListado(datos);
}

// --- Baja lógica ---
//
// Mismo criterio que rutinas: los socios que la están siguiendo la terminan,
// pero deja de ofrecerse para asignaciones nuevas.

export async function darDeBajaPlan(idDieta: number): Promise<PlanListado> {
  const datos = await pedir<DietaApi>(`/nutricion/${idDieta}/baja`, { metodo: 'POST' });
  return aPlanListado(datos);
}

export async function activarPlan(idDieta: number): Promise<PlanListado> {
  const datos = await pedir<DietaApi>(`/nutricion/${idDieta}/reactivar`, { metodo: 'POST' });
  return aPlanListado(datos);
}

// --- Asignación a socios ---

export async function asignarPlanASocio(idDieta: number, idSocio: number): Promise<void> {
  // Si el socio ya tenía una dieta activa, el backend la finaliza: nadie
  // sigue dos planes alimentarios a la vez. La anterior queda como historial.
  await pedir(`/nutricion/${idDieta}/asignar`, {
    metodo: 'POST',
    cuerpo: { id_socio: idSocio },
  });
}
