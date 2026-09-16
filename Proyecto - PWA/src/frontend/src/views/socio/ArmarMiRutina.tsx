import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { ServiceError, mensajeDeError } from '../../services/api';
import {
  crearMiRutinaPropia,
  listarEjerciciosCatalogo,
  type EjercicioCatalogo,
  type MiRutina,
} from '../../services/socioService';
import { EditorEjercicios } from '../rutinas/EditorEjercicios';
import { armarEjercicios, nuevoItem, type ItemEjercicio } from '../rutinas/planillaEjercicios';

// =============================================================================
// ARMAR MI RUTINA — el socio se arma su propia rutina (id_entrenador NULL)
// =============================================================================
// MODO de "Mi rutina" (fixed inset-0), no una ruta: el botón de atrás del
// celular no puede dejarte a mitad de armado.
//
// Usa el MISMO editor que el entrenador (EditorEjercicios): varios días, peso,
// descanso, observaciones y orden. Para rehacer la propia se abre con la que ya
// tiene cargada, no en blanco: rehacer suele ser cambiar un ejercicio.
//
// Al guardar, el backend crea la rutina y se la autoasigna (la propia anterior
// queda en el historial). Si ya tiene una del ENTRENADOR activa, rechaza con
// 409 y acá se explica (la del profe manda).

interface ArmarMiRutinaProps {
  /** La rutina PROPIA actual, para editarla. null/undefined = armar desde cero. */
  actual?: MiRutina | null;
  onCerrar: () => void;
  onGuardada: (rutina: MiRutina) => void;
}

export function ArmarMiRutina({ actual, onCerrar, onGuardada }: ArmarMiRutinaProps) {
  const [nombre, setNombre] = useState(actual?.nombre ?? '');
  const [objetivo, setObjetivo] = useState(actual?.objetivo ?? '');
  const [dias, setDias] = useState(actual?.diasPorSemana ?? Math.max(1, actual?.dias.length ?? 1));
  const [items, setItems] = useState<ItemEjercicio[]>(() =>
    actual ? actual.dias.flatMap((d) => d.ejercicios.map((e) => nuevoItem({ ...e, dia: d.dia }))) : [],
  );

  const [catalogo, setCatalogo] = useState<EjercicioCatalogo[] | null>(null);
  const [errorCatalogo, setErrorCatalogo] = useState<string | null>(null);

  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelado = false;
    listarEjerciciosCatalogo()
      .then((c) => { if (!cancelado) setCatalogo(c); })
      .catch((e: unknown) => { if (!cancelado) setErrorCatalogo(mensajeDeError(e)); });
    return () => { cancelado = true; };
  }, []);

  const puedeGuardar = nombre.trim().length > 0 && items.length > 0 && !guardando;

  const guardar = async () => {
    if (!puedeGuardar) return;
    setError(null);

    let ejercicios;
    try {
      ejercicios = armarEjercicios(items, dias);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
      return;
    }

    setGuardando(true);
    try {
      const rutina = await crearMiRutinaPropia({
        nombre,
        objetivo: objetivo || undefined,
        diasPorSemana: dias,
        ejercicios,
      });
      onGuardada(rutina);
    } catch (e: unknown) {
      // El 409 es el caso esperado: ya tiene una rutina del entrenador. Se
      // muestra el mensaje del backend, que ya lo explica bien.
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
        <p className="font-heading text-lg font-semibold text-text-main">
          {actual ? 'Editar mi rutina' : 'Armar mi rutina'}
        </p>
        <button
          type="button"
          onClick={onCerrar}
          aria-label="Cerrar"
          className="flex size-10 items-center justify-center rounded-full bg-surface-card text-text-main"
        >
          <X size={20} />
        </button>
      </header>

      <div className="min-h-0 flex-1 space-y-5 overflow-y-auto overscroll-contain px-4 py-5 md:mx-auto md:w-full md:max-w-2xl">
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

          <div className="flex flex-col gap-1">
            <span className="font-body text-xs font-medium uppercase tracking-wide text-text-muted">
              Días por semana
            </span>
            <div className="flex flex-wrap gap-2">
              {[1, 2, 3, 4, 5, 6, 7].map((n) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => setDias(n)}
                  className={`size-10 shrink-0 rounded-lg font-mono text-sm ring-1 ${
                    n === dias
                      ? 'bg-primary-volt text-surface-base ring-primary-volt'
                      : 'bg-surface-card text-text-secondary ring-border-idle'
                  }`}
                >
                  {n}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-3">
          <p className="font-heading text-sm font-semibold text-text-main">
            Ejercicios {items.length > 0 && <span className="text-text-muted">({items.length})</span>}
          </p>
          <EditorEjercicios
            items={items}
            setItems={setItems}
            dias={dias}
            catalogo={catalogo}
            errorCatalogo={errorCatalogo}
          />
        </div>

        {error && <p className="font-body text-sm text-status-danger">{error}</p>}
      </div>

      <div className="shrink-0 border-t border-border-idle px-4 pt-3 pb-6">
        <button
          type="button"
          onClick={() => void guardar()}
          disabled={!puedeGuardar}
          className="mx-auto flex w-full items-center justify-center gap-2 rounded-xl bg-primary-volt py-3.5 font-heading text-base font-bold text-surface-base disabled:opacity-40 md:max-w-2xl"
        >
          {guardando ? 'Guardando…' : 'Guardar rutina'}
        </button>
      </div>
      </div>
    </div>
  );
}
