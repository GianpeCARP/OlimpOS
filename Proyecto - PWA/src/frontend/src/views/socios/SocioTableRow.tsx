import { Dumbbell, Pencil, Phone, RotateCcw, Stethoscope, UserX } from 'lucide-react';
import { StatusBadge } from '../../components/ui';
import { EstadoSocio } from '../../config';
import type { SocioListado } from '../../services/sociosService';
import { formatearFecha } from '../../utils/format';
import { parsearFecha } from '../../utils/fechas';

// Equivalente de _table_row (estructura_socios.md): avatar | nombre | plan |
// badge estado | fecha vence | acciones. El doc pide una sola inicial en el
// avatar; se usan las dos (nombre + apellido) para ser consistentes con
// SocioRow del dashboard, que ya muestra "LF" en vez de "L".
interface SocioTableRowProps {
  socio: SocioListado;
  /** Acceso TOTAL a la sección. False = fila de sólo lectura. */
  puedeEditar: boolean;
  /** Acción `altaBajaSocios` de la matriz de permisos. */
  puedeAltaBaja: boolean;
  /**
   * Acción `verHistorialMedico`. Va separada de `puedeEditar` porque no se
   * deduce del acceso a la sección: el Recepcionista tiene Socios en TOTAL y
   * esta acción en false, y el Entrenador está justo al revés —Socios en
   * LECTURA y la acción en true—. Es la única de la matriz donde el mostrador
   * queda por debajo del Entrenador.
   */
  puedeVerHistorialMedico: boolean;
  onEditar: () => void;
  onEntrenadores: () => void;
  onTelefonos: () => void;
  onDarDeBaja: () => void;
  onActivar: () => void;
  onHistorialMedico: () => void;
}

function iniciales(socio: SocioListado): string {
  return `${socio.nombre.charAt(0)}${socio.apellido.charAt(0)}`.toUpperCase();
}

export function SocioTableRow({
  socio,
  puedeEditar,
  puedeAltaBaja,
  puedeVerHistorialMedico,
  onEditar,
  onEntrenadores,
  onTelefonos,
  onDarDeBaja,
  onActivar,
  onHistorialMedico,
}: SocioTableRowProps) {
  const yaDeBaja = socio.estado === EstadoSocio.DE_BAJA;

  return (
    <tr className="border-b border-border-idle transition-colors duration-[120ms] last:border-b-0 hover:bg-surface-hover">
      <td className="py-3 pl-5">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-surface-hover font-heading text-sm font-bold text-primary-volt">
            {iniciales(socio)}
          </div>
          <div className="min-w-0">
            <p className="truncate font-body text-sm text-text-main">{socio.nombreCompleto}</p>
            <p className="truncate font-body text-xs text-text-muted">DNI {socio.dni}</p>
          </div>
        </div>
      </td>
      <td className="py-3 font-body text-sm text-text-secondary">{socio.plan}</td>
      <td className="py-3">
        <StatusBadge status={socio.estado} />
      </td>
      <td className="py-3 font-body text-sm text-text-secondary">
        {socio.vencimiento ? formatearFecha(parsearFecha(socio.vencimiento)) : '—'}
      </td>
      <td className="py-3 pr-5">
        <div className="flex items-center justify-end gap-1">
          {/* Sin acceso TOTAL la fila es de sólo lectura: se ven los datos
              del socio (para saber a quién asignarle una rutina o dieta)
              pero no se puede tocar nada. */}
          {puedeEditar && (
            <button
              type="button"
              onClick={onEditar}
              title="Editar socio"
              className="rounded-md p-2 text-text-muted hover:bg-surface-card hover:text-text-main"
            >
              <Pencil size={16} />
            </button>
          )}
          {/* Los teléfonos se muestran a todos los que ven la grilla: saber
              cómo llamar a un socio no es un dato reservado, y el entrenador
              que lo tiene a cargo es justamente quien más lo necesita. Los
              controles para agregar y borrar sí están restringidos adentro
              del modal. */}
          <button
            type="button"
            onClick={onTelefonos}
            title="Teléfonos"
            className="rounded-md p-2 text-text-muted hover:bg-surface-card hover:text-primary-volt"
          >
            <Phone size={16} />
          </button>
          {/* Este SÍ se muestra a todos los que ven la grilla, incluido el
              Entrenador que la tiene en LECTURA: quién entrena a quién no es
              un dato sensible, y esconderlo justo al entrenador sería
              esconderle lo suyo. Lo que se restringe adentro del modal son
              los controles de asignar y finalizar. */}
          <button
            type="button"
            onClick={onEntrenadores}
            title="Entrenadores a cargo"
            className="rounded-md p-2 text-text-muted hover:bg-surface-card hover:text-primary-volt"
          >
            <Dumbbell size={16} />
          </button>
          {/* Se OMITE, no se deshabilita, para quien no tenga la acción. Un
              botón gris que no responde igual delata que el socio tiene algo
              cargado, y el punto de que el Recepcionista no vea esto es que no
              se entere. */}
          {puedeVerHistorialMedico && (
            <button
              type="button"
              onClick={onHistorialMedico}
              title="Historial médico"
              className="rounded-md p-2 text-text-muted hover:bg-surface-card hover:text-primary-volt"
            >
              <Stethoscope size={16} />
            </button>
          )}
          {/* Un solo botón que cambia de acción según el estado: UserX para
              dar de baja a un socio activo, RotateCcw para reactivar uno ya
              dado de baja — antes solo existía el camino de ida. */}
          {!puedeAltaBaja ? null : yaDeBaja ? (
            <button
              type="button"
              onClick={onActivar}
              title="Reactivar"
              className="rounded-md p-2 text-text-muted hover:bg-surface-card hover:text-status-ok"
            >
              <RotateCcw size={16} />
            </button>
          ) : (
            <button
              type="button"
              onClick={onDarDeBaja}
              title="Dar de baja"
              className="rounded-md p-2 text-text-muted hover:bg-surface-card hover:text-status-danger"
            >
              <UserX size={16} />
            </button>
          )}
        </div>
      </td>
    </tr>
  );
}
