import { useCallback, useEffect, useMemo, useState } from 'react';
import { CalendarX2, Clock, Hourglass, Users } from 'lucide-react';
import { PrimaryButton, SectionCard, Topbar } from '../../components/ui';
import { colors } from '../../config';
import { mensajeDeError } from '../../services/api';
import {
  cancelarMiTurno,
  getTurnosDelSocio,
  reservarMiTurno,
  type TurnoDelSocio,
} from '../../services/socioService';
import { useAuthStore } from '../../store/authStore';
import { useUiStore } from '../../store/uiStore';
import { formatearFecha } from '../../utils/format';
import { parsearFecha } from '../../utils/fechas';
import { SinSocioEnSesion } from './SinSocioEnSesion';

// =============================================================================
// Mis turnos — el socio se anota y se baja solo
// =============================================================================
//
// Esta vista estuvo CONGELADA, y el comentario de SOCIO_NAV_ITEMS en config.ts
// explicaba por qué: el gimnasio iba a pasar a un modelo mixto —musculación y
// cardio de acceso libre, más actividades con horario fijo, cupo y
// profesional asignado— y no tenía sentido escribir la pantalla antes de que
// ese modelo existiera.
//
// Ese modelo ya existe. Actividad tiene cupo, profesor y tolerancia;
// Horario_Actividad declara el horario semanal y el backend genera los turnos
// solo; y la sala abierta se distingue de una clase por su cupo. La
// precondición está cumplida, así que la vista se descongela.
//
// Lo que la ordena: que el socio no tenga que llamar ni pasar por el
// mostrador para anotarse. Y que sepa las reglas ANTES de anotarse, no
// cuando ya es tarde — la tolerancia y la anticipación para cancelar están a
// la vista en cada turno.

function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-surface-hover ${className}`} />;
}

/** Agrupa por fecha manteniendo el orden que ya trae el backend. */
function porDia(turnos: TurnoDelSocio[]): Array<[string, TurnoDelSocio[]]> {
  const mapa = new Map<string, TurnoDelSocio[]>();
  turnos.forEach((t) => {
    const lista = mapa.get(t.fecha) ?? [];
    lista.push(t);
    mapa.set(t.fecha, lista);
  });
  return Array.from(mapa.entries());
}

export function MisTurnosView() {
  const idSocio = useAuthStore((s) => s.idSocio);
  const showSnack = useUiStore((s) => s.showSnack);
  const confirmDialog = useUiStore((s) => s.confirmDialog);

  const [turnos, setTurnos] = useState<TurnoDelSocio[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intento, setIntento] = useState(0);
  const [ocupado, setOcupado] = useState<number | null>(null);

  useEffect(() => {
    if (idSocio === null) return;
    let cancelado = false;
    setTurnos(null);
    setError(null);

    getTurnosDelSocio()
      .then((lista) => {
        if (!cancelado) setTurnos(lista);
      })
      .catch((err: unknown) => {
        if (!cancelado) setError(mensajeDeError(err));
      });

    return () => {
      cancelado = true;
    };
  }, [idSocio, intento]);

  const recargar = useCallback(() => setIntento((n) => n + 1), []);

  const mios = useMemo(() => (turnos ?? []).filter((t) => t.yaAnotado), [turnos]);

  const reservar = useCallback(
    async (turno: TurnoDelSocio) => {
      setOcupado(turno.idTurno);
      try {
        const { estado } = await reservarMiTurno(turno.idTurno);
        // El mensaje distingue los dos desenlaces porque son cosas
        // distintas: uno tiene lugar, el otro está esperando que se libere.
        // Decir "listo" en los dos casos haría que alguien se presentara a
        // una clase en la que no entró.
        if (estado === 'EN_ESPERA') {
          showSnack(
            `Quedaste en lista de espera de ${turno.nombreActividad}. Si alguien cancela, entrás automáticamente y te avisamos.`,
            colors.statusWarn,
          );
        } else {
          showSnack(`Listo, tenés lugar en ${turno.nombreActividad}`, colors.statusOk);
        }
        recargar();
      } catch (err) {
        showSnack(mensajeDeError(err), colors.statusDanger);
      } finally {
        setOcupado(null);
      }
    },
    [showSnack, recargar],
  );

  const cancelar = useCallback(
    (turno: TurnoDelSocio) => {
      if (turno.idMiReserva === undefined) return;
      const enEspera = turno.miEstado === 'EN_ESPERA';

      confirmDialog(
        enEspera ? 'Salir de la lista de espera' : 'Cancelar el turno',
        enEspera
          ? `Vas a salir de la lista de espera de ${turno.nombreActividad}.`
          : `Vas a cancelar ${turno.nombreActividad} del ${formatearFecha(parsearFecha(turno.fecha))} a las ${turno.hora.slice(0, 5)}.` +
            (turno.horasAnticipacionCancelacion > 0
              ? ` Si cancelás con menos de ${turno.horasAnticipacionCancelacion} h de anticipación y usaste un abono, esa clase se pierde.`
              : ''),
        () => {
          setOcupado(turno.idTurno);
          cancelarMiTurno(turno.idMiReserva as number)
            .then(() => {
              showSnack('Listo, ya no estás anotado', colors.statusOk);
              recargar();
            })
            .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger))
            .finally(() => setOcupado(null));
        },
      );
    },
    [confirmDialog, showSnack, recargar],
  );

  if (idSocio === null) {
    return <SinSocioEnSesion titulo="Mis turnos" />;
  }

  return (
    <div>
      <Topbar
        title="Mis turnos"
        subtitle={
          turnos
            ? mios.length === 0
              ? 'No tenés turnos reservados'
              : `${mios.length} turno${mios.length === 1 ? '' : 's'} reservado${mios.length === 1 ? '' : 's'}`
            : undefined
        }
      />

      <div className="space-y-4 p-4 md:p-8">
        {error && (
          <SectionCard>
            <p className="mb-4 font-body text-sm text-status-danger">{error}</p>
            <PrimaryButton label="Reintentar" onClick={recargar} />
          </SectionCard>
        )}

        {!error && !turnos && (
          <div className="space-y-4">
            <Skeleton className="h-24" />
            <Skeleton className="h-64" />
          </div>
        )}

        {turnos && turnos.length === 0 && (
          <SectionCard>
            <div className="flex flex-col items-center gap-3 py-10 text-center">
              <CalendarX2 size={32} style={{ color: colors.textMuted }} />
              <p className="font-body text-sm" style={{ color: colors.textSecondary }}>
                No hay clases programadas para los próximos días.
              </p>
              <p className="font-body text-xs" style={{ color: colors.textMuted }}>
                Cuando el gimnasio cargue el horario semanal, las clases van a aparecer acá.
              </p>
            </div>
          </SectionCard>
        )}

        {turnos && turnos.length > 0 && (
          <>
            {mios.length > 0 && (
              <SectionCard title="Tus próximos turnos">
                <div className="space-y-2">
                  {mios.map((t) => (
                    <FilaTurno
                      key={t.idTurno}
                      turno={t}
                      ocupado={ocupado === t.idTurno}
                      onReservar={reservar}
                      onCancelar={cancelar}
                    />
                  ))}
                </div>
              </SectionCard>
            )}

            <SectionCard title="Clases disponibles">
              <div className="space-y-5">
                {porDia(turnos).map(([fecha, delDia]) => (
                  <div key={fecha}>
                    <p
                      className="mb-2 font-body text-xs uppercase tracking-wide"
                      style={{ color: colors.textMuted }}
                    >
                      {formatearFecha(parsearFecha(fecha))}
                    </p>
                    <div className="space-y-2">
                      {delDia.map((t) => (
                        <FilaTurno
                          key={t.idTurno}
                          turno={t}
                          ocupado={ocupado === t.idTurno}
                          onReservar={reservar}
                          onCancelar={cancelar}
                        />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </SectionCard>
          </>
        )}
      </div>
    </div>
  );
}

interface FilaTurnoProps {
  turno: TurnoDelSocio;
  ocupado: boolean;
  onReservar: (t: TurnoDelSocio) => void;
  onCancelar: (t: TurnoDelSocio) => void;
}

function FilaTurno({ turno, ocupado, onReservar, onCancelar }: FilaTurnoProps) {
  const lleno = turno.cupoDisponible === 0;
  const anotado = turno.miEstado === 'RESERVADA';
  const esperando = turno.miEstado === 'EN_ESPERA';

  // El botón dice exactamente lo que va a pasar. "Reservar" en una clase
  // llena sería mentira: lo que se consigue ahí es un lugar en la cola, y el
  // socio tiene que saberlo ANTES de apretar, no después.
  let etiqueta: string;
  if (anotado) etiqueta = 'Cancelar';
  else if (esperando) etiqueta = 'Salir de la espera';
  else if (lleno) etiqueta = 'Anotarme en la espera';
  else etiqueta = 'Reservar';

  const color = anotado || esperando ? colors.statusDanger : colors.primaryVolt;

  return (
    <div
      className="flex flex-wrap items-center gap-3 rounded-lg border p-3"
      style={{
        borderColor: anotado
          ? colors.statusOk
          : esperando
            ? colors.statusWarn
            : colors.borderIdle,
        backgroundColor: colors.surfaceBase,
      }}
    >
      <div className="flex min-w-[4.5rem] items-center gap-1.5">
        <Clock size={14} style={{ color: colors.textMuted }} />
        <span className="font-mono text-sm" style={{ color: colors.textMain }}>
          {turno.hora.slice(0, 5)}
        </span>
      </div>

      <div className="min-w-[8rem] flex-1">
        <p className="font-body text-sm" style={{ color: colors.textMain }}>
          {turno.nombreActividad}
        </p>
        <p className="font-body text-xs" style={{ color: colors.textMuted }}>
          {turno.nombreProfesional ?? 'Sin profesor asignado'}
          {' · '}
          {/* Las dos reglas que necesita saber ANTES de anotarse. Mostrarlas
              recién cuando ya perdió la clase es la forma más segura de que
              venga a reclamar al mostrador — que es lo que esto evita. */}
          {turno.minutosTolerancia} min de tolerancia
          {turno.horasAnticipacionCancelacion > 0 &&
            ` · cancelar con ${turno.horasAnticipacionCancelacion} h`}
        </p>
      </div>

      <div className="flex items-center gap-1.5">
        <Users size={14} style={{ color: colors.textMuted }} />
        <span className="font-mono text-xs" style={{ color: colors.textSecondary }}>
          {turno.cupoMaximo - turno.cupoDisponible}/{turno.cupoMaximo}
        </span>
      </div>

      {/* Cuánta gente hay esperando. Es lo que le permite decidir si vale la
          pena ponerse en la cola: uno adelante es probable, doce no. */}
      {turno.enEspera > 0 && (
        <div className="flex items-center gap-1.5">
          <Hourglass size={13} style={{ color: colors.statusWarn }} />
          <span className="font-body text-xs" style={{ color: colors.statusWarn }}>
            {turno.enEspera} esperando
          </span>
        </div>
      )}

      {esperando && (
        <span
          className="rounded-full px-2 py-0.5 font-body text-xs"
          style={{ color: colors.statusWarn, backgroundColor: `${colors.statusWarn}1f` }}
        >
          Estás en la lista
        </span>
      )}

      {/* Boton propio y no PrimaryButton: cancelar tiene que verse distinto de
          reservar. Que los dos sean del mismo volt haria que salirse de una
          clase se pareciera a anotarse, y son acciones opuestas. PrimaryButton
          no acepta color por props, y agregarselo lo volveria configurable
          para todo el sistema por un caso puntual. */}
      <button
        type="button"
        disabled={ocupado}
        onClick={() => (anotado || esperando ? onCancelar(turno) : onReservar(turno))}
        className="rounded-lg px-4 py-2 font-body text-sm font-medium transition-opacity disabled:opacity-50"
        style={{
          backgroundColor: color,
          // El volt es casi amarillo: encima SIEMPRE va texto oscuro, nunca
          // blanco. Es la regla de la paleta Kinetic Carbon.
          color: anotado || esperando ? colors.textMain : colors.surfaceBase,
        }}
      >
        {ocupado ? '...' : etiqueta}
      </button>
    </div>
  );
}
