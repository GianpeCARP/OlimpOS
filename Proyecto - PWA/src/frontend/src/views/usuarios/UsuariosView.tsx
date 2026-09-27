import { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertTriangle, Search, UserPlus } from 'lucide-react';
import { PrimaryButton, SectionCard, Topbar } from '../../components/ui';
import { colors, esCuentaDeMayorJerarquia, esCuentaPropiaRestringida } from '../../config';
import { mensajeDeError } from '../../services/api';
import {
  listarUsuarios,
  borrarCuenta,
  desbloquearUsuario,
  resetearPassword,
  darDeBajaUsuario,
  activarUsuario,
  type ResultadoReseteo,
  type UsuarioListado,
} from '../../services/usuariosService';
import { useAuthStore } from '../../store/authStore';
import { useUiStore } from '../../store/uiStore';
import { usePuedeAccion } from '../../hooks/usePermisos';
import { PanelCredenciales } from '../../components/PanelCredenciales';
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
  const rolesActor = useAuthStore((s) => s.roles);
  // Se sigue necesitando para las REGLAS DE FILA de la tabla: esconder los
  // botones sobre la propia cuenta. Ya no viaja a los services —el backend
  // toma el actor del token— pero la vista sí tiene que saber quién sos.
  const idUsuarioActor = useAuthStore((s) => s.usuario?.id_usuario);
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
  // La contraseña recién reseteada, para entregarla por el mismo panel que usa
  // el alta de personal. Se guarda junto al usuario porque el endpoint
  // devuelve las credenciales pero no el mail ni el teléfono a los que
  // mandárselas: eso sale de la fila que ya estaba en la tabla.
  const [credenciales, setCredenciales] = useState<
    { reseteo: ResultadoReseteo; usuario: UsuarioListado } | null
  >(null);

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

  // Null = el alta creó una cuenta y devolvió credenciales, no una fila.
  // En ese caso no hay nada que insertar: se recarga la lista entera.
  const actualizarEnLista = useCallback((actualizado: UsuarioListado | null) => {
    if (!actualizado) {
      recargar();
      return;
    }
    setUsuarios((lista) =>
      lista
        ? lista.some((u) => u.idUsuario === actualizado.idUsuario)
          ? lista.map((u) => (u.idUsuario === actualizado.idUsuario ? actualizado : u))
          : [...lista, actualizado]
        : lista,
    );
  }, [recargar]);

  const pedirBaja = useCallback(
    (usuario: UsuarioListado) => {
      confirmDialog(
        `¿Desactivar el acceso de ${usuario.nombre}?`,
        // Antes prometía "queda registrada en Auditoría", y no hay auditoría.
        // Lo que sí conviene decir: la cuenta y la ficha son dos banderas, y
        // un socio sin acceso sigue siendo socio.
        'Pierde la posibilidad de iniciar sesión en la app. Su ficha no cambia: si es socio, sigue siéndolo. Se puede volver a activar.',
        () => {
          darDeBajaUsuario(usuario.idUsuario)
            .then(() => {
              showSnack(`Acceso de ${usuario.nombre} desactivado`, colors.statusOk);
              recargar();
            })
            .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
        },
      );
    },
    [confirmDialog, showSnack, recargar],
  );

  // Sin confirmDialog: reactivar es reversible y de bajo riesgo, a
  // diferencia de pedirBaja. Mismo criterio que el resto de la app.
  const activar = useCallback(
    (usuario: UsuarioListado) => {
      activarUsuario(usuario.idUsuario)
        .then((actualizado) => {
          showSnack(`Acceso de ${usuario.nombre} reactivado`, colors.statusOk);
          actualizarEnLista(actualizado);
        })
        .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
    },
    [showSnack, actualizarEnLista],
  );

  // Con confirmación explícita: es lo único de Usuarios que no tiene vuelta.
  // La persona no se toca — ver borrar_cuenta en routers/usuarios.py.
  const pedirBorrado = useCallback(
    (usuario: UsuarioListado) => {
      confirmDialog(
        `¿Borrar la cuenta de ${usuario.nombre}?`,
        'Se borra sólo la cuenta de acceso (@' +
          usuario.username +
          '): no puede volver a entrar con ella. Su ficha y su historial quedan, y se le puede crear una cuenta nueva desde "Nuevo usuario". No se puede deshacer.',
        () => {
          borrarCuenta(usuario.idUsuario)
            .then((mensaje) => {
              showSnack(mensaje, colors.statusOk);
              recargar();
            })
            .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
        },
      );
    },
    [confirmDialog, showSnack, recargar],
  );

  const desbloquear = useCallback(
    (usuario: UsuarioListado) => {
      desbloquearUsuario(usuario.idUsuario)
        .then((actualizado) => {
          showSnack(`Se desbloqueó la cuenta de ${usuario.nombre}`, colors.statusOk);
          actualizarEnLista(actualizado);
        })
        .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
    },
    [showSnack, actualizarEnLista],
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
          resetearPassword(usuario.idUsuario)
            .then((reseteo) => {
              // Antes esto era un snack persistente con la clave adentro, y
              // dejaba a quien reseteaba copiándola a mano de un cartelito.
              // Ahora abre el MISMO panel que el alta de personal: muestra
              // usuario y contraseña, y ofrece mandarlos por mail o WhatsApp
              // con el mensaje ya escrito.
              setCredenciales({ reseteo, usuario });
              // El reseteo también destraba al usuario (ver
              // usuariosService.ts). Se recarga la lista porque el endpoint
              // devuelve las credenciales, no la fila actualizada.
              recargar();
            })
            .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
        },
      );
    },
    [confirmDialog, showSnack, recargar],
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
                          esLaMisma={usuario.idUsuario === idUsuarioActor}
                          onEditar={() => setModal({ usuario })}
                          onResetear={() => pedirReseteo(usuario)}
                          onDarDeBaja={() => pedirBaja(usuario)}
                          onActivar={() => activar(usuario)}
                          onDesbloquear={() => desbloquear(usuario)}
                          onBorrar={() => pedirBorrado(usuario)}
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

      {credenciales && (
        <PanelCredenciales
          titulo={`Contraseña reseteada: ${credenciales.usuario.nombre}`}
          mensaje={credenciales.reseteo.mensaje}
          username={credenciales.reseteo.username}
          passwordTemporal={credenciales.reseteo.passwordTemporal}
          textoCredenciales={credenciales.reseteo.textoCredenciales}
          emailEnviado={credenciales.reseteo.emailEnviado}
          email={credenciales.usuario.email ?? ''}
          telefono={credenciales.usuario.telefono ?? ''}
          onClose={() => setCredenciales(null)}
        />
      )}
    </div>
  );
}
