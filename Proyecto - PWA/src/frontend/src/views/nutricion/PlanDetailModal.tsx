import { useEffect, useState } from 'react';
import { Bolt, Minus, TrendingDown, TrendingUp, type LucideIcon } from 'lucide-react';
import { PrimaryButton, StatusBadge } from '../../components/ui';
import { colors, ObjetivoDieta, type ObjetivoDietaValue } from '../../config';
import {
  listarComidasDelPlan,
  type ComidaListada,
  type PlanListado,
} from '../../services/nutricionService';
import { formatearNumero } from '../../utils/format';

// Equivalente de _open_detail (estructura_nutricion.md), con una diferencia
// grande a propósito: el doc muestra una distribución de macros fija
// (30/50/20 vía _macro_bar) que no tiene respaldo en el esquema — Dieta no
// tiene columnas de macros y ese split es el mismo para cualquier plan, no
// un dato real. En su lugar se listan las Comida reales cargadas para el
// plan, agrupadas por día. Si todavía no hay ninguna (no existe un editor
// de comidas — tampoco en el doc), se muestra el estado vacío real en vez
// de inventar una distribución.
const CONFIG_OBJETIVO: Record<ObjetivoDietaValue, { icono: LucideIcon; color: string }> = {
  [ObjetivoDieta.MASA_MUSCULAR]: { icono: TrendingUp, color: colors.statusOk },
  [ObjetivoDieta.BAJAR_PESO]: { icono: TrendingDown, color: colors.statusDanger },
  [ObjetivoDieta.MANTENIMIENTO]: { icono: Minus, color: colors.primaryVolt },
  [ObjetivoDieta.ALTO_RENDIMIENTO]: { icono: Bolt, color: colors.statusWarn },
};
const CONFIG_POR_DEFECTO = { icono: Minus, color: colors.textMuted };

interface PlanDetailModalProps {
  plan: PlanListado;
  /**
   * Gestionar ESTE plan: la acción y que el backend diga que es editable (un
   * Nutricionista ve los planes de sus colegas pero no los toca).
   */
  puedeGestionar: boolean;
  onClose: () => void;
  onEditar: () => void;
  onAsignar: () => void;
}

function agruparPorDia(comidas: ComidaListada[]): Map<number, ComidaListada[]> {
  const grupos = new Map<number, ComidaListada[]>();
  for (const comida of comidas) {
    // Sin día asignado (columna nullable) cae en el grupo 0, mostrado como
    // "Sin día asignado" — no se descarta la comida por eso.
    const dia = comida.dia ?? 0;
    const grupo = grupos.get(dia) ?? [];
    grupo.push(comida);
    grupos.set(dia, grupo);
  }
  return grupos;
}

export function PlanDetailModal({
  plan,
  puedeGestionar,
  onClose,
  onEditar,
  onAsignar,
}: PlanDetailModalProps) {
  // Mismo fallback defensivo que PlanCard: objetivo es texto libre en el
  // esquema, un valor fuera del mapa no puede tumbar el modal.
  const { icono: Icono, color } =
    (plan.objetivo && CONFIG_OBJETIVO[plan.objetivo]) || CONFIG_POR_DEFECTO;

  const [comidas, setComidas] = useState<ComidaListada[] | null>(null);

  useEffect(() => {
    let cancelado = false;
    listarComidasDelPlan(plan.idDieta).then((lista) => {
      if (!cancelado) setComidas(lista);
    });
    return () => {
      cancelado = true;
    };
  }, [plan.idDieta]);

  const grupos = comidas ? agruparPorDia(comidas) : null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      // Cerrar tocando afuera. El click dentro del panel se frena con
      // stopPropagation para que no burbujee hasta acá. Sin esto el único
      // camino de salida era el botón "Cerrar" del pie, que en un plan con
      // muchas comidas queda lejos: había que scrollear hasta abajo para poder
      // cerrar algo que sólo se estaba mirando.
      onClick={onClose}
    >
      <div
        className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-lg border border-border-idle bg-surface-card p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <div
              className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 font-body text-xs font-medium"
              style={{ backgroundColor: `${color}1A`, color }}
            >
              <Icono size={14} />
              {plan.objetivo ?? 'Sin objetivo'}
            </div>
            <h2 className="mt-2 font-heading text-lg font-semibold text-text-main">{plan.nombre}</h2>
          </div>
          <StatusBadge status={plan.estado} />
        </div>

        {plan.caloriasDiarias !== undefined && (
          <div className="mt-4 flex items-baseline gap-1.5">
            <span className="font-mono text-4xl font-bold text-text-main">
              {formatearNumero(plan.caloriasDiarias)}
            </span>
            <span className="font-body text-sm text-text-secondary">kcal/día</span>
          </div>
        )}

        {plan.descripcion && (
          <p className="mt-3 font-body text-sm text-text-secondary">{plan.descripcion}</p>
        )}

        <div className="mt-4 flex flex-wrap gap-x-6 gap-y-1 font-body text-sm text-text-secondary">
          <p>
            Nutricionista: <span className="text-text-main">{plan.nutricionista}</span>
          </p>
          <p>
            Asignados: <span className="text-text-main">{plan.asignados} socios</span>
          </p>
        </div>

        <div className="mt-5 border-t border-border-idle pt-4">
          <h3 className="font-heading text-sm font-semibold text-text-main">Plan alimentario</h3>

          {!grupos ? (
            <p className="mt-2 font-body text-sm text-text-muted">Cargando…</p>
          ) : grupos.size === 0 ? (
            <p className="mt-2 font-body text-sm text-text-muted">
              Todavía no hay comidas cargadas para este plan.
            </p>
          ) : (
            <div className="mt-3 flex flex-col gap-4">
              {[...grupos.entries()].map(([dia, delDia]) => (
                <div key={dia}>
                  <p className="font-body text-xs font-semibold tracking-wide text-text-secondary uppercase">
                    {dia === 0 ? 'Sin día asignado' : `Día ${dia}`}
                  </p>
                  <div className="mt-1.5 flex flex-col divide-y divide-border-idle">
                    {delDia.map((comida) => (
                      <div key={comida.idComida} className="flex items-start justify-between gap-3 py-1.5">
                        <div>
                          {comida.momento && (
                            <p className="font-body text-xs text-text-muted">{comida.momento}</p>
                          )}
                          {/* El nombre es el plato del catálogo o el texto
                              libre; la descripción, la del plato si tiene. */}
                          <p className="font-body text-sm text-text-main">{comida.nombre}</p>
                          {comida.descripcion && (
                            <p className="font-body text-xs text-text-muted">{comida.descripcion}</p>
                          )}
                        </div>
                        {comida.calorias !== undefined && (
                          <span className="shrink-0 font-mono text-xs text-text-secondary">
                            {formatearNumero(comida.calorias)} kcal
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="shrink-0 rounded-md px-4 py-2 font-body text-sm whitespace-nowrap text-text-secondary hover:text-text-main"
          >
            Cerrar
          </button>
          {puedeGestionar && (
            <>
              <button
                type="button"
                onClick={onAsignar}
                className="shrink-0 rounded-md border border-border-idle px-4 py-2 font-body text-sm whitespace-nowrap text-text-secondary hover:bg-surface-hover hover:text-text-main"
              >
                Asignar
              </button>
              <PrimaryButton label="Editar" onClick={onEditar} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
