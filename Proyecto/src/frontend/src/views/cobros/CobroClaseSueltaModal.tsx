import { useEffect, useState } from 'react';
import { CalendarX2, Users } from 'lucide-react';
import { PrimaryButton } from '../../components/ui';
import { mensajeDeError } from '../../services/api';
import { obtenerSedePorDefecto } from '../../services/authService';
import {
  comprarClaseSuelta,
  getTurnosDisponibles,
  type ActividadListada,
  type TurnoDisponible,
} from '../../services/actividadService';
import type { Pago } from '../../types';
import { formatearFecha, formatearMoneda } from '../../utils/format';
import { parsearFecha } from '../../utils/fechas';

// Versión de recepción de socio/ComprarClaseSueltaModal.tsx: mismo selector
// de turno (getTurnosDisponibles, ya construido en Fase 3), pero el socio y
// quién cobra vienen por props en vez de leerse de useAuthStore — acá quien
// está logueado es recepción, cobrando a nombre de otra persona.
interface CobroClaseSueltaModalProps {
  idSocio: number;
  nombreSocio: string;
  actividad: ActividadListada;
  metodo: Pago['metodo'];
  idUsuarioActor?: number;
  onClose: () => void;
  onCobrado: () => void;
}

function Skeleton({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-md bg-surface-hover ${className}`} />;
}

export function CobroClaseSueltaModal({
  idSocio,
  nombreSocio,
  actividad,
  metodo,
  idUsuarioActor,
  onClose,
  onCobrado,
}: CobroClaseSueltaModalProps) {
  const [turnos, setTurnos] = useState<TurnoDisponible[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cobrando, setCobrando] = useState<number | null>(null);
  const [snackError, setSnackError] = useState<string | null>(null);

  useEffect(() => {
    let cancelado = false;
    obtenerSedePorDefecto()
      .then((sede) => getTurnosDisponibles(sede.id_sede, actividad.idActividad))
      .then((lista) => {
        if (!cancelado) setTurnos(lista);
      })
      .catch((err: unknown) => {
        if (!cancelado) setError(mensajeDeError(err));
      });
    return () => {
      cancelado = true;
    };
  }, [actividad.idActividad]);

  const cobrar = async (idTurno: number) => {
    setCobrando(idTurno);
    setSnackError(null);
    try {
      await comprarClaseSuelta(idSocio, idTurno, idUsuarioActor, metodo);
      onCobrado();
      onClose();
    } catch (err) {
      setSnackError(mensajeDeError(err));
    } finally {
      setCobrando(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-md rounded-lg border border-border-idle bg-surface-card p-6">
        <h2 className="font-heading text-lg font-semibold text-text-main">
          Clase suelta de {actividad.nombre}
        </h2>
        <p className="mt-1 font-body text-sm text-text-secondary">
          {formatearMoneda(actividad.precioClaseSuelta)} para {nombreSocio}, sin necesitar ningún plan.
        </p>

        <div className="mt-4 flex flex-col gap-2">
          {(error ?? snackError) && (
            <p className="font-body text-sm text-status-danger">{error ?? snackError}</p>
          )}

          {!error && !turnos && (
            <div className="space-y-2">
              <Skeleton className="h-14" />
              <Skeleton className="h-14" />
            </div>
          )}

          {!error && turnos && turnos.length === 0 && (
            <div className="flex flex-col items-center gap-2 py-6 text-center">
              <CalendarX2 size={28} className="text-text-muted" />
              <p className="font-body text-sm text-text-muted">
                No hay turnos disponibles de {actividad.nombre} por ahora.
              </p>
            </div>
          )}

          {!error &&
            turnos &&
            turnos.map((turno) => {
              const sinCupo = turno.cupoDisponible <= 0;
              return (
                <div
                  key={turno.idTurno}
                  className="flex items-center justify-between gap-3 rounded-md border border-border-idle px-3 py-2.5"
                >
                  <div className="min-w-0">
                    <p className="font-body text-sm text-text-main">
                      {formatearFecha(parsearFecha(turno.fecha))} · {turno.hora}
                    </p>
                    <div className="mt-0.5 flex items-center gap-3 font-body text-xs text-text-muted">
                      <span className="flex items-center gap-1">
                        <Users size={12} />
                        {sinCupo ? 'Sin cupo' : `${turno.cupoDisponible} lugares`}
                      </span>
                      {turno.nombreProfesional && <span>{turno.nombreProfesional}</span>}
                    </div>
                  </div>
                  <PrimaryButton
                    label={cobrando === turno.idTurno ? 'Cobrando…' : 'Cobrar'}
                    onClick={() => cobrar(turno.idTurno)}
                    disabled={sinCupo || cobrando !== null}
                  />
                </div>
              );
            })}
        </div>

        <div className="mt-6 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md px-4 py-2 font-body text-sm text-text-secondary hover:text-text-main"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}
