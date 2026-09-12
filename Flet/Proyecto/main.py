# =============================================================================
# main.py — Punto de entrada del sistema OlimpOS
# =============================================================================

import flet as ft

from app.config import (APP_NAME, Colors, Fonts, WINDOW_WIDTH, WINDOW_HEIGHT,
                        WINDOW_MIN_W, WINDOW_MIN_H)
from app.router import init_router
from app.views.login import show_login


def main(page: ft.Page):
    """
    Configura la ventana y arranca en la pantalla de login.
    """

    # ── Ventana ──────────────────────────────────────────────────────────────
    page.title             = APP_NAME
    page.theme_mode        = ft.ThemeMode.DARK
    page.bgcolor           = Colors.SURFACE_BASE
    page.window.width      = WINDOW_WIDTH
    page.window.height     = WINDOW_HEIGHT
    page.window.min_width  = WINDOW_MIN_W
    page.window.min_height = WINDOW_MIN_H
    page.padding           = 0
    page.spacing           = 0

    # ── Tipografías ──────────────────────────────────────────────────────────
    # Las mismas tres familias que la PWA. Van apuntadas al .ttf directo del
    # repositorio de Google Fonts: `page.fonts` de Flet espera un ARCHIVO de
    # fuente, no una URL de CSS — la versión anterior apuntaba a
    # "fonts.googleapis.com/css2?..." y por eso nunca cargaba ninguna y todo
    # caía en la fuente por defecto del sistema.
    #
    # Para que la app funcione sin internet, bajá estos cuatro archivos a
    # assets/ y cambiá la URL por el nombre del archivo (Flet resuelve los
    # nombres sueltos contra la carpeta assets).
    BASE = "https://raw.githubusercontent.com/google/fonts/main/ofl"
    page.fonts = {
        "Barlow Semi Condensed": f"{BASE}/barlowsemicondensed/BarlowSemiCondensed-Bold.ttf",
        "Archivo":               f"{BASE}/archivo/Archivo%5Bwdth%2Cwght%5D.ttf",
        "JetBrains Mono":        f"{BASE}/jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf",
    }

    # ── Tema ─────────────────────────────────────────────────────────────────
    page.theme = ft.Theme(
        color_scheme_seed=Colors.PRIMARY_VOLT,
        font_family=Fonts.BODY,          # Archivo como fuente por defecto
        visual_density=ft.VisualDensity.COMFORTABLE,
    )

    # ── Router ───────────────────────────────────────────────────────────────
    router = init_router(page)

    # ── Pantalla inicial ─────────────────────────────────────────────────────
    show_login(page, router)


if __name__ == "__main__":
    # assets_dir es necesario para que Flet resuelva las imágenes que se piden
    # por nombre suelto (el logo del sidebar: "logo-removebg-preview.png").
    # Sin este parámetro la carpeta assets/ no se monta y la imagen no aparece.
    ft.run(main, assets_dir="assets")
