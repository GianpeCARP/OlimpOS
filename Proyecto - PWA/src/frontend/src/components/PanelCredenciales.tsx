import { Mail, MessageCircle } from 'lucide-react';
import { PrimaryButton } from './ui';
import { colors } from '../config';
import { useUiStore } from '../store/uiStore';
import { linkMail, linkWhatsapp } from '../utils/contacto';

// Entrega de una contraseña temporal recién generada.
//
// Nació dentro de EmpleadoFormModal, para el alta. Se sacó acá porque el
// RESETEO de contraseña necesita exactamente lo mismo y estaba resuelto peor:
// mostraba la clave en un snack persistente, o sea que quien la reseteaba
// tenía que copiarla a mano de un cartelito antes de cerrarlo. Los dos casos
// son el mismo problema —una contraseña que existe UNA sola vez y hay que
// hacerle llegar a alguien— así que ahora son la misma pantalla.
//
// El texto lo arma el BACKEND (`texto_credenciales`, de notificaciones.py), el
// mismo que manda por mail: así la persona lee lo mismo por donde le llegue, y
// la advertencia de que la contraseña es de un solo uso no depende de que cada
// pantalla se acuerde de incluirla.

/** Asunto del mail de credenciales. Gemelo de app/views/personal.py en Flet. */
export const ASUNTO_CREDENCIALES = 'Tus datos de acceso a OlimpOS';

interface PanelCredencialesProps {
  /** "Empleado dado de alta", "Contraseña reseteada"… */
  titulo: string;
  /** Lo que contestó el backend. */
  mensaje: string;
  username: string;
  passwordTemporal: string;
  /** El mensaje ya armado por el backend. Si no viene, se arma uno mínimo. */
  textoCredenciales?: string;
  emailEnviado?: boolean;
  /** Vacío si la persona no tiene: entonces no se ofrece esa vía. */
  email: string;
  telefono: string;
  onClose: () => void;
}

export function PanelCredenciales({
  titulo,
  mensaje,
  username,
  passwordTemporal,
  textoCredenciales,
  emailEnviado,
  email,
  telefono,
  onClose,
}: PanelCredencialesProps) {
  const showSnack = useUiStore((s) => s.showSnack);
  const texto =
    textoCredenciales ?? `Usuario: ${username} — Contraseña temporal: ${passwordTemporal}`;

  const copiar = () => {
    navigator.clipboard
      .writeText(texto)
      .then(() => showSnack('Mensaje copiado', colors.statusOk))
      .catch(() => showSnack('No se pudo copiar; seleccioná el texto a mano.', colors.statusDanger));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-md rounded-lg border border-border-idle bg-surface-card p-6">
        <h2 className="font-heading text-lg font-semibold text-text-main">{titulo}</h2>
        <p className="mt-2 font-body text-sm text-text-secondary">{mensaje}</p>

        <div className="mt-4 rounded-md border border-border-idle bg-surface-hover p-3">
          <p className="font-body text-xs text-text-muted">Usuario</p>
          <p className="font-mono text-sm text-text-main">{username}</p>
          <p className="mt-2 font-body text-xs text-text-muted">Contraseña temporal</p>
          <p className="font-mono text-sm text-primary-volt select-all">{passwordTemporal}</p>
        </div>

        {emailEnviado && (
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
              // Pestaña nueva, y acá no es un detalle: abre el redactor de
              // Gmail, y si se llevara puesta esta pantalla se perdería la
              // contraseña temporal, que se muestra UNA sola vez.
              target="_blank"
              rel="noreferrer"
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
