# =============================================================================
# views/rutinas.py — Gestión de rutinas de entrenamiento
# =============================================================================
# Esta vista muestra el catálogo de rutinas de entrenamiento disponibles.
# Cada rutina se presenta como una tarjeta con:
#   - Nivel de dificultad (badge coloreado)
#   - Frecuencia semanal y duración
#   - Barra de progreso de socios asignados vs. capacidad máxima
#   - Botones para ver detalles o asignar la rutina
# Permite crear nuevas rutinas mediante un modal.

import flet as ft
from app.config import Colors
from app.state import app_state
from app.components.ui import (build_topbar, level_badge, primary_button,
                                input_field, show_snack, open_dialog, close_dialog)


class RutinasView:
    def __init__(self, page: ft.Page, router):
        self.page   = page
        self.router = router

    def build(self) -> ft.Column:
        """Construye la vista con topbar y grilla responsiva de tarjetas de rutinas."""
        rutinas = app_state.get_rutinas()  # Obtiene la lista de rutinas del estado global

        topbar = build_topbar(
            "Rutinas",
            f"{len(rutinas)} rutinas disponibles",
            actions=[
                primary_button("Nueva Rutina", ft.Icons.ADD_ROUNDED,
                               on_click=self._open_form),
            ]
        )

        # Grilla responsiva: 1 col en mobile, 2 en tablet, 3 en desktop
        cards = ft.ResponsiveRow(
            [self._rutina_card(r) for r in rutinas],
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

    def _rutina_card(self, r: dict) -> ft.Container:
        """
        Construye la tarjeta de una rutina individual.
        Calcula el progreso como fracción de socios asignados sobre el máximo esperado (35).
        """
        # Calcula el porcentaje de ocupación — min(..., 1.0) evita superar el 100%
        progress = min(r["asignados"] / 35, 1.0)

        return ft.Container(
            col={"xs": 12, "sm": 6, "md": 4},  # Responsivo: 1/2/3 columnas
            content=ft.Column([
                # Fila superior: ícono de rutina + badge de nivel de dificultad
                ft.Row([
                    ft.Container(
                        content=ft.Icon(ft.Icons.FITNESS_CENTER_ROUNDED,
                                        color=Colors.ACCENT, size=22),
                        width=44, height=44, border_radius=12,
                        bgcolor=Colors.ACCENT_GLOW,
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Container(expand=True),
                    level_badge(r["nivel"]),  # Verde/Amarillo/Rojo según dificultad
                ]),
                ft.Container(height=14),
                # Nombre de la rutina
                ft.Text(r["nombre"], color=Colors.TEXT_PRIMARY, size=16,
                        weight=ft.FontWeight.BOLD),
                ft.Container(height=8),
                # Pills informativos: frecuencia y duración
                ft.Row([
                    _info_pill(ft.Icons.CALENDAR_TODAY_ROUNDED, f"{r['dias']} días/sem"),
                    _info_pill(ft.Icons.TIMER_ROUNDED, r["duracion"]),
                ], spacing=8),
                ft.Container(height=14),
                # Contador de socios asignados
                ft.Row([
                    ft.Text("Asignados:", color=Colors.TEXT_MUTED, size=12),
                    ft.Text(f"{r['asignados']} socios", color=Colors.TEXT_SECONDARY,
                            size=12, weight=ft.FontWeight.W_500),
                ], spacing=6),
                ft.Container(height=6),
                # Barra de progreso de ocupación (naranja, altura mínima 4px)
                ft.ProgressBar(
                    value=progress,
                    bgcolor=Colors.BG_INPUT,  # Fondo de la barra (parte vacía)
                    color=Colors.ACCENT,      # Color de la parte llena
                    height=4,
                    border_radius=2,
                ),
                ft.Container(height=14),
                # Botones de acción: ver detalles y asignar
                ft.Row([
                    ft.Container(
                        content=ft.Text("Ver detalles", color=Colors.ACCENT,
                                        size=12, weight=ft.FontWeight.W_500),
                        # x=r captura el valor actual de r (evita closure con el valor final del loop)
                        on_click=lambda e, x=r: self._open_detail(x),
                        bgcolor=Colors.ACCENT_GLOW, border_radius=8,
                        padding=ft.padding.symmetric(horizontal=12, vertical=6),
                    ),
                    ft.Container(
                        content=ft.Text("Asignar", color=Colors.TEXT_SECONDARY, size=12),
                        on_click=lambda e: show_snack(self.page, "Función próximamente"),
                        bgcolor=Colors.BG_SIDEBAR, border_radius=8,
                        padding=ft.padding.symmetric(horizontal=12, vertical=6),
                    ),
                ], spacing=8),
            ], spacing=0),
            bgcolor=Colors.BG_CARD,
            border_radius=14,
            border=ft.border.all(1, Colors.BORDER),
            padding=20,
        )

    def _open_form(self, e=None, rutina: dict = None):
        """
        Abre el modal para crear o editar una rutina.
        El modal incluye campos para nombre, nivel, días, duración y descripción.
        """
        is_edit = rutina is not None
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Nueva Rutina" if not is_edit else "Editar Rutina",
                          color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=440,
                content=ft.Column([
                    input_field("Nombre de la rutina", "Ej: Fuerza Total",
                                icon=ft.Icons.FITNESS_CENTER_ROUNDED),
                    ft.Container(height=12),
                    ft.Dropdown(
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
                    # Fila con dos inputs de ancho fijo en paralelo
                    ft.Row([
                        input_field("Días/semana", "Ej: 3",
                                    icon=ft.Icons.CALENDAR_TODAY_ROUNDED, width=180),
                        ft.Container(width=8),
                        input_field("Duración (min)", "Ej: 60",
                                    icon=ft.Icons.TIMER_ROUNDED, width=180),
                    ]),
                    ft.Container(height=12),
                    # Área de texto multilínea para descripción detallada
                    ft.TextField(
                        label="Descripción",
                        hint_text="Detalle los ejercicios y objetivos...",
                        multiline=True, min_lines=3, max_lines=5,
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
                ft.TextButton("Crear Rutina",
                              style=ft.ButtonStyle(color=Colors.ACCENT),
                              on_click=lambda e: self._save(dlg)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(self.page, dlg)

    def _open_detail(self, r: dict):
        """
        Abre un modal de solo lectura con los detalles de una rutina.
        Muestra nivel, frecuencia, duración, asignados y una descripción genérica.
        """
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(r["nombre"], color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=400,
                content=ft.Column([
                    ft.Row([level_badge(r["nivel"])]),     # Badge de dificultad
                    ft.Container(height=16),
                    # Filas de información clave (label: valor)
                    _detail_row("Frecuencia", f"{r['dias']} días por semana"),
                    _detail_row("Duración",   r["duracion"]),
                    _detail_row("Asignados",  f"{r['asignados']} socios"),
                    ft.Container(height=12),
                    ft.Text("Descripción", color=Colors.TEXT_MUTED, size=12,
                            weight=ft.FontWeight.W_600),
                    ft.Container(height=4),
                    # Texto genérico — se reemplazará con datos reales del backend
                    ft.Text("Rutina completa de entrenamiento. Los detalles específicos "
                            "se configurarán al conectar con el backend.",
                            color=Colors.TEXT_SECONDARY, size=13),
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

    def _save(self, dlg):
        """
        Guarda la nueva rutina.
        TODO: conectar con POST /api/rutinas
        """
        close_dialog(self.page, dlg)
        show_snack(self.page, "Rutina creada correctamente ✓", Colors.SUCCESS)


def _info_pill(icon: str, text: str) -> ft.Container:
    """
    Pequeño chip/pill informativo con ícono y texto.
    Se usa para mostrar frecuencia y duración en las tarjetas de rutinas.
    """
    return ft.Container(
        content=ft.Row([
            ft.Icon(icon, color=Colors.TEXT_MUTED, size=12),
            ft.Text(text, color=Colors.TEXT_SECONDARY, size=12),
        ], spacing=4),
        bgcolor=Colors.BG_SIDEBAR,
        border_radius=20,
        padding=ft.padding.symmetric(horizontal=10, vertical=4),
    )


def _detail_row(label: str, value: str) -> ft.Row:
    """
    Fila de detalle con label muted a la izquierda y valor principal a la derecha.
    Usada en el modal de detalles de la rutina.
    """
    from app.config import Colors
    return ft.Row([
        ft.Text(f"{label}:", color=Colors.TEXT_MUTED, size=13, width=100),  # Ancho fijo para alineación
        ft.Text(value, color=Colors.TEXT_PRIMARY, size=13, weight=ft.FontWeight.W_500),
    ])
