// Equivalente de _build_filter_chip (estructura_socios.md): pastilla
// clickeable, resaltada cuando es el filtro activo.
//
// Vive en components/ui/ y no dentro de una vista porque lo usan tanto la
// tabla de socios (filtro por estado) como la grilla de personal (filtro
// por rol), y cualquier listado que venga después va a querer lo mismo.
interface FilterChipProps {
  label: string;
  activo: boolean;
  onClick: () => void;
}

export function FilterChip({ label, activo, onClick }: FilterChipProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-4 py-1.5 font-body text-sm font-medium transition-colors ${
        activo
          ? 'bg-primary-volt text-surface-base'
          : 'border border-border-idle text-text-secondary hover:bg-surface-hover hover:text-text-main'
      }`}
    >
      {label}
    </button>
  );
}
