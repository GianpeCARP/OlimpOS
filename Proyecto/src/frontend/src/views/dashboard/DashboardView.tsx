import { useCallback, useEffect, useState, type CSSProperties } from 'react';
import { useNavigate } from 'react-router';
import {
  Users,
  Banknote,
  CalendarCheck,
  UserPlus,
  Dumbbell,
  Apple,
  type LucideIcon,
} from 'lucide-react';
import { Topbar, StatCard, SectionCard, PrimaryButton } from '../../components/ui';
import { colors, Routes, puedeVerRuta, type RouteValue } from '../../config';
import { mensajeDeError } from '../../services/api';
import {
  obtenerEstadisticas,
  obtenerActividadReciente,
  obtenerSociosRecientes,
  type DashboardStats,
  type EventoActividad,
  type Metrica,
  type SocioResumen,
} from '../../services/dashboardService';
import { useAuthStore } from '../../store/authStore';
import { usePuedeAccion } from '../../hooks/usePermisos';
import { formatearDelta, formatearMoneda, formatearNumero } from '../../utils/format';
import { ActivityItem } from './ActivityItem';
import { SocioRow } from './SocioRow';
import { QuickAction } from './QuickAction';

// Equivalente de DashboardView.build() (estructura_dashboard.md). Vive en su
// propia carpeta porque es la primera vista con piezas propias
// (_activity_item, _socio_row, _quick_btn); las vistas de un solo archivo
// siguen sueltas en views/.

// Ancho del panel de accesos rápidos — estructura_dashboard.md lo fija en
// 240px. Va como custom property porque el ancho solo aplica de `lg` para
// arriba (abajo de eso el panel ocupa todo el ancho) y un style inline no
// puede depender de un breakpoint.
const ANCHO_ACCESOS_RAPIDOS = 240;
const ESTILO_ACCESOS = { '--ancho-accesos': `${ANCHO_ACCESOS_RAPIDOS}px` } as CSSProperties;

/** Nombre a mostrar cuando no hay persona en sesión (state.md: get_user_name). */
const NOMBRE_INVITADO = 'Invitado';

// Configuración de las 4 tarjetas de métricas. Declarativo para que agregar
// o reordenar una métrica sea tocar esta lista y nada más.
//
// El doc pide azul para "Socios Activos", pero la paleta Kinetic Carbon
// (DESIGN.md) no tiene azul: se usa el volt, que es el acento primario.
const TARJETAS: {
  clave: keyof DashboardStats;
  titulo: string;
  icono: LucideIcon;
  color: string;
  /** Contra qué se compara el delta. Se muestra al lado del porcentaje. */
  comparacion: string;
  formatear: (valor: number) => string;
  /** Acción que hay que tener para verla. Sin esto, la ve cualquiera con acceso al dashboard. */
  requiere?: 'verIngresos';
}[] = [
  {
    clave: 'sociosActivos',
    titulo: 'Socios activos',
    icono: Users,
    color: colors.primaryVolt,
    comparacion: 'vs mes anterior',
    formatear: formatearNumero,
  },
  {
    clave: 'ingresosMes',
    titulo: 'Ingresos del mes',
    icono: Banknote,
    color: colors.statusOk,
    comparacion: 'vs mes anterior',
    formatear: formatearMoneda,
    // La matriz le da al Recepcionista "consultas globales: parcial
    // (operativo)". Esta es la parte no-operativa: cuánto factura el
    // gimnasio es dato del dueño, no de quien atiende el mostrador.
    requiere: 'verIngresos',
  },
  {
    clave: 'clasesHoy',
    titulo: 'Clases hoy',
    icono: CalendarCheck,
    color: colors.accentCoral,
    comparacion: 'vs ayer',
    formatear: formatearNumero,
  },
  {
    clave: 'nuevosMes',
    titulo: 'Nuevos este mes',
    icono: UserPlus,
    color: colors.statusWarn,
    comparacion: 'vs mes anterior',
    formatear: formatearNumero,
  },
];

// Accesos rápidos. PROVISIONAL: estructura_dashboard.md describe cómo se ve
// el panel pero no qué acciones lleva. Todas apuntan a rutas que ya existen.
const ACCESOS_RAPIDOS: {
  label: string;
  icono: LucideIcon;
  color: string;
  ruta: RouteValue;
}[] = [
  // Apunta a /socios (alta interna, con plan) y no a /registro (auto-alta
  // pública, con usuario/contraseña): el dueño/staff está cargando a otra
  // persona, no creándose una cuenta propia.
  { label: 'Nuevo socio', icono: UserPlus, color: colors.primaryVolt, ruta: Routes.SOCIOS },
  { label: 'Ver socios', icono: Users, color: colors.statusOk, ruta: Routes.SOCIOS },
  { label: 'Rutinas', icono: Dumbbell, color: colors.accentCoral, ruta: Routes.RUTINAS },
  { label: 'Planes de nutrición', icono: Apple, color: colors.statusWarn, ruta: Routes.NUTRICION },
];

interface DatosDashboard {
  stats: DashboardStats;
  actividad: EventoActividad[];
  sociosRecientes: SocioResumen[];
}

/** Delta listo para StatCard, o undefined si no hay base de comparación. */
function textoDelta(metrica: Metrica, comparacion: string): string | undefined {
  if (metrica.deltaPorcentual === null) return undefined;
  return `${formatearDelta(metrica.deltaPorcentual)} ${comparacion}`;
}

function Skeleton({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-md bg-surface-hover ${className}`} />;
}

export function DashboardView() {
  const navigate = useNavigate();
  const persona = useAuthStore((s) => s.persona);
  const verIngresos = usePuedeAccion('verIngresos');
  // El botón del topbar es un atajo al alta de socios: si el rol no tiene
  // esa acción, no se dibuja. Era el único botón de toda la app que no
  // pasaba por la matriz — hoy no rompe nada porque los tres roles que ven
  // el Dashboard la tienen, pero quedaba como trampa para el próximo rol
  // que se agregue.
  const puedeAltaSocios = usePuedeAccion('altaBajaSocios');

  // El Recepcionista ve un dashboard "parcial": las mismas métricas menos
  // las de facturación.
  const tarjetasVisibles = TARJETAS.filter((t) => t.requiere !== 'verIngresos' || verIngresos);

  // Los accesos rápidos son atajos a secciones: si el rol no puede entrar a
  // esa sección, el atajo sólo lo llevaría a un redirect.
  const roles = useAuthStore((s) => s.roles);
  const accesosVisibles = ACCESOS_RAPIDOS.filter((a) => puedeVerRuta(roles, a.ruta));

  const [datos, setDatos] = useState<DatosDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Cambiar este número vuelve a disparar el efecto de carga (botón
  // "Reintentar"), sin duplicar la lógica de fetch en otra función.
  const [intento, setIntento] = useState(0);

  useEffect(() => {
    // cancelado evita el setState tardío si el usuario navega a otra sección
    // antes de que respondan los services.
    let cancelado = false;
    setDatos(null);
    setError(null);

    // Las tres llamadas son independientes: en paralelo, no en cadena. Con
    // la API real esto son tres requests simultáneos.
    Promise.all([obtenerEstadisticas(), obtenerActividadReciente(), obtenerSociosRecientes()])
      .then(([stats, actividad, sociosRecientes]) => {
        if (!cancelado) setDatos({ stats, actividad, sociosRecientes });
      })
      .catch((err: unknown) => {
        if (!cancelado) setError(mensajeDeError(err));
      });

    return () => {
      cancelado = true;
    };
  }, [intento]);

  const reintentar = useCallback(() => setIntento((n) => n + 1), []);

  const nombre = persona?.nombre ?? NOMBRE_INVITADO;

  return (
    <div>
      <Topbar
        title="Dashboard"
        subtitle={`Hola, ${nombre}`}
        actions={
          puedeAltaSocios ? (
            <PrimaryButton
              label="Nuevo Socio"
              icon={UserPlus}
              onClick={() => navigate(`/${Routes.SOCIOS}`)}
            />
          ) : undefined
        }
      />

      <div className="space-y-6 p-8">
        {error && (
          <SectionCard>
            <p className="mb-4 font-body text-sm text-status-danger">{error}</p>
            <PrimaryButton label="Reintentar" onClick={reintentar} />
          </SectionCard>
        )}

        {!error && !datos && <DashboardSkeleton />}

        {!error && datos && (
          <>
            {/* 1. Métricas */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {tarjetasVisibles.map(({ clave, titulo, icono, color, comparacion, formatear }) => {
                const metrica = datos.stats[clave];
                return (
                  <StatCard
                    key={clave}
                    title={titulo}
                    value={formatear(metrica.valor)}
                    delta={textoDelta(metrica, comparacion)}
                    tendencia={(metrica.deltaPorcentual ?? 0) < 0 ? 'down' : 'up'}
                    icon={icono}
                    color={color}
                  />
                );
              })}
            </div>

            {/* 2. Actividad reciente */}
            <SectionCard title="Actividad reciente">
              {datos.actividad.length === 0 ? (
                <p className="font-body text-sm text-text-muted">Todavía no hay movimientos.</p>
              ) : (
                datos.actividad.map((evento, indice) => (
                  <ActivityItem
                    key={evento.id}
                    evento={evento}
                    ultimo={indice === datos.actividad.length - 1}
                  />
                ))
              )}
            </SectionCard>

            {/* 3. Fila inferior: socios recientes + accesos rápidos */}
            <div className="flex flex-col gap-6 lg:flex-row">
              <div className="flex-1">
                <SectionCard title="Socios recientes">
                  {datos.sociosRecientes.length === 0 ? (
                    <p className="font-body text-sm text-text-muted">
                      Todavía no hay socios cargados.
                    </p>
                  ) : (
                    datos.sociosRecientes.map((socio, indice) => (
                      <SocioRow
                        key={socio.idSocio}
                        socio={socio}
                        ultimo={indice === datos.sociosRecientes.length - 1}
                      />
                    ))
                  )}
                </SectionCard>
              </div>

              <div
                style={ESTILO_ACCESOS}
                className="w-full shrink-0 lg:w-[var(--ancho-accesos)]"
              >
                <SectionCard title="Accesos rápidos" padding="p-3">
                  {/* key={label} y no key={ruta}: dos accesos distintos
                      pueden apuntar a la misma pantalla ("Nuevo socio" y
                      "Ver socios" van los dos a /socios), y con la ruta como
                      clave React tiraba "Encountered two children with the
                      same key" y se reservaba el derecho de omitir uno de
                      los dos botones. El label sí es único en la lista. */}
                  {accesosVisibles.map(({ label, icono, color, ruta }) => (
                    <QuickAction
                      key={label}
                      label={label}
                      icon={icono}
                      color={color}
                      onClick={() => navigate(`/${ruta}`)}
                    />
                  ))}
                </SectionCard>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

/** Esqueleto de carga con la misma silueta que el contenido real. */
function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-28" />
        ))}
      </div>
      <Skeleton className="h-64" />
      <div style={ESTILO_ACCESOS} className="flex flex-col gap-6 lg:flex-row">
        <Skeleton className="h-56 flex-1" />
        <Skeleton className="h-56 w-full shrink-0 lg:w-[var(--ancho-accesos)]" />
      </div>
    </div>
  );
}
