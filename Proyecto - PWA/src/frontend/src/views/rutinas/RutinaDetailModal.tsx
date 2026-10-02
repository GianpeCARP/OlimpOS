import { useEffect, useState } from 'react';
import { PlayCircle, X } from 'lucide-react';
import { PrimaryButton, StatusBadge } from '../../components/ui';
import { mensajeDeError } from '../../services/api';
import {
  obtenerRutina,
  type EjercicioDeRutina,
  type RutinaListado,
} from '../../services/rutinasService';
import { formatearFechaCorta } from '../../utils/format';
import { parsearFecha } from '../../utils/fechas';
import { VerTecnica } from '../socio/VerTecnica';
import { DetailRow } from './DetailRow';

// Detalle de una rutina con su planilla de ejercicios por día. Los ejercicios
// se piden al abrir: el listado no los trae.
//
// "Editar" y "Asignar" sólo si quien mira puede gestionar ESTA rutina: un
// Entrenador ve las de sus colegas, pero no las toca.
interface RutinaDetailModalProps {
  rutina: RutinaListado;
  puedeGestionar: boolean;
  onClose: () => void;
  onEditar: () => void;
  onAsignar: () => void;
}

function resumen(e: EjercicioDeRutina): string {
  const partes: string[] = [];
  if (e.series !== undefined && e.repeticiones) partes.push(`${e.series} × ${e.repeticiones}`);
  else if (e.series !== undefined) partes.push(`${e.series} series`);
  else if (e.repeticiones) partes.push(e.repeticiones);
  if (e.pesoSugerido !== undefined) partes.push(`${e.pesoSugerido} kg`);
  if (e.descansoSegundos !== undefined) partes.push(`${e.descansoSegundos}s desc.`);
  return partes.join(' · ');
}

export function RutinaDetailModal({
  rutina,
  puedeGestionar,
  onClose,
  onEditar,
  onAsignar,
}: RutinaDetailModalProps) {
  const [ejercicios, setEjercicios] = useState<EjercicioDeRutina[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [viendo, setViendo] = useState<EjercicioDeRutina | null>(null);

  const idRutina = rutina.idRutina;
  useEffect(() => {
    let cancelado = false;
    obtenerRutina(idRutina)
      .then((r) => {
        if (!cancelado) setEjercicios(r.ejercicios);
      })
      .catch((err: unknown) => {
        if (!cancelado) setError(mensajeDeError(err));
      });
    return () => {
      cancelado = true;
    };
  }, [idRutina]);

  const dias = ejercicios ? [...new Set(ejercicios.map((e) => e.dia))].sort((a, b) => a - b) : [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      {viendo?.video && (
        <VerTecnica nombre={viendo.nombre} video={viendo.video} onCerrar={() => setViendo(null)} />
      )}
      <div className="flex max-h-[90vh] w-full max-w-lg flex-col rounded-lg border border-border-idle bg-surface-card">
        <div className="flex items-start justify-between gap-3 border-b border-border-idle p-5">
          <div className="min-w-0">
            <h2 className="font-heading text-lg font-semibold break-words text-text-main">
              {rutina.nombre}
            </h2>
            <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
              <StatusBadge status={rutina.estado} />
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar"
            className="shrink-0 rounded-md p-1.5 text-text-muted hover:bg-surface-hover hover:text-text-main"
          >
            <X size={18} />
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain p-5">
          <div className="flex flex-col divide-y divide-border-idle">
            <DetailRow
              label="Frecuencia"
              value={rutina.diasPorSemana !== undefined ? `${rutina.diasPorSemana} días/sem` : '—'}
            />
            <DetailRow label="Entrenador" value={rutina.entrenador} />
            <DetailRow label="Asignados" value={`${rutina.asignados} socios`} />
            <DetailRow label="Creada" value={formatearFechaCorta(parsearFecha(rutina.fechaCreacion))} />
            <DetailRow label="Objetivo" value={rutina.objetivo ?? 'Sin especificar'} />
          </div>

          <div className="mt-5 space-y-4">
            {error && <p className="font-body text-sm text-status-danger">{error}</p>}
            {!error && !ejercicios && (
              <p className="font-body text-sm text-text-muted">Cargando ejercicios…</p>
            )}
            {ejercicios && ejercicios.length === 0 && (
              <p className="font-body text-sm text-text-muted">Esta rutina todavía no tiene ejercicios.</p>
            )}
            {dias.map((d) => (
              <div key={d}>
                <p className="mb-2 font-body text-xs font-semibold tracking-wide text-text-muted uppercase">
                  Día {d}
                </p>
                <ul className="flex flex-col divide-y divide-border-idle">
                  {ejercicios
                    ?.filter((e) => e.dia === d)
                    .map((e) => (
                      <li key={e.idRutinaEjercicio} className="flex items-start justify-between gap-3 py-2">
                        <div className="min-w-0">
                          <p className="font-body text-sm text-text-main">{e.nombre}</p>
                          <p className="font-body text-xs text-text-muted">
                            {e.grupoMuscular}
                            {resumen(e) && ` · ${resumen(e)}`}
                          </p>
                          {e.observaciones && (
                            <p className="font-body text-xs text-status-warn">{e.observaciones}</p>
                          )}
                        </div>
                        {e.video && (
                          <button
                            type="button"
                            onClick={() => setViendo(e)}
                            title="Ver técnica"
                            className="shrink-0 rounded-md p-1.5 text-primary-volt hover:bg-surface-hover"
                          >
                            <PlayCircle size={18} />
                          </button>
                        )}
                      </li>
                    ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="flex shrink-0 flex-wrap justify-end gap-3 border-t border-border-idle p-5">
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 rounded-md px-4 py-2 font-body text-sm whitespace-nowrap text-text-secondary hover:text-text-main"
          >
            Cerrar
          </button>
          {puedeGestionar && (
            <>
              {/* "Asignar" sólo con la rutina ACTIVA: una dada de baja deja de
                  ofrecerse para asignar y el backend contesta 409. "Editar" sí,
                  porque una rutina de baja se puede corregir antes de
                  reactivarla. */}
              {rutina.activo && (
                <button
                  type="button"
                  onClick={onAsignar}
                  className="shrink-0 rounded-md border border-border-idle px-4 py-2 font-body text-sm whitespace-nowrap text-text-secondary hover:bg-surface-hover hover:text-text-main"
                >
                  Asignar
                </button>
              )}
              <PrimaryButton label="Editar" onClick={onEditar} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
