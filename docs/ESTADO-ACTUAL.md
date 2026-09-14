# OlimpOS — Estado actual y próximos pasos

**Última actualización: 2026-09-14.** Este archivo es el "arranque rápido": lo
que está hecho HOY, lo que falta, y las decisiones que no se deducen del código.
Es el equivalente versionado de la memoria de Claude Code (que es local a cada
máquina y NO viaja con el repo). Si arrancás en otra computadora, leé esto +
`CLAUDE.md` y ya sabés dónde estamos.

- **`CLAUDE.md`** (raíz) → contexto base permanente: stack, paleta, performance,
  trampas de Flet/PWA, reglas de git, estados de la base, comandos de verificación.
- **`docs/RESUMEN-PARA-CLAUDE-CODE.md`** → por qué el esquema es como es (reset a 41 tablas).
- **`backend/BITACORA.md`** → recorrido histórico del backend (§1–§15).
- **Este archivo** → qué se hizo ÚLTIMO (portal del socio autosuficiente) y qué sigue.

---

## En una frase

Lo último que se construyó es una tanda de features para que **el socio use la
app solo**, sin depender del personal: contar repeticiones con la cámara, armarse
su propia rutina y su propia dieta, registrar lo que come, y ver su progreso en
gráficos. Todo **self-scoped** (el socio sólo toca lo suyo, el `id` sale del token)
e **invisible para el personal**. Lo próximo es un **coach con IA (LLM)**, decidido
pero todavía NO implementado.

---

## Lo que YA está hecho (y dónde vive)

Todo esto está commiteado y pusheado en `desarrollo` (commits `e724865` y `388e09d`).

### 1. Contador de repeticiones con cámara (PWA, sólo celular)
- Pose con **MediaPipe BlazePose** (`@mediapipe/tasks-vision`) corriendo ENTERO en
  el dispositivo (el video nunca sale del teléfono). Modelo + WASM **bundleados**
  en `Proyecto - PWA/src/frontend/public/mediapipe/` (no CDN; ~40MB en el repo).
- Lógica pura en `views/socio/logicaReps.ts`: 15 movimientos, ángulos 3D, máquina
  de estados con histéresis, filtro One-Euro, medición de **ambos lados** del
  cuerpo, gracia al empezar + anti-rebote. Componente `views/socio/ContadorReps.tsx`.
- **Objetivo de reps + pitido**: el socio dice cuántas quiere y el celu pita al llegar.
- Elegir el ejercicio del **catálogo** (modo suelto) → agrupado por músculo, con buscador.
- Guarda la serie (con peso) en `Registro_Ejercicio`, **offline-first**: cuenta sin
  internet y encola el guardado (`utils/colaRegistros.ts`), reintenta al reconectar.
- Se ofrece sólo en celular (`utils/dispositivo.ts`) y como MODO (no ruta) de Mi rutina
  y del circuito.
- **PENDIENTE (#4):** rediseñar el overlay para producción (las "líneas verdes" del
  esqueleto son feas para el producto final; se dejan mientras se afina el tracking).
- **PENDIENTE:** seguir afinando umbrales de algunos movimientos probando en el celu.

### 2. Rutina propia del socio (sin entrenador)
- `Rutina.id_entrenador` es **NULLABLE**: `NULL` = rutina propia. El dueño se DERIVA
  de `Asignacion_Rutina` (no hay columna nueva). Espejo en `models.py` + `db/schema.sql`.
- **Invisible para el staff**: helper `_rutina_del_staff` en `routers/rutinas.py`
  devuelve 404 a las propias; listar/obtener/asignar/editar/baja las excluyen; el
  historial del staff también.
- Endpoints self-scoped en `routers/portal.py`: `POST/DELETE /portal/mi-rutina/propia`
  (autoasignada; 409 si hay rutina del entrenador; reemplaza la propia anterior),
  `GET /portal/mi-rutina/ejercicios` (catálogo). Campo `es_propia` en la respuesta.
- Frontend: `views/socio/ArmarMiRutina.tsx` + integración en `MiRutinaView.tsx`.
- Suite: `backend/pruebas/test_rutina_propia.py`.

### 3. Dieta propia + registro de comida
- **Espejo de la rutina propia**: `Dieta.id_nutricionista` NULLABLE (`NULL` = dieta
  propia), invisible para el staff (`_dieta_del_staff` en `routers/nutricion.py`),
  la del nutricionista tiene precedencia (409). `POST/DELETE /portal/mi-dieta/propia`.
- Las comidas del plan propio son de **texto libre** (`Comida.descripcion`), porque
  `Comida.id_catalogo_comida` ahora es nullable y el catálogo del gimnasio suele
  estar vacío. Frontend: `views/socio/ArmarMiDieta.tsx`.
- **Registrar comida** (`Registro_Comida`): `GET/POST /portal/mi-dieta/comidas`. Texto
  obligatorio; macros (kcal/proteínas/carbos/grasas) y momento **opcionales, a mano**.
  Frontend: `views/socio/RegistrarComida.tsx`. La IA los va a poder autocompletar
  (ver coach IA), pero NO es obligatorio.
- Suite: `backend/pruebas/test_dieta_propia.py`.

### 4. Tablero de progreso (Mi progreso)
- `views/socio/MiProgresoView.tsx` (ya tenía el peso corporal) + `views/socio/ProgresoExtra.tsx`
  con dos secciones nuevas: **Nutrición** (kcal/proteína promedio + barras por día) y
  **Fuerza** (sparkline del peso levantado por ejercicio + delta). Gráficos hand-rolled,
  **sin librería** (decisión del proyecto: 40kB no se justifican).
- Backend: `GET /portal/mi-rutina/registro-ejercicio`.

---

## Modelo de datos: "registros" vs "planes" (importante, no se ve en el código)

- **Registros** (`Registro_Comida`, `Registro_Ejercicio`, `Registro_Salud`): son un
  **log append-only por fecha**. NO se pisan ni se actualizan: cada carga es una fila
  nueva con su `fecha`. Los viejos quedan para siempre (alimentan los gráficos). NO
  hay "activo": el actual es el de fecha más reciente. Granos: `Registro_Comida` varias
  por día; `Registro_Ejercicio` único `(socio, ejercicio, fecha)` → una por día que se
  ACUMULA si contás dos series; `Registro_Salud` único `(socio, fecha)`.
- **Planes** (`Asignacion_Rutina`, `Asignacion_Dieta`): ahí SÍ hay "actual". Tienen
  `estado` + un **índice único parcial** `una_activa` (`WHERE estado='ACTIVA'`) →
  una sola activa por socio. Al rehacer la propia, la vieja pasa a `FINALIZADA`
  (historial) y la nueva queda `ACTIVA`. La base sabe cuál es la actual por el estado.

---

## Lo que FALTA / próximos pasos

### Coach con IA (LLM) — DECIDIDO, no implementado
El siguiente gran paso. Diseño acordado con el dueño:
- **Chatbot a pedido** (no automático), con **historial guardado** (tabla nueva chica).
- Corre en el **backend** llamando a una **API externa** = **Claude (Anthropic API)**,
  modelo **Haiku 4.5** para el chat común (barato).
- **Tool-use / function calling**: si el socio dice "aplicá este cambio", el LLM
  modifica su rutina/dieta llamando a los MISMOS endpoints self-scoped (con el token
  del socio → no puede tocar nada ajeno). Regla: **propone → el socio confirma → aplica**,
  nunca en silencio.
- **NUNCA** manda datos médicos (patologías) al tercero. Sólo peso/reps/comidas.
- **Consentimiento explícito** del socio (dónde guardarlo, a definir — se propuso un flag por socio).
- Control de costo: resumen compacto de datos por llamada, ventana de chat acotada, tope por día.
- De yapa: **autocompletar de macros** por texto en el registro de comida.
- El "cerebro" del coach NO se entrena: se hace con un **system prompt rico**
  (metodología, reglas, tono, seguridad) + los datos reales del socio + tools + (opcional) RAG.

**Decisión de infraestructura (2026-09-14):** por ahora **"la fácil" = alquilar Claude
vía API (con API key de Anthropic)** — necesita la key (secreto, como el token de
Mercado Pago pendiente); sin ella el código queda listo pero no responde. CONTEXTO: es
un **proyecto escolar con presupuesto ilimitado** y previsto para **servidores locales**,
así que más adelante se puede migrar a un **modelo open-weights auto-hospedado** (Llama/
Qwen/etc.) sin API key — reusando el mismo system prompt y la misma lógica. Tampoco ahí
se entrena desde cero: se bajan pesos ya entrenados y se hace prompting/fine-tuning.

**PENDIENTE de definir con el dueño antes de codear:** la metodología/criterio de
entrenamiento y nutrición que va en el system prompt (estándar sólido vs. material propio),
y dónde persistir el consentimiento.

### Otros pendientes
- **#4 overlay del contador** (sacar líneas verdes) — cuando el tracking esté redondo.
- **Mercado Pago** — falta token, secreto del webhook y URL pública (ver `backend/BITACORA.md` §13).
- **Endurecimiento de seguridad** — ver `docs/vulnerabilidades a arreglar.md`.

---

## Cómo correr y probar

Comandos completos en `CLAUDE.md`. Lo esencial:

- **Backend** (desde `backend/`, SIEMPRE el Python del venv):
  `.venv/Scripts/python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000`
- **Suites** (backend levantado + base VACÍA; vaciar entre una y otra con
  `pruebas/vaciar_base.py --si`, regenerar demo con `pruebas/escenario_demo.py`):
  incluye las nuevas `test_rutina_propia.py`, `test_dieta_propia.py`, `test_registro_ejercicio.py`.
- **PWA** (desde `Proyecto - PWA/src/frontend`): `npx tsc --noEmit -p tsconfig.app.json`
  y `npx oxlint src/` (los dos tienen que dar 0).
- **Probar en el celu (iPhone sin cable):** Vite en HTTPS LAN + túnel de cloudflared:
  1. `VITE_HTTPS=1 npm run dev` (desde el frontend) → HTTPS en :5173.
  2. `cloudflared tunnel --url https://localhost:5173 --no-tls-verify` → da una URL pública `*.trycloudflare.com`.
  3. Abrir esa URL en el celu. El frontend pega a `/api`, que Vite proxea al backend :8000.
  El firewall de Windows (perfil "Public") bloquea el acceso directo por IP, por eso el túnel.
  **El túnel expone todo públicamente: cerralo al terminar.**

---

## Trampas y reglas que ya costaron (resumen; el detalle en CLAUDE.md)

- **Git:** stagear SIEMPRE rutas explícitas, **nunca `git add -A`/`commit -a`** (se
  llevan el `.git.repo-viejo-backup` del sub-repo Flet y archivos sin decidir). Nunca
  commitear `.env` reales. Las credenciales de testeo van SÓLO en
  `backend/CONTRASEÑAS PARA TESTEO Y ACTUALIZADAS.txt`. Los 40MB de `public/mediapipe`
  ya están en la historia (necesarios para que el contador ande en otra máquina).
- **Base de datos:** `db/schema.sql` y Neon coinciden nombre por nombre. Las migraciones
  de esta tanda ya se aplicaron a Neon a mano (Rutina/Dieta/Comida nullables +
  `Comida.descripcion` + `Registro_Comida` con `momento` y macros). Si reconstruís desde
  `db/schema.sql`, ya está todo.
- **Dos estados de la base:** ENTREGA (6 filas) y DEMO (~70). Ver en cuál estás con
  `pruebas/vaciar_base.py` (sin `--si` sólo informa). Credenciales demo: todas `Demo2026!`.
- **Casi todos los bugs aparecen CORRIENDO, no leyendo.** `tsc`/`oxlint`/`compileall`
  no bastan; hay que ejecutar la vista/endpoint con datos reales.
