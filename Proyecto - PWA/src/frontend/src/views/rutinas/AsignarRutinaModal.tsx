import { asignarRutinaASocio, type RutinaListado } from '../../services/rutinasService';
import { AsignarASocioModal } from '../socios/AsignarASocioModal';

// Asignar una rutina a un socio. El modal es el genérico (AsignarASocioModal),
// que también usa Nutrición para asignar planes.
interface AsignarRutinaModalProps {
  rutina: RutinaListado;
  onClose: () => void;
  onAsignada: () => void;
}

export function AsignarRutinaModal({ rutina, onClose, onAsignada }: AsignarRutinaModalProps) {
  return (
    <AsignarASocioModal
      titulo="Asignar rutina"
      subtitulo={rutina.nombre}
      aviso="Si el socio ya sigue otra rutina, se la finaliza y queda en su historial."
      mensajeExito={(s) => `"${rutina.nombre}" asignada a ${s.nombreCompleto}`}
      onAsignar={(s) => asignarRutinaASocio(rutina.idRutina, s.idSocio)}
      onClose={onClose}
      onAsignada={onAsignada}
    />
  );
}
