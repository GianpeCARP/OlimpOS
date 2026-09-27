import { useCallback, useEffect, useMemo, useState } from 'react';
import { Search, UserPlus } from 'lucide-react';
import { FilterChip, PrimaryButton, SectionCard, Topbar } from '../../components/ui';
import { Acceso, colors, RolEmpleado, Routes, type RolEmpleadoValue } from '../../config';
import { mensajeDeError } from '../../services/api';
import {
  listarPersonal,
  darDeBajaEmpleado,
  reactivarEmpleado,
  type EmpleadoListado,
} from '../../services/personalService';
import { useAuthStore } from '../../store/authStore';
import { useUiStore } from '../../store/uiStore';
import { useAccesoSeccion, usePuedeAccion } from '../../hooks/usePermisos';
import { EmpleadoFormModal } from './EmpleadoFormModal';
import { StaffCard } from './StaffCard';

// Equivalente de PersonalView (estructura_personal.md): topbar con el conteo
// de activos + grilla responsiva de tarjetas (xs:1, sm:2, md:3, lg:4).
//
// Agregados que el doc no pedía: buscador y chips de filtro por rol. El .py
// original listaba todo sin filtrar, pero la vista de socios ya dejó armado
// el patrón (y el componente FilterChip), y con el personal creciendo es la
// misma necesidad. El filtro es por rol y no por estado porque el rol es lo
// que distingue a un empleado de otro en esta pantalla.

// 'Todos' no es un rol: es la ausencia de filtro.
type FiltroRol = RolEmpleadoValue | 'Todos';
const FILTROS: FiltroRol[] = ['Todos', ...Object.values(RolEmpleado)];

function Skeleton({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-md bg-surface-hover ${className}`} />;
}

export function PersonalView() {
  const idPersonaSesion = useAuthStore((s) => s.persona?.id_persona);
  const showSnack = useUiStore((s) => s.showSnack);
  const confirmDialog = useUiStore((s) => s.confirmDialog);

  // El Recepcionista tiene esta sección en LECTURA: la ve entera (es
  // operativo, necesita saber quién trabaja hoy) pero no puede editar ni
  // dar de alta/baja a nadie — eso es exclusivo del Dueño.
  const puedeEditar = useAccesoSeccion(Routes.PERSONAL) === Acceso.TOTAL;
  const puedeAltaBajaPersonal = usePuedeAccion('altaBajaPersonal');

  /**
   * Regla a nivel de fila (punto 3 de prompt_permisos_personal.md): nadie
   * puede dar de baja su PROPIO registro de empleado, aunque tenga el
   * permiso general — se dejaría afuera del sistema de un click. El prompt
   * lo pedía sólo para el Recepcionista; se generaliza a cualquier rol
   * porque no hay ningún caso donde auto-desactivarse sea deseable, y así
   * la regla no depende de qué rol tenga permiso mañana.
   */
  const puedeDarDeBajaA = useCallback(
    (empleado: EmpleadoListado) =>
      puedeAltaBajaPersonal && empleado.idPersona !== idPersonaSesion,
    [puedeAltaBajaPersonal, idPersonaSesion],
  );

  const [personal, setPersonal] = useState<EmpleadoListado[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intento, setIntento] = useState(0);

  const [busqueda, setBusqueda] = useState('');
  const [filtro, setFiltro] = useState<FiltroRol>('Todos');

  const [modal, setModal] = useState<{ empleado: EmpleadoListado | null } | null>(null);

  useEffect(() => {
    let cancelado = false;
    setPersonal(null);
    setError(null);
    listarPersonal()
      .then((lista) => {
        if (!cancelado) setPersonal(lista);
      })
      .catch((err: unknown) => {
        if (!cancelado) setError(mensajeDeError(err));
      });
    return () => {
      cancelado = true;
    };
  }, [intento]);

  const recargar = useCallback(() => setIntento((n) => n + 1), []);

  const visibles = useMemo(() => {
    if (!personal) return [];
    const texto = busqueda.trim().toLowerCase();
    return personal.filter((e) => {
      const coincideTexto =
        texto === '' ||
        e.nombreCompleto.toLowerCase().includes(texto) ||
        e.rol.toLowerCase().includes(texto) ||
        (e.detalle?.toLowerCase().includes(texto) ?? false);
      return coincideTexto && (filtro === 'Todos' || e.rol === filtro);
    });
  }, [personal, busqueda, filtro]);

  // El doc pide "{N} empleados activos", no el total: los dados de baja
  // siguen listándose (con el badge en gris) pero no cuentan.
  const activos = personal?.filter((e) => e.activo).length ?? 0;

  const actualizarEnLista = useCallback((actualizado: EmpleadoListado) => {
    setPersonal((lista) =>
      lista
        ? lista.some((e) => e.idEmpleado === actualizado.idEmpleado)
          ? lista.map((e) => (e.idEmpleado === actualizado.idEmpleado ? actualizado : e))
          : [...lista, actualizado]
        : lista,
    );
  }, []);

  const pedirBaja = useCallback(
    (empleado: EmpleadoListado) => {
      confirmDialog(
        `¿Dar de baja a ${empleado.nombreCompleto}?`,
        'Deja de figurar como activo y su cuenta de acceso se desactiva. Si entrena socios, deja de estar a cargo de ellos. Se puede reactivar.',
        () => {
          darDeBajaEmpleado(empleado.idEmpleado)
            .then(() => {
              // "Se dio de baja a X" y no "X fue dado de baja": Persona no
              // tiene sexo cargado en la mayoría de las filas, y el
              // participio en masculino fijo le erraba a la mitad del
              // personal ("Carla Bianchi fue dado de baja"). La forma
              // impersonal es correcta para cualquier persona.
              showSnack(`Se dio de baja a ${empleado.nombreCompleto}`, colors.statusOk);
              recargar();
            })
            .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
        },
      );
    },
    [confirmDialog, showSnack, recargar],
  );

  // Sin diálogo de confirmación: reactivar es una acción de bajo riesgo y
  // reversible (siempre se puede volver a dar de baja), a diferencia de
  // pedirBaja.
  const activar = useCallback(
    (empleado: EmpleadoListado) => {
      reactivarEmpleado(empleado.idEmpleado)
        .then(() => {
          showSnack(`Se reactivó a ${empleado.nombreCompleto}`, colors.statusOk);
          recargar();
        })
        .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
    },
    [showSnack, recargar],
  );

  return (
    <div>
      <Topbar
        title="Personal"
        subtitle={personal ? `${activos} empleados activos` : undefined}
        actions={
          puedeAltaBajaPersonal ? (
            <PrimaryButton
              label="Agregar Empleado"
              icon={UserPlus}
              onClick={() => setModal({ empleado: null })}
            />
          ) : undefined
        }
      />

      <div className="space-y-4 p-8">
        {error && (
          <SectionCard>
            <p className="mb-4 font-body text-sm text-status-danger">{error}</p>
            <PrimaryButton label="Reintentar" onClick={recargar} />
          </SectionCard>
        )}

        {!error && !personal && (
          <div className="space-y-4">
            <Skeleton className="h-10 w-full max-w-sm" />
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
              {[0, 1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-56" />
              ))}
            </div>
          </div>
        )}

        {!error && personal && (
          <>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="relative w-full sm:w-72">
                <Search size={16} className="absolute top-1/2 left-3 -translate-y-1/2 text-text-muted" />
                <input
                  type="text"
                  value={busqueda}
                  onChange={(e) => setBusqueda(e.target.value)}
                  placeholder="Buscar por nombre, rol o especialidad…"
                  className="w-full rounded-md border border-border-idle bg-surface-card py-2 pr-3 pl-9 font-body text-sm text-text-main outline-none placeholder:text-text-muted focus:border-border-active"
                />
              </div>
              <div className="flex flex-wrap gap-2">
                {FILTROS.map((f) => (
                  <FilterChip key={f} label={f} activo={filtro === f} onClick={() => setFiltro(f)} />
                ))}
              </div>
            </div>

            {visibles.length === 0 ? (
              <SectionCard>
                <p className="font-body text-sm text-text-muted">
                  {personal.length === 0
                    ? 'Todavía no hay empleados cargados.'
                    : 'Ningún empleado coincide con la búsqueda o el filtro.'}
                </p>
              </SectionCard>
            ) : (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
                {visibles.map((empleado) => (
                  <StaffCard
                    key={empleado.idEmpleado}
                    empleado={empleado}
                    puedeEditar={puedeEditar}
                    puedeDarDeBaja={puedeDarDeBajaA(empleado)}
                    onEditar={() => setModal({ empleado })}
                    onDarDeBaja={() => pedirBaja(empleado)}
                    onActivar={() => activar(empleado)}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </div>

      {modal && (
        <EmpleadoFormModal
          empleado={modal.empleado}
          onClose={() => setModal(null)}
          onGuardado={actualizarEnLista}
        />
      )}
    </div>
  );
}
