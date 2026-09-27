# A-01 · Qué es OlimpOS y qué problema resuelve

*Piso del capítulo: los pasos que cuesta una operación de mostrador, contados uno por uno, y el
aviso que el sistema muestra en el lugar exacto donde podría haber rechazado.*

Éste es el único capítulo de la masterclass que no habla de software. Habla de un gimnasio: quién
trabaja ahí, con qué aparato en la mano y cuánta gente tiene esperando atrás. Parece contexto y es
lo contrario. La mitad de las decisiones del código —que no haya tope de ingresos por día, que el
alta de un socio no pregunte el plan, que una contraseña se mande por WhatsApp con un botón, que un
socio con la cuota vencida entre igual— no se deducen de ninguna tecnología. Se deducen de acá.

Casi no usa la Parte A0: los pocos términos técnicos que aparecen se enlazan a su capítulo la primera
vez. Lo que define son tres conceptos, y el resto de la masterclass los nombra cada vez que una
decisión se explica "por el mostrador" o "porque el sistema informa": [OlimpOS](#olimpos),
[el mostrador con cola](#el-mostrador-con-cola) y
[el sistema informa, no juzga](#el-sistema-informa-no-juzga).

---

## OlimpOS

### Un gimnasio, una sede

OlimpOS es el sistema de gestión de **un** gimnasio, y el singular es literal. El esquema admite
varias sedes —la tabla `Sede` existe y cada socio apunta a una—, pero el sistema opera una sola: la
PWA dejó de mandar la sede como parámetro porque *"el sistema opera una sola sede y el backend
devuelve todos los turnos"* (`Proyecto - PWA/src/frontend/src/services/actividadService.ts:578-586` ·
`getTurnosDisponibles()`).

Las decisiones que este capítulo explica las toma quien encarga el sistema, a quien `CLAUDE.md` llama
**el dueño**. El nombre se presta a confusión y conviene fijarlo: es la persona que decide cómo tiene
que comportarse el gimnasio, y al probar el sistema entra, justamente, con la cuenta del Dueño.

### Seis clases de personas, y una sola con gente esperando

| Quién | Con qué pantalla | Qué hace ahí | Quién espera mientras tanto |
|---|---|---|---|
| **Recepcionista** | la PC del mostrador: fija, con teclado y mouse, abierta el día entero | registra cada ingreso, cobra, da de alta, contesta a qué hora es la clase | **la fila del mostrador** |
| **Dueño** | la misma PC, o la PWA desde cualquier navegador | lo mismo que el recepcionista, más la facturación y el personal | la fila, cuando atiende el mostrador; nadie, cuando mira los números |
| **Entrenador** | la PWA | arma y asigna rutinas | nadie |
| **Nutricionista** | la PWA | arma y asigna dietas | nadie |
| **Profesor** | la PWA, sólo "Mis clases" | mira quién se anotó a su turno | nadie |
| **Socio** | la PWA, en su celular | paga, reserva, sigue su rutina y su dieta, cuenta repeticiones con la cámara | nadie: el que espera es él, entre serie y serie |

La última columna es la que ordena el sistema. De las seis, **una sola trabaja con gente esperando**,
y es la que hace la operación más frecuente del gimnasio: registrar a cada persona que entra. Esa
coincidencia —la única persona apurada es la que más veces toca la pantalla— convierte al mostrador
en la restricción de diseño que explica la mitad del código, y tiene su propia sección:
[el mostrador con cola](#el-mostrador-con-cola).

El socio está en la otra punta: nadie lo apura, pero tiene el celular en una mano y la atención en el
ejercicio. El README lo dice de su portal: *"está hecho para usarse desde el teléfono, parado en el
gimnasio"*. Por eso el contador de repeticiones mira por la cámara en vez de pedir que se tipee, y
corre en el propio teléfono ([inferencia en el dispositivo](A0-14-vision-en-el-dispositivo.md#inferencia-en-el-dispositivo)).

Cómo sabe el sistema cuál de las seis es cada persona —no hay una columna que lo diga— es la
[derivación de roles](A-06-los-seis-roles.md#derivación-de-roles); qué puede hacer cada una, la
[matriz de permisos](A-08-autorizacion.md#matriz-de-permisos).

### La apuesta del producto

`CLAUDE.md` la escribe en una frase: que la app del socio sea *"tan útil que la gente elija el
gimnasio por la app"*. Un sistema de gestión de gimnasio suele ser una herramienta de la
administración —cuotas, ingresos, caja— que el socio nunca ve. Éste invierte el peso, y se nota en el
código: el portal del socio es el archivo más grande del backend (`backend/routers/portal.py`, 2.432
líneas) y concentra 43 de sus rutas, la cuarta parte de toda la API. Ahí viven la rutina y la dieta
que el socio se arma solo, el registro de lo que entrenó y comió, su progreso, y la autogestión de la
membresía: pausarla o darse de baja. Pagar la cuota desde el celular tiene su propio router,
`backend/routers/pagos_online.py`.

La siguiente pieza de esa apuesta ya está decidida y sin escribir: un coach con IA que le habla al
socio con Claude por API y que, sobre los mismos endpoints del portal, **propone, el socio confirma y
recién ahí aplica** (`docs/ESTADO-ACTUAL.md`, "Grandes, después de la lista").

La otra mitad de la idea es que el personal gestione el gimnasio *"sin fricción"*, y es el resto de
este capítulo.

### Las condiciones del encargo

- **Un proyecto escolar con presupuesto ilimitado y una entrega final por delante.** El presupuesto
  explica que haya servicios pagos en la lista —una base administrada, Mercado Pago, la API de
  Claude—. La entrega explica el nivel de exigencia: *"cuando se acerque el final de entrega del
  proyecto tengo que probar absolutamente todo"*, dejó anotado el dueño (`A CORREGIR PWA .txt`).
- **Pensado para servidores locales.** El backend corre en una máquina del gimnasio
  (`http://127.0.0.1:8000`, según el README), y la única pieza que puede estar afuera es la base:
  hoy es Neon, en São Paulo, y pasar a un Postgres local es cambiar `DATABASE_URL`, *"lo único que
  cambia entre uno y otro"* (README, "Configuración"). Qué cuesta que esté afuera es la
  [base remota](A-11-rendimiento.md#base-remota).
- **Los requisitos llegan probando.** El dueño recorre el sistema rol por rol en la PWA y anota lo que
  encuentra en `A CORREGIR PWA .txt`, en la raíz del repo; una línea de asteriscos separa lo ya
  resuelto de lo nuevo. Ese archivo es la voz del gimnasio adentro del repo, y varias de las
  decisiones de este capítulo empezaron como una línea ahí.

### Las tres piezas, nombradas

> **↓ Capa 1 — las dos apps y el backend, nombrados.** Éste es el piso.

| Pieza | Carpeta | Hecha con | La usan |
|---|---|---|---|
| **La PWA** | `Proyecto - PWA/src/frontend` | [React](A0-06-react.md) + TypeScript + Vite + Tailwind | los seis roles, desde el navegador o instalada en el celular |
| **La app de escritorio** | `Flet/Proyecto` | Python + [Flet](A0-13-flutter-y-flet.md) 0.84 | la PC del mostrador: Recepcionista y Dueño |
| **El backend** | `backend/` | [FastAPI](A0-10-python-del-lado-del-servidor.md#asgi-uvicorn-y-el-router) + [SQLAlchemy](A0-09-el-orm.md) sobre Postgres | las dos apps, y nadie más |

PWA es *progressive web app*: una página web que el celular instala como si fuera una aplicación,
gracias a un [service worker](A0-04-el-navegador-por-dentro.md#service-worker). Las dos apps hablan
con el mismo backend y la misma base; por qué son dos, y qué implica que la PWA sea la referencia y
Flet su gemela, es [dos aplicaciones, un backend](A-03-dos-apps-un-backend.md#dos-aplicaciones-un-backend).

---

## El mostrador con cola

### El problema

`CLAUDE.md` abre la sección sobre cómo piensa el dueño con esta frase: *"Piensa como el gimnasio de
verdad. La persona del mostrador con cola no lee carteles, así que un diálogo de confirmación no frena
nada."*

La escena es concreta. Las clases empiezan a hora fija, así que la gente no llega repartida: llega en
tandas, y cada una pasa por el mostrador. Del otro lado hay una persona
resolviendo una cosa después de otra con alguien enfrente y varios detrás. En ese rato, el tiempo de
esa persona es el recurso más escaso del gimnasio, y cada pantalla que usa lo está gastando. De ahí
salen dos consecuencias, cada una con su subsección: el cartel que nadie lee, y los pasos que se pagan
multiplicados.

### El cartel que nadie lee

Un diálogo de confirmación supone que alguien lo lee. Jef Raskin describió en *The Humane Interface*
(2000) por qué ese supuesto falla: una pregunta que aparece en una operación de todos los días, y que
casi siempre se contesta igual, se vuelve un reflejo. La mano aprieta "Aceptar" antes de que el ojo
termine de leer, y la confirmación deja de confirmar. Aza Raskin lo resumió en 2007 en el título de un
artículo, *Never Use a Warning When you Mean Undo*: si lo que se quiere es poder volver atrás, se deja
hacer y se ofrece deshacer.

El repo lo escribió con palabras de mostrador, en el comentario que explica por qué el fichaje no
pregunta nada (`backend/routers/asistencia.py:51-54`):

> *"quien atiende NO lee el cartel. Con gente haciendo cola, un diálogo de confirmación se acepta sin
> mirarlo —y entonces no frenaba nada— o, peor, deja a un socio parado en la puerta mientras el
> recepcionista descifra qué le está preguntando la pantalla."*

Las dos salidas del diálogo son malas: si no se lee, no protege; si se lee, frena la fila. No hay un
tercer caso en el que sirva.

Lo que lo reemplaza es deshacer. Un ingreso cargado por error —el amigo que fichó por otro, el socio
equivocado— se borra con `deshacer_fichaje()` (`asistencia.py:283-313`), y sólo si es de hoy
(`:306-310`), porque *"corregir el error del momento es operación de mostrador; borrar la asistencia
de la semana pasada sería reescribir estadísticas ya usadas"* (`:297-299`). Y deshacer sí pide
confirmación (`Proyecto - PWA/src/frontend/src/views/asistencia/AsistenciaView.tsx:101-118` ·
`pedirDeshacer`), lo que parece contradecir todo lo anterior y en realidad lo completa. Fichar pasa
una vez por cada persona que entra y se puede corregir; desfichar es la excepción y **borra la fila de
verdad** (`asistencia.py:292-295`), así que no hay nada que lo deshaga a él. La pregunta se pone donde
la operación es rara e irreversible, nunca donde es frecuente y se puede corregir. El otro caso donde el
sistema sí pregunta, el cobro, está explicado con su motivo en
[el recorrido de un pedido](A-04-recorrido-de-un-pedido.md#el-diálogo-y-por-qué-confirmar-acá-no-es-una-molestia).

### La cantidad de pasos que cuesta una operación

> **↓ Capa 1 — los pasos, contados.** Éste es el piso.

Para comparar decisiones hace falta una unidad. Acá se usa el **paso**: cada acción del operador que
le exige mirar la pantalla —un click, un dato tipeado, un cartel leído—. Cuatro operaciones de
mostrador, contadas en el código tal como están y tal como estarían sin la decisión que las acortó:

| Operación | Sin la decisión | Con la decisión | Dónde está |
|---|---|---|---|
| Registrar el segundo ingreso del día de un socio | buscarlo · "Registrar ingreso" · leer el cartel · confirmar — **4** | buscarlo · "Registrar ingreso" — **2** | `backend/routers/asistencia.py:45-66`; `AsistenciaView.tsx:35-42` |
| Cobrarle la primera cuota al socio que se acaba de dar de alta | cerrar el panel del alta · ir a Cobros · buscarlo · elegirlo — **4** | "Cobrar ahora" — **1** | `Proyecto - PWA/src/frontend/src/views/socios/SocioFormModal.tsx:157-170`; `…/views/cobros/CobrosView.tsx:150-172` |
| Hacerle llegar la contraseña temporal a quien se acaba de dar de alta | seleccionarla · copiarla · abrir WhatsApp · abrir un chat con su número · escribirle qué tiene que hacer · pegarla · enviar — **7** | "Enviar por WhatsApp" · enviar — **2** | `Proyecto - PWA/src/frontend/src/components/PanelCredenciales.tsx:112-122`; `…/src/utils/contacto.ts:38-52` · `linkWhatsapp()` |
| En la app de escritorio, atender a una socia que llega a su clase con la cuota vencida: cobrarle y registrar el ingreso | ir a Asistencia · buscarla · "Registrar ingreso" · ir a Cobros · buscarla · elegirla · "Cobrar membresía" — **7** | tocar cobrar · tocar registrar, en su fila de la lista del turno — **2** | `Flet/Proyecto/app/views/recepcion.py:547-591` · `_inscripto()`; `backend/routers/recepcion.py:72-108` · `_alerta_de_socio()` |

Cómo leer cada fila:

- **La primera** es historia: el cartel lo provocaban dos guardas del backend que rechazaban el
  ingreso repetido con un 409 para que el mostrador lo confirmara (`asistencia.py:47-49`). Qué eran y
  por qué se sacaron es [el origen del principio siguiente](#el-origen-una-regla-escrita-para-la-plata-que-terminó-valiendo-para-la-puerta).
- **La segunda** cuenta el camino que existiría sin el botón. "Cobrar ahora" pone al socio en la URL
  (`?socio=<id>`) y Cobros lo elige solo al abrir.
- **La tercera** es historia para el reseteo de contraseña, que antes mostraba la clave *"en un snack
  persistente, o sea que quien la reseteaba tenía que copiarla a mano de un cartelito antes de
  cerrarlo"* (`PanelCredenciales.tsx:9-14`), y para el alta de empleados, donde el dueño lo había
  anotado como *"insólito tener que copiar y guardarme la contraseña"*. Hoy el botón abre
  `https://wa.me/<número>?text=<mensaje>` con el texto que arma el backend (`PanelCredenciales.tsx:16-19`).
- **La cuarta** compara las dos formas que tiene la app de escritorio de hacer lo mismo. En Recepción
  la socia **no se busca**: aparece en la lista del próximo turno con *"Cuota vencida hace N día(s)"*
  al lado del nombre (`backend/routers/recepcion.py:97`), y los dos botones están en su fila. Vale
  para las clases con lista de anotados; la sala abierta, sin profesor y con cupo grande, se muestra
  como un contador (`CUPO_SALA_ABIERTA`, mismo archivo). El cobro abre el mismo diálogo en los dos
  caminos, y ese diálogo no se cuenta en ninguno.

Los pasos no valen lo mismo en todas las operaciones: se pagan **una vez por cada vez que la operación
ocurre**. Registrar un ingreso ocurre por cada persona que entra; dar de alta, una vez por socio en
toda su vida en el gimnasio. Con números de ejemplo —no medidos en este gimnasio—: si entran 150
personas por día y se dan de alta 3, un paso de más en fichar son 150 pasos diarios, y uno de más en
el alta son 3. Por eso registrar un ingreso es la operación con menos pasos del sistema —en Recepción,
a veces uno solo— y ninguna pregunta, mientras que el alta se permite un formulario largo.

### Menos pasos y más completo

La frase es de `CLAUDE.md`, y la segunda mitad importa tanto como la primera: sacar un paso no puede
costar información. Si Recepción ahorrara la búsqueda pero obligara a ir a otra pantalla a ver si la
persona debe, el paso volvería por otro lado. El resultado de buscar a alguien en Recepción trae, en la
misma tarjeta, la cuota, el aviso y el próximo turno, y el comentario dice por qué: *"una sola búsqueda
tiene que cerrar la conversación, no abrir tres pantallas más"* (`Flet/Proyecto/app/views/recepcion.py:230-237`
· `_ficha()`).

Esa promesa tiene un costo en el backend, y el backend lo asume en su diseño. `backend/routers/recepcion.py`
es el único router organizado por **pantalla** y no por entidad (docstring, líneas 8-17): devuelve en
un solo pedido todo lo que el mostrador necesita ver junto, porque armarlo con los endpoints de
turnos y de asistencias serían *"cuatro o cinco pedidos por refresco, cada uno con su latencia"*. Los
pasos que el operador no da tampoco los da la red.

### La cola que no se forma

La otra forma de acortar la fila es sacar gente de ella. Probando la pantalla de Cobros, el dueño lo
escribió así: *"el socio paga desde su celu o pc y listo qué tiene que estar el recepcionista o dueño
cobrando, no tiene sentido realmente, yo entiendo solamente el caso de efectivo"*
(`A CORREGIR PWA .txt`). De esa línea salió la regla que deja el cobro de mostrador para pocos casos
([la caja y sus cuatro casos](A-02-prepago-puro.md#la-caja-y-sus-cuatro-casos)): todo lo que el
socio puede hacer desde su celular es una persona menos en la fila.

Hay una operación que, por diseño, no puede salir del mostrador: el alta. La cuenta de una persona nace
de un alta que hace el personal, nunca de la persona misma ([no existe "Registrarse"](A-07-autenticacion.md#no-existe-registrarse)).
Por eso es la operación con más atajos: la clave se manda con un botón, el cobro se abre con la
persona ya elegida, y los dos están en la misma ventana que confirma el alta, mientras la persona
sigue ahí enfrente.

### Por qué está hecho así

**Qué se optimiza:** el tiempo de la persona del mostrador, en las operaciones que más se repiten.

**Qué restricción acorrala:** una sola persona, una fila, y una pantalla que no se lee cuando hay apuro.

**Qué alternativas se descartaron:**
- Proteger con confirmaciones, que es lo que hacían las guardas del fichaje hasta que se sacaron, por
  las razones de [el cartel que nadie lee](#el-cartel-que-nadie-lee).
- Buscar por nombre. Recepción busca por DNI, y lo justifica (`recepcion.py:173-181` · `_buscador()`):
  *"Buscar 'gonzalez' devuelve cuatro personas y obliga a preguntar cuál; el DNI devuelve una"*.
  Acepta los últimos dígitos, *"que es como la gente los dicta"*, y responde a Enter
  (`:186-188`) porque *"en un mostrador se tipea y se aprieta Enter sin soltar el teclado"*.

**Qué se paga:** el sistema deja pasar cosas que un sistema desconfiado frenaría. Un ingreso repetido
por error queda registrado hasta que alguien lo borra a mano. Y cada atajo es un camino más que existe
dos veces: "Cobrar ahora" está en la PWA y en Flet (`Flet/Proyecto/app/views/socios.py:587` ·
`cobrar_ahora()`), y los dos hay que mantenerlos iguales.

**Cómo se llama:** *deshacer en vez de confirmar*, para las preguntas; y, para el router de Recepción,
un **endpoint por pantalla**, lo que en la industria se conoce como *backend for frontend*.

---

## El sistema informa, no juzga

### El origen: una regla escrita para la plata que terminó valiendo para la puerta

La regla nació el 10/08/2026, con la primera versión de `backend/routers/asistencia.py` (commit
`7427764`), que ya se abría con este docstring (hoy en las líneas 6-19):

> *"Cuando alguien ficha con una deuda o la cuota vencida, el ingreso **se registra igual** y la
> respuesta trae una advertencia. No se rechaza. (…) dejar a alguien afuera del gimnasio es algo que
> decide una persona en el mostrador mirando el caso — puede ser un socio de años que se atrasó dos
> días, o alguien que ya avisó que paga mañana. Un backend que devuelve 403 obliga a que ese criterio
> no exista."*

El mismo archivo, sin embargo, sí juzgaba en otro lado. Un anti-duplicado
(`MINUTOS_ANTI_DUPLICADO = 5`) rechazaba con 409 el segundo ingreso dentro de los cinco minutos,
pensado para *"pasar la tarjeta dos veces porque el lector no sonó"* con un lector que el gimnasio no
tiene. Y cuando el dueño probó el panel, pidió ir más lejos en esa dirección: *"debería haber un
límite de fichajes por día de la misma persona si o si"*, pensando en quien pasa la tarjeta todo el
día para molestar, y a la vez en el caso que un tope castigaría —alguien que paga la cuota y entra
varias veces por día por motivos que no son entrenar—. Y cerró con un pedido: *"Planteame una solución
inteligente"* (`A CORREGIR PWA .txt`).

La respuesta que quedó, en el commit `3d4df15` del 16/09/2026, no fue el tope. El comentario que
ocupa hoy el lugar de las guardas registra que llegó a haber dos —el anti-duplicado y un tope de un
ingreso diario— y que *"Se sacaron las dos"* (`asistencia.py:47-49`). En su lugar se **marca** en vez
de frenar: cada ingreso viaja con su número del día, y la lista muestra "2º de hoy" al lado del
nombre. El mismo comentario (`:55-63`) generaliza la regla: *"la regla vale igual para entrar dos veces que para deber plata"*, y resuelve los
dos casos del dueño a la vez: *"El que pasa diez veces para joder queda a la vista de quien quiera
mirarlo; el que entrena a la mañana y vuelve a la clase de la tarde entra sin que nadie confirme
nada."*

El principio, entonces, no es "el sistema es permisivo". Es que **el sistema no toma decisiones que
dependen de algo que sólo ve la persona del mostrador**: le da el dato, y la decisión queda donde está
la información.

### El aviso mostrado en vez del bloqueo

> **↓ Capa 1 — cómo se escribe "informar" en el backend.** Salteable si leés código a diario.

La decisión está escrita en la firma de una función. `_revisar_situacion()`
(`backend/routers/asistencia.py:95-123`) devuelve `str | None`: un texto si hay algo que mirar, nada si
no. Su docstring lo dice sin vueltas: *"NUNCA lanza: quien llama registra el ingreso igual"*. Revisa, en
orden, si el socio está dado de baja (`:102-103`), si no tiene membresía activa (`:113-114`) y si la
cuota está vencida, con cuántos días (`:116-118`).

La diferencia entre informar y juzgar es la diferencia entre **devolver** y **lanzar**. Una función que
lanza un `HTTPException` corta el pedido: el [código de estado](A0-03-http.md#código-de-estado) sale
403 y la fila nunca se escribe. Una función que devuelve un texto no puede cortar nada, por
construcción. Quien lea `-> str | None` ya sabe, sin leer el cuerpo, que esa revisión no va a dejar a
nadie afuera.

`fichar()` (`asistencia.py:126-225`) usa ese texto sin preguntarle nada:

- Calcula la advertencia (`:169`) y después escribe la fila de `Asistencia` y la confirma
  (`:180-195`) sin consultarla: ningún camino entre esas dos líneas depende de lo que dijo.
- Responde siempre 201, *"aunque el socio tenga problemas: el campo `permitido` y la `advertencia` son
  lo que le dice al mostrador que mire el caso"* (`:135-136`).
- Arma un `mensaje` que suma todo lo que el mostrador tiene que decir en voz alta: a qué clase se le
  acreditó, qué número de ingreso del día es, si perdió el turno, y la advertencia (`:206-216`).

Esto no es un detalle de la pantalla: está en el contrato del proceso. La línea DFD del proceso 52 de
`PROCESOS-LOGICOS-REQUERIDOS.md` declara como salida el *"Ingreso registrado con la clase acreditada,
con aviso de turno perdido, de cuota vencida o de socio dado de baja"* (cómo se lee esa notación está en
[DFD lineal](A-12-como-leer-los-procesos.md#dfd-lineal)). El aviso forma parte de lo que el proceso
entrega.

Los rechazos que sí quedan en `fichar()` (`:140-163`) no son juicios: son los casos en que no hay a
quién registrar —se mandaron dos identificaciones a la vez, la tarjeta no es de nadie, el socio no
existe—. El sistema rechaza lo que no puede hacer, no lo que desaprueba.

> **↓ Capa 2 — tres desenlaces, tres colores.** Éste es el piso.

Del lado de la pantalla, informar es un color. La app de escritorio lo escribe en el docstring de
`_mostrar_resultado()` (`Flet/Proyecto/app/views/asistencia.py:245-277`):

> *"Tres desenlaces, no dos: además de 'salió' y 'falló' existe 'se registró PERO hay algo que mirar'
> — el socio debe, o tiene la cuota vencida. En ese caso el ingreso SÍ queda guardado y se avisa en
> amarillo."*

| Desenlace | Qué pasó en la base | Color | Dónde |
|---|---|---|---|
| Salió | hay fila en `Asistencia` | verde, `STATUS_OK` | `asistencia.py:275-277` |
| Salió, con algo que mirar | hay fila en `Asistencia` | ámbar, `STATUS_WARN`, con el texto de la advertencia | `asistencia.py:275-277` |
| Falló | no hay fila | rojo, `STATUS_DANGER` | `asistencia.py:256-258` |

Recepción aplica la misma regla y deja escrita la prohibición que la sostiene: *"Nunca rojo: el ingreso
SE registró igual"* (`Flet/Proyecto/app/views/recepcion.py:323-325` · `_fichar()`). Ése es el piso del
principio: entre informar y juzgar no hay más distancia que un color en el aviso de abajo de la
pantalla y la existencia de una fila. Si el aviso sale en ámbar y la fila está, el sistema informó. Si
sale en rojo y la fila no está, juzgó.

El mismo panel lleva la idea un paso antes del ingreso: `_alerta_de_socio()`
(`backend/routers/recepcion.py:72-108`) avisa también cuando a la cuota le faltan tres días o menos,
*"para que vuelva ese día"*, y aclara que *"es un aviso, no un cobro"*.

### Nota marcada · en la PWA el tercer desenlace no llega a la pantalla

La PWA, que es la referencia de las dos apps, tiene dos desenlaces y no tres.

`registrarAsistenciaManual()` (`Proyecto - PWA/src/frontend/src/services/actividadService.ts:728-737`)
tipa la respuesta del backend como `{ asistencia: AsistenciaApi }` (`:732`) y devuelve sólo
`datos.asistencia` (`:736`). Todo lo demás que el backend mandó —`permitido`, `advertencia`, `mensaje`,
`clase_acreditada`, `turno_perdido`— llega por la red y se descarta en esa línea. La vista, después,
arma su propio aviso, siempre verde: *"Ingreso registrado: {nombre}"*
(`views/asistencia/AsistenciaView.tsx:94`).

La consecuencia es precisa: un socio con la cuota vencida ficha desde la PWA, el backend registra el
ingreso y avisa, y el recepcionista ve verde. El sistema no juzgó, pero tampoco informó, que era la
mitad de la regla. El comentario del mismo service (`actividadService.ts:717-721`) describe la
advertencia que devuelve el backend, y la función que está debajo la tira.

Es un caso invertido de la regla de las gemelas: acá la que hace lo que dice `CLAUDE.md` —*"Con la
cuota vencida ficha igual y se muestra un aviso"*— es Flet. Queda anotado como hallazgo y no se corrigió
al escribir este capítulo.

### Dónde el sistema sí juzga

El principio tiene una frontera, y el código la muestra caso por caso:

| El sistema decide solo | Por qué ahí sí |
|---|---|
| No se cobra un período mientras hay otro en curso: 409 ([sin cobros por adelantado](A-02-prepago-puro.md#sin-cobros-por-adelantado)) | la decisión depende sólo de fechas que el sistema tiene, y protege el precio del gimnasio; nadie en el mostrador sabe algo que la cambie |
| Una cuenta trabada responde igual que una clave equivocada ([freno de intentos y respuesta indistinguible](A-07-autenticacion.md#freno-de-intentos-y-respuesta-indistinguible)) | quien está del otro lado puede ser un atacante, y cualquier dato de más lo ayuda: ahí el sistema ni siquiera informa |
| Quien no tiene permiso recibe 403 ([el frontend esconde, el backend rechaza](A-08-autorizacion.md#el-frontend-esconde-el-backend-rechaza)) | la matriz de permisos ya es la decisión de una persona, tomada antes |
| La base rechaza un DNI repetido (`db/schema.sql:83`, `UNIQUE`; ver [restricción y tipo enumerado](A0-07-bases-de-datos-relacionales.md#restricción-y-tipo-enumerado)) | dos personas con el mismo DNI harían ambigua cada búsqueda del mostrador, y ninguna persona puede arreglarlo mirando |

El criterio que ordena la tabla es una sola pregunta: **¿quién tiene la información para decidir?**
Si depende de algo que sólo ve una persona —que el que debe es un socio de años, que avisó que paga
mañana—, el sistema informa y la persona decide. Si depende sólo de datos que el sistema ya tiene, o
de protegerse de alguien que no está del lado del gimnasio, el sistema decide solo.

### Por qué está hecho así

**Qué se optimiza:** que cada decisión la tome quien tiene la información, y que no se pierda el dato
de que alguien entró. El docstring da esta segunda razón aparte (`asistencia.py:16-19`): si el ingreso
no se registrara, *"nadie puede responder '¿cuánta gente entró en marzo?' ni detectar que un moroso
viene todos los días"*. Rechazar el ingreso no sólo deja a alguien afuera: borra la prueba de que vino.

**Qué restricción acorrala:** el backend no ve a la persona; el mostrador sí.

**Qué alternativa se descartó:** el torniquete lógico —sin cuota paga no se entra—, que es la lectura
más literal de [prepago puro](A-02-prepago-puro.md#prepago-puro). Prepago quiere decir que se cobra
antes del período, no que sin pago se cierra la puerta.

**Qué se paga:** alguien puede entrenar con la cuota vencida hasta que una persona lo mire, y el
sistema depende de que esa persona lea el ámbar. Que es exactamente lo que falla en la PWA hoy (nota
de arriba): cuando se informa en verde, el costo se paga entero y la compensación no llega.

**Cómo se llama:** *fallar abierto*, a propósito: ante la duda, la puerta queda abierta y el hecho,
registrado. Es el opuesto exacto de [fallar cerrado](A0-07-bases-de-datos-relacionales.md#clave-foránea-y-acción-referencial),
que el mismo sistema aplica a la base y a la seguridad. Las dos puertas fallan hacia lados opuestos
por la misma cuenta de costos: la del gimnasio falla abierta porque su error deja entrar a un socio;
la del sistema falla cerrada porque su error deja entrar a un desconocido.

### Nada muerto en pantalla

El principio tiene un par, y los dos dicen lo mismo desde lados distintos: **la pantalla no miente**.
Informar es no esconder lo que pasó; "nada muerto" es no prometer lo que no va a pasar.

#### La pregunta que decide

`CLAUDE.md` lo formula así: *"Nada muerto en pantalla. Un campo que no se guarda, un botón que no hace
nada o una opción ambigua (como los niveles de rutina) se saca. Si pregunta '¿por qué existe X?',
contestar con el porqué del negocio. Si no hay uno, X sobra."*

La pregunta aparece textual en `A CORREGIR PWA .txt`, y sus respuestas muestran que la regla corta para
los dos lados:

| Lo que el dueño preguntó | ¿Había un porqué del negocio? | Qué pasó |
|---|---|---|
| *"no entendería por qué hay catálogo de condiciones"* | sí: el catálogo dice qué condiciones existen, y la ficha, cuál tiene cada socio y qué hacer con ella | quedó, explicado ([catálogo contra observación](A-05-modelo-de-datos.md#catálogo-contra-observación)) |
| *"el método de pago billetera virtual por qué existe?"* | sí: se concilia en otro lugar que la transferencia | quedó, explicado ([método de pago](A-02-prepago-puro.md#método-de-pago)) |
| *"fichar con tarjeta no tiene sentido"* | no: el gimnasio no tiene lector | se sacó |

#### Tres formas de estar muerto

- **El campo que no se guarda.** El alta de socio dejaba elegir un plan y no lo mandaba a ningún lado:
  *"El socio quedaba sin membresía, y la pantalla daba a entender lo contrario"*
  (`Proyecto - PWA/src/frontend/src/views/socios/SocioFormModal.tsx:21-27`). Un campo muerto no es
  neutro: el recepcionista creía haber asignado un plan que no existía. Lo reemplazó "Cobrar ahora",
  porque el plan no es un dato del socio sino una `Membresia`, y una membresía se crea cobrándola.
- **El control que no hace nada.** La tarjeta "Fichar con tarjeta" era un campo que se mantenía
  enfocado esperando un lector RFID, y *"ocupaba media pantalla del mostrador sin hacer nada"*
  (`AsistenciaView.tsx:19-26`).
- **La opción ambigua.** El filtro de rutinas por nivel se guardaba y funcionaba, y estaba muerto
  igual: *"el 'intermedio' de uno es el 'avanzado' de otro"*
  (`Proyecto - PWA/src/frontend/src/config.ts:744-751`). Una opción que dos personas contestan
  distinto no filtra nada. Se reemplazó por días por semana, un número que significa lo mismo para
  todos; la columna `Rutina.nivel` sigue en la base porque *"borrarla sería un cambio de esquema por un
  dato de presentación"*. Cómo se retiraron juntos el componente de la PWA y su gemelo de Flet está en
  [el comentario que nombra al gemelo](A-03-dos-apps-un-backend.md#el-comentario-que-nombra-al-gemelo).

#### Muerto en pantalla no es muerto en el código

El caso del RFID muestra el alcance exacto de la regla. Se sacó el campo de la pantalla y **se dejó a
propósito** el camino del backend: `POST /asistencia/fichar` sigue aceptando `codigo_rfid`
(`backend/routers/asistencia.py:146-155`), `Socio.codigo_rfid` sigue en la base y `metodo_registro`
sigue admitiendo `RFID`. Las dos apps lo dejan escrito para que nadie lo limpie: *"parecen código muerto
y no lo son"* (`AsistenciaView.tsx:28-33`). El lector físico se compra al final
(`docs/ESTADO-ACTUAL.md`, "Fichaje con RFID"), y ese día sólo habrá que autenticar el aparato.

La diferencia es entre **muerto** y **dormido**. Lo que ve el operador tiene que funcionar hoy, porque
con la fila esperando no se ignora un control: se lo usa. Lo que está en el backend puede esperar una
pieza que tiene nombre y fecha. Los ingresos viejos cargados con lector, además, siguen en la base y la
lista los distingue con un ícono (`AsistenciaView.tsx:190-196`): se sacó la forma de crear nuevos, no
el dato.

La regla alcanza también a lo que el usuario no ve. La PWA le sacó a `getTurnosDisponibles()` el
parámetro de la sede *"en vez de dejarlo ignorado porque obligaba a las vistas a pedir la sede a la API
solo para pasar un número que se descartaba — un viaje de red entero para nada"*
(`actividadService.ts:578-586`). Un parámetro ignorado es un campo muerto en la API, y también cuesta.

#### Por qué está hecho así

**Qué se optimiza:** que todo lo que se ve en pantalla sea confiable, para que quien tiene apuro pueda
actuar sobre lo que ve sin verificarlo.

**Qué alternativa se descartó:** dejar los controles "para más adelante", deshabilitados o
funcionando a medias. Cada "más adelante" es una mentira hoy.

**Qué se paga:** una función planificada, como el lector, no se ve hasta que existe de verdad. Y sacar
algo cuesta el doble, porque hay que sacarlo en las dos apps.

**Cómo se llama:** es *YAGNI* —*you aren't gonna need it*, la regla de la programación extrema de fines
de los noventa: no construir lo que todavía no hace falta—, con una precisión que la regla original no
tiene: acá se aplica a la pantalla y no al backend, donde una pieza con fecha puede esperar.

---

## Con qué se conecta

- **Existe por culpa de…** el mostrador con cola: "Cobrar ahora" en el alta
  ([B-02](B-02-socios.md)): menos pasos porque hay gente esperando.
- **Es la misma idea que…** el [listado en lote](A-11-rendimiento.md#listado-en-lote): Recepción le
  ahorra búsquedas al operador y viajes a la red, la misma cuenta a dos escalas.
- **Se contradice con…** la [respuesta indistinguible](A-07-autenticacion.md#freno-de-intentos-y-respuesta-indistinguible):
  en el login el sistema no informa, porque informar le serviría al atacante.
- **Se contradice con…** [sin cobros por adelantado](A-02-prepago-puro.md#sin-cobros-por-adelantado):
  deja entrar al vencido y rechaza al que quiere pagar de más; en cada caso decide quien tiene la información.
- **Es la misma idea que…** [omitir en vez de deshabilitar](A-08-autorizacion.md#omitir-en-vez-de-deshabilitar):
  la pantalla no muestra lo que no se puede usar, por falta de función en un caso y de permiso en el otro.
- **Existe por culpa de…** [no existe "Registrarse"](A-07-autenticacion.md#no-existe-registrarse): el
  alta es la única operación que no puede salir del mostrador, y por eso es la que más atajos tiene.
