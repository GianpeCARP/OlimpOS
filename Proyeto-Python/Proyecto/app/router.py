# =============================================================================
# router.py — Navegación centralizada con Flet
# =============================================================================
# El Router es el controlador central de navegación de OlimpOS.
# Sabe qué vistas existen, cuál mostrar y aplica reglas de seguridad (guards)
# antes de cada cambio de pantalla. Funciona actualizando el contenedor
# de contenido principal en lugar de reemplazar toda la página.

import flet as ft
from app.config import Routes   # Constantes de rutas para evitar strings sueltos
from app.state import app_state # Estado global — necesario para los guards


class Router:
    """
    Gestiona la navegación entre vistas.
    Usa el stack de contenido del layout principal para mostrar la vista activa.
    Preparado para integrar guards de autenticación y roles.
    """

    def __init__(self, page: ft.Page):
        self.page = page  # Referencia a la ventana principal de Flet

        # Referencia al Container central donde se renderiza la vista activa.
        # Se asigna en setup() una vez que el layout principal está construido.
        self._content_ref: ft.Ref | None = None

        # Referencia al sidebar (reservada para resaltar el ítem activo en futuras versiones).
        self._sidebar_ref: ft.Ref | None = None

        # Caché de vistas ya instanciadas. Actualmente no se usa (se re-instancia siempre),
        # pero está preparado para optimizar navegación en el futuro.
        self._view_cache: dict = {}

        # Diccionario que mapea cada ruta a su clase de vista.
        # Se llena en _register_views() con imports diferidos para evitar
        # dependencias circulares en el momento de importación del módulo.
        self._view_map: dict = {}

    # ── Setup ─────────────────────────────────────────────────────────────────

    def setup(self, content_ref: ft.Ref, sidebar_ref=None):
        """
        Registra las referencias del layout principal.
        Llamado desde login.py (_load_main_app) una vez que el shell
        (sidebar + contenedor) ya está agregado a la página.
        """
        self._content_ref = content_ref    # Referencia al área de contenido central
        self._sidebar_ref = sidebar_ref    # Referencia al sidebar (opcional)
        self._register_views()             # Mapea rutas a clases de vista

    def _register_views(self):
        """
        Registra las vistas disponibles usando imports diferidos (lazy imports).
        Los imports aquí evitan dependencias circulares: si se hicieran en el
        nivel superior del módulo, algunos archivos se cargarían antes de que
        sus dependencias estén disponibles.
        """
        from app.views.dashboard  import DashboardView
        from app.views.socios     import SociosView
        from app.views.personal   import PersonalView
        from app.views.rutinas    import RutinasView
        from app.views.nutricion  import NutricionView
        from app.views.usuarios   import UsuariosView

        # Mapeo ruta → clase de vista
        self._view_map = {
            Routes.DASHBOARD: DashboardView,
            Routes.SOCIOS:    SociosView,
            Routes.PERSONAL:  PersonalView,
            Routes.RUTINAS:   RutinasView,
            Routes.NUTRICION: NutricionView,
            Routes.USUARIOS:  UsuariosView,
        }

    # ── Navegación ────────────────────────────────────────────────────────────

    def navigate(self, route: str):
        """
        Navega a la ruta indicada aplicando guards de seguridad.
        Guards son verificaciones que se ejecutan ANTES de mostrar la vista:
          1. Guard de autenticación: si no hay sesión, redirige al login.
          2. Guard de roles: solo admins pueden acceder a la sección Usuarios.
        Si todos los guards pasan, actualiza el estado y renderiza la vista.
        """
        # Guard 1 — Autenticación
        # Si logged_in es False y se intenta navegar a cualquier ruta que no sea
        # el login, redirige al login automáticamente (protege toda la app).
        if not app_state.logged_in and route != Routes.LOGIN:
            self._go_login()
            return

        # Guard 2 — Roles
        # La sección de Usuarios solo es accesible para administradores.
        # Si un trainer intenta acceder directamente, se ignora la navegación.
        # TODO: mostrar un SnackBar con mensaje "Sin permisos suficientes".
        if route == Routes.USUARIOS and not app_state.is_admin():
            return

        # Actualiza la ruta activa en el estado global
        app_state.current_route = route

        # Instancia la vista correspondiente y la muestra en el contenedor central
        self._render_view(route)

    def _render_view(self, route: str):
        """
        Instancia (o recupera del caché) la vista y la muestra en el layout.
        Funciona actualizando el `.content` del Container referenciado,
        lo que hace que Flet re-renderice solo esa área sin rebuilding total.
        """
        # Si el contenedor de contenido no está disponible aún, sale silenciosamente
        if self._content_ref is None or self._content_ref.current is None:
            return

        # Obtiene la clase de vista desde el mapa de rutas
        view_class = self._view_map.get(route)
        if view_class is None:
            return  # Ruta desconocida — no hace nada

        # Instancia la vista pasándole la página y el router como dependencias
        view_instance = view_class(page=self.page, router=self)

        # Llama al método build() que retorna el árbol de controles Flet
        content = view_instance.build()

        # Reemplaza el contenido del área principal con la nueva vista
        self._content_ref.current.content = content

        # Notifica a Flet que debe actualizar el contenedor para renderizar el cambio
        self._content_ref.current.update()

    def _go_login(self):
        """
        Redirige al login reemplazando toda la página.
        Se usa cuando el guard de autenticación falla.
        """
        from app.views.login import show_login
        show_login(self.page, self)


# ── Instancia global ──────────────────────────────────────────────────────────
# Variable que almacena la instancia del router compartida en toda la app.
# Es None hasta que se llama a init_router() en main.py.
_router_instance: Router | None = None


def get_router() -> Router:
    """
    Retorna la instancia global del router.
    Útil si algún módulo necesita navegar sin tener referencia directa al router.
    """
    return _router_instance


def init_router(page: ft.Page) -> Router:
    """
    Crea e inicializa la instancia global del router.
    Solo se llama una vez desde main.py al arrancar la aplicación.
    Retorna el router para que main.py lo pase a show_login().
    """
    global _router_instance           # Modifica la variable global del módulo
    _router_instance = Router(page)   # Crea el router con la referencia a la página
    return _router_instance
