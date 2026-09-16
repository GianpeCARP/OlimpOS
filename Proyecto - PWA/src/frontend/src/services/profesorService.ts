// Lo que ve el PROFESOR: las clases que dicta él.
//
// Archivo propio y no una sección de actividadService por lo mismo que el
// backend puso el endpoint en /portal y no en /actividades: acá nada acepta
// un id por parámetro. El profesor sale del token, así que no hay forma de
// pedir las clases de otro — y tenerlo separado hace evidente que este
// service no sirve para mirar el catálogo.

import { pedir } from './api';

/** Cómo llegó (o no) cada persona anotada. Lo deriva el backend. */
export type EstadoInscripto = 'pendiente' | 'asistio' | 'ausente' | 'en_espera' | 'cancelada';

interface InscriptoApi {
  id_reserva: number;
  id_socio: number;
  nombre: string;
  dni: string;
  estado: EstadoInscripto;
  es_clase_suelta?: boolean;
  alerta?: string | null;
}

interface MiClaseApi {
  id_turno: number;
  actividad: string;
  fecha: string;
  hora: string;
  minutos_para_empezar: number;
  cupo_maximo: number;
  ocupados: number;
  en_espera: number;
  estado_turno: string;
  inscriptos?: InscriptoApi[];
}

export interface Inscripto {
  idReserva: number;
  idSocio: number;
  nombre: string;
  dni: string;
  estado: EstadoInscripto;
  esClaseSuelta: boolean;
  /** "Cuota vencida hace 3 días" y similares. El backend ya lo resolvió. */
  alerta: string | null;
}

export interface MiClase {
  idTurno: number;
  actividad: string;
  fecha: string;
  hora: string;
  /** Negativo = ya empezó. Lo calcula el servidor: si lo hiciera el navegador,
   *  dos pantallas con la hora mal puesta mostrarían órdenes distintos. */
  minutosParaEmpezar: number;
  cupoMaximo: number;
  ocupados: number;
  enEspera: number;
  estadoTurno: string;
  inscriptos: Inscripto[];
}

function aInscripto(i: InscriptoApi): Inscripto {
  return {
    idReserva: i.id_reserva,
    idSocio: i.id_socio,
    nombre: i.nombre,
    dni: i.dni,
    estado: i.estado,
    esClaseSuelta: i.es_clase_suelta ?? false,
    alerta: i.alerta ?? null,
  };
}

function aMiClase(t: MiClaseApi): MiClase {
  return {
    idTurno: t.id_turno,
    actividad: t.actividad,
    fecha: t.fecha,
    hora: t.hora,
    minutosParaEmpezar: t.minutos_para_empezar,
    cupoMaximo: t.cupo_maximo,
    ocupados: t.ocupados,
    enEspera: t.en_espera,
    estadoTurno: t.estado_turno,
    inscriptos: (t.inscriptos ?? []).map(aInscripto),
  };
}

/**
 * Las clases que dicta este profesor, de la más cercana a la más lejana.
 *
 * `dias` lo acota el backend entre 1 y 31. El default de una semana es lo que
 * un profesor mira de verdad; pedir un año serían cientos de turnos con sus
 * reservas para una pantalla que se lee de un vistazo.
 */
export async function getMisClases(dias = 7): Promise<MiClase[]> {
  const datos = await pedir<MiClaseApi[]>(`/portal/mis-clases?dias=${dias}`);
  return datos.map(aMiClase);
}
