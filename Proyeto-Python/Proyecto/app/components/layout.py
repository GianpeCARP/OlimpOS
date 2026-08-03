# =============================================================================
# components/layout.py — Shell principal (sidebar + contenido)
# =============================================================================

import flet as ft
from app.config import Colors
from app.components.ui import build_sidebar


def build_main_layout(page: ft.Page, router, active_route: str,
                      content: ft.Control) -> ft.Row:
    """
    Construye el caparazón estructural del sistema combinando la barra de
    navegación lateral y el lienzo dinámico de información.
    """

    # ── Referencia al área de contenido ──────────────────────────────────────
    content_ref = ft.Ref[ft.Container]()

    # Registro de persistencia dentro del gestor de rutas
    router.setup(content_ref)

    # ── Sidebar Estática ──────────────────────────────────────────────────────
    sidebar = build_sidebar(page, router, active_route)

    # ── Área de contenido elástica ────────────────────────────────────────────
    content_area = ft.Container(
        ref=content_ref,
        content=content,
        expand=True,
        bgcolor=Colors.BG_DARK,
    )

    # ── Ensamblado responsivo ─────────────────────────────────────────────────
    return ft.Row([sidebar, content_area], spacing=0, expand=True)