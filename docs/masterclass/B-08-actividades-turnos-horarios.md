# B-08 · Actividades, turnos y horarios

*Procesos 60 a 87. Piso del capítulo: la línea que implementa cada paso, en las tres capas.*

Veintiocho procesos, el capítulo más grande de la Parte B después del portal. No se leen en el
orden de la numeración: los números salen de `PROCESOS-LOGICOS-REQUERIDOS.md`, que los ordenó por
ruta, y acá están agrupados por lo que hacen.

| Tema | Procesos |
|---|---|
| El catálogo: qué ofrece el gimnasio | 60, 61, 81, 87 |
| Los abonos: con qué se paga cada actividad | 82, 83, 68, 70 |
| Los horarios: de dónde salen los turnos | 62, 63, 64, 65, 76 |
| Los turnos: la clase concreta | 74, 75, 77 |
| Las reservas: quién va a esa clase | 79, 80, 72 |
| La plata: comprar el abono o la clase suelta | 66, 67, 69, 73, 78 |
| Los profesores habilitados | 71, 84, 85, 86 |

Cinco entidades y hay que tener los nombres claros desde el principio, porque el capítulo entero
depende de no confundirlas. El encabezado del router las define en cinco líneas
(`backend/routers/actividades.py:4-11`):

| Entidad | Qué es | Ejemplo |
|---|---|---|
| `Actividad` | qué ofrece el gimnasio | *Yoga* |
| `Plan_Actividad` | el abono con el que se paga | *Yoga 2 veces por semana* |
| `Inscripcion_Actividad` | un socio anotado a un plan | *Franco compró ese abono el 3/9* |
| `Turno` | la clase concreta | *Yoga, martes 12/08 a las 18:00* |
| `Reserva` | un socio anotado a ese turno | *Franco va a esa clase* |

Lo que hay que traer de la Parte A: qué significa que un estado se derive
([estado derivado](A-09-estados-derivados.md#estado-derivado)), por qué el precio se copia al
comprar ([precio pactado](A-02-prepago-puro.md#precio_pactado-contra-precio_actual)), y qué es una
transacción con lock ([transacción](A0-07-bases-de-datos-relacionales.md#transacción-acid-commit-y-rollback)).

**Lo que se corrió, y cómo.** De este capítulo se corrió una cosa, y en la tanda anterior: el
choque de las claves foráneas compuestas al sacar a un profesor de una actividad (proceso 86), que
hoy está resuelto. El resto es lectura. Correr las reservas contra la base real consumiría clases de
socios de verdad y crearía turnos que el generador después mantiene —la trampa que ya dejó datos
escritos una vez—, así que las afirmaciones sobre concurrencia se justifican con el código y con lo
que dice Postgres, no con una medición.

---

## Piezas comunes

### Por qué el turno es una fila por fecha y no un horario recurrente

Es la primera decisión del módulo y la que explica su tamaño (`actividades.py:13-21`). Guardar
*"Yoga los martes a las 18"* una sola vez sería más compacto. *"El problema aparece el martes que hay
que cancelar la clase porque el profesor se enfermó: con un horario recurrente no hay dónde anotar
esa excepción sin inventar una tabla de excepciones, que termina siendo más complicada que tener una
fila por fecha."*

Con una fila por turno se puede *"cancelar una clase puntual con su motivo, cambiarle el profesor o
ampliarle el cupo sin tocar el resto de las semanas"*.

Y de ahí sale la tensión que recorre el capítulo: si el turno es por fecha, **alguien tiene que
crearlos**. Durante un tiempo los cargaba una persona a mano, y el comentario que encabeza la sección
de horarios cuenta cómo salió (`:1394-1400`): *"Si Yoga era lunes y miércoles 19:00, alguien creaba
dos filas por semana para siempre, y el día que se olvidaba la clase directamente no existía: nadie
podía reservarla y el recepcionista se enteraba cuando llegaba la gente."*

La solución fue **declarar el horario y generar los turnos** —`Horario_Actividad` y `generar_turnos()`,
procesos 63 y 76—, o sea recuperar la compacidad del horario recurrente **sin** perder la fila por
fecha. Las dos representaciones conviven: el horario es la intención, el turno es el hecho, y las
excepciones se anotan en el hecho.

### Las tres reglas del módulo

El encabezado las enumera (`:23-36`), y todo el capítulo es su aplicación:

| Regla | Dónde vive | Proceso |
|---|---|---|
| **1. El cupo no se supera** | `reservar()`, contando reservas activas contra `cupo_maximo` | 79 |
| **2. No se reserva sin saldo** | `reservar()`, con `clases_restantes_de()` | 79 |
| **3. Cancelar a último momento no devuelve la clase** | `cancelar_reserva()`, con `horas_anticipacion_cancelacion` | 72 |

De la primera el docstring dice explícitamente por qué vive en el servidor: *"Si esto viviera solo en
el frontend, bastaría con llamar al endpoint directamente para meter a un socio de más."* Es
[el frontend esconde, el backend rechaza](A-08-autorizacion.md#el-frontend-esconde-el-backend-rechaza)
aplicado a un número.

De la tercera, la asimetría es la decisión: *"Si la cancela el gimnasio, siempre se le devuelve — no
es su culpa."* Por eso hay **dos** estados de cancelación y no uno, `CANCELADA_SOCIO` y
`CANCELADA_GIMNASIO`, y la distinción existe *"exactamente para esto"* (`:316-319`).

### El saldo del abono no es una columna

`clases_restantes` **ya no existe** como campo, y el comentario que lo reemplaza es el argumento
completo (`:122-127`): *"se calcula contando `Reserva`. Contar es la única fuente de verdad, así que
no hay un contador que se pueda desincronizar. Se cuentan las reservas que OCUPAN una clase
(RESERVADA / EN_ESPERA); cancelar una libera la clase automáticamente por dejar de contar."*

Esa última frase es la que paga la decisión. Con un contador guardado, cada camino que cancela una
reserva tendría que acordarse de sumar uno: la cancelación del socio, la del gimnasio, la baja del
abono, la baja de la actividad. Son cuatro lugares, y basta que uno se olvide para que el saldo
mienta para siempre. Contando, los cuatro funcionan sin escribir una línea — y el código lo dice en
cada uno: *"No hace falta 'devolver' la clase: al pasar a CANCELADA_GIMNASIO deja de contar como
usada, así que el saldo se recompone solo"* (`:334-336`).

`clases_restantes_de()` (`:137-148`) devuelve `None` para dos de los tres tipos de límite, y eso es
parte del diseño:

| `tipo_limite` | Qué limita | `clases_restantes` |
|---|---|---|
| `POR_MES` | un total en el mes | el número que queda |
| `POR_SEMANA` | un tope semanal que se recalcula | `None` |
| `CLASE_SUELTA` | una clase, y se agota | `None` |

*"Su límite no es un saldo total"*: preguntarle *"cuántas te quedan"* a un abono semanal no tiene
respuesta única, porque depende de qué semana. El campo en `None` dice *"esta pregunta no aplica"*,
que es información — y es la misma jugada del `ingreso_numero` de
[B-06](B-06-asistencia.md#el-ingreso-repetido-se-marca-no-se-frena).

### El abono vencido se marca al leerlo

`_inscripcion_vigente()` (`:171-195`) hace algo que parece raro en una función de lectura: **escribe**.
Recorre las inscripciones activas del socio y las que pasaron su fecha las pasa a `VENCIDA` sobre la
marcha (`:189-190`). El docstring da el motivo: *"sin una tarea programada, el estado en la base se
queda viejo y un abono terminado seguiría dejando reservar."*

Es el mismo patrón que las bajas programadas de
[A-10](A-10-bajas-logicas.md#cuándo-se-aplica-una-baja-programada-sin-tarea-programada): **no hay
cron, así que la corrección viaja pegada a la lectura**. Lo que se paga es que un `GET` puede escribir
—y que la corrección sólo ocurre si alguien mira—, y lo que se gana es que no existe un proceso que
pueda caerse y dejar el sistema mintiendo.

### `_sumar_un_mes`: un mes calendario, no treinta días

Una función de veinte líneas con un docstring que vale por sí mismo (`:69-90`): *"una membresía
'mensual' de 30 días NO cubre un mes calendario de 31, que es la mayoría de los meses. Usar 30 días
haría que la validación de cobertura pase cuando no debería."*

Y el caso borde resuelto como lo haría un calendario: *"El 31 de enero + 1 mes da 28 de febrero (o
29): se recorta al último día del mes destino."* Esta función es la que decide si un abono entra o no
en la membresía vigente (procesos 69 y 73), así que un error de un día acá sería un abono vendido sin
cobertura.

### Quién puede qué en esta sección

| Barrera | Quién la tiene | La usan |
|---|---|---|
| Sección `ACTIVIDADES` en lectura | Dueño, Recepcionista | 71, 80, 62 |
| Sección `ACTIVIDADES` **o** `COBROS` en lectura | + quien sólo tiene Cobros | 60, 66, 73, 74, 82, 84 |
| Sección `ACTIVIDADES` en TOTAL | Dueño, Recepcionista | 61, 81, 87, 83, 68, 70, 85, 86 |
| Acción `GESTION_TURNOS` | Dueño, Recepcionista | 63, 64, 65, 72, 75, 76, 77, 79 |
| Acción `COBRAR_PAGOS` | Dueño, Recepcionista | 67, 69, 78 |

La segunda fila es la rareza y tiene nombre: `_LEER_PARA_COBRAR` (`:55-57`), construida con
`requiere_alguna_seccion()`. El comentario dice para qué: *"Lecturas que Cobros necesita para cobrar
abonos y clases sueltas: alcanza con tener Cobros, aunque el rol no tenga Actividades."* Es el caso
donde una pantalla necesita datos de **otra** sección para hacer su trabajo, y la alternativa —exigir
las dos— le habría cerrado Cobros a un rol que sí debe cobrar.

Hoy el Dueño y el Recepcionista tienen todo, así que ninguna de las cinco filas separa a nadie. Lo
que separan son **operaciones**, y eso es lo que permite agregar mañana un rol que sólo cobre.

---

## El catálogo

### 60. Consultar el catálogo de actividades

`GET /actividades` · Dueño, Recepcionista (o quien tenga Cobros)

**Qué resuelve.** Qué ofrece el gimnasio, con sus abonos y precios.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Service PWA | `Proyecto - PWA/src/frontend/src/services/actividadService.ts` | 162-186, 214-235 | `getActividades()`, `getActividadesAdmin()` |
| Esquema | `backend/schemas.py` | — | `ActividadOut` con sus `PlanActividadOut` |
| Endpoint | `backend/routers/actividades.py` | 202-208 | `listar_actividades()` |
| Armado | `backend/routers/actividades.py` | 151-168 | `_a_actividad_out()` |
| Vista Flet | `Flet/Proyecto/app/views/actividades.py` | 499-582 | `_card_actividad()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 663-664 | `obtener_actividades()` |

**Cómo funciona.** Todas las actividades ordenadas por nombre, cada una con la lista de sus planes
anidada (`:151-168`). No filtra por `activo`: devuelve también las discontinuadas, y cada cliente
decide. La PWA tiene dos funciones para eso —`getActividades()` para elegir y `getActividadesAdmin()`
para administrar—, que piden lo mismo y filtran distinto.

**Qué escribe y qué lee.** Lee `Actividad` y `Plan_Actividad` (`:207`, `:161-167`). Coincide con la
línea DFD.

**Por qué está hecho así.** Los planes viajan **anidados** en vez de pedirse aparte, y es la misma
decisión del panel de [B-07](B-07-recepcion.md#un-router-organizado-por-pantalla-no-por-entidad) en
chico: la tarjeta de una actividad muestra sus abonos, así que pedirlos por separado serían N+1
pedidos desde el cliente. Lo que se paga es que quien sólo quiere los nombres se lleva los precios
también.

**Qué pasa cuando sale mal.** Sólo 403, para quien no tenga ni Actividades ni Cobros.

---

### 61. Dar de alta una actividad

`POST /actividades` · Dueño, Recepcionista

**Qué resuelve.** Agregar algo nuevo al catálogo: *Yoga*, *Spinning*.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/actividades/ActividadFormModal.tsx` | — | `ActividadFormModal` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/actividadService.ts` | 236-254 | `crearActividad()` |
| Endpoint | `backend/routers/actividades.py` | 211-236 | `crear_actividad()` |
| Vista Flet | `Flet/Proyecto/app/views/actividades.py` | 618-664 | `_form_actividad()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 675-677 | `crear_actividad()` |

**Cómo funciona.** El nombre no se repite, comparado con `ilike` (`:221-224`); se crea activa
(`:226-233`).

**Qué escribe y qué lee.** Lee `Actividad` por nombre (`:222`); escribe `Actividad`
(`nombre`, `descripcion`, `cupo_default`, `horas_anticipacion_cancelacion`, `minutos_tolerancia`,
`activo`) en `:226-233`. Coincide con la línea DFD.

**Por qué está hecho así.** Los tres números que se cargan al crearla son los parámetros de las tres
reglas del módulo: `cupo_default` alimenta la regla 1, `horas_anticipacion_cancelacion` la regla 3, y
`minutos_tolerancia` decide cuándo una reserva deja de servir
([B-06](B-06-asistencia.md#52-fichar-el-ingreso-de-un-socio)). Que vivan **por actividad** y no como
constantes del sistema es la decisión: *"a una clase de Yoga llegar 20 minutos tarde es no ir, y a la
sala de musculación —abierta toda la tarde— casi no le aplica"* (`backend/turnos.py:69-73`).

**Nota marcada · el `ilike` acepta comodines.** `Actividad.nombre.ilike(nombre)` (`:222`) interpreta
`_` y `%` como comodines de patrón, así que una actividad llamada `Yoga_suave` colisiona con
`YogaXsuave`. Es el mismo defecto que [B-05](B-05-cobros-y-pagos.md) encontró y **corrió** en el
nombre duplicado de un plan de membresía. Acá está sin correr, pero el mecanismo es idéntico: el
arreglo es escapar el patrón o comparar con `lower()`.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| Ya existe una con ese nombre | 409 | *"Ya existe una actividad llamada 'X'."* | `actividades.py:221-224` |
| Sin la sección en TOTAL | 403 | el de la dependencia | `:215` |

---

### 81. Editar una actividad

`PUT /actividades/{id_actividad}` · Dueño, Recepcionista

**Qué resuelve.** Corregir el nombre, la descripción o los tres números de la actividad.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Service PWA | `Proyecto - PWA/src/frontend/src/services/actividadService.ts` | 255-286 | `actualizarActividad()` |
| Endpoint | `backend/routers/actividades.py` | 645-678 | `actualizar_actividad()` |
| Vista Flet | `Flet/Proyecto/app/views/actividades.py` | 618-664 | `_form_actividad()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 679-681 | `editar_actividad()` |

**Cómo funciona.** Existe (`_buscar_actividad()`, `:621-626`); el nombre nuevo no choca con **otra**
(`:659-666`); se escriben los cinco campos.

**Por qué está hecho así.** Acá está la decisión de modelado más importante del módulo, y vive en el
docstring (`:652-657`): *"Ojo con `cupo_default`: cambiarlo NO toca los turnos ya programados. Cada
`Turno` guardó su propio `cupo_maximo` al crearse justamente para esto — si el cupo se leyera de la
actividad, bajarlo dejaría turnos con más gente anotada que lugares."*

Es **denormalización deliberada**: `cupo_maximo` es una copia. La alternativa —leer el cupo de la
actividad en cada reserva— ahorraría una columna y crearía un estado imposible: 20 anotados en un
turno de 15. El patrón es el mismo de
[precio pactado](A-02-prepago-puro.md#precio_pactado-contra-precio_actual): **un dato que participa
de una decisión ya tomada se copia en el momento de tomarla.** Y el paralelo es exacto — el precio
protege lo que alguien ya pagó, el cupo protege a quien ya se anotó.

**Qué escribe y qué lee.** Lee `Actividad` (`:658`, `:660-663`); escribe los cinco campos
(`:668-672`). Coincide con la línea DFD.

**Qué pasa cuando sale mal.** 404 *"La actividad no existe."* (`:624-626`), 409 por nombre repetido
(`:664-666`), 403 sin la sección.

---

### 87. Dar de baja o reactivar una actividad

`POST /actividades/{id_actividad}/toggle-estado` · Dueño, Recepcionista

**Qué resuelve.** Discontinuar una actividad, o traerla de vuelta.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Service PWA | `Proyecto - PWA/src/frontend/src/services/actividadService.ts` | 287-309 | `darDeBajaActividad()`, `reactivarActividad()` |
| Endpoint | `backend/routers/actividades.py` | 681-728 | `alternar_estado_actividad()` |
| Vista Flet | `Flet/Proyecto/app/views/actividades.py` | 665-689 | `_baja_actividad()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 683-687 | `cambiar_estado_actividad()` |

**Cómo funciona.** El estado se escribe, no se alterna — y el comentario explica por qué el nombre
del endpoint miente (`actividades.py:713-717`): *"explícito gana sobre el toggle. El toggle solo es seguro si quien
llama conoce el estado actual: con una pantalla desactualizada, 'dar de baja' sobre algo ya dado de
baja lo REACTIVARÍA. El frontend manda el estado que quiere y no depende de lo que crea tener."*

Es [idempotencia](A0-03-http.md#método-http-e-idempotencia) comprada con un parámetro: `?activo=false`
dos veces deja el mismo resultado; un toggle dos veces vuelve al principio. El parámetro sigue siendo
opcional y el toggle sigue funcionando si no viene (`:718`), que es deuda de compatibilidad.

**Al dar de baja se cancelan los turnos FUTUROS** (`:719-728`), con su motivo y cancelando las
reservas como `CANCELADA_GIMNASIO`. El docstring da los dos lados: *"seguir aceptando reservas de una
actividad discontinuada sería vender algo que no se va a dictar. Los turnos pasados no se tocan, son
historial."*

**Por qué está hecho así.** *"NO la borra. Borrarla dejaría huérfanos los turnos, las inscripciones y
los pagos que la referencian — y esos pagos son historial contable"* (`:689-693`). Es
[baja lógica](A-10-bajas-logicas.md#baja-lógica-soft-delete), y el argumento contable es el mismo que
impide borrar un socio.

Lo que **no** hace es cancelar los abonos vigentes de esa actividad. Un socio que compró *Yoga 2 por
semana* el día antes de que se discontinúe se queda con un abono activo cuyas clases ya no existen —
sus reservas futuras se cancelaron, pero la inscripción sigue `ACTIVA` hasta su fecha. Es coherente
con la decisión de no reembolsar en silencio (proceso 67, *"devolver plata es una decisión aparte"*),
y a la vez deja al mostrador sin ningún aviso de que ese abono hay que resolverlo. No está anotado en
el código.

**Qué escribe y qué lee.** Lee `Actividad` y los `Turno` futuros habilitados (`:721-725`); escribe
`Actividad.activo` (`:718`), `Turno.estado` y `Turno.motivo_cancelacion` (`:727-728`) y
`Reserva.estado`/`fecha_cancelacion`. Coincide con la línea DFD.

**Qué pasa cuando sale mal.** 404 y 403. No hay 400: dar de baja algo ya dado de baja con
`?activo=false` es una escritura sin efecto, y eso es lo que la idempotencia busca.

---

## Los abonos

### 82. Consultar los abonos de una actividad · 83. Dar de alta un abono

`GET` y `POST /actividades/{id_actividad}/planes` · Dueño, Recepcionista

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Service PWA | `Proyecto - PWA/src/frontend/src/services/actividadService.ts` | 187-213, 323-357 | `getPlanesDeActividad()`, `getPlanesDeActividadAdmin()`, `crearPlanActividad()` |
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/actividades/PlanFormModal.tsx` | — | `PlanFormModal` |
| Endpoints | `backend/routers/actividades.py` | 731-766 | `listar_planes()`, `crear_plan()` |
| Armado | `backend/routers/actividades.py` | 637-642 | `_a_plan_out()` |
| Vista Flet | `Flet/Proyecto/app/views/actividades.py` | 583-617, 690-740 | `_fila_plan()`, `_form_plan()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 689-695 | `crear_plan_actividad()`, `editar_plan_actividad()` |

**Cómo funciona.** El listado ordena por precio (`:738-741`), que es el orden en que alguien elige un
abono. El alta no valida nada más que lo que valida el esquema: `tipo_limite` es un enum, y los topes
de `cantidad` viven en `PlanActividadCrear`.

**Los topes** son de `CLAUDE.md` y están en el esquema de entrada: 7 por semana, 31 por mes, 1 la
suelta. El de la suelta es el que importa — un plan `CLASE_SUELTA` con cantidad 3 no significa nada, y
el que decide el precio de la clase suelta de una actividad es justamente ese plan (proceso 78).

**Por qué está hecho así.** El precio de la clase suelta **dejó de ser una columna de `Actividad`** y
pasó a ser un plan con `tipo_limite=CLASE_SUELTA` (`actividades.py:1321-1323`). Lo que se gana: un solo lugar donde
viven los precios de una actividad, y la clase suelta se puede dar de baja como cualquier otro abono.
Lo que se paga: una actividad sin ese plan cargado **no se puede vender suelta**, y el error recién
aparece al intentar cobrarla (proceso 78).

**Qué pasa cuando sale mal.** 404 si la actividad no existe (`:737`, `:751`), 403 sin la sección, 422
por los topes de `cantidad`.

---

### 68. Editar un abono de actividad

`PUT /actividades/planes/{id_plan}` · Dueño, Recepcionista

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Service PWA | `Proyecto - PWA/src/frontend/src/services/actividadService.ts` | 358-369 | `actualizarPlanActividad()` |
| Endpoint | `backend/routers/actividades.py` | 769-790 | `actualizar_plan()` |

**Por qué está hecho así.** El docstring es la otra mitad del par con el `cupo_maximo` del proceso 81
(`:775-780`): *"Cambiar el precio NO afecta a quien ya lo compró: la inscripción guardó su
`precio_pactado`. Es la misma razón por la que `Membresia` tiene su copia del precio — un aumento no
puede reescribir lo que alguien ya pagó."*

Tres copias del mismo patrón en el mismo módulo —`cupo_maximo` en `Turno`, `precio_pactado` en
`Inscripcion_Actividad`, y el precio en `Membresia`— y las tres por la misma razón:
[precio pactado](A-02-prepago-puro.md#precio_pactado-contra-precio_actual). Cuando un patrón aparece
tres veces en un archivo, deja de ser una decisión puntual y pasa a ser una regla del sistema.

**Qué pasa cuando sale mal.** 404 *"El plan no existe."* (`:632-634`), 403.

---

### 70. Dar de baja o reactivar un abono de actividad

`POST /actividades/planes/{id_plan}/toggle-estado` · Dueño, Recepcionista

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Service PWA | `Proyecto - PWA/src/frontend/src/services/actividadService.ts` | 370-392 | `darDeBajaPlanActividad()`, `reactivarPlanActividad()` |
| Endpoint | `backend/routers/actividades.py` | 793-812 | `alternar_estado_plan()` |
| Vista Flet | `Flet/Proyecto/app/views/actividades.py` | 741-760 | `_baja_plan()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 697-699 | `cambiar_estado_plan()` |

**Cómo funciona.** El mismo patrón explícito-sobre-toggle del proceso 87. Un plan dado de baja no se
puede comprar (el proceso 69 lo rechaza) y **no cancela** las inscripciones vigentes: quien lo compró
lo termina. Es la distinción entre *"dejar de vender"* y *"quitar lo vendido"*, y acá sólo se hace la
primera.

**Qué pasa cuando sale mal.** 404, 403.

---

## Los horarios

### 62. Listar los horarios semanales

`GET /actividades/horarios` · Dueño, Recepcionista

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/actividades/HorarioSemanal.tsx` | — | `HorarioSemanal` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/turnosService.ts` | 70-84 | `getHorarios()` |
| Endpoint | `backend/routers/actividades.py` | 1433-1448 | `listar_horarios()` |
| Armado | `backend/routers/actividades.py` | 1405-1430 | `_a_horario_out()` |
| Vista Flet | `Flet/Proyecto/app/views/actividades.py` | 129-241 | `_grilla_semanal()`, `_chip_horario()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 826-828 | `obtener_horarios()` |

**Cómo funciona.** Cada horario viaja con `turnos_futuros`, un conteo, y el comentario explica el
filtro que parece de más (`actividades.py:1406-1408`): *"Sólo los HABILITADOS. Contar también los cancelados haría
que la grilla dijera '4 turnos' de un horario cuyos cuatro turnos están cancelados — justo lo
contrario de lo que ese número existe para avisar."*

Ese número es lo único que le dice al dueño si un horario está produciendo clases. Un conteo que
incluya los cancelados no es *"un poco impreciso"*: dice lo opuesto a la verdad en el único caso donde
alguien lo iba a mirar.

**Qué escribe y qué lee.** Lee `Horario_Actividad`, `Actividad`, `Turno` (para el conteo, `:1409-1414`)
y `Profesor`/`Empleado`/`Persona` (`:1424-1425`). Coincide con la línea DFD.

---

### 63. Cargar el horario semanal y generar sus turnos

`POST /actividades/horarios` · Dueño, Recepcionista

**Qué resuelve.** Declarar *"Yoga los lunes 19:00"* y que los turnos aparezcan.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/actividades/HorarioFormModal.tsx` | — | `HorarioFormModal` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/turnosService.ts` | 85-103 | `crearHorario()` |
| Endpoint | `backend/routers/actividades.py` | 1451-1523 | `crear_horario()` |
| Generación | `backend/turnos.py` | 279-345 | `generar_turnos()` |
| Vista Flet | `Flet/Proyecto/app/views/actividades.py` | 242-379 | `_form_horario()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 830-832 | `crear_horario()` |

**Cómo funciona.** La actividad existe (`actividades.py:1466-1469`); si viene profesor, tiene que estar habilitado
para **esa** actividad, con su rol prendido y su empleado activo (`:1476-1487`); no choca con otro
horario del mismo día y hora; se crea; y **se generan los turnos en el acto** (`:1519-1521`).

Generar ahí mismo es deliberado (`:1459-1463`): *"quien acaba de cargar 'Yoga los lunes 19:00' espera
ver los turnos, y si aparecieran recién mañana pensaría que no se guardó y lo cargaría de nuevo."*
Es una decisión de UI que cambia el backend: la alternativa —esperar al próximo arranque— es más
limpia y produce un usuario que carga el horario dos veces.

**La validación del profesor** tiene tres filtros y el comentario dice qué tapa cada uno
(`:1471-1474`): *"sin este control, un horario de Yoga podía quedar a nombre de alguien que da
Spinning, o de un profesor dado de baja que ya no ve nada."* El tercer filtro,
`ProfesorActividad.activo`, es de la tanda del 2026-09-30
([el rol que se apaga](A-10-bajas-logicas.md#la-segunda-fila-de-esa-clase-y-cómo-se-cerró)).

**Por qué el generador está en `turnos.py` y no acá.** Porque lo llaman tres cosas: este endpoint, el
proceso 76 y el arranque del backend. Y es **idempotente**, que es su propiedad más importante
(`turnos.py:281-288`): *"se puede correr todos los días, o diez veces seguidas, y el resultado es el
mismo. Eso permite llamarla sin miedo desde el arranque del backend y desde un botón, sin coordinar
quién la corrió y cuándo."*

Lo que la hace idempotente es el índice único de `Turno` (`id_sede`, `id_actividad`, `fecha`, `hora`),
y el comentario explica por qué **igual** se consulta antes en vez de confiar en el error: *"un
`IntegrityError` aborta la transacción entera y se perderían los turnos buenos generados antes en la
misma pasada"* (`turnos.py:291-295`). La restricción de la base es la garantía; la consulta previa es
para no perder trabajo.

**Y lo que el generador NO toca** (`turnos.py:297-299`): los turnos cargados a mano
(`id_horario_actividad` nulo) y los cancelados. *"Si alguien canceló el turno del lunes por feriado,
volver a crearlo sería deshacer una decisión humana con un proceso automático."*

**Nota marcada · crear un horario escribe turnos de OTROS horarios.** `generar_turnos()` no genera
sólo para el horario nuevo: recorre **todos** los activos en una ventana móvil de 28 días desde hoy
(`turnos.py:300-306`). Con horarios ya cargados, crear uno nuevo crea además los turnos de la semana
que entró en la ventana desde la última corrida. Son legítimos —el generador es idempotente y los
habría creado solo— pero aparecen en un momento que nadie pidió, y es una trampa concreta para quien
pruebe contra la base real: hay que anotar el último `id_turno` antes y borrar los nuevos que no
tengan reserva. Está anotado en `CLAUDE.md`.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| La actividad no existe | 404 | *"La actividad no existe."* | `actividades.py:1466-1469` |
| El profesor no está habilitado, o está de baja | 409 | *"Ese profesor no está asignado a X. Asignalo primero…"* | `:1488-1493` |
| Ya hay un horario ese día y hora | 409 | el del choque | `:1495-…` |

---

### 64. Activar o desactivar un horario semanal

`POST /actividades/horarios/{id_horario}/estado` · Dueño, Recepcionista

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Service PWA | `Proyecto - PWA/src/frontend/src/services/turnosService.ts` | 104-120 | `darDeBajaHorario()` |
| Endpoint | `backend/routers/actividades.py` | 1526-1572 | `cambiar_estado_horario()` |
| Vista Flet | `Flet/Proyecto/app/views/actividades.py` | 457-485 | `_baja_horario()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 834-851 | `cambiar_estado_horario()` |

**Cómo funciona.** `activo` es **obligatorio** y no un toggle, con el mismo argumento del proceso 87
(`actividades.py:1536-1538`): *"con un toggle dos pantallas desactualizadas podrían reactivarlo sin que nadie lo
pida."*

Y `borrar_turnos_futuros` está **apagado por defecto**, que es la parte importante
(`:1540-1546`): *"Dar de baja el horario significa 'no generes más', NO 'borrá lo que ya existe': esos
turnos futuros pueden tener gente anotada, y hacerlos desaparecer dejaría reservas apuntando a la
nada y socios que creen tener clase. Cuando se pide explícitamente, se cancelan (no se borran) y sólo
los que no tienen NADIE anotado."*

Tres decisiones apiladas en un parámetro opcional: por defecto no hacer nada, cuando se pide cancelar
en vez de borrar, y ni así tocar los que tienen gente. Cada una tapa un caso peor que la anterior.

**Nota marcada · el mensaje de Flet decía otra cosa.** El comentario de `state.py` lo registra: el
texto prometía que los turnos vacíos se cancelaban, y no es así salvo que se pida explícitamente. Hoy
dice *"Deja de generar turnos nuevos; los turnos que ya existen siguen en pie — pueden tener gente"*.

---

### 65. Cambiar o sacar el profesor de un horario ya creado

`PUT /actividades/horarios/{id_horario}/profesor` · Dueño, Recepcionista

**Qué resuelve.** Un profesor que se va, una licencia, o haberse equivocado al cargarlo.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/actividades/ProfesorHorarioModal.tsx` | — | `ProfesorHorarioModal` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/turnosService.ts` | 121-134 | `cambiarProfesorDeHorario()` |
| Endpoint | `backend/routers/actividades.py` | 1576-1650 | `cambiar_profesor_de_horario()` |
| Vista Flet | `Flet/Proyecto/app/views/actividades.py` | 380-456 | `_cambiar_profesor_horario()`, `_guardar_profesor_horario()` |

**Cómo funciona.** Misma validación que el alta (`actividades.py:1615-1630`), y después **arrastra a los turnos
futuros habilitados**.

**Por qué está hecho así.** El docstring es el mejor ejemplo del capítulo de una función que existe
por lo que costaba no tenerla (`actividades.py:1584-1591`): *"Hasta acá el profesor sólo se elegía al crear el
horario, y corregirlo obligaba a darlo de baja y cargarlo de nuevo: eso genera turnos nuevos y deja
los viejos cancelados, o sea que arreglar un dato administrativo le volteaba las clases a los que ya
estaban anotados."*

Y el arrastre no es una comodidad, es la parte que importa (`:1593-1598`): *"El profesor del horario se
copia a cada turno al generarlo, y de ahí sale 'Mis clases': si sólo se cambiara el horario, el
profesor nuevo no vería ninguna de las clases que ya están generadas y el viejo las seguiría viendo
todas."*

Ése es el **costo de la copia** que el proceso 81 elogiaba. `cupo_maximo` y `id_profesor` son los dos
campos que `Turno` copia, y los dos por buenas razones — pero una copia hay que mantenerla, y esta
función es ese mantenimiento. Lo que se conserva y lo que no está decidido por fecha:

| Turnos | Qué les pasa | Por qué |
|---|---|---|
| Futuros y `HABILITADO` | se les cambia el profesor | de ahí sale "Mis clases" |
| Pasados | no se tocan | *"la clase del martes pasado la dio esa persona, y reescribirlo sería falsear el registro"* |
| Cancelados | no se tocan | *"ya no son clases"* |

`id_profesor` en `None` saca el profesor y deja el horario como sala abierta, *"que es un estado
válido"* (`:1607-1608`).

**Qué pasa cuando sale mal.** 404 si el horario no existe; 409 con la misma validación del alta.

---

### 76. Generar los turnos que falten

`POST /actividades/turnos/generar` · Dueño, Recepcionista

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Service PWA | `Proyecto - PWA/src/frontend/src/services/turnosService.ts` | 135-150 | `regenerarTurnos()` |
| Endpoint | `backend/routers/actividades.py` | 1652-1674 | `generar()` |
| Generación | `backend/turnos.py` | 279-345 | `generar_turnos()` |
| Vista Flet | `Flet/Proyecto/app/views/actividades.py` | 486-498 | `_regenerar()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 853-855 | `generar_turnos()` |

**Cómo funciona.** Llama al generador y arma un mensaje en tres versiones según qué pasó
(`actividades.py:1666-1673`): se crearon N, no hay horarios, o ya estaban todos.

**Por qué existe si el backend ya lo corre al arrancar.** El docstring lo dice (`actividades.py:1659-1663`): *"alguien
que acaba de cargar varios horarios quiere ver el resultado sin reiniciar nada"*. Y es seguro
ofrecerlo como botón **porque es idempotente**: sin esa propiedad, un botón que alguien puede apretar
dos veces sería un botón peligroso. La idempotencia no es una elegancia técnica acá — es lo que hace
posible la pantalla.

Los tres mensajes son la otra mitad: *"Ya estaban todos los turnos generados. No hizo falta crear
ninguno"* le dice al usuario que el botón funcionó y que no hacía falta. Un botón idempotente que no
dice nada se aprieta cinco veces.

---

## Los turnos

### 74. Ver la agenda de turnos de los próximos días · 75. Programar una clase · 77. Cancelar una clase

`GET /actividades/turnos`, `POST /actividades/turnos`, `POST /actividades/turnos/{id}/cancelar`

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Componente PWA | `Proyecto - PWA/src/frontend/src/components/AgendaTurnos.tsx` | 53-233 | `AgendaTurnos` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/turnosService.ts` | 179-219 | `getAgenda()`, `cancelarTurno()` |
| Service PWA (socio) | `Proyecto - PWA/src/frontend/src/services/actividadService.ts` | 586-638 | `getTurnosDisponibles()` |
| Endpoints | `backend/routers/actividades.py` | 243-263, 266-304, 307-344 | `listar_turnos()`, `crear_turno()`, `cancelar_turno()` |
| Armado | `backend/routers/actividades.py` | 101-119 | `_a_turno_out()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 709-715, 816-819 | `obtener_turnos()`, `cancelar_turno()` |

**Cómo funciona el listado (74).** Un rango de fechas con default de una semana, *"es lo que muestra
la grilla, y sin límite se bajaría el historial completo"* (`:250-252`).

**Cómo funciona el alta (75).** Valida actividad, sede y profesor (`:274-283`), rechaza fechas pasadas
—*"reservar algo que ya ocurrió no tiene sentido y ensuciaría la grilla"* (`:285-288`)— y toma el cupo
de la actividad con la opción de pisarlo *"para una clase puntual (un día que se usa un salón más
grande)"* (`:295-297`).

**Cómo funciona la cancelación (77).** El turno pasa a `CANCELADO` con su motivo, y **cada reserva
activa** pasa a `CANCELADA_GIMNASIO` (`:329-336`). El docstring nombra la razón de que existan dos
estados de cancelación: *"si la clase se cae por culpa del gimnasio, nadie pierde su cupo"*.

Y el comentario del bucle es el que muestra el valor del saldo derivado (`:334-336`): *"No hace falta
'devolver' la clase: al pasar a CANCELADA_GIMNASIO deja de contar como usada, así que el saldo se
recompone solo."* Cuatro líneas de código para una operación que con un contador guardado habría sido
un `UPDATE` por socio y un lugar más donde equivocarse.

**Nota marcada · el alta no valida que el profesor esté habilitado.** `crear_turno()` chequea que el
profesor **exista** (`:281-283`) pero no que esté asignado a esa actividad, a diferencia de
`crear_horario()`, que sí (`actividades.py:1476-1493`). La base lo ataja igual: la clave compuesta
`fk_turno_profesor_habilitado` rechaza el par (`db/schema.sql:1063-1065`), así que el resultado es un
500 sin mensaje en vez de un 409 explicado. Es el mismo patrón de fallo que
[B-03](B-03-personal.md#36-dar-de-baja-a-un-empleado) documentó para la baja del profesor: la base
protege, y lo que falta es traducir el rechazo. Leído, no corrido.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| Actividad, sede o profesor inexistentes | 404 | los tres suyos | `actividades.py:274-283` |
| Fecha pasada | 400 | *"No se puede programar una clase en una fecha pasada."* | `:286-288` |
| El turno no existe (cancelar) | 404 | *"El turno no existe."* | `:322-323` |
| Ya estaba cancelada | 400 | *"Esa clase ya estaba cancelada."* | `:324-326` |

---

## Las reservas

### 79. Anotar a un socio en una clase

`POST /actividades/turnos/{id_turno}/reservar` · Dueño, Recepcionista

**Qué resuelve.** Anotar a alguien en una clase, con las reglas 1 y 2.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Service PWA | `Proyecto - PWA/src/frontend/src/services/actividadService.ts` | 639-653 | `reservarTurno()` |
| Endpoint | `backend/routers/actividades.py` | 351-464 | `reservar()` |
| Saldo | `backend/routers/actividades.py` | 130-148 | `_clases_usadas()`, `clases_restantes_de()` |
| Abono vigente | `backend/routers/actividades.py` | 171-195 | `_inscripcion_vigente()` |
| Base | `db/schema.sql` | — | índice único `(id_turno, id_socio)` y el disparador de cupo |

**Cómo funciona.** El endpoint, en orden:

1. **El turno, con lock** (`:383-387`). Esto merece su propia sección, abajo.
2. **No cancelado** (`:390-392`); **el socio existe** (`:394-396`).
3. **No está ya anotado** (`:399-405`), o 409.
4. **Regla 1, el cupo** (`:417`): si está completo, **no se rechaza** — se anota en lista de espera.
5. **Regla 2, el saldo** (`:420-441`): sin abono vigente, 400 con qué hacer; sin clases restantes,
   409 con la sugerencia de venir como clase suelta.
6. **La reserva** (`:443-452`), con `id_inscripcion` nulo si es clase suelta y el estado según el cupo.

**La lista de espera reemplazó un rechazo** (`:407-415`): *"El rechazo obligaba al socio a estar mirando
la pantalla por si alguien cancelaba, y al lugar liberado a quedar vacío si nadie miraba. Ahora la
cancelación promueve sola al primero de la fila."*

Y el diseño de dónde vive: `EN_ESPERA` **comparte tabla** con las reservas normales *"para que el
índice único (id_turno, id_socio) impida por construcción estar anotado y en espera a la vez"*. Una
tabla aparte habría necesitado un chequeo cruzado que alguien puede olvidar; compartiéndola, la base
lo hace cumplir. Es
[poner la restricción en la capa más baja que pueda sostenerla](A-98-glosario.md#patrones-con-nombre).

#### El lock, y por qué no alcanza con el disparador

Éste es el pasaje más denso del módulo y vale leerlo entero (`:362-381`). `with_for_update()` toma un
lock sobre la fila del turno hasta el fin de la transacción, y el comentario explica el ataque:

> *"Sin esto, dos personas reservando el último lugar al mismo tiempo NO se ven una a la otra —bajo
> READ COMMITTED, que es el default de Postgres, cada transacción ve la base como estaba cuando
> empezó— así que las dos cuentan 19 sobre 20 y las dos entran. El turno termina con 21 y la lista de
> espera, que existe justamente para eso, nunca se usa."*

> **↓ Capa 1 — por qué READ COMMITTED no alcanza.** Salteable si ya viste
> [ACID](A0-07-bases-de-datos-relacionales.md#transacción-acid-commit-y-rollback).
>
> Bajo READ COMMITTED, cada sentencia ve lo confirmado **hasta el instante en que empieza esa
> sentencia**. Dos transacciones que cuentan reservas a la vez ven las mismas 19, porque ninguna de
> las dos confirmó todavía. El conteo de cada una es correcto **para su instante** y las dos llegan a
> la misma conclusión válida: *"hay lugar"*. Es una **anomalía de escritura sesgada** (write skew):
> ninguna sobrescribe lo de la otra, así que Postgres no tiene nada que detectar — cada una modifica
> una fila distinta de `Reserva`—, y la invariante que se rompe es una que sólo existe en la cabeza
> del programa: *"la cantidad de reservas de un turno no supera su cupo"*.
>
> El lock la convierte en algo que la base sí puede vigilar: al bloquear la fila del `Turno`, las dos
> transacciones se serializan sobre ese recurso. La segunda espera, y cuando cuenta ya ve 20.

Y el cierre es la parte que enseña (`:376-381`): *"El CONSTRAINT TRIGGER de la migración 006 cubre lo
otro —un INSERT a mano, un bug, un script de importación— pero NO esta carrera, porque también cuenta
y también contaría 19 en las dos transacciones. Cada uno tapa un agujero distinto; por eso están los
dos."*

Es la distinción que casi siempre se pierde: **una restricción de integridad no es un control de
concurrencia.** El disparador garantiza que ninguna fila sola viole la regla; el lock garantiza que
dos operaciones simultáneas no la violen juntas. Son problemas diferentes y necesitan herramientas
diferentes, y tener las dos no es redundancia. Es
[defensa en profundidad](A-98-glosario.md#patrones-con-nombre) con los dos niveles nombrados.

**Qué escribe y qué lee.**

| Tabla | Atributos | Escribe o lee | Línea |
|---|---|---|---|
| `Turno` | la fila, **con lock**, y `estado`, `cupo_maximo`, `id_actividad` | lee | `:383-387`, `:390`, `:417` |
| `Socio`, `Persona` | la fila y el nombre | lee | `:394`, `:403` |
| `Reserva` | las del turno, para el cupo y el duplicado | lee | `:97-98`, `:400-401` |
| `Inscripcion_Actividad`, `Plan_Actividad` | el abono vigente y su tipo | lee | `:177-187` |
| `Inscripcion_Actividad` | `estado` a `VENCIDA` si pasó su fecha | **escribe** | `:190` |
| `Reserva` | las que consumen el abono, para el saldo | lee | `:131-134` |
| `Reserva` | `id_turno`, `id_socio`, `id_inscripcion`, `fecha_reserva`, `estado` | **escribe** | `:443-452` |

**Discrepancia con la línea DFD.** La línea no declara la escritura de `Inscripcion_Actividad.estado`
que hace `_inscripcion_vigente()` al marcar vencidas. Es un efecto lateral real de un endpoint de
escritura, y la línea lo omite.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| El turno no existe | 404 | *"El turno no existe."* | `actividades.py:388-389` |
| La clase está cancelada | 400 | *"Esa clase está cancelada."* | `:390-392` |
| El socio no existe | 404 | *"El socio no existe."* | `:394-396` |
| Ya está anotado | 409 | *"X ya está anotado en esa clase."* | `:399-405` |
| Sin abono activo | 400 | *"X no tiene un abono activo de Y. Cobrale un plan o marcá la reserva como clase suelta."* | `:422-429` |
| Sin clases restantes | 409 | *"X ya usó todas las clases de su abono. Puede venir como clase suelta."* | `:433-441` |

Los dos últimos son los interesantes porque **cada rechazo incluye la salida**. No dicen sólo qué
está mal: dicen qué hacer. Es
[el mostrador con cola](A-01-que-es-olimpos.md#el-mostrador-con-cola) en el texto de un error.

---

### 72. Cancelar la reserva de un socio y promover la lista de espera

`POST /actividades/reservas/{id_reserva}/cancelar` · Dueño, Recepcionista

**Qué resuelve.** Bajar a alguien de una clase, con la regla 3, y darle el lugar al que espera.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Service PWA | `Proyecto - PWA/src/frontend/src/services/actividadService.ts` | 673-704 | `cancelarReserva()` |
| Endpoint | `backend/routers/actividades.py` | 467-543 | `cancelar_reserva()` |
| Promoción | `backend/turnos.py` | 148-205 | `promover_de_lista_de_espera()` |
| Aviso | `backend/notificaciones.py` | — | `notificar_promocion_lista_espera()` |

**Cómo funciona.** Existe (`actividades.py:481-484`); está `RESERVADA` o `EN_ESPERA` (`:489-491`); se calcula si
avisó con anticipación (`:493-499`); pasa a `CANCELADA_SOCIO`; y **si ocupaba un lugar**, se promueve
al primero de la espera (`:518-520`).

**Se admite cancelar estando en lista de espera** (`:485-488`): *"quien se anotó esperando un lugar
tiene todo el derecho a bajarse antes de que le toque, y si no pudiera, seguiría subiendo en la fila
hasta ocupar un lugar que ya no quiere."* Un caso que es fácil no pensar, y cuya ausencia produce un
bug silencioso: alguien promovido a una clase a la que no piensa ir, ocupando un lugar real.

**La promoción sólo si esta reserva ocupaba un lugar** (`:514-517`): *"cancelar una que ya estaba en
espera no libera nada, y promover ahí correría la fila sin motivo."*

#### Tres detalles de transacción que se descubrieron corriendo

`promover_de_lista_de_espera()` (`turnos.py:148-205`) tiene tres decisiones que no se deducen leyendo
el código de arriba:

**1. No hace `commit`** (`turnos.py:161-165`): *"quien llama ya está dentro de una transacción (la
cancelación) y las dos cosas tienen que pasar juntas o ninguna. Si esto commiteara por su cuenta y
después fallara la cancelación, alguien quedaría promovido a un lugar que nunca se liberó."* La misma
razón está del lado del llamador (`actividades.py:517-520`): *"Si fueran dos, un fallo entre medio
dejaría a alguien promovido a un lugar que nunca se liberó — o el lugar libre sin nadie que lo tome."*

**2. El `flush` explícito, y el comentario lo marca como no decorativo**
(`turnos.py:166-175`): la sesión se crea con `autoflush=False`, así que el
`reserva.estado = 'CANCELADA_SOCIO'` del llamador **todavía no llegó a la base** cuando acá se cuenta
la ocupación. Sin el flush, *"`ocupacion` sigue contando como ocupado el lugar que se acaba de
liberar, concluye que el turno está lleno, y no promueve a nadie: la lista de espera nunca avanza."*

Y la última línea de ese comentario es la más valiosa del archivo: *"Se descubrió probándolo contra la
base, no leyendo el código."* Es exactamente la clase de bug que
[la unidad de trabajo](A0-09-el-orm.md#sesión-y-mapa-de-identidad) produce cuando uno razona sobre el
objeto en memoria y la consulta va a la base.

**3. El mismo lock que `reservar()`** (`turnos.py:177-178`), *"y por el mismo motivo: dos
cancelaciones simultáneas sobre el mismo turno liberarían un lugar cada una"* y promoverían a dos
personas al mismo lugar.

**El orden de la fila es `fecha_reserva`, sin excepciones** (`turnos.py:157-159`), *"y eso es una
ventaja — nadie tiene que justificar por qué eligió a uno."* Una regla simple que no admite
discusión vale más, en un mostrador, que una regla justa que hay que explicar.

**El aviso va después del `commit`** (`actividades.py:525-531`): *"un lugar que se libera y nadie sabe
es un lugar que sigue vacío. `notificar()` nunca levanta excepción, así que si el mail no sale la
cancelación igual queda hecha."* La notificación es **best-effort a propósito**: la operación no
depende de ella.

**Qué pasa cuando sale mal.** 404 *"La reserva no existe."*; 400 *"Esa reserva ya estaba cancelada."*

---

### 80. Consultar los anotados de una clase

`GET /actividades/turnos/{id_turno}/reservas` · Dueño, Recepcionista

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Endpoint | `backend/routers/actividades.py` | 546-566 | `listar_reservas()` |

**Cómo funciona.** Las reservas `RESERVADA` del turno (`:558-566`). El docstring dice para quién es:
*"Es la lista que usa el profesor."*

**Nota marcada · el profesor no puede llamarlo.** Pide `Seccion.ACTIVIDADES` (`:551`), que el Profesor
tiene en `NINGUNO`. La lista que el docstring dice que usa el profesor la ve por otro camino —"Mis
clases" en el portal, [B-14](B-14-portal-del-socio.md)—, y este endpoint queda para el mostrador. El
docstring nombra un usuario que no tiene permiso de usarlo.

Y devuelve **sólo** las `RESERVADA`: los de la lista de espera no aparecen, así que desde acá no se ve
quién está esperando. Para eso está el panel de recepción
([B-07](B-07-recepcion.md#58-abrir-el-panel-de-recepción)), que sí los trae con su estado.

---

## La plata

### 66. Consultar los abonos de un socio · 67. Cancelar un abono y sus clases futuras

`GET /actividades/inscripciones/socio/{id_socio}` · `POST /actividades/inscripciones/{id}/cancelar`

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Service PWA | `Proyecto - PWA/src/frontend/src/services/actividadService.ts` | 512-557 | `getMisInscripciones()`, `cancelarInscripcion()` |
| Endpoints | `backend/routers/actividades.py` | 991-1002, 1140-1181 | `inscripciones_de_socio()`, `cancelar_inscripcion()` |
| Armado | `backend/routers/actividades.py` | 969-988 | `_a_inscripcion_out()` |

**Cómo funciona la cancelación.** El abono pasa a `CANCELADA` y se cancelan **sólo las reservas
futuras** hechas con él (`:1165-1175`).

**Por qué está hecho así.** Dos decisiones, las dos en el docstring (`:1147-1156`):

*"Cancela también las reservas FUTURAS que se hicieron con él: si el abono ya no vale, las clases que
habilitaba tampoco. Las pasadas no se tocan — el socio efectivamente fue a esas clases."*

Y la que importa más: *"El pago NO se anula automáticamente: devolver plata es una decisión aparte que
se toma en la sección Cobros, y hacerla implícita acá sería reembolsar sin que nadie lo haya
decidido."* Es la misma frontera que
[la caja y sus cuatro casos](A-02-prepago-puro.md#la-caja-y-sus-cuatro-casos) dibuja: el dinero se
mueve donde alguien decide moverlo, nunca como efecto lateral de otra operación.

**Qué pasa cuando sale mal.** 404 *"La inscripción no existe."*; 400 *"Ese abono ya estaba
cancelado."*

---

### 69. Cobrar un abono de actividad a un socio

`POST /actividades/planes/{id_plan}/comprar` · Dueño, Recepcionista

**Qué resuelve.** Vender *Yoga 2 por semana*: crea la inscripción y el pago.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Service PWA | `Proyecto - PWA/src/frontend/src/services/actividadService.ts` | 524-536 | `comprarPlan()` |
| Endpoint | `backend/routers/actividades.py` | 1005-1137 | `comprar_plan()` |
| Un mes calendario | `backend/routers/actividades.py` | 69-90 | `_sumar_un_mes()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 721-723 | `comprar_plan_actividad()` |

**Cómo funciona.** Seis validaciones antes de escribir nada:

| # | Qué valida | Código | Línea |
|---|---|---|---|
| 1 | el plan está activo | 400 | `actividades.py:1029-1033` |
| 2 | la actividad no está discontinuada | 400 | `:1035-1039` |
| 3 | el socio existe | 404 | `:1041-1044` |
| 4 | **tiene la cuota al día** | 400 | `:1046-1057` |
| 5 | no tiene ya un abono activo del mismo plan | 409 | `:1059-1066` |
| 6 | **la membresía cubre el mes entero del abono** | 400 | `:1083-1090` |

Después: el precio sale del plan (`:1095`), se crea la `Inscripcion_Actividad` con su
`precio_pactado` (`:1096-1105`) y el `Pago` (`:1107-1117`), todo en una transacción.

**Por qué exige membresía vigente** (`:1013-1016`): *"Los abonos de actividad son un adicional sobre
la cuota, no un reemplazo: sin cuota al día no se puede comprar yoga."* Y el detalle de modelado:
*"Ya no es una FK (`Inscripcion_Actividad` perdió `id_membresia`); ahora es una regla que valida este
endpoint."* La FK garantizaba la relación y ataba la inscripción a **una** membresía concreta, lo que
rompía cada vez que la cuota se renovaba. La regla en el endpoint es más débil y más correcta.

**Por qué exige que la cobertura llegue al mes entero.** Es la validación 6 y la mejor argumentada del
módulo (`:1068-1082`):

> *"El abono vence UN MES DESPUÉS de comprarse, sea cual sea su `tipo_limite`: un plan '2 por semana'
> se factura mensual igual que uno de '12 clases al mes'. `tipo_limite` cambia CÓMO se mide el
> consumo, no cuándo se cobra de nuevo. Y por eso la membresía tiene que cubrir ese mes ENTERO. Si no
> llega, se rechaza acá en vez de recortar el abono en silencio: recortarlo sería cobrarle un mes y
> darle veinte días."*

Y la salida que se ofrece en vez del recorte: *"la alternativa correcta es que el mostrador cobre el
abono JUNTO con la próxima cuota (Cobros permite los dos en un solo cobro), y para eso existe
`/puede-comprar`, que deja preguntarlo ANTES de cobrar nada. 'Renovar primero' ya no es una salida:
no se cobran cuotas por adelantado."*

Ahí se ven tres reglas del sistema encajando: no se cobra por adelantado
([A-02](A-02-prepago-puro.md#sin-cobros-por-adelantado)), el abono es mensual completo, y por lo tanto
hace falta un endpoint que responda la pregunta antes de cobrar. El proceso 73 existe **por** las
otras dos.

**Nota marcada · el combo cuota + abono da 500.** `cobros.py` arma la respuesta de ese combo con la
clase `InscripcionOut` equivocada —hay **dos** definidas en `schemas.py` y la segunda pisa a la
primera—, y la arma con ocho de los catorce campos que exige. Está corrido y documentado en
[B-05, proceso 46](B-05-cobros-y-pagos.md#46-cobrar-una-cuota-en-el-mostrador). Vale nombrarlo acá porque es
justamente la salida que este docstring recomienda: el camino que el código propone para el caso de
cobertura insuficiente es el que hoy falla.

**Qué pasa cuando sale mal.** Los seis de la tabla, más 403 sin `COBRAR_PAGOS`. La línea DFD los
nombra.

---

### 73. Chequear si un socio puede comprar un abono hoy

`GET /actividades/socio/{id_socio}/puede-comprar` · Dueño, Recepcionista (o Cobros)

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Service PWA | `Proyecto - PWA/src/frontend/src/services/actividadService.ts` | 558-585 | `membresiaCubreNuevoPlan()` |
| Endpoint | `backend/routers/actividades.py` | 1188-1254 | `puede_comprar()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 717-719 | `puede_comprar()` |

**Cómo funciona.** Responde las mismas condiciones que el proceso 69 **sin comprar nada**, y devuelve
el motivo cuando no se puede.

**Por qué está hecho así.** El docstring (`actividades.py:1194-1206`): *"la vista de Cobros necesita decidir ANTES de
cobrar si ofrecer el combo 'renovar cuota + comprar abono' en una sola confirmación. Sin esto, el
flujo cobraba la membresía y recién después descubría que el abono no entraba — con la plata ya
cobrada."*

Y la frase que justifica su forma: *"Reusa exactamente las mismas condiciones que `comprar_plan`, así
el chequeo previo y la compra real no pueden desincronizarse."*

**Nota marcada · reusa las condiciones pero no el código.** Las condiciones están **escritas dos
veces**: la consulta de membresía, la comparación con `hoy` y el `_sumar_un_mes()` aparecen en
`comprar_plan()` (`:1046-1090`) y otra vez acá (`:1213-1240`). El docstring promete que no pueden
desincronizarse, y lo que garantiza eso es que alguien se acuerde de tocar los dos. La forma de
cumplir la promesa sería extraer la condición a una función —como hace `estado_renovacion()` para la
cuota (`backend/renovacion.py:56-105`), que es exactamente este patrón bien aplicado— y que los dos la
llamen. Es el mismo defecto que
[A-09](A-09-estados-derivados.md#el-dashboard-que-derivaba-por-su-cuenta) documentó en el dashboard:
una regla copiada en dos caminos.

**Nota marcada · `tiene_deuda` sobrevive por compatibilidad.** El campo se calcula derivándolo de *"no
tener la cuota al día"* (`actividades.py:1224-1228`), y el comentario lo dice: *"Se mantiene el campo `tiene_deuda`
en la respuesta (compatibilidad con las apps)"*. Y hay un `motivo` que nunca se alcanza: *"Tiene una
deuda pendiente. Regularizala antes de comprar."* (`:1245-1246`) está detrás de un `if tiene_deuda`
que, en ese punto, ya sabe que la cuota está al día — o habría salido antes con el otro motivo. Es
código muerto, resto de cuando la deuda era una tabla ([A-02](A-02-prepago-puro.md#prepago-puro)).

---

### 78. Cobrar y anotar una clase suelta sin abono

`POST /actividades/turnos/{id_turno}/clase-suelta` · Dueño, Recepcionista

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Service PWA | `Proyecto - PWA/src/frontend/src/services/actividadService.ts` | 654-672 | `comprarClaseSuelta()` |
| Endpoint | `backend/routers/actividades.py` | 1257-1387 | `comprar_clase_suelta()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 725-727 | `comprar_clase_suelta()` |

**Cómo funciona.** Turno, socio, cuota al día, no anotado, cupo, y el precio del plan `CLASE_SUELTA`
(`actividades.py:1321-1334`). Después crea la `Reserva` sin `id_inscripcion` y el `Pago`.

**Por qué está hecho así.** El docstring marca las dos diferencias con el abono (`actividades.py:1266-1274`):

*"Compite por el MISMO cupo que las reservas hechas con plan: quien paga suelto no tiene prioridad ni
lugar reservado aparte. Por eso el chequeo de cupo es idéntico al de `reservar`."* Es una decisión de
negocio disfrazada de detalle técnico: reservar cupo para las sueltas habría convertido el abono en
un peor trato.

Y: *"Exige membresía activa —hay que ser socio para entrar al gimnasio— pero NO exige que la cuota
cubra un mes: la clase es de hoy, se agota hoy. Es la diferencia con el abono, que se proyecta un mes
hacia adelante."* La validación se ajusta al **alcance temporal de lo que se vende**, y eso es lo que
hace que las dos reglas distintas sean coherentes en vez de arbitrarias.

**Nota marcada · la clase suelta sí rechaza cuando está completa.** `reservar()` manda a lista de
espera (`:407-417`); acá se responde 409 (`:1315-1320`). La asimetría tiene sentido —se está cobrando,
y poner en lista de espera a alguien que acaba de pagar obliga a decidir si se le devuelve la plata—
pero no está argumentada en el código, a diferencia de casi todo lo demás del módulo. Es la única
decisión del capítulo sin su porqué escrito.

**Qué pasa cuando sale mal.** 404 (turno o socio), 400 (clase cancelada, sin cuota al día, sin precio
de suelta cargado), 409 (ya anotado, clase completa).

---

## Los profesores habilitados

### 71. Consultar el plantel · 84. Los habilitados de una actividad · 85. Habilitar · 86. Quitar

`GET /actividades/profesores` · `GET`, `POST` y `DELETE /actividades/{id}/profesores[/{id_profesor}]`

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/actividades/ProfesorAsignacionModal.tsx` | — | `ProfesorAsignacionModal` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/actividadService.ts` | 413-476 | `seniaDeProfesor()`, `getProfesoresDeActividad()`, `asignarProfesorAActividad()`, `desasignarProfesorDeActividad()` |
| Endpoints | `backend/routers/actividades.py` | 569-609, 819-962 | `listar_todos_los_profesores()`, `listar_profesores()`, `asignar_profesor()`, `desasignar_profesor()` |
| Base | `db/schema.sql` | 577-583, 1059-1065 | `Profesor_Actividad` y las dos claves compuestas |
| Vista Flet | `Flet/Proyecto/app/views/actividades.py` | 761-846 | `_asignar_profesores()`, `_fila_profesor()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 667-673, 701-707 | `obtener_todos_los_profesores()`, `obtener_profesores_de_actividad()`, `asignar_profesor()`, `desasignar_profesor()` |

**Cómo funciona.** Dos listas y dos operaciones. El plantel (71) trae los profesores con empleado
activo y rol prendido (`:591-596`); los habilitados de una actividad (84) agregan el tercer filtro,
`ProfesorActividad.activo` (`:835-842`). Habilitar (85) reactiva la fila si existía apagada
(`:891-899`) y rechaza al que ya no cumple el rol o está de baja (`:871-886`). Quitar (86) **apaga la
fila** (`actividades.py:958-962`).

**Por qué la habilitación se apaga y no se borra.** Es el cambio del 2026-09-30 y su porqué completo
está en [la segunda fila de esa clase](A-10-bajas-logicas.md#la-segunda-fila-de-esa-clase-y-cómo-se-cerró).
En corto: esa fila hace dos trabajos —el permiso para programarle la actividad y el destino de las dos
claves compuestas que hacen legítimo cada turno **ya dictado**—, las claves no miran fechas y los
turnos no se borran nunca, así que borrarla era imposible desde la primera clase dada. **Corrido**
contra la base real: sacar a un profesor con una clase dictada ya no revienta, la fila queda apagada,
el turno sigue a su nombre, y volver a habilitarlo reactiva la misma fila.

**Nota marcada · `seniaDeProfesor()` existe para una tarjeta.** La PWA tiene una función que devuelve
un profesor con su seña —DNI o legajo— porque puede haber **homónimos**
(`actividadService.ts:413-426`). `ProfesorActividadOut` suma `dni` y `legajo` por eso mismo, y es una
de las cosas que salieron de B-03: dos profesores con el mismo nombre en un selector no se pueden
distinguir.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| La actividad no existe | 404 | *"La actividad no existe."* | `actividades.py:624-626` |
| El profesor no existe | 404 | *"El profesor no existe."* | `:869-871` |
| Ya no cumple el rol de Profesor | 409 | *"Esa persona ya no cumple el rol de Profesor…"* | `:875-879` |
| Está dado de baja | 409 | *"Ese profesor está dado de baja. Reactivalo desde Personal…"* | `:884-888` |
| Ya estaba habilitado | 409 | el del duplicado | `:901-…` |
| No estaba habilitado (al quitar) | 404 | *"Ese profesor no está asignado a esta actividad."* | `:957-960` |

Los dos 409 del medio son de la tanda del 2026-09-30 y la línea DFD ya los declara.

---

## Con qué se conecta

- **Es la misma idea que…** [estado derivado](A-09-estados-derivados.md#estado-derivado): el saldo de
  un abono se cuenta contando reservas, así que las cuatro formas de cancelar una lo recomponen sin
  escribir nada.
- **Es la misma idea que…** [precio pactado](A-02-prepago-puro.md#precio_pactado-contra-precio_actual):
  `cupo_maximo` en `Turno` y `precio_pactado` en la inscripción son copias, y las dos protegen una
  decisión ya tomada — a quien se anotó y a quien pagó.
- **Existe por culpa de…** [transacción, ACID, commit y rollback](A0-07-bases-de-datos-relacionales.md#transacción-acid-commit-y-rollback):
  el lock del turno existe porque READ COMMITTED deja que dos reservas cuenten el mismo último lugar,
  y el disparador de cupo no cubre esa carrera.
- **Se contradice con…** [sin cobros por adelantado](A-02-prepago-puro.md#sin-cobros-por-adelantado):
  el abono se cobra por mes completo y la cuota no se puede adelantar, así que cuando la cobertura no
  llega la única salida es el combo — que hoy falla.
- **Es el mismo problema que…** [el dashboard que derivaba por su cuenta](A-09-estados-derivados.md#el-dashboard-que-derivaba-por-su-cuenta):
  `puede_comprar()` promete reusar las condiciones de `comprar_plan()` y las tiene escritas dos veces.
- **Es la misma idea que…** [baja lógica](A-10-bajas-logicas.md#baja-lógica-soft-delete): la actividad,
  el plan y la habilitación del profesor se apagan en vez de borrarse, las tres porque hay historial
  colgando.
- **Existe por culpa de…** [el mostrador con cola](A-01-que-es-olimpos.md#el-mostrador-con-cola): la
  lista de espera reemplazó un rechazo, y cada error de reserva incluye qué hacer en vez de sólo qué
  está mal.
