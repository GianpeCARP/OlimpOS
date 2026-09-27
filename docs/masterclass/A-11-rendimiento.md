# A-11 · Rendimiento contra una base remota

*Piso del capítulo: los viajes de ida y vuelta contados hasta São Paulo.*

Este capítulo explica por qué OlimpOS está construido como está construido. Las cinco
piezas que vas a ver acá —el pool, el latido, el listado en lote, el caché de Flet y el
precalentado del arranque— no son optimizaciones prematuras ni adornos de ingeniería: son
cinco respuestas distintas a **un solo número medido**, y ese número no se puede bajar
desde el código.

Si leés un solo capítulo de la Parte A para entender las decisiones del sistema, que sea
este o [el recorrido completo de un pedido](A-04-recorrido-de-un-pedido.md). Ese muestra
*por dónde* pasa un pedido; este muestra *por qué* el camino tiene la forma que tiene.

---

## Base remota

### El problema de origen

Cuando uno aprende a programar contra una base de datos, la aprende **local**: Postgres
corre en la misma máquina que el programa, y una consulta cuesta microsegundos. Bajo ese
supuesto, la pregunta de rendimiento que uno aprende a hacerse es *"¿cuán pesada es esta
consulta?"* — si escanea toda la tabla, si le falta un
[índice B-tree](A0-08-sql-indices-y-planes.md#índice-b-tree), si el plan es malo.

Ese supuesto es falso acá, y su falsedad reordena todo. La base de OlimpOS vive en Neon,
región `sa-east-1` (São Paulo), y el backend corre en una PC en Argentina. Entre el
programa y la base hay unos dos mil kilómetros de fibra, varios routers y un handshake
criptográfico.

Con la base remota, la pregunta de rendimiento cambia de raíz. No es cuán pesada es cada
consulta: es **cuántas veces se pregunta**. Una consulta que en local sería
imperceptiblemente más lenta que otra, acá cuesta exactamente lo mismo que ella —porque
las dos pagan el mismo viaje— y diez consultas livianas cuestan diez veces más que una
pesada.

### Los dos números

Están medidos y escritos en el código, no estimados:

| Operación | Costo | Qué es |
|---|---|---|
| `SELECT 1` en una conexión **ya abierta** | **44 ms** | el piso físico: un viaje de ida y vuelta |
| Abrir una conexión **nueva** (TLS + autenticación) | **825 ms** | 19 veces más caro que una consulta |

`backend/database.py:50-53`, en el bloque de comentario que encabeza la configuración del
motor. Los mismos dos números están repetidos en `Flet/Proyecto/app/api_client.py:171-172`,
y esa duplicación es deliberada: las dos piezas que los usan para decidir están en
proyectos distintos, y quien toque una tiene que ver el número sin cambiar de repo.

El propio comentario dice de dónde vienen: *"son la velocidad de la luz hasta São Paulo y
el costo de un handshake TLS"* (`database.py:56-57`). Vale la pena abrir esa frase, porque
es literal.

> **↓ Capa 2 — de dónde salen los 44 ms.** Salteable si ya sabés estimar latencia de red.

Un [viaje de ida y vuelta](A0-02-como-se-comunican-dos-maquinas.md#tcp-y-el-viaje-de-ida-y-vuelta-rtt)
entre Buenos Aires y São Paulo recorre unos 1.700 km en cada sentido: 3.400 km de fibra
por consulta. La luz en fibra óptica viaja a unos 200.000 km/s —dos tercios de su
velocidad en el vacío, porque el vidrio la frena—. La cuenta da:

```
3.400 km ÷ 200.000 km/s = 17 ms
```

Diecisiete milisegundos es el **piso teórico absoluto**: lo que costaría el viaje si la
fibra fuera un caño recto entre las dos ciudades y no hubiera nada en el medio. Lo medido
son 44 ms, dos veces y media más. Esa diferencia no es misteriosa: la fibra no va derecho
(sigue rutas comerciales y a veces desvía), y en el camino hay una docena de routers, cada
uno de los cuales recibe el paquete entero, lo mira y lo reenvía.

Lo que importa de este cálculo no es el número: es que **44 ms es un límite físico, no un
problema de software**. Ninguna versión de Python, ningún índice y ninguna reescritura del
backend lo bajan. La única forma de mejorar es preguntar menos veces.

> **↓ Capa 3 — de dónde salen los 825 ms.** Salteable si conocés el handshake de TLS.

Abrir una conexión nueva no es un viaje: son varios, en serie, y cada uno cuesta 44 ms.

```
1. Handshake de TCP (SYN, SYN-ACK, ACK) .............. 1 viaje  ≈  44 ms
2. Handshake de TLS (negociar cifrado y verificar)  1 a 2 viajes ≈  44-88 ms
3. Arranque del protocolo de Postgres y autenticar  1 a 2 viajes ≈  44-88 ms
                                                     ────────────────────────
                                                     ≈ 130 a 220 ms
```

La aritmética explica entre 130 y 220 de los 825 ms medidos. **El resto —unos 600 ms— no
lo explica el modelo**, y es honesto decirlo en vez de inventar una justificación: Neon no
es un Postgres pelado escuchando en un puerto, sino un proxy de conexiones que lee el
nombre del host, decide a qué compute mandarte y lo activa si hace falta. Ese trabajo está
adentro de los 825 ms y no se puede desglosar desde acá.

La lección metodológica es más valiosa que el desglose: **el número que gobierna las
decisiones del sistema es el medido, no el calculado.** El cálculo sirve para saber que
825 ms no es un bug —tiene que ser caro, son varios viajes— pero el valor que se usa para
decidir sale de haberlo cronometrado.

Para el detalle de qué negocia TLS y por qué cuesta viajes, ver
[TLS](A0-02-como-se-comunican-dos-maquinas.md#tls).

### El síntoma, en palabras del dueño

Todo esto se descubrió a partir de un reporte que no menciona ni la red ni la base:

> *"Si cambio de panel rápido carga al toque, pero si espero un rato vuelve la tardanza, y
> a veces aparece de la nada."*

Está transcripto en `backend/database.py:62-63` y otra vez en
`Flet/Proyecto/app/api_client.py:185-187`. Las tres partes de esa frase son tres pistas
distintas, y cada una llevó a una pieza distinta del sistema: "carga al toque" es el
caché funcionando, "si espero un rato vuelve la tardanza" es una conexión que se murió
sola, y "aparece de la nada" es que cada conexión del pool muere en un momento distinto.

### Por qué está hecho así

**Qué se optimiza:** la cantidad de viajes a la base, y nada más. Ni el uso de CPU, ni la
memoria, ni el tamaño de las respuestas.

**Qué restringe:** la base tiene que estar en Neon. Es lo que pide la consigna del
proyecto, y no es negociable desde el código.

**Qué alternativa se descartó:** poner la base local, que es la solución obvia y elimina
el problema de raíz. No se descartó para siempre —`database.py:6-9` dice que mañana va a
vivir en un servidor del gimnasio y que ese cambio *"no toca ni una línea de este
archivo: lo único que cambia es `DATABASE_URL` en el `.env`"`—. Se descartó **para hoy**, y
la decisión de fondo fue no diseñar la aplicación como si la base ya fuera local.

**Qué se pagó:** complejidad permanente. Cinco mecanismos —pool configurado, precalentado,
latido, carga en lote y caché de dos generaciones— que en una base local no harían falta y
que igual habrá que mantener cuando la base se mude, porque sacarlos sería una migración
en sí misma. El sistema quedó preparado para el peor caso, y ese seguro se paga todos los
días en líneas de código.

**Cómo se llama:** diseñar para la latencia. El nombre general del error que evita es
*fallacy of zero latency*, la primera de las falacias de la computación distribuida:
suponer que la red no cuesta.

---

## Pool de conexiones

### El problema de origen

Si abrir una conexión cuesta 825 ms, abrir una por pedido es inaceptable: cada pantalla
arrancaría con casi un segundo de castigo antes de la primera consulta. La respuesta
estándar es un **pool**: un puñado de conexiones que se abren una vez, se prestan a cada
pedido y se devuelven en vez de cerrarse.

Eso es lo que hace `SessionLocal` en `backend/database.py:117`, y lo que la dependencia
`get_db()` (`database.py:154-165`) presta y devuelve en cada pedido. La conexión no se
cierra al terminar: vuelve al pool.

Hasta acá es la configuración que trae SQLAlchemy por defecto, y **no alcanzaba**.

### Las conexiones se mueren solas

Con `pool_recycle=-1` —el valor por defecto— SQLAlchemy no recicla nunca: deja las
conexiones en el pool hasta que alguien del otro lado las cierra. Y hay dos alguien:

- **Neon**, que corta conexiones ociosas por su cuenta.
- **El NAT del router**, que al no ver tráfico durante un rato da la conexión por muerta y
  descarta la traducción de puertos que la sostenía.

Cuando eso pasa, `pool_pre_ping=True` detecta que la conexión está muerta y reconecta de
forma transparente. La aplicación no falla —y eso es bueno— pero **ese pedido paga los
825 ms**. Y como cada conexión del pool se muere en un momento distinto, la lentitud
aparece de manera aparentemente aleatoria: exactamente el *"a veces aparece de la nada"*
del reporte (`database.py:65-71`).

Notá el tipo de falla: no hay error, no hay log, no hay excepción. El sistema funciona y
sólo se siente raro. Es el modo de fallar más difícil de diagnosticar, porque no deja
rastro más que en la percepción de quien lo usa.

### Las tres piezas, y qué arregla cada una

La configuración real está en `backend/database.py:92-113`. Cada parámetro tapa un agujero
distinto:

| Parámetro | Valor | Qué resuelve |
|---|---|---|
| `pool_recycle` | `240` (4 min) | descarta las conexiones **antes** de que Neon o el NAT las corten |
| `keepalives` + los tres que lo acompañan | `1`, `30`, `10`, `5` | manda un paquete cada 30 s sobre la conexión ociosa, para que el NAT no la dé por muerta |
| `pool_size` | `10` | el pool se llena una vez y no vuelve a pagar 825 ms por crecer |
| `pool_timeout` | `10` | si el pool está lleno, fallar en 10 s en vez de esperar 30 |
| `pool_pre_ping` | `True` | seguro final: una conexión muerta nunca llega como error a la pantalla |

El razonamiento de `pool_recycle` está en una sola frase que vale memorizar
(`database.py:76-77`): *"reciclar es barato cuando lo decidimos nosotros —pasa entre
pedidos— y caro cuando lo decide la red —pasa en medio de uno"*. Es la misma idea que
aparece en cualquier sistema que prefiere el mantenimiento programado a la reparación de
emergencia: no se evita el costo, se elige **cuándo** pagarlo.

Los `keepalives` merecen una nota aparte porque atacan un caso que `pool_recycle` no cubre.
`database.py:81-83` describe el peor escenario: una conexión *"viva para nosotros y cortada
para el otro extremo"*. Ahí no hay nada que reciclar —desde el lado de Python la conexión
parece perfecta— y el error aparece recién al usarla. Los `keepalives` no viven en
SQLAlchemy: `psycopg2` los pasa como parámetros de conexión a `libpq`, la biblioteca C de
Postgres, que a su vez los configura en el socket TCP del sistema operativo. Son una
opción del socket, dos capas por debajo del ORM.

Y `pool_pre_ping` se mantiene **aunque cueste un viaje de 44 ms en cada préstamo**
(`database.py:89-91`). Es una decisión de las que definen el criterio de un sistema:
44 ms de peaje fijo a cambio de que una conexión muerta nunca se convierta en un error en
pantalla. Con las tres piezas anteriores funcionando, casi nunca tiene que reconectar, así
que el seguro sale barato — pero se paga siempre.

### El precalentado del arranque

Queda un caso que el pool no resuelve: la **primera** pantalla después de levantar el
backend, cuando el pool está vacío y alguien tiene que pagar los 825 ms.

`calentar_pool()` (`backend/database.py:122-151`) abre tres conexiones al arrancar,
ejecuta un `SELECT 1` en cada una y las cierra. El truco está en el comentario del
`finally` (`database.py:148-149`): cerrarlas **las devuelve al pool**, no las destruye.
Quedan abiertas contra Neon, listas para el primer pedido real.

Lo interesante es lo que hace cuando falla. El `except` es deliberadamente amplio y no
propaga nada (`database.py:144-146`), y el docstring da el razonamiento: *"un arranque que
revienta por esto sería peor que un primer pedido lento"*. Es una regla general de diseño
disfrazada de detalle: **una optimización nunca puede ser un requisito para arrancar**. El
precalentado cumple esa regla: nunca es él quien frena el arranque.

### Nota marcada · el arranque sin base se corta antes

El mismo docstring promete más de lo que el sistema entrega (`database.py:131-133`): *"Si Neon
está dormido o la red está caída NO se propaga el error: el backend tiene que poder arrancar
igual"*. La promesa no depende sólo de esta función, sino de lo que corre antes, y antes corre
`Base.metadata.create_all()` (`main.py:142`), que necesita conectarse a la base y **no está
protegida**.

Se verificó arrancando el `lifespan` real con la base apuntada a un puerto local cerrado —sin
tocar Neon ni levantar el servidor—: el arranque se corta con `OperationalError` en
`main.py:142`, antes de llegar a `calentar_pool()`. Con la red caída **el backend no arranca**.
Lo que el `except` evita es otra cosa, más acotada: que una falla del precalentado en sí aborte
un arranque que ya tenía base. Y la especificación de procesos lo dice bien: el proceso 172
declara *"arranque abortado si la base no responde"*.

Con Neon suspendido, en cambio, no hay corte: la primera conexión lo despierta, y el arranque
sólo tarda más.

### Nota marcada · discrepancia entre comentario y código

El comentario de `database.py:86-87` dice que el pool tiene *"10 fijas y sin overflow"*,
pero la línea 97 configura `max_overflow=5`. El pool puede crecer hasta 15 conexiones, no
10, y las cinco de más sí pagan 825 ms al abrirse.

**Gana el código:** el comportamiento real es que hay overflow. La afirmación de fondo del
comentario sigue siendo cierta —el pool se llena una vez y no vuelve a pagar el handshake
en operación normal— porque el overflow sólo se usa si los diez préstamos simultáneos se
agotan, que con un puñado de personas usando el sistema no pasa. Lo que quedó viejo es la
palabra "sin".

### Por qué está hecho así

**Qué se optimiza:** no volver a pagar nunca los 825 ms en un pedido real.

**Qué restringe:** el otro extremo de la conexión no lo controlamos. Neon corta cuando
quiere y el NAT del router del gimnasio también.

**Qué alternativa se descartó:** confiar en `pool_pre_ping` solo, que era el estado
inicial. Funcionaba —nunca hubo un error— pero trasladaba el costo a un pedido al azar, y
un sistema que a veces tarda un segundo sin motivo visible se siente roto aunque no lo
esté.

**Qué se pagó:** cinco parámetros que hay que entender para tocar, y un peaje fijo de
44 ms por préstamo que viene de `pool_pre_ping`.

**Cómo se llama:** agrupamiento de recursos (*pooling*). El patrón general es pagar una
vez algo caro y reusarlo, y en este sistema aparece dos veces: acá con las conexiones y en
[servir y refrescar](#servir-y-refrescar) con las respuestas.

---

## Latido

### El problema de origen

El pool resuelve que las conexiones no se mueran. No resuelve que **la base entera se
duerma**.

Neon, en su plan gratuito, **suspende el compute** después de unos minutos sin consultas, y
despertarlo cuesta segundos —no milisegundos—. Sumado a los 825 ms de una conexión nueva,
es la otra mitad del *"a veces la tardanza aparece de la nada"*
(`backend/main.py:68-72`).

Es un problema de una naturaleza distinta a los anteriores: no lo causa la distancia ni el
NAT, lo causa una decisión comercial del proveedor. Y por eso la solución no es técnica en
el sentido habitual — es simplemente **no dejar de usar la base nunca**.

### La solución, y su costo real

Un `SELECT 1` cada dos minutos. `SEGUNDOS_ENTRE_LATIDOS = 120` en `backend/main.py:85`, y
el bucle en `_latido()` (`main.py:90-113`).

Ese latido hace dos cosas con una sola consulta (`main.py:74-76`): mantiene el compute
despierto **y** hace que las conexiones del pool no queden ociosas el tiempo suficiente
para que alguien las corte. Refuerza a los `keepalives` desde otra capa: aquéllos mandan
un paquete TCP vacío, éste manda tráfico real de Postgres.

El costo, dicho en el propio comentario (`main.py:83-84`): 30 consultas por hora, contra
el riesgo de *"despertar el compute en medio de un cobro"*. Treinta viajes de 44 ms por
hora son 1,3 segundos de red por hora. La comparación no necesita más análisis.

> **↓ Capa 2 — por qué es un hilo y no una tarea async.** Salteable si ya sabés por qué.

La decisión está justificada en `main.py:78-81` y es de las más instructivas del repo:
**SQLAlchemy acá es síncrono.** Poner el latido como tarea del bucle de eventos
bloquearía el bucle entero durante los 44 ms del viaje, cada dos minutos — y mientras el
bucle está bloqueado, ningún otro pedido avanza.

Un hilo aparte no tiene ese problema porque, mientras espera la red, no retiene el
[GIL](A0-10-python-del-lado-del-servidor.md#gil-y-concurrencia--paralelismo). Se lanza como
`daemon=True` (`main.py:149`), lo que significa que muere solo cuando el proceso termina,
sin que nadie tenga que cancelarlo. Para la diferencia entre una
[corrutina](A0-10-python-del-lado-del-servidor.md#corrutina) y un hilo, y por qué esperar
la red no bloquea pero calcular sí, el capítulo de Python del servidor.

### De paso, el gancho del mantenimiento diario

El latido hace una segunda cosa que no tiene nada que ver con el rendimiento
(`main.py:97-106`): una vez por día aplica las bajas programadas que ya vencieron, llamando
a `aplicar_bajas_vencidas(db)`.

El motivo está escrito y es el tipo de razonamiento que no se deduce leyendo el código:
*"un backend que no se reinicia en semanas no puede depender del arranque para
aplicarlas"*. Las bajas también se aplican al arrancar y al leer socios, pero un servidor
que lleva tres semanas encendido y donde nadie abrió la grilla de socios necesitaba un
tercer camino. El latido ya corría en segundo plano, a intervalo conocido, con una sesión
de base disponible: era el lugar natural para colgar una tarea periódica.

Vale ver el patrón: **el sistema no tiene planificador de tareas**, ni `cron`, ni Celery,
ni un scheduler. Tiene un hilo que late para no dormirse, y de ese hilo cuelga lo poco que
hay que hacer periódicamente. Es la solución proporcionada al problema, y es más fácil de
razonar que una dependencia nueva. Cómo se ven esos procesos que corren solos desde el
lado de la especificación está en
[cómo leer los procesos](A-12-como-leer-los-procesos.md).

### El `except` que no registra nada

`main.py:107-113` traga la excepción y no la anota. Es a propósito, y la justificación es
de operación, no de programación: un latido fallido *"puede ser un corte de red de un
segundo"*, el próximo lo reintenta, y si la base está de verdad caída la persona se entera
por la pantalla — que es donde corresponde. Un log por latido fallido llenaría la consola
de ruido justo durante un corte, que es cuando uno necesita leerla.

Al apagar, `_latido_activo.set()` (`main.py:194`) corta el bucle, porque el hilo usa
`Event.wait()` como espera interrumpible en lugar de `sleep`.

---

## Listado en lote

### El problema de origen

El [problema N+1](A0-09-el-orm.md#n1) es la forma más común de arruinar el rendimiento sin
escribir una sola consulta lenta. Con una base local es un problema de libro; con la base
a 44 ms de viaje es el problema que hace que una pantalla no se pueda usar.

`backend/routers/socios.py:174-181` tiene los números medidos de este repo, y conviene
leerlos despacio. El armador de a uno, `_a_socio_out()` (`socios.py:259`), hace **cuatro
consultas por socio**: la membresía vigente, el teléfono principal, `persona.usuario` y
`membresia.tipo`. Reusarlo en un bucle da:

| Socios | Consultas | Tiempo |
|---|---|---|
| 3 | 14 | 1,4 s |
| 100 | ~400 | *"medio minuto"* |

Y la frase que cierra el razonamiento (`socios.py:179-181`): *"el costo no es la base: es
la RED (…) lo único que importa es cuántas veces se pregunta, no qué tan pesada es cada
pregunta"*.

### La solución: un número fijo de consultas

`_listar_socios_en_lote()` (`backend/routers/socios.py:170-258`) arma la misma grilla con
una cantidad de consultas que **no depende de cuántas filas haya**. Usa `selectinload`
—[carga ansiosa](A0-09-el-orm.md#carga-perezosa-contra-carga-ansiosa), que trae cada
relación en una consulta aparte y en lote— más dos consultas propias.

Contadas una por una, que es el piso de este capítulo:

| # | Consulta | Dónde |
|---|---|---|
| 1 | los socios | `socios.py:191-202` (`.all()`) |
| 2 | sus personas | `selectinload(Socio.persona)` |
| 3 | los teléfonos de esas personas | `selectinload(Persona.telefonos)`, línea 198 |
| 4 | los usuarios de esas personas | `selectinload(Persona.usuario)`, línea 199 |
| 5 | los contactos de emergencia | `selectinload(Persona.contactos_emergencia)`, línea 200 |
| 6 | las bajas programadas | `pendientes_por_socio()`, línea 207 → `bajas.py:58-65` |
| 7 | todas las membresías de esos socios | `socios.py:213-218` |
| 8 | los tipos de membresía | `selectinload(Membresia.tipo)`, línea 214 |

**Ocho consultas, con tres socios o con quinientos**: 352 ms de red fijos. Con cien socios,
el camino de a uno haría unas 400 consultas y tardaría 17,6 segundos.

Pasados los quinientos hay un matiz: `selectinload` manda el `IN` en tandas de 500 ids
([carga ansiosa](A0-09-el-orm.md#carga-perezosa-contra-carga-ansiosa)). Con mil socios,
cada una de las cuatro relaciones cargadas así (consultas 2 a 5) hace dos consultas en vez
de una, y el total sube a **doce**. Las consultas 6 y 7 no se parten porque el código arma
su `IN` a mano, y la 8 depende de cuántos *tipos* de membresía hay, que son un puñado. La
cifra deja de ser estrictamente fija, pero crece de a una cada quinientas filas: doce
consultas contra las 4.000 del camino de a uno, que a 44 ms cada una serían **176
segundos, casi tres minutos**.

La consulta 7 tiene un detalle que vale la pena: en vez de pedir la membresía vigente de
cada socio, trae **todas** las membresías de todos los socios ordenadas por el mismo
criterio que usa `_membresia_vigente()` y se queda con la primera de cada uno mediante
`vigentes.setdefault(m.id_socio, m)` (`socios.py:219-220`). El mismo criterio de negocio,
una sola consulta. Es la jugada típica de la carga en lote: **traer de más y filtrar en
memoria** sale infinitamente más barato que preguntar de menos muchas veces, porque la
memoria es gratis y el viaje no.

### Nota marcada · el conteo quedó viejo

El docstring de `socios.py:183-184` dice *"acá se pregunta cinco veces en total"* y
enumera tres grupos: *"socios, personas (con teléfonos y usuario), y membresías (con su
tipo)"*. El comentario de `Flet/Proyecto/app/api_client.py:173` dice seis.

**Ninguno de los dos coincide con el código de hoy, que hace ocho.** La causa es
rastreable: la enumeración del docstring no incluye
`selectinload(Persona.contactos_emergencia)` ni `pendientes_por_socio()`, que son las dos
consultas que agregaron los contactos de emergencia múltiples y la baja programada después
de que se escribiera ese comentario.

**Gana el código.** Y conviene ser preciso sobre qué quedó mal: el número. La propiedad
que el docstring afirma —que la cantidad de consultas es **fija** y no crece con las
filas— sigue siendo verdadera, y es la única que importa para el rendimiento. Ocho
consultas constantes son tan buenas como cinco constantes, y ambas son otra categoría
frente a cuatro por fila.

### La trampa que dejó la grilla "vacía pero funcionando"

`socios.py:193-197` guarda un comentario sobre un error ya cometido, y es el mejor ejemplo
del repo de por qué un error silencioso es peor que un error ruidoso.

La primera versión de este armador pasó a `selectinload` una relación que **no existía**,
`Socio.membresias`. El endpoint devolvía 500. Y como el cliente de Flet traduce un error a
una lista vacía, la grilla se veía *"vacía pero funcionando"* — sin cartel de error, sin
nada roto en pantalla: simplemente un gimnasio sin socios.

Un 500 visible se arregla en cinco minutos. Una grilla vacía que parece correcta puede
sobrevivir semanas, y en el medio alguien puede concluir que la base se borró. La lección
que el comentario deja escrita es de método: las relaciones se **verifican** con
`sqlalchemy.inspect(Socio).relationships`, no se recuerdan.

### Los dos caminos tienen que dar lo mismo

`_a_socio_out()` no se borró: sigue existiendo para el socio de a uno —alta, edición,
baja— *"donde cuatro consultas están bien y el código se lee mejor"*
(`socios.py:186-187`).

Tener dos caminos para armar la misma salida es deuda: pueden divergir. La forma de
controlarla está en `socios.py:187-189`: **toda regla de derivación vive en una sola
función que los dos llaman.** El estado del socio sale de `_estado_socio()`
(`socios.py:97`) en los dos casos, así que un cambio de regla no puede aplicarse a la
grilla y no a la ficha. Esa función es el tema de
[estados derivados](A-09-estados-derivados.md).

Lo mismo con las dos grillas del sistema: `socios.py:1132` anota que la de entrenadores
usa *"el mismo camino en lote que /socios"*.

### Por qué está hecho así

**Qué se optimiza:** cantidad de consultas por pantalla, con independencia del número de
filas.

**Qué restringe:** que la grilla necesita datos de siete tablas para pintar una fila, y
que quitar columnas no era opción porque el mostrador las usa.

**Qué alternativa se descartó:** dos, en realidad. Reusar `_a_socio_out()` en un bucle
—descartada por los números de arriba—. Y desnormalizar: guardar en `Socio` una copia del
estado, el plan y el teléfono para leer todo de una tabla. Esa habría bajado a una
consulta, y se descartó porque obliga a mantener las copias sincronizadas en cada
escritura, que es el problema que
[estados derivados](A-09-estados-derivados.md) explica por qué este sistema evita.

**Qué se pagó:** dos caminos de armado que hay que mantener de acuerdo, y un armador de
casi noventa líneas bastante más difícil de leer que un bucle.

**Cómo se llama:** carga en lote, o *eager loading*. El anti-patrón que evita es el N+1.

---

## Servir y refrescar

### El problema de origen

Todo lo anterior pasa en el backend. Pero incluso con ocho consultas fijas, `GET /socios`
tarda **450 ms**, y `GET /personal` **570 ms** (`Flet/Proyecto/app/api_client.py:173-174`).
Eso es lo que la persona del mostrador espera cada vez que cambia de panel, con una cola
adelante.

La respuesta obvia es cachear en el cliente. La primera versión de Flet hizo exactamente
eso: guardar la respuesta 15 segundos y después tirarla. Un caché con vencimiento, de
manual.

**No funcionó, y el modo en que falló es la parte que enseña** (`api_client.py:180-191`).
Dentro de la ventana de 15 segundos había caché y todo era instantáneo; pasada la ventana
se volvían a esperar los 450 ms completos. El caché *"escondía el problema en vez de
resolverlo, y encima lo volvía impredecible — la misma acción tardaba distinto según
cuánto habías tardado vos en hacerla"*.

Ese es el diagnóstico exacto del *"si cambiás entre paneles rápido cargan al toque, pero si
esperás un rato vuelve la tardanza"*. El caché con vencimiento no era la solución al
síntoma: **era una de sus causas.**

### Cómo funciona ahora

La regla es una sola y está en `api_client.py:195-198`: **se sirve siempre lo que hay en
caché, al instante, aunque esté vencido.** Si está vencido, además se dispara un refresco
en segundo plano que actualiza la entrada para la próxima vez.

```
primera visita  ->  se espera (no hay nada que mostrar)
resto           ->  instantáneo, siempre
```

La pantalla nunca espera a la red. En el peor caso muestra datos de hace un minuto y se
corrige sola. `FRESCURA = 30` (`api_client.py:223`) no es un tiempo de vida: es el momento
en que la entrada empieza a considerarse vieja y a disparar refrescos — se sigue sirviendo
igual.

El nombre del patrón está en el propio comentario (`api_client.py:203`): es
**stale-while-revalidate**, el mismo que define HTTP para sus cachés. Y encaja por una
razón de negocio, no de tecnología (`api_client.py:203-205`): los datos de este sistema son
de lectura frecuente y escritura rara — *"la grilla de socios se mira cien veces por cada
vez que se da de alta a alguien"*.

> **↓ Capa 2 — las tres estructuras que lo sostienen.** Salteable si conocés el patrón.

`api_client.py:225-232`:

| Estructura | Qué guarda | Para qué |
|---|---|---|
| `_cache` | `{ruta: (momento, respuesta)}` | lo que se sirve |
| `_refrescando` | conjunto de rutas | que dos pantallas no disparen dos refrescos de lo mismo |
| `_candado` | un `Lock` | que los hilos no se pisen al tocar las dos anteriores |
| `_generacion` | un entero que sólo sube | descartar refrescos que llegaron tarde |

El refresco corre en un hilo aparte (`api_client.py:295-298`), por el mismo motivo que el
latido: el cliente HTTP es síncrono y esperarlo en el hilo de la interfaz congelaría la
pantalla. `_refrescando` garantiza un solo refresco en vuelo por ruta
(`api_client.py:293-294`), y el `finally` lo descarta siempre (`api_client.py:265-267`) para
que un fallo no deje la ruta marcada para siempre.

### Lo que escribe, invalida todo

Acá está la decisión más agresiva del sistema, y la mejor justificada. Cualquier `POST`,
`PUT` o `DELETE` llama a `limpiar_cache()` (`api_client.py:235-246`), que **borra el caché
entero** — no la ruta que se tocó.

El razonamiento está en `api_client.py:207-216` y es un ejemplo de elegir el error más
barato. Cobrar una membresía cambia `/socios` (el estado del socio),
`/cobros/socio/{id}`, `/dashboard/stats` y `/cobros/deudas` **a la vez**. Invalidar "sólo
lo relacionado" exigiría un mapa de dependencias entre rutas mantenido a mano. Y el día
que alguien agregue un endpoint y se olvide de anotarlo, la pantalla mostraría un dato
viejo **después de cobrar** — *"que es el único momento en que un dato viejo es
inaceptable"*.

La conclusión, textual: *"tirar todo cuesta un pedido de más y no se puede olvidar."*

Vale detenerse en la forma de ese argumento, porque se puede reusar en cualquier sistema.
No compara las dos opciones por eficiencia —la invalidación dirigida gana por lejos—: las
compara por **cómo fallan cuando alguien se equivoca**. Tirar todo falla haciendo un pedido
innecesario. La invalidación dirigida falla mostrando plata mal. Cuando los modos de falla
son tan asimétricos, la eficiencia deja de ser el criterio.

### La generación, y el refresco que llega tarde

Queda una carrera fina. Un refresco en vuelo pidió `/socios` hace 400 ms. Mientras
viajaba, alguien cobró una cuota y el caché se vació. Si ese refresco guardara su
respuesta, **resucitaría el estado anterior al cobro** — un dato viejo escrito después de
la escritura que lo invalidó.

La solución es un contador de generación (`api_client.py:229-232`). `limpiar_cache()` lo
incrementa; el hilo de refresco se guarda la generación con la que salió y, al volver,
sólo escribe si sigue siendo la misma:

```python
if generacion == _generacion:
    _cache[path] = (time.monotonic(), respuesta)
```

`api_client.py:258-259`, y el mismo chequeo en el camino sincrónico en las líneas 309-310.
Si la generación cambió, el resultado se descarta en silencio. Nueve líneas para cerrar una
carrera que aparecería como *"cobré y la grilla mostró el estado viejo"*, una vez cada
tanto, imposible de reproducir a mano.

El cierre de sesión también vacía el caché (`api_client.py:72`), y por un motivo distinto
del rendimiento: las respuestas guardadas son de la persona anterior. Eso pertenece al
aislamiento de datos por rol, en [autorización](A-08-autorizacion.md).

### Por qué está hecho así

**Qué se optimiza:** el tiempo que la pantalla del mostrador espera. El objetivo no es que
el sistema haga menos trabajo, sino que **la persona nunca espere**.

**Qué restringe:** los 450 a 570 ms por pantalla, que ya son el resultado de haber
optimizado el backend todo lo posible.

**Qué alternativa se descartó:** el caché con vencimiento, que estuvo implementado y se
sacó. Y la invalidación dirigida, descartada por su modo de fallar.

**Qué se pagó:** datos de hasta un minuto de antigüedad en pantalla, tres estructuras
compartidas entre hilos con un candado, y un pedido de más por cada escritura.

**Cómo se llama:** *stale-while-revalidate* para el servido, e invalidación por generación
para la carrera.

---

## El cuello es la red, nunca Python

Esta sección no agrega un mecanismo: da la conclusión que ordena las cinco anteriores y
permite decidir sin volver a medir.

Tomemos `GET /socios`, que tarda 450 ms medidos, y repartamos ese tiempo:

```
8 consultas × 44 ms de viaje ..................  352 ms   ≈ 78 %
todo lo demás .................................   98 ms   ≈ 22 %
```

Ese "todo lo demás" incluye absolutamente todo lo que hace Python: el planificador de
Postgres, el armado de objetos del ORM, las ocho vueltas del bucle que arma la salida, la
validación de Pydantic, la serialización a JSON y el envío de la respuesta.

De ahí salen dos consecuencias prácticas.

**Optimizar cálculo no mueve la aguja.** Si alguien reescribiera el armador de la grilla
para que fuera el doble de rápido, la pantalla pasaría de 450 a unos 425 ms: una mejora de
5 % que nadie percibe. Reescribir el backend entero en un lenguaje compilado tocaría, como
máximo, ese 22 %.

**Optimizar viajes sí.** Quitar una sola consulta de las ocho ahorra 44 ms — más que
duplicar la velocidad de todo el código Python del endpoint. Por eso todo el esfuerzo de
rendimiento de este sistema está puesto en contar consultas y no en perfilar funciones.

Esto también explica por qué el backend es asíncrono aunque el trabajo sea síncrono.
Durante esos 352 ms el proceso está **esperando**, no calculando: no retiene el
[GIL](A0-10-python-del-lado-del-servidor.md#gil-y-concurrencia--paralelismo) y puede atender
otros pedidos mientras espera. La concurrencia acá no sirve para calcular más rápido,
sirve para que la espera de uno no sea la espera de todos.

### Lo que esta conclusión prohíbe

Las cinco piezas de este capítulo se ven, leídas de a una, como complejidad injustificada:
un pool con cinco parámetros, un hilo que consulta cada dos minutos, un armador de noventa
líneas, un caché con contador de generación. **Ninguna se puede sacar sin que vuelva un
síntoma que ya se reportó y se arregló.** Concretamente:

| Si se saca | Vuelve |
|---|---|
| `pool_recycle` o los `keepalives` | pedidos de 825 ms aparentemente al azar |
| el latido | segundos de espera al volver después de un rato |
| el listado en lote | una grilla que tarda medio minuto con 100 socios |
| el caché de Flet | medio segundo cada vez que se cambia de panel |
| `calentar_pool()` | la primera pantalla siempre lenta |

Y cuando la base se mude al servidor local del gimnasio, todo esto se va a volver
innecesario sin volverse incorrecto. Sacarlo será una decisión con su propio análisis, no
una limpieza.

---

## Con qué se conecta

- **Es la misma idea que…** el [pool de conexiones](#pool-de-conexiones) y
  [servir y refrescar](#servir-y-refrescar): pagar una vez algo caro y reusarlo, con la
  conexión y con la respuesta.
- **Es el mismo problema que…** el [N+1](A0-09-el-orm.md#n1) y los 825 ms de una conexión
  nueva: viajes de ida y vuelta, a dos escalas distintas.
- **Es la misma idea que…** la
  [carga ansiosa](A0-09-el-orm.md#carga-perezosa-contra-carga-ansiosa) y el
  [listado en lote](#listado-en-lote): el mismo mecanismo visto como herramienta del ORM y
  como decisión de rendimiento.
- **Existe por culpa de…** el [latido](#latido) y el mantenimiento diario: es el único
  proceso periódico del sistema, así que de él cuelga lo que tiene que correr todos los
  días ([A-12](A-12-como-leer-los-procesos.md)).
- **Existe por culpa de…** la invalidación total del caché al cerrar sesión: las respuestas
  guardadas pertenecen a la persona anterior ([A-08](A-08-autorizacion.md)).
- **Se contradice con…** `pool_pre_ping`, que cuesta un viaje en cada préstamo justamente
  en el capítulo que dice que hay que ahorrar viajes. Ganó la certeza de que una conexión
  muerta no llegue a la pantalla, y el resto de la configuración está puesta para que ese
  seguro casi nunca tenga que actuar.
