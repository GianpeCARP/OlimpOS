import { CalendarCheck, ShoppingCart } from 'lucide-react';
import { PrimaryButton } from '../../components/ui';
import type {
  ActividadListada,
  InscripcionListada,
  PlanActividadListado,
} from '../../services/actividadService';
import { formatearMoneda } from '../../utils/format';

// Una actividad del catálogo con sus planes, cada uno con su propio botón
// de compra — no es una tarjeta "elegí una opción y confirmá" como
// RutinaCard/PlanCard (que representan UNA fila ya asignada); acá cada
// PLAN es su propia acción posible, porque el socio puede tener planes
// activos de varias actividades a la vez.
interface ActividadCatalogoCardProps {
  actividad: ActividadListada;
  planes: PlanActividadListado[];
  /** Para avisar "esto reemplaza tu plan actual" antes de que el socio confirme — ver REGLA 7. */
  inscripcionActivaDeEstaActividad?: InscripcionListada;
  onComprarPlan: (plan: PlanActividadListado) => void;
  onComprarClaseSuelta: () => void;
}

export function ActividadCatalogoCard({
  actividad,
  planes,
  inscripcionActivaDeEstaActividad,
  onComprarPlan,
  onComprarClaseSuelta,
}: ActividadCatalogoCardProps) {
  return (
    <div className="flex flex-col rounded-lg border border-border-idle bg-surface-card p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <CalendarCheck size={18} className="shrink-0 text-primary-volt" />
            <h3 className="truncate font-heading text-lg font-semibold text-text-main">
              {actividad.nombre}
            </h3>
          </div>
          {actividad.descripcion && (
            <p className="mt-1 font-body text-sm text-text-secondary">{actividad.descripcion}</p>
          )}
        </div>
      </div>

      {inscripcionActivaDeEstaActividad && (
        <p className="mt-3 rounded-md bg-surface-hover px-3 py-2 font-body text-xs text-text-secondary">
          Ya tenés <span className="text-text-main">{inscripcionActivaDeEstaActividad.nombrePlan}</span>{' '}
          activo. Comprar otro plan de {actividad.nombre} lo reemplaza.
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
              <PrimaryButton label="Comprar" onClick={() => onComprarPlan(plan)} />
            </div>
          ))}
        </div>
      )}

      <div className="mt-auto pt-4">
        <button
          type="button"
          onClick={onComprarClaseSuelta}
          className="flex w-full items-center justify-center gap-2 rounded-md border border-border-idle px-3 py-2 font-body text-sm text-text-secondary transition-colors hover:bg-surface-hover hover:text-text-main"
        >
          <ShoppingCart size={14} />
          Comprar clase suelta ({formatearMoneda(actividad.precioClaseSuelta)})
        </button>
      </div>
    </div>
  );
}
