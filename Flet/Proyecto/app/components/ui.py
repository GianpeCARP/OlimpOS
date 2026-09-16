# =============================================================================
# components/ui.py — Librería de componentes de OlimpOS
# =============================================================================
# Cada función fabrica un widget Flet ya vestido con el sistema de diseño.
# Ninguna vista arma widgets "desde cero": todas reutilizan esto para que la
# app se vea consistente.
#
# ── Equivalencias con la PWA ────────────────────────────────────────────────
# Cada componente de acá es el gemelo de uno de React en
# src/frontend/src/components/ui/. Si tocás uno, mirá el otro:
#   build_sidebar   ↔ Sidebar.tsx        primary_button ↔ PrimaryButton.tsx
#   build_topbar    ↔ Topbar.tsx         input_field    ↔ InputField.tsx
#   stat_card       ↔ StatCard.tsx       section_card   ↔ SectionCard.tsx
#   status_badge    ↔ StatusBadge.tsx
#   filter_chip     ↔ FilterChip.tsx     show_snack     ↔ Snackbar.tsx
#   confirm_dialog  ↔ ConfirmDialog.tsx
# =============================================================================

import flet as ft
from app.config import (Colors, Fonts, Radius, alpha, NAV_ITEMS, APP_NAME,
                        SIDEBAR_WIDTH, TOPBAR_HEIGHT)
from app.state import app_state


# =============================================================================
# SIDEBAR
# =============================================================================

# Referencias a los botones del menú, para poder apagarlos todos al navegar.
# Se vacía en cada build_sidebar(): si no, cada reconstrucción del sidebar
# dejaba adentro los botones viejos —ya fuera de la página— y el bucle de
# apagado terminaba llamando .update() sobre controles muertos.
_todos_los_botones = []


def build_sidebar(page: ft.Page, router, active_route: str) -> ft.Container:
    """
    Barra de navegación lateral. Espejo de Sidebar.tsx: fondo un tono más
    claro que el lienzo, el ítem activo pintado de volt con texto oscuro, y
    abajo el nombre del usuario con el botón de cerrar sesión.
    """
    _todos_los_botones.clear()

    # Sólo las secciones que el rol puede abrir.
    #
    # Antes se dibujaban las nueve siempre. Con el backend real eso significa
    # que un Entrenador ve nueve ítems de los cuales siete le contestan que no
    # tiene acceso — la app se siente rota aunque esté haciendo exactamente lo
    # que debe. Esconderlas no es seguridad (el archivo está en el disco del
    # cliente y el que decide es el backend): es no ofrecer puertas cerradas.
    visibles = app_state.secciones_visibles()
    nav_items = [_nav_item(item, item["route"] == active_route, router)
                 for item in NAV_ITEMS if item["route"] in visibles]

    # ── Encabezado: nombre de la app ─────────────────────────────────────────
    # La PWA sólo pone el nombre en tipografía de título; acá se le suma el
    # logo, que es la única licencia que se toma respecto de la web (en
    # escritorio la marca ayuda a ubicar la ventana entre otras abiertas).
    logo_section = ft.Container(
        content=ft.Row([
            ft.Container(
                content=ft.Image(
                    src="logo-removebg-preview.png",
                    width=28, height=28, fit="contain",
                ),
                width=36, height=36,
                border_radius=Radius.SM,
                bgcolor=Colors.PRIMARY_VOLT,
                alignment=ft.Alignment.CENTER,
            ),
            ft.Text(APP_NAME, color=Colors.TEXT_MAIN, size=24,
                    weight=ft.FontWeight.W_800, font_family=Fonts.TITLE),
        ], spacing=12),
        padding=ft.Padding.only(left=24, right=24, top=22, bottom=22),
    )

    # ── Footer: usuario + logout ─────────────────────────────────────────────
    def handle_logout(e):
        from app.state import app_state as estado
        estado.logout()
        from app.views.login import show_login
        show_login(page, router)

    logout_btn = ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.LOGOUT_ROUNDED, color=Colors.TEXT_SECONDARY, size=18),
            ft.Text("Cerrar sesión", color=Colors.TEXT_SECONDARY, size=14,
                    font_family=Fonts.BODY),
        ], spacing=12),
        border_radius=Radius.SM,
        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
        on_click=handle_logout,
        animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
    )

    def logout_hover(e: ft.HoverEvent):
        """Hover: fondo de tarjeta y texto en rojo, igual que en la web."""
        entrando = str(e.data).lower() == "true"
        fila = logout_btn.content
        logout_btn.bgcolor = Colors.SURFACE_CARD if entrando else None
        color = Colors.STATUS_DANGER if entrando else Colors.TEXT_SECONDARY
        fila.controls[0].color = color
        fila.controls[1].color = color
        logout_btn.update()

    logout_btn.on_hover = logout_hover

    sidebar_footer = ft.Container(
        content=ft.Column([
            ft.Container(
                content=ft.Text(app_state.get_user_name(),
                                color=Colors.TEXT_SECONDARY, size=14,
                                font_family=Fonts.BODY),
                padding=ft.Padding.only(left=12, bottom=8),
            ),
            logout_btn,
        ], spacing=0),
        padding=ft.Padding.only(left=12, right=12, top=16, bottom=16),
        border=ft.Border.only(top=ft.BorderSide(1, Colors.BORDER_IDLE)),
    )

    return ft.Container(
        content=ft.Column([
            logo_section,
            ft.ListView(controls=nav_items, spacing=4, expand=True),
            sidebar_footer,
        ], spacing=0),
        width=SIDEBAR_WIDTH,
        height=page.window.height,
        bgcolor=Colors.SURFACE_HOVER,
        border=ft.Border.only(right=ft.BorderSide(1, Colors.BORDER_IDLE)),
    )


def _nav_item(item: dict, is_active: bool, router) -> ft.Container:
    """
    Ítem del menú lateral.

    Activo   → fondo volt + texto oscuro + semibold (es el estado más visible
               de toda la app, igual que en la PWA).
    Inactivo → texto secundario; en hover se aclara con fondo de tarjeta.
    """
    icon = ft.Icon(item["icon"],
                   color=Colors.SURFACE_BASE if is_active else Colors.TEXT_SECONDARY,
                   size=18)
    text = ft.Text(item["label"],
                   color=Colors.SURFACE_BASE if is_active else Colors.TEXT_SECONDARY,
                   size=14, font_family=Fonts.BODY,
                   weight=ft.FontWeight.W_600 if is_active else ft.FontWeight.NORMAL)

    def on_hover(e: ft.HoverEvent):
        # La ruta activa se lee del estado en vivo: el ítem activo no cambia
        # con el hover, sólo los demás.
        from app.state import app_state as estado
        if item["route"] == estado.current_route:
            return
        entrando = str(e.data).lower() == "true"
        e.control.bgcolor = Colors.SURFACE_CARD if entrando else None
        color = Colors.TEXT_MAIN if entrando else Colors.TEXT_SECONDARY
        icon.color = color
        text.color = color
        e.control.update()

    def on_click(e):
        from app.state import app_state as estado
        estado.current_route = item["route"]

        # Apaga todos los ítems y prende sólo el clickeado, sin reconstruir
        # el sidebar entero.
        for boton in _todos_los_botones:
            boton["container"].bgcolor = None
            boton["icon"].color = Colors.TEXT_SECONDARY
            boton["text"].color = Colors.TEXT_SECONDARY
            boton["text"].weight = ft.FontWeight.NORMAL
            boton["container"].update()

        e.control.bgcolor = Colors.PRIMARY_VOLT
        icon.color = Colors.SURFACE_BASE
        text.color = Colors.SURFACE_BASE
        text.weight = ft.FontWeight.W_600
        e.control.update()

        router.navigate(item["route"])

    contenedor = ft.Container(
        content=ft.Row([icon, text], spacing=12),
        bgcolor=Colors.PRIMARY_VOLT if is_active else None,
        border_radius=Radius.SM,
        padding=ft.Padding.symmetric(horizontal=12, vertical=9),
        margin=ft.Margin.only(left=12, right=12),
        on_hover=on_hover,
        on_click=on_click,
        animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
    )

    _todos_los_botones.append({
        "container": contenedor, "icon": icon, "text": text,
    })
    return contenedor


# =============================================================================
# TOPBAR
# =============================================================================

def build_topbar(title: str, subtitle: str = "", actions: list = None) -> ft.Container:
    """
    Barra superior de cada sección: título, subtítulo opcional y acciones a la
    derecha. Espejo de Topbar.tsx (misma altura, mismo padding, misma línea
    inferior de 1px).
    """
    izquierda = [
        ft.Text(title, color=Colors.TEXT_MAIN, size=24,
                weight=ft.FontWeight.BOLD, font_family=Fonts.TITLE),
    ]
    if subtitle:
        izquierda.append(
            ft.Text(subtitle, color=Colors.TEXT_SECONDARY, size=14,
                    font_family=Fonts.BODY)
        )

    return ft.Container(
        content=ft.Row([
            ft.Column(izquierda, spacing=0, tight=True),
            ft.Row(actions or [], spacing=12),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
           vertical_alignment=ft.CrossAxisAlignment.CENTER),
        height=TOPBAR_HEIGHT + 24,
        padding=ft.Padding.symmetric(horizontal=32, vertical=12),
        border=ft.Border.only(bottom=ft.BorderSide(1, Colors.BORDER_IDLE)),
    )


# =============================================================================
# STAT CARD
# =============================================================================

def stat_card(title: str, value, delta: str = "", tendencia: str = "up",
              icon: str = ft.Icons.INFO_ROUNDED, color: str = None,
              delta_es_bueno: bool = None) -> ft.Container:
    """
    Tarjeta de métrica del dashboard. Espejo de StatCard.tsx:
    título chico + ícono arriba, número grande en monoespaciada, y el delta
    abajo con su flecha.

    `delta_es_bueno` existe porque en la web hubo que separarlo de la
    dirección de la flecha: bajar 4 kg es una flecha hacia abajo pero es una
    buena noticia, y pintarla de rojo confundía.
    """
    color = color or Colors.PRIMARY_VOLT
    es_baja = tendencia == "down"
    bueno = delta_es_bueno if delta_es_bueno is not None else (not es_baja)

    controles = [
        ft.Row([
            ft.Text(title, color=Colors.TEXT_SECONDARY, size=14,
                    font_family=Fonts.BODY),
            ft.Icon(icon, color=color, size=18),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Container(height=8),
        # Monoespaciada sólo para métricas — DESIGN.md §6.
        ft.Text(str(value), color=Colors.TEXT_MAIN, size=30,
                weight=ft.FontWeight.BOLD, font_family=Fonts.MONO),
    ]

    if delta:
        controles.append(
            ft.Row([
                # Flechas diagonales, como los ArrowUpRight/ArrowDownRight de
                # la web (no las verticales, que se leen como "ordenar").
                ft.Icon(
                    ft.Icons.SOUTH_EAST_ROUNDED if es_baja else ft.Icons.NORTH_EAST_ROUNDED,
                    color=Colors.STATUS_OK if bueno else Colors.STATUS_DANGER,
                    size=14,
                ),
                ft.Text(delta,
                        color=Colors.STATUS_OK if bueno else Colors.STATUS_DANGER,
                        size=12, font_family=Fonts.BODY),
            ], spacing=4)
        )

    return ft.Container(
        content=ft.Column(controles, spacing=2),
        bgcolor=Colors.SURFACE_CARD,
        border_radius=Radius.MD,
        padding=20,
        border=ft.Border.all(1, Colors.BORDER_IDLE),
        expand=True,
    )


# =============================================================================
# STATUS BADGE
# =============================================================================

# Estado → color del texto. El fondo se calcula con alpha() al 10%, igual que
# el `${color}1A` de StatusBadge.tsx.
#
# Ojo: en la versión anterior varios estados tenían el fondo hardcodeado en
# verde ("#22C55E20") aunque el texto fuera rojo. Con alpha() eso no puede
# volver a pasar: el fondo siempre se deriva del mismo color del texto.
STATUS_COLORS = {
    # Socios
    "Activo":         Colors.STATUS_OK,
    "Por vencer":     Colors.STATUS_WARN,
    "Vencido":        Colors.STATUS_DANGER,
    "Suspendido":     Colors.STATUS_WARN,
    "Sin membresía":  Colors.TEXT_MUTED,
    "Dado de baja":   Colors.STATUS_DANGER,
    # Empleados / rutinas / dietas
    "Inactivo":       Colors.TEXT_MUTED,
    "Activa":         Colors.STATUS_OK,
    "Inactiva":       Colors.TEXT_MUTED,
    # Usuarios
    "Bloqueado":      Colors.STATUS_DANGER,
    # Inscripciones a actividades
    "Vencida":        Colors.STATUS_DANGER,
    "Cancelada":      Colors.TEXT_MUTED,
    # Pagos
    "Confirmado":     Colors.STATUS_OK,
    "Pendiente":      Colors.STATUS_WARN,
    "Cancelado":      Colors.TEXT_MUTED,
    "Reembolsado":    Colors.STATUS_WARN,
}


def status_badge(status: str) -> ft.Container:
    """Pastilla de estado. Cualquier estado no mapeado cae en gris neutro."""
    color = STATUS_COLORS.get(status, Colors.TEXT_MUTED)
    return ft.Container(
        content=ft.Text(status, color=color, size=12,
                        weight=ft.FontWeight.W_500, font_family=Fonts.BODY),
        bgcolor=alpha(color, 0.10),
        border_radius=20,
        padding=ft.Padding.symmetric(horizontal=12, vertical=4),
    )


# Acá vivía level_badge (Principiante/Intermedio/Avanzado). Se retiró el
# 2026-09-16 junto con su gemelo LevelBadge.tsx: el nivel era una etiqueta
# ambigua —el "intermedio" de uno es el "avanzado" de otro— y filtrar por ella
# no servía. Las rutinas se filtran por días por semana, que es un número con
# significado igual para todos.


# =============================================================================
# BOTONES
# =============================================================================

def primary_button(label: str, icon: str = None, on_click=None,
                   width: int = None, disabled: bool = False) -> ft.Container:
    """
    Botón de acción principal: fondo volt y texto OSCURO.

    El texto oscuro no es un capricho — el volt (#C6F135) es casi amarillo, y
    con texto blanco encima no se lee. Es la firma visual del producto y está
    igual en PrimaryButton.tsx.
    """
    contenido = []
    if icon:
        contenido.append(ft.Icon(icon, color=Colors.SURFACE_BASE, size=16))
    contenido.append(ft.Text(label, color=Colors.SURFACE_BASE, size=14,
                             weight=ft.FontWeight.W_600, font_family=Fonts.BODY))

    btn = ft.Container(
        content=ft.Row(contenido, spacing=8,
                       alignment=ft.MainAxisAlignment.CENTER, tight=True),
        bgcolor=Colors.PRIMARY_VOLT if not disabled else Colors.PRIMARY_DIM,
        border_radius=Radius.SM,
        height=40,
        width=width,
        padding=ft.Padding.symmetric(horizontal=20),
        on_click=None if disabled else on_click,
        animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
        opacity=0.5 if disabled else 1,
    )

    if not disabled:
        def on_hover(e: ft.HoverEvent):
            # La web usa hover:opacity-90; acá el equivalente literal.
            e.control.opacity = 0.9 if str(e.data).lower() == "true" else 1
            e.control.update()
        btn.on_hover = on_hover

    return btn


def secondary_button(label: str, icon: str = None, on_click=None,
                     width: int = None) -> ft.Container:
    """
    Botón secundario: sólo borde, sin relleno. Es el equivalente de los
    botones "Ver detalles" / "Cancelar" que en la PWA son un <button> con
    `border border-border-idle` y texto secundario.
    """
    contenido = []
    if icon:
        contenido.append(ft.Icon(icon, color=Colors.TEXT_SECONDARY, size=16))
    contenido.append(ft.Text(label, color=Colors.TEXT_SECONDARY, size=14,
                             font_family=Fonts.BODY))

    btn = ft.Container(
        content=ft.Row(contenido, spacing=8,
                       alignment=ft.MainAxisAlignment.CENTER, tight=True),
        border=ft.Border.all(1, Colors.BORDER_IDLE),
        border_radius=Radius.SM,
        height=40,
        width=width,
        padding=ft.Padding.symmetric(horizontal=16),
        on_click=on_click,
        animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
    )

    def on_hover(e: ft.HoverEvent):
        entrando = str(e.data).lower() == "true"
        e.control.bgcolor = Colors.SURFACE_HOVER if entrando else None
        for c in e.control.content.controls:
            c.color = Colors.TEXT_MAIN if entrando else Colors.TEXT_SECONDARY
        e.control.update()

    btn.on_hover = on_hover
    return btn


def icon_action(icon: str, tooltip: str = "", on_click=None,
                color_hover: str = None) -> ft.Container:
    """
    Botón de sólo ícono para las acciones de fila (editar, dar de baja,
    reactivar). En la web son los <button> chiquitos del final de cada fila.
    """
    color_hover = color_hover or Colors.TEXT_MAIN
    ico = ft.Icon(icon, color=Colors.TEXT_MUTED, size=16)

    btn = ft.Container(
        content=ico,
        border_radius=Radius.SM,
        padding=6,
        tooltip=tooltip,
        on_click=on_click,
        animate=ft.Animation(120, ft.AnimationCurve.EASE_OUT),
    )

    def on_hover(e: ft.HoverEvent):
        entrando = str(e.data).lower() == "true"
        e.control.bgcolor = Colors.SURFACE_HOVER if entrando else None
        ico.color = color_hover if entrando else Colors.TEXT_MUTED
        e.control.update()

    btn.on_hover = on_hover
    return btn


def filter_chip(label: str, activo: bool, on_click=None) -> ft.Container:
    """
    Chip de filtro (Todos / Activos / Vencidos). Espejo de FilterChip.tsx:
    activo = pastilla volt con texto oscuro; inactivo = sólo borde.
    """
    return ft.Container(
        content=ft.Text(
            label,
            color=Colors.SURFACE_BASE if activo else Colors.TEXT_SECONDARY,
            size=14, weight=ft.FontWeight.W_500, font_family=Fonts.BODY,
        ),
        bgcolor=Colors.PRIMARY_VOLT if activo else None,
        border=None if activo else ft.Border.all(1, Colors.BORDER_IDLE),
        border_radius=20,
        padding=ft.Padding.symmetric(horizontal=16, vertical=7),
        on_click=on_click,
        animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
    )


# =============================================================================
# CAMPOS DE FORMULARIO
# =============================================================================

def input_field(label: str, hint: str = "", password: bool = False,
                icon: str = None, ref: ft.Ref = None, width=None,
                value: str = "", multiline: bool = False) -> ft.TextField:
    """
    Campo de texto del sistema. Espejo de InputField.tsx.

    Cambio respecto de la versión anterior: el ancho ya no está clavado en
    420px ignorando el parámetro `width` — así el mismo campo sirve tanto para
    el login como para un formulario de dos columnas.
    """
    return ft.TextField(
        ref=ref,
        label=label,
        value=value,
        hint_text=hint,
        password=password,
        can_reveal_password=password,
        prefix_icon=icon,
        multiline=multiline,
        min_lines=3 if multiline else 1,
        color=Colors.TEXT_MAIN,
        text_size=14,
        label_style=ft.TextStyle(color=Colors.TEXT_SECONDARY, size=14,
                                 font_family=Fonts.BODY),
        hint_style=ft.TextStyle(color=Colors.TEXT_MUTED, size=14,
                                font_family=Fonts.BODY),
        bgcolor=Colors.SURFACE_CARD,
        border_color=Colors.BORDER_IDLE,
        focused_border_color=Colors.BORDER_ACTIVE,
        cursor_color=Colors.PRIMARY_VOLT,
        border_radius=Radius.SM,
        content_padding=ft.Padding.symmetric(horizontal=14, vertical=12),
        width=width,
    )


class _TelefonoCompuesto:
    """
    Lo que queda en el `ref` de un telefono_field: expone `.value` con el
    número COMPLETO ("+54 3415551234"), igual que un TextField. Así los
    formularios que leen `ref.current.value` no se enteran de que adentro hay
    un selector de país y un campo.
    """

    def __init__(self, pais: ft.Dropdown, numero: ft.TextField):
        self.pais = pais
        self.numero = numero

    @property
    def value(self) -> str:
        from app.telefono import unir_telefono
        return unir_telefono(self.pais.value, self.numero.value or "")


def telefono_field(label: str, hint: str = "", ref: ft.Ref = None,
                   value: str = "", icon: str = ft.Icons.PHONE_OUTLINED) -> ft.Row:
    """
    Teléfono con código de país. Gemelo de TelefonoField.tsx. El número se
    filtra mientras se tipea (sin letras). Ver app/telefono.py.
    """
    from app.telefono import PAISES, limpiar_numero_local, separar_telefono

    prefijo, numero = separar_telefono(value)
    pais = ft.Dropdown(
        label="País",
        options=[ft.dropdown.Option(key=pre, text=f"{bandera} {pre}")
                 for _, pre, bandera in PAISES],
        value=prefijo,
        width=120,
        color=Colors.TEXT_MAIN, bgcolor=Colors.SURFACE_CARD,
        border_color=Colors.BORDER_IDLE, focused_border_color=Colors.BORDER_ACTIVE,
        border_radius=Radius.SM,
    )
    campo = input_field(label, hint, icon=icon, value=numero)

    def filtrar(e):
        limpio = limpiar_numero_local(campo.value)
        if limpio != campo.value:
            campo.value = limpio
            campo.update()

    campo.on_change = filtrar
    fila = ft.Row([pais, ft.Container(content=campo, expand=True)], spacing=8,
                  vertical_alignment=ft.CrossAxisAlignment.START)
    compuesto = _TelefonoCompuesto(pais, campo)
    # ft.Ref guarda una referencia DÉBIL: si nadie más retiene al compuesto,
    # el recolector se lo lleva y el formulario lee None al guardar. Se cuelga
    # de la fila, que vive mientras viva el diálogo que la contiene.
    fila.data = compuesto
    if ref is not None:
        ref.current = compuesto
    return fila


def select_field(label: str, opciones: list, ref: ft.Ref = None,
                 value: str = None, width=None, on_change=None) -> ft.Dropdown:
    """
    Desplegable con el mismo vestido que input_field. Espejo de
    SelectField.tsx. `opciones` es una lista de strings o de tuplas
    (valor, etiqueta).

    Ojo con el nombre del callback: en Flet 0.84 el Dropdown NO tiene
    `on_change` —eso es del TextField—, el evento se llama `on_select`. Acá se
    recibe como `on_change` para que todas las funciones de este archivo se
    llamen igual desde las vistas, y se conecta al evento correcto adentro.
    """
    items = []
    for op in opciones:
        if isinstance(op, (tuple, list)):
            items.append(ft.dropdown.Option(key=str(op[0]), text=str(op[1])))
        else:
            items.append(ft.dropdown.Option(key=str(op), text=str(op)))

    return ft.Dropdown(
        ref=ref,
        label=label,
        value=value,
        options=items,
        color=Colors.TEXT_MAIN,
        text_size=14,
        label_style=ft.TextStyle(color=Colors.TEXT_SECONDARY, size=14,
                                 font_family=Fonts.BODY),
        bgcolor=Colors.SURFACE_CARD,
        border_color=Colors.BORDER_IDLE,
        focused_border_color=Colors.BORDER_ACTIVE,
        border_radius=Radius.SM,
        content_padding=ft.Padding.symmetric(horizontal=14, vertical=12),
        width=width,
        on_select=on_change,
    )


def search_field(hint: str = "Buscar…", ref: ft.Ref = None,
                 width=320, on_change=None) -> ft.TextField:
    """Buscador con lupa. En la web es el input con ícono Search embebido."""
    return ft.TextField(
        ref=ref,
        hint_text=hint,
        prefix_icon=ft.Icons.SEARCH_ROUNDED,
        color=Colors.TEXT_MAIN,
        text_size=14,
        hint_style=ft.TextStyle(color=Colors.TEXT_MUTED, size=14,
                                font_family=Fonts.BODY),
        bgcolor=Colors.SURFACE_CARD,
        border_color=Colors.BORDER_IDLE,
        focused_border_color=Colors.BORDER_ACTIVE,
        cursor_color=Colors.PRIMARY_VOLT,
        border_radius=Radius.SM,
        content_padding=ft.Padding.symmetric(horizontal=14, vertical=10),
        width=width,
        height=42,
        on_change=on_change,
    )


# =============================================================================
# CONTENEDORES
# =============================================================================

def section_card(content: ft.Control, title: str = "", padding: int = 20) -> ft.Container:
    """Contenedor de sección con borde y título opcional. Espejo de SectionCard.tsx."""
    if title:
        inner = ft.Column([
            ft.Text(title, color=Colors.TEXT_MAIN, size=18,
                    weight=ft.FontWeight.W_600, font_family=Fonts.TITLE),
            content,
        ], spacing=12)
    else:
        inner = content

    return ft.Container(
        content=inner,
        bgcolor=Colors.SURFACE_CARD,
        border_radius=Radius.MD,
        border=ft.Border.all(1, Colors.BORDER_IDLE),
        padding=padding,
    )


def empty_state(mensaje: str, icon: str = ft.Icons.INFO_OUTLINE_ROUNDED) -> ft.Container:
    """
    Estado vacío. La PWA nunca deja un panel en blanco: siempre explica por qué
    no hay nada ("Todavía no hay socios cargados").
    """
    return ft.Container(
        content=ft.Column([
            ft.Icon(icon, color=Colors.TEXT_MUTED, size=28),
            ft.Text(mensaje, color=Colors.TEXT_MUTED, size=14,
                    font_family=Fonts.BODY),
        ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        alignment=ft.Alignment.CENTER,
        padding=ft.Padding.symmetric(vertical=32),
    )


def divider_row() -> ft.Container:
    """Línea divisoria de 1px, la que separa filas dentro de una tarjeta."""
    return ft.Container(height=1, bgcolor=Colors.BORDER_IDLE)


def table_header(columnas: list) -> ft.Container:
    """
    Encabezado de tabla. `columnas` es una lista de (texto, expand) o de
    (texto, ancho_fijo) usando ancho como int negativo… mantenido simple:
    cada item es una tupla (texto, expand:int).
    """
    celdas = []
    for texto, peso in columnas:
        celdas.append(
            ft.Container(
                content=ft.Text(texto.upper(), color=Colors.TEXT_MUTED, size=11,
                                weight=ft.FontWeight.W_600, font_family=Fonts.BODY),
                expand=peso,
            )
        )
    return ft.Container(
        content=ft.Row(celdas, spacing=12),
        padding=ft.Padding.only(left=4, right=4, top=4, bottom=12),
        border=ft.Border.only(bottom=ft.BorderSide(1, Colors.BORDER_IDLE)),
    )


def avatar(texto: str, size: int = 36, bgcolor: str = None) -> ft.Container:
    """
    Avatar circular con iniciales. En la web es el mismo círculo volt con
    texto oscuro que aparece en Socios y en el Dashboard.
    """
    return ft.Container(
        content=ft.Text(texto[:2].upper(), color=Colors.SURFACE_BASE,
                        size=int(size * 0.36), weight=ft.FontWeight.BOLD,
                        font_family=Fonts.BODY),
        width=size, height=size,
        border_radius=size // 2,
        bgcolor=bgcolor or Colors.PRIMARY_VOLT,
        alignment=ft.Alignment.CENTER,
    )


# =============================================================================
# FEEDBACK (snackbar y diálogos)
# =============================================================================

def show_snack(page: ft.Page, message: str, color: str = None):
    """
    Notificación temporal. Espejo de Snackbar.tsx: fondo de tarjeta con borde
    y el TEXTO coloreado —no el fondo entero, que era lo que hacía la versión
    anterior y tapaba el mensaje cuando el color era claro.
    """
    color = color or Colors.STATUS_OK
    page.snack_bar = ft.SnackBar(
        content=ft.Text(message, color=color, size=14, font_family=Fonts.BODY),
        bgcolor=Colors.SURFACE_CARD,
        duration=3000,
    )
    page.snack_bar.open = True
    page.update()


def confirm_dialog(page: ft.Page, title: str, message: str,
                   on_confirm=None, texto_confirmar: str = "Confirmar") -> ft.AlertDialog:
    """
    Diálogo modal de confirmación. Espejo de ConfirmDialog.tsx: título en
    tipografía de título, mensaje en secundario, "Cancelar" plano a la
    izquierda y el botón principal volt a la derecha.
    """
    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text(title, color=Colors.TEXT_MAIN, size=18,
                      weight=ft.FontWeight.W_600, font_family=Fonts.TITLE),
        content=ft.Text(message, color=Colors.TEXT_SECONDARY, size=14,
                        font_family=Fonts.BODY),
        bgcolor=Colors.SURFACE_CARD,
        shape=ft.RoundedRectangleBorder(radius=Radius.MD),
        actions=[
            ft.TextButton(
                "Cancelar",
                style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                on_click=lambda e: close_dialog(page, dlg),
            ),
            primary_button(
                texto_confirmar,
                on_click=lambda e: (close_dialog(page, dlg),
                                    on_confirm() if on_confirm else None),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    return dlg


def form_dialog(page: ft.Page, title: str, campos: list,
                on_save=None, texto_guardar: str = "Guardar") -> ft.AlertDialog:
    """
    Diálogo de alta/edición reutilizable. Recibe una lista de controles ya
    construidos (input_field, select_field…) y los apila.

    Es el equivalente de los *FormModal.tsx de la web (SocioFormModal,
    EmpleadoFormModal, etc.): mismo contenedor, mismo par de botones al pie.
    """
    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text(title, color=Colors.TEXT_MAIN, size=18,
                      weight=ft.FontWeight.W_600, font_family=Fonts.TITLE),
        content=ft.Container(
            content=ft.Column(campos, spacing=14, tight=True,
                              scroll=ft.ScrollMode.AUTO),
            width=440,
        ),
        bgcolor=Colors.SURFACE_CARD,
        shape=ft.RoundedRectangleBorder(radius=Radius.MD),
        actions=[
            ft.TextButton(
                "Cancelar",
                style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                on_click=lambda e: close_dialog(page, dlg),
            ),
            primary_button(
                texto_guardar,
                on_click=lambda e: (close_dialog(page, dlg),
                                    on_save() if on_save else None),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    return dlg


def open_dialog(page: ft.Page, dlg: ft.AlertDialog):
    """Agrega el diálogo al overlay y lo abre."""
    page.overlay.append(dlg)
    dlg.open = True
    page.update()


def close_dialog(page: ft.Page, dlg: ft.AlertDialog):
    """Cierra el diálogo (Flet lo oculta en el próximo update)."""
    dlg.open = False
    page.update()
