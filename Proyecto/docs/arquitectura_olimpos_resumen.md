# OlimpOS — Arquitectura del sistema (resumen conceptual)

Sistema de gestión para gimnasios. Este documento describe **la arquitectura y
las responsabilidades**, no la implementación. La versión original es Flet
(Python de escritorio); lo que sigue es agnóstico del framework, para poder
reconstruirlo en React u otro stack.

> **Nota de traducción:** al final de cada sección marco con **[Flet→React]**
> qué mecanismos son específicos de Flet y cómo se resuelven en React, para que
> no te lleves conceptos que no aplican.

---

## Arquitectura en capas

El sistema separa responsabilidades en capas, con una regla de dependencias
estricta: **configuración y estado no dependen de nadie; todo lo demás depende
de ellos; las vistas nunca se importan entre sí.**

```
Config ─┐
        ├─→ Componentes ─→ Vistas
Estado ─┘         ↑
              Navegación (conecta vistas sin que se conozcan entre sí)
```

### 1. Configuración
Centraliza todas las constantes: paleta de colores, tipografía, rutas de
navegación, ítems del menú lateral, dimensiones. **Nada está hardcodeado en los
componentes** — todo se importa desde acá. Cambiar un color se hace en un solo
lugar.

### 2. Estado global (fuente única de verdad)
Una sola instancia global guarda **la sesión del usuario** y **todos los datos**
(socios, personal, rutinas, etc.). Las vistas nunca guardan datos propios: los
piden a esta capa. Hoy los datos son mock; cada método está marcado para
reemplazarse por una llamada HTTP al backend.

Métodos principales: `login`, `logout`, `is_admin`, `get_user_name`,
`get_socios`, `get_personal`, `get_rutinas`, `get_planes_nutricion`,
`get_dashboard_stats`, `get_actividad_reciente`.

> **[Flet→React]** El "estado global singleton" en React es un Context +
> useReducer, o una store (Zustand/Redux). El concepto es idéntico: una sola
> fuente de verdad que las vistas consumen. La capa de datos mock async que
> definimos antes (carpeta `services/`) reemplaza a estos métodos.

### 3. Navegación (router con guards)
Controlador central de navegación. Antes de cada cambio de pantalla aplica dos
**guards de seguridad**:

- **Guard de autenticación:** si no hay sesión y la ruta no es login → redirige
  a login. Protege todas las vistas sin repetir código en cada una.
- **Guard de rol:** si la ruta es de admin y el usuario no es admin → ignora la
  navegación.

> **[Flet→React]** Esto es React Router. Los guards son "rutas protegidas"
> (un componente wrapper que checkea sesión/rol antes de renderizar).
> **Importante de seguridad:** estos guards son solo de UX — esconden pantallas.
> La seguridad real la impone el backend, que valida sesión y rol del lado del
> servidor. El front nunca es la barrera.

### 4. Componentes reutilizables (sistema de diseño)
Librería de widgets compartidos para consistencia visual. Todas las vistas los
consumen en vez de construir UI desde cero:

- `build_sidebar` — panel lateral con logo, menú (ítem activo resaltado), logout
- `build_topbar` — barra superior de cada sección (título, subtítulo, acciones)
- `stat_card` — tarjeta de métrica con valor grande, tendencia y color
- `status_badge` — píldora de estado (Activo/Vencido)
- `level_badge` — píldora de dificultad (Principiante/Intermedio/Avanzado)
- `primary_button` — botón de acción principal
- `input_field` — campo de texto estilizado (soporta password e ícono)
- `section_card` — contenedor tipo tarjeta con título opcional
- `show_snack` — notificación temporal
- `confirm_dialog` / `open_dialog` / `close_dialog` — modales

> **[Flet→React]** Esta es tu carpeta `components/`. Cada uno de estos es un
> componente React reutilizable. Los modales (open/close dialog) en React se
> manejan con estado local + un componente Modal, no con un "overlay de página".

### 5. Layout (shell)
Arma el shell de la app: sidebar fijo + área de contenido expandible. El
contenido cambia según la navegación; el sidebar permanece.

> **[Flet→React]** Es un layout con `<Outlet>` de React Router: el shell
> (sidebar) es fijo y solo cambia el contenido interno.

---

## Patrón de las vistas

Todas las vistas siguen el mismo molde:

- Reciben contexto (página + navegación) al construirse.
- Exponen un método que retorna su UI.
- **Obtienen datos del estado global, nunca los almacenan.**
- Usan componentes compartidos para construir la UI.
- Navegan a otras vistas a través del router, nunca importándose entre sí.

> **[Flet→React]** "Clase con método build()" → componente funcional React que
> retorna JSX. "Obtener datos del estado" → hook que consume el context/store.

### Las 7 vistas

| Vista | Qué hace |
|---|---|
| **Login** | Dos paneles: decorativo + formulario. Valida credenciales y carga el shell. |
| **Dashboard** | Bienvenida post-login: 4 métricas, feed de actividad, socios recientes, accesos rápidos. |
| **Socios** | Tabla con búsqueda en tiempo real, filtros (Todos/Activos/Vencidos), ordenamiento, alta/edición/baja. |
| **Personal** | Grilla de tarjetas de empleados (avatar, rol, turno). Alta/edición. |
| **Rutinas** | Catálogo en tarjetas con nivel, frecuencia, ocupación. Creación y detalle. |
| **Nutrición** | KPIs calóricos + tarjetas de planes con macros. Creación y detalle. |
| **Usuarios** | Solo admin. Gestión de accesos + matriz de permisos por rol. |

---

## Matriz de permisos por rol

| Rol | Acceso |
|---|---|
| **admin** | Todo |
| **trainer** (entrenador) | Dashboard, Socios, Rutinas |
| **nutri** (nutricionista) | Dashboard, Socios, Nutrición |
| **staff** (recepción) | Dashboard, Socios |

---

## Integración con backend (pendiente)

Cada método de datos del estado global reemplaza su mock por una llamada HTTP:

```
login()                → POST /api/auth/login
get_socios()           → GET  /api/socios
get_personal()         → GET  /api/personal
get_rutinas()          → GET  /api/rutinas
get_planes_nutricion() → GET  /api/nutricion
get_dashboard_stats()  → GET  /api/stats
get_actividad_reciente → GET  /api/actividad?limit=5
guardar socio/rutina/… → POST/PUT a su endpoint
reset password         → POST /api/usuarios/{id}/reset-password
```

---

## Conceptos de arquitectura que SÍ se trasladan

Independientes del framework, valen para React igual:

1. **Fuente única de verdad** para estado y datos.
2. **Config centralizada** — colores, rutas y constantes en un solo lugar.
3. **Componentes reutilizables** — no repetir UI.
4. **Vistas desacopladas** — no se conocen entre sí, se comunican por
   navegación y estado.
5. **Guards de navegación** — auth y rol, con la seguridad real en el backend.
6. **Capa de datos separada** — hoy mock, mañana HTTP, sin tocar las vistas.

## Mecanismos de Flet que NO se trasladan (se resuelven distinto en React)

- **Refs para leer/modificar controles** → en React se usa estado (useState), no
  referencias manuales a widgets.
- **Reemplazar `.content` de un container** → en React el re-render es
  automático cuando cambia el estado; no se manipula el árbol a mano.
- **Overlay de página para modales** → componente Modal con estado.
- **`lambda e, x=s:` para capturar variables de loop** → en React no existe ese
  bug; se pasa la variable directo en el map/JSX.
- **`ResponsiveRow` con `col={...}`** → en React es CSS grid/flex + Tailwind.
- **Colores hex de 8 dígitos para opacidad** → en React/Tailwind se usa
  `rgba()` o utilidades de opacidad.
