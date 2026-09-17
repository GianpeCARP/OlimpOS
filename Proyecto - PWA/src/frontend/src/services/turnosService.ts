// Horario semanal y turnos, vistos desde el PERSONAL (Dueño y Recepcionista).
//
// Archivo aparte de actividadService porque ese ya mezcla catálogo, compras
// del socio y fichaje; esto es otra pregunta: CUÁNDO hay clase y QUIÉN se
// anotó. Y porque faltaba entero: el backend tenía los endpoints de horarios
// desde que se hizo la generación automática, y la PWA nunca los llamó — el
// dueño probando la web no tenía dónde cargar un horario, así que no existía
// ningún turno, "Mis clases" del profesor salía vacío y el socio con una
// clase suelta comprada no tenía dónde usarla.

import { pedir } from './api';
import { aMiClase, type MiClase, type MiClaseApi } from './profesorService';

// =========================================================================
// HORARIO SEMANAL
// =========================================================================

/** Índice + 1 = día ISO (1 = lunes), el mismo número que guarda la base. */
export const DIAS_SEMANA = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];

interface HorarioApi {
  id_horario_actividad: number;
  id_actividad: number;
  actividad: string;
  dia_semana: number;
  dia_nombre: string;
  hora: string;
  cupo: number;
  id_profesor: number | null;
  profesor: string | null;
  vigente_desde: string;
  vigente_hasta: string | null;
  activo: boolean;
  turnos_futuros: number;
}

export interface Horario {
  idHorario: number;
  idActividad: number;
  actividad: string;
  /** ISO: 1 = lunes … 7 = domingo, igual que la base. */
  diaSemana: number;
  diaNombre: string;
  /** "19:00" (sin segundos). */
  hora: string;
  cupo: number;
  idProfesor: number | null;
  profesor: string | null;
  activo: boolean;
  /** Turnos generados que todavía no pasaron. 0 en un horario activo = algo anda mal. */
  turnosFuturos: number;
}

function aHorario(h: HorarioApi): Horario {
  return {
    idHorario: h.id_horario_actividad,
    idActividad: h.id_actividad,
    actividad: h.actividad,
    diaSemana: h.dia_semana,
    diaNombre: h.dia_nombre,
    hora: h.hora.slice(0, 5),
    cupo: h.cupo,
    idProfesor: h.id_profesor,
    profesor: h.profesor,
    activo: h.activo,
    turnosFuturos: h.turnos_futuros,
  };
}

export async function getHorarios(): Promise<Horario[]> {
  const datos = await pedir<HorarioApi[]>('/actividades/horarios');
  return datos.map(aHorario);
}

export interface HorarioInput {
  idActividad: number;
  diaSemana: number;
  /** "HH:MM". */
  hora: string;
  cupo: number;
  idProfesor: number | null;
}

/** Crea el horario. El backend genera sus turnos en el acto (4 semanas). */
export async function crearHorario(input: HorarioInput): Promise<Horario> {
  const datos = await pedir<HorarioApi>('/actividades/horarios', {
    metodo: 'POST',
    cuerpo: {
      id_actividad: input.idActividad,
      dia_semana: input.diaSemana,
      hora: `${input.hora}:00`,
      cupo: input.cupo,
      id_profesor: input.idProfesor,
    },
  });
  return aHorario(datos);
}

/**
 * Da de baja un horario: deja de generar turnos. Los ya generados NO se tocan
 * (pueden tener gente anotada); si hay que sacar alguno, se cancela desde la
 * agenda. Mismo criterio que Flet.
 */
export async function darDeBajaHorario(idHorario: number): Promise<void> {
  await pedir<HorarioApi>(`/actividades/horarios/${idHorario}/estado?activo=false`, {
    metodo: 'POST',
  });
}

/**
 * Le cambia (o le saca) el profesor a un horario ya creado.
 *
 * Antes la única forma era darlo de baja y cargarlo de nuevo, y eso genera
 * turnos nuevos dejando los viejos cancelados: corregir un dato administrativo
 * le volteaba la clase a los que ya estaban anotados.
 *
 * El backend arrastra el cambio a los turnos futuros HABILITADOS, porque de ahí
 * sale "Mis clases": sin eso el profesor nuevo no vería ninguna de las clases ya
 * generadas y el viejo las seguiría viendo todas. Los pasados no se tocan.
 */
export async function cambiarProfesorDeHorario(
  idHorario: number,
  idProfesor: number | null,
): Promise<Horario> {
  // Sin `id_profesor` en la query, el backend lo lee como None y deja el
  // horario como sala abierta, que es un estado válido.
  const query = idProfesor === null ? '' : `?id_profesor=${idProfesor}`;
  const datos = await pedir<HorarioApi>(
    `/actividades/horarios/${idHorario}/profesor${query}`,
    { metodo: 'PUT' },
  );
  return aHorario(datos);
}

export async function regenerarTurnos(): Promise<string> {
  const datos = await pedir<{ mensaje: string }>('/actividades/turnos/generar', {
    metodo: 'POST',
  });
  return datos.mensaje;
}

// =========================================================================
// AGENDA DE TURNOS
// =========================================================================

interface TurnoApi {
  id_turno: number;
  id_actividad: number;
  actividad: string;
  fecha: string;
  hora: string;
  cupo_maximo: number;
  reservados: number;
  lugares_libres: number;
  estado: 'HABILITADO' | 'CANCELADO';
  profesor: string | null;
  motivo_cancelacion: string | null;
}

export interface TurnoAgenda {
  idTurno: number;
  idActividad: number;
  actividad: string;
  fecha: string;
  hora: string;
  cupoMaximo: number;
  reservados: number;
  cancelado: boolean;
  profesor: string | null;
  motivoCancelacion: string | null;
}

/** "YYYY-MM-DD" en hora LOCAL: toISOString() daría el día de Greenwich. */
function isoLocal(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

/** Los turnos de hoy a `dias` adelante, en el orden de la base (fecha, hora). */
export async function getAgenda(dias = 7): Promise<TurnoAgenda[]> {
  const hoy = new Date();
  const hasta = new Date(hoy);
  hasta.setDate(hoy.getDate() + dias);
  const datos = await pedir<TurnoApi[]>(
    `/actividades/turnos?desde=${isoLocal(hoy)}&hasta=${isoLocal(hasta)}`,
  );
  return datos.map((t) => ({
    idTurno: t.id_turno,
    idActividad: t.id_actividad,
    actividad: t.actividad,
    fecha: t.fecha,
    hora: t.hora.slice(0, 5),
    cupoMaximo: t.cupo_maximo,
    reservados: t.reservados,
    cancelado: t.estado === 'CANCELADO',
    profesor: t.profesor,
    motivoCancelacion: t.motivo_cancelacion,
  }));
}

/**
 * Un turno con la lista de anotados. Es el mismo armado que usan el panel de
 * Recepción de Flet y "Mis clases": el mostrador, el profesor y el dueño ven
 * la misma lista con los mismos estados.
 */
export async function getDetalleTurno(idTurno: number): Promise<MiClase> {
  const datos = await pedir<MiClaseApi>(`/recepcion/turnos/${idTurno}`);
  return aMiClase(datos);
}

/**
 * Cancela una clase puntual. Las reservas pasan a CANCELADA_GIMNASIO y la
 * clase se le devuelve sola a cada socio (deja de contar como usada).
 */
export async function cancelarTurno(idTurno: number, motivo: string): Promise<void> {
  await pedir<TurnoApi>(
    `/actividades/turnos/${idTurno}/cancelar?motivo=${encodeURIComponent(motivo)}`,
    { metodo: 'POST' },
  );
}
