# A0-04 · El navegador por dentro

> **Piso de este capítulo: el píxel pintado y la intercepción del pedido.** Bajamos desde
> el texto que llega por la red hasta el momento exacto en que un valor se convierte en
> luz en la pantalla, y hasta el punto en que un pedido saliente puede ser atrapado antes
> de tocar la red.

---

## Por qué hay un capítulo entero sobre esto

El capítulo anterior terminó con un [pedido y una respuesta HTTP](A0-03-http.md#pedido-y-respuesta-http)
viajando como texto. Ese texto llega a algún lado. Ese algún lado es el navegador, y la
pregunta de este capítulo es qué hace con él.

La respuesta cambió por completo dos veces. El navegador nació en 1990, con el
WorldWideWeb de Tim Berners-Lee, como **un visor de documentos**: recibía marcado,
lo formateaba y lo mostraba. Punto. Cualquier cambio en lo que se veía exigía pedir el
documento entero otra vez, porque no había nada del lado del cliente que pudiera
modificar la página ya mostrada.

Ese modelo tiene un límite muy concreto, y el problema que lo reveló fue tan chico como
esto: un formulario con un campo mal completado obligaba a un viaje de ida y vuelta al
servidor para decir "el DNI tiene letras". En 1995, con conexiones telefónicas, eso eran
varios segundos para informar un error que la máquina que tenía el dato adelante podía
detectar sola. Netscape le encargó a Brendan Eich un lenguaje embebido para resolverlo, y
lo que hizo falta para que ese lenguaje sirviera de algo fue **darle algo que tocar**: una
representación de la página, viva, en memoria, modificable. Ese es el origen del DOM, y de
ahí en adelante todo lo que hay en este capítulo es una pieza más agregada al mismo
proyecto: convertir un visor de documentos en una plataforma donde corren programas.

OlimpOS vive de ese proyecto terminado. La PWA no es un sitio con formularios: es una
aplicación que dibuja tarjetas, abre la cámara, cuenta repeticiones a 30 cuadros por
segundo y guarda trabajo pendiente cuando no hay wifi. Nada de eso es posible en un visor
de documentos, y cada una de las ocho piezas de este capítulo es lo que lo hace posible.

**Un navegador es, como programa, varios [procesos](A0-01-como-corre-un-programa.md#proceso-y-espacio-de-direcciones)
a la vez**, no uno. Hay un proceso coordinador —el que dibuja las pestañas, la barra de
direcciones y habla con el sistema operativo— y hay procesos *de render*, en general uno
por sitio abierto, que son los que arman la página y ejecutan su código. Que sean procesos
separados no es una decisión de rendimiento: es la política de seguridad de la sección
["Origen y política del mismo origen"](#origen-y-política-del-mismo-origen) llevada hasta
el [espacio de direcciones](A0-01-como-corre-un-programa.md#proceso-y-espacio-de-direcciones),
donde el sistema operativo la hace cumplir aunque el navegador tenga un error. Cuando en
este capítulo se diga "el navegador hace X", en casi todos los casos quien lo hace es el
proceso de render de esa pestaña.

---

## DOM

**El problema que vino a resolver.** El documento llega como texto y se muestra una vez.
Para que un programa pueda cambiar lo que se ve sin pedir el documento otra vez, tiene que
existir una representación de ese documento que el programa pueda leer y escribir. El DOM
—*Document Object Model*— es esa representación: el documento convertido en objetos.

La primera versión, la de Netscape 2 en 1995, era ridículamente chica: se podía llegar a
los formularios y a las imágenes, y a nada más. Se la llama retrospectivamente "DOM nivel
0". Lo que vino después —poder crear, mover y borrar cualquier nodo— es la generalización
de esa idea, estandarizada por el W3C recién a partir de 1998, después de años en que
Netscape e Internet Explorer tenían cada uno el suyo.

> **↓ Capa 1 — qué es el DOM, exactamente.** Salteable si ya lo sabés.

Es **un árbol**. Cada etiqueta del marcado es un nodo, cada nodo tiene un padre y una
lista ordenada de hijos, y cada texto suelto entre etiquetas también es un nodo. El
documento de la PWA, `Proyecto - PWA/src/frontend/index.html`, produce un árbol cuya raíz
es `html`, con dos hijos —`head` (líneas 3-29) y `body` (30-33)— y con un solo nodo de
contenido real: `<div id="root">` en la línea 31. Todo lo que ve un socio o un
recepcionista cuelga de ese único `div` vacío.

El árbol no es el texto. Es el resultado de interpretarlo, y el navegador corrige mientras
interpreta: cierra etiquetas que faltaban, mueve contenido que estaba en un lugar ilegal,
inventa un `tbody` si hace falta. Por eso dos archivos distintos pueden producir el mismo
árbol, y por eso mirar el marcado original y mirar el DOM en las herramientas del
navegador a veces no coincide.

> **↓ Capa 2 — cómo se construye, paso a paso.** Salteable si ya lo sabés.

El proceso de render recibe los bytes de la respuesta y los atraviesa en dos etapas:

1. **Tokenizador.** Lee byte a byte y emite piezas: "etiqueta de apertura `div` con
   atributo `id` valor `root`", "texto", "etiqueta de cierre". Es una máquina de estados
   que nunca falla: cualquier secuencia de bytes produce algún resultado.
2. **Constructor de árbol.** Consume esas piezas y mantiene una pila de elementos
   abiertos; cada apertura empuja un nodo y lo cuelga del que está arriba de la pila, cada
   cierre desapila.

La construcción es **incremental**: el árbol se va armando mientras los bytes llegan, y el
navegador puede empezar a mostrar antes de que la respuesta termine. Eso se rompe con los
scripts: al encontrar un `<script>` sin marcar, el constructor **se detiene** —el script
podría insertar marcado en ese mismo punto— hasta que el script se baje y se ejecute. Por
eso el de la línea 32 dice `type="module"`: un módulo se difiere por definición, se ejecuta
recién cuando el documento terminó de parsearse, y la construcción del árbol no se frena
esperándolo.

> **↓ Capa 3 — el piso: el nodo en memoria.** Acá termina el descenso de este concepto.

Un nodo no es una abstracción: es **un objeto en el montón del proceso de render**, con
campos para su etiqueta, sus atributos, un puntero al padre, punteros a los hermanos y a
los hijos, y un puntero a los estilos que le corresponden. Cuando el código pide un nodo,
lo que recibe es una **referencia a ese objeto**, no una copia: escribirle un atributo
escribe en la memoria de ese proceso, y por eso el efecto es inmediato y por eso lo que
una pestaña haga no puede tocar el árbol de otra.

Eso se ve en una sola línea de este repo. En
`Proyecto - PWA/src/frontend/src/main.tsx:6` · `createRoot(...)`:

```tsx
createRoot(document.getElementById('root')!).render(
```

`document.getElementById('root')` recorre el árbol buscando el nodo cuyo atributo `id`
vale `root` y devuelve la referencia a ese objeto. Es el único punto de todo el sistema
donde alguien agarra un nodo a mano para construir la aplicación encima. De ahí en
adelante, quien crea, mueve y borra nodos es React ([A0-06](A0-06-react.md#árbol-virtual-y-reconciliación)),
y por eso conviene ver con números cuán poco se toca el DOM directamente en la PWA. Un
`grep` por `document.`, `window.` y `navigator.` sobre `src/` devuelve **catorce
apariciones** fuera del contador de repeticiones, y ninguna crea un nodo:

| Archivo y línea | Qué hace |
|---|---|
| `src/main.tsx:6` | monta la aplicación en `#root` |
| `src/services/api.ts:102` | lee `document.cookie` |
| `src/utils/colaRegistros.ts:153` | escucha el evento `online` |
| `src/utils/dispositivo.ts:10,14-16` | consulta `navigator.mediaDevices` y dos `matchMedia` |
| `src/views/socio/CircuitoView.tsx:82,98,110,112,116` | pantalla completa, bloqueo de apagado y visibilidad |
| `src/views/socio/MiCuotaView.tsx:185` | navega a la URL de pago con `window.location.href` |
| `src/views/socio/useCircuito.ts:140` | vibración del teléfono |
| `src/components/PanelCredenciales.tsx:65` | copia al portapapeles |

Las catorce son **capacidades del dispositivo** —la cámara, el portapapeles, la vibración,
la pantalla— o **lectura de estado del navegador**. Ninguna es manipulación de la página.
Esa separación tan limpia no es casualidad: es exactamente lo que React vino a comprar, y
el capítulo que lo explica es [A0-06](A0-06-react.md).

---

## Motor de render y canvas

**El problema que vino a resolver.** Un árbol de nodos dice *qué* hay, y no dice *dónde*
ni *de qué color*. Al principio eso estaba mezclado: el marcado traía etiquetas como
`<font>` y `<center>`, y cambiar el aspecto de un sitio significaba editar cada documento.
Håkon Wium Lie propuso en 1994 separar las dos cosas en hojas de estilo, y CSS 1 salió en
1996. Desde entonces el navegador tiene dos entradas —el árbol y las reglas de estilo— y
un trabajo: producir una imagen.

> **↓ Capa 1 — la cadena de cinco pasos.** Salteable si ya la sabés.

1. **Estilo.** Las reglas de todas las hojas se combinan con el árbol y a cada nodo le
   queda un valor final para cada propiedad. Acá se resuelven la herencia, la cascada y la
   especificidad.
2. **Distribución (*layout*).** Con los estilos resueltos, el motor calcula para cada
   elemento **una caja**: posición x/y y tamaño en píxeles CSS, recorriendo el árbol de
   arriba abajo y de abajo arriba según el tipo de caja. Acá es donde un porcentaje se
   convierte en un número.
3. **Pintado (*paint*).** Cada caja se traduce a una **lista de órdenes de dibujo**:
   "rectángulo relleno de `#1C1F26` con esquinas de 10 px", "este texto con esta fuente en
   esta posición". Todavía no hay píxeles: hay instrucciones.
4. **Composición.** Las listas se reparten en **capas**, se rasterizan (ahí sí se
   convierten en mapas de píxeles, normalmente en la GPU) y se apilan en el orden
   correcto.
5. **Presentación.** El fotograma resultante se entrega a la pantalla.

Lo que importa de esta cadena es **cuánto cuesta rehacer cada paso**. Cambiar un color de
fondo obliga a rehacer del 3 en adelante. Cambiar un ancho obliga a rehacer del 2, y el 2
puede propagarse a media página. Mover una capa que ya está rasterizada no obliga a nada
más que al 4. Es la razón por la que dos cambios que en el código se escriben igual
pueden costar órdenes de magnitud distintas.

> **↓ Capa 2 — el piso: el píxel pintado.** Acá termina el descenso de este concepto.

Rasterizar es evaluar, para cada píxel de una capa, qué color le corresponde según las
órdenes de dibujo que lo cubren, mezclando por transparencia de atrás hacia adelante. El
resultado es un arreglo de enteros, cuatro canales por píxel. Ese arreglo se sube como
textura, el compositor las apila en el orden de las capas y el sistema operativo entrega
el fotograma a la pantalla. **Ese entero es el píxel pintado, y es el piso de este
capítulo.**

### Dónde se ve la distribución en este repo

En `Proyecto - PWA/src/frontend/src/layout/AppLayout.tsx:11-18` hay documentado un error
que es puro paso 2, y vale la pena porque el síntoma no se parece a la causa. El
contenedor principal usaba una altura *mínima*, así que crecía con el contenido; la caja
calculada nunca era más chica que lo que tenía adentro, de modo que el `overflow-y-auto`
del `<main>` **no tenía contra qué desbordar** y no se activaba nunca. El que scrolleaba
era el documento entero, y la barra lateral —que no está fijada— se iba con él. La
corrección, en la línea 33, es fijar la altura del contenedor (`h-full`) para que el
desborde ocurra adentro:

```tsx
<div className="flex h-full overflow-hidden bg-surface-base">
```

Un contenedor con altura y desbordamiento oculto obliga a que el hijo con
`overflow-y-auto` se haga cargo de su propio scroll. La caja calculada es la que manda.

### Canvas

**El problema que vino a resolver.** Todo lo anterior supone que lo que se dibuja son
elementos: cajas con estilo, en un árbol. Hay cosas que no son eso —un gráfico, un juego,
el esqueleto de una persona sobre un video— y forzarlas al árbol significa crear y
destruir cientos de nodos por fotograma, con estilo, distribución y pintado para cada uno.
Apple resolvió esto en 2004 para los *widgets* de Dashboard con un elemento nuevo, y se
estandarizó después: **`<canvas>` es un nodo sin hijos que expone una superficie de
píxeles y un juego de órdenes de dibujo**.

El canvas saltea los pasos 1 y 2 de la cadena. No hay estilo por elemento ni distribución
por elemento porque adentro no hay elementos: hay una matriz de píxeles y una API que
escribe sobre ella. Lo que se paga es todo lo que el árbol daba gratis: el texto no se
selecciona, no hay accesibilidad, no hay eventos por forma, no hay nada que un lector de
pantalla pueda recorrer. Es un intercambio consciente, no un atajo.

En OlimpOS hay exactamente un canvas, y es el del contador de repeticiones. En
`Proyecto - PWA/src/frontend/src/views/socio/ContadorReps.tsx:607-608` · `ContadorReps`:

```tsx
<video ref={videoRef} playsInline muted className="absolute inset-0 h-full w-full object-cover" />
<canvas ref={canvasRef} className="absolute inset-0 h-full w-full object-cover" />
```

Dos nodos superpuestos: abajo el video crudo de la cámara, arriba un canvas transparente
donde se dibujan los puntos y las líneas del esqueleto. En `ContadorReps.tsx:229-235` se
toma el contexto de dibujo y se ajusta el tamaño de la superficie al del video:

```tsx
if (canvas.width !== video.videoWidth) {
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  drawRef.current = new DrawingUtils(canvas.getContext('2d')!);
}
const ctx = canvas.getContext('2d')!;
ctx.clearRect(0, 0, canvas.width, canvas.height);
```

`getContext('2d')` devuelve el objeto con las órdenes de dibujo; `clearRect` borra toda la
superficie. Eso pasa **una vez por fotograma**, y después se dibujan 33 puntos y sus
conexiones (`ContadorReps.tsx:241-255`). Con nodos eso serían 33 elementos creados y
destruidos treinta veces por segundo, cada uno con su paso de estilo y de distribución.
Con canvas son 33 órdenes de dibujo sobre una textura que ya existe. Esa es la razón
técnica de que el esqueleto se dibuje así y no con elementos.

Flutter lleva esta misma idea hasta el final: no dibuja *algunas* cosas sobre una
superficie, dibuja **todas**. Ese es el
[canvas de Flutter](A0-13-flutter-y-flet.md#canvas-de-flutter), que es otra cosa que el
del navegador aunque se llame igual, y es lo que hace que la app de escritorio se vea
idéntica en cualquier sistema.

---

## Bucle de eventos, tarea y microtarea, promesa y `async`/`await`

**El problema que vino a resolver.** El DOM es estado mutable compartido: un árbol que
cualquier parte del programa puede modificar. Si dos hilos lo tocaran a la vez habría que
poner candados en cada nodo, y cualquier código de página podría dejar el árbol a medio
modificar mientras el motor de render lo lee. La decisión de Netscape, que sigue vigente
treinta años después, fue radical y simple: **el código de una página corre en un solo
hilo**. Ese hilo no puede bloquearse esperando nada, porque también es el que atiende los
clicks y el que le abre la ventana al motor de render. De esa restricción sale todo lo
demás: si no podés esperar, tenés que pedir y seguir, y que te avisen.

> **↓ Capa 1 — el bucle y sus dos colas.** Salteable si ya lo sabés.

El hilo no corre "el programa": corre **un bucle**. En cada vuelta:

1. Toma **una** tarea de la cola de tareas y la ejecuta **hasta el final**. Una tarea es
   el trabajo completo asociado a un evento: el manejador de un click, el vencimiento de
   un temporizador, la llegada de una respuesta de red, la ejecución inicial del script.
   Nadie la interrumpe: esto se llama *run to completion*, y es lo que permite que ningún
   candado haga falta.
2. Vacía **entera** la cola de microtareas. Una microtarea es la continuación de una
   promesa. Si una microtarea encola otra, esa también se ejecuta en esta misma vuelta, y
   la siguiente, y la siguiente: la cola se vacía hasta quedar en cero.
3. Si es momento de mostrar un fotograma, corre las devoluciones de
   `requestAnimationFrame` y después le da paso al motor de render para que haga estilo,
   distribución, pintado y composición.
4. Vuelve al paso 1.

La diferencia entre las dos colas importa y se nota: las microtareas **se cuelan antes**
que cualquier tarea pendiente y antes de cualquier pintado. Un encadenamiento de promesas
que nunca termina congela la pantalla sin que haya ningún bucle infinito a la vista.

> **↓ Capa 2 — la promesa, y qué es exactamente `await`.** Salteable si ya lo sabés.

Antes de las promesas, "avisame cuando esté" se escribía pasando una función como
argumento. Eso funciona para un paso; para cinco encadenados produce anidamiento y, sobre
todo, **no hay forma de propagar un error** hacia afuera: cada nivel tiene que manejar el
suyo. La promesa es la respuesta: un objeto que representa un valor que todavía no está,
con tres estados posibles —pendiente, cumplida, rechazada—, que pasa de pendiente a uno de
los otros dos **una sola vez** y para siempre.

Lo que hace `.then(f)` es registrar `f` para que el bucle la ponga en la cola de
microtareas cuando la promesa se resuelva. Si ya estaba resuelta, la encola igual, en la
próxima vuelta: nunca corre de forma síncrona. Esa garantía es la que hace que el orden
sea predecible.

`async`/`await` es notación para lo mismo, no un mecanismo nuevo. Una función marcada
`async` devuelve siempre una promesa. Un `await` adentro de ella hace tres cosas: **suspende
la función en ese punto guardando su estado** —variables locales y punto de retorno—,
devuelve el control al bucle, y registra la reanudación como microtarea de la promesa que
esperó. Cuando el bucle la toma, la función sigue desde exactamente donde estaba, como si
nunca se hubiera ido. El hilo, mientras tanto, atendió clicks.

Por eso `await` no bloquea nada aunque se lea como si bloqueara, y por eso `await` sobre
un cálculo largo no sirve para nada: lo que libera el hilo es la suspensión, y sólo se
suspende ante algo que se resuelve más tarde. **Esperar la red no bloquea; calcular sí.**

> **↓ Capa 3 — el piso: la cola vaciándose, fotograma por fotograma.** Acá termina el
> descenso de este concepto.

El caso más nítido del repo es el bucle del contador de repeticiones, en
`ContadorReps.tsx:222-290` · `bucle()`. La última línea del cuerpo, en la 289, es:

```tsx
rafRef.current = requestAnimationFrame(bucle);
```

`requestAnimationFrame` no es un temporizador: inserta la función en el **paso 3** del
bucle de la próxima vuelta que vaya a producir un fotograma. Es decir, el contador se
vuelve a ejecutar exactamente una vez por fotograma, sincronizado con el pintado, y el
navegador lo deja de llamar cuando la pestaña no está visible —no hay fotograma que
producir—. Nada de eso se programó: se obtiene por usar la función correcta.

Adentro de ese fotograma, en la línea 237, hay una llamada **síncrona**:

```tsx
const res = lm.detectForVideo(video, performance.now());
```

La inferencia del modelo no devuelve una promesa: ocurre ahí, en el hilo, dentro de la
misma tarea. Eso significa que el presupuesto de un fotograma —16,6 ms si la pantalla va a
60 Hz— se reparte entre la inferencia, el borrado y dibujado del canvas, y el re-render de
React que dispara `setReps((n) => n + 1)` en la línea 277. Si la suma se pasa, el navegador
no se cuelga: **simplemente pinta menos fotogramas**, porque la vuelta siguiente del bucle
llega más tarde. El contador pierde suavidad y capacidad de detectar una repetición rápida,
no correctitud. Esa es la diferencia práctica entre un hilo saturado y un hilo bloqueado, y
es la razón por la que en la línea 169 se intenta primero con el delegado de GPU
(`crear('GPU')`) y sólo si falla se cae a CPU (línea 171): mover la inferencia fuera del
hilo del bucle es lo que devuelve presupuesto de fotograma.

Del otro lado del mismo mecanismo está lo que el navegador hace cuando decide que la
pestaña no merece atención. En `CircuitoView.tsx:109-112`, el circuito vuelve a pedir el
bloqueo de apagado de pantalla cada vez que la pestaña se hace visible:

```tsx
const alVolver = () => {
  if (document.visibilityState === 'visible') void pedir();
};
document.addEventListener('visibilitychange', alVolver);
```

El sistema suelta ese bloqueo al cambiar de aplicación, y el comentario de las líneas
106-107 dice el porqué: si no se vuelve a pedir, la pantalla se apaga en medio del
descanso. El bucle de eventos de una pestaña en segundo plano se atiende con cuentagotas;
todo lo que dependa de que la pestaña siga corriendo tiene que reconstruirse al volver.

El bucle de eventos de Python, del lado del servidor, es la misma idea con otras piezas y
otro candado, y se explica en [A0-10](A0-10-python-del-lado-del-servidor.md#corrutina).

---

## `fetch`

**El problema que vino a resolver.** Con DOM y con un bucle de eventos ya se puede cambiar
la página sin recargarla, pero los datos nuevos siguen estando del otro lado de la red y
la única forma de traerlos era navegar, que destruye la página entera. El equipo de
Outlook Web Access en Microsoft agregó un objeto para pedir datos sin navegar —lo que
después se llamó `XMLHttpRequest`—, Mozilla y el resto lo copiaron, y en 2005 el término
"AJAX" le puso nombre a la técnica. Esa API estaba construida sobre un objeto mutable con
estados numerados y devoluciones de llamada; `fetch`, estandarizado en 2015, la rehízo
sobre promesas y sobre un modelo explícito de pedido y respuesta.

> **↓ Capa 1 — qué devuelve y cuándo.** Salteable si ya lo sabés.

`fetch(url, opciones)` devuelve una promesa que se resuelve **cuando llegan las cabeceras
de la respuesta**, no cuando terminó el cuerpo. Lo que trae es un objeto `Response` con el
[código de estado](A0-03-http.md#código-de-estado) y las
[cabeceras](A0-03-http.md#cabecera-http) ya disponibles, y con el cuerpo todavía como un
flujo por leer. Leerlo es una segunda promesa: `respuesta.json()`.

Y hay una regla que sorprende a todo el mundo la primera vez: **la promesa de `fetch` no
se rechaza por un código de error**. Un 404, un 409 y un 500 son respuestas que llegaron
bien; la promesa se cumple y el status viene adentro. Sólo se rechaza si **no hubo
respuesta**: la red cayó, el nombre no resolvió, la política de origen bloqueó la lectura,
o alguien abortó el pedido. Está escrito tal cual en
`Proyecto - PWA/src/frontend/src/services/api.ts:222-223`.

> **↓ Capa 2 — el piso: el pedido saliendo del navegador.** Acá termina el descenso de
> este concepto.

Entre la llamada y el cable, el navegador hace cinco cosas:

1. **Resuelve la URL** contra la de la página. `'/api/...'` es relativa: hereda esquema,
   host y puerto de la página que la ejecuta. Esto es central en este sistema y se retoma
   más abajo.
2. **Aplica las reglas de origen** y decide si el pedido se manda directo, si necesita un
   pedido previo, y —lo que decide el punto siguiente— si adjunta las cookies.
3. **Adjunta o no las [cookies](A0-12-sesiones-y-autenticacion.md#cookie-y-sus-atributos)**
   según la opción `credentials`, cuyo valor por omisión es "sólo si el pedido es del
   mismo origen".
4. **Agrega las cabeceras que pone él**: `Host`, `Origin` en los métodos que modifican,
   `Accept`, `User-Agent`, `Content-Length`, las de codificación.
5. **Consigue una conexión**: reusa una [conexión TCP](A0-02-como-se-comunican-dos-maquinas.md#tcp-y-el-viaje-de-ida-y-vuelta-rtt)
   ya abierta con ese host si la hay, y si no abre una —con su
   [saludo de TLS](A0-02-como-se-comunican-dos-maquinas.md#tls) si corresponde— y recién
   ahí escribe los bytes.

Esto es lo que sale literalmente del navegador cuando un socio termina una serie en el
contador de repeticiones, con el pedido que arma
`src/services/socioService.ts:803-813` · `guardarRegistroEjercicio()`:

```http
POST /api/portal/mi-rutina/registro-ejercicio HTTP/1.1
Host: localhost:5173
Origin: http://localhost:5173
Content-Type: application/json
X-CSRF-Token: <el valor de la cookie olimpos_csrf>
Cookie: olimpos_session=<el JWT>; olimpos_csrf=<el mismo valor>
Content-Length: 68

{"id_ejercicio":31,"repeticiones":12,"peso":40,"observaciones":null}
```

Los nombres de esas dos cookies son los de `backend/cookies.py:45` y `backend/cookies.py:51`
(`COOKIE_SESION` y `COOKIE_CSRF`). Qué son y por qué son dos lo explica
[A0-12](A0-12-sesiones-y-autenticacion.md#cookie-y-sus-atributos); acá lo que importa es
que **el navegador las escribió solo**: en el código de la PWA no hay ninguna línea que
arme esa cabecera.

### Un solo lugar en toda la PWA

Un `grep -rn "fetch("` sobre `src/` devuelve **una sola coincidencia**:
`src/services/api.ts:210`, dentro de `pedir()`. Las quince capas de servicio de la PWA
pasan por esa función y ninguna toca la red por su cuenta. Vale la pena mirar cinco
decisiones que están concentradas ahí gracias a eso:

```tsx
respuesta = await fetch(`${API_URL}${ruta}`, {
  method: metodo,
  headers,
  credentials: 'include',
  signal: AbortSignal.timeout(TIMEOUT_MS),
  body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
});
```

- **`credentials: 'include'`** (línea 217) fuerza el envío de las cookies aunque el pedido
  no sea del mismo origen. En el camino normal de este sistema el pedido **ya es** del
  mismo origen —por el proxy—, así que no cambia nada; está para el caso en que
  `VITE_API_URL` apunte a otro host. El comentario de las líneas 213-216 describe
  precisamente ese escenario sin proxy.
- **`AbortSignal.timeout(15_000)`** (líneas 184 y 218). `fetch` **no tiene tiempo máximo
  propio**: si el servidor acepta la conexión y después no contesta, la promesa queda
  pendiente para siempre y la pantalla se queda cargando sin error. Un `AbortSignal` es la
  única forma de cortarlo desde afuera, y cuando dispara, `fetch` rechaza con una
  excepción cuyo nombre es `TimeoutError` — que es lo que se distingue en la línea 224.
- **El cuerpo se serializa acá** (línea 219): un objeto de JavaScript se convierte en la
  cadena [JSON](A0-03-http.md#json-como-cuerpo) que viaja, y en la 234 la respuesta se
  parsea de vuelta. Los tipos no sobreviven ese viaje; lo que se pierde ahí lo explica
  [A0-05](A0-05-javascript-y-typescript.md#frontera-de-confianza-del-tipo).
- **El 204 se corta antes de parsear** (línea 230): una respuesta sin contenido no tiene
  JSON que leer, y `respuesta.json()` sobre un cuerpo vacío rechaza.
- **El fallo de red se reporta como status 0** (líneas 225 y 227), un valor que no existe
  en HTTP, para que las pantallas manejen "el backend dijo que no" y "el backend no
  contestó" con el mismo tipo de error. De esa convención depende la cola del contador de
  repeticiones, que en `src/utils/colaRegistros.ts:107` trata el 0 como transitorio y
  conserva la serie.

---

## Origen y política del mismo origen

**El problema que vino a resolver.** Apenas existió un lenguaje que puede leer el DOM,
existió este agujero: si una página abre otra en un marco o en una ventana, y su código
puede leer el DOM de esa otra, entonces un sitio cualquiera puede abrir el del banco, leer
el saldo, leer el formulario, leer todo. La primera versión de JavaScript, en Netscape
Navigator 2 (1995), llegó con la regla que lo tapa, y es la regla más importante de la
seguridad web: **el código de un origen no puede leer los recursos de otro origen.**

> **↓ Capa 1 — qué es un origen.** Salteable si ya lo sabés.

Un origen es una **tripla**: esquema, host y puerto. Se comparan los tres, exactos, sin
interpretación. `http://localhost:5173` y `http://127.0.0.1:8000` son orígenes distintos
dos veces: el host es distinto —`localhost` y `127.0.0.1` son cadenas diferentes aunque
resuelvan a la misma máquina— y el [puerto](A0-02-como-se-comunican-dos-maquinas.md#puerto)
también. `http://ejemplo.com` y `https://ejemplo.com` son orígenes distintos por el
esquema, aunque para una persona sean "el mismo sitio".

> **↓ Capa 2 — el piso: la comparación, y qué prohíbe exactamente.** Acá termina el
> descenso de este concepto.

La comparación es literalmente esa: tres igualdades de cadenas y un número. Lo sutil es el
alcance de la prohibición, porque casi todos los problemas de seguridad de la web viven en
esa distinción:

- **Prohibido leer.** El código de un origen no puede leer el DOM de otro, ni el cuerpo de
  una respuesta de otro origen, ni las cookies de otro host.
- **Permitido mandar.** Un origen **sí** puede provocar que el navegador mande pedidos a
  otro: una imagen, un formulario, un `fetch`. El pedido sale, el servidor lo procesa, y
  lo único que el atacante no consigue es **leer la respuesta**.

Esa asimetría —mandar sí, leer no— es la que hace posible el ataque que se explica en
[A0-12](A0-12-sesiones-y-autenticacion.md#csrf), y es también la que hace posible la
defensa que este sistema usa, en `src/services/api.ts:101-104` · `tokenCsrf()`:

```tsx
function tokenCsrf(): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|;\\s*)${COOKIE_CSRF}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}
```

El comentario de las líneas 95-99 lo dice en una frase: un sitio atacante puede hacer que
el navegador **mande** nuestras cookies, pero no puede **leerlas**, así que no puede copiar
ese valor a una cabecera. El mecanismo completo es el
[token CSRF de doble envío](A0-12-sesiones-y-autenticacion.md#token-csrf-de-doble-envío);
lo que aporta este capítulo es de dónde sale su poder: de la línea de arriba, que sólo
funciona porque el origen coincide.

La excepción reglamentada a todo esto —cómo un servidor autoriza que otro origen lea sus
respuestas— es [CORS](A0-12-sesiones-y-autenticacion.md#cors-y-preflight).

### Por qué existe el proxy `/api`

Este sistema **elimina el problema en vez de administrarlo**. En
`Proyecto - PWA/src/frontend/vite.config.ts:55-62` el servidor de desarrollo declara:

```ts
proxy: {
  '/api': {
    target: destinoApi,
    changeOrigin: false,   // conserva el Host, así la cookie queda en localhost
    rewrite: (ruta) => ruta.replace(/^\/api/, ''),
  },
},
```

Y en `src/services/api.ts:56` la base de la API es relativa:

```tsx
const API_URL = import.meta.env.VITE_API_URL ?? '/api';
```

Con eso, **el navegador nunca ve otro origen**. Todo sale a `http://localhost:5173/api/...`,
que es el origen de la página; el servidor de desarrollo actúa como
[proxy inverso](A0-03-http.md#proxy-inverso), le saca el prefijo `/api` y reenvía al
backend real. Consecuencias, todas verificables en ese archivo:

- No hay pedido a otro origen, así que **CORS no interviene en ningún momento** (el
  comentario de las líneas 40-41 lo dice).
- La cookie queda registrada bajo `localhost`, así que `document.cookie` la puede leer y el
  token CSRF es alcanzable.
- `changeOrigin: false` (línea 58) es deliberado: cambiar el `Host` al reenviar haría que
  el backend emitiera la cookie para el host del backend, y volvería el problema por otra
  puerta.

Las líneas 43-46 del mismo archivo agregan la parte estratégica: esto **no es una muleta
de desarrollo**. En producción la PWA y la API van a estar detrás del mismo dominio, así
que el proxy hace que el entorno de desarrollo se parezca a producción en vez de diferir
de ella. La app de escritorio no pasa por acá y no le hace falta: no es una página, no
tiene origen y no arrastra cookies.

---

## Almacenamiento del navegador

**El problema que vino a resolver.** Hasta 2009, el único lugar donde una página podía
guardar algo en el dispositivo era la cookie, y la cookie tiene dos defectos como almacén:
pesa poco —unos 4 KB— y, sobre todo, **viaja en cada pedido al servidor**, se la necesite o
no. Guardar ahí las preferencias de una interfaz significa pagar esos bytes en cada uno de
los cientos de pedidos que hace un sitio. `localStorage`, que llegó con HTML5 tras un
experimento previo de Firefox, resuelve exactamente eso: unos 5 MB por origen que **nunca
se mandan a ningún lado**.

> **↓ Capa 1 — los tres almacenes y en qué se diferencian.** Salteable si ya lo sabés.

| Almacén | Vive | Forma | Acceso |
|---|---|---|---|
| `localStorage` | hasta que alguien lo borre | cadena → cadena | síncrono |
| `sessionStorage` | mientras viva la pestaña | cadena → cadena | síncrono |
| IndexedDB | hasta que alguien lo borre | objetos y archivos binarios, con índices | asíncrono |

Los tres están **particionados por origen**: el almacén de `http://localhost:5173` y el de
`https://ejemplo.com` son dos cosas distintas, y ninguna página puede llegar a la otra. Es
la misma regla de la sección anterior, aplicada al disco.

Que `localStorage` sea síncrono tiene una consecuencia directa sobre el bucle de eventos:
leer o escribir ahí **detiene el hilo** hasta que termina. Con claves chicas es
imperceptible; con un objeto grande y serializado en cada cambio, no.

> **↓ Capa 2 — el piso: el byte guardado en el perfil.** Acá termina el descenso de este
> concepto.

`localStorage.setItem(clave, valor)` no escribe un archivo por clave. El proceso de render
le pasa el par al proceso del navegador, que lo escribe en una base incrustada dentro de la
carpeta de perfil del usuario, **agrupada por origen** (en los navegadores basados en
Chromium, una base LevelDB bajo el directorio `Local Storage`). Los hechos que se derivan
de eso son los que hay que tener presentes al decidir qué se guarda ahí:

- **No está cifrado.** Cualquiera con acceso al disco y al perfil lo lee en texto plano.
- **Desaparece sin aviso.** Se va si la persona borra los datos del sitio, si usa una
  ventana privada, y puede irse si el sistema necesita espacio y desaloja orígenes poco
  usados.
- **Escribir puede fallar.** En modo privado, con la cuota llena o con el almacenamiento
  bloqueado por política, `setItem` **lanza una excepción**, y una excepción no atrapada en
  medio de un manejador de eventos se lleva puesta la pantalla.
- **Lo lee cualquier código de la página.** Incluido el que no escribió nadie de este
  equipo, si alguna vez se inyecta.

Este repo trata los cuatro hechos explícitamente. El cuarto es el que decidió dónde **no**
va la sesión: `src/services/api.ts:66-86` arranca con "ESTA APP NO GUARDA EL TOKEN. En
ningún lado", y explica que antes el token vivía en `sessionStorage` y se lo movió a una
cookie que JavaScript no puede leer, precisamente porque cualquier cosa que JavaScript
pueda leer, un script inyectado también. El tercero está atendido en cada acceso: en
`src/utils/colaRegistros.ts:49-67` · `leer()` y `escribir()`, las dos funciones envuelven
todo en `try`/`catch`, y el comentario de las líneas 24-26 dice el porqué —"una serie no
guardada no debe romper la pantalla"—.

### Qué guarda OlimpOS en el navegador, exactamente

Dos claves. Ninguna más: un `grep` de `localStorage`, `sessionStorage` e `indexedDB` sobre
`src/` da nueve coincidencias en dos archivos, más tres comentarios.

| Clave | Archivo | Qué es |
|---|---|---|
| `olimpos.reps.cola` | `src/utils/colaRegistros.ts:34` · `CLAVE` | las series contadas por la cámara que todavía no se pudieron subir |
| `olimpos.circuito` | `src/views/socio/useCircuito.ts:28` · `CLAVE_GUARDADO` | en qué ejercicio y en qué serie va un circuito a medias |

Las dos comparten una propiedad que las hace aptas para este almacén y que conviene
nombrar: **son estado del que se puede prescindir**. Si `olimpos.circuito` se pierde, el
socio retoma el circuito desde el principio; el comentario de `useCircuito.ts:25-27` aclara
que se guarda "lo mínimo que hace falta para reconstruir dónde estaba: el resto se deriva
de la rutina, que se vuelve a pedir igual". Y la restauración tiene tres condiciones
(`useCircuito.ts:93-95`): la misma rutina, el mismo día, y que no haya pasado demasiado
tiempo. Un progreso viejo no se retoma, se descarta.

Lo mismo para la cola: `colaRegistros.ts:40` declara que una serie que no se pudo subir en
dos semanas ya no tiene valor de historial, y la línea 91 la filtra antes de intentar nada.
Es un almacén que puede fallar, así que lo que se pone ahí tiene que poder perderse. Qué
hace la cola cuando la red vuelve, y por qué distingue un rechazo de una caída, es
[C-02](C-02-offline-first-cola.md).

> Un comentario de `App.tsx` dice que al arrancar se busca un token en `sessionStorage`; no
> queda ninguno, y la discrepancia está anotada en
> [los dos mecanismos de este sistema](A0-12-sesiones-y-autenticacion.md#los-dos-mecanismos-de-este-sistema-y-por-qué-son-dos).

---

## Service worker

**El problema que vino a resolver.** Una página no existe cuando la pestaña está cerrada,
y sin red no existe en absoluto: el navegador pide el documento, falla, y muestra el
dinosaurio. El primer intento de arreglarlo, *AppCache* (2008), era declarativo: un archivo
que listaba qué guardar. Fracasó de una manera que se volvió famosa —actualizaba mal,
guardaba cosas que nadie pidió, y no había forma de corregirlo desde el código— y el
reemplazo, que llegó con Chrome 40 en 2014, invirtió el modelo: en vez de una lista, **un
programa**.

> **↓ Capa 1 — qué es un service worker.** Salteable si ya lo sabés.

Es un archivo de JavaScript que corre en un contexto propio, **sin DOM y sin `window`**,
en un hilo aparte, y que **sobrevive a la página**: el navegador lo arranca cuando lo
necesita y lo apaga cuando no. Se registra para un *alcance* —un prefijo de rutas— y a
partir de ahí **el navegador le pasa todos los pedidos de ese alcance antes de tocar la
red**. El worker decide: responder él, ir a la red, o ir a la red y guardar la respuesta.

Que no tenga DOM no es una limitación arbitraria: si lo tuviera, tendría que existir una
página, y la gracia es justamente que funciona sin ella.

Dos condiciones lo gobiernan: sólo funciona en **contexto seguro** —HTTPS, o `localhost`
como excepción para desarrollo—, porque un proxy que se puede inyectar en una conexión sin
cifrar es una puerta trasera permanente; y la primera visita **nunca** pasa por él: se
instala mientras se sirve la página, y empieza a trabajar desde la siguiente.

> **↓ Capa 2 — el piso: la intercepción del pedido.** Acá termina el descenso de este
> concepto.

El worker recibe un evento por cada pedido y tiene una única palanca: **decir, de forma
síncrona dentro de ese evento, que él se hace cargo**. Si lo dice, entrega una respuesta
—fabricada, sacada de un almacén de respuestas, o traída de la red— y el pedido original
nunca sale. Si no lo dice, el navegador sigue como si el worker no existiera. No hay punto
medio ni se puede decidir más tarde: esa decisión, tomada o no tomada en ese instante, **es
la intercepción**, y es el piso de esta parte del capítulo.

### Cómo está armado acá

En todo `src/` **no hay una sola línea que registre un service worker**: el `grep` de
`serviceWorker` y `pwa-register` no devuelve nada. La registración la inyecta el
complemento al construir. En `Proyecto - PWA/src/frontend/dist/index.html`, el cierre del
`<head>` tiene dos etiquetas que no están en el `index.html` del código fuente:

```html
<link rel="manifest" href="/manifest.webmanifest"><script id="vite-plugin-pwa:register-sw" src="/registerSW.js"></script>
```

Y `dist/registerSW.js` es una línea:

```js
if('serviceWorker' in navigator) {window.addEventListener('load', () => {navigator.serviceWorker.register('/sw.js', { scope: '/' })})}
```

Tres cosas ahí, y las tres importan: se comprueba el soporte antes de usarlo, se registra
**después** del evento `load` —para no competir por ancho de banda con la carga de la
propia página— y el alcance es `/`, toda la aplicación.

El worker generado, `dist/sw.js`, termina con la línea que define su comportamiento
completo:

```js
e.precacheAndRoute([...], {}), e.cleanupOutdatedCaches(),
e.registerRoute(new e.NavigationRoute(e.createHandlerBoundToURL("index.html")))
```

- **`precacheAndRoute`** recibe la lista de lo que se guarda en la instalación. Son
  **nueve entradas**, y se pueden leer completas en el archivo: `registerSW.js`,
  `index.html`, el CSS, el JavaScript, los cuatro íconos y el manifiesto. Cada una lleva
  una firma de su contenido, salvo el CSS y el JavaScript, que traen `revision: null`
  porque su nombre ya incluye un identificador del contenido: si el archivo cambia, cambia
  el nombre.
- **`NavigationRoute`** dice que **cualquier navegación** —abrir la app, recargar, entrar
  por una URL interna— se responde con el `index.html` guardado, sin tocar la red. Es lo
  que hace que la aplicación abra sin conexión.
- **Nada más**. No hay ninguna regla para `/api/...`, así que los pedidos de datos no
  encuentran ruta que los tome, el worker no los intercepta y salen a la red normalmente.
  Eso es deliberado y es lo correcto: una respuesta guardada de un listado de socios sería
  un dato viejo presentado como actual.

### Las dos decisiones que se tomaron acá, y qué costaron

**El modelo de pose queda fuera del precaché.** `Proyecto - PWA/src/frontend/vite.config.ts:76-78`:

```ts
workbox: {
  globIgnores: ['**/mediapipe/**'],
},
```

La carpeta `public/mediapipe` pesa unos 41 MB: 5,8 MB del modelo
(`pose_landmarker_lite.task`) y unos 35 MB de tres compilaciones alternativas del motor de
inferencia, de las cuales el navegador baja **una sola** según lo que soporte el
dispositivo —en la práctica, unos 18 MB entre modelo y motor—. El comentario de las líneas
73-75 da las dos razones: sólo lo necesita quien usa el contador de repeticiones, y sin esa
exclusión la construcción **falla**, porque el complemento rechaza precachear archivos por
encima de su límite. Lo que se paga: el contador **no funciona sin conexión la primera
vez**. Se puede comprobar contando: el precaché tiene nueve entradas y `mediapipe` no
aparece ninguna vez en `dist/sw.js`.

**El worker está apagado en desarrollo.** `vite.config.ts:79-102`, el bloque `devOptions`
comentado, explica que se probó encenderlo y se volvió atrás por dos motivos. El primero es
que no sirve: sobre HTTP y por la IP de la red no hay contexto seguro, así que la opción de
instalar no aparece igual. El segundo es el que duele: **el worker guarda respuestas**, y
en desarrollo eso significa depurar un error de CSS que ya estaba arreglado, porque lo que
se está viendo es la versión anterior. El comentario deja además la salida sin renunciar a
nada —`localhost` sí es contexto seguro, y con el teléfono por USB y redirección de puertos
se abre como `localhost`— que es la diferencia entre apagar algo y apagarlo sabiendo cómo
volver a encenderlo.

El manifiesto, los cuatro íconos y la instalación como aplicación son
[C-04](C-04-pwa-instalable.md).

---

## CSS utilitario y viewport móvil

**El problema que vino a resolver, parte uno: las hojas de estilo crecen y no encogen.**
Con una clase por componente, el archivo de estilos crece con cada pantalla nueva y nunca
se achica, porque nadie sabe si `card-2` sigue usándose en algún lado. Peor: los nombres se
pudren —`card`, `card-new`, `card-final`— y terminan describiendo la historia del proyecto
en vez de lo que hacen. La respuesta utilitaria invierte la relación: **una clase, una
declaración**, con nombre derivado de la declaración (`flex`, `h-full`, `px-4`), y una
herramienta que recorre el código y emite **sólo las clases que aparecen**. El archivo pasa
a crecer con la variedad de estilos usados, no con la cantidad de componentes, y borrar una
pantalla borra su CSS automáticamente.

En este repo la paleta se declara una vez, como variables, en
`Proyecto - PWA/src/frontend/src/index.css:3-32`, dentro del bloque `@theme`:

```css
@theme {
  --color-surface-base: #15171C;
  --color-surface-card: #1C1F26;
  ...
  --color-primary-volt: #C6F135;
```

De cada variable sale una familia de clases, y por eso en las vistas se lee
`bg-surface-base` y no `bg-[#15171C]`. Las líneas 88-97 fijan el fondo del `body` con la
misma variable, para que el color exista antes de que React monte nada.

Dos utilitarios merecen mención porque parecen decoración y no lo son. Los botones de esta
app llevan `shrink-0 whitespace-nowrap` —67 archivos de `src/` usan `shrink-0`—, y sin eso,
en una pantalla angosta, un botón dentro de un contenedor flexible se comprime hasta
desaparecer o parte su texto en dos líneas: son dos declaraciones que compran el
comportamiento correcto en el teléfono, que es donde se usa la PWA.

**El problema que vino a resolver, parte dos: el teléfono.** En 2007 el iPhone tuvo que
mostrar una web entera diseñada para monitores de mil píxeles en una pantalla de 320. La
solución de Safari fue inventar **dos viewports**: uno de distribución, ancho y ficticio
(980 px), contra el que se calculan las cajas, y uno visual, el pedacito que se ve, que la
persona mueve y agranda con los dedos. Una página que sí está diseñada para el teléfono
tiene que poder decir "no me mientas el ancho", y eso es lo que declara `index.html:18`:

```html
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
```

> **↓ Capa 1 — por qué `100vh` miente.** Salteable si ya lo sabés.

En el teléfono la barra de direcciones aparece y desaparece con el scroll, así que la
altura visible **cambia mientras se usa la página**. Si `vh` siguiera ese cambio, cualquier
elemento dimensionado en `vh` se redistribuiría en medio de un scroll, con el contenido
saltando bajo el dedo. Para evitarlo, la especificación congeló `vh` en la altura del
viewport **con la barra escondida**, es decir la más grande. La consecuencia es la trampa:
`100vh` es más alto que lo que se ve, siempre que la barra esté a la vista.

Las unidades dinámicas —`dvh`— resuelven el otro lado: siguen la altura real, con el costo
de redistribución que `vh` evitaba. Sirven cuando lo que se dimensiona es **el contenedor
raíz**, que no tiene hermanos que salten.

> **↓ Capa 2 — el piso: la caja calculada en píxeles.** Acá termina el descenso de este
> concepto.

`index.css:56-69` aplica exactamente eso, y lo hace en dos tiempos:

```css
html, body, #root { height: 100%; min-height: 100%; }

@supports (height: 100dvh) {
  html, body, #root { height: 100dvh; }
}
```

Primero una base que funciona en cualquier navegador, y encima la regla condicional. El
comentario de las líneas 53-55 explica el orden: si esto corre en un navegador que no
conoce `dvh`, cae en el comportamiento anterior en vez de quedarse **sin altura**, que es
lo que pasaría si la única declaración fuera la que no entiende. Desde ahí la altura se
hereda hacia abajo, y por eso `AppLayout.tsx:33` puede usar `h-full` sin volver a nombrar
unidades: el comentario de las líneas 29-32 aclara que la altura real la fija `index.css` y
que acá simplemente se hereda.

El síntoma que esto corrigió está escrito en `index.css:43-47`: en un iPhone, el final del
contenido quedaba **debajo de la interfaz del navegador**, y al bajar rápido "no se llegaba
al límite". No era un error de scroll: era una caja calculada más alta que la pantalla.

La otra regla del bloque, `index.css:83-86`:

```css
html, body { overscroll-behavior: none; }
```

Sin ella, cuando el scroll de un panel llega al tope, el gesto **sigue de largo hacia el
documento** y Safari lo interpreta como "tirar para recargar". El comentario de las líneas
76-78 pone el costo en términos del gimnasio: recargar en medio de un circuito significa
perder el progreso. `none` corta las dos cosas —el encadenamiento y el gesto— sin tocar el
scroll de cada panel.

> **⚠ Discrepancia entre una regla del proyecto y el código.** `CLAUDE.md` fija "`100dvh` y
> nunca `h-screen`". Quedan dos usos de `min-h-screen`: `src/views/LoginView.tsx:66` y
> `src/views/CambiarPasswordView.tsx:78`. Son las dos únicas pantallas que no pasan por
> `AppLayout`. El efecto es acotado, y conviene decir por qué: `min-h-screen` es una altura
> **mínima**, no fija, así que el contenido nunca queda cortado; lo que puede quedar
> descentrado es el formulario, que se centra contra una caja un poco más alta que lo
> visible. Es exactamente lo que describe el comentario de `src/App.tsx:47-49` para la
> pantalla de arranque, donde sí se usó `min-h-full`.

---

## Qué significa exactamente "del lado del cliente"

La frase se usa como sinónimo de "en el navegador", y así no dice nada. Con todo lo
anterior en la mano se puede decir con precisión, y son **tres afirmaciones distintas**:

1. **El código está en el dispositivo de quien lo usa, así que es público y modificable.**
   Para ejecutarlo, el navegador tuvo que bajarlo entero. Cualquiera puede leerlo,
   detenerlo en medio, cambiar una variable y seguir. No hay forma de esconder nada ahí, y
   no es cuestión de esforzarse más: es la definición.
2. **Se ejecuta con los recursos de quien lo usa.** Su procesador, su GPU, su batería, su
   cámara, su almacenamiento. El servidor no se entera de que pasó, y no puede saber si
   pasó, salvo que el código se lo cuente.
3. **Su estado vive en la pestaña y muere con ella**, a menos que alguien lo escriba en el
   almacenamiento del navegador o lo mande al servidor.

Las dos decisiones más características de OlimpOS son aplicaciones directas de esas tres
afirmaciones, una de cada lado: una aprovecha el punto 2, la otra convive con el punto 1.

### Por qué el contador de repeticiones corre acá y no en el backend

**Qué se estaba optimizando.** Que una repetición se cuente **en el mismo fotograma en que
se ve**. El socio levanta, baja, y el número tiene que cambiar mientras el movimiento
termina: si llega medio segundo tarde, el contador es un adorno.

**Qué restricciones acorralaban la decisión.** El wifi del gimnasio, que es justamente lo
que no hay que dar por sentado —está escrito en `src/utils/colaRegistros.ts:5-10`—; el
backend, que atiende contra una base remota y no está dimensionado para trabajo pesado de
procesador (el capítulo que explica por qué es
[A0-10](A0-10-python-del-lado-del-servidor.md)); y el hecho de que el dato de entrada es
**video de una persona en ropa deportiva**, que es de lo más sensible que puede circular
por una red.

**La alternativa descartada, en serio.** Mandar los fotogramas al servidor y hacer la
inferencia ahí. No es absurda: centraliza el modelo, se actualiza en un solo lugar, no
exige nada del teléfono. Muere por aritmética: a 30 cuadros por segundo, cada cuadro sería
un viaje de ida y vuelta completo, y el capítulo
[A0-02](A0-02-como-se-comunican-dos-maquinas.md#tcp-y-el-viaje-de-ida-y-vuelta-rtt) ya
mostró lo que cuesta uno solo. Aunque la red fuera instantánea, el servidor tendría que
sostener treinta inferencias por segundo **por cada socio entrenando a la vez**. Y quedaría
el problema que ninguna optimización arregla: el video de los socios viajando y pasando por
una máquina que alguien administra.

**Qué se eligió y qué se pagó.** Corre en el teléfono. La evidencia de que eso es literal
está en dos lugares. En `ContadorReps.tsx:49-50`, el modelo y el motor se sirven desde la
propia aplicación y no desde un servicio externo:

```tsx
const RUTA_WASM = '/mediapipe/wasm';
const RUTA_MODELO = '/mediapipe/pose_landmarker_lite.task';
```

Y en `src/services/socioService.ts:803-813`, lo único que cruza la red al terminar una
serie son **cuatro escalares**:

```tsx
cuerpo: {
  id_ejercicio: datos.idEjercicio,
  repeticiones: datos.repeticiones,
  peso: datos.peso,
  observaciones: datos.observaciones?.trim() || null,
},
```

Ni un fotograma. El precio de esa elección está a la vista y es alto: unos 18 MB que el
teléfono baja la primera vez, y que además —por lo que vimos en la sección del service
worker— quedan fuera del precaché, así que **esa primera vez necesita conexión**; una
inferencia cuyo rendimiento depende del teléfono, con el respaldo a CPU de
`ContadorReps.tsx:169-172` para cuando la GPU no está disponible; umbrales que hay que
ajustar probando en dispositivos reales; y el resultado, que ya no está en el servidor en
el momento en que ocurre, sino cuando la cola logra subirlo.

Esa cola **es** el precio hecho código: si el cómputo se movió al cliente, el resultado
queda del lado del cliente hasta que haya red. Por eso `colaRegistros.ts` existe, y por eso
`encolarRegistro()` (líneas 137-145) escribe primero y sube después, en ese orden.

**El nombre del patrón:** mover el cómputo hasta donde está el dato, en vez de mover el
dato hasta donde está el cómputo. Cuando el dato es enorme y el resultado es chico —30
cuadros por segundo contra cuatro números—, el cálculo de qué conviene mover no tiene
vuelta. La mecánica de la inferencia y el ángulo que decide una repetición son
[A0-14](A0-14-vision-en-el-dispositivo.md#inferencia-en-el-dispositivo); lo que aporta este
capítulo es por qué ese trabajo ocurre en el navegador.

### Por qué `VITE_API_URL` termina en el bundle y nunca lleva nada privado

`VITE_API_URL` parece una [variable de entorno](A0-01-como-corre-un-programa.md#variable-de-entorno-y-archivo-env)
y no lo es, o no del modo en que lo es una del servidor. Una variable de entorno se **lee
en tiempo de ejecución**, del entorno del proceso. Esta se **sustituye en tiempo de
construcción**, en el texto del programa, antes de que exista nada que ejecutar. La
diferencia es total y se puede comprobar en el paquete ya construido.

En el código fuente, `src/services/api.ts:56` dice:

```tsx
const API_URL = import.meta.env.VITE_API_URL ?? '/api';
```

En `dist/assets/index-3ZEPFFtl.js`, el paquete que baja el navegador, la cadena
`import.meta.env` aparece **cero veces**, y lo que hay en su lugar es:

```js
var Qn=`/api`,$n=`olimpos_csrf`,...
```

No quedó una lectura, quedó **el valor**, escrito como literal. No hay ningún momento en
que el navegador consulte un entorno: el valor es parte del programa desde antes de que el
programa se sirva. Y como el paquete se sirve a cualquiera que abra la página, **todo lo
que se sustituya ahí es público**, con la misma inevitabilidad de la afirmación 1 de más
arriba.

De ahí sale la regla, escrita en
`Proyecto - PWA/src/frontend/.env.example:10-12`: "TODO lo que empiece con `VITE_` termina
en el paquete que baja el navegador. Nunca poner un secreto acá". El prefijo no es un
adorno de nombre: **es la frontera**, y la herramienta de construcción sólo sustituye lo
que lo lleva. Por eso la misma configuración usa dos variables con dos destinos distintos
(`.env.example:14-24`):

| Variable | Prefijo | Quién la ve |
|---|---|---|
| `VITE_API_URL` | sí | el navegador, escrita en el paquete |
| `API_PROXY_DESTINO` | no | sólo el servidor de desarrollo, en `vite.config.ts:11` |

`API_PROXY_DESTINO` dice a qué máquina reenviar, y **no debe llegar al navegador**: no
porque sea un secreto, sino porque decirle al cliente dónde está realmente el backend es
información que no necesita y que en producción no sería cierta.

Que el valor sea público no lo vuelve un problema, porque **lo que se guarda ahí no es
secreto por naturaleza**: `/api` es una ruta relativa, y lo único que revela es que la API
cuelga del mismo origen que la página, que es evidente mirando cualquier pedido en las
herramientas del navegador.

Los secretos de verdad viven en otro archivo, leído por otro proceso, en otra máquina:
`backend/.env`. Ahí están `JWT_SECRET_KEY`, `DATABASE_URL`, `MP_ACCESS_TOKEN` y
`MP_WEBHOOK_SECRET`, y **ninguno de esos nombres puede aparecer nunca en el paquete de la
PWA**, porque no hay forma de que un valor llegue al navegador y siga siendo secreto. Son
dos archivos `.env` distintos a propósito, y `.env.example:7-8` lo dice con todas las
letras: "son dos programas que leen cada uno su propia carpeta. El del backend tiene
secretos; este, nada privado".

El corolario que ordena todo el diseño del backend es el mismo razonamiento llevado un paso
más: si el código del cliente es público y modificable, entonces **nada de lo que llegue
desde el cliente se puede creer** —ni los datos, ni los tipos, ni el permiso—. Eso se
explica en [A0-05](A0-05-javascript-y-typescript.md#frontera-de-confianza-del-tipo).

> **⚠ Discrepancia entre un comentario y el código.** El `.env` de la PWA
> (`Proyecto - PWA/src/frontend/.env`, líneas 1-4) dice que si la variable falta, `api.ts`
> cae en `http://127.0.0.1:8000`. Ya no: `api.ts:56` cae en `/api`, y el comentario de las
> líneas 49-55 del mismo archivo cuenta que el valor por omisión se cambió justamente
> porque el anterior producía 401 silenciosos cuando faltaba el archivo. **Gana el código**:
> hoy este `.env` es opcional, y el comentario describe la situación anterior al cambio.

---

## Con qué se conecta

- **Existe por culpa de…** el service worker: sin un proxy adentro del navegador no hay
  nada que responda cuando no hay red, y de ahí cuelga la cola sin conexión
  ([C-02](C-02-offline-first-cola.md)).
- **Existe por culpa de…** el origen: CORS es la excepción reglamentada a la política del
  mismo origen, no un mecanismo aparte
  ([A0-12](A0-12-sesiones-y-autenticacion.md#cors-y-preflight)).
- **Es la misma idea que…** el canvas del navegador y el
  [canvas de Flutter](A0-13-flutter-y-flet.md#canvas-de-flutter): una superficie sin nodos
  donde se dibuja a mano, para escaparle al costo del árbol.
- **Es el mismo problema que…** este bucle de eventos y el de Python del lado del servidor:
  un solo hilo atendiendo, donde esperar la red no bloquea y calcular sí
  ([A0-10](A0-10-python-del-lado-del-servidor.md#corrutina)).
- **Se contradice con…** el almacenamiento del navegador y la
  [cookie `httponly`](A0-12-sesiones-y-autenticacion.md#cookie-y-sus-atributos): el mismo
  navegador ofrece dos lugares donde guardar la sesión, y este sistema eligió el único que
  JavaScript no puede leer.
- **Es la misma idea que…** el paquete público y la
  [frontera de confianza del tipo](A0-05-javascript-y-typescript.md#frontera-de-confianza-del-tipo):
  nada que esté del lado del cliente —ni el código, ni el dato, ni el tipo— se puede creer.
