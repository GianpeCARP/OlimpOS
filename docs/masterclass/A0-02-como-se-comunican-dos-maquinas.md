# A0-02 · Cómo se comunican dos máquinas

**Piso de este capítulo: el paquete viajando por el medio físico** — la trama que sale
del cable o de la antena, con sus bytes contados, y el momento exacto en que el receptor
la descarta sin avisarle a nadie. Más abajo hay física, y la física no explica nada de
OlimpOS.

Este capítulo explica cómo dos programas que no comparten nada logran ponerse de acuerdo
sobre una secuencia de bytes. **Qué dicen esos bytes no es tema de acá**: el idioma que
hablan encima de todo esto es HTTP, y lo explica el capítulo siguiente
([A0-03](A0-03-http.md)).

---

## El problema de origen: dos procesos que no comparten memoria

Un [proceso](A0-01-como-corre-un-programa.md#proceso-y-espacio-de-direcciones) vive
adentro de su propio mapa de direcciones y el sistema operativo no lo deja leer el mapa
de al lado. Esa es la regla incluso entre dos procesos de la misma máquina: el backend de
OlimpOS y la app de escritorio corren a un metro de distancia, en la misma PC del
mostrador, y no tienen una sola posición de memoria en común.

Entre dos máquinas distintas el problema es peor, porque no hay siquiera una memoria que
prohibir. Lo único que existe entre ellas es un medio físico —un cable de cobre, una
fibra, una radio— capaz de transportar **bits, y nada más**. Todo lo que dos programas
quieran compartir tiene que poder escribirse como una tira de bytes, salir por ese medio y
reconstruirse del otro lado.

El primer intento serio de resolver esto copió el teléfono: **conmutación de circuitos**,
es decir, reservar un camino físico completo entre los dos extremos y usarlo en exclusiva
mientras dure la conversación. Funciona para voz y es un desperdicio absurdo para datos,
porque dos computadoras hablan a ráfagas: mandan un golpe de bytes y se quedan calladas
minutos. Entre 1960 y 1966, Paul Baran en la RAND y Donald Davies en el NPL británico
llegaron por caminos distintos a la misma idea opuesta —Davies le puso el nombre
*packet*—: **partir el mensaje en pedazos, ponerle a cada pedazo la dirección de destino y
soltarlo a la red**, sin reservar nada. Cada pedazo se arregla solo. Si hay que compartir
el camino con otros, se comparte; si un pedazo se pierde, se pierde.

ARPANET puso eso a andar en 1969, y en 1974 Vinton Cerf y Robert Kahn publicaron el
protocolo que permitía que redes distintas se conectaran entre sí. En 1978 ese protocolo
único se partió en dos —IP por un lado, TCP por otro— por un motivo que va a importar en
este capítulo: **no todo el mundo necesita las garantías caras**, y quien no las necesita
no tiene por qué pagarlas. El 1 de enero de 1983 ARPANET migró a esa familia de dos
protocolos de un día para el otro, y es la que sigue moviendo cada byte que este repo
manda o recibe.

Bajemos.

---

## Paquete, dirección IP y DNS

> **↓ Capa 1 — qué es exactamente un paquete.** Salteable si ya sabés qué lleva escrito un
> datagrama IP.

Un **paquete** (o datagrama IP) es una tira de bytes con dos partes: una **cabecera** con
los datos del envío y un **cuerpo** con lo que se quiso mandar. La cabecera de IPv4 mide
20 bytes en su forma habitual y lo que importa de ella es esto:

| Campo | Tamaño | Para qué |
|---|---|---|
| Versión | 4 bits | `4` para IPv4, `6` para IPv6. |
| Largo total | 16 bits | Cuántos bytes mide el paquete entero, cabecera incluida. |
| Tiempo de vida (TTL) | 8 bits | Un contador que cada máquina intermedia baja en uno; al llegar a cero el paquete se tira. |
| Protocolo | 8 bits | Qué hay adentro del cuerpo: `6` = TCP, `17` = UDP. |
| Dirección de origen | 32 bits | Quién lo manda. |
| Dirección de destino | 32 bits | A quién va. |

Una **dirección IP** (versión 4) es exactamente eso: **un número de 32 bits**. Los cuatro
grupos separados por puntos que uno escribe —`127.0.0.1`, `192.168.0.146`— son una
comodidad para leerlo: cada grupo es un byte, de 0 a 255. No hay nada adentro de esos 32
bits que diga "computadora de Gianluca" ni "servidor de Neon": es una etiqueta numérica
que identifica **una interfaz de red**, no una máquina y mucho menos un programa.

El campo TTL es la única defensa contra un error de configuración que mande un paquete a
dar vueltas para siempre: sin él, un lazo entre dos routers mal configurados llenaría la
red de paquetes inmortales. Con él, el paquete muere después de unos 64 saltos.

Y hay una propiedad que define todo lo que viene después: **IP promete intentarlo, no
lograrlo**. Un paquete puede perderse, puede llegar duplicado, pueden llegar dos en orden
distinto al que salieron, y el que lo mandó no se entera de nada. A esa promesa mínima se
la llama *entrega de mejor esfuerzo*, y no es una limitación técnica que alguien no supo
resolver: es la decisión de diseño que hace que la red sea barata y que cada extremo pague
sólo las garantías que necesita.

> **↓ Capa 2 — cómo llega un paquete a la otra punta.** Salteable si ya sabés qué hace un
> router con una tabla de ruteo.

Nadie conoce el camino completo. Cada máquina por la que pasa el paquete —arrancando por
la que lo emitió— hace siempre lo mismo: mira la **dirección de destino**, la busca en su
tabla de ruteo, y se la pasa al siguiente. La tabla no tiene una fila por destino posible
(serían miles de millones): tiene filas por **rangos**, más una fila final que dice "todo
lo demás, mandáselo a mi router", que es la ruta por omisión de cualquier PC hogareña.

Tres rangos están reservados para redes privadas y no se rutean por internet:
`10.0.0.0/8`, `172.16.0.0/12` y `192.168.0.0/16`. La IP que aparece en el README de este
repo, `192.168.0.146` (`README.md:163`), pertenece al tercero: es la dirección de la PC
del desarrollo **dentro de su Wi-Fi**, y no significa nada afuera de esa casa. Miles de
routers en el mundo tienen a alguien con esa misma dirección.

Que igual se pueda navegar desde una dirección así es mérito de **NAT**: el router de la
casa reescribe la dirección de origen de cada paquete que sale, poniendo la suya pública,
y anota en una tabla a quién le corresponde la respuesta. Esa tabla es la clave de dos
cosas que aparecen más abajo en este mismo capítulo: **una conexión que se queda callada
demasiado tiempo pierde su fila** y deja de existir para el router, y **desde afuera no se
puede iniciar una conversación** contra una IP privada, porque no hay fila que consultar.
Eso último es literalmente lo que documenta `backend/.env.example:125`: la URL donde
Mercado Pago avisa que un pago cambió de estado *no puede* ser una dirección local,
porque el aviso lo origina un servidor de internet y no hay forma de que llegue.

> **↓ Capa 3 — de dónde sale la dirección, si nadie escribe números.** Salteable si ya
> sabés cómo resuelve un nombre el DNS.

Nadie escribe `ep-xxxx…` como número. En este repo, la cadena de conexión a la base
apunta a un **nombre**: `postgresql://usuario:password@ep-xxxx.us-east-2.aws.neon.tech/olimpos?sslmode=require`
(`backend/.env.example:20`). Antes de que salga un solo paquete hacia la base, ese nombre
tiene que convertirse en 32 bits, y ese paso previo es el **DNS**.

El nombre se lee **de derecha a izquierda**, y cada tramo lo resuelve alguien distinto: los
servidores raíz saben quién atiende `.tech`, los de `.tech` saben quién atiende
`neon.tech`, y ese último —el *autoritativo*— sabe la dirección exacta de
`ep-xxxx.us-east-2.aws.neon.tech`. La máquina que pregunta casi nunca hace ese recorrido:
le pregunta a un **resolutor recursivo** (el del proveedor de internet, o uno público) que
lo hace por ella y le devuelve el número ya masticado. Cada respuesta viene con un tiempo
de vida propio y queda guardada, así que la segunda consulta al mismo nombre no cuesta
nada.

Lo importante para este repo es que **resolver un nombre y llegar a la máquina son dos
pasos independientes, y fallan por separado**. El README lo tiene anotado como síntoma
concreto: la dirección del túnel de Cloudflare puede no resolver desde la PC y andar
perfecto desde el celular, porque lo que falla no es la red sino el resolutor del
proveedor (`README.md:170`). Un problema de DNS se ve igual que un servidor caído y no
tiene nada que ver.

También es el paso donde se decide **cuál** de las direcciones de un nombre se usa,
cuando hay más de una. Ese detalle costó una trampa en este repo y tiene su propia sección
más abajo.

> **↓ Capa 4 — el paquete en el cable. Piso del capítulo.** Salteable si ya sabés qué es
> una trama de Ethernet y qué hace el receptor cuando el CRC no da.

Un paquete IP no viaja solo: viaja **adentro** de otra cosa, porque la red física local no
entiende de direcciones IP. En Ethernet, el paquete se mete adentro de una **trama** que
lleva, por delante, un preámbulo de sincronización, la dirección física de destino (6
bytes), la de origen (6 bytes) y dos bytes que dicen qué hay adentro; y por detrás, 4
bytes de **CRC**, un número calculado sobre todo el contenido.

La traducción de "dirección IP del vecino" a "dirección física del vecino" la hace ARP:
un grito a toda la red local preguntando quién tiene tal IP, y la respuesta del que la
tiene. Por eso esta capa **sólo existe entre vecinos**: cada salto del camino desarma la
trama, mira el paquete IP que traía adentro y lo vuelve a envolver en una trama nueva para
el salto siguiente. La dirección IP sobrevive de punta a punta; la dirección física se
descarta y se reescribe en cada tramo.

El tamaño máximo de esa trama es lo que fija cuánto puede medir el paquete: en Ethernet,
1500 bytes de cuerpo. Descontando los 20 de la cabecera IP y los 20 de la cabecera TCP,
quedan **1460 bytes útiles por paquete**. Toda transferencia más grande que eso —la lista
de socios, el modelo de pose de 35 MB— es, físicamente, una sucesión de miles de paquetes
de ese tamaño.

Y abajo del todo, la trama es una señal: en par trenzado, niveles de voltaje que cambian
millones de veces por segundo; en Wi-Fi, una portadora de radio modulada. Bits.

**Acá está el piso, y conviene mirarlo bien, porque explica todo lo que viene después.**
Cuando esa señal se degrada —un cable largo, un microondas prendido al lado del router, un
switch saturado— los bits llegan cambiados. El receptor recalcula el CRC, le da distinto,
y hace lo único que puede hacer: **tira la trama y no le avisa a nadie**. No hay mensaje de
error, no hay reintento, no hay registro. La pérdida, vista desde el que mandó, es
indistinguible del silencio.

---

## TCP y el viaje de ida y vuelta (RTT)

Subimos. El piso nos dejó tres agujeros: los paquetes **se pierden en silencio**, pueden
**llegar desordenados** (dos paquetes pueden tomar caminos distintos y el segundo llegar
antes) y pueden **llegar duplicados** (si alguien retransmitió por las dudas). Un programa
que quiera mandar la lista de socios no puede convivir con eso.

**TCP es el protocolo que compra las tres garantías que IP no da**, y las compra con la
única moneda disponible: *hacer que el otro extremo confirme*. Su idea central es que el
programa no ve paquetes, ve **un chorro de bytes numerados**: cada byte de la conversación
tiene un número de orden, y la cabecera TCP —20 bytes, también con puerto de origen,
puerto de destino, número de secuencia, número de acuse, banderas y ventana— lleva escrito
desde qué número arranca cada envío.

Con esa numeración, los tres agujeros se tapan solos:

- **Orden.** El receptor guarda en un búfer lo que llega adelantado y no se lo entrega al
  programa hasta tener el tramo que falta. El programa lee siempre en orden, aunque los
  paquetes hayan llegado a los saltos.
- **Duplicados.** Un tramo que ya se recibió llega con números que ya están cubiertos: se
  descarta.
- **Pérdida.** El receptor confirma con un **acuse** (ACK) lo que tiene. El emisor arranca
  un cronómetro por cada envío; si el acuse no llega antes de que suene, **retransmite**.
  El primer plazo arranca alrededor de un segundo y **se duplica en cada reintento**, para
  no empeorar una red que quizás está congestionada justamente porque todos retransmiten.

> **↓ Capa 5 — adentro del saludo de tres pasos.** Este descenso no va hacia el cable: va
> hacia adentro de un mecanismo que ya nombramos. Salteable si ya sabés qué es un SYN.

Todo eso necesita que los dos lados se pongan de acuerdo primero sobre desde qué número
arranca cada uno. Eso es el **saludo de tres pasos** —el *handshake* que nombran los
comentarios de `backend/database.py:57`—, y son tres paquetes:

1. El cliente manda un paquete con la bandera **SYN** y su número inicial.
2. El servidor responde con **SYN + ACK**: acusa el del cliente y manda el suyo.
3. El cliente acusa el del servidor con un **ACK**, y recién ahí puede mandar datos.

Contá los viajes: el primer byte útil sale **después de que un paquete fue y volvió**. Esa
unidad —*lo que tarda algo en ir y que la respuesta vuelva*— es el **viaje de ida y vuelta,
o RTT**, y es la moneda en la que se mide todo lo caro de este sistema. No se puede
negociar: está hecha de distancia. La luz en fibra viaja a unos 200.000 km/s, así que
6.000 km de ida y vuelta ya son 30 milisegundos **antes** de que ningún programa haga
absolutamente nada.

Por eso la pregunta de rendimiento correcta, en un sistema como este, nunca es "cuánto
tarda el código" sino **"cuántos viajes de ida y vuelta hace"**. El repo tiene ese número
medido contra la base, en `backend/database.py:50-58`, y la cuenta completa —qué pasa
cuando el viaje es hasta São Paulo y por qué abrir una conexión nueva cuesta diecinueve
veces más que usar una abierta— es el tema de [A-11](A-11-rendimiento.md#base-remota).

La conexión también se cierra con un diálogo (FIN de cada lado, o un RST que la corta de
golpe), y tiene un tercer estado que suele olvidarse: **el silencio**. Una conexión TCP
abierta y ociosa **no emite un solo paquete**, y eso, que parece gratis, es exactamente lo
que la mata: la fila del NAT del router (capa 2) se vence, o el proveedor de la base
recicla la conexión, y el extremo que no se enteró sigue creyendo que la tiene viva. El
error aparece recién cuando alguien intenta usarla, que es el peor momento posible.

La respuesta de TCP a eso son los **keepalives**: cada tanto manda un paquete sin datos,
cuyo único propósito es forzar un acuse y renovar todas las filas intermedias. Este repo
los tiene prendidos a mano en la conexión a la base, en `backend/database.py:102-112`:

```python
"keepalives": 1,
"keepalives_idle": 30,
"keepalives_interval": 10,
"keepalives_count": 5,
```

Se leen así: después de 30 segundos sin tráfico, mandá un sondeo; si no contesta, repetilo
cada 10 segundos; a los 5 sondeos sin respuesta, dala por muerta. Los cuatro van juntos
—el primero habilita, los otros tres calibran— y el comentario de `database.py:79-83`
nombra con precisión el caso que evitan: una conexión "viva para nosotros y cortada para
el otro extremo". Por qué esa configuración y no otra, y qué tiene que ver con el pool, lo
decide [A-11](A-11-rendimiento.md#pool-de-conexiones); acá sólo importa que el mecanismo
es un paquete vacío pidiendo que le contesten.

Un último detalle que este repo usa sin decirlo: **la dirección IP del que habla no viaja
adentro del mensaje, es una propiedad de la conexión**. El sistema operativo la conoce
porque está en la cabecera de cada paquete que recibe. Por eso, cuando el backend necesita
saber de dónde viene un intento de ingreso, la lee del socket y no del contenido:

```python
def _ip(request: Request) -> str:
    # La del socket y no X-Forwarded-For, que lo escribe el cliente. Ver
    # limite_intentos.py.
    return request.client.host if request.client else "desconocida"
```

`backend/routers/auth_router.py:69-72` · `_ip()`. La diferencia es de fondo: el contenido
lo escribe quien manda y puede mentir; la dirección de origen la impone el camino. El
costo de esa decisión está anotado en `backend/limite_intentos.py:28-31`: detrás de un
intermediario —el proxy del servidor de desarrollo, un nginx en producción— **todos los
pedidos llegan desde la misma dirección**, así que un freno por IP se vuelve grueso y el
que protege de verdad tiene que ser otro. Para qué se usa ese dato, en
[A-07](A-07-autenticacion.md#freno-de-intentos-y-respuesta-indistinguible).

---

## Puerto

Una dirección IP identifica una interfaz de red, y en esa interfaz hay **un solo cable para
muchos programas**. En la PC del desarrollo de OlimpOS, ahora mismo, puede haber tres
procesos esperando pedidos a la vez. Los tres tienen la misma dirección. Hace falta un
segundo número que diga **a cuál de todos** va cada paquete.

Ese número es el **puerto**: 16 bits —de 0 a 65535— que viajan en la cabecera TCP, dos
bytes para el de origen y dos para el de destino. Con eso, el sistema operativo puede
repartir: mira el puerto de destino de cada paquete que entra y se lo entrega al proceso
que se anotó para ese número.

> **↓ Capa 6 — cómo reparte el sistema operativo, exactamente.** Salteable si ya sabés qué
> es un socket de escucha.

La tabla que consulta el núcleo no está indexada por puerto sino por **cinco valores**:
protocolo, dirección local, puerto local, dirección remota y puerto remoto. Una entrada así
—la *quíntupla*— identifica **una conversación**, no un programa. Eso es lo que permite que
un solo backend escuchando en el puerto 8000 atienda a la app de escritorio y a tres
pestañas del navegador al mismo tiempo sin confundirlas: comparten los tres primeros
valores y difieren en los dos últimos, porque **el que inicia la conexión toma un puerto
de origen distinto cada vez**, elegido por su propio sistema operativo de un rango alto
(en Windows, habitualmente de 49152 para arriba).

Un proceso que quiere recibir conexiones hace dos cosas distintas: primero **se ata**
(`bind`) a una dirección local y un puerto, y después **escucha**. Ese socket de escucha es
una entrada especial en la misma tabla, con las dos puntas remotas en blanco: "cualquiera
que llegue a esta dirección y este puerto, es para mí". Y de ahí sale la regla que importa:
**dos procesos no pueden atarse a la misma combinación de dirección y puerto**. El segundo
que lo intenta recibe un rechazo del núcleo —en Windows, el error 10048— y no hay forma de
negociarlo.

Los números por debajo de 1024 están reservados por convención para servicios conocidos, y
el resto es tierra de nadie. Este repo usa cinco puertos, y ninguno de ellos es
casualidad:

| Puerto | Quién escucha | Dónde está escrito |
|---|---|---|
| 8000 | El backend FastAPI | `README.md:128`, `instalar.ps1:383` |
| 5173 | El servidor de desarrollo de la PWA | `README.md:130`, `backend/.env.example:56` |
| 8551 | La app de escritorio servida como página web | `Flet/Proyecto/scripts/lanzar_flet_navegador.py:41` |
| 5432 | PostgreSQL, **implícito**: la cadena de conexión no lo dice | `backend/.env.example:20` |
| 587 / 465 | El servidor de correo saliente | `backend/notificaciones.py:127-136` |

La fila del 5432 muestra qué es exactamente una convención: la cadena
`…neon.tech/olimpos?sslmode=require` **no menciona ningún puerto**, y la conexión llega
igual porque la biblioteca de Postgres completa el 5432 cuando no se lo dan. Nada en la red
obliga a eso; es un acuerdo que todo el mundo respeta.

### Por qué el puerto 8000 ocupado hace que el proceso nuevo muera en silencio

`CLAUDE.md:275-277` lo anota como trampa: *"Si el puerto 8000 está tomado, el proceso nuevo
muere en silencio y responde el viejo. Contar las rutas de `/openapi.json`."* Con el
mecanismo de arriba, se explica entero.

El backend de OlimpOS corre **sin recarga automática** (`CLAUDE.md:275`), así que cambiar
una ruta obliga a matar el proceso y levantarlo de nuevo a mano. Si el anterior no murió
—quedó en otra terminal, quedó colgado cerrando la ventana— sigue atado al 8000. El
proceso nuevo llega, intenta atarse, el núcleo lo rechaza con el 10048, y uvicorn hace lo
único correcto: no puede escuchar, así que termina.

Lo que hace que esto sea traicionero **no es el proceso que muere: es el que sobrevive.**
La verificación natural es abrir `http://127.0.0.1:8000/docs` o pedir `/openapi.json`, y
esa verificación **da bien**, porque hay alguien escuchando en el 8000. Simplemente no es
el que uno levantó. El cambio recién escrito no está, la ruta nueva no existe, y la
pantalla muestra el comportamiento viejo con una consistencia perfecta que lleva a buscar
el error adentro del código. Se suma una segunda trampa que el repo también documenta: si
la salida de uvicorn se redirigió a un archivo, el mensaje de error puede seguir en el
búfer y no estar escrito todavía, así que **ese archivo no prueba nada**
(`CLAUDE.md:278-279`).

**Ingeniería inversa de la respuesta que eligió el repo.** Lo que se estaba optimizando no
era evitar la colisión —no se puede: es una regla del núcleo— sino **detectarla en un
segundo**. La restricción es que "el puerto responde" y "responde el proceso que levanté"
son afirmaciones distintas y se ven iguales. La alternativa obvia, matar por las dudas todo
proceso de Python antes de arrancar, se descartó sola: en esta máquina también corre la app
de escritorio. La que se eligió es pedirle al proceso que responde **una huella que cambia
con el código**: la cantidad de rutas publicadas.

```bash
curl -s http://127.0.0.1:8000/openapi.json | .venv/Scripts/python.exe -c "import json,sys; print(len(json.load(sys.stdin)['paths']))"
```

`CLAUDE.md:341`. El número esperado hoy es 130 (`docs/ESTADO-ACTUAL.md:28`), y si da menos,
contestó el viejo. Se paga con un número más para mantener a mano, que hay que corregir
cada vez que se agrega una ruta. El patrón se llama **verificar la identidad de quien
responde, no sólo que alguien responda**, y aparece igual en cualquier chequeo de salud que
devuelve una versión en vez de un "OK".

---

## Loopback contra IP de la LAN

Toda máquina tiene una interfaz de red que **no está conectada a nada**: el *loopback*. Su
dirección es `127.0.0.1` y funciona como cualquier otra —se le puede mandar paquetes, se
puede escuchar en ella— con una diferencia total: cuando el sistema operativo mira la
tabla de ruteo y ve que el destino cae en `127.0.0.0/8`, no busca ningún camino. Copia el
paquete a la cola de entrada de la misma máquina. **Nunca toca una tarjeta de red, nunca
sale al cable, nunca lo ve nadie.** Todo el rango de 16 millones de direcciones que arranca
en `127.` está reservado para eso.

La IP de la LAN —`192.168.0.146` en el README— es lo contrario: es una interfaz real, la
del Wi-Fi o la del cable, y los paquetes que se le mandan salen de verdad y son visibles
para todo lo que esté en esa red.

Y acá está el punto que hay que tener grabado, porque es de donde salen las dos trampas
que siguen: **atarse a una dirección no es elegir un nombre, es elegir una interfaz**. Un
proceso atado a `127.0.0.1:8000` sólo recibe lo que se originó en su propia máquina. Ese
mismo proceso atado a `0.0.0.0:8000` recibe por **todas** las interfaces. Son dos
configuraciones distintas del mismo programa, y desde afuera la diferencia entre "no está
corriendo" y "está corriendo y no escucha por acá" es exactamente cero.

### Por qué el backend está atado a `127.0.0.1` y qué se paga por eso

Las dos formas de levantar el backend que llevan la dirección escrita —`README.md:128` y
la línea que imprime el instalador al terminar, `instalar.ps1:383`— dicen lo mismo:
`--host 127.0.0.1 --port 8000`. En todo el repo **no hay un solo `0.0.0.0`**, y la única
apertura a la red es condicional, en el servidor de desarrollo de la PWA:

```ts
const httpsLan = process.env.VITE_HTTPS === '1'
…
host: httpsLan ? true : undefined,
```

`Proyecto - PWA/src/frontend/vite.config.ts:17` y `:53`. El comentario de la línea 51
explica el efecto: con esa variable prendida "se expone en la LAN". Sin ella, el servidor
de desarrollo tampoco sale de la máquina.

> **Discrepancia anotada, no corregida.** El encabezado de `backend/main.py:10` muestra el
> arranque como `uvicorn main:app --reload`, sin dirección ni puerto, mientras
> `CLAUDE.md:275` establece que el backend **corre sin `--reload`**. Las dos cosas terminan
> en el mismo lugar por omisión —uvicorn, cuando no le dan nada, se ata a `127.0.0.1:8000`—
> pero el comando del encabezado no es el que el proyecto usa. Gana el código y la regla
> del dueño: sin recarga automática, con la dirección y el puerto escritos.

Lo que se estaba optimizando es **superficie**: el backend tiene toda la información del
gimnasio y, atado al loopback, no existe para nadie más que para los programas de esa PC.
La restricción es que el gimnasio comparte Wi-Fi con quien esté adentro. La alternativa
—abrirlo con `0.0.0.0` para que el celular le pegue directo— se descarta por dos motivos
que se suman: cualquiera en esa red llegaría a la API, y además la sesión de la PWA dejaría
de cumplir la condición de "mismo sitio" que exigen la cookie y el proxy de desarrollo
(→ [A0-12](A0-12-sesiones-y-autenticacion.md#cookie-y-sus-atributos),
[A-04](A-04-recorrido-de-un-pedido.md#proxy-api-de-vite)). Lo que se paga es concreto:
**probar en el celular deja de ser directo** y pasa a necesitar una cadena de intermediarios
—y con ella, la trampa que sigue—. El patrón se llama **atar el servicio a la interfaz más
chica que alcance**.

### La trampa del túnel: por qué `localhost` no sirve ahí

Para probar la PWA en un teléfono, el README arma esta cadena (`README.md:158-166`):

```bash
cloudflared tunnel --url https://192.168.0.146:5173 --no-tls-verify
```

`cloudflared` es un programa que corre **en la misma PC**, abre una conexión saliente hacia
la red de Cloudflare, consigue un nombre público `…trycloudflare.com` y, por cada pedido
que le llega a ese nombre, abre una conexión local contra lo que diga `--url`. El truco es
que la conexión hacia afuera **la inicia la PC**, que es lo único que el NAT y el firewall
dejan pasar sin configurar nada.

El README es explícito en la línea 169: **va la IP de la red, no `localhost`**, y contra
`localhost` la respuesta es 502. Ese número dice algo preciso: el problema no está entre el
celular y Cloudflare —esa parte anduvo— sino en **el último salto, el que va de
`cloudflared` al servidor de desarrollo**, que es el único que ocurre dentro de la PC. El
intermediario no pudo conectarse a lo que le dieron.

Y no pudo porque `localhost` **no es una dirección: es un nombre**, y nombres y direcciones
se resuelven por separado (capa 3). El repo tiene documentada, en otro archivo y por otro
motivo, exactamente esa forma de fallar:

```python
# 127.0.0.1 y no localhost: en Windows, "localhost" puede resolver primero a
# ::1 (IPv6) mientras uvicorn escucha en IPv4, y la conexión falla con un
# timeout confuso que parece un backend caído.
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
```

`Flet/Proyecto/app/api_client.py:35-38` · `API_URL`. El nombre `localhost` tiene **dos**
direcciones —`127.0.0.1` y `::1`, la de IPv6— y quien resuelve elige una. Si el proceso
que escucha se ató a la otra, la conexión no encuentra a nadie. La app de escritorio lo
resolvió de la única forma que no depende de quién resuelva: **escribiendo el número**.

Las dos trampas son la misma lección con dos caras. Una dice que el nombre puede llevarte a
una interfaz donde no hay nadie escuchando; la otra, que la interfaz donde sí hay alguien
escuchando puede no ser la que el nombre nombra. En los dos casos la regla práctica es la
misma: **apuntá a la dirección que el servidor imprimió cuando arrancó**, no a un sinónimo.

Hay un tercer caso en el repo que cierra el concepto desde el lado opuesto, y está en dos
líneas seguidas de `backend/.env.example`. La URL del aviso de pago **no puede** ser local
(`:125`), porque la llama un servidor de internet. La URL de retorno del socio **sí puede**
serlo (`:131-133`), porque la abre el navegador del propio socio, que está en la misma
máquina. Misma dirección, dos veredictos opuestos, y la diferencia es una sola pregunta:
**quién origina la conexión**.

Un detalle final que parece redundante y no lo es: `backend/.env.example:56` declara los
orígenes permitidos como `http://localhost:5173,http://127.0.0.1:5173`. Los dos son la
misma máquina y el mismo proceso; están los dos porque, para el navegador, **son dos sitios
distintos** y la comparación es textual (→ [A0-04](A0-04-el-navegador-por-dentro.md#origen-y-política-del-mismo-origen),
[A0-12](A0-12-sesiones-y-autenticacion.md#cors-y-preflight)).

---

## TLS

Todo lo anterior deja un agujero enorme, y se ve mejor desde la capa 2: **el paquete pasa
por máquinas ajenas**. El router de la casa, el del proveedor, media docena de equipos
intermedios y el proveedor del otro extremo ven cada byte tal cual salió. Con TCP solo, la
contraseña de la base de datos de OlimpOS viaja legible, y cualquiera de esos equipos puede
además cambiarla en el camino sin que ninguno de los dos extremos lo note.

**TLS es una capa que se inserta entre TCP y el protocolo de arriba**, y da tres cosas:
confidencialidad (lo que va adentro queda cifrado), integridad (si alguien lo modifica, se
detecta) y autenticación del servidor (el que contesta es el dueño de ese nombre y no
alguien parado en el medio). Nació en Netscape en 1994 como SSL, para poder poner un número
de tarjeta en una página web; el nombre cambió a TLS en 1999, y la versión que se usa hoy
es TLS 1.3, de 2018.

> **↓ Capa 7 — adentro del saludo de TLS, contado en viajes.** Este es el piso del tema:
> más abajo están las primitivas, y ésas son de otro capítulo.

El saludo de TLS ocurre **después** del saludo de TCP, sobre la conexión ya establecida, y
consiste en acordar una clave que sólo conozcan los dos extremos. En TLS 1.3 son dos
mensajes:

1. El cliente manda la lista de algoritmos que soporta y **su mitad del intercambio de
   claves**.
2. El servidor elige, manda su mitad, manda su **certificado** —un documento que ata ese
   nombre a una clave pública y que viene firmado por una autoridad en la que el cliente
   ya confía— y a partir de ahí todo va cifrado.

Contado en viajes de ida y vuelta, el costo del canal seguro es este:

| Paso | Viajes |
|---|---|
| Resolver el nombre (si no está en caché) | 1 |
| Saludo de TCP | 1 |
| Saludo de TLS 1.3 (1.2 cuesta el doble) | 1 |
| Autenticación del protocolo de arriba (Postgres pide usuario y contraseña) | 1 o más |

**Antes del primer byte útil ya se pagaron tres o cuatro viajes completos**, y ninguno
depende de la velocidad de la máquina. Las primitivas que hacen posible ese intercambio
—la función hash, la firma, de dónde sale un valor impredecible— se definen en
[A0-11](A0-11-criptografia-aplicada.md), y lo que cuesta esta cuenta contra São Paulo,
medido, en [A-11](A-11-rendimiento.md#base-remota).

Acá abajo, TLS aparece en cuatro lugares del repo, y cada uno enseña algo distinto:

- **La base lo exige.** `backend/.env.example:15` lo dice sin vueltas: *"El `sslmode=require`
  es obligatorio, Neon rechaza conexiones sin cifrar"*, y por eso la cadena de la línea 20
  lo lleva pegado. No es una preferencia del repo: es el otro extremo el que no acepta
  hablar en claro.
- **El certificado que no convence a nadie.** Con `VITE_HTTPS=1`, el servidor de desarrollo
  se levanta con un certificado generado en el momento
  (`Proyecto - PWA/src/frontend/vite.config.ts:67`), que ninguna autoridad firmó. El
  navegador del celular avisa que el sitio no es de confianza y hay que aceptar a mano
  (`README.md:154`). Es la parte de autenticación fallando en forma correcta: el cifrado
  funciona igual, lo que no se puede probar es **quién** está del otro lado.
- **Por qué el túnel no avisa nada.** El mismo README pasa `--no-tls-verify`
  (`README.md:163`) para que `cloudflared` acepte ese certificado propio en el tramo local,
  y la línea 166 explica el resto: al celular le llega un certificado emitido por
  Cloudflare, que sí está en la lista de autoridades de confianza. El canal termina siendo
  dos tramos cifrados distintos, con Cloudflare leyendo en claro en el medio — que es
  precisamente por qué `README.md:172` advierte que el túnel es público y se cierra al
  terminar.
- **Y el correo, que elige con el puerto.** Va en la sección siguiente, porque es el caso
  más claro de todo el repo.

---

## El envío de credenciales, que es el mismo TCP con otro diálogo

Este capítulo explicó una sola forma de hablar, no un solo idioma. Para verlo, el mejor
ejemplo del repo es el módulo que manda por correo la
[contraseña temporal](A-07-autenticacion.md#contraseña-temporal-y-primer-ingreso) de una
cuenta recién creada: `backend/notificaciones.py`. No usa HTTP en ningún momento; usa **SMTP**,
que es otro protocolo de texto sobre el mismo TCP, con un diálogo propio de órdenes cortas
—el cliente se presenta, declara el remitente, declara el destinatario, manda el cuerpo,
cierra— cada una con una respuesta numerada del servidor.

Lo que lo hace valioso acá es que **usa el puerto para elegir el dialecto de TLS**:

```python
# STARTTLS: se abre en claro y se cifra antes de mandar nada. Es lo que
# esperan Gmail, Outlook y la mayoría en el puerto 587. El 465 en
# cambio arranca cifrado de entrada (SMTP_SSL), por eso se distingue.
if SMTP_PORT == 465:
    …smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, …)
else:
    …smtplib.SMTP(SMTP_HOST, SMTP_PORT, …)
        servidor.starttls(context=ssl.create_default_context())
```

`backend/notificaciones.py:123-139` · `enviar_credenciales()`. Son las dos formas posibles
de meter TLS adentro de un protocolo viejo. En el **465** la conexión nace cifrada: el
saludo de TLS ocurre inmediatamente después del de TCP y el servidor SMTP no dice una
palabra antes. En el **587** la conexión nace en claro, el cliente pregunta en el propio
idioma del protocolo si se puede pasar a cifrado, y recién entonces empieza el saludo de
TLS sobre la conexión ya abierta. El repo elige mirando el número de puerto, que es la
única pista disponible, y es correcto porque **la convención del puerto es, de hecho, lo
que declara cuál de las dos cosas va a pasar**.

El manejo de errores de ese bloque también es un mapa de este capítulo. `OSError` está en
el mismo `except` que las fallas de SMTP porque cubre todo lo que puede romperse *abajo*
del protocolo, y el comentario las enumera: *"host inalcanzable, DNS que no resuelve,
timeout"* (`backend/notificaciones.py:148-151`). Son, en orden, una falla de ruteo (capa
2), una falla de resolución de nombre (capa 3) y la ausencia del acuse que TCP esperaba.
Tres capas distintas, una sola línea de código, y el mismo resultado para el personal del
mostrador: `enviado=False` y el texto listo para copiarlo a WhatsApp
(`backend/notificaciones.py:152-156`), porque la regla de ese módulo es no romper el alta
pase lo que pase.

---

## Con qué se conecta

- **Existe por culpa de…** el túnel contra `localhost` devuelve 502 porque el servidor de
  desarrollo quedó atado a otra interfaz ([C-04](C-04-pwa-instalable.md)).
- **Existe por culpa de…** si el puerto 8000 ya está tomado, el proceso nuevo no arranca y
  responde el viejo; por eso se cuentan las rutas publicadas
  ([A0-10](A0-10-python-del-lado-del-servidor.md#asgi-uvicorn-y-el-router)).
- **Es el mismo problema que…** el viaje de ida y vuelta que acá es una unidad, en A-11 es
  una factura medida contra São Paulo ([A-11](A-11-rendimiento.md#base-remota)).
- **Existe por culpa de…** TLS aparece porque el paquete pasa por máquinas ajenas; las
  primitivas que lo cifran y lo firman se definen en
  ([A0-11](A0-11-criptografia-aplicada.md#función-hash-criptográfica)).
- **Se contradice con…** `localhost` y `127.0.0.1` son la misma máquina para la red y dos
  sitios distintos para el navegador, y por eso los orígenes permitidos listan los dos
  ([A0-04](A0-04-el-navegador-por-dentro.md#origen-y-política-del-mismo-origen)).
- **Es la misma idea que…** la dirección del que pide se lee del socket y no de una
  cabecera, porque la cabecera la escribe el cliente
  ([A-07](A-07-autenticacion.md#freno-de-intentos-y-respuesta-indistinguible)).
