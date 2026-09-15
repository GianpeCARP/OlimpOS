import { useState, type SubmitEvent } from 'react';
import { InputField, PrimaryButton } from '../../components/ui';
import { colors } from '../../config';
import { mensajeDeError } from '../../services/api';
import { crearPlato } from '../../services/nutricionService';
import { useUiStore } from '../../store/uiStore';

// Alta de un plato en el catálogo. De acá salen el nombre y las calorías de
// cada comida de un plan; antes no había forma de cargarlo desde ninguna app.
interface PlatoFormModalProps {
  onClose: () => void;
}

export function PlatoFormModal({ onClose }: PlatoFormModalProps) {
  const showSnack = useUiStore((s) => s.showSnack);
  const [nombre, setNombre] = useState('');
  const [calorias, setCalorias] = useState('');
  const [descripcion, setDescripcion] = useState('');
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: SubmitEvent) => {
    e.preventDefault();
    setGuardando(true);
    setError(null);
    try {
      const plato = await crearPlato({
        nombre,
        calorias: calorias.trim() ? Number(calorias) : undefined,
        descripcion,
      });
      showSnack(`"${plato.nombre}" agregado al catálogo`, colors.statusOk);
      onClose();
    } catch (err) {
      setError(mensajeDeError(err));
      setGuardando(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md rounded-lg border border-border-idle bg-surface-card p-6"
      >
        <h2 className="font-heading text-lg font-semibold text-text-main">Nuevo plato</h2>
        <div className="mt-4 flex flex-col gap-4">
          <InputField label="Nombre" value={nombre} onChange={setNombre} name="nombre" required />
          <InputField
            label="Calorías (kcal)"
            value={calorias}
            onChange={setCalorias}
            name="calorias"
            type="number"
            min={0}
            max={5000}
            hint="Opcional. Suma al total del día en el plan."
          />
          <label className="flex flex-col gap-1.5 font-body text-sm">
            <span className="text-text-secondary">Descripción</span>
            <textarea
              value={descripcion}
              onChange={(e) => setDescripcion(e.target.value)}
              rows={2}
              placeholder="Ej: 150 g de pechuga a la plancha + ensalada"
              className="w-full resize-none rounded-md border border-border-idle bg-surface-card px-3 py-2 font-body text-sm text-text-main outline-none placeholder:text-text-muted focus:border-border-active"
            />
          </label>
          {error && <p className="font-body text-sm text-status-danger">{error}</p>}
        </div>
        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 rounded-md px-4 py-2 font-body text-sm whitespace-nowrap text-text-secondary hover:text-text-main"
          >
            Cancelar
          </button>
          <PrimaryButton label={guardando ? 'Guardando…' : 'Agregar plato'} type="submit" disabled={guardando} />
        </div>
      </form>
    </div>
  );
}
