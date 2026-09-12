import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { DiaDeRutina, EjercicioDelDia } from '../../services/socioService';

// La máquina de estados del circuito, separada de la pantalla.
//
// Vive aparte de CircuitoView por una razón concreta y no por prolijidad: la
// lógica de "en qué serie voy, cuándo arranca el descanso, qué pasa si vuelvo
// después de bloquear el teléfono" se puede leer y razonar entera sin tener
// JSX en el medio. Y al revés: la pantalla queda siendo sólo cómo se ve.
//
// TODO ESTO ES DEL LADO DEL CLIENTE. No toca el backend, y es deliberado: un
// cronómetro que necesita servidor es un cronómetro que falla cuando el wifi
// del gimnasio anda mal, que es exactamente cuando se está usando. Los datos
// que necesita —series, repeticiones, descanso— ya vienen en la rutina que el
// entrenador cargó.

export type Fase = 'ejercicio' | 'descanso' | 'terminado';

/** Cuánto descansar cuando el entrenador no lo especificó. */
const DESCANSO_POR_DEFECTO = 60;

/** Series a asumir cuando el ejercicio no las trae cargadas. */
const SERIES_POR_DEFECTO = 1;

// Se guarda el progreso acá para que cerrar la app o atender un mensaje no lo
// pierda. Es lo mínimo que hace falta para reconstruir dónde estaba: el resto
// se deriva de la rutina, que se vuelve a pedir igual.
const CLAVE_GUARDADO = 'olimpos.circuito';

interface Guardado {
  idRutina: number;
  dia: number;
  indice: number;
  serie: number;
  completadas: number[];
  /** Marca de tiempo, para no restaurar un circuito de anteayer. */
  guardadoEn: number;
}

/** Después de esto, un circuito a medias se descarta en vez de retomarse. */
const VENCE_GUARDADO_MS = 6 * 60 * 60 * 1000;   // 6 horas

function seriesDe(ejercicio: EjercicioDelDia): number {
  return Math.max(1, ejercicio.series ?? SERIES_POR_DEFECTO);
}

function descansoDe(ejercicio: EjercicioDelDia): number {
  return Math.max(0, ejercicio.descansoSegundos ?? DESCANSO_POR_DEFECTO);
}

interface Opciones {
  dia: DiaDeRutina;
  idRutina: number;
  /** Se llama al terminar el último ejercicio o al salir. */
  onSalir: () => void;
}

export function useCircuito({ dia, idRutina, onSalir }: Opciones) {
  const ejercicios = dia.ejercicios;

  const [indice, setIndice] = useState(0);
  const [serie, setSerie] = useState(1);
  const [fase, setFase] = useState<Fase>('ejercicio');
  // Índices de los ejercicios ya terminados. Se guarda cuáles y no cuántos
  // porque se puede saltear uno y volver después: con un contador, el
  // progreso mentiría en cuanto alguien altere el orden.
  const [completadas, setCompletadas] = useState<number[]>([]);

  // --- El descanso ---------------------------------------------------------
  // Se guarda CUÁNDO TERMINA, no cuántos segundos faltan. Con un contador que
  // se decrementa, el reloj se atrasa: el navegador ralentiza los timers de
  // una pestaña en segundo plano, así que bloquear el teléfono 30 segundos
  // durante el descanso dejaba el número congelado. Con una marca de tiempo,
  // al volver ya está donde tiene que estar.
  const [finDescanso, setFinDescanso] = useState<number | null>(null);
  const [restante, setRestante] = useState(0);
  const [pausado, setPausado] = useState(false);
  // Cuando se pausa se guarda lo que faltaba, para poder reanudar desde ahí.
  const restanteAlPausar = useRef(0);

  const ejercicio = ejercicios[indice];
  const totalSeries = ejercicio ? seriesDe(ejercicio) : 0;

  // --- Persistencia --------------------------------------------------------
  useEffect(() => {
    try {
      const crudo = localStorage.getItem(CLAVE_GUARDADO);
      if (!crudo) return;
      const g = JSON.parse(crudo) as Guardado;
      // Sólo se retoma si es la MISMA rutina y el MISMO día. Retomar el
      // progreso de otro día pondría al socio en el ejercicio 4 de una lista
      // que no es la que está mirando.
      if (g.idRutina !== idRutina || g.dia !== dia.dia) return;
      if (Date.now() - g.guardadoEn > VENCE_GUARDADO_MS) return;
      if (g.indice >= ejercicios.length) return;
      setIndice(g.indice);
      setSerie(g.serie);
      setCompletadas(g.completadas ?? []);
    } catch {
      // localStorage puede fallar (modo privado, cuota llena) y un circuito
      // que no arranca por no poder LEER un progreso viejo sería absurdo.
    }
    // Sólo al montar: retomar en medio del circuito lo reiniciaría.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (fase === 'terminado') return;
    try {
      const g: Guardado = {
        idRutina, dia: dia.dia, indice, serie, completadas,
        guardadoEn: Date.now(),
      };
      localStorage.setItem(CLAVE_GUARDADO, JSON.stringify(g));
    } catch {
      // Ver arriba: sin guardado el circuito funciona igual, sólo que no
      // sobrevive a que se cierre la app.
    }
  }, [idRutina, dia.dia, indice, serie, completadas, fase]);

  const olvidarProgreso = useCallback(() => {
    try {
      localStorage.removeItem(CLAVE_GUARDADO);
    } catch {
      /* ídem */
    }
  }, []);

  // --- El reloj del descanso ----------------------------------------------
  useEffect(() => {
    if (fase !== 'descanso' || finDescanso === null || pausado) return;

    const tick = () => {
      const faltan = Math.max(0, Math.ceil((finDescanso - Date.now()) / 1000));
      setRestante(faltan);
      if (faltan === 0) {
        // Vibrar y no sonar: en un gimnasio con música un beep no se escucha,
        // y el teléfono suele estar en el bolsillo. `vibrate` no existe en
        // iOS, así que se consulta antes en vez de asumir.
        if (typeof navigator.vibrate === 'function') navigator.vibrate([200, 100, 200]);
        setFase('ejercicio');
        setFinDescanso(null);
      }
    };

    tick();
    const id = setInterval(tick, 250);   // 250ms: el número nunca "salta"
    return () => clearInterval(id);
  }, [fase, finDescanso, pausado]);

  // --- Acciones ------------------------------------------------------------

  const avanzarEjercicio = useCallback(() => {
    setCompletadas((previas) =>
      previas.includes(indice) ? previas : [...previas, indice],
    );
    // El siguiente SIN completar. Así, quien salteó el 3 porque la máquina
    // estaba ocupada vuelve a él al final en vez de perderlo.
    const siguiente = ejercicios.findIndex(
      (_, i) => i > indice && !completadas.includes(i),
    );
    const pendiente = siguiente !== -1
      ? siguiente
      : ejercicios.findIndex((_, i) => i !== indice && !completadas.includes(i));

    if (pendiente === -1) {
      setFase('terminado');
      olvidarProgreso();
      return;
    }
    setIndice(pendiente);
    setSerie(1);
    setFase('ejercicio');
    setFinDescanso(null);
  }, [indice, ejercicios, completadas, olvidarProgreso]);

  /**
   * El botón grande. Cierra la serie y arranca el descanso SOLO.
   *
   * Que el descanso empiece sin pedir permiso es la decisión de diseño más
   * importante de la pantalla: entre serie y serie el socio tiene las manos
   * ocupadas y el pulso a 150. Cada toque de más es uno que no va a dar.
   */
  const completarSerie = useCallback(() => {
    if (!ejercicio) return;

    const esUltima = serie >= totalSeries;
    if (esUltima) {
      avanzarEjercicio();
      return;
    }

    setSerie((s) => s + 1);
    const descanso = descansoDe(ejercicio);
    if (descanso === 0) return;          // sin descanso cargado, sigue de una
    setFase('descanso');
    setPausado(false);
    setFinDescanso(Date.now() + descanso * 1000);
  }, [ejercicio, serie, totalSeries, avanzarEjercicio]);

  /** Saltar el descanso y volver a la serie. */
  const saltearDescanso = useCallback(() => {
    setFase('ejercicio');
    setFinDescanso(null);
    setPausado(false);
  }, []);

  const alternarPausa = useCallback(() => {
    setPausado((estaba) => {
      if (estaba) {
        setFinDescanso(Date.now() + restanteAlPausar.current * 1000);
        return false;
      }
      restanteAlPausar.current = restante;
      return true;
    });
  }, [restante]);

  /** Pasar de ejercicio sin darlo por hecho: queda pendiente para el final. */
  const saltearEjercicio = useCallback(() => {
    const siguiente = ejercicios.findIndex(
      (_, i) => i > indice && !completadas.includes(i),
    );
    const pendiente = siguiente !== -1
      ? siguiente
      : ejercicios.findIndex((_, i) => i !== indice && !completadas.includes(i));
    if (pendiente === -1) return;        // no hay a dónde ir
    setIndice(pendiente);
    setSerie(1);
    setFase('ejercicio');
    setFinDescanso(null);
  }, [indice, ejercicios, completadas]);

  const salir = useCallback(() => {
    olvidarProgreso();
    onSalir();
  }, [olvidarProgreso, onSalir]);

  // --- Lo que necesita la pantalla ----------------------------------------

  const progreso = useMemo(() => {
    const total = ejercicios.length;
    // El ejercicio en curso cuenta como "en el que voy", así que el numerador
    // es completados + 1 mientras quede algo por hacer.
    const hechos = completadas.length;
    return {
      hechos,
      total,
      actual: Math.min(hechos + 1, total),
      porcentaje: total ? Math.round((hechos / total) * 100) : 0,
    };
  }, [completadas, ejercicios.length]);

  return {
    ejercicio,
    indice,
    serie,
    totalSeries,
    fase,
    restante,
    pausado,
    progreso,
    completadas,
    completarSerie,
    saltearDescanso,
    saltearEjercicio,
    alternarPausa,
    salir,
  };
}
