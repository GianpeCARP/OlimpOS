# Estructura: rutinas.py

## Ubicación original
`views/rutinas.py` — Gestión de rutinas de entrenamiento

## Archivos que importa
- `app.config` → usa `Colors`
- `app.state` → usa `app_state` (método `get_rutinas()`)
- `app.components.ui` → usa `build_topbar()`, `level_badge()`, `primary_button()`, `input_field()`, `show_snack()`, `open_dialog()`, `close_dialog()`

## Clase: RutinasView

### Constructor: __init__(page, router)
Guarda `self.page` y `self.router`.

### Método: build()
1. Obtiene rutinas con `app_state.get_rutinas()`
2. **Topbar** — título "Rutinas", conteo "{N} rutinas disponibles", botón "Nueva Rutina"
3. **Grilla responsiva** de tarjetas: 1 col mobile, 2 tablet, 3 desktop

### Método: _rutina_card(r: dict)
Construye la tarjeta de una rutina.
- Keys del dict: `nombre`, `nivel`, `dias`, `duracion`, `asignados`
- Calcula progreso: `min(r["asignados"] / 35, 1.0)` — 35 es el máximo esperado
- Layout vertical:
  1. Ícono fitness + badge de nivel (via `level_badge()`)
  2. Nombre de la rutina
  3. Pills informativos: "{dias} días/sem" y "{duracion}" (via `_info_pill()`)
  4. Contador "Asignados: {N} socios"
  5. Barra de progreso (color ACCENT)
  6. Botones: "Ver detalles" (abre modal) | "Asignar" (snack próximamente)
- Responsive: `col = {xs: 12, sm: 6, md: 4}`

### Método: _open_form(e, rutina=None)
Modal de crear/editar rutina.
- Campos: nombre (input), nivel (dropdown: Principiante/Intermedio/Avanzado), días/semana (input), duración en min (input), descripción (textarea multilínea 3-5 líneas)
- Acciones: Cancelar | Crear Rutina

### Método: _open_detail(r: dict)
Modal de solo lectura con detalles de la rutina.
- Muestra: badge de nivel, frecuencia, duración, asignados, descripción genérica
- Acción: Cerrar

### Método: _save(dlg)
Cierra modal y muestra snack "Rutina creada correctamente ✓".
```
# TODO: conectar con POST /api/rutinas
```

## Función helper: _info_pill(icon, text)
Chip/pill compacto con ícono + texto. Fondo `Colors.BG_SIDEBAR`, bordes redondeados.

## Función helper: _detail_row(label, value)
Fila de detalle: label muted (ancho fijo 100px) a la izquierda, valor a la derecha.
