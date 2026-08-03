# Estructura: nutricion.py

## Ubicación original
`views/nutricion.py` — Gestión de planes nutricionales

## Archivos que importa
- `app.config` → usa `Colors`
- `app.state` → usa `app_state` (método `get_planes_nutricion()`)
- `app.components.ui` → usa `build_topbar()`, `primary_button()`, `input_field()`, `show_snack()`, `open_dialog()`, `close_dialog()`

## Constante: OBJETIVO_CONFIG
Mapeo de objetivo nutricional a su representación visual:
```
"Masa muscular"    → (color SUCCESS/verde,   fondo "#22C55E20", ícono TRENDING_UP)
"Bajar peso"       → (color DANGER/rojo,     fondo "#EF444420", ícono TRENDING_DOWN)
"Mantenimiento"    → (color INFO/azul,       fondo "#3B82F620", ícono TRENDING_FLAT)
"Alto rendimiento" → (color WARNING/amarillo, fondo "#F59E0B20", ícono BOLT)
```

## Clase: NutricionView

### Constructor: __init__(page, router)
Guarda `self.page` y `self.router`.

### Método: build()
1. Obtiene planes con `app_state.get_planes_nutricion()`
2. **Topbar** — título "Nutrición", conteo "{N} planes nutricionales", botón "Nuevo Plan"
3. **Resumen calórico** — 4 tarjetas de estadística (via `_cal_stat()`):
   - Promedio Cal.: `sum(cals) // len(cals)` kcal
   - Plan más bajo: `min(cals)` kcal
   - Plan más alto: `max(cals)` kcal
   - Total asignados: suma de `p["asignados"]` socios
4. **Grilla responsiva** de tarjetas de planes: 1 col mobile, 2 desktop

### Método: _plan_card(p: dict)
Construye la tarjeta de un plan nutricional.
- Keys del dict: `nombre`, `objetivo`, `calorias`, `asignados`
- Obtiene color/fondo/ícono de `OBJETIVO_CONFIG` con fallback gris
- Layout vertical:
  1. Ícono de objetivo + badge del objetivo
  2. Nombre del plan
  3. Calorías en número grande + "kcal/día"
  4. Divider
  5. Socios asignados + botón "Ver plan"
- Responsive: `col = {xs: 12, sm: 6}`

### Método: _open_form(e)
Modal de creación de plan nutricional.
- Campos: nombre (input), objetivo (dropdown con keys de OBJETIVO_CONFIG, default "Mantenimiento"), calorías diarias (input), fila triple de macros: proteínas/carbos/grasas en gramos (3 inputs lado a lado, ancho 130 cada uno), notas adicionales (textarea 3-4 líneas)
- Acciones: Cancelar | Crear Plan

### Método: _open_detail(p: dict)
Modal de detalle de un plan.
- Muestra: ícono+nombre del objetivo, calorías en grande, distribución de macros con barras de progreso (via `_macro_bar()`): Proteínas 30%, Carbohidratos 50%, Grasas 20%. Socios asignados.
- Acción: Cerrar

### Método: _save(dlg)
Cierra modal y muestra snack "Plan nutricional creado ✓".
```
# TODO: conectar con POST /api/nutricion
```

## Función helper: _cal_stat(label, value, icon, color)
Tarjeta de estadística compacta para el resumen superior.
Layout vertical: ícono en cuadrado redondeado | valor en negrita | label secundario.
`expand=True` para que las 4 compartan el ancho equitativamente.

## Función helper: _macro_bar(label, pct, color)
Barra de distribución de macronutriente.
- `pct`: float entre 0.0 y 1.0
- Layout: label (ancho fijo 110px) + porcentaje a la derecha, barra de progreso debajo
