# B-02 · Socios

*Procesos 6 a 28. Piso del capítulo: la línea que implementa cada paso, en las tres capas.*

Es la sección más grande del sistema después del portal: veintitrés procesos sobre la ficha del
socio. Se agrupan en seis temas, aunque `PROCESOS-LOGICOS-REQUERIDOS.md` los numera mezclados y este
capítulo respeta esa numeración:

| Tema | Procesos |
|---|---|
| La ficha: listar, dar de alta, consultar y editar | 6, 7, 10, 11 |
| La baja: darla, anularla y revertirla | 12, 13, 24 |
| Los contactos de emergencia | 14 a 17 |
| Los teléfonos | 25 a 28 |
| Los entrenadores a cargo | 8, 9, 18, 19 |
| El historial médico | 20 a 23 |

El porqué de casi todo ya está explicado en la Parte A: el estado del socio en
[A-09](A-09-estados-derivados.md), la grilla en lote en
[A-11](A-11-rendimiento.md#listado-en-lote), las bajas en [A-10](A-10-bajas-logicas.md), las
credenciales del alta en [A-07](A-07-autenticacion.md#contraseña-temporal-y-primer-ingreso). Este
capítulo sigue el código de cada proceso, cruza las tablas contra la línea DFD y registra cada
rechazo. Lo que se repite entre procesos se explica una vez, en "Piezas comunes", y cada proceso
remite ahí.

---

## Piezas comunes

### Quién puede qué en esta sección

Los procesos de Socios usan cuatro barreras distintas, y la diferencia entre ellas explica casi todas
las entidades de las líneas DFD:

| Barrera | Quién la tiene | La usan |
|---|---|---|
| Sección `SOCIOS` en lectura | Dueño, Recepcionista, Entrenador, Nutricionista | todo lo que sólo lee: 6, 9, 10, 14, 18, 25 |
| Acción `ALTA_BAJA_SOCIOS` | Dueño, Recepcionista | todo lo que escribe la ficha: 7, 11, 12, 13, 15-17, 24, 26-28 |
| Acción `GESTION_RUTINAS` | Dueño, Recepcionista, Entrenador | los entrenadores a cargo: 8, 19 |
| Acción `VER_HISTORIAL_MEDICO` | Dueño, Entrenador, Nutricionista | el historial médico: 20 a 23 |

Cómo se evalúan una sección y una acción está en
[sección con nivel y acción suelta](A-08-autorizacion.md#sección-con-nivel-y-acción-suelta). La
cuarta fila es la única de todo el sistema donde el Recepcionista queda por debajo del Entrenador, y
por eso el historial médico vive en su propio router (`backend/routers/patologias.py:7-27`) en vez de
mezclado con el resto de `/socios`: cada endpoint llevaría un permiso distinto del resto del archivo.
En la grilla, el botón del historial se **omite** para quien no tiene la acción
([omitir en vez de deshabilitar](A-08-autorizacion.md#omitir-en-vez-de-deshabilitar)).

### V-10: el Entrenador y el Nutricionista ven a todos los socios

El permiso de lectura es **por sección**, no por asignación. Un Entrenador ve la grilla completa, la
ficha de cualquier socio y —con `VER_HISTORIAL_MEDICO`— el historial médico de cualquiera, sea o no
alumno suyo. `docs/vulnerabilidades a arreglar.md` lo registra como V-10 y lo verifica: una
entrenadora lee la patología de un socio que no entrena.

Es una decisión y no un descuido, y el código dice por qué en la primera línea donde aparece:
`listar_socios()` pide lectura *"porque un Entrenador necesita ver a quién le asigna una rutina"*
(`backend/routers/socios.py:293-295`). La asignación empieza siempre por alguien que busca a una
persona que **todavía no** es suya: un Entrenador que toma un cliente nuevo (proceso 19) tiene que
poder encontrarlo, y un filtro "sólo los míos" haría imposible el primer paso. El documento de
vulnerabilidades deja anotado el costo —dato médico y DNI al alcance de cualquier entrenador— y el
momento de revisarlo: a escala, con varias sedes y decenas de profesionales, conviene acotar por
asignación.

### La grilla: `SocioOut` y sus dos armadores

Todo proceso que devuelve un socio devuelve un `SocioOut` (`backend/schemas.py:426-485`), la fila de
la grilla con su estado, su plan, su vencimiento, su baja programada y el aviso de cuenta sin acceso
ya resueltos. Hay dos funciones que lo arman, y tienen que dar lo mismo:

- `_listar_socios_en_lote()` (`socios.py:170-256`) para las grillas, con un número fijo de consultas
  sin importar cuántas filas haya ([listado en lote](A-11-rendimiento.md#listado-en-lote); su
  docstring dice "cinco" y son ocho, [nota del conteo](A-11-rendimiento.md#nota-marcada--el-conteo-quedó-viejo)).
- `_a_socio_out()` (`socios.py:259-285`) para un socio solo —el alta, la edición, la baja—, con cuatro
  consultas más la de la baja pendiente.

Las dos derivan el estado con la misma función, `_estado_socio()`
([los seis estados](A-09-estados-derivados.md#los-seis-estados-del-socio-y-su-precedencia)), y las dos
mandan `cuenta_activa`, la bandera de la cuenta de acceso que la grilla muestra como "Sin acceso a
la app" ([las dos banderas](A-10-bajas-logicas.md#las-dos-banderas)). Los tres campos `emergencia_*`
son el contacto **principal** aplanado para la grilla (`_datos_personales()`, `socios.py:150-167`),
no la lista entera.

### Las listas con un principal: teléfonos y contactos de emergencia

Los procesos 14 a 17 y 25 a 28 son el mismo patrón aplicado a dos tablas 1:N, `Telefono` y
`Contacto_Emergencia`. Las reglas, idénticas en las dos:

1. **Uno es el principal**, el que sale en la grilla y en el botón de llamar. La base no lo garantiza
   —`principal` es una columna con `DEFAULT false` y ningún índice la protege (`db/schema.sql:109` y
   `:122`)—, así que lo garantiza el código: antes de marcar uno se desmarcan todos
   (`_desmarcar_principales()`, `socios.py:783-792`; `_desmarcar_emergencias_principales()`,
   `:1176-1181`).
2. **El primero que se carga es principal** aunque no se lo pida (`:825` y `:1206`).
3. **El principal no se desmarca a secas**: pedirlo se ignora, porque dejaría la ficha sin ninguno;
   para cambiarlo se marca el otro (`:851-855` y `:1224-1227`).
4. **Al borrar el principal asciende el más viejo** (`:886-891` y `:1245-1250`).
5. **El mismo número dos veces se rechaza**, comparando sólo los dígitos: `"341 555-1234"` y
   `"3415551234"` son el mismo teléfono (`_digitos()`, `:762-769`).
6. **Una fila de otra persona responde 404, no 403** (`_telefono_de()`, `:772-780`;
   `_emergencia_de()`, `:1164-1173`): que exista un teléfono con ese id en otra ficha no es información
   de quien mira ésta ([aislamiento de lo propio](A-08-autorizacion.md#aislamiento-de-lo-propio)).

Las dos filas se **borran de verdad**, a diferencia de casi todo el sistema: un número equivocado no es
historia que preservar, es un dato falso que hace perder una llamada (`:875-877` y `:1236-1237`).

Y una observación que vale para las dos: la regla 5 sólo se aplica al **agregar**. Editar un número no
controla que choque con otro de la ficha. No se alcanza desde ninguna pantalla, porque las dos apps
usan el `PUT` únicamente para marcar el principal y reenvían el número que ya estaba
(`TelefonosModal.tsx:99-108`, `EmergenciaModal.tsx:114-120`, `state.py:1163-1174`).

---

## Los veintitrés procesos

### 6. Listar socios y aplicar las bajas programadas vencidas

`GET /socios` · Dueño, Recepcionista, Entrenador, Nutricionista

**Qué resuelve.** La grilla de socios del personal, con el estado de cada uno. De paso, aplica las
bajas programadas cuya fecha ya llegó.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/socios/SociosView.tsx` | 69-412 | `SociosView` (la carga, 120-134) |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/sociosService.ts` | 140-143 | `listarSocios()` |
| Esquemas | `backend/schemas.py` | 426-485 | `SocioOut` |
| Endpoint | `backend/routers/socios.py` | 288-299 | `listar_socios()` |
| Armado | `backend/routers/socios.py` | 170-256 | `_listar_socios_en_lote()` |
| Regla de negocio | `backend/bajas.py` | 128-148 | `aplicar_bajas_vencidas()` |
| Vista Flet | `Flet/Proyecto/app/views/socios.py` | 38-116 | `build()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 385-436 | `get_socios()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 420-421 | `obtener_socios()` |

**Cómo funciona.** El endpoint hace dos cosas (`socios.py:298-299`): aplica las bajas vencidas y
devuelve la grilla, del socio más nuevo al más viejo. `aplicar_bajas_vencidas()` busca las bajas
pendientes con fecha hasta hoy (`bajas.py:130-132`), las marca como aplicadas, deja de baja a cada
socio que siga activo —apagándole la cuenta si la baja no es voluntaria— (`:138-143`), promueve la lista
de espera de los turnos que quedaron libres (`:145-146`) y confirma (`:147`). Si no había ninguna,
no escribe nada (`:133-134`). Después, `_listar_socios_en_lote()` arma la grilla
([la grilla](#la-grilla-socioout-y-sus-dos-armadores)).

**Qué escribe y qué lee.** Las escrituras son todas de la baja que se aplica: `Baja.pendiente`
(`bajas.py:140`), `Socio.activo`, `Membresia.estado`, `Reserva.estado` y `Reserva.fecha_cancelacion`,
y `Usuario.activo` (`aplicar_baja()`, `bajas.py:103-124`), más el ascenso en la lista de espera, que
vuelve a escribir `Reserva.estado`. Las lecturas son las del armado en lote: `Socio`, `Persona` con
sus `Telefono`, su `Usuario` y sus `Contacto_Emergencia`, `Membresia` con su `Tipo_Membresia`, y las
`Baja` pendientes. Coincide con la línea DFD.

**Por qué está hecho así.** No hay tareas programadas en el sistema, así que una baja que llega a su
fecha se aplica en uno de tres momentos: al arrancar el backend, una vez por día desde el latido, y al
leer la grilla ([cuándo se aplica una baja programada](A-10-bajas-logicas.md#cuándo-se-aplica-una-baja-programada-sin-tarea-programada)).
Aplicarla al leer garantiza que nadie vea como activo a alguien que ya dejó de serlo.

Eso convierte a este `GET` en **el único que escribe** en la sección, y el middleware de CSRF
descansa en la regla contraria: *"si algún día un GET escribe en la base, este middleware deja de
protegerlo"* (`backend/csrf.py:51-54`). Acá no hay riesgo, y conviene decir por qué: lo que se escribe
no depende de nada que traiga el pedido, sólo de la fecha. Un sitio ajeno que disparara este `GET`
aplicaría las mismas bajas que se iban a aplicar igual al día siguiente.

**Qué pasa cuando sale mal.** El único rechazo es de permisos: 403 para Profesor y Socio, que no
tienen la sección.

---

### 7. Dar de alta un socio con su cuenta de acceso y credenciales temporales

`POST /socios` · Dueño, Recepcionista

**Qué resuelve.** Cargar a una persona nueva como socio en el mostrador, con su cuenta de acceso y una
contraseña temporal para entregarle en el momento.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/socios/SocioFormModal.tsx` | 45-297 | `SocioFormModal` (el envío, `handleSubmit`, desde 98) |
| Entrega de la clave | `Proyecto - PWA/src/frontend/src/components/PanelCredenciales.tsx` | 48-151 | `PanelCredenciales` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/sociosService.ts` | 430-460 | `crearSocio()` |
| Esquemas | `backend/schemas.py` | 213-289 | `SocioAltaRequest`, `SocioAltaResponse` |
| Endpoint | `backend/routers/socios.py` | 302-472 | `alta_socio()` |
| Credenciales | `backend/auth.py` | 90-143 | `generar_password_temporal()`, `generar_username()` |
| Envío por mail | `backend/notificaciones.py` | 89-164 | `enviar_credenciales()` |
| Vista Flet | `Flet/Proyecto/app/views/socios.py` | 336-648 | `_open_form()`, `_save_socio()`, `_mostrar_credenciales()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1101-1124 | `alta_socio()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 428-429 | `alta_socio()` |

**Cómo funciona.** Del lado de las pantallas, las dos apps mandan la sede clavada en 1 y piden
siempre la cuenta (`sociosService.ts:442-443`, `views/socios.py:525-528`): el sistema opera una sola
sede. La PWA, además, vuelve a pedir el socio recién creado (`sociosService.ts:447-450`), porque la
respuesta del alta trae la persona y no la fila de la grilla; es el único cliente del proceso 10.

El endpoint (`socios.py:315-472`), en orden:

1. **La sede existe**, o 404 (`:320-324`). Se valida primero porque es lo único que no depende de la
   persona.
2. **La persona**: si el DNI ya está cargado, se reusa (`:331`); si no, se crea (`:333-349`) con un
   `flush` para tener su id sin confirmar nada todavía
   ([`flush` contra `commit`](A0-09-el-orm.md#flush-contra-commit)), y con su contacto de emergencia si
   vino (`:353-361`). Si la persona ya es socia, 409 (`:362-366`).
3. **El email no choca** con el de otra persona, o 409 (`:370-380`): la base lo haría cumplir igual
   con su `UNIQUE`, pero con un mensaje incomprensible.
4. **El teléfono**, como principal (`:385-391`).
5. **El socio**, con fecha de alta de hoy (`:394-403`), y su número —`S-0001`— armado **después** del
   insert, a partir del id que dio la base (`:404`, con `_numero_socio()`, `:60-70`): calcularlo antes
   daría números repetidos con dos altas simultáneas
   ([identidad generada](A0-07-bases-de-datos-relacionales.md#clave-primaria-e-identidad-generada)).
6. **La cuenta** (`:410-432`): si la persona ya tenía una —un empleado que se hace socio—, se conserva
   con su contraseña; si no, se genera usuario y clave temporal, y la cuenta nace marcada para cambiarla
   ([contraseña temporal](A-07-autenticacion.md#contraseña-temporal-y-primer-ingreso)).
7. **Una sola confirmación** para todo (`:434`): si algo falló más arriba, no queda una persona sin
   ficha ni una ficha sin cuenta.
8. **El mail, después de confirmar** (`:443-450`): mandarlo antes podría entregar credenciales de una
   cuenta que no llegó a existir, y `enviar_credenciales()` no lanza, así que un correo caído no tumba
   un alta ya guardada.

La respuesta trae la contraseña temporal en texto, la única vez que existe legible, y las dos apps la
muestran en el panel de credenciales, que ofrece "Cobrar ahora"
([los pasos del mostrador](A-01-que-es-olimpos.md#la-cantidad-de-pasos-que-cuesta-una-operación)).

**Qué escribe y qué lee.**

| Tabla | Atributos | Escribe o lee | Línea |
|---|---|---|---|
| `Sede` | `id_sede` | lee | `socios.py:320` |
| `Persona` | `dni` (para reusar), `email` (para el choque) | lee | `:331`, `:371-375` |
| `Persona` | `dni`, `nombre`, `apellido`, `email`, `sexo`, `fecha_nacimiento`, `calle`, `numero_calle`, `localidad` | escribe | `:334-344` |
| `Contacto_Emergencia` | `id_persona`, `nombre`, `telefono`, `parentesco`, `principal` | escribe | `:354-360` |
| `Telefono` | `id_persona`, `numero`, `tipo`, `principal` | escribe | `:386-391` |
| `Socio` | `id_persona`, `id_sede`, `fecha_alta`, `objetivo`, `observaciones`, `activo`, `numero_socio` | escribe | `:394-404` |
| `Socio` | la existencia de la fila | lee | `:362` |
| `Usuario` | `username` (para no repetirlo) y la cuenta de la persona | lee | `:411`, `:419` |
| `Usuario` | `id_persona`, `username`, `password_hash`, `debe_cambiar_password`, `activo` | escribe | `:424-432` |

Coincide con la línea DFD.

**Por qué está hecho así.** Un solo pedido y no tres encadenados, para que el alta sea una
[transacción](A0-07-bases-de-datos-relacionales.md#transacción-acid-commit-y-rollback): *"en un
mostrador con gente esperando, media alta a medio hacer es peor que ninguna"*
(`schemas.py:218-223`). El alta no elige plan: el plan es una membresía, y una membresía se crea
cobrándola; el selector que dejaba elegirlo y no lo guardaba se sacó
([nada muerto en pantalla](A-01-que-es-olimpos.md#nada-muerto-en-pantalla)). Y no existe un
"Registrarse": la cuenta sólo nace de este alta ([A-07](A-07-autenticacion.md#no-existe-registrarse)).

**Nota marcada · el reuso de la persona no cubre al socio que vuelve, y pierde datos del formulario.**
El comentario del reuso (`socios.py:327-330`) pone dos ejemplos: *"un empleado del gimnasio que se hace
socio, o alguien que se dio de baja y vuelve"*. El segundo no pasa por acá: la baja es lógica, la fila
de `Socio` sigue existiendo, y el alta responde 409 *"ya está registrado como socio"* (`:362-366`). El
que vuelve se reactiva (proceso 24). Y cuando la persona sí se reusa —el empleado—, el alta toma sólo
lo que es del socio: la fecha de nacimiento, el domicilio y el contacto de emergencia del formulario
**se descartan sin aviso**, porque sólo se guardan al crear la persona (`:333-361`), y el teléfono se
agrega igual como principal (`:385-391`) sin desmarcar el que ya tuviera, así que la ficha puede quedar
con dos principales ([regla 1](#las-listas-con-un-principal-teléfonos-y-contactos-de-emergencia)). El
caso es real, porque todo empleado tiene cargado un mail o un teléfono.

**Nota marcada · Flet invita a cargar lesiones donde el Recepcionista las ve.** El campo
`observaciones` de la ficha lo lee cualquiera que vea Socios. La PWA lo aclara en el formulario:
*"Notas del mostrador. Las lesiones y condiciones van en la ficha médica"*
(`SocioFormModal.tsx:242`). Flet, en el mismo campo, sugiere *"Lesiones, restricciones..."*
(`views/socios.py:450`). Es una divergencia entre las gemelas en la que la PWA tiene razón: el texto de
Flet empuja un dato médico al único lugar de la ficha que el Recepcionista sí ve.

El docstring del módulo, además, describe un alta que no existe: *"La persona llega al mostrador,
paga, y el personal carga sus datos"* (`socios.py:11`). El alta no cobra nada; el cobro es el paso
siguiente, en Cobros.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| La sede no existe | 404 | *"La sede indicada no existe."* | `socios.py:320-324` |
| La persona ya es socia | 409 | *"{nombre} ya está registrado como socio."* | `socios.py:362-366` |
| El email es de otra persona | 409 | *"Ese email ya está registrado para otra persona."* | `socios.py:376-380` |
| DNI de menos de 6 caracteres, nombre o apellido vacíos | 422 | el de Pydantic | `schemas.py:226-228` |
| Teléfono con letras o menos de 6 dígitos | 422 | *"El teléfono sólo puede tener números…"* | `schemas.py:41-54` |
| Email sin dominio completo | 422 | *"El email tiene que tener un dominio completo…"*, antes que el de `EmailStr` ([por qué](B-04-usuarios-y-cuentas.md#41-editar-el-usuario-y-el-email-de-una-cuenta)) | `schemas.py:74-100` |
| Fecha de nacimiento futura o anterior a 1900 | 422 | *"La fecha de nacimiento no puede ser posterior a hoy."* y el de 1900 | `schemas.py:57-71` |

La línea DFD nombra los tres primeros. Los 422 son rechazos del esquema, antes del endpoint.

---

### 8. Finalizar la asignación de un entrenador conservando el historial

`POST /socios/entrenadores/asignaciones/{id_asignacion}/finalizar` · Dueño, Recepcionista, Entrenador

**Qué resuelve.** Que un entrenador deje de estar a cargo de un socio, sin borrar que lo estuvo.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/socios/EntrenadoresModal.tsx` | 42-250 | `EntrenadoresModal` (la llamada, 116) |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/sociosService.ts` | 661-669 | `finalizarAsignacionEntrenador()` |
| Esquemas | `backend/schemas.py` | 2202-2214 | `AsignacionEntrenadorOut` |
| Endpoint | `backend/routers/socios.py` | 1068-1105 | `finalizar_asignacion()` |
| Quién es el entrenador | `backend/routers/rutinas.py` | 68-80 | `_entrenador_de_sesion()` |
| Vista Flet | `Flet/Proyecto/app/views/socios.py` | 942-1071 | `_entrenadores()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1618-1622 | `finalizar_entrenador()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 870-871 | `finalizar_asignacion_entrenador()` |

**Cómo funciona.** Busca la asignación (`socios.py:1087-1090`); si quien pide es un Entrenador, sólo
puede terminar las suyas (`:1091-1096`); si ya estaba finalizada, 400 (`:1097-1099`); si no, la marca
`FINALIZADA` con la fecha de hoy (`:1101-1104`). La ruta va por el id de la asignación y no bajo el del
socio (`:1083-1085`): pedir los dos permitiría mandar una combinación que no coincide.

**Qué escribe y qué lee.** Escribe `Asignacion_Entrenador.estado` y `fecha_fin` (`:1101-1102`); lee la
asignación, el entrenador de la sesión (`rutinas.py:68-80`) y la persona del entrenador para la
respuesta (`_a_asignacion_out()`, `:923-936`). Coincide con la línea DFD.

**Por qué está hecho así.** No se borra porque el historial es el motivo de que la tabla exista
(`:1076-1081`); es la [baja lógica](A-10-bajas-logicas.md#baja-lógica-soft-delete) aplicada a una
relación.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| La asignación no existe | 404 | *"Esa asignación no existe."* | `socios.py:1088-1090` |
| Un Entrenador intenta terminar la de otro | 403 | *"Sólo podés terminar tus propias asignaciones."* | `socios.py:1092-1096` |
| Ya estaba finalizada | 400 | *"Esa asignación ya estaba finalizada."* | `socios.py:1097-1099` |

---

### 9. Listar los socios que entrena un entrenador

`GET /socios/entrenadores/{id_entrenador}/socios` · Dueño, Recepcionista, Entrenador, Nutricionista

**Qué resuelve.** La vista inversa de la asignación: a quiénes entrena este entrenador.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | — (ninguna pantalla lo usa) | | |
| Service PWA | — (ningún service lo llama) | | |
| Esquemas | `backend/schemas.py` | 426-485 | `SocioOut` |
| Endpoint | `backend/routers/socios.py` | 1108-1134 | `socios_del_entrenador()` |
| Vista Flet | — (no existe en Flet) | | |

**Cómo funciona.** Comprueba que el entrenador exista (`:1121-1123`), busca los socios activos con una
asignación activa de ese entrenador (`:1125-1131`) y los arma con el mismo camino en lote que la grilla
(`:1133-1134`).

**Qué escribe y qué lee.** No escribe. Lee `Entrenador`, `Asignacion_Entrenador` y todo lo de la grilla.
Coincide con la línea DFD, con una diferencia de comportamiento respecto del proceso 6: no aplica las
bajas vencidas antes de leer.

**Nota marcada · el endpoint no tiene ningún cliente.** Su docstring dice que *"es la que usa el
entrenador"* y que existe porque la pregunta del entrenador al llegar es *"¿a quiénes tengo yo?"*
(`socios.py:1115-1119`). Ninguna de las dos apps la llama: no hay pantalla de "mis socios" para el
Entrenador, que hoy trabaja desde la grilla completa (y por eso [V-10](#v-10-el-entrenador-y-el-nutricionista-ven-a-todos-los-socios)
le importa tanto). El endpoint está hecho y probado; le falta la pantalla que lo justifica.

**Qué pasa cuando sale mal.** 404 *"Ese entrenador no existe."* (`socios.py:1121-1123`).

---

### 10. Consultar la ficha de un socio

`GET /socios/{id_socio}` · Dueño, Recepcionista, Entrenador, Nutricionista

**Qué resuelve.** Un socio solo, con la misma forma que una fila de la grilla.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | — (lo llama el alta, no una pantalla) | | |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/sociosService.ts` | 462-465 | `obtenerSocio()` |
| Endpoint | `backend/routers/socios.py` | 479-488 | `obtener_socio()` |
| Armado | `backend/routers/socios.py` | 259-285 | `_a_socio_out()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 424-425 | `obtener_socio()` (ningún estado lo llama) |

**Cómo funciona.** Busca el socio por clave primaria y lo arma de a uno (`socios.py:485-488`). Su único
cliente es `crearSocio()`, que lo pide después del alta (`sociosService.ts:450`).

**Qué escribe y qué lee.** No escribe. Lee lo mismo que una fila de la grilla, consulta por consulta
([la grilla](#la-grilla-socioout-y-sus-dos-armadores)). Coincide con la línea DFD.

**Por qué está hecho así.** Una línea: es el armador de a uno expuesto como ruta. Que el alta necesite
un segundo pedido para obtener la fila es un viaje de más en una operación que ocurre una vez por
socio, que es donde un paso de más cuesta menos.

**Qué pasa cuando sale mal.** 404 *"El socio no existe."* (`socios.py:486-487`).

---

### 11. Editar la ficha de un socio

`PUT /socios/{id_socio}` · Dueño, Recepcionista

**Qué resuelve.** Corregir los datos personales, el objetivo, las observaciones, el teléfono principal
y el contacto de emergencia principal.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/socios/SocioFormModal.tsx` | 45-297 | `SocioFormModal` (la edición, 107) |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/sociosService.ts` | 493-510 | `actualizarSocio()` |
| Esquemas | `backend/schemas.py` | 290-322 | `SocioEditarRequest` |
| Endpoint | `backend/routers/socios.py` | 491-596 | `editar_socio()` |
| Vista Flet | `Flet/Proyecto/app/views/socios.py` | 485-545 | `_save_socio()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 438-442 | `editar_socio()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 432-433 | `editar_socio()` |

**Cómo funciona.** El endpoint (`socios.py:516-596`):

1. Si el email cambia y es de otra persona, 409 (`:523-530`).
2. Nombre y apellido se escriben siempre, porque el esquema los exige (`:533-534`).
3. **El resto, sólo si vino en el pedido** (`:540-553`): `model_fields_set` distingue "no lo mandó" de
   "lo mandó vacío para borrarlo" (`:508-514`). Es la corrección de un caso real: un formulario que no
   tenía un campo lo borraba en silencio. El choque de esta regla con la semántica de `PUT` está en
   [método HTTP e idempotencia](A0-03-http.md#método-http-e-idempotencia).
4. **El contacto de emergencia principal** se crea o se actualiza, nunca se borra desde acá
   (`:559-575`). Crearlo exige nombre y teléfono juntos, o 400 (`:564-567`).
5. **El teléfono principal** se actualiza, se crea si no había ninguno, o se **borra** si llegó vacío
   (`:579-592`).
6. Confirma y devuelve la fila armada de a uno (`:594-596`).

**Qué escribe y qué lee.** Escribe `Persona` (`nombre`, `apellido`, `email`, `fecha_nacimiento`,
`calle`, `numero_calle`, `localidad`), `Socio` (`objetivo`, `observaciones`), `Contacto_Emergencia` y
`Telefono` (crear, actualizar o borrar); lee lo mismo que la ficha. Coincide con la línea DFD.

**Por qué está hecho así.** El DNI no se edita: *"sería decir que es otra persona"* (`:506`). Y el
formulario toca dos tablas porque los datos personales viven en `Persona` y no se repiten por cada
función que la persona cumple (`:501-504`; [tabla subtipo](A-05-modelo-de-datos.md#tabla-subtipo-especialización)).

Dos detalles del paso 4 y el paso 5, que se apartan de las reglas generales. El contacto de emergencia
se trata como un **bloque**: si vienen el nombre o el teléfono, el parentesco se escribe siempre, aunque
no haya venido (`:575`). No pierde datos en la práctica, porque las dos apps mandan los tres campos
juntos, precargados con el principal (`SocioFormModal.tsx:72-84`). Y vaciar el teléfono **borra el
principal sin ascender a otro** (`:591-592`), a diferencia del borrado de teléfonos, que sí asciende
([regla 4](#las-listas-con-un-principal-teléfonos-y-contactos-de-emergencia)); la grilla igual muestra
el que quede, porque toma "el principal, o el primero que haya".

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| El socio no existe | 404 | *"El socio no existe."* | `socios.py:517-518` |
| El email es de otra persona | 409 | *"Ese email ya está registrado para otra persona."* | `socios.py:528-530` |
| Contacto de emergencia nuevo sin nombre o sin teléfono | 400 | *"El contacto de emergencia necesita nombre y teléfono."* | `socios.py:564-567` |
| Datos inválidos (email, teléfono, fecha) | 422 | los de los validadores del esquema | `schemas.py:290-322` |

---

### 12. Anular una baja programada que todavía no ocurrió

`POST /socios/{id_socio}/anular-baja` · Dueño, Recepcionista

**Qué resuelve.** El socio que avisó que se iba y cambió de idea antes de la fecha.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/socios/SociosView.tsx` | 207-217 | `anularBaja` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/sociosService.ts` | 545-548 | `anularBajaSocio()` |
| Endpoint | `backend/routers/socios.py` | 668-690 | `anular_baja()` |
| Regla de negocio | `backend/bajas.py` | 51-55 | `baja_pendiente()` |
| Vista Flet | `Flet/Proyecto/app/views/socios.py` | 925-930 | `_anular_baja()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1135-1138 | `anular_baja_socio()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 446-447 | `anular_baja_socio()` |

**Cómo funciona.** Busca la baja pendiente del socio (`socios.py:683`) y la **borra** (`:687`). Si no
hay ninguna, 400.

**Qué escribe y qué lee.** Borra la fila de `Baja` entera, y por eso la línea DFD declara todos sus
atributos en el bloque de escritura; lee el socio y lo que hace falta para devolver la fila. Coincide.

**Por qué está hecho así.** Es uno de los pocos borrados reales del sistema, y el docstring dice por qué:
*"una baja que nunca se aplicó no es historial de nada"* (`:677-678`). Una baja ya aplicada no se anula:
se reactiva al socio (proceso 24). La baja programada y su anulación están en
[baja programada y baja inmediata](A-10-bajas-logicas.md#baja-programada-y-baja-inmediata).

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| El socio no existe | 404 | *"El socio no existe."* | `socios.py:681-682` |
| No tiene una baja programada | 400 | *"{nombre} no tiene una baja programada."* | `socios.py:684-686` |

---

### 13. Dar de baja a un socio, programada al vencer el período pago o inmediata

`POST /socios/{id_socio}/baja` · Dueño, Recepcionista

**Qué resuelve.** Registrar que un socio se va, sin quitarle los días que pagó, o cortarlo hoy cuando el
gimnasio lo decide.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/socios/BajaSocioModal.tsx` | 34-104 | `BajaSocioModal` |
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/socios/SociosView.tsx` | 184-203 | `confirmarBaja` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/sociosService.ts` | 525-538 | `darDeBajaSocio()` |
| Esquemas | `backend/schemas.py` | 410-425 | `TipoBaja`, `BajaRequest` |
| Endpoint | `backend/routers/socios.py` | 599-665 | `dar_de_baja()` |
| Regla de negocio | `backend/bajas.py` | 51-125 | `baja_pendiente()`, `_cerrar_pausa()`, `fecha_de_baja()`, `aplicar_baja()` |
| Lista de espera | `backend/turnos.py` | 148-205 | `promover_de_lista_de_espera()` |
| Vista Flet | `Flet/Proyecto/app/views/socios.py` | 828-923 | `_confirmar_baja()`, `_ejecutar_baja()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1126-1130 | `dar_de_baja_socio()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 436-439 | `dar_de_baja_socio()` |

**Cómo funciona.** El endpoint (`socios.py:620-665`) rechaza al socio que ya estaba de baja (`:623-625`)
y al que ya tiene una baja programada, salvo que se pida la inmediata (`:627-632`). Después, dos caminos:

- **Programada** (el caso por defecto, `:647-656`): `fecha_de_baja()` cierra la pausa en curso si la
  hay —sumándole al vencimiento los días que se usaron— y devuelve el día siguiente al vencimiento, o hoy
  si no hay período pago (`bajas.py:81-94`). Si esa fecha es futura, la baja queda **pendiente** y el
  socio sigue activo; si es hoy, se aplica en el acto.
- **Inmediata** (`:634-646`): corta hoy aunque tenga la cuota paga. Si ya había una programada, la
  adelanta reusando la misma fila (`:639-643`).

Cuando la baja se aplica, `aplicar_baja()` deja al socio inactivo, cancela sus membresías activas o
suspendidas, cancela sus reservas futuras y apaga la cuenta si el tipo no es voluntario
(`bajas.py:97-125`); el endpoint promueve la lista de espera de cada turno que quedó con lugar
(`socios.py:659-661`). Todo en una confirmación (`:663`).

**Qué escribe y qué lee.** Escribe `Baja` (`:645-656`), `Congelamiento.estado` y `fecha_reanudacion`
(al cerrar la pausa, `bajas.py:68-78`), `Membresia.fecha_vencimiento` (la extensión de la pausa) y
`estado`, `Socio.activo`, `Reserva.estado` y `fecha_cancelacion`, y `Usuario.activo`. Lee además
`Turno` para las reservas futuras y la lista de espera. Coincide con la línea DFD.

**Por qué está hecho así.** Todo el diseño —la baja que respeta lo pagado, el tipo que decide si la
cuenta se apaga, la baja inmediata como excepción del personal— está en
[bajas lógicas](A-10-bajas-logicas.md#baja-programada-y-baja-inmediata) y en
[tipo de baja y el acople de la cuenta](A-10-bajas-logicas.md#tipo-de-baja-y-el-acople-de-la-cuenta).

**Nota marcada · la PWA registra todas las bajas como administrativas.** El tipo de baja dice **por qué
se va** el socio —se fue por su cuenta, dejó de pagar, lo decidió el gimnasio— y decide qué pasa con su
cuenta: la voluntaria la deja viva, las otras dos la apagan. Flet pregunta el tipo, con voluntaria por
defecto, y el motivo (`views/socios.py:862-870`). La PWA no pregunta ninguno de los dos: manda siempre
`'ADMINISTRATIVA'` y un motivo vacío (`sociosService.ts:528-535`), con un comentario que confunde quién
**carga** la baja con por qué **se va** el socio: *"'ADMINISTRATIVA' porque acá la inicia el staff, no el
socio"* (`:518`). La consecuencia: el mismo socio que viene al mostrador a darse de baja por su cuenta
conserva el acceso a la app si lo carga Flet, y lo pierde si lo carga la PWA, que es la referencia. El
comentario de la línea 516, además, todavía dice que la baja *"cancela la membresía vigente y desactiva
la cuenta de acceso"*, que ya no es cierto para la programada ni para la voluntaria.

**Nota marcada · la baja inmediata no cierra la pausa en curso.** La pausa sólo se cierra en el camino
programado, dentro de `fecha_de_baja()` (`bajas.py:86`). La inmediata va directo a `aplicar_baja()`, que
cancela la membresía suspendida y no toca su `Congelamiento`, que queda `ACTIVO`. Casi siempre da igual,
porque la membresía ya está cancelada. Deja de dar igual si el socio se reactiva y paga una membresía
nueva antes de la fecha de fin de aquella pausa: `_congelamiento_vigente()` del portal busca la pausa
activa del socio sin mirar a qué membresía pertenece (`backend/routers/portal.py:1829-1850`), y la
encontraría como si estuviera en curso.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| El socio no existe | 404 | *"El socio no existe."* | `socios.py:621-622` |
| Ya estaba dado de baja | 400 | *"{nombre} ya estaba dado de baja."* | `socios.py:623-625` |
| Ya tiene una baja programada y no se pidió la inmediata | 400 | *"{nombre} ya tiene la baja programada para el {fecha}."* | `socios.py:628-632` |
| Tipo de baja fuera de los tres valores | 422 | el de Pydantic | `schemas.py:410-419` |

---

### 14. Consultar a quién avisar en una emergencia

`GET /socios/{id_socio}/contactos-emergencia` · Dueño, Recepcionista, Entrenador, Nutricionista

**Qué resuelve.** La lista de contactos de emergencia del socio, con el principal primero.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/socios/EmergenciaModal.tsx` | 46-294 | `EmergenciaModal` (la carga, 67) |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/sociosService.ts` | 279-286 | `listarContactosEmergencia()` |
| Esquemas | `backend/schemas.py` | 361-380 | `ContactoEmergenciaOut` |
| Endpoint | `backend/routers/socios.py` | 1253-1267 | `contactos_emergencia_del_socio()` |
| Vista Flet | `Flet/Proyecto/app/views/socios.py` | 650-761 | `_emergencia()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1182-1198 | `get_contactos_emergencia()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 477-478 | `contactos_emergencia_de_socio()` |

**Cómo funciona.** Comprueba el socio y devuelve sus contactos ordenados (`socios.py:1265-1267`, con
`_emergencias_ordenadas()`, `:1155-1161`).

**Qué escribe y qué lee.** No escribe; lee `Socio` y `Contacto_Emergencia`. Coincide.

**Por qué está hecho así.** Pide la sección y no la acción del historial médico, a propósito: el
Recepcionista lo ve, porque *"en una emergencia el dato sirve justamente en el mostrador"*
(`:1261-1263`). El dato médico se esconde del mostrador; a quién llamar, no.

**Qué pasa cuando sale mal.** 404 *"El socio no existe."* (`_socio_o_404()`, `socios.py:746-751`).

---

### 15. Agregar un contacto de emergencia a la ficha

`POST /socios/{id_socio}/contactos-emergencia` · Dueño, Recepcionista

**Qué resuelve.** Sumar a quién avisar: la madre y la pareja, no una u otra.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/socios/EmergenciaModal.tsx` | 46-294 | `EmergenciaModal` (el alta, 95) |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/sociosService.ts` | 288-297 | `agregarContactoEmergencia()` |
| Esquemas | `backend/schemas.py` | 381-409 | `ContactoEmergenciaRequest` |
| Endpoint | `backend/routers/socios.py` | 1270-1283 | `agregar_contacto_emergencia()` |
| Regla | `backend/routers/socios.py` | 1184-1215 | `_agregar_emergencia()` |
| Vista Flet | `Flet/Proyecto/app/views/socios.py` | 763-780 | `_agregar_emergencia()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1200-1211 | `agregar_contacto_emergencia()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 481-482 | `agregar_contacto_emergencia()` |

**Cómo funciona.** `_agregar_emergencia()` rechaza un número repetido, marca el principal si
corresponde y agrega la fila (`socios.py:1195-1215`); el endpoint confirma (`:1281`). Las reglas son las
de [las listas con un principal](#las-listas-con-un-principal-teléfonos-y-contactos-de-emergencia).

**Qué escribe y qué lee.** Escribe `Contacto_Emergencia` (y el `principal` de los demás, al
desmarcarlos); lee el socio y los contactos existentes. Coincide.

**Por qué está hecho así.** La función vive acá y no copiada en el portal porque "Mi perfil" del socio
usa la misma: *"la regla del principal y la del número repetido tienen que ser LA MISMA"*
(`:1189-1193`). Antes la tabla admitía varios contactos y la app hacía upsert de uno solo, así que
cargar a la madre pisaba a la pareja (`:1141-1152`).

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| El socio no existe | 404 | *"El socio no existe."* | `socios.py:746-751` |
| El número ya está cargado | 409 | *"Ese número ya está cargado como contacto de emergencia."* | `socios.py:1199-1202` |
| Datos inválidos | 422 | los del esquema | `schemas.py:381-409` |

---

### 16. Editar un contacto de emergencia y elegir cuál es el principal

`PUT /socios/{id_socio}/contactos-emergencia/{id_contacto}` · Dueño, Recepcionista

**Qué resuelve.** En la práctica, cambiar cuál es el contacto principal.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/socios/EmergenciaModal.tsx` | 46-294 | `EmergenciaModal` (`marcarPrincipal`, 114) |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/sociosService.ts` | 299-309 | `editarContactoEmergencia()` |
| Endpoint | `backend/routers/socios.py` | 1286-1300 | `editar_contacto_emergencia()` |
| Regla | `backend/routers/socios.py` | 1218-1231 | `_editar_emergencia()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1213-1225 | `marcar_emergencia_principal()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 485-486 | `editar_contacto_emergencia()` |

**Cómo funciona.** Comprueba que el contacto sea de esta ficha (`socios.py:1296`), aplica la regla del
principal y reescribe nombre, teléfono y parentesco (`:1221-1231`). Las dos apps lo usan sólo para marcar
el principal, reenviando lo demás tal como estaba.

**Qué escribe y qué lee.** Escribe `Contacto_Emergencia` (`nombre`, `telefono`, `parentesco`,
`principal`); lee el socio y el contacto. Coincide.

**Por qué está hecho así.** Una línea: es la regla 3 de
[las listas con un principal](#las-listas-con-un-principal-teléfonos-y-contactos-de-emergencia).

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| El socio no existe | 404 | *"El socio no existe."* | `socios.py:746-751` |
| El contacto no es de esta ficha | 404 | *"Ese contacto de emergencia no está en la ficha de este socio."* | `socios.py:1167-1172` |

---

### 17. Sacar un contacto de emergencia de la ficha y ascender el principal si hacía falta

`DELETE /socios/{id_socio}/contactos-emergencia/{id_contacto}` · Dueño, Recepcionista

**Qué resuelve.** Borrar un contacto al que ya no hay que llamar.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/socios/EmergenciaModal.tsx` | 46-294 | `EmergenciaModal` (el borrado, 136) |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/sociosService.ts` | 311-318 | `borrarContactoEmergencia()` |
| Endpoint | `backend/routers/socios.py` | 1303-1314 | `borrar_contacto_emergencia()` |
| Regla | `backend/routers/socios.py` | 1234-1250 | `_borrar_emergencia()` |
| Vista Flet | `Flet/Proyecto/app/views/socios.py` | 782-808 | `_confirmar_borrar_emergencia()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1227-1232 | `borrar_contacto_emergencia()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 489-490 | `borrar_contacto_emergencia()` |

**Cómo funciona.** Borra la fila, manda el borrado a la base con un `flush` y, si era el principal,
asciende al más viejo de los que quedan (`socios.py:1242-1250`).

**Qué escribe y qué lee.** Borra la fila de `Contacto_Emergencia` y puede escribir el `principal` de
otra; lee el socio y los contactos. Coincide.

**Por qué está hecho así.** Una línea: el borrado es real y el ascenso evita una ficha con contactos
pero sin principal ([reglas 4 y 6](#las-listas-con-un-principal-teléfonos-y-contactos-de-emergencia)).

**Qué pasa cuando sale mal.** Los mismos dos 404 del proceso 16.

---

### 18. Consultar los entrenadores a cargo de un socio con su historial

`GET /socios/{id_socio}/entrenadores` · Dueño, Recepcionista, Entrenador, Nutricionista

**Qué resuelve.** Quién entrena a este socio hoy, y quién lo entrenó antes.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/socios/EntrenadoresModal.tsx` | 42-250 | `EntrenadoresModal` (la carga, 61-62) |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/sociosService.ts` | 627-632 | `listarEntrenadoresDeSocio()` |
| Esquemas | `backend/schemas.py` | 2202-2214 | `AsignacionEntrenadorOut` |
| Endpoint | `backend/routers/socios.py` | 939-969 | `entrenadores_del_socio()` |
| Vista Flet | `Flet/Proyecto/app/views/socios.py` | 942-1071 | `_entrenadores()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1591-1612 | `get_entrenadores_de_socio()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 861-863 | `obtener_entrenadores_de_socio()` |

**Cómo funciona.** Comprueba el socio (`socios.py:956-958`), trae sus asignaciones —sólo las activas si
se pide `solo_activos`— de la más nueva a la más vieja (`:960-968`) y le pone a cada una el nombre y la
especialidad del entrenador (`_a_asignacion_out()`, `:923-936`).

**Qué escribe y qué lee.** No escribe; lee `Socio`, `Asignacion_Entrenador`, `Entrenador`, `Empleado` y
`Persona`. Coincide.

**Por qué está hecho así.** Devuelve el historial por defecto porque el historial es la razón de la
tabla: la columna vieja `Socio.id_entrenador_a_cargo` borraba al anterior al reasignar, y nadie podía
responder quién lo entrenaba en marzo (`:949-952` y `:900-906`).

**Qué pasa cuando sale mal.** 404 *"El socio no existe."* (`socios.py:956-958`).

---

### 19. Asignarle un entrenador a cargo a un socio

`POST /socios/{id_socio}/entrenadores` · Dueño, Recepcionista, Entrenador

**Qué resuelve.** Poner a un entrenador a cargo de un socio, o que un entrenador tome a un socio nuevo.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/socios/EntrenadoresModal.tsx` | 42-250 | `EntrenadoresModal` (la asignación, 102) |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/sociosService.ts` | 642-651 | `asignarEntrenador()` |
| Esquemas | `backend/schemas.py` | 2191-2214 | `AsignarEntrenadorRequest`, `AsignacionEntrenadorOut` |
| Endpoint | `backend/routers/socios.py` | 972-1065 | `asignar_entrenador()` |
| Quién es el entrenador | `backend/routers/rutinas.py` | 68-80 | `_entrenador_de_sesion()` |
| Vista Flet | `Flet/Proyecto/app/views/socios.py` | 942-1071 | `_entrenadores()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1614-1616 | `asignar_entrenador()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 866-867 | `asignar_entrenador()` |

**Cómo funciona.** El endpoint (`socios.py:993-1065`), en orden:

1. El socio existe y está activo (`:993-1002`).
2. Si quien pide es un Entrenador, sólo puede asignarse a sí mismo (`:1004-1009`).
3. El entrenador existe y sigue trabajando en el gimnasio (`:1011-1020`).
4. No está ya a cargo de este socio (`:1022-1033`).
5. **Si ya hubo una asignación del mismo entrenador con la misma fecha de inicio, se reactiva esa fila**
   en vez de crear otra (`:1044-1054`). El índice único es por socio, entrenador y fecha de inicio, así
   que soltar a un socio y volver a tomarlo el mismo día —apretar el botón equivocado— terminaba en un
   500 (`:1037-1043`).
6. Si no, una asignación nueva (`:1056-1065`).

**Qué escribe y qué lee.** Escribe `Asignacion_Entrenador` (`id_socio`, `id_entrenador`,
`fecha_inicio`, `fecha_fin`, `estado`); lee `Socio.activo`, `Empleado.activo`, `Entrenador`, la
persona del entrenador y las asignaciones existentes. Coincide.

**Por qué está hecho así.** **Se permiten varios entrenadores a la vez**, y es la diferencia deliberada
con la rutina y la dieta, que admiten una sola activa ([asignación con estado](A-05-modelo-de-datos.md#asignación-con-estado)):
un socio con uno de musculación y otro de funcional es normal (`:983-991`). Lo que se impide es la misma
relación duplicada.

**Nota marcada · quién decide quién entrena a quién.** `CLAUDE.md` dice que *"Quién entrena a quién lo
deciden el Dueño y el Recepcionista"*. El código deja además que el Entrenador lo decida **para sí
mismo**: tomar un socio o soltarlo, nunca ponerle ni sacarle a otro (`socios.py:912-921`), con la acción
`GESTION_RUTINAS`, que el Entrenador tiene. El archivo de procesos coincide con el código: pone al
Entrenador como entidad de los procesos 8 y 19. Gana el código; la frase de `CLAUDE.md` describe lo que
decide el mostrador, no todo lo que se puede hacer.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| El socio no existe | 404 | *"El socio no existe."* | `socios.py:994-996` |
| El socio está dado de baja | 400 | *"Ese socio está dado de baja. Reactivalo antes de asignarle un entrenador."* | `socios.py:997-1002` |
| Un Entrenador intenta asignar a otro | 403 | *"Sólo podés asignarte a vos mismo como entrenador."* | `socios.py:1005-1009` |
| El entrenador no existe | 404 | *"Ese entrenador no existe."* | `socios.py:1012-1014` |
| El entrenador ya no trabaja en el gimnasio | 400 | *"Ese entrenador ya no trabaja en el gimnasio. Elegí uno activo."* | `socios.py:1015-1020` |
| Ya está a cargo de este socio | 409 | *"{nombre} ya está a cargo de este socio."* | `socios.py:1027-1033` |

---

### 20. Consultar el historial médico de un socio

`GET /socios/{id_socio}/patologias` · Dueño, Entrenador, Nutricionista

**Qué resuelve.** Qué condiciones tiene el socio, y qué hacer con cada una.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/socios/PatologiasModal.tsx` | 63-451 | `PatologiasModal` (la carga, 87) |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/patologiasService.ts` | 104-107 | `listarPatologiasDeSocio()` |
| Esquemas | `backend/schemas.py` | 2252-2257 | `PatologiaDeSocioOut` |
| Endpoint | `backend/routers/patologias.py` | 119-133 | `patologias_del_socio()` |
| Vista Flet | `Flet/Proyecto/app/views/socios.py` | 1254-1407 | `_patologias()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1655-1675 | `get_patologias_de_socio()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 895-896 | `obtener_patologias_de_socio()` |

**Cómo funciona.** Comprueba el socio y devuelve sus condiciones, cada una con el nombre y la descripción
del catálogo, ordenadas por nombre (`patologias.py:126-133`).

**Qué escribe y qué lee.** No escribe; lee `Socio`, `Socio_Patologia` y `Patologia`. Coincide.

**Por qué está hecho así.** Dos tablas porque responden dos preguntas
([catálogo contra observación](A-05-modelo-de-datos.md#catálogo-contra-observación)), y un permiso
propio porque el mostrador no lo necesita ([quién puede qué](#quién-puede-qué-en-esta-sección)). Es
también uno de los dos accesos que registra [V-10](#v-10-el-entrenador-y-el-nutricionista-ven-a-todos-los-socios).
El docstring del router dice que para una emergencia al mostrador le alcanza *"el contacto de
emergencia, que vive en Persona"* (`patologias.py:18-19`); desde que son varios, vive en su propia tabla.

**Qué pasa cuando sale mal.** 404 *"El socio no existe."* (`patologias.py:126-128`); 403 para el
Recepcionista, que no tiene la acción.

---

### 21. Registrarle una patología a un socio

`POST /socios/{id_socio}/patologias` · Dueño, Entrenador, Nutricionista

**Qué resuelve.** Cargar una condición del catálogo en la ficha del socio, con su fecha y lo que hay que
tener en cuenta.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/socios/PatologiasModal.tsx` | 63-451 | `PatologiasModal` (el alta, 135) |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/patologiasService.ts` | 123-132 | `asignarPatologia()` |
| Esquemas | `backend/schemas.py` | 2230-2251 | `AsignarPatologiaRequest` |
| Endpoint | `backend/routers/patologias.py` | 136-180 | `asignar_patologia()` |
| Vista Flet | `Flet/Proyecto/app/views/socios.py` | 1254-1407 | `_patologias()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1677-1687 | `asignar_patologia()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 899-900 | `asignar_patologia()` |

**Cómo funciona.** Comprueba el socio (`patologias.py:151-153`) y que la patología esté en el catálogo
(`:155-158`); si el socio ya la tenía, 409 (`:163-169`); si no, agrega la fila y confirma
(`:171-180`). La fecha de diagnóstico futura la rechaza el esquema antes (`schemas.py:2241-2250`).

**Qué escribe y qué lee.** Escribe `Socio_Patologia` (`id_socio`, `id_patologia`, `fecha_diagnostico`,
`observaciones`); lee `Socio`, `Patologia` y la fila existente. Coincide.

**Por qué está hecho así.** El chequeo del 409 repite lo que ya garantiza la clave primaria compuesta, y
el comentario dice para qué: sin él, el rechazo de la base le llegaría a la pantalla como un error
genérico de servidor (`patologias.py:160-162`). Es
[validar dos veces, decidir una](A0-07-bases-de-datos-relacionales.md#restricción-y-tipo-enumerado).

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| El socio no existe | 404 | *"El socio no existe."* | `patologias.py:151-153` |
| La patología no está en el catálogo | 404 | *"Esa patología no está en el catálogo."* | `patologias.py:156-158` |
| El socio ya la tenía | 409 | *"Ese socio ya tiene «{nombre}» registrada. Editala si querés cambiar las observaciones."* | `patologias.py:164-169` |
| Fecha de diagnóstico futura | 422 | *"La fecha de diagnóstico no puede ser posterior a hoy."* | `schemas.py:2246-2249` |

---

### 22. Editar la patología registrada de un socio

`PUT /socios/{id_socio}/patologias/{id_patologia}` · Dueño, Entrenador, Nutricionista

**Qué resuelve.** Actualizar las observaciones o la fecha: una lesión que mejora, una medicación que
cambia.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/socios/PatologiasModal.tsx` | 63-451 | `PatologiasModal` (la edición, 153) |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/patologiasService.ts` | 141-150 | `editarPatologiaDeSocio()` |
| Esquemas | `backend/schemas.py` | 2230-2251 | `AsignarPatologiaRequest` |
| Endpoint | `backend/routers/patologias.py` | 183-208 | `editar_patologia_del_socio()` |
| Vista Flet | `Flet/Proyecto/app/views/socios.py` | 1409-1474 | `_editar_patologia()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1689-1705 | `editar_patologia_de_socio()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 903-907 | `editar_patologia_de_socio()` |

**Cómo funciona.** Busca la fila por la clave compuesta (`patologias.py:199-202`) y reescribe la fecha y
las observaciones (`:204-207`).

**Qué escribe y qué lee.** Escribe `Socio_Patologia.fecha_diagnostico` y `observaciones`; lee la fila y
el catálogo para la respuesta. Coincide.

**Por qué está hecho así.** Existe para no tener que borrar y volver a cargar, que perdería la fecha
original (`:195-197`). Un detalle del contrato: reusa el esquema del alta, que exige `id_patologia` en el
cuerpo aunque el endpoint use el de la ruta y descarte el otro. El cliente de Flet lo documenta
(`api_client.py:904-906`): sin ese campo, el pedido vuelve con un 422.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| El socio no tiene esa patología | 404 | *"Ese socio no tiene esa patología registrada."* | `patologias.py:200-202` |
| Fecha de diagnóstico futura | 422 | *"La fecha de diagnóstico no puede ser posterior a hoy."* | `schemas.py:2246-2249` |

---

### 23. Quitarle una patología a un socio

`DELETE /socios/{id_socio}/patologias/{id_patologia}` · Dueño, Entrenador, Nutricionista

**Qué resuelve.** Sacar una condición que el socio ya no tiene.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/socios/PatologiasModal.tsx` | 63-451 | `PatologiasModal` (el borrado, 193) |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/patologiasService.ts` | 162-164 | `quitarPatologia()` |
| Endpoint | `backend/routers/patologias.py` | 211-238 | `quitar_patologia()` |
| Vista Flet | `Flet/Proyecto/app/views/socios.py` | 1254-1407 | `_patologias()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1707-1719 | `quitar_patologia()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 910-911 | `quitar_patologia()` |

**Cómo funciona.** Busca la fila y la borra (`patologias.py:233-238`).

**Qué escribe y qué lee.** Borra la fila de `Socio_Patologia`, y por eso la línea DFD declara sus cuatro
atributos en la escritura. Coincide.

**Por qué está hecho así.** Es un borrado real, contra la regla general del sistema, y el docstring da el
motivo: esto no es un hecho histórico sino el estado de salud **actual**, y guardar condiciones médicas
viejas de alguien es justamente el dato que no conviene acumular sin motivo (`patologias.py:222-231`).

**Qué pasa cuando sale mal.** 404 *"Ese socio no tiene esa patología registrada."*
(`patologias.py:234-236`).

---

### 24. Reactivar a un socio dado de baja y devolverle el acceso a la app

`POST /socios/{id_socio}/reactivar` · Dueño, Recepcionista

**Qué resuelve.** El socio que se había ido y vuelve.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/socios/SociosView.tsx` | 221-231 | `activar` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/sociosService.ts` | 550-553 | `reactivarSocio()` |
| Endpoint | `backend/routers/socios.py` | 693-721 | `reactivar()` |
| Vista Flet | `Flet/Proyecto/app/views/socios.py` | 932-937 | `_reactivar()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1132-1133 | `reactivar_socio()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 442-443 | `reactivar_socio()` |

**Cómo funciona.** Si el socio ya estaba activo, 400 (`socios.py:711-713`). Si no, lo reactiva y le
prende la cuenta de acceso si tiene una (`:715-717`).

**Qué escribe y qué lee.** Escribe `Socio.activo` y `Usuario.activo`; lee lo de la ficha para la
respuesta. Coincide.

**Por qué está hecho así.** Vuelve **sin membresía**, a propósito: reactivar la vieja le regalaría los
días que pasaron mientras estuvo afuera (`:702-704`). Y las bajas quedan en el historial, como registro
de que se fue y volvió (`:706`).

El costo está en la cuenta. Reactivar prende `Usuario.activo` sin importar por qué estaba apagado. Las
dos banderas están desacopladas a propósito
([las dos banderas](A-10-bajas-logicas.md#las-dos-banderas)), y una cuenta que alguien desactivó desde
Usuarios por otra razón vuelve a quedar activa si el socio pasa por una baja y una reactivación. Es la
regla del dueño —*"reactivar al socio la devuelve"*—, y el precio es que la reactivación no recuerda por
qué estaba apagada.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| El socio no existe | 404 | *"El socio no existe."* | `socios.py:709-710` |
| Ya estaba activo | 400 | *"{nombre} ya estaba activo."* | `socios.py:711-713` |

---

### 25. Listar los teléfonos de la ficha de un socio

`GET /socios/{id_socio}/telefonos` · Dueño, Recepcionista, Entrenador, Nutricionista

**Qué resuelve.** Todos los números del socio, con el principal primero.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/socios/TelefonosModal.tsx` | 47-251 | `TelefonosModal` (la carga, 62) |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/sociosService.ts` | 193-196 | `listarTelefonos()` |
| Esquemas | `backend/schemas.py` | 323-336 | `TelefonoOut` |
| Endpoint | `backend/routers/socios.py` | 795-803 | `telefonos_del_socio()` |
| Vista Flet | `Flet/Proyecto/app/views/socios.py` | 1101-1187 | `_telefonos()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1140-1154 | `get_telefonos_de_socio()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 455-456 | `telefonos_de_socio()` |

**Cómo funciona.** Comprueba el socio y devuelve sus teléfonos ordenados (`socios.py:801-803`).

**Qué escribe y qué lee.** No escribe; lee `Socio` y `Telefono`. Coincide.

**Por qué está hecho así.** Una línea: `Telefono` es una tabla desde el primer día porque una persona
tiene varios números, y la ficha no la aprovechaba hasta que tuvo sus propios endpoints
(`socios.py:728-739`).

**Qué pasa cuando sale mal.** 404 *"El socio no existe."* (`socios.py:746-751`).

---

### 26. Agregar un teléfono a la ficha de un socio

`POST /socios/{id_socio}/telefonos` · Dueño, Recepcionista

**Qué resuelve.** Sumar un número que el socio dicta en el mostrador, sin tocar el resto de la ficha.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/socios/TelefonosModal.tsx` | 47-251 | `TelefonosModal` (el alta, 86) |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/sociosService.ts` | 198-207 | `agregarTelefono()` |
| Esquemas | `backend/schemas.py` | 337-360 | `TelefonoRequest` |
| Endpoint | `backend/routers/socios.py` | 806-834 | `agregar_telefono()` |
| Vista Flet | `Flet/Proyecto/app/views/socios.py` | 1189-1199 | `_agregar_telefono()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1156-1161 | `agregar_telefono()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 459-460 | `agregar_telefono()` |

**Cómo funciona.** Rechaza un número que ya esté (`socios.py:819-821`), decide si es el principal
(`:825-827`) y agrega la fila (`:829-834`).

**Qué escribe y qué lee.** Escribe `Telefono` (`id_persona`, `numero`, `tipo`, `principal`, y el
`principal` de los demás al desmarcarlos); lee el socio y los teléfonos existentes. Coincide.

**Por qué está hecho así.** Separado del `PUT` de la ficha porque agregar un número no es editar la
ficha: pasa en otro momento, y no tiene por qué arrastrar nombre, email y objetivo en el mismo pedido,
que es como se pisan datos sin querer (`socios.py:736-739`).

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| El socio no existe | 404 | *"El socio no existe."* | `socios.py:746-751` |
| El número ya está cargado | 409 | *"Ese número ya está cargado en la ficha."* | `socios.py:819-821` |
| Número con letras o menos de 6 dígitos | 422 | *"El teléfono sólo puede tener números…"* | `schemas.py:337-360` |
| Tipo distinto de `CELULAR` o `FIJO` | 422 | *"El tipo de teléfono tiene que ser CELULAR o FIJO."* | `schemas.py:349-358` |

---

### 27. Editar un teléfono de la ficha y elegir cuál es el principal

`PUT /socios/{id_socio}/telefonos/{id_telefono}` · Dueño, Recepcionista

**Qué resuelve.** En la práctica, cambiar cuál es el teléfono principal.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/socios/TelefonosModal.tsx` | 47-251 | `TelefonosModal` (`marcarPrincipal`, 99) |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/sociosService.ts` | 209-219 | `editarTelefono()` |
| Endpoint | `backend/routers/socios.py` | 837-861 | `editar_telefono()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1163-1174 | `marcar_telefono_principal()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 463-464 | `editar_telefono()` |

**Cómo funciona.** Comprueba que el teléfono sea de esta ficha (`socios.py:846`), aplica la regla del
principal (`:848-855`) y reescribe número y tipo (`:857-858`).

**Qué escribe y qué lee.** Escribe `Telefono` (`numero`, `tipo`, `principal`); lee el socio y el
teléfono. Coincide.

**Por qué está hecho así.** Una línea: la regla 3 de
[las listas con un principal](#las-listas-con-un-principal-teléfonos-y-contactos-de-emergencia), y el
control de repetidos que sólo tiene el alta.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| El socio no existe | 404 | *"El socio no existe."* | `socios.py:746-751` |
| El teléfono no es de esta ficha | 404 | *"Ese teléfono no está en la ficha de este socio."* | `socios.py:774-779` |

---

### 28. Sacar un teléfono de la ficha y ascender el principal si hacía falta

`DELETE /socios/{id_socio}/telefonos/{id_telefono}` · Dueño, Recepcionista

**Qué resuelve.** Borrar un número que ya no existe o que estaba mal cargado.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/socios/TelefonosModal.tsx` | 47-251 | `TelefonosModal` (el borrado, 120) |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/sociosService.ts` | 221-223 | `borrarTelefono()` |
| Endpoint | `backend/routers/socios.py` | 864-893 | `borrar_telefono()` |
| Vista Flet | `Flet/Proyecto/app/views/socios.py` | 1201-1226 | `_confirmar_borrar_telefono()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1176-1180 | `borrar_telefono()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 467-468 | `borrar_telefono()` |

**Cómo funciona.** Borra la fila y, si era el principal, asciende al más viejo de los que quedan
(`socios.py:881-893`).

**Qué escribe y qué lee.** Borra la fila de `Telefono` y puede escribir el `principal` de otro; lee el
socio y los teléfonos. Coincide.

**Por qué está hecho así.** Una línea: el mismo borrado real con ascenso que los contactos de emergencia
([reglas 4 y 6](#las-listas-con-un-principal-teléfonos-y-contactos-de-emergencia)).

**Qué pasa cuando sale mal.** Los mismos dos 404 del proceso 27.

---

## Con qué se conecta

- **Existe por culpa de…** [el mostrador con cola](A-01-que-es-olimpos.md#el-mostrador-con-cola): el
  alta es una sola transacción y un solo pedido porque media alta a medio hacer, con gente esperando,
  es peor que ninguna.
- **Se contradice con…** [las dos banderas](A-10-bajas-logicas.md#las-dos-banderas): la reactivación
  prende la cuenta sin saber por qué estaba apagada; ganó la regla simple de "reactivar devuelve el
  acceso".
- **Es la misma idea que…** [aislamiento de lo propio](A-08-autorizacion.md#aislamiento-de-lo-propio):
  un teléfono o un contacto de otra ficha responde 404 y no 403, para no confirmar que existe.
- **Se contradice con…** [el frontend esconde, el backend rechaza](A-08-autorizacion.md#el-frontend-esconde-el-backend-rechaza):
  V-10 es el caso en que el backend tampoco rechaza, porque el permiso es por sección; ganó poder
  encontrar al socio que todavía no es de nadie.
