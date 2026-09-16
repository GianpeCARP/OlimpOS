import { useState } from 'react';
import { Phone, type LucideIcon } from 'lucide-react';
import {
  PAISES,
  limpiarNumeroLocal,
  separarTelefono,
  unirTelefono,
} from '../../utils/telefono';

// Campo de teléfono con código de país. Mismo label/borde/foco que InputField
// para que se vea de la misma familia. Gemelo de telefono_field en
// app/components/ui.py (Flet).
//
// `value` y `onChange` manejan el número COMPLETO ("+54 3415551234"): quien lo
// usa no sabe que hay un selector adentro, guarda y manda lo mismo que antes.
// El país vive en estado propio porque, con el número vacío, `value` es "" y no
// guarda qué país se eligió.

interface TelefonoFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  hint?: string;
  icon?: LucideIcon;
  name?: string;
  required?: boolean;
}

export function TelefonoField({
  label,
  value,
  onChange,
  hint,
  icon: Icon = Phone,
  name,
  required,
}: TelefonoFieldProps) {
  const inicial = separarTelefono(value);
  const [prefijo, setPrefijo] = useState(inicial.prefijo);
  const numero = separarTelefono(value).numero;

  return (
    <label className="flex flex-col gap-1.5 font-body text-sm">
      <span className="text-text-secondary">
        {label}
        {required && <span className="text-accent-coral"> *</span>}
      </span>
      <div className="flex items-center gap-2 rounded-md border border-border-idle bg-surface-card px-3 py-2 focus-within:border-border-active">
        {Icon && <Icon size={16} className="shrink-0 text-text-muted" />}
        <select
          aria-label="País"
          value={prefijo}
          onChange={(e) => {
            setPrefijo(e.target.value);
            onChange(unirTelefono(e.target.value, numero));
          }}
          className="shrink-0 appearance-none bg-transparent font-mono text-text-main outline-none [&>option]:bg-surface-card"
        >
          {PAISES.map((p) => (
            <option key={p.prefijo} value={p.prefijo}>
              {p.bandera} {p.prefijo}
            </option>
          ))}
        </select>
        <span className="h-4 w-px shrink-0 bg-border-idle" />
        <input
          name={name}
          type="tel"
          value={numero}
          onChange={(e) => onChange(unirTelefono(prefijo, limpiarNumeroLocal(e.target.value)))}
          required={required}
          className="w-full min-w-0 bg-transparent text-text-main outline-none placeholder:text-text-muted"
        />
      </div>
      {hint && <span className="text-xs text-text-muted">{hint}</span>}
    </label>
  );
}
