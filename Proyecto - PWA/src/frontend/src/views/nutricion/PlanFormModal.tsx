import { useEffect, useMemo, useState, type SubmitEvent } from 'react';
import { Copy, Plus, Trash2, X } from 'lucide-react';
import { InputField, PrimaryButton, SelectField, type SelectOption } from '../../components/ui';
import { colors, ObjetivoDieta, type ObjetivoDietaValue } from '../../config';
import { mensajeDeError } from '../../services/api';
import {
  actualizarPlan,
  crearPlan,
  listarComidasDelPlan,
  listarNutricionistasActivos,
  listarPlatos,
  type ComidaInput,
  type PlanListado,
  type PlatoCatalogo,
} from '../../services/nutricionService';
import { useUiStore } from '../../store/uiStore';
import { formatearNumero } from '../../utils/format';

// Alta y edición de un plan nutricional CON su plan alimentario: las comidas
// de cada día (1 a 7), cada una con su momento y un plato del catálogo o texto
// libre. Espejo de RutinaFormModal: al guardar se manda el plan entero y en
// edición el backend reemplaza el anterior.
//
// En mobile ocupa la pantalla entera; desde `md` es un modal centrado.
//
// Sin campos de macros (no existen en el esquema) y con selector de
// "Nutricionista a cargo" porque Dieta.id_nutricionista es NOT NULL. A un
// Nutricionista el backend le devuelve sólo a sí mismo en ese selector.

interface PlanFormModalProps {
  /** null = alta nueva. Con un plan, abre en modo edición. */
  plan: PlanListado | null;
  onClose: () => void;
  onGuardado: (plan: PlanListado) => void;
}

interface ItemComida {
  clave: number;
  dia: number;
  momento: string;
  /** '' = texto libre. */
  idPlato: string;
  texto: string;
}

const OPCIONES_OBJETIVO: SelectOption[] = Object.values(ObjetivoDieta).map((objetivo) => ({
  value: objetivo,
  label: objetivo,
}));

// Los mismos momentos que ordena el backend (ORDEN_MOMENTOS en nutricion.py).
const MOMENTOS = ['Desayuno', 'Media mañana', 'Almuerzo', 'Merienda', 'Cena', 'Colación'];
const DIAS = [1, 2, 3, 4, 5, 6, 7];

// Clave estable para React (sin crypto.randomUUID: no existe en HTTP por IP).
let siguienteClave = 1;

export function PlanFormModal({ plan, onClose, onGuardado }: PlanFormModalProps) {
  const [nombre, setNombre] = useState(plan?.nombre ?? '');
  const [objetivo, setObjetivo] = useState<ObjetivoDietaValue>(
    plan?.objetivo ?? ObjetivoDieta.MANTENIMIENTO,
  );
  const [caloriasDiarias, setCaloriasDiarias] = useState(
    plan?.caloriasDiarias !== undefined ? String(plan.caloriasDiarias) : '2000',
  );
  const [descripcion, setDescripcion] = useState(plan?.descripcion ?? '');
  const [idNutricionista, setIdNutricionista] = useState(plan ? String(plan.idNutricionista) : '');
  const [nutricionistas, setNutricionistas] = useState<SelectOption[] | null>(null);

  const [platos, setPlatos] = useState<PlatoCatalogo[]>([]);
  const [items, setItems] = useState<ItemComida[]>([]);
  const [dia, setDia] = useState(1);
  const [cargandoComidas, setCargandoComidas] = useState(plan !== null);

  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const showSnack = useUiStore((s) => s.showSnack);

  const idDieta = plan?.idDieta ?? null;
  const idNutriPlan = plan?.idNutricionista ?? null;
  const nombreNutriPlan = plan?.nutricionista ?? '';

  useEffect(() => {
    let cancelado = false;
    listarNutricionistasActivos()
      .then((lista) => {
        if (cancelado) return;
        const opciones = lista.map((n) => ({ value: String(n.idNutricionista), label: n.nombre }));
        // Si el nutricionista del plan en edición ya no está activo, se suma
        // igual para no reemplazarlo en silencio al guardar.
        if (idNutriPlan !== null && !lista.some((n) => n.idNutricionista === idNutriPlan)) {
          opciones.push({ value: String(idNutriPlan), label: `${nombreNutriPlan} (inactivo)` });
        }
        setNutricionistas(opciones);
        // En alta el <select> ya muestra la primera opción: sin sincronizar
        // el estado, crear sin tocarlo mandaba un id vacío.
        if (idNutriPlan === null && lista.length > 0) {
          setIdNutricionista((actual) => actual || String(lista[0].idNutricionista));
        }
      })
      .catch((err: unknown) => {
        if (!cancelado) setError(mensajeDeError(err));
      });
    listarPlatos()
      .then((lista) => {
        if (!cancelado) setPlatos(lista);
      })
      .catch(() => undefined); // sin catálogo igual se puede cargar texto libre
    return () => {
      cancelado = true;
    };
  }, [idNutriPlan, nombreNutriPlan]);

  useEffect(() => {
    if (idDieta === null) return;
    let cancelado = false;
    listarComidasDelPlan(idDieta)
      .then((comidas) => {
        if (cancelado) return;
        setItems(
          comidas.map((c) => ({
            clave: siguienteClave++,
            dia: c.dia ?? 1,
            momento: c.momento ?? MOMENTOS[0],
            idPlato: c.idCatalogoComida ? String(c.idCatalogoComida) : '',
            texto: c.idCatalogoComida ? '' : c.nombre,
          })),
        );
        setCargandoComidas(false);
      })
      .catch((err: unknown) => {
        if (!cancelado) setError(mensajeDeError(err));
      });
    return () => {
      cancelado = true;
    };
  }, [idDieta]);

  const platoPorId = useMemo(() => new Map(platos.map((p) => [String(p.idCatalogoComida), p])), [platos]);
  const opcionesPlato: SelectOption[] = useMemo(
    () => [
      { value: '', label: 'Texto libre…' },
      ...platos.map((p) => ({
        value: String(p.idCatalogoComida),
        label: p.calorias !== undefined ? `${p.nombre} (${formatearNumero(p.calorias)} kcal)` : p.nombre,
      })),
    ],
    [platos],
  );

  const delDia = items.filter((i) => i.dia === dia);
  const kcalDelDia = (d: number) =>
    items
      .filter((i) => i.dia === d && i.idPlato)
      .reduce((total, i) => total + (platoPorId.get(i.idPlato)?.calorias ?? 0), 0);

  const agregar = () => {
    const usados = delDia.length;
    setItems((xs) => [
      ...xs,
      {
        clave: siguienteClave++,
        dia,
        momento: MOMENTOS[Math.min(usados, MOMENTOS.length - 1)],
        idPlato: '',
        texto: '',
      },
    ]);
  };

  const cambiar = (clave: number, campo: 'momento' | 'idPlato' | 'texto', valor: string) =>
    setItems((xs) => xs.map((i) => (i.clave === clave ? { ...i, [campo]: valor } : i)));

  const quitar = (clave: number) => setItems((xs) => xs.filter((i) => i.clave !== clave));

  /** Copia las comidas del día actual a los otros seis (reemplaza lo que tuvieran). */
  const copiarATodos = () => {
    const base = items.filter((i) => i.dia === dia);
    setItems([
      ...base,
      ...DIAS.filter((d) => d !== dia).flatMap((d) =>
        base.map((i) => ({ ...i, clave: siguienteClave++, dia: d })),
      ),
    ]);
    showSnack(`Día ${dia} copiado a los demás días`, colors.statusOk);
  };

  const handleSubmit = async (e: SubmitEvent) => {
    e.preventDefault();
    setError(null);

    const incompleta = items.find((i) => !i.idPlato && !i.texto.trim());
    if (incompleta) {
      setDia(incompleta.dia);
      setError(`Día ${incompleta.dia}: una comida (${incompleta.momento}) no tiene plato ni descripción.`);
      return;
    }
    const comidas: ComidaInput[] = items.map((i) => ({
      dia: i.dia,
      momento: i.momento,
      idCatalogoComida: i.idPlato ? Number(i.idPlato) : undefined,
      descripcion: i.idPlato ? undefined : i.texto.trim().slice(0, 200),
    }));

    setGuardando(true);
    try {
      const input = {
        nombre,
        objetivo,
        caloriasDiarias: Number(caloriasDiarias),
        descripcion,
        idNutricionista: Number(idNutricionista),
        comidas,
      };
      const resultado = plan ? await actualizarPlan(plan.idDieta, input) : await crearPlan(input);
      showSnack(plan ? 'Plan actualizado correctamente' : 'Plan nutricional creado correctamente', colors.statusOk);
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
            {plan ? 'Editar plan' : 'Nuevo plan nutricional'}
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
              label="Objetivo"
              value={objetivo}
              onChange={(v) => setObjetivo(v as ObjetivoDietaValue)}
              options={OPCIONES_OBJETIVO}
              name="objetivo"
              required
            />
            <InputField
              label="Calorías diarias"
              value={caloriasDiarias}
              onChange={setCaloriasDiarias}
              name="calorias_diarias"
              type="number"
              min={800}
              max={6000}
              hint="Entre 800 y 6000 kcal/día"
              required
            />
            <div className="sm:col-span-2">
              <SelectField
                label="Nutricionista a cargo"
                value={idNutricionista}
                onChange={setIdNutricionista}
                options={nutricionistas ?? []}
                name="nutricionista"
                required
              />
            </div>
            <label className="flex flex-col gap-1.5 font-body text-sm sm:col-span-2">
              <span className="text-text-secondary">Notas adicionales</span>
              <textarea
                value={descripcion}
                onChange={(e) => setDescripcion(e.target.value)}
                rows={2}
                placeholder="Ej: Sin lactosa, evitar frituras"
                className="w-full resize-none rounded-md border border-border-idle bg-surface-card px-3 py-2 font-body text-sm text-text-main outline-none placeholder:text-text-muted focus:border-border-active"
              />
            </label>
          </div>

          {/* ── Plan alimentario por día ─────────────────────────────── */}
          <div className="space-y-3">
            <p className="font-heading text-sm font-semibold text-text-main">Plan alimentario</p>

            <div className="flex flex-wrap gap-2">
              {DIAS.map((d) => {
                const cantidad = items.filter((i) => i.dia === d).length;
                return (
                  <button
                    key={d}
                    type="button"
                    onClick={() => setDia(d)}
                    className={`shrink-0 rounded-full px-3 py-1.5 font-body text-sm whitespace-nowrap ring-1 ${
                      d === dia
                        ? 'bg-primary-volt text-surface-base ring-primary-volt'
                        : 'bg-surface-base text-text-secondary ring-border-idle'
                    }`}
                  >
                    Día {d}
                    {cantidad > 0 && <span className="ml-1 opacity-70">({cantidad})</span>}
                  </button>
                );
              })}
            </div>

            {kcalDelDia(dia) > 0 && (
              <p className="font-body text-xs text-text-muted">
                Día {dia}: {formatearNumero(kcalDelDia(dia))} kcal con platos del catálogo
                {Number(caloriasDiarias) > 0 && ` (objetivo ${formatearNumero(Number(caloriasDiarias))})`}
              </p>
            )}

            {cargandoComidas ? (
              <p className="font-body text-sm text-text-muted">Cargando comidas…</p>
            ) : delDia.length === 0 ? (
              <p className="rounded-lg border border-dashed border-border-idle px-4 py-6 text-center font-body text-sm text-text-muted">
                El Día {dia} todavía no tiene comidas.
              </p>
            ) : (
              delDia.map((it) => (
                <div key={it.clave} className="space-y-2 rounded-lg bg-surface-base p-3 ring-1 ring-border-idle">
                  <div className="flex items-end gap-2">
                    <div className="w-36 shrink-0">
                      <SelectField
                        label="Momento"
                        value={it.momento}
                        onChange={(v) => cambiar(it.clave, 'momento', v)}
                        options={MOMENTOS.map((m) => ({ value: m, label: m }))}
                      />
                    </div>
                    <div className="min-w-0 flex-1">
                      <SelectField
                        label="Plato"
                        value={it.idPlato}
                        onChange={(v) => cambiar(it.clave, 'idPlato', v)}
                        options={opcionesPlato}
                      />
                    </div>
                    <button
                      type="button"
                      onClick={() => quitar(it.clave)}
                      aria-label="Quitar comida"
                      className="mb-1.5 shrink-0 rounded-md p-1.5 text-text-muted hover:text-status-danger"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                  {!it.idPlato && (
                    <input
                      type="text"
                      value={it.texto}
                      onChange={(e) => cambiar(it.clave, 'texto', e.target.value)}
                      maxLength={200}
                      placeholder="Ej: 2 huevos revueltos + tostada integral"
                      className="w-full rounded-md bg-surface-card px-3 py-2 font-body text-sm text-text-main outline-none ring-1 ring-border-idle placeholder:text-text-muted focus:ring-primary-volt"
                    />
                  )}
                </div>
              ))
            )}

            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={agregar}
                disabled={cargandoComidas}
                className="flex flex-1 items-center justify-center gap-2 rounded-lg border border-border-idle py-3 font-body text-sm font-medium whitespace-nowrap text-text-secondary hover:bg-surface-hover disabled:opacity-40"
              >
                <Plus size={16} /> Agregar comida al Día {dia}
              </button>
              {delDia.length > 0 && (
                <button
                  type="button"
                  onClick={copiarATodos}
                  className="flex shrink-0 items-center justify-center gap-2 rounded-lg border border-border-idle px-4 py-3 font-body text-sm whitespace-nowrap text-text-secondary hover:bg-surface-hover"
                >
                  <Copy size={16} /> Copiar a todos los días
                </button>
              )}
            </div>
            {platos.length === 0 && (
              <p className="font-body text-xs text-text-muted">
                El catálogo de platos está vacío: podés escribir cada comida como texto libre o
                cargar platos con "+ Plato".
              </p>
            )}
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
            label={guardando ? 'Guardando…' : plan ? 'Guardar' : 'Crear Plan'}
            type="submit"
            disabled={guardando || nutricionistas === null || cargandoComidas}
          />
        </footer>
      </form>
    </div>
  );
}
