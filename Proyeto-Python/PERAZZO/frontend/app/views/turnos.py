# =============================================================================
# views/turnos.py — Grilla semanal de turnos (clases) del gimnasio
# =============================================================================
# Vista pensada para que de un vistazo se vea toda la semana: una columna
# por día, con una tarjeta por turno ordenada por horario. Cada tarjeta
# muestra el nombre de la clase, el horario, el instructor y el cupo
# ocupado. Clickeando "Inscribir socio" se anota a un socio en el turno,
# igual patrón que "Asignar" en Rutinas/Nutrición.

import flet as ft
from app.config import Colors
from app.state import app_state, DIAS_SEMANA_ORDEN
from app.components.ui import (build_topbar, primary_button, input_field,
                                show_snack, open_dialog, close_dialog)

# Paleta de colores sugerida para las clases (el admin puede tipear otro hex si quiere)
COLORES_SUGERIDOS = [
    ("Naranja", "#FF5722"), ("Verde", "#22C55E"), ("Azul", "#3B82F6"),
    ("Violeta", "#A78BFA"), ("Amarillo", "#F59E0B"), ("Rosa", "#EC4899"),
]


class TurnosView:
    def __init__(self, page: ft.Page, router):
        self.page = page
        self.router = router
        self.grilla_ref = ft.Ref[ft.Row]()
        self._turnos: list = []

    def build(self) -> ft.Column:
        self._turnos = app_state.get_turnos()

        topbar = build_topbar(
            "Turnos",
            f"{len(self._turnos)} clases programadas esta semana",
            actions=[
                primary_button("Nuevo Turno", ft.Icons.ADD_ROUNDED,
                               on_click=self._open_form),
            ]
        )

        grilla = ft.Row(
            ref=self.grilla_ref,
            controls=self._construir_columnas_dias(),
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.START,
            scroll=ft.ScrollMode.AUTO,
        )

        body = ft.Column([
            topbar,
            ft.Container(
                content=grilla,
                padding=ft.Padding.all(24),
                expand=True,
            ),
        ], spacing=0, expand=True, scroll=ft.ScrollMode.AUTO)

        return body

    def _refrescar(self):
        self._turnos = app_state.get_turnos()
        self.grilla_ref.current.controls = self._construir_columnas_dias()
        self.grilla_ref.current.update()

    def _construir_columnas_dias(self) -> list:
        columnas = []
        for dia in DIAS_SEMANA_ORDEN:
            turnos_del_dia = sorted(
                [t for t in self._turnos if t["dia"] == dia],
                key=lambda t: t["hora_inicio"],
            )
            columnas.append(self._columna_dia(dia, turnos_del_dia))
        return columnas

    def _columna_dia(self, dia: str, turnos_del_dia: list) -> ft.Container:
        tarjetas = [self._turno_card(t) for t in turnos_del_dia]
        if not tarjetas:
            tarjetas = [
                ft.Container(
                    content=ft.Text("Sin turnos", color=Colors.TEXT_MUTED, size=11,
                                    text_align=ft.TextAlign.CENTER),
                    padding=ft.Padding.symmetric(vertical=16),
                    alignment=ft.Alignment.CENTER,
                )
            ]

        return ft.Container(
            width=190,
            content=ft.Column([
                ft.Container(
                    content=ft.Text(dia, color=Colors.TEXT_PRIMARY, size=14,
                                    weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                    padding=ft.Padding.symmetric(vertical=10),
                    bgcolor=Colors.BG_SIDEBAR,
                    border_radius=10,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Container(height=10),
                ft.Column(tarjetas, spacing=8),
            ], spacing=0),
        )

    def _turno_card(self, t: dict) -> ft.Container:
        cupo_ocupado = min(t["inscriptos"] / t["cupo_maximo"], 1.0) if t["cupo_maximo"] else 0
        color = t["color"]

        return ft.Container(
            content=ft.Column([
                ft.Text(t["nombre"], color=Colors.TEXT_PRIMARY, size=13,
                        weight=ft.FontWeight.BOLD),
                ft.Container(height=4),
                ft.Row([
                    ft.Icon(ft.Icons.SCHEDULE_ROUNDED, color=Colors.TEXT_MUTED, size=12),
                    ft.Text(f"{t['hora_inicio']} - {t['hora_fin']}",
                            color=Colors.TEXT_SECONDARY, size=11),
                ], spacing=4),
                ft.Container(height=4),
                ft.Row([
                    ft.Icon(ft.Icons.PERSON_OUTLINE_ROUNDED, color=Colors.TEXT_MUTED, size=12),
                    ft.Text(t["instructor"], color=Colors.TEXT_SECONDARY, size=11,
                            overflow=ft.TextOverflow.ELLIPSIS),
                ], spacing=4),
                ft.Container(height=6),
                ft.ProgressBar(
                    value=cupo_ocupado, bgcolor=Colors.BG_INPUT, color=color,
                    height=4, border_radius=2,
                ),
                ft.Container(height=4),
                ft.Text(f"{t['inscriptos']}/{t['cupo_maximo']} inscriptos",
                        color=Colors.TEXT_MUTED, size=10),
                ft.Container(height=8),
                ft.Row([
                    ft.Container(
                        content=ft.Text("Inscribir", color=color, size=11,
                                        weight=ft.FontWeight.W_500),
                        on_click=lambda e, x=t: self._open_inscribir(x),
                        bgcolor=f"{color}20", border_radius=6,
                        padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                    ),
                    ft.Container(expand=True),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE_ROUNDED, icon_color=Colors.TEXT_MUTED,
                                  icon_size=14, tooltip="Eliminar turno",
                                  on_click=lambda e, x=t: self._eliminar(x)),
                ]),
            ], spacing=0),
            bgcolor=Colors.BG_CARD,
            border_radius=10,
            border=ft.Border.all(1, Colors.BORDER),
            # Franja de color a la izquierda para identificar la clase de un vistazo
            padding=ft.Padding.only(left=10, top=10, right=8, bottom=8),
        )

    def _open_form(self, e=None):
        nombre_ref = ft.Ref[ft.TextField]()
        dia_ref = ft.Ref[ft.Dropdown]()
        hora_inicio_ref = ft.Ref[ft.TextField]()
        hora_fin_ref = ft.Ref[ft.TextField]()
        instructor_ref = ft.Ref[ft.Dropdown]()
        cupo_ref = ft.Ref[ft.TextField]()
        color_elegido = {"valor": COLORES_SUGERIDOS[0][1]}
        swatches_ref = ft.Ref[ft.Row]()

        personal = app_state.get_personal()
        opciones_instructor = [ft.dropdown.Option(key="", text="Sin asignar")] + [
            ft.dropdown.Option(key=p["dni"], text=p["nombre"]) for p in personal
        ]

        def _swatches() -> list:
            controles = []
            for nombre_color, hex_color in COLORES_SUGERIDOS:
                seleccionado = hex_color == color_elegido["valor"]
                controles.append(
                    ft.Container(
                        width=28, height=28, border_radius=14, bgcolor=hex_color,
                        border=ft.Border.all(2, Colors.TEXT_PRIMARY if seleccionado else "transparent"),
                        tooltip=nombre_color,
                        on_click=lambda e, c=hex_color: _elegir_color(c),
                    )
                )
            return controles

        def _elegir_color(hex_color):
            color_elegido["valor"] = hex_color
            swatches_ref.current.controls = _swatches()
            swatches_ref.current.update()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Nuevo Turno", color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=440,
                content=ft.Column([
                    input_field("Nombre de la clase", "Ej: Spinning",
                                icon=ft.Icons.FITNESS_CENTER_ROUNDED, ref=nombre_ref),
                    ft.Container(height=12),
                    ft.Dropdown(
                        ref=dia_ref,
                        label="Día de la semana",
                        options=[ft.dropdown.Option(d) for d in DIAS_SEMANA_ORDEN],
                        value="Lunes",
                        color=Colors.TEXT_PRIMARY, bgcolor=Colors.BG_INPUT,
                        border_color=Colors.BORDER, focused_border_color=Colors.ACCENT,
                        border_radius=10,
                    ),
                    ft.Container(height=12),
                    ft.Row([
                        input_field("Hora inicio", "08:00", width=190, ref=hora_inicio_ref),
                        ft.Container(width=8),
                        input_field("Hora fin", "09:00", width=190, ref=hora_fin_ref),
                    ]),
                    ft.Container(height=12),
                    ft.Dropdown(
                        ref=instructor_ref,
                        label="Instructor",
                        options=opciones_instructor,
                        value="",
                        color=Colors.TEXT_PRIMARY, bgcolor=Colors.BG_INPUT,
                        border_color=Colors.BORDER, focused_border_color=Colors.ACCENT,
                        border_radius=10,
                    ),
                    ft.Container(height=12),
                    input_field("Cupo máximo", "15", icon=ft.Icons.GROUP_ROUNDED, ref=cupo_ref),
                    ft.Container(height=12),
                    ft.Text("Color de la clase", color=Colors.TEXT_MUTED, size=12),
                    ft.Container(height=6),
                    ft.Row(ref=swatches_ref, controls=_swatches(), spacing=8),
                ], spacing=0, tight=True),
            ),
            actions=[
                ft.TextButton("Cancelar", style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                              on_click=lambda e: close_dialog(self.page, dlg)),
                ft.TextButton("Crear Turno", style=ft.ButtonStyle(color=Colors.ACCENT),
                              on_click=lambda e: self._save(
                                  dlg, nombre_ref, dia_ref, hora_inicio_ref, hora_fin_ref,
                                  instructor_ref, cupo_ref, color_elegido)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(self.page, dlg)

    def _save(self, dlg, nombre_ref, dia_ref, hora_inicio_ref, hora_fin_ref,
              instructor_ref, cupo_ref, color_elegido):
        nombre = (nombre_ref.current.value or "").strip()
        hora_inicio = (hora_inicio_ref.current.value or "").strip()
        hora_fin = (hora_fin_ref.current.value or "").strip()

        if not nombre or not hora_inicio or not hora_fin:
            show_snack(self.page, "Nombre, hora de inicio y hora de fin son obligatorios", Colors.DANGER)
            return

        dia_display = dia_ref.current.value
        instructor_dni = instructor_ref.current.value or None

        try:
            cupo = int(cupo_ref.current.value or 15)
        except ValueError:
            cupo = 15

        resultado = app_state.crear_turno(
            nombre, dia_display, hora_inicio, hora_fin,
            instructor_dni, cupo, color_elegido["valor"],
        )
        close_dialog(self.page, dlg)

        if resultado["ok"]:
            show_snack(self.page, "Turno creado correctamente ✓", Colors.SUCCESS)
            self._refrescar()
        else:
            show_snack(self.page, resultado["mensaje"] or "No se pudo crear el turno", Colors.DANGER)

    def _open_inscribir(self, turno: dict):
        socios = app_state.get_socios()
        if not socios:
            show_snack(self.page, "Todavía no hay socios cargados para inscribir.", Colors.WARNING)
            return

        socio_ref = ft.Ref[ft.Dropdown]()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Inscribir en '{turno['nombre']}'",
                          color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=380,
                content=ft.Column([
                    ft.Text(f"{turno['dia']} {turno['hora_inicio']}-{turno['hora_fin']} · "
                            f"{turno['inscriptos']}/{turno['cupo_maximo']} cupos ocupados",
                            color=Colors.TEXT_SECONDARY, size=12),
                    ft.Container(height=12),
                    ft.Dropdown(
                        ref=socio_ref,
                        label="Socio",
                        options=[ft.dropdown.Option(key=s["dni"], text=s["nombre"]) for s in socios],
                        color=Colors.TEXT_PRIMARY, bgcolor=Colors.BG_INPUT,
                        border_color=Colors.BORDER, focused_border_color=Colors.ACCENT,
                        border_radius=10,
                    ),
                ], spacing=0, tight=True),
            ),
            actions=[
                ft.TextButton("Cancelar", style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                              on_click=lambda e: close_dialog(self.page, dlg)),
                ft.TextButton("Inscribir", style=ft.ButtonStyle(color=Colors.ACCENT),
                              on_click=lambda e: self._confirmar_inscripcion(dlg, turno, socio_ref)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(self.page, dlg)

    def _confirmar_inscripcion(self, dlg, turno, socio_ref):
        if not socio_ref.current.value:
            show_snack(self.page, "Elegí un socio para inscribir.", Colors.DANGER)
            return

        resultado = app_state.inscribir_socio_turno(turno["id"], socio_ref.current.value)
        close_dialog(self.page, dlg)

        if resultado["ok"]:
            show_snack(self.page, resultado["mensaje"], Colors.SUCCESS)
            self._refrescar()
        else:
            show_snack(self.page, resultado["mensaje"] or "No se pudo inscribir al socio", Colors.DANGER)

    def _eliminar(self, turno: dict):
        resultado = app_state.eliminar_turno(turno["id"])
        if resultado["ok"]:
            show_snack(self.page, f"Turno '{turno['nombre']}' eliminado", Colors.DANGER)
            self._refrescar()
        else:
            show_snack(self.page, resultado["mensaje"] or "No se pudo eliminar el turno", Colors.DANGER)
