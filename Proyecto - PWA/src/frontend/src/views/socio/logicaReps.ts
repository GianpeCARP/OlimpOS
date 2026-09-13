// =============================================================================
// LÓGICA DEL CONTADOR DE REPETICIONES — pura, sin React ni cámara
// =============================================================================
// Separada del componente por lo mismo que useCircuito: acá se puede razonar
// "en qué fase estoy, cuándo cuenta una rep" sin JSX en el medio.
//
// La idea: cada movimiento se define por UN ángulo de articulación (tres
// landmarks) y dos umbrales con HISTÉRESIS. La rep se cuenta al completar el
// ciclo flexionar→extender. La histéresis (flex < ext, con hueco) evita que un
// temblor cruce el umbral de ida y vuelta y cuente de más.

/** Un punto 3D de MediaPipe (worldLandmarks: metros, origen en la cadera). */
export interface Punto3D {
  x: number;
  y: number;
  z: number;
}

/** Landmark 2D con visibilidad (0-1): lo usamos para elegir el lado mejor visto. */
export interface Punto2D {
  visibility?: number;
}

export type Fase = 'ext' | 'flex';

export interface Movimiento {
  clave: string;
  nombre: string;
  // Índices [extremo, VÉRTICE, extremo] del ángulo, por lado del cuerpo.
  // (MediaPipe Pose, 33 puntos: hombro 11/12, codo 13/14, muñeca 15/16,
  //  cadera 23/24, rodilla 25/26, tobillo 27/28.)
  izq: [number, number, number];
  der: [number, number, number];
  /** Por debajo de este ángulo se considera FLEXIONADO. */
  flex: number;
  /** Por encima de este ángulo, EXTENDIDO. La rep cuenta al volver acá. */
  ext: number;
  /** Cómo pararse para que la cámara lo mida bien. */
  pista: string;
}

// Empezamos con dos, para probar el mecanismo. Después se mapean los ejercicios
// del catálogo a uno de estos.
export const MOVIMIENTOS: Movimiento[] = [
  {
    clave: 'sentadilla',
    nombre: 'Sentadilla',
    izq: [23, 25, 27],
    der: [24, 26, 28],
    // Más exigente que antes: la rodilla tiene que bajar de 95° (bajada casi
    // completa, muslo cerca del paralelo) para contar, no un medio recorrido.
    // No hace falta llegar al piso; con volver arriba de 160° cierra la rep.
    flex: 95,
    ext: 160,
    pista: 'Cámara DE PERFIL y que entre el cuerpo COMPLETO, de la cabeza a los pies.',
  },
  {
    clave: 'curl',
    nombre: 'Curl de bíceps',
    izq: [11, 13, 15],
    der: [12, 14, 16],
    flex: 70,
    ext: 150,
    pista: 'Cámara DE FRENTE, que se vea el brazo entero.',
  },
  // --- Más movimientos (ángulo de codo o rodilla). Umbrales de arranque:
  // se afinan probando, igual que la sentadilla. ---
  {
    clave: 'press_militar',
    nombre: 'Press militar',
    izq: [11, 13, 15],
    der: [12, 14, 16],
    flex: 90,
    ext: 155,
    pista: 'De frente o de perfil, parado, que se vean hombros y brazos.',
  },
  {
    clave: 'press_banca',
    nombre: 'Press de banca',
    izq: [11, 13, 15],
    der: [12, 14, 16],
    flex: 95,
    ext: 155,
    pista: 'DE PERFIL al banco, que se vean hombro, codo y muñeca.',
  },
  {
    clave: 'dominadas',
    nombre: 'Dominadas',
    izq: [11, 13, 15],
    der: [12, 14, 16],
    flex: 90,
    ext: 150,
    pista: 'De frente o de perfil, que se vea el brazo entero de arriba a abajo.',
  },
  {
    clave: 'fondos',
    nombre: 'Fondos',
    izq: [11, 13, 15],
    der: [12, 14, 16],
    flex: 100,
    ext: 155,
    pista: 'DE PERFIL, que se vean hombro, codo y muñeca.',
  },
  {
    clave: 'prensa',
    nombre: 'Prensa de piernas',
    izq: [23, 25, 27],
    der: [24, 26, 28],
    flex: 95,
    ext: 155,
    pista: 'De costado, que se vean cadera, rodilla y tobillo.',
  },
  {
    clave: 'flexiones',
    nombre: 'Flexiones',
    izq: [11, 13, 15],
    der: [12, 14, 16],
    flex: 100,
    ext: 155,
    pista: 'DE PERFIL y a ras del piso: que se vean hombro, codo y muñeca.',
  },
  {
    clave: 'jalon',
    nombre: 'Jalón al pecho',
    izq: [11, 13, 15],
    der: [12, 14, 16],
    flex: 90,
    ext: 150,
    pista: 'De frente, que se vean los brazos completos.',
  },
  {
    clave: 'remo',
    nombre: 'Remo',
    izq: [11, 13, 15],
    der: [12, 14, 16],
    flex: 90,
    ext: 150,
    pista: 'DE PERFIL, que se vean hombro, codo y muñeca. (Sensible a la forma.)',
  },
  {
    clave: 'triceps',
    nombre: 'Extensión de tríceps',
    izq: [11, 13, 15],
    der: [12, 14, 16],
    flex: 100,
    ext: 155,
    pista: 'De frente o de perfil, que se vea el brazo entero.',
  },
  {
    clave: 'extension_piernas',
    nombre: 'Extensión de piernas',
    izq: [23, 25, 27],
    der: [24, 26, 28],
    flex: 100,
    ext: 160,
    pista: 'De costado, sentado, que se vean cadera, rodilla y tobillo.',
  },
  // --- Ángulo de CADERA (hombro-cadera-rodilla) ---
  {
    clave: 'peso_muerto',
    nombre: 'Peso muerto',
    izq: [11, 23, 25],
    der: [12, 24, 26],
    flex: 120,
    ext: 160,
    pista: 'DE PERFIL y cuerpo completo. (Bisagra de cadera, sensible a la forma.)',
  },
  {
    clave: 'hip_thrust',
    nombre: 'Hip thrust',
    izq: [11, 23, 25],
    der: [12, 24, 26],
    flex: 125,
    ext: 160,
    pista: 'DE PERFIL, que se vean hombro, cadera y rodilla.',
  },
  // --- Ángulo de HOMBRO (cadera-hombro-muñeca): brazo abajo ≈ 10°, a la altura
  // del hombro ≈ 90°. Acá el "arriba" es el ángulo GRANDE, al revés que un curl. ---
  {
    clave: 'lateral',
    nombre: 'Elevaciones laterales',
    izq: [23, 11, 15],
    der: [24, 12, 16],
    flex: 30,
    ext: 70,
    pista: 'De frente, que se vean los dos brazos de punta a punta.',
  },
];

/**
 * Mapea un ejercicio del catálogo (por nombre) a un movimiento soportado por el
 * contador, o null si todavía no lo soportamos. Devolver null es a propósito:
 * mejor no ofrecer la cámara para un ejercicio que no sabemos contar bien que
 * contar cualquier cosa. Se irá ampliando a medida que agreguemos movimientos.
 */
export function movimientoDeEjercicio(nombre: string): Movimiento | null {
  const n = (nombre || '').toLowerCase();
  const por = (clave: string) => MOVIMIENTOS.find((m) => m.clave === clave) ?? null;
  // Orden: palabras más específicas primero. Varios nombres comparten palabras
  // ("press de banca"/"press militar"; "peso muerto"/"peso muerto rumano"), así
  // que se chequea por la palabra distintiva.
  if (n.includes('sentadilla')) return por('sentadilla');
  if (n.includes('prensa')) return por('prensa');
  if (n.includes('hip thrust') || n.includes('empuje de cadera') || n.includes('puente de gl')) return por('hip_thrust');
  // Peso muerto (incluye el rumano) → bisagra de cadera.
  if (n.includes('peso muerto') || n.includes('rumano')) return por('peso_muerto');
  if (n.includes('jal') || n.includes('pulldown') || n.includes('polea al pecho')) return por('jalon');
  if (n.includes('remo')) return por('remo');
  if (n.includes('dominada') || n.includes('pull')) return por('dominadas');
  if (n.includes('fondo')) return por('fondos');
  if (n.includes('lateral')) return por('lateral');
  if (n.includes('tr') && (n.includes('ceps') || n.includes('pushdown'))) return por('triceps');
  // Curl de bíceps, pero NO el "curl femoral"/de piernas (ése es de rodilla y
  // todavía no lo soportamos: mejor no ofrecerlo que contarlo como bíceps).
  if (n.includes('curl') && !n.includes('femoral') && !n.includes('pierna')) return por('curl');
  if (n.includes('extensi') && n.includes('pierna')) return por('extension_piernas');
  if (n.includes('flexion') || n.includes('lagartija')) return por('flexiones');
  if (n.includes('banca') || n.includes('inclinad') || n.includes('incline')) return por('press_banca');
  if (n.includes('militar') || n.includes('hombro') || n.includes('overhead')) return por('press_militar');
  // NO contamos (todavía o por naturaleza): aperturas (fly), plancha
  // (isométrico), cinta/cardio, y cualquier cosa no reconocida.
  return null;
}

/** Ángulo (en grados) en el vértice `b`, formado por `a`-`b`-`c`, en 3D. */
export function anguloEntre(a: Punto3D, b: Punto3D, c: Punto3D): number {
  const abx = a.x - b.x, aby = a.y - b.y, abz = a.z - b.z;
  const cbx = c.x - b.x, cby = c.y - b.y, cbz = c.z - b.z;
  const dot = abx * cbx + aby * cby + abz * cbz;
  const mag = Math.hypot(abx, aby, abz) * Math.hypot(cbx, cby, cbz);
  if (mag === 0) return 180;
  const cos = Math.min(1, Math.max(-1, dot / mag));
  return (Math.acos(cos) * 180) / Math.PI;
}

function visMin(l2d: Punto2D[], idx: [number, number, number]): number {
  return Math.min(...idx.map((i) => l2d[i]?.visibility ?? 1));
}

/**
 * Ángulo del movimiento eligiendo el lado del cuerpo MEJOR VISTO. Devuelve null
 * si ni el mejor lado se ve con confianza suficiente (ocluido, fuera de cuadro):
 * ahí no conviene contar nada.
 */
export function anguloMovimiento(
  world: Punto3D[],
  l2d: Punto2D[],
  m: Movimiento,
): number | null {
  const visL = visMin(l2d, m.izq);
  const visR = visMin(l2d, m.der);
  // Compuerta de confianza: si ni el lado mejor visto llega a 0.6, no medimos
  // (cuerpo ocluido, fuera de cuadro, contraluz). Mejor no contar que contar mal.
  if (Math.max(visL, visR) < 0.6) return null;
  const lado = visR >= visL ? m.der : m.izq;
  return anguloEntre(world[lado[0]], world[lado[1]], world[lado[2]]);
}

/**
 * Un paso de la máquina de estados. Recibe la fase actual y el ángulo (ya
 * suavizado) y devuelve la fase nueva y si se completó una repetición.
 */
export function pasoRep(
  fase: Fase,
  angulo: number,
  m: Movimiento,
): { fase: Fase; conto: boolean } {
  if (fase === 'ext' && angulo < m.flex) return { fase: 'flex', conto: false };
  if (fase === 'flex' && angulo > m.ext) return { fase: 'ext', conto: true };
  return { fase, conto: false };
}

// =============================================================================
// FILTRO ONE-EURO — suaviza el ángulo SIN meter retardo notable
// =============================================================================
// Un promedio exponencial fijo obliga a elegir entre temblor (poco suavizado) y
// retardo (mucho). El One-Euro es adaptativo: cuando el ángulo casi no se mueve
// suaviza fuerte (saca el jitter de los picos y valles, donde se cuentan las
// reps), y cuando el movimiento es rápido baja el suavizado (no llega tarde al
// umbral). Es el estándar para señales de interacción en tiempo real.
//
//   alpha(cutoff, dt) = 1 / (1 + tau/dt),  tau = 1/(2*pi*cutoff)

export interface FiltroUnEuro {
  /** `tMs` = timestamp en ms (performance.now()). */
  filtrar(valor: number, tMs: number): number;
  reiniciar(): void;
}

export function crearFiltroUnEuro(
  { minCutoff = 1.5, beta = 0.03, dCutoff = 1.0 }: {
    minCutoff?: number;
    beta?: number;
    dCutoff?: number;
  } = {},
): FiltroUnEuro {
  let xPrev: number | null = null;
  let dxPrev = 0;
  let tPrev = 0;
  const alpha = (cutoff: number, dt: number) => {
    const tau = 1 / (2 * Math.PI * cutoff);
    return 1 / (1 + tau / dt);
  };
  return {
    filtrar(x, tMs) {
      if (xPrev === null) {
        xPrev = x;
        tPrev = tMs;
        return x;
      }
      let dt = (tMs - tPrev) / 1000;
      if (!(dt > 0)) dt = 1 / 30; // si el reloj no avanzó, asumimos ~30fps
      tPrev = tMs;
      const dx = (x - xPrev) / dt;
      const aD = alpha(dCutoff, dt);
      const edx = aD * dx + (1 - aD) * dxPrev;
      dxPrev = edx;
      const cutoff = minCutoff + beta * Math.abs(edx);
      const aX = alpha(cutoff, dt);
      const xHat = aX * x + (1 - aX) * xPrev;
      xPrev = xHat;
      return xHat;
    },
    reiniciar() {
      xPrev = null;
      dxPrev = 0;
      tPrev = 0;
    },
  };
}
