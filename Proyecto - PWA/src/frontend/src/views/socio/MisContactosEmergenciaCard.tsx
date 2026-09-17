import { useEffect, useState } from 'react';
import { Phone, Plus, ShieldAlert, Star, Trash2 } from 'lucide-react';
import { InputField, PrimaryButton, SectionCard, TelefonoField } from '../../components/ui';
import { colors } from '../../config';
import { mensajeDeError } from '../../services/api';
import {
  agregarMiContactoEmergencia,
  borrarMiContactoEmergencia,
  editarMiContactoEmergencia,
  listarMisContactosEmergencia,
  type MiContactoEmergencia,
} from '../../services/socioService';
import { useUiStore } from '../../store/uiStore';

// Los contactos de emergencia del socio, en "Mi perfil".
//
// POR QUÉ ES UNA TARJETA APARTE Y NO TRES CAMPOS DEL FORMULARIO
// -------------------------------------------------------------
// Antes eran exactamente eso: tres campos (nombre, teléfono, parentesco)
// dentro de "Datos de contacto", que al guardar hacían upsert de UNA fila de
// Contacto_Emergencia. Pero la tabla es 1:N desde el primer día —su COMMENT
// dice "Multivaluado, por eso tabla propia y no columnas de Persona"—, así que
// el socio que quería dejar el teléfono de la madre Y el de la pareja pisaba
// uno con el otro sin enterarse de nada.
//
// Con tres campos no hay forma de arreglarlo: un formulario de campos fijos
// sólo puede describir UN contacto. Hace falta una lista, y una lista necesita
// su propio alta y su propio borrado, que es justo lo que un submit de
// "Guardar cambios" no sabe hacer.
//
// Mismo molde que MisCondicionesCard, por el mismo motivo: habla con otros
// endpoints y tiene su propio estado de carga, así que un fallo acá no tumba
// el resto de la pantalla.
//
// Su gemelo del otro lado del mostrador es EmergenciaModal, en la grilla de
// Socios: el mismo dato mirado por el personal.

export function MisContactosEmergenciaCard() {
  const showSnack = useUiStore((s) => s.showSnack);
  const confirmDialog = useUiStore((s) => s.confirmDialog);

  const [contactos, setContactos] = useState<MiContactoEmergencia[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intento, setIntento] = useState(0);
  const [guardando, setGuardando] = useState(false);

  const [nombre, setNombre] = useState('');
  const [telefono, setTelefono] = useState('');
  const [parentesco, setParentesco] = useState('');

  useEffect(() => {
    let cancelado = false;
    setError(null);
    listarMisContactosEmergencia()
      .then((lista) => {
        if (!cancelado) setContactos(lista);
      })
      .catch((err: unknown) => {
        if (!cancelado) setError(mensajeDeError(err));
      });
    return () => {
      cancelado = true;
    };
  }, [intento]);

  const recargar = () => setIntento((n) => n + 1);

  const agregar = async () => {
    if (nombre.trim().length === 0) {
      showSnack('Escribí a quién llamamos.', colors.statusDanger);
      return;
    }
    if (telefono.trim().length === 0) {
      showSnack('Escribí un número.', colors.statusDanger);
      return;
    }
    setGuardando(true);
    try {
      // `principal: false` a secas: el backend marca principal al PRIMERO
      // aunque no se lo pidan, porque si ninguno lo es el personal no ve
      // ninguno en la ficha.
      await agregarMiContactoEmergencia({ nombre, telefono, parentesco, principal: false });
      showSnack('Listo, guardamos el contacto', colors.statusOk);
      setNombre('');
      setTelefono('');
      setParentesco('');
      recargar();
    } catch (err) {
      showSnack(mensajeDeError(err), colors.statusDanger);
    } finally {
      setGuardando(false);
    }
  };

  const marcarPrincipal = (contacto: MiContactoEmergencia) => {
    editarMiContactoEmergencia(contacto.idContactoEmergencia, {
      nombre: contacto.nombre,
      telefono: contacto.telefono,
      parentesco: contacto.parentesco ?? '',
      principal: true,
    })
      .then(() => {
        showSnack('Ahora llamamos primero a ese contacto', colors.statusOk);
        recargar();
      })
      .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
  };

  const pedirBorrar = (contacto: MiContactoEmergencia) => {
    confirmDialog(
      `¿Borrar a ${contacto.nombre}?`,
      contacto.principal
        ? 'Es tu contacto principal. Si te queda algún otro cargado, pasa a ocupar su lugar.'
        : 'Lo sacamos de tu ficha.',
      () => {
        borrarMiContactoEmergencia(contacto.idContactoEmergencia)
          .then(() => {
            showSnack('Contacto borrado', colors.statusOk);
            recargar();
          })
          .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
      },
    );
  };

  return (
    <SectionCard>
      <div className="mb-4 flex items-center gap-2">
        <ShieldAlert size={16} className="text-accent-coral" />
        <h3 className="font-heading text-sm font-semibold text-text-main">
          Contactos de emergencia
        </h3>
      </div>
      <p className="mb-4 font-body text-xs text-text-muted">
        A quién llamamos si te pasa algo entrenando. Podés cargar más de uno: llamamos primero
        al principal y seguimos por los demás.
      </p>

      {error && <p className="font-body text-sm text-status-danger">{error}</p>}

      {!error && contactos === null && (
        <p className="font-body text-sm text-text-muted">Cargando…</p>
      )}

      {!error && contactos !== null && (
        <>
          <ul className="flex flex-col gap-2">
            {contactos.length === 0 && (
              <li className="font-body text-sm text-text-muted">
                Todavía no cargaste ninguno.
              </li>
            )}
            {contactos.map((c) => (
              <li
                key={c.idContactoEmergencia}
                className="flex items-center gap-3 rounded-md border border-border-idle p-3"
              >
                <Phone size={16} className="shrink-0 text-accent-coral" />
                <div className="min-w-0 flex-1">
                  <p className="font-body text-sm text-text-main">
                    {c.nombre}
                    {c.parentesco && <span className="text-text-muted"> · {c.parentesco}</span>}
                  </p>
                  <p className="mt-0.5 font-body text-xs text-text-muted">
                    {c.telefono}
                    {c.principal && ' · principal'}
                  </p>
                </div>

                {!c.principal && (
                  <button
                    type="button"
                    onClick={() => marcarPrincipal(c)}
                    title="Que llamemos primero a este"
                    className="shrink-0 rounded-md p-1.5 text-text-muted hover:bg-surface-hover hover:text-primary-volt"
                  >
                    <Star size={15} />
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => pedirBorrar(c)}
                  title="Borrarlo"
                  className="shrink-0 rounded-md p-1.5 text-text-muted hover:bg-surface-hover hover:text-status-danger"
                >
                  <Trash2 size={15} />
                </button>
              </li>
            ))}
          </ul>

          <div className="mt-6 flex flex-col gap-4 border-t border-border-idle pt-5">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <InputField
                label="Nombre"
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
            </div>
            <div className="flex justify-end">
              <PrimaryButton
                label={guardando ? 'Guardando…' : 'Agregar contacto'}
                icon={Plus}
                onClick={() => void agregar()}
                disabled={guardando}
              />
            </div>
          </div>
        </>
      )}
    </SectionCard>
  );
}
