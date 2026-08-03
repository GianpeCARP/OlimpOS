import { colors } from '../../config';

// Equivalente de level_badge + LEVEL_COLORS (ui.md). Mismo caso que
// StatusBadge: sin strings/colores reales en los docs, mapa provisorio.
const LEVEL_COLORS: Record<string, string> = {
  Principiante: colors.statusOk,
  Intermedio: colors.statusWarn,
  Avanzado: colors.accentCoral,
};

interface LevelBadgeProps {
  nivel: string;
}

export function LevelBadge({ nivel }: LevelBadgeProps) {
  const color = LEVEL_COLORS[nivel] ?? colors.textMuted;
  return (
    <span
      className="inline-flex items-center rounded-full px-3 py-1 font-body text-xs font-medium"
      style={{ backgroundColor: `${color}1A`, color }}
    >
      {nivel}
    </span>
  );
}
