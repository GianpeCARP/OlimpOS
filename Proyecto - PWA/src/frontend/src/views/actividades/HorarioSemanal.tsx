import { CalendarPlus, RefreshCw, X } from 'lucide-react';
import { SectionCard } from '../../components/ui';
import { DIAS_SEMANA, type Horario } from '../../services/turnosService';

// El horario de la semana como grilla de 7 columnas. Gemela de
// _grilla_semanal en app/views/actividades.py (Flet).
//
// Grilla y no lista porque el horario de un gimnasio se piensa en semana: lo
// que uno quiere ver de un vistazo es qué días están vacíos y a qué hora se
// pisan dos clases. Una lista ordenada por actividad esconde justo eso.
//
// Va ARRIBA del catálogo: el catálogo dice qué actividades existen; esto dice
// cuándo pasan, que es lo que hace que existan turnos y que alguien pueda
// reservar. Una actividad sin horario no la ve nadie.

interface HorarioSemanalProps {
  horarios: Horario[];
  /** Sin la acción gestionTurnos no se dibujan los botones (se omiten, no se deshabilitan). */
  puedeGestionar: boolean;
  onNuevo: () => void;
  onBaja: (horario: Horario) => void;
  onRegenerar: () => void;
}

export function HorarioSemanal({
  horarios,
  puedeGestionar,
  onNuevo,
  onBaja,
  onRegenerar,
}: HorarioSemanalProps) {
  const activos = horarios.filter((h) => h.activo);
  const turnosGenerados = activos.reduce((suma, h) => suma + h.turnosFuturos, 0);

  return (
    <SectionCard>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="font-heading text-lg font-semibold text-text-main">Horario semanal</h2>
          <p className="font-body text-xs text-text-muted">
            {turnosGenerados > 0
              ? `${turnosGenerados} turnos generados hacia adelante`
              : 'Sin horarios no hay turnos, y sin turnos nadie puede reservar.'}
          </p>
        </div>
        {puedeGestionar && (
          <div className="flex shrink-0 gap-2">
            <button
              type="button"
              onClick={onRegenerar}
              className="inline-flex shrink-0 items-center gap-1.5 rounded-md px-3 py-2 font-body text-sm whitespace-nowrap text-text-secondary hover:bg-surface-hover hover:text-text-main"
            >
              <RefreshCw size={14} /> Regenerar turnos
            </button>
            <button
              type="button"
              onClick={onNuevo}
              className="inline-flex shrink-0 items-center gap-1.5 rounded-md border border-border-idle px-3 py-2 font-body text-sm whitespace-nowrap text-text-main hover:border-primary-volt"
            >
              <CalendarPlus size={14} /> Nuevo horario
            </button>
          </div>
        )}
      </div>

      {activos.length === 0 ? (
        <p className="mt-4 font-body text-sm text-text-muted">
          Todavía no hay ningún horario cargado. Mientras no haya uno, nadie puede reservar, el
          profesor no ve clases y el mostrador no tiene turnos que mirar.
        </p>
      ) : (
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-4 xl:grid-cols-7">
          {DIAS_SEMANA.map((nombre, i) => {
            const delDia = activos
              .filter((h) => h.diaSemana === i + 1)
              .sort((a, b) => a.hora.localeCompare(b.hora));
            return (
              <div key={nombre} className="min-w-0">
                <p className="mb-2 font-body text-[10px] font-semibold tracking-wide text-text-muted uppercase">
                  {nombre}
                </p>
                <div className="flex flex-col gap-2">
                  {delDia.length === 0 ? (
                    <span className="font-body text-xs text-text-muted">—</span>
                  ) : (
                    delDia.map((h) => (
                      <ChipHorario
                        key={h.idHorario}
                        horario={h}
                        puedeGestionar={puedeGestionar}
                        onBaja={() => onBaja(h)}
                      />
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </SectionCard>
  );
}

/**
 * Un horario dentro de su día. Muestra cuántos turnos futuros generó: es la
 * forma de ver que la generación automática corre. Un horario activo con 0
 * turnos futuros se pinta de advertencia, porque algo no está funcionando.
 */
function ChipHorario({
  horario,
  puedeGestionar,
  onBaja,
}: {
  horario: Horario;
  puedeGestionar: boolean;
  onBaja: () => void;
}) {
  const sinTurnos = horario.turnosFuturos === 0;
  return (
    <div
      className={`rounded-md border px-2 py-1.5 ${
        sinTurnos
          ? 'border-status-warn/30 bg-status-warn/10'
          : 'border-primary-volt/30 bg-primary-volt/10'
      }`}
    >
      <div className="flex items-center justify-between gap-1">
        <span
          className={`font-mono text-sm font-bold ${sinTurnos ? 'text-status-warn' : 'text-primary-volt'}`}
        >
          {horario.hora}
        </span>
        {puedeGestionar && (
          <button
            type="button"
            onClick={onBaja}
            title="Dar de baja este horario"
            className="shrink-0 rounded p-0.5 text-text-muted hover:text-status-danger"
          >
            <X size={12} />
          </button>
        )}
      </div>
      <p className="truncate font-body text-xs text-text-main">{horario.actividad}</p>
      <p className="truncate font-body text-[10px] text-text-muted">
        cupo {horario.cupo} · {horario.profesor ?? 'sin profesor'}
      </p>
      <p className={`font-body text-[10px] ${sinTurnos ? 'text-status-warn' : 'text-text-muted'}`}>
        {sinTurnos ? 'sin turnos generados' : `${horario.turnosFuturos} turnos`}
      </p>
    </div>
  );
}
