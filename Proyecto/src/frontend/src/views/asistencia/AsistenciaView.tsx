import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { Fingerprint, PencilLine, Search, UserCheck } from 'lucide-react';
import { PrimaryButton, SectionCard, Topbar } from '../../components/ui';
import { colors } from '../../config';
import { mensajeDeError } from '../../services/api';
import {
  ficharRFID,
  getAsistenciasDeHoy,
  registrarAsistenciaManual,
  type AsistenciaRegistrada,
} from '../../services/actividadService';
import { listarSocios, type SocioListado } from '../../services/sociosService';
import { useAuthStore } from '../../store/authStore';
import { useUiStore } from '../../store/uiStore';

// Panel de recepción (especificacion_definitiva_actividades.md, Fase 4):
// fichaje por tarjeta RFID + carga manual para quien se olvidó la tarjeta.
// Un lector RFID funciona como un teclado rápido que termina en Enter, por
// eso el input de tarjeta se automantiene enfocado y se limpia solo después
// de cada lectura — no hace falta que recepción clickee nada entre fichajes.
//
// A diferencia de Mis Actividades, acá no hace falta recargar todo tras
// cada acción: un fichaje nuevo no le cambia el estado a ningún otro, así
// que alcanza con agregarlo al principio de la lista local.

const MAX_RESULTADOS_BUSQUEDA = 6;

function horaDe(fechaHoraIngreso: string): string {
  return fechaHoraIngreso.slice(11, 16);
}

export function AsistenciaView() {
  const idUsuarioActor = useAuthStore((s) => s.usuario?.id_usuario);
  const showSnack = useUiStore((s) => s.showSnack);

  const [fichajes, setFichajes] = useState<AsistenciaRegistrada[] | null>(null);
  const [socios, setSocios] = useState<SocioListado[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [codigoRfid, setCodigoRfid] = useState('');
  const [fichando, setFichando] = useState(false);
  const rfidRef = useRef<HTMLInputElement>(null);

  const [busqueda, setBusqueda] = useState('');
  const [registrandoIdSocio, setRegistrandoIdSocio] = useState<number | null>(null);

  useEffect(() => {
    Promise.all([getAsistenciasDeHoy(), listarSocios()])
      .then(([listaFichajes, listaSocios]) => {
        setFichajes(listaFichajes);
        setSocios(listaSocios);
      })
      .catch((err: unknown) => setError(mensajeDeError(err)));
    rfidRef.current?.focus();
  }, []);

  const resultadosBusqueda = useMemo(() => {
    const texto = busqueda.trim().toLowerCase();
    if (!texto || !socios) return [];
    return socios
      .filter((s) => s.activo && (s.nombreCompleto.toLowerCase().includes(texto) || s.dni.includes(texto)))
      .slice(0, MAX_RESULTADOS_BUSQUEDA);
  }, [busqueda, socios]);

  const fichar = (e: FormEvent) => {
    e.preventDefault();
    if (!codigoRfid.trim() || fichando) return;
    setFichando(true);
    ficharRFID(codigoRfid)
      .then((registro) => {
        setFichajes((prev) => [registro, ...(prev ?? [])]);
        showSnack(`Ingreso registrado: ${registro.nombreSocio}`, colors.statusOk);
      })
      .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger))
      .finally(() => {
        setCodigoRfid('');
        setFichando(false);
        rfidRef.current?.focus();
      });
  };

  const registrarManual = (socio: SocioListado) => {
    if (!idUsuarioActor) return;
    setRegistrandoIdSocio(socio.idSocio);
    registrarAsistenciaManual(socio.idSocio, idUsuarioActor)
      .then((registro) => {
        setFichajes((prev) => [registro, ...(prev ?? [])]);
        showSnack(`Ingreso registrado: ${registro.nombreSocio}`, colors.statusOk);
        setBusqueda('');
      })
      .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger))
      .finally(() => setRegistrandoIdSocio(null));
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

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <SectionCard title="Fichar con tarjeta">
            <form onSubmit={fichar} className="flex flex-col gap-3">
              <label className="flex flex-col gap-1.5 font-body text-sm">
                <span className="text-text-secondary">Código de tarjeta</span>
                <div className="flex items-center gap-2 rounded-md border border-border-idle bg-surface-card px-3 py-2 focus-within:border-border-active">
                  <Fingerprint size={16} className="text-text-muted" />
                  <input
                    ref={rfidRef}
                    value={codigoRfid}
                    onChange={(e) => setCodigoRfid(e.target.value)}
                    placeholder="Pasá la tarjeta o escribí el código…"
                    disabled={fichando}
                    className="w-full bg-transparent text-text-main outline-none placeholder:text-text-muted"
                  />
                </div>
              </label>
              <p className="font-body text-xs text-text-muted">
                El campo queda enfocado todo el tiempo: pasar la tarjeta alcanza, no hace falta clickear nada.
              </p>
            </form>
          </SectionCard>

          <SectionCard title="Carga manual">
            <div className="flex flex-col gap-3">
              <label className="flex flex-col gap-1.5 font-body text-sm">
                <span className="text-text-secondary">Buscar socio por nombre o DNI</span>
                <div className="flex items-center gap-2 rounded-md border border-border-idle bg-surface-card px-3 py-2 focus-within:border-border-active">
                  <Search size={16} className="text-text-muted" />
                  <input
                    value={busqueda}
                    onChange={(e) => setBusqueda(e.target.value)}
                    placeholder="Para quien se olvidó la tarjeta…"
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
        </div>

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
                  <div className="flex items-center gap-2 min-w-0">
                    {f.metodoRegistro === 'RFID' ? (
                      <Fingerprint size={16} className="shrink-0 text-primary-volt" />
                    ) : (
                      <PencilLine size={16} className="shrink-0 text-text-muted" />
                    )}
                    <p className="truncate font-body text-sm text-text-main">{f.nombreSocio}</p>
                  </div>
                  <span className="font-mono text-xs text-text-secondary">{horaDe(f.fechaHoraIngreso)}</span>
                </div>
              ))}
            </div>
          )}
        </SectionCard>
      </div>
    </div>
  );
}
