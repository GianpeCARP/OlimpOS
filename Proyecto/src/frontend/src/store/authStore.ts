import { create } from 'zustand';
import type { Usuario, Persona, Baja } from '../types';
import { mensajeDeError } from '../services/api';
import { haySesion } from '../services/api';
import {
  login as loginService,
  cambiarPassword as cambiarPasswordService,
  darDeBaja as darDeBajaService,
  logout as logoutService,
  sesionActual as sesionActualService,
} from '../services/authService';

// password_hash nunca debe llegar al frontend, ni siquiera en el estado de sesión.
type SesionUsuario = Omit<Usuario, 'password_hash'>;

interface AuthState {
  usuario: SesionUsuario | null;
  persona: Persona | null;
  roles: string[];
  /** Id de Socio de la sesión. Lo consume todo el portal — ver LoginResultado. */
  idSocio: number | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  /**
   * Username que quedó esperando definir su contraseña. Lo escribe `login`
   * cuando el backend contesta que la clave es temporal, y lo lee la pantalla
   * de cambio para no volver a pedirlo. En ese momento NO hay sesión ni
   * token: el backend los negó a propósito.
   */
  usernamePendienteCambio: string | null;
  /**
   * True mientras se le pregunta al backend quién es el dueño de la cookie.
   * Arranca en true si hay cookies: sin este flag, el primer render pasaría por
   * ProtectedRoute con isAuthenticated todavía en false y mandaría al login
   * antes de que la respuesta llegue — el F5 seguiría deslogueando, sólo que
   * más despacio.
   */
  isRehidratando: boolean;
  /** Reconstruye la sesión preguntándole al backend por la cookie. Ver GET /me. */
  rehidratar: () => Promise<void>;
  /**
   * Devuelve el desenlace del login. Es lo que necesita quien llama para
   * decidir a dónde navegar en el mismo tick — el `set()` de zustand todavía
   * no se ve reflejado en ese render.
   *
   * Tres desenlaces y no dos: además de entrar o fallar (que lanza), existe
   * "credenciales correctas pero falta definir la contraseña".
   */
  login: (
    username: string,
    password: string,
  ) => Promise<{ debeCambiarPassword: true } | { debeCambiarPassword: false; roles: string[] }>;
  /** Define la contraseña definitiva de `usernamePendienteCambio`. */
  cambiarPassword: (passwordActual: string, passwordNueva: string) => Promise<void>;
  // No hay acción de registro: el auto-registro se eliminó (ver config.ts).
  // El alta de un socio la hace el personal, y va a entrar por el service de
  // socios contra el backend, no por el store de sesión.
  darDeBaja: (idSocio: number, tipo: NonNullable<Baja['tipo']>, motivo?: string) => Promise<void>;
  logout: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  usuario: null,
  persona: null,
  roles: [],
  idSocio: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
  usernamePendienteCambio: null,
  // Sólo hay algo que rehidratar si quedaron cookies de antes del F5.
  isRehidratando: haySesion(),

  rehidratar: async () => {
    if (!haySesion()) {
      set({ isRehidratando: false });
      return;
    }
    try {
      const { usuario, persona, roles, idSocio } = await sesionActualService();
      set({
        usuario,
        persona,
        roles,
        idSocio: idSocio ?? null,
        isAuthenticated: true,
        isRehidratando: false,
      });
    } catch {
      // Token vencido, alterado, o cuenta desactivada. Se limpia y a login;
      // no se muestra ningún error porque el usuario no hizo nada mal — su
      // sesión simplemente caducó.
      // No hay nada que borrar desde acá: la cookie de sesión es
      // httponly. Igual quedó inservible, y el backend la va a
      // reemplazar en el próximo login.
      set({ isAuthenticated: false, isRehidratando: false });
    }
  },

  login: async (username, password) => {
    set({ isLoading: true, error: null });
    try {
      const resultado = await loginService(username, password);

      // Credenciales correctas, pero la cuenta tiene contraseña temporal. No
      // se toca nada del estado de sesión: sigue sin haber sesión. Lo único
      // que se recuerda es el username, para la pantalla de cambio.
      if (resultado.debeCambiarPassword) {
        set({ isLoading: false, usernamePendienteCambio: username.trim() });
        return { debeCambiarPassword: true };
      }

      const { usuario, persona, roles, idSocio } = resultado;
      set({
        usuario,
        persona,
        roles,
        idSocio: idSocio ?? null,
        isAuthenticated: true,
        isLoading: false,
        usernamePendienteCambio: null,
      });
      return { debeCambiarPassword: false, roles };
    } catch (err) {
      set({ isLoading: false, error: mensajeDeError(err) });
      throw err;
    }
  },

  cambiarPassword: async (passwordActual, passwordNueva) => {
    const username = get().usernamePendienteCambio;
    if (!username) {
      throw new Error('No hay ninguna cuenta pendiente de cambio de contraseña.');
    }
    set({ isLoading: true, error: null });
    try {
      await cambiarPasswordService(username, passwordActual, passwordNueva);
      set({ isLoading: false, usernamePendienteCambio: null });
    } catch (err) {
      set({ isLoading: false, error: mensajeDeError(err) });
      throw err;
    }
  },

  darDeBaja: async (idSocio, tipo, motivo) => {
    set({ isLoading: true, error: null });
    try {
      // El actor de la baja es el usuario logueado que la dispara, no un
      // parámetro que el componente tenga que pasar a mano.
      const idUsuarioActor = get().usuario?.id_usuario;
      await darDeBajaService(idSocio, tipo, motivo, idUsuarioActor);
      set({ isLoading: false });
    } catch (err) {
      set({ isLoading: false, error: mensajeDeError(err) });
      throw err;
    }
  },

  logout: async () => {
    // Se le avisa al backend ANTES de limpiar la pantalla: la cookie de
    // sesión es httponly y solo el servidor puede borrarla. Si solo se
    // vaciara el store, la pantalla mostraría el login pero la sesión
    // seguiría abierta en el navegador.
    try {
      await logoutService();
    } catch {
      // Si el backend no responde igual se limpia la pantalla: dejar al
      // usuario "adentro" porque falló la red sería peor. La cookie expira
      // sola por max-age.
    }
    set({
      usuario: null,
      persona: null,
      roles: [],
      idSocio: null,
      isAuthenticated: false,
      usernamePendienteCambio: null,
    });
  },
}));
