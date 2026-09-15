import { useCallback, useEffect, useMemo, useState } from 'react';
import { Plus } from 'lucide-react';
import { FilterChip, PrimaryButton, SectionCard, Topbar } from '../../components/ui';
import { colors, NivelRutina, type NivelRutinaValue } from '../../config';
import { mensajeDeError } from '../../services/api';
import {
  listarRutinas,
  darDeBajaRutina,
  activarRutina,
  type RutinaListado,
} from '../../services/rutinasService';
import { useUiStore } from '../../store/uiStore';
import { usePuedeAccion } from '../../hooks/usePermisos';
import { AsignarRutinaModal } from './AsignarRutinaModal';
import { EjercicioFormModal } from './EjercicioFormModal';
import { RutinaCard } from './RutinaCard';
import { RutinaDetailModal } from './RutinaDetailModal';
import { RutinaFormModal } from './RutinaFormModal';

// Equivalente de RutinasView (estructura_rutinas.md): topbar con conteo +
// grilla responsiva de tarjetas (1 col mobile, 2 tablet, 3 desktop).
//
// Buscador y chips por nivel son un agregado sobre el doc (que no filtraba
// nada), para mantener consistencia con socios y personal — mismos
// componentes reusados, sin lógica nueva.

type FiltroNivel = NivelRutinaValue | 'Todos';
const FILTROS: FiltroNivel[] = ['Todos', ...Object.values(NivelRutina)];

function Skeleton({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-md bg-surface-hover ${className}`} />;
}

export function RutinasView() {
  const showSnack = useUiStore((s) => s.showSnack);
  const confirmDialog = useUiStore((s) => s.confirmDialog);

  // Sólo el Entrenador gestiona rutinas. El Nutricionista llega hasta acá
  // (tiene lectura, para ver qué rutina tiene un socio) pero sin ningún
  // botón de acción.
  const puedeGestionar = usePuedeAccion('gestionRutinas');

  const [rutinas, setRutinas] = useState<RutinaListado[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intento, setIntento] = useState(0);

  const [busqueda, setBusqueda] = useState('');
  const [filtro, setFiltro] = useState<FiltroNivel>('Todos');

  const [formModal, setFormModal] = useState<{ rutina: RutinaListado | null } | null>(null);
  const [detalle, setDetalle] = useState<RutinaListado | null>(null);
  const [asignando, setAsignando] = useState<RutinaListado | null>(null);
  const [nuevoEjercicio, setNuevoEjercicio] = useState(false);

  useEffect(() => {
    let cancelado = false;
    setRutinas(null);
    setError(null);
    listarRutinas()
      .then((lista) => {
        if (!cancelado) setRutinas(lista);
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
    if (!rutinas) return [];
    const texto = busqueda.trim().toLowerCase();
    return rutinas.filter((r) => {
      const coincideTexto =
        texto === '' ||
        r.nombre.toLowerCase().includes(texto) ||
        (r.objetivo?.toLowerCase().includes(texto) ?? false);
      return coincideTexto && (filtro === 'Todos' || r.nivel === filtro);
    });
  }, [rutinas, busqueda, filtro]);

  const actualizarEnLista = useCallback((actualizada: RutinaListado) => {
    setRutinas((lista) =>
      lista
        ? lista.some((r) => r.idRutina === actualizada.idRutina)
          ? lista.map((r) => (r.idRutina === actualizada.idRutina ? actualizada : r))
          : [...lista, actualizada]
        : lista,
    );
  }, []);

  // Gestionar ESTA rutina: tener la acción y que el backend diga que es
  // editable (un Entrenador ve las de sus colegas pero no las toca).
  const gestionable = useCallback(
    (rutina: RutinaListado) => puedeGestionar && rutina.puedeEditar,
    [puedeGestionar],
  );

  const pedirBaja = useCallback(
    (rutina: RutinaListado) => {
      confirmDialog(
        `¿Dar de baja "${rutina.nombre}"?`,
        'La rutina deja de figurar como activa. Esta acción queda registrada en Auditoría.',
        () => {
          darDeBajaRutina(rutina.idRutina)
            .then(() => {
              showSnack(`"${rutina.nombre}" fue dada de baja`, colors.statusOk);
              recargar();
            })
            .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
        },
      );
    },
    [confirmDialog, showSnack, recargar],
  );

  // Sin diálogo de confirmación: reactivar es una acción de bajo riesgo y
  // reversible (siempre se puede volver a dar de baja), a diferencia de
  // pedirBaja.
  const activar = useCallback(
    (rutina: RutinaListado) => {
      activarRutina(rutina.idRutina)
        .then((actualizada) => {
          showSnack(`"${rutina.nombre}" fue reactivada`, colors.statusOk);
          actualizarEnLista(actualizada);
        })
        .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
    },
    [showSnack, actualizarEnLista],
  );

  return (
    <div>
      <Topbar
        title="Rutinas"
        subtitle={rutinas ? `${rutinas.length} rutinas disponibles` : undefined}
        actions={
          puedeGestionar ? (
            <div className="flex flex-wrap justify-end gap-2">
              <button
                type="button"
                onClick={() => setNuevoEjercicio(true)}
                className="flex shrink-0 items-center gap-1.5 rounded-md border border-border-idle px-3 py-2 font-body text-sm whitespace-nowrap text-text-secondary hover:bg-surface-hover hover:text-text-main"
              >
                <Plus size={16} /> Ejercicio
              </button>
              <PrimaryButton
                label="Nueva Rutina"
                icon={Plus}
                onClick={() => setFormModal({ rutina: null })}
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

        {!error && !rutinas && (
          <div className="space-y-4">
            <Skeleton className="h-10 w-full max-w-sm" />
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {[0, 1, 2].map((i) => (
                <Skeleton key={i} className="h-64" />
              ))}
            </div>
          </div>
        )}

        {!error && rutinas && (
          <>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="relative w-full sm:w-72">
                <input
                  type="text"
                  value={busqueda}
                  onChange={(e) => setBusqueda(e.target.value)}
                  placeholder="Buscar por nombre u objetivo…"
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
                  {rutinas.length === 0
                    ? 'Todavía no hay rutinas cargadas.'
                    : 'Ninguna rutina coincide con la búsqueda o el filtro.'}
                </p>
              </SectionCard>
            ) : (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                {visibles.map((rutina) => (
                  <RutinaCard
                    key={rutina.idRutina}
                    rutina={rutina}
                    puedeGestionar={gestionable(rutina)}
                    onVerDetalle={() => setDetalle(rutina)}
                    onAsignar={() => setAsignando(rutina)}
                    onDarDeBaja={() => pedirBaja(rutina)}
                    onActivar={() => activar(rutina)}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </div>

      {formModal && (
        <RutinaFormModal
          rutina={formModal.rutina}
          onClose={() => setFormModal(null)}
          onGuardado={actualizarEnLista}
        />
      )}

      {detalle && (
        <RutinaDetailModal
          rutina={detalle}
          puedeGestionar={gestionable(detalle)}
          onClose={() => setDetalle(null)}
          onEditar={() => {
            setFormModal({ rutina: detalle });
            setDetalle(null);
          }}
          onAsignar={() => {
            setAsignando(detalle);
            setDetalle(null);
          }}
        />
      )}

      {asignando && (
        <AsignarRutinaModal
          rutina={asignando}
          onClose={() => setAsignando(null)}
          onAsignada={recargar}
        />
      )}

      {nuevoEjercicio && (
        <EjercicioFormModal onClose={() => setNuevoEjercicio(false)} onCreado={() => {}} />
      )}
    </div>
  );
}
