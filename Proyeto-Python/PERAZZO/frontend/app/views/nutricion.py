# =============================================================================
# views/nutricion.py — Gestión de planes nutricionales
# =============================================================================

import flet as ft
from app.config import Colors
from app.state import app_state
from app.components.ui import (build_topbar, primary_button, input_field,
                                show_snack, open_dialog, close_dialog)

OBJETIVO_CONFIG = {
    "Masa muscular":    (Colors.SUCCESS,  "#22C55E20", ft.Icons.TRENDING_UP_ROUNDED),
    "Bajar peso":       (Colors.DANGER,   "#EF444420", ft.Icons.TRENDING_DOWN_ROUNDED),
    "Mantenimiento":    (Colors.INFO,     "#3B82F620", ft.Icons.TRENDING_FLAT_ROUNDED),
    "Alto rendimiento": (Colors.WARNING,  "#F59E0B20", ft.Icons.BOLT_ROUNDED),
}


class NutricionView:
    def __init__(self, page: ft.Page, router):
        self.page = page
        self.router = router
        self.cards_ref = ft.Ref[ft.ResponsiveRow]()
        self._planes: list = []

    def build(self) -> ft.Column:
        self._planes = app_state.get_planes_nutricion()

        topbar = build_topbar(
            "Nutrición",
            f"{len(self._planes)} planes nutricionales",
            actions=[
                primary_button("Nuevo Plan", ft.Icons.ADD_ROUNDED,
                               on_click=self._open_form),
            ]
        )

        cals = [p["calorias"] for p in self._planes] or [0]
        summary = ft.Container(
            content=ft.Row([
                _cal_stat("Promedio Cal.",  f"{sum(cals)//len(cals)} kcal",
                          ft.Icons.LOCAL_FIRE_DEPARTMENT_ROUNDED, Colors.ACCENT),
                _cal_stat("Plan más bajo",  f"{min(cals)} kcal",
                          ft.Icons.ARROW_DOWNWARD_ROUNDED, Colors.INFO),
                _cal_stat("Plan más alto",  f"{max(cals)} kcal",
                          ft.Icons.ARROW_UPWARD_ROUNDED, Colors.SUCCESS),
                _cal_stat("Total asignados",
                          f"{sum(p['asignados'] for p in self._planes)} socios",
                          ft.Icons.GROUP_ROUNDED, Colors.WARNING),
            ], spacing=16),
            padding=ft.Padding.only(bottom=20),
        )

        cards = ft.ResponsiveRow(
            ref=self.cards_ref,
            controls=[self._plan_card(p) for p in self._planes],
            spacing=16, run_spacing=16,
        )

        body = ft.Column([
            topbar,
            ft.Container(
                content=ft.Column([summary, cards], spacing=0),
                padding=ft.Padding.all(24),
                expand=True,
            ),
        ], spacing=0, expand=True, scroll=ft.ScrollMode.AUTO)

        return body

    def _refrescar(self):
        self._planes = app_state.get_planes_nutricion()
        self.cards_ref.current.controls = [self._plan_card(p) for p in self._planes]
        self.cards_ref.current.update()

    def _plan_card(self, p: dict) -> ft.Container:
        color, bg, icon = OBJETIVO_CONFIG.get(
            p["objetivo"], (Colors.TEXT_SECONDARY, Colors.BG_INPUT, ft.Icons.RESTAURANT_MENU_ROUNDED)
        )

        return ft.Container(
            col={"xs": 12, "sm": 6},
            content=ft.Column([
                ft.Row([
                    ft.Container(
                        content=ft.Icon(icon, color=color, size=22),
                        width=46, height=46, border_radius=12,
                        bgcolor=bg, alignment=ft.Alignment.CENTER,
                    ),
                    ft.Container(expand=True),
                    ft.Container(
                        content=ft.Text(p["objetivo"], color=color, size=11,
                                        weight=ft.FontWeight.W_600),
                        bgcolor=bg, border_radius=20,
                        padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                    ),
                ]),
                ft.Container(height=14),
                ft.Text(p["nombre"], color=Colors.TEXT_PRIMARY, size=17,
                        weight=ft.FontWeight.BOLD),
                ft.Container(height=6),
                ft.Row([
                    ft.Text(str(p["calorias"]), color=Colors.ACCENT, size=28,
                            weight=ft.FontWeight.BOLD, font_family="Bebas Neue"),
                    ft.Text("kcal/día", color=Colors.TEXT_MUTED, size=14),
                ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.END),
                ft.Container(height=12),
                ft.Divider(color=Colors.BORDER, height=1),
                ft.Container(height=10),
                ft.Row([
                    ft.Row([
                        ft.Icon(ft.Icons.GROUP_ROUNDED, color=Colors.TEXT_MUTED, size=14),
                        ft.Text(f"{p['asignados']} asignados",
                                color=Colors.TEXT_SECONDARY, size=12),
                    ], spacing=4),
                    ft.Container(expand=True),
                    ft.TextButton(
                        "Asignar",
                        style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                        on_click=lambda e, x=p: self._open_asignar(x),
                    ),
                    ft.TextButton(
                        "Ver plan",
                        style=ft.ButtonStyle(color=Colors.ACCENT),
                        on_click=lambda e, x=p: self._open_detail(x),
                    ),
                ]),
            ], spacing=0),
            bgcolor=Colors.BG_CARD,
            border_radius=14,
            border=ft.Border.all(1, Colors.BORDER),
            padding=20,
        )

    def _open_form(self, e=None):
        nombre_ref = ft.Ref[ft.TextField]()
        objetivo_ref = ft.Ref[ft.Dropdown]()
        calorias_ref = ft.Ref[ft.TextField]()
        proteinas_ref = ft.Ref[ft.TextField]()
        carbos_ref = ft.Ref[ft.TextField]()
        grasas_ref = ft.Ref[ft.TextField]()
        notas_ref = ft.Ref[ft.TextField]()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Nuevo Plan Nutricional",
                          color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=440,
                content=ft.Column([
                    input_field("Nombre del plan", "Ej: Volumen Limpio",
                                icon=ft.Icons.RESTAURANT_MENU_ROUNDED, ref=nombre_ref),
                    ft.Container(height=12),
                    ft.Dropdown(
                        ref=objetivo_ref,
                        label="Objetivo",
                        options=[ft.dropdown.Option(k) for k in OBJETIVO_CONFIG],
                        value="Mantenimiento",
                        color=Colors.TEXT_PRIMARY, bgcolor=Colors.BG_INPUT,
                        border_color=Colors.BORDER, focused_border_color=Colors.ACCENT,
                        border_radius=10,
                    ),
                    ft.Container(height=12),
                    input_field("Calorías diarias (kcal)", "Ej: 2400",
                                icon=ft.Icons.LOCAL_FIRE_DEPARTMENT_ROUNDED, ref=calorias_ref),
                    ft.Container(height=12),
                    ft.Row([
                        input_field("Proteínas (g)", "150", width=130, ref=proteinas_ref),
                        ft.Container(width=8),
                        input_field("Carbos (g)", "250", width=130, ref=carbos_ref),
                        ft.Container(width=8),
                        input_field("Grasas (g)", "70", width=130, ref=grasas_ref),
                    ]),
                    ft.Container(height=12),
                    ft.TextField(
                        ref=notas_ref,
                        label="Notas adicionales",
                        hint_text="Restricciones, alimentos preferidos...",
                        multiline=True, min_lines=3, max_lines=4,
                        color=Colors.TEXT_PRIMARY,
                        hint_style=ft.TextStyle(color=Colors.TEXT_MUTED),
                        bgcolor=Colors.BG_INPUT,
                        border_color=Colors.BORDER,
                        focused_border_color=Colors.ACCENT,
                        border_radius=10,
                        content_padding=ft.Padding.all(12),
                    ),
                ], spacing=0, tight=True),
            ),
            actions=[
                ft.TextButton("Cancelar",
                              style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                              on_click=lambda e: close_dialog(self.page, dlg)),
                ft.TextButton("Crear Plan",
                              style=ft.ButtonStyle(color=Colors.ACCENT),
                              on_click=lambda e: self._save(
                                  dlg, nombre_ref, objetivo_ref, calorias_ref,
                                  proteinas_ref, carbos_ref, grasas_ref, notas_ref)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(self.page, dlg)

    def _save(self, dlg, nombre_ref, objetivo_ref, calorias_ref,
              proteinas_ref, carbos_ref, grasas_ref, notas_ref):
        nombre = (nombre_ref.current.value or "").strip()
        if not nombre:
            show_snack(self.page, "El nombre del plan es obligatorio", Colors.DANGER)
            return

        objetivo_display = objetivo_ref.current.value

        try:
            calorias = int(calorias_ref.current.value or 0)
        except ValueError:
            show_snack(self.page, "Las calorías deben ser un número", Colors.DANGER)
            return

        def _a_entero_opcional(ref):
            valor = (ref.current.value or "").strip()
            return int(valor) if valor.isdigit() else None

        proteinas = _a_entero_opcional(proteinas_ref)
        carbohidratos = _a_entero_opcional(carbos_ref)
        grasas = _a_entero_opcional(grasas_ref)
        notas = (notas_ref.current.value or "").strip() or None

        resultado = app_state.crear_plan_nutricion(
            nombre, objetivo_display, calorias, proteinas, carbohidratos, grasas, notas
        )
        close_dialog(self.page, dlg)

        if resultado["ok"]:
            show_snack(self.page, "Plan nutricional creado ✓", Colors.SUCCESS)
            self._refrescar()
        else:
            show_snack(self.page, resultado["mensaje"] or "No se pudo crear el plan", Colors.DANGER)

    def _open_detail(self, p: dict):
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
                    ft.Row([
                        ft.Text(str(p["calorias"]), color=Colors.ACCENT, size=36,
                                weight=ft.FontWeight.BOLD, font_family="Bebas Neue"),
                        ft.Text("kcal / día", color=Colors.TEXT_MUTED, size=14),
                    ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.END),
                    ft.Container(height=16),
                    ft.Text("Distribución de macros", color=Colors.TEXT_MUTED, size=12),
                    ft.Container(height=8),
                    _macro_bar("Proteínas", p.get("proteinas_g"), Colors.SUCCESS),
                    ft.Container(height=6),
                    _macro_bar("Carbohidratos", p.get("carbohidratos_g"), Colors.INFO),
                    ft.Container(height=6),
                    _macro_bar("Grasas", p.get("grasas_g"), Colors.WARNING),
                    ft.Container(height=16),
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

    def _open_asignar(self, plan: dict):
        socios = app_state.get_socios()
        if not socios:
            show_snack(self.page, "Todavía no hay socios cargados para asignar.", Colors.WARNING)
            return

        socio_ref = ft.Ref[ft.Dropdown]()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Asignar '{plan['nombre']}'",
                          color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=380,
                content=ft.Dropdown(
                    ref=socio_ref,
                    label="Socio",
                    options=[ft.dropdown.Option(key=s["dni"], text=s["nombre"]) for s in socios],
                    color=Colors.TEXT_PRIMARY, bgcolor=Colors.BG_INPUT,
                    border_color=Colors.BORDER, focused_border_color=Colors.ACCENT,
                    border_radius=10,
                ),
            ),
            actions=[
                ft.TextButton("Cancelar",
                              style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                              on_click=lambda e: close_dialog(self.page, dlg)),
                ft.TextButton("Asignar",
                              style=ft.ButtonStyle(color=Colors.ACCENT),
                              on_click=lambda e: self._confirmar_asignacion(dlg, plan, socio_ref)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(self.page, dlg)

    def _confirmar_asignacion(self, dlg, plan, socio_ref):
        if not socio_ref.current.value:
            show_snack(self.page, "Elegí un socio para asignar el plan.", Colors.DANGER)
            return

        socio_dni = socio_ref.current.value
        resultado = app_state.asignar_plan_nutricion(plan["id"], socio_dni)
        close_dialog(self.page, dlg)

        if resultado["ok"]:
            show_snack(self.page, resultado["mensaje"], Colors.SUCCESS)
            self._refrescar()
        else:
            show_snack(self.page, resultado["mensaje"] or "No se pudo asignar el plan", Colors.DANGER)


def _cal_stat(label: str, value: str, icon: str, color: str) -> ft.Container:
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
        border=ft.Border.all(1, Colors.BORDER),
        padding=16,
        expand=True,
    )


def _macro_bar(label: str, gramos, color: str) -> ft.Column:
    """
    Barra de macronutriente. Si el plan tiene gramos cargados, muestra el
    valor real; si no (planes viejos sin ese dato), muestra un guion.
    """
    from app.config import Colors
    texto_valor = f"{gramos} g" if gramos else "-"
    return ft.Column([
        ft.Row([
            ft.Text(label, color=Colors.TEXT_SECONDARY, size=12, width=110),
            ft.Text(texto_valor, color=color, size=12, weight=ft.FontWeight.W_600),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
    ], spacing=4)
