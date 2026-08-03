import { ArrowDownRight, ArrowUpRight, type LucideIcon } from 'lucide-react';

// Equivalente de stat_card (ui.md). El círculo desenfocado al 7% de opacidad
// en la esquina superior derecha es el "artefacto excéntrico" que pide
// DESIGN.md §4 para las tarjetas de métricas.
interface StatCardProps {
  title: string;
  value: string;
  delta?: string;
  tendencia?: 'up' | 'down';
  /**
   * Si el cambio es bueno o malo, cuando eso NO coincide con su dirección.
   *
   * Por defecto se asume "subir es bueno, bajar es malo", que sirve para
   * socios activos, ingresos o clases. Pero no es universal: en el peso de
   * alguien que entrena para bajar, la flecha tiene que apuntar hacia abajo
   * (es la dirección real del cambio) y el color tiene que ser verde (es el
   * resultado que buscaba). Sin este prop, la app le pintaba en rojo al
   * socio los 4,6 kg que había logrado bajar.
   *
   * La flecha la sigue mandando `tendencia`; esto sólo decide el color.
   */
  deltaEsBueno?: boolean;
  icon: LucideIcon;
  color: string;
}

export function StatCard({
  title,
  value,
  delta,
  tendencia,
  deltaEsBueno,
  icon: Icon,
  color,
}: StatCardProps) {
  const TrendIcon = tendencia === 'down' ? ArrowDownRight : ArrowUpRight;
  const bueno = deltaEsBueno ?? tendencia !== 'down';

  return (
    <div className="relative overflow-hidden rounded-lg border border-border-idle bg-surface-card p-5">
      <div
        aria-hidden
        className="pointer-events-none absolute -top-8 -right-8 h-32 w-32 rounded-full blur-2xl"
        style={{ backgroundColor: color, opacity: 0.07 }}
      />
      <div className="relative flex items-center justify-between">
        <span className="font-body text-sm text-text-secondary">{title}</span>
        <Icon size={18} color={color} />
      </div>
      {/* font-mono (JetBrains Mono) exclusivo para métricas — DESIGN.md §6 */}
      <div className="relative mt-2 font-mono text-3xl font-bold text-text-main">
        {value}
      </div>
      {delta && (
        <div
          className={`relative mt-1 flex items-center gap-1 font-body text-xs ${
            bueno ? 'text-status-ok' : 'text-status-danger'
          }`}
        >
          <TrendIcon size={14} />
          {delta}
        </div>
      )}
    </div>
  );
}
