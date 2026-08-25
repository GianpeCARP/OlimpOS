# OlimpOS — Masterclass de programación

**Todo lo que hay que entender para defender este sistema, explicado desde adentro.**

---

Este archivo es el hermano de `OlimpOS-masterclass-modelo-de-datos.md`. Aquel
explica **la base**; éste explica **el código que la usa**: el backend FastAPI,
la PWA de React y la app de escritorio de Flet.

No es un manual de referencia ni un tutorial de FastAPI. Es una **explicación
del sistema que ya existe**, con la lógica invertida respecto de un tutorial
normal:

> Un tutorial dice *"así se hace un login con JWT"*.
> Esto dice *"éste es el problema que existe cuando alguien cierra el navegador
> y vuelve mañana; mirá las cuatro soluciones posibles, por qué las otras tres
> fallan, y en qué línea exacta de OlimpOS está la que se eligió"*.

Cada concepto se presenta en cuatro pasos, siempre en el mismo orden:

| Paso | Pregunta que responde |
|---|---|
| **El problema** | ¿Qué se rompe si esto no existe? |
| **La idea** | ¿Cuál es el mecanismo, en abstracto? |
| **En OlimpOS** | ¿En qué archivo y qué línea vive? |
| **La pregunta de examen** | ¿Cómo lo defendés en 30 segundos? |

Las referencias a archivos son de la forma `archivo.py:123`. **Todas fueron
verificadas contra el código el 25 de agosto de 2026.** Si alguna no coincide,
el código cambió después — abrí el archivo, no confíes en el número.

> ### Antes de empezar: la Parte 0
>
> El resto del archivo usa unos treinta términos —*trigger*, *middleware*,
> *endpoint*, *transacción*, *hook*, *DOM*— **sin frenar a definirlos**. La
> **[Parte 0](#parte-0--los-ladrillos)** los explica todos, agrupados y con la
> misma pregunta de siempre: *¿qué problema existía antes de que esto
> existiera?*
>
> No hace falta leerla entera. Si te cruzás una palabra que te suena pero no
> podrías explicar, está ahí.

---

## Cómo está construido el sistema, en una página

Antes de cualquier concepto, el mapa. Tres programas que se hablan por HTTP:

```
   ┌─────────────────────────┐        ┌──────────────────────────┐
   │   PWA  (el socio)       │        │   Flet  (el personal)    │
   │   React + TypeScript    │        │   Python de escritorio   │
   │   corre en el NAVEGADOR │        │   corre como PROGRAMA    │
   └───────────┬─────────────┘        └────────────┬─────────────┘
               │                                   │
       cookie httpOnly                  Authorization: Bearer
       + header X-CSRF-Token            + X-Client-Type: escritorio
               │                                   │
               └─────────────┬─────────────────────┘
                             │  HTTP / JSON
                  ┌──────────▼───────────┐
                  │   BACKEND FastAPI    │   15 routers
                  │   main.py            │   138 endpoints
                  │                      │
                  │   middleware CSRF    │   ← rechaza antes de tocar nada
                  │   dependencias       │   ← 401 / 403
                  │   routers            │   ← reglas de negocio
                  │   SQLAlchemy (ORM)   │   ← traduce a SQL
                  └──────────┬───────────┘
                             │  TCP + TLS   (44 ms de ida y vuelta)
                  ┌──────────▼───────────┐
                  │  PostgreSQL en Neon  │   37 tablas
                  │  sa-east-1 São Paulo │   7 triggers, 67 FKs
                  └──────────────────────┘
```

Los números, contados sobre el código (no estimados):

| | |
|---|---|
| Endpoints | **138** en 15 routers |
| Verbos | 64 POST, 61 GET, 10 PUT, 3 DELETE |
| Tablas | **37** en `schema.sql`, 37 en `models.py`, 37 en Neon |
| Migraciones | **9** |
| Servicios de la PWA | 14 · **52** componentes de vista |
| Vistas de Flet | **11** (10 secciones + login) |
| Copias de la matriz de permisos | **3**, verificadas por un script |

---

# PARTE 0 — Los ladrillos

**Leé esto primero si alguna palabra de las que siguen te suena pero no la
podrías explicar.**

Todo lo que viene después está construido sobre unos treinta términos que el
resto del archivo usa sin frenar a definirlos. Acá están definidos, en el mismo
orden en que aparecen en un pedido real, y cada uno con la misma pregunta:
**¿qué problema existía antes de que esto existiera?**

No hace falta leerla de corrido. Si ya sabés qué es un endpoint, saltá a la
Parte I y volvé cuando algo no cierre.

---

## 0.1 · Las palabras de la web

### Cliente y servidor

Dos programas que se hablan por la red. El **cliente** pide; el **servidor**
contesta. En OlimpOS hay dos clientes (la PWA y Flet) y un servidor (el backend).

Lo importante no es la definición sino la asimetría: **el cliente corre en la
máquina de otro**. El servidor corre en la tuya.

### HTTP, pedido y respuesta

**HTTP** es el idioma en que se hablan. Cada conversación tiene exactamente dos
turnos:

```
  PEDIDO  (lo manda el cliente)          RESPUESTA (la manda el servidor)
  ─────────────────────────────          ────────────────────────────────
  POST /socios/7/baja                    409 Conflict
  Authorization: Bearer eyJ…             Content-Type: application/json
  X-CSRF-Token: k3f9…
                                         {"detail": "Ese socio ya está
  {"motivo": "se mudó"}                    dado de baja."}
```

Cuatro partes en cada uno:

| Parte | En el pedido | En la respuesta |
|---|---|---|
| **Verbo** | `POST` — qué quiere hacer | — |
| **Ruta** | `/socios/7/baja` — sobre qué | — |
| **Código** | — | `409` — cómo salió |
| **Headers** | metadatos: quién soy, qué formato | metadatos: qué formato, cookies |
| **Cuerpo** *(body)* | los datos que manda | los datos que devuelve |

> **HTTP no tiene memoria.** Cada pedido llega solo, sin ninguna relación con el
> anterior. El servidor no "recuerda" que hace dos segundos te logueaste. Ese
> problema —y no otro— es el que resuelven las cookies y los JWT.

### Endpoint

**Una combinación concreta de verbo + ruta que la API sabe contestar.**
`GET /socios` es un endpoint. `POST /socios` es **otro** endpoint distinto,
aunque la ruta sea la misma.

En OlimpOS hay **138**. Cada uno es una función de Python con un decorador arriba:

```python
@router.get("/socios")          # ← esto declara el endpoint
def listar(...):                # ← esto es lo que hace
    ...
```

### Decorador

Esa línea con `@` que va **arriba** de una función en Python. No es un
comentario: es código que **envuelve** la función y le agrega comportamiento sin
tocar su cuerpo.

`@router.get("/socios")` no cambia lo que hace `listar()`. Lo que hace es
**anotarla en el registro de rutas** para que FastAPI sepa que esa función es la
que atiende `GET /socios`.

Analogía: es el cartelito que le colgás a una puerta. La puerta sigue siendo la
misma; lo que cambia es que ahora la gente sabe cuál es.

### Header

Un par `Nombre: valor` que viaja junto al pedido, **aparte del cuerpo**. Son los
metadatos: quién sos, qué formato mandás, qué idioma preferís.

Los tres que importan en OlimpOS:

| Header | Quién lo manda | Para qué |
|---|---|---|
| `Authorization: Bearer …` | Flet | Lleva el token de sesión |
| `X-CSRF-Token: …` | La PWA | Prueba que el pedido lo originó ella |
| `X-Client-Type: escritorio` | Flet | Declara que **no** es un navegador |

Los que empiezan con `X-` son inventados por la aplicación; el resto son
estándar.

### Cookie

Un pedacito de texto que **el servidor le pide al navegador que guarde**, y que
el navegador **devuelve solo, automáticamente, en todo pedido a ese dominio**.

Esa palabra —**solo**— es todo. El navegador la manda sin que nadie se lo pida y
sin importar quién originó el pedido. Es lo que hace cómoda la sesión, y es
exactamente lo que habilita el ataque CSRF de la §15.

Una cookie puede tener banderas que cambian su comportamiento:

| Bandera | Qué hace |
|---|---|
| `httpOnly` | JavaScript **no puede leerla**. Sólo viaja al servidor. |
| `Secure` | El navegador la manda **sólo por HTTPS**. |
| `SameSite=lax` | No la manda en POST originados por **otro sitio**. |
| `max-age` | Cuántos segundos vive. |

### Origen

La terna **esquema + host + puerto**. `http://localhost:5173` y
`http://127.0.0.1:8000` son **orígenes distintos** — cambia el host y el puerto,
aunque las dos sean tu misma máquina.

Es la unidad con la que el navegador decide qué le permite a una página hacerle
a otra. De ahí salen CORS (§16) y la **política de mismo origen**, que es la
regla de que una página **no puede leer** datos de otro origen.

### JSON

El formato en que viajan los datos. Es texto plano con una estructura:

```json
{"id_socio": 7, "nombre": "Ana", "activo": true, "telefonos": ["11-4444"]}
```

Ganó porque lo entienden todos los lenguajes y **se lee a ojo**.

### Base64

**No es cifrado.** Es una forma de escribir bytes usando sólo letras, números y
un par de símbolos, para que sobrevivan a un medio que espera texto.

Cualquiera lo revierte, sin clave y en un segundo. Por eso importa saber que
**las dos primeras partes de un JWT son Base64**: quien tenga el token puede
leer su contenido.

### API

*Application Programming Interface*: el conjunto de endpoints que un programa
expone para que otros programas lo usen. Cuando decimos "la API de OlimpOS", son
esos 138 endpoints tomados como un todo.

### Socket, TLS, handshake y RTT

Cuatro palabras de la capa de abajo que aparecen en la parte de rendimiento:

- **Socket**: el canal abierto entre dos programas por la red. Mientras un
  pedido viaja, el proceso está *"esperando el socket"* — no calculando.
- **TLS**: el cifrado de la conexión. Es la `s` de HTTPS.
- **Handshake**: el saludo inicial para abrir esa conexión cifrada — acordar
  claves, verificar certificados. **Es caro**: en OlimpOS cuesta 825 ms.
- **RTT** *(round-trip time)*: cuánto tarda algo en ir y volver. Contra Neon en
  São Paulo son **44 ms**, y es un piso físico.

> La diferencia entre esos dos números —44 ms contra 825 ms, 19 veces— es la que
> explica **todo** el trabajo de rendimiento de la Parte VIII.

---

## 0.2 · Las palabras de la base de datos

### Tabla, fila, columna

Una **tabla** es una planilla. Cada **fila** es una cosa (un socio, un pago);
cada **columna** es un dato de esa cosa (el DNI, el monto). OlimpOS tiene **37**
tablas.

### Clave primaria (PK)

La columna que identifica a cada fila **de forma única**. `Persona.id_persona`
es la PK de `Persona`: no hay dos personas con el mismo.

En OlimpOS son números que asigna la base sola, y hay una decisión detrás: la PK
de `Persona` es `id_persona` y **no el DNI**, aunque el DNI también sea único.
Motivo: un DNI mal tipeado se corrige con un `UPDATE` de una columna, y no
arrastrando el cambio por las diez tablas que lo referenciaban.

### Clave foránea (FK, *foreign key*)

Una columna que **apunta a la clave primaria de otra tabla**.
`Membresia.id_socio` guarda el id de un socio, y la base **garantiza** que ese
socio existe: si intentás insertar una membresía apuntando a un socio inexistente,
la rechaza.

Eso se llama **integridad referencial**, y es una de las razones principales de
usar una base de datos y no archivos. OlimpOS tiene **67** foreign keys.

### Índice

**El índice del final de un libro.** Sin él, buscar "Perazzo" significa leer todas
las páginas. Con él, vas directo.

Una base sin índice hace lo mismo: recorre la tabla entera. Con índice, salta.

El precio es doble: ocupa espacio y **cada escritura tiene que actualizarlo**.
Por eso no se indexa todo, sólo lo que se busca seguido.

Dos variantes que aparecen en OlimpOS:

- **Índice ÚNICO**: además de acelerar, **prohíbe duplicados**. `Usuario.username`
  es único, así que la base impide dos cuentas con el mismo nombre.
- **Índice único PARCIAL**: único **sólo donde se cumple una condición**. La
  migración 009 creó uno que impide dos rutinas `ACTIVA` del mismo socio —
  pero deja tener veinte finalizadas. La regla no es "una rutina por socio", es
  "una **activa** por socio", y el índice dice exactamente eso.

### Constraint (restricción)

**Una regla declarada en la tabla, que la base hace cumplir en toda escritura,
venga de donde venga.**

Las cuatro más comunes:

| Constraint | Qué exige |
|---|---|
| `NOT NULL` | La columna no puede quedar vacía |
| `UNIQUE` | No puede repetirse el valor |
| `CHECK` | Una condición: `monto > 0`, `fecha_fin >= fecha_inicio` |
| `FOREIGN KEY` | Lo apuntado tiene que existir |

Lo clave: **es declarativa**. Vos decís *qué* tiene que cumplirse, no *cómo*
verificarlo. La base se encarga.

### Trigger

> Ésta es la que más aparece en el archivo y la que más conviene entender bien.

**Un trigger es un pedazo de código que la base ejecuta sola, automáticamente,
cuando le pasa algo a una tabla.** Nadie lo llama. Se dispara.

De ahí el nombre: *trigger* es **gatillo**. Vos definís el gatillo una vez y
después *"cada vez que alguien inserte una fila en `Reserva`, corré esto"*.

**Analogía:** un detector de humo cableado al edificio. No importa quién prendió
el fósforo, ni si leyó el reglamento, ni si entró por la puerta o por la ventana.
Suena igual.

**El problema que resuelve.** Una regla que vive en el código de la aplicación
sólo se cumple si pasás por la aplicación. Alguien que escribe SQL directo en el
panel de Neon **se la saltea entera**. Y eso no es hipotético: en OlimpOS se
comprobó insertando **5 reservas en un turno de cupo 2**, y la base las aceptó
todas sin decir nada.

El trigger cierra ese agujero, porque vive del otro lado.

**Trigger vs constraint** —se parecen y no son lo mismo:

| | Constraint | Trigger |
|---|---|---|
| Cómo se escribe | Declarativo: *qué* debe cumplirse | Procedural: **código** que decide |
| Alcance | Mira la fila, o una referencia | Puede **consultar otras tablas** |
| Ejemplo | `monto > 0` | *"contá las reservas de este turno y compará con su cupo"* |

Se usa un trigger cuando la regla **necesita mirar otras filas**. "El monto tiene
que ser positivo" es un CHECK. "No puede haber más reservas que el cupo del
turno" necesita contar filas de una tabla y leer una columna de otra: eso un
CHECK no lo puede hacer.

**Cuándo se dispara.** Ahí está el matiz que el archivo usa varias veces:

- Un trigger **normal** corre **inmediatamente**, fila por fila.
- Un `CONSTRAINT TRIGGER ... DEFERRABLE INITIALLY DEFERRED` corre **recién al
  confirmar la transacción**.

¿Por qué querrías esperar hasta el final? Por un caso real: la lista de espera
**cancela a uno y promueve a otro en la misma operación**. Si el trigger corriera
al instante, vería el estado intermedio —donde por un microsegundo hay uno de
más— y rechazaría una operación **que termina siendo perfectamente válida**.
Diferirlo al final hace que sólo importe el resultado.

**Dónde están.** OlimpOS tiene **7** constraint triggers en `schema.sql`. Los dos
del cupo vinieron de la migración 006.

**Y el límite honesto**, que está escrito en la propia migración: el trigger
**no** resuelve dos personas reservando el último lugar al mismo tiempo, porque
él también cuenta, y también contaría 19 en las dos transacciones. Eso lo tapa un
bloqueo de fila desde el backend. Cada uno cubre lo que el otro no.

### Transacción

**Un bloque de operaciones que pasan todas o no pasa ninguna.**

Analogía: una transferencia bancaria. Descontar de una cuenta y sumar a la otra
son dos operaciones, pero **no puede ocurrir sólo la primera**. O las dos, o
ninguna.

Dos verbos la cierran:

- **`commit`** — confirmalo todo. A partir de acá es permanente y los demás lo ven.
- **`rollback`** — deshacé todo. Como si no hubiera pasado nada.

Eso es lo que permite que un endpoint que falla a la mitad no deje la base en un
estado inconsistente: se hace rollback y no queda rastro.

Y `flush`, que aparece bastante en el archivo, es un tercer verbo intermedio:
**mandá el SQL a la base pero todavía no confirmes**. Sirve cuando necesitás el
id que la base acaba de generar, o cuando importa el **orden** en que se escriben
las cosas.

### Snapshot y niveles de aislamiento

Si dos transacciones corren al mismo tiempo, ¿qué ve cada una de lo que hace la
otra?

Un **snapshot** es la "foto" de la base que una transacción está viendo.
PostgreSQL, por defecto, le da a **cada sentencia** una foto de lo confirmado
hasta ese momento. Eso se llama **READ COMMITTED**.

La consecuencia práctica —y es la que produce la condición de carrera de la §30—
es que **una transacción nunca ve lo que otra todavía no confirmó**. Las dos
cuentan 19 lugares ocupados, y las dos entran.

### DDL y esquema

El **esquema** es la estructura de la base: qué tablas hay, qué columnas, qué
reglas. El **DDL** (*Data Definition Language*) es el SQL que la define:
`CREATE TABLE`, `ALTER TABLE`, `CREATE INDEX`.

En OlimpOS ese DDL vive en `Proyecto/db/schema.sql` y es **la única fuente de
verdad** de la estructura.

### Migración

Un archivo con los cambios necesarios para llevar una base **que ya tiene datos**
de una versión del esquema a la siguiente.

Hace falta porque no se puede volver a correr `schema.sql` sobre una base cargada:
un `CREATE TABLE` de algo que ya existe falla, y uno que no fallara sería peor —
borraría todo para recrearlo.

OlimpOS tiene **9**, numeradas. La 006 es la de los triggers de cupo.

### ORM

*Object-Relational Mapper*. Traduce entre **filas de SQL** y **objetos del
lenguaje**. En vez de escribir SQL a mano y armar objetos, escribís
`db.query(Socio).filter(...)` y él genera el SQL.

Lo que ganás: seguridad contra inyección SQL, menos código repetido.
Lo que perdés: **visibilidad** — una línea de Python puede disparar 45 consultas
sin que se note. Ése es el problema N+1 de la §28.

En OlimpOS el ORM es **SQLAlchemy**.

### Carga perezosa (*lazy loading*)

Cuando el ORM trae un socio, **no** trae automáticamente sus pagos, ni su persona,
ni sus membresías. Los trae **recién si los pedís**, con una consulta nueva en ese
momento.

Es cómodo y es exactamente lo que causa el N+1: pedirlos dentro de un bucle
significa una consulta por vuelta.

---

## 0.3 · Las palabras del backend

### Framework

Una biblioteca que además **impone una forma de estructurar el programa**. Vos
escribís las piezas; él decide cuándo llamarlas.

En OlimpOS el framework del backend es **FastAPI**.

### Router

Un archivo que agrupa endpoints relacionados. `routers/cobros.py` tiene los 8
endpoints de cobros; `routers/socios.py`, los 10 de socios. Son **15** routers.

Es organización, no magia: sin ellos, los 138 endpoints estarían en un solo
archivo.

### Middleware

**Código que se ejecuta entre que el pedido llega y el endpoint corre, y que ve
TODOS los pedidos.**

**Analogía:** el control de seguridad de un aeropuerto. Todo el mundo pasa por
ahí, antes de llegar a cualquier puerta de embarque. No hay forma de llegar a la
puerta sin haber pasado.

Puede dejar pasar el pedido, modificarlo, o cortarlo ahí mismo con una respuesta.

En OlimpOS hay dos: el de **CORS** y el de **CSRF**. Y que el de CSRF sea
middleware —y no algo que cada endpoint tenga que pedir— es una decisión
explícita: *"una dependencia hay que acordarse de ponerla en cada endpoint nuevo,
y el día que alguien se olvide, ese endpoint queda abierto sin que nada avise"*.

### Dependencia (en FastAPI)

Una función que FastAPI **ejecuta antes** del endpoint, y cuyo resultado le pasa
como parámetro. Si la dependencia lanza un error, **el cuerpo del endpoint nunca
corre**.

Se declara en la firma:

```python
def listar(sesion: Sesion = Depends(requiere_seccion(Seccion.SOCIOS))):
```

Eso se lee: *"para entrar acá hace falta una sesión con acceso a SOCIOS"*. Y
como está en la firma y no adentro, **no se puede olvidar de chequear a mitad de
camino**.

Es lo que hace que los permisos de OlimpOS sean difíciles de romper por descuido.

### Schema de validación

Un molde que describe **la forma exacta** de lo que entra o sale de un endpoint:
qué campos, de qué tipo, con qué rangos. Si el pedido no encaja, se rechaza
**antes** de ejecutar una línea del endpoint.

En OlimpOS los escribe **Pydantic**, y viven en `schemas.py`. Son distintos de
los modelos del ORM a propósito — la §25 explica por qué, y el motivo es de
seguridad.

### Hilo (*thread*)

Una línea de ejecución dentro de un mismo programa. Varios hilos avanzan "a la
vez" dentro del mismo proceso, compartiendo la memoria.

Sirven cuando hay que **esperar varias cosas al mismo tiempo** — por ejemplo,
doce pedidos de red. Ahí no compiten: todos están esperando.

Un **hilo daemon** es uno que **no impide que el programa termine**. Sin esa
marca, cerrar el backend se colgaría esperando a un hilo que nunca termina.

### Candado (*lock*)

Cuando varios hilos tocan la misma variable, hace falta un turno. Un candado
garantiza que **sólo uno por vez** entra a ese pedazo de código.

Sin él, un hilo podría estar leyendo una lista mientras otro la vacía.

### Event loop, async y await

Otra forma de hacer varias cosas a la vez, sin hilos: **un solo hilo que va
alternando** entre tareas cada vez que una se pone a esperar.

Ese despachador es el **event loop**. `async def` marca una función que sabe
pausarse, y `await` es el punto donde dice *"acá espero, atendé a otro mientras
tanto"*.

La trampa: si una función `async` hace algo que bloquea **sin avisar**, congela
el loop entero y nadie más es atendido. Por eso en OlimpOS casi todos los
endpoints son `def` normales —SQLAlchemy es síncrono— y FastAPI los corre en
hilos aparte.

### El GIL

*Global Interpreter Lock*: un candado interno de Python que permite que **un solo
hilo ejecute código Python a la vez**.

De ahí sale la creencia de que "los hilos en Python no sirven". Es cierto **sólo
para trabajo de cálculo**. Cuando un hilo se pone a esperar la red, **libera el
GIL** — así que para esperar doce respuestas al mismo tiempo, los hilos funcionan
perfecto.

OlimpOS es enteramente de espera, no de cálculo. Por eso el GIL no molesta.

### Pool de conexiones

Abrir una conexión a la base cuesta **825 ms**. Abrirla y cerrarla en cada pedido
sería insostenible.

Un **pool** es un conjunto de conexiones **ya abiertas** que se prestan y se
devuelven. El pedido toma una, la usa, la devuelve. El handshake se paga una vez.

### Caché

Guardar una respuesta ya calculada para no volver a pedirla.

La parte fácil es guardar. La difícil es **invalidar**: decidir cuándo lo
guardado dejó de ser cierto. La §33 cuenta las dos estrategias que se probaron.

### Idempotente

Una operación es **idempotente** si aplicarla varias veces da el mismo resultado
que aplicarla una.

`x = 5` lo es. `x = x + 5` no. "Marcar el pago 123 como confirmado" lo es;
"sumarle un mes a la membresía" **no** — y por eso el webhook de Mercado Pago
necesita protección: reintenta por diseño, y sin guard cobraría dos veces.

---

## 0.4 · Las palabras del frontend

### DOM

*Document Object Model*: el **árbol de objetos** que el navegador construye a
partir del HTML, y que es lo que efectivamente está en pantalla.

La distinción que importa: el archivo `.html` es el **plano**; el DOM es **el
edificio**. JavaScript no modifica el archivo — modifica el DOM, y por eso los
cambios se ven al instante sin recargar.

### Componente

Un pedazo de interfaz reutilizable, con su propio HTML y su propia lógica: un
botón, una tarjeta de socio, una pantalla entera. La PWA tiene **52** archivos de
vista.

### Render

El acto de **calcular cómo se ve** un componente para un estado dado. React
vuelve a renderizar cuando el estado cambia, y aplica al DOM sólo la diferencia.

La idea de fondo, que da vuelta la forma tradicional de programar interfaces:

```
    UI = f(estado)
```

En vez de *"cuando pase X, cambiá el elemento Y"*, se declara **cómo se ve todo
para un estado dado**. Nadie toca el DOM a mano.

### Estado

Los datos que, al cambiar, hacen que la pantalla se redibuje. El texto de un
buscador, la lista de socios cargada, si un modal está abierto.

### Hook

En React, una función que empieza con `use` y le da a un componente una capacidad
que por sí solo no tendría:

| Hook | Qué le da |
|---|---|
| `useState` | **Memoria**: un valor que sobrevive entre renders |
| `useEffect` | **Efectos**: correr algo cuando el componente aparece o cambia algo |
| `useMemo` | **Caché**: no recalcular algo caro en cada render |

`useEffect` es donde se piden los datos a la API, y tiene un **array de
dependencias**: la lista de valores que, al cambiar, hacen que vuelva a correr.
Ese array **se evalúa durante el render**, y ahí está el bug de la §36.

### Store

Estado **global**, fuera del árbol de componentes, para lo que necesitan muchas
pantallas lejanas entre sí. En OlimpOS la sesión vive en un store
(`authStore.ts`); el texto de un buscador, no.

### SPA

*Single Page Application*: el navegador carga **una** página y después reescribe
su contenido con JavaScript. La URL cambia sin recargar.

Se gana velocidad de transición; se pierde todo lo que el navegador hacía solo, y
hay que reimplementarlo — incluyendo qué mostrar cuando alguien aprieta F5.

### Bundle y build

El código fuente son cientos de archivos. El **build** los junta, traduce el
TypeScript a JavaScript, y produce unos pocos archivos optimizados: el **bundle**.

Eso es lo que baja el navegador. Y de ahí sale una regla dura: **todo lo que
entra al bundle es público**. Nunca va un secreto ahí.

### Service worker

Un script que el navegador corre **aparte de la página**, entre ella y la red.
Puede interceptar pedidos y contestarlos desde su propio caché — que es lo que
permite que una PWA funcione sin internet.

Su contracara: **cachea**, y en desarrollo eso significa que un arreglo puede no
verse porque devuelve la versión vieja. Por eso en OlimpOS está apagado durante
el desarrollo, a propósito.

### PWA

*Progressive Web App*: una web que el celular puede **instalar** como si fuera
una app nativa — ícono propio, sin barra de direcciones, con su pantalla de
arranque.

Necesita tres cosas: un **manifiesto** (nombre, íconos, colores), un **service
worker**, y **contexto seguro** (HTTPS o `localhost`). Sin la tercera, la opción
de instalar no aparece aunque las otras dos estén.

### TypeScript

JavaScript con tipos. Los tipos se verifican al compilar y después
**desaparecen**: el navegador corre JavaScript común.

Eso define exactamente qué garantiza —que no llames un método que no existe— y
qué **no**: nada en tiempo de ejecución. Si el backend manda algo distinto de lo
declarado, TypeScript no se entera.

---

## Los diez términos que más aparecen, en una línea

Si sólo te llevás diez:

| | |
|---|---|
| **Endpoint** | Un verbo + una ruta que la API sabe contestar. Hay 138. |
| **Header** | Metadato que viaja junto al pedido, aparte de los datos. |
| **Cookie** | Texto que el navegador guarda y **devuelve solo** en cada pedido. |
| **Middleware** | Código que ven **todos** los pedidos, antes del endpoint. |
| **Dependencia** | Función que corre **antes** del endpoint y puede cortarlo. |
| **Trigger** | Código que **la base** ejecuta sola al escribirse una tabla. |
| **Constraint** | Regla declarada en la tabla que la base hace cumplir siempre. |
| **Transacción** | Bloque que pasa entero o no pasa nada. |
| **Hook** | Función `use…` que le da memoria o efectos a un componente. |
| **DOM** | El árbol que el navegador tiene en memoria y que sí está en pantalla. |

---

# PARTE I — La arquitectura

## 1. Cliente–servidor: por qué el backend no es "el que guarda los datos"

### El problema

La forma intuitiva de pensar un sistema es: *"la app hace todo y la base guarda
los datos"*. Con esa idea, el backend parece un intermediario innecesario — un
gasto de trabajo. ¿Por qué no que la PWA hable directo con PostgreSQL?

Porque **todo lo que corre en la máquina del usuario es negociable**. La PWA
baja al navegador como archivos de texto: cualquiera abre las devtools y los
edita. Flet corre como un programa en la máquina del mostrador: cualquiera con
acceso a esa máquina puede reemplazarlo.

Si la regla *"un recepcionista no puede dar de alta empleados"* viviera sólo en
el frontend, alcanzaría con borrar un `if` para saltearla.

### La idea

El backend existe para ser **el único lugar del sistema que el usuario no
controla**. Todo lo demás es sugerencia; esto es la ley.

De ahí sale la frase que se repite en todo el proyecto:

> **El frontend esconde. El backend rechaza.**

Están escritas literalmente, y las dos veces con la misma advertencia:

- `backend/permisos.py:23` — *"la copia de config.ts es UX (decide qué se
  dibuja), esta copia es SEGURIDAD (decide qué se ejecuta)"*
- `config.ts:191` — *"⚠️ ESTO ES UX, NO SEGURIDAD"*

### En OlimpOS

La prueba de que el frontend no alcanza está escrita en el propio código, y no
es hipotética: `config.ts:585-592` documenta un agujero **real** que existió.
El Recepcionista tenía `gestionUsuarios: true` sin noción de jerarquía, así que
la tabla le dibujaba los botones sobre la fila del Dueño. El peor no era
"desactivar" sino **"resetear contraseña"**: genera una clave temporal y la
muestra en pantalla a quien apretó el botón.

> Un recepcionista podía resetearle la contraseña al Dueño, leerla en su propia
> pantalla, y entrar con control total. **Escalación de privilegios completa,
> sin devtools ni nada raro: tres clicks en la interfaz normal.**

El arreglo tiene dos mitades y hacen falta las dos: `esCuentaDeMayorJerarquia`
(`config.ts:600`) oculta los botones, y `_validar_jerarquia` en el router de
usuarios rechaza la operación aunque el botón aparezca.

### La pregunta de examen

> *"¿Por qué validás los permisos dos veces?"*

No son dos validaciones del mismo tipo. La del frontend evita que alguien vea
un botón que le va a dar error — es **cortesía**. La del backend evita que la
operación ocurra — es **seguridad**. Sacar la primera empeora la experiencia;
sacar la segunda abre el sistema.

---

## 2. Por qué tres programas y no uno

La pregunta razonable es: si la PWA ya muestra todo, ¿para qué la app de
escritorio? Y si el backend ya tiene la lógica, ¿por qué dos frontends?

La respuesta no es técnica, es de **público**:

| | PWA | Flet |
|---|---|---|
| Quién | Los socios | El personal |
| Dónde | Cualquier celular | La máquina del mostrador |
| Instalación | Ninguna: es una URL | Un programa instalado |
| Amenazas propias | XSS, CSRF (es un navegador) | Ninguna de esas dos |
| Sesión | Cookie `httpOnly` + CSRF | `Authorization: Bearer` |

Ese último renglón es el ejemplo más limpio de todo el proyecto de una decisión
que **parece inconsistencia y es diseño**. Está explicado en
`backend/cookies.py:21-34`:

> *"Darle cookies a Flet no agregaría ninguna seguridad y le sumaría la
> complejidad del CSRF sin motivo. Cada cliente usa el mecanismo que resuelve
> SUS amenazas — eso es diseño, no inconsistencia."*

Y el backend lo resuelve con **un solo header**. `auth_router.py:171`:

```python
es_escritorio = (x_client_type or "").strip().lower() == CLIENTE_ESCRITORIO
```

Si el cliente se declara escritorio, el token va en el cuerpo (`:174`). Si no,
va en cookies y el cuerpo lleva `None` (`:176-179`), porque **que el navegador
no pueda leer el token es todo el punto de la cookie `httpOnly`**.

---

## 3. Las capas del backend, y qué protege cada una

Un pedido a `/socios` atraviesa esto, en orden:

```
  1. CORS             ¿este ORIGEN puede hablarme?         main.py:181
  2. CSRF             ¿el header coincide con la cookie?   main.py:200
  3. obtener_sesion   ¿hay sesión válida?         → 401    security.py:77
  4. requiere_seccion ¿el rol entra acá?          → 403    security.py:140
  5. requiere_accion  ¿puede ejecutar ESTO?       → 403    security.py:169
  6. Pydantic         ¿el cuerpo tiene la forma?  → 422    schemas.py
  7. el router        reglas de negocio           → 400/404/409
  8. la base          constraints, triggers       → error de integridad
```

Cada capa asume que la anterior pudo fallar. Eso se llama **defensa en
profundidad**, y el ejemplo canónico en OlimpOS es el cupo de un turno, que
está defendido **tres** veces:

| Dónde | Qué tapa | Qué NO tapa |
|---|---|---|
| El frontend deshabilita el botón | El caso normal | Un `curl` directo |
| `with_for_update()` en `actividades.py:354` | Dos personas reservando a la vez | Un INSERT a mano en la base |
| `CONSTRAINT TRIGGER` (migración 006) | INSERT manual, script, bug futuro | La carrera entre transacciones |

Y está escrito así en `actividades.py:348-351`: *"Cada uno tapa un agujero
distinto; por eso están los dos."* Ese es el razonamiento correcto — no *"por
las dudas"*, sino que cada defensa cubre exactamente lo que la otra no puede.

---

# PARTE II — Criptografía

Esta es la parte que más se pregunta y peor se contesta, porque casi todo el
mundo usa la palabra "encriptar" para tres cosas distintas.

## 4. La distinción que ordena todo: cifrar ≠ hashear ≠ firmar

Son **tres operaciones diferentes**, con propósitos diferentes, y confundirlas
es el error más común.

|   | Cifrar | Hashear | Firmar (MAC) |
|---|---|---|---|
| ¿Se puede volver atrás? | **Sí**, con la clave | **No**, nunca | No aplica |
| Para qué sirve | Que nadie LEA | Que nadie RECUPERE | Que nadie ALTERE |
| Pregunta que responde | *"¿qué dice?"* | *"¿es la misma?"* | *"¿lo escribí yo?"* |
| En OlimpOS | TLS (la conexión) | contraseñas | JWT y webhook |

La analogía que funciona:

- **Cifrar** es una caja fuerte. Guardás algo, y con la llave lo sacás igual.
- **Hashear** es una picadora de carne. Metés un bife y sale carne picada.
  Podés meter otro bife y ver si sale la misma carne picada — pero de la carne
  picada **no vuelve a salir el bife**.
- **Firmar** es un sello de lacre. No esconde nada: cualquiera lee la carta.
  Lo que garantiza es que si alguien la modificó, el sello ya no cierra.

> **Por qué importa esta distinción en la defensa:** si decís "las contraseñas
> están encriptadas", la repregunta natural es *"¿y quién tiene la clave para
> desencriptarlas?"*. La respuesta correcta es que **no hay clave, porque no
> están cifradas: están hasheadas, y eso es más fuerte**. Ni vos, ni el dueño
> del gimnasio, ni alguien con acceso total a Neon puede leer una contraseña.

Está dicho textualmente en `auth.py:62-65`:

> *"Nunca se 'desencripta' el hash guardado: se vuelve a hashear lo que la
> persona escribió (con el mismo salt, que viaja dentro del hash) y se comparan
> los resultados. Por eso ni siquiera con acceso directo a la base se pueden
> leer las contraseñas."*

---

## 5. bcrypt — las contraseñas

**Herramienta:** `bcrypt~=4.2.0`, usada directamente (sin `passlib`).

### El problema

Guardar contraseñas en texto plano significa que quien vea la base ve todas las
contraseñas de todos los socios. Y como la gente reusa contraseñas, se filtra
también su mail, su banco y su Instagram.

La primera idea es hashear con SHA-256. **No alcanza**, por dos razones:

1. **SHA-256 es rápido a propósito.** Una GPU calcula miles de millones por
   segundo. Probar todas las contraseñas de 8 caracteres es cuestión de horas.
2. **Sin sal, dos personas con la misma contraseña tienen el mismo hash.** Se
   ve de un vistazo quién usa `123456`, y existen tablas precalculadas
   (*rainbow tables*) con los hashes de millones de contraseñas comunes.

### La idea

bcrypt resuelve las dos:

- **Sal (*salt*):** un valor aleatorio distinto por contraseña, que se mezcla
  antes de hashear y **se guarda dentro del propio hash**. Dos socios con la
  misma contraseña tienen hashes distintos, y las tablas precalculadas quedan
  inservibles.
- **Costo (*cost factor*):** bcrypt está diseñado para ser **lento a
  propósito**, y cuánto es configurable. El costo es un exponente: cada +1
  duplica el trabajo. Que verificar un login tarde una fracción de segundo no
  molesta a nadie, pero convierte "probar mil millones de contraseñas" en algo
  que tarda siglos.

Es la única familia de algoritmos donde **la lentitud es la característica, no
un defecto**.

### En OlimpOS

```python
# auth.py:57
return bcrypt.hashpw(_a_bytes(password), bcrypt.gensalt()).decode("utf-8")

# auth.py:72
return bcrypt.checkpw(_a_bytes(password_plano), password_hash.encode("utf-8"))
```

`gensalt()` genera la sal aleatoria y fija el costo por defecto de la librería.
`checkpw` extrae la sal del hash guardado, rehashea lo que la persona escribió,
y compara.

**El detalle de los 72 bytes** (`auth.py:38-48`) es el tipo de cosa que
distingue a alguien que entendió de alguien que copió:

```python
BCRYPT_MAX_BYTES = 72

def _a_bytes(password: str) -> bytes:
    """Codifica a UTF-8 y recorta a los 72 bytes que bcrypt realmente usa."""
    return password.encode("utf-8")[:BCRYPT_MAX_BYTES]
```

bcrypt **sólo mira los primeros 72 bytes** de la contraseña. Es un límite del
algoritmo, no de la librería. El código trunca explícitamente en vez de dejar
que la librería lance una excepción con una contraseña larga pero legítima, y
el comentario anota la salida correcta si algún día hiciera falta más:
**pasar la contraseña por SHA-256 antes de bcrypt** (que da 32 bytes fijos), no
subir ese número.

Ojo con un detalle de codificación: son 72 **bytes**, no caracteres. Una `ñ` o
un emoji ocupan más de un byte en UTF-8.

### Por qué no `passlib`

`requirements.txt` lo documenta: passlib está sin mantenimiento desde 2020 y es
incompatible con bcrypt 4.1+. La combinación produce el error engañoso
*"password cannot be longer than 72 bytes"* **con contraseñas de cualquier
largo**, y manda a depurar en la dirección equivocada.

### La pregunta de examen

> *"¿Qué pasa si alguien roba tu base de datos?"*

Se lleva los hashes, no las contraseñas. Para cada cuenta tendría que hacer
fuerza bruta por separado —la sal impide atacarlas todas juntas— y cada intento
le cuesta el costo de bcrypt. Lo que sí se lleva son los **datos personales**,
y contra eso el hash no hace nada: eso lo protege el control de acceso a Neon.

---

## 6. Aleatoriedad: `secrets` y no `random`

**Herramienta:** el módulo `secrets` de la biblioteca estándar de Python.

### El problema

Cuando el mostrador da de alta a un socio, el sistema le fabrica una contraseña
temporal. Si esa contraseña fuera predecible, cualquiera podría adivinar la de
la próxima persona que se anote.

### La idea

`random` usa el algoritmo **Mersenne Twister**, pensado para simulaciones. Es
rápido y estadísticamente uniforme, pero **determinista**: con suficientes
salidas observadas se reconstruye su estado interno y se predicen todas las
siguientes. `secrets` usa la fuente criptográfica del sistema operativo,
diseñada para que eso sea imposible.

Está anotado en `auth.py:94-97`:

> *"random usa un generador predecible pensado para simulaciones, y con unas
> pocas salidas se puede reconstruir su estado interno y adivinar las
> siguientes."*

### En OlimpOS — los tres usos

```python
# auth.py:99   — contraseña temporal (~72 bits de entropía)
return secrets.token_urlsafe(LARGO_PASSWORD_TEMPORAL)   # LARGO = 12

# csrf.py:60   — token CSRF por sesión
return secrets.token_urlsafe(32)

# auth.py:134  — desempate de username imposible de adivinar
base = f"socio{secrets.randbelow(10000):04d}"
```

Fijate el razonamiento de por qué 12 y no 64 (`auth.py:84-86`): es una clave
que **dura hasta el primer ingreso** y que **alguien tiene que poder dictar por
teléfono**. Más larga no agrega seguridad real y sí fricción. El token CSRF, en
cambio, no lo dicta nadie: va a 32 bytes.

> **Concepto: entropía.** Es cuántos bits de "sorpresa" tiene un secreto.
> 72 bits significa que hay 2⁷² posibilidades. Un atacante que probara mil
> millones por segundo tardaría más que la edad del universo — y eso **sin
> contar** que a los 5 intentos la cuenta se bloquea.

---

## 7. JWT — la sesión que no se guarda en ningún lado

**Herramienta:** `python-jose[cryptography]~=3.3.0`, algoritmo **HS256**.

### El problema

HTTP **no tiene memoria**. Cada pedido llega solo, sin ninguna relación con el
anterior. Entonces: después del login, ¿cómo sabe el backend, en el pedido
número 200, que sos vos?

La solución clásica es la **sesión con estado**: el servidor guarda una tabla
`sesiones` y le da al cliente un identificador. Funciona, pero cada pedido
implica **una consulta más a la base**. Con una base a 44 ms de distancia, eso
es caro.

### La idea

Un JWT invierte el problema: en vez de guardar la sesión en el servidor y
darle al cliente un ticket, **se le da al cliente la sesión entera, sellada**.

Un JWT tiene tres partes separadas por puntos:

```
   eyJhbGciOiJIUzI1NiJ9  .  eyJzdWIiOiI3Iiwicm9sZXMiOlsiZHVlbm8iXX0  .  4pQ7x…
   └──── cabecera ────┘     └────────────── contenido ────────────┘     └ firma ┘
        qué algoritmo            quién sos, qué roles, cuándo vence
```

**Lo más importante y lo que más se dice mal:**

> **Un JWT NO está cifrado. Está FIRMADO.**

Las dos primeras partes son **Base64**, que no es cifrado: es una forma de
escribir bytes con letras. Cualquiera que tenga el token puede leer su
contenido — pegalo en jwt.io y lo ves. Lo que la firma garantiza no es secreto,
es **integridad**: si alguien cambia una sola letra del contenido, la firma deja
de cerrar y el backend lo rechaza.

De ahí sale la regla: **nunca poner un secreto adentro de un JWT.**

### HS256, y el matiz que casi nadie menciona

HS256 es **HMAC con SHA-256**: una firma **simétrica**. La misma clave firma y
verifica. La consecuencia práctica es fuerte:

> Cualquiera que pueda **verificar** un token puede también **falsificarlo**.

Por eso `JWT_SECRET_KEY` no puede salir nunca del servidor. La alternativa
sería RS256 (asimétrico: una clave privada firma, una pública verifica), que
tiene sentido cuando varios servicios distintos necesitan validar tokens que
sólo uno emite. Acá hay **un solo backend**, así que HS256 es la elección
correcta y más simple.

### En OlimpOS

```python
# auth.py:28-33 — sin secreto, el backend NO ARRANCA
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("Falta JWT_SECRET_KEY en el .env. Generá una con: ...")

# auth.py:35-36
ALGORITMO = "HS256"
EXPIRACION_MINUTOS = int(os.getenv("JWT_EXPIRACION_MINUTOS", "480"))   # 8 horas

# auth.py:176-184 — el contenido firmado
payload = {
    "sub": str(id_usuario),   # la spec de JWT pide que `sub` sea string
    "username": username,
    "roles": roles,
    "id_socio": id_socio,
    "iat": ahora,
    "exp": ahora + timedelta(minutes=EXPIRACION_MINUTOS),
}
return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITMO)

# auth.py:194-197 — verificar es una sola llamada, y falla silenciosa
try:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITMO])
except JWTError:
    return None
```

Tres decisiones adentro de esas líneas, cada una con su motivo escrito:

**1. `sub` lleva el `id_usuario`, no el `username`** (`auth.py:171-173`). El
username se puede editar; el id no. Un token viejo tiene que seguir apuntando a
la misma cuenta aunque le hayan cambiado el nombre de acceso.

**2. Los roles viajan DENTRO del token** (`auth.py:164-169`). Se calculan una
sola vez en el login con `roles_de_persona` (`models.py:921`), que lee seis
relaciones. Recalcularlos en cada pedido costaría cinco JOINs por request para
un dato que no cambia durante la sesión.

**3. `id_socio` viaja firmado** (`auth.py:157-162`), y esto es una decisión de
seguridad, no de comodidad: es el id con el que trabajan **todas** las pantallas
del portal. Si cada una lo resolviera por su cuenta, alcanzaría con que una se
olvidara de filtrar para empezar a mostrar datos de otra persona. Al venir
firmado, **el cliente no puede alterarlo**.

### El precio del JWT, y cómo se paga

Un token sin estado **no se puede revocar**: mientras no expire, es válido. Si
despedís a alguien a las 9 de la mañana, su token sigue sirviendo ocho horas.

OlimpOS lo resuelve con una consulta barata por PK en cada pedido
(`security.py:99-103`):

```python
# security.py:118-120
usuario = db.get(Usuario, id_usuario)
if usuario is None or not usuario.activo or usuario.bloqueado:
    raise _NO_AUTENTICADO
```

Es una decisión con un trade-off explícito y vale la pena poder enunciarlo:

| | Efecto |
|---|---|
| Cambiar un **rol** | NO tiene efecto hasta el próximo login (viene del token) |
| **Desactivar** una cuenta | Efecto **inmediato** (se relee de la base) |

Se eligió pagar una consulta por PK —barata, por índice— para que lo urgente
sea inmediato, y aceptar la demora en lo que no lo es.

Y hay un tercer corte, en `security.py:126-131`: si la cuenta quedó marcada con
`debe_cambiar_password`, ningún token sirve. Un token emitido antes de un reseteo
no puede seguir operando.

### La pregunta de examen

> *"Si el JWT se puede leer, ¿no es inseguro que lleve los roles?"*

No, porque **los roles no son un secreto**: son los roles de esa misma persona,
que ya los conoce. Lo que importa es que no los pueda **cambiar**, y eso lo
garantiza la firma. Si el token dijera `roles: ["dueno"]` sin la clave, la
verificación fallaría y `decodificar_token` devolvería `None`.

---

## 8. HMAC — verificar que el aviso vino de Mercado Pago

**Herramienta:** `hmac` + `hashlib` (biblioteca estándar).

### El problema

Cuando alguien paga online, Mercado Pago le avisa al backend con un POST a una
URL. Esa URL **tiene que ser pública** — MP tiene que poder llamarla desde sus
servidores, así que no puede exigir login.

Entonces: cualquiera que descubra la URL puede hacer un POST diciendo *"el pago
123 está aprobado"*. Sin verificación, **acreditar cuotas gratis sería cuestión
de adivinar un número**.

### La idea

**HMAC** (Hash-based Message Authentication Code) responde exactamente la
pregunta *"¿este mensaje lo escribió alguien que conoce el secreto?"*.

Funciona así: las dos partes comparten un secreto. El que manda arma un texto
con los datos del mensaje, lo pasa por HMAC-SHA256 con el secreto, y adjunta el
resultado. El que recibe **repite el cálculo** con su copia del secreto y
compara. Si dan igual, el mensaje vino de quien dice y no fue modificado.

No es lo mismo que hashear a secas: un hash simple lo puede calcular cualquiera.
HMAC **requiere el secreto**, y por eso autentica.

### En OlimpOS

```python
# mercadopago.py:270
def verificar_firma(x_signature: str, x_request_id: str, data_id: str) -> bool:

# mercadopago.py:286-287 — sin secreto configurado, se rechaza TODO
if not MP_WEBHOOK_SECRET or not x_signature:
    return False

# mercadopago.py:299-305
manifiesto = f"id:{data_id};request-id:{x_request_id};ts:{ts};"
esperada = hmac.new(
    MP_WEBHOOK_SECRET.encode(),
    manifiesto.encode(),
    hashlib.sha256,
).hexdigest()
return hmac.compare_digest(esperada, firma)
```

El `if` de la línea 286 es una decisión de diseño que conviene saber nombrar:
**fail closed** (fallar cerrado). Si falta la configuración, se rechaza todo en
vez de aceptar todo. El comentario lo dice sin vueltas: *"Un webhook sin
verificar es una puerta abierta."*

El uso está en `pagos_online.py:311`, y lo que hace después es igual de
importante:

```python
if not mp.verificar_firma(x_signature, x_request_id, id_pago_mp):
    print(f"  [MP] Aviso RECHAZADO por firma inválida (pago {id_pago_mp}).")
    return MensajeResponse(mensaje="Firma inválida. El aviso se descarta.")
```

### Dos decisiones más del webhook que valen oro en una defensa

**1. Del cuerpo sólo se lee el ID** (`pagos_online.py:294-296`). El estado y el
monto **se releen preguntándole a Mercado Pago** con nuestro token. ¿Por qué, si
la firma ya garantiza que el mensaje es auténtico? Porque es defensa en
profundidad: el cuerpo llega por HTTP y lo puede escribir cualquiera que
descubra la URL. Confiar en el dato que llega es una capa menos.

**2. Siempre contesta 200** (`pagos_online.py:290-292`), incluso al descartar el
aviso. Si contestara error, Mercado Pago **reintentaría** el mismo aviso una y
otra vez creyendo que no llegó.

Y eso enlaza con el concepto siguiente.

---

## 9. Idempotencia — que el mismo aviso dos veces no cobre dos veces

### El problema

Mercado Pago **reintenta por diseño** si no le contestás rápido. O sea que el
mismo aviso de pago puede llegar dos, tres o cinco veces. Sin protección, una
cuota se acreditaría varias veces y la membresía se extendería el doble.

### La idea

Una operación es **idempotente** cuando aplicarla N veces da el mismo resultado
que aplicarla una. No es "que no falle dos veces": es que el **efecto** sea el
mismo.

- `x = 5` es idempotente. `x = x + 5` no lo es.
- "Marcar el pago 123 como confirmado" es idempotente.
- "Sumar un mes a la membresía" **no lo es** — y por eso hace falta el guard.

### En OlimpOS

```python
# pagos_online.py:194-197
comprobante = f"MP-{id_pago_mp}"

if pago.numero_comprobante == comprobante and pago.estado == estado:
    return "Ya estaba aplicado. No se hizo nada."
```

Y acá está el detalle que hace la diferencia entre entender y copiar
(`pagos_online.py:180-184`):

> *"La idempotencia se apoya en `Pago.numero_comprobante`, que es UNIQUE en el
> esquema (…) Que la defensa viva en el esquema y no sólo en este `if` importa,
> porque **el `if` se puede olvidar de aplicar y el UNIQUE no**."*

Es el mismo patrón que se repite en todo el proyecto: la regla se **baja al
esquema**, donde no se puede olvidar, en vez de quedarse en un `if` que el
próximo endpoint puede no copiar.

Hay una tercera defensa, y es la que más llama la atención en una defensa oral
(`pagos_online.py:199-206`): **si el monto no coincide, NO se acredita**. Puede
ser un id reutilizado, un aviso apuntando al pago equivocado, o alguien
probando. Se deja `PENDIENTE` para que lo mire una persona.

---

## 10. Comparación en tiempo constante — el ataque que nadie ve venir

### El problema

Esto es lo más contraintuitivo de toda la sección, y por eso es la mejor
pregunta para lucirse.

Comparar dos strings con `==` parece inofensivo. No lo es cuando uno de los dos
es un secreto, porque **`==` corta apenas encuentra una diferencia**:

```
  esperado:  "abc123..."
  recibido:  "xyz..."      -> falla en el carácter 1: rápido
  recibido:  "abc999..."   -> falla en el carácter 4: un poquito más lento
```

Esa diferencia de tiempo es minúscula —nanosegundos— pero **medible con
suficientes intentos**. Un atacante prueba todos los primeros caracteres, se
queda con el que tarda más, y repite. Así **reconstruye el token carácter por
carácter**, convirtiendo un problema exponencial (probar todos los tokens) en
uno lineal (probar 64 opciones por posición).

Se llama **ataque de temporización** (*timing attack*).

### La idea

`secrets.compare_digest` compara **siempre todas las posiciones**, sin cortar
antes. Tarda lo mismo den igual o no, así que el tiempo no filtra información.

### En OlimpOS — los dos usos

```python
# csrf.py:87 — el token CSRF
if not cookie_csrf or not header_csrf or not secrets.compare_digest(cookie_csrf, header_csrf):

# mercadopago.py:305 — la firma del webhook
return hmac.compare_digest(esperada, firma)
```

El comentario de `csrf.py:84-86` lo explica exacto:

> *"compare_digest y no ==: comparar strings con == corta apenas encuentra una
> diferencia, y ese tiempo distinto permite adivinar el token carácter por
> carácter. compare_digest tarda lo mismo siempre."*

> **Matiz de rigor:** `compare_digest` es de tiempo constante respecto del
> **contenido**, no del **largo**. Si los dos strings tienen largos distintos,
> eso sí se puede notar. Para tokens de largo fijo —que es el caso acá— no
> importa.

### El mismo principio, en otro lado

La misma idea aparece **sin criptografía** en el login. `auth_router.py:44`:

```python
CREDENCIALES_INVALIDAS = "Usuario o contraseña incorrectos"
```

Un solo mensaje para **cuatro** situaciones distintas: usuario inexistente,
cuenta inactiva, cuenta bloqueada, contraseña incorrecta. Si dijera *"ese
usuario no existe"*, el login se convertiría en **un detector de cuentas
válidas** — probás mil usernames y averiguás cuáles existen antes de empezar a
adivinar contraseñas.

Es el mismo concepto general: **no filtrar información por el costado**. Ahí es
por el mensaje; en `compare_digest`, por el reloj.

La contracara honesta está anotada en el `CLAUDE.md`: desde afuera **no se
distingue** "me equivoqué" de "ya está bloqueada". Es el precio, y se pagó a
propósito.

---

## 11. Fuerza bruta — el bloqueo a los 5 intentos

```python
# auth_router.py:46
MAX_INTENTOS_FALLIDOS = 5

# auth_router.py:72-75
usuario.intentos_fallidos = (usuario.intentos_fallidos or 0) + 1
if usuario.intentos_fallidos >= MAX_INTENTOS_FALLIDOS:
    usuario.bloqueado = True
db.commit()
```

El detalle que hay que poder explicar es **por qué hay un `db.commit()` ahí**,
en una request que va a terminar en 401 (`auth_router.py:64-66`):

> *"El contador se guarda con commit aunque la request termine en 401: si se
> perdiera al hacer rollback, el bloqueo nunca llegaría a dispararse y la cuenta
> quedaría abierta a fuerza bruta."*

Es un caso donde **el efecto secundario tiene que sobrevivir al error**. Sin ese
commit, el contador nunca pasaría de 1.

---

## 12. Tabla maestra: amenaza → defensa → dónde vive

Ésta es la tabla para llevar impresa.

| Amenaza | Qué haría el atacante | Defensa | Archivo:línea |
|---|---|---|---|
| **Robo de la base** | Leer las contraseñas | bcrypt con sal | `auth.py:57` |
| **Rainbow tables** | Buscar el hash en una tabla precalculada | sal aleatoria por contraseña | `auth.py:57` (`gensalt`) |
| **Fuerza bruta offline** | Probar millones de contraseñas | costo de bcrypt (lento a propósito) | `auth.py:57` |
| **Fuerza bruta online** | Probar contraseñas contra el login | bloqueo a los 5 intentos | `auth_router.py:73` |
| **Enumeración de usuarios** | Averiguar qué cuentas existen | un solo mensaje de error | `auth_router.py:44` |
| **Token falsificado** | Editar sus roles a "dueno" | firma HS256 | `auth.py:184` / `:195` |
| **Token robado, uso eterno** | Usarlo para siempre | `exp` a 8 h + relectura del usuario | `auth.py:182`, `security.py:118` |
| **Cuenta dada de baja** | Seguir operando con el token viejo | se relee `activo`/`bloqueado` | `security.py:119` |
| **Contraseña reseteada** | Seguir con el token anterior | corte por `debe_cambiar_password` | `security.py:126` |
| **XSS roba la sesión** | Leer el token con JavaScript | cookie `httpOnly` | `cookies.py:88` |
| **CSRF** | Hacerte disparar un POST desde otro sitio | doble envío de cookie + `SameSite=lax` | `csrf.py:87`, `cookies.py:74` |
| **Sitio cualquiera llama a la API** | Pedidos autenticados desde otro origen | CORS con lista, nunca `*` | `main.py:181-194` |
| **Sesión en WiFi abierto** | Leer la cookie del cable | `Secure` (sólo HTTPS) | `cookies.py:65` |
| **Webhook falso** | "El pago 123 está aprobado" | HMAC-SHA256 | `mercadopago.py:300` |
| **Webhook repetido** | Acreditar dos veces | idempotencia + UNIQUE | `pagos_online.py:196` |
| **Monto adulterado** | Pagar $1, acreditar $30.000 | se compara contra el `Pago` | `pagos_online.py:203` |
| **Timing attack** | Adivinar el token por el reloj | `compare_digest` | `csrf.py:87`, `mercadopago.py:305` |
| **Contraseña temporal predecible** | Adivinar la del próximo socio | `secrets`, no `random` | `auth.py:99` |
| **Hash filtrado en una respuesta** | Leer `password_hash` de un JSON | el schema no lo declara | `schemas.py:62-74` |
| **Escalación de privilegios** | Resetearle la clave al Dueño | jerarquía de filas | `config.ts:600` |
| **Secreto en el repo** | Leer `DATABASE_URL` en GitHub | `.env` ignorado, `.env.example` versionado | `EMPEZAR-EN-OTRA-PC.md` §1 |

**Una defensa que NO es criptografía y es la más importante de todas:**
`schemas.py:62-74`. `UsuarioOut` simplemente **no declara** `password_hash`. No
hay un `del` ni un filtro que pueda fallar: el campo no existe en el molde de
salida, así que no hay forma de que se filtre por olvido — *"ni siquiera si
alguien devuelve el objeto ORM entero desde un endpoint"* (`schemas.py:6-10`).

Eso es **seguridad por construcción**: la vulnerabilidad no está mitigada, es
imposible de escribir.

---

# PARTE III — La sesión y su transporte

## 13. Dónde guardar el token: las cuatro opciones y por qué ganó la cookie

Éste es **el** tema donde conviene poder recorrer las alternativas, porque la
respuesta correcta depende del cliente.

| Dónde | ¿Lo lee JS? | Resiste XSS | Resiste CSRF | ¿Se usa acá? |
|---|---|---|---|---|
| Variable en memoria | Sí | No | Sí | **Sí, en Flet** |
| `localStorage` | Sí | **No** | Sí | No |
| `sessionStorage` | Sí | **No** | Sí | No (se usó antes) |
| Cookie `httpOnly` | **No** | **Sí** | **No** → hace falta CSRF | **Sí, en la PWA** |

Las dos primeras filas son robables con XSS: alcanza con que un script inyectado
las lea y las mande a otro servidor. La cookie `httpOnly` **no es visible para
JavaScript**, así que ni un XSS puede exfiltrarla.

Y ahí está el punto que hay que entender bien:

> **La cookie no elimina el riesgo, lo cambia de forma.** Con XSS y cookie
> `httpOnly`, el atacante puede **disparar pedidos** desde la página de la
> víctima (mientras esté ahí), pero **no llevarse la sesión** para usarla
> después, desde otra máquina, cuando quiera. Es la diferencia entre un daño
> acotado y una cuenta comprometida para siempre.

Está dicho así en `cookies.py:8-19`, con la conclusión más importante del
archivo:

> *"No es opcional: **cookie sin CSRF es peor que token en localStorage**."*

Porque una cookie la manda el navegador **sola**, en todo pedido a ese dominio,
sin importar quién lo originó. Eso es exactamente el ataque siguiente.

---

## 14. XSS — inyección de scripts

### El problema

Si tu app muestra texto que escribió un usuario sin procesarlo, y ese texto es
una etiqueta `<script>`, el navegador lo **ejecuta**. Ese script corre con todos
los privilegios de la página: lee `localStorage`, hace pedidos con la sesión,
mira el DOM.

### En OlimpOS

React **escapa por defecto** todo lo que se interpola en JSX. `{socio.nombre}`
se inserta como **texto**, no como HTML. Un socio cuyo nombre fuera una etiqueta
de script se vería en pantalla con esas letras, literal.

La forma de romper esa protección se llama, sin ironía,
`dangerouslySetInnerHTML`. El nombre es una advertencia deliberada de la
biblioteca.

**Verificado en este repo:** no se usa en ningún lado.

```
grep -rn "dangerouslySetInnerHTML" Proyecto/src/frontend/src/   →  sin resultados
```

Flet tiene el problema aún menos: no renderiza HTML. Un `ft.Text` dibuja texto
en un canvas; no hay parser de HTML donde inyectar nada.

---

## 15. CSRF — el ataque que la cookie trae puesto

### El problema

Éste es el ataque más difícil de explicar y el que mejor queda cuando lo
explicás bien. La descripción de `csrf.py:9-18` es tan clara que conviene
memorizarla:

> El navegador manda las cookies de un dominio **solas**, en cada pedido, sin
> importar quién lo originó. Entonces, si el dueño del gimnasio está logueado en
> OlimpOS y abre otra pestaña con una página maliciosa, esa página puede poner un
> formulario apuntando a `https://olimpos/socios/7/baja` con método POST y
> enviarlo por JavaScript apenas carga.
>
> El navegador adjunta la cookie de sesión. **Para el backend es un pedido
> perfectamente autenticado del dueño.** Se da de baja un socio y nadie apretó
> nada.

Lo brutal es que el atacante **nunca ve la respuesta** (la política de mismo
origen se lo impide) y **no le hace falta**: le alcanza con que la acción
ocurra.

### La idea: doble envío de cookie

Se emiten **dos** cookies en el login:

| Cookie | `httpOnly` | Quién la lee |
|---|---|---|
| `olimpos_session` | **Sí** | Sólo el servidor |
| `olimpos_csrf` | **No** | La PWA, a propósito |

La PWA lee la segunda y la **copia al header `X-CSRF-Token`** en cada pedido que
modifica algo. El backend exige que header y cookie coincidan.

**Por qué esto funciona**, y es el punto que hay que poder decir:

> El sitio atacante puede lograr que el navegador **MANDE** las cookies, pero no
> puede **LEERLAS** — la política de mismo origen se lo impide. Sin poder leer
> el token, no puede armar el header, y el pedido se rechaza.

Que la cookie CSRF sea legible **no la debilita**, porque lo que la hace
funcionar no es que sea secreta: es que un sitio de otro dominio no puede
leerla. Está anotado en `cookies.py:47-51`.

### En OlimpOS — las dos mitades

**Backend** (`csrf.py:63-95`):

```python
# csrf.py:55 — los verbos que no modifican nada no necesitan protección
METODOS_SEGUROS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})

# csrf.py:71-79
if request.method in METODOS_SEGUROS:
    return await call_next(request)

cookie_sesion = request.cookies.get(COOKIE_SESION)
if not cookie_sesion:
    # Sin cookie no hay credencial ambiente que robar: es Flet con Bearer,
    # o un pedido sin autenticar. El CSRF no aplica.
    return await call_next(request)

# csrf.py:87
if not cookie_csrf or not header_csrf or not secrets.compare_digest(cookie_csrf, header_csrf):
    return JSONResponse(status_code=403, ...)
```

**PWA** (`api.ts:82-85` y `:154-157`): `tokenCsrf()` lee la cookie con una
expresión regular sobre `document.cookie`, y el cliente la copia al header sólo
cuando el método no es GET — *"mandarlo de más no rompe nada, y olvidarlo de
menos da un 403 difícil de diagnosticar"*.

### Tres decisiones de diseño en ese middleware

**1. Es middleware, no dependencia** (`csrf.py:64-69`). Una dependencia hay que
acordarse de ponerla en cada endpoint nuevo, y el día que alguien se olvide, ese
endpoint queda abierto **sin que nada avise**. Como middleware, la protección es
por defecto y **no hay forma de saltearla por descuido**.

Es la misma filosofía que el UNIQUE del comprobante y que `UsuarioOut` sin
`password_hash`: **hacer que el error sea imposible, no que esté prohibido**.

**2. La lista de métodos seguros descansa en una regla que el resto del código
debe respetar** (`csrf.py:51-54`): *"si algún día un GET escribe en la base,
este middleware deja de protegerlo"*. Es una dependencia explícita entre dos
partes lejanas del sistema, y está anotada donde corresponde.

**3. Si no hay cookie, pasa de largo** (`csrf.py:74-79`). Ahí está la
convivencia con Flet: sin credencial ambiente no hay CSRF posible, así que
exigirle un token sería ceremonia sin beneficio.

### La segunda capa: `SameSite=lax`

```python
# cookies.py:74
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax")
```

`SameSite=lax` le dice al navegador que **no mande la cookie en POST originados
por otro sitio**. Eso ya frena la mayor parte del CSRF por sí solo. El token es
la segunda capa, *"para los casos que lax no cubre y para no depender de que
todos los navegadores se comporten igual"* (`cookies.py:67-71`).

Y hay una nota que muestra criterio: `strict` sería más duro pero **rompe algo
útil** — al llegar desde un link externo, el primer pedido va sin cookie y el
usuario aparece deslogueado. Se eligió `lax` sabiendo lo que se dejaba.

---

## 16. CORS — lo que protege NO es tu servidor

### El problema

Y acá está el malentendido más común de todo el desarrollo web.

### La idea

CORS (*Cross-Origin Resource Sharing*) es una regla que **aplica el navegador**,
no el servidor. Un **origen** es la terna `esquema + host + puerto`:
`http://localhost:5173` y `http://127.0.0.1:8000` son **orígenes distintos**
(distinto host y distinto puerto).

Por defecto, el navegador impide que una página de un origen lea la respuesta de
otro. CORS es la forma en que el servidor dice *"a este origen sí le permito"*.

> **Lo que hay que entender:** CORS **no protege a tu servidor**. Un `curl`
> ignora CORS por completo — no hay navegador que lo aplique. Lo que CORS
> protege es **al usuario**: impide que cualquier página web random le haga
> pedidos autenticados a tu API usando las cookies que ese usuario ya tiene.

Por eso CORS **no reemplaza** la autenticación. Son cosas distintas: CORS decide
qué **páginas** pueden hablarte; la autenticación decide qué **personas**.

### En OlimpOS

```python
# main.py:181-194
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origenes_cors(),   # leídos del .env, NUNCA comodín
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

El comentario de las líneas 184-190 explica la combinación prohibida:

> *"Es también el motivo por el que `allow_origins` NUNCA puede ser el comodín:
> la combinación de comodín y credenciales está **prohibida por la spec de
> CORS** justamente porque dejaría a cualquier sitio hacer pedidos
> autenticados."*

Es una prohibición **del estándar**, no una recomendación: los navegadores
rechazan esa combinación. Y `main.py:43-48` marca la diferencia con el proyecto
de referencia del profesor, que sí usa el comodín — puede hacerlo porque su
único frontend es Flet, **que no es un navegador y por lo tanto no aplica
CORS**.

### El orden de los middlewares

```python
# main.py:196-200
# El middleware de CSRF va DESPUÉS del de CORS en el código, lo que en
# Starlette significa que se ejecuta ANTES en el pedido entrante (los
# middlewares se apilan en orden inverso).
app.middleware("http")(middleware_csrf)
```

Los middlewares en Starlette funcionan como una **cebolla**: el orden en que se
registran define el orden en que envuelven el pedido. Es exactamente el que se
quiere: **rechazar un pedido sin token CSRF antes de que llegue a tocar la
base.**

---

## 17. El proxy de Vite — por qué CORS casi no aparece en desarrollo

Acá hay una sutileza que rompe a mucha gente y en OlimpOS está resuelta de una
forma que **además** hace que desarrollo se parezca a producción.

### El problema

La PWA corre en `localhost:5173` y el backend en `127.0.0.1:8000`. Aunque los
dos sean "tu máquina", para el navegador son **hosts distintos**, y las cookies
pertenecen a un host. El resultado (`vite.config.ts:18-30`):

1. La cookie queda guardada bajo `127.0.0.1`; la página está en `localhost` y
   **no puede leerla**. `document.cookie` devuelve vacío y el token CSRF se
   vuelve inalcanzable.
2. Además son *sitios* distintos, así que `SameSite=lax` le prohíbe al navegador
   mandar la cookie en los fetch. **Todo responde 401.**

### La idea

Un **proxy inverso**: el servidor de desarrollo de Vite acepta pedidos a
`/api/...` y los reenvía al backend. Para el navegador **todo es el mismo
origen**.

```typescript
// vite.config.ts:44-54
server: {
  proxy: {
    '/api': {
      target: destinoApi,
      changeOrigin: false,   // conserva el Host, así la cookie queda en localhost
      rewrite: (ruta) => ruta.replace(/^\/api/, ''),
    },
  },
},
```

La cookie es de `localhost`, `document.cookie` la lee, `SameSite` queda
satisfecho, y **CORS desaparece por completo** porque ya no hay pedidos
cross-origin.

Y la observación que eleva esto de truco a decisión (`vite.config.ts:37-40`):

> *"Y esto NO es una muleta de desarrollo: en producción la PWA y la API van a
> estar detrás del mismo dominio (o del mismo reverse proxy), que es exactamente
> lo que esto simula. **El proxy hace que desarrollo se parezca a producción en
> vez de diferir de ella.**"*

Por eso `VITE_API_URL=/api` — una ruta **relativa**, no una URL absoluta.

---

## 18. Variables de entorno: la línea entre secreto y público

El `.env.example` de la PWA dice algo que hay que tener clarísimo:

> *"Ojo: TODO lo que empiece con `VITE_` termina en el bundle que baja el
> navegador. **Nunca poner un secreto acá.**"*

Y por eso hay dos variables con prefijos distintos:

| Variable | Prefijo | Llega al navegador | Por qué |
|---|---|---|---|
| `VITE_API_URL=/api` | `VITE_` | **Sí** | Lo necesita el `fetch` del cliente |
| `API_PROXY_DESTINO=...:8000` | ninguno | **No** | Sólo lo usa el servidor de Vite |

En el backend la línea es más dura todavía: `auth.py:29-33` hace que el proceso
**no arranque** si falta `JWT_SECRET_KEY`, con el comando para generar una en el
propio mensaje de error. Lo mismo `database.py:40-44` con `DATABASE_URL`.

> **Concepto: *fail fast*.** Si falta una configuración crítica, es mejor no
> arrancar que arrancar mal. Un backend que levanta sin `JWT_SECRET_KEY` y usa
> un default sería **mucho peor**: todos los tokens firmados con una clave que
> está en el código de un repo público.

Y un detalle operativo que se paga caro si se ignora: `JWT_SECRET_KEY` **tiene
que ser la misma en las dos máquinas** donde se levanta el proyecto. Si cambia,
todos los tokens emitidos antes dejan de validar. No es un problema de
seguridad, pero desconcierta: **el login anda y cualquier pantalla responde
401**.

---

# PARTE IV — Autenticación y autorización

## 19. 401 y 403 no son lo mismo

Dos palabras que se parecen y significan cosas distintas:

| | Pregunta | Código | Analogía |
|---|---|---|---|
| **Autenticación** | ¿Quién sos? | **401** Unauthorized | El documento en la puerta |
| **Autorización** | ¿Qué podés hacer? | **403** Forbidden | La pulsera que te dejaron poner |

El 401 dice *"no sé quién sos, identificate"*. El 403 dice *"sé perfectamente
quién sos, y no podés"*. Volver a loguearte arregla un 401 y **no hace nada**
contra un 403.

`security.py:8-12` lo pone en tres renglones:

```
obtener_sesion            ¿hay una sesión válida?            -> 401
requiere_seccion(...)     ¿el rol entra a esta sección?      -> 403
requiere_accion(...)      ¿el rol puede ejecutar esto?       -> 403
```

En el código real hay 3 usos de `HTTP_401_UNAUTHORIZED` y **17** de
`HTTP_403_FORBIDDEN`. Tiene sentido: identificarse es una sola cosa; los
permisos son muchos.

---

## 20. Inyección de dependencias — la barrera que no se puede olvidar

### El problema

La forma ingenua de chequear permisos es al principio de cada endpoint:

```python
@router.get("/socios")
def listar(db = Depends(get_db)):
    if not tiene_permiso(...):      # ← hay que acordarse SIEMPRE
        raise HTTPException(403)
```

El problema no es que esté mal: es que **depende de la memoria**. El día 40,
alguien agrega un endpoint y se olvida. No falla nada visible — simplemente
queda abierto.

### La idea

FastAPI resuelve las dependencias **antes** de ejecutar el cuerpo del endpoint.
Si la dependencia lanza, el cuerpo **nunca corre**.

Así, el permiso deja de ser algo que se hace adentro y pasa a ser parte de **la
firma de la función**:

```python
# security.py:144-151, del docstring
@router.get("/socios")
def listar(sesion: Sesion = Depends(requiere_seccion(Seccion.SOCIOS))):
    ...

@router.post("/socios")
def crear(sesion: Sesion = Depends(requiere_seccion(Seccion.SOCIOS, Acceso.TOTAL))):
    ...
```

`security.py:14-17` lo dice mejor que cualquier explicación:

> *"un endpoint mal escrito no puede 'olvidarse' de chequear permisos a mitad de
> camino: **si la dependencia está en la firma, la barrera ya se aplicó**."*

### El detalle del default, que es lo mejor del archivo

```python
# security.py:140
def requiere_seccion(seccion: str, minimo: str = Acceso.LECTURA):
```

El default es `LECTURA`, no `TOTAL`. Las escrituras tienen que pedir `TOTAL`
explícitamente. Y el motivo (`security.py:153-155`):

> *"que el pedido más permisivo sea el default hace que **olvidarse escriba de
> menos, no de más**."*

Eso se llama **fallar seguro** (*fail safe*). El descuido tiene que llevar al
caso restrictivo, no al abierto.

### `requiere_accion` va ADEMÁS, no en lugar de

`security.py:173-177` explica el caso que lo justifica: el Recepcionista en
Personal **entra a la sección** (LECTURA) pero **no puede dar de alta a nadie**.

- Proteger sólo la ruta → lo dejaría crear empleados.
- Proteger sólo la acción → lo dejaría ver una pantalla que no le corresponde.

Son dos permisos distintos sobre la misma pantalla, y hacen falta los dos.

---

## 21. RBAC — la matriz de permisos

### La idea

**RBAC** (*Role-Based Access Control*): los permisos no se le dan a personas, se
le dan a **roles**, y a las personas se les dan roles. Sin eso, cada alta
requeriría configurar permisos de cero y nadie podría responder *"¿qué puede
hacer un recepcionista?"* sin revisar todas las cuentas.

### Las tres decisiones de diseño de esta matriz

**1. Tres niveles, no dos** (`permisos.py:36-44`). El caso que lo obliga: un
Entrenador tiene que poder **consultar** la dieta de un socio (para saber de
quién es) **sin poder gestionarla**. Eso no es ni acceso total ni acceso nulo.

```python
class Acceso:
    NINGUNO = "ninguno"
    LECTURA = "lectura"
    TOTAL   = "total"
```

**2. Los roles se acumulan y gana el más alto** (`permisos.py:298-301`). El
dueño del gimnasio suele entrenar ahí (`dueno` + `socio`). La regla:

```python
# permisos.py:303-313
def acceso_a_seccion(roles: list[str], seccion: str) -> str:
    mejor = Acceso.NINGUNO
    for rol in roles:
        nivel = PERMISOS.get(rol, {})["secciones"].get(seccion, Acceso.NINGUNO)
        if _JERARQUIA[nivel] > _JERARQUIA[mejor]:
            mejor = nivel
    return mejor
```

> *"tener un rol extra nunca puede quitar permisos."*

Y `puede_accion` es un `any` por la misma razón (`permisos.py:321-324`).

**3. Los roles se DERIVAN, no se guardan.** `models.py:45` lo aclara: *"NO son
una columna de la base. Se derivan"*. `roles_de_persona` (`models.py:921-958`)
los lee de las tablas de rol:

```python
if persona.dueno is not None:      roles.append(Rol.DUENO)
if persona.socio is not None:      roles.append(Rol.SOCIO)
empleado = persona.empleado
if empleado is not None:
    if empleado.entrenador    is not None: roles.append(Rol.ENTRENADOR)
    if empleado.nutricionista is not None: roles.append(Rol.NUTRICIONISTA)
    if empleado.recepcionista is not None: roles.append(Rol.RECEPCIONISTA)
```

Esto es el mismo principio que la masterclass de datos llama **derivar en vez de
guardar**: si el rol fuera una columna, podría decir `entrenador` mientras la
tabla `Entrenador` no tiene fila. Derivándolo, **no puede haber contradicción**.

**Y un rol que a propósito no existe** (`models.py:52-53`): no hay
`Rol.PROFESOR`. Un profesor da clases pero **no inicia sesión**. Por eso
`auth_router.py:146-154` rechaza el login de una persona sin roles con un
mensaje claro: *"dejarla entrar la llevaría a un sistema donde no puede abrir ni
una sección: mejor un rechazo claro que una pantalla vacía"*.

### El permiso más interesante de toda la matriz

```python
# permisos.py:109
VER_HISTORIAL_MEDICO = "verHistorialMedico"
```

Es **la única acción donde el Recepcionista queda por debajo del Entrenador**
(`permisos.py:97-108`), y el razonamiento es de negocio, no técnico:

> El mostrador maneja plata, turnos e ingresos; **no hay ninguna tarea suya que
> requiera saber quién tiene diabetes, epilepsia o una lesión de rodilla**. Para
> una emergencia lo que hace falta es el contacto de emergencia, que vive en
> `Persona` y sí ve.
>
> El Entrenador y el Nutricionista sí: **una rodilla operada cambia la rutina y
> una celiaquía cambia la dieta**. Ese es todo el motivo por el que el gimnasio
> guarda ese dato.

Eso es **minimización de datos**: cada quien accede a lo que su tarea requiere,
y a nada más. Es un principio de protección de datos personales, no una
ocurrencia.

Tiene una consecuencia de UI que también es doctrina: el botón se **omite**, no
se deshabilita. Un botón gris que no responde igual delata que el socio tiene
algo cargado.

---

## 22. Las tres copias del mismo dato, y el script que las vigila

### El problema

La matriz vive en **tres archivos**, uno por lenguaje:

```
backend/permisos.py                        (Python — SEGURIDAD)
Proyecto/src/frontend/src/config.ts        (TypeScript — UX)
Proyeto-Python/Proyecto/app/permisos.py    (Python — UX)
```

Duplicar datos es exactamente lo que uno aprende a no hacer. ¿Por qué acá sí?

Porque **no hay forma de compartirla en tiempo de ejecución sin agregar un paso
de build** (`permisos.py:10-13`), y los tres consumidores la necesitan en su
propio lenguaje. Es una duplicación **deliberada y documentada**, no un
descuido.

### Por qué esta duplicación es peor que la de la paleta

`permisos.py:15-19` hace una observación finísima:

> *"La diferencia con la paleta es que acá desincronizarse **no se ve**: un
> color mal copiado salta a la vista, un permiso mal copiado no. Los síntomas
> son asimétricos y silenciosos."*

Los dos modos de falla (`check_permisos.py:16-19`):

| Divergencia | Síntoma | Gravedad |
|---|---|---|
| Backend **más restrictivo** | El botón aparece y la API responde 403 | Molesto |
| Backend **más permisivo** | La API deja pasar algo que el front creía prohibido | **Grave** |

### La solución: hacerlo verificable

`check_permisos.py` compara las tres copias y falla si difieren.
`check_permisos.py:10-14` explica por qué existe:

> *"permisos.py documenta que es un espejo de config.ts y que desincronizarse es
> silencioso. **Un comentario que pide 'acordate de tocar el otro' es
> exactamente el tipo de regla que nadie cumple a los tres meses.** Esto la
> vuelve verificable en un segundo."*

Y contempla una diferencia **legítima** (`:21-25`): Flet no declara las siete
secciones del portal del socio, porque esas pantallas son de la PWA. Lo que se
exige es que **donde las tres hablen de lo mismo, digan lo mismo**.

Hay además un mapeo explícito para el único caso raro
(`check_permisos.py:48-57`): `recepcion` existe sólo en Flet, y sus endpoints
están protegidos con `Seccion.ASISTENCIA`. Lo que se verifica no es que exista
allá, sino que su nivel en Flet **nunca supere** al de la sección que realmente
la protege — *"si lo superara, un rol vería el panel en el menú y recibiría 403
al abrirlo"*.

### La cuarta copia, y la lección

Apareció una **cuarta** copia escrita a mano en `app/views/usuarios.py`: un
diccionario `PERMISOS_RESUMEN` que la pantalla usaba para explicarle a alguien
qué puede hacer cada rol. `check_permisos.py` **no la miraba**, porque no era
una matriz sino una lista suelta.

Estaba mal **para los cuatro roles** (`views/usuarios.py:30-39`):

| Rol | Decía | Realidad |
|---|---|---|
| Recepcionista | Actividades; omitía 5 secciones | tiene las 5; Actividades no |
| Entrenador | Dashboard, Asistencia, Actividades | ninguna de las tres |
| Nutricionista | Dashboard | no la ve |
| Dueño | faltaba Recepción | la ve |

El comentario viejo decía *"si las dos se contradicen, manda el backend"*. Y la
observación que cierra el tema (`:41-44`):

> *"Es cierto, pero no alcanza: la tarjeta existe para **EXPLICARLE** a alguien
> qué puede hacer cada rol, y **una explicación equivocada es peor que
> ninguna** — manda a discutir con la app en vez de leerla."*

El arreglo no fue agregarle un cuarto chequeo al script. Fue **derivarla**:

```python
# views/usuarios.py:49-63
def _secciones_de(rol: str) -> list[str]:
    salida = []
    for item in NAV_ITEMS:
        nivel = permisos.acceso_a_seccion([rol], item["route"])
        if nivel == permisos.Acceso.NINGUNO:
            continue
        salida.append(item["label"] + ("*" if nivel == permisos.Acceso.LECTURA else ""))
    return salida
```

> *"Derivarla elimina el problema de raíz: **no hay nada que sincronizar**."*

Y marca con `*` las de sólo lectura, porque *"ve Personal"* y *"puede tocar
Personal"* no son lo mismo — una lista que no distingue los dos casos **vuelve a
explicar mal**.

### La regla general, que aplica a todo el proyecto

> **Si podés derivar un dato, derivalo. Si tenés que duplicarlo, hacé que un
> script verifique las copias. Un comentario que pide acordarse no es una
> solución.**

---

# PARTE V — HTTP y el diseño de la API

## 23. Los verbos, y qué promete cada uno

| Verbo | Qué significa | ¿Idempotente? | En OlimpOS |
|---|---|---|---|
| `GET` | Leer, sin efectos | Sí | **61** |
| `POST` | Crear o ejecutar | **No** | **64** |
| `PUT` | Reemplazar completo | Sí | **10** |
| `DELETE` | Borrar | Sí | **3** |

**Que haya sólo 3 DELETE en 138 endpoints no es un olvido: es el diseño.** El
proyecto usa **soft-delete** — nada se borra, se marca como inactivo. Dar de
baja a un socio es un `POST /socios/{id}/baja`, no un `DELETE`, porque:

1. Sus pagos, asistencias y membresías **siguen existiendo** y siguen teniendo
   sentido. Borrar la fila rompería todas esas referencias.
2. Se puede **reactivar**. Y el `CLAUDE.md` lo pide explícitamente: *"soft-delete
   siempre con los dos caminos: baja **y** reactivación desde el principio"*.
3. La pregunta *"¿cuánta gente se dio de baja en marzo?"* necesita que el dato
   exista.

Que haya más POST que GET (64 vs 61) también dice algo: es un sistema **de
gestión**, donde se opera tanto como se consulta.

---

## 24. Los códigos de estado, y qué significa cada elección

Contados sobre el código:

| Código | Usos | Qué comunica |
|---|---|---|
| `404 NOT_FOUND` | 86 | El recurso no existe |
| `400 BAD_REQUEST` | 54 | El pedido está mal formado o viola una regla |
| `409 CONFLICT` | 37 | Choca con el estado actual |
| `201 CREATED` | 31 | Se creó algo nuevo |
| `403 FORBIDDEN` | 17 | Sé quién sos y no podés |
| `401 UNAUTHORIZED` | 3 | No sé quién sos |
| `204 NO_CONTENT` | 3 | Listo, y no hay nada que devolver |
| `402 PAYMENT_REQUIRED` | 2 | Falta pagar |
| `503`, `502` | 1 c/u | Problema de un servicio externo |

### La diferencia 400 vs 409, que es la que más se confunde

- **400**: el pedido está mal. *"La promoción no puede terminar antes de
  empezar."* Con esos datos **nunca** va a funcionar.
- **409**: el pedido está bien, pero **choca con el estado actual**. *"Ese socio
  ya está anotado en esa clase."* Mañana, con otro estado, el mismo pedido
  funcionaría.

Ejemplo real, `actividades.py:369-373`:

```python
if ya:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"{socio.persona.nombre_completo} ya está anotado en esa clase.",
    )
```

### Los tres códigos raros, que son los más interesantes

**`402 PAYMENT_REQUIRED`** (`portal.py:841` y `:849`) es un código que casi nadie
usa. Acá encaja perfecto: el socio quiere reservar un turno y no tiene membresía
activa. Y el mensaje distingue dos situaciones (`portal.py:836-846`): si la
membresía está **suspendida** (congelada), avisa *"reanudala para poder reservar
— **no hace falta que pagues de nuevo**"*. Es la clase de detalle que evita un
reclamo en el mostrador.

**`503 SERVICE_UNAVAILABLE`** (`pagos_online.py:113`): Mercado Pago no está
configurado. No es culpa del cliente (4xx) ni un bug (500): es un servicio que
no está disponible.

**`502 BAD_GATEWAY`** (`pagos_online.py:156`): fallamos al hablar con Mercado
Pago. Es literalmente lo que significa 502 — el intermediario no pudo con el de
más atrás. Y fijate lo que hace **antes** de lanzar:

```python
pago.estado = "CANCELADO"
pago.fecha_cancelacion = datetime.now()
db.commit()
raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, ...)
```

Se creó un `Pago` en PENDIENTE, falló la comunicación, **y se cancela antes de
avisar**. Sin eso quedaría un pago pendiente fantasma que nadie va a cerrar.

---

## 25. Los dos sistemas de modelos, y por qué no es duplicación

Ésta es la pregunta que **siempre** aparece: *"¿por qué tenés `models.py` Y
`schemas.py` si describen lo mismo?"*

**No describen lo mismo.** Describen dos cosas que se parecen:

| | `models.py` (SQLAlchemy) | `schemas.py` (Pydantic) |
|---|---|---|
| Describe | Una **tabla** | Un **mensaje** |
| Habla con | PostgreSQL | El cliente HTTP |
| Valida | Tipos de columna | Rangos, formatos, reglas |
| Tamaño | 1.032 líneas | 1.697 líneas |

### El caso que lo justifica solo

`schemas.py:6-10`:

> *"La tabla `Usuario` tiene `password_hash`, y ese campo **no puede salir
> jamás** en una respuesta. Como `UsuarioOut` simplemente no lo declara, no hay
> forma de que se filtre por olvido — ni siquiera si alguien devuelve el objeto
> ORM entero desde un endpoint."*

```python
# schemas.py:62-74
class UsuarioOut(BaseModel):
    """La cuenta, SIN el hash."""
    model_config = ConfigDict(from_attributes=True)
    id_usuario: int
    id_persona: int
    username: str
    ultimo_acceso: datetime | None = None
    activo: bool
```

Si fueran el mismo objeto, ocultar el hash sería algo que **hay que acordarse de
hacer** en cada endpoint. Siendo dos, es **imposible de olvidar**.

### La validación que el ORM no puede hacer

```python
# schemas.py:43
password_nueva: str = Field(min_length=8)
```

`schemas.py:39-42`: *"min_length en el schema y no en el cuerpo del endpoint:
así el rechazo ocurre **antes de ejecutar una sola línea del router**, y el
mensaje de error lo arma FastAPI solo."*

Y para reglas que involucran **varios campos a la vez**, un `model_validator`
(`schemas.py:421-434`):

```python
@model_validator(mode="after")
def _una_sola_forma_de_descuento(self):
    tiene_porcentaje = self.porcentaje_descuento is not None
    tiene_monto = self.monto_fijo_descuento is not None
    if tiene_porcentaje and tiene_monto:
        raise ValueError("Elegí una sola forma de descuento: porcentaje O monto fijo, no las dos.")
    if not tiene_porcentaje and not tiene_monto:
        raise ValueError("La promoción necesita un descuento: un porcentaje o un monto fijo.")
    return self
```

`schemas.py:405-407` explica por qué esa regla vive ahí:

> *"sin ella se podría cargar una promo con los dos campos y **nadie sabría cuál
> gana al cobrar**, o con ninguno y sería un descuento de cero disfrazado de
> descuento."*

Y el segundo validador (`:436-442`) tiene un matiz que muestra cuidado: admite
`fecha_inicio == fecha_fin`, porque **una promo de un solo día es normal**. Lo
que no puede es terminar antes de empezar.

### Bonus: la documentación sale sola

De los tipos de Pydantic, FastAPI genera un **OpenAPI** completo. Por eso el
`CLAUDE.md` puede verificar contra qué backend estás corriendo contando
endpoints del `openapi.json`.

Eso no es un accesorio: **detectó tres fallos falsos de una corrida entera de
suites** cuando un uvicorn viejo seguía escuchando en el puerto 8000.

---

# PARTE VI — La base de datos desde el código

## 26. ORM — el traductor, y su precio

### La idea

Un **ORM** (*Object-Relational Mapper*) traduce entre filas de SQL y objetos de
Python. En vez de escribir SQL a mano y armar objetos, escribís
`db.query(Socio).filter(...)` y el ORM genera el SQL.

Lo que ganás: seguridad contra inyección SQL (el ORM parametriza siempre), menos
código repetitivo, y portabilidad entre motores.

Lo que perdés: **visibilidad**. Una línea de Python puede disparar 45 consultas
sin que se note. Ese es exactamente el problema que aparece más abajo.

### La decisión de OlimpOS: los modelos MAPEAN, no DEFINEN

Ésta es una decisión que hay que poder defender, porque va **contra** lo que
hace el proyecto de referencia del profesor. `database.py:11-27`:

> *"El esquema de OlimpOS ya existe escrito a mano y normalizado hasta 3FN en
> `Proyecto/db/schema.sql`. Ese archivo es la **ÚNICA fuente de verdad**.
>
> Los modelos SQLAlchemy de `models.py` **MAPEAN** ese esquema, no lo definen.
> Es una diferencia deliberada respecto del proyecto de referencia del profe,
> que crea las tablas desde los modelos con `Base.metadata.create_all()`. Si acá
> hiciéramos lo mismo, los modelos y el DDL entregado podrían **divergir sin que
> nadie se entere**, y la base real dejaría de coincidir con el diagrama
> presentado."*

`create_all()` se sigue llamando en `main.py:117`, pero como **red de
seguridad**: SQLAlchemy sólo crea tablas que no existen y nunca modifica una
existente, así que sobre una base ya cargada es un **no-op**.

> **Nota de mantenimiento:** los comentarios de `database.py:13` y `main.py:113`
> todavía dicen **"35 tablas"**. Son 37. El número quedó viejo cuando se
> agregaron `Congelamiento` y `Promocion`; el resto del razonamiento sigue
> siendo válido.

---

## 27. Sesión, transacción, y la diferencia entre `flush` y `commit`

### La idea

Una **sesión** de SQLAlchemy es una unidad de trabajo: junta los cambios y los
manda a la base cuando se le pide.

```python
# database.py:117
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

Los dos `False` son decisiones, y el segundo muerde:

- `autocommit=False`: nada se confirma solo. Hace falta un `commit()` explícito.
- **`autoflush=False`**: **nada llega a la base hasta que se lo pedís**.

### `flush` vs `commit`

| | Qué hace | ¿Se puede deshacer? |
|---|---|---|
| `flush()` | Manda el SQL a la base, **dentro** de la transacción | **Sí**, con rollback |
| `commit()` | Confirma la transacción | No |

`flush` es "escribilo pero no lo confirmes". Sirve para dos cosas, y las dos
aparecen en OlimpOS:

**1. Necesitás el ID que genera la base.** `socios.py:353`:

```python
db.flush()                       # ahora sí existe id_socio
```

Antes del flush, `socio.id_socio` es `None` — lo asigna PostgreSQL. Si querés
insertar algo que lo referencia, primero tiene que existir.

**2. El ORDEN importa por una restricción de la base.** Éste es el caso fino, y
está en `rutinas.py:342-354`:

```python
# El flush NO es opcional desde la migración 009.
#
# Esa migración agregó un índice único parcial que impide dos asignaciones
# ACTIVA por socio. Un índice parcial no puede ser DEFERRABLE en Postgres,
# así que se evalúa al terminar cada sentencia — y SQLAlchemy ordena su
# flush poniendo los INSERT ANTES que los UPDATE. Sin esto, la fila nueva
# entraría mientras la anterior sigue ACTIVA y la base rechazaría una
# reasignación que es perfectamente válida.
db.flush()
```

Vale la pena desarmarlo porque encadena **tres** conceptos:

1. La migración 009 creó un **índice único parcial**: único *sólo donde* el
   estado es `ACTIVA`. Impide dos rutinas activas del mismo socio.
2. En PostgreSQL, un **índice** no puede ser `DEFERRABLE` (sólo los
   *constraints*, y un constraint no admite condición). Se evalúa al terminar
   **cada sentencia**, no al confirmar.
3. SQLAlchemy, al volcar, **ordena los INSERT antes que los UPDATE**.

Juntando las tres: el INSERT de la rutina nueva entraría **mientras la vieja
sigue ACTIVA**, y el índice rechazaría una reasignación válida. El `flush`
fuerza el UPDATE primero.

`autoflush=False` mordió **dos veces** por esto — la otra fue en la promoción de
la lista de espera, donde el cupo se contaba antes de que la cancelación
estuviera escrita.

### La sesión por request

```python
# database.py:154-165
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

El `yield` en el medio de un `try/finally` es un **generador usado como
contexto**: FastAPI ejecuta hasta el `yield`, le pasa `db` al endpoint, y cuando
termina —**incluso si lanzó una excepción**— corre el `finally`.

`database.py:115-116` marca el motivo de una sesión por request: *"nunca
compartir una sesión entre requests concurrentes, porque **no son thread-safe** y
se pisan las transacciones"*.

---

## 28. El problema N+1 — el bug de rendimiento más común del mundo

### El problema

Es el error clásico del ORM, y en OlimpOS costó **2,88 segundos** medidos.

`roles_de_persona()` lee **seis** relaciones de la Persona. Con carga perezosa
(*lazy loading*), cada relación es una consulta **por fila**:

```
    1 consulta para traer los 8 usuarios
  + 6 consultas por cada uno
  = 45 consultas
```

Se llama **N+1**: una consulta inicial más N por cada resultado.

Y lo que lo hace traicionero: **con pocos datos no se nota**. Con 3 socios es
imperceptible. Con 100, la pantalla tarda medio minuto. `usuarios.py:70`: *"Con
100 socios serían 600."*

Y el costo real no es la base — es **la red**. Cada viaje a Neon cuesta ~44 ms,
así que lo único que importa es **cuántas veces se pregunta**, no qué tan pesada
es cada pregunta.

### Las dos soluciones, y cuándo va cada una

**`selectinload`** — para relaciones uno-a-uno en cadena:

```python
# usuarios.py:82-88
CARGA_DE_ROLES = (
    selectinload(Persona.dueno),
    selectinload(Persona.socio),
    selectinload(Persona.empleado).selectinload(Empleado.entrenador),
    selectinload(Persona.empleado).selectinload(Empleado.nutricionista),
    selectinload(Persona.empleado).selectinload(Empleado.recepcionista),
)
```

Trae las relaciones en **un puñado de consultas extra con `IN (...)`**, sin
importar cuántas filas haya. Resultado: **2,88 s → 0,54 s**.

Y `usuarios.py:77-78` explica por qué `selectinload` y no `joinedload`: *"son
relaciones uno-a-uno en cadena y **el JOIN múltiple duplicaría filas**"*.

**Consulta en lote manual** — cuando lo que hace falta no es una relación sino
una regla:

```python
# socios.py:139
def _listar_socios_en_lote(db: Session, consulta) -> list[SocioOut]:
```

`_a_socio_out` hacía **cuatro** consultas por socio. `socios.py:145-153`:

> *"Con 3 socios eran 14 consultas y 1,4 segundos; con 100 socios serían ~400 y
> la pantalla tardaría medio minuto. (…) Acá se pregunta cinco veces en total,
> sin importar cuántas filas haya."*

El truco de la "membresía vigente" merece mirarse (`socios.py:176-187`):

```python
vigentes: dict[int, Membresia] = {}
filas = (db.query(Membresia)
         .options(selectinload(Membresia.tipo))
         .filter(Membresia.id_socio.in_(ids))
         .order_by(Membresia.fecha_inicio.desc(), Membresia.id_membresia.desc())
         .all())
for m in filas:
    vigentes.setdefault(m.id_socio, m)
```

Se traen **todas** las membresías ordenadas igual que en `_membresia_vigente`, y
`setdefault` se queda con la **primera** de cada socio — que por ese orden es la
vigente. **Mismo criterio, una sola consulta.**

Resultado: **14 consultas / 0,68 s → 6 consultas / 0,34 s**.

### Los dos detalles de método que valen tanto como el arreglo

**1. Se verificó que da lo mismo.** No se confió: se compararon los
`model_dump()` de las dos implementaciones.

**2. No se borró la versión lenta.** `_a_socio_out` se conservó **para el socio
de a uno** (alta, edición, baja), donde cuatro consultas están bien y el código
se lee mejor. Y —esto es lo importante— **los dos caminos comparten
`_estado_socio`** (`socios.py:93`), así que **una regla de derivación no puede
divergir**.

> Ésa es la forma correcta de tener dos implementaciones: que compartan la parte
> que **decide**, y difieran sólo en la que **busca**.

### El bug que casi se cuela, y por qué es peor que un error

`socios.py:162-166`:

> *"Solo relaciones que EXISTEN. Se verificaron con
> `sqlalchemy.inspect(Socio).relationships`: la primera versión de esto inventó
> `Socio.membresias`, el endpoint devolvía 500 y —**como Flet traduce el error a
> una lista vacía**— la grilla se veía **'vacía pero funcionando'**, que es peor
> que un error."*

Un error se ve y se arregla. Una pantalla vacía **parece un dato**.

---

## 29. El pool de conexiones — de dónde salían los "2 segundos de la nada"

### Los números que ordenan todo

Medidos contra la base real, no estimados:

```
    SELECT 1 en una conexión YA abierta ......  44 ms   <- piso físico (RTT)
    Abrir una conexión NUEVA (TLS + auth) .... 825 ms   <- 19x más caro
```

Los 44 ms son **la velocidad de la luz hasta São Paulo** más el ida y vuelta del
protocolo. `database.py:55-58`:

> *"ninguno tiene que ver con Python: son la velocidad de la luz hasta São Paulo
> y el costo de un handshake TLS. Lo único que se puede hacer es **(a) preguntar
> MENOS veces** y **(b) no tener que reconectar nunca**."*

> **La conclusión que hay que poder decir en una defensa:** durante toda la
> request el proceso está **esperando un socket, no calculando**. Reescribir
> esto en Go, Rust o C daría **exactamente los mismos 44 ms**. La elección de
> lenguaje es irrelevante para este problema.

### El bug, y por qué el síntoma era la pista entera

El reporte fue:

> *"si cambio de panel rápido carga al toque, pero si espero un rato vuelve la
> tardanza, y **a veces aparece de la nada**"*

Ese perfil es la firma de **una conexión que se muere sola**. Con
`pool_recycle=-1` (el default) SQLAlchemy no recicla nunca: deja las conexiones
en el pool hasta que alguien del otro lado las cierra —Neon por inactividad, o
el NAT del router por no ver tráfico—. `pool_pre_ping` detecta la conexión
muerta y reconecta de forma transparente: **la app no falla, pero esa request
paga 825 ms**. Y como cada conexión muere en un momento distinto, la lentitud
aparece "de la nada".

### Las cuatro piezas, y qué tapa cada una

```python
# database.py:92-113
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=240,
    pool_size=10,
    max_overflow=5,
    pool_timeout=10,
    connect_args={
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
        "application_name": "olimpos-backend",
    },
)
```

| Pieza | Qué evita |
|---|---|
| `pool_recycle=240` | Reciclar **cuando lo decidimos nosotros** (entre requests) y no cuando lo decide la red (en medio de una) |
| keepalives TCP | Que el NAT dé por muerta una conexión ociosa. Es el caso peor: está "viva" para nosotros y **cortada del otro lado** |
| `pool_size=10` | El pool se llena una vez al arrancar y no vuelve a pagar los 825 ms |
| `pool_pre_ping` | Que una conexión muerta **nunca llegue como error a la pantalla** |

`pool_timeout=10` tiene su propio razonamiento (`database.py:98-100`): el default
es 30 s. *"Preferible enterarse rápido: si el pool se agota hay un problema de
conexiones que no se devuelven, y **esconderlo 30 segundos no ayuda**."*

Y `application_name` (`:109-111`) aparece en `pg_stat_activity` de Neon: si
alguna vez hay conexiones colgadas, **se ve de dónde salieron**.

### El latido

```python
# main.py:79
SEGUNDOS_ENTRE_LATIDOS = 120

# main.py:84-89
def _latido():
    while not _latido_activo.wait(SEGUNDOS_ENTRE_LATIDOS):
        try:
            with engine.connect() as con:
                con.execute(text("SELECT 1"))
        except Exception:
            pass

# main.py:124
threading.Thread(target=_latido, name="latido-neon", daemon=True).start()
```

Neon (plan gratuito) **suspende el compute** tras unos minutos sin consultas, y
despertarlo cuesta segundos. Un `SELECT 1` cada dos minutos alcanza para las dos
cosas: mantiene el compute despierto **y** hace que las conexiones no queden
ociosas lo suficiente como para que las corten.

Cuatro detalles de ese bloque, y cada uno es un concepto:

**1. Un hilo y no una tarea async** (`main.py:72-75`). SQLAlchemy acá es
**síncrono**. Meterlo en el event loop lo bloquearía durante el RTT (~44 ms) cada
dos minutos.

**2. `daemon=True`.** Un hilo daemon **no impide que el proceso termine**. Sin
eso, cerrar el backend colgaría esperando un hilo que nunca termina.

**3. `_latido_activo.wait(120)` en vez de `time.sleep(120)`.** Es un
`threading.Event`: espera 120 segundos **o hasta que alguien lo active**. Al
apagar, `main.py:167` hace `_latido_activo.set()` y el hilo sale **al instante**
en vez de dormir hasta 2 minutos más.

**4. El `except` que no loguea** (`main.py:90-96`). Deliberado: *"Que falle un
latido no es noticia: puede ser un corte de red de un segundo. (…) Un log acá por
cada latido fallido llenaría la consola de ruido durante un corte."*

### Calentar el pool

```python
# database.py:122
def calentar_pool(cantidad: int = 3) -> None:
```

Abre conexiones al arrancar para que **el primero que use la app no pague los
825 ms**. Y el detalle final (`database.py:148-151`): cerrarlas las **devuelve**
al pool, no las destruye. Quedan abiertas contra Neon, listas.

Con una condición de robustez (`:131-134`): si Neon está dormido, **no se
propaga el error**. *"Un arranque que revienta por esto sería peor que un primer
pedido lento."*

---

# PARTE VII — Concurrencia

## 30. Condiciones de carrera — dos personas y el último lugar

### El problema

Dos socios aprietan "reservar" en el mismo milisegundo, para el último lugar de
un turno de cupo 20. El código hace lo obvio:

```
  1. contar las reservas   -> 19
  2. ¿19 < 20?             -> sí
  3. insertar la reserva
```

Si las dos transacciones ejecutan el paso 1 **antes** de que cualquiera llegue
al paso 3, **las dos cuentan 19, las dos pasan el chequeo, y el turno termina
con 21**.

Eso es una **condición de carrera**: el resultado depende del orden en que se
intercalan dos ejecuciones concurrentes.

### El matiz de aislamiento (acá conviene ser preciso)

`actividades.py:338-343` lo explica así:

> *"bajo READ COMMITTED, que es el default de Postgres, cada transacción ve la
> base como estaba cuando empezó — así que las dos cuentan 19 sobre 20 y las dos
> entran."*

**La conclusión es correcta, y el mecanismo conviene decirlo con más
precisión**, porque es exactamente el tipo de repregunta que hace un profesor:

En **READ COMMITTED**, cada **sentencia** ve un snapshot tomado al inicio de
**esa sentencia** (no al inicio de la transacción — eso sería REPEATABLE READ).
La carrera ocurre igual, y por una razón más simple: **ninguna de las dos
transacciones confirmó todavía**, así que ninguna ve el INSERT de la otra, sin
importar cuándo tome su snapshot.

| Nivel | Qué ve cada sentencia | ¿Frena esta carrera? |
|---|---|---|
| READ COMMITTED (default) | Lo confirmado al inicio de **la sentencia** | No |
| REPEATABLE READ | Lo confirmado al inicio de **la transacción** | No por sí solo |
| SERIALIZABLE | Como si fueran en serie | Sí, pero aborta y hay que reintentar |

### La solución: bloqueo de fila

```python
# actividades.py:352-355
turno = (db.query(Turno)
         .filter(Turno.id_turno == id_turno)
         .with_for_update()
         .first())
```

`SELECT ... FOR UPDATE` **bloquea la fila del turno** hasta el final de la
transacción. La segunda transacción **espera** a que la primera confirme, y
recién ahí cuenta: ve 20, y va a la lista de espera **como corresponde**.

Fijate que **no se bloquean las reservas**: se bloquea **el turno**, que es el
recurso que se está repartiendo. Todas las transacciones que quieran reservar en
ese turno pasan por esa fila, así que se serializan entre sí — **y no molestan a
quien reserva en otro turno**.

Ese es el arte del locking: **bloquear lo mínimo que serializa lo que hay que
serializar**.

Aparece tres veces en el proyecto: `actividades.py:354` (el personal anota),
`portal.py:791` (el socio reserva) y `turnos.py:183`.

### Y por qué el trigger no alcanza, ni tampoco el lock solo

Ésta es la parte que hay que poder explicar entera. La migración 006 dice
textualmente qué resuelve y qué no:

**El trigger SÍ resuelve:** un bug de la aplicación que se olvide de contar, un
INSERT hecho a mano desde el SQL Editor, un script de importación, y **bajarle
el cupo a un turno que ya tiene más gente anotada**.

**El trigger NO resuelve la carrera**, porque **también cuenta** — y también
contaría 19 en las dos transacciones. Diferir al commit achica la ventana pero
no la elimina.

| Mecanismo | Tapa | No tapa |
|---|---|---|
| `SELECT ... FOR UPDATE` | La carrera entre transacciones | INSERT manual, script, endpoint nuevo |
| `CONSTRAINT TRIGGER` | Todo lo que no pase por el endpoint | La carrera |

> *"O sea: **el lock evita la carrera, el trigger evita todo lo demás**. Ninguno
> de los dos reemplaza al otro y por eso están los dos."*

### Por qué el trigger es DEFERRABLE

```sql
CREATE CONSTRAINT TRIGGER trg_reserva_cupo
  AFTER INSERT OR UPDATE OF estado, id_turno ON "Reserva"
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION trg_reserva_respeta_cupo();
```

Se evalúa **al confirmar la transacción**, no fila por fila. Y hace falta por un
caso concreto: **mover gente dentro del mismo turno en una sola transacción**
—cancelar a uno y promover a otro, que es exactamente lo que hace la lista de
espera— sin que el **estado intermedio** dispare el error aunque el estado final
sea válido.

Y el trigger tiene una decisión de negocio adentro:

```sql
IF NEW.estado IS DISTINCT FROM 'RESERVADA' THEN
  RETURN NULL;
END IF;
```

`EN_ESPERA` **no ocupa lugar**: *"por definición la lista de espera existe para
los que NO entraron. Si contaran, el turno se vería lleno con gente que no tiene
lugar y **la cola nunca avanzaría**."*

---

## 31. Hilos, el GIL, y por qué acá no molesta

### El problema

Python tiene el **GIL** (*Global Interpreter Lock*): un candado que permite que
**un solo hilo ejecute bytecode a la vez**. La conclusión que todo el mundo saca
es "los hilos en Python no sirven".

### La idea

Esa conclusión es correcta **sólo para trabajo de CPU**. Cuando un hilo hace una
operación de **entrada/salida** —esperar un socket, leer un archivo— **libera el
GIL** mientras espera.

O sea:

- **CPU-bound** (calcular): los hilos no ayudan. El GIL los serializa.
- **I/O-bound** (esperar red): los hilos ayudan **muchísimo**. Están todos
  esperando, no compitiendo.

OlimpOS es **enteramente I/O-bound**. `api_client.py:316-319`:

> *"Van en HILOS PARALELOS y no en serie: son ocho pedidos de ~400ms cada uno.
> En serie serían más de tres segundos; en paralelo, lo que tarde el más lento,
> porque el tiempo es de RED y no de CPU (**por eso el GIL de Python no molesta
> acá: los hilos están esperando el socket, no calculando**)."*

### Los cuatro usos de hilos en OlimpOS

| Dónde | Para qué |
|---|---|
| `main.py:124` | El latido contra Neon |
| `api_client.py:289` | Refrescar el caché sin que nadie espere |
| `api_client.py:352` | Precargar 12 rutas en paralelo al loguearse |
| El pool de FastAPI | Cada endpoint síncrono corre en un worker |

Y **todos los propios** son daemon. Ninguno debe impedir que el programa cierre.

### La sección crítica y el candado

Cuando varios hilos tocan la misma estructura, hace falta un **candado**:

```python
# api_client.py:221
_candado = threading.Lock()

# api_client.py:237-240
def limpiar_cache() -> None:
    global _generacion
    with _candado:
        _cache.clear()
        _generacion += 1
```

Sin el candado, un hilo podría estar leyendo `_cache` mientras otro lo vacía.

Y hay una segunda protección, más sutil (`api_client.py:286-294`):

```python
with _candado:
    if path not in _refrescando:
        _refrescando.add(path)
        threading.Thread(...).start()
```

`_refrescando` garantiza **un solo hilo por ruta**: *"sin este control, entrar y
salir de un panel diez veces dispararía diez pedidos idénticos."*

### Hilos vs async: por qué el backend usa los dos

FastAPI corre sobre un **event loop** async. Un endpoint `async def` que hace una
operación bloqueante **congela el loop entero** — nadie más es atendido.

En OlimpOS, SQLAlchemy es **síncrono**, así que casi todos los endpoints son
`def` normales. FastAPI los corre en un **pool de hilos**, y el loop queda libre.

El webhook, en cambio, es `async def` (`pagos_online.py:277`), porque necesita
`await request.json()` para leer el cuerpo crudo.

> **La regla:** `async def` para operaciones que saben esperar sin bloquear;
> `def` normal cuando la librería es síncrona, y dejás que el framework lo mande
> a un hilo.

---

# PARTE VIII — Rendimiento

## 32. Latencia vs. ancho de banda — la distinción que ordena todo

- **Ancho de banda**: cuántos datos entran por segundo. Se soluciona con plata.
- **Latencia**: cuánto tarda **el primer byte** en llegar. La limita la física.

44 ms hasta São Paulo son **latencia**. No importa si la respuesta pesa 1 KB o
1 MB: el viaje cuesta lo mismo.

De ahí sale la única estrategia posible: **reducir el NÚMERO de viajes, no el
tamaño de cada uno**. Es el hilo que une todo lo anterior:

| Técnica | Cómo reduce viajes |
|---|---|
| Pool de conexiones | Elimina el handshake (825 ms) de casi todos los pedidos |
| `selectinload` | 45 consultas → un puñado |
| Listado en lote | 4 por socio → 5 en total |
| Caché | 1 viaje → 0 |
| Precarga en paralelo | 8 viajes en serie → 8 a la vez |

Y la palanca que queda si algún día hiciera falta más: **acercar la base**. Un
PostgreSQL local baja el RTT a ~1 ms, y —esto es lo elegante— **no toca una sola
línea de código**: sólo `DATABASE_URL`. Está previsto desde el principio en
`database.py:6-9`.

---

## 33. Caché: el intento que falló y el que funcionó

### Intento 1: TTL a secas — y por qué fue un error

Guardar la respuesta 15 segundos y después tirarla. Resultado
(`api_client.py:174-185`):

> *"El síntoma que deja es exactamente el que se reportó: **'si cambiás entre
> paneles rápido cargan al toque, pero si esperás un rato vuelve la
> tardanza'**.
>
> Claro: dentro de la ventana había caché y era instantáneo; pasada la ventana
> se volvía a esperar los 450 ms completos. El caché **escondía el problema en
> vez de resolverlo**, y encima lo volvía **impredecible** — la misma acción
> tardaba distinto según cuánto habías tardado vos en hacerla."*

Eso último es lo importante: un sistema **consistentemente** lento se siente
mejor que uno **impredecible**. La gente se adapta a lo previsible.

### Intento 2: servir-y-refrescar (*stale-while-revalidate*)

> **Se devuelve SIEMPRE lo que hay en caché, al instante, aunque esté vencido.
> Si está vencido, se dispara un refresco EN SEGUNDO PLANO.**

```
    primera visita  ->  se espera (no hay nada que mostrar)
    resto           ->  instantáneo, siempre
```

La pantalla **nunca espera a la red**: en el peor caso muestra datos de hace un
minuto y **se corrige sola**.

```python
# api_client.py:217
FRESCURA = 30

# api_client.py:280-295
if guardado is not None:
    cuando, respuesta = guardado
    if time.monotonic() - cuando > limite:
        with _candado:
            if path not in _refrescando:
                _refrescando.add(path)
                threading.Thread(target=_refrescar_en_segundo_plano, ...).start()
    return respuesta        # ← se devuelve YA, vencido o no
```

Encaja porque los datos de este sistema son de **lectura frecuente y escritura
rara**: *"la grilla de socios se mira cien veces por cada vez que se da de alta
a alguien"*.

> **Detalle de rigor:** `time.monotonic()` y no `time.time()`. El reloj monótono
> **nunca retrocede**; el de pared sí puede (ajuste de NTP, cambio de horario).
> Un caché medido con `time.time()` puede creer que una entrada es del futuro.

### La invalidación, que es la parte difícil

OlimpOS eligió lo simple, **a propósito**:

```python
# api_client.py:360-372
def _post(path, body=None):  limpiar_cache(); return _pedir("POST", path, body)
def _put(path, body):        limpiar_cache(); return _pedir("PUT", path, body)
def _delete(path):           limpiar_cache(); return _pedir("DELETE", path)
```

**Cualquier escritura borra el caché entero**, no sólo la ruta que tocó. El
razonamiento (`api_client.py:201-210`):

> *"Cobrar una membresía cambia `/socios`, `/cobros/socio/{id}`,
> `/dashboard/stats` y `/cobros/deudas` **a la vez**. Invalidar 'sólo lo
> relacionado' exigiría un mapa de dependencias entre rutas mantenido a mano, y
> el día que alguien agregue un endpoint y se olvide de anotarlo, la pantalla
> mostraría un dato viejo **DESPUÉS de cobrar** — que es el único momento en que
> un dato viejo es inaceptable. **Tirar todo cuesta un pedido de más y no se
> puede olvidar.**"*

Es la misma filosofía del middleware CSRF: **elegir el mecanismo que no se puede
olvidar de aplicar**, aunque cueste un poco más.

### El contador de generación — la carrera que casi nadie ve

Éste es el detalle más fino de todo el archivo:

```python
# api_client.py:226
_generacion = 0

# api_client.py:249-253
with _candado:
    if generacion == _generacion:
        _cache[path] = (time.monotonic(), respuesta)
```

El escenario que evita:

```
   t=0    sale un refresco de /socios
   t=1    alguien COBRA una membresía  ->  limpiar_cache()
   t=2    llega el refresco... con datos de t=0, ANTERIORES al cobro
```

Sin el contador, ese refresco **resucitaría un dato viejo justo después de una
escritura**. Con el contador, el refresco ve que la generación cambió y
**descarta su propio resultado**.

### El logout tira el caché — y es seguridad, no rendimiento

```python
# api_client.py:61-72
def limpiar_token() -> None:
    global _token
    _token = None
    limpiar_cache()
```

> *"las respuestas guardadas se trajeron con los permisos de la sesión que se
> está cerrando. Sin este borrado, **un Recepcionista que entrara después del
> Dueño podría leer del caché una respuesta que a él el backend le habría
> negado**."*

Un caché que ignora quién preguntó es un agujero de autorización.

### La precarga

```python
# api_client.py:324-339 — 12 rutas
RUTAS_A_PRECARGAR = (
    "/recepcion/panel",   # primero: es donde aterriza el Recepcionista
    "/socios", "/personal", "/usuarios", "/rutinas", "/nutricion",
    "/cobros/tipos-membresia",
    "/dashboard/stats", "/dashboard/actividad", "/dashboard/socios-recientes",
    "/asistencia/hoy",
    "/promociones?solo_vigentes=true",
)
```

Dos decisiones adentro:

**1. Es una lista de RUTAS, no de funciones** (`api_client.py:321-323`): *"si una
ruta cambia de nombre, esto deja de precargarla y la app sigue andando igual,
sólo que un poco más lenta la primera vez. **Un error acá nunca debe impedir
entrar.**"*

**2. Los 403 no rompen nada** (`:346-349`): un Entrenador no puede ver
`/usuarios`, ese pedido falla, y como `_get` no cachea errores, simplemente no
queda nada. Sin efectos.

### El resultado

```
    seccion         1a vez      2a   tras 35s
    dashboard           9 ms    2 ms     3 ms
    recepcion           1 ms    1 ms     3 ms
    socios              3 ms    1 ms     2 ms
    personal            1 ms    1 ms     2 ms
    usuarios            3 ms    3 ms     4 ms
    TOTAL              19 ms    9 ms    18 ms
```

**4175 ms → 19 ms** para recorrer los nueve paneles. Y el caso que fallaba
—esperar un rato y volver— también quedó instantáneo.

Recepción es el único con frescura corta (5 s en vez de 30): es el panel del
mostrador y **su valor es estar al día**.

---

# PARTE IX — La PWA

## 34. SPA — una sola página que finge ser muchas

En una web tradicional, cada click pide una página nueva al servidor. En una
**SPA** (*Single Page Application*), el navegador carga **una** página y después
**reescribe el contenido** con JavaScript. La URL cambia sin recargar.

Ventaja: las transiciones son instantáneas y el estado sobrevive.
Costo: la primera carga es más pesada, y **hay que reimplementar cosas que el
navegador daba gratis** — como el botón "atrás", o saber qué mostrar cuando
alguien pega una URL directa.

De ahí sale una consecuencia que se nota en OlimpOS: **el F5**.

### El problema del F5, y la rehidratación

Si la sesión vive en memoria de JavaScript, recargar la borra. Solución ingenua:
guardarla en `localStorage`. Pero eso es exactamente lo que **no** se quiere
(`api.ts:64-67`):

> *"Tampoco se guarda la identidad (usuario, persona, roles): eso se le pregunta
> al backend con `GET /me` en cada arranque. **Si los roles vivieran en el
> navegador, alcanzaría con editarlos desde las devtools para verse secciones
> ajenas.**"*

Así que la PWA **no guarda nada** y le pregunta al backend quién es. Eso se llama
**rehidratar**.

Pero trae un problema de tiempos. `App.tsx:53-57`:

> *"Hasta que conteste **no se monta el router**: si se montara, `ProtectedRoute`
> vería `isAuthenticated` en false y redirigiría al login antes de que llegue la
> respuesta, con lo cual el F5 seguiría cerrando la sesión."*

```typescript
// authStore.ts:73 — arranca en true SÓLO si quedaron cookies
isRehidratando: haySesion(),

// App.tsx:61-65
useEffect(() => { void rehidratar(); }, [rehidratar]);
if (isRehidratando) return <Rehidratando />;
```

Y `haySesion()` (`api.ts:95-97`) es un truco elegante: mira **la cookie CSRF**,
porque la de sesión es `httpOnly` y no se puede consultar desde JS. Las dos se
emiten y se borran juntas, así que una alcanza como indicio.

`api.ts:92-93` es honesto sobre qué es eso: *"Es solo una PISTA para evitar un
`GET /me` inútil al arrancar: **la verdad sobre si la sesión sirve la tiene el
backend**."*

---

## 35. El modelo de componentes, y el estado

### La idea

React invierte la forma de pensar la interfaz. En vez de *"cuando pase X,
modificá el elemento Y"*, se declara **cómo se ve la pantalla para un estado
dado**, y React se encarga de aplicar el mínimo cambio.

```
    UI = f(estado)
```

Cambiás el estado, y la interfaz se recalcula. **No se toca el DOM a mano.**

### Estado local vs. global

| | Dónde | Cuándo |
|---|---|---|
| `useState` | Dentro de un componente | Sólo a ese componente le importa |
| Store global (zustand) | Fuera del árbol | Muchos componentes lejanos lo necesitan |

En OlimpOS, la sesión es global (`store/authStore.ts`) porque la necesitan el
sidebar, cada ruta protegida y cada pantalla. El texto de un buscador es local.

### El detalle de zustand que hay que saber

```typescript
// ProtectedRoute.tsx:21-22
const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
const roles = useAuthStore((s) => s.roles);
```

Esa función `(s) => s.isAuthenticated` es un **selector**. El componente se
vuelve a renderizar **sólo si ese pedazo cambió**. Si se hiciera
`const store = useAuthStore()`, se re-renderizaría ante **cualquier** cambio del
store.

### Y una trampa de sincronía que está documentada

`authStore.ts:42-49`:

> *"Devuelve el desenlace del login. Es lo que necesita quien llama para decidir
> a dónde navegar **en el mismo tick** — el `set()` de zustand todavía no se ve
> reflejado en ese render."*

Después de `set({ roles })`, leer `get().roles` en la línea siguiente **no
devuelve el valor nuevo** en ese render. Por eso `login()` **retorna** los roles
en vez de esperar que el llamador los lea del store.

Y tiene **tres** desenlaces, no dos (`authStore.ts:47-48`): además de entrar o
fallar, existe *"credenciales correctas pero falta definir la contraseña"*.

### El guard de rutas

```typescript
// ProtectedRoute.tsx:24-34
if (!isAuthenticated) {
  return <Navigate to={`/${Routes.LOGIN}`} replace />;
}
if (seccion && !puedeVerRuta(roles, seccion)) {
  return <Navigate to={`/${rutaInicialPara(roles)}`} replace />;
}
return <Outlet />;
```

Dos detalles:

**1. No redirige siempre al dashboard** (`:28-31`): *"acá se redirige a la
primera sección que el rol sí pueda ver, que no siempre es el dashboard: **un
Entrenador no lo tiene habilitado**"*.

**2. La ruta de registro se ELIMINÓ, no se ocultó** (`App.tsx:72-76`): *"Se sacó
la ruta y no sólo el link del login: dejando la ruta viva, escribir `/registro`
en la barra de direcciones seguía abriendo la pantalla — que es exactamente el
antipatrón de 'el front esconde pero no rechaza'."*

---

## 36. `useEffect` y sus dos trampas, las dos presentes en el código

### Trampa 1 — la TDZ, que `tsc` da por buena

```typescript
// CobrosView.tsx:182-189
const tipoElegido = tiposMembresia?.find((t) => String(t.id_tipo_membresia) === idTipoElegido);

// Va DESPUES de `tipoElegido` y no junto al resto de los efectos: el array
// de dependencias se evalua durante el render, asi que ponerlo arriba lo
// leeria antes de su `const` y tiraria un ReferenceError por TDZ. No lo
// detecta tsc — la referencia es valida para el compilador, el problema es
// el orden en tiempo de ejecucion.
useEffect(() => { ... }, [idPromocionElegida, tipoElegido]);
```

**El concepto: TDZ** (*Temporal Dead Zone*). Las declaraciones `let` y `const` se
"elevan" (*hoisting*) al principio del bloque, pero quedan **sin inicializar**
hasta que la ejecución llega a la línea. Tocarlas antes tira `ReferenceError`.
(Con `var` no pasa: da `undefined`. Ése es justamente uno de los motivos por los
que `let`/`const` existen.)

Lo traicionero: **el array de dependencias se evalúa DURANTE el render**, no
después. Poner el efecto arriba lee `tipoElegido` antes de su `const`.

Y **TypeScript no lo ve**: para el compilador la referencia es perfectamente
válida. Es un error de **orden en tiempo de ejecución**, no de tipos.

> **La lección general:** `tsc` verifica que los tipos encajen. **No** verifica
> que las cosas pasen en el orden correcto.

### Trampa 2 — la carrera de las respuestas

```typescript
// CobrosView.tsx:194-204
let cancelado = false;
vistaPreviaDescuento(...)
  .then((v) => { if (!cancelado) setPrevia(v); })
  .catch(() => { if (!cancelado) setPrevia(null); });
return () => { cancelado = true; };
```

El escenario: el usuario elige la promo A, sale un pedido; cambia rápido a la B,
sale otro. **Si la respuesta de A llega DESPUÉS de la de B**, pisa el resultado
correcto con uno viejo.

La función que `useEffect` retorna es su **limpieza**: React la ejecuta antes de
volver a correr el efecto. Al marcar `cancelado = true`, la respuesta que llegue
tarde **se descarta sola**.

> Es **la misma idea** que el contador de generación del caché de Flet
> (`api_client.py:226`): una respuesta en vuelo que llega tarde no debe pisar
> algo más nuevo. Dos lenguajes, dos capas, **el mismo problema y la misma
> forma de solución**.

Y el `.catch(() => undefined)` de `CobrosView.tsx:165-168` muestra otro criterio:

> *"Sin snack: quedarse sin promociones no impide cobrar a precio de lista, que
> es el caso normal. Un cartel de error acá alarmaría por algo que no bloquea
> nada."*

**No todo error merece un cartel.**

---

## 37. El cliente HTTP de la PWA

`services/api.ts` es la gemela de `api_client.py`. Mismo rol, mismo contrato
(`api.ts:42-43`).

**Un error tipado, para que las vistas no adivinen** (`api.ts:13-21`):

```typescript
export class ServiceError extends Error {
  status: number;
}
```

**Un timeout, porque `fetch` no tiene** (`api.ts:124-135`):

> *"`fetch` no tiene timeout propio: si el servidor acepta la conexión y después
> no contesta —está reiniciándose, la base quedó colgada— **la promesa nunca se
> resuelve**. Eso dejaba la app clavada en la pantalla de arranque, en negro, sin
> llegar nunca al login."*

15 segundos, y no menos, porque *"el tier gratuito de Neon duerme la base y el
primer pedido después de un rato tarda varios segundos en despertarla"*.

**El detalle de `fetch` que sorprende a todo el mundo** (`api.ts:173-174`):

> *"`fetch` **sólo rechaza por fallo de red, CORS o timeout** — nunca por un
> status 4xx/5xx, que sí llegan como respuesta."*

O sea: un `404` **no** entra al `catch`. Hay que mirar `respuesta.ok`. Es el
error número uno de quien viene de `axios`.

**Y `credentials: 'include'`** (`api.ts:161-171`):

> *"Sin esto el navegador **NO manda la cookie de sesión** en pedidos
> cross-origin (…) Es el complemento obligatorio de `allow_credentials=True` del
> lado del backend."*

Las dos mitades tienen que estar. Una sola no sirve.

**Y la traducción de los dos formatos de error de FastAPI** (`api.ts:100-117`):
los errores normales traen `{detail: "texto"}` y los de Pydantic traen
`{detail: [{msg, loc}, ...]}`. Sin contemplar los dos, *"un 422 mostraría en
pantalla el array de objetos en crudo"*. `api_client.py:104-113` hace lo mismo,
en Python.

---

## 38. TypeScript, y qué garantiza de verdad

TypeScript agrega tipos a JavaScript. Se verifican al compilar y **desaparecen**
al ejecutar: el navegador corre JavaScript común.

Eso define exactamente qué garantiza y qué no:

| Garantiza | NO garantiza |
|---|---|
| Que no llames un método que no existe | Que el backend devuelva lo que decís que devuelve |
| Que no falte un campo obligatorio | Que el orden de ejecución sea correcto (la TDZ) |
| Que un `switch` cubra todos los casos | Nada en tiempo de ejecución |

El segundo punto es el importante: si `SocioOut` dice `nombre: string` pero el
backend manda `null`, TypeScript **no se entera**. Los tipos describen un
**contrato**, y el contrato hay que sostenerlo de los dos lados.

Un uso muy fino en OlimpOS (`config.ts:222-225`):

```typescript
export type SeccionPrivada = Exclude<
  RouteValue,
  typeof Routes.LOGIN | typeof Routes.CAMBIAR_PASSWORD
>;
```

Un tipo **derivado** de otro. Si mañana se agrega una ruta a `Routes`,
`SeccionPrivada` la incluye sola, y `Record<SeccionPrivada, AccesoValue>` obliga
a que **todos los roles declaren su permiso** — si falta uno, no compila.

> Eso es usar el compilador como **verificador de completitud**. No es
> decoración: es la misma idea de "derivar en vez de duplicar", aplicada a los
> tipos.

**Y la trampa del comando** (`CLAUDE.md`):

```bash
npx tsc --noEmit -p tsconfig.app.json   # ojo: SIN -p no compila nada y siempre da OK
```

Sin `-p`, `tsc` no toma la configuración del proyecto, no encuentra archivos y
**siempre da OK**. Un chequeo que siempre pasa es peor que ninguno: da confianza
falsa.

---

## 39. Tailwind v4 y la paleta duplicada

```css
/* index.css:3-32 */
@theme {
  --color-surface-base: #15171C;
  --color-primary-volt: #C6F135;
  ...
}
```

Tailwind v4 **genera las clases utilitarias a partir de esas variables**.
Declarar `--color-surface-base` hace que exista `bg-surface-base`. La paleta se
define **una vez** y el resto del código usa nombres, no hex.

### La duplicación deliberada

El mismo set vive en **tres** lugares:

| Archivo | Para |
|---|---|
| `index.css` (bloque `@theme`) | La PWA |
| `app/config.py` (clase `Colors`) | Flet |
| `vite.config.ts:102-103` (`manifest`) | La app instalada |

El tercero no es redundante y tiene una historia (`vite.config.ts:89-96`):
estaban en violeta y blanco (los defaults de la plantilla). `background_color` es
**lo que pinta la pantalla de arranque de la app instalada**, así que una app
dark-only **arrancaba con un flash BLANCO**. Y `theme_color` tiñe la barra de
estado del celular, que quedaba violeta sobre una app verde y gris.

---

## 40. PWA — qué la hace "instalable"

Tres piezas:

| Pieza | Qué hace |
|---|---|
| **Manifest** | Nombre, íconos, colores, `display: standalone` |
| **Service worker** | Un proxy en el navegador: cachea y permite funcionar offline |
| **Contexto seguro** | HTTPS o `localhost`. **Obligatorio.** |

### Por qué `devOptions` está apagado, y es una decisión

`vite.config.ts:61-84` documenta que se probó y se volvió atrás:

**1. No sirve sobre HTTP.** Chrome y Safari exigen contexto seguro para ofrecer
"Instalar app", así que abriendo por la IP de la red el manifiesto se sirve
**pero la opción no aparece igual**.

**2. El service worker CACHEA**, y en desarrollo eso es un problema: *"un arreglo
de CSS o de JS puede no verse en el teléfono porque el SW devuelve la versión
vieja, y se termina **depurando un bug que ya estaba resuelto**"*.

Y da la salida real: Chrome trata `localhost` como contexto seguro **aunque sea
HTTP**, así que con el celular por USB y port forwarding en `chrome://inspect`
(5173 → localhost:5173) se abre como `http://localhost:5173` y funciona todo.

### Los cuatro íconos y el logo chico

`vite.config.ts:105-119` explica un bug de diseño con geometría adentro:

> Un ícono `maskable` **lo recorta el sistema** con la forma que quiera (círculo,
> cuadrado redondeado, gota), así que su contenido tiene que caber en un círculo
> del 80 % del lado. Para un logo cuadrado eso es **80/√2 ≈ 56 %** del ancho.
>
> Un archivo que cumple esa regla se ve **BIEN recortado** y **ridículamente
> chico** cuando el sistema lo usa como ícono normal.

Antes el **mismo** PNG servía para `any` y para `maskable`. Separados, cada uno
hace lo suyo: los `any` llenan el cuadro al 92 %; los `maskable` van al 58 %
sobre el fondo de la app.

### `100vh` miente en iOS

```css
/* index.css:40-68 */
@supports (height: 100dvh) {
  html, body, #root { height: 100dvh; }
}
```

> *"`100vh` MIENTE en Safari de iOS: incluye el alto de la barra de direcciones,
> que se esconde al scrollear. O sea que el contenedor queda más alto que lo que
> se ve, y el final del contenido queda DEBAJO de la interfaz del navegador."*

`100dvh` (*dynamic viewport height*) es el alto **real** disponible. Y el
`@supports` es **degradación elegante**: si el navegador no lo soporta, cae en
`height: 100%` en vez de quedarse sin altura.

---

# PARTE X — Flet

## 41. UI declarativa en Python

Flet permite escribir interfaces de escritorio en Python. Por debajo usa
**Flutter**: el Python describe el árbol de controles y Flutter lo dibuja.

La consecuencia práctica: **no hay HTML ni CSS**. Un `ft.Text` no es un párrafo
HTML; es un objeto que Flutter pinta en un canvas. Por eso el CSS no aplica, y
por eso el XSS tampoco.

El ciclo es distinto al de React:

| React | Flet |
|---|---|
| Cambiás el estado, React recalcula | Modificás el objeto y llamás `.update()` |
| El framework detecta qué cambió | **Vos** decís qué actualizar |

```python
# router.py:193-196
self._content_ref.current.content = content
self._content_ref.current.update()
```

Sin ese `.update()`, el cambio existe en memoria y **no se ve**.

---

## 42. Las siete trampas de Flet 0.84, y qué concepto enseña cada una

Todas se encontraron **corriendo la app**, no leyendo el código.

### 1. Pegarle dos dígitos al color no da transparencia

```python
# config.py:105
return ft.Colors.with_opacity(opacidad, color)
```

Flet lee el hex de 8 dígitos como **`#AARRGGBB`** — con el alfa **adelante** — y
corre los canales. Sale un color completamente distinto: *"era el motivo de que
los íconos de 'Actividad Reciente' se vieran rojos"*.

> **Concepto: el orden de los canales no es universal.** CSS usa `#RRGGBBAA`;
> Flet (como Flutter y Android) usa `#AARRGGBB`. Asumir uno vale un bug visual
> que no rompe nada y por eso sobrevive.

### 2. El `scroll` va en la Column INTERNA

Una `ft.Column([...], expand=True, scroll=AUTO)` con un hijo `expand=True` hace
que Flet **centre todo verticalmente**, y la pantalla arranca con un hueco enorme
arriba.

Patrón correcto: topbar fijo + `Container(content=Column(..., scroll=AUTO,
expand=True), expand=True)`.

### 3. `ft.Dropdown` usa `on_select`, no `on_change`

`on_change` es del `TextField`. Con el nombre equivocado **no hay error**: el
callback simplemente no se llama nunca.

> **Concepto: el peor error es el que no falla.** Un `AttributeError` se arregla
> en un minuto; un callback que nunca corre se busca media hora.

### 4. `page.fonts` necesita un `.ttf`, no un CSS de Google Fonts

Con el CSS no carga ninguna fuente y todo cae en la del sistema. **Silencioso**:
la app anda, se ve distinta.

### 5. `assets_dir="assets"` es obligatorio

Sin eso, las imágenes por nombre suelto (el logo del sidebar) no se resuelven.

### 6. Las APIs viejas ya están migradas

Se usa `ft.Padding / Border / Margin / BorderRadius` y `ft.run`, no las
minúsculas ni `ft.app`. La app arranca con **cero `DeprecationWarning`**; si
aparece uno, algo se revirtió.

> **Concepto: cero warnings como línea de base.** Con 40 warnings normales, el
> número 41 —el que importa— no lo ve nadie. Mantener el cero es lo que convierte
> un warning en una señal.

### 7. Que la app ARRANQUE no significa que se pueda ENTRAR

Ésta es la más importante, y la que originó una herramienta nueva.

---

## 43. Los tres bugs que sólo se veían haciendo clic

Los tres revientan **al CONSTRUIR una vista** con datos que el backend devuelve
legítimamente. Los tres sobrevivieron a `compileall`, a **nueve** suites de
integración y a un arranque sin un solo warning.

### Bug 1 — el orden de inicialización

```
The application encountered an error: 'NoneType' object is not callable
```

`_load_main_app` (login.py) hacía:

```
    linea 266:  vista_inicial = router.view_class(inicial)
    linea 267:  initial_content = vista_inicial(page=page, router=router).build()
    ...
    linea 284:  router.setup(content_ref)      # ← quien LLENABA el mapa
```

El mapa de rutas se registraba **dieciocho líneas después de usarlo**. Siempre
estaba vacío, `view_class` devolvía `None`, y la línea siguiente hacía
`None(page=...)`. **Rompía el login de los cuatro roles.**

**El arreglo, y por qué no fue el obvio** (`router.py:112-117`):

> *"Se podría haber arreglado subiendo el `setup()` en login.py, pero el problema
> de fondo es que **`setup()` hace dos cosas sin relación**: guardar las
> referencias del layout **Y** registrar las vistas. Registrar no necesita
> ninguna referencia, así que atarlo a ese momento era la causa. Con el registro
> al primer uso, **el orden deja de importar y no hay una segunda forma de volver
> a romperlo desde otro archivo**."*

```python
# router.py:63-64 — idempotente
if self._view_map:
    return

# router.py:119
self._register_views()
```

Y se cerró el otro camino: `_render_view` usa `self.view_class(route)`
(`router.py:182`) en vez de leer `_view_map` directo, *"así las dos entradas
comparten el registro perezoso y no hay una que funcione y otra que no según el
orden"*.

> **Concepto: acoplamiento temporal.** Cuando A tiene que llamarse antes que B y
> nada lo obliga, es cuestión de tiempo. La solución robusta no es acordarse del
> orden: es **eliminar la dependencia**.

### Bug 2 — el `None` que estaba documentado y no implementado

```
TypeError: '>=' not supported between instances of 'NoneType' and 'int'
```

`_texto_delta` hacía `delta_pct >= 0`, y el backend manda `None` cuando el mes
anterior fue cero. **No era un descuido del backend** — está en el docstring de
`_delta` desde que se escribió (`dashboard.py:49-59`):

```python
def _delta(actual: float, anterior: float) -> float | None:
    """
    Variación porcentual. None si no hay base de comparación.

    El caso a evitar es 0 -> 1: matemáticamente es un aumento infinito, y
    mostrar "+100%" sería inventar un dato. La vista, con None, no muestra
    nada, que es lo honesto.
    """
```

**El contrato estaba completo; faltaba implementada una de las dos mitades.**

Y lo decisivo: **la PWA sí la tenía**.

```typescript
// DashboardView.tsx:124-127
function textoDelta(metrica: Metrica, comparacion: string): string | undefined {
  if (metrica.deltaPorcentual === null) return undefined;
  ...
}
// DashboardView.tsx:223
tendencia={(metrica.deltaPorcentual ?? 0) < 0 ? 'down' : 'up'}
```

Era una **asimetría entre gemelas**, no una decisión. Y el arreglo de Flet lo
dice explícitamente (`views/dashboard.py:95-100`):

```python
# `or 0` porque delta_pct puede ser None (…) Mismo `?? 0` que usa
# DashboardView.tsx.
"down" if (m["delta_pct"] or 0) < 0 else "up",
```

Con una base sin historial —o sea, **en cualquier demo**— las cuatro métricas
vienen en `None` y el Dashboard **no abría nunca**.

### Bug 3 — la lista vacía

Nutrición hacía `sum(cals)//len(cals)`. Sin planes cargados,
`ZeroDivisionError` —y `min`/`max` un `ValueError`—, así que la sección entera no
abría **para ningún rol**. Otra vez, la PWA ya lo resolvía con un chequeo de
largo antes de dividir.

> **Concepto: el caso vacío es un caso.** Cero elementos, cero filas, cero mes
> anterior. **Es el estado en el que arranca todo sistema nuevo**, o sea el que
> ve cualquiera que abra el proyecto por primera vez.

### La herramienta que faltaba

Los tres tienen la misma forma, y ninguno de los chequeos existentes podía
verlos. `pruebas_vistas.py:17-24`:

> *"Los dos sobrevivieron a `compileall`, a las 9 suites de integración y a que
> la app arrancara sin un solo warning. Porque **las suites prueban el BACKEND
> por HTTP: nunca instancian una vista de Flet**. Y `compileall` no ejecuta.
>
> Lo que faltaba era esto: **llamar a `build()` de cada vista con una sesión real
> de cada rol**. No verifica que la pantalla se vea bien —para eso hay que
> abrirla— pero sí que se pueda **ABRIR**, que es justo lo que fallaba."*

25 combinaciones (rol × sección), segundos de ejecución. Y conviene correrla
**también con la base vacía**, que es donde estos tres se disparan.

> **Encontré una cosa acá:** `pruebas_vistas.py:34` tiene la raíz **hardcodeada**
> a `D:/OlimpOs/Proyeto-Python/Proyecto`, que es la ruta de la otra PC. En esta
> máquina ese directorio no existe. Hoy funciona igual —Python agrega el
> directorio del script a `sys.path` por su cuenta— pero es frágil y contradice
> lo que promete `EMPEZAR-EN-OTRA-PC.md`. Se arregla derivándola del propio
> archivo con `pathlib.Path(__file__).parent`.

---

# PARTE XI — ¿Por qué hay tantas formas distintas de hacer algo simple?

Ésta es una de las preguntas más incómodas que te pueden hacer, y merece su
propia parte porque **la respuesta no es "porque sí"**. En cada caso hay una
razón nombrable, y son cinco razones distintas.

## Razón 1 — Porque cada cliente tiene amenazas distintas

**El caso:** dos formas de mandar la sesión.

```
    PWA   ->  cookie httpOnly + header X-CSRF-Token
    Flet  ->  Authorization: Bearer
```

Parece inconsistencia. Es diseño. La PWA corre en un navegador y tiene **dos
problemas que Flet no tiene**: XSS (hay páginas donde inyectar scripts) y CSRF
(hay cookies ambiente y "otros sitios"). Flet no tiene ninguno de los dos.

> Darle cookies a Flet **no agregaría seguridad** y le sumaría la complejidad del
> CSRF sin motivo (`cookies.py:32-34`).

**La regla:** *una defensa que no corresponde a una amenaza real es ceremonia.*

---

## Razón 2 — Porque el mismo dato tiene que existir en tres lenguajes

**El caso:** la matriz de permisos, en Python (backend), TypeScript (PWA) y
Python (Flet).

No hay forma de compartirla en tiempo de ejecución **sin agregar un paso de
build**. Y la copia del backend hace algo distinto de las otras dos: **decide qué
se ejecuta**, no qué se dibuja.

**La regla:** *si tenés que duplicar, hacelo explícito y verificable.* De ahí
`check_permisos.py`. Y donde **se pueda derivar**, derivar — que es lo que se
hizo con la cuarta copia.

Lo mismo con la paleta: vive en `index.css`, `config.py` y el manifest. La
diferencia, anotada en `permisos.py:15-19`, es que **el color mal copiado se ve y
el permiso mal copiado no**. Por eso uno tiene script y el otro no.

---

## Razón 3 — Porque cada capa tapa un agujero que la otra no puede

**El caso:** el cupo de un turno, defendido tres veces.

Ninguna de las tres es redundante:

| Defensa | Tapa | No tapa |
|---|---|---|
| Botón deshabilitado | El caso normal | Un `curl` |
| `SELECT ... FOR UPDATE` | La carrera entre transacciones | Un INSERT manual |
| `CONSTRAINT TRIGGER` | Todo lo que no pase por el endpoint | La carrera |

Lo mismo con los permisos (frontend esconde / backend rechaza) y con la
idempotencia del webhook (el `if` + el UNIQUE del esquema).

**La regla:** *si dos defensas tapan exactamente lo mismo, una sobra. Si tapan
cosas distintas, hacen falta las dos.* La pregunta correcta no es "¿esto ya está
validado?" sino **"¿qué caso tapa esta capa que la otra no puede?"**.

---

## Razón 4 — Porque el ORM y el HTTP describen cosas distintas

**El caso:** `models.py` y `schemas.py`.

Una tabla y un mensaje **no son lo mismo**, aunque se parezcan. `Usuario` tiene
`password_hash` porque la tabla lo necesita; `UsuarioOut` no lo declara porque el
mensaje **no puede** llevarlo.

Y `schemas.py` es **más grande** que `models.py` (1697 vs 1032 líneas), lo cual
tiene sentido: una tabla tiene una forma, pero los mensajes son muchos —
`SocioCrear`, `SocioEditar`, `SocioOut` tienen campos distintos aunque hablen del
mismo socio.

**La regla:** *dos cosas que cambian por motivos distintos deben poder cambiar
por separado.* Agregar una columna interna no debería cambiar la API; cambiar el
formato de una respuesta no debería tocar la base.

---

## Razón 5 — Porque la primera solución obvia falla, y hay registro de eso

**El caso:** el caché.

TTL a secas **se probó y se descartó**, porque reproducía la queja original.
Servir-y-refrescar la resolvió. Las dos son "cachear"; sólo una funciona para
este problema.

Lo mismo con:

| Primera idea | Por qué falló | Lo que quedó |
|---|---|---|
| Token en `sessionStorage` | Robable con XSS | Cookie `httpOnly` + CSRF |
| `pool_pre_ping` solo | Reconectaba en medio de una request (825 ms) | + `pool_recycle` + keepalives + latido |
| `_a_socio_out` en un bucle | N+1: 4 consultas por socio | Listado en lote |
| Un PNG para `any` y `maskable` | El logo se veía chico | Cuatro archivos |
| `is_admin()` booleano en Flet | Bloqueaba en silencio | Matriz + snackbar que explica |
| `PERMISOS_RESUMEN` a mano | Mal para los 4 roles | Derivado de la matriz |
| Subir el `setup()` en login.py | Dejaba la trampa armada | Registro perezoso e idempotente |

**La regla:** *el código que sobrevive no es el primero que se escribe.* Y las
versiones descartadas valen: por eso están anotadas en los comentarios y en la
bitácora, no borradas.

---

## Y una razón que NO aparece en este proyecto

Vale nombrarla porque es la más común en otros: **"porque quedó así"**.

En OlimpOS, cada duplicación que encontrás tiene un comentario explicando por qué
existe. Eso no es prolijidad: es lo que permite **borrarla con confianza** el día
que la razón deje de aplicar. Una duplicación sin explicación no se puede tocar,
porque nadie sabe si el motivo sigue vigente.

> Si te preguntan *"¿esto no está duplicado?"*, la respuesta correcta nunca es
> "sí, pero anda". Es: **"sí, por [razón], y está verificado por [mecanismo]"**.

---

# PARTE XII — Cómo se verifica que esto funciona

## 44. Los cinco niveles, y qué caza cada uno

Lo más valioso de este proyecto no es que tenga pruebas: es que **está
documentado qué NO ve cada nivel**.

| Nivel | Comando | Caza | **NO caza** |
|---|---|---|---|
| Compilación | `compileall` | Error de sintaxis | Import faltante, división por cero |
| Import real | `python -c "import main"` | Import faltante al cargar | Un nombre usado sólo dentro de una función |
| AST | script a medida | Nombres sin importar | Errores de lógica |
| Suites (9) | `pruebas/test_*.py` | Reglas de negocio del backend | **Cualquier cosa de la UI** |
| Vistas | `pruebas_vistas.py` | Que cada pantalla ABRA | Que se vea bien |

### Las tres reglas que costaron caro

**1. "Compilar no es correr."**

> *"`python -m compileall` compila pero no ejecuta: un import faltante pasa el
> chequeo y revienta al arrancar. Y un nombre usado sólo dentro de una función
> tampoco lo detecta el import — eso ya mordió **tres** veces (la última:
> `input_field` en `views/cobros.py`)."*

Y la herramienta que sí lo caza: **parsear con `ast`** y comparar los `Name`
cargados contra los importados y los ligados localmente.

**2. "Correr no alcanza si no verificás contra QUÉ corrés."**

Un `uvicorn` que no pudo tomar el puerto 8000 **muere en silencio** y el proceso
viejo sigue atendiendo. Una corrida entera dio **tres fallos falsos** por eso. Se
detecta comparando la cantidad de endpoints del `openapi.json`.

**3. "Que el proceso levante no significa que la pantalla funcione."**

Los tres bugs de la Parte X. De ahí nació `pruebas_vistas.py`.

### El agujero de las suites que nadie esperaba

`test_patologias.py` **cubría** el caso —el socio cargaba "Asma"— pero le pasaba
el `ID_ASMA` que había leído **el entrenador**, por una variable de Python. En la
app real esa variable no existe: el socio no tenía forma de listar el catálogo,
porque `GET /patologias` exige `VER_HISTORIAL_MEDICO` y el rol Socio lo tiene en
`false`.

Un **endpoint completo e inusable**.

> *"La lección no es 'la suite estaba mal escrita'. Es que **una prueba que arma
> su escenario con un solo token no puede detectar un permiso faltante entre dos
> roles**: el guard nunca se ejerce porque el dato viaja por el costado."*

El arreglo fue `GET /portal/catalogo-patologias`, guardado por
`Seccion.MI_PERFIL`. **No** se le aflojó el permiso al endpoint de gestión, y ahí
está el patrón que quedó establecido:

> **Cuando el portal necesita un catálogo que vive detrás de un permiso de
> gestión, se republica recortado; no se afloja el permiso del otro lado.**

## 45. Por qué las suites corren contra la base de verdad

No son unitarias: corren contra Neon, con el backend levantado y **la base
vacía**. Cada una arma su propio escenario.

Dos de ellas tocan la base **directamente por SQL**, y el motivo es exacto:
*"para que una cuota venza hay que esperar un mes, y **para probar que la base
frena un INSERT hay que hacer ese INSERT sin pasar por la app**"*.

Una prueba que sólo pasa por HTTP **no puede verificar una defensa de la base**,
porque el endpoint la evita.

Y `vaciar_base.py` tiene una lección de SQL adentro: usa `TRUNCATE ... RESTART
IDENTITY CASCADE` sobre todas las tablas en **UNA sola sentencia**, y las tres
cosas son necesarias:

- `RESTART IDENTITY` porque las suites imprimen ids, y comparar dos corridas es
  imposible si una arranca en `id_socio=1` y la otra en 47.
- `CASCADE` por las 67 foreign keys.
- **Una sola sentencia** porque entre las tablas hay **ciclos de FK** y truncarlas
  de a una falla igual.

---

# PARTE XIII — Autoexamen

Si podés contestar estas veinte sin mirar, entendiste el sistema.

**Criptografía**
1. ¿Están cifradas las contraseñas? *(Trampa: no. Están hasheadas, y es más fuerte.)*
2. ¿Por qué bcrypt y no SHA-256?
3. ¿Para qué sirve la sal y por qué se guarda dentro del hash?
4. ¿Se puede leer el contenido de un JWT sin la clave? *(Sí. Está firmado, no cifrado.)*
5. ¿Qué pasa si alguien edita el campo `roles` de su token?
6. ¿Por qué HS256 y no RS256 acá?
7. ¿Por qué `compare_digest` y no `==`?
8. ¿Qué protege el HMAC del webhook que no protege el HTTPS?

**Sesión y web**
9. ¿Por qué la cookie de sesión es `httpOnly` y la de CSRF no?
10. Explicá el CSRF con un ejemplo, y por qué el doble envío lo frena.
11. ¿CORS protege a tu servidor? *(No. Protege al usuario. `curl` lo ignora.)*
12. ¿Por qué el proxy de Vite y no apuntar `fetch` al backend?
13. ¿Qué pasa si desactivás una cuenta? ¿Y si le cambiás el rol? *(Uno es inmediato, el otro no.)*

**Datos y concurrencia**
14. ¿Qué es un N+1 y por qué no se nota en desarrollo?
15. Dos personas reservan el último lugar a la vez. ¿Qué pasa y qué lo frena?
16. ¿Por qué el trigger de cupo no alcanza, si ya cuenta?
17. ¿Cuál es la diferencia entre `flush` y `commit`, y por qué hay uno en `rutinas.py:354`?

**Arquitectura**
18. ¿Por qué hay 3 copias de la matriz de permisos y cómo evitás que diverjan?
19. ¿Por qué `models.py` y `schemas.py` si describen lo mismo? *(Trampa: no describen lo mismo.)*
20. ¿Por qué un caché con TTL fue un error y qué lo reemplazó?

---

## Las diez ideas que atraviesan todo el proyecto

Si tuvieras que quedarte con diez frases, son éstas. Cada una aparece en varias
capas distintas, que es lo que las vuelve principios y no trucos.

1. **El frontend esconde, el backend rechaza.** Todo lo que corre en la máquina
   del usuario es negociable.
2. **Hacé que el error sea imposible, no que esté prohibido.** El middleware que
   no se puede saltear, el schema que no declara el campo, el UNIQUE en la base.
3. **Fallá seguro.** El default de `requiere_seccion` es el restrictivo; el
   webhook sin secreto rechaza todo; el backend sin `JWT_SECRET_KEY` no arranca.
4. **Derivá en vez de guardar.** Los roles, el estado del socio, el resumen de
   permisos. Un dato derivado no puede contradecir a su fuente.
5. **Si duplicás, hacelo verificable.** `check_permisos.py` existe porque un
   comentario que pide acordarse no es una solución.
6. **Cada defensa tiene que tapar algo que las otras no.** Si no, sobra.
7. **La regla vive en la estructura, no en un `if`.** El `if` se puede olvidar de
   copiar; el constraint no.
8. **El caso vacío es un caso.** Cero filas, cero mes anterior, cero planes. Es
   el estado inicial de todo sistema.
9. **El cuello de botella es la red, no el lenguaje.** Preguntar menos veces y no
   esperar la respuesta son las dos únicas palancas.
10. **Casi todos los bugs aparecieron corriendo, no leyendo** — y los peores, no
    al correr sino **al hacer clic**.

---

## Cómo verificar cualquier número de este archivo

Ninguna cifra de acá hay que creerla. Todas se cuentan:

```bash
# Endpoints por verbo
grep -rhn "@router\.\(get\|post\|put\|delete\)" backend/routers/*.py \
  | sed 's/.*@router\.\([a-z]*\).*/\1/' | sort | uniq -c

# Total de endpoints
grep -rc "@router\." backend/routers/*.py | awk -F: '{s+=$2} END {print s}'

# Códigos de estado usados
grep -rho "status\.HTTP_[0-9_A-Z]*" backend/ --include="*.py" | sort | uniq -c | sort -rn

# Tablas: los tres lados tienen que dar 37
grep -c "^CREATE TABLE" Proyecto/db/schema.sql
grep -c "__tablename__" backend/models.py

# Dónde aparece cada primitiva criptográfica
grep -rn "bcrypt\|hmac\|secrets\.\|jwt\." backend/ --include="*.py"

# Las tres copias de la matriz dicen lo mismo
cd backend && .venv/Scripts/python.exe check_permisos.py
```

---

*Verificado contra el código el 25 de agosto de 2026 — rama `desarrollo`,
commit `e7c1275`. Compañero de `OlimpOS-masterclass-modelo-de-datos.md`.*
