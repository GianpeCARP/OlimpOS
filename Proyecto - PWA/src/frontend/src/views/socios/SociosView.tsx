import { useCallback, useEffect, useMemo, useState } from 'react';
import { Search, UserPlus } from 'lucide-react';
import { FilterChip, PrimaryButton, SectionCard, Topbar } from '../../components/ui';
import { Acceso, colors, EstadoSocio, Routes, type EstadoSocioValue } from '../../config';
import { mensajeDeError } from '../../services/api';
import {
  listarSocios,
  darDeBajaSocio,
  anularBajaSocio,
  reactivarSocio,
  type SocioListado,
} from '../../services/sociosService';
import { useUiStore } from '../../store/uiStore';
import { useAccesoSeccion, usePuedeAccion } from '../../hooks/usePermisos';
import { useAuthStore } from '../../store/authStore';
import { formatearFecha } from '../../utils/format';
import { parsearFecha } from '../../utils/fechas';
import { EntrenadoresModal } from './EntrenadoresModal';
import { PatologiasModal } from './PatologiasModal';
import { SocioFormModal } from './SocioFormModal';
import { SocioTableRow } from './SocioTableRow';
import { SortableHeader } from './SortableHeader';
import { BajaSocioModal } from './BajaSocioModal';
import { EmergenciaModal } from './EmergenciaModal';
import { TelefonosModal } from './TelefonosModal';

// Equivalente de SociosView (estructura_socios.md).
//
// El doc especifica 3 chips de estado ("Todos"/"Activos"/"Vencidos") y una
// sola columna ordenable (Nombre, A-Z ↔ Z-A). Acá el estado de un socio
// tiene 6 valores posibles (EstadoSocio en config.ts, calculados en
// membresiaService a partir de Socio + Membresia) y no solo 2 — así que los
// chips agrupan varios estados cada uno (ver coincideFiltro) — y se agregan
// dos columnas ordenables más que el doc no cubría: "Vence" (para priorizar
// a quién contactar) y "Estado" (para agrupar por urgencia). El mecanismo es
// el mismo header-clickeable que ya pedía el doc para "Nombre", solo que se
// reusa en dos columnas más.

type FiltroEstado = 'Todos' | 'Activos' | 'Vencidos';
const FILTROS: FiltroEstado[] = ['Todos', 'Activos', 'Vencidos'];

type CampoOrden = 'nombre' | 'estado' | 'vencimiento';

// Orden de urgencia para el filtro "Vencidos" y para ordenar por Estado:
// primero lo que necesita acción del staff, al final lo que no.
const PRIORIDAD_ESTADO: Record<EstadoSocioValue, number> = {
  [EstadoSocio.VENCIDO]: 0,
  [EstadoSocio.SUSPENDIDO]: 1,
  [EstadoSocio.POR_VENCER]: 2,
  [EstadoSocio.SIN_MEMBRESIA]: 3,
  [EstadoSocio.ACTIVO]: 4,
  // Abajo de ACTIVO a propósito: una pausa la pidió el socio, así que no
  // requiere que el staff haga nada. Va cerca del final justamente porque
  // esta lista ordena por "qué necesita acción", no por gravedad.
  [EstadoSocio.EN_PAUSA]: 5,
  [EstadoSocio.DE_BAJA]: 6,
};

function coincideFiltro(estado: EstadoSocioValue, filtro: FiltroEstado): boolean {
  if (filtro === 'Todos') return true;
  if (filtro === 'Activos') return estado === EstadoSocio.ACTIVO || estado === EstadoSocio.POR_VENCER;
  return estado === EstadoSocio.VENCIDO || estado === EstadoSocio.SUSPENDIDO;
}

function Skeleton({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-md bg-surface-hover ${className}`} />;
}

export function SociosView() {
  const showSnack = useUiStore((s) => s.showSnack);

  // Dos permisos distintos y no uno: Entrenador/Nutricionista tienen la
  // sección en LECTURA (necesitan saber a quién le asignan una rutina o
  // dieta) — ven la tabla pero ningún botón. Editar exige acceso TOTAL;
  // el alta y la baja exigen además la acción puntual de la matriz.
  const puedeEditar = useAccesoSeccion(Routes.SOCIOS) === Acceso.TOTAL;
  const puedeAltaBaja = usePuedeAccion('altaBajaSocios');
  // Un tercer permiso, que no se deduce de los otros dos ni del acceso a la
  // sección: el Recepcionista tiene Socios en TOTAL y esta acción en false,
  // mientras que el Entrenador está justo al revés. Es la única de la matriz
  // donde el mostrador queda por debajo del Entrenador, y el motivo está en el
  // docstring de routers/patologias.py.
  const puedeVerHistorialMedico = usePuedeAccion('verHistorialMedico');
  // Asignar un entrenador pide `gestionRutinas` y NO `altaBajaSocios`: no es
  // un dato administrativo del socio, es una decisión de entrenamiento.
  //
  // Pero al ENTRENADOR no se le ofrece: quién entrena a quién lo deciden el
  // Dueño y el Recepcionista. Él abre el modal y ve los entrenadores del
  // socio, sin asignar ni finalizar. (El backend además le impide tocar
  // asignaciones que no sean suyas.)
  const roles = useAuthStore((s) => s.roles);
  const puedeAsignarEntrenadores =
    usePuedeAccion('gestionRutinas') && (roles.includes('dueno') || roles.includes('recepcionista'));

  const [socios, setSocios] = useState<SocioListado[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intento, setIntento] = useState(0);

  const [busqueda, setBusqueda] = useState('');
  const [filtro, setFiltro] = useState<FiltroEstado>('Todos');
  // Campo y sentido van juntos en un solo estado: son una sola decisión
  // ("ordenar por X en sentido Y") y separarlos obliga a que un setter llame
  // al otro, que es impuro — StrictMode invoca los updaters dos veces y el
  // toggle se cancelaba solo.
  const [orden, setOrden] = useState<{ campo: CampoOrden; ascendente: boolean }>({
    campo: 'nombre',
    ascendente: true,
  });

  const [modal, setModal] = useState<{ socio: SocioListado | null } | null>(null);
  // Estado propio y no un tercer valor dentro de `modal`: el historial médico
  // no comparte nada con el formulario de alta/edición —ni datos ni permiso—
  // y meterlos en el mismo estado obligaría a discriminar el tipo en cada uso.
  const [historial, setHistorial] = useState<SocioListado | null>(null);
  const [entrenadores, setEntrenadores] = useState<SocioListado | null>(null);
  const [telefonos, setTelefonos] = useState<SocioListado | null>(null);
  const [emergencia, setEmergencia] = useState<SocioListado | null>(null);
  const [baja, setBaja] = useState<SocioListado | null>(null);

  useEffect(() => {
    let cancelado = false;
    setSocios(null);
    setError(null);
    listarSocios()
      .then((lista) => {
        if (!cancelado) setSocios(lista);
      })
      .catch((err: unknown) => {
        if (!cancelado) setError(mensajeDeError(err));
      });
    return () => {
      cancelado = true;
    };
  }, [intento]);

  const recargar = useCallback(() => setIntento((n) => n + 1), []);

  // Click en la misma columna: invierte el sentido. Click en otra: pasa a
  // esa columna, siempre arrancando ascendente.
  const alternarOrden = useCallback((campo: CampoOrden) => {
    setOrden((actual) =>
      actual.campo === campo
        ? { campo, ascendente: !actual.ascendente }
        : { campo, ascendente: true },
    );
  }, []);

  const sociosVisibles = useMemo(() => {
    if (!socios) return [];

    const texto = busqueda.trim().toLowerCase();
    const filtrados = socios.filter((s) => {
      const coincideTexto =
        texto === '' ||
        s.nombreCompleto.toLowerCase().includes(texto) ||
        s.plan.toLowerCase().includes(texto);
      return coincideTexto && coincideFiltro(s.estado, filtro);
    });

    const signo = orden.ascendente ? 1 : -1;
    return filtrados.sort((a, b) => {
      if (orden.campo === 'nombre') return signo * a.nombreCompleto.localeCompare(b.nombreCompleto);
      if (orden.campo === 'estado') return signo * (PRIORIDAD_ESTADO[a.estado] - PRIORIDAD_ESTADO[b.estado]);
      // 'vencimiento': sin fecha va siempre al final, sea cual sea el sentido.
      if (!a.vencimiento && !b.vencimiento) return 0;
      if (!a.vencimiento) return 1;
      if (!b.vencimiento) return -1;
      return signo * a.vencimiento.localeCompare(b.vencimiento);
    });
  }, [socios, busqueda, filtro, orden]);

  const actualizarEnLista = useCallback((actualizado: SocioListado) => {
    setSocios((lista) =>
      lista
        ? lista.some((s) => s.idSocio === actualizado.idSocio)
          ? lista.map((s) => (s.idSocio === actualizado.idSocio ? actualizado : s))
          : [...lista, actualizado]
        : lista,
    );
  }, []);

  // La baja pasa por BajaSocioModal y no por el confirmDialog genérico: con la
  // cuota paga hay que elegir CUÁNDO (al vencer, o ahora perdiendo los días).
  const confirmarBaja = useCallback(
    (socio: SocioListado, inmediata: boolean) => {
      setBaja(null);
      darDeBajaSocio(socio.idSocio, { inmediata })
        .then((actualizado) => {
          // Forma impersonal: el participio en masculino fijo le erraba
          // al género de la mitad de los socios (mismo criterio que
          // PersonalView).
          showSnack(
            actualizado.bajaProgramada
              ? `La baja de ${socio.nombreCompleto} queda para el ${formatearFecha(parsearFecha(actualizado.bajaProgramada))}`
              : `Se dio de baja a ${socio.nombreCompleto}`,
            colors.statusOk,
          );
          recargar();
        })
        .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
    },
    [showSnack, recargar],
  );

  // Anular una baja programada tampoco pide confirmación: no borra nada que
  // haya ocurrido, y siempre se puede volver a programar.
  const anularBaja = useCallback(
    (socio: SocioListado) => {
      anularBajaSocio(socio.idSocio)
        .then(() => {
          showSnack(`Se anuló la baja de ${socio.nombreCompleto}`, colors.statusOk);
          recargar();
        })
        .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
    },
    [showSnack, recargar],
  );

  // Sin diálogo de confirmación: reactivar es una acción de bajo riesgo y
  // reversible (siempre se puede volver a dar de baja), a diferencia de la baja.
  const activar = useCallback(
    (socio: SocioListado) => {
      reactivarSocio(socio.idSocio)
        .then(() => {
          showSnack(`Se reactivó a ${socio.nombreCompleto}`, colors.statusOk);
          recargar();
        })
        .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
    },
    [showSnack, recargar],
  );

  return (
    <div>
      <Topbar
        title="Socios"
        subtitle={socios ? `${socios.length} socios registrados` : undefined}
        actions={
          puedeAltaBaja ? (
            <PrimaryButton label="Nuevo Socio" icon={UserPlus} onClick={() => setModal({ socio: null })} />
          ) : undefined
        }
      />

      <div className="space-y-4 p-8">
        {error && (
          <SectionCard>
            <p className="mb-4 font-body text-sm text-status-danger">{error}</p>
            <PrimaryButton label="Reintentar" onClick={recargar} />
          </SectionCard>
        )}

        {!error && !socios && (
          <div className="space-y-4">
            <Skeleton className="h-10 w-full max-w-sm" />
            <Skeleton className="h-96" />
          </div>
        )}

        {!error && socios && (
          <>
            {/* Barra de búsqueda + chips de filtro (estructura_socios.md). */}
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="relative w-full sm:w-72">
                <Search size={16} className="absolute top-1/2 left-3 -translate-y-1/2 text-text-muted" />
                <input
                  type="text"
                  value={busqueda}
                  onChange={(e) => setBusqueda(e.target.value)}
                  placeholder="Buscar por nombre o plan…"
                  className="w-full rounded-md border border-border-idle bg-surface-card py-2 pr-3 pl-9 font-body text-sm text-text-main outline-none placeholder:text-text-muted focus:border-border-active"
                />
              </div>
              <div className="flex gap-2">
                {FILTROS.map((f) => (
                  <FilterChip key={f} label={f} activo={filtro === f} onClick={() => setFiltro(f)} />
                ))}
              </div>
            </div>

            <SectionCard padding="p-0">
              {sociosVisibles.length === 0 ? (
                <p className="p-5 font-body text-sm text-text-muted">
                  {socios.length === 0
                    ? 'Todavía no hay socios cargados.'
                    : 'Ningún socio coincide con la búsqueda o el filtro.'}
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-border-idle">
                        <th className="py-3 pl-5 text-left">
                          <SortableHeader
                            label="Nombre"
                            campo="nombre"
                            ordenActual={orden.campo}
                            ascendente={orden.ascendente}
                            onClick={alternarOrden}
                          />
                        </th>
                        <th className="py-3 text-left font-body text-xs font-semibold tracking-wide text-text-secondary uppercase">
                          Plan
                        </th>
                        <th className="py-3 text-left">
                          <SortableHeader
                            label="Estado"
                            campo="estado"
                            ordenActual={orden.campo}
                            ascendente={orden.ascendente}
                            onClick={alternarOrden}
                          />
                        </th>
                        <th className="py-3 text-left">
                          <SortableHeader
                            label="Vence"
                            campo="vencimiento"
                            ordenActual={orden.campo}
                            ascendente={orden.ascendente}
                            onClick={alternarOrden}
                          />
                        </th>
                        <th className="py-3 pr-5 text-right font-body text-xs font-semibold tracking-wide text-text-secondary uppercase">
                          Acciones
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {sociosVisibles.map((socio) => (
                        <SocioTableRow
                          key={socio.idSocio}
                          socio={socio}
                          puedeEditar={puedeEditar}
                          puedeAltaBaja={puedeAltaBaja}
                          puedeVerHistorialMedico={puedeVerHistorialMedico}
                          onEditar={() => setModal({ socio })}
                          onEntrenadores={() => setEntrenadores(socio)}
                          onTelefonos={() => setTelefonos(socio)}
                          onEmergencia={() => setEmergencia(socio)}
                          onDarDeBaja={() => setBaja(socio)}
                          onActivar={() => activar(socio)}
                          onAnularBaja={() => anularBaja(socio)}
                          onHistorialMedico={() => setHistorial(socio)}
                        />
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </SectionCard>
          </>
        )}
      </div>

      {modal && (
        <SocioFormModal
          socio={modal.socio}
          onClose={() => setModal(null)}
          onGuardado={actualizarEnLista}
        />
      )}

      {/* No recarga la grilla al cerrar: las patologías no son una columna de
          la tabla, así que nada de lo que se toca acá adentro cambia lo que se
          está viendo detrás. */}
      {historial && (
        <PatologiasModal socio={historial} onClose={() => setHistorial(null)} />
      )}

      {/* Recarga la grilla, igual que el de teléfonos: el contacto de
          emergencia que muestra la ficha es el PRINCIPAL, así que agregar
          uno, borrarlo o cambiar cuál es el principal cambia lo que el
          formulario de edición va a mostrar la próxima vez que se abra. Sin
          recargar, editar al socio después reenviaría el contacto viejo. */}
      {emergencia && (
        <EmergenciaModal
          socio={emergencia}
          puedeGestionar={puedeAltaBaja}
          onClose={() => setEmergencia(null)}
          onCambio={recargar}
        />
      )}

      {baja && (
        <BajaSocioModal
          socio={baja}
          onClose={() => setBaja(null)}
          onConfirmar={(inmediata) => confirmarBaja(baja, inmediata)}
        />
      )}

      {telefonos && (
        <TelefonosModal
          socio={telefonos}
          puedeGestionar={puedeAltaBaja}
          onClose={() => setTelefonos(null)}
          onCambio={recargar}
        />
      )}

      {/* Tampoco recarga la grilla: el entrenador a cargo no es una columna
          de la tabla. */}
      {entrenadores && (
        <EntrenadoresModal
          socio={entrenadores}
          puedeGestionar={puedeAsignarEntrenadores}
          onClose={() => setEntrenadores(null)}
        />
      )}
    </div>
  );
}
