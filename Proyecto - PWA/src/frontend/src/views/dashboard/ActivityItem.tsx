import { UserPlus, Banknote, Dumbbell, AlertTriangle, type LucideIcon } from 'lucide-react';
import { colors } from '../../config';
import type { EventoActividad, TipoActividad } from '../../services/dashboardService';
import { formatearTiempoRelativo } from '../../utils/format';

// Equivalente de _activity_item + ACTIVITY_ICONS (estructura_dashboard.md).
//
// El doc pide azul para "nuevo_socio", pero la paleta Kinetic Carbon
// (DESIGN.md) no tiene azul: se usa el volt, que es el acento primario y
// cumple la misma función de "informativo/neutro positivo".
const ICONOS_ACTIVIDAD: Record<TipoActividad, { icono: LucideIcon; color: string }> = {
  nuevo_socio: { icono: UserPlus, color: colors.primaryVolt },
  pago: { icono: Banknote, color: colors.statusOk },
  rutina: { icono: Dumbbell, color: colors.accentCoral },
  vencimiento: { icono: AlertTriangle, color: colors.statusWarn },
};

interface ActivityItemProps {
  evento: EventoActividad;
  /** El último ítem no lleva línea divisoria abajo. */
  ultimo?: boolean;
}

export function ActivityItem({ evento, ultimo }: ActivityItemProps) {
  const { icono: Icono, color } = ICONOS_ACTIVIDAD[evento.tipo];

  return (
    <div
      className={`flex items-center gap-3 py-3 ${ultimo ? '' : 'border-b border-border-idle'}`}
    >
      {/* Fondo translúcido del mismo color del ícono: 1A = 10% de opacidad
          en hexadecimal, el recurso que usa todo el sistema de diseño. */}
      <div
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md"
        style={{ backgroundColor: `${color}1A` }}
      >
        <Icono size={16} color={color} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate font-body text-sm text-text-main">{evento.descripcion}</p>
        {/* El texto relativo se calcula al renderizar a partir del timestamp
            real, no viene escrito desde los datos. */}
        <p className="font-body text-xs text-text-muted">
          {formatearTiempoRelativo(evento.fecha)}
        </p>
      </div>
    </div>
  );
}
