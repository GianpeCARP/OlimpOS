// Sección Socios, conectada a la API real (routers/socios.py).
//
// Las firmas exportadas son las mismas que tenía la versión mock: las vistas
// no se tocaron. Lo único que cambió es el cuerpo de cada función — antes
// buscaba en arrays de mockDb, ahora hace un pedido HTTP.
//
// El `estado` y el `plan` YA VIENEN resueltos del backend. Antes se derivaban
// acá (estadoDeSocio en membresiaService), pero esa regla —los 7 días de
// aviso, qué gana entre "de baja" y "vencido"— tiene que valer igual en la
// PWA, en Flet y en cualquier reporte. Con la derivación en el servidor hay
// una sola versión de la verdad; con la derivación en el cliente había que
// mantener la misma lógica en tres lugares y el día que cambie, dos se
// olvidan.

import type { TipoMembresia } from '../types';
import type { EstadoSocioValue } from '../config';
import { pedir } from './api';

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
  /** "YYYY-MM-DD". */
  fechaNacimiento?: string;
  calle?: string;
  numeroCalle?: string;
  localidad?: string;
  /** Contacto de emergencia principal: se puede llamar desde la grilla. */
  emergenciaNombre?: string;
  emergenciaTelefono?: string;
  emergenciaParentesco?: string;
  /**
   * "YYYY-MM-DD" de la baja PROGRAMADA: pidió la baja con la cuota paga y
   * sigue activo hasta ese día (backend/bajas.py). Se puede anular.
   */
  bajaProgramada?: string;
  idTipoMembresia?: number;
  plan: string;
  estado: EstadoSocioValue;
  /** Vencimiento de la membresía vigente, o undefined si no tiene una. */
  vencimiento?: string;
  activo: boolean;
}

/** La forma exacta en que responde el backend (snake_case). */
interface SocioApi {
  id_socio: number;
  id_persona: number;
  dni: string;
  nombre: string;
  apellido: string;
  email: string | null;
  telefono: string | null;
  fecha_nacimiento?: string | null;
  calle?: string | null;
  numero_calle?: string | null;
  localidad?: string | null;
  emergencia_nombre?: string | null;
  emergencia_telefono?: string | null;
  emergencia_parentesco?: string | null;
  baja_programada?: string | null;
  id_tipo_membresia: number | null;
  plan: string;
  estado: string;
  vencimiento: string | null;
  activo: boolean;
}

/**
 * Traduce snake_case (backend) a camelCase (frontend).
 *
 * Vive en un solo lugar a propósito: si cada función hiciera su propia
 * conversión, agregar un campo obligaría a tocarlas todas y alcanzaría con
 * olvidarse de una para que esa pantalla muestre undefined.
 */
function aSocioListado(s: SocioApi): SocioListado {
  return {
    idSocio: s.id_socio,
    idPersona: s.id_persona,
    dni: s.dni,
    nombre: s.nombre,
    apellido: s.apellido,
    nombreCompleto: `${s.nombre} ${s.apellido}`.trim(),
    // `?? undefined` y no `?? ''`: el backend manda null cuando no hay dato,
    // y la vista distingue "sin teléfono" de "teléfono vacío".
    email: s.email ?? undefined,
    telefono: s.telefono ?? undefined,
    fechaNacimiento: s.fecha_nacimiento ?? undefined,
    calle: s.calle ?? undefined,
    numeroCalle: s.numero_calle ?? undefined,
    localidad: s.localidad ?? undefined,
    emergenciaNombre: s.emergencia_nombre ?? undefined,
    emergenciaTelefono: s.emergencia_telefono ?? undefined,
    emergenciaParentesco: s.emergencia_parentesco ?? undefined,
    bajaProgramada: s.baja_programada ?? undefined,
    idTipoMembresia: s.id_tipo_membresia ?? undefined,
    plan: s.plan,
    estado: s.estado as EstadoSocioValue,
    vencimiento: s.vencimiento ?? undefined,
    activo: s.activo,
  };
}

/**
 * Trae todos los socios sin filtrar. La búsqueda, los chips de estado y el
 * orden de columnas son responsabilidad de la vista, que los resuelve en
 * memoria sobre la lista completa — así se mantiene un único fetch por visita
 * a la pantalla.
 */
export async function listarSocios(): Promise<SocioListado[]> {
  const datos = await pedir<SocioApi[]>('/socios');
  return datos.map(aSocioListado);
}

// =========================================================================
// TELÉFONOS DE LA FICHA
// =========================================================================
//
// `Telefono` siempre fue una tabla —una persona tiene el celular, el de la
// casa, el del trabajo— pero la ficha la usaba como si fuera una columna:
// `SocioListado.telefono` es el PRINCIPAL, que el backend aplana para el
// listado, y era el único que se podía cargar.
//
// Estas funciones manejan todos los demás. Van por endpoints propios y no por
// el PUT de la ficha porque agregar un número no es editar la ficha: pasa en
// otro momento y no tiene por qué arrastrar nombre, email y objetivo en el
// mismo pedido (ver routers/socios.py).

export type TipoTelefono = 'CELULAR' | 'FIJO';

export interface TelefonoDeSocio {
  idTelefono: number;
  numero: string;
  tipo: TipoTelefono;
  /** El que sale en el listado y al que se llama primero. Hay uno solo. */
  principal: boolean;
}

interface TelefonoApi {
  id_telefono: number;
  numero: string;
  tipo: string | null;
  principal: boolean;
}

function aTelefono(t: TelefonoApi): TelefonoDeSocio {
  return {
    idTelefono: t.id_telefono,
    numero: t.numero,
    // El ENUM de la base sólo tiene estos dos; cualquier otra cosa (o null,
    // que la columna admite) se muestra como celular, que es el caso común.
    tipo: t.tipo === 'FIJO' ? 'FIJO' : 'CELULAR',
    principal: t.principal,
  };
}

export interface TelefonoInput {
  numero: string;
  tipo: TipoTelefono;
  principal: boolean;
}

export async function listarTelefonos(idSocio: number): Promise<TelefonoDeSocio[]> {
  const datos = await pedir<TelefonoApi[]>(`/socios/${idSocio}/telefonos`);
  return datos.map(aTelefono);
}

export async function agregarTelefono(
  idSocio: number,
  input: TelefonoInput,
): Promise<TelefonoDeSocio> {
  const datos = await pedir<TelefonoApi>(`/socios/${idSocio}/telefonos`, {
    metodo: 'POST',
    cuerpo: { numero: input.numero.trim(), tipo: input.tipo, principal: input.principal },
  });
  return aTelefono(datos);
}

export async function editarTelefono(
  idSocio: number,
  idTelefono: number,
  input: TelefonoInput,
): Promise<TelefonoDeSocio> {
  const datos = await pedir<TelefonoApi>(`/socios/${idSocio}/telefonos/${idTelefono}`, {
    metodo: 'PUT',
    cuerpo: { numero: input.numero.trim(), tipo: input.tipo, principal: input.principal },
  });
  return aTelefono(datos);
}

export async function borrarTelefono(idSocio: number, idTelefono: number): Promise<void> {
  await pedir<void>(`/socios/${idSocio}/telefonos/${idTelefono}`, { metodo: 'DELETE' });
}

/** La forma en que el backend devuelve los planes. */
interface TipoMembresiaApi {
  id_tipo_membresia: number;
  nombre: string;
  descripcion: string | null;
  duracion_dias: number;
  precio_actual: number;
  activo: boolean;
}

/** Planes activos para el selector del formulario de alta/edición. */
export async function listarTiposMembresia(): Promise<TipoMembresia[]> {
  const datos = await pedir<TipoMembresiaApi[]>('/cobros/tipos-membresia');
  return datos
    .filter((t) => t.activo)
    .map((t) => ({
      id_tipo_membresia: t.id_tipo_membresia,
      nombre: t.nombre,
      descripcion: t.descripcion ?? undefined,
      duracion_dias: t.duracion_dias,
      precio_actual: t.precio_actual,
      activo: t.activo,
    }));
}

// --- Datos personales (alta y edición) ---

/** Fecha de nacimiento, domicilio y contacto de emergencia. Todos opcionales. */
export interface DatosPersonalesSocio {
  fechaNacimiento?: string;
  calle?: string;
  numeroCalle?: string;
  localidad?: string;
  emergenciaNombre?: string;
  emergenciaTelefono?: string;
  emergenciaParentesco?: string;
}

/** Vacío viaja como null: el backend distingue "no hay dato" de un texto en blanco. */
function cuerpoDatosPersonales(d: DatosPersonalesSocio = {}) {
  return {
    fecha_nacimiento: d.fechaNacimiento || null,
    calle: d.calle?.trim() || null,
    numero_calle: d.numeroCalle?.trim() || null,
    localidad: d.localidad?.trim() || null,
    emergencia_nombre: d.emergenciaNombre?.trim() || null,
    emergencia_telefono: d.emergenciaTelefono?.trim() || null,
    emergencia_parentesco: d.emergenciaParentesco?.trim() || null,
  };
}

// --- Alta ---

export interface CrearSocioInput {
  dni: string;
  nombre: string;
  apellido: string;
  // Opcionales: el staff puede cargar un socio en el momento y completar el
  // contacto después.
  email?: string;
  telefono?: string;
  // Los pide el alta desde el 2026-09-16: antes el backend los aceptaba y
  // ninguna pantalla los preguntaba, así que nadie los tenía cargados.
  datosPersonales?: DatosPersonalesSocio;
  // Acá había `idTipoMembresia`, y no se mandaba nunca: el formulario dejaba
  // elegir un plan y el socio quedaba SIN membresía, sin ningún aviso. Se sacó
  // el 2026-09-16. El plan no es un dato del socio: es una Membresía, y se
  // crea cobrándola (Cobros). El alta ofrece "Cobrar ahora" para eso.
}

/**
 * Respuesta del alta. Incluye las credenciales que generó el sistema.
 *
 * `passwordTemporal` es la ÚNICA vez que esa contraseña existe legible: en la
 * base solo queda su hash. Hay que mostrarla en pantalla para que el mostrador
 * se la dicte al socio — y no guardarla ni loguearla en ningún lado.
 */
export interface AltaSocioResultado {
  socio: SocioListado;
  username?: string;
  passwordTemporal?: string;
  mensaje: string;
  emailEnviado: boolean;
  /** Mensaje ya armado para copiar y mandar por WhatsApp si el mail no salió. */
  textoCredenciales?: string;
}

interface AltaSocioApi {
  id_socio: number;
  numero_socio: string;
  persona: { id_persona: number; dni: string; nombre: string; apellido: string; email: string | null };
  username: string | null;
  password_temporal: string | null;
  mensaje: string;
  email_enviado: boolean;
  texto_credenciales: string | null;
}

/**
 * Alta desde el mostrador ("registro por invitación").
 *
 * El backend crea Persona + Teléfono + Socio + Usuario en UNA transacción y
 * genera las credenciales. No se le manda contraseña: la elige el sistema, y
 * la cuenta nace obligada a cambiarla en el primer ingreso.
 *
 * `idSede` no se pide al formulario todavía: no existe la pantalla de sedes,
 * así que se usa la primera. Cuando exista, sale del selector.
 */
export async function crearSocio(input: CrearSocioInput): Promise<AltaSocioResultado> {
  const datos = await pedir<AltaSocioApi>('/socios', {
    metodo: 'POST',
    cuerpo: {
      dni: input.dni.trim(),
      nombre: input.nombre.trim(),
      apellido: input.apellido.trim(),
      email: input.email?.trim() || null,
      telefono: input.telefono?.trim() || null,
      ...cuerpoDatosPersonales(input.datosPersonales),
      id_sede: 1,
      crear_cuenta: true,
    },
  });

  // El alta devuelve la persona, no la fila de listado completa. Se relee el
  // socio para que quien llame reciba lo mismo que devuelve listarSocios y la
  // tabla pueda insertarlo sin refrescar todo.
  const socio = await obtenerSocio(datos.id_socio);

  return {
    socio,
    username: datos.username ?? undefined,
    passwordTemporal: datos.password_temporal ?? undefined,
    mensaje: datos.mensaje,
    emailEnviado: datos.email_enviado,
    textoCredenciales: datos.texto_credenciales ?? undefined,
  };
}

export async function obtenerSocio(idSocio: number): Promise<SocioListado> {
  const datos = await pedir<SocioApi>(`/socios/${idSocio}`);
  return aSocioListado(datos);
}

// --- Edición ---

export interface EditarSocioInput {
  nombre: string;
  apellido: string;
  email?: string;
  telefono?: string;
  objetivo?: string;
  datosPersonales?: DatosPersonalesSocio;
}

/**
 * Edita los datos de contacto de un socio.
 *
 * NO toca la membresía, y es deliberado. La versión mock intentaba aplicar
 * cambios de plan desde acá, y el comentario que quedó documentado explicaba
 * el bug que eso producía: abrir "Editar" para corregir un teléfono y guardar
 * regalaba una renovación de 30 días, con su fecha de vencimiento y su estado
 * ACTIVA, sin que se registrara ningún pago.
 *
 * La conclusión de ese comentario es la que ahora se aplica de verdad:
 * "renovar es una acción propia, explícita y con cobro asociado; no un efecto
 * secundario de editar los datos de contacto". Los cambios de plan van por la
 * sección Cobros, que registra el pago junto con la membresía.
 */
export async function actualizarSocio(
  idSocio: number,
  input: EditarSocioInput,
): Promise<SocioListado> {
  const datos = await pedir<SocioApi>(`/socios/${idSocio}`, {
    metodo: 'PUT',
    cuerpo: {
      nombre: input.nombre.trim(),
      apellido: input.apellido.trim(),
      email: input.email?.trim() || null,
      telefono: input.telefono?.trim() ?? null,
      objetivo: input.objetivo?.trim() || null,
      ...cuerpoDatosPersonales(input.datosPersonales),
    },
  });
  return aSocioListado(datos);
}

// --- Baja ---
//
// La vista la llama "eliminar", pero borrar la fila rompería el historial de
// pagos y asistencias — y esos datos siguen siendo del gimnasio aunque la
// persona se haya ido. El backend hace baja lógica: registra el motivo en la
// tabla Baja, cancela la membresía vigente y desactiva la cuenta de acceso.
//
// 'ADMINISTRATIVA' porque acá la inicia el staff, no el socio.

/**
 * `inmediata` = cortar HOY aunque tenga la cuota paga (pierde los días que le
 * quedaban). Sin eso, con la cuota paga la baja queda programada al vencimiento.
 */
export async function darDeBajaSocio(
  idSocio: number,
  opciones: { inmediata?: boolean; motivo?: string } = {},
): Promise<SocioListado> {
  const datos = await pedir<SocioApi>(`/socios/${idSocio}/baja`, {
    metodo: 'POST',
    cuerpo: {
      tipo: 'ADMINISTRATIVA',
      motivo: opciones.motivo?.trim() || null,
      inmediata: opciones.inmediata ?? false,
    },
  });
  return aSocioListado(datos);
}

/**
 * Camino de vuelta. El socio vuelve SIN membresía: hay que cobrarle de nuevo.
 * Reactivar la vieja le regalaría los días que pasaron mientras estuvo de baja.
 */
/** Anula una baja programada que todavía no corrió (el socio cambió de idea). */
export async function anularBajaSocio(idSocio: number): Promise<SocioListado> {
  const datos = await pedir<SocioApi>(`/socios/${idSocio}/anular-baja`, { metodo: 'POST' });
  return aSocioListado(datos);
}

export async function reactivarSocio(idSocio: number): Promise<SocioListado> {
  const datos = await pedir<SocioApi>(`/socios/${idSocio}/reactivar`, { metodo: 'POST' });
  return aSocioListado(datos);
}

// =========================================================================
// ENTRENADOR A CARGO
// =========================================================================
//
// Quién entrena a quién. Vive en Asignacion_Entrenador desde la migración 003,
// que sacó la vieja columna Socio.id_entrenador_a_cargo.
//
// Esa columna cometía el mismo error que Telefono ya evitaba: meter en un
// campo de valor único un hecho que en la realidad es MÚLTIPLE —un socio puede
// tener a la vez uno de musculación y otro de funcional— y CAMBIANTE, porque
// reasignar pisaba el valor anterior y el historial se perdía.
//
// DOS PERMISOS DISTINTOS, y no es un detalle:
//   - LEER la lista pide sólo la sección SOCIOS (el Entrenador la tiene en
//     LECTURA), así que la ve todo el que ve la grilla.
//   - ASIGNAR y FINALIZAR piden la acción `gestionRutinas`, NO
//     `altaBajaSocios`. Asignar un entrenador no es un dato administrativo del
//     socio, es una decisión de entrenamiento — y así la tienen el Dueño, el
//     Recepcionista y el propio Entrenador, que es quien toma un cliente
//     nuevo. No hay escalación en dejárselo al entrenador: ya ve a todos los
//     socios en LECTURA, así que asignarse uno no le muestra nada nuevo.
//
// Gemelo de la sección ENTRENADOR A CARGO de `app/api_client.py` en Flet.

export interface AsignacionEntrenador {
  idAsignacion: number;
  idSocio: number;
  idEntrenador: number;
  entrenador: string;
  especialidad?: string;
  /** ISO (yyyy-mm-dd). */
  fechaInicio: string;
  /** undefined mientras sigue entrenándolo. */
  fechaFin?: string;
  estado: string;
  /** Derivado de `estado`, que es lo que mira la vista en todos lados. */
  activa: boolean;
}

interface AsignacionEntrenadorApi {
  id_asignacion: number;
  id_socio: number;
  id_entrenador: number;
  entrenador: string;
  especialidad: string | null;
  fecha_inicio: string;
  fecha_fin: string | null;
  estado: string;
}

function aAsignacion(a: AsignacionEntrenadorApi): AsignacionEntrenador {
  return {
    idAsignacion: a.id_asignacion,
    idSocio: a.id_socio,
    idEntrenador: a.id_entrenador,
    entrenador: a.entrenador,
    especialidad: a.especialidad ?? undefined,
    fechaInicio: a.fecha_inicio,
    fechaFin: a.fecha_fin ?? undefined,
    estado: a.estado,
    activa: a.estado === 'ACTIVA',
  };
}

/**
 * Los entrenadores de un socio, CON historial.
 *
 * Trae también las finalizadas y es deliberado: ese historial es el motivo por
 * el que esto es una tabla y no la columna que había antes. Con la columna,
 * reasignar borraba al anterior y nadie podía responder "¿quién lo entrenaba
 * en marzo?".
 */
export async function listarEntrenadoresDeSocio(
  idSocio: number,
): Promise<AsignacionEntrenador[]> {
  const datos = await pedir<AsignacionEntrenadorApi[]>(`/socios/${idSocio}/entrenadores`);
  return datos.map(aAsignacion);
}

/**
 * Le pone un entrenador a cargo.
 *
 * SE PERMITEN VARIOS A LA VEZ — es la diferencia deliberada con las rutinas y
 * las dietas, que admiten una sola activa. Lo que sí rechaza el backend (409)
 * es asignar dos veces al MISMO: eso no es "dos entrenadores", es la misma
 * relación duplicada, y después nadie sabría cuál de las dos filas finalizar.
 */
export async function asignarEntrenador(
  idSocio: number,
  idEntrenador: number,
): Promise<AsignacionEntrenador> {
  const datos = await pedir<AsignacionEntrenadorApi>(`/socios/${idSocio}/entrenadores`, {
    metodo: 'POST',
    cuerpo: { id_entrenador: idEntrenador },
  });
  return aAsignacion(datos);
}

/**
 * Termina la relación. NO borra la fila: queda con su fecha_fin y sigue
 * explicando quién entrenaba a quién en ese período.
 *
 * La ruta va por /socios/entrenadores/asignaciones/{id} y no bajo el id del
 * socio: el id de la asignación ya lo identifica, y pedir los dos permitiría
 * mandar una combinación inconsistente.
 */
export async function finalizarAsignacionEntrenador(
  idAsignacion: number,
): Promise<AsignacionEntrenador> {
  const datos = await pedir<AsignacionEntrenadorApi>(
    `/socios/entrenadores/asignaciones/${idAsignacion}/finalizar`,
    { metodo: 'POST' },
  );
  return aAsignacion(datos);
}
