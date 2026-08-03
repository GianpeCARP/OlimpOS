import { useState, type SubmitEvent } from 'react';
import { Link, useNavigate } from 'react-router';
import { User, Lock } from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import { useUiStore } from '../store/uiStore';
import { mensajeDeError } from '../services/api';
import { InputField, PrimaryButton } from '../components/ui';
import { APP_NAME, Routes, colors, rutaInicialPara } from '../config';

// Equivalente de show_login (main.md/router.md). Pantalla real, no
// placeholder: auth.spec.md ya está implementado de punta a punta.
export function LoginView() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);
  const isLoading = useAuthStore((s) => s.isLoading);
  const showSnack = useUiStore((s) => s.showSnack);

  const handleSubmit = async (e: SubmitEvent) => {
    e.preventDefault();
    try {
      // login() devuelve los roles de la sesión recién abierta — no se
      // pueden leer del store acá porque el set() de zustand todavía no
      // se reflejó en este render. El destino depende del rol: un
      // Entrenador no ve el Dashboard.
      const { roles } = await login(username, password);
      navigate(`/${rutaInicialPara(roles)}`);
    } catch (err) {
      showSnack(mensajeDeError(err), colors.statusDanger);
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
        <div className="mt-6">
          <PrimaryButton
            label={isLoading ? 'Ingresando…' : 'Ingresar'}
            type="submit"
            disabled={isLoading}
            width="100%"
          />
        </div>

        <p className="mt-4 text-center font-body text-sm text-text-secondary">
          ¿No tenés cuenta?{' '}
          <Link to={`/${Routes.REGISTRO}`} className="text-primary-volt hover:underline">
            Registrate
          </Link>
        </p>
      </form>
    </div>
  );
}
