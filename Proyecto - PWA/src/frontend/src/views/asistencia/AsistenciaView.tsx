import { useEffect, useMemo, useState } from 'react';
import { Fingerprint, PencilLine, Search, Trash2, UserCheck } from 'lucide-react';
import { PrimaryButton, SectionCard, Topbar } from '../../components/ui';
import { colors } from '../../config';
import { mensajeDeError } from '../../services/api';
import {
  deshacerFichaje,
  getAsistenciasDeHoy,
  registrarAsistenciaManual,
  type AsistenciaRegistrada,
} from '../../services/actividadService';
import { listarSocios, type SocioListado } from '../../services/sociosService';
import { useAuthStore } from '../../store/authStore';
import { useUiStore } from '../../store/uiStore';

// Panel de recepción (especificacion_definitiva_actividades.md, Fase 4): se
// busca al socio, se le registra el ingreso, y abajo está la lista del día.
//
// SE RETIRÓ EL FICHAJE CON TARJETA
// --------------------------------
// Había una tarjeta "Fichar con tarjeta" con un input que se automantenía
// enfocado, pensada para un lector RFID —que funciona como un teclado rápido
// terminado en Enter—. El gimnasio no usa lector, así que ocupaba media
// pantalla del mostrador sin hacer nada. Los ingresos históricos con
// metodo_registro='RFID' siguen existiendo y la lista los distingue por el
// ícono: lo que se sacó es la forma de crear nuevos, no el dato viejo.
//
// PERO EL CAMINO RFID DEL BACKEND QUEDA A PROPÓSITO. Lo que se sacó fue el
// campo de texto, que no era un lector. El fichaje con tarjeta va a volver como
// aparato físico en la puerta, cuando se compre el sensor. Por eso `Socio.
// codigo_rfid` y el `codigo_rfid` de POST /asistencia/fichar siguen ahí aunque
// hoy nada los use: parecen código muerto y no lo son. Ver "Lo que FALTA" en
// docs/ESTADO-ACTUAL.md antes de limpiarlos.
//
// EL INGRESO REPETIDO SE MARCA, NO SE FRENA
// -----------------------------------------
// Antes, el segundo ingreso del día abría un diálogo de confirmación. Se sacó:
// quien atiende el mostrador no lee el cartel —con gente en la cola lo acepta
// sin mirarlo, o deja al socio parado en la puerta—. Ahora se registra siempre
// y la lista muestra un chip "2º de hoy" al lado del nombre. El dato sigue
// estando para quien quiera mirar el caso; lo que no hay es una pantalla
// pidiéndole permiso a alguien que está apurado.
//
// A diferencia de Mis Actividades, acá no hace falta recargar todo tras cada
// acción: un fichaje nuevo no le cambia el estado a ningún otro, así que
// alcanza con agregarlo al principio de la lista local.

const MAX_RESULTADOS_BUSQUEDA = 6;

function horaDe(fechaHoraIngreso: string): string {
  return fechaHoraIngreso.slice(11, 16);
}

export function AsistenciaView() {
  const idUsuarioActor = useAuthStore((s) => s.usuario?.id_usuario);
  const showSnack = useUiStore((s) => s.showSnack);
  const confirmDialog = useUiStore((s) => s.confirmDialog);

  const [fichajes, setFichajes] = useState<AsistenciaRegistrada[] | null>(null);
  const [socios, setSocios] = useState<SocioListado[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [busqueda, setBusqueda] = useState('');
  const [registrandoIdSocio, setRegistrandoIdSocio] = useState<number | null>(null);
  const [borrandoId, setBorrandoId] = useState<number | null>(null);

  useEffect(() => {
    Promise.all([getAsistenciasDeHoy(), listarSocios()])
      .then(([listaFichajes, listaSocios]) => {
        setFichajes(listaFichajes);
        setSocios(listaSocios);
      })
      .catch((err: unknown) => setError(mensajeDeError(err)));
  }, []);

  const resultadosBusqueda = useMemo(() => {
    const texto = busqueda.trim().toLowerCase();
    if (!texto || !socios) return [];
    return socios
      .filter((s) => s.activo && (s.nombreCompleto.toLowerCase().includes(texto) || s.dni.includes(texto)))
      .slice(0, MAX_RESULTADOS_BUSQUEDA);
  }, [busqueda, socios]);

  const registrarManual = (socio: SocioListado) => {
    if (!idUsuarioActor) return;
    setRegistrandoIdSocio(socio.idSocio);
    registrarAsistenciaManual(socio.idSocio, idUsuarioActor)
      .then((registro) => {
        setFichajes((prev) => [registro, ...(prev ?? [])]);
        // Si es repetido se dice acá también, no sólo en el chip de la lista:
        // quien acaba de tocar el botón está mirando el snack, no la lista.
        const repetido =
          (registro.ingresoNumero ?? 1) > 1 ? ` (${registro.ingresoNumero}º ingreso de hoy)` : '';
        showSnack(`Ingreso registrado: ${registro.nombreSocio}${repetido}`, colors.statusOk);
        setBusqueda('');
      })
      .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger))
      .finally(() => setRegistrandoIdSocio(null));
  };

  const pedirDeshacer = (f: AsistenciaRegistrada) => {
    confirmDialog(
      '¿Borrar este ingreso?',
      `Se elimina el ingreso de ${f.nombreSocio} de las ${horaDe(f.fechaHoraIngreso)}. ` +
        'Es para el ingreso que no ocurrió —alguien que fichó por otro, o el socio equivocado—: ' +
        'desaparece de la lista y deja de contar en el total del día.',
      () => {
        setBorrandoId(f.idAsistencia);
        deshacerFichaje(f.idAsistencia)
          .then(() => {
            setFichajes((prev) => (prev ?? []).filter((x) => x.idAsistencia !== f.idAsistencia));
            showSnack('Ingreso borrado', colors.statusOk);
          })
          .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger))
          .finally(() => setBorrandoId(null));
      },
    );
  };

  return (
    <div>
      <Topbar
        title="Panel de asistencia"
        subtitle={fichajes ? `${fichajes.length} ingreso${fichajes.length === 1 ? '' : 's'} hoy` : undefined}
      />

      <div className="space-y-4 p-8">
        {error && (
          <SectionCard>
            <p className="font-body text-sm text-status-danger">{error}</p>
          </SectionCard>
        )}

        <SectionCard title="Registrar ingreso">
          <div className="flex flex-col gap-3">
            <label className="flex flex-col gap-1.5 font-body text-sm">
              <span className="text-text-secondary">Buscar socio por nombre o DNI</span>
              <div className="flex items-center gap-2 rounded-md border border-border-idle bg-surface-card px-3 py-2 focus-within:border-border-active">
                <Search size={16} className="text-text-muted" />
                <input
                  value={busqueda}
                  onChange={(e) => setBusqueda(e.target.value)}
                  placeholder="Nombre o DNI del socio…"
                  className="w-full bg-transparent text-text-main outline-none placeholder:text-text-muted"
                />
              </div>
            </label>

            {busqueda.trim() && (
              <div className="flex flex-col divide-y divide-border-idle">
                {resultadosBusqueda.length === 0 ? (
                  <p className="py-2 font-body text-sm text-text-muted">Ningún socio activo coincide.</p>
                ) : (
                  resultadosBusqueda.map((socio) => (
                    <div key={socio.idSocio} className="flex items-center justify-between gap-3 py-2">
                      <div className="min-w-0">
                        <p className="font-body text-sm text-text-main">{socio.nombreCompleto}</p>
                        <p className="font-body text-xs text-text-muted">DNI {socio.dni}</p>
                      </div>
                      <PrimaryButton
                        label={registrandoIdSocio === socio.idSocio ? 'Registrando…' : 'Registrar ingreso'}
                        onClick={() => registrarManual(socio)}
                        disabled={registrandoIdSocio !== null}
                      />
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </SectionCard>

        <SectionCard title="Fichajes de hoy">
          {!fichajes ? (
            <div className="space-y-2">
              {[0, 1, 2].map((i) => (
                <div key={i} className="h-12 animate-pulse rounded-md bg-surface-hover" />
              ))}
            </div>
          ) : fichajes.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-8 text-center">
              <UserCheck size={28} className="text-text-muted" />
              <p className="font-body text-sm text-text-muted">Todavía no hay ingresos registrados hoy.</p>
            </div>
          ) : (
            <div className="flex flex-col divide-y divide-border-idle">
              {fichajes.map((f) => (
                <div key={f.idAsistencia} className="flex items-center justify-between gap-3 py-2.5">
                  <div className="flex min-w-0 items-center gap-2">
                    {/* Los ingresos viejos cargados con lector siguen en la
                        base: el ícono los distingue de los manuales. */}
                    {f.metodoRegistro === 'RFID' ? (
                      <Fingerprint size={16} className="shrink-0 text-primary-volt" />
                    ) : (
                      <PencilLine size={16} className="shrink-0 text-text-muted" />
                    )}
                    <p className="truncate font-body text-sm text-text-main">{f.nombreSocio}</p>
                    {/* Lo que reemplazó al tope diario: se ve que ya había
                        entrado hoy, sin haberle frenado el paso a nadie. */}
                    {(f.ingresoNumero ?? 1) > 1 && (
                      <span
                        title="Ya había fichado antes hoy"
                        className="shrink-0 whitespace-nowrap rounded-full bg-surface-hover px-2 py-0.5 font-body text-[11px] text-status-warn"
                      >
                        {f.ingresoNumero}º de hoy
                      </span>
                    )}
                  </div>
                  <div className="flex shrink-0 items-center gap-3">
                    <span className="font-mono text-xs text-text-secondary">{horaDe(f.fechaHoraIngreso)}</span>
                    <button
                      type="button"
                      onClick={() => pedirDeshacer(f)}
                      disabled={borrandoId !== null}
                      title="Deshacer este ingreso"
                      className="rounded-md p-1 text-text-muted hover:bg-surface-hover hover:text-status-danger disabled:opacity-40"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </SectionCard>
      </div>
    </div>
  );
}
