import { useEffect, useMemo, useState } from 'react';
import { CalendarDays, Plus, Stethoscope, Trash2 } from 'lucide-react';
import { InputField, PrimaryButton, SectionCard, SelectField, type SelectOption } from '../../components/ui';
import { colors } from '../../config';
import { mensajeDeError } from '../../services/api';
import {
  agregarMiCondicion,
  getCatalogoDeCondiciones,
  getMisCondiciones,
  quitarMiCondicion,
  type CondicionDelCatalogo,
  type MiCondicion,
} from '../../services/socioService';
import { useUiStore } from '../../store/uiStore';
import { formatearFecha } from '../../utils/format';
import { parsearFecha } from '../../utils/fechas';

// Tercer bloque de "Mi perfil". No tiene gemelo en Flet y no es un olvido: la
// app de escritorio la usa el PERSONAL, y el personal edita el historial de
// OTROS desde la grilla de Socios (`_patologias` en app/views/socios.py). Esto
// es el mismo dato mirado desde el otro lado del mostrador.
//
// Por qué el socio puede cargarlas él mismo: "soy asmático" es algo que él
// sabe y el gimnasio necesita, y obligarlo a ir a recepción a contarlo —donde
// además el recepcionista no debería enterarse, porque no tiene el permiso—
// sería exactamente al revés.
//
// Va abajo del formulario de contacto y no arriba porque el socio entra a esta
// pantalla a consultar sus datos y a corregir un teléfono; declarar una
// condición es algo que hace una vez.

function Skeleton({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-md bg-surface-hover ${className}`} />;
}

export function MisCondicionesCard() {
  const showSnack = useUiStore((s) => s.showSnack);
  const confirmDialog = useUiStore((s) => s.confirmDialog);

  const [mias, setMias] = useState<MiCondicion[] | null>(null);
  const [catalogo, setCatalogo] = useState<CondicionDelCatalogo[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intento, setIntento] = useState(0);

  const [abierto, setAbierto] = useState(false);
  const [seleccion, setSeleccion] = useState('');
  const [fecha, setFecha] = useState('');
  const [observaciones, setObservaciones] = useState('');
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    let cancelado = false;
    setError(null);
    Promise.all([getMisCondiciones(), getCatalogoDeCondiciones()])
      .then(([propias, todas]) => {
        if (cancelado) return;
        setMias(propias);
        setCatalogo(todas);
      })
      .catch((err: unknown) => {
        if (!cancelado) setError(mensajeDeError(err));
      });
    return () => {
      cancelado = true;
    };
  }, [intento]);

  const recargar = () => setIntento((n) => n + 1);

  // Las que ya declaró no se vuelven a ofrecer: el backend responde 409.
  const elegibles = useMemo(() => {
    if (!catalogo || !mias) return [];
    const yaTiene = new Set(mias.map((p) => p.idPatologia));
    return catalogo.filter((c) => !yaTiene.has(c.idPatologia));
  }, [catalogo, mias]);

  const opciones: SelectOption[] = elegibles.map((c) => ({
    value: String(c.idPatologia),
    label: c.nombre,
  }));

  const cerrarFormulario = () => {
    setAbierto(false);
    setSeleccion('');
    setFecha('');
    setObservaciones('');
  };

  const agregar = async () => {
    if (seleccion === '') {
      showSnack('Elegí una condición de la lista.', colors.statusDanger);
      return;
    }
    setGuardando(true);
    try {
      await agregarMiCondicion({
        idPatologia: Number(seleccion),
        fechaDiagnostico: fecha || undefined,
        observaciones,
      });
      showSnack('Listo, quedó registrada.', colors.statusOk);
      cerrarFormulario();
      recargar();
    } catch (err) {
      showSnack(mensajeDeError(err), colors.statusDanger);
    } finally {
      setGuardando(false);
    }
  };

  const pedirQuitar = (condicion: MiCondicion) => {
    confirmDialog(
      `¿Sacar «${condicion.nombre}» de tu ficha?`,
      'Tu entrenador y tu nutricionista dejan de verla al armarte una rutina o una dieta.',
      () => {
        quitarMiCondicion(condicion.idPatologia)
          .then(() => {
            showSnack('Listo, la sacamos de tu ficha.', colors.statusOk);
            recargar();
          })
          .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
      },
    );
  };

  if (error) {
    return (
      <SectionCard title="Tu salud">
        <p className="mb-4 font-body text-sm text-status-danger">{error}</p>
        <PrimaryButton label="Reintentar" onClick={recargar} />
      </SectionCard>
    );
  }

  if (mias === null || catalogo === null) {
    return (
      <SectionCard title="Tu salud">
        <Skeleton className="h-24" />
      </SectionCard>
    );
  }

  return (
    <SectionCard title="Tu salud">
      <p className="mb-5 font-body text-sm text-text-secondary">
        Contanos qué condiciones tenés. Tu entrenador y tu nutricionista las ven al armarte una
        rutina o una dieta — una rodilla operada cambia el entrenamiento y una celiaquía cambia
        la dieta. Recepción no las ve.
      </p>

      <ul className="flex flex-col gap-2">
        {mias.length === 0 && (
          <li className="font-body text-sm text-text-muted">
            No tenés ninguna condición cargada.
          </li>
        )}
        {mias.map((c) => (
          <li
            key={c.idPatologia}
            className="flex items-start gap-3 rounded-md border border-border-idle p-3"
          >
            <Stethoscope size={16} className="mt-0.5 shrink-0 text-primary-volt" />
            <div className="min-w-0 flex-1">
              <p className="font-body text-sm text-text-main">{c.nombre}</p>
              <p className="font-body text-xs text-text-muted">
                {c.fechaDiagnostico
                  ? `desde ${formatearFecha(parsearFecha(c.fechaDiagnostico))}`
                  : 'sin fecha'}
                {' · '}
                {c.observaciones ?? c.descripcion ?? 'sin observaciones'}
              </p>
            </div>
            <button
              type="button"
              onClick={() => pedirQuitar(c)}
              title="Sacarla de tu ficha"
              className="rounded-md p-1.5 text-text-muted hover:bg-surface-hover hover:text-status-danger"
            >
              <Trash2 size={15} />
            </button>
          </li>
        ))}
      </ul>

      <div className="mt-5 border-t border-border-idle pt-5">
        {!abierto ? (
          <button
            type="button"
            onClick={() => setAbierto(true)}
            disabled={elegibles.length === 0}
            className="flex items-center gap-1.5 font-body text-sm text-text-secondary hover:text-text-main disabled:cursor-not-allowed disabled:text-text-muted disabled:hover:text-text-muted"
          >
            <Plus size={15} />
            Agregar una condición
          </button>
        ) : (
          <div className="flex flex-col gap-4">
            <SelectField
              label="¿Cuál?"
              value={seleccion}
              onChange={setSeleccion}
              options={opciones}
              placeholder="Elegí una de la lista"
              name="miCondicion"
            />
            <InputField
              label="¿Desde cuándo?"
              value={fecha}
              onChange={setFecha}
              icon={CalendarDays}
              type="date"
              name="miCondicionFecha"
            />
            <label className="flex flex-col gap-1.5 font-body text-sm">
              <span className="text-text-secondary">Algo que debamos saber</span>
              <textarea
                value={observaciones}
                onChange={(e) => setObservaciones(e.target.value)}
                rows={2}
                placeholder="Ej: es la rodilla derecha, no puedo hacer impacto"
                className="rounded-md border border-border-idle bg-surface-card px-3 py-2 font-body text-sm text-text-main outline-none placeholder:text-text-muted focus:border-border-active"
              />
            </label>
            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={cerrarFormulario}
                className="shrink-0 rounded-md px-4 py-2 font-body text-sm whitespace-nowrap text-text-secondary hover:text-text-main"
              >
                Cancelar
              </button>
              <PrimaryButton
                label={guardando ? 'Guardando…' : 'Agregar'}
                onClick={() => void agregar()}
                disabled={guardando}
              />
            </div>
          </div>
        )}

        {/* El socio NO puede inventar condiciones: el catálogo lo mantiene el
            staff. Sin este aviso, alguien que no encuentra la suya en la lista
            no tiene forma de saber que existe un camino. */}
        {elegibles.length === 0 && (
          <p className="mt-2 font-body text-xs text-text-muted">
            {catalogo.length === 0
              ? 'Todavía no hay condiciones cargadas en el sistema.'
              : 'Ya cargaste todas las de la lista.'}{' '}
            Si la tuya no está, pedile a tu entrenador o al nutricionista que la agregue.
          </p>
        )}
      </div>
    </SectionCard>
  );
}
