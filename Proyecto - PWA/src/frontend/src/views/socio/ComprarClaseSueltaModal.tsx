import { useEffect, useState } from 'react';
import { CalendarX2, Users } from 'lucide-react';
import { PrimaryButton } from '../../components/ui';
import { colors } from '../../config';
import { mensajeDeError } from '../../services/api';
import type { ActividadListada } from '../../services/actividadService';
// Del portal del socio: los endpoints del personal devolvian 403 acá.
import {
  comprarMiClaseSuelta,
  getTurnosDelSocio,
  type TurnoDelSocio,
} from '../../services/socioService';
import { useAuthStore } from '../../store/authStore';
import { useUiStore } from '../../store/uiStore';
import { formatearFecha, formatearMoneda } from '../../utils/format';
import { parsearFecha } from '../../utils/fechas';

// Selector de turno para "comprar clase suelta" (REGLA 5). NO es la vista
// "Mis Turnos" — esa sigue sin construirse (ver project-olimpos-modelo-
// turnos en memoria: el array turnos está congelado hasta resolver el
// modelo mixto). Esto es un recorte mínimo, acotado a esta única compra:
// lee getTurnosDisponibles (ya construido en Fase 3), no administra
// reservas ni permite cancelarlas, no tiene filtros de fecha ni calendario.
//
// Como `turnos` hoy sólo tiene filas de Musculación (congelado), elegir acá
// una actividad sin turnos reales (Yoga, Boxeo) muestra el estado vacío
// real en vez de inventar horarios — no es un bug, es el dato tal cual está.
interface ComprarClaseSueltaModalProps {
  actividad: ActividadListada;
  onClose: () => void;
}

function Skeleton({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-md bg-surface-hover ${className}`} />;
}

export function ComprarClaseSueltaModal({ actividad, onClose }: ComprarClaseSueltaModalProps) {
  // Ni idSocio ni el id del usuario: el backend los saca del token firmado.
  // Mandarlos desde acá era el vector que cerró la auditoría del 2026-08-03.
  const idSocio = useAuthStore((s) => s.idSocio);
  const showSnack = useUiStore((s) => s.showSnack);

  const [turnos, setTurnos] = useState<TurnoDelSocio[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [comprando, setComprando] = useState<number | null>(null);

  useEffect(() => {
    let cancelado = false;
    getTurnosDelSocio()
      .then((lista) => {
        // Se filtra acá y no en el backend porque /mis-turnos/disponibles
        // devuelve TODA la grilla: es el mismo pedido que usa la pantalla de
        // turnos, y pedirlo dos veces con filtros distintos sería una consulta
        // de más para mostrar un subconjunto de lo que ya se tiene.
        const deEsta = lista.filter((t) => t.nombreActividad === actividad.nombre);
        if (!cancelado) setTurnos(deEsta);
      })
      .catch((err: unknown) => {
        if (!cancelado) setError(mensajeDeError(err));
      });
    return () => {
      cancelado = true;
    };
  }, [actividad.idActividad, actividad.nombre]);

  const comprar = async (idTurno: number) => {
    if (idSocio === null) return;
    setComprando(idTurno);
    try {
      const { mensaje } = await comprarMiClaseSuelta(idTurno, 'EFECTIVO');
      // El mensaje lo redacta el backend y ya viene en segunda persona
      // ("Compraste una clase suelta de Yoga por $6.000"). Rearmarlo acá
      // significaria dos textos para lo mismo, y el del servidor es el unico
      // que sabe cuanto se cobro realmente.
      showSnack(mensaje, colors.statusOk);
      onClose();
    } catch (err) {
      showSnack(mensajeDeError(err), colors.statusDanger);
    } finally {
      setComprando(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-md rounded-lg border border-border-idle bg-surface-card p-6">
        <h2 className="font-heading text-lg font-semibold text-text-main">
          Clase suelta de {actividad.nombre}
        </h2>
        <p className="mt-1 font-body text-sm text-text-secondary">
          {formatearMoneda(actividad.precioClaseSuelta)} por clase, sin necesitar ningún plan.
        </p>

        <div className="mt-4 flex flex-col gap-2">
          {error && <p className="font-body text-sm text-status-danger">{error}</p>}

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
                    label={comprando === turno.idTurno ? 'Comprando…' : 'Comprar'}
                    onClick={() => comprar(turno.idTurno)}
                    disabled={sinCupo || comprando !== null}
                  />
                </div>
              );
            })}
        </div>

        <div className="mt-6 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 rounded-md px-4 py-2 font-body text-sm whitespace-nowrap text-text-secondary hover:text-text-main"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}
