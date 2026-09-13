// Cobros, conectado a la API real (routers/cobros.py).
//
// EL MONTO LO CALCULA EL SERVIDOR
// Ninguna de estas funciones manda un importe: mandan QUÉ se está cobrando
// (el plan, el abono, la deuda) y el backend busca el precio. Si el monto
// viniera del cliente, cualquiera con la consola abierta podría cobrar $1 una
// membresía de $30.000 y en la base quedaría un pago perfectamente válido.
//
// POR QUÉ EL COMBO ES UNA SOLA LLAMADA
// Membresía y abono de actividad se cobran juntos en un único pedido porque
// Inscripcion_Actividad.id_membresia es NOT NULL: el abono se cuelga de la
// membresía. En dos llamadas habría una ventana en la que el plan quedó pago
// sin membresía a la que atarse — y si la segunda falla, el socio pagó algo
// que no existe.

import { pedir } from './api';
import type { MiCuota } from './socioService';

export type MetodoPago =
  | 'EFECTIVO'
  | 'DEBITO'
  | 'CREDITO'
  | 'TRANSFERENCIA'
  | 'BILLETERA_VIRTUAL';

// --- Estado de cuenta ---

export interface DeudaListada {
  idDeuda: number;
  monto: number;
  fechaGeneracion: string;
  fechaVencimiento?: string;
  observaciones?: string;
}

export interface PagoListado {
  idPago: number;
  monto: number;
  metodo: MetodoPago;
  fechaPago: string;
  periodoDesde?: string;
  periodoHasta?: string;
  estado: string;
  numeroComprobante?: string;
}

export interface EstadoCuenta {
  idSocio: number;
  socio: string;
  numeroSocio?: string;
  alDia: boolean;
  plan?: string;
  vencimiento?: string;
  diasRestantes?: number;
  deudaTotal: number;
  deudas: DeudaListada[];
  ultimosPagos: PagoListado[];
}

interface PagoApi {
  id_pago: number;
  monto: number;
  metodo: MetodoPago;
  fecha_pago: string;
  periodo_desde: string | null;
  periodo_hasta: string | null;
  estado: string;
  numero_comprobante: string | null;
}

interface DeudaApi {
  id_deuda: number;
  monto: number;
  fecha_generacion: string;
  fecha_vencimiento: string | null;
  observaciones: string | null;
}

interface EstadoCuentaApi {
  id_socio: number;
  socio: string;
  numero_socio: string | null;
  al_dia: boolean;
  membresia_actual: {
    tipo: string;
    precio_pactado: number;
    fecha_inicio: string;
    fecha_vencimiento: string | null;
    dias_restantes: number | null;
  } | null;
  deuda_total: number;
  deudas: DeudaApi[];
  ultimos_pagos: PagoApi[];
}

function aPago(p: PagoApi): PagoListado {
  return {
    idPago: p.id_pago,
    monto: p.monto,
    metodo: p.metodo,
    fechaPago: p.fecha_pago,
    periodoDesde: p.periodo_desde ?? undefined,
    periodoHasta: p.periodo_hasta ?? undefined,
    estado: p.estado,
    numeroComprobante: p.numero_comprobante ?? undefined,
  };
}

function aDeuda(d: DeudaApi): DeudaListada {
  return {
    idDeuda: d.id_deuda,
    monto: d.monto,
    fechaGeneracion: d.fecha_generacion,
    fechaVencimiento: d.fecha_vencimiento ?? undefined,
    observaciones: d.observaciones ?? undefined,
  };
}

/**
 * Todo lo que el mostrador necesita ver antes de cobrarle a alguien.
 *
 * `alDia` son DOS condiciones, no una: tener membresía vigente Y no deber
 * nada. Alguien puede tener la cuota del mes paga y arrastrar una deuda
 * vieja, y ese caso no es "al día".
 */
export async function obtenerEstadoCuenta(idSocio: number): Promise<EstadoCuenta> {
  const d = await pedir<EstadoCuentaApi>(`/cobros/socio/${idSocio}`);
  return {
    idSocio: d.id_socio,
    socio: d.socio,
    numeroSocio: d.numero_socio ?? undefined,
    alDia: d.al_dia,
    plan: d.membresia_actual?.tipo,
    vencimiento: d.membresia_actual?.fecha_vencimiento ?? undefined,
    diasRestantes: d.membresia_actual?.dias_restantes ?? undefined,
    deudaTotal: d.deuda_total,
    deudas: d.deudas.map(aDeuda),
    ultimosPagos: d.ultimos_pagos.map(aPago),
  };
}

// listarDeudasPendientes se eliminó: el esquema nuevo no tiene tabla Deuda.
// El estado "debe" se deriva de no tener membresía vigente (prepago puro).

// --- Cobro ---

export interface MembresiaCobrada {
  idMembresia: number;
  plan: string;
  vencimiento: string;
  monto: number;
}

export interface AbonoCobrado {
  idInscripcion: number;
  actividad: string;
  plan: string;
  clasesRestantes?: number;
  vencimiento: string;
  monto: number;
}

export interface CobroRealizado {
  membresia: MembresiaCobrada;
  /** Solo si se cobró el combo con abono de actividad. */
  abono?: AbonoCobrado;
  deudasSaldadas: number;
  total: number;
  mensaje: string;
  /**
   * Qué promoción se aplicó y cuánto ahorró. Van aparte de `total` porque el
   * comprobante muestra las tres cifras —lista, descuento y final— y con el
   * total solo no se puede reconstruir cuánto se descontó.
   */
  promocion?: string;
  precioLista?: number;
  descuento?: number;
}

interface CobroApi {
  pago: PagoApi;
  membresia: {
    id_membresia: number;
    tipo: string;
    fecha_vencimiento: string | null;
    precio_pactado: number;
  };
  inscripcion: {
    id_inscripcion: number;
    actividad: string;
    plan: string;
    clases_restantes: number | null;
    fecha_vencimiento: string;
    precio_pactado: number;
  } | null;
  deudas_saldadas: DeudaApi[];
  total: number;
  mensaje: string;
  promocion: string | null;
  precio_lista: number | null;
  descuento: number | null;
}

/**
 * Cobra una membresía nueva o una renovación — es la misma operación, porque
 * en el esquema no hay diferencia: siempre es una fila NUEVA de Membresia,
 * nunca se pisa la anterior. Eso es lo que deja el historial de cuándo estuvo
 * al día y cuándo no.
 *
 * Si la vigente todavía no venció, la nueva arranca DESPUÉS de ese
 * vencimiento: quien paga por adelantado no pierde los días que le quedaban.
 *
 * Con `idPlanActividad` cobra además un abono de actividad, en la misma
 * transacción. Ese abono vence junto con la membresía: si la membresía cubre
 * más, los días de diferencia van sin cargo. Un abono que sobreviva a la
 * membresía dejaría al socio con clases disponibles y sin derecho a entrar.
 */
export async function cobrar(
  idSocio: number,
  idTipoMembresia: number,
  metodo: MetodoPago,
  opciones: {
    idPlanActividad?: number;
    numeroComprobante?: string;
    /**
     * Descuento a aplicar. Viaja el ID y NO el monto ya descontado: si el
     * cliente mandara el precio final, cualquiera con la consola abierta se
     * regalaría la membresía. El backend busca la promo, verifica que esté
     * vigente y recalcula.
     */
    idPromocion?: number;
  } = {},
): Promise<CobroRealizado> {
  const d = await pedir<CobroApi>('/cobros', {
    metodo: 'POST',
    cuerpo: {
      id_socio: idSocio,
      id_tipo_membresia: idTipoMembresia,
      metodo,
      id_plan_actividad: opciones.idPlanActividad ?? null,
      numero_comprobante: opciones.numeroComprobante ?? null,
      id_promocion: opciones.idPromocion ?? null,
      saldar_deudas: true,
    },
  });

  return {
    membresia: {
      idMembresia: d.membresia.id_membresia,
      plan: d.membresia.tipo,
      vencimiento: d.membresia.fecha_vencimiento ?? '',
      monto: d.membresia.precio_pactado,
    },
    abono: d.inscripcion
      ? {
          idInscripcion: d.inscripcion.id_inscripcion,
          actividad: d.inscripcion.actividad,
          plan: d.inscripcion.plan,
          clasesRestantes: d.inscripcion.clases_restantes ?? undefined,
          vencimiento: d.inscripcion.fecha_vencimiento,
          monto: d.inscripcion.precio_pactado,
        }
      : undefined,
    deudasSaldadas: d.deudas_saldadas.length,
    total: d.total,
    mensaje: d.mensaje,
    promocion: d.promocion ?? undefined,
    precioLista: d.precio_lista ?? undefined,
    descuento: d.descuento ?? undefined,
  };
}

// pagarDeuda se eliminó junto con el endpoint /cobros/deudas/{id}/pagar: ya no
// hay deudas que saldar aparte. Renovar la membresía (cobrar) es lo que pone
// al socio al día.

/**
 * Anula un pago mal registrado. NO lo borra: le pone estado CANCELADO.
 *
 * Un registro contable que desaparece es un agujero en la caja. Y anular
 * revierte todo lo que ese pago habilitó — cancela la membresía y vuelve a
 * dejar pendientes las deudas que había saldado. Sin eso, anular un cobro le
 * dejaría al socio el mes pago y las deudas perdonadas de regalo.
 */
export async function anularPago(idPago: number): Promise<PagoListado> {
  const p = await pedir<PagoApi>(`/cobros/pagos/${idPago}/anular`, { metodo: 'POST' });
  return aPago(p);
}

// --- Catálogo de planes ---

export interface TipoMembresiaOpcion {
  idTipoMembresia: number;
  nombre: string;
  duracionDias: number;
  precio: number;
}

export async function listarTiposMembresia(): Promise<TipoMembresiaOpcion[]> {
  const datos = await pedir<{
    id_tipo_membresia: number;
    nombre: string;
    duracion_dias: number;
    precio_actual: number;
    activo: boolean;
  }[]>('/cobros/tipos-membresia');

  return datos
    .filter((t) => t.activo)
    .map((t) => ({
      idTipoMembresia: t.id_tipo_membresia,
      nombre: t.nombre,
      duracionDias: t.duracion_dias,
      precio: t.precio_actual,
    }));
}

/**
 * Estado de cuenta de un socio, con la MISMA forma que devuelve el portal.
 *
 * La diferencia con getMiCuota() de socioService es de quién puede llamarla:
 * acá el id viaja como parámetro porque es el mostrador mirando la cuenta de
 * OTRA persona, y el permiso lo da la sección Cobros. En el portal no hay
 * parámetro: el socio solo puede ver la suya.
 *
 * Devuelve el mismo tipo a propósito — la pantalla de Cobros reusa los
 * componentes del portal para mostrar la cuenta, y dos formas distintas
 * obligarían a duplicarlos.
 */
export async function obtenerCuotaDeSocio(idSocio: number): Promise<MiCuota> {
  const d = await pedir<EstadoCuentaApi>(`/cobros/socio/${idSocio}`);
  const m = d.membresia_actual;

  return {
    tieneMembresia: m !== null,
    alDia: d.al_dia,
    plan: m?.tipo ?? 'Sin plan',
    estado: (m ? estadoDeMembresia(m.dias_restantes) : 'Sin membresía') as MiCuota['estado'],
    precioPactado: m?.precio_pactado ?? undefined,
    fechaInicio: m?.fecha_inicio ?? undefined,
    vencimiento: m?.fecha_vencimiento ?? undefined,
    diasParaVencer: m?.dias_restantes ?? undefined,
    deudas: d.deudas.map((x) => ({
      idDeuda: x.id_deuda,
      monto: x.monto,
      fechaGeneracion: x.fecha_generacion,
      fechaVencimiento: x.fecha_vencimiento ?? undefined,
      // El backend de gestión no lo calcula (el mostrador ve la fecha), así
      // que se deriva acá. Es el único lugar donde el cliente hace esta
      // cuenta, y no decide nada: solo pinta el "hace N días".
      diasDeAtraso: x.fecha_vencimiento
        ? Math.floor((Date.now() - new Date(x.fecha_vencimiento).getTime()) / 86_400_000)
        : 0,
      observaciones: x.observaciones ?? undefined,
    })),
    totalAdeudado: d.deuda_total,
    pagos: d.ultimos_pagos.map((p) => ({
      idPago: p.id_pago,
      fecha: p.fecha_pago,
      monto: p.monto,
      metodo: p.metodo,
      estado: p.estado,
      numeroComprobante: p.numero_comprobante ?? undefined,
    })),
  };
}

/** Mismo criterio que la sección Socios: 7 días de aviso antes de vencer. */
function estadoDeMembresia(dias: number | null): string {
  if (dias === null) return 'Activo';
  if (dias < 0) return 'Vencido';
  if (dias <= 7) return 'Por vencer';
  return 'Activo';
}
