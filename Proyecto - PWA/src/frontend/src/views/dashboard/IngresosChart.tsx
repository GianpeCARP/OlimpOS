import { useEffect, useState } from 'react';
import { FilterChip, SectionCard } from '../../components/ui';
import { mensajeDeError } from '../../services/api';
import {
  obtenerIngresosPorPeriodo,
  type EscalaIngresos,
  type IngresosPorPeriodo,
} from '../../services/dashboardService';
import { formatearMoneda } from '../../utils/format';

// Ingresos por día, mes o año. Sólo para quien tiene `verIngresos` (el Dueño):
// lo decide DashboardView, que no lo monta para los demás.
//
// Es un componente aparte, con su propia carga, a propósito: cambiar de escala
// vuelve a pedir SÓLO el gráfico. Si viviera en el Promise.all del dashboard,
// cada click en "Mes" recargaría también métricas, actividad y socios.
//
// Sin librería de gráficos, igual que ProgresoExtra.tsx: barras con altura en
// porcentaje. Traer 40 kB por esto no se justifica.
//
// Gemelo de _card_ingresos en app/views/dashboard.py (Flet).

const ESCALAS: { valor: EscalaIngresos; label: string }[] = [
  { valor: 'dia', label: 'Día' },
  { valor: 'mes', label: 'Mes' },
  { valor: 'anio', label: 'Año' },
];

/** Qué dice debajo del total, según la escala. */
const RANGO: Record<EscalaIngresos, string> = {
  dia: 'últimos 30 días',
  mes: 'últimos 12 meses',
  anio: 'últimos 5 años',
};

// Que un día chico no desaparezca del todo al lado de uno grande.
const ALTURA_MINIMA = 4; // %

export function IngresosChart() {
  const [escala, setEscala] = useState<EscalaIngresos>('dia');
  const [datos, setDatos] = useState<IngresosPorPeriodo | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelado = false;
    setDatos(null);
    setError(null);
    obtenerIngresosPorPeriodo(escala)
      .then((d) => {
        if (!cancelado) setDatos(d);
      })
      .catch((err: unknown) => {
        if (!cancelado) setError(mensajeDeError(err));
      });
    return () => {
      cancelado = true;
    };
  }, [escala]);

  const maximo = datos ? Math.max(...datos.puntos.map((p) => p.monto), 1) : 1;
  // Con 30 barras no entran 30 rótulos legibles: se rotula uno cada cinco.
  // En mes (12) y año (5) sí entran todos.
  const cadaCuantos = escala === 'dia' ? 5 : 1;

  return (
    <SectionCard title="Ingresos">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-mono text-2xl font-bold text-text-main">
            {datos ? formatearMoneda(datos.total) : '—'}
          </p>
          <p className="font-body text-xs text-text-muted">{RANGO[escala]}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {ESCALAS.map((e) => (
            <FilterChip
              key={e.valor}
              label={e.label}
              activo={escala === e.valor}
              onClick={() => setEscala(e.valor)}
            />
          ))}
        </div>
      </div>

      {error && <p className="mt-4 font-body text-sm text-status-danger">{error}</p>}

      {!error && !datos && <div className="mt-4 h-44 animate-pulse rounded-md bg-surface-hover" />}

      {!error && datos && (
        <div className="mt-4">
          {datos.total === 0 && (
            <p className="mb-2 font-body text-xs text-text-muted">
              Todavía no hay cobros confirmados en este período.
            </p>
          )}
          <div className={`flex h-40 items-end ${escala === 'dia' ? 'gap-0.5' : 'gap-1.5'}`}>
            {datos.puntos.map((p) => {
              const alto =
                p.monto <= 0 ? 0 : ALTURA_MINIMA + (p.monto / maximo) * (100 - ALTURA_MINIMA);
              return (
                <div key={p.periodo} className="flex h-full flex-1 flex-col justify-end">
                  <div
                    className="w-full rounded-t-sm bg-primary-volt/70 transition-[height] hover:bg-primary-volt"
                    style={{ height: `${alto}%` }}
                    title={`${p.etiqueta}: ${formatearMoneda(p.monto)}`}
                  />
                </div>
              );
            })}
          </div>
          <div
            className={`mt-2 flex border-t border-border-idle pt-2 ${escala === 'dia' ? 'gap-0.5' : 'gap-1.5'}`}
          >
            {datos.puntos.map((p, i) => (
              <span
                key={p.periodo}
                className="flex-1 overflow-visible text-center font-body text-[10px] whitespace-nowrap text-text-muted"
              >
                {i % cadaCuantos === 0 ? p.etiqueta : ''}
              </span>
            ))}
          </div>
        </div>
      )}
    </SectionCard>
  );
}
