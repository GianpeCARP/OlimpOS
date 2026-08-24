// Historial médico del socio, conectado a la API real (routers/patologias.py).
//
// POR QUÉ ES UN SERVICE APARTE Y NO PARTE DE sociosService
// ========================================================
// Por el mismo motivo por el que en el backend es un router aparte, aunque
// tres de las cinco rutas empiecen con /socios: el permiso es distinto.
//
// Todo /socios lo protege la sección SOCIOS, que el Recepcionista tiene en
// TOTAL. Acá el guard es la acción `verHistorialMedico`, que el Recepcionista
// NO tiene — es la única de la matriz donde queda por debajo del Entrenador y
// del Nutricionista.
//
// Mezclar estas funciones entre las de sociosService habría significado que
// las vistas tengan que acordarse de que dos de las diez piden otro permiso, y
// ese es justo el tipo de excepción que a los seis meses alguien copia mal.
//
// Gemelo de la sección HISTORIAL MÉDICO de `app/api_client.py` en Flet.

import { pedir } from './api';

// --- El catálogo ---

export interface PatologiaCatalogo {
  idPatologia: number;
  nombre: string;
  descripcion?: string;
}

interface PatologiaApi {
  id_patologia: number;
  nombre: string;
  descripcion: string | null;
}

function aCatalogo(p: PatologiaApi): PatologiaCatalogo {
  return {
    idPatologia: p.id_patologia,
    nombre: p.nombre,
    descripcion: p.descripcion ?? undefined,
  };
}

/**
 * Las condiciones que el gimnasio registra.
 *
 * Es un catálogo y no un campo de texto libre por 1FN: "asma, rodilla operada,
 * hipertensión" en una sola celda no se puede filtrar ni contar, y cada quien
 * lo escribe distinto. Con el catálogo, "qué socios tienen asma" es una
 * consulta y no una búsqueda de texto con suerte.
 */
export async function listarCatalogoPatologias(): Promise<PatologiaCatalogo[]> {
  const datos = await pedir<PatologiaApi[]>('/patologias');
  return datos.map(aCatalogo);
}

/**
 * Suma una condición al catálogo.
 *
 * El backend compara el nombre SIN distinguir mayúsculas y rechaza la
 * repetida con un 409: "Asma" y "asma" son la misma cosa, y dejar que
 * convivan haría que la mitad de los socios asmáticos no aparezca al filtrar
 * por una de las dos.
 */
export async function crearPatologia(
  nombre: string,
  descripcion?: string,
): Promise<PatologiaCatalogo> {
  const datos = await pedir<PatologiaApi>('/patologias', {
    metodo: 'POST',
    cuerpo: { nombre: nombre.trim(), descripcion: descripcion?.trim() || null },
  });
  return aCatalogo(datos);
}

// --- Las de un socio ---

export interface PatologiaDeSocio {
  idPatologia: number;
  nombre: string;
  descripcion?: string;
  /** ISO (yyyy-mm-dd) tal como la manda el backend. La vista la formatea. */
  fechaDiagnostico?: string;
  observaciones?: string;
}

interface PatologiaDeSocioApi {
  id_patologia: number;
  nombre: string;
  descripcion: string | null;
  fecha_diagnostico: string | null;
  observaciones: string | null;
}

function aPatologiaDeSocio(p: PatologiaDeSocioApi): PatologiaDeSocio {
  return {
    idPatologia: p.id_patologia,
    nombre: p.nombre,
    descripcion: p.descripcion ?? undefined,
    fechaDiagnostico: p.fecha_diagnostico ?? undefined,
    observaciones: p.observaciones ?? undefined,
  };
}

export async function listarPatologiasDeSocio(idSocio: number): Promise<PatologiaDeSocio[]> {
  const datos = await pedir<PatologiaDeSocioApi[]>(`/socios/${idSocio}/patologias`);
  return datos.map(aPatologiaDeSocio);
}

export interface DatosPatologia {
  idPatologia: number;
  /** ISO (yyyy-mm-dd). El input type="date" ya entrega este formato. */
  fechaDiagnostico?: string;
  observaciones?: string;
}

/**
 * Le registra una condición a un socio.
 *
 * `observaciones` es lo que más le sirve al entrenador y no lo puede saber el
 * catálogo: "rodilla derecha", "controlada con medicación", "evitar impacto".
 * El nombre de la patología dice QUÉ tiene; esto dice qué hacer.
 */
export async function asignarPatologia(
  idSocio: number,
  datos: DatosPatologia,
): Promise<PatologiaDeSocio> {
  const respuesta = await pedir<PatologiaDeSocioApi>(`/socios/${idSocio}/patologias`, {
    metodo: 'POST',
    cuerpo: cuerpoDe(datos),
  });
  return aPatologiaDeSocio(respuesta);
}

/**
 * Cambia la fecha o las observaciones.
 *
 * Existe en vez de "borrar y volver a cargar" porque las observaciones cambian
 * más seguido que el diagnóstico —una lesión que mejora, una medicación que se
 * ajusta— y rehacer la fila perdería la fecha original.
 */
export async function editarPatologiaDeSocio(
  idSocio: number,
  datos: DatosPatologia,
): Promise<PatologiaDeSocio> {
  const respuesta = await pedir<PatologiaDeSocioApi>(
    `/socios/${idSocio}/patologias/${datos.idPatologia}`,
    { metodo: 'PUT', cuerpo: cuerpoDe(datos) },
  );
  return aPatologiaDeSocio(respuesta);
}

/**
 * Le saca una condición.
 *
 * Acá SÍ se borra la fila, a diferencia de casi todo el resto del sistema
 * —socios, rutinas, actividades— que usa baja lógica. No es un hecho
 * histórico: es el estado de salud ACTUAL. Una lesión que se curó no es "una
 * lesión finalizada" que convenga arrastrar, y guardar condiciones médicas
 * viejas de alguien es justamente el tipo de dato que no conviene acumular sin
 * motivo.
 */
export async function quitarPatologia(idSocio: number, idPatologia: number): Promise<void> {
  await pedir<void>(`/socios/${idSocio}/patologias/${idPatologia}`, { metodo: 'DELETE' });
}

/**
 * El cuerpo que esperan el POST y el PUT.
 *
 * El PUT también exige `id_patologia` aunque ya venga en la URL: el backend
 * reusa el mismo schema de Pydantic para los dos, y sin ese campo devuelve un
 * 422 que en pantalla parece un error de servidor.
 */
function cuerpoDe(datos: DatosPatologia) {
  return {
    id_patologia: datos.idPatologia,
    fecha_diagnostico: datos.fechaDiagnostico || null,
    observaciones: datos.observaciones?.trim() || null,
  };
}
