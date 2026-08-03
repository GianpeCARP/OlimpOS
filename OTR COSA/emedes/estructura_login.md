# Estructura: login.py

## Ubicación original
`views/login.py` — Vista de inicio de sesión

## Archivos que importa
- `app.config` → usa `APP_NAME` (nombre de la app para mostrar en pantalla)
- `app.state` → usa `app_state` (estado global: método `login(username, password)` y `get_user_name()`)
- `app.components.ui` → usa `input_field()`, `show_snack()`

## Variables de color locales (no vienen de config)
```
C_BG_PAGE    = "#040F09"    # Fondo de pantalla completa
C_CARD_BG    = "#0A1A10"    # Fondo del panel derecho (formulario)
C_LEFT_BG    = "#00D06A"    # Panel izquierdo: verde vibrante
C_TEXT_LEFT  = "#02301A"    # Texto oscuro sobre el panel verde
C_TEXT_RIGHT = "#E8F5E9"    # Texto claro sobre el panel oscuro
C_TEXT_MUTED = "#4A785B"    # Texto secundario/apagado
C_ACCENT     = "#00FF7F"    # Botones y detalles destacados
```

## Estructura de la pantalla
Layout de tarjeta central flotante (1300×700) con dos paneles lado a lado:

- **Panel izquierdo** (40% del ancho): fondo verde vibrante con logo, nombre de la app, slogan, tres features decorativas y copyright.
- **Panel derecho** (60% del ancho): fondo oscuro con formulario de login.

## Referencias (variables de estado del formulario)
```
username_ref  → campo de texto del usuario
password_ref  → campo de texto de la contraseña
error_ref     → texto de error (visible = false por defecto)
btn_ref       → contenedor del botón de login
```

## Función principal: show_login(page, router)
Reemplaza todo el contenido de la página con la vista de login.

### Flujo de login (handle_login):
1. Lee `username_ref` y `password_ref`, los trimea y pasa a minúsculas el user
2. Si alguno está vacío → muestra error "Es necesario completar todos los campos"
3. Llama a `app_state.login(username, password)` que retorna `(ok: bool, msg: str)`
4. Si `ok` es true → oculta el error, limpia el listener de teclado, llama a `_load_main_app()`
5. Si `ok` es false → muestra `msg` en el texto de error

### Listener de teclado:
- Tecla Enter ejecuta `handle_login()` (permite enviar el formulario sin click)

## Función: _feature_row(icon, text)
Helper que construye una fila decorativa para el panel izquierdo.
Layout: ícono en cuadrado redondeado semitransparente + texto.

## Función: _load_main_app(page, router)
Se ejecuta tras login exitoso. Carga la estructura principal de la app:
1. Importa `Routes`, `build_main_layout`, `DashboardView`
2. Crea el contenedor principal con ref (`content_ref`)
3. Construye el dashboard como vista inicial
4. Construye la sidebar con `build_sidebar()`
5. Ensambla sidebar + contenido en un Row horizontal
6. Configura el router con `router.setup(content_ref)`
7. Establece la ruta actual como `Routes.DASHBOARD`

## Credenciales mock de demostración
Se muestran en pantalla: `admin / admin123` y `trainer / train123`
