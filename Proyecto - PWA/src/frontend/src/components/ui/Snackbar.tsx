import { useUiStore } from '../../store/uiStore';

// Equivalente de show_snack (ui.md). Se monta una vez en App.tsx (NO en
// AppLayout: LoginView no pasa por ese layout y también necesita mostrar
// mensajes — los errores de credenciales salen por acá) y lee del uiStore
// global — equivalente a page.snack_bar en Flet.
// Por encima de todo (modales z-50, ConfirmDialog z-[70]): un aviso que
// aparece detrás del panel que lo disparó no se lee.
export function Snackbar() {
  const { open, message, color } = useUiStore((s) => s.snackbar);
  const closeSnack = useUiStore((s) => s.closeSnack);

  if (!open) return null;

  return (
    <div className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2 rounded-md border border-border-idle bg-surface-card px-5 py-3 font-body text-sm shadow-lg">
      <span style={{ color }}>{message}</span>
      <button onClick={closeSnack} className="ml-4 text-text-muted hover:text-text-main">
        ✕
      </button>
    </div>
  );
}
