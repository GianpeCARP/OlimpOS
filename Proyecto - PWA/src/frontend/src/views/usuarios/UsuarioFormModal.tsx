import { useEffect, useState, type SubmitEvent } from 'react';
import { IdCard, Mail, User } from 'lucide-react';
import { InputField, PrimaryButton, SelectField, type SelectOption } from '../../components/ui';
import { colors } from '../../config';
import { mensajeDeError } from '../../services/api';
import {
  crearUsuario,
  actualizarUsuario,
  listarPersonasSinUsuario,
  type PersonaSinUsuario,
  type ResultadoCredenciales,
  type UsuarioListado,
} from '../../services/usuariosService';
import { useUiStore } from '../../store/uiStore';
import { PanelCredenciales } from '../../components/PanelCredenciales';

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
  /**
   * El alta devuelve credenciales, no una fila de la tabla: por eso puede
   * llegar null y quien escucha recarga la lista en vez de insertar.
   */
  onGuardado: (usuario: UsuarioListado | null) => void;
}

export function UsuarioFormModal({ usuario, onClose, onGuardado }: UsuarioFormModalProps) {
  const esEdicion = usuario !== null;

  const [idPersona, setIdPersona] = useState('');
  const [username, setUsername] = useState(usuario?.username ?? '');
  const [email, setEmail] = useState(usuario?.email ?? '');

  const [candidatos, setCandidatos] = useState<SelectOption[] | null>(null);
  // Las personas completas, no sólo las opciones: al crear la cuenta hace
  // falta el mail y el teléfono de la elegida para mandarle las credenciales.
  const [personas, setPersonas] = useState<PersonaSinUsuario[]>([]);
  const [guardando, setGuardando] = useState(false);
  // La cuenta recién creada cuyas credenciales hay que entregar. Mientras
  // tenga valor, el modal muestra el panel de entrega en vez del formulario.
  const [credenciales, setCredenciales] = useState<
    { cred: ResultadoCredenciales; persona: PersonaSinUsuario | undefined } | null
  >(null);

  const showSnack = useUiStore((s) => s.showSnack);

  useEffect(() => {
    if (esEdicion) return;
    let cancelado = false;
    listarPersonasSinUsuario()
      .then((lista) => {
        if (cancelado) return;
        setPersonas(lista);
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
      if (usuario) {
        const actualizado = await actualizarUsuario(usuario.idUsuario, { username, email });
        showSnack('Usuario actualizado correctamente', colors.statusOk);
        onGuardado(actualizado);
      } else {
        // El alta no manda username ni contraseña: los genera el backend. Que
        // un administrador eligiera la clave de otro significaría que la
        // conoce, y para siempre.
        const cred = await crearUsuario({ idPersona: Number(idPersona) });
        // La lista se recarga desde el padre: el alta devuelve credenciales,
        // no la fila de la tabla.
        onGuardado(null);
        // Y el modal NO se cierra: pasa al MISMO panel de entrega que el alta
        // de personal y el reseteo, desde donde se mandan por mail o
        // WhatsApp. Antes salían en un aviso para copiar a mano.
        setCredenciales({ cred, persona: personas.find((p) => String(p.idPersona) === idPersona) });
        return;
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
        titulo="Cuenta creada"
        mensaje={credenciales.cred.mensaje}
        username={credenciales.cred.username}
        passwordTemporal={credenciales.cred.passwordTemporal}
        textoCredenciales={credenciales.cred.textoCredenciales}
        emailEnviado={credenciales.cred.emailEnviado}
        email={credenciales.persona?.email ?? ''}
        telefono={credenciales.persona?.telefono ?? ''}
        onClose={onClose}
      />
    );
  }

  // Mientras llega la lista NO se dibuja el formulario. Antes sí se dibujaba,
  // con el selector vacío, y si la respuesta venía sin candidatos el modal
  // saltaba al aviso de abajo: se veía un formulario que aparecía y
  // desaparecía en un instante, que parece un bug aunque no lo sea.
  const cargando = !esEdicion && candidatos === null;

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

        {cargando ? (
          <p className="mt-4 font-body text-sm text-text-muted">Buscando personas sin cuenta…</p>
        ) : sinCandidatos ? (
          // El mensaje viejo ("todos los socios y empleados activos ya tienen
          // cuenta") era cierto pero no explicaba nada, y con la base recién
          // entregada —donde no hay NADIE cargado— se leía como un error.
          // Lo que falta decir es qué hace esta pantalla y dónde se crea una
          // persona, que es lo que alguien busca cuando toca "Nuevo usuario".
          <div className="mt-4 flex flex-col gap-2 font-body text-sm text-text-secondary">
            <p>No hay nadie a quien darle acceso: todas las personas cargadas ya tienen cuenta.</p>
            <p>
              Esta pantalla no crea personas. La cuenta se crea sola al dar de alta a alguien en{' '}
              <span className="text-text-main">Socios</span> o en{' '}
              <span className="text-text-main">Personal</span>. Acá sólo se le da acceso a alguien
              que haya quedado cargado sin cuenta.
            </p>
          </div>
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

            {/* En el ALTA no se piden usuario ni contraseña: los genera el
                backend y se muestran una sola vez al guardar. Que un
                administrador eligiera la clave de otro significaría que la
                conoce, y para siempre. */}
            {esEdicion ? (
              <>
                <InputField label="Usuario" value={username} onChange={setUsername} icon={User} name="username" required />
                <InputField label="Email" value={email} onChange={setEmail} icon={Mail} type="email" name="email" />
              </>
            ) : (
              <p className="font-body text-sm text-text-secondary">
                El sistema va a generar el nombre de usuario y una contraseña
                temporal. Se muestran una sola vez al guardar, y la persona
                tiene que cambiarla en su primer ingreso.
              </p>
            )}
          </div>
        )}

        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 rounded-md px-4 py-2 font-body text-sm whitespace-nowrap text-text-secondary hover:text-text-main"
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
