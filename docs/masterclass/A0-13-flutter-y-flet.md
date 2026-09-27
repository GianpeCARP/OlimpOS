# A0-13 · Flutter y Flet

*Piso del capítulo: el canvas dibujando.*

La app de escritorio de OlimpOS está escrita en Python y se ve casi idéntica a la PWA. Esa
combinación no es obvia: Python no tiene una forma nativa de dibujar interfaces modernas, y
la que usa este repo funciona a través de **dos programas que se hablan**. Este capítulo
explica esas dos piezas —Flutter, que dibuja, y Flet, que lo maneja desde Python— y baja
hasta el punto donde un botón deja de ser un objeto y pasa a ser píxeles.

Las cinco trampas de Flet 0.84 que `CLAUDE.md` documenta como recetas —"usá `alpha()`",
"el scroll va adentro", "`on_select` y no `on_change`"— acá se explican **por su
mecanismo**. Una receta sirve hasta que aparece el caso que no cubre; el mecanismo sirve
para ese caso también.

**Todo lo que este capítulo afirma sobre Flet se verificó en el paquete instalado**, Flet
0.84.0 (`flet`, `flet-desktop` y `flet-web`, en el Python del sistema que usa
`Flet/Proyecto`). Las rutas que empiezan con `flet/` son de ese paquete, no del repo.

---

## Widget y árbol de widgets

### El problema de origen

Es el mismo problema que resolvió React en el navegador, y conviene nombrarlo así porque
la solución es la misma: sincronizar a mano el estado de un programa con lo que muestra la
pantalla no escala. Cada cambio obliga a recordar qué partes de la pantalla dependen de él
y actualizarlas una por una, y el día que alguien se olvida de una, la pantalla miente. La
respuesta de React —describir cómo tiene que verse la pantalla para un estado dado, y dejar
que el framework calcule qué cambió— está en
[árbol virtual y reconciliación](A0-06-react.md#árbol-virtual-y-reconciliación) y no se
repite acá.

Flutter, que Google publicó en su versión 1.0 en diciembre de 2018, aplica esa misma idea
fuera del navegador. La unidad de descripción se llama **widget**: un objeto inmutable que
dice "acá va un texto con este estilo" o "una columna con estos hijos". La pantalla entera
es un **árbol de widgets**, y cuando el estado cambia se describe un árbol nuevo y Flutter
compara.

### Tres árboles, no uno

Lo que distingue a Flutter es que ese árbol de descripciones es sólo el primero de tres, y
cada uno responde a una pregunta distinta:

| Árbol | Qué es | Qué pregunta responde |
|---|---|---|
| **Widgets** | descripciones inmutables, se reconstruyen en cada cambio | ¿qué tiene que haber? |
| **Elementos** | instancias que persisten entre reconstrucciones | ¿cuál es cuál? (la identidad) |
| **Objetos de render** | los que miden, ubican y pintan | ¿dónde va y cómo se ve? |

Los widgets son baratos y se tiran todo el tiempo. Los objetos de render son caros y se
reusan mientras se pueda. El árbol de elementos es el que hace de puente entre los dos: le
dice a Flutter que el widget nuevo "es el mismo" que el viejo, así que el objeto de render
se actualiza en vez de reconstruirse.

> **↓ Capa 1 — cómo se mide una pantalla.** Acá está el mecanismo de la trampa del scroll.

Los objetos de render se miden con un protocolo de una sola pasada que la documentación de
Flutter resume en tres frases: **las restricciones bajan, los tamaños suben, el padre
ubica.** Cada padre le dice a cada hijo "podés medir entre tanto y tanto de ancho y de
alto"; el hijo elige su tamaño dentro de ese rango y lo devuelve; el padre decide dónde
ponerlo.

Dos piezas de ese protocolo chocan entre sí:

- **Un contenedor con scroll** le dice a su hijo, en el eje del scroll: *"tomá la altura
  que quieras, no hay límite"*. Es lo que le permite tener más contenido que pantalla.
- **Un hijo que se expande** (`expand=True` en Flet) pide lo contrario: *"dame exactamente
  el espacio que sobra"*. Para calcular lo que sobra hace falta un límite.

Poner un hijo que se expande adentro de un contenedor con scroll es pedir "el resto de un
espacio infinito". No tiene respuesta.

### Vuelta al repo: el hueco enorme arriba

En Flet, `scroll=` sobre una `Column` convierte esa columna en contenedor con scroll. El
repo cayó en el choque de arriba, y lo documenta en tres vistas con el mismo síntoma. En
`Flet/Proyecto/app/views/dashboard.py:176-180`:

> *"Poner el scroll en la Column exterior (con un hijo expand adentro) hacía que Flet
> centrara todo verticalmente cuando el contenido no llenaba la pantalla, y la pantalla
> arrancaba con un hueco enorme arriba."*

La misma nota está en `app/views/recepcion.py:100-102` y en `app/views/socios.py:753`. Qué
hace exactamente Flet para resolver la contradicción ocurre del lado de Dart y no está en
el paquete de Python, así que el centrado es el **síntoma observado**, no algo deducido. Lo
que sí se deduce del protocolo es por qué la solución funciona.

La estructura correcta está en `recepcion.py:103-106`:

```python
return ft.Column([
    topbar,
    ft.Container(content=cuerpo, padding=ft.Padding.all(24), expand=True),
], spacing=0, expand=True)
```

La columna de afuera **no** tiene scroll: recibe una altura con límite (la de la ventana),
deja fijo el `topbar` y le da al `Container` exactamente lo que sobra. Recién adentro de
`cuerpo` está la columna con scroll, y ella sí recibe un límite, el que le dio su padre. Cada
pieza del protocolo recibe la clase de restricción que sabe usar.

---

## Canvas de Flutter

### El problema de origen

Un botón de Windows no es igual a uno de macOS, ni a uno de Android. Los frameworks que
quieren correr en todas partes tomaron históricamente una de dos rutas: **envolver los
controles nativos** de cada sistema —con lo cual la app se ve distinta en cada uno y hereda
las diferencias de comportamiento— o **dibujar todo ellos mismos**.

Flutter tomó la segunda sin concesiones: **no usa ningún control del sistema operativo.**
Cada botón, cada campo de texto, cada sombra, lo pinta el motor de Flutter píxel por píxel
sobre una superficie en blanco. Ese motor tiene su propia biblioteca de gráficos —Skia,
la misma que dibuja Chrome, y en algunas plataformas su reemplazo más nuevo, Impeller—.

Esa decisión técnica es la que hace posible una decisión del dueño: que la PWA y Flet **se
vean casi idénticas**. Si Flet envolviera los controles de Windows, un botón de la app de
escritorio se vería como un botón de Windows, no como el de la PWA. Como Flutter dibuja
todo, la paleta Kinetic Carbon se ve igual en la PC de recepción que en el navegador. Por
qué el dueño quiso las dos apps así se explica en
[las dos aplicaciones](A-03-dos-apps-un-backend.md).

> **↓ Capa 1 — el objeto de render convertido en instrucción de dibujo.**

Al final del protocolo de medida, cada objeto de render tiene un tamaño y una posición.
Entonces Flutter recorre el árbol y le pide a cada uno que **se pinte**: el objeto recibe un
lienzo y emite instrucciones —"un rectángulo redondeado de 8 píxeles de radio en tal
lugar, relleno con `#1C1F26`", "este texto en esta fuente en tal coordenada"—. Esas
instrucciones no se ejecutan una por una: se graban en una lista, y el motor las
transforma en trabajo para la placa de video. Ese es el piso de este capítulo: **el canvas
dibujando.**

> **↓ Capa 2 — dónde queda ese canvas, en cada modo.**

- **En la ventana de escritorio** (`ft.run(main, assets_dir="assets")`,
  `Flet/Proyecto/main.py:64`), la superficie es la ventana nativa que abre el cliente de
  Flutter. Windows sólo ve un rectángulo que se llena de píxeles.
- **En el navegador**, la superficie es un elemento HTML `<canvas>`. En Flet 0.84 no hay otra
  opción: el renderizador web sólo puede ser `canvaskit` o `skwasm`
  (`flet/controls/types.py:33-40`, la enumeración `WebRenderer`). Los dos son Skia compilado
  a WebAssembly, dibujando en ese `<canvas>`. El modo que armaba la página con elementos HTML
  ya no existe.

### Dos canvas con el mismo nombre

Conviene no confundir este canvas con el que describe
[motor de render y canvas](A0-04-el-navegador-por-dentro.md#motor-de-render-y-canvas). Ése
es un **nodo del DOM** sobre el que una página dibuja con JavaScript, y en OlimpOS lo usa
exactamente una pieza: el contador de repeticiones, que pinta el esqueleto encima del
video. El de esta sección es **la superficie completa del motor de Flutter**: en el
navegador está implementada sobre un `<canvas>`, pero en la ventana de escritorio ni
siquiera existe un navegador. Son dos conceptos distintos que comparten la palabra.

### La consecuencia: no hay nada que tocar

Como en modo web toda la app es un solo `<canvas>`, **el DOM no contiene ni un botón ni un
campo.** Para un programa que inspecciona la página buscando el campo "usuario" para
escribir en él, no hay nada que encontrar: hay un rectángulo de píxeles.

Los campos de texto tienen una excepción, y explica el último detalle. Cuando un campo toma
el foco, Flutter crea un elemento `<input>` invisible encima de él para recibir el texto
del sistema operativo —el teclado, el autocompletado, los acentos compuestos—. Ese
elemento existe sólo mientras el campo tiene foco. Y el navegador inserta caracteres en un
`<input>` sólo como respuesta a eventos de teclado **genuinos**: un evento fabricado desde
el código de la página queda marcado como no confiable (`isTrusted` en falso) y no produce
texto.

`CLAUDE.md` documenta el resultado sin detallar cuál de los dos mecanismos lo causó con la
herramienta que se usó: *"Flutter no recibe el teclado sintetizado por automatización: el
login hay que tipearlo a mano"*. Y documenta la salida: lo que se puede automatizar de un
diálogo es **armarlo y auditarle el árbol de controles**, instanciando la vista con un
estado simulado y leyendo `page.overlay`. Es decir, en vez de mirar los píxeles, se mira
el árbol del que salieron. Por qué eso es posible —y qué cuesta— está al final de la
[sección siguiente](#control-de-flet-update-y-pageoverlay).

---

## Puente Python ↔ Flutter

### El problema de origen

Flutter se programa en Dart. Las apps de Flutter son programas Dart compilados, con el motor
adentro. Python no puede correr **adentro** de esa app.

La idea de Flet es resolver eso sin tocar Flutter: correr **dos programas separados**. Uno
es un cliente de Flutter ya compilado, que viene dentro del paquete `flet-desktop` y sabe
dibujar cualquier control de Flet. El otro es el proceso de Python con el código de la app.
El cliente de Flutter no sabe nada de OlimpOS; el proceso de Python no sabe dibujar. Se
hablan por un canal, y todo lo que pasa en pantalla es el resultado de esa conversación.

> **↓ Capa 1 — el canal.**

`flet/messaging/flet_socket_server.py`, en `start()`, elige el canal según el sistema
operativo. Textual del docstring: *"TCP on Windows or when `port > 0`; UDS on non-Windows
when `port == 0`"*. En esta PC, que es Windows, Python abre un servidor TCP en `localhost`,
en un [puerto](A0-02-como-se-comunican-dos-maquinas.md#puerto) libre que le pide al
sistema, y el cliente de Flutter se conecta a él. En Linux o macOS usaría un *socket de
dominio Unix*, un archivo especial en la carpeta temporal que cumple el mismo papel sin
pasar por la pila de red.

Que sea `localhost` importa: la conversación nunca sale de la máquina
([loopback](A0-02-como-se-comunican-dos-maquinas.md#loopback-contra-ip-de-la-lan)), así que
cada mensaje cruza en microsegundos, no en los 44 ms de São Paulo.

En **modo web** el canal cambia de forma, no de contenido. El cliente de Flutter corre
adentro del navegador, y ahí no puede abrir un socket TCP crudo: usa un **WebSocket**
(`flet_web/fastapi/flet_app.py:104`, el método `handle(websocket)`). Un WebSocket arranca
como un pedido HTTP común y, si el servidor acepta, esa misma conexión se convierte en un
canal abierto en los dos sentidos, por el que cualquiera de las puntas puede mandar
mensajes cuando quiera, sin que el otro haya preguntado nada. Es justamente lo que necesita
Flet: que Python pueda empujar cambios a la pantalla sin esperar un pedido.

> **↓ Capa 2 — el mensaje que cruza el puente.** Este es el piso del concepto.

Por ese canal no viaja texto sino **msgpack**: un formato binario con la misma estructura
que JSON —números, textos, listas, diccionarios— pero más compacto y más rápido de leer.
Cada mensaje es un par, y el docstring de `flet/messaging/protocol.py` (en `ClientAction`)
lo dice textual: *"protocol frames are encoded as `[action_code, body]`"*.

Los códigos posibles son seis, y cada uno tiene un sentido fijo:

| Código | Acción | Sentido | Qué lleva |
|---|---|---|---|
| 1 | `REGISTER_CLIENT` | los dos | el saludo inicial: el cliente se presenta y recibe la sesión |
| 2 | `PATCH_CONTROL` | Python → Flutter | los cambios del árbol de controles |
| 3 | `CONTROL_EVENT` | Flutter → Python | "tocaron este botón", "cambió este campo" |
| 4 | `UPDATE_CONTROL_PROPS` | Flutter → Python | un valor que cambió del lado del cliente (el texto tipeado) |
| 5 | `INVOKE_METHOD` | los dos | una llamada a un método del control y su respuesta |
| 6 | `SESSION_CRASHED` | Python → Flutter | el código de Python explotó |

`flet/messaging/protocol.py:222-259`. El docstring agrega una restricción que muestra que
son dos programas escritos por separado: los números *"must stay in sync with Dart
`MessageAction` values"*. Si Python y Dart no coinciden en qué es el 3, cada uno entiende
otra cosa.

### Un click, contado

Con esa tabla, el recorrido de un click en la app de escritorio es exacto:

1. La persona toca "Cobrar". El cliente de Flutter manda un `CONTROL_EVENT` por el socket.
2. Python recibe el mensaje y ejecuta el manejador del botón.
3. El manejador llama al backend de FastAPI por HTTP (y ahí empieza el recorrido de
   [A-04](A-04-recorrido-de-un-pedido.md), con su viaje a São Paulo).
4. Con la respuesta, el manejador cambia controles y llama a `update()`.
5. Python manda un `PATCH_CONTROL` con lo que cambió.
6. Flutter aplica el parche, mide de nuevo lo que haga falta y repinta.

Son **dos puentes en serie**: el de Flet, en microsegundos por loopback, y el HTTP al
backend, en cientos de milisegundos contra Neon. Por eso en la app de escritorio el costo
del primero no importa y todo el esfuerzo de rendimiento está en el segundo.

### Por qué está hecho así

**Qué se optimiza:** escribir la app del mostrador en Python —el mismo lenguaje que el
backend— y aun así obtener una interfaz que se vea igual a la PWA.

**Qué alternativa se descartó:** las bibliotecas de interfaz tradicionales de Python, como
Tkinter o PyQt, que corren en un solo proceso y envuelven controles del sistema. No hay
puente ni protocolo, pero tampoco hay forma de que se vean como la PWA.

**Qué se pagó:** dos programas en vez de uno, un protocolo en el medio, y una versión de
Flet con su propia API que cambia entre versiones. Las trampas de la sección siguiente son
el precio concreto.

**Cómo se llama:** arquitectura cliente-servidor aplicada a una interfaz local. Es la misma
separación que hay entre la PWA y el backend, pero adentro de la misma máquina.

---

## Control de Flet, `update()` y `page.overlay`

### El control

Del lado de Python, cada widget de Flutter tiene un gemelo: un **control** de Flet. `ft.Text`,
`ft.Column`, `ft.Dropdown` son clases de Python —técnicamente `dataclasses`, clases cuyos
atributos están declarados como campos— y cada campo es una propiedad que puede cruzar el
puente. Cambiar `texto.value = "Hola"` cambia un objeto de Python y **nada más**: la
pantalla no se entera.

### `update()`: el parche

`update()` es la llamada que sincroniza. Y no manda el árbol entero: manda **la diferencia**.
El codificador de Flet guarda, en cada control, una copia de cómo estaba la última vez que
se envió —el docstring de `flet/messaging/protocol.py` habla de *"snapshots (…) captured into
`__prev_*` attributes for patch"*— y al llamar a `update()` compara, arma un
`PATCH_CONTROL` sólo con lo distinto, y lo manda.

Es la misma técnica que el [mapa de identidad del ORM](A0-09-el-orm.md#sesión-y-mapa-de-identidad)
usa para emitir un `UPDATE` sólo de las columnas cambiadas: una foto al enviar, una
comparación al volver a enviar. La diferencia es que acá hay que pedirlo: el repo tiene **52
llamadas a `.update()`** en `Flet/Proyecto/app/`.

### La trampa del `Dropdown`, por su mecanismo

`CLAUDE.md` lo dice como receta: *"`ft.Dropdown` usa `on_select`, no `on_change`"*. El
porqué está en qué es un campo.

En Flet 0.84, `Dropdown` declara `on_select` como campo (`flet/controls/material/dropdown.py:226`,
*"Called when the selected item of this dropdown has changed"*) y **no tiene** un campo
`on_change`. Lo que lo vuelve un error fácil de cometer es que es **la excepción entre sus
hermanos**: revisando los campos de cada control en el paquete instalado, `TextField`,
`Checkbox`, `Switch`, `Slider` y `RadioGroup` usan todos `on_change`, y `Dropdown` es el
único control de entrada que avisa el cambio con otro nombre. Quien viene de escribir
cuatro formularios escribe `on_change` por reflejo.

Lo que pasa depende de cómo se escriba, y se probó con el paquete instalado:

| Cómo se escribe | Qué pasa |
|---|---|
| `ft.Dropdown(on_change=f)` | `TypeError: Dropdown.__init__() got an unexpected keyword argument 'on_change'` |
| `d = ft.Dropdown()` y después `d.on_change = f` | **nada**: ni error ni evento |

El primer caso es ruidoso: explota al construir la vista y se arregla en un minuto. El
segundo es el peligroso, y el mecanismo es preciso. Python deja agregarle cualquier atributo
nuevo a un objeto, así que la asignación funciona. Pero `on_change` no es un campo del
`dataclass`, y el codificador sólo manda campos. El manejador queda colgado de un objeto de
Python y **nunca cruza el puente**: Flutter no sabe que hay que avisar, y la persona elige
una opción que no dispara nada.

### La trampa del color, por su mecanismo

La otra receta de `CLAUDE.md`: *"`f"{color}20"` no es transparencia (Flet lee `#AARRGGBB`):
usar `alpha()` de `config.py`"*.

Un color hexadecimal de seis dígitos tiene tres pares: rojo, verde y azul. Para agregar
transparencia se agrega un cuarto par, y **la PWA y Flet no se ponen de acuerdo en dónde
va**:

- **CSS**, y por lo tanto la PWA, lee ocho dígitos como `#RRGGBBAA`: la opacidad **al
  final**.
- **Flutter**, y por lo tanto Flet, los lee como `#AARRGGBB`: la opacidad **adelante**.

Con el volt del sistema, `#C6F135` (`Flet/Proyecto/app/config.py:53`), y dos dígitos `20`
pegados al final:

```
"#C6F13520"
  CSS     →  RR=C6 GG=F1 BB=35  AA=20  →  el volt, al 12,5 % de opacidad
  Flutter →  AA=C6  RR=F1 GG=35 BB=20  →  #F13520, un rojo anaranjado, al 78 %
```

El mismo texto, en las dos apps gemelas, es dos colores distintos. Y el resultado de
Flutter coincide con el síntoma que el docstring de `alpha()` reporta como la razón del
arreglo: *"era el motivo de que los íconos de 'Actividad Reciente' se vieran rojos"*
(`config.py:100-112`).

`alpha()` resuelve esto sin armar el hex a mano: delega en `ft.Colors.with_opacity`, que
devuelve el formato `"color,opacidad"` que Flet interpreta sin ambigüedad.

### `page.overlay`: la capa de los diálogos

Una pantalla de Flet tiene su árbol principal y, encima, una lista aparte, `page.overlay`,
para lo que tiene que flotar sobre todo lo demás: diálogos, avisos, selectores. En este repo,
los diálogos entran ahí por un solo camino, `open_dialog()` en
`Flet/Proyecto/app/components/ui.py:803-807`:

```python
def open_dialog(page: ft.Page, dlg: ft.AlertDialog):
    """Agrega el diálogo al overlay y lo abre."""
    page.overlay.append(dlg)
    dlg.open = True
    page.update()
```

y salen por `close_dialog()` (`ui.py:810-813`), que hace `dlg.open = False` y `update()`.
El primero se llama desde **47** lugares y el segundo desde **68** (un mismo diálogo suele
cerrarse desde más de un botón).

### Por qué está hecho así: el diálogo que nunca se va

Hay una consecuencia de esas dos funciones que no está escrita en ningún lado del repo:
**`close_dialog()` oculta el diálogo pero no lo saca de `page.overlay`, y ningún otro lugar
lo saca.** Una búsqueda de `overlay.remove`, `overlay.clear` u `overlay.pop` en todo
`app/` no encuentra nada. Cada diálogo que se abre en una sesión queda en el árbol, oculto,
hasta que se cierra la aplicación: en la PC del mostrador, abierta todo el día cobrando y
fichando, se acumulan de a cientos. Qué tan caro es eso —en memoria, y en el trabajo de
comparar el árbol en cada `update()`— no se midió.

Flet 0.84 tiene una forma que sí los saca: `page.show_dialog(dialog)`
(`flet/controls/base_page.py:374`) mete el diálogo en una pila propia y envuelve su evento
de cierre para **quitarlo de la pila** cuando se descarta, y `page.pop_dialog()` (línea 421)
cierra el último.

Lo que hace interesante el caso es que la forma actual **también compra algo**. La técnica
que `CLAUDE.md` documenta para probar diálogos sin navegador —armarlos con un estado simulado
y leer `page.overlay`— funciona precisamente porque los diálogos viven en esa lista. Pasar
a `show_dialog()` limpiaría la acumulación y obligaría a cambiar cómo se auditan. Es una
decisión con dos lados, y queda anotada como tal, no como un defecto.

---

## `assets_dir` y modo web

### El problema de origen

La app muestra archivos que no son código: el logo de la barra lateral, por ejemplo. El
cliente de Flutter los pide por nombre suelto —`"logo-removebg-preview.png"`— y alguien
tiene que saber en qué carpeta buscarlos. Eso es `assets_dir`, y `main.py:61-64` lo explica
junto a la línea que arranca la app:

```python
# assets_dir es necesario para que Flet resuelva las imágenes que se piden
# por nombre suelto (el logo del sidebar: "logo-removebg-preview.png").
# Sin este parámetro la carpeta assets/ no se monta y la imagen no aparece.
ft.run(main, assets_dir="assets")
```

### El modo web, y por qué existe

`ft.run(main, assets_dir="assets")` abre una ventana nativa. Para ver la app en el navegador
existe `Flet/Proyecto/scripts/lanzar_flet_navegador.py`, que reusa **la misma función
`main()`** y sólo cambia cómo se muestra (línea 41):

```python
ft.run(main, view=ft.AppView.WEB_BROWSER, port=8551, assets_dir=ASSETS)
```

El docstring dice para qué (líneas 4-6): la ventana nativa es *"imposible de
screenshotear"*. Con el mismo código servido como página, las herramientas del navegador sí
pueden capturarla.

Ese archivo documenta dos trampas que ya costaron. Las dos se entienden con un mecanismo
que no es de Flet.

> **↓ Capa 1 — la imagen que no da 404.**

Primera trampa (líneas 17-22): con `assets_dir="assets"` a secas, Flet resuelve la ruta
relativa **contra la carpeta del script que llama a `ft.run()`**, no contra la carpeta de
trabajo, *"aunque se haga os.chdir()"*. Como el lanzador vive en `scripts/`, buscaba
`scripts/assets/`, que no existe.

Lo instructivo es cómo falló: el logo *"devolvía 200 con 3775 bytes de HTML en vez del
PNG, y en pantalla quedaba el recuadro verde vacío. Cuesta verlo porque no da 404"*.

Eso no es un capricho de Flet sino un comportamiento estándar de los servidores de
aplicaciones de una sola página. Cuando la navegación la resuelve el propio cliente
([enrutado del lado del cliente](A0-06-react.md#enrutado-del-lado-del-cliente)), el
servidor no conoce las rutas: cualquier dirección que no sea un archivo existente se
responde con el `index.html`, para que el cliente la interprete. Esa misma regla, aplicada
a una imagen que no existe, devuelve la página principal con código 200. Para el navegador
es una respuesta exitosa que resulta no ser una imagen, y no hay ningún error que mirar.

La solución es una ruta absoluta derivada del propio archivo (líneas 27-32 y 37-39), con un
chequeo que corta el arranque si la carpeta no existe, porque es preferible no arrancar a
arrancar con el logo roto sin saberlo. Y la raíz se deriva de `__file__` y no de una ruta
fija porque, como anota el comentario, *"el repo vive en D: en una máquina y en E: en la
otra"*.

> **↓ Capa 2 — el archivo que se importa a sí mismo.**

Segunda trampa (líneas 11-15): el lanzador **no puede llamarse `flet_web.py`**. Para servir
por HTTP, Flet ejecuta `from flet_web.fastapi… import …`. Python busca los módulos en el
orden de `sys.path`, y el primer lugar de esa lista es la carpeta del script que se está
ejecutando. Con un archivo llamado `flet_web.py` en esa carpeta, Python lo encuentra
**antes** que el paquete instalado, importa el lanzador en lugar de Flet, y todo termina en
un error que no menciona nombres de archivo: *"asyncio.run() cannot be called from a running
event loop"*.

Es el caso general de **un nombre que tapa a otro**, y la regla que deja es corta: un
archivo propio nunca se llama como un paquete instalado.

---

## Con qué se conecta

- **Es la misma idea que…** el [árbol virtual de React](A0-06-react.md#árbol-virtual-y-reconciliación):
  describir la pantalla y dejar que el framework calcule qué cambió; `update()` es ese
  cálculo pedido a mano.
- **Es la misma idea que…** el [mapa de identidad](A0-09-el-orm.md#sesión-y-mapa-de-identidad):
  una foto al enviar y una comparación al reenviar, para mandar sólo la diferencia.
- **Existe por culpa de…** que las dos apps se vean casi idénticas
  ([A-03](A-03-dos-apps-un-backend.md)): sólo un motor que pinta cada píxel puede dar la misma
  interfaz en la ventana y en el navegador.
- **Se contradice con…** la PWA, en el hex de ocho dígitos: CSS pone la opacidad al final y
  Flutter adelante, así que el mismo texto es un color distinto en cada gemela.
- **Es el mismo problema que…** los [dos puentes del click](#un-click-contado): el de Flet
  cuesta microsegundos por loopback y el del backend cientos de milisegundos contra Neon
  ([base remota](A-11-rendimiento.md#base-remota)).
- **Existe por culpa de…** el [enrutado del lado del cliente](A0-06-react.md#enrutado-del-lado-del-cliente):
  el servidor devuelve `index.html` para cualquier ruta, y por eso una imagen que falta
  responde 200.
