import { useState, type SubmitEvent } from 'react';
import { useNavigate } from 'react-router';
import { User, Lock } from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import { mensajeDeError } from '../services/api';
import { InputField, PrimaryButton } from '../components/ui';
import { APP_NAME, MAX_INTENTOS_FALLIDOS, Routes, rutaInicialPara } from '../config';

// Equivalente de show_login (main.md/router.md). Pantalla real, no
// placeholder: auth.spec.md ya está implementado de punta a punta.
//
// Esta pantalla tiene SOLO usuario y contraseña, sin link a registro. Es un
// desvío deliberado de auth.spec.md 3.1 (registro de socio), impuesto por la
// consigna: "la regla de oro para sistemas internos de administración es que
// no debe existir un botón Registrarse en la pantalla de inicio". Las altas
// las hace el personal desde la app de escritorio y el sistema genera una
// contraseña temporal — ver backend/README.md, "registro por invitación".
export function LoginView() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  // El error de credenciales se muestra INLINE, debajo de los campos, y no en
  // el snackbar. El snackbar vive pegado al borde inferior de la ventana: con
  // el formulario centrado quedaba a casi 300px del botón, en letra chica y
  // durante 4 segundos. En la práctica no se veía.
  //
  // Además así queda igual que la app Flet, que siempre mostró el error
  // debajo de los campos (app/views/login.py, error_ref). El snackbar se
  // reserva para avisos de otras pantallas, donde la vista no tiene un lugar
  // natural donde poner el mensaje.
  const [error, setError] = useState('');

  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);
  const isLoading = useAuthStore((s) => s.isLoading);

  const handleSubmit = async (e: SubmitEvent) => {
    e.preventDefault();
    setError('');
    try {
      // login() devuelve el desenlace — no se puede leer del store acá
      // porque el set() de zustand todavía no se reflejó en este render.
      const resultado = await login(username, password);

      // Credenciales correctas, pero la cuenta tiene contraseña temporal: el
      // backend verificó la clave y aun así no emitió token. No hay sesión
      // que abrir, el único camino es definir una contraseña propia.
      if (resultado.debeCambiarPassword) {
        navigate(`/${Routes.CAMBIAR_PASSWORD}`);
        return;
      }

      // El destino depende del rol: un Entrenador no ve el Dashboard.
      navigate(`/${rutaInicialPara(resultado.roles)}`);
    } catch (err) {
      setError(mensajeDeError(err));
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface-base px-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-lg border border-border-idle bg-surface-card p-8"
      >
        <h1 className="mb-6 text-center font-heading text-3xl font-extrabold text-text-main">
          {APP_NAME}
        </h1>
        <div className="flex flex-col gap-4">
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
            name="password"
            required
          />
        </div>

        {/* Ocupa lugar sólo cuando hay algo que decir, igual que el error_ref
            de Flet: reservar el alto siempre dejaría un hueco permanente. */}
        {error && (
          <div className="mt-4" role="alert">
            <p className="font-body text-sm text-status-danger">{error}</p>
            <p className="mt-1 font-body text-xs text-text-muted">
              Después de {MAX_INTENTOS_FALLIDOS} intentos fallidos la cuenta se
              bloquea y hay que pedirle al gimnasio que la desbloquee.
            </p>
          </div>
        )}

        <div className="mt-6">
          <PrimaryButton
            label={isLoading ? 'Ingresando…' : 'Ingresar'}
            type="submit"
            disabled={isLoading}
            width="100%"
          />
        </div>

        <p className="mt-4 text-center font-body text-sm text-text-secondary">
          Usá las credenciales que te dio el gimnasio.
        </p>
      </form>
    </div>
  );
}
