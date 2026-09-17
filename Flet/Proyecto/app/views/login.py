# =============================================================================
# views/login.py — Vista de inicio de sesión
# =============================================================================
# Espejo de LoginView.tsx de la PWA: una sola tarjeta centrada sobre el fondo
# base, con el nombre de la app arriba, los dos campos y el botón volt a lo
# ancho. Se reemplazó el diseño anterior (panel verde neón partido a la mitad)
# porque usaba una paleta propia —siete colores hardcodeados en este archivo—
# que no existía en ninguna otra pantalla ni en la web.

import flet as ft
from app.config import (APP_NAME, MAX_INTENTOS_FALLIDOS, MINUTOS_CUENTA_TRABADA,
                        Colors, Fonts, Radius)
from app.state import app_state
from app.components.ui import input_field, primary_button


def _aviso_intentos(texto: str, ref=None, visible: bool = True) -> ft.Text:
    """Renglón gris con la regla de los intentos fallidos (gemelo del <p> muted de la PWA)."""
    return ft.Text(texto, ref=ref, color=Colors.TEXT_MUTED, size=11,
                   font_family=Fonts.BODY, visible=visible)


def _boton_ancho(btn: ft.Container) -> ft.Container:
    """Hace que un botón ocupe todo el ancho disponible de su fila."""
    btn.expand = True
    return btn


def show_login(page: ft.Page, router):
    """Reemplaza el contenido de la página con la pantalla de login."""

    username_ref = ft.Ref[ft.TextField]()
    password_ref = ft.Ref[ft.TextField]()
    error_ref    = ft.Ref[ft.Text]()
    aviso_ref    = ft.Ref[ft.Text]()

    def handle_login(e=None):
        u = (username_ref.current.value or "").strip().lower()
        # La contraseña NO se recorta: los espacios son parte de la contraseña.
        p = password_ref.current.value or ""

        if not u or not p:
            error_ref.current.value   = "Completá usuario y contraseña."
            error_ref.current.visible = True
            error_ref.current.update()
            return

        resultado = app_state.login(u, p)

        if not resultado["ok"]:
            error_ref.current.value   = resultado["mensaje"]
            error_ref.current.visible = True
            error_ref.current.update()
            # Como en LoginView.tsx: con una cuenta trabada el backend responde
            # lo mismo que con la contraseña mal (a propósito), así que sin este
            # aviso nadie entiende por qué la clave correcta "no anda".
            aviso_ref.current.visible = True
            aviso_ref.current.update()
            return

        error_ref.current.visible = False
        error_ref.current.update()
        page.on_keyboard_event = None

        # Credenciales correctas, pero la cuenta todavía tiene su contraseña
        # temporal: la API confirmó la clave y aun así no emitió token. No hay
        # sesión que cargar — el único camino es la pantalla de cambio.
        if resultado["requiere_cambio"]:
            show_cambiar_password(page, router)
        else:
            _load_main_app(page, router)

    def on_key(e: ft.KeyboardEvent):
        if e.key == "Enter":
            handle_login()

    page.on_keyboard_event = on_key

    # ── Tarjeta de login ─────────────────────────────────────────────────────
    card = ft.Container(
        width=420,
        bgcolor=Colors.SURFACE_CARD,
        border=ft.Border.all(1, Colors.BORDER_IDLE),
        border_radius=Radius.MD,
        padding=ft.Padding.all(32),
        content=ft.Column([
            # Nombre de la app, centrado y en tipografía de título
            ft.Container(
                content=ft.Text(APP_NAME, color=Colors.TEXT_MAIN, size=34,
                                weight=ft.FontWeight.W_800,
                                font_family=Fonts.TITLE,
                                text_align=ft.TextAlign.CENTER),
                alignment=ft.Alignment.CENTER,
                padding=ft.Padding.only(bottom=24),
            ),

            input_field("Usuario", "nombre de usuario",
                        icon=ft.Icons.PERSON_OUTLINE_ROUNDED,
                        ref=username_ref),
            ft.Container(height=2),
            input_field("Contraseña", "••••••••", password=True,
                        icon=ft.Icons.LOCK_OUTLINE_ROUNDED,
                        ref=password_ref),

            # Renglón de error — ocupa lugar sólo cuando hay algo que decir
            ft.Text(ref=error_ref, color=Colors.STATUS_DANGER, size=13,
                    font_family=Fonts.BODY, visible=False, value=""),
            _aviso_intentos(
                f"Después de {MAX_INTENTOS_FALLIDOS} intentos fallidos la cuenta queda "
                f"trabada {MINUTOS_CUENTA_TRABADA} minutos, aunque después pongas bien "
                "la contraseña. Esperá, o pedí que la desbloqueen desde Usuarios.",
                ref=aviso_ref, visible=False),

            ft.Container(height=10),
            # El botón va dentro de un Row con expand para que ocupe todo el
            # ancho de la tarjeta (equivale al width="100%" de la web).
            ft.Row([_boton_ancho(primary_button("Ingresar", on_click=handle_login))]),

            # Acá vivía el bloque de "Credenciales de prueba" con admin/admin123
            # y trainer/train123 a la vista. Se borró junto con _mock_users de
            # state.py cuando el login pasó a la API real: las cuentas ahora
            # son las de la base, y publicar credenciales en la pantalla de
            # ingreso de un sistema de gestión no va ni en desarrollo.
            ft.Container(
                content=ft.Text(
                    "Usá las credenciales que te dio el gimnasio.",
                    color=Colors.TEXT_SECONDARY, size=12,
                    font_family=Fonts.BODY, text_align=ft.TextAlign.CENTER,
                ),
                alignment=ft.Alignment.CENTER,
                padding=ft.Padding.only(top=24),
            ),
        ], spacing=8, tight=True),
    )

    page.controls.clear()
    page.add(
        ft.Container(
            expand=True,
            bgcolor=Colors.SURFACE_BASE,
            alignment=ft.Alignment.CENTER,
            content=card,
        )
    )
    page.update()


# =============================================================================
# CAMBIO DE CONTRASEÑA OBLIGATORIO
# =============================================================================
# Segunda pantalla del flujo de ingreso, y la única forma de salir del estado
# "credenciales correctas pero sin sesión".
#
# Se llega acá en tres casos, todos el mismo mecanismo: el primer ingreso del
# dueño (cuenta creada por el seeder), el primer ingreso de cualquier cuenta
# creada por el personal, y el reingreso después de que un admin resetee la
# clave. Por eso el subtítulo menciona los dos motivos.
#
# Al terminar NO entra al sistema: vuelve al login. Es deliberado — así el
# primer uso de la contraseña nueva es un login normal y queda probada.

LARGO_MINIMO_PASSWORD = 8


def show_cambiar_password(page: ft.Page, router):
    """Pantalla de cambio obligatorio. Espejo visual de la tarjeta de login."""

    actual_ref    = ft.Ref[ft.TextField]()
    nueva_ref     = ft.Ref[ft.TextField]()
    confirmar_ref = ft.Ref[ft.TextField]()
    error_ref     = ft.Ref[ft.Text]()

    def mostrar_error(texto: str):
        error_ref.current.value   = texto
        error_ref.current.visible = True
        error_ref.current.update()

    def handle_guardar(e=None):
        actual    = actual_ref.current.value or ""
        nueva     = nueva_ref.current.value or ""
        confirmar = confirmar_ref.current.value or ""

        if not actual or not nueva:
            return mostrar_error("Completá todos los campos.")

        # Las dos validaciones locales existen para no gastar un viaje al
        # servidor en errores que se detectan acá. El largo mínimo lo vuelve a
        # validar el backend igual (schemas.py), que es donde cuenta.
        if nueva != confirmar:
            return mostrar_error("Las contraseñas nuevas no coinciden.")

        if len(nueva) < LARGO_MINIMO_PASSWORD:
            return mostrar_error(
                f"La contraseña nueva necesita al menos {LARGO_MINIMO_PASSWORD} caracteres."
            )

        resultado = app_state.cambiar_password(actual, nueva)

        if not resultado["ok"]:
            return mostrar_error(resultado["mensaje"])

        page.on_keyboard_event = None
        show_login(page, router)

    def on_key(e: ft.KeyboardEvent):
        if e.key == "Enter":
            handle_guardar()

    page.on_keyboard_event = on_key

    card = ft.Container(
        width=420,
        bgcolor=Colors.SURFACE_CARD,
        border=ft.Border.all(1, Colors.BORDER_IDLE),
        border_radius=Radius.MD,
        padding=ft.Padding.all(32),
        content=ft.Column([
            ft.Text("Cambiá tu contraseña", color=Colors.TEXT_MAIN, size=24,
                    weight=ft.FontWeight.W_800, font_family=Fonts.TITLE),
            ft.Container(
                content=ft.Text(
                    "Es tu primer ingreso, o te resetearon la clave. "
                    "Definí una contraseña propia para continuar.",
                    color=Colors.TEXT_SECONDARY, size=13, font_family=Fonts.BODY,
                ),
                padding=ft.Padding.only(top=4, bottom=20),
            ),

            input_field("Contraseña actual", "la que te dieron", password=True,
                        icon=ft.Icons.LOCK_CLOCK_OUTLINED, ref=actual_ref),
            ft.Container(height=2),
            input_field("Contraseña nueva", "••••••••", password=True,
                        icon=ft.Icons.LOCK_OUTLINE_ROUNDED, ref=nueva_ref),
            ft.Container(height=2),
            input_field("Repetí la nueva", "••••••••", password=True,
                        icon=ft.Icons.LOCK_OUTLINE_ROUNDED, ref=confirmar_ref),

            ft.Text(ref=error_ref, color=Colors.STATUS_DANGER, size=13,
                    font_family=Fonts.BODY, visible=False, value=""),
            _aviso_intentos(
                "Cada error en la contraseña actual cuenta como un intento fallido: "
                f"a los {MAX_INTENTOS_FALLIDOS} la cuenta queda trabada "
                f"{MINUTOS_CUENTA_TRABADA} minutos."),

            ft.Container(height=10),
            ft.Row([_boton_ancho(primary_button("Guardar y volver al ingreso",
                                                 on_click=handle_guardar))]),
        ], spacing=8, tight=True),
    )

    page.controls.clear()
    page.add(
        ft.Container(
            expand=True,
            bgcolor=Colors.SURFACE_BASE,
            alignment=ft.Alignment.CENTER,
            content=card,
        )
    )
    page.update()


# =============================================================================
# CARGA DE LA APLICACIÓN PRINCIPAL
# =============================================================================

def _load_main_app(page: ft.Page, router):
    """
    Arma el shell (sidebar + contenido) después de un login exitoso.

    La pantalla inicial NO es siempre el Dashboard. Un Entrenador lo tiene en
    NINGUNO según la matriz de permisos, así que aterrizaba en una sección
    que no puede ver: el guard del router la rechazaba y quedaba mirando una
    pantalla en blanco apenas entraba. Se lo lleva a la primera sección que sí
    puede abrir, respetando el orden del menú.

    Y si no puede abrir NINGUNA —hoy el Profesor, que tiene cuenta pero su
    pantalla vive en la PWA— caía igual al Dashboard, que tampoco puede ver:
    entraba bien y se quedaba mirando una pantalla vacía. Ver SinSeccionesView.
    """
    from app.config import Routes
    from app.components.ui import build_sidebar

    content_ref = ft.Ref[ft.Container]()

    inicial = app_state.primera_seccion()

    if inicial is None:
        # Sin ninguna sección no hay ruta que fijar ni ítem que resaltar: el
        # sidebar va a salir sin nav (le queda el logo y el cerrar sesión).
        from app.views.sin_secciones import SinSeccionesView
        initial_content = SinSeccionesView(page=page, router=router).build()
        inicial = Routes.DASHBOARD  # sólo para que el sidebar tenga un activo
        app_state.current_route = inicial
    else:
        # La ruta activa se fija ANTES de construir el sidebar: así el ítem ya
        # nace resaltado y el hover sabe cuál no debe apagar.
        app_state.current_route = inicial

        vista_inicial = router.view_class(inicial)
        initial_content = vista_inicial(page=page, router=router).build()

    content_container = ft.Container(
        ref=content_ref,
        content=initial_content,
        expand=True,
        bgcolor=Colors.SURFACE_BASE,
    )

    sidebar = build_sidebar(page, router, inicial)

    shell = ft.Row([sidebar, content_container], spacing=0, expand=True)

    page.controls.clear()
    page.add(ft.Container(content=shell, expand=True, bgcolor=Colors.SURFACE_BASE))
    page.update()

    router.setup(content_ref)
