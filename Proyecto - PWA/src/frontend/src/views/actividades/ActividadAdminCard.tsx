import { Ban, CalendarCheck, GraduationCap, Pencil, Plus, RotateCcw, Users2 } from 'lucide-react';
import { StatusBadge } from '../../components/ui';
import { EstadoRutina } from '../../config';
import type { ActividadAdmin, PlanActividadAdmin, ProfesorAsignable } from '../../services/actividadService';
import { formatearMoneda } from '../../utils/format';

// Actividad + sus planes anidados en una sola card: un plan sin su
// actividad no tiene sentido propio (es "12 clases al mes" ¿de qué?), así
// que se gestionan juntos, mismo criterio que Personal con sus 4 tipos de
// empleado en una sola vista. Los profesores asignados se muestran igual
// (sólo lectura acá) — gestionarlos abre ProfesorAsignacionModal, que es
// donde vive el toggle de verdad.
interface ActividadAdminCardProps {
  actividad: ActividadAdmin;
  planes: PlanActividadAdmin[];
  profesoresAsignados: ProfesorAsignable[];
  onEditarActividad: () => void;
  onDarDeBajaActividad: () => void;
  onReactivarActividad: () => void;
  onNuevoPlan: () => void;
  onEditarPlan: (plan: PlanActividadAdmin) => void;
  onDarDeBajaPlan: (plan: PlanActividadAdmin) => void;
  onReactivarPlan: (plan: PlanActividadAdmin) => void;
  onGestionarProfesores: () => void;
}

function etiquetaLimite(plan: PlanActividadAdmin): string {
  return plan.tipoLimite === 'POR_MES'
    ? `${plan.cantidad} clases/mes`
    : `${plan.cantidad}x por semana`;
}

export function ActividadAdminCard({
  actividad,
  planes,
  profesoresAsignados,
  onEditarActividad,
  onDarDeBajaActividad,
  onReactivarActividad,
  onNuevoPlan,
  onEditarPlan,
  onDarDeBajaPlan,
  onReactivarPlan,
  onGestionarProfesores,
}: ActividadAdminCardProps) {
  const estado = actividad.activa ? EstadoRutina.ACTIVA : EstadoRutina.INACTIVA;

  return (
    <div className="flex flex-col rounded-lg border border-border-idle bg-surface-card p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <CalendarCheck size={18} className="shrink-0 text-primary-volt" />
          <h3 className="truncate font-heading text-lg font-semibold text-text-main">
            {actividad.nombre}
          </h3>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <StatusBadge status={estado} />
          {actividad.activa ? (
            <button
              type="button"
              onClick={onDarDeBajaActividad}
              title="Dar de baja"
              className="rounded-md p-1 text-text-muted hover:bg-surface-hover hover:text-status-danger"
            >
              <Ban size={14} />
            </button>
          ) : (
            <button
              type="button"
              onClick={onReactivarActividad}
              title="Reactivar"
              className="rounded-md p-1 text-text-muted hover:bg-surface-hover hover:text-status-ok"
            >
              <RotateCcw size={14} />
            </button>
          )}
          <button
            type="button"
            onClick={onEditarActividad}
            title="Editar"
            className="rounded-md p-1 text-text-muted hover:bg-surface-hover hover:text-text-main"
          >
            <Pencil size={14} />
          </button>
        </div>
      </div>

      {actividad.descripcion && (
        <p className="mt-1 font-body text-sm text-text-secondary">{actividad.descripcion}</p>
      )}

      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 font-body text-xs text-text-muted">
        <span>Cupo por turno: {actividad.cupoDefault}</span>
        <span>Clase suelta: {formatearMoneda(actividad.precioClaseSuelta)}</span>
        <span>
          Cancelación:{' '}
          {actividad.horasAnticipacionCancelacion === 0
            ? 'sin anticipación'
            : `${actividad.horasAnticipacionCancelacion}hs antes`}
        </span>
      </div>

      <div className="mt-3 flex items-start justify-between gap-3 border-t border-border-idle pt-3">
        <div className="flex min-w-0 flex-wrap items-center gap-1.5">
          {profesoresAsignados.length === 0 ? (
            <span className="font-body text-xs text-text-muted">Sin profesores asignados</span>
          ) : (
            profesoresAsignados.map((profesor) => (
              <span
                key={profesor.idProfesor}
                className="inline-flex items-center gap-1 rounded-full bg-surface-hover px-2.5 py-1 font-body text-xs text-text-secondary"
              >
                <GraduationCap size={11} />
                {profesor.nombre}
              </span>
            ))
          )}
        </div>
        <button
          type="button"
          onClick={onGestionarProfesores}
          title="Asignar profesores"
          className="shrink-0 rounded-md p-1 text-text-muted hover:bg-surface-hover hover:text-text-main"
        >
          <Users2 size={14} />
        </button>
      </div>

      <div className="mt-4 flex flex-col divide-y divide-border-idle border-t border-border-idle">
        {planes.length === 0 ? (
          <p className="py-3 font-body text-sm text-text-muted">Todavía no tiene planes cargados.</p>
        ) : (
          planes.map((plan) => (
            <div key={plan.idPlanActividad} className="flex items-center justify-between gap-3 py-2.5">
              <div className="min-w-0">
                <p className="truncate font-body text-sm text-text-main">{plan.nombre}</p>
                <p className="font-body text-xs text-text-secondary">
                  {etiquetaLimite(plan)} · {formatearMoneda(plan.precio)}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-1.5">
                <StatusBadge status={plan.activo ? EstadoRutina.ACTIVA : EstadoRutina.INACTIVA} />
                {plan.activo ? (
                  <button
                    type="button"
                    onClick={() => onDarDeBajaPlan(plan)}
                    title="Dar de baja"
                    className="rounded-md p-1 text-text-muted hover:bg-surface-hover hover:text-status-danger"
                  >
                    <Ban size={14} />
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => onReactivarPlan(plan)}
                    title="Reactivar"
                    className="rounded-md p-1 text-text-muted hover:bg-surface-hover hover:text-status-ok"
                  >
                    <RotateCcw size={14} />
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => onEditarPlan(plan)}
                  title="Editar"
                  className="rounded-md p-1 text-text-muted hover:bg-surface-hover hover:text-text-main"
                >
                  <Pencil size={14} />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="mt-3">
        <button
          type="button"
          onClick={onNuevoPlan}
          className="flex w-full items-center justify-center gap-2 rounded-md border border-border-idle px-3 py-2 font-body text-sm text-text-secondary transition-colors hover:bg-surface-hover hover:text-text-main"
        >
          <Plus size={14} />
          Nuevo plan
        </button>
      </div>
    </div>
  );
}
