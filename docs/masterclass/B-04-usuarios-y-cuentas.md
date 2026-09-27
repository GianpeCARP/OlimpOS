# B-04 · Usuarios y cuentas de acceso

*Procesos 38 a 45. Piso del capítulo: la línea que implementa cada paso, en las tres capas.*

Ocho procesos sobre la **cuenta de acceso**, que no es la persona: la persona nace con el alta en Socios
o en Personal, y la cuenta es su credencial para entrar. Se agrupan en tres temas:

| Tema | Procesos |
|---|---|
| Ver: las cuentas y las personas que todavía no tienen una | 38, 40 |
| Dar y corregir el acceso: crear la cuenta, editar usuario y email | 39, 41 |
| Operar sobre una cuenta: resetear, desbloquear, activar o desactivar, borrar | 44, 43, 45, 42 |

El porqué de fondo está en la Parte A: la contraseña que genera el sistema y se muestra una vez, en
[contraseña temporal](A-07-autenticacion.md#contraseña-temporal-y-primer-ingreso); la traba por
intentos fallidos, en [freno de intentos](A-07-autenticacion.md#freno-de-intentos-y-respuesta-indistinguible);
por qué desactivar corta una sesión y un token no, en
[caducidad y revocación](A0-12-sesiones-y-autenticacion.md#caducidad-y-revocación); que la cuenta y la
ficha son cosas distintas, en [las dos banderas](A-10-bajas-logicas.md#las-dos-banderas); y el único
borrado real del sistema, en [borrado real de la cuenta](A-10-bajas-logicas.md#borrado-real-de-la-cuenta).

**Lo que se corrió, y cómo.** Esta vez de punta a punta por HTTP: el cliente de pruebas de FastAPI
contra la aplicación real, con la base apuntando a un PostgreSQL 17 local y descartable cargado con
`db/schema.sql` (nunca Neon, sin levantar uvicorn y sin correr el arranque), con login, cambio de clave
y cada endpoint del router como los llaman las apps de escritorio. Cada resultado obtenido así dice
**corrido**.

---

## Piezas comunes

### Quién puede qué en esta sección

| Barrera | Quién la tiene | La usan |
|---|---|---|
| Sección `USUARIOS` en lectura | Dueño y Recepcionista, los dos en total | 38, 40 |
| Acción `GESTION_USUARIOS` | Dueño y Recepcionista | 39, 41 a 45 |

El Recepcionista tiene la sección completa porque el mostrador es donde aparece el socio que se olvidó
la clave. Las dos apps, sin embargo, abren la pantalla con un cartel que dice *"Esta sección es
exclusiva para administradores del sistema."* (`Proyecto - PWA/src/frontend/src/views/usuarios/UsuariosView.tsx:224-233`,
`Flet/Proyecto/app/views/usuarios.py:99`), que al Recepcionista que la usa todos los días le dice algo
que no es.

### Las dos reglas de fila

La matriz de permisos contesta "¿este rol puede gestionar cuentas?". Acá hacen falta dos respuestas que
la matriz no puede dar, porque no dependen de quién pregunta sino de **qué fila toca**
(`backend/routers/usuarios.py:7-33`):

1. **La cuenta propia.** Nadie fuera del Dueño edita su propia cuenta
   (`_validar_no_es_propia()`, `:184-197`), y nadie —tampoco el Dueño— la desactiva ni la borra
   (`:14-18`).
2. **La cuenta de un dueño.** Sólo un Dueño opera sobre la cuenta de un Dueño
   (`_validar_jerarquia()`, `:167-181`). Es la importante, y el docstring cuenta por qué: el
   Recepcionista tiene `GESTION_USUARIOS`, y sin esta regla podía resetearle la clave al Dueño, **leer
   la temporal en su propia pantalla** y entrar con control total: *"Escalación de privilegios
   completa, con tres clicks y sin herramientas"* (`:28-30`).

Cada operación aplica una combinación distinta, y tres de ellas agregan una regla propia más dura:

| Operación | Sobre la propia, quien no es dueño | Sobre la propia, el Dueño | Sobre la de un dueño, quien no es dueño |
|---|---|---|---|
| Editar (41) | 403 | permitido | 403 |
| Resetear la clave (44) | permitido, y corta su sesión | permitido, y corta su sesión | 403 |
| Desbloquear (43) | el backend no lo impide; la pantalla no lo ofrece | permitido | 403 |
| Activar o desactivar (45) | 403 | **403 también** (`:484-489`) | 403 |
| Borrar (42) | 403 | **403 también** (`:550-552`) | 403, y nunca la última de un dueño (`:554-561`) |
| Crear (39) | — | — | 403 si la persona es dueña (`:314-318`) |

Resetear la propia queda permitido a propósito: *"no hay riesgo en eso, y es lo que deja hacer
cualquier sistema real"* (`:20-21`). Y corta la sesión porque la cuenta queda marcada para cambiar la
clave y el backend rechaza sus tokens ([la bandera que rechaza el token](A-07-autenticacion.md#la-bandera-que-rechaza-el-token)).

Las dos reglas están en las tres capas: el backend, que las hace cumplir; la PWA
(`esCuentaPropiaRestringida()` y `esCuentaDeMayorJerarquia()`, `Proyecto - PWA/src/frontend/src/config.ts:647-654`
y `:675-678`), que **omite** los botones; y Flet (`views/usuarios.py:200-207`), que los omite también y,
si la fila queda sin ninguno, dice por qué. Es [el frontend esconde, el backend rechaza](A-08-autorizacion.md#el-frontend-esconde-el-backend-rechaza)
con [botones omitidos](A-08-autorizacion.md#omitir-en-vez-de-deshabilitar). **Corrido:** la dueña que
se desactiva, la recepcionista que resetea a la dueña y la dueña que borra su propia cuenta reciben los
tres su 403.

**La fila propia del Dueño.** Las pantallas eximen al Dueño de la regla de la cuenta propia, para que
pueda editarse (`config.ts:652`; `views/usuarios.py:206-207`), y el backend no deja que nadie se
desactive, *"NI SIQUIERA EL DUEÑO"* (`usuarios.py:475-489`), porque *"un click dejó la instalación sin
acceso"*. Por eso las dos apps preguntan aparte si la fila es **literalmente** la de quien mira, y ahí no
dibujan el botón de estado (`UsuarioRow.tsx:75-77`; `views/usuarios.py:243-248`). Hasta el 2026-09-26 no
lo hacían: la fila del Dueño mostraba un "Desactivar" que siempre recibía 403
([nada muerto en pantalla](A-01-que-es-olimpos.md#nada-muerto-en-pantalla)).

### Cómo se ve una cuenta en la tabla

`_a_usuario_out()` (`usuarios.py:96-116`) arma cada fila con tres datos derivados:

- **Bloqueada** es la columna `bloqueado` **o** la traba temporal por intentos fallidos
  (`:97-102`), que vive en la memoria del proceso y no en ninguna tabla
  ([almacén que no es tabla](A-05-modelo-de-datos.md#almacén-que-no-es-tabla)). *"Si la traba no se
  viera, nadie sabría que hay algo que desbloquear."*
- **Los roles**, derivados de las tablas donde aparece la persona (`:111`;
  [derivación de roles](A-06-los-seis-roles.md#derivación-de-roles)).
- **El teléfono principal**, o el primero que haya (`:110`, con `_telefono_principal()` en
  `:119-125`), para ofrecer las credenciales por WhatsApp a quien no dejó mail.

Las dos apps reducen eso a un estado con prioridad —**Inactiva** antes que **Bloqueada** antes que
**Activa**— (`Proyecto - PWA/src/frontend/src/services/usuariosService.ts:63-69`,
`Flet/Proyecto/app/state.py:1337-1338`) y a un solo rol, el primero de la lista
(`usuariosService.ts:59-61`, `state.py:1336`).

**Una cuenta bloqueada sigue activa, y se puede apagar.** El estado "Bloqueada" tapa al "Activa", así
que las dos apps deciden el botón de estado con la bandera `activo` y no con el estado que muestran, y
ofrecen "Desbloquear" **aparte** (`UsuarioRow.tsx:120-153`; en Flet `views/usuarios.py:170`, `:234-257`
y `:564`, con la bandera que agrega `state.py:1341`). Importa con una cuenta atacada: los intentos
fallidos la traban y quien administra quiere apagarla. Hasta el 2026-09-26 el botón de estado ofrecía,
en esa fila, Desbloquear o Activar y nunca Desactivar: para apagarla había que destrabarla primero.

Dos detalles menores de la tabla. El primer rol de la lista no es *"el de mayor jerarquía"*, como dice
el comentario (`usuariosService.ts:53-58`): un socio contratado como entrenador sale como "Socio",
porque `roles_de_persona()` pone el de socio antes que los de empleado (`backend/models.py:1026-1039`).
Y Flet marca con *"Clave sin cambiar"* la cuenta que todavía tiene la temporal
(`views/usuarios.py:285-292`), y la PWA no.

---

## Los ocho procesos

### 38. Listar las cuentas de acceso

`GET /usuarios` · Dueño, Recepcionista

**Qué resuelve.** La tabla de cuentas, con el rol, el estado y las acciones de cada una.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/usuarios/UsuariosView.tsx` | 38-344 | `UsuariosView` (la carga, 66-80) |
| Fila PWA | `Proyecto - PWA/src/frontend/src/views/usuarios/UsuarioRow.tsx` | 54-170 | `UsuarioRow` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/usuariosService.ts` | 59-93 | `rolPrincipal()`, `estadoDe()`, `aUsuarioListado()`, `listarUsuarios()` |
| Esquema | `backend/schemas.py` | 1796-1820 | `UsuarioAdminOut` |
| Endpoint | `backend/routers/usuarios.py` | 204-219 | `listar_usuarios()` |
| Armado | `backend/routers/usuarios.py` | 82-154 | `CARGA_DE_ROLES`, `_a_usuario_out()` |
| Vista Flet | `Flet/Proyecto/app/views/usuarios.py` | 82-333 | `build()`, `_user_row()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1323-1346 | `get_usuarios()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 733-734 | `obtener_usuarios()` |

**Cómo funciona.** Una consulta por las cuentas, con la persona y sus roles en lote
(`usuarios.py:215-218`), ordenadas por id, y cada fila armada como se contó arriba. `CARGA_DE_ROLES`
es la lista de relaciones que se traen de una vez: sin ella, *"8 cuentas -> 45 consultas -> 2,88s"*
(`:72`), la cuenta que [el listado en lote](A-11-rendimiento.md#listado-en-lote) enseña a evitar. La
PWA filtra en memoria por nombre o usuario (`UsuariosView.tsx:84-91`).

**Qué escribe y qué lee.**

| Tabla | Atributos | Escribe o lee | Línea |
|---|---|---|---|
| `Usuario` | `id_usuario`, `id_persona`, `username`, `activo`, `bloqueado`, `debe_cambiar_password`, `ultimo_acceso` | lee | `usuarios.py:215`, `:103-115` |
| `Persona` | `dni`, `nombre`, `apellido`, `email` | lee | `:101`, `:107-109` |
| `Telefono` | `numero`, `principal` | lee | `:92`, `:110-110` |
| `Dueno`, `Socio`, `Empleado` y sus cuatro subtipos | la existencia de la fila | lee | `:83-88`, `:111` |

Coincide con la línea DFD, que no puede nombrar la traba en memoria: no es una tabla.

**Por qué está hecho así.** El rol y el bloqueo se derivan en vez de guardarse, por lo mismo que en
toda la aplicación; lo que agrega este listado es la carga anticipada, que el comentario de
`CARGA_DE_ROLES` pide repetir *"en CADA listado que llame a roles_de_persona"* (`:80-81`).

**Qué pasa cuando sale mal.** 403 para quien no tiene la sección: Entrenador, Nutricionista, Profesor y
Socio.

---

### 39. Crear la cuenta de acceso de una persona ya cargada

`POST /usuarios` · Dueño, Recepcionista

**Qué resuelve.** Darle acceso a alguien que ya está cargado y no tiene cuenta: un empleado cargado
sin acceso, o alguien a quien se le borró la suya (`usuarios.py:277-279`).

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/usuarios/UsuarioFormModal.tsx` | 35-230 | `UsuarioFormModal` (el envío, `handleSubmit`, 90-119) |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/usuariosService.ts` | 181-187 | `crearUsuario()` |
| Esquemas | `backend/schemas.py` | 1856-1859, 1862-1873 | `UsuarioCrearRequest`, `CredencialesResponse` |
| Endpoint | `backend/routers/usuarios.py` | 268-349 | `crear_cuenta()` |
| Credenciales | `backend/auth.py` | 90-143 | `generar_password_temporal()`, `generar_username()` |
| Envío por mail | `backend/notificaciones.py` | 89-164 | `enviar_credenciales()` |
| Vista Flet | `Flet/Proyecto/app/views/usuarios.py` | 335-437 | `_open_form()`, `_crear_cuenta()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1358-1373 | `crear_cuenta()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 741-742 | `crear_cuenta()` |

**Cómo funciona.** El pedido lleva sólo el id de la persona: *"los datos personales ya existen en
Persona y pedirlos de nuevo permitiría cargar dos versiones distintas de la misma persona"*
(`schemas.py:1857-1858`). El endpoint, en orden:

1. **La persona existe**, o 404 (`usuarios.py:285-290`).
2. **No tiene cuenta**, o 409 (`:292-296`).
3. **No es un empleado dado de baja**, o 409 (`:298-299`): su vuelta se da desde Personal.
4. **Tiene algún rol**, o 400: una cuenta sin roles *"no podría entrar a ninguna sección"* (`:301-310`).
5. **Si es dueña, la crea un dueño**, o 403: *"Crear la cuenta de un Dueño es, de hecho, crear un
   administrador"* (`:312-318`).
6. **Usuario y clave los genera el sistema** (`:320-324`), y la cuenta nace marcada para cambiarla
   (`:326-332`). Una confirmación (`:333`).
7. **El mail, después de confirmar** (`:335-337`), para no mandar credenciales de una cuenta que no
   llegó a existir.

Las dos apps muestran entonces las credenciales en el **panel de entrega**, con el mail y el teléfono
de la persona elegida para mandarlas por mail o WhatsApp con el mensaje ya escrito: la PWA guarda las
personas completas y no sólo las opciones del selector (`UsuarioFormModal.tsx:43-50`, `:105-109` y
`:121-135`), y Flet le pasa los dos datos al diálogo (`views/usuarios.py:430-437`). El teléfono viene
en la lista de candidatos (proceso 40).

**Qué escribe y qué lee.**

| Tabla | Atributos | Escribe o lee | Línea |
|---|---|---|---|
| `Persona` | `nombre`, `apellido`, `email` | lee | `usuarios.py:285`, `:323`, `:337` |
| `Usuario` | la cuenta de la persona y `username` (para no repetirlo) | lee | `:292`, `:320-321` |
| `Empleado` | `activo` | lee | `:298` |
| `Dueno`, `Socio`, `Empleado` y sus cuatro subtipos | la existencia de la fila | lee | `:301` |
| `Usuario` | `id_persona`, `username`, `password_hash`, `debe_cambiar_password`, `activo` | escribe | `:326-332` |

Coincide con la línea DFD.

**Por qué está hecho así.** No recibe contraseña porque *"que un administrador elija la contraseña de
otro sería peor — la conocería para siempre"* (`:281-283`), el mismo razonamiento del alta
([contraseña temporal](A-07-autenticacion.md#contraseña-temporal-y-primer-ingreso)).

El paso 3 existe porque `roles_de_persona()` mira que **exista** la fila del subtipo, no que el
empleado siga activo (`backend/models.py:1026-1039`): un entrenador dado de baja sigue siendo
`entrenador` para la derivación. Por eso el router lo pregunta aparte, en una sola función que usan
los tres caminos que dan acceso —este, la lista de candidatos y la reactivación—
(`_empleado_dado_de_baja()` y `_rechazar_empleado_dado_de_baja()`, `usuarios.py:128-154`). La vuelta
se da desde Personal, porque *"el acceso de un empleado se justifica en el puesto"*
([el acople total](A-10-bajas-logicas.md#en-los-empleados-el-acople-es-total)).

Hasta el 2026-09-26 sólo la reactivación preguntaba. **Corrido** antes del arreglo, por HTTP: un
entrenador dado de baja y sin cuenta aparecía entre los candidatos, la recepcionista le creaba la
cuenta, y él iniciaba sesión con `roles: ["entrenador"]` y listaba a todos los socios. **Corrido**
después: no aparece, crearle la cuenta da 409, y reactivado desde Personal vuelve a la lista y la cuenta
se le crea. Con un socio dado de baja no se hace nada: una baja voluntaria le deja la cuenta viva a
propósito, así que su caso depende del tipo de baja y queda como decisión del dueño (proceso 45).

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| La persona no existe | 404 | *"No existe una persona con ese id."* | `usuarios.py:285-290` |
| Ya tiene cuenta | 409 | *"{nombre} ya tiene una cuenta ('{usuario}')."* | `usuarios.py:292-296` |
| Es un empleado dado de baja | 409 | *"{nombre} está dado de baja como empleado. Reactivalo desde Personal…"* | `usuarios.py:146-154`, `:298-299` |
| No tiene ningún rol | 400 | *"{nombre} no tiene ningún perfil que habilite el acceso…"* | `usuarios.py:301-310` |
| Es dueña y quien pide no | 403 | *"Solo un dueño puede crear la cuenta de otro dueño."* | `usuarios.py:314-318` |

La línea DFD nombra los cinco.

---

### 40. Listar las personas sin cuenta de acceso

`GET /usuarios/personas-sin-cuenta` · Dueño, Recepcionista

**Qué resuelve.** Las opciones del selector "Persona" al crear una cuenta.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/usuarios/UsuarioFormModal.tsx` | 55-88 | `listarPersonasSinUsuario` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/usuariosService.ts` | 117-139 | `listarPersonasSinUsuario()` |
| Esquema | `backend/schemas.py` | 1823-1835 | `PersonaSinCuentaOut` |
| Endpoint | `backend/routers/usuarios.py` | 222-261 | `listar_personas_sin_cuenta()` |
| Vista Flet | `Flet/Proyecto/app/views/usuarios.py` | 335-417 | `_open_form()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1348-1356 | `get_personas_sin_cuenta()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 737-738 | `obtener_personas_sin_cuenta()` |

**Cómo funciona.** Las personas sin `Usuario`, con sus roles en lote (`usuarios.py:241-244`), menos las
que no tienen ninguno y las de un empleado dado de baja (`:249-250`), cada una con su teléfono
principal (`:256-258`). La PWA muestra cada una con su rol principal, *"para que el staff
no cree una cuenta sin saber con qué permisos va a quedar"* (`UsuarioFormModal.tsx:62-65`), y
preselecciona la primera (`:72`); Flet muestra el DNI y todos los roles. Si no hay nadie, las dos
explican que las cuentas nacen con el alta en Socios o Personal (`UsuarioFormModal.tsx:165-173`,
`views/usuarios.py:355-365`).

**Qué escribe y qué lee.** Lee `Persona` (`id_persona`, `dni`, `nombre`, `apellido`, `email`), sus
`Telefono`, la existencia de su `Usuario`, las tablas de rol y `Empleado.activo`. Coincide con la línea
DFD.

**Por qué está hecho así.** Va declarada antes que `/{id_usuario}` porque FastAPI prueba las rutas en
orden y leería `personas-sin-cuenta` como un id (`:202-205`).

Y deja afuera al empleado dado de baja por lo mismo que el selector de entrenadores recorta
(B-03, proceso 31): *"ofrecerlo sería ofrecer lo que después falla"* (`:230-234`).

**Qué pasa cuando sale mal.** 403 para quien no tiene la sección.

---

### 41. Editar el usuario y el email de una cuenta

`PUT /usuarios/{id_usuario}` · Dueño, Recepcionista

**Qué resuelve.** Corregir el nombre de usuario o el mail de contacto de una cuenta.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/usuarios/UsuarioFormModal.tsx` | 35-230 | `UsuarioFormModal` (la edición, 94-97 y 196-200) |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/usuariosService.ts` | 196-205 | `actualizarUsuario()` |
| Esquema | `backend/schemas.py` | 1838-1847 | `UsuarioEditarRequest` |
| Endpoint | `backend/routers/usuarios.py` | 576-649 | `editar_usuario()` |
| Vista Flet | `Flet/Proyecto/app/views/usuarios.py` | 439-482 | `_editar()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 587-589 | `editar_usuario()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 602-603 | `editar_usuario()` |

**Cómo funciona.** El endpoint, en orden:

1. **La cuenta existe**, o 404 (`usuarios.py:598`, `_buscar_usuario()` en `:157-164`).
2. **Las dos reglas de fila** (`:599-600`).
3. **El usuario, recortado y en minúsculas, no queda vacío**, o 400 (`:602-608`).
4. **No lo usa otra cuenta**, o 409 (`:612-617`), antes de que lo diga el `UNIQUE` de la base con un
   mensaje incomprensible.
5. **El email no es de otra persona**, o 409 (`:619-626`).
6. **Un empleado no queda sin mail ni teléfono**, o 400 (`:628-635`): la misma regla que su propio
   formulario.
7. **La traba por intentos se muda con el nombre**, si cambia (`:637-642`).
8. **Se escriben los dos** (`:644-645`) y se confirma (`:647`).

**Qué escribe y qué lee.** Lee la cuenta, su persona y los usernames y mails de las demás; escribe
`Usuario.username` y `Persona.email`. Coincide con la línea DFD.

**Por qué está hecho así.** No cambia el rol, porque *"se deriva de las tablas donde la persona
aparece (…) así que 'cambiarlo' acá sería mentir"*, ni la contraseña, porque para eso está el reseteo
(`usuarios.py:586-593`).

**El nombre de usuario, en minúsculas.** Se guarda así (`:602-605`) y el login lo compara así
(`routers/auth_router.py:143`, y lo mismo el cambio de clave, `:307`), como los usuarios que genera el
sistema y el del dueño inicial (`backend/seeder.py:46-47`). Hasta el 2026-09-26 se guardaba tal cual y
el login lo comparaba tal cual, mientras Flet lo mandaba en minúsculas
([B-01, proceso 3](B-01-acceso-y-sesion.md#3-iniciar-sesión)): **corrido** antes del arreglo, una
cuenta renombrada `Mario.DJ` entraba por la PWA y daba 401 por Flet. **Corrido** después: se guarda
`mario.dj` y entra escrita de cualquier forma. La traba por intentos fallidos cuelga del nombre de
usuario, así que renombrar la muda con la cuenta (`limite_intentos.renombrar()`,
`backend/limite_intentos.py:86-95`); **corrido**: una cuenta trabada, renombrada, sigue trabada con el
nombre nuevo hasta que alguien la desbloquea.

**El mail, con el mismo validador que el resto.** Todos los formularios que cargan un mail tienen dos
controles: el tipo `EmailStr` y un validador propio, `_email_valido()` (`schemas.py:74-100`), que exige
una terminación de al menos dos letras y **pasa el mail a minúsculas**, para que *"Juan@Gmail.com"* y
*"juan@gmail.com"* no entren como dos personas. A este esquema le faltaba el segundo, y lo tiene desde
el 2026-09-26 (`schemas.py:1849-1853`): antes aceptaba *"juan@casa.c"* y guardaba `Juan@gmail.com` con
mayúscula, y como el choque del paso 5 y el `UNIQUE` de la base comparan el texto exacto, dos personas
podían terminar con la misma casilla escrita distinto.

El validador corre **antes** que `EmailStr` (`mode="before"`, en los seis esquemas), y el porqué es el
idioma del error. En el orden por defecto el tipo del campo se valida antes que los validadores que se
le agregan ([esquema de entrada y salida](A0-10-python-del-lado-del-servidor.md#esquema-de-entrada-y-salida-y-el-422)),
así que un mail sin punto lo rechazaba `EmailStr`, en inglés —*"value is not a valid email address: The
part after the @-sign is not valid. It should have a period."*—, en **todos** los formularios, y el
mensaje propio sólo salía con una terminación de una letra. Corriendo primero, sale siempre en
castellano. **Corrido**, con los esquemas: *"juan@casa"* y *"juan@casa.c"* dan *"El email tiene que
tener un dominio completo, como nombre@gmail.com."*, *"Juan@Gmail.com"* queda `juan@gmail.com`, y el
campo vacío queda sin mail.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| La cuenta no existe | 404 | *"La cuenta indicada no existe."* | `usuarios.py:157-164` |
| Es la propia, y quien pide no es dueño | 403 | *"No podés modificar el estado de tu propia cuenta."* | `usuarios.py:184-197` |
| Es de un dueño, y quien pide no | 403 | *"Solo un dueño puede operar sobre la cuenta de un dueño."* | `usuarios.py:167-181` |
| El usuario queda vacío | 400 | *"El nombre de usuario es obligatorio."* | `usuarios.py:602-608` |
| El usuario ya existe | 409 | *"El usuario '{usuario}' ya está en uso."* | `usuarios.py:612-617` |
| El email es de otra persona | 409 | *"Ese email ya está registrado para otra persona."* | `usuarios.py:619-626` |
| Un empleado quedaría sin mail ni teléfono | 400 | *"Cargá un email o un teléfono: hace falta para contactarlo."* | `usuarios.py:628-635` |
| Email sin dominio completo | 422 | *"El email tiene que tener un dominio completo, como nombre@gmail.com."* | `schemas.py:74-100` |
| Usuario de más de 50 caracteres | 422 | el de Pydantic | `schemas.py:1846` |

La línea DFD nombra los siete primeros.

---

### 42. Borrar una cuenta de acceso

`DELETE /usuarios/{id_usuario}` · Dueño, Recepcionista

**Qué resuelve.** Sacar una cuenta que no tendría que existir, sin tocar a la persona.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/usuarios/UsuariosView.tsx` | 146-164 | `pedirBorrado` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/usuariosService.ts` | 214-217 | `borrarCuenta()` |
| Endpoint | `backend/routers/usuarios.py` | 520-573 | `borrar_cuenta()` |
| Vista Flet | `Flet/Proyecto/app/views/usuarios.py` | 532-546 | `_confirmar_borrado()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1390-1391 | `borrar_cuenta()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 753-754 | `borrar_cuenta()` |

**Cómo funciona.** El concepto —la única fila principal que el sistema borra de verdad, la clave
foránea que se pone en `NULL` a mano y las reglas que no dejan al sistema sin dueño— está entero en
[borrado real de la cuenta](A-10-bajas-logicas.md#borrado-real-de-la-cuenta). El recorrido, con sus
líneas: la jerarquía (`usuarios.py:548`), la propia (`:550-552`), la última de un dueño (`:554-561`),
los fichajes manuales que pasan a `NULL` (`:564-566`), la traba en memoria que se limpia (`:567-568`) y
el borrado (`:569-570`). Las dos apps confirman antes con el mismo texto, que avisa que *"No se puede
deshacer"* (`UsuariosView.tsx:148-152`, `views/usuarios.py:541-546`).

**Qué escribe y qué lee.** Escribe `Asistencia.id_registrado_por` y borra el `Usuario`; lee la cuenta,
su persona, sus roles y, si es de un dueño, las demás cuentas de dueño. Coincide con la línea DFD.

**Por qué está hecho así.** Ver [borrado real de la cuenta](A-10-bajas-logicas.md#borrado-real-de-la-cuenta).
Borrar la cuenta de un empleado dado de baja no lo devuelve a la lista de candidatas: el proceso 40 lo
deja afuera y el 39 no le crea otra (antes del 2026-09-26, ésa era la puerta de vuelta).

Un detalle de la regla de la última cuenta: para contar cuántos dueños quedan, recorre **todas** las
cuentas y deriva los roles de cada una sin carga anticipada (`:535-536`). Corre sólo cuando la cuenta a
borrar es de un dueño, así que el costo casi nunca se paga; pero es el
[N+1](A0-09-el-orm.md#n1) que el resto del archivo evita.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| La cuenta no existe | 404 | *"La cuenta indicada no existe."* | `usuarios.py:157-164` |
| Es de un dueño, y quien pide no | 403 | *"Solo un dueño puede operar sobre la cuenta de un dueño."* | `usuarios.py:548` |
| Es la propia, de cualquiera | 403 | *"No podés borrar tu propia cuenta."* | `usuarios.py:550-552` |
| Es la última cuenta de un dueño | 409 | *"Es la única cuenta de un dueño: borrarla dejaría el sistema sin administrador."* | `usuarios.py:554-561` |

La línea DFD nombra los cuatro.

---

### 43. Desbloquear una cuenta sin tocar su contraseña

`POST /usuarios/{id_usuario}/desbloquear` · Dueño, Recepcionista

**Qué resuelve.** Destrabar a quien se equivocó de clave cinco veces pero se la acuerda.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/usuarios/UsuariosView.tsx` | 166-176 | `desbloquear` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/usuariosService.ts` | 226-229 | `desbloquearUsuario()` |
| Endpoint | `backend/routers/usuarios.py` | 409-441 | `desbloquear()` |
| Traba en memoria | `backend/limite_intentos.py` | 68-83 | `cuenta_trabada()`, `destrabar()` |
| Vista Flet | `Flet/Proyecto/app/views/usuarios.py` | 548-553 | `_desbloquear()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1387-1388 | `desbloquear_usuario()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 749-750 | `desbloquear_usuario()` |

**Cómo funciona.** La jerarquía (`usuarios.py:423`); si la cuenta no tiene ni la columna `bloqueado`,
ni intentos acumulados, ni traba en memoria, 400 (`:425-431`); si tiene alguna, se limpian las tres
(`:433-438`), se confirma y se devuelve la fila. Las dos apps ofrecen el botón sólo sobre una cuenta
bloqueada (`UsuarioRow.tsx:143-143`, `views/usuarios.py:236-240`).

**Qué escribe y qué lee.** Escribe `Usuario.bloqueado` y `Usuario.intentos_fallidos`, y borra la traba
del diccionario en memoria; lee la cuenta y su persona. Coincide con la línea DFD.

**Por qué está hecho así.** Es distinto de resetear: *"acá la persona sí se acuerda su clave y el
bloqueo fue un accidente (tecleó mal, tenía el Bloq Mayús). Cambiarle la contraseña en ese caso sería
molestarla al pedo"* (`usuarios.py:418-420`). Qué traba el login, cuánto dura y por qué responde igual
que una clave equivocada está en
[freno de intentos](A-07-autenticacion.md#freno-de-intentos-y-respuesta-indistinguible).

`limite_intentos` se importa **adentro** de las funciones, y dos veces dentro de ésta (`:425`, `:437`).
El módulo no importa nada del backend (`backend/limite_intentos.py:34-35`), así que no hay un ciclo que
lo justifique: es costumbre, no necesidad.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| La cuenta no existe | 404 | *"La cuenta indicada no existe."* | `usuarios.py:157-164` |
| Es de un dueño, y quien pide no | 403 | *"Solo un dueño puede operar sobre la cuenta de un dueño."* | `usuarios.py:167-181` |
| No estaba bloqueada | 400 | *"Esa cuenta no está bloqueada."* | `usuarios.py:425-431` |

La línea DFD nombra los tres. **Corrido**, el tercero.

---

### 44. Resetear la contraseña de una cuenta

`POST /usuarios/{id_usuario}/resetear-password` · Dueño, Recepcionista

**Qué resuelve.** El olvido: una clave temporal nueva, que la persona cambia al entrar.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/usuarios/UsuariosView.tsx` | 178-205, 329-341 | `pedirReseteo`, `PanelCredenciales` |
| Entrega de la clave | `Proyecto - PWA/src/frontend/src/components/PanelCredenciales.tsx` | 48-151 | `PanelCredenciales` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/usuariosService.ts` | 252-264 | `resetearPassword()` |
| Endpoint | `backend/routers/usuarios.py` | 356-406 | `resetear_password()` |
| Vista Flet | `Flet/Proyecto/app/views/usuarios.py` | 484-530, 571-639 | `_reset_password()`, `_confirmar_reset()`, `_mostrar_credenciales()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1375-1385 | `resetear_password_usuario()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 745-746 | `resetear_password()` |

**Cómo funciona.** Sólo la jerarquía, a propósito: *"Sin _validar_no_es_propia: resetearse la propia
contraseña es inofensivo"* (`usuarios.py:377-378`). Después, una clave temporal nueva (`:380-381`), la
marca de cambio obligatorio (`:382`), la cuenta destrabada en la columna, el contador y la memoria
(`:383-388`), la confirmación (`:389`) y el mail (`:391-394`). Las dos apps confirman antes y muestran
la clave en el panel de entrega, con el mail y el teléfono de la fila, porque el endpoint devuelve las
credenciales pero no a dónde mandarlas (`UsuariosView.tsx:58-61`, `views/usuarios.py:526-530`).

**Qué escribe y qué lee.** Escribe `Usuario.password_hash`, `debe_cambiar_password`, `bloqueado` e
`intentos_fallidos`; lee la cuenta, su persona y sus roles. Coincide con la línea DFD.

**Por qué está hecho así.** Es el mismo mecanismo que el alta y que el primer ingreso del dueño:
*"Un solo camino para los tres casos (…) es lo que hace que no haya un segundo flujo de contraseñas que
mantener"* (`usuarios.py:366-370`;
[contraseña temporal](A-07-autenticacion.md#contraseña-temporal-y-primer-ingreso)). Destraba de paso
porque quien llegó a los cinco intentos *"casi siempre, porque no se acordaba la contraseña"*
(`:372-374`). Y es el botón que la regla de jerarquía existe para cerrar: el único de la sección que le
**muestra** una clave a quien lo aprieta. Resetearse a uno mismo corta la sesión en el acto
([la bandera que rechaza el token](A-07-autenticacion.md#la-bandera-que-rechaza-el-token)); si el único
dueño lo hace y pierde la temporal, nadie puede rescatarlo desde la app.

El comentario de la confirmación en la PWA justifica la clave temporal con que *"acá no hay backend de
email al que mandarle nada"* (`UsuariosView.tsx:182-184`). Lo hay: el mismo endpoint manda el mail
cuando hay servidor de correo configurado (`usuarios.py:391-394`).

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| La cuenta no existe | 404 | *"La cuenta indicada no existe."* | `usuarios.py:157-164` |
| Es de un dueño, y quien pide no | 403 | *"Solo un dueño puede operar sobre la cuenta de un dueño."* | `usuarios.py:167-181` |

La línea DFD nombra los dos. **Corrido**, el segundo: la recepcionista que resetea a la dueña.

---

### 45. Activar o desactivar una cuenta de acceso

`POST /usuarios/{id_usuario}/toggle-estado` · Dueño, Recepcionista

**Qué resuelve.** Cortarle o devolverle el acceso a alguien sin tocar su ficha.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/usuarios/UsuariosView.tsx` | 109-142 | `pedirBaja`, `activar` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/usuariosService.ts` | 274-296 | `alternarEstadoUsuario()`, `darDeBajaUsuario`, `activarUsuario` |
| Endpoint | `backend/routers/usuarios.py` | 444-517 | `alternar_estado()` |
| Vista Flet | `Flet/Proyecto/app/views/usuarios.py` | 555-569 | `_cambiar_estado()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1393-1397 | `cambiar_estado_usuario()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 757-761 | `cambiar_estado_usuario()` |

**Cómo funciona.** El endpoint, en orden:

1. **Las dos reglas de fila** (`usuarios.py:472-473`), y además que **nadie** se desactive a sí mismo,
   tampoco el Dueño (`:484-489`).
2. **El destino**: el que vino en `?activo=`, o el contrario al actual si no vino (`:491`).
3. **No se reactiva la cuenta de un empleado dado de baja**, o 409: eso se hace desde Personal, *"que
   devuelve el puesto y el acceso juntos"* (`:505-506`).
4. **Se escribe el estado**, y si es para activar, se destraba del todo (`:508-514`): *"Reactivar y
   dejarla bloqueada sería reactivarla a medias."*

Desactivar pide confirmación y activar no, por la regla de toda la app: lo reversible no se pregunta
(`UsuariosView.tsx:130-131`).

**Qué escribe y qué lee.** Escribe `Usuario.activo`, `bloqueado` e `intentos_fallidos`; lee la cuenta,
su persona, sus roles y `Empleado.activo`. Coincide con la línea DFD.

**Por qué está hecho así.** Desactivar es *"la ÚNICA forma de revocar una sesión en el acto"*: el token
no se puede invalidar antes de que venza, pero la sesión relee la cuenta en cada pedido
(`usuarios.py:454-458`; [caducidad y revocación](A0-12-sesiones-y-autenticacion.md#caducidad-y-revocación)).
Por eso el destino viaja explícito: con un "invertí lo que haya", dos personas que desactivan a la vez
la misma cuenta comprometida la dejan **activa**, porque el segundo pedido la reactiva (`:464-469`). Con
el destino, el pedido se puede repetir sin cambiar el resultado
([idempotencia](A0-03-http.md#método-http-e-idempotencia)); las dos apps lo mandan siempre
(`usuariosService.ts:285-296`, `api_client.py:758-761`). Y la cuenta y la ficha son
[dos banderas](A-10-bajas-logicas.md#las-dos-banderas): desactivar la cuenta de un socio no lo da de
baja.

**Nota marcada · la guarda de la reactivación mira al empleado, no al socio.** El paso 3 frena la
cuenta de un empleado dado de baja (`usuarios.py:505-506`); la de un socio dado de baja por mora o por
decisión administrativa —que la baja apagó— se puede volver a prender desde acá sin reactivar al socio,
y lo mismo crearle una nueva (proceso 39). No se tocó porque para el socio depende del tipo de baja: la
voluntaria le deja la cuenta viva a propósito
([tipo de baja](A-10-bajas-logicas.md#tipo-de-baja-y-el-acople-de-la-cuenta)), y la de mora o
administrativa, no. Es una decisión del dueño. Leído, no corrido.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| La cuenta no existe | 404 | *"La cuenta indicada no existe."* | `usuarios.py:157-164` |
| Es la propia, y quien pide no es dueño | 403 | *"No podés modificar el estado de tu propia cuenta."* | `usuarios.py:184-197` |
| Es la propia, y quien pide es el Dueño | 403 | *"No podés desactivar tu propia cuenta: quedarías afuera del sistema sin poder volver a entrar."* | `usuarios.py:484-489` |
| Es de un dueño, y quien pide no | 403 | *"Solo un dueño puede operar sobre la cuenta de un dueño."* | `usuarios.py:167-181` |
| Reactivar a un empleado dado de baja | 409 | *"{nombre} está dado de baja como empleado. Reactivalo desde Personal…"* | `usuarios.py:505-506` |
| `activo` que no es booleano | 422 | el de Pydantic | `usuarios.py:447` |

La línea DFD nombra los cinco primeros. **Corrido**, el tercero y el quinto.

---

## Con qué se conecta

- **Es la misma idea que…** [las dos banderas](A-10-bajas-logicas.md#las-dos-banderas): el acceso de
  un empleado se justifica en el puesto, así que ningún camino de Usuarios —ni reactivar, ni crear una
  cuenta nueva— se lo devuelve a quien Personal dio de baja; la vuelta se da desde Personal.
- **Existe por culpa de…** [la derivación de roles](A-06-los-seis-roles.md#derivación-de-roles): la
  derivación mira que exista la fila del subtipo, no que el empleado siga activo, y por eso cada camino
  que da acceso tiene que preguntarlo aparte.
- **Es la misma idea que…** [el frontend esconde, el backend rechaza](A-08-autorizacion.md#el-frontend-esconde-el-backend-rechaza):
  las reglas de fila viven en las tres capas y tienen que decir lo mismo; cuando la pantalla eximía al
  Dueño de no desactivarse, le ofrecía un botón que siempre recibía 403.
- **Es la misma idea que…** [idempotencia](A0-03-http.md#método-http-e-idempotencia): activar o
  desactivar manda el estado destino, y dos desactivaciones seguidas dejan la cuenta desactivada en vez
  de volver a prenderla.
- **Existe por culpa de…** [el esquema de entrada y salida](A0-10-python-del-lado-del-servidor.md#esquema-de-entrada-y-salida-y-el-422):
  el validador propio del mail corre antes que `EmailStr`, porque en el orden por defecto el tipo
  contestaba primero, y en inglés.
