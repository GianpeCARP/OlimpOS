# =============================================================================
# main.py — Punto de entrada del sistema OlimpOS
# =============================================================================

import flet as ft

from app.config import (APP_NAME, Colors, WINDOW_WIDTH, WINDOW_HEIGHT,
                        WINDOW_MIN_W, WINDOW_MIN_H)
from app.router import init_router
from app.views.login import show_login


def main(page: ft.Page):
    """
    Configura el lienzo inicial del sistema operativo e inicia el flujo
    de autenticación con la estética Apple Dark.
    """

    #  Configuración de la ventana 
    page.title             = APP_NAME
    page.theme_mode        = ft.ThemeMode.DARK
    page.bgcolor          = Colors.BG_DARK
    page.window.width     = WINDOW_WIDTH
    page.window.height    = WINDOW_HEIGHT
    page.window.min_width = WINDOW_MIN_W
    page.window.min_height = WINDOW_MIN_H
    page.padding          = 0
    page.spacing          = 0

    
    page.fonts = {
        "Inter": "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap",
        "JetBrains Mono": "https://fonts.googleapis.com/css2?family=JetBrains+Mono&display=swap"
    }

    # Aplicación del esquema 
    page.theme = ft.Theme(
        color_scheme_seed=Colors.ACCENT,
        visual_density=ft.VisualDensity.COMFORTABLE,
    )

    #  Inicializar router 
    router = init_router(page)

    # Pantalla Inicial 
    show_login(page, router)


if __name__ == "__main__":
    ft.app(target=main)