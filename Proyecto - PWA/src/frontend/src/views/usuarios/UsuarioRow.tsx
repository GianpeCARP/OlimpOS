import { Ban, KeyRound, Pencil, RotateCcw, Unlock } from 'lucide-react';
import { StatusBadge } from '../../components/ui';
import { EstadoUsuario } from '../../config';
import type { UsuarioListado } from '../../services/usuariosService';
import { RoleChip } from './RoleChip';

// Equivalente de _user_row (estructura_usuarios.md): avatar+nombre+@username
// | chip de rol | badge de estado | botones de acción. El doc pinta cada
// botón de un color fijo (azul, amarillo, rojo/verde); acá siguen el mismo
// criterio que el resto de la app — neutro con hover del color semántico —
// para no romper la consistencia visual con Socios/Personal/Rutinas/
// Nutrición.
//
// El tercer botón tiene 3 variantes en vez de 2 (a diferencia de las otras
// vistas): activo/bloqueado/inactivo son estados independientes de Usuario
// (bloqueado no implica inactivo), así que "desbloquear" es una acción
// propia, distinta de "activar".
interface UsuarioRowProps {
  usuario: UsuarioListado;
  /** False = fila de sólo lectura, sin ninguna acción. */
  puedeGestionar: boolean;
  /**
   * Es la cuenta de quien está logueado: no puede editarla ni darla de
   * baja/reactivarla desde acá (esCuentaPropiaRestringida en config.ts).
   * Resetear la propia contraseña sigue permitido — no pasa por esta regla.
   */
  esCuentaPropia: boolean;
  /**
   * Es la cuenta de un Dueño y quien mira no lo es
   * (esCuentaDeMayorJerarquia en config.ts). Bloquea las tres acciones,
   * reseteo incluido: mostrar la contraseña temporal del Dueño a un rol
   * inferior le entrega la cuenta entera.
   */
  esCuentaProtegida: boolean;
  onEditar: () => void;
  onResetear: () => void;
  onDarDeBaja: () => void;
  onActivar: () => void;
  onDesbloquear: () => void;
}

function iniciales(nombre: string): string {
  const partes = nombre.trim().split(/\s+/);
  return `${partes[0]?.charAt(0) ?? ''}${partes[1]?.charAt(0) ?? ''}`.toUpperCase();
}

export function UsuarioRow({
  usuario,
  puedeGestionar,
  esCuentaPropia,
  esCuentaProtegida,
  onEditar,
  onResetear,
  onDarDeBaja,
  onActivar,
  onDesbloquear,
}: UsuarioRowProps) {
  const yaInactivo = usuario.estado === EstadoUsuario.INACTIVO;
  const bloqueado = usuario.estado === EstadoUsuario.BLOQUEADO;
  // La jerarquía apaga la fila entera: sobre la cuenta de un Dueño, un rol
  // inferior no ve ningún botón.
  const puedeOperar = puedeGestionar && !esCuentaProtegida;
  // Editar y cambiar de estado (baja/activar/desbloquear) quedan afuera en
  // la fila propia; Resetear no — ver el comentario de esCuentaPropia arriba.
  const puedeEditarOCambiarEstado = puedeOperar && !esCuentaPropia;

  return (
    <tr className="border-b border-border-idle transition-colors duration-[120ms] last:border-b-0 hover:bg-surface-hover">
      <td className="py-3 pl-5">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-surface-hover font-heading text-sm font-bold text-primary-volt">
            {iniciales(usuario.nombre)}
          </div>
          <div className="min-w-0">
            <p className="truncate font-body text-sm text-text-main">{usuario.nombre}</p>
            <p className="truncate font-body text-xs text-text-muted">@{usuario.username}</p>
          </div>
        </div>
      </td>
      <td className="py-3">
        <RoleChip rol={usuario.rol} label={usuario.rolLabel} />
      </td>
      <td className="py-3">
        <StatusBadge status={usuario.estado} />
      </td>
      <td className="py-3 pr-5">
        <div className="flex items-center justify-end gap-1">
          {puedeEditarOCambiarEstado && (
            <button
              type="button"
              onClick={onEditar}
              title="Editar"
              className="rounded-md p-2 text-text-muted hover:bg-surface-card hover:text-text-main"
            >
              <Pencil size={16} />
            </button>
          )}
          {puedeOperar && (
            <button
              type="button"
              onClick={onResetear}
              title="Resetear contraseña"
              className="rounded-md p-2 text-text-muted hover:bg-surface-card hover:text-status-warn"
            >
              <KeyRound size={16} />
            </button>
          )}
          {/* Mismo patrón de las otras vistas: el botón cambia de acción
              según el estado en vez de deshabilitarse sin salida — acá con
              una tercera variante para "bloqueado", que no es lo mismo que
              "inactivo". */}
          {!puedeEditarOCambiarEstado ? null : yaInactivo ? (
            <button
              type="button"
              onClick={onActivar}
              title="Activar"
              className="rounded-md p-2 text-text-muted hover:bg-surface-card hover:text-status-ok"
            >
              <RotateCcw size={16} />
            </button>
          ) : bloqueado ? (
            <button
              type="button"
              onClick={onDesbloquear}
              title="Desbloquear"
              className="rounded-md p-2 text-text-muted hover:bg-surface-card hover:text-status-ok"
            >
              <Unlock size={16} />
            </button>
          ) : (
            <button
              type="button"
              onClick={onDarDeBaja}
              title="Desactivar"
              className="rounded-md p-2 text-text-muted hover:bg-surface-card hover:text-status-danger"
            >
              <Ban size={16} />
            </button>
          )}
        </div>
      </td>
    </tr>
  );
}
