# A0-08 · SQL, índices y planes de consulta

> **Piso de este capítulo: la página de 8 KB leída del disco, y las comparaciones
> contadas una por una.** Más abajo que eso —el sector físico, el firmware del SSD, el
> protocolo del bus— ya no explica nada de OlimpOS: la base corre en Neon y nadie de este
> repo va a tocar un disco. Más arriba que eso tampoco alcanza, porque sin saber que la
> unidad de lectura es la página no se entiende por qué un índice existe.

Este capítulo se apoya en [tabla, fila, columna y cardinalidad](A0-07-bases-de-datos-relacionales.md#tabla-fila-columna-y-cardinalidad),
[clave primaria](A0-07-bases-de-datos-relacionales.md#clave-primaria-e-identidad-generada),
[clave foránea](A0-07-bases-de-datos-relacionales.md#clave-foránea-y-acción-referencial),
[restricción y tipo enumerado](A0-07-bases-de-datos-relacionales.md#restricción-y-tipo-enumerado),
[normalización (3FN)](A0-07-bases-de-datos-relacionales.md#normalización-3fn) y
[transacción, ACID, commit y rollback](A0-07-bases-de-datos-relacionales.md#transacción-acid-commit-y-rollback),
todos definidos en A0-07. Acá no se vuelven a definir: se usan.

**Una aclaración de método, antes de empezar.** Este capítulo se escribió en modo sólo
lectura contra un repositorio cuya base tiene datos reales de producción. **No se corrió
`EXPLAIN` ni ninguna otra consulta.** Todo lo que se afirma sobre planes sale de leer las
definiciones de índice de `db/schema.sql` y las condiciones de filtro del código, y de
aplicarles las reglas documentadas del planificador de PostgreSQL 14 (`db/schema.sql:4`
declara esa versión mínima). Donde eso no alcanza para afirmar algo, el texto lo dice.

---

## SQL, JOIN y agregación

### El problema del que nació

Antes de 1970 los datos se guardaban en modelos jerárquicos y de red (IMS, CODASYL), y
consultarlos era **navegar**: el programa abría un archivo, seguía un puntero al registro
padre, recorría la cadena de hijos y comparaba a mano. El programa no decía qué quería:
decía cómo recorrer. Consecuencia: si alguien cambiaba el orden físico de los registros o
agregaba un índice, había que reescribir los programas.

Edgar Codd publicó en 1970 *A Relational Model of Data for Large Shared Data Banks*
proponiendo lo contrario: que el programa describa **qué conjunto de filas quiere**, y que
el sistema decida cómo obtenerlo. Donald Chamberlin y Raymond Boyce implementaron esa idea
como lenguaje en IBM en 1974 con el nombre SEQUEL, que por un conflicto de marca quedó en
SQL.

Eso es lo único que hay que retener para leer el resto del capítulo: **SQL es declarativo**.
`SELECT count(*) FROM "Reserva" WHERE id_turno = 12 AND estado = 'RESERVADA'` no dice si
hay que leer toda la tabla o saltar a un índice. Dice qué filas cuentan. Quién decide el
cómo es el planificador, y ese es el último apartado de este capítulo.

### Las tres cosas que hay que saber pedir

**Filtrar.** `WHERE` recorta filas. Es la parte que los índices pueden acelerar y la única
que el planificador puede resolver de más de una manera.

**Cruzar (`JOIN`).** La [normalización](A0-07-bases-de-datos-relacionales.md#normalización-3fn)
partió los hechos en tablas distintas para no repetirlos; el `JOIN` es lo que los vuelve a
juntar en la fila de salida. Se cruza por la condición que la
[clave foránea](A0-07-bases-de-datos-relacionales.md#clave-foránea-y-acción-referencial)
ya declara. Hay dos variantes que importan acá:

- `INNER JOIN` (el `JOIN` a secas): si no hay pareja del otro lado, la fila desaparece del
  resultado.
- `LEFT JOIN`: si no hay pareja, la fila se conserva y las columnas del otro lado vienen en
  `NULL`.

La diferencia no es cosmética, y el repo tiene el caso escrito. En `db/schema.sql:1277-1281`,
adentro de la función `trg_reserva_respeta_cupo()`:

```sql
SELECT t.cupo_maximo, a.nombre
  INTO v_cupo, v_actividad
FROM "Turno" t
LEFT JOIN "Actividad" a ON a.id_actividad = t.id_actividad
WHERE t.id_turno = NEW.id_turno;
```

Es `LEFT` y no `INNER` porque lo que se necesita de verdad es `t.cupo_maximo`; el nombre de
la actividad es sólo para el mensaje de error de la línea 1280. Con un `INNER JOIN`, un
turno cuya actividad se hubiera borrado en la misma transacción devolvería **cero filas**,
`v_cupo` quedaría en `NULL` y el control de cupo se saltearía entero por culpa de una
columna decorativa. El `LEFT` asegura que el cupo llegue aunque el nombre no. La línea 1281
lo cierra con `coalesce(v_actividad, 'sin actividad')`, que es exactamente admitir que el
`NULL` es posible.

**Resumir (agregación).** `count()`, `sum()`, `max()` y compañía colapsan muchas filas en un
valor. Sin `GROUP BY` colapsan todo el conjunto filtrado en una sola fila; con `GROUP BY`
colapsan un valor por cada grupo distinto de las columnas agrupadas.

El repo usa las dos formas y en los dos casos la decisión está argumentada en el código.

Sin agrupar, `db/schema.sql:1289-1291`:

```sql
SELECT count(*) INTO v_ocupados
FROM "Reserva"
WHERE id_turno = NEW.id_turno AND estado = 'RESERVADA';
```

Agrupando, `backend/routers/dashboard.py:212-219` · `ingresos_por_periodo()`. El código
arma `func.date_trunc(unidad, Pago.fecha_pago)`, filtra por `Pago.estado == "CONFIRMADO"` y
agrupa por ese mismo truncado. La construcción de la consulta es trabajo del ORM
(→ [A0-09](A0-09-el-orm.md)); lo que importa acá es el SQL que representa —un `SUM` con
`GROUP BY date_trunc(...)`— y el motivo, escrito en el docstring, `backend/routers/dashboard.py:194-196`:

> *"La agrupación la hace la BASE (date_trunc + group by) y no Python: con un año de pagos
> serían miles de filas viajando desde São Paulo para devolver doce números."*

Esa frase es el principio operativo de todo el backend en una línea: **agregar donde están
los datos y mover el resultado, no mover los datos para agregarlos acá.**

> **↓ Capa 2 — qué le pasa a ese texto adentro de Postgres.** Salteable si ya lo sabés.
>
> El texto de la consulta entra por una conexión y atraviesa cuatro etapas antes de
> devolver nada:
>
> 1. **Análisis sintáctico.** El texto se convierte en un árbol. Acá se detecta un `SELCT`
>    mal escrito y nada más: todavía no se sabe si `"Reserva"` existe.
> 2. **Análisis semántico.** Cada nombre se resuelve contra el catálogo del sistema
>    (`pg_class`, `pg_attribute`): la tabla pasa a ser un identificador numérico, la columna
>    un número de atributo y un tipo. Acá se levanta "column does not exist".
> 3. **Reescritura.** Se aplican reglas y se expanden las vistas. En este esquema no hay
>    vistas, así que esta etapa no hace nada.
> 4. **Planificación y ejecución.** El árbol se convierte en un **plan**: un árbol de nodos
>    ejecutables. El ejecutor lo recorre pidiéndole filas al nodo raíz, que se las pide a
>    sus hijos, hasta que el nodo de más abajo lee páginas.
>
> **El piso de este concepto está justo ahí: la fila que el nodo de más arriba devuelve.**
> Todo lo demás de este capítulo es sobre cómo el nodo de más abajo consigue las suyas.

### Lo que la agregación permitió no guardar

`backend/routers/actividades.py:130-134` · `_clases_usadas()` cuenta las reservas de una
inscripción en vez de leer un contador:

```python
def _clases_usadas(db: Session, id_inscripcion: int) -> int:
    return (db.query(func.count(Reserva.id_reserva))
            .filter(Reserva.id_inscripcion == id_inscripcion,
                    Reserva.estado.in_(("RESERVADA", "EN_ESPERA")))
            .scalar()) or 0
```

El comentario de `backend/routers/actividades.py:122-128` dice por qué: `clases_restantes`
**era** una columna y se eliminó. Contar es la única fuente de verdad, así que no hay
contador que se pueda desincronizar, y cancelar una reserva libera la clase sola por dejar
de contar. Es el mismo criterio que encabeza el esquema en `db/schema.sql:24-27`: *"no
guardar lo que se puede derivar"*.

Lo que se paga por esa elección se ve recién en el último apartado de este capítulo, y no
es gratis.

---

## Página de 8 KB

### El problema del que nació

Ni un disco mecánico ni un SSD saben devolver "el byte 4.211". Los dos leen bloques: el
mecánico porque el cabezal tiene que posicionarse y esperar a que el sector pase por
abajo, el SSD porque la unidad de lectura de la NAND es una página física del chip. Pedir
un byte y pedir cuatro kilobytes cuesta prácticamente lo mismo.

Un sistema de base de datos que ignorara eso sería absurdamente lento: leería una fila,
pagaría el bloque entero, tiraría el resto y volvería a pedir otro bloque para la fila
siguiente. Así que Postgres adopta el bloque como **su** unidad y lo llama página. El
tamaño se fija al compilar, y el valor por omisión —el que Neon sirve, y no hay nada en
este repo que lo cambie— es **8192 bytes**.

La consecuencia es la frase que hay que memorizar: **Postgres no lee filas, lee páginas.**
Leer una fila de `Asistencia` es leer las 8 KB que la contienen, con las otras ciento
diecinueve filas que hayan caído ahí adentro.

> **↓ Capa 2 — qué hay adentro de una página de montón.** Salteable si ya lo sabés.
>
> Una página de tabla (Postgres la llama *heap page*, página de montón) tiene cuatro zonas,
> y las filas crecen desde el final hacia el principio mientras el directorio crece desde
> el principio hacia el final:
>
> | Zona | Tamaño | Qué guarda |
> |---|---|---|
> | `PageHeaderData` | 24 bytes | Punteros a la zona libre, número de WAL, suma de verificación |
> | Punteros de línea | 4 bytes cada uno | Un directorio: posición y largo de cada fila dentro de la página |
> | Espacio libre | lo que quede | Donde crece cada lado |
> | Tuplas | variable | Las filas, escritas desde el fondo hacia arriba |
>
> El puntero de línea es la razón por la que una fila se puede mover adentro de su página
> sin que ningún índice se entere: el índice apunta al par (número de página, número de
> puntero), no al byte.
>
> Cada fila lleva además su propio encabezado de 23 bytes, alineado a 24, con los
> identificadores de transacción que deciden qué versión de la fila ve cada sesión (es lo
> que hace posible lo que A0-07 define como
> [transacción, ACID, commit y rollback](A0-07-bases-de-datos-relacionales.md#transacción-acid-commit-y-rollback)).

> **↓ Capa 3 — cuántas filas de este repo entran en una página.** Salteable si ya lo sabés.
>
> Hagamos la cuenta con `Asistencia`, una de las tablas que más crecen del esquema (una fila por
> cada vez que alguien ficha). Su definición está en `db/schema.sql:704-712`:
>
> | Columna | Tipo | Bytes |
> |---|---|---|
> | `id_asistencia` | `integer` | 4 |
> | `id_socio` | `integer` | 4 |
> | `id_sede` | `integer` | 4 |
> | `id_reserva` | `integer` | 4 |
> | `fecha_hora_ingreso` | `timestamp` | 8 |
> | `fecha_hora_egreso` | `timestamp` | 8 |
> | `metodo_registro` | `metodo_registro` (enumerado) | 4 |
> | `id_registrado_por` | `integer` | 4 |
>
> Suman 40 bytes de datos. Sumale 24 de encabezado de fila y 4 del puntero de línea: **68
> bytes por fila**. La página tiene 8192 menos los 24 de su encabezado, o sea 8168
> utilizables.
>
> ```
> 8168 / 68 ≈ 120 filas de Asistencia por página
> ```
>
> Con eso, cincuenta mil fichajes ocupan `50.000 / 120 ≈ 417` páginas, es decir unos
> **3,4 MB**. Ese número es el que hay que tener en la cabeza para el apartado siguiente:
> recorrer `Asistencia` entera de punta a punta son 417 lecturas de página, no cincuenta
> mil.
>
> Un matiz que no cambia el orden de magnitud pero conviene saber: muchas de esas lecturas
> no llegan al disco. Postgres mantiene su propia memoria compartida de páginas y abajo
> está el caché del sistema operativo; una página caliente se sirve de memoria. **El piso
> declarado de este capítulo es la página leída del disco**, y ahí paramos: si está en
> memoria o no cambia cuánto tarda, no cambia cuántas páginas hacen falta, y es lo segundo
> lo que decide si conviene un índice.

---

## Índice B-tree

### El problema del que nació, con números

Sin índice, responder `WHERE id_socio = 812` sobre `Asistencia` sólo se puede hacer de una
manera: leer todas las páginas, y dentro de cada una comparar el `id_socio` de cada fila
contra 812. Con cincuenta mil filas son **cincuenta mil comparaciones y 417 lecturas de
página**. Eso es búsqueda lineal: el costo crece proporcional a la cantidad de filas. En
notación de órdenes, O(n).

La primera idea obvia —mantener la tabla ordenada por `id_socio` y hacer búsqueda binaria—
resuelve la lectura y arruina la escritura: insertar un fichaje en el medio obligaría a
correr todo lo que viene después. Con 417 páginas, una inserción costaría cientos de
escrituras.

Rudolf Bayer y Edward McCreight publicaron la salida en 1972 (el trabajo es de 1970, en los
laboratorios de Boeing): el **B-tree**, un árbol ordenado que se mantiene balanceado solo
—todas las hojas quedan a la misma profundidad— y cuyos nodos tienen el tamaño de un bloque
de disco. Esa última decisión es la clave, y es la que conecta este apartado con el
anterior: el nodo mide lo que mide una página **porque la unidad de costo es la página**.
Un nodo con cientos de claves adentro se lee al mismo precio que uno con dos.

Postgres usa una variante llamada B+tree: las claves de verdad viven todas en las hojas, y
los niveles de arriba son sólo señalizadores. Todo índice de este esquema es de ese tipo;
en `db/schema.sql` no hay ningún `USING gin`, `USING gist` ni `USING hash`.

> **↓ Capa 2 — cómo se recorre, con las comparaciones contadas.** Este es el piso del
> concepto. Salteable si ya lo sabés.
>
> Tomemos `Asistencia_id_socio_fecha_hora_ingreso_idx`, definido en `db/schema.sql:1140`
> sobre `(id_socio, fecha_hora_ingreso)`.
>
> **Cuántas claves entran en una página de índice.** La entrada tiene 8 bytes de
> encabezado, 4 del `integer`, 4 de relleno para alinear el `timestamp` a 8, y 8 del
> `timestamp`: 24 bytes, más 4 del puntero de línea, **28 bytes por clave**. La página de
> índice pierde 24 bytes de encabezado y 16 de la zona especial que guarda los punteros al
> hermano izquierdo y derecho, así que quedan 8152:
>
> ```
> 8152 / 28 ≈ 291 claves por página llena
> con el factor de relleno por omisión de las hojas (90 %) ≈ 260 claves
> ```
>
> **Cuántos niveles tiene el árbol.** Con un abanico de 260:
>
> | Niveles | Filas que alcanza a indexar |
> |---|---|
> | 1 | 260 |
> | 2 | 67.600 |
> | 3 | 17.576.000 |
> | 4 | 4.569.760.000 |
>
> Cincuenta mil fichajes entran en **dos niveles**: una raíz y una capa de hojas.
>
> **Cuántas comparaciones cuesta.** Adentro de cada página, Postgres hace búsqueda binaria
> sobre las claves ordenadas: ⌈log₂ 260⌉ = **9 comparaciones por página**. Dos niveles son
> **18 comparaciones**. Después hay que ir a buscar la fila al montón, que es **una lectura
> de página más** por cada fila devuelta.
>
> El balance completo, para el mismo `WHERE id_socio = 812` sobre 50.000 filas:
>
> | | Comparaciones | Lecturas de página |
> |---|---|---|
> | Sin índice | 50.000 | 417 |
> | Con índice | 18 | 2 del índice + 1 por fila devuelta |
>
> **De 50.000 a 18.** Eso es pasar de O(n) a O(log n), y esta tabla es el piso del
> capítulo: no "es más rápido", sino cincuenta mil contra dieciocho.
>
> **Y ahora la parte que explica por qué el B-tree sigue siendo la estructura correcta
> cuando la tabla se hace grande.** Multipliquemos el gimnasio: dos mil socios que van tres
> veces por semana generan unos 312.000 fichajes por año.
>
> | Filas | Niveles | Comparaciones | Comparaciones sin índice |
> |---|---|---|---|
> | 50.000 | 2 | 18 | 50.000 |
> | 1.000.000 | 3 | 27 | 1.000.000 |
> | 17.000.000 | 3 | 27 | 17.000.000 |
> | 300.000.000 | 4 | 36 | 300.000.000 |
>
> La tabla se multiplicó por seis mil y el costo pasó de 18 a 36. Ese es todo el argumento.
>
> Un detalle que suele confundirse: el abanico grande **no** reduce las comparaciones —son
> siempre del orden de log₂ n, porque las búsquedas binarias de cada nivel se componen—.
> Lo que el abanico grande reduce son las **lecturas de página**, que son log₂₆₀ n. Como el
> costo real está en la página y no en la comparación, esa es exactamente la magnitud que
> había que atacar. El B-tree existe para eso.

> **↓ Capa 3 — qué cuesta mantenerlo.** Salteable si ya lo sabés.
>
> Un índice no es una lectura más rápida a cambio de nada. Cada índice es **una estructura
> más que hay que escribir**.
>
> `Asistencia` tiene cuatro índices B-tree: el que Postgres crea solo por la
> [clave primaria](A0-07-bases-de-datos-relacionales.md#clave-primaria-e-identidad-generada),
> más los tres declarados en `db/schema.sql:1139-1141`. Entonces un fichaje —una fila nueva—
> cuesta:
>
> 1. Escribir la fila en una página de montón con lugar libre.
> 2. Insertar la clave en el índice de la clave primaria.
> 3. Insertar la clave en `Asistencia_id_sede_fecha_hora_ingreso_idx`.
> 4. Insertar la clave en `Asistencia_id_socio_fecha_hora_ingreso_idx`.
> 5. Insertar la clave en `asistencia_reserva_idx` **sólo si `id_reserva` no es nulo** (por
>    qué, en el apartado siguiente).
>
> Cuatro o cinco páginas tocadas donde el dato es una. Y cada una de esas páginas se escribe
> además en el registro de escritura anticipada (el WAL) antes de que el
> [commit](A0-07-bases-de-datos-relacionales.md#transacción-acid-commit-y-rollback) devuelva
> OK, porque si no la durabilidad no se cumpliría.
>
> Además, cuando una página de índice se llena, **se divide**: se reparte su contenido en
> dos páginas, se escriben las dos, y el nivel de arriba recibe una clave nueva —que puede
> desatar otra división, hasta la raíz—. Es el precio de que el árbol se mantenga
> balanceado solo.
>
> Hay un caso donde este costo se evita, y el repo lo tiene: en
> `backend/routers/asistencia.py:277` · `registrar_salida()` se escribe
> `fecha_hora_egreso`, que **no está en ningún índice**. Postgres puede resolver ese
> `UPDATE` con la optimización HOT (*heap-only tuple*): si en la misma página hay lugar para
> la versión nueva de la fila, la encadena a la vieja y **no toca ni uno de los cuatro
> índices**. Registrar la salida es, en escrituras de índice, gratis. Registrar la entrada
> no lo es.
>
> **El corolario está escrito en el propio esquema.** `db/schema.sql:1153-1156`, arriba de
> `registro_ejercicio_socio_ej_fecha_uidx`:
>
> > *"El indice (id_socio, id_ejercicio) fue eliminado: era prefijo exacto de este. Un
> > B-tree se recorre por sus columnas iniciales, asi que el de tres columnas ya resolvia
> > todo lo que resolvia el de dos, y tener los dos costaba espacio y escrituras sin ninguna
> > ganancia."*
>
> Ese comentario tiene adentro las dos reglas que gobiernan un índice compuesto y conviene
> leerlo despacio. Un B-tree sobre `(a, b, c)` está ordenado primero por `a`, después por
> `b`, después por `c`. Por lo tanto sirve para `WHERE a = ?`, para `WHERE a = ? AND b = ?`
> y para `WHERE a = ? AND b = ? AND c = ?`, porque en los tres casos las filas que
> interesan están **contiguas**. No sirve para `WHERE b = ?` a secas: esas filas están
> desparramadas por todas las hojas. Un índice sobre `(a, b)` conviviendo con uno sobre
> `(a, b, c)` es, entonces, puro costo de escritura.
>
> `db/schema.sql` declara 34 índices explícitos. Sumados los que Postgres crea solo —uno por
> cada una de las 41 claves primarias y uno por cada una de las 23 declaraciones `UNIQUE` de
> columna o de restricción— la base sostiene del orden de **98 árboles B**. Cada escritura
> de una fila paga los árboles de su tabla, y sólo los de su tabla.

---

## Índice único parcial

### El problema del que nació

La regla del negocio es: **un socio no puede tener dos rutinas vigentes a la vez.**

Con las herramientas de A0-07 esa regla no se puede escribir. `UNIQUE (id_socio)` sobre
`Asignacion_Rutina` diría "un socio tiene una sola rutina en toda su vida", que es absurdo:
la tabla existe justamente para llevar el historial, con `estado` en `FINALIZADA` o
`CANCELADA` cuando el socio cambió de rutina. `UNIQUE (id_socio, estado)` tampoco: diría
"una sola FINALIZADA", y un socio que pasó por cinco rutinas tiene cinco.

Lo que hace falta es una unicidad que valga **sólo sobre un subconjunto de las filas**.
Postgres la ofrece desde la versión 7.2 (2002) con el índice parcial: un `CREATE INDEX` con
`WHERE`.

```sql
CREATE UNIQUE INDEX asignacion_rutina_una_activa_uidx ON "Asignacion_Rutina" (id_socio)
    WHERE (estado = 'ACTIVA'::estado_asignacion);
```

Eso es `db/schema.sql:1150-1151`, literal. Y el comentario de la tabla, en
`db/schema.sql:801-805`, dice para qué:

> *"INDICE PARCIAL asignacion_rutina_una_activa_uidx: un socio no puede tener dos rutinas
> VIGENTES a la vez. El historial no cuenta, para eso el indice es parcial. Sin el WHERE
> diria 'una sola rutina en toda su vida', que seria absurdo."*

> **↓ Capa 2 — qué le pasa a una fila que no cumple el `WHERE`.** Este es el piso del
> concepto. Salteable si ya lo sabés.
>
> **La fila no entra al árbol. En absoluto.** No entra marcada, no entra en una zona
> aparte: el índice simplemente no tiene una entrada para ella. Eso tiene tres consecuencias
> encadenadas, y las tres importan:
>
> 1. **La unicidad no la puede violar**, porque la unicidad se chequea buscando la clave en
>    el árbol, y la clave no está ahí. Un socio puede tener quince asignaciones
>    `FINALIZADA` con el mismo `id_socio` y ninguna colisiona con ninguna.
> 2. **El índice es más chico**, en proporción exacta a cuántas filas quedan afuera. Un
>    socio con cinco asignaciones históricas y una vigente aporta una sola entrada.
> 3. **La escritura de las filas que no cumplen es más barata**, porque no hay clave que
>    insertar. Es el punto 5 de la cuenta del apartado anterior: `asistencia_reserva_idx`
>    (`db/schema.sql:1141`) es parcial con `WHERE (id_reserva IS NOT NULL)`, así que un
>    fichaje espontáneo —el socio que entra a entrenar sin haber reservado— no paga ese
>    índice. Ahí el `WHERE` no está para garantizar nada: está para no indexar una columna
>    que la mayoría de las filas tiene en nulo.
>
> **Y la trampa, que el esquema documenta arriba de todos los índices**, en
> `db/schema.sql:1095-1098`:
>
> > *"los índices parciales dependen de que la columna de estado sea NOT NULL. Una fila con
> > estado nulo no cumple la condición del WHERE, así que queda FUERA del índice y convive
> > con una activa sin disparar conflicto. Por eso las ocho columnas de estado del esquema
> > son obligatorias."*
>
> Leído desde acá, el mecanismo es transparente: `NULL = 'ACTIVA'` no da falso, da `NULL`, y
> el `WHERE` de un índice parcial sólo admite filas donde la condición da verdadero
> verdadero. Una fila con `estado` nulo se escapa por el mismo agujero por el que se escapan
> las `FINALIZADA`, con la diferencia de que esta sí es una asignación vigente para todo el
> resto del sistema. Por eso `db/schema.sql:1147-1151` no alcanza solo: necesita el
> `NOT NULL` de `db/schema.sql:798`, y el comentario de `db/schema.sql:1095-1098` lo deja
> escrito: por esta razón *"las ocho columnas de estado del esquema son obligatorias"*.

### Los siete parciales de este esquema, y sus dos familias

| Índice | Línea de `db/schema.sql` | Condición | Para qué |
|---|---|---|---|
| `membresia_una_activa_uidx` | 1095-1096 | `estado = 'ACTIVA'` | una sola membresía vigente por socio |
| `congelamiento_una_activa_uidx` | 1102-1103 | `estado = 'ACTIVO'` | un solo congelamiento vigente por membresía |
| `horario_actividad_unico_uidx` | 1110-1111 | `activo` | un solo horario vigente por sede, actividad, día y hora |
| `asignacion_rutina_una_activa_uidx` | 1135-1136 | `estado = 'ACTIVA'` | una sola rutina vigente por socio |
| `asignacion_dieta_una_activa_uidx` | 1155-1156 | `estado = 'ACTIVA'` | una sola dieta vigente por socio |
| `turno_horario_actividad_idx` | 1116-1117 | `id_horario_actividad IS NOT NULL` | no indexar los turnos sueltos |
| `asistencia_reserva_idx` | 1126 | `id_reserva IS NOT NULL` | no indexar los fichajes sin reserva |

Los cinco primeros son **únicos** y existen para garantizar una regla. Los dos últimos **no
son únicos** y existen para no pagar un índice sobre una columna mayormente nula. Mismo
mecanismo, dos usos que no se parecen en nada.

### El precio: un índice parcial no puede ser diferido

Acá aparece lo que este mecanismo cobró, y es lo que lo convierte en una decisión de diseño
y no en un truco.

Casi todas las validaciones de este esquema son disparadores diferidos —`db/schema.sql:1182-1186`
lo explica: validan al confirmar la transacción y no al escribir cada fila, para que una
operación de varios pasos pueda pasar por estados intermedios inválidos—. **Un índice único
parcial no admite eso.** Sólo una restricción `UNIQUE` declarada como tal puede ser
`DEFERRABLE`, y una restricción `UNIQUE` no acepta un `WHERE`. El índice se evalúa al
terminar cada sentencia.

Reasignarle a un socio la rutina B cuando tenía la A son dos escrituras: finalizar la A y
crear la B. Si entran en ese orden no pasa nada; si entran al revés, hay un instante con dos
`ACTIVA` y la base rechaza la operación. Y el orden no lo elige el programador: lo elige el
ORM (→ [A0-09](A0-09-el-orm.md)), que agrupa los `INSERT` antes que los `UPDATE`. Entonces
el endpoint tiene que forzarlo a mano. Es `backend/routers/rutinas.py:408-429` ·
`asignar_rutina()`: el bucle de las líneas 404-411 pone la anterior en `FINALIZADA`, y la
línea 425 es un `db.flush()` con diez líneas de comentario arriba explicando que **no es
opcional**:

> *"Un índice parcial no puede ser DEFERRABLE en Postgres, así que se evalúa al terminar
> cada sentencia — y SQLAlchemy ordena su flush poniendo los INSERT ANTES que los UPDATE.
> Sin esto, la fila nueva entraría mientras la anterior sigue ACTIVA y la base rechazaría
> una reasignación que es perfectamente válida."*

El mismo par de escrituras aparece en dietas, con el mismo índice parcial
(`asignacion_dieta_una_activa_uidx`) y la misma necesidad.

### Cómo se comprobó que hace las dos cosas

`backend/pruebas/test_una_sola_activa.py` existe sólo para esto, y su encabezado
(líneas 9-15) nombra los dos chequeos y dice que son **opuestos**:

- **Que la base frene dos vigentes aunque el `INSERT` no pase por la aplicación.** El paso 4
  del guion (líneas 121-133) mete una segunda fila `ACTIVA` con SQL directo y espera que la
  base la rechace. Antes del índice, la regla vivía sólo en el código del endpoint: dos
  `INSERT` por SQL entraban las dos, y el síntoma era silencioso —el socio quedaba con dos
  rutinas y el sistema mostraba las dos como buenas—.
- **Que el `WHERE` no rompa el historial.** El paso 5 (líneas 135-146) inserta una segunda
  fila `FINALIZADA` del mismo socio y espera que **entre**. Si el índice no fuera parcial,
  este chequeo fallaría.

Entre los dos está el paso 2 (líneas 100-115), que reasigna por el endpoint y verifica que
queda una sola `ACTIVA` y que la anterior sigue en el historial: es el que detecta si
alguien saca el `flush()` de `backend/routers/rutinas.py:429`.

*(El archivo es un guion que se corre contra el backend levantado y la base vacía. Para
escribir este capítulo se leyó, no se ejecutó.)*

---

## Plan de consulta y planificador

### El problema del que nació

Si SQL declara qué y no cómo, alguien tiene que elegir el cómo. Ese alguien es el
**planificador**, y la elección no es obvia: para `WHERE id_socio = 812` sobre `Asistencia`
tiene al menos tres caminos —leer la tabla entera comparando, entrar por
`Asistencia_id_socio_fecha_hora_ingreso_idx`, o entrar por el índice y resolver todo ahí si
las columnas pedidas están en la clave—. El planificador estima el costo de cada uno y se
queda con el más barato. El resultado de esa decisión es el **plan**: un árbol de nodos que
el ejecutor recorre.

La idea es de 1979, del optimizador por costo de System R en IBM, y la parte contraintuitiva
es esta: **el escaneo secuencial no es el camino malo.** Si la consulta devuelve una
fracción grande de la tabla, leer todo de corrido gana, porque el índice obliga a alternar
entre páginas de índice y páginas de montón en orden aleatorio, y por cada fila devuelta
paga una lectura extra. El cruce está más abajo de lo que uno diría: con una tabla de
417 páginas y una consulta que devuelve la mitad de las filas, el índice pierde por goleada.

> **↓ Capa 2 — con qué decide, y por qué a veces se equivoca.** Salteable si ya lo sabés.
>
> El planificador no mira los datos: mira **estadísticas** que `ANALYZE` dejó guardadas por
> columna —cuántas filas tiene la tabla, cuántos valores distintos hay en cada columna, cuál
> es la lista de los valores más frecuentes y sus proporciones, y un histograma del resto—.
> Con eso estima la **selectividad** de cada condición: qué fracción de filas va a
> sobrevivir. Después le pone precio a cada nodo posible con unas constantes que expresan
> cuánto vale una lectura secuencial, una lectura aleatoria y una comparación, y suma.
>
> De ahí salen las dos formas típicas de que un plan salga mal, y ninguna es un error del
> planificador:
>
> - **Estadísticas viejas.** Una tabla que creció mucho desde el último `ANALYZE` se estima
>   con el tamaño viejo. El proceso de mantenimiento automático las refresca, pero después
>   de una carga masiva conviene no confiar.
> - **Columnas correlacionadas.** El planificador supone independencia entre condiciones. Si
>   dos columnas están correlacionadas de hecho, multiplica selectividades que no se
>   multiplican y estima de menos.
>
> **El piso de este concepto es el nodo elegido**, y para ver cuál eligió se le pide el plan
> con `EXPLAIN`. **En este repo no se corrió:** el capítulo se escribió en modo sólo lectura
> y la base tiene datos reales de producción. Lo que sigue no son planes medidos: son
> condiciones de filtro leídas del código, contrastadas contra las definiciones de índice de
> `db/schema.sql`.

### Las tres cosas que apagan un índice, las tres en este repo

**1. Una función sobre la columna.** Un B-tree sobre `fecha_pago` guarda `fecha_pago`, no
`date(fecha_pago)`. `backend/routers/dashboard.py:113-118` · `ingresos()` filtra así:

```python
db.query(func.coalesce(func.sum(Pago.monto), 0))
  .filter(Pago.estado == "CONFIRMADO",
          func.date(Pago.fecha_pago) >= desde,
          func.date(Pago.fecha_pago) <= hasta)
```

Envuelta en `date(...)`, la condición no es utilizable por ningún índice sobre la columna
cruda. Compará con `backend/routers/dashboard.py:216`, que en el gráfico de ingresos compara
la columna tal cual:

```python
.filter(Pago.estado == "CONFIRMADO",
        Pago.fecha_pago >= datetime.combine(inicios[0], datetime.min.time()))
```

**Y ahora el matiz que hace que esto no sea un defecto.** Los dos índices de `Pago` son
`(id_sede, fecha_pago)` y `(id_socio, fecha_pago)` (`db/schema.sql:1120-1121`): en los dos,
`fecha_pago` es la **segunda** columna. Por la regla del prefijo que documenta
`db/schema.sql:1154`, una consulta que filtra únicamente por fecha no puede usar ninguno de
los dos ni aunque estuviera escrita sin la función. Los índices de `Pago` están puestos para
las otras dos preguntas que el sistema hace de verdad —los pagos de una sede por fecha y los
pagos de un socio por fecha—, y el total mensual del panel se resuelve recorriendo `Pago`.
Con una tabla de pagos que crece unas pocas miles de filas por año, eso son un puñado de
páginas: el escaneo secuencial es la respuesta correcta y no hay nada que cambiar.

**2. Un comodín al principio de un `LIKE`.** Es el caso de la búsqueda del mostrador,
`backend/routers/recepcion.py:329-335` · `buscar()`:

```python
patron = f"%{dni.strip()}%"
socios = (db.query(Socio)
          .join(Persona, Persona.id_persona == Socio.id_persona)
          .filter(Persona.dni.like(patron))
          .order_by(Persona.apellido, Persona.nombre)
          .limit(10)
          .all())
```

`Persona.dni` está declarado `NOT NULL UNIQUE` en `db/schema.sql:83`, así que **tiene** un
índice único. Y el `LIKE '%…%'` no lo puede usar: un B-tree ordena por el comienzo de la
cadena, y un patrón que empieza con comodín no acota ningún rango de ese orden. (`LIKE 'abc%'`
sí lo usaría, con la salvedad de la clasificación de la base de datos.) La consulta recorre
`Persona`.

Eso es deliberado y el docstring lo explica sin nombrar el índice, en
`backend/routers/recepcion.py:322-323`: *"Se aceptan coincidencias parciales para poder
tipear los últimos dígitos, que es como la gente los dicta."* Lo que compró la búsqueda
exacta —usar el índice— se cambió por lo que necesita el mostrador: que la persona diga
"termina en 4507" y alcance. El `.limit(10)` de la línea 334 es el que le pone techo al
costo del resultado.

**3. Una columna que no es la primera del índice.** Ya quedó dicho con `Pago`. Vale también
al revés: `_clases_usadas()` (`backend/routers/actividades.py:130-134`) filtra
`Reserva.id_inscripcion` y `Reserva.estado`, y los índices de `Reserva` son
`(id_turno, estado)` y `(id_turno, id_socio)` más el de la clave primaria
(`db/schema.sql:1136-1137`): **ninguno empieza por `id_inscripcion`**. Postgres tampoco
indexa sola una columna que es
[clave foránea](A0-07-bases-de-datos-relacionales.md#clave-foránea-y-acción-referencial) —
indexa el lado referenciado, que ya es clave primaria, nunca el que referencia—, así que
`Reserva_id_inscripcion_fkey` (`db/schema.sql:1060`) no aporta ninguno. Contar las clases
usadas de un abono recorre `Reserva` entera.

Es la contracara exacta de haber eliminado la columna `clases_restantes`: derivar el
contador en vez de guardarlo elimina el riesgo de desincronización y a cambio paga un
recorrido por consulta. Con un turno de yoga por día y decenas de reservas por semana, esa
tabla se mide en miles de filas y el recorrido son unas pocas páginas. **Es una decisión
tomada con conocimiento del tamaño, no un olvido**; si `Reserva` creciera en un orden de
magnitud, el índice que haría falta se deduce sin ambigüedad de la condición de las líneas
132-133.

### Los índices que sí se usan, y por qué se sabe

Tres casos donde la condición del código calza exactamente con un índice declarado:

| Consulta | Índice que la sirve |
|---|---|
| `db/schema.sql:1289-1291`, el `count(*)` del disparador de cupo, filtra `(id_turno, estado)` | `Reserva_id_turno_estado_idx`, `db/schema.sql:1136`, sobre `(id_turno, estado)` |
| `backend/routers/dashboard.py:329-331` filtra `estado = 'ACTIVA'` y `fecha_vencimiento` entre hoy y el límite de aviso | `Membresia_estado_fecha_vencimiento_idx`, `db/schema.sql:1107`, sobre `(estado, fecha_vencimiento)` |
| `backend/routers/portal.py:1139-1141` busca la medición de hoy por `(id_socio, fecha)` | `Registro_Salud_id_socio_fecha_idx`, `db/schema.sql:1104`, único sobre `(id_socio, fecha)` |

El segundo es el molde del índice compuesto bien elegido: **igualdad en la primera columna,
rango en la segunda.** Las membresías `ACTIVA` quedan contiguas en el árbol y adentro de ese
bloque están ordenadas por vencimiento, así que el rango de siete días es un tramo seguido
de hojas. Invertir las columnas —`(fecha_vencimiento, estado)`— serviría bastante peor: el
rango de fechas quedaría primero y obligaría a descartar las canceladas una por una
adentro de él.

Hay un cuarto caso que muestra lo que un índice hace además de filtrar.
`backend/routers/portal.py:1078-1083` pide las mediciones de un socio con
`.order_by(RegistroSalud.fecha)`. Como el índice de `db/schema.sql:1104` está ordenado por
`(id_socio, fecha)`, entrar por él devuelve las filas **ya ordenadas**: el plan puede no
tener nodo de ordenamiento. Un B-tree no sólo encuentra: entrega en orden, y eso alcanza
para `ORDER BY`, para `MIN`/`MAX` y para el `ORDER BY … DESC LIMIT 1` que el propio esquema
recomienda en `db/schema.sql:27` para sacar el peso actual de `Registro_Salud`.

---

## Por qué está hecho así

**Qué se estaba optimizando.** Dos cosas que tiran para lados distintos: que ninguna regla
del negocio dependa de que el código la recuerde, y que la base no se llene de estructuras
que hay que escribir en cada alta. El resultado es un esquema con muchos índices —98
árboles— pero con muy pocos puestos "por las dudas": cada uno de los 34 explícitos responde
a una consulta concreta del backend o garantiza una regla concreta.

**Qué restricción acorralaba.** La base no está en la máquina que corre el backend, así que
cada consulta cuesta una ida y vuelta por la red. Eso empuja a resolver en la base todo lo
que se pueda —el `GROUP BY` del gráfico de ingresos, el `count(*)` del cupo, la unicidad de
la asignación vigente— y a no traer filas para procesarlas acá. Un chequeo de "una sola
vigente" hecho leyendo primero y escribiendo después son dos viajes **y** una ventana en el
medio donde otro pedido puede colarse; el índice lo resuelve en cero viajes adicionales y
sin ventana.

**Qué alternativas se descartaron, en serio.**

- *Dejar la regla de "una sola vigente" sólo en el código del endpoint.* Es lo que había
  antes, y el encabezado de `backend/pruebas/test_una_sola_activa.py:4-7` cuenta cómo
  falló: dos `INSERT` por SQL entraban las dos y el síntoma era silencioso. Cualquier
  camino nuevo hacia esa tabla —un guion de migración, una corrección manual, un endpoint
  futuro— tenía que acordarse de la regla.
- *Modelarla con una restricción `UNIQUE` común.* No se puede sin borrar el historial, que
  es el dato que la tabla existe para guardar.
- *Ponerle un índice a cada columna que aparece en un `WHERE`.* Es la tentación obvia y el
  esquema la resistió: `db/schema.sql:1153-1156` documenta el índice que se **sacó** por ser
  prefijo de otro. Cada índice de más es una escritura de más en cada alta, para siempre.
- *Guardar `clases_restantes` como columna.* Existió y se eliminó: *"clases_restantes fue
  ELIMINADA: el consumo se calcula al vuelo contando Reserva"* (`db/schema.sql:668`). Un
  contador guardado es rápido de leer y se
  desincroniza en la primera cancelación que alguien olvide descontar.

**Qué se pagó.** Tres cosas, todas visibles en el código:

1. **El `flush()` obligatorio.** El índice parcial no puede diferirse, así que el endpoint
   tiene que ordenar sus escrituras a mano (`backend/routers/rutinas.py:417-429`). Diez
   líneas de comentario existen para que nadie borre una línea que parece inofensiva.
2. **Un recorrido por consulta en `_clases_usadas()`**, que es lo que cuesta derivar en vez
   de guardar cuando no hay índice que ayude.
3. **Cuatro o cinco escrituras por fichaje.** Es el precio de que el panel de recepción
   pueda listar los ingresos de hoy por sede y el historial de un socio sin recorrer nada.

**Cómo se llama el patrón.** Dos, y conviene tener los nombres: **poner la restricción en la
capa más baja que pueda sostenerla** —si la base la puede garantizar, la garantiza la base,
porque es la única capa por la que pasan todos los caminos— y **derivar en vez de
almacenar**, que acá aparece dos veces con resultados opuestos: barato cuando hay índice que
lo sostiene, un recorrido cuando no.

---

## Con qué se conecta

- **Es la misma idea que…** la regla de no cobrar por adelantado y el índice único parcial
  de `Membresia`: la misma garantía sostenida desde dos capas, el backend rechazando y la
  base impidiendo ([A-02](A-02-prepago-puro.md)).
- **Existe por culpa de…** la [normalización (3FN)](A0-07-bases-de-datos-relacionales.md#normalización-3fn):
  los hechos se parten en tablas para no repetirlos, y el `JOIN` es lo que los vuelve a
  juntar.
- **Es el mismo problema que…** el [paquete](A0-02-como-se-comunican-dos-maquinas.md#paquete-dirección-ip-y-dns)
  y la página de 8 KB: el costo se paga por bloque y no por byte, así que conviene pedir de
  a bloques.
- **Es la misma idea que…** el plan de consulta y la [compilación al vuelo](A0-01-como-corre-un-programa.md#intérprete-bytecode-y-compilación-al-vuelo):
  en los dos casos un intermediario decide cómo ejecutar algo que se declaró sin decir cómo.
- **Se contradice con…** los disparadores diferidos de este mismo esquema: el índice parcial
  no admite diferirse, así que obliga a ordenar a mano escrituras que el ORM ordenaba solo
  ([A0-09](A0-09-el-orm.md)).
