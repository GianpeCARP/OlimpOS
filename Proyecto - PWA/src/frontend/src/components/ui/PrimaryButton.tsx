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
      // shrink-0 y whitespace-nowrap: los dos arreglan el MISMO bug, que en un
      // celular se veia como el boton reducido a la letra "G" y una franja de
      // color.
      //
      // El boton es un flex ITEM de su contenedor, y flex-shrink vale 1 por
      // defecto: cuando el ancho no alcanza —una pantalla angosta— el
      // contenedor lo comprime POR DEBAJO de su contenido y le recorta el
      // texto. Por eso "Guardando..." entraba y "Guardar cambios", que es mas
      // largo, no.
      //
      // shrink-0 le prohibe encogerse; whitespace-nowrap le prohibe partir la
      // etiqueta en dos lineas, que es lo que haria si igual quedara justo.
      // Un boton primario nunca deberia ceder ancho: si algo tiene que
      // achicarse en una fila, es el texto de al lado, no la accion.
      className="flex shrink-0 items-center justify-center gap-2 rounded-md bg-primary-volt px-5 py-2.5 font-body text-sm font-semibold whitespace-nowrap text-surface-base transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
    >
      {Icon && <Icon size={16} />}
      {label}
    </button>
  );
}
