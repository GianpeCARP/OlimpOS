import { create } from 'zustand';
import type { Usuario, Persona, Baja } from '../types';
import { mensajeDeError } from '../services/api';
import {
  login as loginService,
  registrarSocio as registrarSocioService,
  darDeBaja as darDeBajaService,
  type RegistroSocioInput,
} from '../services/authService';

// password_hash nunca debe llegar al frontend, ni siquiera en el estado de sesión.
type SesionUsuario = Omit<Usuario, 'password_hash'>;

interface AuthState {
  usuario: SesionUsuario | null;
  persona: Persona | null;
  roles: string[];
  /** Id de Socio de la sesión. Lo consume todo el portal — ver LoginResultado. */
  idSocio: number | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  /**
   * Devuelve los roles de la sesión recién abierta. Hace falta porque quien
   * llama necesita decidir a dónde navegar en el mismo tick, y el `set()`
   * de zustand todavía no se ve reflejado en ese render.
   */
  login: (username: string, password: string) => Promise<{ roles: string[] }>;
  registrar: (input: RegistroSocioInput) => Promise<void>;
  darDeBaja: (idSocio: number, tipo: NonNullable<Baja['tipo']>, motivo?: string) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  usuario: null,
  persona: null,
  roles: [],
  idSocio: null,
  token: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  login: async (username, password) => {
    set({ isLoading: true, error: null });
    try {
      const { usuario, persona, roles, token, idSocio } = await loginService(username, password);
      set({
        usuario,
        persona,
        roles,
        idSocio: idSocio ?? null,
        token,
        isAuthenticated: true,
        isLoading: false,
      });
      return { roles };
    } catch (err) {
      set({ isLoading: false, error: mensajeDeError(err) });
      throw err;
    }
  },

  registrar: async (input) => {
    set({ isLoading: true, error: null });
    try {
      await registrarSocioService(input);
      set({ isLoading: false });
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

  logout: () =>
    set({
      usuario: null,
      persona: null,
      roles: [],
      idSocio: null,
      token: null,
      isAuthenticated: false,
    }),
}));
