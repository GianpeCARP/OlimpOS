import { useEffect, useMemo, useState } from 'react';
import { Check, GripVertical, Plus, Search, Trash2, X } from 'lucide-react';
import { ServiceError, mensajeDeError } from '../../services/api';
import {
  crearMiRutinaPropia,
  listarEjerciciosCatalogo,
  type EjercicioCatalogo,
  type MiRutina,
} from '../../services/socioService';

// =============================================================================
// ARMAR MI RUTINA — el socio se arma su propia rutina (id_entrenador NULL)
// =============================================================================
// MODO de "Mi rutina" (fixed inset-0), no una ruta: el botón de atrás del
// celular no puede dejarte a mitad de armado. Un día, lista de ejercicios: el
// backend soporta varios días, pero para el socio arrancamos simple.
//
// Al guardar, el backend crea la rutina y se la autoasigna. Si ya tiene una del
// ENTRENADOR activa, rechaza con 409 y acá se explica (la del profe manda).

interface ItemRutina {
  ejercicio: EjercicioCatalogo;
  // Strings: son inputs. Se parsean al guardar. Vacío = no cargado.
  series: string;
  repeticiones: string;
  descanso: string;
}

interface ArmarMiRutinaProps {
  onCerrar: () => void;
  onGuardada: (rutina: MiRutina) => void;
}

export function ArmarMiRutina({ onCerrar, onGuardada }: ArmarMiRutinaProps) {
  const [nombre, setNombre] = useState('');
  const [objetivo, setObjetivo] = useState('');
  const [items, setItems] = useState<ItemRutina[]>([]);

  const [catalogo, setCatalogo] = useState<EjercicioCatalogo[] | null>(null);
  const [errorCatalogo, setErrorCatalogo] = useState<string | null>(null);
  const [eligiendo, setEligiendo] = useState(false);

  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelado = false;
    listarEjerciciosCatalogo()
      .then((c) => { if (!cancelado) setCatalogo(c); })
      .catch((e: unknown) => { if (!cancelado) setErrorCatalogo(mensajeDeError(e)); });
    return () => { cancelado = true; };
  }, []);

  const idsAgregados = useMemo(
    () => new Set(items.map((i) => i.ejercicio.idEjercicio)),
    [items],
  );

  const agregar = (ej: EjercicioCatalogo) => {
    if (idsAgregados.has(ej.idEjercicio)) {
      // Ya está: tocar de nuevo lo quita (toggle), así el picker sirve para las dos cosas.
      setItems((xs) => xs.filter((i) => i.ejercicio.idEjercicio !== ej.idEjercicio));
      return;
    }
    setItems((xs) => [...xs, { ejercicio: ej, series: '', repeticiones: '', descanso: '' }]);
  };

  const quitar = (id: number) =>
    setItems((xs) => xs.filter((i) => i.ejercicio.idEjercicio !== id));

  const cambiar = (id: number, campo: keyof Omit<ItemRutina, 'ejercicio'>, valor: string) =>
    setItems((xs) => xs.map((i) => (i.ejercicio.idEjercicio === id ? { ...i, [campo]: valor } : i)));

  const puedeGuardar = nombre.trim().length > 0 && items.length > 0 && !guardando;

  const guardar = async () => {
    if (!puedeGuardar) return;
    setGuardando(true);
    setError(null);
    try {
      const rutina = await crearMiRutinaPropia({
        nombre,
        objetivo: objetivo || undefined,
        // Un día, ejercicios en el orden en que los fue agregando.
        diasPorSemana: 1,
        ejercicios: items.map((i, idx) => ({
          idEjercicio: i.ejercicio.idEjercicio,
          dia: 1,
          orden: idx + 1,
          series: i.series ? Number(i.series) : undefined,
          repeticiones: i.repeticiones || undefined,
          descansoSegundos: i.descanso ? Number(i.descanso) : undefined,
        })),
      });
      onGuardada(rutina);
    } catch (e: unknown) {
      // El 409 es el caso esperado: ya tiene una rutina del entrenador. Se
      // muestra el mensaje del backend, que ya lo explica bien.
      if (e instanceof ServiceError && e.status === 409) {
        setError(e.message);
      } else {
        setError(mensajeDeError(e));
      }
      setGuardando(false);
    }
  };

  // ==========================================================================
  // PICKER DEL CATÁLOGO
  // ==========================================================================
  if (eligiendo) {
    return (
      <PickerCatalogo
        catalogo={catalogo}
        error={errorCatalogo}
        agregados={idsAgregados}
        onToggle={agregar}
        onListo={() => setEligiendo(false)}
      />
    );
  }

  // ==========================================================================
  // ARMADOR
  // ==========================================================================
  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-surface-base">
      <header className="flex shrink-0 items-center justify-between border-b border-border-idle px-4 py-3">
        <p className="font-heading text-lg font-semibold text-text-main">Armar mi rutina</p>
        <button
          type="button"
          onClick={onCerrar}
          aria-label="Cerrar"
          className="flex size-10 items-center justify-center rounded-full bg-surface-card text-text-main"
        >
          <X size={20} />
        </button>
      </header>

      <div className="flex-1 space-y-5 overflow-y-auto overscroll-contain px-4 py-5">
        {/* Nombre + objetivo */}
        <div className="space-y-3">
          <label className="flex flex-col gap-1">
            <span className="font-body text-xs font-medium uppercase tracking-wide text-text-muted">
              Nombre de tu rutina
            </span>
            <input
              type="text"
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              placeholder="Ej: Fuerza — Lunes/Miércoles"
              maxLength={100}
              className="rounded-lg bg-surface-card px-3 py-2.5 font-body text-base text-text-main outline-none ring-1 ring-border-idle focus:ring-primary-volt"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="font-body text-xs font-medium uppercase tracking-wide text-text-muted">
              Objetivo <span className="normal-case text-text-muted/70">(opcional)</span>
            </span>
            <input
              type="text"
              value={objetivo}
              onChange={(e) => setObjetivo(e.target.value)}
              placeholder="Ej: Ganar fuerza en pecho"
              maxLength={100}
              className="rounded-lg bg-surface-card px-3 py-2.5 font-body text-base text-text-main outline-none ring-1 ring-border-idle focus:ring-primary-volt"
            />
          </label>
        </div>

        {/* Lista de ejercicios agregados */}
        <div className="space-y-3">
          <p className="font-heading text-sm font-semibold text-text-main">
            Ejercicios {items.length > 0 && <span className="text-text-muted">({items.length})</span>}
          </p>

          {items.length === 0 ? (
            <p className="rounded-lg border border-dashed border-border-idle px-4 py-6 text-center font-body text-sm text-text-muted">
              Todavía no agregaste ejercicios. Tocá “Agregar ejercicio” para elegir del catálogo.
            </p>
          ) : (
            items.map((it) => (
              <div key={it.ejercicio.idEjercicio} className="rounded-lg bg-surface-card p-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex min-w-0 items-start gap-2">
                    <GripVertical size={16} className="mt-0.5 shrink-0 text-text-muted" />
                    <div className="min-w-0">
                      <p className="truncate font-body text-sm font-medium text-text-main">
                        {it.ejercicio.nombre}
                      </p>
                      <p className="font-body text-xs text-text-muted">{it.ejercicio.grupoMuscular}</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => quitar(it.ejercicio.idEjercicio)}
                    aria-label="Quitar"
                    className="shrink-0 rounded-md p-1.5 text-text-muted hover:text-status-danger"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>

                {/* Series / reps / descanso */}
                <div className="mt-3 grid grid-cols-3 gap-2">
                  <CampoMini
                    etiqueta="Series"
                    value={it.series}
                    onChange={(v) => cambiar(it.ejercicio.idEjercicio, 'series', v)}
                    placeholder="4"
                  />
                  <CampoMini
                    etiqueta="Reps"
                    value={it.repeticiones}
                    onChange={(v) => cambiar(it.ejercicio.idEjercicio, 'repeticiones', v)}
                    placeholder="8-12"
                    texto
                  />
                  <CampoMini
                    etiqueta="Descanso (s)"
                    value={it.descanso}
                    onChange={(v) => cambiar(it.ejercicio.idEjercicio, 'descanso', v)}
                    placeholder="60"
                  />
                </div>
              </div>
            ))
          )}

          <button
            type="button"
            onClick={() => setEligiendo(true)}
            className="flex w-full items-center justify-center gap-2 rounded-lg border border-border-idle py-3 font-body text-sm font-medium text-text-secondary"
          >
            <Plus size={16} /> Agregar ejercicio
          </button>
        </div>

        {error && <p className="font-body text-sm text-status-danger">{error}</p>}
      </div>

      {/* Guardar */}
      <div className="shrink-0 border-t border-border-idle px-4 pt-3 pb-6">
        <button
          type="button"
          onClick={() => void guardar()}
          disabled={!puedeGuardar}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary-volt py-3.5 font-heading text-base font-bold text-surface-base disabled:opacity-40"
        >
          {guardando ? 'Guardando…' : 'Guardar rutina'}
        </button>
      </div>
    </div>
  );
}

// -----------------------------------------------------------------------------

function CampoMini({
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
        inputMode={texto ? 'text' : 'numeric'}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-md bg-surface-base px-2 py-1.5 text-center font-mono text-sm text-text-main outline-none ring-1 ring-border-idle focus:ring-primary-volt"
      />
    </label>
  );
}

// -----------------------------------------------------------------------------

function PickerCatalogo({
  catalogo,
  error,
  agregados,
  onToggle,
  onListo,
}: {
  catalogo: EjercicioCatalogo[] | null;
  error: string | null;
  agregados: Set<number>;
  onToggle: (ej: EjercicioCatalogo) => void;
  onListo: () => void;
}) {
  const [busqueda, setBusqueda] = useState('');

  // Agrupado por grupo muscular, filtrado por la búsqueda.
  const grupos = useMemo(() => {
    if (!catalogo) return [];
    const q = busqueda.trim().toLowerCase();
    const filtrados = q
      ? catalogo.filter(
          (e) => e.nombre.toLowerCase().includes(q) || e.grupoMuscular.toLowerCase().includes(q),
        )
      : catalogo;
    const mapa = new Map<string, EjercicioCatalogo[]>();
    for (const e of filtrados) {
      const g = mapa.get(e.grupoMuscular) ?? [];
      g.push(e);
      mapa.set(e.grupoMuscular, g);
    }
    return [...mapa.entries()];
  }, [catalogo, busqueda]);

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-surface-base">
      <header className="flex shrink-0 items-center justify-between gap-3 border-b border-border-idle px-4 py-3">
        <p className="font-heading text-lg font-semibold text-text-main">Elegí ejercicios</p>
        <button
          type="button"
          onClick={onListo}
          className="shrink-0 rounded-lg bg-primary-volt px-4 py-1.5 font-body text-sm font-semibold text-surface-base"
        >
          Listo {agregados.size > 0 && `(${agregados.size})`}
        </button>
      </header>

      {/* Buscador */}
      <div className="shrink-0 px-4 py-3">
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
                  <button
                    key={e.idEjercicio}
                    type="button"
                    onClick={() => onToggle(e)}
                    className={`flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2.5 text-left ring-1 transition-colors ${
                      puesto
                        ? 'bg-primary-volt/10 ring-primary-volt'
                        : 'bg-surface-card ring-border-idle'
                    }`}
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
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
