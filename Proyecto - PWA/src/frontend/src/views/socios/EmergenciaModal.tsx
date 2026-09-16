import { HeartPulse, MessageCircle, Phone, X } from 'lucide-react';
import type { SocioListado } from '../../services/sociosService';
import { linkWhatsapp, soloDigitos } from '../../utils/contacto';

// El contacto de emergencia de un socio, a un toque de la grilla.
//
// No existía en ninguna pantalla del personal: el dato se cargaba (el socio
// desde "Mi perfil") y nadie del gimnasio podía verlo, que es exactamente
// cuando hace falta. Muestra el número GRANDE —si la PC no puede llamar, alguien
// lo marca en su celular— y ofrece llamar (tel:, que en un celular marca solo)
// y WhatsApp.

interface EmergenciaModalProps {
  socio: SocioListado;
  onClose: () => void;
}

export function EmergenciaModal({ socio, onClose }: EmergenciaModalProps) {
  const telefono = socio.emergenciaTelefono;

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
            <HeartPulse size={18} className="shrink-0 text-status-danger" />
            <h2 className="truncate font-heading text-lg font-semibold text-text-main">
              Contacto de emergencia
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 rounded p-1 text-text-muted hover:text-text-main"
          >
            <X size={16} />
          </button>
        </div>
        <p className="mt-1 font-body text-xs text-text-muted">De {socio.nombreCompleto}</p>

        {!telefono ? (
          <p className="mt-4 font-body text-sm text-text-secondary">
            No tiene un contacto de emergencia cargado. Se carga desde "Editar socio", o lo
            completa el socio en su perfil.
          </p>
        ) : (
          <>
            <div className="mt-4 rounded-md border border-border-idle bg-surface-base/40 p-4">
              <p className="font-body text-sm text-text-main">
                {socio.emergenciaNombre}
                {socio.emergenciaParentesco && (
                  <span className="text-text-muted"> · {socio.emergenciaParentesco}</span>
                )}
              </p>
              <p className="mt-1 font-mono text-2xl font-bold text-primary-volt">{telefono}</p>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <a
                href={`tel:${soloDigitos(telefono)}`}
                className="inline-flex shrink-0 items-center justify-center gap-2 rounded-md bg-status-danger px-3 py-2 font-body text-sm font-semibold whitespace-nowrap text-white hover:opacity-90"
              >
                <Phone size={14} /> Llamar
              </a>
              <a
                href={linkWhatsapp(telefono)}
                target="_blank"
                rel="noreferrer"
                className="inline-flex shrink-0 items-center justify-center gap-2 rounded-md border border-border-idle px-3 py-2 font-body text-sm whitespace-nowrap text-text-main hover:border-primary-volt"
              >
                <MessageCircle size={14} /> WhatsApp
              </a>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
