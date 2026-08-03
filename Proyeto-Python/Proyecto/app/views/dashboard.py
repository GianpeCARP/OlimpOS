# =============================================================================
# views/dashboard.py — Vista principal del dashboard
# =============================================================================
# Esta vista es la pantalla de inicio tras el login exitoso.
# Muestra un resumen ejecutivo del gimnasio con cuatro secciones:
#   1. Tarjetas de estadísticas (socios, ingresos, clases, nuevos)
#   2. Feed de actividad reciente
#   3. Lista de socios recientes
#   4. Panel de accesos rápidos a otras secciones

import flet as ft
from app.config import Colors, Routes           # Colores globales y rutas de navegación
from app.state import app_state                 # Estado global con los datos mock
# Componentes reutilizables del sistema de diseño
from app.components.ui import (build_topbar, stat_card, section_card,
                                status_badge, primary_button)


class DashboardView:
    """
    Vista del Dashboard principal.
    Sigue el patrón de todas las vistas del sistema:
      - Se instancia con `page` y `router` como dependencias
      - Expone un método `build()` que retorna el árbol de controles Flet
    """

    def __init__(self, page: ft.Page, router):
        self.page   = page    # Referencia a la ventana — necesaria para diálogos y snacks
        self.router = router  # Referencia al router — para los botones de navegación

    def build(self) -> ft.Column:
        """
        Construye y retorna el árbol completo de controles de la vista.
        Obtiene los datos del estado global y los organiza en secciones.
        """
        stats     = app_state.get_dashboard_stats()      # Dict con 4 métricas del gimnasio
        actividad = app_state.get_actividad_reciente()   # Lista de 5 eventos recientes

        # ── Topbar de sección ─────────────────────────────────────────────────
        # Muestra "Dashboard" como título, saludo al usuario y botón "Nuevo Socio"
        topbar = build_topbar(
            "Dashboard",
            f"Bienvenido, {app_state.get_user_name()} 👋",  # Saludo personalizado
            actions=[
                # Botón de acción rápida que navega directamente a la sección Socios
                primary_button("Nuevo Socio", ft.Icons.PERSON_ADD_ROUNDED,
                               on_click=lambda e: self.router.navigate(Routes.SOCIOS)),
            ]
        )

        # ── Tarjetas de estadísticas ──────────────────────────────────────────
        # Cuatro tarjetas en fila horizontal, cada una con una métrica clave.
        # stat_card() recibe: título, valor, delta, tendencia, ícono y color.
        stats_row = ft.Row([
            stat_card("Socios Activos",
                      stats["socios_activos"]["valor"],
                      stats["socios_activos"]["delta"],
                      stats["socios_activos"]["tendencia"],
                      ft.Icons.GROUP_ROUNDED, Colors.INFO),          # Azul
            stat_card("Ingresos Mensuales",
                      stats["ingresos_mes"]["valor"],
                      stats["ingresos_mes"]["delta"],
                      stats["ingresos_mes"]["tendencia"],
                      ft.Icons.ATTACH_MONEY_ROUNDED, Colors.SUCCESS), # Verde
            stat_card("Clases Hoy",
                      stats["clases_hoy"]["valor"],
                      stats["clases_hoy"]["delta"],
                      stats["clases_hoy"]["tendencia"],
                      ft.Icons.FITNESS_CENTER_ROUNDED, Colors.ACCENT),# Verde del sistema
            stat_card("Nuevos este Mes",
                      stats["nuevos_mes"]["valor"],
                      stats["nuevos_mes"]["delta"],
                      stats["nuevos_mes"]["tendencia"],
                      ft.Icons.PERSON_ADD_ROUNDED, Colors.WARNING),  # Amarillo
        ], spacing=16)

        # ── Actividad reciente ────────────────────────────────────────────────
        # Genera un widget por cada evento de actividad usando la función helper
        activity_items = [_activity_item(a) for a in actividad]

        # Envuelve los ítems en una section_card con título
        activity_card = section_card(
            ft.Column(activity_items, spacing=0),  # Columna de ítems sin espaciado extra
            title="Actividad Reciente",
            padding=20,
        )

        # ── Accesos rápidos ───────────────────────────────────────────────────
        # Panel lateral con botones que navegan directamente a secciones clave.
        # Cada botón usa _quick_btn() que incluye ícono, texto y animación hover.
        quick_access = ft.Column([
            ft.Text("Accesos Rápidos", color=Colors.TEXT_PRIMARY, size=15,
                    weight=ft.FontWeight.BOLD),
            ft.Container(height=12),
            _quick_btn("Registrar Socio", ft.Icons.PERSON_ADD_ROUNDED,
                       Colors.INFO,    lambda e: self.router.navigate(Routes.SOCIOS)),
            ft.Container(height=8),
            _quick_btn("Asignar Rutina", ft.Icons.FITNESS_CENTER_ROUNDED,
                       Colors.SUCCESS,  lambda e: self.router.navigate(Routes.RUTINAS)),
            ft.Container(height=8),
            _quick_btn("Plan Nutricional", ft.Icons.RESTAURANT_MENU_ROUNDED,
                       Colors.WARNING,  lambda e: self.router.navigate(Routes.NUTRICION)),
            ft.Container(height=8),
            _quick_btn("Ver Personal", ft.Icons.BADGE_ROUNDED,
                       Colors.ACCENT,   lambda e: self.router.navigate(Routes.PERSONAL)),
        ])

        # Envuelve el panel de accesos rápidos en un Container con estilo de tarjeta
        quick_card = ft.Container(
            content=quick_access,
            bgcolor=Colors.BG_CARD,
            border_radius=14,
            border=ft.border.all(1, Colors.BORDER),
            padding=20,
            width=240,  # Ancho fijo igual al sidebar para alineación visual
        )

        # ── Socios recientes ──────────────────────────────────────────────────
        # Muestra los primeros 4 socios de la lista con su estado
        socios = app_state.get_socios()[:4]         # Solo los 4 primeros
        socios_rows = [_socio_row(s) for s in socios] # Un widget por socio

        socios_card = section_card(
            ft.Column(socios_rows, spacing=4),
            title="Socios Recientes",
            padding=20,
        )

        # ── Fila inferior: socios + accesos rápidos ───────────────────────────
        # Layout de dos columnas: lista de socios (flexible) + panel rápido (fijo)
        bottom_row = ft.Row([
            ft.Column([socios_card], expand=True),  # Socios ocupa el espacio restante
            quick_card,                              # Panel fijo de 240px a la derecha
        ], spacing=16, vertical_alignment=ft.CrossAxisAlignment.START)

        # ── Ensamblado final de la vista ──────────────────────────────────────
        # Column principal con topbar + área de contenido con scroll
        body = ft.Column([
            topbar,
            ft.Container(
                content=ft.Column([
                    stats_row,                          # Tarjetas de estadísticas
                    ft.Container(height=16),
                    ft.Row([
                        ft.Column([activity_card], expand=True),  # Feed de actividad
                    ]),
                    ft.Container(height=16),
                    bottom_row,                         # Socios + accesos rápidos
                ], spacing=0),
                padding=ft.padding.all(24),            # Padding interior del área de contenido
                expand=True,
            ),
        ], spacing=0, expand=True, scroll=ft.ScrollMode.AUTO)  # Scroll automático si el contenido supera la ventana

        return body


# =============================================================================
# HELPERS PRIVADOS DEL DASHBOARD
# =============================================================================

# Mapeo de tipo de actividad → (ícono, color)
# Permite que cada tipo de evento tenga su representación visual única
ACTIVITY_ICONS = {
    "nuevo_socio": (ft.Icons.PERSON_ADD_ROUNDED,    Colors.INFO),     # Azul para nuevos socios
    "pago":        (ft.Icons.ATTACH_MONEY_ROUNDED,  Colors.SUCCESS),  # Verde para pagos
    "rutina":      (ft.Icons.FITNESS_CENTER_ROUNDED, Colors.ACCENT),  # Naranja para rutinas
    "vencimiento": (ft.Icons.WARNING_ROUNDED,        Colors.WARNING), # Amarillo para alertas
}

def _activity_item(act: dict) -> ft.Container:
    """
    Construye un ítem individual del feed de actividad reciente.
    Muestra: ícono de tipo en fondo coloreado, descripción y hora relativa.
    Incluye una línea divisoria inferior para separar los ítems.
    """
    # Obtiene ícono y color según el tipo de actividad, con valores por defecto
    icon, color = ACTIVITY_ICONS.get(act["tipo"], (ft.Icons.INFO_ROUNDED, Colors.INFO))

    return ft.Container(
        content=ft.Row([
            # Ícono de tipo con fondo translúcido del color correspondiente
            ft.Container(
                content=ft.Icon(icon, color=color, size=16),
                width=34, height=34, border_radius=10,
                bgcolor=f"{color}20",             # 20 en hex = ~12% de opacidad
                alignment=ft.Alignment.CENTER,
            ),
            # Columna derecha: descripción en texto principal + hora en texto muted
            ft.Column([
                ft.Text(act["desc"], color=Colors.TEXT_PRIMARY, size=13),
                ft.Text(act["hora"], color=Colors.TEXT_MUTED, size=11),
            ], spacing=2, tight=True, expand=True),
        ], spacing=12),
        padding=ft.padding.symmetric(vertical=10, horizontal=4),
        # Línea divisoria solo en la parte inferior de cada ítem
        border=ft.border.only(bottom=ft.BorderSide(1, Colors.BORDER)),
    )


def _quick_btn(label: str, icon: str, color: str, on_click) -> ft.Container:
    """
    Construye un botón de acceso rápido para el panel lateral del dashboard.
    Diseño: ícono coloreado | texto | flecha derecha
    Incluye animación hover que cambia el fondo al color del ícono.
    """
    def on_hover(e: ft.HoverEvent):
        """Al hacer hover, cambia el fondo a la versión translúcida del color del ícono."""
        e.control.bgcolor = f"{color}20" if e.data == "true" else Colors.BG_INPUT
        e.control.update()

    return ft.Container(
        content=ft.Row([
            # Ícono cuadrado con color de categoría
            ft.Container(
                content=ft.Icon(icon, color=color, size=18),
                width=34, height=34, border_radius=8,
                bgcolor=f"{color}20",
                alignment=ft.Alignment.CENTER,
            ),
            ft.Text(label, color=Colors.TEXT_PRIMARY, size=13),
            ft.Container(expand=True),  # Empuja la flecha a la derecha
            ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, color=Colors.TEXT_MUTED, size=18),
        ], spacing=10),
        bgcolor=Colors.BG_INPUT,        # Fondo oscuro en reposo
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
        on_click=on_click,
        on_hover=on_hover,
        animate=ft.Animation(120),     # Transición de color muy rápida (120ms)
    )


def _socio_row(s: dict) -> ft.Container:
    """
    Construye una fila de la lista de socios recientes.
    Muestra: avatar con inicial | nombre y plan | badge de estado
    """
    initial = s["nombre"][0].upper()  # Primera letra del nombre para el avatar

    return ft.Container(
        content=ft.Row([
            # Avatar circular naranja con la inicial del socio
            ft.Container(
                content=ft.Text(initial, color=Colors.WHITE, size=13,
                                weight=ft.FontWeight.BOLD),
                width=34, height=34, border_radius=17,  # border_radius = mitad del tamaño → círculo
                bgcolor=Colors.ACCENT, alignment=ft.Alignment.CENTER,
            ),
            # Columna con nombre en texto principal y plan en texto secundario
            ft.Column([
                ft.Text(s["nombre"], color=Colors.TEXT_PRIMARY, size=13),
                ft.Text(s["plan"], color=Colors.TEXT_SECONDARY, size=11),
            ], spacing=1, tight=True, expand=True),
            # Badge de estado (Activo, Vencido, etc.) alineado a la derecha
            status_badge(s["estado"]),
        ], spacing=10),
        padding=ft.padding.symmetric(vertical=6),
        border=ft.border.only(bottom=ft.BorderSide(1, Colors.BORDER)),
    )
