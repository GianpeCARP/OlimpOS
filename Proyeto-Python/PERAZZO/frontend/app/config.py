# =============================================================================
# config.py — Configuración global del sistema OlimpOS
# =============================================================================
# Este archivo centraliza TODAS las constantes del sistema: colores, tipografía,
# rutas de navegación, ítems del menú y dimensiones de ventana.
# Cualquier archivo que necesite una constante la importa desde aquí,
# lo que garantiza consistencia visual y facilita cambios globales.

import flet as ft  # Importa Flet para usar sus íconos en NAV_ITEMS

# Nombre y versión de la aplicación — se usan en la barra de título y el logo
APP_NAME    = "OlimpOS"
APP_VERSION = "1.0.0"


# ── Paleta de colores ────────────────────────────────────────────────────────
class Colors:
    """
    Define todos los colores del sistema en formato hexadecimal.
    Agrupados por categoría semántica para facilitar mantenimiento.
    Todos los componentes visuales importan colores exclusivamente de aquí.
    """

    # ── Fondos ───────────────────────────────────────────────────────────────
    BG_DARK       = "#0D0F14"   # Fondo principal de la ventana (negro azulado oscuro)
    BG_CARD       = "#13161E"   # Fondo de tarjetas y paneles secundarios
    BG_SIDEBAR    = "#0A0C10"   # Fondo del sidebar (más oscuro que el principal)
    BG_INPUT      = "#1C2030"   # Fondo de campos de texto y botones secundarios

    # ── Acento principal ─────────────────────────────────────────────────────
    ACCENT        = "#FF5722"   # Naranja eléctrico — color principal de la marca
    ACCENT_LIGHT  = "#FF7043"   # Variante más clara del acento (hover de botones)
    ACCENT_GLOW   = "#FF572240" # Acento con 25% de opacidad (fondos decorativos)

    # ── Texto ────────────────────────────────────────────────────────────────
    TEXT_PRIMARY   = "#F0F2F8"  # Texto principal (casi blanco, alto contraste)
    TEXT_SECONDARY = "#7A8099"  # Texto secundario y subtítulos (gris azulado)
    TEXT_MUTED     = "#3D4259"  # Texto desactivado / labels (gris muy apagado)

    # ── Estados ──────────────────────────────────────────────────────────────
    SUCCESS = "#22C55E"  # Verde — éxito, activo, positivo
    WARNING = "#F59E0B"  # Amarillo — advertencia, turno mañana
    DANGER  = "#EF4444"  # Rojo — error, vencido, peligro
    INFO    = "#3B82F6"  # Azul — información, turno tarde

    # ── Bordes ───────────────────────────────────────────────────────────────
    BORDER       = "#1F2335"   # Borde estándar entre secciones y tarjetas
    BORDER_FOCUS = "#FF5722"   # Borde al enfocar un input (mismo que ACCENT)

    WHITE = "#FFFFFF"           # Blanco puro — texto sobre fondos de acento


# ── Tipografía ────────────────────────────────────────────────────────────────
class Fonts:
    """
    Define las fuentes utilizadas en la aplicación.
    Las fuentes deben estar registradas en page.fonts (main.py) para usarse.
    """
    TITLE = "Bebas Neue"      # Fuente display para títulos y números grandes
    BODY  = "DM Sans"         # Fuente sans-serif para texto general
    MONO  = "JetBrains Mono"  # Fuente monoespaciada (reservada para código)


# ── Rutas / Secciones ─────────────────────────────────────────────────────────
class Routes:
    """
    Define las rutas de navegación del sistema como constantes de cadena.
    El Router usa estos valores para identificar qué vista mostrar.
    Usar constantes en lugar de strings literales previene errores de tipeo.
    """
    LOGIN     = "login"        # Pantalla de inicio de sesión
    DASHBOARD = "dashboard"    # Vista principal con estadísticas
    ALTA      = "alta_persona" # Alta unificada: Persona + Socio/Empleado + Usuario
    SOCIOS    = "socios"       # Consulta y modificación de socios
    PERSONAL  = "personal"     # Consulta y modificación de personal/empleados
    RUTINAS   = "rutinas"      # Catálogo de rutinas de entrenamiento
    NUTRICION = "nutricion"    # Planes nutricionales
    TURNOS    = "turnos"       # Clases y horarios del gimnasio
    USUARIOS  = "usuarios"     # Consulta y modificación de usuarios del sistema


# ── Menú de navegación ────────────────────────────────────────────────────────
# Lista de diccionarios que describe cada ítem del menú lateral (sidebar).
# Cada ítem tiene:
#   label: texto visible en el sidebar
#   icon:  ícono de Material Design que muestra junto al label
#   route: constante de Routes que el router usa al hacer clic
NAV_ITEMS = [
    {"label": "Dashboard",      "icon": ft.Icons.DASHBOARD,         "route": Routes.DASHBOARD},
    {"label": "Nueva Persona",  "icon": ft.Icons.PERSON_ADD,        "route": Routes.ALTA},
    {"label": "Socios",         "icon": ft.Icons.GROUP,             "route": Routes.SOCIOS},
    {"label": "Personal",       "icon": ft.Icons.BADGE,             "route": Routes.PERSONAL},
    {"label": "Rutinas",        "icon": ft.Icons.FITNESS_CENTER,    "route": Routes.RUTINAS},
    {"label": "Nutrición",      "icon": ft.Icons.RESTAURANT_MENU,   "route": Routes.NUTRICION},
    {"label": "Turnos",         "icon": ft.Icons.CALENDAR_MONTH,    "route": Routes.TURNOS},
    {"label": "Usuarios",       "icon": ft.Icons.MANAGE_ACCOUNTS,   "route": Routes.USUARIOS},
]

# ── Dimensiones ────────────────────────────────────────────────────────────────
# Todas las medidas están en píxeles y se usan en múltiples archivos.
# Centralizar estos valores evita hardcodear números en los componentes.

SIDEBAR_WIDTH  = 240   # Ancho fijo del panel de navegación lateral
TOPBAR_HEIGHT  = 64    # Alto de la barra superior de cada sección
WINDOW_WIDTH   = 1280  # Ancho inicial de la ventana de la aplicación
WINDOW_HEIGHT  = 800   # Alto inicial de la ventana de la aplicación
WINDOW_MIN_W   = 1024  # Ancho mínimo — impide que la UI se rompa al achicar
WINDOW_MIN_H   = 640   # Alto mínimo — impide que la UI se rompa al achicar
