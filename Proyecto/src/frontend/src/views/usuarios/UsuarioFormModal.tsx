import { useEffect, useState, type SubmitEvent } from 'react';
import { IdCard, Lock, Mail, User } from 'lucide-react';
import { InputField, PrimaryButton, SelectField, type SelectOption } from '../../components/ui';
import { colors } from '../../config';
import { mensajeDeError } from '../../services/api';
import {
  crearUsuario,
  actualizarUsuario,
  listarPersonasSinUsuario,
  type UsuarioListado,
} from '../../services/usuariosService';
import { useAuthStore } from '../../store/authStore';
import { useUiStore } from '../../store/uiStore';

// Equivalente de _open_form (estructura_usuarios.md). Dos diferencias con
// el doc, explicadas en usuariosService.ts: en vez de tipear un nombre
// libre, el alta elige entre las Personas que todavía no tienen cuenta
// (Usuario necesita una Persona ya existente); y no hay selector de rol —
// el rol se DERIVA de lo que la persona ya es en el esquema (socio, o
// empleado y de qué tipo), así la cuenta nunca puede contradecir la ficha.
// El rol resultante se muestra en la etiqueta de cada opción.
interface UsuarioFormModalProps {
  /** null = alta nueva. Con un usuario, abre en modo edición. */
  usuario: UsuarioListado | null;
  onClose: () => void;
  onGuardado: (usuario: UsuarioListado) => void;
}

export function UsuarioFormModal({ usuario, onClose, onGuardado }: UsuarioFormModalProps) {
  const esEdicion = usuario !== null;

  const [idPersona, setIdPersona] = useState('');
  const [username, setUsername] = useState(usuario?.username ?? '');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState(usuario?.email ?? '');

  const [candidatos, setCandidatos] = useState<SelectOption[] | null>(null);
  const [guardando, setGuardando] = useState(false);

  const idUsuarioActor = useAuthStore((s) => s.usuario?.id_usuario);
  const showSnack = useUiStore((s) => s.showSnack);

  useEffect(() => {
    if (esEdicion) return;
    let cancelado = false;
    listarPersonasSinUsuario()
      .then((lista) => {
        if (cancelado) return;
        // El rol va en la etiqueta porque no es elegible: se deriva de lo
        // que la persona ya es (socio o empleado, y de qué tipo). Mostrarlo
        // evita que el staff cree una cuenta sin saber con qué permisos va
        // a quedar.
        setCandidatos(
          lista.map((p) => ({
            value: String(p.idPersona),
            label: `${p.nombre} — ${p.rolLabel}`,
          })),
        );
        setIdPersona((actual) => actual || (lista[0] ? String(lista[0].idPersona) : ''));
      })
      // Sin catch, un rechazo dejaba `candidatos` en null para siempre: el
      // modal se quedaba con el selector vacío y "Guardar" deshabilitado,
      // sin decir por qué, y encima tiraba un unhandled rejection a la
      // consola. Con la lista vacía al menos cae en el mensaje de "no hay
      // candidatos" y el error se ve en el snack.
      .catch((err: unknown) => {
        if (cancelado) return;
        setCandidatos([]);
        showSnack(mensajeDeError(err), colors.statusDanger);
      });
    return () => {
      cancelado = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSubmit = async (e: SubmitEvent) => {
    e.preventDefault();
    setGuardando(true);
    try {
      const resultado = usuario
        ? await actualizarUsuario(usuario.idUsuario, { username, email }, idUsuarioActor)
        : await crearUsuario({ idPersona: Number(idPersona), username, password }, idUsuarioActor);
      showSnack(
        usuario ? 'Usuario actualizado correctamente' : 'Usuario creado correctamente',
        colors.statusOk,
      );
      onGuardado(resultado);
      onClose();
    } catch (err) {
      showSnack(mensajeDeError(err), colors.statusDanger);
    } finally {
      setGuardando(false);
    }
  };

  // Sin personas pendientes de acceso, el alta no tiene qué hacer — se
  // avisa en vez de mostrar un formulario que no se puede enviar.
  const sinCandidatos = !esEdicion && candidatos !== null && candidatos.length === 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md rounded-lg border border-border-idle bg-surface-card p-6"
      >
        <h2 className="font-heading text-lg font-semibold text-text-main">
          {esEdicion ? 'Editar usuario' : 'Nuevo usuario'}
        </h2>

        {sinCandidatos ? (
          <p className="mt-4 font-body text-sm text-text-secondary">
            Todos los socios y empleados activos ya tienen una cuenta de acceso.
          </p>
        ) : (
          <div className="mt-4 flex flex-col gap-4">
            {esEdicion ? (
              <p className="font-body text-sm text-text-secondary">
                <IdCard size={14} className="mr-1 inline-block align-text-bottom" />
                {usuario.nombre} · <span className="text-text-main">{usuario.rolLabel}</span>
              </p>
            ) : (
              <SelectField
                label="Persona"
                value={idPersona}
                onChange={setIdPersona}
                options={candidatos ?? []}
                name="socio"
                required
              />
            )}

            <InputField label="Usuario" value={username} onChange={setUsername} icon={User} name="username" required />

            {esEdicion ? (
              <InputField label="Email" value={email} onChange={setEmail} icon={Mail} type="email" name="email" />
            ) : (
              <InputField
                label="Contraseña inicial"
                value={password}
                onChange={setPassword}
                password
                icon={Lock}
                name="password"
                hint="El usuario deberá cambiar su contraseña en el primer inicio de sesión. Mínimo 8 caracteres."
                required
              />
            )}
          </div>
        )}

        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md px-4 py-2 font-body text-sm text-text-secondary hover:text-text-main"
          >
            {sinCandidatos ? 'Cerrar' : 'Cancelar'}
          </button>
          {!sinCandidatos && (
            <PrimaryButton
              label={guardando ? 'Guardando…' : 'Guardar'}
              type="submit"
              disabled={guardando || (!esEdicion && candidatos === null)}
            />
          )}
        </div>
      </form>
    </div>
  );
}
