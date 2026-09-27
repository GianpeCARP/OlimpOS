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

**Lo que se corrió, y cómo.** Cuatro de los hallazgos de este capítulo dependen de lo que hace
PostgreSQL con una clave foránea, y eso no se ve leyendo. Se probaron llamando a las funciones reales
de `backend/routers/personal.py` —con una sesión del Dueño armada a mano, sin HTTP— contra un
PostgreSQL 17 local y descartable, creado en una carpeta temporal y cargado con `db/schema.sql`. Nunca
contra Neon: la variable de la base apuntaba al servidor local antes de importar el backend, y el
servidor se borró al terminar. Cada resultado obtenido así dice **corrido**; el resto es lectura.

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
es *"una decisión del negocio, no operativa del día a día"* (`backend/routers/personal.py:167-169`).
Las dos últimas filas son la rareza de la sección: dos endpoints que viven bajo `/personal` y no piden
la sección Personal, porque los usan los formularios de Rutinas y de Nutrición (procesos 31 y 33).

Una regla más, a nivel de fila: **nadie se da de baja a sí mismo**. Está en los tres lugares —el
backend la hace cumplir (`personal.py:597-602`), y las dos apps omiten el botón en la propia tarjeta
(`PersonalView.tsx:54-58`, `Flet/Proyecto/app/views/personal.py:100-101`)—, y el comentario del
backend da el porqué: *"se quedaría sin acceso en el acto, y si era el único con el permiso no habría
quien lo revierta"*.

### El rol es una fila, y la base exige que exista

Un empleado es Entrenador, Nutricionista, Recepcionista o Profesor según en cuál de las cuatro tablas
hijas tenga fila. El router lo lleva a una tabla de datos, `ESPECIALIDADES` (`personal.py:64-69`), que
dice qué clase corresponde a cada rol y qué campos acepta cada una:

| Rol | Tabla | Campos propios |
|---|---|---|
| Entrenador | `Entrenador` | `titulo`, `especialidad`, `matricula` |
| Nutricionista | `Nutricionista` | `titulo`, `matricula` |
| Recepcionista | `Recepcionista` | `id_franja_laboral` |
| Profesor | `Profesor` | `titulo`, `especialidad` |

Esa tabla la usan el alta (`:234-236`), la lectura y la edición (`:540-562`). Para leer el rol,
`_especialidad_de()` (`:81-90`) prueba las cuatro relaciones en ese orden y devuelve la primera que
tiene fila.

La base agrega la mitad que el código no ve: **cinco disparadores de restricción**
(`db/schema.sql:1176-1216` la función, `:1218-1241` los disparadores). Uno corre al insertar un
`Empleado` y los otros cuatro al borrar una fila de cualquier subtipo, y los cinco verifican lo mismo:
que el empleado tenga al menos un subtipo. Son `DEFERRABLE INITIALLY DEFERRED`, así que verifican **al
confirmar**, no en cada sentencia
([consistencia al final](A0-07-bases-de-datos-relacionales.md#c--consistencia-al-final-las-reglas-se-cumplen)).
Eso es lo que hace posibles dos operaciones de este capítulo:

- **El alta** (proceso 30) inserta primero el `Empleado` —que en ese instante no tiene subtipo— y
  después la fila de su rol. Al confirmar, la regla ya se cumple.
- **El cambio de rol** (proceso 35) borra la fila del rol viejo e inserta la del nuevo. Entre una
  sentencia y otra, el empleado no es nada; al confirmar, ya es otra cosa. **Corrido:** un entrenador
  sin trabajo a su nombre pasó a nutricionista sin error.

**Nota marcada · el código contempla un estado que la base prohíbe.** El docstring del módulo dice que
*"un empleado sin fila en ninguna hija es alguien cargado a quien todavía no se le asignó función, que
es un estado válido"* (`personal.py:20-21`). Para la base no lo es: `trg_empleado_completo` rechaza el
`COMMIT` de un empleado sin subtipo. Las ramas que cuidan ese caso no hacen daño pero no se ejecutan
nunca: `rol=None` en la respuesta (`backend/schemas.py:1729`, *"cargado sin especialidad todavía"*), el
fallback de la PWA que lo muestra como Recepcionista
(`Proyecto - PWA/src/frontend/src/services/personalService.ts:118-121`) y el "Sin asignar" de Flet
(`Flet/Proyecto/app/state.py:460`, con su caída a Entrenador en `views/personal.py:238-244`). Acá no
gana el código ni el comentario: gana la base.

### El Profesor tiene cuenta, como los otros tres

Hasta el 2026-09-16 el Profesor no tenía rol de sesión: *"da clases, no usa el sistema"*. Desde
entonces tiene cuenta y su pantalla, "Mis clases" en la PWA, y el alta lo dice en el lugar que manda,
el código: *"Los CUATRO roles pueden tener cuenta"* (`personal.py:242-245`), y la casilla se respeta
igual para los cuatro (`:246`). Las dos apps la piden siempre (`personalService.ts:266`,
`Flet/Proyecto/app/views/personal.py:432`), y el encabezado del router y los dos comentarios del
esquema lo cuentan igual (`personal.py:28-32`, `schemas.py:1655-1657`, `:1706-1707`).

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

**Qué resuelve.** La grilla de tarjetas del personal: nombre, rol, el dato propio del rol, el teléfono
principal, si tiene cuenta y si está activo.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/personal/PersonalView.tsx` | 35-243 | `PersonalView` (la carga, 69-83) |
| Tarjeta PWA | `Proyecto - PWA/src/frontend/src/views/personal/StaffCard.tsx` | 87-205 | `StaffCard` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/personalService.ts` | 88-138 | `detalleDeRol()`, `aEmpleadoListado()`, `listarPersonal()` |
| Esquema | `backend/schemas.py` | 1721-1745 | `EmpleadoOut` |
| Endpoint | `backend/routers/personal.py` | 133-155 | `listar_personal()` |
| Armado | `backend/routers/personal.py` | 81-130 | `_especialidad_de()`, `_telefono_principal()`, `_a_empleado_out()` |
| Vista Flet | `Flet/Proyecto/app/views/personal.py` | 57-203 | `build()`, `_staff_card()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 444-482 | `get_personal()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 497-498 | `obtener_personal()` |

**Cómo funciona.** El endpoint trae a todos los empleados, activos y dados de baja, ordenados por id
(`personal.py:146-154`), y arma cada fila con `_a_empleado_out()` (`:100-130`):

1. **El rol**, con `_especialidad_de()` (`:102`).
2. **Los datos del rol**, con `getattr(fila, campo, None)` (`:115-117`): cada hija tiene sólo algunos
   campos, y pedirle `titulo` a un Recepcionista tiene que dar `None`, no romper.
3. **El turno**, que ya no es texto sino una clave foránea a `Franja_Laboral`: viaja el nombre de la
   franja, sólo para el Recepcionista (`:120-122`), y el id aparte, para el formulario (`:123`).
4. **El teléfono principal**, o el más viejo si ninguno está marcado (`_telefono_principal()`,
   `:93-97`).
5. **Si tiene cuenta** (`:129`).

La PWA filtra en memoria, por texto y por rol (`PersonalView.tsx:87-98`), y el subtítulo cuenta sólo
los activos (`:100-102`); los dados de baja siguen en la grilla, con el distintivo en gris. La tarjeta
muestra debajo del nombre el dato que corresponde a cada rol (`personalService.ts:88-100`): la franja del
Recepcionista, la especialidad del Entrenador o del Profesor, el título de la Nutricionista.

**Qué escribe y qué lee.**

| Tabla | Atributos | Escribe o lee | Línea |
|---|---|---|---|
| `Empleado` | `id_empleado`, `id_persona`, `id_sede`, `legajo`, `fecha_ingreso`, `fecha_egreso`, `activo` | lee | `personal.py:146`, `:105-111` |
| `Persona` | `dni`, `nombre`, `apellido`, `email` | lee | `:124-127` |
| `Telefono` | `numero`, `principal` | lee | `:148`, `:93-97` |
| `Entrenador`, `Nutricionista`, `Recepcionista`, `Profesor` | sus campos propios | lee | `:86-89`, `:115-123` |
| `Franja_Laboral` | `nombre` | lee | `:120` |
| `Usuario` | la existencia de la fila | lee | `:129` |

Coincide con la línea DFD.

**Por qué está hecho así.** El rol se deriva porque es una fila
([tabla subtipo](A-05-modelo-de-datos.md#tabla-subtipo-especialización)), y la carga anticipada existe
para que esa derivación no cueste una consulta por empleado
([listado en lote](A-11-rendimiento.md#listado-en-lote)). Lo que sigue muestra que la cuenta quedó a
medias.

**Nota marcada · la carga anticipada se olvidó del cuarto subtipo y de la cuenta.** El comentario de
la consulta dice que el rol *"se deriva de cual de los tres subtipos tiene fila"* (`personal.py:142-145`),
y carga esos tres: `entrenador`, `nutricionista` y `recepcionista` (`:149-151`). Son cuatro. Tampoco
carga `persona.usuario`, que el armado lee para cada fila (`:129`), ni la franja del Recepcionista
(`:120`). Cada una de esas lecturas es una consulta perezosa aparte ([N+1](A0-09-el-orm.md#n1)).
**Corrido**, con seis empleados de los cuales dos eran profesores: **14 consultas** —las 6 en lote, 6
de `Usuario` (una por empleado) y 2 de `Profesor` (una por cada empleado para el que el bucle de
`_especialidad_de()` llega a la cuarta tabla)—. Cada empleado suma una consulta, cada profesor otra, y
cada franja distinta una más. El remedio está escrito en el mismo repo: `CARGA_DE_ROLES` de
`backend/routers/usuarios.py:82-93`, que el comentario cita como modelo, sí incluye `Empleado.profesor`.

**Nota marcada · dos diferencias de la gemela.** El subtítulo de Flet dice *"{N} empleados activos"*
contando a todos, también a los dados de baja (`views/personal.py:63`), contra el conteo de activos de
la PWA. Y la tarjeta de Flet muestra un chip *"Turno —"* para todo el que no es Recepcionista
(`state.py:461`, `views/personal.py:174`), donde la PWA muestra la especialidad o el título.

**Qué pasa cuando sale mal.** El único rechazo es de permisos: 403 para Entrenador, Nutricionista,
Profesor y Socio, que no tienen la sección.

---

### 30. Dar de alta un empleado

`POST /personal` · Dueño

**Qué resuelve.** Contratar a alguien: su persona, su ficha de empleado con legajo, la fila de su rol
y, si se pide, su cuenta con una contraseña temporal para entregarle.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/personal/EmpleadoFormModal.tsx` | 49-243 | `EmpleadoFormModal` (el envío, `handleSubmit`, 93-138) |
| Entrega de la clave | `Proyecto - PWA/src/frontend/src/components/PanelCredenciales.tsx` | 48-151 | `PanelCredenciales` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/personalService.ts` | 158-281 | `repartirDetalle()`, `crearEmpleado()` |
| Esquemas | `backend/schemas.py` | 1665-1708, 1779-1789 | `EmpleadoAltaRequest`, `EmpleadoAltaResponse` |
| Endpoint | `backend/routers/personal.py` | 158-301 | `alta_empleado()` |
| Tabla de roles y legajo | `backend/routers/personal.py` | 64-78 | `ESPECIALIDADES`, `_legajo()` |
| Credenciales | `backend/auth.py` | 90-143 | `generar_password_temporal()`, `generar_username()` |
| Envío por mail | `backend/notificaciones.py` | 89-164 | `enviar_credenciales()` |
| Base | `db/schema.sql` | 1218-1221 | `trg_empleado_completo` |
| Vista Flet | `Flet/Proyecto/app/views/personal.py` | 205-528 | `_open_form()`, `_save()`, `_mostrar_credenciales()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1234-1252 | `alta_empleado()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 518-519 | `alta_empleado()` |

**Cómo funciona.** Las dos apps arman el pedido distinto. La PWA muestra **un solo campo** para el dato
del rol, cuya etiqueta cambia con el rol (`EmpleadoFormModal.tsx:35-40`), y `repartirDetalle()`
(`personalService.ts:172-184`) lo pone en la columna que corresponde —el id de la franja para el
Recepcionista, el título para la Nutricionista, la especialidad para Entrenador y Profesor— y no manda
ninguna otra. Flet muestra **título, especialidad, matrícula y franja siempre**
(`views/personal.py:308-318`, el pedido en `:405-422`); el
esquema acepta cualquier combinación porque *"el router ignora los que no correspondan"*
(`schemas.py:1696-1699`). Las dos mandan la sede clavada en 1 (`personalService.ts:264`,
`views/personal.py:429`), y las dos exigen mail o teléfono antes de salir a la red
(`EmpleadoFormModal.tsx:93-101`, `views/personal.py:387-396`).

El endpoint, en orden:

1. **La sede existe**, o 404 (`personal.py:173-177`).
2. **La persona**: si el DNI ya está cargado, se reusa (`:182`) —*"un socio del gimnasio al que
   contratan de entrenador es el caso típico"* (`:180-181`)—; si no, se crea con un `flush`
   (`:184-193`). Si ya es empleado, 409 (`:194-198`), también si está dado de baja: esa persona se
   reactiva (proceso 37).
3. **El email no choca** con el de otra persona, o 409 (`:200-210`).
4. **El teléfono**, como principal (`:212-218`).
5. **El empleado**, con fecha de ingreso de hoy si no vino otra, y un `flush` para conocer su id
   (`:220-228`). El legajo `E-0001` se arma **después**, con ese id (`:229`, `_legajo()` en `:71-78`),
   por la misma razón que el número de socio: calcularlo antes daría legajos repetidos con dos altas
   simultáneas ([identidad generada](A0-07-bases-de-datos-relacionales.md#clave-primaria-e-identidad-generada)).
6. **La fila del rol**, con sólo los campos que esa tabla tiene (`:234-236`): *"crear la fila en la
   tabla hija ES asignarle la función"* (`:232-233`).
7. **La cuenta**, si se pidió (`:246-261`): si la persona ya tenía una, se conserva; si no, usuario y
   clave temporal, con la cuenta marcada para cambiarla.
8. **Una sola confirmación** (`:263`). Ahí corre `trg_empleado_completo` y verifica que el empleado
   tenga su rol; si algo falló antes, no queda nada a medias.
9. **El mail, después de confirmar** (`:268-275`), y un mensaje en tres versiones según haya clave
   nueva, cuenta conservada o ninguna cuenta (`:277-288`).

Con la respuesta, la PWA vuelve a pedir el empleado para tener la fila de la grilla
(`personalService.ts:271`, el único cliente del proceso 34) y, si hay clave, abre el panel de entrega en
vez de cerrar (`EmpleadoFormModal.tsx:122-125`).

**Qué escribe y qué lee.**

| Tabla | Atributos | Escribe o lee | Línea |
|---|---|---|---|
| `Sede` | `id_sede` | lee | `personal.py:173` |
| `Persona` | `dni` (para reusar), `email` (para el choque) | lee | `:182`, `:201-205` |
| `Persona` | `dni`, `nombre`, `apellido`, `email`, `fecha_nacimiento` | escribe | `:185-191` |
| `Empleado` | la existencia de la fila de la persona | lee | `:194` |
| `Telefono` | `id_persona`, `numero`, `tipo`, `principal` | escribe | `:213-218` |
| `Empleado` | `id_persona`, `id_sede`, `fecha_ingreso`, `activo`, `legajo` | escribe | `:221-229` |
| `Entrenador`, `Nutricionista`, `Recepcionista` o `Profesor` | `id_empleado` y sus campos propios | escribe | `:234-236` |
| `Usuario` | la cuenta de la persona y `username` (para no repetirlo) | lee | `:247-248`, `:250-253` |
| `Usuario` | `id_persona`, `username`, `password_hash`, `debe_cambiar_password`, `activo` | escribe | `:255-261` |

Coincide con la línea DFD, que además lee `Persona.activo`: sale en la respuesta, con la persona
(`:294`).

**Por qué está hecho así.** Una sola transacción, igual que el alta de socio
([B-02](B-02-socios.md#7-dar-de-alta-un-socio-con-su-cuenta-de-acceso-y-credenciales-temporales)). Mail
o teléfono obligatorios porque sin ninguno *"no hay por dónde mandarle sus credenciales"*
(`schemas.py:1683-1684`). Y `ESPECIALIDADES` como tabla de datos en vez de un `if` de cuatro ramas
repetido en el alta, la lectura y la edición (`personal.py:61-63`).

**Nota marcada · el reuso de la persona, otra vez.** Es el mismo mecanismo del alta de socio, con las
mismas pérdidas: si la persona ya existía, el nombre, el apellido, el email y la fecha de nacimiento
del formulario **se descartan sin aviso** —sólo se usan al crearla (`personal.py:184-192`)—, y el
teléfono se agrega como principal sin desmarcar el que ya tuviera (`:212-218`), así que la ficha puede
quedar con dos principales. Y agrega uno propio: la cuenta que *"se conserva"* (`:247-248`) puede estar
**apagada**. Un ex socio dado de baja por mora tiene la cuenta desactivada
([tipo de baja](A-10-bajas-logicas.md#tipo-de-baja-y-el-acople-de-la-cuenta)); si el gimnasio lo
contrata, el alta no la prende, el mensaje dice *"Ya tenía cuenta ('…'), se conserva"* (`:282-286`) y el
empleado nuevo no puede entrar. Leído, no corrido.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| La sede no existe | 404 | *"La sede indicada no existe."* | `personal.py:173-177` |
| La persona ya es empleado, activo o de baja | 409 | *"{nombre} ya está registrado como empleado."* | `personal.py:194-198` |
| El email es de otra persona | 409 | *"Ese email ya está registrado para otra persona."* | `personal.py:200-210` |
| Sin mail ni teléfono | 422 | *"Cargá un email o un teléfono: hace falta para contactarlo."* | `schemas.py:1681-1688` |
| DNI de menos de 6 caracteres, nombre o apellido vacíos, rol que no existe | 422 | el de Pydantic | `schemas.py:1671-1673`, `:1695` |
| Teléfono con letras o email sin dominio | 422 | los de sus validadores | `schemas.py:41-54`, `:74-100` |
| Una franja que no existe | 500 | ninguno legible | `personal.py:263` |

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
| Endpoint | `backend/routers/personal.py` | 416-435 | `listar_entrenadores()` |
| Armado | `backend/routers/personal.py` | 392-413 | `_opciones()` |
| Quién pide | `backend/routers/rutinas.py` | 68-80 | `_entrenador_de_sesion()` |
| Vistas Flet | `Flet/Proyecto/app/views/rutinas.py` | 240 | `get_entrenadores` |
| | `Flet/Proyecto/app/views/socios.py` | 965 | `get_entrenadores` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1254-1264 | `get_entrenadores()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 501-502 | `obtener_entrenadores()` |

**Cómo funciona.** `_opciones()` trae los entrenadores cuyo empleado está activo (`personal.py:400-405`),
les pone el nombre de la persona (`:407-412`) y los ordena por nombre (`:413`). Después, si quien pide
tiene ficha de entrenador, la lista se reduce a él (`:431-434`): `_entrenador_de_sesion()` busca un
empleado de esa persona con fila en `Entrenador` (`rutinas.py:75-80`). El Dueño, el Recepcionista y la
Nutricionista reciben a todos. **Corrido:** una entrenadora recibió sólo su nombre; una nutricionista,
los dos entrenadores.

**Qué escribe y qué lee.** Lee `Entrenador` (`id_entrenador`, `id_empleado`), `Empleado` (`activo`, y
`id_persona` para reconocer a quien pide) y `Persona` (`nombre`, `apellido`). Coincide con la línea DFD.

**Por qué está hecho así.** Pide la sección Rutinas y no Personal porque *"quien arma una rutina
necesita elegir el entrenador aunque no tenga acceso a la ficha de personal"* (`personal.py:422-424`).
Filtra a los activos para no ofrecer a quien ya no trabaja (`:396-398`). Y el recorte al propio
entrenador es el backend ayudando a esconder: el alta de rutina rechaza igual una a nombre de otro, pero
*"filtrarlo acá hace que los selectores de las dos apps dejen de ofrecer algo que después falla, sin
tocar ninguna pantalla"* (`:428-429`;
[el frontend esconde, el backend rechaza](A-08-autorizacion.md#el-frontend-esconde-el-backend-rechaza)).
Va declarado antes que `/{id_empleado}` porque FastAPI prueba las rutas en orden, y si no leería
`entrenadores` como un id (`:387-389`).

`_opciones()` repite en chico el problema del proceso 29: dos consultas perezosas por profesional, el
empleado y la persona (`:408`). **Corrido:** con dos entrenadores activos, 5 consultas más la de
reconocer a quien pide. Con los pocos entrenadores de un gimnasio, no se nota.

**Qué pasa cuando sale mal.** 403 para Profesor y Socio, que no tienen la sección Rutinas.

---

### 32. Listar el catálogo de franjas laborales

`GET /personal/franjas` · Dueño, Recepcionista

**Qué resuelve.** Las opciones del selector de turno del Recepcionista, en el alta y la edición.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/personal/EmpleadoFormModal.tsx` | 68-74 | `listarFranjas` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/personalService.ts` | 218-221 | `listarFranjas()` |
| Esquema | `backend/schemas.py` | 1711-1718 | `FranjaLaboralOut` |
| Endpoint | `backend/routers/personal.py` | 456-472 | `listar_franjas()` |
| Vista Flet | `Flet/Proyecto/app/views/personal.py` | 246-249 | `get_franjas` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 484-490 | `get_franjas()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 509-511 | `obtener_franjas()` |

**Cómo funciona.** Las franjas activas, ordenadas por id (`personal.py:468-471`). La base de ENTREGA
trae tres.

**Qué escribe y qué lee.** Lee `Franja_Laboral` (`id_franja_laboral`, `nombre`, `hora_desde`,
`hora_hasta`, `activo`). Coincide con la línea DFD.

**Por qué está hecho así.** Reemplaza un texto libre, *"el viejo varchar `turno_laboral`"*
(`personal.py:463-464`), por una clave foránea a un catálogo: con texto, "Mañana" y "mañana" eran dos
turnos. El docstring del módulo todavía dibuja `Recepcionista (turno_laboral)` (`:14`), de antes del
cambio. Y la tarjeta de la PWA sigue atada a los nombres: busca el color del chip en un mapa de tres
valores fijos —"Mañana", "Tarde", "Noche"— (`StaffCard.tsx:39-43`, `:99`), y el tipo lo promete con un
`as` que nadie verifica (`personalService.ts:123`). Una franja con otro nombre deja el color en
`undefined`; Flet, con el mismo mapa, cae a un gris neutro (`views/personal.py:95`).

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
| Endpoint | `backend/routers/personal.py` | 438-453 | `listar_nutricionistas()` |
| Armado | `backend/routers/personal.py` | 392-413 | `_opciones()` |
| Quién pide | `backend/routers/nutricion.py` | 71-77 | `_nutricionista_de_sesion()` |
| Vista Flet | `Flet/Proyecto/app/views/nutricion.py` | 274-287 | `_open_form()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1266-1268 | `get_nutricionistas()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 505-506 | `obtener_nutricionistas()` |

**Cómo funciona.** El espejo exacto del 31: `_opciones()` con la tabla `Nutricionista` (`personal.py:449`)
—las activas, por nombre— y, si quien pide tiene ficha de nutricionista, la lista se reduce a ella
(`:450-452`). **Corrido:** una nutricionista recibió sólo su nombre; la dueña, las tres activas.

**Qué escribe y qué lee.** Lee `Nutricionista`, `Empleado` y `Persona`, como el proceso 31. Coincide con
la línea DFD.

**Por qué está hecho así.** Pide la sección Nutrición porque lo usa el formulario de dietas, y recorta
a la propia porque el alta de una dieta rechaza con 403 una a nombre de otro, *"No podés crear dietas a
nombre de otro nutricionista."* (`backend/routers/nutricion.py:88-93`). Sin el recorte, que faltó hasta
el 2026-09-26, la PWA —que preselecciona el primero de la lista cuando la dieta es nueva
(`PlanFormModal.tsx:95-99`)— le ofrecía a una nutricionista que no fuera la primera en orden alfabético
una dieta a nombre de otra, y guardar sin tocar el selector terminaba en ese 403. Los comentarios de
las dos apps ya lo daban por hecho (`PlanFormModal.tsx:27-28`,
`Flet/Proyecto/app/views/nutricion.py:282-285`).

**Qué pasa cuando sale mal.** 403 para Profesor y Socio, que no tienen la sección Nutrición.

---

### 34. Consultar la ficha de un empleado

`GET /personal/{id_empleado}` · Dueño, Recepcionista

**Qué resuelve.** Una fila de la grilla, sola.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Service PWA | `Proyecto - PWA/src/frontend/src/services/personalService.ts` | 140-143 | `obtenerEmpleado()` |
| Endpoint | `backend/routers/personal.py` | 475-485 | `obtener_empleado()` |
| Armado | `backend/routers/personal.py` | 100-130 | `_a_empleado_out()` |

**Cómo funciona.** Busca por clave primaria (`personal.py:481`) y arma la fila con la misma función que
el listado. **Corrido:** cinco consultas para un entrenador —el empleado, la persona, su fila de
`Entrenador`, sus teléfonos y su cuenta—, todas perezosas; para una sola fila, da igual.

**Qué escribe y qué lee.** Lo mismo que el proceso 29, para un empleado. Coincide con la línea DFD.

**Por qué está hecho así.** Su único cliente es el alta de la PWA (`personalService.ts:271`), que
necesita la fila de la grilla y recibe la persona. Flet no lo usa: después de escribir,
vuelve a pedir la lista entera ([servir y refrescar](A-11-rendimiento.md#servir-y-refrescar)).

**Qué pasa cuando sale mal.** 404 *"El empleado no existe."* (`personal.py:482-484`), y 403 para quien
no tiene la sección.

---

### 35. Editar un empleado y su rol

`PUT /personal/{id_empleado}` · Dueño

**Qué resuelve.** Corregir los datos de un empleado y, si hace falta, cambiarle la función.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/personal/EmpleadoFormModal.tsx` | 49-243 | `EmpleadoFormModal` (la edición, 107-110) |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/personalService.ts` | 172-202, 292-308 | `repartirDetalle()`, `detalleEditable()`, `actualizarEmpleado()` |
| Esquema | `backend/schemas.py` | 1748-1772 | `EmpleadoEditarRequest` |
| Endpoint | `backend/routers/personal.py` | 488-566 | `editar_empleado()` |
| Validación | `backend/routers/personal.py` | 308-381 | `_validar_cambio_de_rol()` |
| Base | `db/schema.sql` | 1223-1241 | `trg_entrenador_no_deja_colgado` y sus tres gemelos |
| Vista Flet | `Flet/Proyecto/app/views/personal.py` | 205-450 | `_open_form()`, `_save()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1278-1280 | `editar_empleado()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 514-515 | `editar_empleado()` |

**Cómo funciona.** El endpoint, en orden:

1. **El empleado existe**, o 404 (`personal.py:502-505`).
2. **El email nuevo no choca** con el de otra persona, o 409 (`:509-516`).
3. **El cambio de rol es posible**, o 409 con el motivo (`:518`, `_validar_cambio_de_rol()` en
   `:308-381`). Sólo se mira si el rol cambia; qué se mira está más abajo.
4. **Nombre, apellido y email**, siempre (`:520-522`).
5. **El teléfono, sólo si vino** (`:524-537`): con número, pisa el principal o crea uno; vacío, borra el
   principal.
6. **El rol** (`:540-562`). Si es el mismo, se copian **sólo los campos del rol que vinieron en el
   pedido** (`:543-552`). Si cambió, se borra la fila vieja, se fuerza un `flush` —sin él, SQLAlchemy
   podría mandar el insert antes que el borrado— (`:556-560`) y se inserta la nueva (`:561-562`).
7. **Una confirmación** (`:564`), donde los disparadores diferidos verifican que el empleado haya
   terminado con algún rol ([el rol es una fila](#el-rol-es-una-fila-y-la-base-exige-que-exista)).

Un cambio de rol no le cambia los permisos a quien ya tiene la sesión abierta: los roles viajan en el
token y se leen en el próximo ingreso ([identidad firmada](A-07-autenticacion.md#identidad-firmada)).

**Qué escribe y qué lee.**

| Tabla | Atributos | Escribe o lee | Línea |
|---|---|---|---|
| `Empleado` | la fila | lee | `personal.py:502` |
| `Persona` | `email` (para el choque) | lee | `:510-513` |
| `Rutina`, `Asignacion_Entrenador`, `Horario_Actividad`, `Turno`, `Dieta`, `Profesor_Actividad` | cuántas filas apuntan al rol viejo | lee | `:338`, `:343-351`, `:362`, `:368-371`, `:376-378` |
| `Persona` | `nombre`, `apellido`, `email` | escribe | `:520-522` |
| `Telefono` | `numero` (o la fila entera, al borrar) | escribe | `:525-537` |
| la tabla del rol viejo | la fila | borra | `:556` |
| la tabla del rol nuevo | `id_empleado` y sus campos propios | escribe | `:550-552`, `:561-562` |

Coincide con la línea DFD.

**Por qué está hecho así.** Cambiar de rol es borrar una fila e insertar otra porque el rol **es** la
fila. Y esa fila es el destino de claves foráneas sin acción al borrar, así que con algo apuntándole la
base rechaza el borrado
([acción referencial](A0-07-bases-de-datos-relacionales.md#acción-referencial-qué-le-pasa-al-hijo-cuando-muere-el-padre)).
`_validar_cambio_de_rol()` mira, antes de tocar nada, cada tabla que apunta:

| Tabla que apunta | A qué | Declarada en | Si hay filas |
|---|---|---|---|
| `Rutina` | `Entrenador` | `db/schema.sql:1053` | 409: *"tiene {n} rutina(s) a su nombre. Reasignalas a otro entrenador primero."* (`personal.py:338-341`) |
| `Asignacion_Entrenador` | `Entrenador` | `db/schema.sql:1061` | 409: *"tuvo {n} socio(s) a cargo, contando los que ya terminaron… Ese historial no se borra, así que hoy el rol no se puede cambiar."* (`:343-359`) |
| `Horario_Actividad`, `Turno` | `Entrenador` (a cargo) | `db/schema.sql:1021`, `:1025` | 409, en el mismo mensaje: *"tiene {n} horario(s) o turno(s) de sala a su nombre"* (`:346-359`) |
| `Dieta` | `Nutricionista` | `db/schema.sql:1064` | 409: *"tiene {n} dieta(s) a su nombre. Reasignalas a otro nutricionista primero."* (`:361-365`) |
| `Horario_Actividad`, `Turno` | `Profesor` (vía `Profesor_Actividad`) | `db/schema.sql:1032-1038` | 409: *"tiene {n} horario(s) o clase(s) a su nombre. Ese historial no se borra…"* (`:367-374`) |
| `Profesor_Actividad` | `Profesor` | `db/schema.sql:1017` | 409: *"está habilitado para {n} actividad(es). Sacalo de esas actividades en Actividades primero."* (`:376-381`) |

Los mensajes separan dos clases de bloqueo, y el docstring dice por qué (`personal.py:320-327`): lo que
**se puede sacar** —rutinas y dietas que se reasignan, las actividades de un profesor que todavía no dio
clases— dice qué hacer primero; el **historial** —los socios que tuvo a cargo, los horarios y los turnos
a su nombre— no se borra nunca, y con él el rol no se puede cambiar. **Corrido** contra un PostgreSQL
descartable: una entrenadora con una sola asignación, ya finalizada; un entrenador con un horario de
sala; un profesor con un horario; un profesor sólo habilitado; y una nutricionista con una dieta. Los
cinco recibieron su 409 con el mensaje, y un entrenador sin nada a su nombre pasó a nutricionista sin
error.

**Nota marcada · el cambio de rol con historial es un límite, no una regla del negocio.** Como la
historia de asignaciones no se borra nunca
([B-02, proceso 8](B-02-socios.md#8-finalizar-la-asignación-de-un-entrenador-conservando-el-historial)),
**un entrenador que alguna vez tuvo un alumno a cargo no puede cambiar de rol**, y un profesor que tuvo
una clase a su nombre tampoco. Nadie lo decidió: sale de que cambiar de rol **borra** la fila vieja. El
dueño eligió, el 2026-09-26, frenarlo con un mensaje en vez del 500 que daba antes, y dejarlo anotado
para resolverlo a futuro. El camino sería que el cambio conserve la fila vieja en vez de borrarla, lo
que obliga a decidir cómo se deriva el rol cuando un empleado tiene dos filas de subtipo.

**Editar sin cambiar el rol no borra lo que no se tocó.** El paso 6 aplica la regla del `PUT` de socio
([B-02, proceso 11](B-02-socios.md#11-editar-la-ficha-de-un-socio)): un campo ausente se conserva, uno
en `null` se borra (`personal.py:544-552`; el esquema lo anota campo por campo, `schemas.py:1769-1771`).
Hace falta porque cada app muestra campos distintos. La PWA muestra uno por rol y manda sólo ese
(`personalService.ts:172-184`), precargado con la columna exacta que va a escribir (`detalleEditable()`,
`:193-202`) y no con el dato de la tarjeta, que cae a otra columna si la primera está vacía. Flet muestra
título, especialidad y matrícula (`views/personal.py:308-318`). Hasta el 2026-09-26 el endpoint copiaba
todos los campos, la PWA mandaba en `null` los que no mostraba y Flet no tenía el de especialidad:
editarle el teléfono a un entrenador desde la PWA le borraba el título y la matrícula, desde Flet le
borraba la especialidad, y a una nutricionista con matrícula y sin título la PWA le mudaba la matrícula
al título. **Corrido:** hoy los tres casos conservan lo que no se tocó, y un `null` explícito sí borra.

Dos diferencias menores de la gemela, en el mismo formulario. Flet ofrece el DNI **editable** en la
edición, con un comentario que dice que *"no se edita desde acá"* (`views/personal.py:282-286`): el
esquema de edición no tiene DNI y lo descarta sin aviso
([nada muerto en pantalla](A-01-que-es-olimpos.md#nada-muerto-en-pantalla)); la PWA lo muestra como
texto (`EmpleadoFormModal.tsx:169-182`). Y un teléfono vaciado: la PWA manda la cadena vacía
(`personalService.ts:302`) y el backend borra el principal, sin ascender otro, mientras que Flet manda
`None` (`views/personal.py:413`) y el backend no lo toca. Desde Flet, el teléfono de un empleado no se
puede quitar.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| El empleado no existe | 404 | *"El empleado no existe."* | `personal.py:502-505` |
| El email es de otra persona | 409 | *"Ese email ya está registrado para otra persona."* | `personal.py:514-516` |
| Cambio de rol con algo que se puede sacar: rutinas, dietas o actividades habilitadas | 409 | *"No se puede cambiarle el rol: …"* y qué hacer primero | `personal.py:338-341`, `:361-365`, `:376-381` |
| Cambio de rol con historial: socios que tuvo a cargo, horarios o turnos a su nombre | 409 | *"No se puede cambiarle el rol: … Ese historial no se borra, así que hoy el rol no se puede cambiar."* | `personal.py:343-359`, `:367-374` |
| Sin mail ni teléfono | 422 | *"Cargá un email o un teléfono: hace falta para contactarlo."* | `schemas.py:1763-1768` |

---

### 36. Dar de baja a un empleado

`POST /personal/{id_empleado}/baja` · Dueño

**Qué resuelve.** Que alguien que dejó de trabajar en el gimnasio deje de figurar como activo y deje de
poder entrar, sin borrar nada de lo que hizo.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/personal/PersonalView.tsx` | 114-135 | `pedirBaja` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/personalService.ts` | 318-327 | `darDeBajaEmpleado()` |
| Esquema | `backend/schemas.py` | 1775-1776 | `BajaEmpleadoRequest` |
| Endpoint | `backend/routers/personal.py` | 569-643 | `dar_de_baja_empleado()` |
| Vista Flet | `Flet/Proyecto/app/views/personal.py` | 343-361 | `_cambiar_estado()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1270-1272 | `baja_empleado()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 522-523 | `baja_empleado()` |

**Cómo funciona.** Las dos apps confirman antes, con el mismo texto: *"Deja de figurar como activo y
su cuenta de acceso se desactiva. Si entrena socios, deja de estar a cargo de ellos. Se puede
reactivar."* (`PersonalView.tsx:116-132`, `views/personal.py:355-361`). El endpoint:

1. **Existe**, o 404 (`personal.py:588-591`); **no estaba ya de baja**, o 400 (`:592-595`); **no es uno
   mismo**, o 403 (`:597-602`).
2. **La ficha**: inactiva, con fecha de egreso de hoy (`:604-605`).
3. **La cuenta**, apagada, si tiene (`:607-608`).
4. **Si es profesor, sus habilitaciones**: se borran las filas de `Profesor_Actividad`, para que no
   siga figurando entre quienes pueden dictar una actividad (`:619-622`). Los turnos ya programados no
   se tocan (`:615-618`).
5. **Si es entrenador, sus alumnos**: las asignaciones `ACTIVA` que lo tienen a cargo pasan a
   `FINALIZADA`, con fecha de fin de hoy (`:633-639`). Las ya finalizadas conservan su fecha.
6. **Una confirmación** (`:641`).

**Qué escribe y qué lee.**

| Tabla | Atributos | Escribe o lee | Línea |
|---|---|---|---|
| `Empleado` | `activo`, `id_persona` | lee | `personal.py:592`, `:599` |
| `Empleado` | `activo`, `fecha_egreso` | escribe | `:604-605` |
| `Usuario` | `activo` | escribe | `:607-608` |
| `Profesor` | la existencia de la fila | lee | `:619` |
| `Profesor_Actividad` | las filas del profesor | borra | `:620-622` |
| `Entrenador` | la existencia de la fila | lee | `:633` |
| `Asignacion_Entrenador` | `id_entrenador`, `estado` (para elegir las activas) | lee | `:635-636` |
| `Asignacion_Entrenador` | `estado`, `fecha_fin` | escribe | `:637-638` |

Coincide con la línea DFD, salvo en un rechazo que la línea no tiene; lo cuenta la nota que sigue.

**Por qué está hecho así.** [Baja lógica](A-10-bajas-logicas.md#baja-lógica-soft-delete): *"la fila del
rol queda intacta: alguien dado de baja sigue habiendo sido entrenador, y sus rutinas siguen atribuidas
a él"* (`personal.py:580-581`). Y la cuenta se apaga siempre, a diferencia del socio, porque el acceso
de un empleado se justifica en el puesto
([el acople total](A-10-bajas-logicas.md#en-los-empleados-el-acople-es-total)).

Las asignaciones del entrenador se cierran por la regla de `CLAUDE.md` —*"al cambiar el estado de una
entidad, decidir qué pasa con todo lo que la referencia"*—: sin el paso 5, el portal del socio, que
lista las asignaciones `ACTIVA` (`backend/routers/portal.py:2209-2213`), le seguía mostrando en "Mi
entrenador" a alguien que ya no trabaja en el gimnasio. Se **finalizan** y no se borran, con el mismo
cierre que `finalizar_asignacion()` (`backend/routers/socios.py:1101-1102`), para que el historial de
quién entrenó a quién quede (`personal.py:629-630`). **Corrido** contra un PostgreSQL descartable: las
dos asignaciones activas de un entrenador pasaron a finalizadas con fecha de hoy, una vieja conservó
su fecha, la de otra entrenadora con el mismo alumno no se tocó, y la reactivación no las reabrió.

**Nota marcada · un profesor que dictó una clase no se puede dar de baja.** El paso 4 choca con dos
claves foráneas compuestas: `fk_horario_profesor_habilitado` y `fk_turno_profesor_habilitado`
(`db/schema.sql:1032-1038`) exigen que el par profesor-actividad de cada horario y de cada turno exista
en `Profesor_Actividad`. Borrar la habilitación mientras un horario o un turno la usa es borrar un padre
con hijos, y el esquema no declara acción
([el truco del nulo en una clave compuesta](A0-07-bases-de-datos-relacionales.md#el-truco-del-nulo-en-una-clave-foránea-compuesta)
explica cuándo se verifica). **Corrido:** un profesor con un horario cargado → `IntegrityError` en
`fk_horario_profesor_habilitado`, en el borrado de la línea 620. La transacción entera se deshizo: el
empleado siguió activo y con la cuenta prendida. Un profesor sólo habilitado, sin horario, se dio de
baja bien.

El comentario del paso quiere exactamente lo que la base impide: que los turnos *"guardan su propio
id_profesor"* y queden, mientras se borra la habilitación (`personal.py:615-618`). No pueden convivir.
Y como los turnos no se borran nunca —los pasados quedan, y cambiar el profesor de un horario sólo mueve
los futuros—, **todo profesor que tuvo un turno queda imposible de dar de baja** desde esta pantalla,
con un 500 sin explicación. El comentario dice que es *"exactamente el mismo criterio que
desasignar_profesor"*, y es cierto: `desasignar_profesor()` (`backend/routers/actividades.py:879-897`)
borra la misma fila con la misma promesa, y le toca
[B-08](B-08-actividades-turnos-horarios.md). La línea DFD de este proceso no lo registra.

**Nota marcada · el motivo que no llega a ningún lado.** `BajaEmpleadoRequest` acepta un `motivo`
(`schemas.py:1775-1776`) y los dos clientes lo pasan si lo reciben (`personalService.ts:318-325`,
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
| El empleado no existe | 404 | *"El empleado no existe."* | `personal.py:588-591` |
| Ya estaba de baja | 400 | *"{nombre} ya estaba dado de baja."* | `personal.py:592-595` |
| Es uno mismo | 403 | *"No podés darte de baja a vos mismo."* | `personal.py:597-602` |
| Es un profesor con horarios o turnos | 500 | ninguno legible | `personal.py:620-622` |

La línea DFD nombra los tres primeros.

**Qué ve la pantalla con un 500.** El backend no tiene manejador para los errores de la base, y
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
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/personal/PersonalView.tsx` | 137-150 | `activar` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/personalService.ts` | 329-332 | `reactivarEmpleado()` |
| Endpoint | `backend/routers/personal.py` | 646-669 | `reactivar_empleado()` |
| Vista Flet | `Flet/Proyecto/app/views/personal.py` | 343-354 | `_cambiar_estado()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1274-1276 | `reactivar_empleado()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 526-527 | `reactivar_empleado()` |

**Cómo funciona.** Existe, o 404 (`personal.py:653-656`); estaba de baja, o 400 (`:657-660`). La ficha
vuelve a activa y **se borra la fecha de egreso** (`:662-663`); la cuenta, si tiene, se prende
(`:664-665`). Las dos apps lo hacen sin confirmación: *"reactivar es una acción de bajo riesgo y
reversible"* (`PersonalView.tsx:137-139`).

**Qué escribe y qué lee.** Escribe `Empleado.activo`, `Empleado.fecha_egreso` y `Usuario.activo`; lee
el empleado y su persona. Coincide con la línea DFD.

**Por qué está hecho así.** Es el segundo camino de la baja lógica
([los dos caminos](A-10-bajas-logicas.md#los-dos-caminos)): lo que la baja marcó, la reactivación lo
desmarca. Y prende la cuenta sin preguntar por qué estaba apagada, como la reactivación del socio
([B-02, proceso 24](B-02-socios.md#24-reactivar-a-un-socio-dado-de-baja-y-devolverle-el-acceso-a-la-app)).
Las asignaciones que la baja finalizó **no** se reabren, a propósito: *"a la vuelta, a quién entrena se
decide de nuevo, que es lo que el gimnasio haría de verdad"* (`personal.py:631-632`).

**Nota marcada · lo que la baja borró no vuelve.** Hay dos cosas que el segundo camino no puede
deshacer, porque la baja no las marcó sino que las borró o las pisó. Las **habilitaciones del
profesor**, borradas en la baja (`personal.py:620-622`): el profesor vuelve sin ninguna actividad, y hay
que asignárselas de nuevo en Actividades. Y la **fecha de egreso**, que la reactivación pone en `NULL`
(`:663`): con una sola `fecha_ingreso`, la original, la ficha no cuenta que la persona se fue y volvió.
El socio no tiene este problema porque sus bajas son filas de `Baja`
([A-10](A-10-bajas-logicas.md#tipo-de-baja-y-el-acople-de-la-cuenta)); el empleado guarda el episodio en
dos columnas que se pisan.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| El empleado no existe | 404 | *"El empleado no existe."* | `personal.py:653-656` |
| Ya estaba activo | 400 | *"{nombre} ya estaba activo."* | `personal.py:657-660` |

---

## Con qué se conecta

- **Se contradice con…** [clave foránea y acción referencial](A0-07-bases-de-datos-relacionales.md#clave-foránea-y-acción-referencial):
  el rechazo que protege el historial es el que impide dar de baja a un profesor que dictó una clase y
  cambiarle el rol a un empleado con historial; ganó el historial, y el cambio de rol lo dice con un
  409, pero la baja del profesor todavía no.
- **Existe por culpa de…** [la tabla subtipo](A-05-modelo-de-datos.md#tabla-subtipo-especialización):
  cambiar el rol es borrar una fila e insertar otra, porque el rol es la fila, y los disparadores
  diferidos son lo que deja pasar el instante en que el empleado no es nada.
- **Es el mismo problema que…** [listado en lote](A-11-rendimiento.md#listado-en-lote): a la grilla de
  personal le faltan dos relaciones en la carga anticipada y vuelve a crecer una consulta por empleado,
  la causa que el lote había cerrado en Socios.
- **Existe por culpa de…** [aplicación gemela](A-03-dos-apps-un-backend.md#aplicación-gemela-y-componente-gemelo):
  la edición del empleado toca sólo los campos que vinieron porque dos formularios distintos escriben la
  misma fila, y con "todos, siempre" cada gemela borraba lo que la otra cargaba.
- **Es la misma idea que…** [el frontend esconde, el backend rechaza](A-08-autorizacion.md#el-frontend-esconde-el-backend-rechaza):
  los selectores de entrenadores y de nutricionistas son el backend ayudando a esconder: a quien sólo
  puede elegirse a sí mismo le devuelven sólo a él, para no ofrecer lo que después rechaza.
