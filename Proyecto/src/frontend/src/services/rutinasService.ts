// Sección Rutinas, conectada a la API real (routers/rutinas.py).
//
// La rutina es una PLANTILLA que arma un entrenador, no algo de un socio en
// particular: que alguien la siga se registra aparte, en Asignacion_Rutina.
// Esa separación es la que permite asignar la misma rutina a quince personas
// sin duplicarla, y que cada una tenga sus propias fechas.
//
// El nombre del entrenador YA VIENE resuelto: el backend recorre
// Entrenador -> Empleado -> Persona. Antes eso lo hacía este archivo con
// nombrePorEmpleado, que leía de mockDb.

import type { NivelRutinaValue, EstadoRutinaValue } from '../config';
import { EstadoRutina } from '../config';
import { pedir } from './api';

/**
 * Cuántos socios se consideran "rutina llena" para la barra de progreso.
 *
 * Es un número de PRESENTACIÓN, no una regla de negocio: el backend no impide
 * asignar más. Por eso vive acá y no en el servidor — si mañana se decide que
 * una rutina tiene cupo real, ahí sí pasa a ser del backend.
 */
const CAPACIDAD_MAXIMA_RUTINA = 20;

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

export interface EjercicioDeRutina {
  idRutinaEjercicio: number;
  idEjercicio: number;
  nombre: string;
  grupoMuscular: string;
  dia: number;
  orden: number;
  series?: number;
  /** Texto libre: en el gimnasio se escribe "8-12" o "al fallo". */
  repeticiones?: string;
  pesoSugerido?: number;
  descansoSegundos?: number;
  observaciones?: string;
}

interface RutinaApi {
  id_rutina: number;
  id_entrenador: number;
  entrenador: string;
  nombre: string;
  objetivo: string | null;
  nivel: string | null;
  dias_por_semana: number | null;
  fecha_creacion: string | null;
  activo: boolean;
  asignados: number;
  ejercicios: {
    id_rutina_ejercicio: number;
    id_ejercicio: number;
    nombre_ejercicio: string;
    grupo_muscular: string;
    dia: number;
    orden: number;
    series: number | null;
    repeticiones: string | null;
    peso_sugerido: number | null;
    descanso_segundos: number | null;
    observaciones: string | null;
  }[];
}

function aRutinaListado(r: RutinaApi): RutinaListado {
  return {
    idRutina: r.id_rutina,
    nombre: r.nombre,
    nivel: (r.nivel ?? undefined) as NivelRutinaValue | undefined,
    objetivo: r.objetivo ?? undefined,
    diasPorSemana: r.dias_por_semana ?? undefined,
    asignados: r.asignados,
    progreso: Math.min(r.asignados / CAPACIDAD_MAXIMA_RUTINA, 1),
    idEntrenador: r.id_entrenador,
    entrenador: r.entrenador,
    fechaCreacion: r.fecha_creacion ?? '',
    activo: r.activo,
    estado: r.activo ? EstadoRutina.ACTIVA : EstadoRutina.INACTIVA,
  };
}

export async function listarRutinas(): Promise<RutinaListado[]> {
  const datos = await pedir<RutinaApi[]>('/rutinas');
  return datos.map(aRutinaListado);
}

/**
 * El detalle SÍ trae los ejercicios, ya ordenados por día y orden — que es
 * como se lee la planilla en el gimnasio. El listado no los trae porque la
 * grilla muestra tarjetas y bajarlos sería traer datos que nadie mira.
 */
export async function obtenerRutina(
  idRutina: number,
): Promise<RutinaListado & { ejercicios: EjercicioDeRutina[] }> {
  const r = await pedir<RutinaApi>(`/rutinas/${idRutina}`);
  return {
    ...aRutinaListado(r),
    ejercicios: r.ejercicios.map((e) => ({
      idRutinaEjercicio: e.id_rutina_ejercicio,
      idEjercicio: e.id_ejercicio,
      nombre: e.nombre_ejercicio,
      grupoMuscular: e.grupo_muscular,
      dia: e.dia,
      orden: e.orden,
      series: e.series ?? undefined,
      repeticiones: e.repeticiones ?? undefined,
      pesoSugerido: e.peso_sugerido ?? undefined,
      descansoSegundos: e.descanso_segundos ?? undefined,
      observaciones: e.observaciones ?? undefined,
    })),
  };
}

// --- Entrenadores para el selector del formulario ---

export interface EntrenadorOpcion {
  idEntrenador: number;
  nombre: string;
}

/**
 * Solo entrenadores con el empleado ACTIVO: no tiene sentido asignarle una
 * rutina nueva a alguien que ya no trabaja acá. El filtro lo aplica el
 * backend, que además rechaza el alta si igual se le manda uno de baja.
 */
export async function listarEntrenadoresActivos(): Promise<EntrenadorOpcion[]> {
  const datos = await pedir<{ id: number; nombre: string }[]>('/personal/entrenadores');
  return datos.map((e) => ({ idEntrenador: e.id, nombre: e.nombre }));
}

// --- Alta y edición ---

export interface RutinaInput {
  nombre: string;
  nivel: NivelRutinaValue;
  diasPorSemana: number;
  objetivo?: string;
  /**
   * A cargo de quién queda.
   *
   * Un ENTRENADOR puede omitirlo: la rutina queda a su nombre, y mandar el id
   * de otro le da 403 — no puede crear rutinas a nombre ajeno. El Dueño y el
   * Recepcionista SÍ tienen que mandarlo: tienen el permiso pero no son
   * entrenadores, así que para ellos elegir no es suplantar, es delegar.
   */
  idEntrenador?: number;
}

export async function crearRutina(input: RutinaInput): Promise<RutinaListado> {
  const datos = await pedir<RutinaApi>('/rutinas', {
    metodo: 'POST',
    cuerpo: {
      nombre: input.nombre.trim(),
      nivel: input.nivel,
      dias_por_semana: input.diasPorSemana,
      objetivo: input.objetivo?.trim() || null,
      id_entrenador: input.idEntrenador ?? null,
      ejercicios: [],
    },
  });
  return aRutinaListado(datos);
}

export async function actualizarRutina(
  idRutina: number,
  input: RutinaInput,
): Promise<RutinaListado> {
  const datos = await pedir<RutinaApi>(`/rutinas/${idRutina}`, {
    metodo: 'PUT',
    cuerpo: {
      nombre: input.nombre.trim(),
      nivel: input.nivel,
      dias_por_semana: input.diasPorSemana,
      objetivo: input.objetivo?.trim() || null,
      id_entrenador: input.idEntrenador ?? null,
    },
  });
  return aRutinaListado(datos);
}

// --- Baja lógica ---
//
// La fila queda: borrarla rompería las asignaciones históricas —quedarían
// apuntando a una rutina inexistente— y con ellas el registro de qué entrenó
// cada socio.
//
// Los socios que la están siguiendo AHORA no se tocan: la rutina desactivada
// deja de ofrecerse para asignaciones nuevas, pero quien ya la tiene la
// termina. Cortársela de un día para el otro dejaría a alguien sin plan sin
// que nadie lo hubiera decidido.

export async function darDeBajaRutina(idRutina: number): Promise<RutinaListado> {
  const datos = await pedir<RutinaApi>(`/rutinas/${idRutina}/baja`, { metodo: 'POST' });
  return aRutinaListado(datos);
}

export async function activarRutina(idRutina: number): Promise<RutinaListado> {
  const datos = await pedir<RutinaApi>(`/rutinas/${idRutina}/reactivar`, { metodo: 'POST' });
  return aRutinaListado(datos);
}

// --- Asignación a socios ---

export async function asignarRutinaASocio(
  idRutina: number,
  idSocio: number,
): Promise<void> {
  // Si el socio ya tenía una rutina activa, el backend la FINALIZA y deja
  // esta: nadie sigue dos rutinas de musculación a la vez. La anterior queda
  // como historial, no se borra.
  await pedir(`/rutinas/${idRutina}/asignar`, {
    metodo: 'POST',
    cuerpo: { id_socio: idSocio },
  });
}
