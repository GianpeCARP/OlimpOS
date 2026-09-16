# =============================================================================
# config.py — Configuración global del sistema OlimpOS
# =============================================================================
# Compatible con Flet 0.84.0 (colores netos en hex, sin funciones de opacidad).
#
# ── IMPORTANTE ───────────────────────────────────────────────────────────────
# La paleta de este archivo es "Kinetic Carbon", la MISMA que usa la PWA web
# (src/frontend/src/index.css y config.ts). Las dos aplicaciones son el mismo
# producto visto desde dos lugares distintos: la PWA la usan los socios desde
# el navegador, esta app de escritorio la usa el personal del gimnasio. Tienen
# que verse como una sola cosa.
#
# Si algún día cambia un color, cambia en los DOS archivos o dejan de ser la
# misma marca:
#   PWA  → src/frontend/src/index.css        (bloque @theme)
#   Flet → este archivo                       (clase Colors)
# =============================================================================

import flet as ft

# Nombre y versión de la aplicación
APP_NAME    = "OlimpOS"
APP_VERSION = "1.0.0"

# Espejo de MAX_INTENTOS_FALLIDOS (backend/routers/auth_router.py) y de
# BLOQUEO_CUENTA_SEG (backend/limite_intentos.py), igual que en config.ts de la
# PWA. Sólo se usan para AVISAR: quien cuenta y traba es el backend. Los fallos
# de "contraseña actual" al cambiarla suman al mismo contador que el login.
MAX_INTENTOS_FALLIDOS  = 5
MINUTOS_CUENTA_TRABADA = 15


# ── Paleta de colores (Kinetic Carbon — espejo de la PWA) ────────────────────
class Colors:
    """
    Paleta espejo de la web. Los nombres nuevos (SURFACE_*, PRIMARY_*, TEXT_*)
    son los que hay que usar de acá en adelante porque se llaman igual que los
    tokens de Tailwind en la PWA, así comparar las dos apps es directo.

    Los nombres viejos (BG_DARK, ACCENT, SUCCESS…) se conservan más abajo como
    alias apuntando a los valores nuevos: cualquier código que todavía no se
    haya migrado sigue funcionando y además se pinta con la paleta correcta.
    """

    # ── Superficies ──────────────────────────────────────────────────────────
    SURFACE_BASE  = "#15171C"  # Fondo de la ventana (--color-surface-base)
    SURFACE_CARD  = "#1C1F26"  # Tarjetas, modales, contenedores
    SURFACE_HOVER = "#242832"  # Sidebar y estados hover

    # ── Acento principal: verde volt ─────────────────────────────────────────
    # Este es el color firma del producto. Ojo: sobre volt el texto va OSCURO
    # (SURFACE_BASE), nunca blanco — es un amarillo-verde muy claro.
    PRIMARY_VOLT  = "#C6F135"
    PRIMARY_DIM   = "#9BBE22"
    ACCENT_CORAL  = "#FF6B3D"
    ACCENT_DIM    = "#D2542C"

    # ── Bordes ───────────────────────────────────────────────────────────────
    BORDER_IDLE   = "#2A3324"  # Borde de 1px de cualquier contenedor
    BORDER_ACTIVE = "#586A36"  # Borde con foco

    # ── Texto ────────────────────────────────────────────────────────────────
    TEXT_MAIN      = "#F2F3F5"
    TEXT_SECONDARY = "#A4A9B4"
    TEXT_MUTED     = "#6C7280"

    # ── Estados ──────────────────────────────────────────────────────────────
    STATUS_OK     = "#3DDC97"
    STATUS_WARN   = "#FFC24B"
    STATUS_DANGER = "#FF5C5C"

    WHITE = "#FFFFFF"

    # ── Alias de compatibilidad ──────────────────────────────────────────────
    # Nombres de la paleta anterior ("Apple Dark" verde esmeralda) apuntando a
    # los valores nuevos. Están para que ninguna vista todavía sin migrar tire
    # AttributeError y para que igual se pinte con la paleta correcta.
    BG_DARK      = SURFACE_BASE
    BG_CARD      = SURFACE_CARD
    BG_GLASS     = SURFACE_HOVER
    BG_SIDEBAR   = SURFACE_HOVER
    BG_INPUT     = SURFACE_BASE

    ACCENT       = PRIMARY_VOLT
    ACCENT_LIGHT = PRIMARY_VOLT
    ACCENT_DARK  = PRIMARY_DIM
    ACCENT_GLOW  = SURFACE_CARD

    TEXT_PRIMARY = TEXT_MAIN

    SUCCESS = STATUS_OK
    WARNING = STATUS_WARN
    DANGER  = STATUS_DANGER
    INFO    = PRIMARY_VOLT      # La PWA no tiene un "info" azul: usa el volt.

    BORDER       = BORDER_IDLE
    BORDER_FOCUS = BORDER_ACTIVE


def alpha(color: str, opacidad: float) -> str:
    """
    Color translúcido — el equivalente Flet del `backgroundColor: ${color}1A`
    que usan los badges de la PWA.

    Delega en ft.Colors.with_opacity, que en Flet 0.84 devuelve el formato
    "color,opacidad". NO se arma el hex a mano: pegarle dos dígitos al final
    del color (el viejo f"{color}20") da un valor de 8 dígitos que Flet lee
    como #AARRGGBB —con el alfa ADELANTE—, así que corre los canales y sale
    un color completamente distinto. Ese bug estaba en el código anterior y
    era el motivo de que los íconos de "Actividad Reciente" se vieran rojos.
    """
    return ft.Colors.with_opacity(opacidad, color)


# ── Tipografía (misma que la PWA) ────────────────────────────────────────────
class Fonts:
    """
    Barlow Semi Condensed para títulos, Archivo para texto corrido y
    JetBrains Mono exclusivo para métricas (DESIGN.md §6 de la PWA).
    Los archivos se registran en main.py (page.fonts).
    """
    TITLE = "Barlow Semi Condensed"   # h1/h2 — font-heading
    BODY  = "Archivo"                  # texto general — font-body
    MONO  = "JetBrains Mono"           # números grandes — font-mono


# ── Radios de esquina (--radius-* de la PWA) ─────────────────────────────────
class Radius:
    SM = 6
    MD = 10
    LG = 14


# ── Rutas ────────────────────────────────────────────────────────────────────
class Routes:
    LOGIN       = "login"
    DASHBOARD   = "dashboard"
    RECEPCION   = "recepcion"
    SOCIOS      = "socios"
    COBROS      = "cobros"
    ASISTENCIA  = "asistencia"
    PERSONAL    = "personal"
    RUTINAS     = "rutinas"
    NUTRICION   = "nutricion"
    ACTIVIDADES = "actividades"
    USUARIOS    = "usuarios"


# ── Menú de navegación ───────────────────────────────────────────────────────
# Mismo orden y mismas etiquetas que NAV_ITEMS de la PWA (config.ts). Los
# íconos son los equivalentes de Material a los de lucide-react que usa la web:
#   LayoutDashboard→DASHBOARD, Users→GROUP, Wallet→ACCOUNT_BALANCE_WALLET,
#   Fingerprint→FINGERPRINT, UserCog→BADGE, Dumbbell→FITNESS_CENTER,
#   Apple→RESTAURANT_MENU, CalendarCheck→EVENT_AVAILABLE, ShieldCheck→VERIFIED_USER
NAV_ITEMS = [
    {"label": "Dashboard",   "icon": ft.Icons.DASHBOARD,                 "route": Routes.DASHBOARD},
    # Va segundo, arriba de todo lo demas: es la pantalla que el recepcionista
    # mira todo el dia. Para el Dueno es una mas; para el mostrador es LA vista.
    {"label": "Recepción",   "icon": ft.Icons.SUPPORT_AGENT_ROUNDED,     "route": Routes.RECEPCION},
    {"label": "Socios",      "icon": ft.Icons.GROUP,                     "route": Routes.SOCIOS},
    {"label": "Cobros",      "icon": ft.Icons.ACCOUNT_BALANCE_WALLET,    "route": Routes.COBROS},
    {"label": "Asistencia",  "icon": ft.Icons.FINGERPRINT,               "route": Routes.ASISTENCIA},
    {"label": "Personal",    "icon": ft.Icons.BADGE,                     "route": Routes.PERSONAL},
    {"label": "Rutinas",     "icon": ft.Icons.FITNESS_CENTER,            "route": Routes.RUTINAS},
    {"label": "Nutrición",   "icon": ft.Icons.RESTAURANT_MENU,           "route": Routes.NUTRICION},
    {"label": "Actividades", "icon": ft.Icons.EVENT_AVAILABLE,           "route": Routes.ACTIVIDADES},
    {"label": "Usuarios",    "icon": ft.Icons.VERIFIED_USER,             "route": Routes.USUARIOS},
]

# ── Dimensiones ──────────────────────────────────────────────────────────────
SIDEBAR_WIDTH  = 260   # Igual que la PWA (config.ts)
TOPBAR_HEIGHT  = 64    # Igual que la PWA
WINDOW_WIDTH   = 1350
WINDOW_HEIGHT  = 912
WINDOW_MIN_W   = 1024
WINDOW_MIN_H   = 640
