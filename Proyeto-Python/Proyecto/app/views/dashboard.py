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
from app.state import app_state
from app.components.ui import (build_topbar, stat_card, section_card,
                               status_badge, primary_button, divider_row)


# Ancho del panel de accesos rápidos. La PWA lo fija en 240px
# (ANCHO_ACCESOS_RAPIDOS en DashboardView.tsx).
ANCHO_ACCESOS = 240

# ── Configuración de las 4 tarjetas de métricas ──────────────────────────────
# Declarativo, igual que TARJETAS en la web: agregar o reordenar una métrica es
# tocar esta lista y nada más.
#
# `requiere_ingresos` marca la de facturación: el Recepcionista ve el dashboard
# "parcial" (todas menos esa). Hoy no se filtra porque los permisos entran con
# la API — queda declarado para que el filtro sea una línea cuando llegue.
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

    def build(self) -> ft.Column:
        stats     = app_state.get_dashboard_stats()
        actividad = app_state.get_actividad_reciente()
        socios    = app_state.get_socios()[:4]

        topbar = build_topbar(
            "Dashboard",
            f"Hola, {app_state.get_user_name()}",
            actions=[
                primary_button("Nuevo socio", ft.Icons.PERSON_ADD_ROUNDED,
                               on_click=lambda e: self.router.navigate(Routes.SOCIOS)),
            ],
        )

        # ── 1. Métricas ──────────────────────────────────────────────────────
        tarjetas = []
        for t in TARJETAS:
            m = stats[t["clave"]]
            tarjetas.append(
                stat_card(
                    t["titulo"],
                    _formatear(m["valor"], t["formato"]),
                    _texto_delta(m["delta_pct"], t["comparacion"]),
                    "down" if m["delta_pct"] < 0 else "up",
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
                *[self._acceso(a) for a in ACCESOS_RAPIDOS],
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
                    fila_metricas,
                    ft.Container(height=24),
                    card_actividad,
                    ft.Container(height=24),
                    fila_inferior,
                ], spacing=0, scroll=ft.ScrollMode.AUTO, expand=True),
                padding=ft.Padding.all(32),
                expand=True,
            ),
        ], spacing=0, expand=True)

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


def _texto_delta(delta_pct: float, comparacion: str) -> str:
    """
    Arma el texto del delta: "+80% vs mes anterior".

    Se construye acá y no en state.py por la misma razón que en la web: el
    dato es el porcentaje, la frase de comparación es cosa de la vista.
    """
    signo = "+" if delta_pct >= 0 else ""
    # Los porcentajes redondos se muestran sin decimales; el resto con uno y
    # coma decimal, como se escribe en castellano.
    if float(delta_pct).is_integer():
        numero = f"{signo}{int(delta_pct)}%"
    else:
        numero = f"{signo}{delta_pct:.1f}%".replace(".", ",")
    return f"{numero} {comparacion}"
