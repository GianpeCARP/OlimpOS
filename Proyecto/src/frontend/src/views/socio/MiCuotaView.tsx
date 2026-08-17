import { useCallback, useEffect, useState } from 'react';
import {
  AlertTriangle,
  Banknote,
  CalendarClock,
  CreditCard,
  Info,
  LogOut,
  Pause,
  Play,
  Wallet,
} from 'lucide-react';
import {
  PrimaryButton,
  SectionCard,
  StatCard,
  StatusBadge,
  Topbar,
} from '../../components/ui';
import { colors } from '../../config';
import { mensajeDeError } from '../../services/api';
import {
  congelarMiMembresia,
  darmeDeBaja,
  getMiCuota,
  getMisCongelamientos,
  getPlanesDisponibles,
  iniciarPagoDeCuota,
  reanudarMiMembresia,
  simularAcreditacion,
  type Congelamiento,
  type MiCuota,
  type PlanDisponible,
} from '../../services/socioService';
import { useAuthStore } from '../../store/authStore';
import { useUiStore } from '../../store/uiStore';
import { InputField } from '../../components/ui';
// formatearFecha (con año cuando no es el año en curso) y no
// formatearFechaCorta: una membresía anual arranca y vence el mismo día de
// meses distintos, y sin el año las dos fechas se leían idénticas.
import { formatearFecha, formatearMoneda } from '../../utils/format';
import { parsearFecha } from '../../utils/fechas';
import { SinSocioEnSesion } from './SinSocioEnSesion';

// Vista 5 del portal (docs/prompt_portal_socio.md).
//
// ESTA VISTA YA NO ES SOLO LECTURA, y el cambio merece explicación porque
// contradice la nota que estaba acá antes.
//
// Decía: "cobrar es de recepción (DFD 2.3: el socio consulta, el dueño
// modifica); el socio ve lo que debe y con eso va al mostrador". Era fiel al
// DFD original, pero el dueño del proyecto cambió el criterio: el socio tiene
// que poder manejarse solo en todo aspecto y pasar por recepción únicamente
// si es muy necesario, más allá del primer registro.
//
// Lo que se agregó acá es la autogestión de la MEMBRESÍA: pausarla por un
// viaje o una lesión, reanudarla, y darse de baja. Son cosas que antes
// requerían ir al mostrador a pedirle a otra persona que las hiciera.
//
// El botón de PAGAR sigue sin estar, pero ya no por la razón de antes: falta
// la integración con Mercado Pago. Cuando exista, va acá.
//
// Reutiliza StatCard, StatusBadge y SectionCard.

/** Cómo se pinta cada estado de pago en la tabla de historial. */
const COLOR_ESTADO_PAGO: Record<string, string> = {
  CONFIRMADO: colors.statusOk,
  PENDIENTE: colors.statusWarn,
  CANCELADO: colors.textMuted,
  REEMBOLSADO: colors.textMuted,
};

const ETIQUETA_ESTADO_PAGO: Record<string, string> = {
  CONFIRMADO: 'Confirmado',
  PENDIENTE: 'Pendiente',
  CANCELADO: 'Cancelado',
  REEMBOLSADO: 'Reembolsado',
};

function Skeleton({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-md bg-surface-hover ${className}`} />;
}

/** "vence en 20 días" / "venció hace 5 días" / "vence hoy". */
function textoVencimiento(dias: number): string {
  if (dias === 0) return 'Vence hoy';
  if (dias > 0) return `Faltan ${dias} ${dias === 1 ? 'día' : 'días'}`;
  const atraso = Math.abs(dias);
  return `Venció hace ${atraso} ${atraso === 1 ? 'día' : 'días'}`;
}

export function MiCuotaView() {
  const idSocio = useAuthStore((s) => s.idSocio);

  const [cuota, setCuota] = useState<MiCuota | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intento, setIntento] = useState(0);

  useEffect(() => {
    if (idSocio === null) return;
    let cancelado = false;
    setCuota(null);
    setError(null);
    Promise.all([getMiCuota(), getMisCongelamientos(), getPlanesDisponibles()])
      .then(([datos, pausas, listaPlanes]) => {
        if (cancelado) return;
        setCuota(datos);
        setCongelamientos(pausas);
        setPlanes(listaPlanes);
      })
      .catch((err: unknown) => {
        if (!cancelado) setError(mensajeDeError(err));
      });
    return () => {
      cancelado = true;
    };
  }, [idSocio, intento]);

  // ── Autogestión de la membresía ────────────────────────────────────────
  const showSnack = useUiStore((s) => s.showSnack);
  const confirmDialog = useUiStore((s) => s.confirmDialog);
  const [congelamientos, setCongelamientos] = useState<Congelamiento[]>([]);
  const [hastaCuando, setHastaCuando] = useState('');
  const [motivoPausa, setMotivoPausa] = useState('');
  const [procesando, setProcesando] = useState(false);
  const [planes, setPlanes] = useState<PlanDisponible[]>([]);
  const [pagando, setPagando] = useState<number | null>(null);

  const recargar = useCallback(() => setIntento((n) => n + 1), []);

  const pausaActiva = congelamientos.find((c) => c.estado === 'ACTIVO') ?? null;

  const congelar = useCallback(() => {
    if (!hastaCuando) {
      showSnack('Elegí hasta cuándo querés pausarla', colors.statusWarn);
      return;
    }
    setProcesando(true);
    congelarMiMembresia(hastaCuando, motivoPausa || undefined)
      .then(() => {
        showSnack('Listo, tu membresía quedó en pausa', colors.statusOk);
        setHastaCuando('');
        setMotivoPausa('');
        recargar();
      })
      .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger))
      .finally(() => setProcesando(false));
  }, [hastaCuando, motivoPausa, showSnack, recargar]);

  const reanudar = useCallback(() => {
    setProcesando(true);
    reanudarMiMembresia()
      .then((c) => {
        // El mensaje lo arma el backend porque incluye cuántos días se
        // sumaron, y ese número lo calcula él: son los días que REALMENTE
        // estuvo pausada, no los que pidió. Rearmarlo acá significaría
        // repetir esa cuenta en el cliente y arriesgar que diga otra cosa.
        showSnack(c.mensaje ?? 'Tu membresía vuelve a estar activa', colors.statusOk);
        recargar();
      })
      .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger))
      .finally(() => setProcesando(false));
  }, [showSnack, recargar]);

  const pagar = useCallback(
    async (plan: PlanDisponible) => {
      setPagando(plan.idTipoMembresia);
      try {
        const r = await iniciarPagoDeCuota(plan.idTipoMembresia);
        if (r.simulado) {
          // Modo simulado: no hay Mercado Pago. Se acredita a mano para poder
          // ver qué pasa después del pago. El backend sólo habilita esto
          // cuando NO hay un token real cargado.
          await simularAcreditacion(r.idPago);
          showSnack(`[Simulado] Se acreditó ${plan.nombre}. No se cobró nada.`, colors.statusWarn);
          recargar();
          return;
        }
        // Pago real: se sale de la app hacia el checkout de Mercado Pago.
        // No se abre en pestaña nueva a propósito — los bloqueadores de
        // popups las frenan y el socio se queda mirando una pantalla que no
        // hace nada.
        showSnack(r.mensaje, colors.statusOk);
        window.location.href = r.urlCheckout;
      } catch (err) {
        showSnack(mensajeDeError(err), colors.statusDanger);
      } finally {
        setPagando(null);
      }
    },
    [showSnack, recargar],
  );

  const darDeBaja = useCallback(() => {
    confirmDialog(
      'Darte de baja',
      'Se cancela tu membresía y las clases que tengas reservadas. ' +
        'Tu cuenta sigue activa: vas a poder entrar cuando quieras a ver tu ' +
        'historial, y si volvés no hace falta que te den de alta de nuevo.',
      () => {
        setProcesando(true);
        darmeDeBaja()
          .then(({ mensaje }) => {
            showSnack(mensaje, colors.statusOk);
            recargar();
          })
          .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger))
          .finally(() => setProcesando(false));
      },
    );
  }, [confirmDialog, showSnack, recargar]);

  if (idSocio === null) {
    return <SinSocioEnSesion titulo="Mi cuota" />;
  }

  const tieneDeuda = (cuota?.deudas.length ?? 0) > 0;

  return (
    <div>
      <Topbar title="Mi cuota" subtitle={cuota ? cuota.plan : undefined} />

      <div className="space-y-4 p-8">
        {error && (
          <SectionCard>
            <p className="mb-4 font-body text-sm text-status-danger">{error}</p>
            <PrimaryButton label="Reintentar" onClick={recargar} />
          </SectionCard>
        )}

        {!error && !cuota && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-28" />
              ))}
            </div>
            <Skeleton className="h-56" />
          </div>
        )}

        {!error && cuota && (
          <>
            {/* La deuda va PRIMERA, arriba de todo: es lo único de esta
                pantalla que pide una acción del socio. Debajo de tres
                tarjetas y una tabla, se la perdería. */}
            {tieneDeuda && (
              <div
                className="rounded-lg border px-5 py-4"
                style={{
                  borderColor: colors.statusDanger,
                  backgroundColor: `${colors.statusDanger}14`,
                }}
              >
                <div className="flex items-start gap-3">
                  <AlertTriangle
                    size={20}
                    color={colors.statusDanger}
                    className="mt-0.5 shrink-0"
                  />
                  <div className="min-w-0 flex-1">
                    <p className="font-heading text-lg font-semibold text-text-main">
                      Tenés {formatearMoneda(cuota.totalAdeudado)} pendiente
                      {cuota.deudas.length > 1 ? 's' : ''}
                    </p>
                    <p className="mt-1 font-body text-sm text-text-secondary">
                      Acercate a recepción para regularizar. Desde acá no se puede pagar.
                    </p>

                    <div className="mt-4 flex flex-col divide-y divide-border-idle border-t border-border-idle pt-2">
                      {cuota.deudas.map((deuda) => (
                        <div
                          key={deuda.idDeuda}
                          className="flex flex-wrap items-baseline justify-between gap-2 py-2"
                        >
                          <div className="min-w-0">
                            <p className="font-body text-sm text-text-main">
                              {deuda.observaciones ?? 'Cuota impaga'}
                            </p>
                            <p className="font-body text-xs text-text-muted">
                              Generada el{' '}
                              {formatearFecha(parsearFecha(deuda.fechaGeneracion))}
                              {/* Sólo se muestra el atraso si realmente hay
                                  atraso: una deuda generada que todavía no
                                  venció no es una deuda "vencida hace -3
                                  días". */}
                              {deuda.diasDeAtraso > 0 &&
                                ` · ${deuda.diasDeAtraso} ${
                                  deuda.diasDeAtraso === 1 ? 'día' : 'días'
                                } de atraso`}
                            </p>
                          </div>
                          <span className="font-mono text-sm text-text-main">
                            {formatearMoneda(deuda.monto)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <StatCard
                title="Próximo vencimiento"
                value={
                  cuota.vencimiento
                    ? formatearFecha(parsearFecha(cuota.vencimiento))
                    // "No vence" y "Sin membresía" son casos distintos que
                    // vencimiento=undefined no alcanza a distinguir — ver
                    // el comentario de MiCuota.tieneMembresia.
                    : cuota.tieneMembresia
                      ? 'No vence'
                      : 'Sin membresía'
                }
                delta={
                  cuota.diasParaVencer !== undefined
                    ? textoVencimiento(cuota.diasParaVencer)
                    : undefined
                }
                // Vencida o por vencer se pinta en rojo; con margen, verde.
                // La flecha no aporta acá, pero StatCard siempre dibuja una:
                // se usa la que acompaña al color.
                tendencia={
                  cuota.diasParaVencer !== undefined && cuota.diasParaVencer < 0 ? 'down' : 'up'
                }
                deltaEsBueno={cuota.diasParaVencer !== undefined && cuota.diasParaVencer >= 0}
                icon={CalendarClock}
                color={colors.primaryVolt}
              />
              <StatCard
                title="Valor de tu plan"
                value={
                  cuota.precioPactado !== undefined
                    ? formatearMoneda(cuota.precioPactado)
                    : '—'
                }
                icon={CreditCard}
                color={colors.statusOk}
              />
              <StatCard
                title="Saldo pendiente"
                value={formatearMoneda(cuota.totalAdeudado)}
                icon={Banknote}
                color={tieneDeuda ? colors.statusDanger : colors.textSecondary}
              />
            </div>

            <SectionCard title="Tu membresía">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-heading text-lg font-semibold text-text-main">
                    {cuota.plan}
                  </p>
                  {cuota.fechaInicio && (
                    <p className="font-body text-sm text-text-secondary">
                      Desde el {formatearFecha(parsearFecha(cuota.fechaInicio))}
                    </p>
                  )}
                </div>
                <StatusBadge status={cuota.estado} />
              </div>

              {!tieneDeuda && (
                <div className="mt-4 flex items-start gap-3 border-t border-border-idle pt-4">
                  <Info size={16} className="mt-0.5 shrink-0 text-text-muted" />
                  <p className="font-body text-sm text-text-secondary">
                    Estás al día, no tenés nada pendiente. Para cambiar de plan, acercate
                    a recepción.
                  </p>
                </div>
              )}
            </SectionCard>

            {/* ── Autogestión ──────────────────────────────────────────────
                Pausar y darse de baja sin pedirle a nadie que lo haga.

                La tarjeta cambia entera según si hay una pausa activa: no
                tiene sentido ofrecer "pausar" a alguien que ya está pausado,
                ni "reanudar" a quien no lo está. Mostrar los dos botones
                siempre y deshabilitar uno obliga a leer para entender cuál
                aplica. */}
            {/* ── Pagar ────────────────────────────────────────────────────
                Va ARRIBA de la autogestión y de la baja: es lo que la mayoría
                viene a hacer, y lo que resuelve la deuda que la pantalla
                acaba de mostrar.

                Si el backend no tiene Mercado Pago configurado, el pedido
                falla con un 503 cuyo mensaje manda a recepción. No se
                esconden los botones: que el socio vea el precio y sepa cuánto
                tiene que llevar es útil igual. */}
            {planes.length > 0 && (
              <SectionCard title={tieneDeuda ? 'Regularizar tu cuota' : 'Renovar tu cuota'}>
                <div className="space-y-2">
                  {planes.map((plan) => (
                    <div
                      key={plan.idTipoMembresia}
                      className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border-idle p-3"
                    >
                      <div>
                        <p className="font-body text-sm text-text-main">{plan.nombre}</p>
                        <p className="font-body text-xs text-text-muted">
                          {plan.duracionDias} días
                          {plan.descripcion ? ` · ${plan.descripcion}` : ''}
                        </p>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="font-mono text-sm text-text-main">
                          {formatearMoneda(plan.precio)}
                        </span>
                        <PrimaryButton
                          label={pagando === plan.idTipoMembresia ? 'Un momento...' : 'Pagar'}
                          icon={Wallet}
                          disabled={pagando !== null || procesando}
                          onClick={() => void pagar(plan)}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </SectionCard>
            )}

            <SectionCard title="Tu membresía, a tu manera">
              {pausaActiva ? (
                <div className="space-y-4">
                  <div className="flex items-start gap-3 rounded-lg border border-status-warn/40 bg-status-warn/10 p-3">
                    <Pause size={16} className="mt-0.5 shrink-0 text-status-warn" />
                    <div>
                      <p className="font-body text-sm text-text-main">
                        Tu membresía está en pausa
                        {pausaActiva.motivo ? ` (${pausaActiva.motivo})` : ''}.
                      </p>
                      <p className="font-body text-xs text-text-secondary">
                        Pediste hasta el{' '}
                        {formatearFecha(parsearFecha(pausaActiva.fechaFin))}, pero podés
                        volver cuando quieras: sólo se te suman al vencimiento los días
                        que realmente estuviste afuera.
                      </p>
                    </div>
                  </div>
                  <PrimaryButton
                    label={procesando ? 'Un momento...' : 'Volver a activarla'}
                    icon={Play}
                    disabled={procesando}
                    onClick={reanudar}
                  />
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="flex items-start gap-3">
                    <Pause size={16} className="mt-0.5 shrink-0 text-text-muted" />
                    <p className="font-body text-sm text-text-secondary">
                      ¿Te vas de viaje o estás lesionado? Pausá la cuota y no perdés los
                      días que pagaste: se te suman al vencimiento cuando volvés.
                      La pausa mínima es de 7 días.
                    </p>
                  </div>
                  <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                    <InputField
                      label="Hasta cuándo"
                      type="date"
                      value={hastaCuando}
                      onChange={setHastaCuando}
                    />
                    <InputField
                      label="Motivo (opcional)"
                      hint="Ej: viaje"
                      value={motivoPausa}
                      onChange={setMotivoPausa}
                    />
                  </div>
                  <PrimaryButton
                    label={procesando ? 'Un momento...' : 'Pausar mi membresía'}
                    icon={Pause}
                    disabled={procesando}
                    onClick={congelar}
                  />
                </div>
              )}

              {/* Las pausas ya usadas. Importa mostrarlas porque hay un tope
                  anual: sin el historial, el socio se entera de que se quedó
                  sin días recién cuando el backend le rechaza el pedido. */}
              {congelamientos.some((c) => c.estado === 'FINALIZADO') && (
                <div className="mt-4 border-t border-border-idle pt-4">
                  <p className="mb-2 font-body text-xs uppercase tracking-wide text-text-muted">
                    Pausas anteriores
                  </p>
                  <div className="space-y-1">
                    {congelamientos
                      .filter((c) => c.estado === 'FINALIZADO')
                      .map((c) => (
                        <p
                          key={c.idCongelamiento}
                          className="font-body text-xs text-text-secondary"
                        >
                          {formatearFecha(parsearFecha(c.fechaInicio))} —{' '}
                          {c.diasAplicados ?? 0} día
                          {(c.diasAplicados ?? 0) === 1 ? '' : 's'}
                          {c.motivo ? ` · ${c.motivo}` : ''}
                        </p>
                      ))}
                  </div>
                </div>
              )}

              {/* La baja va al final y separada: es la acción más
                  irreversible de la pantalla y no tiene por qué competir
                  visualmente con pausar, que es lo que la mayoría busca. */}
              <div className="mt-4 border-t border-border-idle pt-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="font-body text-xs text-text-muted">
                    ¿Ya no querés seguir? Podés darte de baja. Tu cuenta y tu historial
                    quedan igual, y si volvés no hace falta que te den de alta de nuevo.
                  </p>
                  <button
                    type="button"
                    disabled={procesando}
                    onClick={darDeBaja}
                    className="flex items-center gap-2 rounded-lg border px-3 py-2 font-body text-sm transition-opacity disabled:opacity-50"
                    style={{ borderColor: colors.statusDanger, color: colors.statusDanger }}
                  >
                    <LogOut size={14} />
                    Darme de baja
                  </button>
                </div>
              </div>
            </SectionCard>

            <SectionCard title="Historial de pagos">
              {cuota.pagos.length === 0 ? (
                <p className="font-body text-sm text-text-muted">
                  Todavía no registramos ningún pago tuyo.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-border-idle">
                        {['Fecha', 'Monto', 'Método', 'Estado', 'Comprobante'].map((h) => (
                          <th
                            key={h}
                            className="py-2 pr-4 text-left font-body text-xs font-semibold tracking-wide text-text-secondary uppercase"
                          >
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {cuota.pagos.map((pago) => (
                        <tr key={pago.idPago} className="border-b border-border-idle last:border-b-0">
                          <td className="py-2 pr-4 font-body text-sm text-text-main">
                            {formatearFecha(parsearFecha(pago.fecha))}
                          </td>
                          <td className="py-2 pr-4 font-mono text-sm text-text-main">
                            {formatearMoneda(pago.monto)}
                          </td>
                          <td className="py-2 pr-4 font-body text-sm text-text-secondary">
                            {pago.metodo}
                          </td>
                          <td className="py-2 pr-4">
                            <span
                              className="font-body text-xs"
                              style={{ color: COLOR_ESTADO_PAGO[pago.estado] ?? colors.textMuted }}
                            >
                              {ETIQUETA_ESTADO_PAGO[pago.estado] ?? pago.estado}
                            </span>
                          </td>
                          <td className="py-2 pr-4 font-mono text-xs text-text-muted">
                            {pago.numeroComprobante ?? '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </SectionCard>
          </>
        )}
      </div>
    </div>
  );
}
