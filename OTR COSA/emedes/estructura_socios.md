# Estructura: socios.py

## Ubicación original
`views/socios.py` — Gestión de socios del gimnasio (con filtrado activo)

## Archivos que importa
- `app.config` → usa `Colors`
- `app.state` → usa `app_state` (método `get_socios()`)
- `app.components.ui` → usa `build_topbar()`, `status_badge()`, `primary_button()`, `input_field()`, `show_snack()`, `open_dialog()`, `close_dialog()`, `confirm_dialog()`

## Clase: SociosView

### Constructor: __init__(page, router)
Variables de instancia:
```
self.sort_ascending = True        # True = A-Z, False = Z-A
self.page           = page
self.router         = router
self.search_ref     = Ref()       # Referencia al campo de búsqueda
self.table_ref      = Ref()       # Referencia a la columna que contiene la tabla
self.current_filter = "Todos"     # Filtro activo: "Todos" | "Activos" | "Vencidos"
self.search_row_ref = Ref()       # Referencia al Row de la barra de búsqueda + chips
```

### Método: build()
Construye la vista completa:
1. **Topbar** — título "Socios", conteo "{N} socios registrados", botón "Nuevo Socio"
2. **Barra de búsqueda** — input con búsqueda en tiempo real (`on_change → _on_search`) + 3 chips de filtro ("Todos", "Activos", "Vencidos")
3. **Tabla de socios** — contenedor con ref para actualizar dinámicamente

### Método: _build_filter_chip(label)
Construye un chip de filtro interactivo.
- Determina colores según si es el filtro activo (`self.current_filter == label`)
- Al hacer click: actualiza `self.current_filter`, redibuja los 3 chips, y llama `_update_table()`

### Método: _update_table()
Lógica central de filtrado y ordenamiento:
1. Lee el texto de búsqueda del campo
2. Obtiene todos los socios de `app_state.get_socios()`
3. Filtra por texto (busca en `nombre` y `plan`, case-insensitive)
4. Filtra por estado según `self.current_filter`
5. Ordena alfabéticamente según `self.sort_ascending`
6. Reemplaza el contenido de `self.table_ref` con la tabla reconstruida

### Método: _on_search(e)
Callback de cada keystroke en el campo de búsqueda. Llama a `_update_table()`.

### Método: _toggle_sort(e)
Alterna `self.sort_ascending` y llama a `_update_table()`.

### Método: _build_table(socios: list)
Construye la tabla completa:
- **Header**: columnas "Nombre" (clickeable para ordenar, con ícono SORT), "Plan", "Estado", "Vence", "Acciones". Color de header: `Colors.SUCCESS`.
- **Filas**: una por socio, generadas con `_table_row()`

### Método: _table_row(s: dict)
Construye una fila de la tabla.
- Keys del dict: `nombre`, `plan`, `estado`, `vence`
- Layout: avatar (inicial) | nombre | plan | badge estado | fecha vence | botones editar/eliminar
- Efecto hover: cambia bgcolor a `Colors.BG_INPUT`
- Animación de 120ms

### Método: _open_form(e, socio=None)
Modal de crear/editar socio.
- Campos: nombre (con ref), plan (dropdown: Básico/Premium/Anual), email, teléfono
- En edición: pre-carga el nombre y selecciona el plan actual
- Acciones: Cancelar | Guardar

### Método: _save_socio(dlg)
Cierra el modal y muestra snack "Socio guardado correctamente ✓".
```
# TODO: conectar con POST /api/socios o PUT /api/socios/{id}
```

### Método: _confirm_delete(socio)
Muestra `confirm_dialog` preguntando "¿Estás seguro de eliminar a {nombre}?"
- Al confirmar: muestra snack "{nombre} eliminado"
