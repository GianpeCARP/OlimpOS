import { useState, type SubmitEvent } from 'react';
import { Award, IdCard, Mail, Phone, User } from 'lucide-react';
import { InputField, PrimaryButton, SelectField, type SelectOption } from '../../components/ui';
import {
  colors,
  RolEmpleado,
  TurnoLaboral,
  type RolEmpleadoValue,
} from '../../config';
import { mensajeDeError } from '../../services/api';
import {
  crearEmpleado,
  actualizarEmpleado,
  type EmpleadoListado,
} from '../../services/personalService';
import { useUiStore, SNACK_PERSISTENTE } from '../../store/uiStore';

// Equivalente de _open_form/_save (estructura_personal.md), adaptado al
// esquema real. El doc tiene un campo "turno" fijo para todos; acá el
// último campo cambia según el rol, porque en la base cada rol guarda una
// cosa distinta: turno_laboral el recepcionista, especialidad el entrenador
// y titulo el nutricionista.

const OPCIONES_ROL: SelectOption[] = Object.values(RolEmpleado).map((rol) => ({
  value: rol,
  label: rol,
}));

const OPCIONES_TURNO: SelectOption[] = Object.values(TurnoLaboral).map((turno) => ({
  value: turno,
  label: turno,
}));

/** Etiqueta y tipo de control del campo específico de cada rol. */
const CAMPO_POR_ROL: Record<RolEmpleadoValue, { label: string; select: boolean }> = {
  [RolEmpleado.ENTRENADOR]: { label: 'Especialidad', select: false },
  [RolEmpleado.NUTRICIONISTA]: { label: 'Título', select: false },
  [RolEmpleado.RECEPCIONISTA]: { label: 'Turno', select: true },
  [RolEmpleado.PROFESOR]: { label: 'Especialidad', select: false },
};

interface EmpleadoFormModalProps {
  /** null = alta nueva. Con un empleado, abre en modo edición. */
  empleado: EmpleadoListado | null;
  onClose: () => void;
  onGuardado: (empleado: EmpleadoListado) => void;
}

export function EmpleadoFormModal({ empleado, onClose, onGuardado }: EmpleadoFormModalProps) {
  const [dni, setDni] = useState(empleado?.dni ?? '');
  const [nombre, setNombre] = useState(empleado?.nombre ?? '');
  const [apellido, setApellido] = useState(empleado?.apellido ?? '');
  const [email, setEmail] = useState(empleado?.email ?? '');
  const [telefono, setTelefono] = useState(empleado?.telefono ?? '');
  const [rol, setRol] = useState<RolEmpleadoValue>(empleado?.rol ?? RolEmpleado.ENTRENADOR);
  // En recepcionistas `detalle` viene como "Turno Mañana" (listo para
  // mostrar) pero el valor que se edita es el turno pelado.
  const [detalle, setDetalle] = useState(empleado?.turno ?? empleado?.detalle ?? '');

  const [guardando, setGuardando] = useState(false);

  const showSnack = useUiStore((s) => s.showSnack);

  const campo = CAMPO_POR_ROL[rol];

  // Cambiar de rol vacía el campo específico: un turno no tiene sentido
  // como especialidad, ni al revés.
  const cambiarRol = (nuevo: string) => {
    setRol(nuevo as RolEmpleadoValue);
    setDetalle('');
  };

  const handleSubmit = async (e: SubmitEvent) => {
    e.preventDefault();
    setGuardando(true);
    try {
      const datos = { dni, nombre, apellido, email, telefono, rol, detalle };

      if (empleado) {
        const actualizado = await actualizarEmpleado(empleado.idEmpleado, datos);
        showSnack('Empleado actualizado correctamente', colors.statusOk);
        onGuardado(actualizado);
      } else {
        const alta = await crearEmpleado(datos);
        // Las credenciales se muestran UNA vez: el backend guarda solo el
        // hash. Un Profesor no recibe ninguna —no inicia sesión— y en ese
        // caso el backend lo explica en `mensaje`.
        if (alta.passwordTemporal) {
          showSnack(
            `Empleado creado. Usuario: ${alta.username} — Contraseña temporal: ` +
              `${alta.passwordTemporal} (anotala, no se vuelve a mostrar)`,
            colors.statusOk,
            SNACK_PERSISTENTE,
          );
        } else {
          showSnack(alta.mensaje, colors.statusOk);
        }
        onGuardado(alta.empleado);
      }

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
          {empleado ? 'Editar empleado' : 'Nuevo empleado'}
        </h2>

        <div className="mt-4 flex flex-col gap-4">
          {/* El DNI identifica a la persona: se carga al alta y no se edita. */}
          {empleado ? (
            <p className="font-body text-sm text-text-secondary">
              DNI <span className="text-text-main">{dni}</span>
              {empleado.legajo && (
                <>
                  {' · Legajo '}
                  <span className="text-text-main">{empleado.legajo}</span>
                </>
              )}
            </p>
          ) : (
            <InputField label="DNI" value={dni} onChange={setDni} icon={IdCard} name="dni" required />
          )}

          <div className="grid grid-cols-2 gap-3">
            <InputField label="Nombre" value={nombre} onChange={setNombre} icon={User} name="nombre" required />
            <InputField label="Apellido" value={apellido} onChange={setApellido} name="apellido" required />
          </div>

          <InputField label="Email" value={email} onChange={setEmail} icon={Mail} type="email" name="email" />
          <InputField label="Teléfono" value={telefono} onChange={setTelefono} icon={Phone} type="tel" name="telefono" />

          <SelectField
            label="Rol"
            value={rol}
            onChange={cambiarRol}
            options={OPCIONES_ROL}
            name="rol"
            required
          />

          {campo.select ? (
            <SelectField
              label={campo.label}
              value={detalle}
              onChange={setDetalle}
              options={OPCIONES_TURNO}
              placeholder="Sin turno asignado"
              name="detalle"
            />
          ) : (
            <InputField
              label={campo.label}
              value={detalle}
              onChange={setDetalle}
              icon={Award}
              name="detalle"
            />
          )}
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
            label={guardando ? 'Guardando…' : 'Guardar'}
            type="submit"
            disabled={guardando}
          />
        </div>
      </form>
    </div>
  );
}
