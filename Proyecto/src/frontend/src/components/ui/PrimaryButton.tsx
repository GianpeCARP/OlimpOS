import type { LucideIcon } from 'lucide-react';

// Equivalente de primary_button (ui.md). Fondo primary-volt + texto oscuro,
// como pide DESIGN.md §4 para botones primarios.
interface PrimaryButtonProps {
  label: string;
  icon?: LucideIcon;
  onClick?: () => void;
  width?: number | string;
  disabled?: boolean;
  type?: 'button' | 'submit';
}

export function PrimaryButton({
  label,
  icon: Icon,
  onClick,
  width,
  disabled,
  type = 'button',
}: PrimaryButtonProps) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      style={width ? { width } : undefined}
      className="flex items-center justify-center gap-2 rounded-md bg-primary-volt px-5 py-2.5 font-body text-sm font-semibold text-surface-base transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
    >
      {Icon && <Icon size={16} />}
      {label}
    </button>
  );
}
