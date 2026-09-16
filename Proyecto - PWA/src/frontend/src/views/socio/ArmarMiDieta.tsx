import { useState } from 'react';
import { Plus, Trash2, Utensils, X } from 'lucide-react';
import { ServiceError, mensajeDeError } from '../../services/api';
import {
  crearMiDietaPropia,
  type MiDieta,
} from '../../services/socioService';

// =============================================================================
// ARMAR MI DIETA — el socio se arma su propia dieta (id_nutricionista NULL)
// =============================================================================
// MODO de "Mi dieta" (fixed inset-0), no una ruta. Espejo de ArmarMiRutina, pero
// las comidas son de TEXTO LIBRE: el catálogo del gimnasio puede estar vacío y,
// de todos modos, nadie quiere elegir "avena con banana" de una lista.
//
// Al guardar, el backend crea la dieta y se la autoasigna. Si ya tiene una del
// NUTRICIONISTA activa, rechaza con 409 (la del profesional manda).

const MOMENTOS = ['Desayuno', 'Media mañana', 'Almuerzo', 'Merienda', 'Cena', 'Snack'];

interface ItemComida {
  momento: string;
  descripcion: string;
}

interface ArmarMiDietaProps {
  onCerrar: () => void;
  onGuardada: (dieta: MiDieta) => void;
}

export function ArmarMiDieta({ onCerrar, onGuardada }: ArmarMiDietaProps) {
  const [nombre, setNombre] = useState('');
  const [objetivo, setObjetivo] = useState('');
  const [calorias, setCalorias] = useState('');
  const [items, setItems] = useState<ItemComida[]>([{ momento: 'Desayuno', descripcion: '' }]);

  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const agregar = () =>
    setItems((xs) => [...xs, { momento: MOMENTOS[Math.min(xs.length, MOMENTOS.length - 1)], descripcion: '' }]);
  const quitar = (i: number) => setItems((xs) => xs.filter((_, idx) => idx !== i));
  const cambiar = (i: number, campo: keyof ItemComida, valor: string) =>
    setItems((xs) => xs.map((it, idx) => (idx === i ? { ...it, [campo]: valor } : it)));

  const comidasValidas = items.filter((i) => i.descripcion.trim().length > 0);
  const puedeGuardar = nombre.trim().length > 0 && comidasValidas.length > 0 && !guardando;

  const guardar = async () => {
    if (!puedeGuardar) return;
    setGuardando(true);
    setError(null);
    try {
      const kcal = Number(calorias);
      const dieta = await crearMiDietaPropia({
        nombre,
        objetivo: objetivo || undefined,
        caloriasDiarias: calorias && Number.isFinite(kcal) && kcal > 0 ? Math.floor(kcal) : undefined,
        comidas: comidasValidas.map((i) => ({
          momento: i.momento || undefined,
          descripcion: i.descripcion,
        })),
      });
      onGuardada(dieta);
    } catch (e: unknown) {
      // 409 = ya tiene una dieta del nutricionista. Se muestra el mensaje del
      // backend, que ya lo explica.
      setError(e instanceof ServiceError && e.status === 409 ? e.message : mensajeDeError(e));
      setGuardando(false);
    }
  };

  return (
    // En el celular ocupa toda la pantalla (es donde se usa parado en el
    // gimnasio); desde tablet es una ventana centrada como el resto de los
    // modales. A pantalla completa en una PC quedaba estirado de lado a lado.
    <div className="fixed inset-0 z-50 flex bg-surface-base md:items-center md:justify-center md:bg-black/60 md:p-4">
      <div className="flex h-full w-full flex-col bg-surface-base md:h-auto md:max-h-[85dvh] md:max-w-2xl md:overflow-hidden md:rounded-lg md:border md:border-border-idle md:bg-surface-card">
      <header className="flex shrink-0 items-center justify-between border-b border-border-idle px-4 py-3">
        <p className="font-heading text-lg font-semibold text-text-main">Armar mi dieta</p>
        <button
          type="button"
          onClick={onCerrar}
          aria-label="Cerrar"
          className="flex size-10 items-center justify-center rounded-full bg-surface-card text-text-main"
        >
          <X size={20} />
        </button>
      </header>

      <div className="min-h-0 flex-1 space-y-5 overflow-y-auto overscroll-contain px-4 py-5">
        <div className="space-y-3">
          <label className="flex flex-col gap-1">
            <span className="font-body text-xs font-medium uppercase tracking-wide text-text-muted">
              Nombre de tu dieta
            </span>
            <input
              type="text"
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              placeholder="Ej: Volumen limpio"
              maxLength={100}
              className="rounded-lg bg-surface-card px-3 py-2.5 font-body text-base text-text-main outline-none ring-1 ring-border-idle focus:ring-primary-volt"
            />
          </label>

          <div className="flex gap-3">
            <label className="flex flex-1 flex-col gap-1">
              <span className="font-body text-xs font-medium uppercase tracking-wide text-text-muted">
                Objetivo <span className="normal-case text-text-muted/70">(opcional)</span>
              </span>
              <input
                type="text"
                value={objetivo}
                onChange={(e) => setObjetivo(e.target.value)}
                placeholder="Subir masa"
                maxLength={100}
                className="rounded-lg bg-surface-card px-3 py-2.5 font-body text-base text-text-main outline-none ring-1 ring-border-idle focus:ring-primary-volt"
              />
            </label>
            <label className="flex w-28 flex-col gap-1">
              <span className="font-body text-xs font-medium uppercase tracking-wide text-text-muted">
                kcal/día
              </span>
              <input
                type="text"
                inputMode="numeric"
                value={calorias}
                onChange={(e) => setCalorias(e.target.value.replace(/\D/g, ''))}
                placeholder="—"
                className="rounded-lg bg-surface-card px-3 py-2.5 text-center font-mono text-base text-text-main outline-none ring-1 ring-border-idle focus:ring-primary-volt"
              />
            </label>
          </div>
        </div>

        <div className="space-y-3">
          <p className="font-heading text-sm font-semibold text-text-main">
            Comidas {comidasValidas.length > 0 && <span className="text-text-muted">({comidasValidas.length})</span>}
          </p>

          {items.map((it, i) => (
            <div key={i} className="rounded-lg bg-surface-card p-3">
              <div className="flex items-center justify-between gap-2">
                <select
                  value={it.momento}
                  onChange={(e) => cambiar(i, 'momento', e.target.value)}
                  className="rounded-md bg-surface-base px-2 py-1.5 font-body text-sm text-text-main outline-none ring-1 ring-border-idle focus:ring-primary-volt"
                >
                  {MOMENTOS.map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
                {items.length > 1 && (
                  <button
                    type="button"
                    onClick={() => quitar(i)}
                    aria-label="Quitar comida"
                    className="rounded-md p-1.5 text-text-muted hover:text-status-danger"
                  >
                    <Trash2 size={16} />
                  </button>
                )}
              </div>
              <input
                type="text"
                value={it.descripcion}
                onChange={(e) => cambiar(i, 'descripcion', e.target.value)}
                placeholder="Qué comés (ej: avena con banana y 2 huevos)"
                maxLength={200}
                className="mt-2 w-full rounded-md bg-surface-base px-3 py-2 font-body text-sm text-text-main outline-none ring-1 ring-border-idle focus:ring-primary-volt"
              />
            </div>
          ))}

          <button
            type="button"
            onClick={agregar}
            className="flex w-full items-center justify-center gap-2 rounded-lg border border-border-idle py-3 font-body text-sm font-medium text-text-secondary"
          >
            <Plus size={16} /> Agregar comida
          </button>
        </div>

        {error && <p className="font-body text-sm text-status-danger">{error}</p>}
      </div>

      <div className="shrink-0 border-t border-border-idle px-4 pt-3 pb-6">
        <button
          type="button"
          onClick={() => void guardar()}
          disabled={!puedeGuardar}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary-volt py-3.5 font-heading text-base font-bold text-surface-base disabled:opacity-40"
        >
          <Utensils size={18} /> {guardando ? 'Guardando…' : 'Guardar dieta'}
        </button>
      </div>
      </div>
    </div>
  );
}
