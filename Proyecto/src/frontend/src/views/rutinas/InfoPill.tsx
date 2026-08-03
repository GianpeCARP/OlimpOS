import type { LucideIcon } from 'lucide-react';

// Equivalente de _info_pill (estructura_rutinas.md): chip compacto con
// ícono + texto, fondo neutro. El doc pide Colors.BG_SIDEBAR (paleta
// vieja) — acá se usa surface-hover, el mismo neutro que ya usa el resto
// de la UI (p. ej. el avatar circular de las tarjetas de socio/personal).
interface InfoPillProps {
  icon: LucideIcon;
  text: string;
}

export function InfoPill({ icon: Icon, text }: InfoPillProps) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-surface-hover px-3 py-1 font-body text-xs text-text-secondary">
      <Icon size={12} />
      {text}
    </span>
  );
}
