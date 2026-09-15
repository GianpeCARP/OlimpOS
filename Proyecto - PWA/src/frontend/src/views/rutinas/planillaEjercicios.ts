import type { EjercicioCatalogo } from '../../services/socioService';

// La lógica (sin UI) de la planilla de ejercicios de una rutina. Vive aparte
// de EditorEjercicios.tsx porque un archivo de componentes que además exporta
// funciones rompe el fast refresh de Vite.

/** Un ejercicio de la planilla. Los números van como texto: son inputs. */
export interface ItemEjercicio {
  clave: number;
  idEjercicio: number;
  nombre: string;
  grupoMuscular: string;
  dia: number;
  series: string;
  repeticiones: string;
  peso: string;
  descanso: string;
  observaciones: string;
}

/** Lo que manda el backend en cada fila de Rutina_Ejercicio. */
export interface EjercicioArmado {
  idEjercicio: number;
  dia: number;
  orden: number;
  series?: number;
  repeticiones?: string;
  pesoSugerido?: number;
  descansoSegundos?: number;
  observaciones?: string;
}

// Clave estable para React. No crypto.randomUUID(): sólo existe en contexto
// seguro, y la PWA se abre por la IP de la red en HTTP.
let siguienteClave = 1;

/** Arma un item desde un ejercicio del catálogo o de una rutina ya cargada. */
export function nuevoItem(e: {
  idEjercicio: number;
  nombre: string;
  grupoMuscular: string;
  dia: number;
  series?: number;
  repeticiones?: string;
  pesoSugerido?: number;
  descansoSegundos?: number;
  observaciones?: string;
}): ItemEjercicio {
  return {
    clave: siguienteClave++,
    idEjercicio: e.idEjercicio,
    nombre: e.nombre,
    grupoMuscular: e.grupoMuscular,
    dia: e.dia,
    series: e.series?.toString() ?? '',
    repeticiones: e.repeticiones ?? '',
    peso: e.pesoSugerido?.toString() ?? '',
    descanso: e.descansoSegundos?.toString() ?? '',
    observaciones: e.observaciones ?? '',
  };
}

function aNumero(valor: string, campo: string, ejercicio: string, entero: boolean): number | undefined {
  const t = valor.trim().replace(',', '.');
  if (t === '') return undefined;
  const n = Number(t);
  if (!Number.isFinite(n) || n < 0 || (entero && !Number.isInteger(n))) {
    throw new Error(`${ejercicio}: "${valor}" no es un valor válido para ${campo}.`);
  }
  return n;
}

/**
 * La planilla lista para el backend. Tira un Error con un mensaje para mostrar
 * si algo no cierra (un número mal escrito, ejercicios en un día que ya no
 * existe porque se bajaron los días por semana).
 */
export function armarEjercicios(items: ItemEjercicio[], dias: number): EjercicioArmado[] {
  const fuera = items.find((i) => i.dia > dias);
  if (fuera) {
    throw new Error(
      `Hay ejercicios en el Día ${fuera.dia}, que queda fuera de los ${dias} días por semana. Quitalos o subí los días.`,
    );
  }
  const ordenPorDia = new Map<number, number>();
  // sort es estable: dentro de cada día se respeta el orden de la lista.
  return [...items]
    .sort((a, b) => a.dia - b.dia)
    .map((it) => {
      const orden = (ordenPorDia.get(it.dia) ?? 0) + 1;
      ordenPorDia.set(it.dia, orden);
      return {
        idEjercicio: it.idEjercicio,
        dia: it.dia,
        orden,
        series: aNumero(it.series, 'series', it.nombre, true),
        repeticiones: it.repeticiones.trim() || undefined,
        pesoSugerido: aNumero(it.peso, 'el peso', it.nombre, false),
        descansoSegundos: aNumero(it.descanso, 'el descanso', it.nombre, true),
        observaciones: it.observaciones.trim() || undefined,
      };
    });
}

/** El catálogo filtrado por la búsqueda y agrupado por músculo. */
export function agruparCatalogo(
  catalogo: EjercicioCatalogo[] | null,
  busqueda: string,
): [string, EjercicioCatalogo[]][] {
  if (!catalogo) return [];
  const q = busqueda.trim().toLowerCase();
  const filtrados = q
    ? catalogo.filter(
        (e) => e.nombre.toLowerCase().includes(q) || e.grupoMuscular.toLowerCase().includes(q),
      )
    : catalogo;
  const mapa = new Map<string, EjercicioCatalogo[]>();
  for (const e of filtrados) {
    const g = mapa.get(e.grupoMuscular) ?? [];
    g.push(e);
    mapa.set(e.grupoMuscular, g);
  }
  return [...mapa.entries()];
}
