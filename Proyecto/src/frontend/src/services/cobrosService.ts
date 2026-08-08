// Cobros (especificacion_definitiva_actividades.md, Fase 4: "Cobros
// (ampliar): además de membresía, cobrar plan de actividad y clase suelta,
// con las validaciones de reglas 1 y 8"). "Ampliar" asume que ya existía un
// cobro de membresía — no existía: membresiaService.ts es de sólo lectura
// (estados derivados), crearMembresiaInicial (sociosService.ts) es privada
// y no genera Pago, y no hay ningún pagarDeuda en todo el proyecto. Así que
// esto es la base entera, no una extensión.
//
// Vive en su propio archivo y no adentro de membresiaService.ts/
// socioService.ts porque el flujo de caja de recepción cruza tres dominios
// bajo una sola pantalla: Membresia, Deuda, y — reusando actividadService.ts
// tal cual, sin duplicar sus 8 reglas — Plan_Actividad/Turno.
// socioService.ts es explícito en su comentario de getMiCuota: "acá no hay
// un pagarDeuda(), ni siquiera comentado" porque esa pantalla es de
// consulta del socio, no de cobro — este archivo es exactamente lo que
// falta del otro lado del mostrador.
//
// getMiCuota (socioService.ts) se reutiliza tal cual para el estado de
// cuenta: ya es de sólo lectura y ya toma idSocio como parámetro plano, sin
// nada atado a la sesión del socio que la llama.

import type { Membresia, Pago, TipoMembresia } from '../types';
import { ServiceError, delay } from './api';
import { registrarAuditoria } from './auditoriaService';
import { membresiaVigente } from './membresiaService';
import {
  comprarPlan,
  tieneDeudaPendiente,
  vencimientoDePlanComprado,
  type InscripcionListada,
} from './actividadService';
import { aFechaISO, aTimestampISO, parsearFecha, sumarDias } from '../utils/fechas';
import { formatearFechaConAnio } from '../utils/format';
import {
  socios,
  membresias,
  deudas,
  pagos,
  tiposMembresia,
  planesActividad,
  sedes,
  siguienteId,
} from './mockDb';

function resolverSocio(idSocio: number) {
  const socio = socios.find((s) => s.id_socio === idSocio);
  if (!socio) throw new ServiceError(404, 'El socio no existe');
  return socio;
}

function sedeActiva() {
  const sede = sedes.find((s) => s.activo);
  if (!sede) throw new ServiceError(500, 'No hay ninguna sede activa configurada');
  return sede;
}

export interface MembresiaCobrada {
  idMembresia: number;
  plan: string;
  vencimiento: string;
  monto: number;
}

/**
 * Cobra una membresía nueva o una renovación — es la misma operación,
 * porque en el esquema no hay diferencia entre las dos: siempre es una fila
 * NUEVA de Membresia (historial, igual que Inscripcion_Actividad), nunca se
 * pisa la anterior. Si la vigente todavía no venció, la nueva arranca
 * DESPUÉS de ese vencimiento (no se pierden los días ya pagados); si venció
 * o no tiene ninguna, arranca hoy.
 */
function resolverTipoMembresia(idTipoMembresia: number): TipoMembresia {
  const tipo = tiposMembresia.find((t) => t.id_tipo_membresia === idTipoMembresia && t.activo);
  if (!tipo) throw new ServiceError(404, 'El tipo de membresía no existe');
  return tipo;
}

/**
 * Desde/hasta que le corresponde a una renovación. `cubrirHasta` sólo lo
 * usa el combo: estira el vencimiento si el período normal del tipo no
 * llegara a cubrir el plan que se cobra junto (ver cobrarMembresiaYPlan).
 */
function periodoDeRenovacion(
  idSocio: number,
  tipo: TipoMembresia,
  hoy: Date,
  cubrirHasta?: Date,
): { inicio: Date; vencimiento: Date } {
  const vigente = membresiaVigente(idSocio);
  const vencimientoVigente = vigente?.fecha_vencimiento ? parsearFecha(vigente.fecha_vencimiento) : undefined;
  const inicio = vencimientoVigente && vencimientoVigente > hoy ? vencimientoVigente : hoy;
  const normal = sumarDias(inicio, tipo.duracion_dias);
  return { inicio, vencimiento: cubrirHasta && cubrirHasta > normal ? cubrirHasta : normal };
}

/** Escribe la Membresia + su Pago. Sin validaciones: las hace quien la llama. */
function registrarMembresiaCobrada(
  idSocio: number,
  tipo: TipoMembresia,
  metodo: Pago['metodo'],
  hoy: Date,
  periodo: { inicio: Date; vencimiento: Date },
  idUsuarioActor?: number,
): MembresiaCobrada {
  const membresia: Membresia = {
    id_membresia: siguienteId.membresia(),
    id_socio: idSocio,
    id_tipo_membresia: tipo.id_tipo_membresia,
    precio_pactado: tipo.precio_actual,
    fecha_inicio: aFechaISO(periodo.inicio),
    fecha_vencimiento: aFechaISO(periodo.vencimiento),
    estado: 'ACTIVA',
  };
  membresias.push(membresia);

  pagos.push({
    id_pago: siguienteId.pago(),
    id_socio: idSocio,
    id_membresia: membresia.id_membresia,
    id_sede: sedeActiva().id_sede,
    metodo,
    monto: tipo.precio_actual,
    fecha_pago: aTimestampISO(hoy),
    es_adelanto: false,
    estado: 'CONFIRMADO',
    id_registrado_por: idUsuarioActor,
  });

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Membresia',
    id_entidad: membresia.id_membresia,
    accion: 'ALTA',
    detalle: `Cobro de ${tipo.nombre}`,
  });

  return {
    idMembresia: membresia.id_membresia,
    plan: tipo.nombre,
    vencimiento: membresia.fecha_vencimiento as string,
    monto: tipo.precio_actual,
  };
}

export async function cobrarMembresia(
  idSocio: number,
  idTipoMembresia: number,
  metodo: Pago['metodo'],
  idUsuarioActor?: number,
): Promise<MembresiaCobrada> {
  await delay();
  resolverSocio(idSocio);
  const tipo = resolverTipoMembresia(idTipoMembresia);
  const hoy = new Date();
  return registrarMembresiaCobrada(idSocio, tipo, metodo, hoy, periodoDeRenovacion(idSocio, tipo, hoy), idUsuarioActor);
}

export interface ComboCobrado {
  membresia: MembresiaCobrada;
  inscripcion: InscripcionListada;
  total: number;
}

/**
 * Combo "renovar membresía + cobrar plan de actividad" en una sola
 * operación. Existe porque en un gimnasio real pasa todo el tiempo: la
 * membresía vence a mitad de mes y el plan de actividad siempre se cobra
 * por mes completo (REGLA 1), así que sin renovar no entra.
 *
 * Dos cosas que ESTA función garantiza y que encadenar las dos llamadas
 * desde la vista no garantizaba:
 *
 * 1. **No cobra la membresía si el plan igual va a rebotar.** Todo lo que
 *    puede rechazar el plan por adelantado (que exista, que esté activo,
 *    que no haya deuda — REGLA 8) se valida ANTES de escribir nada.
 * 2. **La renovación alcanza siempre.** Un tipo "mensual" de 30 días NO
 *    cubre un mes calendario de 31 días, que son la mayoría: renovar y
 *    después comprar fallaba por un día. Acá el vencimiento se estira
 *    hasta cubrir el plan (`cubrirHasta`). Es una decisión de negocio
 *    explícita del combo: los días de diferencia van sin cargo. El
 *    vencimiento real vuelve en el resultado y la vista lo confirma en
 *    pantalla apenas se cobra.
 */
export async function cobrarMembresiaYPlan(
  idSocio: number,
  idTipoMembresia: number,
  idPlanActividad: number,
  metodo: Pago['metodo'],
  idUsuarioActor?: number,
): Promise<ComboCobrado> {
  await delay();
  resolverSocio(idSocio);
  const tipo = resolverTipoMembresia(idTipoMembresia);

  // --- Todo lo que puede rebotar, ANTES de tocar la caja ---
  const plan = planesActividad.find((p) => p.id_plan_actividad === idPlanActividad && p.activo);
  if (!plan) throw new ServiceError(404, 'El plan no existe');
  if (tieneDeudaPendiente(idSocio)) {
    throw new ServiceError(403, 'Tiene una deuda pendiente. Cobrala primero.');
  }

  const hoy = new Date();
  const periodo = periodoDeRenovacion(idSocio, tipo, hoy, vencimientoDePlanComprado(hoy));
  const membresia = registrarMembresiaCobrada(idSocio, tipo, metodo, hoy, periodo, idUsuarioActor);

  // Con la membresía ya cubriendo el mes entero, comprarPlan no puede
  // rechazar por REGLA 1. Si aun así fallara, queda auditado que la
  // membresía se cobró: es una fila propia de Pago, no se pierde.
  const inscripcion = await comprarPlan(idSocio, idPlanActividad, idUsuarioActor, metodo);

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Membresia',
    id_entidad: membresia.idMembresia,
    accion: 'MODIFICACION',
    detalle: `Combo con "${plan.nombre}" — cubre hasta ${formatearFechaConAnio(periodo.vencimiento)}`,
  });

  return { membresia, inscripcion, total: membresia.monto + plan.precio };
}

/**
 * Salda una deuda puntual — no todas las del socio, una por una, para que
 * quede clara la relación 1 a 1 con el Pago que la cancela
 * (Deuda.id_pago_cancelatorio, columna del esquema que hasta ahora no la
 * escribía nadie).
 */
export async function pagarDeuda(
  idSocio: number,
  idDeuda: number,
  metodo: Pago['metodo'],
  idUsuarioActor?: number,
): Promise<void> {
  await delay();
  resolverSocio(idSocio);
  const deuda = deudas.find((d) => d.id_deuda === idDeuda && d.id_socio === idSocio);
  if (!deuda) throw new ServiceError(404, 'La deuda no existe');
  if (deuda.estado !== 'PENDIENTE') throw new ServiceError(400, 'Esa deuda ya no está pendiente');

  const pago: Pago = {
    id_pago: siguienteId.pago(),
    id_socio: idSocio,
    id_membresia: deuda.id_membresia,
    id_sede: sedeActiva().id_sede,
    metodo,
    monto: deuda.monto,
    fecha_pago: aTimestampISO(new Date()),
    es_adelanto: false,
    estado: 'CONFIRMADO',
    id_registrado_por: idUsuarioActor,
  };
  pagos.push(pago);

  deuda.estado = 'PAGADA';
  deuda.id_pago_cancelatorio = pago.id_pago;

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Deuda',
    id_entidad: idDeuda,
    accion: 'MODIFICACION',
    detalle: 'Pagada en recepción',
  });
}
