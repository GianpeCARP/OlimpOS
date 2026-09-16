import { useMemo, useState, type SubmitEvent } from 'react';
import { CalendarDays, Clock, Dumbbell, GraduationCap, Users2 } from 'lucide-react';
import { InputField, PrimaryButton, SelectField, type SelectOption } from '../../components/ui';
import { colors } from '../../config';
import { mensajeDeError } from '../../services/api';
import type { ActividadAdmin, ProfesorAsignable } from '../../services/actividadService';
import { crearHorario, DIAS_SEMANA } from '../../services/turnosService';
import { useUiStore } from '../../store/uiStore';

// Alta de un horario semanal ("Yoga, los lunes 19:00"). Al guardar, el backend
// genera los turnos de las próximas 4 semanas en el acto: quien acaba de
// cargarlo espera verlos, y si aparecieran mañana lo cargaría de nuevo.
//
// El PROFESOR se elige acá y no es un detalle: pasa a cada turno generado, y
// de ahí sale "Mis clases". Un horario sin profesor deja al profesor mirando
// una pantalla vacía aunque esté asignado a la actividad. Sólo se ofrecen los
// asignados a ESA actividad (el backend lo valida igual), y si hay uno solo
// viene elegido.

/** Valor del select para "sin profesor": sala abierta o clase sin nadie fijo. */
const SIN_PROFESOR = '';

interface HorarioFormModalProps {
  actividades: ActividadAdmin[];
  profesoresPorActividad: Map<number, ProfesorAsignable[]>;
  onClose: () => void;
  onGuardado: () => void;
}

function asignadosDe(
  mapa: Map<number, ProfesorAsignable[]>,
  idActividad: number,
): ProfesorAsignable[] {
  return (mapa.get(idActividad) ?? []).filter((p) => p.asignado);
}

export function HorarioFormModal({
  actividades,
  profesoresPorActividad,
  onClose,
  onGuardado,
}: HorarioFormModalProps) {
  const vigentes = useMemo(() => actividades.filter((a) => a.activa), [actividades]);
  const primera = vigentes[0];

  const [idActividad, setIdActividad] = useState(primera ? String(primera.idActividad) : '');
  const [dia, setDia] = useState('1');
  const [hora, setHora] = useState('');
  const [cupo, setCupo] = useState(primera ? String(primera.cupoDefault) : '');
  const [idProfesor, setIdProfesor] = useState(() => {
    const deLaPrimera = primera ? asignadosDe(profesoresPorActividad, primera.idActividad) : [];
    return deLaPrimera.length === 1 ? String(deLaPrimera[0].idProfesor) : SIN_PROFESOR;
  });
  const [guardando, setGuardando] = useState(false);

  const showSnack = useUiStore((s) => s.showSnack);

  const asignados = idActividad ? asignadosDe(profesoresPorActividad, Number(idActividad)) : [];

  // Cambiar de actividad trae su cupo por defecto y su profesor (si tiene uno
  // solo): lo contrario obligaría a reescribir dos campos que casi siempre
  // coinciden con lo que la actividad ya dice.
  const elegirActividad = (valor: string) => {
    setIdActividad(valor);
    const actividad = vigentes.find((a) => String(a.idActividad) === valor);
    if (actividad) setCupo(String(actividad.cupoDefault));
    const deEsa = asignadosDe(profesoresPorActividad, Number(valor));
    setIdProfesor(deEsa.length === 1 ? String(deEsa[0].idProfesor) : SIN_PROFESOR);
  };

  const handleSubmit = async (e: SubmitEvent) => {
    e.preventDefault();
    setGuardando(true);
    try {
      await crearHorario({
        idActividad: Number(idActividad),
        diaSemana: Number(dia),
        hora,
        cupo: Number(cupo),
        idProfesor: idProfesor === SIN_PROFESOR ? null : Number(idProfesor),
      });
      showSnack('Horario creado: ya se generaron sus turnos', colors.statusOk);
      onGuardado();
      onClose();
    } catch (err) {
      showSnack(mensajeDeError(err), colors.statusDanger);
    } finally {
      setGuardando(false);
    }
  };

  const opcionesActividad: SelectOption[] = vigentes.map((a) => ({
    value: String(a.idActividad),
    label: a.nombre,
  }));
  const opcionesDia: SelectOption[] = DIAS_SEMANA.map((nombre, i) => ({
    value: String(i + 1),
    label: nombre,
  }));
  const opcionesProfesor: SelectOption[] = [
    { value: SIN_PROFESOR, label: 'Sin profesor' },
    ...asignados.map((p) => ({ value: String(p.idProfesor), label: p.nombre })),
  ];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <form
        onSubmit={handleSubmit}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md rounded-lg border border-border-idle bg-surface-card p-6"
      >
        <h2 className="font-heading text-lg font-semibold text-text-main">Nuevo horario semanal</h2>
        <p className="mt-1 font-body text-xs text-text-muted">
          Se generan los turnos de las próximas 4 semanas, y se renuevan solos.
        </p>

        {vigentes.length === 0 ? (
          <p className="mt-4 font-body text-sm text-status-warn">
            Primero cargá una actividad: el horario es de una actividad.
          </p>
        ) : (
          <div className="mt-4 flex flex-col gap-4">
            <SelectField
              label="Actividad"
              value={idActividad}
              onChange={elegirActividad}
              options={opcionesActividad}
              icon={Dumbbell}
              name="actividad"
              required
            />
            <div className="grid grid-cols-2 gap-3">
              <SelectField
                label="Día"
                value={dia}
                onChange={setDia}
                options={opcionesDia}
                icon={CalendarDays}
                name="dia"
                required
              />
              <InputField
                label="Hora"
                value={hora}
                onChange={setHora}
                type="time"
                icon={Clock}
                name="hora"
                required
              />
            </div>
            <InputField
              label="Cupo"
              value={cupo}
              onChange={setCupo}
              type="number"
              min={1}
              max={100}
              icon={Users2}
              name="cupo"
              required
            />
            <SelectField
              label="Profesor"
              value={idProfesor}
              onChange={setIdProfesor}
              options={opcionesProfesor}
              icon={GraduationCap}
              name="profesor"
            />
            {asignados.length === 0 && (
              <p className="-mt-2 font-body text-xs text-text-muted">
                Esta actividad no tiene profesores asignados. Asignalos desde su tarjeta para que
                el horario figure en "Mis clases".
              </p>
            )}
          </div>
        )}

        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 rounded-md px-4 py-2 font-body text-sm whitespace-nowrap text-text-secondary hover:text-text-main"
          >
            Cancelar
          </button>
          {vigentes.length > 0 && (
            <PrimaryButton
              label={guardando ? 'Guardando…' : 'Crear y generar turnos'}
              type="submit"
              disabled={guardando}
            />
          )}
        </div>
      </form>
    </div>
  );
}
