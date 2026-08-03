import { create } from 'zustand';
import { colors } from '../config';

// Estado global de UI — equivalente a page.snack_bar / page.overlay de Flet,
// que son globales a la página. show_snack/confirm_dialog/open_dialog/
// close_dialog de ui.md se resuelven leyendo/mutando este store desde
// <Snackbar/> y <ConfirmDialog/>, montados una sola vez en App.tsx.

const SNACK_DURATION_MS = 4000;
/**
 * Duración para mensajes que el usuario tiene que LEER Y ANOTAR, no sólo
 * ver pasar: hoy es el caso de la contraseña temporal de un reseteo, que se
 * genera una sola vez y no se puede volver a consultar. Con los 4s del
 * default se iba de pantalla antes de que nadie llegara a copiarla, y la
 * cuenta quedaba con una clave que ya no sabía nadie. `0` = no se cierra
 * sola, hay que apretar la ✕.
 */
export const SNACK_PERSISTENTE = 0;

let snackTimeout: ReturnType<typeof setTimeout> | undefined;

interface SnackbarState {
  open: boolean;
  message: string;
  color: string;
}

interface DialogState {
  open: boolean;
  title: string;
  message: string;
  onConfirm: (() => void) | null;
}

interface UiState {
  snackbar: SnackbarState;
  dialog: DialogState;
  /** `duracionMs` en SNACK_PERSISTENTE deja el mensaje hasta que lo cierren. */
  showSnack: (message: string, color?: string, duracionMs?: number) => void;
  closeSnack: () => void;
  confirmDialog: (title: string, message: string, onConfirm: () => void) => void;
  closeDialog: () => void;
}

export const useUiStore = create<UiState>((set) => ({
  snackbar: { open: false, message: '', color: colors.statusOk },
  dialog: { open: false, title: '', message: '', onConfirm: null },

  showSnack: (message, color = colors.statusOk, duracionMs = SNACK_DURATION_MS) => {
    clearTimeout(snackTimeout);
    set({ snackbar: { open: true, message, color } });
    if (duracionMs === SNACK_PERSISTENTE) return;
    snackTimeout = setTimeout(() => {
      set((s) => ({ snackbar: { ...s.snackbar, open: false } }));
    }, duracionMs);
  },

  closeSnack: () => {
    clearTimeout(snackTimeout);
    set((s) => ({ snackbar: { ...s.snackbar, open: false } }));
  },

  confirmDialog: (title, message, onConfirm) =>
    set({ dialog: { open: true, title, message, onConfirm } }),

  closeDialog: () =>
    set({ dialog: { open: false, title: '', message: '', onConfirm: null } }),
}));
