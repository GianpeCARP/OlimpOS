import { useEffect, useState } from 'react';
import { MessageCircle, Phone, Plus, Star, Trash2, X } from 'lucide-react';
import { PrimaryButton, SelectField, type SelectOption, TelefonoField } from '../../components/ui';
import { colors } from '../../config';
import { mensajeDeError } from '../../services/api';
import {
  agregarTelefono,
  borrarTelefono,
  editarTelefono,
  listarTelefonos,
  type SocioListado,
  type TelefonoDeSocio,
  type TipoTelefono,
} from '../../services/sociosService';
import { useUiStore } from '../../store/uiStore';
import { linkWhatsapp } from '../../utils/contacto';

// Los teléfonos de un socio, que hasta acá eran uno solo.
//
// POR QUÉ UN MODAL APARTE Y NO UN CAMPO MÁS DE LA FICHA
// -----------------------------------------------------
// La tabla Telefono existe desde el primer día justamente porque una persona
// tiene varios números, pero el formulario de la ficha tenía UN campo y el
// backend le pisaba el principal. Cargar un segundo número pasa en otro
// momento —el socio lo dicta en el mostrador— y no tiene por qué obligar a
// reenviar nombre, email y objetivo, que es como se pisan datos sin querer.
//
// Mismo molde que PatologiasModal: lista + formulario de alta abajo, y el
// modal no recarga la grilla al cerrarse porque el teléfono no es una de sus
// columnas… salvo que cambie el PRINCIPAL, que sí es el que la ficha muestra
// (ver `onCambio`).

const OPCIONES_TIPO: SelectOption[] = [
  { value: 'CELULAR', label: 'Celular' },
  { value: 'FIJO', label: 'Fijo' },
];

interface TelefonosModalProps {
  socio: SocioListado;
  /** Con acceso de sólo lectura se ven los números pero no se tocan. */
  puedeGestionar: boolean;
  onClose: () => void;
  /** Se llama cuando cambió algo que la ficha del socio muestra. */
  onCambio: () => void;
}

export function TelefonosModal({ socio, puedeGestionar, onClose, onCambio }: TelefonosModalProps) {
  const showSnack = useUiStore((s) => s.showSnack);
  const confirmDialog = useUiStore((s) => s.confirmDialog);

  const [telefonos, setTelefonos] = useState<TelefonoDeSocio[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intento, setIntento] = useState(0);
  const [guardando, setGuardando] = useState(false);

  const [numero, setNumero] = useState('');
  const [tipo, setTipo] = useState<TipoTelefono>('CELULAR');

  useEffect(() => {
    let cancelado = false;
    setError(null);
    listarTelefonos(socio.idSocio)
      .then((lista) => {
        if (!cancelado) setTelefonos(lista);
      })
      .catch((err: unknown) => {
        if (!cancelado) setError(mensajeDeError(err));
      });
    return () => {
      cancelado = true;
    };
  }, [socio.idSocio, intento]);

  const recargar = () => setIntento((n) => n + 1);

  const agregar = async () => {
    if (numero.trim().length === 0) {
      showSnack('Escribí un número.', colors.statusDanger);
      return;
    }
    setGuardando(true);
    try {
      // `principal: false` a secas: el backend marca principal al PRIMERO de
      // la ficha aunque no se lo pidan, porque una ficha con teléfonos donde
      // ninguno es el principal no muestra ninguno.
      await agregarTelefono(socio.idSocio, { numero, tipo, principal: false });
      showSnack('Teléfono agregado.', colors.statusOk);
      setNumero('');
      setTipo('CELULAR');
      recargar();
      onCambio();
    } catch (err) {
      showSnack(mensajeDeError(err), colors.statusDanger);
    } finally {
      setGuardando(false);
    }
  };

  const marcarPrincipal = (telefono: TelefonoDeSocio) => {
    editarTelefono(socio.idSocio, telefono.idTelefono, {
      numero: telefono.numero,
      tipo: telefono.tipo,
      principal: true,
    })
      .then(() => {
        showSnack('Ahora es el teléfono principal.', colors.statusOk);
        recargar();
        onCambio();
      })
      .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
  };

  const pedirBorrar = (telefono: TelefonoDeSocio) => {
    confirmDialog(
      `¿Borrar el ${telefono.numero}?`,
      telefono.principal
        ? 'Es el teléfono principal. Si quedan otros cargados, el más viejo pasa a ocupar su lugar.'
        : 'Se saca el número de la ficha.',
      () => {
        borrarTelefono(socio.idSocio, telefono.idTelefono)
          .then(() => {
            showSnack('Teléfono borrado.', colors.statusOk);
            recargar();
            onCambio();
          })
          .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
      },
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="flex max-h-[85vh] w-full max-w-lg flex-col rounded-lg border border-border-idle bg-surface-card">
        <div className="flex items-start justify-between border-b border-border-idle p-6 pb-4">
          <div>
            <h2 className="font-heading text-lg font-semibold text-text-main">Teléfonos</h2>
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

          {!error && telefonos === null && (
            <p className="font-body text-sm text-text-muted">Cargando…</p>
          )}

          {!error && telefonos !== null && (
            <>
              <p className="font-body text-xs text-text-muted">
                El principal es el que aparece en la ficha y al que se llama primero.
              </p>

              <ul className="mt-4 flex flex-col gap-2">
                {telefonos.length === 0 && (
                  <li className="font-body text-sm text-text-muted">
                    No tiene ningún teléfono cargado.
                  </li>
                )}
                {telefonos.map((t) => (
                  <li
                    key={t.idTelefono}
                    className="flex items-center gap-3 rounded-md border border-border-idle p-3"
                  >
                    <Phone size={16} className="shrink-0 text-primary-volt" />
                    <div className="min-w-0 flex-1">
                      <p className="font-body text-sm text-text-main">{t.numero}</p>
                      <p className="font-body text-xs text-text-muted">
                        {t.tipo === 'FIJO' ? 'Fijo' : 'Celular'}
                        {t.principal && ' · principal'}
                      </p>
                    </div>

                    {/* Sólo a un celular se le puede mandar un WhatsApp; a un
                        fijo el link abriría una conversación que no existe. */}
                    {t.tipo === 'CELULAR' && (
                      <a
                        href={linkWhatsapp(t.numero)}
                        target="_blank"
                        rel="noreferrer"
                        title={`WhatsApp a ${t.numero}`}
                        className="rounded-md p-1.5 text-text-muted hover:bg-surface-hover hover:text-text-main"
                      >
                        <MessageCircle size={15} />
                      </a>
                    )}

                    {puedeGestionar && !t.principal && (
                      <button
                        type="button"
                        onClick={() => marcarPrincipal(t)}
                        title="Marcarlo como principal"
                        className="rounded-md p-1.5 text-text-muted hover:bg-surface-hover hover:text-primary-volt"
                      >
                        <Star size={15} />
                      </button>
                    )}
                    {puedeGestionar && (
                      <button
                        type="button"
                        onClick={() => pedirBorrar(t)}
                        title="Borrarlo de la ficha"
                        className="rounded-md p-1.5 text-text-muted hover:bg-surface-hover hover:text-status-danger"
                      >
                        <Trash2 size={15} />
                      </button>
                    )}
                  </li>
                ))}
              </ul>

              {puedeGestionar && (
                <div className="mt-6 flex flex-col gap-4 border-t border-border-idle pt-5">
                  <TelefonoField
                    label="Agregar teléfono"
                    value={numero}
                    onChange={setNumero}
                    name="numeroTelefono"
                  />
                  <SelectField
                    label="Tipo"
                    value={tipo}
                    onChange={(v: string) => setTipo(v as TipoTelefono)}
                    options={OPCIONES_TIPO}
                    name="tipoTelefono"
                  />
                  <div className="flex justify-end">
                    <PrimaryButton
                      label={guardando ? 'Guardando…' : 'Agregar'}
                      icon={Plus}
                      onClick={() => void agregar()}
                      disabled={guardando}
                    />
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
