import { useEffect, useMemo, useState } from 'react';
import { PlayCircle, Wrench, X } from 'lucide-react';
import { mensajeDeError } from '../../services/api';
import { listarEjerciciosCatalogo, type EjercicioCatalogo } from '../../services/socioService';
import { Buscador } from '../rutinas/EditorEjercicios';
import { agruparCatalogo } from '../rutinas/planillaEjercicios';
import { VerTecnica } from './VerTecnica';

// Los ejercicios del gimnasio, para mirarlos sueltos: qué es cada uno, cómo se
// hace (descripción + video) y si necesita máquina. No hace falta tener una
// rutina para entrar.
//
// Es un MODO de Mi rutina y no una sección del menú, por el mismo motivo que
// el circuito: las secciones son entradas de la matriz de permisos, copiada en
// tres lugares, y el catálogo ya se expone bajo MI_RUTINA
// (/portal/mi-rutina/ejercicios).

interface CatalogoEjerciciosProps {
  onCerrar: () => void;
  /**
   * De dónde se trae el catálogo. Por defecto, el endpoint del PORTAL
   * (/portal/mi-rutina/ejercicios), que exige la sección MI_RUTINA.
   *
   * Existe porque este componente también lo abre el PERSONAL desde Rutinas,
   * y ahí el del portal contesta 403: el Dueño o el Entrenador no tienen
   * "Mi rutina", que es una pantalla del socio. Rutinas le pasa el endpoint de
   * gestión (/rutinas/ejercicios), que devuelve lo mismo pero exige la sección
   * RUTINAS. Mismo catálogo, dos puertas, cada rol por la suya.
   */
  cargar?: () => Promise<EjercicioCatalogo[]>;
}

export function CatalogoEjercicios({
  onCerrar,
  cargar = listarEjerciciosCatalogo,
}: CatalogoEjerciciosProps) {
  const [catalogo, setCatalogo] = useState<EjercicioCatalogo[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busqueda, setBusqueda] = useState('');
  const [abierto, setAbierto] = useState<number | null>(null);
  const [viendo, setViendo] = useState<EjercicioCatalogo | null>(null);

  useEffect(() => {
    let cancelado = false;
    cargar()
      .then((c) => { if (!cancelado) setCatalogo(c); })
      .catch((e: unknown) => { if (!cancelado) setError(mensajeDeError(e)); });
    return () => { cancelado = true; };
  }, [cargar]);

  const grupos = useMemo(() => agruparCatalogo(catalogo, busqueda), [catalogo, busqueda]);

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-surface-base">
      {viendo?.video && (
        <VerTecnica nombre={viendo.nombre} video={viendo.video} onCerrar={() => setViendo(null)} />
      )}

      <header className="flex shrink-0 items-center justify-between border-b border-border-idle px-4 py-3">
        <p className="font-heading text-lg font-semibold text-text-main">Ejercicios del gimnasio</p>
        <button
          type="button"
          onClick={onCerrar}
          aria-label="Cerrar"
          className="flex size-10 items-center justify-center rounded-full bg-surface-card text-text-main"
        >
          <X size={20} />
        </button>
      </header>

      <div className="shrink-0 px-4 py-3 md:mx-auto md:w-full md:max-w-2xl">
        <Buscador value={busqueda} onChange={setBusqueda} />
      </div>

      <div className="min-h-0 flex-1 space-y-5 overflow-y-auto overscroll-contain px-4 pb-6 md:mx-auto md:w-full md:max-w-2xl">
        {error && <p className="font-body text-sm text-status-danger">{error}</p>}
        {!catalogo && !error && <p className="font-body text-sm text-text-muted">Cargando ejercicios…</p>}
        {catalogo && grupos.length === 0 && (
          <p className="font-body text-sm text-text-muted">
            {catalogo.length === 0 ? 'Todavía no hay ejercicios cargados.' : 'No hay ejercicios que coincidan.'}
          </p>
        )}

        {grupos.map(([grupo, ejercicios]) => (
          <div key={grupo} className="space-y-2">
            <p className="font-body text-xs font-semibold uppercase tracking-wide text-text-muted">{grupo}</p>
            <div className="space-y-1.5">
              {ejercicios.map((e) => {
                const expandido = abierto === e.idEjercicio;
                const tieneDetalle = Boolean(e.descripcion) || e.requiereMaquina;
                return (
                  <div key={e.idEjercicio} className="rounded-lg bg-surface-card ring-1 ring-border-idle">
                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => setAbierto(expandido ? null : e.idEjercicio)}
                        disabled={!tieneDetalle}
                        className="min-w-0 flex-1 px-3 py-2.5 text-left"
                      >
                        <span className="block truncate font-body text-sm text-text-main">{e.nombre}</span>
                        {tieneDetalle && !expandido && (
                          <span className="block font-body text-xs text-text-muted">Tocá para ver cómo se hace</span>
                        )}
                      </button>
                      {e.video && (
                        <button
                          type="button"
                          onClick={() => setViendo(e)}
                          className="mr-2 flex shrink-0 items-center gap-1.5 rounded-md border border-border-idle px-2.5 py-1.5 font-body text-xs whitespace-nowrap text-primary-volt"
                        >
                          <PlayCircle size={14} /> Ver técnica
                        </button>
                      )}
                    </div>
                    {expandido && (
                      <div className="space-y-2 border-t border-border-idle px-3 py-2.5">
                        {e.requiereMaquina && (
                          <p className="flex items-center gap-1.5 font-body text-xs text-text-secondary">
                            <Wrench size={12} /> Requiere máquina
                          </p>
                        )}
                        {e.descripcion && (
                          <p className="font-body text-sm whitespace-pre-line text-text-secondary">
                            {e.descripcion}
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
