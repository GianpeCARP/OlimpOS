import { useCallback, useEffect, useState } from 'react';
import { AlertTriangle, BookOpen, Calendar, Camera, Dumbbell, Pencil, Play, PlayCircle, Sparkles, Target, Timer, Trash2, User } from 'lucide-react';
import { LevelBadge, PrimaryButton, SectionCard, Topbar } from '../../components/ui';
import { colors } from '../../config';
import { mensajeDeError } from '../../services/api';
import { eliminarMiRutinaPropia, getMiRutina, type DiaDeRutina, type EjercicioDelDia, type MiRutina } from '../../services/socioService';
import { useAuthStore } from '../../store/authStore';
import { formatearFecha } from '../../utils/format';
import { parsearFecha } from '../../utils/fechas';
import { esCelular } from '../../utils/dispositivo';
import { InfoPill } from '../rutinas/InfoPill';
import { ArmarMiRutina } from './ArmarMiRutina';
import { CatalogoEjercicios } from './CatalogoEjercicios';
import { CircuitoView } from './CircuitoView';
import { ContadorReps } from './ContadorReps';
import { MiEntrenadorCard } from './MiEntrenadorCard';
import { SinSocioEnSesion } from './SinSocioEnSesion';
import { VerTecnica } from './VerTecnica';

// Vista 2 del portal (docs/prompt_portal_socio.md). SOLO LECTURA: no hay un
// solo botón que modifique nada.
//
// Sobre "reutilizá la misma card de rutina del admin": se reutilizan sus
// PIEZAS (LevelBadge, InfoPill, SectionCard) pero no el componente
// RutinaCard entero, y vale la pena decir por qué. RutinaCard muestra
// "Asignados: N socios" con una barra de ocupación sobre la capacidad de la
// rutina — es información de gestión del gimnasio, no del socio. A él no le
// aporta nada saber que otras 12 personas hacen su mismo plan, y es
// exactamente el tipo de dato que no debería cruzar la frontera del portal.
// También traería "Ver detalles" y "Asignar", que acá no tienen sentido.
//
// El resultado se ve como la card del admin porque usa los mismos ladrillos,
// que es lo que el prompt busca; lo que no arrastra es la parte de gestión.

const DIAS_SEMANA = ['Día 1', 'Día 2', 'Día 3', 'Día 4', 'Día 5', 'Día 6', 'Día 7'];

/**
 * El descanso se guarda en segundos; acá se muestra como se dice en un
 * gimnasio: "45 seg", "2 min", "1 min 30".
 *
 * Nada de dividir y mostrar el decimal: 90 segundos son "1 min 30", no
 * "1.5 min" — nadie cuenta descansos en minutos fraccionados.
 */
function formatearDescanso(segundos: number): string {
  if (segundos < 60) return `${segundos} seg`;
  const minutos = Math.floor(segundos / 60);
  const resto = segundos % 60;
  return resto === 0 ? `${minutos} min` : `${minutos} min ${resto}`;
}

function FilaEjercicio({ ejercicio }: { ejercicio: EjercicioDelDia }) {
  const [viendo, setViendo] = useState(false);
  return (
    <div className="flex flex-col gap-2 py-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
      {viendo && ejercicio.video && (
        <VerTecnica nombre={ejercicio.nombre} video={ejercicio.video} onCerrar={() => setViendo(false)} />
      )}
      <div className="min-w-0">
        <p className="font-body text-sm text-text-main">{ejercicio.nombre}</p>
        <p className="font-body text-xs text-text-muted">{ejercicio.grupoMuscular}</p>
        {ejercicio.observaciones && (
          <p className="mt-1 font-body text-xs text-status-warn">{ejercicio.observaciones}</p>
        )}
        {ejercicio.video && (
          <button
            type="button"
            onClick={() => setViendo(true)}
            className="mt-2 flex shrink-0 items-center gap-1.5 rounded-md border border-border-idle px-3 py-1.5 font-body text-xs whitespace-nowrap text-primary-volt"
          >
            <PlayCircle size={14} /> Ver técnica
          </button>
        )}
      </div>

      {/* Las cifras en font-mono, igual que el resto de las métricas de la
          app (DESIGN.md §6): así se leen alineadas de un vistazo entre
          ejercicio y ejercicio. */}
      <div className="flex shrink-0 flex-wrap items-center gap-x-4 gap-y-1 font-mono text-xs text-text-secondary">
        {ejercicio.series !== undefined && ejercicio.repeticiones && (
          <span className="text-text-main">
            {ejercicio.series} × {ejercicio.repeticiones}
          </span>
        )}
        {/* Series sin reps (o al revés) es raro pero posible: las dos
            columnas son nullable en el esquema. Se muestra lo que haya en
            vez de esconder la fila entera. */}
        {ejercicio.series !== undefined && !ejercicio.repeticiones && (
          <span className="text-text-main">{ejercicio.series} series</span>
        )}
        {ejercicio.series === undefined && ejercicio.repeticiones && (
          <span className="text-text-main">{ejercicio.repeticiones}</span>
        )}
        {ejercicio.pesoSugerido !== undefined && <span>{ejercicio.pesoSugerido} kg</span>}
        {ejercicio.descansoSegundos !== undefined && (
          <span className="flex items-center gap-1">
            <Timer size={12} />
            {formatearDescanso(ejercicio.descansoSegundos)}
          </span>
        )}
      </div>
    </div>
  );
}

function Skeleton({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-md bg-surface-hover ${className}`} />;
}

export function MiRutinaView() {
  // El dia que se esta entrenando, o null si se esta mirando la rutina.
  //
  // Vive acá y no en una ruta propia (`/mi-rutina/circuito`) a proposito: el
  // circuito NO es una pantalla a la que se navega, es un modo de esta. Con
  // una ruta, el boton de atras del celular saldria del circuito en medio de
  // una serie, y volver a entrar por la URL sin rutina cargada seria una
  // pantalla vacia que hay que contemplar. Como estado, no existe sin datos.
  const [entrenando, setEntrenando] = useState<DiaDeRutina | null>(null);
  // Contador de reps con cámara: otro MODO de esta pantalla (no una ruta),
  // igual que el circuito. Sólo se ofrece en el celular — ver `esCelular`.
  const [contando, setContando] = useState(false);
  const [puedeContar] = useState(() => esCelular());
  // Armar/rehacer la rutina propia: otro MODO de esta pantalla (no una ruta).
  const [armando, setArmando] = useState(false);
  const [eliminando, setEliminando] = useState(false);
  // Mirar el catálogo de ejercicios suelto: otro MODO, no una ruta.
  const [explorando, setExplorando] = useState(false);

  const idSocio = useAuthStore((s) => s.idSocio);

  const [rutina, setRutina] = useState<MiRutina | null>(null);
  // `cargado` va aparte de `rutina`: null es una respuesta VÁLIDA (el socio
  // no tiene rutina asignada), así que no alcanza con mirar si rutina es
  // null para saber si terminó de cargar. Sin esto, el estado vacío
  // aparecía por un instante en cada carga.
  const [cargado, setCargado] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [intento, setIntento] = useState(0);

  useEffect(() => {
    if (idSocio === null) return;
    let cancelado = false;
    setCargado(false);
    setError(null);
    getMiRutina()
      .then((datos) => {
        if (cancelado) return;
        setRutina(datos);
        setCargado(true);
      })
      .catch((err: unknown) => {
        if (!cancelado) setError(mensajeDeError(err));
      });
    return () => {
      cancelado = true;
    };
  }, [idSocio, intento]);

  const recargar = useCallback(() => setIntento((n) => n + 1), []);

  const eliminarPropia = useCallback(async () => {
    if (eliminando) return;
    setEliminando(true);
    setError(null);
    try {
      await eliminarMiRutinaPropia();
      setRutina(null);
    } catch (err: unknown) {
      setError(mensajeDeError(err));
    } finally {
      setEliminando(false);
    }
  }, [eliminando]);

  if (idSocio === null) {
    return <SinSocioEnSesion titulo="Mi rutina" />;
  }

  // Cuando hay circuito, es LO UNICO que se dibuja: se monta encima de todo
  // (fixed inset-0) y tapa el menu. No se desmonta MiRutinaView por debajo
  // para que al salir la pantalla siga donde estaba, sin volver a pedir la
  // rutina.
  return (
    <div>
      {entrenando && rutina && (
        <CircuitoView
          dia={entrenando}
          idRutina={rutina.idRutina}
          nombreRutina={rutina.nombre}
          etiquetaDia={DIAS_SEMANA[entrenando.dia - 1] ?? `Día ${entrenando.dia}`}
          onSalir={() => setEntrenando(null)}
        />
      )}

      {contando && <ContadorReps onSalir={() => setContando(false)} />}

      {explorando && <CatalogoEjercicios onCerrar={() => setExplorando(false)} />}

      {armando && (
        <ArmarMiRutina
          actual={rutina?.esPropia ? rutina : null}
          onCerrar={() => setArmando(false)}
          onGuardada={(r) => {
            setRutina(r);
            setArmando(false);
          }}
        />
      )}

      <Topbar
        title="Mi rutina"
        subtitle={
          cargado && rutina
            ? rutina.esPropia
              ? 'Te la armaste vos'
              : `Te la armó ${rutina.entrenador}`
            : undefined
        }
      />

      <div className="space-y-4 p-4 md:p-8">
        {error && (
          <SectionCard>
            <p className="mb-4 font-body text-sm text-status-danger">{error}</p>
            <PrimaryButton label="Reintentar" onClick={recargar} />
          </SectionCard>
        )}

        {!error && !cargado && (
          <div className="space-y-4">
            <Skeleton className="h-40" />
            <Skeleton className="h-64" />
          </div>
        )}

        {/* Estado vacío: es un caso normal, no un error. El socio recién
            anotado todavía no tiene rutina y el mensaje tiene que decirle
            qué va a pasar, no sonar a que algo falló. */}
        {/* Fuera de los dos bloques de abajo a proposito: se dibuja tenga o
            no rutina. Un socio recien anotado suele tener entrenador y
            todavia ninguna rutina, y es justo el que mas necesita saber a
            quien preguntarle. */}
        {!error && cargado && <MiEntrenadorCard />}

        {/* Contador de reps con cámara — sólo en el celular (parás el teléfono
            y apuntás). En una compu ni aparece. Prototipo: por ahora abre la
            cámara y te dibuja el cuerpo; el conteo llega en el próximo paso. */}
        {!error && cargado && puedeContar && (
          <SectionCard>
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="font-heading text-base font-semibold text-text-main">
                  Contar repeticiones{' '}
                  <span className="align-middle text-xs font-normal text-primary-volt">
                    beta
                  </span>
                </p>
                <p className="font-body text-xs text-text-secondary">
                  Apoyá el teléfono y la cámara sigue tu movimiento. No sale del dispositivo.
                </p>
              </div>
              <PrimaryButton
                label="Probar"
                icon={Camera}
                onClick={() => setContando(true)}
              />
            </div>
          </SectionCard>
        )}

        {/* El catálogo se ofrece siempre, tenga o no rutina: mirar cómo se
            hace un ejercicio no depende de tener un plan. */}
        {!error && cargado && (
          <SectionCard>
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="font-heading text-base font-semibold text-text-main">
                  Ejercicios del gimnasio
                </p>
                <p className="font-body text-xs text-text-secondary">
                  Mirá cómo se hace cada uno, con video.
                </p>
              </div>
              <PrimaryButton label="Ver" icon={BookOpen} onClick={() => setExplorando(true)} />
            </div>
          </SectionCard>
        )}

        {!error && cargado && !rutina && (
          <SectionCard>
            <div className="flex flex-col items-center gap-3 py-8 text-center">
              <Dumbbell size={32} className="text-text-muted" />
              <p className="font-heading text-lg font-semibold text-text-main">
                Todavía no tenés una rutina asignada
              </p>
              <p className="max-w-md font-body text-sm text-text-secondary">
                Tu entrenador te va a asignar una pronto. Si querés, mientras tanto podés
                armarte una vos mismo.
              </p>
              <button
                type="button"
                onClick={() => setArmando(true)}
                className="mt-2 flex items-center gap-2 rounded-lg bg-primary-volt px-5 py-3 font-body text-base font-semibold whitespace-nowrap text-surface-base active:opacity-90"
              >
                <Sparkles size={18} /> Armar mi rutina
              </button>
            </div>
          </SectionCard>
        )}

        {!error && cargado && rutina && (
          <>
            <SectionCard>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <h2 className="font-heading text-xl font-semibold text-text-main">
                    {rutina.nombre}
                  </h2>
                  {rutina.nivel && (
                    <div className="mt-2">
                      <LevelBadge nivel={rutina.nivel} />
                    </div>
                  )}
                </div>
                <Dumbbell size={20} className="shrink-0 text-primary-volt" />
              </div>

              <div className="mt-4 flex flex-wrap gap-2">
                {rutina.diasPorSemana !== undefined && (
                  <InfoPill icon={Calendar} text={`${rutina.diasPorSemana} días/sem`} />
                )}
                {rutina.objetivo && <InfoPill icon={Target} text={rutina.objetivo} />}
                <InfoPill icon={User} text={rutina.entrenador} />
              </div>

              <p className="mt-4 border-t border-border-idle pt-4 font-body text-xs text-text-muted">
                {rutina.esPropia ? 'La armaste el ' : 'La tenés asignada desde el '}
                {formatearFecha(parsearFecha(rutina.fechaInicio))}.
              </p>

              {/* Editar/eliminar SÓLO en la rutina propia: la del entrenador no
                  la toca el socio. */}
              {rutina.esPropia && (
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => setArmando(true)}
                    className="flex items-center gap-2 rounded-lg border border-border-idle px-4 py-2 font-body text-sm whitespace-nowrap text-text-secondary"
                  >
                    <Pencil size={15} /> Rehacer
                  </button>
                  <button
                    type="button"
                    onClick={() => void eliminarPropia()}
                    disabled={eliminando}
                    className="flex items-center gap-2 rounded-lg border border-border-idle px-4 py-2 font-body text-sm whitespace-nowrap text-status-danger disabled:opacity-40"
                  >
                    <Trash2 size={15} /> {eliminando ? 'Eliminando…' : 'Eliminar'}
                  </button>
                </div>
              )}

              {/* La rutina se dio de baja pero la asignación sigue viva: el
                  socio tiene que saberlo, no descubrirlo entrenando. */}
              {rutina.rutinaDeBaja && (
                <div
                  className="mt-4 flex items-start gap-3 rounded-lg border px-4 py-3"
                  style={{
                    borderColor: colors.statusWarn,
                    backgroundColor: `${colors.statusWarn}14`,
                  }}
                >
                  <AlertTriangle size={16} color={colors.statusWarn} className="mt-0.5 shrink-0" />
                  <p className="font-body text-sm text-text-main">
                    El gimnasio dio de baja este plan. Podés seguir usándolo, pero consultá con tu
                    entrenador si te conviene pasar a uno nuevo.
                  </p>
                </div>
              )}
            </SectionCard>

            {/* Sin ejercicios cargados: la rutina existe pero el entrenador
                todavía no le puso contenido. Distinto de "no tenés rutina". */}
            {rutina.dias.length === 0 ? (
              <SectionCard title="Ejercicios">
                <p className="font-body text-sm text-text-muted">
                  Tu entrenador todavía no cargó los ejercicios de este plan.
                </p>
              </SectionCard>
            ) : (
              rutina.dias.map((dia) => (
                <SectionCard key={dia.dia} title={DIAS_SEMANA[dia.dia - 1] ?? `Día ${dia.dia}`}>
                  {/* Arriba de los ejercicios y ocupando todo el ancho: es la
                      acción principal de la pantalla en el gimnasio, y quien
                      llega hasta acá ya sabe qué le toca hoy. Enterrarlo al
                      final obligaría a scrollear siete ejercicios para
                      empezar. */}
                  <button
                    type="button"
                    onClick={() => setEntrenando(dia)}
                    className="mb-4 flex w-full items-center justify-center gap-2 rounded-lg bg-primary-volt py-3.5 font-body text-base font-semibold whitespace-nowrap text-surface-base active:opacity-90"
                  >
                    <Play size={18} />
                    Comenzar entrenamiento
                  </button>

                  <div className="flex flex-col divide-y divide-border-idle">
                    {dia.ejercicios.map((ejercicio) => (
                      <FilaEjercicio key={ejercicio.idRutinaEjercicio} ejercicio={ejercicio} />
                    ))}
                  </div>
                </SectionCard>
              ))
            )}
          </>
        )}
      </div>
    </div>
  );
}
