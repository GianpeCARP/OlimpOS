# =============================================================================
# config.py — Configuración global del sistema OlimpOS Elite
# =============================================================================
# Versión compatible con Flet 0.84.0 (Colores netos sin funciones de opacidad)

import flet as ft

# Nombre y versión de la aplicación
APP_NAME    = "OlimpOS"
APP_VERSION = "1.0.0"


# ── Paleta de colores (Minimalismo Apple Dark) ───────────────────────────────
class Colors:
    """
    Colores netos y sólidos calculados sobre la nueva base minimalista.
    """

    
    BG_DARK       = "#121417"  # Fondo base infinito, ultra oscuro y limpio
    BG_CARD       = "#1C1F24"  # Contenedores de módulos, tarjetas y superficies
    BG_GLASS      = "#16191D"  # Simulación de nivel traslúcido intermedio
    BG_SIDEBAR    = "#16191D"  # Fondo lateral con separación clara del lienzo
    BG_INPUT      = "#0A0B0D"  # Campos de texto hundidos de alta fidelidad

    #  Acento principal 
    ACCENT        = "#17B161"  # Verde esmeralda fino y predominante
    ACCENT_LIGHT  = "#22C55E"  # Variante viva para interacciones
    ACCENT_DARK   = "#15803D"  # Tono oscuro para elementos de control
    ACCENT_GLOW   = "#0F4C5C"  # Acento secundario profundo para delimitar atmósferas

    #  Texto 
    TEXT_PRIMARY  = "#F5F5F7"  # Blanco roto
    TEXT_SECONDARY= "#86868B"  # Gris corporativo para etiquetas y datos secundarios
    TEXT_MUTED    = "#424245"  # Texto apagado 

    #  Estados 
    SUCCESS = "#17B161"
    WARNING = "#FF9F0A"
    DANGER  = "#FF453A"
    INFO    = "#0A84FF"

    #  Bordes Sólidos 
    BORDER       = "#2D3139"  # Delimitador fino de contenedores (1px)
    BORDER_FOCUS = "#17B161"  # Anillo de enfoque activo

    WHITE = "#FFFFFF"


# Tipografía (Estilo limpio Sans-Serif Tech) 
class Fonts:
    TITLE = "Inter"
    BODY  = "Inter"
    MONO  = "JetBrains Mono"


#  Rutas 
class Routes:
    LOGIN     = "login"
    DASHBOARD = "dashboard"
    SOCIOS    = "socios"
    PERSONAL  = "personal"
    RUTINAS   = "rutinas"
    NUTRICION = "nutricion"
    USUARIOS  = "usuarios"


# ── Menú de navegación 
NAV_ITEMS = [
    {"label": "Dashboard",  "icon": ft.Icons.DASHBOARD,         "route": Routes.DASHBOARD},
    {"label": "Socios",     "icon": ft.Icons.GROUP,             "route": Routes.SOCIOS},
    {"label": "Personal",   "icon": ft.Icons.BADGE,             "route": Routes.PERSONAL},
    {"label": "Rutinas",    "icon": ft.Icons.FITNESS_CENTER,    "route": Routes.RUTINAS},
    {"label": "Nutrición",  "icon": ft.Icons.RESTAURANT_MENU,   "route": Routes.NUTRICION},
    {"label": "Usuarios",   "icon": ft.Icons.MANAGE_ACCOUNTS,   "route": Routes.USUARIOS},
]

# ── Dimensiones ────────────────────────────────────────────────────────────────
SIDEBAR_WIDTH  = 240
TOPBAR_HEIGHT  = 64
WINDOW_WIDTH   = 1350
WINDOW_HEIGHT  = 912
WINDOW_MIN_W   = 1024
WINDOW_MIN_H   = 640