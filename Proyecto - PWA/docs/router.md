# Estructura Lógica — `router.py` (Controlador de Navegación)

Este documento detalla la estructura de programación, dependencias y variables del archivo `router.py`. Este módulo actúa como el cerebro de navegación de la SPA (Single Page Application), gestionando el reemplazo de componentes en el layout principal y aplicando guardias de seguridad (middlewares) antes de los cambios de ruta.

## Dependencias e Importaciones
*   `flet` (Framework de UI base).
*   `app.config`: Provee el objeto `Routes` (enum/constantes) para referenciar las rutas por nombre de variable y no por strings quemados.
*   `app.state`: Provee `app_state`, el objeto de estado global que permite verificar la autenticación y permisos del usuario activo.
*   *(Imports Diferidos)*: Las vistas de la aplicación (`DashboardView`, `SociosView`, `PersonalView`, `RutinasView`, `NutricionView`, `UsuariosView`) y `show_login` se importan dentro de los métodos, no en la cabecera. 
    *   *Razón:* Esto previene problemas de dependencias circulares durante el parseo inicial del módulo, garantizando que el router pueda compilar antes de que las vistas estén listas.

## Variables Globales
*   **`_router_instance`**: Variable global de módulo (inicializada en `None`). 
    *   *Razón de creación:* Almacena la única instancia de la clase `Router` bajo el patrón Singleton. Permite que componentes profundos accedan a los métodos de navegación sin necesidad de un paso infinito de parámetros (prop drilling).

## Clase: `Router`

### Variables de Instancia (Propiedades)
Se inicializan en `__init__(self, page)`:
*   **`self.page`**: Referencia al objeto de la ventana/lienzo principal.
*   **`self._content_ref`**: Referencia (puntero reactivo) al contenedor principal donde se dibujarán las vistas. Empieza en `None`.
*   **`self._sidebar_ref`**: Referencia a la barra de navegación lateral. Empieza en `None`. *Razón:* Reservada para que el router pueda interactuar con el menú lateral (ej. resaltar el ítem activo en el futuro).
*   **`self._view_cache`**: (Diccionario) Vacío por defecto. *Razón:* Espacio de memoria preparado para almacenar instancias de vistas ya generadas y optimizar la navegación sin re-instanciar clases constantemente.
*   **`self._view_map`**: (Diccionario) Vacío por defecto. Se poblará con la relación clave-valor entre la ruta destino y la clase que debe renderizarla.

### Métodos (Funciones)

#### `setup(self, content_ref, sidebar_ref=None)`
*   **Propósito:** Inyecta en el router las referencias a las partes dinámicas del layout principal, una vez que la pantalla "Shell" o contenedor principal ya fue construida.
*   **Variables mutadas:** Asigna `self._content_ref` y `self._sidebar_ref`, y ejecuta `self._register_views()`.

#### `_register_views(self)`
*   **Propósito:** Mapea las constantes de rutas con sus respectivas clases de renderizado.
*   **Variables mutadas:** Pobla `self._view_map` asignando `Routes.DASHBOARD` a `DashboardView`, etc.

#### `navigate(self, route)`
*   **Propósito:** Método principal expuesto para cambiar de pantalla. Incluye la lógica de *Guards* (protección de rutas).
*   **Parámetros:** `route` (String) identificador de la ruta a la que se desea ir.
*   **Lógica de Guards:**
    1.  *Autenticación:* Si `app_state.logged_in` es falso y la ruta solicitada no es `Routes.LOGIN`, cancela el proceso y llama a `self._go_login()`.
    2.  *Autorización (Roles):* Si la ruta solicitada es `Routes.USUARIOS` y `app_state.is_admin()` es falso, cancela la navegación silenciosamente.
*   **Variables mutadas:** Actualiza el estado global `app_state.current_route = route`. Finalmente llama a `self._render_view(route)`.

#### `_render_view(self, route)`
*   **Propósito:** Instanciar la vista solicitada e inyectarla en el layout principal.
*   **Variables Locales Creadas:**
    *   `view_class`: Recuperada de `self._view_map` usando el parámetro `route`.
    *   `view_instance`: Instancia de la clase recuperada, inyectándole `self.page` y `self` (router) como parámetros.
    *   `content`: El resultado (árbol de UI) de llamar al método `build()` de la instancia.
*   **Variables Mutadas:** Sobrescribe `self._content_ref.current.content` con el nuevo `content` y ordena al framework re-renderizar solo esa porción de la pantalla.

#### `_go_login(self)`
*   **Propósito:** Método privado para redirigir forzosamente a la pantalla de inicio de sesión cuando un usuario no autorizado intenta navegar. Llama a la función `show_login(self.page, self)`.

## Funciones Standalone

*   **`init_router(page)`**: Inicializa el sistema. Muta la variable global `_router_instance` creando un nuevo objeto `Router(page)` y lo devuelve. Se llama una única vez desde `main.py`.
*   **`get_router()`**: Función getter para recuperar `_router_instance` desde cualquier parte de la aplicación, habilitando navegación global sin inyección de dependencias estricta.
