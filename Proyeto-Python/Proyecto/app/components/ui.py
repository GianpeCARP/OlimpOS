# =============================================================================
# components/ui.py — Componentes reutilizables del sistema
# =============================================================================
# Este archivo es la "librería de componentes" de OlimpOS.
# Cada función fabrica un widget Flet listo para usar con el estilo visual
# del sistema. Ninguna vista construye widgets "desde cero" — siempre reutilizan
# las funciones definidas aquí para garantizar consistencia.

import flet as ft
# Importa todas las constantes necesarias desde config.py
from app.config import Colors, NAV_ITEMS, APP_NAME, SIDEBAR_WIDTH, TOPBAR_HEIGHT
from app.state import app_state  # Para mostrar el nombre del usuario en el sidebar


# =============================================================================
# SIDEBAR
# =============================================================================

def build_sidebar(page: ft.Page, router, active_route: str) -> ft.Container:
    """
    Construye el sidebar de navegación lateral completo.
    Incluye: logo, menú de ítems, y footer con datos del usuario y logout.
    `active_route` indica qué ítem del menú debe aparecer resaltado.
    """

    # Genera la lista de widgets de ítems de menú, marcando el activo
    
    nav_items = []
    for item in NAV_ITEMS:
        is_active = item["route"] == active_route  # True si esta ruta es la activa
        nav_items.append(_nav_item(item, is_active, router))  # Crea el widget del ítem

    # ── Sección del logo ──────────────────────────────────────────────────────
    logo_section = ft.Container(
        content=ft.Column([
            ft.Row([
                # Cuadrado verde con el logo del sistema 
                ft.Container(
                    content=ft.Image(
                        src="logo-removebg-preview.png",     # Nombre de tu archivo en assets
                        width=40,                # Tamaño ideal para que entre cómodo en el contenedor
                        height=40,
                        fit="contain", #Evita que se deforme
                    ),
                    width=50, 
                    height=50, 
                    border_radius=12,
                    bgcolor="#FFFFFF",
                    border=ft.border.all(width=2, color=Colors.ACCENT),
                    alignment=ft.Alignment.CENTER, # Centra el icono perfectamente adentro del recuadro
                ),
                # Nombre del sistema y subtítulo
                ft.Column([
                    ft.Text(APP_NAME, color=Colors.ACCENT, size=20,
                            weight=ft.FontWeight.BOLD, font_family="Bebas Neue"),
                    ft.Text("Sistema de Gestión", color=Colors.TEXT_SECONDARY, size=10),
                ], spacing=0, tight=True),
            ], spacing=12),
        ]),
        padding=ft.padding.only(left=20, top=24, bottom=24, right=20),
    )

    # ── Línea divisoria entre logo y menú ─────────────────────────────────────
    divider = ft.Container(
        height=1, bgcolor=Colors.BORDER,
        margin=ft.margin.only(left=20, right=20, bottom=8)
    )

    # ── Label de sección "MENÚ PRINCIPAL" ────────────────────────────────────
    section_label = ft.Container(
        content=ft.Text("MENÚ PRINCIPAL", color=Colors.TEXT_MUTED, size=10,
                        weight=ft.FontWeight.W_800),
        padding=ft.padding.only(left=20, bottom=8, top=8),
    )

    # ── Footer del sidebar con datos de usuario y botón de logout ─────────────

    def handle_logout(e):
        """
        Cierra la sesión del usuario cuando hace clic en el ícono de logout.
        Llama a logout() del estado global para limpiar la sesión y
        redirige al login reconstruyendo toda la página.
        """
        from app.state import app_state
        app_state.logout()              # Limpia logged_in y current_user
        from app.views.login import show_login
        show_login(page, router)        # Reconstruye la pantalla de login

    sidebar_footer = ft.Container(
        content=ft.Column([
            ft.Divider(color=Colors.BORDER, height=1),  # Línea separadora
            ft.Container(height=12),
            ft.Row([
                # Avatar circular con inicial del usuario
                ft.Container(
                    content=ft.Text(
                        value="U", # Momentaneamente fijo a "U" (User) — podría ser la inicial del nombre del usuario o un avatar personalizado
                        # Nota: la línea comentada recuperaría el avatar de la sesión.
                        # Actualmente se muestra vacío; podría usarse app_state.get_user_avatar() o value=app_state.get_user_name()[0].upper() if app_state.get_user_name() else "U"
                        color=Colors.WHITE, size=14, weight=ft.FontWeight.BOLD
                    ),
                    width=36, height=36, border_radius=18,
                    bgcolor=Colors.ACCENT, alignment=ft.Alignment.CENTER,
                ),
                # Nombre y rol del usuario activo
                ft.Column([
                    ft.Text(
                        app_state.get_user_name(),  # Ej: "Administrador"
                        color=Colors.TEXT_PRIMARY, size=13, weight=ft.FontWeight.W_700
                    ),
                    ft.Text(
                        # Nota: podría mostrarse el rol con app_state.get_user_role()
                        color=Colors.TEXT_SECONDARY, size=11
                    ),
                ], spacing=1, tight=True, expand=True),
                # Botón de cerrar sesión
                ft.IconButton(
                    icon=ft.Icons.LOGOUT_ROUNDED,
                    icon_size=18,
                    tooltip="Cerrar sesión",
                    on_click=handle_logout,  # Llama a la función de logout definida arriba
                    
                    style=ft.ButtonStyle(
                        color={
                            
                            ft.ControlState.HOVERED: Colors.DANGER, 
                    
                            
                            ft.ControlState.DEFAULT: Colors.TEXT_SECONDARY,})
                ),
            ], spacing=10),
        ]),
        padding=ft.padding.only(left=12, right=12, bottom=16),
    )

    #  Ensamblado final del sidebar 
    return ft.Container(
        content=ft.Column([
            logo_section,   # Logo + nombre del sistema
            divider,        # Línea divisoria
            section_label,  # Label "MENÚ PRINCIPAL"
            # ListView es más estable que Column para menús laterales en Flet:
            # maneja correctamente el scroll cuando hay muchos ítems
            ft.ListView(
                controls=nav_items,  # Lista de ítems de navegación
                spacing=2,
                expand=True,         # Ocupa todo el espacio entre label y footer
            ),
            sidebar_footer,  # Avatar, nombre y botón de logout
        ], spacing=0),
        width=SIDEBAR_WIDTH,            # 240 px — fijo desde config.py
        height=page.window.height,      # Ocupa toda la altura de la ventana
        bgcolor=Colors.BG_SIDEBAR,      # Fondo más oscuro que el área principal
        border=ft.border.only(right=ft.BorderSide(1, Colors.BORDER)),  # Borde derecho separador
    )

# La lista se llena una sola vez al arrancar la barra lateral (ej. 5 botones = 5 elementos)
_todos_los_botones = []

def _nav_item(item: dict, is_active: bool, router) -> ft.Container:
    """
    Construye un ítem individual del menú de navegación lateral de forma dinámica.
    """
    
    bg_color   = Colors.ACCENT_GLOW if is_active else ft.Colors.TRANSPARENT
    icon_color = Colors.ACCENT if is_active else Colors.TEXT_SECONDARY
    text_color = Colors.TEXT_PRIMARY if is_active else Colors.TEXT_SECONDARY

    
    indicator = ft.Container(
        width=3, height=32, border_radius=2,
        bgcolor=Colors.ACCENT if is_active else ft.Colors.TRANSPARENT,
    )
    icon = ft.Icon(item["icon"], color=icon_color, size=20)
    text = ft.Text(
        item["label"], color=text_color, size=14,
        weight=ft.FontWeight.W_600 if is_active else ft.FontWeight.NORMAL
    )

    def on_hover(e: ft.HoverEvent):
        """
        Maneja el hover visual leyendo la ruta activa en tiempo real.
        Arreglado convirtiendo e.data a minúsculas para evitar mañas de Flet.
        """
        from app.state import app_state
        es_activo_real = item["route"] == app_state.current_route

       
        if es_activo_real:
            e.control.bgcolor = Colors.ACCENT_GLOW
            indicator.bgcolor = Colors.ACCENT
            icon.color        = Colors.ACCENT
            text.color        = Colors.TEXT_PRIMARY
            e.control.update()
            return

        # SI NO ES EL ACTIVO: Evaluamos la entrada y salida con .lower()
        # Esto transforma "True" en "true" y "False" en "false" automáticamente.
        estado_mouse = str(e.data).lower()
        #BORRAR LOS ENTRA Y SALE LUEGO
        if estado_mouse == "true":
            print(f"ENTRA - Ítem: {item['label']}")
            e.control.bgcolor = Colors.BG_INPUT
            icon.color        = Colors.TEXT_PRIMARY
            text.color        = Colors.TEXT_PRIMARY
        else:
            print(f"SALE - Ítem: {item['label']}")
            e.control.bgcolor = ft.Colors.TRANSPARENT
            icon.color        = Colors.TEXT_SECONDARY
            text.color        = Colors.TEXT_SECONDARY
        
        e.control.update()

    def on_click(e):
        """
        Navegación inteligente: Apaga el resto de los botones y enciende este.
        """
        from app.state import app_state
        
        # 1. Actualizamos la brújula global de la aplicación ANTES de viajar
        app_state.current_route = item["route"]

        # 2. EL APAGÓN ABSOLUTO: Dejamos a todos los botones en gris/transparente de forma nativa
        for boton in _todos_los_botones:
            boton["container"].bgcolor = ft.Colors.TRANSPARENT
            boton["indicator"].bgcolor = ft.Colors.TRANSPARENT
            boton["icon"].color        = Colors.TEXT_SECONDARY
            boton["text"].color        = Colors.TEXT_SECONDARY
            boton["text"].weight       = ft.FontWeight.NORMAL
            boton["container"].update()  # Forzamos a Flet a pintar el apagado

        # 3. EL ENCENDIDO: Pintamos el verde brillante únicamente en el botón que clickeaste
        e.control.bgcolor = Colors.ACCENT_GLOW
        indicator.bgcolor = Colors.ACCENT
        icon.color        = Colors.ACCENT
        text.color        = Colors.TEXT_PRIMARY
        text.weight       = ft.FontWeight.W_600
        e.control.update()  # Forzamos a Flet a pintar el encendido

        # 4. Viajamos
        router.navigate(item["route"])

    # Armamos el contenedor principal
    contenedor_padre = ft.Container(
        content=ft.Row([
            indicator,
            ft.Container(width=8),
            icon,
            ft.Container(width=10),
            text,
        ], spacing=0),
        bgcolor=bg_color,
        border_radius=8,
        height=44,
        margin=ft.margin.only(left=8, right=8),
        padding=ft.padding.only(right=12),
        on_hover=on_hover,
        on_click=on_click,
        animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
    )

    # GUARDAMOS LAS REFERENCIAS: Se ejecuta una sola vez por botón al arrancar la app
    _todos_los_botones.append({
        "container": contenedor_padre,
        "indicator": indicator,
        "icon": icon,
        "text": text
    })

    return contenedor_padre
    
# =============================================================================
# TOPBAR
# =============================================================================

def build_topbar(title: str, subtitle: str = "", actions: list = None) -> ft.Container:
    """
    Construye la barra superior de cada sección.
    Muestra el título de la sección, un subtítulo opcional y botones de acción
    (por ejemplo, "Nuevo Socio") alineados a la derecha.
    """
    # Agrupa los botones de acción en una fila (puede estar vacía)
    right_content = ft.Row(actions or [], spacing=8)

    return ft.Container(
        content=ft.Row([
            # Columna izquierda: título y subtítulo
            ft.Column([
                ft.Text(title, color=Colors.TEXT_PRIMARY, size=22,
                        weight=ft.FontWeight.BOLD, font_family="Bebas Neue"),
                # Muestra el subtítulo solo si se proporcionó uno
                ft.Text(subtitle, color=Colors.TEXT_SECONDARY, size=13) if subtitle else ft.Container(),
            ], spacing=2, tight=True),
            # Fila derecha: espacio flexible + acciones
            ft.Row([ft.Container(expand=True), right_content]),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),  # Título izq, acciones der
        height=TOPBAR_HEIGHT + 20,  # 84 px total — un poco más alto que el TOPBAR_HEIGHT base
        padding=ft.padding.only(left=28, right=24, top=16, bottom=12),
        border=ft.border.only(bottom=ft.BorderSide(1, Colors.BORDER)),  # Línea separadora inferior
    )


# =============================================================================
# STAT CARD (tarjeta de estadística para el dashboard)
# =============================================================================

def stat_card(title: str, value: str, delta: str, tendencia: str,
              icon: str, color: str = Colors.ACCENT) -> ft.Container:
    """
    Tarjeta de estadística usada en el dashboard.
    Muestra: ícono de categoría, valor principal grande, título descriptivo
    y delta (variación) con ícono de flecha según tendencia (up/down).
    """
    # Determina si la tendencia es positiva (verde/flecha arriba) o negativa (rojo/flecha abajo)
    is_up       = tendencia == "up"
    delta_color = Colors.SUCCESS if is_up else Colors.DANGER
    delta_icon  = ft.Icons.ARROW_UPWARD_ROUNDED if is_up else ft.Icons.ARROW_DOWNWARD_ROUNDED

    return ft.Container(
        content=ft.Column([
            ft.Row([
                # Ícono de categoría con fondo translúcido del mismo color
                ft.Container(
                    content=ft.Icon(icon, color=color, size=22),
                    width=44, height=44, border_radius=12,
                    bgcolor=f"{color}20",         # 20 = ~12% de opacidad en hex
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Container(expand=True),         # Empuja el delta a la derecha
                # Delta con ícono de flecha y porcentaje/número de variación
                ft.Row([
                    ft.Icon(delta_icon, color=delta_color, size=14),
                    
                    # 1. CAMBIAMOS LA FUENTE DEL DELTA A DM SANS
                    ft.Text(delta, color=delta_color, size=12, weight=ft.FontWeight.W_600, font_family="DM Sans"),
                ], spacing=2),
            ]),
            ft.Container(height=12),
            
            # 2. CORREGIDO: Cambiamos "Bebas Neue" por "DM Sans" para normalizar los números grandes
            ft.Text(str(value), color=Colors.TEXT_PRIMARY, size=28,
                    weight=ft.FontWeight.BOLD, font_family="DM Sans"),
            
            # 3. CAMBIAMOS LA FUENTE DEL TÍTULO ABAJO A DM SANS
            ft.Text(title, color=Colors.TEXT_SECONDARY, size=13, font_family="DM Sans"),
        ], spacing=0),
        bgcolor=Colors.BG_CARD,
        border_radius=14,
        padding=20,
        border=ft.border.all(1, Colors.BORDER),
        expand=True,                              # Se expande para ocupar partes iguales del Row
        animate=ft.Animation(200),               # Animación suave al aparecer
    )


# =============================================================================
# STATUS BADGE (indicador de estado coloreado)
# =============================================================================

# Mapa de estado → (color de texto, color de fondo con transparencia)
STATUS_COLORS = {
    "Activo":     (Colors.SUCCESS, "#22C55E20"),         # Verde
    "Vencido":    (Colors.DANGER,  "#22C55E20"),          # Rojo
    "Suspendido": (Colors.WARNING, "#F59E0B20"),          # Amarillo
    "Inactivo":   (Colors.TEXT_SECONDARY, "#7A809920"),  # Gris
}

def status_badge(status: str) -> ft.Container:
    """
    Badge de estado con forma de pastilla redondeada.
    El color varía según el estado (Activo, Vencido, Suspendido, Inactivo).
    Se usa en tablas de socios, empleados y usuarios.
    """
    # Obtiene los colores del estado, o gris por defecto si el estado no está mapeado
    text_c, bg_c = STATUS_COLORS.get(status, (Colors.TEXT_SECONDARY, "#7A809920"))
    return ft.Container(
        content=ft.Text(status, color=text_c, size=11, weight=ft.FontWeight.W_600),
        bgcolor=bg_c,
        border_radius=20,  # Totalmente redondeado para aspecto de "pill"
        padding=ft.padding.symmetric(horizontal=10, vertical=4),
    )


# =============================================================================
# PRIMARY BUTTON (botón de acción principal)
# =============================================================================

def primary_button(label: str, icon: str = None, on_click=None, width: int = None) -> ft.Container:
    """
    Botón de acción principal con estilo naranja (color de acento).
    Opcionalmente muestra un ícono a la izquierda del texto.
    Incluye animación de hover que aclara el fondo al pasar el mouse.
    """
    # Construye el contenido del botón: ícono opcional + texto
    row_content = []
    if icon:
        row_content.append(ft.Icon(icon, color=Colors.WHITE, size=16))
    row_content.append(ft.Text(label, color=Colors.WHITE, size=13, weight=ft.FontWeight.W_600))

    def on_hover(e: ft.HoverEvent):
        """Cambia el fondo a una versión más clara del acento en hover."""
        e.control.bgcolor = Colors.ACCENT_LIGHT if e.data == "true" else Colors.ACCENT
        e.control.update()

    btn = ft.Container(
        content=ft.Row(row_content, spacing=6, alignment=ft.MainAxisAlignment.CENTER),
        bgcolor=Colors.ACCENT,       # Fondo naranja eléctrico
        border_radius=8,
        height=40,
        width=width,                 # Ancho fijo opcional; si es None, se ajusta al contenido
        padding=ft.padding.symmetric(horizontal=16),
        on_click=on_click,
        on_hover=on_hover,
        animate=ft.Animation(150),  # Transición suave de color en hover
    )
    return btn


# =============================================================================
# INPUT FIELD (campo de texto estilizado)
# =============================================================================

def input_field(label: str, hint: str = "", password: bool = False,
                icon: str = None, ref: ft.Ref = None, width=None) -> ft.TextField:
    """
    Campo de texto con el estilo visual del sistema.
    Aplica automáticamente colores, fuentes y estilos de borde del sistema.
    Parámetros:
        label:    Texto flotante sobre el campo
        hint:     Texto placeholder cuando está vacío
        password: Si True, oculta el texto y muestra botón de revelar
        icon:     Ícono opcional a la izquierda del texto
        ref:      ft.Ref para acceder al valor del campo desde fuera del widget
        width:    Ancho fijo opcional en píxeles
    """
    return ft.TextField(
        ref=ref,                                    # Permite leer/escribir el valor desde el padre
        label=label,
        hint_text=hint,
        password=password,                          # Oculta el texto si es campo de contraseña
        can_reveal_password=password,              # Muestra el ícono de ojo para contraseñas
        prefix_icon=icon,                           # Ícono prefijo dentro del campo
        color=Colors.TEXT_PRIMARY,                 # Color del texto ingresado
        label_style=ft.TextStyle(color=Colors.TEXT_SECONDARY),  # Color del label flotante
        hint_style=ft.TextStyle(color=Colors.TEXT_MUTED),       # Color del placeholder
        bgcolor=Colors.BG_INPUT,                   # Fondo del campo
        border_color=Colors.BORDER,                # Borde en reposo
        focused_border_color=Colors.ACCENT,       # Borde naranja al hacer foco
        border_radius=10,
        content_padding=ft.padding.symmetric(horizontal=16, vertical=12),
        width=420,                               # Ancho fijo opcional
    )


# =============================================================================
# SECTION CARD (contenedor de sección con borde y fondo)
# =============================================================================

def section_card(content: ft.Control, title: str = "", padding: int = 20) -> ft.Container:
    """
    Contenedor visual de sección con fondo de tarjeta y borde.
    Opcionalmente muestra un título en negrita arriba del contenido.
    Se usa en el dashboard para "Actividad Reciente" y "Socios Recientes".
    """
    # Si se proporcionó un título, lo agrega arriba del contenido
    inner = ft.Column([
        ft.Text(title, color=Colors.TEXT_PRIMARY, size=15,
                weight=ft.FontWeight.BOLD) if title else ft.Container(),
        content,
    ], spacing=16 if title else 0)  # Espaciado adicional si hay título

    return ft.Container(
        content=inner,
        bgcolor=Colors.BG_CARD,
        border_radius=14,
        border=ft.border.all(1, Colors.BORDER),
        padding=padding,
    )


# =============================================================================
# LEVEL BADGE (badge de nivel para rutinas)
# =============================================================================

# Mapa de nivel → (color de texto, color de fondo translúcido)
LEVEL_COLORS = {
    "Principiante": (Colors.SUCCESS, "#22C55E20"),  # Verde — fácil
    "Intermedio":   (Colors.WARNING, "#22C55E20"),  # Amarillo — medio
    "Avanzado":     (Colors.DANGER,  "#22C55E20"),  # Rojo — difícil
}

def level_badge(nivel: str) -> ft.Container:
    """
    Badge de nivel de dificultad para las tarjetas de rutinas.
    Mismo estilo visual que status_badge pero para niveles de entrenamiento.
    """
    # Obtiene colores por nivel, o gris si el nivel no está en el mapa
    text_c, bg_c = LEVEL_COLORS.get(nivel, (Colors.TEXT_SECONDARY, "#7A809920"))
    return ft.Container(
        content=ft.Text(nivel, color=text_c, size=11, weight=ft.FontWeight.W_600),
        bgcolor=bg_c, border_radius=20,
        padding=ft.padding.symmetric(horizontal=10, vertical=4),
    )


# =============================================================================
# SNACKBAR HELPER
# =============================================================================

def show_snack(page: ft.Page, message: str, color: str = Colors.SUCCESS):
    """
    Muestra una notificación temporal (SnackBar) en la parte inferior de la pantalla.
    Usado para confirmar acciones (guardado, eliminado) o mostrar errores.
    El SnackBar desaparece automáticamente después de 3 segundos.
    Parámetros:
        message: Texto a mostrar en la notificación
        color:   Color de fondo — verde (éxito), rojo (error), naranja (advertencia)
    """
    page.snack_bar = ft.SnackBar(
        content=ft.Text(message, color=Colors.WHITE),
        bgcolor=color,
        duration=3000,  # Duración en milisegundos (3 segundos)
    )
    page.snack_bar.open = True  # Activa la visibilidad del snackbar
    page.update()               # Flet necesita update() para mostrar el cambio


# =============================================================================
# DIÁLOGO GENÉRICO DE CONFIRMACIÓN
# =============================================================================

def confirm_dialog(page: ft.Page, title: str, message: str, on_confirm=None) -> ft.AlertDialog:
    """
    Crea un diálogo modal de confirmación reutilizable.
    Muestra título, mensaje y dos botones: Cancelar y Confirmar.
    Al confirmar, ejecuta el callback `on_confirm` si fue proporcionado.
    Se usa principalmente para confirmar eliminaciones de registros.
    """
    dlg = ft.AlertDialog(
        modal=True,  # Bloquea la interacción con el resto de la UI mientras está abierto
        title=ft.Text(title, color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
        content=ft.Text(message, color=Colors.TEXT_SECONDARY),
        bgcolor=Colors.BG_CARD,
        actions=[
            # Botón cancelar — cierra el diálogo sin ejecutar nada
            ft.TextButton("Cancelar",
                          style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                          on_click=lambda e: close_dialog(page, dlg)),
            # Botón confirmar — cierra el diálogo Y ejecuta el callback
            ft.TextButton("Confirmar",
                          style=ft.ButtonStyle(color=Colors.ACCENT),
                          on_click=lambda e: (close_dialog(page, dlg), on_confirm and on_confirm())),
        ],
        actions_alignment=ft.MainAxisAlignment.END,  # Botones alineados a la derecha
    )
    return dlg


def open_dialog(page: ft.Page, dlg: ft.AlertDialog):
    """
    Agrega el diálogo al overlay de la página y lo marca como abierto.
    El overlay es la capa de Flet que muestra modales sobre el contenido.
    """
    page.overlay.append(dlg)  # Agrega el diálogo a la capa de overlays
    dlg.open = True            # Lo marca como visible
    page.update()              # Flet renderiza el cambio


def close_dialog(page: ft.Page, dlg: ft.AlertDialog):
    """
    Cierra el diálogo sin eliminarlo del overlay.
    Flet lo ocultará en el próximo update().
    """
    dlg.open = False  # Oculta el diálogo
    page.update()     # Flet renderiza el cambio
