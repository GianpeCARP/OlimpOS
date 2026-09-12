# Estructura Lógica — `ui.py` (Librería de Componentes)

Este documento detalla la estructura del archivo `ui.py`. Excluye los detalles estéticos (colores, fuentes, paddings) para enfocarse estrictamente en los nombres de las funciones, sus parámetros, el manejo de estado local y la inyección de dependencias. 

## Dependencias e Importaciones
*   `flet`: Framework de UI base.
*   `app.config`: Importa constantes globales (`Colors`, `NAV_ITEMS`, `APP_NAME`, `SIDEBAR_WIDTH`, `TOPBAR_HEIGHT`).
*   `app.state`: Importa `app_state` (acceso a sesión para avatar, nombre de usuario y logout).

## Variables Globales del Módulo
*   **`_todos_los_botones`**: (Lista) Se inicializa vacía. 
    *   *Propósito:* Almacena referencias a los contenedores y textos de todos los botones de navegación generados. Es un mecanismo de estado local para lograr la mutación de UI (apagar/encender) sin recargar todo el sidebar.
*   **`STATUS_COLORS`**: (Diccionario) Mapea strings de estado ("Activo", "Vencido", etc.) con sus combinaciones de variables de color.
*   **`LEVEL_COLORS`**: (Diccionario) Mapea strings de nivel ("Principiante", "Intermedio", etc.) con variables de color.

## Funciones de Construcción (Componentes / Widgets)

### `build_sidebar(page, router, active_route)`
*   **Propósito:** Orquesta el ensamblado de la barra lateral (Logo + Menú + Footer).
*   **Lógica Interna:** Itera sobre la constante `NAV_ITEMS` y llama a `_nav_item()` por cada iteración.
*   **Funciones Anidadas:** 
    *   `handle_logout(e)`: Dispara `app_state.logout()` y redirige llamando a `show_login(page, router)`.

### `_nav_item(item, is_active, router)`
*   **Propósito:** Construye un botón de navegación individual.
*   **Mutaciones de Estado:** Inyecta un diccionario con las referencias de su UI (`container`, `indicator`, `icon`, `text`) dentro de la lista global `_todos_los_botones`.
*   **Funciones Anidadas (Eventos):**
    *   `on_hover(e)`: Muta variables visuales del botón evaluando el evento del puntero contra la ruta activa real (`app_state.current_route`).
    *   `on_click(e)`: 
        1. Actualiza `app_state.current_route`.
        2. Itera `_todos_los_botones` reseteando visualmente todos.
        3. Enciende visualmente el botón clickeado.
        4. Llama a `router.navigate(item["route"])`.

### `build_topbar(title, subtitle, actions)`
*   **Propósito:** Ensambla la cabecera dinámica de las vistas.
*   **Parámetros:** `title` (String), `subtitle` (String, opcional), `actions` (Lista de widgets, ej: botones de "Nuevo").

### `stat_card(title, value, delta, tendencia, icon, color)`
*   **Propósito:** Tarjeta de métricas para el Dashboard.
*   **Lógica Interna:** Evalúa si `tendencia` es `"up"` o `"down"` para definir mutaciones condicionales de íconos y variables (positivo/negativo).

### `status_badge(status)`
*   **Propósito:** Indicador tipo píldora.
*   **Lógica Interna:** Recupera los valores de la variable global `STATUS_COLORS` usando `.get()` y pasando valores por defecto.

### `primary_button(label, icon, on_click, width)`
*   **Propósito:** Botón de acción principal.
*   **Funciones Anidadas:** `on_hover(e)` (Mutación simple en respuesta al puntero).

### `input_field(label, hint, password, icon, ref, width)`
*   **Propósito:** Abstracción del campo de texto base (`ft.TextField`).
*   **Parámetros Clave:** Recibe e inyecta un `ref` (`ft.Ref`) permitiendo que las vistas padres capturen los datos introducidos sin manejar estados complejos.

### `section_card(content, title, padding)`
*   **Propósito:** Contenedor de agrupamiento lógico de información.

### `level_badge(nivel)`
*   **Propósito:** Similar a `status_badge` pero consume la variable `LEVEL_COLORS`.

## Funciones Auxiliares (Helpers y Diálogos)

### `show_snack(page, message, color)`
*   **Propósito:** Muta `page.snack_bar` instanciando un `ft.SnackBar`, fuerza su visibilidad (`open = True`) y ejecuta `page.update()`.

### `confirm_dialog(page, title, message, on_confirm)`
*   **Propósito:** Retorna (no abre) una instancia de `ft.AlertDialog`.
*   **Parámetros Clave:** `on_confirm` (Callback function). El botón de confirmación ejecuta una lambda que primero cierra el diálogo y luego evalúa y ejecuta el callback si existe.

### `open_dialog(page, dlg)`
*   **Propósito:** Inyecta el modal en `page.overlay`, cambia su bandera y repinta el DOM (`page.update()`).

### `close_dialog(page, dlg)`
*   **Propósito:** Cambia la bandera a falso y oculta el componente repintando el DOM.
