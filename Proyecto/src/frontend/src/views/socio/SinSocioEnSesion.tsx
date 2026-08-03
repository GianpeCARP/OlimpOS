import { AlertTriangle } from 'lucide-react';
import { SectionCard, Topbar } from '../../components/ui';
import { colors } from '../../config';

/**
 * Estado de error compartido por las seis vistas del portal: la sesión tiene
 * rol de socio pero no trae `idSocio`.
 *
 * No debería pasar nunca — el rol `socio` se deriva de tener una fila Socio,
 * así que una cosa implica la otra. Pero "no debería pasar nunca" es
 * exactamente lo que termina mostrando una pantalla en blanco cuando pasa,
 * y sin este cartel el síntoma sería un perfil con todos los campos vacíos:
 * el socio pensaría que perdió sus datos en vez de que hay un problema de
 * cuenta. Prefiero un mensaje que mande a recepción.
 *
 * Vive suelto en su propio archivo porque las seis vistas hacen el mismo
 * chequeo antes de pedir datos.
 */
export function SinSocioEnSesion({ titulo }: { titulo: string }) {
  return (
    <div>
      <Topbar title={titulo} />
      <div className="p-8">
        <SectionCard>
          <div className="flex items-start gap-3">
            <AlertTriangle size={18} color={colors.statusWarn} className="mt-0.5 shrink-0" />
            <div>
              <p className="font-body text-sm text-text-main">
                Tu cuenta no está asociada a una ficha de socio.
              </p>
              <p className="mt-1 font-body text-sm text-text-secondary">
                Acercate a recepción así lo resuelven — no es algo que puedas arreglar desde acá.
              </p>
            </div>
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
