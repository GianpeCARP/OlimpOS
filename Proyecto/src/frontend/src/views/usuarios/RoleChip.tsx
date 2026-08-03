import { Apple, Dumbbell, Headset, Shield, User, type LucideIcon } from 'lucide-react';
import { colors, Roles, type RolValue } from '../../config';

// Equivalente de ROLE_CONFIG (estructura_usuarios.md). El doc tenía 4 roles
// de sistema inventados (admin/trainer/staff/nutri); estos son los reales,
// derivados del esquema: Dueño + los tres subtipos de Empleado + Socio.
//
// Los íconos coinciden con los que ya usa StaffCard para los mismos roles
// (Dumbbell/Apple-ish/Headset), para que un entrenador se vea igual en las
// dos pantallas.
const CONFIG_ROL: Record<RolValue, { icono: LucideIcon; color: string }> = {
  [Roles.DUENO]: { icono: Shield, color: colors.accentCoral },
  [Roles.RECEPCIONISTA]: { icono: Headset, color: colors.statusWarn },
  [Roles.ENTRENADOR]: { icono: Dumbbell, color: colors.statusOk },
  [Roles.NUTRICIONISTA]: { icono: Apple, color: colors.primaryVolt },
  [Roles.SOCIO]: { icono: User, color: colors.textSecondary },
};

interface RoleChipProps {
  rol: RolValue;
  label: string;
}

export function RoleChip({ rol, label }: RoleChipProps) {
  const { icono: Icono, color } = CONFIG_ROL[rol];
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 font-body text-xs font-medium"
      style={{ backgroundColor: `${color}1A`, color }}
    >
      <Icono size={12} />
      {label}
    </span>
  );
}
