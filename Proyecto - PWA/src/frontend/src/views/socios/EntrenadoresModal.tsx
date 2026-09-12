import { useEffect, useMemo, useState } from 'react';
import { Dumbbell, Plus, X } from 'lucide-react';
import { PrimaryButton, SelectField, type SelectOption } from '../../components/ui';
import { colors } from '../../config';
import { mensajeDeError } from '../../services/api';
import { listarEntrenadoresActivos, type EntrenadorOpcion } from '../../services/rutinasService';
import {
  asignarEntrenador,
  finalizarAsignacionEntrenador,
  listarEntrenadoresDeSocio,
  type AsignacionEntrenador,
  type SocioListado,
} from '../../services/sociosService';
import { useUiStore } from '../../store/uiStore';
import { formatearFecha } from '../../utils/format';
import { parsearFecha } from '../../utils/fechas';

// Gemelo de `_entrenadores` de `app/views/socios.py` en Flet.
//
// Es una LISTA con un selector abajo y no un simple desplegable, y eso no es
// una decisión de diseño: un socio puede tener a la vez uno de musculación y
// otro de funcional, y el backend lo permite explícitamente. Un desplegable
// diría "elegí SU entrenador", que es exactamente la idea equivocada que tenía
// la columna vieja.
//
// Las FINALIZADAS se muestran, en gris. Ese historial es el motivo por el que
// esto es una tabla: con la columna, reasignar borraba al anterior.
//
// Diferencia con PatologiasModal: acá el modal se abre para TODOS los que ven
// la grilla, y lo que se esconde son los controles de escritura. Quién entrena
// a quién no es un dato sensible —el historial médico sí—, así que ocultarlo
// entero al Entrenador (que tiene Socios en LECTURA) sería esconderle
// justamente lo suyo.

interface EntrenadoresModalProps {
  socio: SocioListado;
  /** Acción `gestionRutinas`. False = el modal es de sólo consulta. */
  puedeGestionar: boolean;
  onClose: () => void;
}

export function EntrenadoresModal({ socio, puedeGestionar, onClose }: EntrenadoresModalProps) {
  const showSnack = useUiStore((s) => s.showSnack);

  const [asignaciones, setAsignaciones] = useState<AsignacionEntrenador[] | null>(null);
  const [disponibles, setDisponibles] = useState<EntrenadorOpcion[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intento, setIntento] = useState(0);

  const [seleccion, setSeleccion] = useState('');
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    let cancelado = false;
    setError(null);
    // El listado de entrenadores sólo se pide si hay algo que hacer con él:
    // /personal/entrenadores exige la sección RUTINAS, y quien abre esto de
    // sólo lectura puede no tenerla. Pedirlo igual daría un 403 que tumbaría
    // el Promise.all y dejaría la pantalla en error sin motivo.
    const pedidos = puedeGestionar
      ? Promise.all([listarEntrenadoresDeSocio(socio.idSocio), listarEntrenadoresActivos()])
      : listarEntrenadoresDeSocio(socio.idSocio).then(
          (lista): [AsignacionEntrenador[], EntrenadorOpcion[]] => [lista, []],
        );

    pedidos
      .then(([propios, todos]) => {
        if (cancelado) return;
        setAsignaciones(propios);
        setDisponibles(todos);
      })
      .catch((err: unknown) => {
        if (!cancelado) setError(mensajeDeError(err));
      });
    return () => {
      cancelado = true;
    };
  }, [socio.idSocio, intento, puedeGestionar]);

  const recargar = () => setIntento((n) => n + 1);

  // Los que ya están a cargo no se vuelven a ofrecer: el backend responde 409
  // y hacerle elegir algo que va a fallar es hacerle perder el tiempo.
  const elegibles = useMemo(() => {
    if (!disponibles || !asignaciones) return [];
    const activos = new Set(asignaciones.filter((a) => a.activa).map((a) => a.idEntrenador));
    return disponibles.filter((e) => !activos.has(e.idEntrenador));
  }, [disponibles, asignaciones]);

  const opciones: SelectOption[] = elegibles.map((e) => ({
    value: String(e.idEntrenador),
    label: e.nombre,
  }));

  const asignar = async () => {
    if (seleccion === '') {
      showSnack('Elegí un entrenador de la lista.', colors.statusDanger);
      return;
    }
    setGuardando(true);
    try {
      await asignarEntrenador(socio.idSocio, Number(seleccion));
      showSnack('Entrenador asignado.', colors.statusOk);
      setSeleccion('');
      recargar();
    } catch (err) {
      showSnack(mensajeDeError(err), colors.statusDanger);
    } finally {
      setGuardando(false);
    }
  };

  const finalizar = async (asignacion: AsignacionEntrenador) => {
    setGuardando(true);
    try {
      await finalizarAsignacionEntrenador(asignacion.idAsignacion);
      showSnack('Listo. La asignación queda en el historial, no se borra.', colors.statusOk);
      recargar();
    } catch (err) {
      showSnack(mensajeDeError(err), colors.statusDanger);
    } finally {
      setGuardando(false);
    }
  };

  const cargando = asignaciones === null || disponibles === null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="flex max-h-[85vh] w-full max-w-lg flex-col rounded-lg border border-border-idle bg-surface-card">
        <div className="flex items-start justify-between border-b border-border-idle p-6 pb-4">
          <div>
            <h2 className="font-heading text-lg font-semibold text-text-main">
              Entrenadores a cargo
            </h2>
            <p className="font-body text-sm text-text-secondary">{socio.nombreCompleto}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            title="Cerrar"
            className="rounded-md p-1 text-text-muted hover:bg-surface-hover hover:text-text-main"
          >
            <X size={18} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {error && <p className="font-body text-sm text-status-danger">{error}</p>}
          {!error && cargando && <p className="font-body text-sm text-text-muted">Cargando…</p>}

          {!error && !cargando && (
            <>
              <p className="font-body text-xs text-text-muted">
                Puede tener más de uno a la vez — por ejemplo, uno de musculación y otro de
                funcional.
              </p>

              <ul className="mt-4 flex flex-col gap-2">
                {asignaciones.length === 0 && (
                  <li className="font-body text-sm text-text-muted">
                    Todavía no tiene ningún entrenador asignado.
                  </li>
                )}
                {asignaciones.map((a) => (
                  <li
                    key={a.idAsignacion}
                    className="flex items-center gap-3 rounded-md border border-border-idle p-3"
                  >
                    <Dumbbell
                      size={16}
                      className={a.activa ? 'shrink-0 text-primary-volt' : 'shrink-0 text-text-muted'}
                    />
                    <div className="min-w-0 flex-1">
                      <p
                        className={
                          a.activa
                            ? 'font-body text-sm text-text-main'
                            : 'font-body text-sm text-text-muted'
                        }
                      >
                        {a.entrenador}
                      </p>
                      <p className="font-body text-xs text-text-muted">
                        {a.especialidad ?? '—'}
                        {' · '}
                        {a.activa
                          ? 'desde ' + formatearFecha(parsearFecha(a.fechaInicio))
                          : formatearFecha(parsearFecha(a.fechaInicio)) +
                            ' — ' +
                            (a.fechaFin ? formatearFecha(parsearFecha(a.fechaFin)) : '—')}
                      </p>
                    </div>
                    {a.activa && puedeGestionar && (
                      <button
                        type="button"
                        onClick={() => void finalizar(a)}
                        disabled={guardando}
                        title="Terminar la relación (queda en el historial)"
                        className="rounded-md p-1.5 text-text-muted hover:bg-surface-hover hover:text-status-danger disabled:cursor-not-allowed"
                      >
                        <X size={15} />
                      </button>
                    )}
                    {!a.activa && (
                      <span className="font-body text-xs text-text-muted">finalizada</span>
                    )}
                  </li>
                ))}
              </ul>

              {puedeGestionar && (
                <div className="mt-6 border-t border-border-idle pt-5">
                  {elegibles.length > 0 ? (
                    <div className="flex items-end gap-3">
                      <div className="flex-1">
                        <SelectField
                          label="Asignar entrenador"
                          value={seleccion}
                          onChange={setSeleccion}
                          options={opciones}
                          placeholder="Elegí uno"
                          name="entrenador"
                        />
                      </div>
                      <PrimaryButton
                        label={guardando ? 'Asignando…' : 'Asignar'}
                        icon={Plus}
                        onClick={() => void asignar()}
                        disabled={guardando}
                      />
                    </div>
                  ) : disponibles.length > 0 ? (
                    <p className="font-body text-sm text-text-muted">
                      Ya tiene a cargo a todos los entrenadores disponibles.
                    </p>
                  ) : (
                    <p className="font-body text-sm text-status-warn">
                      No hay entrenadores activos cargados.
                    </p>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
