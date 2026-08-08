import { useCallback, useEffect, useState } from 'react';
import { AlertTriangle, Banknote, CalendarClock, CreditCard, Info } from 'lucide-react';
import {
  PrimaryButton,
  SectionCard,
  StatCard,
  StatusBadge,
  Topbar,
} from '../../components/ui';
import { colors } from '../../config';
import { mensajeDeError } from '../../services/api';
import { getMiCuota, type MiCuota } from '../../services/socioService';
import { useAuthStore } from '../../store/authStore';
// formatearFecha (con año cuando no es el año en curso) y no
// formatearFechaCorta: una membresía anual arranca y vence el mismo día de
// meses distintos, y sin el año las dos fechas se leían idénticas.
import { formatearFecha, formatearMoneda } from '../../utils/format';
import { parsearFecha } from '../../utils/fechas';
import { SinSocioEnSesion } from './SinSocioEnSesion';

// Vista 5 del portal (docs/prompt_portal_socio.md). SOLO LECTURA, y acá la
// restricción es de negocio, no de comodidad: **no hay botón de pago**.
//
// Cobrar es de recepción (DFD 2.3: el socio consulta, el dueño modifica).
// El socio ve lo que debe y con eso va al mostrador. No es una limitación
// que haya que disculpar en la interfaz — se dice derecho: "acercate a
// recepción".
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
    getMiCuota(idSocio)
      .then((datos) => {
        if (!cancelado) setCuota(datos);
      })
      .catch((err: unknown) => {
        if (!cancelado) setError(mensajeDeError(err));
      });
    return () => {
      cancelado = true;
    };
  }, [idSocio, intento]);

  const recargar = useCallback(() => setIntento((n) => n + 1), []);

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
                    Estás al día, no tenés nada pendiente. Para renovar o cambiar de plan,
                    acercate a recepción.
                  </p>
                </div>
              )}
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
