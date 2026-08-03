// "Base de datos" en memoria, compartida por todos los services.
//
// Por qué existe este archivo y no una copia de los datos dentro de cada
// service: si authService tuviera su lista de socios y dashboardService
// otra, un alta hecha desde el registro no aparecería nunca en el
// dashboard, y las dos listas irían divergiendo. Un solo backend real =
// una sola base acá.
//
// Todo vive en memoria y se pierde al recargar la página. El día que exista
// la API de FastAPI, este archivo se borra y cada service cambia sus
// lecturas por fetch — las firmas públicas de los services no cambian.

import type {
  Persona,
  Usuario,
  Telefono,
  Socio,
  Baja,
  Auditoria,
  Sede,
  Empleado,
  Entrenador,
  Nutricionista,
  Recepcionista,
  TipoMembresia,
  Membresia,
  Pago,
  Turno,
  Rutina,
  AsignacionRutina,
  Dieta,
  Comida,
  AsignacionDieta,
  Ejercicio,
  RutinaEjercicio,
  RegistroSalud,
  Deuda,
} from '../types';
import { Roles, type RolValue } from '../config';
import { aFechaISO, aTimestampISO } from '../utils/fechas';

// El rol todavía no es una tabla propia (la spec de roles/permisos no está
// escrita); hasta entonces viaja pegado al usuario en el mock.
export interface UsuarioMock extends Usuario {
  rol: RolValue;
}

// --- Helpers de semilla ---
//
// Las fechas se generan relativas a hoy, no fijas: si estuvieran escritas a
// mano ("2026-08-15"), en un mes el dashboard mostraría cero ingresos y cero
// altas del mes y parecería roto.

/** Días de un mes "tipo", usados para escalar las semillas del mes en curso. */
const DIAS_MES_TIPICO = 30;

/**
 * Día `dia` del mes desplazado `meses` respecto del actual, en hora local.
 *
 * Para meses pasados el día se usa tal cual. Para el mes en curso se escala
 * sobre los días ya transcurridos: pedir el día 14 un día 3 devuelve el día
 * 1, no el 14. Sin ese ajuste las semillas futuras se recortarían todas al
 * instante actual y el feed mostraría varias altas "hace un minuto", que es
 * justo lo que no pasa en un gimnasio real.
 */
function fechaSemilla(meses: number, dia: number, hora = 10): Date {
  const ahora = new Date();

  if (meses !== 0) {
    return new Date(ahora.getFullYear(), ahora.getMonth() + meses, dia, hora);
  }

  const diaEscalado = Math.max(1, Math.round((dia / DIAS_MES_TIPICO) * ahora.getDate()));
  const fecha = new Date(ahora.getFullYear(), ahora.getMonth(), diaEscalado, hora);

  // Cayó hoy pero a una hora que todavía no llegó: se corre a un rato antes
  // de ahora. Nunca se siembran datos en el futuro.
  const UNA_HORA_MS = 60 * 60 * 1000;
  return fecha > ahora ? new Date(ahora.getTime() - UNA_HORA_MS) : fecha;
}

/** Fecha a N días de hoy (negativo = pasado). Para vencimientos. */
function fechaRelativa(dias: number): Date {
  const fecha = new Date();
  fecha.setDate(fecha.getDate() + dias);
  return fecha;
}

// --- Sedes ---

export const sedes: Sede[] = [
  {
    id_sede: 1,
    id_dueno: 1,
    nombre: 'Sede Central',
    localidad: 'Moreno',
    abierto_24hs: true,
    activo: true,
  },
];

// --- Personas ---
//
// 1 y 2 son las cuentas demo (socio y dueño). El resto son socios de
// relleno para que el dashboard tenga datos con los que calcular.

export const personas: Persona[] = [
  // La cuenta demo del socio es la única con la ficha COMPLETA (domicilio,
  // nacimiento, contacto de emergencia). No es capricho: es la persona que
  // se usa para probar el portal, y "Mi perfil" muestra justamente esos
  // campos. Con la ficha a medias no se distinguiría un dato que falta en
  // la base de un bug de la vista.
  {
    id_persona: 1,
    dni: '30111222',
    apellido: 'Demo',
    nombre: 'Socio',
    email: 'socio@olimpos.local',
    sexo: 'Masculino',
    calle: 'Av. Victorica',
    numero_calle: '1450',
    localidad: 'Moreno',
    fecha_nacimiento: '1995-04-18',
    emergencia_nombre: 'Marta Demo',
    emergencia_telefono: '1155667788',
    emergencia_parentesco: 'Madre',
    fecha_alta: aTimestampISO(fechaSemilla(-14, 5)),
    activo: true,
  },
  {
    id_persona: 2,
    dni: '00000000',
    apellido: 'Admin',
    nombre: 'Dueño',
    email: 'dueno@olimpos.local',
    fecha_alta: aTimestampISO(fechaSemilla(-14, 5)),
    activo: true,
  },
  {
    id_persona: 3,
    dni: '31445678',
    apellido: 'Fernández',
    nombre: 'Lucía',
    email: 'lucia.fernandez@olimpos.local',
    fecha_alta: aTimestampISO(fechaSemilla(-5, 12)),
    activo: false,
  },
  {
    id_persona: 4,
    dni: '33987654',
    apellido: 'Gómez',
    nombre: 'Martín',
    email: 'martin.gomez@olimpos.local',
    fecha_alta: aTimestampISO(fechaSemilla(-3, 20)),
    activo: true,
  },
  {
    id_persona: 5,
    dni: '35112233',
    apellido: 'Ruiz',
    nombre: 'Camila',
    email: 'camila.ruiz@olimpos.local',
    fecha_alta: aTimestampISO(fechaSemilla(-1, 4)),
    activo: true,
  },
  {
    id_persona: 6,
    dni: '36778899',
    apellido: 'Sosa',
    nombre: 'Diego',
    email: 'diego.sosa@olimpos.local',
    fecha_alta: aTimestampISO(fechaSemilla(-1, 11)),
    activo: true,
  },
  {
    id_persona: 7,
    dni: '37223344',
    apellido: 'Ríos',
    nombre: 'Valentina',
    email: 'valentina.rios@olimpos.local',
    fecha_alta: aTimestampISO(fechaSemilla(-1, 22)),
    activo: true,
  },
  {
    id_persona: 8,
    dni: '38445566',
    apellido: 'Paz',
    nombre: 'Nicolás',
    email: 'nicolas.paz@olimpos.local',
    fecha_alta: aTimestampISO(fechaSemilla(0, 2)),
    activo: true,
  },
  {
    id_persona: 9,
    dni: '39667788',
    apellido: 'Molina',
    nombre: 'Julieta',
    email: 'julieta.molina@olimpos.local',
    fecha_alta: aTimestampISO(fechaSemilla(0, 5)),
    activo: true,
  },
  {
    id_persona: 10,
    dni: '40889900',
    apellido: 'Arce',
    nombre: 'Federico',
    email: 'federico.arce@olimpos.local',
    fecha_alta: aTimestampISO(fechaSemilla(0, 9)),
    activo: true,
  },
  {
    id_persona: 11,
    dni: '41334455',
    apellido: 'Ledesma',
    nombre: 'Sofía',
    email: 'sofia.ledesma@olimpos.local',
    fecha_alta: aTimestampISO(fechaSemilla(0, 14)),
    activo: true,
  },
  // 12 en adelante: personal del gimnasio (ver empleados más abajo).
  {
    id_persona: 12,
    dni: '29556677',
    apellido: 'Bustos',
    nombre: 'Sergio',
    email: 'sergio.bustos@olimpos.local',
    fecha_alta: aTimestampISO(fechaSemilla(-14, 5)),
    activo: true,
  },
  {
    id_persona: 13,
    dni: '32778899',
    apellido: 'Herrera',
    nombre: 'Paula',
    email: 'paula.herrera@olimpos.local',
    fecha_alta: aTimestampISO(fechaSemilla(-9, 8)),
    activo: true,
  },
  {
    id_persona: 14,
    dni: '34990011',
    apellido: 'Rocha',
    nombre: 'Iván',
    email: 'ivan.rocha@olimpos.local',
    fecha_alta: aTimestampISO(fechaSemilla(-11, 3)),
    activo: false,
  },
  {
    id_persona: 15,
    dni: '30443322',
    apellido: 'Lopresti',
    nombre: 'Mariana',
    email: 'mariana.lopresti@olimpos.local',
    fecha_alta: aTimestampISO(fechaSemilla(-7, 15)),
    activo: true,
  },
  {
    id_persona: 16,
    dni: '36221100',
    apellido: 'Bianchi',
    nombre: 'Carla',
    email: 'carla.bianchi@olimpos.local',
    fecha_alta: aTimestampISO(fechaSemilla(-6, 2)),
    activo: true,
  },
  {
    id_persona: 17,
    dni: '33667711',
    apellido: 'Quiroga',
    nombre: 'Andrés',
    email: 'andres.quiroga@olimpos.local',
    fecha_alta: aTimestampISO(fechaSemilla(-4, 19)),
    activo: true,
  },
  {
    id_persona: 18,
    dni: '38112299',
    apellido: 'Vega',
    nombre: 'Rocío',
    email: 'rocio.vega@olimpos.local',
    fecha_alta: aTimestampISO(fechaSemilla(-2, 10)),
    activo: true,
  },
];

// --- Usuarios ---
//
// password_hash guarda la contraseña en texto plano SOLO en este mock, para
// poder comparar sin librería de hashing en el frontend. El backend real
// nunca va a mandar este campo — existe acá únicamente para simular login.
// Los socios de relleno no tienen usuario: en el gimnasio real la mayoría
// se da de alta en el mostrador y nunca crea cuenta en la app.

export const usuarios: UsuarioMock[] = [
  {
    id_usuario: 1,
    id_persona: 1,
    username: 'socio_demo',
    password_hash: 'Socio1234',
    intentos_fallidos: 0,
    bloqueado: false,
    activo: true,
    rol: Roles.SOCIO,
  },
  {
    id_usuario: 2,
    id_persona: 2,
    username: 'dueno_demo',
    password_hash: 'Dueno1234',
    intentos_fallidos: 0,
    bloqueado: false,
    activo: true,
    rol: Roles.DUENO,
  },
  // Una cuenta demo por rol de personal, para poder probar la matriz de
  // permisos sin tener que crearlas a mano en cada recarga. Apuntan a
  // empleados reales del seed de más abajo: Sergio Bustos (entrenador, id
  // 12), Mariana Lopresti (nutricionista, id 15) y Carla Bianchi
  // (recepcionista, id 16).
  {
    id_usuario: 3,
    id_persona: 12,
    username: 'entrenador_demo',
    password_hash: 'Entrenador1234',
    intentos_fallidos: 0,
    bloqueado: false,
    activo: true,
    rol: Roles.ENTRENADOR,
  },
  {
    id_usuario: 4,
    id_persona: 15,
    username: 'nutri_demo',
    password_hash: 'Nutri1234',
    intentos_fallidos: 0,
    bloqueado: false,
    activo: true,
    rol: Roles.NUTRICIONISTA,
  },
  {
    id_usuario: 5,
    id_persona: 16,
    username: 'recepcion_demo',
    password_hash: 'Recepcion1234',
    intentos_fallidos: 0,
    bloqueado: false,
    activo: true,
    rol: Roles.RECEPCIONISTA,
  },
];

// --- Teléfonos ---

export const telefonos: Telefono[] = [
  { id_telefono: 1, id_persona: 1, numero: '1122334455', tipo: 'CELULAR', principal: true },
  { id_telefono: 2, id_persona: 2, numero: '1199887766', tipo: 'CELULAR', principal: true },
  { id_telefono: 3, id_persona: 12, numero: '1144556677', tipo: 'CELULAR', principal: true },
  { id_telefono: 4, id_persona: 13, numero: '1133221100', tipo: 'CELULAR', principal: true },
  { id_telefono: 5, id_persona: 15, numero: '1155443322', tipo: 'CELULAR', principal: true },
  { id_telefono: 6, id_persona: 16, numero: '1177889900', tipo: 'CELULAR', principal: true },
];

// --- Socios ---
//
// La persona 2 (dueño) no es socio. El socio 2 está dado de baja: sirve
// para que "Socios activos" no sea simplemente la cantidad de filas.

export const socios: Socio[] = [
  {
    id_socio: 1,
    id_persona: 1,
    id_sede: 1,
    numero_socio: 'S-0001',
    fecha_alta: aFechaISO(fechaSemilla(-14, 5)),
    activo: true,
  },
  {
    id_socio: 2,
    id_persona: 3,
    id_sede: 1,
    numero_socio: 'S-0002',
    fecha_alta: aFechaISO(fechaSemilla(-5, 12)),
    activo: false,
  },
  {
    id_socio: 3,
    id_persona: 4,
    id_sede: 1,
    numero_socio: 'S-0003',
    fecha_alta: aFechaISO(fechaSemilla(-3, 20)),
    activo: true,
  },
  {
    id_socio: 4,
    id_persona: 5,
    id_sede: 1,
    numero_socio: 'S-0004',
    fecha_alta: aFechaISO(fechaSemilla(-1, 4)),
    activo: true,
  },
  {
    id_socio: 5,
    id_persona: 6,
    id_sede: 1,
    numero_socio: 'S-0005',
    fecha_alta: aFechaISO(fechaSemilla(-1, 11)),
    activo: true,
  },
  {
    id_socio: 6,
    id_persona: 7,
    id_sede: 1,
    numero_socio: 'S-0006',
    fecha_alta: aFechaISO(fechaSemilla(-1, 22)),
    activo: true,
  },
  {
    id_socio: 7,
    id_persona: 8,
    id_sede: 1,
    numero_socio: 'S-0007',
    fecha_alta: aFechaISO(fechaSemilla(0, 2)),
    activo: true,
  },
  {
    id_socio: 8,
    id_persona: 9,
    id_sede: 1,
    numero_socio: 'S-0008',
    fecha_alta: aFechaISO(fechaSemilla(0, 5)),
    activo: true,
  },
  {
    id_socio: 9,
    id_persona: 10,
    id_sede: 1,
    numero_socio: 'S-0009',
    fecha_alta: aFechaISO(fechaSemilla(0, 9)),
    activo: true,
  },
  {
    id_socio: 10,
    id_persona: 11,
    id_sede: 1,
    numero_socio: 'S-0010',
    fecha_alta: aFechaISO(fechaSemilla(0, 14)),
    activo: true,
  },
];

// --- Bajas ---

export const bajas: Baja[] = [
  {
    id_baja: 1,
    id_socio: 2,
    fecha_baja: aFechaISO(fechaSemilla(-1, 25)),
    tipo: 'MORA',
    motivo: 'Tres cuotas impagas',
  },
];

// --- Personal ---
//
// Empleado guarda lo común (legajo, sede, ingreso/egreso) y el rol sale de
// en cuál de las tres tablas hijas está la fila. Iván Rocha está inactivo
// (con fecha_egreso) para que la vista tenga un caso de baja real.

export const empleados: Empleado[] = [
  {
    id_empleado: 1,
    id_persona: 12,
    id_sede: 1,
    legajo: 'E-0001',
    fecha_ingreso: aFechaISO(fechaSemilla(-14, 5)),
    activo: true,
  },
  {
    id_empleado: 2,
    id_persona: 13,
    id_sede: 1,
    legajo: 'E-0002',
    fecha_ingreso: aFechaISO(fechaSemilla(-9, 8)),
    activo: true,
  },
  {
    id_empleado: 3,
    id_persona: 14,
    id_sede: 1,
    legajo: 'E-0003',
    fecha_ingreso: aFechaISO(fechaSemilla(-11, 3)),
    fecha_egreso: aFechaISO(fechaSemilla(-2, 20)),
    activo: false,
  },
  {
    id_empleado: 4,
    id_persona: 15,
    id_sede: 1,
    legajo: 'E-0004',
    fecha_ingreso: aFechaISO(fechaSemilla(-7, 15)),
    activo: true,
  },
  {
    id_empleado: 5,
    id_persona: 16,
    id_sede: 1,
    legajo: 'E-0005',
    fecha_ingreso: aFechaISO(fechaSemilla(-6, 2)),
    activo: true,
  },
  {
    id_empleado: 6,
    id_persona: 17,
    id_sede: 1,
    legajo: 'E-0006',
    fecha_ingreso: aFechaISO(fechaSemilla(-4, 19)),
    activo: true,
  },
  {
    id_empleado: 7,
    id_persona: 18,
    id_sede: 1,
    legajo: 'E-0007',
    fecha_ingreso: aFechaISO(fechaSemilla(-2, 10)),
    activo: true,
  },
];

export const entrenadores: Entrenador[] = [
  {
    id_entrenador: 1,
    id_empleado: 1,
    titulo: 'Profesor de Educación Física',
    especialidad: 'Musculación',
    matricula: 'EF-14522',
  },
  {
    id_entrenador: 2,
    id_empleado: 2,
    titulo: 'Profesora de Educación Física',
    especialidad: 'Entrenamiento funcional',
    matricula: 'EF-20871',
  },
  {
    id_entrenador: 3,
    id_empleado: 3,
    especialidad: 'CrossFit',
    matricula: 'EF-19034',
  },
];

export const nutricionistas: Nutricionista[] = [
  {
    id_nutricionista: 1,
    id_empleado: 4,
    titulo: 'Licenciada en Nutrición',
    matricula: 'MN-8823',
  },
];

export const recepcionistas: Recepcionista[] = [
  { id_recepcionista: 1, id_empleado: 5, turno_laboral: 'Mañana' },
  { id_recepcionista: 2, id_empleado: 6, turno_laboral: 'Tarde' },
  { id_recepcionista: 3, id_empleado: 7, turno_laboral: 'Noche' },
];

// --- Tipos de membresía y membresías ---

export const tiposMembresia: TipoMembresia[] = [
  {
    id_tipo_membresia: 1,
    nombre: 'Mensual Full',
    duracion_dias: 30,
    precio_actual: 28000,
    activo: true,
  },
  {
    id_tipo_membresia: 2,
    nombre: 'Mensual Básico',
    duracion_dias: 30,
    precio_actual: 19500,
    activo: true,
  },
  {
    id_tipo_membresia: 3,
    nombre: 'Trimestral Full',
    duracion_dias: 90,
    precio_actual: 75000,
    activo: true,
  },
  {
    id_tipo_membresia: 4,
    nombre: 'Pase Libre Anual',
    duracion_dias: 365,
    precio_actual: 260000,
    activo: true,
  },
];

// Los vencimientos son relativos a hoy a propósito, para que el dashboard
// muestre siempre una mezcla de estados: vigentes, por vencer y vencidas.
export const membresias: Membresia[] = [
  {
    id_membresia: 1,
    id_socio: 1,
    id_tipo_membresia: 4,
    precio_pactado: 260000,
    fecha_inicio: aFechaISO(fechaRelativa(-345)),
    fecha_vencimiento: aFechaISO(fechaRelativa(20)),
    estado: 'ACTIVA',
  },
  {
    id_membresia: 2,
    id_socio: 2,
    id_tipo_membresia: 2,
    precio_pactado: 19500,
    fecha_inicio: aFechaISO(fechaSemilla(-2, 12)),
    fecha_vencimiento: aFechaISO(fechaRelativa(-38)),
    estado: 'CANCELADA',
  },
  {
    id_membresia: 3,
    id_socio: 3,
    id_tipo_membresia: 1,
    precio_pactado: 28000,
    fecha_inicio: aFechaISO(fechaRelativa(-27)),
    fecha_vencimiento: aFechaISO(fechaRelativa(3)),
    estado: 'ACTIVA',
  },
  {
    id_membresia: 4,
    id_socio: 4,
    id_tipo_membresia: 2,
    precio_pactado: 19500,
    fecha_inicio: aFechaISO(fechaRelativa(-35)),
    fecha_vencimiento: aFechaISO(fechaRelativa(-5)),
    estado: 'VENCIDA',
  },
  {
    id_membresia: 5,
    id_socio: 5,
    id_tipo_membresia: 3,
    precio_pactado: 75000,
    fecha_inicio: aFechaISO(fechaRelativa(-45)),
    fecha_vencimiento: aFechaISO(fechaRelativa(45)),
    estado: 'ACTIVA',
  },
  {
    id_membresia: 6,
    id_socio: 6,
    id_tipo_membresia: 1,
    precio_pactado: 28000,
    fecha_inicio: aFechaISO(fechaRelativa(-18)),
    fecha_vencimiento: aFechaISO(fechaRelativa(12)),
    estado: 'ACTIVA',
  },
  {
    id_membresia: 7,
    id_socio: 7,
    id_tipo_membresia: 1,
    precio_pactado: 28000,
    fecha_inicio: aFechaISO(fechaRelativa(-5)),
    fecha_vencimiento: aFechaISO(fechaRelativa(25)),
    estado: 'ACTIVA',
  },
  {
    id_membresia: 8,
    id_socio: 8,
    id_tipo_membresia: 2,
    precio_pactado: 19500,
    fecha_inicio: aFechaISO(fechaRelativa(-24)),
    fecha_vencimiento: aFechaISO(fechaRelativa(6)),
    estado: 'ACTIVA',
  },
  {
    id_membresia: 9,
    id_socio: 9,
    id_tipo_membresia: 3,
    precio_pactado: 75000,
    fecha_inicio: aFechaISO(fechaRelativa(-62)),
    fecha_vencimiento: aFechaISO(fechaRelativa(28)),
    estado: 'ACTIVA',
  },
  {
    id_membresia: 10,
    id_socio: 10,
    id_tipo_membresia: 1,
    precio_pactado: 28000,
    fecha_inicio: aFechaISO(fechaRelativa(-1)),
    fecha_vencimiento: aFechaISO(fechaRelativa(29)),
    estado: 'ACTIVA',
  },
];

// --- Pagos ---
//
// Mes corriente y mes anterior: hacen falta los dos para poder calcular la
// variación de ingresos sin inventar el número.

export const pagos: Pago[] = [
  // Mes anterior
  { id_pago: 1, id_socio: 1, id_membresia: 1, id_sede: 1, metodo: 'TRANSFERENCIA', monto: 21600, fecha_pago: aTimestampISO(fechaSemilla(-1, 3, 9)), es_adelanto: false, estado: 'CONFIRMADO', numero_comprobante: 'A-000101' },
  { id_pago: 2, id_socio: 3, id_membresia: 3, id_sede: 1, metodo: 'EFECTIVO', monto: 28000, fecha_pago: aTimestampISO(fechaSemilla(-1, 6, 18)), es_adelanto: false, estado: 'CONFIRMADO', numero_comprobante: 'A-000102' },
  { id_pago: 3, id_socio: 4, id_membresia: 4, id_sede: 1, metodo: 'DEBITO', monto: 19500, fecha_pago: aTimestampISO(fechaSemilla(-1, 9, 11)), es_adelanto: false, estado: 'CONFIRMADO', numero_comprobante: 'A-000103' },
  { id_pago: 4, id_socio: 5, id_membresia: 5, id_sede: 1, metodo: 'CREDITO', monto: 75000, fecha_pago: aTimestampISO(fechaSemilla(-1, 12, 16)), es_adelanto: false, estado: 'CONFIRMADO', numero_comprobante: 'A-000104' },
  { id_pago: 5, id_socio: 6, id_membresia: 6, id_sede: 1, metodo: 'BILLETERA_VIRTUAL', monto: 28000, fecha_pago: aTimestampISO(fechaSemilla(-1, 19, 20)), es_adelanto: false, estado: 'CONFIRMADO', numero_comprobante: 'A-000105' },
  { id_pago: 6, id_socio: 9, id_membresia: 9, id_sede: 1, metodo: 'TRANSFERENCIA', monto: 75000, fecha_pago: aTimestampISO(fechaSemilla(-1, 24, 10)), es_adelanto: false, estado: 'CONFIRMADO', numero_comprobante: 'A-000106' },
  // Mes corriente
  { id_pago: 7, id_socio: 7, id_membresia: 7, id_sede: 1, metodo: 'EFECTIVO', monto: 28000, fecha_pago: aTimestampISO(fechaSemilla(0, 2, 12)), es_adelanto: false, estado: 'CONFIRMADO', numero_comprobante: 'A-000107' },
  { id_pago: 8, id_socio: 8, id_membresia: 8, id_sede: 1, metodo: 'DEBITO', monto: 19500, fecha_pago: aTimestampISO(fechaSemilla(0, 5, 17)), es_adelanto: false, estado: 'CONFIRMADO', numero_comprobante: 'A-000108' },
  { id_pago: 9, id_socio: 6, id_membresia: 6, id_sede: 1, metodo: 'BILLETERA_VIRTUAL', monto: 28000, fecha_pago: aTimestampISO(fechaSemilla(0, 8, 9)), es_adelanto: false, estado: 'CONFIRMADO', numero_comprobante: 'A-000109' },
  { id_pago: 10, id_socio: 10, id_membresia: 10, id_sede: 1, metodo: 'TRANSFERENCIA', monto: 28000, fecha_pago: aTimestampISO(fechaSemilla(0, 9, 15)), es_adelanto: false, estado: 'CONFIRMADO', numero_comprobante: 'A-000110' },
  { id_pago: 11, id_socio: 1, id_membresia: 1, id_sede: 1, metodo: 'TRANSFERENCIA', monto: 21600, fecha_pago: aTimestampISO(fechaSemilla(0, 11, 8)), es_adelanto: true, estado: 'CONFIRMADO', numero_comprobante: 'A-000111' },
  { id_pago: 12, id_socio: 5, id_membresia: 5, id_sede: 1, metodo: 'CREDITO', monto: 37500, fecha_pago: aTimestampISO(fechaSemilla(0, 13, 19)), es_adelanto: false, estado: 'CONFIRMADO', numero_comprobante: 'A-000112' },
  { id_pago: 13, id_socio: 3, id_membresia: 3, id_sede: 1, metodo: 'EFECTIVO', monto: 28000, fecha_pago: aTimestampISO(fechaSemilla(0, 14, 11)), es_adelanto: false, estado: 'CONFIRMADO', numero_comprobante: 'A-000113' },
  // Pendiente y cancelado: no deben sumar a los ingresos del mes.
  { id_pago: 14, id_socio: 9, id_membresia: 9, id_sede: 1, metodo: 'TRANSFERENCIA', monto: 75000, fecha_pago: aTimestampISO(fechaSemilla(0, 15, 14)), es_adelanto: false, estado: 'PENDIENTE' },
  { id_pago: 15, id_socio: 4, id_membresia: 4, id_sede: 1, metodo: 'DEBITO', monto: 19500, fecha_pago: aTimestampISO(fechaSemilla(0, 16, 13)), es_adelanto: false, estado: 'CANCELADO', fecha_cancelacion: aTimestampISO(fechaSemilla(0, 16, 18)) },
];

// --- Turnos (clases) ---
//
// Hoy y ayer: el dashboard compara una cosa contra la otra.

export const turnos: Turno[] = [
  { id_turno: 1, id_sede: 1, fecha: aFechaISO(fechaRelativa(-1)), cupo_maximo: 20, estado: 'HABILITADO' },
  { id_turno: 2, id_sede: 1, fecha: aFechaISO(fechaRelativa(-1)), cupo_maximo: 20, estado: 'HABILITADO' },
  { id_turno: 3, id_sede: 1, fecha: aFechaISO(fechaRelativa(-1)), cupo_maximo: 15, estado: 'HABILITADO' },
  { id_turno: 4, id_sede: 1, fecha: aFechaISO(fechaRelativa(-1)), cupo_maximo: 15, estado: 'HABILITADO' },
  { id_turno: 5, id_sede: 1, fecha: aFechaISO(fechaRelativa(-1)), cupo_maximo: 25, estado: 'HABILITADO' },
  { id_turno: 6, id_sede: 1, fecha: aFechaISO(new Date()), cupo_maximo: 20, estado: 'HABILITADO' },
  { id_turno: 7, id_sede: 1, fecha: aFechaISO(new Date()), cupo_maximo: 20, estado: 'HABILITADO' },
  { id_turno: 8, id_sede: 1, fecha: aFechaISO(new Date()), cupo_maximo: 15, estado: 'HABILITADO' },
  { id_turno: 9, id_sede: 1, fecha: aFechaISO(new Date()), cupo_maximo: 15, estado: 'HABILITADO' },
  { id_turno: 10, id_sede: 1, fecha: aFechaISO(new Date()), cupo_maximo: 25, estado: 'HABILITADO' },
  { id_turno: 11, id_sede: 1, fecha: aFechaISO(new Date()), cupo_maximo: 20, estado: 'HABILITADO' },
  {
    id_turno: 12,
    id_sede: 1,
    fecha: aFechaISO(new Date()),
    cupo_maximo: 20,
    estado: 'CANCELADO',
    motivo_cancelacion: 'Mantenimiento de sala',
  },
];

// --- Rutinas ---
//
// id_entrenador referencia el array entrenadores de arriba (1: Sergio
// Bustos, 2: Paula Herrera, 3: Iván Rocha). La de Iván queda como caso de
// rutina creada por un entrenador que ya no está activo — el service no la
// oculta (existió, tiene historial), pero el selector de alta solo ofrece
// entrenadores activos.

export const rutinas: Rutina[] = [
  {
    id_rutina: 1,
    id_entrenador: 1,
    nombre: 'Fuerza Full Body',
    objetivo: 'Ganancia de fuerza general',
    nivel: 'Intermedio',
    dias_por_semana: 4,
    fecha_creacion: aFechaISO(fechaSemilla(-6, 1)),
    activo: true,
  },
  {
    id_rutina: 2,
    id_entrenador: 2,
    nombre: 'Funcional Metabólico',
    objetivo: 'Pérdida de grasa y resistencia',
    nivel: 'Principiante',
    dias_por_semana: 3,
    fecha_creacion: aFechaISO(fechaSemilla(-3, 10)),
    activo: true,
  },
  {
    id_rutina: 3,
    id_entrenador: 3,
    nombre: 'CrossFit Intro',
    objetivo: 'Adaptación a movimientos olímpicos',
    nivel: 'Principiante',
    dias_por_semana: 3,
    fecha_creacion: aFechaISO(fechaSemilla(-8, 15)),
    activo: true,
  },
  {
    id_rutina: 4,
    id_entrenador: 1,
    nombre: 'Hipertrofia Avanzada',
    objetivo: 'Ganancia de masa muscular',
    nivel: 'Avanzado',
    dias_por_semana: 5,
    fecha_creacion: aFechaISO(fechaSemilla(-1, 5)),
    activo: true,
  },
];

// Estados variados a propósito: FINALIZADA/CANCELADA no cuentan como
// "asignados" en la tarjeta (solo ACTIVA), así que hacen falta para
// verificar que el conteo no sea simplemente "cuántas filas hay".
export const asignacionesRutina: AsignacionRutina[] = [
  { id_asignacion_rutina: 1, id_socio: 1, id_rutina: 1, id_entrenador: 1, fecha_inicio: aFechaISO(fechaRelativa(-40)), estado: 'ACTIVA' },
  { id_asignacion_rutina: 2, id_socio: 3, id_rutina: 1, id_entrenador: 1, fecha_inicio: aFechaISO(fechaRelativa(-20)), estado: 'ACTIVA' },
  { id_asignacion_rutina: 3, id_socio: 5, id_rutina: 1, id_entrenador: 1, fecha_inicio: aFechaISO(fechaRelativa(-15)), estado: 'ACTIVA' },
  { id_asignacion_rutina: 4, id_socio: 6, id_rutina: 2, id_entrenador: 2, fecha_inicio: aFechaISO(fechaRelativa(-25)), estado: 'ACTIVA' },
  { id_asignacion_rutina: 5, id_socio: 7, id_rutina: 2, id_entrenador: 2, fecha_inicio: aFechaISO(fechaRelativa(-10)), estado: 'ACTIVA' },
  { id_asignacion_rutina: 6, id_socio: 8, id_rutina: 3, id_entrenador: 3, fecha_inicio: aFechaISO(fechaRelativa(-60)), fecha_fin: aFechaISO(fechaRelativa(-30)), estado: 'FINALIZADA' },
  { id_asignacion_rutina: 7, id_socio: 9, id_rutina: 4, id_entrenador: 1, fecha_inicio: aFechaISO(fechaRelativa(-4)), estado: 'ACTIVA' },
  { id_asignacion_rutina: 8, id_socio: 4, id_rutina: 2, id_entrenador: 2, fecha_inicio: aFechaISO(fechaRelativa(-18)), fecha_fin: aFechaISO(fechaRelativa(-2)), estado: 'CANCELADA' },
];

// --- Ejercicios y su carga dentro de cada rutina ---
//
// Catálogo global, independiente de las rutinas: grupo_muscular describe al
// ejercicio, no a la rutina que lo usa (3FN, según el comentario del
// esquema). El mismo "Sentadilla" aparece en varias rutinas sin duplicarse.

export const ejercicios: Ejercicio[] = [
  { id_ejercicio: 1, nombre: 'Sentadilla con barra', grupo_muscular: 'Piernas', requiere_maquina: false },
  { id_ejercicio: 2, nombre: 'Peso muerto', grupo_muscular: 'Espalda', requiere_maquina: false },
  { id_ejercicio: 3, nombre: 'Press de banca', grupo_muscular: 'Pecho', requiere_maquina: false },
  { id_ejercicio: 4, nombre: 'Dominadas', grupo_muscular: 'Espalda', requiere_maquina: false },
  { id_ejercicio: 5, nombre: 'Press militar', grupo_muscular: 'Hombros', requiere_maquina: false },
  { id_ejercicio: 6, nombre: 'Remo con barra', grupo_muscular: 'Espalda', requiere_maquina: false },
  { id_ejercicio: 7, nombre: 'Prensa de piernas', grupo_muscular: 'Piernas', requiere_maquina: true },
  { id_ejercicio: 8, nombre: 'Curl de bíceps con mancuernas', grupo_muscular: 'Brazos', requiere_maquina: false },
  { id_ejercicio: 9, nombre: 'Extensión de tríceps en polea', grupo_muscular: 'Brazos', requiere_maquina: true },
  { id_ejercicio: 10, nombre: 'Elevaciones laterales', grupo_muscular: 'Hombros', requiere_maquina: false },
  { id_ejercicio: 11, nombre: 'Plancha abdominal', grupo_muscular: 'Core', requiere_maquina: false },
  { id_ejercicio: 12, nombre: 'Zancadas con mancuernas', grupo_muscular: 'Piernas', requiere_maquina: false },
];

// Carga de la rutina 1 ("Fuerza Full Body", 4 días/semana) — la que tiene
// asignada el socio demo, así que es la que se ve en "Mi rutina".
//
// `repeticiones` es texto y no número a propósito (varchar(20) en el
// esquema): en la planilla de un gimnasio se escribe "10-12" o "al fallo",
// no siempre un entero. El orden dentro del día es el campo `orden`, no la
// posición en este array — el índice del esquema es (id_rutina, dia, orden).
export const rutinaEjercicios: RutinaEjercicio[] = [
  // Día 1 — Tren inferior
  { id_rutina_ejercicio: 1, id_rutina: 1, id_ejercicio: 1, dia: 1, orden: 1, series: 4, repeticiones: '8-10', peso_sugerido: 60, descanso_segundos: 120 },
  { id_rutina_ejercicio: 2, id_rutina: 1, id_ejercicio: 7, dia: 1, orden: 2, series: 3, repeticiones: '12', peso_sugerido: 120, descanso_segundos: 90 },
  { id_rutina_ejercicio: 3, id_rutina: 1, id_ejercicio: 12, dia: 1, orden: 3, series: 3, repeticiones: '10 por pierna', descanso_segundos: 60 },
  { id_rutina_ejercicio: 4, id_rutina: 1, id_ejercicio: 11, dia: 1, orden: 4, series: 3, repeticiones: '45 seg', descanso_segundos: 45, observaciones: 'Mantené la cadera alineada' },
  // Día 2 — Empuje
  { id_rutina_ejercicio: 5, id_rutina: 1, id_ejercicio: 3, dia: 2, orden: 1, series: 4, repeticiones: '8', peso_sugerido: 50, descanso_segundos: 120 },
  { id_rutina_ejercicio: 6, id_rutina: 1, id_ejercicio: 5, dia: 2, orden: 2, series: 3, repeticiones: '10', peso_sugerido: 30, descanso_segundos: 90 },
  { id_rutina_ejercicio: 7, id_rutina: 1, id_ejercicio: 10, dia: 2, orden: 3, series: 3, repeticiones: '12-15', peso_sugerido: 8, descanso_segundos: 60 },
  { id_rutina_ejercicio: 8, id_rutina: 1, id_ejercicio: 9, dia: 2, orden: 4, series: 3, repeticiones: '12', descanso_segundos: 60 },
  // Día 3 — Tracción
  { id_rutina_ejercicio: 9, id_rutina: 1, id_ejercicio: 2, dia: 3, orden: 1, series: 4, repeticiones: '6', peso_sugerido: 80, descanso_segundos: 150, observaciones: 'Espalda recta, no redondear' },
  { id_rutina_ejercicio: 10, id_rutina: 1, id_ejercicio: 4, dia: 3, orden: 2, series: 4, repeticiones: 'al fallo', descanso_segundos: 120 },
  { id_rutina_ejercicio: 11, id_rutina: 1, id_ejercicio: 6, dia: 3, orden: 3, series: 3, repeticiones: '10', peso_sugerido: 40, descanso_segundos: 90 },
  { id_rutina_ejercicio: 12, id_rutina: 1, id_ejercicio: 8, dia: 3, orden: 4, series: 3, repeticiones: '12', peso_sugerido: 10, descanso_segundos: 60 },
  // Día 4 — Full body liviano
  { id_rutina_ejercicio: 13, id_rutina: 1, id_ejercicio: 1, dia: 4, orden: 1, series: 3, repeticiones: '12', peso_sugerido: 40, descanso_segundos: 90 },
  { id_rutina_ejercicio: 14, id_rutina: 1, id_ejercicio: 3, dia: 4, orden: 2, series: 3, repeticiones: '12', peso_sugerido: 35, descanso_segundos: 90 },
  { id_rutina_ejercicio: 15, id_rutina: 1, id_ejercicio: 6, dia: 4, orden: 3, series: 3, repeticiones: '12', peso_sugerido: 30, descanso_segundos: 90 },
  { id_rutina_ejercicio: 16, id_rutina: 1, id_ejercicio: 11, dia: 4, orden: 4, series: 3, repeticiones: '60 seg', descanso_segundos: 45 },
];

// --- Planes de nutrición ---
//
// id_nutricionista referencia el array nutricionistas de arriba — hoy solo
// hay una (Mariana Lopresti, id 1), así que los cuatro planes son suyos.
// Es un dato real, no un límite artificial: cuando se sume otro
// nutricionista, el selector de alta ya los va a listar a los dos.

export const dietas: Dieta[] = [
  {
    id_dieta: 1,
    id_nutricionista: 1,
    nombre: 'Volumen Limpio',
    objetivo: 'Masa muscular',
    calorias_diarias: 2800,
    descripcion: 'Superávit calórico moderado con foco en proteína magra y carbohidratos complejos.',
    fecha_creacion: aFechaISO(fechaSemilla(-5, 3)),
    activo: true,
  },
  {
    id_dieta: 2,
    id_nutricionista: 1,
    nombre: 'Déficit Controlado',
    objetivo: 'Bajar peso',
    calorias_diarias: 1600,
    descripcion: 'Déficit moderado, alto en fibra y saciedad, sin restringir ningún grupo de alimentos.',
    fecha_creacion: aFechaISO(fechaSemilla(-3, 12)),
    activo: true,
  },
  {
    id_dieta: 3,
    id_nutricionista: 1,
    nombre: 'Mantenimiento Estándar',
    objetivo: 'Mantenimiento',
    calorias_diarias: 2200,
    descripcion: 'Plan equilibrado para sostener el peso actual junto con la actividad del gimnasio.',
    fecha_creacion: aFechaISO(fechaSemilla(-8, 20)),
    activo: true,
  },
  {
    id_dieta: 4,
    id_nutricionista: 1,
    nombre: 'Rendimiento Competitivo',
    objetivo: 'Alto rendimiento',
    calorias_diarias: 3200,
    descripcion: 'Alto aporte energético para deportistas con doble turno de entrenamiento.',
    fecha_creacion: aFechaISO(fechaSemilla(-1, 8)),
    activo: true,
  },
];

// Comidas de ejemplo, cargadas solo para dos de los cuatro planes — no hay
// todavía un editor de comidas (estructura_nutricion.md tampoco lo tiene),
// así que el resto de los planes queda sin comidas hasta que exista esa
// spec, mostrando el estado vacío real en vez de datos inventados.
export const comidas: Comida[] = [
  { id_comida: 1, id_dieta: 1, dia: 1, momento: 'Desayuno', descripcion: 'Avena con banana y whey protein', calorias: 520 },
  { id_comida: 2, id_dieta: 1, dia: 1, momento: 'Almuerzo', descripcion: 'Pollo a la plancha, arroz integral y ensalada', calorias: 780 },
  { id_comida: 3, id_dieta: 1, dia: 1, momento: 'Merienda', descripcion: 'Yogur griego con frutos secos', calorias: 350 },
  { id_comida: 4, id_dieta: 1, dia: 1, momento: 'Cena', descripcion: 'Salmón, batata asada y brócoli', calorias: 690 },
  { id_comida: 5, id_dieta: 1, dia: 2, momento: 'Desayuno', descripcion: 'Tostadas integrales con palta y huevo', calorias: 490 },
  { id_comida: 6, id_dieta: 1, dia: 2, momento: 'Almuerzo', descripcion: 'Carne magra, puré de calabaza y ensalada', calorias: 810 },
  { id_comida: 7, id_dieta: 2, dia: 1, momento: 'Desayuno', descripcion: 'Yogur descremado con avena y frutos rojos', calorias: 310 },
  { id_comida: 8, id_dieta: 2, dia: 1, momento: 'Almuerzo', descripcion: 'Pechuga de pollo, vegetales al vapor', calorias: 450 },
  { id_comida: 9, id_dieta: 2, dia: 1, momento: 'Merienda', descripcion: 'Fruta fresca de estación', calorias: 120 },
  { id_comida: 10, id_dieta: 2, dia: 1, momento: 'Cena', descripcion: 'Merluza al horno con ensalada verde', calorias: 380 },
];

// Estados variados a propósito, mismo criterio que asignacionesRutina:
// FINALIZADA/CANCELADA no cuentan como "asignados" en la tarjeta.
export const asignacionesDieta: AsignacionDieta[] = [
  // Con observaciones cargadas: es el campo propio de la ASIGNACIÓN (las
  // indicaciones para ESE socio), distinto de Dieta.descripcion, y sin un
  // caso con dato no se vería que la vista los distingue.
  { id_asignacion_dieta: 1, id_socio: 1, id_dieta: 1, id_nutricionista: 1, fecha_inicio: aFechaISO(fechaRelativa(-30)), estado: 'ACTIVA', observaciones: 'Evitar lácteos por intolerancia. Tomar el batido apenas terminás de entrenar.' },
  { id_asignacion_dieta: 2, id_socio: 9, id_dieta: 1, id_nutricionista: 1, fecha_inicio: aFechaISO(fechaRelativa(-12)), estado: 'ACTIVA' },
  { id_asignacion_dieta: 3, id_socio: 4, id_dieta: 2, id_nutricionista: 1, fecha_inicio: aFechaISO(fechaRelativa(-22)), estado: 'ACTIVA' },
  { id_asignacion_dieta: 4, id_socio: 6, id_dieta: 2, id_nutricionista: 1, fecha_inicio: aFechaISO(fechaRelativa(-6)), estado: 'ACTIVA' },
  { id_asignacion_dieta: 5, id_socio: 7, id_dieta: 2, id_nutricionista: 1, fecha_inicio: aFechaISO(fechaRelativa(-5)), estado: 'ACTIVA' },
  { id_asignacion_dieta: 6, id_socio: 5, id_dieta: 3, id_nutricionista: 1, fecha_inicio: aFechaISO(fechaRelativa(-50)), fecha_fin: aFechaISO(fechaRelativa(-15)), estado: 'FINALIZADA' },
  { id_asignacion_dieta: 7, id_socio: 3, id_dieta: 4, id_nutricionista: 1, fecha_inicio: aFechaISO(fechaRelativa(-3)), estado: 'ACTIVA' },
];

// --- Deudas ---
//
// En el sistema real las genera un job diario que busca membresías vencidas
// sin pago que las cubra (ver el comentario de la tabla en schema.sql); acá
// vienen del seed.
//
// La del socio demo es coherente con el resto de sus datos, no un dato
// suelto para que la pantalla tenga algo: su plan es el Pase Libre Anual de
// $260.000 y sus pagos son de $21.600 (una cuota mensual del anual), así que
// tiene sentido que le figure una cuota impaga de ese mismo monto. La
// membresía sigue ACTIVA —vence más adelante— y eso NO es contradictorio:
// deber una cuota y tener la membresía vigente son dos cosas distintas, que
// es justamente por lo que Deuda es una tabla aparte de Membresia.

export const deudas: Deuda[] = [
  {
    id_deuda: 1,
    id_socio: 1,
    id_membresia: 1,
    monto: 21600,
    fecha_generacion: aFechaISO(fechaRelativa(-38)),
    fecha_vencimiento: aFechaISO(fechaRelativa(-8)),
    estado: 'PENDIENTE',
    generada_automaticamente: true,
    observaciones: 'Cuota mensual del plan anual',
  },
];

// --- Registros de salud (peso / composición corporal) ---
//
// Historial del socio demo a lo largo de ~3 meses. Es 1:N con unique
// (id_socio, fecha): una medición por día, pero se conserva toda la
// progresión — "peso actual" no es una columna, es la fila de fecha más
// alta (así lo documenta el esquema).
//
// La progresión es a la baja y con un rebote en el medio a propósito: una
// curva perfectamente descendente haría que cualquier bug de orden pase
// desapercibido, y además no se parece a ningún proceso real.

export const registrosSalud: RegistroSalud[] = [
  { id_registro_salud: 1, id_socio: 1, fecha: aFechaISO(fechaRelativa(-90)), peso: 86.4, altura: 1.78, grasa_corporal: 24.1, masa_muscular: 62.1 },
  { id_registro_salud: 2, id_socio: 1, fecha: aFechaISO(fechaRelativa(-75)), peso: 85.1, altura: 1.78, grasa_corporal: 23.4, masa_muscular: 62.4 },
  { id_registro_salud: 3, id_socio: 1, fecha: aFechaISO(fechaRelativa(-60)), peso: 84.7, altura: 1.78, grasa_corporal: 22.8, masa_muscular: 63 },
  { id_registro_salud: 4, id_socio: 1, fecha: aFechaISO(fechaRelativa(-45)), peso: 85.3, altura: 1.78, grasa_corporal: 22.9, masa_muscular: 63.2, observaciones: 'Semana de vacaciones' },
  { id_registro_salud: 5, id_socio: 1, fecha: aFechaISO(fechaRelativa(-30)), peso: 83.6, altura: 1.78, grasa_corporal: 21.7, masa_muscular: 64 },
  { id_registro_salud: 6, id_socio: 1, fecha: aFechaISO(fechaRelativa(-15)), peso: 82.4, altura: 1.78, grasa_corporal: 20.9, masa_muscular: 64.6 },
  { id_registro_salud: 7, id_socio: 1, fecha: aFechaISO(fechaRelativa(-4)), peso: 81.8, altura: 1.78, grasa_corporal: 20.3, masa_muscular: 65.1 },
];

// --- Auditoría ---

export const auditoria: Auditoria[] = [];

// --- Generación de IDs ---

/**
 * Imita una secuencia de Postgres: arranca en el mayor id ya usado y sube de
 * a uno, sin volver a mirar el array. Usar `array.length + 1` sería un bug
 * latente — apenas se filtre o se saque un elemento, la longitud deja de
 * coincidir con el último id y se repiten claves primarias.
 */
export function crearSecuencia(idsExistentes: number[]): () => number {
  let ultimo = idsExistentes.length > 0 ? Math.max(...idsExistentes) : 0;
  return () => {
    ultimo += 1;
    return ultimo;
  };
}

export const siguienteId = {
  persona: crearSecuencia(personas.map((p) => p.id_persona)),
  usuario: crearSecuencia(usuarios.map((u) => u.id_usuario)),
  telefono: crearSecuencia(telefonos.map((t) => t.id_telefono)),
  socio: crearSecuencia(socios.map((s) => s.id_socio)),
  baja: crearSecuencia(bajas.map((b) => b.id_baja)),
  auditoria: crearSecuencia(auditoria.map((a) => a.id_auditoria)),
  membresia: crearSecuencia(membresias.map((m) => m.id_membresia)),
  pago: crearSecuencia(pagos.map((p) => p.id_pago)),
  empleado: crearSecuencia(empleados.map((e) => e.id_empleado)),
  entrenador: crearSecuencia(entrenadores.map((e) => e.id_entrenador)),
  nutricionista: crearSecuencia(nutricionistas.map((n) => n.id_nutricionista)),
  recepcionista: crearSecuencia(recepcionistas.map((r) => r.id_recepcionista)),
  rutina: crearSecuencia(rutinas.map((r) => r.id_rutina)),
  dieta: crearSecuencia(dietas.map((d) => d.id_dieta)),
  registroSalud: crearSecuencia(registrosSalud.map((r) => r.id_registro_salud)),
};

/** Número de socio correlativo, con el mismo formato que la semilla. */
export function proximoNumeroSocio(idSocio: number): string {
  return `S-${String(idSocio).padStart(4, '0')}`;
}

/** Legajo de empleado correlativo, con el mismo formato que la semilla. */
export function proximoLegajo(idEmpleado: number): string {
  return `E-${String(idEmpleado).padStart(4, '0')}`;
}
