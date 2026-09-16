import { useState, type ReactNode } from 'react';
import { AlertTriangle, CalendarClock, UserX } from 'lucide-react';
import { PrimaryButton } from '../../components/ui';
import { EstadoSocio } from '../../config';
import type { SocioListado } from '../../services/sociosService';
import { formatearFecha } from '../../utils/format';
import { parsearFecha } from '../../utils/fechas';

// La baja de un socio desde el personal, con la opción de CUÁNDO.
//
// Por defecto la baja respeta lo que pagó: con la cuota paga queda programada
// para el día siguiente al vencimiento (backend/bajas.py). "Ahora" existe para
// el caso excepcional —una expulsión— y dice con todas las letras que pierde
// los días que le quedaban, porque es la única forma de que alguien la elija
// sabiendo lo que hace.
//
// Sin cuota paga no hay nada que elegir: la baja es inmediata igual, y el modal
// se reduce a la confirmación de siempre.

/** Estados en los que el socio tiene un período pago corriendo (o en pausa). */
const CON_CUOTA_PAGA = new Set<string>([
  EstadoSocio.ACTIVO,
  EstadoSocio.POR_VENCER,
  EstadoSocio.EN_PAUSA,
  EstadoSocio.SUSPENDIDO,
]);

interface BajaSocioModalProps {
  socio: SocioListado;
  onClose: () => void;
  onConfirmar: (inmediata: boolean) => void;
}

export function BajaSocioModal({ socio, onClose, onConfirmar }: BajaSocioModalProps) {
  // Con baja ya programada, lo único que se puede pedir acá es adelantarla.
  const yaProgramada = Boolean(socio.bajaProgramada);
  const hayQueElegir = CON_CUOTA_PAGA.has(socio.estado) && !yaProgramada;
  const [inmediata, setInmediata] = useState(yaProgramada);

  const vence = socio.vencimiento ? formatearFecha(parsearFecha(socio.vencimiento)) : null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md rounded-lg border border-border-idle bg-surface-card p-6"
      >
        <h2 className="font-heading text-lg font-semibold text-text-main">
          {yaProgramada ? 'Adelantar la baja' : `¿Dar de baja a ${socio.nombreCompleto}?`}
        </h2>
        <p className="mt-1 font-body text-sm text-text-secondary">
          {yaProgramada
            ? `Tiene la baja programada para el ${formatearFecha(parsearFecha(socio.bajaProgramada!))}. Podés hacerla efectiva hoy.`
            : 'La ficha no se borra: queda su historial y se puede reactivar.'}
        </p>

        {hayQueElegir && (
          <div className="mt-4 flex flex-col gap-2">
            <Opcion
              elegida={!inmediata}
              onElegir={() => setInmediata(false)}
              icono={<CalendarClock size={16} className="text-primary-volt" />}
              titulo={vence ? `Al vencer la cuota (${vence})` : 'Al vencer la cuota'}
              detalle="Sigue entrenando hasta el vencimiento: no pierde los días que pagó. Hasta entonces se puede anular."
            />
            <Opcion
              elegida={inmediata}
              onElegir={() => setInmediata(true)}
              icono={<UserX size={16} className="text-status-danger" />}
              titulo="Ahora"
              detalle="Corta hoy y pierde el acceso a la app. Pierde los días de cuota que le quedaban, sin devolución."
            />
          </div>
        )}

        {(inmediata || !hayQueElegir) && (
          <p className="mt-4 flex items-start gap-2 font-body text-xs text-status-danger">
            <AlertTriangle size={14} className="mt-0.5 shrink-0" />
            {hayQueElegir || yaProgramada
              ? 'Pierde los días de cuota que le quedaban.'
              : 'Deja de figurar como activo y pierde el acceso a la app.'}
          </p>
        )}

        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 rounded-md px-4 py-2 font-body text-sm whitespace-nowrap text-text-secondary hover:text-text-main"
          >
            Cancelar
          </button>
          <PrimaryButton
            label={inmediata || !hayQueElegir ? 'Dar de baja ahora' : 'Programar la baja'}
            onClick={() => onConfirmar(inmediata)}
          />
        </div>
      </div>
    </div>
  );
}

function Opcion({
  elegida,
  onElegir,
  icono,
  titulo,
  detalle,
}: {
  elegida: boolean;
  onElegir: () => void;
  icono: ReactNode;
  titulo: string;
  detalle: string;
}) {
  return (
    <button
      type="button"
      onClick={onElegir}
      className={`flex items-start gap-3 rounded-md border p-3 text-left transition-colors ${
        elegida ? 'border-primary-volt bg-primary-volt/5' : 'border-border-idle hover:border-border-active'
      }`}
    >
      <span className="mt-0.5 shrink-0">{icono}</span>
      <span className="min-w-0">
        <span className="block font-body text-sm text-text-main">{titulo}</span>
        <span className="block font-body text-xs text-text-muted">{detalle}</span>
      </span>
    </button>
  );
}
