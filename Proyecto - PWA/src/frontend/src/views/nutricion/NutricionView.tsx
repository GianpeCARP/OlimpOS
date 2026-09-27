import { useCallback, useEffect, useMemo, useState } from 'react';
import { Flame, Plus, TrendingDown, TrendingUp, Users } from 'lucide-react';
import { FilterChip, PrimaryButton, SectionCard, StatCard, Topbar } from '../../components/ui';
import { colors, ObjetivoDieta, type ObjetivoDietaValue } from '../../config';
import { mensajeDeError } from '../../services/api';
import {
  listarPlanes,
  darDeBajaPlan,
  activarPlan,
  asignarPlanASocio,
  type PlanListado,
} from '../../services/nutricionService';
import { useUiStore } from '../../store/uiStore';
import { usePuedeAccion } from '../../hooks/usePermisos';
import { formatearNumero } from '../../utils/format';
import { AsignarASocioModal } from '../socios/AsignarASocioModal';
import { PlanCard } from './PlanCard';
import { PlanDetailModal } from './PlanDetailModal';
import { PlanFormModal } from './PlanFormModal';
import { PlatoFormModal } from './PlatoFormModal';

// Equivalente de NutricionView (estructura_nutricion.md): topbar con
// conteo + resumen calórico (4 _cal_stat, acá reusando el StatCard del
// dashboard) + grilla responsiva de tarjetas (1 col mobile, 2 desktop).
//
// Buscador y chips por objetivo son el mismo agregado de consistencia que
// en socios/personal/rutinas.

type FiltroObjetivo = ObjetivoDietaValue | 'Todos';
const FILTROS: FiltroObjetivo[] = ['Todos', ...Object.values(ObjetivoDieta)];

function Skeleton({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-md bg-surface-hover ${className}`} />;
}

/** Los 4 _cal_stat del doc, calculados sobre la misma lista que ya se pidió para las tarjetas — un solo fetch, como hacía el .py original. */
function calcularResumen(planes: PlanListado[]) {
  const calorias = planes
    .map((p) => p.caloriasDiarias)
    .filter((c): c is number => c !== undefined);

  const promedio = calorias.length > 0 ? Math.round(calorias.reduce((a, b) => a + b, 0) / calorias.length) : 0;
  const minimo = calorias.length > 0 ? Math.min(...calorias) : 0;
  const maximo = calorias.length > 0 ? Math.max(...calorias) : 0;
  const totalAsignados = planes.reduce((total, p) => total + p.asignados, 0);

  return { promedio, minimo, maximo, totalAsignados };
}

export function NutricionView() {
  const showSnack = useUiStore((s) => s.showSnack);
  const confirmDialog = useUiStore((s) => s.confirmDialog);

  // Espejo de RutinasView: sólo el Nutricionista gestiona dietas. El
  // Entrenador llega hasta acá con lectura — el caso que pidió el usuario:
  // "puede consultarlas para ver a qué socio le pertenece, pero no puede
  // desligarla ni darle de alta otra".
  const puedeGestionar = usePuedeAccion('gestionDietas');

  const [planes, setPlanes] = useState<PlanListado[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intento, setIntento] = useState(0);

  const [busqueda, setBusqueda] = useState('');
  const [filtro, setFiltro] = useState<FiltroObjetivo>('Todos');

  const [formModal, setFormModal] = useState<{ plan: PlanListado | null } | null>(null);
  const [detalle, setDetalle] = useState<PlanListado | null>(null);
  const [asignando, setAsignando] = useState<PlanListado | null>(null);
  const [nuevoPlato, setNuevoPlato] = useState(false);

  // Gestionar ESTE plan: la acción y que el backend diga que es editable.
  const gestionable = useCallback(
    (plan: PlanListado) => puedeGestionar && plan.puedeEditar,
    [puedeGestionar],
  );

  useEffect(() => {
    let cancelado = false;
    setPlanes(null);
    setError(null);
    listarPlanes()
      .then((lista) => {
        if (!cancelado) setPlanes(lista);
      })
      .catch((err: unknown) => {
        if (!cancelado) setError(mensajeDeError(err));
      });
    return () => {
      cancelado = true;
    };
  }, [intento]);

  const recargar = useCallback(() => setIntento((n) => n + 1), []);

  const visibles = useMemo(() => {
    if (!planes) return [];
    const texto = busqueda.trim().toLowerCase();
    return planes.filter((p) => {
      const coincideTexto =
        texto === '' ||
        p.nombre.toLowerCase().includes(texto) ||
        (p.descripcion?.toLowerCase().includes(texto) ?? false);
      return coincideTexto && (filtro === 'Todos' || p.objetivo === filtro);
    });
  }, [planes, busqueda, filtro]);

  const resumen = useMemo(() => calcularResumen(planes ?? []), [planes]);

  const actualizarEnLista = useCallback((actualizado: PlanListado) => {
    setPlanes((lista) =>
      lista
        ? lista.some((p) => p.idDieta === actualizado.idDieta)
          ? lista.map((p) => (p.idDieta === actualizado.idDieta ? actualizado : p))
          : [...lista, actualizado]
        : lista,
    );
  }, []);

  const pedirBaja = useCallback(
    (plan: PlanListado) => {
      confirmDialog(
        `¿Dar de baja "${plan.nombre}"?`,
        // El mismo texto que su gemelo de Flet, que dice lo que hace el backend
        // (dar_de_baja_dieta). Antes prometía una auditoría que no existe.
        'El plan deja de figurar como activo. Los socios que lo siguen lo terminan.',
        () => {
          darDeBajaPlan(plan.idDieta)
            .then(() => {
              showSnack(`"${plan.nombre}" fue dado de baja`, colors.statusOk);
              recargar();
            })
            .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
        },
      );
    },
    [confirmDialog, showSnack, recargar],
  );

  // Sin confirmDialog: reactivar es reversible y de bajo riesgo, a
  // diferencia de pedirBaja. Mismo criterio que rutinas/socios/personal.
  const activar = useCallback(
    (plan: PlanListado) => {
      activarPlan(plan.idDieta)
        .then((actualizado) => {
          showSnack(`"${plan.nombre}" fue reactivado`, colors.statusOk);
          actualizarEnLista(actualizado);
        })
        .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
    },
    [showSnack, actualizarEnLista],
  );

  return (
    <div>
      <Topbar
        title="Nutrición"
        subtitle={planes ? `${planes.length} planes nutricionales` : undefined}
        actions={
          puedeGestionar ? (
            <div className="flex flex-wrap justify-end gap-2">
              <button
                type="button"
                onClick={() => setNuevoPlato(true)}
                className="flex shrink-0 items-center gap-1.5 rounded-md border border-border-idle px-3 py-2 font-body text-sm whitespace-nowrap text-text-secondary hover:bg-surface-hover hover:text-text-main"
              >
                <Plus size={16} /> Plato
              </button>
              <PrimaryButton
                label="Nuevo Plan"
                icon={Plus}
                onClick={() => setFormModal({ plan: null })}
              />
            </div>
          ) : undefined
        }
      />

      <div className="space-y-4 p-4 md:p-8">
        {error && (
          <SectionCard>
            <p className="mb-4 font-body text-sm text-status-danger">{error}</p>
            <PrimaryButton label="Reintentar" onClick={recargar} />
          </SectionCard>
        )}

        {!error && !planes && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {[0, 1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-28" />
              ))}
            </div>
            <Skeleton className="h-10 w-full max-w-sm" />
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {[0, 1].map((i) => (
                <Skeleton key={i} className="h-56" />
              ))}
            </div>
          </div>
        )}

        {!error && planes && (
          <>
            {/* Resumen calórico (4 _cal_stat del doc), reusando StatCard. */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <StatCard
                title="Promedio Cal."
                value={`${formatearNumero(resumen.promedio)} kcal`}
                icon={Flame}
                color={colors.accentCoral}
              />
              <StatCard
                title="Plan más bajo"
                value={`${formatearNumero(resumen.minimo)} kcal`}
                icon={TrendingDown}
                color={colors.statusOk}
              />
              <StatCard
                title="Plan más alto"
                value={`${formatearNumero(resumen.maximo)} kcal`}
                icon={TrendingUp}
                color={colors.statusWarn}
              />
              <StatCard
                title="Total asignados"
                value={`${resumen.totalAsignados}`}
                icon={Users}
                color={colors.primaryVolt}
              />
            </div>

            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              {/* Ancho fijo (no flex-1): con flex-1 + un hermano que envuelve
                  en varias líneas (los chips de objetivo), flexbox le daba
                  prioridad al ancho "natural" de los chips y terminaba
                  comprimiendo el buscador a un par de caracteres — ni
                  max-w-sm ni min-w-0 alcanzaban para evitarlo de forma
                  confiable. */}
              <div className="relative w-full sm:w-72">
                <input
                  type="text"
                  value={busqueda}
                  onChange={(e) => setBusqueda(e.target.value)}
                  placeholder="Buscar por nombre o notas…"
                  className="w-full rounded-md border border-border-idle bg-surface-card px-3 py-2 font-body text-sm text-text-main outline-none placeholder:text-text-muted focus:border-border-active"
                />
              </div>
              <div className="flex flex-wrap gap-2">
                {FILTROS.map((f) => (
                  <FilterChip key={f} label={f} activo={filtro === f} onClick={() => setFiltro(f)} />
                ))}
              </div>
            </div>

            {visibles.length === 0 ? (
              <SectionCard>
                <p className="font-body text-sm text-text-muted">
                  {planes.length === 0
                    ? 'Todavía no hay planes nutricionales cargados.'
                    : 'Ningún plan coincide con la búsqueda o el filtro.'}
                </p>
              </SectionCard>
            ) : (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                {visibles.map((plan) => (
                  <PlanCard
                    key={plan.idDieta}
                    plan={plan}
                    puedeGestionar={gestionable(plan)}
                    onVerPlan={() => setDetalle(plan)}
                    onAsignar={() => setAsignando(plan)}
                    onDarDeBaja={() => pedirBaja(plan)}
                    onActivar={() => activar(plan)}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </div>

      {formModal && (
        <PlanFormModal
          plan={formModal.plan}
          onClose={() => setFormModal(null)}
          onGuardado={actualizarEnLista}
        />
      )}

      {detalle && (
        <PlanDetailModal
          plan={detalle}
          puedeGestionar={gestionable(detalle)}
          onClose={() => setDetalle(null)}
          onEditar={() => {
            setFormModal({ plan: detalle });
            setDetalle(null);
          }}
          onAsignar={() => {
            setAsignando(detalle);
            setDetalle(null);
          }}
        />
      )}

      {asignando && (
        <AsignarASocioModal
          titulo="Asignar plan nutricional"
          subtitulo={asignando.nombre}
          aviso="Si el socio ya sigue otro plan, se lo finaliza y queda en su historial."
          mensajeExito={(s) => `"${asignando.nombre}" asignado a ${s.nombreCompleto}`}
          onAsignar={(s) => asignarPlanASocio(asignando.idDieta, s.idSocio)}
          onClose={() => setAsignando(null)}
          onAsignada={recargar}
        />
      )}

      {nuevoPlato && <PlatoFormModal onClose={() => setNuevoPlato(false)} />}
    </div>
  );
}
