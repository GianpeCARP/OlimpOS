import { useState, type SubmitEvent } from 'react';
import { Navigate, useNavigate } from 'react-router';
import { LockKeyhole, Lock } from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import { useUiStore } from '../store/uiStore';
import { mensajeDeError } from '../services/api';
import { InputField, PrimaryButton } from '../components/ui';
import { APP_NAME, Routes, colors } from '../config';

// Segunda pantalla del flujo de ingreso, y la única salida del estado
// "credenciales correctas pero sin sesión".
//
// Se llega acá en tres casos, todos el mismo mecanismo: el primer ingreso de
// una cuenta creada por el personal, el primer ingreso del dueño (cuenta del
// seeder), y el reingreso después de que un admin resetee la clave. Por eso
// el subtítulo menciona los dos motivos.
//
// Gemela de show_cambiar_password en la app Flet (app/views/login.py).

/** Mismo mínimo que valida el backend en schemas.py. */
const LARGO_MINIMO_PASSWORD = 8;

export function CambiarPasswordView() {
  const [actual, setActual] = useState('');
  const [nueva, setNueva] = useState('');
  const [confirmar, setConfirmar] = useState('');

  const navigate = useNavigate();
  const cambiarPassword = useAuthStore((s) => s.cambiarPassword);
  const isLoading = useAuthStore((s) => s.isLoading);
  const usernamePendiente = useAuthStore((s) => s.usernamePendienteCambio);
  const showSnack = useUiStore((s) => s.showSnack);

  // Entrar por URL sin haber pasado por el login deja la pantalla sin saber
  // de quién es la cuenta que hay que cambiar. Se vuelve al login en vez de
  // mostrar un formulario que va a fallar al enviarse.
  if (!usernamePendiente) {
    return <Navigate to={`/${Routes.LOGIN}`} replace />;
  }

  const handleSubmit = async (e: SubmitEvent) => {
    e.preventDefault();

    // Las dos validaciones locales existen para no gastar un viaje al
    // servidor en errores que se detectan acá. El largo lo revalida el
    // backend igual, que es donde cuenta.
    if (nueva !== confirmar) {
      showSnack('Las contraseñas nuevas no coinciden', colors.statusDanger);
      return;
    }
    if (nueva.length < LARGO_MINIMO_PASSWORD) {
      showSnack(
        `La contraseña nueva necesita al menos ${LARGO_MINIMO_PASSWORD} caracteres`,
        colors.statusDanger,
      );
      return;
    }

    try {
      await cambiarPassword(actual, nueva);
      // Vuelve al login y NO entra directo, a propósito: así el primer uso de
      // la contraseña nueva es un login normal y queda probada antes de que
      // nadie dependa de ella.
      showSnack('Contraseña actualizada. Ingresá con la nueva.', colors.statusOk);
      navigate(`/${Routes.LOGIN}`);
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
        <h1 className="text-center font-heading text-3xl font-extrabold text-text-main">
          {APP_NAME}
        </h1>
        <h2 className="mt-4 font-heading text-xl font-bold text-text-main">
          Cambiá tu contraseña
        </h2>
        <p className="mt-1 mb-6 font-body text-sm text-text-secondary">
          Es tu primer ingreso, o te resetearon la clave. Definí una contraseña
          propia para continuar.
        </p>

        <div className="flex flex-col gap-4">
          <InputField
            label="Contraseña actual"
            value={actual}
            onChange={setActual}
            password
            icon={LockKeyhole}
            name="password-actual"
            required
          />
          <InputField
            label="Contraseña nueva"
            value={nueva}
            onChange={setNueva}
            password
            icon={Lock}
            name="password-nueva"
            required
          />
          <InputField
            label="Repetí la nueva"
            value={confirmar}
            onChange={setConfirmar}
            password
            icon={Lock}
            name="password-confirmar"
            required
          />
        </div>

        <div className="mt-6">
          <PrimaryButton
            label={isLoading ? 'Guardando…' : 'Guardar y volver al ingreso'}
            type="submit"
            disabled={isLoading}
            width="100%"
          />
        </div>
      </form>
    </div>
  );
}
