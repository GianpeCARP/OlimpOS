# Estructura: usuarios.py

## Ubicación original
`views/usuarios.py` — Gestión de usuarios del sistema (solo admin)

## Archivos que importa
- `app.config` → usa `Colors`
- `app.state` → usa `app_state` (no usa un getter específico, los datos están hardcodeados en este archivo)
- `app.components.ui` → usa `build_topbar()`, `status_badge()`, `primary_button()`, `input_field()`, `show_snack()`, `open_dialog()`, `close_dialog()`

## Constante: ROLE_CONFIG
Mapeo de rol del sistema a su representación visual:
```
"admin"   → ("Administrador", color ACCENT/naranja,   fondo "#FF572220", ícono SHIELD)
"trainer" → ("Entrenador",    color SUCCESS/verde,    fondo "#22C55E20", ícono FITNESS_CENTER)
"staff"   → ("Recepción",     color INFO/azul,        fondo "#3B82F620", ícono SUPPORT_AGENT)
"nutri"   → ("Nutricionista", color WARNING/amarillo, fondo "#F59E0B20", ícono RESTAURANT_MENU)
```

## Datos mock: _MOCK_SYSTEM_USERS
Lista hardcodeada (no viene de app_state):
```python
[
    {"id": 1, "nombre": "Administrador",  "username": "admin",   "role": "admin",   "estado": "Activo"},
    {"id": 2, "nombre": "Carlos Pérez",   "username": "trainer", "role": "trainer", "estado": "Activo"},
    {"id": 3, "nombre": "Roberto Silva",  "username": "rsilva",  "role": "staff",   "estado": "Activo"},
    {"id": 4, "nombre": "María Gómez",    "username": "mgomez",  "role": "nutri",   "estado": "Inactivo"},
]
```

## Clase: UsuariosView

### Constructor: __init__(page, router)
Guarda `self.page` y `self.router`.

### Método: build()
1. Usa `_MOCK_SYSTEM_USERS` como fuente de datos
2. **Topbar** — título "Usuarios", subtítulo "Gestión de accesos al sistema", botón "Nuevo Usuario"
3. **Banner de advertencia** — "Esta sección es exclusiva para administradores del sistema." Fondo `ACCENT_GLOW` con borde `ACCENT`.
4. **Tabla de usuarios** — header + filas con `_user_row()`
5. **Panel de permisos por rol** — muestra qué secciones puede ver cada rol

### Método: _user_row(u: dict)
Construye una fila de la tabla de usuarios.
- Keys del dict: `id`, `nombre`, `username`, `role`, `estado`
- Obtiene label/color/fondo/ícono de `ROLE_CONFIG`
- Layout: avatar (inicial, color del rol) con nombre + @username | chip de rol con ícono | badge de estado | 3 botones de acción:
  - Editar (azul INFO)
  - Resetear contraseña (amarillo WARNING)
  - Desactivar/Activar (rojo DANGER o verde SUCCESS según estado actual)
- Efecto hover con animación 120ms

### Método: _open_form(e, usuario=None)
Modal de crear/editar usuario.
- Campos: nombre (input con ref), username (input con ref), rol (dropdown: admin/trainer/nutri/staff, default "staff"), email (input)
- Solo en creación (no en edición): campo de contraseña inicial + aviso "El usuario deberá cambiar su contraseña al primer login"
- En edición: pre-carga nombre y username
- Acciones: Cancelar | Guardar

### Método: _save(dlg)
Cierra modal y muestra snack "Usuario guardado correctamente ✓".
```
# TODO: POST/PUT /api/usuarios
```

### Método: _reset_password(u: dict)
Modal de confirmación para resetear la contraseña de un usuario.
- Texto: "Se enviará un enlace de reseteo a {nombre}. El usuario deberá crear una nueva contraseña."
- Acciones: Cancelar | Confirmar → snack "Reseteo enviado a {nombre}"

## Función helper: _table_header()
Construye el header de la tabla con columnas: "Usuario" (expand 3), "Rol" (expand 2), "Estado" (expand 2), "Acciones" (expand 2). Fondo `Colors.BG_SIDEBAR`.

## Función helper: _perms_row(rol, cfg)
Construye una fila del panel de permisos por rol.
- Muestra el ícono del rol + nombre + chips de cada sección permitida
- Permisos por rol:
```
admin   → ["Dashboard", "Socios", "Personal", "Rutinas", "Nutrición", "Usuarios"]
trainer → ["Dashboard", "Socios", "Rutinas"]
nutri   → ["Dashboard", "Socios", "Nutrición"]
staff   → ["Dashboard", "Socios"]
```
