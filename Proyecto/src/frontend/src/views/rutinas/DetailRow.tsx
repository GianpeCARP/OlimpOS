// Equivalente de _detail_row (estructura_rutinas.md): label muted con
// ancho fijo a la izquierda, valor a la derecha.
interface DetailRowProps {
  label: string;
  value: string;
}

export function DetailRow({ label, value }: DetailRowProps) {
  return (
    <div className="flex gap-3 py-1.5 font-body text-sm">
      <span className="w-[100px] shrink-0 text-text-muted">{label}</span>
      <span className="text-text-main">{value}</span>
    </div>
  );
}
