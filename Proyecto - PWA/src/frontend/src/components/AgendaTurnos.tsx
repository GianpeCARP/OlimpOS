import { useCallback, useEffect, useState } from 'react';
import { Ban, CalendarClock, ChevronDown, ChevronRight, CircleAlert, GraduationCap, Users2 } from 'lucide-react';
import { SectionCard } from './ui';
import { colors } from '../config';
import { usePuedeAccion } from '../hooks/usePermisos';
import { mensajeDeError } from '../services/api';
import type { MiClase } from '../services/profesorService';
import {
  cancelarTurno,
  getAgenda,
  getDetalleTurno,
  type TurnoAgenda,
} from '../services/turnosService';
import { useUiStore } from '../store/uiStore';
import {
  ESTADO_INSCRIPTO_COLOR,
  ESTADO_INSCRIPTO_LABEL,
  fechaCortaConDia,
} from '../utils/estadoInscripto';

// Los próximos turnos con quién se anotó, para el PERSONAL.
//
// Faltaba en toda la PWA: el socio veía sus turnos y el profesor los suyos,
// pero ni el Dueño ni el Recepcionista tenían dónde ver "mañana a las 19 hay
// Yoga con 8 anotados, y son estos". Se usa en dos lugares: en Actividades
// (la agenda completa de la semana) y en el Dashboard (`compacto`: sólo lo que
// está por pasar, arriba de todo, que es lo primero que mira el mostrador).
//
// La lista de anotados se pide al EXPANDIR un turno y no con la agenda: una
// semana puede tener decenas de turnos, y bajar todas sus reservas para mirar
// una sola sería pagar decenas de consultas por nada.

/** En el dashboard: cuántos turnos mostrar como máximo. */
const MAX_COMPACTO = 6;
/** Un turno sigue apareciendo hasta esta cantidad de minutos después de empezar (clase en curso). */
const MINUTOS_EN_CURSO = 60;

interface AgendaTurnosProps {
  /** Días hacia adelante (incluye hoy). */
  dias?: number;
  /** Versión corta para el dashboard: sólo lo próximo, sin cancelados. */
  compacto?: boolean;
  /** Cambiar este número recarga la agenda (por ejemplo, después de crear un horario). */
  recarga?: number;
}

function inicioDe(t: TurnoAgenda): Date {
  const [anio, mes, dia] = t.fecha.split('-').map(Number);
  const [h, m] = t.hora.split(':').map(Number);
  return new Date(anio, mes - 1, dia, h, m);
}

export function AgendaTurnos({ dias = 7, compacto = false, recarga = 0 }: AgendaTurnosProps) {
  const puedeCancelar = usePuedeAccion('gestionTurnos');
  const showSnack = useUiStore((s) => s.showSnack);
  const confirmDialog = useUiStore((s) => s.confirmDialog);

  const [turnos, setTurnos] = useState<TurnoAgenda[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intento, setIntento] = useState(0);
  const [abierto, setAbierto] = useState<number | null>(null);
  const [detalle, setDetalle] = useState<MiClase | null>(null);

  useEffect(() => {
    let cancelado = false;
    setError(null);
    getAgenda(dias)
      .then((lista) => {
        if (!cancelado) setTurnos(lista);
      })
      .catch((err: unknown) => {
        if (!cancelado) setError(mensajeDeError(err));
      });
    return () => {
      cancelado = true;
    };
  }, [dias, intento, recarga]);

  const alternar = useCallback(
    (idTurno: number) => {
      if (abierto === idTurno) {
        setAbierto(null);
        return;
      }
      setAbierto(idTurno);
      setDetalle(null);
      getDetalleTurno(idTurno)
        .then(setDetalle)
        .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
    },
    [abierto, showSnack],
  );

  const pedirCancelacion = useCallback(
    (t: TurnoAgenda) => {
      confirmDialog(
        `¿Cancelar ${t.actividad} del ${fechaCortaConDia(t.fecha)} a las ${t.hora}?`,
        t.reservados > 0
          ? `Hay ${t.reservados} anotado(s). Se les cancela la reserva y la clase se les devuelve.`
          : 'No hay nadie anotado.',
        () => {
          cancelarTurno(t.idTurno, 'Cancelada por el gimnasio')
            .then(() => {
              showSnack('Turno cancelado', colors.statusOk);
              setAbierto(null);
              setIntento((n) => n + 1);
            })
            .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
        },
      );
    },
    [confirmDialog, showSnack],
  );

  const ahora = Date.now();
  const visibles = (turnos ?? []).filter((t) => {
    if (!compacto) return true;
    return !t.cancelado && inicioDe(t).getTime() >= ahora - MINUTOS_EN_CURSO * 60_000;
  });
  const mostrados = compacto ? visibles.slice(0, MAX_COMPACTO) : visibles;

  // Agrupados por fecha, respetando el orden que ya trae el backend.
  const porDia = new Map<string, TurnoAgenda[]>();
  mostrados.forEach((t) => porDia.set(t.fecha, [...(porDia.get(t.fecha) ?? []), t]));

  return (
    <SectionCard title={compacto ? 'Próximos turnos' : `Turnos de los próximos ${dias} días`}>
      {error && <p className="font-body text-sm text-status-danger">{error}</p>}

      {!error && !turnos && <div className="h-24 animate-pulse rounded-md bg-surface-hover" />}

      {!error && turnos && mostrados.length === 0 && (
        <div className="flex flex-col items-center gap-1 py-6 text-center">
          <CalendarClock size={24} className="text-text-muted" />
          <p className="font-body text-sm text-text-muted">No hay turnos por delante.</p>
          <p className="font-body text-xs text-text-muted">
            Los turnos salen del horario semanal de cada actividad (sección Actividades).
          </p>
        </div>
      )}

      {!error &&
        Array.from(porDia.entries()).map(([fecha, delDia]) => (
          <div key={fecha} className="mb-3 last:mb-0">
            <p className="mb-1 font-body text-[10px] font-semibold tracking-wide text-text-muted uppercase">
              {fechaCortaConDia(fecha)}
            </p>
            <div className="flex flex-col divide-y divide-border-idle rounded-md border border-border-idle">
              {delDia.map((t) => (
                <div key={t.idTurno}>
                  <div className="flex items-center gap-2 px-3 py-2">
                    <button
                      type="button"
                      onClick={() => alternar(t.idTurno)}
                      className="flex min-w-0 flex-1 items-center gap-3 text-left"
                    >
                      {abierto === t.idTurno ? (
                        <ChevronDown size={14} className="shrink-0 text-text-muted" />
                      ) : (
                        <ChevronRight size={14} className="shrink-0 text-text-muted" />
                      )}
                      <span className="w-12 shrink-0 font-mono text-sm font-semibold text-primary-volt">
                        {t.hora}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span
                          className={`block truncate font-body text-sm ${t.cancelado ? 'text-text-muted line-through' : 'text-text-main'}`}
                        >
                          {t.actividad}
                        </span>
                        <span className="flex items-center gap-1 truncate font-body text-xs text-text-muted">
                          <GraduationCap size={11} className="shrink-0" />
                          {t.cancelado ? (t.motivoCancelacion ?? 'Cancelado') : (t.profesor ?? 'Sin profesor')}
                        </span>
                      </span>
                      <span className="inline-flex shrink-0 items-center gap-1 font-body text-xs whitespace-nowrap text-text-secondary">
                        <Users2 size={12} />
                        {t.reservados}/{t.cupoMaximo}
                      </span>
                    </button>
                    {puedeCancelar && !t.cancelado && !compacto && (
                      <button
                        type="button"
                        onClick={() => pedirCancelacion(t)}
                        title="Cancelar este turno"
                        className="shrink-0 rounded p-1 text-text-muted hover:text-status-danger"
                      >
                        <Ban size={14} />
                      </button>
                    )}
                  </div>

                  {abierto === t.idTurno && (
                    <div className="border-t border-border-idle bg-surface-base/40 px-3 py-2 pl-10">
                      {!detalle ? (
                        <p className="font-body text-xs text-text-muted">Cargando anotados…</p>
                      ) : detalle.inscriptos.length === 0 ? (
                        <p className="font-body text-xs text-text-muted">Todavía no se anotó nadie.</p>
                      ) : (
                        detalle.inscriptos.map((i) => (
                          <div key={i.idReserva} className="flex items-center justify-between gap-3 py-1">
                            <div className="min-w-0">
                              <p className="truncate font-body text-sm text-text-main">
                                {i.nombre}
                                {i.esClaseSuelta && (
                                  <span className="ml-2 font-body text-[10px] text-text-muted">clase suelta</span>
                                )}
                              </p>
                              {i.alerta && (
                                <p className="flex items-center gap-1 font-body text-xs text-status-warn">
                                  <CircleAlert size={11} className="shrink-0" />
                                  {i.alerta}
                                </p>
                              )}
                            </div>
                            <span
                              className={`shrink-0 font-body text-xs whitespace-nowrap ${ESTADO_INSCRIPTO_COLOR[i.estado]}`}
                            >
                              {ESTADO_INSCRIPTO_LABEL[i.estado]}
                            </span>
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
    </SectionCard>
  );
}
