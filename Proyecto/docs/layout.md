# Estructura Lógica — `layout.py` (Shell Principal)

Este documento mapea la estructura de `layout.py`, responsable de ensamblar el "caparazón" o *Shell* de la aplicación (barra lateral + área dinámica de contenido).

## Dependencias e Importaciones
*   `flet`: Framework de UI base.
*   `app.config`: Importa el namespace `Colors` (para el fondo del contenedor central).
*   `app.components.ui`: Importa la función `build_sidebar`.

## Funciones Principales

### `build_main_layout(page, router, active_route, content)`
*   **Propósito:** Construye y retorna la estructura principal en formato de fila (`ft.Row`), acoplando la navegación estática y el contenedor dinámico.
*   **Parámetros:**
    *   `page`: Objeto del lienzo principal.
    *   `router`: Instancia del enrutador global.
    *   `active_route`: (String) Identificador de la ruta actual (para marcar el botón activo).
    *   `content`: (ft.Control) El widget/árbol de UI que representa la vista solicitada.
*   **Variables Locales / Mutaciones:**
    *   **`content_ref`**: Instancia de `ft.Ref[ft.Container]()`. 
        *   *Crucial:* Se le pasa al `router.setup(content_ref)` para que el enrutador sepa exactamente qué contenedor debe mutar al navegar, sin recargar toda la fila.
    *   **`sidebar`**: Almacena el retorno de `build_sidebar(page, router, active_route)`.
    *   **`content_area`**: Instancia de `ft.Container`. Se le inyecta el `content_ref` y el `content` inicial.
*   **Retorno:** Devuelve el componente ensamblado listo para renderizar.
