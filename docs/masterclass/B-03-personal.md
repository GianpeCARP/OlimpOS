# B-03 · Personal

*Procesos 29 a 37. Piso del capítulo: la línea que implementa cada paso, en las tres capas.*

Nueve procesos sobre la ficha del empleado, en tres temas:

| Tema | Procesos |
|---|---|
| La ficha: listar, dar de alta, consultar y editar | 29, 30, 34, 35 |
| La baja y la vuelta | 36, 37 |
| Los catálogos que usan otros formularios | 31, 32, 33 |

El porqué de fondo ya está en la Parte A: que el rol sea una fila y no una columna, en
[la tabla subtipo](A-05-modelo-de-datos.md#tabla-subtipo-especialización); cómo se calcula, en
[derivación de roles](A-06-los-seis-roles.md#derivación-de-roles); las credenciales del alta, en
[contraseña temporal](A-07-autenticacion.md#contraseña-temporal-y-primer-ingreso); por qué la baja de
un empleado le apaga siempre la cuenta, en
[el acople total](A-10-bajas-logicas.md#en-los-empleados-el-acople-es-total). Este capítulo sigue el
código de cada proceso, cruza las tablas contra la línea DFD y registra cada rechazo.

**Lo que se corrió, y cómo.** Varios hallazgos de este capítulo dependen de lo que hace PostgreSQL con
una clave foránea, y eso no se ve leyendo. Se probaron llamando a las funciones reales de
`backend/routers/personal.py` —con una sesión del Dueño armada a mano, sin HTTP— de dos maneras, según
qué había disponible en la máquina:

- **Contra un PostgreSQL 17 local y descartable**, creado en una carpeta temporal y cargado con
  `db/schema.sql`, con la variable de la base apuntando ahí antes de importar el backend y el servidor
  borrado al terminar. Así se corrieron los hallazgos originales del capítulo.
- **Contra la base real**, cuando no hubo Postgres local a mano, con **todo lo creado marcado** —un
  prefijo reconocible en el DNI— y **borrado al terminar**, comparando los conteos de las once tablas
  tocadas antes y después. Así se corrió el cambio de roles múltiples de los procesos 29, 30 y 35: 22
  chequeos, y la base quedó idéntica. Es la única técnica que sirve cuando el 409 que hay que comprobar
  ya no existe y lo que hay que ver es qué queda escrito.

Cada resultado obtenido de cualquiera de las dos maneras dice **corrido**; el resto es lectura.

---

## Piezas comunes

### Quién puede qué en esta sección

| Barrera | Quién la tiene | La usan |
|---|---|---|
| Sección `PERSONAL` en lectura | Dueño (total), Recepcionista (lectura) | 29, 32, 34 |
| Acción `ALTA_BAJA_PERSONAL` | Dueño | 30, 35, 36, 37 |
| Sección `RUTINAS` en lectura | Dueño, Recepcionista, Entrenador, Nutricionista | 31 |
| Sección `NUTRICION` en lectura | Dueño, Recepcionista, Entrenador, Nutricionista | 33 |

El Recepcionista ve la grilla entera porque *"es operativo, necesita saber quién trabaja hoy"*
(`Proyecto - PWA/src/frontend/src/views/personal/PersonalView.tsx:40-42`), pero contratar y desvincular
es *"una decisión del negocio, no operativa del día a día"* (`backend/routers/personal.py:220-222`).
Las dos últimas filas son la rareza de la sección: dos endpoints que viven bajo `/personal` y no piden
la sección Personal, porque los usan los formularios de Rutinas y de Nutrición (procesos 31 y 33).

Una regla más, a nivel de fila: **nadie se da de baja a sí mismo**. Está en los tres lugares —el
backend la hace cumplir (`personal.py:661-664`), y las dos apps omiten el botón en la propia tarjeta
(`PersonalView.tsx:54-58`, `Flet/Proyecto/app/views/personal.py:145-146`)—, y el comentario del
backend da el porqué: *"se quedaría sin acceso en el acto, y si era el único con el permiso no habría
quien lo revierta"*.

### Los roles son filas, y una fila apagada sigue siendo una fila

Un empleado es Entrenador, Nutricionista, Recepcionista o Profesor según en cuál de las cuatro tablas
hijas tenga fila **prendida**. El router lo lleva a una tabla de datos, `ESPECIALIDADES`
(`personal.py:83-88`), que dice qué clase corresponde a cada rol y qué campos acepta cada una:

| Rol | Tabla | Campos propios |
|---|---|---|
| Entrenador | `Entrenador` | `titulo`, `especialidad`, `matricula` |
| Nutricionista | `Nutricionista` | `titulo`, `matricula` |
| Recepcionista | `Recepcionista` | `id_franja_laboral` |
| Profesor | `Profesor` | `titulo`, `especialidad` |

Esa tabla la usan el alta (`:290-293`) y `_aplicar_roles()` (`:370-427`), que es por donde pasan la
edición y todo cambio de rol. Para leer los roles, `_especialidades_de()` (`:112-131`) recorre las
cuatro y devuelve **todas** las que están prendidas, no la primera que encuentra.

**Son varios, y son varios desde el primer día del esquema.** Las cuatro hijas de `Empleado` son
subtipos **solapados** (`db/schema.sql:213-215`): nada impidió nunca que la misma persona fuera
entrenadora y profesora. Lo que imponía "un rol y uno solo" era esta capa, que leía la primera fila y,
al cambiar de rol, **borraba** la vieja. Eso terminó el 2026-09-29: la fila queda con `activo=false`
sosteniendo su historial, y quién es alguien HOY lo dice ese flag
([el rol que se apaga](A-10-bajas-logicas.md#el-rol-que-se-apaga) cuenta qué se rompía con el borrado,
qué se descartó y qué se paga). De ahí salen los tres hechos que gobiernan los procesos 29, 30 y 35:

1. La API habla de **`roles` y `detalles`** en plural, con los datos de cada rol en su casillero
   (`schemas.py:1736-1752`, `:1755-1780`).
2. El alta y la edición reciben una **lista** de roles, con al menos uno (`schemas.py:1699`,
   `:1801`), y las dos apps los eligen con **casillas**.
3. Un rol apagado no da sesión, ni permisos, ni aparece en ningún selector. Los seis lugares que
   preguntan por él están listados en A-10; el que manda es `roles_de_persona()`.

La base agrega la mitad que el código no ve: **cinco disparadores de restricción**
(`db/schema.sql:1203-1243` la función, `:1245-1268` los disparadores). Uno corre al insertar un
`Empleado` y los otros cuatro al borrar una fila de cualquier subtipo, y los cinco verifican lo mismo:
que el empleado tenga al menos un subtipo. Son `DEFERRABLE INITIALLY DEFERRED`, así que verifican **al
confirmar**, no en cada sentencia
([consistencia al final](A0-07-bases-de-datos-relacionales.md#c--consistencia-al-final-las-reglas-se-cumplen)).
Eso es lo que hace posible el alta (proceso 30): inserta primero el `Empleado` —que en ese instante no
tiene subtipo— y después la fila de cada rol; al confirmar, la regla ya se cumple. Los otros cuatro
disparadores, los del borrado, quedaron **sin trabajo**: desde que el cambio de rol apaga en vez de
borrar, ninguna ruta de la aplicación borra una fila de subtipo.

**Nota marcada · el estado que la base prohíbe, ahora sí alcanzable.** El docstring del módulo dice que
*"un empleado sin fila en ninguna hija es alguien cargado a quien todavía no se le asignó función"*
(`personal.py:44-46`). Para la base eso sigue siendo falso: `trg_empleado_completo` rechaza el `COMMIT`
de un empleado sin **ninguna** fila. Pero el disparador cuenta filas, no flags, así que un empleado con
las cuatro filas **apagadas** lo pasa sin problema, y ése sí sería "alguien sin función": `roles` vendría
vacía y la tarjeta diría "Sin rol asignado" (`StaffCard.tsx:142-144`, `views/personal.py:109-110`). Hoy
no se puede llegar ahí desde ninguna pantalla —el alta y la edición piden al menos un rol, en los dos
esquemas y en las dos apps—, así que la rama existe como red y no como camino. Antes del 2026-09-29 era
directamente inalcanzable.

### El Profesor tiene cuenta, como los otros tres

Hasta el 2026-09-16 el Profesor no tenía rol de sesión: *"da clases, no usa el sistema"*. Desde
entonces tiene cuenta y su pantalla, "Mis clases" en la PWA, y el alta lo dice en el lugar que manda,
el código: *"Los CUATRO roles pueden tener cuenta"* (`personal.py:299-302`), y la casilla se respeta
igual para los cuatro (`:303`). Las dos apps la piden siempre (`personalService.ts:328`,
`Flet/Proyecto/app/views/personal.py:481`), y el encabezado del router y los dos comentarios del
esquema lo cuentan igual (`personal.py:48-52`, `schemas.py:1655-1657`, `:1721-1722`).

Hasta el 2026-09-26, Flet mandaba `crear_cuenta = rol != "Profesor"`, con un comentario que invocaba
una regla del backend que ya no existía: el mismo alta le daba cuenta al profesor desde la PWA y no
desde Flet, y el profesor cargado en el mostrador quedaba sin "Mis clases". Era un caso de
[gemelas](A-03-dos-apps-un-backend.md#aplicación-gemela-y-componente-gemelo) que se separaron en un
comportamiento y no sólo en un texto. Qué ve el profesor si se sienta en la PC del mostrador —entra,
y la app le dice dónde está su pantalla— está en [B-01](B-01-acceso-y-sesion.md#3-iniciar-sesión).

---

## Los nueve procesos

### 29. Listar el personal

`GET /personal` · Dueño, Recepcionista

**Qué resuelve.** La grilla de tarjetas del personal: nombre, sus roles con el dato propio de cada uno,
el teléfono principal, si tiene cuenta y si está activo.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/personal/PersonalView.tsx` | 35-245 | `PersonalView` (la carga, 69-83) |
| Tarjeta PWA | `Proyecto - PWA/src/frontend/src/views/personal/StaffCard.tsx` | 87-219 | `StaffCard` (los renglones de rol, 141-169) |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/personalService.ts` | 132-178 | `detalleDeRol()`, `aEmpleadoListado()`, `listarPersonal()` |
| Esquemas | `backend/schemas.py` | 1736-1780 | `DetalleRolOut`, `EmpleadoOut` |
| Endpoint | `backend/routers/personal.py` | 182-208 | `listar_personal()` |
| Armado | `backend/routers/personal.py` | 100-179 | `_fila_de_rol()`, `_especialidades_de()`, `_telefono_principal()`, `_a_detalle_out()`, `_a_empleado_out()` |
| Vista Flet | `Flet/Proyecto/app/views/personal.py` | 63-236 | `build()`, `_renglones_de_rol()`, `_staff_card()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 445-514 | `_primero_no_vacio()`, `get_personal()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 497-498 | `obtener_personal()` |

**Cómo funciona.** El endpoint trae a todos los empleados, activos y dados de baja, ordenados por id
(`personal.py:196-209`), y arma cada fila con `_a_empleado_out()` (`:159-179`):

1. **Los roles prendidos**, con `_especialidades_de()` (`:161`), que devuelve pares (rol, fila) en el
   orden de `ESPECIALIDADES`; de ahí sale `roles` (`:171`).
2. **Los datos de cada rol**, uno por rol, con `_a_detalle_out()` (`:141-156`, llamado en `:172`). Usa
   `getattr(fila, campo, None)` (`:147-149`) porque cada hija tiene sólo algunos campos, y pedirle
   `titulo` a un Recepcionista tiene que dar `None`, no romper.
3. **El turno**, que no es texto sino una clave foránea a `Franja_Laboral`: viaja el nombre de la
   franja, sólo en el detalle del Recepcionista (`:152-154`), y el id aparte, para el formulario
   (`:155`).
4. **El teléfono principal**, o el más viejo si ninguno está marcado (`_telefono_principal()`,
   `:134-138`).
5. **Si tiene cuenta** (`:178`).

El paso 2 es la razón por la que los datos del rol **no** están aplanados en `EmpleadoOut`. Con dos
roles prendidos hay dos especialidades distintas —la del entrenador y la del profesor son columnas
distintas de tablas distintas— y una sola tríada `titulo`/`especialidad`/`matricula` hacía que la de un
rol pisara la del otro en pantalla (`schemas.py:1736-1747`).

La PWA filtra en memoria, por texto y por rol, y la coincidencia es contra **cualquiera** de sus roles
(`PersonalView.tsx:87-100`): alguien que es entrenador y profesor aparece con los dos filtros. El
subtítulo cuenta sólo los activos (`:102-104`); los dados de baja siguen en la grilla, con el distintivo
en gris. La tarjeta dibuja **un renglón por rol**, cada uno con su ícono y su chip
(`StaffCard.tsx:141-169`), y el chip lleva el color de la franja sólo cuando el dato ES una franja
(`:150`); Flet hace lo mismo en `_renglones_de_rol()` (`views/personal.py:94-134`).

**Qué escribe y qué lee.**

| Tabla | Atributos | Escribe o lee | Línea |
|---|---|---|---|
| `Empleado` | `id_empleado`, `id_persona`, `id_sede`, `legajo`, `fecha_ingreso`, `fecha_egreso`, `activo` | lee | `personal.py:196`, `:164-170` |
| `Persona` | `dni`, `nombre`, `apellido`, `email` | lee | `:173-176` |
| `Telefono` | `numero`, `principal` | lee | `:198`, `:134-138` |
| `Entrenador`, `Nutricionista`, `Recepcionista`, `Profesor` | `activo` y sus campos propios | lee | `:107-109`, `:112-131`, `:147-155` |
| `Franja_Laboral` | `nombre` | lee | `:152` |
| `Usuario` | la existencia de la fila | lee | `:178` |

Coincide con la línea DFD.

**Por qué está hecho así.** Los roles se derivan porque son filas
([tabla subtipo](A-05-modelo-de-datos.md#tabla-subtipo-especialización)) y se filtran por su flag
([el rol que se apaga](A-10-bajas-logicas.md#el-rol-que-se-apaga)); la carga anticipada existe para que
esa derivación no cueste una consulta por empleado
([listado en lote](A-11-rendimiento.md#listado-en-lote)). Lo que sigue muestra que la cuenta todavía no
cierra del todo.

**Nota marcada · a la carga anticipada le falta la cuenta.** El comentario de la consulta decía que el
rol *"se deriva de cual de los tres subtipos tiene fila"* y cargaba tres, cuando son cuatro; ahora carga
los cuatro y, encadenada, la franja del Recepcionista (`personal.py:191-206`). Queda afuera
`persona.usuario`, que el armado lee para cada fila (`:178`): una consulta perezosa por empleado
([N+1](A0-09-el-orm.md#n1)). **Corrido** antes del arreglo, con seis empleados de los cuales dos eran
profesores: **14 consultas** —las 6 en lote, 6 de `Usuario` y 2 de `Profesor`—. Hoy quedarían las 6 de
`Usuario`. El remedio está escrito en el mismo repo: `CARGA_DE_ROLES` de
`backend/routers/usuarios.py:82-93`, que el comentario cita como modelo, la incluye.

**Nota marcada · una diferencia de la gemela.** El subtítulo de Flet dice *"{N} empleados activos"*
contando a todos, también a los dados de baja (`views/personal.py:68`), contra el conteo de activos de
la PWA. El chip *"Turno —"* que Flet mostraba a todo el que no era Recepcionista ya no está: cada rol
muestra su propio dato, y sin dato no se dibuja chip.

**Qué pasa cuando sale mal.** El único rechazo es de permisos: 403 para Entrenador, Nutricionista,
Profesor y Socio, que no tienen la sección.

---

### 30. Dar de alta un empleado

`POST /personal` · Dueño

**Qué resuelve.** Contratar a alguien: su persona, su ficha de empleado con legajo, una fila por cada
rol que va a cumplir y, si se pide, su cuenta con una contraseña temporal para entregarle.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/personal/EmpleadoFormModal.tsx` | 43-296 | `EmpleadoFormModal` (las casillas, 219-244; el envío, `handleSubmit`, 110-158) |
| Entrega de la clave | `Proyecto - PWA/src/frontend/src/components/PanelCredenciales.tsx` | 48-151 | `PanelCredenciales` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/personalService.ts` | 173-345 | `camposDeRoles()`, `camposDelPedido()`, `crearEmpleado()` |
| Esquemas | `backend/schemas.py` | 1665-1723, 1827-1837 | `EmpleadoAltaRequest`, `EmpleadoAltaResponse` |
| Endpoint | `backend/routers/personal.py` | 211-363 | `alta_empleado()` |
| Tabla de roles y legajo | `backend/routers/personal.py` | 83-97 | `ESPECIALIDADES`, `_legajo()` |
| Credenciales | `backend/auth.py` | 90-143 | `generar_password_temporal()`, `generar_username()` |
| Envío por mail | `backend/notificaciones.py` | 89-164 | `enviar_credenciales()` |
| Base | `db/schema.sql` | 1245-1248 | `trg_empleado_completo` |
| Vista Flet | `Flet/Proyecto/app/views/personal.py` | 238-578 | `_open_form()`, `_save()`, `_mostrar_credenciales()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1266-1284 | `alta_empleado()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 518-519 | `alta_empleado()` |

**Cómo funciona.** Las dos apps eligen los roles con **casillas** —se marca más de uno
(`EmpleadoFormModal.tsx:219-244`, `views/personal.py:275-284` y `:317-330`)—, y al menos una tiene que
quedar marcada: las dos lo avisan antes de salir a la red (`EmpleadoFormModal.tsx:97-100`,
`views/personal.py:422-427`) y el esquema lo exige igual con `min_length=1` (`schemas.py:1699`).

Los campos propios los arman distinto. La PWA muestra **un campo por dato, no por rol**: la unión de
los que piden los roles marcados, que `camposDeRoles()` calcula sin repetir
(`personalService.ts:197-217`, con el mapa rol → campo en `:197-202`). Entrenador y Profesor piden los dos "Especialidad", y con dos inputs
iguales en pantalla nadie sabría cuál es cuál, así que va uno solo y su valor se escribe en las dos
filas: es la misma especialidad de la misma persona, guardada dos veces porque son dos tablas.
`camposDelPedido()` (`:227-237`) manda **sólo** esos campos. Flet muestra **título, especialidad,
matrícula y franja siempre** (`views/personal.py:350-360`, el pedido en `:454-471`); el esquema acepta
cualquier combinación porque *"el router ignora los que no correspondan"* (`schemas.py:1708-1715`). Las
dos mandan la sede clavada en 1 (`personalService.ts:326`, `views/personal.py:478`), y las dos exigen
mail o teléfono antes de salir a la red (`EmpleadoFormModal.tsx:113-121`, `views/personal.py:436-445`).

El endpoint, en orden:

1. **La sede existe**, o 404 (`personal.py:226-230`).
2. **La persona**: si el DNI ya está cargado, se reusa (`:235`) —*"un socio del gimnasio al que
   contratan de entrenador es el caso típico"* (`:233-234`)—; si no, se crea con un `flush`
   (`:237-246`). Si ya es empleado, 409 (`:247-251`), también si está dado de baja: esa persona se
   reactiva (proceso 37).
3. **El email no choca** con el de otra persona, o 409 (`:253-263`).
4. **El teléfono**, como principal (`:265-271`).
5. **El empleado**, con fecha de ingreso de hoy si no vino otra, y un `flush` para conocer su id
   (`:273-281`). El legajo `E-0001` se arma **después**, con ese id (`:282`, `_legajo()` en `:90-97`),
   por la misma razón que el número de socio: calcularlo antes daría legajos repetidos con dos altas
   simultáneas ([identidad generada](A0-07-bases-de-datos-relacionales.md#clave-primaria-e-identidad-generada)).
6. **Una fila por cada rol pedido**, prendida, con sólo los campos que esa tabla tiene (`:291-294`):
   *"crear la fila en la tabla hija ES asignarle la función"* (`:285-286`).
7. **La cuenta**, si se pidió (`:303-318`): si la persona ya tenía una, se conserva; si no, usuario y
   clave temporal, con la cuenta marcada para cambiarla.
8. **Una sola confirmación** (`:320`). Ahí corre `trg_empleado_completo` y verifica que el empleado
   tenga al menos un rol; si algo falló antes, no queda nada a medias.
9. **El mail, después de confirmar** (`:325-332`), y un mensaje en tres versiones según haya clave
   nueva, cuenta conservada o ninguna cuenta (`:339-349`). El mensaje nombra **todos** los roles
   —*"Entrenador y Profesor dado de alta (legajo E-0012)"*, armado en `:335-337`— porque nombrar uno
   solo haría dudar de si los otros se guardaron. **Corrido** contra la base real: ése es el texto
   exacto que devolvió un alta con dos roles.

Con la respuesta, la PWA vuelve a pedir el empleado para tener la fila de la grilla
(`personalService.ts:333`, el único cliente del proceso 34) y, si hay clave, abre el panel de entrega en
vez de cerrar (`EmpleadoFormModal.tsx:142-145`).

**Qué escribe y qué lee.**

| Tabla | Atributos | Escribe o lee | Línea |
|---|---|---|---|
| `Sede` | `id_sede` | lee | `personal.py:226` |
| `Persona` | `dni` (para reusar), `email` (para el choque) | lee | `:235`, `:254-258` |
| `Persona` | `dni`, `nombre`, `apellido`, `email`, `fecha_nacimiento` | escribe | `:238-244` |
| `Empleado` | la existencia de la fila de la persona | lee | `:247` |
| `Telefono` | `id_persona`, `numero`, `tipo`, `principal` | escribe | `:266-271` |
| `Empleado` | `id_persona`, `id_sede`, `fecha_ingreso`, `activo`, `legajo` | escribe | `:274-282` |
| `Entrenador`, `Nutricionista`, `Recepcionista` y/o `Profesor` | `id_empleado`, `activo` y sus campos propios, una fila por rol | escribe | `:291-294` |
| `Usuario` | la cuenta de la persona y `username` (para no repetirlo) | lee | `:304-305`, `:307-310` |
| `Usuario` | `id_persona`, `username`, `password_hash`, `debe_cambiar_password`, `activo` | escribe | `:312-318` |

Coincide con la línea DFD, que además lee `Persona.activo`: sale en la respuesta, con la persona
(`:356`).

**Por qué está hecho así.** Una sola transacción, igual que el alta de socio
([B-02](B-02-socios.md#7-dar-de-alta-un-socio-con-su-cuenta-de-acceso-y-credenciales-temporales)). Mail
o teléfono obligatorios porque sin ninguno *"no hay por dónde mandarle sus credenciales"*
(`schemas.py:1683-1684`). Y `ESPECIALIDADES` como tabla de datos en vez de un `if` de cuatro ramas
repetido en el alta, la lectura y la edición (`personal.py:80-82`): con roles múltiples ese `if` habría
pasado a ser un `if` de cuatro ramas **dentro de un bucle**, y la tabla de datos lo convierte en tres
líneas (`:291-294`).

**Nota marcada · el reuso de la persona, otra vez.** Es el mismo mecanismo del alta de socio, con las
mismas pérdidas: si la persona ya existía, el nombre, el apellido, el email y la fecha de nacimiento
del formulario **se descartan sin aviso** —sólo se usan al crearla (`personal.py:237-245`)—, y el
teléfono se agrega como principal sin desmarcar el que ya tuviera (`:265-271`), así que la ficha puede
quedar con dos principales. Y agrega uno propio: la cuenta que *"se conserva"* (`:304-305`) puede estar
**apagada**. Un ex socio dado de baja por mora tiene la cuenta desactivada
([tipo de baja](A-10-bajas-logicas.md#tipo-de-baja-y-el-acople-de-la-cuenta)); si el gimnasio lo
contrata, el alta no la prende, el mensaje dice *"Ya tenía cuenta ('…'), se conserva"* (`:344-348`) y el
empleado nuevo no puede entrar. Leído, no corrido.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| La sede no existe | 404 | *"La sede indicada no existe."* | `personal.py:226-230` |
| La persona ya es empleado, activo o de baja | 409 | *"{nombre} ya está registrado como empleado."* | `personal.py:247-251` |
| El email es de otra persona | 409 | *"Ese email ya está registrado para otra persona."* | `personal.py:253-263` |
| Sin mail ni teléfono | 422 | *"Cargá un email o un teléfono: hace falta para contactarlo."* | `schemas.py:1681-1688` |
| DNI de menos de 6 caracteres, nombre o apellido vacíos, rol que no existe | 422 | el de Pydantic | `schemas.py:1671-1673`, `:1695` |
| Teléfono con letras o email sin dominio | 422 | los de sus validadores | `schemas.py:41-54`, `:74-100` |
| Una franja que no existe | 500 | ninguno legible | `personal.py:320` |

La línea DFD nombra los cuatro primeros. El último sólo se alcanza armando el pedido a mano, porque
las dos apps ofrecen franjas reales; **corrido**: la clave foránea de `Recepcionista` rechaza el
`COMMIT` y no queda ni la persona. Qué ve la pantalla con un 500 está en el proceso 36.

---

### 31. Listar los entrenadores disponibles

`GET /personal/entrenadores` · Dueño, Recepcionista, Entrenador, Nutricionista

**Qué resuelve.** El selector "Entrenador a cargo" del formulario de rutinas y del panel que asigna un
entrenador a un socio.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vistas PWA | `Proyecto - PWA/src/frontend/src/views/rutinas/RutinaFormModal.tsx` | 60 | `listarEntrenadoresActivos` |
| | `Proyecto - PWA/src/frontend/src/views/socios/EntrenadoresModal.tsx` | 61 | `listarEntrenadoresActivos` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/rutinasService.ts` | 208-211 | `listarEntrenadoresActivos()` |
| Esquema | `backend/schemas.py` | 1594-1602 | `ProfesionalOpcion` |
| Endpoint | `backend/routers/personal.py` | 501-520 | `listar_entrenadores()` |
| Armado | `backend/routers/personal.py` | 472-498 | `_opciones()` |
| Quién pide | `backend/routers/rutinas.py` | 68-79 | `_entrenador_de_sesion()` |
| Vistas Flet | `Flet/Proyecto/app/views/rutinas.py` | 257 | `get_entrenadores` |
| | `Flet/Proyecto/app/views/socios.py` | 965 | `get_entrenadores` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1286-1296 | `get_entrenadores()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 501-502 | `obtener_entrenadores()` |

**Cómo funciona.** `_opciones()` trae los entrenadores que pasan **dos** filtros
(`personal.py:484-490`): su empleado está activo **y** su fila de `Entrenador` está prendida. Les pone el
nombre de la persona (`:491-496`) y los ordena por nombre (`:498`). Después, si quien pide tiene ficha de
entrenador, la lista se reduce a él (`:515-518`): `_entrenador_de_sesion()` busca un empleado de esa
persona con fila **prendida** en `Entrenador` (`rutinas.py:68-84`). El Dueño, el Recepcionista y la
Nutricionista reciben a todos. **Corrido:** una entrenadora recibió sólo su nombre; una nutricionista,
los dos entrenadores; y una entrenadora a la que se le cambió el rol a recepcionista desapareció de la
lista sin que su fila se haya borrado.

**Qué escribe y qué lee.** Lee `Entrenador` (`id_entrenador`, `id_empleado`, `activo`), `Empleado`
(`activo`, y `id_persona` para reconocer a quien pide) y `Persona` (`nombre`, `apellido`). Coincide con la
línea DFD, corregida para nombrar el `activo` del subtipo.

**Por qué está hecho así.** Pide la sección Rutinas y no Personal porque *"quien arma una rutina
necesita elegir el entrenador aunque no tenga acceso a la ficha de personal"* (`personal.py:506-508`).
Los **dos** filtros por activo son dos preguntas distintas y hacen falta las dos, y el docstring lo
dice (`:473-481`): `Empleado.activo` es seguir trabajando acá, `Entrenador.activo` es seguir cumpliendo
ESE rol. Una entrenadora que pasó a recepción cumple el primero y no el segundo, y ofrecerla haría que
el formulario le asigne trabajo que no va a hacer
([el rol que se apaga](A-10-bajas-logicas.md#el-rol-que-se-apaga)). Y el recorte al propio
entrenador es el backend ayudando a esconder: el alta de rutina rechaza igual una a nombre de otro, pero
*"filtrarlo acá hace que los selectores de las dos apps dejen de ofrecer algo que después falla, sin
tocar ninguna pantalla"* (`:512-513`;
[el frontend esconde, el backend rechaza](A-08-autorizacion.md#el-frontend-esconde-el-backend-rechaza)).
Va declarado antes que `/{id_empleado}` porque FastAPI prueba las rutas en orden, y si no leería
`entrenadores` como un id (`:466-468`).

`_opciones()` repite en chico el problema del proceso 29: dos consultas perezosas por profesional, el
empleado y la persona (`:492`). **Corrido:** con dos entrenadores activos, 5 consultas más la de
reconocer a quien pide. Con los pocos entrenadores de un gimnasio, no se nota.

**Qué pasa cuando sale mal.** 403 para Profesor y Socio, que no tienen la sección Rutinas.

---

### 32. Listar el catálogo de franjas laborales

`GET /personal/franjas` · Dueño, Recepcionista

**Qué resuelve.** Las opciones del selector de turno del Recepcionista, en el alta y la edición.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/personal/EmpleadoFormModal.tsx` | 70-76 | `listarFranjas` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/personalService.ts` | 280-283 | `listarFranjas()` |
| Esquema | `backend/schemas.py` | 1726-1733 | `FranjaLaboralOut` |
| Endpoint | `backend/routers/personal.py` | 541-557 | `listar_franjas()` |
| Vista Flet | `Flet/Proyecto/app/views/personal.py` | 287-290 | `get_franjas` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 516-522 | `get_franjas()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 509-511 | `obtener_franjas()` |

**Cómo funciona.** Las franjas activas, ordenadas por id (`personal.py:552-555`). La base de ENTREGA
trae tres.

**Qué escribe y qué lee.** Lee `Franja_Laboral` (`id_franja_laboral`, `nombre`, `hora_desde`,
`hora_hasta`, `activo`). Coincide con la línea DFD.

**Por qué está hecho así.** Reemplaza un texto libre, *"el viejo varchar `turno_laboral`"*
(`personal.py:547-548`), por una clave foránea a un catálogo: con texto, "Mañana" y "mañana" eran dos
turnos. El docstring del módulo todavía dibuja `Recepcionista (turno_laboral)` (`:14`), de antes del
cambio. Y la tarjeta de la PWA sigue atada a los nombres: busca el color del chip en un mapa de tres
valores fijos —"Mañana", "Tarde", "Noche"— (`StaffCard.tsx:39-43`, `:99`), y el tipo lo promete con un
`as` que nadie verifica (`personalService.ts:123`). Una franja con otro nombre deja el color en
`undefined`; Flet, con el mismo mapa, cae a un gris neutro (`views/personal.py:94`).

**Qué pasa cuando sale mal.** 403 para quien no tiene la sección Personal.

---

### 33. Listar los nutricionistas disponibles

`GET /personal/nutricionistas` · Dueño, Recepcionista, Entrenador, Nutricionista

**Qué resuelve.** El selector "Nutricionista a cargo" del formulario de dietas.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/nutricion/PlanFormModal.tsx` | 83-103 | `listarNutricionistasActivos` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/nutricionService.ts` | 100-103 | `listarNutricionistasActivos()` |
| Endpoint | `backend/routers/personal.py` | 523-538 | `listar_nutricionistas()` |
| Armado | `backend/routers/personal.py` | 472-498 | `_opciones()` |
| Quién pide | `backend/routers/nutricion.py` | 71-76 | `_nutricionista_de_sesion()` |
| Vista Flet | `Flet/Proyecto/app/views/nutricion.py` | 285-298 | `_open_form()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1298-1300 | `get_nutricionistas()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 505-506 | `obtener_nutricionistas()` |

**Cómo funciona.** El espejo exacto del 31: `_opciones()` con la tabla `Nutricionista` (`personal.py:533`)
—con los mismos dos filtros por activo, y por nombre— y, si quien pide tiene ficha **prendida** de
nutricionista, la lista se reduce a ella (`:534-536`, con `_nutricionista_de_sesion()` en
`nutricion.py:71-80`). **Corrido:** una nutricionista recibió sólo su nombre; la dueña, las tres activas.

**Qué escribe y qué lee.** Lee `Nutricionista` (incluido su `activo`), `Empleado` y `Persona`, como el
proceso 31. Coincide con la línea DFD, corregida igual que la del 31.

**Por qué está hecho así.** Pide la sección Nutrición porque lo usa el formulario de dietas, y recorta
a la propia porque el alta de una dieta rechaza con 403 una a nombre de otro, *"No podés crear dietas a
nombre de otro nutricionista."* (`backend/routers/nutricion.py:91-96`). Sin el recorte, que faltó hasta
el 2026-09-26, la PWA —que preselecciona el primero de la lista cuando la dieta es nueva
(`PlanFormModal.tsx:95-99`)— le ofrecía a una nutricionista que no fuera la primera en orden alfabético
una dieta a nombre de otra, y guardar sin tocar el selector terminaba en ese 403. Los comentarios de
las dos apps ya lo daban por hecho (`PlanFormModal.tsx:27-28`,
`Flet/Proyecto/app/views/nutricion.py:293-296`).

**Qué pasa cuando sale mal.** 403 para Profesor y Socio, que no tienen la sección Nutrición.

---

### 34. Consultar la ficha de un empleado

`GET /personal/{id_empleado}` · Dueño, Recepcionista

**Qué resuelve.** Una fila de la grilla, sola.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Service PWA | `Proyecto - PWA/src/frontend/src/services/personalService.ts` | 166-169 | `obtenerEmpleado()` |
| Endpoint | `backend/routers/personal.py` | 560-570 | `obtener_empleado()` |
| Armado | `backend/routers/personal.py` | 159-179 | `_a_empleado_out()` |

**Cómo funciona.** Busca por clave primaria (`personal.py:565`) y arma la fila con la misma función que
el listado. **Corrido:** cinco consultas para un entrenador —el empleado, la persona, su fila de
`Entrenador`, sus teléfonos y su cuenta—, todas perezosas; para una sola fila, da igual.

**Qué escribe y qué lee.** Lo mismo que el proceso 29, para un empleado. Coincide con la línea DFD.

**Por qué está hecho así.** Su único cliente es el alta de la PWA (`personalService.ts:333`), que
necesita la fila de la grilla y recibe la persona. Flet no lo usa: después de escribir,
vuelve a pedir la lista entera ([servir y refrescar](A-11-rendimiento.md#servir-y-refrescar)).

**Qué pasa cuando sale mal.** 404 *"El empleado no existe."* (`personal.py:566-568`), y 403 para quien
no tiene la sección.

---

### 35. Editar un empleado y sus roles

`PUT /personal/{id_empleado}` · Dueño

**Qué resuelve.** Corregir los datos de un empleado y, si hace falta, cambiarle las funciones: agregarle
una, sacarle otra, o cambiar de una a otra.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/personal/EmpleadoFormModal.tsx` | 43-296 | `EmpleadoFormModal` (`alternarRol()`, 93-108; la edición, 127-130) |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/personalService.ts` | 197-266, 347-372 | `camposDeRoles()`, `camposDelPedido()`, `valoresDeRoles()`, `actualizarEmpleado()` |
| Esquema | `backend/schemas.py` | 1783-1820 | `EmpleadoEditarRequest` |
| Endpoint | `backend/routers/personal.py` | 572-627 | `editar_empleado()` |
| Aplicación de roles | `backend/routers/personal.py` | 370-427 | `_aplicar_roles()` |
| Cierre al apagar | `backend/routers/personal.py` | 430-460 | `_limpiar_al_apagar()` |
| Base | `db/schema.sql` | 209, 228, 241, 262 | la columna `activo` de los cuatro subtipos |
| Vista Flet | `Flet/Proyecto/app/views/personal.py` | 238-500 | `_open_form()`, `_save()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1310-1312 | `editar_empleado()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 514-515 | `editar_empleado()` |

**Cómo funciona.** El pedido trae `roles`: el **conjunto completo** que tiene que quedar prendido, no un
delta. El docstring del esquema dice por qué (`schemas.py:1785-1791`): así el formulario no lleva la
cuenta de qué cambió, y un delta del estilo *"sacale entrenador"* no distinguiría entre "no lo mandé" y
"sacalo".

El endpoint, en orden:

1. **El empleado existe**, o 404 (`personal.py:588-591`).
2. **El email nuevo no choca** con el de otra persona, o 409 (`:595-602`).
3. **Nombre, apellido y email**, siempre (`:604-606`).
4. **El teléfono, sólo si vino** (`:608-621`): con número, pisa el principal o crea uno; vacío, borra el
   principal.
5. **Los roles**, con `_aplicar_roles()` (`:624`), que recorre los cuatro y hace una de tres cosas con
   cada uno (`:403-428`):

| El rol… | …y su fila | Qué pasa | Línea |
|---|---|---|---|
| vino en el pedido | no existe | se crea prendida, con todos los campos | `:408-413` |
| vino en el pedido | existe apagada | **se reactiva**, con sus datos como estaban | `:415` |
| vino en el pedido | existe prendida | sólo se tocan los campos que vinieron | `:422-424` |
| no vino | está prendida | se **apaga** y se cierra lo que cuelga de ella | `:426-428` |

6. **Una confirmación** (`:626`).

**No se borra ninguna fila, y por eso no hay 409.** Esto es lo que cambió el 2026-09-29, y es el
capítulo entero de [el rol que se apaga](A-10-bajas-logicas.md#el-rol-que-se-apaga): hasta entonces el
paso 5 hacía `db.delete(fila_vieja)`, esa fila es el destino de seis claves foráneas sin acción al
borrar, y una validación previa —`_validar_cambio_de_rol()`, 74 líneas— tenía que frenar con 409 a
cualquiera que tuviera una rutina, un socio a cargo, una dieta, un horario, un turno o una actividad
habilitada. El historial de asignaciones no se borra nunca
([asignación con estado](A-05-modelo-de-datos.md#asignación-con-estado)), así que **un entrenador que
alguna vez tuvo un alumno no podía cambiar de rol jamás**. Apagar en vez de borrar dejó esa validación
sin nada que validar, y se borró entera.

**Reactivar una fila vieja devuelve sus datos.** Es un efecto lateral que resultó útil: quien fue
entrenador, pasó a nutricionista y vuelve, recupera su título y su matrícula tal como estaban, porque la
fila nunca se fue (`:415`). **Corrido** contra la base real: la matrícula `MN-ZZ` volvió sola, y el
`id_entrenador` fue el mismo de antes, así que sus rutinas siguieron apuntándole.

**Apagar un rol cierra lo que cuelga de él.** El flag alcanza para que la persona no entre más con ese
rol, pero no para que desaparezca de las pantallas de los demás: un entrenador que pasa a recepción
seguiría saliendo en "Mi entrenador" del socio, que lista las asignaciones `ACTIVA`
(`backend/routers/portal.py:2209-2213`). `_limpiar_al_apagar()` (`:431-461`) las **finaliza**, con fecha
de hoy (`:457-461`) —el mismo cierre que la baja del empleado (proceso 36) y que
`finalizar_asignacion()`—, y el historial de quién entrenó a quién queda. Los otros tres roles no
necesitan nada, y el docstring dice por qué cada uno (`:446-452`): las dietas de un nutricionista quedan
asignadas porque `Asignacion_Dieta` ata socio con dieta y no socio con nutricionista; los horarios y
turnos de un profesor guardan su `id_profesor` y siguen teniendo responsable, y deja de aparecer como
opción porque los selectores filtran por el flag; y el recepcionista no produce nada propio.

**Corrido** contra la base real, con datos marcados y borrados después: a un empleado con dos roles
(Entrenador y Profesor), una rutina, un socio a cargo con asignación `ACTIVA` y luego cambiado a
Recepcionista, le quedaron las dos filas viejas apagadas con sus datos intactos, la nueva prendida, la
asignación en `FINALIZADA` con la fecha de hoy, la rutina intacta y a su nombre, `roles_de_persona()`
devolviendo `['recepcionista']`, y desapareció del selector de entrenadores. Volver a Entrenador
reactivó la misma fila y **no** reabrió la asignación.

**Un rol que se saca no le cambia los permisos a quien ya tiene la sesión abierta**: los roles viajan en
el token y se releen en el próximo ingreso ([identidad firmada](A-07-autenticacion.md#identidad-firmada)).
A quien le cambian el rol hay que decirle que salga y vuelva a entrar.

**Qué escribe y qué lee.**

| Tabla | Atributos | Escribe o lee | Línea |
|---|---|---|---|
| `Empleado` | la fila | lee | `personal.py:588` |
| `Persona` | `email` (para el choque) | lee | `:595-599` |
| `Persona` | `nombre`, `apellido`, `email` | escribe | `:604-606` |
| `Telefono` | `numero` (o la fila entera, al borrar) | escribe | `:608-621` |
| `Entrenador`, `Nutricionista`, `Recepcionista`, `Profesor` | `activo` de cada fila prendida o apagada, y los campos propios que vinieron | escribe | `:408-427` |
| `Asignacion_Entrenador` | `estado` (para elegir las `ACTIVA`) | lee | `:457-458` |
| `Asignacion_Entrenador` | `estado`, `fecha_fin` | escribe | `:459-460` |

**Discrepancia con la línea DFD.** La línea del proceso 35 declaraba como salida el 409 por *"cambio de
rol bloqueado por tener rutinas, dietas o actividades habilitadas"* y por *"tener historial en el rol"*.
Ese rechazo ya no existe. Se corrigió la línea junto con el código, y se le sumaron dos cosas que ahora
sí escribe: el flag `activo` de cada subtipo y `Asignacion_Entrenador` (`estado`, `fecha_fin`).

**Por qué está hecho así.** La decisión de fondo —apagar en vez de borrar— y lo que se descartó para
llegar a ella están en [el rol que se apaga](A-10-bajas-logicas.md#el-rol-que-se-apaga). Lo propio de
este proceso son dos elecciones más chicas:

**El conjunto completo en vez de un delta.** El costo es que el formulario tiene que mandar siempre los
cuatro estados, y que un cliente que se olvide un rol lo apaga. Lo que se gana es que la operación es
[idempotente](A-12-como-leer-los-procesos.md): mandar dos veces el mismo pedido deja el mismo resultado,
y el endpoint no tiene que interpretar la ausencia de un campo como una orden.

**Un campo por dato y no por rol, en la PWA.** Entrenador y Profesor guardan los dos una
`especialidad`, en dos columnas distintas de dos tablas distintas. Mostrar dos inputs con la misma
etiqueta era inaceptable, y `camposDeRoles()` (`personalService.ts:197-217`) resuelve mostrando la
**unión** de los campos que piden los roles marcados. El precio: con los dos roles marcados no se puede
poner una especialidad distinta en cada uno desde la PWA; el valor va a las dos filas. Flet sí las
distingue, porque muestra los tres campos siempre. Es una asimetría nueva entre las
[gemelas](A-03-dos-apps-un-backend.md#aplicación-gemela-y-componente-gemelo), y la PWA es la referencia:
si el dueño quiere especialidades distintas por rol, el cambio es en la PWA.

**Marcar un rol precarga lo que esa persona ya tenía en él.** `valoresDeRoles()`
(`personalService.ts:247-266`) busca, para cada campo, el valor del primer rol marcado que lo use. Sin
eso, marcarle Nutricionista a alguien que ya lo había sido abría el Título vacío y guardar lo borraba.
Y el valor sale de la **columna exacta** que se va a escribir, no del `detalle` de la tarjeta, que elige
un campo con fallback: a una nutricionista con matrícula y sin título le precargaba la matrícula, y
guardar la mudaba al título.

**Editar sin tocar los roles no borra lo que no se tocó.** El paso 5 aplica la regla del `PUT` de socio
([B-02, proceso 11](B-02-socios.md#11-editar-la-ficha-de-un-socio)): un campo ausente se conserva, uno
en `null` se borra (`personal.py:422-424`; el esquema lo anota campo por campo, `schemas.py:1817-1820`).
Hace falta porque cada app muestra campos distintos: la PWA sólo los de los roles marcados
(`personalService.ts:227-237`), Flet título, especialidad y matrícula siempre
(`views/personal.py:350-360`). Hasta el 2026-09-26 el endpoint copiaba todos los campos, la PWA mandaba
en `null` los que no mostraba y Flet no tenía el de especialidad: editarle el teléfono a un entrenador
desde la PWA le borraba el título y la matrícula, desde Flet le borraba la especialidad, y a una
nutricionista con matrícula y sin título la PWA le mudaba la matrícula al título. **Corrido:** los tres
casos conservan lo que no se tocó, y un `null` explícito sí borra.

Dos diferencias menores de la gemela, en el mismo formulario. Flet ofrece el DNI **editable** en la
edición, con un comentario que dice que *"no se edita desde acá"* (`views/personal.py:311-315`): el
esquema de edición no tiene DNI y lo descarta sin aviso
([nada muerto en pantalla](A-01-que-es-olimpos.md#nada-muerto-en-pantalla)); la PWA lo muestra como
texto (`EmpleadoFormModal.tsx:189-202`). Y un teléfono vaciado: la PWA manda la cadena vacía
(`personalService.ts:368`) y el backend borra el principal, sin ascender otro, mientras que Flet manda
`None` (`views/personal.py:462`) y el backend no lo toca. Desde Flet, el teléfono de un empleado no se
puede quitar.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| El empleado no existe | 404 | *"El empleado no existe."* | `personal.py:588-591` |
| El email es de otra persona | 409 | *"Ese email ya está registrado para otra persona."* | `personal.py:600-602` |
| Sin ningún rol marcado | 422 | el de Pydantic sobre `min_length=1` | `schemas.py:1801` |
| Sin mail ni teléfono | 422 | *"Cargá un email o un teléfono: hace falta para contactarlo."* | `schemas.py:1811-1816` |

Los dos primeros son los que declara la línea DFD, que además nombra el nuevo "ningún rol marcado".

---

### 36. Dar de baja a un empleado

`POST /personal/{id_empleado}/baja` · Dueño

**Qué resuelve.** Que alguien que dejó de trabajar en el gimnasio deje de figurar como activo y deje de
poder entrar, sin borrar nada de lo que hizo.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/personal/PersonalView.tsx` | 116-137 | `pedirBaja` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/personalService.ts` | 384-393 | `darDeBajaEmpleado()` |
| Esquema | `backend/schemas.py` | 1823-1824 | `BajaEmpleadoRequest` |
| Endpoint | `backend/routers/personal.py` | 631-716 | `dar_de_baja_empleado()` |
| Vista Flet | `Flet/Proyecto/app/views/personal.py` | 386-404 | `_cambiar_estado()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1302-1304 | `baja_empleado()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 522-523 | `baja_empleado()` |

**Cómo funciona.** Las dos apps confirman antes, con el mismo texto: *"Deja de figurar como activo y
su cuenta de acceso se desactiva. Si entrena socios, deja de estar a cargo de ellos. Se puede
reactivar."* (`PersonalView.tsx:118-134`, `views/personal.py:397-403`). El endpoint:

1. **Existe**, o 404 (`personal.py:650-653`); **no estaba ya de baja**, o 400 (`:654-657`); **no es uno
   mismo**, o 403 (`:661-664`).
2. **La ficha**: inactiva, con fecha de egreso de hoy (`:666-667`).
3. **La cuenta**, apagada, si tiene (`:669-670`).
4. **Si es entrenador, sus alumnos**: las asignaciones `ACTIVA` que lo tienen a cargo pasan a
   `FINALIZADA`, con fecha de fin de hoy (`:716-722`). Las ya finalizadas conservan su fecha. Pregunta
   `rol_activo(empleado.entrenador)` (`:716`) y no si la fila existe, porque puede existir apagada
   ([el rol que se apaga](A-10-bajas-logicas.md#el-rol-que-se-apaga)): sin el flag, a alguien que
   **fue** entrenador y ahora es recepcionista le cerraría asignaciones de un rol que ya no cumple.
5. **Sus habilitaciones para dictar actividades: nada.** Y ahí está el arreglo del 2026-09-30, que es
   lo que sigue.

**El paso que se sacó.** Hasta el 2026-09-30 había un paso más: borrar las filas de
`Profesor_Actividad`, para que el profesor de baja *"no siguiera figurando entre quienes pueden dictar
Yoga"*. Tenía dos problemas, y el segundo es el que enseña.

**No funcionaba.** Esa fila es el destino de `fk_horario_profesor_habilitado` y
`fk_turno_profesor_habilitado` (`db/schema.sql:1059-1065`), que exigen que el par profesor-actividad de
cada horario y de cada turno exista en `Profesor_Actividad`. Las claves no miran fechas y los turnos no
se borran nunca —dar de baja un horario los *cancela*, y lo dice en su propio comentario
(`backend/routers/actividades.py:1541-1546`)—, así que desde la primera clase dictada el borrado era
imposible y **la baja entera se deshacía con un 500**. **Corrido:** un profesor con un horario cargado
daba `IntegrityError` en `fk_horario_profesor_habilitado`; el empleado seguía activo y con la cuenta
prendida. Uno sólo habilitado, sin horario, se daba de baja bien: por eso estuvo tanto tiempo
invisible.

**Y era innecesario.** El objetivo —que no figure entre los disponibles— ya lo cumplían **cuatro
filtros por `Empleado.activo`** que estaban puestos de antes: el plantel de profesores
(`actividades.py:591-596`), los habilitados de una actividad (`:835-842`), y las dos validaciones del
profesor a cargo de un horario (`:1476-1484`, `:1615-1623`). Un empleado de baja no aparecía en
ninguna lista **sin borrarle nada**. Se sacó el paso y el 500 desapareció sin agregar ni una línea de
lógica nueva (`personal.py:672-694`, que hoy es sólo el comentario que lo explica).

Sacarlo de **una** actividad sigue siendo una decisión aparte y explícita, y ésa apaga la fila en vez
de borrarla: le toca a [B-08](B-08-actividades-turnos-horarios.md), y el porqué está en
[la segunda fila de esa clase](A-10-bajas-logicas.md#la-segunda-fila-de-esa-clase-y-cómo-se-cerró).
6. **Una confirmación** (`:714`).

**Qué escribe y qué lee.**

| Tabla | Atributos | Escribe o lee | Línea |
|---|---|---|---|
| `Empleado` | `activo`, `id_persona` | lee | `personal.py:654`, `:661` |
| `Empleado` | `activo`, `fecha_egreso` | escribe | `:666-667` |
| `Usuario` | `activo` | escribe | `:669-670` |
| `Entrenador` | `activo` y la existencia de la fila | lee | `:716` |
| `Asignacion_Entrenador` | `id_entrenador`, `estado` (para elegir las activas) | lee | `:718-719` |
| `Asignacion_Entrenador` | `estado`, `fecha_fin` | escribe | `:720-721` |

**Discrepancia con la línea DFD, corregida.** La línea declaraba que la baja escribía
`Profesor_Actividad` y que el empleado quedaba *"con sus actividades desasignadas"*. Ya no: se corrigió
junto con el código, y ahora dice que las habilitaciones quedan intactas y vuelven con él. El 500 que
la línea nunca nombró dejó de existir.

**Por qué está hecho así.** [Baja lógica](A-10-bajas-logicas.md#baja-lógica-soft-delete): *"la fila del
rol queda intacta: alguien dado de baja sigue habiendo sido entrenador, y sus rutinas siguen atribuidas
a él"* (`personal.py:641-642`). Y la cuenta se apaga siempre, a diferencia del socio, porque el acceso
de un empleado se justifica en el puesto
([el acople total](A-10-bajas-logicas.md#en-los-empleados-el-acople-es-total)).

Las asignaciones del entrenador se cierran por la regla de `CLAUDE.md` —*"al cambiar el estado de una
entidad, decidir qué pasa con todo lo que la referencia"*—: sin el paso 5, el portal del socio, que
lista las asignaciones `ACTIVA` (`backend/routers/portal.py:2209-2213`), le seguía mostrando en "Mi
entrenador" a alguien que ya no trabaja en el gimnasio. Se **finalizan** y no se borran, con el mismo
cierre que `finalizar_asignacion()` (`backend/routers/socios.py:1101-1102`), para que el historial de
quién entrenó a quién quede (`personal.py:701-702`). **Corrido** contra un PostgreSQL descartable: las
dos asignaciones activas de un entrenador pasaron a finalizadas con fecha de hoy, una vieja conservó
su fecha, la de otra entrenadora con el mismo alumno no se tocó, y la reactivación no las reabrió.

**Nota marcada · el motivo que no llega a ningún lado.** `BajaEmpleadoRequest` acepta un `motivo`
(`schemas.py:1823-1824`) y los dos clientes lo pasan si lo reciben (`personalService.ts:384-391`,
`api_client.py:522-523`), pero ninguna pantalla lo pide, el endpoint no lo lee y `Empleado` no tiene
dónde guardarlo (`db/schema.sql:186-194`). De la baja de un empleado queda sólo la fecha. Hasta el
2026-09-26, además, la confirmación de la PWA prometía *"Esta acción queda registrada en Auditoría."*,
y lo mismo las de Usuarios, Rutinas y Nutrición, sin que exista ninguna auditoría entre las 41 tablas
del esquema; las cuatro dicen ahora lo que pasa, las de Rutinas y Nutrición con el texto de sus gemelas
de Flet. El único rastro es una interfaz `Auditoria` que nadie usa
(`Proyecto - PWA/src/frontend/src/types.ts:73`).

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| El empleado no existe | 404 | *"El empleado no existe."* | `personal.py:649-652` |
| Ya estaba de baja | 400 | *"{nombre} ya estaba dado de baja."* | `personal.py:653-656` |
| Es uno mismo | 403 | *"No podés darte de baja a vos mismo."* | `personal.py:661-664` |

Los tres los nombra la línea DFD, y desde el 2026-09-30 son los tres únicos: el cuarto era un 500 sin
mensaje, el del profesor con clases dictadas.

**Qué ve la pantalla con un 500.** Sigue valiendo para los que quedan —un 500 de la base puede aparecer
en cualquier endpoint, y el de la franja inexistente del proceso 30 es uno—. El backend no tiene manejador para los errores de la base, y
FastAPI, sin modo de depuración, responde un texto plano. Las dos apps esperan JSON, no lo encuentran y
dicen sólo el código: *"El servidor respondió un error (500)."* en la PWA
(`Proyecto - PWA/src/frontend/src/services/api.ts:135`) y *"El servidor respondió algo inesperado
(código 500)."* en Flet (`Flet/Proyecto/app/api_client.py:117`). El nombre de la restricción queda en el
registro del servidor, no en la pantalla.

---

### 37. Reactivar a un empleado

`POST /personal/{id_empleado}/reactivar` · Dueño

**Qué resuelve.** La vuelta de alguien que se había ido.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/personal/PersonalView.tsx` | 139-152 | `activar` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/personalService.ts` | 395-398 | `reactivarEmpleado()` |
| Endpoint | `backend/routers/personal.py` | 719-742 | `reactivar_empleado()` |
| Vista Flet | `Flet/Proyecto/app/views/personal.py` | 386-397 | `_cambiar_estado()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1306-1308 | `reactivar_empleado()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 526-527 | `reactivar_empleado()` |

**Cómo funciona.** Existe, o 404 (`personal.py:725-728`); estaba de baja, o 400 (`:729-732`). La ficha
vuelve a activa y **se borra la fecha de egreso** (`:734-735`); la cuenta, si tiene, se prende
(`:736-737`). Las dos apps lo hacen sin confirmación: *"reactivar es una acción de bajo riesgo y
reversible"* (`PersonalView.tsx:139-141`).

**Qué escribe y qué lee.** Escribe `Empleado.activo`, `Empleado.fecha_egreso` y `Usuario.activo`; lee
el empleado y su persona. Coincide con la línea DFD.

**Por qué está hecho así.** Es el segundo camino de la baja lógica
([los dos caminos](A-10-bajas-logicas.md#los-dos-caminos)): lo que la baja marcó, la reactivación lo
desmarca. Y prende la cuenta sin preguntar por qué estaba apagada, como la reactivación del socio
([B-02, proceso 24](B-02-socios.md#24-reactivar-a-un-socio-dado-de-baja-y-devolverle-el-acceso-a-la-app)).
Las asignaciones que la baja finalizó **no** se reabren, a propósito: *"a la vuelta, a quién entrena se
decide de nuevo, que es lo que el gimnasio haría de verdad"* (`personal.py:703-704`).

**Las habilitaciones sí vuelven, desde el 2026-09-30.** Este apartado decía que no, y con razón: la
baja **borraba** las filas de `Profesor_Actividad`, así que el profesor volvía sin ninguna actividad y
había que asignárselas de nuevo una por una. Lo que la baja borra no lo puede deshacer ningún segundo
camino. Ahora la baja no las toca —el objetivo de que no figure entre los disponibles ya lo cumple el
filtro por `Empleado.activo`—, así que la vuelta no tiene nada que reconstruir: sus actividades siguen
ahí. **Corrido** contra la base real: un profesor con una actividad y un turno dictado se dio de baja,
dejó de aparecer en la lista de habilitados y en el plantel, y al reactivarlo volvió a aparecer sin que
nadie lo reasignara. Es la diferencia entre los dos caminos de la
[baja lógica](A-10-bajas-logicas.md#los-dos-caminos): lo que se marca se desmarca, lo que se borra se
perdió.

**Nota marcada · la fecha de egreso se pisa.** Queda una cosa que el segundo camino no deshace, y ésta
sí es una pérdida real: la **fecha de egreso**, que la reactivación pone en `NULL` (`:735`). Con una
sola `fecha_ingreso`, la original, la ficha no cuenta que la persona se fue y volvió. El socio no tiene
este problema porque sus bajas son filas de `Baja`
([A-10](A-10-bajas-logicas.md#tipo-de-baja-y-el-acople-de-la-cuenta)); el empleado guarda el episodio en
dos columnas que se pisan.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| El empleado no existe | 404 | *"El empleado no existe."* | `personal.py:725-728` |
| Ya estaba activo | 400 | *"{nombre} ya estaba activo."* | `personal.py:729-732` |

---

## Con qué se conecta

- **Existe por culpa de…** [clave foránea y acción referencial](A0-07-bases-de-datos-relacionales.md#clave-foránea-y-acción-referencial):
  el mismo rechazo que protege el historial trababa el cambio de rol y la baja de un profesor que dictó
  una clase; los dos se resolvieron igual, apagando la fila en vez de borrarla, y el segundo además
  descubrió que el borrado era innecesario.
- **Existe por culpa de…** [el rol que se apaga](A-10-bajas-logicas.md#el-rol-que-se-apaga): los roles
  van en plural y con casillas, y el 409 del cambio de rol desapareció, porque la fila del rol viejo
  dejó de borrarse.
- **Existe por culpa de…** [la tabla subtipo](A-05-modelo-de-datos.md#tabla-subtipo-especialización):
  el rol es la fila, y por eso el alta inserta el empleado antes de tener función y los disparadores
  diferidos dejan pasar ese instante en que no es nada.
- **Es el mismo problema que…** [listado en lote](A-11-rendimiento.md#listado-en-lote): a la grilla de
  personal le faltan dos relaciones en la carga anticipada y vuelve a crecer una consulta por empleado,
  la causa que el lote había cerrado en Socios.
- **Existe por culpa de…** [aplicación gemela](A-03-dos-apps-un-backend.md#aplicación-gemela-y-componente-gemelo):
  la edición del empleado toca sólo los campos que vinieron porque dos formularios distintos escriben la
  misma fila, y con "todos, siempre" cada gemela borraba lo que la otra cargaba.
- **Es la misma idea que…** [el frontend esconde, el backend rechaza](A-08-autorizacion.md#el-frontend-esconde-el-backend-rechaza):
  los selectores de entrenadores y de nutricionistas son el backend ayudando a esconder: a quien sólo
  puede elegirse a sí mismo le devuelven sólo a él, para no ofrecer lo que después rechaza.
