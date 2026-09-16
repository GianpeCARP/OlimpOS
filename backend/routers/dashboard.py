"""
routers/dashboard.py
--------------------
Las métricas de la pantalla principal.

POR QUÉ ESTO ES UN ENDPOINT Y NO SE CALCULA EN EL FRONTEND
----------------------------------------------------------
Cada número de acá resume TODAS las filas de una tabla. "Ingresos del mes" es
la suma de todos los pagos confirmados; "socios activos" cuenta todos los
socios. Calcularlo en el cliente obligaría a bajarse la tabla entera para
mostrar un número — con cien socios ya es absurdo, con mil es inviable.

Además el delta compara contra el mes anterior, que son datos que el cliente
directamente no tiene: nadie se baja el historial completo para pintar una
flechita verde.

TODO SE COMPARA CONTRA EL MES ANTERIOR
--------------------------------------
Un número solo ("9 socios activos") no dice nada. Lo que hace útil un
dashboard es la tendencia: 9 socios con +80% es un gimnasio creciendo; con
-30% es uno que se está vaciando. Por eso cada métrica viaja con su delta.

El delta es None —no cero— cuando el mes anterior fue cero: dividir daría
infinito, y mostrar "+100%" cuando se pasó de 0 a 1 socio es engañoso.
"""

from datetime import date, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import InscripcionActividad, Membresia, Pago, Persona, Reserva, Socio, Turno
from permisos import Accion, Seccion
from schemas import (
    DashboardStats, EventoActividad, IngresosPorPeriodo, Metrica, PuntoIngresos, SocioResumen,
)
from security import Sesion, obtener_sesion, requiere_accion, requiere_seccion
from permisos import puede_accion

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

EVENTOS_RECIENTES = 10
SOCIOS_RECIENTES = 5
# Días de anticipación con que se avisa un vencimiento. Una semana da tiempo
# a que el mostrador llame antes de que el socio quede sin acceso.
DIAS_AVISO_VENCIMIENTO = 7


def _delta(actual: float, anterior: float) -> float | None:
    """
    Variación porcentual. None si no hay base de comparación.

    El caso a evitar es 0 -> 1: matemáticamente es un aumento infinito, y
    mostrar "+100%" sería inventar un dato. La vista, con None, no muestra
    nada, que es lo honesto.
    """
    if anterior == 0:
        return None
    return round(((actual - anterior) / anterior) * 100, 1)


def _rango_mes(referencia: date) -> tuple[date, date]:
    """Primer y último día del mes de `referencia`."""
    primero = referencia.replace(day=1)
    if primero.month == 12:
        siguiente = primero.replace(year=primero.year + 1, month=1)
    else:
        siguiente = primero.replace(month=primero.month + 1)
    return primero, siguiente - timedelta(days=1)


def _iniciales(nombre: str, apellido: str) -> str:
    """'Ana García' -> 'AG'. Es el avatar circular de la tabla."""
    a = nombre.strip()[:1].upper()
    b = apellido.strip()[:1].upper()
    return (a + b) or "?"


@router.get("/stats", response_model=DashboardStats)
def estadisticas(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.DASHBOARD)),
):
    """
    Las cuatro métricas de la portada.

    OJO con `ingresosMes`: es un dato de NEGOCIO, no operativo. Quien no tenga
    el permiso `verIngresos` —hoy, todos menos el Dueño— recibe ceros. No se
    omite el campo ni se devuelve null porque la vista espera la métrica
    siempre; devolver cero mantiene el contrato sin filtrar la cifra real.
    """
    hoy = date.today()
    inicio_mes, _ = _rango_mes(hoy)
    inicio_mes_previo, fin_mes_previo = _rango_mes(inicio_mes - timedelta(days=1))

    # --- Socios activos -----------------------------------------------------
    activos = db.query(func.count(Socio.id_socio)).filter(Socio.activo == True).scalar() or 0  # noqa: E712
    # Comparación: cuántos había al cerrar el mes pasado, contando por fecha
    # de alta. No es exacto (no descuenta las bajas posteriores) pero es la
    # aproximación que se puede hacer sin una tabla de snapshots diarios.
    activos_previo = (
        db.query(func.count(Socio.id_socio))
        .filter(Socio.activo == True, Socio.fecha_alta <= fin_mes_previo)  # noqa: E712
        .scalar() or 0
    )

    # --- Ingresos del mes ---------------------------------------------------
    def ingresos(desde: date, hasta: date) -> float:
        total = (
            db.query(func.coalesce(func.sum(Pago.monto), 0))
            .filter(Pago.estado == "CONFIRMADO",
                    func.date(Pago.fecha_pago) >= desde,
                    func.date(Pago.fecha_pago) <= hasta)
            .scalar()
        )
        return float(total or 0)

    ve_ingresos = puede_accion(sesion.roles, Accion.VER_INGRESOS)
    ingresos_mes = ingresos(inicio_mes, hoy) if ve_ingresos else 0.0
    ingresos_previo = ingresos(inicio_mes_previo, fin_mes_previo) if ve_ingresos else 0.0

    # --- Clases de hoy ------------------------------------------------------
    clases_hoy = (
        db.query(func.count(Turno.id_turno))
        .filter(Turno.fecha == hoy, Turno.estado == "HABILITADO")
        .scalar() or 0
    )
    clases_ayer = (
        db.query(func.count(Turno.id_turno))
        .filter(Turno.fecha == hoy - timedelta(days=1), Turno.estado == "HABILITADO")
        .scalar() or 0
    )

    # --- Altas del mes ------------------------------------------------------
    nuevos = (
        db.query(func.count(Socio.id_socio))
        .filter(Socio.fecha_alta >= inicio_mes, Socio.fecha_alta <= hoy)
        .scalar() or 0
    )
    nuevos_previo = (
        db.query(func.count(Socio.id_socio))
        .filter(Socio.fecha_alta >= inicio_mes_previo, Socio.fecha_alta <= fin_mes_previo)
        .scalar() or 0
    )

    return DashboardStats(
        sociosActivos=Metrica(valor=activos, deltaPorcentual=_delta(activos, activos_previo)),
        ingresosMes=Metrica(valor=ingresos_mes,
                             deltaPorcentual=_delta(ingresos_mes, ingresos_previo)),
        clasesHoy=Metrica(valor=clases_hoy, deltaPorcentual=_delta(clases_hoy, clases_ayer)),
        nuevosMes=Metrica(valor=nuevos, deltaPorcentual=_delta(nuevos, nuevos_previo)),
    )


# =============================================================================
# INGRESOS POR PERÍODO — el gráfico del Dueño
# =============================================================================

# Cuántas barras muestra cada escala. Es lo que se mira en un dashboard: el
# último mes día por día, el último año mes por mes, y los últimos años. Un
# período más largo no entra legible en una tarjeta.
PERIODOS_POR_ESCALA = {"dia": 30, "mes": 12, "anio": 5}

MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun",
                "jul", "ago", "sep", "oct", "nov", "dic"]


def _restar_meses(referencia: date, meses: int) -> date:
    """Primer día del mes que está `meses` meses antes de `referencia`."""
    total = referencia.year * 12 + (referencia.month - 1) - meses
    return date(total // 12, total % 12 + 1, 1)


@router.get("/ingresos", response_model=IngresosPorPeriodo)
def ingresos_por_periodo(
    escala: Literal["dia", "mes", "anio"] = "dia",
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.VER_INGRESOS)),
):
    """
    Ingresos agrupados por día, mes o año, para el gráfico del dashboard.

    Protegido por la ACCIÓN `verIngresos` y no sólo por la sección: el
    Recepcionista entra al dashboard, pero la facturación es dato de negocio.
    Mismo criterio que `ingresosMes` en /stats, sólo que acá no hay nada que
    mostrarle en cero, así que directamente se le niega.

    Mismo criterio de suma que /stats: sólo pagos CONFIRMADOS. Uno pendiente o
    reembolsado no es plata que entró.

    La agrupación la hace la BASE (date_trunc + group by) y no Python: con un
    año de pagos serían miles de filas viajando desde São Paulo para devolver
    doce números.
    """
    hoy = date.today()
    cantidad = PERIODOS_POR_ESCALA[escala]

    # Los inicios de cada período, del más viejo al más nuevo.
    if escala == "dia":
        inicios = [hoy - timedelta(days=i) for i in range(cantidad - 1, -1, -1)]
        unidad = "day"
    elif escala == "mes":
        inicios = [_restar_meses(hoy, i) for i in range(cantidad - 1, -1, -1)]
        unidad = "month"
    else:
        inicios = [date(hoy.year - i, 1, 1) for i in range(cantidad - 1, -1, -1)]
        unidad = "year"

    periodo = func.date_trunc(unidad, Pago.fecha_pago)
    filas = (
        db.query(periodo, func.sum(Pago.monto))
        .filter(Pago.estado == "CONFIRMADO",
                Pago.fecha_pago >= datetime.combine(inicios[0], datetime.min.time()))
        .group_by(periodo)
        .all()
    )
    monto_por_inicio = {inicio.date(): float(monto or 0) for inicio, monto in filas}

    def etiqueta(d: date) -> str:
        if escala == "dia":
            return f"{d.day:02d}/{d.month:02d}"
        if escala == "mes":
            return f"{MESES_CORTOS[d.month - 1]} {d.year % 100:02d}"
        return str(d.year)

    # Todos los períodos, también los que quedaron en cero: ver el comentario
    # de IngresosPorPeriodo.puntos.
    puntos = [PuntoIngresos(periodo=d, etiqueta=etiqueta(d),
                            monto=monto_por_inicio.get(d, 0.0))
              for d in inicios]

    return IngresosPorPeriodo(escala=escala,
                              total=round(sum(p.monto for p in puntos), 2),
                              puntos=puntos)


def _concepto_de_pago(db: Session, pago: Pago) -> str | None:
    """
    Qué se pagó, en pocas palabras: "Mensual", "Yoga: 8 clases al mes",
    "clase suelta de Yoga".

    No hay una columna "concepto": se deriva de a qué está atado el pago (una
    membresía, una inscripción a un plan, o la reserva de una clase suelta).
    Un "pagó $15.000" sin esto obligaba a abrir Cobros para saber de qué.
    """
    if pago.membresia is not None and pago.membresia.tipo is not None:
        return pago.membresia.tipo.nombre
    if pago.id_inscripcion is not None:
        inscripcion = db.get(InscripcionActividad, pago.id_inscripcion)
        if inscripcion is not None and inscripcion.plan is not None:
            plan = inscripcion.plan
            actividad = plan.actividad.nombre if plan.actividad else "?"
            if plan.tipo_limite == "CLASE_SUELTA":
                return f"clase suelta de {actividad}"
            return f"{actividad}: {plan.nombre}"
    reserva = db.query(Reserva).filter(Reserva.id_pago == pago.id_pago).first()
    if reserva is not None and reserva.turno is not None and reserva.turno.actividad:
        return f"clase suelta de {reserva.turno.actividad.nombre}"
    return None


@router.get("/actividad", response_model=list[EventoActividad])
def actividad_reciente(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.DASHBOARD)),
):
    """
    El feed de la portada: qué pasó últimamente y qué está por pasar.

    Mezcla tres orígenes distintos (pagos, altas, vencimientos próximos) en
    una sola lista ordenada por fecha. Que sea un solo endpoint y no tres es
    lo que permite que el feed esté ordenado entre sí — con tres listas
    separadas, la vista tendría que intercalarlas a mano.

    Los vencimientos son eventos FUTUROS y aparecen igual: "vence en 3 días"
    es lo más accionable del panel, porque es sobre lo único que el mostrador
    puede hacer algo antes de que pase.
    """
    eventos: list[EventoActividad] = []
    hoy = date.today()

    # --- Pagos recientes ----------------------------------------------------
    # Los ve también el Recepcionista (decisión del dueño, 2026-09-16). Lo que
    # es dato de negocio es el TOTAL facturado (métrica y gráfico, detrás de
    # verIngresos); cada cobro suelto es trabajo del mostrador, que en general
    # lo cobró él mismo.
    pagos = (
        db.query(Pago)
        .filter(Pago.estado == "CONFIRMADO")
        .order_by(Pago.fecha_pago.desc())
        .limit(EVENTOS_RECIENTES)
        .all()
    )
    for p in pagos:
        nombre = p.socio.persona.nombre_completo if p.socio and p.socio.persona else "?"
        concepto = _concepto_de_pago(db, p)
        eventos.append(EventoActividad(
            id=f"pago-{p.id_pago}",
            tipo="pago",
            descripcion=(f"{nombre} pagó ${float(p.monto):,.2f}"
                         + (f" ({concepto})" if concepto else "")),
            fecha=p.fecha_pago,
        ))

    # --- Altas de socios ----------------------------------------------------
    altas = (
        db.query(Socio)
        .order_by(Socio.id_socio.desc())
        .limit(EVENTOS_RECIENTES)
        .all()
    )
    for s in altas:
        nombre = s.persona.nombre_completo if s.persona else "?"
        eventos.append(EventoActividad(
            id=f"nuevo_socio-{s.id_socio}",
            tipo="nuevo_socio",
            descripcion=f"{nombre} se dio de alta como socio",
            # fecha_alta es un date; el feed ordena por datetime.
            fecha=datetime.combine(s.fecha_alta, datetime.min.time()),
        ))

    # --- Vencimientos próximos ----------------------------------------------
    limite = hoy + timedelta(days=DIAS_AVISO_VENCIMIENTO)
    por_vencer = (
        db.query(Membresia)
        .filter(Membresia.estado == "ACTIVA",
                Membresia.fecha_vencimiento >= hoy,
                Membresia.fecha_vencimiento <= limite)
        .all()
    )
    for m in por_vencer:
        nombre = m.socio.persona.nombre_completo if m.socio and m.socio.persona else "?"
        dias = (m.fecha_vencimiento - hoy).days
        cuando = "hoy" if dias == 0 else f"en {dias} día(s)"
        eventos.append(EventoActividad(
            id=f"vencimiento-{m.id_membresia}",
            tipo="vencimiento",
            descripcion=f"Vence la membresía de {nombre} {cuando}",
            fecha=datetime.combine(m.fecha_vencimiento, datetime.min.time()),
        ))

    eventos.sort(key=lambda e: e.fecha, reverse=True)
    return eventos[:EVENTOS_RECIENTES]


@router.get("/socios-recientes", response_model=list[SocioResumen])
def socios_recientes(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.DASHBOARD)),
):
    """
    Las últimas altas, con su estado de cuota.

    El `estado` no es una columna: se deriva de la membresía vigente —Activo,
    Por vencer o Vencido—. Es el mismo criterio que usa la sección Cobros, y
    se calcula acá para que la tarjeta del dashboard no tenga que pedir el
    estado de cuenta de cada socio por separado.
    """
    socios = db.query(Socio).order_by(Socio.id_socio.desc()).limit(SOCIOS_RECIENTES).all()
    hoy = date.today()

    salida = []
    for s in socios:
        persona = s.persona
        membresia = (
            db.query(Membresia)
            .filter(Membresia.id_socio == s.id_socio, Membresia.estado == "ACTIVA")
            .order_by(Membresia.fecha_vencimiento.desc())
            .first()
        )

        if membresia is None or membresia.fecha_vencimiento is None:
            estado, plan = "Vencido", "Sin plan"
        else:
            dias = (membresia.fecha_vencimiento - hoy).days
            plan = membresia.tipo.nombre if membresia.tipo else "?"
            if dias < 0:
                estado = "Vencido"
            elif dias <= DIAS_AVISO_VENCIMIENTO:
                estado = "Por vencer"
            else:
                estado = "Activo"

        salida.append(SocioResumen(
            idSocio=s.id_socio,
            nombre=persona.nombre_completo if persona else "?",
            iniciales=_iniciales(persona.nombre, persona.apellido) if persona else "?",
            plan=plan,
            estado=estado,
        ))
    return salida
