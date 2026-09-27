# A0-05 · JavaScript y TypeScript

> **Piso de este capítulo: qué NO existe en tiempo de ejecución.** El descenso baja desde
> el texto que escribe el programador hasta las instrucciones que ejecuta el procesador, y
> se detiene en el punto exacto donde se puede afirmar, con el archivo compilado en la
> mano, que de todo el sistema de tipos no quedó ni un byte. Ese punto es el que explica
> por qué este sistema valida en el servidor y no en la pantalla.

Este capítulo se apoya en [A0-01](A0-01-como-corre-un-programa.md) (proceso, bytecode,
instrucción de máquina, variable de entorno), [A0-02](A0-02-como-se-comunican-dos-maquinas.md)
(el viaje de ida y vuelta), [A0-03](A0-03-http.md) (el cuerpo JSON, el código de estado) y
[A0-04](A0-04-el-navegador-por-dentro.md) (el DOM, el bucle de eventos, `fetch`). No usa
nada de lo que viene después.

---

## Motor de JavaScript

**El problema de origen.** En 1995 Netscape necesitaba que una página pudiera reaccionar a
un click sin volver a pedirle el documento al servidor: validar un formulario antes de
mandarlo, mostrar un mensaje, cambiar una imagen. Brendan Eich escribió el lenguaje en
diez días para la versión 2.0 del navegador. Las restricciones de ese encargo explican casi
todo lo que vino después: tenía que ser interpretable sin un paso de compilación (la página
llega como texto y hay que ejecutarla ya), tenía que perdonar errores en vez de negarse a
correr (el autor de la página no es un programador profesional, y una página rota es peor
que una página con una función que no anda) y no podía tener tipos declarados, porque eso
habría exigido un compilador que en ese contexto nadie iba a correr.

Durante diez años eso alcanzó, porque los programas eran de veinte líneas. Dejó de alcanzar
cuando las páginas pasaron a ser aplicaciones: en 2008 Google publicó V8 con Chrome, Apple
publicó SquirrelFish y Mozilla TraceMonkey, todos en el mismo año y todos resolviendo el
mismo problema — un lenguaje diseñado para ser interpretado ahora tenía que correr bucles
de miles de iteraciones. La respuesta no fue cambiar el lenguaje: fue meter un compilador
adentro del intérprete.

> **↓ Capa 1 — de texto a árbol.** Salteable si ya lo sabés.

El motor recibe una cadena de caracteres. El *analizador léxico* la corta en unidades
mínimas (`const`, `bucle`, `=`, `(`, `)`, `=>`, `{`), y el *analizador sintáctico* arma con
ellas un árbol que representa la estructura del programa: una declaración cuyo hijo derecho
es una función, cuyo cuerpo es una lista de sentencias, y así. Ese árbol es lo mismo que
[A0-01](A0-01-como-corre-un-programa.md#intérprete-bytecode-y-compilación-al-vuelo) describe
como paso previo a la traducción.

Hay un detalle que importa para una aplicación como esta: los motores no parsean todo
completo la primera vez. Hacen un *pre-parseo* que sólo verifica que la sintaxis cierre y
anota dónde empieza y dónde termina cada función, y recién parsean el cuerpo de verdad
cuando la función se llama por primera vez. El motivo es el tamaño: el paquete que baja la
PWA de este repo tiene 633.775 bytes de JavaScript
(`Proyecto - PWA/src/frontend/dist/assets/index-3ZEPFFtl.js`), y la enorme mayoría de esas
funciones no se ejecutan nunca en una sesión dada — quien entra a Cobros no toca el contador
de repeticiones.

> **↓ Capa 2 — de árbol a bytecode.**

El árbol no se ejecuta: se traduce a *bytecode*, una secuencia de instrucciones de una
máquina virtual que no existe en ningún silicio. En V8 el componente que lo genera y lo
ejecuta se llama Ignition, y sus instrucciones operan sobre registros propios del motor
(`LdaNamedProperty`, `Add`, `JumpIfFalse`), no sobre los registros del procesador. Es el
mismo mecanismo de dos etapas del concepto de
[intérprete y bytecode](A0-01-como-corre-un-programa.md#intérprete-bytecode-y-compilación-al-vuelo),
aplicado acá a un lenguaje que llega por la red.

Mientras ejecuta, el intérprete **anota**. Por cada operación que depende del tipo de sus
operandos —una suma, un acceso a propiedad— guarda en una estructura al costado qué se
encontró realmente: "en este `+` los dos lados fueron siempre números de punto flotante",
"en este `a.x` el objeto tuvo siempre la misma forma". Esa forma —qué propiedades tiene un
objeto y en qué orden— es lo que V8 llama *hidden class*, y es lo que permite que
`punto.x` se resuelva como "leé el desplazamiento 8 desde el principio del objeto" en vez
de como "buscá la clave `x` en una tabla".

> **↓ Capa 3 — de bytecode a instrucciones de máquina.**

Cuando una función se ejecuta lo suficiente, el motor la considera caliente y la manda a un
compilador optimizador. V8 tiene hoy tres escalones por encima del intérprete (Sparkplug,
Maglev y TurboFan, de más rápido de compilar a más agresivo de optimizar). El compilador usa
las anotaciones del intérprete como **suposiciones**: si el `+` siempre vio dos flotantes,
emite la instrucción de suma de punto flotante directa, sin ninguna comprobación de tipo; si
el objeto siempre tuvo la misma forma, emite un acceso por desplazamiento fijo. El resultado
ya es lo que [A0-01](A0-01-como-corre-un-programa.md#instrucción-de-máquina-y-compuerta-lógica)
llama instrucción de máquina: la operación que el procesador sabe hacer, ejecutada por sus
compuertas, sin ninguna capa intermedia. **Ese es el piso de esta parte del descenso y acá
se corta**, porque bajar un escalón más no explica nada de OlimpOS.

La suposición se protege con una guarda: antes del código optimizado hay una comprobación
barata de que la forma sigue siendo la esperada. Si falla —alguien llamó la misma función con
una cadena— el motor *desoptimiza*: descarta el código nativo, reconstruye el estado que
tendría el intérprete en ese punto exacto y sigue en bytecode. Esto es lo que hace que en
JavaScript una función que recibe siempre el mismo tipo sea de otro orden de magnitud que la
misma función recibiendo dos tipos distintos, sin que el código fuente cambie una letra.

**Vuelta al repo.** Todo esto tiene un solo lugar donde importa en este sistema, y conviene
decirlo con precisión porque es lo que ordena el resto del capítulo. En la PWA hay 126
archivos `.ts`/`.tsx` y 26.745 líneas, y prácticamente todas corren **una vez por click** y
después se quedan esperando una respuesta de la red: leer una lista, armar un pedido, pintar
una tabla. Nada de eso llega a ser código caliente; se ejecuta en el intérprete y ahí muere.
La excepción es una sola:

- `Proyecto - PWA/src/frontend/src/views/socio/ContadorReps.tsx:222-290` · `bucle` — la
  función que se vuelve a agendar a sí misma con `requestAnimationFrame` en la línea 289, o
  sea unas sesenta veces por segundo mientras la cámara está abierta.
- `Proyecto - PWA/src/frontend/src/views/socio/logicaReps.ts:232-240` · `anguloEntre` —
  aritmética de punto flotante pura sobre seis restas, tres multiplicaciones, dos `Math.hypot`
  y un `Math.acos`, llamada varias veces por fotograma desde ese bucle. (Qué calcula y por qué
  esa cuenta es la del ángulo lo explica
  [A0-14](A0-14-vision-en-el-dispositivo.md#ángulo-entre-tres-puntos); acá sólo importa que es
  la única función del repositorio que el compilador optimizador llega a ver.)

Es la única parte de la PWA donde el reparto del tiempo lo decide el procesador y no la red.

---

## Cierre (closure)

**El problema de origen.** Una función que se pasa como argumento para que alguien la llame
después —un manejador de click, el `.then()` de una promesa, la limpieza de un efecto— se
ejecuta en un momento en que el marco de pila que la creó ya no existe. Si las variables
locales vivieran sólo en la pila, esa función se despertaría sin nada alrededor. En un
lenguaje donde casi toda la ejecución es "esto pasa cuando el usuario haga algo" o "esto pasa
cuando conteste el servidor" —que es exactamente el modelo del
[bucle de eventos](A0-04-el-navegador-por-dentro.md#bucle-de-eventos-tarea-y-microtarea-promesa-y-asyncawait)—
eso lo volvería inutilizable. El cierre es el mecanismo que lo resuelve: **la función se
lleva consigo el entorno donde fue escrita.**

> **↓ Capa 1 — dónde vive ese entorno.**

Al entrar en un alcance, el motor crea un *registro de entorno*: una estructura con un
casillero por cada `let`, `const`, parámetro o `function` de ese bloque. Un objeto función
guarda dos cosas: el código a ejecutar y un puntero al registro de entorno vigente en el
momento de crearse. Cuando el cuerpo menciona un nombre que no es local, el motor sigue esa
cadena de punteros hacia afuera hasta encontrar el casillero.

La consecuencia de memoria es la que define el piso: si ninguna función escapa, el motor
puede poner esos casilleros en la pila y descartarlos al volver. Si alguna escapa, el registro
se aloja en el montón y **vive mientras viva la función que lo apunta**, no mientras dure la
llamada que lo creó. Y lo que se comparte es el casillero, no una copia de su valor: dos
funciones creadas en el mismo alcance ven y modifican exactamente el mismo dato.

**Vuelta al repo.** El caso más claro está en el contador de repeticiones, en
`Proyecto - PWA/src/frontend/src/views/socio/ContadorReps.tsx:192-301`. Adentro del efecto hay
una sola variable, `let vivo = true` (línea 195), y **tres funciones distintas la comparten**:

| Función | Líneas | Qué hace con `vivo` |
|---|---|---|
| `arrancar` | 197-220 | la lee después de `await getUserMedia` (203) y después del `catch` (215) |
| `bucle` | 222-290 | la lee en cada fotograma (226) |
| la limpieza del efecto | 294-299 | la **escribe** en `false` (295) |

Cuando la persona cierra la cámara, React ejecuta la limpieza y `vivo` pasa a `false`. El
siguiente fotograma que ya estaba agendado entra en `bucle`, lee **ese mismo casillero** y
vuelve sin dibujar ni contar nada. Ninguna de las tres funciones recibe `vivo` por parámetro
y ninguna la guarda en el módulo: las tres apuntan al mismo registro de entorno, que el motor
mantiene vivo en el montón precisamente porque `bucle` sigue encolado en el navegador.

Sin cierres habría que inventar un lugar donde guardar ese `true`/`false` —una variable de
módulo, una propiedad de un objeto— y ese lugar sería compartido entre todas las instancias
del componente, que es el error que el cierre evita de arranque. Es también el mecanismo
sobre el que se apoya que un componente "recuerde" entre renders, cosa que explica
[A0-06](A0-06-react.md#props-estado-local-y-re-render) en su lugar.

---

## Tipado estático y borrado de tipos

**El problema de origen.** Hacia 2010 había bases de JavaScript de decenas de miles de líneas
y ninguna forma de saber, parado en una función, qué recibe. No es una molestia estética: es
que renombrar un campo obliga a buscar la cadena de texto en todo el proyecto y rezar, y que
pasar `undefined` donde se esperaba un número no falla en la llamada sino tres capas más
abajo. Hubo dos intentos previos de resolverlo sin cambiar el lenguaje: Closure Compiler de
Google, que ponía los tipos en comentarios `/** @param {number} */`, y más tarde Flow de
Facebook. Microsoft publicó TypeScript en 2012, con Anders Hejlsberg —el de Turbo Pascal y
C#— a cargo, y tomó una decisión de diseño que es la que hay que entender:

> TypeScript es un **superconjunto sintáctico** de JavaScript, y todo lo que agrega
> **desaparece** antes de ejecutarse.

La alternativa era diseñar un lenguaje distinto que compilara a JavaScript (lo que hicieron
Dart, CoffeeScript y GWT). Se descartó porque obligaba a reescribir el código existente y
partía el ecosistema en dos. El precio de la decisión elegida es el tema de este capítulo:
**el chequeo ocurre antes de correr, y en tiempo de ejecución no queda absolutamente nada de
él.** La restricción de fondo es sencilla y no tiene vuelta: el navegador que describe
[A0-04](A0-04-el-navegador-por-dentro.md) nunca va a ejecutar TypeScript. Sólo ejecuta lo que
el motor de la sección anterior sabe parsear.

> **↓ Capa 1 — quién chequea y quién borra son dos programas distintos.**

Acá está el punto que casi nunca se dice y del que se deducen todas las rarezas de la
configuración de este repositorio. En `Proyecto - PWA/src/frontend/tsconfig.app.json:16` está
escrito:

```json
"noEmit": true,
```

Es decir: **`tsc` en este proyecto no produce ni un solo archivo.** Chequea y devuelve un
código de salida. El JavaScript que termina corriendo lo produce esbuild, adentro de Vite, y
esbuild **no tiene información de tipos**: procesa archivo por archivo, borra las
anotaciones y sigue. Nunca abre el archivo de al lado.

De esa separación salen tres consecuencias, las tres verificables en el repo:

1. **`"verbatimModuleSyntax": true`** (`tsconfig.app.json:14`). Si un archivo escribe
   `import { MiCuota } from './socioService'`, el borrador no puede saber si `MiCuota` es un
   tipo (hay que eliminar la importación entera) o un valor (hay que conservarla). Hay que
   decírselo. Por eso en `Proyecto - PWA/src/frontend/src` hay **43 apariciones de
   `import type`**, por ejemplo
   `Proyecto - PWA/src/frontend/src/services/cobrosService.ts:17` ·
   `import type { MiCuota } from './socioService';`.

2. **`"erasableSyntaxOnly": true`** (`tsconfig.app.json:22`). Casi todo lo que agrega
   TypeScript se puede borrar sin pensar: una anotación, una interfaz, un genérico. Hay una
   familia que no —`enum`, `namespace` con código adentro, las propiedades declaradas en los
   parámetros del constructor—, porque no se borran: se *traducen* a objetos y asignaciones
   reales. Esta opción las prohíbe, para que borrar sea siempre una operación puramente
   textual. Verificado con `grep` sobre todo `src`: la palabra `enum` aparece tres veces y las
   tres son dentro de un comentario (`config.ts:184`, `services/personalService.ts:206`,
   `services/socioService.ts:991`). **Como palabra clave, cero.**

3. **Los conjuntos de valores se escriben como objetos, no como tipos.** En
   `Proyecto - PWA/src/frontend/src/config.ts:684-698`:

   ```ts
   export const EstadoSocio = {
     ACTIVO: 'Activo',
     // …
     DE_BAJA: 'Dado de baja',
   } as const;

   export type EstadoSocioValue = (typeof EstadoSocio)[keyof typeof EstadoSocio];
   ```

   El objeto `EstadoSocio` es un valor de JavaScript común y silvestre y sobrevive; el tipo
   se **deriva de él** con `typeof` y `keyof`, en esa dirección y no al revés, porque sólo
   una de las dos cosas va a existir cuando el código corra. (Cuáles son esos estados y por
   qué son los que son lo explica [A-09](A-09-estados-derivados.md); acá sólo importa la
   forma en que están escritos.)

> **↓ Capa 2 — el JavaScript que queda, medido.**

Hasta acá es argumentación. Ahora el archivo. En
`Proyecto - PWA/src/frontend/dist/assets/index-3ZEPFFtl.js` está el paquete construido —633.775
bytes, una compilación del 2026-09-12, posterior a buena parte del código fuente pero
anterior a los últimos cambios de `api.ts`, así que sólo cito de él fragmentos que verifiqué
idénticos en las dos puntas—. Contando apariciones con `grep`:

| Se busca en el paquete | Apariciones |
|---|---|
| la palabra `interface` | **0** |
| `SocioListado` (interfaz de `sociosService.ts`) | **0** |
| `OpcionesPedido` (interfaz de `api.ts:168-171`) | **0** |
| `AvisoSesionCaida` (alias de tipo de `api.ts:154`) | **0** |
| `MiCuota` (interfaz de `socioService.ts`) | **0** |
| `RolValue` (alias derivado de `config.ts:197`) | **0** |
| `import.meta.env` | **0** |
| `ServiceError` | **1** |

La única aparición de `ServiceError` merece mirarse de cerca, porque muestra la frontera
exacta. El fuente, en `Proyecto - PWA/src/frontend/src/services/api.ts:13-21`:

```ts
export class ServiceError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ServiceError';
    this.status = status;
  }
}
```

Y lo que quedó en el paquete:

```js
Xn=class extends Error{status;constructor(e,t){super(t),this.name=`ServiceError`,this.status=e}}
```

Tres cosas, una por una:

- `status: number` quedó en `status;`. El campo **existe** (es una declaración de campo de
  clase, que es JavaScript legítimo desde ES2022); lo que desapareció es `: number`.
- `(status: number, message: string)` quedó en `(e,t)`. Los nombres los acortó el minificador;
  las anotaciones no las acortó nadie, simplemente no están.
- El nombre de la clase pasó a ser `Xn`, y sin embargo la cadena `` `ServiceError` `` sigue
  ahí — porque es un literal de texto que el programa escribe en `this.name`, o sea un dato,
  no un tipo. Lo que sobrevive es lo que el programa **usa**, no lo que el programa
  **declara**.

El caso más elocuente es el final de `pedir`. Fuente,
`Proyecto - PWA/src/frontend/src/services/api.ts:239-248`:

```ts
  if (!respuesta.ok) {
    const mensaje = mensajeDelCuerpo(datos, respuesta.status);
    // …
    throw new ServiceError(respuesta.status, mensaje);
  }

  return datos as T;
```

Paquete:

```js
throw new Xn(a.status,rr(o,a.status));return o}
```

**`return datos as T` compiló a `return o`.** La afirmación de tipo no dejó una comprobación,
ni una conversión, ni un byte. Ese es el piso declarado del capítulo, alcanzado y medido:
*de todo el sistema de tipos, lo que existe en tiempo de ejecución es nada.*

> **Nota de lectura, verificada.** `tsconfig.app.json` y `tsconfig.node.json` no contienen la
> clave `strict` ni ninguna de sus subopciones, y ninguno de los dos usa `extends`. El valor
> documentado por defecto de `strict` es `false`. Lo anoto porque cambia qué chequea el
> compilador —y por lo tanto de qué protege el tipo mientras todavía existe—, no como
> objeción: no corrí el compilador, así que no afirmo qué diagnóstico concreto se enciende o
> se apaga con eso.

---

## Frontera de confianza del tipo

**El problema de origen.** Un tipo es una afirmación del programador sobre la forma de un
dato. Mientras el dato nace y muere adentro del programa, el compilador puede verificar esa
afirmación contra el resto del código. En el borde —lo que llega por la red, lo que se lee de
un archivo, lo que escribe un usuario— no hay nada que verificar contra qué: el dato viene de
otro proceso, en otra máquina, escrito en otro lenguaje. **Ahí el tipo deja de ser una
verificación y pasa a ser una declaración de intenciones.** Y como acabamos de ver que no
queda nada de él al correr, tampoco hay quien lo controle después.

La frontera de este sistema está en una función, y en una línea de esa función.

`Proyecto - PWA/src/frontend/src/services/api.ts:194` · `pedir()`:

```ts
export async function pedir<T>(ruta: string, opciones: OpcionesPedido = {}): Promise<T> {
```

`T` es un parámetro de tipo: quien llama dice qué espera recibir. `sociosService.ts:141`
escribe `await pedir<SocioApi[]>('/socios')`, y a partir de ahí todo el archivo trata a ese
valor como un arreglo de `SocioApi`. Lo único que ocurre en el medio es la línea 247,
`return datos as T`, que ya vimos que compila a `return o`. Entre el
[cuerpo JSON](A0-03-http.md#json-como-cuerpo) que llegó del servidor y el tipo que el resto de
la aplicación da por cierto **no hay ni una comprobación**. Si el backend agrega un campo, la
PWA lo ignora; si le saca uno, la PWA lee `undefined` y se entera cuando intenta usarlo, tres
pantallas después.

Hay un segundo lugar donde la frontera se ve todavía mejor, porque ahí la afirmación es más
fuerte que el dato. En
`Proyecto - PWA/src/frontend/src/services/sociosService.ts:102-132` ·
`aSocioListado()`, la interfaz de entrada declara `estado: string` (línea 88) y la línea 126
dice:

```ts
    estado: s.estado as EstadoSocioValue,
```

`EstadoSocioValue` es la unión derivada del objeto de `config.ts:684-698`. La afirmación es
"esta cadena es uno de esos literales". Nadie lo comprueba. Si el backend emitiera mañana una
cadena que no está en el objeto, la conversión la dejaría pasar igual, el valor viajaría a la
grilla y la píldora de estado caería al color neutro sin un error, sin una advertencia y sin
nada en la consola — que es exactamente el modo de fallar contra el que avisa el comentario
de `config.ts:680-683`.

> **↓ Capa 1 — cómo se ve un chequeo de verdad, para contraste.**

La PWA sí comprueba en tiempo de ejecución en un solo lugar, y vale la pena mirarlo porque
muestra qué herramientas quedan cuando el tipo ya no está.
`Proyecto - PWA/src/frontend/src/services/api.ts:126-136` · `mensajeDelCuerpo()`:

```ts
function mensajeDelCuerpo(cuerpo: unknown, status: number): string {
  if (typeof cuerpo === 'object' && cuerpo !== null && 'detail' in cuerpo) {
    const detail = (cuerpo as { detail: unknown }).detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const primero = detail[0] as { msg?: string };
      if (primero?.msg) return primero.msg;
    }
  }
  return `El servidor respondió un error (${status}).`;
}
```

El parámetro es `unknown`, que es el tipo que no deja hacer nada sin preguntar primero. Las
preguntas son `typeof`, `!== null`, el operador `in` y `Array.isArray`: **operadores de
JavaScript, no de TypeScript**, los únicos que sobreviven al borrado. Se escribió así porque
el cuerpo de error de FastAPI tiene dos formas —`{ detail: "texto" }` para los errores
normales y `{ detail: [{ msg, loc }, …] }` para los de validación— y sin distinguirlas la
pantalla mostraría un arreglo de objetos en crudo.

**Vuelta al repo: dónde está entonces la validación de verdad.** En el backend, y en Python.
Cuando la PWA manda una contraseña nueva, su tipo dice `string` y nada más; el chequeo real
está en `backend/schemas.py:113-142` · `CambiarPasswordRequest`, que exige ocho caracteres
(`Field(min_length=8)`, línea 120) y, en `_password_razonable` (líneas 122-142), que tenga
letras y números (133-135), que no esté en la lista de las más probadas de
`schemas.py:105-110` (136-138) y que no pase de 72 bytes (139-141). Ese
rechazo ocurre **antes de que corra una sola línea del router**, y el mecanismo por el que
eso pasa y el formato del error que devuelve lo explica
[A0-10](A0-10-python-del-lado-del-servidor.md#esquema-de-entrada-y-salida-y-el-422).

La misma regla está escrita en las dos puntas: `LARGO_MINIMO_PASSWORD = 8` en
`Proyecto - PWA/src/frontend/src/views/CambiarPasswordView.tsx:27`, usada en la línea 57 para
avisar sin ir al servidor. Las dos copias no cumplen la misma función: la del navegador
existe para que la persona no espere un viaje de ida y vuelta para enterarse de algo obvio, y
la del servidor existe porque es la única que un atacante no puede saltear.

> **Discrepancia menor, verificada.** El comentario de `backend/schemas.py:119` dice
> "(`LARGO_MINIMO_PASSWORD` en `authService.ts`)". La constante no está en ese archivo: está
> en `views/CambiarPasswordView.tsx:27`. Buscado con `grep -rn "LARGO_MINIMO"` sobre todo
> `src`, una sola definición. El comentario quedó apuntando a dónde vivía antes.

**Por qué está hecho así.** Se podría validar la forma de cada respuesta en el cliente —hay
librerías que generan un comprobador a partir del tipo, o se podría escribir a mano una
función por interfaz—. Lo que se estaba optimizando acá es la cantidad de lugares donde una
regla puede quedar desincronizada: con un solo backend y dos aplicaciones consumiéndolo
([A-03](A-03-dos-apps-un-backend.md)), duplicar el comprobador significa mantener tres
versiones de la misma verdad. La restricción que acorrala es que **el cliente no es un lugar
donde se pueda hacer cumplir nada**: cualquiera puede abrir las herramientas del navegador y
mandar el pedido a mano, sin pasar por el código de la PWA. Lo elegido es validar una vez, del
lado del servidor, y usar los tipos del cliente para lo que sí sirven: que el editor y `tsc`
encuentren las inconsistencias internas antes de publicar. Lo que se paga es lo del párrafo
de arriba — un cambio de forma en la respuesta no se detecta al compilar, se detecta en
pantalla. El patrón tiene nombre: **validar en la frontera, y la frontera es el servidor.**

---

## Zona muerta temporal (TDZ)

**El problema de origen.** JavaScript nació con una sola forma de declarar variables, `var`,
y con una regla que en 1995 parecía piadosa: la declaración se "iza" al principio de la
función, así que usar una variable antes de escribirla no es un error, simplemente vale
`undefined`. El resultado en la práctica fue que un error de orden —leer algo antes de
calcularlo— no se manifestaba como un error sino como un `undefined` que se propagaba
silenciosamente hasta reventar lejos del lugar donde estaba la causa.

ES2015 agregó `let` y `const` y cambió esa regla a propósito. El comité eligió que leer una
declaración de bloque antes de su inicialización **lance una excepción**, en vez de devolver
`undefined`. Fallar ruidosamente y en el lugar exacto es mejor que seguir con un valor falso.

> **↓ Capa 1 — qué hace el motor exactamente.**

El binding de un `let` o un `const` **sí se crea** al entrar en el alcance, junto con el
registro de entorno de la sección de cierres. Lo que no tiene es valor: la especificación dice
que queda *sin inicializar*, y que toda lectura de un binding sin inicializar tiene que lanzar
`ReferenceError`. V8 lo implementa poniendo en el casillero un valor centinela interno —en su
código fuente se llama `the_hole`— y comprobándolo en cada lectura de una variable de bloque
cuyo uso el compilador no pudo probar seguro. El tramo entre "el alcance empezó" y "la línea
de la declaración se ejecutó" es la **zona muerta temporal**, y caer adentro produce
exactamente esto:

```
ReferenceError: Cannot access 'tipoElegido' before initialization
```

Temporal y no espacial: no depende de dónde está escrita la lectura, depende de si el flujo de
ejecución ya pasó por la línea de la declaración.

> **↓ Capa 2 — por qué el compilador no siempre lo ve.**

TypeScript tiene un diagnóstico para esto ("variable de ámbito de bloque usada antes de su
declaración"), pero es un chequeo **sintáctico y por alcance**. Cuando la lectura está adentro
del cuerpo de una función, el compilador la acepta, y hace bien: no puede saber cuándo se va
a llamar esa función, y lo normal es que se llame después.

El repositorio tiene el caso legal y el caso ilegal, en dos archivos, y conviene verlos
juntos.

**El legal.** En `Proyecto - PWA/src/frontend/src/views/socio/ContadorReps.tsx`, `arrancar`
(línea 197) llama a `bucle()` en la línea 213, y `const bucle` se declara recién en la 222.
Eso compila y funciona, porque `arrancar()` se invoca en la línea 292, cuando `bucle` ya está
inicializado — y además es `async` y espera a la cámara antes de llegar a esa línea. La
referencia está adentro de un cuerpo de función: diferida.

**El ilegal.** En `Proyecto - PWA/src/frontend/src/views/cobros/CobrosView.tsx`, el arreglo de
dependencias de un efecto **no está adentro de la función**: es un argumento, y se evalúa
durante el render, en el momento. Por eso el archivo tiene dos efectos deliberadamente
ubicados debajo de las constantes que nombran, cada uno con su motivo escrito al lado:

- `CobrosView.tsx:150-172` — el efecto que preselecciona un socio por parámetro de URL va
  después de `seleccionarSocio` (declarada en 123-142). El comentario de las líneas 154-156 lo
  dice: *"el array de dependencias se evalúa durante el render, y leer una const declarada más
  abajo revienta con un ReferenceError que tsc no ve"*.
- `CobrosView.tsx:209-230` — el efecto que pide la vista previa del descuento va después de
  `const tipoElegido` (línea 207), por lo mismo. Comentario en 209-213.

La regla está anotada como trampa del proyecto en `CLAUDE.md:273-274`: *"Un `useEffect` que en
sus deps lee un `const` declarado más abajo compila y revienta por TDZ. Poner los efectos
después."*

> **Lo que no verifiqué.** Los comentarios del código afirman que `tsc` no detecta este caso.
> No corrí el compilador —el encargo de esta masterclass es de sólo lectura—, así que no
> confirmo ni desmiento qué diagnóstico emite TypeScript para una referencia ubicada dentro del
> arreglo de dependencias. Lo que sí es verificable y es la lección: el arreglo se evalúa
> durante el render y no cuando corre el efecto, y por eso el orden de las declaraciones en el
> cuerpo de un componente es semántico y no cosmético. Cuándo corre un efecto respecto del
> render lo explica [A0-06](A0-06-react.md#efecto-y-arreglo-de-dependencias).

---

## Empaquetador y servidor de desarrollo

**El problema de origen.** Son dos problemas encadenados. El primero: hasta 2017 el navegador
no tenía ningún sistema de módulos, así que un proyecto repartido en archivos tenía que
concatenarlos a mano o declarar variables globales y confiar en el orden de los `<script>`. De
ahí salieron Browserify y webpack: programas que leen el grafo de importaciones y escriben un
solo archivo. El segundo problema sobrevivió a los módulos nativos: `import { useState } from
'react'` no es una URL, y el navegador sólo sabe pedir URLs. Alguien tiene que traducir ese
*especificador desnudo* a una ruta concreta. Y aunque los tradujera, 126 archivos son 126
pedidos, cada uno con su viaje de ida y vuelta
([A0-02](A0-02-como-se-comunican-dos-maquinas.md#tcp-y-el-viaje-de-ida-y-vuelta-rtt)).

Vite resuelve los dos, pero con estrategias opuestas según el momento.

> **↓ Capa 1 — en desarrollo, no empaqueta.**

`npm run dev` levanta un servidor HTTP que sirve `index.html` tal cual está, con su
`<script type="module" src="/src/main.tsx">`. El navegador pide ese archivo; el servidor lo
lee, le borra los tipos con esbuild, transforma el JSX y —esto es lo central— **reescribe las
importaciones** antes de devolverlo: `from 'react'` sale como una ruta servible bajo
`/node_modules/.vite/deps/`. El navegador pide entonces esos archivos, y así sucesivamente.
Cada archivo se transforma la primera vez que alguien lo pide y no antes, que es lo que hace
que arrancar el servidor sea instantáneo por más grande que sea el proyecto.

Ese mismo servidor hace una segunda cosa que no tiene nada que ver con módulos: reenvía a otro
servidor todo lo que empiece con `/api`, según `Proyecto - PWA/src/frontend/vite.config.ts:55-63`.
Es un [proxy inverso](A0-03-http.md#proxy-inverso), y existe por una razón de sesión que
explica [A-04](A-04-recorrido-de-un-pedido.md#proxy-api-de-vite); acá sólo interesa el hecho de
que **el mismo proceso que compila también rutea**, porque de eso depende la sección siguiente.

> **↓ Capa 2 — en producción, empaqueta.**

`npm run build` corre `tsc -b && vite build` (`package.json`, sección `scripts`). Vite delega
en Rollup, que recorre el grafo desde `main.tsx`, descarta lo que nadie importa, junta todo y
escribe un archivo con el contenido en el nombre:
`dist/assets/index-3ZEPFFtl.js`. Ese sufijo es un resumen del contenido, y está para que el
archivo se pueda guardar en caché para siempre: si cambia una línea, cambia el nombre, y el
navegador pide uno nuevo en vez de servir el viejo. El `dist/index.html:29` generado apunta
ahí:

```html
<script type="module" crossorigin src="/assets/index-3ZEPFFtl.js"></script>
```

26.745 líneas repartidas en 126 archivos terminan en un pedido. La excepción declarada está en
`vite.config.ts:76-78`: el modelo de pose y el WASM de MediaPipe quedan fuera del paquete y
fuera del precacheo, porque sólo los necesita quien abre el contador de repeticiones. El
modelo, `dist/mediapipe/pose_landmarker_lite.task`, pesa por sí solo 5.777.746 bytes: nueve
veces el paquete entero de la aplicación.

> **↓ Capa 3 — el piso: qué es exactamente una variable de `.env` acá.**

`Proyecto - PWA/src/frontend/src/services/api.ts:56` dice:

```ts
const API_URL = import.meta.env.VITE_API_URL ?? '/api';
```

Eso **no** es leer una [variable de entorno](A0-01-como-corre-un-programa.md#variable-de-entorno-y-archivo-env)
del proceso. El navegador no tiene entorno, y no hay ningún proceso cuyo entorno consultar.
Es una **sustitución de texto** que hace el empaquetador: busca esa expresión en el fuente y
la reemplaza por el literal. La prueba está medida en la tabla de más arriba —`import.meta.env`
aparece **cero** veces en el paquete— y el resultado se lee directo:

```js
Qn=`/api`,$n=`olimpos_csrf`,er=`X-CSRF-Token`;
```

De ahí sale la regla que `Proyecto - PWA/src/frontend/.env.example` explica en su cabecera y
que `CLAUDE.md` repite: sólo las variables con prefijo `VITE_` se sustituyen, y **todo lo que
se sustituye queda escrito en un archivo que baja cualquiera que abra la página**. Por eso en
ese mismo `.env.example` la dirección del backend real se llama `API_PROXY_DESTINO`, **sin**
prefijo: la usa el servidor de desarrollo de la capa 1, que sí es un proceso con entorno, y no
tiene que llegar al navegador. Ese es el piso de este concepto: el módulo resuelto y el archivo
servido, y el hecho de que en el segundo no queda ninguna indirección — el valor está escrito
ahí, en texto.

---

## El chequeo que siempre da OK: por qué `tsc` va con `-p tsconfig.app.json`

Esto no es un concepto nuevo: es la consecuencia operativa directa de que chequear y borrar
sean dos programas distintos. Como `tsc` no emite nada, correrlo es **el único momento** en
que alguien mira los tipos. Si ese comando miente, el sistema de tipos no existe ni antes de
correr.

El proyecto tiene tres archivos de configuración. El de la raíz,
`Proyecto - PWA/src/frontend/tsconfig.json`, entero:

```json
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" }
  ]
}
```

No tiene `include`, y su lista de archivos está vacía a propósito: es una configuración de
*solución*, cuyo único trabajo es nombrar dos proyectos reales. Y ahí está la trampa. `tsc`
sin `-p` busca el `tsconfig.json` más cercano, encuentra este, arma la lista de archivos a
chequear, le da vacía, chequea cero archivos y sale con código 0. No protesta por la lista
vacía porque TypeScript exime de esa queja justamente a las configuraciones que declaran
`references`. Un `npx tsc --noEmit` a secas, en esta carpeta, **siempre da OK**, con el
proyecto compilando o con el proyecto roto. Por eso `CLAUDE.md` deja escrito el comando con la
bandera:

```bash
npx tsc --noEmit -p tsconfig.app.json
```

`-p` apunta al proyecto que sí tiene `"include": ["src"]` (`tsconfig.app.json:25`). Vale la
pena notar que el comando de construcción del propio proyecto **no** tiene el problema:
`npm run build` corre `tsc -b`, y el modo de construcción sí sigue las referencias. El que
miente es el comando de verificación suelto, que es el que se tipea a mano.

**Por qué está hecho así.** La partición en dos proyectos no es decorativa. `tsconfig.app.json`
declara `"lib": ["ES2023", "DOM"]` y `"types": ["vite/client"]` (líneas 5 y 7);
`tsconfig.node.json` declara `"lib": ["ES2023"]` y `"types": ["node"]` (líneas 5 y 6), y su
`include` es un solo archivo: `vite.config.ts`. Son dos entornos de ejecución distintos — uno
corre en el navegador y el otro en Node, antes de que exista un navegador. Lo que se estaba
optimizando es que cada archivo se chequee contra el mundo que realmente va a tener:
`vite.config.ts` usa `process.cwd()` (línea 11) y no puede ver `document`; los archivos de
`src` usan `document.cookie` (`api.ts:102`) y no tienen por qué ver `process`. La alternativa
—un solo `tsconfig.json` que incluya todo— se descarta sola: habría que unir `DOM` y `node` en
un mismo `lib`, y a partir de ahí el compilador aceptaría `process.env` en una vista de React
y `window` en la configuración de Vite, que son dos errores que sólo aparecerían corriendo. Lo
que se pagó por la decisión correcta es exactamente esta trampa: una configuración raíz que
existe para no chequear nada, y un comando de verificación que hay que escribir con la bandera
o no verifica. El patrón se llama **configuración de solución con referencias de proyecto**, y
la contrapartida —que la raíz sea un índice y no un proyecto— es inherente a él.

---

## Con qué se conecta

- **Es la misma idea que…** el intérprete y el bytecode de un programa cualquiera: el motor de
  JavaScript es ese mismo esquema de dos etapas, con un compilador optimizador encima ([A0-01](A0-01-como-corre-un-programa.md#intérprete-bytecode-y-compilación-al-vuelo)).
- **Existe por culpa de…** el bucle de eventos: una función que se ejecuta más tarde necesita
  el cierre porque el marco de pila que la creó ya no está ([A0-04](A0-04-el-navegador-por-dentro.md#bucle-de-eventos-tarea-y-microtarea-promesa-y-asyncawait)).
- **Es el mismo problema que…** el arreglo de dependencias de un efecto: el orden de
  declaración importa en tiempo de ejecución aunque el compilador no chille ([A0-06](A0-06-react.md#efecto-y-arreglo-de-dependencias)).
- **Existe por culpa de…** el borrado de tipos: la validación real vive del lado del servidor
  porque el tipo del cliente ya no existe cuando llega el pedido ([A0-10](A0-10-python-del-lado-del-servidor.md#esquema-de-entrada-y-salida-y-el-422)).
- **Es la misma idea que…** el frontend esconde y el backend rechaza: nada que venga del
  cliente se cree, ni el tipo ni el permiso ([A-08](A-08-autorizacion.md#el-frontend-esconde-el-backend-rechaza)).
- **Existe por culpa de…** el proxy `/api`: el servidor de desarrollo que resuelve módulos es
  el mismo proceso que reenvía los pedidos al backend ([A-04](A-04-recorrido-de-un-pedido.md#proxy-api-de-vite)).
