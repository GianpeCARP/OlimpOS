# OlimpOS — contexto permanente

Este archivo tiene lo que **no cambia seguido**: la idea, cómo piensa el dueño,
la estructura, las reglas del negocio y las trampas técnicas. **Dónde estamos
parados HOY** (qué falta, qué no se probó, en qué estado está la base) vive en
`docs/ESTADO-ACTUAL.md`, que se carga acá abajo automáticamente:

@docs/ESTADO-ACTUAL.md

**Regla de mantenimiento de estos dos archivos** (pedido explícito del dueño):
- Tienen que alcanzar para retomar todo después de un `/clear`, **sin
  contradecirse** entre sí ni con el código.
- `ESTADO-ACTUAL.md` es una **foto del presente, no un historial**: al terminar
  algo se ACTUALIZA el punto (se borra de "falta", se corrige lo que cambió), no
  se agrega una "tanda" nueva al final. El historial lo tiene git.
- Si un cambio toca una regla del negocio, una decisión o la estructura, se
  corrige ACÁ en el mismo momento. Antes de escribir un dato, verificarlo.
- Corto: si algo se deduce leyendo el código, no va.
- **Lo hace cumplir un hook** (`.claude/hooks/recordar_estado.py`, registrado en
  `.claude/settings.json`). Si hay cambios de código más nuevos que
  `ESTADO-ACTUAL.md`, frena el final de la sesión UNA vez y pide actualizarlo. Si
  no hay nada que cambiar, basta con terminar de nuevo. No desactivarlo.

---

## Qué es y cuál es la idea

Sistema de gestión para un gimnasio. Es un **proyecto escolar con presupuesto
ilimitado**, pensado para **servidores locales**, y con entrega final por delante
(el dueño va a probar absolutamente todo al acercarse la fecha).

La idea de producto: que la app del socio sea **tan útil que la gente elija el
gimnasio por la app** (rutina y dieta propias, contador de repeticiones con la
cámara, progreso, y a futuro un coach con IA). Y que el personal gestione el
gimnasio sin fricción.

**Son dos aplicaciones del mismo producto** contra **un solo backend**:

| App | Carpeta | Quién la usa | Stack |
|---|---|---|---|
| **PWA web** | `Proyecto - PWA/src/frontend` | Socio, Entrenador, Nutricionista, Profesor (desde el celular o el navegador) y también el Dueño | React + TS + Vite + Tailwind |
| **Escritorio** | `Flet/Proyecto` | La PC de **recepción**: Recepcionista y Dueño | Python + **Flet 0.84** |
| **Backend** | `backend/` | Las dos apps | FastAPI + SQLAlchemy sobre **Neon** (Postgres) |

- **La PWA es la referencia y Flet es su gemela.** Si difieren, la que está bien es
  la PWA. Todo arreglo de la PWA se **replica en Flet** en la misma tanda, porque el
  dueño prueba en la PWA y da por hecho que Flet quedó igual. Única excepción:
  **Recepción** (panel del mostrador) existe sólo en Flet.
- **Las dos se ven casi idénticas** (decisión del dueño), con la paleta **Kinetic
  Carbon** duplicada en `index.css` (`@theme`) + `config.ts` y en `app/config.py`
  (`Colors`). Fondo `#15171C`, tarjetas `#1C1F26`, acento volt `#C6F135`, **siempre
  con texto oscuro encima**. Cada componente de `app/components/ui.py` dice de qué
  `.tsx` es gemelo: si tocás uno, mirá el otro.

---

## Cómo piensa el dueño (leer antes de proponer algo)

- **Piensa como el gimnasio de verdad.** La persona del mostrador con cola no lee
  carteles, así que un diálogo de confirmación no frena nada. El sistema **informa,
  no juzga**.
- **Nada muerto en pantalla.** Un campo que no se guarda, un botón que no hace nada o
  una opción ambigua (como los niveles de rutina) se saca. Si pregunta "¿por qué
  existe X?", contestar con el porqué del negocio. Si no hay uno, X sobra.
- **Menos pasos y más completo:** "Asignar" desde la tarjeta, "Cobrar ahora" al dar de
  alta, credenciales por WhatsApp o mail en vez de copiarlas a mano.
- **Profesional:** topes razonables, validaciones de email, teléfono sin letras,
  fechas que no pueden ser futuras.
- **La administración controla quién entra.** No existe "Registrarse".
- **Pragmático con hardware e infraestructura:** el RFID se programa cuando compre el
  lector, y la IA va por API ahora y quizás con un modelo propio después.
- **Cuando pide varias cosas ("hacé las 3", "mandale mecha") quiere todas, completas.**
- **Commits sólo cuando lo pide**, y se pushea a `desarrollo`. **Avisarle antes de
  arrancar el coach con IA.**
- Escribe en español rioplatense y anota lo que encuentra en `A CORREGIR PWA .txt`
  (en la raíz). Los separadores `*****` marcan lo ya resuelto.

---

## Estructura del repo

```
D:\OlimpOs\
├── backend/          API FastAPI. routers/, models.py, schemas.py, permisos.py,
│                     security.py, limite_intentos.py, pruebas/ (suites + scripts de base),
│                     CONTRASEÑAS PARA TESTEO Y ACTUALIZADAS.txt, .env (secretos)
├── db/               schema.sql + seed.sql: fuente de verdad del esquema (41 tablas)
├── docs/             ESTADO-ACTUAL.md, RESUMEN-PARA-CLAUDE-CODE.md (por qué el esquema),
│                     olimpos_schema_actual.dbml, vulnerabilidades a arreglar.md, specs/
├── Flet/Proyecto/    app/ (views/, components/ui.py, state.py, api_client.py, permisos.py),
│                     pruebas_vistas.py, scripts/lanzar_flet_navegador.py
├── Proyecto - PWA/   src/frontend/src (views/, services/, components/, config.ts),
│                     docs/*.md (citados +100 veces desde comentarios: NO borrar)
├── videos/           los que baja backend/demonio_videos.py
├── README.md         la cara del repo: qué es, instalación, cómo se corre
└── instalar.ps1      instalador de Windows (winget + venv + npm ci + .env)
```

- `db/schema.sql` y Neon coinciden nombre por nombre: una tabla nueva va en los dos
  (y en `models.py`).
- **Dos `.env` distintos a propósito.** El del backend tiene secretos. El del frontend
  es **opcional**: `VITE_API_URL` vale `/api` por defecto y termina en el bundle, así
  que nunca lleva nada privado.

---

## Arquitectura que conviene saber

- **Roles (6): dueno, recepcionista, entrenador, nutricionista, profesor, socio.** No
  son una columna: se **derivan** de las tablas subtipo (`roles_de_persona` en
  `models.py`). `id_socio` e `id_profesor` viajan firmados en el JWT, así que los
  endpoints "mis cosas" nunca aceptan ids por parámetro.
- **Permisos: una matriz en TRES copias** (`backend/permisos.py`, `app/permisos.py` y
  `config.ts`) que `backend/check_permisos.py` verifica. Hay secciones con nivel
  NINGUNO, LECTURA o TOTAL, más acciones sueltas (`verIngresos`, `gestionPromociones`,
  `verHistorialMedico`…). Para mostrar permisos en pantalla, **derivarlos**: nunca
  escribirlos a mano.
- **Sesión.** La PWA usa una cookie httponly + CSRF a través del proxy de Vite `/api`
  (`SameSite=lax`: página y API tienen que ser el mismo sitio). Flet manda
  `X-Client-Type: escritorio` y recibe un token Bearer. El header gana sobre la cookie.
- **Freno de login** (`limite_intentos.py`, en memoria): 5 fallos traban la cuenta
  **15 min** y 20 fallos desde la misma IP en 10 min dan **429**. En desarrollo todo
  llega desde 127.0.0.1. **Los fallos de "contraseña actual" al cambiarla suman al
  mismo contador.** Trabada responde igual que una clave equivocada (a propósito). Se
  destraba con "Desbloquear" en Usuarios, resetear la contraseña o reiniciar el
  backend. La columna `bloqueado` es sólo para el bloqueo manual.
- **Rendimiento:** Neon está en São Paulo (44 ms por consulta, 825 ms por conexión
  nueva). El cuello es la red, nunca Python. No desarmar: el pool con
  `pool_recycle=240` + keepalives, el latido `SELECT 1` cada 2 min (Neon suspende el
  compute), los listados en lote con `selectinload` (nada de N+1) y el
  servir-y-refrescar de `api_client.py` en Flet. **Cualquier escritura y el logout
  invalidan TODO el caché de Flet.**
- **Gráficos hechos a mano, sin librería**, en las dos apps (Flet 0.84 no trae).

---

## Reglas del negocio (decisiones del dueño: parecen bugs si no se conocen)

**Plata**
- **Prepago puro. No hay tabla `Deuda`.** "Debe" = no tiene membresía vigente. El
  estado del socio se calcula en orden: De baja > Sin membresía > Suspendido >
  Vencido > Por vencer (0 a 7 días) > Activo. **Queda vencido el día siguiente al
  vencimiento.**
- **La caja existe para 4 casos:** efectivo, el socio que no usa la app, un pago que
  entró por fuera y corregir un cobro. El resto lo paga el socio desde la app. Lo
  mismo vale para la clase suelta.
- **Métodos de pago = cómo paga la persona, no el proveedor.** `BILLETERA_VIRTUAL` ≠
  `TRANSFERENCIA` porque se concilian en lugares distintos. El pago online se guarda
  como billetera, no como "MERCADO_PAGO".
- **Promociones:** sólo porcentuales, guardadas en el `Pago`. Tienen que estar
  vigentes **el día que arranca el período cobrado**, no hoy. Listarlas pide la
  sección Cobros; gestionarlas pide `gestionPromociones` (sólo el Dueño).
- **No se cobran cuotas por adelantado** (`backend/renovacion.py`). Con un período en
  curso (activo sin vencer o en pausa) no se cobra otro, ni en el mostrador ni online:
  se renueva desde el día siguiente al vencimiento y la membresía nueva arranca HOY.
  Motivo del dueño: quien paga meses adelantados congela el precio y el gimnasio
  pierde con cada aumento. Las pantallas reciben `puede_renovar` + motivo y no ofrecen
  el cobro. `Pago.es_adelanto` queda siempre en false. Un abono de actividad que no
  entra en la cuota vigente se cobra junto con la próxima cuota.
- **No hay renovación automática.** Cada período se cobra a mano (mostrador) o con un
  checkout de Mercado Pago de pago único (preferencia, no suscripción): si el socio no
  paga, la cuota simplemente vence. `Pago.id_tipo_membresia` guarda qué plan se cobró.
- **El alta de socio no elige plan.** Ofrece "Cobrar ahora", que abre Cobros con el
  socio ya elegido.
- **La facturación la ve sólo el Dueño** (`verIngresos`: métrica del mes y gráfico por
  día, mes o año). Cada cobro suelto, en cambio, aparece en "Actividad reciente" también
  para el Recepcionista, con qué se pagó entre paréntesis (se deriva de la membresía,
  la inscripción o la reserva del pago).

**Asistencia**
- Con la cuota vencida **ficha igual** y se muestra un aviso.
- **Sin tope por día y sin preguntar:** cada ingreso trae `ingreso_numero` y la lista
  muestra "2º de hoy".
- **Desfichar** sólo sobre los ingresos de hoy.
- **Fichar acredita reservas y borrar la asistencia no lo revierte**: no fichar socios
  reales en pruebas.
- **La tarjeta RFID va a existir como lector físico.** Lo que se sacó fue el campo
  para tipear el código.

**Personas y accesos**
- **No hay "Registrarse", ni siquiera pagando.** El personal da de alta a la persona,
  el sistema genera una contraseña temporal que se muestra **una sola vez**, y en el
  primer ingreso la persona elige la suya. `PanelCredenciales` permite mandarla por
  mail o WhatsApp.
- **El botón de mail abre el redactor de Gmail**, no `mailto:` (las PCs del gimnasio
  no tienen cliente de correo). Vive en `utils/contacto.ts` y `app/contacto.py`.
- **Un empleado necesita mail o teléfono.** Un socio tiene **varios teléfonos**, con
  uno principal, y **varios contactos de emergencia**, también con uno principal
  (`Contacto_Emergencia` siempre fue 1:N). Los tres campos `emergencia_*` de
  `SocioOut` son el PRINCIPAL aplanado para la grilla, no todo lo que hay.
- **Teléfonos con código de país:** todo campo de teléfono usa `TelefonoField` /
  `telefono_field` (selector de país, Argentina por defecto) y guarda el número completo
  (`+54 3415551234`). Los viejos sin `+` se leen como argentinos, sin migrar.
  `linkWhatsapp` agrega el 9 de celular argentino.
- **Objetivo y observaciones** (columnas de `Socio`) se cargan en el alta y la edición,
  en las dos apps. El PUT de socio **sólo toca lo que vino en el pedido**: un campo
  ausente se conserva, uno vacío borra. Sin eso, un formulario al que le falte un campo
  lo borra en silencio.
- **Datos personales del socio** (fecha de nacimiento, domicilio, contacto de
  emergencia) se cargan en el **alta y la edición**, nunca al cobrar. Los contactos de
  emergencia se llaman desde un botón de la grilla, que ven todos los que ven
  Socios, y ahí mismo se agregan y se borran; el socio gestiona los suyos desde
  "Mi perfil".
- **La baja de un socio no le quita los días pagos** (`backend/bajas.py`). Con cuota
  vigente queda PROGRAMADA (`Baja.pendiente`) para el día siguiente al vencimiento y
  hasta entonces sigue activo; se puede anular mientras tanto, y con la baja pendiente
  no se renueva. Sin cuota vigente es inmediata. El personal puede elegir "dar de baja ahora"
  (`inmediata`, para una expulsión): corta hoy, pierde los días y adelanta una programada. Se aplica sola al arrancar el backend,
  una vez por día desde el latido y al leer socios. La voluntaria deja viva la cuenta
  de acceso; la de mora o administrativa la desactiva.
- **La cuenta de acceso y ser socio son DOS banderas distintas.** `Usuario.activo`
  es entrar a la app; `Socio.activo` es ser socio del gimnasio. Desactivar la
  cuenta desde Usuarios **no da de baja al socio**: sigue pagando, entrenando y
  fichando, y sigue contando en el dashboard. Para que los paneles no se
  contradigan, `SocioOut` manda `cuenta_activa` y la grilla de Socios avisa
  **"Sin acceso a la app"**. Al revés sí está acoplado: la baja de mora o
  administrativa apaga la cuenta (la voluntaria no) y reactivar al socio la
  devuelve. En empleados el acople es total, porque ahí el acceso se justifica
  en el puesto.
- **Bajas lógicas y reversibles.** Dar de baja un empleado lo desasigna de sus
  actividades, pero no toca los turnos ya programados. **Usuarios no reactiva la
  cuenta de alguien dado de baja** (eso se hace desde Personal) **ni crea personas**:
  la cuenta nace con el alta en Socios o Personal.
- **Resetear la propia contraseña está permitido y CORTA la sesión**: el backend
  rechaza (401) cualquier token de una cuenta marcada para cambiar la clave, y la PWA
  manda al login con el motivo. La temporal se muestra UNA vez: si el único dueño se
  la resetea y la pierde, nadie puede rescatarlo desde la app (sólo un dueño opera
  sobre un dueño) y la salida es reescribirle el hash en la base con
  `auth.hashear_password` — el hash no se puede leer, se reemplaza.
- **Borrar una cuenta** borra sólo el `Usuario` (la persona y su historial quedan).
  Nadie borra la propia; sólo un Dueño borra la de un Dueño, y nunca la última.
- **Historial médico:** el catálogo dice QUÉ tiene y las observaciones por socio dicen
  QUÉ HACER. **El Recepcionista no lo ve**, y el botón se **omite** (no se
  deshabilita) para no delatar que hay algo cargado. La fecha no puede ser futura.

**Entrenamiento y actividades**
- Varios entrenadores a la vez es normal. **Quién entrena a quién lo deciden el Dueño
  y el Recepcionista.** Un Entrenador toca **sólo sus** rutinas; un Nutricionista,
  sus dietas.
- **Rutina y dieta propias del socio** (`id_entrenador` / `id_nutricionista` NULL):
  invisibles para el personal (404). Si hay una asignada por el personal, esa manda
  (409).
- **Las rutinas no tienen nivel.** Se filtran por días por semana (1 a 7). La columna
  `Rutina.nivel` queda sin usar a propósito.
- **Circuito y contador de repeticiones: sólo en celular**, del lado del cliente y
  offline-first (MediaPipe corre en el dispositivo, cola en `utils/colaRegistros.ts`).
- **Clase suelta = `Plan_Actividad` con `tipo_limite=CLASE_SUELTA`.** Las clases
  restantes **se cuentan** en `Reserva`, no se guardan. Topes: 7 por semana, 31 por
  mes, 1 la suelta; cupo por turno de 1 a 100.
- **Sin horario no hay turnos.** Los turnos los genera el backend (4 semanas) desde
  `Horario_Actividad`, que se carga en Actividades con su **profesor** (tiene que estar
  asignado a esa actividad): de ahí salen "Mis clases", "Mis turnos" y la agenda del
  personal. **Actividades la gestionan el Dueño y el Recepcionista** con los mismos
  permisos.
- **El Profesor tiene cuenta, sólo para "Mis clases"** en la PWA. En Flet no tiene
  secciones.
- **Registros vs planes.** `Registro_*` es un log append-only por fecha, nunca se pisa.
  `Asignacion_Rutina` y `Asignacion_Dieta` tienen `estado`, con **una sola ACTIVA**
  por socio (índice único parcial).

---

## Trampas que ya costaron (todas aparecieron CORRIENDO, no leyendo)

**Verificar de verdad**
- `compileall` no ejecuta: un nombre sin importar pasa. `-c "import main"` + el chequeo
  AST de nombres cargados contra ligados.
- `tsc` **con `-p tsconfig.app.json`**: sin eso no compila nada y siempre da OK.
- Un `useEffect` que en sus deps lee un `const` declarado más abajo compila y revienta
  por TDZ. Poner los efectos después.
- **Uvicorn corre sin `--reload`**: tocar rutas = reiniciar. Si el puerto 8000 está
  tomado, el proceso nuevo muere en silencio y responde el viejo. Contar las rutas de
  `/openapi.json`.
- La salida de uvicorn redirigida a un archivo queda en buffer: ese log **no** es
  prueba de qué pedidos llegaron.

**Flet 0.84**
1. `f"{color}20"` no es transparencia (Flet lee `#AARRGGBB`): usar `alpha()` de
   `config.py`.
2. El `scroll` va en la Column **interna**. En la exterior con un hijo `expand`, centra
   todo verticalmente.
3. `ft.Dropdown` usa `on_select`, no `on_change`.
4. `page.fonts` necesita una URL a un `.ttf`, no el CSS de Google Fonts.
5. `assets_dir` es obligatorio, y **absoluto** en el lanzador web.
6. Nada de APIs viejas (`ft.padding`, `ft.app`…): la app arranca con cero
   DeprecationWarning.
7. **Que arranque no significa que la vista se construya.** `pruebas_vistas.py` hace
   `build()` con cada rol (necesita el backend y cuentas de cada rol), y hay que
   correrlo también con la base vacía (divisiones por cero, deltas en None).
8. **Los diálogos no los cubre `pruebas_vistas`.** Un `ft.Row(wrap=True)` con
   `TextField` adentro dibuja un bloque gris: hay que abrirlo en el navegador con
   `scripts/lanzar_flet_navegador.py`. No renombrarlo a `flet_web.py` y no tocar
   `main.py`. Recargar mucho apila sesiones, y el aviso de Chrome para guardar
   contraseña bloquea los clicks. El lanzador **deriva la raíz de su propia
   ubicación**: no volver a clavarle una ruta, que el repo vive en `D:` en una
   máquina y en `E:` en la otra. Y **Flutter no recibe el teclado sintetizado**
   por automatización: el login hay que tipearlo a mano, así que lo que se puede
   automatizar de un diálogo es armarlo y auditarle el árbol de controles
   (instanciar la vista con el `app_state` simulado y leer `page.overlay`).

**PWA en el celular** (ni tsc ni oxlint lo detectan)
- `100dvh` y nunca `h-screen` (iOS). `overscroll-behavior: none` (si no, Safari
  recarga la página).
- Los botones llevan `shrink-0 whitespace-nowrap`. La sidebar es un cajón en mobile.
- Chrome en iOS es Safari por dentro. Forzar el ancho de un contenedor no simula un
  teléfono.
- `devOptions` del plugin PWA apagado. Los íconos son 4 archivos, generados con
  `scripts/generar_iconos.ps1`.

**Proceso**
- Nada de regex multilínea sobre varios archivos a la vez (rompió 4 vistas): archivo
  por archivo.
- Comentarios que explican el **porqué**: el código está muy comentado a propósito,
  no borrar esas notas.
- Soft delete con los dos caminos (baja y reactivación). Al cambiar el estado de una
  entidad, decidir qué pasa con todo lo que la referencia.
- **Una "transacción descartada" NO protege la base si lo que se prueba hace su
  propio `commit()`.** Casi todos los endpoints commitean adentro: llamarlos
  desde un `db.begin()` y cerrar con `rollback()` no revierte nada —el commit
  del endpoint ya se llevó también las filas de prueba—. Ya pasó: un escenario
  de horario + turnos + 3 profesores quedó escrito en la base del dueño. Para
  probar un endpoint contra la base real hay que **marcar todo lo creado**
  (un prefijo reconocible en DNI y legajo) y **borrarlo a mano después**,
  verificando los conteos antes y después.
- Las búsquedas truncadas (o el Glob sobre rutas con espacios, como
  `Proyecto - PWA`) no prueban que algo "no existe": usar Grep sin límite.

---

## Cómo verificar y correr

```bash
# Backend (desde backend/, SIEMPRE el Python del venv)
.venv/Scripts/python.exe -c "import main"
.venv/Scripts/python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
.venv/Scripts/python.exe check_permisos.py
curl -s http://127.0.0.1:8000/openapi.json | .venv/Scripts/python.exe -c "import json,sys; print(len(json.load(sys.stdin)['paths']))"

# PWA (desde Proyecto - PWA/src/frontend)
npx tsc --noEmit -p tsconfig.app.json
npx oxlint src/
npm run dev          # :5173, proxea /api al :8000

# Flet (desde Flet/Proyecto)
python -m compileall -q app main.py
python pruebas_vistas.py
```

- **Suites de integración** (`backend/pruebas/test_*.py`, 11): corren contra Neon con
  el backend levantado y **la base VACÍA**, vaciándola entre una y otra.
  `test_extension_congelamiento` no imprime "TODOS LOS CHEQUEOS PASARON": mirar el
  código de salida. Se autentican con `X-Client-Type: escritorio` + Bearer.
- **Estados de la base:** ENTREGA = 9 filas (la cuenta `dueno`, la sede, 2 tipos de
  membresía y 3 franjas laborales). DEMO = `pruebas/escenario_demo.py`, que además
  **cambia la contraseña del dueño**. `pruebas/vaciar_base.py` sin `--si` sólo informa
  en qué estado está. **Nunca vaciar ni recargar sin que el dueño lo pida.** Un script
  contra la base real restaura lo que toca.
- **Credenciales:** sólo en `backend/CONTRASEÑAS PARA TESTEO Y ACTUALIZADAS.txt`, y
  **toda cuenta nueva se anota ahí**.
- **iPhone sin cable:** `VITE_HTTPS=1 npm run dev` + `cloudflared tunnel --url
  https://localhost:5173 --no-tls-verify`. **El túnel es público: cerrarlo al
  terminar.**

## Git

- Monorepo `github.com/GianpeCARP/OlimpOS`, rama de trabajo `desarrollo`.
- **`main` se mantiene al día**: después de pushear a `desarrollo`, adelantarla con
  `git push origin desarrollo:main`. Es un avance directo porque `main` nunca tiene
  nada propio; si alguna vez no lo fuera, preguntar antes de fusionar.
- **Siempre rutas explícitas; nunca `git add -A` ni `commit -a`**: arrastran cosas que
  no van (el `.git.repo-viejo-backup` dentro de `Flet/Proyecto`, archivos a medio
  decidir).
- Nunca commitear `.env` reales. `A CORREGIR PWA .txt` está versionado (a pedido del
  dueño), así que viaja con el resto.
