import { Check, Eye, Minus } from 'lucide-react';
import { SectionCard } from '../../components/ui';
import {
  Acceso,
  PERMISOS,
  Roles,
  RolLabel,
  SECCIONES_ADMIN,
  colors,
  etiquetaSeccion,
  type AccesoValue,
  type AccionesRol,
  type RolValue,
} from '../../config';

// Equivalente de _perms_row (estructura_usuarios.md), pero derivado de la
// misma tabla PERMISOS que aplican el Sidebar y ProtectedRoute — no una
// tabla aparte y hardcodeada por rol como hace el doc. Si el permiso cambia
// en config.ts, esta pantalla lo refleja sola, no puede desincronizarse.
//
// El doc mostraba sólo qué secciones ve cada rol; acá se muestran las dos
// mitades, secciones y acciones, tal como pidió prompt_permisos_personal.md.
//
// El Socio no se lista: es un CLIENTE, no personal — no tiene nada que
// hacer en un panel de administración. (Hoy sigue teniendo acceso técnico a
// estas pantallas, ver el comentario en PERMISOS; se corrige cuando exista
// su portal propio.)
const ROLES_MOSTRADOS: RolValue[] = [
  Roles.DUENO,
  Roles.RECEPCIONISTA,
  Roles.ENTRENADOR,
  Roles.NUTRICIONISTA,
];

/** Las acciones de la matriz que hoy tienen una pantalla donde aplicarse. */
const ACCIONES_CON_PANTALLA: { clave: keyof AccionesRol; label: string }[] = [
  { clave: 'altaBajaSocios', label: 'Alta/baja de socios' },
  { clave: 'altaBajaPersonal', label: 'Alta/baja de personal' },
  { clave: 'gestionRutinas', label: 'Gestión de rutinas' },
  { clave: 'gestionDietas', label: 'Gestión de dietas' },
  { clave: 'gestionUsuarios', label: 'Gestión de usuarios' },
  { clave: 'verIngresos', label: 'Ver ingresos' },
  // Cobros (especificacion_definitiva_actividades.md, Fase 4) le dio
  // pantalla propia a esta acción — se mueve de la lista de abajo, no se
  // duplica.
  { clave: 'cobrarPagos', label: 'Cobrar/consultar pagos' },
];

/**
 * Acciones que ya están en la matriz pero todavía no tienen panel
 * construido. Se listan aparte para no dar a entender que hoy se están
 * aplicando: no hay pantalla de promociones, deudas independientes ni
 * turnos (gestionDeudas es CONDONAR/generar deuda a mano — cobrar una ya
 * generada sí tiene pantalla, es cobrarPagos, arriba).
 */
const ACCIONES_SIN_PANTALLA: { clave: keyof AccionesRol; label: string }[] = [
  { clave: 'gestionPromociones', label: 'Promociones' },
  { clave: 'gestionDeudas', label: 'Deudas' },
  { clave: 'gestionTurnos', label: 'Turnos' },
];

function IconoAcceso({ acceso }: { acceso: AccesoValue }) {
  if (acceso === Acceso.TOTAL) {
    return <Check size={14} color={colors.statusOk} aria-label="Acceso total" />;
  }
  if (acceso === Acceso.LECTURA) {
    return <Eye size={14} color={colors.statusWarn} aria-label="Sólo lectura" />;
  }
  return <Minus size={14} color={colors.textMuted} aria-label="Sin acceso" />;
}

function IconoAccion({ permitido }: { permitido: boolean }) {
  return permitido ? (
    <Check size={14} color={colors.statusOk} aria-label="Permitido" />
  ) : (
    <Minus size={14} color={colors.textMuted} aria-label="No permitido" />
  );
}

/** Celda de encabezado de rol, compartida por las dos tablas. */
function EncabezadoRoles() {
  return (
    <tr className="border-b border-border-idle">
      <th className="py-2 pr-4 text-left font-body text-xs font-semibold tracking-wide text-text-secondary uppercase">
        &nbsp;
      </th>
      {ROLES_MOSTRADOS.map((rol) => (
        <th
          key={rol}
          className="px-2 py-2 text-center font-body text-xs font-semibold text-text-secondary"
        >
          {RolLabel[rol]}
        </th>
      ))}
    </tr>
  );
}

export function PermisosPanel() {
  return (
    <SectionCard title="Permisos por rol">
      <div className="overflow-x-auto">
        <p className="mb-2 font-body text-xs font-semibold tracking-wide text-text-secondary uppercase">
          Secciones
        </p>
        <table className="w-full">
          <thead>
            <EncabezadoRoles />
          </thead>
          <tbody>
            {SECCIONES_ADMIN.map((seccion) => (
              <tr key={seccion} className="border-b border-border-idle last:border-b-0">
                <td className="py-2 pr-4 font-body text-sm text-text-main">
                  {etiquetaSeccion(seccion)}
                </td>
                {ROLES_MOSTRADOS.map((rol) => (
                  <td key={rol} className="px-2 py-2">
                    <div className="flex justify-center">
                      <IconoAcceso acceso={PERMISOS[rol].secciones[seccion]} />
                    </div>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>

        <p className="mt-5 mb-2 font-body text-xs font-semibold tracking-wide text-text-secondary uppercase">
          Acciones
        </p>
        {/* Los dos grupos de acciones van en UNA sola tabla, separados por
            una fila-título: en tablas distintas cada una calcula el ancho
            de sus columnas por separado y los tildes no alinean entre
            grupos. */}
        <table className="w-full">
          <thead>
            <EncabezadoRoles />
          </thead>
          <tbody>
            {ACCIONES_CON_PANTALLA.map(({ clave, label }) => (
              <tr key={clave} className="border-b border-border-idle">
                <td className="py-2 pr-4 font-body text-sm text-text-main">{label}</td>
                {ROLES_MOSTRADOS.map((rol) => (
                  <td key={rol} className="px-2 py-2">
                    <div className="flex justify-center">
                      <IconoAccion permitido={PERMISOS[rol].acciones[clave]} />
                    </div>
                  </td>
                ))}
              </tr>
            ))}

            <tr>
              <td
                colSpan={ROLES_MOSTRADOS.length + 1}
                className="pt-5 pb-2 font-body text-xs font-semibold tracking-wide text-text-muted uppercase"
              >
                Sin pantalla todavía
              </td>
            </tr>
            {ACCIONES_SIN_PANTALLA.map(({ clave, label }) => (
              <tr key={clave} className="border-b border-border-idle last:border-b-0">
                <td className="py-2 pr-4 font-body text-sm text-text-muted">{label}</td>
                {ROLES_MOSTRADOS.map((rol) => (
                  <td key={rol} className="px-2 py-2">
                    <div className="flex justify-center opacity-50">
                      <IconoAccion permitido={PERMISOS[rol].acciones[clave]} />
                    </div>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-4 flex flex-wrap gap-x-5 gap-y-1 border-t border-border-idle pt-3 font-body text-xs text-text-muted">
        <span className="flex items-center gap-1.5">
          <Check size={12} color={colors.statusOk} /> Total
        </span>
        <span className="flex items-center gap-1.5">
          <Eye size={12} color={colors.statusWarn} /> Sólo lectura
        </span>
        <span className="flex items-center gap-1.5">
          <Minus size={12} color={colors.textMuted} /> Sin acceso
        </span>
      </div>

      <p className="mt-3 font-body text-xs text-text-muted">
        Pagos, promociones, deudas y turnos todavía no tienen pantalla propia: su permiso está
        definido pero no se aplica en ningún lado por ahora.
      </p>
    </SectionCard>
  );
}
