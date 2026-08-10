import { useCallback, useEffect, useState } from 'react';
import {
  AlertTriangle,
  Apple,
  Bolt,
  Flame,
  Minus,
  StickyNote,
  TrendingDown,
  TrendingUp,
  User,
  type LucideIcon,
} from 'lucide-react';
import { PrimaryButton, SectionCard, Topbar } from '../../components/ui';
import { ObjetivoDieta, colors, type ObjetivoDietaValue } from '../../config';
import { mensajeDeError } from '../../services/api';
import { getMiDieta, type MiDieta } from '../../services/socioService';
import { useAuthStore } from '../../store/authStore';
import { formatearFecha, formatearNumero } from '../../utils/format';
import { parsearFecha } from '../../utils/fechas';
import { InfoPill } from '../rutinas/InfoPill';
import { SinSocioEnSesion } from './SinSocioEnSesion';

// Vista 4 del portal (docs/prompt_portal_socio.md). Espejo de MiRutinaView:
// solo lectura, sin un botón que modifique nada.
//
// Mismo criterio que allá sobre "reutilizá la card del admin": se reutilizan
// las piezas (SectionCard, InfoPill, el chip de objetivo) pero no PlanCard
// entero, que muestra "N socios asignados" — dato de gestión que no le
// corresponde al socio.
//
// El mapa de objetivos se repite acá en vez de importarse de PlanCard porque
// ese componente no lo exporta y no vale la pena tocar la vista de admin
// para esto. Si aparece un tercer lugar que lo necesite, ahí sí conviene
// subirlo a config.ts junto a ObjetivoDieta.
const CONFIG_OBJETIVO: Record<ObjetivoDietaValue, { icono: LucideIcon; color: string }> = {
  [ObjetivoDieta.MASA_MUSCULAR]: { icono: TrendingUp, color: colors.statusOk },
  [ObjetivoDieta.BAJAR_PESO]: { icono: TrendingDown, color: colors.statusDanger },
  [ObjetivoDieta.MANTENIMIENTO]: { icono: Minus, color: colors.primaryVolt },
  [ObjetivoDieta.ALTO_RENDIMIENTO]: { icono: Bolt, color: colors.statusWarn },
};
const CONFIG_POR_DEFECTO = { icono: Minus, color: colors.textMuted };

function Skeleton({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-md bg-surface-hover ${className}`} />;
}

export function MiDietaView() {
  const idSocio = useAuthStore((s) => s.idSocio);

  const [dieta, setDieta] = useState<MiDieta | null>(null);
  // Igual que en Mi rutina: null es una respuesta válida (no tiene dieta),
  // así que hace falta un flag aparte para saber si ya cargó.
  const [cargado, setCargado] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [intento, setIntento] = useState(0);

  useEffect(() => {
    if (idSocio === null) return;
    let cancelado = false;
    setCargado(false);
    setError(null);
    getMiDieta()
      .then((datos) => {
        if (cancelado) return;
        setDieta(datos);
        setCargado(true);
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
    return <SinSocioEnSesion titulo="Mi dieta" />;
  }

  // Mismo fallback defensivo que se corrigió en PlanCard: objetivo es
  // varchar libre en el esquema, un valor fuera del mapa no puede tumbar la
  // vista con un TypeError.
  const { icono: IconoObjetivo, color: colorObjetivo } =
    (dieta?.objetivo && CONFIG_OBJETIVO[dieta.objetivo as keyof typeof CONFIG_OBJETIVO]) ||
    CONFIG_POR_DEFECTO;

  return (
    <div>
      <Topbar
        title="Mi dieta"
        subtitle={cargado && dieta ? `Te la armó ${dieta.nutricionista}` : undefined}
      />

      <div className="space-y-4 p-8">
        {error && (
          <SectionCard>
            <p className="mb-4 font-body text-sm text-status-danger">{error}</p>
            <PrimaryButton label="Reintentar" onClick={recargar} />
          </SectionCard>
        )}

        {!error && !cargado && (
          <div className="space-y-4">
            <Skeleton className="h-44" />
            <Skeleton className="h-64" />
          </div>
        )}

        {!error && cargado && !dieta && (
          <SectionCard>
            <div className="flex flex-col items-center gap-3 py-8 text-center">
              <Apple size={32} className="text-text-muted" />
              <p className="font-heading text-lg font-semibold text-text-main">
                Todavía no tenés un plan nutricional
              </p>
              <p className="max-w-md font-body text-sm text-text-secondary">
                Si querés uno, pedilo en recepción y te coordinan una consulta con la
                nutricionista.
              </p>
            </div>
          </SectionCard>
        )}

        {!error && cargado && dieta && (
          <>
            <SectionCard>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div
                    className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 font-body text-xs font-medium"
                    style={{
                      backgroundColor: `${colorObjetivo}1A`,
                      color: colorObjetivo,
                    }}
                  >
                    <IconoObjetivo size={14} />
                    {dieta.objetivo ?? 'Sin objetivo'}
                  </div>
                  <h2 className="mt-2 font-heading text-xl font-semibold text-text-main">
                    {dieta.nombre}
                  </h2>
                </div>
                <Apple size={20} className="shrink-0 text-primary-volt" />
              </div>

              {dieta.caloriasDiarias !== undefined && (
                <div className="mt-4 flex items-baseline gap-1.5">
                  {/* font-mono para métricas, igual que PlanCard/StatCard. */}
                  <span className="font-mono text-4xl font-bold text-text-main">
                    {formatearNumero(dieta.caloriasDiarias)}
                  </span>
                  <span className="font-body text-sm text-text-secondary">kcal/día</span>
                </div>
              )}

              {dieta.descripcion && (
                <p className="mt-3 font-body text-sm text-text-secondary">{dieta.descripcion}</p>
              )}

              <div className="mt-4 flex flex-wrap gap-2">
                <InfoPill icon={User} text={dieta.nutricionista} />
                {dieta.caloriasDiarias !== undefined && (
                  <InfoPill
                    icon={Flame}
                    text={`${formatearNumero(dieta.caloriasDiarias)} kcal objetivo`}
                  />
                )}
              </div>

              {/* Observaciones de la ASIGNACIÓN: son las indicaciones que la
                  nutricionista le dejó a este socio en particular, distintas
                  de la descripción general del plan. Se destacan porque son
                  lo más específico que hay en toda la pantalla. */}
              {dieta.observaciones && (
                <div className="mt-4 flex items-start gap-3 rounded-lg border border-border-idle bg-surface-hover px-4 py-3">
                  <StickyNote size={16} className="mt-0.5 shrink-0 text-primary-volt" />
                  <div>
                    <p className="font-body text-xs text-text-muted">Indicaciones para vos</p>
                    <p className="font-body text-sm text-text-main">{dieta.observaciones}</p>
                  </div>
                </div>
              )}

              <p className="mt-4 border-t border-border-idle pt-4 font-body text-xs text-text-muted">
                Lo tenés asignado desde el {formatearFecha(parsearFecha(dieta.fechaInicio))}.
              </p>

              {dieta.dietaDeBaja && (
                <div
                  className="mt-4 flex items-start gap-3 rounded-lg border px-4 py-3"
                  style={{
                    borderColor: colors.statusWarn,
                    backgroundColor: `${colors.statusWarn}14`,
                  }}
                >
                  <AlertTriangle size={16} color={colors.statusWarn} className="mt-0.5 shrink-0" />
                  <p className="font-body text-sm text-text-main">
                    El gimnasio dio de baja este plan. Consultá con la nutricionista antes de
                    seguir con él.
                  </p>
                </div>
              )}
            </SectionCard>

            {dieta.dias.length === 0 ? (
              <SectionCard title="Plan alimentario">
                <p className="font-body text-sm text-text-muted">
                  Tu nutricionista todavía no cargó las comidas de este plan. Las indicaciones de
                  arriba son las que valen por ahora.
                </p>
              </SectionCard>
            ) : (
              dieta.dias.map((dia) => (
                <SectionCard
                  key={dia.dia}
                  title={dia.dia === 0 ? 'Sin día asignado' : `Día ${dia.dia}`}
                >
                  <div className="flex flex-col divide-y divide-border-idle">
                    {dia.comidas.map((comida) => (
                      <div
                        key={comida.idComida}
                        className="flex items-start justify-between gap-4 py-3"
                      >
                        <div className="min-w-0">
                          {comida.momento && (
                            <p className="font-body text-xs text-text-muted">{comida.momento}</p>
                          )}
                          <p className="font-body text-sm text-text-main">{comida.descripcion}</p>
                        </div>
                        {comida.calorias !== undefined && (
                          <span className="shrink-0 font-mono text-xs text-text-secondary">
                            {formatearNumero(comida.calorias)} kcal
                          </span>
                        )}
                      </div>
                    ))}
                  </div>

                  {dia.caloriasDelDia !== undefined && (
                    <div className="mt-3 flex justify-between border-t border-border-idle pt-3">
                      <span className="font-body text-sm text-text-secondary">Total del día</span>
                      <span className="font-mono text-sm text-text-main">
                        {formatearNumero(dia.caloriasDelDia)} kcal
                      </span>
                    </div>
                  )}
                </SectionCard>
              ))
            )}
          </>
        )}
      </div>
    </div>
  );
}
