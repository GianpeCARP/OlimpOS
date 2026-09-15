import { Ban, Bolt, Minus, RotateCcw, TrendingDown, TrendingUp, type LucideIcon } from 'lucide-react';
import { PrimaryButton, StatusBadge } from '../../components/ui';
import { colors, EstadoDieta, ObjetivoDieta, type ObjetivoDietaValue } from '../../config';
import type { PlanListado } from '../../services/nutricionService';
import { formatearNumero } from '../../utils/format';

// Equivalente de _plan_card + OBJETIVO_CONFIG (estructura_nutricion.md).
// El doc pide azul (INFO) para "Mantenimiento" — Kinetic Carbon no tiene
// azul, se usa primary-volt (el otro caso de sustitución ya documentado en
// StaffCard para Tarde/Noche).
const CONFIG_OBJETIVO: Record<ObjetivoDietaValue, { icono: LucideIcon; color: string }> = {
  [ObjetivoDieta.MASA_MUSCULAR]: { icono: TrendingUp, color: colors.statusOk },
  [ObjetivoDieta.BAJAR_PESO]: { icono: TrendingDown, color: colors.statusDanger },
  [ObjetivoDieta.MANTENIMIENTO]: { icono: Minus, color: colors.primaryVolt },
  [ObjetivoDieta.ALTO_RENDIMIENTO]: { icono: Bolt, color: colors.statusWarn },
};
const CONFIG_POR_DEFECTO = { icono: Minus, color: colors.textMuted };

interface PlanCardProps {
  plan: PlanListado;
  /** False para roles con acceso de sólo lectura (p. ej. Entrenador). */
  puedeGestionar: boolean;
  onVerPlan: () => void;
  onDarDeBaja: () => void;
  onActivar: () => void;
}

export function PlanCard({
  plan,
  puedeGestionar,
  onVerPlan,
  onDarDeBaja,
  onActivar,
}: PlanCardProps) {
  // `?? CONFIG_POR_DEFECTO` y no sólo el ternario: Dieta.objetivo es un
  // varchar(100) libre en el esquema, así que puede traer cualquier texto
  // (una fila cargada a mano, un import, un valor de ObjetivoDieta que se
  // renombre). Con el ternario solo, un objetivo fuera del mapa devolvía
  // undefined y el destructuring reventaba la tarjeta entera con un
  // TypeError. Ahora cae al ícono neutro, que es lo que ya hacen
  // StatusBadge y LevelBadge con sus propios mapas.
  const { icono: Icono, color } =
    (plan.objetivo && CONFIG_OBJETIVO[plan.objetivo]) || CONFIG_POR_DEFECTO;
  const yaInactivo = plan.estado === EstadoDieta.INACTIVA;

  return (
    <div className="flex flex-col rounded-lg border border-border-idle bg-surface-card p-5">
      <div className="flex items-start justify-between">
        <div
          className="flex items-center gap-1.5 rounded-full px-3 py-1 font-body text-xs font-medium"
          style={{ backgroundColor: `${color}1A`, color }}
        >
          <Icono size={14} />
          {plan.objetivo ?? 'Sin objetivo'}
        </div>
        <div className="flex items-center gap-1.5">
          <StatusBadge status={plan.estado} />
          {/* Mismo patrón que RutinaCard: un solo botón que cambia de
              acción según el estado, los dos caminos desde el principio.
              Con acceso de sólo lectura no se dibuja ninguno. */}
          {!puedeGestionar ? null : yaInactivo ? (
            <button
              type="button"
              onClick={onActivar}
              title="Reactivar"
              className="rounded-md p-1 text-text-muted hover:bg-surface-hover hover:text-status-ok"
            >
              <RotateCcw size={14} />
            </button>
          ) : (
            <button
              type="button"
              onClick={onDarDeBaja}
              title="Dar de baja"
              className="rounded-md p-1 text-text-muted hover:bg-surface-hover hover:text-status-danger"
            >
              <Ban size={14} />
            </button>
          )}
        </div>
      </div>

      <h3 className="mt-3 truncate font-heading text-lg font-semibold text-text-main">
        {plan.nombre}
      </h3>

      {plan.caloriasDiarias !== undefined && (
        <div className="mt-2 flex items-baseline gap-1.5">
          {/* font-mono exclusivo para métricas — DESIGN.md §6, igual que StatCard. */}
          <span className="font-mono text-3xl font-bold text-text-main">
            {formatearNumero(plan.caloriasDiarias)}
          </span>
          <span className="font-body text-sm text-text-secondary">kcal/día</span>
        </div>
      )}

      <div className="mt-4 border-t border-border-idle pt-4">
        <p className="font-body text-sm text-text-secondary">
          <span className="text-text-main">{plan.asignados}</span> socios asignados
        </p>
        {/* Quién lo armó: con los planes de todo el plantel a la vista, es lo
            que explica por qué algunos no tienen botones. */}
        <p className="mt-1 font-body text-xs text-text-muted">{plan.nutricionista}</p>
      </div>

      <div className="mt-4">
        <PrimaryButton label="Ver plan" onClick={onVerPlan} width="100%" />
      </div>
    </div>
  );
}
