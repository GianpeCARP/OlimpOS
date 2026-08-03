import { StatusBadge } from '../../components/ui';
import type { SocioResumen } from '../../services/dashboardService';

// Equivalente de _socio_row (estructura_dashboard.md): avatar con inicial |
// nombre + plan | badge de estado.
interface SocioRowProps {
  socio: SocioResumen;
  /** La última fila no lleva línea divisoria abajo. */
  ultimo?: boolean;
}

export function SocioRow({ socio, ultimo }: SocioRowProps) {
  return (
    <div
      className={`flex items-center gap-3 py-3 ${ultimo ? '' : 'border-b border-border-idle'}`}
    >
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-surface-hover font-heading text-sm font-bold text-primary-volt">
        {socio.iniciales}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate font-body text-sm text-text-main">{socio.nombre}</p>
        <p className="truncate font-body text-xs text-text-muted">{socio.plan}</p>
      </div>
      <StatusBadge status={socio.estado} />
    </div>
  );
}
