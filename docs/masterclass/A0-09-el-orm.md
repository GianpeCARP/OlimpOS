# A0-09 · El ORM

*Piso del capítulo: las consultas emitidas, contadas una por una.*

Un ORM es la capa que deja escribir `socio.persona.telefonos` en vez de SQL. Es una de las
abstracciones más cómodas de todo el stack y, en un sistema con la base a 44 ms de viaje,
una de las más peligrosas: cada punto de esa expresión puede ser una consulta, y el código
no lo muestra. Este capítulo baja hasta el SQL que cada línea de Python manda a la base,
para que ese costo deje de ser invisible.

### Cómo se obtuvo el SQL de este capítulo

Ninguna consulta de este capítulo está escrita de memoria. Todas salieron de correr **los
modelos reales del repo** —`Persona`, `Socio` y `Telefono`, importados tal cual de
`backend/models.py`— contra una base SQLite **en memoria**, creada y destruida en cada
corrida, con un escucha que anota cada sentencia antes de mandarla. Nunca se tocó Neon: el
motor de `database.py` se crea al importar, pero no se conecta hasta que alguien lo usa.

La diferencia de base cambia la **forma de escribir** algunos detalles —SQLite marca los
parámetros con `?` y Postgres con nombres— pero no la **cantidad ni la forma** de las
consultas, porque eso lo decide el ORM antes de hablar con la base. Lo que se cuenta acá es
exactamente lo que se cuenta contra Neon.

---

## Mapeo objeto-relacional y relación

### El problema de origen

Un programa orientado a objetos piensa en **grafos**: un socio *tiene* una persona, que
*tiene* teléfonos, y se llega de uno a otro siguiendo referencias en memoria. Una base
relacional piensa en **tablas**: filas sueltas que se relacionan por valores iguales en
columnas de [clave foránea](A0-07-bases-de-datos-relacionales.md#clave-foránea-y-acción-referencial).
Ninguno de los dos modelos está mal, pero no encajan: esa distancia se conoce desde los
años noventa como el **desajuste de impedancia objeto-relacional**, tomando prestada la
expresión de la electricidad.

Sin un ORM, cada lectura se escribe a mano dos veces: el SQL que trae las filas y el código
que convierte cada fila en un objeto y conecta los objetos entre sí. Es trabajo mecánico,
repetitivo y propenso a errores, y se repite en cada pantalla.

Martin Fowler sistematizó las soluciones en *Patterns of Enterprise Application
Architecture* (2002), y cuatro de los patrones de ese libro son exactamente las cuatro
secciones de este capítulo: el **mapeador de datos** (esta sección), la **unidad de
trabajo** y el **mapa de identidad** (la sesión), y la **carga perezosa**. SQLAlchemy, que
Mike Bayer publicó en 2006, es una implementación de esos patrones en Python.

### Qué es mapear

Mapear es declarar, una sola vez, que una clase corresponde a una tabla y cada atributo a
una columna. De ahí en adelante el ORM escribe el SQL. Una clase de `backend/models.py` es
eso: una declaración de correspondencia.

En este repo el mapeo tiene una dirección que no es la habitual, y está explicada en el
docstring de `backend/database.py:11-27`: **los modelos mapean el esquema, no lo
definen.** La fuente de verdad es `db/schema.sql`, escrito a mano; `models.py` lo describe.
Muchos proyectos hacen lo contrario —escriben los modelos y dejan que el ORM cree las
tablas con `create_all()`— y el docstring explica por qué acá no: los modelos y el DDL
entregado *"podrían divergir sin que nadie se entere"*. `create_all()` se sigue llamando
al arrancar, pero como red de seguridad: sólo crea tablas que no existen y nunca modifica
una existente. Cómo se mantienen de acuerdo el esquema y los modelos es tema de
[el modelo de datos](A-05-modelo-de-datos.md).

### La relación: una clave foránea convertida en atributo

La clave foránea es una columna con un número. La **relación** es el atributo que convierte
ese número en el objeto al que apunta. `backend/models.py:126`:

```python
telefonos = relationship("Telefono", back_populates="persona")
```

y del otro lado, `models.py:147`:

```python
persona = relationship("Persona", back_populates="telefonos")
```

`back_populates` une los dos lados en memoria: agregar un teléfono a `persona.telefonos`
actualiza `telefono.persona`, y al revés, sin que nadie escriba nada.

La [cardinalidad](A0-07-bases-de-datos-relacionales.md#tabla-fila-columna-y-cardinalidad)
se traduce en la forma del atributo. Una relación uno-a-muchos es una **lista**
(`persona.telefonos`). Una uno-a-uno se declara con `uselist=False` y es un **objeto o
`None`** (`persona.usuario`, `persona.socio`, `persona.empleado` y `persona.dueno`, en
`models.py:122-125`).

> **↓ Capa 1 — qué SQL implica cada atributo.**

Cada relación es, en el fondo, una consulta ya escrita que espera su momento. Estas son las
dos que implican `socio.persona` y `persona.telefonos`, tal como las emitió SQLAlchemy
(recortadas las columnas, que son todas las de la tabla):

```sql
SELECT "Persona".id_persona, "Persona".dni, …  FROM "Persona"  WHERE "Persona".id_persona = ?
SELECT "Telefono".id_telefono, …              FROM "Telefono" WHERE ? = "Telefono".id_persona
```

La primera va de muchos a uno: conoce el `id_persona` del socio y busca **una** persona.
La segunda va de uno a muchos: conoce el `id_persona` y busca **todos** los teléfonos que lo
tienen como clave foránea.

Fijate además en las comillas dobles de `"Persona"` y `"Telefono"`: los nombres de tabla de
`schema.sql` llevan mayúscula, y Postgres baja a minúsculas todo nombre sin comillas. El
ORM las pone siempre, y por eso `Persona` y `persona` serían, para la base, dos tablas
distintas.

### Tres opciones de relación que el repo usa, y por qué

- **`cascade="all, delete-orphan"`**, una sola vez en todo el archivo:
  `Rutina.ejercicios` (`models.py:581-582`). Quitar un ejercicio de la lista de la rutina
  borra su fila, y borrar la rutina borra todos sus ejercicios. Está sólo ahí porque es el
  único caso donde el hijo no tiene ninguna existencia sin el padre: una línea de
  "4 × 12 de sentadilla" no significa nada fuera de su rutina. Un teléfono, en cambio, se
  borra con reglas propias (el principal que asciende), así que nadie quiere que se borre
  solo.
- **`viewonly=True`** en `Socio.entrenadores` (`models.py:344`): la relación se puede leer
  pero el ORM se niega a escribir a través de ella. Asignar un entrenador tiene reglas
  —fechas, estado, una sola asignación activa— que viven en su endpoint, y una relación de
  sólo lectura impide que alguien las saltee con un `append`.
- **Nada de `lazy=`** en ninguna de las relaciones. Ese silencio es una decisión, y es el
  tema de [la carga perezosa](#carga-perezosa-contra-carga-ansiosa).

---

## Sesión y mapa de identidad

### El problema de origen

Si cada asignación a un atributo mandara un `UPDATE` a la base, cambiar tres campos de una
persona serían tres viajes. Y si el programa pidiera dos veces la misma fila, tendría dos
objetos distintos para una sola persona: cambiar uno no cambiaría el otro, y guardar los
dos pisaría uno con el otro.

La **sesión** resuelve las dos cosas. Es la **unidad de trabajo** de Fowler: un espacio
donde el programa lee y modifica objetos libremente, y que recién al final traduce todo lo
que cambió en el SQL mínimo necesario.

### La sesión de este sistema

`backend/database.py:117`:

```python
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

Y el comentario que la precede (`database.py:115-116`): *"una sesión por request: nunca
compartir una sesión entre requests concurrentes, porque no son thread-safe y se pisan las
transacciones"*. Cada pedido recibe la suya por
[inyección de dependencias](A0-10-python-del-lado-del-servidor.md#inyección-de-dependencias),
con `get_db()` (`database.py:154-165`), que la abre, la presta y la cierra siempre, aunque
el endpoint haya lanzado una excepción.

Los dos parámetros de `sessionmaker` merecen una lectura precisa, porque ninguno hace lo
que su nombre sugiere a primera vista:

- **`autocommit=False` no hace nada.** En SQLAlchemy 2.0, que es la versión instalada
  (2.0.51), el modo *autocommit* se eliminó: el parámetro sólo acepta `False`, y pasarle
  `True` levanta `ArgumentError: autocommit=True is no longer supported` (verificado). Es
  un resto de la versión 1.x, inofensivo.
- **`autoflush=False` sí hace algo, y es lo contrario del valor por defecto**, que es
  `True`. Con `autoflush=True`, antes de cada consulta la sesión manda a la base los
  cambios pendientes, para que la consulta los vea. Con `False`, no: hay que pedirlo a mano
  con `flush()`. Por eso el backend tiene **32 llamadas a `db.flush()`**, que en la
  configuración por defecto casi no harían falta. La línea es textualmente la del
  tutorial clásico de bases de datos de FastAPI, y el repo no documenta por qué la
  conserva; su efecto se ve en la [sección de `flush`](#flush-contra-commit).

### El mapa de identidad

Adentro de la sesión hay un diccionario: por cada fila cargada, la clave primaria apunta
al objeto que la representa. Es el **mapa de identidad**, y garantiza que **una fila es un
solo objeto** mientras dure la sesión.

> **↓ Capa 1 — lo que se ve al pedir dos veces la misma fila.**

```python
a = db.query(Persona).filter(Persona.dni == "90000001").one()
b = db.get(Persona, a.id_persona)
a is b                                  # True
```

Consultas emitidas: **una.**

```sql
[1] SELECT "Persona".id_persona, … FROM "Persona" WHERE "Persona".dni = ?   ('90000001',)
```

`a is b` es `True`: no son dos objetos iguales, es **el mismo objeto**. Y la segunda línea
no mandó nada a la base: `db.get()` busca primero en el mapa de identidad, y como esa clave
primaria ya estaba, devolvió el objeto que había sin viajar. Con Neon, eso es un viaje de
44 ms que no se paga.

La diferencia entre las dos formas de pedir importa: `db.get(Modelo, id)` consulta el mapa
primero, y `db.query(...).filter(...)` va siempre a la base (aunque, si la fila ya estaba,
igual devuelve el objeto existente en vez de crear otro).

### El cambio detectado

El otro trabajo de la sesión es **darse cuenta sola** de qué cambió. Cuando se carga un
objeto, la sesión guarda una copia del estado de cada atributo; al modificarlo, lo marca
como sucio.

> **↓ Capa 2 — el cambio detectado, en el piso.**

```python
p = db.get(Persona, 1)
p.apellido = "Garcia Ruiz"
db.dirty          # IdentitySet([<models.Persona object at 0x…>])
db.flush()
```

Consultas emitidas por el `flush`: **una.**

```sql
[1] UPDATE "Persona" SET apellido=? WHERE "Persona".id_persona = ?   ('Garcia Ruiz', 1)
```

Nadie escribió un `UPDATE`. La sesión comparó el estado actual del objeto con la copia que
guardó al cargarlo, vio que sólo cambió `apellido`, y mandó un `UPDATE` **de esa columna
sola**, no de las doce que tiene la tabla. Ese es el mecanismo completo: una comparación
contra una foto tomada al leer.

### Vuelta al repo

El alta de socio usa esta detección en un lugar concreto. `backend/routers/socios.py:403-404`:

```python
db.flush()                       # ahora sí existe id_socio
socio.numero_socio = _numero_socio(socio.id_socio)
```

El número de socio visible se arma a partir del id que asigna la base, así que recién se
puede calcular después de que el `INSERT` viajó. La segunda línea modifica un objeto que
**ya está en la base**, y no hay ningún `UPDATE` escrito: la sesión lo marca como sucio y
lo manda junto con todo lo demás en el `commit()` de la línea 434.

---

## `flush` contra `commit`

### El problema de origen

El alta de un socio crea una `Persona`, después un `Socio` que apunta a esa persona, y
quizás un `Usuario` y un teléfono que también apuntan a ella. Hay dos requisitos que tiran
para lados opuestos:

- **Todo o nada.** Si falla la creación del usuario, no puede quedar una persona suelta sin
  socio. Esto pide una sola
  [transacción](A0-07-bases-de-datos-relacionales.md#transacción-acid-commit-y-rollback)
  que se confirme al final.
- **El id antes del final.** El `Socio` necesita el `id_persona` para su clave foránea, y
  ese número lo asigna la base al insertar
  ([identidad generada](A0-07-bases-de-datos-relacionales.md#clave-primaria-e-identidad-generada)).
  Esto pide mandar el `INSERT` de la persona **antes** de terminar.

La salida es separar dos operaciones que parecen una: **mandar** los cambios a la base y
**confirmarlos**.

### La diferencia, en el piso

- **`flush()`** manda a la base los `INSERT`, `UPDATE` y `DELETE` pendientes, **dentro de
  la transacción abierta**. La base los ejecuta, asigna los ids y aplica las
  restricciones, pero nada es definitivo: todavía se puede deshacer.
- **`commit()`** hace un `flush()` de lo que falte y **cierra la transacción**. Desde ahí es
  permanente. Qué garantiza exactamente la base en ese momento es tema de A0-07.

> **↓ Capa 1 — el INSERT enviado contra la transacción cerrada.**

```python
nueva = Persona(dni="90000099", nombre="Prueba", apellido="Flush")
db.add(nueva)
nueva.id_persona                        # None
db.flush()
nueva.id_persona                        # 4
db.rollback()
# en una sesión nueva:
db.query(Persona).filter_by(dni="90000099").first()   # None
```

Antes del `flush`, el objeto no tiene id: sólo existe en Python. Después del `flush`, tiene
el `4`, que asignó la base, así que la fila **existió** en la base. Después del
`rollback`, una sesión nueva no la encuentra: existió sólo adentro de una transacción que
nunca se confirmó.

Ese es el contrato completo: `flush` hace que la base *vea* el cambio; `commit` hace que el
cambio *quede*.

### Vuelta al repo

`alta_socio` (`backend/routers/socios.py:303`) es la versión de producción de ese
experimento, y el comentario de las líneas 346-348 lo dice con la misma precisión: *"flush
y no commit: manda el INSERT para que la base asigne el id_persona, pero deja la
transacción abierta. Si algo falla más abajo, se deshace todo junto."*

La secuencia completa:

| Línea | Qué hace | Por qué |
|---|---|---|
| 349 | `db.flush()` | para tener el `id_persona` |
| 361 | `db.flush()` | el contacto de emergencia, si vino |
| 403 | `db.flush()` | para tener el `id_socio` |
| 404 | `socio.numero_socio = …` | cambio detectado, sin `UPDATE` escrito |
| 434 | `db.commit()` | **una sola** confirmación para todo |

Tres envíos y una confirmación. Si cualquier paso entre la línea 349 y la 434 levanta una
excepción —por ejemplo el `409` del email repetido, en la línea 377—, `get_db()` cierra la
sesión sin haber confirmado y la base descarta la persona, el socio y el contacto juntos.

Y la cuenta en todo el backend: **32 `flush()` y 101 `commit()`**. Que haya tantos commits es
coherente con el diseño —cada endpoint que escribe confirma lo suyo al final—, y tiene una
consecuencia que ya se pagó una vez en este proyecto: como los endpoints hacen su propio
`commit()`, envolverlos en una transacción externa para "probar sin ensuciar la base" no
protege nada. Es la trampa que A0-07 explica en su sección de transacciones.

---

## Carga perezosa contra carga ansiosa

### El problema de origen

Cargar un `Socio` plantea una pregunta sin respuesta obvia: ¿se trae también su persona?
¿Los teléfonos de la persona? ¿Su cuenta de usuario, sus membresías, los tipos de esas
membresías, sus reservas, los turnos de esas reservas? El grafo de objetos está conectado,
y seguir todas las relaciones desde un socio termina trayendo media base.

Hay dos respuestas extremas, y el patrón de Fowler se llama como la primera:

- **Carga perezosa:** no traer nada que no se pidió. La relación queda como una promesa, y
  se consulta **recién cuando alguien toca el atributo**.
- **Carga ansiosa:** traer por adelantado lo que se sabe que se va a usar.

La perezosa es la correcta por defecto: nunca trae de más. Su problema aparece en una sola
situación, y esa situación es la [sección siguiente](#n1).

### El valor por defecto del repo

**Ninguna relación de `backend/models.py` declara `lazy=`.** Todas usan el valor por
defecto de SQLAlchemy, `lazy="select"`: perezosas. La carga ansiosa no se declara en el
modelo sino **en cada consulta que la necesita**, con `.options(selectinload(...))`.

Es la decisión correcta y vale la pena ver por qué. Si la ansiedad se declarara en el
modelo, cada consulta de `Socio` en todo el sistema —incluida la que sólo quiere el nombre
para un cartel— traería la persona, los teléfonos y las membresías. Declarándola en la
consulta, cada pantalla paga sólo lo que usa.

> **↓ Capa 1 — qué pasa al tocar un atributo perezoso.**

El atributo `socio.persona` no es un valor guardado: es un **descriptor**, un objeto que
Python consulta cada vez que se lee ese atributo. La primera vez, el descriptor ve que la
relación no está cargada, arma la consulta y la manda. Las siguientes, devuelve lo que ya
trajo. Por eso la consulta no aparece en el código: aparece en el momento de **leer**.

> **↓ Capa 2 — la carga ansiosa con `selectinload`, en el piso.**

Con tres socios cargados, este código:

```python
socios = db.query(Socio).options(
    selectinload(Socio.persona).selectinload(Persona.telefonos)
).all()
for s in socios:
    _ = [t.numero for t in s.persona.telefonos]
```

emite **tres consultas, siempre**:

```sql
[1] SELECT "Socio".id_socio, …    FROM "Socio"
[2] SELECT "Persona".id_persona, … FROM "Persona"  WHERE "Persona".id_persona IN (?, ?, ?)   (1, 2, 3)
[3] SELECT "Telefono".id_persona, … FROM "Telefono" WHERE "Telefono".id_persona IN (?, ?, ?)  (1, 2, 3)
```

La jugada de `selectinload` está en las consultas 2 y 3: después de traer los socios, junta
**todos** los `id_persona` que necesita y los pide en una sola consulta con `IN`. Después
hace lo mismo con los teléfonos de esas personas. El bucle posterior ya no dispara nada:
todo está en el mapa de identidad.

> **↓ Capa 3 — el límite de la tanda.**

"Siempre tres" tiene una letra chica. SQLAlchemy 2.0.51 parte la lista del `IN` en **tandas
de 500 ids** (`SelectInLoader._chunksize`, verificado en el entorno del backend). Con 499
socios son tres consultas; con 1.000 son cinco, porque cada relación necesita dos tandas.

La cantidad deja de ser constante en sentido estricto, pero crece de a una cada 500 filas,
y un gimnasio tarda mucho en llegar ahí. El
[listado en lote de A-11](A-11-rendimiento.md#listado-en-lote) cuenta esto sobre la grilla
real de socios.

### `selectinload` y no `JOIN`

Hay otra forma de carga ansiosa, `joinedload`, que trae todo en **una sola** consulta con
`JOIN`. Parece mejor —una consulta en vez de tres—, y el repo no la usa en ningún lado.
El motivo tiene que ver con cómo un `JOIN` arma su resultado:

- Juntar una tabla con otra **uno-a-uno** da una fila por fila de la primera. Sin problema.
- Juntar con una **uno-a-muchos** repite la fila del padre por cada hijo: una persona con
  tres teléfonos vuelve **tres veces**.
- Juntar con **dos** relaciones uno-a-muchos a la vez multiplica: una persona con tres
  teléfonos y dos contactos de emergencia vuelve **seis veces**, y la base manda por la red
  seis copias de cada dato de la persona.

`selectinload` no tiene ese problema: cada tabla viene en su consulta, cada fila una sola
vez. Paga con más viajes —uno por relación— pero en cantidad fija. La grilla de socios
carga teléfonos y contactos de emergencia juntos, que es exactamente el caso que hace
explotar el `JOIN`.

### Nota marcada · la razón que da `usuarios.py`

`backend/routers/usuarios.py:76-78` justifica la elección así: *"Se elige sobre `joinedload`
porque son relaciones uno-a-uno en cadena y el JOIN múltiple duplicaría filas."*

Las dos mitades de la frase no se sostienen entre sí. Las relaciones de roles
—`Persona.dueno`, `Persona.socio`, `Persona.empleado` y los cuatro subtipos de empleado—
**son** uno-a-uno, y como se vio arriba, un `JOIN` de relaciones uno-a-uno **no** duplica
filas: devuelve una por persona. Si la carga fuera sólo de roles, el motivo escrito no
justificaría nada.

Pero la carga ya no es sólo de roles. `CARGA_DE_ROLES` (`usuarios.py:82-93`) termina con
`selectinload(Persona.telefonos)`, que se agregó después —su propio comentario explica por
qué— y **esa sí es uno-a-muchos**. Con los teléfonos adentro, un `JOIN` repetiría cada
persona una vez por teléfono. La conclusión del comentario hoy es verdadera, pero por una
razón distinta de la que escribe: **no duplican los roles, duplican los teléfonos.**

La decisión fue buena en los dos momentos; lo que quedó desalineado es la justificación
con el código que tiene debajo. Es el riesgo típico de los comentarios que explican el
porqué: el código cambia y el porqué no se relee. Cuánto cuesta cargar los roles es tema
de [los seis roles](A-06-los-seis-roles.md).

---

## N+1

### El problema

La carga perezosa es correcta para un objeto. Se vuelve catastrófica en un **bucle**.

```python
for s in db.query(Socio).all():
    _ = [t.numero for t in s.persona.telefonos]
```

Es el mismo código de la sección anterior, **sin** el `selectinload`. Parece idéntico en
comportamiento, y en resultado lo es. En consultas no.

> **↓ Capa 1 — las consultas contadas, una por una.** Este es el piso del capítulo.

Con los mismos tres socios:

```sql
[1] SELECT "Socio".id_socio, …     FROM "Socio"
[2] SELECT "Persona".id_persona, … FROM "Persona"  WHERE "Persona".id_persona = ?   (1,)
[3] SELECT "Telefono".id_telefono, … FROM "Telefono" WHERE ? = "Telefono".id_persona  (1,)
[4] SELECT "Persona".id_persona, … FROM "Persona"  WHERE "Persona".id_persona = ?   (2,)
[5] SELECT "Telefono".id_telefono, … FROM "Telefono" WHERE ? = "Telefono".id_persona  (2,)
[6] SELECT "Persona".id_persona, … FROM "Persona"  WHERE "Persona".id_persona = ?   (3,)
[7] SELECT "Telefono".id_telefono, … FROM "Telefono" WHERE ? = "Telefono".id_persona  (3,)
```

**Siete consultas contra tres.** La primera trae la lista; después, **por cada socio**, el
bucle toca `s.persona` (una consulta) y `.telefonos` (otra). Es el patrón que le da nombre al
problema: **1** consulta para la lista, más **N** por los elementos. Con dos relaciones
tocadas por vuelta, la fórmula exacta es 1 + 2N; con *k* relaciones, 1 + *k*·N.

Con 3 socios la diferencia es 7 contra 3. Con 100, es 201 contra 3. Y la cantidad de
consultas perezosas crece con cada socio que se da de alta, mientras la ansiosa no se
mueve.

### Por qué se esconde

El N+1 es difícil de ver por tres razones que se suman:

- **El código es correcto.** No hay un error que buscar: el bucle devuelve exactamente lo
  que tiene que devolver.
- **No hay un SQL a la vista.** La consulta aparece al leer un atributo, y leer un atributo
  no parece una operación cara.
- **En desarrollo no se nota.** Con tres socios cargados y la base en la misma máquina, 7
  consultas o 3 tardan lo mismo: nada. El problema aparece con datos reales y base remota,
  que es justamente cuando ya está en producción.

Lo que lo vuelve grave en este sistema es la distancia: cada consulta cuesta un viaje de
44 ms hasta São Paulo. Los números medidos sobre la grilla de socios real —14 consultas y
1,4 segundos con tres socios, cuando se armaba de a uno— están en
[base remota](A-11-rendimiento.md#base-remota) y en
[listado en lote](A-11-rendimiento.md#listado-en-lote), que es la respuesta que el repo le
dio.

### Cómo se detecta: contando

La herramienta que produjo todas las consultas de este capítulo sirve igual para cazar un
N+1 en cualquier endpoint, y son cinco líneas:

```python
from sqlalchemy import event

consultas = []

@event.listens_for(engine, "before_cursor_execute")
def _anotar(conn, cursor, sql, params, context, executemany):
    consultas.append(sql)
```

El evento `before_cursor_execute` se dispara justo antes de que cada sentencia salga hacia
la base. Si la lista crece con la cantidad de filas, hay un N+1. Si queda fija, no. Así se
midieron los números que cita `usuarios.py:72` —*"8 cuentas → 45 consultas → 2,88 s"*— y
los del docstring de la grilla de socios: contando, no estimando.

### Vuelta al repo: dónde la carga perezosa está bien

No toda lectura perezosa es un N+1. En `alta_socio`, `persona.socio is not None`
(`socios.py:362`) y `persona.usuario is not None` (`socios.py:411`) son cargas perezosas:
cada una dispara una consulta. Y está perfecto, porque es **un** objeto, no un bucle. Traer
esas relaciones con `selectinload` no ahorraría nada.

La regla que sale de este capítulo es corta: **la carga perezosa sirve para un objeto; en
un listado, cualquier relación que se toque adentro del bucle tiene que estar en
`selectinload`.** El comentario de `usuarios.py:80-81` lo dice como advertencia: *"esto hay
que repetirlo en CADA listado que llame a roles_de_persona"*.

---

## Con qué se conecta

- **Es la misma idea que…** el [listado en lote](A-11-rendimiento.md#listado-en-lote):
  la carga ansiosa es el mecanismo del ORM, y el listado en lote es la decisión de
  rendimiento que lo aplica.
- **Es el mismo problema que…** los 825 ms de una conexión nueva
  ([pool de conexiones](A-11-rendimiento.md#pool-de-conexiones)): viajes de ida y vuelta, a
  dos escalas distintas.
- **Existe por culpa de…** la [base remota](A-11-rendimiento.md#base-remota): con Postgres
  en la misma máquina, el N+1 sería un detalle y no un problema de producto.
- **Es la misma idea que…** la
  [transacción](A0-07-bases-de-datos-relacionales.md#transacción-acid-commit-y-rollback):
  la sesión acumula cambios y los confirma juntos, igual que la base acumula escrituras y
  las confirma juntas.
- **Se contradice con…** `autoflush=False`: el valor por defecto de SQLAlchemy es `True`, el
  repo lo apaga, y lo paga con 32 `flush()` escritos a mano.
