# =============================================================================
# views/personal.py — Consulta y modificación del personal
# =============================================================================
# El alta de un empleado nuevo se hace desde "Nueva Persona". Acá solo
# se consulta el listado y se puede editar su rol/turno/estado o
# eliminar la ficha.

import flet as ft
from app.config import Colors, Routes
from app.state import app_state, ROL_DISPLAY, TURNO_LABORAL_DISPLAY, ESTADO_EMPLEADO_DISPLAY
from app.components.ui import build_topbar, status_badge, primary_button, show_snack, open_dialog, close_dialog

TURNO_COLORS = {
    "Mañana": (Colors.WARNING, "#F59E0B20"),
    "Tarde":  (Colors.INFO,    "#3B82F620"),
    "Noche":  ("#A78BFA",     "#A78BFA20"),
}

ROL_ICONS = {
    "Entrenador":    ft.Icons.FITNESS_CENTER_ROUNDED,
    "Nutricionista": ft.Icons.RESTAURANT_MENU_ROUNDED,
    "Recepción":     ft.Icons.SUPPORT_AGENT_ROUNDED,
    "Administrador": ft.Icons.ADMIN_PANEL_SETTINGS_ROUNDED,
    "Propietario":   ft.Icons.SHIELD_ROUNDED,
}


class PersonalView:
    def __init__(self, page: ft.Page, router):
        self.page = page
        self.router = router
        self.cards_ref = ft.Ref[ft.ResponsiveRow]()
        self._personal: list = []

    def build(self) -> ft.Column:
        self._personal = app_state.get_personal()

        topbar = build_topbar(
            "Personal",
            f"{len(self._personal)} empleados cargados",
            actions=[
                primary_button("Nueva Persona", ft.Icons.PERSON_ADD_ROUNDED,
                               on_click=lambda e: self.router.navigate(Routes.ALTA)),
            ]
        )

        cards = ft.ResponsiveRow(
            ref=self.cards_ref,
            controls=[self._staff_card(p) for p in self._personal],
            spacing=16, run_spacing=16,
        )

        body = ft.Column([
            topbar,
            ft.Container(
                content=ft.Column([cards], spacing=0),
                padding=ft.Padding.all(24),
                expand=True,
            ),
        ], spacing=0, expand=True, scroll=ft.ScrollMode.AUTO)

        return body

    def _refrescar(self):
        self._personal = app_state.get_personal()
        self.cards_ref.current.controls = [self._staff_card(p) for p in self._personal]
        self.cards_ref.current.update()

    def _staff_card(self, p: dict) -> ft.Container:
        initial = p["nombre"][0].upper() if p["nombre"] else "?"
        turno_c, turno_bg = TURNO_COLORS.get(p["turno"], (Colors.TEXT_SECONDARY, Colors.BG_INPUT))
        rol_icon = ROL_ICONS.get(p["rol"], ft.Icons.PERSON_ROUNDED)

        return ft.Container(
            col={"xs": 12, "sm": 6, "md": 4, "lg": 3},
            content=ft.Column([
                ft.Row([
                    ft.Container(
                        content=ft.Text(initial, color=Colors.WHITE, size=20, weight=ft.FontWeight.BOLD),
                        width=52, height=52, border_radius=26,
                        bgcolor=Colors.ACCENT, alignment=ft.Alignment.CENTER,
                    ),
                    ft.Container(expand=True),
                    status_badge(p["estado"]),
                ]),
                ft.Container(height=12),
                ft.Text(p["nombre"], color=Colors.TEXT_PRIMARY, size=15, weight=ft.FontWeight.BOLD),
                ft.Row([
                    ft.Icon(rol_icon, color=Colors.TEXT_SECONDARY, size=14),
                    ft.Text(p["rol"], color=Colors.TEXT_SECONDARY, size=13),
                ], spacing=4),
                ft.Container(height=12),
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.SCHEDULE_ROUNDED, color=turno_c, size=14),
                        ft.Text(f"Turno {p['turno']}", color=turno_c, size=12, weight=ft.FontWeight.W_500),
                    ], spacing=6),
                    bgcolor=turno_bg, border_radius=20,
                    padding=ft.Padding.symmetric(horizontal=10, vertical=5),
                ),
                ft.Container(height=16),
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.EDIT_ROUNDED, color=Colors.INFO, size=14),
                        ft.Text("Editar", color=Colors.INFO, size=12),
                    ], spacing=4),
                    on_click=lambda e, x=p: self._open_editar(x),
                    bgcolor="#3B82F620", border_radius=8,
                    padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                ),
            ], spacing=4),
            bgcolor=Colors.BG_CARD,
            border_radius=14,
            border=ft.Border.all(1, Colors.BORDER),
            padding=20,
        )

    def _open_editar(self, empleado: dict):
        rol_ref = ft.Ref[ft.Dropdown]()
        turno_ref = ft.Ref[ft.Dropdown]()
        estado_ref = ft.Ref[ft.Dropdown]()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Editar {empleado['nombre']}", color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=380,
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.BADGE_ROUNDED, color=Colors.TEXT_MUTED, size=14),
                        ft.Text(f"DNI: {empleado['dni']}", color=Colors.TEXT_SECONDARY, size=13),
                    ], spacing=8),
                    ft.Container(height=16),
                    ft.Dropdown(
                        ref=rol_ref, label="Rol",
                        options=[ft.dropdown.Option(v) for v in ROL_DISPLAY.values()],
                        value=empleado["rol"],
                        color=Colors.TEXT_PRIMARY, bgcolor=Colors.BG_INPUT,
                        border_color=Colors.BORDER, focused_border_color=Colors.ACCENT,
                        border_radius=10,
                    ),
                    ft.Container(height=12),
                    ft.Dropdown(
                        ref=turno_ref, label="Turno",
                        options=[ft.dropdown.Option(v) for v in TURNO_LABORAL_DISPLAY.values()],
                        value=empleado["turno"],
                        color=Colors.TEXT_PRIMARY, bgcolor=Colors.BG_INPUT,
                        border_color=Colors.BORDER, focused_border_color=Colors.ACCENT,
                        border_radius=10,
                    ),
                    ft.Container(height=12),
                    ft.Dropdown(
                        ref=estado_ref, label="Estado",
                        options=[ft.dropdown.Option(v) for v in ESTADO_EMPLEADO_DISPLAY.values()],
                        value=empleado["estado"],
                        color=Colors.TEXT_PRIMARY, bgcolor=Colors.BG_INPUT,
                        border_color=Colors.BORDER, focused_border_color=Colors.ACCENT,
                        border_radius=10,
                    ),
                ], spacing=0, tight=True),
            ),
            actions=[
                ft.TextButton("Cancelar", style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                              on_click=lambda e: close_dialog(self.page, dlg)),
                ft.TextButton("Guardar", style=ft.ButtonStyle(color=Colors.ACCENT),
                              on_click=lambda e: self._guardar_edicion(dlg, empleado, rol_ref, turno_ref, estado_ref)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(self.page, dlg)

    def _guardar_edicion(self, dlg, empleado, rol_ref, turno_ref, estado_ref):
        resultado = app_state.actualizar_empleado(
            empleado["dni"], rol_ref.current.value, turno_ref.current.value, estado_ref.current.value
        )
        close_dialog(self.page, dlg)

        if resultado["ok"]:
            show_snack(self.page, "Empleado actualizado correctamente ✓", Colors.SUCCESS)
            self._refrescar()
        else:
            show_snack(self.page, resultado["mensaje"] or "No se pudo actualizar", Colors.DANGER)
