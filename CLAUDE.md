# OlimpOS — contexto del proyecto

> ## ⚠️ ACTUALIZACIÓN 2026-09-12 — LEER ESTO PRIMERO (supersede lo de abajo)
>
> Hubo dos cambios grandes que dejan desactualizadas varias partes de este
> archivo. Lo que sigue manda sobre cualquier cosa que lo contradiga más abajo:
>
> **1. Reorganización de carpetas.** La raíz ahora es:
> ```
> D:\OlimpOs\
> ├── backend/            API FastAPI (una sola, para las dos apps)
> ├── db/                 schema.sql + seed.sql DEFINITIVOS (compartidos)
> ├── docs/               guías, RESUMEN, dbml, PDF, vulnerabilidades; docs/specs/
> ├── Flet/Proyecto/      app de escritorio (Flet) — antes Proyeto-Python/Proyecto
> ├── Proyecto - PWA/     la PWA React — antes Proyecto/  (adentro: src/, docs/, openspec/)
> └── CLAUDE.md
> ```
> Sustituciones a aplicar mentalmente en TODO este archivo:
> `Proyeto-Python/Proyecto` → `Flet/Proyecto`; la PWA `Proyecto/` → `Proyecto - PWA/`;
> el DDL `Proyecto/db/schema.sql` → `db/schema.sql`. Se eliminó `Proyecto - PWA/db/`
> (schema/seed viejos + migrations): la fuente de verdad es `db/`.
>
> **2. Esquema de base NUEVO (41 tablas, no 37).** Neon se reconstruyó desde cero
> con `db/schema.sql` + `db/seed.sql` y el backend se sincronizó. Cambios de fondo:
> - **NO existe la tabla `Deuda`** (ni router, ni `deudas.py`, ni `generar_deudas`).
>   El estado "debe" se DERIVA de no tener membresía vigente. Prepago puro.
> - **`clases_restantes` no se guarda**: se cuenta `Reserva` (ver `clases_restantes_de`
>   en `routers/actividades.py`). Cancelar libera la clase por dejar de contar.
> - **Promoción sólo porcentual** (se eliminó el monto fijo) y se movió de `Membresia`
>   a **`Pago`** (`id_promocion` + `monto_descuento`).
> - **Clase suelta = un `Plan_Actividad` con `tipo_limite=CLASE_SUELTA`**, no una
>   columna `precio_clase_suelta` de Actividad.
> - Contacto de emergencia → tabla `Contacto_Emergencia`; franja del recepcionista →
>   FK `Franja_Laboral`; `Comida` obligatoriamente del `Catalogo_Comida`.
> - `Congelamiento` cuelga de la membresía (sin `id_socio`), con `origen`; los días se
>   derivan de las fechas. Nuevas tablas: `Contacto_Emergencia`, `Franja_Laboral`,
>   `Registro_Ejercicio`, `Catalogo_Comida`, `Registro_Comida`.
>
> **Estado**: backend sincronizado, booteando, con las **8 suites en verde**
> (`test_deudas` se retiró: probaba una feature eliminada). **Flet y PWA todavía NO
> están adaptados** a estos cambios de contrato — es lo que queda pendiente.
> El detalle del recorrido está en `docs/RESUMEN-PARA-CLAUDE-CODE.md`.

---

Sistema de gestión para un gimnasio. **Son dos aplicaciones del mismo producto**, no
dos productos distintos:

| App | Carpeta | Quién la usa | Stack |
|---|---|---|---|
| **PWA web** | `Proyecto - PWA/` | Los **socios**, desde el navegador | React + TypeScript + Vite + Tailwind |
| **App de escritorio** | `Flet/Proyecto/` | El **personal** del gimnasio | Python + **Flet 0.84.0** |

**Las dos tienen que verse casi idénticas.** Es una decisión del dueño del proyecto,
no una sugerencia. Ambas usan la paleta **"Kinetic Carbon"**.

---

## Regla de oro: la paleta está duplicada

El mismo set de colores vive en **dos archivos**. Si cambiás uno solo, las apps dejan
de ser la misma marca:

- PWA → `Proyecto - PWA/src/frontend/src/index.css` (bloque `@theme`) y `config.ts`
- Flet → `Flet/Proyecto/app/config.py` (clase `Colors`)

Colores clave: fondo `#15171C`, tarjetas `#1C1F26`, acento **volt** `#C6F135`.
El volt es casi amarillo: **encima siempre va texto oscuro**, nunca blanco.

Cada componente de `app/components/ui.py` (Flet) declara en su comentario de qué
componente `.tsx` de la PWA es gemelo. Si tocás uno, mirá el otro.

---

## Estado actual

**Las dos apps están terminadas y funcionando contra la API real.**

- La PWA tiene implementada la extensión completa de Actividades (planes por mes o
  por semana, clases sueltas —ahora como plan `CLASE_SUELTA`—, asistencia, cobros).
- **Historial médico** (patologías) en las dos apps: catálogo compartido y
  condiciones por socio. Del lado del personal cuelga de Socios; del lado del
  socio, de "Mi perfil" (`MisCondicionesCard`), donde él mismo puede
  declararlas. El botón se **omite** —no se deshabilita— para quien no tenga la
  acción `verHistorialMedico`: uno gris que no responde igual delata que el
  socio tiene algo cargado.
- **Entrenador a cargo** en las dos: se admiten VARIOS a la vez (uno de
  musculación y otro de funcional es normal, no un error de datos) y las
  finalizadas quedan en el historial. En la PWA el socio lo ve en "Mi rutina"
  (`MiEntrenadorCard`).
- **Circuito de ejercicios** en la PWA: el socio toca "Comenzar entrenamiento"
  en Mi rutina y la pantalla lo lleva ejercicio por ejercicio con el descanso
  cronometrado. **Todo del lado del cliente** —no toca el backend— porque un
  cronómetro que necesita servidor falla justo cuando el wifi del gimnasio anda
  mal. Es un MODO de Mi rutina y no una sección ni una ruta: como estado, el
  botón de atrás del celular no puede sacarte en medio de una serie.
- **Promociones** en las dos, dentro de Cobros. Ojo con el reparto de permisos,
  que es el diseño y no un detalle: **listar** pide la sección COBROS (para que
  el Recepcionista pueda elegir una al cobrar) y **crear/editar/dar de baja**
  pide `GESTION_PROMOCIONES`, que sólo tiene el Dueño.
- La app Flet tiene diez secciones para el personal: Dashboard, **Recepción**,
  Socios, Cobros, Asistencia, Personal, Rutinas, Nutrición, Actividades, Usuarios.
  Recepción no tiene gemela en la PWA: es el panel del mostrador (próximos turnos,
  búsqueda por DNI, cobro en el acto) y es donde aterriza un Recepcionista al entrar,
  en vez del Dashboard.

**El backend ya existe** y las dos apps están cableadas contra él. Es **Python +
FastAPI** sobre Neon (decisión ya tomada, no revisitar; no va a ser Node), en
`backend/`, con **~135 endpoints** y **41 tablas** modeladas (ver el bloque de
actualización del 2026-09-12 arriba). El DDL (`db/schema.sql`) y Neon coinciden
nombre por nombre: si agregás una tabla en uno, va en el otro.

Las tres cosas que este archivo daba por pendientes YA NO LO ESTÁN, y conviene
saberlo porque las notas viejas pedían explícitamente no tocarlas:

- **No hay mocks.** `services/mockDb.ts` se borró del repo y `app/state.py` habla
  con `api_client.py`. Ningún dato sale de memoria.
- **Las escrituras de Flet escriben.** Las nueve vistas llaman a la API; ya no
  queda ningún `TODO` de cableado.
- **Los permisos SÍ están implementados, y el guard del router de Flet está
  ACTIVO.** La nota vieja decía "no lo arregles descomentándolo" y tenía razón
  *en su momento*: el guard era un `is_admin()` booleano que además moría en
  silencio. Esa precondición ya se cumplió — `app/permisos.py` es la tercera
  copia de la matriz (5 roles × 3 niveles) y ahora el guard avisa por qué
  bloquea. **Descomentarlo ya está hecho; volver a comentarlo sería el error.**

  Ojo con las COPIAS de la matriz: vive en tres lugares
  (`backend/permisos.py`, `app/permisos.py`, `config.ts`) y `check_permisos.py`
  verifica que digan lo mismo. Apareció una **cuarta**, escrita a mano en
  `app/views/usuarios.py`, que el chequeo no miraba porque no era una matriz
  sino una lista suelta — y estaba mal para los cuatro roles. Ahora se deriva.
  Si necesitás mostrar permisos en pantalla, **derivalos**; no los escribas.

Lo que sí falta está en `backend/BITACORA.md` **§13**: sólo Mercado Pago, y no
depende del código (falta el token, el secreto del webhook y una URL pública).
El trabajo de rendimiento está en la **§14**, y el circuito más todo lo de
mobile en la **§15**.
Los cuatro pendientes que listaba la §12 —UI de patologías, entrenador a cargo
en la PWA, `Promocion` sin usar y la divergencia de `Consulta_Cruzada`— están
cerrados.

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

7. **Que la app ARRANQUE no significa que se pueda ENTRAR ni NAVEGAR.** Tres
   bugs de esta familia llegaron hasta una demo, y los tres revientan al
   CONSTRUIR una vista con datos que el backend devuelve legítimamente:

   - `router.view_class()` devolvía `None` porque `router.setup()` —que
     registraba el mapa de rutas— se llamaba 18 líneas DESPUÉS de usarlo en
     `login.py`. `None(page=...)` → `'NoneType' object is not callable`, y el
     login de los **cuatro** roles roto.
   - El Dashboard hacía `delta_pct >= 0` con un delta que el backend manda en
     `None` cuando no hay mes anterior. Con base nueva, las cuatro métricas
     vienen en None: nunca abría.
   - Nutrición hacía `sum(cals)//len(cals)` sin planes cargados
     (`ZeroDivisionError`, y `min`/`max` un `ValueError`).

   Los tres sobrevivieron a `compileall`, a las 9 suites y a un arranque sin
   warnings, porque **las suites prueban el backend por HTTP y nunca instancian
   una vista de Flet**. Y los dos últimos ya estaban resueltos en la PWA: eran
   asimetrías entre gemelas, no decisiones. Antes de dar por buena una vista:

   ```bash
   python pruebas_vistas.py     # desde Flet/Proyecto
   ```

   Entra con cada rol y llama a `build()` de cada sección que ese rol ve (25
   combinaciones, segundos). Correla **también con la base vacía**: es donde
   estos tres se disparan, y lo que va a ver cualquiera que arranque de cero.

---

## La PWA en el teléfono (es donde se usa de verdad)

El portal del socio se usa en un celular parado en el gimnasio. Cuatro bugs
llegaron a producción por probarse siempre en pantalla grande, y **ninguno lo
detecta `tsc`, `oxlint` ni las suites** — son estilos que funcionan por
accidente cuando sobra ancho. Están cerrados; lo que sigue es para no
reabrirlos:

1. **`h-screen` (=`100vh`) MIENTE en iOS.** Incluye la barra de direcciones,
   que se esconde al scrollear, así que el final del contenido queda debajo de
   ella. Va **`100dvh`**, definido en `index.css` sobre `html/body/#root`; los
   contenedores heredan con `h-full`.
2. **`overscroll-behavior: none`** en `html/body` y `overscroll-contain` en el
   área de contenido. Sin eso, el gesto sigue de largo al documento y Safari lo
   toma como *pull-to-refresh*: la página se recarga sola. En el circuito eso
   es perder el progreso.
3. **Los botones llevan `shrink-0` + `whitespace-nowrap`.** Son flex items y
   `flex-shrink` vale 1: en pantalla angosta el contenedor los comprime por
   debajo de su contenido y les recorta la etiqueta (el bug se veía como un
   botón reducido a la letra "G").
4. **La sidebar es un cajón deslizante en mobile** (`fixed` + `translate`, con
   hamburguesa en el Topbar) y vuelve a ser columna desde `md`. Con 260px fijos
   dejaba ~120px de contenido en un teléfono.

> **Chrome en iOS es Safari por dentro.** Apple obliga a WebKit, así que
> probar "en otro navegador" del iPhone no descarta nada: para eso hay que ir a
> Android o a la compu.

> **Forzar el ancho de un CONTENEDOR no simula un teléfono.** Los media queries
> miran el VIEWPORT. Sirve para probar el ancho de un botón, no el layout.

**Los íconos** son cuatro archivos y no dos a propósito: un `maskable` lo
recorta el sistema a un círculo del 80%, así que su contenido debe caber en el
56% del lado — y un archivo que cumple eso se ve diminuto usado como icono
normal. Los `any` van transparentes; el de iOS va **con** fondo porque iOS
compone la transparencia sobre negro. Se regeneran con
`Proyecto - PWA/src/frontend/scripts/generar_iconos.ps1` desde el logo de
`Flet/Proyecto/assets/`.

**`devOptions` del plugin PWA queda APAGADO.** Sobre HTTP no habilita instalar
nada igual (hace falta contexto seguro) y el service worker cachea código viejo
en desarrollo. Para probar la instalación: celular por USB y *port forwarding*
en `chrome://inspect`, porque `localhost` sí es contexto seguro.

---

## Rendimiento: la base está lejos, y eso ordena todo

Medido, no estimado. La base es Neon en **sa-east-1 (São Paulo)**:

    SELECT 1 en una conexión YA abierta ......  44 ms   <- piso físico (RTT)
    Abrir una conexión NUEVA (TLS + auth) .... 825 ms   <- 19x

**El cuello de botella nunca es Python.** Durante una request el proceso está
esperando un socket, no calculando; reescribir esto en otro lenguaje daría los
mismos 44 ms. Las dos únicas palancas son **preguntar menos veces** y **no
esperar la respuesta**. (Por lo mismo el GIL no molesta: los hilos de precarga
y refresco esperan red.)

Cuatro cosas ya implementadas que **no hay que desarmar sin leer la §14**:

1. **El pool** (`backend/database.py`): `pool_recycle=240` + keepalives de TCP.
   Sin esto las conexiones mueren solas y una request cualquiera paga 825 ms —
   era el "a veces tarda 2 segundos de la nada".
2. **El latido** (`backend/main.py`): un `SELECT 1` cada 2 minutos en un hilo
   daemon. Neon (plan gratuito) **suspende el compute** tras unos minutos sin
   consultas y despertarlo cuesta segundos.
3. **Listados en lote, no en bucle.** `roles_de_persona()` toca 6 relaciones
   por fila: sin `selectinload`, `/usuarios` hacía 45 consultas para 8 cuentas.
   Y `/socios` usa `_listar_socios_en_lote` (nº fijo de consultas);
   `_a_socio_out` quedó sólo para el socio de a uno.
4. **Servir-y-refrescar en Flet** (`app/api_client.py`): se devuelve el caché al
   instante aunque esté vencido y se refresca por atrás; el login precarga en
   paralelo. Un caché con TTL a secas **no alcanza** — se probó y reproducía la
   queja original (rápido dentro de la ventana, lento fuera).

> **Cualquier escritura invalida TODO el caché**, no sólo la ruta que tocó, y
> el logout también. Lo primero porque cobrar cambia cuatro rutas a la vez; lo
> segundo porque el caché guarda respuestas traídas con los permisos de la
> sesión anterior.

Recorrer los nueve paneles: **4175 ms → 19 ms**.

Si alguna vez hace falta bajar el piso de 44 ms, la palanca es **acercar la
base** (Postgres local ≈ 1 ms). No toca código: sólo `DATABASE_URL`.

---

## Cómo verificar los cambios

**Backend** (desde `backend/`). Ojo: usar SIEMPRE el Python del venv, no el
global — el global no tiene las dependencias y da errores que parecen bugs:
```bash
.venv/Scripts/python.exe -c "import main"          # compila Y ejecuta: compileall NO alcanza
.venv/Scripts/python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
.venv/Scripts/python.exe check_permisos.py         # las 3 copias de la matriz de permisos
```

**Las 9 suites de integración** viven en `backend/pruebas/`. No son unitarias:
corren contra Neon de verdad, con el backend levantado y **la base vacía**.
Cada una arma su propio escenario.

> **Antes de correr una suite, verificá contra QUÉ backend estás corriendo.**
> Un `uvicorn` que no pudo tomar el puerto 8000 muere en silencio y el proceso
> viejo sigue atendiendo: una corrida entera dio tres fallos falsos por eso. Se
> ve comparando la cantidad de endpoints:
> ```bash
> curl -s http://127.0.0.1:8000/openapi.json | .venv/Scripts/python.exe -c "import json,sys; print(len(json.load(sys.stdin)['paths']))"
> ```
```bash
.venv/Scripts/python.exe pruebas/test_una_sola_activa.py
.venv/Scripts/python.exe pruebas/test_patologias.py
.venv/Scripts/python.exe pruebas/test_entrenador_a_cargo.py
.venv/Scripts/python.exe pruebas/test_deudas.py
.venv/Scripts/python.exe pruebas/test_pago_online.py
.venv/Scripts/python.exe pruebas/test_portal_socio.py
.venv/Scripts/python.exe pruebas/test_mi_membresia.py
.venv/Scripts/python.exe pruebas/test_extension_congelamiento.py
.venv/Scripts/python.exe pruebas/test_promociones.py
```
Ojo: `test_extension_congelamiento` **no imprime** la línea "TODOS LOS CHEQUEOS
PASARON" — usa otro formato. Mirá su código de salida, no grepées el texto.

Entre suite y suite hay que **vaciar la base**, o la anterior le deja datos a la
siguiente y fallan por el escenario, no por un bug. Ya no se hace a mano:

```bash
.venv/Scripts/python.exe pruebas/vaciar_base.py        # muestra qué borraría
.venv/Scripts/python.exe pruebas/vaciar_base.py --si   # lo hace
```

La base "vacía" son 6 filas: Persona + Dueno del titular, Sede Central, 2 tipos
de membresía y la cuenta `dueno` (que nace con `debe_cambiar_password`, así que
el primer login pide cambiarla — la inicial está en `DUENO_INICIAL_PASSWORD` del
`.env`).

Con la base vacía **las pantallas no muestran nada**, así que para MIRARLAS hay
otro script, que no es una suite y no reemplaza a ninguna:

```bash
.venv/Scripts/python.exe pruebas/escenario_demo.py   # 4 empleados, 3 socios, patologías, promociones
```

Las contraseñas de esas cuentas —y de la del dueño— viven en
`backend/CONTRASEÑAS PARA TESTEO Y ACTUALIZADAS.txt`. **Anotá ahí toda cuenta
nueva**: el alta devuelve la contraseña temporal UNA sola vez.

> A los **5 intentos fallidos la cuenta se bloquea**, y el mensaje es idéntico
> al de una contraseña equivocada (a propósito, para no revelar el estado de una
> cuenta ajena). Desde afuera no se distingue, así que si el login falla y estás
> seguro de la clave, mirá la fila:
> `SELECT username, bloqueado, intentos_fallidos FROM "Usuario";`

> **Casi todos los bugs de este proyecto aparecieron CORRIENDO, no leyendo.**
> `python -m compileall` compila pero no ejecuta: un import faltante pasa el
> chequeo y revienta al arrancar. Y un nombre usado sólo dentro de una función
> tampoco lo detecta el import — eso ya mordió **tres** veces (la última:
> `input_field` en `views/cobros.py`).
>
> Dos continuaciones de la misma regla, las dos pagadas:
> - **Correr no alcanza si no verificás contra qué corrés** (el backend viejo en
>   el puerto 8000 dio tres fallos falsos).
> - **Que el proceso levante no significa que la pantalla funcione** (ver la
>   trampa 7 de Flet, más arriba).
>
> Para Python, un chequeo que sí encuentra los nombres sin importar: parsear el
> archivo con `ast` y comparar los `Name` cargados contra los importados y los
> ligados localmente. Es lo que cazó el `input_field`.
>
> En TypeScript, `tsc` tampoco alcanza para todo: un `useEffect` cuyo array de
> dependencias lee un `const` declarado más abajo compila perfecto y revienta en
> ejecución con un `ReferenceError` por TDZ (el array se evalúa DURANTE el
> render).

**PWA** (desde `Proyecto - PWA/src/frontend`):
```bash
npx tsc --noEmit -p tsconfig.app.json   # ojo: SIN -p no compila nada y siempre da OK
npx oxlint src/
npx tsc --build --force
```

**Flet** (desde `Flet/Proyecto`):
```bash
python -m compileall -q app main.py   # NO alcanza: ver la trampa 7
python pruebas_vistas.py              # build() de cada vista con cada rol
```
`compileall` no ejecuta nada, así que aprueba un nombre sin importar y una
división por cero que sólo pasan al abrir la pantalla. `pruebas_vistas.py` es lo
que cubre ese hueco; necesita el backend levantado y las cuentas del escenario
de demo.
Flet abre una ventana nativa que no se puede screenshotear. Para revisarla visualmente,
lanzarla en el navegador:
```python
ft.run(main, view=ft.AppView.WEB_BROWSER, port=8551, assets_dir="assets")
```
Dos cosas del entorno: recargar muchas veces deja **sesiones Flet apiladas** y la
navegación parece rota sin estarlo (hard reload y una sola sesión); y el **aviso de
Chrome para guardar contraseña bloquea los clicks** de automatización.

Credenciales: **`admin/admin123` y `trainer/train123` YA NO EXISTEN.** Eran de
la época de los datos en memoria y no hay ninguna cuenta así en la base. Las
reales están en `backend/CONTRASEÑAS PARA TESTEO Y ACTUALIZADAS.txt`.

Para verla en el navegador **no toques `main.py`**: usá el envoltorio que ya
está hecho, `scripts/lanzar_flet_navegador.py`, que importa su `main()` y lo
lanza con otra vista. Su docstring anota las dos trampas que ya costaron
tiempo: **el archivo no puede llamarse `flet_web.py`** —Flet hace
`from flet_web.fastapi import ...` para servir por HTTP, el directorio del
script va primero en `sys.path`, y termina importándose el envoltorio en vez
del paquete (`asyncio.run() cannot be called from a running event loop`)— y
**`assets_dir` tiene que ser ABSOLUTO**, porque Flet lo resuelve contra el
directorio del script y no contra el cwd: con la ruta relativa servía el
`index.html` para cualquier archivo y el logo del sidebar quedaba vacío sin
dar 404.

---

## Estado del entorno: dos cosas que conviene chequear antes de empezar

No son bugs ni pendientes de código. Son estados en los que la máquina puede
estar, y confundirlos hace perder tiempo o pisar trabajo ajeno.

### 1. La base puede estar en DOS estados, y no se ve a simple vista

| | Cuándo | Cómo se ve |
|---|---|---|
| **Entrega** | 6 filas | Las pantallas están vacías. Sólo existe la cuenta `dueno` |
| **Demo** | ~70 filas | 4 empleados, 3 socios, rutina, patologías, promociones |

Para saber en cuál estás, desde `backend/`:

```bash
.venv/Scripts/python.exe pruebas/vaciar_base.py     # SIN --si: sólo informa
```

Lista las tablas con datos y no toca nada. Con `--si` la deja en las 6 filas
de entrega; `pruebas/escenario_demo.py` la vuelve a llenar.

> **Las suites necesitan la base VACÍA y la dejan escrita.** Hay que vaciar
> entre una y otra o la anterior le deja datos a la siguiente y fallan por el
> escenario, no por un bug. Y **`escenario_demo.py` le cambia la contraseña al
> `dueno`** (entra con la inicial del `.env` y la cambia): todo eso está
> anotado en `backend/CONTRASEÑAS PARA TESTEO Y ACTUALIZADAS.txt`, que además
> es donde va TODA cuenta nueva — el alta devuelve la contraseña temporal una
> sola vez.

**Antes de dar por buena una prueba contra la base, mirá en qué estado
está.** Un "no muestra nada" puede ser un bug de la pantalla o simplemente la
base de entrega, y son dos investigaciones muy distintas.

### 2. `git status` trae muchos cambios sin commitear que NO son de tu sesión

Tras la reorganización de carpetas del 2026-09-12 y la sincronización del
backend hay **muchísimos** cambios sin commitear (movimientos de `db/`, `docs/`,
`Flet/`, `Proyecto - PWA/`, borrado del `db/` viejo de la PWA, y todo el backend
tocado). Están **sin decidir**: es el dueño del proyecto quien commitea.

No commitees por tu cuenta salvo que te lo pidan. Y ojo con `git add -A` o
`git commit -a`: se llevan puesto el `.git.repo-viejo-backup` del sub-repo Flet
y cualquier cosa a medio decidir. Agregá siempre los archivos explícitos que tocaste.

---

## Git: el proyecto Flet vive en DOS repos

- Monorepo (las dos apps) → `github.com/GianpeCARP/OlimpOS`
- Sólo el Flet → `github.com/GianpeCARP/Proyecto`

`Flet/Proyecto` era un repo propio y **su `.git` está renombrado a
`.git.repo-viejo-backup`**. Si lo restaurás, el monorepo vuelve a verlo como submódulo
vacío y se rompe la subida. Para commitear y pushear ahí **sin restaurarlo**:

```bash
cd "D:/OlimpOs/Flet/Proyecto"
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
- La documentación en `Proyecto - PWA/docs/*.md` está **citada más de 100 veces desde los
  comentarios del código** como justificación de decisiones. No borrarla.

---

## Dónde está el historial detallado

Este archivo es el resumen. El detalle fino vive en varios lugares:

- **`docs/RESUMEN-PARA-CLAUDE-CODE.md`** — qué cambió en el esquema nuevo y por qué.
- **`backend/BITACORA.md`** — el recorrido completo del backend (secciones §1–§15).
- La **memoria de Claude Code**, en `C:\Users\Pardini\.claude\projects\<carpeta>\memory\`,
  donde `<carpeta>` deriva del directorio donde abrís la sesión (p. ej.
  `D--OlimpOs` si abrís en `D:\OlimpOs`). OJO: la memoria vieja bajo
  `D--OlimpOs-Proyecto` era de cuando la PWA estaba en `D:\OlimpOs\Proyecto`, carpeta
  que ya no existe (hoy es `Proyecto - PWA`).

Este `CLAUDE.md` se levanta desde cualquier carpeta del repo.
