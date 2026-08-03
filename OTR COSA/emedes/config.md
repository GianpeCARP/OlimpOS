# Estructura Lógica — `config.py` (Configuración Global)

Este documento mapea la estructura de configuración del archivo `config.py`. Excluye los motivos estéticos y se centra estrictamente en los nombres de variables, constantes y estructuras de datos necesarias para que el sistema mantenga su integridad referencial.

## Dependencias e Importaciones
*   `flet`: Utilizado únicamente para inyectar los enumeradores de iconos en la configuración del menú.

## Constantes de Aplicación
Variables de alcance global para identificar el software y su versionado:
*   **`APP_NAME`**: (String) Nombre del sistema ("OlimpOS").
*   **`APP_VERSION`**: (String) Versión actual.

## Dimensiones (Constantes Numéricas)
Definen la geometría base de la ventana y el layout:
*   **`SIDEBAR_WIDTH`**: Ancho del menú lateral.
*   **`TOPBAR_HEIGHT`**: Alto de la barra superior.
*   **`WINDOW_WIDTH` / `WINDOW_HEIGHT`**: Tamaño de ventana por defecto.
*   **`WINDOW_MIN_W` / `WINDOW_MIN_H`**: Límites mínimos de redimensionamiento.

## Clases de Espacio de Nombres (Namespaces / Enums)
Agrupan constantes relacionadas. No se instancian, se usan sus atributos de clase directamente.

### `Colors`
Variables utilizadas en toda la UI. Los nombres deben mantenerse intactos para no romper la lógica de pintado en los componentes:
*   *Fondos:* `BG_DARK`, `BG_CARD`, `BG_GLASS`, `BG_SIDEBAR`, `BG_INPUT`.
*   *Acentos:* `ACCENT`, `ACCENT_LIGHT`, `ACCENT_DARK`, `ACCENT_GLOW`.
*   *Textos:* `TEXT_PRIMARY`, `TEXT_SECONDARY`, `TEXT_MUTED`.
*   *Estados:* `SUCCESS`, `WARNING`, `DANGER`, `INFO`.
*   *Bordes / Otros:* `BORDER`, `BORDER_FOCUS`, `WHITE`.

### `Fonts`
Nombres de las tipografías para uso global:
*   `TITLE`, `BODY`, `MONO`.

### `Routes`
Variables en formato String que definen los identificadores exactos de cada pantalla. Su uso evita errores tipográficos en el ruteo:
*   `LOGIN`, `DASHBOARD`, `SOCIOS`, `PERSONAL`, `RUTINAS`, `NUTRICION`, `USUARIOS`.

## Estructuras de Navegación
*   **`NAV_ITEMS`**: (Lista de Diccionarios). Define dinámicamente los botones que debe renderizar la barra lateral (Sidebar).
    *   *Estructura de cada diccionario:*
        *   `label`: Texto a mostrar en el botón.
        *   `icon`: Constante del ícono extraída del framework (`ft.Icons.*`).
        *   `route`: Destino asociado, extraído de la clase `Routes` (ej. `Routes.DASHBOARD`).
