# =============================================================================
# views/socios.py — Consulta y modificación de socios
# =============================================================================
# El alta de un socio nuevo se hace desde la sección "Nueva Persona"
# (app/views/alta_persona.py). Esta pantalla es solo para ver el listado,
# buscar, editar el plan/estado de un socio existente, o eliminarlo.

import flet as ft
from app.config import Colors, Routes
from app.state import app_state, PLAN_DISPLAY, ESTADO_SOCIO_DISPLAY
from app.components.ui import (build_topbar, status_badge, primary_button,
                                show_snack, open_dialog, close_dialog, confirm_dialog)


class SociosView:
    def __init__(self, page: ft.Page, router):
        self.page = page
        self.router = router
        self.search_ref = ft.Ref[ft.TextField]()
        self.table_ref = ft.Ref[ft.Column]()
        self._todos_los_socios: list = []

    def build(self) -> ft.Column:
        self._todos_los_socios = app_state.get_socios()

        topbar = build_topbar(
            "Socios",
            f"{len(self._todos_los_socios)} socios registrados",
            actions=[
                primary_button("Nueva Persona", ft.Icons.PERSON_ADD_ROUNDED,
                               on_click=lambda e: self.router.navigate(Routes.ALTA)),
            ]
        )

        search_bar = ft.Container(
            content=ft.TextField(
                ref=self.search_ref,
                hint_text="Buscar por nombre, plan...",
                prefix_icon=ft.Icons.SEARCH_ROUNDED,
                color=Colors.TEXT_PRIMARY,
                hint_style=ft.TextStyle(color=Colors.TEXT_MUTED),
                bgcolor=Colors.BG_INPUT,
                border_color=Colors.BORDER,
                focused_border_color=Colors.ACCENT,
                border_radius=10,
                height=44,
                content_padding=ft.Padding.symmetric(horizontal=16, vertical=10),
                on_change=self._on_search,
            ),
            padding=ft.Padding.only(bottom=16),
        )

        table_content = self._build_table(self._todos_los_socios)
        table_col = ft.Column(ref=self.table_ref, controls=[table_content])

        body = ft.Column([
            topbar,
            ft.Container(
                content=ft.Column([
                    search_bar,
                    ft.Container(
                        content=table_col,
                        bgcolor=Colors.BG_CARD,
                        border_radius=14,
                        border=ft.Border.all(1, Colors.BORDER),
                        padding=0,
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    ),
                ]),
                padding=ft.Padding.all(24),
                expand=True,
            ),
        ], spacing=0, expand=True, scroll=ft.ScrollMode.AUTO)

        return body

    def _build_table(self, socios: list) -> ft.Column:
        header = ft.Container(
            content=ft.Row([
                ft.Text("DNI",      color=Colors.TEXT_MUTED, size=12, weight=ft.FontWeight.W_600, expand=2),
                ft.Text("Nombre",   color=Colors.TEXT_MUTED, size=12, weight=ft.FontWeight.W_600, expand=3),
                ft.Text("Plan",     color=Colors.TEXT_MUTED, size=12, weight=ft.FontWeight.W_600, expand=2),
                ft.Text("Estado",   color=Colors.TEXT_MUTED, size=12, weight=ft.FontWeight.W_600, expand=2),
                ft.Text("Vence",    color=Colors.TEXT_MUTED, size=12, weight=ft.FontWeight.W_600, expand=2),
                ft.Text("Acciones", color=Colors.TEXT_MUTED, size=12, weight=ft.FontWeight.W_600, expand=2),
            ]),
            padding=ft.Padding.symmetric(horizontal=20, vertical=14),
            bgcolor=Colors.BG_SIDEBAR,
        )

        rows = [header]
        if not socios:
            rows.append(ft.Container(
                content=ft.Column([
                    ft.Text("Todavía no hay socios cargados.", color=Colors.TEXT_MUTED, size=13),
                    ft.Container(height=6),
                    ft.Text("Usá \"Nueva Persona\" para dar de alta al primero.",
                            color=Colors.TEXT_MUTED, size=12),
                ]),
                padding=ft.Padding.symmetric(horizontal=20, vertical=20),
            ))
        for s in socios:
            rows.append(self._table_row(s))

        return ft.Column(rows, spacing=0)

    def _table_row(self, s: dict) -> ft.Container:
        initial = s["nombre"][0].upper() if s["nombre"] else "?"

        def on_hover(e: ft.HoverEvent):
            e.control.bgcolor = Colors.BG_INPUT if e.data == "true" else ft.Colors.TRANSPARENT
            e.control.update()

        return ft.Container(
            content=ft.Row([
                ft.Container(content=ft.Text(s["dni"], color=Colors.TEXT_SECONDARY, size=13), expand=2),
                ft.Row([
                    ft.Container(
                        content=ft.Text(initial, color=Colors.WHITE, size=13, weight=ft.FontWeight.BOLD),
                        width=32, height=32, border_radius=16,
                        bgcolor=Colors.ACCENT, alignment=ft.Alignment.CENTER,
                    ),
                    ft.Text(s["nombre"], color=Colors.TEXT_PRIMARY, size=14),
                ], spacing=10, expand=3),
                ft.Container(content=ft.Text(s["plan"], color=Colors.TEXT_SECONDARY, size=13), expand=2),
                ft.Container(content=status_badge(s["estado"]), expand=2, alignment=ft.Alignment.CENTER_LEFT),
                ft.Text(s["vence"], color=Colors.TEXT_SECONDARY, size=13, expand=2),
                ft.Row([
                    ft.IconButton(ft.Icons.EDIT_ROUNDED, icon_color=Colors.INFO,
                                  icon_size=18, tooltip="Editar",
                                  on_click=lambda e, x=s: self._open_editar(x)),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE_ROUNDED, icon_color=Colors.DANGER,
                                  icon_size=18, tooltip="Eliminar",
                                  on_click=lambda e, x=s: self._confirm_delete(x)),
                ], expand=2),
            ]),
            padding=ft.Padding.symmetric(horizontal=20, vertical=12),
            border=ft.Border.only(bottom=ft.BorderSide(1, Colors.BORDER)),
            on_hover=on_hover,
            animate=ft.Animation(120),
        )

    def _on_search(self, e):
        query = (e.control.value or "").lower()
        filtered = [s for s in self._todos_los_socios
                    if query in s["nombre"].lower() or query in s["plan"].lower()]
        self.table_ref.current.controls = [self._build_table(filtered)]
        self.table_ref.current.update()

    def _refrescar(self):
        self._todos_los_socios = app_state.get_socios()
        self.table_ref.current.controls = [self._build_table(self._todos_los_socios)]
        self.table_ref.current.update()

    def _open_editar(self, socio: dict):
        plan_ref = ft.Ref[ft.Dropdown]()
        estado_ref = ft.Ref[ft.Dropdown]()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Editar {socio['nombre']}", color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=380,
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.BADGE_ROUNDED, color=Colors.TEXT_MUTED, size=14),
                        ft.Text(f"DNI: {socio['dni']}", color=Colors.TEXT_SECONDARY, size=13),
                    ], spacing=8),
                    ft.Container(height=16),
                    ft.Dropdown(
                        ref=plan_ref, label="Plan",
                        options=[ft.dropdown.Option(v) for v in PLAN_DISPLAY.values()],
                        value=socio["plan"],
                        color=Colors.TEXT_PRIMARY, bgcolor=Colors.BG_INPUT,
                        border_color=Colors.BORDER, focused_border_color=Colors.ACCENT,
                        border_radius=10,
                    ),
                    ft.Container(height=12),
                    ft.Dropdown(
                        ref=estado_ref, label="Estado",
                        options=[ft.dropdown.Option(v) for v in ESTADO_SOCIO_DISPLAY.values()],
                        value=socio["estado"],
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
                              on_click=lambda e: self._guardar_edicion(dlg, socio, plan_ref, estado_ref)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(self.page, dlg)

    def _guardar_edicion(self, dlg, socio, plan_ref, estado_ref):
        resultado = app_state.actualizar_socio(socio["dni"], plan_ref.current.value, estado_ref.current.value)
        close_dialog(self.page, dlg)

        if resultado["ok"]:
            show_snack(self.page, "Socio actualizado correctamente ✓", Colors.SUCCESS)
            self._refrescar()
        else:
            show_snack(self.page, resultado["mensaje"] or "No se pudo actualizar", Colors.DANGER)

    def _confirm_delete(self, socio: dict):
        dlg = confirm_dialog(
            self.page, "Eliminar Socio",
            f"¿Estás seguro de eliminar a {socio['nombre']} como socio? Esta acción no se puede deshacer.",
            on_confirm=lambda: self._eliminar(socio),
        )
        open_dialog(self.page, dlg)

    def _eliminar(self, socio: dict):
        resultado = app_state.eliminar_socio(socio["dni"])
        if resultado["ok"]:
            show_snack(self.page, f"{socio['nombre']} eliminado", Colors.DANGER)
            self._refrescar()
        else:
            show_snack(self.page, resultado["mensaje"] or "No se pudo eliminar", Colors.DANGER)
