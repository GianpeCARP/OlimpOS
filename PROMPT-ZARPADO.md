# PROMPT-ZARPADO — Masterclass de OlimpOS

Este archivo **es el prompt**. Lo que sigue son las instrucciones para producir una
explicación completa del código de OlimpOS, al nivel de un curso de posgrado del MIT.
No es documentación de referencia ni un README: es una **clase**.

---

## 0. Antes que nada: prohibiciones duras

El repo está conectado a una base **de producción, con datos reales que el dueño cargó
a mano**. Romperla es infinitamente peor que escribir un capítulo flojo.

- **Sólo lectura.** No edites ni crees archivos fuera de los entregables de la sección 8.
- **Nada contra la base.** Ningún script de `backend/pruebas/`, jamás `vaciar_base.py`
  ni `escenario_demo.py`, ninguna consulta a Neon.
- **No levantes el backend** (`uvicorn`) ni `npm run dev`. Si se ocupa el puerto 8000, el
  proceso nuevo muere en silencio y el viejo sigue respondiendo.
- Comandos permitidos: `cat`, `sed -n`, `grep`, `find`, `wc`.

---

## 1. Qué hay que producir

Una masterclass en cuatro partes, escrita en **español rioplatense**, que le permita a
alguien que nunca vio este repo entender **todo el sistema hasta el fondo** y después
**encontrar cualquier línea de código** que implemente cualquier cosa.

| Parte | Qué es | Se organiza por |
|---|---|---|
| **A0 · Cimientos** | Cada tecnología del stack explicada bajando de capa hasta el piso. | Temas, de abajo hacia arriba |
| **A · El sistema** | Cómo esas piezas forman OlimpOS y por qué así. | Temas, en orden constructivo |
| **B · Los 173 procesos** | Cada proceso, con archivo y rango de líneas en las tres capas. | `PROCESOS-LOGICOS-REQUERIDOS.md` |
| **C · Lo que no es un proceso** | El código que no cuelga de ningún endpoint. | Subsistemas |

---

## 2. El método de explicación

Esta sección manda sobre todas las demás. Un capítulo que la incumpla se reescribe
aunque sea correcto.

### 2.1 Regla del origen

**Ningún concepto se presenta por lo que es. Se presenta por el problema que vino a
resolver.** Un concepto sin su problema es arbitrario, y lo arbitrario no se entiende:
se memoriza.

- Mal: *"Una cookie es un par clave-valor que el navegador guarda y reenvía."*
- Bien: *"HTTP nació sin memoria: cada pedido llega y el servidor no tiene forma de
  saber si viene de quien pidió hace un segundo. Eso alcanzaba para servir documentos,
  y deja de alcanzar apenas querés que alguien inicie sesión. La cookie es la respuesta
  mínima a ese problema: el servidor manda un papelito, el navegador lo guarda y lo
  vuelve a adjuntar solo en cada pedido siguiente. Todo lo demás —expiración, dominio,
  `SameSite`, `httponly`— son parches a agujeros que ese mecanismo mínimo dejó abiertos,
  y cada uno se explica por el agujero que tapa."*

Cuando exista, contá **el origen histórico real**: qué se hacía antes, qué se rompió,
quién lo propuso. No es color: es lo que hace que la solución parezca inevitable en vez
de caprichosa.

### 2.2 Regla del descenso

Explicado el qué y el porqué, **bajás una capa y explicás cómo está implementado**. Y
después otra. Y otra, hasta llegar al **piso declarado del tema** (sección 2.3).

Cada capa se marca con un encabezado que diga en qué nivel está, para que el lector que
ya sabe pueda saltearla sin perder el hilo:

```markdown
> **↓ Capa 2 — qué hace el navegador con eso.** Salteable si ya lo sabés.
```

Prohibido cerrar una explicación con una caja negra sin abrir. Si escribís "el navegador
lo guarda", la capa siguiente dice **dónde** lo guarda, **en qué formato**, **cuándo lo
borra** y **qué lo puede leer**.

### 2.3 Regla del piso

El descenso no es infinito ni arbitrario: **cada capítulo declara su piso en la primera
línea** y baja hasta ahí. Esta tabla fija el piso de cada tema. El piso está elegido
donde bajar un escalón más ya no explica nada de OlimpOS.

| Tema | El descenso | Piso |
|---|---|---|
| **React** | componente → JSX → árbol virtual → reconciliación → DOM real → motor de render → pintado | el píxel en pantalla |
| **JavaScript corriendo** | fuente → parseo → bytecode → JIT → instrucciones de máquina | la instrucción de máquina (nombrá las compuertas y pará ahí) |
| **TypeScript** | tipos → chequeo → **borrado** → el JS que queda | qué **no** existe en tiempo de ejecución |
| **HTTP** | método, cabeceras y cuerpo como texto plano → TCP (handshake, orden, reintento) → IP → paquetes → medio físico | el paquete viajando |
| **Cookies** | `Set-Cookie` → almacén del navegador → reenvío automático → `SameSite`, `httponly`, dominio | el byte en la cabecera |
| **CSRF** | el navegador adjunta cookies **solo** → el ataque, paso a paso → el token → por qué `SameSite=lax` obliga a que la página y la API sean el mismo sitio | el pedido falso completo, escrito |
| **Hash y JWT** | `header.payload.firma` → base64url → HMAC → SHA-256 → rondas, XOR, rotaciones, sumas | **las compuertas lógicas** — acá el descenso llega de verdad al fondo, y corresponde |
| **Contraseñas** | hash lento + sal → por qué el hash no se lee, se reemplaza → costo de trabajo | el ataque de diccionario con números concretos |
| **SQL y Postgres** | tabla → fila → página de 8 KB → índice B-tree → planificador → disco | la página en disco |
| **Índices** | búsqueda lineal → árbol balanceado → de O(n) a O(log n) | la cantidad de comparaciones, con números |
| **ORM** | clase ↔ tabla → sesión → unidad de trabajo → **el SQL exacto que emite** → el problema N+1 | las consultas contadas, una por una |
| **Conexión a la base** | TCP + TLS + autenticación → viajes de ida y vuelta → 825 ms → pool y `pool_recycle` | los RTT contados hasta São Paulo |
| **Async y el event loop** | corrutina → bucle de eventos → concurrencia ≠ paralelismo → el GIL | por qué esperar la red no bloquea y calcular sí |
| **Flet** | control Python → puente → Flutter → árbol de widgets → canvas | el canvas dibujando |
| **MediaPipe** | imagen → tensor → red neuronal → 33 puntos → ángulo por producto escalar | la aritmética del ángulo, hecha a mano |
| **Service worker** | un proxy adentro del navegador → intercepta `fetch` → caché → instalable | la intercepción del pedido |

Si un tema no está en la tabla, elegí su piso con este criterio y declaralo igual.

### 2.4 Regla del retorno

**Todo descenso vuelve a subir.** Un capítulo que baja hasta SHA-256 y termina ahí es un
apunte de criptografía, no una clase sobre OlimpOS. Cerrá cada descenso volviendo al
repo, con archivo y línea:

> *"...y por eso el token no se puede falsificar sin la clave. En este repo esa clave es
> `SECRET_KEY` de `backend/.env`, la firma se arma en `security.py:XX` y se verifica en
> `security.py:XX`. Si mañana rotás esa clave, todas las sesiones abiertas mueren de
> golpe — que es exactamente lo que dice V-08 cuando anota que el JWT no tiene
> revocación: la única revocación disponible es esa, y es a todo o nada."*

### 2.5 Regla de la fuente única

**Cada concepto se explica UNA sola vez, en un solo lugar, y ese lugar es el único que
lo explica.** En todos los demás se lo nombra y se enlaza. Un hash es lo que es: se
define a fondo en A0-11 y nunca más se vuelve a definir, ni "desde otro ángulo", ni
"aplicado a este caso", ni "repasando brevemente".

Leer el mismo concepto explicado dos veces es la marca de un documento escrito sin
criterio, y hace dudar de todo lo demás. Es peor que una explicación corta.

**El presupuesto de profundidad se gasta bajando de capa, no repitiendo desde otro
ángulo.** Si te sobra espacio en un capítulo, la respuesta correcta es descender un
escalón más hacia el piso, o aplicar la sección 2.7 — nunca volver a contar lo mismo con
otras palabras.

**Un segundo ángulo se permite sólo si pasa esta prueba**, y hay que escribir en el
texto cuál de las dos condiciones cumple:

1. El mismo mecanismo **cumple roles opuestos** en dos lugares del sistema, y verlo una
   sola vez no deja ver la oposición. *(El `X-Client-Type` que en Flet es comodidad y en
   seguridad es la vulnerabilidad V-11: mismo mecanismo, dos lecturas que se contradicen.)*
2. La segunda vista **revela un modo de fallar** que la primera no podía mostrar.

Si no cumple ninguna, es redundancia: enlazá y seguí.

### 2.6 Regla de la conexión

Las conexiones se escriben, pero **como punteros de una línea, nunca como
explicaciones**. Cada capítulo cierra con **"Con qué se conecta"**: de tres a seis
viñetas, una línea cada una, cada una nombrando el otro concepto y el tipo de vínculo, y
**enlazando** en vez de desarrollar.

- **Es la misma idea que…** — *el pool de conexiones y el caché de `api_client.py`:
  pagar una vez algo caro y reusarlo (→ A0-12, A-11).*
- **Existe por culpa de…** — *el token CSRF existe sólo porque la cookie se reenvía
  sola; Flet, que manda la sesión a mano, no lo necesita (→ A0-12).*
- **Es el mismo problema que…** — *el N+1 y los 825 ms de conexión nueva: viajes de ida
  y vuelta, a dos escalas (→ A0-09, A-11).*
- **Se contradice con…** — cuando dos decisiones del sistema tiran para lados opuestos,
  nombralas y decí cuál ganó.

Si una viñeta necesita un párrafo para entenderse, no es una conexión: es un concepto
que le falta su lugar propio. Dáselo, y enlazalo desde acá.

### 2.7 Regla de la ingeniería inversa

El descenso de 2.2 va del concepto al mecanismo. Esta regla va **al revés**: del código
concreto hacia arriba, hasta la decisión estratégica que lo explica. Es la que convierte
una lectura de código en una clase de diseño.

Para cada subsistema —y para cada proceso de la Parte B que tenga algo para enseñar—
reconstruí, leyendo el código, esto:

1. **Qué estaba optimizando quien lo escribió.** Velocidad de mostrador, costo de
   mantenimiento, cantidad de viajes a la base, simplicidad de la pantalla.
2. **Qué restricciones lo acorralaban.** La base a 44 ms, Flet 0.84 sin librería de
   gráficos, el celular sin conexión estable, el rol que no puede ver cierto dato.
3. **Qué alternativas había, y qué se pierde con cada una.** Al menos una descartada,
   dicha en serio: guardar el estado del socio en una columna, acoplar `Usuario.activo`
   con `Socio.activo`, modelar una tabla `Deuda`.
4. **Cuál se eligió y qué se pagó por elegirla.** Toda decisión cuesta algo; si no
   encontrás el costo, no entendiste la decisión.
5. **El nombre del patrón**, cuando lo tenga. Derivar en vez de almacenar. Soft delete.
   Servir y refrescar. Denormalizar para leer. Idempotencia. Fallar cerrado. Poner el
   nombre es lo que hace que el lector reconozca la misma jugada la próxima vez que la
   vea en otro sistema.

Escribilo en **conceptos estratégicos, no narrando el código**. "El bucle recorre las
membresías y compara fechas" no es ingeniería inversa. "El sistema elige derivar el
estado en cada lectura en vez de guardarlo, porque un estado guardado se vuelve mentira
al día siguiente sin que nadie escriba nada; el precio son dos consultas más por fila,
y por eso al lado hay un `selectinload`" sí lo es.

### 2.8 Prohibiciones

- **Analogías sin mecanismo.** "Es como una caja", "pensalo como un cajón de archivos".
  Se permite una analogía **sólo** si inmediatamente después viene el mecanismo real.
- **Frases que no se pueden verificar.** "Se encarga de", "maneja la lógica", "realiza
  las validaciones necesarias", "gestiona el flujo". Si escribís "valida los datos",
  enumerá qué valida y qué devuelve cuando falla.
- **Usar un término antes de definirlo.** La primera vez que aparece, se define en su
  lugar. Si ya se definió antes, se lo nombra y se enlaza, no se lo repite.
- **Explicar dos veces lo mismo.** Incluye el "repasemos brevemente", el "dicho de otra
  manera" y el "visto desde el lado del servidor". Ver 2.5.
- **Sobre-explicar lo que se entiende solo.** Un `getter` de tres líneas no necesita
  cinco párrafos. La profundidad va donde hay una decisión atrás; donde no la hay,
  una línea alcanza y sobra.
- **Anglicismos sin traducir.** "Endpoint", "commit", "hash", "token" y "caché" pasan
  porque están en el código. "Deployar", "mockear", "handlear", no.
- **Terminar en caja negra.** Ver 2.2.

---

## 3. Parte A0 — Cimientos

De abajo hacia arriba: cada capítulo sólo usa lo que ya construyeron los anteriores.
Este es el orden, y cada uno se escribe con el método de la sección 2 completo —origen,
descenso hasta su piso, retorno al repo, conexiones.

1. **Qué pasa cuando corre un programa.** Proceso, memoria, instrucciones. El piso donde
   la abstracción toca el silicio, nombrado una vez para no volver a bajar hasta acá.
2. **Cómo se comunican dos máquinas.** Paquetes, IP, TCP, puertos. Por qué "127.0.0.1"
   no es lo mismo que la IP de la LAN, que es exactamente la trampa del túnel de
   Cloudflare documentada en el README.
3. **HTTP.** Pedido y respuesta como texto. Métodos, códigos, cabeceras, cuerpo. Por qué
   no tiene memoria.
4. **El navegador por dentro.** DOM, motor de render, bucle de eventos, `fetch`,
   almacenamiento. Qué significa que algo corra "del lado del cliente".
5. **JavaScript y TypeScript.** Qué ejecuta el motor, qué agrega TS y —lo importante—
   **qué desaparece al compilar**: por qué un tipo no te protege de lo que llega por la
   red.
6. **React.** El problema que resuelve (sincronizar estado y pantalla a mano no escala),
   componentes, estado, re-render, reconciliación, efectos. Por qué un `useEffect` que
   lee una `const` declarada más abajo compila y revienta por TDZ.
7. **Bases de datos relacionales.** Tabla, fila, clave primaria, clave foránea,
   normalización, transacción, ACID. Qué garantiza un `commit` y qué no.
8. **SQL, índices y planes de consulta.** Por qué un índice cambia el orden de magnitud
   y qué cuesta mantenerlo.
9. **El ORM.** Mapear objetos a filas, la sesión como unidad de trabajo, carga perezosa
   contra carga ansiosa, y el N+1 con las consultas contadas.
10. **Python del lado del servidor.** FastAPI, corrutinas, el bucle de eventos, el GIL,
    inyección de dependencias. Por qué en este sistema el cuello es la red y no la CPU.
11. **Criptografía aplicada.** Función hash, HMAC, firma, sal, hash lento. **Este es el
    capítulo que baja hasta las compuertas**, y es el lugar correcto para hacerlo.
12. **Sesiones y autenticación en la web.** Cookies, tokens, cabeceras, CSRF, CORS,
    `SameSite`. Los dos mecanismos que usa este sistema y por qué son dos.
13. **Flutter y Flet.** Árbol de widgets, canvas, y qué significa que Flet sea Python
    manejando Flutter por un puente.
14. **Visión por computadora en el dispositivo.** Imagen, tensor, inferencia,
    puntos clave, y el ángulo entre tres puntos calculado a mano.

### Cómo se lee la Parte A0 sin leerla entera

Arrancá `00-indice.md` con una **tabla de ruteo**: para cada capítulo, una línea de
"esto ya lo sabés si podés responder esta pregunta". Ejemplo: *"Capítulo 11 — si sabés
por qué un hash no se puede revertir pero sí se puede romper con un diccionario,
salteátelo."* El lector decide qué leer; el documento no decide por él.

---

## 4. Parte A — El sistema

Doce capítulos, en orden constructivo. Todo lo de acá se apoya en A0 y ya puede usar su
vocabulario sin volver a definirlo.

1. **Qué es OlimpOS y qué problema resuelve.** El gimnasio real, no el software. Quién
   se para frente a qué pantalla y con cuánta cola esperando atrás. Esto explica la
   mitad de las decisiones del sistema.
2. **El modelo de negocio codificado: prepago puro.** Por qué no existe una tabla
   `Deuda` y qué significa entonces "deber". Definir "membresía vigente".
3. **Las dos aplicaciones y el único backend.** Por qué existe cada una, quién usa cada
   una, y qué implica que la PWA sea la referencia y Flet su gemela.
4. **El recorrido completo de un pedido.** *El capítulo bisagra de toda la masterclass.*
   Seguir un click concreto —conviene "cobrar una cuota"— desde el `onClick` del `.tsx`,
   por el service, el proxy `/api` de Vite, el middleware de CSRF, la dependencia de
   permisos, el handler, el ORM, la red hasta São Paulo, el `commit`, y todo el camino
   de vuelta hasta el re-render. Con archivo y línea en cada escala, y **enlazando cada
   escala al capítulo de A0 que la explica**. Todo lo demás en la Parte B es una
   variación de este recorrido.
5. **El modelo de datos.** Las 41 tablas de `db/schema.sql` agrupadas por qué modelan.
   Qué es una tabla subtipo y por qué `Persona` → `Socio`/`Empleado` → `Entrenador` se
   parte así en vez de llevar una columna `rol`.
6. **Los seis roles y cómo se derivan.** `roles_de_persona()` en `models.py`: por qué la
   pregunta "¿qué rol tiene esta persona?" se responde con consultas y no con una
   lectura, y qué cuesta eso en viajes a la base.
7. **Autenticación.** Qué lleva adentro el JWT de este sistema, por qué `id_socio` e
   `id_profesor` viajan firmados y qué ataque concreto evita eso. Cookie httponly + CSRF
   en la PWA contra Bearer en Flet, y por qué dos mecanismos para un mismo backend. El
   freno de intentos y por qué una cuenta trabada responde igual que una clave errada.
8. **Autorización.** La matriz de permisos: secciones con nivel, acciones sueltas, y por
   qué vive en tres copias que `check_permisos.py` mantiene sincronizadas.
9. **Estados derivados contra estados guardados.** El estado del socio, su orden de
   precedencia, y la regla de que queda vencido el día *siguiente* al vencimiento.
   Generalizar: cuándo un dato se guarda y cuándo se calcula, y qué se paga en cada caso.
10. **Bajas lógicas y reversibilidad.** Soft delete, las dos banderas independientes
    (`Usuario.activo` vs `Socio.activo`), la baja programada, y qué le pasa a todo lo que
    referencia una entidad cuando cambia de estado.
11. **Rendimiento contra una base remota.** Neon en São Paulo: 44 ms por consulta,
    825 ms por conexión nueva. El N+1 con las consultas contadas, `selectinload`, el pool
    con `pool_recycle`, el latido `SELECT 1` y el servir-y-refrescar de Flet. La
    conclusión que ordena todo: **el cuello es la red, nunca Python.**
12. **Cómo leer `PROCESOS-LOGICOS-REQUERIDOS.md`.** La notación DFD lineal y sus
    convenciones. Sin este capítulo, la Parte B no se entiende.

Cerrá con dos apéndices:

- **Glosario alfabético** de todo término definido en A0 y A, cada uno con una línea y
  el capítulo donde se define a fondo.
- **Mapa de conexiones**: el grafo de la sección 2.5 junto, en una tabla de tres
  columnas —concepto, con qué se conecta, de qué tipo es la conexión—. Es el índice por
  el que se navega cuando lo que buscás es entender, no ubicar código.

---

## 5. Parte B — Los 173 procesos

El esqueleto es `PROCESOS-LOGICOS-REQUERIDOS.md`: **mismo orden, misma numeración,
mismos títulos, las 15 secciones**. Un capítulo por sección:

| # | Sección | Procesos |
|---|---|---|
| 1 | Acceso y sesión | 1–5 |
| 2 | Socios | 6–28 |
| 3 | Personal | 29–37 |
| 4 | Usuarios y cuentas de acceso | 38–45 |
| 5 | Cobros y pagos | 46–51 |
| 6 | Asistencia | 52–56 |
| 7 | Recepción | 57–59 |
| 8 | Actividades, turnos y horarios | 60–87 |
| 9 | Rutinas | 88–97 |
| 10 | Nutrición | 98–107 |
| 11 | Patologías | 108–109 |
| 12 | Promociones | 110–117 |
| 13 | Dashboard | 118–121 |
| 14 | Portal del socio | 122–167 |
| 15 | Procesos automáticos | 168–173 |

### Plantilla obligatoria, idéntica para los 173

````markdown
### 46. Cobrar una cuota

`POST /cobros/cuota` · Dueño, Recepcionista

**Qué resuelve.** Una o dos frases, en términos del gimnasio, no del código.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/cobros/CobrosView.tsx` | 118–186 | `CobrosView` |
| Service PWA | `…/src/services/cobrosService.ts` | 44–58 | `cobrarCuota()` |
| Esquemas | `backend/schemas.py` | 901–940 | `CobroCuotaIn`, `PagoOut` |
| Endpoint | `backend/routers/cobros.py` | 88–201 | `cobrar_cuota()` |
| Regla de negocio | `backend/renovacion.py` | 12–64 | `puede_renovar()` |
| Vista Flet | `Flet/Proyecto/app/views/cobros.py` | 310–402 | `_dialogo_cobro()` |

**Cómo funciona.** La explicación de cátedra, siguiendo el código en el orden en que
corre. Cada afirmación anclada a una línea. Acá va el grueso del texto. Cuando toques un
concepto de A0, enlazalo en vez de re-explicarlo.

**Qué escribe y qué lee.** Las tablas de la línea DFD del proceso, con la línea de
código donde se toca cada una. Si el código toca una tabla que la línea DFD no declara,
o al revés, **decilo explícitamente**: es un hallazgo, no un error de redacción.

**Por qué está hecho así.** Ingeniería inversa según la sección 2.7: qué se estaba
optimizando, qué restricción acorralaba, qué alternativa se descartó, qué se pagó y cómo
se llama el patrón. Si el proceso no tiene ninguna decisión interesante atrás —un listado
que lista y nada más—, **escribí una línea y seguí**: inflarlo es peor que no ponerlo.

**Qué pasa cuando sale mal.** Cada error que declara el `CONCEPTO_SALIDA` del proceso,
con el código HTTP, el mensaje y la línea que lo levanta.
````

### Reglas de la tabla "dónde vive el código"

Innegociables, porque son lo que hace que esto sirva dentro de seis meses:

1. **Todo rango de líneas se verifica abriendo el archivo.** Nada de estimar. Si no lo
   abriste y no viste las líneas, no ponés el rango.
2. **Todo rango lleva su símbolo al lado** —función, clase, componente o constante—
   porque los números se corren con la primera edición y el nombre no.
3. **Rutas completas y relativas a la raíz del repo**, con las carpetas tal cual se
   llaman, espacios incluidos (`Proyecto - PWA/...`).
4. **Una fila por capa que participa realmente.** Si el proceso no tiene pantalla en
   Flet, la fila dice `— (no existe en Flet)` y una nota al pie aclara si eso es correcto
   (el portal del socio) o un pendiente conocido (Recepción).
5. **Si no lo encontrás, escribí "no localizado"** y con qué lo buscaste. Una línea
   inventada envenena el documento entero; un "no localizado" es trabajo pendiente
   honesto y visible.

---

## 6. Parte C — Lo que no es un proceso

Nada de esto cuelga de un endpoint, y varias son el código más interesante del repo.
Un capítulo cada una, con la misma exigencia de archivo y rango de líneas, y el mismo
método de descenso de la sección 2:

1. **El contador de repeticiones.** MediaPipe en el dispositivo, la geometría de los
   ángulos, los umbrales, la máquina de estados de una repetición. Por qué es sólo
   celular y por qué corre del lado del cliente.
2. **Offline-first y la cola de registros.** `utils/colaRegistros.ts`: qué se encola,
   cuándo se vacía, qué pasa con un duplicado.
3. **Los gráficos dibujados a mano**, en las dos apps, sin librería. La matemática de
   mapear valores a píxeles.
4. **La PWA como aplicación instalable.** Manifiesto, service worker, íconos, y las
   trampas de iOS (`100dvh`, `overscroll-behavior`).
5. **La capa de red de cada app.** `services/api.ts` contra `app/api_client.py`: el
   manejo del 401, el CSRF, y el caché de Flet que se invalida entero con cada escritura
   y con el logout.
6. **El sistema de diseño compartido.** La paleta Kinetic Carbon en sus tres copias y el
   contrato de componentes gemelos de `app/components/ui.py`.
7. **Los dos lanzadores y el instalador.** `scripts/lanzar_flet_navegador.py`,
   `instalar.ps1`, y por qué un `.ps1` con acentos tiene que ir en UTF-8 con BOM.
8. **El demonio de videos.** `backend/demonio_videos.py`: un proceso cuyo estado es la
   existencia del archivo, no una fila.

---

## 7. Fuentes de verdad, y qué hacer si se contradicen

| Fuente | Para qué |
|---|---|
| El código | La verdad última. Si algo no coincide, gana el código. |
| `PROCESOS-LOGICOS-REQUERIDOS.md` | Los 173 procesos, sus roles y sus tablas. |
| `db/schema.sql` | Las 41 tablas, sus columnas y sus nombres reales. |
| `CLAUDE.md` | Las **decisiones del dueño**: el porqué que no se deduce leyendo. |
| `docs/ESTADO-ACTUAL.md` | Qué está hecho, qué falta y qué no se probó. |
| `docs/RESUMEN-PARA-CLAUDE-CODE.md` | Por qué el esquema es como es. |

Cuando el código contradiga a un documento, **explicá el código y anotá la
discrepancia** en el capítulo, en una nota marcada. No la corrijas en el documento
original y no la escondas.

---

## 8. Entregables

En `docs/masterclass/`, un archivo por capítulo, numerado para que ordene solo:

```
docs/masterclass/
├── 00-indice.md                    ← índice navegable + tabla de ruteo (sección 3)
├── A0-01-como-corre-un-programa.md … A0-14-vision-en-el-dispositivo.md
├── A-01-que-es-olimpos.md … A-12-como-leer-los-procesos.md
├── A-98-glosario.md
├── A-99-mapa-de-conexiones.md
├── B-01-acceso-y-sesion.md … B-15-procesos-automaticos.md
└── C-01-contador-reps.md … C-08-demonio-videos.md
```

**No toques ningún otro archivo del repo.** En particular: no edites
`PROCESOS-LOGICOS-REQUERIDOS.md`, `CLAUDE.md` ni `docs/ESTADO-ACTUAL.md`.

---

## 9. Las trampas: que la masterclass no las repita

Hay cosas que parecen bugs y son decisiones, documentadas en `CLAUDE.md`. Si tu
explicación de alguna suena a disculpa o a "esto habría que arreglarlo", está mal
escrita: **explicá la decisión y su motivo.**

Que no exista tabla `Deuda` · que no se pueda cobrar por adelantado (el 409) ·
`es_adelanto` siempre en false · `Rutina.nivel` sin usar · el RFID que parece código
muerto y no lo es · `Usuario.activo` y `Socio.activo` desacoplados · el botón de
patologías que se **omite** en vez de deshabilitarse · el mail que abre Gmail y no
`mailto:` · los gráficos sin librería · la matriz de permisos y la paleta triplicadas ·
que no exista "Registrarse" · V-08 y V-10 como decisiones conscientes.

Y del lado técnico, código que está bien aunque parezca raro: `alpha()` en vez de
`f"{color}20"` en Flet · el `scroll` en la Column interna · `on_select` y no `on_change`
en `ft.Dropdown` · `100dvh` y nunca `h-screen` · `shrink-0 whitespace-nowrap` en los
botones.

---

## 10. Control de calidad, antes de dar un capítulo por terminado

1. **Todo rango de líneas fue verificado abriendo el archivo.** Sin excepción.
2. **Todo símbolo citado existe** con ese nombre exacto.
3. **Ninguna caja negra quedó sin abrir**: el capítulo llegó a su piso declarado.
4. **El descenso volvió a subir**: cada bajada termina apuntando a código de este repo.
5. **Ningún concepto se explica dos veces.** Buscá en el capítulo "como vimos", "dicho de
   otra manera", "repasemos", "visto desde": cada aparición es sospechosa de redundancia
   y hay que reemplazarla por un enlace, salvo que cumpla una de las dos condiciones de
   la sección 2.5 y lo diga.
6. **La profundidad se gastó bajando, no repitiendo.** Si el capítulo es largo, tiene que
   ser porque llegó al piso o porque hizo ingeniería inversa, nunca por acumular ángulos.
7. **Hay ingeniería inversa donde hay una decisión**, y no la hay donde no la hay.
8. **El apartado "Con qué se conecta" está**, es de una línea por viñeta, y sus enlaces
   existen.
9. **Los 173 procesos tienen capítulo**, ninguno saltado, numeración igual al original.
10. **Cada tabla de la línea DFD aparece** en "qué escribe y qué lee".
11. **Ningún término se usó antes de definirse**, y todo lo definido está en el glosario.
12. **Cero frases de relleno.** Buscá "se encarga de", "maneja la lógica", "realiza las
    validaciones correspondientes": si aparecen, reescribí el párrafo con lo que hace de
    verdad.
13. **La prueba final, en dos partes:** un lector que no conoce el repo puede, con tu
    capítulo abierto, encontrar el código y entender por qué está escrito así, **sin
    quedarse con ninguna pregunta cuya respuesta sea "y eso cómo funciona por dentro"**
    y **sin haber leído dos veces la misma cosa**. Las dos partes pesan igual.

---

## 11. Cómo repartir el trabajo

Si esto se ejecuta con varios agentes en paralelo, el corte natural es:

- **A0 y A los escribe un solo autor, primero, y en ese orden.** Son los que fijan el
  vocabulario y el grafo de conexiones: si los escriben varios en paralelo, cada capítulo
  inventa sus propios términos y se pierde justamente lo que esta masterclass busca. El
  capítulo 4 de A (el recorrido completo) es el que más rinde revisar dos veces.
- **La Parte B se reparte por sección**, que ya vienen del tamaño justo. Las dos grandes
  —Socios (23) y Portal del socio (46)— conviene partirlas en dos cada una. Todos los
  autores reciben A0 y A ya escritos, para usar su vocabulario y no redefinir nada.
- **La Parte C se reparte por capítulo**, que son independientes entre sí.
- **Al final, un paso de coherencia**: que los enlaces del índice resuelvan, que el
  glosario cubra todo lo definido, que el mapa de conexiones no tenga puntas sueltas y
  que ningún capítulo redefina un término de otro.
