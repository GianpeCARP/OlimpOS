import { useUiStore } from '../../store/uiStore';
import { PrimaryButton } from './PrimaryButton';

// Equivalente de confirm_dialog/open_dialog/close_dialog (ui.md). Se monta
// una vez en App.tsx (NO en AppLayout — ver el comentario en Snackbar.tsx) y
// lee del uiStore global — equivalente a page.overlay.
export function ConfirmDialog() {
  const { open, title, message, onConfirm } = useUiStore((s) => s.dialog);
  const closeDialog = useUiStore((s) => s.closeDialog);

  if (!open) return null;

  return (
    // z-[70] y no z-50: los modales de las pantallas (fichas, formularios) son
    // z-50 y se montan DESPUÉS en el DOM, así que con el mismo z el diálogo
    // quedaba DETRÁS — "¿Quitar X de la ficha?" aparecía tapado por la ficha y
    // había que cerrarla para poder confirmar.
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/60">
      <div className="w-full max-w-sm rounded-lg border border-border-idle bg-surface-card p-6">
        <h2 className="font-heading text-lg font-semibold text-text-main">{title}</h2>
        <p className="mt-2 font-body text-sm text-text-secondary">{message}</p>
        <div className="mt-5 flex justify-end gap-3">
          <button
            onClick={closeDialog}
            className="shrink-0 rounded-md px-4 py-2 font-body text-sm whitespace-nowrap text-text-secondary hover:text-text-main"
          >
            Cancelar
          </button>
          <PrimaryButton
            label="Confirmar"
            onClick={() => {
              onConfirm?.();
              closeDialog();
            }}
          />
        </div>
      </div>
    </div>
  );
}
