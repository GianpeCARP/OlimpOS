import { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertTriangle, Search, Wallet } from 'lucide-react';
import { PrimaryButton, SectionCard, SelectField, StatusBadge, Topbar, type SelectOption } from '../../components/ui';
import { colors, EstadoPago } from '../../config';
import { mensajeDeError } from '../../services/api';
import {
  getActividades,
  getMisInscripciones,
  getPlanesDeActividad,
  comprarPlan,
  membresiaCubreNuevoPlan,
  type ActividadListada,
  type InscripcionListada,
  type PlanActividadListado,
} from '../../services/actividadService';
import { cobrar, pagarDeuda } from '../../services/cobrosService';
import { obtenerCuotaDeSocio } from '../../services/cobrosService';
import type { MiCuota } from '../../services/socioService';
import { listarSocios, listarTiposMembresia, type SocioListado } from '../../services/sociosService';
import type { Pago, TipoMembresia } from '../../types';
import { useAuthStore } from '../../store/authStore';
import { useUiStore } from '../../store/uiStore';
import { formatearFecha, formatearFechaConAnio, formatearMoneda } from '../../utils/format';
import { parsearFecha } from '../../utils/fechas';
import { CobroActividadCard } from './CobroActividadCard';
import { CobroClaseSueltaModal } from './CobroClaseSueltaModal';

// Cobros (Recepción): buscar un socio, ver su cuenta, cobrarle. Reutiliza
// TODO lo ya construido en vez de duplicarlo — getMiCuota (socioService)
// para el estado de cuenta, y comprarPlan/comprarClaseSuelta
// (actividadService, con sus REGLAS 1/7/8 intactas) para los cobros de
// actividades. Lo único nuevo de verdad es cobrarMembresia/pagarDeuda
// (cobrosService.ts), que hasta ahora no existían en ningún lado.
//
// Un solo selector de "Método de pago" arriba de todo, compartido por
// cualquier acción que se dispare desde acá — a diferencia de Mis
// Actividades (donde el socio paga UNA cosa a la vez), acá recepción puede
// cobrar varias cosas seguidas en la misma visita del socio, casi siempre
// con el mismo medio.

const OPCIONES_METODO: SelectOption[] = [
  { value: 'EFECTIVO', label: 'Efectivo' },
  { value: 'DEBITO', label: 'Débito' },
  { value: 'CREDITO', label: 'Crédito' },
  { value: 'TRANSFERENCIA', label: 'Transferencia' },
  { value: 'BILLETERA_VIRTUAL', label: 'Billetera virtual' },
];

const MAX_RESULTADOS_BUSQUEDA = 6;

function Skeleton({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-md bg-surface-hover ${className}`} />;
}

interface DatosActividades {
  actividades: ActividadListada[];
  planesPorActividad: Map<number, PlanActividadListado[]>;
}

export function CobrosView() {
  const idUsuarioActor = useAuthStore((s) => s.usuario?.id_usuario);
  const showSnack = useUiStore((s) => s.showSnack);
  const confirmDialog = useUiStore((s) => s.confirmDialog);

  const [socios, setSocios] = useState<SocioListado[] | null>(null);
  const [tiposMembresia, setTiposMembresia] = useState<TipoMembresia[] | null>(null);
  const [datosActividades, setDatosActividades] = useState<DatosActividades | null>(null);
  const [errorInicial, setErrorInicial] = useState<string | null>(null);

  const [busqueda, setBusqueda] = useState('');
  const [socioSeleccionado, setSocioSeleccionado] = useState<SocioListado | null>(null);

  const [cuenta, setCuenta] = useState<MiCuota | null>(null);
  const [inscripcionesActivas, setInscripcionesActivas] = useState<InscripcionListada[]>([]);
  const [cargandoCuenta, setCargandoCuenta] = useState(false);

  const [metodo, setMetodo] = useState<Pago['metodo']>('EFECTIVO');
  const [idTipoElegido, setIdTipoElegido] = useState('');
  const [claseSueltaDe, setClaseSueltaDe] = useState<ActividadListada | null>(null);
  const [ocupado, setOcupado] = useState(false);

  useEffect(() => {
    Promise.all([listarSocios(), listarTiposMembresia(), getActividades()])
      .then(async ([listaSocios, tipos, actividades]) => {
        const listasDePlanes = await Promise.all(
          actividades.map((a) => getPlanesDeActividad(a.idActividad)),
        );
        const planesPorActividad = new Map<number, PlanActividadListado[]>();
        actividades.forEach((a, i) => planesPorActividad.set(a.idActividad, listasDePlanes[i]));

        setSocios(listaSocios);
        setTiposMembresia(tipos);
        setDatosActividades({ actividades, planesPorActividad });
        if (tipos.length > 0) setIdTipoElegido(String(tipos[0].id_tipo_membresia));
      })
      .catch((err: unknown) => setErrorInicial(mensajeDeError(err)));
  }, []);

  const cargarCuenta = useCallback((idSocio: number) => {
    setCargandoCuenta(true);
    Promise.all([obtenerCuotaDeSocio(idSocio), getMisInscripciones(idSocio)])
      .then(([miCuota, inscripciones]) => {
        setCuenta(miCuota);
        setInscripcionesActivas(inscripciones.filter((i) => i.estado === 'ACTIVA'));
      })
      .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger))
      .finally(() => setCargandoCuenta(false));
  }, [showSnack]);

  const seleccionarSocio = useCallback(
    (socio: SocioListado) => {
      setSocioSeleccionado(socio);
      setBusqueda('');
      cargarCuenta(socio.idSocio);
      // "Plan a cobrar" arranca en el tipo que el socio YA tiene — además
      // de ser lo más práctico para una renovación simple, es el que usa
      // el combo cuando hay que renovar para cubrir un plan de actividad:
      // sin esto, el combo terminaría cobrando el tipo que hubiera quedado
      // seleccionado de una visita anterior.
      //
      // Se verifica que siga estando en la lista: un tipo dado de baja no
      // lo devuelve listarTiposMembresia, y seleccionarlo igual dejaba el
      // <select> mostrando un value inexistente y `tipoElegido` undefined.
      const vigente = tiposMembresia?.find((t) => t.id_tipo_membresia === socio.idTipoMembresia);
      const porDefecto = vigente ?? tiposMembresia?.[0];
      if (porDefecto) setIdTipoElegido(String(porDefecto.id_tipo_membresia));
    },
    [cargarCuenta, tiposMembresia],
  );

  const cambiarSocio = useCallback(() => {
    setSocioSeleccionado(null);
    setCuenta(null);
    setInscripcionesActivas([]);
  }, []);

  const resultadosBusqueda = useMemo(() => {
    const texto = busqueda.trim().toLowerCase();
    if (!texto || !socios) return [];
    return socios
      .filter((s) => s.activo && (s.nombreCompleto.toLowerCase().includes(texto) || s.dni.includes(texto)))
      .slice(0, MAX_RESULTADOS_BUSQUEDA);
  }, [busqueda, socios]);

  const tipoElegido = tiposMembresia?.find((t) => String(t.id_tipo_membresia) === idTipoElegido);

  const cobrarMembresiaClick = () => {
    if (!socioSeleccionado || !tipoElegido) return;
    const yaTiene = cuenta?.tieneMembresia;
    confirmDialog(
      `¿Cobrar "${tipoElegido.nombre}"?`,
      `Se cobran ${formatearMoneda(tipoElegido.precio_actual)} en ${OPCIONES_METODO.find((o) => o.value === metodo)?.label}.${
        yaTiene ? ' Se suma a partir del vencimiento actual, sin perder los días ya pagados.' : ''
      }`,
      () => {
        setOcupado(true);
        cobrar(socioSeleccionado.idSocio, tipoElegido.id_tipo_membresia, metodo)
          .then((resultado) => {
            showSnack(
              `Cobrado: ${resultado.membresia.plan} hasta el ${formatearFecha(parsearFecha(resultado.membresia.vencimiento))}`,
              colors.statusOk,
            );
            cargarCuenta(socioSeleccionado.idSocio);
          })
          .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger))
          .finally(() => setOcupado(false));
      },
    );
  };

  const cobrarDeudaClick = (deuda: NonNullable<MiCuota['deudas']>[number]) => {
    if (!socioSeleccionado) return;
    confirmDialog(
      `¿Cobrar deuda de ${formatearMoneda(deuda.monto)}?`,
      `Se registra como pagada en ${OPCIONES_METODO.find((o) => o.value === metodo)?.label}.`,
      () => {
        setOcupado(true);
        pagarDeuda(deuda.idDeuda, metodo)
          .then(() => {
            showSnack(`Deuda de ${formatearMoneda(deuda.monto)} cobrada`, colors.statusOk);
            cargarCuenta(socioSeleccionado.idSocio);
          })
          .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger))
          .finally(() => setOcupado(false));
      },
    );
  };

  const metodoLabel = () => OPCIONES_METODO.find((o) => o.value === metodo)?.label;

  const cobrarSoloPlan = (plan: PlanActividadListado, planViejo?: InscripcionListada) => {
    if (!socioSeleccionado) return;
    confirmDialog(
      `¿Cobrar "${plan.nombre}"?`,
      planViejo
        ? `Se cobran ${formatearMoneda(plan.precio)} en ${metodoLabel()}. El plan actual (${planViejo.nombrePlan}) se reemplaza sin devolución.`
        : `Se cobran ${formatearMoneda(plan.precio)} en ${metodoLabel()}.`,
      () => {
        setOcupado(true);
        comprarPlan(socioSeleccionado.idSocio, plan.idPlanActividad, idUsuarioActor, metodo)
          .then(() => {
            showSnack(`Cobrado: ${plan.nombre}`, colors.statusOk);
            cargarCuenta(socioSeleccionado.idSocio);
          })
          .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger))
          .finally(() => setOcupado(false));
      },
    );
  };

  /**
   * Combo "renovar + cobrar": cuando la membresía actual no llega a cubrir
   * el mes completo del plan (REGLA 1), en vez de dejar que el socio se
   * entere recién con el rechazo, se le ofrece resolver las dos cosas en
   * una sola confirmación — situación que en un gimnasio real pasa todo el
   * tiempo (la membresía vence a mitad de mes). Usa el MISMO tipo de
   * membresía que el socio ya tenía (precargado en seleccionarSocio), así
   * es un solo click y no un formulario más para completar.
   */
  const cobrarComboMembresiaYPlan = (plan: PlanActividadListado, tipo: TipoMembresia, planViejo?: InscripcionListada) => {
    if (!socioSeleccionado) return;
    const total = tipo.precio_actual + plan.precio;
    confirmDialog(
      `¿Renovar membresía y cobrar "${plan.nombre}"?`,
      `Su membresía actual no llega a cubrir todo el mes de este plan, así que se renueva junto con el plan y queda cubriéndolo entero. Se cobran ${formatearMoneda(tipo.precio_actual)} de ${tipo.nombre} + ${formatearMoneda(plan.precio)} de ${plan.nombre} = ${formatearMoneda(total)} en ${metodoLabel()}.` +
        (planViejo ? ` El plan actual (${planViejo.nombrePlan}) se reemplaza sin devolución.` : ''),
      () => {
        setOcupado(true);
        // Una sola llamada al service: valida todo lo que puede rebotar
        // ANTES de cobrar la membresía, y garantiza que la renovación
        // alcance a cubrir el plan. Encadenar las dos llamadas desde acá
        // cobraba la membresía y después dejaba el plan afuera.
        // Una sola llamada: el backend crea membresía + abono en la misma
        // transacción. Inscripcion_Actividad.id_membresia es NOT NULL, así
        // que encadenar dos pedidos dejaría al plan sin membresía si el
        // segundo falla.
        cobrar(socioSeleccionado.idSocio, tipo.id_tipo_membresia, metodo, {
          idPlanActividad: plan.idPlanActividad,
        })
          .then((resultado) => {
            showSnack(
              `Cobrado: ${tipo.nombre} hasta el ${formatearFecha(parsearFecha(resultado.membresia.vencimiento))} + ${plan.nombre}`,
              colors.statusOk,
            );
            cargarCuenta(socioSeleccionado.idSocio);
          })
          .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger))
          .finally(() => setOcupado(false));
      },
    );
  };

  const cobrarPlanClick = (actividad: ActividadListada, plan: PlanActividadListado) => {
    if (!socioSeleccionado) return;
    const planViejo = inscripcionesActivas.find((i) => i.idActividad === actividad.idActividad);

    membresiaCubreNuevoPlan(socioSeleccionado.idSocio)
      .then((cubre) => {
        if (!cubre && tipoElegido) {
          cobrarComboMembresiaYPlan(plan, tipoElegido, planViejo);
        } else {
          cobrarSoloPlan(plan, planViejo);
        }
      })
      .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
  };

  return (
    <div>
      <Topbar title="Cobros" subtitle={socioSeleccionado ? socioSeleccionado.nombreCompleto : undefined} />

      <div className="space-y-4 p-8">
        {errorInicial && (
          <SectionCard>
            <p className="font-body text-sm text-status-danger">{errorInicial}</p>
          </SectionCard>
        )}

        {!errorInicial && !socios && (
          <div className="space-y-4">
            <Skeleton className="h-16" />
          </div>
        )}

        {!errorInicial && socios && !socioSeleccionado && (
          <SectionCard title="Buscar socio">
            <div className="flex items-center gap-2 rounded-md border border-border-idle bg-surface-card px-3 py-2 focus-within:border-border-active">
              <Search size={16} className="text-text-muted" />
              <input
                value={busqueda}
                onChange={(e) => setBusqueda(e.target.value)}
                placeholder="Buscar por nombre o DNI…"
                className="w-full bg-transparent text-text-main outline-none placeholder:text-text-muted"
              />
            </div>

            {busqueda.trim() && (
              <div className="mt-3 flex flex-col divide-y divide-border-idle">
                {resultadosBusqueda.length === 0 ? (
                  <p className="py-2 font-body text-sm text-text-muted">Ningún socio activo coincide.</p>
                ) : (
                  resultadosBusqueda.map((socio) => (
                    <button
                      key={socio.idSocio}
                      type="button"
                      onClick={() => seleccionarSocio(socio)}
                      className="flex items-center justify-between gap-3 py-2.5 text-left hover:opacity-80"
                    >
                      <div className="min-w-0">
                        <p className="font-body text-sm text-text-main">{socio.nombreCompleto}</p>
                        <p className="font-body text-xs text-text-muted">
                          DNI {socio.dni} · {socio.plan}
                        </p>
                      </div>
                      <StatusBadge status={socio.estado} />
                    </button>
                  ))
                )}
              </div>
            )}
          </SectionCard>
        )}

        {socioSeleccionado && (
          <>
            <SectionCard>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-heading text-lg font-semibold text-text-main">
                    {socioSeleccionado.nombreCompleto}
                  </p>
                  <p className="font-body text-sm text-text-secondary">
                    DNI {socioSeleccionado.dni} · {socioSeleccionado.plan}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <StatusBadge status={socioSeleccionado.estado} />
                  <button
                    type="button"
                    onClick={cambiarSocio}
                    className="font-body text-xs text-text-muted hover:text-text-main"
                  >
                    Cambiar socio
                  </button>
                </div>
              </div>

              <div className="mt-4 max-w-xs">
                <SelectField
                  label="Método de pago"
                  value={metodo}
                  onChange={(v) => setMetodo(v as Pago['metodo'])}
                  options={OPCIONES_METODO}
                  icon={Wallet}
                />
              </div>
            </SectionCard>

            {cargandoCuenta && !cuenta && (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <Skeleton className="h-32" />
                <Skeleton className="h-32" />
              </div>
            )}

            {cuenta && (
              <>
                {cuenta.totalAdeudado > 0 && (
                  <SectionCard title="Deudas pendientes">
                    <div className="mb-3 flex items-start gap-2 rounded-md bg-status-danger/10 px-3 py-2">
                      <AlertTriangle size={16} className="mt-0.5 shrink-0 text-status-danger" />
                      <p className="font-body text-sm text-status-danger">
                        Debe regularizar la deuda antes de poder comprar planes o clases sueltas.
                      </p>
                    </div>
                    <div className="flex flex-col divide-y divide-border-idle">
                      {cuenta.deudas.map((deuda) => (
                        <div key={deuda.idDeuda} className="flex items-center justify-between gap-3 py-2.5">
                          <div className="min-w-0">
                            <p className="font-body text-sm text-text-main">{formatearMoneda(deuda.monto)}</p>
                            <p className="font-body text-xs text-text-muted">
                              Generada el {formatearFechaConAnio(parsearFecha(deuda.fechaGeneracion))}
                              {deuda.diasDeAtraso > 0 && ` · ${deuda.diasDeAtraso} días de atraso`}
                              {deuda.observaciones && ` · ${deuda.observaciones}`}
                            </p>
                          </div>
                          <PrimaryButton
                            label="Cobrar"
                            onClick={() => cobrarDeudaClick(deuda)}
                            disabled={ocupado}
                          />
                        </div>
                      ))}
                    </div>
                  </SectionCard>
                )}

                <SectionCard title="Membresía">
                  <p className="font-body text-sm text-text-secondary">
                    {cuenta.tieneMembresia
                      ? `Plan actual: ${cuenta.plan}${
                          cuenta.vencimiento
                            ? ` · vence el ${formatearFechaConAnio(parsearFecha(cuenta.vencimiento))}`
                            : ' · no vence'
                        }`
                      : 'Todavía no tiene ninguna membresía.'}
                  </p>

                  {tiposMembresia && tiposMembresia.length > 0 && (
                    <div className="mt-3 flex flex-wrap items-end gap-3">
                      <div className="w-56">
                        <SelectField
                          label="Plan a cobrar"
                          value={idTipoElegido}
                          onChange={setIdTipoElegido}
                          options={tiposMembresia.map((t) => ({
                            value: String(t.id_tipo_membresia),
                            label: `${t.nombre} — ${formatearMoneda(t.precio_actual)}`,
                          }))}
                        />
                      </div>
                      <PrimaryButton
                        label={cuenta.tieneMembresia ? 'Cobrar renovación' : 'Cobrar membresía'}
                        onClick={cobrarMembresiaClick}
                        disabled={ocupado || !tipoElegido}
                      />
                    </div>
                  )}
                </SectionCard>

                <div>
                  <h2 className="mb-3 font-heading text-lg font-semibold text-text-main">Actividades</h2>
                  {!datosActividades || datosActividades.actividades.length === 0 ? (
                    <SectionCard>
                      <p className="font-body text-sm text-text-muted">Todavía no hay actividades cargadas.</p>
                    </SectionCard>
                  ) : (
                    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                      {datosActividades.actividades.map((actividad) => (
                        <CobroActividadCard
                          key={actividad.idActividad}
                          actividad={actividad}
                          planes={datosActividades.planesPorActividad.get(actividad.idActividad) ?? []}
                          inscripcionActivaDeEstaActividad={inscripcionesActivas.find(
                            (i) => i.idActividad === actividad.idActividad,
                          )}
                          onCobrarPlan={(plan) => cobrarPlanClick(actividad, plan)}
                          onCobrarClaseSuelta={() => setClaseSueltaDe(actividad)}
                        />
                      ))}
                    </div>
                  )}
                </div>

                <SectionCard title="Historial de pagos">
                  {cuenta.pagos.length === 0 ? (
                    <p className="font-body text-sm text-text-muted">Todavía no tiene pagos registrados.</p>
                  ) : (
                    <div className="flex flex-col divide-y divide-border-idle">
                      {cuenta.pagos.map((pago) => (
                        <div key={pago.idPago} className="flex items-center justify-between gap-3 py-2.5">
                          <div className="min-w-0">
                            <p className="font-body text-sm text-text-main">{formatearMoneda(pago.monto)}</p>
                            <p className="font-body text-xs text-text-muted">
                              {formatearFechaConAnio(parsearFecha(pago.fecha))} · {pago.metodo}
                              {pago.numeroComprobante && ` · Comp. ${pago.numeroComprobante}`}
                            </p>
                          </div>
                          <StatusBadge status={EstadoPago[pago.estado as keyof typeof EstadoPago] ?? pago.estado} />
                        </div>
                      ))}
                    </div>
                  )}
                </SectionCard>
              </>
            )}
          </>
        )}
      </div>

      {claseSueltaDe && socioSeleccionado && (
        <CobroClaseSueltaModal
          idSocio={socioSeleccionado.idSocio}
          nombreSocio={socioSeleccionado.nombreCompleto}
          actividad={claseSueltaDe}
          metodo={metodo}
          idUsuarioActor={idUsuarioActor}
          onClose={() => setClaseSueltaDe(null)}
          onCobrado={() => {
            showSnack(`Clase suelta de ${claseSueltaDe.nombre} cobrada`, colors.statusOk);
            cargarCuenta(socioSeleccionado.idSocio);
          }}
        />
      )}
    </div>
  );
}
