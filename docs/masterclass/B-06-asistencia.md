# B-06 · Asistencia

*Procesos 52 a 56. Piso del capítulo: la línea que implementa cada paso, en las tres capas.*

Cinco procesos sobre el ingreso al gimnasio, en tres temas:

| Tema | Procesos |
|---|---|
| Fichar, y deshacer el fichaje mal cargado | 52, 55 |
| Lo que el panel lee | 53 |
| Lo que existe en la API y ninguna pantalla usa | 54, 56 |

Es el capítulo más corto de la Parte B y el que tiene la decisión de negocio más fuerte del
sistema: **el gimnasio no cierra la puerta**. Todo lo demás de este módulo —que no haya tope
diario, que la clase se acredite sola, que el aviso viaje aparte del rechazo— sale de ahí.

El porqué de fondo ya está en la Parte A: por qué el estado del socio se calcula y no se guarda,
en [estado derivado](A-09-estados-derivados.md#estado-derivado); qué significa "deber" sin una tabla
`Deuda`, en [prepago puro](A-02-prepago-puro.md#prepago-puro); y por qué una decisión del mostrador
no la toma el backend, en [el mostrador con cola](A-01-que-es-olimpos.md#el-mostrador-con-cola).

**Lo que se corrió, y cómo.** Nada de este capítulo se corrió: es lectura. Y hay un motivo que
conviene decir de entrada, porque es una regla del repo y no una comodidad: **fichar acredita
reservas, y borrar la asistencia no lo revierte** (`CLAUDE.md`). Probar el fichaje contra la base
real le consume la clase a un socio de verdad, y deshacerlo con el proceso 55 borra el ingreso pero
no le devuelve la reserva. Un escenario completo exigiría crear un socio marcado, una actividad, un
turno y una reserva —y ya hay un antecedente de eso quedando escrito en la base del dueño—. Lo que
sí se puede afirmar leyendo está afirmado; lo que dependería de correrlo se dice como tal.

---

## Piezas comunes

### Quién puede qué en esta sección

| Barrera | Quién la tiene | La usan |
|---|---|---|
| Sección `ASISTENCIA` en lectura | Dueño, Recepcionista (los dos en TOTAL) | 53, 54 |
| Sección `ASISTENCIA` en TOTAL | Dueño, Recepcionista | 52, 55, 56 |

Los otros cuatro roles tienen la sección en `NINGUNO`: el Entrenador y la Nutricionista con su
línea propia (`backend/permisos.py:243`, `:266`), y el Socio y el Profesor por `_SIN_ADMIN`
(`:140-150`, la de asistencia en `:145`), el diccionario que los dos desparraman con `**`
(`:295`, `:322`). Es la sección con la lista de roles más
corta de todo el sistema, y tiene sentido: fichar es la operación del mostrador y nada más. El socio
no ficha desde su teléfono —eso sería fichar por otro— y su propio historial lo ve por otro camino,
el portal ([B-14](B-14-portal-del-socio.md)).

La distinción entre lectura y TOTAL acá es fina pero real: leer el feed del día es mirar, y fichar,
desfichar o cerrar un egreso es escribir. Como los dos roles que ven la sección la tienen en TOTAL,
hoy la diferencia no separa a nadie; separa **operaciones**, y es lo que hace que agregar mañana un
rol que sólo mire no requiera tocar ningún endpoint.

### El sistema informa, no juzga

Éste es el eje del capítulo, y está escrito en el encabezado del router
(`backend/routers/asistencia.py:6-19`): cuando alguien ficha con la cuota vencida, **el ingreso se
registra igual** y la respuesta trae una advertencia. No se rechaza.

El docstring da dos razones, y son de naturaleza distinta:

**La del negocio.** *"Dejar a alguien afuera del gimnasio es algo que decide una persona en el
mostrador mirando el caso — puede ser un socio de años que se atrasó dos días, o alguien que ya
avisó que paga mañana. Un backend que devuelve 403 obliga a que ese criterio no exista."* Un 403 no
es una regla más estricta: es la eliminación del juicio humano en el único lugar donde el juicio
humano es lo correcto.

**La de los datos.** *"Si el ingreso no se registrara, el gimnasio perdería el dato de que esa
persona estuvo. Después nadie puede responder '¿cuánta gente entró en marzo?' ni detectar que un
moroso viene todos los días."* Rechazar no sólo decide mal: además destruye la información con la
que alguien podría decidir bien.

De esa decisión sale la forma del contrato de respuesta. `FicharResponse`
(`backend/schemas.py:594-615`) devuelve **201 con `permitido=False`**, que es una combinación que
suele oler mal y acá es exactamente lo que se quiere: la operación se hizo, y aparte hay algo que
mirar. El código HTTP habla del registro; `permitido` habla de la situación del socio.

> **↓ Capa 1 — por qué no son campos mezclados.** Salteable si ya viste el esquema.
>
> La respuesta separa **tres** cosas que podrían haber sido una sola:
>
> | Campo | De qué habla | La conversación en el mostrador |
> |---|---|---|
> | `advertencia` | la cuota: sin membresía, vencida, o el socio dado de baja | *"andá a pagar"* |
> | `turno_perdido` | llegó tarde a una clase que tenía reservada | *"perdiste la clase"* |
> | `clase_acreditada` | llegó a tiempo y se le contó | *"listo, ya estás anotado"* |
>
> El comentario de `turno_perdido` dice por qué va aparte de `advertencia` (`schemas.py:611-615`):
> *"son dos conversaciones distintas en el mostrador (…) Mezclarlas hace que se lea una sola y se
> ignore la otra."* Es la misma idea que
> [omitir en vez de deshabilitar](A-08-autorizacion.md#omitir-en-vez-de-deshabilitar), aplicada al
> texto: un aviso que dice dos cosas a la vez se lee como si dijera una.

**Nota marcada · la PWA tira dos de los tres.** `registrarAsistenciaManual()`
(`Proyecto - PWA/src/frontend/src/services/actividadService.ts:728-737`) se queda **sólo** con
`asistencia` y descarta `permitido`, `advertencia`, `clase_acreditada` y `turno_perdido`. Y
`AsistenciaView` saca siempre un snack verde (`:94` de `AsistenciaView.tsx`, con
`colors.statusOk` fijo). El resultado: **un socio con la cuota vencida ficha y el mostrador ve
verde**, contra el *"se muestra un aviso"* de `CLAUDE.md`. Flet sí lo muestra, en ámbar, y su
`_mostrar_resultado()` explica los tres desenlaces —*"además de 'salió' y 'falló' existe 'se
registró PERO hay algo que mirar'"*— y elige el color según `advertencia`
(`Flet/Proyecto/app/views/asistencia.py:246-277`, el color en `:275-277`). Lo notable es que el
backend hizo el trabajo entero —separó los tres campos, redactó el mensaje— y la gemela que es la
**referencia** es la que no lo usa. Ya está anotado en [A-01](A-01-que-es-olimpos.md) y en
`docs/ESTADO-ACTUAL.md`.

### El ingreso repetido se marca, no se frena

La segunda mitad de la misma decisión, y la que muestra cómo se arregla un diálogo de confirmación
que no sirve. Había dos guardas: un anti-duplicado de cinco minutos y un tope de un ingreso diario,
las dos con 409 para que el mostrador confirmara. Se sacaron las dos, y el comentario que las
reemplaza (`asistencia.py:45-66`) es la clase:

*"Quien atiende NO lee el cartel. Con gente haciendo cola, un diálogo de confirmación se acepta sin
mirarlo —y entonces no frenaba nada— o, peor, deja a un socio parado en la puerta mientras el
recepcionista descifra qué le está preguntando la pantalla."*

En su lugar, cada ingreso viaja con **`ingreso_numero`**: qué número de entrada del día es para ese
socio. El segundo se registra sin preguntar y la lista lo marca. El comentario cierra con la frase
que justifica el cambio sin perder nada: *"El conteo del día sigue siendo interpretable, porque el
dato está: son pases, y `ingreso_numero > 1` dice cuáles de ellos son repetidos."*

**Ese número no existe en ninguna columna.** Se cuenta al responder (`AsistenciaOut.ingreso_numero`,
`schemas.py:585-591`), y por eso viene en `None` donde "ingreso del día" no significa nada —el
historial de un socio, proceso 54—. Es
[estado derivado](A-09-estados-derivados.md#estado-derivado) en su versión más chica: un dato que se
calcula porque guardarlo obligaría a mantenerlo.

Las dos apps lo muestran igual, con un chip al lado del nombre: *"2º de hoy"*
(`AsistenciaView.tsx:200-206`, `views/asistencia.py:193-217`). La PWA además lo repite en el snack
del momento, y dice por qué: *"quien acaba de tocar el botón está mirando el snack, no la lista"*
(`AsistenciaView.tsx:90-94`).

### Lo que se retiró y no hay que limpiar

El fichaje por tarjeta **no tiene pantalla en ninguna de las dos apps**, y el camino RFID del
backend sigue entero: `Socio.codigo_rfid`, el campo `codigo_rfid` de `FicharRequest`
(`schemas.py:573`) y la rama que lo resuelve (`asistencia.py:147-157`). Parece código muerto y no lo
es. El encabezado de la vista de la PWA lo dice con todas las letras
(`AsistenciaView.tsx:20-33`): había una tarjeta con un input que se automantenía enfocado, pensada
para un lector —que funciona como un teclado rápido terminado en Enter—, el gimnasio no tiene lector,
y ocupaba media pantalla del mostrador sin hacer nada. *"Lo que se sacó fue el campo de texto, que no
era un lector."* El aparato físico va a ir en la puerta cuando se compre el sensor.

Es el ejemplo canónico de
[muerto en pantalla no es muerto en el código](A-01-que-es-olimpos.md#muerto-en-pantalla-no-es-muerto-en-el-código),
y los ingresos viejos con `metodo_registro='RFID'` siguen existiendo: la lista los distingue por el
ícono.

---

## Los cinco procesos

### 52. Fichar el ingreso de un socio

`POST /asistencia/fichar` · Dueño, Recepcionista

**Qué resuelve.** Registrar que alguien entró al gimnasio y, de paso y sin que nadie lo pida,
acreditarle la clase que tenía reservada.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/asistencia/AsistenciaView.tsx` | 54-229 | `AsistenciaView` (el envío, `registrarManual`, 84-99) |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/actividadService.ts` | 728-737 | `registrarAsistenciaManual()` |
| Esquemas | `backend/schemas.py` | 563-615 | `FicharRequest`, `AsistenciaOut`, `FicharResponse` |
| Endpoint | `backend/routers/asistencia.py` | 126-225 | `fichar()` |
| Situación del socio | `backend/routers/asistencia.py` | 95-123 | `_revisar_situacion()` |
| Acreditación de la clase | `backend/turnos.py` | 207-272 | `reserva_a_acreditar()` |
| Vencimiento de la reserva | `backend/turnos.py` | 65-75 | `vence_a()` |
| Vista Flet | `Flet/Proyecto/app/views/asistencia.py` | 81-139 | `_card_manual()`, `_registrar()` |
| Aviso en pantalla | `Flet/Proyecto/app/views/asistencia.py` | 246-277 | `_mostrar_resultado()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 940-982 | `fichar_manual()`, `_fichaje()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 646-651 | `fichar_manual()` |

**Cómo funciona.** El endpoint, en orden:

1. **Exactamente una vía de identificación**, o 400 (`asistencia.py:139-145`). La condición es
   `bool(datos.codigo_rfid) == bool(datos.id_socio)`, que con dos booleanos rechaza tanto "ninguna"
   como "las dos" en una sola línea. El comentario dice por qué no se aceptan ambas: *"aceptar ambas
   dejaría ambiguo a quién se fichó si discreparan"*.
2. **El socio**, por tarjeta o por id (`:147-163`). Cada rama tiene su 404 con su mensaje —*"Esa
   tarjeta no está asignada a ningún socio."* contra *"El socio no existe."*— y fija el
   `metodo_registro` que va a quedar guardado.
3. **La situación del socio**, con `_revisar_situacion()` (`:169`). Devuelve un texto o `None`, y su
   docstring pone la garantía en mayúsculas: *"NUNCA lanza: quien llama registra el ingreso igual."*
4. **La clase a acreditar**, con `reserva_a_acreditar()` (`:178`). Es el paso más interesante del
   capítulo y tiene su propia sección abajo.
5. **La fila de `Asistencia`** (`:180-195`), con el `id_reserva` de la clase acreditada y el
   `id_registrado_por` de quien tenía la sesión abierta.
6. **Confirmar, y recién después contar** (`:193-205`). El orden importa y está anotado: *"Se cuenta
   DESPUÉS del commit, así que la fila recién creada ya entra en el total: el primer ingreso del día
   da 1."*
7. **El mensaje, armado por acumulación** (`:207-216`): nombre, la clase si hubo, el número de
   ingreso si es repetido, el turno perdido si lo hubo y la advertencia si la hay. Cada pieza se
   suma si corresponde, así que el mostrador lee una sola línea con todo.

**Qué revisa `_revisar_situacion()`**, en orden de precedencia:

| Condición | Lo que devuelve | Línea |
|---|---|---|
| El socio está dado de baja | *"El socio está dado de baja."* | `asistencia.py:103-104` |
| No tiene ninguna membresía `ACTIVA` | *"No tiene ninguna membresía activa."* | `:115-116` |
| La membresía activa venció | *"La cuota venció hace N día(s) (fecha)."* | `:118-120` |
| Todo en orden | `None` | `:125` |

Es el mismo orden de precedencia que
[los seis estados del socio](A-09-estados-derivados.md#los-seis-estados-del-socio-y-su-precedencia),
recortado a lo que le importa al mostrador. Y el comentario del final cierra el hueco que alguien
buscaría: *"Ya no hay chequeo de tabla Deuda: se eliminó del esquema. El estado 'debe' es derivable,
y las dos condiciones de arriba ya lo cubren enteramente"* (`:121-124`) —
[prepago puro](A-02-prepago-puro.md#prepago-puro).

#### La clase que se acredita sola

`reserva_a_acreditar()` (`turnos.py:207-272`) es lo que convierte el fichaje en algo más que un
registro de entrada, y su docstring dice qué se está optimizando: *"Que esto sea automático es el
punto de todo el rediseño: el recepcionista no tiene que buscar a la persona, ni la clase, ni tildar
nada. Pasa la tarjeta y el sistema decide."*

Devuelve una tupla de tres desenlaces posibles, y la forma de la tupla es el contrato:

| Devuelve | Qué pasó |
|---|---|
| `(reserva, None)` | llegó a tiempo: se le acredita la clase |
| `(None, "texto")` | tenía una reserva y se le pasó la hora |
| `(None, None)` | no tenía nada reservado para ahora |

Cómo lo resuelve:

1. **Las candidatas, en una sola consulta** (`:228-239`): las reservas `RESERVADA` del socio, de
   turnos `HABILITADO`, de **hoy o de ayer**. Lo de ayer no es un descuido y está comentado: *"un
   turno de las 23:30 con tolerancia sigue vivo pasada la medianoche, y filtrar sólo por hoy lo
   perdería."*
2. **Las ya acreditadas se descartan** (`:245`, con `reservas_con_asistencia()` en `:106-122`):
   *"si alguien pasa la tarjeta dos veces no se le puede acreditar la misma clase de nuevo, ni
   saltar a la siguiente del día."* Ésta es la guarda que reemplaza al anti-duplicado que se sacó —
   el ingreso repetido se permite, pero no cobra dos veces la misma clase.
3. **La ventana**, asimétrica a propósito (`:252-256`): hacia atrás, la tolerancia de la actividad
   (`vence_a()`); hacia adelante, **dos horas**, porque *"la gente llega temprano y no tendría
   sentido no acreditarle la clase a quien vino 20 minutos antes"*.
4. **Si hay varias a tiempo, la más cercana a empezar** (`:258-262`): *"si alguien tiene dos clases
   seguidas y llega entre las dos, se le acredita la que está por empezar."*
5. **Si todas vencieron, se avisa por la más reciente** (`:264-270`): *"es la que la persona vino a
   hacer."*

La tolerancia vive en `Actividad` y no como constante, y el porqué es de negocio
(`turnos.py:69-73`): *"a una clase de Yoga llegar 20 minutos tarde es no ir, y a la sala de
musculación —abierta toda la tarde— casi no le aplica."*

**Que haya perdido el turno NO impide el ingreso**, y el comentario del endpoint lo argumenta
(`asistencia.py:175-177`): *"Rechazarlo haría que haber reservado lo dejara peor que no haber
reservado."* Es la segunda de las dos decisiones que encabezan `turnos.py` (`:27-30`), y es una
regla de diseño de sistemas de turnos que vale fuera de este repo: **una reserva nunca puede
empeorar la posición de quien reservó.**

**Qué escribe y qué lee.**

| Tabla | Atributos | Escribe o lee | Línea |
|---|---|---|---|
| `Socio` | `codigo_rfid` o la clave primaria, más `activo`, `id_sede` | lee | `asistencia.py:148-150`, `:158`, `:103`, `:182` |
| `Persona` | `nombre`, `apellido` | lee | `:207` (vía `nombre_completo`), `:71-72` |
| `Membresia` | `id_socio`, `estado`, `fecha_inicio`, `fecha_vencimiento` | lee | `:107-112`, `:118` |
| `Reserva` | `id_socio`, `id_turno`, `estado` | lee | `turnos.py:232-233` |
| `Turno` | `id_turno`, `id_actividad`, `fecha`, `estado`, `hora` | lee | `turnos.py:230`, `:234`, `:237`, `:252` |
| `Actividad` | `nombre`, `minutos_tolerancia` | lee | `turnos.py:231`, `:75`, `:269-270` |
| `Asistencia` | las que ya tienen reserva acreditada | lee | `turnos.py:115-121` |
| `Asistencia` | las del socio de hoy, para numerar | lee | `asistencia.py:87-92` |
| `Asistencia` | `id_socio`, `id_sede`, `id_reserva`, `fecha_hora_ingreso`, `metodo_registro`, `id_registrado_por` | **escribe** | `asistencia.py:180-195` |
| `Usuario` | quién ficha (de la sesión) | lee | `:194` (`sesion.id_usuario`) |

Coincide con la línea DFD.

**Por qué está hecho así.** Lo grande es la decisión de negocio, que ya está arriba. Lo propio del
código son tres elecciones:

**La acreditación se guarda en `Asistencia.id_reserva` y no como estado en `Reserva`.** El
comentario del endpoint lo dice (`asistencia.py:183-186`): *"'asistió' no es un estado guardado en
Reserva, se deriva de que exista esta fila apuntándole."* La alternativa descartada está en el
encabezado de `turnos.py` (`:11-24`): un `estado_reserva` con `ASISTIO` y `AUSENTE` obligaría a un
proceso que corra solo marcando ausentes, y *"ese proceso se cae, se atrasa o corre dos veces, y
mientras tanto el panel muestra como pendiente un turno que venció hace una hora"*. Lo que se paga:
una consulta más para saber si alguien asistió, y una función (`reservas_con_asistencia`) para
traerlas todas de una vez en los paneles. Lo que se gana lo dice la última línea: *"si el reloj
avanza, la respuesta cambia sola"*. El patrón:
[derivar en vez de almacenar](A-09-estados-derivados.md#estado-derivado).

**La lógica de turnos vive en `turnos.py` y no en el router.** El encabezado del módulo da la razón,
y es de consistencia entre pantallas (`turnos.py:4-7`): *"si el panel dice que una reserva sigue
viva y el molinete dice que venció, el mostrador deja de confiar en la pantalla."* Tres clientes
—el panel del recepcionista, el fichaje y el portal del socio— tienen que responder exactamente lo
mismo. El patrón: una
[regla resuelta en un solo lugar](A-09-estados-derivados.md#regla-resuelta-en-el-backend).

**El 201 con `permitido=False`.** La alternativa era un 200 para el caso bueno y un 4xx para el de
la cuota vencida. Se descartó porque el ingreso **ocurrió**: un 4xx diría que no se escribió nada, y
se escribió. Lo que se paga es un contrato que hay que leer con atención —y el precio se cobró
exactamente donde era previsible, en la gemela que ignora los campos extra (ver la nota de arriba).

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| Ni tarjeta ni id, o las dos | 400 | *"Indicá el código RFID o el id del socio, pero no los dos."* | `asistencia.py:139-145` |
| La tarjeta no está asignada | 404 | *"Esa tarjeta no está asignada a ningún socio."* | `:152-156` |
| El socio no existe | 404 | *"El socio no existe."* | `:160-164` |
| Sin la sección en TOTAL | 403 | el de la dependencia | `:130` |

La línea DFD nombra los tres primeros y, además, lista como salidas los **avisos** —turno perdido,
cuota vencida, socio dado de baja—, que no son rechazos: viajan en un 201. Es la distinción que el
capítulo entero explica.

---

### 53. Consultar los ingresos del día

`GET /asistencia/hoy` · Dueño, Recepcionista

**Qué resuelve.** El feed del panel: quién entró hoy, a qué hora, por qué vía, y cuál de sus
ingresos del día es cada uno.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/asistencia/AsistenciaView.tsx` | 54-229 | `AsistenciaView` (la carga, 64-82) |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/actividadService.ts` | 694-708 | `aAsistenciaRegistrada()`, `getAsistenciasDeHoy()` |
| Endpoint | `backend/routers/asistencia.py` | 228-252 | `ingresos_de_hoy()` |
| Armado | `backend/routers/asistencia.py` | 69-81 | `_a_asistencia_out()` |
| Vista Flet | `Flet/Proyecto/app/views/asistencia.py` | 143-217 | `_card_fichajes()`, `_filas_fichajes()`, `_nombre_con_chip()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 830-843 | `get_asistencias_hoy()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 638-639 | `obtener_asistencias_hoy()` |

**Cómo funciona.** Los ingresos de hoy, del más reciente al más viejo (`asistencia.py:234-240`), y
después la numeración. Ese bloque (`:242-251`) es lo único que no es trivial, y vale la pena por
cómo evita el problema en vez de resolverlo:

```python
llevados: dict[int, int] = {}
numero_de: dict[int, int] = {}
for a in reversed(asistencias):
    llevados[a.id_socio] = llevados.get(a.id_socio, 0) + 1
    numero_de[a.id_asistencia] = llevados[a.id_socio]
```

Se recorre **al revés** porque la lista viene del más reciente al más viejo y el número se cuenta
desde el primero del día. Y se cuenta en memoria, no con una consulta por fila, con el motivo
escrito al lado: *"serían N viajes a São Paulo para un dato que ya está en memoria"*
([N+1](A0-09-el-orm.md#n1), [base remota](A-11-rendimiento.md#base-remota)). Las filas ya están
traídas; numerarlas cuesta un diccionario.

**Qué escribe y qué lee.** Sólo lee: `Asistencia` (`id_asistencia`, `id_socio`,
`fecha_hora_ingreso`, `fecha_hora_egreso`, `metodo_registro`) en `:235-239`, y `Socio`
(`numero_socio`) y `Persona` (`nombre`, `apellido`) en el armado, `:70-76`. Coincide con la línea
DFD.

**Por qué está hecho así.** La ventana es el día calendario y arranca en
`datetime.combine(date.today(), datetime.min.time())` (`:234`), no en "las últimas 24 horas". Para
un mostrador, "hoy" es el día que dice el calendario: a las 9 de la mañana nadie quiere ver los
ingresos de ayer a las 11 de la noche.

**Nota marcada · el listado no carga nada por anticipado.** `_a_asistencia_out()` lee `a.socio` y
`socio.persona` por cada fila (`:70-71`), y la consulta no trae ninguna relación
(`:235-239`): son **dos consultas perezosas por ingreso**. Con veinte ingresos en el día son
cuarenta viajes de más, a 44 ms cada uno. El remedio es el mismo `selectinload` que usan los
listados de Socios y de Usuarios ([listado en lote](A-11-rendimiento.md#listado-en-lote)), y acá
falta. Leído, no medido: el número exacto depende de cuántos socios distintos haya en la lista,
porque la sesión del ORM reusa los que ya trajo ([sesión y mapa de identidad](A0-09-el-orm.md#sesión-y-mapa-de-identidad)).

**Nota marcada · una diferencia de la gemela en el contador.** Flet no refresca el subtítulo
*"N ingresos hoy"* cuando se ficha, y lo dice en vez de disimularlo
(`views/asistencia.py:269-273`): *"build_topbar recibe un string, no una referencia, así que no hay
nada a lo que apuntar. Se actualiza al volver a entrar a la sección. Dejar un update que no puede
funcionar sería peor que esta limitación anotada."* Es una limitación de
[Flet como Python manejando Flutter](A0-13-flutter-y-flet.md#control-de-flet-update-y-pageoverlay):
lo que no es un control no se puede actualizar.

**Qué pasa cuando sale mal.** Sólo 403, para los cuatro roles sin la sección.

---

### 54. Consultar el historial de ingresos de un socio

`GET /asistencia/socio/{id_socio}` · Dueño, Recepcionista

**Qué resuelve.** Ver la regularidad de un socio: sus últimos ingresos, del más reciente al más
viejo.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Endpoint | `backend/routers/asistencia.py` | 316-331 | `historial_socio()` |
| Armado | `backend/routers/asistencia.py` | 69-81 | `_a_asistencia_out()` |
| Vista PWA | — (no existe) | | |
| Vista Flet | — (no existe) | | |

**Cómo funciona.** Los ingresos de ese socio ordenados por fecha descendente, con un límite de 30
por defecto y un tope duro de 200: `.limit(min(limite, 200))` (`:329`). El `min` es la parte que
importa — sin él, `?limite=999999` sería una consulta que trae todo. `ingreso_numero` viaja en
`None` porque acá no significa nada: el comentario del esquema lo anota
(`schemas.py:590`), *"None donde 'ingreso del día' no significa nada: el historial de un socio."*

**Qué escribe y qué lee.** Sólo lee, lo mismo que el proceso 53 pero filtrado por socio
(`:326-330`). Coincide con la línea DFD.

**Por qué está hecho así.** El tope duro es
[fallar cerrado](A0-07-bases-de-datos-relacionales.md#restricción-y-tipo-enumerado) aplicado a un
parámetro de la URL: el cliente propone y el servidor acota. Y no valida que el socio exista —un
socio inexistente devuelve lista vacía, no 404—, que para un listado es defendible: la pregunta
*"¿cuándo entró?"* tiene la misma respuesta útil para "nunca" y para "no existe", y ahorra una
consulta.

**Nota marcada · ninguna pantalla lo usa.** No hay un solo cliente: ni la PWA ni Flet lo llaman
(buscado con `grep` sobre `asistencia/socio`, `historial_socio` y `historialAsistencia` en los dos
frontends, sin resultados). Es el mismo caso que
[`GET /socios/entrenadores/{id}/socios`](B-02-socios.md#19-asignarle-un-entrenador-a-cargo-a-un-socio) y que
las funciones de anular un pago de [B-05](B-05-cobros-y-pagos.md#47-anular-un-pago): existe en la
API, está bien hecho, y a la pregunta que responde —*"¿este socio viene seguido?"*— hoy no hay
ninguna pantalla donde hacérsela. El lugar natural sería la ficha del socio, al lado del botón de
contacto de emergencia.

**Qué pasa cuando sale mal.** Sólo 403. Un socio inexistente devuelve `[]`.

---

### 55. Deshacer un fichaje del día

`DELETE /asistencia/{id_asistencia}` · Dueño, Recepcionista

**Qué resuelve.** Borrar el ingreso que no ocurrió: el amigo que pasó la tarjeta por otro, o el
socio equivocado.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/asistencia/AsistenciaView.tsx` | 101-118 | `pedirDeshacer` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/actividadService.ts` | 745-747 | `deshacerFichaje()` |
| Endpoint | `backend/routers/asistencia.py` | 283-313 | `deshacer_fichaje()` |
| Vista Flet | `Flet/Proyecto/app/views/asistencia.py` | 221-242 | `_pedir_deshacer()`, `_deshacer()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 956-959 | `deshacer_fichaje()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 654-656 | `deshacer_fichaje()` |

**Cómo funciona.** Existe, o 404 (`:304-306`); es de hoy, o 400 (`:308-312`); se borra (`:314-315`).
Las dos apps confirman antes, y el texto de la PWA dice para qué es y qué pasa
(`AsistenciaView.tsx:101-118`): *"Es para el ingreso que no ocurrió —alguien que fichó por otro, o
el socio equivocado—: desaparece de la lista y deja de contar en el total del día."*

**Qué escribe y qué lee.** Lee `Asistencia` (`id_asistencia`, `fecha_hora_ingreso`) en
`asistencia.py:304` y `:308`, y **borra la fila** en `:314`. Coincide con la línea DFD.

**Por qué está hecho así.** Acá el sistema **borra de verdad**, y es la excepción que confirma la
regla de [las bajas lógicas](A-10-bajas-logicas.md#baja-lógica-soft-delete). El docstring da el
criterio (`asistencia.py:290-296`): *"un ingreso que no ocurrió no es historia que preservar: es un dato falso."*
Es exactamente la frontera que A-10 fija con la baja programada anulada —*"una baja que nunca
ocurrió no es historial de nada"*—: **se marca lo que pasó; se borra lo que nunca llegó a pasar.**

Y el límite a hoy es el otro lado de la misma decisión (`asistencia.py:298-300`): *"corregir el error del momento
es operación de mostrador; borrar la asistencia de la semana pasada sería reescribir estadísticas ya
usadas, y para eso no hay botón."* El borrado real se permite exactamente donde el dato todavía no
se usó para nada.

**Nota marcada · borrar el ingreso no le devuelve la clase.** Ésta es la consecuencia que no está
escrita en ningún comentario del endpoint y sí en `CLAUDE.md`, como advertencia para quien pruebe:
**fichar acredita reservas y borrar la asistencia no lo revierte**. El mecanismo lo explica solo: la
acreditación se deriva de que exista la fila de `Asistencia` apuntando a la reserva, así que borrar
la fila debería devolver la reserva a "pendiente"… y lo hace, pero sólo hasta que la tolerancia
vence. Si el turno ya pasó, la reserva queda como ausente y la clase está consumida igual. Para el
caso de negocio real —el ingreso cargado al socio equivocado, corregido en el momento— el turno casi
siempre sigue vivo y no hay problema. Para el que prueba en la base real, hay. Leído, no corrido: es
lo que hace que probar este proceso contra Neon sea caro, y por eso este capítulo no lo corrió.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| El ingreso no existe | 404 | *"Ese registro de ingreso no existe."* | `asistencia.py:304-306` |
| No es de hoy | 400 | *"Sólo se pueden deshacer los ingresos de hoy."* | `:308-312` |

Coincide con la línea DFD.

---

### 56. Registrar el egreso de un ingreso

`POST /asistencia/{id_asistencia}/salida` · Dueño, Recepcionista

**Qué resuelve.** Marcar a qué hora se fue alguien.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Endpoint | `backend/routers/asistencia.py` | 255-280 | `registrar_salida()` |
| Vista PWA | — (no existe) | | |
| Vista Flet | — (no existe) | | |

**Cómo funciona.** Existe, o 404 (`:269-271`); no tenía egreso cargado, o 400 (`:273-275`); se
escribe la hora actual (`:277`).

**Qué escribe y qué lee.** Lee la fila y su `fecha_hora_egreso` (`:269`, `:273`); escribe
`fecha_hora_egreso` (`:277`). Coincide con la línea DFD.

**Por qué está hecho así.** El docstring contesta la pregunta que uno se hace al ver una columna
nullable (`:262-266`): *"Es opcional: la mayoría de los gimnasios no controla la salida, y un
ingreso sin egreso es un registro válido —significa 'entró'—, no un dato incompleto."* Eso es lo que
justifica que `Asistencia.fecha_hora_egreso` sea nullable y que ninguna consulta la exija: el nulo
no es un dato que falta, es la respuesta.

El 400 cuando ya había egreso es lo contrario de
[idempotencia](A0-03-http.md#método-http-e-idempotencia), y acá es correcto: pisar la
hora de salida sin avisar convertiría un error de tipeo en un dato silenciosamente cambiado.

**Nota marcada · tampoco tiene pantalla.** Como el 54, no lo llama nadie
(buscado con `grep` sobre `/salida` y `registrarSalida` en los dos frontends). A diferencia del 54,
acá la ausencia es coherente con el propio docstring: si *"la mayoría de los gimnasios no controla
la salida"*, no tener el botón es la decisión y no el olvido. Lo que queda por decidir es si el
endpoint se queda esperando el molinete —como el camino RFID del proceso 52, que sí está anotado
como pendiente— o si sobra. Hoy es la única pieza del módulo sin un motivo escrito para existir.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| El ingreso no existe | 404 | *"Ese registro de ingreso no existe."* | `asistencia.py:269-271` |
| Ya tenía la salida cargada | 400 | *"Ese ingreso ya tenía la salida registrada."* | `:273-275` |

Coincide con la línea DFD.

---

## Con qué se conecta

- **Se contradice con…** [el frontend esconde, el backend rechaza](A-08-autorizacion.md#el-frontend-esconde-el-backend-rechaza):
  acá el backend **no** rechaza a propósito, y el frontend tampoco esconde: informa. Es el único
  módulo donde la regla se invierte, porque la decisión es de una persona y no del sistema.
- **Es la misma idea que…** [estado derivado](A-09-estados-derivados.md#estado-derivado): ni el
  número de ingreso del día ni el "asistió" de una reserva se guardan; los dos se cuentan al
  responder, y por eso no hay nada que pueda quedar desincronizado.
- **Existe por culpa de…** [el mostrador con cola](A-01-que-es-olimpos.md#el-mostrador-con-cola):
  el tope diario y el anti-duplicado se sacaron porque un diálogo de confirmación no frena nada
  cuando quien atiende está apurado; el chip *"2º de hoy"* conserva el dato sin pedir permiso.
- **Es la misma idea que…** [baja lógica](A-10-bajas-logicas.md#baja-lógica-soft-delete): desfichar
  borra la fila de verdad, y por la misma frontera que hace que una baja anulada se borre — se marca
  lo que pasó, se borra lo que nunca ocurrió.
- **Es el mismo problema que…** [listado en lote](A-11-rendimiento.md#listado-en-lote): al feed del
  día le faltan las dos relaciones en la carga anticipada, y vuelve a crecer una consulta por
  ingreso.
- **Existe por culpa de…** [muerto en pantalla no es muerto en el código](A-01-que-es-olimpos.md#muerto-en-pantalla-no-es-muerto-en-el-código):
  el camino RFID del fichaje no tiene pantalla y no se limpia, porque el lector va a existir como
  aparato en la puerta.
