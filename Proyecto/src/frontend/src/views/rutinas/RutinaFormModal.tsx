import { useEffect, useState, type SubmitEvent } from 'react';
import { InputField, PrimaryButton, SelectField, type SelectOption } from '../../components/ui';
import { colors, NivelRutina, type NivelRutinaValue } from '../../config';
import { mensajeDeError } from '../../services/api';
import {
  crearRutina,
  actualizarRutina,
  listarEntrenadoresActivos,
  type RutinaInput,
  type RutinaListado,
} from '../../services/rutinasService';
import { useAuthStore } from '../../store/authStore';
import { useUiStore } from '../../store/uiStore';

// Equivalente de _open_form/_save (estructura_rutinas.md), con dos
// diferencias explicadas en rutinasService.ts: "objetivo" hace de
// descripción (Rutina no tiene esa columna) y hay un selector de
// "Entrenador a cargo" que el doc no pedía pero Rutina.id_entrenador exige
// (NOT NULL en el esquema).
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
  const [idEntrenador, setIdEntrenador] = useState(
    rutina ? String(rutina.idEntrenador) : '',
  );

  const [entrenadores, setEntrenadores] = useState<SelectOption[] | null>(null);
  const [guardando, setGuardando] = useState(false);

  const idUsuarioActor = useAuthStore((s) => s.usuario?.id_usuario);
  const showSnack = useUiStore((s) => s.showSnack);

  useEffect(() => {
    let cancelado = false;
    listarEntrenadoresActivos().then((lista) => {
      if (cancelado) return;
      setEntrenadores(lista.map((e) => ({ value: String(e.idEntrenador), label: e.nombre })));
      // En alta nueva, el <select> ya muestra la primera opción marcada
      // apenas se renderiza, pero el estado de React seguía en '' porque
      // nada lo había sincronizado — crear sin tocar el dropdown mandaba
      // idEntrenador='' y el service rechazaba con "El entrenador a cargo
      // no existe" aunque en pantalla se viera uno seleccionado.
      if (!rutina && lista.length > 0) {
        setIdEntrenador((actual) => actual || String(lista[0].idEntrenador));
      }
      // En edición, si el entrenador de la rutina ya no está activo, se
      // agrega igual como opción (deshabilitada la comparación no aplica a
      // <select>, así que directamente se suma a la lista) para no
      // reemplazarlo en silencio por otra persona al guardar.
      if (rutina && !lista.some((e) => e.idEntrenador === rutina.idEntrenador)) {
        setEntrenadores((actual) => [
          ...(actual ?? []),
          { value: String(rutina.idEntrenador), label: `${rutina.entrenador} (inactivo)` },
        ]);
      }
    });
    return () => {
      cancelado = true;
    };
    // rutina no cambia mientras el modal está abierto — solo importa la
    // carga inicial.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSubmit = async (e: SubmitEvent) => {
    e.preventDefault();
    setGuardando(true);
    try {
      const input: RutinaInput = {
        nombre,
        nivel,
        diasPorSemana: Number(diasPorSemana),
        objetivo,
        idEntrenador: Number(idEntrenador),
      };
      const resultado = rutina
        ? await actualizarRutina(rutina.idRutina, input, idUsuarioActor)
        : await crearRutina(input, idUsuarioActor);
      showSnack(
        rutina ? 'Rutina actualizada correctamente' : 'Rutina creada correctamente',
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
          {rutina ? 'Editar rutina' : 'Nueva rutina'}
        </h2>

        <div className="mt-4 flex flex-col gap-4">
          <InputField label="Nombre" value={nombre} onChange={setNombre} name="nombre" required />

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

          <SelectField
            label="Entrenador a cargo"
            value={idEntrenador}
            onChange={setIdEntrenador}
            options={entrenadores ?? []}
            name="entrenador"
            required
          />

          <label className="flex flex-col gap-1.5 font-body text-sm">
            <span className="text-text-secondary">Objetivo</span>
            <textarea
              value={objetivo}
              onChange={(e) => setObjetivo(e.target.value)}
              rows={3}
              maxLength={100}
              placeholder="Ej: Ganancia de fuerza general"
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
            label={guardando ? 'Guardando…' : rutina ? 'Guardar' : 'Crear Rutina'}
            type="submit"
            disabled={guardando || entrenadores === null}
          />
        </div>
      </form>
    </div>
  );
}
