# B-07 · Recepción

*Procesos 57 a 59. Piso del capítulo: la línea que implementa cada paso, en las tres capas.*

Tres procesos, y ninguno es una operación: los tres **leen**. Es el capítulo más chico de la Parte B
y a la vez el único donde el corte de la API no sigue a las entidades sino a **una pantalla**.

| Tema | Procesos |
|---|---|
| El panel, y el turno que se expande | 58, 59 |
| La búsqueda que cierra la conversación | 57 |

Por eso el capítulo se lee distinto a los demás: no hay validaciones ni rechazos que enumerar —hay
un 404 en total— y todo el interés está en **por qué estos tres endpoints existen** cuando los datos
que devuelven ya viven en `/actividades` y `/asistencia`.

Lo que hay que traer de la Parte A: qué es un
[backend for frontend](A-01-que-es-olimpos.md#menos-pasos-y-más-completo), por qué el
estado de una reserva se deriva en vez de guardarse
([estado derivado](A-09-estados-derivados.md#estado-derivado)), y qué significa que el mostrador
tenga cola ([el mostrador con cola](A-01-que-es-olimpos.md#el-mostrador-con-cola)).

**Y una particularidad que conviene saber antes de leer:** el backend de esta sección está **entero**
y la PWA consume **uno** de los tres endpoints. La pantalla completa existe sólo en Flet, y el dueño
la pidió también para la web. Es el pendiente más grande del repo que no es una función nueva sino
una pantalla que falta, y está anotado en `docs/ESTADO-ACTUAL.md`.

**Lo que se corrió, y cómo.** Nada: es lectura. Los tres procesos son `GET` sin efectos, así que lo
único que correrlos probaría es el conteo de consultas — y ése se puede leer, que es lo que hace la
nota marcada del proceso 58.

---

## Piezas comunes

### Un router organizado por pantalla, no por entidad

Éste es el porqué del capítulo, y está en el encabezado del módulo
(`backend/routers/recepcion.py:6-22`). Los endpoints de `/actividades` y `/asistencia` están
organizados por **entidad** —esto es un turno, esto es una asistencia—, *"que es lo correcto para una
API"*. Este router está organizado por **pantalla**: devuelve, en un solo pedido, todo lo que el
recepcionista necesita ver al mismo tiempo.

El docstring da dos razones, y la segunda es la que no se ve venir:

**La latencia.** El panel se refresca solo cada pocos segundos. Armarlo con los endpoints por
entidad serían *"cuatro o cinco pedidos por refresco, cada uno con su latencia"*. Contra una base en
São Paulo eso son varios cientos de milisegundos por refresco
([base remota](A-11-rendimiento.md#base-remota)).

**La consistencia.** Y *"—peor— con la posibilidad de que la lista de turnos llegue de un instante y
la de asistencias de otro, mostrando a alguien como ausente en un turno que ya se le acreditó"*.
Cuatro pedidos son cuatro fotos de momentos distintos; una pantalla que las mezcla puede mostrar un
estado que nunca existió. Un solo pedido es **una** foto.

Esa segunda razón es la importante, porque es la que no se arregla con más velocidad. Un
[backend for frontend](A-01-que-es-olimpos.md#menos-pasos-y-más-completo) se suele
justificar por rendimiento; acá además compra **atomicidad de lectura**, que es lo único que hace
que el panel se pueda creer.

La regla que cierra el docstring ordena todas las decisiones del módulo: *"el recepcionista no
debería tener que BUSCAR nada. La información llega ordenada por urgencia, con la acción al lado, y
las advertencias (cuota vencida, deuda) ya resueltas del lado del servidor para que no tenga que
abrir otra pantalla a confirmarlas."* Es
[el mostrador con cola](A-01-que-es-olimpos.md#el-mostrador-con-cola) convertido en diseño de API.

### Tres constantes que son decisiones

El módulo abre con tres números, y los tres tienen su porqué escrito al lado — que es lo que los
distingue de configuración arbitraria:

| Constante | Valor | Por qué ese valor | Línea |
|---|---|---|---|
| `HORAS_ADELANTE` | 6 | *"más que eso llena la pantalla de cosas que no van a pasar en este rato, y el mostrador deja de mirarla"* | `recepcion.py:48-51` |
| `MINUTOS_MOSTRAR_VENCIDOS` | 60 | *"para que el mostrador pueda explicar por qué alguien reclama una clase que ya no figura arriba, no para poder marcarla: eso ya no se puede"* | `:53-56` |
| `CUPO_SALA_ABIERTA` | 25 | el umbral que separa una clase de la sala de musculación | `:58-65` |

La tercera es la más interesante, porque explica una decisión de modelado que **no** se tomó
(`:61-65`): *"El umbral es por cupo y no por un flag en la tabla a propósito: no hace falta que nadie
marque nada, y una clase de 15 nunca se confunde con la sala de 40. Si algún día hace falta
distinguirlo con precisión, se agrega la columna; hoy sería configuración que nadie va a tocar."*

Es [YAGNI](A-98-glosario.md#patrones-con-nombre) argumentado de la forma correcta: no *"no lo
necesitamos"*, sino *"el dato que haría falta ya está implícito en otro, y pedirle a alguien que lo
marque agrega un paso que se va a olvidar"*. Lo que se paga: una clase de 30 personas con profesor
se seguiría listando entera —la condición pide además `id_profesor is None` (`:126`)—, y una sala sin
profesor de cupo 20 se listaría nombre por nombre. Los dos casos son improbables en este gimnasio y
el costo de equivocarse es cosmético.

### La alerta del socio, resuelta en el servidor

`_alerta_de_socio()` (`recepcion.py:72-108`) devuelve *"lo que el mostrador tiene que decirle a esta
persona cuando aparezca"*, y su docstring dice por qué vive acá: *"hacerlo por fila en el cliente
serían dos consultas por cada persona anotada en el turno"*.

| Condición | La alerta | Línea |
|---|---|---|
| El socio está dado de baja | *"Socio dado de baja."* | `:80-81` |
| Sin membresía `ACTIVA` | *"Sin membresía activa."* | `:92-93` |
| La membresía venció | *"Cuota vencida hace N día(s)."* | `:95-97` |
| Vence en 3 días o menos | *"La cuota le vence en N día(s)."* | `:104-106` |
| Todo en orden | `None` | `:108` |

Las tres primeras son las mismas de `_revisar_situacion()` del fichaje
([B-06](B-06-asistencia.md#52-fichar-el-ingreso-de-un-socio)) y con el mismo orden de precedencia. La
cuarta es propia de este módulo y es la que tiene la decisión de negocio (`:100-103`): *"Aviso
temprano: es el único momento en que se tiene la atención de la persona, y avisarle tres días antes
evita el corte en seco del día que vence. Es un aviso, no un cobro: la cuota se renueva recién cuando
vence, así que se le avisa para que vuelva ese día."*

Esa última frase es la que evita la contradicción con
[sin cobros por adelantado](A-02-prepago-puro.md#sin-cobros-por-adelantado): el aviso no habilita el
cobro. Y por eso, al lado de cada anotado, viaja además `puede_cobrar_cuota`, que sale de
`estado_renovacion()` (`backend/renovacion.py:56-105`) — la misma función que decide si el botón de
Cobros aparece. El mostrador ve *"le vence en 2 días"* y **no** ve el botón de cobrar, y las dos
cosas son correctas.

**Nota marcada · dos consultas por anotado, y son las que el docstring quería evitar.**
`_alerta_de_socio()` hace una consulta a `Membresia` (`:87-91`) y `estado_renovacion()` hace las
suyas, y las dos se llaman **dentro del bucle** de inscriptos
(`recepcion.py:144-145`). El docstring dice que se
resuelve en el servidor *"porque hacerlo por fila en el cliente serían dos consultas por cada
persona"* — y en el servidor también son por fila: lo que se ahorró es la **latencia de red** de cada
una, no la consulta. Con veinte anotados en el turno son cuarenta consultas contra São Paulo, y el
panel se refresca cada diez segundos (`Flet/Proyecto/app/views/recepcion.py:29-31`). El remedio es el
mismo de los otros listados: traer las membresías de todos los anotados en una consulta y pasarlas
por parámetro, exactamente como ya hace `reservas_con_asistencia()` en el mismo archivo. Leído, no
medido.

### El estado de cada anotado no sale de ninguna columna

Los cinco estados que muestra el panel —*"Falta llegar"*, *"Presente"*, *"No llegó"*, *"En espera"*,
*"Canceló"*— los deriva `estado_de_reserva()` (`backend/turnos.py:78-103`), y el comentario de Flet
explica la consecuencia mejor que ninguna otra parte del repo
(`views/recepcion.py:33-38`): *"Por eso no hay forma de que la pantalla muestre 'pendiente' en un
turno que venció hace una hora — si el reloj avanza, la respuesta cambia sola."*

`estado_de_reserva()` recibe `asistio` **por parámetro** en vez de consultarlo, y su docstring dice
por qué (`turnos.py:82-86`): *"el panel muestra decenas de reservas y resolverlo fila por fila sería
una consulta por cada una. Quien llama trae el conjunto de una y esta función queda pura — sin base
de datos, fácil de probar."* Es el patrón que la nota marcada de arriba dice que falta aplicar a la
alerta: **la función pura recibe los datos, el llamador los trae en lote.** Acá está bien hecho para
la asistencia y no para la membresía, en el mismo bucle.

---

## Los tres procesos

### 58. Abrir el panel de recepción

`GET /recepcion/panel` · Dueño, Recepcionista

**Qué resuelve.** Lo primero que ve el recepcionista al entrar y lo único que necesita mirar durante
el día: quién está por llegar, quién ya llegó, y a quién hay que decirle algo cuando aparezca.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Endpoint | `backend/routers/recepcion.py` | 175-244 | `panel()` |
| Armado del turno | `backend/routers/recepcion.py` | 111-168 | `_a_turno_de_panel()` |
| Alerta del socio | `backend/routers/recepcion.py` | 72-108 | `_alerta_de_socio()` |
| Estado de cada anotado | `backend/turnos.py` | 78-103 | `estado_de_reserva()` |
| Asistencias en lote | `backend/turnos.py` | 106-122 | `reservas_con_asistencia()` |
| Si se le puede cobrar | `backend/renovacion.py` | 56-105 | `estado_renovacion()` |
| Esquemas | `backend/schemas.py` | 1959-2021 | `InscriptoEnTurno`, `TurnoDePanel`, `PanelRecepcion` |
| Vista Flet | `Flet/Proyecto/app/views/recepcion.py` | 69-106, 424-592 | `build()`, `_resumen()`, `_lista_de_turnos()`, `_turno()`, `_inscripto()` |
| Refresco Flet | `Flet/Proyecto/app/views/recepcion.py` | 118-170 | `_arrancar_refresco()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1440-1490 | `get_panel_recepcion()`, `_turno_panel()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 795-809 | `obtener_panel_recepcion()` |
| Vista PWA | — (no existe) | | pendiente pedido por el dueño |

**Cómo funciona.** El endpoint, en orden:

1. **Los turnos de hoy y de ayer**, habilitados, ordenados por fecha y hora (`:195-205`). Lo de ayer
   tiene el mismo motivo que en el fichaje y está comentado: *"un turno de las 23:30 con tolerancia
   sigue vivo pasada la medianoche, y filtrar sólo por hoy lo perdería justo en el momento en que el
   mostrador más lo necesita."*
2. **Cada turno se clasifica en dos listas** (`:210-222`), comparando el instante actual con
   `vence_a()`:
   - **Todavía se puede llegar** y empieza dentro de las 6 horas → `turnos`.
   - **Ya venció** pero hace menos de 60 minutos → `vencidos_recientes`.
   - Todo lo demás no se muestra.
3. **El orden de cada lista** (`:224-225`): los próximos por cercanía ascendente; los vencidos al
   revés, el más reciente primero. Cada uno ordenado por lo que el mostrador va a necesitar antes.
4. **Los totales del día** (`:227-237`), y acá hay una sutileza anotada: *"Los totales del día miran
   SÓLO hoy, aunque arriba se hayan traído los de ayer: son el resumen de la jornada, y sumarle la
   cola de anoche haría que el número no cierre con lo que el mostrador vio pasar."* Dos consultas de
   agregación, `count()` sobre `Reserva` y sobre `Asistencia`.

**La lista de vencidos es de sólo lectura, y es una decisión.** El docstring lo dice (`:186-190`):
*"van en `vencidos_recientes`, que existe sólo para poder explicar el reclamo de alguien que llegó
tarde. Desde ahí no se puede marcar a nadie — el turno venció y ya está."* Es lo contrario de lo que
haría una pantalla pensada para "arreglar" datos: la ventana de una hora existe para **sostener una
conversación**, no para reabrir una decisión que el reloj ya tomó.

**El colapso de la sala abierta** (`:126-128`, `:130-133`): un turno sin profesor y con cupo ≥ 25 no
lista a sus anotados. El comentario da el porqué: *"40 nombres taparían las clases de 15, que son
donde el cupo importa de verdad. Los contadores igual se calculan, así la línea muestra 'Musculación
18:00 — 23 anotados' y se puede expandir pidiendo ese turno puntual."* Ese "expandir" es el proceso
59, y es la única razón por la que existe.

**El orden de los anotados** (`:146-150`) es la regla del módulo aplicada a una lista: *"Los que
faltan llegar primero: son sobre los que el mostrador puede hacer algo. Los que ya asistieron y los
ausentes van al final."* El criterio de orden no es alfabético ni cronológico: es **por
accionabilidad**.

**Qué escribe y qué lee.** No escribe nada. Lee:

| Tabla | Atributos | Línea |
|---|---|---|
| `Turno` | `id_turno`, `id_actividad`, `fecha`, `hora`, `estado`, `cupo_maximo`, `id_profesor` | `:198-202`, `:126`, `:155-163` |
| `Actividad` | `nombre`, `minutos_tolerancia` | `:199`, `:157`, vía `vence_a()` en `turnos.py:74-75` |
| `Reserva` | `id_turno`, `id_socio`, `id_inscripcion`, `estado`, `fecha_reserva` | `:114-117`, `:121-122`, `:135` |
| `Asistencia` | las que acreditan una reserva; y el total del día | `turnos.py:115-121`, `recepcion.py:234-236` |
| `Socio` | `id_socio`, `id_persona`, `activo` | `:136`, `:80` |
| `Persona` | `nombre`, `apellido`, `dni` | `:139-140` |
| `Membresia` | `id_socio`, `estado`, `fecha_vencimiento` | `:87-91` |
| `Profesor`, `Empleado`, `Persona` | el nombre del profesor a cargo | `:164-165` |

**Discrepancia con la línea DFD.** La línea declara `Baja` (`id_socio`, `fecha_baja`, `pendiente`)
entre lo que se lee, y el código **no la toca**: `_alerta_de_socio()` mira `Socio.activo`, no la fila
de `Baja`. Es una lectura de más en la especificación, no en el código. (Lo mismo vale para los
procesos 57 y 59, que declaran `Baja` por la misma razón: comparten `_alerta_de_socio()`.)

**Por qué está hecho así.** El grueso está en las piezas comunes: un endpoint por pantalla, por
latencia y sobre todo por consistencia. Lo propio de este proceso son dos elecciones:

**La ventana de 6 horas contra "todo el día".** Devolver todos los turnos del día sería una consulta
igual de barata y una pantalla inútil: a las 9 de la mañana, la clase de las 21 no es información,
es ruido. Lo que se paga es que un turno que empieza en 7 horas no se ve, y si el recepcionista
quiere planificar tiene que ir a la agenda ([B-08](B-08-actividades-turnos-horarios.md)). La
separación es deliberada: **el panel es para el rato que viene, la agenda es para la semana.**

**El refresco lo hace el cliente, no un canal abierto.** Flet lo resuelve con un hilo que vuelve a
pedir el panel cada diez segundos (`views/recepcion.py:118-170`), y el número está argumentado
(`:26-31`): *"suficiente para que un ingreso aparezca antes de que la persona termine de guardar la
tarjeta, y lo bastante espaciado como para que sean seis pedidos por minuto desde una sola máquina —
nada."* La alternativa era un WebSocket o SSE, que daría actualización instantánea y obligaría a
mantener una conexión viva, un canal en el backend y una reconexión cuando la PC del mostrador
suspenda. Para una máquina y un dato que tolera diez segundos de atraso, el sondeo gana por
simplicidad. El patrón: **sondeo con intervalo justificado**, y lo que se paga es hasta diez segundos
de atraso en el peor caso.

**Qué pasa cuando sale mal.** Sólo 403, para los cuatro roles sin la sección `ASISTENCIA`. Sin
turnos en la ventana devuelve las dos listas vacías y los totales en cero, que es exactamente lo que
la línea DFD declara.

---

### 59. Ver el detalle de un turno del panel

`GET /recepcion/turnos/{id_turno}` · Dueño, Recepcionista

**Qué resuelve.** Expandir la línea colapsada de la sala abierta: los 40 nombres que el panel no
lista.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Endpoint | `backend/routers/recepcion.py` | 247-275 | `detalle_de_turno()` |
| Lista completa | `backend/routers/recepcion.py` | 278-301 | `_inscriptos_de()` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/turnosService.ts` | 205-213 | `getDetalleTurno()` |
| Componente PWA | `Proyecto - PWA/src/frontend/src/components/AgendaTurnos.tsx` | 53-233 | `AgendaTurnos` (el pedido, 87) |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1558-1560 | `get_detalle_turno()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 812-813 | `obtener_turno_detalle()` |

**Cómo funciona.** Busca el turno con su actividad, o 404 (`:262-269`); arma el `TurnoDePanel` con la
misma función que el panel (`:272`); y **si es sala abierta, reemplaza la lista** por la completa
(`:273-275`). El comentario dice por qué la regla de colapso no aplica: *"se pidió este turno
explícitamente, o sea que alguien quiere ver la lista completa."*

`_inscriptos_de()` (`:278-301`) es casi una copia del bucle de `_a_turno_de_panel()`, sin la
condición de colapso. Es duplicación deliberada y chica —veinte líneas— contra la alternativa de
meterle un parámetro más a la función del panel; discutible en cualquier dirección, y sin
consecuencia funcional.

**Qué escribe y qué lee.** Lo mismo que el proceso 58 para un turno solo. Coincide con la línea DFD,
con la misma discrepancia de `Baja`.

**Por qué está hecho así.** Existe **sólo** por el colapso de la sala abierta: sin esa regla, el
panel ya traería todo y este endpoint no haría falta. Es un buen ejemplo de una decisión de UI
—no tapar las clases chicas con 40 nombres— que se paga con un endpoint más en la API.

**Nota marcada · el único de los tres que la PWA usa, y para otra cosa.** La PWA lo llama desde
`AgendaTurnos` (`turnosService.ts:205-213`, el pedido en `AgendaTurnos.tsx:87`) para mostrar los
anotados de un turno de la **agenda**, que es una pantalla distinta del panel del mostrador. O sea:
de los tres endpoints de este router, la PWA consume el único que no necesita el panel para tener
sentido. Los otros dos —el panel y la búsqueda— **no los llama nadie** desde la web. Lo que falta
para cerrarlo está en `docs/ESTADO-ACTUAL.md`: la ruta, el ítem de menú, los dos servicios y la
matriz de permisos en sus tres copias (hoy `RECEPCION` sólo existe en la de Flet, y
`backend/check_permisos.py:52` explica por qué eso no es una inconsistencia: *"no un area nueva de
permisos"*, porque los endpoints están protegidos por `ASISTENCIA`).

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| El turno no existe | 404 | *"El turno no existe."* | `recepcion.py:267-269` |

Coincide con la línea DFD. Es el único rechazo de todo el capítulo.

---

### 57. Buscar un socio por DNI en el mostrador

`GET /recepcion/buscar` · Dueño, Recepcionista

**Qué resuelve.** Alguien llega al mostrador sin turno, o con una pregunta. Se tipea su DNI y vuelve
todo lo que el recepcionista iba a preguntar después.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Endpoint | `backend/routers/recepcion.py` | 308-384 | `buscar()` |
| Esquema | `backend/schemas.py` | 2024-2045 | `ResultadoBusqueda` |
| Vista Flet | `Flet/Proyecto/app/views/recepcion.py` | 172-228, 230-303 | `_buscador()`, `_buscar()`, `_ficha()` |
| Acciones Flet | `Flet/Proyecto/app/views/recepcion.py` | 305-420 | `_fichar()`, `_cobrar()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 822-823 | `buscar_por_dni()` |
| Vista PWA | — (no existe) | | pendiente pedido por el dueño |

**Cómo funciona.** Busca por coincidencia parcial de DNI, hasta 10 resultados, ordenados por apellido
y nombre (`:329-335`). Para cada socio arma:

1. **El estado de la membresía** (`:340-350`), en tres valores: *"Sin membresía"*, *"Vencida"*,
   *"Activa"*.
2. **Su próximo turno** (`:352-365`): la primera reserva `RESERVADA` de un turno habilitado de hoy en
   adelante, armada con `_a_turno_de_panel()` pero **sin inscriptos** (`con_inscriptos=False` en
   `:365`) — al mostrador le importa *"tenés Yoga a las 19"*, no quiénes más van.
3. **La alerta y si se le puede cobrar** (`:379-380`), las mismas dos del panel.

**Por qué por DNI y no por nombre.** El docstring tiene el mejor argumento de diseño de todo el
módulo (`:315-320`): *"en el mostrador la persona TIENE el documento en la mano: se tipea sin
ambigüedad, no tiene acentos, y no hay dos socios con el mismo. Buscar 'gonzalez' devuelve cuatro
personas y obliga a preguntar cuál; buscar el DNI devuelve una."*

Y por eso se aceptan coincidencias **parciales** (`:322-323`): *"para poder tipear los últimos
dígitos, que es como la gente los dicta."* El `min_length=2` del parámetro (`:310`) es lo que evita
que un carácter suelto devuelva medio padrón.

**Qué escribe y qué lee.** No escribe nada. Lee `Socio` y `Persona` para la búsqueda (`:330-333`),
`Membresia` para el estado (`:341-345`), `Turno`, `Actividad` y `Reserva` para el próximo turno
(`:353-362`), y lo que arrastran `_alerta_de_socio()` y `estado_renovacion()`. Coincide con la línea
DFD salvo en `Baja`, como los otros dos.

**Por qué está hecho así.** *"Una sola búsqueda cierra la conversación en vez de abrir tres pantallas
más"* (`:324-326`). Es la misma decisión del router entero, en chico: el endpoint podría haber
devuelto sólo la lista de socios y dejar que el cliente pidiera la membresía y el turno de cada uno,
y eso son dos pedidos más por resultado.

Y es donde el patrón se paga más caro: **la búsqueda hace un trabajo proporcional a los resultados**.
Por cada uno de los hasta 10 socios hay una consulta de membresía, una del próximo turno, las de
`_alerta_de_socio()` y las de `estado_renovacion()`. Con diez resultados son unas cuarenta consultas
para una búsqueda que casi siempre devuelve uno. Lo que lo salva es que **casi siempre devuelve uno**:
el DNI es único, y el caso de diez resultados sólo aparece tipeando dos dígitos. La decisión es
correcta para el uso real y frágil para el uso raro, y eso conviene saberlo antes de que alguien
decida buscar por apellido.

**Nota marcada · `deuda_total` viaja siempre en cero.** El campo está en `ResultadoBusqueda` y se
llena con `0.0` fijo, con el motivo al lado (`:378`): *"sin tabla Deuda: el estado 'debe' es
derivable"*. Es un campo del contrato que no informa nada, y la ficha de Flet lo muestra. Es el mismo
resto que [B-05](B-05-cobros-y-pagos.md) encontró en las dos apps armando "deudas" que llegan vacías
— [prepago puro](A-02-prepago-puro.md#prepago-puro): la tabla no existe, y lo que quedó son campos
que devuelven el cero de una pregunta que ya no se hace.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| El DNI tiene menos de 2 caracteres | 422 | el de Pydantic sobre `min_length` | `recepcion.py:310` |
| Sin la sección | 403 | el de la dependencia | `:312` |

Ningún DNI que coincida devuelve `[]`, no 404. Coincide con la línea DFD.

---

## Con qué se conecta

- **Es la misma idea que…** [backend for frontend](A-01-que-es-olimpos.md#menos-pasos-y-más-completo):
  el router entero existe para que el panel sea UN pedido, y lo que compra no es sólo velocidad sino
  una sola foto del instante.
- **Existe por culpa de…** [el mostrador con cola](A-01-que-es-olimpos.md#el-mostrador-con-cola): la
  información llega ordenada por accionabilidad y con la alerta ya resuelta, para que nadie tenga que
  abrir otra pantalla mientras hay gente esperando.
- **Es la misma idea que…** [estado derivado](A-09-estados-derivados.md#estado-derivado): los cinco
  estados de cada anotado se calculan contra el reloj, así que el panel no puede mostrar "pendiente"
  en un turno que venció.
- **Es el mismo problema que…** [N+1](A0-09-el-orm.md#n1): la alerta y el `puede_cobrar_cuota` se
  resuelven dentro del bucle de anotados, que es exactamente lo que el docstring de la alerta decía
  estar evitando.
- **Se contradice con…** [aplicación gemela](A-03-dos-apps-un-backend.md#aplicación-gemela-y-componente-gemelo):
  es la única pantalla del personal que no tiene gemela, y la PWA —que es la referencia— consume uno
  de los tres endpoints; el dueño pidió que exista también en la web.
- **Existe por culpa de…** [sin cobros por adelantado](A-02-prepago-puro.md#sin-cobros-por-adelantado):
  el aviso de "le vence en 2 días" viaja junto a un `puede_cobrar_cuota` en falso, y las dos cosas
  son correctas a la vez.
