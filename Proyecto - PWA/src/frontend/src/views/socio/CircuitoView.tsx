import { useEffect, useRef, useState } from 'react';
import { Camera, Check, ChevronsRight, Pause, Play, X } from 'lucide-react';
import type { DiaDeRutina } from '../../services/socioService';
import { esCelular } from '../../utils/dispositivo';
import { movimientoDeEjercicio } from './logicaReps';
import { ContadorReps } from './ContadorReps';
import { useCircuito } from './useCircuito';

// El circuito: un ejercicio a la vez, a pantalla completa.
//
// POR QUE NO ES UNA SECCION DEL MENU
// ==================================
// Porque las secciones son entradas de la matriz de permisos, y la matriz
// esta copiada en TRES lugares (config.ts, backend/permisos.py y el
// app/permisos.py de Flet) que check_permisos.py verifica. Sumar una seccion
// para esto obligaria a tocar las tres. Y ademas el circuito no existe sin una
// rutina: una seccion aparte estaria vacia justo para el socio que todavia no
// tiene una asignada, que es el que mas se confunde. Es el mismo criterio por
// el que /portal/mi-entrenador vive bajo MI_RUTINA y no tiene seccion propia.
//
// COMO SE USA DE VERDAD
// =====================
// Alguien parado en el gimnasio, con el telefono en una mano y las manos
// ocupadas. De ahi salen las tres decisiones de esta pantalla:
//
//   1. UN boton grande y todo lo demas chico. La accion frecuente —cerrar la
//      serie— tiene que poder tocarse sin mirar.
//   2. El descanso arranca SOLO. Cada toque de mas entre serie y serie es uno
//      que no se va a dar.
//   3. Numeros enormes. Se leen a un metro, con el telefono apoyado en el
//      banco.

interface CircuitoViewProps {
  dia: DiaDeRutina;
  idRutina: number;
  nombreRutina: string;
  etiquetaDia: string;
  onSalir: () => void;
}

/** mm:ss a partir de segundos. */
function reloj(segundos: number): string {
  const m = Math.floor(segundos / 60);
  const s = segundos % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}

export function CircuitoView({
  dia,
  idRutina,
  nombreRutina,
  etiquetaDia,
  onSalir,
}: CircuitoViewProps) {
  const c = useCircuito({ dia, idRutina, onSalir });
  const contenedor = useRef<HTMLDivElement>(null);

  // Contar reps con la cámara para el ejercicio ACTUAL (sólo en celular, y sólo
  // si ese ejercicio está soportado por el contador). El movimiento sale
  // mapeado del catálogo: acá el socio no elige nada, ya está en su serie.
  const [contando, setContando] = useState(false);
  const [puedeContar] = useState(() => esCelular());
  const movCamara = c.ejercicio ? movimientoDeEjercicio(c.ejercicio.nombre) : null;

  // --- Pantalla completa ---------------------------------------------------
  // La API de fullscreen SI funciona sobre HTTP (sólo pide un gesto del
  // usuario, que fue el botón "Comenzar"). Es lo que permite tener la
  // experiencia inmersiva sin depender de que la PWA esté instalada, que
  // exigiría HTTPS.
  useEffect(() => {
    const nodo = contenedor.current;
    if (!nodo?.requestFullscreen) return;
    nodo.requestFullscreen().catch(() => {
      // Si el navegador lo rechaza (iOS Safari no lo soporta en cualquier
      // elemento) la pantalla funciona igual, sólo que con la barra del
      // navegador arriba. No es motivo para no dejar entrenar.
    });
    return () => {
      if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
    };
  }, []);

  // --- Que no se apague la pantalla ---------------------------------------
  // Screen Wake Lock SÓLO existe en contexto seguro (HTTPS o localhost), así
  // que abriendo la app por la IP de la red esto no va a estar. Se consulta
  // antes de usarlo en vez de asumir: en producción, con HTTPS, funciona solo
  // sin tocar una línea.
  useEffect(() => {
    let lock: WakeLockSentinel | null = null;
    let cancelado = false;

    const pedir = async () => {
      try {
        if (!('wakeLock' in navigator)) return;
        lock = await navigator.wakeLock.request('screen');
        if (cancelado) { void lock.release(); lock = null; }
      } catch {
        // Lo rechaza si la pestaña no está visible, entre otras cosas. No es
        // un error que valga la pena mostrar.
      }
    };

    void pedir();
    // El sistema lo suelta al cambiar de app. Al volver hay que volver a
    // pedirlo o la pantalla se apaga en medio del descanso.
    const alVolver = () => {
      if (document.visibilityState === 'visible') void pedir();
    };
    document.addEventListener('visibilitychange', alVolver);

    return () => {
      cancelado = true;
      document.removeEventListener('visibilitychange', alVolver);
      if (lock) void lock.release();
    };
  }, []);

  // --- Terminado -----------------------------------------------------------
  if (c.fase === 'terminado') {
    return (
      <div
        ref={contenedor}
        className="fixed inset-0 z-50 flex flex-col items-center justify-center gap-6 bg-surface-base p-8 text-center"
      >
        <div className="flex h-24 w-24 items-center justify-center rounded-full bg-primary-volt">
          <Check size={48} className="text-surface-base" />
        </div>
        <div>
          <h1 className="font-heading text-3xl font-bold text-text-main">
            Entrenamiento completo
          </h1>
          <p className="mt-2 font-body text-base text-text-secondary">
            {etiquetaDia} · {c.progreso.total}{' '}
            {c.progreso.total === 1 ? 'ejercicio' : 'ejercicios'}
          </p>
        </div>
        <button
          type="button"
          onClick={c.salir}
          className="rounded-lg bg-primary-volt px-8 py-4 font-body text-base font-semibold whitespace-nowrap text-surface-base"
        >
          Listo
        </button>
      </div>
    );
  }

  if (!c.ejercicio) {
    return (
      <div
        ref={contenedor}
        className="fixed inset-0 z-50 flex flex-col items-center justify-center gap-4 bg-surface-base p-8 text-center"
      >
        <p className="font-body text-base text-text-secondary">
          Este día no tiene ejercicios cargados.
        </p>
        <button
          type="button"
          onClick={c.salir}
          className="rounded-lg border border-border-idle px-6 py-3 font-body text-sm text-text-secondary"
        >
          Volver
        </button>
      </div>
    );
  }

  const enDescanso = c.fase === 'descanso';

  // El contador se monta ENCIMA del circuito; al cerrarlo (X) se vuelve acá,
  // a la misma serie. El circuito no se desmonta por debajo.
  if (contando && movCamara && c.ejercicio) {
    // Objetivo sugerido = el primer número de las reps del ejercicio ("8-12" -> 8,
    // "al fallo" -> sin objetivo). El socio lo puede cambiar en el contador.
    const m = c.ejercicio.repeticiones?.match(/\d+/);
    const objetivoSugerido = m ? Number(m[0]) : undefined;
    return (
      <ContadorReps
        movimientoFijo={movCamara}
        idEjercicio={c.ejercicio.idEjercicio}
        objetivoSugerido={objetivoSugerido}
        onSalir={() => setContando(false)}
      />
    );
  }

  return (
    <div
      ref={contenedor}
      // h-full y no h-screen: en iOS `100vh` incluye la barra del navegador y
      // el boton de abajo quedaria tapado por ella. La altura real la fija
      // index.css con 100dvh. Ver el comentario de AppLayout.
      className="fixed inset-0 z-50 flex h-full flex-col bg-surface-base"
    >
      {/* ── Encabezado: contexto y salida ─────────────────────────────── */}
      <header className="flex shrink-0 items-center justify-between gap-3 px-5 pt-4 md:pt-5">
        <div className="min-w-0">
          <p className="truncate font-body text-xs text-text-muted">{nombreRutina}</p>
          <p className="truncate font-heading text-sm font-semibold text-text-main">
            {etiquetaDia}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-3">
          <span className="font-mono text-xs text-text-secondary">
            {c.progreso.actual}/{c.progreso.total}
          </span>
          <button
            type="button"
            onClick={c.salir}
            aria-label="Salir del circuito"
            className="rounded-md p-2 text-text-muted hover:bg-surface-hover hover:text-text-main"
          >
            <X size={20} />
          </button>
        </div>
      </header>

      {/* Barra de progreso del circuito entero. */}
      <div className="mt-4 h-1 w-full bg-surface-hover">
        <div
          className="h-full bg-primary-volt transition-[width] duration-300"
          style={{ width: `${c.progreso.porcentaje}%` }}
        />
      </div>

      {/* ── El centro: o el ejercicio, o el descanso ──────────────────── */}
      <main className="flex flex-1 flex-col items-center justify-center gap-4 overflow-y-auto overscroll-contain px-6 py-4 text-center md:gap-6">
        {enDescanso ? (
          <>
            <p className="font-body text-sm tracking-widest text-text-muted uppercase">
              Descanso
            </p>
            {/* tabular-nums: sin esto el ancho del numero cambia con cada
                digito y el contador "tiembla" mientras baja. */}
            <p className="font-mono text-6xl font-bold text-primary-volt tabular-nums md:text-7xl">
              {reloj(c.restante)}
            </p>
            <p className="font-body text-base text-text-secondary">
              Después va la serie {c.serie} de {c.totalSeries}
            </p>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={c.alternarPausa}
                className="flex shrink-0 items-center gap-2 rounded-lg border border-border-idle px-5 py-3 font-body text-sm whitespace-nowrap text-text-secondary"
              >
                {c.pausado ? <Play size={16} /> : <Pause size={16} />}
                {c.pausado ? 'Seguir' : 'Pausar'}
              </button>
              <button
                type="button"
                onClick={c.saltearDescanso}
                className="flex shrink-0 items-center gap-2 rounded-lg border border-border-idle px-5 py-3 font-body text-sm whitespace-nowrap text-text-secondary"
              >
                <ChevronsRight size={16} />
                Saltear
              </button>
            </div>
          </>
        ) : (
          <>
            <p className="font-body text-sm tracking-widest text-text-muted uppercase">
              {c.ejercicio.grupoMuscular}
            </p>
            <h1 className="font-heading text-3xl leading-tight font-bold break-words text-text-main md:text-4xl">
              {c.ejercicio.nombre}
            </h1>

            <p className="font-mono text-4xl font-bold text-primary-volt tabular-nums md:text-5xl">
              {c.totalSeries} × {c.ejercicio.repeticiones ?? '—'}
            </p>

            {c.ejercicio.pesoSugerido !== undefined && (
              <p className="font-body text-base text-text-secondary">
                {c.ejercicio.pesoSugerido} kg sugerido
              </p>
            )}

            {/* Los puntos de serie. Se ve de un vistazo cuánto falta sin
                tener que leer un número. */}
            <div className="flex flex-wrap items-center justify-center gap-2">
              {Array.from({ length: c.totalSeries }, (_, i) => (
                <span
                  key={i}
                  className={
                    i < c.serie - 1
                      ? 'h-3 w-3 rounded-full bg-primary-volt'
                      : i === c.serie - 1
                        ? 'h-3 w-3 rounded-full ring-2 ring-primary-volt'
                        : 'h-3 w-3 rounded-full bg-surface-hover'
                  }
                />
              ))}
              <span className="ml-2 font-body text-sm text-text-muted">
                serie {c.serie} de {c.totalSeries}
              </span>
            </div>

            {c.ejercicio.observaciones && (
              <p className="max-w-sm font-body text-sm text-status-warn">
                {c.ejercicio.observaciones}
              </p>
            )}
          </>
        )}
      </main>

      {/* ── El botón grande ───────────────────────────────────────────── */}
      {/* pb generoso: en un celular con gesto de inicio, un botón pegado al
          borde inferior compite con el del sistema. */}
      <footer className="flex shrink-0 flex-col gap-2 px-5 pt-3 pb-6 md:gap-3 md:pt-4 md:pb-8">
        {!enDescanso && (
          <button
            type="button"
            onClick={c.completarSerie}
            className="w-full rounded-xl bg-primary-volt py-5 font-heading text-xl font-bold whitespace-nowrap text-surface-base active:opacity-90 md:py-6"
          >
            {c.serie >= c.totalSeries ? 'Terminar ejercicio' : 'Serie completada'}
          </button>
        )}
        {/* Contar con la cámara: sólo en celular y sólo si el ejercicio actual
            está soportado por el contador. Como no lo está la mayoría todavía,
            aparece sólo cuando de verdad sirve. */}
        {!enDescanso && puedeContar && movCamara && (
          <button
            type="button"
            onClick={() => setContando(true)}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-border-idle py-3 font-body text-sm whitespace-nowrap text-text-secondary"
          >
            <Camera size={16} /> Contar con cámara
          </button>
        )}
        {!enDescanso && c.progreso.total > 1 && (
          <button
            type="button"
            onClick={c.saltearEjercicio}
            className="w-full py-2 font-body text-sm text-text-muted"
          >
            Saltear este ejercicio
          </button>
        )}
      </footer>
    </div>
  );
}
