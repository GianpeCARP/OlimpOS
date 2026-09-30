import { useEffect, useState, type SubmitEvent } from 'react';
import { Award, IdCard, Mail, User } from 'lucide-react';
import { InputField, PrimaryButton, SelectField, type SelectOption, TelefonoField } from '../../components/ui';
import {
  colors,
  RolEmpleado,
  type RolEmpleadoValue,
} from '../../config';
import { mensajeDeError } from '../../services/api';
import {
  crearEmpleado,
  actualizarEmpleado,
  camposDeRoles,
  listarFranjas,
  valoresDeRoles,
  type AltaEmpleadoResultado,
  type EmpleadoListado,
} from '../../services/personalService';
import { useUiStore } from '../../store/uiStore';
// El panel de entrega de credenciales vivía acá adentro. Se movió a
// components/ porque el reseteo de contraseña en Usuarios necesita el mismo.
import { PanelCredenciales } from '../../components/PanelCredenciales';

// Equivalente de _open_form/_save (estructura_personal.md), adaptado al
// esquema real. El doc tiene un campo "turno" fijo para todos; acá los campos
// que se muestran dependen de los roles marcados, porque en la base cada rol
// guarda una cosa distinta: la franja el recepcionista, la especialidad el
// entrenador y el profesor, el título el nutricionista.
//
// LOS ROLES SON CASILLAS, NO UN SELECTOR
// Los cuatro subtipos de Empleado son SOLAPADOS en el esquema: la misma
// persona puede ser entrenadora y profesora. Esto era un <select> de un solo
// valor porque el backend borraba la fila del rol viejo al cambiarlo; desde
// que la apaga en vez de borrarla (ver Entrenador.activo en models.py), los
// roles se acumulan y se eligen con casillas.

const TODOS_LOS_ROLES = Object.values(RolEmpleado);

interface EmpleadoFormModalProps {
  /** null = alta nueva. Con un empleado, abre en modo edición. */
  empleado: EmpleadoListado | null;
  onClose: () => void;
  onGuardado: (empleado: EmpleadoListado) => void;
}

export function EmpleadoFormModal({ empleado, onClose, onGuardado }: EmpleadoFormModalProps) {
  const [dni, setDni] = useState(empleado?.dni ?? '');
  const [nombre, setNombre] = useState(empleado?.nombre ?? '');
  const [apellido, setApellido] = useState(empleado?.apellido ?? '');
  const [email, setEmail] = useState(empleado?.email ?? '');
  const [telefono, setTelefono] = useState(empleado?.telefono ?? '');
  const [roles, setRoles] = useState<RolEmpleadoValue[]>(
    empleado?.roles.length ? empleado.roles : [RolEmpleado.ENTRENADOR],
  );
  // Un estado por campo, y no uno solo: con dos roles marcados puede haber dos
  // campos distintos a la vista (Especialidad y Título), y un único `detalle`
  // compartido los pisaba entre sí.
  const iniciales = valoresDeRoles(empleado, empleado?.roles ?? []);
  const [especialidad, setEspecialidad] = useState(iniciales.especialidad);
  const [titulo, setTitulo] = useState(iniciales.titulo);
  const [idFranja, setIdFranja] = useState(iniciales.idFranjaLaboral);

  /**
   * Alta recién hecha cuyas credenciales hay que entregar. Mientras tenga
   * valor, el modal muestra el panel de credenciales en lugar del formulario
   * — ver el comentario de `handleSubmit`.
   */
  const [credenciales, setCredenciales] = useState<AltaEmpleadoResultado | null>(null);

  // Catálogo de franjas para el selector de turno del recepcionista.
  const [franjasOpc, setFranjasOpc] = useState<SelectOption[]>([]);
  useEffect(() => {
    listarFranjas()
      .then((fs) => setFranjasOpc(fs.map((f) => ({ value: String(f.idFranjaLaboral), label: f.nombre }))))
      .catch(() => setFranjasOpc([]));
  }, []);

  const [guardando, setGuardando] = useState(false);

  const showSnack = useUiStore((s) => s.showSnack);

  const campos = camposDeRoles(roles);

  /**
   * Marca o desmarca un rol. Al menos uno tiene que quedar: el backend lo
   * exige igual (`roles` con min_length=1) y un empleado sin ningún rol no
   * podría entrar a ninguna sección, así que la última casilla no se destilda.
   *
   * Al marcar un rol nuevo se precarga su campo con lo que esa persona ya
   * tenía guardado en él, si es que lo tenía. Sin eso, marcar Nutricionista a
   * alguien que ya lo había sido abría el Título vacío y guardar lo borraba.
   */
  const alternarRol = (rolTocado: RolEmpleadoValue) => {
    const siguientes = roles.includes(rolTocado)
      ? roles.filter((r) => r !== rolTocado)
      : [...roles, rolTocado];
    if (siguientes.length === 0) {
      showSnack('Tiene que quedar al menos un rol.', colors.statusWarn);
      return;
    }
    setRoles(siguientes);

    const previos = valoresDeRoles(empleado, siguientes);
    const visibles = camposDeRoles(siguientes);
    if (visibles.includes('especialidad') && !especialidad) setEspecialidad(previos.especialidad);
    if (visibles.includes('titulo') && !titulo) setTitulo(previos.titulo);
    if (visibles.includes('franja') && !idFranja) setIdFranja(previos.idFranjaLaboral);
  };

  const handleSubmit = async (e: SubmitEvent) => {
    e.preventDefault();

    // Mail o teléfono, al menos uno. El backend lo exige igual —es la regla,
    // no una comodidad de esta pantalla— pero avisar acá evita el viaje y
    // señala el problema mientras el formulario está a la vista: un empleado
    // al que nadie sabe cómo contactar no sirve de nada.
    if (!email.trim() && !telefono.trim()) {
      showSnack('Cargá un email o un teléfono: sin una de las dos vías no hay forma de contactarlo.',
        colors.statusDanger);
      return;
    }

    setGuardando(true);
    try {
      const datos = { dni, nombre, apellido, email, telefono, roles, especialidad, titulo, idFranjaLaboral: idFranja };

      if (empleado) {
        const actualizado = await actualizarEmpleado(empleado.idEmpleado, datos);
        showSnack('Empleado actualizado correctamente', colors.statusOk);
        onGuardado(actualizado);
      } else {
        const alta = await crearEmpleado(datos);
        onGuardado(alta.empleado);

        // Las credenciales se muestran UNA vez: el backend guarda solo el
        // hash. Las reciben los cuatro roles, Profesor incluido; sólo faltan si
        // la persona ya tenía cuenta, y el backend lo explica en `mensaje`.
        //
        // Con credenciales el modal NO se cierra: pasa al panel de entrega,
        // desde donde se le mandan por mail o WhatsApp. Antes salían en un
        // snack y había que copiarlas a mano antes de que se fuera.
        if (alta.passwordTemporal) {
          setCredenciales(alta);
          return;
        }
        showSnack(alta.mensaje, colors.statusOk);
      }

      onClose();
    } catch (err) {
      showSnack(mensajeDeError(err), colors.statusDanger);
    } finally {
      setGuardando(false);
    }
  };

  // Se exigen los DOS campos y no sólo que el objeto exista: son opcionales en
  // AltaEmpleadoResultado —el alta puede terminar sin crear cuenta, y el
  // backend los manda en null— así que un guard flojo dejaba abrir el panel de
  // entrega sin nada que entregar, con los recuadros de usuario y contraseña
  // en blanco. De paso TypeScript los estrecha a `string` acá adentro.
  if (credenciales?.username && credenciales.passwordTemporal) {
    return (
      <PanelCredenciales
        titulo="Empleado dado de alta"
        mensaje={credenciales.mensaje}
        username={credenciales.username}
        passwordTemporal={credenciales.passwordTemporal}
        textoCredenciales={credenciales.textoCredenciales}
        emailEnviado={credenciales.emailEnviado}
        email={email.trim()}
        telefono={telefono.trim()}
        onClose={onClose}
      />
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md rounded-lg border border-border-idle bg-surface-card p-6"
      >
        <h2 className="font-heading text-lg font-semibold text-text-main">
          {empleado ? 'Editar empleado' : 'Nuevo empleado'}
        </h2>

        <div className="mt-4 flex flex-col gap-4">
          {/* El DNI identifica a la persona: se carga al alta y no se edita. */}
          {empleado ? (
            <p className="font-body text-sm text-text-secondary">
              DNI <span className="text-text-main">{dni}</span>
              {empleado.legajo && (
                <>
                  {' · Legajo '}
                  <span className="text-text-main">{empleado.legajo}</span>
                </>
              )}
            </p>
          ) : (
            <InputField label="DNI" value={dni} onChange={setDni} icon={IdCard} name="dni" required />
          )}

          <div className="grid grid-cols-2 gap-3">
            <InputField label="Nombre" value={nombre} onChange={setNombre} icon={User} name="nombre" required />
            <InputField label="Apellido" value={apellido} onChange={setApellido} name="apellido" required />
          </div>

          <InputField label="Email" value={email} onChange={setEmail} icon={Mail} type="email" name="email" />
          {/* El teléfono se filtra mientras se tipea: el campo aceptaba letras
              y el error recién aparecía al guardar el formulario entero. */}
          <TelefonoField label="Teléfono" value={telefono} onChange={setTelefono} name="telefono" />
          <p className="-mt-2 font-body text-xs text-text-muted">
            Email o teléfono: al menos uno de los dos, para poder contactarlo.
          </p>

          {/* Casillas y no un selector: los roles se acumulan. Alguien puede
              ser entrenador Y profesor, y con un selector había que elegir. */}
          <fieldset>
            <legend className="mb-2 font-body text-xs font-medium text-text-secondary">
              Roles
            </legend>
            <div className="grid grid-cols-2 gap-x-3 gap-y-2">
              {TODOS_LOS_ROLES.map((r) => (
                <label
                  key={r}
                  className="flex items-center gap-2 font-body text-sm text-text-secondary"
                >
                  <input
                    type="checkbox"
                    checked={roles.includes(r)}
                    onChange={() => alternarRol(r)}
                    className="size-4 shrink-0 accent-primary-volt"
                    name={`rol-${r}`}
                  />
                  <span className="truncate">{r}</span>
                </label>
              ))}
            </div>
            <p className="mt-2 font-body text-xs text-text-muted">
              Se puede marcar más de uno. Sacarle un rol no borra nada de lo que hizo
              con él; si le sacás Entrenador, deja de estar a cargo de sus socios.
            </p>
          </fieldset>

          {/* Un campo por dato, no por rol: Entrenador y Profesor piden los dos
              "Especialidad" y con dos inputs iguales nadie sabría cuál es cuál
              (ver camposDeRoles). */}
          {campos.includes('especialidad') && (
            <InputField
              label="Especialidad"
              value={especialidad}
              onChange={setEspecialidad}
              icon={Award}
              name="especialidad"
            />
          )}
          {campos.includes('titulo') && (
            <InputField
              label="Título"
              value={titulo}
              onChange={setTitulo}
              icon={Award}
              name="titulo"
            />
          )}
          {campos.includes('franja') && (
            <SelectField
              label="Turno / franja"
              value={idFranja}
              onChange={setIdFranja}
              options={franjasOpc}
              placeholder="Sin turno asignado"
              name="id_franja_laboral"
            />
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
