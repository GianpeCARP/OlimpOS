# A-05 · El modelo de datos

*Piso del capítulo: la fila que existe o no existe, y las restricciones que la base hace cumplir sola.*

La base de OlimpOS tiene 41 tablas. Este capítulo no las recorre una por una: explica **las cinco formas de
modelar** que se repiten en ellas, porque entendidas esas cinco, cualquier tabla del esquema se lee sola.
Cómo funcionan una tabla, una clave foránea o una transacción está en
[bases de datos relacionales](A0-07-bases-de-datos-relacionales.md); acá está qué decidió este sistema con
esas herramientas.

La fuente de verdad es `db/schema.sql`, escrito a mano. Los modelos de `backend/models.py` lo **describen**,
no lo definen ([mapeo objeto-relacional](A0-09-el-orm.md#mapeo-objeto-relacional-y-relación)). Y coinciden:
comparando las dos cosas con un script —cada tabla del esquema contra las que mapean los modelos, y dentro de
cada tabla cada columna— dan **41 tablas en los dos lados y ninguna columna distinta**. Es la regla de
`CLAUDE.md` —*"db/schema.sql y Neon coinciden nombre por nombre"*— verificada contra el código.

---

## El mapa: 41 tablas, ocho grupos

| Grupo | Tablas | Qué modela |
|---|---|---|
| Personas | `Persona`, `Telefono`, `Contacto_Emergencia`, `Usuario` | quién es alguien, cómo se lo contacta y con qué entra |
| Roles | `Dueno`, `Socio`, `Empleado`, `Entrenador`, `Nutricionista`, `Recepcionista`, `Profesor` | qué es alguien para el gimnasio |
| Organización | `Sede`, `Franja_Laboral` | dónde y en qué horario |
| Plata | `Tipo_Membresia`, `Membresia`, `Congelamiento`, `Promocion`, `Pago`, `Baja` | qué se cobró, qué período corre, cómo terminó |
| Actividades | `Actividad`, `Plan_Actividad`, `Profesor_Actividad`, `Horario_Actividad`, `Turno`, `Inscripcion_Actividad`, `Reserva`, `Asistencia` | las clases, sus turnos y quién va |
| Entrenamiento | `Ejercicio`, `Rutina`, `Rutina_Ejercicio`, `Asignacion_Rutina`, `Registro_Ejercicio`, `Asignacion_Entrenador` | los planes de entrenamiento y lo que se hizo |
| Nutrición | `Catalogo_Comida`, `Dieta`, `Comida`, `Asignacion_Dieta`, `Registro_Comida` | los planes de comida y lo que se comió |
| Salud | `Patologia`, `Socio_Patologia`, `Registro_Salud` | condiciones médicas y mediciones |

4 + 7 + 2 + 6 + 8 + 6 + 5 + 3 = 41.

---

## Tabla subtipo (especialización)

### El problema de origen

¿Cómo se guarda qué es alguien? La respuesta obvia es una columna: `Usuario.rol = 'entrenador'`. Tiene tres
problemas, y los tres aparecen en este gimnasio:

1. **Una persona puede ser varias cosas.** El dueño entrena en su propio gimnasio: es dueño **y** socio. Un
   entrenador puede ser socio. Una sola columna no guarda dos valores.
2. **Cada rol tiene sus propios datos.** Un socio tiene número de socio, fecha de alta y objetivo; una
   recepcionista tiene una franja horaria; un entrenador, una especialidad. Con una tabla única, cada columna
   de cada rol estaría vacía para todos los que no lo tienen.
3. **La columna sería una segunda fuente de verdad.** El comentario de la tabla `Usuario` lo dice
   (`db/schema.sql:145-146`): *"El rol se DERIVA de en qué subtipo aparece la persona: no hay columna de rol
   porque sería una segunda fuente de verdad."* Si la columna dijera "socio" y no hubiera fila en `Socio`, ¿qué
   es esa persona?

### La especialización

La respuesta del esquema es **partir la entidad**. Hay una tabla con lo que todos tienen —`Persona`: nombre,
DNI, domicilio— y, colgando de ella, una tabla por cada cosa que alguien puede ser. Y la especialización tiene
dos niveles, porque "empleado" también se especializa:

```
Persona
 ├── Usuario        (la cuenta de acceso)
 ├── Dueno
 ├── Socio
 └── Empleado
      ├── Entrenador
      ├── Nutricionista
      ├── Recepcionista
      └── Profesor
```

En el vocabulario del modelado entidad-relación esto se llama **especialización** —o generalización, leída de
abajo hacia arriba—, y cada tabla hija establece con la madre una relación "es un": un socio **es una**
persona. Esta especialización tiene dos propiedades con nombre propio:

- **Superpuesta**, no disjunta: una persona puede estar a la vez en `Dueno` y en `Socio`, o en `Socio` y en
  `Empleado`. También **entre los cuatro hijos de `Empleado`**: el comentario de `Entrenador` lo dice desde el
  primer día (`schema.sql:213-215`, *"son subtipos SOLAPADOS, una misma persona puede tener las dos filas si
  cumple los dos roles"*), y hasta el 2026-09-29 sólo la base lo permitía —la app trataba el rol de un empleado
  como uno solo (ver [el rol que se apaga](A-10-bajas-logicas.md#el-rol-que-se-apaga))—.
- **Parcial**, no total: una persona puede no estar en ninguna tabla hija.

> **↓ Capa 1 — la fila que existe o no existe en la tabla hija.** Éste es el piso.

Cada tabla hija apunta a su madre con una clave foránea que es, además, **`NOT NULL UNIQUE`**:

| Tabla hija | Columna | Línea |
|---|---|---|
| `Usuario` | `id_persona integer NOT NULL UNIQUE` | `schema.sql:134` |
| `Dueno` | `id_persona integer NOT NULL UNIQUE` | `schema.sql:153` |
| `Empleado` | `id_persona integer NOT NULL UNIQUE` | `schema.sql:188` |
| `Socio` | `id_persona integer NOT NULL UNIQUE` | `schema.sql:278` |
| `Entrenador` | `id_empleado integer NOT NULL UNIQUE` | `schema.sql:205` |
| `Profesor` | `id_empleado integer NOT NULL UNIQUE` | `schema.sql:225` |
| `Nutricionista` | `id_empleado integer NOT NULL UNIQUE` | `schema.sql:238` |
| `Recepcionista` | `id_empleado integer NOT NULL UNIQUE` | `schema.sql:260` |

`UNIQUE` es lo que convierte la relación en uno a uno: una persona puede tener **a lo sumo una** fila en
`Socio`. Y a partir de ahí, que alguien sea socio **no está escrito en ningún campo**: es la existencia de esa
fila. Preguntar si una persona es socio es preguntar si hay una fila en `Socio` con su `id_persona`. Cómo se
convierte eso en roles de sesión, y cuántas consultas cuesta, es tema de
[derivación de roles](A-06-los-seis-roles.md#derivación-de-roles).

**Con una excepción, en los cuatro subtipos del empleado.** Ahí la existencia de la fila dejó de alcanzar: las
cuatro tienen una columna `activo` (`schema.sql:209`, `:228`, `:241`, `:262`) y la pregunta se responde con el
flag, no con la fila. La fila de un rol que la persona dejó de cumplir **queda**, porque es la percha de todo su
historial —rutinas, socios a cargo, horarios, turnos— y borrarla se lo llevaba puesto. El porqué completo, con
lo que se descartó y lo que se paga, está en
[el rol que se apaga](A-10-bajas-logicas.md#el-rol-que-se-apaga). Los otros cuatro subtipos —`Usuario`, `Dueno`,
`Socio`, `Empleado`— no lo necesitan: `Socio.activo` y `Empleado.activo` ya existían por la baja lógica, y
`Dueno` no se apaga.

### Nota marcada · lo que el esquema todavía llama "abierto"

El mismo comentario de `Usuario` termina con una advertencia (`schema.sql:147-149`): *"ABIERTO: una Persona
puede ser Socio Y Empleado a la vez (los UNIQUE son independientes entre sí). Si eso ocurre, la derivación del
rol queda ambigua."*

En el código **ya no es un problema abierto**. La ambigüedad existía si el rol tenía que ser uno solo; la
función que deriva los roles devuelve una **lista** y los acumula —su docstring da el ejemplo de *"un entrenador
puede ser socio también"*—, y la matriz de permisos le da a quien tiene varios el permiso más alto de todos. La
especialización superpuesta está resuelta; el comentario del esquema es anterior a esa resolución. Gana el
código.

### Por qué está hecho así

**Qué se optimiza:** una sola fuente de verdad sobre qué es cada persona, y datos de cada rol sin columnas
vacías para los demás.

**Qué se paga:** saber qué es alguien cuesta consultas —entre tres y siete, medidas en A-06—, y dar de alta un
socio son dos filas, persona y socio, la segunda con el id de la primera; por eso el alta usa
[`flush` antes de `commit`](A0-09-el-orm.md#flush-contra-commit).

**Cómo se llama:** especialización superpuesta y parcial, implementada como **una tabla por subtipo** con clave
foránea única hacia la tabla madre.

---

## Log append-only

### El problema de origen

El socio registra lo que entrenó, lo que comió y cuánto pesa. En esas tablas **el historial es el dato**: un
gráfico de peso necesita cada medición pasada, y una serie hecha hace un mes sigue siendo una serie hecha. Si
una carga nueva reemplazara a la anterior, el progreso se borraría a sí mismo.

La respuesta es un **log de sólo agregar** (*append-only*): se escribe una fila nueva por cada hecho, y las
viejas no se modifican. `CLAUDE.md` distingue estas tablas de los planes: *"`Registro_*` es un log append-only
por fecha, nunca se pisa"*, mientras que una rutina o una dieta sí se editan.

### La fila que nunca se actualiza, tabla por tabla

> **↓ Capa 1 — el grano de cada registro.** Éste es el piso.

Las tres tablas de registro cumplen lo mismo a nivel de día: **ninguna fila de un día pasado se modifica
nunca**. Lo que cambia entre ellas es qué pasa **dentro del día de hoy**, y eso lo decide el índice de cada una:

| Tabla | Única por | Si se carga dos veces el mismo día |
|---|---|---|
| `Registro_Salud` | socio y fecha (`schema.sql:1089`) | **se rechaza** con un 409 |
| `Registro_Ejercicio` | socio, ejercicio y fecha (`schema.sql:1142-1143`) | **se acumula** en la fila del día |
| `Registro_Comida` | nada: el índice no es único (`schema.sql:1158`) | **se agrega** otra fila |

La medición rechaza la segunda carga en vez de reemplazarla, y el docstring de `cargar_medicion()` en
`backend/routers/portal.py` explica por qué: *"Sobrescribir le borraría al socio un dato que él mismo cargó, sin
avisarle — y la serie perdería el registro de que ese día midió otra cosa."*

El ejercicio es el caso fino. Su grano es un ejercicio por día, así que la segunda serie no crea una fila: se
suma a la del día. `cargar_registro_ejercicio()` (`portal.py:1212`) lo describe en su docstring: la primera serie
crea la fila *"y cada serie siguiente la ACUMULA (una más en series_hechas, sus reps agregadas a la lista, y el
peso se queda con el MÁXIMO del día, que es lo que cuenta para el récord). Es un upsert, no un insert"*. La fila
de hoy sí se actualiza, pero sólo **creciendo**: nunca se pierde una serie. Lo único que se resume es el peso,
que guarda el máximo y no el de cada serie, porque es lo que mide un récord.

Las comidas, en cambio, son varias por día y cada una es un hecho distinto: una fila cada una.

---

## Asignación con estado

### El problema de origen

Un socio sigue una rutina y una dieta, y cambian con el tiempo. Hace falta guardar dos cosas que parecen
contradecirse: **todas** las rutinas que tuvo —el historial— y **cuál es la actual** —una sola—.

La solución son las tablas `Asignacion_Rutina` y `Asignacion_Dieta`. Cada asignación es una fila con su
`estado`: `ACTIVA`, `FINALIZADA` o `CANCELADA` (el enumerado `estado_asignacion`, y el porqué de guardar ese
estado en vez de derivarlo está en [estado guardado](A-09-estados-derivados.md#estado-guardado)). Las viejas
quedan finalizadas; la actual es la activa.

### El índice único parcial que la protege

> **↓ Capa 1 — la regla que hace cumplir la base.** Éste es el piso.

"Una sola activa por socio" no lo garantiza el código: lo garantiza la base. `db/schema.sql:1135-1136`:

```sql
CREATE UNIQUE INDEX asignacion_rutina_una_activa_uidx ON "Asignacion_Rutina" (id_socio)
    WHERE (estado = 'ACTIVA'::estado_asignacion);
```

y su gemelo para las dietas en las líneas 1155-1156. Es un índice **único** que sólo abarca las filas **activas**.
El comentario que lo documenta (`schema.sql:788-790`) explica por qué el `WHERE` es la mitad de la idea: *"El
historial no cuenta, para eso el índice es parcial. Sin el WHERE diría 'una sola rutina en toda su vida', que
sería absurdo."* Cómo funciona un índice parcial por dentro está en
[índice único parcial](A0-08-sql-indices-y-planes.md#índice-único-parcial).

Que lo garantice la base y no el código cambia qué puede fallar. Si dos pedidos intentaran activar dos rutinas a
la vez para el mismo socio, el código de cada uno podría creer que no había otra; la base rechaza la segunda
igual. Una regla que vive en la base no depende de que todo el código la respete.

### La misma jugada, en la plata

El patrón se repite donde más importa. `Membresia` tiene su propio índice de una activa por socio
(`schema.sql:1095-1096`), y su comentario dice por qué es crítico (líneas 390-392): *"Congelamiento cuelga de acá:
dos activas romperían toda la lógica de congelamiento y de extensión de vencimiento."* Es la garantía, del lado de
la base, de la invariante de [un solo período en curso](A-02-prepago-puro.md#sin-cobros-por-adelantado). Y
`Congelamiento` tiene el suyo: una sola pausa activa por membresía.

### La regla escrita por ausencia

`Asignacion_Entrenador` también tiene estado, y **no** tiene índice de una activa. Tiene un índice único sobre
socio, entrenador y fecha de inicio (`schema.sql:1145-1146`), que impide asignar dos veces lo mismo el mismo día,
pero nada impide que un socio tenga dos entrenadores activos a la vez. Y está bien: `CLAUDE.md` dice que
*"varios entrenadores a la vez es normal"*. En este esquema, la ausencia de un índice también es una decisión.

---

## Catálogo contra observación

### Dos preguntas, dos tablas

El historial médico de un socio responde dos preguntas distintas, y cada una tiene su tabla:

| Tabla | Pregunta | Columnas |
|---|---|---|
| `Patologia` | ¿**qué** condiciones existen? | `id_patologia`, `nombre` (único), `descripcion` |
| `Socio_Patologia` | ¿**qué tiene** esta persona, y **qué hacer**? | `id_socio`, `id_patologia`, `fecha_diagnostico`, `observaciones` |

`CLAUDE.md` lo formula así: *"el catálogo dice QUÉ tiene y las observaciones por socio dicen QUÉ HACER"*.
"Hernia de disco" es una fila del catálogo; que un socio la tiene desde 2024 y que **no tiene que cargar peso
sobre la espalda** es una fila de `Socio_Patologia`, y esas observaciones son lo que un entrenador necesita leer
antes de armarle una rutina.

> **↓ Capa 1 — por qué son dos y no una.** Éste es el piso.

Los comentarios del esquema justifican la separación con las formas normales, una por una. De `Patologia`
(`schema.sql:287-288`): *"3FN: catálogo. El nombre depende de la patología, no del socio que la tiene."* De
`Socio_Patologia` (`schema.sql:300-303`): *"1FN: rompe lo que sería un varchar multivaluado de patologías. 2FN:
fecha_diagnostico y observaciones dependen de la clave COMPLETA (socio + patología)"*. La clave primaria de la
segunda es el par `(id_socio, id_patologia)`: un socio no puede tener la misma condición cargada dos veces. Qué
exige cada forma normal está en [normalización](A0-07-bases-de-datos-relacionales.md#normalización-3fn).

### El patrón, en otros lados

La misma separación aparece en el entrenamiento —`Ejercicio` es el catálogo de ejercicios; `Rutina_Ejercicio` dice
qué ejercicio va en esta rutina, en qué día y con cuántas series— y en la nutrición, con `Catalogo_Comida` frente a
las comidas de una dieta y a lo que el socio registró. Siempre lo mismo: **qué existe**, separado de **qué pasa con
esto en este caso**.

Quién puede ver el historial médico es un tema de permisos, y tiene su propia regla: el recepcionista no lo ve, y
el botón se [omite en vez de deshabilitarse](A-08-autorizacion.md#omitir-en-vez-de-deshabilitar).

---

## Almacén que no es tabla

### Estado que no vive en ninguna fila

Hay un dato del sistema que no está en la base. Los entrenadores cargan en cada ejercicio un enlace a un video de
YouTube, y un proceso aparte, `backend/demonio_videos.py`, lo descarga al servidor para que el socio lo vea sin
depender de YouTube. La pregunta "¿este video ya está descargado?" no tiene columna.

> **↓ Capa 1 — el archivo que existe o no en el disco.** Éste es el piso.

El docstring del demonio define el estado sin rodeos (`demonio_videos.py:10-11`): *"'Ya descargado' = existe
VIDEOS_DIR/<id de youtube>.mp4 (ver videos.py). No hay estado en la base: si una descarga falla, la próxima pasada
la reintenta."* El nombre del archivo sale del id del video (`archivo_de()`, `backend/videos.py:60`), y que ese
archivo exista **es** que el video está descargado.

La razón es la misma de [derivar en vez de almacenar](A-09-estados-derivados.md#estado-derivado): una columna
`descargado = true` podría mentir —alguien borra el archivo, se cambia el disco— y el sistema la seguiría creyendo.
La existencia de un archivo no puede mentir sobre sí misma. Se pregunta donde está la verdad.

Hay un detalle de implementación que protege esa verdad. El demonio descarga a una carpeta temporal y recién al
terminar mueve el archivo a su lugar (`demonio_videos.py:37-39`): *"así /videos nunca sirve un archivo a medio
bajar, que el socio vería cortado"*. Mover un archivo dentro del mismo disco es una operación que ocurre de una
vez: el archivo aparece completo o no aparece, y por eso "existe" sigue queriendo decir "está listo".

Este almacén tiene una consecuencia en la especificación: `PROCESOS-LOGICOS-REQUERIDOS.md` sólo puede nombrar
tablas, así que el proceso que descarga videos aparece ahí leyendo `Ejercicio` y sin escribir nada. Ese límite de la
notación se explica en [cómo leer los procesos](A-12-como-leer-los-procesos.md), y el demonio completo, en
[el demonio de videos](C-08-demonio-videos.md).

---

## Con qué se conecta

- **Existe por culpa de…** la [tabla subtipo](#tabla-subtipo-especialización) y la
  [derivación de roles](A-06-los-seis-roles.md#derivación-de-roles): como no hay columna de rol, saber qué es alguien
  cuesta consultas.
- **Es la misma idea que…** el [estado derivado](A-09-estados-derivados.md#estado-derivado): ni el rol ni el video
  descargado tienen columna, porque una columna sería otra fuente de verdad que puede mentir.
- **Es la misma idea que…** el [índice único parcial](A0-08-sql-indices-y-planes.md#índice-único-parcial): la regla
  de una sola activa vive en la base, no en el código.
- **Existe por culpa de…** [sin cobros por adelantado](A-02-prepago-puro.md#sin-cobros-por-adelantado): la base
  garantiza una sola membresía activa por socio, la misma invariante que la regla de negocio.
- **Es la misma idea que…** la [normalización](A0-07-bases-de-datos-relacionales.md#normalización-3fn): los
  comentarios del esquema justifican cada separación de tablas con su forma normal.
