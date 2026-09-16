import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router';
import { Search, Tag, Wallet } from 'lucide-react';
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
import { cobrar } from '../../services/cobrosService';
import {
  listarPromociones,
  vistaPreviaDescuento,
  type Promocion,
  type VistaPrevia,
} from '../../services/promocionesService';
import { obtenerCuotaDeSocio } from '../../services/cobrosService';
import type { MiCuota } from '../../services/socioService';
import { listarSocios, listarTiposMembresia, type SocioListado } from '../../services/sociosService';
import type { Pago, TipoMembresia } from '../../types';
import { useAuthStore } from '../../store/authStore';
import { useUiStore } from '../../store/uiStore';
import { usePuedeAccion } from '../../hooks/usePermisos';
import { formatearFecha, formatearFechaConAnio, formatearMoneda } from '../../utils/format';
import { parsearFecha } from '../../utils/fechas';
import { CobroActividadCard } from './CobroActividadCard';
import { PromocionesPanel } from './PromocionesPanel';
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
  // La accion mas restringida de la matriz: la tiene el Dueno y nadie mas.
  // El Recepcionista SI ve el selector de promociones al cobrar —lo necesita—
  // pero no este panel, que es donde se inventan.
  const puedeGestionarPromociones = usePuedeAccion('gestionPromociones');
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

  // Socio preseleccionado por URL (?socio=<id>). Lo usa el alta de socio con
  // "Cobrar ahora": el socio recién cargado no tiene membresía y lo lógico es
  // cobrársela en el mismo momento, sin tener que volver a buscarlo.
  //
  // Va DESPUÉS de seleccionarSocio a propósito: el array de dependencias se
  // evalúa durante el render, y leer una const declarada más abajo revienta
  // con un ReferenceError que tsc no ve (ver CLAUDE.md, trampa de TDZ).
  //
  // Espera a que estén los socios Y los tipos de membresía: seleccionarSocio
  // usa los tipos para elegir el plan por defecto. Después limpia el parámetro
  // para que volver a entrar a Cobros no reabra siempre al mismo socio.
  const [parametros, setParametros] = useSearchParams();
  const idSocioPreseleccionado = parametros.get('socio');
  useEffect(() => {
    if (!idSocioPreseleccionado || !socios || !tiposMembresia) return;
    const encontrado = socios.find((s) => String(s.idSocio) === idSocioPreseleccionado);
    if (encontrado) {
      seleccionarSocio(encontrado);
    } else {
      showSnack('No se encontró el socio a cobrar. Buscalo en la lista.', colors.statusWarn);
    }
    setParametros({}, { replace: true });
  }, [idSocioPreseleccionado, socios, tiposMembresia, seleccionarSocio, setParametros, showSnack]);

  // Promociones VIGENTES nada más: el mostrador no tiene por qué poder elegir
  // una de enero en marzo. El backend igual la rechazaría, pero ofrecerla y
  // después negarla sería hacerle perder el tiempo a quien cobra.
  const [promociones, setPromociones] = useState<Promocion[]>([]);
  const [idPromocionElegida, setIdPromocionElegida] = useState('');
  // Lo que saldría cobrar, calculado POR EL BACKEND. No se multiplica acá: la
  // fórmula (con su piso en cero y su redondeo) vive en un solo lugar, y así
  // el número que se ve antes de cobrar es el mismo que se va a registrar.
  const [previa, setPrevia] = useState<VistaPrevia | null>(null);

  useEffect(() => {
    let cancelado = false;
    listarPromociones(true)
      .then((lista) => {
        if (!cancelado) setPromociones(lista);
      })
      // Sin snack: quedarse sin promociones no impide cobrar a precio de
      // lista, que es el caso normal. Un cartel de error acá alarmaría por
      // algo que no bloquea nada.
      .catch(() => undefined);
    return () => {
      cancelado = true;
    };
  }, []);

  const resultadosBusqueda = useMemo(() => {
    const texto = busqueda.trim().toLowerCase();
    if (!texto || !socios) return [];
    return socios
      .filter((s) => s.activo && (s.nombreCompleto.toLowerCase().includes(texto) || s.dni.includes(texto)))
      .slice(0, MAX_RESULTADOS_BUSQUEDA);
  }, [busqueda, socios]);

  const tipoElegido = tiposMembresia?.find((t) => String(t.id_tipo_membresia) === idTipoElegido);

  // Va DESPUES de `tipoElegido` y no junto al resto de los efectos: el array
  // de dependencias se evalua durante el render, asi que ponerlo arriba lo
  // leeria antes de su `const` y tiraria un ReferenceError por TDZ. No lo
  // detecta tsc — la referencia es valida para el compilador, el problema es
  // el orden en tiempo de ejecucion.
  useEffect(() => {
    if (idPromocionElegida === '' || !tipoElegido) {
      setPrevia(null);
      return;
    }
    let cancelado = false;
    vistaPreviaDescuento(Number(idPromocionElegida), tipoElegido.id_tipo_membresia)
      .then((v) => {
        if (!cancelado) setPrevia(v);
      })
      .catch(() => {
        if (!cancelado) setPrevia(null);
      });
    return () => {
      cancelado = true;
    };
  }, [idPromocionElegida, tipoElegido]);


  const cobrarMembresiaClick = () => {
    if (!socioSeleccionado || !tipoElegido) return;
    // El monto del diálogo sale de la vista previa cuando hay promo: mostrar
    // el precio de lista y después cobrar otro sería pedir una confirmación
    // sobre una cifra que no es la que se va a registrar.
    const aCobrar = previa ? previa.precioFinal : tipoElegido.precio_actual;
    const detallePromo = previa
      ? ` Incluye "${previa.promocion}": ${formatearMoneda(previa.descuento)} de descuento sobre ${formatearMoneda(previa.precioLista)}.`
      : '';
    confirmDialog(
      `¿Cobrar "${tipoElegido.nombre}"?`,
      `Se cobran ${formatearMoneda(aCobrar)} en ${OPCIONES_METODO.find((o) => o.value === metodo)?.label}.${detallePromo} El período arranca hoy.`,
      () => {
        setOcupado(true);
        cobrar(socioSeleccionado.idSocio, tipoElegido.id_tipo_membresia, metodo, {
          idPromocion: idPromocionElegida === '' ? undefined : Number(idPromocionElegida),
        })
          .then((resultado) => {
            showSnack(
              `Cobrado: ${resultado.membresia.plan} hasta el ${formatearFecha(parsearFecha(resultado.membresia.vencimiento))}` +
                (resultado.descuento
                  ? ` — ${formatearMoneda(resultado.descuento)} de descuento por "${resultado.promocion}"`
                  : ''),
              colors.statusOk,
            );
            // La promo se limpia después de cobrar: dejarla puesta haría que
            // el siguiente socio que atienda el mostrador se lleve el
            // descuento sin que nadie lo haya decidido.
            setIdPromocionElegida('');
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
      `¿Cobrar membresía y "${plan.nombre}"?`,
      `No tiene la cuota vigente, así que se cobra junto con el plan y los dos arrancan hoy. Se cobran ${formatearMoneda(tipo.precio_actual)} de ${tipo.nombre} + ${formatearMoneda(plan.precio)} de ${plan.nombre} = ${formatearMoneda(total)} en ${metodoLabel()}.` +
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
        if (cubre) {
          cobrarSoloPlan(plan, planViejo);
        } else if (cuenta?.puedeRenovar && tipoElegido) {
          // Sin cuota vigente se cobran las dos cosas juntas, empezando hoy.
          cobrarComboMembresiaYPlan(plan, tipoElegido, planViejo);
        } else {
          // Con cuota vigente que no cubre el mes del abono ya no hay combo:
          // sería renovar por adelantado. El abono se cobra con la próxima
          // cuota, cuando venza.
          showSnack(
            `La cuota no cubre el mes entero de "${plan.nombre}". Cobralo junto con la próxima cuota` +
              (cuenta?.renovableDesde
                ? `, desde el ${formatearFechaConAnio(parsearFecha(cuenta.renovableDesde))}.`
                : ', cuando venza.'),
            colors.statusWarn,
          );
        }
      })
      .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
  };

  return (
    <div>
      <Topbar title="Cobros" subtitle={socioSeleccionado ? socioSeleccionado.nombreCompleto : undefined} />

      <div className="space-y-4 p-8">
        {/* Fuera del flujo del socio a proposito: administrar descuentos no
            depende de tener a nadie seleccionado. Arranca plegado para no
            empujar el buscador hacia abajo. */}
        {puedeGestionarPromociones && <PromocionesPanel />}

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

                  {/* Sin adelantos: con la cuota vigente o en pausa no se ofrece
                      cobrar otra, se dice desde cuándo (el motivo lo redacta el
                      backend, que es quien aplica la regla). */}
                  {!cuenta.puedeRenovar && (
                    <p className="mt-3 rounded-md border border-border-idle bg-surface-hover px-3 py-2 font-body text-sm text-text-secondary">
                      {cuenta.motivoNoRenovar}
                    </p>
                  )}

                  {cuenta.puedeRenovar && tiposMembresia && tiposMembresia.length > 0 && (
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
                      {/* Solo si hay alguna vigente: un selector vacío que
                          dice "Sin promoción" y no ofrece nada más es ruido en
                          la pantalla que más se usa del sistema. */}
                      {promociones.length > 0 && (
                        <div className="w-56">
                          <SelectField
                            label="Promoción"
                            value={idPromocionElegida}
                            onChange={setIdPromocionElegida}
                            options={promociones.map((p) => ({
                              value: String(p.idPromocion),
                              label: `${p.nombre} — ${p.etiqueta}`,
                            }))}
                            placeholder="Sin promoción"
                            icon={Tag}
                          />
                        </div>
                      )}
                      <PrimaryButton
                        label={cuenta.tieneMembresia ? 'Cobrar renovación' : 'Cobrar membresía'}
                        onClick={cobrarMembresiaClick}
                        disabled={ocupado || !tipoElegido}
                      />
                    </div>
                  )}

                  {/* Las tres cifras, no solo el final: quien cobra tiene que
                      poder decirle al socio cuánto era y cuánto se le
                      descontó. */}
                  {previa && (
                    <div className="mt-3 flex flex-wrap items-baseline gap-x-3 gap-y-1 rounded-md border border-border-active bg-surface-hover px-3 py-2">
                      <Tag size={14} className="text-primary-volt" />
                      <span className="font-body text-sm text-text-secondary line-through">
                        {formatearMoneda(previa.precioLista)}
                      </span>
                      <span className="font-mono text-base font-semibold text-primary-volt">
                        {formatearMoneda(previa.precioFinal)}
                      </span>
                      <span className="font-body text-xs text-text-muted">
                        ahorra {formatearMoneda(previa.descuento)} con "{previa.promocion}"
                      </span>
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
