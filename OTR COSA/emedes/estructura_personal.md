# Estructura: personal.py

## Ubicación original
`views/personal.py` — Gestión del personal del gimnasio

## Archivos que importa
- `app.config` → usa `Colors`
- `app.state` → usa `app_state` (método `get_personal()`)
- `app.components.ui` → usa `build_topbar()`, `status_badge()`, `primary_button()`, `input_field()`, `show_snack()`, `open_dialog()`, `close_dialog()`

## Constante: TURNO_COLORS
Mapeo de turno a colores para el chip de horario:
```
"Mañana" → (color WARNING/amarillo, fondo "#453511")
"Tarde"  → (color INFO/azul,        fondo "#172554")
"Noche"  → (color "#A78BFA"/violeta, fondo "#334155")
```

## Constante: ROL_ICONS
Mapeo de rol a ícono:
```
"Entrenador"    → FITNESS_CENTER_ROUNDED
"Nutricionista" → RESTAURANT_MENU_ROUNDED
"Recepcionista" → SUPPORT_AGENT_ROUNDED
```

## Clase: PersonalView

### Constructor: __init__(page, router)
Guarda `self.page` y `self.router`.

### Método: build()
1. Obtiene personal con `app_state.get_personal()`
2. **Topbar** — título "Personal", subtítulo "{N} empleados activos", botón "Agregar Empleado"
3. **Grilla responsiva** de tarjetas: `xs:1 col, sm:2, md:3, lg:4`

### Método: _staff_card(p: dict)
Construye la tarjeta de un empleado.
- Keys del dict: `nombre`, `rol`, `turno`, `estado`
- Layout vertical:
  1. Avatar circular con inicial + badge estado (Activo/Inactivo)
  2. Nombre en negrita
  3. Rol con ícono correspondiente
  4. Chip de turno coloreado: ícono reloj + "Turno {turno}"
  5. Botones: "Editar" (abre modal) | "Contactar"
- Responsive: `col = {xs: 12, sm: 6, md: 4, lg: 3}`

### Método: _open_form(e, empleado=None)
Modal de crear/editar empleado.
- Campos: nombre (input con ref), rol (dropdown: Entrenador/Nutricionista/Recepcionista/Administrativo), turno (dropdown: Mañana/Tarde/Noche), email (input)
- En edición: pre-carga nombre, selecciona rol y turno del empleado
- Acciones: Cancelar | Guardar

### Método: _save(dlg)
Cierra modal y muestra snack "Empleado guardado correctamente ✓".
```
# TODO: conectar con POST /api/personal o PUT /api/personal/{id}
```
