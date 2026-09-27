# A-09 · Estados derivados contra estados guardados

*Piso del capítulo: la función que calcula un estado en cada lectura, y el orden de sus
chequeos.*

Un sistema de gestión está lleno de preguntas de la forma "¿en qué estado está esto?". ¿El
socio está al día? ¿Esta reserva fue o faltó? ¿Esta membresía corre o está en pausa? Para cada
una hay dos formas de tener la respuesta: **guardarla** en una columna, o **calcularla** cada
vez que alguien la pide. Este capítulo explica cuándo corresponde cada una, con el caso que
más se ve del sistema —la píldora de estado del socio— como ejemplo principal.

Cómo se usa esa respuesta para decidir si se puede cobrar está en
[el recorrido de un pedido](A-04-recorrido-de-un-pedido.md#escala-16--la-regla-de-negocio), y
qué significa "deber" en un sistema sin deudas, en
[membresía vigente](A-02-prepago-puro.md#membresía-vigente-y-qué-significa-deber). Acá está
el mecanismo que los dos usan.

---

## Estado derivado

### El problema de origen: el estado que miente sin que nadie escriba

Una membresía que vence el 30 de septiembre se guarda con `estado = 'ACTIVA'`. El 1 de octubre
ya no está activa, pero la columna **sigue diciendo `ACTIVA`**: nadie escribió nada, y sin
embargo el dato pasó a ser falso. El tiempo no dispara ningún `UPDATE`.

Frente a eso hay dos salidas:

1. **Un proceso que corra solo**, todas las noches, recorriendo las membresías y marcando
   `VENCIDA` las que pasaron su fecha. El estado se sigue guardando, y alguien lo mantiene al
   día.
2. **No guardarlo**: calcular el estado cada vez que alguien lo pide, a partir de las fechas y
   del día de hoy. Si el reloj avanza, la respuesta cambia sola.

La segunda se llama **derivar en vez de almacenar**, y `backend/turnos.py:19-23` tiene la mejor
justificación escrita del repo, a propósito de la asistencia a clases:

> *"Guardarlos obligaría a un proceso que corra solo marcando ausentes. Ese proceso se cae, se
> atrasa o corre dos veces, y mientras tanto el panel muestra como pendiente un turno que venció
> hace una hora. Derivándolos no hay nada que pueda desincronizarse: si el reloj avanza, la
> respuesta cambia sola."*

El argumento no es que el proceso sea difícil de escribir. Es que un proceso que corre solo
**tiene modos de fallar propios** —no corre, corre tarde, corre dos veces— y cada uno produce un
dato falso en pantalla sin ningún error visible. Una función que calcula no tiene ninguno de esos
modos: no corre en ningún momento en particular, corre cuando se la llama.

Este sistema, además, casi no tiene procesos que corran solos. El único es el
[latido](A-11-rendimiento.md#latido), y de él cuelga el mantenimiento diario de las bajas
programadas. Derivar es lo que permite no necesitar más.

> **↓ Capa 1 — lo que cuesta derivar.** Este es el piso del concepto.

Derivar no es gratis: para calcular el estado de un socio hay que traer su membresía más reciente
y el tipo de esa membresía, en cada lectura. Para una ficha son dos consultas; para una grilla de
cien socios, hechas de a una, serían doscientas. El precio de derivar se paga en viajes a la base,
y por eso siempre viene acompañado de la técnica que lo abarata: traer todo en lote. La grilla de
socios resuelve el estado de todos con un número fijo de consultas
([listado en lote](A-11-rendimiento.md#listado-en-lote)).

`estado_de_reserva()` (`backend/turnos.py:78`) muestra la misma preocupación desde el otro lado.
Recibe como parámetro si la persona asistió, en vez de consultarlo adentro, y su docstring explica
por qué: *"el panel muestra decenas de reservas y resolverlo fila por fila sería una consulta por
cada una. Quien llama trae el conjunto de una y esta función queda pura — sin base de datos, fácil
de probar."* La derivación queda pura, sin tocar la base, y el costo de las consultas lo absorbe
quien la llama, en lote.

### El caso híbrido: derivar y, de paso, escribir

Hay una función que hace las dos cosas a la vez. `_membresia_vigente()` en
`backend/routers/cobros.py:106` busca la membresía activa más reciente, y al pasar **marca como
`VENCIDA`** las que ya pasaron su fecha (líneas 124-125). El docstring dice por qué (líneas
110-112): *"sin una tarea programada que las revise, el estado en la base se queda viejo, y
'activa pero vencida hace tres meses' es peor que no tener el campo."*

Es una escritura **perezosa**: la columna se corrige recién cuando alguien pasa por ese camino. Por
eso ninguna pantalla confía en que `ACTIVA` quiera decir vigente. El cálculo del estado del socio,
que se ve en la sección siguiente, vuelve a mirar la fecha siempre, esté o no corregida la columna.

(Un detalle de nombres: hay **dos** funciones llamadas `_membresia_vigente`, en dos routers, y no
hacen lo mismo. La de `cobros.py` devuelve la **activa** más reciente y corrige las vencidas; la de
`backend/routers/socios.py:87` devuelve la más reciente **en cualquier estado** y no escribe nada.
Como son privadas de cada módulo no chocan, pero el mismo nombre para dos criterios distintos es
una trampa para quien las lea juntas.)

### Por qué está hecho así

**Qué se optimiza:** que ningún estado que dependa del paso del tiempo pueda estar mal en pantalla.

**Qué se descartó:** la tarea programada que actualiza estados. Este backend no tiene un
planificador de tareas, y agregarlo para mantener columnas al día sería agregar una pieza que falla
en silencio para resolver un problema que un cálculo resuelve sin fallar.

**Qué se paga:** consultas en cada lectura, que se compensan cargando en lote; y la disciplina de
que **una regla de derivación viva en un solo lugar**. Qué pasa cuando esa disciplina se rompe es la
nota del final del capítulo.

**Cómo se llama:** derivar en vez de almacenar. La regla práctica para reconocer cuándo aplica está
en [estado guardado](#estado-guardado).

---

## Los seis estados del socio y su precedencia

### La función

El estado que se ve en la píldora de la grilla de socios lo calcula una sola función,
`_estado_socio()` (`backend/routers/socios.py:97-129`). Recibe el socio y su membresía más
reciente, y devuelve una de seis etiquetas, definidas como constantes en las líneas 79-84: `Activo`,
`Por vencer`, `Vencido`, `Suspendido`, `Sin membresía`, `Dado de baja`.

> **↓ Capa 1 — el orden de los chequeos.** Este es el piso del concepto.

La función es una cascada: pregunta en orden, y la primera condición que se cumple decide. El
código, del dueño al detalle:

| # | Si… | Etiqueta | Líneas |
|---|---|---|---|
| 1 | el socio no está activo (`socio.activo` es falso) | **Dado de baja** | 110-111 |
| 2 | no tiene ninguna membresía | **Sin membresía** | 112-113 |
| 3 | la membresía está `SUSPENDIDA` | **Suspendido** | 114-115 |
| 4 | la membresía está `VENCIDA` o `CANCELADA` | **Vencido** | 116-117 |
| 5 | está `ACTIVA` y no tiene fecha de vencimiento | **Activo** | 121-122 |
| 6 | está `ACTIVA` y faltan… menos de cero días | **Vencido** | 124-126 |
| | …entre cero y siete días | **Por vencer** | 127-128 |
| | …más de siete | **Activo** | 129 |

### Por qué el orden importa

El docstring (líneas 106-108) lo resume en un ejemplo: *"'dado de baja' gana sobre cualquier estado
de membresía. Alguien de baja con la cuota paga sigue estando de baja."*

Invertir dos filas de la tabla cambia la respuesta en casos reales. Si el chequeo 6 fuera antes que
el 1, un socio dado de baja con la cuota paga hasta fin de mes aparecería como "Activo". Si el 4
fuera antes que el 3, una membresía en pausa podría leerse como vencida. La precedencia **es** la
regla; las condiciones sueltas, sin su orden, no dicen nada.

Y el caso 5 tiene una sutileza escrita en su comentario (líneas 119-120): una membresía sin fecha de
vencimiento *"no puede estar 'por vencer' — no hay fecha contra la cual calcularlo"*.

### Seis niveles, siete etiquetas: "En pausa"

`CLAUDE.md` enumera siete etiquetas, y el `EstadoSocio` de la PWA (`config.ts:684-696`) declara
siete. El backend define seis. No hay contradicción: son **seis niveles de precedencia y siete
palabras**, porque el nivel 3 tiene dos nombres. Una membresía `SUSPENDIDA` se llama **"Suspendido"**
en la grilla del personal y **"En pausa"** en el portal del socio.

Lo que decide qué palabra se usa es **quién mira**. El portal la dice "En pausa" en dos lugares, los
dos con la misma lógica (`backend/routers/portal.py:173-174` y `860-864`), y la grilla del personal la
dice "Suspendido" con `_estado_socio()`. El motivo de tener dos palabras está en `config.ts:689-692`:
*"'Suspendido' se lee como un castigo y el socio que pausó su cuota por dos semanas de vacaciones no
merece esa palabra"*.

El portal agrega otra razón, que explica por qué la pausa se chequea **antes** que las fechas
(`portal.py:168-172`): *"mientras está congelada el reloj no corre, así que 'faltan 90 días' o 'por
vencer' serían igual de engañosos. Sin esto, Mi perfil decía 'Activo' mientras Mi cuota decía 'En
pausa' — dos pantallas del mismo socio contándole cosas distintas."*

### Nota marcada · lo que dicen los comentarios sobre la pausa

Dos comentarios no coinciden del todo con el código:

- `config.ts:689-692` justifica las dos palabras con *"Quien suspende es el gimnasio; quien pausa es el
  socio"*. En el código **no existe una suspensión decidida por el gimnasio**: el único lugar que crea
  un `Congelamiento` es el portal, cuando el socio pausa su propia cuota (`portal.py:1994`). Toda
  membresía `SUSPENDIDA` de hoy la pausó su socio, y la diferencia entre las dos palabras es de
  audiencia, no de quién la pidió.
- El comentario de `socios.py:77` habla de *"Los seis estados posibles"* y lo presenta como espejo del
  `EstadoSocio` de la PWA, que tiene siete. Los seis del backend son los niveles; la séptima palabra
  sólo la usa el portal.

Gana el código en los dos casos.

### Las etiquetas viajan como texto

Un detalle de diseño que parece menor: los estados no viajan como códigos (`"POR_VENCER"`) sino como
el texto final, con tilde y todo (`"Sin membresía"`). El comentario de `socios.py:77-78` lo explica:
*"los valores viajan en castellano porque son literalmente el texto de la píldora"*.

La consecuencia está escrita del lado de la PWA (`config.ts:680-683`): el cliente usa ese texto para
elegir el color de la píldora, así que *"el literal tiene que ser el mismo de los dos lados o el badge
cae al color neutro sin avisar"*. Una tilde de menos en el backend no rompe nada visible salvo el
color, que pasa a gris.

---

## Vencido el día siguiente

### La comparación exacta

`CLAUDE.md` lo dice como regla: *"Queda vencido el día siguiente al vencimiento."* En el código es
una resta de fechas y dos comparaciones (`backend/routers/socios.py:124-129`):

```python
dias = (membresia.fecha_vencimiento - date.today()).days
if dias < 0:
    return ESTADO_VENCIDO
if dias <= DIAS_AVISO_VENCIMIENTO:
    return ESTADO_POR_VENCER
return ESTADO_ACTIVO
```

Éste es el piso. Con una membresía que vence el 30 de septiembre:

| Día | `dias` | Estado |
|---|---|---|
| 22 de septiembre | 8 | Activo |
| 23 de septiembre | 7 | Por vencer |
| 30 de septiembre | **0** | **Por vencer** |
| 1 de octubre | **−1** | **Vencido** |

El día del vencimiento da cero, y cero no es menor que cero: todavía está pago. El socio pasa a
"Vencido" recién al día siguiente. **La fecha de vencimiento es el último día cubierto, no el primero
sin cubrir.**

La regla que decide si se puede cobrar usa el mismo criterio con otra comparación —un `>=` contra el
día de hoy—, y está explicada en
[la escala 16 del recorrido](A-04-recorrido-de-un-pedido.md#escala-16--la-regla-de-negocio). Las dos
tienen que coincidir: si una considerara vencido el día 30 y la otra no, habría un día en el que el
socio figura "Vencido" y el sistema no le deja pagar.

### La ventana de "Por vencer"

Los siete días de aviso los fija `DIAS_AVISO_VENCIMIENTO`, y el comentario que la define
(`backend/routers/socios.py:73-74`) da el motivo de negocio: *"una semana, para que el mostrador llame a
tiempo"*. Es el estado que existe porque no hay renovación automática: si nadie hace nada, la cuota
vence, y "Por vencer" es la oportunidad de hacer algo antes.

### El siete, en un solo lugar del backend

Escribiendo este capítulo, la constante estaba en tres lugares: definida en `socios.py`, **copiada** en
`backend/routers/dashboard.py` con su propio siete, y exportada en el `config.ts` de la PWA. Dos copias en el
backend quieren decir que el día que el dueño decida avisar con diez días, alcanza con olvidarse de una para
que la grilla y el dashboard no se pongan de acuerdo.

Se corrigió: el backend tiene hoy **una sola definición**, `socios.py:75`, y el dashboard la importa
(`dashboard.py:49`), en el mismo lugar donde antes estaba la copia. Queda el siete del `config.ts:702` de la
PWA, que está exportado y **ninguna pantalla importa**: no puede desincronizar nada, porque nada lo lee.

---

## Estado guardado

### Qué sí se guarda

No todo estado se deriva. En la base hay nueve tablas con columna de estado, y siete enumerados que
definen sus valores (`db/schema.sql:62-68`):

| Enumerado | Valores | Tabla |
|---|---|---|
| `estado_membresia` | `ACTIVA`, `VENCIDA`, `SUSPENDIDA`, `CANCELADA` | `Membresia` |
| `estado_pago` | `CONFIRMADO`, `PENDIENTE`, `CANCELADO`, `REEMBOLSADO` | `Pago` |
| `estado_reserva` | `RESERVADA`, `EN_ESPERA`, `CANCELADA_SOCIO`, `CANCELADA_GIMNASIO` | `Reserva` |
| `estado_turno` | `HABILITADO`, `CANCELADO` | `Turno` |
| `estado_inscripcion` | `ACTIVA`, `VENCIDA`, `CANCELADA` | `Inscripcion_Actividad` |
| `estado_congelamiento` | `ACTIVO`, `FINALIZADO`, `CANCELADO` | `Congelamiento` |
| `estado_asignacion` | `ACTIVA`, `FINALIZADA`, `CANCELADA` | `Asignacion_Entrenador`, `Asignacion_Rutina`, `Asignacion_Dieta` |

Éste es el piso del concepto: la columna `estado`, con su enumerado.

### La prueba para decidir

La diferencia con el estado del socio es de naturaleza, y se puede formular como una pregunta: **¿este
valor lo decidió alguien, o es la consecuencia de que pasó el tiempo?**

- Un pago **cancelado** lo canceló una persona. Una reserva **cancelada por el gimnasio** la canceló el
  gimnasio, y eso es distinto de que la cancele el socio. Un turno **cancelado**, una asignación
  **finalizada**, una pausa **activa**: todas son decisiones. Nada en la base permite reconstruirlas si
  no se guardan, porque el hecho de que alguien decidió no deja otro rastro.
- Que una membresía **ya venció**, o que alguien **faltó** a una clase, no lo decidió nadie: es la
  consecuencia de comparar una fecha con el reloj. Eso se deriva.

**Las decisiones se guardan; las consecuencias del tiempo se calculan.**

### El caso que muestra la regla: la reserva sin "asistió"

`estado_reserva` es el ejemplo más limpio de la prueba bien aplicada. Guarda que la reserva existe, que
está en lista de espera y quién la canceló —decisiones—, y **deliberadamente no guarda si la persona
fue**. `backend/turnos.py:13-17`:

> *"`estado_reserva` tiene RESERVADA, EN_ESPERA y las dos cancelaciones. NO tiene 'ASISTIO' ni 'AUSENTE',
> y es deliberado: asistió → hay una fila en Asistencia con id_reserva = esta reserva; ausente → ya pasó
> hora + tolerancia y no hay ninguna."*

"Asistió" se deriva de que exista un fichaje, y "ausente", del reloj.

### El caso que la tensiona: `VENCIDA`

`estado_membresia` mezcla las dos naturalezas. `ACTIVA`, `SUSPENDIDA` y `CANCELADA` son decisiones:
alguien cobró, alguien pausó, alguien anuló. Las escrituras en el backend lo confirman: `SUSPENDIDA` la
escribe la pausa del portal (`portal.py:2010`), `ACTIVA` la reanudación (`portal.py:1870`), `CANCELADA` la
anulación de un pago (`cobros.py:515`) y la baja (`backend/bajas.py:109`).

`VENCIDA`, en cambio, **es una consecuencia del tiempo guardada en una columna**. Y por eso es la única
que se escribe de forma perezosa ([el caso híbrido](#el-caso-híbrido-derivar-y-de-paso-escribir)), y la
única en la que el cálculo del estado del socio no confía: `_estado_socio()` trata `ACTIVA` con fecha
pasada como vencida, esté o no marcada. El enumerado tiene un valor que, por la prueba de arriba, no
debería estar guardado; el código lo compensa volviendo a mirar la fecha siempre.

---

## Regla resuelta en el backend

### La mudanza de la regla

El estado del socio no siempre se calculó en el servidor. `Proyecto - PWA/src/frontend/src/services/sociosService.ts:7-13`
cuenta la historia:

> *"El `estado` y el `plan` YA VIENEN resueltos del backend. Antes se derivaban acá (estadoDeSocio en
> membresiaService), pero esa regla —los 7 días de aviso, qué gana entre 'de baja' y 'vencido'— tiene que
> valer igual en la PWA, en Flet y en cualquier reporte. Con la derivación en el servidor hay una sola
> versión de la verdad; con la derivación en el cliente había que mantener la misma lógica en tres lugares
> y el día que cambie, dos se olvidan."*

Y el docstring de `_estado_socio()` lo confirma desde el otro lado (`socios.py:101-104`): es *"el port
exacto de `estadoDeSocio`"* de la PWA, mudado al backend *"porque si no habría que mantener la misma regla
en tres lugares"*. La función de la PWA ya no existe.

### El campo que la pantalla recibe resuelto

Éste es el piso: la pantalla no calcula nada. Recibe `estado` ya resuelto —`"Por vencer"`, con su texto
final— y sólo decide de qué color pintarlo. Lo mismo hace la decisión de si se puede cobrar, que viaja
con su motivo redactado (`puede_renovar` y `motivo_no_renovar`); cómo y por qué está en el bloque de
ingeniería inversa de
[la escala 16 del recorrido](A-04-recorrido-de-un-pedido.md#escala-16--la-regla-de-negocio).

El principio es el mismo que separa [lo que se esconde de lo que se rechaza](A-08-autorizacion.md#el-frontend-esconde-el-backend-rechaza):
**el servidor decide, el cliente muestra.** Una regla que se decide en un solo lugar no puede contradecirse
consigo misma.

### El dashboard que derivaba por su cuenta

La regla estuvo en un solo lugar para todas las pantallas **salvo una**, y el caso vale como lección. La
tarjeta de "socios recientes" del dashboard, `socios_recientes()` (`backend/routers/dashboard.py:350`, detrás
de `GET /dashboard/socios-recientes`), no llamaba a `_estado_socio()`: armaba el estado con su propia versión
de la regla, más corta. Miraba sólo membresías `ACTIVA`, no distinguía la ausencia de membresía, no miraba
si el socio estaba dado de baja, y cuando no encontraba una membresía activa con fecha contestaba "Vencido".
Su docstring decía usar *"el mismo criterio que usa la sección Cobros"*; implementaba tres de los seis
niveles.

El resultado era el mismo socio con dos estados en dos pantallas:

| Socio | Grilla de Socios | Dashboard, antes | Dashboard, hoy |
|---|---|---|---|
| con la cuota en pausa | Suspendido | **Vencido** | Suspendido |
| con una membresía sin vencimiento | Activo | **Vencido** | Activo |
| sin ninguna membresía | Sin membresía | **Vencido** | Sin membresía |
| dado de baja | Dado de baja | **Vencido** | Dado de baja |

El caso más visible era el tercero, porque la tarjeta muestra **las últimas altas**, y un socio recién dado
de alta todavía no tiene plan: aparecía en rojo como vencido.

Era exactamente el problema que la mudanza de la regla al backend quería resolver —*"el día que cambie, dos
se olvidan"*—, y había reaparecido **adentro del backend**: dos funciones del servidor derivaban el mismo
estado de dos maneras. Se corrigió como lo hace la grilla: la tarjeta ahora usa `_membresia_vigente()` y
`_estado_socio()` de `socios.py` (`dashboard.py:370` y `376`). Se verificó corriendo la función real sobre una
base en memoria con siete casos —los cuatro de la tabla más vencido, por vencer y al día—, comparando en cada
uno la respuesta de la tarjeta con la de `_estado_socio()`: coinciden los siete.

---

## Con qué se conecta

- **Es la misma idea que…** las [clases restantes](A-02-prepago-puro.md#clase-suelta-y-abono-de-actividad):
  un saldo que se cuenta en cada lectura en vez de guardarse, para que no haya contador que se desincronice.
- **Existe por culpa de…** que el sistema casi no tiene procesos que corran solos: el único es el
  [latido](A-11-rendimiento.md#latido), y derivar es lo que evita necesitar otro.
- **Es el mismo problema que…** el [N+1](A0-09-el-orm.md#n1): derivar cuesta consultas por fila, y sin carga
  en lote el precio crece con cada socio.
- **Se contradice con…** `estado_membresia`, que guarda `VENCIDA`, una consecuencia del tiempo; el código lo
  compensa volviendo a mirar la fecha.
- **Es la misma idea que…** [el frontend esconde, el backend rechaza](A-08-autorizacion.md#el-frontend-esconde-el-backend-rechaza):
  el servidor decide y la pantalla muestra.
- **Es la misma idea que…** la [promoción porcentual](A-02-prepago-puro.md#promoción-porcentual): las dos
  reglas se escriben contra una fecha del período y no contra el día del trámite —el estado, contra el
  último día cubierto; la promoción, contra el inicio del período cobrado—.
