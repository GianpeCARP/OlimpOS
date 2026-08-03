import { useEffect, useState, type SubmitEvent } from 'react';
import { InputField, PrimaryButton, SelectField, type SelectOption } from '../../components/ui';
import { colors, ObjetivoDieta, type ObjetivoDietaValue } from '../../config';
import { mensajeDeError } from '../../services/api';
import {
  crearPlan,
  actualizarPlan,
  listarNutricionistasActivos,
  type PlanInput,
  type PlanListado,
} from '../../services/nutricionService';
import { useAuthStore } from '../../store/authStore';
import { useUiStore } from '../../store/uiStore';

// Equivalente de _open_form/_save (estructura_nutricion.md), con las
// diferencias explicadas en nutricionService.ts: sin campos de macros (no
// existen en el esquema) y con un selector de "Nutricionista a cargo" que
// el doc no pedía pero Dieta.id_nutricionista exige (NOT NULL).
interface PlanFormModalProps {
  /** null = alta nueva. Con un plan, abre en modo edición. */
  plan: PlanListado | null;
  onClose: () => void;
  onGuardado: (plan: PlanListado) => void;
}

const OPCIONES_OBJETIVO: SelectOption[] = Object.values(ObjetivoDieta).map((objetivo) => ({
  value: objetivo,
  label: objetivo,
}));

export function PlanFormModal({ plan, onClose, onGuardado }: PlanFormModalProps) {
  const [nombre, setNombre] = useState(plan?.nombre ?? '');
  const [objetivo, setObjetivo] = useState<ObjetivoDietaValue>(
    plan?.objetivo ?? ObjetivoDieta.MANTENIMIENTO,
  );
  const [caloriasDiarias, setCaloriasDiarias] = useState(
    plan?.caloriasDiarias !== undefined ? String(plan.caloriasDiarias) : '2000',
  );
  const [descripcion, setDescripcion] = useState(plan?.descripcion ?? '');
  const [idNutricionista, setIdNutricionista] = useState(
    plan ? String(plan.idNutricionista) : '',
  );

  const [nutricionistas, setNutricionistas] = useState<SelectOption[] | null>(null);
  const [guardando, setGuardando] = useState(false);

  const idUsuarioActor = useAuthStore((s) => s.usuario?.id_usuario);
  const showSnack = useUiStore((s) => s.showSnack);

  useEffect(() => {
    let cancelado = false;
    listarNutricionistasActivos().then((lista) => {
      if (cancelado) return;
      setNutricionistas(lista.map((n) => ({ value: String(n.idNutricionista), label: n.nombre })));
      // En alta nueva, el <select> del navegador ya muestra la primera
      // opción marcada apenas se renderiza (así funciona un <select> sin
      // placeholder vacío) — pero el estado de React seguía en '' porque
      // nada lo había sincronizado. Sin esto, crear un plan sin tocar el
      // dropdown mandaba idNutricionista='' y el service rechazaba con
      // "El nutricionista a cargo no existe" aunque en pantalla se viera
      // uno seleccionado.
      if (!plan && lista.length > 0) {
        setIdNutricionista((actual) => actual || String(lista[0].idNutricionista));
      }
      // Mismo criterio: si el nutricionista del plan en edición ya no está
      // activo, se agrega igual para no reemplazarlo en silencio por otra
      // persona al guardar.
      if (plan && !lista.some((n) => n.idNutricionista === plan.idNutricionista)) {
        setNutricionistas((actual) => [
          ...(actual ?? []),
          { value: String(plan.idNutricionista), label: `${plan.nutricionista} (inactivo)` },
        ]);
      }
    });
    return () => {
      cancelado = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSubmit = async (e: SubmitEvent) => {
    e.preventDefault();
    setGuardando(true);
    try {
      const input: PlanInput = {
        nombre,
        objetivo,
        caloriasDiarias: Number(caloriasDiarias),
        descripcion,
        idNutricionista: Number(idNutricionista),
      };
      const resultado = plan
        ? await actualizarPlan(plan.idDieta, input, idUsuarioActor)
        : await crearPlan(input, idUsuarioActor);
      showSnack(
        plan ? 'Plan actualizado correctamente' : 'Plan nutricional creado correctamente',
        colors.statusOk,
      );
      onGuardado(resultado);
      onClose();
    } catch (err) {
      showSnack(mensajeDeError(err), colors.statusDanger);
    } finally {
      setGuardando(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md rounded-lg border border-border-idle bg-surface-card p-6"
      >
        <h2 className="font-heading text-lg font-semibold text-text-main">
          {plan ? 'Editar plan' : 'Nuevo plan nutricional'}
        </h2>

        <div className="mt-4 flex flex-col gap-4">
          <InputField label="Nombre" value={nombre} onChange={setNombre} name="nombre" required />

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

          <SelectField
            label="Nutricionista a cargo"
            value={idNutricionista}
            onChange={setIdNutricionista}
            options={nutricionistas ?? []}
            name="nutricionista"
            required
          />

          <label className="flex flex-col gap-1.5 font-body text-sm">
            <span className="text-text-secondary">Notas adicionales</span>
            <textarea
              value={descripcion}
              onChange={(e) => setDescripcion(e.target.value)}
              rows={3}
              placeholder="Ej: Sin lactosa, evitar frituras"
              className="w-full resize-none rounded-md border border-border-idle bg-surface-card px-3 py-2 font-body text-sm text-text-main outline-none placeholder:text-text-muted focus:border-border-active"
            />
          </label>
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md px-4 py-2 font-body text-sm text-text-secondary hover:text-text-main"
          >
            Cancelar
          </button>
          <PrimaryButton
            label={guardando ? 'Guardando…' : plan ? 'Guardar' : 'Crear Plan'}
            type="submit"
            disabled={guardando || nutricionistas === null}
          />
        </div>
      </form>
    </div>
  );
}
