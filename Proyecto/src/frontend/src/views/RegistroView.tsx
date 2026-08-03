import { useEffect, useState, type SubmitEvent } from 'react';
import { Link, useNavigate } from 'react-router';
import { User, Lock, Mail, Phone, IdCard, Calendar } from 'lucide-react';
import type { Sede } from '../types';
import { useAuthStore } from '../store/authStore';
import { useUiStore } from '../store/uiStore';
import { mensajeDeError } from '../services/api';
import { obtenerSedePorDefecto } from '../services/authService';
import { InputField, PrimaryButton } from '../components/ui';
import { APP_NAME, Routes, colors } from '../config';

// Equivalente de auth.spec.md 3.1 (registro de socio). No autentica al
// terminar — el spec solo pide crear la cuenta, el login es un paso aparte.
export function RegistroView() {
  const [dni, setDni] = useState('');
  const [apellido, setApellido] = useState('');
  const [nombre, setNombre] = useState('');
  const [email, setEmail] = useState('');
  const [fechaNacimiento, setFechaNacimiento] = useState('');
  const [telefono, setTelefono] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  // La sede del alta la resuelve el service, no la vista: es un dato, no una
  // constante de UI. Hoy devuelve la única sede activa del mock; cuando
  // exista la spec de sedes, esto pasa a ser un selector y el resto del
  // formulario no se toca.
  const [sede, setSede] = useState<Sede | null>(null);

  const navigate = useNavigate();
  const registrar = useAuthStore((s) => s.registrar);
  const isLoading = useAuthStore((s) => s.isLoading);
  const showSnack = useUiStore((s) => s.showSnack);

  useEffect(() => {
    // cancelado evita el setState tardío si el usuario se va de la pantalla
    // antes de que responda el service (que tiene delay artificial).
    let cancelado = false;
    obtenerSedePorDefecto()
      .then((s) => {
        if (!cancelado) setSede(s);
      })
      .catch((err: unknown) => {
        if (cancelado) return;
        showSnack(mensajeDeError(err), colors.statusDanger);
      });
    return () => {
      cancelado = true;
    };
  }, [showSnack]);

  const handleSubmit = async (e: SubmitEvent) => {
    e.preventDefault();
    // Sin sede no hay alta posible: el botón ya está deshabilitado, esto es
    // el cinturón de seguridad para el submit por Enter.
    if (!sede) return;
    try {
      await registrar({
        dni,
        apellido,
        nombre,
        email,
        fecha_nacimiento: fechaNacimiento || undefined,
        telefono,
        id_sede: sede.id_sede,
        username,
        password,
      });
      showSnack('Cuenta creada. Ya podés iniciar sesión.', colors.statusOk);
      navigate(`/${Routes.LOGIN}`);
    } catch (err) {
      // Los mensajes exactos (DNI/email/username duplicado, password corta,
      // sede inexistente) ya vienen armados desde authService según la
      // tabla "Errores esperados" de auth.spec.md 3.1 — no se reformulan acá.
      showSnack(mensajeDeError(err), colors.statusDanger);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface-base px-4 py-10">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md rounded-lg border border-border-idle bg-surface-card p-8"
      >
        <h1 className="mb-1 text-center font-heading text-3xl font-extrabold text-text-main">
          {APP_NAME}
        </h1>
        <p className="mb-6 text-center font-body text-sm text-text-secondary">
          Crear cuenta de socio
        </p>

        <div className="flex flex-col gap-4">
          <InputField label="DNI" value={dni} onChange={setDni} icon={IdCard} name="dni" required />
          <div className="grid grid-cols-2 gap-3">
            <InputField label="Nombre" value={nombre} onChange={setNombre} name="nombre" required />
            <InputField label="Apellido" value={apellido} onChange={setApellido} name="apellido" required />
          </div>
          <InputField
            label="Email"
            value={email}
            onChange={setEmail}
            icon={Mail}
            name="email"
            type="email"
            required
          />
          <InputField
            label="Teléfono"
            value={telefono}
            onChange={setTelefono}
            icon={Phone}
            name="telefono"
            type="tel"
            required
          />
          <InputField
            label="Fecha de nacimiento"
            value={fechaNacimiento}
            onChange={setFechaNacimiento}
            icon={Calendar}
            type="date"
            hint="Opcional"
            name="fecha_nacimiento"
          />

          {/* Una sola sede por ahora: se muestra la que devolvió el service,
              sin selector, hasta que exista la spec `sedes`. */}
          <div className="font-body text-sm text-text-secondary">
            Sede:{' '}
            <span className="text-text-main">{sede ? sede.nombre : 'Cargando…'}</span>
          </div>

          <InputField
            label="Usuario"
            value={username}
            onChange={setUsername}
            icon={User}
            name="username"
            required
          />
          <InputField
            label="Contraseña"
            value={password}
            onChange={setPassword}
            password
            icon={Lock}
            hint="Mínimo 8 caracteres"
            name="password"
            required
          />
        </div>

        <div className="mt-6">
          <PrimaryButton
            label={isLoading ? 'Creando cuenta…' : 'Crear cuenta'}
            type="submit"
            disabled={isLoading || !sede}
            width="100%"
          />
        </div>

        <p className="mt-4 text-center font-body text-sm text-text-secondary">
          ¿Ya tenés cuenta?{' '}
          <Link to={`/${Routes.LOGIN}`} className="text-primary-volt hover:underline">
            Iniciá sesión
          </Link>
        </p>
      </form>
    </div>
  );
}
