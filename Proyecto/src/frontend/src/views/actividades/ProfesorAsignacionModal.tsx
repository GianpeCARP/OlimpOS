import { useEffect, useState } from 'react';
import { GraduationCap } from 'lucide-react';
import { colors } from '../../config';
import { mensajeDeError } from '../../services/api';
import {
  asignarProfesorAActividad,
  desasignarProfesorDeActividad,
  getProfesoresDeActividad,
  type ActividadAdmin,
  type ProfesorAsignable,
} from '../../services/actividadService';
import { useAuthStore } from '../../store/authStore';
import { useUiStore } from '../../store/uiStore';

// Relación profesor↔actividad (especificacion_definitiva_actividades.md,
// Fase 4: "Asignar profesores"). Cada fila se guarda al toque, no hay un
// "Guardar" al pie — mismo criterio que un panel de permisos: es una lista
// de toggles, no un formulario con estado intermedio que pueda perderse.
interface ProfesorAsignacionModalProps {
  actividad: ActividadAdmin;
  onClose: () => void;
  /** Avisa al cerrar si hubo al menos un cambio, para que el padre recargue. */
  onCambio: () => void;
}

function Skeleton({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-md bg-surface-hover ${className}`} />;
}

export function ProfesorAsignacionModal({ actividad, onClose, onCambio }: ProfesorAsignacionModalProps) {
  const idUsuarioActor = useAuthStore((s) => s.usuario?.id_usuario);
  const showSnack = useUiStore((s) => s.showSnack);

  const [profesores, setProfesores] = useState<ProfesorAsignable[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cambiando, setCambiando] = useState<number | null>(null);
  const [huboCambios, setHuboCambios] = useState(false);

  useEffect(() => {
    let cancelado = false;
    getProfesoresDeActividad(actividad.idActividad)
      .then((lista) => {
        if (!cancelado) setProfesores(lista);
      })
      .catch((err: unknown) => {
        if (!cancelado) setError(mensajeDeError(err));
      });
    return () => {
      cancelado = true;
    };
  }, [actividad.idActividad]);

  const alternar = (profesor: ProfesorAsignable) => {
    setCambiando(profesor.idProfesor);
    const accion = profesor.asignado
      ? desasignarProfesorDeActividad(profesor.idProfesor, actividad.idActividad, idUsuarioActor)
      : asignarProfesorAActividad(profesor.idProfesor, actividad.idActividad, idUsuarioActor);

    accion
      .then(() => {
        setProfesores((prev) =>
          (prev ?? []).map((p) =>
            p.idProfesor === profesor.idProfesor ? { ...p, asignado: !p.asignado } : p,
          ),
        );
        setHuboCambios(true);
      })
      .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger))
      .finally(() => setCambiando(null));
  };

  const cerrar = () => {
    if (huboCambios) onCambio();
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-md rounded-lg border border-border-idle bg-surface-card p-6">
        <h2 className="font-heading text-lg font-semibold text-text-main">
          Profesores de {actividad.nombre}
        </h2>
        <p className="mt-1 font-body text-sm text-text-secondary">
          Tocá un profesor para asignarlo o quitarlo de esta actividad.
        </p>

        <div className="mt-4 flex flex-col gap-2">
          {error && <p className="font-body text-sm text-status-danger">{error}</p>}

          {!error && !profesores && (
            <div className="space-y-2">
              <Skeleton className="h-12" />
              <Skeleton className="h-12" />
            </div>
          )}

          {!error && profesores && profesores.length === 0 && (
            <p className="py-4 text-center font-body text-sm text-text-muted">
              Todavía no hay profesores activos para asignar. Dalos de alta en Personal.
            </p>
          )}

          {!error &&
            profesores &&
            profesores.map((profesor) => (
              <button
                key={profesor.idProfesor}
                type="button"
                onClick={() => alternar(profesor)}
                disabled={cambiando !== null}
                className={`flex items-center justify-between gap-3 rounded-md border px-3 py-2.5 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${
                  profesor.asignado
                    ? 'border-primary-volt bg-primary-volt/10'
                    : 'border-border-idle hover:bg-surface-hover'
                }`}
              >
                <div className="flex items-center gap-2 min-w-0">
                  <GraduationCap
                    size={16}
                    className={`shrink-0 ${profesor.asignado ? 'text-primary-volt' : 'text-text-muted'}`}
                  />
                  <div className="min-w-0">
                    <p className="truncate font-body text-sm text-text-main">{profesor.nombre}</p>
                    {profesor.especialidad && (
                      <p className="truncate font-body text-xs text-text-muted">{profesor.especialidad}</p>
                    )}
                  </div>
                </div>
                <span
                  className={`shrink-0 font-body text-xs font-medium ${
                    profesor.asignado ? 'text-primary-volt' : 'text-text-muted'
                  }`}
                >
                  {cambiando === profesor.idProfesor
                    ? '…'
                    : profesor.asignado
                      ? 'Asignado'
                      : 'Asignar'}
                </span>
              </button>
            ))}
        </div>

        <div className="mt-6 flex justify-end">
          <button
            type="button"
            onClick={cerrar}
            className="rounded-md px-4 py-2 font-body text-sm text-text-secondary hover:text-text-main"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}
