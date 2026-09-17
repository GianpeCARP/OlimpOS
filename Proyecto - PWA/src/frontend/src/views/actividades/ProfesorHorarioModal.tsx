import { useState } from 'react';
import { GraduationCap, X } from 'lucide-react';
import { PrimaryButton, SelectField, type SelectOption } from '../../components/ui';
import { colors } from '../../config';
import { mensajeDeError } from '../../services/api';
import { seniaDeProfesor, type ProfesorAsignable } from '../../services/actividadService';
import { cambiarProfesorDeHorario, type Horario } from '../../services/turnosService';
import { useUiStore } from '../../store/uiStore';

// Cambiarle el profesor a un horario YA CREADO.
//
// POR QUÉ EXISTE
// --------------
// El profesor sólo se elegía al crear el horario. Corregirlo obligaba a darlo
// de baja y cargarlo de nuevo, y eso genera turnos nuevos dejando cancelados
// los viejos: arreglar un dato administrativo le volteaba la clase a los que ya
// estaban anotados. Un profesor que se va, una licencia o haberse equivocado al
// cargarlo son cosas normales, no motivo para rehacer el horario.
//
// El cambio ARRASTRA a los turnos futuros (lo hace el backend), porque de ahí
// sale "Mis clases": sin eso el profesor nuevo no vería ninguna de las clases ya
// generadas y el viejo las seguiría viendo todas.

/** Valor del select para "sin profesor": sala abierta o clase sin nadie fijo. */
const SIN_PROFESOR = '';

interface ProfesorHorarioModalProps {
  horario: Horario;
  /** Los asignados a la actividad de ESTE horario: el backend no acepta otros. */
  asignados: ProfesorAsignable[];
  onClose: () => void;
  onGuardado: () => void;
}

export function ProfesorHorarioModal({
  horario,
  asignados,
  onClose,
  onGuardado,
}: ProfesorHorarioModalProps) {
  const showSnack = useUiStore((s) => s.showSnack);

  const [idProfesor, setIdProfesor] = useState(
    horario.idProfesor === null ? SIN_PROFESOR : String(horario.idProfesor),
  );
  const [guardando, setGuardando] = useState(false);

  // Legajo o DNI en la etiqueta: dos homónimos daban dos opciones idénticas.
  const opciones: SelectOption[] = [
    { value: SIN_PROFESOR, label: 'Sin profesor' },
    ...asignados.map((p) => {
      const senia = seniaDeProfesor(p);
      return {
        value: String(p.idProfesor),
        label: senia ? `${p.nombre} · ${senia}` : p.nombre,
      };
    }),
  ];

  const guardar = async () => {
    setGuardando(true);
    try {
      await cambiarProfesorDeHorario(
        horario.idHorario,
        idProfesor === SIN_PROFESOR ? null : Number(idProfesor),
      );
      showSnack('Listo, cambiamos el profesor del horario.', colors.statusOk);
      onGuardado();
      onClose();
    } catch (err) {
      showSnack(mensajeDeError(err), colors.statusDanger);
    } finally {
      setGuardando(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-sm rounded-lg border border-border-idle bg-surface-card p-6"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-center gap-2">
            <GraduationCap size={18} className="shrink-0 text-primary-volt" />
            <h2 className="truncate font-heading text-lg font-semibold text-text-main">
              Profesor del horario
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            title="Cerrar"
            className="shrink-0 rounded p-1 text-text-muted hover:text-text-main"
          >
            <X size={16} />
          </button>
        </div>
        <p className="mt-1 font-body text-xs text-text-muted">
          {horario.actividad} · {horario.diaNombre} {horario.hora}
        </p>

        {asignados.length === 0 ? (
          <p className="mt-4 font-body text-sm text-text-secondary">
            {horario.actividad} no tiene profesores asignados. Asignale uno desde la tarjeta
            de la actividad y volvé acá.
          </p>
        ) : (
          <>
            <div className="mt-4">
              <SelectField
                label="Profesor"
                value={idProfesor}
                onChange={setIdProfesor}
                options={opciones}
                name="idProfesorHorario"
              />
            </div>
            <p className="mt-3 font-body text-xs text-text-muted">
              El cambio también se aplica a los turnos de hoy en adelante que ya estén
              generados. Los que ya pasaron quedan con el profesor que dio esa clase.
            </p>
            <div className="mt-5 flex justify-end">
              <PrimaryButton
                label={guardando ? 'Guardando…' : 'Guardar'}
                onClick={() => void guardar()}
                disabled={guardando}
              />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
