# =============================================================================
# views/login.py — Vista de inicio de sesión
# =============================================================================
# Espejo de LoginView.tsx de la PWA: una sola tarjeta centrada sobre el fondo
# base, con el nombre de la app arriba, los dos campos y el botón volt a lo
# ancho. Se reemplazó el diseño anterior (panel verde neón partido a la mitad)
# porque usaba una paleta propia —siete colores hardcodeados en este archivo—
# que no existía en ninguna otra pantalla ni en la web.

import flet as ft
from app.config import APP_NAME, Colors, Fonts, Radius
from app.state import app_state
from app.components.ui import input_field, primary_button


def _boton_ancho(btn: ft.Container) -> ft.Container:
    """Hace que un botón ocupe todo el ancho disponible de su fila."""
    btn.expand = True
    return btn


def show_login(page: ft.Page, router):
    """Reemplaza el contenido de la página con la pantalla de login."""

    username_ref = ft.Ref[ft.TextField]()
    password_ref = ft.Ref[ft.TextField]()
    error_ref    = ft.Ref[ft.Text]()

    def handle_login(e=None):
        u = (username_ref.current.value or "").strip().lower()
        p = (password_ref.current.value or "").strip()

        if not u or not p:
            error_ref.current.value   = "Completá usuario y contraseña."
            error_ref.current.visible = True
            error_ref.current.update()
            return

        ok, msg = app_state.login(u, p)

        if ok:
            error_ref.current.visible = False
            error_ref.current.update()
            page.on_keyboard_event = None
            _load_main_app(page, router)
        else:
            error_ref.current.value   = msg
            error_ref.current.visible = True
            error_ref.current.update()

    def on_key(e: ft.KeyboardEvent):
        if e.key == "Enter":
            handle_login()

    page.on_keyboard_event = on_key

    # ── Tarjeta de login ─────────────────────────────────────────────────────
    card = ft.Container(
        width=420,
        bgcolor=Colors.SURFACE_CARD,
        border=ft.Border.all(1, Colors.BORDER_IDLE),
        border_radius=Radius.MD,
        padding=ft.Padding.all(32),
        content=ft.Column([
            # Nombre de la app, centrado y en tipografía de título
            ft.Container(
                content=ft.Text(APP_NAME, color=Colors.TEXT_MAIN, size=34,
                                weight=ft.FontWeight.W_800,
                                font_family=Fonts.TITLE,
                                text_align=ft.TextAlign.CENTER),
                alignment=ft.Alignment.CENTER,
                padding=ft.Padding.only(bottom=24),
            ),

            input_field("Usuario", "nombre de usuario",
                        icon=ft.Icons.PERSON_OUTLINE_ROUNDED,
                        ref=username_ref),
            ft.Container(height=2),
            input_field("Contraseña", "••••••••", password=True,
                        icon=ft.Icons.LOCK_OUTLINE_ROUNDED,
                        ref=password_ref),

            # Renglón de error — ocupa lugar sólo cuando hay algo que decir
            ft.Text(ref=error_ref, color=Colors.STATUS_DANGER, size=13,
                    font_family=Fonts.BODY, visible=False, value=""),

            ft.Container(height=10),
            # El botón va dentro de un Row con expand para que ocupe todo el
            # ancho de la tarjeta (equivale al width="100%" de la web).
            ft.Row([_boton_ancho(primary_button("Ingresar", on_click=handle_login))]),

            # ── Credenciales de prueba ───────────────────────────────────────
            # Quedan a la vista mientras no exista la API. Cuando FastAPI esté
            # conectado esto se borra junto con _mock_users de state.py.
            ft.Container(
                content=ft.Column([
                    ft.Text("Credenciales de prueba", color=Colors.TEXT_MUTED,
                            size=12, font_family=Fonts.BODY),
                    ft.Text("admin / admin123   ·   trainer / train123",
                            color=Colors.TEXT_SECONDARY, size=12,
                            font_family=Fonts.MONO),
                ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                alignment=ft.Alignment.CENTER,
                padding=ft.Padding.only(top=24),
            ),
        ], spacing=8, tight=True),
    )

    page.controls.clear()
    page.add(
        ft.Container(
            expand=True,
            bgcolor=Colors.SURFACE_BASE,
            alignment=ft.Alignment.CENTER,
            content=card,
        )
    )
    page.update()


# =============================================================================
# CARGA DE LA APLICACIÓN PRINCIPAL
# =============================================================================

def _load_main_app(page: ft.Page, router):
    """
    Arma el shell (sidebar + contenido) después de un login exitoso y deja el
    Dashboard como pantalla inicial.
    """
    from app.config import Routes
    from app.views.dashboard import DashboardView
    from app.components.ui import build_sidebar

    content_ref = ft.Ref[ft.Container]()

    # La ruta activa se fija ANTES de construir el sidebar: así el ítem
    # Dashboard ya nace resaltado y el hover sabe cuál no debe apagar.
    app_state.current_route = Routes.DASHBOARD

    initial_content = DashboardView(page=page, router=router).build()

    content_container = ft.Container(
        ref=content_ref,
        content=initial_content,
        expand=True,
        bgcolor=Colors.SURFACE_BASE,
    )

    sidebar = build_sidebar(page, router, Routes.DASHBOARD)

    shell = ft.Row([sidebar, content_container], spacing=0, expand=True)

    page.controls.clear()
    page.add(ft.Container(content=shell, expand=True, bgcolor=Colors.SURFACE_BASE))
    page.update()

    router.setup(content_ref)
