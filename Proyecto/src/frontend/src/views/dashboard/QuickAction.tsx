import type { CSSProperties } from 'react';
import { ChevronRight, type LucideIcon } from 'lucide-react';

// Equivalente de _quick_btn (estructura_dashboard.md): ícono cuadrado
// coloreado | texto | flecha, con hover translúcido y transición de 120ms.
interface QuickActionProps {
  label: string;
  icon: LucideIcon;
  color: string;
  onClick: () => void;
}

export function QuickAction({ label, icon: Icon, color, onClick }: QuickActionProps) {
  // El color de hover es dinámico (depende de la acción), y Tailwind no
  // puede generar clases con valores que se conocen recién en runtime. Se
  // pasa como custom property y la clase la lee con var().
  const estilo = { '--hover-bg': `${color}1A` } as CSSProperties;

  return (
    <button
      type="button"
      onClick={onClick}
      style={estilo}
      className="flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-left transition-colors duration-[120ms] hover:bg-[var(--hover-bg)]"
    >
      <span
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md"
        style={{ backgroundColor: `${color}1A` }}
      >
        <Icon size={16} color={color} />
      </span>
      <span className="flex-1 font-body text-sm text-text-main">{label}</span>
      <ChevronRight size={16} className="text-text-muted" />
    </button>
  );
}
