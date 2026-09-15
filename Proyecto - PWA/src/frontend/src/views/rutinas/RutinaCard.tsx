import { Ban, Calendar, Dumbbell, RotateCcw, Target, User } from 'lucide-react';
import { LevelBadge, PrimaryButton, StatusBadge } from '../../components/ui';
import { EstadoRutina } from '../../config';
import type { RutinaListado } from '../../services/rutinasService';
import { InfoPill } from './InfoPill';

// Equivalente de _rutina_card (estructura_rutinas.md). El segundo pill
// muestra `objetivo` en vez de una "duración" que Rutina no tiene como
// columna — ver el comentario grande en rutinasService.ts. El StatusBadge +
// el botón de baja/reactivación del encabezado no están en el doc — mismo
// patrón que StaffCard, agregado porque Rutina sí tiene `activo` en el
// esquema.
interface RutinaCardProps {
  rutina: RutinaListado;
  /** False para roles con acceso de sólo lectura (p. ej. Nutricionista). */
  puedeGestionar: boolean;
  onVerDetalle: () => void;
  onAsignar: () => void;
  onDarDeBaja: () => void;
  onActivar: () => void;
}

export function RutinaCard({
  rutina,
  puedeGestionar,
  onVerDetalle,
  onAsignar,
  onDarDeBaja,
  onActivar,
}: RutinaCardProps) {
  const porcentaje = Math.round(rutina.progreso * 100);
  const yaInactiva = rutina.estado === EstadoRutina.INACTIVA;

  return (
    <div className="flex flex-col rounded-lg border border-border-idle bg-surface-card p-5">
      <div className="flex items-start justify-between">
        <Dumbbell size={20} className="text-primary-volt" />
        <div className="flex items-center gap-1.5">
          <StatusBadge status={rutina.estado} />
          {/* Un solo botón que cambia de acción según el estado: Ban para
              dar de baja una rutina activa, RotateCcw para reactivar una ya
              inactiva. Ban en vez de UserX: acá no se da de baja a una
              persona. Con acceso de sólo lectura no se dibuja ninguno. */}
          {!puedeGestionar ? null : yaInactiva ? (
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
              <Ban size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Nivel en su propia línea, no al lado del nombre: compartir fila
          con un badge le quitaba ancho al truncate y recortaba nombres que
          antes entraban enteros. */}
      <h3 className="mt-3 truncate font-heading text-lg font-semibold text-text-main">
        {rutina.nombre}
      </h3>
      {rutina.nivel && (
        <div className="mt-1.5">
          <LevelBadge nivel={rutina.nivel} />
        </div>
      )}

      <div className="mt-3 flex flex-wrap gap-2">
        {rutina.diasPorSemana !== undefined && (
          <InfoPill icon={Calendar} text={`${rutina.diasPorSemana} días/sem`} />
        )}
        {rutina.objetivo && <InfoPill icon={Target} text={rutina.objetivo} />}
        {/* Quién la armó: con las rutinas de todo el plantel a la vista, es lo
            que explica por qué algunas no tienen botones. */}
        <InfoPill icon={User} text={rutina.entrenador} />
      </div>

      <p className="mt-4 font-body text-sm text-text-secondary">
        Asignados: <span className="text-text-main">{rutina.asignados}</span> socios
      </p>

      {/* Barra de progreso, color ACCENT según el doc — acá accent-coral. */}
      <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-surface-hover">
        <div
          className="h-full rounded-full bg-accent-coral transition-[width]"
          style={{ width: `${porcentaje}%` }}
        />
      </div>

      <div className="mt-auto flex gap-2 pt-5">
        <button
          type="button"
          onClick={onVerDetalle}
          className="flex flex-1 items-center justify-center rounded-md border border-border-idle px-3 py-2 font-body text-sm text-text-secondary transition-colors hover:bg-surface-hover hover:text-text-main"
        >
          Ver detalles
        </button>
        {/* Asignar una rutina a un socio es gestionarla: sólo el Entrenador. */}
        {puedeGestionar && (
          <div className="flex-1">
            <PrimaryButton label="Asignar" onClick={onAsignar} width="100%" />
          </div>
        )}
      </div>
    </div>
  );
}
