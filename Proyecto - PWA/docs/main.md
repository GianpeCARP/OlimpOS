# Estructura Lógica — `main.py` (Punto de Entrada)

Este documento detalla la estructura de programación, dependencias y variables del archivo `main.py` del sistema OlimpOS. Debe usarse como referencia estricta para portar la lógica a otros lenguajes o frameworks, manteniendo los nombres y responsabilidades.

## Dependencias e Importaciones
El archivo requiere los siguientes módulos/archivos para funcionar:
*   `flet` (Framework de UI base).
*   `app.config`: Provee las constantes de configuración visual y de ventana (`APP_NAME`, `Colors`, `WINDOW_WIDTH`, `WINDOW_HEIGHT`, `WINDOW_MIN_W`, `WINDOW_MIN_H`).
*   `app.router`: Provee la función `init_router` para inicializar el singleton de navegación.
*   `app.views.login`: Provee la función `show_login` para renderizar el componente inicial.

## Funciones Principales

### `main(page)`
*   **Propósito:** Es la función de inicialización del ciclo de vida de la aplicación. Configura el contenedor principal (ventana o lienzo web), inyecta los estilos globales y dispara el primer renderizado.
*   **Parámetros:**
    *   `page`: Objeto que representa la ventana/lienzo principal proporcionado por el framework.

## Variables Utilizadas y Mutadas

Dentro de la función `main`, se modifican las propiedades del objeto `page` y se instancian variables locales para el flujo de la aplicación. Es crucial mantener estos nombres y asignaciones en la migración:

*   **`page.title`**: (String) Asignado con `APP_NAME`. Define el título de la ventana.
*   **`page.theme_mode`**: Forzado a modo oscuro.
*   **`page.bgcolor`**: Asignado con `Colors.BG_DARK`. Define el color de fondo general de la aplicación.
*   **`page.window.width` / `page.window.height`**: (Numérico) Asignados con `WINDOW_WIDTH` y `WINDOW_HEIGHT` para el tamaño inicial.
*   **`page.window.min_width` / `page.window.min_height`**: (Numérico) Asignados con `WINDOW_MIN_W` y `WINDOW_MIN_H` para evitar roturas de diseño al achicar la ventana.
*   **`page.padding` / `page.spacing`**: Asignados a `0` para eliminar márgenes por defecto del framework base y tener control manual del layout.
*   **`page.fonts`**: (Diccionario) Mapea nombres de fuentes ("Inter", "JetBrains Mono") con sus URLs de importación (Google Fonts).
*   **`page.theme`**: (Objeto Theme) Define el esquema de color general utilizando `Colors.ACCENT` como semilla y establece una densidad visual cómoda.
*   **`router`**: (Variable Local) Instanciada mediante la llamada a `init_router(page)`. Guarda la instancia global del enrutador. 
    *   *Razón de creación:* Se requiere capturar esta instancia en el inicio para inyectarla como dependencia hacia la primera vista de la aplicación, permitiendo que la navegación fluya a partir de allí.
