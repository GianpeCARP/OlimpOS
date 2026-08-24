import { useCallback, useEffect, useMemo, useState } from 'react';
import { PrimaryButton, SectionCard, StatusBadge, Topbar } from '../../components/ui';
import { colors, EstadoInscripcionActividad } from '../../config';
import { mensajeDeError } from '../../services/api';
import type {
  ActividadListada,
  InscripcionListada,
  PlanActividadListado,
} from '../../services/actividadService';
// Del servicio del SOCIO, no del personal.
//
// Esta vista llamaba a /actividades/* mandando id_socio en el cuerpo, y esas
// rutas estan protegidas con permisos de mostrador: un socio recibia 403 en
// las cuatro llamadas, o sea que la seccion no funcionaba. Ahora usa
// /portal/mi-*, donde el id sale del token firmado.
import {
  cancelarMiAbono,
  comprarMiPlan,
  getCatalogoDelSocio,
  getMisAbonos,
} from '../../services/socioService';
import { useAuthStore } from '../../store/authStore';
import { useUiStore } from '../../store/uiStore';
import { formatearFecha, formatearMoneda } from '../../utils/format';
import { parsearFecha } from '../../utils/fechas';
import { ActividadCatalogoCard } from './ActividadCatalogoCard';
import { ComprarClaseSueltaModal } from './ComprarClaseSueltaModal';
import { SinSocioEnSesion } from './SinSocioEnSesion';

// Vista nueva del portal (especificacion_definitiva_actividades.md, Fase
// 4): planes de actividades con horario (yoga, boxeo, etc.) — DISTINTO de
// Mi Rutina (musculación). No depende de "Mis Turnos": comprar/cancelar un
// plan no necesita elegir turno; sólo "comprar clase suelta" sí, y ese
// selector vive acotado adentro de ComprarClaseSueltaModal (ver el
// comentario grande ahí de por qué no es la vista Mis Turnos).
//
// Las reglas de negocio (cobertura, upgrade, deudas) las aplica el service
// — acá sólo se muestra el mensaje que devuelve, tal cual, igual que en
// cualquier otra vista de la app. No se duplica esa lógica en el frontend.

interface DatosMisActividades {
  actividades: ActividadListada[];
  planesPorActividad: Map<number, PlanActividadListado[]>;
  misInscripciones: InscripcionListada[];
}

function Skeleton({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-md bg-surface-hover ${className}`} />;
}

function EtiquetaConsumo(insc: InscripcionListada): string {
  if (insc.tipoLimite === 'POR_MES') {
    return `${insc.clasesRestantes ?? 0} de ${insc.cantidad} clases este mes`;
  }
  return `Hasta ${insc.cantidad} veces por semana`;
}

export function MisActividadesView() {
  const idSocio = useAuthStore((s) => s.idSocio);
  const showSnack = useUiStore((s) => s.showSnack);
  const confirmDialog = useUiStore((s) => s.confirmDialog);

  const [datos, setDatos] = useState<DatosMisActividades | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intento, setIntento] = useState(0);
  const [claseSueltaDe, setClaseSueltaDe] = useState<ActividadListada | null>(null);

  useEffect(() => {
    if (idSocio === null) return;
    let cancelado = false;
    setDatos(null);
    setError(null);

    // El catalogo del socio trae los planes ANIDADOS, asi que se fue el
    // N+1: antes se pedia la lista de actividades y despues una consulta de
    // planes POR CADA UNA. Con cinco actividades eran seis pedidos para
    // dibujar una pantalla.
    Promise.all([getCatalogoDelSocio(), getMisAbonos()])
      .then(([catalogo, misInscripciones]) => {
        if (cancelado) return;
        const planesPorActividad = new Map<number, PlanActividadListado[]>();
        catalogo.forEach((a) => planesPorActividad.set(a.idActividad, a.planes));
        const actividades: ActividadListada[] = catalogo.map(({ planes: _planes, ...a }) => a);
        setDatos({ actividades, planesPorActividad, misInscripciones });
      })
      .catch((err: unknown) => {
        if (!cancelado) setError(mensajeDeError(err));
      });

    return () => {
      cancelado = true;
    };
  }, [idSocio, intento]);

  const recargar = useCallback(() => setIntento((n) => n + 1), []);

  const { activas, historial } = useMemo(() => {
    const todas = datos?.misInscripciones ?? [];
    return {
      activas: todas.filter((i) => i.estado === 'ACTIVA'),
      historial: todas.filter((i) => i.estado !== 'ACTIVA'),
    };
  }, [datos]);

  const pedirCompra = useCallback(
    (actividad: ActividadListada, plan: PlanActividadListado) => {
      if (idSocio === null) return;
      // REGLA 7: si ya hay un plan activo de esta misma actividad, comprar
      // otro lo reemplaza SIN devolución — el confirm tiene que decirlo
      // antes de cobrar, no después.
      const planViejo = activas.find((i) => i.idActividad === actividad.idActividad);
      confirmDialog(
        `¿Comprar "${plan.nombre}"?`,
        planViejo
          ? `Se cobran ${formatearMoneda(plan.precio)}. Tu plan actual (${planViejo.nombrePlan}) se cancela sin devolución al confirmar.`
          : `Se cobran ${formatearMoneda(plan.precio)} por este plan.`,
        () => {
          comprarMiPlan(plan.idPlanActividad, 'EFECTIVO')
            .then(() => {
              showSnack(`Listo, ya tenés "${plan.nombre}" activo`, colors.statusOk);
              recargar();
            })
            .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
        },
      );
    },
    [idSocio, activas, confirmDialog, showSnack, recargar],
  );

  const pedirCancelacion = useCallback(
    (insc: InscripcionListada) => {
      if (idSocio === null) return;
      confirmDialog(
        `¿Cancelar tu plan de ${insc.nombreActividad}?`,
        `Dejás de poder reservar turnos de ${insc.nombreActividad} con "${insc.nombrePlan}". Esta acción no se puede deshacer.`,
        () => {
          cancelarMiAbono(insc.idInscripcion)
            .then(() => {
              showSnack(`Cancelaste tu plan de ${insc.nombreActividad}`, colors.statusOk);
              recargar();
            })
            .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
        },
      );
    },
    [idSocio, confirmDialog, showSnack, recargar],
  );

  if (idSocio === null) {
    return <SinSocioEnSesion titulo="Mis actividades" />;
  }

  return (
    <div>
      <Topbar
        title="Mis actividades"
        subtitle={
          datos ? `${activas.length} plan${activas.length === 1 ? '' : 'es'} activo${activas.length === 1 ? '' : 's'}` : undefined
        }
      />

      <div className="space-y-4 p-4 md:p-8">
        {error && (
          <SectionCard>
            <p className="mb-4 font-body text-sm text-status-danger">{error}</p>
            <PrimaryButton label="Reintentar" onClick={recargar} />
          </SectionCard>
        )}

        {!error && !datos && (
          <div className="space-y-4">
            <Skeleton className="h-32" />
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-56" />
              ))}
            </div>
          </div>
        )}

        {!error && datos && (
          <>
            <SectionCard title="Tus planes activos">
              {activas.length === 0 ? (
                <p className="font-body text-sm text-text-muted">
                  Todavía no tenés ningún plan de actividad. Elegí uno del catálogo de abajo.
                </p>
              ) : (
                <div className="flex flex-col divide-y divide-border-idle">
                  {activas.map((insc) => (
                    <div
                      key={insc.idInscripcion}
                      className="flex flex-wrap items-center justify-between gap-3 py-3"
                    >
                      <div className="min-w-0">
                        <p className="font-body text-sm text-text-main">
                          {insc.nombreActividad} — {insc.nombrePlan}
                        </p>
                        <p className="font-body text-xs text-text-secondary">
                          {EtiquetaConsumo(insc)} · vence el{' '}
                          {formatearFecha(parsearFecha(insc.fechaVencimiento))}
                        </p>
                      </div>
                      <div className="flex items-center gap-3">
                        <StatusBadge status={EstadoInscripcionActividad[insc.estado]} />
                        <button
                          type="button"
                          onClick={() => pedirCancelacion(insc)}
                          className="font-body text-xs text-text-muted hover:text-status-danger"
                        >
                          Cancelar
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </SectionCard>

            <div>
              <h2 className="mb-3 font-heading text-lg font-semibold text-text-main">
                Catálogo de actividades
              </h2>
              {datos.actividades.length === 0 ? (
                <SectionCard>
                  <p className="font-body text-sm text-text-muted">
                    Todavía no hay actividades cargadas.
                  </p>
                </SectionCard>
              ) : (
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {datos.actividades.map((actividad) => (
                    <ActividadCatalogoCard
                      key={actividad.idActividad}
                      actividad={actividad}
                      planes={datos.planesPorActividad.get(actividad.idActividad) ?? []}
                      inscripcionActivaDeEstaActividad={activas.find(
                        (i) => i.idActividad === actividad.idActividad,
                      )}
                      onComprarPlan={(plan) => pedirCompra(actividad, plan)}
                      onComprarClaseSuelta={() => setClaseSueltaDe(actividad)}
                    />
                  ))}
                </div>
              )}
            </div>

            {historial.length > 0 && (
              <SectionCard title="Historial">
                <div className="flex flex-col divide-y divide-border-idle">
                  {historial.map((insc) => (
                    <div
                      key={insc.idInscripcion}
                      className="flex flex-wrap items-center justify-between gap-3 py-2.5"
                    >
                      <div className="min-w-0">
                        <p className="font-body text-sm text-text-secondary">
                          {insc.nombreActividad} — {insc.nombrePlan}
                        </p>
                        <p className="font-body text-xs text-text-muted">
                          {formatearFecha(parsearFecha(insc.fechaInicio))} al{' '}
                          {formatearFecha(parsearFecha(insc.fechaVencimiento))}
                        </p>
                      </div>
                      <StatusBadge status={insc.estado} />
                    </div>
                  ))}
                </div>
              </SectionCard>
            )}
          </>
        )}
      </div>

      {claseSueltaDe && (
        <ComprarClaseSueltaModal actividad={claseSueltaDe} onClose={() => setClaseSueltaDe(null)} />
      )}
    </div>
  );
}
