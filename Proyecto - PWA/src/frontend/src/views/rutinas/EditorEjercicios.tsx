import { useMemo, useState, type Dispatch, type SetStateAction } from 'react';
import { ArrowDown, ArrowUp, Check, PlayCircle, Plus, Search, Trash2 } from 'lucide-react';
import type { EjercicioCatalogo } from '../../services/socioService';
import { VerTecnica } from '../socio/VerTecnica';
import { agruparCatalogo, nuevoItem, type ItemEjercicio } from './planillaEjercicios';

// =============================================================================
// EDITOR DE EJERCICIOS POR DÍA — compartido por el entrenador y el socio
// =============================================================================
// La planilla de una rutina: pestañas por día y, en cada una, los ejercicios
// elegidos del catálogo con series, reps, peso, descanso y observaciones.
//
// Lo usan dos pantallas que tienen que armar exactamente lo mismo:
//   - RutinaFormModal: el entrenador arma o edita una rutina del gimnasio.
//   - ArmarMiRutina: el socio se arma la suya.
// Tenerlo en un solo lugar evita que una de las dos se quede atrás (la del
// socio arrancó con un solo día y sin peso).
//
// El editor no guarda nada: maneja la lista y `armarEjercicios`
// (planillaEjercicios.ts) la convierte en lo que espera el backend al guardar.

type CampoEditable = 'series' | 'repeticiones' | 'peso' | 'descanso' | 'observaciones';

interface EditorEjerciciosProps {
  items: ItemEjercicio[];
  setItems: Dispatch<SetStateAction<ItemEjercicio[]>>;
  /** Días por semana: cuántas pestañas hay. */
  dias: number;
  catalogo: EjercicioCatalogo[] | null;
  errorCatalogo: string | null;
  /** Mientras se traen los ejercicios de una rutina que se está editando. */
  cargando?: boolean;
}

export function EditorEjercicios({
  items,
  setItems,
  dias,
  catalogo,
  errorCatalogo,
  cargando = false,
}: EditorEjerciciosProps) {
  const [diaActivo, setDiaActivo] = useState(1);
  const [eligiendo, setEligiendo] = useState(false);

  // Si bajaron los días por semana, la pestaña activa no puede quedar afuera.
  const dia = Math.min(diaActivo, dias);
  const delDia = items.filter((i) => i.dia === dia);
  const idsDelDia = useMemo(
    () => new Set(items.filter((i) => i.dia === dia).map((i) => i.idEjercicio)),
    [items, dia],
  );
  const fueraDeRango = items.filter((i) => i.dia > dias).length;

  const alternar = (ej: EjercicioCatalogo) => {
    if (idsDelDia.has(ej.idEjercicio)) {
      setItems((xs) => xs.filter((i) => !(i.dia === dia && i.idEjercicio === ej.idEjercicio)));
      return;
    }
    setItems((xs) => [...xs, nuevoItem({ ...ej, dia })]);
  };

  const quitar = (clave: number) => setItems((xs) => xs.filter((i) => i.clave !== clave));

  const cambiar = (clave: number, campo: CampoEditable, valor: string) =>
    setItems((xs) => xs.map((i) => (i.clave === clave ? { ...i, [campo]: valor } : i)));

  /** Sube o baja un ejercicio DENTRO de su día. */
  const mover = (clave: number, delta: -1 | 1) =>
    setItems((xs) => {
      const i = xs.findIndex((x) => x.clave === clave);
      if (i < 0) return xs;
      let j = i + delta;
      while (j >= 0 && j < xs.length && xs[j].dia !== xs[i].dia) j += delta;
      if (j < 0 || j >= xs.length) return xs;
      const copia = [...xs];
      [copia[i], copia[j]] = [copia[j], copia[i]];
      return copia;
    });

  return (
    <div className="space-y-3">
      {eligiendo && (
        <PickerCatalogo
          titulo={`Día ${dia}: elegí ejercicios`}
          catalogo={catalogo}
          error={errorCatalogo}
          agregados={idsDelDia}
          onToggle={alternar}
          onListo={() => setEligiendo(false)}
        />
      )}

      <div className="flex flex-wrap gap-2">
        {Array.from({ length: dias }, (_, i) => i + 1).map((d) => {
          const cantidad = items.filter((it) => it.dia === d).length;
          return (
            <button
              key={d}
              type="button"
              onClick={() => setDiaActivo(d)}
              className={`shrink-0 rounded-full px-3 py-1.5 font-body text-sm whitespace-nowrap ring-1 ${
                d === dia
                  ? 'bg-primary-volt text-surface-base ring-primary-volt'
                  : 'bg-surface-base text-text-secondary ring-border-idle'
              }`}
            >
              Día {d}
              {cantidad > 0 && <span className="ml-1 opacity-70">({cantidad})</span>}
            </button>
          );
        })}
      </div>

      {cargando ? (
        <p className="font-body text-sm text-text-muted">Cargando ejercicios…</p>
      ) : delDia.length === 0 ? (
        <p className="rounded-lg border border-dashed border-border-idle px-4 py-6 text-center font-body text-sm text-text-muted">
          El Día {dia} todavía no tiene ejercicios.
        </p>
      ) : (
        delDia.map((it, idx) => (
          <div key={it.clave} className="rounded-lg bg-surface-base p-3 ring-1 ring-border-idle">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="truncate font-body text-sm font-medium text-text-main">
                  {idx + 1}. {it.nombre}
                </p>
                <p className="font-body text-xs text-text-muted">{it.grupoMuscular}</p>
              </div>
              <div className="flex shrink-0 items-center">
                <button
                  type="button"
                  onClick={() => mover(it.clave, -1)}
                  disabled={idx === 0}
                  aria-label="Subir"
                  className="rounded-md p-1.5 text-text-muted hover:text-text-main disabled:opacity-30"
                >
                  <ArrowUp size={16} />
                </button>
                <button
                  type="button"
                  onClick={() => mover(it.clave, 1)}
                  disabled={idx === delDia.length - 1}
                  aria-label="Bajar"
                  className="rounded-md p-1.5 text-text-muted hover:text-text-main disabled:opacity-30"
                >
                  <ArrowDown size={16} />
                </button>
                <button
                  type="button"
                  onClick={() => quitar(it.clave)}
                  aria-label="Quitar"
                  className="rounded-md p-1.5 text-text-muted hover:text-status-danger"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>

            <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
              <CampoMini
                etiqueta="Series"
                value={it.series}
                onChange={(v) => cambiar(it.clave, 'series', v)}
                placeholder="4"
              />
              <CampoMini
                etiqueta="Reps"
                value={it.repeticiones}
                onChange={(v) => cambiar(it.clave, 'repeticiones', v.slice(0, 20))}
                placeholder="8-12"
                texto
              />
              <CampoMini
                etiqueta="Peso (kg)"
                value={it.peso}
                onChange={(v) => cambiar(it.clave, 'peso', v)}
                placeholder="40"
              />
              <CampoMini
                etiqueta="Descanso (s)"
                value={it.descanso}
                onChange={(v) => cambiar(it.clave, 'descanso', v)}
                placeholder="60"
              />
            </div>
            <input
              type="text"
              value={it.observaciones}
              onChange={(e) => cambiar(it.clave, 'observaciones', e.target.value)}
              placeholder="Observaciones (opcional)"
              className="mt-2 w-full rounded-md bg-surface-card px-2 py-1.5 font-body text-sm text-text-main outline-none ring-1 ring-border-idle placeholder:text-text-muted focus:ring-primary-volt"
            />
          </div>
        ))
      )}

      <button
        type="button"
        onClick={() => setEligiendo(true)}
        disabled={cargando}
        className="flex w-full items-center justify-center gap-2 rounded-lg border border-border-idle py-3 font-body text-sm font-medium whitespace-nowrap text-text-secondary hover:bg-surface-hover disabled:opacity-40"
      >
        <Plus size={16} /> Agregar ejercicios al Día {dia}
      </button>

      {fueraDeRango > 0 && (
        <p className="font-body text-xs text-status-warn">
          Hay {fueraDeRango} ejercicio(s) en días que quedaron fuera de los {dias} días por semana.
        </p>
      )}
    </div>
  );
}

// -----------------------------------------------------------------------------

export function CampoMini({
  etiqueta,
  value,
  onChange,
  placeholder,
  texto = false,
}: {
  etiqueta: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  texto?: boolean;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="font-body text-[10px] uppercase tracking-wide text-text-muted">{etiqueta}</span>
      <input
        type="text"
        inputMode={texto ? 'text' : 'decimal'}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-md bg-surface-card px-2 py-1.5 text-center font-mono text-sm text-text-main outline-none ring-1 ring-border-idle focus:ring-primary-volt"
      />
    </label>
  );
}

// -----------------------------------------------------------------------------

/**
 * El catálogo a pantalla completa, agrupado por músculo y con buscador. Tocar
 * un ejercicio lo agrega o lo quita; el ▶ muestra la técnica antes de elegirlo.
 */
export function PickerCatalogo({
  titulo = 'Elegí ejercicios',
  catalogo,
  error,
  agregados,
  onToggle,
  onListo,
}: {
  titulo?: string;
  catalogo: EjercicioCatalogo[] | null;
  error: string | null;
  agregados: Set<number>;
  onToggle: (ej: EjercicioCatalogo) => void;
  onListo: () => void;
}) {
  const [busqueda, setBusqueda] = useState('');
  const [viendo, setViendo] = useState<EjercicioCatalogo | null>(null);

  const grupos = useMemo(() => agruparCatalogo(catalogo, busqueda), [catalogo, busqueda]);

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-surface-base">
      {viendo?.video && (
        <VerTecnica nombre={viendo.nombre} video={viendo.video} onCerrar={() => setViendo(null)} />
      )}
      <header className="flex shrink-0 items-center justify-between gap-3 border-b border-border-idle px-4 py-3">
        <p className="min-w-0 truncate font-heading text-lg font-semibold text-text-main">{titulo}</p>
        <button
          type="button"
          onClick={onListo}
          className="shrink-0 rounded-lg bg-primary-volt px-4 py-1.5 font-body text-sm font-semibold whitespace-nowrap text-surface-base"
        >
          Listo {agregados.size > 0 && `(${agregados.size})`}
        </button>
      </header>

      <div className="shrink-0 px-4 py-3">
        <Buscador value={busqueda} onChange={setBusqueda} />
      </div>

      <div className="min-h-0 flex-1 space-y-5 overflow-y-auto overscroll-contain px-4 pb-6">
        {error && <p className="font-body text-sm text-status-danger">{error}</p>}
        {!catalogo && !error && <p className="font-body text-sm text-text-muted">Cargando catálogo…</p>}
        {catalogo && grupos.length === 0 && (
          <p className="font-body text-sm text-text-muted">No hay ejercicios que coincidan.</p>
        )}

        {grupos.map(([grupo, ejercicios]) => (
          <div key={grupo} className="space-y-2">
            <p className="font-body text-xs font-semibold uppercase tracking-wide text-text-muted">
              {grupo}
            </p>
            <div className="space-y-1.5">
              {ejercicios.map((e) => {
                const puesto = agregados.has(e.idEjercicio);
                return (
                  <div
                    key={e.idEjercicio}
                    className={`flex items-center gap-1 rounded-lg ring-1 transition-colors ${
                      puesto ? 'bg-primary-volt/10 ring-primary-volt' : 'bg-surface-card ring-border-idle'
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => onToggle(e)}
                      className="flex min-w-0 flex-1 items-center justify-between gap-2 px-3 py-2.5 text-left"
                    >
                      <span className="min-w-0 truncate font-body text-sm text-text-main">{e.nombre}</span>
                      <span
                        className={`flex size-5 shrink-0 items-center justify-center rounded-full ${
                          puesto ? 'bg-primary-volt text-surface-base' : 'border border-border-idle'
                        }`}
                      >
                        {puesto ? <Check size={14} /> : <Plus size={14} className="text-text-muted" />}
                      </span>
                    </button>
                    {e.video && (
                      <button
                        type="button"
                        onClick={() => setViendo(e)}
                        aria-label={`Ver técnica de ${e.nombre}`}
                        className="shrink-0 rounded-md p-2 text-primary-volt"
                      >
                        <PlayCircle size={18} />
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// -----------------------------------------------------------------------------

export function Buscador({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <div className="flex items-center gap-2 rounded-lg bg-surface-card px-3 py-2 ring-1 ring-border-idle focus-within:ring-primary-volt">
      <Search size={16} className="shrink-0 text-text-muted" />
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Buscar ejercicio o grupo…"
        className="w-full bg-transparent font-body text-sm text-text-main outline-none"
      />
    </div>
  );
}
