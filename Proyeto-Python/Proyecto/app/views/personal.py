# =============================================================================
# views/personal.py — Gestión del personal del gimnasio
# =============================================================================
# Esta vista muestra el equipo de empleados en formato de tarjetas (cards).
# Cada card incluye: avatar, nombre, rol, turno y botones de acción.
# Permite agregar nuevos empleados o editar los existentes mediante un modal.

import flet as ft
from app.config import Colors
from app.state import app_state
from app.components.ui import (build_topbar, status_badge, primary_button,
                                input_field, show_snack, open_dialog, close_dialog)

# Mapa turno → (color de texto, color de fondo translúcido)
# Cada turno tiene un color distintivo para identificación visual rápida
TURNO_COLORS = {
    "Mañana": (Colors.WARNING, "#453511"),  # Amarillo — turno diurno
    "Tarde":  (Colors.INFO,    "#172554"),  # Azul — turno vespertino
    "Noche": ("#A78BFA", "#334155"), # Violeta — turno nocturno
}


# Mapa rol → ícono de Material Design correspondiente
ROL_ICONS = {
    "Entrenador":    ft.Icons.FITNESS_CENTER_ROUNDED,
    #"Entrenadora":   ft.Icons.FITNESS_CENTER_ROUNDED,
    "Nutricionista": ft.Icons.RESTAURANT_MENU_ROUNDED,
    "Recepcionista": ft.Icons.SUPPORT_AGENT_ROUNDED,
}


class PersonalView:
    def __init__(self, page: ft.Page, router):
        self.page   = page
        self.router = router

    def build(self) -> ft.Column:
        """Construye la vista con topbar y grilla de tarjetas de personal."""
        personal = app_state.get_personal()  # Lista de empleados del estado global

        topbar = build_topbar(
            "Personal",
            f"{len(personal)} empleados activos",
            actions=[
                primary_button("Agregar Empleado", ft.Icons.BADGE_ROUNDED,
                               on_click=self._open_form),
            ]
        )

        # ResponsiveRow adapta la cantidad de columnas al ancho de la ventana:
        # xs (mobile): 1 columna, sm (tablet): 2 columnas, md: 3, lg: 4
        cards = ft.ResponsiveRow(
            [self._staff_card(p) for p in personal],
            spacing=16, run_spacing=16,
        )

        body = ft.Column([
            topbar,
            ft.Container(
                content=ft.Column([cards], spacing=0),
                padding=ft.padding.all(24),
                expand=True,
            ),
        ], spacing=0, expand=True, scroll=ft.ScrollMode.AUTO)

        return body

    def _staff_card(self, p: dict) -> ft.Container:
        """
        Construye la tarjeta de un empleado individual.
        Layout vertical: avatar + estado | nombre | rol | chip de turno | acciones
        """
        initial   = p["nombre"][0].upper()  # Inicial para el avatar
        turno_c, turno_bg = TURNO_COLORS.get(p["turno"], (Colors.TEXT_SECONDARY, Colors.BG_INPUT))
        rol_icon  = ROL_ICONS.get(p["rol"], ft.Icons.PERSON_ROUNDED)

        return ft.Container(
            # col define el ancho responsivo de la tarjeta en el ResponsiveRow
            col={"xs": 12, "sm": 6, "md": 4, "lg": 3},
            content=ft.Column([
                # Fila superior: avatar + badge de estado
                ft.Row([
                    ft.Container(
                        content=ft.Text(initial, color=Colors.WHITE, size=20,
                                        weight=ft.FontWeight.BOLD),
                        width=52, height=52, border_radius=26,
                        bgcolor=Colors.ACCENT, alignment=ft.Alignment.CENTER,
                    ),
                    ft.Container(expand=True),
                    status_badge(p["estado"]),  # Badge Activo/Inactivo
                ]),
                ft.Container(height=12),
                # Nombre del empleado
                ft.Text(p["nombre"], color=Colors.TEXT_PRIMARY, size=15,
                        weight=ft.FontWeight.BOLD),
                # Rol con ícono correspondiente
                ft.Row([
                    ft.Icon(rol_icon, color=Colors.TEXT_SECONDARY, size=14),
                    ft.Text(p["rol"], color=Colors.TEXT_SECONDARY, size=13),
                ], spacing=4),
                ft.Container(height=12),
                # Chip de turno coloreado según horario (Mañana/Tarde/Noche)
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.SCHEDULE_ROUNDED, color=turno_c, size=14),
                        ft.Text(f"Turno {p['turno']}", color=turno_c, size=12,
                                weight=ft.FontWeight.W_500),
                    ], spacing=6),
                    bgcolor=turno_bg,
                    border_radius=20,
                    padding=ft.padding.symmetric(horizontal=10, vertical=5),
                ),
                ft.Container(height=16),
                # Botones de acción: Editar y Contactar
                ft.Row([
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.EDIT_ROUNDED, color=Colors.INFO, size=14),
                            ft.Text("Editar", color=Colors.INFO, size=12),
                        ], spacing=4),
                        # x=p captura la variable por valor en el lambda (evita closure bug)
                        on_click=lambda e, x=p: self._open_form(e, x),
                        bgcolor="#3B82F620", border_radius=8,
                        padding=ft.padding.symmetric(horizontal=10, vertical=6),
                    ),
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.EMAIL_OUTLINED, color=Colors.TEXT_SECONDARY, size=14),
                            ft.Text("Contactar", color=Colors.TEXT_SECONDARY, size=12),
                        ], spacing=4),
                        bgcolor=Colors.BG_SIDEBAR, border_radius=8,
                        padding=ft.padding.symmetric(horizontal=10, vertical=6),
                    ),
                ], spacing=8),
            ], spacing=4),
            bgcolor=Colors.BG_CARD,
            border_radius=14,
            border=ft.border.all(1, Colors.BORDER),
            padding=20,
        )

    def _open_form(self, e=None, empleado: dict = None):
        """
        Abre el modal de crear/editar empleado.
        En modo edición pre-carga el nombre y selecciona rol y turno del empleado.
        """
        is_edit    = empleado is not None
        nombre_ref = ft.Ref[ft.TextField]()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Editar Empleado" if is_edit else "Nuevo Empleado",
                          color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=420,
                content=ft.Column([
                    input_field("Nombre completo", "Ej: María González",
                                icon=ft.Icons.PERSON_OUTLINE_ROUNDED, ref=nombre_ref),
                    ft.Container(height=12),
                    ft.Dropdown(
                        label="Rol",
                        options=[
                            ft.dropdown.Option("Entrenador"),
                            ft.dropdown.Option("Nutricionista"),
                            ft.dropdown.Option("Recepcionista"),
                            ft.dropdown.Option("Administrativo"),
                        ],
                        value=empleado["rol"] if is_edit else "Entrenador",
                        color=Colors.TEXT_PRIMARY, bgcolor=Colors.BG_INPUT,
                        border_color=Colors.BORDER, focused_border_color=Colors.ACCENT,
                        border_radius=10,
                    ),
                    ft.Container(height=12),
                    ft.Dropdown(
                        label="Turno",
                        options=[
                            ft.dropdown.Option("Mañana"),
                            ft.dropdown.Option("Tarde"),
                            ft.dropdown.Option("Noche"),
                        ],
                        value=empleado["turno"] if is_edit else "Mañana",
                        color=Colors.TEXT_PRIMARY, bgcolor=Colors.BG_INPUT,
                        border_color=Colors.BORDER, focused_border_color=Colors.ACCENT,
                        border_radius=10,
                    ),
                    ft.Container(height=12),
                    input_field("Email", "empleado@gimnasio.com",
                                icon=ft.Icons.EMAIL_OUTLINED),
                ], spacing=0, tight=True),
            ),
            actions=[
                ft.TextButton("Cancelar",
                              style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                              on_click=lambda e: close_dialog(self.page, dlg)),
                ft.TextButton("Guardar",
                              style=ft.ButtonStyle(color=Colors.ACCENT),
                              on_click=lambda e: self._save(dlg)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        # Pre-carga el nombre si estamos editando y el Ref ya está montado
        if is_edit and nombre_ref.current:
            nombre_ref.current.value = empleado["nombre"]

        open_dialog(self.page, dlg)

    def _save(self, dlg):
        """
        Guarda el empleado (crear o editar).
        TODO: conectar con POST /api/personal o PUT /api/personal/{id}
        """
        close_dialog(self.page, dlg)
        show_snack(self.page, "Empleado guardado correctamente ✓", Colors.SUCCESS)
