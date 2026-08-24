import { useState, type SubmitEvent } from 'react';
import { DollarSign, Hash, Tag } from 'lucide-react';
import { InputField, PrimaryButton, SelectField, type SelectOption } from '../../components/ui';
import { colors } from '../../config';
import { mensajeDeError } from '../../services/api';
import {
  crearPlanActividad,
  actualizarPlanActividad,
  type PlanActividadAdmin,
} from '../../services/actividadService';
import { useAuthStore } from '../../store/authStore';
import { useUiStore } from '../../store/uiStore';

const OPCIONES_TIPO_LIMITE: SelectOption[] = [
  { value: 'POR_MES', label: 'Clases por mes' },
  { value: 'POR_SEMANA', label: 'Veces por semana' },
];

interface PlanFormModalProps {
  idActividad: number;
  /** null = alta nueva. Con un plan, abre en modo edición. */
  plan: PlanActividadAdmin | null;
  onClose: () => void;
  onGuardado: (plan: PlanActividadAdmin) => void;
}

export function PlanFormModal({ idActividad, plan, onClose, onGuardado }: PlanFormModalProps) {
  const [nombre, setNombre] = useState(plan?.nombre ?? '');
  const [tipoLimite, setTipoLimite] = useState<'POR_SEMANA' | 'POR_MES'>(
    plan?.tipoLimite ?? 'POR_MES',
  );
  const [cantidad, setCantidad] = useState(plan ? String(plan.cantidad) : '');
  const [precio, setPrecio] = useState(plan ? String(plan.precio) : '');

  const [guardando, setGuardando] = useState(false);

  const idUsuarioActor = useAuthStore((s) => s.usuario?.id_usuario);
  const showSnack = useUiStore((s) => s.showSnack);

  const handleSubmit = async (e: SubmitEvent) => {
    e.preventDefault();
    setGuardando(true);
    try {
      const datos = { nombre, tipoLimite, cantidad: Number(cantidad), precio: Number(precio) };
      const resultado = plan
        ? await actualizarPlanActividad(plan.idPlanActividad, datos, idUsuarioActor)
        : await crearPlanActividad(idActividad, datos, idUsuarioActor);
      showSnack(plan ? 'Plan actualizado correctamente' : 'Plan creado correctamente', colors.statusOk);
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
          {plan ? 'Editar plan' : 'Nuevo plan'}
        </h2>

        <div className="mt-4 flex flex-col gap-4">
          <InputField label="Nombre" value={nombre} onChange={setNombre} icon={Tag} name="nombre" required />

          <SelectField
            label="Se factura por"
            value={tipoLimite}
            onChange={(v) => setTipoLimite(v as 'POR_SEMANA' | 'POR_MES')}
            options={OPCIONES_TIPO_LIMITE}
            name="tipoLimite"
            required
          />

          <div className="grid grid-cols-2 gap-3">
            <InputField
              label={tipoLimite === 'POR_MES' ? 'Clases al mes' : 'Veces por semana'}
              value={cantidad}
              onChange={setCantidad}
              icon={Hash}
              type="number"
              min={1}
              name="cantidad"
              required
            />
            <InputField
              label="Precio"
              value={precio}
              onChange={setPrecio}
              icon={DollarSign}
              type="number"
              min={0}
              name="precio"
              required
            />
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 rounded-md px-4 py-2 font-body text-sm whitespace-nowrap text-text-secondary hover:text-text-main"
          >
            Cancelar
          </button>
          <PrimaryButton
            label={guardando ? 'Guardando…' : 'Guardar'}
            type="submit"
            disabled={guardando}
          />
        </div>
      </form>
    </div>
  );
}
