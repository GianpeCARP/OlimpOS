import { ChevronDown, type LucideIcon } from 'lucide-react';

// Hermano de InputField para <select>: mismo label/borde/foco, para que un
// formulario con inputs y dropdowns mezclados se vea como una sola familia
// de componentes. Value siempre es string (así es un <select> nativo); el
// que arma las opciones decide qué representa cada value (un id, un enum).
export interface SelectOption {
  value: string;
  label: string;
}

interface SelectFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
  /** Texto de la opción vacía (value=""), p. ej. "Sin plan asignado". */
  placeholder?: string;
  icon?: LucideIcon;
  name?: string;
  required?: boolean;
}

export function SelectField({
  label,
  value,
  onChange,
  options,
  placeholder,
  icon: Icon,
  name,
  required,
}: SelectFieldProps) {
  return (
    <label className="flex flex-col gap-1.5 font-body text-sm">
      <span className="text-text-secondary">
        {label}
        {required && <span className="text-accent-coral"> *</span>}
      </span>
      <div className="flex items-center gap-2 rounded-md border border-border-idle bg-surface-card px-3 py-2 focus-within:border-border-active">
        {Icon && <Icon size={16} className="text-text-muted" />}
        <select
          name={name}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          required={required}
          className="w-full appearance-none bg-transparent text-text-main outline-none [&>option]:bg-surface-card"
        >
          {placeholder !== undefined && <option value="">{placeholder}</option>}
          {options.map((opcion) => (
            <option key={opcion.value} value={opcion.value}>
              {opcion.label}
            </option>
          ))}
        </select>
        <ChevronDown size={16} className="shrink-0 text-text-muted" />
      </div>
    </label>
  );
}
