// Promociones, conectado a la API real (routers/promociones.py).
//
// Un descuento por PORCENTAJE o por MONTO FIJO, con ventana de fechas.
//
// DOS PERMISOS, Y LA DIFERENCIA ES EL PUNTO
// -----------------------------------------
//   Crear / editar / dar de baja  ->  acción `gestionPromociones`  (solo Dueño)
//   Listar                        ->  sección COBROS               (+ Recepcionista)
//
// Definir un descuento es una decisión de negocio; aplicarlo al cobrar es
// operativo. El Recepcionista tiene que PODER VER las promos vigentes —si no,
// no puede elegir ninguna en el mostrador— pero no inventarlas. Es el mismo
// reparto que ya rige la lista de precios.
//
// EL DESCUENTO NO SE CALCULA ACÁ
// -------------------------------
// Esta capa nunca multiplica nada. Para saber cuánto sale un plan con una
// promo se llama a `vistaPreviaDescuento`, que le pregunta al backend. La
// alternativa —traer el porcentaje y hacer la cuenta en el cliente— dejaría la
// fórmula (con su piso en cero y su redondeo) escrita en tres lugares: acá, en
// Flet y en el backend. Es el mismo criterio que ya rige el `estado` del
// socio.
//
// Gemelo de la sección PROMOCIONES de `app/api_client.py` en Flet.

import { pedir } from './api';

export interface Promocion {
  idPromocion: number;
  nombre: string;
  descripcion?: string;
  porcentajeDescuento?: number;
  /** ISO (yyyy-mm-dd). */
  fechaInicio: string;
  fechaFin: string;
  idSede?: number;
  /** Baja lógica: el Dueño la apagó a mano. */
  activo: boolean;
  /**
   * Activa Y dentro de la ventana de fechas. Lo deriva el backend, no es una
   * columna: una promo de enero sigue con `activo` en true en marzo, y
   * cobrarla entonces sería regalar plata.
   */
  vigente: boolean;
  /** "20% OFF", ya armado por el backend. */
  etiqueta: string;
}

interface PromocionApi {
  id_promocion: number;
  nombre: string;
  descripcion: string | null;
  porcentaje_descuento: number;
  fecha_inicio: string;
  fecha_fin: string;
  id_sede: number | null;
  activo: boolean;
  vigente: boolean;
  etiqueta: string;
}

function aPromocion(p: PromocionApi): Promocion {
  return {
    idPromocion: p.id_promocion,
    nombre: p.nombre,
    descripcion: p.descripcion ?? undefined,
    porcentajeDescuento: p.porcentaje_descuento,
    fechaInicio: p.fecha_inicio,
    fechaFin: p.fecha_fin,
    idSede: p.id_sede ?? undefined,
    activo: p.activo,
    vigente: p.vigente,
    etiqueta: p.etiqueta,
  };
}

/**
 * El catálogo de descuentos.
 *
 * Sin filtro trae TODAS, incluidas las apagadas y las vencidas: la pantalla de
 * administración las necesita para poder reactivar una del año pasado en vez
 * de volver a cargarla. `soloVigentes` es lo que pide el selector del
 * mostrador, que no tiene por qué ofrecer una promo de enero en marzo.
 */
export async function listarPromociones(soloVigentes = false): Promise<Promocion[]> {
  const ruta = soloVigentes ? '/promociones?solo_vigentes=true' : '/promociones';
  const datos = await pedir<PromocionApi[]>(ruta);
  return datos.map(aPromocion);
}

export interface PromocionInput {
  nombre: string;
  descripcion?: string;
  /** El descuento es SIEMPRE porcentual (el monto fijo se eliminó). */
  porcentajeDescuento: number;
  fechaInicio: string;
  fechaFin: string;
  idSede?: number;
}

function cuerpoDe(input: PromocionInput) {
  return {
    nombre: input.nombre.trim(),
    descripcion: input.descripcion?.trim() || null,
    porcentaje_descuento: input.porcentajeDescuento,
    fecha_inicio: input.fechaInicio,
    fecha_fin: input.fechaFin,
    id_sede: input.idSede ?? null,
  };
}

export async function crearPromocion(input: PromocionInput): Promise<Promocion> {
  const datos = await pedir<PromocionApi>('/promociones', {
    metodo: 'POST',
    cuerpo: cuerpoDe(input),
  });
  return aPromocion(datos);
}

/**
 * Edita una promoción.
 *
 * NO recalcula lo ya cobrado, y es deliberado: `Membresia.precio_pactado`
 * guarda el monto que se cobró de verdad. Si editar la promo cambiara el
 * historial de plata, ese historial cambiaría solo — que es exactamente lo que
 * el resto del sistema evita.
 */
export async function actualizarPromocion(
  idPromocion: number,
  input: PromocionInput,
): Promise<Promocion> {
  const datos = await pedir<PromocionApi>(`/promociones/${idPromocion}`, {
    metodo: 'PUT',
    cuerpo: cuerpoDe(input),
  });
  return aPromocion(datos);
}

/**
 * La apaga. NO borra la fila: la referencian las membresías que se cobraron
 * con ella, y el historial es el que responde "¿por qué a este socio le
 * cobramos $24.000 en vez de $30.000?".
 */
export async function darDeBajaPromocion(idPromocion: number): Promise<Promocion> {
  const datos = await pedir<PromocionApi>(`/promociones/${idPromocion}/baja`, {
    metodo: 'POST',
  });
  return aPromocion(datos);
}

/**
 * La vuelve a encender. Ojo: NO le mueve las fechas, así que una vencida queda
 * activa pero sigue sin poder aplicarse. Extender una promoción es cambiarle
 * la fecha de fin, una decisión explícita.
 */
export async function reactivarPromocion(idPromocion: number): Promise<Promocion> {
  const datos = await pedir<PromocionApi>(`/promociones/${idPromocion}/reactivar`, {
    metodo: 'POST',
  });
  return aPromocion(datos);
}

/** Cuántas membresías se cobraron con ella. Para decidir antes de apagarla. */
export async function usoDePromocion(idPromocion: number): Promise<string> {
  const datos = await pedir<{ mensaje: string }>(`/promociones/${idPromocion}/uso`);
  return datos.mensaje;
}

export interface VistaPrevia {
  precioLista: number;
  descuento: number;
  precioFinal: number;
  promocion: string;
}

/**
 * Cuánto saldría cobrar ese plan con esa promo. No cobra nada.
 *
 * Es un viaje al servidor para una multiplicación, y vale la pena: es lo que
 * garantiza que el número que ve el mostrador antes de cobrar sea el mismo que
 * el backend va a registrar.
 */
export async function vistaPreviaDescuento(
  idPromocion: number,
  idTipoMembresia: number,
): Promise<VistaPrevia> {
  const d = await pedir<{
    precio_lista: number;
    descuento: number;
    precio_final: number;
    promocion: string;
  }>(`/promociones/${idPromocion}/vista-previa?id_tipo_membresia=${idTipoMembresia}`);
  return {
    precioLista: d.precio_lista,
    descuento: d.descuento,
    precioFinal: d.precio_final,
    promocion: d.promocion,
  };
}
