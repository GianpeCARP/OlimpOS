import { useState, type SubmitEvent } from 'react';
import { InputField, PrimaryButton } from '../../components/ui';
import { colors } from '../../config';
import { mensajeDeError } from '../../services/api';
import { crearEjercicio } from '../../services/rutinasService';
import { useUiStore } from '../../store/uiStore';

// Alta de un ejercicio del catálogo compartido, con el link del video.
//
// El entrenador sólo pega un link de YouTube del canal del gimnasio: el
// demonio del servidor (backend/demonio_videos.py) lo baja solo, y recién ahí
// el socio ve "Ver técnica". Nadie del personal necesita acceso al FTP.
// Gemelo de _open_form_ejercicio en app/views/rutinas.py (Flet).
interface EjercicioFormModalProps {
  onClose: () => void;
  onCreado: () => void;
}

export function EjercicioFormModal({ onClose, onCreado }: EjercicioFormModalProps) {
  const showSnack = useUiStore((s) => s.showSnack);
  const [nombre, setNombre] = useState('');
  const [grupoMuscular, setGrupoMuscular] = useState('');
  const [descripcion, setDescripcion] = useState('');
  const [urlVideo, setUrlVideo] = useState('');
  const [requiereMaquina, setRequiereMaquina] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: SubmitEvent) => {
    e.preventDefault();
    setGuardando(true);
    setError(null);
    try {
      await crearEjercicio({ nombre, grupoMuscular, descripcion, urlVideo, requiereMaquina });
      showSnack(
        urlVideo.trim()
          ? 'Ejercicio creado. El video va a estar disponible en unos minutos.'
          : 'Ejercicio creado.',
        colors.statusOk,
      );
      onCreado();
      onClose();
    } catch (err) {
      setError(mensajeDeError(err));
      setGuardando(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <form
        onSubmit={handleSubmit}
        className="flex max-h-[90vh] w-full max-w-md flex-col rounded-lg border border-border-idle bg-surface-card"
      >
        <h2 className="shrink-0 px-6 pt-6 font-heading text-lg font-semibold text-text-main">
          Nuevo ejercicio
        </h2>

        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-6 py-4">
          <InputField label="Nombre" value={nombre} onChange={setNombre} name="nombre" required />
          <InputField
            label="Grupo muscular"
            value={grupoMuscular}
            onChange={setGrupoMuscular}
            name="grupo_muscular"
            hint="Ej: Piernas, Pecho, Espalda"
            required
          />
          <label className="flex flex-col gap-1.5 font-body text-sm">
            <span className="text-text-secondary">Descripción</span>
            <textarea
              value={descripcion}
              onChange={(e) => setDescripcion(e.target.value)}
              rows={3}
              placeholder="Cómo se hace, qué cuidar…"
              className="w-full resize-none rounded-md border border-border-idle bg-surface-card px-3 py-2 font-body text-sm text-text-main outline-none placeholder:text-text-muted focus:border-border-active"
            />
          </label>
          <InputField
            label="Video (link de YouTube)"
            value={urlVideo}
            onChange={setUrlVideo}
            name="url_video"
            hint="Del canal del gimnasio. Tarda unos minutos en quedar disponible para los socios."
          />
          <label className="flex items-center gap-2 font-body text-sm text-text-secondary">
            <input
              type="checkbox"
              checked={requiereMaquina}
              onChange={(e) => setRequiereMaquina(e.target.checked)}
              className="size-4 accent-primary-volt"
            />
            Requiere máquina
          </label>
          {error && <p className="font-body text-sm text-status-danger">{error}</p>}
        </div>

        <div className="flex shrink-0 justify-end gap-3 px-6 pt-2 pb-6">
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 rounded-md px-4 py-2 font-body text-sm whitespace-nowrap text-text-secondary hover:text-text-main"
          >
            Cancelar
          </button>
          <PrimaryButton label={guardando ? 'Guardando…' : 'Crear ejercicio'} type="submit" disabled={guardando} />
        </div>
      </form>
    </div>
  );
}
