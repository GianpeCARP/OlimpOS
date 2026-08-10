# =============================================================================
# views/login.py — Vista de inicio de sesión
# =============================================================================
# Se divide en dos paneles (izquierdo decorativo / derecho formulario) igual
# que antes, pero ahora el login llama a la API real (app_state.login) y
# contempla el caso de "primer ingreso": si el backend indica
# debe_cambiar_password=True, se muestra una segunda pantalla que obliga
# a definir una contraseña propia antes de entrar al sistema.

import flet as ft
from app.config import Colors, APP_NAME
from app.state import app_state
from app.components.ui import input_field, show_snack


def show_login(page: ft.Page, router):
    """
    Reemplaza el contenido de la página con la vista de login.
    """
    username_ref = ft.Ref[ft.TextField]()  # Campo de email
    password_ref = ft.Ref[ft.TextField]()  # Campo de contraseña
    error_ref    = ft.Ref[ft.Text]()       # Texto de error (oculto por defecto)

    def handle_login(e=None):
        """
        Lee los campos, valida que no estén vacíos y llama a
        app_state.login(). Según el resultado:
          - credenciales inválidas / error de red -> muestra el error
          - debe_cambiar_password=True -> va a la pantalla de cambio de clave
          - login exitoso -> carga el shell principal (dashboard)
        """
        email = (username_ref.current.value or "").strip()
        password = password_ref.current.value or ""

        if not email or not password:
            error_ref.current.value = "Completá todos los campos"
            error_ref.current.visible = True
            error_ref.current.update()
            return

        resultado = app_state.login(email, password)

        if not resultado["ok"]:
            error_ref.current.value = resultado["mensaje"]
            error_ref.current.visible = True
            error_ref.current.update()
            return

        error_ref.current.visible = False
        error_ref.current.update()

        if resultado["requiere_cambio"]:
            show_cambiar_password(page, router)
        else:
            _load_main_app(page, router)

    def on_key(e: ft.KeyboardEvent):
        """Permite enviar el formulario presionando Enter."""
        if e.key == "Enter":
            handle_login()

    page.on_keyboard_event = on_key

    # ── Panel izquierdo — decorativo ──────────────────────────────────────────
    left_panel = ft.Container(
        expand=2,
        bgcolor=Colors.BG_SIDEBAR,
        content=ft.Stack([
            ft.Container(
                content=ft.Column([
                    ft.Container(
                        width=300, height=300, border_radius=150,
                        bgcolor=Colors.ACCENT_GLOW,
                        margin=ft.Margin.only(top=-80, left=-80),
                    ),
                ]),
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("Olimp", color=Colors.ACCENT, size=96,
                            weight=ft.FontWeight.BOLD, font_family="Bebas Neue",
                            opacity=0.08),
                    ft.Text("OS", color=Colors.TEXT_PRIMARY, size=96,
                            weight=ft.FontWeight.BOLD, font_family="Bebas Neue",
                            opacity=0.04),
                ], spacing=-20),
                alignment=ft.Alignment.CENTER,
                expand=True,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Container(
                        content=ft.Text("O", color=Colors.BG_DARK, size=32,
                                        weight=ft.FontWeight.BOLD),
                        width=60, height=60, border_radius=16,
                        bgcolor=Colors.ACCENT,
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Container(height=24),
                    ft.Text(APP_NAME, color=Colors.TEXT_PRIMARY, size=48,
                            weight=ft.FontWeight.BOLD, font_family="Bebas Neue"),
                    ft.Text("Sistema de Gestión\nIntegral para Gimnasios",
                            color=Colors.TEXT_SECONDARY, size=16,
                            text_align=ft.TextAlign.LEFT),
                    ft.Container(height=32),
                    _feature_row(ft.Icons.GROUP_ROUNDED, "Gestión completa de socios"),
                    ft.Container(height=12),
                    _feature_row(ft.Icons.FITNESS_CENTER_ROUNDED, "Rutinas y seguimiento"),
                    ft.Container(height=12),
                    _feature_row(ft.Icons.RESTAURANT_MENU_ROUNDED, "Planes nutricionales"),
                    ft.Container(height=12),
                    _feature_row(ft.Icons.ANALYTICS_ROUNDED, "Dashboard con estadísticas"),
                ], horizontal_alignment=ft.CrossAxisAlignment.START),
                padding=ft.Padding.all(52),
                alignment=ft.Alignment.CENTER_LEFT,
                expand=True,
            ),
        ]),
    )

    # ── Panel derecho — formulario de login ───────────────────────────────────
    login_form = ft.Container(
        expand=1,
        bgcolor=Colors.BG_DARK,
        content=ft.Column([
            ft.Container(expand=True),
            ft.Container(
                content=ft.Column([
                    ft.Text("Bienvenido de nuevo", color=Colors.TEXT_PRIMARY,
                            size=28, weight=ft.FontWeight.BOLD),
                    ft.Text("Ingresá tus credenciales para continuar",
                            color=Colors.TEXT_SECONDARY, size=14),
                    ft.Container(height=32),

                    input_field("Email", "tu_email@gimnasio.com",
                                icon=ft.Icons.PERSON_OUTLINE_ROUNDED,
                                ref=username_ref),
                    ft.Container(height=16),
                    input_field("Contraseña", "••••••••", password=True,
                                icon=ft.Icons.LOCK_OUTLINE_ROUNDED,
                                ref=password_ref),
                    ft.Container(height=8),

                    ft.Text(ref=error_ref, color=Colors.DANGER, size=12,
                            visible=False, value=""),
                    ft.Container(height=12),

                    ft.Container(
                        content=ft.Row([
                            ft.Text("Iniciar sesión", color=Colors.WHITE, size=15,
                                    weight=ft.FontWeight.W_600),
                        ], alignment=ft.MainAxisAlignment.CENTER),
                        bgcolor=Colors.ACCENT,
                        border_radius=10,
                        height=48,
                        on_click=handle_login,
                        animate=ft.Animation(150, ft.AnimationCurve.EASE_IN_OUT),
                    ),

                    ft.Container(height=24),
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.INFO_OUTLINE_ROUNDED, color=Colors.TEXT_MUTED, size=14),
                            ft.Text(
                                "Usá las credenciales que te dio el administrador del sistema.",
                                color=Colors.TEXT_SECONDARY, size=12,
                            ),
                        ], spacing=8),
                        bgcolor=Colors.BG_INPUT,
                        border_radius=8,
                        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                    ),
                ], spacing=0,
                   horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
                width=380,
                padding=ft.Padding.all(40),
                bgcolor=Colors.BG_CARD,
                border_radius=20,
                border=ft.Border.all(1, Colors.BORDER),
            ),
            ft.Container(expand=True),
            ft.Text(f"© 2025 {APP_NAME} — Todos los derechos reservados",
                    color=Colors.TEXT_MUTED, size=11,
                    text_align=ft.TextAlign.CENTER),
            ft.Container(height=24),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.Padding.symmetric(horizontal=40),
    )

    page.controls.clear()
    page.add(
        ft.Container(
            content=ft.Row([left_panel, login_form], spacing=0, expand=True),
            expand=True,
            bgcolor=Colors.BG_DARK,
        )
    )
    page.update()


def show_cambiar_password(page: ft.Page, router):
    """
    Pantalla de cambio de contraseña obligatorio (primer ingreso, o
    después de un reseteo hecho por un administrador). Usa
    app_state.email_pendiente_cambio, que quedó guardado por el login.
    """
    actual_ref = ft.Ref[ft.TextField]()
    nueva_ref = ft.Ref[ft.TextField]()
    confirmar_ref = ft.Ref[ft.TextField]()
    error_ref = ft.Ref[ft.Text]()

    def al_guardar(e=None):
        actual = actual_ref.current.value or ""
        nueva = nueva_ref.current.value or ""
        confirmar = confirmar_ref.current.value or ""

        if nueva != confirmar:
            error_ref.current.value = "Las contraseñas no coinciden."
            error_ref.current.visible = True
            error_ref.current.update()
            return

        if len(nueva) < 6:
            error_ref.current.value = "La nueva contraseña debe tener al menos 6 caracteres."
            error_ref.current.visible = True
            error_ref.current.update()
            return

        resultado = app_state.cambiar_password(actual, nueva)

        if not resultado["ok"]:
            error_ref.current.value = resultado["mensaje"]
            error_ref.current.visible = True
            error_ref.current.update()
            return

        show_login(page, router)

    card = ft.Container(
        content=ft.Column([
            ft.Text("Cambio de contraseña obligatorio", color=Colors.TEXT_PRIMARY,
                    size=22, weight=ft.FontWeight.BOLD),
            ft.Text("Es tu primer ingreso (o te resetearon la clave). "
                    "Definí una contraseña propia para continuar.",
                    color=Colors.TEXT_SECONDARY, size=13),
            ft.Container(height=24),
            input_field("Contraseña actual (temporal)", "", password=True,
                        icon=ft.Icons.LOCK_CLOCK_ROUNDED, ref=actual_ref),
            ft.Container(height=16),
            input_field("Nueva contraseña", "", password=True,
                        icon=ft.Icons.LOCK_OUTLINE_ROUNDED, ref=nueva_ref),
            ft.Container(height=16),
            input_field("Confirmar contraseña", "", password=True,
                        icon=ft.Icons.LOCK_OUTLINE_ROUNDED, ref=confirmar_ref),
            ft.Container(height=8),
            ft.Text(ref=error_ref, color=Colors.DANGER, size=12, visible=False, value=""),
            ft.Container(height=16),
            ft.Container(
                content=ft.Row([
                    ft.Text("Guardar y continuar", color=Colors.WHITE, size=15,
                            weight=ft.FontWeight.W_600),
                ], alignment=ft.MainAxisAlignment.CENTER),
                bgcolor=Colors.ACCENT,
                border_radius=10,
                height=48,
                on_click=al_guardar,
            ),
        ], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
        width=400,
        padding=ft.Padding.all(40),
        bgcolor=Colors.BG_CARD,
        border_radius=20,
        border=ft.Border.all(1, Colors.BORDER),
    )

    page.controls.clear()
    page.add(
        ft.Container(
            content=ft.Column([card], alignment=ft.MainAxisAlignment.CENTER,
                               horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            expand=True,
            bgcolor=Colors.BG_DARK,
            alignment=ft.Alignment.CENTER,
        )
    )
    page.update()


def _load_main_app(page: ft.Page, router):
    """
    Carga la estructura principal de la aplicación tras el login exitoso.
    """
    from app.config import Routes
    from app.components.layout import build_main_layout
    from app.views.dashboard import DashboardView

    content_ref = ft.Ref[ft.Container]()

    dashboard = DashboardView(page=page, router=router)
    initial_content = dashboard.build()

    content_container = ft.Container(
        ref=content_ref,
        content=initial_content,
        expand=True,
        bgcolor=Colors.BG_DARK,
    )

    from app.components.ui import build_sidebar
    sidebar = build_sidebar(page, router, Routes.DASHBOARD)

    shell = ft.Row([sidebar, content_container], spacing=0, expand=True)

    router.setup(content_ref)

    page.controls.clear()
    page.add(ft.Container(content=shell, expand=True))
    page.update()

    app_state.current_route = Routes.DASHBOARD


def _feature_row(icon: str, text: str) -> ft.Row:
    from app.config import Colors
    return ft.Row([
        ft.Container(
            content=ft.Icon(icon, color=Colors.ACCENT, size=18),
            width=36, height=36, border_radius=10,
            bgcolor=Colors.ACCENT_GLOW,
            alignment=ft.Alignment.CENTER,
        ),
        ft.Text(text, color=Colors.TEXT_SECONDARY, size=14),
    ], spacing=12)
