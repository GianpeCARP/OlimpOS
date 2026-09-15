import { X } from 'lucide-react';
import { urlDelBackend } from '../../services/api';

// El video tutorial de un ejercicio, a pantalla completa encima de lo que haya.
//
// El archivo lo bajó el demonio del servidor desde el canal del gimnasio
// (backend/demonio_videos.py), así que se reproduce desde el servidor propio y
// no depende de YouTube.

interface VerTecnicaProps {
  nombre: string;
  video: string;
  onCerrar: () => void;
}

export function VerTecnica({ nombre, video, onCerrar }: VerTecnicaProps) {
  return (
    <div className="fixed inset-0 z-[60] flex h-full flex-col bg-surface-base">
      <header className="flex shrink-0 items-center justify-between gap-3 px-5 pt-4">
        <p className="truncate font-heading text-base font-semibold text-text-main">{nombre}</p>
        <button
          type="button"
          onClick={onCerrar}
          aria-label="Cerrar video"
          className="shrink-0 rounded-md p-2 text-text-muted hover:bg-surface-hover hover:text-text-main"
        >
          <X size={20} />
        </button>
      </header>
      {/* min-h-0: un hijo flex no se achica por debajo de su contenido, así
          que sin esto un video vertical (los shorts) quedaba más alto que la
          ventana y la barra de controles caía fuera de la pantalla. */}
      <div className="flex min-h-0 flex-1 items-center justify-center p-4">
        {/* playsInline: sin esto el iPhone lo abre en su reproductor a
            pantalla completa y al cerrarlo no vuelve acá. */}
        <video
          src={urlDelBackend(video)}
          controls
          autoPlay
          playsInline
          className="h-full w-full rounded-lg bg-black object-contain"
        />
      </div>
    </div>
  );
}
