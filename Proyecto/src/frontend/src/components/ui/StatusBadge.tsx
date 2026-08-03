import { colors, EstadoEmpleado, EstadoRutina, EstadoSocio, EstadoUsuario } from '../../config';

// Equivalente de status_badge + STATUS_COLORS (ui.md). Las claves salen de
// EstadoSocio (config.ts) y no de literales sueltos: el service calcula el
// estado con esa misma constante, así que si el texto cambia, cambia de los
// dos lados a la vez. Cualquier status sin match cae en el color neutro.
const STATUS_COLORS: Record<string, string> = {
  [EstadoSocio.ACTIVO]: colors.statusOk,
  [EstadoSocio.POR_VENCER]: colors.statusWarn,
  [EstadoSocio.VENCIDO]: colors.statusDanger,
  [EstadoSocio.SUSPENDIDO]: colors.statusWarn,
  [EstadoSocio.DE_BAJA]: colors.statusDanger,
  // EstadoEmpleado.ACTIVO es el mismo literal 'Activo' que EstadoSocio.ACTIVO
  // — una sola entrada cubre a los dos, no hace falta repetirla.
  [EstadoEmpleado.INACTIVO]: colors.textMuted,
  [EstadoRutina.ACTIVA]: colors.statusOk,
  [EstadoRutina.INACTIVA]: colors.textMuted,
  [EstadoUsuario.BLOQUEADO]: colors.statusDanger,
  // SIN_MEMBRESIA no se lista: el neutro por defecto es justo lo que
  // corresponde a un socio recién dado de alta al que todavía no se le
  // cargó el plan.
};

interface StatusBadgeProps {
  status: string;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const color = STATUS_COLORS[status] ?? colors.textMuted;
  return (
    <span
      className="inline-flex items-center rounded-full px-3 py-1 font-body text-xs font-medium"
      style={{ backgroundColor: `${color}1A`, color }}
    >
      {status}
    </span>
  );
}
