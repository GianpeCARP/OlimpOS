# B-09 · Rutinas

*Procesos 88 a 97. Piso del capítulo: la línea que implementa cada paso, en las tres capas.*

Diez procesos sobre un router de 588 líneas, el más chico de los módulos grandes. Y el único cuyo
encabezado arranca justificando su propia forma: *"TRES NIVELES, Y POR QUÉ NO SON UNO SOLO"*
(`backend/routers/rutinas.py:6-22`). Ésa es la decisión que explica el capítulo entero, así que va
primero.

Los números salen de `PROCESOS-LOGICOS-REQUERIDOS.md`, que los ordenó por ruta. Acá están agrupados
por lo que hacen:

| Tema | Procesos |
|---|---|
| El catálogo de ejercicios | 91, 92 |
| El catálogo de rutinas: leer y escribir | 88, 93, 89, 94 |
| Asignarle una rutina a un socio | 95, 90 |
| Sacar una rutina de circulación | 96, 97 |

Lo que hay que traer de la Parte A: qué es una
[asignación con estado](A-05-modelo-de-datos.md#asignación-con-estado) y cómo un
[índice único parcial](A0-08-sql-indices-y-planes.md#índice-único-parcial) garantiza una sola activa
por socio; por qué lo que se armó solo responde 404 y no 403
([aislamiento de lo propio](A-08-autorizacion.md#aislamiento-de-lo-propio)); qué diferencia hay entre
[`flush` y `commit`](A0-09-el-orm.md#flush-contra-commit) y qué es un [N+1](A0-09-el-orm.md#n1).

**Lo que se corrió, y cómo.** De este capítulo se corrió bastante, y dos corridas cambiaron lo que el
capítulo iba a decir. Van contra **SQLite en memoria** con los modelos y las funciones **reales** del
router, por una razón de la máquina —acá no hay un PostgreSQL local, que es la técnica que usaron B-03
y B-04— y por una razón del contenido: lo que se mide es el **orden de las sentencias que emite
SQLAlchemy**, el **número de consultas** y el comportamiento de un **índice único parcial**, y ninguna
de las tres depende del motor. Donde el motor sí importa —cuánto cuesta cada consulta— el número es de
Neon y se dice que no sale de la medición. Los cuatro guiones son `b09_flush.py`, `b09_consultas.py`,
`b09_menores.py` y `b09_expire.py`, en el scratchpad de la sesión.

---

## Piezas comunes

### Tres niveles, y por qué no son uno solo

El encabezado del router los nombra (`backend/routers/rutinas.py:8-10`):

| Nivel | Qué es | Ejemplo |
|---|---|---|
| `Ejercicio` | existe UNA vez en todo el sistema | *Press de banca* |
| `Rutina` | la plantilla que arma un entrenador | *Fuerza Total, 3 días* |
| `Asignacion_Rutina` | qué socio sigue qué rutina, desde cuándo | *Franco la sigue desde el 3/9* |

La tentación es la de siempre: guardar los ejercicios adentro de cada rutina y la rutina adentro de
cada socio. El docstring descarta las dos con un argumento cada una (`:12-22`).

Los **ejercicios embebidos**: *"'Sentadilla' quedaría escrito distinto en cada rutina ('sentadilla',
'Sentadillas', 'Sentadilla libre') y no habría forma de responder «¿qué rutinas usan este
ejercicio?»"*. Es tercera forma normal aplicada a un catálogo, y el comentario de la base lo dice con
otras palabras: *"grupo_muscular depende del EJERCICIO, no de la rutina en que aparece"*
(`db/schema.sql:754-758`).

Las **rutinas embebidas en el socio**: *"asignar la misma rutina a quince personas la duplicaría
quince veces, y corregir una serie obligaría a editarlas todas"*. El esquema remata la idea desde el
otro lado: `Rutina_Ejercicio` **no puede** tener una columna `peso_hecho`, *"porque esta fila es de la
PLANTILLA y la comparten todos los socios que siguen esa rutina, así que un peso acá no tendría
dueño"* (`db/schema.sql:797-801`). Lo que el socio levantó de verdad vive en `Registro_Ejercicio`, con
grano `(socio, ejercicio, fecha)`.

El par **plantilla / realidad** es, entonces, dos tablas a propósito: `Rutina_Ejercicio` dice qué
debería hacer y `Registro_Ejercicio` qué hizo (`db/schema.sql:833-836`). Y la clave foránea del
registro apunta a `Ejercicio`, **no** a `Rutina_Ejercicio` (`db/schema.sql:1086`) — un detalle que
parece menor y es el que habilita el proceso 94, como se ve más abajo.

### La rutina propia del socio es invisible para el personal, y responde 404

`Rutina.id_entrenador` es **nullable**, y un NULL no significa "sin entrenador asignado": significa
**rutina propia de un socio**, la que se armó él mismo desde el portal (`db/schema.sql:775-780`). El
dueño de esa rutina no se guarda —no hay `id_socio` en `Rutina`— se **deriva** de su
`Asignacion_Rutina`, porque una rutina propia se le asigna exactamente a su autor y a nadie más.

Del lado del personal, esa fila no existe. Lo hace valer una sola función de nueve líneas,
`_rutina_del_staff()` (`rutinas.py:218-232`), y la decisión está en el `or`:

```python
if rutina is None or rutina.id_entrenador is None:
    raise HTTPException(status_code=404, detail="La rutina no existe.")
```

El docstring explica por qué el mismo 404 y no un 403 (`:222-227`): *"Un 403 —o cualquier mensaje
distinto— confirmaría que el id existe y es de alguien, que es justo lo que no tiene que poder saberse
desde acá."* Es [aislamiento de lo propio](A-08-autorizacion.md#aislamiento-de-lo-propio) aplicado al
revés de lo habitual: acá lo que se protege no es lo del personal frente al socio, sino **lo del socio
frente al personal**.

Esa función es la puerta de **cinco** de los diez procesos —93, 94, 95, 96 y 97— y el filtro
equivalente está escrito a mano en los dos que listan: `listar_rutinas()` (`:302`) y
`rutinas_de_socio()` (`:500`) agregan `Rutina.id_entrenador.isnot(None)` al `WHERE`. Siete de diez
procesos repiten la misma condición de dos formas distintas, y `_a_rutina_out()` la vuelve a preguntar
para decidir el texto (`:202-207`): si es propia, el campo `entrenador` dice *"Rutina propia"* en vez
de *"Sin asignar"*.

### Qué es "mía": tres funciones y un campo en la respuesta

Un Entrenador toca **sólo sus** rutinas; el Dueño y el Recepcionista, todas. Eso se resuelve en tres
pasos cortos:

| Función | Líneas | Qué hace |
|---|---|---|
| `_entrenador_de_sesion()` | `rutinas.py:68-84` | la ficha de Entrenador de quien está logueado, o `None` |
| `_puede_editar()` | `:87-95` | `propio is None or rutina.id_entrenador == propio.id_entrenador` |
| `_exigir_editable()` | `:98-103` | lo anterior, o 403 |

El `None` de la primera **no es un error**: *"El Dueño y el Recepcionista pueden crear rutinas sin ser
entrenadores, así que esto puede devolver None legítimamente"* (`:72-73`). Y entonces el `propio is
None` de la segunda se lee *"quien no es entrenador no tiene rutinas propias que defender: puede con
todas"*.

El detalle que no se ve leyendo rápido está en el `return` de la primera (`:84`):

```python
return empleado.entrenador if empleado and rol_activo(empleado.entrenador) else None
```

`rol_activo()` y no `is not None`, y el comentario de arriba dice por qué (`:80-83`): *"la fila de un
rol apagado sigue existiendo para sostener su historial. Sin el flag, alguien que pasó de entrenador a
recepcionista seguía siendo «entrenador de la sesión» y editaba rutinas."* Es la consecuencia directa
de [el rol que se apaga](A-10-bajas-logicas.md#el-rol-que-se-apaga): cada lugar que antes preguntaba
"¿tiene fila?" ahora tiene que preguntar "¿está prendida?", y éste es uno de ellos.

Lo que el backend decide, las pantallas lo **reciben**: `RutinaOut.puede_editar`
(`backend/schemas.py:1494-1496`) viaja por rutina, y las dos apps lo combinan con el permiso de
sección —`gestionable()` en la PWA
(`Proyecto - PWA/src/frontend/src/views/rutinas/RutinasView.tsx:114-117`) y `_gestionable()` en Flet
(`Flet/Proyecto/app/views/rutinas.py:72-73`)— para decidir **qué botones dibujar**. Los dos
comentarios aclaran que eso no es el control: *"Lo decide el backend (`puede_editar`) y es el que de
verdad lo impide; acá sólo se decide qué botones se dibujan"*
(`Flet/Proyecto/app/views/rutinas.py:15-16`). Es
[el frontend esconde, el backend rechaza](A-08-autorizacion.md#el-frontend-esconde-el-backend-rechaza)
con un agregado: el permiso **por fila** no se puede derivar de la matriz, así que tiene que venir en
el dato.

**Nota marcada · "Sólo el Entrenador gestiona rutinas".** Lo dice el comentario que precede al hook de
permisos de la PWA (`RutinasView.tsx:54-56`), y no es así: `gestionRutinas` la tienen el **Dueño**, el
**Recepcionista** y el Entrenador (`backend/permisos.py:185`, `:220`, `:250`). La segunda mitad de la
frase sí es correcta —el Nutricionista llega a la pantalla con lectura y sin ningún botón—. Es el mismo
tipo de cartel desactualizado que B-04 encontró en Usuarios.

### El autor sale de la sesión, no del cuerpo del pedido

`_resolver_entrenador()` (`rutinas.py:134-174`) decide a nombre de quién queda una rutina, y tiene dos
ramas que no son simétricas:

- **Quien pide ES entrenador** → la rutina es suya. Mandar el id de otro da **403**: *"sería crear
  rutinas a nombre ajeno, y el historial de quién armó qué dejaría de significar algo"* (`:140-142`).
- **Quien pide NO es entrenador** (Dueño, Recepcionista) → tiene que elegir uno, o **400**. *"Para
  ellos elegir no es suplantar: es delegar, y tienen el permiso"* (`:147`).

La asimetría es el punto. El mismo campo del mismo pedido está **prohibido** para un rol y es
**obligatorio** para otro, y la regla no sale de la matriz de permisos: sale de si la sesión tiene
ficha de entrenador. La matriz dice quién puede gestionar rutinas; esto dice a nombre de quién quedan.

El backend no se queda solo con eso: `GET /personal/entrenadores` **recorta la lista al propio** si
quien pregunta es entrenador (`backend/routers/personal.py:516-520`), así que el selector de las dos
apps no ofrece algo que después va a fallar. *"Filtrarlo acá hace que los selectores de las dos apps
dejen de ofrecer algo que después falla, sin tocar ninguna pantalla"* (`personal.py:513-514`).

**Nota marcada · el porqué escrito cinco veces, y en los cinco está mal.** La rama del Dueño se
justifica así: *"`Rutina.id_entrenador` es NOT NULL y ellos no tienen ficha de entrenador, así que sin
elegir no hay a quién atribuirla"* (`rutinas.py:145-146`). **La columna no es NOT NULL.** Es nullable,
y lo es a propósito desde que existen las rutinas propias del socio: `db/schema.sql:763` la declara
`integer` sin más, y `backend/models.py:592` escribe `nullable=True` explícito. La misma frase está en
cinco lugares:

| Dónde | Líneas |
|---|---|
| `backend/routers/rutinas.py` | 145-146 |
| `backend/schemas.py` | 1430-1433 (docstring de `RutinaCrear`) |
| `Proyecto - PWA/src/frontend/src/views/rutinas/RutinaFormModal.tsx` | 26-28 |
| `Flet/Proyecto/app/views/rutinas.py` | 230-232 |
| `Flet/Proyecto/app/state.py` | 1290-1294 |

Lo interesante es que **la regla sigue siendo correcta y el motivo que la sostiene ya no**. Pedirle un
entrenador al Dueño hace falta igual, pero por atribución y no por la base: una rutina del catálogo sin
entrenador sería indistinguible de una rutina propia de un socio y, por lo tanto, **invisible para el
personal que la acaba de crear**. El NULL dejó de ser imposible y pasó a significar otra cosa; el
comentario quedó contando la versión anterior del esquema. No se tocó: queda anotado.

### Lo que cuesta leer una rutina, medido

Ninguna de las tres consultas de lectura del router pide carga anticipada, y los dos conversores
recorren relaciones: `_nombre_entrenador()` camina `Entrenador → Empleado → Persona`
(`rutinas.py:56-65`) y `_a_rutina_out()` cuenta `rutina.asignaciones` (`:213`) y lee `re.ejercicio` por
cada fila de la planilla (`:187-196`). **Corrido** con 6 rutinas, 5 ejercicios cada una y 4
asignaciones cada una, en dos escenarios —un entrenador para todas, y uno por rutina—:

| Proceso | Consultas | De dónde salen |
|---|---|---|
| 88 `listar_rutinas` | **11 a 26** | 2 fijas + **1 por rutina** (`Asignacion_Rutina`) + **3 por entrenador distinto** (`Entrenador`, `Empleado`, `Persona`) |
| 93 `obtener_rutina` | **12** | 7 fijas + **1 por ejercicio** de la planilla |
| 90 `rutinas_de_socio` | **9** | 3 fijas + **1 por asignación**, y es de `Rutina`, que la consulta ya trajo |

La horquilla del catálogo tiene una explicación que vale aprender: la fórmula es **2 + N + 3·E**, con
`N` rutinas y `E` **entrenadores distintos** entre ellas. Las 6 rutinas de la prueba cuestan **11**
consultas si son todas del mismo entrenador y **26** si cada una tiene el suyo, y la diferencia no la
hace el código sino [el mapa de identidad](A0-09-el-orm.md#sesión-y-mapa-de-identidad): la segunda
rutina del mismo entrenador encuentra su `Entrenador`, su `Empleado` y su `Persona` ya cargados en la
sesión y no vuelve a preguntar. O sea que **el costo de este listado depende de los datos**, que es
justo lo que un `selectinload` deja de hacer. Sobre
[la base remota](A-11-rendimiento.md#base-remota), a 44 ms cada una y en serie, el peor caso es más de
un segundo para dibujar seis tarjetas. Es exactamente el [N+1](A0-09-el-orm.md#n1) que
[el listado en lote](A-11-rendimiento.md#listado-en-lote) ya cerró en Socios y en Usuarios con
`selectinload`, y que [B-06](B-06-asistencia.md#con-qué-se-conecta) encontró abierto en el feed de
ingresos. Acá está abierto en los tres listados del módulo — y en los tres de Nutrición, que son los
mismos ([B-10](B-10-nutricion.md#lo-que-cuesta-leer-un-plan-medido)).

El caso del proceso 90 es el más llamativo y vale como lección aparte: la consulta **hace un `JOIN` con
`Rutina`** (`rutinas.py:498`) y, aun así, `a.rutina.nombre` (`:510`) dispara una consulta por fila. El
`JOIN` está ahí para el `WHERE`, no para llenar la relación — para eso hay que decírselo al ORM con
`contains_eager()` o `joinedload()`. Seis consultas que piden datos que ya venían en la respuesta de la
primera.

### El video del ejercicio no está en ninguna columna

`RutinaEjercicioOut.video_local` y `EjercicioOut.video_local` no son columnas: las calcula
`video_local()` (`backend/videos.py:66-76`) preguntándole al **disco** si el archivo existe. Es el
[almacén que no es tabla](A-05-modelo-de-datos.md#almacén-que-no-es-tabla) en su forma más pura, y la
consecuencia de producto está escrita al lado: *"None mientras el demonio no lo bajó: el socio ve el
ejercicio igual, sólo que sin el botón de «Ver técnica»"*. El demonio que los baja es
[C-08](C-08-demonio-videos.md). Lo que importa acá es que **cada ejercicio de cada planilla cuesta un
`is_file()`**: disco local, no red, así que no entra en la cuenta de arriba.

---

## El catálogo de ejercicios

### 91. Consultar el catálogo de ejercicios

`GET /rutinas/ejercicios` · Dueño, Recepcionista, Entrenador, Nutricionista

**Qué resuelve.** Los ejercicios que el gimnasio tiene cargados, para elegirlos al armar una rutina o
para mirar la técnica.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Endpoint | `backend/routers/rutinas.py` | 241-246 | `listar_ejercicios()` |
| Esquema | `backend/schemas.py` | 1356-1372 | `EjercicioOut` |
| Video derivado | `backend/videos.py` | 66-76 | `video_local()` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/rutinasService.ts` | 165-168 | `listarEjercicios()` |
| Vista PWA (mirar) | `Proyecto - PWA/src/frontend/src/views/rutinas/RutinasView.tsx` | 263-265 | `CatalogoEjercicios` con la prop `cargar` |
| Vista PWA (elegir) | `Proyecto - PWA/src/frontend/src/views/rutinas/EditorEjercicios.tsx` | 253-353 | `PickerCatalogo` |
| Agrupado PWA | `Proyecto - PWA/src/frontend/src/views/rutinas/planillaEjercicios.ts` | 106-124 | `agruparCatalogo()` |
| Vista Flet | `Flet/Proyecto/app/views/rutinas.py` | 315-339 | `render_catalogo()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1343-1351 | `get_ejercicios()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 542-543 | `obtener_ejercicios()` |

**Cómo funciona.** Una consulta, ordenada por grupo muscular y después por nombre
(`backend/routers/rutinas.py:246`). El orden no es decorativo: es el que agrupa la lista en pantalla, y
las dos apps la agrupan por `grupo_muscular` sin volver a ordenar nada — `agruparCatalogo()` construye
un `Map` en el orden en que llegan las filas
(`Proyecto - PWA/src/frontend/src/views/rutinas/planillaEjercicios.ts:117-123`).

El `video_local` lo agrega un `model_validator(mode="after")` del propio esquema
(`backend/schemas.py:1369-1372`), así que ningún endpoint tiene que acordarse de calcularlo.

**Qué escribe y qué lee.** Lee `Ejercicio` (`backend/routers/rutinas.py:246`). No escribe nada.
Coincide con la línea DFD, con la salvedad que el propio archivo de procesos declara: el archivo del
video no es una tabla y no entra en la notación.

**Por qué está hecho así.** El endpoint pide la **sección** y no la acción, así que el Nutricionista lo
puede llamar. Tiene sentido para el módulo entero —*"necesita ver la rutina de un socio para no armarle
una dieta que la contradiga, pero no tocarla"* (`backend/routers/rutinas.py:26-28`)— y de paso resuelve
el caso raro: el catálogo de ejercicios también lo abre el **socio** desde su portal, con otro endpoint.
La PWA reusa el mismo componente para los dos y le pasa **de dónde cargar**, porque el del portal exige
"Mi rutina" y *"le contestaba 403 al Dueño"*
(`Proyecto - PWA/src/frontend/src/views/rutinas/RutinasView.tsx:260-262`).

**Qué pasa cuando sale mal.** Sólo 403, para el Profesor y el Socio, que tienen la sección en NINGUNO.

---

### 92. Dar de alta un ejercicio en el catálogo

`POST /rutinas/ejercicios` · Dueño, Recepcionista, Entrenador

**Qué resuelve.** Sumar un ejercicio al catálogo compartido, con el link del video de técnica.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Endpoint | `backend/routers/rutinas.py` | 249-280 | `crear_ejercicio()` |
| Esquema | `backend/schemas.py` | 1375-1391 | `EjercicioCrear`, `_link_de_youtube()` |
| Validación del link | `backend/videos.py` | 52-57 | `id_youtube()` |
| Base | `db/schema.sql` | 745-758 | `Ejercicio`, con `nombre UNIQUE` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/rutinasService.ts` | 182-194 | `crearEjercicio()` |
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/rutinas/EjercicioFormModal.tsx` | 19-111 | `EjercicioFormModal` |
| Vista Flet | `Flet/Proyecto/app/views/rutinas.py` | 588-654 | `_open_form_ejercicio()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1340-1341 | `crear_ejercicio()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 546-547 | `crear_ejercicio()` |

**Cómo funciona.** Dos validaciones y un `INSERT`.

La primera corre **en el esquema**, antes de llegar al endpoint: si hay `url_video` y no es un link de
YouTube, 422. El comentario dice por qué ahí y no en el demonio (`backend/schemas.py:1385-1387`): *"si
el link no es de YouTube el entrenador tiene que enterarse al guardar, no descubrir días después que el
video nunca apareció."* Lo que decide si un link vale es `id_youtube()`, la misma función con la que el
demonio arma después el nombre del archivo: una sola definición.

La segunda es el nombre duplicado (`backend/routers/rutinas.py:264-268`). `Ejercicio.nombre` es
`UNIQUE` en el esquema (`db/schema.sql:747`) y el chequeo a mano existe *"para dar un mensaje claro en
vez del error de restricción de PostgreSQL"*. Y el docstring defiende la restricción misma: *"dos filas
'Sentadilla' partirían en dos el historial de ese ejercicio"* — que es, otra vez, el argumento de los
tres niveles.

**Qué escribe y qué lee.** Escribe `Ejercicio` con sus cinco campos
(`backend/routers/rutinas.py:270-277`); lee `Ejercicio` para el duplicado (`:264`). Coincide con la
línea DFD, que declara las dos cosas.

**Por qué está hecho así.** El entrenador pega un link y nada más. Nadie del personal sube un archivo
ni toca un FTP: el [demonio de videos](C-08-demonio-videos.md) lo baja solo y el socio ve "Ver técnica"
cuando esté. Lo que se paga es la espera, y las dos pantallas la dicen en vez de esconderla:
*"Ejercicio creado. El video va a estar disponible en unos minutos"*
(`Proyecto - PWA/src/frontend/src/views/rutinas/EjercicioFormModal.tsx:36-39` y
`Flet/Proyecto/app/views/rutinas.py:626-628`). Es
[el sistema informa, no juzga](A-01-que-es-olimpos.md#el-sistema-informa-no-juzga) aplicado a una
latencia.

En la PWA, el botón para **ver** el catálogo va **antes** que el de agregar, y ese orden es el arreglo
de un problema real (`Proyecto - PWA/src/frontend/src/views/rutinas/RutinasView.tsx:162-165`): *"el
problema era cargar por segunda vez un ejercicio que ya estaba, porque la única puerta era el alta."*

**Nota marcada · el guion bajo del `ilike` es un comodín.** La comparación del duplicado usa
`Ejercicio.nombre.ilike(nombre)` (`backend/routers/rutinas.py:264`), y en `LIKE` el `_` significa "un
carácter cualquiera". **Corrido:** con un `PressXbanca` ya cargado, crear `Press_banca` responde 409
*"Ya existe un ejercicio llamado 'Press_banca'"*. Es el mismo defecto que B-05 corrió en el nombre de
un plan de membresía y que [B-08](B-08-actividades-turnos-horarios.md#con-qué-se-conecta) encontró en
el nombre de una actividad: tres copias del mismo chequeo, con el mismo agujero.

**Nota marcada · Flet no tiene el botón de ver el catálogo.** La barra de Flet ofrece *"Nuevo
Ejercicio"* y *"Nueva Rutina"* (`Flet/Proyecto/app/views/rutinas.py:41-48`), y nada más: el catálogo se
ve sólo **adentro** del formulario de rutina, al elegir ejercicios. O sea que el arreglo de la PWA
—mirar antes de cargar— no está replicado, y la PWA es la referencia.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| El link no es de YouTube | 422 | *"El video tiene que ser un link de YouTube."* | `backend/schemas.py:1389-1390` |
| Nombre vacío o de más de 100 | 422 | el de Pydantic, en inglés | `backend/schemas.py:1376` |
| Ya existe ese nombre | 409 | *"Ya existe un ejercicio llamado 'X'."* | `backend/routers/rutinas.py:265-268` |
| Sin la acción `gestionRutinas` | 403 | el genérico de la acción | `backend/security.py:197-215` · `requiere_accion()` |

---

## El catálogo de rutinas

### 88. Consultar el catálogo de rutinas

`GET /rutinas` · Dueño, Recepcionista, Entrenador, Nutricionista

**Qué resuelve.** Las rutinas que el gimnasio tiene armadas, con cuántos socios sigue cada una y si
quien mira puede tocarla.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Endpoint | `backend/routers/rutinas.py` | 287-312 | `listar_rutinas()` |
| Armado | `backend/routers/rutinas.py` | 177-215 | `_a_rutina_out()` |
| Permiso por fila | `backend/routers/rutinas.py` | 68-95 | `_entrenador_de_sesion()`, `_puede_editar()` |
| Esquema | `backend/schemas.py` | 1478-1496 | `RutinaOut` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/rutinasService.ts` | 92-112 | `aRutinaListado()`, `listarRutinas()` |
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/rutinas/RutinasView.tsx` | 50-304 | `RutinasView` |
| Tarjeta PWA | `Proyecto - PWA/src/frontend/src/views/rutinas/RutinaCard.tsx` | 23-113 | `RutinaCard` |
| Vista Flet | `Flet/Proyecto/app/views/rutinas.py` | 38-143 | `build()`, `_rutina_card()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 526-552 | `get_rutinas()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 534-535 | `obtener_rutinas()` |

**Cómo funciona.** Una consulta con un filtro y un `ORDER BY`, y después un bucle
(`backend/routers/rutinas.py:300-312`):

1. **Las rutinas que NO son propias de un socio**, las más nuevas primero (`:300-305`).
2. **La ficha de entrenador de quien pregunta**, una sola vez para toda la lista (`:306`).
3. **Por rutina**, `_a_rutina_out(r, con_ejercicios=False)` y `out.puede_editar = _puede_editar(...)`
   (`:308-311`).

El `con_ejercicios=False` es la decisión de tamaño: *"la grilla muestra tarjetas"* (`:293`), y la
planilla completa de cada rutina sería traer datos que nadie mira. El detalle se pide aparte, en el
proceso 93, cuando se abre una.

`asignados` sí viaja: es `sum(1 for a in rutina.asignaciones if a.estado == "ACTIVA")` (`:213`), y el
esquema explica por qué lo cuenta el backend (`backend/schemas.py:1489-1491`): *"hacerlo en el cliente
obligaría a bajarse todas las asignaciones para mostrar un número."* Las dos apps lo usan igual, para
una barra de ocupación sobre un máximo de 20 que **no es una regla de negocio**: *"el backend no impide
asignar más. Por eso vive acá y no en el servidor — si mañana se decide que una rutina tiene cupo real,
ahí sí pasa a ser del backend"*
(`Proyecto - PWA/src/frontend/src/services/rutinasService.ts:19-23`). Flet lo tiene clavado en la
tarjeta, con el mismo número y la misma aclaración (`Flet/Proyecto/app/views/rutinas.py:92-94`).

**Qué escribe y qué lee.** Lee `Rutina` (`:317-322`), `Asignacion_Rutina` (`:230`), y
`Entrenador → Empleado → Persona` para el nombre (`:62-65`). No escribe nada. Coincide con la línea
DFD.

**Por qué está hecho así.** Lo que decide la forma de este endpoint es el **filtro**, no el formato. El
docstring lo argumenta en una frase que vale para todo el módulo (`:312-315`): *"el catálogo es lo que
un entrenador elige para asignar, y una rutina propia no se le asigna a nadie más que a su autor. Que
apareciera acá sería, literalmente, ofrecerla para asignar a terceros."* La rutina propia no se oculta
por pudor: se oculta porque **la lista es una lista de candidatas a asignar**, y ésa no es candidata.

Lo que se paga está medido más arriba: 2 + 4·N consultas. Sobre una base en São Paulo, el precio de no
haber escrito `selectinload`.

**Nota marcada · la PWA filtra y Flet no.** La PWA tiene buscador por nombre u objetivo y chips por
**días por semana** (`RutinasView.tsx:39-44`, `:211-231`), y el comentario explica el reemplazo: antes
los chips filtraban por nivel, y se retiró porque *"«intermedio» no significa lo mismo para dos
entrenadores, así que el filtro no ayudaba a encontrar nada. «3 días» sí"* (`:33-37`). Flet no tiene ni
buscador ni chips: dibuja todas las tarjetas (`Flet/Proyecto/app/views/rutinas.py:53-57`). Con un
catálogo chico da igual; con cien rutinas, no.

**Nota marcada · `duracion`, una clave que nadie lee.** `get_rutinas()` de Flet arma un campo
`duracion` a partir del objetivo (`Flet/Proyecto/app/state.py:541`) y ninguna vista lo usa: la tarjeta
muestra `dias` y `objetivo` (`Flet/Proyecto/app/views/rutinas.py:121-126`). Es el resto de una versión
anterior de la tarjeta; el comentario que lo acompaña sigue explicando una decisión que ya no se toma
(`state.py:530-533`).

**Qué pasa cuando sale mal.** Sólo 403, para el Profesor y el Socio.

---

### 93. Consultar el detalle de una rutina

`GET /rutinas/{id_rutina}` · Dueño, Recepcionista, Entrenador, Nutricionista

**Qué resuelve.** La planilla completa de una rutina: qué ejercicios, en qué día, con cuántas series y
repeticiones.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Endpoint | `backend/routers/rutinas.py` | 315-325 | `obtener_rutina()` |
| Puerta de la rutina propia | `backend/routers/rutinas.py` | 218-232 | `_rutina_del_staff()` |
| Armado y orden | `backend/routers/rutinas.py` | 177-215 | `_a_rutina_out()` |
| Esquema | `backend/schemas.py` | 1406-1419 | `RutinaEjercicioOut` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/rutinasService.ts` | 119-140 | `obtenerRutina()` |
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/rutinas/RutinaDetailModal.tsx` | 38-179 | `RutinaDetailModal` |
| Resumen de una fila | `Proyecto - PWA/src/frontend/src/views/rutinas/RutinaDetailModal.tsx` | 28-36 | `resumen()` |
| Vista Flet | `Flet/Proyecto/app/views/rutinas.py` | 147-214 | `_open_detail()` |
| Resumen Flet | `Flet/Proyecto/app/views/rutinas.py` | 705-717 | `_resumen()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 554-585 | `get_rutina()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 538-539 | `obtener_rutina()` |

**Cómo funciona.** Tres líneas de endpoint (`backend/routers/rutinas.py:322-325`): la rutina por
`_rutina_del_staff()`, el armado con ejercicios, y `puede_editar`. Todo lo interesante está en el
armado.

El orden de la planilla lo decide el backend, por `(dia, orden)` (`:183`), y el comentario dice por qué
no se deja al cliente: *"es como se lee la planilla en el gimnasio, y dejarlo al orden de inserción
daría una lista arbitraria que el frontend tendría que reordenar."* Las dos apps confían en eso: la PWA
agrupa por día recorriendo la lista tal como llega, y Flet lo mismo
(`Flet/Proyecto/app/views/rutinas.py:168-179`).

`repeticiones` es **texto** y no un número, y es una de las decisiones de dominio más claras del repo:
*"en el gimnasio se escribe «8-12» o «al fallo»"* (`backend/schemas.py:1399-1400`, y el mismo argumento
en `backend/models.py:610-612`). Un `int` habría obligado a inventar dos columnas y a perder "al
fallo". El precio es que no se puede sumar ni promediar, y nada en el sistema lo necesita.

`peso_sugerido` sale como `float` y las dos apps lo vuelven a texto para mostrarlo, con la misma
corrección: Flet tiene `_texto()`, que convierte `60.0` en `"60"`
(`Flet/Proyecto/app/views/rutinas.py:661-667`), y la PWA hace lo propio en `nuevoItem()`
(`Proyecto - PWA/src/frontend/src/views/rutinas/planillaEjercicios.ts:55-59`). Son dos
implementaciones del mismo detalle de presentación, que es lo que pasa cuando hay
[dos apps gemelas](A-03-dos-apps-un-backend.md#aplicación-gemela-y-componente-gemelo).

**Qué escribe y qué lee.** Lee `Rutina` (`backend/routers/rutinas.py:229`), `Rutina_Ejercicio` y
`Ejercicio` (`:183-196`), `Asignacion_Rutina` (`:213`) y la cadena del entrenador (`:62-65`). No
escribe. Coincide con la línea DFD.

**Por qué está hecho así.** La división listado / detalle no es estética: el listado baja 6 rutinas sin
planilla y el detalle baja una con todo. Es lo mismo que hace Socios con la grilla y la ficha, por el
mismo motivo —[la base remota](A-11-rendimiento.md#base-remota)— y acá con un agregado: el formulario
de edición **también** pide el detalle al abrir, porque el listado no lo trae
(`Proyecto - PWA/src/frontend/src/views/rutinas/RutinaFormModal.tsx:47-48`, `:101-116`). Un pedido más
por abrir el modal, a cambio de un listado liviano.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| No existe ese id | 404 | *"La rutina no existe."* | `backend/routers/rutinas.py:230-231` |
| Es la rutina propia de un socio | 404 | el **mismo** mensaje, a propósito | `backend/routers/rutinas.py:230-231` |
| Sin la sección Rutinas | 403 | el genérico de la sección | `backend/security.py:162-169` |

---

### 89. Crear una rutina del catálogo con sus ejercicios

`POST /rutinas` · Dueño, Recepcionista, Entrenador

**Qué resuelve.** Que un entrenador arme una plantilla nueva con su planilla completa, en un solo
guardado.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Endpoint | `backend/routers/rutinas.py` | 328-363 | `crear_rutina()` |
| A nombre de quién | `backend/routers/rutinas.py` | 134-174 | `_resolver_entrenador()` |
| Ejercicios | `backend/routers/rutinas.py` | 106-131 | `_validar_ejercicios()`, `_agregar_ejercicios()` |
| Esquemas | `backend/schemas.py` | 1394-1403, 1422-1447 | `RutinaEjercicioCrear`, `RutinaCrear` |
| Base | `db/schema.sql` | 761-801, 1157 | `Rutina`, `Rutina_Ejercicio` y su índice único |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/rutinasService.ts` | 247-272 | `aEjercicioApi()`, `crearRutina()` |
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/rutinas/RutinaFormModal.tsx` | 37-248 | `RutinaFormModal` |
| Editor de la planilla | `Proyecto - PWA/src/frontend/src/views/rutinas/EditorEjercicios.tsx` | 35-215 | `EditorEjercicios` |
| Armado de la planilla | `Proyecto - PWA/src/frontend/src/views/rutinas/planillaEjercicios.ts` | 63-103 | `aNumero()`, `armarEjercicios()` |
| Selector de entrenador | `backend/routers/personal.py` | 501-520 | `listar_entrenadores()` |
| Vista Flet | `Flet/Proyecto/app/views/rutinas.py` | 238-517 | `_open_form()` |
| Armado Flet | `Flet/Proyecto/app/views/rutinas.py` | 670-702 | `_numero()`, `_armar_ejercicios()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1316-1317 | `crear_rutina()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 550-551 | `crear_rutina()` |

**Cómo funciona.** Cuatro pasos y un solo `commit`
(`backend/routers/rutinas.py:346-363`):

1. **A nombre de quién** — `_resolver_entrenador()`, con las dos ramas asimétricas de arriba.
2. **La rutina** — `db.add(rutina)` y `db.flush()` (`:355-356`). Acá el `flush` **sí** hace falta y por
   el motivo clásico: hace falta el `id_rutina` que genera la base para colgarle los ejercicios, y
   `flush` lo trae sin confirmar nada ([`flush` contra `commit`](A0-09-el-orm.md#flush-contra-commit)).
3. **Todos los ejercicios existen** — `_validar_ejercicios()` (`:358`), y el orden importa: *"ANTES de
   insertar ninguno: si el tercero no existe, no tiene que quedar una rutina con los dos primeros
   cargados"* (`:108-109`).
4. **Los ejercicios** y el `commit` (`:359-361`).

El paso 3 merece una vuelta más, porque el argumento del docstring es **más débil que la realidad**: la
transacción ya garantizaría que no quede nada a medias, aunque el `INSERT` del tercero falle con la
clave foránea. Lo que de verdad compra validar antes es el **mensaje**: `"El ejercicio con id 5 no
existe."` con un 404 (`:113-116`) en lugar de un `IntegrityError` y un 500 sin explicación. Es la misma
jugada que el chequeo del nombre duplicado del proceso 92: la restricción de la base es el piso, el
chequeo a mano es el mensaje.

El `orden` de cada fila **lo calcula el cliente**, no el servidor: `armarEjercicios()` numera de 1 en
adelante dentro de cada día, aprovechando que `sort` es estable
(`Proyecto - PWA/src/frontend/src/views/rutinas/planillaEjercicios.ts:85-102`), y `_armar_ejercicios()`
de Flet hace exactamente lo mismo, con el comentario que lo declara gemelo
(`Flet/Proyecto/app/views/rutinas.py:683-702`). Es decir: el orden de la planilla es una decisión de la
pantalla —el entrenador sube y baja ejercicios con dos flechas
(`Proyecto - PWA/src/frontend/src/views/rutinas/EditorEjercicios.tsx:69-79`)— y el backend lo guarda
tal cual llega.

**Qué escribe y qué lee.** Escribe `Rutina` (`:348-355`) y `Rutina_Ejercicio` (`:119-131`); lee
`Entrenador` y `Empleado` para resolver el autor (`:165-173`), `Ejercicio` para validar (`:112`), y
`Asignacion_Rutina` y `Persona` al armar la respuesta (`:213`, `:62-65`). Coincide con la línea DFD.

**Por qué está hecho así.** La rutina y su planilla se guardan **juntas** porque es un solo acto
humano: el entrenador arma la planilla en el salón, desde el celular, y guarda cómo quedó. Partirlo en
"crear la rutina" y después "agregarle ejercicios" dejaría rutinas vacías cada vez que alguien cierre
el modal a mitad de camino. El precio es un cuerpo de pedido grande y una transacción más larga, que en
este volumen no se siente.

El editor de la planilla es **un solo componente** para dos pantallas que tienen que armar lo mismo: el
formulario del entrenador y el `ArmarMiRutina` del socio. El comentario dice qué pasó cuando eran dos
(`Proyecto - PWA/src/frontend/src/views/rutinas/EditorEjercicios.tsx:13-17`): *"Tenerlo en un solo
lugar evita que una de las dos se quede atrás (la del socio arrancó con un solo día y sin peso)."*

**Nota marcada · dos ejercicios en el mismo (día, orden) dan 500.** `Rutina_Ejercicio` tiene un índice
**único** sobre `(id_rutina, dia, orden)` (`db/schema.sql:1157`) y `_validar_ejercicios()` sólo mira
que cada ejercicio exista. **Corrido:** un `POST` con dos ejercicios en el día 1, orden 1 revienta con
`IntegrityError` —o sea un 500 sin mensaje— y la rutina no queda a medias, porque es la misma
transacción. Hoy no se alcanza desde ninguna pantalla, porque las dos derivan el `orden`; se alcanza
por API. Es el mismo patrón que B-08 anotó en `crear_turno()`: una restricción de la base atajando algo
que el endpoint no explicó, y el usuario recibiendo un 500 en vez de un 409.

**Nota marcada · `nan` pasa el filtro de Flet y no el de la PWA.** `aNumero()` de la PWA rechaza con
`Number.isFinite` (`planillaEjercicios.ts:67`); `_numero()` de Flet compara `n < 0` y, para un campo
decimal, `float('nan')` no es menor que cero. **Corrido:** `_numero('nan', 'el peso', ...)` devuelve
`NaN`; en un campo entero sí lo rechaza, porque `nan.is_integer()` es `False`. Un peso sugerido `NaN`
es el único valor que las dos apps tratan distinto en este formulario.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| Un entrenador manda el id de otro | 403 | *"No podés crear rutinas a nombre de otro entrenador."* | `backend/routers/rutinas.py:153-156` |
| El Dueño no eligió entrenador | 400 | *"Elegí el entrenador que va a quedar a cargo de la rutina."* | `:160-163` |
| El entrenador elegido no existe | 404 | *"El entrenador indicado no existe."* | `:166-168` |
| El entrenador está dado de baja | 400 | *"Ese entrenador está dado de baja. Elegí uno activo."* | `:169-173` |
| Un ejercicio no existe | 404 | *"El ejercicio con id N no existe."* | `:112-116` |
| Días fuera de 1 a 7, o nombre de más de 100 | 422 | el de Pydantic, en inglés | `backend/schemas.py:1437-1445` |

El 422 en inglés es el mismo menor que B-01 anotó para el largo de la contraseña: las dos apps
controlan el rango antes —la PWA recorta con `Math.min(7, Math.max(1, ...))`
(`Proyecto - PWA/src/frontend/src/views/rutinas/RutinaFormModal.tsx:118`) y Flet valida con un mensaje
en castellano (`Flet/Proyecto/app/views/rutinas.py:449-452`)—, así que el texto de Pydantic sólo se ve
llamando la API directamente.

---

### 94. Editar una rutina y reemplazar sus ejercicios

`PUT /rutinas/{id_rutina}` · Dueño, Recepcionista, Entrenador

**Qué resuelve.** Que el entrenador reacomode la planilla y guarde cómo quedó, y que el Dueño pueda
pasarle una rutina a otro entrenador cuando alguien se va.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Endpoint | `backend/routers/rutinas.py` | 523-564 | `editar_rutina()` |
| Esquema | `backend/schemas.py` | 1450-1458 | `RutinaEditarRequest` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/rutinasService.ts` | 274-291 | `actualizarRutina()` |
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/rutinas/RutinaFormModal.tsx` | 37-248 | `RutinaFormModal`, en modo edición |
| Vista Flet | `Flet/Proyecto/app/views/rutinas.py` | 238-517 | `_open_form()`, con `es_edicion` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1323-1325 | `editar_rutina()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 558-559 | `editar_rutina()` |

**Cómo funciona.** La rutina por `_rutina_del_staff()`, el permiso por `_exigir_editable()`, y después
tres bloques (`backend/routers/rutinas.py:543-564`):

1. **El entrenador a cargo**, sólo si vino y **sólo si cambió** (`:546-547`). La condición doble es
   importante: un `PUT` que repite el entrenador actual no pasa por `_resolver_entrenador()`, así que
   **no** se le aplica la validación de "está dado de baja". Es a propósito, y lo dicen las dos
   pantallas desde el otro lado: si el entrenador de la rutina ya no está activo, el selector lo agrega
   igual como opción *"(inactivo)"* *"para no reemplazarlo en silencio al guardar"*
   (`Proyecto - PWA/src/frontend/src/views/rutinas/RutinaFormModal.tsx:64-71` y
   `Flet/Proyecto/app/views/rutinas.py:285-289`). Editarle el nombre a una rutina de alguien que se fue
   no se la pasa a otro.
2. **Los tres campos propios** (`:543-545`).
3. **La planilla, si vino** (`:547-553`): valida, **borra todas** las filas de `Rutina_Ejercicio` de esa
   rutina con un `DELETE` en bloque, y vuelve a insertar.

El `None` del campo `ejercicios` es el que distingue dos pedidos distintos, y el esquema lo declara
(`backend/schemas.py:1456-1457`): *"None = los ejercicios no se tocan. Una lista (aunque sea vacía)
REEMPLAZA todos los de la rutina."* La PWA lo respeta omitiendo **la clave entera** y no mandando
`null` (`Proyecto - PWA/src/frontend/src/services/rutinasService.ts:285-287`).

Y el borrar-y-reinsertar sólo es legítimo por el detalle de claves foráneas de más arriba, que el
docstring nombra (`backend/routers/rutinas.py:535-536`): *"Nada apunta a Rutina_Ejercicio (el registro de series va por
Ejercicio), así que borrar y volver a insertar no rompe ningún historial."* Se verifica en el esquema:
`Registro_Ejercicio` apunta a `Ejercicio` y a `Socio` (`db/schema.sql:1085-1086`), nunca a la fila de
la plantilla. Si apuntara, este endpoint no podría existir en esta forma — sería exactamente el choque
de [el rol que se apaga](A-10-bajas-logicas.md#el-rol-que-se-apaga) y de la habilitación del profesor
de [B-08](B-08-actividades-turnos-horarios.md#71-consultar-el-plantel--84-los-habilitados-de-una-actividad--85-habilitar--86-quitar).

**Qué escribe y qué lee.** Escribe `Rutina` (`:524-528`) y `Rutina_Ejercicio`, borrando e insertando
(`:532-536`); lee `Rutina` (`:229`), `Empleado` y `Entrenador` si cambia el autor (`:165-173`),
`Ejercicio` al validar (`:112`), y `Asignacion_Rutina` y `Persona` al responder. Coincide con la línea
DFD.

**Por qué está hecho así.** Reemplazar la lista entera, en vez de tener endpoints de agregar y quitar
de a uno, **es la forma del formulario**: *"el entrenador reacomoda la planilla y guarda cómo quedó"*
(`:511`). Un `PUT` que recibe el estado final es más simple de llamar y más fácil de razonar que cinco
llamadas incrementales, y no necesita que el cliente lleve la cuenta de qué cambió. Lo que se paga son
`id_rutina_ejercicio` nuevos en cada guardado —las filas no son las mismas filas— y eso sólo sería un
problema si algo las referenciara. No las referencia nada, y es la misma razón por la que se puede
borrar.

**Nota marcada · el `db.expire()` del final no hace falta.** Después del `commit` hay un
`db.refresh(rutina)` y un `db.expire(rutina, ["ejercicios"])` (`:539-540`). El segundo está ahí porque
el `DELETE` en bloque lleva `synchronize_session=False` y deja la colección cargada en la sesión
mintiendo. Pero la sesión del proyecto se crea sin tocar `expire_on_commit`
(`backend/database.py:117`), así que **el `commit` ya expiró todo**, incluida la colección.
**Corrido:** con la línea y sin la línea, y también forzando que la colección esté cargada antes de
editar, la respuesta trae sólo el ejercicio nuevo en los tres casos. No cuesta nada y no hace nada;
queda anotado junto con su pariente del proceso 95, que sí cuesta.

**Nota marcada · un `PUT` que puede borrar en silencio.** `RutinaEditarRequest` tiene `objetivo` y
`dias_por_semana` con default `None` y el endpoint los asigna sin preguntar (`backend/routers/rutinas.py:550-551`), así que un
`PUT` que no mande `objetivo` lo **borra**. Es exactamente el problema que se arregló en el `PUT` de
socio y en el de empleado con `model_fields_set` —*"un formulario incompleto ya no puede borrar datos
en silencio"*— y que en Rutinas sigue abierto. Hoy no se alcanza: las dos apps mandan siempre los
cuatro campos (`rutinasService.ts:280-284` y `Flet/Proyecto/app/views/rutinas.py:464-470`). Se alcanza
por API, y lo hereda cualquier cliente nuevo que mande sólo lo que cambió.

**Qué pasa cuando sale mal.** Los mismos del alta, más los dos de la puerta:

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| No existe, o es la rutina propia de un socio | 404 | *"La rutina no existe."* | `backend/routers/rutinas.py:230-231` |
| Es de otro entrenador | 403 | *"Esa rutina es de otro entrenador: podés verla, no modificarla."* | `:100-103` |
| El entrenador nuevo no existe o está de baja | 404 / 400 | los de `_resolver_entrenador()` | `:166-173` |
| Un ejercicio no existe | 404 | *"El ejercicio con id N no existe."* | `:112-116` |
| Dos ejercicios en el mismo (día, orden) | 500 | ninguno | `db/schema.sql:1157` |

---

## Asignarle una rutina a un socio

### 95. Asignar una rutina a un socio y finalizar la que tenía

`POST /rutinas/{id_rutina}/asignar` · Dueño, Recepcionista, Entrenador

**Qué resuelve.** Que el socio empiece a seguir esta rutina. Si seguía otra, deja de seguirla, y eso
queda escrito.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Endpoint | `backend/routers/rutinas.py` | 370-475 | `asignar_rutina()` |
| Esquemas | `backend/schemas.py` | 1499-1513 | `AsignarRutinaRequest`, `AsignacionRutinaOut` |
| Base | `db/schema.sql` | 804-817, 1162-1163 | `Asignacion_Rutina` y `asignacion_rutina_una_activa_uidx` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/rutinasService.ts` | 316-327 | `asignarRutinaASocio()` |
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/rutinas/AsignarRutinaModal.tsx` | 12-24 | `AsignarRutinaModal` |
| Modal genérico PWA | `Proyecto - PWA/src/frontend/src/views/socios/AsignarASocioModal.tsx` | 29-140 | `AsignarASocioModal` |
| Vista Flet | `Flet/Proyecto/app/views/rutinas.py` | 521-586 | `_open_asignar()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1319-1321 | `asignar_rutina()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 554-555 | `asignar_rutina()` |

**Cómo funciona.** En orden (`backend/routers/rutinas.py:395-464`):

1. **La rutina** por `_rutina_del_staff()` y el permiso por `_exigir_editable()` (`:395-396`).
2. **La rutina está ACTIVA**, o 409 (`:413-417`). Ver más abajo, en el proceso 96, por qué este paso
   es del 2026-10-01 y qué pasaba antes.
3. **El socio** existe, o 404 (`:419-421`).
4. **Las asignaciones ACTIVAS de ese socio** (`:425-430`). Por cada una: si es **esta misma** rutina,
   409; si es otra, pasa a `FINALIZADA` con `fecha_fin` de hoy (`:431-438`).
5. **La asignación nueva**, `ACTIVA`, con `fecha_inicio` de hoy salvo que venga otra (`:454-462`).

El paso 4 es la decisión de negocio, y el docstring la argumenta desde el mostrador (`:381-385`): *"en
el mostrador lo que se quiere decir con «asignale esta» es «cambiale la que tenía» — hacer que falle
obligaría a dar de baja la anterior a mano, y el día que alguien se olvide el socio queda con dos."* Es
[el mostrador con cola](A-01-que-es-olimpos.md#el-mostrador-con-cola): un paso en vez de dos, y sin un
diálogo que pregunte lo obvio. Y la anterior **no se borra**: *"queda como historial, con su estado en
FINALIZADA"* (`:387`), que es la definición misma de una
[asignación con estado](A-05-modelo-de-datos.md#asignación-con-estado).

El bucle del paso 4 recorre una lista aunque la base garantice **una sola** ACTIVA por socio: el índice
parcial `asignacion_rutina_una_activa_uidx` lo impide (`db/schema.sql:1162-1163`). Recorrer igual es
defensa contra los datos que entraron antes de que existiera el índice, y cuesta nada.

El `409` de "ya tiene esa misma rutina" sale **antes** de finalizar nada, dentro del mismo bucle
(`:409-413`), así que no deja al socio sin rutina por haber tocado el botón dos veces. La redacción usa
el nombre completo del socio, *"Franco Distillio ya tiene asignada esa rutina"*, porque el que lo lee
está mirando una lista de nombres y no de ids.

**Qué escribe y qué lee.** Escribe `Asignacion_Rutina` dos veces: el `UPDATE` de la anterior
(`:414-415`) y el `INSERT` de la nueva (`:431-439`). Lee `Rutina` (`:229`), `Socio` (`:396`),
`Asignacion_Rutina` (`:402-407`), `Persona` para el mensaje y la respuesta (`:412`, `:446`), y
`Empleado` y `Entrenador` por `_exigir_editable()` (`:75-84`). Coincide con la línea DFD.

**Por qué está hecho así.** Una sola rutina activa por socio es una regla de dominio —*"Nadie sigue dos
rutinas de musculación a la vez"* (`:382`)— y está defendida en **dos** capas con criterios distintos:
el endpoint la cumple finalizando la anterior, y la base la garantiza con el índice parcial. Las dos
hacen falta: sin el índice, cualquier camino que se olvide de finalizar deja dos activas para siempre;
sin el endpoint, el mostrador recibiría un error de restricción cada vez que quiere cambiar una rutina.
El [índice único parcial](A0-08-sql-indices-y-planes.md#índice-único-parcial) es el que permite que
convivan la regla y el historial, y el comentario del esquema lo dice mejor que cualquier paráfrasis
(`db/schema.sql:815-817`): *"El historial no cuenta, para eso el índice es parcial. Sin el WHERE diría
«una sola rutina en toda su vida», que sería absurdo."*

Lo que **no** vive más en esta tabla es el entrenador: `Asignacion_Rutina` no tiene `id_entrenador`, y
el modelo explica por qué (`backend/models.py:637-639`): *"el entrenador que la escribió sale de
Rutina.id_entrenador. Guardarlo también en la asignación sería una segunda fuente de verdad."* Una sola
pregunta, un solo lugar donde responderla.

**Nota marcada · el `flush` del medio no hace falta, y el comentario que lo justifica dice lo
contrario de lo que pasa.** Entre finalizar la anterior e insertar la nueva hay un `db.flush()` con doce
líneas de comentario (`backend/routers/rutinas.py:440-452`). El argumento: *"SQLAlchemy ordena su flush
poniendo los INSERT ANTES que los UPDATE. Sin esto, la fila nueva entraría mientras la anterior sigue
ACTIVA y la base rechazaría una reasignación que es perfectamente válida."*

**Corrido**, con el índice parcial creado y la función real del router llamada dos veces —una tal cual
está y otra recompilada **sin esa línea**—: las dos reasignan sin error, las dos dejan una `ACTIVA` y
una `FINALIZADA`, y las dos emiten el `UPDATE` **antes** del `INSERT`. El orden es el inverso del que
dice el comentario, y no depende del motor: `save_obj()` de SQLAlchemy recorre las tablas y llama a
`_emit_update_statements()` antes que a `_emit_insert_statements()`
(`.venv/Lib/site-packages/sqlalchemy/orm/persistence.py`, dentro de `save_obj`). O sea que el `flush`
es un viaje de ida y vuelta a São Paulo —44 ms— en cada asignación de rutina, y no evita nada. La
consecuencia para el diseño del índice la saca
[A0-08](A0-08-sql-indices-y-planes.md#el-precio-un-índice-parcial-no-puede-ser-diferido), que es donde
vive el concepto: lo que se paga por no poder diferir no es esta línea, es que ningún camino puede
pasar por un estado intermedio con dos `ACTIVA`.

Lo que hace interesante al hallazgo es el **precedente que el comentario cita**: *"Es el mismo tipo de
detalle que ya mordió en promover_de_lista_de_espera"*. Ahí el `flush` **sí** es imprescindible, y por
un motivo distinto: después de él viene una **consulta** —contar la ocupación del turno— y con
`autoflush=False` esa consulta no vería el cambio que el llamador tiene en memoria
(`backend/turnos.py:166-175`). La regla real es *"hace falta un flush cuando lo que sigue es una
lectura que depende de lo escrito"*, y acá lo que sigue es un `INSERT` y un `commit`. El patrón se
copió sin su condición de aplicación, y de paso se le inventó un mecanismo. Es el mismo pariente que el
`db.expire()` del proceso 94: dos defensas que la configuración de la sesión ya cubre. No se tocó
ninguna de las dos.

**Nota marcada · `fecha_fin` entra y nadie la manda.** `AsignarRutinaRequest` acepta `fecha_inicio` y
`fecha_fin` (`backend/schemas.py:1499-1502`) y el endpoint las guarda tal cual (`:435-436`), sin
comparar una con otra. Ninguna de las dos apps las manda: la PWA manda sólo `id_socio`
(`Proyecto - PWA/src/frontend/src/services/rutinasService.ts:325`) y Flet lo mismo
(`Flet/Proyecto/app/api_client.py:555`). Por API se puede crear una asignación que termina antes de
empezar.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| No existe, o es la rutina propia de un socio | 404 | *"La rutina no existe."* | `backend/routers/rutinas.py:230-231` |
| Es de otro entrenador | 403 | *"Esa rutina es de otro entrenador: podés verla, no modificarla."* | `:100-103` |
| La rutina está dada de baja | 409 | *"Esa rutina está dada de baja: reactivala antes de asignarla."* | `:413-417` |
| El socio no existe | 404 | *"El socio no existe."* | `:420-421` |
| Ya tiene asignada esa misma rutina | 409 | *"NOMBRE ya tiene asignada esa rutina."* | `:432-436` |

---

### 90. Consultar el historial de rutinas de un socio

`GET /rutinas/asignaciones/socio/{id_socio}` · Dueño, Recepcionista, Entrenador, Nutricionista

**Qué resuelve.** Qué rutinas le asignó el personal a este socio, la actual primero. Responde "¿qué
viene entrenando?".

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Endpoint | `backend/routers/rutinas.py` | 478-516 | `rutinas_de_socio()` |
| Esquema | `backend/schemas.py` | 1505-1513 | `AsignacionRutinaOut` |
| Base | `db/schema.sql` | 804-817, 1159 | `Asignacion_Rutina` y su índice `(id_socio, estado)` |
| Service PWA | — (no existe) | | ninguna pantalla lo llama |
| Vista Flet | — (no existe) | | ninguna pantalla lo llama |

**Cómo funciona.** Una consulta con `JOIN`, dos filtros y un orden
(`backend/routers/rutinas.py:496-503`): las asignaciones de ese socio cuyas rutinas tienen entrenador,
por `fecha_inicio` descendente. Después, un armado fila por fila (`:504-516`).

Los dos filtros son los dos límites del endpoint. El primero —`AsignacionRutina.id_socio == id_socio`—
es un `id` **por parámetro**, y el docstring aclara que eso es legítimo sólo porque es un endpoint de
gestión (`:487-490`): *"El socio consultando SU propia rutina va por el portal (mi-rutina), que filtra
por el id_socio firmado en su token y no acepta un id por parámetro — si aceptara uno, cualquier socio
podría pedir la rutina de otro cambiando un número."* Es la frontera de
[identidad firmada](A-07-autenticacion.md#identidad-firmada) dicha desde el lado que **no** la
necesita: el personal ya tiene permiso para ver a cualquier socio, así que para él el id es un dato.

El segundo —`Rutina.id_entrenador.isnot(None)`— es la rutina propia otra vez (`:492-494`): *"son suyas
y no parte del historial que gestiona el personal. El socio las ve por su portal; el staff, ni siquiera
en el historial de asignaciones."* Es el único lugar del módulo donde la exclusión de la rutina propia
cambia el significado de una lista en vez de ocultar una fila: el historial que ve el personal **no es**
todo lo que el socio entrenó.

**Qué escribe y qué lee.** Lee `Asignacion_Rutina` y `Rutina` (`:496-503`), y `Socio` y `Persona` para
el nombre (`:508`). No escribe nada. Coincide con la línea DFD.

**Por qué está hecho así.** La lectura de este endpoint es la de los demás del módulo —una consulta y
un armado—, y lo único que tiene de propio es el orden: *"la actual primero"* (`:485`) por
`fecha_inicio` descendente y no por estado. Con una sola activa garantizada por el índice, ordenar por
fecha alcanza: la activa es siempre la más nueva.

**Nota marcada · ningún cliente lo llama.** No hay función en `rutinasService.ts` que pida
`/rutinas/asignaciones/socio/...` ni nada en `api_client.py` de Flet; una búsqueda de `asignaciones`
sobre las dos apps devuelve sólo las del entrenador a cargo y comentarios. Es una pérdida, no un resto:
la pregunta que contesta —*"¿qué viene entrenando este socio?"*— es la que uno se hace parado frente a
su ficha, al lado del botón de contacto de emergencia, y es la mitad que le falta a
`asignados` para ser útil. Es el mismo caso que el historial de ingresos de un socio de
[B-06](B-06-asistencia.md#con-qué-se-conecta) y que `GET /socios/entrenadores/{id}/socios` de
[B-02](B-02-socios.md#con-qué-se-conecta): tres endpoints escritos, probados por su forma, y sin
pantalla que los use.

**Qué pasa cuando sale mal.** Un socio que no existe devuelve **lista vacía**, no 404 — la consulta no
pregunta por el socio, filtra por su id. La línea DFD lo declara así (*"lista vacia si no tiene
ninguna"*). Y 403 para el Profesor y el Socio.

---

## Sacar una rutina de circulación

### 96. Dar de baja una rutina del catálogo · 97. Reactivar una rutina del catálogo

`POST /rutinas/{id_rutina}/baja` y `POST /rutinas/{id_rutina}/reactivar` · Dueño, Recepcionista,
Entrenador

**Qué resuelve.** Que una rutina deje de ofrecerse para asignar, sin tocar a los socios que la están
siguiendo. Y que vuelva.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Endpoints | `backend/routers/rutinas.py` | 567-611 | `dar_de_baja_rutina()`, `reactivar_rutina()` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/rutinasService.ts` | 293-312 | `darDeBajaRutina()`, `activarRutina()` |
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/rutinas/RutinasView.tsx` | 119-152 | `pedirBaja()`, `activar()` |
| Tarjeta PWA | `Proyecto - PWA/src/frontend/src/views/rutinas/RutinaCard.tsx` | 23-113 | `RutinaCard`, con un botón que cambia según el estado |
| Vista Flet | `Flet/Proyecto/app/views/rutinas.py` | 216-234 | `_cambiar_estado()`, `_aplicar()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1327-1331 | `baja_rutina()`, `reactivar_rutina()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 562-567 | `baja_rutina()`, `reactivar_rutina()` |

**Cómo funciona.** Los dos endpoints son el mismo endpoint con el booleano al revés: la puerta, el
permiso, el chequeo de que el estado **cambie** de verdad, y una línea de asignación
(`backend/routers/rutinas.py:584-593` y `:602-611`). Los dos devuelven la `RutinaOut` completa, así que
las pantallas pueden actualizar la tarjeta sin recargar la lista — y la PWA lo aprovecha en la
reactivación (`actualizarEnLista`, `RutinasView.tsx:147`) pero no en la baja, donde recarga (`:130`).

**Qué escribe y qué lee.** Escribe `Rutina.activo` (`backend/routers/rutinas.py:590`, `:608`); lee `Rutina`,
`Rutina_Ejercicio`, `Ejercicio`, `Asignacion_Rutina` y la cadena del entrenador, todo para armar la
respuesta. Coincide con la línea DFD, que declara esa lista larga de lecturas por esa razón.

**Por qué está hecho así.** Es una [baja lógica](A-10-bajas-logicas.md#baja-lógica-soft-delete), y tiene
los dos argumentos separados.

El primero es el de siempre: *"Borrarla rompería las asignaciones históricas —quedarían apuntando a una
rutina inexistente— y con ellas el registro de qué entrenó cada socio"*
(`backend/routers/rutinas.py:576-577`).
`Asignacion_Rutina.id_rutina` es una clave foránea sin acción al borrar (`db/schema.sql:1084`), así que
el `DELETE` fallaría igual: el soft delete no es una preferencia, es la única salida.

El segundo es de producto y es el que define el alcance: *"Los socios que la están siguiendo AHORA no se
tocan: la rutina desactivada deja de ofrecerse para asignaciones nuevas, pero quien ya la tiene la
termina. Cortársela de un día para el otro dejaría a alguien sin plan de entrenamiento sin que nadie lo
decidiera"* (`:556-559`). Es la misma asimetría que la baja de una actividad en
[B-08](B-08-actividades-turnos-horarios.md#con-qué-se-conecta): la baja corta el **futuro** y no toca lo
ya acordado. Con una diferencia a favor: acá eso no deja nada pendiente de resolver, porque una rutina
no se cobra.

Lo que no hace la baja: **no** saca la rutina del catálogo que devuelve el proceso 88.
`listar_rutinas()` no filtra por `activo` (`backend/routers/rutinas.py:300-305`), así que la rutina de
baja sigue apareciendo, con su chip *"Inactiva"*. Eso es deliberado y es lo que hace posible
reactivarla: si desapareciera de la lista, el proceso 97 no tendría desde dónde llamarse.

**Lo que la baja no hacía, hasta el 2026-09-30.** Esto salió escribiendo el capítulo y se arregló en
el mismo día, así que vale contarlo completo: las dos pantallas y los dos docstrings prometían que la
rutina desactivada *"deja de ofrecerse para asignar"*, y **ningún lugar lo hacía cumplir**.
`asignar_rutina()` no miraba `rutina.activo`; la tarjeta de la PWA dibujaba *"Asignar"* con sólo
`puedeGestionar`; y el diálogo de detalle de Flet lo ponía al lado de *"Reactivar"*, o sea que ofrecía
las dos cosas a la vez. La baja hacía exactamente una cosa: pintar el chip *"Inactiva"*.

El arreglo son **tres capas y dos módulos**, y el reparto es el del principio
[el frontend esconde, el backend rechaza](A-08-autorizacion.md#el-frontend-esconde-el-backend-rechaza):

| Capa | Qué hace ahora | Dónde |
|---|---|---|
| Endpoint | 409 *"Esa rutina está dada de baja: reactivala antes de asignarla."* | `backend/routers/rutinas.py:413-417` |
| Tarjeta PWA | el botón pide `puedeGestionar && !yaInactiva` | `Proyecto - PWA/src/frontend/src/views/rutinas/RutinaCard.tsx:100-109` |
| Detalle PWA | el botón pide `rutina.activo`; *"Editar"* queda igual | `Proyecto - PWA/src/frontend/src/views/rutinas/RutinaDetailModal.tsx:157-174` |
| Flet | `_asignable()`, usado por la tarjeta y por el diálogo | `Flet/Proyecto/app/views/rutinas.py:75-87`, `:99-100`, `:191-197` |

Tres cosas que vale subrayar del arreglo:

- **El 409 es el que de verdad lo impide**; esconder el botón evita el error, no lo prohíbe. Por eso el
  comentario del endpoint lo dice en esos términos (`backend/routers/rutinas.py:406-408`).
- **409 y no 400**: el pedido está bien formado, lo que choca es el estado de la rutina. Y el mensaje
  dice **qué hacer** —reactivala— porque se hace desde la misma pantalla, que es
  [el sistema informa, no juzga](A-01-que-es-olimpos.md#el-sistema-informa-no-juzga).
- **Editar sigue permitido** con la rutina de baja: se la corrige y después se la reactiva. Lo que se
  cierra es asignarla, no tocarla.

Y el mismo arreglo fue a **Nutrición**, que tenía el defecto calcado: `asignar_dieta()` tampoco miraba
`dieta.activo` y las cuatro pantallas ofrecían *"Asignar"* sobre un plan de baja
(`backend/routers/nutricion.py:359-371`, y `_asignable()` en
`Flet/Proyecto/app/views/nutricion.py:50-57`). Lo explica [B-10](B-10-nutricion.md).

**Corrido**, llamando a las dos funciones reales contra SQLite en memoria: el plan y la rutina de baja
responden 409 y no dejan nada escrito, y los activos se siguen asignando. Y el árbol de controles de
Flet, armado con estado simulado, confirma que de las cuatro pantallas desapareció *"Asignar"* y que
siguen estando *"Editar"*, *"Reactivar"* y *"Ver"*.

El par de confirmaciones es asimétrico a propósito, y las dos apps lo dicen igual. La baja pregunta;
reactivar, no: *"reactivar es una acción de bajo riesgo y reversible (siempre se puede volver a dar de
baja)"* (`RutinasView.tsx:139-141`) y *"Baja con confirmación; reactivar sin, porque es reversible y de
bajo riesgo"* (`Flet/Proyecto/app/views/rutinas.py:217`). Y el texto del diálogo es el mismo en las dos,
palabra por palabra: *"Deja de ofrecerse para asignar. Los socios que la están siguiendo la terminan."*
Es uno de los textos que se reescribieron al sacar las promesas de auditoría: antes decía *"queda
registrada en Auditoría"*, y no hay auditoría (`RutinasView.tsx:123-125`).

**Nota marcada · en Flet el botón vive en otro lado.** La PWA pone el botón de baja/reactivación en el
encabezado de **la tarjeta** (`RutinaCard.tsx:38-40`); Flet lo pone en las acciones del **diálogo de
detalle** (`Flet/Proyecto/app/views/rutinas.py:183-201`), así que hay que abrir la rutina para darla de
baja. Un paso más que en la referencia.

**Nota marcada · los títulos 96 y 97 del archivo de procesos.** Los dos están encabezados con su propia
ruta —*"96. POST /rutinas/{id_rutina}/baja"*— en vez de con un nombre
(`PROCESOS-LOGICOS-REQUERIDOS.md`). El nombre sí está, adentro de la línea DFD: *"(96. Dar de baja una
rutina del catalogo)"* y *"(97. Reactivar una rutina del catalogo)"*. Este capítulo usa esos nombres,
que son los que el propio archivo declara como evento lógico. Son los dos únicos de los diez con el
encabezado así.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| No existe, o es la rutina propia de un socio | 404 | *"La rutina no existe."* | `backend/routers/rutinas.py:230-231` |
| Es de otro entrenador | 403 | *"Esa rutina es de otro entrenador: podés verla, no modificarla."* | `:100-103` |
| Ya estaba desactivada | 400 | *"Esa rutina ya estaba desactivada."* | `:586-588` |
| Ya estaba activa | 400 | *"Esa rutina ya estaba activa."* | `:604-606` |

Los dos 400 del final son lo que la línea DFD declara como *"rutina que ya estaba desactivada"* y
*"rutina que ya estaba activa"*: el sistema no deja pasar en silencio una operación que no hace nada.

---

## Con qué se conecta

- **Es la misma idea que…** [aislamiento de lo propio](A-08-autorizacion.md#aislamiento-de-lo-propio):
  la rutina propia del socio es invisible para el personal y responde el **mismo** 404 que una
  inexistente, porque un 403 confirmaría que existe.
- **Es la misma idea que…**
  [asignación con estado](A-05-modelo-de-datos.md#asignación-con-estado): asignar una rutina nueva
  finaliza la anterior en vez de borrarla, y el índice único parcial garantiza una sola activa sin
  tocar el historial.
- **Es la misma idea que…** [baja lógica](A-10-bajas-logicas.md#baja-lógica-soft-delete): la rutina se
  apaga en vez de borrarse, corta el futuro y no toca a quien ya la sigue — y sigue en el catálogo,
  porque si desapareciera no habría desde dónde reactivarla.
- **Existe por culpa de…** [el rol que se apaga](A-10-bajas-logicas.md#el-rol-que-se-apaga):
  `_entrenador_de_sesion()` pregunta por el flag y no por la fila, porque si no, quien pasó de
  entrenador a recepcionista seguiría editando rutinas.
- **Es el mismo problema que…** [N+1](A0-09-el-orm.md#n1): los tres listados del módulo cuestan
  2 + N + 3·E consultas —entre 11 y 26 para seis rutinas, según cuántos entrenadores distintos haya— y
  el historial de un socio pide por fila una `Rutina` que su propio `JOIN` ya trajo.
- **Se contradice con…** [`flush` contra `commit`](A0-09-el-orm.md#flush-contra-commit): el `flush` de
  la asignación se justifica con un orden de sentencias que SQLAlchemy no usa, y cuesta un viaje a la
  base que no evita nada; el que lo inspiró, en la lista de espera, sí hace falta porque después viene
  una lectura.
- **Es la misma idea que…**
  [aplicación gemela y componente gemelo](A-03-dos-apps-un-backend.md#aplicación-gemela-y-componente-gemelo):
  el editor de la planilla es **un** componente para el entrenador y para el socio, y lo es porque
  cuando eran dos, la del socio se quedó atrás.
- **Existe por culpa de…**
  [almacén que no es tabla](A-05-modelo-de-datos.md#almacén-que-no-es-tabla): el `video_local` de cada
  ejercicio no es una columna, es un `is_file()`, y por eso un ejercicio puede existir sin su video.
- **Es la misma idea que…**
  [el frontend esconde, el backend rechaza](A-08-autorizacion.md#el-frontend-esconde-el-backend-rechaza):
  que una rutina de baja no se asigne lo garantiza el 409 del endpoint, y esconder el botón en las
  cuatro pantallas es lo que evita que alguien se lleve el error.
