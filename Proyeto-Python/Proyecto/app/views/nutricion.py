# =============================================================================
# views/nutricion.py — Gestión de planes nutricionales
# =============================================================================
# Esta vista administra los planes de alimentación del gimnasio.
# Características:
#   - Resumen estadístico: promedio calórico, plan más bajo, más alto, total asignados
#   - Grilla de tarjetas por plan, cada una mostrando calorías y objetivo
#   - Modal de creación con campos de nombre, objetivo, calorías y macronutrientes
#   - Modal de detalle con distribución de macros en barras de progreso

import flet as ft
from app.config import Colors
from app.state import app_state
from app.components.ui import (build_topbar, primary_button, input_field,
                                show_snack, open_dialog, close_dialog)

# Configuración visual por objetivo nutricional:
# objetivo → (color de texto, fondo translúcido, ícono de tendencia)
OBJETIVO_CONFIG = {
    "Masa muscular":    (Colors.SUCCESS,  "#22C55E20", ft.Icons.TRENDING_UP_ROUNDED),
    "Bajar peso":       (Colors.DANGER,   "#EF444420", ft.Icons.TRENDING_DOWN_ROUNDED),
    "Mantenimiento":    (Colors.INFO,     "#3B82F620", ft.Icons.TRENDING_FLAT_ROUNDED),
    "Alto rendimiento": (Colors.WARNING,  "#F59E0B20", ft.Icons.BOLT_ROUNDED),
}


class NutricionView:
    def __init__(self, page: ft.Page, router):
        self.page   = page
        self.router = router

    def build(self) -> ft.Column:
        """Construye la vista con resumen estadístico y grilla de planes."""
        planes = app_state.get_planes_nutricion()  # Lista de planes nutricionales

        topbar = build_topbar(
            "Nutrición",
            f"{len(planes)} planes nutricionales",
            actions=[
                primary_button("Nuevo Plan", ft.Icons.ADD_ROUNDED,
                               on_click=self._open_form),
            ]
        )

        # ── Resumen calórico ───────────────────────────────────────────────────
        # Calcula estadísticas a partir de la lista de planes para mostrar KPIs
        cals = [p["calorias"] for p in planes]  # Lista de calorías de todos los planes
        summary = ft.Container(
            content=ft.Row([
                _cal_stat("Promedio Cal.",  f"{sum(cals)//len(cals)} kcal",
                          ft.Icons.LOCAL_FIRE_DEPARTMENT_ROUNDED, Colors.ACCENT),
                _cal_stat("Plan más bajo",  f"{min(cals)} kcal",
                          ft.Icons.ARROW_DOWNWARD_ROUNDED, Colors.INFO),
                _cal_stat("Plan más alto",  f"{max(cals)} kcal",
                          ft.Icons.ARROW_UPWARD_ROUNDED, Colors.SUCCESS),
                _cal_stat("Total asignados",
                          f"{sum(p['asignados'] for p in planes)} socios",
                          ft.Icons.GROUP_ROUNDED, Colors.WARNING),
            ], spacing=16),
            padding=ft.padding.only(bottom=20),
        )

        # Grilla responsiva de tarjetas: 1 columna en mobile, 2 en tablet/desktop
        cards = ft.ResponsiveRow(
            [self._plan_card(p) for p in planes],
            spacing=16, run_spacing=16,
        )

        body = ft.Column([
            topbar,
            ft.Container(
                content=ft.Column([summary, cards], spacing=0),
                padding=ft.padding.all(24),
                expand=True,
            ),
        ], spacing=0, expand=True, scroll=ft.ScrollMode.AUTO)

        return body

    def _plan_card(self, p: dict) -> ft.Container:
        """
        Construye la tarjeta de un plan nutricional.
        Muestra el objetivo con color e ícono, el nombre, las calorías en grande
        y la cantidad de socios asignados con un botón de detalle.
        """
        # Obtiene configuración visual del objetivo; usa gris como fallback
        color, bg, icon = OBJETIVO_CONFIG.get(
            p["objetivo"], (Colors.TEXT_SECONDARY, Colors.BG_INPUT, ft.Icons.RESTAURANT_MENU_ROUNDED)
        )

        return ft.Container(
            col={"xs": 12, "sm": 6},  # 1 columna en mobile, 2 en pantallas más anchas
            content=ft.Column([
                # Fila superior: ícono de objetivo + badge de objetivo
                ft.Row([
                    ft.Container(
                        content=ft.Icon(icon, color=color, size=22),
                        width=46, height=46, border_radius=12,
                        bgcolor=bg, alignment=ft.Alignment.CENTER,
                    ),
                    ft.Container(expand=True),
                    # Badge del objetivo (Masa muscular, Bajar peso, etc.)
                    ft.Container(
                        content=ft.Text(p["objetivo"], color=color, size=11,
                                        weight=ft.FontWeight.W_600),
                        bgcolor=bg, border_radius=20,
                        padding=ft.padding.symmetric(horizontal=10, vertical=4),
                    ),
                ]),
                ft.Container(height=14),
                # Nombre del plan
                ft.Text(p["nombre"], color=Colors.TEXT_PRIMARY, size=17,
                        weight=ft.FontWeight.BOLD),
                ft.Container(height=6),
                # Calorías en número grande (DM Sans) + unidad "kcal/día"
                ft.Row([
                    ft.Text(str(p["calorias"]), color=Colors.ACCENT, size=28,
                            weight=ft.FontWeight.BOLD, font_family="DM Sans"),
                    ft.Text("kcal/día", color=Colors.TEXT_MUTED, size=14),
                ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.END),
                ft.Container(height=12),
                ft.Divider(color=Colors.BORDER, height=1),
                ft.Container(height=10),
                # Pie de tarjeta: socios asignados + botón de detalle
                ft.Row([
                    ft.Row([
                        ft.Icon(ft.Icons.GROUP_ROUNDED, color=Colors.TEXT_MUTED, size=14),
                        ft.Text(f"{p['asignados']} asignados",
                                color=Colors.TEXT_SECONDARY, size=12),
                    ], spacing=4),
                    ft.Container(expand=True),
                    ft.TextButton(
                        "Ver plan",
                        style=ft.ButtonStyle(color=Colors.ACCENT),
                        on_click=lambda e, x=p: self._open_detail(x),
                    ),
                ]),
            ], spacing=0),
            bgcolor=Colors.BG_CARD,
            border_radius=14,
            border=ft.border.all(1, Colors.BORDER),
            padding=20,
        )

    def _open_form(self, e=None):
        """
        Abre el modal de creación de un nuevo plan nutricional.
        Incluye campos para nombre, objetivo, calorías y distribución de macros.
        """
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Nuevo Plan Nutricional",
                          color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=440,
                content=ft.Column([
                    input_field("Nombre del plan", "Ej: Volumen Limpio",
                                icon=ft.Icons.RESTAURANT_MENU_ROUNDED),
                    ft.Container(height=12),
                    # Dropdown de objetivo nutricional
                    ft.Dropdown(
                        label="Objetivo",
                        options=[ft.dropdown.Option(k) for k in OBJETIVO_CONFIG],
                        value="Mantenimiento",  # Valor por defecto
                        color=Colors.TEXT_PRIMARY, bgcolor=Colors.BG_INPUT,
                        border_color=Colors.BORDER, focused_border_color=Colors.ACCENT,
                        border_radius=10,
                    ),
                    ft.Container(height=12),
                    input_field("Calorías diarias (kcal)", "Ej: 2400",
                                icon=ft.Icons.LOCAL_FIRE_DEPARTMENT_ROUNDED),
                    ft.Container(height=12),
                    # Fila de tres inputs para macronutrientes en paralelo
                    ft.Row([
                        input_field("Proteínas (g)", "150", width=130),
                        ft.Container(width=8),
                        input_field("Carbos (g)", "250", width=130),
                        ft.Container(width=8),
                        input_field("Grasas (g)", "70", width=130),
                    ]),
                    ft.Container(height=12),
                    # Área de texto para notas adicionales (restricciones, preferencias)
                    ft.TextField(
                        label="Notas adicionales",
                        hint_text="Restricciones, alimentos preferidos...",
                        multiline=True, min_lines=3, max_lines=4,
                        color=Colors.TEXT_PRIMARY,
                        hint_style=ft.TextStyle(color=Colors.TEXT_MUTED),
                        bgcolor=Colors.BG_INPUT,
                        border_color=Colors.BORDER,
                        focused_border_color=Colors.ACCENT,
                        border_radius=10,
                        content_padding=ft.padding.all(12),
                    ),
                ], spacing=0, tight=True),
            ),
            actions=[
                ft.TextButton("Cancelar",
                              style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                              on_click=lambda e: close_dialog(self.page, dlg)),
                ft.TextButton("Crear Plan",
                              style=ft.ButtonStyle(color=Colors.ACCENT),
                              on_click=lambda e: self._save(dlg)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(self.page, dlg)

    def _open_detail(self, p: dict):
        """
        Abre el modal de detalle de un plan nutricional.
        Muestra objetivo, calorías y distribución de macronutrientes
        en barras de progreso (30% proteínas, 50% carbos, 20% grasas — referencial).
        """
        color, bg, icon = OBJETIVO_CONFIG.get(
            p["objetivo"], (Colors.TEXT_SECONDARY, Colors.BG_INPUT, ft.Icons.INFO_ROUNDED)
        )
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(p["nombre"], color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=380,
                content=ft.Column([
                    # Fila de objetivo con ícono y nombre
                    ft.Row([
                        ft.Container(
                            content=ft.Icon(icon, color=color, size=18),
                            width=36, height=36, border_radius=10,
                            bgcolor=bg, alignment=ft.Alignment.CENTER,
                        ),
                        ft.Text(p["objetivo"], color=color, size=14,
                                weight=ft.FontWeight.W_500),
                    ], spacing=10),
                    ft.Container(height=16),
                    # Calorías en grande
                    ft.Row([
                        ft.Text(str(p["calorias"]), color=Colors.ACCENT, size=36,
                                weight=ft.FontWeight.BOLD, font_family="DM Sans"),
                        ft.Text("kcal / día", color=Colors.TEXT_MUTED, size=14),
                    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.END),
                    ft.Container(height=16),
                    ft.Text("Distribución de macros (referencial)",
                            color=Colors.TEXT_MUTED, size=12),
                    ft.Container(height=8),
                    # Barras de progreso para cada macronutriente
                    _macro_bar("Proteínas",      0.30, Colors.SUCCESS),  # 30%
                    ft.Container(height=6),
                    _macro_bar("Carbohidratos",  0.50, Colors.INFO),     # 50%
                    ft.Container(height=6),
                    _macro_bar("Grasas",         0.20, Colors.WARNING),  # 20%
                    ft.Container(height=16),
                    # Cantidad de socios asignados
                    ft.Row([
                        ft.Icon(ft.Icons.GROUP_ROUNDED, color=Colors.TEXT_MUTED, size=14),
                        ft.Text(f"{p['asignados']} socios asignados a este plan",
                                color=Colors.TEXT_SECONDARY, size=13),
                    ], spacing=6),
                ], spacing=0),
            ),
            actions=[
                ft.TextButton("Cerrar",
                              style=ft.ButtonStyle(color=Colors.ACCENT),
                              on_click=lambda e: close_dialog(self.page, dlg)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(self.page, dlg)

    def _save(self, dlg):
        """
        Guarda el nuevo plan nutricional.
        TODO: conectar con POST /api/nutricion
        """
        close_dialog(self.page, dlg)
        show_snack(self.page, "Plan nutricional creado ✓", Colors.SUCCESS)


def _cal_stat(label: str, value: str, icon: str, color: str) -> ft.Container:
    """
    Tarjeta de estadística calórica para el resumen superior.
    Más compacta que stat_card() del dashboard — solo ícono, valor y label.
    expand=True hace que las 4 tarjetas compartan el ancho disponible equitativamente.
    """
    return ft.Container(
        content=ft.Column([
            ft.Container(
                content=ft.Icon(icon, color=color, size=18),
                width=36, height=36, border_radius=10,
                bgcolor=f"{color}20", alignment=ft.Alignment.CENTER,
            ),
            ft.Text(value, color=Colors.TEXT_PRIMARY, size=16,
                    weight=ft.FontWeight.BOLD),
            ft.Text(label, color=Colors.TEXT_SECONDARY, size=12),
        ], spacing=4),
        bgcolor=Colors.BG_CARD,
        border_radius=12,
        border=ft.border.all(1, Colors.BORDER),
        padding=16,
        expand=True,
    )


def _macro_bar(label: str, pct: float, color: str) -> ft.Column:
    """
    Construye una fila de distribución de macronutriente con:
      - Label a la izquierda y porcentaje a la derecha
      - ProgressBar que muestra visualmente la proporción
    pct: valor entre 0.0 y 1.0 que representa el porcentaje del macronutriente.
    """
    from app.config import Colors
    return ft.Column([
        ft.Row([
            ft.Text(label, color=Colors.TEXT_SECONDARY, size=12, width=110),
            ft.Text(f"{int(pct*100)}%", color=color, size=12,
                    weight=ft.FontWeight.W_600),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.ProgressBar(value=pct, bgcolor=Colors.BG_INPUT, color=color,
                       height=6, border_radius=3),
    ], spacing=4)
