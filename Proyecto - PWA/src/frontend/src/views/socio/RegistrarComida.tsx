import { useEffect, useState } from 'react';
import { Plus, X } from 'lucide-react';
import { mensajeDeError } from '../../services/api';
import {
  listarMisComidas,
  registrarComida,
  type ComidaRegistrada,
} from '../../services/socioService';
import { formatearFecha } from '../../utils/format';
import { parsearFecha } from '../../utils/fechas';

// =============================================================================
// REGISTRAR COMIDA — lo que el socio comió (Registro_Comida)
// =============================================================================
// MODO de "Mi dieta" (fixed inset-0). El texto es obligatorio; los macros son
// opcionales y se cargan a mano (más adelante el coach IA los va a poder
// autocompletar). No depende de tener una dieta cargada: se puede registrar
// siempre.

const MOMENTOS = ['Desayuno', 'Media mañana', 'Almuerzo', 'Merienda', 'Cena', 'Snack'];

const soloNum = (s: string) => s.replace(/[^\d]/g, '');
const aNum = (s: string): number | undefined => {
  const n = Number(s);
  return s && Number.isFinite(n) && n > 0 ? n : undefined;
};

interface RegistrarComidaProps {
  onCerrar: () => void;
}

export function RegistrarComida({ onCerrar }: RegistrarComidaProps) {
  const [texto, setTexto] = useState('');
  const [momento, setMomento] = useState('Almuerzo');
  const [calorias, setCalorias] = useState('');
  const [prote, setProte] = useState('');
  const [carbo, setCarbo] = useState('');
  const [grasa, setGrasa] = useState('');

  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [historial, setHistorial] = useState<ComidaRegistrada[] | null>(null);

  useEffect(() => {
    let cancelado = false;
    listarMisComidas(7)
      .then((c) => { if (!cancelado) setHistorial(c); })
      .catch(() => { if (!cancelado) setHistorial([]); });
    return () => { cancelado = true; };
  }, []);

  const puedeGuardar = texto.trim().length > 0 && !guardando;

  const guardar = async () => {
    if (!puedeGuardar) return;
    setGuardando(true);
    setError(null);
    try {
      const nueva = await registrarComida({
        comidaIngerida: texto,
        momento: momento || undefined,
        calorias: aNum(calorias),
        proteinas: aNum(prote),
        carbohidratos: aNum(carbo),
        grasas: aNum(grasa),
      });
      setHistorial((h) => [nueva, ...(h ?? [])]);
      // Limpiar para la próxima carga, dejando el momento elegido.
      setTexto(''); setCalorias(''); setProte(''); setCarbo(''); setGrasa('');
    } catch (e: unknown) {
      setError(mensajeDeError(e));
    } finally {
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
        <p className="font-heading text-lg font-semibold text-text-main">Registrar comida</p>
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
        {/* Formulario */}
        <div className="space-y-3 rounded-lg bg-surface-card p-4">
          <label className="flex flex-col gap-1">
            <span className="font-body text-xs font-medium uppercase tracking-wide text-text-muted">
              ¿Qué comiste?
            </span>
            <textarea
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              placeholder="Ej: 2 huevos revueltos, pan integral y un café con leche"
              rows={2}
              maxLength={1000}
              className="resize-none rounded-lg bg-surface-base px-3 py-2.5 font-body text-base text-text-main outline-none ring-1 ring-border-idle focus:ring-primary-volt"
            />
          </label>

          <label className="flex flex-col gap-1">
            <span className="font-body text-xs font-medium uppercase tracking-wide text-text-muted">
              Momento
            </span>
            <select
              value={momento}
              onChange={(e) => setMomento(e.target.value)}
              className="rounded-lg bg-surface-base px-3 py-2.5 font-body text-sm text-text-main outline-none ring-1 ring-border-idle focus:ring-primary-volt"
            >
              {MOMENTOS.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </label>

          <div>
            <p className="mb-1 font-body text-xs font-medium uppercase tracking-wide text-text-muted">
              Macros <span className="normal-case text-text-muted/70">(opcional)</span>
            </p>
            <div className="grid grid-cols-4 gap-2">
              <CampoMacro etiqueta="kcal" value={calorias} onChange={(v) => setCalorias(soloNum(v))} />
              <CampoMacro etiqueta="Prot" value={prote} onChange={(v) => setProte(soloNum(v))} />
              <CampoMacro etiqueta="Carb" value={carbo} onChange={(v) => setCarbo(soloNum(v))} />
              <CampoMacro etiqueta="Gras" value={grasa} onChange={(v) => setGrasa(soloNum(v))} />
            </div>
            <p className="mt-1.5 font-body text-xs text-text-muted">
              Si no los sabés, dejalos vacíos. Más adelante el coach los estima solo.
            </p>
          </div>

          {error && <p className="font-body text-sm text-status-danger">{error}</p>}

          <button
            type="button"
            onClick={() => void guardar()}
            disabled={!puedeGuardar}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary-volt py-3 font-heading text-base font-bold text-surface-base disabled:opacity-40"
          >
            <Plus size={18} /> {guardando ? 'Guardando…' : 'Registrar'}
          </button>
        </div>

        {/* Historial */}
        <div className="space-y-2">
          <p className="font-heading text-sm font-semibold text-text-main">Últimos días</p>
          {historial === null && (
            <p className="font-body text-sm text-text-muted">Cargando…</p>
          )}
          {historial !== null && historial.length === 0 && (
            <p className="rounded-lg border border-dashed border-border-idle px-4 py-6 text-center font-body text-sm text-text-muted">
              Todavía no registraste ninguna comida.
            </p>
          )}
          {historial?.map((c) => (
            <div key={c.idRegistroComida} className="rounded-lg bg-surface-card p-3">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-body text-xs text-text-muted">
                    {formatearFecha(parsearFecha(c.fecha))}
                    {c.momento ? ` · ${c.momento}` : ''}
                  </p>
                  <p className="font-body text-sm text-text-main">{c.comidaIngerida}</p>
                </div>
                {c.calorias !== undefined && (
                  <span className="shrink-0 font-mono text-xs text-text-secondary">
                    {c.calorias} kcal
                  </span>
                )}
              </div>
              {(c.proteinas !== undefined || c.carbohidratos !== undefined || c.grasas !== undefined) && (
                <div className="mt-1.5 flex gap-3 font-mono text-xs text-text-muted">
                  {c.proteinas !== undefined && <span>P {c.proteinas}g</span>}
                  {c.carbohidratos !== undefined && <span>C {c.carbohidratos}g</span>}
                  {c.grasas !== undefined && <span>G {c.grasas}g</span>}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
      </div>
    </div>
  );
}

function CampoMacro({
  etiqueta,
  value,
  onChange,
}: {
  etiqueta: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex flex-col items-center gap-1">
      <span className="font-body text-[10px] uppercase tracking-wide text-text-muted">{etiqueta}</span>
      <input
        type="text"
        inputMode="numeric"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="—"
        className="w-full rounded-md bg-surface-base px-1 py-1.5 text-center font-mono text-sm text-text-main outline-none ring-1 ring-border-idle focus:ring-primary-volt"
      />
    </label>
  );
}
