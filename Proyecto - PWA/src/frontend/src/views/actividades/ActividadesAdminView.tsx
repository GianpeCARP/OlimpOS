import { useCallback, useEffect, useState } from 'react';
import { Plus } from 'lucide-react';
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
import { useAuthStore } from '../../store/authStore';
import { useUiStore } from '../../store/uiStore';
import { ActividadAdminCard } from './ActividadAdminCard';
import { ActividadFormModal } from './ActividadFormModal';
import { PlanFormModal } from './PlanFormModal';
import { ProfesorAsignacionModal } from './ProfesorAsignacionModal';

// ABM del catálogo de actividades (especificacion_definitiva_actividades.md,
// Fase 4, sección Dueño). Exclusiva del Dueño — ver el comentario en
// config.ts sobre por qué esta sección, a diferencia de Asistencia, no es
// operativa del día a día sino configuración de negocio (precios, cupos).
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
}

function Skeleton({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-md bg-surface-hover ${className}`} />;
}

export function ActividadesAdminView() {
  const idUsuarioActor = useAuthStore((s) => s.usuario?.id_usuario);
  const showSnack = useUiStore((s) => s.showSnack);
  const confirmDialog = useUiStore((s) => s.confirmDialog);

  const [datos, setDatos] = useState<DatosAdmin | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intento, setIntento] = useState(0);

  const [actividadEnForm, setActividadEnForm] = useState<ActividadAdmin | 'nueva' | null>(null);
  const [planEnForm, setPlanEnForm] = useState<{
    idActividad: number;
    plan: PlanActividadAdmin | null;
  } | null>(null);
  const [actividadParaProfesores, setActividadParaProfesores] = useState<ActividadAdmin | null>(null);

  useEffect(() => {
    setDatos(null);
    setError(null);

    getActividadesAdmin()
      .then(async (actividades) => {
        const [listasDePlanes, listasDeProfesores] = await Promise.all([
          Promise.all(actividades.map((a) => getPlanesDeActividadAdmin(a.idActividad))),
          Promise.all(actividades.map((a) => getProfesoresDeActividad(a.idActividad))),
        ]);
        const planesPorActividad = new Map<number, PlanActividadAdmin[]>();
        const profesoresPorActividad = new Map<number, ProfesorAsignable[]>();
        actividades.forEach((a, i) => {
          planesPorActividad.set(a.idActividad, listasDePlanes[i]);
          profesoresPorActividad.set(a.idActividad, listasDeProfesores[i]);
        });
        setDatos({ actividades, planesPorActividad, profesoresPorActividad });
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

  return (
    <div>
      <Topbar
        title="Actividades"
        subtitle={datos ? `${datos.actividades.length} actividades en el catálogo` : undefined}
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
            <div className="flex justify-end">
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
