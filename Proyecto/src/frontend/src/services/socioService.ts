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

import type { EstadoSocioValue, NivelRutinaValue } from '../config';
import { pedir } from './api';

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
  nombre: string;
  grupoMuscular: string;
  series?: number;
  /** Texto libre: "10-12", "al fallo", "45 seg". */
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
  /** La rutina fue dada de baja pero la asignación sigue activa. */
  rutinaDeBaja: boolean;
  /** Desde cuándo la tiene asignada. Viene de la asignación, no de la plantilla. */
  fechaInicio: string;
  dias: DiaDeRutina[];
}

interface RutinaApi {
  id_rutina: number;
  nombre: string;
  nivel: string | null;
  objetivo: string | null;
  dias_por_semana: number | null;
  entrenador: string;
  rutina_de_baja: boolean;
  fecha_inicio: string;
  ejercicios: {
    id_rutina_ejercicio: number;
    nombre_ejercicio: string;
    grupo_muscular: string;
    dia: number;
    orden: number;
    series: number | null;
    repeticiones: string | null;
    peso_sugerido: number | null;
    descanso_segundos: number | null;
    observaciones: string | null;
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
      nombre: e.nombre_ejercicio,
      grupoMuscular: e.grupo_muscular,
      series: e.series ?? undefined,
      repeticiones: e.repeticiones ?? undefined,
      pesoSugerido: e.peso_sugerido ?? undefined,
      descansoSegundos: e.descanso_segundos ?? undefined,
      observaciones: e.observaciones ?? undefined,
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
export async function getMiRutina(): Promise<MiRutina | null> {
  const r = await pedir<RutinaApi | null>('/portal/mi-rutina');
  if (!r) return null;
  return {
    idRutina: r.id_rutina,
    nombre: r.nombre,
    nivel: (r.nivel ?? undefined) as NivelRutinaValue | undefined,
    objetivo: r.objetivo ?? undefined,
    diasPorSemana: r.dias_por_semana ?? undefined,
    entrenador: r.entrenador,
    // La rutina se dio de baja del catálogo pero la asignación sigue activa:
    // el socio la termina. La vista lo avisa para que sepa que no se la van a
    // renovar.
    rutinaDeBaja: r.rutina_de_baja,
    fechaInicio: r.fecha_inicio,
    dias: agruparPorDia(r.ejercicios),
  };
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

export async function getMiDieta(): Promise<MiDieta | null> {
  const d = await pedir<DietaApi | null>('/portal/mi-dieta');
  if (!d) return null;

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
