# =============================================================================
# components/layout.py — Shell principal (sidebar + contenido)
# =============================================================================
# Este archivo define la función `build_main_layout` que arma el "shell"
# visual de la aplicación: el sidebar fijo a la izquierda y el área de
# contenido expandible a la derecha.
# NOTA: en el flujo actual, esta función existe como utilidad pero el shell
# se construye directamente en login.py (_load_main_app) para mantener
# referencias locales al content_ref. Ambos enfoques son equivalentes.

import flet as ft
from app.config import Colors, SIDEBAR_WIDTH    # Colores y ancho del sidebar
from app.components.ui import build_sidebar      # Función que construye el sidebar


def build_main_layout(page: ft.Page, router, active_route: str,
                      content: ft.Control) -> ft.Row:
    """
    Construye el layout principal de la aplicación tras el login exitoso.

    Parámetros:
        page:         Objeto Page de Flet — referencia a la ventana
        router:       Instancia del Router — necesaria para el sidebar y el contenido
        active_route: Ruta activa para resaltar el ítem correcto del menú
        content:      El widget de la vista inicial a mostrar (generalmente Dashboard)

    Retorna:
        Un ft.Row con dos hijos:
          - sidebar (ancho fijo de 240 px)
          - content_area (expandible, ocupa el resto de la ventana)

    Flujo interno:
        1. Crea un ft.Ref[ft.Container] para poder actualizar el contenido después
        2. Llama a router.setup() para registrar esa referencia en el router
        3. Construye el sidebar pasando la ruta activa
        4. Envuelve `content` en un Container referenciado
        5. Retorna el Row con sidebar + contenedor
    """

    # ── Referencia al área de contenido ──────────────────────────────────────
    # ft.Ref permite obtener el control real (current) después de que Flet lo renderice.
    # El router usa esta referencia en _render_view() para reemplazar el contenido
    # al navegar a otra sección sin reconstruir toda la página.
    content_ref = ft.Ref[ft.Container]()

    # Registra la referencia en el router para que pueda actualizar el contenido
    # al llamar a router.navigate().
    router.setup(content_ref)

    # ── Sidebar ───────────────────────────────────────────────────────────────
    # Construye el panel de navegación lateral con el ítem activo resaltado.
    sidebar = build_sidebar(page, router, active_route)

    # ── Área de contenido ─────────────────────────────────────────────────────
    # Container expandible que contendrá la vista activa.
    # Al navegar, el router reemplaza su `.content` con la nueva vista.
    content_area = ft.Container(
        ref=content_ref,          # Registra la referencia para acceso posterior
        content=content,          # Vista inicial (Dashboard al iniciar)
        expand=True,              # Ocupa todo el espacio horizontal disponible
        bgcolor=Colors.BG_DARK,   # Fondo oscuro estándar del área de contenido
    )

    # ── Ensamblado final ──────────────────────────────────────────────────────
    # Row horizontal: sidebar fijo a la izquierda + contenido expandible a la derecha.
    # spacing=0 elimina cualquier separación entre los dos paneles.
    return ft.Row([sidebar, content_area], spacing=0, expand=True)
