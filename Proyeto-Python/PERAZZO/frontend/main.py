# =============================================================================
# main.py — Punto de entrada del sistema OlimpOS
# =============================================================================
# Este archivo es el primero que ejecuta Flet al iniciar la aplicación.
# Define y llama a la función `main(page)` que configura la ventana y arranca
# la pantalla de login.

import flet as ft  # Importa el framework Flet para construir la interfaz gráfica
import ssl

ssl._create_default_https_context = ssl._create_unverified_context
# Importa constantes de configuración global desde config.py:
# APP_NAME: nombre de la app ("OlimpOS")
# Colors: clase con todos los colores del sistema
# WINDOW_*: dimensiones predeterminadas y mínimas de la ventana
from app.config import (APP_NAME, Colors, WINDOW_WIDTH, WINDOW_HEIGHT,
                        WINDOW_MIN_W, WINDOW_MIN_H)

# Importa la función que inicializa el sistema de navegación (router)
from app.router import init_router

# Importa la función que muestra la pantalla de login
from app.views.login import show_login


def main(page: ft.Page):
    """
    Función principal de la aplicación.
    Flet la llama automáticamente al arrancar, pasando el objeto `page`
    que representa la ventana del sistema operativo.
    """

    # ── Configuración de la ventana ───────────────────────────────────────────

    page.title            = APP_NAME            # Título que aparece en la barra de la ventana
    page.theme_mode       = ft.ThemeMode.DARK   # Activa el modo oscuro globalmente
    page.bgcolor          = Colors.BG_DARK      # Color de fondo de la ventana (#0D0F14)
    page.window.width     = WINDOW_WIDTH        # Ancho inicial de la ventana (1280 px)
    page.window.height    = WINDOW_HEIGHT       # Alto inicial de la ventana (800 px)
    page.window.min_width = WINDOW_MIN_W        # Ancho mínimo permitido (1024 px)
    page.window.min_height = WINDOW_MIN_H       # Alto mínimo permitido (640 px)
    page.padding          = 0                   # Elimina el padding interno de la página
    page.spacing          = 0                   # Elimina el espaciado entre controles

    # Registra fuentes personalizadas en Google Fonts para usarlas por nombre
    page.fonts = {
        # Fuente display usada en títulos grandes y el logo
        "Bebas Neue": "https://fonts.gstatic.com/s/bebasneuepro/v9/L0ZlFf1Xt7-dHVHOLLIEoqvXNBJkfefG.woff2",
        # Fuente sans-serif usada en el cuerpo general de texto
        "DM Sans":    "https://fonts.gstatic.com/s/dmsans/v14/rP2Hp2ywxg089UriCZa4ET-DNl0.woff2",
    }

    # Aplica el tema visual global de Flet:
    # color_scheme_seed genera automáticamente una paleta de colores complementarios
    # basada en el color de acento naranja (#FF5722)
    page.theme = ft.Theme(
        color_scheme_seed=Colors.ACCENT,
        visual_density=ft.VisualDensity.COMFORTABLE,  # Espaciado cómodo entre controles
    )

    # ── Inicializar router ────────────────────────────────────────────────────
    # Crea e instancia el Router (gestor de navegación) y lo guarda globalmente.
    # El router controla qué vista se muestra en cada momento.
    router = init_router(page)

    # ── Mostrar login como pantalla inicial ───────────────────────────────────
    # Llama a la función que construye y muestra la pantalla de inicio de sesión.
    # Le pasa `page` (la ventana) y `router` (para poder navegar tras autenticarse).
    show_login(page, router)


# Punto de entrada estándar de Python.
# ft.app() inicia el event loop de Flet y llama a `main` con el objeto page.
if __name__ == "__main__":
    ft.app(target=main)
