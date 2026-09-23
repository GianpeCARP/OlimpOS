import { useState, type SubmitEvent } from 'react';
import { useNavigate } from 'react-router';
import { Cake, ClipboardList, Flag, HeartPulse, House, IdCard, Mail, MapPin, User } from 'lucide-react';
import { InputField, PrimaryButton, TelefonoField } from '../../components/ui';
import { PanelCredenciales } from '../../components/PanelCredenciales';
import { Acceso, colors, Routes } from '../../config';
import { useAccesoSeccion } from '../../hooks/usePermisos';
import { mensajeDeError } from '../../services/api';
import {
  crearSocio,
  actualizarSocio,
  type AltaSocioResultado,
  type SocioListado,
} from '../../services/sociosService';
import { useUiStore } from '../../store/uiStore';

// Equivalente de _open_form/_save_socio (estructura_socios.md), adaptado al
// esquema real: nombre/apellido van separados (así está Persona en
// db/schema.sql).
//
// SE SACÓ EL SELECTOR DE "PLAN" (2026-09-16)
// ------------------------------------------
// El alta dejaba elegir un plan y NO lo guardaba: el service no lo mandaba y el
// backend no tiene ese campo. El socio quedaba sin membresía, y la pantalla
// daba a entender lo contrario. Flet ya lo había sacado por el mismo motivo
// (ver views/socios.py): el plan no es un dato del socio, es una Membresía, y
// se crea COBRÁNDOLA.
//
// Lo que reemplaza al selector es mejor que el selector: al terminar el alta,
// el panel de credenciales ofrece "Cobrar ahora", que abre Cobros con este
// socio ya elegido. Ahí están todas las opciones que el alta nunca podía
// tener —método de pago, promoción, comprobante, actividades—, sin volver a
// buscar a la persona.
//
// No hay Modal genérico todavía en components/ui/ — se arma el overlay acá
// mismo, con la misma pinta que ConfirmDialog (fondo negro/60 + card
// centrada).
interface SocioFormModalProps {
  /** null = alta nueva. Con un socio, el formulario abre en modo edición. */
  socio: SocioListado | null;
  onClose: () => void;
  onGuardado: (socio: SocioListado) => void;
}

export function SocioFormModal({ socio, onClose, onGuardado }: SocioFormModalProps) {
  const esEdicion = socio !== null;
  const navigate = useNavigate();
  // "Cobrar ahora" sólo se ofrece a quien puede entrar a Cobros. Hoy son los
  // mismos que dan de alta socios (Dueño y Recepcionista), pero se chequea en
  // vez de asumirlo: un botón que lleva a una pantalla que rebota es peor que
  // no tenerlo.
  const puedeCobrar = useAccesoSeccion(Routes.COBROS) !== Acceso.NINGUNO;

  const [dni, setDni] = useState(socio?.dni ?? '');
  const [nombre, setNombre] = useState(socio?.nombre ?? '');
  const [apellido, setApellido] = useState(socio?.apellido ?? '');
  const [email, setEmail] = useState(socio?.email ?? '');
  const [telefono, setTelefono] = useState(socio?.telefono ?? '');
  // Objetivo y observaciones son columnas de Socio y las pedía sólo Flet. Sin
  // ellas acá, editar desde la PWA las mandaba vacías y las BORRABA (hoy el
  // backend ignora lo que no viene, pero igual hacían falta: el objetivo es el
  // dato con el que el entrenador le arma la rutina).
  const [objetivo, setObjetivo] = useState(socio?.objetivo ?? '');
  const [observaciones, setObservaciones] = useState(socio?.observaciones ?? '');
  // Datos personales: los pedía el esquema desde siempre y ninguna pantalla
  // los preguntaba. Van en el alta (con la persona enfrente) y en la edición,
  // NO al cobrar: el cobro es otra conversación.
  const [fechaNacimiento, setFechaNacimiento] = useState(socio?.fechaNacimiento ?? '');
  const [calle, setCalle] = useState(socio?.calle ?? '');
  const [numeroCalle, setNumeroCalle] = useState(socio?.numeroCalle ?? '');
  const [localidad, setLocalidad] = useState(socio?.localidad ?? '');
  const [emergenciaNombre, setEmergenciaNombre] = useState(socio?.emergenciaNombre ?? '');
  const [emergenciaTelefono, setEmergenciaTelefono] = useState(socio?.emergenciaTelefono ?? '');
  const [emergenciaParentesco, setEmergenciaParentesco] = useState(
    socio?.emergenciaParentesco ?? '',
  );
  const datosPersonales = {
    fechaNacimiento,
    calle,
    numeroCalle,
    localidad,
    emergenciaNombre,
    emergenciaTelefono,
    emergenciaParentesco,
  };
  // Tope del input de fecha: nadie nace mañana. El backend lo valida igual,
  // porque con el teclado se puede escribir cualquier cosa.
  const hoy = new Date();
  const hoyIso = `${hoy.getFullYear()}-${String(hoy.getMonth() + 1).padStart(2, '0')}-${String(hoy.getDate()).padStart(2, '0')}`;

  const [guardando, setGuardando] = useState(false);
  // Las credenciales del alta. Mientras hay, el modal muestra el panel de
  // entrega en vez del formulario (mismo patrón que EmpleadoFormModal).
  const [alta, setAlta] = useState<AltaSocioResultado | null>(null);

  const showSnack = useUiStore((s) => s.showSnack);

  const handleSubmit = async (e: SubmitEvent) => {
    e.preventDefault();
    setGuardando(true);
    try {
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
          objetivo,
          observaciones,
          datosPersonales,
        });
        showSnack('Socio actualizado correctamente', colors.statusOk);
        onGuardado(actualizado);
        onClose();
        return;
      }

      const resultado = await crearSocio({
        dni, nombre, apellido, email, telefono, objetivo, observaciones, datosPersonales,
      });
      // La tabla se actualiza YA, aunque el modal siga abierto con las
      // credenciales: el socio existe desde este momento.
      onGuardado(resultado.socio);

      if (resultado.username && resultado.passwordTemporal) {
        // Antes esto era un snack persistente con la clave adentro, que había
        // que copiar a mano. Ahora es el mismo panel del alta de personal,
        // con los botones para mandarla por mail o WhatsApp.
        setAlta(resultado);
      } else {
        showSnack(resultado.mensaje, colors.statusOk);
        onClose();
      }
    } catch (err) {
      showSnack(mensajeDeError(err), colors.statusDanger);
    } finally {
      setGuardando(false);
    }
  };

  if (alta?.username && alta.passwordTemporal) {
    return (
      <PanelCredenciales
        titulo="Socio dado de alta"
        mensaje={alta.mensaje}
        username={alta.username}
        passwordTemporal={alta.passwordTemporal}
        textoCredenciales={alta.textoCredenciales}
        emailEnviado={alta.emailEnviado}
        email={email.trim()}
        telefono={telefono.trim()}
        onClose={onClose}
        accionPrincipal={
          puedeCobrar
            ? {
                label: 'Cobrar ahora',
                // El socio viaja en la URL y no en memoria: así Cobros no
                // depende de esta pantalla, y un F5 no pierde a quién se le
                // estaba cobrando. Cobros lo lee, lo elige y limpia la URL.
                onClick: () => {
                  onClose();
                  navigate(`/${Routes.COBROS}?socio=${alta.socio.idSocio}`);
                },
              }
            : undefined
        }
      />
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <form
        onSubmit={handleSubmit}
        className="max-h-[90dvh] w-full max-w-lg overflow-y-auto overscroll-contain rounded-lg border border-border-idle bg-surface-card p-6"
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
          <TelefonoField label="Teléfono" value={telefono} onChange={setTelefono} name="telefono" />

          <InputField
            label="Fecha de nacimiento"
            value={fechaNacimiento}
            onChange={setFechaNacimiento}
            icon={Cake}
            type="date"
            min="1900-01-01"
            max={hoyIso}
            name="fechaNacimiento"
          />

          <p className="-mb-2 font-body text-xs font-semibold tracking-wide text-text-muted uppercase">
            Domicilio
          </p>
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2">
              <InputField label="Calle" value={calle} onChange={setCalle} icon={House} name="calle" />
            </div>
            <InputField label="Número" value={numeroCalle} onChange={setNumeroCalle} name="numeroCalle" />
          </div>
          <InputField label="Localidad" value={localidad} onChange={setLocalidad} icon={MapPin} name="localidad" />

          <p className="-mb-2 font-body text-xs font-semibold tracking-wide text-text-muted uppercase">
            En el gimnasio
          </p>
          <InputField
            label="Objetivo"
            value={objetivo}
            onChange={setObjetivo}
            icon={Flag}
            hint="Ej: bajar de peso, ganar masa muscular"
            name="objetivo"
          />
          <InputField
            label="Observaciones"
            value={observaciones}
            onChange={setObservaciones}
            icon={ClipboardList}
            hint="Notas del mostrador. Las lesiones y condiciones van en la ficha médica."
            name="observaciones"
          />

          <p className="-mb-2 font-body text-xs font-semibold tracking-wide text-text-muted uppercase">
            Contacto de emergencia
          </p>
          <div className="grid grid-cols-2 gap-3">
            <InputField
              label="Nombre"
              value={emergenciaNombre}
              onChange={setEmergenciaNombre}
              icon={HeartPulse}
              name="emergenciaNombre"
            />
            <InputField
              label="Parentesco"
              value={emergenciaParentesco}
              onChange={setEmergenciaParentesco}
              hint="Ej: madre, pareja"
              name="emergenciaParentesco"
            />
          </div>
          <TelefonoField
            label="Teléfono de emergencia"
            value={emergenciaTelefono}
            onChange={setEmergenciaTelefono}
            name="emergenciaTelefono"
          />

          {!esEdicion && (
            <p className="font-body text-xs text-text-muted">
              El plan no se elige acá: se cobra. Al guardar vas a poder ir a Cobros con este
              socio ya seleccionado.
            </p>
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
