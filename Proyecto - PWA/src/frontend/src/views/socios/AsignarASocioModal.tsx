import { useEffect, useMemo, useState } from 'react';
import { Search, X } from 'lucide-react';
import { colors } from '../../config';
import { mensajeDeError } from '../../services/api';
import { listarSocios, type SocioListado } from '../../services/sociosService';
import { useUiStore } from '../../store/uiStore';

// Elegir un socio activo (por nombre o DNI) y asignarle algo: una rutina, un
// plan nutricional. Lo que cambia entre esos casos es el texto y la llamada al
// backend, así que entran por props y el modal es uno solo.
//
// Sólo socios ACTIVOS: a uno dado de baja no le sirve un plan nuevo.

interface AsignarASocioModalProps {
  titulo: string;
  /** Qué se asigna (el nombre de la rutina o del plan). */
  subtitulo: string;
  /** Qué pasa si el socio ya tenía uno — para que no sorprenda. */
  aviso: string;
  mensajeExito: (socio: SocioListado) => string;
  onAsignar: (socio: SocioListado) => Promise<void>;
  onClose: () => void;
  onAsignada: () => void;
}

// Tope de filas dibujadas: con cientos de socios, la búsqueda es el camino.
const MAX_FILAS = 50;

export function AsignarASocioModal({
  titulo,
  subtitulo,
  aviso,
  mensajeExito,
  onAsignar,
  onClose,
  onAsignada,
}: AsignarASocioModalProps) {
  const showSnack = useUiStore((s) => s.showSnack);
  const [socios, setSocios] = useState<SocioListado[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busqueda, setBusqueda] = useState('');
  const [asignando, setAsignando] = useState<number | null>(null);

  useEffect(() => {
    let cancelado = false;
    listarSocios()
      .then((lista) => {
        if (!cancelado) setSocios(lista.filter((s) => s.activo));
      })
      .catch((err: unknown) => {
        if (!cancelado) setError(mensajeDeError(err));
      });
    return () => {
      cancelado = true;
    };
  }, []);

  const visibles = useMemo(() => {
    if (!socios) return [];
    const q = busqueda.trim().toLowerCase();
    const filtrados = q
      ? socios.filter((s) => s.nombreCompleto.toLowerCase().includes(q) || s.dni.includes(q))
      : socios;
    return filtrados.slice(0, MAX_FILAS);
  }, [socios, busqueda]);

  const asignar = async (socio: SocioListado) => {
    setAsignando(socio.idSocio);
    try {
      await onAsignar(socio);
      showSnack(mensajeExito(socio), colors.statusOk);
      onAsignada();
      onClose();
    } catch (err) {
      showSnack(mensajeDeError(err), colors.statusDanger);
      setAsignando(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="flex max-h-[85vh] w-full max-w-md flex-col rounded-lg border border-border-idle bg-surface-card">
        <div className="flex items-start justify-between gap-3 border-b border-border-idle p-5 pb-4">
          <div className="min-w-0">
            <h2 className="font-heading text-lg font-semibold text-text-main">{titulo}</h2>
            <p className="truncate font-body text-sm text-text-secondary">{subtitulo}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar"
            className="shrink-0 rounded-md p-1.5 text-text-muted hover:bg-surface-hover hover:text-text-main"
          >
            <X size={18} />
          </button>
        </div>

        <div className="shrink-0 px-5 pt-4">
          <div className="flex items-center gap-2 rounded-md border border-border-idle px-3 py-2 focus-within:border-border-active">
            <Search size={16} className="shrink-0 text-text-muted" />
            <input
              type="text"
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              placeholder="Buscar por nombre o DNI…"
              className="w-full bg-transparent font-body text-sm text-text-main outline-none placeholder:text-text-muted"
            />
          </div>
          <p className="mt-2 font-body text-xs text-text-muted">{aviso}</p>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain p-5">
          {error && <p className="font-body text-sm text-status-danger">{error}</p>}
          {!error && !socios && <p className="font-body text-sm text-text-muted">Cargando socios…</p>}
          {socios && visibles.length === 0 && (
            <p className="font-body text-sm text-text-muted">Ningún socio activo coincide.</p>
          )}
          <ul className="flex flex-col divide-y divide-border-idle">
            {visibles.map((s) => (
              <li key={s.idSocio} className="flex items-center justify-between gap-3 py-2.5">
                <div className="min-w-0">
                  <p className="truncate font-body text-sm text-text-main">{s.nombreCompleto}</p>
                  <p className="font-body text-xs text-text-muted">DNI {s.dni}</p>
                </div>
                <button
                  type="button"
                  onClick={() => void asignar(s)}
                  disabled={asignando !== null}
                  className="shrink-0 rounded-md bg-primary-volt px-3 py-1.5 font-body text-sm font-semibold whitespace-nowrap text-surface-base disabled:opacity-40"
                >
                  {asignando === s.idSocio ? 'Asignando…' : 'Asignar'}
                </button>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
