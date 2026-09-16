import { useEffect, useState, type SubmitEvent } from 'react';
import { Award, IdCard, Mail, MessageCircle, Phone, User } from 'lucide-react';
import { InputField, PrimaryButton, SelectField, type SelectOption } from '../../components/ui';
import {
  colors,
  RolEmpleado,
  type RolEmpleadoValue,
} from '../../config';
import { mensajeDeError } from '../../services/api';
import {
  crearEmpleado,
  actualizarEmpleado,
  listarFranjas,
  type AltaEmpleadoResultado,
  type EmpleadoListado,
} from '../../services/personalService';
import { linkMail, linkWhatsapp, limpiarTelefono } from '../../utils/contacto';
import { useUiStore } from '../../store/uiStore';

// Equivalente de _open_form/_save (estructura_personal.md), adaptado al
// esquema real. El doc tiene un campo "turno" fijo para todos; acá el
// último campo cambia según el rol, porque en la base cada rol guarda una
// cosa distinta: turno_laboral el recepcionista, especialidad el entrenador
// y titulo el nutricionista.

const OPCIONES_ROL: SelectOption[] = Object.values(RolEmpleado).map((rol) => ({
  value: rol,
  label: rol,
}));

/** Etiqueta y tipo de control del campo específico de cada rol. */
const CAMPO_POR_ROL: Record<RolEmpleadoValue, { label: string; select: boolean }> = {
  [RolEmpleado.ENTRENADOR]: { label: 'Especialidad', select: false },
  [RolEmpleado.NUTRICIONISTA]: { label: 'Título', select: false },
  [RolEmpleado.RECEPCIONISTA]: { label: 'Turno / franja', select: true },
  [RolEmpleado.PROFESOR]: { label: 'Especialidad', select: false },
};

const ASUNTO_CREDENCIALES = 'Tus datos de acceso a OlimpOS';

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
  // Para recepcionista `detalle` es el ID de la franja (FK Franja_Laboral);
  // para los demás roles es texto libre (especialidad/título).
  const [detalle, setDetalle] = useState(
    empleado
      ? empleado.rol === RolEmpleado.RECEPCIONISTA
        ? (empleado.idFranjaLaboral ? String(empleado.idFranjaLaboral) : '')
        : (empleado.detalle ?? '')
      : '',
  );

  /**
   * Alta recién hecha cuyas credenciales hay que entregar. Mientras tenga
   * valor, el modal muestra el panel de credenciales en lugar del formulario
   * — ver el comentario de `handleSubmit`.
   */
  const [credenciales, setCredenciales] = useState<AltaEmpleadoResultado | null>(null);

  // Catálogo de franjas para el selector de turno del recepcionista.
  const [franjasOpc, setFranjasOpc] = useState<SelectOption[]>([]);
  useEffect(() => {
    listarFranjas()
      .then((fs) => setFranjasOpc(fs.map((f) => ({ value: String(f.idFranjaLaboral), label: f.nombre }))))
      .catch(() => setFranjasOpc([]));
  }, []);

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

    // Mail o teléfono, al menos uno. El backend lo exige igual —es la regla,
    // no una comodidad de esta pantalla— pero avisar acá evita el viaje y
    // señala el problema mientras el formulario está a la vista: un empleado
    // al que nadie sabe cómo contactar no sirve de nada.
    if (!email.trim() && !telefono.trim()) {
      showSnack('Cargá un email o un teléfono: sin una de las dos vías no hay forma de contactarlo.',
        colors.statusDanger);
      return;
    }

    setGuardando(true);
    try {
      const datos = { dni, nombre, apellido, email, telefono, rol, detalle };

      if (empleado) {
        const actualizado = await actualizarEmpleado(empleado.idEmpleado, datos);
        showSnack('Empleado actualizado correctamente', colors.statusOk);
        onGuardado(actualizado);
      } else {
        const alta = await crearEmpleado(datos);
        onGuardado(alta.empleado);

        // Las credenciales se muestran UNA vez: el backend guarda solo el
        // hash. Un Profesor no recibe ninguna —no inicia sesión— y en ese
        // caso el backend lo explica en `mensaje`.
        //
        // Con credenciales el modal NO se cierra: pasa al panel de entrega,
        // desde donde se le mandan por mail o WhatsApp. Antes salían en un
        // snack y había que copiarlas a mano antes de que se fuera.
        if (alta.passwordTemporal) {
          setCredenciales(alta);
          return;
        }
        showSnack(alta.mensaje, colors.statusOk);
      }

      onClose();
    } catch (err) {
      showSnack(mensajeDeError(err), colors.statusDanger);
    } finally {
      setGuardando(false);
    }
  };

  if (credenciales) {
    return (
      <PanelCredenciales
        alta={credenciales}
        email={email.trim()}
        telefono={telefono.trim()}
        onClose={onClose}
      />
    );
  }

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
          {/* El teléfono se filtra mientras se tipea: el campo aceptaba letras
              y el error recién aparecía al guardar el formulario entero. */}
          <InputField
            label="Teléfono"
            value={telefono}
            onChange={(v: string) => setTelefono(limpiarTelefono(v))}
            icon={Phone}
            type="tel"
            name="telefono"
          />
          <p className="-mt-2 font-body text-xs text-text-muted">
            Email o teléfono: al menos uno de los dos, para poder contactarlo.
          </p>

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
              options={franjasOpc}
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

interface PanelCredencialesProps {
  alta: AltaEmpleadoResultado;
  email: string;
  telefono: string;
  onClose: () => void;
}

/**
 * Entrega de las credenciales del empleado recién creado.
 *
 * Reemplaza al "anotala, no se vuelve a mostrar": la contraseña temporal se
 * genera una sola vez y en la base queda el hash, así que hasta acá el alta
 * terminaba con alguien copiando una clave a mano para pasársela por otro
 * lado. Los botones abren el mail o el WhatsApp con el mensaje ya escrito.
 *
 * El texto lo arma el BACKEND (`texto_credenciales`, de notificaciones.py),
 * el mismo que manda por mail: así el empleado lee lo mismo por donde le
 * llegue, y la advertencia de que la contraseña es de un solo uso no depende
 * de que cada pantalla se acuerde de incluirla.
 */
function PanelCredenciales({ alta, email, telefono, onClose }: PanelCredencialesProps) {
  const showSnack = useUiStore((s) => s.showSnack);
  const texto = alta.textoCredenciales
    ?? `Usuario: ${alta.username} — Contraseña temporal: ${alta.passwordTemporal}`;

  const copiar = () => {
    navigator.clipboard
      .writeText(texto)
      .then(() => showSnack('Mensaje copiado', colors.statusOk))
      .catch(() => showSnack('No se pudo copiar; seleccioná el texto a mano.', colors.statusDanger));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-md rounded-lg border border-border-idle bg-surface-card p-6">
        <h2 className="font-heading text-lg font-semibold text-text-main">Empleado dado de alta</h2>
        <p className="mt-2 font-body text-sm text-text-secondary">{alta.mensaje}</p>

        <div className="mt-4 rounded-md border border-border-idle bg-surface-hover p-3">
          <p className="font-body text-xs text-text-muted">Usuario</p>
          <p className="font-mono text-sm text-text-main">{alta.username}</p>
          <p className="mt-2 font-body text-xs text-text-muted">Contraseña temporal</p>
          <p className="font-mono text-sm text-primary-volt select-all">{alta.passwordTemporal}</p>
        </div>

        {alta.emailEnviado && (
          <p className="mt-3 font-body text-xs text-status-ok">
            Ya se le envió un mail a {email} con estos datos.
          </p>
        )}

        <p className="mt-3 font-body text-xs text-status-warn">
          No se puede volver a ver: en la base queda sólo el hash. Mandásela ahora.
        </p>

        <div className="mt-5 flex flex-wrap gap-2">
          {/* El mail va primero cuando existe: queda guardado y buscable, y un
              WhatsApp con una contraseña se pierde en la conversación. Si la
              persona sólo dejó teléfono, WhatsApp es la única vía. */}
          {email && (
            <a
              href={linkMail(email, ASUNTO_CREDENCIALES, texto)}
              className="flex shrink-0 items-center justify-center gap-2 rounded-md border border-border-idle px-3 py-2 font-body text-sm whitespace-nowrap text-text-secondary transition-colors hover:bg-surface-hover hover:text-text-main"
            >
              <Mail size={14} />
              Enviar por mail
            </a>
          )}
          {telefono && (
            <a
              href={linkWhatsapp(telefono, texto)}
              target="_blank"
              rel="noreferrer"
              className="flex shrink-0 items-center justify-center gap-2 rounded-md border border-border-idle px-3 py-2 font-body text-sm whitespace-nowrap text-text-secondary transition-colors hover:bg-surface-hover hover:text-text-main"
            >
              <MessageCircle size={14} />
              Enviar por WhatsApp
            </a>
          )}
          <button
            type="button"
            onClick={copiar}
            className="flex shrink-0 items-center justify-center gap-2 rounded-md border border-border-idle px-3 py-2 font-body text-sm whitespace-nowrap text-text-secondary transition-colors hover:bg-surface-hover hover:text-text-main"
          >
            Copiar mensaje
          </button>
        </div>

        <div className="mt-6 flex justify-end">
          <PrimaryButton label="Listo" onClick={onClose} />
        </div>
      </div>
    </div>
  );
}
