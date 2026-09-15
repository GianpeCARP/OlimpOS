import { useEffect, useState, type SubmitEvent } from 'react';
import { X } from 'lucide-react';
import { InputField, PrimaryButton, SelectField, type SelectOption } from '../../components/ui';
import { colors, NivelRutina, type NivelRutinaValue } from '../../config';
import { mensajeDeError } from '../../services/api';
import type { EjercicioCatalogo } from '../../services/socioService';
import {
  actualizarRutina,
  crearRutina,
  listarEjercicios,
  listarEntrenadoresActivos,
  obtenerRutina,
  type RutinaListado,
} from '../../services/rutinasService';
import { useUiStore } from '../../store/uiStore';
import { EditorEjercicios } from './EditorEjercicios';
import { armarEjercicios, nuevoItem, type ItemEjercicio } from './planillaEjercicios';

// Alta y edición de una rutina CON sus ejercicios, elegidos del catálogo y
// organizados por día (ver EditorEjercicios). Al guardar se manda la planilla
// entera; en edición el backend reemplaza la anterior por esta.
//
// El entrenador lo usa mucho desde el celular (anda por el salón), así que en
// mobile ocupa la pantalla entera y desde `md` es un modal centrado.
//
// "Objetivo" hace de descripción (Rutina no tiene esa columna) y el selector
// de entrenador existe porque Rutina.id_entrenador es NOT NULL. A un
// Entrenador el backend le devuelve sólo a sí mismo en ese selector.

interface RutinaFormModalProps {
  /** null = alta nueva. Con una rutina, abre en modo edición. */
  rutina: RutinaListado | null;
  onClose: () => void;
  onGuardado: (rutina: RutinaListado) => void;
}

const OPCIONES_NIVEL: SelectOption[] = Object.values(NivelRutina).map((nivel) => ({
  value: nivel,
  label: nivel,
}));

export function RutinaFormModal({ rutina, onClose, onGuardado }: RutinaFormModalProps) {
  const [nombre, setNombre] = useState(rutina?.nombre ?? '');
  const [nivel, setNivel] = useState<NivelRutinaValue>(rutina?.nivel ?? NivelRutina.PRINCIPIANTE);
  const [diasPorSemana, setDiasPorSemana] = useState(String(rutina?.diasPorSemana ?? 3));
  const [objetivo, setObjetivo] = useState(rutina?.objetivo ?? '');
  const [idEntrenador, setIdEntrenador] = useState(rutina ? String(rutina.idEntrenador) : '');
  const [entrenadores, setEntrenadores] = useState<SelectOption[] | null>(null);

  const [items, setItems] = useState<ItemEjercicio[]>([]);
  const [catalogo, setCatalogo] = useState<EjercicioCatalogo[] | null>(null);
  const [errorCatalogo, setErrorCatalogo] = useState<string | null>(null);
  // En edición los ejercicios se piden al abrir: el listado de rutinas no los trae.
  const [cargandoEjercicios, setCargandoEjercicios] = useState(rutina !== null);

  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const showSnack = useUiStore((s) => s.showSnack);

  const idRutina = rutina?.idRutina ?? null;
  const idEntrenadorRutina = rutina?.idEntrenador ?? null;
  const nombreEntrenadorRutina = rutina?.entrenador ?? '';

  useEffect(() => {
    let cancelado = false;
    listarEntrenadoresActivos()
      .then((lista) => {
        if (cancelado) return;
        const opciones = lista.map((e) => ({ value: String(e.idEntrenador), label: e.nombre }));
        // En edición, si el entrenador de la rutina ya no está activo, se suma
        // igual como opción para no reemplazarlo en silencio al guardar.
        if (idEntrenadorRutina !== null && !lista.some((e) => e.idEntrenador === idEntrenadorRutina)) {
          opciones.push({
            value: String(idEntrenadorRutina),
            label: `${nombreEntrenadorRutina} (inactivo)`,
          });
        }
        setEntrenadores(opciones);
        // En alta el <select> ya muestra la primera opción: sin sincronizar el
        // estado, crear sin tocarlo mandaba un id vacío.
        if (idEntrenadorRutina === null && lista.length > 0) {
          setIdEntrenador((actual) => actual || String(lista[0].idEntrenador));
        }
      })
      .catch((err: unknown) => {
        if (!cancelado) setError(mensajeDeError(err));
      });
    return () => {
      cancelado = true;
    };
  }, [idEntrenadorRutina, nombreEntrenadorRutina]);

  useEffect(() => {
    let cancelado = false;
    listarEjercicios()
      .then((c) => {
        if (!cancelado) setCatalogo(c);
      })
      .catch((err: unknown) => {
        if (!cancelado) setErrorCatalogo(mensajeDeError(err));
      });
    return () => {
      cancelado = true;
    };
  }, []);

  useEffect(() => {
    if (idRutina === null) return;
    let cancelado = false;
    obtenerRutina(idRutina)
      .then((r) => {
        if (cancelado) return;
        setItems(r.ejercicios.map(nuevoItem));
        setCargandoEjercicios(false);
      })
      .catch((err: unknown) => {
        if (!cancelado) setError(mensajeDeError(err));
      });
    return () => {
      cancelado = true;
    };
  }, [idRutina]);

  const dias = Math.min(7, Math.max(1, Math.trunc(Number(diasPorSemana)) || 1));

  const handleSubmit = async (e: SubmitEvent) => {
    e.preventDefault();
    setError(null);

    let ejercicios;
    try {
      ejercicios = armarEjercicios(items, dias);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      return;
    }

    setGuardando(true);
    try {
      const input = {
        nombre,
        nivel,
        diasPorSemana: dias,
        objetivo,
        idEntrenador: Number(idEntrenador),
        ejercicios,
      };
      const resultado = rutina
        ? await actualizarRutina(rutina.idRutina, input)
        : await crearRutina(input);
      showSnack(
        rutina ? 'Rutina actualizada correctamente' : 'Rutina creada correctamente',
        colors.statusOk,
      );
      onGuardado(resultado);
      onClose();
    } catch (err) {
      setError(mensajeDeError(err));
    } finally {
      setGuardando(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex bg-surface-base md:items-center md:justify-center md:bg-black/60 md:p-4">
      <form
        onSubmit={handleSubmit}
        className="flex h-full w-full flex-col bg-surface-card md:h-auto md:max-h-[90vh] md:max-w-2xl md:rounded-lg md:border md:border-border-idle"
      >
        <header className="flex shrink-0 items-center justify-between border-b border-border-idle px-5 py-4">
          <h2 className="font-heading text-lg font-semibold text-text-main">
            {rutina ? 'Editar rutina' : 'Nueva rutina'}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar"
            className="rounded-md p-1.5 text-text-muted hover:bg-surface-hover hover:text-text-main"
          >
            <X size={18} />
          </button>
        </header>

        <div className="min-h-0 flex-1 space-y-6 overflow-y-auto overscroll-contain px-5 py-5">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <InputField label="Nombre" value={nombre} onChange={setNombre} name="nombre" required />
            </div>
            <SelectField
              label="Nivel"
              value={nivel}
              onChange={(v) => setNivel(v as NivelRutinaValue)}
              options={OPCIONES_NIVEL}
              name="nivel"
              required
            />
            <InputField
              label="Días por semana"
              value={diasPorSemana}
              onChange={setDiasPorSemana}
              name="dias_por_semana"
              type="number"
              min={1}
              max={7}
              hint="Entre 1 y 7"
              required
            />
            <div className="sm:col-span-2">
              <SelectField
                label="Entrenador a cargo"
                value={idEntrenador}
                onChange={setIdEntrenador}
                options={entrenadores ?? []}
                name="entrenador"
                required
              />
            </div>
            <label className="flex flex-col gap-1.5 font-body text-sm sm:col-span-2">
              <span className="text-text-secondary">Objetivo</span>
              <textarea
                value={objetivo}
                onChange={(e) => setObjetivo(e.target.value)}
                rows={2}
                maxLength={100}
                placeholder="Ej: Ganancia de fuerza general"
                className="w-full resize-none rounded-md border border-border-idle bg-surface-card px-3 py-2 font-body text-sm text-text-main outline-none placeholder:text-text-muted focus:border-border-active"
              />
            </label>
          </div>

          <div className="space-y-3">
            <p className="font-heading text-sm font-semibold text-text-main">Ejercicios</p>
            <EditorEjercicios
              items={items}
              setItems={setItems}
              dias={dias}
              catalogo={catalogo}
              errorCatalogo={errorCatalogo}
              cargando={cargandoEjercicios}
            />
          </div>

          {error && <p className="font-body text-sm text-status-danger">{error}</p>}
        </div>

        <footer className="flex shrink-0 justify-end gap-3 border-t border-border-idle px-5 pt-3 pb-5">
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 rounded-md px-4 py-2 font-body text-sm whitespace-nowrap text-text-secondary hover:text-text-main"
          >
            Cancelar
          </button>
          <PrimaryButton
            label={guardando ? 'Guardando…' : rutina ? 'Guardar' : 'Crear Rutina'}
            type="submit"
            disabled={guardando || entrenadores === null || cargandoEjercicios}
          />
        </footer>
      </form>
    </div>
  );
}
