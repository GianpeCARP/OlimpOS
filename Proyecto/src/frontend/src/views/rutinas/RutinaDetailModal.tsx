import { LevelBadge, PrimaryButton, StatusBadge } from '../../components/ui';
import type { RutinaListado } from '../../services/rutinasService';
import { formatearFechaCorta } from '../../utils/format';
import { parsearFecha } from '../../utils/fechas';
import { DetailRow } from './DetailRow';

// Equivalente de _open_detail (estructura_rutinas.md): modal de solo
// lectura. Dos agregados sobre el doc: "Entrenador a cargo" (dato real
// disponible, a diferencia del pill de duración) y el botón "Editar" — el
// doc solo pone "Cerrar", pero sin una entrada a _open_form(rutina) no
// habría forma de corregir una rutina ya creada.
interface RutinaDetailModalProps {
  rutina: RutinaListado;
  /** False para roles con acceso de sólo lectura: se ve el detalle, sin "Editar". */
  puedeGestionar: boolean;
  onClose: () => void;
  onEditar: () => void;
}

export function RutinaDetailModal({
  rutina,
  puedeGestionar,
  onClose,
  onEditar,
}: RutinaDetailModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-md rounded-lg border border-border-idle bg-surface-card p-6">
        <div className="flex items-start justify-between gap-3">
          <h2 className="font-heading text-lg font-semibold text-text-main">{rutina.nombre}</h2>
          <div className="flex shrink-0 items-center gap-1.5">
            {rutina.nivel && <LevelBadge nivel={rutina.nivel} />}
            <StatusBadge status={rutina.estado} />
          </div>
        </div>

        <div className="mt-4 flex flex-col divide-y divide-border-idle">
          <DetailRow
            label="Frecuencia"
            value={rutina.diasPorSemana !== undefined ? `${rutina.diasPorSemana} días/sem` : '—'}
          />
          <DetailRow label="Entrenador" value={rutina.entrenador} />
          <DetailRow label="Asignados" value={`${rutina.asignados} socios`} />
          <DetailRow label="Creada" value={formatearFechaCorta(parsearFecha(rutina.fechaCreacion))} />
          <DetailRow label="Objetivo" value={rutina.objetivo ?? 'Sin especificar'} />
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="rounded-md px-4 py-2 font-body text-sm text-text-secondary hover:text-text-main"
          >
            Cerrar
          </button>
          {puedeGestionar && <PrimaryButton label="Editar" onClick={onEditar} />}
        </div>
      </div>
    </div>
  );
}
