# OlimpOS — contexto del proyecto

Sistema de gestión para un gimnasio. **Son dos aplicaciones del mismo producto**, no
dos productos distintos:

| App | Carpeta | Quién la usa | Stack |
|---|---|---|---|
| **PWA web** | `Proyecto/` | Los **socios**, desde el navegador | React + TypeScript + Vite + Tailwind |
| **App de escritorio** | `Proyeto-Python/Proyecto/` | El **personal** del gimnasio | Python + **Flet 0.84.0** |

> Ojo: la carpeta se llama `Proyeto-Python` (sin la "c"). No es un error de tipeo tuyo.

**Las dos tienen que verse casi idénticas.** Es una decisión del dueño del proyecto,
no una sugerencia. Ambas usan la paleta **"Kinetic Carbon"**.

---

## Regla de oro: la paleta está duplicada

El mismo set de colores vive en **dos archivos**. Si cambiás uno solo, las apps dejan
de ser la misma marca:

- PWA → `Proyecto/src/frontend/src/index.css` (bloque `@theme`) y `config.ts`
- Flet → `Proyeto-Python/Proyecto/app/config.py` (clase `Colors`)

Colores clave: fondo `#15171C`, tarjetas `#1C1F26`, acento **volt** `#C6F135`.
El volt es casi amarillo: **encima siempre va texto oscuro**, nunca blanco.

Cada componente de `app/components/ui.py` (Flet) declara en su comentario de qué
componente `.tsx` de la PWA es gemelo. Si tocás uno, mirá el otro.

---

## Estado actual

**Todo el front-end está hecho y funcionando** en las dos apps, con datos mock.

- La PWA tiene implementada la extensión completa de Actividades (planes por mes o
  por semana, clases sueltas, asistencia, cobros), según
  `Proyecto/especificacion_definitiva_actividades.md`.
- La app Flet tiene las mismas secciones que la PWA para el personal: Dashboard,
  Socios, Cobros, Asistencia, Personal, Rutinas, Nutrición, Actividades, Usuarios.

**Lo que falta es el backend.** Va a ser **Python + FastAPI** (decisión ya tomada, no
revisitar; no va a ser Node). Hasta entonces:

- Los datos salen de mocks en memoria: `services/mockDb.ts` (PWA) y `app/state.py` (Flet).
- Las acciones de escritura de las vistas nuevas de Flet (Cobros, Asistencia,
  Actividades) **tienen el diseño completo y están cableadas, pero no escriben nada**:
  cada una tiene su endpoint marcado con un comentario `TODO`.
- **Los permisos no están implementados.** El guard de roles del router de Flet está
  **comentado a propósito**, con la nota de que va reemplazado por la matriz de
  permisos de `config.ts` (5 roles × 3 niveles de acceso), no por un `is_admin()`
  booleano. **No lo "arregles" descomentándolo**: con él activo no se puede ni abrir
  la sección Usuarios para revisar su diseño.

---

## Trampas de Flet 0.84 (ya costaron tiempo — no repetirlas)

Todas se encontraron **corriendo la app**, no leyendo el código:

1. **`f"{color}20"` NO da transparencia.** Flet lee el hex de 8 dígitos como
   `#AARRGGBB` — con el alfa **adelante** — y corre los canales, así que sale un color
   completamente distinto (los íconos del dashboard se veían rojos). Usar el helper
   `alpha()` de `config.py`, que delega en `ft.Colors.with_opacity`.

2. **El `scroll` va en la Column INTERNA, nunca en la exterior.** Una
   `ft.Column([...], expand=True, scroll=AUTO)` con un hijo `expand=True` adentro hace
   que Flet **centre todo verticalmente** y la pantalla arranque con un hueco enorme
   arriba. Patrón correcto: topbar fijo + `Container(content=Column(..., scroll=AUTO,
   expand=True), expand=True)`.

3. **`ft.Dropdown` usa `on_select`**, no `on_change` (eso es del `TextField`).

4. **`page.fonts` necesita una URL a un archivo `.ttf`**, no a un CSS de Google Fonts.
   Con el CSS no carga ninguna fuente y todo cae en la del sistema.

5. **`assets_dir="assets"` es obligatorio** al arrancar o las imágenes por nombre
   suelto (el logo del sidebar) no se resuelven.

6. **Las APIs viejas ya están migradas**: se usa `ft.Padding / Border / Margin /
   BorderRadius` y `ft.run`, no `ft.padding / border / margin / border_radius` ni
   `ft.app`. La app arranca con **cero `DeprecationWarning`**; si aparece uno, algo se
   revirtió.

---

## Cómo verificar los cambios

**PWA** (desde `Proyecto/src/frontend`):
```bash
npx tsc --noEmit -p tsconfig.app.json   # ojo: SIN -p no compila nada y siempre da OK
npx oxlint src/
npx tsc --build --force
```

**Flet** (desde `Proyeto-Python/Proyecto`):
```bash
python -m compileall -q app main.py
```
Flet abre una ventana nativa que no se puede screenshotear. Para revisarla visualmente,
lanzarla en el navegador:
```python
ft.run(main, view=ft.AppView.WEB_BROWSER, port=8551, assets_dir="assets")
```
Dos cosas del entorno: recargar muchas veces deja **sesiones Flet apiladas** y la
navegación parece rota sin estarlo (hard reload y una sola sesión); y el **aviso de
Chrome para guardar contraseña bloquea los clicks** de automatización.

Credenciales de prueba de la app Flet: `admin / admin123` y `trainer / train123`.

---

## Git: el proyecto Flet vive en DOS repos

- Monorepo (las dos apps) → `github.com/GianpeCARP/OlimpOS`
- Sólo el Flet → `github.com/GianpeCARP/Proyecto`

`Proyeto-Python/Proyecto` era un repo propio y **su `.git` está renombrado a
`.git.repo-viejo-backup`**. Si lo restaurás, el monorepo vuelve a verlo como submódulo
vacío y se rompe la subida. Para commitear y pushear ahí **sin restaurarlo**:

```bash
cd "D:/OlimpOs/Proyeto-Python/Proyecto"
export GIT_DIR="$PWD/.git.repo-viejo-backup" GIT_WORK_TREE="$PWD"
git add <archivos-explicitos>    # NUNCA "git add -A": mete el .git.repo-viejo-backup entero
git commit -m "..."
git push origin main
```

---

## Cómo trabajar en este proyecto

- **Nada de regex multilínea sobre varios archivos a la vez.** Un reemplazo estructural
  aplicado a las 9 vistas de golpe rompió 4 archivos con `SyntaxError`. Los reemplazos
  de token simple sí son seguros. Para cambios de estructura: archivo por archivo, y
  compilar después de cada tanda.
- **Los comentarios explican el *por qué*, no el *qué*.** El código de este proyecto
  está muy comentado a propósito, y varios comentarios documentan desvíos deliberados
  respecto de la especificación. Mantené ese estilo y no borres esas notas.
- **Soft-delete siempre con los dos caminos**: baja *y* reactivación desde el principio.
- **Al cambiar el estado de una entidad, decidir qué pasa con todo lo que la referencia**
  (cascadas). Varios bugs reales salieron de ahí.
- La documentación en `Proyecto/docs/*.md` está **citada más de 100 veces desde los
  comentarios del código** como justificación de decisiones. No borrarla.

---

## Dónde está el historial detallado

Este archivo es el resumen. El detalle fino (bugs cerrados, auditorías, decisiones
puntuales) vive en la memoria de Claude Code:

```
C:\Users\Pardini\.claude\projects\D--OlimpOs-Proyecto\memory\
```

Esa memoria **sólo se carga si abrís la sesión parada en `D:\OlimpOs\Proyecto`**. Este
`CLAUDE.md`, en cambio, se levanta desde cualquier carpeta del repo. Si necesitás el
detalle de algo puntual, leé el archivo correspondiente de esa carpeta; no hace falta
leerla entera.
