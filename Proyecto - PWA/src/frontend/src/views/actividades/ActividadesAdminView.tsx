import { useCallback, useEffect, useState } from 'react';
import { Plus } from 'lucide-react';
import { AgendaTurnos } from '../../components/AgendaTurnos';
import { PrimaryButton, SectionCard, Topbar } from '../../components/ui';
import { colors } from '../../config';
import { mensajeDeError } from '../../services/api';
import {
  darDeBajaActividad,
  darDeBajaPlanActividad,
  getActividadesAdmin,
  getPlanesDeActividadAdmin,
  getProfesoresDeActividad,
  reactivarActividad,
  reactivarPlanActividad,
  type ActividadAdmin,
  type PlanActividadAdmin,
  type ProfesorAsignable,
} from '../../services/actividadService';
import {
  darDeBajaHorario,
  getHorarios,
  regenerarTurnos,
  type Horario,
} from '../../services/turnosService';
import { usePuedeAccion } from '../../hooks/usePermisos';
import { useAuthStore } from '../../store/authStore';
import { useUiStore } from '../../store/uiStore';
import { ActividadAdminCard } from './ActividadAdminCard';
import { ActividadFormModal } from './ActividadFormModal';
import { HorarioFormModal } from './HorarioFormModal';
import { HorarioSemanal } from './HorarioSemanal';
import { PlanFormModal } from './PlanFormModal';
import { ProfesorAsignacionModal } from './ProfesorAsignacionModal';

// ABM del catálogo de actividades (especificacion_definitiva_actividades.md,
// Fase 4). Dueño y Recepcionista — ver el comentario de ACTIVIDADES en
// config.ts. Además del catálogo tiene el horario semanal (de ahí salen los
// turnos) y la agenda de los próximos turnos con quién se anotó.
//
// Después de CUALQUIER mutación se recarga todo (`recargar`) en vez de
// parchear el estado local: acá conviven dos entidades anidadas (actividad
// + sus planes) y un parche quirúrgico duplicaría en el frontend la misma
// lógica que ya vive en el service, para una pantalla que no se usa a cada
// rato.

interface DatosAdmin {
  actividades: ActividadAdmin[];
  planesPorActividad: Map<number, PlanActividadAdmin[]>;
  profesoresPorActividad: Map<number, ProfesorAsignable[]>;
  horarios: Horario[];
}

function Skeleton({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-md bg-surface-hover ${className}`} />;
}

export function ActividadesAdminView() {
  const idUsuarioActor = useAuthStore((s) => s.usuario?.id_usuario);
  const showSnack = useUiStore((s) => s.showSnack);
  const confirmDialog = useUiStore((s) => s.confirmDialog);
  const puedeGestionarTurnos = usePuedeAccion('gestionTurnos');

  const [datos, setDatos] = useState<DatosAdmin | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intento, setIntento] = useState(0);

  const [actividadEnForm, setActividadEnForm] = useState<ActividadAdmin | 'nueva' | null>(null);
  const [planEnForm, setPlanEnForm] = useState<{
    idActividad: number;
    plan: PlanActividadAdmin | null;
  } | null>(null);
  const [actividadParaProfesores, setActividadParaProfesores] = useState<ActividadAdmin | null>(null);
  const [horarioNuevo, setHorarioNuevo] = useState(false);

  useEffect(() => {
    setDatos(null);
    setError(null);

    getActividadesAdmin()
      .then(async (actividades) => {
        const [listasDePlanes, listasDeProfesores, horarios] = await Promise.all([
          Promise.all(actividades.map((a) => getPlanesDeActividadAdmin(a.idActividad))),
          Promise.all(actividades.map((a) => getProfesoresDeActividad(a.idActividad))),
          getHorarios(),
        ]);
        const planesPorActividad = new Map<number, PlanActividadAdmin[]>();
        const profesoresPorActividad = new Map<number, ProfesorAsignable[]>();
        actividades.forEach((a, i) => {
          planesPorActividad.set(a.idActividad, listasDePlanes[i]);
          profesoresPorActividad.set(a.idActividad, listasDeProfesores[i]);
        });
        setDatos({ actividades, planesPorActividad, profesoresPorActividad, horarios });
      })
      .catch((err: unknown) => setError(mensajeDeError(err)));
  }, [intento]);

  const recargar = useCallback(() => setIntento((n) => n + 1), []);

  const pedirBajaActividad = useCallback(
    (actividad: ActividadAdmin) => {
      confirmDialog(
        `¿Dar de baja "${actividad.nombre}"?`,
        'Deja de aparecer en el catálogo para compras nuevas. Las inscripciones ya activas no se ven afectadas.',
        () => {
          darDeBajaActividad(actividad.idActividad, idUsuarioActor)
            .then(() => {
              showSnack(`"${actividad.nombre}" fue dada de baja`, colors.statusOk);
              recargar();
            })
            .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
        },
      );
    },
    [confirmDialog, idUsuarioActor, showSnack, recargar],
  );

  // Sin confirmación: reactivar es reversible (siempre se puede volver a
  // dar de baja), mismo criterio que Rutinas/Personal.
  const reactivarActividadClick = useCallback(
    (actividad: ActividadAdmin) => {
      reactivarActividad(actividad.idActividad, idUsuarioActor)
        .then(() => {
          showSnack(`"${actividad.nombre}" fue reactivada`, colors.statusOk);
          recargar();
        })
        .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
    },
    [idUsuarioActor, showSnack, recargar],
  );

  const pedirBajaPlan = useCallback(
    (plan: PlanActividadAdmin) => {
      confirmDialog(
        `¿Dar de baja "${plan.nombre}"?`,
        'Deja de poder comprarse. Quienes ya lo tengan activo siguen usándolo hasta que venza.',
        () => {
          darDeBajaPlanActividad(plan.idPlanActividad, idUsuarioActor)
            .then(() => {
              showSnack(`"${plan.nombre}" fue dado de baja`, colors.statusOk);
              recargar();
            })
            .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
        },
      );
    },
    [confirmDialog, idUsuarioActor, showSnack, recargar],
  );

  const reactivarPlanClick = useCallback(
    (plan: PlanActividadAdmin) => {
      reactivarPlanActividad(plan.idPlanActividad, idUsuarioActor)
        .then(() => {
          showSnack(`"${plan.nombre}" fue reactivado`, colors.statusOk);
          recargar();
        })
        .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
    },
    [idUsuarioActor, showSnack, recargar],
  );

  // Dar de baja un horario = "no generes más", NO "borrá lo que ya existe":
  // los turnos futuros ya generados pueden tener gente anotada. Si hay que
  // sacar alguno, se cancela desde la agenda. Mismo criterio que Flet.
  const pedirBajaHorario = useCallback(
    (horario: Horario) => {
      confirmDialog(
        `¿Dar de baja ${horario.actividad} — ${horario.diaNombre} ${horario.hora}?`,
        `Deja de generar turnos nuevos. Los ${horario.turnosFuturos} que ya están generados no se tocan: si querés sacar alguno, cancelalo desde la agenda de turnos.`,
        () => {
          darDeBajaHorario(horario.idHorario)
            .then(() => {
              showSnack('Horario dado de baja', colors.statusOk);
              recargar();
            })
            .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
        },
      );
    },
    [confirmDialog, showSnack, recargar],
  );

  const regenerar = useCallback(() => {
    regenerarTurnos()
      .then((mensaje) => {
        showSnack(mensaje, colors.statusOk);
        recargar();
      })
      .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
  }, [showSnack, recargar]);

  return (
    <div>
      <Topbar
        title="Actividades"
        subtitle={
          datos
            ? `${datos.actividades.length} actividades · ${datos.horarios.filter((h) => h.activo).length} horarios semanales`
            : undefined
        }
      />

      <div className="space-y-4 p-8">
        {error && (
          <SectionCard>
            <p className="mb-4 font-body text-sm text-status-danger">{error}</p>
            <PrimaryButton label="Reintentar" onClick={recargar} />
          </SectionCard>
        )}

        {!error && !datos && (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-72" />
            ))}
          </div>
        )}

        {!error && datos && (
          <>
            <HorarioSemanal
              horarios={datos.horarios}
              puedeGestionar={puedeGestionarTurnos}
              onNuevo={() => setHorarioNuevo(true)}
              onBaja={pedirBajaHorario}
              onRegenerar={regenerar}
            />

            <AgendaTurnos recarga={intento} />

            <div className="flex items-center justify-between pt-2">
              <h2 className="font-heading text-lg font-semibold text-text-main">Catálogo</h2>
              <PrimaryButton
                label="Nueva actividad"
                icon={Plus}
                onClick={() => setActividadEnForm('nueva')}
              />
            </div>

            {datos.actividades.length === 0 ? (
              <SectionCard>
                <p className="font-body text-sm text-text-muted">
                  Todavía no hay actividades cargadas.
                </p>
              </SectionCard>
            ) : (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                {datos.actividades.map((actividad) => (
                  <ActividadAdminCard
                    key={actividad.idActividad}
                    actividad={actividad}
                    planes={datos.planesPorActividad.get(actividad.idActividad) ?? []}
                    profesoresAsignados={(datos.profesoresPorActividad.get(actividad.idActividad) ?? []).filter(
                      (p) => p.asignado,
                    )}
                    onEditarActividad={() => setActividadEnForm(actividad)}
                    onDarDeBajaActividad={() => pedirBajaActividad(actividad)}
                    onReactivarActividad={() => reactivarActividadClick(actividad)}
                    onNuevoPlan={() => setPlanEnForm({ idActividad: actividad.idActividad, plan: null })}
                    onEditarPlan={(plan) => setPlanEnForm({ idActividad: actividad.idActividad, plan })}
                    onDarDeBajaPlan={pedirBajaPlan}
                    onReactivarPlan={reactivarPlanClick}
                    onGestionarProfesores={() => setActividadParaProfesores(actividad)}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </div>

      {actividadEnForm && (
        <ActividadFormModal
          actividad={actividadEnForm === 'nueva' ? null : actividadEnForm}
          onClose={() => setActividadEnForm(null)}
          onGuardado={recargar}
        />
      )}

      {planEnForm && (
        <PlanFormModal
          idActividad={planEnForm.idActividad}
          plan={planEnForm.plan}
          onClose={() => setPlanEnForm(null)}
          onGuardado={recargar}
        />
      )}

      {horarioNuevo && datos && (
        <HorarioFormModal
          actividades={datos.actividades}
          profesoresPorActividad={datos.profesoresPorActividad}
          onClose={() => setHorarioNuevo(false)}
          onGuardado={recargar}
        />
      )}

      {actividadParaProfesores && (
        <ProfesorAsignacionModal
          actividad={actividadParaProfesores}
          onClose={() => setActividadParaProfesores(null)}
          onCambio={recargar}
        />
      )}
    </div>
  );
}
