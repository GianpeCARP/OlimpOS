import { useEffect, useRef, useState } from 'react';
import { Bell, Camera, Check, Play, RefreshCw, RotateCcw, Search, Square, X } from 'lucide-react';
import {
  DrawingUtils,
  FilesetResolver,
  PoseLandmarker,
} from '@mediapipe/tasks-vision';
import { colors } from '../../config';
import { mensajeDeError } from '../../services/api';
import {
  listarEjerciciosCatalogo,
  type EjercicioCatalogo,
} from '../../services/socioService';
import {
  activarReintentoAutomatico,
  encolarRegistro,
  sincronizar,
} from '../../utils/colaRegistros';
import {
  crearFiltroUnEuro,
  medirMovimiento,
  MOVIMIENTOS,
  movimientoDeEjercicio,
  pasoRep,
  type Fase,
  type Movimiento,
} from './logicaReps';

// Al empezar la serie se ignoran los conteos del primer tramo: es cuando el
// socio se acomoda en posición, y ese movimiento de setup no es una rep.
const GRACIA_MS = 700;
// Dos reps no pueden estar más cerca que esto: mata dobles conteos por temblor
// y algún fantasma. Nadie hace una rep real en menos de medio segundo.
const MIN_ENTRE_REPS_MS = 450;

// =============================================================================
// CONTADOR DE REPETICIONES — prototipo (incremento 2: conteo)
// =============================================================================
// Flujo: se abre en una pantalla de PREPARACIÓN (cámara todavía apagada) que
// muestra, centrada, la posición correcta para el ejercicio elegido. Recién al
// tocar "Activar cámara" se pide la cámara, que ocupa la pantalla completa.
//
// TODO corre en el dispositivo (MediaPipe BlazePose): el video NUNCA sale del
// teléfono. La lógica de conteo vive en logicaReps.ts, sin JSX. El modelo y el
// WASM están BUNDLEADOS en /public/mediapipe (no CDN).

type Estado = 'cargando' | 'pidiendo-camara' | 'listo' | 'error';

const RUTA_WASM = '/mediapipe/wasm';
const RUTA_MODELO = '/mediapipe/pose_landmarker_lite.task';

interface ContadorRepsProps {
  onSalir: () => void;
  /** Si viene del circuito, el ejercicio ya está decidido: se fija el
   *  movimiento y no se muestra el selector. */
  movimientoFijo?: Movimiento;
  /** Id del ejercicio en el catálogo. Sólo viene del circuito: es lo que
   *  permite ANOTAR la serie en Registro_Ejercicio. Sin él (modo "Probar"
   *  suelto) el contador cuenta pero no guarda —hasta el selector de catálogo. */
  idEjercicio?: number;
  /** Objetivo de reps sugerido (del circuito: las que dice el ejercicio).
   *  Prellena el input; el socio lo puede cambiar. */
  objetivoSugerido?: number;
}

export function ContadorReps({ onSalir, movimientoFijo, idEjercicio, objetivoSugerido }: ContadorRepsProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const landmarkerRef = useRef<PoseLandmarker | null>(null);
  const rafRef = useRef<number | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const drawRef = useRef<DrawingUtils | null>(null);

  // 'elegir' = eligiendo el ejercicio del catálogo (sólo modo suelto);
  // 'prep' = leyendo la posición, cámara APAGADA; 'camara' = cámara encendida.
  // Desde el circuito el ejercicio ya viene fijo, así que se salta 'elegir'.
  const [pantalla, setPantalla] = useState<'elegir' | 'prep' | 'camara'>(
    movimientoFijo ? 'prep' : 'elegir',
  );
  const [estado, setEstado] = useState<Estado>('cargando');
  const [error, setError] = useState<string | null>(null);
  const [detectado, setDetectado] = useState(false);
  const [frontal, setFrontal] = useState(true);

  // --- Elección del ejercicio (modo suelto) --------------------------------
  // El ejercicio elegido del catálogo aporta su id, así que en modo suelto la
  // serie TAMBIÉN se puede guardar (igual que desde el circuito). El del
  // circuito llega por prop; el suelto se elige acá.
  const [idEjercicioElegido, setIdEjercicioElegido] = useState<number | undefined>(undefined);
  const idEjercicioEfectivo = idEjercicio ?? idEjercicioElegido;
  // El catálogo, sólo los ejercicios que sabemos contar. Se carga una vez, en
  // modo suelto (desde el circuito no se elige nada).
  const [catalogo, setCatalogo] = useState<EjercicioCatalogo[] | null>(null);
  const [errorCatalogo, setErrorCatalogo] = useState<string | null>(null);
  const [busqueda, setBusqueda] = useState('');

  // --- Conteo --------------------------------------------------------------
  const [movimiento, setMovimiento] = useState<Movimiento>(movimientoFijo ?? MOVIMIENTOS[0]);
  const [serieActiva, setSerieActiva] = useState(false);
  const [reps, setReps] = useState(0);
  const [resumen, setResumen] = useState<{ reps: number; movimiento: string } | null>(null);
  const [pulso, setPulso] = useState(0);
  const [bump, setBump] = useState(false);

  // --- Objetivo de reps + pitido ------------------------------------------
  // El socio dice cuántas quiere hacer; cuando las iguala, el celu PITA (y
  // vibra fuerte), porque en la serie de tu vida vas con los ojos cerrados y no
  // estás mirando la pantalla. Vacío = sin objetivo, no avisa.
  const [objetivo, setObjetivo] = useState(objetivoSugerido ? String(objetivoSugerido) : '');
  const objetivoNum = Math.floor(Number(objetivo)) || 0;
  const audioRef = useRef<AudioContext | null>(null);

  // --- Guardado de la serie (sólo si vino del circuito con id de ejercicio) --
  // 'guardado' entró al backend; 'encolado' quedó pendiente sin red y se subirá
  // solo cuando vuelva. El peso lo carga el socio al terminar: la cámara no lo
  // sabe. Vacío = 0 kg (la fila igual sirve para el conteo de reps).
  const puedeGuardar = idEjercicioEfectivo !== undefined;
  const [peso, setPeso] = useState('');
  const [guardado, setGuardado] = useState<'idle' | 'guardando' | 'guardado' | 'encolado'>('idle');

  const serieRef = useRef(false);
  const movRef = useRef(movimiento);
  const faseRef = useRef<Fase>('ext');
  // Un filtro por señal (lado más flexionado y lado más extendido): se suavizan
  // por separado antes de decidir la fase.
  const filtroMinRef = useRef(crearFiltroUnEuro());
  const filtroMaxRef = useRef(crearFiltroUnEuro());
  const inicioSerieRef = useRef(0);   // cuándo arrancó la serie (para la gracia)
  const ultimaRepRef = useRef(0);     // cuándo se contó la última (anti-rebote)
  useEffect(() => { movRef.current = movimiento; }, [movimiento]);
  useEffect(() => { serieRef.current = serieActiva; }, [serieActiva]);

  // "Te veo bien" mientras hay un ángulo confiable del movimiento. Se avisa
  // sólo tras varios frames sin señal, para no titilar. verBienRef evita
  // llamar a setState en cada frame.
  const [verBien, setVerBien] = useState(true);
  const verBienRef = useRef(true);
  const sinSenalRef = useRef(0);
  const marcarVer = (v: boolean) => {
    if (verBienRef.current !== v) {
      verBienRef.current = v;
      setVerBien(v);
    }
  };

  useEffect(() => {
    if (pulso === 0) return;
    setBump(true);
    const t = setTimeout(() => setBump(false), 160);
    return () => clearTimeout(t);
  }, [pulso]);

  // --- Modelo: se carga una vez, EN PARALELO a la pantalla de preparación ---
  // Así, mientras el socio lee la posición y elige el ejercicio, el modelo ya
  // se está bajando; al activar la cámara casi no hay espera.
  useEffect(() => {
    let vivo = true;
    (async () => {
      try {
        const vision = await FilesetResolver.forVisionTasks(RUTA_WASM);
        const crear = (delegate: 'GPU' | 'CPU') =>
          PoseLandmarker.createFromOptions(vision, {
            baseOptions: { modelAssetPath: RUTA_MODELO, delegate },
            runningMode: 'VIDEO',
            numPoses: 1,
          });
        let lm: PoseLandmarker;
        try {
          lm = await crear('GPU');
        } catch {
          lm = await crear('CPU');
        }
        if (!vivo) {
          lm.close();
          return;
        }
        landmarkerRef.current = lm;
        setEstado('pidiendo-camara');
      } catch {
        if (vivo) {
          setError('No se pudo cargar el detector de pose en este dispositivo.');
          setEstado('error');
        }
      }
    })();
    return () => {
      vivo = false;
    };
  }, []);

  // --- Cámara + bucle: sólo una vez activada la pantalla de cámara ----------
  useEffect(() => {
    if (pantalla !== 'camara' || estado === 'cargando' || estado === 'error') return;

    let vivo = true;

    const arrancar = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: frontal ? 'user' : 'environment' },
          audio: false,
        });
        if (!vivo) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        const video = videoRef.current;
        if (!video) return;
        video.srcObject = stream;
        await video.play();
        setEstado('listo');
        bucle();
      } catch {
        if (vivo) {
          setError('No pudimos usar la cámara. Revisá que le hayas dado permiso.');
          setEstado('error');
        }
      }
    };

    const bucle = () => {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      const lm = landmarkerRef.current;
      if (!vivo || !video || !canvas || !lm) return;

      if (video.readyState >= 2 && video.videoWidth > 0) {
        if (canvas.width !== video.videoWidth) {
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          drawRef.current = new DrawingUtils(canvas.getContext('2d')!);
        }
        const ctx = canvas.getContext('2d')!;
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        const res = lm.detectForVideo(video, performance.now());
        const hay = !!res.landmarks?.length;
        setDetectado(hay);

        if (hay && drawRef.current) {
          for (const puntos of res.landmarks) {
            drawRef.current.drawConnectors(
              puntos,
              PoseLandmarker.POSE_CONNECTIONS,
              { color: 'rgba(198, 241, 53, 0.85)', lineWidth: 4 },
            );
            drawRef.current.drawLandmarks(puntos, {
              color: colors.primaryVolt,
              fillColor: colors.surfaceBase,
              lineWidth: 2,
              radius: 5,
            });
          }
        }

        if (serieRef.current) {
          const med = hay && res.worldLandmarks?.length
            ? medirMovimiento(res.worldLandmarks[0], res.landmarks[0], movRef.current)
            : null;
          if (med !== null) {
            sinSenalRef.current = 0;
            marcarVer(true);
            const ahora = performance.now();
            const suaveMin = filtroMinRef.current.filtrar(med.min, ahora);
            const suaveMax = filtroMaxRef.current.filtrar(med.max, ahora);
            const r = pasoRep(faseRef.current, suaveMin, suaveMax, movRef.current);
            faseRef.current = r.fase;
            // Sólo cuenta si pasó la gracia del arranque (setup) y el anti-rebote
            // desde la última rep. Si no, la fase avanza igual pero no suma.
            if (
              r.conto &&
              ahora - inicioSerieRef.current > GRACIA_MS &&
              ahora - ultimaRepRef.current > MIN_ENTRE_REPS_MS
            ) {
              ultimaRepRef.current = ahora;
              setReps((n) => n + 1);
              setPulso((p) => p + 1);
              navigator.vibrate?.(30);
            }
          } else {
            // Sin señal confiable: no se cuenta. Se avisa recién tras ~0.4s
            // seguidos para no titilar por un frame perdido.
            sinSenalRef.current += 1;
            if (sinSenalRef.current > 12) marcarVer(false);
          }
        }
      }
      rafRef.current = requestAnimationFrame(bucle);
    };

    arrancar();

    return () => {
      vivo = false;
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [frontal, pantalla, estado === 'cargando']);

  useEffect(() => {
    return () => {
      landmarkerRef.current?.close();
      landmarkerRef.current = null;
    };
  }, []);

  // Al abrir el contador, subir lo que haya quedado sin guardar de antes (por
  // ejemplo, una serie contada ayer sin wifi) y dejar armado el reintento
  // automático para cuando la red vuelva. No hace nada si la cola está vacía.
  useEffect(() => {
    activarReintentoAutomatico();
    void sincronizar();
  }, []);

  // El catálogo para elegir en modo suelto. Sólo si no viene fijo del circuito.
  useEffect(() => {
    if (movimientoFijo) return;
    let cancelado = false;
    listarEjerciciosCatalogo()
      .then((c) => { if (!cancelado) setCatalogo(c); })
      .catch((e: unknown) => { if (!cancelado) setErrorCatalogo(mensajeDeError(e)); });
    return () => { cancelado = true; };
  }, [movimientoFijo]);

  const elegirEjercicio = (ej: EjercicioCatalogo) => {
    const mov = movimientoDeEjercicio(ej.nombre);
    if (!mov) return; // sólo se muestran los soportados, pero por las dudas
    setMovimiento(mov);
    setIdEjercicioElegido(ej.idEjercicio);
    setPantalla('prep');
  };

  // El pitido usa Web Audio: hay que crear/despertar el AudioContext desde un
  // gesto del usuario (iOS lo exige), y "Empezar serie" lo es.
  const asegurarAudio = () => {
    try {
      if (!audioRef.current) {
        const AC = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
        if (AC) audioRef.current = new AC();
      }
      void audioRef.current?.resume();
    } catch {
      // Sin audio (permisos, navegador raro): la vibración sigue avisando.
    }
  };

  const pitar = () => {
    const ctx = audioRef.current;
    if (!ctx) return;
    try {
      // Dos beeps cortos, bien distinguibles del silencio de la serie.
      for (const t0 of [0, 0.18]) {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.value = 880;
        const t = ctx.currentTime + t0;
        gain.gain.setValueAtTime(0.0001, t);
        gain.gain.exponentialRampToValueAtTime(0.35, t + 0.01);
        gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.14);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(t);
        osc.stop(t + 0.15);
      }
    } catch {
      // Ignorar: si el audio falla, ya vibró.
    }
  };

  const empezar = () => {
    asegurarAudio();
    setResumen(null);
    setReps(0);
    setPeso('');
    setGuardado('idle');
    faseRef.current = 'ext';
    filtroMinRef.current.reiniciar();
    filtroMaxRef.current.reiniciar();
    inicioSerieRef.current = performance.now();
    ultimaRepRef.current = 0;
    sinSenalRef.current = 0;
    marcarVer(true);
    setSerieActiva(true);
  };

  // Avisa (pitido + vibración fuerte) al igualar el objetivo. Se dispara sólo en
  // el frame en que reps llega justo al número: reps sube de a uno.
  useEffect(() => {
    if (!serieActiva || objetivoNum <= 0) return;
    if (reps === objetivoNum) {
      pitar();
      navigator.vibrate?.([120, 60, 120]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reps]);

  const terminar = () => {
    setSerieActiva(false);
    setResumen({ reps, movimiento: movimiento.nombre });
  };

  // Guarda la serie recién terminada. Encola SIEMPRE y sube si hay red; si no,
  // queda pendiente y se sube sola al reconectar. Nunca tira: perder una serie
  // por un guardado fallido sería peor que el guardado en sí.
  const guardarSerie = async () => {
    if (!puedeGuardar || resumen === null || resumen.reps < 1) return;
    setGuardado('guardando');
    const kg = Number(peso.replace(',', '.'));
    const resultado = await encolarRegistro({
      idEjercicio: idEjercicioEfectivo!,
      repeticiones: resumen.reps,
      peso: Number.isFinite(kg) && kg > 0 ? kg : 0,
      observaciones: 'Contado con cámara',
    });
    setGuardado(resultado);
  };

  const reiniciar = () => {
    setReps(0);
    faseRef.current = 'ext';
    filtroMinRef.current.reiniciar();
    filtroMaxRef.current.reiniciar();
    inicioSerieRef.current = performance.now();
    ultimaRepRef.current = 0;
  };

  // ==========================================================================
  // PANTALLA DE ELECCIÓN — elegir el ejercicio del catálogo (modo suelto)
  // ==========================================================================
  if (pantalla === 'elegir') {
    // Sólo los ejercicios que sabemos contar, filtrados por la búsqueda y
    // agrupados por grupo muscular.
    const q = busqueda.trim().toLowerCase();
    const soportados = (catalogo ?? []).filter((e) => movimientoDeEjercicio(e.nombre) !== null);
    const filtrados = q
      ? soportados.filter(
          (e) => e.nombre.toLowerCase().includes(q) || e.grupoMuscular.toLowerCase().includes(q),
        )
      : soportados;
    const grupos = new Map<string, EjercicioCatalogo[]>();
    for (const e of filtrados) {
      const g = grupos.get(e.grupoMuscular) ?? [];
      g.push(e);
      grupos.set(e.grupoMuscular, g);
    }

    return (
      <div className="fixed inset-0 z-50 flex flex-col bg-surface-base">
        <header className="flex shrink-0 items-center justify-between px-4 py-3">
          <p className="font-heading text-lg font-semibold uppercase tracking-wide text-text-main">
            ¿Qué vas a hacer?
          </p>
          <button
            type="button"
            onClick={onSalir}
            aria-label="Cerrar"
            className="flex size-10 items-center justify-center rounded-full bg-surface-card text-text-main"
          >
            <X size={20} />
          </button>
        </header>

        <div className="shrink-0 px-4 pb-3">
          <div className="flex items-center gap-2 rounded-lg bg-surface-card px-3 py-2 ring-1 ring-border-idle focus-within:ring-primary-volt">
            <Search size={16} className="shrink-0 text-text-muted" />
            <input
              type="text"
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              placeholder="Buscar ejercicio o grupo…"
              className="w-full bg-transparent font-body text-sm text-text-main outline-none"
            />
          </div>
        </div>

        <div className="flex-1 space-y-5 overflow-y-auto overscroll-contain px-4 pb-6">
          {errorCatalogo && <p className="font-body text-sm text-status-danger">{errorCatalogo}</p>}
          {!catalogo && !errorCatalogo && (
            <p className="font-body text-sm text-text-muted">Cargando ejercicios…</p>
          )}
          {catalogo && [...grupos.keys()].length === 0 && (
            <p className="font-body text-sm text-text-muted">
              No hay ejercicios que la cámara sepa contar todavía.
            </p>
          )}
          {[...grupos.entries()].map(([grupo, ejercicios]) => (
            <div key={grupo} className="space-y-2">
              <p className="font-body text-xs font-semibold uppercase tracking-wide text-text-muted">
                {grupo}
              </p>
              <div className="space-y-1.5">
                {ejercicios.map((e) => (
                  <button
                    key={e.idEjercicio}
                    type="button"
                    onClick={() => elegirEjercicio(e)}
                    className="flex w-full items-center justify-between gap-2 rounded-lg bg-surface-card px-3 py-3 text-left ring-1 ring-border-idle active:bg-surface-hover"
                  >
                    <span className="min-w-0 truncate font-body text-sm text-text-main">{e.nombre}</span>
                    <Camera size={16} className="shrink-0 text-primary-volt" />
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // ==========================================================================
  // PANTALLA DE PREPARACIÓN — cámara apagada, posición centrada
  // ==========================================================================
  if (pantalla === 'prep') {
    return (
      <div className="fixed inset-0 z-50 flex flex-col bg-surface-base">
        <header className="flex shrink-0 items-center justify-between px-4 py-3">
          <p className="font-heading text-lg font-semibold uppercase tracking-wide text-text-main">
            Contar reps <span className="text-xs font-normal text-primary-volt">beta</span>
          </p>
          <button
            type="button"
            onClick={onSalir}
            aria-label="Cerrar"
            className="flex size-10 items-center justify-center rounded-full bg-surface-card text-text-main"
          >
            <X size={20} />
          </button>
        </header>

        <div className="flex flex-1 flex-col items-center justify-center gap-7 px-6 text-center">
          <div className="flex flex-col items-center gap-2">
            <p className="font-heading text-2xl font-bold text-text-main">
              {movimiento.nombre}
            </p>
            {/* Del circuito el ejercicio es fijo; en modo suelto se puede volver
                a elegir otro del catálogo. */}
            {!movimientoFijo && (
              <button
                type="button"
                onClick={() => setPantalla('elegir')}
                className="font-body text-sm text-primary-volt underline underline-offset-2"
              >
                Cambiar ejercicio
              </button>
            )}
          </div>

          <div className="flex max-w-xs flex-col items-center gap-3">
            <div className="flex size-14 items-center justify-center rounded-full bg-primary-volt/10">
              <Camera size={26} className="text-primary-volt" />
            </div>
            <p className="font-heading text-sm font-semibold uppercase tracking-widest text-text-muted">
              Posición
            </p>
            <p className="font-body text-lg leading-snug text-text-main">
              {movimiento.pista}
            </p>
          </div>

          {/* Objetivo de reps: cuando llegás, el celu pita. Prellenado con lo
              que dice el ejercicio si viene del circuito; editable siempre. */}
          <label className="flex w-full max-w-xs flex-col items-center gap-2">
            <span className="flex items-center gap-1.5 font-heading text-sm font-semibold uppercase tracking-widest text-text-muted">
              <Bell size={14} /> ¿Cuántas repes?
            </span>
            <input
              type="text"
              inputMode="numeric"
              value={objetivo}
              onChange={(e) => setObjetivo(e.target.value.replace(/\D/g, ''))}
              placeholder="—"
              className="w-24 rounded-lg bg-surface-card px-3 py-2 text-center font-heading text-3xl font-bold tabular-nums text-text-main outline-none ring-1 ring-border-idle focus:ring-primary-volt"
            />
            <span className="font-body text-xs text-text-muted">
              Te aviso con un pitido cuando llegues. Dejalo vacío si vas libre.
            </span>
          </label>
        </div>

        <div className="shrink-0 px-6 pb-8">
          <button
            type="button"
            onClick={() => setPantalla('camara')}
            className="mx-auto flex w-full max-w-xs items-center justify-center gap-2 rounded-xl bg-primary-volt py-3 font-heading text-base font-semibold uppercase tracking-wide text-surface-base"
          >
            <Camera size={18} /> Activar cámara
          </button>
        </div>
      </div>
    );
  }

  // ==========================================================================
  // PANTALLA DE CÁMARA — a pantalla completa, controles flotantes
  // ==========================================================================
  const cargandoCamara = estado === 'cargando' || estado === 'pidiendo-camara';

  return (
    <div className="fixed inset-0 z-50 bg-surface-base">
      {/* La cámara ocupa TODO */}
      <div className={`absolute inset-0 ${frontal ? '-scale-x-100' : ''}`}>
        <video ref={videoRef} playsInline muted className="absolute inset-0 h-full w-full object-cover" />
        <canvas ref={canvasRef} className="absolute inset-0 h-full w-full object-cover" />
      </div>

      {/* Barra superior flotante */}
      <div className="absolute inset-x-0 top-0 flex items-center justify-between bg-gradient-to-b from-black/70 to-transparent px-4 pb-8 pt-3">
        <p className="font-heading text-base font-semibold uppercase tracking-wide text-white">
          {movimiento.nombre}
        </p>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setFrontal((f) => !f)}
            disabled={estado !== 'listo' || serieActiva}
            aria-label="Cambiar de cámara"
            className="flex size-10 items-center justify-center rounded-full bg-black/40 text-white disabled:opacity-40"
          >
            <RefreshCw size={18} />
          </button>
          <button
            type="button"
            onClick={onSalir}
            aria-label="Cerrar"
            className="flex size-10 items-center justify-center rounded-full bg-black/40 text-white"
          >
            <X size={20} />
          </button>
        </div>
      </div>

      {cargandoCamara && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-surface-base/80">
          <Camera size={32} className="animate-pulse text-primary-volt" />
          <p className="font-body text-sm text-text-secondary">
            {estado === 'cargando' ? 'Preparando el detector…' : 'Encendiendo la cámara…'}
          </p>
        </div>
      )}
      {estado === 'error' && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-surface-base px-6 text-center">
          <p className="font-body text-sm text-status-danger">{error}</p>
          <button
            type="button"
            onClick={onSalir}
            className="rounded-lg bg-surface-card px-4 py-2 font-body text-sm text-text-main"
          >
            Volver
          </button>
        </div>
      )}

      {/* Chip de detección (fuera de la serie) */}
      {estado === 'listo' && !serieActiva && !resumen && (
        <div className="pointer-events-none absolute left-1/2 top-14 -translate-x-1/2">
          <span
            className={`rounded-full px-3 py-1 font-body text-xs font-medium ${
              detectado ? 'bg-primary-volt text-surface-base' : 'bg-black/50 text-white'
            }`}
          >
            {detectado ? 'Cuerpo detectado' : 'Buscándote…'}
          </span>
        </div>
      )}

      {/* Número grande, durante la serie */}
      {estado === 'listo' && serieActiva && (
        <div className="pointer-events-none absolute inset-x-0 top-0 flex flex-col items-center pt-14">
          <span
            className={`font-heading font-bold leading-none text-primary-volt tabular-nums drop-shadow-[0_2px_16px_rgba(0,0,0,0.8)] transition-transform duration-150 ${
              bump ? 'scale-110' : 'scale-100'
            }`}
            style={{ fontSize: '6rem' }}
          >
            {reps}
          </span>
          <span className="mt-1 font-body text-sm font-medium uppercase tracking-widest text-white/85 drop-shadow-[0_1px_6px_rgba(0,0,0,0.9)]">
            {objetivoNum > 0 ? `de ${objetivoNum}` : 'repeticiones'}
          </span>
          {objetivoNum > 0 && reps >= objetivoNum && (
            <span className="mt-3 flex items-center gap-1.5 rounded-full bg-primary-volt px-3 py-1 font-heading text-sm font-bold uppercase tracking-wide text-surface-base drop-shadow-[0_2px_10px_rgba(0,0,0,0.6)]">
              <Bell size={14} /> ¡Llegaste!
            </span>
          )}
          {!verBien && (
            <span className="mt-3 rounded-full bg-status-warn/90 px-3 py-1 font-body text-xs font-medium text-surface-base">
              Acomodate: no te veo bien
            </span>
          )}
        </div>
      )}

      {/* Resumen */}
      {estado === 'listo' && resumen && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-surface-base/90 px-6 text-center">
          <Check size={40} className="text-status-ok" />
          <p className="font-heading text-5xl font-bold text-primary-volt tabular-nums">{resumen.reps}</p>
          <p className="font-body text-sm text-text-secondary">
            repeticiones de {resumen.movimiento}
          </p>

          {/* Guardar sólo tiene sentido si vino del circuito (hay ejercicio) y
              se contó al menos una rep. Antes de guardar, se pide el peso. */}
          {puedeGuardar && resumen.reps > 0 && guardado === 'idle' && (
            <div className="mt-2 flex w-full max-w-xs flex-col items-center gap-3">
              <label className="flex w-full flex-col items-center gap-1">
                <span className="font-body text-xs uppercase tracking-widest text-text-muted">
                  Peso (kg) · opcional
                </span>
                <input
                  type="text"
                  inputMode="decimal"
                  value={peso}
                  onChange={(e) => setPeso(e.target.value)}
                  placeholder="0"
                  className="w-28 rounded-lg bg-surface-card px-3 py-2 text-center font-heading text-2xl font-bold tabular-nums text-text-main outline-none ring-1 ring-border-idle focus:ring-primary-volt"
                />
              </label>
              <button
                type="button"
                onClick={() => void guardarSerie()}
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary-volt py-3 font-heading text-base font-semibold uppercase tracking-wide text-surface-base"
              >
                <Check size={18} /> Guardar serie
              </button>
            </div>
          )}

          {guardado === 'guardando' && (
            <p className="mt-1 font-body text-sm text-text-secondary">Guardando…</p>
          )}
          {guardado === 'guardado' && (
            <p className="mt-1 flex items-center gap-1.5 font-body text-sm font-medium text-status-ok">
              <Check size={16} /> Serie guardada
            </p>
          )}
          {guardado === 'encolado' && (
            <p className="mt-1 max-w-xs font-body text-sm font-medium text-status-warn">
              Sin internet: la serie se va a guardar sola cuando vuelva la conexión.
            </p>
          )}
        </div>
      )}

      {/* Controles flotantes abajo */}
      <div className="absolute inset-x-0 bottom-0 space-y-3 bg-gradient-to-t from-black/75 to-transparent px-4 pb-6 pt-10">
        {!serieActiva ? (
          <button
            type="button"
            onClick={empezar}
            disabled={estado !== 'listo'}
            className="mx-auto flex w-full max-w-xs items-center justify-center gap-2 rounded-xl bg-primary-volt py-3 font-heading text-base font-semibold uppercase tracking-wide text-surface-base disabled:opacity-40"
          >
            {resumen ? <RefreshCw size={18} /> : <Play size={18} />}
            {resumen ? 'Empezar otra' : 'Empezar serie'}
          </button>
        ) : (
          <div className="mx-auto flex w-full max-w-sm gap-2">
            <button
              type="button"
              onClick={reiniciar}
              className="flex shrink-0 items-center justify-center gap-2 rounded-xl bg-black/50 px-5 py-3 font-heading text-sm font-semibold uppercase tracking-wide text-white"
            >
              <RotateCcw size={18} /> Reiniciar
            </button>
            <button
              type="button"
              onClick={terminar}
              className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-black/60 py-3 font-heading text-base font-semibold uppercase tracking-wide text-white"
            >
              <Square size={18} /> Terminar
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
