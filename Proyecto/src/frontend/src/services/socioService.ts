// Portal del socio (docs/prompt_portal_socio.md).
//
// ⚠️ LA REGLA QUE MANDA EN ESTE ARCHIVO, y la razón de que exista separado
// de sociosService.ts:
//
//   Toda función de acá recibe `idSocio` y devuelve ÚNICAMENTE datos de ESE
//   socio. Nunca una lista de otros, nunca un total del gimnasio, nunca un
//   dato de otra persona.
//
// El nombre es a propósito casi igual al de sociosService (singular vs
// plural) porque son las dos caras de la misma tabla, y conviene que
// chirríe al leerlo:
//
//   sociosService.ts  -> lo que el STAFF ve de TODOS los socios.
//   socioService.ts   -> lo que UN socio ve de SÍ MISMO.
//
// Si alguna vez una función de este archivo necesita `.filter()` sobre una
// lista completa para después quedarse con varios resultados de personas
// distintas, está en el archivo equivocado.
//
// Esto es la mitad de la historia: la otra mitad es que el backend valide
// que el idSocio del token es el mismo que el de la request. Un `fetch`
// hecho a mano con otro id tiene que devolver 403, no datos. Acá el id sale
// de authStore, que cualquiera puede editar desde las devtools.

import type { Pago, Persona, RegistroSalud, Socio } from '../types';
import type { EstadoSocioValue, NivelRutinaValue, ObjetivoDietaValue } from '../config';
import { aFechaISO, diasEntre, parsearFecha } from '../utils/fechas';
import { ServiceError, delay } from './api';
import { registrarAuditoria } from './auditoriaService';
import { estadoDeSocio, membresiaVigente, nombrePlan } from './membresiaService';
import { nombrePorEmpleado } from './personalService';
import { esEmailValido, limpiar } from './validacion';
import {
  personas,
  socios,
  sedes,
  telefonos,
  siguienteId,
  asignacionesRutina,
  rutinas,
  rutinaEjercicios,
  ejercicios,
  entrenadores,
  registrosSalud,
  asignacionesDieta,
  dietas,
  comidas,
  nutricionistas,
  deudas,
  pagos,
} from './mockDb';

// --- Helpers internos ---

/**
 * Resuelve el par Socio+Persona de un id, o corta con 404.
 *
 * Todas las funciones públicas arrancan por acá en vez de buscar sueltas:
 * así ninguna puede olvidarse de verificar que el socio existe y devolver
 * `undefined` disfrazado de dato válido.
 */
function resolver(idSocio: number): { socio: Socio; persona: Persona } {
  const socio = socios.find((s) => s.id_socio === idSocio);
  if (!socio) {
    throw new ServiceError(404, 'No encontramos tu ficha de socio');
  }
  const persona = personas.find((p) => p.id_persona === socio.id_persona);
  if (!persona) {
    throw new ServiceError(404, 'No encontramos tu ficha de socio');
  }
  return { socio, persona };
}

function telefonoPrincipal(idPersona: number): string | undefined {
  const propios = telefonos.filter((t) => t.id_persona === idPersona);
  return (propios.find((t) => t.principal) ?? propios[0])?.numero;
}

// --- 1. Mi Perfil ---

export interface MiPerfil {
  idSocio: number;
  numeroSocio?: string;
  nombreCompleto: string;
  dni: string;
  fechaNacimiento?: string;
  /** Domicilio ya armado ("Av. Victorica 1450, Moreno"), o undefined si no cargó ninguno. */
  domicilio?: string;
  sede: string;
  fechaAlta: string;

  // Editables por el socio.
  email?: string;
  telefono?: string;
  emergenciaNombre?: string;
  emergenciaTelefono?: string;
  emergenciaParentesco?: string;

  // Solo lectura, para el encabezado.
  plan: string;
  estado: EstadoSocioValue;
  vencimiento?: string;
}

/** Une calle + número + localidad saltando lo que falte, sin dejar comas sueltas. */
function armarDomicilio(persona: Persona): string | undefined {
  const linea = [persona.calle, persona.numero_calle].filter(Boolean).join(' ').trim();
  const partes = [linea, persona.localidad].filter((p) => p && p !== '');
  return partes.length > 0 ? partes.join(', ') : undefined;
}

/**
 * Arma el perfil sin latencia simulada. Existe separado de getMiPerfil para
 * que actualizarMisDatosDeContacto pueda devolver el perfil ya actualizado
 * sin encadenar un segundo `delay()`: guardar tardaría el doble que cargar
 * y se nota.
 */
function armarPerfil(idSocio: number): MiPerfil {
  const { socio, persona } = resolver(idSocio);
  const membresia = membresiaVigente(idSocio);

  return {
    idSocio: socio.id_socio,
    numeroSocio: socio.numero_socio,
    nombreCompleto: `${persona.nombre} ${persona.apellido}`.trim(),
    dni: persona.dni,
    fechaNacimiento: persona.fecha_nacimiento,
    domicilio: armarDomicilio(persona),
    sede: sedes.find((s) => s.id_sede === socio.id_sede)?.nombre ?? 'Sin sede',
    fechaAlta: socio.fecha_alta,

    email: persona.email,
    telefono: telefonoPrincipal(persona.id_persona),
    emergenciaNombre: persona.emergencia_nombre,
    emergenciaTelefono: persona.emergencia_telefono,
    emergenciaParentesco: persona.emergencia_parentesco,

    plan: nombrePlan(idSocio),
    estado: estadoDeSocio(socio),
    vencimiento: membresia?.fecha_vencimiento,
  };
}

export async function getMiPerfil(idSocio: number): Promise<MiPerfil> {
  await delay();
  return armarPerfil(idSocio);
}

/**
 * Lo único que el socio puede modificar de su ficha.
 *
 * Lo que NO está en esta interfaz es tan importante como lo que está: no
 * hay dni, ni nombre, ni sede, ni plan, ni numero_socio, ni activo. No es
 * que el formulario no los muestre editables — es que no existe forma de
 * mandarlos. Un campo que no está en el input no se puede colar con un
 * fetch a mano, y ese es justamente el tipo de agujero que un formulario
 * "casi igual al de admin" deja abierto sin que se note.
 *
 * El plan queda afuera a propósito aunque el socio lo vea: cambiarlo es
 * facturar, y eso lo hace recepción.
 */
export interface MisDatosDeContacto {
  email?: string;
  telefono?: string;
  emergenciaNombre?: string;
  emergenciaTelefono?: string;
  emergenciaParentesco?: string;
}

export async function actualizarMisDatosDeContacto(
  idSocio: number,
  input: MisDatosDeContacto,
  idUsuarioActor?: number,
): Promise<MiPerfil> {
  await delay();
  const { persona } = resolver(idSocio);

  const email = limpiar(input.email).toLowerCase() || undefined;
  if (email && !esEmailValido(email)) {
    throw new ServiceError(400, 'El email no tiene un formato válido');
  }
  // Persona.email es unique en el esquema: hay que excluirse a uno mismo del
  // chequeo o guardar sin cambiar el mail daría "ya está en uso".
  if (email && personas.some((p) => p.id_persona !== persona.id_persona && p.email?.toLowerCase() === email)) {
    throw new ServiceError(409, 'Ese email ya está en uso');
  }

  const telefono = limpiar(input.telefono) || undefined;
  const emergenciaNombre = limpiar(input.emergenciaNombre) || undefined;
  const emergenciaTelefono = limpiar(input.emergenciaTelefono) || undefined;
  const emergenciaParentesco = limpiar(input.emergenciaParentesco) || undefined;

  // Un contacto de emergencia con teléfono pero sin nombre no sirve para
  // nada el día que haga falta usarlo, así que se exige el par completo.
  // Vacío del todo sí se acepta: es opcional en el esquema.
  if (emergenciaTelefono && !emergenciaNombre) {
    throw new ServiceError(400, 'Poné también el nombre de tu contacto de emergencia');
  }
  if (emergenciaNombre && !emergenciaTelefono) {
    throw new ServiceError(400, 'Poné también el teléfono de tu contacto de emergencia');
  }

  persona.email = email;
  persona.emergencia_nombre = emergenciaNombre;
  persona.emergencia_telefono = emergenciaTelefono;
  persona.emergencia_parentesco = emergenciaParentesco;

  // Mismo criterio que sociosService/personalService: el teléfono principal
  // es un solo campo del formulario, así que se reemplaza entero.
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

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Persona',
    id_entidad: persona.id_persona,
    accion: 'MODIFICACION',
    detalle: 'Datos de contacto actualizados por el socio',
  });

  return armarPerfil(idSocio);
}

// --- 2. Mi Rutina ---

export interface EjercicioDelDia {
  idRutinaEjercicio: number;
  nombre: string;
  grupoMuscular: string;
  series?: number;
  /** Texto libre: "10-12", "al fallo", "45 seg". Ver RutinaEjercicio. */
  repeticiones?: string;
  pesoSugerido?: number;
  descansoSegundos?: number;
  observaciones?: string;
}

export interface DiaDeRutina {
  dia: number;
  ejercicios: EjercicioDelDia[];
}

export interface MiRutina {
  idRutina: number;
  nombre: string;
  nivel?: NivelRutinaValue;
  objetivo?: string;
  diasPorSemana?: number;
  entrenador: string;
  fechaInicio: string;
  /** La rutina fue dada de baja pero la asignación sigue activa — ver abajo. */
  rutinaDeBaja: boolean;
  dias: DiaDeRutina[];
}

/**
 * La rutina que el socio tiene asignada HOY, o null si no tiene ninguna.
 *
 * Se busca por Asignacion_Rutina con estado ACTIVA y no por la rutina más
 * reciente: una asignación FINALIZADA o CANCELADA es justamente la que ya
 * no está vigente. Si hubiera más de una activa (no debería, pero el
 * esquema no lo impide), gana la de fecha_inicio más nueva.
 */
export async function getMiRutina(idSocio: number): Promise<MiRutina | null> {
  await delay();
  resolver(idSocio); // valida que el socio exista antes de devolver null

  const asignacion = asignacionesRutina
    .filter((a) => a.id_socio === idSocio && a.estado === 'ACTIVA')
    .sort((a, b) => b.fecha_inicio.localeCompare(a.fecha_inicio))[0];
  if (!asignacion) return null;

  const rutina = rutinas.find((r) => r.id_rutina === asignacion.id_rutina);
  if (!rutina) return null;

  // Los ejercicios se ordenan por (dia, orden), que es el índice que tiene
  // el esquema: `orden` es el que manda dentro del día, no la posición en
  // la tabla.
  const propios = rutinaEjercicios
    .filter((re) => re.id_rutina === rutina.id_rutina)
    .sort((a, b) => a.dia - b.dia || a.orden - b.orden);

  const dias: DiaDeRutina[] = [];
  for (const re of propios) {
    const ejercicio = ejercicios.find((e) => e.id_ejercicio === re.id_ejercicio);
    if (!ejercicio) continue;
    let grupo = dias.find((d) => d.dia === re.dia);
    if (!grupo) {
      grupo = { dia: re.dia, ejercicios: [] };
      dias.push(grupo);
    }
    grupo.ejercicios.push({
      idRutinaEjercicio: re.id_rutina_ejercicio,
      nombre: ejercicio.nombre,
      grupoMuscular: ejercicio.grupo_muscular,
      series: re.series,
      repeticiones: re.repeticiones,
      pesoSugerido: re.peso_sugerido,
      descansoSegundos: re.descanso_segundos,
      observaciones: re.observaciones,
    });
  }

  const entrenadorDeLaRutina = entrenadores.find(
    (e) => e.id_entrenador === rutina.id_entrenador,
  );

  return {
    idRutina: rutina.id_rutina,
    nombre: rutina.nombre,
    nivel: rutina.nivel as NivelRutinaValue | undefined,
    objetivo: rutina.objetivo,
    diasPorSemana: rutina.dias_por_semana,
    entrenador: entrenadorDeLaRutina
      ? nombrePorEmpleado(entrenadorDeLaRutina.id_empleado)
      : 'Sin asignar',
    fechaInicio: asignacion.fecha_inicio,
    // Puede pasar: el entrenador da de baja la rutina y las asignaciones
    // existentes NO se cancelan (decisión documentada en rutinasService).
    // El socio la sigue teniendo asignada, así que se le muestra igual —
    // pero con un aviso, porque es la clase de detalle que si se oculta
    // termina en "seguí entrenando tres meses un plan discontinuado".
    rutinaDeBaja: !rutina.activo,
    dias,
  };
}

// --- 3. Mi Progreso ---

export interface MedicionListada {
  idRegistroSalud: number;
  fecha: string;
  peso?: number;
  grasaCorporal?: number;
  masaMuscular?: number;
  observaciones?: string;
}

export interface MiProgreso {
  /** De la más vieja a la más nueva: así se lee el gráfico de izquierda a derecha. */
  mediciones: MedicionListada[];
  pesoActual?: number;
  /** Diferencia contra la PRIMERA medición. Negativo = bajó. */
  variacionPeso?: number;
  grasaActual?: number;
  altura?: number;
  /** True si ya cargó una medición hoy — el unique del esquema no deja otra. */
  yaCargoHoy: boolean;
}

/** Las mediciones del socio, ordenadas cronológicamente. */
function medicionesDe(idSocio: number): RegistroSalud[] {
  return registrosSalud
    .filter((r) => r.id_socio === idSocio)
    .sort((a, b) => a.fecha.localeCompare(b.fecha));
}

export async function getMiProgreso(idSocio: number): Promise<MiProgreso> {
  await delay();
  resolver(idSocio);
  return armarProgreso(idSocio);
}

function armarProgreso(idSocio: number): MiProgreso {
  const propias = medicionesDe(idSocio);
  const primera = propias[0];
  const ultima = propias[propias.length - 1];
  const hoy = aFechaISO(new Date());

  return {
    mediciones: propias.map((r) => ({
      idRegistroSalud: r.id_registro_salud,
      fecha: r.fecha,
      peso: r.peso,
      grasaCorporal: r.grasa_corporal,
      masaMuscular: r.masa_muscular,
      observaciones: r.observaciones,
    })),
    pesoActual: ultima?.peso,
    // Sólo tiene sentido si hay dos mediciones CON peso: con una sola no hay
    // contra qué comparar, y mostrar "0 kg" sugeriría que se estancó cuando
    // en realidad recién empieza.
    variacionPeso:
      propias.length > 1 && primera?.peso !== undefined && ultima?.peso !== undefined
        ? Number((ultima.peso - primera.peso).toFixed(1))
        : undefined,
    grasaActual: ultima?.grasa_corporal,
    // La altura no cambia: se toma la última cargada y sirve de default en
    // el formulario, para que el socio no la tenga que reescribir siempre.
    altura: [...propias].reverse().find((r) => r.altura !== undefined)?.altura,
    yaCargoHoy: propias.some((r) => r.fecha === hoy),
  };
}

export interface NuevaMedicion {
  peso: number;
  altura?: number;
  grasaCorporal?: number;
  masaMuscular?: number;
  observaciones?: string;
}

// Rangos de sanidad. No son reglas del negocio ni están en el esquema
// (numeric(5,2) acepta cualquier cosa): son topes para atajar el dedazo
// evidente —un 8 o un 800 en vez de 80— antes de que ensucie el historial y
// el gráfico quede ilegible por una sola fila absurda.
const PESO_MIN = 30;
const PESO_MAX = 300;
const ALTURA_MIN = 1.2;
const ALTURA_MAX = 2.5;
const PORCENTAJE_MAX = 99;

/**
 * Carga una medición del día de hoy.
 *
 * El unique (id_socio, fecha) del esquema es el que manda: **no** se
 * sobrescribe la fila del día en silencio. Si ya cargó hoy, se rechaza y se
 * explica por qué. Pisar el valor anterior sería exactamente la "anomalía
 * de borrado" contra la que advierte el comentario de la tabla, y además le
 * borraría al socio un dato que él mismo cargó sin avisarle.
 */
export async function guardarMedicion(
  idSocio: number,
  input: NuevaMedicion,
  idUsuarioActor?: number,
): Promise<MiProgreso> {
  await delay();
  resolver(idSocio);

  const hoy = aFechaISO(new Date());
  if (registrosSalud.some((r) => r.id_socio === idSocio && r.fecha === hoy)) {
    throw new ServiceError(
      409,
      'Ya cargaste una medición hoy. Podés cargar la próxima mañana.',
    );
  }

  if (!Number.isFinite(input.peso) || input.peso < PESO_MIN || input.peso > PESO_MAX) {
    throw new ServiceError(400, `El peso tiene que estar entre ${PESO_MIN} y ${PESO_MAX} kg`);
  }
  if (
    input.altura !== undefined &&
    (!Number.isFinite(input.altura) || input.altura < ALTURA_MIN || input.altura > ALTURA_MAX)
  ) {
    throw new ServiceError(400, `La altura tiene que estar entre ${ALTURA_MIN} y ${ALTURA_MAX} m`);
  }
  for (const [valor, etiqueta] of [
    [input.grasaCorporal, 'grasa corporal'],
    [input.masaMuscular, 'masa muscular'],
  ] as const) {
    if (valor !== undefined && (!Number.isFinite(valor) || valor <= 0 || valor > PORCENTAJE_MAX)) {
      throw new ServiceError(400, `El valor de ${etiqueta} no es válido`);
    }
  }

  registrosSalud.push({
    id_registro_salud: siguienteId.registroSalud(),
    id_socio: idSocio,
    fecha: hoy,
    peso: input.peso,
    altura: input.altura,
    grasa_corporal: input.grasaCorporal,
    masa_muscular: input.masaMuscular,
    observaciones: limpiar(input.observaciones) || undefined,
    // La cargó el socio desde su portal, no el staff desde el mostrador.
    id_registrado_por: idUsuarioActor,
  });

  registrarAuditoria({
    id_usuario: idUsuarioActor,
    entidad: 'Registro_Salud',
    id_entidad: idSocio,
    accion: 'ALTA',
    detalle: 'Medición cargada por el socio',
  });

  return armarProgreso(idSocio);
}

// --- 4. Mi Dieta ---

export interface ComidaDelDia {
  idComida: number;
  momento?: string;
  descripcion: string;
  calorias?: number;
}

export interface DiaDeDieta {
  dia: number;
  comidas: ComidaDelDia[];
  /** Suma de las calorías del día, sólo si TODAS las comidas las tienen. */
  caloriasDelDia?: number;
}

export interface MiDieta {
  idDieta: number;
  nombre: string;
  objetivo?: ObjetivoDietaValue;
  caloriasDiarias?: number;
  descripcion?: string;
  nutricionista: string;
  fechaInicio: string;
  observaciones?: string;
  dietaDeBaja: boolean;
  dias: DiaDeDieta[];
}

/**
 * El plan nutricional vigente del socio, o null si no tiene.
 *
 * Mismo criterio que getMiRutina: se busca la Asignacion_Dieta ACTIVA, no
 * la dieta más reciente.
 */
export async function getMiDieta(idSocio: number): Promise<MiDieta | null> {
  await delay();
  resolver(idSocio);

  const asignacion = asignacionesDieta
    .filter((a) => a.id_socio === idSocio && a.estado === 'ACTIVA')
    .sort((a, b) => b.fecha_inicio.localeCompare(a.fecha_inicio))[0];
  if (!asignacion) return null;

  const dieta = dietas.find((d) => d.id_dieta === asignacion.id_dieta);
  if (!dieta) return null;

  // Comida.dia es nullable: las que no lo tienen caen al grupo 0, que la
  // vista rotula "Sin día asignado" (mismo criterio que PlanDetailModal).
  // No se descartan: una comida sin día sigue siendo parte del plan.
  const dias: DiaDeDieta[] = [];
  for (const comida of comidas.filter((c) => c.id_dieta === dieta.id_dieta)) {
    const numeroDia = comida.dia ?? 0;
    let grupo = dias.find((d) => d.dia === numeroDia);
    if (!grupo) {
      grupo = { dia: numeroDia, comidas: [] };
      dias.push(grupo);
    }
    grupo.comidas.push({
      idComida: comida.id_comida,
      momento: comida.momento,
      descripcion: comida.descripcion,
      calorias: comida.calorias,
    });
  }
  dias.sort((a, b) => a.dia - b.dia);

  for (const dia of dias) {
    const conCalorias = dia.comidas.filter((c) => c.calorias !== undefined);
    // Sólo se suma si TODAS las comidas del día tienen calorías cargadas.
    // Sumar un subconjunto daría un total más bajo que el real y el socio lo
    // leería como "me quedan calorías disponibles" — peor que no mostrarlo.
    dia.caloriasDelDia =
      conCalorias.length > 0 && conCalorias.length === dia.comidas.length
        ? conCalorias.reduce((total, c) => total + (c.calorias ?? 0), 0)
        : undefined;
  }

  const nutricionistaDelPlan = nutricionistas.find(
    (n) => n.id_nutricionista === dieta.id_nutricionista,
  );

  return {
    idDieta: dieta.id_dieta,
    nombre: dieta.nombre,
    objetivo: dieta.objetivo as ObjetivoDietaValue | undefined,
    caloriasDiarias: dieta.calorias_diarias,
    descripcion: dieta.descripcion,
    nutricionista: nutricionistaDelPlan
      ? nombrePorEmpleado(nutricionistaDelPlan.id_empleado)
      : 'Sin asignar',
    fechaInicio: asignacion.fecha_inicio,
    // Asignacion_Dieta tiene observaciones propias (Asignacion_Rutina no):
    // son las indicaciones que el nutricionista le dejó a ESTE socio sobre
    // este plan, distintas de la descripción general de la dieta.
    observaciones: asignacion.observaciones,
    dietaDeBaja: !dieta.activo,
    dias,
  };
}

// --- 5. Mi Cuota ---

export interface DeudaListada {
  idDeuda: number;
  monto: number;
  fechaGeneracion: string;
  fechaVencimiento?: string;
  observaciones?: string;
  /** Días de atraso respecto de hoy. 0 o negativo = todavía no venció. */
  diasDeAtraso: number;
}

export interface PagoListado {
  idPago: number;
  fecha: string;
  monto: number;
  metodo: string;
  estado: Pago['estado'];
  numeroComprobante?: string;
}

export interface MiCuota {
  /**
   * False = no tiene ninguna membresía. Hace falta como campo propio porque
   * `vencimiento` undefined ya no alcanza para distinguir "sin membresía" de
   * "con membresía que no vence nunca" (extensión de actividades, REGLA 1
   * de actividadService) — las dos dejan `vencimiento` en undefined.
   */
  tieneMembresia: boolean;
  plan: string;
  estado: EstadoSocioValue;
  precioPactado?: number;
  fechaInicio?: string;
  /** undefined = sin membresía O con membresía sin vencimiento — usar tieneMembresia para distinguir. */
  vencimiento?: string;
  /** Días hasta el vencimiento. Negativo = ya venció. undefined si no tiene membresía o si no vence nunca. */
  diasParaVencer?: number;
  /** Sólo las PENDIENTE: las PAGADA y CONDONADA ya no se le reclaman. */
  deudas: DeudaListada[];
  totalAdeudado: number;
  pagos: PagoListado[];
}

/**
 * Cómo se muestra cada método de pago. El esquema los guarda en mayúsculas
 * y con guión bajo (BILLETERA_VIRTUAL) porque es un enum de Postgres; eso
 * no se le muestra a nadie.
 */
const ETIQUETA_METODO: Record<Pago['metodo'], string> = {
  EFECTIVO: 'Efectivo',
  DEBITO: 'Débito',
  CREDITO: 'Crédito',
  TRANSFERENCIA: 'Transferencia',
  BILLETERA_VIRTUAL: 'Billetera virtual',
};

/**
 * Estado de cuenta del socio: su membresía, lo que debe y lo que pagó.
 *
 * NO expone ninguna acción de cobro. Cobrar es de recepción (DFD 2.3: el
 * socio consulta, el dueño modifica) — por eso acá no hay un
 * `pagarDeuda()`, ni siquiera comentado. Si mañana el gimnasio suma pagos
 * online, eso es una pasarela y una spec propia, no un botón en esta
 * pantalla.
 */
export async function getMiCuota(idSocio: number): Promise<MiCuota> {
  await delay();
  const { socio } = resolver(idSocio);

  const membresia = membresiaVigente(idSocio);
  const hoy = new Date();

  const propias = deudas
    .filter((d) => d.id_socio === idSocio && d.estado === 'PENDIENTE')
    .sort((a, b) => a.fecha_generacion.localeCompare(b.fecha_generacion))
    .map((d) => ({
      idDeuda: d.id_deuda,
      monto: d.monto,
      fechaGeneracion: d.fecha_generacion,
      fechaVencimiento: d.fecha_vencimiento,
      observaciones: d.observaciones,
      diasDeAtraso: d.fecha_vencimiento
        ? diasEntre(parsearFecha(d.fecha_vencimiento), hoy)
        : 0,
    }));

  return {
    tieneMembresia: membresia !== undefined,
    plan: nombrePlan(idSocio),
    estado: estadoDeSocio(socio, hoy),
    precioPactado: membresia?.precio_pactado,
    fechaInicio: membresia?.fecha_inicio,
    vencimiento: membresia?.fecha_vencimiento,
    // Ojo: es membresia?.fecha_vencimiento, NO sólo membresia — una
    // membresía activa sin vencimiento (cubre siempre) SÍ existe pero no
    // tiene "días para vencer" que calcular.
    diasParaVencer: membresia?.fecha_vencimiento
      ? diasEntre(hoy, parsearFecha(membresia.fecha_vencimiento))
      : undefined,
    deudas: propias,
    totalAdeudado: propias.reduce((total, d) => total + d.monto, 0),
    // Todos sus pagos, del más nuevo al más viejo. Se incluyen los
    // PENDIENTE y CANCELADO además de los CONFIRMADO: si un pago del socio
    // quedó pendiente o se anuló, esconderlo lo dejaría preguntándose dónde
    // fue a parar su plata. El estado va en la tabla.
    pagos: pagos
      .filter((p) => p.id_socio === idSocio)
      .sort((a, b) => b.fecha_pago.localeCompare(a.fecha_pago))
      .map((p) => ({
        idPago: p.id_pago,
        fecha: p.fecha_pago,
        monto: p.monto,
        metodo: ETIQUETA_METODO[p.metodo] ?? p.metodo,
        estado: p.estado,
        numeroComprobante: p.numero_comprobante,
      })),
  };
}
