# A0-01 · Qué pasa cuando corre un programa

> **Piso de este capítulo: la compuerta lógica.** Se la nombra una sola vez, acá, y el
> descenso se detiene ahí. Ningún otro capítulo de la masterclass vuelve a bajar hasta
> este nivel salvo [A0-11](A0-11-criptografia-aplicada.md), que baja otra vez hasta las
> compuertas para mostrar cómo se calcula un hash — usando el vocabulario que fija esta
> página, sin redefinirlo.

Este es el capítulo del fondo. Todo lo demás en OlimpOS —una cookie, una consulta, un
componente de React, un widget de Flutter— termina siendo lo mismo: un procesador
ejecutando instrucciones sobre memoria que alguien le reservó. Explicar eso una vez, acá,
es lo que le permite a los trece capítulos siguientes de la Parte A0 decir "el proceso del
backend" o "el hilo que refresca" sin tener que volver a explicar qué es un proceso o un
hilo.

**Lo que este capítulo define y nadie más vuelve a definir:** proceso y espacio de
direcciones, instrucción de máquina y compuerta lógica, hilo y hilo demonio, intérprete y
bytecode y compilación al vuelo, variable de entorno y archivo `.env`, y la codificación de
un archivo de texto hasta el byte de la marca de orden.

**Lo que este capítulo NO toca**, aunque esté a un paso: cómo dos máquinas se hablan y qué
es un puerto (A0-02), cómo funciona el
[bucle de eventos](A0-04-el-navegador-por-dentro.md#bucle-de-eventos-tarea-y-microtarea-promesa-y-asyncawait)
o qué es el [GIL](A0-10-python-del-lado-del-servidor.md). Acá sólo llegamos hasta la puerta
de cada uno de esos temas y los nombramos.

---

## Proceso y espacio de direcciones

### El problema del que nace

Una computadora, en su forma más pelada, hace una cosa: lee un número de la memoria, lo
interpreta como una orden, la ejecuta, y pasa al número siguiente. No tiene idea de
"programas". No sabe que existen "aplicaciones". Hay memoria, hay un contador que dice qué
dirección leer ahora, y eso es todo.

Con esa máquina desnuda, correr un programa era literalmente cargarlo en memoria a partir
de una dirección fija y apuntar el contador ahí. Funcionaba mientras corriera **un solo
programa a la vez**, que es cómo se usaban las computadoras hasta los años sesenta: uno
entregaba su trabajo, la máquina lo corría entero, y recién ahí tomaba el siguiente.

Dos cosas rompieron ese modelo, y las dos son el origen del proceso:

1. **La máquina se quedaba parada.** Cuando el programa pedía algo lento —una cinta, un
   disco, una impresora— el procesador no tenía nada que hacer y esperaba. Se estaba
   desperdiciando el recurso más caro del edificio. La idea obvia fue tener varios
   programas cargados a la vez y, cuando uno se pone a esperar, darle el procesador a otro.
2. **Un programa podía escribir en la memoria de otro.** Apenas hay dos programas cargados
   simultáneamente, un error de cálculo en una dirección —un índice fuera de rango— pisa
   los datos del vecino. Y no sólo por error: nada impedía leer a propósito lo que el otro
   tenía cargado.

La solución a las dos cosas a la vez es el **proceso**: cada programa en ejecución recibe
del sistema operativo su propio mapa de memoria, su propia cuenta de qué archivos tiene
abiertos, su propio directorio de trabajo, y la ilusión completa de que la máquina es suya.
El mecanismo que hace posible la ilusión es la **memoria virtual**, y su primera
implementación reconocible fue el *one-level store* de la máquina Atlas de Manchester, a
principios de los sesenta: el programa escribe direcciones como si arrancara en cero y
tuviera toda la memoria disponible, y el hardware traduce cada una a la posición real que
le tocó.

Un proceso, entonces, es la respuesta a una pregunta de negocio del sistema operativo: *¿cómo
hago para que varios programas compartan una máquina sin que se pisen ni se espíen?*

> **↓ Capa 2 — qué le da exactamente el sistema operativo al proceso.** Salteable si ya lo sabés.

Lo que el proceso recibe es un **espacio de direcciones**: un rango de números que, para él,
son las direcciones de memoria. Adentro de ese rango hay zonas con roles distintos, y las
cuatro que importan siempre son:

- **El código.** Las instrucciones del programa, cargadas desde el archivo ejecutable.
  Normalmente marcadas como sólo lectura: el proceso puede ejecutarlas, no reescribirlas.
- **Los datos estáticos.** Las constantes y las variables que existen desde el arranque
  hasta el final.
- **La pila.** Donde viven las variables locales de cada llamada a función. Crece cuando se
  entra a una función y se destraba al salir, en orden estricto de último en entrar,
  primero en salir. Por eso una recursión sin fondo termina en un error de pila: no es una
  metáfora, es que ese rango se acabó.
- **El montón.** Donde viven los objetos cuyo tamaño o duración no se sabe al compilar. Un
  diccionario de Python al que se le agregan claves, un arreglo de JavaScript que crece, un
  objeto que una función devuelve y otra sigue usando: todos están acá. Se pide y se
  devuelve explícitamente, o —como en Python y en JavaScript— lo devuelve solo un
  recolector de basura cuando nadie lo apunta más.

> **↓ Capa 3 — por qué ese mapa no se puede violar.** Salteable si ya lo sabés.

La ilusión no la sostiene el sistema operativo revisando cada acceso, porque eso costaría
más que el programa. La sostiene el hardware. El procesador tiene una unidad de gestión de
memoria que traduce cada dirección que el programa usa a una dirección física real, y lo
hace consultando una tabla que el sistema operativo escribió y que el programa no puede
tocar. La traducción está dividida en bloques —páginas, típicamente de 4 KB— y cada entrada
de la tabla dice, además de a dónde va, si esa página se puede leer, escribir o ejecutar.

Si el programa usa una dirección que no tiene entrada, o escribe en una página marcada de
sólo lectura, el hardware no hace la operación: interrumpe. El control salta al sistema
operativo, que decide qué hacer. En el caso normal eso es matar el proceso, y eso es
exactamente lo que se ve en pantalla cuando un programa "se cierra solo" sin mensaje.

Dos consecuencias que van a aparecer en el resto de la masterclass:

- **La memoria de un proceso es inaccesible desde otro.** No hay forma de que el proceso de
  Vite lea una variable del proceso de uvicorn. Si dos procesos tienen que compartir algo,
  tienen que mandárselo: por un archivo, por la red, o por algún canal que el sistema
  operativo provea. No hay atajo.
- **Todo lo que está en el montón muere cuando muere el proceso.** No es una política que
  alguien programó: el sistema operativo desarma el mapa entero y esas páginas se le dan a
  otro. Si un dato tiene que sobrevivir a un reinicio, tiene que estar en un disco o en otra
  máquina.

> **↓ Capa 4 — y qué es una dirección, en última instancia.** Salteable si ya lo sabés.

Una dirección es un número binario en un registro del procesador, y "la memoria" es un
arreglo de celdas que responden a ese número. Poner una dirección en el bus y pedir una
lectura es, físicamente, poner tensión alta o baja en un conjunto de líneas y esperar que
el módulo de memoria conteste con otro conjunto. La abstracción toca el silicio acá: **un
byte de memoria es un estado eléctrico estable, y una dirección es una combinación de bits
que selecciona cuál.** Más abajo está la compuerta lógica, que se nombra en la sección
siguiente y donde el descenso se termina.

### Vuelta al repo: dónde se ve esto en OlimpOS

En OlimpOS hay tres lugares donde una decisión de diseño se apoya *exclusivamente* en que
el montón pertenece al proceso y muere con él.

**El freno de intentos de login.** `backend/limite_intentos.py:41-43` declara tres cosas a
nivel de módulo:

```python
_candado = threading.Lock()
_fallos_por_ip: dict[str, list[float]] = {}
_trabada_hasta: dict[str, float] = {}
```

Esos dos diccionarios son el freno completo: cuántos fallos vio cada IP y hasta cuándo está
trabada cada cuenta. Viven en el montón del proceso de uvicorn. El módulo lo dice en su
propio encabezado (`backend/limite_intentos.py:7`, "Dos mecanismos, en memoria del
proceso") y justifica la elección en `backend/limite_intentos.py:23-26`: no hace falta que
sobreviva a un reinicio, porque un reinicio que destraba cuentas no le sirve a un atacante,
y así no se paga ni una columna más ni una consulta más en cada login. La consecuencia
práctica está documentada en `CLAUDE.md`: una cuenta trabada se destraba desde la pantalla
de Usuarios, reseteando la contraseña **o reiniciando el backend**. Reiniciar el backend
destraba a todos porque mata el proceso, y con él los dos diccionarios. El mecanismo
completo del freno —los cinco fallos, los quince minutos, el 429 por IP y por qué una
cuenta trabada responde igual que una clave equivocada— es de
[A-07](A-07-autenticacion.md#freno-de-intentos-y-respuesta-indistinguible).

**El token de sesión de la app de escritorio.** `Flet/Proyecto/app/api_client.py:45-49`:

```python
# El token de la sesión vive en una variable de módulo y NO se escribe nunca
# en disco: al cerrar la app la sesión se pierde y hay que volver a entrar.
_token: str | None = None
```

Acá la propiedad del proceso *es* la medida de seguridad. La máquina del mostrador es
compartida; que la sesión no sobreviva al cierre de la aplicación no es una limitación que
se toleró, es el comportamiento buscado, y se consigue sin escribir una línea de código de
expiración: alcanza con no persistir nada. El costo es que un cierre accidental obliga a
entrar de nuevo, y eso se aceptó.

**El caché de la app de escritorio.** `Flet/Proyecto/app/api_client.py:225-227` declara
`_cache`, `_refrescando` y su candado, también a nivel de módulo. Lo mismo: cerrar la
aplicación deja el caché en cero, sin código de limpieza. El patrón de caché en sí, sus
treinta segundos de frescura y por qué se invalida entero con cada escritura son de
[A-11](A-11-rendimiento.md#servir-y-refrescar).

---

## Instrucción de máquina y compuerta lógica

### El problema del que nace

Un procesador no entiende `if`, ni `def`, ni `const`. Entiende un repertorio fijo y chico
de operaciones, cada una codificada como un número: sumar dos registros, copiar de memoria
a un registro, comparar dos valores, saltar a otra dirección si la comparación anterior dio
cero. Eso es una **instrucción de máquina**, y es la unidad mínima de "hacer algo" que
existe en toda la pila.

El origen del formato es la idea de programa almacenado, formulada en el borrador del
informe sobre el EDVAC de 1945: las instrucciones se guardan **en la misma memoria que los
datos**. Antes, programar una máquina era recablearla. Después, un programa pasó a ser un
bloque de números indistinguible de cualquier otro bloque de números, y eso es lo que hace
posible todo lo que sigue: un compilador puede *producir* instrucciones porque producir
instrucciones es escribir números en memoria.

> **↓ Capa 2 — qué hace el procesador con una instrucción.** Salteable si ya lo sabés.

El ciclo es siempre el mismo y no cambió conceptualmente en ochenta años:

1. **Buscar.** El contador de programa tiene una dirección. Se lee la memoria en esa
   dirección y se trae el número que hay ahí.
2. **Decodificar.** Ese número se parte en campos: qué operación es, sobre qué registros,
   con qué constante. El repertorio de operaciones y cómo se codifica cada una es lo que
   define una arquitectura, y es por lo que un ejecutable compilado para una familia de
   procesadores no corre en otra.
3. **Ejecutar.** La unidad correspondiente hace la cuenta.
4. **Guardar** el resultado y avanzar el contador.

Un núcleo moderno hace esto con varias instrucciones en vuelo a la vez, en distinto punto
del ciclo, y reordena las que no dependen entre sí. Eso cambia los números pero no el
modelo.

> **↓ Capa 3 — qué es "ejecutar" una suma.** Salteable si ya lo sabés.

Sumar dos registros de 64 bits es una operación combinacional: entran 128 bits y salen 64
más un acarreo, sin que intervenga ningún programa. El circuito que la hace está armado con
**compuertas lógicas**: bloques que toman una o dos entradas eléctricas y producen una
salida según una regla fija —AND da alto sólo si las dos entradas son altas, OR si al menos
una lo es, XOR si son distintas, NOT invierte—.

Un sumador de un bit es un XOR para el resultado y un AND para el acarreo; encadenando
sesenta y cuatro de esos, con el acarreo de cada uno entrando al siguiente, se suma un
registro entero. Cada compuerta, a su vez, es un puñado de transistores, y un transistor es
un interruptor que una tensión abre o cierra.

**Y acá se termina el descenso de toda la masterclass.** El puente entre el álgebra de
Boole y el circuito eléctrico lo estableció Claude Shannon en su tesis de maestría de 1937,
al mostrar que un circuito de relés implementa exactamente una expresión booleana. Desde
ese punto para abajo hay física, y la física no explica ninguna decisión de OlimpOS.

### Vuelta al repo: por qué la CPU nunca es el cuello

El interés práctico de haber bajado hasta acá es que ahora se puede contar. Una instrucción
tarda del orden de un ciclo de reloj, y un procesador de escritorio corre a unos 3 GHz: tres
mil millones de ciclos por segundo.

En `backend/database.py:50-53` están los dos números medidos de este sistema:

```
SELECT 1 en una conexión YA abierta ......  44 ms
Abrir una conexión NUEVA (TLS + auth) .... 825 ms
```

Traducidos a la unidad de este capítulo:

| Espera | Milisegundos | Ciclos de procesador que pasan mientras tanto |
|---|---|---|
| Una consulta sobre una conexión abierta | 44 | ~130.000.000 |
| Abrir una conexión nueva | 825 | ~2.500.000.000 |

Y son un piso, porque un núcleo moderno retira más de una instrucción por ciclo. Ciento
treinta millones de instrucciones es más de lo que gasta el backend entero armando la
respuesta de un listado. Esa es la mitad del argumento de que el cuello de OlimpOS no está
en el procesador: **cualquier cálculo que el backend haga es ruido al lado de una sola
espera de red.** La otra mitad —el reparto medido del tiempo real de un pedido, y las
decisiones de arquitectura que salen de ahí— es de
[A-11](A-11-rendimiento.md#el-cuello-es-la-red-nunca-python).

Hay un detalle que redondea el punto y que se ve en `backend/main.py:93`. El hilo del latido
no se queda contando hasta ciento veinte segundos:

```python
while not _latido_activo.wait(SEGUNDOS_ENTRE_LATIDOS):
```

`wait()` bloquea. Durante esos dos minutos el hilo no ejecuta **ni una** instrucción: el
sistema operativo lo saca de la lista de ejecutables y el procesador se dedica a otra cosa.
Esperar, en una computadora, es gratis en instrucciones. Calcular no. Toda la sección de
rendimiento de este sistema sale de esa asimetría.

---

## Hilo (y hilo demonio)

### El problema del que nace

El proceso resolvió el aislamiento, y el aislamiento tiene un precio: dos procesos no
comparten memoria, así que para que colaboren hay que copiar datos de uno a otro y
coordinarlos. Cuando lo que hace falta es que **el mismo programa** haga dos cosas a la vez
—atender un pedido mientras otro espera al disco—, pagar el aislamiento entre las dos
mitades es absurdo: son el mismo programa, quieren ver los mismos datos.

De ahí sale el **hilo**: una línea de ejecución más adentro del mismo proceso, con su
propia pila y su propio juego de registros, pero **compartiendo el espacio de direcciones**
con las demás. Dos hilos del mismo proceso ven el mismo montón, los mismos objetos, las
mismas variables de módulo. Eso es lo que los hace baratos y lo que los hace peligrosos.

> **↓ Capa 2 — qué es cambiar de hilo.** Salteable si ya lo sabés.

El procesador tiene un solo contador de programa y un solo juego de registros por núcleo. Un
hilo *es*, desde el punto de vista del hardware, un valor para cada uno de esos registros
más un puntero a su pila. Cambiar de hilo es guardar todos esos valores en memoria y cargar
los del otro. El sistema operativo lo hace cuando el hilo se bloquea esperando algo, o
cuando se le acaba el turno que le tocó.

De ahí sale la propiedad incómoda: **el cambio puede ocurrir en cualquier instrucción**,
incluso en el medio de algo que en el código fuente parece una sola operación. `contador +=
1` son tres pasos —leer, sumar, escribir—, y si dos hilos los intercalan, una de las dos
sumas se pierde. La operación que en el código se ve atómica no lo es en instrucciones.

La respuesta a eso es el **candado**: un objeto que sólo un hilo puede tener a la vez; el
que lo pide mientras otro lo tiene queda bloqueado hasta que se libere. No hace que la
operación sea atómica: hace que nadie más pueda estar adentro mientras dura.

> **↓ Capa 3 — el hilo demonio.** Salteable si ya lo sabés.

Normalmente un proceso no termina hasta que terminan todos sus hilos, porque terminar con
un hilo a medias dejaría trabajo cortado. Pero hay hilos cuyo trabajo *nunca* termina por
diseño: un bucle que cada dos minutos hace algo, para siempre. Si el proceso esperara a ese
hilo, no se apagaría nunca.

Un **hilo demonio** es un hilo marcado como "no cuentes conmigo para decidir si el proceso
sigue vivo". Cuando los hilos normales terminan, el proceso termina y el demonio muere donde
esté, sin avisar y sin oportunidad de limpiar. Es la marca correcta para trabajo de fondo
descartable, y la incorrecta para cualquier cosa que tenga que quedar consistente.

### Vuelta al repo: dónde hay hilos en OlimpOS

**El backend tiene muchos más hilos de los que parece.** En `backend/routers/` hay **165
decoradores `@router.<método>`**, uno por operación de la API, y de todas las funciones que
esas líneas decoran **una sola** está declarada con `async def`:
`backend/routers/pagos_online.py:294`, `webhook_mercadopago`. Todas las demás son `def` a
secas. Esa proporción no es un descuido: es una decisión con consecuencias directas en este
capítulo.

*(165 operaciones no es lo mismo que 165 direcciones: una misma dirección atendida con `GET`
y con `PUT` son dos operaciones y un solo camino, que es lo que cuenta el chequeo de rutas
publicadas de `CLAUDE.md`.)*

Cuando FastAPI recibe un pedido, mira cómo está declarada la función que lo atiende. En
`backend/.venv/Lib/site-packages/fastapi/routing.py:211-214`:

```python
if is_coroutine:
    return await dependant.call(**values)
else:
    return await run_in_threadpool(dependant.call, **values)
```

Es decir: los endpoints declarados con `def` —o sea, todos menos el del webhook— **no
corren en el hilo principal**. Cada uno se despacha a un hilo de un conjunto reservado
(`backend/.venv/Lib/site-packages/starlette/concurrency.py:35-37`, que delega en
`anyio.to_thread.run_sync`), y ese conjunto admite hasta cuarenta hilos simultáneos por
omisión (`backend/.venv/Lib/site-packages/anyio/_backends/_asyncio.py:3093-3099`,
`CapacityLimiter(40)`). El motivo de la elección —que el acceso a la base en este sistema es
síncrono y bloquearía el hilo único si corriera ahí— es de
[A0-10](A0-10-python-del-lado-del-servidor.md#corrutina).

Lo que importa acá es la consecuencia: hasta cuarenta hilos tocando **los mismos
diccionarios del montón**. Por eso `backend/limite_intentos.py:41` declara un candado, y
por eso cada una de sus cinco funciones públicas hace su trabajo adentro de un bloque
`with _candado:` (`backend/limite_intentos.py:46-83`). Sin ese candado, dos logins fallidos
simultáneos podrían perder uno de los dos registros, y el freno contaría de menos.

**Los hilos demonio del sistema son tres**, y los tres siguen la misma lógica.

| Dónde | Línea | Qué hace | Por qué demonio |
|---|---|---|---|
| Backend | `backend/main.py:149` | `threading.Thread(target=_latido, name="latido-neon", daemon=True).start()` | Su bucle no termina nunca (`backend/main.py:93`); si no fuera demonio, uvicorn no podría apagarse. |
| Flet | `Flet/Proyecto/app/api_client.py:295-300` | Refresca por detrás una entrada de caché vencida | Si la persona cierra la aplicación en el medio, ese refresco no importa. |
| Flet | `Flet/Proyecto/app/api_client.py:358-363` | Precarga rutas después del login | Ídem: su resultado es una comodidad, no un compromiso. |

El comentario de `backend/main.py:78-84` explica la elección con precisión y conviene
leerlo, porque es la misma disyuntiva que aparece en todo servidor: el latido usa acceso
síncrono a la base, meterlo en el hilo principal bloquearía la atención de pedidos durante
los 44 ms de cada consulta, y un hilo demonio "no molesta a nadie y muere solo cuando el
proceso termina, sin necesidad de cancelarlo".

Con un matiz que el propio código corrige: en `backend/main.py:194`, al apagar, se hace
`_latido_activo.set()`. Ser demonio garantiza que el hilo no impida el apagado, pero no que
se apague *ordenadamente*; poner ese evento hace que el `wait()` de la línea 93 devuelva
inmediatamente y el bucle salga solo, en vez de quedar consultando la base mientras uvicorn
cierra. Es la diferencia entre "no me va a trabar" y "ya terminó".

---

## Intérprete, bytecode y compilación al vuelo

### El problema del que nace

Las instrucciones de máquina son específicas de una familia de procesadores y de un sistema
operativo. Un programa compilado a instrucciones nativas es rápido y es intransferible:
hay que compilarlo de nuevo para cada combinación en la que quiera correr.

Durante décadas se convivió con eso. La salida apareció cuando se aceptó un intercambio:
compilar no a instrucciones de la máquina real, sino a instrucciones de una **máquina
inventada**, sencilla y siempre igual. Ese código intermedio —bytecode— no lo ejecuta nadie
directamente; lo lee un programa, el **intérprete**, que por cada instrucción del código
intermedio ejecuta el puñado de instrucciones nativas que le corresponden. El programa pasa
a ser portable al costo de ser más lento. La jugada es vieja: el sistema p de UCSD Pascal la
usaba en los setenta, y la máquina virtual de Java la volvió masiva en los noventa.

El costo se volvió a atacar con la **compilación al vuelo**: mientras el programa corre, el
motor mide qué partes se ejecutan muchas veces y esas —sólo esas— las traduce a
instrucciones nativas de verdad, aprovechando que ya sabe con qué tipos de datos se las
llamó. El código caliente termina corriendo a velocidad nativa; el que se ejecuta una vez
no se paga compilarlo. La técnica viene de la investigación sobre el lenguaje Self en los
ochenta y noventa, y de ahí pasó a los motores de Java y, después, a los de JavaScript.

En OlimpOS conviven las dos variantes: **Python interpreta bytecode sin compilarlo a
nativo**, y el navegador que corre la PWA sí compila al vuelo. Cómo lo hace ese motor en
particular es de [A0-05](A0-05-javascript-y-typescript.md#motor-de-javascript); acá se
define el mecanismo general y se muestra el bytecode, que se puede abrir y mirar.

> **↓ Capa 2 — el bytecode existe como archivo, y se puede leer.** Salteable si ya lo sabés.

Cuando Python importa un módulo, lo compila a bytecode y **guarda el resultado en disco**
para no repetir la compilación la próxima vez. El repo está lleno de esos archivos: una
carpeta `__pycache__` al lado de cada paquete.

Tomemos el del punto de entrada del backend, `backend/__pycache__/main.cpython-311.pyc`.
Sus primeros dieciséis bytes son:

```
a7 0d 0d 0a   00 00 00 00   f8 12 ab 6a   2a 36 00 00
```

Cada campo se puede leer:

- `a7 0d` — el número mágico, 0x0DA7 = 3495, que identifica la versión del formato de
  bytecode. Es de CPython 3.11, que es lo que dice el nombre del archivo. Si se abre este
  archivo con otra versión de Python, el número no coincide y se recompila: por eso
  actualizar el intérprete nunca deja bytecode viejo corriendo.
- `0d 0a` — retorno de carro y salto de línea, puestos a propósito para que el archivo se
  arruine de forma detectable si alguien lo copia en modo texto.
- `00 00 00 00` — banderas. En cero significa que la validez se decide por fecha, no por
  hash del fuente.
- `f8 12 ab 6a` — la fecha de modificación del archivo `.py` cuando se compiló.
- `2a 36 00 00` — el tamaño del fuente: 0x362a = **13.866 bytes**, que es exactamente lo que
  mide `backend/main.py`.

Esos dos últimos campos son el mecanismo completo de invalidación: al importar, Python
compara la fecha y el tamaño del `.py` con lo que dice el encabezado del `.pyc`; si
coinciden, usa el bytecode guardado, y si no, recompila. Después de los dieciséis bytes de
encabezado viene el objeto de código serializado: las instrucciones de la máquina virtual
de Python, las constantes y los nombres.

### Vuelta al repo: compilar no es ejecutar, y ya costó

Que compilar y ejecutar sean dos pasos distintos tiene una consecuencia práctica que
`CLAUDE.md` anota como trampa aprendida, en la sección de verificación:

> `compileall` no ejecuta: un nombre sin importar pasa. `-c "import main"` + el chequeo AST
> de nombres cargados contra ligados.

Es exactamente lo que este capítulo predice. `python -m compileall -q app main.py` —el
comando que `CLAUDE.md` da para la app de escritorio— hace una sola cosa: parsear el fuente
y escribir el bytecode. Comprueba que el archivo es Python **sintácticamente válido**. No
comprueba que los nombres que usa existan, porque en Python el nombre se resuelve recién
cuando la instrucción se ejecuta: usar `datetime` sin haberlo importado compila
perfectamente y revienta la primera vez que esa línea corre, que puede ser dentro de un mes
y en el mostrador.

Por eso la verificación real del backend es `.venv/Scripts/python.exe -c "import main"`:
importar **ejecuta** el módulo de arriba a abajo, y ahí sí se cae si falta un import o si un
nombre no existe al nivel del módulo.

El mismo capítulo explica la otra trampa del arranque, en
`Flet/Proyecto/scripts/lanzar_flet_navegador.py:11-15`. El intérprete, para importar
`flet_web`, busca en una lista de directorios que arma al arrancar y que empieza por la
carpeta del script que se ejecutó. Si ese script se llamara `flet_web.py`, Python
encontraría **el script** antes que el paquete instalado y lo importaría a él. El archivo
lo documenta porque ya pasó. Lo que hace en su lugar es fijar la raíz a mano
(`Flet/Proyecto/scripts/lanzar_flet_navegador.py:30-32`), derivándola de la ubicación del
propio archivo en vez de clavar una ruta, porque el repo vive en `D:` en una máquina y en
`E:` en otra. El resto de lo que hace ese lanzador es de
[C-07](C-07-lanzadores-e-instalador.md).

---

## Variable de entorno y archivo `.env`

### El problema del que nace

Un programa necesita datos que cambian según dónde corra: a qué base conectarse, con qué
clave firmar, qué orígenes aceptar. Poner eso en el código tiene dos problemas que no se
arreglan con disciplina:

1. **Los secretos quedan en el repositorio.** Quien clona el proyecto se lleva la contraseña
   de la base. Quien mira el historial se la lleva aunque después se haya borrado.
2. **Cambiar de entorno obliga a tocar el código.** Pasar de la base de pruebas a la real
   sería una edición y un nuevo despliegue, cuando lo único que cambió es una cadena.

Los argumentos de la línea de comandos no alcanzan: los ve cualquiera que liste los procesos
y hay que pasárselos a cada hijo a mano. La respuesta de Unix —presente ya en la Versión 7,
alrededor de 1979, junto con el intérprete de Bourne— fue darle a cada proceso un tercer
canal de entrada además de los argumentos y los archivos: el **entorno**, un conjunto de
pares nombre-valor que **el proceso hijo hereda automáticamente del padre** cuando se lo
crea.

> **↓ Capa 2 — qué es materialmente el entorno.** Salteable si ya lo sabés.

El entorno es un arreglo de cadenas de la forma `NOMBRE=valor`, copiado dentro del espacio
de direcciones del proceso nuevo en el momento de crearlo. Tres propiedades que se deducen
de ahí y que explican todo lo que sigue:

- **Es una copia, no un vínculo.** Si después de arrancar el hijo el padre cambia una
  variable, el hijo no se entera. Lo que cada proceso tiene es la foto del momento en que
  nació.
- **Es texto y nada más.** No hay enteros, ni booleanos, ni listas. `"true"`, `"1"` y `"si"`
  son tres cadenas distintas y el programa decide qué considera verdadero. Tampoco hay
  campos obligatorios: una variable ausente es indistinguible de una vacía salvo que el
  programa lo chequee.
- **No es una caja fuerte.** Está en la memoria del proceso y el sistema operativo permite
  leerla a quien tenga permiso sobre él. Protege del repositorio y del historial de git, no
  de alguien con acceso a la máquina.

Y una consecuencia de nomenclatura que conviene fijar acá: **un archivo `.env` no es un
mecanismo del sistema operativo.** Es un archivo de texto con líneas `NOMBRE=valor` que
*alguna biblioteca* lee y carga en el entorno del proceso ya arrancado. El sistema operativo
no sabe que existe.

> **↓ Capa 3 — la carga, línea por línea.** Salteable si ya lo sabés.

En el backend la biblioteca es `python-dotenv`, y lo que hace se lee entero en
`backend/.venv/Lib/site-packages/dotenv/main.py:88-101`:

```python
for k, v in self.dict().items():
    if k in os.environ and not self.override:
        continue
    if v is not None:
        os.environ[k] = v
```

Tres cosas quedan claras de esas cuatro líneas, y ninguna es obvia desde afuera:

- El `.env` termina en `os.environ`, que es el entorno **real** del proceso: a partir de esa
  llamada las variables son indistinguibles de las que vinieron heredadas.
- **Una variable ya presente en el entorno gana sobre el archivo**, porque el `continue` de
  la línea 96 salta las que ya están. Si alguien exportó `DATABASE_URL` en su terminal, el
  `.env` del repo se ignora en silencio para esa variable.
- No hay validación de tipos ni de presencia. Si una línea falta, no pasa nada hasta que
  alguien pida el valor.

### Vuelta al repo: los cuatro lugares donde OlimpOS usa el entorno

**1. El backend, que se niega a existir sin la cadena de conexión.**
`backend/database.py:36-44` es el patrón bien hecho:

```python
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Falta la variable DATABASE_URL. Copiá backend/.env.example a ...")
```

Eso corre **al importar el módulo**, no al atender un pedido. Si falta la variable, el
proceso no llega a existir como servidor: muere en el arranque con un mensaje que dice qué
copiar. Es lo opuesto a fallar dentro de tres horas, en el mostrador, con un error de
conexión incomprensible. El motivo de que la cadena esté ahí y no en el código está escrito
en `backend/database.py:6-9`: cuando la base se mude del proveedor remoto a un servidor
local del gimnasio, no cambia ni una línea de ese archivo, cambia una línea del `.env`.

El resto del backend lee el entorno con valores por omisión, que es el otro patrón: `_origenes_cors()`
en `backend/main.py:45-61`, `_DOCS_PUBLICOS` en `backend/main.py:116` y `_HTTPS` en
`backend/main.py:121`. Los tres muestran la propiedad de "es texto y nada más": para decidir
si `COOKIE_SECURE` está activo, la línea 121 tiene que escribir
`.strip().lower() == "true"` a mano, y la 116 acepta cuatro grafías distintas
(`"1"`, `"true"`, `"si"`, `"sí"`) porque no hay ningún tipo que lo resuelva.

**2. El demonio de videos, que hereda el `PATH`.** `backend/demonio_videos.py` es un proceso
aparte: se arranca solo, tiene su propio `load_dotenv()` en la línea 29 y sus propias
variables (`VIDEOS_INTERVALO_MIN` en la 31, `VIDEOS_CANAL_YOUTUBE` en la 35). Lo interesante
es la línea 133:

```python
if shutil.which("ffmpeg") is None:
    print("AVISO: ffmpeg no está en el PATH; los videos pueden no descargarse.")
```

`PATH` es la variable de entorno más vieja del oficio: la lista de directorios donde buscar
un ejecutable cuando se lo nombra sin ruta. `which` la recorre. Y el aviso es un aviso, no
un error: el proceso arranca igual y reintenta en la pasada siguiente. Ese proceso completo
es de [C-08](C-08-demonio-videos.md).

**3. Vite, que lee el entorno en dos momentos distintos.**
`Proyecto - PWA/src/frontend/vite.config.ts:11-12` y `:17`:

```ts
const destinoApi = loadEnv(mode, process.cwd(), '').API_PROXY_DESTINO
  ?? 'http://127.0.0.1:8000'
const httpsLan = process.env.VITE_HTTPS === '1'
```

Las dos líneas corren en el proceso de Node que arranca el servidor de desarrollo, y las dos
leen el entorno de ese proceso. La segunda es la que `CLAUDE.md` documenta como
`VITE_HTTPS=1 npm run dev` para probar en el celular: una variable puesta delante del
comando entra en el entorno de ese proceso y de ningún otro.

**4. La PWA, donde la variable de entorno no existe en tiempo de ejecución.** Y este es el
caso que justifica haber definido el concepto con precisión, porque parece lo mismo y es
otra cosa. `Proyecto - PWA/src/frontend/src/services/api.ts:56`:

```ts
const API_URL = import.meta.env.VITE_API_URL ?? '/api';
```

El código de la PWA **no corre en ningún proceso que tenga ese entorno**: corre en el
navegador de la persona, en otra máquina. No hay `.env` que leer ni entorno que heredar. Lo
que ocurre es que el empaquetador, al construir, **reemplaza el texto
`import.meta.env.VITE_API_URL` por el valor, como si alguien lo hubiera tipeado ahí**.

Se puede comprobar en el paquete ya construido, `Proyecto - PWA/src/frontend/dist/assets/index-3ZEPFFtl.js`
(633.775 bytes). Buscar `import.meta.env` da **cero** resultados; buscar `VITE_API_URL` da
**cero**. Lo que quedó es:

```js
var Qn=`/api`,$n=`olimpos_csrf`,er=`X-CSRF-Token`;
```

La expresión entera —la lectura de la variable, el operador de valor por omisión y las dos
alternativas— colapsó en una constante. El nombre de la variable de entorno no sobrevivió al
paso de construcción. De ahí sale la regla que `CLAUDE.md` fija para este repo: el `.env` del
frontend **nunca lleva nada privado**, porque cualquier cosa que se ponga ahí termina
escrita, en claro, en un archivo que se le descarga a cualquiera que abra la página. Y de ahí
sale también que ese `.env` sea opcional: el valor por omisión `/api` está en el código y
alcanza. El mecanismo de construcción es de
[A0-05](A0-05-javascript-y-typescript.md#empaquetador-y-servidor-de-desarrollo).

> **⚠ Discrepancia entre un comentario y el código, documentada y no corregida.** El archivo
> `Proyecto - PWA/src/frontend/.env` dice en su comentario que "si falta, api.ts cae en
> `http://127.0.0.1:8000`". Eso describe una versión anterior: `api.ts:56` cae hoy en
> `/api`, y el comentario de `api.ts:45-55` narra el cambio y la fecha del incidente que lo
> motivó. Gana el código. Se anota acá porque es, en sí misma, la ilustración del problema:
> un valor de configuración escrito en dos lados se desincroniza sin que nada falle.

---

## Codificación: de caracteres a bytes, y el intérprete que adivina mal

### El problema del que nace

Un archivo no contiene letras. Contiene bytes. Que el byte `0x41` se lea como `A` es un
acuerdo, y durante mucho tiempo hubo un acuerdo distinto por región. ASCII definió 128
caracteres en 7 bits —suficiente para el inglés, sin `ñ`, sin `á`, sin `¿`— y el octavo bit
quedó libre; cada país lo llenó con su propia tabla. El mismo byte `0xF3` era una letra
distinta según quién abriera el archivo.

UTF-8, propuesto por Ken Thompson y Rob Pike en 1992, terminó con eso de la única manera que
podía funcionar: un largo variable, de uno a cuatro bytes por carácter, donde los 128
caracteres de ASCII siguen ocupando **exactamente un byte y el mismo de siempre**. Un archivo
en inglés puro es idéntico en ASCII y en UTF-8, y por eso se pudo adoptar sin romper nada.

> **↓ Capa 2 — el byte, y la marca que dice en qué idioma están los bytes.** Salteable si ya lo sabés.

La letra `ó` es el punto de código U+00F3. En UTF-8 se escribe con dos bytes: `C3 B3`. Si un
programa lee ese archivo suponiendo una tabla de un byte por carácter de las viejas, no ve
`ó`: ve dos caracteres, `Ã` y `³`. Nada falla, nada avisa; el texto simplemente queda mal, y
si esos bytes estaban adentro de una palabra clave del lenguaje, el programa ni siquiera
parsea.

Para que el lector no tenga que adivinar se usa la **marca de orden de bytes**: los tres
bytes `EF BB BF` al principio del archivo. El nombre viene de UTF-16, donde efectivamente
indicaba en qué orden venían los pares de bytes. En UTF-8 no hay ningún orden que marcar y la
marca es pura señal: *esto está en UTF-8*. Es exactamente lo que necesita un intérprete que,
si no, adivina por omisión.

### Vuelta al repo: el instalador empieza con tres bytes que no se ven

`CLAUDE.md` lo anota como trampa ya pagada: *"un `.ps1` con acentos tiene que guardarse en
UTF-8 **con BOM** o PowerShell 5.1 lo lee como ANSI y ni siquiera parsea."*

Se puede verificar. Los primeros bytes de `instalar.ps1`:

```
ef bb bf   3c 23 0a   ...
```

`EF BB BF` es la marca; recién después viene `3c 23` = `<#`, que es como PowerShell abre un
bloque de comentario. El archivo tiene acentos desde la tercera línea ("deja OlimpOS listo
para correr en una máquina nueva"), y el mecanismo del fallo es el que se describió arriba:
Windows PowerShell 5.1, sin la marca, supone la tabla local de un byte por carácter, lee
`C3 A1` como dos caracteres raros en vez de `á`, y el análisis del guion se rompe antes de
ejecutar una sola línea. No es que el instalador funcione mal: no arranca.

La simetría vale la pena: el propio instalador, cuando escribe el `.env` del backend, es
explícito sobre la codificación en `instalar.ps1:301`
(`Set-Content ... -Encoding UTF8 -NoNewline`), porque el archivo que produce lo va a leer
después la biblioteca de Python de la sección anterior, que espera UTF-8. Lo que hace
funcionar a los dos programas es que se pusieron de acuerdo sobre el significado de los
bytes; el resto del instalador es de [C-07](C-07-lanzadores-e-instalador.md).

---

## Los tres procesos que corren en esta máquina

Cerramos donde empezamos, pero con el vocabulario puesto. Desarrollar OlimpOS es tener tres
procesos arriba al mismo tiempo. Los comandos son los de `CLAUDE.md`:

| Proceso | Cómo se arranca | Qué es realmente | Qué muere con él |
|---|---|---|---|
| **Backend** | `.venv/Scripts/python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000` | Un proceso de Python que interpreta el bytecode de `backend/main.py` y de todo lo que importa | Los diccionarios del freno de intentos, las conexiones abiertas a la base, el hilo del latido |
| **Servidor de la PWA** | `npm run dev` (`Proyecto - PWA/src/frontend/package.json:7`, `"dev": "vite"`) | Un proceso de Node que compila los módulos a pedido y reenvía `/api` al backend | El grafo de módulos en memoria y el reenvío |
| **Escritorio** | ejecutar `Flet/Proyecto/main.py`, que llama a `ft.run(main, assets_dir="assets")` en la línea 64 | Un proceso de Python que maneja por mensajes a un cliente gráfico aparte | El token de sesión, el caché, los hilos de refresco |

Y un cuarto que **no** corre en esta máquina: `backend/demonio_videos.py`, cuyo bucle
infinito está en las líneas 141-143 y que vive en el servidor de archivos.

Hay una observación de este capítulo que ningún otro va a hacer, porque sólo se ve a nivel
de proceso: **en dos de los tres casos, el código que la persona usa no corre en el proceso
que se arrancó.**

- El proceso de Vite **no ejecuta la PWA**. Le entrega archivos a un navegador, y el
  navegador —un cuarto proceso, en la máquina de la persona o en su teléfono— es el que los
  ejecuta. Apagar Vite no detiene una pestaña ya cargada; sólo impide cargarla de nuevo. Lo
  que ese navegador hace con los archivos es de
  [A0-04](A0-04-el-navegador-por-dentro.md).
- El proceso de Python de Flet **no dibuja la ventana**. Maneja por mensajes a un cliente
  gráfico que es otro programa. El código Python no corre adentro de la interfaz, y por eso
  cada cosa que se cambia en pantalla hay que mandarla explícitamente. El mecanismo del
  puente Python ↔ Flutter es de [A0-13](A0-13-flutter-y-flet.md).

Sólo el backend ejecuta su propia lógica en su propio espacio de direcciones. Esa asimetría
explica por qué las verificaciones de las tres capas son tan distintas entre sí: al backend
se lo verifica importándolo, a la PWA compilándola, y a la app de escritorio hay que
**construirle las vistas** (`Flet/Proyecto/pruebas_vistas.py`) porque compilar su Python no
prueba que la interfaz del otro lado del puente se arme.

Y la última: el proceso es **la unidad de reinicio**. Cambiar una línea de `backend/main.py`
no cambia nada en el proceso que ya está corriendo, porque ese proceso tiene el bytecode
cargado en su montón desde que arrancó. Hay que matarlo y arrancar otro. `CLAUDE.md` lo
anota con su consecuencia más molesta —si el puerto sigue tomado, el proceso nuevo muere en
silencio y sigue respondiendo el viejo—, y da la forma de detectarlo: contar las rutas que
publica `/openapi.json`. Por qué dos procesos no pueden escuchar el mismo número es de
[A0-02](A0-02-como-se-comunican-dos-maquinas.md#puerto).

---

## Con qué se conecta

- **Es la misma idea que…** el hilo demonio del latido y los hilos demonio que refrescan el
  caché de la app de escritorio: trabajo de fondo descartable que no puede impedir que el
  proceso termine ([A-11](A-11-rendimiento.md#servir-y-refrescar)).
- **Existe por culpa de…** el candado de `backend/limite_intentos.py:41` existe únicamente
  porque los hilos comparten el montón del proceso, y el backend atiende con hasta cuarenta
  ([A0-10](A0-10-python-del-lado-del-servidor.md#corrutina)).
- **Es el mismo problema que…** el bytecode de Python y el borrado de tipos de TypeScript:
  las dos son verificaciones que pasan sin que se ejecute una sola línea, y por eso ninguna
  de las dos alcanza ([A0-05](A0-05-javascript-y-typescript.md#tipado-estático-y-borrado-de-tipos)).
- **Existe por culpa de…** la variable de entorno de la PWA desaparece en la construcción, y
  por eso su `.env` nunca puede llevar un secreto y el del backend sí
  ([A0-11](A0-11-criptografia-aplicada.md#clave-secreta)).
- **Es el mismo problema que…** los 130 millones de ciclos que pasan durante cada consulta a
  la base: medidos en instrucciones, vuelven irrelevante optimizar cálculo
  ([A-11](A-11-rendimiento.md#el-cuello-es-la-red-nunca-python)).
- **Se contradice con…** lo mismo que aísla la memoria del backend de todo lo demás es lo que
  obliga a matarlo entero para que tome una línea nueva
  ([A0-10](A0-10-python-del-lado-del-servidor.md#asgi-uvicorn-y-el-router)).
