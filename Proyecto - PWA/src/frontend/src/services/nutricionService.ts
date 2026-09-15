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
  /**
   * Si quien lo mira puede editarlo, darlo de baja y asignarlo. Lo decide el
   * backend: un Nutricionista ve los planes de sus colegas pero no los toca.
   */
  puedeEditar: boolean;
}

export interface ComidaListada {
  idComida: number;
  dia?: number;
  momento?: string;
  /** Plato del catálogo, o undefined si la comida es texto libre (el texto va en `nombre`). */
  idCatalogoComida?: number;
  /** Nombre del plato (viene del Catalogo_Comida). */
  nombre: string;
  descripcion?: string;
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
    id_catalogo_comida: number | null;
    nombre: string;
    descripcion: string | null;
    calorias: number | null;
  }[];
  puede_editar?: boolean;
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
    puedeEditar: d.puede_editar ?? true,
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
    idCatalogoComida: c.id_catalogo_comida ?? undefined,
    nombre: c.nombre,
    descripcion: c.descripcion ?? undefined,
    calorias: c.calorias ?? undefined,
  }));
}

// --- Catálogo de platos ---
//
// De acá salen el nombre y las calorías de cada comida de un plan. Una comida
// también puede ser texto libre, porque el catálogo suele arrancar vacío.

export interface PlatoCatalogo {
  idCatalogoComida: number;
  nombre: string;
  descripcion?: string;
  calorias?: number;
}

interface PlatoApi {
  id_catalogo_comida: number;
  nombre: string;
  descripcion: string | null;
  calorias: number | null;
}

function aPlato(p: PlatoApi): PlatoCatalogo {
  return {
    idCatalogoComida: p.id_catalogo_comida,
    nombre: p.nombre,
    descripcion: p.descripcion ?? undefined,
    calorias: p.calorias ?? undefined,
  };
}

export async function listarPlatos(): Promise<PlatoCatalogo[]> {
  const datos = await pedir<PlatoApi[]>('/nutricion/catalogo-comidas');
  return datos.map(aPlato);
}

export async function crearPlato(input: {
  nombre: string;
  calorias?: number;
  descripcion?: string;
}): Promise<PlatoCatalogo> {
  const datos = await pedir<PlatoApi>('/nutricion/catalogo-comidas', {
    metodo: 'POST',
    cuerpo: {
      nombre: input.nombre.trim(),
      calorias: input.calorias ?? null,
      descripcion: input.descripcion?.trim() || null,
    },
  });
  return aPlato(datos);
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
  /**
   * El plan alimentario entero, como quedó. Al editar REEMPLAZA todas las
   * comidas; si se omite, no se tocan.
   */
  comidas?: ComidaInput[];
}

/** Una comida del plan: plato del catálogo O texto libre. */
export interface ComidaInput {
  dia: number;
  momento?: string;
  idCatalogoComida?: number;
  descripcion?: string;
}

function aComidaApi(c: ComidaInput) {
  return {
    dia: c.dia,
    momento: c.momento ?? null,
    id_catalogo_comida: c.idCatalogoComida ?? null,
    descripcion: c.idCatalogoComida ? null : c.descripcion?.trim() || null,
  };
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
      comidas: (input.comidas ?? []).map(aComidaApi),
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
      // Sin la clave cuando no vienen: el backend lo lee como "no tocar".
      ...(input.comidas ? { comidas: input.comidas.map(aComidaApi) } : {}),
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
