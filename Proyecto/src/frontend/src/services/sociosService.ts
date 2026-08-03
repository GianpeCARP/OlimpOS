// Mock de estructura_socios.md: listado con búsqueda/filtro/orden, alta y
// edición desde el panel interno (distinto del auto-registro público de
// auth.spec.md 3.1: acá el alta la hace el staff, sin usuario/contraseña —
// muchos socios de gimnasio nunca abren la app).
//
// Igual que authService/dashboardService, todo se apoya en mockDb.ts: un
// alta hecha acá aparece de inmediato en el dashboard, y viceversa.

import type { Persona, Socio, TipoMembresia } from '../types';
import type { EstadoSocioValue } from '../config';
import { aFechaISO, aTimestampISO, sumarDias } from '../utils/fechas';
import { nombreCompleto } from '../utils/personas';
import { ServiceError, delay } from './api';
import { registrarAuditoria } from './auditoriaService';
import { esEmailValido, limpiar } from './validacion';
import { darDeBaja, reactivarSocio as reactivarSocioAuth } from './authService';
import { estadoDeSocio, membresiaVigente, nombrePlan } from './membresiaService';
import {
  personas,
  socios,
  telefonos,
  sedes,
  membresias,
  tiposMembresia,
  siguienteId,
  proximoNumeroSocio,
} from './mockDb';

// --- Listado ---

export interface SocioListado {
  idSocio: number;
  idPersona: number;
  dni: string;
  nombre: string;
  apellido: string;
  nombreCompleto: string;
  email?: string;
  telefono?: string;
  idTipoMembresia?: number;
  plan: string;
  estado: EstadoSocioValue;
  /** Vencimiento de la membresía vigente, o undefined si no tiene una. */
  vencimiento?: string;
  activo: boolean;
}

function telefonoPrincipal(idPersona: number): string | undefined {
  const propios = telefonos.filter((t) => t.id_persona === idPersona);
  return (propios.find((t) => t.principal) ?? propios[0])?.numero;
}

function aSocioListado(socio: Socio, persona: Persona): SocioListado {
  const membresia = membresiaVigente(socio.id_socio);
  return {
    idSocio: socio.id_socio,
    idPersona: persona.id_persona,
    dni: persona.dni,
    nombre: persona.nombre,
    apellido: persona.apellido,
    nombreCompleto: nombreCompleto(persona),
    email: persona.email,
    telefono: telefonoPrincipal(persona.id_persona),
    idTipoMembresia: membresia?.id_tipo_membresia,
    plan: nombrePlan(socio.id_socio),
    estado: estadoDeSocio(socio),
    vencimiento: membresia?.fecha_vencimiento,
    activo: socio.activo,
  };
}

/**
 * Trae todos los socios sin filtrar. La búsqueda, los chips de estado y el
 * orden de columnas son responsabilidad de la vista (estructura_socios.md:
 * _update_table hace las tres cosas en memoria, sobre la lista completa que
 * ya tiene cargada) — así se mantiene un único fetch por visita a la
 * pantalla, igual que hacía la versión original en Flet.
 */
export async function listarSocios(): Promise<SocioListado[]> {
  await delay();
  return socios
    .map((socio) => {
      const persona = personas.find((p) => p.id_persona === socio.id_persona);
      return persona ? aSocioListado(socio, persona) : null;
    })
    .filter((s): s is SocioListado => s !== null);
}

/** Planes activos para el selector del formulario de alta/edición. */
export async function listarTiposMembresia(): Promise<TipoMembresia[]> {
  await delay();
  return tiposMembresia.filter((t) => t.activo);
}

// --- Alta (admin) ---

export interface CrearSocioInput {
  dni: string;
  nombre: string;
  apellido: string;
  // Opcionales acá y no en el registro público: el staff puede cargar un
  // socio en el momento y completar el contacto después.
  email?: string;
  telefono?: string;
  idTipoMembresia?: number;
}

function obtenerSedeActiva(): { id_sede: number } {
  const sede = sedes.find((s) => s.activo);
  if (!sede) {
    throw new ServiceError(500, 'No hay ninguna sede activa configurada');
  }
  return sede;
}

/** Crea la Membresia inicial de un socio recién dado de alta con plan. */
function crearMembresiaInicial(idSocio: number, tipo: TipoMembresia): void {
  const inicio = new Date();
  membresias.push({
    id_membresia: siguienteId.membresia(),
    id_socio: idSocio,
    id_tipo_membresia: tipo.id_tipo_membresia,
    precio_pactado: tipo.precio_actual,
    fecha_inicio: aFechaISO(inicio),
    fecha_vencimiento: aFechaISO(sumarDias(inicio, tipo.duracion_dias)),
    estado: 'ACTIVA',
  });
}

export async function crearSocio(
  input: CrearSocioInput,
  idUsuarioActor?: number,
): Promise<SocioListado> {
  await delay();

  const dni = limpiar(input.dni);
  const nombre = limpiar(input.nombre);
  const apellido = limpiar(input.apellido);
  const email = limpiar(input.email).toLowerCase() || undefined;
  const telefono = limpiar(input.telefono) || undefined;

  if (dni === '' || nombre === '' || apellido === '') {
    throw new ServiceError(400, 'DNI, nombre y apellido son obligatorios');
  }
  if (email && !esEmailValido(email)) {
    throw new ServiceError(400, 'El email no tiene un formato válido');
  }
  if (personas.some((p) => p.dni === dni)) {
    throw new ServiceError(409, 'Ya existe una persona con ese DNI');
  }
  if (email && personas.some((p) => p.email?.toLowerCase() === email)) {
    throw new ServiceError(409, 'Ese email ya está en uso');
  }

  let tipo: TipoMembresia | undefined;
  if (input.idTipoMembresia !== undefined) {
    tipo = tiposMembresia.find((t) => t.id_tipo_membresia === input.idTipoMembresia && t.activo);
    if (!tipo) {
      throw new ServiceError(400, 'El plan seleccionado no existe');
    }
  }

  const sede = obtenerSedeActiva();

  const persona: Persona = {
    id_persona: siguienteId.persona(),
    dni,
    nombre,
    apellido,
    email,
    fecha_alta: aTimestampISO(new Date()),
    activo: true,
  };
  personas.push(persona);

  if (telefono) {
    telefonos.push({
      id_telefono: siguienteId.telefono(),
      id_persona: persona.id_persona,
      numero: telefono,
      tipo: 'CELULAR',
      principal: true,
    });
  }

  const idSocio = siguienteId.socio();
  const socio: Socio = {
    id_socio: idSocio,
    id_persona: persona.id_persona,
    id_sede: sede.id_sede,
    numero_socio: proximoNumeroSocio(idSocio),
    fecha_alta: aFechaISO(new Date()),
    activo: true,
  };
  socios.push(socio);

  if (tipo) {
    crearMembresiaInicial(idSocio, tipo);
  }

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Socio',
    id_entidad: idSocio,
    accion: 'ALTA',
  });

  return aSocioListado(socio, persona);
}

// --- Edición ---

export interface EditarSocioInput {
  nombre: string;
  apellido: string;
  email?: string;
  telefono?: string;
  /** undefined = sin plan (cancela la membresía vigente, si tenía una). */
  idTipoMembresia?: number;
}

/** Deja al socio con el plan pedido: cambia, asigna o cancela la membresía vigente. */
function aplicarPlan(idSocio: number, idTipoMembresia: number | undefined): void {
  const vigente = membresiaVigente(idSocio);

  if (idTipoMembresia === undefined) {
    // "Sin plan asignado": no se borra el historial, se cancela la vigente.
    if (vigente && vigente.estado === 'ACTIVA') {
      vigente.estado = 'CANCELADA';
    }
    return;
  }

  const tipo = tiposMembresia.find((t) => t.id_tipo_membresia === idTipoMembresia && t.activo);
  if (!tipo) {
    throw new ServiceError(400, 'El plan seleccionado no existe');
  }

  if (vigente && vigente.estado === 'ACTIVA') {
    // Cambio de plan: se pisa el tipo/precio de la membresía en curso, no se
    // tocan las fechas — cambiar de plan no es lo mismo que renovar.
    vigente.id_tipo_membresia = tipo.id_tipo_membresia;
    vigente.precio_pactado = tipo.precio_actual;
    return;
  }

  // La membresía más reciente no está vigente (VENCIDA/CANCELADA/SUSPENDIDA)
  // y el formulario trae el MISMO plan que ya tenía. Eso no es pedir nada: es
  // el estado en que el modal abre por defecto (el <select> se precarga con
  // socio.idTipoMembresia, que sale de esa misma membresía vencida). Crear
  // una membresía nueva acá regalaba una renovación de 30 días —con su fecha
  // de vencimiento y su estado ACTIVA— cada vez que alguien abría "Editar" y
  // guardaba para corregir un teléfono, sin que se registrara ningún pago.
  //
  // Renovar es una acción propia, explícita y con cobro asociado; no un
  // efecto secundario de editar los datos de contacto. Hasta que exista esa
  // pantalla, editar deja la membresía como está.
  if (vigente && vigente.id_tipo_membresia === tipo.id_tipo_membresia) {
    return;
  }

  // Sin ninguna membresía previa, o con un plan DISTINTO al que tenía: acá sí
  // hay una decisión del usuario, se crea la membresía.
  crearMembresiaInicial(idSocio, tipo);
}

export async function actualizarSocio(
  idSocio: number,
  input: EditarSocioInput,
  idUsuarioActor?: number,
): Promise<SocioListado> {
  await delay();

  const socio = socios.find((s) => s.id_socio === idSocio);
  if (!socio) {
    throw new ServiceError(404, 'El socio no existe');
  }
  const persona = personas.find((p) => p.id_persona === socio.id_persona);
  if (!persona) {
    throw new ServiceError(404, 'El socio no existe');
  }

  const nombre = limpiar(input.nombre);
  const apellido = limpiar(input.apellido);
  const email = limpiar(input.email).toLowerCase() || undefined;
  const telefono = limpiar(input.telefono) || undefined;

  if (nombre === '' || apellido === '') {
    throw new ServiceError(400, 'Nombre y apellido son obligatorios');
  }
  if (email && !esEmailValido(email)) {
    throw new ServiceError(400, 'El email no tiene un formato válido');
  }
  if (email && personas.some((p) => p.id_persona !== persona.id_persona && p.email?.toLowerCase() === email)) {
    throw new ServiceError(409, 'Ese email ya está en uso');
  }

  persona.nombre = nombre;
  persona.apellido = apellido;
  persona.email = email;

  // El teléfono principal se reemplaza entero: es un solo campo en el
  // formulario, no una lista editable fila por fila (eso es una spec propia
  // que todavía no existe).
  const indicePrincipal = telefonos.findIndex(
    (t) => t.id_persona === persona.id_persona && t.principal,
  );
  if (telefono) {
    if (indicePrincipal >= 0) {
      telefonos[indicePrincipal].numero = telefono;
    } else {
      telefonos.push({
        id_telefono: siguienteId.telefono(),
        id_persona: persona.id_persona,
        numero: telefono,
        tipo: 'CELULAR',
        principal: true,
      });
    }
  } else if (indicePrincipal >= 0) {
    telefonos.splice(indicePrincipal, 1);
  }

  aplicarPlan(idSocio, input.idTipoMembresia);

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Socio',
    id_entidad: idSocio,
    accion: 'MODIFICACION',
  });

  return aSocioListado(socio, persona);
}

// --- Baja ---
//
// estructura_socios.md la llama "eliminar", pero borrar la fila rompería el
// historial de pagos/auditoría y el modelo real no tiene delete, tiene
// Baja (auth.spec.md 3.3) — reutiliza esa misma lógica en vez de duplicarla.
// 'ADMINISTRATIVA' porque acá la inicia el staff, no el socio.
export async function darDeBajaSocio(
  idSocio: number,
  motivo?: string,
  idUsuarioActor?: number,
): Promise<void> {
  await darDeBaja(idSocio, 'ADMINISTRATIVA', motivo, idUsuarioActor);
}

/** Camino de vuelta de darDeBajaSocio — reexportada con el nombre que usa esta vista. */
export async function reactivarSocio(idSocio: number, idUsuarioActor?: number): Promise<void> {
  await reactivarSocioAuth(idSocio, idUsuarioActor);
}
