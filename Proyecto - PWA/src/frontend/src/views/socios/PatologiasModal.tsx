import { useEffect, useMemo, useState } from 'react';
import { CalendarDays, Plus, Stethoscope, Trash2, Pencil, X } from 'lucide-react';
import { InputField, PrimaryButton, SelectField, type SelectOption } from '../../components/ui';
import { colors } from '../../config';
import { mensajeDeError } from '../../services/api';
import {
  asignarPatologia,
  crearPatologia,
  editarPatologiaDeSocio,
  listarCatalogoPatologias,
  listarPatologiasDeSocio,
  quitarPatologia,
  type PatologiaCatalogo,
  type PatologiaDeSocio,
} from '../../services/patologiasService';
import type { SocioListado } from '../../services/sociosService';
import { useUiStore } from '../../store/uiStore';
import { formatearFecha } from '../../utils/format';
import { aFechaISO, parsearFecha } from '../../utils/fechas';

// Gemelo de `_patologias` / `_editar_patologia` / `_nueva_del_catalogo` de
// `app/views/socios.py` en Flet. Allá son tres AlertDialog encadenados porque
// Flet no anida contenido dentro de un diálogo abierto; acá es UN modal con
// tres modos, que es lo idiomático en React y además no pierde el scroll de la
// lista al abrir el formulario.
//
// La otra diferencia deliberada: la fecha de diagnóstico usa un input
// type="date" nativo, que ya entrega ISO. En Flet no hay equivalente cómodo y
// el campo se escribe a mano como dd/mm/aaaa y se parsea — misma pantalla,
// distinta herramienta.
//
// QUIÉN VE ESTO: sólo quien tenga la acción `verHistorialMedico`. El
// Recepcionista entra a Socios con acceso TOTAL y NO la tiene, así que el
// botón que abre este modal no se dibuja para él (ver SocioTableRow). El
// guard de verdad está en el backend; el de la UI es para no ofrecer algo que
// va a volver 403.

interface PatologiasModalProps {
  socio: SocioListado;
  onClose: () => void;
}

/**
 * Tope del selector de fecha: no se diagnostica algo que todavía no pasó.
 *
 * El backend ya lo rechaza, pero un `max` en el input hace que el calendario
 * directamente no ofrezca los días futuros — mejor que dejar elegir y contestar
 * con un error después de mandar el formulario.
 *
 * Con `aFechaISO` y no `toISOString()`: este último pasa a UTC, y a la noche
 * (UTC-3) ya devuelve la fecha de mañana, que es justo el día que hay que
 * bloquear.
 */
function hoyISO(): string {
  return aFechaISO(new Date());
}

type Modo =
  | { tipo: 'lista' }
  | { tipo: 'editar'; patologia: PatologiaDeSocio }
  | { tipo: 'nuevaDelCatalogo' };

export function PatologiasModal({ socio, onClose }: PatologiasModalProps) {
  const showSnack = useUiStore((s) => s.showSnack);
  const confirmDialog = useUiStore((s) => s.confirmDialog);

  const [registradas, setRegistradas] = useState<PatologiaDeSocio[] | null>(null);
  const [catalogo, setCatalogo] = useState<PatologiaCatalogo[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intento, setIntento] = useState(0);

  const [modo, setModo] = useState<Modo>({ tipo: 'lista' });
  const [guardando, setGuardando] = useState(false);

  // Formulario de alta (lista) y de edición: comparten los mismos dos campos.
  const [seleccion, setSeleccion] = useState('');
  const [fecha, setFecha] = useState('');
  const [observaciones, setObservaciones] = useState('');

  // Formulario del catálogo.
  const [nombreNuevo, setNombreNuevo] = useState('');
  const [descripcionNueva, setDescripcionNueva] = useState('');

  useEffect(() => {
    let cancelado = false;
    setError(null);
    Promise.all([listarPatologiasDeSocio(socio.idSocio), listarCatalogoPatologias()])
      .then(([propias, todas]) => {
        if (cancelado) return;
        setRegistradas(propias);
        setCatalogo(todas);
      })
      .catch((err: unknown) => {
        if (!cancelado) setError(mensajeDeError(err));
      });
    return () => {
      cancelado = true;
    };
  }, [socio.idSocio, intento]);

  const recargar = () => setIntento((n) => n + 1);

  // Las que ya tiene no se vuelven a ofrecer: el backend responde 409 y
  // hacerle elegir algo que va a fallar es hacerle perder el tiempo. Mismo
  // criterio que el selector de entrenadores.
  const elegibles = useMemo(() => {
    if (!catalogo || !registradas) return [];
    const yaTiene = new Set(registradas.map((p) => p.idPatologia));
    return catalogo.filter((c) => !yaTiene.has(c.idPatologia));
  }, [catalogo, registradas]);

  const opciones: SelectOption[] = elegibles.map((c) => ({
    value: String(c.idPatologia),
    label: c.nombre,
  }));

  const limpiarFormulario = () => {
    setSeleccion('');
    setFecha('');
    setObservaciones('');
  };

  const volverALista = () => {
    setModo({ tipo: 'lista' });
    limpiarFormulario();
  };

  const agregar = async () => {
    if (seleccion === '') {
      showSnack('Elegí una condición de la lista.', colors.statusDanger);
      return;
    }
    setGuardando(true);
    try {
      await asignarPatologia(socio.idSocio, {
        idPatologia: Number(seleccion),
        fechaDiagnostico: fecha || undefined,
        observaciones,
      });
      showSnack('Condición registrada.', colors.statusOk);
      limpiarFormulario();
      recargar();
    } catch (err) {
      showSnack(mensajeDeError(err), colors.statusDanger);
    } finally {
      setGuardando(false);
    }
  };

  const guardarEdicion = async (patologia: PatologiaDeSocio) => {
    setGuardando(true);
    try {
      await editarPatologiaDeSocio(socio.idSocio, {
        idPatologia: patologia.idPatologia,
        fechaDiagnostico: fecha || undefined,
        observaciones,
      });
      showSnack('Condición actualizada.', colors.statusOk);
      volverALista();
      recargar();
    } catch (err) {
      showSnack(mensajeDeError(err), colors.statusDanger);
    } finally {
      setGuardando(false);
    }
  };

  const guardarEnCatalogo = async () => {
    if (nombreNuevo.trim().length < 2) {
      showSnack('El nombre de la condición es obligatorio.', colors.statusDanger);
      return;
    }
    setGuardando(true);
    try {
      await crearPatologia(nombreNuevo, descripcionNueva);
      showSnack('Condición agregada al catálogo.', colors.statusOk);
      setNombreNuevo('');
      setDescripcionNueva('');
      volverALista();
      recargar();
    } catch (err) {
      showSnack(mensajeDeError(err), colors.statusDanger);
    } finally {
      setGuardando(false);
    }
  };

  const pedirQuitar = (patologia: PatologiaDeSocio) => {
    confirmDialog(
      `¿Quitar «${patologia.nombre}» de la ficha?`,
      'La condición se borra de la ficha del socio. El catálogo no se toca: sigue disponible para los demás.',
      () => {
        quitarPatologia(socio.idSocio, patologia.idPatologia)
          .then(() => {
            showSnack('Condición eliminada de la ficha.', colors.statusOk);
            recargar();
          })
          .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
      },
    );
  };

  const abrirEdicion = (patologia: PatologiaDeSocio) => {
    setFecha(patologia.fechaDiagnostico ?? '');
    setObservaciones(patologia.observaciones ?? '');
    setModo({ tipo: 'editar', patologia });
  };

  const cargando = registradas === null || catalogo === null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="flex max-h-[85vh] w-full max-w-lg flex-col rounded-lg border border-border-idle bg-surface-card">
        <div className="flex items-start justify-between border-b border-border-idle p-6 pb-4">
          <div>
            <h2 className="font-heading text-lg font-semibold text-text-main">Historial médico</h2>
            <p className="font-body text-sm text-text-secondary">{socio.nombreCompleto}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            title="Cerrar"
            className="rounded-md p-1 text-text-muted hover:bg-surface-hover hover:text-text-main"
          >
            <X size={18} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {error && <p className="font-body text-sm text-status-danger">{error}</p>}

          {!error && cargando && (
            <p className="font-body text-sm text-text-muted">Cargando…</p>
          )}

          {!error && !cargando && modo.tipo === 'lista' && (
            <>
              <p className="font-body text-xs text-text-muted">
                Lo que hay que tener en cuenta al armarle una rutina o una dieta.
              </p>

              <ul className="mt-4 flex flex-col gap-2">
                {registradas.length === 0 && (
                  <li className="font-body text-sm text-text-muted">
                    No tiene ninguna condición registrada.
                  </li>
                )}
                {registradas.map((p) => (
                  <li
                    key={p.idPatologia}
                    className="flex items-start gap-3 rounded-md border border-border-idle p-3"
                  >
                    {/* Volt y no un azul: la paleta no tiene un color "info"
                        propio, y Colors.INFO de Flet es un alias de
                        PRIMARY_VOLT. Las dos apps pintan este ícono igual. */}
                    <Stethoscope size={16} className="mt-0.5 shrink-0 text-primary-volt" />
                    <div className="min-w-0 flex-1">
                      <p className="font-body text-sm text-text-main">{p.nombre}</p>
                      <p className="font-body text-xs text-text-muted">
                        {p.fechaDiagnostico
                          ? `desde ${formatearFecha(parsearFecha(p.fechaDiagnostico))}`
                          : 'sin fecha'}
                        {' · '}
                        {p.observaciones ?? p.descripcion ?? 'sin observaciones'}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => abrirEdicion(p)}
                      title="Editar fecha y observaciones"
                      className="rounded-md p-1.5 text-text-muted hover:bg-surface-hover hover:text-text-main"
                    >
                      <Pencil size={15} />
                    </button>
                    <button
                      type="button"
                      onClick={() => pedirQuitar(p)}
                      title="Quitarla de la ficha"
                      className="rounded-md p-1.5 text-text-muted hover:bg-surface-hover hover:text-status-danger"
                    >
                      <Trash2 size={15} />
                    </button>
                  </li>
                ))}
              </ul>

              <div className="mt-6 border-t border-border-idle pt-5">
                {elegibles.length > 0 ? (
                  <div className="flex flex-col gap-4">
                    <SelectField
                      label="Agregar condición"
                      value={seleccion}
                      onChange={setSeleccion}
                      options={opciones}
                      placeholder="Elegí una del catálogo"
                      name="patologia"
                    />
                    <InputField
                      label="Fecha de diagnóstico"
                      value={fecha}
                      onChange={setFecha}
                      icon={CalendarDays}
                      type="date"
                      max={hoyISO()}
                      name="fechaDiagnostico"
                    />
                    <label className="flex flex-col gap-1.5 font-body text-sm">
                      <span className="text-text-secondary">Observaciones</span>
                      <textarea
                        value={observaciones}
                        onChange={(e) => setObservaciones(e.target.value)}
                        rows={2}
                        placeholder="Ej: rodilla derecha, evitar impacto"
                        className="rounded-md border border-border-idle bg-surface-card px-3 py-2 font-body text-sm text-text-main outline-none placeholder:text-text-muted focus:border-border-active"
                      />
                    </label>
                    <div className="flex justify-end">
                      <PrimaryButton
                        label={guardando ? 'Guardando…' : 'Agregar'}
                        icon={Plus}
                        onClick={() => void agregar()}
                        disabled={guardando}
                      />
                    </div>
                  </div>
                ) : catalogo.length > 0 ? (
                  <p className="font-body text-sm text-text-muted">
                    Ya tiene registradas todas las condiciones del catálogo.
                  </p>
                ) : (
                  // Sin esto la pantalla nace muerta: la base entregada viene
                  // con el catálogo vacío, y sin una condición cargada no hay
                  // nada para elegir ni forma de salir del paso desde acá.
                  <p className="font-body text-sm text-status-warn">
                    El catálogo está vacío. Cargá la primera condición con el botón de abajo.
                  </p>
                )}

                <button
                  type="button"
                  onClick={() => setModo({ tipo: 'nuevaDelCatalogo' })}
                  className="mt-4 flex items-center gap-1.5 font-body text-sm text-text-secondary hover:text-text-main"
                >
                  <Plus size={15} />
                  ¿No está en la lista? Agregarla al catálogo
                </button>
              </div>
            </>
          )}

          {!error && !cargando && modo.tipo === 'editar' && (
            <div className="flex flex-col gap-4">
              <div>
                <p className="font-heading text-base font-semibold text-text-main">
                  {modo.patologia.nombre}
                </p>
                <p className="font-body text-xs text-text-muted">
                  El nombre no se edita acá: sale del catálogo y cambiarlo se lo cambiaría a
                  todos los socios que lo tengan.
                </p>
              </div>
              <InputField
                label="Fecha de diagnóstico"
                value={fecha}
                onChange={setFecha}
                icon={CalendarDays}
                type="date"
                max={hoyISO()}
                name="fechaDiagnosticoEdicion"
              />
              <label className="flex flex-col gap-1.5 font-body text-sm">
                <span className="text-text-secondary">Observaciones</span>
                <textarea
                  value={observaciones}
                  onChange={(e) => setObservaciones(e.target.value)}
                  rows={3}
                  placeholder="Ej: rodilla derecha, evitar impacto"
                  className="rounded-md border border-border-idle bg-surface-card px-3 py-2 font-body text-sm text-text-main outline-none placeholder:text-text-muted focus:border-border-active"
                />
              </label>
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={volverALista}
                  className="shrink-0 rounded-md px-4 py-2 font-body text-sm whitespace-nowrap text-text-secondary hover:text-text-main"
                >
                  Cancelar
                </button>
                <PrimaryButton
                  label={guardando ? 'Guardando…' : 'Guardar'}
                  onClick={() => void guardarEdicion(modo.patologia)}
                  disabled={guardando}
                />
              </div>
            </div>
          )}

          {!error && !cargando && modo.tipo === 'nuevaDelCatalogo' && (
            <div className="flex flex-col gap-4">
              <div>
                <p className="font-heading text-base font-semibold text-text-main">
                  Nueva condición del catálogo
                </p>
                {/* Son dos pasos y no uno a propósito: el catálogo es compartido
                    por todo el gimnasio, y dejar que se cargue al vuelo mientras
                    se completa una ficha es exactamente cómo terminan
                    conviviendo "Asma", "asma" y "ASMA" — que es lo que el
                    catálogo venía a evitar. */}
                <p className="font-body text-xs text-text-muted">
                  Queda disponible para todos los socios, no sólo para este.
                </p>
              </div>
              <InputField
                label="Nombre"
                value={nombreNuevo}
                onChange={setNombreNuevo}
                icon={Stethoscope}
                name="nombrePatologia"
                required
              />
              <label className="flex flex-col gap-1.5 font-body text-sm">
                <span className="text-text-secondary">Descripción</span>
                <textarea
                  value={descripcionNueva}
                  onChange={(e) => setDescripcionNueva(e.target.value)}
                  rows={3}
                  placeholder="Qué implica para el entrenamiento"
                  className="rounded-md border border-border-idle bg-surface-card px-3 py-2 font-body text-sm text-text-main outline-none placeholder:text-text-muted focus:border-border-active"
                />
              </label>
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={volverALista}
                  className="shrink-0 rounded-md px-4 py-2 font-body text-sm whitespace-nowrap text-text-secondary hover:text-text-main"
                >
                  Cancelar
                </button>
                <PrimaryButton
                  label={guardando ? 'Guardando…' : 'Guardar'}
                  onClick={() => void guardarEnCatalogo()}
                  disabled={guardando}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
