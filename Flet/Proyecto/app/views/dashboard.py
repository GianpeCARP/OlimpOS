# =============================================================================
# views/dashboard.py — Pantalla de inicio
# =============================================================================
# Espejo de DashboardView.tsx de la PWA. Mismo contenido y mismo orden:
#   1. Cuatro tarjetas de métricas
#   2. Actividad reciente
#   3. Fila inferior: socios recientes (elástico) + accesos rápidos (240px)
#
# Las etiquetas, los colores de cada tarjeta y los textos de los accesos
# rápidos están copiados uno a uno de la web para que las dos pantallas se
# lean igual.

import flet as ft
from app.config import Colors, Fonts, Radius, Routes, alpha
from app.permisos import Accion
from app.components.agenda_turnos import agenda_turnos
from app.state import app_state
from app.components.ui import (build_topbar, stat_card, section_card,
                               status_badge, primary_button, divider_row,
                               filter_chip)


# Ancho del panel de accesos rápidos. La PWA lo fija en 240px
# (ANCHO_ACCESOS_RAPIDOS en DashboardView.tsx).
ANCHO_ACCESOS = 240

# ── Gráfico de ingresos (sólo el Dueño) ──────────────────────────────────────
# Gemelo de IngresosChart.tsx. Flet 0.84 no trae componente de gráficos (ni
# ft.BarChart ni el paquete flet_charts), así que las barras son rectángulos
# con altura proporcional — lo mismo que hace la PWA, que tampoco usa librería.
ESCALAS_INGRESOS = [("dia", "Día"), ("mes", "Mes"), ("anio", "Año")]
RANGO_INGRESOS = {"dia": "últimos 30 días", "mes": "últimos 12 meses",
                  "anio": "últimos 5 años"}
ALTO_GRAFICO = 150

# ── Configuración de las 4 tarjetas de métricas ──────────────────────────────
# Declarativo, igual que TARJETAS en la web: agregar o reordenar una métrica es
# tocar esta lista y nada más.
#
# `requiere_ingresos` marca la de facturación: el Recepcionista ve el dashboard
# "parcial" (todas menos esa), igual que DashboardView.tsx. Se filtra con la
# acción verIngresos en build().
TARJETAS = [
    {"clave": "socios_activos", "titulo": "Socios activos",  "icono": ft.Icons.GROUP_ROUNDED,
     "color": Colors.PRIMARY_VOLT,  "comparacion": "vs mes anterior", "formato": "numero"},
    {"clave": "ingresos_mes",   "titulo": "Ingresos del mes", "icono": ft.Icons.PAYMENTS_ROUNDED,
     "color": Colors.STATUS_OK,     "comparacion": "vs mes anterior", "formato": "moneda",
     "requiere_ingresos": True},
    {"clave": "clases_hoy",     "titulo": "Clases hoy",       "icono": ft.Icons.EVENT_AVAILABLE_ROUNDED,
     "color": Colors.ACCENT_CORAL,  "comparacion": "vs ayer",         "formato": "numero"},
    {"clave": "nuevos_mes",     "titulo": "Nuevos este mes",  "icono": ft.Icons.PERSON_ADD_ROUNDED,
     "color": Colors.STATUS_WARN,   "comparacion": "vs mes anterior", "formato": "numero"},
]

# ── Accesos rápidos ──────────────────────────────────────────────────────────
# Mismos cuatro atajos que la web, en el mismo orden y con los mismos colores.
ACCESOS_RAPIDOS = [
    {"label": "Nuevo socio",         "icono": ft.Icons.PERSON_ADD_ROUNDED,     "color": Colors.PRIMARY_VOLT, "ruta": Routes.SOCIOS},
    {"label": "Ver socios",          "icono": ft.Icons.GROUP_ROUNDED,          "color": Colors.STATUS_OK,    "ruta": Routes.SOCIOS},
    {"label": "Rutinas",             "icono": ft.Icons.FITNESS_CENTER_ROUNDED, "color": Colors.ACCENT_CORAL, "ruta": Routes.RUTINAS},
    {"label": "Planes de nutrición", "icono": ft.Icons.RESTAURANT_MENU_ROUNDED,"color": Colors.STATUS_WARN,  "ruta": Routes.NUTRICION},
]

# ── Íconos del feed de actividad ─────────────────────────────────────────────
# Mismo mapa que ICONOS_ACTIVIDAD de la web. Kinetic Carbon no tiene azul, así
# que "nuevo_socio" usa el volt (el acento primario cumple la misma función de
# informativo/neutro positivo).
ICONOS_ACTIVIDAD = {
    "nuevo_socio": (ft.Icons.PERSON_ADD_ROUNDED,     Colors.PRIMARY_VOLT),
    "pago":        (ft.Icons.PAYMENTS_ROUNDED,       Colors.STATUS_OK),
    "rutina":      (ft.Icons.FITNESS_CENTER_ROUNDED, Colors.ACCENT_CORAL),
    "vencimiento": (ft.Icons.WARNING_ROUNDED,        Colors.STATUS_WARN),
}


class DashboardView:
    def __init__(self, page: ft.Page, router):
        self.page   = page
        self.router = router
        # Escala del gráfico de ingresos. Arranca en días, igual que la PWA.
        self._escala = "dia"

    def build(self) -> ft.Column:
        stats     = app_state.get_dashboard_stats()
        actividad = app_state.get_actividad_reciente()
        # Endpoint dedicado: `get_socios()[:4]` traia la grilla entera —un
        # pedido de ~0,9s— para mostrar cuatro filas. Ver el docstring de
        # get_socios_recientes en state.py.
        socios    = app_state.get_socios_recientes()[:4]

        # Atajo al alta de socios: sólo con la acción (DashboardView.tsx).
        topbar = build_topbar(
            "Dashboard",
            f"Hola, {app_state.get_user_name()}",
            actions=[
                primary_button("Nuevo socio", ft.Icons.PERSON_ADD_ROUNDED,
                               on_click=lambda e: self.router.navigate(Routes.SOCIOS)),
            ] if app_state.puede(Accion.ALTA_BAJA_SOCIOS) else [],
        )

        # ── 1. Métricas ──────────────────────────────────────────────────────
        ver_ingresos = app_state.puede(Accion.VER_INGRESOS)
        tarjetas = []
        for t in TARJETAS:
            if t.get("requiere_ingresos") and not ver_ingresos:
                continue
            m = stats[t["clave"]]
            tarjetas.append(
                stat_card(
                    t["titulo"],
                    _formatear(m["valor"], t["formato"]),
                    _texto_delta(m["delta_pct"], t["comparacion"]),
                    # `or 0` porque delta_pct puede ser None: sin esto la
                    # comparación explota antes de llegar a stat_card. Con None
                    # la tendencia da igual —no se dibuja la flecha— pero hay
                    # que poder calcularla sin reventar. Mismo `?? 0` que usa
                    # DashboardView.tsx.
                    "down" if (m["delta_pct"] or 0) < 0 else "up",
                    t["icono"],
                    t["color"],
                )
            )
        fila_metricas = ft.Row(tarjetas, spacing=16)

        # ── 2. Actividad reciente ────────────────────────────────────────────
        items = []
        for i, a in enumerate(actividad):
            items.append(_item_actividad(a))
            if i < len(actividad) - 1:
                items.append(divider_row())
        card_actividad = section_card(ft.Column(items, spacing=0),
                                      title="Actividad reciente")

        # ── 3. Socios recientes + accesos rápidos ────────────────────────────
        filas_socios = []
        for i, s in enumerate(socios):
            filas_socios.append(_fila_socio(s))
            if i < len(socios) - 1:
                filas_socios.append(divider_row())
        card_socios = section_card(ft.Column(filas_socios, spacing=0),
                                   title="Socios recientes")

        card_accesos = ft.Container(
            content=ft.Column([
                ft.Text("Accesos rápidos", color=Colors.TEXT_MAIN, size=18,
                        weight=ft.FontWeight.W_600, font_family=Fonts.TITLE),
                ft.Container(height=6),
                # Un atajo a una sección que el rol no puede abrir sólo lo
                # llevaría a un rechazo: se filtran como en la PWA.
                *[self._acceso(a) for a in ACCESOS_RAPIDOS
                  if app_state.puede_ver(a["ruta"])],
            ], spacing=2),
            bgcolor=Colors.SURFACE_CARD,
            border_radius=Radius.MD,
            border=ft.Border.all(1, Colors.BORDER_IDLE),
            padding=20,
            width=ANCHO_ACCESOS,
        )

        fila_inferior = ft.Row([
            ft.Column([card_socios], expand=True),
            card_accesos,
        ], spacing=24, vertical_alignment=ft.CrossAxisAlignment.START)

        # ── Próximos turnos ──────────────────────────────────────────────────
        # Gemelo de <AgendaTurnos compacto /> de DashboardView.tsx. Para quien
        # atiende el mostrador (no ve la facturación) van ARRIBA de todo; el
        # Dueño los ve después de sus números.
        ver_turnos = app_state.puede_ver(Routes.ASISTENCIA)
        turnos_arriba = ver_turnos and not ver_ingresos
        card_turnos = agenda_turnos(self.page, dias=2, compacto=True) if ver_turnos else None

        # ── Ensamblado ───────────────────────────────────────────────────────
        # Separación de 24px entre bloques y padding de 32, igual que el
        # `space-y-6 p-8` de la web.
        # El topbar queda fijo arriba y sólo el contenido scrollea — igual que
        # en la web, donde el <main> es el que tiene overflow-y-auto. Poner el
        # scroll en la Column exterior (con un hijo expand adentro) hacía que
        # Flet centrara todo verticalmente cuando el contenido no llenaba la
        # pantalla, y la pantalla arrancaba con un hueco enorme arriba.
        return ft.Column([
            topbar,
            ft.Container(
                content=ft.Column([
                    *([card_turnos, ft.Container(height=24)] if turnos_arriba else []),
                    fila_metricas,
                    ft.Container(height=24),
                    # Sólo con verIngresos: el Recepcionista ve el dashboard,
                    # pero la facturación no. Mismo lugar que en la PWA.
                    *([self._card_ingresos(), ft.Container(height=24)]
                      if ver_ingresos else []),
                    *([card_turnos, ft.Container(height=24)]
                      if ver_turnos and not turnos_arriba else []),
                    card_actividad,
                    ft.Container(height=24),
                    fila_inferior,
                ], spacing=0, scroll=ft.ScrollMode.AUTO, expand=True),
                padding=ft.Padding.all(32),
                expand=True,
            ),
        ], spacing=0, expand=True)

    # ── Gráfico de ingresos ──────────────────────────────────────────────────

    def _card_ingresos(self) -> ft.Control:
        """
        La tarjeta con los chips Día/Mes/Año y las barras.

        Cambiar de escala repinta SÓLO esta tarjeta, no el dashboard entero:
        rearmar todo volvería a pedir métricas, actividad y socios por un click.
        """
        chips = ft.Row([], spacing=8, wrap=True)
        contenido = ft.Column([], spacing=0)

        def pintar(escala: str):
            self._escala = escala
            chips.controls = [
                filter_chip(label, valor == escala,
                            on_click=lambda e, v=valor: cambiar(v))
                for valor, label in ESCALAS_INGRESOS
            ]
            contenido.controls = [
                self._grafico_ingresos(app_state.get_ingresos_por_periodo(escala), escala)
            ]

        def cambiar(escala: str):
            pintar(escala)
            chips.update()
            contenido.update()

        pintar(self._escala)
        return section_card(
            ft.Column([chips, ft.Container(height=12), contenido], spacing=0),
            title="Ingresos",
        )

    def _grafico_ingresos(self, datos: dict, escala: str) -> ft.Control:
        puntos = datos["puntos"]
        # `+ [1]` para que el máximo nunca sea cero: sin cobros, todas las
        # barras quedan en cero y no hay división por cero.
        maximo = max([p["monto"] for p in puntos] + [1])
        # Con 30 barras no entran 30 rótulos: uno cada cinco. Mes y año, todos.
        cada = 5 if escala == "dia" else 1
        separacion = 2 if escala == "dia" else 6

        barras, rotulos = [], []
        for i, p in enumerate(puntos):
            # 4% de piso para que un día chico no desaparezca al lado de uno
            # grande. Mismo criterio que ALTURA_MINIMA en la PWA.
            alto = 0 if p["monto"] <= 0 else int(
                ALTO_GRAFICO * (0.04 + 0.96 * p["monto"] / maximo))
            barras.append(ft.Container(
                content=ft.Column([
                    ft.Container(
                        height=alto,
                        bgcolor=alpha(Colors.PRIMARY_VOLT, 0.7),
                        border_radius=2,
                        tooltip=f"{p['etiqueta']}: {_formatear(p['monto'], 'moneda')}",
                    ),
                ], alignment=ft.MainAxisAlignment.END, spacing=0),
                height=ALTO_GRAFICO,
                expand=True,
            ))
            rotulos.append(ft.Container(
                content=ft.Text(p["etiqueta"] if i % cada == 0 else "",
                                size=9, color=Colors.TEXT_MUTED,
                                text_align=ft.TextAlign.CENTER, no_wrap=True),
                expand=True,
            ))

        return ft.Column([
            ft.Text(_formatear(datos["total"], "moneda"), size=24,
                    weight=ft.FontWeight.BOLD, font_family=Fonts.MONO,
                    color=Colors.TEXT_MAIN),
            ft.Text(RANGO_INGRESOS[escala], size=12, color=Colors.TEXT_MUTED),
            *([ft.Container(height=6),
               ft.Text("Todavía no hay cobros confirmados en este período.",
                       size=12, color=Colors.TEXT_MUTED)]
              if not datos["total"] else []),
            ft.Container(height=12),
            ft.Row(barras, spacing=separacion),
            ft.Container(height=1, bgcolor=Colors.BORDER_IDLE),
            ft.Container(height=6),
            ft.Row(rotulos, spacing=separacion),
        ], spacing=0)

    def _acceso(self, acceso: dict) -> ft.Container:
        """Atajo del panel lateral: ícono cuadrado coloreado | texto | flecha."""
        color = acceso["color"]

        btn = ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(acceso["icono"], color=color, size=16),
                    width=32, height=32, border_radius=Radius.SM,
                    bgcolor=alpha(color, 0.10),
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Text(acceso["label"], color=Colors.TEXT_MAIN, size=14,
                        font_family=Fonts.BODY, expand=True),
                ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, color=Colors.TEXT_MUTED, size=16),
            ], spacing=12),
            border_radius=Radius.SM,
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            on_click=lambda e, r=acceso["ruta"]: self.router.navigate(r),
            animate=ft.Animation(120, ft.AnimationCurve.EASE_OUT),
        )

        def on_hover(e: ft.HoverEvent):
            btn.bgcolor = alpha(color, 0.10) if str(e.data).lower() == "true" else None
            btn.update()

        btn.on_hover = on_hover
        return btn


# =============================================================================
# PIEZAS DEL DASHBOARD
# =============================================================================

def _item_actividad(act: dict) -> ft.Container:
    """Fila del feed: ícono con fondo translúcido | descripción | hora relativa."""
    icono, color = ICONOS_ACTIVIDAD.get(act["tipo"],
                                        (ft.Icons.INFO_ROUNDED, Colors.PRIMARY_VOLT))
    return ft.Container(
        content=ft.Row([
            ft.Container(
                content=ft.Icon(icono, color=color, size=16),
                width=36, height=36, border_radius=Radius.SM,
                bgcolor=alpha(color, 0.10),
                alignment=ft.Alignment.CENTER,
            ),
            ft.Column([
                ft.Text(act["desc"], color=Colors.TEXT_MAIN, size=14,
                        font_family=Fonts.BODY),
                ft.Text(act["hora"], color=Colors.TEXT_MUTED, size=12,
                        font_family=Fonts.BODY),
            ], spacing=1, tight=True, expand=True),
        ], spacing=12),
        padding=ft.Padding.symmetric(vertical=10),
    )


def _fila_socio(s: dict) -> ft.Container:
    """
    Fila de socio reciente.

    El avatar acá NO es el círculo volt con texto oscuro que se usa en la
    tabla de Socios: en el dashboard la web lo pinta al revés —círculo oscuro
    con las iniciales en volt— para que la lista no compita visualmente con
    las métricas de arriba (SocioRow.tsx).
    """
    iniciales = "".join(p[0] for p in s["nombre"].split()[:2]).upper()

    return ft.Container(
        content=ft.Row([
            ft.Container(
                content=ft.Text(iniciales, color=Colors.PRIMARY_VOLT, size=13,
                                weight=ft.FontWeight.BOLD, font_family=Fonts.TITLE),
                width=36, height=36, border_radius=18,
                bgcolor=Colors.SURFACE_HOVER,
                alignment=ft.Alignment.CENTER,
            ),
            ft.Column([
                ft.Text(s["nombre"], color=Colors.TEXT_MAIN, size=14,
                        font_family=Fonts.BODY),
                ft.Text(s["plan"], color=Colors.TEXT_MUTED, size=12,
                        font_family=Fonts.BODY),
            ], spacing=1, tight=True, expand=True),
            status_badge(s["estado"]),
        ], spacing=12),
        padding=ft.Padding.symmetric(vertical=10),
    )


# =============================================================================
# FORMATO
# =============================================================================

def _formatear(valor, formato: str) -> str:
    """Número con separador de miles, o precio si la métrica es de plata."""
    if formato == "moneda":
        return f"$ {int(valor):,}".replace(",", ".")
    try:
        return f"{int(valor):,}".replace(",", ".")
    except (TypeError, ValueError):
        return str(valor)


def _texto_delta(delta_pct: float | None, comparacion: str) -> str:
    """
    Arma el texto del delta: "+80% vs mes anterior".

    Se construye acá y no en state.py por la misma razón que en la web: el
    dato es el porcentaje, la frase de comparación es cosa de la vista.

    CON None DEVUELVE CADENA VACÍA, y `stat_card` con un delta vacío no dibuja
    el renglón. Eso es lo que pide el contrato del backend, que ya lo tenía
    escrito en el docstring de `_delta` (routers/dashboard.py): el delta es
    None —no cero— cuando el mes anterior fue cero, porque dividir daría
    infinito y mostrar "+100%" al pasar de 0 a 1 socio sería inventar un dato.
    "La vista, con None, no muestra nada, que es lo honesto."

    Esa mitad del contrato no estaba implementada acá y reventaba con
    `'>=' not supported between instances of 'NoneType' and 'int'` apenas se
    abría el Dashboard sobre una base sin historial — o sea, en la primera
    demo. La PWA sí la tenía (`textoDelta` en DashboardView.tsx devuelve
    undefined); era una asimetría entre gemelas, no una decisión.
    """
    if delta_pct is None:
        return ""

    signo = "+" if delta_pct >= 0 else ""
    # Los porcentajes redondos se muestran sin decimales; el resto con uno y
    # coma decimal, como se escribe en castellano.
    if float(delta_pct).is_integer():
        numero = f"{signo}{int(delta_pct)}%"
    else:
        numero = f"{signo}{delta_pct:.1f}%".replace(".", ",")
    return f"{numero} {comparacion}"
