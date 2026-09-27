# A0-14 · Visión por computadora en el dispositivo

> **Piso de este capítulo: la aritmética del ángulo, hecha a mano.** El descenso baja del
> fotograma al tensor, del tensor a la inferencia, de la inferencia a los 33 puntos, y de
> los tres puntos al número de grados —producto escalar, módulos y arcocoseno, con los
> números escritos—. Ahí para. Bajar un escalón más (cómo multiplica matrices el
> procesador gráfico) ya no explica nada de OlimpOS: ese escalón lo nombró una vez
> [Instrucción de máquina y compuerta lógica](A0-01-como-corre-un-programa.md#instrucción-de-máquina-y-compuerta-lógica)
> y no se vuelve a bajar.

---

## El problema del que nace

Un socio entrenando solo pierde la cuenta. No es una anécdota: en la última serie, la que
importa, la persona va con los ojos cerrados y la cabeza en otro lado, y lo que anota
después es lo que se acuerda. Todo el registro de progreso del sistema se apoya en un
número que alguien recuerda mal.

La forma obvia de resolverlo es un sensor: una pulsera con acelerómetro, una máquina
instrumentada. Cuesta plata, hay que comprarlo por socio y sólo funciona con el ejercicio
para el que se diseñó. La forma no obvia es mirar. Todo el mundo ya tiene una cámara en el
bolsillo.

**Qué hacía falta para que "mirar" fuera posible.** Durante treinta años, encontrar un
cuerpo humano en una imagen se hacía con descriptores escritos a mano: estructuras
pictóricas (Fischler y Elschlager, 1973; retomadas por Felzenszwalb y Huttenlocher en
2005) que modelaban el cuerpo como partes rígidas unidas por resortes, y buscaban la
combinación más barata. Funcionaba con fondo limpio, ropa contrastada y la persona de
frente. La Kinect (2010) lo resolvió de otra manera: puso un sensor de profundidad —un
proyector de infrarrojos— para tener, además del color, la distancia de cada píxel, y
sobre eso clasificó parte del cuerpo píxel por píxel. Anduvo muy bien, y exigía comprar
hardware especial.

El salto vino con las redes convolucionales: DeepPose (Toshev y Szegedy, Google, 2014)
mostró que una red podía **regresar directamente las coordenadas** de las articulaciones
desde una imagen común, sin sensor de profundidad y sin modelo de resortes. OpenPose (CMU,
2017) lo llevó a varias personas a la vez. Los dos eran caros: pensados para una placa de
video de escritorio.

El último eslabón es el que usa este repo: **BlazePose** (Google, 2020), una familia de
redes diseñada con la restricción al revés —no "la mejor precisión posible", sino "la
mejor precisión que entre en 33 milisegundos en un teléfono"—. Eso es lo que hace que un
socio pueda apoyar el celular contra una mancuerna y que el conteo pase entero adentro del
aparato.

Este capítulo baja por ese camino hasta el número de grados, y vuelve a subir a los dos
archivos donde vive: `Proyecto - PWA/src/frontend/src/views/socio/logicaReps.ts` y
`Proyecto - PWA/src/frontend/src/views/socio/ContadorReps.tsx`.

---

## Fotograma y tensor

Un **fotograma** es una foto: una matriz de píxeles, y cada píxel un puñado de números.
Un **tensor** es la forma en que un modelo consume esa matriz: un arreglo multidimensional
de números en punto flotante, con una forma declarada y un orden de ejes acordado.

Son dos cosas distintas y entre una y otra hay una conversión que cuesta.

> **↓ Capa 1 — qué hay adentro de un fotograma.** Salteable si ya lo sabés.

La cámara entrega una imagen; en este código nadie le pide una resolución concreta —el
único pedido es de qué lado mira, `facingMode`, en
`Proyecto - PWA/src/frontend/src/views/socio/ContadorReps.tsx:199-202`— así que el tamaño
lo decide el dispositivo. Tomemos un caso común, 1280 × 720:

| Cuenta | Resultado |
|---|---|
| píxeles por fotograma | 1280 × 720 = **921 600** |
| bytes por fotograma (3 canales, 1 byte por canal) | 921 600 × 3 = **2 764 800 B** ≈ 2,64 MiB |
| bytes por segundo a 30 fotogramas | 2 764 800 × 30 = **82 944 000 B/s** ≈ 79 MiB/s |
| lo mismo en bits por segundo | ≈ **663 Mbit/s** |

Ese último número es todo el argumento de [Inferencia en el
dispositivo](#inferencia-en-el-dispositivo): 663 Mbit/s es el caudal en crudo de una sola
persona haciendo sentadillas. No hay red del gimnasio que lo suba, y comprimirlo cuesta
tiempo que no sobra.

El fotograma no se toca en JavaScript. Vive en el elemento `<video>`
(`ContadorReps.tsx:607`), que el navegador alimenta desde la cámara sin pasar por el
código de la página. Lo que la página hace es pasarle **el elemento** a MediaPipe
(`ContadorReps.tsx:237`); la biblioteca lo sube a la textura de video del procesador
gráfico sin copiarlo a memoria de JavaScript. Ese detalle es la diferencia entre 30
fotogramas por segundo y 5.

> **↓ Capa 2 — de la imagen al tensor.** Salteable si ya lo sabés.

El modelo no acepta "una imagen". Acepta un tensor de forma fija: lote, alto, ancho,
canales. Para llegar ahí, la imagen se recorta, se reescala al tamaño exacto que el modelo
espera, y cada byte de 0 a 255 se convierte en un número decimal —típicamente a `[0, 1]` o
a `[-1, 1]`, según con qué normalización se entrenó—.

El archivo del modelo en este repo declara esa entrada, pero no en texto legible: lo único
que se lee al abrirlo son las descripciones de sus metadatos, `Input image to be detected`
e `Input image to be landmarked`. **La resolución exacta de entrada no está localizada**:
la busqué con `grep -a` de cadenas imprimibles sobre
`Proyecto - PWA/src/frontend/public/mediapipe/pose_landmarker_lite.task` y las dimensiones
están guardadas como enteros binarios del formato, no como texto. Lo que sí queda
verificado es que hay **dos** entradas de imagen, porque hay dos modelos adentro; eso se
explica en la sección siguiente.

El punto conceptual: un tensor es números, no una foto. En cuanto la imagen entra a esa
forma, deja de tener píxeles y pasa a tener activaciones, y desde ahí hasta la salida lo
único que ocurre son sumas y multiplicaciones.

---

## Modelo entrenado e inferencia

Un **modelo entrenado** es un archivo de números: los pesos que quedaron después de
mostrarle a una red millones de imágenes con las articulaciones marcadas a mano. La
**inferencia** es el acto de pasarle una entrada nueva y leer la salida. Son dos
actividades con costos que no se parecen: entrenar tomó semanas de granja de servidores en
Google en 2021; inferir tiene que entrar en 33 milisegundos en un teléfono. **Acá sólo
ocurre la segunda.** En este repo no hay una sola línea que entrene nada.

> **↓ Capa 1 — qué hay adentro del archivo.** Salteable si ya lo sabés.

El modelo de este repo son 5 777 746 bytes (≈ 5,5 MiB) en
`Proyecto - PWA/src/frontend/public/mediapipe/pose_landmarker_lite.task`, y la ruta está
escrita en `ContadorReps.tsx:50` (`RUTA_MODELO`). El `.task` es un contenedor comprimido
—las firmas `PK` aparecen junto a los nombres de archivo— y adentro tiene **dos** redes,
que se leen como texto en el propio archivo:

| Archivo interno | Modelo que declara | Para qué |
|---|---|---|
| `pose_detector.tflite` | `blazepose_detector_eff_retina_4kp_sparse_2021_10_18` | Encontrar dónde está la persona en el cuadro |
| `pose_landmarks_detector.tflite` | `blazepose_ghum_39kp_lite_oss_2021_07_02` | Sobre ese recorte, ubicar los puntos del cuerpo |

Las dos etapas existen por una razón de costo: buscar una persona en toda la imagen es
caro, y una persona que entrena no se teletransporta entre un fotograma y el siguiente.
Por eso la tarea se crea con `runningMode: 'VIDEO'` (`ContadorReps.tsx:164`) y se la llama
con una marca de tiempo creciente (`ContadorReps.tsx:237`): en ese modo la biblioteca
guarda estado entre llamadas, reusa el recorte de la persona mientras le sigue el rastro y
vuelve al detector cuando lo pierde. *(La política exacta de cuándo vuelve al detector
vive adentro de `@mediapipe/tasks-vision`, no en este repo.)*

También se lee, en el nombre del segundo modelo, `39kp`: la red predice **39** puntos,
mientras que la interfaz publica **33** —los que enumera el comentario de
`Proyecto - PWA/src/frontend/src/views/socio/logicaReps.ts:29-31`—. Los seis de diferencia
son auxiliares que el modelo usa para alinear el recorte del cuadro siguiente y que la
biblioteca no expone. *(Esto último es inferencia mía a partir del nombre del archivo y de
la arquitectura de dos etapas, no un dato escrito en el repo.)*

> **↓ Capa 2 — qué hace la red con el tensor.** Salteable si ya lo sabés.

Una red convolucional es una pila de capas, y cada capa es la misma operación repetida:
tomar una ventanita del tensor de entrada, multiplicarla término a término por un bloque
de pesos, sumar todo y escribir un número en el tensor de salida. Multiplicar y acumular,
millones de veces. Eso es lo que quiere decir "inferencia" cuando se la mira de cerca: una
**multiplicación de matrices** gigante, sin decisiones ni ramas.

El archivo deja ver **cómo** se abarató esa pila para que entre en un teléfono. Dos
trucos, los dos legibles en los nombres de las operaciones del modelo:

- **Convolución separable en profundidad.** Contando las dos redes del
  contenedor, el archivo trae 33 operaciones distintas llamadas
  `depthwise_conv2d_N/depthwise` (que el número coincida con los 33 puntos clave es
  casualidad: son cosas sin relación). Una convolución normal mezcla, en un solo paso,
  el vecindario espacial y todos los canales; la separable hace primero el vecindario
  canal por canal y después la mezcla entre canales con una ventana de 1×1. Da casi el
  mismo resultado con una fracción de las multiplicaciones. Es la idea que hizo posible
  MobileNet, y de ahí el "Blaze" del nombre.
- **Pesos cuantizados.** Casi toda operación aparece duplicada con el sufijo
  `_dequantize`: los pesos se guardan en enteros chicos y se convierten a decimales recién
  al usarlos. Menos bytes en el archivo y menos memoria movida, que en un teléfono es el
  costo que manda.

La salida no es una sola. El nombre del modelo de puntos declara cinco:
`ld_3d`, `output_poseflag`, `output_segmentation`, `output_heatmap` y `world_3d` —y hay
una `activation_poseflag/Sigmoid`, que es el número entre 0 y 1 que dice "acá hay una
persona"—. Este código usa dos de esas cinco: los puntos en coordenadas de imagen y los
puntos en metros. La máscara de segmentación y el mapa de calor se calculan igual, porque
vienen en la misma pasada. Es parte de lo que se paga por usar un modelo empaquetado en
vez de uno propio.

> **↑ Retorno.** El modelo se carga una sola vez, en
> `ContadorReps.tsx:156-189`, y a propósito **antes** de que haga falta: el efecto corre
> con el arreglo de dependencias vacío al montarse el componente, mientras el socio
> todavía está leyendo en qué posición pararse. Adentro hay un detalle que vale: se intenta
> crear la tarea con `delegate: 'GPU'` y, si eso tira, se reintenta con `'CPU'`
> (`ContadorReps.tsx:161-172`). La misma red, la misma cuenta, ejecutada en el procesador
> gráfico o en el central; si el teléfono no da el primero, el contador anda más lento pero
> anda. Cuando ninguno de los dos funciona, el estado pasa a `'error'` y la pantalla lo
> dice (`ContadorReps.tsx:179-184`). El efecto y su lista de dependencias se explican en
> [Efecto y arreglo de dependencias](A0-06-react.md#efecto-y-arreglo-de-dependencias); el
> tiempo de ejecución de MediaPipe llega como bytecode de WebAssembly desde
> `RUTA_WASM` (`ContadorReps.tsx:49`), que el navegador compila al cargarlo igual que
> cualquier otro [bytecode](A0-01-como-corre-un-programa.md#intérprete-bytecode-y-compilación-al-vuelo).

---

## Punto clave (landmark)

Un **punto clave** es una articulación con nombre: el codo izquierdo es el índice 13,
siempre, en todos los fotogramas. Esa promesa —el mismo índice es siempre la misma parte
del cuerpo— es lo único que hace posible todo lo que sigue, porque permite escribir
"rodilla" como un número.

La numeración de los 33 está fijada por BlazePose y en este repo queda anotada en el
comentario de `logicaReps.ts:29-31`, que es la tabla de consulta que usa el resto del
archivo:

| Parte | Izquierda | Derecha |
|---|---|---|
| Hombro | 11 | 12 |
| Codo | 13 | 14 |
| Muñeca | 15 | 16 |
| Cadera | 23 | 24 |
| Rodilla | 25 | 26 |
| Tobillo | 27 | 28 |

> **↓ Capa 1 — dos sistemas de coordenadas, no uno.** Salteable si ya lo sabés.

MediaPipe devuelve los mismos 33 puntos **dos veces**, y son dos cosas distintas:

- `landmarks` — coordenadas normalizadas a la imagen: `x` e `y` entre 0 y 1 respecto del
  ancho y el alto del cuadro, con el origen arriba a la izquierda. Sirven para dibujar
  encima del video. Cada punto trae además un número de 0 a 1, `visibility`, que es la
  confianza del modelo en que ese punto está realmente visible y no tapado o fuera de
  cuadro.
- `worldLandmarks` — coordenadas **en metros**, con el origen en el punto medio entre las
  caderas. No dependen del encuadre: si el socio se aleja de la cámara, sus `landmarks`
  se achican y sus `worldLandmarks` no cambian.

Este repo declara las dos formas como dos interfaces separadas —`Punto3D` en
`logicaReps.ts:12-17` con `x`, `y`, `z`, y `Punto2D` en `logicaReps.ts:19-22` con nada más
que `visibility`— y las usa **cruzadas**, cada una para lo que sirve. En
`ContadorReps.tsx:258-260` la llamada es:

```ts
medirMovimiento(res.worldLandmarks[0], res.landmarks[0], movRef.current)
```

Los metros para la geometría; el cuadro, sólo por la confianza. La decisión se paga: si
sólo se usaran las coordenadas de imagen, el mismo ejercicio mediría distinto según a qué
distancia esté el teléfono, porque la perspectiva aplasta lo que está lejos. Con los
metros, el ángulo de la rodilla es el ángulo de la rodilla.

`Punto2D` merece un párrafo por lo que **no** tiene: declara un solo campo opcional. Es
una interfaz escrita para pedir lo mínimo —el resto de los campos del objeto real de
MediaPipe existen y no le importan a esta función—. Eso es
[tipado estático](A0-05-javascript-y-typescript.md#tipado-estático-y-borrado-de-tipos) bien
usado: describir el contrato, no la estructura entera.

> **↓ Capa 2 — el umbral de visibilidad.** Salteable si ya lo sabés.

Ninguna de las dos listas viene marcada como "confiable". El modelo siempre devuelve 33
puntos: si el pie está fuera de cuadro, inventa uno y le pone `visibility` bajo. Por eso
hay una función de cinco líneas que decide si mirar o no mirar, `visMin()` en
`logicaReps.ts:242-244`: toma los tres índices del ángulo y devuelve **el menor** de sus
tres valores de confianza. El menor, no el promedio: un ángulo con dos puntos buenos y uno
inventado es un ángulo inventado.

El corte está en 0,6 y se aplica lado por lado, en `logicaReps.ts:273-274`. Si ningún lado
llega, `medirMovimiento()` devuelve `null` (`logicaReps.ts:275`) y arriba, en el bucle, no
se cuenta nada: se incrementa un contador de fotogramas sin señal y, recién pasados 12
—unos 0,4 s a 30 fotogramas por segundo— la pantalla avisa que no ve bien
(`ContadorReps.tsx:282-286`). No avisa al primer fotograma perdido a propósito: un aviso
que titila es peor que ninguno.

---

## Ángulo entre tres puntos

Acá está el piso. Tres puntos en el espacio, un número de grados, y ninguna biblioteca en
el medio: diez líneas de aritmética en `logicaReps.ts:231-240`.

El problema es este. Un movimiento de gimnasio, casi cualquiera, es una articulación que
se cierra y se abre. Sentadilla: la rodilla. Curl: el codo. Peso muerto: la cadera. Si se
pudiera medir cuánto está cerrada esa articulación en cada fotograma, contar
repeticiones sería contar ciclos de un número. Y una articulación es, geométricamente,
**tres puntos**: el de arriba, el del medio —el vértice— y el de abajo. Eso es lo que
declara `Movimiento` en `logicaReps.ts:26-40`, con sus dos ternas `izq` y `der`, y el
comentario que aclara el orden: `[extremo, VÉRTICE, extremo]`.

```ts
export function anguloEntre(a: Punto3D, b: Punto3D, c: Punto3D): number {
  const abx = a.x - b.x, aby = a.y - b.y, abz = a.z - b.z;
  const cbx = c.x - b.x, cby = c.y - b.y, cbz = c.z - b.z;
  const dot = abx * cbx + aby * cby + abz * cbz;
  const mag = Math.hypot(abx, aby, abz) * Math.hypot(cbx, cby, cbz);
  if (mag === 0) return 180;
  const cos = Math.min(1, Math.max(-1, dot / mag));
  return (Math.acos(cos) * 180) / Math.PI;
}
```

> **↓ Capa 1 — por qué el producto escalar da el ángulo.** Salteable si ya lo sabés.

Un vector es una flecha: a dónde ir y cuánto. Restar `a − b` da la flecha que va del
vértice al extremo de arriba; restar `c − b`, la que va del vértice al de abajo. El ángulo
de la articulación es el ángulo que abren esas dos flechas.

El **producto escalar** de dos vectores es la suma de los productos de sus componentes
—una sola línea de multiplicaciones y sumas— y cumple una identidad que es todo el truco:

```
u · v = |u| × |v| × cos(θ)
```

Es decir: si dividís el producto escalar por el producto de los dos largos, lo que queda
es exactamente el coseno del ángulo. Despejar θ es aplicar el arcocoseno. No hay
trigonometría más que esa, y no hace falta saber cómo están orientados los ejes: la
identidad vale en cualquier sistema de coordenadas, porque todo lo que entra son
diferencias entre puntos. Si mañana MediaPipe diera vuelta el eje `y`, esta función
seguiría dando el mismo número.

`Math.hypot(x, y, z)` es √(x² + y² + z²), el largo de la flecha. Los dos largos se
multiplican y ese producto es el divisor.

> **↓ Capa 2 — LA CUENTA, CON NÚMEROS.** Este es el piso del capítulo; no hay capa 3.

Sentadilla. Los índices son `izq: [23, 25, 27]` —cadera, **rodilla**, tobillo—
(`logicaReps.ts:48`) y los umbrales `flex: 95` y `ext: 160` (`logicaReps.ts:53-54`). Las
coordenadas están en metros y con origen en la cadera, así que la cadera queda en el cero.

**Caso A — arriba, la pierna casi derecha.**

```
a = cadera  (23) = ( 0,00 ;  0,00 ;  0,00 )
b = rodilla (25) = ( 0,05 ;  0,45 ;  0,00 )      ← el vértice
c = tobillo (27) = ( 0,00 ;  0,90 ;  0,00 )
```

1. Las dos flechas, desde el vértice:
   `ab = a − b = (−0,05 ; −0,45 ; 0,00)`
   `cb = c − b = (−0,05 ; +0,45 ; 0,00)`
2. Producto escalar:
   `dot = (−0,05)(−0,05) + (−0,45)(+0,45) + (0)(0) = 0,0025 − 0,2025 = −0,2000`
3. Los dos largos:
   `|ab| = √(0,0025 + 0,2025) = √0,2050 = 0,452769`
   `|cb| = 0,452769`
   `mag = 0,452769 × 0,452769 = 0,205000`
4. Coseno:
   `cos = −0,2000 / 0,205000 = −0,975610`
5. Arcocoseno y a grados:
   `acos(−0,975610) = 2,9203 rad`; `2,9203 × 180 / π = **167,32°**`

167,32° es mayor que `ext = 160`: la pierna está **extendida**.

**Caso B — abajo, muslo cerca del paralelo.**

```
a = cadera  (23) = ( 0,00 ;  0,00 ;  0,00 )
b = rodilla (25) = ( 0,40 ;  0,05 ;  0,00 )      ← la rodilla se fue adelante
c = tobillo (27) = ( 0,38 ;  0,50 ;  0,00 )
```

1. `ab = (−0,40 ; −0,05 ; 0,00)` · `cb = (−0,02 ; +0,45 ; 0,00)`
2. `dot = (−0,40)(−0,02) + (−0,05)(0,45) = 0,0080 − 0,0225 = −0,0145`
3. `|ab| = √(0,1600 + 0,0025) = √0,1625 = 0,403113`
   `|cb| = √(0,0004 + 0,2025) = √0,2029 = 0,450444`
   `mag = 0,403113 × 0,450444 = 0,181580`
4. `cos = −0,0145 / 0,181580 = −0,079855`
5. `acos(−0,079855) = 1,6506 rad` → **94,58°**

94,58° es menor que `flex = 95`: la pierna está **flexionada**, y con eso la máquina de
estados entra en fase de bajada.

**Por qué esto importa, en una tercera cuenta.** Movamos la rodilla dos centímetros menos
hacia adelante —`b = (0,38 ; 0,05 ; 0,00)`, todo lo demás igual—:

```
ab = (−0,38 ; −0,05 ; 0,00)   cb = (0,00 ; +0,45 ; 0,00)
dot = 0 + (−0,05)(0,45) = −0,0225
|ab| = √(0,1444 + 0,0025) = 0,383275      |cb| = 0,450000
mag = 0,172474
cos = −0,0225 / 0,172474 = −0,130454
acos → 97,50°
```

**97,50° contra 94,58°: dos centímetros de rodilla son 2,92 grados**, y esos 2,92 grados
son la diferencia entre que la repetición cuente y que no. Esto no es un defecto del
método: es exactamente por qué los umbrales de `MOVIMIENTOS` están anotados con el
historial de su calibración —el comentario de `logicaReps.ts:50-52` cuenta que la
sentadilla se endureció a 95° "para que no cuente un medio recorrido", y el de
`logicaReps.ts:118-120` que las flexiones se relajaron de 100/155 a 105/150 porque
contaban de menos—. Un umbral en este sistema no es una constante elegida: es el resultado
de probar con el teléfono en la mano.

> **↓ Capa 2b — las dos guardas numéricas, y qué pasa si no estuvieran.**

Las dos líneas que parecen defensa paranoica son los dos únicos modos en que esta función
puede devolver basura:

- **`if (mag === 0) return 180;`** (`logicaReps.ts:237`). Si dos de los tres puntos caen en
  la misma coordenada exacta, uno de los largos es 0, el divisor es 0 y `dot / mag` da
  `NaN` (0/0) o `±Infinity`. Devolver 180 es declarar "extendido", que es la postura de
  reposo. Tiene una consecuencia que conviene tener presente: si eso ocurriera con la
  máquina en fase `'flex'`, el 180 alcanzaría para cerrar la repetición. En la práctica no
  llega ahí, porque el filtro de visibilidad de 0,6 descarta antes los fotogramas en que
  el modelo colapsa puntos, y porque el valor pasa por el suavizado antes de compararse.
- **`Math.min(1, Math.max(-1, dot / mag))`** (`logicaReps.ts:238`). Con la pierna
  perfectamente derecha, la matemática exacta da `dot / mag = −1`. La aritmética de punto
  flotante de doble precisión no es exacta: las raíces cuadradas de `Math.hypot` pueden
  dejar el cociente en −1,0000000000000002. `Math.acos` de un valor fuera de `[−1, 1]`
  devuelve `NaN`, y un `NaN` acá **no explota**: se propaga. Todas las comparaciones de
  `pasoRep()` contra un `NaN` dan falso, así que la fase se congela y el contador deja de
  contar **sin ningún mensaje de error**. Dos caracteres de recorte evitan el peor tipo de
  falla: la silenciosa.

> **↑ Retorno.** Esa función se llama, en cada lado del cuerpo que se vea con confianza,
> desde `medirMovimiento()` (`logicaReps.ts:267-277`), y de ahí sale el par de números que
> alimenta todo lo que sigue.

---

## Máquina de estados con umbral

Con el ángulo resuelto queda la pregunta de arriba: **cuándo es una repetición**.

La respuesta ingenua —"contá cuando el ángulo baje de 95"— no funciona por dos razones, y
las dos se ven con números:

1. **A 30 fotogramas por segundo, "estar abajo" dura muchos fotogramas.** Medio segundo en
   el fondo de la sentadilla son 15 fotogramas con el ángulo bajo 95. Contaría 15
   repeticiones.
2. **La señal tiembla.** Corregido lo anterior contando sólo el cruce, un ángulo que se
   queda apoyado en 95,0 con ±1,5° de ruido del modelo cruza la línea varias veces por
   segundo. Contaría de tres a cinco repeticiones por cada una real.

La solución tiene noventa años y nombre propio. En 1934 Otto Schmitt, estudiando el
impulso nervioso del calamar gigante, necesitaba convertir una señal analógica sucia en
una decisión limpia de sí/no, y construyó un circuito con **dos** niveles de conmutación
en vez de uno: para pasar a encendido hay que superar el nivel alto, y para volver a
apagado hay que caer por debajo del nivel bajo. En el medio queda una banda muerta donde
el ruido no puede hacer nada. Eso es el **disparador de Schmitt**, y la propiedad se llama
**histéresis**: la salida depende no sólo del valor actual sino de por dónde se venía.

Este archivo lo implementa en diez líneas. Hay dos estados —`type Fase = 'ext' | 'flex'`,
`logicaReps.ts:24`— y dos transiciones, en `pasoRep()` (`logicaReps.ts:287-296`):

```ts
if (fase === 'ext'  && angMin < m.flex) return { fase: 'flex', conto: false };
if (fase === 'flex' && angMax > m.ext)  return { fase: 'ext',  conto: true  };
return { fase, conto: false };
```

Leído en voz alta: *estando arriba, si bajás de 95 pasás a "abajo" y todavía no contás;
estando abajo, si volvés a superar 160 pasás a "arriba" y **ahí** cuenta*. La banda muerta
de la sentadilla son **65 grados** de recorrido (95 a 160), que ningún temblor del modelo
va a cruzar por accidente. Y la repetición se acredita **al volver arriba**, no al llegar
abajo: bajar y quedarse no es una repetición.

> **↓ Capa 1 — por qué son dos ángulos y no uno.** Salteable si ya lo sabés.

`pasoRep()` no recibe "el ángulo". Recibe dos: `angMin` y `angMax`. Salen de
`medirMovimiento()` (`logicaReps.ts:267-277`), que mide **los dos lados del cuerpo** que
pasen el filtro de visibilidad y devuelve el mínimo y el máximo de los ángulos obtenidos
(`logicaReps.ts:246-252`, `MedicionMovimiento`).

El comentario de `logicaReps.ts:254-266` explica la decisión, y vale la pena porque es la
única parte del mecanismo que no es geometría sino conocimiento del gimnasio: en un jalón
o un press, un brazo casi nunca acompaña al otro con exactitud. Midiendo un solo lado —el
mejor visto— la repetición no cuenta cuando el lado medido es justo el que se quedó atrás.
Con mínimo y máximo, la regla pasa a ser: **"bajó" = el lado más flexionado llegó abajo;
"subió" = el lado más extendido volvió arriba**. La repetición cuenta aunque los brazos no
vuelvan parejos, que es como se entrena de verdad. Cuando el socio está de perfil y se ve
un solo lado, `min === max` y el comportamiento es el de un solo ángulo.

> **↓ Capa 2 — las dos guardas de tiempo.** Salteable si ya lo sabés.

La máquina de estados sola todavía se puede engañar, así que el bucle le pone dos
condiciones de reloj antes de sumar (`ContadorReps.tsx:271-280`):

| Constante | Valor | Qué evita |
|---|---|---|
| `GRACIA_MS` (`ContadorReps.tsx:31`) | 700 ms | Los primeros 0,7 s de la serie son el socio acomodándose. Ese movimiento de preparación no es una repetición. |
| `MIN_ENTRE_REPS_MS` (`ContadorReps.tsx:34`) | 450 ms | Dos repeticiones no pueden estar más cerca que eso, o sea un tope duro de 2,2 por segundo. Nadie hace una sentadilla real en menos de medio segundo. |

El detalle fino está en el comentario de `ContadorReps.tsx:269-270`: cuando una de las dos
guardas rechaza, **la fase avanza igual y sólo no se suma**. Si se descartara también la
transición, la máquina quedaría trabada en `'flex'` y la repetición siguiente tampoco
contaría: un rechazo se propagaría hacia adelante para siempre.

---

## El filtro que hace usable el umbral

*(El filtro One-Euro no figura en la tabla de conceptos del contrato de vocabulario; por
la regla de desempate queda definido acá, que es el capítulo más de abajo que lo toca.)*

Un umbral compara contra un número. Si ese número tiembla, el umbral tiembla con él. La
respuesta clásica es un promedio exponencial: `x̂ = α·x + (1−α)·x̂anterior`, con `α` fijo
entre 0 y 1. Y ahí aparece un compromiso que no tiene salida: con `α` chico se suaviza
bien pero la señal llega **tarde** —el ángulo real ya cruzó los 95 y el suavizado todavía
marca 97—, y con `α` grande se llega a tiempo pero vuelve el temblor.

El filtro **One-Euro** rompe el compromiso haciendo `α` variable: suaviza fuerte cuando la
señal casi no se mueve, y suelta el suavizado cuando la señal se mueve rápido. El
razonamiento es que el ruido molesta donde la señal está quieta —los picos y los valles,
que es justo donde se cuentan las repeticiones— y el retardo molesta donde la señal corre.
Está implementado en `logicaReps.ts:315-355`, y la fórmula está escrita en el comentario
de `logicaReps.ts:307`:

```
tau = 1 / (2π · cutoff)          alpha(cutoff, dt) = 1 / (1 + tau/dt)
cutoff = minCutoff + beta · |velocidad estimada|
```

Con los valores por omisión del repo —`minCutoff = 1.5`, `beta = 0.03`
(`logicaReps.ts:316`)— y a 30 fotogramas por segundo (`dt = 0,0333 s`), el peso que recibe
la medición nueva es:

| Situación | Velocidad del ángulo | `cutoff` | `tau` | **α** |
|---|---|---|---|---|
| Quieto en el fondo | 0 °/s | 1,50 Hz | 0,1061 s | **0,239** |
| Bajando normal | 90 °/s | 4,20 Hz | 0,0379 s | **0,468** |
| Subiendo rápido | 200 °/s | 7,50 Hz | 0,0212 s | **0,611** |

Quieto, la medición nueva pesa 24% y la historia 76%: el temblor se plancha. En plena
bajada pesa 47%, y subiendo fuerte 61%: el filtro casi no frena y el cruce del umbral
llega a tiempo. Eso es lo que un `α` fijo no puede dar.

> **↓ Capa 1 — dos detalles de implementación que no son adorno.**

- **El estado vive en un cierre, no en un objeto.** `crearFiltroUnEuro()` declara `xPrev`,
  `dxPrev` y `tPrev` (`logicaReps.ts:322-324`) y devuelve un objeto con dos métodos que
  las leen y las escriben. Las variables no son accesibles desde afuera y no hay `this`,
  ni clase, ni estado de React: es un [cierre](A0-05-javascript-y-typescript.md#cierre-closure)
  puro. Por eso el componente puede guardar dos filtros independientes —uno para el mínimo
  y otro para el máximo— con dos llamadas (`ContadorReps.tsx:126-127`) y sin ninguna
  coordinación entre ellos.
- **`if (!(dt > 0)) dt = 1 / 30;`** (`logicaReps.ts:337`). La guarda está escrita negando
  la condición buena en vez de preguntando `dt <= 0`, y la diferencia es real: si `dt`
  fuera `NaN`, `NaN <= 0` da falso y el `NaN` seguiría de largo hasta envenenar `alpha` y
  con él todos los valores siguientes; `!(NaN > 0)` da verdadero y lo atrapa. Cubre los
  dos casos —el reloj que no avanzó y el que devolvió algo que no es un número— con una
  sola comparación.

La velocidad que gobierna `cutoff` también se filtra, con su propio `dCutoff = 1.0`
(`logicaReps.ts:340-342`): `α` para la derivada da 0,173, o sea que la estimación de
velocidad es muy suave. Tiene sentido: si la velocidad estimada saltara, el suavizado
saltaría con ella y el filtro adaptativo se volvería otra fuente de ruido.

Y se reinicia entero al empezar cada serie —`filtroMinRef.current.reiniciar()` y su gemelo
en `ContadorReps.tsx:381-382`, junto con `faseRef.current = 'ext'`—: una serie nueva
arranca sin la historia de la anterior.

---

## Inferencia en el dispositivo

**Inferencia en el dispositivo** es correr el modelo en el aparato de la persona en vez de
mandar la entrada a un servidor. Cambia tres cosas de golpe: la latencia, el costo y la
privacidad. Acá las tres empujan para el mismo lado.

**La latencia.** A 30 fotogramas por segundo, el presupuesto por fotograma es **33 ms**
—detectar, medir, decidir y dibujar—. Mandar el fotograma a un servidor implica, como
mínimo, un [viaje de ida y vuelta](A0-02-como-se-comunican-dos-maquinas.md#tcp-y-el-viaje-de-ida-y-vuelta-rtt)
por la red antes de que el servidor empiece a calcular. Cualquier ida y vuelta que no sea
dentro del mismo edificio ya consume el presupuesto entero. Y no es un fotograma: son 30
por segundo.

**El caudal.** Los 79 MiB/s de la tabla del principio son el video en crudo de **una**
persona. Comprimirlo bajaría el número y sumaría tiempo de codificación adentro del mismo
presupuesto de 33 ms.

**El costo.** Un servidor que corra BlazePose para varios socios a la vez necesita
procesador gráfico, y eso se alquila por hora. Corriendo en el teléfono, el modelo es
gratis y escala solo: cada socio nuevo trae su propio procesador.

**La privacidad.** Lo que la cámara está mirando es el cuerpo de una persona entrenando.
El comentario de cabecera del componente lo dice sin vueltas: *"TODO corre en el
dispositivo (MediaPipe BlazePose): el video NUNCA sale del teléfono"*
(`ContadorReps.tsx:43-45`). El backend no tiene ninguna ruta que reciba video, y no la
necesita: lo único que sale del teléfono al terminar la serie es un número de repeticiones
y un peso (`ContadorReps.tsx:409-420`, `guardarSerie()`), y eso pasa por la cola de
registros de [C-02](C-02-offline-first-cola.md).

> **↓ Capa 1 — qué se paga por esta decisión.** Salteable si ya lo sabés.

- **Peso de descarga.** El tiempo de ejecución de WebAssembly pesa 11 756 954 bytes
  (≈ 11,2 MiB) y el modelo 5 777 746 bytes (≈ 5,5 MiB): **unos 17 MiB la primera vez que
  alguien abre el contador**. En `Proyecto - PWA/src/frontend/public/mediapipe/wasm` hay
  tres versiones del tiempo de ejecución —con SIMD, sin SIMD y con módulos— y el navegador
  baja la que su motor soporta, no las tres. Sumadas en disco son ≈ 33,8 MiB, que es de
  donde sale el "~35 MB" del comentario de
  `Proyecto - PWA/src/frontend/vite.config.ts:72-75`.
- **Y por eso quedan fuera del precacheo.** `globIgnores: ['**/mediapipe/**']`
  (`vite.config.ts:76-78`) saca esa carpeta de lo que el service worker guarda al
  instalar. Sin esa línea, cada socio que instala la aplicación se baja 35 MB que
  probablemente no use, y además la compilación aborta por el límite de 2 MB por archivo
  de la herramienta. El precio: la primera vez que se abre el contador hay una espera,
  y por eso el modelo se empieza a cargar mientras el socio todavía lee la pantalla de
  preparación (`ContadorReps.tsx:153-156`).
- **El aparato tiene que dar.** No todos los teléfonos sostienen 30 inferencias por
  segundo. De ahí el intento GPU y el respaldo CPU de `ContadorReps.tsx:161-172`.

> **↓ Capa 2 — quién ve la función, y cómo se decide eso.** Salteable si ya lo sabés.

El contador **sólo aparece en el celular**, y no por el tamaño de la pantalla sino porque
la operación consiste en apoyar el teléfono, alejarse y entrar en cuadro. En una
computadora de escritorio la función no tiene sentido físico.

Decidirlo bien es más difícil de lo que parece, y el archivo
`Proyecto - PWA/src/frontend/src/utils/dispositivo.ts:1-18` explica por qué: la cadena de
identificación del navegador miente, y una ventana angosta puede ser una computadora con
el navegador achicado. `esCelular()` (líneas 13-18) exige **tres** señales a la vez, unidas
con `&&`:

1. `soportaCamara()` — existe `navigator.mediaDevices.getUserMedia` (líneas 9-11).
2. `(pointer: coarse)` — el puntero es grueso, o sea un dedo y no un mouse.
3. `(max-width: 820px)` — la pantalla es angosta.

Las tres tienen que dar. En una computadora portátil con cámara y ventana angosta falla la
segunda, y la función ni se dibuja: la pantalla que no la ofrece no muestra un botón gris,
directamente no muestra nada. El resultado se congela en el estado inicial de un `useState`
con función de inicialización —`const [puedeContar] = useState(() => esCelular())`, en
`Proyecto - PWA/src/frontend/src/views/socio/MiRutinaView.tsx:121` y en
`Proyecto - PWA/src/frontend/src/views/socio/CircuitoView.tsx:63`— así que se evalúa una
vez al montar y no vuelve a correr en cada
[re-render](A0-06-react.md#props-estado-local-y-re-render).

---

## Dónde vive todo esto, línea por línea

Rangos verificados abriendo los archivos. Todas las rutas son relativas a la raíz del
repo.

| Qué | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Los dos sistemas de coordenadas, como tipos | `Proyecto - PWA/src/frontend/src/views/socio/logicaReps.ts` | 12–22 | `Punto3D`, `Punto2D` |
| Los dos estados de la máquina | ídem | 24 | `Fase` |
| Un movimiento: ternas, umbrales y pista | ídem | 26–40 | `Movimiento` |
| Los 15 movimientos, con el historial de calibración en comentarios | ídem | 44–194 | `MOVIMIENTOS` |
| Del ejercicio del catálogo al movimiento, o `null` | ídem | 202–229 | `movimientoDeEjercicio()` |
| **El ángulo, la cuenta entera** | ídem | 231–240 | `anguloEntre()` |
| La confianza mínima de los tres puntos | ídem | 242–244 | `visMin()` |
| El par mínimo/máximo | ídem | 246–252 | `MedicionMovimiento` |
| Medir los dos lados del cuerpo | ídem | 267–277 | `medirMovimiento()` |
| La máquina de estados con histéresis | ídem | 287–296 | `pasoRep()` |
| El filtro adaptativo y su estado en cierre | ídem | 315–355 | `crearFiltroUnEuro()` |
| Rutas del tiempo de ejecución y del modelo | `Proyecto - PWA/src/frontend/src/views/socio/ContadorReps.tsx` | 49–50 | `RUTA_WASM`, `RUTA_MODELO` |
| Las dos guardas de tiempo | ídem | 29–34 | `GRACIA_MS`, `MIN_ENTRE_REPS_MS` |
| Estado del bucle, fuera de React | ídem | 121–131 | `faseRef`, `filtroMinRef`, `filtroMaxRef`, … |
| Carga del modelo, con respaldo a CPU | ídem | 156–189 | efecto de montaje |
| Cámara, bucle y limpieza | ídem | 192–301 | efecto de cámara |
| El bucle por fotograma | ídem | 222–290 | `bucle()` |
| La inferencia | ídem | 237 | `detectForVideo()` |
| El esqueleto dibujado sobre el canvas | ídem | 241–255 | `DrawingUtils` |
| Medición, suavizado, transición y conteo | ídem | 257–288 | — |
| Reinicio completo al empezar la serie | ídem | 374–388 | `empezar()` |
| Video y canvas superpuestos | ídem | 604–609 | — |
| Compuerta de celular, tres señales | `Proyecto - PWA/src/frontend/src/utils/dispositivo.ts` | 9–18 | `soportaCamara()`, `esCelular()` |
| Los ~17 MiB fuera del precacheo | `Proyecto - PWA/src/frontend/vite.config.ts` | 72–78 | `workbox.globIgnores` |

Dos notas de arquitectura que se leen en esa tabla y no en el código:

- **`logicaReps.ts` no importa nada.** Ni React, ni MediaPipe, ni la cámara. Recibe
  arreglos de números y devuelve números y estados. Por eso la sección del ángulo de este
  capítulo se pudo escribir con lápiz y papel: no hay nada más ahí adentro.
- **El bucle escribe en referencias, no en estado de React.** `faseRef`, `filtroMinRef`,
  `ultimaRepRef` y compañía (`ContadorReps.tsx:121-131`) existen porque el bucle corre 30
  veces por segundo y provocar un re-render por fotograma haría competir el conteo con el
  pintado en el mismo hilo. Lo único que sí pasa por el estado de React es lo que tiene que
  verse: el número de repeticiones (`ContadorReps.tsx:277-278`). El bucle mismo se reagenda
  con `requestAnimationFrame` (`ContadorReps.tsx:289`), que lo sincroniza con el ritmo de
  pintado del navegador.

---

## Por qué está hecho así

**Qué se estaba optimizando.** Que la repetición cuente *de la forma que sea*. No la
precisión biomecánica: el objetivo declarado en los comentarios es que el socio no tenga
que mirar la pantalla ni corregir la técnica para que el número suba
(`logicaReps.ts:254-266`, y el pitido al llegar al objetivo en `ContadorReps.tsx:105-108`,
para *"la serie de tu vida"* con los ojos cerrados).

**Qué restricciones acorralaban.** 33 ms por fotograma en un teléfono de gama media; un
solo hilo para contar y pintar; una red que puede no estar; un modelo que devuelve puntos
con ruido y a veces inventados.

**Qué alternativas se descartaron.**

- *Mandar el video al servidor.* Muere en la primera cuenta: 663 Mbit/s y un viaje de ida
  y vuelta por fotograma.
- *Medir un solo lado, el mejor visto.* Es lo que había, y se cambió: el comentario de
  `logicaReps.ts:254-266` lo dice y explica el caso que lo rompía —un brazo que se queda—.
- *Un solo umbral.* Cuenta de tres a cinco repeticiones por cada real en cuanto la señal
  se apoya en el umbral.
- *Un promedio exponencial de `α` fijo.* Descartado en el comentario de
  `logicaReps.ts:298-305`, con el argumento de que obliga a elegir entre temblor y retardo.
- *Contar cualquier ejercicio mapeándolo al movimiento más parecido.*
  `movimientoDeEjercicio()` devuelve `null` a propósito para lo que no sabe contar, y el
  comentario de `logicaReps.ts:196-201` da el motivo: *"mejor no ofrecer la cámara para un
  ejercicio que no sabemos contar bien que contar cualquier cosa"*. El curl femoral queda
  afuera explícitamente para que no lo cuente el movimiento de bíceps
  (`logicaReps.ts:219-221`), y las aperturas y la plancha quedan afuera por naturaleza
  (`logicaReps.ts:226-228`).

**Qué se pagó.**

- Unos 17 MiB de descarga la primera vez, y una carpeta entera fuera del precacheo.
- Umbrales que no se pueden calcular: hay que probarlos con el teléfono, movimiento por
  movimiento. Los comentarios de `logicaReps.ts:50-52`, `118-120` y `167-169` son el
  registro de tres de esas calibraciones.
- Falsos negativos con técnica pobre: un peso muerto con la espalda trabada no baja de
  100° y no cuenta. Eso es deliberado —el comentario de `logicaReps.ts:167-169` dice que se
  endureció justamente *"para que una técnica de mentira no cuente"*—, y el precio es que
  quien entrena mal ve un número que no le cierra.
- El sistema no sabe el peso levantado: la cámara no lo ve, así que lo carga el socio al
  terminar (`ContadorReps.tsx:113-116`).

**Los nombres de los patrones.** **Histéresis** o **disparador de Schmitt**, para los dos
umbrales con banda muerta. **Fallar cerrado**, para el `null` de `movimientoDeEjercicio()`
y para el `null` de `medirMovimiento()`: ante la duda, no contar. **Mover el trabajo al
borde**, para toda la decisión de correr el modelo en el cliente. Reconocer estos tres la
próxima vez que aparezcan en otro sistema vale más que recordar los umbrales de la
sentadilla.

---

## Lo que no quedó verificado

- **La resolución exacta de entrada de cada uno de los dos modelos.** Está en el
  `.task` como enteros binarios; con `grep -a` sobre cadenas imprimibles sólo salen las
  descripciones (`Input image to be detected`, `Input image to be landmarked`) y los
  nombres de las operaciones.
- **Que los 6 puntos de diferencia entre los 39 del nombre del modelo y los 33 de la
  interfaz sean auxiliares de alineación.** Es una lectura del nombre
  `blazepose_ghum_39kp_lite` cruzada con la arquitectura de dos etapas, no un dato escrito
  en el repo.
- **Cuándo exactamente la biblioteca vuelve a correr el detector** en modo `VIDEO`. La
  política vive dentro de `@mediapipe/tasks-vision`, que este repo consume como
  dependencia.

---

## Con qué se conecta

- **Es la misma idea que…** la cola de registros sin conexión: los dos mueven trabajo al
  cliente porque la red no está garantizada ([C-02](C-02-offline-first-cola.md)).
- **Existe por culpa de…** el GIL de Python: procesar video en el servidor sería
  exactamente el trabajo de cálculo puro que este backend no puede pagar
  ([A0-10](A0-10-python-del-lado-del-servidor.md)).
- **Es el mismo problema que…** el bucle de eventos del navegador: el conteo, el dibujo y
  la inferencia comparten un único hilo, y por eso el estado del bucle vive en referencias
  y no en estado de React ([A0-04](A0-04-el-navegador-por-dentro.md)).
- **Existe por culpa de…** el borrado de tipos: `Punto3D` no existe al correr, así que un
  arreglo con menos de 33 puntos revienta en el acceso y no en el compilador
  ([A0-05](A0-05-javascript-y-typescript.md#frontera-de-confianza-del-tipo)).
- **Es la misma idea que…** el cierre: el filtro guarda su historia en variables
  capturadas, sin clase ni estado compartido
  ([A0-05](A0-05-javascript-y-typescript.md#cierre-closure)).
- **Es el mismo problema que…** el canvas del navegador: el esqueleto se pinta encima del
  video sin crear un nodo del DOM por punto
  ([A0-04](A0-04-el-navegador-por-dentro.md#motor-de-render-y-canvas)).

El contador completo —la pantalla, sus modos, la máquina de estados vista como producto y
su relación con el circuito de entrenamiento— se desarrolla en
[C-01](C-01-contador-reps.md), que usa el vocabulario de este capítulo sin volver a
definirlo.
