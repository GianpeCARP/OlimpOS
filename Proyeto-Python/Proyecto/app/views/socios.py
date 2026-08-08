# =============================================================================
# views/socios.py — Gestión de socios del gimnasio (CON FILTRADO ACTIVO)
# =============================================================================

import flet as ft
from app.config import Colors                 # Paleta de colores del sistema
from app.state import app_state               # Estado global con los datos de socios
# Componentes reutilizables del sistema de diseño
from app.components.ui import (build_topbar, status_badge, primary_button,
                               input_field, show_snack, open_dialog,
                               close_dialog, confirm_dialog)


class SociosView:
    """
    Vista de gestión de socios con filtrado dinámico en tiempo real
    por términos de búsqueda (input) y por estado (Todos/Activos/Vencidos).
    """

    def __init__(self, page: ft.Page, router):
        self.sort_ascending = True # True = A-Z, False = Z-A
        self.page   = page
        self.router = router
        # Ref al campo de búsqueda — permite leer su valor al filtrar
        self.search_ref = ft.Ref[ft.TextField]()
        # Ref a la Column que contiene la tabla — permite reemplazar su contenido al filtrar
        self.table_ref  = ft.Ref[ft.Column]()
        
        # NUEVO: Guardamos el estado del filtro seleccionado ("Todos", "Activos", "Vencidos")
        self.current_filter = "Todos"
        # NUEVO: Ref para el contenedor de la barra de búsqueda que aloja los chips
        self.search_row_ref = ft.Ref[ft.Row]()

    def build(self) -> ft.Column:
        """Construye y retorna el árbol completo de controles de la vista."""
        socios = app_state.get_socios()  # Obtiene la lista completa de socios

        # Topbar con título, conteo de socios y botón "Nuevo Socio"
        topbar = build_topbar(
            "Socios",
            f"{len(socios)} socios registrados",
            actions=[
                primary_button("Nuevo Socio", ft.Icons.PERSON_ADD_ROUNDED,
                               on_click=self._open_form),  # Abre el modal de creación
            ]
        )

        # ── Barra de búsqueda + chips de filtro ──────────────────────────────
        # REFACTORIZADO: Metemos los chips adentro de un ft.Row con ref para poder redibujarlos
        search_bar = ft.Container(
            content=ft.Row(
                ref=self.search_row_ref,
                controls=[
                    # Campo de texto con búsqueda en tiempo real (on_change)
                    ft.TextField(
                        ref=self.search_ref,
                        hint_text="Buscar por nombre, plan...",
                        prefix_icon=ft.Icons.SEARCH_ROUNDED,
                        color=Colors.TEXT_PRIMARY,
                        hint_style=ft.TextStyle(color=Colors.TEXT_MUTED),
                        bgcolor=Colors.BG_INPUT,
                        border_color=Colors.BORDER,
                        focused_border_color=Colors.ACCENT,
                        border_radius=10,
                        expand=True,
                        height=44,
                        content_padding=ft.Padding.symmetric(horizontal=16, vertical=10),
                        on_change=self._on_search,  # Se llama en cada keystroke
                    ),
                    # Construimos los chips llamando a la nueva función interna
                    self._build_filter_chip("Todos"),
                    self._build_filter_chip("Activos"),
                    self._build_filter_chip("Vencidos"),
                    
                ], 
                spacing=10
            ),
            padding=ft.Padding.only(bottom=16),
        )

        # ── Tabla de socios ───────────────────────────────────────────────────
        table_content = self._build_table(socios)
        table_col = ft.Column(
            ref=self.table_ref,           # Ref para actualizar al filtrar
            controls=[table_content],     # La tabla es el único hijo inicial
        )

        # ── Ensamblado final ──────────────────────────────────────────────────
        body = ft.Column([
            topbar,
            ft.Container(
                content=ft.Column([
                    search_bar,
                    # Container con borde que envuelve la tabla
                    ft.Container(
                        content=table_col,
                        bgcolor=Colors.BG_CARD,
                        border_radius=14,
                        border=ft.Border.all(1, Colors.BORDER),
                        padding=0,
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    ),
                ], spacing=0, scroll=ft.ScrollMode.AUTO, expand=True),
                padding=ft.Padding.all(24),
                expand=True,
            ),
        ], spacing=0, expand=True)

        return body

    def _build_filter_chip(self, label: str) -> ft.Container:
        """
        NUEVO MÉTODO: Construye un chip de filtro interactivo.
        Determina sus colores basándose en si coincide con el filtro activo global.
        """
        # Chequeamos si este chip en particular es el seleccionado actualmente
        is_active = self.current_filter == label

        def on_chip_click(e):
            # 1. Cambiamos el estado global del filtro al que se clickeó
            self.current_filter = label
            
            # 2. Re-renderizamos la fila de búsqueda para que cambien los colores de los chips
            # Reemplazamos los controles manteniendo el buscador intacto en la posición 0
            search_input = self.search_row_ref.current.controls[0]
            self.search_row_ref.current.controls = [
                search_input,
                self._build_filter_chip("Todos"),
                self._build_filter_chip("Activos"),
                self._build_filter_chip("Vencidos")
            ]
            self.search_row_ref.current.update()

            # 3. Filtramos los datos de la tabla de socios
            self._update_table()

        return ft.Container(
            content=ft.Text(
                label,
                color=Colors.ACCENT if is_active else Colors.TEXT_SECONDARY,
                size=13,
                weight=ft.FontWeight.W_600 if is_active else ft.FontWeight.NORMAL
            ),
            bgcolor=Colors.ACCENT_GLOW if is_active else Colors.BG_INPUT,
            border_radius=20,
            padding=ft.Padding.symmetric(horizontal=14, vertical=8),
            border=ft.Border.all(1, Colors.ACCENT if is_active else Colors.BORDER),
            on_click=on_chip_click, # <-- ACÁ ESTÁ LA MAGIA, ahora responde al click
            
        )

    def _update_table(self):
        """
        Lógica central: filtra por texto, filtra por estado y ordena alfabéticamente.
        """
        # 1. Obtener datos y query de búsqueda
        query = self.search_ref.current.value.lower() if self.search_ref.current else ""
        socios = app_state.get_socios()

        # 2. Aplicar filtros (Búsqueda + Estado)
        filtered = []
        for s in socios:
            matches_search = query in s["nombre"].lower() or query in s["plan"].lower()
            
            matches_status = False
            if self.current_filter == "Todos":
                matches_status = True
            elif self.current_filter == "Activos" and s["estado"].lower() == "activo":
                matches_status = True
            elif self.current_filter == "Vencidos" and s["estado"].lower() == "vencido":
                matches_status = True

            if matches_search and matches_status:
                filtered.append(s)

        # 3. Aplicar Ordenamiento (Aquí usamos la variable que creamos en el init)
        # sort_ascending es True (A-Z) o False (Z-A)
        filtered.sort(key=lambda x: x["nombre"].lower(), reverse=not self.sort_ascending)

        # 4. Actualizar la interfaz
        self.table_ref.current.controls = [self._build_table(filtered)]
        self.table_ref.current.update()

    def _on_search(self, e):
        """Callback de búsqueda en tiempo real (keystroke). Redirige al filtro central."""
        self._update_table()

    def _toggle_sort(self, e):
        # Alternar el sentido del orden
        self.sort_ascending = not self.sort_ascending
        
        # Refrescar la tabla aplicando el nuevo orden
        self._update_table()

    def _build_table(self, socios: list) -> ft.Column:
        header = ft.Container(
            content=ft.Row([
                
                ft.TextButton(
                    content=ft.Row([
                        ft.Text("Nombre", color=Colors.SUCCESS, size=12, weight=ft.FontWeight.W_600),
                        ft.Icon(ft.Icons.SORT, size=14, color=Colors.SUCCESS)
                    ]),
                    on_click=self._toggle_sort, 
                    expand=3,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5))
                ),
                ft.Text("Plan",    color=Colors.SUCCESS, size=12, weight=ft.FontWeight.W_600, expand=2),
                ft.Text("Estado",  color=Colors.SUCCESS, size=12, weight=ft.FontWeight.W_600, expand=2),
                ft.Text("Vence",   color=Colors.SUCCESS, size=12, weight=ft.FontWeight.W_600, expand=2),
                ft.Text("Acciones", color=Colors.SUCCESS, size=12, weight=ft.FontWeight.W_600, expand=2),
            ]),
            padding=ft.Padding.symmetric(horizontal=20, vertical=14),
            bgcolor=Colors.BG_SIDEBAR,
        )
        

        rows = [header]
        for s in socios:
            rows.append(self._table_row(s))

        return ft.Column(rows, spacing=0)

    def _table_row(self, s: dict) -> ft.Container:
        """Construye una fila de la tabla para un socio específico."""
        initial = s["nombre"][0].upper()

        def on_hover(e: ft.HoverEvent):
            e.control.bgcolor = Colors.BG_INPUT if e.data == "true" else ft.Colors.TRANSPARENT
            e.control.update()

        return ft.Container(
            content=ft.Row([
                ft.Row([
                    ft.Container(
                        content=ft.Text(initial, color=Colors.SURFACE_BASE, size=13, weight=ft.FontWeight.BOLD),
                        width=32, height=32, border_radius=16,
                        bgcolor=Colors.ACCENT, alignment=ft.Alignment.CENTER,
                    ),
                    ft.Text(s["nombre"], color=Colors.TEXT_PRIMARY, size=14),
                ], spacing=10, expand=3),
                ft.Container(content=ft.Text(s["plan"], color=Colors.TEXT_SECONDARY, size=13), expand=2),
                ft.Container(content=status_badge(s["estado"]), expand=2, alignment=ft.Alignment.CENTER_LEFT),
                ft.Text(s["vence"], color=Colors.TEXT_SECONDARY, size=13, expand=2),
                ft.Row([
                    ft.IconButton(ft.Icons.EDIT_ROUNDED, icon_color=Colors.INFO, icon_size=18, tooltip="Editar",
                                  on_click=lambda e, x=s: self._open_form(e, x)),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE_ROUNDED, icon_color=Colors.DANGER, icon_size=18, tooltip="Eliminar",
                                  on_click=lambda e, x=s: self._confirm_delete(x)),
                ], expand=2),
            ]),
            padding=ft.Padding.symmetric(horizontal=20, vertical=12),
            border=ft.Border.only(bottom=ft.BorderSide(1, Colors.BORDER)),
            on_hover=on_hover,
            animate=ft.Animation(120),
        )

    def _open_form(self, e=None, socio: dict = None):
        """Abre el modal para crear o editar un socio."""
        is_edit    = socio is not None
        nombre_ref = ft.Ref[ft.TextField]()
        plan_ref   = ft.Ref[ft.Dropdown]()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Editar Socio" if is_edit else "Nuevo Socio", color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=420,
                content=ft.Column([
                    input_field("Nombre completo", "Ej: Juan García", icon=ft.Icons.PERSON_OUTLINE_ROUNDED, ref=nombre_ref),
                    ft.Container(height=12),
                    ft.Dropdown(
                        ref=plan_ref,
                        label="Plan",
                        options=[
                            ft.dropdown.Option("Básico"),
                            ft.dropdown.Option("Premium"),
                            ft.dropdown.Option("Anual"),
                        ],
                        value=socio["plan"] if is_edit else "Básico",
                        color=Colors.TEXT_PRIMARY,
                        bgcolor=Colors.BG_INPUT,
                        border_color=Colors.BORDER,
                        focused_border_color=Colors.ACCENT,
                        border_radius=10,
                    ),
                    ft.Container(height=12),
                    input_field("Email", "ejemplo@mail.com", icon=ft.Icons.EMAIL_OUTLINED),
                    ft.Container(height=12),
                    input_field("Teléfono", "+54 9 000 0000000", icon=ft.Icons.PHONE_OUTLINED),
                ], spacing=0, tight=True),
            ),
            actions=[
                ft.TextButton("Cancelar", style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY), on_click=lambda e: close_dialog(self.page, dlg)),
                ft.TextButton("Guardar", style=ft.ButtonStyle(color=Colors.ACCENT), on_click=lambda e: self._save_socio(dlg)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        if is_edit and nombre_ref.current:
            nombre_ref.current.value = socio["nombre"]

        open_dialog(self.page, dlg)

    def _save_socio(self, dlg):
        close_dialog(self.page, dlg)
        show_snack(self.page, "Socio guardado correctamente ✓", Colors.SUCCESS)

    def _confirm_delete(self, socio: dict):
        dlg = confirm_dialog(
            self.page,
            "Eliminar Socio",
            f"¿Estás seguro de eliminar a {socio['nombre']}? Esta acción no se puede deshacer.",
            on_confirm=lambda: show_snack(self.page, f"{socio['nombre']} eliminado", Colors.DANGER),
        )
        open_dialog(self.page, dlg)