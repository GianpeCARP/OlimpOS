# B-10 · Nutrición

*Procesos 98 a 107. Piso del capítulo: la línea que implementa cada paso, en las tres capas.*

El encabezado del router dice qué es esto en tres palabras: *"ESPEJO ESTRUCTURAL DE RUTINAS"*
(`backend/routers/nutricion.py:6-20`). Diez procesos que son los diez de
[B-09](B-09-rutinas.md) con otros nombres, y el comentario de la base lo pone en dos renglones
(`db/schema.sql:861-863`):

```
Rutina -> Rutina_Ejercicio -> Asignacion_Rutina -> Registro_Ejercicio
Dieta  -> Comida           -> Asignacion_Dieta  -> Registro_Comida
```

Así que este capítulo hace una cosa distinta de los anteriores: **no vuelve a explicar lo que ya está
explicado**. Primero la tabla de correspondencias, después las diferencias —que son cuatro y una de
ellas es la más interesante de los dos módulos juntos—, y recién entonces los procesos, cortos, con su
tabla de código y lo que tengan de propio.

| Tema | Procesos |
|---|---|
| Los platos del catálogo | 101, 102 |
| El catálogo de dietas: leer y escribir | 98, 103, 99, 104 |
| Asignarle una dieta a un socio | 105, 100 |
| Sacar una dieta de circulación | 106, 107 |

**Lo que se corrió, y cómo.** Cinco cosas, con SQLite en memoria y las funciones reales del router
(`b10_nutricion.py` en el scratchpad de la sesión). La más importante necesitó algo que B-09 no:
**`PRAGMA foreign_keys=ON`**, porque SQLite no exige las claves foráneas por defecto y justamente lo
que había que probar era una. Y un detalle del armado que sale de ahí: con el pragma puesto, la `Sede`
de prueba ya no puede inventarse un `id_dueno`; hay que crearle el `Dueno`.

---

## Lo que es igual, proceso por proceso

| Nutrición | Rutinas | Qué comparten |
|---|---|---|
| 98 `GET /nutricion` | [88](B-09-rutinas.md#88-consultar-el-catálogo-de-rutinas) | el catálogo sin el detalle, con `asignados` y `puede_editar` por fila |
| 99 `POST /nutricion` | [89](B-09-rutinas.md#89-crear-una-rutina-del-catálogo-con-sus-ejercicios) | crear la plantilla con su contenido en una transacción |
| 100 `GET …/asignaciones/socio/{id}` | [90](B-09-rutinas.md#90-consultar-el-historial-de-rutinas-de-un-socio) | el historial del socio, y **ningún cliente que lo llame** |
| 101 `GET …/catalogo-comidas` | [91](B-09-rutinas.md#91-consultar-el-catálogo-de-ejercicios) | el catálogo compartido del que se eligen las piezas |
| 102 `POST …/catalogo-comidas` | [92](B-09-rutinas.md#92-dar-de-alta-un-ejercicio-en-el-catálogo) | sumar una pieza, con el nombre `UNIQUE` chequeado a mano |
| 103 `GET /nutricion/{id}` | [93](B-09-rutinas.md#93-consultar-el-detalle-de-una-rutina) | el detalle con el contenido ordenado por el backend |
| 104 `PUT /nutricion/{id}` | [94](B-09-rutinas.md#94-editar-una-rutina-y-reemplazar-sus-ejercicios) | editar y **reemplazar el contenido en bloque** |
| 105 `POST /nutricion/{id}/asignar` | [95](B-09-rutinas.md#95-asignar-una-rutina-a-un-socio-y-finalizar-la-que-tenía) | asignar y finalizar la anterior, con el índice único parcial atrás |
| 106 y 107 baja y reactivar | [96 y 97](B-09-rutinas.md#96-dar-de-baja-una-rutina-del-catálogo--97-reactivar-una-rutina-del-catálogo) | baja lógica, y los dos 400 de "ya estaba así" |

Y los nueve mecanismos que se heredan tal cual, cada uno explicado una sola vez y allá:

| Mecanismo | Dónde está explicado | El gemelo acá |
|---|---|---|
| La plantilla propia del socio es invisible y da **404** | [B-09](B-09-rutinas.md#la-rutina-propia-del-socio-es-invisible-para-el-personal-y-responde-404) | `_dieta_del_staff()` (`backend/routers/nutricion.py:196-205`) |
| Qué es "mío": tres funciones y un campo en la respuesta | [B-09](B-09-rutinas.md#qué-es-mía-tres-funciones-y-un-campo-en-la-respuesta) | `_nutricionista_de_sesion()`, `_puede_editar()`, `_exigir_editable()` (`:71-80`, `:117-130`) |
| El autor sale de la sesión, y el Dueño tiene que elegir | [B-09](B-09-rutinas.md#el-autor-sale-de-la-sesión-no-del-cuerpo-del-pedido) | `_resolver_nutricionista()` (`:83-114`) |
| El rol apagado no es rol (`rol_activo`) | [A-10](A-10-bajas-logicas.md#el-rol-que-se-apaga) | `:79-80` |
| El selector recortado al propio | [B-03](B-03-personal.md) · `GET /personal/nutricionistas` | `backend/routers/personal.py:523-538` |
| Validar todo el contenido antes de insertar nada | [B-09](B-09-rutinas.md#89-crear-una-rutina-del-catálogo-con-sus-ejercicios) | `_agregar_comidas()` (`backend/routers/nutricion.py:139-142`) |
| El `flush` de la asignación, que no hace falta | [B-09](B-09-rutinas.md#95-asignar-una-rutina-a-un-socio-y-finalizar-la-que-tenía) y [A0-08](A0-08-sql-indices-y-planes.md#el-precio-un-índice-parcial-no-puede-ser-diferido) | `:406`, con el mismo comentario copiado |
| El `db.expire()` del final, que tampoco | [B-09](B-09-rutinas.md#94-editar-una-rutina-y-reemplazar-sus-ejercicios) | `:522` |
| Una rutina/dieta de baja no se asigna (409) | [B-09](B-09-rutinas.md#96-dar-de-baja-una-rutina-del-catálogo--97-reactivar-una-rutina-del-catálogo) | `:359-371`, del 2026-10-01 |

El último merece una línea aparte, porque es el único de la lista que **cambió escribiendo estos dos
capítulos**: el defecto —que la baja prometiera que el plan deja de ofrecerse y nada lo impidiera—
estaba calcado en los dos módulos, y se arregló en los dos a la vez. Ésa es la otra cara de tener el
mismo código escrito dos veces: el defecto también viene duplicado.

---

## Las cuatro diferencias

### 1. El plato es un catálogo con `activo`, y la comida puede ser texto libre

`Ejercicio` y `Catalogo_Comida` cumplen el mismo papel —la pieza compartida— pero no son iguales:

| | `Ejercicio` | `Catalogo_Comida` |
|---|---|---|
| Columna `activo` | no tiene | **sí** (`db/schema.sql:870`) |
| ¿La pieza es obligatoria? | sí: `Rutina_Ejercicio.id_ejercicio` es `NOT NULL` | **no**: `Comida.id_catalogo_comida` es nullable |
| Si no está en el catálogo | hay que cargarlo primero | se escribe como **texto libre** |

Lo segundo es la diferencia que se nota. `Comida` admite un plato del catálogo **o** una descripción
suelta, y la base lo exige con un `CHECK` (`db/schema.sql:912-914`):

```sql
CONSTRAINT chk_comida_plato CHECK (id_catalogo_comida IS NOT NULL OR descripcion IS NOT NULL)
```

El porqué está en el esquema de la API, y es de producto (`backend/schemas.py:1522-1527`): *"El texto
libre existe porque el catálogo del gimnasio suele arrancar vacío y armar un plan no puede esperar a
que alguien cargue cada plato."* En Rutinas no hacía falta porque un ejercicio **es** un ejercicio en
cualquier rutina; un *"pollo con arroz"*, en cambio, cambia de cantidades y de contexto, y el
encabezado del router usa justamente eso para explicar por qué `Comida` no es un catálogo
(`backend/routers/nutricion.py:16-20`): *"'pollo con arroz' descripto en una dieta no es la misma
entidad que en otra, porque cambian las cantidades y el contexto."*

De ahí sale el `_a_comida_out()` (`:153-168`), que decide de dónde leer cada campo: si la comida
apunta a un plato, el nombre, la descripción y las calorías salen **del catálogo**; si es texto libre,
el nombre es ese texto y **no hay calorías**. El comentario del esquema de la base lo justifica desde
las formas normales (`db/schema.sql:873-876`): *"Las calorias, el nombre y la descripcion viven ACA
porque dependen del PLATO, no de la dieta ni del dia en que aparece. Es exactamente la razon por la
que Comida.calorias y Comida.descripcion fueron eliminadas."* Y después `descripcion` **volvió**, con
otro significado —el texto libre— lo que la historia del esquema anota al lado (`:923-926`).

El `CHECK` no se espera a la base: lo valida el esquema de la API con un `model_validator`
(`backend/schemas.py:1534-1540`), que devuelve un 422 en castellano —*"Cada comida necesita un plato
del catálogo o una descripción"*— en vez del error de restricción. Es el mismo criterio del nombre
duplicado: **la restricción de la base es el piso, el chequeo a mano es el mensaje.**

**Nota marcada · el `activo` de un plato no se puede apagar desde ninguna parte.**
`listar_catalogo_comidas()` filtra por `CatalogoComida.activo.is_(True)` (`backend/routers/nutricion.py:226`)
y el alta lo pone en `True` (`:252`). No existe ningún endpoint que lo baje: ni un `PUT`, ni un
`/baja`, nada. O sea que la columna sólo se puede cambiar editando la base a mano, y un plato cargado
mal se queda en el catálogo para siempre. Es el mismo caso que los planes de membresía de
[B-05](B-05-cobros-y-pagos.md#con-qué-se-conecta): el filtro existe, el flag existe, y la pantalla que
lo movería no.

### 2. Algo SÍ apunta a `Comida` — y el docstring dice que no

Ésta es la diferencia importante del capítulo, y la que convierte al proceso 104 en otra cosa que el 94.

En Rutinas, el `PUT` puede borrar todas las filas de `Rutina_Ejercicio` y volver a insertarlas porque
**nada las referencia**: `Registro_Ejercicio` apunta a `Ejercicio`, no a la fila de la plantilla
(`db/schema.sql:1086`). Acá no es así. `Registro_Comida.id_comida` apunta a **`Comida`**
(`db/schema.sql:1097`), o sea a la fila de la plantilla, y por una razón que la tabla explica
(`db/schema.sql:968-970`): *"id_comida = que comida de la dieta CORRESPONDIA. comida_ingerida = que
comio DE VERDAD. Son dos hechos distintos: el socio pudo comer algo diferente de lo planificado, y
registrar esa diferencia es el proposito de la tabla."*

Esa columna es **nullable** (`db/schema.sql:950`), y eso es lo que hace posible la salida que tomó el
endpoint: antes de borrar las comidas viejas, les **desvincula** los registros
(`backend/routers/nutricion.py:506-518`):

```python
ids_viejas = [c.id_comida for c in dieta.comidas]
if ids_viejas:
    db.query(RegistroComida).filter(RegistroComida.id_comida.in_(ids_viejas)) \
        .update({RegistroComida.id_comida: None}, synchronize_session=False)
db.query(Comida).filter(Comida.id_dieta == dieta.id_dieta).delete(synchronize_session=False)
```

El comentario de arriba dice qué se gana y qué se pierde (`:507-511`): *"lo que un socio registró
contra una comida del plan viejo conserva su texto y sus macros, sólo pierde el vínculo. Sin esto,
borrar las comidas fallaría por la FK apenas alguien hubiera registrado algo."*

**Y el docstring de la misma función dice lo contrario** (`:490-492`): *"Nada apunta a Comida
(Registro_Comida lleva el texto de lo comido, no una FK obligatoria al plan), así que borrar y volver a
insertar no rompe historial."* Lo que pasó se ve leyendo las dos cosas juntas: el docstring se copió de
`editar_rutina`, donde la frase es verdad, y el cuerpo se adaptó. *"No una FK obligatoria"* es cierto
—es opcional— y es justo lo que permite ponerla en `NULL`; lo que no es cierto es *"nada apunta"*. La
frase describe el módulo del que se copió, no éste.

**Corrido**, con `PRAGMA foreign_keys=ON` y un `Registro_Comida` apuntando a una comida del plan:

| Qué se corrió | Resultado |
|---|---|
| El `PUT` tal cual está | reemplaza las comidas, y el registro queda con `id_comida = NULL` **conservando** su texto y sus 900 kcal |
| El mismo `PUT` sin esas cuatro líneas | **`IntegrityError`**: la clave foránea frena el borrado — un 500 sin mensaje |
| El mismo `PUT` sin esas líneas, pero sin ningún registro cargado | pasa sin error |

La tercera fila es la que explica por qué un defecto así puede vivir mucho tiempo: **el camino falla
sólo si alguien ya registró una comida**. Con el catálogo recién cargado y nadie usando el portal, el
`PUT` anda perfecto.

Y queda una pregunta de producto que el código resuelve en silencio: el registro desvinculado **pierde
contra qué comida se comparaba**. Lo que el socio comió sigue ahí, pero *"lo que correspondía"* se
borra, así que una comparación plan-contra-realidad hacia atrás no se puede reconstruir después de una
edición del plan. Es una decisión razonable —la alternativa sería no poder editar nunca un plan en uso—
pero no está anotada como decisión en ningún lado.

### 3. El objetivo calórico no es la suma de las comidas

`Dieta.calorias_diarias` parece un derivado y no lo es. El comentario de la columna es una de las
mejores defensas del esquema contra su propia regla (`db/schema.sql:897-901`): *"Objetivo calorico
diario pautado por el nutricionista. NO es la suma de Comida.calorias: es la intencion clinica, no el
contenido. Que la suma real difiera del objetivo es informacion valida, no una inconsistencia. Por eso
no viola la regla de «no guardar lo derivable»: no es derivable de nada."*

Es el contraejemplo exacto de [estado derivado](A-09-estados-derivados.md#estado-derivado), y por eso
vale tenerlo a mano: la regla no es *"no guardes números que se puedan calcular"*, es *"no guardes dos
veces el mismo hecho"*. El objetivo y el contenido son **dos hechos distintos**, y la distancia entre
los dos es lo que el nutricionista mira. La pantalla del socio lo usa así: *"Mi progreso"* compara los
últimos siete días contra este objetivo con una tolerancia del ±10%.

Rutinas no tiene nada equivalente: `dias_por_semana` sí es la intención y la planilla es el contenido,
pero a nadie se le ocurriría sumarlos.

### 4. El que mira sin tocar es el Entrenador

La simetría de permisos está dicha en los dos encabezados y es exacta:

| Sección | TOTAL | LECTURA | NINGUNO |
|---|---|---|---|
| Rutinas | Dueño, Recepcionista, **Entrenador** | *Nutricionista* | Profesor, Socio |
| Nutrición | Dueño, Recepcionista, **Nutricionista** | *Entrenador* | Profesor, Socio |

Sale de la matriz (`backend/permisos.py:178`, `:210`, `:241`, `:264`, y `GESTION_DIETAS` en `:221` y
`:273`). El porqué del cruce lo dice el router (`backend/routers/nutricion.py:24-27`): el Entrenador
*"puede consultar la dieta de un socio para ver de quién es y no contradecirla con la rutina, pero no
darla de alta ni desligarla"*. Cada profesional lee el plan del otro para no chocarlo, y no lo toca.

En la práctica eso significa que los procesos **98, 100, 101 y 103** —los cuatro de lectura— los puede
llamar el Entrenador, y los otros seis no. Es la única diferencia de roles entre los dos módulos.

### Lo que cuesta leer un plan, medido

Los tres listados tienen el mismo N+1 que los de Rutinas, con la misma forma y los mismos números.
**Corrido** con 6 dietas, 5 comidas cada una y 4 asignaciones cada una, todas del mismo nutricionista:

| Proceso | Consultas | De dónde salen |
|---|---|---|
| 98 `listar_dietas` | **11** | 2 fijas + 1 por dieta (`Asignacion_Dieta`) + 3 por nutricionista distinto |
| 103 `obtener_dieta` | **12** | 7 fijas + **1 por comida**, que es la del plato en `Catalogo_Comida` |
| 100 `dietas_de_socio` | **9** | 3 fijas + 1 por asignación, de `Dieta`, que su propio `JOIN` ya trajo |

Son los mismos tres números de [B-09](B-09-rutinas.md#lo-que-cuesta-leer-una-rutina-medido) —no es
casualidad: es el mismo código—. Vale la misma fórmula, **2 + N + 3·P** con `P` profesionales
distintos, y la misma lectura: el costo del listado depende de los datos porque lo que ahorra es
[el mapa de identidad](A0-09-el-orm.md#sesión-y-mapa-de-identidad) y no una carga anticipada.

---

## Los platos del catálogo

### 101. Consultar el catálogo de platos

`GET /nutricion/catalogo-comidas` · Dueño, Recepcionista, Entrenador, Nutricionista

**Qué resuelve.** Los platos con los que se arma un plan, con su nombre y sus calorías.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Endpoint | `backend/routers/nutricion.py` | 212-229 | `listar_catalogo_comidas()` |
| Esquema | `backend/schemas.py` | 1555-1562 | `CatalogoComidaOut` |
| Base | `db/schema.sql` | 865-876 | `Catalogo_Comida` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/nutricionService.ts` | 144-156 | `aPlato()`, `listarPlatos()` |
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/nutricion/PlanFormModal.tsx` | 58-420 | `PlanFormModal`, el selector de platos |
| Vista Flet | `Flet/Proyecto/app/views/nutricion.py` | 285-515 | `_open_form()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 609-614 | `get_platos()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 594-595 | `obtener_catalogo_comidas()` |

**Cómo funciona.** Una consulta con un filtro —`activo` en `True`— ordenada por nombre
(`backend/routers/nutricion.py:225-228`). La ruta está declarada **antes** de `/{id_dieta}` y el
docstring dice por qué (`:222-223`): *"FastAPI resuelve por orden de declaración, y si estuviera
después leería «catalogo-comidas» como un id."* Es la misma precaución que `/rutinas/ejercicios`.

**Qué escribe y qué lee.** Lee `Catalogo_Comida` (`:225-228`). No escribe. Coincide con la línea DFD,
que además es la única de los diez que menciona el filtro (*"catalogo de platos activos"*).

**Por qué está hecho así.** Es el único catálogo del sistema con `activo`, y el filtro está del lado
del servidor para que ninguna de las dos apps pueda ofrecer un plato retirado. Lo que se paga está en
la nota marcada de arriba: no hay cómo retirarlo.

**Qué pasa cuando sale mal.** Sólo 403, para el Profesor y el Socio.

---

### 102. Dar de alta un plato en el catálogo de comidas

`POST /nutricion/catalogo-comidas` · Dueño, Recepcionista, Nutricionista

**Qué resuelve.** Cargar un plato nuevo, con sus calorías, para poder usarlo en los planes.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Endpoint | `backend/routers/nutricion.py` | 232-256 | `crear_plato()` |
| Esquema | `backend/schemas.py` | 1587-1591 | `CatalogoComidaCrear` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/nutricionService.ts` | 158-173 | `crearPlato()` |
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/nutricion/PlatoFormModal.tsx` | 14-84 | `PlatoFormModal` |
| Vista Flet | `Flet/Proyecto/app/views/nutricion.py` | 584-627 | `_open_plato()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 616-617 | `crear_plato()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 598-599 | `crear_plato()` |

**Cómo funciona.** Chequeo de nombre duplicado y un `INSERT` con `activo=True`
(`backend/routers/nutricion.py:247-256`). El docstring cuenta de dónde salió el endpoint (`:240-242`):
*"Antes no había forma de cargarlo desde ninguna app, y el catálogo es de donde salen nombre y calorías
de cada comida de un plan."* O sea que las dos pantallas de alta son más nuevas que el resto del
módulo.

`calorias` acepta `0` a `5000` (`backend/schemas.py:1591`), que es el tipo de tope razonable que pide
el dueño: un plato de 50.000 kcal es un dedo que se resbaló, no un dato.

**Qué escribe y qué lee.** Escribe `Catalogo_Comida` (`:251-253`); lee `Catalogo_Comida` para el
duplicado (`:248`). Coincide con la línea DFD.

**Por qué está hecho así.** Igual que el ejercicio: el nombre es `UNIQUE` en la base
(`db/schema.sql:867`) y el chequeo a mano existe *"para dar un mensaje claro en vez del error de
restricción (mismo criterio que crear_ejercicio)"* (`backend/routers/nutricion.py:244-245`). Y vale el
mismo argumento de fondo: dos filas *"Pollo con arroz"* partirían en dos las calorías de ese plato.

**Nota marcada · cuarta copia del comodín.** `CatalogoComida.nombre.ilike(nombre)`
(`backend/routers/nutricion.py:248`) tiene el mismo agujero que los otros tres: el `_` de `LIKE` es un
comodín. **Corrido:** con `PolloXarroz` cargado, crear `Pollo_arroz` responde 409 *"Ya existe un plato
llamado 'Pollo_arroz'"*. Van cuatro: plan de membresía (B-05), actividad (B-08), ejercicio (B-09) y
plato. Es el mismo arreglo de una línea en cuatro archivos.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| Ya existe ese nombre | 409 | *"Ya existe un plato llamado 'X'."* | `backend/routers/nutricion.py:249-250` |
| Nombre vacío o de más de 120 | 422 | el de Pydantic, en inglés | `backend/schemas.py:1589` |
| Calorías fuera de 0 a 5000 | 422 | el de Pydantic, en inglés | `backend/schemas.py:1591` |
| Sin la acción `gestionDietas` | 403 | el genérico de la acción | `backend/security.py:197-215` |

---

## El catálogo de dietas

### 98. Consultar el catálogo de dietas

`GET /nutricion` · Dueño, Recepcionista, Entrenador, Nutricionista

**Qué resuelve.** Los planes que el gimnasio tiene armados, con cuántos socios sigue cada uno.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Endpoint | `backend/routers/nutricion.py` | 259-283 | `listar_dietas()` |
| Armado | `backend/routers/nutricion.py` | 171-193 | `_a_dieta_out()` |
| Esquema | `backend/schemas.py` | 1605-1628 | `DietaOut` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/nutricionService.ts` | 70-92 | `aPlanListado()`, `listarPlanes()` |
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/nutricion/NutricionView.tsx` | 50-322 | `NutricionView` |
| Tarjeta PWA | `Proyecto - PWA/src/frontend/src/views/nutricion/PlanCard.tsx` | 29-132 | `PlanCard` |
| Vista Flet | `Flet/Proyecto/app/views/nutricion.py` | 59-183 | `build()`, `_plan_card()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 589-607 | `get_planes_nutricion()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 574-575 | `obtener_dietas()` |

**Cómo funciona.** Idéntico al 88: las dietas que no son propias de un socio, las más nuevas primero,
el nutricionista de la sesión una sola vez, y después `_a_dieta_out(d, con_comidas=False)` con
`puede_editar` por fila (`backend/routers/nutricion.py:271-283`).

Lo propio es lo que muestra la tarjeta: acá el dato de cabecera es **las calorías diarias**, y los
chips de filtro son por **objetivo** —el enum `ObjetivoDieta`— y no por un número
(`Proyecto - PWA/src/frontend/src/views/nutricion/NutricionView.tsx:30`). Es la diferencia de dominio
con los días por semana de Rutinas: a un plan se lo busca por para qué sirve.

**Qué escribe y qué lee.** Lee `Dieta` (`:271-276`), `Asignacion_Dieta` (`:191`) y
`Nutricionista → Empleado → Persona` (`:65-68`). No escribe. Coincide con la línea DFD.

**Por qué está hecho así.** Ver [B-09](B-09-rutinas.md#88-consultar-el-catálogo-de-rutinas): el filtro
de la dieta propia es lo que define la lista, porque *"el catálogo es lo que un nutricionista elige para
asignar, y una dieta propia es del socio y de nadie más"* (`backend/routers/nutricion.py:267-269`).

**Qué pasa cuando sale mal.** Sólo 403, para el Profesor y el Socio.

---

### 103. Consultar el detalle de una dieta

`GET /nutricion/{id_dieta}` · Dueño, Recepcionista, Entrenador, Nutricionista

**Qué resuelve.** El plan completo: qué se come cada día y en qué momento.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Endpoint | `backend/routers/nutricion.py` | 286-296 | `obtener_dieta()` |
| Orden de las comidas | `backend/routers/nutricion.py` | 50-60 | `ORDEN_MOMENTOS`, `_clave_orden_comida()` |
| Armado de una comida | `backend/routers/nutricion.py` | 153-168 | `_a_comida_out()` |
| Esquema | `backend/schemas.py` | 1542-1553 | `ComidaOut` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/nutricionService.ts` | 112-128 | `listarComidasDelPlan()` |
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/nutricion/PlanDetailModal.tsx` | 53-201 | `PlanDetailModal` |
| Vista Flet | `Flet/Proyecto/app/views/nutricion.py` | 185-283 | `_open_detail()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 623-638 | `get_comidas_dieta()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 578-579 | `obtener_dieta()` |

**Cómo funciona.** Tres líneas de endpoint y todo el interés en el orden. Las comidas no salen por
`(dia, momento)` alfabético sino por un **diccionario de precedencia**
(`backend/routers/nutricion.py:50-55`):

| | desayuno | media mañana | almuerzo | merienda | media tarde | cena | colación |
|---|---|---|---|---|---|---|---|
| orden | 1 | 2 | 3 | 4 | 5 | 6 | 7 |

Y el comentario que lo precede es de los que explican un problema en una línea: *"Ordenar
alfabéticamente pondría Almuerzo antes que Desayuno, que no es como se come."* Es el mismo tipo de
decisión que el `(dia, orden)` de la planilla de Rutinas —el backend entrega el orden en que se lee— con
la diferencia de que acá el orden **no está en los datos**: `Comida.momento` es texto libre
(`db/schema.sql:908`, y el esquema lo anota como pendiente: *"momento es varchar libre, deberia ser
enum"*), así que hay que mapearlo.

`_clave_orden_comida()` (`:58-60`) normaliza con `strip().lower()` y usa **99** como orden por defecto:
un momento que no esté en la tabla —*"pre-entreno"*, o *"Almuerzo liviano"*— cae al final del día en vez
de romper nada. Es degradación elegante en tres líneas; el precio es que un momento mal tipeado no se
nota, se ordena último.

**Qué escribe y qué lee.** Lee `Dieta` (`:202`), `Comida` y `Catalogo_Comida` (`:159-167`),
`Asignacion_Dieta` (`:191`) y la cadena del nutricionista. No escribe. Coincide con la línea DFD.

**Por qué está hecho así.** Misma división listado/detalle que Rutinas y por el mismo motivo
([la base remota](A-11-rendimiento.md#base-remota)). Lo propio es que acá el detalle cuesta **una
consulta por comida**, porque cada una va a buscar su plato al catálogo: el precio de que el nombre y
las calorías vivan en `Catalogo_Comida` y no en `Comida`, que es la decisión correcta de normalización
con su costo de lectura a la vista.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| No existe ese id | 404 | *"La dieta no existe."* | `backend/routers/nutricion.py:203-204` |
| Es la dieta propia de un socio | 404 | el **mismo** mensaje, a propósito | `:203-204` |
| Sin la sección Nutrición | 403 | el genérico de la sección | `backend/security.py:162-169` |

---

### 99. Crear una dieta del catálogo con sus comidas

`POST /nutricion` · Dueño, Recepcionista, Nutricionista

**Qué resuelve.** Que el nutricionista arme un plan nuevo completo en un solo guardado.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Endpoint | `backend/routers/nutricion.py` | 299-329 | `crear_dieta()` |
| A nombre de quién | `backend/routers/nutricion.py` | 83-114 | `_resolver_nutricionista()` |
| Comidas | `backend/routers/nutricion.py` | 133-150 | `_agregar_comidas()` |
| Esquemas | `backend/schemas.py` | 1520-1540, 1565-1572 | `ComidaCrear`, `DietaCrear` |
| Base | `db/schema.sql` | 904-927 | `Comida` y su `CHECK` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/nutricionService.ts` | 202-224 | `aComidaApi()`, `crearPlan()` |
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/nutricion/PlanFormModal.tsx` | 58-420 | `PlanFormModal` |
| Selector PWA | `Proyecto - PWA/src/frontend/src/services/nutricionService.ts` | 100-108 | `listarNutricionistasActivos()` |
| Vista Flet | `Flet/Proyecto/app/views/nutricion.py` | 285-515 | `_open_form()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1333-1334 | `crear_dieta()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 582-583 | `crear_dieta()` |

**Cómo funciona.** Los mismos cuatro pasos del 89 —resolver el autor, insertar la dieta, `flush` para
tener el id, validar y agregar las comidas, un solo `commit`— en
`backend/routers/nutricion.py:312-329`.

La diferencia está adentro de `_agregar_comidas()` (`:133-150`), que hace dos cosas que su gemelo no.
La primera: valida los platos del catálogo **sólo cuando vienen** (`:139-142`), porque una comida puede
no tener plato. La segunda, en la línea del `INSERT` (`:149`):

```python
descripcion=None if c.id_catalogo_comida is not None else c.descripcion,
```

Si hay plato, la descripción se **descarta**. No es un olvido: con plato, el nombre y la descripción
salen del catálogo, así que guardar también un texto libre sería la segunda fuente de verdad que el
comentario de la base rechaza. Lo que se paga es que el pedido puede traer los dos campos y uno se
pierde **en silencio** — el 422 del esquema sólo exige "al menos uno", no "exactamente uno".

Y el `momento` se normaliza acá, no en el esquema (`:147`): `(c.momento or "").strip() or None`, para
que un momento en blanco quede en `NULL` y no como cadena vacía.

**Qué escribe y qué lee.** Escribe `Dieta` (`:314-322`) y `Comida` (`:143-150`); lee `Nutricionista` y
`Empleado` (`:105-113`), `Catalogo_Comida` al validar (`:140`), y `Asignacion_Dieta` y `Persona` al
armar la respuesta. Coincide con la línea DFD.

**Por qué está hecho así.** Ver [B-09](B-09-rutinas.md#89-crear-una-rutina-del-catálogo-con-sus-ejercicios):
el plan y su contenido se guardan juntos porque es un solo acto humano. Lo que acá se suma es el texto
libre, y la razón vuelve a ser el mostrador y no la base: un plan no puede esperar a que alguien cargue
el catálogo entero.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| Un nutricionista manda el id de otro | 403 | *"No podés crear dietas a nombre de otro nutricionista."* | `backend/routers/nutricion.py:93-96` |
| El Dueño no eligió nutricionista | 400 | *"Elegí el nutricionista que va a quedar a cargo de la dieta."* | `:100-103` |
| El nutricionista no existe | 404 | *"El nutricionista indicado no existe."* | `:106-108` |
| Está dado de baja | 400 | *"Ese nutricionista está dado de baja. Elegí uno activo."* | `:109-113` |
| Un plato no existe | 404 | *"El plato con id N no existe."* | `:140-142` |
| Una comida sin plato ni descripción | 422 | *"Cada comida necesita un plato del catálogo o una descripción."* | `backend/schemas.py:1537-1538` |
| Día fuera de 1 a 7, nombre de más de 100 | 422 | el de Pydantic, en inglés | `backend/schemas.py:1528`, `:1567` |

---

### 104. Editar una dieta y reemplazar sus comidas

`PUT /nutricion/{id_dieta}` · Dueño, Recepcionista, Nutricionista

**Qué resuelve.** Que el nutricionista reacomode el plan y guarde cómo quedó, sin perder lo que el
socio ya registró.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Endpoint | `backend/routers/nutricion.py` | 479-523 | `editar_dieta()` |
| La desvinculación | `backend/routers/nutricion.py` | 506-518 | `RegistroComida`, puesto en `None` |
| Esquema | `backend/schemas.py` | 1575-1584 | `DietaEditarRequest` |
| Base | `db/schema.sql` | 947-970, 1097 | `Registro_Comida` y su clave foránea |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/nutricionService.ts` | 226-245 | `actualizarPlan()` |
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/nutricion/PlanFormModal.tsx` | 58-420 | `PlanFormModal`, en modo edición |
| Vista Flet | `Flet/Proyecto/app/views/nutricion.py` | 285-515 | `_open_form()`, con `es_edicion` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 640-641 | `editar_dieta()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 590-591 | `editar_dieta()` |

**Cómo funciona.** La dieta por `_dieta_del_staff()`, el permiso por `_exigir_editable()`, el
nutricionista sólo si vino y cambió, los cuatro campos propios, y —si vinieron comidas— el bloque de
reemplazo (`backend/routers/nutricion.py:494-518`). Ese bloque es lo único que no es el 94, y está
explicado arriba en [la segunda diferencia](#2-algo-sí-apunta-a-comida--y-el-docstring-dice-que-no):
**desvincular los registros del socio, borrar las comidas, insertar las nuevas**, en ese orden y en la
misma transacción.

El `None` del campo `comidas` distingue los dos pedidos igual que en Rutinas, y el esquema lo declara
nombrando a su gemelo (`backend/schemas.py:1581-1583`): *"None = las comidas no se tocan. Una lista
(aunque sea vacía) REEMPLAZA todas […] Espejo de RutinaEditarRequest.ejercicios."*

**Qué escribe y qué lee.** Escribe `Dieta` (`:499-504`), `Comida` borrando e insertando (`:516`,
`:143-150`) y **`Registro_Comida`**, poniendo `id_comida` en `NULL` (`:514-515`); lee `Dieta` (`:202`),
`Comida` para juntar los ids viejos (`:512`), `Catalogo_Comida` al validar (`:140`), `Nutricionista` y
`Empleado` si cambia el autor, y `Asignacion_Dieta` y `Persona` al responder. **Coincide con la línea
DFD**, que es la única de los diez que declara `-> (Registro_Comida -- id_comida)` como escritura: el
archivo de procesos vio lo que el docstring de la función niega.

**Por qué está hecho así.** La alternativa a desvincular era **no poder editar** un plan que alguien ya
está siguiendo, porque la clave foránea frena el borrado. Entre perder el vínculo y perder la
posibilidad de corregir un plan en uso, se eligió lo primero, y se eligió bien: lo que el socio comió
—el texto y los macros— es el dato valioso, y *"lo que correspondía"* es contexto. Lo que se pagó está
dicho arriba: después de una edición no se puede reconstruir hacia atrás la comparación plan contra
realidad.

El patrón tiene nombre y conviene tenerlo: **desvincular en vez de borrar en cascada**. `ON DELETE
CASCADE` habría borrado los registros del socio —datos suyos, por una edición del plan de otro—; `ON
DELETE SET NULL` haría esto solo, pero ninguna clave foránea de este esquema declara acción al borrar,
así que lo hace el endpoint a mano. Es la misma familia que
[el rol que se apaga](A-10-bajas-logicas.md#el-rol-que-se-apaga): cuando un `DELETE` choca con una
clave foránea, la pregunta es qué significa esa fila para el que la referencia.

**Nota marcada · el docstring dice que nada apunta a `Comida`.** Está desarrollado
[arriba](#2-algo-sí-apunta-a-comida--y-el-docstring-dice-que-no), con las tres corridas. En corto: la
frase se copió de `editar_rutina`, donde es verdad, y contradice a las cuatro líneas que le siguen.

**Nota marcada · el mismo `PUT` que puede borrar en silencio.** `objetivo`, `calorias_diarias` y
`descripcion` tienen default `None` y el endpoint los asigna sin preguntar (`:501-504`), así que un
`PUT` que no los mande los **borra** — y acá uno de ellos es el objetivo calórico contra el que *"Mi
progreso"* compara. Es el mismo defecto que B-09 anotó en el `PUT` de rutina y que ya se arregló en los
de socio y empleado con `model_fields_set`. Hoy inalcanzable: las dos apps mandan los cinco campos
siempre.

**Qué pasa cuando sale mal.** Los del alta, más los dos de la puerta:

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| No existe, o es la dieta propia de un socio | 404 | *"La dieta no existe."* | `backend/routers/nutricion.py:203-204` |
| Es de otro nutricionista | 403 | *"Ese plan es de otro nutricionista: podés verlo, no modificarlo."* | `:127-130` |
| El nutricionista nuevo no existe o está de baja | 404 / 400 | los de `_resolver_nutricionista()` | `:106-113` |
| Un plato no existe | 404 | *"El plato con id N no existe."* | `:140-142` |
| Una comida sin plato ni descripción | 422 | el del esquema, en castellano | `backend/schemas.py:1537-1538` |

---

## Asignarle una dieta a un socio

### 105. Asignar una dieta a un socio y finalizar la que tenía

`POST /nutricion/{id_dieta}/asignar` · Dueño, Recepcionista, Nutricionista

**Qué resuelve.** Que el socio empiece a seguir este plan. Si seguía otro, deja de seguirlo y queda
escrito.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Endpoint | `backend/routers/nutricion.py` | 336-431 | `asignar_dieta()` |
| El 409 de la dieta de baja | `backend/routers/nutricion.py` | 359-371 | la validación del 2026-10-01 |
| Esquemas | `backend/schemas.py` | 1623-1627, 1630-1645 | `AsignarDietaRequest`, `AsignacionDietaOut` |
| Base | `db/schema.sql` | 930-944, 1182-1183 | `Asignacion_Dieta` y `asignacion_dieta_una_activa_uidx` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/nutricionService.ts` | 259-266 | `asignarPlanASocio()` |
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/nutricion/NutricionView.tsx` | 308-316 | `AsignarASocioModal` reusado |
| Vista Flet | `Flet/Proyecto/app/views/nutricion.py` | 517-582 | `_open_asignar()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1336-1338 | `asignar_dieta()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 586-587 | `asignar_dieta()` |

**Cómo funciona.** Los cinco pasos del 95, con el 409 de la dieta de baja en segundo lugar
(`backend/routers/nutricion.py:354-417`). El docstring remite a su gemelo en la primera línea del
párrafo (`:347-349`): *"Igual que con las rutinas: si ya tenía una ACTIVA se la finaliza en vez de
rechazar el pedido."*

Dos cosas propias, las dos chicas:

- **`observaciones`**. `Asignacion_Dieta` tiene una columna que `Asignacion_Rutina` no tiene
  (`db/schema.sql:937`), y el endpoint la guarda (`:415`). Es texto libre sobre **esta asignación** —no
  sobre el plan— y el comentario de la tabla la nombra entre los atributos propios que justifican que
  la asociativa esté historizada (`db/schema.sql:940-944`). **Ninguna de las dos apps la manda**: la
  PWA envía sólo `id_socio` (`Proyecto - PWA/src/frontend/src/services/nutricionService.ts:264`) y Flet
  lo mismo (`Flet/Proyecto/app/api_client.py:587`). Viaja en la respuesta y sale por la API.
- **El modal de asignar es el mismo que el de Rutinas.** `AsignarASocioModal` (`:308-316`) lo comparten
  las dos secciones, y Flet tiene su propio `_open_asignar()` en cada vista, con el comentario que lo
  declara gemelo (`Flet/Proyecto/app/views/nutricion.py:509-510`). Un componente de más en la PWA, dos
  copias en Flet: el mismo desbalance que
  [A-03](A-03-dos-apps-un-backend.md#aplicación-gemela-y-componente-gemelo) describe.

**Qué escribe y qué lee.** Escribe `Asignacion_Dieta` dos veces —el `UPDATE` de la anterior (`:391-392`)
y el `INSERT` de la nueva (`:408-417`)—; lee `Dieta` (`:202`), `Socio` (`:373`), `Asignacion_Dieta`
(`:379-384`), `Persona` (`:389`, `:424`), y `Empleado` y `Nutricionista` por `_exigir_editable()`
(`:72-80`). Coincide con la línea DFD.

**Por qué está hecho así.** Ver [B-09](B-09-rutinas.md#95-asignar-una-rutina-a-un-socio-y-finalizar-la-que-tenía):
la regla de negocio —*"Nadie sigue dos planes alimentarios a la vez"* (`:348`)— está defendida en el
endpoint y en el [índice único parcial](A0-08-sql-indices-y-planes.md#índice-único-parcial), y las dos
hacen falta por motivos distintos.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| No existe, o es la dieta propia de un socio | 404 | *"La dieta no existe."* | `backend/routers/nutricion.py:203-204` |
| Es de otro nutricionista | 403 | *"Ese plan es de otro nutricionista: podés verlo, no modificarlo."* | `:127-130` |
| El plan está dado de baja | 409 | *"Ese plan está dado de baja: reactivalo antes de asignarlo."* | `:367-371` |
| El socio no existe | 404 | *"El socio no existe."* | `:374-375` |
| Ya tiene asignada esa misma dieta | 409 | *"NOMBRE ya tiene asignada esa dieta."* | `:386-390` |

---

### 100. Consultar el historial de dietas de un socio

`GET /nutricion/asignaciones/socio/{id_socio}` · Dueño, Recepcionista, Entrenador, Nutricionista

**Qué resuelve.** Qué planes le asignó el personal a este socio, el actual primero.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Endpoint | `backend/routers/nutricion.py` | 434-472 | `dietas_de_socio()` |
| Esquema | `backend/schemas.py` | 1630-1645 | `AsignacionDietaOut` |
| Base | `db/schema.sql` | 930-944, 1179 | `Asignacion_Dieta` y su índice `(id_socio, estado)` |
| Service PWA | — (no existe) | | ninguna pantalla lo llama |
| Vista Flet | — (no existe) | | ninguna pantalla lo llama |

**Cómo funciona.** Idéntico al 90, con el `JOIN` para el filtro de la dieta propia y el orden por
`fecha_inicio` descendente (`backend/routers/nutricion.py:451-458`). El docstring repite la frontera del
portal en los mismos términos (`:443-446`): el socio va por `mi-dieta`, *"que filtra por el id_socio
firmado en su token en vez de aceptar uno por parámetro"*.

**Qué escribe y qué lee.** Lee `Asignacion_Dieta` y `Dieta` (`:451-458`), y `Socio` y `Persona` para el
nombre (`:463`). No escribe. Coincide con la línea DFD.

**Por qué está hecho así.** Nada propio: es el 90 con otros nombres.

**Nota marcada · ningún cliente lo llama, igual que su gemelo.** No hay función en `nutricionService.ts`
ni en `api_client.py` que pida esta ruta. Van **cuatro** endpoints de esta forma —el historial de
ingresos de [B-06](B-06-asistencia.md#con-qué-se-conecta), los socios de un entrenador de
[B-02](B-02-socios.md#con-qué-se-conecta), el historial de rutinas de
[B-09](B-09-rutinas.md#90-consultar-el-historial-de-rutinas-de-un-socio) y éste—, y los cuatro
contestan preguntas de **la ficha del socio**: qué viene haciendo. Juntos son una pantalla que no está.

**Qué pasa cuando sale mal.** Un socio inexistente devuelve **lista vacía**, no 404. Y 403 para el
Profesor y el Socio.

---

## Sacar una dieta de circulación

### 106. Dar de baja una dieta del catálogo · 107. Reactivar una dieta del catálogo

`POST /nutricion/{id_dieta}/baja` y `POST /nutricion/{id_dieta}/reactivar` · Dueño, Recepcionista,
Nutricionista

**Qué resuelve.** Que un plan deje de ofrecerse para asignar, sin cortárselo a quien lo está siguiendo.
Y que vuelva.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Endpoints | `backend/routers/nutricion.py` | 526-564 | `dar_de_baja_dieta()`, `reactivar_dieta()` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/nutricionService.ts` | 247-257 | `darDeBajaPlan()`, `activarPlan()` |
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/nutricion/NutricionView.tsx` | 120-152 | `pedirBaja()`, `activar()` |
| Tarjeta PWA | `Proyecto - PWA/src/frontend/src/views/nutricion/PlanCard.tsx` | 29-132 | `PlanCard` |
| Vista Flet | `Flet/Proyecto/app/views/nutricion.py` | 629-648 | `_cambiar_estado()`, `_aplicar()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 643-648 | `baja_dieta()`, `reactivar_dieta()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 606-611 | `baja_dieta()`, `reactivar_dieta()` |

**Cómo funciona.** El mismo endpoint dos veces con el booleano al revés
(`backend/routers/nutricion.py:537-546` y `:555-564`): la puerta, el permiso, que el estado cambie de
verdad, y una asignación.

**Qué escribe y qué lee.** Escribe `Dieta.activo` (`:543`, `:561`); lee todo lo que hace falta para
armar la respuesta completa. Coincide con la línea DFD.

**Por qué está hecho así.** [Baja lógica](A-10-bajas-logicas.md#baja-lógica-soft-delete) con los dos
mismos argumentos del 96: la fila es destino de claves foráneas sin acción al borrar
(`db/schema.sql:1095`), y los socios que lo siguen lo terminan
(`backend/routers/nutricion.py:533-535`). Y desde el 2026-10-01, además, **la baja hace lo que promete**:
el 409 del proceso 105 es el que lo garantiza, y las dos pantallas esconden el botón.

El texto de la confirmación es el de su gemelo con el vocabulario del módulo: *"El plan deja de figurar
como activo. Los socios que lo siguen lo terminan."*
(`Proyecto - PWA/src/frontend/src/views/nutricion/NutricionView.tsx:126`). Y la asimetría también:
dar de baja pregunta, reactivar no.

**Nota marcada · los títulos 106 y 107 del archivo de procesos.** Igual que 96 y 97, están encabezados
con su propia ruta en vez de con un nombre; el nombre está adentro de la línea DFD (*"Dar de baja una
dieta del catalogo"*, *"Reactivar una dieta del catalogo"*) y es el que usa este capítulo. Son los
cuatro únicos casos de los 173.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| No existe, o es la dieta propia de un socio | 404 | *"La dieta no existe."* | `backend/routers/nutricion.py:203-204` |
| Es de otro nutricionista | 403 | *"Ese plan es de otro nutricionista…"* | `:127-130` |
| Ya estaba desactivada | 400 | *"Esa dieta ya estaba desactivada."* | `:539-541` |
| Ya estaba activa | 400 | *"Esa dieta ya estaba activa."* | `:557-559` |

---

## Con qué se conecta

- **Es la misma idea que…**
  [aplicación gemela y componente gemelo](A-03-dos-apps-un-backend.md#aplicación-gemela-y-componente-gemelo):
  Nutrición y Rutinas son el mismo código dos veces, y eso duplica tanto el acierto —el índice parcial,
  el 404 de lo propio— como el defecto: el comodín del `ilike`, el `PUT` que borra en silencio y la baja
  que no impedía asignar aparecieron los dos en los dos.
- **Existe por culpa de…**
  [clave foránea y acción referencial](A0-07-bases-de-datos-relacionales.md#clave-foránea-y-acción-referencial):
  el `PUT` desvincula los registros del socio antes de borrar las comidas porque `Registro_Comida`
  apunta a `Comida` y ninguna clave foránea de este esquema declara acción al borrar.
- **Se contradice con…** [estado derivado](A-09-estados-derivados.md#estado-derivado):
  `Dieta.calorias_diarias` se guarda **a propósito** aunque parezca derivable, porque el objetivo del
  nutricionista y la suma de los platos son dos hechos distintos y la distancia entre los dos es
  información.
- **Es el mismo problema que…** [N+1](A0-09-el-orm.md#n1): los tres listados cuestan lo mismo que los de
  Rutinas, y el detalle de un plan agrega una consulta por comida para traerle el plato.
- **Es la misma idea que…** [baja lógica](A-10-bajas-logicas.md#baja-lógica-soft-delete): el plan se
  apaga, corta el futuro y no toca a quien lo sigue — y desde el 2026-10-01 eso lo hace cumplir un 409,
  no sólo un chip.
- **Es la misma idea que…** [aislamiento de lo propio](A-08-autorizacion.md#aislamiento-de-lo-propio):
  la dieta propia del socio responde el mismo 404 que una inexistente, en los cinco endpoints que pasan
  por `_dieta_del_staff()`.
