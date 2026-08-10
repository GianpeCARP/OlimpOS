# =============================================================================
# views/rutinas.py — Gestión de rutinas de entrenamiento
# =============================================================================

import flet as ft
from app.config import Colors
from app.state import app_state
from app.components.ui import (build_topbar, level_badge, primary_button,
                                input_field, show_snack, open_dialog, close_dialog)


class RutinasView:
    def __init__(self, page: ft.Page, router):
        self.page = page
        self.router = router
        self.cards_ref = ft.Ref[ft.ResponsiveRow]()
        self._rutinas: list = []

    def build(self) -> ft.Column:
        self._rutinas = app_state.get_rutinas()

        topbar = build_topbar(
            "Rutinas",
            f"{len(self._rutinas)} rutinas disponibles",
            actions=[
                primary_button("Nueva Rutina", ft.Icons.ADD_ROUNDED,
                               on_click=self._open_form),
            ]
        )

        cards = ft.ResponsiveRow(
            ref=self.cards_ref,
            controls=[self._rutina_card(r) for r in self._rutinas],
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
        self._rutinas = app_state.get_rutinas()
        self.cards_ref.current.controls = [self._rutina_card(r) for r in self._rutinas]
        self.cards_ref.current.update()

    def _rutina_card(self, r: dict) -> ft.Container:
        progress = min(r["asignados"] / 35, 1.0)

        return ft.Container(
            col={"xs": 12, "sm": 6, "md": 4},
            content=ft.Column([
                ft.Row([
                    ft.Container(
                        content=ft.Icon(ft.Icons.FITNESS_CENTER_ROUNDED,
                                        color=Colors.ACCENT, size=22),
                        width=44, height=44, border_radius=12,
                        bgcolor=Colors.ACCENT_GLOW,
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Container(expand=True),
                    level_badge(r["nivel"]),
                ]),
                ft.Container(height=14),
                ft.Text(r["nombre"], color=Colors.TEXT_PRIMARY, size=16,
                        weight=ft.FontWeight.BOLD),
                ft.Container(height=8),
                ft.Row([
                    _info_pill(ft.Icons.CALENDAR_TODAY_ROUNDED, f"{r['dias']} días/sem"),
                    _info_pill(ft.Icons.TIMER_ROUNDED, r["duracion"]),
                ], spacing=8),
                ft.Container(height=14),
                ft.Row([
                    ft.Text("Asignados:", color=Colors.TEXT_MUTED, size=12),
                    ft.Text(f"{r['asignados']} socios", color=Colors.TEXT_SECONDARY,
                            size=12, weight=ft.FontWeight.W_500),
                ], spacing=6),
                ft.Container(height=6),
                ft.ProgressBar(
                    value=progress,
                    bgcolor=Colors.BG_INPUT,
                    color=Colors.ACCENT,
                    height=4,
                    border_radius=2,
                ),
                ft.Container(height=14),
                ft.Row([
                    ft.Container(
                        content=ft.Text("Ver detalles", color=Colors.ACCENT,
                                        size=12, weight=ft.FontWeight.W_500),
                        on_click=lambda e, x=r: self._open_detail(x),
                        bgcolor=Colors.ACCENT_GLOW, border_radius=8,
                        padding=ft.Padding.symmetric(horizontal=12, vertical=6),
                    ),
                    ft.Container(
                        content=ft.Text("Asignar", color=Colors.TEXT_SECONDARY, size=12),
                        on_click=lambda e, x=r: self._open_asignar(x),
                        bgcolor=Colors.BG_SIDEBAR, border_radius=8,
                        padding=ft.Padding.symmetric(horizontal=12, vertical=6),
                    ),
                ], spacing=8),
            ], spacing=0),
            bgcolor=Colors.BG_CARD,
            border_radius=14,
            border=ft.Border.all(1, Colors.BORDER),
            padding=20,
        )

    def _open_form(self, e=None):
        nombre_ref = ft.Ref[ft.TextField]()
        nivel_ref = ft.Ref[ft.Dropdown]()
        dias_ref = ft.Ref[ft.TextField]()
        duracion_ref = ft.Ref[ft.TextField]()
        descripcion_ref = ft.Ref[ft.TextField]()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Nueva Rutina", color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=440,
                content=ft.Column([
                    input_field("Nombre de la rutina", "Ej: Fuerza Total",
                                icon=ft.Icons.FITNESS_CENTER_ROUNDED, ref=nombre_ref),
                    ft.Container(height=12),
                    ft.Dropdown(
                        ref=nivel_ref,
                        label="Nivel",
                        options=[
                            ft.dropdown.Option("Principiante"),
                            ft.dropdown.Option("Intermedio"),
                            ft.dropdown.Option("Avanzado"),
                        ],
                        value="Principiante",
                        color=Colors.TEXT_PRIMARY, bgcolor=Colors.BG_INPUT,
                        border_color=Colors.BORDER, focused_border_color=Colors.ACCENT,
                        border_radius=10,
                    ),
                    ft.Container(height=12),
                    ft.Row([
                        input_field("Días/semana", "Ej: 3",
                                    icon=ft.Icons.CALENDAR_TODAY_ROUNDED, width=180, ref=dias_ref),
                        ft.Container(width=8),
                        input_field("Duración (min)", "Ej: 60",
                                    icon=ft.Icons.TIMER_ROUNDED, width=180, ref=duracion_ref),
                    ]),
                    ft.Container(height=12),
                    ft.TextField(
                        ref=descripcion_ref,
                        label="Descripción",
                        hint_text="Detalle los ejercicios y objetivos...",
                        multiline=True, min_lines=3, max_lines=5,
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
                ft.TextButton("Crear Rutina",
                              style=ft.ButtonStyle(color=Colors.ACCENT),
                              on_click=lambda e: self._save(
                                  dlg, nombre_ref, nivel_ref, dias_ref, duracion_ref, descripcion_ref)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(self.page, dlg)

    def _save(self, dlg, nombre_ref, nivel_ref, dias_ref, duracion_ref, descripcion_ref):
        nombre = (nombre_ref.current.value or "").strip()
        if not nombre:
            show_snack(self.page, "El nombre de la rutina es obligatorio", Colors.DANGER)
            return

        nivel_display = nivel_ref.current.value

        try:
            dias = int(dias_ref.current.value or 3)
        except ValueError:
            dias = 3
        try:
            duracion = int(duracion_ref.current.value or 60)
        except ValueError:
            duracion = 60

        descripcion = (descripcion_ref.current.value or "").strip() or None

        resultado = app_state.crear_rutina(nombre, nivel_display, dias, duracion, descripcion)
        close_dialog(self.page, dlg)

        if resultado["ok"]:
            show_snack(self.page, "Rutina creada correctamente ✓", Colors.SUCCESS)
            self._refrescar()
        else:
            show_snack(self.page, resultado["mensaje"] or "No se pudo crear la rutina", Colors.DANGER)

    def _open_detail(self, r: dict):
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(r["nombre"], color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=400,
                content=ft.Column([
                    ft.Row([level_badge(r["nivel"])]),
                    ft.Container(height=16),
                    _detail_row("Frecuencia", f"{r['dias']} días por semana"),
                    _detail_row("Duración", r["duracion"]),
                    _detail_row("Asignados", f"{r['asignados']} socios"),
                ], spacing=6),
            ),
            actions=[
                ft.TextButton("Cerrar",
                              style=ft.ButtonStyle(color=Colors.ACCENT),
                              on_click=lambda e: close_dialog(self.page, dlg)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(self.page, dlg)

    def _open_asignar(self, rutina: dict):
        """
        Abre un modal con un Dropdown de socios para elegir a quién
        asignarle la rutina. Antes este botón solo mostraba "Función
        próximamente"; ahora llama de verdad a POST /rutinas/{id}/asignar/{socio_id}.
        """
        socios = app_state.get_socios()
        if not socios:
            show_snack(self.page, "Todavía no hay socios cargados para asignar.", Colors.WARNING)
            return

        socio_ref = ft.Ref[ft.Dropdown]()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Asignar '{rutina['nombre']}'",
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
                              on_click=lambda e: self._confirmar_asignacion(dlg, rutina, socio_ref)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(self.page, dlg)

    def _confirmar_asignacion(self, dlg, rutina, socio_ref):
        if not socio_ref.current.value:
            show_snack(self.page, "Elegí un socio para asignar la rutina.", Colors.DANGER)
            return

        socio_dni = socio_ref.current.value
        resultado = app_state.asignar_rutina(rutina["id"], socio_dni)
        close_dialog(self.page, dlg)

        if resultado["ok"]:
            show_snack(self.page, resultado["mensaje"], Colors.SUCCESS)
            self._refrescar()
        else:
            show_snack(self.page, resultado["mensaje"] or "No se pudo asignar la rutina", Colors.DANGER)


def _info_pill(icon: str, text: str) -> ft.Container:
    return ft.Container(
        content=ft.Row([
            ft.Icon(icon, color=Colors.TEXT_MUTED, size=12),
            ft.Text(text, color=Colors.TEXT_SECONDARY, size=12),
        ], spacing=4),
        bgcolor=Colors.BG_SIDEBAR,
        border_radius=20,
        padding=ft.Padding.symmetric(horizontal=10, vertical=4),
    )


def _detail_row(label: str, value: str) -> ft.Row:
    from app.config import Colors
    return ft.Row([
        ft.Text(f"{label}:", color=Colors.TEXT_MUTED, size=13, width=100),
        ft.Text(value, color=Colors.TEXT_PRIMARY, size=13, weight=ft.FontWeight.W_500),
    ])
