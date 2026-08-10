import { useCallback, useEffect, useState, type SubmitEvent } from 'react';
import { Activity, Percent, Scale, TrendingUp } from 'lucide-react';
import {
  InputField,
  PrimaryButton,
  SectionCard,
  StatCard,
  Topbar,
} from '../../components/ui';
import { colors } from '../../config';
import { mensajeDeError } from '../../services/api';
import {
  getMiProgreso,
  guardarMedicion,
  type MedicionListada,
  type MiProgreso,
} from '../../services/socioService';
import { useAuthStore } from '../../store/authStore';
import { useUiStore } from '../../store/uiStore';
import { formatearFecha, formatearFechaCorta } from '../../utils/format';
import { parsearFecha } from '../../utils/fechas';
import { SinSocioEnSesion } from './SinSocioEnSesion';

// Vista 3 del portal (docs/prompt_portal_socio.md). El ÚNICO lugar donde el
// socio carga datos.
//
// Reutiliza StatCard (el mismo del dashboard y de nutrición) e InputField.
// El gráfico de evolución no usa ninguna librería: son divs con altura
// proporcional, el mismo recurso que la barra de ocupación de RutinaCard.
// Meter una librería de charts para siete puntos sería traer 40 kB para
// dibujar lo que resuelve un flex con alturas en porcentaje.

/**
 * Altura mínima de una barra, en % del alto del gráfico. Sin esto, el peso
 * más bajo del historial queda en 0 y parece que ese día el socio no cargó
 * nada, cuando es justo el mejor dato de la serie.
 */
const ALTURA_MINIMA_BARRA = 8;

interface GraficoProps {
  mediciones: MedicionListada[];
}

/**
 * Barras de evolución del peso. La escala NO arranca en cero a propósito:
 * entre 81 y 86 kg, un eje desde 0 daría siete barras casi idénticas y no
 * se vería ningún cambio. Se normaliza contra el rango real de la serie,
 * que es lo que hace visible la progresión.
 */
function GraficoDePeso({ mediciones }: GraficoProps) {
  const conPeso = mediciones.filter(
    (m): m is MedicionListada & { peso: number } => m.peso !== undefined,
  );

  if (conPeso.length < 2) {
    return (
      <p className="font-body text-sm text-text-muted">
        Con una sola medición todavía no hay evolución para mostrar. Cargá la próxima y acá vas a
        ver la curva.
      </p>
    );
  }

  const pesos = conPeso.map((m) => m.peso);
  const minimo = Math.min(...pesos);
  const maximo = Math.max(...pesos);
  // Serie plana (todas iguales): sin rango, la normalización dividiría por
  // cero. Se dibujan todas a media altura.
  const rango = maximo - minimo;

  return (
    <div>
      <div className="flex h-40 items-end gap-2">
        {conPeso.map((m) => {
          const proporcion = rango === 0 ? 0.5 : (m.peso - minimo) / rango;
          const alto = ALTURA_MINIMA_BARRA + proporcion * (100 - ALTURA_MINIMA_BARRA);
          return (
            // h-full y justify-end en la columna: sin una altura DEFINIDA en
            // el padre, el `height: X%` de la barra no resuelve contra nada
            // y el navegador lo trata como auto — las barras no se dibujaban
            // y el gráfico se veía como una fila de números flotando. El
            // contenedor de arriba tiene h-40, así que h-full acá le da a la
            // columna una altura concreta contra la cual calcular el %.
            <div
              key={m.idRegistroSalud}
              className="flex h-full flex-1 flex-col items-center justify-end gap-1.5"
            >
              <span className="font-mono text-[10px] text-text-secondary">{m.peso}</span>
              <div
                className="w-full rounded-t-sm bg-primary-volt/70 transition-[height]"
                style={{ height: `${alto}%` }}
                // El title da el dato exacto al pasar el mouse: la etiqueta
                // de arriba se recorta en pantallas chicas.
                title={`${m.peso} kg el ${formatearFechaCorta(parsearFecha(m.fecha))}`}
              />
            </div>
          );
        })}
      </div>
      <div className="mt-2 flex gap-2 border-t border-border-idle pt-2">
        {conPeso.map((m) => (
          <span
            key={m.idRegistroSalud}
            className="flex-1 text-center font-body text-[10px] text-text-muted"
          >
            {formatearFechaCorta(parsearFecha(m.fecha))}
          </span>
        ))}
      </div>
    </div>
  );
}

function Skeleton({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-md bg-surface-hover ${className}`} />;
}

export function MiProgresoView() {
  const idSocio = useAuthStore((s) => s.idSocio);
  const showSnack = useUiStore((s) => s.showSnack);

  const [progreso, setProgreso] = useState<MiProgreso | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intento, setIntento] = useState(0);
  const [guardando, setGuardando] = useState(false);

  const [peso, setPeso] = useState('');
  const [altura, setAltura] = useState('');
  const [grasa, setGrasa] = useState('');
  const [masaMuscular, setMasaMuscular] = useState('');
  const [observaciones, setObservaciones] = useState('');

  useEffect(() => {
    if (idSocio === null) return;
    let cancelado = false;
    setProgreso(null);
    setError(null);
    getMiProgreso()
      .then((datos) => {
        if (cancelado) return;
        setProgreso(datos);
        // La altura se precarga con la última conocida: no cambia entre
        // mediciones y hacerla tipear cada vez es la forma más rápida de
        // que el socio la deje vacía para siempre.
        setAltura((actual) => actual || (datos.altura !== undefined ? String(datos.altura) : ''));
      })
      .catch((err: unknown) => {
        if (!cancelado) setError(mensajeDeError(err));
      });
    return () => {
      cancelado = true;
    };
  }, [idSocio, intento]);

  const recargar = useCallback(() => setIntento((n) => n + 1), []);

  const handleSubmit = async (e: SubmitEvent) => {
    e.preventDefault();
    if (idSocio === null) return;
    setGuardando(true);
    try {
      // Los inputs devuelven string; el service quiere números. Los campos
      // opcionales vacíos van como undefined y no como NaN, que pasaría el
      // chequeo de "está definido" y rompería la validación de rango.
      const aNumero = (valor: string) => (valor.trim() === '' ? undefined : Number(valor));
      await guardarMedicion({
          peso: Number(peso),
          altura: aNumero(altura),
          grasaCorporal: aNumero(grasa),
          masaMuscular: aNumero(masaMuscular),
          observaciones,
        }
      );
      // guardarMedicion no devuelve el progreso completo: los resúmenes
      // (peso actual, variación, altura) los calcula el servidor sobre la
      // serie entera, así que se vuelve a pedir en vez de recalcularlos acá.
      setProgreso(await getMiProgreso());
      // Se limpia lo que es de HOY y se conserva la altura, que sirve para
      // la próxima.
      setPeso('');
      setGrasa('');
      setMasaMuscular('');
      setObservaciones('');
      showSnack('Listo, guardamos tu medición de hoy', colors.statusOk);
    } catch (err) {
      showSnack(mensajeDeError(err), colors.statusDanger);
    } finally {
      setGuardando(false);
    }
  };

  if (idSocio === null) {
    return <SinSocioEnSesion titulo="Mi progreso" />;
  }

  const variacion = progreso?.variacionPeso;
  const bajo = variacion !== undefined && variacion < 0;

  return (
    <div>
      <Topbar
        title="Mi progreso"
        subtitle={
          progreso ? `${progreso.mediciones.length} mediciones registradas` : undefined
        }
      />

      <div className="space-y-4 p-8">
        {error && (
          <SectionCard>
            <p className="mb-4 font-body text-sm text-status-danger">{error}</p>
            <PrimaryButton label="Reintentar" onClick={recargar} />
          </SectionCard>
        )}

        {!error && !progreso && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-28" />
              ))}
            </div>
            <Skeleton className="h-64" />
          </div>
        )}

        {!error && progreso && (
          <>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <StatCard
                title="Peso actual"
                value={progreso.pesoActual !== undefined ? `${progreso.pesoActual} kg` : '—'}
                icon={Scale}
                color={colors.primaryVolt}
                // El delta sólo aparece si hay contra qué comparar.
                delta={
                  variacion !== undefined
                    ? `${variacion > 0 ? '+' : ''}${variacion} kg desde que empezaste`
                    : undefined
                }
                // La flecha sigue la dirección real del cambio, pero el
                // color no: en el peso de alguien que entrena, bajar es el
                // objetivo. Ver deltaEsBueno en StatCard.
                //
                // Ojo: esto asume que TODO socio quiere bajar de peso, y no
                // es cierto —el que hace volumen quiere lo contrario—. El
                // dato que lo resolvería bien es el objetivo del socio
                // (Socio.objetivo existe en el esquema, hoy vacío en el
                // seed). Hasta que se cargue, se toma el caso mayoritario en
                // un gimnasio y se deja escrito acá que es una suposición.
                tendencia={bajo ? 'down' : 'up'}
                deltaEsBueno={bajo}
              />
              <StatCard
                title="Grasa corporal"
                value={progreso.grasaActual !== undefined ? `${progreso.grasaActual} %` : '—'}
                icon={Percent}
                color={colors.accentCoral}
              />
              <StatCard
                title="Mediciones"
                value={`${progreso.mediciones.length}`}
                icon={Activity}
                color={colors.statusOk}
              />
            </div>

            <SectionCard title="Evolución del peso">
              <GraficoDePeso mediciones={progreso.mediciones} />
            </SectionCard>

            <form onSubmit={handleSubmit}>
              <SectionCard title="Cargar medición de hoy">
                {progreso.yaCargoHoy ? (
                  // Ya cargó hoy: se dice antes de que complete el form y se
                  // lleve el rechazo después de tipear todo. El unique del
                  // esquema es (id_socio, fecha) — una por día.
                  <div className="flex items-start gap-3">
                    <TrendingUp size={16} color={colors.statusOk} className="mt-0.5 shrink-0" />
                    <div>
                      <p className="font-body text-sm text-text-main">
                        Ya cargaste tu medición de hoy.
                      </p>
                      <p className="mt-1 font-body text-sm text-text-secondary">
                        Se registra una por día. Volvé mañana para cargar la próxima.
                      </p>
                    </div>
                  </div>
                ) : (
                  <>
                    <p className="mb-5 font-body text-sm text-text-secondary">
                      Pesate siempre en condiciones parecidas (misma hora, antes de entrenar) para
                      que la comparación sirva de algo. Sólo el peso es obligatorio.
                    </p>

                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                      <InputField
                        label="Peso (kg)"
                        value={peso}
                        onChange={setPeso}
                        icon={Scale}
                        type="number"
                        name="peso"
                        required
                      />
                      <InputField
                        label="Altura (m)"
                        value={altura}
                        onChange={setAltura}
                        type="number"
                        name="altura"
                        hint="Ej: 1.78"
                      />
                      <InputField
                        label="Grasa corporal (%)"
                        value={grasa}
                        onChange={setGrasa}
                        type="number"
                        name="grasa_corporal"
                      />
                      <InputField
                        label="Masa muscular (kg)"
                        value={masaMuscular}
                        onChange={setMasaMuscular}
                        type="number"
                        name="masa_muscular"
                      />
                    </div>

                    <div className="mt-4">
                      <InputField
                        label="Notas"
                        value={observaciones}
                        onChange={setObservaciones}
                        name="observaciones"
                        hint="Opcional. Ej: semana de vacaciones, vuelvo de una lesión."
                      />
                    </div>

                    <div className="mt-6 flex justify-end">
                      <PrimaryButton
                        label={guardando ? 'Guardando…' : 'Guardar medición'}
                        type="submit"
                        disabled={guardando}
                      />
                    </div>
                  </>
                )}
              </SectionCard>
            </form>

            {progreso.mediciones.length > 0 && (
              <SectionCard title="Historial">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-border-idle">
                        {['Fecha', 'Peso', 'Grasa', 'Músculo', 'Notas'].map((h) => (
                          <th
                            key={h}
                            className="py-2 pr-4 text-left font-body text-xs font-semibold tracking-wide text-text-secondary uppercase"
                          >
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {/* Al revés que el gráfico: la más nueva arriba, que es
                          la que el socio viene a mirar. */}
                      {[...progreso.mediciones].reverse().map((m) => (
                        <tr
                          key={m.idRegistroSalud}
                          className="border-b border-border-idle last:border-b-0"
                        >
                          {/* La tabla sí lleva el año (el historial puede
                              cruzar de año); el eje del gráfico se queda con
                              el formato corto por espacio. */}
                          <td className="py-2 pr-4 font-body text-sm text-text-main">
                            {formatearFecha(parsearFecha(m.fecha))}
                          </td>
                          <td className="py-2 pr-4 font-mono text-sm text-text-secondary">
                            {m.peso !== undefined ? `${m.peso} kg` : '—'}
                          </td>
                          <td className="py-2 pr-4 font-mono text-sm text-text-secondary">
                            {m.grasaCorporal !== undefined ? `${m.grasaCorporal} %` : '—'}
                          </td>
                          <td className="py-2 pr-4 font-mono text-sm text-text-secondary">
                            {m.masaMuscular !== undefined ? `${m.masaMuscular} kg` : '—'}
                          </td>
                          <td className="py-2 pr-4 font-body text-sm text-text-muted">
                            {m.observaciones || '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </SectionCard>
            )}
          </>
        )}
      </div>
    </div>
  );
}
