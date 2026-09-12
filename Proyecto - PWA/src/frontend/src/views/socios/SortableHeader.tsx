import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-react';

// Encabezado de columna clickeable para ordenar. estructura_socios.md solo
// describe esto para "Nombre" (con ícono SORT + toggle ascendente/
// descendente) — el mismo mecanismo se reusa para "Vence" y "Estado", que
// son criterios de orden igual de útiles para el staff y no estaban
// cubiertos en el doc (ver comentario en SociosView).
//
// El doc pide el header en Colors.SUCCESS (verde), de la paleta vieja de
// Flet — se ignora, como el resto de esos valores stale, y se usa el mismo
// gris secundario que el resto de los títulos de sección.
interface SortableHeaderProps<T extends string> {
  label: string;
  campo: T;
  ordenActual: T;
  ascendente: boolean;
  onClick: (campo: T) => void;
  className?: string;
}

export function SortableHeader<T extends string>({
  label,
  campo,
  ordenActual,
  ascendente,
  onClick,
  className = '',
}: SortableHeaderProps<T>) {
  const activo = ordenActual === campo;

  return (
    <button
      type="button"
      onClick={() => onClick(campo)}
      className={`flex items-center gap-1 font-body text-xs font-semibold tracking-wide text-text-secondary uppercase hover:text-text-main ${className}`}
    >
      {label}
      {activo ? (
        ascendente ? (
          <ArrowUp size={12} />
        ) : (
          <ArrowDown size={12} />
        )
      ) : (
        <ArrowUpDown size={12} className="opacity-40" />
      )}
    </button>
  );
}
