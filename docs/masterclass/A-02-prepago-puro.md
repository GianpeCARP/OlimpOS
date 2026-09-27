# A-02 · El modelo de negocio codificado: prepago puro

*Piso del capítulo: la columna que guarda cada hecho de plata, y la tabla que no existe.*

Este capítulo es sobre plata, y la plata es donde un sistema de gestión deja de ser
software genérico y pasa a ser **un negocio en particular**. Casi todas las reglas de acá
se ven como bugs si no se conoce la decisión que las produjo: no hay tabla de deudas, no se
puede pagar el mes que viene, la promoción no se evalúa hoy, Mercado Pago no se llama
Mercado Pago en la base.

El recorrido de un cobro por el código —dónde se levanta el 409, de dónde sale el precio,
cómo se valida la promoción— está en [el recorrido de un pedido](A-04-recorrido-de-un-pedido.md),
que sigue un cobro de cuota escala por escala. Acá no se repite ese camino: se explica **por
qué el negocio lo quiere así**, y qué se pierde con cada decisión.

---

## Prepago puro

### Dos formas de cobrar un servicio

Hay dos modelos, y todo lo demás del capítulo se desprende de cuál se elige.

- **Pospago:** primero se da el servicio, después se cobra. Es el modelo de la luz o del
  teléfono. Implica que en todo momento alguien **debe** algo: hay saldos, vencimientos de
  factura, intereses por mora, recordatorios, gestión de cobranza, y una tabla que registra
  cuánto debe cada uno.
- **Prepago:** primero se cobra, después se da el servicio. Es el modelo de la carga de la
  tarjeta de colectivo. Nadie debe nada nunca: o pagaste el período, o no lo pagaste.

El gimnasio eligió prepago, y lo eligió sin grises. `CLAUDE.md` lo dice en dos frases —*"Prepago
puro. No hay tabla `Deuda`"*— y el esquema escribe la política completa en el encabezado de su
sección de dinero (`db/schema.sql:349-356`): sin débito automático ni suscripción; si el gimnasio
cierra por un perjuicio propio, la membresía se congela con origen `GIMNASIO` y no se devuelve
plata; si el socio se va a mitad de período, no hay compensación; y el reembolso existe sólo para
casos residuales como un cobro duplicado, y es siempre total.

### La tabla que no existe

Éste es el piso del concepto, y es una ausencia. `db/schema.sql` tiene 41 tablas y ninguna se
llama `Deuda`: no hay dónde registrar que alguien debe algo, porque en este modelo nadie debe
algo.

La ausencia se nota en el resto del sistema como una serie de cosas que se sacaron. "Mi cuota"
tenía un "Saldo pendiente" y un bloque de deudas que siempre daban cero, y se eliminaron
(`docs/ESTADO-ACTUAL.md`). La pantalla de cobros de Flet lo deja escrito
(`Flet/Proyecto/app/views/cobros.py:191`): *"Sin bloque de deudas: el esquema eliminó la
tabla Deuda (prepago puro)"*. Y quedan dos vestigios de antes: el docstring de
`backend/routers/cobros.py` todavía se presenta como *"Planes, cobros, membresías y
deudas"*, y la acción `gestionDeudas` sigue en la matriz de permisos sin proteger nada
(detallado en la [nota sobre la matriz](A-08-autorizacion.md#matriz-de-permisos)).

### Por qué está hecho así

**Qué se optimiza:** que el gimnasio no tenga que cobrarle a nadie después. Una persona de
[mostrador con cola](A-01-que-es-olimpos.md#el-mostrador-con-cola) no puede perseguir deudas, calcular intereses ni conciliar saldos. En
prepago, cada cobro cierra el tema: la plata entró y el período está pago.

**Qué alternativa se descartó:** el pospago mensual, que es lo que tienen muchos gimnasios
con débito automático. Con él aparecen la deuda, el cobro fallido y el socio moroso, y cada
uno trae su propia pantalla, su propio estado y su propia regla.

**Qué se pagó:** el gimnasio no le da crédito a nadie. Y como se ve en la nota que sigue, eso
no significa que le cierre la puerta.

**Cómo se llama:** además de prepago, es un caso de **derivar en vez de almacenar**. La deuda
no es un dato guardado: es la conclusión de mirar las membresías, y esa técnica es el tema de
[estados derivados](A-09-estados-derivados.md).

### Prepago no quiere decir que sin pago no se entra

La lectura más literal de "prepago" sería que sin cuota paga no se entra. **No es la regla.**
`CLAUDE.md` lo dice sin ambigüedad: *"Con la cuota vencida ficha igual y se muestra un
aviso"*. [El sistema informa, no juzga](A-01-que-es-olimpos.md#el-sistema-informa-no-juzga).

La consecuencia para este capítulo es precisa: **prepago quiere decir que se cobra antes del
período, no que sin pago no se entra.** Son dos reglas distintas, y el gimnasio adoptó la
primera sin la segunda.

---

## Membresía vigente y qué significa "deber"

### Deber es una ausencia, no un saldo

Si no hay deuda, ¿qué quiere decir que un socio "debe"? `CLAUDE.md` lo define en cinco
palabras: *"'Debe' = no tiene membresía vigente"*.

Y una **membresía vigente** es una fila de `Membresia` en estado `ACTIVA` cuyo período cubre
el día de hoy: que empezó y todavía no terminó. El período lo marcan dos columnas,
`fecha_inicio` y `fecha_vencimiento` (`db/schema.sql:375-383`).

Lo que se sigue de esa definición cambia la pregunta que se le puede hacer al sistema. **"¿Cuánto
debe?" no tiene respuesta**, porque no hay un saldo: hay un período pagado o no hay ninguno. La
pregunta que sí tiene respuesta es otra, y el docstring de `backend/routers/cobros.py:24-26` la
nombra al explicar por qué renovar crea una fila nueva en vez de modificar la anterior: *"Así
queda el historial de cuándo estuvo al día y cuándo no, que es lo que permite responder
'¿desde cuándo debe?'"*. La respuesta es la fecha de vencimiento de su última membresía.

> **↓ Capa 1 — la comparación contra hoy.**

Todo lo anterior se reduce a una comparación de fechas: el vencimiento contra el día de hoy.
Esa comparación la hacen dos piezas del sistema, cada una con su propósito: el cálculo del
estado del socio —Activo, Por vencer, Vencido y los demás, con su orden de precedencia— en
[estados derivados](A-09-estados-derivados.md), y la regla que decide si se puede cobrar, en
[la escala 16 del recorrido](A-04-recorrido-de-un-pedido.md#escala-16--la-regla-de-negocio),
donde se ve el `>=` exacto y por qué el día del vencimiento todavía está pago.

Un caso borde lo resuelve el esquema: `fecha_vencimiento` **admite `NULL`**, y una membresía
sin vencimiento está vigente para siempre. No hay período que termine, y por lo tanto nada que
renovar.

### Nota sobre un nombre

`_membresia_vigente()` en `backend/routers/socios.py:87-93` no devuelve una membresía vigente
en el sentido de arriba. Su docstring es exacto: *"La membresía más reciente del socio,
cualquiera sea su estado"*. Trae la **candidata** —la última—, y quién decide si está vigente es
el cálculo del estado, que después compara sus fechas y su estado. El nombre abrevia el uso más
frecuente; no es un error, pero conviene no leerlo literal.

---

## `precio_pactado` contra `precio_actual`

### Tres precios, tres hechos

En la base hay más de un número que se llama "precio", y cada uno registra un hecho distinto:

| Columna | Tabla | Qué registra | ¿Cambia con el tiempo? |
|---|---|---|---|
| `precio_actual` | `Tipo_Membresia` | lo que cuesta el plan **hoy** | sí, cada vez que el dueño lo actualiza |
| `precio_pactado` | `Membresia` | lo que costó **ese período** cuando se vendió | nunca |
| `monto` y `monto_descuento` | `Pago` | lo que **efectivamente se cobró**, y cuánto se descontó | nunca |

`db/schema.sql:361-368` para el plan y `375-383` para la membresía. En la semilla del estado de
entrega (`db/seed.sql:111-112`), el plan Mensual cuesta $35.000 por 30 días y el Trimestral
$95.000 por 90; al crear una membresía, la semilla copia el precio actual del plan en el
pactado (`seed.sql:337-338`), que es exactamente lo que pasa en cada venta real.

> **↓ Capa 1 — por qué no es redundante.**

Tener el mismo número en dos tablas parece violar la
[tercera forma normal](A0-07-bases-de-datos-relacionales.md#normalización-3fn), que prohíbe
guardar un dato que se puede deducir de otro. No la viola, porque **no se puede deducir**: el
precio pactado de una membresía de marzo no se obtiene del precio actual del plan, que ya es el
de octubre. Son dos hechos distintos sobre dos cosas distintas —la lista de precios de hoy, y
el contrato de un período— que el día de la venta coinciden por casualidad. Si la membresía
leyera el precio del plan en vez de guardarlo, cada aumento reescribiría retroactivamente lo
que pagó cada socio en el pasado.

### Nota marcada · quién puede cobrar un precio distinto

El dueño puede cobrar un monto que no sea el de la lista —un precio pactado especial, un
ajuste—, y cómo lo hace el handler está en
[el precio del recorrido](A-04-recorrido-de-un-pedido.md#154--el-precio-líneas-277-288). Hay una
diferencia entre lo que dice el docstring y lo que hace el código. El docstring de
`backend/routers/cobros.py` afirma que `monto_manual` *"exige el permiso de promociones, que en
la matriz solo tiene el Dueño"*. El código no consulta la matriz: compara el rol `"dueno"` a
mano. Hoy el resultado es el mismo, porque sólo el dueño tiene `gestionPromociones`, pero el
mecanismo descripto no es el que corre: si mañana alguien le diera ese permiso a otro rol, el
docstring diría que puede y el código seguiría diciendo que no. Gana el código.

---

## Sin cobros por adelantado

### Prepago no es adelanto

La distinción que ordena toda la sección:

- **Prepago** es pagar **este** período antes de usarlo. Es la regla general del sistema.
- **Adelanto** es pagar **el período siguiente** mientras el actual todavía corre. Es lo que
  está prohibido.

Y el plan Trimestral **no es un adelanto**: es **un solo período** de 90 días, vendido de una
vez al precio que el gimnasio decidió para ese plan. Lo que la regla prohíbe no es comprometerse
por más tiempo; es **apilar períodos**.

### Por qué: la economía del precio congelado

`backend/renovacion.py:9-12` da el motivo, que es de plata: quien paga ocho meses por adelantado
*"se queda con el precio de hoy, y si la cuota aumenta en el medio el gimnasio cobra esos meses
a precio viejo. Con el adelanto permitido, lo único que separaba al socio de congelar su precio
era tener la plata junta"*.

Con los precios de la semilla y **un aumento hipotético** para ver el mecanismo: un socio paga
ocho meses del plan Mensual juntos, a $35.000 cada uno, $280.000. En el tercer mes la cuota
sube a $42.000. Los meses tres a ocho ya están cobrados a $35.000: son seis meses a $7.000 menos
cada uno, **$42.000 que el gimnasio no cobra, exactamente una cuota entera**. Y el socio que no
tenía la plata junta paga los $42.000 cada mes. La regla existe para que el precio lo pague
igual todo el mundo.

En un país donde la cuota de un gimnasio se actualiza varias veces por año, esto no es un caso
raro sino el caso normal. Y explica la forma del Trimestral: el gimnasio **sí** vende un
compromiso más largo con descuento —$95.000 contra los $105.000 de tres mensuales, alrededor de
un 9,5 %—, pero lo acota a 90 días y lo vuelve a cotizar en cada renovación. Controla cuánto se
congela y por cuánto tiempo. (Cotizarlo de nuevo, eso sí, hoy exige editar la base: ninguna app
cambia el precio de un plan, y lo cuenta [B-05, proceso 50](B-05-cobros-y-pagos.md#50-crear-un-plan-de-membresía).)

### El segundo motivo: un bug que se fue con la regla

El docstring de `renovacion.py:14-19` guarda un motivo que no es de plata, y es el que muestra
que la regla también simplificó el modelo. Mientras se podía renovar con la cuota vigente, el
cobro hacía algo raro: *"marcaba VENCIDA la membresía que estaba corriendo y creaba la próxima
ACTIVA con inicio futuro. 'Mi cuota' mostraba el plan y las fechas del período que todavía no
había empezado, y con una cuota congelada se creaban períodos superpuestos."*

Prohibir el adelanto no arregló ese código: **lo volvió innecesario**. *"Sin adelantos, la
membresía nueva siempre arranca HOY y ese camino desaparece entero."* Queda una garantía que
antes no había: un socio tiene **a lo sumo un período en curso, y ese período siempre contiene
el día de hoy**. Ninguna membresía empieza en el futuro, ninguna se superpone con otra, y "Mi
cuota" no tiene dos candidatos para mostrar.

### El esquema recuerda lo que el negocio apagó

El esquema se diseñó para soportar adelantos, y todavía lo muestra. `Pago` tiene una columna
`es_adelanto` con una restricción que sólo tiene sentido si puede ser verdadera
(`db/schema.sql:484`):

```sql
CONSTRAINT chk_pago_adelanto_periodo CHECK (NOT es_adelanto OR periodo_desde IS NOT NULL)
```

"Si es un adelanto, tiene que decir desde cuándo cubre." La regla de negocio apagó esa
capacidad, y el comentario de la columna (`schema.sql:496-499`) lo registra: *"Siempre false
desde 2026-09-16 (…) Se conserva por los pagos históricos y por chk_pago_adelanto_periodo"*. La
columna no se borró porque puede haber pagos anteriores a esa fecha marcados como adelanto, y un
registro contable no se reescribe.

### Dónde vive la regla

La regla está en un solo lugar, `estado_renovacion()` de `backend/renovacion.py`, y la usan los
tres caminos que cobran una cuota —mostrador, pago online y su acreditación— y las pantallas,
que la reciben resuelta para no ofrecer un botón que después se rechaza. Sus seis condiciones,
el día de corte y por qué la regla viaja con su motivo redactado están en
[la escala 16 del recorrido](A-04-recorrido-de-un-pedido.md#escala-16--la-regla-de-negocio). El
409 que la hace cumplir, y por qué es la red de seguridad y no el mecanismo, en
[el 409 es el rechazo interesante](A-04-recorrido-de-un-pedido.md#el-409-es-el-rechazo-interesante).

### Por qué está hecho así

**Qué se optimiza:** que ningún socio pueda congelar su precio por más tiempo del que el
gimnasio decide, y que el modelo de membresías tenga un solo período en curso.

**Qué alternativas había, y qué se pierde con cada una.** Permitir el adelanto y cobrar la
diferencia cuando la cuota aumente: reintroduce la deuda, porque el socio le debería al gimnasio
la diferencia, y el sistema es prepago. Permitirlo con el precio indexado: lo mismo, más una
cuenta que nadie en el mostrador puede explicar. Permitirlo y aceptar la pérdida: es lo que había,
y lo que el dueño decidió cortar.

**Qué se pagó:** el socio que quiere pagar todo el año de una vez no puede, salvo con el
Trimestral; y el gimnasio pierde la plata que entraría antes con los adelantos.

**Cómo se llama:** una **invariante** —una propiedad que el sistema garantiza siempre—: un solo
período en curso, y contiene hoy. Una regla de negocio que, además de cuidar la caja, hizo más
simple el modelo de datos.

---

## Sin renovación automática

### El pago único, no la suscripción

Ningún período se renueva solo. Cada uno se cobra por un acto explícito: el recepcionista en el
mostrador, o el socio desde la app. `CLAUDE.md` lo dice sin rodeos —*"No hay renovación
automática"*— y el esquema lo pone en la primera línea de su política de dinero: *"Sin debito
automatico ni suscripcion"* (`db/schema.sql:350`).

Del lado del pago online, la diferencia está en qué se le pide a Mercado Pago. La plataforma
ofrece dos cosas distintas: una **preferencia**, que es un cobro único —la persona paga una vez y
termina—, y una **suscripción**, que es una autorización para cobrarle a la persona todos los
meses sin que vuelva a hacer nada. El backend pide la primera: `/checkout/preferences`
(`backend/mercadopago.py:249`). Éste es el piso del concepto.

### Si el socio no paga, la cuota vence

Y ahí termina. No hay reintentos, ni estado de "cobro fallido", ni aviso de mora: el período se
terminó y no empezó otro. El socio pasa a "Vencido" al día siguiente del vencimiento, y como el
sistema informa y no juzga, sigue pudiendo fichar con un aviso.

Esa es la razón de fondo para no suscribir: una renovación automática **cobra sin que la persona
actúe**, y cuando el cobro falla —tarjeta vencida, sin saldo— aparece un período que se dio sin
estar pago. Eso es una deuda, y el sistema no tiene dónde ponerla.

**Qué se pagó:** cada período necesita que alguien haga algo. El estado **"Por vencer"** —los
siete días antes del vencimiento— existe para eso: que el socio y el mostrador vean venir el
vencimiento antes de que llegue ([estados derivados](A-09-estados-derivados.md)). Y
`Pago.id_tipo_membresia` guarda qué plan se cobró en cada pago, porque sin renovación automática
no hay "el plan del socio": hay un plan por período, y puede cambiar en cada uno.

---

## Promoción porcentual

### Sólo porcentajes

La única forma de descuento del sistema es una **promoción porcentual**: un porcentaje sobre el
precio, con fechas de vigencia. `Promocion` (`db/schema.sql:437-450`) guarda el porcentaje en
`porcentaje_descuento numeric(5,2)` y lo acota con una restricción: mayor que cero y hasta cien.
No existe un descuento de monto fijo.

Una propiedad de esa elección, que se sigue de la sección anterior aunque ningún documento la da
como motivo: un porcentaje **conserva la proporción cuando el precio cambia**. Un "20 %" sigue
siendo un 20 % después de un aumento; un "$7.000 menos" pesaría cada vez menos.

### Guardada en el pago

La promoción no se aplica leyéndola cada vez: queda **registrada en el `Pago`**, con `id_promocion`
y `monto_descuento` (`schema.sql:464-484`). Es la misma lógica que `precio_pactado`: el descuento
que se hizo ese día es un hecho histórico. Si el dueño cambia el porcentaje de la promoción, o la
da de baja, los pagos que ya la usaron no cambian.

### Vigente el día que arranca el período, no hoy

Ésta es la regla que parece un error. `CLAUDE.md`: las promociones *"tienen que estar vigentes el
día que arranca el período cobrado, no hoy"*.

El motivo es qué cosa se está descontando. Una promoción no descuenta **el acto de pagar**:
descuenta **un período del servicio**. Una promoción de enero es un descuento sobre los períodos
de enero, y lo que decide si le corresponde a un período es cuándo empieza ese período, no qué día
pasó la persona por el mostrador.

Hoy las dos fechas son la misma, porque sin adelantos el período nuevo siempre arranca hoy. El
código igual se escribe contra el inicio del período —la línea 315 de `cobros.py`, con
`inicio_periodo = date.today()` y un comentario que lo explica—, de modo que la regla sigue siendo
correcta el día que las dos fechas se separen. Los rechazos que resultan de esa regla y la función
que la chequea están en
[la promoción del recorrido](A-04-recorrido-de-un-pedido.md#155--la-promoción-líneas-290-337).

Listar las promociones pide la sección Cobros; crearlas y editarlas pide `gestionPromociones`, que
en la [matriz](A-08-autorizacion.md#matriz-de-permisos) sólo tiene el dueño.

---

## Método de pago

### Los cinco valores

`db/schema.sql:69`:

```sql
CREATE TYPE metodo_pago AS ENUM ('EFECTIVO', 'DEBITO', 'CREDITO', 'TRANSFERENCIA', 'BILLETERA_VIRTUAL');
```

Éste es el piso del concepto, y la regla que lo organiza es una sola: **el método describe cómo
paga la persona, no qué empresa procesa el pago.**

### Mercado Pago no se llama Mercado Pago

Un pago hecho desde la app, a través de Mercado Pago, se guarda como `BILLETERA_VIRTUAL`. El
comentario de `backend/routers/pagos_online.py:140-143` explica por qué no se agregó un valor
propio:

> *"No se agrega un valor 'MERCADO_PAGO' porque el enum describe CÓMO paga la persona, no con qué
> proveedor lo procesamos: si mañana se cambia de pasarela, el método de pago del socio sigue
> siendo el mismo."*

Es una separación entre **lo que pasó** —la persona pagó con una billetera en el celular— y **cómo
se implementó** —con qué empresa hoy—. Lo primero es un dato del negocio y va a la base; lo segundo
es un detalle técnico que puede cambiar, y si estuviera en el enumerado, cambiar de proveedor
dividiría en dos categorías los pagos que para el gimnasio son iguales.

### Transferencia no es billetera

La pregunta obvia es por qué `BILLETERA_VIRTUAL` y `TRANSFERENCIA` son valores distintos, si las
dos cosas son "plata que llega por internet". `CLAUDE.md` da la respuesta: *"se concilian en
lugares distintos"*. Una transferencia aparece en el resumen del banco del gimnasio; un pago con
billetera aparece en la cuenta del proveedor de la billetera, y llega al banco después, agrupado.
Conciliar es cruzar lo que dice el sistema con lo que dice cada una de esas fuentes, y el método de
pago es lo que le dice a quien concilia **dónde buscar** cada peso.

---

## La caja y sus cuatro casos

### La regla

El cobro en el mostrador existe, pero no es el camino principal. `CLAUDE.md` lo limita a cuatro
casos, y todo lo demás lo paga el socio desde la app:

1. **Efectivo.**
2. **El socio que no usa la app.**
3. **Un pago que entró por fuera.**
4. **Corregir un cobro.**

Lo mismo vale para la clase suelta.

### Una regla de uso, no de código

Este es el piso, y hay que decirlo con precisión: **los cuatro casos no están escritos en ningún
lugar del código.** Ningún endpoint pregunta "¿es uno de los cuatro casos?". Es una regla de
cómo se usa el sistema, y el código lo que hace es **proveer la herramienta que cada caso
necesita**:

| Caso | Qué del sistema lo atiende |
|---|---|
| Efectivo | el valor `EFECTIVO` del método de pago, que sólo tiene sentido en el mostrador |
| El socio sin app | el cobro de mostrador, con cualquier método |
| Un pago que entró por fuera | `numero_comprobante`, que es `UNIQUE` en `Pago`: una transferencia que llegó por su cuenta se registra una vez con su comprobante, y la base impide registrarla dos veces |
| Corregir un cobro | `anular_pago()` (`backend/routers/cobros.py:490`), que pone el pago en `CANCELADO` con su fecha y **nunca borra la fila** |

La última merece su razón, que está en el docstring de `cobros.py:21-22`: *"Un registro contable
que desaparece es un agujero en la caja: si alguien cobra y después borra la fila, no queda rastro
de que cobró."* Corregir un error no es borrarlo: es dejar registrado el error y su anulación
—aunque hoy la herramienta existe sólo en la API: ninguna pantalla la llama
([B-05, proceso 47](B-05-cobros-y-pagos.md#47-anular-un-pago))—. Es
la misma idea de las [bajas lógicas](A-10-bajas-logicas.md).

Y en los cuatro casos rige lo que el mismo docstring pone en mayúsculas: *"EL MONTO LO CALCULA EL
BACKEND, NUNCA EL CLIENTE"*, con el ejemplo del ataque que evita —cobrar $1 una membresía de
$30.000 desde la consola del navegador—.

---

## Clase suelta y abono de actividad

### Vender actividad aparte de la cuota

La cuota da acceso al gimnasio. Las actividades con turno —yoga, boxeo— se venden aparte, con
**planes de actividad** (`Plan_Actividad`, `db/schema.sql:541`), y la forma de cada plan la decide
una sola columna, `tipo_limite`, con tres valores (`schema.sql:73`):

| `tipo_limite` | Qué vende | Qué significa `cantidad` |
|---|---|---|
| `POR_SEMANA` | un abono de N clases por semana | clases por semana, y se renueva cada semana |
| `POR_MES` | un abono de N clases en el mes | un saldo total que se va gastando |
| `CLASE_SUELTA` | una clase | siempre 1 |

La **clase suelta** no es un concepto aparte en la base: es un plan de actividad con
`tipo_limite = CLASE_SUELTA`. Ése es el piso.

### Los topes, y por qué son de lógica y no de precio

`backend/schemas.py:943-948` limita la cantidad de cada tipo: 7 por semana, 31 por mes, 1 la
suelta. El docstring (líneas 938-941) explica que no es una restricción comercial:

> *"Una semana tiene 7 días y un mes 31. Sin esto se podía cargar '8 clases por semana' o '32 por
> mes', que no son planes caros: son planes IMPOSIBLES — el socio los compra y nunca puede usar lo
> que pagó, porque no existen tantos días donde gastarlos."*

Y la suelta tiene su propio razonamiento en una línea: *"Una clase suelta es una: si fueran dos, es
un abono."*

### Las clases restantes se cuentan

Un abono por mes tiene un saldo: si se compraron 8 clases y se usaron 3, quedan 5. La forma obvia
de guardarlo es una columna que se descuenta en cada reserva. **El sistema no la tiene.** El
comentario de `backend/routers/actividades.py:125-129`:

> *"`clases_restantes` YA NO es una columna: se calcula contando Reserva. Contar es la única fuente
> de verdad, así que no hay un contador que se pueda desincronizar. Se cuentan las reservas que
> OCUPAN una clase (RESERVADA / EN_ESPERA); cancelar una libera la clase automáticamente por dejar
> de contar."*

`clases_restantes_de()` (línea 137) resta de la cantidad del plan las reservas que ocupan una
clase, y sólo lo hace para `POR_MES`: el semanal se recalcula cada semana y la suelta es de a una,
así que ninguno de los dos tiene un saldo total. Un contador guardado se desincronizaría con la
primera cancelación que no lo actualizara; una cuenta no puede desincronizarse, porque no hay nada
que actualizar. Es otra vez **derivar en vez de almacenar**.

### Nota marcada · el docstring que describe el contador que ya no existe

El docstring del módulo, en `actividades.py:30-31`, todavía dice que al reservar *"se descuenta de
`clases_restantes`"*, como si fuera una columna que se decrementa. Es la descripción del mecanismo
anterior. El comportamiento es el de las líneas 125-129 —se cuenta, no se descuenta— y el
resultado para el socio es el mismo: sin saldo no hay reserva. Gana el código.

---

## Con qué se conecta

- **Es la misma idea que…** [estados derivados](A-09-estados-derivados.md): "debe" y las clases
  restantes no se guardan, se calculan; y por eso no hay nada que se pueda desincronizar.
- **Es el mismo problema que…** `precio_pactado`: congelar un precio para un período es correcto;
  congelarlo para períodos apilados es exactamente el adelanto que se prohibió.
- **Se contradice con…** "el sistema informa, no juzga": el cobro es prepago, pero el acceso no se
  corta, y el gimnasio decidió confiar en eso.
- **Es la misma idea que…** las [bajas lógicas](A-10-bajas-logicas.md): anular un pago lo marca y
  no lo borra, igual que dar de baja a una persona.
- **Existe por culpa de…** [el frontend esconde, el backend rechaza](A-08-autorizacion.md#el-frontend-esconde-el-backend-rechaza):
  la regla del adelanto viaja resuelta a las pantallas y además se rechaza en el servidor.
- **Es la misma idea que…** la [baja programada](A-10-bajas-logicas.md#baja-programada-y-baja-inmediata):
  las dos respetan lo que el socio ya pagó; una no le cobra de más, la otra no le quita días.
