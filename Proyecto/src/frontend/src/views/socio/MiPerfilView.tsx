import { useCallback, useEffect, useState, type SubmitEvent } from 'react';
import { CalendarDays, IdCard, Mail, MapPin, Phone, ShieldAlert, Users } from 'lucide-react';
import {
  InputField,
  PrimaryButton,
  SectionCard,
  StatusBadge,
  Topbar,
} from '../../components/ui';
import { colors } from '../../config';
import { mensajeDeError } from '../../services/api';
import {
  getMiPerfil,
  actualizarMisDatosDeContacto,
  type MiPerfil,
} from '../../services/socioService';
import { useAuthStore } from '../../store/authStore';
import { useUiStore } from '../../store/uiStore';
import { formatearFecha, formatearFechaConAnio } from '../../utils/format';
import { parsearFecha } from '../../utils/fechas';
import { MisCondicionesCard } from './MisCondicionesCard';
import { SinSocioEnSesion } from './SinSocioEnSesion';

// Vista 1 del portal (docs/prompt_portal_socio.md).
//
// Componentes reutilizados, ninguno nuevo: Topbar, SectionCard, StatusBadge,
// InputField y PrimaryButton. La única pieza propia del portal es
// SinSocioEnSesion, y no es un componente de diseño sino un estado de error
// que sólo puede pasar en estas rutas.
//
// La vista está partida en bloques a propósito, y el orden importa:
//
//   1. "Tus datos" — SOLO LECTURA. Lo que el socio no puede cambiar (dni,
//      nombre, sede, plan, número de socio). Va primero porque es lo que
//      viene a consultar.
//   2. "Datos de contacto" — el formulario de la ficha. Todo lo editable
//      junto, separado visualmente del bloque de arriba.
//   3. "Tu salud" — sus patologías. Va último porque es lo que menos se
//      toca: se declara una vez y no se vuelve. Es un componente aparte
//      (MisCondicionesCard) porque habla con otros endpoints y con su propio
//      estado de carga.
//
// Esa separación no es estética: si los campos editables y los fijos
// estuvieran mezclados en una sola grilla, la diferencia entre "no lo podés
// cambiar" y "todavía no lo cargaste" quedaría dependiendo de si el input
// está deshabilitado, que es la clase de detalle que se rompe en silencio.
// Acá directamente no hay input para lo que no se toca.

/** Fila de dato de sólo lectura. Local: no la usa ninguna otra vista. */
function Dato({
  icono: Icono,
  etiqueta,
  valor,
}: {
  icono: typeof Mail;
  etiqueta: string;
  valor?: string;
}) {
  return (
    <div className="flex items-start gap-3">
      <Icono size={16} className="mt-0.5 shrink-0 text-text-muted" />
      <div className="min-w-0">
        <p className="font-body text-xs text-text-muted">{etiqueta}</p>
        {/* Sin dato se muestra un guión y no el string vacío: deja claro que
            el campo existe y está sin cargar, en vez de parecer un bug. */}
        <p className="font-body text-sm break-words text-text-main">{valor || '—'}</p>
      </div>
    </div>
  );
}

function Skeleton({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-md bg-surface-hover ${className}`} />;
}

export function MiPerfilView() {
  const idSocio = useAuthStore((s) => s.idSocio);
  const showSnack = useUiStore((s) => s.showSnack);

  const [perfil, setPerfil] = useState<MiPerfil | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intento, setIntento] = useState(0);
  const [guardando, setGuardando] = useState(false);

  // Un state por campo editable, igual que en los formularios de admin. Se
  // inicializan vacíos y se llenan cuando llega el perfil (no se puede usar
  // el valor inicial de useState porque en el primer render todavía no
  // existe).
  const [email, setEmail] = useState('');
  const [telefono, setTelefono] = useState('');
  const [emergenciaNombre, setEmergenciaNombre] = useState('');
  const [emergenciaTelefono, setEmergenciaTelefono] = useState('');
  const [emergenciaParentesco, setEmergenciaParentesco] = useState('');

  /**
   * Vuelca el perfil recibido en los campos del formulario. Se llama al
   * cargar y después de guardar, para que lo que se ve sea siempre lo que
   * quedó guardado (el service normaliza: recorta espacios, baja el mail a
   * minúsculas). Si no se resincronizara, el input seguiría mostrando lo
   * tipeado y no lo persistido.
   */
  const volcarEnFormulario = useCallback((datos: MiPerfil) => {
    setEmail(datos.email ?? '');
    setTelefono(datos.telefono ?? '');
    setEmergenciaNombre(datos.emergenciaNombre ?? '');
    setEmergenciaTelefono(datos.emergenciaTelefono ?? '');
    setEmergenciaParentesco(datos.emergenciaParentesco ?? '');
  }, []);

  useEffect(() => {
    if (idSocio === null) return;
    let cancelado = false;
    setPerfil(null);
    setError(null);
    getMiPerfil()
      .then((datos) => {
        if (cancelado) return;
        setPerfil(datos);
        volcarEnFormulario(datos);
      })
      .catch((err: unknown) => {
        if (!cancelado) setError(mensajeDeError(err));
      });
    return () => {
      cancelado = true;
    };
  }, [idSocio, intento, volcarEnFormulario]);

  const recargar = useCallback(() => setIntento((n) => n + 1), []);

  const handleSubmit = async (e: SubmitEvent) => {
    e.preventDefault();
    if (idSocio === null) return;
    setGuardando(true);
    try {
      const actualizado = await actualizarMisDatosDeContacto({ email, telefono, emergenciaNombre, emergenciaTelefono, emergenciaParentesco }
      );
      setPerfil(actualizado);
      volcarEnFormulario(actualizado);
      showSnack('Listo, actualizamos tus datos', colors.statusOk);
    } catch (err) {
      showSnack(mensajeDeError(err), colors.statusDanger);
    } finally {
      setGuardando(false);
    }
  };

  // Una cuenta con rol socio pero sin fila Socio no debería existir, pero si
  // existe hay que decirlo y no renderizar un perfil vacío.
  if (idSocio === null) {
    return <SinSocioEnSesion titulo="Mi perfil" />;
  }

  return (
    <div>
      <Topbar
        title="Mi perfil"
        subtitle={perfil ? `Socio ${perfil.numeroSocio ?? ''}`.trim() : undefined}
      />

      <div className="space-y-4 p-4 md:p-8">
        {error && (
          <SectionCard>
            <p className="mb-4 font-body text-sm text-status-danger">{error}</p>
            <PrimaryButton label="Reintentar" onClick={recargar} />
          </SectionCard>
        )}

        {!error && !perfil && (
          <div className="space-y-4">
            <Skeleton className="h-48" />
            <Skeleton className="h-72" />
          </div>
        )}

        {!error && perfil && (
          <>
            <SectionCard title="Tus datos">
              {/* Encabezado con nombre + estado de la cuota. El StatusBadge
                  es el mismo que usa la tabla de socios del admin: si el
                  criterio de "Activo / Por vencer / Vencido" cambia en
                  membresiaService, cambia acá también. */}
              <div className="mb-5 flex flex-wrap items-center justify-between gap-3 border-b border-border-idle pb-4">
                <div>
                  <p className="font-heading text-xl font-semibold text-text-main">
                    {perfil.nombreCompleto}
                  </p>
                  <p className="font-body text-sm text-text-secondary">{perfil.plan}</p>
                </div>
                <StatusBadge status={perfil.estado} />
              </div>

              <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
                <Dato icono={IdCard} etiqueta="DNI" valor={perfil.dni} />
                <Dato
                  icono={CalendarDays}
                  etiqueta="Fecha de nacimiento"
                  // Siempre con año, no "cuando no sea el actual": una fecha
                  // de nacimiento sin año ("18-abr") no dice absolutamente
                  // nada.
                  valor={
                    perfil.fechaNacimiento
                      ? formatearFechaConAnio(parsearFecha(perfil.fechaNacimiento))
                      : undefined
                  }
                />
                <Dato icono={MapPin} etiqueta="Domicilio" valor={perfil.domicilio} />
                <Dato icono={Users} etiqueta="Sede" valor={perfil.sede} />
                <Dato
                  icono={CalendarDays}
                  etiqueta="Socio desde"
                  valor={formatearFecha(parsearFecha(perfil.fechaAlta))}
                />
                <Dato
                  icono={CalendarDays}
                  etiqueta="Vence tu cuota"
                  valor={
                    perfil.vencimiento
                      ? formatearFecha(parsearFecha(perfil.vencimiento))
                      : undefined
                  }
                />
              </div>

              <p className="mt-5 border-t border-border-idle pt-4 font-body text-xs text-text-muted">
                ¿Algo de acá está mal? Estos datos los cambia el gimnasio: acercate a recepción.
              </p>
            </SectionCard>

            <form onSubmit={handleSubmit}>
              <SectionCard title="Datos de contacto">
                <p className="mb-5 font-body text-sm text-text-secondary">
                  Esto sí lo podés editar vos. Mantenelo al día para que podamos avisarte cuando
                  vence tu cuota.
                </p>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <InputField
                    label="Email"
                    value={email}
                    onChange={setEmail}
                    icon={Mail}
                    type="email"
                    name="email"
                  />
                  <InputField
                    label="Teléfono"
                    value={telefono}
                    onChange={setTelefono}
                    icon={Phone}
                    type="tel"
                    name="telefono"
                  />
                </div>

                <div className="mt-6 border-t border-border-idle pt-5">
                  <div className="mb-4 flex items-center gap-2">
                    <ShieldAlert size={16} className="text-accent-coral" />
                    <h3 className="font-heading text-sm font-semibold text-text-main">
                      Contacto de emergencia
                    </h3>
                  </div>
                  <p className="mb-4 font-body text-xs text-text-muted">
                    A quién llamamos si te pasa algo entrenando. Cargá nombre y teléfono, o dejá
                    los dos vacíos.
                  </p>

                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                    <InputField
                      label="Nombre"
                      value={emergenciaNombre}
                      onChange={setEmergenciaNombre}
                      name="emergencia_nombre"
                    />
                    <InputField
                      label="Teléfono"
                      value={emergenciaTelefono}
                      onChange={setEmergenciaTelefono}
                      icon={Phone}
                      type="tel"
                      name="emergencia_telefono"
                    />
                    <InputField
                      label="Parentesco"
                      value={emergenciaParentesco}
                      onChange={setEmergenciaParentesco}
                      name="emergencia_parentesco"
                    />
                  </div>
                </div>

                <div className="mt-6 flex justify-end">
                  <PrimaryButton
                    label={guardando ? 'Guardando…' : 'Guardar cambios'}
                    type="submit"
                    disabled={guardando}
                  />
                </div>
              </SectionCard>
            </form>

            {/* Trae sus propios datos y su propio estado de carga: no depende
                de `perfil`, así que un fallo del endpoint de patologías deja
                el resto de la pantalla en pie en vez de tumbarla entera. */}
            <MisCondicionesCard />
          </>
        )}
      </div>
    </div>
  );
}
