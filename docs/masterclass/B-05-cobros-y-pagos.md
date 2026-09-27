# B-05 · Cobros y pagos

*Procesos 46 a 51. Piso del capítulo: la línea que implementa cada paso, en las tres capas.*

Seis procesos sobre la plata que entra, en cuatro temas:

| Tema | Procesos |
|---|---|
| Cobrar en el mostrador y corregir un cobro | 46, 47 |
| Ver: el estado de cuenta de un socio y los planes | 48, 49 |
| El catálogo: crear un plan | 50 |
| El aviso de Mercado Pago | 51 |

Este es el capítulo de la Parte B que más se apoya en la Parte A, porque las reglas de la plata ya
están enteras ahí. Por qué no hay deuda sino membresía vigente, por qué no se cobra por adelantado,
cómo se aplica una promoción, qué son los métodos de pago y para qué existe la caja están en
[prepago puro](A-02-prepago-puro.md). Y el cobro del proceso 46 está recorrido **línea por línea**, del
click al re-render, en [el recorrido de un pedido](A-04-recorrido-de-un-pedido.md). Acá se sigue el
resto, se cruza cada proceso contra su línea DFD y se registra cada rechazo.

**Lo que se corrió, y cómo.** Por HTTP, con el cliente de pruebas de FastAPI contra la app real y la
base apuntando a un PostgreSQL 17 local y descartable cargado con `db/schema.sql` (nunca Neon); la
acreditación de Mercado Pago, llamando a la función directamente. Cada resultado obtenido así dice
**corrido**.

---

## Piezas comunes

### Quién puede qué en esta sección

| Barrera | Quién la tiene | La usan |
|---|---|---|
| Sección `COBROS` en lectura | Dueño y Recepcionista, los dos en total | 48, 49 |
| Sección `COBROS` en total | Dueño y Recepcionista | 47 |
| Acción `COBRAR_PAGOS` | Dueño y Recepcionista | 46 |
| Acción `GESTION_PROMOCIONES` | Dueño | 50 |
| Ninguna sesión: la firma HMAC | Mercado Pago | 51 |

Dos rarezas. Anular un pago (47) no pide una acción sino el nivel total de la sección
(`backend/routers/cobros.py:493`), así que hoy lo pueden los mismos que cobran. Y crear un plan (50)
pide la acción de **promociones**, porque *"definir la lista de precios es una decisión de negocio"*
(`cobros.py:158-160`): el nombre de la acción dice menos de lo que protege, y qué dice de ella el panel
de permisos está en [A-08](A-08-autorizacion.md#nota-marcada--la-parte-del-panel-escrita-a-mano).

### La membresía vencida se corrige al leerla

No hay ninguna tarea programada que marque como `VENCIDA` una membresía cuya fecha pasó. La corrige
quien la lee: `_membresia_vigente()` (`cobros.py:106-128`) recorre las `ACTIVA` del socio, marca
`VENCIDA` las que ya pasaron y devuelve la más reciente que sigue en fecha, porque *"'activa pero
vencida hace tres meses' es peor que no tener el campo"*. La llaman el cobro (46), para que el insert
de la membresía nueva no choque con el índice de una sola `ACTIVA`
([A-04](A-04-recorrido-de-un-pedido.md#escala-15--el-handler-línea-por-línea)), y el estado de cuenta
(48), que después **confirma** esa escritura (`:209`).

Eso convierte al estado de cuenta en un `GET` que escribe, como la grilla de socios, y por la misma
razón no es un riesgo: lo que escribe no depende de nada que traiga el pedido, sólo de la fecha
([B-02, proceso 6](B-02-socios.md#6-listar-socios-y-aplicar-las-bajas-programadas-vencidas)).
**Corrido:** una membresía vencida hace un mes y todavía `ACTIVA` en la base pasó a `VENCIDA` con sólo
consultar el estado de cuenta.

### Las deudas que ya no existen

La respuesta del estado de cuenta todavía trae `deudas` y `deuda_total`, siempre vacías
(`cobros.py:212-216`), el cobro devuelve `deudas_saldadas`, siempre vacía (`:480`), y el pedido del cobro
acepta un `saldar_deudas` que nadie lee (`backend/schemas.py:748`). Quedaron *"por compatibilidad con
las apps"* cuando se eliminó la tabla, y las dos apps los siguen recorriendo: la PWA arma una lista de
deudas con días de atraso que nunca tiene elementos (`Proyecto - PWA/src/frontend/src/services/cobrosService.ts:350-363`)
y Flet lo mismo (`Flet/Proyecto/app/state.py:742-757`). Por qué no hay deuda está en
[la tabla que no existe](A-02-prepago-puro.md#la-tabla-que-no-existe); el `saldar_deudas` sin leer, en
[las discrepancias del recorrido](A-04-recorrido-de-un-pedido.md#discrepancias-encontradas).

---

## Los seis procesos

### 46. Cobrar una cuota en el mostrador

`POST /cobros` · Dueño, Recepcionista

**Qué resuelve.** Cobrarle la cuota a un socio en el mostrador y, si hace falta, un abono de actividad
en el mismo cobro.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/cobros/CobrosView.tsx` | 69-610 | `CobrosView` (la cuota, 233-268; el combo, 301-332) |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/cobrosService.ts` | 222-275 | `cobrar()` |
| Esquemas | `backend/schemas.py` | 730-767, 809-839 | `CobrarRequest`, `InscripcionOut`, `CobroResponse` |
| Endpoint | `backend/routers/cobros.py` | 236-486 | `cobrar()` |
| Regla de negocio | `backend/renovacion.py` | 1-105 | `estado_renovacion()` |
| Vista Flet | `Flet/Proyecto/app/views/cobros.py` | 760-848 | `_cobrar_membresia()`, `_cobrar_plan()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 954-979 | `cobrar_membresia()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 626-627 | `cobrar()` |

**Cómo funciona.** Está recorrido entero en [A-04](A-04-recorrido-de-un-pedido.md), escala por escala:
el socio (`cobros.py:257-259`), la regla del prepago (`:261-266`), el plan (`:268-275`), el precio y el
monto manual (`:277-288`), la promoción (`:290-337`), el comprobante duplicado (`:339-350`) y las dos
escrituras, membresía y pago, en una sola transacción (`:352-415`). Lo que A-04 no sigue es la tercera
escritura, la del **abono de actividad** (`:417-463`): si el pedido trae `id_plan_actividad`, se crea una
inscripción con la misma vigencia que la membresía —*"para que un abono nunca sobreviva a la cuota que
da acceso al gimnasio"* (`:418-421`)—, se suma su precio al total del pago (`:446-448`) y se arma su
resumen para la respuesta (`:450-463`). Las dos apps ofrecen ese combo cuando el socio no tiene la
cuota vigente y quiere una actividad (`CobrosView.tsx:301-332`; `views/cobros.py:821-836`).

**Qué escribe y qué lee.** Escribe `Membresia`, `Pago` y, con el combo, `Inscripcion_Actividad`; lee
`Socio`, `Persona`, `Baja`, `Membresia`, `Tipo_Membresia`, `Promocion`, `Pago` (el comprobante) y
`Plan_Actividad` con su `Actividad`. El detalle, con las consultas contadas, está en
[la escala 17](A-04-recorrido-de-un-pedido.md#escala-17--el-orm-con-las-consultas-contadas). Coincide
con la línea DFD.

**Por qué está hecho así.** El monto lo calcula el backend y nunca el cliente (`cobros.py:7-16`), y todo
va en una transacción porque *"un cobro registrado sin membresía deja al socio pagando sin acceso, y una
membresía sin pago le regala el mes"* (`:249-251`). El resto del porqué está en
[A-04](A-04-recorrido-de-un-pedido.md#por-qué-está-hecho-así) y [A-02](A-02-prepago-puro.md).

**Nota marcada · el cobro con abono de actividad revienta siempre.** `schemas.py` define **dos clases
con el mismo nombre**, `InscripcionOut`: una con los ocho campos del resumen del cobro
(`schemas.py:809-817`) y otra, más abajo, con los catorce de Actividades (`:970-984`). En un módulo de
Python, un nombre vale lo último que se le asignó, así que la segunda **pisa** a la primera para quien
la importe. `CobroResponse` no se entera, porque tomó la primera al definirse (`:823`, antes de la
línea 970). Pero `cobros.py` la importa por nombre (`cobros.py:41`) y recibe la segunda, y la arma con
ocho campos (`:454-463`): Pydantic reclama los seis que faltan y el endpoint responde 500. **Corrido**:
*"cobrar Mensual + Yoga"* dio 500 y no quedó escrito nada, porque la excepción salta antes de
confirmar; el mismo cobro sin la actividad, 201. La segunda clase entró el 2026-08-11 con el ABM de
Actividades, así que el combo que ofrecen las dos apps no funciona desde entonces; su comentario en la
PWA, además, invoca una regla que ya no existe, *"Inscripcion_Actividad.id_membresia es NOT NULL"*
(`CobrosView.tsx:315-317`), cuando la inscripción *"perdió id_membresia"* (`cobros.py:418-419`).

**Qué pasa cuando sale mal.** Los rechazos del cobro, con la línea que los levanta y lo que ve quien
cobra, están en [los finales que no son el feliz](A-04-recorrido-de-un-pedido.md#los-finales-que-no-son-el-feliz).
Faltan en esa tabla los del abono:

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| El plan de actividad no existe | 404 | *"El plan de actividad no existe."* | `cobros.py:425-428` |
| El plan de actividad está dado de baja | 400 | *"El plan '{nombre}' está dado de baja y no se puede vender."* | `cobros.py:429-433` |
| Cualquier combo cuota + abono | 500 | ninguno legible | `cobros.py:454-463` |

La línea DFD nombra todos los rechazos de A-04 y los dos primeros de esta tabla; el 500 no.

---

### 47. Anular un pago

`POST /cobros/pagos/{id_pago}/anular` · Dueño, Recepcionista

**Qué resuelve.** Corregir un cobro mal registrado, que es el cuarto de los
[cuatro casos de la caja](A-02-prepago-puro.md#la-caja-y-sus-cuatro-casos).

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Service PWA | `Proyecto - PWA/src/frontend/src/services/cobrosService.ts` | 280-292 | `anularPago()` |
| Endpoint | `backend/routers/cobros.py` | 489-519 | `anular_pago()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 1015-1016 | `anular_pago()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 630-631 | `anular_pago()` |

**Cómo funciona.** El pago existe, o 404 (`cobros.py:501-503`); no estaba ya anulado, o 400 (`:505-509`).
Pasa a `CANCELADO` con la fecha (`:511-512`) y, si habilitó una membresía, la membresía pasa a
`CANCELADA` (`:514-515`). No se borra nada.

**Qué escribe y qué lee.** Escribe `Pago.estado`, `Pago.fecha_cancelacion` y `Membresia.estado`; lee
el pago, su membresía y el socio con su persona, para la respuesta. Coincide con la línea DFD.

**Por qué está hecho así.** *"Un registro contable que desaparece es un agujero en la caja"*
(`cobros.py:18-22`): anular es una [baja lógica](A-10-bajas-logicas.md#baja-lógica-soft-delete) del
pago. Y la membresía se cancela porque *"si no, anular un cobro le dejaría al socio el mes pago de
arriba"* (`:498-499`).

**Nota marcada · ninguna pantalla anula un pago.** La PWA tiene `anularPago()` y Flet `anular_pago()`,
en el servicio, el estado y el cliente, y **ninguna vista los llama**. Corregir un cobro, uno de los
cuatro casos para los que existe la caja, no se puede hacer desde ninguna app: sólo llamando a la API.
El comentario del servicio de la PWA, además, describe un endpoint de antes: *"vuelve a dejar pendientes
las deudas que había saldado"* (`cobrosService.ts:284-288`).

**Nota marcada · el abono cobrado con el pago no se anula.** La membresía que habilitó el pago se
cancela; la inscripción que se cobró en el mismo pago —el `id_inscripcion` del pago— no se toca. Es la
regla de `CLAUDE.md` —*"al cambiar el estado de una entidad, decidir qué pasa con todo lo que la
referencia"*— aplicada a una sola de las dos referencias. **Corrido**, con el combo armado a mano (el
cobro real revienta, proceso 46): después de anular, el pago quedó `CANCELADO` y la membresía
`CANCELADA`, y la inscripción de Yoga siguió `ACTIVA` hasta su vencimiento, un mes de clases sin pagar.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| El pago no existe | 404 | *"El pago no existe."* | `cobros.py:501-503` |
| Ya estaba anulado | 400 | *"Ese pago ya estaba anulado."* | `cobros.py:505-509` |

La línea DFD nombra los dos.

---

### 48. Consultar el estado de cuenta de un socio

`GET /cobros/socio/{id_socio}` · Dueño, Recepcionista

**Qué resuelve.** Todo lo que el mostrador necesita ver antes de cobrarle a alguien (`cobros.py:194`):
la membresía vigente, los últimos pagos y desde cuándo se puede renovar.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/cobros/CobrosView.tsx` | 112-121 | `cargarCuenta` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/cobrosService.ts` | 326-373 | `obtenerCuotaDeSocio()` |
| Esquema | `backend/schemas.py` | 840-855 | `EstadoCuentaOut` |
| Endpoint | `backend/routers/cobros.py` | 188-229 | `estado_cuenta()` |
| Membresía vigente | `backend/routers/cobros.py` | 106-128 | `_membresia_vigente()` |
| Regla de negocio | `backend/renovacion.py` | 1-105 | `estado_renovacion()` |
| Vista Flet | `Flet/Proyecto/app/views/cobros.py` | 188-207, 417-447 | `_panel_cuenta()`, `_bloque_historial()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 723-783 | `get_cuenta_socio()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 622-623 | `obtener_estado_cuenta()` |

**Cómo funciona.** El socio existe, o 404 (`cobros.py:195-197`). La membresía vigente, corrigiendo las
vencidas (`:199`; [pieza común](#la-membresía-vencida-se-corrige-al-leerla)); los cinco pagos más
recientes, anulados incluidos (`:201-207`); la confirmación de lo corregido (`:209`); y la regla de
renovación, con su motivo y su fecha (`:210`), que es la que decide si la pantalla ofrece cobrar
([dónde vive la regla](A-02-prepago-puro.md#dónde-vive-la-regla)). "Al día" es tener una membresía
vigente y nada más (`:212-222`). La PWA convierte la respuesta a la misma forma que "Mi cuota" del
portal, para reusar sus componentes (`cobrosService.ts:326-333`).

**Qué escribe y qué lee.** Escribe `Membresia.estado` (las vencidas); lee `Socio`, `Persona`, `Membresia`
con su `Tipo_Membresia`, `Pago` y `Baja`. Coincide con la línea DFD.

**Por qué está hecho así.** Cinco pagos y no todos, porque *"el mostrador necesita ver los últimos para
confirmar que no está cobrando dos veces, no el historial completo"* (`cobros.py:55-58`). Y los días que
le quedan a la membresía se calculan con la fecha del **servidor**, porque *"un navegador con la fecha
cambiada podría mostrarse al día estando vencido"* (`:89-92`).

La PWA tiene además una segunda función que pide este mismo endpoint, `obtenerEstadoCuenta()`
(`cobrosService.ts:129-143`), que no usa ninguna vista.

**Qué pasa cuando sale mal.** 404 *"El socio no existe."* (`cobros.py:195-197`), y 403 para quien no
tiene la sección.

---

### 49. Listar los planes de membresía

`GET /cobros/tipos-membresia` · Dueño, Recepcionista

**Qué resuelve.** El selector "Plan a cobrar" de la pantalla de Cobros.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/cobros/CobrosView.tsx` | 95-110 | `listarTiposMembresia` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/sociosService.ts` | 330-344 | `listarTiposMembresia()` |
| Esquema | `backend/schemas.py` | 650-657 | `TipoMembresiaOut` |
| Endpoint | `backend/routers/cobros.py` | 135-148 | `listar_tipos()` |
| Vista Flet | `Flet/Proyecto/app/views/cobros.py` | 247-327 | `_bloque_membresia()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 711-721 | `get_tipos_membresia()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 618-619 | `obtener_tipos_membresia()` |

**Cómo funciona.** Todos los planes, activos o no, del más barato al más caro (`cobros.py:140`). La PWA
se queda con los activos (`sociosService.ts:333-334`); Flet los muestra todos (`state.py:711-721`), y
cobrar uno dado de baja lo rechaza el backend (proceso 46).

**Qué escribe y qué lee.** Lee `Tipo_Membresia` entera. Coincide con la línea DFD.

**Por qué está hecho así.** El socio no usa este endpoint: el portal tiene el suyo, porque éste pide la
sección Cobros (`backend/routers/pagos_online.py:61-63`; [B-14](B-14-portal-del-socio.md)).

Dos restos. La PWA tiene **dos** funciones con este nombre: la que usa Cobros vive en el servicio de
Socios y dice ser *"para el selector del formulario de alta/edición"* (`sociosService.ts:330`), un
selector que se sacó porque el alta no elige plan; la del servicio de Cobros
(`cobrosService.ts:303-320`) no la usa nadie.

**Qué pasa cuando sale mal.** 403 para quien no tiene la sección.

---

### 50. Crear un plan de membresía

`POST /cobros/tipos-membresia` · Dueño

**Qué resuelve.** Agregar un plan nuevo al catálogo, con su duración y su precio.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Esquemas | `backend/schemas.py` | 643-657 | `TipoMembresiaCrear`, `TipoMembresiaOut` |
| Endpoint | `backend/routers/cobros.py` | 151-181 | `crear_tipo()` |

**Cómo funciona.** El nombre, recortado, no existe ya sin distinguir mayúsculas, o 409
(`cobros.py:162-167`); el plan nace activo (`:169-176`). El esquema exige duración y precio mayores que
cero (`schemas.py:643-648`).

**Qué escribe y qué lee.** Escribe `Tipo_Membresia` (`nombre`, `descripcion`, `duracion_dias`,
`precio_actual`, `activo`); lee los nombres existentes. Coincide con la línea DFD.

**Por qué está hecho así.** Sólo el Dueño, porque *"definir la lista de precios es una decisión de
negocio, no operativa del día"* (`cobros.py:158-160`).

**Nota marcada · el catálogo de planes no se administra desde ninguna app.** Este endpoint no tiene
cliente: ni la PWA ni Flet lo llaman. Y no existe ningún endpoint que **edite** un plan o lo **dé de
baja**: ninguna línea del backend escribe `Tipo_Membresia.precio_actual` o `activo` después de crearlo.
Los planes que hay son los que cargó la base de entrega, y cambiarles el precio exige editar la base a
mano. Pesa sobre una regla central: el motivo para
[no cobrar por adelantado](A-02-prepago-puro.md#sin-cobros-por-adelantado) es que los precios suben,
y el sistema no tiene cómo subirlos. Por lo mismo, el rechazo del cobro a un plan *"dado de baja"*
(proceso 46) hoy no lo puede disparar nadie.

**Nota marcada · el nombre duplicado se compara con un patrón.** El choque de nombres usa `ilike`
(`cobros.py:163`), que trata `_` y `%` como comodines. **Corrido:** con un plan llamado *"PaseXlibre"*,
crear *"Pase_libre"* dio 409 *"Ya existe un plan llamado 'Pase_libre'"*, porque el guion bajo coincide
con cualquier letra. Lo evita comparar en minúsculas sin patrón, como hace el `UNIQUE` de la base, que
distingue mayúsculas.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| El nombre ya existe (o coincide con el patrón) | 409 | *"Ya existe un plan llamado '{nombre}'."* | `cobros.py:163-167` |
| Quien pide no es el Dueño | 403 | *"No tenés permisos para realizar esta acción."* | `backend/security.py:208-212` |
| Duración o precio no positivos | 422 | el de Pydantic | `schemas.py:643-648` |

La línea DFD nombra los dos primeros. **Corrido**, el primero y el de la recepcionista.

---

### 51. Acreditar el aviso de pago de Mercado Pago

`POST /webhooks/mercadopago` · sin sesión: lo llama Mercado Pago

**Qué resuelve.** Darle al socio lo que pagó online, cuando Mercado Pago avisa que el pago se aprobó.
El pago nace antes, en el portal, cuando el socio arranca el checkout ([B-14](B-14-portal-del-socio.md)).

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Endpoint | `backend/routers/pagos_online.py` | 293-353 | `webhook_mercadopago()` |
| Acreditación | `backend/routers/pagos_online.py` | 186-290 | `_acreditar()`, `_extender_membresia()` |
| Firma | `backend/mercadopago.py` | 270-305 | `verificar_firma()` |
| Consulta a Mercado Pago | `backend/mercadopago.py` | 308-341 | `consultar_pago()`, `estado_interno()` |
| Estados | `backend/mercadopago.py` | 150-160 | `ESTADOS` |
| Regla de negocio | `backend/renovacion.py` | 1-105 | `estado_renovacion()` |

**Cómo funciona.** El endpoint (`pagos_online.py:293-353`):

1. **Lee el cuerpo, y de él sólo el id** del pago de Mercado Pago (`:315-326`); un cuerpo ilegible,
   un aviso que no es de pagos o sin id se descarta.
2. **Verifica la firma** de la cabecera `x-signature` (`:328-333`): sin firma válida no se acredita
   nada. El mecanismo —el texto firmado, HMAC-SHA256 con el secreto compartido y la comparación en
   tiempo constante— está en [HMAC y firma simétrica](A0-11-criptografia-aplicada.md#hmac-y-firma-simétrica).
3. **Le pregunta a Mercado Pago** cómo terminó ese pago, con el token propio (`:335-343`), y de la
   respuesta saca el id del pago interno, el estado y el monto.
4. **Acredita** (`:345-351`, `_acreditar()` en `:186-229`): si el mismo aviso ya se aplicó, no hace
   nada (`:208-209`); si el monto no coincide con el del pago, no acredita y lo deja para que una persona
   lo mire (`:211-218`); si no, guarda el id de Mercado Pago como comprobante, el estado y, si se aprobó,
   **le da la membresía** (`:220-228`).
5. **La membresía** (`_extender_membresia()`, `:232-290`) sale del plan guardado en el pago, arranca hoy
   y dura lo que dura el plan. Si entre el checkout y el aviso el socio ya tiene un período en curso —el
   mostrador le cobró mientras tanto—, no se crea una segunda: el pago queda confirmado y sin membresía
   *"para devolverlo"* (`:256-265`).
6. **Contesta 200 siempre**, también cuando descarta (`:307-309`).

**Qué escribe y qué lee.** Escribe `Pago` (`estado`, `numero_comprobante`, `fecha_cancelacion`,
`id_membresia`) y `Membresia`; lee el `Pago`, su `Tipo_Membresia`, las `Membresia` del socio y su `Baja`.
Coincide con la línea DFD.

**Por qué está hecho así.** Sin sesión, porque lo llama un servidor que no tiene cookie ni token: *"lo
que la protege es que nadie más puede firmar"* (`pagos_online.py:10-20`). Del cuerpo sólo se cree el
id, porque *"llega por HTTP y lo puede escribir cualquiera que descubra la URL"* (`:311-313`), y el
monto se relee con el token propio: es la [frontera de confianza](A0-05-javascript-y-typescript.md#frontera-de-confianza-del-tipo)
llevada a un servidor ajeno. Siempre 200, porque Mercado Pago *"reintentaría el mismo aviso una y otra
vez creyendo que no llegó"* (`:307-309`), y por la misma razón acreditar tiene que poder repetirse: la
defensa vive en el `UNIQUE` de `numero_comprobante`, *"porque el if se puede olvidar de aplicar y el
UNIQUE no"* (`:192-196`; [idempotencia](A0-03-http.md#método-http-e-idempotencia)). La membresía se da
recién acá, porque *"extender antes sería regalar la cuota a quien abandona el checkout"*
(`:236-237`). **Corrido:** el aviso aprobado creó la membresía; el mismo aviso repetido respondió *"Ya
estaba aplicado. No se hizo nada."*; y un monto distinto no se acreditó.

Este es el único `async def` del repo, y adentro hace llamadas que bloquean: qué significa eso para
el resto de los pedidos está en [A0-10](A0-10-python-del-lado-del-servidor.md). Y todo el proceso está
**escrito y no probado contra Mercado Pago** (`pagos_online.py:7-8`): faltan el token, el secreto del
webhook y una URL pública, y mientras tanto el sistema corre en modo simulado.

**Nota marcada · un reembolso no le quita la membresía al socio.** Mercado Pago traduce *refunded* y
*charged_back* —un reembolso y un contracargo— a `REEMBOLSADO` (`mercadopago.py:158-159`), y la
acreditación de ese aviso sólo cambia el estado del pago (`pagos_online.py:220-223`): la membresía que
ese pago habilitó sigue activa hasta su vencimiento. Anular un pago en el mostrador, en cambio, sí la
cancela (proceso 47). **Corrido:** después de aprobarse y reembolsarse, el pago quedó `REEMBOLSADO` y la
membresía `ACTIVA` con su vencimiento intacto. Hoy no se manifiesta porque Mercado Pago no está
conectado.

**Nota marcada · el pago confirmado sin membresía sólo queda en el log.** El caso del paso 5 —se cobró
online con un período en curso— deja el pago `CONFIRMADO` y sin membresía, *"que es lo que ve quien
revise la caja para devolverlo"*, pero lo único que avisa es un `print` (`pagos_online.py:263-264`).
Ninguna pantalla lista los pagos confirmados sin membresía.

**Qué pasa cuando sale mal.** Nunca responde un error: descarta con 200 y lo explica en el mensaje.

| Caso | Mensaje | Dónde |
|---|---|---|
| Cuerpo ilegible | *"Cuerpo ilegible. Se ignora."* | `pagos_online.py:315-318` |
| Aviso que no es de pagos | *"Aviso de tipo '…'. No aplica."* | `pagos_online.py:320-322` |
| Sin id de pago | *"El aviso no trae id de pago. Se ignora."* | `pagos_online.py:324-326` |
| Firma inválida o sin secreto configurado | *"Firma inválida. El aviso se descarta."* | `pagos_online.py:328-333` |
| No se pudo consultar a Mercado Pago | *"No se pudo consultar el pago. Se reintentará."* | `pagos_online.py:335-338` |
| El pago no tiene referencia interna | *"El pago … no tiene referencia nuestra. Se ignora."* | `pagos_online.py:340-343` |
| El pago interno no existe | *"No existe el pago … Se ignora."* | `pagos_online.py:202-204` |
| El monto no coincide | *"El monto no coincide: … NO se acredita."* | `pagos_online.py:211-218` |

La línea DFD nombra la firma, el duplicado, el monto, la consulta y el pago inexistente.

---

## Con qué se conecta

- **Se contradice con…** [la caja y sus cuatro casos](A-02-prepago-puro.md#la-caja-y-sus-cuatro-casos):
  la caja existe, entre otras cosas, para corregir un cobro, y anular un pago está en la API pero no
  en ninguna pantalla; hoy gana no poder corregir desde el mostrador.
- **Es la misma idea que…** [la baja lógica](A-10-bajas-logicas.md#baja-lógica-soft-delete): anular
  marca el pago en vez de borrarlo y cancela la membresía que habilitó, pero deja activo el abono que se
  cobró con él.
- **Existe por culpa de…** [el esquema de entrada y salida](A0-10-python-del-lado-del-servidor.md#esquema-de-entrada-y-salida-y-el-422):
  el cobro con abono revienta porque en un módulo de Python gana la última definición de un nombre, y
  la respuesta ya había tomado la primera.
- **Es la misma idea que…** [la frontera de confianza del tipo](A0-05-javascript-y-typescript.md#frontera-de-confianza-del-tipo):
  del aviso de Mercado Pago sólo se cree el id; el estado y el monto se releen con el token propio,
  porque el cuerpo lo puede escribir cualquiera.
- **Se contradice con…** [sin cobros por adelantado](A-02-prepago-puro.md#sin-cobros-por-adelantado):
  la regla existe porque los precios suben, y ninguna app puede subir el precio de un plan; hoy gana
  editar la base a mano.
