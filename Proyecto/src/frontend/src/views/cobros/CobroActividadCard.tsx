import { CalendarCheck, ShoppingCart } from 'lucide-react';
import { PrimaryButton } from '../../components/ui';
import type {
  ActividadListada,
  InscripcionListada,
  PlanActividadListado,
} from '../../services/actividadService';
import { formatearMoneda } from '../../utils/format';

// Espejo de socio/ActividadCatalogoCard.tsx con "Cobrar" en vez de
// "Comprar" — mismo aviso de REGLA 7 (reemplazo sin devolución) para que
// recepción no dispare el reemplazo a ciegas.
interface CobroActividadCardProps {
  actividad: ActividadListada;
  planes: PlanActividadListado[];
  inscripcionActivaDeEstaActividad?: InscripcionListada;
  onCobrarPlan: (plan: PlanActividadListado) => void;
  onCobrarClaseSuelta: () => void;
}

export function CobroActividadCard({
  actividad,
  planes,
  inscripcionActivaDeEstaActividad,
  onCobrarPlan,
  onCobrarClaseSuelta,
}: CobroActividadCardProps) {
  return (
    <div className="flex flex-col rounded-lg border border-border-idle bg-surface-card p-5">
      <div className="flex items-center gap-2">
        <CalendarCheck size={18} className="shrink-0 text-primary-volt" />
        <h3 className="truncate font-heading text-lg font-semibold text-text-main">
          {actividad.nombre}
        </h3>
      </div>

      {inscripcionActivaDeEstaActividad && (
        <p className="mt-3 rounded-md bg-surface-hover px-3 py-2 font-body text-xs text-text-secondary">
          Ya tiene <span className="text-text-main">{inscripcionActivaDeEstaActividad.nombrePlan}</span>{' '}
          activo. Cobrar otro plan de {actividad.nombre} lo reemplaza sin devolución.
        </p>
      )}

      {planes.length === 0 ? (
        <p className="mt-4 font-body text-sm text-text-muted">
          Todavía no hay planes cargados para esta actividad.
        </p>
      ) : (
        <div className="mt-4 flex flex-col divide-y divide-border-idle">
          {planes.map((plan) => (
            <div key={plan.idPlanActividad} className="flex items-center justify-between gap-3 py-2.5">
              <div className="min-w-0">
                <p className="font-body text-sm text-text-main">{plan.nombre}</p>
                <p className="font-mono text-xs text-text-secondary">{formatearMoneda(plan.precio)}</p>
              </div>
              <PrimaryButton label="Cobrar" onClick={() => onCobrarPlan(plan)} />
            </div>
          ))}
        </div>
      )}

      <div className="mt-auto pt-4">
        <button
          type="button"
          onClick={onCobrarClaseSuelta}
          className="flex w-full items-center justify-center gap-2 rounded-md border border-border-idle px-3 py-2 font-body text-sm text-text-secondary transition-colors hover:bg-surface-hover hover:text-text-main"
        >
          <ShoppingCart size={14} />
          Clase suelta ({formatearMoneda(actividad.precioClaseSuelta)})
        </button>
      </div>
    </div>
  );
}
