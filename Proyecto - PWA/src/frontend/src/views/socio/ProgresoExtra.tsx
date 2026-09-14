import { useEffect, useState } from 'react';
import { Dumbbell, Flame, Minus, TrendingDown, TrendingUp, Utensils } from 'lucide-react';
import { SectionCard } from '../../components/ui';
import { colors } from '../../config';
import {
  listarMisComidas,
  listarMisRegistrosEjercicio,
  type ComidaRegistrada,
  type RegistroEjercicioListado,
} from '../../services/socioService';
import { formatearFechaCorta } from '../../utils/format';
import { parsearFecha } from '../../utils/fechas';

// =============================================================================
// PROGRESO — nutrición y fuerza. Se suman a MiProgresoView (que ya grafica el
// peso corporal). La idea: que el socio vea de un vistazo si mejora o empeora.
//
// Sin librería de charts, igual que el gráfico de peso: barras con altura en %
// y una sparkline en SVG hecha a mano. Traer 40 kB para esto no se justifica.

const ALTURA_MINIMA = 6; // % — que un valor chico no desaparezca del todo.

/** Barras verticales, escala desde CERO (para calorías, el cero es real). */
function GraficoBarras({
  datos,
}: {
  datos: { etiqueta: string; valor: number; titulo: string }[];
}) {
  const maximo = Math.max(...datos.map((d) => d.valor), 1);
  return (
    <div>
      <div className="flex h-36 items-end gap-1.5">
        {datos.map((d, i) => {
          const alto = d.valor <= 0 ? 0 : ALTURA_MINIMA + (d.valor / maximo) * (100 - ALTURA_MINIMA);
          return (
            <div key={i} className="flex h-full flex-1 flex-col items-center justify-end gap-1">
              <div
                className="w-full rounded-t-sm bg-primary-volt/70 transition-[height]"
                style={{ height: `${alto}%` }}
                title={d.titulo}
              />
            </div>
          );
        })}
      </div>
      <div className="mt-2 flex gap-1.5 border-t border-border-idle pt-2">
        {datos.map((d, i) => (
          <span key={i} className="flex-1 text-center font-body text-[10px] text-text-muted">
            {d.etiqueta}
          </span>
        ))}
      </div>
    </div>
  );
}

/** Línea de tendencia en SVG (para la fuerza por ejercicio). */
function Sparkline({ valores, subiendo }: { valores: number[]; subiendo: boolean }) {
  const w = 100;
  const h = 28;
  const min = Math.min(...valores);
  const max = Math.max(...valores);
  const rango = max - min || 1;
  const puntos = valores
    .map((v, i) => {
      const x = valores.length === 1 ? w / 2 : (i / (valores.length - 1)) * w;
      const y = h - 3 - ((v - min) / rango) * (h - 6);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
  const color = subiendo ? colors.statusOk : colors.textMuted;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className="h-8 w-full">
      <polyline points={puntos} fill="none" stroke={color} strokeWidth={2}
        strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

// -----------------------------------------------------------------------------
// NUTRICIÓN
// -----------------------------------------------------------------------------

interface DiaNutricion {
  fecha: string;
  calorias: number;
  proteinas: number;
}

function agruparPorDia(comidas: ComidaRegistrada[]): DiaNutricion[] {
  const mapa = new Map<string, DiaNutricion>();
  for (const c of comidas) {
    const d = mapa.get(c.fecha) ?? { fecha: c.fecha, calorias: 0, proteinas: 0 };
    d.calorias += c.calorias ?? 0;
    d.proteinas += c.proteinas ?? 0;
    mapa.set(c.fecha, d);
  }
  // De vieja a nueva, para leer el gráfico de izquierda a derecha.
  return [...mapa.values()].sort((a, b) => a.fecha.localeCompare(b.fecha));
}

export function SeccionNutricion() {
  const [comidas, setComidas] = useState<ComidaRegistrada[] | null>(null);

  useEffect(() => {
    let cancelado = false;
    listarMisComidas(30)
      .then((c) => { if (!cancelado) setComidas(c); })
      .catch(() => { if (!cancelado) setComidas([]); });
    return () => { cancelado = true; };
  }, []);

  if (comidas === null) {
    return (
      <SectionCard title="Nutrición">
        <div className="h-36 animate-pulse rounded-md bg-surface-hover" />
      </SectionCard>
    );
  }

  const dias = agruparPorDia(comidas);
  const conCalorias = dias.filter((d) => d.calorias > 0);

  if (conCalorias.length === 0) {
    return (
      <SectionCard title="Nutrición">
        <p className="font-body text-sm text-text-muted">
          Registrá tus comidas con calorías en “Mi dieta” y acá vas a ver tu promedio y la
          evolución día a día.
        </p>
      </SectionCard>
    );
  }

  const ultimos = conCalorias.slice(-14);
  const promCal = Math.round(conCalorias.reduce((s, d) => s + d.calorias, 0) / conCalorias.length);
  const promProt = Math.round(conCalorias.reduce((s, d) => s + d.proteinas, 0) / conCalorias.length);

  return (
    <SectionCard title="Nutrición">
      <div className="mb-4 flex flex-wrap gap-4">
        <div className="flex items-center gap-2">
          <Flame size={18} className="text-primary-volt" />
          <div>
            <p className="font-mono text-xl font-bold text-text-main">{promCal}</p>
            <p className="font-body text-xs text-text-muted">kcal/día (promedio)</p>
          </div>
        </div>
        {promProt > 0 && (
          <div className="flex items-center gap-2">
            <Utensils size={18} className="text-accent-coral" />
            <div>
              <p className="font-mono text-xl font-bold text-text-main">{promProt} g</p>
              <p className="font-body text-xs text-text-muted">proteína/día (promedio)</p>
            </div>
          </div>
        )}
      </div>
      <p className="mb-2 font-body text-xs text-text-muted">Calorías por día (últimos con registro)</p>
      <GraficoBarras
        datos={ultimos.map((d) => ({
          etiqueta: formatearFechaCorta(parsearFecha(d.fecha)),
          valor: d.calorias,
          titulo: `${d.calorias} kcal el ${formatearFechaCorta(parsearFecha(d.fecha))}`,
        }))}
      />
    </SectionCard>
  );
}

// -----------------------------------------------------------------------------
// FUERZA
// -----------------------------------------------------------------------------

interface ProgresoEjercicio {
  idEjercicio: number;
  nombre: string;
  pesos: number[];
  primero: number;
  ultimo: number;
  ultimaFecha: string;
}

function agruparPorEjercicio(regs: RegistroEjercicioListado[]): ProgresoEjercicio[] {
  const mapa = new Map<number, RegistroEjercicioListado[]>();
  for (const r of regs) {
    const g = mapa.get(r.idEjercicio) ?? [];
    g.push(r);
    mapa.set(r.idEjercicio, g);
  }
  const salida: ProgresoEjercicio[] = [];
  for (const g of mapa.values()) {
    // Ya vienen de viejo a nuevo desde el backend.
    const pesos = g.map((r) => r.pesoHecho);
    salida.push({
      idEjercicio: g[0].idEjercicio,
      nombre: g[0].nombreEjercicio,
      pesos,
      primero: pesos[0],
      ultimo: pesos[pesos.length - 1],
      ultimaFecha: g[g.length - 1].fecha,
    });
  }
  // El más entrenado recientemente, primero.
  return salida.sort((a, b) => b.ultimaFecha.localeCompare(a.ultimaFecha));
}

export function SeccionFuerza() {
  const [regs, setRegs] = useState<RegistroEjercicioListado[] | null>(null);

  useEffect(() => {
    let cancelado = false;
    listarMisRegistrosEjercicio(120)
      .then((r) => { if (!cancelado) setRegs(r); })
      .catch(() => { if (!cancelado) setRegs([]); });
    return () => { cancelado = true; };
  }, []);

  if (regs === null) {
    return (
      <SectionCard title="Fuerza">
        <div className="h-24 animate-pulse rounded-md bg-surface-hover" />
      </SectionCard>
    );
  }

  const ejercicios = agruparPorEjercicio(regs);

  if (ejercicios.length === 0) {
    return (
      <SectionCard title="Fuerza">
        <p className="font-body text-sm text-text-muted">
          Contá tus series con la cámara (y cargá el peso al terminar) y acá vas a ver cómo
          progresa la carga en cada ejercicio.
        </p>
      </SectionCard>
    );
  }

  return (
    <SectionCard title="Fuerza">
      <p className="mb-3 font-body text-xs text-text-muted">
        Peso máximo por día en cada ejercicio, desde que empezaste a registrar.
      </p>
      <div className="flex flex-col divide-y divide-border-idle">
        {ejercicios.map((e) => {
          const delta = Math.round((e.ultimo - e.primero) * 10) / 10;
          const subio = delta > 0;
          const bajo = delta < 0;
          const Icono = subio ? TrendingUp : bajo ? TrendingDown : Minus;
          const colorDelta = subio ? colors.statusOk : bajo ? colors.statusDanger : colors.textMuted;
          return (
            <div key={e.idEjercicio} className="flex items-center gap-3 py-3">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <Dumbbell size={14} className="shrink-0 text-primary-volt" />
                  <p className="truncate font-body text-sm text-text-main">{e.nombre}</p>
                </div>
                <p className="mt-0.5 font-mono text-xs text-text-secondary">
                  {e.primero} → {e.ultimo} kg
                  {e.pesos.length > 1 && (
                    <span className="ml-2 inline-flex items-center gap-0.5" style={{ color: colorDelta }}>
                      <Icono size={12} />
                      {delta > 0 ? '+' : ''}{delta} kg
                    </span>
                  )}
                </p>
              </div>
              <div className="w-24 shrink-0">
                {e.pesos.length > 1 ? (
                  <Sparkline valores={e.pesos} subiendo={!bajo} />
                ) : (
                  <span className="font-body text-[10px] text-text-muted">1 registro</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </SectionCard>
  );
}
