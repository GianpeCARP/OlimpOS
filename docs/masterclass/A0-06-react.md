# A0-06 · React

> **Piso de este capítulo: el píxel en pantalla.** El descenso va componente → JSX →
> llamada a `jsx()` → objeto elemento → árbol de fibras → reconciliación → mutación
> aplicada al nodo del DOM. El último escalón —del nodo del DOM al píxel— lo baja
> [el motor de render](A0-04-el-navegador-por-dentro.md#motor-de-render-y-canvas), y acá
> se entrega ahí con el enlace en vez de volver a contarlo. Debajo del JSX no se vuelve a
> bajar hasta el bytecode: eso ya lo hizo [el motor de
> JavaScript](A0-05-javascript-y-typescript.md#motor-de-javascript).

La versión que usa este repo es React 19 (`Proyecto - PWA/src/frontend/package.json:14-15`,
`react` y `react-dom` en `^19.2.8`). Todo lo que sigue —el nombre del símbolo de los
elementos, las dos fases del ciclo, el comportamiento de `StrictMode`— es de esa versión y
se verifica en el paquete que la app genera.

---

## El problema: sincronizar estado y pantalla a mano no escala

Una aplicación web tiene, de un lado, datos que cambian —la lista de socios, el filtro
elegido, si el menú lateral está abierto— y del otro un árbol de nodos que se ve
([DOM](A0-04-el-navegador-por-dentro.md#dom)). La forma directa de unir los dos es
imperativa: cuando un dato cambia, buscás a mano cada lugar de la pantalla que lo muestra y
lo tocás.

Eso funciona hasta que hay más de un lugar. Con **D** datos y **P** lugares donde cada uno
aparece, el programa tiene que contener hasta **D × P** instrucciones de la forma "cuando
cambie esto, tocá aquello". Cada pantalla nueva no agrega nodos: agrega aristas. Y el modo
de fallar es el peor posible: no es una excepción, es **un píxel viejo**. La fila que
quedó con el estado anterior porque alguien agregó un camino de escritura y se olvidó de
uno de los seis lugares. No tira error, no queda en ningún log, y lo único que lo detecta
es una persona mirando.

El ancestro de esta app tiene el caso escrito. La barra lateral de la app de escritorio
llevaba a mano la lista de todos sus botones para saber cuál pintar como activo, y el
comentario que documenta el reemplazo lo dice en dos líneas
(`Proyecto - PWA/src/frontend/src/components/ui/Sidebar.tsx:7-9`):

> *El resaltado del ítem activo lo resuelve `<NavLink>` de react-router en vez de la lista
> manual `_todos_los_botones` que mutaba Flet a mano.*

Una lista de botones mutada a mano es exactamente una arista de esas D × P: alguien tiene
que acordarse de apagar el anterior antes de prender el nuevo, y el día que se agrega una
sección hay que acordarse de agregarla ahí también.

**El origen histórico.** El problema lo tuvo Facebook alrededor de 2011 con las pantallas
de anuncios y el feed: demasiadas piezas de interfaz mostrando el mismo dato, y una clase
de bug —la vista desactualizada— que no se podía atacar con más disciplina. Jordan Walke
escribió la primera versión inspirándose en XHP, una extensión de PHP que ya permitía
escribir marcado dentro del código del servidor y volver a generar la página entera ante
cada cambio; la idea fue llevar esa regeneración total al navegador, donde regenerar todo
es carísimo. React se liberó como código abierto en mayo de 2013 y la primera reacción
pública fue de rechazo, por mezclar marcado con lógica en el mismo archivo.

**La apuesta.** En vez de escribir la *transición* —de este estado a aquel otro, tocá
estos nodos—, escribís el **destino**: una función que, dado el estado, devuelve cómo
tendría que verse la pantalla entera. Las D × P aristas desaparecen porque ya no hay
aristas: hay una función que se vuelve a llamar. Lo que queda por resolver es el costo, y
todo el resto del capítulo es cómo React lo paga.

---

## Componente y JSX

Un **componente** es una función de JavaScript que recibe un objeto de datos y devuelve una
descripción de pantalla. No devuelve nodos del DOM y no toca nada: devuelve un valor.

El ejemplo mínimo de este repo tiene doce líneas
(`Proyecto - PWA/src/frontend/src/components/ui/FilterChip.tsx:13-26` · `FilterChip`): recibe
`label`, `activo` y `onClick`, y devuelve un `<button>` cuya clase depende de `activo`. No
hay ninguna rama que diga "si antes estaba activo y ahora no, sacale la clase". Sólo dice
cómo se ve **ahora**.

Ese `<button …>` que aparece adentro de una función de JavaScript es **JSX**: una extensión
de sintaxis que no existe en el lenguaje y que desaparece antes de que el motor vea el
archivo. No es una cadena de texto, no es HTML y no se interpreta en tiempo de ejecución.

> **↓ Capa 1 — en qué se convierte el JSX.** Salteable si ya lo sabés.

El proyecto declara la transformación en dos lugares que tienen que coincidir:
`"jsx": "react-jsx"` en `Proyecto - PWA/src/frontend/tsconfig.app.json:17`, y el plugin de
React de Vite en `Proyecto - PWA/src/frontend/vite.config.ts:2` (importación) y `:68`
(registro). Con `"noEmit": true` en la misma línea 19 del `tsconfig`, TypeScript **no
emite nada**: sólo chequea. Quien realmente convierte el archivo es el plugin, y lo hace
con el "runtime automático", que significa que el archivo no necesita importar `React` para
usar JSX —ninguno de los `.tsx` de este repo lo importa, y compilan igual—.

Cada etiqueta se convierte en una llamada a una función: `jsx(tipo, props)` cuando tiene un
solo hijo o ninguno, `jsxs(tipo, props)` cuando tiene varios, y un tercer argumento cuando
lleva `key`.

Esto no hay que creerlo: está en el paquete que se publica. El bundle vive en
`Proyecto - PWA/src/frontend/dist/assets/index-3ZEPFFtl.js`, son 633.775 bytes en un puñado
de líneas larguísimas, así que no se cita por número de línea sino por búsqueda —y el
nombre del archivo cambia de hash en cada compilación—. Buscando el fragmento de la barra
lateral:

```bash
grep -o "md:static md:translate-x-0.\{0,400\}" dist/assets/index-3ZEPFFtl.js
```

aparece, entre otras cosas, esto (reformateado; los nombres de una letra son del
minificador):

```js
(0,L.jsx)(`nav`,{
  className:`flex flex-col gap-1 px-3`,
  children: a.map(({label:e,icon:t,route:n}) =>
    (0,L.jsxs)(Pn,{ to:`/${n}`, onClick:s, className:({isActive:e})=>`…`,
                    children:[(0,L.jsx)(t,{size:18}), e] }, n))
})
```

El original está en `Sidebar.tsx:65-79`. La correspondencia es literal: `<nav className=…>`
pasó a `jsx('nav', {className: …, children: …})`, el `<NavLink>` pasó a `jsxs(Pn, {…}, n)`
—`Pn` es el componente `NavLink` después de minificar—, y **los hijos entraron como una
propiedad más llamada `children`**. No hay ninguna cadena de HTML en el resultado: hay
llamadas a funciones con objetos.

> **↓ Capa 2 — qué devuelve esa llamada.** Salteable si ya lo sabés.

La fábrica también está en el bundle, completa. Se la encuentra con:

```bash
grep -o "react.transitional.element.\{0,300\}" dist/assets/index-3ZEPFFtl.js
```

y, reformateada, dice esto:

```js
var t = Symbol.for(`react.transitional.element`),
    n = Symbol.for(`react.fragment`);
function r(e, n, r) {            // e = tipo, n = props, r = key
  var i = null;
  if (r !== void 0) i = `` + r;              // la key se pasa a texto
  if (n.key !== void 0) i = `` + n.key;
  if (`key` in n) { for (var a in r = {}, n) if (a !== `key`) r[a] = n[a]; }
  else r = n;                                 // ...y se saca de las props
  n = r.ref;
  return { $$typeof: t, type: e, key: i, ref: n === void 0 ? null : n, props: r };
}
e.Fragment = n; e.jsx = r; e.jsxs = r;
```

El piso de este concepto es esa llamada, y acá está lo que produce: **un objeto plano**.
Cinco campos, ninguna referencia al documento, nada que el navegador entienda. `$$typeof`
es un símbolo global (`Symbol.for`, la tabla compartida del motor) que sirve para
distinguir un elemento legítimo de un objeto cualquiera que alguien haya metido en los
datos. `type` es `'nav'` —una cadena, para las etiquetas del navegador— o la función del
componente. `props` es el objeto con todo lo demás, incluidos los hijos.

Crear un elemento, entonces, **no dibuja nada y no cuesta casi nada**: es construir un
objeto. Esa es la mitad de por qué la apuesta de "devolvé la pantalla entera cada vez" es
pagable. La otra mitad viene en la reconciliación.

Dos consecuencias que se ven en el repo:

- `key` sale de `props` con un bucle explícito en la fábrica. Nunca llega al componente
  como dato: es información **para React**, no para vos. Eso se desarrolla en
  [Clave (`key`) de lista](#clave-key-de-lista).
- El elemento se puede guardar en una variable, pasarlo como parámetro o devolverlo desde
  una condición sin que pase nada. `App.tsx:80` devuelve `<Rehidratando />` y `:83-171`
  devuelve el router: en las dos ramas lo que se devuelve es un objeto, y quien decide qué
  hacer con él es React.

---

## Props, estado local y re-render

**Props** son el objeto que el componente recibe: el segundo argumento de `jsx()`, ya
visto. Bajan siempre del padre al hijo y el hijo no los modifica —`FilterChip` recibe
`activo` y `onClick`, y para cambiar el filtro no toca nada: llama a `onClick`, que es una
función que le dio el padre (`SociosView.tsx:276`)—. El flujo de datos es de una sola
dirección, y eso es lo que hace que buscar "quién cambió esto" termine siempre en un solo
lugar.

**Estado local** es lo que el componente necesita recordar **entre una llamada y la
siguiente**, porque la función se va a volver a ejecutar desde cero. Se declara con
`useState`, que devuelve el valor actual y una función para pedir el próximo:

```tsx
const [busqueda, setBusqueda] = useState('');
```

(`Proyecto - PWA/src/frontend/src/views/socios/SociosView.tsx:98-99` · `SociosView`.)

**Re-render** es exactamente eso: React vuelve a llamar la función del componente. No
recrea la pantalla, no toca el DOM todavía, no destruye nada. Llama la función, recibe un
árbol de objetos elemento nuevo, y recién después decide qué hacer con él.

> **↓ Capa 1 — dónde guarda React ese estado, si la función arranca de cero cada vez.**
> Salteable si ya lo sabés.

No lo guarda en la función: lo guarda en una estructura paralela, una por componente
montado, que React llama *fiber* (fibra). Los nombres de sus campos sobreviven a la
minificación porque son propiedades de objeto; en el bundle de este repo están todos:

```bash
grep -o "memoizedState" dist/assets/index-3ZEPFFtl.js | wc -l    # 243
grep -o "stateNode"     dist/assets/index-3ZEPFFtl.js | wc -l    # 148
grep -o "alternate"     dist/assets/index-3ZEPFFtl.js | wc -l    #  87
```

`memoizedState` es el campo donde cuelga la **lista encadenada de hooks** de ese
componente: el primer `useState` es el primer nodo, el segundo es el siguiente, y así. La
correspondencia entre "este `useState`" y "este nodo" no se hace por nombre —React nunca ve
el nombre `busqueda`— sino **por orden de llamada**. De ahí sale, sin ninguna arbitrariedad,
la regla de que los hooks se llaman siempre, en el mismo orden, y nunca dentro de un `if`:
un `useState` salteado corre toda la lista un lugar y el componente empieza a leer el
estado del vecino. El repo la hace cumplir con el verificador estático:
`Proyecto - PWA/src/frontend/.oxlintrc.json:5` tiene `"react/rules-of-hooks": "error"`.

El cierre que se lleva cada hook es el mecanismo de
[A0-05](A0-05-javascript-y-typescript.md#cierre-closure): la función que devolvés en un
efecto o el manejador de un `onClick` capturan las variables **del render en que se
crearon**, no las del render actual. Un manejador viejo que quedó colgado de un nodo ve el
valor viejo, y eso es correcto: es el valor que había cuando se dibujó lo que el usuario
está tocando.

> **↓ Capa 2 — cuántas veces se vuelve a llamar la función.** Salteable si ya lo sabés.

Llamar a un `set…` no ejecuta el componente ahí mismo: encola una actualización. React
junta **todas** las que ocurran en el mismo turno del
[bucle de eventos](A0-04-el-navegador-por-dentro.md) y hace un solo re-render. Esto vale
también dentro de una promesa resuelta, que es donde más importa.

El caso está en `Proyecto - PWA/src/frontend/src/views/cobros/CobrosView.tsx:95-110`
(`CobrosView`, efecto de carga inicial): las líneas 104, 105, 106 y 107 llaman cuatro
`set…` seguidos dentro del `.then` de un `Promise.all`. Son **un** re-render, no cuatro. Sin
ese agrupado, la pantalla de Cobros pasaría por tres estados intermedios en los que tiene
socios pero todavía no tipos de membresía, y `tipoElegido` (línea 207) sería `undefined` en
dos de ellos.

React también **compara antes de trabajar**: si el valor nuevo es igual al viejo, no vuelve
a renderizar. La comparación es `Object.is`, y React trae su propia implementación de
respaldo por si el motor no la tiene. Está en el bundle:

```js
function Or(e,t){ return e===t && (e!==0 || 1/e==1/t) || e!==e && t!==t }
var kr = typeof Object.is==`function` ? Object.is : Or;
```

Es igualdad por identidad, no por contenido: dos objetos con los mismos campos son
distintos. Por eso el estado se reemplaza y no se muta —`actualizarEnLista` en
`SociosView.tsx:171-179` devuelve un arreglo nuevo con `.map`, nunca asigna sobre el
existente—; si mutara, React compararía el arreglo consigo mismo, daría igual, y no
redibujaría nada.

> **↓ Capa 3 — la trampa de las funciones de actualización, con un caso real.**
> Salteable si ya lo sabés.

A un `set…` se le puede pasar un valor o una función `(anterior) => nuevo`. La segunda
forma es obligatoria cuando el valor nuevo depende del viejo, porque entre que se encola y
se aplica puede haber otras actualizaciones en la cola. La condición es que esa función sea
**pura**: mismo argumento, mismo resultado, sin efectos.

React no puede verificar pureza, pero puede exponerla: en desarrollo, `<StrictMode>`
(`Proyecto - PWA/src/frontend/src/main.tsx:1,7-9`) **invoca dos veces** el cuerpo del
componente y las funciones de actualización. Si son puras, el segundo resultado es idéntico
al primero y no se nota nada. Si no lo son, el bug aparece en desarrollo en vez de en
producción.

Este repo tiene la cicatriz, documentada en
`SociosView.tsx:101-108`:

> *Campo y sentido van juntos en un solo estado: son una sola decisión ("ordenar por X en
> sentido Y") y separarlos obliga a que un setter llame al otro, que es impuro —
> StrictMode invoca los updaters dos veces y el toggle se cancelaba solo.*

Con dos estados separados, invertir el sentido era `setAscendente((a) => !a)`. Invocada dos
veces sobre el mismo valor, esa función devuelve el valor original: la flecha de la columna
no se movía nunca. La solución no fue apagar `StrictMode` sino modelar bien: un solo estado
`{ campo, ascendente }` y un único actualizador puro que lo calcula entero
(`SociosView.tsx:140-146` · `alternarOrden`).

> **↓ Capa 4 — cuando el re-render es demasiado caro.** Salteable si ya lo sabés.

Volver a llamar una función cuesta poco, pero no cuesta cero, y hay lugares donde se
ejecuta decenas de veces por segundo. El contador de repeticiones procesa cada fotograma de
la cámara: un `set…` por fotograma serían 30 o 60 re-renders por segundo de una vista con
video encima.

La salida es `useRef`: una caja que sobrevive a los re-renders y cuyo cambio **no dispara
ninguno**. En `Proyecto - PWA/src/frontend/src/views/socio/ContadorReps.tsx:67-72` hay seis
(`videoRef`, `canvasRef`, `landmarkerRef`, `rafRef`, `streamRef`, `drawRef`) para los
objetos del navegador y del modelo, y en `:121-129` otras ocho para el estado del conteo.
El comentario de `:133-135` dice para qué sirve la distinción:

> *"Te veo bien" mientras hay un ángulo confiable del movimiento. Se avisa sólo tras varios
> frames sin señal, para no titilar. verBienRef evita llamar a setState en cada frame.*

Y el patrón completo está en `:139-143` (`marcarVer`): la referencia guarda el valor de cada
fotograma; el `setState` se llama **sólo cuando el valor cambia de verdad**. La regla que
sale de ahí: si un dato tiene que verse, va en estado; si sólo tiene que recordarse, va en
una referencia.

---

## Árbol virtual y reconciliación

De un re-render sale un árbol de objetos elemento —el **árbol virtual**— que describe cómo
tendría que verse la pantalla. React ya tiene el árbol de la vez anterior. **Reconciliación**
es el algoritmo que compara los dos y produce la lista mínima de mutaciones a aplicar sobre
el DOM real.

Comparar dos árboles cualesquiera para encontrar la diferencia mínima es un problema de
orden cúbico en la cantidad de nodos: inviable en cada tecla que alguien aprieta. React no
lo resuelve: lo evita, con dos suposiciones que no son universalmente ciertas pero sí lo son
casi siempre en una interfaz.

1. **Dos elementos de tipo distinto en la misma posición producen árboles distintos.** No se
   intenta emparejar nada: se destruye el subárbol viejo —con su DOM y con todo el estado de
   sus componentes— y se construye el nuevo desde cero.
2. **Los hijos de una lista se emparejan por posición**, salvo que el programador dé otra
   identidad con `key`.

Con esas dos, el recorrido es lineal.

La primera regla se ve entera en `Proyecto - PWA/src/frontend/src/App.tsx:80-83`. Mientras
la sesión se rehidrata, `App` devuelve `<Rehidratando />` (línea 80); cuando termina,
devuelve `<BrowserRouter>` (línea 83). Misma posición, tipo distinto: React **no** intenta
convertir uno en otro. Desmonta el `<div>` de la pantalla de carga y monta el router
completo. Eso es exactamente lo que se buscaba, y el motivo está escrito arriba, en
`:57-61`: si el router se montara antes de que el backend conteste quién es el dueño de la
cookie, la ruta protegida vería la sesión en falso y redirigiría al login —o sea, cada F5
cerraría la sesión—.

> **↓ Capa 1 — con qué compara React, si el árbol virtual es un objeto nuevo cada vez.**
> Salteable si ya lo sabés.

No compara el árbol de elementos nuevo contra el de elementos viejo. Compara el nuevo contra
el **árbol de fibras**, que es persistente y vive entre render y render. Cada fibra guarda,
además de `memoizedState`:

- `stateNode`: el nodo real del DOM al que corresponde esa fibra.
- `child`, `sibling`, `return`: el árbol representado como lista encadenada —primer hijo,
  hermano siguiente, padre—, para poder recorrerlo con un bucle y poder **frenar en el
  medio** y retomar, cosa que con recursión no se puede.
- `alternate`: el puntero a la otra copia. React mantiene dos árboles, el que está en
  pantalla y el que está construyendo, y al terminar los intercambia. Nunca hay un árbol a
  medio actualizar visible.
- `flags`: el conjunto de marcas que dice qué mutación necesita esa fibra —insertar, borrar,
  actualizar, ejecutar un efecto—.

Los cinco están en el bundle de este repo (`grep -o "\.sibling"` da 99 apariciones,
`"\.return\b"` da 173, `"\.flags"` da 181), y el recorrido por hermanos se puede leer tal
cual, minificado:

```js
for (e = e.child; e !== null;) { if (t = p(e), t !== null) return t; e = e.sibling }
```

> **↓ Capa 2 — las dos fases, y el momento exacto en que se toca el DOM.**
> Salteable si ya lo sabés.

El trabajo se parte en dos fases con propiedades opuestas, y esa partición es la razón de
ser de toda la estructura anterior.

**Fase de render.** React llama las funciones de los componentes y arma el árbol de fibras
nuevo, marcando `flags`. No toca el DOM. Como no toca nada observable, se puede pausar,
retomar o **tirar a la basura** si llega una actualización más urgente. Es también la razón
por la que el cuerpo de un componente tiene que ser puro: puede ejecutarse más de una vez
por cada vez que se muestra, y `StrictMode` lo fuerza en desarrollo.

**Fase de commit.** Un solo bloque sincrónico, no interrumpible: React recorre las fibras
marcadas y aplica las mutaciones al DOM real —`appendChild`, `removeChild`, cambiar un
atributo, cambiar el texto de un nodo—. Después intercambia los árboles por `alternate`.

Acá está el piso de este concepto: **la mutación aplicada al nodo del DOM**. Y acá también
está el aporte propio de React al último escalón: como todas las mutaciones de una
actualización se aplican en un único bloque sincrónico, el navegador nunca llega a pintar
un fotograma intermedio con media lista vieja y media nueva. Lo que pasa de ahí en adelante
—invalidar estilos, recalcular la distribución, pintar— es del navegador y está explicado
en [motor de render](A0-04-el-navegador-por-dentro.md#motor-de-render-y-canvas). Ese es el
píxel, y es donde este capítulo entrega.

**El costo de esta arquitectura, dicho sin rodeos:** React redibuja de más. Cambiar una
letra en el buscador de socios vuelve a llamar `SociosView` entera y a construir cientos de
objetos elemento que, comparados, resultan iguales. Lo que compra a cambio es que el
programa no contenga ni una sola instrucción de sincronización, y que agregar una columna a
la tabla no obligue a revisar ningún camino de actualización. En una pantalla de gestión
contra una base remota, donde una consulta cuesta órdenes de magnitud más que un re-render,
el canje es trivialmente favorable; en el bucle de la cámara no lo es, y por eso ahí se usan
referencias.

---

## Clave (`key`) de lista

La segunda suposición de la reconciliación —los hijos se emparejan por posición— es la que
falla cuando la lista cambia de orden, se le saca un elemento del medio o se le inserta uno
adelante. Emparejando por posición, sacar el primero de cuatro hace que React crea que
cambiaron los cuatro.

La `key` es la identidad explícita que se le da a cada hijo para que el emparejamiento sea
por identidad y no por lugar. No es un dato del componente: ya se vio en la fábrica que
viaja como **tercer argumento** de `jsx()` y que el bucle de la fábrica la excluye
expresamente del objeto `props`. Y se convierte a texto (`i = '' + r`), así que
`key={socio.idSocio}` con un número guarda la cadena `"42"`.

En el repo hay tres formas y las tres están bien elegidas:

| Origen de la clave | Dónde | Por qué ahí |
|---|---|---|
| El identificador de la base | `SociosView.tsx:329-331` (`key={socio.idSocio}`) | La fila **es** ese socio; el id no cambia nunca. |
| Un valor propio y único | `Sidebar.tsx:66-68` (`key={route}`) | Cada ítem del menú es su ruta, y dos ítems no comparten ruta. |
| Un contador propio | `EditorEjercicios.tsx:122-123` (`key={it.clave}`) | Los ejercicios de una rutina **todavía no existen en la base**: no hay id que usar. |

El tercero es el interesante, y su mecánica está en
`Proyecto - PWA/src/frontend/src/views/rutinas/planillaEjercicios.ts:33-35,50`
(`nuevoItem`): un contador de módulo que arranca en 1 y se incrementa por ítem creado.
El comentario explica por qué no se usó el generador de identificadores del navegador:

> *Clave estable para React. No `crypto.randomUUID()`: sólo existe en contexto seguro, y la
> PWA se abre por la IP de la red en HTTP.*

Un contador de módulo basta porque la clave no tiene que ser única en el universo: tiene que
ser única **entre hermanos** y estable **mientras el componente esté montado**.

Y la razón concreta por la que ahí no alcanzaba con el índice está a tres pantallas de
distancia, en `EditorEjercicios.tsx:69-79` (`mover`): subir o bajar un ejercicio dentro de
su día **intercambia dos posiciones del arreglo** (línea 77). Con `key={idx}`, la
reconciliación empareja posición con posición: React conservaría los dos nodos `<div>` y
sus `<input>` donde están y les cambiaría el contenido. Los valores visibles seguirían bien
—son campos controlados, su `value` sale de las props: `CampoMini` en `:219-245`—, pero todo
lo que vive en el nodo del DOM y no en React se quedaría pegado a la posición en vez de
seguir al ejercicio: el foco, la posición del cursor dentro del campo, la selección de
texto. Con `key={it.clave}`, React reconoce los dos ítems, **mueve** los nodos existentes y
no toca nada adentro.

La misma regla, del otro lado: cuando la lista sólo se dibuja y nunca se reordena ni se
filtra, el índice es una clave legítima. Los nueve `key={i}` del repo son todos de esqueletos
de carga —por ejemplo `SociosView` no, pero sí `ActividadesAdminView.tsx:218`,
`DashboardView.tsx:320`, `PersonalView.tsx:181`—: rectángulos grises idénticos, sin estado,
que aparecen y desaparecen todos juntos.

---

## Efecto y arreglo de dependencias

El cuerpo de un componente tiene que ser puro, y ya se vio por qué: la fase de render puede
ejecutarlo dos veces, o descartarlo. Pero una pantalla real necesita hacer cosas que no son
puras —pedirle datos al backend, suscribirse a algo, prender una cámara, arrancar un
temporizador—. Ese trabajo no puede vivir en el cuerpo.

`useEffect` es el lugar donde va: una función que React guarda durante el render y ejecuta
**después**, ya en el mundo real, cuando el árbol ya está en pantalla. Recibe dos cosas: la
función y el **arreglo de dependencias**, que es la lista de valores de los que ese trabajo
depende.

> **↓ Capa 1 — en qué momento exacto corre, y cómo se decide si vuelve a correr.**
> Salteable si ya lo sabés.

El momento es el piso de este concepto: React agenda los efectos **después de la fase de
commit y después de que el navegador pinta**. No bloquean el fotograma. Por eso una pantalla
que carga datos en un efecto se dibuja primero vacía (o con su esqueleto) y se completa
después: el orden no es un descuido, es la definición.

Si el efecto devuelve una función, esa función es la **limpieza**, y React la ejecuta antes
de volver a correr el efecto y al desmontar el componente.

La decisión de volver a correr se toma comparando el arreglo de dependencias de este render
con el del anterior, **elemento por elemento**, con la misma igualdad por identidad que ya
se usó para el estado. Un arreglo vacío `[]` nunca cambia, así que el efecto corre una sola
vez al montar (`App.tsx:65-67` y `:73-78`, `CobrosView.tsx:95-110`). Sin arreglo, corre
después de cada render.

Igualdad por identidad tiene una consecuencia inmediata: si una dependencia es una función
declarada en el cuerpo del componente, cada render crea una función nueva, el arreglo cambia
siempre y el efecto corre siempre. Para eso existe `useCallback`, que devuelve **la misma
referencia** mientras sus propias dependencias no cambien. En `CobrosView.tsx:123-142`,
`seleccionarSocio` es un `useCallback` precisamente porque en `:172` es dependencia de un
efecto.

> **↓ Capa 2 — por qué casi todos los efectos de este repo declaran una variable
> `cancelado`.** Salteable si ya lo sabés.

Un efecto que pide datos arranca algo que tarda. Mientras tanto el componente puede
re-renderizarse con otro parámetro, o desmontarse. Cuando la respuesta vieja llega, su
`.then` sigue vivo —es un cierre, nadie lo canceló— y llama a un `set…` con datos que ya no
corresponden. Con dos pedidos en vuelo, gana el que vuelve último, que no es
necesariamente el último que se pidió.

La forma canónica está en `SociosView.tsx:120-134`:

```tsx
useEffect(() => {
  let cancelado = false;
  setSocios(null);
  setError(null);
  listarSocios()
    .then((lista) => { if (!cancelado) setSocios(lista); })
    .catch((err: unknown) => { if (!cancelado) setError(mensajeDeError(err)); });
  return () => { cancelado = true; };
}, [intento]);
```

La limpieza no cancela el pedido: marca la bandera. El `.then` que llegue tarde entra, mira
`cancelado` —la variable **de su render**, por el cierre— y no escribe nada. La misma
estructura se repite en `CobrosView.tsx:184-198` (promociones) y `:214-230` (vista previa
del descuento).

Ese `[intento]` de la línea 134 es el otro idiom que conviene reconocer: `intento` es un
contador (`:97`) y `recargar` (`:136`) sólo le suma uno. No representa nada del dominio;
existe para que cambiar una dependencia vuelva a disparar el efecto. Es "recargar" expresado
en el único vocabulario que el modelo tiene: cambiar un valor.

Y hay un motivo más, específico de desarrollo, para que la limpieza esté siempre: bajo
`<StrictMode>` React monta cada componente, ejecuta la limpieza y lo vuelve a montar. Un
efecto sin limpieza deja dos suscripciones, dos temporizadores o dos cámaras encendidas, y
el bug se descubre en producción cuando ya no hay quien lo duplique.

---

## Store global fuera de React

Las props bajan de padre a hijo. Cuando un dato lo necesitan dos ramas lejanas del árbol, la
única salida dentro del modelo es subirlo al ancestro común y volver a bajarlo atravesando
todos los componentes del medio, que no lo usan y sólo lo reenvían.

El repo tiene el caso escrito y cuantificado en
`Proyecto - PWA/src/frontend/src/store/uiStore.ts:36-46`, sobre si el menú lateral está
abierto:

> *Vive en el store y no en AppLayout porque quien lo abre es el botón del Topbar, y el
> Topbar lo arma cada vista por su cuenta (así lo pide layout.md). Pasarlo por props
> obligaría a que las ~15 vistas lo reenvíen, y alcanzaría con que una se olvide para que
> ahí no se pueda abrir el menú.*

Quince reenvíos que no hacen nada, y un modo de fallar silencioso en cada uno. Un **store
global** resuelve eso sacando el dato del árbol: vive en un módulo, cualquier componente lo
lee directo, y los que están en el medio ni se enteran. Este repo tiene dos —`uiStore.ts`
(menú, avisos, diálogo de confirmación) y `authStore.ts` (sesión, persona, roles)—, los dos
armados con zustand (`package.json:19`).

> **↓ Capa 1 — qué es un store, sin la biblioteca.** Salteable si ya lo sabés.

Tres cosas: un valor, un conjunto de suscriptores y una función para cambiarlo que avisa. El
bundle lo muestra entero, porque zustand es chico y sobrevive legible a la minificación:

```bash
grep -o "let t,n=new Set.\{0,220\}" dist/assets/index-3ZEPFFtl.js
```

```js
let t,                                  // el estado
    n = new Set,                        // los suscriptores
    r = (e, r) => {                     // el set(...)
      let i = typeof e == `function` ? e(t) : e;
      if (!Object.is(i, t)) {           // nada cambió -> no se avisa
        let e = t;
        t = (r ?? (typeof i != `object` || !i)) ? i : Object.assign({}, t, i);
        n.forEach(n => n(t, e));        // avisar a todos
      }
    }
```

Un `Set` de funciones, una comparación por identidad y un `Object.assign` que **mezcla
superficialmente** el objeto parcial sobre el estado anterior. Eso explica por qué
`abrirMenu` puede escribirse `set({ menuAbierto: true })` sin tocar el resto
(`uiStore.ts:60`) y por qué `closeSnack` tiene que escribir
`set((s) => ({ snackbar: { ...s.snackbar, open: false } }))` (`:75-77`): la mezcla es de un
solo nivel, así que el objeto anidado hay que reconstruirlo a mano.

> **↓ Capa 2 — cómo se entera React.** Salteable si ya lo sabés.

Acá está el piso del concepto: **la suscripción que dispara el re-render**. Cada componente
que llama `useUiStore(selector)` agrega una función a ese `Set`. Cuando el estado cambia,
se le avisa; el enganche corre el selector sobre el estado nuevo, lo compara por identidad
con el resultado anterior y, **sólo si cambió**, pide un re-render de ese componente.

El selector no es cosmético: es la granularidad. En `Sidebar.tsx:34-35`, la barra lateral se
suscribe a `menuAbierto` y a `cerrarMenu`; en `CobrosView.tsx:71`, Cobros se suscribe a
`showSnack`. Cuando alguien abre el menú, `Sidebar` se vuelve a renderizar y `CobrosView`
no, porque su selector devuelve la misma función de siempre —`showSnack` se define una vez
dentro del objeto de `create` (`uiStore.ts:65`) y su identidad no cambia jamás—.

La parte de "fuera de React" del nombre se ve cuando no hay componente. En
`App.tsx:73-78`, la capa de red avisa por un callback que la sesión se cayó, y el manejador
escribe en los dos stores con `useAuthStore.getState()` y `useUiStore.getState()`. Ahí no
hay hook, no hay árbol y no hay render: se muta el valor del módulo, el `Set` se recorre, y
los componentes suscritos reaccionan. Un store que viviera adentro de React no se podría
tocar desde ahí.

> **↓ Capa 3 — el envoltorio que evita repetir la suscripción.** Salteable si ya lo sabés.

Un hook no tiene que ser de React: cualquier función cuyo nombre empiece con `use` y que
llame hooks adentro lo es, y sirve para nombrar una combinación que se repite.
`Proyecto - PWA/src/frontend/src/hooks/usePermisos.ts:21-24` (`usePuedeAccion`) es el
ejemplo mínimo: lee `roles` del store de sesión y se lo pasa a una función pura de
`config.ts`. Tres líneas, y el motivo está en `:1-4`: que las vistas no repitan
`useAuthStore((s) => s.roles)` cada una por su cuenta.

---

## Enrutado del lado del cliente

Un `<a href="/socios">` común hace que el navegador tire abajo todo: el documento, el
montón de JavaScript, los stores, las listas ya traídas, la posición del scroll. Y después
pide un documento nuevo y vuelve a arrancar. Para una aplicación cuyos datos vienen de una
base remota, eso convierte cada cambio de sección en una recarga completa más todas las
consultas de nuevo.

El **enrutado del lado del cliente** es cambiar de pantalla sin pedir documento: se reescribe
la URL con la interfaz de historial del navegador —que cambia la barra de direcciones y
apila una entrada sin emitir ningún pedido—, y un componente que escucha esos cambios cruza
la ruta nueva contra una tabla y devuelve el árbol que corresponde. Ese es el piso del
concepto: **la URL cambiada sin pedir una página nueva**.

La tabla de este sistema está entera en `Proyecto - PWA/src/frontend/src/App.tsx:86-170`, con
`react-router` (`package.json:18`). Tres cosas para leerla:

- **Las rutas anidan y heredan.** `:100` abre un `<Route element={<ProtectedRoute />}>` sin
  `path`: no representa una URL, envuelve a todas las de adentro. Lo mismo `:101` con
  `<AppLayout />`. La pieza que lo hace posible es `<Outlet />`
  (`ProtectedRoute.tsx:36`): el agujero donde el enrutador inserta la ruta hija que
  coincidió. Gracias a eso un chequeo que si no habría que repetir en dieciocho vistas es un
  componente escrito una vez.
- **La URL es estado.** `CobrosView.tsx:161-162` lee `?socio=<id>` con `useSearchParams`, que
  es un hook como `useState` sólo que el valor vive en la barra de direcciones. Lo escribe
  el alta de socio con "Cobrar ahora". Y en `:171` lo borra con
  `setParametros({}, { replace: true })`: `replace` pisa la entrada del historial en vez de
  apilar otra, para que el botón "atrás" no devuelva al usuario a la URL con el parámetro y
  reabra el mismo socio.
- **La ruta que no coincide con ninguna.** `:169`, `path="*"`, manda a `RedirectInicial` en
  vez de dejar la pantalla en blanco.

`<NavLink>` (`Sidebar.tsx:67-69`) dibuja un `<a>` de verdad —se puede copiar el enlace,
abrirlo en otra pestaña, y un lector de pantalla lo anuncia como enlace— y le intercepta el
click para hacer la navegación sin recarga. Además le pasa a su `className` si está activo
(`:75-82`), que es la lista de botones mutada a mano de la barra lateral de Flet, resuelta
por el enrutador.

Una aclaración que hay que dejar hecha acá y no repetir: `ProtectedRoute` decide **qué se
dibuja**, no qué se permite. El archivo lo dice en `:13-14` y el hook de permisos en
`:6-8`. Quién puede entrar realmente a cada cosa se resuelve del lado del servidor, y ese es
el tema del capítulo de autorización.

---

## El retorno: el efecto que compila y revienta

Con todo lo anterior, la trampa que `CLAUDE.md` anota en una línea —*"un `useEffect` que en
sus deps lee un `const` declarado más abajo compila y revienta por TDZ"*— se vuelve una
consecuencia obligada en vez de una curiosidad.

Los tres hechos que la producen ya están dichos:

1. `useEffect(fn, deps)` es **una llamada a función común**. JavaScript evalúa los argumentos
   antes de entrar, así que el arreglo literal `[idPromocionElegida, tipoElegido]` se
   construye —y por lo tanto **se leen sus variables**— en el momento de la llamada.
2. Esa llamada está en el cuerpo del componente, que se ejecuta **de arriba hacia abajo, en
   cada render**. No hay nada diferido: la línea 214 corre antes que la 215.
3. Una `const` no existe hasta que su línea se ejecuta. Leerla antes es la
   [zona muerta temporal](A0-05-javascript-y-typescript.md#zona-muerta-temporal-tdz), y el
   resultado es un `ReferenceError` en tiempo de ejecución.

Poner un efecto arriba de la `const` que usa como dependencia, entonces, no es un descuido
de estilo: es leer una variable antes de que exista, en la primera línea que se ejecuta de
la pantalla. La aplicación no dibuja nada —el error se lanza durante el render, antes del
commit— y se ve la pantalla en blanco.

El repo tiene los dos casos, los dos con el efecto deliberadamente **fuera** del bloque de
efectos y con el motivo escrito arriba.

**Caso 1 — `CobrosView.tsx:154-172`.** El efecto que abre Cobros con un socio ya
seleccionado depende de `seleccionarSocio`, que es el `useCallback` de `:123-142`. El
comentario de `:154-156`:

> *Va DESPUÉS de seleccionarSocio a propósito: el array de dependencias se evalúa durante el
> render, y leer una const declarada más abajo revienta con un ReferenceError que tsc no ve
> (ver CLAUDE.md, trampa de TDZ).*

**Caso 2 — `CobrosView.tsx:207-230`.** El efecto que pide la vista previa del descuento
depende de `tipoElegido`, la `const` de `:207`. El comentario de `:209-213`:

> *Va DESPUES de `tipoElegido` y no junto al resto de los efectos: el array de dependencias
> se evalua durante el render, asi que ponerlo arriba lo leeria antes de su `const` y
> tiraria un ReferenceError por TDZ. No lo detecta tsc — la referencia es valida para el
> compilador, el problema es el orden en tiempo de ejecucion.*

Los dos comentarios existen porque el arreglo de posiciones es invisible: un archivo con
todos los efectos agrupados arriba y todos los valores derivados abajo se ve más prolijo, y
esa prolijidad es exactamente lo que rompe. La única defensa es la nota al lado.

**Por qué las herramientas de este proyecto no lo atajan.** Acá hay que separar dos cosas
que se confunden:

- `npm run dev` **no chequea tipos en absoluto**. En
  `Proyecto - PWA/src/frontend/package.json:7-8`, `"dev"` es `vite` a secas y `"build"` es
  `tsc -b && vite build`. El servidor de desarrollo transpila borrando los tipos
  ([borrado de tipos](A0-05-javascript-y-typescript.md#tipado-estático-y-borrado-de-tipos),
  garantizado además por `"erasableSyntaxOnly": true` en `tsconfig.app.json:22`) y no corre
  el chequeador. Mientras se desarrolla, entonces, **nada mira ese archivo antes de
  ejecutarlo**: el error aparece como pantalla en blanco, sin una sola línea de compilador.
- El verificador estático que sí está configurado tampoco lo cubre:
  `.oxlintrc.json:4-7` habilita `react/rules-of-hooks` —que vigila el **orden de llamada** de
  los hooks, no el contenido de sus dependencias— y `react/only-export-components`. La regla
  que revisa arreglos de dependencias no está en esa lista.

> **⚠ Discrepancia anotada, no corregida.** El comentario de `CobrosView.tsx:211-213` dice
> "No lo detecta tsc". Bajo la restricción de sólo lectura de esta masterclass no se pudo
> correr `npx tsc --noEmit -p tsconfig.app.json` sobre una versión con el efecto movido para
> comprobarlo, y TypeScript **sí** tiene un diagnóstico para el caso directo (`TS2448`,
> "Block-scoped variable used before its declaration") que podría alcanzar a un arreglo de
> dependencias escrito en el mismo bloque. Lo que queda verificado y es lo que importa en la
> práctica: **el ciclo de desarrollo no lo detecta**, porque `npm run dev` no invoca a `tsc`,
> y el verificador que sí corre no mira las dependencias. Queda como cosa a comprobar cuando
> se pueda ejecutar el chequeador.

Y el cierre del retorno, que es lo que hay que llevarse: el arreglo de dependencias parece
declarativo —una lista de nombres— y no lo es. Es código que corre, en una posición precisa,
dentro de una función que se ejecuta entera de arriba abajo en cada render. Todo el capítulo
apunta a eso: React no es magia declarativa encima del lenguaje, es una función de
JavaScript que se llama muchas veces, y las reglas del lenguaje siguen valiendo adentro.

---

## Por qué está hecho así

**Qué se estaba optimizando.** Costo de mantenimiento, no velocidad. La decisión de escribir
la pantalla como una función del estado se paga en trabajo de máquina —árboles de objetos
que se construyen y se descartan— y se cobra en trabajo humano: ningún camino de
sincronización que revisar, ninguna pantalla que se pueda quedar vieja porque alguien se
olvidó de una arista.

**Qué restricciones acorralaban.** El DOM es la estructura cara: tocarlo invalida estilos y
distribución y arrastra al motor de render. Comparar dos árboles arbitrarios es cúbico.
Y el motor de JavaScript tiene un solo hilo, así que cualquier trabajo largo se come el
fotograma.

**Qué alternativas había.** La imperativa —mutar el DOM a mano, que es lo que hacía la barra
lateral de Flet con su lista de botones— escala mal pero no necesita ninguna maquinaria: no
hay árbol virtual, no hay reconciliación, no hay trampas de orden. La otra alternativa
seria es el enlace bidireccional, donde el marco observa cada propiedad y sabe con
precisión qué cambió: ahorra la comparación entera, al precio de que los datos dejen de
tener una sola dirección y de que "quién cambió esto" vuelva a no tener respuesta única.

**Qué se eligió y qué se pagó.** React eligió la comparación, con dos suposiciones que la
vuelven lineal, y el precio es que el programador tiene que suministrar a mano lo que el
marco no puede deducir: la identidad de los elementos de una lista (`key`) y la lista de
valores de los que depende un efecto (el arreglo de dependencias). Las dos cosas son
declaraciones manuales que nada verifica, y cada una tiene su modo de fallar —una lista que
pierde el foco al reordenarse, un efecto que corre de más o de menos, y el orden de
declaración que revienta por la zona muerta temporal—.

**El nombre del patrón.** Renderizado declarativo con flujo de datos en una sola dirección,
apoyado en una **representación intermedia barata** —construir objetos y compararlos sale
mucho más barato que tocar la estructura real, así que conviene tener dos copias—. Es la
misma jugada que aparece en cualquier sistema que pone una capa liviana delante de una
pesada, y reconocerla acá es reconocerla después.

---

## Con qué se conecta

- **Es el mismo problema que…** la zona muerta temporal: el orden de declaración importa en
  tiempo de ejecución aunque nada lo marque antes de correr
  ([A0-05](A0-05-javascript-y-typescript.md#zona-muerta-temporal-tdz)).
- **Es la misma idea que…** el cierre: un efecto y un `useState` recuerdan porque se llevan
  el entorno del render en que se crearon
  ([A0-05](A0-05-javascript-y-typescript.md#cierre-closure)).
- **Existe por culpa de…** el DOM: el árbol virtual es una copia barata que sólo tiene
  sentido porque tocar el árbol caro cuesta
  ([A0-04](A0-04-el-navegador-por-dentro.md#dom)).
- **Es la misma idea que…** el motor de render: React agrupa sus mutaciones en un commit
  sincrónico por la misma razón por la que el navegador agrupa el dibujo en un fotograma
  ([A0-04](A0-04-el-navegador-por-dentro.md#motor-de-render-y-canvas)).
- **Existe por culpa de…** el servidor de desarrollo: `npm run dev` transpila sin chequear
  tipos, y por eso un error de orden aparece corriendo y no compilando
  ([A0-05](A0-05-javascript-y-typescript.md#empaquetador-y-servidor-de-desarrollo)).
- **Se contradice con…** el enrutado del lado del cliente parece una barrera de acceso y no
  lo es: quién entra realmente a cada ruta lo decide el servidor
  ([A-08](A-08-autorizacion.md#el-frontend-esconde-el-backend-rechaza)).
