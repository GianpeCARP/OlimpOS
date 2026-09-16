import { useState } from 'react';
import { Eye, EyeOff, type LucideIcon } from 'lucide-react';

// Equivalente de input_field (ui.md). Controlado (value/onChange) en vez
// del ft.Ref que usaba Flet para que el padre lea el valor sin re-render —
// en React lo idiomático es el estado controlado por el padre.
interface InputFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  hint?: string;
  password?: boolean;
  icon?: LucideIcon;
  name?: string;
  // Marca el campo como obligatorio: pinta un * en el label y activa la
  // validación nativa del navegador al enviar el form. Es solo comodidad de
  // UX — la regla de verdad la aplica la capa de services, que es la que
  // mañana reemplaza la API.
  required?: boolean;
  // Tipo de input HTML para los campos que no son texto libre (email, tel,
  // date, number): habilita el teclado correcto en mobile y el chequeo
  // nativo de formato/rango. Se ignora si password está activo.
  type?: 'text' | 'email' | 'tel' | 'date' | 'number' | 'time';
  // Rango del campo. Con type="number" son números; con type="date" son
  // fechas ISO ("2026-09-15"), que es el formato en que el input nativo espera
  // sus límites — por eso aceptan las dos formas y no sólo número.
  min?: number | string;
  max?: number | string;
}

export function InputField({
  label,
  value,
  onChange,
  hint,
  password,
  icon: Icon,
  name,
  required,
  type = 'text',
  min,
  max,
}: InputFieldProps) {
  const [visible, setVisible] = useState(false);
  const inputType = password ? (visible ? 'text' : 'password') : type;

  return (
    <label className="flex flex-col gap-1.5 font-body text-sm">
      <span className="text-text-secondary">
        {label}
        {required && <span className="text-accent-coral"> *</span>}
      </span>
      <div className="flex items-center gap-2 rounded-md border border-border-idle bg-surface-card px-3 py-2 focus-within:border-border-active">
        {Icon && <Icon size={16} className="text-text-muted" />}
        <input
          name={name}
          type={inputType}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          required={required}
          min={min}
          max={max}
          className="w-full bg-transparent text-text-main outline-none placeholder:text-text-muted [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
        />
        {password && (
          <button
            type="button"
            onClick={() => setVisible((v) => !v)}
            className="text-text-muted"
          >
            {visible ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        )}
      </div>
      {hint && <span className="text-xs text-text-muted">{hint}</span>}
    </label>
  );
}
