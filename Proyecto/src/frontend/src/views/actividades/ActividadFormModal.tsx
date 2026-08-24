import { useState, type SubmitEvent } from 'react';
import { Clock, DollarSign, Tag, Users } from 'lucide-react';
import { InputField, PrimaryButton } from '../../components/ui';
import { colors } from '../../config';
import { mensajeDeError } from '../../services/api';
import {
  crearActividad,
  actualizarActividad,
  type ActividadAdmin,
} from '../../services/actividadService';
import { useAuthStore } from '../../store/authStore';
import { useUiStore } from '../../store/uiStore';

// Alta/edición de una Actividad del catálogo (especificacion_definitiva_
// actividades.md, Fase 4: "ABM de actividades... cupo, precio, ventana de
// cancelación"). No toca Plan_Actividad — eso vive en PlanFormModal, uno
// por uno, porque una actividad puede tener varios planes y editarlos
// junto con la actividad misma mezclaría dos altas en un solo submit.
interface ActividadFormModalProps {
  /** null = alta nueva. Con una actividad, abre en modo edición. */
  actividad: ActividadAdmin | null;
  onClose: () => void;
  onGuardado: (actividad: ActividadAdmin) => void;
}

export function ActividadFormModal({ actividad, onClose, onGuardado }: ActividadFormModalProps) {
  const [nombre, setNombre] = useState(actividad?.nombre ?? '');
  const [descripcion, setDescripcion] = useState(actividad?.descripcion ?? '');
  const [cupoDefault, setCupoDefault] = useState(
    actividad ? String(actividad.cupoDefault) : '20',
  );
  const [precioClaseSuelta, setPrecioClaseSuelta] = useState(
    actividad ? String(actividad.precioClaseSuelta) : '',
  );
  const [horasAnticipacion, setHorasAnticipacion] = useState(
    actividad ? String(actividad.horasAnticipacionCancelacion) : '0',
  );

  const [guardando, setGuardando] = useState(false);

  const idUsuarioActor = useAuthStore((s) => s.usuario?.id_usuario);
  const showSnack = useUiStore((s) => s.showSnack);

  const handleSubmit = async (e: SubmitEvent) => {
    e.preventDefault();
    setGuardando(true);
    try {
      const datos = {
        nombre,
        descripcion,
        cupoDefault: Number(cupoDefault),
        precioClaseSuelta: Number(precioClaseSuelta),
        horasAnticipacionCancelacion: Number(horasAnticipacion),
      };
      const resultado = actividad
        ? await actualizarActividad(actividad.idActividad, datos, idUsuarioActor)
        : await crearActividad(datos, idUsuarioActor);
      showSnack(
        actividad ? 'Actividad actualizada correctamente' : 'Actividad creada correctamente',
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
          {actividad ? 'Editar actividad' : 'Nueva actividad'}
        </h2>

        <div className="mt-4 flex flex-col gap-4">
          <InputField label="Nombre" value={nombre} onChange={setNombre} icon={Tag} name="nombre" required />

          <label className="flex flex-col gap-1.5 font-body text-sm">
            <span className="text-text-secondary">Descripción</span>
            <textarea
              value={descripcion}
              onChange={(e) => setDescripcion(e.target.value)}
              rows={2}
              maxLength={200}
              placeholder="Ej: Clase de yoga para todos los niveles"
              className="w-full resize-none rounded-md border border-border-idle bg-surface-card px-3 py-2 font-body text-sm text-text-main outline-none placeholder:text-text-muted focus:border-border-active"
            />
          </label>

          <div className="grid grid-cols-2 gap-3">
            <InputField
              label="Cupo por turno"
              value={cupoDefault}
              onChange={setCupoDefault}
              icon={Users}
              type="number"
              min={1}
              name="cupoDefault"
              required
            />
            <InputField
              label="Precio clase suelta"
              value={precioClaseSuelta}
              onChange={setPrecioClaseSuelta}
              icon={DollarSign}
              type="number"
              min={0}
              name="precioClaseSuelta"
              required
            />
          </div>

          <InputField
            label="Horas de anticipación para cancelar"
            value={horasAnticipacion}
            onChange={setHorasAnticipacion}
            icon={Clock}
            type="number"
            min={0}
            hint="0 = se puede cancelar hasta último momento sin perder la clase"
            name="horasAnticipacion"
            required
          />
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
