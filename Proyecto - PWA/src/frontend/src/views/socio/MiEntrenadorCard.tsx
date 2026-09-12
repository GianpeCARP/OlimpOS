import { useEffect, useState } from 'react';
import { User } from 'lucide-react';
import { SectionCard } from '../../components/ui';
import { mensajeDeError } from '../../services/api';
import { getMisEntrenadores, type MiEntrenador } from '../../services/socioService';
import { formatearFecha } from '../../utils/format';
import { parsearFecha } from '../../utils/fechas';

// Quién entrena al socio. Va arriba de la rutina en MiRutinaView.
//
// NO ES LO MISMO que el `Te la armó X` del encabezado de esa vista: aquél es
// quien ARMÓ la plantilla, un dato de la rutina. Esto es quien está a cargo
// del socio, y pueden ser personas distintas. Más importante: puede haber
// entrenador a cargo SIN rutina asignada todavía —es el caso normal de alguien
// que recién arranca— y por eso esta card se dibuja aunque `getMiRutina`
// devuelva null. Si viviera adentro del bloque de la rutina, justo el socio
// nuevo, que es el que más necesita saber a quién preguntarle, no lo vería.
//
// Sin historial, a diferencia del modal del personal: el backend sólo devuelve
// las asignaciones ACTIVAS. Al socio le interesa a quién preguntarle hoy, no
// quién lo entrenaba en marzo.
//
// Si no tiene ninguno, no se dibuja NADA. Una card vacía diciendo "no tenés
// entrenador" en una pantalla que ya tiene su propio estado vacío para la
// rutina sería un segundo cartel de ausencia para el mismo socio nuevo.

export function MiEntrenadorCard() {
  const [entrenadores, setEntrenadores] = useState<MiEntrenador[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelado = false;
    getMisEntrenadores()
      .then((lista) => {
        if (!cancelado) setEntrenadores(lista);
      })
      .catch((err: unknown) => {
        if (!cancelado) setError(mensajeDeError(err));
      });
    return () => {
      cancelado = true;
    };
  }, []);

  // Un fallo acá no tumba la pantalla: la rutina es lo que el socio vino a
  // ver, y quedarse sin saber el nombre del entrenador no justifica taparla.
  if (error || !entrenadores || entrenadores.length === 0) return null;

  return (
    <SectionCard title={entrenadores.length === 1 ? 'Tu entrenador' : 'Tus entrenadores'}>
      <div className="flex flex-col gap-3">
        {entrenadores.map((e) => (
          <div key={e.idAsignacion} className="flex items-center gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-surface-hover">
              <User size={16} className="text-primary-volt" />
            </div>
            <div className="min-w-0">
              <p className="font-body text-sm text-text-main">{e.nombre}</p>
              <p className="font-body text-xs text-text-muted">
                {e.especialidad ?? 'Entrenador'}
                {' · '}
                desde {formatearFecha(parsearFecha(e.desde))}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Explica el caso de los dos a la vez, que sorprende si no se avisa. */}
      {entrenadores.length > 1 && (
        <p className="mt-4 border-t border-border-idle pt-4 font-body text-xs text-text-muted">
          Tenés más de uno porque cada uno se ocupa de algo distinto — por ejemplo, musculación y
          funcional.
        </p>
      )}
    </SectionCard>
  );
}
