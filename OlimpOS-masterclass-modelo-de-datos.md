# OlimpOS — Masterclass del modelo de datos

**Documento de referencia interna · Estado: `schema.sql` con las migraciones 001 a 009 ya incorporadas · Última verificación: 21 de agosto de 2026**

Este documento explica las **37 tablas**, los **13 enums** y las **67 relaciones** del sistema. No es un catálogo: es el razonamiento detrás de cada decisión, incluyendo dónde ese razonamiento podría haber ido para otro lado.

Todo lo que se afirma acá está **contado sobre el `schema.sql` real**, no recordado ni estimado. Si un número de este documento no coincide con lo que devuelve la base, el que está mal es el documento.

### Las tres piezas de esta documentación

Este archivo no viaja solo. Hay tres formas de mirar el mismo modelo, y cada una sirve para algo distinto:

| Pieza | Qué es | Para qué sirve |
|---|---|---|
| **Este archivo** | El texto completo, con el razonamiento de cada decisión | Estudiarlo, buscar algo puntual, preparar una defensa |
| **`olimpos_schema.dbml`** (raíz del repo) | El esquema en formato DBML | Pegarlo en [dbdiagram.io](https://dbdiagram.io/d) → **Import > DBML** y ver el **diagrama ER completo**, con las 37 tablas y las 67 relaciones dibujadas |
| **La página interactiva** | Recorrido visual publicado como artifact | Repasar rápido: el mapa radial de `Socio`, el explorador de las 37 tablas, y las preguntas de defensa plegables |

El `.dbml` está generado desde `schema.sql` y verificado contra él: 37 tablas, 13 enums, 67 referencias. Sus comentarios (`Note:`) llevan la versión corta del "por qué" de cada tabla, así que el diagrama de dbdiagram.io no queda mudo — al hacer clic en una tabla aparece su justificación.

### Cómo leer esto

Hay tres formas de usar este archivo, y conviene saber cuál te sirve hoy:

- **De punta a punta**, si querés entender el modelo por primera vez. El orden está pensado para eso: primero el criterio (§1), después las piezas sueltas (§2–3), después el mapa (§4), y recién ahí tabla por tabla (§6).
- **Por búsqueda**, si ya sabés qué tabla te interesa. Andá directo a su ficha en §6; cada una es autocontenida.
- **Para defenderlo**, si alguien te va a preguntar. §10 tiene las preguntas probables con la respuesta corta, y §9 tiene las tres decisiones que un profesor cuestionaría primero.

### El inventario, de una

| Qué | Cuánto | Dónde se explica |
|---|---|---|
| Tablas | **37** | §6 |
| Enums (tipos con lista cerrada) | **13** | §3 |
| Claves foráneas | **67** (65 simples + 2 compuestas) | §7 |
| Restricciones `CHECK` | **7** | §8 |
| Funciones de trigger | **3** (con 7 disparadores) | §8 |
| Índices únicos **parciales** | **4** | §8 |
| Tablas que nadie referencia (hojas) | **13** | §4 |
| Migraciones aplicadas | **9** | §5 |

---

## Índice

1. [Cómo se decide si algo merece ser una tabla](#1-cómo-se-decide-si-algo-merece-ser-una-tabla)
2. [Qué es un enum, y por qué a veces gana el enum y a veces la tabla](#2-qué-es-un-enum)
3. [Los 13 enums, uno por uno](#3-los-13-enums-uno-por-uno)
4. [La topología: cómo está armado el mapa](#4-la-topología-del-modelo)
5. [`schema.sql`, migraciones y la base real: quién manda](#5-schemasql-migraciones-y-la-base-real)
6. [Las 37 tablas, una por una](#6-las-37-tablas)
7. [Las 67 relaciones explicadas](#7-las-relaciones)
8. [Lo que el diagrama no muestra](#8-lo-que-el-diagrama-no-muestra)
9. [Las cuatro ideas que explican todo el modelo](#9-las-cuatro-ideas-de-fondo)
10. [Las tres tablas que te van a cuestionar](#10-las-tres-tablas-que-te-van-a-cuestionar)
11. [Qué se pierde al bajar de 37 a 13 tablas](#11-el-modelo-de-13-tablas)
12. [Apéndice — Preguntas de defensa](#apéndice--preguntas-de-defensa-y-cómo-responderlas)

---

## 1. Cómo se decide si algo merece ser una tabla

Antes de mirar tabla por tabla conviene tener el criterio, porque si no la respuesta a "¿por qué esta tabla?" suena siempre igual y a nadie le queda nada.

> **La analogía que ordena todo el capítulo.** Pensá una tabla como **una planilla de papel en un archivador**. Una fila es un renglón; una columna es una casilla de ese renglón. Con eso en la cabeza, las seis razones de abajo son seis maneras distintas de descubrir que *el dato no entra en una casilla* — y cuando un dato no entra en una casilla, necesita su propia planilla.

Una tabla existe por alguna de estas seis razones. Ninguna es "porque queda más prolijo".

### Razón 1 — Un atributo que en la realidad es múltiple (1FN)

Una celda guarda un valor. Si el hecho del mundo real admite varios valores a la vez, no entra en una columna, y el intento de meterlo igual produce el error clásico: una columna de texto con valores separados por comas.

Ejemplo del sistema: una persona puede tener celular **y** fijo. Por eso existe `Telefono` y no una columna `telefonos` en `Persona`.

**La analogía.** Es la casilla "Teléfono:" de un formulario de papel. Si la persona tiene tres, o escribe apretado y ya nadie entiende dónde termina uno y empieza el otro, o tacha y pone una flecha al margen. La base sufre exactamente lo mismo: con `"11-2345-6789 / 4567-8901"` adentro de un `varchar`, buscar un número exacto pasa a ser **buscar texto dentro de texto** — y ahí un número que termina igual que otro te devuelve el socio equivocado.

Cómo se reconoce: en la frase que describe el hecho aparece un plural. *"Una rutina tiene varios ejercicios"*, *"un socio puede tener varias patologías"*.

**El test de una línea:** si podés decir *"…y también…"* sin que la frase suene rara, es razón 1.

### Razón 2 — Un hecho que cambia con el tiempo y cuyo pasado importa

Una columna guarda el valor de ahora. Cuando cambia, el anterior desaparece — un `UPDATE` no deja rastro. Si el valor viejo era información valiosa, la columna es el lugar equivocado.

Ejemplo del sistema: el precio que un socio pactó por su membresía. Si viviera en `Tipo_Membresia.precio_actual` y ese precio subiera, todos los pagos históricos pasarían a "haber sido" al precio nuevo. Por eso `Membresia.precio_pactado` guarda lo que se acordó ese día, y son dos hechos distintos que conviven.

**La analogía.** Una columna es **un pizarrón**; una tabla con fechas es **un cuaderno**. En el pizarrón siempre está el número de hoy, y para escribir el de hoy hay que borrar el de ayer. En el cuaderno se agrega un renglón y queda todo. La pregunta de diseño es siempre la misma: *¿esto es un pizarrón o es un cuaderno?* El peso del socio parece pizarrón (¿cuánto pesa hoy?) y es cuaderno (la progresión **es** el producto que el gimnasio vende).

**Un matiz que importa:** un `UPDATE` no es un cambio, es una **destrucción con reemplazo**. La base no guarda el valor anterior en ningún lado; no hay "deshacer". Por eso esta razón no es paranoia de archivista: es que el dato viejo, si no lo pusiste en una fila propia, ya no existe en ninguna parte del universo.

Cómo se reconoce: preguntarse *"si esto cambia mañana, ¿me importa lo que decía ayer?"*. Si la respuesta es sí, va con fecha en una tabla propia.

### Razón 3 — Atributos que sólo existen para algunas filas (herencia)

Cuando un conjunto de entidades comparte una parte de sus datos pero cada subgrupo suma los suyos, meter todo en una tabla ancha produce columnas que están en `NULL` no porque el dato se desconozca, sino porque **la pregunta no aplica**. Son dos NULL distintos que la base no sabe diferenciar.

Ejemplo del sistema: `Persona` tiene lo común (DNI, nombre, contacto de emergencia); `Entrenador` suma `matricula`; `Recepcionista` suma `turno_laboral`. Un recepcionista no tiene matrícula *en blanco*: no tiene matrícula, punto.

**La analogía.** Es un formulario único para todo el personal, con una casilla "Matrícula profesional:" que el recepcionista deja vacía. Al mes siguiente nadie sabe si la dejó vacía **porque no le corresponde** o porque **se olvidó de completarla**. Son dos situaciones distintas —una es "no aplica", la otra es "falta el dato"— y la base las guarda idénticas: `NULL`. Ese es el costo real de la tabla ancha, y no se arregla con buena voluntad: se arregla separando las planillas.

> **La frase para defenderlo en una oral:** *"`NULL` en la base significa 'no sé'. Cuando lo uso para decir 'no aplica', estoy metiendo dos significados en un mismo símbolo, y después ninguna consulta puede distinguirlos."*

### Razón 4 — Relación de muchos a muchos

Cuando los dos lados de una relación pueden repetirse, la relación no cabe como columna en ninguno de los dos: necesita su propia tabla.

Ejemplo del sistema: un profesor dicta varias actividades y una actividad la pueden dictar varios profesores. Por eso `Profesor_Actividad`.

**La analogía.** Pensá en poner el dato como columna y vas a ver que **no hay dónde**. ¿`Profesor.actividades`? No entra (razón 1). ¿`Actividad.profesores`? Tampoco. El vínculo no es propiedad de ninguno de los dos: **es propiedad del par**. Por eso necesita su propia planilla, donde cada renglón es un apretón de manos entre una fila de acá y una fila de allá.

Cómo se reconoce: la frase funciona igual leída al derecho y al revés, y en los dos sentidos aparece un plural.

**El test de una línea:** decila al revés. *"Un profesor dicta varias actividades"* / *"una actividad la dictan varios profesores"*. Si las dos son verdad, es N:M y va tabla intermedia.

### Razón 5 — Catálogo (evitar repetir el mismo texto en muchas filas)

Si un valor descriptivo se repite en muchas filas, guardarlo como texto en cada una significa que un error de tipeo crea una categoría fantasma, y que renombrarlo obliga a tocar miles de filas. El catálogo le da a ese valor un lugar único.

Ejemplo del sistema: `Patologia`. Sin catálogo, "diabetes", "Diabetes" y "diabetes tipo 2" son tres patologías distintas para la base.

**La analogía.** Es la diferencia entre **escribir el nombre del país en cada sobre** y **tener un sello**. Con el sello, el nombre está bien escrito una sola vez y todos los sobres heredan esa forma; si algún día cambia, se cambia el sello. Escribiéndolo a mano, cada sobre es una oportunidad nueva de escribirlo distinto — y la base no tiene forma de saber que "diabetes" y "Diabetes" son la misma cosa, porque para ella son dos textos diferentes y punto.

**El costo escondido:** el problema no es el espacio (el texto repetido ocupa poco). El problema es que **la consulta deja de ser confiable**. `WHERE patologia = 'diabetes'` no devuelve a los que tienen `'Diabetes'`, y nadie se entera de que faltan — no hay error, hay resultados incompletos, que es mucho peor.

### Razón 6 — Un evento (algo que pasó, con su fecha y su detalle)

Un evento no es un atributo de nadie: es un hecho con existencia propia, que ocurrió en un momento y puede repetirse. Los eventos siempre son tablas.

Ejemplo del sistema: `Pago`, `Asistencia`, `Reserva`. Un socio no "tiene un pago": hizo muchos, cada uno con su fecha, monto y método.

**La analogía.** Un atributo responde *"¿cómo es?"*; un evento responde *"¿qué pasó?"*. El color de ojos es un atributo de la persona. Un cobro no es una característica de nadie: es algo que **ocurrió**, en un momento, entre dos partes, y que quedaría registrado aunque el socio se borrara del mundo. Los eventos tienen fecha propia porque **existen en el tiempo**, no en la ficha de alguien.

**Cómo se reconoce:** si la frase natural es *"el 3 de marzo, Fulano hizo X"*, es evento. Si es *"Fulano es X"*, es atributo.

### El criterio inverso, que importa igual

Si ninguna de las seis razones aplica, **agregar la tabla es sobre-ingeniería**. Una tabla de más no es gratis: suma un `JOIN` a cada consulta, una FK que mantener y una entidad más que entender. El modelo tiene 37 tablas, pero también tiene 13 enums que son, precisamente, los casos donde se decidió *no* hacer una tabla.

Y hay un caso real en este proyecto donde se aplicó el criterio inverso **hacia atrás**: la tabla `Consulta_Cruzada` existía en el diseño original y **se eliminó**, porque en la revisión del backend se comprobó que ningún endpoint la escribía ni la leía. Una tabla que nadie usa no es "capacidad futura": es una promesa que el modelo hace y el sistema no cumple. La historia completa está en [§10](#10-las-tres-tablas-que-te-van-a-cuestionar).

### Tabla resumen de las seis razones

| # | Razón | Pregunta que la detecta | Ejemplo en OlimpOS |
|---|---|---|---|
| 1 | Atributo múltiple (1FN) | ¿Puede haber más de uno **a la vez**? | `Telefono` |
| 2 | Historia | Si cambia mañana, ¿me importa lo de ayer? | `Registro_Salud`, `Baja` |
| 3 | Herencia | ¿Hay atributos que sólo aplican a algunos? | `Entrenador`, `Socio` |
| 4 | N:M | ¿La frase vale al derecho **y** al revés? | `Profesor_Actividad` |
| 5 | Catálogo | ¿El mismo texto se repite en muchas filas? | `Ejercicio`, `Patologia` |
| 6 | Evento | ¿La frase natural empieza con una fecha? | `Pago`, `Asistencia` |

---

## 2. Qué es un enum

Un **enum** (de *enumeration*, enumeración) es un tipo de dato que vos definís, y que sólo admite valores de una lista cerrada que escribiste de antemano.

Cuando declarás:

```sql
CREATE TYPE estado_turno AS ENUM ('HABILITADO', 'CANCELADO');
```

...estás creando un tipo nuevo, al mismo nivel que `int` o `varchar`. Una columna declarada `estado estado_turno` **solamente** puede contener `'HABILITADO'` o `'CANCELADO'`. Cualquier otra cosa —`'habilitado'` en minúscula, `'SUSPENDIDO'`, un espacio de más— es rechazada por el motor con un error, no guardada.

### Qué se gana frente a un `varchar`

Si esa columna fuera `varchar(20)`, la base aceptaría `'HABILITADO'`, `'habilitado'`, `'Habilitdo'` y `'asdasd'` con la misma indiferencia. El error de tipeo entra, y se descubre semanas después cuando un turno no aparece en ninguna consulta porque su estado tiene una letra cambiada. Con enum, ese error es imposible: se rechaza en el momento de escribir.

Además ocupa menos espacio (internamente se guarda un número de 4 bytes, no el texto) y las comparaciones son más rápidas.

### Qué se pierde frente a una tabla de catálogo

Tres cosas, y son las que definen cuándo *no* usar enum:

1. **El valor no puede tener atributos propios.** `'CANCELADO'` es una etiqueta y nada más. Si mañana cada estado necesitara un color para la interfaz, un orden de visualización o una descripción larga, el enum no tiene dónde ponerlos: haría falta una tabla.
2. **Agregar un valor es un cambio de esquema, no un alta de datos.** Sumar un estado nuevo requiere un `ALTER TYPE`, o sea una migración corrida por alguien con permisos sobre la estructura. Con una tabla de catálogo, sería un `INSERT` que puede hacer el dueño desde una pantalla.
3. **Sacar un valor es prácticamente imposible.** PostgreSQL no soporta quitar valores de un enum. Está documentado en la propia migración 005: para eliminar `EN_ESPERA` habría que recrear el tipo entero y todas las columnas que lo usan.

### La regla que usa este sistema

> Enum cuando el conjunto de valores es **cerrado, estable y sin atributos propios**, y cada fila tiene **exactamente uno** a la vez.
>
> Tabla cuando alguno de esos tres supuestos se cae.

Contraste dentro del mismo esquema, para ver que no es dogma:

- `Baja.tipo` es un enum (`VOLUNTARIA`, `MORA`, `ADMINISTRATIVA`): son tres etiquetas fijas, sin datos propios, y una baja es de un solo tipo.
- `Patologia` es una tabla: cada patología tiene `descripcion` propia (atributo → razón 5), la lista crece con el uso (no es cerrada), y un socio puede tener varias a la vez (→ razón 1).

Si `Baja.tipo` algún día necesitara, por ejemplo, un plazo de reingreso distinto según el tipo, dejaría de ser candidato a enum y habría que promoverlo a tabla. Ese es el momento de revisar la decisión, no antes.

### Un detalle del que casi nadie se entera hasta que lo sufre

El orden en que se declaran los valores de un enum **es** el orden de comparación. `ORDER BY estado` no ordena alfabéticamente: ordena por posición de declaración. En este sistema hay un caso concreto: `estado_reserva` quedó como `RESERVADA, EN_ESPERA, CANCELADA_SOCIO, CANCELADA_GIMNASIO`, con `EN_ESPERA` en **segundo** lugar y no al final, aunque se agregó después de las otras tres. Eso pasó porque la migración 005 lo insertó ahí a propósito; el efecto práctico es que al ordenar reservas por estado, las que están en espera aparecen inmediatamente después de las confirmadas y antes de las canceladas — que es un orden razonable para mostrar en pantalla, pero conviene saber que existe y que no es alfabético.

Y una trampa operativa, también documentada en 005: PostgreSQL no permite **usar** un valor de enum recién agregado dentro de la misma transacción que lo agregó. Por eso el `ALTER TYPE ... ADD VALUE 'EN_ESPERA'` está solo y arriba de todo en esa migración, separado del resto.

---

## 3. Los 13 enums, uno por uno

### `estado_turno` → `HABILITADO`, `CANCELADO`
Usado en: `Turno.estado`

Si una clase se da o se suspendió. Sólo dos valores porque un turno no tiene estados intermedios: o está en pie o no. Nótese que **no existe** un estado `FINALIZADO` o `PASADO`: que un turno ya haya ocurrido no es un dato que se guarde, se deduce comparando `fecha`/`hora` contra el reloj. Guardarlo obligaría a un proceso que marque turnos vencidos, que se puede caer o atrasar; derivarlo no puede desincronizarse nunca.

### `estado_reserva` → `RESERVADA`, `EN_ESPERA`, `CANCELADA_SOCIO`, `CANCELADA_GIMNASIO`
Usado en: `Reserva.estado`

El estado de la anotación de un socio en un turno. Dos decisiones acá:

**Por qué dos cancelaciones distintas y no una sola.** No es lo mismo que el socio se baje a que el gimnasio suspenda la clase. En el primer caso puede corresponder penalizar o descontar la clase; en el segundo hay que devolver el crédito. Si fuera un único `CANCELADA`, esa diferencia habría que sacarla de otro lado (¿quién la canceló? ¿había motivo en el turno?) y sería reconstrucción, no dato.

**Por qué `EN_ESPERA` vive acá y no en una tabla `Lista_Espera` aparte.** Porque una espera *es* una reserva que todavía no consiguió lugar, y compartir la tabla hace que el índice único `(id_turno, id_socio)` que ya existía impida gratis que alguien esté anotado y en espera al mismo tiempo. Con una tabla aparte, esa contradicción habría que chequearla a mano en los dos sentidos, en cada alta. Está comprobado: al intentar insertar al mismo socio como `RESERVADA` y como `EN_ESPERA` en el mismo turno, la base lo rechaza sola.

**La contracara, que hay que tener presente al programar:** `EN_ESPERA` no ocupa cupo. Cualquier conteo de ocupación tiene que filtrar `WHERE estado = 'RESERVADA'`. Un conteo sin filtrar sobre un turno con gente en cola devuelve un número mayor que el real.

### `estado_asignacion` → `ACTIVA`, `FINALIZADA`, `CANCELADA`
Usado en: `Asignacion_Rutina.estado`, `Asignacion_Dieta.estado`, `Asignacion_Entrenador.estado`

Un solo enum compartido por las tres tablas de asignación, porque las tres tienen el mismo ciclo de vida: está vigente, se terminó, o se dio de baja antes de empezar.

La distinción `FINALIZADA` vs `CANCELADA` no es cosmética: una rutina finalizada se cumplió y forma parte del historial de entrenamiento del socio; una cancelada nunca llegó a usarse. Al mirar la progresión de alguien, las canceladas son ruido y las finalizadas son señal.

### `estado_congelamiento` → `ACTIVO`, `FINALIZADO`, `CANCELADO`
Usado en: `Congelamiento.estado`

Es el mismo ciclo de vida que `estado_asignacion` pero en masculino, porque "congelamiento" es masculino y "asignación" femenina. Podría haberse reutilizado `estado_asignacion` y ahorrarse un tipo, a costa de escribir `estado = 'ACTIVA'` sobre un congelamiento. Se prefirió la concordancia gramatical sobre la economía de tipos: es una decisión de legibilidad, y es la clase de detalle que hace que el SQL se lea como castellano en vez de como una traducción.

### `estado_membresia` → `ACTIVA`, `VENCIDA`, `SUSPENDIDA`, `CANCELADA`
Usado en: `Membresia.estado`

Cuatro estados con causas distintas: `VENCIDA` es por paso del tiempo, `SUSPENDIDA` es por decisión administrativa (típicamente mora), `CANCELADA` es baja definitiva. La diferencia entre vencida y suspendida importa porque una vencida se resuelve pagando y una suspendida requiere que alguien la reactive.

### `estado_pago` → `CONFIRMADO`, `PENDIENTE`, `CANCELADO`, `REEMBOLSADO`
Usado en: `Pago.estado`

Acá se ve una decisión de fondo del sistema: **un pago nunca se borra**. Si se anula, pasa a `CANCELADO` y queda la fila. Esto es contabilidad, no gestión de datos: el registro de que existió un cobro y después se anuló es en sí mismo información auditable. Un `DELETE` destruiría evidencia.

`REEMBOLSADO` se distingue de `CANCELADO` porque en uno el dinero volvió al socio y en el otro la operación nunca se concretó — distinción imprescindible para cuadrar caja.

### `estado_deuda` → `PENDIENTE`, `PAGADA`, `CONDONADA`
Usado en: `Deuda.estado`

`CONDONADA` es el valor interesante: una deuda que el gimnasio decide no cobrar. Podría representarse borrando la fila, y sería un error — la decisión de perdonar una deuda es exactamente el tipo de acto que conviene tener registrado, con su fecha y su responsable. Es la misma filosofía que `estado_pago`.

### `estado_inscripcion` → `ACTIVA`, `VENCIDA`, `CANCELADA`
Usado en: `Inscripcion_Actividad.estado`

Ciclo de vida de la compra de un plan de actividad. Paralelo al de membresía pero sin `SUSPENDIDA`, porque una inscripción a Yoga no se suspende administrativamente: o está vigente, o se venció, o se dio de baja.

### `tipo_baja` → `VOLUNTARIA`, `MORA`, `ADMINISTRATIVA`
Usado en: `Baja.tipo`

Por qué se fue el socio. Sirve para métricas de retención: un pico de bajas por mora y un pico de bajas voluntarias son dos problemas de negocio completamente distintos, y sin este campo serían indistinguibles.

### `tipo_telefono` → `CELULAR`, `FIJO`
Usado en: `Telefono.tipo`

Ejemplo de manual de cuándo el enum es la elección obvia: dos valores, sin atributos propios, un teléfono es de un solo tipo.

### `tipo_limite` → `POR_SEMANA`, `POR_MES`
Usado en: `Plan_Actividad.tipo_limite`

El más sutil de los trece, porque **cambia el significado de otra columna**. En la misma fila está `cantidad`, y este enum define cómo leerla: con `POR_SEMANA`, `cantidad = 2` significa "dos veces por semana"; con `POR_MES`, `cantidad = 12` significa "doce clases en el mes".

Tiene una consecuencia que se propaga a otra tabla: `Inscripcion_Actividad.clases_restantes` sólo se usa cuando el plan es `POR_MES`. En los planes semanales no hay contador guardado — el consumo se cuenta dinámicamente sobre `Reserva`, porque el límite se reinicia cada semana y un contador tendría que resetearse solo, con un proceso que puede fallar.

### `metodo_pago` → `EFECTIVO`, `DEBITO`, `CREDITO`, `TRANSFERENCIA`, `BILLETERA_VIRTUAL`
Usado en: `Pago.metodo`

Cómo pagó. Es candidato a convertirse en tabla el día que cada método necesite atributos propios (comisión del procesador, plazo de acreditación, si requiere comprobante). Mientras sean etiquetas, el enum alcanza. Vale tenerlo en el radar porque es el enum de esta lista con más chances de crecer.

### `metodo_registro` → `RFID`, `MANUAL`
Usado en: `Asistencia.metodo_registro`

Si la entrada se registró con la tarjeta o la cargó una persona. Es un dato de auditoría: las entradas manuales son las que conviene revisar si algo no cuadra, porque implican intervención humana.

---

## 4. La topología del modelo

Antes de entrar tabla por tabla, conviene ver la forma del conjunto. Estos números salen de contar las claves foráneas reales de la base.

### Las tablas más referenciadas (el centro de gravedad)

| Tabla | La referencian | Quiénes |
|---|---|---|
| `Socio` | **13 tablas** | Asignacion_Dieta, Asignacion_Entrenador, Asignacion_Rutina, Asistencia, Baja, Congelamiento, Deuda, Inscripcion_Actividad, Membresia, Pago, Registro_Salud, Reserva, Socio_Patologia |
| `Sede` | 7 tablas | Asistencia, Empleado, Horario_Actividad, Pago, Promocion, Socio, Turno |
| `Persona` | 5 tablas | Dueno, Empleado, Socio, Telefono, Usuario |
| `Entrenador` | 5 tablas | Asignacion_Entrenador, Asignacion_Rutina, Horario_Actividad, Rutina, Turno |
| `Empleado` | 4 tablas | Entrenador, Nutricionista, Profesor, Recepcionista |
| `Actividad` | 4 tablas | Horario_Actividad, Plan_Actividad, Profesor_Actividad, Turno |
| `Membresia` | 4 tablas | Congelamiento, Deuda, Inscripcion_Actividad, Pago |

Que `Socio` sea el centro no es casualidad ni desprolijidad: **es la confirmación de que el modelo entendió de qué se trata el negocio**. Un gimnasio es un sistema que gira alrededor de sus socios; todo lo demás (pagos, asistencias, rutinas, dietas, membresías) son hechos que le ocurren a un socio. Si el centro de gravedad fuera otro —digamos, `Turno`— habría que sospechar que el modelo se armó mirando la operación diaria en vez del negocio.

> **La analogía.** El grafo de FK es un **mapa de calles**, y las tablas más referenciadas son **las avenidas**. Que todo el tránsito pase por `Socio` significa que el barrio se construyó alrededor de esa avenida, que es exactamente lo que uno espera de un gimnasio. Un modelo donde la avenida principal fuera `Pago` sería el modelo de una cobranza, no el de un gimnasio; uno donde fuera `Turno`, el de una agenda.

**Por qué `Empleado` bajó de 5 a 4.** En versiones anteriores de este documento figuraba con 5, porque `Consulta_Cruzada` lo referenciaba. Esa tabla ya no existe (ver [§10](#10-las-tres-tablas-que-te-van-a-cuestionar)). Por el mismo motivo, `Rutina` y `Dieta` pasaron de 3 referencias a 2 cada una.

### Las tablas hoja (nadie las referencia)

**Trece** tablas no son apuntadas por nadie: `Asignacion_Dieta`, `Asignacion_Entrenador`, `Asignacion_Rutina`, `Asistencia`, `Baja`, `Comida`, `Congelamiento`, `Deuda`, `Recepcionista`, `Registro_Salud`, `Rutina_Ejercicio`, `Socio_Patologia`, `Telefono`.

Ser hoja no es un defecto: significa que esa tabla es un **destino final** del modelo, un hecho que se registra y se consulta pero del que no cuelga nada más. `Asistencia` es el ejemplo puro: alguien entró al gimnasio, se anota, y ningún otro concepto del sistema necesita referirse a esa entrada en particular.

> **La analogía.** En el mapa de calles, las hojas son **las casas**, no las avenidas. Nadie pasa *a través* de una casa para llegar a otro lado: se llega y se termina el viaje ahí. Un modelo sano tiene muchas hojas — si **todo** apuntara a todo, cada consulta arrastraría medio esquema.

**El matiz que hay que tener listo:** ser hoja significa "nadie me apunta", **no** "no sirvo". `Deuda` es hoja y sostiene toda la cobranza del gimnasio. La pregunta que sí importa no es *"¿alguien la referencia?"* sino *"¿alguien la usa?"* — y esa se responde mirando el backend, no el diagrama. Es justamente la distinción que decidió el destino de `Consulta_Cruzada` (era hoja **y** nadie la usaba → se fue) frente al de `Deuda` (es hoja pero el backend la crea, la consulta y la salda → se queda).

`Recepcionista` en esa lista tiene una lectura distinta y vale señalarla: los otros tres subtipos de empleado **sí** son referenciados (`Entrenador` por 5 tablas, `Nutricionista` por 2, `Profesor` por 2), porque sus roles producen cosas — rutinas, dietas, clases dictadas. El recepcionista no produce entidades propias: su trabajo es operar el sistema, y esa huella queda en `Asistencia.id_registrado_por`, que apunta a `Usuario`, no a `Recepcionista`. Su defensa es estructural y está desarrollada en [§10](#10-las-tres-tablas-que-te-van-a-cuestionar).

### La cadena de dependencias fuerte

Hay un orden obligatorio para poblar la base desde cero, impuesto por las columnas `NOT NULL`:

```
Persona → Dueno → Sede → Empleado → (Entrenador | Nutricionista | Recepcionista | Profesor)
                    ↓
                  Socio → Membresia → Inscripcion_Actividad
```

No se puede crear una `Sede` sin un `Dueno`, ni un `Dueno` sin una `Persona`. Por eso el `seed.sql` usa `WITH ... RETURNING` encadenados: cada paso necesita el ID que generó el anterior.

> **La analogía.** Es armar un mueble: no podés atornillar la puerta antes de tener el lateral. Las FK `NOT NULL` son las instrucciones del manual, y no son una sugerencia — la base **se niega** a insertar la fila si el padre no está.

---

## 5. `schema.sql`, migraciones y la base real

Esta sección no estaba en las versiones anteriores del documento y es probablemente la más útil de todas para trabajar, porque explica **dónde vive la verdad** — que es la primera pregunta que hay que poder contestar antes de tocar nada.

### Los tres lugares donde existe el esquema

| Dónde | Qué es | Cuándo se lee |
|---|---|---|
| `Proyecto/db/schema.sql` | El DDL completo, para crear la base **desde cero** | Una vez, al crear una base nueva |
| `Proyecto/db/migrations/*.sql` | Nueve cambios **incrementales**, cada uno partiendo del estado anterior | Una vez cada uno, a mano, sobre la base ya existente |
| La base en Neon | El estado **real** contra el que corre la API | Siempre |

### Por qué existen las migraciones si `schema.sql` ya lo tiene todo

Porque **no se puede volver a correr `schema.sql` sobre una base con datos**. Una vez que Neon tiene socios, pagos y membresías cargados, un `CREATE TABLE` de una tabla que ya existe falla, y uno que no fallara sería peor: borraría todo para recrearlo.

> **La analogía.** `schema.sql` son **los planos de la casa**; las migraciones son **las órdenes de obra**. Si la casa todavía no está construida, alcanza con los planos. Si ya está construida y hay gente viviendo adentro, no le das los planos nuevos al albañil: le das la orden puntual *"abrir una ventana en la pared norte"*. Las dos cosas describen la misma casa terminada, pero sirven en momentos distintos.

### La regla que sostiene todo (y que ya se rompió dos veces)

Cada migración se escribe **dos veces**: una como el `ALTER`/`CREATE` incremental en `migrations/`, y otra ya integrada dentro de `schema.sql`. Así, los dos caminos —"aplicar las 9 migraciones en orden" y "correr `schema.sql` de una"— terminan en el mismo lugar.

Eso significa que **no hace falta leer las migraciones para entender el modelo**: `schema.sql` es autosuficiente. Las migraciones se leen por otra razón — porque cuentan *por qué* se cambió algo, y varias documentan un bug real que se descubrió corriendo la base, no leyendo el código.

Pero es una **convención sostenida por personas**, no una garantía del motor. Y falló dos veces, las dos detectadas y corregidas el 21 de agosto de 2026:

1. **La migración 008 (`Congelamiento`)** creó la tabla en Neon y su clase en el backend, pero nunca se dobló en `schema.sql`. Durante un tiempo, la base real tuvo 37 tablas y el DDL entregado 36. Quien creara una base nueva desde `schema.sql` se quedaba sin poder congelar membresías.
2. **La migración 006 (los triggers de cupo)** tuvo exactamente el mismo problema: los dos `CONSTRAINT TRIGGER` que impiden sobrevender un turno vivían sólo en la migración. Una base nueva arrancaba **sin el blindaje de cupo**, con el agujero que esa migración había ido a tapar.

**Por qué este tipo de bug es tan peligroso:** no rompe nada hoy. La base que ya está andando funciona perfecto; el que sufre es el que crea la base **la próxima vez** — y para entonces nadie se acuerda. Es una bomba de tiempo silenciosa, y la única defensa es contar: si `schema.sql` tiene 37 `CREATE TABLE` y el backend mapea 37 clases, están sincronizados.

### Las nueve migraciones, y qué agrega cada una

| # | Qué agrega | Por qué apareció |
|---|---|---|
| 001 | `Usuario.debe_cambiar_password` | Faltaba para el flujo de contraseña temporal |
| 002 | Triggers de integridad del personal + staff del turno | Reglas que el esquema v5 no tenía |
| 003 | `Asignacion_Entrenador` | La columna vieja pisaba el historial |
| 004 | `Actividad.minutos_tolerancia` | La tolerancia no es la misma para yoga que para la sala |
| 005 | `Horario_Actividad` + `EN_ESPERA` | Cargar cada turno a mano no escala |
| 006 | Triggers de cupo | **Se comprobó**: la base aceptaba 5 reservas en un turno de cupo 2 |
| 007 | `Horario_Actividad.id_entrenador_a_cargo` | Descuido de la 005: musculación no podía tener horario |
| 008 | `Congelamiento` | Pausar la cuota sin regalar ni robar días |
| 009 | Índices de "una sola activa" | **Se comprobó**: entraban dos rutinas activas del mismo socio |

Fijate el patrón: **las migraciones 006 y 009 nacieron de probar la base a mano**, no de releer la especificación. Las dos dicen textualmente "se comprobó insertando…". Es la diferencia entre creer que una regla está y verificar que está — y en los dos casos, la regla vivía sólo en el código del backend y la base no sabía nada.

### El detalle que hace idempotente a una migración

Casi todas usan `IF NOT EXISTS`, `DROP ... IF EXISTS` antes de crear, o un bloque `DO $$ ... END $$` que chequea antes de actuar. Eso las hace **idempotentes**: correrlas dos veces no duplica ni rompe nada.

No es prolijidad. Es que nadie lleva un registro confiable de qué migración se aplicó a qué base, y la alternativa a la idempotencia es que alguien tenga que **acordarse** — que es exactamente el tipo de garantía que este modelo evita en todos los demás lugares.

---

## 6. Las 37 tablas

Cada ficha responde: **qué es**, **por qué existe** (cuál de las seis razones), **por qué se pensó así**, **por qué no se simplifica**, **de dónde sale** (a qué apunta) y **a dónde va** (quién la apunta).

Las 37 se reparten en siete bloques temáticos. El reparto es para leerlo, no una división que exista en la base:

| Bloque | Tablas | De qué se trata |
|---|---|---|
| A — Identidad y personas | 9 | Quién es quién, y cómo entra al sistema |
| B — Socios y su ciclo de vida | 5 | El socio, su salud, su salida |
| C — Dinero | 6 | Membresías, pagos, deudas, pausas |
| D — Entrenamiento | 5 | Ejercicios, rutinas y a quién se le asignan |
| E — Nutrición | 3 | Espejo del bloque D, en comida |
| F — Actividades, turnos y reservas | 8 | La operación diaria del gimnasio |
| G — Organización | 1 | La sede, raíz de todo |

---

### BLOQUE A — Identidad y personas (9 tablas)

---

#### `Persona`

**Qué es.** El registro de un ser humano en el sistema: DNI, nombre, apellido, contacto, dirección, contacto de emergencia. 15 columnas, de las cuales sólo 4 son obligatorias (`dni`, `apellido`, `nombre`, y el `id`).

**Por qué existe (razón 3 — herencia).** Es el **supertipo** de toda la jerarquía humana. Un dueño, un empleado y un socio son, antes que nada, personas, y comparten exactamente los mismos datos personales. Sin esta tabla, el DNI, el nombre y el domicilio estarían repetidos en tres tablas distintas.

**Por qué se pensó así.** Hay un caso que fuerza la decisión: **la misma persona puede ser socio y empleado a la vez**. El entrenador que además entrena en el gimnasio donde trabaja. Con datos personales duplicados en `Empleado` y en `Socio`, esa persona tendría dos domicilios que pueden divergir, dos teléfonos, dos contactos de emergencia. Cuando se mude, alguien va a actualizar uno y olvidarse del otro. Con `Persona` única, se actualiza en un solo lugar y vale para todos sus roles.

**Por qué no se simplifica.** Fusionarla con `Socio` (el subtipo más numeroso) rompería a los empleados que no son socios y al dueño. Y el contacto de emergencia, que está acá como tres columnas (`emergencia_nombre`, `emergencia_telefono`, `emergencia_parentesco`), es correcto que sea columnas y no tabla: es un dato monovaluado (un contacto de emergencia por persona), así que la razón 1 no aplica.

**De dónde sale.** De ningún lado: es raíz, no tiene FK salientes.

**A dónde va.** La referencian 5 tablas: `Dueno`, `Empleado`, `Socio`, `Telefono`, `Usuario`.

---

#### `Telefono`

**Qué es.** Los teléfonos de una persona, con tipo (celular/fijo) y una marca de cuál es el principal.

**Por qué existe (razón 1 — 1FN).** Una persona puede tener más de un teléfono. Es el ejemplo canónico de la primera forma normal: el intento de meterlo como columna produce `telefonos VARCHAR(200)` con `"11-2345-6789 / 4567-8901"` adentro, y a partir de ahí buscar un número exacto requiere buscar texto dentro de texto, con todos los errores que eso arrastra.

**Por qué se pensó así.** La columna `principal` (booleano) resuelve "¿a cuál llamo primero?" sin necesidad de un orden implícito ni de asumir que el primero cargado es el bueno.

**Por qué no se simplifica.** Podría argumentarse que dos columnas fijas (`celular`, `telefono_fijo`) alcanzarían. Funciona hasta que alguien tiene dos celulares — y entonces hay que agregar `celular_2`, y después `celular_3`, modificando la estructura de la tabla cada vez. La tabla aparte no tiene ese techo.

**De dónde sale.** `id_persona` → `Persona`.

**A dónde va.** A ningún lado (tabla hoja).

---

#### `Usuario`

**Qué es.** Las credenciales de acceso al sistema: usuario, hash de contraseña, estado de bloqueo, intentos fallidos.

**Por qué existe.** Separa **identidad** (quién sos: `Persona`) de **autenticación** (cómo entrás al sistema). No toda persona registrada tiene cuenta: un socio que nunca usó la app existe como `Persona` y como `Socio`, pero no tiene fila acá.

**Por qué se pensó así — el punto más interesante del modelo.** No hay tabla de roles ni columna `rol`. **El rol se deriva** de en qué subtipos aparece la persona: si tiene fila en `Entrenador`, es entrenador; si además tiene fila en `Profesor`, es las dos cosas. Esto significa que el permiso y el hecho son el mismo dato — es imposible que alguien figure como entrenador en el login pero no tenga registro de entrenador, porque es la misma información leída desde un lado o el otro.

**Sobre `debe_cambiar_password`.** Nace en `true` por defecto **a propósito**, porque toda cuenta arranca con una clave temporal que eligió otra persona (el sistema para el dueño inicial, el personal para socios y empleados). Mientras la bandera esté en `true`, el login valida la contraseña pero **no emite token**: devuelve una señal para que el frontend redirija a cambiarla. Recién el segundo login entrega la sesión. La misma mecánica cubre tres situaciones distintas con un solo campo: alta del dueño, alta de un usuario nuevo, y reseteo por olvido.

**Por qué no se simplifica.** Fusionar `Usuario` con `Persona` obligaría a que toda persona tenga usuario y contraseña, incluyendo a los socios que nunca van a entrar a la app. Serían columnas en NULL en la mayoría de las filas — el síntoma de la razón 3 aplicado al revés.

**De dónde sale.** `id_persona` → `Persona` (relación 1:1, forzada por `UNIQUE`).

**A dónde va.** `Asistencia.id_registrado_por` la apunta, para saber qué operador registró cada entrada.

---

#### `Dueno`

**Qué es.** El subtipo dueño, con su porcentaje de participación en el negocio.

**Por qué existe (razón 3 — herencia).** `porcentaje_participacion` es un atributo que sólo tiene sentido para un dueño.

**Por qué se pensó así.** Que sea tabla y no un booleano `es_dueno` en `Persona` permite el caso de sociedad: dos dueños con 50% cada uno. El campo de porcentaje sería absurdo en `Persona` (¿qué porcentaje tiene un socio?).

**Por qué no se simplifica.** Con un solo dueño parece sobrar, y es la crítica razonable. Se sostiene porque `Sede` y `Promocion` apuntan acá: si mañana entra un socio capitalista, el modelo ya lo soporta sin migración.

**De dónde sale.** `id_persona` → `Persona`.

**A dónde va.** `Sede.id_dueno` y `Promocion.id_dueno`.

---

#### `Empleado`

**Qué es.** El subtipo empleado: legajo, fecha de ingreso, fecha de egreso, sede donde trabaja.

**Por qué existe (razón 3 — herencia).** Datos laborales que no aplican ni a socios ni al dueño.

**Por qué se pensó así.** `fecha_egreso` nullable en vez de borrar la fila: un empleado que se fue sigue existiendo, porque las rutinas que escribió y las clases que dictó siguen apuntando a él. Borrarlo rompería el historial.

**Un detalle de 3FN.** El dueño del empleado no está acá: se obtiene navegando `Empleado → Sede → Dueno`. Ponerlo directo sería una dependencia transitiva (el dueño depende de la sede, no del empleado) y violaría la tercera forma normal.

**Por qué no se simplifica.** Este es el nudo de la pregunta "¿por qué no una sola tabla de empleados con un tipo?". Dos razones independientes, y basta una:

1. **Atributos distintos por subtipo.** `Entrenador` tiene `matricula` y `especialidad`; `Recepcionista` tiene `turno_laboral`. En una tabla única, todas esas columnas conviven y quedan en NULL para quien no corresponde — y ese NULL no significa "se desconoce", significa "no aplica". Son dos cosas distintas que la base no puede distinguir.
2. **Una persona puede tener dos roles a la vez.** Entrenador *y* Profesor simultáneamente. Una columna `tipo` guarda un valor: no puede representarlo. La única salida sería texto separado por comas, que es exactamente la violación de 1FN que el modelo evita en `Telefono`.

Y una tercera razón, más fina: `Rutina.id_entrenador` apunta a `Entrenador`, no a `Empleado`. Eso hace **estructuralmente imposible** que un recepcionista figure como autor de una rutina. Con tabla única y columna `tipo`, esa garantía desaparece y hay que reimplementarla con un CHECK o un trigger — trabajo extra para recuperar algo que el diseño correcto da gratis.

**El blindaje que no se ve.** Un `CONSTRAINT TRIGGER` diferido (migración 002) impide que exista un `Empleado` sin ninguna fila de subtipo — un "empleado colgado" que no es ni entrenador, ni profesor, ni recepcionista, ni nutricionista. Es diferido (se evalúa al confirmar la transacción, no al insertar) precisamente para que el alta en dos pasos —crear el empleado y después su subtipo— funcione dentro de una misma transacción.

**De dónde sale.** `id_persona` → `Persona`, `id_sede` → `Sede`.

**A dónde va.** Los cuatro subtipos: `Entrenador`, `Nutricionista`, `Recepcionista`, `Profesor`.

---

#### `Entrenador`, `Nutricionista`, `Recepcionista`, `Profesor` (4 tablas)

**Qué son.** Los cuatro subtipos de empleado, cada uno con sus atributos profesionales:

| Tabla | Atributos propios |
|---|---|
| `Entrenador` | `titulo`, `especialidad`, `matricula` |
| `Nutricionista` | `titulo`, `matricula` |
| `Recepcionista` | `turno_laboral` |
| `Profesor` | `titulo`, `especialidad` |

**Por qué existen (razón 3).** Ver la explicación en `Empleado`. Cada uno suma lo suyo sobre la base común.

**Por qué Entrenador y Profesor son tablas distintas.** Es la distinción menos obvia del modelo y conviene tenerla clara para defenderla: el **Entrenador** arma rutinas de musculación y hace seguimiento personalizado; el **Profesor** dicta clases grupales con horario fijo (yoga, boxeo). Son trabajos diferentes con relaciones diferentes: `Rutina` cuelga de `Entrenador`, mientras que `Profesor_Actividad` y `Turno.id_profesor` cuelgan de `Profesor`. Una persona con las dos capacidades tiene una fila en cada tabla, y eso es correcto, no duplicación.

**Por qué son subtipos "solapados".** En la teoría de modelado, una jerarquía puede ser *disjunta* (cada instancia pertenece a un solo subtipo) o *solapada* (puede pertenecer a varios). Ésta es **solapada**, y por eso no sirve un discriminador único — que es justamente la razón por la que la restricción de "todo empleado debe tener al menos un subtipo" necesita un trigger y no puede ser un simple CHECK.

**De dónde salen.** Los cuatro: `id_empleado` → `Empleado`, con `UNIQUE` (1:1).

**A dónde van.**
- `Entrenador` ← `Rutina`, `Asignacion_Rutina`, `Asignacion_Entrenador`, `Turno`, `Horario_Actividad` (5 tablas)
- `Nutricionista` ← `Dieta`, `Asignacion_Dieta`
- `Profesor` ← `Profesor_Actividad`, `Turno`
- `Recepcionista` ← nadie (ver la nota de tablas hoja más arriba)

---

### BLOQUE B — Socios y su ciclo de vida (5 tablas)

---

#### `Socio`

**Qué es.** El subtipo socio: número de socio, código RFID de la tarjeta, fecha de alta, objetivo personal.

**Por qué existe (razón 3).** `codigo_rfid` y `numero_socio` son atributos que sólo tienen sentido para quien usa el gimnasio como cliente.

**Por qué se pensó así.** `codigo_rfid` con `UNIQUE`: dos socios no pueden compartir tarjeta, y la base lo garantiza. Es la clave que hace funcionar el molinete.

**Lo que ya NO tiene, y por qué (migración 003).** Existía una columna `id_entrenador_a_cargo` que fue eliminada. El problema no era de normalización en sentido estricto —esa columna dependía enteramente de `id_socio`, así que no violaba 1FN, 2FN ni 3FN—, sino de **cardinalidad y tiempo**: una columna de valor único no puede representar que un socio tenga dos entrenadores a la vez (uno de musculación y otro de funcional), ni conservar quién lo entrenaba antes, porque un `UPDATE` pisa el valor anterior sin dejar rastro. Se reemplazó por la tabla `Asignacion_Entrenador`.

**Por qué no se simplifica.** Fusionar `Socio` con `Persona` obligaría a que toda persona sea socio, incluyendo empleados que no entrenan ahí y al dueño.

**De dónde sale.** `id_persona` → `Persona`, `id_sede` → `Sede`.

**A dónde va.** **13 tablas** lo referencian. Es el centro de gravedad del modelo.

---

#### `Baja`

**Qué es.** El registro de cuándo y por qué un socio dejó el gimnasio.

**Por qué existe (razón 2 — historia).** Un socio puede irse y volver. Con un booleano `activo` en `Socio`, la segunda baja pisaría a la primera y se perdería la historia: cuántas veces se fue, por qué motivo cada vez, cuánto duró afuera.

**Por qué se pensó así.** Es 1:N, no 1:1, precisamente para admitir reingresos. `Socio.activo` sigue existiendo como estado actual (es rápido de consultar), pero `Baja` es el registro histórico. No es redundancia: uno responde "¿está activo hoy?" y el otro "¿cuál fue su trayectoria?".

**Por qué no se simplifica.** Sin esta tabla, la métrica de retención —de las más importantes para un gimnasio— sería imposible de calcular hacia atrás.

**De dónde sale.** `id_socio` → `Socio`.

**A dónde va.** A ningún lado (hoja).

---

#### `Registro_Salud`

**Qué es.** Mediciones corporales del socio a lo largo del tiempo: peso, altura, grasa corporal, masa muscular.

**Por qué existe (razón 2 — historia).** El peso actual sirve poco; la **progresión** es todo el producto. Un socio que bajó 8 kilos en cuatro meses tiene ahí la prueba de que el gimnasio funciona, y esa es la razón por la que renueva.

**Por qué se pensó así.** El índice `UNIQUE (id_socio, fecha)` impide dos mediciones el mismo día (evita duplicados por error de carga) pero permite todas las fechas que haga falta. Y el peso actual **no se guarda en `Socio`**: se deriva con `ORDER BY fecha DESC LIMIT 1`. Guardarlo en los dos lugares crearía dos fuentes de verdad que pueden divergir.

**Por qué no se simplifica.** Cuatro columnas en `Socio` (`peso`, `altura`, etc.) darían la foto de hoy y destruirían la película.

**De dónde sale.** `id_socio` → `Socio`.

**A dónde va.** A ningún lado (hoja).

---

#### `Patologia` y `Socio_Patologia`

**Qué son.** `Patologia` es el catálogo de condiciones médicas. `Socio_Patologia` vincula socios con patologías, agregando fecha de diagnóstico y observaciones.

**Por qué existen.** `Patologia` por razón 5 (catálogo): sin ella, "hipertensión" estaría escrito distinto en cada ficha. `Socio_Patologia` por razones 1 y 4: un socio puede tener varias patologías, y una patología la tienen muchos socios — muchos a muchos puro.

**Por qué se pensó así.** `Socio_Patologia` tiene clave primaria compuesta `(id_socio, id_patologia)`: impide cargar dos veces la misma patología al mismo socio. Y tiene atributos propios (`fecha_diagnostico`, `observaciones`) que dependen de **la combinación** de socio y patología, no de uno solo — eso es exactamente la segunda forma normal bien aplicada.

**Por qué no se simplifica.** Una columna `patologias TEXT` en `Socio` haría imposible responder "¿qué socios son diabéticos?" de manera confiable, que es justo la consulta que un entrenador necesita antes de armar una rutina.

**De dónde salen.** `Socio_Patologia`: `id_socio` → `Socio`, `id_patologia` → `Patologia`.

**A dónde van.** `Patologia` ← `Socio_Patologia`. `Socio_Patologia` no va a ningún lado (hoja).

---

### BLOQUE C — Dinero (6 tablas)

---

#### `Tipo_Membresia`

**Qué es.** El catálogo de planes de membresía: nombre, duración en días, precio actual.

**Por qué existe (razón 5 — catálogo).** Sin él, cada `Membresia` repetiría el nombre y la duración del plan. Cambiar el precio del plan mensual obligaría a recorrer todas las membresías.

**Por qué se pensó así.** `precio_actual` es el precio **vigente hoy**, para nuevas ventas. No es el precio al que se vendió cada membresía existente — ese está en `Membresia.precio_pactado`.

**Por qué no se simplifica.** Es la separación que evita la dependencia transitiva de 3FN: sin el catálogo, `duracion_dias` en `Membresia` dependería del tipo de plan y no de la membresía en sí.

**De dónde sale.** De ningún lado.

**A dónde va.** `Membresia.id_tipo_membresia`.

---

#### `Membresia`

**Qué es.** La membresía concreta que compró un socio: desde cuándo, hasta cuándo, a qué precio, con qué promoción, en qué estado.

**Por qué existe (razón 2 y 6 — historia + evento).** Es el contrato entre socio y gimnasio, y se renueva. Cada renovación es una fila nueva, así que el historial completo de cuánto pagó y cuándo queda registrado.

**Por qué se pensó así — el punto de 3FN que más se pregunta.** `precio_pactado` acá y `precio_actual` en `Tipo_Membresia` **no son redundancia**. Son dos hechos distintos: uno es "cuánto se acordó el día que este socio compró" (histórico, inmutable) y el otro es "cuánto cuesta hoy" (vigente, cambia). Si el gimnasio aumenta 20%, las membresías vendidas antes tienen que seguir diciendo el precio viejo, porque eso es lo que la persona pagó. Derivar el precio del catálogo reescribiría la historia contable cada vez que hay un aumento.

**Por qué no se simplifica.** Meter las fechas de membresía en `Socio` limitaría a un socio a una sola membresía en toda su vida.

**De dónde sale.** `id_socio` → `Socio`, `id_tipo_membresia` → `Tipo_Membresia`, `id_promocion` → `Promocion`.

**A dónde va.** `Pago`, `Deuda`, `Inscripcion_Actividad`, `Congelamiento`.

---

#### `Promocion`

**Qué es.** Descuentos con vigencia: porcentaje o monto fijo, entre dos fechas, para una sede o para todas.

**Por qué existe (razón 6 — evento con vigencia).** Una promoción tiene vida propia, se aplica a muchas membresías y tiene fecha de inicio y fin.

**Por qué se pensó así.** `id_sede` **nullable** significa "aplica a todas las sedes". Es un uso deliberado del NULL como valor semántico ("sin restricción de sede"), y está bien acá porque no es ambiguo: no hay ningún otro motivo por el que ese campo podría estar vacío.

Que tenga tanto `porcentaje_descuento` como `monto_fijo_descuento` permite las dos modalidades comerciales sin forzar una conversión.

**Por qué no se simplifica.** Guardar el descuento como columna suelta en `Membresia` perdería la trazabilidad de qué campaña generó qué ventas — que es exactamente lo que el dueño quiere saber para decidir si repetirla.

**De dónde sale.** `id_dueno` → `Dueno`, `id_sede` → `Sede`.

**A dónde va.** `Membresia.id_promocion`.

---

#### `Pago`

**Qué es.** Cada movimiento de dinero: monto, método, fecha, comprobante, período que cubre.

**Por qué existe (razón 6 — evento).** Un pago es un hecho puntual, irrepetible y auditable.

**Por qué se pensó así.** Varias decisiones que vale desmenuzar:

- **Nunca se borra.** Anular es `estado = 'CANCELADO'` más `fecha_cancelacion`. En contabilidad, el rastro de lo que se anuló es tan importante como lo que quedó.
- **`numero_comprobante` con `UNIQUE`:** impide emitir dos veces el mismo número, que es un problema fiscal, no informático.
- **`es_adelanto`:** distingue el pago de un período futuro, que afecta cómo se imputa.
- **Tres FK opcionales distintas** (`id_membresia`, `id_inscripcion`, `id_sede`): un pago puede corresponder a una membresía, a una inscripción a actividad, o a ninguna de las dos (una clase suelta). Por eso las tres son nullable.

**Por qué no se simplifica.** Un campo `pagado boolean` en `Membresia` no soportaría pagos parciales, ni adelantos, ni métodos distintos, ni la anulación con rastro.

**De dónde sale.** `id_socio` → `Socio`, `id_membresia` → `Membresia`, `id_inscripcion` → `Inscripcion_Actividad`, `id_sede` → `Sede`.

**A dónde va.** `Deuda.id_pago_cancelatorio`, `Reserva.id_pago`.

---

#### `Deuda`

**Qué es.** Lo que un socio debe: monto, cuándo se generó, cuándo vence, en qué estado.

**Por qué existe (razón 6 — evento).** La deuda es una obligación con vida propia: nace (al vencer una membresía impaga), puede vencer, puede pagarse, puede condonarse.

**Por qué se pensó así.** `generada_automaticamente` distingue la deuda que creó el sistema (un proceso diario al vencer membresías) de la que cargó una persona a mano — dato de auditoría útil cuando un socio reclama.

`id_pago_cancelatorio` cierra el círculo: apunta al pago que saldó esta deuda, dejando la trazabilidad completa de deuda → pago.

**Por qué no se simplifica.** Un campo `debe_plata boolean` en `Socio` no diría cuánto, desde cuándo, ni por qué concepto.

**De dónde sale.** `id_socio` → `Socio`, `id_membresia` → `Membresia`, `id_pago_cancelatorio` → `Pago`.

**A dónde va.** A ningún lado (hoja).

---

#### `Congelamiento`

**Qué es.** La pausa de una membresía por viaje o lesión, sin perder los días pagados.

**Por qué existe (razón 2 — historia).** Un socio congela más de una vez a lo largo de los años, y cada congelamiento tiene su motivo y sus fechas. Con dos columnas en `Membresia`, el segundo congelamiento pisaría al primero — y ese historial es justamente el dato que hace falta si algún día se quiere poner un tope anual de días congelados.

**Por qué se pensó así — la decisión más fina de esta tabla.** La extensión del vencimiento se aplica **al reanudar, no al congelar**. Al pedir la pausa todavía no se sabe cuántos días van a ser realmente: alguien que pide 30 y vuelve a los 10 tiene que recuperar 10, no 30. Si se extendiera por adelantado habría que descontar la diferencia después, y esa clase de corrección es la que sale mal.

Por eso `fecha_fin` es un **tope**, no una promesa, y `dias_aplicados` se escribe recién al reanudar.

**Por qué `dias_aplicados` se guarda en vez de derivarse.** Podría calcularse como `fecha_reanudacion - fecha_inicio`, y sin embargo se guarda. La razón: es el número que **ya se aplicó** al vencimiento de la membresía. Si mañana cambia la forma de contar los días (por ejemplo, se decide no contar domingos), el histórico tiene que seguir explicando por qué el vencimiento quedó donde quedó. Es una excepción consciente a la regla de "no guardar lo derivable", y la excepción se justifica porque el número documenta un efecto ya producido.

**El índice único parcial.** `UNIQUE (id_socio) WHERE estado = 'ACTIVO'`: un solo congelamiento activo por socio a la vez. Si hubiera dos superpuestos, sería imposible saber cuántos días sumar sin contarlos dos veces. El `WHERE` es lo que hace que esto funcione: sin él, un socio no podría congelar más de una vez **en toda su vida**.

**De dónde sale.** `id_socio` → `Socio`, `id_membresia` → `Membresia`.

**A dónde va.** A ningún lado (hoja).

---

### BLOQUE D — Entrenamiento (5 tablas)

---

#### `Ejercicio`

**Qué es.** El catálogo de ejercicios: nombre, grupo muscular, descripción, video, si requiere máquina.

**Por qué existe (razón 5 — catálogo).** "Press de banca" se usa en cientos de rutinas. Escribirlo como texto en cada una multiplica el mismo dato y abre la puerta a variantes tipeadas distinto.

**Por qué se pensó así.** `grupo_muscular` vive acá y no en la rutina, porque es una propiedad **del ejercicio**, no de la rutina que lo usa. Ponerlo en `Rutina_Ejercicio` sería una violación de 3FN de libro: dependería del ejercicio, no de la combinación rutina-ejercicio.

`url_video` centralizado significa que corregir un link arregla todas las rutinas que usan ese ejercicio.

**Por qué no se simplifica.** Sin catálogo, la consulta "mostrame todos los ejercicios de espalda" tendría que buscar texto libre y devolvería resultados incompletos por cada error de tipeo histórico.

**De dónde sale.** De ningún lado.

**A dónde va.** `Rutina_Ejercicio.id_ejercicio`.

---

#### `Rutina`

**Qué es.** La plantilla de un plan de entrenamiento: nombre, objetivo, nivel, días por semana, y quién la creó.

**Por qué existe (razón 6).** Es una entidad con autor y contenido propio.

**Por qué se pensó así — el punto clave.** `Rutina` es una **plantilla reutilizable**, no la rutina de una persona. Una rutina "Hipertrofia principiante 4 días" se escribe una vez y se asigna a treinta socios. Por eso está separada de `Asignacion_Rutina`: la plantilla es una cosa y el hecho de que Fulano la esté haciendo desde marzo es otra.

**Por qué `id_entrenador` apunta a `Entrenador` y no a `Empleado`.** Porque así la base **garantiza estructuralmente** que sólo un entrenador puede figurar como autor. Si apuntara a `Empleado`, un recepcionista podría quedar como autor de una rutina y haría falta un CHECK para impedirlo.

**Por qué no se simplifica.** Fusionar `Rutina` con `Asignacion_Rutina` obligaría a duplicar la plantilla entera —con todos sus ejercicios— por cada socio que la use. Treinta socios con la misma rutina serían treinta copias del mismo contenido, y corregir una serie mal cargada exigiría corregir las treinta.

**De dónde sale.** `id_entrenador` → `Entrenador`.

**A dónde va.** `Rutina_Ejercicio` (su contenido) y `Asignacion_Rutina` (a quién se le asignó).

---

#### `Rutina_Ejercicio`

**Qué es.** El contenido de una rutina: qué ejercicio, qué día, en qué orden, cuántas series, cuántas repeticiones, cuánto peso, cuánto descanso.

**Por qué existe (razón 1 — 1FN).** Una rutina tiene muchos ejercicios. Imposible como columna.

**Por qué se pensó así.** Tiene **atributos propios de la combinación**: las series y repeticiones no son del ejercicio (el press de banca no tiene "4 series" en abstracto) ni de la rutina (una rutina no tiene "12 repeticiones" en general), sino de **este ejercicio dentro de esta rutina**. Eso es 2FN aplicada correctamente.

`repeticiones` es `varchar` y no `int` a propósito: en el gimnasio real se escribe "8-12" o "al fallo", y forzarlo a número perdería información que el entrenador necesita transmitir.

El índice `UNIQUE (id_rutina, dia, orden)` impide dos ejercicios en la misma posición del mismo día.

**Por qué no se simplifica.** Es la tabla intermedia de un N:M enriquecido. Sin ella, la rutina sería un campo de texto con la planilla adentro, y sería imposible responder "¿qué rutinas usan sentadilla?".

**De dónde sale.** `id_rutina` → `Rutina`, `id_ejercicio` → `Ejercicio`.

**A dónde va.** A ningún lado (hoja).

---

#### `Asignacion_Rutina`

**Qué es.** El hecho de que un socio esté haciendo una rutina, desde cuándo, hasta cuándo, asignada por quién.

**Por qué existe (razón 2 y 4 — historia + N:M).** Un socio pasa por muchas rutinas a lo largo del tiempo, y una rutina se asigna a muchos socios.

**Por qué se pensó así.** PK subrogada (`id_asignacion_rutina`) en vez de clave compuesta, para permitir que un socio vuelva a una rutina que ya hizo antes: dos filas distintas con fechas distintas.

`id_entrenador` acá es **independiente** de `Rutina.id_entrenador`: uno es quien escribió la plantilla, el otro quien decidió asignársela a este socio. Pueden ser personas distintas, y esa distinción es real en un gimnasio con varios entrenadores.

**El índice de la migración 009.** `UNIQUE (id_socio) WHERE estado = 'ACTIVA'`: un socio no puede tener dos rutinas vigentes a la vez. La regla existía sólo en el código del backend; la base no sabía nada, y se comprobó insertando dos asignaciones activas por SQL directo — entraron las dos. El síntoma era silencioso: el socio quedaba con dos rutinas y el sistema mostraba las dos como buenas.

**Una consecuencia práctica que hay que conocer.** Un índice único **parcial** no puede ser diferido en PostgreSQL (sólo los constraints pueden diferirse, y un constraint no admite `WHERE`). Se evalúa al terminar cada sentencia. Eso importa porque el endpoint que reasigna rutina marca la anterior como finalizada y después inserta la nueva — pero los ORM suelen ordenar los INSERT antes que los UPDATE en su volcado, y sin un `flush` explícito en el medio, la fila nueva entra mientras la vieja sigue activa y el índice rompe una operación que en realidad es válida.

**De dónde sale.** `id_socio` → `Socio`, `id_rutina` → `Rutina`, `id_entrenador` → `Entrenador`.

**A dónde va.** A ningún lado (hoja).

---

#### `Asignacion_Entrenador`

**Qué es.** Qué entrenador está a cargo de qué socio, desde cuándo y hasta cuándo.

**Por qué existe (razón 2 y 4).** Reemplaza a la vieja columna `Socio.id_entrenador_a_cargo` (migración 003). El problema de aquella columna no era violar una forma normal —dependía enteramente de `id_socio`—, sino que **una columna de valor único no puede representar un hecho múltiple ni conservar el pasado**.

**Por qué se pensó así — y en qué se diferencia de sus dos hermanas.** Tiene la misma forma que `Asignacion_Rutina` y `Asignacion_Dieta` (PK subrogada, `fecha_inicio`, `fecha_fin`, `estado`), pero con una diferencia deliberada: **acá SÍ se permite más de una fila activa por socio al mismo tiempo**. Un socio con un entrenador de musculación y otro de funcional es normal, no un error. Por eso la migración 009, que le puso a rutina y dieta el índice de "una sola activa", dejó a esta tabla afuera **a propósito**.

Esto tiene una lectura conceptual que vale la pena registrar: las tres tablas comparten estructura pero no reglas. La estructura la impone la naturaleza del problema (historia + N:M); las reglas las impone el negocio, y el negocio dice cosas distintas para cada una.

**La limitación honesta de la migración.** La columna vieja nunca guardó *desde cuándo* ese entrenador estaba a cargo. Al migrar, los socios que ya tenían entrenador recibieron `fecha_inicio = fecha de la migración`, no la fecha real — que no se puede reconstruir porque nunca se guardó. El historial arranca desde ahí.

**De dónde sale.** `id_socio` → `Socio`, `id_entrenador` → `Entrenador`.

**A dónde va.** A ningún lado (hoja).

---

### BLOQUE E — Nutrición (3 tablas)

---

#### `Dieta`

**Qué es.** La plantilla de un plan alimentario: nombre, objetivo, calorías diarias, autor.

**Por qué existe (razón 6).** Espejo exacto de `Rutina`, en el dominio nutricional.

**Por qué se pensó así.** Misma lógica de plantilla reutilizable: una dieta "Déficit calórico 1800 kcal" se escribe una vez y se asigna a muchos socios.

`id_nutricionista` apunta a `Nutricionista`, no a `Empleado`, por la misma razón estructural que en `Rutina`.

**Por qué no se simplifica.** Ver `Rutina`: fusionarla con la asignación duplicaría el contenido completo por socio.

**De dónde sale.** `id_nutricionista` → `Nutricionista`.

**A dónde va.** `Comida` (su contenido) y `Asignacion_Dieta` (a quién se le asignó).

---

#### `Comida`

**Qué es.** Cada comida de una dieta: qué día, qué momento (desayuno, almuerzo), qué se come, cuántas calorías.

**Por qué existe (razón 1 — 1FN).** Una dieta tiene muchas comidas. Es el equivalente nutricional de `Rutina_Ejercicio`.

**Por qué se pensó así.** `descripcion` como `text` libre en vez de un catálogo de alimentos: es una decisión de alcance consciente. Un catálogo de alimentos con macronutrientes sería un sistema entero en sí mismo; para el nivel de este producto, el texto libre que escribe el nutricionista alcanza.

**Por qué no se simplifica.** Una dieta como campo de texto único impediría contar calorías por día o reordenar comidas.

**De dónde sale.** `id_dieta` → `Dieta`.

**A dónde va.** A ningún lado (hoja).

---

#### `Asignacion_Dieta`

**Qué es.** Qué dieta sigue qué socio, desde cuándo, asignada por quién.

**Por qué existe (razón 2 y 4).** Espejo de `Asignacion_Rutina`.

**Por qué se pensó así.** Misma estructura, misma regla de "una sola activa" (migración 009). La migración 009 además le agregó el índice `UNIQUE (id_socio, id_dieta, fecha_inicio)` que **le faltaba** —`Asignacion_Rutina` y `Asignacion_Entrenador` ya lo tenían—, corrigiendo una asimetría por la cual la misma dieta se podía asignar dos veces el mismo día al mismo socio.

Ese detalle es instructivo: las tres tablas de asignación nacieron con la misma idea pero terminaron con reglas distintas por accidente, y la 009 las emparejó donde correspondía y las dejó distintas donde la diferencia era intencional.

**De dónde sale.** `id_socio` → `Socio`, `id_dieta` → `Dieta`, `id_nutricionista` → `Nutricionista`.

**A dónde va.** A ningún lado (hoja).

---

### BLOQUE F — Actividades, turnos y reservas (8 tablas)

---

#### `Actividad`

**Qué es.** El catálogo de lo que se puede hacer en el gimnasio: musculación, yoga, boxeo. Con cupo por defecto, precio de clase suelta, horas de anticipación para cancelar, minutos de tolerancia.

**Por qué existe (razón 5 — catálogo).**

**Por qué se pensó así — la decisión estructural más importante del bloque.** **Musculación es una fila más acá**, no un caso especial. Podría haberse tratado la sala como algo aparte ("acceso libre" versus "clases"), y se decidió que no: al meterla como una actividad más, todo el sistema de `Turno` / `Reserva` / `Inscripcion` funciona igual para las tres, sin duplicar lógica.

Las diferencias entre ellas se expresan como **datos, no como código**:
- Musculación tiene `horas_anticipacion_cancelacion = 0` (acceso libre, se cancela cuando sea); yoga 12, boxeo 24.
- Musculación no lleva profesor: sus turnos usan `id_entrenador_a_cargo` o directamente no tienen staff.
- Musculación no tiene plan semanal (no tendría sentido limitar el acceso libre a dos veces por semana).

**Sobre `minutos_tolerancia` (migración 004).** Cuántos minutos después de la hora del turno se sigue aceptando la llegada. Está por actividad y no como constante en el código porque la tolerancia razonable no es la misma para todo: llegar 20 minutos tarde a una clase de yoga de 45 es no ir; a la sala abierta toda la tarde, el concepto casi no aplica. Como constante en el backend, cambiarlo requeriría un programador y un despliegue; como columna, lo cambia el dueño desde una pantalla. El CHECK lo limita a 0–180 — un techo holgado a propósito, puesto para atajar al dedo que escribe 1500 queriendo 15, no para discutir qué es razonable.

**Lo que NO existe, y es una decisión.** No hay estados `ASISTIO` / `AUSENTE` en `Reserva`. Son **derivables**: asistió = existe fila en `Asistencia` con ese `id_reserva`; ausente = ya pasó `hora + minutos_tolerancia` y esa fila no existe. Persistirlos obligaría a un proceso que marque ausentes periódicamente, que se puede caer, atrasar o correr dos veces — y mientras tanto el panel mostraría como "pendiente" un turno que venció hace una hora. Derivándolos no hay nada que pueda desincronizarse: si el reloj avanza, la respuesta cambia sola.

**De dónde sale.** De ningún lado.

**A dónde va.** `Plan_Actividad`, `Profesor_Actividad`, `Turno`, `Horario_Actividad`.

---

#### `Plan_Actividad`

**Qué es.** Las modalidades de contratación de una actividad: "2 veces por semana", "12 clases al mes", con su precio.

**Por qué existe (razón 1 y 5).** Una actividad tiene varios planes. Y el plan tiene atributos propios (`tipo_limite`, `cantidad`, `precio`) que no son de la actividad.

**Por qué se pensó así.** La combinación `tipo_limite` + `cantidad` es lo que hace flexible el modelo comercial sin tocar código: agregar "3 veces por semana" es un INSERT, no un despliegue.

**Por qué no se simplifica.** Columnas fijas en `Actividad` (`precio_2x_semana`, `precio_3x_semana`...) obligarían a modificar la tabla cada vez que el dueño inventa una promoción.

**De dónde sale.** `id_actividad` → `Actividad`.

**A dónde va.** `Inscripcion_Actividad.id_plan_actividad`.

---

#### `Inscripcion_Actividad`

**Qué es.** La compra concreta de un plan por parte de un socio: precio pactado, vigencia, clases restantes.

**Por qué existe (razón 2 y 6).** Es el contrato de actividad, paralelo a `Membresia` pero para clases.

**Por qué se pensó así.** Tres detalles:

- `precio_pactado` acá, igual que en `Membresia`, por la misma razón histórica.
- `id_membresia` **NOT NULL**: ata la inscripción a la membresía que la cubre. Una inscripción no puede vencer después que la membresía que la habilita, y esa regla se valida al comprar.
- `clases_restantes` **sólo se usa si el plan es `POR_MES`**. En los planes semanales queda en NULL y el consumo se cuenta dinámicamente sobre `Reserva`. Es una decisión consciente de no desnormalizar donde no hace falta: un contador semanal tendría que reiniciarse solo cada lunes, con un proceso que puede fallar.

**De dónde sale.** `id_socio` → `Socio`, `id_plan_actividad` → `Plan_Actividad`, `id_membresia` → `Membresia`.

**A dónde va.** `Pago.id_inscripcion`, `Reserva.id_inscripcion`.

---

#### `Profesor_Actividad`

**Qué es.** Qué actividades puede dictar cada profesor.

**Por qué existe (razón 4 — N:M puro).** Un profesor dicta varias actividades; una actividad la dictan varios profesores. Sin atributos propios: sólo el vínculo.

**Por qué se pensó así.** PK compuesta `(id_profesor, id_actividad)`: la combinación no se puede repetir, y no hace falta un ID artificial porque no hay nada más que guardar.

**Por qué es más importante de lo que parece.** Esta tabla es el **destino de dos claves foráneas compuestas** (desde `Turno` y desde `Horario_Actividad`). Es decir: no sólo documenta quién puede dictar qué, sino que la base la usa para **impedir** que se asigne un profesor a una clase que no está habilitado a dar. Es una tabla de datos que funciona como mecanismo de integridad.

**De dónde sale.** `id_profesor` → `Profesor`, `id_actividad` → `Actividad`.

**A dónde va.** `Turno` y `Horario_Actividad` la referencian con FK compuesta.

---

#### `Horario_Actividad`

**Qué es.** El horario semanal de una actividad: "Yoga, lunes 19:00, cupo 20, profesora Romina", con vigencia desde/hasta.

**Por qué existe (razón 6 — regla de generación).** Sin esta tabla, alguien tiene que crear a mano cada fila de `Turno`, para siempre. Si yoga es lunes y miércoles, son dos altas por semana de por vida; el día que alguien se olvida, la clase directamente no existe y nadie puede reservarla.

**Por qué se pensó así.** La actividad declara **su horario**, y el backend genera los turnos de las próximas semanas a partir de eso. Los turnos siguen siendo filas reales y editables: se puede cancelar el del lunes que viene por feriado sin tocar el horario.

**El detalle de `dia_semana`.** Es un entero 1–7 en formato ISO (1 = lunes ... 7 = domingo), **no** el día de semana nativo de PostgreSQL (que empieza en 0 = domingo). Se eligió ISO porque acá la semana empieza el lunes, igual que en el calendario que ve la gente, y porque PostgreSQL tiene `EXTRACT(ISODOW FROM fecha)` que devuelve exactamente eso — así la generación de turnos compara sin convertir nada.

**Sobre `vigente_desde` / `vigente_hasta`.** Permiten decir "Yoga pasa a las 20:00 desde el 1 de marzo" sin borrar el horario viejo ni perder los turnos ya generados con el anterior. Es historización aplicada a una regla, no a un hecho.

**La corrección de la migración 007.** La tabla nació (en la 005) con sólo `id_profesor`, pensada mirando yoga y boxeo. Consecuencia: un turno generado desde un horario **nunca** podía tener entrenador, así que declarar el horario semanal de musculación creaba turnos sin nadie a cargo y sin forma de asignarlo. La 007 le agregó `id_entrenador_a_cargo` y el CHECK `chk_horario_un_solo_staff`, dándole exactamente la misma forma que `Turno`. Fue un descuido reconocido, no una decisión — y está documentado como tal en la propia migración.

**Por qué no se simplifica.** Guardar el horario como texto ("lunes y miércoles 19hs") lo volvería inservible para generar nada automáticamente.

**De dónde sale.** `id_sede` → `Sede`, `id_actividad` → `Actividad`, `id_entrenador_a_cargo` → `Entrenador`, y la FK compuesta `(id_profesor, id_actividad)` → `Profesor_Actividad`.

**A dónde va.** `Turno.id_horario_actividad`.

---

#### `Turno`

**Qué es.** Una clase concreta: sede, actividad, fecha, hora, cupo, staff a cargo, estado.

**Por qué existe (razón 6 — evento programado).** Es la unidad reservable del sistema.

**Por qué se pensó así.** Varias capas:

- **`hora` sin hora de fin.** Es la hora de llegada, no un rango. Viene del diseño original de acceso libre: lo que importa es cuándo empieza y cuánta tolerancia hay (que sale de `Actividad.minutos_tolerancia`).
- **Dos campos de staff excluyentes.** `id_entrenador_a_cargo` para musculación/sala, `id_profesor` para clases. El CHECK `chk_turno_un_solo_staff` impide que vengan los dos. **Que ambos sean NULL sí es válido**: es la sala abierta sin nadie asignado — de hecho, los turnos de musculación del seed tienen los dos en NULL.
- **El unique cambió.** Antes era "un turno por día"; ahora es `(id_sede, id_actividad, fecha, hora)`, lo que permite varias clases el mismo día a distintas horas.
- **`id_horario_actividad` (migración 005).** De qué horario semanal nació este turno. **NULL = cargado a mano**, y la generación automática nunca los toca: alguien los creó por algo (una clase extra, un recuperatorio) y no le corresponde a un proceso decidir que sobran.

**El blindaje de la FK compuesta.** `(id_profesor, id_actividad)` → `Profesor_Actividad` garantiza que el profesor asignado esté habilitado para esa actividad. Es declarativo y no hardcodea el nombre "Musculación": si el profesor no dicta esa actividad, no entra. Y como PostgreSQL no evalúa una FK cuando alguna de sus columnas es NULL, los turnos sin profesor (musculación) quedan exentos **automáticamente**, sin necesidad de una excepción escrita.

**El blindaje del cupo (migración 006).** Hasta esa migración, el cupo lo controlaba sólo el backend: se comprobó insertando más reservas que cupo y la base las aceptó todas. Ahora hay dos triggers: uno impide que una reserva pase a `RESERVADA` si el turno está lleno, otro impide bajarle el cupo a un turno que ya tiene más gente anotada. Con una salvedad documentada: **ninguno de los dos cubre la carrera** entre dos transacciones simultáneas reservando el último lugar — eso lo resuelve un bloqueo de fila del lado de la aplicación. El trigger tapa el resto (bugs, INSERT manuales, importaciones), y los dos mecanismos se complementan sin reemplazarse.

**De dónde sale.** `id_sede` → `Sede`, `id_actividad` → `Actividad`, `id_entrenador_a_cargo` → `Entrenador`, `id_profesor` → `Profesor`, `id_horario_actividad` → `Horario_Actividad`, más la FK compuesta a `Profesor_Actividad`.

**A dónde va.** `Reserva.id_turno`.

---

#### `Reserva`

**Qué es.** La anotación de un socio en un turno, con su estado y de qué inscripción o pago sale.

**Por qué existe (razón 4 y 6 — N:M enriquecido + evento).** Un socio reserva muchos turnos; un turno tiene muchos socios anotados.

**Por qué se pensó así.**

- **`UNIQUE (id_turno, id_socio)`:** nadie se anota dos veces al mismo turno. Este índice, que parece rutinario, es el que hace funcionar gratis la lista de espera (ver abajo).
- **`id_inscripcion` o `es_clase_suelta` + `id_pago`:** la reserva se paga con un plan contratado o como clase suelta. Las dos vías conviven.
- **`EN_ESPERA` como estado y no como tabla:** una espera *es* una reserva sin lugar. Al compartir tabla, el índice único de arriba impide **por construcción** que alguien esté anotado y en espera a la vez. Con tabla aparte habría que chequearlo a mano en los dos sentidos.
- **El orden de la cola sale de `fecha_reserva`.** No hay columna "posición": el primero que llegó es el de fecha más vieja. Otra vez, no guardar lo que se puede derivar.

**El trigger de cupo es diferido a propósito.** Se evalúa al confirmar la transacción, no fila por fila. Eso permite, en una sola operación, cancelar a alguien y promover al primero de la cola —que es exactamente lo que hace la lista de espera— sin que el estado intermedio dispare un error aunque el estado final sea perfectamente válido.

**De dónde sale.** `id_turno` → `Turno`, `id_socio` → `Socio`, `id_inscripcion` → `Inscripcion_Actividad`, `id_pago` → `Pago`.

**A dónde va.** `Asistencia.id_reserva`.

---

#### `Asistencia`

**Qué es.** El registro de entrada (y salida) al gimnasio: cuándo entró, cuándo salió, por qué método, quién lo registró.

**Por qué existe (razón 6 — evento).** Es el hecho físico de que alguien cruzó la puerta.

**Por qué se pensó así.**

- **Es 1:N con `Reserva`, no 1:1.** Un socio puede entrar y salir varias veces en un día. Y `id_reserva` es **nullable**: se puede entrar sin reserva previa (acceso libre a la sala).
- **`id_registrado_por` apunta a `Usuario`, no a `Empleado`.** Lo que interesa auditar es qué **cuenta** hizo la operación, que es lo que efectivamente se puede rastrear en un sistema.
- **`metodo_registro`** distingue tarjeta de carga manual: las manuales son las que conviene revisar cuando algo no cuadra.

**Su rol silencioso.** Esta tabla es la que hace posible que "asistió" sea derivable en vez de guardado. La existencia de una fila acá con cierto `id_reserva` **es** la prueba de asistencia.

**De dónde sale.** `id_socio` → `Socio`, `id_sede` → `Sede`, `id_reserva` → `Reserva`, `id_registrado_por` → `Usuario`.

**A dónde va.** A ningún lado (hoja).

---

### BLOQUE G — Organización (1 tabla)

---

#### `Sede`

**Qué es.** La sucursal: nombre, dirección, teléfono, capacidad, horarios, si abre 24hs.

**Por qué existe.** Es la raíz organizativa: empleados, socios, turnos, pagos y promociones pertenecen a una sede.

**Por qué se pensó así.** El modelo es **multi-sede aunque hoy haya una sola**. Eso no es sobre-ingeniería gratuita: agregar la dimensión sede después, con datos cargados, obligaría a modificar siete tablas y decidir a qué sede pertenece cada fila histórica. Tenerla desde el principio cuesta una FK.

**Aclaración importante.** La regla de "una única sede" **no está en el esquema**: vive en el `seed.sql`, que es idempotente (no crea una segunda sede si ya hay una) y fija todas sus referencias a una sola. Es una convención de los datos de ejemplo, no una restricción estructural.

**De dónde sale.** `id_dueno` → `Dueno`.

**A dónde va.** 7 tablas: `Empleado`, `Socio`, `Turno`, `Pago`, `Asistencia`, `Promocion`, `Horario_Actividad`.

---

### La tabla que estaba acá y ya no está: `Consulta_Cruzada`

Si mirás una versión vieja del DER (`olimpos_schema_v4.dbml` o `v5`), vas a encontrar en este bloque una tabla llamada `Consulta_Cruzada`, con tres FK (`Empleado`, `Rutina`, `Dieta`) y un `CHECK` en XOR. **Ya no existe**, y conviene saber por qué, porque es la clase de pregunta que aparece en una defensa.

**Qué pretendía ser.** El registro de que un profesional consultó el plan de otra disciplina: el nutricionista mirando la rutina del socio para ajustar la dieta al gasto calórico, o el entrenador mirando la dieta. Sobre el papel, trazabilidad de acceso a datos de salud — de las cosas más defendibles que puede tener un modelo.

**Por qué se eliminó.** Porque **nunca se implementó**. Al auditar el backend endpoint por endpoint, no apareció una sola línea que la escribiera ni que la leyera: no tenía clase en `models.py`, ningún router la nombraba, ningún permiso la tocaba. Existía en el DDL y en el diagrama, y en ningún otro lado.

**El principio que aplica.** Una tabla de auditoría que no registra nada **no es trazabilidad: es la promesa de trazabilidad**. Y es peor que no tenerla, porque un lector del diagrama concluye razonablemente que el sistema audita esos accesos, cuando no audita ninguno. El modelo estaría afirmando algo falso sobre el sistema.

**Cómo defender la decisión si te la preguntan.** Hay dos respuestas legítimas y opuestas, y las dos son mejores que dejarla decorativa:

1. *"La saqué porque el sistema no la usaba, y un modelo tiene que describir el sistema que existe."* ← es la que se tomó.
2. *"La dejo y la cableo"*: agregar el modelo y hacer que los endpoints que muestran la rutina o la dieta de un socio inserten la fila. Es trabajo real, pero convierte la promesa en un hecho.

Lo que **no** es defendible es la tercera opción: dejarla en el diagrama sin que nadie la escriba, y presentarla como si auditara algo.

> **La lección general, que vale para todo el modelo:** una tabla se justifica por **uso**, no por buena intención. El resto de este documento explica por qué cada tabla existe; ésta es la única que explica por qué una dejó de existir, y por eso es la más instructiva de las 38 que alguna vez hubo.

---

## 7. Las relaciones

Son **67 claves foráneas: 65 simples y 2 compuestas**. En vez de listarlas una por una (ya están en las fichas de cada tabla), acá van agrupadas por **qué tipo de relación** representan, que es lo que hay que entender para leer el diagrama.

*(Eran 70 cuando existía `Consulta_Cruzada`, que aportaba tres.)*

### Qué significa una clave foránea

Una FK es una columna que guarda el ID de una fila de otra tabla. Su efecto es doble:

1. **Conecta** los datos: `Membresia.id_socio = 5` significa "esta membresía es del socio 5".
2. **Garantiza** que la conexión sea válida: es **imposible** insertar una membresía con `id_socio = 999` si no existe el socio 999. La base lo rechaza.

Ese segundo punto es el que convierte al esquema en un blindaje: reglas que no dependen de que el programador se acuerde.

> **La analogía.** Una FK es **el número de socio escrito en la ficha**, con un bibliotecario que verifica. Podrías anotar el número a mano en un papelito (eso sería guardar un `int` suelto, sin FK) y nadie te avisaría si escribís uno que no existe. La FK es el bibliotecario que, antes de aceptar la ficha, va al fichero, busca ese número, y si no está te devuelve el papel. **No se cansa, no se distrae y no está de licencia** — esa es toda la diferencia entre una regla en la base y una regla en el código.

**Lo que una FK NO hace, y conviene tener claro:** no impide que el dato sea absurdo, sólo que sea *inexistente*. Podés registrarle un pago al socio equivocado y la FK no dice nada: el socio existe, así que la referencia es válida. La FK garantiza **integridad referencial**, no corrección semántica. Para lo segundo están los `CHECK`, los triggers y —donde no alcanzan— el backend.

### Por qué `DEFERRABLE INITIALLY IMMEDIATE` en todas

Todas las FK del modelo llevan ese sufijo, y significa: *"se validan al instante (IMMEDIATE), pero **podrían** posponerse hasta el `COMMIT` si alguna operación lo pidiera explícitamente (DEFERRABLE)"*.

Hoy ninguna lo pide. Está puesto porque **habilitarlo después es un `ALTER TABLE` sobre cada FK**, y no cuesta nada dejarlo abierto desde el principio. Es la misma filosofía que multi-sede: preparar la puerta mientras es gratis.

### Tipo 1 — Herencia (1:1 obligatoria)

```
Persona ←── Dueno       (id_persona UNIQUE)
Persona ←── Empleado    (id_persona UNIQUE)
Persona ←── Socio       (id_persona UNIQUE)
Persona ←── Usuario     (id_persona UNIQUE)

Empleado ←── Entrenador     (id_empleado UNIQUE)
Empleado ←── Nutricionista  (id_empleado UNIQUE)
Empleado ←── Recepcionista  (id_empleado UNIQUE)
Empleado ←── Profesor       (id_empleado UNIQUE)
```

El `UNIQUE` es lo que las hace 1:1. Sin él, una persona podría tener dos filas de `Socio`, lo cual no significa nada.

En el diagrama de dbdiagram se ven con la notación `-` (uno a uno) en vez de `>` (muchos a uno).

### Tipo 2 — Pertenencia (muchos a uno)

Las más numerosas. `Membresia → Socio`, `Turno → Sede`, `Comida → Dieta`, etc. Se leen: "muchas membresías pertenecen a un socio".

Cuando la FK es `NOT NULL`, la pertenencia es **obligatoria** (un turno sin sede no puede existir). Cuando es nullable, es **opcional** y el NULL significa algo: `Promocion.id_sede` en NULL = aplica a todas las sedes; `Reserva.id_inscripcion` en NULL = es clase suelta.

### Tipo 3 — Relaciones N:M puras

```
Profesor ←── Profesor_Actividad ──→ Actividad
Socio    ←── Socio_Patologia    ──→ Patologia
```

Tabla intermedia con PK compuesta, sin ID artificial porque no hay nada más que guardar (salvo, en `Socio_Patologia`, atributos que dependen de la combinación).

### Tipo 4 — N:M enriquecido con historia

```
Socio ←── Asignacion_Rutina     ──→ Rutina      (+ Entrenador)
Socio ←── Asignacion_Dieta      ──→ Dieta       (+ Nutricionista)
Socio ←── Asignacion_Entrenador ──→ Entrenador
Socio ←── Reserva               ──→ Turno       (+ Inscripcion, Pago)
Rutina ←── Rutina_Ejercicio     ──→ Ejercicio
```

Igual que el tipo 3 pero con PK subrogada y atributos propios (fechas, estado). La PK subrogada es lo que permite repetir la misma combinación en el tiempo: un socio puede volver a hacer una rutina que ya hizo.

### Tipo 5 — Las dos FK compuestas (el blindaje declarativo)

```
Turno.(id_profesor, id_actividad)             ──→ Profesor_Actividad
Horario_Actividad.(id_profesor, id_actividad) ──→ Profesor_Actividad
```

Son las relaciones más sofisticadas del modelo. En vez de verificar por separado que el profesor existe y que la actividad existe, verifican que **esa combinación** exista en la tabla de habilitaciones. Efecto: es imposible poner un profesor a dictar una actividad que no está habilitado a dar, sin escribir una sola línea de código.

Y aprovechan un comportamiento del estándar SQL: cuando una columna de una FK compuesta es NULL, la restricción **no se evalúa**. Por eso los turnos de musculación (sin profesor) quedan exentos automáticamente, sin necesidad de escribir la excepción.

### Una asimetría real que conviene conocer

`Turno` tiene **además** una FK simple `id_profesor → Profesor`, que es técnicamente redundante (la compuesta ya garantiza validez). `Horario_Actividad` **no la tiene**, sólo la compuesta. Ninguna de las dos está mal: en `Horario_Actividad` alcanza porque `Profesor_Actividad.id_profesor` ya tiene su propia FK a `Profesor`, así que la validez se garantiza transitivamente. Es una diferencia histórica entre migraciones, no un error, pero está bueno saberla para no confundirse leyendo el diagrama.

### Auto-referencias y ciclos

No hay ninguna tabla que se apunte a sí misma, y no hay ciclos obligatorios. Todas las FK son `DEFERRABLE INITIALLY IMMEDIATE`, lo que significa que se validan al instante pero **podrían** diferirse al commit si alguna operación lo necesitara. Es una puerta abierta a futuro, sin costo hoy.

---

## 8. Lo que el diagrama no muestra

Un diagrama entidad-relación muestra estructura, no reglas de comportamiento. Estas cosas existen en la base y **no se ven** en dbdiagram ni en ningún ER:

> **La analogía.** El diagrama es **el plano de la casa**: te dice dónde están las paredes y las puertas. No te dice que la puerta del sótano tiene alarma, que la ventana del norte no abre más de 15 cm, ni que el ascensor no arranca si hay más de ocho personas. Todo eso también es la casa — simplemente no se dibuja. Esta sección es la lista de alarmas.

### Los CHECK (7 restricciones)

Un `CHECK` es una condición que la fila tiene que cumplir para poder existir. Se evalúa en cada `INSERT` y cada `UPDATE`, y su límite es que **sólo puede mirar la fila que se está escribiendo** — no puede consultar otras tablas ni contar nada.

| Tabla | Restricción | Qué impide |
|---|---|---|
| `Turno` | `chk_turno_un_solo_staff` | Entrenador y profesor a la vez (ambos `NULL` sí se permite) |
| `Horario_Actividad` | `chk_horario_un_solo_staff` | Ídem, en el horario semanal |
| `Actividad` | `chk_actividad_tolerancia` | Tolerancia fuera de 0–180 minutos |
| `Congelamiento` | `chk_congelamiento_rango` | Fecha de fin anterior a la de inicio |
| `Horario_Actividad` | `chk_horario_dia_semana` | Día fuera de 1–7 |
| `Horario_Actividad` | `chk_horario_cupo` | Cupo cero o negativo |
| `Horario_Actividad` | `chk_horario_vigencia` | Vigencia que termina antes de empezar |

*(Eran 8: `Consulta_Cruzada.chk_una_referencia` se fue con su tabla.)*

**Por qué `chk_actividad_tolerancia` limita a 0–180 y no a algo más fino.** El techo es holgado a propósito. No está para discutir cuál es una tolerancia razonable —eso lo decide el dueño— sino para **atajar al dedo que escribe 1500 queriendo escribir 15**. Un `CHECK` que intenta imponer criterio de negocio termina peleado con el negocio; uno que sólo ataja lo absurdo, no molesta nunca.

### Los triggers (3 funciones, 7 disparadores)

Un trigger es código que la base ejecuta sola cuando algo pasa. Se usa donde el `CHECK` no llega.

| Función | Migración | Qué impide | Enganchada en |
|---|---|---|---|
| `trg_empleado_debe_tener_subtipo` | 002 | Un `Empleado` que no es ni entrenador, ni profesor, ni recepcionista, ni nutricionista | 5 disparadores: `INSERT` en `Empleado` + `DELETE`/`UPDATE` en cada subtipo |
| `trg_reserva_respeta_cupo` | 006 | Reservar sobre un turno lleno | 1: `INSERT`/`UPDATE` en `Reserva` |
| `trg_turno_cupo_no_menor_a_reservas` | 006 | Bajarle el cupo a un turno que ya tiene más gente anotada | 1: `UPDATE` de `cupo_maximo` en `Turno` |

**Por qué triggers y no CHECK.** Las tres reglas necesitan **contar filas de otra tabla**: ¿cuántos subtipos tiene este empleado? ¿cuántas reservas tiene este turno? Un `CHECK` no puede hacer eso — sólo ve la fila que tiene delante. Es la frontera exacta entre las dos herramientas.

**Por qué los tres son `DEFERRABLE INITIALLY DEFERRED`** (se evalúan al `COMMIT`, no fila por fila). Porque las tres reglas se violan **temporalmente** durante operaciones que son perfectamente válidas:

- Dar de alta un empleado son dos `INSERT` (primero `Empleado`, después su subtipo). Entre uno y otro, el empleado está "colgado" — y es correcto que lo esté por un instante.
- La lista de espera cancela a uno y promueve al siguiente en la misma transacción. Si el trigger corriera fila por fila, el `INSERT` del promovido podría verse como sobrecupo antes de que el `UPDATE` del que canceló libere el lugar.

> **La analogía.** Un trigger inmediato es **un inspector que revisa cada ladrillo**; uno diferido es **el inspector que viene al final de la jornada**. Si estás cambiando una pared de lugar, el primero te frena a mitad de camino por algo que ibas a arreglar en el paso siguiente. El segundo mira el resultado, que es lo que realmente importa.

**El límite honesto del trigger de cupo.** No cubre la carrera entre dos transacciones simultáneas reservando el último lugar — dos personas que aprietan "reservar" en el mismo milisegundo pueden ver las dos que hay lugar. Eso lo resuelve un bloqueo de fila (`SELECT ... FOR UPDATE`) del lado del backend. El trigger tapa **todo lo demás**: bugs, `INSERT` manuales, importaciones, un endpoint nuevo que se olvide de chequear. Los dos mecanismos se complementan; ninguno reemplaza al otro, y decirlo así es más sólido que afirmar que la base está blindada del todo.

### Los índices únicos parciales (4)

DBML no tiene sintaxis para el `WHERE` de un índice, así que en el diagrama se ven como índices únicos comunes, lo cual es engañoso:

| Índice | Condición real | Qué logra |
|---|---|---|
| `asignacion_rutina_una_activa_uidx` | `WHERE estado = 'ACTIVA'` | Una rutina vigente por socio |
| `asignacion_dieta_una_activa_uidx` | `WHERE estado = 'ACTIVA'` | Una dieta vigente por socio |
| `congelamiento_uno_activo_uidx` | `WHERE estado = 'ACTIVO'` | Un congelamiento activo por socio |
| `horario_actividad_slot_uidx` | `WHERE activo` | Un horario activo por sede/actividad/día/hora |

**El `WHERE` es todo.** Sin él, la restricción diría "un socio no puede tener más de una rutina **en toda su vida**", que es absurdo. Con él, dice "no puede tener dos **vigentes al mismo tiempo**", que es la regla real. El historial (`FINALIZADA`, `CANCELADA`) queda fuera del índice y por eso puede repetirse libremente.

Y `Asignacion_Entrenador` **no tiene** el suyo, deliberadamente: ahí varias activas a la vez es lo correcto.

### Lo que tampoco se ve: los defaults con lógica

`Usuario.debe_cambiar_password DEFAULT true` no es un valor cualquiera: es la implementación de una política de seguridad **en una sola palabra**. Toda cuenta nace obligada a cambiar la clave, sin que ningún programador tenga que acordarse de setearlo en el alta — porque el que se olvida de setear un campo obtiene el `DEFAULT`, y acá el `DEFAULT` es el camino seguro.

Es un patrón que vale la pena nombrar: **hacer que la opción segura sea la que ocurre cuando nadie hace nada**. El descuido, en vez de abrir un agujero, cae del lado correcto.

---

## 9. Las cuatro ideas de fondo

Si tuvieras que explicar el modelo entero en cinco minutos, no hablarías de 37 tablas: hablarías de estas cuatro decisiones, porque **cada una se repite en muchas tablas** y entenderlas es entender el resto por deducción.

### Idea 1 — Derivar en vez de guardar

Un dato **derivado** se calcula en el momento de la consulta; uno **guardado** vive en una columna. La regla del modelo: si se puede derivar de forma barata y confiable, no se guarda.

Casos concretos:

| Lo que NO se guarda | De dónde sale |
|---|---|
| Si un socio asistió a un turno | ¿Existe fila en `Asistencia` con ese `id_reserva`? |
| Si un turno ya pasó | Comparar `fecha`/`hora` contra el reloj |
| El peso actual del socio | El `Registro_Salud` más reciente |
| La posición en la lista de espera | El orden por `fecha_reserva` |
| Cuántas clases consumió en la semana | Contar `Reserva` de esa semana |
| El rol de un usuario | En qué tablas de subtipo tiene fila |

**Por qué.** Un dato guardado puede **desincronizarse**; uno derivado, no. Marcar ausentes requeriría un proceso periódico que puede caerse, atrasarse o correr dos veces — y mientras tanto el panel mostraría "pendiente" un turno que venció hace una hora. Derivándolo, si el reloj avanza, la respuesta cambia sola.

> **La analogía.** Guardar lo derivable es **sacarle una foto al reloj**. La foto es exacta en el instante en que se toma y empieza a mentir un segundo después. Mirar el reloj cuesta un poquito más cada vez, pero nunca miente.

**La excepción, y por qué es excepción.** `Congelamiento.dias_aplicados` **se guarda** aunque podría calcularse (`fecha_reanudacion - fecha_inicio`). Se guarda porque es el número que **ya se aplicó** al vencimiento de la membresía: documenta un efecto producido, no un estado presente. Si mañana cambia la forma de contar los días, el histórico tiene que seguir explicando por qué el vencimiento quedó donde quedó.

La regla completa, entonces, es más fina: *no guardes lo que podés derivar, salvo que lo derivado sea un **hecho consumado** que tenga que sobrevivir a un cambio de reglas.* Lo mismo aplica a `Membresia.precio_pactado`.

### Idea 2 — Nada se borra; todo cambia de estado

`Pago` anulado → `estado = 'CANCELADO'`. Deuda perdonada → `CONDONADA`. Socio que se va → fila en `Baja`. Empleado que renuncia → `fecha_egreso`, no `DELETE`.

**Por qué.** Dos razones que se refuerzan:

1. **Contable/auditable.** El registro de que existió un cobro y después se anuló *es en sí mismo información*. Un `DELETE` no deja el dato en cero: lo hace desaparecer, y con él la posibilidad de responder qué pasó.
2. **Referencial.** Un empleado que se fue sigue siendo el autor de rutinas que hoy hacen treinta socios. Borrarlo rompería las FK — o peor, si hubiera `ON DELETE CASCADE`, se llevaría las rutinas puestas.

> **La analogía.** Es la diferencia entre **tachar** y **usar liquid paper**. Tachado, se sigue viendo qué decía y que alguien lo cambió. Con corrector, queda prolijo y nadie puede reconstruir nada — que es exactamente lo que no querés en algo que maneja plata.

### Idea 3 — La regla vive en la estructura, no en el código

La pregunta que ordena todo el modelo: *si el backend tuviera un bug, ¿esta regla igual se cumple?*

| Regla | Dónde vive | Qué la hace cumplir |
|---|---|---|
| Un recepcionista no puede ser autor de una rutina | Estructura | `Rutina.id_entrenador` → `Entrenador`, no → `Empleado` |
| Un profesor no dicta una actividad para la que no está habilitado | Estructura | FK **compuesta** a `Profesor_Actividad` |
| Nadie se anota dos veces al mismo turno | Estructura | `UNIQUE (id_turno, id_socio)` |
| Un socio no tiene dos rutinas vigentes | Estructura | Índice único **parcial** |
| Un turno no se sobrevende | Estructura (casi) | Trigger diferido + bloqueo en el backend |
| Dos personas reservando el último lugar a la vez | **Código** | `SELECT ... FOR UPDATE` |

**El caso más elegante del modelo** es la FK compuesta `(id_profesor, id_actividad) → Profesor_Actividad`. En vez de verificar por separado que el profesor existe y que la actividad existe, verifica que **esa combinación esté habilitada**. Y aprovecha una regla del estándar SQL: cuando una columna de una FK compuesta es `NULL`, la restricción **no se evalúa** — por eso los turnos de musculación (sin profesor) quedan exentos **automáticamente**, sin escribir la excepción en ningún lado.

> **La analogía.** Es la diferencia entre **un cartel que dice "no pasar"** y **una puerta que no abre**. El cartel funciona mientras todos lo lean y lo respeten; la puerta funciona siempre, incluso con el que no sabe leer. Una regla en el backend es un cartel: la respeta el código que se acordó de chequearla. Una regla en el esquema es la puerta.

### Idea 4 — Preparar la puerta mientras es gratis

Tres decisiones del modelo cuestan casi nada hoy y evitan una migración dolorosa mañana:

- **Multi-sede con una sola sede.** Agregar la dimensión sede después, con datos cargados, obligaría a modificar siete tablas y decidir a qué sede pertenece cada fila histórica — un dato que ya nadie puede reconstruir. Tenerla desde el principio cuesta una FK.
- **`Dueno` como tabla con un solo dueño.** Si mañana entra un socio capitalista con 30%, el modelo ya lo soporta.
- **`DEFERRABLE` en todas las FK.** Habilitarlo después es un `ALTER` por cada una.

**Dónde está el límite.** Esto se vuelve sobre-ingeniería cuando la puerta que preparás es para algo que **nadie pidió y nadie va a pedir**. La diferencia práctica: multi-sede cuesta una columna en siete tablas y el negocio (un gimnasio) plausiblemente abre otra sucursal. Una tabla de auditoría que nadie escribe cuesta una entidad entera en el diagrama y no habilita nada — por eso `Consulta_Cruzada` se fue y `Sede` se queda.

---

## 10. Las tres tablas que te van a cuestionar

Estas son las tres que un profesor mira dos veces. Ninguna hay que borrar: **hay que tener la respuesta lista**, y las tres respuestas son de tipos distintos.

### `Recepcionista` — la más débil, y su defensa es estructural

**La objeción.** Tiene **un solo atributo propio** (`turno_laboral`) y **nadie la referencia**, a diferencia de sus tres hermanas: `Entrenador` es apuntada por 5 tablas, `Nutricionista` por 2, `Profesor` por 2. Es la única de las 37 donde hay que *explicar* en vez de *mostrar*.

**La defensa, en tres capas:**

1. **Estructural.** Sin ella, un recepcionista sería un `Empleado` sin ningún subtipo — y el trigger `trg_empleado_debe_tener_subtipo` (migración 002) **lo rechaza**. La jerarquía exige totalidad: todo empleado es al menos uno de los cuatro. Eliminarla obligaría a debilitar esa regla, que es una de las mejores del modelo.
2. **Semántica.** `turno_laboral` (mañana/tarde/noche) sólo tiene sentido para quien atiende el mostrador. En una tabla ancha sería otra columna en `NULL` para los otros tres roles — la razón 3 exactamente.
3. **De simetría.** Los cuatro subtipos son el mismo concepto aplicado cuatro veces. Sacar uno porque "produce menos entidades" convertiría una jerarquía limpia en tres tablas más una excepción que hay que explicar.

**Por qué no la referencia nadie, y por qué está bien.** Los otros roles *producen entidades* (rutinas, dietas, clases dictadas). El recepcionista **opera el sistema**, y esa huella queda registrada — pero en `Asistencia.id_registrado_por`, que apunta a `Usuario`. Es correcto que apunte ahí: lo que interesa auditar es **qué cuenta** hizo la operación, que es lo rastreable, no qué rol tenía esa persona.

**Si te aprietan:** *"Si mañana el recepcionista produjera algo propio —una caja diaria, un turno de caja— colgaría de esta tabla. Hoy no produce nada, y eso no la hace innecesaria: la hace **completa pero silenciosa**."*

**Y el dato honesto:** si aun así se decidiera sacarla, el costo sería **lineal, no cuadrático**. No tiene tablas dependientes, así que es una hoja del grafo; el código del backend ya trata a los cuatro subtipos de forma genérica con un diccionario (`ESPECIALIDADES` en `routers/personal.py`), así que sale de una sola línea. Lo único que habría que editar a mano es la matriz de permisos. Una tarde de trabajo, sin efecto dominó.

### `Dueno` — parece de más con un solo dueño, y se sostiene sin esfuerzo

**La objeción.** Hay un solo dueño. ¿Para qué una tabla?

**La defensa:**

1. **`Sede` y `Promocion` cuelgan de ahí.** No es una hoja decorativa: es un nodo con dos dependientes.
2. **`porcentaje_participacion` no tendría dónde vivir.** En `Persona` sería absurdo (¿qué porcentaje de participación tiene un socio?). Es el ejemplo de manual de la razón 3.
3. **Habilita la sociedad sin migrar.** Dos dueños al 50% entran hoy con un `INSERT`.
4. **Es el ancla de reglas de autorización reales.** El backend tiene dos reglas que dependen de esta tabla: *"sólo un dueño opera sobre la cuenta de otro dueño"* y *"nadie fuera del dueño se desactiva a sí mismo"*.

De las tres, es la más fácil de defender, y la que más caro saldría tocar: eliminarla implicaría rediseñar el modelo de autorización, no editar un diccionario.

### `Consulta_Cruzada` — era decorativa, y por eso ya no está

**La objeción original.** Es una tabla de auditoría, no de operación. Si el sistema no registra efectivamente esas consultas, es decorativa; si las registra, es trazabilidad de acceso a datos de salud, que es de lo más defendible que hay.

**Lo que se verificó.** Se auditó el backend endpoint por endpoint: no tenía clase en `models.py`, ningún router la nombraba, ningún permiso la tocaba. Existía en el DDL y en el diagrama, y en ningún otro lado. **Era decorativa, confirmado.**

**Qué se hizo.** Se eliminó del `schema.sql`, con la lógica desarrollada en el bloque G: una tabla de auditoría que no audita nada no es trazabilidad, es la *promesa* de trazabilidad, y hace que el diagrama afirme algo falso sobre el sistema.

**La respuesta si te preguntan por qué no está en el DER viejo que ya entregaste.** *"Estaba, y la saqué después de auditar el backend. El modelo tiene que describir el sistema que existe. La alternativa honesta era implementarla; entre dejar una promesa vacía en el diagrama y sacarla, saqué."*

> **El principio que unifica las tres:** una tabla se justifica por **uso o por estructura**, nunca por intención. `Recepcionista` se justifica por estructura (sin ella se rompe la jerarquía). `Dueno`, por uso (dos tablas cuelgan) y por estructura. `Consulta_Cruzada` no tenía ninguna de las dos.

---

## 11. El modelo de 13 tablas

Esta sección compara contra un modelo alternativo de 13 tablas para el mismo dominio. No es un análisis de un diagrama concreto: es **qué se pierde estructuralmente** al modelar un gimnasio con 13 tablas en vez de 37.

Lo primero que se puede afirmar: **24 tablas de diferencia no son 24 detalles**. Con 13 tablas, un modelo de gimnasio típicamente cubre esto:

```
Persona/Usuario · Socio · Empleado · Membresia · Pago ·
Actividad · Turno · Reserva · Asistencia · Rutina ·
Ejercicio · Dieta · (alguna intermedia)
```

Lo que **necesariamente** queda afuera, y por qué duele cada cosa:

### 1. La jerarquía de empleados colapsada
Sin `Entrenador` / `Nutricionista` / `Recepcionista` / `Profesor` separados, aparece una columna `tipo` en `Empleado`. Consecuencias inevitables: los atributos propios de cada rol (`matricula`, `turno_laboral`, `especialidad`) conviven en la misma tabla en NULL para quien no corresponde; **nadie puede tener dos roles a la vez**; y `Rutina.id_entrenador` pasa a apuntar a `Empleado`, con lo cual la base ya no impide que un recepcionista figure como autor de una rutina.

### 2. La separación plantilla / asignación
Si no existen `Asignacion_Rutina` y `Asignacion_Dieta`, la rutina se asigna metiendo `id_socio` directamente en `Rutina`. Eso significa: una rutina por socio (no reutilizable), duplicación completa del contenido para treinta socios que hacen lo mismo, y **cero historial** — al cambiar de rutina se pierde la anterior.

### 3. El detalle de las plantillas
Sin `Rutina_Ejercicio` y `Comida`, el contenido de rutinas y dietas termina en un campo de texto. Se vuelve imposible responder "¿qué rutinas usan sentadilla?" o contar calorías por día.

### 4. Toda la historización
Sin `Baja`, `Registro_Salud` y `Congelamiento`: no hay métricas de retención, no hay progresión física del socio (que es el producto que el socio percibe), y no hay forma de pausar una membresía sin regalar o robar días.

### 5. La flexibilidad comercial
Sin `Tipo_Membresia`, `Plan_Actividad` y `Promocion`, los precios y modalidades quedan como columnas fijas o texto. Cada plan nuevo que invente el dueño requiere un programador.

### 6. Las tablas N:M
Sin `Socio_Patologia` ni `Profesor_Actividad`, las patologías van a un campo de texto (imposible consultar) y no hay forma de saber —ni de hacer cumplir— qué profesor puede dictar qué.

### 7. La capa de integridad completa
Sin `Profesor_Actividad` no existen las FK compuestas, y sin `Horario_Actividad` no hay generación automática de turnos. Todas esas reglas pasan a depender del código de la aplicación.

### Y la observación honesta al revés

Con 13 tablas **se puede tener un sistema que funcione**, y probablemente esa persona lo tenga andando. La diferencia no está en si funciona hoy, sino en:

- qué pasa cuando el dueño pide una función nueva (¿alcanza con un INSERT o hay que migrar la estructura?);
- qué pasa cuando dos personas hacen la misma operación a la vez;
- qué se puede responder sobre el pasado (¿cuántos socios se fueron por mora el año pasado? ¿cuánto bajó de peso este socio desde que empezó?);
- y cuántas de las reglas del negocio sobreviven a un bug del backend.

El modelo de 37 tablas no es "más prolijo": es un modelo donde **una parte importante de las reglas del negocio están escritas en la estructura**, y por lo tanto no dependen de que nadie se acuerde de programarlas.

Y la contracara honesta, que conviene decir antes de que te la digan: **más tablas no es automáticamente mejor**. La prueba está dentro de este mismo modelo — `Consulta_Cruzada` era una tabla más y se eliminó, porque no aportaba ni uso ni estructura. El criterio nunca fue "más granular"; fue "cada tabla tiene que estar justificada por una de las seis razones". 37 es el número que salió de aplicar ese criterio, no una meta.

---

## Apéndice — Preguntas de defensa y cómo responderlas

Preguntas probables en una defensa oral, con el núcleo de la respuesta:

**¿Por qué no una sola tabla de empleados con un campo tipo?**
Porque los subtipos son *solapados* (una persona puede ser entrenador y profesor a la vez), lo cual una columna de valor único no puede representar; y porque cada subtipo tiene atributos exclusivos que en una tabla única quedarían en NULL sin significar "se desconoce" sino "no aplica".

**¿`precio_pactado` y `precio_actual` no es redundancia?**
No: son dos hechos distintos. Uno es el precio histórico al que se vendió esa membresía (inmutable), el otro el precio vigente para nuevas ventas. Derivar uno del otro reescribiría la historia contable en cada aumento.

**¿Por qué musculación es una actividad y no algo aparte?**
Para que todo el sistema de turnos, reservas e inscripciones funcione igual para las tres sin duplicar lógica. Las diferencias se expresan como datos (tolerancia, horas de cancelación, staff), no como código.

**¿Por qué no guardan si el socio asistió?**
Porque es derivable: existe fila en `Asistencia` con ese `id_reserva`. Guardarlo obligaría a un proceso periódico que puede fallar, y mientras tanto el dato guardado estaría mintiendo.

**¿Por qué tantos estados en vez de borrar filas?**
Porque el registro de que algo existió y se anuló es información auditable, sobre todo en pagos y deudas. Un DELETE destruye evidencia.

**¿Qué es un índice único parcial y por qué el WHERE es tan importante?**
Un índice que sólo se aplica a las filas que cumplen una condición. Sin el `WHERE estado = 'ACTIVA'`, la regla diría "un socio no puede tener más de una rutina en toda su vida" en vez de "no puede tener dos vigentes a la vez".

### Las que preguntan por lo que NO está

**¿Por qué `Recepcionista` no la referencia nadie? ¿No sobra?**
No sobra: sin ella, un recepcionista sería un `Empleado` sin subtipo y el trigger de totalidad lo rechaza. Los otros roles producen entidades (rutinas, dietas); el recepcionista opera el sistema, y esa huella queda en `Asistencia.id_registrado_por`, que apunta a `Usuario` porque lo auditable es la cuenta, no el rol. Ver [§10](#10-las-tres-tablas-que-te-van-a-cuestionar).

**¿Por qué sacaste `Consulta_Cruzada` si estaba en el DER que entregaste?**
Porque al auditar el backend se comprobó que ningún endpoint la escribía ni la leía. Una tabla de auditoría que no registra nada no es trazabilidad: es la promesa de trazabilidad, y hace que el diagrama afirme algo falso sobre el sistema. La alternativa honesta era implementarla; entre eso y dejar una promesa vacía, se sacó.

**¿Para qué una tabla `Dueno` si hay un solo dueño?**
Porque `Sede` y `Promocion` cuelgan de ahí, porque `porcentaje_participacion` no tendría dónde vivir sin ella, y porque es el ancla de dos reglas de autorización del backend. Además, una sociedad de dos dueños entra hoy con un `INSERT` en vez de una migración.

**¿Por qué hay migraciones si `schema.sql` ya tiene todo?**
Porque `schema.sql` no se puede volver a correr sobre una base con datos. Las migraciones son el camino incremental para la base que ya existe; `schema.sql` es el camino directo para una base nueva. Los dos llegan al mismo estado, y cada migración se escribe en los dos lugares. Ver [§5](#5-schemasql-migraciones-y-la-base-real).

**¿El gimnasio cobra sólo prepago?**
No. La cuota es prepago (mostrador o Mercado Pago puntual, sin débito automático recurrente), pero **la mora no bloquea el ingreso**: el fichaje se registra igual y devuelve una advertencia. Es una decisión de negocio explícita — dejar a alguien afuera lo decide una persona en el mostrador mirando el caso, y un backend que devuelve 403 hace que ese criterio no pueda existir. Además, si el ingreso no se registrara, se perdería el dato de que esa persona estuvo.

### Las de teoría pura

**¿Esta jerarquía es disjunta o solapada?**
Solapada: una persona puede ser `Entrenador` y `Profesor` a la vez. Por eso no sirve un discriminador único y la restricción de totalidad ("todo empleado es al menos un subtipo") necesita un trigger en vez de un `CHECK`.

**¿Es total o parcial?**
Total, y forzada: el trigger `trg_empleado_debe_tener_subtipo` impide que exista un `Empleado` sin ninguna fila de subtipo.

**¿Por qué `Socio_Patologia` tiene atributos propios? ¿No es sólo un vínculo?**
`fecha_diagnostico` y `observaciones` dependen de **la combinación** socio + patología, no de ninguno de los dos por separado. La fecha en que a Fulano le diagnosticaron diabetes no es un atributo de Fulano ni de la diabetes. Eso es 2FN correctamente aplicada.

**¿Hay alguna violación de forma normal en el modelo?**
No conocida hasta 3FN. Los dos casos que *parecen* violación y no lo son: `Membresia.precio_pactado` vs `Tipo_Membresia.precio_actual` (son hechos distintos, no redundancia) y `Socio.activo` vs la tabla `Baja` (uno responde "¿está activo hoy?", el otro "¿cuál fue su trayectoria?"). El dueño de un empleado, en cambio, **no** está en `Empleado`: se obtiene navegando `Empleado → Sede → Dueno`, justamente para no crear una dependencia transitiva.

**¿Por qué `repeticiones` es `varchar` y no `int`?**
Porque en el gimnasio real se escribe "8-12" o "al fallo". Forzarlo a número perdería información que el entrenador necesita transmitir. Es un caso donde el tipo más estricto sería el peor tipo.

---

## Cómo verificar cualquier número de este documento

Todo lo que se afirma acá se puede recontar en diez segundos. Desde `Proyecto/db/`:

```bash
grep -c '^CREATE TABLE' schema.sql          # 37 tablas
grep -c '^CREATE TYPE'  schema.sql          # 13 enums
grep -c 'ADD FOREIGN KEY' schema.sql        # 65 FK simples (+2 compuestas = 67)
grep -o 'CONSTRAINT chk_[a-z_]*' schema.sql | sort -u | wc -l   # 7 CHECK
grep -c 'CREATE CONSTRAINT TRIGGER' schema.sql                  # 7 disparadores
grep -c 'CREATE OR REPLACE FUNCTION' schema.sql                 # 3 funciones
```

Y para verificar que el backend no se desincronizó del esquema:

```bash
grep -c 'class .*(Base):' ../../backend/models.py   # tiene que dar 37
```

Si esos dos números difieren, hay una tabla en el DDL que el backend no mapea (o al revés) — que es exactamente el bug que apareció dos veces con las migraciones 006 y 008.

---

*Documento verificado el 21 de agosto de 2026 contra `Proyecto/db/schema.sql`: **37 tablas, 13 enums, 67 claves foráneas (65 simples + 2 compuestas), 7 CHECK, 3 funciones de trigger con 7 disparadores, 4 índices únicos parciales y 13 tablas hoja**. Las 9 migraciones están incorporadas al DDL.*
