# Estructura: dashboard.py

## Ubicación original
`views/dashboard.py` — Vista principal del dashboard (pantalla de inicio tras login)

## Archivos que importa
- `app.config` → usa `Colors` (paleta global), `Routes` (rutas de navegación)
- `app.state` → usa `app_state` (estado global con datos mock)
- `app.components.ui` → usa `build_topbar()`, `stat_card()`, `section_card()`, `status_badge()`, `primary_button()`

## Constante: ACTIVITY_ICONS
Mapeo de tipo de actividad a su representación visual:
```
"nuevo_socio" → (ícono PERSON_ADD,       color INFO/azul)
"pago"        → (ícono ATTACH_MONEY,     color SUCCESS/verde)
"rutina"      → (ícono FITNESS_CENTER,   color ACCENT/naranja)
"vencimiento" → (ícono WARNING,          color WARNING/amarillo)
```

## Clase: DashboardView

### Constructor: __init__(page, router)
Guarda referencias a `page` (ventana) y `router` (navegación).

### Método: build() → retorna el árbol de controles

#### Datos que consume del estado global:
```
stats     = app_state.get_dashboard_stats()     # Dict con 4 métricas
actividad = app_state.get_actividad_reciente()  # Lista de 5 eventos
socios    = app_state.get_socios()[:4]          # Primeros 4 socios
```

#### Secciones que construye (en orden vertical):

1. **Topbar** — título "Dashboard", saludo con nombre del usuario, botón "Nuevo Socio"

2. **Stats row** — 4 tarjetas en fila horizontal:
   - Socios Activos (azul)
   - Ingresos Mensuales (verde)
   - Clases Hoy (naranja/accent)
   - Nuevos este Mes (amarillo)
   - Cada tarjeta recibe: título, valor, delta, tendencia, ícono, color

3. **Actividad reciente** — lista de ítems generados por `_activity_item()`, envuelta en `section_card`

4. **Fila inferior** — dos columnas:
   - Izquierda (expand): lista de socios recientes con `_socio_row()`
   - Derecha (ancho fijo 240px): panel de accesos rápidos con `_quick_btn()`

## Función helper: _activity_item(act: dict)
Construye un ítem del feed de actividad.
- Recibe dict con keys: `tipo`, `desc`, `hora`
- Layout: ícono con fondo translúcido | descripción + hora
- Línea divisoria inferior

## Función helper: _quick_btn(label, icon, color, on_click)
Construye un botón del panel de accesos rápidos.
- Layout: ícono cuadrado coloreado | texto | flecha derecha
- Efecto hover: cambia fondo a versión translúcida del color
- Animación de transición de 120ms

## Función helper: _socio_row(s: dict)
Construye una fila de socio reciente.
- Recibe dict con keys: `nombre`, `plan`, `estado`
- Layout: avatar circular con inicial | nombre + plan | badge de estado
- Línea divisoria inferior
