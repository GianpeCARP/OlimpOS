import { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertTriangle, Search, UserPlus } from 'lucide-react';
import { PrimaryButton, SectionCard, Topbar } from '../../components/ui';
import { colors, esCuentaDeMayorJerarquia, esCuentaPropiaRestringida } from '../../config';
import { mensajeDeError } from '../../services/api';
import {
  listarUsuarios,
  desbloquearUsuario,
  resetearPassword,
  darDeBajaUsuario,
  activarUsuario,
  type UsuarioListado,
} from '../../services/usuariosService';
import { useAuthStore } from '../../store/authStore';
import { SNACK_PERSISTENTE, useUiStore } from '../../store/uiStore';
import { usePuedeAccion } from '../../hooks/usePermisos';
import { PermisosPanel } from './PermisosPanel';
import { UsuarioFormModal } from './UsuarioFormModal';
import { UsuarioRow } from './UsuarioRow';

// Equivalente de UsuariosView (estructura_usuarios.md): banner de
// advertencia + tabla de usuarios + panel de permisos por rol. Diferencias
// grandes con el doc explicadas en usuariosService.ts (no hay modelo real
// de roles admin/trainer/staff/nutri) y PermisosPanel.tsx (el panel de
// permisos se deriva del guard real, no de una tabla aparte).
//
// Buscador es el mismo agregado de consistencia que en las otras vistas de
// listado; sin chips de filtro esta vez — con solo 2 roles reales, no
// aporta sobre poder leer la columna Rol directamente.

function Skeleton({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-md bg-surface-hover ${className}`} />;
}

export function UsuariosView() {
  const idUsuarioActor = useAuthStore((s) => s.usuario?.id_usuario);
  const rolesActor = useAuthStore((s) => s.roles);
  const showSnack = useUiStore((s) => s.showSnack);
  const confirmDialog = useUiStore((s) => s.confirmDialog);

  // Dueño y Recepcionista tienen esta sección en TOTAL — se chequea igual
  // en vez de asumirlo, así si mañana algún rol entra en LECTURA la tabla
  // queda sin botones sin tener que acordarse de tocar este archivo.
  const puedeGestionar = usePuedeAccion('gestionUsuarios');

  const [usuarios, setUsuarios] = useState<UsuarioListado[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intento, setIntento] = useState(0);

  const [busqueda, setBusqueda] = useState('');
  const [modal, setModal] = useState<{ usuario: UsuarioListado | null } | null>(null);

  useEffect(() => {
    let cancelado = false;
    setUsuarios(null);
    setError(null);
    listarUsuarios()
      .then((lista) => {
        if (!cancelado) setUsuarios(lista);
      })
      .catch((err: unknown) => {
        if (!cancelado) setError(mensajeDeError(err));
      });
    return () => {
      cancelado = true;
    };
  }, [intento]);

  const recargar = useCallback(() => setIntento((n) => n + 1), []);

  const visibles = useMemo(() => {
    if (!usuarios) return [];
    const texto = busqueda.trim().toLowerCase();
    if (texto === '') return usuarios;
    return usuarios.filter(
      (u) => u.nombre.toLowerCase().includes(texto) || u.username.toLowerCase().includes(texto),
    );
  }, [usuarios, busqueda]);

  const actualizarEnLista = useCallback((actualizado: UsuarioListado) => {
    setUsuarios((lista) =>
      lista
        ? lista.some((u) => u.idUsuario === actualizado.idUsuario)
          ? lista.map((u) => (u.idUsuario === actualizado.idUsuario ? actualizado : u))
          : [...lista, actualizado]
        : lista,
    );
  }, []);

  const pedirBaja = useCallback(
    (usuario: UsuarioListado) => {
      confirmDialog(
        `¿Desactivar el acceso de ${usuario.nombre}?`,
        'Pierde la posibilidad de iniciar sesión en la app. Esta acción queda registrada en Auditoría.',
        () => {
          darDeBajaUsuario(usuario.idUsuario, idUsuarioActor)
            .then(() => {
              showSnack(`Acceso de ${usuario.nombre} desactivado`, colors.statusOk);
              recargar();
            })
            .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
        },
      );
    },
    [confirmDialog, idUsuarioActor, showSnack, recargar],
  );

  // Sin confirmDialog: reactivar es reversible y de bajo riesgo, a
  // diferencia de pedirBaja. Mismo criterio que el resto de la app.
  const activar = useCallback(
    (usuario: UsuarioListado) => {
      activarUsuario(usuario.idUsuario, idUsuarioActor)
        .then((actualizado) => {
          showSnack(`Acceso de ${usuario.nombre} reactivado`, colors.statusOk);
          actualizarEnLista(actualizado);
        })
        .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
    },
    [idUsuarioActor, showSnack, actualizarEnLista],
  );

  const desbloquear = useCallback(
    (usuario: UsuarioListado) => {
      desbloquearUsuario(usuario.idUsuario, idUsuarioActor)
        .then((actualizado) => {
          showSnack(`Se desbloqueó la cuenta de ${usuario.nombre}`, colors.statusOk);
          actualizarEnLista(actualizado);
        })
        .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
    },
    [idUsuarioActor, showSnack, actualizarEnLista],
  );

  const pedirReseteo = useCallback(
    (usuario: UsuarioListado) => {
      confirmDialog(
        `¿Resetear la contraseña de ${usuario.nombre}?`,
        // El doc dice "se enviará un enlace de reseteo" — acá no hay backend
        // de email al que mandarle nada, así que se genera una contraseña
        // temporal real en vez de simular un envío que no ocurre.
        'Se va a generar una contraseña temporal nueva. La actual deja de funcionar.',
        () => {
          resetearPassword(usuario.idUsuario, idUsuarioActor)
            .then(({ usuario: actualizado, passwordTemporal }) => {
              // Persistente a propósito: esta contraseña se genera una sola
              // vez y no queda guardada en ningún lado consultable, así que
              // si el snack se cierra solo a los 4 segundos la cuenta queda
              // con una clave que no sabe nadie. Se cierra a mano, después
              // de anotarla.
              showSnack(
                `Nueva contraseña temporal para ${usuario.nombre}: ${passwordTemporal}`,
                colors.statusOk,
                SNACK_PERSISTENTE,
              );
              // El reseteo también destraba al usuario (ver
              // usuariosService.ts) — actualizarEnLista ya refleja ese
              // cambio de estado, no hace falta recargar todo.
              actualizarEnLista(actualizado);
            })
            .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
        },
      );
    },
    [confirmDialog, idUsuarioActor, showSnack, actualizarEnLista],
  );

  return (
    <div>
      <Topbar
        title="Usuarios"
        subtitle="Gestión de accesos al sistema"
        actions={
          puedeGestionar ? (
            <PrimaryButton
              label="Nuevo Usuario"
              icon={UserPlus}
              onClick={() => setModal({ usuario: null })}
            />
          ) : undefined
        }
      />

      <div className="space-y-4 p-8">
        {/* Banner de advertencia (estructura_usuarios.md). */}
        <div
          className="flex items-center gap-3 rounded-lg border px-4 py-3"
          style={{ borderColor: colors.accentCoral, backgroundColor: `${colors.accentCoral}14` }}
        >
          <AlertTriangle size={18} color={colors.accentCoral} className="shrink-0" />
          <p className="font-body text-sm text-text-main">
            Esta sección es exclusiva para administradores del sistema.
          </p>
        </div>

        {error && (
          <SectionCard>
            <p className="mb-4 font-body text-sm text-status-danger">{error}</p>
            <PrimaryButton label="Reintentar" onClick={recargar} />
          </SectionCard>
        )}

        {!error && !usuarios && (
          <div className="space-y-4">
            <Skeleton className="h-10 w-full max-w-sm" />
            <Skeleton className="h-64" />
            <Skeleton className="h-40" />
          </div>
        )}

        {!error && usuarios && (
          <>
            <div className="relative w-full sm:w-72">
              <Search size={16} className="absolute top-1/2 left-3 -translate-y-1/2 text-text-muted" />
              <input
                type="text"
                value={busqueda}
                onChange={(e) => setBusqueda(e.target.value)}
                placeholder="Buscar por nombre o usuario…"
                className="w-full rounded-md border border-border-idle bg-surface-card py-2 pr-3 pl-9 font-body text-sm text-text-main outline-none placeholder:text-text-muted focus:border-border-active"
              />
            </div>

            <SectionCard padding="p-0">
              {visibles.length === 0 ? (
                <p className="p-5 font-body text-sm text-text-muted">
                  {usuarios.length === 0
                    ? 'Todavía no hay usuarios cargados.'
                    : 'Ningún usuario coincide con la búsqueda.'}
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-border-idle">
                        <th className="py-3 pl-5 text-left font-body text-xs font-semibold tracking-wide text-text-secondary uppercase">
                          Usuario
                        </th>
                        <th className="py-3 text-left font-body text-xs font-semibold tracking-wide text-text-secondary uppercase">
                          Rol
                        </th>
                        <th className="py-3 text-left font-body text-xs font-semibold tracking-wide text-text-secondary uppercase">
                          Estado
                        </th>
                        <th className="py-3 pr-5 text-right font-body text-xs font-semibold tracking-wide text-text-secondary uppercase">
                          Acciones
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {visibles.map((usuario) => (
                        <UsuarioRow
                          key={usuario.idUsuario}
                          usuario={usuario}
                          puedeGestionar={puedeGestionar}
                          esCuentaPropia={esCuentaPropiaRestringida(
                            rolesActor,
                            usuario.idUsuario,
                            idUsuarioActor,
                          )}
                          esCuentaProtegida={esCuentaDeMayorJerarquia(rolesActor, usuario.rol)}
                          onEditar={() => setModal({ usuario })}
                          onResetear={() => pedirReseteo(usuario)}
                          onDarDeBaja={() => pedirBaja(usuario)}
                          onActivar={() => activar(usuario)}
                          onDesbloquear={() => desbloquear(usuario)}
                        />
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </SectionCard>

            <PermisosPanel />
          </>
        )}
      </div>

      {modal && (
        <UsuarioFormModal
          usuario={modal.usuario}
          onClose={() => setModal(null)}
          onGuardado={actualizarEnLista}
        />
      )}
    </div>
  );
}
