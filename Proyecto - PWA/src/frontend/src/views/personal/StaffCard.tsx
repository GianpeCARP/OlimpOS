import {
  Clock,
  Dumbbell,
  GraduationCap,
  Headset,
  Mail,
  MessageCircle,
  Pencil,
  RotateCcw,
  UserX,
  UtensilsCrossed,
  type LucideIcon,
} from 'lucide-react';
import { StatusBadge } from '../../components/ui';
import {
  colors,
  EstadoEmpleado,
  RolEmpleado,
  TurnoLaboral,
  type RolEmpleadoValue,
  type TurnoLaboralValue,
} from '../../config';
import type { EmpleadoListado } from '../../services/personalService';
import { linkMail, linkWhatsapp } from '../../utils/contacto';

// Equivalente de _staff_card + ROL_ICONS + TURNO_COLORS
// (estructura_personal.md).

const ICONOS_ROL: Record<RolEmpleadoValue, LucideIcon> = {
  [RolEmpleado.ENTRENADOR]: Dumbbell,
  [RolEmpleado.NUTRICIONISTA]: UtensilsCrossed,
  [RolEmpleado.RECEPCIONISTA]: Headset,
  [RolEmpleado.PROFESOR]: GraduationCap,
};

// El doc pide azul para "Tarde" y violeta para "Noche"; Kinetic Carbon
// (DESIGN.md) es una paleta oscura sin azul ni violeta, así que se usan los
// acentos que sí existen. "Mañana" sí coincide: amarillo en los dos.
const COLORES_TURNO: Record<TurnoLaboralValue, string> = {
  [TurnoLaboral.MANANA]: colors.statusWarn,
  [TurnoLaboral.TARDE]: colors.accentCoral,
  [TurnoLaboral.NOCHE]: colors.primaryVolt,
};

/**
 * A dónde escribirle a un empleado, y con qué ícono.
 *
 * El mail gana cuando están los dos: es la vía donde una contraseña o un aviso
 * del gimnasio quedan guardados y buscables, mientras que un WhatsApp se
 * pierde en la conversación. El teléfono es el respaldo para quien no dejó
 * mail — que es la mitad de los casos reales.
 */
function vinculoDeContacto(
  empleado: EmpleadoListado,
): { href: string; titulo: string; Icono: LucideIcon } | null {
  if (empleado.email) {
    return {
      href: linkMail(empleado.email),
      titulo: `Escribir a ${empleado.email}`,
      Icono: Mail,
    };
  }
  if (empleado.telefono) {
    return {
      href: linkWhatsapp(empleado.telefono),
      titulo: `WhatsApp a ${empleado.telefono}`,
      Icono: MessageCircle,
    };
  }
  return null;
}

interface StaffCardProps {
  empleado: EmpleadoListado;
  /** Acceso TOTAL a la sección. False = tarjeta de sólo lectura. */
  puedeEditar: boolean;
  /**
   * Ya viene resuelto con la regla de fila aplicada (nadie se da de baja a
   * sí mismo) — la tarjeta no tiene por qué conocer quién está logueado.
   */
  puedeDarDeBaja: boolean;
  onEditar: () => void;
  onDarDeBaja: () => void;
  onActivar: () => void;
}

export function StaffCard({
  empleado,
  puedeEditar,
  puedeDarDeBaja,
  onEditar,
  onDarDeBaja,
  onActivar,
}: StaffCardProps) {
  const IconoRol = ICONOS_ROL[empleado.rol];
  const contacto = vinculoDeContacto(empleado);
  // Solo los recepcionistas tienen turno; para el resto el chip lleva el
  // color neutro y muestra su dato propio (especialidad o título).
  const colorChip = empleado.turno ? COLORES_TURNO[empleado.turno] : colors.textSecondary;
  const yaInactivo = empleado.estado === EstadoEmpleado.INACTIVO;

  return (
    <div className="flex flex-col rounded-lg border border-border-idle bg-surface-card p-5">
      <div className="flex items-start justify-between">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-surface-hover font-heading text-base font-bold text-primary-volt">
          {empleado.iniciales}
        </div>
        <div className="flex items-center gap-1.5">
          <StatusBadge status={empleado.estado} />
          {/* Un solo botón que cambia de acción según el estado: UserX para
              dar de baja a un empleado activo, RotateCcw para reactivar uno
              ya inactivo — antes solo existía el camino de ida. Sin permiso
              (o si es la propia ficha del usuario) no se dibuja ninguno. */}
          {!puedeDarDeBaja ? null : yaInactivo ? (
            <button
              type="button"
              onClick={onActivar}
              title="Reactivar"
              className="rounded-md p-1 text-text-muted hover:bg-surface-hover hover:text-status-ok"
            >
              <RotateCcw size={14} />
            </button>
          ) : (
            <button
              type="button"
              onClick={onDarDeBaja}
              title="Dar de baja"
              className="rounded-md p-1 text-text-muted hover:bg-surface-hover hover:text-status-danger"
            >
              <UserX size={14} />
            </button>
          )}
        </div>
      </div>

      <h3 className="mt-3 truncate font-heading text-lg font-semibold text-text-main">
        {empleado.nombreCompleto}
      </h3>

      <div className="mt-1 flex items-center gap-2 font-body text-sm text-text-secondary">
        <IconoRol size={14} />
        <span className="truncate">{empleado.rol}</span>
      </div>

      {/* Chip del dato propio del rol. Si el campo está vacío en la base no
          se dibuja nada, en vez de un chip con texto de relleno. */}
      {empleado.detalle && (
        <div
          className="mt-3 inline-flex w-fit max-w-full items-center gap-1.5 rounded-full px-3 py-1 font-body text-xs font-medium"
          style={{ backgroundColor: `${colorChip}1A`, color: colorChip }}
        >
          {empleado.turno && <Clock size={12} className="shrink-0" />}
          <span className="truncate">{empleado.detalle}</span>
        </div>
      )}

      {/* mt-auto empuja los botones al pie: las tarjetas de una misma fila
          tienen alto distinto según cuántos datos tenga cada empleado. */}
      <div className="mt-auto flex gap-2 pt-5">
        {/* Con acceso de sólo lectura queda únicamente "Contactar": el
            Recepcionista necesita poder llamar a un compañero, no editarle
            la ficha. */}
        {puedeEditar && (
          <button
            type="button"
            onClick={onEditar}
            className="flex flex-1 items-center justify-center gap-2 rounded-md border border-border-idle px-3 py-2 font-body text-sm text-text-secondary transition-colors hover:bg-surface-hover hover:text-text-main"
          >
            <Pencil size={14} />
            Editar
          </button>
        )}
        {/* "Contactar" abre el mail o el WhatsApp, según lo que tenga cargado
            (ver `contacto` más arriba). Desde que el alta exige al menos una
            de las dos vías, un empleado nuevo siempre tiene a dónde: el estado
            apagado queda para las fichas viejas, cargadas antes de esa regla,
            y es la señal de que a esa persona hay que completarle el contacto. */}
        {contacto ? (
          <a
            href={contacto.href}
            // Los dos destinos son páginas —wa.me y el redactor de Gmail—, así
            // que los dos van en pestaña nueva y el panel no se pierde. Ojo: el
            // mail NO es un mailto: (ver linkMail en utils/contacto.ts); con un
            // mailto: esta pestaña quedaba en blanco y no pasaba nada.
            target="_blank"
            rel="noreferrer"
            title={contacto.titulo}
            className="flex flex-1 items-center justify-center gap-2 rounded-md border border-border-idle px-3 py-2 font-body text-sm text-text-secondary transition-colors hover:bg-surface-hover hover:text-text-main"
          >
            <contacto.Icono size={14} />
            Contactar
          </a>
        ) : (
          <span
            title="Sin email ni teléfono cargados"
            className="flex flex-1 cursor-not-allowed items-center justify-center gap-2 rounded-md border border-border-idle px-3 py-2 font-body text-sm text-text-muted opacity-40"
          >
            <Mail size={14} />
            Contactar
          </span>
        )}
      </div>
    </div>
  );
}
