// Portal del socio, conectado a la API real (routers/portal.py).
//
// NINGUNA FUNCIÓN DE ACÁ RECIBE UN idSocio
// Y ese es el cambio más importante del archivo. Antes todas lo tomaban como
// parámetro; ahora el backend lo saca del token, firmado en el login.
//
//     antes:  getMiRutina(idSocio)   ← el número lo elegía el cliente
//     ahora:  getMiRutina()          ← solo puede ser la propia
//
// Con el id como parámetro, alcanzaba con que UNA pantalla se olvidara de
// pasar el correcto —o con que alguien cambiara un número en las devtools—
// para que un socio viera la ficha médica, la dieta o el estado de cuenta de
// otro. Sin parámetro, ese olvido no es posible.
//
// Es lo que ya advertía el comentario de LoginResultado.idSocio: "si cada
// pantalla hiciera la traversal persona -> socio por su cuenta, alcanzaría con
// que una sola se olvidara de filtrar".

import type { EstadoSocioValue } from '../config';
import { pedir } from './api';
import type {
  ActividadListada,
  InscripcionListada,
  PlanActividadListado,
  TurnoDisponible,
} from './actividadService';

// =========================================================================
// MI PERFIL
// =========================================================================

export interface MiPerfil {
  idSocio: number;
  numeroSocio?: string;
  nombreCompleto: string;
  dni: string;
  fechaNacimiento?: string;
  /** Ya armado ("Av. Victorica 1450, Moreno"), o undefined si no cargó ninguno. */
  domicilio?: string;
  sede: string;
  fechaAlta: string;
  objetivo?: string;

  // Solo lectura, para el encabezado.
  plan: string;
  estado: EstadoSocioValue;
  vencimiento?: string;

  // Editables por el socio.
  email?: string;
  telefono?: string;
  emergenciaNombre?: string;
  emergenciaTelefono?: string;
  emergenciaParentesco?: string;
}

interface PerfilApi {
  id_socio: number;
  numero_socio: string | null;
  dni: string;
  nombre: string;
  apellido: string;
  email: string | null;
  telefono: string | null;
  fecha_nacimiento: string | null;
  fecha_alta: string;
  objetivo: string | null;
  sede: string | null;
  emergencia_nombre: string | null;
  emergencia_telefono: string | null;
  emergencia_parentesco: string | null;
  domicilio: string | null;
  plan: string;
  estado: string;
  vencimiento: string | null;
}

function aMiPerfil(p: PerfilApi): MiPerfil {
  return {
    idSocio: p.id_socio,
    numeroSocio: p.numero_socio ?? undefined,
    nombreCompleto: `${p.nombre} ${p.apellido}`.trim(),
    dni: p.dni,
    fechaNacimiento: p.fecha_nacimiento ?? undefined,
    domicilio: p.domicilio ?? undefined,
    sede: p.sede ?? 'Sin sede',
    plan: p.plan,
    estado: p.estado as EstadoSocioValue,
    vencimiento: p.vencimiento ?? undefined,
    fechaAlta: p.fecha_alta,
    objetivo: p.objetivo ?? undefined,
    email: p.email ?? undefined,
    telefono: p.telefono ?? undefined,
    emergenciaNombre: p.emergencia_nombre ?? undefined,
    emergenciaTelefono: p.emergencia_telefono ?? undefined,
    emergenciaParentesco: p.emergencia_parentesco ?? undefined,
  };
}

export async function getMiPerfil(): Promise<MiPerfil> {
  return aMiPerfil(await pedir<PerfilApi>('/portal/mi-perfil'));
}

export interface MisDatosDeContacto {
  email?: string;
  telefono?: string;
  emergenciaNombre?: string;
  emergenciaTelefono?: string;
  emergenciaParentesco?: string;
}

/**
 * El socio edita SU contacto. Nada más.
 *
 * No están el DNI, el nombre ni la sede: eso lo administra el gimnasio, y
 * dejar que el socio los cambie permitiría, por ejemplo, editarse el DNI para
 * figurar como otra persona. El objetivo tampoco: lo acuerda con su
 * entrenador.
 */
export async function actualizarMisDatosDeContacto(
  datos: MisDatosDeContacto,
): Promise<MiPerfil> {
  const p = await pedir<PerfilApi>('/portal/mi-perfil', {
    metodo: 'PUT',
    cuerpo: {
      email: datos.email?.trim() || null,
      telefono: datos.telefono?.trim() ?? null,
      emergencia_nombre: datos.emergenciaNombre?.trim() || null,
      emergencia_telefono: datos.emergenciaTelefono?.trim() || null,
      emergencia_parentesco: datos.emergenciaParentesco?.trim() || null,
    },
  });
  return aMiPerfil(p);
}

// =========================================================================
// MI RUTINA
// =========================================================================

export interface EjercicioDelDia {
  idRutinaEjercicio: number;
  /** Id del ejercicio en el CATÁLOGO (Ejercicio), no el de la fila de la
   *  plantilla. Es el que necesita Registro_Ejercicio al anotar una serie
   *  hecha: el contador con cámara lo manda al backend. */
  idEjercicio: number;
  nombre: string;
  grupoMuscular: string;
  series?: number;
  /** Texto libre: "10-12", "al fallo", "45 seg". */
  repeticiones?: string;
  pesoSugerido?: number;
  descansoSegundos?: number;
  observaciones?: string;
  /** Ruta del video tutorial ya descargado en el servidor. Sin él, no hay
   *  botón "Ver técnica" (el entrenador no cargó link o todavía se está bajando). */
  video?: string;
}

export interface DiaDeRutina {
  dia: number;
  ejercicios: EjercicioDelDia[];
}

export interface MiRutina {
  idRutina: number;
  nombre: string;
  objetivo?: string;
  diasPorSemana?: number;
  entrenador: string;
  /** True si es la rutina PROPIA del socio (la puede editar/eliminar él). */
  esPropia: boolean;
  /** La rutina fue dada de baja pero la asignación sigue activa. */
  rutinaDeBaja: boolean;
  /** Desde cuándo la tiene asignada. Viene de la asignación, no de la plantilla. */
  fechaInicio: string;
  dias: DiaDeRutina[];
}

interface RutinaApi {
  id_rutina: number;
  nombre: string;
  objetivo: string | null;
  dias_por_semana: number | null;
  entrenador: string;
  es_propia?: boolean;
  rutina_de_baja: boolean;
  fecha_inicio: string;
  ejercicios: {
    id_rutina_ejercicio: number;
    id_ejercicio: number;
    nombre_ejercicio: string;
    grupo_muscular: string;
    dia: number;
    orden: number;
    series: number | null;
    repeticiones: string | null;
    peso_sugerido: number | null;
    descanso_segundos: number | null;
    observaciones: string | null;
    video_local: string | null;
  }[];
}

/**
 * Agrupa la lista plana de ejercicios en días.
 *
 * El backend los manda ya ordenados por día y orden, así que alcanza con
 * recorrerlos una vez: cada vez que cambia el día, arranca un grupo nuevo.
 * Ordenarlos acá sería repetir un trabajo ya hecho.
 */
function agruparPorDia(ejercicios: RutinaApi['ejercicios']): DiaDeRutina[] {
  const dias: DiaDeRutina[] = [];
  for (const e of ejercicios) {
    let grupo = dias.find((d) => d.dia === e.dia);
    if (!grupo) {
      grupo = { dia: e.dia, ejercicios: [] };
      dias.push(grupo);
    }
    grupo.ejercicios.push({
      idRutinaEjercicio: e.id_rutina_ejercicio,
      idEjercicio: e.id_ejercicio,
      nombre: e.nombre_ejercicio,
      grupoMuscular: e.grupo_muscular,
      series: e.series ?? undefined,
      repeticiones: e.repeticiones ?? undefined,
      pesoSugerido: e.peso_sugerido ?? undefined,
      descansoSegundos: e.descanso_segundos ?? undefined,
      observaciones: e.observaciones ?? undefined,
      video: e.video_local ?? undefined,
    });
  }
  return dias;
}

/**
 * La rutina asignada HOY, o null si no tiene ninguna.
 *
 * Null y no un error: un socio recién anotado sin rutina es un estado normal.
 * La vista muestra "todavía no tenés rutina asignada" en vez de una pantalla
 * de error.
 */
function mapearMiRutina(r: RutinaApi): MiRutina {
  return {
    idRutina: r.id_rutina,
    nombre: r.nombre,
    objetivo: r.objetivo ?? undefined,
    diasPorSemana: r.dias_por_semana ?? undefined,
    entrenador: r.entrenador,
    esPropia: r.es_propia ?? false,
    // La rutina se dio de baja del catálogo pero la asignación sigue activa:
    // el socio la termina. La vista lo avisa para que sepa que no se la van a
    // renovar. (En una rutina propia esto no pasa: la maneja el mismo socio.)
    rutinaDeBaja: r.rutina_de_baja,
    fechaInicio: r.fecha_inicio,
    dias: agruparPorDia(r.ejercicios),
  };
}

export async function getMiRutina(): Promise<MiRutina | null> {
  const r = await pedir<RutinaApi | null>('/portal/mi-rutina');
  if (!r) return null;
  return mapearMiRutina(r);
}

// =========================================================================
// MI RUTINA PROPIA — el socio se la arma solo (id_entrenador NULL)
// =========================================================================
// Es el mismo mecanismo que una rutina de entrenador, pero suya y de nadie más:
// invisible para el personal, no asignable a otro. El backend la crea a NULL y
// se la autoasigna al id del token. Ver routers/portal.py.

/** Un ejercicio del catálogo, para elegir al armar la rutina propia. */
export interface EjercicioCatalogo {
  idEjercicio: number;
  nombre: string;
  grupoMuscular: string;
  descripcion?: string;
  requiereMaquina: boolean;
  /** Ruta del video tutorial ya descargado en el servidor, si hay. */
  video?: string;
}

interface EjercicioCatalogoApi {
  id_ejercicio: number;
  nombre: string;
  grupo_muscular: string;
  descripcion: string | null;
  url_video: string | null;
  video_local: string | null;
  requiere_maquina: boolean;
}

/** El catálogo de ejercicios del que el socio elige (agrupado por músculo en la UI). */
export async function listarEjerciciosCatalogo(): Promise<EjercicioCatalogo[]> {
  const r = await pedir<EjercicioCatalogoApi[]>('/portal/mi-rutina/ejercicios');
  return r.map((e) => ({
    idEjercicio: e.id_ejercicio,
    nombre: e.nombre,
    grupoMuscular: e.grupo_muscular,
    descripcion: e.descripcion ?? undefined,
    requiereMaquina: e.requiere_maquina,
    video: e.video_local ?? undefined,
  }));
}

/** Un ejercicio tal como el socio lo agrega a SU rutina (con sus series/reps). */
export interface EjercicioParaRutina {
  idEjercicio: number;
  dia: number;
  orden: number;
  series?: number;
  repeticiones?: string;
  pesoSugerido?: number;
  descansoSegundos?: number;
  observaciones?: string;
}

export interface MiRutinaPropiaNueva {
  nombre: string;
  objetivo?: string;
  diasPorSemana?: number;
  ejercicios: EjercicioParaRutina[];
}

/**
 * Crea (o rehace) la rutina propia del socio y la deja activa.
 *
 * Si ya tenía una del ENTRENADOR activa, el backend rechaza con 409 (la del
 * profe manda). Si tenía una propia anterior, la reemplaza. El socio destino
 * NO se manda: sale del token.
 */
export async function crearMiRutinaPropia(datos: MiRutinaPropiaNueva): Promise<MiRutina> {
  const r = await pedir<RutinaApi>('/portal/mi-rutina/propia', {
    metodo: 'POST',
    cuerpo: {
      nombre: datos.nombre.trim(),
      objetivo: datos.objetivo?.trim() || null,
      dias_por_semana: datos.diasPorSemana ?? null,
      ejercicios: datos.ejercicios.map((e) => ({
        id_ejercicio: e.idEjercicio,
        dia: e.dia,
        orden: e.orden,
        series: e.series ?? null,
        repeticiones: e.repeticiones?.trim() || null,
        peso_sugerido: e.pesoSugerido ?? null,
        descanso_segundos: e.descansoSegundos ?? null,
        observaciones: e.observaciones?.trim() || null,
      })),
    },
  });
  return mapearMiRutina(r);
}

/** Retira la rutina propia activa (queda como historial; no se borra). */
export async function eliminarMiRutinaPropia(): Promise<void> {
  await pedir('/portal/mi-rutina/propia', { metodo: 'DELETE' });
}

// Progreso de fuerza: lo que el socio levantó, para graficar la evolución.
export interface RegistroEjercicioListado {
  idRegistroEjercicio: number;
  idEjercicio: number;
  nombreEjercicio: string;
  fecha: string;
  pesoHecho: number;
  seriesHechas?: number;
  repeticionesHechas?: string;
}

interface RegistroEjercicioListadoApi {
  id_registro_ejercicio: number;
  id_ejercicio: number;
  nombre_ejercicio: string;
  fecha: string;
  peso_hecho: number;
  series_hechas: number | null;
  repeticiones_hechas: string | null;
}

/** Los registros de ejercicio del socio (últimos `dias` días, viejo→nuevo). */
export async function listarMisRegistrosEjercicio(dias = 120): Promise<RegistroEjercicioListado[]> {
  const r = await pedir<RegistroEjercicioListadoApi[]>(`/portal/mi-rutina/registro-ejercicio?dias=${dias}`);
  return r.map((x) => ({
    idRegistroEjercicio: x.id_registro_ejercicio,
    idEjercicio: x.id_ejercicio,
    nombreEjercicio: x.nombre_ejercicio,
    fecha: x.fecha,
    pesoHecho: x.peso_hecho,
    seriesHechas: x.series_hechas ?? undefined,
    repeticionesHechas: x.repeticiones_hechas ?? undefined,
  }));
}

// =========================================================================
// MI DIETA
// =========================================================================

export interface ComidaDelDia {
  idComida: number;
  momento?: string;
  descripcion: string;
  calorias?: number;
}

export interface DiaDeDieta {
  dia: number;
  comidas: ComidaDelDia[];
  /** Suma de las calorías del día. undefined si ninguna comida las tiene. */
  caloriasDelDia?: number;
}

export interface MiDieta {
  idDieta: number;
  nombre: string;
  objetivo?: string;
  caloriasDiarias?: number;
  descripcion?: string;
  nutricionista: string;
  /** True si es la dieta PROPIA del socio (la puede editar/eliminar él). */
  esPropia: boolean;
  dietaDeBaja: boolean;
  /** Desde cuándo la tiene asignada. Viene de la asignación, no de la plantilla. */
  fechaInicio: string;
  /** Nota que le dejó el nutricionista al asignársela. */
  observaciones?: string;
  dias: DiaDeDieta[];
}

interface DietaApi {
  id_dieta: number;
  nombre: string;
  objetivo: string | null;
  calorias_diarias: number | null;
  descripcion: string | null;
  nutricionista: string;
  es_propia?: boolean;
  dieta_de_baja: boolean;
  fecha_inicio: string;
  observaciones: string | null;
  dias: {
    dia: number;
    calorias_del_dia: number | null;
    comidas: {
      id_comida: number;
      momento: string | null;
      descripcion: string;
      calorias: number | null;
    }[];
  }[];
}

function mapearMiDieta(d: DietaApi): MiDieta {
  // Ya vienen agrupadas por día y en el orden del día (Desayuno → Almuerzo →
  // Cena), con las calorías sumadas. Eso lo hace el backend: es la misma
  // cuenta para todos y ordenar alfabéticamente pondría Almuerzo primero.
  return {
    idDieta: d.id_dieta,
    nombre: d.nombre,
    objetivo: d.objetivo ?? undefined,
    caloriasDiarias: d.calorias_diarias ?? undefined,
    descripcion: d.descripcion ?? undefined,
    nutricionista: d.nutricionista,
    esPropia: d.es_propia ?? false,
    dietaDeBaja: d.dieta_de_baja,
    fechaInicio: d.fecha_inicio,
    observaciones: d.observaciones ?? undefined,
    dias: d.dias.map((g) => ({
      dia: g.dia,
      caloriasDelDia: g.calorias_del_dia ?? undefined,
      comidas: g.comidas.map((c) => ({
        idComida: c.id_comida,
        momento: c.momento ?? undefined,
        descripcion: c.descripcion,
        calorias: c.calorias ?? undefined,
      })),
    })),
  };
}

export async function getMiDieta(): Promise<MiDieta | null> {
  const d = await pedir<DietaApi | null>('/portal/mi-dieta');
  if (!d) return null;
  return mapearMiDieta(d);
}

// =========================================================================
// MI DIETA PROPIA — el socio se la arma solo (id_nutricionista NULL)
// =========================================================================
// Espejo de la rutina propia, pero con comidas de TEXTO LIBRE (el catálogo del
// gimnasio puede estar vacío). Invisible para el personal; se autoasigna.

/** Una comida del plan propio, en texto libre. */
export interface ComidaPropia {
  momento?: string;       // Desayuno, Almuerzo, Merienda, Cena…
  descripcion: string;    // "avena con banana y huevos"
  dia?: number;
}

export interface MiDietaPropiaNueva {
  nombre: string;
  objetivo?: string;
  caloriasDiarias?: number;
  comidas: ComidaPropia[];
}

/**
 * Crea (o rehace) la dieta propia del socio y la deja activa. Si ya tenía una
 * del NUTRICIONISTA activa, el backend rechaza con 409. El socio destino no se
 * manda: sale del token.
 */
export async function crearMiDietaPropia(datos: MiDietaPropiaNueva): Promise<MiDieta> {
  const d = await pedir<DietaApi>('/portal/mi-dieta/propia', {
    metodo: 'POST',
    cuerpo: {
      nombre: datos.nombre.trim(),
      objetivo: datos.objetivo?.trim() || null,
      calorias_diarias: datos.caloriasDiarias ?? null,
      comidas: datos.comidas.map((c) => ({
        momento: c.momento?.trim() || null,
        descripcion: c.descripcion.trim(),
        dia: c.dia ?? null,
      })),
    },
  });
  return mapearMiDieta(d);
}

/** Retira la dieta propia activa (queda como historial; no se borra). */
export async function eliminarMiDietaPropia(): Promise<void> {
  await pedir('/portal/mi-dieta/propia', { metodo: 'DELETE' });
}

// =========================================================================
// MIS COMIDAS — lo que el socio comió (Registro_Comida)
// =========================================================================

export interface ComidaRegistrada {
  idRegistroComida: number;
  fecha: string;
  momento?: string;
  comidaIngerida: string;
  calorias?: number;
  proteinas?: number;
  carbohidratos?: number;
  grasas?: number;
}

export interface RegistroComidaNuevo {
  comidaIngerida: string;
  momento?: string;
  calorias?: number;
  proteinas?: number;
  carbohidratos?: number;
  grasas?: number;
}

interface ComidaRegistradaApi {
  id_registro_comida: number;
  fecha: string;
  momento: string | null;
  comida_ingerida: string;
  calorias_estimadas: number | null;
  proteinas_g: number | null;
  carbohidratos_g: number | null;
  grasas_g: number | null;
}

function mapearComidaRegistrada(r: ComidaRegistradaApi): ComidaRegistrada {
  return {
    idRegistroComida: r.id_registro_comida,
    fecha: r.fecha,
    momento: r.momento ?? undefined,
    comidaIngerida: r.comida_ingerida,
    calorias: r.calorias_estimadas ?? undefined,
    proteinas: r.proteinas_g ?? undefined,
    carbohidratos: r.carbohidratos_g ?? undefined,
    grasas: r.grasas_g ?? undefined,
  };
}

/** Lo que el socio registró que comió en los últimos `dias` días (nuevo primero). */
export async function listarMisComidas(dias = 7): Promise<ComidaRegistrada[]> {
  const r = await pedir<ComidaRegistradaApi[]>(`/portal/mi-dieta/comidas?dias=${dias}`);
  return r.map(mapearComidaRegistrada);
}

/** Registra una comida. El texto es obligatorio; los macros, opcionales. */
export async function registrarComida(datos: RegistroComidaNuevo): Promise<ComidaRegistrada> {
  const r = await pedir<ComidaRegistradaApi>('/portal/mi-dieta/comidas', {
    metodo: 'POST',
    cuerpo: {
      comida_ingerida: datos.comidaIngerida.trim(),
      momento: datos.momento?.trim() || null,
      calorias_estimadas: datos.calorias ?? null,
      proteinas_g: datos.proteinas ?? null,
      carbohidratos_g: datos.carbohidratos ?? null,
      grasas_g: datos.grasas ?? null,
    },
  });
  return mapearComidaRegistrada(r);
}

// =========================================================================
// MI PROGRESO
// =========================================================================

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
  /** True si ya cargó una medición hoy — es una por día. */
  yaCargoHoy: boolean;
}

interface ProgresoApi {
  mediciones: {
    id_registro_salud: number;
    fecha: string;
    peso: number | null;
    grasa_corporal: number | null;
    masa_muscular: number | null;
    observaciones: string | null;
  }[];
  peso_actual: number | null;
  variacion_peso: number | null;
  grasa_actual: number | null;
  altura: number | null;
  ya_cargo_hoy: boolean;
}

export async function getMiProgreso(): Promise<MiProgreso> {
  const p = await pedir<ProgresoApi>('/portal/mi-progreso');
  return {
    mediciones: p.mediciones.map((m) => ({
      idRegistroSalud: m.id_registro_salud,
      fecha: m.fecha,
      peso: m.peso ?? undefined,
      grasaCorporal: m.grasa_corporal ?? undefined,
      masaMuscular: m.masa_muscular ?? undefined,
      observaciones: m.observaciones ?? undefined,
    })),
    pesoActual: p.peso_actual ?? undefined,
    variacionPeso: p.variacion_peso ?? undefined,
    grasaActual: p.grasa_actual ?? undefined,
    altura: p.altura ?? undefined,
    yaCargoHoy: p.ya_cargo_hoy,
  };
}

export interface NuevaMedicion {
  peso: number;
  altura?: number;
  grasaCorporal?: number;
  masaMuscular?: number;
  observaciones?: string;
}

/**
 * Carga la medición de hoy.
 *
 * Es UNA por día y la del día NO se pisa en silencio: si ya cargó, el backend
 * rechaza con 409 y lo explica. Sobrescribir le borraría al socio un dato que
 * él mismo cargó, sin avisarle.
 *
 * Los rangos (peso 30–300, altura 1.2–2.5) los valida el servidor. No son
 * reglas del negocio: son topes para atajar el dedazo evidente —un 8 o un 800
 * en vez de 80— antes de que deje el gráfico ilegible por una fila absurda.
 */
export async function guardarMedicion(datos: NuevaMedicion): Promise<void> {
  await pedir('/portal/mi-progreso/mediciones', {
    metodo: 'POST',
    cuerpo: {
      peso: datos.peso,
      altura: datos.altura ?? null,
      grasa_corporal: datos.grasaCorporal ?? null,
      masa_muscular: datos.masaMuscular ?? null,
      observaciones: datos.observaciones?.trim() || null,
    },
  });
}

/** Una serie que el socio hizo, contada por la cámara del circuito. */
export interface RegistroEjercicioNuevo {
  idEjercicio: number;
  /** Reps contadas en ESTA serie. */
  repeticiones: number;
  /** kg. La cámara no lo sabe: lo carga el socio al terminar. 0 si no lo cargó. */
  peso: number;
  observaciones?: string;
}

/**
 * Anota una serie hecha en Registro_Ejercicio.
 *
 * El grano de esa tabla es (socio, ejercicio, fecha): el backend hace UPSERT,
 * así que varias series del mismo ejercicio en el día se acumulan en una fila.
 * Por eso NO hay que preocuparse acá por deduplicar: cada llamada suma una
 * serie real.
 *
 * La reintenta la cola offline (utils/colaRegistros): esta función sólo hace
 * el pedido y deja que el error (de red o del server) suba.
 */
export async function guardarRegistroEjercicio(datos: RegistroEjercicioNuevo): Promise<void> {
  await pedir('/portal/mi-rutina/registro-ejercicio', {
    metodo: 'POST',
    cuerpo: {
      id_ejercicio: datos.idEjercicio,
      repeticiones: datos.repeticiones,
      peso: datos.peso,
      observaciones: datos.observaciones?.trim() || null,
    },
  });
}

// =========================================================================
// MI CUOTA
// =========================================================================

export interface DeudaListada {
  idDeuda: number;
  monto: number;
  fechaGeneracion: string;
  fechaVencimiento?: string;
  /** Días de atraso respecto de hoy. 0 o negativo = todavía no venció. */
  diasDeAtraso: number;
  /** Descripción de la deuda ("cuota de marzo"), no una nota interna. */
  observaciones?: string;
}

export interface PagoListado {
  idPago: number;
  fecha: string;
  monto: number;
  metodo: string;
  estado: string;
  numeroComprobante?: string;
}

export interface MiCuota {
  /**
   * False = no tiene ninguna membresía. Hace falta como campo propio porque
   * `vencimiento` undefined no alcanza para distinguir "sin membresía" de
   * "con membresía que no vence nunca" — las dos lo dejan undefined.
   */
  tieneMembresia: boolean;
  alDia: boolean;
  plan: string;
  estado: EstadoSocioValue;
  precioPactado?: number;
  fechaInicio?: string;
  vencimiento?: string;
  /** Días hasta el vencimiento. Negativo = ya venció. */
  diasParaVencer?: number;
  /** Sólo las PENDIENTE: las PAGADA y CONDONADA ya no se le reclaman. */
  deudas: DeudaListada[];
  totalAdeudado: number;
  pagos: PagoListado[];
}

interface CuotaApi {
  tiene_membresia: boolean;
  al_dia: boolean;
  plan: string | null;
  estado: string;
  precio_pactado: number | null;
  fecha_inicio: string | null;
  fecha_vencimiento: string | null;
  dias_restantes: number | null;
  deuda_total: number;
  deudas: {
    id_deuda: number;
    monto: number;
    fecha_generacion: string;
    fecha_vencimiento: string | null;
    dias_de_atraso: number;
    observaciones: string | null;
  }[];
  ultimos_pagos: {
    id_pago: number;
    monto: number;
    metodo: string;
    fecha_pago: string;
    estado: string;
    numero_comprobante: string | null;
  }[];
}

/**
 * Estado de la cuota del socio.
 *
 * Es el espejo de /cobros/socio/{id} pero SIN el id. Y muestra menos: el
 * socio ve el TOTAL de lo que debe, no el detalle de cada deuda — las
 * observaciones de una deuda son notas internas del mostrador.
 *
 * Acá no hay ningún pagarDeuda(), ni siquiera comentado: esta pantalla es de
 * consulta. Cobrar es del otro lado del mostrador y vive en cobrosService.
 */
export async function getMiCuota(): Promise<MiCuota> {
  const c = await pedir<CuotaApi>('/portal/mi-cuota');
  return {
    tieneMembresia: c.tiene_membresia,
    alDia: c.al_dia,
    plan: c.plan ?? 'Sin plan',
    estado: c.estado as EstadoSocioValue,
    precioPactado: c.precio_pactado ?? undefined,
    fechaInicio: c.fecha_inicio ?? undefined,
    vencimiento: c.fecha_vencimiento ?? undefined,
    diasParaVencer: c.dias_restantes ?? undefined,
    deudas: c.deudas.map((d) => ({
      idDeuda: d.id_deuda,
      monto: d.monto,
      fechaGeneracion: d.fecha_generacion,
      fechaVencimiento: d.fecha_vencimiento ?? undefined,
      diasDeAtraso: d.dias_de_atraso,
      observaciones: d.observaciones ?? undefined,
    })),
    totalAdeudado: c.deuda_total,
    pagos: c.ultimos_pagos.map((p) => ({
      idPago: p.id_pago,
      fecha: p.fecha_pago,
      monto: p.monto,
      metodo: p.metodo,
      estado: p.estado,
      numeroComprobante: p.numero_comprobante ?? undefined,
    })),
  };
}

// =========================================================================
// MIS ASISTENCIAS
// =========================================================================

export interface AsistenciaListada {
  idAsistencia: number;
  fechaHoraIngreso: string;
  fechaHoraEgreso?: string;
}

/** Los últimos ingresos al gimnasio. Es la base del gráfico de regularidad. */
export async function getMisAsistencias(): Promise<AsistenciaListada[]> {
  const datos = await pedir<{
    id_asistencia: number;
    fecha_hora_ingreso: string;
    fecha_hora_egreso: string | null;
  }[]>('/portal/mi-progreso/asistencias');

  return datos.map((a) => ({
    idAsistencia: a.id_asistencia,
    fechaHoraIngreso: a.fecha_hora_ingreso,
    fechaHoraEgreso: a.fecha_hora_egreso ?? undefined,
  }));
}

// =============================================================================
// AUTOGESTIÓN — lo que el socio hace solo
// =============================================================================
//
// Todo lo de acá abajo apunta a `/portal/mi-*`, donde el backend saca el
// id_socio del TOKEN FIRMADO y no del cuerpo del pedido.
//
// No es un detalle de estilo. Las vistas del socio venían llamando a los
// endpoints del personal (`/actividades/planes/{id}/comprar`) mandando
// `id_socio` en el cuerpo, y eso hoy devuelve 403 para cualquier socio: esas
// rutas están protegidas con acciones que sólo tiene el mostrador. O sea que
// la sección de Actividades del socio no funcionaba — no le faltaba una
// función, devolvía 403 en las cuatro llamadas.
//
// Y aunque el permiso se hubiera aflojado, mandar el id en el cuerpo es el
// vector que documentó la auditoría del 2026-08-03: un socio cambiando ese
// número compraba, cancelaba o cobraba a nombre de otro.

/** Los métodos que acepta el backend (enum del esquema). */
export type MetodoPagoSocio =
  | 'EFECTIVO'
  | 'DEBITO'
  | 'CREDITO'
  | 'TRANSFERENCIA'
  | 'BILLETERA_VIRTUAL';

interface PlanApi {
  id_plan_actividad: number;
  id_actividad: number;
  nombre: string;
  tipo_limite: 'POR_SEMANA' | 'POR_MES' | 'CLASE_SUELTA';
  cantidad: number;
  precio: number;
  activo: boolean;
}

interface ActividadCatalogoApi {
  id_actividad: number;
  nombre: string;
  descripcion?: string | null;
  cupo_default: number;
  horas_anticipacion_cancelacion: number;
  minutos_tolerancia: number;
  planes: PlanApi[];
}

/**
 * El catálogo con sus planes, en UN pedido.
 *
 * El backend ya devuelve los planes anidados y filtrados —sólo actividades
 * activas con planes activos—, así que no hace falta una segunda vuelta por
 * actividad. Ofrecerle a alguien comprar un plan discontinuado terminaría en
 * un rechazo que no entendería.
 */
export async function getCatalogoDelSocio(): Promise<
  Array<ActividadListada & { planes: PlanActividadListado[] }>
> {
  const datos = await pedir<ActividadCatalogoApi[]>('/portal/mis-actividades/catalogo');
  return datos.map((a) => ({
    idActividad: a.id_actividad,
    nombre: a.nombre,
    descripcion: a.descripcion ?? undefined,
    cupoDefault: a.cupo_default,
    // La clase suelta es un plan (CLASE_SUELTA): su precio sale de ahí.
    precioClaseSuelta:
      Number(a.planes.find((p) => p.tipo_limite === 'CLASE_SUELTA')?.precio ?? 0),
    horasAnticipacionCancelacion: a.horas_anticipacion_cancelacion,
    planes: a.planes.map((p) => ({
      idPlanActividad: p.id_plan_actividad,
      idActividad: p.id_actividad,
      nombre: p.nombre,
      tipoLimite: p.tipo_limite,
      cantidad: p.cantidad,
      precio: Number(p.precio),
    })),
  }));
}

/** Compra un abono. NO lleva id_socio: sale del token. */
export async function comprarMiPlan(
  idPlanActividad: number,
  metodo: MetodoPagoSocio,
): Promise<{ mensaje: string }> {
  return pedir<{ mensaje: string }>(
    `/portal/mis-actividades/planes/${idPlanActividad}/comprar`,
    { metodo: 'POST', cuerpo: { metodo } },
  );
}

/** Paga una clase suelta y queda reservado en ese turno. */
export async function comprarMiClaseSuelta(
  idTurno: number,
  metodo: MetodoPagoSocio,
): Promise<{ mensaje: string }> {
  return pedir<{ mensaje: string }>(
    `/portal/mis-turnos/${idTurno}/clase-suelta`,
    { metodo: 'POST', cuerpo: { metodo } },
  );
}

// =============================================================================
// TURNOS
// =============================================================================

/**
 * Un turno como lo ve el socio, con lo que necesita para decidir.
 *
 * Extiende TurnoDisponible con tres cosas que el catálogo del personal no
 * tiene y que acá cambian el comportamiento del botón: si ya está anotado, si
 * está en lista de espera, y cuánta gente está esperando.
 */
export interface TurnoDelSocio extends TurnoDisponible {
  enEspera: number;
  yaAnotado: boolean;
  miEstado?: 'RESERVADA' | 'EN_ESPERA';
  idMiReserva?: number;
  minutosTolerancia: number;
  horasAnticipacionCancelacion: number;
}

interface TurnoSocioApi {
  id_turno: number;
  actividad: string;
  fecha: string;
  hora: string;
  cupo_maximo: number;
  ocupados: number;
  lugares_libres: number;
  en_espera: number;
  profesor?: string | null;
  minutos_tolerancia: number;
  horas_anticipacion_cancelacion: number;
  ya_anotado: boolean;
  mi_estado?: string | null;
  id_mi_reserva?: number | null;
}

/**
 * Las clases a las que se puede anotar, incluidas las LLENAS.
 *
 * Las llenas vienen a propósito: esconderlas haría que el socio ni supiera
 * que existe la clase, y la lista de espera —que existe justamente para
 * eso— no la usaría nadie.
 */
export async function getTurnosDelSocio(dias = 14): Promise<TurnoDelSocio[]> {
  const datos = await pedir<TurnoSocioApi[]>(
    `/portal/mis-turnos/disponibles?dias=${dias}`,
  );
  return datos.map((t) => ({
    idTurno: t.id_turno,
    // El backend manda el nombre, no el id: el socio no elige por id y la
    // vista no necesita el número para nada.
    idActividad: 0,
    nombreActividad: t.actividad,
    fecha: t.fecha,
    hora: t.hora,
    cupoMaximo: t.cupo_maximo,
    cupoDisponible: t.lugares_libres,
    nombreProfesional: t.profesor ?? undefined,
    enEspera: t.en_espera,
    yaAnotado: t.ya_anotado,
    miEstado: (t.mi_estado as 'RESERVADA' | 'EN_ESPERA' | undefined) ?? undefined,
    idMiReserva: t.id_mi_reserva ?? undefined,
    minutosTolerancia: t.minutos_tolerancia,
    horasAnticipacionCancelacion: t.horas_anticipacion_cancelacion,
  }));
}

/**
 * Se anota. Si la clase está llena queda EN_ESPERA en vez de fallar: cuando
 * alguien cancele, el backend lo promueve solo y le avisa.
 */
export async function reservarMiTurno(
  idTurno: number,
): Promise<{ estado: 'RESERVADA' | 'EN_ESPERA' }> {
  const r = await pedir<{ estado: 'RESERVADA' | 'EN_ESPERA' }>(
    `/portal/mis-turnos/${idTurno}/reservar`,
    { metodo: 'POST' },
  );
  return { estado: r.estado };
}

/** Se baja. El backend verifica que la reserva sea suya. */
export async function cancelarMiTurno(idReserva: number): Promise<void> {
  await pedir(`/portal/mis-turnos/${idReserva}/cancelar`, { metodo: 'POST' });
}

// =============================================================================
// MI MEMBRESÍA — congelar, reanudar, darse de baja
// =============================================================================

export interface Congelamiento {
  idCongelamiento: number;
  fechaInicio: string;
  fechaFin: string;
  fechaReanudacion?: string;
  diasAplicados?: number;
  diasPedidos: number;
  motivo?: string;
  estado: 'ACTIVO' | 'FINALIZADO' | 'CANCELADO';
  mensaje?: string;
}

interface CongelamientoApi {
  id_congelamiento: number;
  fecha_inicio: string;
  fecha_fin: string;
  fecha_reanudacion?: string | null;
  dias_aplicados?: number | null;
  dias_pedidos: number;
  motivo?: string | null;
  estado: 'ACTIVO' | 'FINALIZADO' | 'CANCELADO';
  mensaje?: string | null;
}

function aCongelamiento(c: CongelamientoApi): Congelamiento {
  return {
    idCongelamiento: c.id_congelamiento,
    fechaInicio: c.fecha_inicio,
    fechaFin: c.fecha_fin,
    fechaReanudacion: c.fecha_reanudacion ?? undefined,
    diasAplicados: c.dias_aplicados ?? undefined,
    diasPedidos: c.dias_pedidos,
    motivo: c.motivo ?? undefined,
    estado: c.estado,
    mensaje: c.mensaje ?? undefined,
  };
}

export async function getMisCongelamientos(): Promise<Congelamiento[]> {
  const datos = await pedir<CongelamientoApi[]>('/portal/mi-membresia/congelamientos');
  return datos.map(aCongelamiento);
}

/**
 * Pausa la membresía. `fechaFin` es un TOPE, no una promesa: se puede
 * reanudar antes y sólo se suman los días que realmente estuvo pausada.
 */
export async function congelarMiMembresia(
  fechaFin: string,
  motivo?: string,
  fechaInicio?: string,
): Promise<Congelamiento> {
  const datos = await pedir<CongelamientoApi>('/portal/mi-membresia/congelar', {
    metodo: 'POST',
    cuerpo: { fecha_fin: fechaFin, motivo: motivo || null, fecha_inicio: fechaInicio || null },
  });
  return aCongelamiento(datos);
}

export async function reanudarMiMembresia(): Promise<Congelamiento> {
  const datos = await pedir<CongelamientoApi>('/portal/mi-membresia/reanudar', {
    metodo: 'POST',
  });
  return aCongelamiento(datos);
}

/**
 * Se da de baja.
 *
 * La cuenta NO se desactiva: puede seguir entrando a ver su historial y, si
 * vuelve, no hace falta darlo de alta otra vez. (El endpoint del mostrador sí
 * desactiva la cuenta, y por eso este no lo reusa: aplicado a uno mismo,
 * apretar el botón lo dejaría afuera sin poder volver a entrar.)
 */
export async function darmeDeBaja(motivo?: string): Promise<{ mensaje: string }> {
  return pedir<{ mensaje: string }>('/portal/mi-membresia/baja', {
    metodo: 'POST',
    cuerpo: { motivo: motivo || null },
  });
}

// =============================================================================
// MIS ABONOS
// =============================================================================

interface InscripcionApiSocio {
  id_inscripcion: number;
  id_actividad: number;
  actividad: string;
  plan: string;
  tipo_limite: 'POR_SEMANA' | 'POR_MES' | 'CLASE_SUELTA';
  cantidad: number;
  clases_restantes?: number | null;
  precio_pactado: number;
  fecha_inicio: string;
  fecha_vencimiento: string;
  estado: 'ACTIVA' | 'VENCIDA' | 'CANCELADA';
}

/** Los abonos propios. El id sale del token, no de la URL. */
export async function getMisAbonos(): Promise<InscripcionListada[]> {
  const datos = await pedir<InscripcionApiSocio[]>('/portal/mis-actividades/inscripciones');
  return datos.map((i) => ({
    idInscripcion: i.id_inscripcion,
    idActividad: i.id_actividad,
    nombreActividad: i.actividad,
    nombrePlan: i.plan,
    tipoLimite: i.tipo_limite,
    cantidad: i.cantidad,
    clasesRestantes: i.clases_restantes ?? undefined,
    precioPactado: Number(i.precio_pactado),
    fechaInicio: i.fecha_inicio,
    fechaVencimiento: i.fecha_vencimiento,
    estado: i.estado,
  }));
}

/** Da de baja un abono propio. */
export async function cancelarMiAbono(idInscripcion: number): Promise<void> {
  await pedir(`/portal/mis-actividades/inscripciones/${idInscripcion}/cancelar`, {
    metodo: 'POST',
  });
}

// =============================================================================
// PAGO ONLINE
// =============================================================================

export interface PagoIniciado {
  idPago: number;
  monto: number;
  plan: string;
  urlCheckout: string;
  simulado: boolean;
  mensaje: string;
}

interface PagoIniciadoApi {
  id_pago: number;
  monto: number;
  plan: string;
  url_checkout: string;
  simulado: boolean;
  mensaje: string;
}

/**
 * Arranca el pago de una cuota y devuelve a dónde mandar al socio.
 *
 * NO lleva monto: sale del plan y lo lee el backend. Con un monto en el
 * cuerpo, cualquiera con la consola abierta pagaría $1 una cuota de $30.000.
 *
 * El pago queda PENDIENTE hasta que Mercado Pago confirme. Que el socio haya
 * apretado el botón no significa que la plata llegó.
 */
export async function iniciarPagoDeCuota(idTipoMembresia: number): Promise<PagoIniciado> {
  const d = await pedir<PagoIniciadoApi>('/portal/mi-cuota/pagar', {
    metodo: 'POST',
    cuerpo: { id_tipo_membresia: idTipoMembresia },
  });
  return {
    idPago: d.id_pago,
    monto: Number(d.monto),
    plan: d.plan,
    urlCheckout: d.url_checkout,
    simulado: d.simulado,
    mensaje: d.mensaje,
  };
}

/**
 * Acredita un pago a mano. SÓLO existe con el backend en modo simulado.
 *
 * Es el reemplazo del webhook mientras no haya URL pública: sin esto el flujo
 * se corta en "te llevamos a Mercado Pago" y no hay forma de probar la
 * pantalla después del pago. Con un token real cargado el backend responde
 * 404 y este llamado falla, que es lo correcto.
 */
export async function simularAcreditacion(idPago: number): Promise<{ mensaje: string }> {
  return pedir<{ mensaje: string }>(`/portal/mi-cuota/pagar/${idPago}/simular`, {
    metodo: 'POST',
  });
}

export interface PlanDisponible {
  idTipoMembresia: number;
  nombre: string;
  descripcion?: string;
  duracionDias: number;
  precio: number;
}

/**
 * Los planes que el socio puede comprar.
 *
 * Endpoint propio y no /cobros/tipos-membresia: ese está protegido con la
 * sección COBROS, que el socio tiene en NINGUNO. Trae sólo lo necesario para
 * elegir.
 */
export async function getPlanesDisponibles(): Promise<PlanDisponible[]> {
  const datos = await pedir<Array<{
    id_tipo_membresia: number;
    nombre: string;
    descripcion?: string | null;
    duracion_dias: number;
    precio: number;
  }>>('/portal/mi-cuota/planes');
  return datos.map((p) => ({
    idTipoMembresia: p.id_tipo_membresia,
    nombre: p.nombre,
    descripcion: p.descripcion ?? undefined,
    duracionDias: p.duracion_dias,
    precio: Number(p.precio),
  }));
}

// =========================================================================
// MIS CONDICIONES DE SALUD
// =========================================================================
//
// El socio ve y administra las SUYAS. No usa la acción `verHistorialMedico`
// —esa es para ver las de OTROS, y el socio no la tiene— sino su propia
// sección MI_PERFIL. Es la misma distinción de siempre en este archivo:
// mirar la ficha ajena y mirar la propia son permisos distintos.
//
// Que el socio pueda CARGARLAS es deliberado y va en la dirección de que se
// maneje solo: "soy asmático" es algo que él sabe y el gimnasio necesita, y
// obligarlo a ir al mostrador a contarlo —donde además el recepcionista no
// debería enterarse— sería exactamente al revés.
//
// Estas funciones NO están en patologiasService: aquél habla con
// /patologias y /socios/{id}/patologias, que exigen `verHistorialMedico`.
// Llamarlas desde el portal daría 403. Misma tabla, otro permiso, otro
// service — igual que pasa con las cuotas.

export interface MiCondicion {
  idPatologia: number;
  nombre: string;
  descripcion?: string;
  /** ISO (yyyy-mm-dd). */
  fechaDiagnostico?: string;
  observaciones?: string;
}

interface MiCondicionApi {
  id_patologia: number;
  nombre: string;
  descripcion: string | null;
  fecha_diagnostico: string | null;
  observaciones: string | null;
}

function aMiCondicion(p: MiCondicionApi): MiCondicion {
  return {
    idPatologia: p.id_patologia,
    nombre: p.nombre,
    descripcion: p.descripcion ?? undefined,
    fechaDiagnostico: p.fecha_diagnostico ?? undefined,
    observaciones: p.observaciones ?? undefined,
  };
}

export async function getMisCondiciones(): Promise<MiCondicion[]> {
  const datos = await pedir<MiCondicionApi[]>('/portal/mis-patologias');
  return datos.map(aMiCondicion);
}

export interface CondicionDelCatalogo {
  idPatologia: number;
  nombre: string;
  descripcion?: string;
}

/**
 * El catálogo, recortado para el portal.
 *
 * Endpoint propio y no /patologias: ese exige `verHistorialMedico`, que el
 * socio tiene en false como todas las acciones. Mismo motivo por el que
 * getPlanesDisponibles no usa /cobros/tipos-membresia.
 */
export async function getCatalogoDeCondiciones(): Promise<CondicionDelCatalogo[]> {
  const datos = await pedir<MiCondicionApi[]>('/portal/catalogo-patologias');
  return datos.map((p) => ({
    idPatologia: p.id_patologia,
    nombre: p.nombre,
    descripcion: p.descripcion ?? undefined,
  }));
}

/**
 * Declara una condición propia.
 *
 * Sólo del catálogo: no se acepta texto libre. Si tiene algo que no está en
 * la lista, lo carga un entrenador o un nutricionista al catálogo primero.
 * Dejar escribir libremente lo rompería con veinte formas de escribir "asma"
 * y volvería inútil poder contar cuántos socios la tienen — que es todo el
 * motivo de que sea una tabla y no un varchar.
 */
export async function agregarMiCondicion(datos: {
  idPatologia: number;
  fechaDiagnostico?: string;
  observaciones?: string;
}): Promise<MiCondicion> {
  const respuesta = await pedir<MiCondicionApi>('/portal/mis-patologias', {
    metodo: 'POST',
    cuerpo: {
      id_patologia: datos.idPatologia,
      fecha_diagnostico: datos.fechaDiagnostico || null,
      observaciones: datos.observaciones?.trim() || null,
    },
  });
  return aMiCondicion(respuesta);
}

/**
 * Se saca una condición.
 *
 * No hay "editar" del lado del socio —el backend expone el PUT sólo para el
 * staff—, así que corregir una observación es quitarla y volver a cargarla.
 * Se pierde la fecha original, que es justamente lo que el PUT evita del otro
 * lado; queda anotado como asimetría conocida y no como olvido.
 */
export async function quitarMiCondicion(idPatologia: number): Promise<void> {
  await pedir<void>(`/portal/mis-patologias/${idPatologia}`, { metodo: 'DELETE' });
}

// =========================================================================
// MI ENTRENADOR
// =========================================================================
//
// Quién lo entrena HOY. A diferencia del endpoint del personal, acá el
// backend NO devuelve el historial: al socio le interesa a quién preguntarle
// hoy, no quién lo entrenaba en marzo. Ese dato es del gimnasio —sirve para
// auditar y para que un entrenador nuevo se ponga al día— y no aporta nada en
// la app de quien entrena.
//
// Va bajo la sección MI_RUTINA y no una propia: el entrenador a cargo es
// parte de la misma pregunta que "cuál es mi rutina", y crear una sección
// sólo para esto obligaría a sumarla a las tres copias de la matriz de
// permisos para una pantalla que no existe.
//
// OJO, NO CONFUNDIR con `MiRutina.entrenador`: ese es quien ARMÓ el plan, un
// dato de la rutina. Esto es quien está a cargo del socio, y pueden ser
// personas distintas — o puede haber entrenador a cargo sin ninguna rutina
// asignada todavía.

export interface MiEntrenador {
  idAsignacion: number;
  idEntrenador: number;
  nombre: string;
  especialidad?: string;
  /** ISO (yyyy-mm-dd). */
  desde: string;
}

export async function getMisEntrenadores(): Promise<MiEntrenador[]> {
  const datos = await pedir<Array<{
    id_asignacion: number;
    id_entrenador: number;
    entrenador: string;
    especialidad: string | null;
    fecha_inicio: string;
  }>>('/portal/mi-entrenador');
  return datos.map((a) => ({
    idAsignacion: a.id_asignacion,
    idEntrenador: a.id_entrenador,
    nombre: a.entrenador,
    especialidad: a.especialidad ?? undefined,
    desde: a.fecha_inicio,
  }));
}
