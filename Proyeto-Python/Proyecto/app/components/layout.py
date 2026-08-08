# =============================================================================
# components/layout.py — Shell principal (sidebar + contenido)
# =============================================================================

import flet as ft
from app.config import Colors
from app.components.ui import build_sidebar


def build_main_layout(page: ft.Page, router, active_route: str,
                      content: ft.Control) -> ft.Row:
    """
    Arma el caparazón de la app: sidebar fijo a la izquierda y el área de
    contenido que cambia con la navegación.

    Equivale a AppLayout.tsx de la PWA (`<Sidebar />` + `<main>` con overflow).
    """

    content_ref = ft.Ref[ft.Container]()

    # El router guarda esta referencia para poder reemplazar sólo el contenido
    # al navegar, sin reconstruir el sidebar.
    router.setup(content_ref)

    sidebar = build_sidebar(page, router, active_route)

    content_area = ft.Container(
        ref=content_ref,
        content=content,
        expand=True,
        bgcolor=Colors.SURFACE_BASE,
    )

    return ft.Row([sidebar, content_area], spacing=0, expand=True)
