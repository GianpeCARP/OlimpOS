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

/** Todas las deudas pendientes del gimnasio, la más vieja primero. */
export async function listarDeudasPendientes(): Promise<(DeudaListada & { socio: string })[]> {
  const datos = await pedir<(DeudaApi & { socio: string })[]>('/cobros/deudas');
  return datos.map((d) => ({ ...aDeuda(d), socio: d.socio }));
}

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
  opciones: { idPlanActividad?: number; numeroComprobante?: string } = {},
): Promise<CobroRealizado> {
  const d = await pedir<CobroApi>('/cobros', {
    metodo: 'POST',
    cuerpo: {
      id_socio: idSocio,
      id_tipo_membresia: idTipoMembresia,
      metodo,
      id_plan_actividad: opciones.idPlanActividad ?? null,
      numero_comprobante: opciones.numeroComprobante ?? null,
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
  };
}

/**
 * Cobra UNA deuda puntual, sin renovar la membresía.
 *
 * Es el caso de quien viene a ponerse al día pero todavía no renueva. El
 * monto lo pone la deuda: cobrar $1 una deuda de $30.000 sería tan grave como
 * en el cobro de membresía.
 *
 * Deja registrada la relación 1 a 1 entre la deuda y el pago que la canceló,
 * así después se puede responder "¿con qué pago se saldó esto?" sin cruzar
 * montos y fechas a ojo.
 */
export async function pagarDeuda(
  idDeuda: number,
  metodo: MetodoPago,
  numeroComprobante?: string,
): Promise<PagoListado> {
  const p = await pedir<PagoApi>(`/cobros/deudas/${idDeuda}/pagar`, {
    metodo: 'POST',
    cuerpo: { metodo, numero_comprobante: numeroComprobante ?? null },
  });
  return aPago(p);
}

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
