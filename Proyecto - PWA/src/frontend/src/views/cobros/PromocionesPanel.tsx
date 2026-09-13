import { useCallback, useEffect, useState } from 'react';
import { ChevronDown, ChevronRight, Pencil, Plus, Power, Tag } from 'lucide-react';
import { InputField, PrimaryButton, SectionCard } from '../../components/ui';
import { colors } from '../../config';
import { mensajeDeError } from '../../services/api';
import {
  actualizarPromocion,
  crearPromocion,
  darDeBajaPromocion,
  listarPromociones,
  reactivarPromocion,
  usoDePromocion,
  type Promocion,
  type PromocionInput,
} from '../../services/promocionesService';
import { useUiStore } from '../../store/uiStore';
import { formatearFecha } from '../../utils/format';
import { parsearFecha } from '../../utils/fechas';

// Administración de descuentos. Solo la ve el Dueño — la acción
// `gestionPromociones` es la única de la matriz que tiene él solo.
//
// POR QUÉ VIVE DENTRO DE COBROS Y NO EN SU PROPIA SECCIÓN
// --------------------------------------------------------
// Porque las secciones no son una decisión de esta pantalla: son las entradas
// de la matriz de permisos, y la matriz está copiada en TRES lugares (config.ts,
// backend/permisos.py y app/permisos.py de Flet). Sumar una sección para un
// panel que usa un solo rol obligaría a tocar las tres copias y a que
// check_permisos.py las siga viendo iguales. Cobros ya es donde se aplica el
// descuento; el catálogo va al lado.
//
// ARRANCA PLEGADO, y no es un detalle estético: Cobros es la pantalla del
// mostrador, donde hay alguien esperando del otro lado. Un panel de
// administración abierto empujaría el buscador de socios hacia abajo en la
// pantalla que más se usa del sistema.
//
// Gemelo del panel de promociones de `app/views/cobros.py` en Flet.

/** Estado del formulario. Vacío = alta; con promo = edición. */
interface Borrador {
  idPromocion?: number;
  nombre: string;
  descripcion: string;
  /** El descuento es SIEMPRE porcentual (0-100). */
  valor: string;
  fechaInicio: string;
  fechaFin: string;
}

function borradorVacio(): Borrador {
  const hoy = new Date().toISOString().slice(0, 10);
  return {
    nombre: '',
    descripcion: '',
    valor: '',
    fechaInicio: hoy,
    fechaFin: hoy,
  };
}

function aBorrador(p: Promocion): Borrador {
  return {
    idPromocion: p.idPromocion,
    nombre: p.nombre,
    descripcion: p.descripcion ?? '',
    valor: String(p.porcentajeDescuento ?? ''),
    fechaInicio: p.fechaInicio,
    fechaFin: p.fechaFin,
  };
}

export function PromocionesPanel() {
  const showSnack = useUiStore((s) => s.showSnack);
  const confirmDialog = useUiStore((s) => s.confirmDialog);

  const [abierto, setAbierto] = useState(false);
  const [promociones, setPromociones] = useState<Promocion[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [borrador, setBorrador] = useState<Borrador | null>(null);
  const [guardando, setGuardando] = useState(false);

  const cargar = useCallback(() => {
    setError(null);
    listarPromociones()
      .then(setPromociones)
      .catch((err: unknown) => setError(mensajeDeError(err)));
  }, []);

  // Solo pide datos cuando se despliega: si cargara siempre, el mostrador
  // pagaría un pedido de más en cada visita a Cobros por un panel que casi
  // nunca abre.
  useEffect(() => {
    if (abierto && promociones === null) cargar();
  }, [abierto, promociones, cargar]);

  const guardar = async () => {
    if (!borrador) return;
    const valor = Number(borrador.valor);
    if (!borrador.nombre.trim() || borrador.nombre.trim().length < 2) {
      showSnack('La promoción necesita un nombre.', colors.statusDanger);
      return;
    }
    if (!Number.isFinite(valor) || valor <= 0) {
      showSnack('El descuento tiene que ser mayor que cero.', colors.statusDanger);
      return;
    }
    if (valor > 100) {
      showSnack('Un porcentaje no puede pasar de 100.', colors.statusDanger);
      return;
    }
    if (borrador.fechaFin < borrador.fechaInicio) {
      showSnack('La promoción no puede terminar antes de empezar.', colors.statusDanger);
      return;
    }

    const input: PromocionInput = {
      nombre: borrador.nombre,
      descripcion: borrador.descripcion,
      porcentajeDescuento: valor,
      fechaInicio: borrador.fechaInicio,
      fechaFin: borrador.fechaFin,
    };

    setGuardando(true);
    try {
      if (borrador.idPromocion !== undefined) {
        await actualizarPromocion(borrador.idPromocion, input);
        showSnack('Promoción actualizada.', colors.statusOk);
      } else {
        await crearPromocion(input);
        showSnack('Promoción creada.', colors.statusOk);
      }
      setBorrador(null);
      cargar();
    } catch (err) {
      showSnack(mensajeDeError(err), colors.statusDanger);
    } finally {
      setGuardando(false);
    }
  };

  const alternarEstado = async (promo: Promocion) => {
    if (promo.activo) {
      // Se consulta el uso ANTES de preguntar: apagar una que usaron 40 socios
      // no es lo mismo que apagar una que no usó nadie, y quien decide tiene
      // que verlo en el mismo diálogo donde confirma.
      let uso = '';
      try {
        uso = await usoDePromocion(promo.idPromocion);
      } catch {
        uso = '';
      }
      confirmDialog(
        `¿Dar de baja "${promo.nombre}"?`,
        `${uso} La promoción deja de poder aplicarse, pero la fila no se borra: la referencian las membresías que ya se cobraron con ella.`,
        () => {
          darDeBajaPromocion(promo.idPromocion)
            .then(() => {
              showSnack(`"${promo.nombre}" dada de baja.`, colors.statusOk);
              cargar();
            })
            .catch((err: unknown) => showSnack(mensajeDeError(err), colors.statusDanger));
        },
      );
      return;
    }

    try {
      const vuelta = await reactivarPromocion(promo.idPromocion);
      showSnack(
        vuelta.vigente
          ? `"${vuelta.nombre}" volvió a estar vigente.`
          : `"${vuelta.nombre}" quedó activa, pero fuera de fecha: cambiale las fechas para poder aplicarla.`,
        vuelta.vigente ? colors.statusOk : colors.statusWarn,
      );
      cargar();
    } catch (err) {
      showSnack(mensajeDeError(err), colors.statusDanger);
    }
  };

  return (
    <SectionCard padding="p-0">
      <button
        type="button"
        onClick={() => setAbierto((v) => !v)}
        className="flex w-full items-center gap-2 px-5 py-4 text-left"
      >
        {abierto ? (
          <ChevronDown size={16} className="text-text-muted" />
        ) : (
          <ChevronRight size={16} className="text-text-muted" />
        )}
        <Tag size={16} className="text-primary-volt" />
        <span className="font-heading text-base font-semibold text-text-main">Promociones</span>
        <span className="font-body text-xs text-text-muted">
          {promociones ? `${promociones.filter((p) => p.vigente).length} vigentes` : 'descuentos sobre el precio de lista'}
        </span>
      </button>

      {abierto && (
        <div className="border-t border-border-idle px-5 py-4">
          {error && <p className="font-body text-sm text-status-danger">{error}</p>}
          {!error && promociones === null && (
            <p className="font-body text-sm text-text-muted">Cargando…</p>
          )}

          {!error && promociones !== null && (
            <>
              {promociones.length === 0 && (
                <p className="font-body text-sm text-text-muted">
                  Todavía no hay ninguna promoción cargada.
                </p>
              )}

              <ul className="flex flex-col gap-2">
                {promociones.map((p) => (
                  <li
                    key={p.idPromocion}
                    className="flex flex-wrap items-center gap-3 rounded-md border border-border-idle p-3"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-baseline gap-2">
                        <span
                          className={
                            p.vigente
                              ? 'font-body text-sm text-text-main'
                              : 'font-body text-sm text-text-muted'
                          }
                        >
                          {p.nombre}
                        </span>
                        <span className="font-mono text-xs text-primary-volt">{p.etiqueta}</span>
                        {/* Tres estados y no dos: "vigente", "apagada" y
                            "activa pero fuera de fecha" son distintos, y el
                            tercero es el que confunde si no se nombra. */}
                        {!p.activo ? (
                          <span className="font-body text-xs text-text-muted">dada de baja</span>
                        ) : (
                          !p.vigente && (
                            <span className="font-body text-xs text-status-warn">fuera de fecha</span>
                          )
                        )}
                      </div>
                      <p className="font-body text-xs text-text-muted">
                        {formatearFecha(parsearFecha(p.fechaInicio))} —{' '}
                        {formatearFecha(parsearFecha(p.fechaFin))}
                        {p.descripcion ? ` · ${p.descripcion}` : ''}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setBorrador(aBorrador(p))}
                      title="Editar"
                      className="rounded-md p-2 text-text-muted hover:bg-surface-hover hover:text-text-main"
                    >
                      <Pencil size={15} />
                    </button>
                    <button
                      type="button"
                      onClick={() => void alternarEstado(p)}
                      title={p.activo ? 'Dar de baja' : 'Reactivar'}
                      className={
                        p.activo
                          ? 'rounded-md p-2 text-text-muted hover:bg-surface-hover hover:text-status-danger'
                          : 'rounded-md p-2 text-text-muted hover:bg-surface-hover hover:text-status-ok'
                      }
                    >
                      <Power size={15} />
                    </button>
                  </li>
                ))}
              </ul>

              {borrador === null ? (
                <button
                  type="button"
                  onClick={() => setBorrador(borradorVacio())}
                  className="mt-4 flex items-center gap-1.5 font-body text-sm text-text-secondary hover:text-text-main"
                >
                  <Plus size={15} />
                  Nueva promoción
                </button>
              ) : (
                <div className="mt-4 flex flex-col gap-4 border-t border-border-idle pt-4">
                  <p className="font-heading text-sm font-semibold text-text-main">
                    {borrador.idPromocion !== undefined ? 'Editar promoción' : 'Nueva promoción'}
                  </p>

                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <InputField
                      label="Nombre"
                      value={borrador.nombre}
                      onChange={(v) => setBorrador({ ...borrador, nombre: v })}
                      name="nombrePromo"
                      required
                    />
                    <InputField
                      label="Descripción"
                      value={borrador.descripcion}
                      onChange={(v) => setBorrador({ ...borrador, descripcion: v })}
                      name="descPromo"
                    />
                  </div>

                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    {/* El descuento es siempre porcentual (el monto fijo se
                        eliminó por decisión comercial). */}
                    <InputField
                      label="Porcentaje de descuento (%)"
                      value={borrador.valor}
                      onChange={(v) => setBorrador({ ...borrador, valor: v })}
                      type="number"
                      min={0}
                      max={100}
                      name="valorPromo"
                      required
                    />
                  </div>

                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <InputField
                      label="Desde"
                      value={borrador.fechaInicio}
                      onChange={(v) => setBorrador({ ...borrador, fechaInicio: v })}
                      type="date"
                      name="desdePromo"
                    />
                    <InputField
                      label="Hasta"
                      value={borrador.fechaFin}
                      onChange={(v) => setBorrador({ ...borrador, fechaFin: v })}
                      type="date"
                      name="hastaPromo"
                    />
                  </div>

                  <div className="flex justify-end gap-3">
                    <button
                      type="button"
                      onClick={() => setBorrador(null)}
                      className="shrink-0 rounded-md px-4 py-2 font-body text-sm whitespace-nowrap text-text-secondary hover:text-text-main"
                    >
                      Cancelar
                    </button>
                    <PrimaryButton
                      label={guardando ? 'Guardando…' : 'Guardar'}
                      onClick={() => void guardar()}
                      disabled={guardando}
                    />
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </SectionCard>
  );
}
