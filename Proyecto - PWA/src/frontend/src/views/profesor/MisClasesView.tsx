import { useEffect, useState } from 'react';
import { CalendarCheck, CircleAlert, Users2 } from 'lucide-react';
import { SectionCard, Topbar } from '../../components/ui';
import { mensajeDeError } from '../../services/api';
import { getMisClases, type EstadoInscripto, type MiClase } from '../../services/profesorService';

// "Mis clases" — la única pantalla del profesor.
//
// Existe porque hasta el 2026-09-16 el profesor NO tenía cuenta: daba clases
// y se enteraba de su horario por WhatsApp o por un papel en la pared, y para
// saber quién se había anotado tenía que preguntarle a alguien del mostrador.
// El endpoint que lista los anotados existía desde siempre —su docstring decía
// "es la lista que usa el profesor"— pero ninguna pantalla lo llamaba.
//
// Es SÓLO LECTURA a propósito. El profesor mira su clase; cancelar un turno
// sigue siendo decisión de quien maneja el gimnasio, no de quien la dicta.
//
// Los datos vienen del mismo armador que el panel de recepción, así que dicen
// exactamente lo mismo que ve el mostrador. No hay dos versiones de "quién se
// anotó" que puedan discrepar.

const ESTADO_LABEL: Record<EstadoInscripto, string> = {
  pendiente: 'Falta llegar',
  asistio: 'Presente',
  ausente: 'No llegó',
  en_espera: 'En espera',
  cancelada: 'Canceló',
};

// Mismos colores que la vista de Recepción en Flet, para que el mismo estado
// no se vea de dos colores distintos según quién mire.
const ESTADO_COLOR: Record<EstadoInscripto, string> = {
  pendiente: 'text-text-secondary',
  asistio: 'text-status-ok',
  ausente: 'text-status-danger',
  en_espera: 'text-status-warn',
  cancelada: 'text-text-muted',
};

/** "lun 16/09". Local y no del util compartido: son dos líneas y evita atar
 *  esta pantalla a un formato pensado para otra. */
function fechaCorta(iso: string): string {
  const [anio, mes, dia] = iso.split('-').map(Number);
  const d = new Date(anio, mes - 1, dia);
  const diaSemana = ['dom', 'lun', 'mar', 'mié', 'jue', 'vie', 'sáb'][d.getDay()];
  return `${diaSemana} ${String(dia).padStart(2, '0')}/${String(mes).padStart(2, '0')}`;
}

/** "en 25 min", "en 3 h", "empezó hace 10 min". */
function cuando(minutos: number): string {
  if (minutos < 0) {
    const pasados = Math.abs(minutos);
    return pasados < 60 ? `empezó hace ${pasados} min` : 'ya empezó';
  }
  if (minutos < 60) return `en ${minutos} min`;
  return `en ${Math.round(minutos / 60)} h`;
}

export function MisClasesView() {
  const [clases, setClases] = useState<MiClase[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getMisClases()
      .then(setClases)
      .catch((err: unknown) => setError(mensajeDeError(err)));
  }, []);

  return (
    <div>
      <Topbar
        title="Mis clases"
        subtitle={
          clases
            ? `${clases.length} clase${clases.length === 1 ? '' : 's'} en los próximos 7 días`
            : undefined
        }
      />

      <div className="space-y-4 p-4 md:p-8">
        {error && (
          <SectionCard>
            <p className="font-body text-sm text-status-danger">{error}</p>
          </SectionCard>
        )}

        {!error && !clases && (
          <div className="space-y-3">
            {[0, 1].map((i) => (
              <div key={i} className="h-40 animate-pulse rounded-lg bg-surface-hover" />
            ))}
          </div>
        )}

        {!error && clases && clases.length === 0 && (
          <SectionCard>
            <div className="flex flex-col items-center gap-2 py-8 text-center">
              <CalendarCheck size={28} className="text-text-muted" />
              <p className="font-body text-sm text-text-muted">
                No tenés clases asignadas en los próximos 7 días.
              </p>
              <p className="font-body text-xs text-text-muted">
                Las asigna el gimnasio desde el horario semanal de cada actividad.
              </p>
            </div>
          </SectionCard>
        )}

        {!error &&
          clases?.map((clase) => (
            <SectionCard key={clase.idTurno}>
              <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                <div className="flex min-w-0 items-center gap-2">
                  <CalendarCheck size={18} className="shrink-0 text-primary-volt" />
                  <h3 className="truncate font-heading text-lg font-semibold text-text-main">
                    {clase.actividad}
                  </h3>
                </div>
                <span className="shrink-0 font-mono text-sm text-text-secondary">
                  {fechaCorta(clase.fecha)} · {clase.hora.slice(0, 5)}
                </span>
              </div>

              <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 font-body text-xs text-text-muted">
                <span className="inline-flex items-center gap-1">
                  <Users2 size={12} />
                  {clase.ocupados}/{clase.cupoMaximo} anotados
                </span>
                {clase.enEspera > 0 && <span>{clase.enEspera} en espera</span>}
                <span>{cuando(clase.minutosParaEmpezar)}</span>
              </div>

              <div className="mt-3 flex flex-col divide-y divide-border-idle border-t border-border-idle">
                {clase.inscriptos.length === 0 ? (
                  <p className="py-3 font-body text-sm text-text-muted">
                    Todavía no se anotó nadie.
                  </p>
                ) : (
                  clase.inscriptos.map((inscripto) => (
                    <div
                      key={inscripto.idReserva}
                      className="flex items-center justify-between gap-3 py-2.5"
                    >
                      <div className="min-w-0">
                        <p className="truncate font-body text-sm text-text-main">
                          {inscripto.nombre}
                        </p>
                        {/* La alerta es para el mostrador, no para el profesor:
                            se muestra pero sin acción, porque cobrar no es su
                            tarea. Saber que alguien está con la cuota vencida
                            igual le sirve para mandarlo a recepción. */}
                        {inscripto.alerta && (
                          <p className="flex items-center gap-1 font-body text-xs text-status-warn">
                            <CircleAlert size={11} className="shrink-0" />
                            {inscripto.alerta}
                          </p>
                        )}
                      </div>
                      <span
                        className={`shrink-0 whitespace-nowrap font-body text-xs ${ESTADO_COLOR[inscripto.estado]}`}
                      >
                        {ESTADO_LABEL[inscripto.estado]}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </SectionCard>
          ))}
      </div>
    </div>
  );
}
