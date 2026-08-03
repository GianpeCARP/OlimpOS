# =============================================================================
# views/login.py — Vista de inicio de sesión (Diseño Tarjeta Curva - Full Green)
# =============================================================================

import flet as ft
from app.config import APP_NAME           
from app.state import app_state           
from app.components.ui import input_field, show_snack  

# ── PALETA DE VERDES DIRECTO ACÁ ─────────────────────────────────────────────
C_BG_PAGE = "#040F09"       # Fondo de pantalla: Verde casi negro muy profundo
C_CARD_BG = "#0A1A10"       # Fondo del panel derecho (Formulario)
C_LEFT_BG = "#00D06A"       # Panel izquierdo: Verde neón/vibrante puro
C_TEXT_LEFT = "#02301A"     # Texto oscuro sobre el panel verde vibrante
C_TEXT_RIGHT = "#E8F5E9"    # Texto claro sobre el panel oscuro
C_TEXT_MUTED = "#4A785B"    # Texto secundario/apagado
C_ACCENT = "#00FF7F"        # Detalles y botones: Spring Green muy llamativo


def show_login(page: ft.Page, router):
    """
    Reemplaza el contenido de la página con la vista de login.
    Diseño de Tarjeta Central imponente.
    """

    # ── Referencias (Refs) INTACTAS ───────────────────────────────────────────
    username_ref = ft.Ref[ft.TextField]()  
    password_ref = ft.Ref[ft.TextField]()  
    error_ref    = ft.Ref[ft.Text]()       
    btn_ref      = ft.Ref[ft.Container]()  

    def handle_login(e=None):
        u = username_ref.current.value.strip().lower()
        p = password_ref.current.value.strip()

        if not u or not p:
            error_ref.current.value   = "Es necesario completar todos los campos."
            error_ref.current.visible = True
            error_ref.current.update()  
            return

        ok, msg = app_state.login(u, p)

        if ok:
            error_ref.current.visible = False  
            error_ref.current.update()
            page.on_keyboard_event=None
            _load_main_app(page, router)        
        else:
            error_ref.current.value   = msg
            error_ref.current.visible = True
            error_ref.current.update()

    def on_key(e: ft.KeyboardEvent):
        if e.key == "Enter":
            handle_login()

    page.on_keyboard_event = on_key

    # ── Panel Izquierdo 
    left_panel = ft.Container(
        expand=4,  # Proporción 44% ya que 9/4
        bgcolor=C_LEFT_BG, 
        border_radius=ft.border_radius.only(top_left=30, bottom_left=30, top_right=150, bottom_right=0),
        padding=ft.padding.all(60),
        content=ft.Column(
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Container(
                    content=ft.Image(
                        src="logo-removebg-preview.png",     
                        width=100,                
                        height=100,
                        fit="contain", 
                        color=C_TEXT_LEFT, 
                    ),
                    margin=ft.margin.only(bottom=20),
                ),
                # Título de alto impacto
                ft.Text(
                    APP_NAME, 
                    color=C_TEXT_LEFT, 
                    size=72,
                    weight=ft.FontWeight.W_900, 
                    font_family="Bebas Neue",
                ),
                ft.Text(
                    "Sistema de Gestión\nIntegral para Gimnasios.",
                    color=C_TEXT_LEFT, 
                    size=26,
                    weight=ft.FontWeight.W_700,
                    font_family="Inter",
                ),
                ft.Container(height=40),
                
                # Características con íconos restauradas
                _feature_row(ft.Icons.SHIELD_OUTLINED, "Infraestructura de máxima seguridad"),
                ft.Container(height=20),
                _feature_row(ft.Icons.AUTO_GRAPH, "Métricas y rendimiento en tiempo real"),
                ft.Container(height=20),
                _feature_row(ft.Icons.FITNESS_CENTER_ROUNDED, "Gestión integral de equipamiento"),

                ft.Container(expand=True), 
                ft.Text("©2026 OlimpOS - All rights deserved", color=C_TEXT_LEFT, size=13, weight=ft.FontWeight.W_200),
            ]
        ),
    )

    # ── Panel Derecho - Formulario 
    right_panel = ft.Container(
        expand=5, # Proporción 56%
        padding=ft.padding.only(left=100, right=100, top=60, bottom=60),
        content=ft.Column(
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Text(
                    "Bienvenido de nuevo.", 
                    color=C_TEXT_RIGHT,
                    size=36, 
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Text(
                    "Ingresá tus credenciales para comenzar.",
                    color=C_TEXT_MUTED, 
                    size=16
                ),
                ft.Container(height=50),

                input_field(
                    "Usuario", 
                    "nombre_usuario",
                    icon=ft.Icons.PERSON_OUTLINE_ROUNDED,
                    ref=username_ref
                ),
                ft.Container(height=5),
                input_field(
                    "Contraseña", 
                    "••••••••", 
                    password=True,
                    icon=ft.Icons.LOCK_OUTLINE_ROUNDED,
                    ref=password_ref
                ),
                ft.Container(height=2),

                # Texto de error 
                ft.Text(
                    ref=error_ref, 
                    color=ft.Colors.RED_400, 
                    size=13,
                    visible=False, 
                    value="",
                ),
                ft.Container(height=40),

                # Botón 
                ft.Container(
                    ref=btn_ref,
                    content=ft.Row([
                        ft.Text("Iniciar sesión", color=C_CARD_BG, size=18,
                                weight=ft.FontWeight.W_800, font_family="Inter",)
                    ], alignment=ft.MainAxisAlignment.CENTER),
                    bgcolor=C_ACCENT,
                    border_radius=12,
                    height=55,
                    on_click=handle_login,
                    animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
                ),

                ft.Container(height=40),
                
                # Demo text
                ft.Row([
                    ft.Text("Demo:", color=C_TEXT_MUTED, size=13),
                    ft.Text("admin / admin123 - trainer / train123", color=C_TEXT_MUTED, size=13, weight=ft.FontWeight.BOLD),
                ], alignment=ft.MainAxisAlignment.CENTER)
            ]
        )
    )

    # ── Tarjeta Central Flotante (AMPLIADA) ──────────────────────────────────
    main_card = ft.Container(
        width=1300,  
        height=700,  
        border_radius=30,
        bgcolor=C_CARD_BG,
        shadow=ft.BoxShadow(
            spread_radius=0, blur_radius=60,
            color=ft.Colors.with_opacity(0.20, C_ACCENT), 
            offset=ft.Offset(0, 15)
        ),
        content=ft.Row(
            spacing=0,
            expand=True,
            controls=[left_panel, right_panel]
        )
    )

    # ── Renderizado en la página ─────────────────────────────────────────────
    page.controls.clear()  
    page.add(
        ft.Container(
            expand=True,
            bgcolor=C_BG_PAGE, 
            alignment=ft.Alignment.CENTER, 
            content=main_card
        )
    )
    page.update()  


# =========================================================================
# LÓGICA DE CARGA ORIGINAL INTACTA Y FUNCIÓN DE FEATURES
# =========================================================================

def _feature_row(icon: str, text: str) -> ft.Row:
    """
    Fila decorativa adaptada a la paleta del panel izquierdo.
    """
    return ft.Row(
        spacing=16,
        controls=[
            ft.Container(
                content=ft.Icon(icon, color=C_TEXT_LEFT, size=22),
                width=45, height=45, 
                border_radius=14,
                bgcolor=ft.Colors.with_opacity(0.12, C_TEXT_LEFT), # Fondo oscuro semi-transparente
                alignment=ft.Alignment.CENTER,
            ),
            ft.Text(text, color=C_TEXT_LEFT, size=15, weight=ft.FontWeight.W_600),
        ]
    )

def _load_main_app(page: ft.Page, router):
    """
    Carga la estructura principal de la aplicación tras el login exitoso.
    """
    from app.config import Routes
    from app.components.layout import build_main_layout
    from app.views.dashboard import DashboardView

    content_ref = ft.Ref[ft.Container]()
    sidebar_ref = ft.Ref[ft.Container]()

    dashboard        = DashboardView(page=page, router=router)
    initial_content  = dashboard.build()

    content_container = ft.Container(
        ref=content_ref,
        content=initial_content,
        expand=True,
        bgcolor=C_CARD_BG, 
    )

    from app.components.ui import build_sidebar
    sidebar_original = build_sidebar(page, router, Routes.DASHBOARD)

    sidebar_container = ft.Container(
        ref=sidebar_ref,
        content=sidebar_original,
    )

    shell = ft.Row([sidebar_container, content_container], spacing=0, expand=True)

    page.controls.clear()
    page.add(ft.Container(content=shell, expand=True))
    page.update() 

    router.setup(content_ref)
    
    app_state.current_route = Routes.DASHBOARD