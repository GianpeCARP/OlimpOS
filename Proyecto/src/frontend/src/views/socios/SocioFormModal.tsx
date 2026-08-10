import { useEffect, useState, type SubmitEvent } from 'react';
import { IdCard, Mail, Phone, User } from 'lucide-react';
import { InputField, PrimaryButton, SelectField, type SelectOption } from '../../components/ui';
import { colors } from '../../config';
import { mensajeDeError } from '../../services/api';
import {
  crearSocio,
  actualizarSocio,
  listarTiposMembresia,
  type SocioListado,
} from '../../services/sociosService';
import type { TipoMembresia } from '../../types';
import { formatearMoneda } from '../../utils/format';
import { useUiStore, SNACK_PERSISTENTE } from '../../store/uiStore';

// Equivalente de _open_form/_save_socio (estructura_socios.md), adaptado al
// esquema real: el doc pide un solo campo "nombre" y un plan de 3 opciones
// fijas (Básico/Premium/Anual); acá nombre/apellido van separados (así está
// Persona en db/schema.sql) y el plan sale de Tipo_Membresia, no de un
// literal inventado.
//
// No hay Modal genérico todavía en components/ui/ — se arma el overlay acá
// mismo, con la misma pinta que ConfirmDialog (fondo negro/60 + card
// centrada), porque es el único lugar que hoy necesita un formulario dentro
// de un diálogo.
interface SocioFormModalProps {
  /** null = alta nueva. Con un socio, el formulario abre en modo edición. */
  socio: SocioListado | null;
  onClose: () => void;
  onGuardado: (socio: SocioListado) => void;
}

export function SocioFormModal({ socio, onClose, onGuardado }: SocioFormModalProps) {
  const esEdicion = socio !== null;

  const [dni, setDni] = useState(socio?.dni ?? '');
  const [nombre, setNombre] = useState(socio?.nombre ?? '');
  const [apellido, setApellido] = useState(socio?.apellido ?? '');
  const [email, setEmail] = useState(socio?.email ?? '');
  const [telefono, setTelefono] = useState(socio?.telefono ?? '');
  const [idTipoMembresia, setIdTipoMembresia] = useState(
    socio?.idTipoMembresia !== undefined ? String(socio.idTipoMembresia) : '',
  );

  const [planes, setPlanes] = useState<TipoMembresia[] | null>(null);
  const [guardando, setGuardando] = useState(false);

  const showSnack = useUiStore((s) => s.showSnack);

  useEffect(() => {
    let cancelado = false;
    listarTiposMembresia().then((lista) => {
      if (!cancelado) setPlanes(lista);
    });
    return () => {
      cancelado = true;
    };
  }, []);

  const opcionesPlan: SelectOption[] =
    planes?.map((plan) => ({
      value: String(plan.id_tipo_membresia),
      label: `${plan.nombre} — ${formatearMoneda(plan.precio_actual)}`,
    })) ?? [];

  const handleSubmit = async (e: SubmitEvent) => {
    e.preventDefault();
    setGuardando(true);
    try {
      const idTipoMembresiaNum = idTipoMembresia === '' ? undefined : Number(idTipoMembresia);

      if (socio) {
        // Editar NO toca la membresía: cambiar de plan es una acción con
        // cobro asociado y va por la sección Cobros. Ver el comentario en
        // sociosService.actualizarSocio — hacerlo acá regalaba renovaciones
        // de 30 días cada vez que alguien corregía un teléfono.
        const actualizado = await actualizarSocio(socio.idSocio, {
          nombre,
          apellido,
          email,
          telefono,
        });
        showSnack('Socio actualizado correctamente', colors.statusOk);
        onGuardado(actualizado);
      } else {
        const alta = await crearSocio({
          dni,
          nombre,
          apellido,
          email,
          telefono,
          idTipoMembresia: idTipoMembresiaNum,
        });

        // Las credenciales se muestran UNA sola vez: el backend guarda solo
        // el hash, así que si el operador no las copia ahora hay que
        // resetearlas. Por eso el mensaje no se cierra solo.
        if (alta.passwordTemporal) {
          showSnack(
            `Socio creado. Usuario: ${alta.username} — Contraseña temporal: ` +
              `${alta.passwordTemporal} (anotala, no se vuelve a mostrar)`,
            colors.statusOk,
            SNACK_PERSISTENTE,
          );
        } else {
          showSnack(alta.mensaje, colors.statusOk);
        }
        onGuardado(alta.socio);
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
          {esEdicion ? 'Editar socio' : 'Nuevo socio'}
        </h2>

        <div className="mt-4 flex flex-col gap-4">
          {/* El DNI es la identidad de la persona: se carga una sola vez al
              alta y no se vuelve a tocar desde acá. */}
          {esEdicion ? (
            <p className="font-body text-sm text-text-secondary">
              DNI <span className="text-text-main">{dni}</span>
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

          {/* El plan solo se elige en el ALTA. Al editar no aparece porque
              cambiar de plan implica un cobro y va por la sección Cobros:
              dejarlo acá prometía algo que este formulario ya no hace. */}
          {!esEdicion && (
            <SelectField
              label="Plan"
              value={idTipoMembresia}
              onChange={setIdTipoMembresia}
              options={opcionesPlan}
              placeholder="Sin plan asignado"
              name="plan"
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
            disabled={guardando || planes === null}
          />
        </div>
      </form>
    </div>
  );
}
