import { useEffect, useState } from 'react';
import { HeartPulse, MessageCircle, Phone, Plus, Star, Trash2, X } from 'lucide-react';
import { InputField, PrimaryButton, TelefonoField } from '../../components/ui';
import { colors } from '../../config';
import { mensajeDeError } from '../../services/api';
import {
  agregarContactoEmergencia,
  borrarContactoEmergencia,
  type ContactoEmergencia,
  editarContactoEmergencia,
  listarContactosEmergencia,
  type SocioListado,
} from '../../services/sociosService';
import { useUiStore } from '../../store/uiStore';
import { linkWhatsapp, soloDigitos } from '../../utils/contacto';

// Los contactos de emergencia de un socio, a un toque de la grilla.
//
// No existía en ninguna pantalla del personal: el dato se cargaba (el socio
// desde "Mi perfil") y nadie del gimnasio podía verlo, que es exactamente
// cuando hace falta. Muestra el número GRANDE —si la PC no puede llamar,
// alguien lo marca en su celular— y ofrece llamar (tel:, que en un celular
// marca solo) y WhatsApp.
//
// POR QUÉ SON VARIOS Y NO UNO
// ---------------------------
// Contacto_Emergencia es 1:N desde el primer día: el COMMENT de la tabla dice
// "Multivaluado, por eso tabla propia y no columnas de Persona". Pero la app
// entraba y salía por tres campos sueltos (emergencia_nombre/telefono/
// parentesco) que hacían upsert de UNA fila, así que cargar a la madre pisaba
// a la pareja. En una emergencia se llama al que atienda, no al único que
// entró en el formulario.
//
// Mismo molde que TelefonosModal, que ya resolvió exactamente este problema
// para los teléfonos: lista + alta abajo, uno marcado como principal.

interface EmergenciaModalProps {
  socio: SocioListado;
  /** Con acceso de sólo lectura se ven los contactos pero no se tocan. */
  puedeGestionar: boolean;
  onClose: () => void;
  /** Se llama cuando cambió el principal, que es el que muestra la ficha. */
  onCambio: () => void;
}

export function EmergenciaModal({
  socio,
  puedeGestionar,
  onClose,
  onCambio,
}: EmergenciaModalProps) {
  const showSnack = useUiStore((s) => s.showSnack);
  const confirmDialog = useUiStore((s) => s.confirmDialog);

  const [contactos, setContactos] = useState<ContactoEmergencia[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intento, setIntento] = useState(0);
  const [guardando, setGuardando] = useState(false);

  const [nombre, setNombre] = useState('');
  const [telefono, setTelefono] = useState('');
  const [parentesco, setParentesco] = useState('');

  useEffect(() => {
    let cancelado = false;
    setError(null);
    listarContactosEmergencia(socio.idSocio)
      .then((lista) => {
        if (!cancelado) setContactos(lista);
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
    if (nombre.trim().length === 0) {
      showSnack('Escribí a quién hay que llamar.', colors.statusDanger);
      return;
    }
    if (telefono.trim().length === 0) {
      showSnack('Escribí un número.', colors.statusDanger);
      return;
    }
    setGuardando(true);
    try {
      // `principal: false` a secas: el backend marca principal al PRIMERO
      // aunque no se lo pidan, porque una ficha con contactos donde ninguno es
      // el principal no muestra ninguno en la grilla.
      await agregarContactoEmergencia(socio.idSocio, {
        nombre,
        telefono,
        parentesco,
        principal: false,
      });
      showSnack('Contacto agregado.', colors.statusOk);
      setNombre('');
      setTelefono('');
      setParentesco('');
      recargar();
      onCambio();
    } catch (err) {
      showSnack(mensajeDeError(err), colors.statusDanger);
    } finally {
      setGuardando(false);
    }
  };

  const marcarPrincipal = (contacto: ContactoEmergencia) => {
    editarContactoEmergencia(socio.idSocio, contacto.idContactoEmergencia, {
      nombre: contacto.nombre,
      telefono: contacto.telefono,
      parentesco: contacto.parentesco ?? '',
      principal: true,
    })
      .then(() => {
        showSnack('Ahora es el contacto principal.', colors.statusOk);
        recargar();
        onCambio();
      })
      .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
  };

  const pedirBorrar = (contacto: ContactoEmergencia) => {
    confirmDialog(
      `¿Borrar a ${contacto.nombre}?`,
      contacto.principal
        ? 'Es el contacto principal. Si quedan otros cargados, el más viejo pasa a ocupar su lugar.'
        : 'Se saca el contacto de la ficha.',
      () => {
        borrarContactoEmergencia(socio.idSocio, contacto.idContactoEmergencia)
          .then(() => {
            showSnack('Contacto borrado.', colors.statusOk);
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
        <div className="flex items-start justify-between gap-3 border-b border-border-idle p-6 pb-4">
          <div className="flex min-w-0 items-center gap-2">
            <HeartPulse size={18} className="shrink-0 text-status-danger" />
            <div className="min-w-0">
              <h2 className="truncate font-heading text-lg font-semibold text-text-main">
                Contactos de emergencia
              </h2>
              <p className="font-body text-sm text-text-secondary">{socio.nombreCompleto}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            title="Cerrar"
            className="shrink-0 rounded-md p-1 text-text-muted hover:bg-surface-hover hover:text-text-main"
          >
            <X size={18} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {error && <p className="font-body text-sm text-status-danger">{error}</p>}

          {!error && contactos === null && (
            <p className="font-body text-sm text-text-muted">Cargando…</p>
          )}

          {!error && contactos !== null && (
            <>
              {contactos.length === 0 ? (
                <p className="font-body text-sm text-text-secondary">
                  No tiene ningún contacto de emergencia cargado. Se carga acá, o lo completa
                  el socio en su perfil.
                </p>
              ) : (
                <p className="font-body text-xs text-text-muted">
                  Al principal se lo llama primero, y es el que aparece en la ficha.
                </p>
              )}

              <ul className="mt-4 flex flex-col gap-3">
                {contactos.map((c) => (
                  <li
                    key={c.idContactoEmergencia}
                    className="rounded-md border border-border-idle p-4"
                  >
                    <div className="flex items-start gap-3">
                      <div className="min-w-0 flex-1">
                        <p className="font-body text-sm text-text-main">
                          {c.nombre}
                          {c.parentesco && (
                            <span className="text-text-muted"> · {c.parentesco}</span>
                          )}
                        </p>
                        {/* El número GRANDE: si la PC del mostrador no puede
                            llamar, alguien lo marca en su celular leyéndolo. */}
                        <p className="mt-1 font-mono text-2xl font-bold text-primary-volt">
                          {c.telefono}
                        </p>
                        {c.principal && (
                          <p className="mt-1 font-body text-xs text-text-muted">principal</p>
                        )}
                      </div>

                      {puedeGestionar && !c.principal && (
                        <button
                          type="button"
                          onClick={() => marcarPrincipal(c)}
                          title="Marcarlo como principal"
                          className="shrink-0 rounded-md p-1.5 text-text-muted hover:bg-surface-hover hover:text-primary-volt"
                        >
                          <Star size={15} />
                        </button>
                      )}
                      {puedeGestionar && (
                        <button
                          type="button"
                          onClick={() => pedirBorrar(c)}
                          title="Borrarlo de la ficha"
                          className="shrink-0 rounded-md p-1.5 text-text-muted hover:bg-surface-hover hover:text-status-danger"
                        >
                          <Trash2 size={15} />
                        </button>
                      )}
                    </div>

                    <div className="mt-3 grid grid-cols-2 gap-3">
                      <a
                        href={`tel:${soloDigitos(c.telefono)}`}
                        className="inline-flex shrink-0 items-center justify-center gap-2 rounded-md bg-status-danger px-3 py-2 font-body text-sm font-semibold whitespace-nowrap text-white hover:opacity-90"
                      >
                        <Phone size={14} /> Llamar
                      </a>
                      <a
                        href={linkWhatsapp(c.telefono)}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex shrink-0 items-center justify-center gap-2 rounded-md border border-border-idle px-3 py-2 font-body text-sm whitespace-nowrap text-text-main hover:border-primary-volt"
                      >
                        <MessageCircle size={14} /> WhatsApp
                      </a>
                    </div>
                  </li>
                ))}
              </ul>

              {puedeGestionar && (
                <div className="mt-6 flex flex-col gap-4 border-t border-border-idle pt-5">
                  <InputField
                    label="Agregar contacto"
                    value={nombre}
                    onChange={setNombre}
                    hint="Nombre y apellido"
                    name="nombreEmergencia"
                  />
                  <TelefonoField
                    label="Teléfono"
                    value={telefono}
                    onChange={setTelefono}
                    name="telefonoEmergencia"
                  />
                  <InputField
                    label="Parentesco"
                    value={parentesco}
                    onChange={setParentesco}
                    hint="Madre, pareja, hermano…"
                    name="parentescoEmergencia"
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
