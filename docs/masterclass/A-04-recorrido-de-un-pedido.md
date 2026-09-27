# A-04 · El recorrido completo de un pedido

**Piso de este capítulo: archivo y línea de cada escala.** No bajamos a explicar qué es
una cookie, qué hace el bucle de eventos o cómo se arma un índice B-tree: eso ya tiene
dueño en la Parte A0 y acá se enlaza. Lo que se baja acá es **horizontal**: se sigue un
solo click, de punta a punta, y en cada escala se dice qué archivo lo atiende, en qué
líneas, con qué símbolo, y a qué capítulo de A0 pertenece el mecanismo que esa escala usa.
Cuando aparece una decisión de diseño se la reconstruye; cuando no la hay, una línea
alcanza.

Este es el capítulo bisagra. Las quince secciones de la Parte B describen 173 procesos, y
los 173 son **variaciones de este mismo recorrido**: cambian el componente que dispara,
el service, el handler y las tablas, pero la escalera es siempre ésta. Quien entienda este
capítulo puede leer cualquier proceso de la Parte B con sólo mirar su tabla de "dónde vive
el código".

---

## El click que vamos a seguir

Son las 19:40 de un martes. En el mostrador hay cuatro personas esperando. La segunda de
la fila es una socia cuya cuota venció ayer; quiere renovarla y paga en efectivo. El
Recepcionista ya la tiene seleccionada en la pantalla de Cobros, con el plan "Trimestral"
elegido en el desplegable, y aprieta **Cobrar renovación**.

Entre ese dedo y el "Cobrado: Trimestral hasta el 24/12/2026" que aparece abajo a la
izquierda hay **dieciocho escalas**, tres procesos distintos (el navegador, el servidor de
desarrollo, el backend), una base de datos a 4.900 kilómetros y, en el camino feliz,
catorce viajes de ida y vuelta contra esa base. Nada de eso lo ve quien cobra. Todo eso es
lo que sigue.

Elegimos este click y no otro por tres motivos. Primero, porque **escribe**: un `GET` se
saltea la mitad de las barreras del sistema —el token CSRF no se le exige, no hay
transacción que confirmar— y dejaría fuera justo lo interesante. Segundo, porque **toca
una regla de negocio que puede rechazarlo** ([Sin cobros por
adelantado](A-02-prepago-puro.md#sin-cobros-por-adelantado)), así que el recorrido tiene un
final feliz y varios infelices, y los infelices enseñan más. Y tercero, porque es
literalmente la operación por la que existe el sistema: el gimnasio es
[prepago puro](A-02-prepago-puro.md#prepago-puro), y cobrar la cuota es el hecho del que
cuelgan el acceso, el estado del socio y la facturación.

---

## Las capas del recorrido

Éste es el mapa completo. Cada fila es una escala, con su archivo, su rango de líneas
verificado, el símbolo que lo implementa y el capítulo que explica el mecanismo. Las
secciones que siguen recorren la tabla de arriba abajo y después de abajo arriba.

### Ida

| # | Escala | Archivo · líneas | Símbolo | Mecanismo explicado en |
|---|---|---|---|---|
| 1 | El botón y el diálogo | `Proyecto - PWA/src/frontend/src/views/cobros/CobrosView.tsx:517-521` y `233-268` | `PrimaryButton`, `cobrarMembresiaClick` | [A0-06](A0-06-react.md#componente-y-jsx) |
| 2 | El service | `Proyecto - PWA/src/frontend/src/services/cobrosService.ts:222-275` | `cobrar()` | este capítulo |
| 3 | El cliente HTTP | `Proyecto - PWA/src/frontend/src/services/api.ts:194-247` | `pedir()` | [A0-04](A0-04-el-navegador-por-dentro.md#fetch) |
| 4 | El proxy de desarrollo | `Proyecto - PWA/src/frontend/vite.config.ts:50-64` | `server.proxy` | [A0-03](A0-03-http.md#proxy-inverso) |
| 5 | La red | — | — | [A0-02](A0-02-como-se-comunican-dos-maquinas.md#tcp-y-el-viaje-de-ida-y-vuelta-rtt) |
| 6 | uvicorn y la aplicación | `backend/main.py:198-212` | `app` | [A0-10](A0-10-python-del-lado-del-servidor.md#asgi-uvicorn-y-el-router) |
| 7 | Cabeceras de seguridad | `backend/main.py:252-277` | `cabeceras_de_seguridad()` | [A0-10](A0-10-python-del-lado-del-servidor.md#middleware) |
| 8 | El middleware de CSRF | `backend/csrf.py:63-95` | `middleware_csrf()` | [A0-12](A0-12-sesiones-y-autenticacion.md#token-csrf-de-doble-envío) |
| 9 | El middleware de CORS | `backend/main.py:214-227` | `CORSMiddleware` | [A0-12](A0-12-sesiones-y-autenticacion.md#cors-y-preflight) |
| 10 | El router y la ruta | `backend/routers/cobros.py:53` y `236` | `router`, `@router.post("")` | [A0-10](A0-10-python-del-lado-del-servidor.md#asgi-uvicorn-y-el-router) |
| 11 | El esquema de entrada | `backend/schemas.py:730-767` | `CobrarRequest` | [A0-10](A0-10-python-del-lado-del-servidor.md#esquema-de-entrada-y-salida-y-el-422) |
| 12 | La sesión de base | `backend/database.py:154-165` | `get_db()` | [A0-09](A0-09-el-orm.md#sesión-y-mapa-de-identidad) |
| 13 | La verificación de sesión | `backend/security.py:80-142` | `obtener_sesion()` | [A0-12](A0-12-sesiones-y-autenticacion.md#jwt) |
| 14 | La dependencia de permisos | `backend/security.py:197-214` · `backend/permisos.py:358-361` | `requiere_accion()`, `puede_accion()` | [A-08](A-08-autorizacion.md#matriz-de-permisos) |
| 15 | El handler | `backend/routers/cobros.py:237-486` | `cobrar()` | este capítulo |
| 16 | La regla de negocio | `backend/renovacion.py:56-105` | `estado_renovacion()` | [A-02](A-02-prepago-puro.md#sin-cobros-por-adelantado) |
| 17 | El ORM | `backend/models.py:453-478` y `481-524` | `Membresia`, `Pago` | [A0-09](A0-09-el-orm.md) |
| 18 | La conexión y el commit | `backend/database.py:92-113` · `backend/routers/cobros.py:465` | `engine`, `db.commit()` | [A0-07](A0-07-bases-de-datos-relacionales.md#transacción-acid-commit-y-rollback) |

### Vuelta

| # | Escala | Archivo · líneas | Símbolo |
|---|---|---|---|
| 18' | La respuesta se arma | `backend/routers/cobros.py:469-486` · `backend/schemas.py:820-832` | `CobroResponse` |
| 9'-7' | Los middlewares, al revés | `backend/main.py:214-227`, `233`, `252-277` | — |
| 4' | El proxy devuelve | `Proyecto - PWA/src/frontend/vite.config.ts:55-63` | `server.proxy` |
| 3' | El JSON parseado | `Proyecto - PWA/src/frontend/src/services/api.ts:230-247` | `pedir()` |
| 2' | El remapeo a la vista | `Proyecto - PWA/src/frontend/src/services/cobrosService.ts:251-274` | `cobrar()` |
| 1' | El re-render | `CobrosView.tsx:250-265` · `store/uiStore.ts:65-72` · `components/ui/Snackbar.tsx:9-23` | `showSnack`, `cargarCuenta`, `Snackbar` |

Dos aclaraciones sobre la tabla antes de arrancar. La escala 5 no tiene archivo porque no
es código de este repo: es el sistema operativo moviendo bytes, y su dueño es A0-02. Y las
escalas 7, 8 y 9 aparecen en la ida en orden inverso al que están escritas en
`backend/main.py`; por qué, en su sección.

---

## Escala 1 · El botón, el diálogo y el cierre que se lleva todo

El disparo está en `Proyecto - PWA/src/frontend/src/views/cobros/CobrosView.tsx:517-521`:

```tsx
<PrimaryButton
  label={cuenta.tieneMembresia ? 'Cobrar renovación' : 'Cobrar membresía'}
  onClick={cobrarMembresiaClick}
  disabled={ocupado || !tipoElegido}
/>
```

Tres cosas para mirar ahí, y ninguna es decorativa.

**La etiqueta cambia sola.** `cuenta.tieneMembresia` viene del backend, no de una bandera
local: es un campo de la respuesta de `GET /cobros/socio/{id}`, mapeado en
`Proyecto - PWA/src/frontend/src/services/cobrosService.ts:339`. Cobrar la primera membresía
y renovar son **la misma operación** —el mismo endpoint, la misma fila nueva en
`Membresia`—, y la única diferencia real es la palabra que lee quien atiende.

**El botón puede no existir.** El bloque entero está adentro de un condicional en
`CobrosView.tsx:486`:
`{cuenta.puedeRenovar && tiposMembresia && tiposMembresia.length > 0 && (...)}`.
Si el backend dijo que no se puede renovar, no hay botón deshabilitado: no hay botón. En
su lugar, `CobrosView.tsx:480-484` muestra el texto que **redactó el backend**
(`cuenta.motivoNoRenovar`). Esto es la [regla resuelta en el
backend](A-09-estados-derivados.md) aplicada al pie de la letra: la pantalla no recalcula
la regla del prepago, la recibe resuelta con su motivo, y por eso no puede ofrecer un
cobro que la API va a rechazar.

**`disabled` cubre el doble click.** `ocupado` es estado local
(`CobrosView.tsx:93`), se pone en `true` antes de disparar el pedido
(`CobrosView.tsx:246`) y vuelve a `false` en el `.finally()` (`CobrosView.tsx:265`). Es la
primera de tres defensas contra el cobro duplicado; las otras dos están en el backend y en
la base.

`PrimaryButton` vive en
`Proyecto - PWA/src/frontend/src/components/ui/PrimaryButton.tsx:14-48` y no hace nada más
que dibujar un `<button>` con la paleta. Sus dos clases raras, `shrink-0` y
`whitespace-nowrap` (línea 42), están documentadas en el comentario de arriba: sin ellas, en
un celular el botón se comprime por debajo de su contenido y "Cobrar renovación" se parte en
dos líneas o se recorta a la primera letra.

### El diálogo, y por qué confirmar acá no es una molestia

`cobrarMembresiaClick` está en `CobrosView.tsx:233-268`. Lo primero que hace no es pedir
nada: arma un texto y abre un diálogo.

```tsx
const aCobrar = previa ? previa.precioFinal : tipoElegido.precio_actual;
```

Esa línea (238) resuelve un problema chico y real: si hay una promoción elegida, el número
que se confirma tiene que ser **el que se va a registrar**, no el de lista. `previa` es la
respuesta de la vista previa de descuento, pedida por el efecto de las líneas 214-230, y su
comentario de las líneas 179-182 dice por qué el descuento no se multiplica en el cliente:
la fórmula, con su piso en cero y su redondeo, vive en un solo lugar
(`backend/routers/promociones.py:88-103`, `precio_con_promo()`), y así el número que se ve
antes de cobrar es exactamente el que se va a guardar.

El diálogo se abre llamando a `confirmDialog` del store global
(`Proyecto - PWA/src/frontend/src/store/uiStore.ts:79-80`), que sólo escribe un objeto
`{open, title, message, onConfirm}`. Quien lo dibuja es `ConfirmDialog`
(`Proyecto - PWA/src/frontend/src/components/ui/ConfirmDialog.tsx:7-40`), montado **una
sola vez** en `App.tsx:85`. El botón "Confirmar" de ese componente (líneas 29-35) invoca
`onConfirm?.()` y después `closeDialog()`.

Acá hay un detalle de JavaScript que conviene nombrar aunque no explicarlo: el tercer
argumento de `confirmDialog` es una función anónima definida adentro de
`cobrarMembresiaClick`, y esa función lee `socioSeleccionado`, `tipoElegido`, `metodo` e
`idPromocionElegida`. Cuando `ConfirmDialog` la ejecuta, medio segundo después y desde otro
componente, esos valores siguen siendo los correctos porque la función se los llevó
consigo: es un [cierre](A0-05-javascript-y-typescript.md#cierre-closure). No hay ningún
mecanismo de paso de parámetros entre los dos componentes; el valor viaja adentro de la
función.

> **Ingeniería inversa · ¿por qué un diálogo, si el dueño odia la fricción?**
> `CLAUDE.md` es explícito en que el [mostrador con cola](A-01-que-es-olimpos.md#el-mostrador-con-cola)
> no lee carteles y en que el sistema
> [informa en vez de juzgar](A-01-que-es-olimpos.md#el-sistema-informa-no-juzga). Un diálogo de confirmación parece ir en contra de eso. No lo
> está, y el motivo es qué se optimiza en cada caso. Los avisos que el dueño sacó eran
> **preguntas sobre algo reversible** —el ejemplo vivo es el fichaje, que no tiene tope por
> día ni pregunta nada—: frenan la cola y no evitan nada, porque desfichar lo corrige.
> Este diálogo, en cambio, es lo último que se puede leer antes de una **escritura
> contable**: después del click hay una fila en `Pago` que, por decisión explícita, no se
> borra nunca —se anula, y anular deja rastro (`backend/routers/cobros.py:489-519`)—. Lo que
> se paga por tenerlo es un segundo de cada cobro; lo que se compra es que el monto, el
> método y el plan se lean una vez antes de que existan. El patrón es **confirmar sólo lo
> que no se deshace**, y la línea que lo decide es la que separa a `Pago` de `Asistencia`.

---

## Service del frontend

*(Escala 2 del mapa.)*

**El problema.** Una vista de React sabe de botones, de estado y de pantalla. No tiene por
qué saber que el cobro viaja como `POST` a `/cobros`, que el campo se llama
`id_tipo_membresia` y no `idTipoMembresia`, que hay que mandar `credentials: 'include'`, ni
que un 409 trae el mensaje adentro de `detail`. Si lo supiera, cada vista sería un cliente
HTTP a medias, y el día que cambie una ruta habría que buscarla en quince archivos.

**La definición.** El **service del frontend** es la capa que traduce una intención de
pantalla en un pedido HTTP, y la respuesta del pedido en datos de vista. En este sistema la
regla es absoluta y se puede verificar: **ninguna pantalla llama a la red por su cuenta**.
En la PWA los services viven en `Proyecto - PWA/src/frontend/src/services/`, uno por
dominio; en la app de escritorio el rol equivalente lo cumple
`Flet/Proyecto/app/api_client.py`, y entre la vista y ese cliente hay además
`Flet/Proyecto/app/state.py`.

La función que nos toca es `cobrar()`, en
`Proyecto - PWA/src/frontend/src/services/cobrosService.ts:222-275`. Hace exactamente tres
cosas.

**Uno: arma el cuerpo** (líneas 238-249).

```ts
const d = await pedir<CobroApi>('/cobros', {
  metodo: 'POST',
  cuerpo: {
    id_socio: idSocio,
    id_tipo_membresia: idTipoMembresia,
    metodo,
    id_plan_actividad: opciones.idPlanActividad ?? null,
    numero_comprobante: opciones.numeroComprobante ?? null,
    id_promocion: opciones.idPromocion ?? null,
    saldar_deudas: true,
  },
});
```

Acá está la frontera de nomenclatura del sistema: **la PWA escribe en `camelCase` y la API
en `snake_case`**, y la traducción ocurre en esta línea y en su gemela de la vuelta. No es
una convención cosmética: los nombres de `snake_case` son los de las columnas de
`db/schema.sql`, y mantenerlos idénticos desde la columna hasta el cuerpo del pedido
significa que buscar `id_tipo_membresia` con `grep` encuentra el DDL, el modelo, el
esquema, el handler y el service — la cadena entera.

**Dos: no manda el monto.** Es lo más importante del archivo y está escrito en el
comentario de cabecera (`cobrosService.ts:3-7`) y repetido en el docstring del router
(`backend/routers/cobros.py:7-16`). El cuerpo dice **qué** se está cobrando —el plan, la
promoción— y nunca **cuánto**. Si el precio viajara desde el cliente, cualquiera con la
consola del navegador abierta podría cobrar $1 una membresía de $30.000 y en la base
quedaría un `Pago` perfectamente válido, con su fecha, su método y su comprobante. La
promoción sigue la misma regla y por eso viaja `id_promocion` y no un descuento ya
calculado (comentario en `cobrosService.ts:229-234`).

Esto es la [frontera de confianza del
tipo](A0-05-javascript-y-typescript.md#frontera-de-confianza-del-tipo) llevada al plano del
negocio: el tipo `MetodoPago` de la línea 19 no protege de nada, porque en tiempo de
ejecución no existe; lo que protege es que el dato caro no esté en el pedido.

**Tres: no guarda nada.** `cobrar()` no tiene estado, no cachea, no recuerda el último
cobro. Devuelve una promesa y se olvida. Quien decide qué hacer con el resultado es la
vista.

> **Ingeniería inversa · el service como frontera, y qué se paga por él.**
> Lo que se optimiza es el **costo de cambiar**: hoy hay una sola definición de qué es
> cobrar una cuota en toda la PWA, y por eso agregar `id_promocion` al pedido —cuando el
> dueño pidió promociones— se hizo tocando tres líneas de este archivo y ninguna de las
> vistas. La restricción que lo acorrala es que las dos apps son
> [gemelas](A-03-dos-apps-un-backend.md): cada cambio se replica en Flet en la misma tanda,
> y replicar una línea de un service es barato mientras que replicar llamadas de red
> desperdigadas en las vistas es donde se pierden los arreglos. La alternativa descartada
> es la obvia —`fetch` directo en el componente, que es lo que hace media internet—: es más
> corta de escribir y deja el `credentials: 'include'`, el token CSRF y el manejo del 401
> como cosas de las que cada vista se tiene que acordar; alcanza con que una se olvide para
> que ahí la sesión no viaje. Lo que se paga es una indirección más y un archivo extra por
> dominio. El patrón se llama **capa anticorrupción**: adentro del service vive el
> vocabulario de la API, y afuera, el de la pantalla.

---

## Escala 3 · `pedir()`, el único lugar donde la PWA toca la red

`Proyecto - PWA/src/frontend/src/services/api.ts:194-247`. Todos los services pasan por
acá; es el gemelo de `Flet/Proyecto/app/api_client.py`, y su comentario de cabecera
(líneas 42-43) lo dice: si cambia el manejo de un código de estado en uno, hay que mirar el
otro.

En el camino del cobro, `pedir()` hace cinco cosas antes de mandar nada.

**Uno · la URL base.** `const API_URL = import.meta.env.VITE_API_URL ?? '/api'` (línea 56).
Ese `/api` es **relativo a la página**, y el comentario de las líneas 45-55 cuenta qué pasó
el 2026-09-16 cuando el valor por defecto era absoluto: alguien borró el `.env` del
frontend pensando que alcanzaba con el del backend, la PWA quedó pegándole a
`http://127.0.0.1:8000` mientras la página estaba en `http://localhost:5173`, y **todo
respondía 401 después de un login exitoso**, sin ningún aviso de por qué. Son dos
[orígenes](A0-04-el-navegador-por-dentro.md#origen-y-política-del-mismo-origen) distintos;
por qué eso rompe la sesión se ve en la escala 4.

**Dos · el token CSRF** (líneas 203-206).

```ts
if (metodo !== 'GET') {
  const csrf = tokenCsrf();
  if (csrf) headers[HEADER_CSRF] = csrf;
}
```

`tokenCsrf()` (líneas 101-104) lee la cookie `olimpos_csrf` con una expresión regular sobre
`document.cookie`. Que esa cookie **sí** sea legible desde JavaScript es el mecanismo, no
un descuido: es la mitad del [token CSRF de doble
envío](A0-12-sesiones-y-autenticacion.md#token-csrf-de-doble-envío), y la emite el backend
junto con la de sesión en `backend/cookies.py:93-101`, con `httponly=False` explícito y su
comentario al lado. La otra cookie, `olimpos_session`, se emite dos líneas más arriba
(84-92) con `httponly=True`, y esta función no puede verla — ni ésta ni ningún script
inyectado.

El condicional `metodo !== 'GET'` replica exactamente la lista de métodos que el backend
considera seguros (`backend/csrf.py:55`). El comentario de las líneas 199-202 explica por
qué se manda aunque el endpoint sea público: mandarlo de más no rompe nada y olvidarlo de
menos da un 403 difícil de diagnosticar.

**Tres · `credentials: 'include'`** (línea 217). Sin esta opción, `fetch` no adjunta la
cookie de sesión en un pedido a otro origen. Es el complemento obligatorio del
`allow_credentials=True` de `backend/main.py:224`; los dos son una sola decisión escrita en
dos archivos.

**Cuatro · el corte por tiempo** (línea 218, con la constante en 184).
`AbortSignal.timeout(15_000)`. `fetch` no tiene vencimiento propio: si el servidor acepta
la conexión TCP y después no contesta —se está reiniciando, la base quedó colgada— la
promesa **nunca se resuelve**, y el comentario de las líneas 174-183 cuenta el síntoma que
eso producía: la app clavada en negro en la pantalla de arranque, sin llegar nunca al
login. Los quince segundos no son un número redondo cualquiera: el plan gratuito de Neon
suspende el compute y el primer pedido después de un rato tarda varios segundos en
despertarlo.

**Cinco · el cuerpo.** `body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo)`
(línea 219). Acá el objeto de JavaScript se convierte en [JSON como
cuerpo](A0-03-http.md#json-como-cuerpo) y deja de ser un objeto para ser una cadena de
texto; los tipos de TypeScript, que ya no existían en tiempo de ejecución, tampoco dejan
rastro en el texto.

### Los bytes que efectivamente salen

Con todo eso, el pedido que el navegador escribe en el socket es, literalmente, esto:

```http
POST /api/cobros HTTP/1.1
Host: localhost:5173
Content-Type: application/json
X-CSRF-Token: 6tQ2n_A9xK0pL3sV8wYb1cE4dF7gH-jM2nP5rS8tU1w
Cookie: olimpos_session=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...; olimpos_csrf=6tQ2n_A9xK0pL3sV8wYb1cE4dF7gH-jM2nP5rS8tU1w
Content-Length: 149

{"id_socio":12,"id_tipo_membresia":3,"metodo":"EFECTIVO","id_plan_actividad":null,"numero_comprobante":null,"id_promocion":null,"saldar_deudas":true}
```

Tres observaciones sobre ese bloque de texto, y las tres importan más adelante.

La línea `Cookie:` **la escribió el navegador, no la aplicación**. `pedir()` nunca tocó
`olimpos_session`; no puede. La línea `X-CSRF-Token:` la escribió la aplicación copiando la
segunda cookie. Esa asimetría —una la pone el navegador solo, la otra hay que copiarla a
mano— es toda la defensa contra el [CSRF](A0-12-sesiones-y-autenticacion.md#csrf) resumida
en dos líneas de cabecera.

Y `Host: localhost:5173` es el puerto del servidor de desarrollo de Vite, no el 8000 del
backend. El pedido no va a donde uno pensaría. De eso se trata la escala siguiente.

---

## Proxy `/api` de Vite

*(Escala 4 del mapa.)*

**El problema, con el síntoma real.** La PWA en desarrollo se sirve desde
`http://localhost:5173` y el backend escucha en `http://127.0.0.1:8000`. Son dos
[puertos](A0-02-como-se-comunican-dos-maquinas.md#puerto) distintos y, peor, dos nombres de
host distintos. Si `fetch` apuntara directo al backend pasarían dos cosas, encadenadas:

1. El backend responde el login con `Set-Cookie` y el navegador guarda las dos cookies
   **bajo el host `127.0.0.1`**. La página, que está en `localhost`, no las puede leer:
   `document.cookie` devuelve vacío y `tokenCsrf()` devuelve `null`. El token CSRF se
   vuelve inalcanzable.
2. Además son dos **sitios** distintos, así que
   [`SameSite=lax`](A0-12-sesiones-y-autenticacion.md#cookie-y-sus-atributos) —el valor que
   pone `backend/cookies.py:74`— le prohíbe al navegador adjuntar la cookie de sesión en el
   `fetch`. La sesión nunca llega, y todo responde 401.

Eso es exactamente lo que pasó y está anotado en
`Proyecto - PWA/src/frontend/src/services/api.ts:45-55`: un login exitoso seguido de 401 en
todas las pantallas, sin ningún mensaje que explicara por qué.

**La solución.** `Proyecto - PWA/src/frontend/vite.config.ts:50-64` configura el servidor
de desarrollo como [proxy inverso](A0-03-http.md#proxy-inverso) para todo lo que empiece
con `/api`:

```ts
server: {
  proxy: {
    '/api': {
      target: destinoApi,
      changeOrigin: false,
      rewrite: (ruta) => ruta.replace(/^\/api/, ''),
    },
  },
},
```

Tres piezas, tres efectos.

**`target`** (línea 57) sale de `destinoApi`, definido en las líneas 11-12: la variable de
entorno `API_PROXY_DESTINO`, o `http://127.0.0.1:8000` por defecto. Es el único lugar del
proyecto donde aparece la dirección real del backend, y el comentario de las líneas 9-10 lo
subraya: el código de la app nunca habla con esa URL.

**`changeOrigin: false`** (línea 58) conserva la cabecera `Host: localhost:5173` al
reenviar. Si estuviera en `true`, Vite la reescribiría a `127.0.0.1:8000` y el `Set-Cookie`
de la respuesta volvería atado a ese host — es decir, volveríamos al problema original por
la puerta de atrás.

**`rewrite`** (línea 61) le saca el prefijo. El backend expone `/cobros`, no `/api/cobros`;
el `/api` existe sólo para que el proxy sepa qué derivar y qué servir como archivo de la
aplicación. Se puede verificar en el propio router: `backend/routers/cobros.py:53` declara
`APIRouter(prefix="/cobros")`, sin `/api` en ninguna parte.

**Qué gana el navegador con esto.** Que el pedido que él ve sea
`http://localhost:5173/api/cobros`: **mismo origen que la página**. La cookie es de
`localhost`, `document.cookie` la lee, `SameSite=lax` queda satisfecho y —de yapa— los
pedidos dejan de ser entre orígenes distintos, así que
[CORS](A0-12-sesiones-y-autenticacion.md#cors-y-preflight) no interviene en absoluto: no
hay `OPTIONS` previo, no hay `Access-Control-Allow-Origin` que negociar.

> **Ingeniería inversa · el proxy no es una muleta de desarrollo.**
> Lo que se optimiza acá es que **desarrollo se parezca a producción en vez de diferir de
> ella**, y está escrito en el comentario de las líneas 43-46: en producción la PWA y la
> API van a estar detrás del mismo dominio o del mismo proxy inverso, que es exactamente lo
> que esto simula. La restricción es la elegida en A0-12: la sesión de la PWA viaja en
> cookie `httponly` para que un script inyectado no se la pueda llevar, y esa elección
> arrastra las reglas de sitio de las cookies como consecuencia obligatoria.
> Las alternativas existían y las dos se descartan por un motivo concreto. **`SameSite=none`
> con `Secure`**: dejaría viajar la cookie entre sitios, pero además de exigir HTTPS en
> desarrollo reabre el CSRF para el que `lax` era la primera capa
> (`backend/cookies.py:67-70`). **Token en `localStorage`**: elimina el problema de sitio de
> un plumazo, y es justo lo que había antes y se sacó a propósito
> (`Proyecto - PWA/src/frontend/src/services/api.ts:66-77`), porque un token que JavaScript
> puede leer un script inyectado también lo puede leer y mandar afuera.
> Lo que se paga por el proxy es un salto extra en cada pedido de desarrollo —unos pocos
> milisegundos contra `localhost`, invisibles al lado de los 44 ms hasta la base— y una
> configuración más que hay que entender cuando algo no llega. El patrón es
> **colapsar el origen**: en lugar de negociar permisos entre dos sitios, hacer que sean uno.
> Y la app de escritorio no pasa por acá (comentario de las líneas 48-49): le pega directo
> al backend y se autentica con un [token
> portador](A0-12-sesiones-y-autenticacion.md#token-portador-y-authorization), que no
> depende ni de cookies ni de orígenes.

---

## Escala 5 · La red

El pedido sale del proceso del navegador, baja al sistema operativo y vuelve a subir al
proceso de Node que corre Vite; Vite reescribe la ruta y abre —o reusa— una conexión TCP
contra `127.0.0.1:8000`, donde escucha uvicorn. Los dos saltos son sobre
[loopback](A0-02-como-se-comunican-dos-maquinas.md#loopback-contra-ip-de-la-lan): no salen
de la máquina, no hay tarjeta de red de por medio y el costo es despreciable frente a
cualquier otra escala de este recorrido.

Una sola cosa vale la pena recordar acá, y es la trampa del
[puerto](A0-02-como-se-comunican-dos-maquinas.md#puerto): si el 8000 ya estaba tomado por
un uvicorn viejo, el proceso nuevo muere en silencio y quien contesta es el viejo — con las
rutas de antes. Por eso la verificación estándar de este repo no es "arrancó", es contar
las rutas que publica `/openapi.json`.

---

## Escala 6 · uvicorn, la aplicación, y lo que ya pasó antes del primer pedido

Del otro lado del socket, uvicorn parsea los bytes y llama a la aplicación ASGI declarada
en `backend/main.py:198-212`. Para cuando llega nuestro pedido, esa aplicación ya hizo tres
cosas que no tienen nada que ver con él y sin las cuales el cobro sería mucho más lento o
directamente fallaría. Están en el `lifespan` (`backend/main.py:124-195`), que corre una
sola vez, antes de aceptar el primer pedido:

- **`calentar_pool()`** (línea 146, definida en `backend/database.py:122-151`) abre tres
  conexiones contra Neon y las devuelve al pool. El comentario dice por qué: para que el
  primero que use la app no pague los 825 ms del saludo TLS. Esos 825 ms y los 44 ms de una
  consulta sobre conexión abierta son los dos números que ordenan todo el sistema
  ([A-11](A-11-rendimiento.md#base-remota)).
- **El hilo del latido** (línea 149, el cuerpo en `backend/main.py:90-113`) manda un
  `SELECT 1` cada dos minutos para que Neon no suspenda el compute y para que el NAT no dé
  por muertas las conexiones ociosas. Es un hilo y no una tarea del bucle de eventos a
  propósito: SQLAlchemy acá es síncrono y meter la consulta en el bucle lo bloquearía
  durante el viaje de ida y vuelta (comentario de las líneas 78-81).
- **`aplicar_bajas_vencidas(db)`** (línea 166) y **`generar_turnos(db)`** (línea 170),
  que son dos de los procesos que no cuelgan de ningún endpoint.

Nada de esto lo dispara el cobro. Se nombra acá porque **la escala 18 sería veinte veces
más lenta sin la primera**: cuando el handler pida una conexión, ya hay una abierta
esperando.

---

## Escalas 7, 8 y 9 · La pila de middlewares, y por qué se leen al revés

Hay tres [middlewares](A0-10-python-del-lado-del-servidor.md#middleware) registrados, en
este orden de código:

| Línea de `backend/main.py` | Qué es |
|---|---|
| 214-227 | `CORSMiddleware` |
| 233 | `middleware_csrf` |
| 252-277 | `cabeceras_de_seguridad` |

Y el pedido los atraviesa **al revés**: primero `cabeceras_de_seguridad`, después
`middleware_csrf`, después `CORSMiddleware`, y recién ahí el router. El comentario de las
líneas 229-232 lo dice con todas las letras y explica que el orden resultante es el
buscado: **rechazar un pedido sin token CSRF antes de que llegue a tocar la base**.

### Escala 7 · Las cabeceras de seguridad

`cabeceras_de_seguridad` (líneas 252-277) es el envoltorio más externo, así que en la ida
no hace nada: llama a `call_next` y espera. Su trabajo es todo en la vuelta. Se lo nombra
acá porque su posición **es** su función: al ser el último registrado, envuelve a todos los
demás, y por eso las cabeceras aparecen también en los preflight de CORS y en los rechazos
del CSRF — es decir, en respuestas que nunca llegaron al router.

### Escala 8 · El middleware de CSRF

`backend/csrf.py:63-95`. Acá nuestro pedido puede morir, y conviene ver la secuencia exacta
de decisiones:

```python
if request.method in METODOS_SEGUROS:        # línea 71
    return await call_next(request)

cookie_sesion = request.cookies.get(COOKIE_SESION)   # línea 74
if not cookie_sesion:                                 # línea 75
    return await call_next(request)

cookie_csrf = request.cookies.get(COOKIE_CSRF)        # línea 81
header_csrf = request.headers.get(HEADER_CSRF)        # línea 82

if not cookie_csrf or not header_csrf or not secrets.compare_digest(cookie_csrf, header_csrf):
    return JSONResponse(status_code=403, ...)         # líneas 87-93
return await call_next(request)                       # línea 95
```

Nuestro `POST` no está en `METODOS_SEGUROS` (línea 55) y **sí** trae la cookie de sesión,
así que llega a la comparación. Cookie y cabecera coinciden —las puso la misma sesión— y el
pedido sigue.

Dos detalles con nombre propio. `secrets.compare_digest` y no `==` (comentario de las
líneas 84-86): comparar cadenas con `==` corta apenas encuentra una diferencia, y esa
diferencia de tiempo permitiría adivinar el token carácter por carácter; `compare_digest`
tarda lo mismo siempre. Y la condición de la línea 75: **sin cookie de sesión, no hay CSRF
que frenar**. Un cliente que manda la sesión a mano en la cabecera `Authorization` —la app
de escritorio— no tiene ninguna credencial que un tercero pueda hacer viajar sin querer,
que es la definición misma del ataque. Por eso pasa de largo, y por eso el archivo
documenta la asimetría en sus líneas 31-39.

> **Ingeniería inversa · por qué middleware y no dependencia.**
> El comentario de las líneas 64-69 contesta solo: *una dependencia hay que acordarse de
> ponerla en cada endpoint nuevo, y el día que alguien se olvide, ese endpoint queda abierto
> sin que nada avise*. Se optimiza la **imposibilidad del descuido**, no la elegancia. La
> alternativa —declarar la protección en la firma de cada handler, como sí se hace con los
> permisos— tiene la ventaja de que se lee en el lugar donde importa, y la desventaja fatal
> de que su ausencia también se lee como "este endpoint no la necesita". Lo que se paga por
> el middleware es que el chequeo queda invisible desde el handler y que su alcance se
> define por una lista de métodos, no por endpoint: si algún día un `GET` escribiera en la
> base, la protección dejaría de cubrirlo sin que nadie lo note, y por eso el propio archivo
> lo anota (líneas 51-54). El patrón es **fallar cerrado por defecto**.

### Escala 9 · El middleware de CORS

`backend/main.py:214-227`. En este recorrido **no hace absolutamente nada**, y entenderlo
es más útil que verlo actuar: gracias al proxy de la escala 4, el pedido llega sin cabecera
`Origin` de otro sitio, así que `CORSMiddleware` lo deja pasar tal cual.

Existe para el caso en que la PWA se sirva desde otro origen —una prueba desde el celular
por un túnel, un despliegue con dominios separados—. Lo que sí importa siempre es la
combinación de sus líneas 216 y 224: `allow_origins` sale del `.env`
(`_origenes_cors()`, líneas 45-61) y **nunca puede ser `["*"]`**, porque con
`allow_credentials=True` la especificación de CORS prohíbe el comodín justamente para que
ninguna página arbitraria pueda hacer pedidos autenticados desde el navegador de alguien
logueado. El comentario de las líneas 50-54 registra además la diferencia con el proyecto
de referencia de la cátedra, que usa `["*"]` porque su único cliente es de escritorio y no
aplica CORS.

---

## Escalas 10 y 11 · La ruta y el esquema de entrada

El pedido llega al enrutador de FastAPI, que busca el par método + ruta en su tabla. La
entrada es `backend/routers/cobros.py:236-241`:

```python
@router.post("", response_model=CobroResponse, status_code=status.HTTP_201_CREATED)
def cobrar(
    datos: CobrarRequest,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.COBRAR_PAGOS)),
):
```

La ruta vacía se concatena con el prefijo del router (`backend/routers/cobros.py:53`), así
que la ruta completa es `POST /cobros`. Ese router está enganchado a la aplicación en
`backend/main.py:300`; olvidarse de esa línea es el error que el comentario de las líneas
283-286 señala como el más común: los endpoints existen en el código y la API responde 404
como si no se hubieran escrito nunca.

**La firma es el contrato.** Los tres parámetros no son argumentos que alguien pase: son
declaraciones de lo que la función necesita, y FastAPI las resuelve **antes** de ejecutar
una sola línea del cuerpo ([inyección de
dependencias](A0-10-python-del-lado-del-servidor.md#inyección-de-dependencias)). Las
resuelve en este orden:

1. `datos: CobrarRequest` — parsear el JSON del cuerpo y validarlo.
2. `db: Session = Depends(get_db)` — abrir la sesión de base.
3. `sesion: Sesion = Depends(requiere_accion(...))` — que a su vez depende de
   `obtener_sesion`, que a su vez depende de `get_db`.

Si cualquiera de los tres falla, **el cuerpo de `cobrar()` no corre nunca**. Ésa es la
propiedad que hace que un handler no pueda "olvidarse" de chequear permisos a mitad de
camino, y está escrita en el docstring de `backend/security.py:14-17`.

### El esquema de entrada

`CobrarRequest` está en `backend/schemas.py:730-767`. Declara siete campos y dos de ellos
tienen historia:

```python
id_socio: int
id_tipo_membresia: int
metodo: MetodoPago
monto_manual: float | None = Field(default=None, ge=1, allow_inf_nan=False)
numero_comprobante: str | None = None
saldar_deudas: bool = True
id_plan_actividad: int | None = None
id_promocion: int | None = None
```

`metodo: MetodoPago` (el enumerado está en `backend/schemas.py:622-627`) es la primera
barrera real: un cuerpo con `"metodo": "MERCADO_PAGO"` no llega al handler, se rechaza con
un 422 antes. Los cinco valores permitidos son [método de
pago](A-02-prepago-puro.md#método-de-pago) en el sentido del negocio —cómo paga la persona,
no qué proveedor procesa—, y son los mismos del tipo `metodo_pago` de la base
(`db/schema.sql:471`).

`monto_manual` lleva `ge=1` y `allow_inf_nan=False` (línea 743), y el comentario de las
líneas 740-742 dice qué pasaba sin eso: con `gt=0` pasaban `Infinity` y `NaN` —que el
parser de JSON acepta— y reventaban con un 500 al escribir en Postgres, y pasaba `0.0001`,
que redondeado quedaba **un cobro de $0,00 con la membresía activada**.

El 422 que emite Pydantic no sale tal cual: `backend/main.py:236-249` lo intercepta y
devuelve sólo `loc`, `msg` y `type`, **sin el valor recibido**. El comentario explica los
dos motivos: FastAPI copia en la respuesta el `input` que no validó, y con `Infinity` esa
copia no se puede serializar —el 422 correcto terminaba siendo un 500—; y además no
corresponde devolverle al cliente lo que mandó, que podría ser una contraseña que no
cumplía la regla.

Éste es el punto donde el sistema **recupera** lo que perdió al compilar TypeScript. El
tipo `MetodoPago` de `cobrosService.ts:19-24` desapareció al [borrarse los
tipos](A0-05-javascript-y-typescript.md#tipado-estático-y-borrado-de-tipos); lo que llega
al backend es texto. `CobrarRequest` es la primera y única validación que existe de verdad.

---

## Escalas 12 y 13 · La sesión de base y la verificación de sesión

**`get_db`** (`backend/database.py:154-165`) es un generador: abre una `SessionLocal`, la
entrega con `yield` y la cierra en el `finally`, pase lo que pase. Que la cierre en el
`finally` es lo que garantiza que la conexión vuelva al pool incluso si el handler lanza
una excepción; sin eso, cada 409 se llevaría una conexión y el pool se agotaría solo. Ojo
con lo que "cerrar" significa acá: devuelve la conexión al pool, no la destruye — es la
misma distinción que documenta `backend/database.py:148-151`.

**`obtener_sesion`** (`backend/security.py:80-142`) es la escala que decide si este pedido
tiene dueño. Su secuencia:

```python
token = token_header or token_cookie          # línea 108
if not token: raise _NO_AUTENTICADO           # líneas 109-110
payload = decodificar_token(token)            # línea 112
if not payload: raise _NO_AUTENTICADO         # líneas 113-114
id_usuario = int(payload.get("sub", ""))      # línea 117
usuario = db.get(Usuario, id_usuario)         # línea 121
if usuario is None or not usuario.activo or usuario.bloqueado: raise   # líneas 122-123
if usuario.debe_cambiar_password: raise 401 con otro mensaje           # líneas 129-134
roles = payload.get("roles") or []            # línea 136
return Sesion(usuario=..., roles=..., id_socio=..., id_profesor=...)   # líneas 140-142
```

La línea 108 es el corazón de los [dos mecanismos de
sesión](A-07-autenticacion.md#los-dos-mecanismos-de-sesión-y-x-client-type): se aceptan los
dos transportes y **la cabecera gana sobre la cookie**, porque es explícita. En nuestro
recorrido no hay cabecera `Authorization`, así que `token` es el valor de
`olimpos_session`, el mismo que aparecía en la línea `Cookie:` de la escala 3.

`decodificar_token` (`backend/auth.py:194-204`) verifica la firma y el vencimiento de una
sola llamada, y devuelve `None` para los tres casos de fallo —inválido, alterado o
vencido— porque quien llama no necesita distinguirlos y al cliente no le conviene saber
cuál fue. El mecanismo de la firma es
[HMAC](A0-11-criptografia-aplicada.md#hmac-y-firma-simétrica), y lo único que separa a
quien puede firmar de quien no es la [clave
secreta](A0-11-criptografia-aplicada.md#clave-secreta).

La línea 121 merece su propio párrafo, porque es una consulta que a primera vista sobra: el
[JWT](A0-12-sesiones-y-autenticacion.md#jwt) ya trae la identidad, ¿para qué ir a la base?
El docstring lo contesta en las líneas 102-106: **el token es inmutable hasta que expira
—ocho horas— y hace falta que desactivar o bloquear una cuenta tenga efecto ya**. Sin esa
consulta, alguien a quien le acaban de dar de baja seguiría cobrando el resto de la
jornada. Es una consulta por clave primaria, la más barata que existe, y es la única
revocación parcial que un JWT admite: la total es rotar la clave, que mata todas las
sesiones a la vez.

La línea 129 es la que dejó afuera a la cuenta `dueno` del sistema real: un reseteo que no
se completó le dejó `debe_cambiar_password` en `true`, y desde entonces el backend rechaza
cualquier token suyo con ese 401 específico.

Los `roles` de la línea 136 vienen firmados adentro del token y **no se recalculan**: se
derivaron una sola vez, en el login ([A-06](A-06-los-seis-roles.md#derivación-de-roles)).
Lo mismo `id_socio` e `id_profesor` (líneas 141-142), que son [identidad
firmada](A-07-autenticacion.md#identidad-firmada).

---

## Escala 14 · La dependencia de permisos

`requiere_accion(Accion.COBRAR_PAGOS)` es una **fábrica**: se ejecuta cuando Python define
la función —una vez, al importar el módulo— y devuelve la dependencia que FastAPI va a
llamar en cada pedido. Está en `backend/security.py:197-214`:

```python
def dependencia(sesion: Sesion = Depends(obtener_sesion)) -> Sesion:
    if not puede_accion(sesion.roles, accion):
        raise HTTPException(403, "No tenés permisos para realizar esta acción.")
    return sesion
```

`puede_accion` (`backend/permisos.py:358-361`) resuelve la pregunta en una línea:

```python
return any(PERMISOS.get(rol, {}).get("acciones", {}).get(accion, False) for rol in roles)
```

Recibe una **lista** de roles y no uno solo porque los roles se acumulan —el dueño del
gimnasio suele entrenar ahí, y entonces es `dueno` y `socio` a la vez— y la regla, escrita
en el comentario de las líneas 335-338, es que un rol de más nunca puede quitar permisos.
Con una sesión de Recepcionista, la búsqueda llega a `backend/permisos.py:224`:
`Accion.COBRAR_PAGOS: True`. Pasa.

Vale la pena mirar las dos filas de al lado en esa misma tabla, porque dibujan el límite
exacto del mostrador: `Accion.VER_INGRESOS: False` (línea 223) y
`Accion.GESTION_PROMOCIONES: False` (línea 225). El Recepcionista **cobra** pero no ve la
facturación del mes ni inventa descuentos — sí puede aplicar uno que ya existe, que es por
lo que la vista pide `gestionPromociones` sólo para el panel de administración
(`CobrosView.tsx:75` y `369`) y no para el desplegable de promociones del cobro
(`CobrosView.tsx:502-516`). El hook que lo consulta es `usePuedeAccion`
(`Proyecto - PWA/src/frontend/src/hooks/usePermisos.ts:21-24`), y su propio archivo aclara
en las líneas 6-8 que eso decide qué se **dibuja**, no qué se permite.

Este es el punto donde la copia de la [matriz de
permisos](A-08-autorizacion.md#matriz-de-permisos) que vive en el backend hace su trabajo.
La copia del frontend ya había hecho el suyo en la escala 1, decidiendo qué botones
dibujar; si alguien fuerza el store desde las herramientas del navegador y hace aparecer el
botón, **choca acá**
([A-08](A-08-autorizacion.md#el-frontend-esconde-el-backend-rechaza)).

Una diferencia que conviene tener presente: este endpoint pide una **acción**
(`requiere_accion`), no un nivel de sección. `GET /cobros/socio/{id}`, dos secciones más
arriba en el mismo archivo (`backend/routers/cobros.py:192`), pide
`requiere_seccion(Seccion.COBROS)` con el nivel por defecto, que es LECTURA. Y anular un
pago (`backend/routers/cobros.py:493`) pide `Seccion.COBROS` con nivel TOTAL. Los tres
grados están en el mismo archivo, a doscientas líneas de distancia.

---

## Escala 15 · El handler, línea por línea

Recién ahora corre la primera línea del cuerpo de `cobrar()`
(`backend/routers/cobros.py:237-486`). Lo que sigue es el orden real de ejecución del
camino feliz, sin promoción, sin comprobante y sin abono de actividad.

### 15.1 · ¿Existe el socio? (líneas 257-259)

```python
socio = db.get(Socio, datos.id_socio)
if socio is None:
    raise HTTPException(404, "El socio no existe.")
```

`db.get` es la forma barata: busca por clave primaria y, si el objeto ya está en el mapa de
identidad de la sesión, ni siquiera consulta
([A0-09](A0-09-el-orm.md#sesión-y-mapa-de-identidad)). Acá consulta, porque la sesión recién
se abrió y lo único que trajo hasta ahora es el `Usuario`.

### 15.2 · La regla del prepago (líneas 261-266)

```python
renovacion = estado_renovacion(db, socio.id_socio)
if not renovacion.puede:
    raise HTTPException(409, f"{_nombre_socio(socio)}: {renovacion.motivo}")
```

Va **antes que todo lo demás**, y el comentario de la línea 262 dice por qué: ningún otro
dato cambia la respuesta. Si el socio tiene un período en curso, da lo mismo qué plan, qué
promoción y qué comprobante venían: el cobro no ocurre. Es la escala 16 y tiene sección
propia.

### 15.3 · ¿Existe el plan y está vivo? (líneas 268-275)

Dos chequeos y dos códigos distintos: 404 si el plan no existe, **400** si existe pero está
dado de baja. Son situaciones diferentes y el mostrador necesita distinguirlas: la primera
es un id mal formado, la segunda es un plan que alguien retiró del catálogo y que todavía
aparece en la pantalla de otra persona.

### 15.4 · El precio (líneas 277-288)

```python
precio = float(tipo.precio_actual)
if datos.monto_manual is not None:
    if not any(r in sesion.roles for r in ("dueno",)):
        raise HTTPException(403, "Solo el dueño puede cobrar un monto distinto al del plan.")
    precio = datos.monto_manual
```

El precio **sale de la base**, de `Tipo_Membresia.precio_actual`, nunca del pedido. La
excepción legítima —un precio pactado distinto, un ajuste— existe, y está cerrada con un
chequeo de rol escrito a mano en la línea 283. Nótese que no usa `puede_accion`: compara el
rol directamente. Es la única comprobación de autorización de todo el recorrido que no pasa
por la matriz, y vale anotarla como tal.

`float(tipo.precio_actual)` es el primer cruce de tipos del lado del servidor: la columna es
`numeric(10,2)` (`db/schema.sql:366`) y el ORM la entrega como `Decimal`. Se convierte acá y
se vuelve a convertir en cada salida (`backend/routers/cobros.py:76`, `98`) porque los
esquemas declaran `float`.

### 15.5 · La promoción (líneas 290-337)

No corre en nuestro camino, pero tiene cuatro rechazos que conviene tener ubicados, porque
son la mitad de los errores que declara el proceso 46:

| Condición | Líneas | Respuesta |
|---|---|---|
| Vino promoción **y** monto manual | 298-307 | 400 · "Elegí una sola cosa" |
| La promoción no existe | 309-312 | 404 |
| No está vigente el día de inicio del período | 317-326 | 400, con el motivo separado |
| Es de otra sede | 329-334 | 400 |

La línea 315 (`inicio_periodo = date.today()`) y su comentario son el enganche con el resto
del sistema: la promoción tiene que estar vigente **cuando arranca el período cobrado**, y
como no hay adelantos, ese día es siempre hoy
([A-02](A-02-prepago-puro.md#sin-cobros-por-adelantado)). El chequeo lo hace `esta_vigente`
(`backend/routers/promociones.py:58-68`), que valida dos cosas distintas —la baja lógica y
la ventana de fechas— y por eso el mensaje de error distingue cuál de las dos falló: una se
arregla reactivando la promoción y la otra cambiándole las fechas.

El cálculo lo hace `precio_con_promo` (`backend/routers/promociones.py:88-103`),
**importado** desde el router de promociones en `backend/routers/cobros.py:51`. El
comentario de las líneas 47-50 explica la importación: es la única definición de cuánto
descuenta una promoción, y duplicarla acá haría que el día que cambie la regla, la vista
previa muestre un número y el cobro registre otro.

### 15.6 · Las dos escrituras (líneas 352-415)

Acá empieza lo irreversible, y conviene verlo junto con los índices de la base, porque dos
líneas del handler existen **sólo** para no chocar contra ellos.

```python
hoy = date.today()
_membresia_vigente(db, socio.id_socio)   # línea 359
inicio = hoy                              # línea 360

while (db.query(Membresia)
       .filter(Membresia.id_socio == socio.id_socio,
               Membresia.fecha_inicio == inicio)
       .first()) is not None:             # líneas 375-378
    inicio = inicio + timedelta(days=1)   # línea 379
```

**La línea 359 protege el índice `membresia_una_activa_uidx`** (`db/schema.sql:1095-1096`),
que es un [índice único parcial](A0-08-sql-indices-y-planes.md#índice-único-parcial) sobre
`(id_socio) WHERE estado = 'ACTIVA'`: un socio no puede tener dos membresías ACTIVA a la
vez. El punto es que `estado_renovacion` **no marca nada**: si encuentra una ACTIVA con
`fecha_vencimiento` pasada, devuelve "sí, se puede renovar" y deja la fila como está
(`backend/renovacion.py:95-105`). Es decir, en el instante previo al INSERT hay, en la base,
una fila ACTIVA del mismo socio. `_membresia_vigente`
(`backend/routers/cobros.py:106-128`) recorre las ACTIVA y le pone `VENCIDA` a las que ya
pasaron su fecha (líneas 124-125); esos cambios quedan pendientes en la sesión y salen como
`UPDATE` en el `flush` siguiente. Sin esa llamada, el INSERT que sale del `flush` de la
línea 390 violaría el índice y el mostrador vería un 500 sin explicación: el nombre del
constraint queda en el registro del servidor, y la pantalla sólo dice el código
([qué ve la pantalla con un 500](B-03-personal.md#36-dar-de-baja-a-un-empleado)).

**Las líneas 375-379 protegen el otro índice**, `Membresia_id_socio_fecha_inicio_idx`
(`db/schema.sql:1093`), que es único sobre `(id_socio, fecha_inicio)`. El comentario de las
líneas 362-374 cuenta el caso real que lo dispara: se cobra, se anula el pago por un error
—lo que deja la membresía en `CANCELADA` pero con `fecha_inicio` de hoy— y se vuelve a
cobrar el mismo día. La membresía nueva chocaría. La decisión es **correr el inicio al
primer día libre en vez de fallar**, y el comentario la justifica en términos del
mostrador: el socio está enfrente pagando, y negarle el cobro por un detalle de índices
sería absurdo; un día de corrimiento no le quita nada, porque el vencimiento se calcula
desde ahí (línea 386).

Después vienen las dos escrituras:

```python
membresia = Membresia(..., fecha_inicio=inicio,
                      fecha_vencimiento=inicio + timedelta(days=tipo.duracion_dias),
                      estado="ACTIVA")          # líneas 381-388
db.add(membresia)
db.flush()                                      # línea 390

pago = Pago(id_socio=..., id_membresia=membresia.id_membresia, ...,
            es_adelanto=False, estado="CONFIRMADO", ...)   # líneas 398-413
db.add(pago)
db.flush()                                      # línea 415
```

El `flush` de la línea 390 es lo que hace posible la línea 400. [`flush` no es
`commit`](A0-09-el-orm.md#flush-contra-commit): manda el INSERT a la base y recibe de
vuelta el `id_membresia` que generó la secuencia, sin cerrar la transacción. Sin él,
`membresia.id_membresia` sería `None` y el `Pago` quedaría huérfano.

`es_adelanto=False` en la línea 408 es literal y siempre: la columna existe en el esquema
(`db/schema.sql:476`) con un `CHECK` que la referencia y con su propio comentario
(`db/schema.sql:496-499`) explicando que quedó en false desde el 2026-09-16. Es memoria de
una regla que cambió, no código olvidado.

Y `fecha_pago=datetime.now()` (línea 405) usa el reloj del servidor. La misma decisión
aparece en `_a_membresia_out` (`backend/routers/cobros.py:89-92`), donde el comentario la
explica: si el frontend calculara los días restantes con su propio reloj, un navegador con
la fecha cambiada podría mostrarse al día estando vencido.

---

## Escala 16 · La regla de negocio

`backend/renovacion.py:56-105`, `estado_renovacion()`. Es el archivo más corto del backend
que decide más plata.

La regla, tal como la escribió el dueño el 2026-09-16 y está documentada en las líneas 1-33
del archivo: **no se cobran períodos por adelantado**. El motivo no es técnico: quien paga
ocho meses juntos se queda con el precio de hoy, y si la cuota aumenta en el medio el
gimnasio cobra esos meses a precio viejo. Con el adelanto permitido, lo único que separaba
a un socio de congelar su precio era tener la plata junta.

La función devuelve un `EstadoRenovacion` (líneas 43-50) con tres campos: `puede`, `motivo`
y `desde`. Chequea seis cosas, en este orden:

| # | Condición | Líneas | Qué devuelve |
|---|---|---|---|
| 1 | Hay una baja programada | 61-68 | No · "Tiene la baja programada para el dd/mm/aaaa" |
| 2 | Hay una membresía `SUSPENDIDA` | 70-79 | No · "La cuota está en pausa" |
| 3 | No hay ninguna `ACTIVA` | 81-87 | **Sí** |
| 4 | La `ACTIVA` no vence nunca | 89-93 | No · "no hay nada que renovar" |
| 5 | La `ACTIVA` vence hoy o después | 95-103 | No · con `desde` = vencimiento + 1 día |
| 6 | La `ACTIVA` ya venció | 105 | **Sí** |

El orden importa y no es casual: es el mismo criterio de precedencia que gobierna el estado
del socio ([A-09](A-09-estados-derivados.md)). La baja programada gana sobre todo, porque
cobrarle a alguien que ya dijo que se va sería cobrar un período que nadie va a usar
(comentario de las líneas 59-60).

La línea 95 es la que define el día de corte exacto:

```python
if vigente.fecha_vencimiento >= hoy:
```

Con `>=`, una membresía que vence **hoy** todavía bloquea la renovación, y el `desde` que
se devuelve es `fecha_vencimiento + 1 día` (línea 96). Es la misma decisión que hace que un
socio quede "Vencido" recién el día siguiente al vencimiento: el día del vencimiento
todavía está pago. Invertir ese `>=` por un `>` no rompería ninguna prueba y le regalaría un
día a cada socio, o se lo quitaría, según hacia dónde se invierta.

**El motivo viaja redactado.** Las líneas 100-102 arman el texto en castellano rioplatense
completo, con las dos fechas, y ese texto llega hasta la pantalla sin que nadie lo vuelva a
escribir: el campo `motivo_no_renovar` de `EstadoCuentaOut` (`backend/schemas.py:854`), el
`motivoNoRenovar` de `obtenerCuotaDeSocio` (`cobrosService.ts:341`) y el párrafo de
`CobrosView.tsx:480-484` son la misma cadena.

> **Ingeniería inversa · la regla en tres capas, y por qué está tres veces.**
> Lo que se optimiza es que **ninguna pantalla ofrezca un botón que la API va a rechazar**.
> La restricción es que hay tres caminos que cobran una cuota —el mostrador, el pago online
> y su acreditación— y dos pantallas que la ofrecen, en dos aplicaciones distintas. La
> alternativa simple era dejar la regla sólo en el handler: es más económica y el resultado
> sería un 409 en la cara del Recepcionista después de haber contado la plata. La
> alternativa opuesta —calcular la regla en cada pantalla— la duplicaría en tres lenguajes y
> garantizaría que se desincronice. Lo elegido es **una definición, consumida de dos
> formas**: `estado_renovacion()` es la única implementación, el handler la usa para
> rechazar (`backend/routers/cobros.py:263-266`) y las pantallas la reciben resuelta, con su
> motivo, a través de tres campos de `EstadoCuentaOut` (`backend/schemas.py:853-855`). Lo
> que se paga son tres consultas más en cada lectura del estado de cuenta, y una respuesta
> más gorda. El patrón es **decidir en el servidor, mostrar en el cliente**, y su marca
> reconocible es un campo booleano que viaja junto a la cadena que lo explica.

---

## Escala 17 · El ORM, con las consultas contadas

Hasta acá se habló de "consultar la base" en abstracto. Ésta es la cuenta real de un cobro
sin promoción, sin comprobante y sin abono. Cada fila es **un viaje de ida y vuelta** contra
São Paulo, uno después del otro, sobre la misma conexión.

| # | Línea que la dispara | Sentencia |
|---|---|---|
| 1 | `backend/security.py:121` | `SELECT` de `Usuario` por clave primaria |
| 2 | `backend/routers/cobros.py:257` | `SELECT` de `Socio` por clave primaria |
| 3 | `backend/bajas.py:52-55`, vía `backend/renovacion.py:62` | `SELECT` de `Baja` pendiente del socio, `LIMIT 1` |
| 4 | `backend/renovacion.py:70-73` | `SELECT` de `Membresia` `SUSPENDIDA`, `LIMIT 1` |
| 5 | `backend/renovacion.py:81-85` | `SELECT` de `Membresia` `ACTIVA` ordenada por vencimiento, `LIMIT 1` |
| 6 | `backend/routers/cobros.py:268` | `SELECT` de `Tipo_Membresia` por clave primaria |
| 7 | `backend/routers/cobros.py:114-119`, vía `359` | `SELECT` de todas las `Membresia` `ACTIVA` del socio |
| 8 | `backend/routers/cobros.py:375-378` | `SELECT` de `Membresia` por `(id_socio, fecha_inicio)` |
| 9 | `backend/routers/cobros.py:390` | `UPDATE` de las vencidas (si las hubo) **+** `INSERT` en `Membresia` |
| 10 | `backend/routers/cobros.py:415` | `INSERT` en `Pago` |
| 11 | `backend/routers/cobros.py:465` | `COMMIT` |
| 12 | `backend/routers/cobros.py:466` | `SELECT` de `Pago` (el `refresh`) |
| 13 | `backend/routers/cobros.py:467` | `SELECT` de `Membresia` (el `refresh`) |
| 14 | `backend/routers/cobros.py:469`, vía `_nombre_socio` | `SELECT` de `Persona` (carga perezosa de `Socio.persona`) |

Son **catorce viajes**. A los 44 ms medidos y anotados en `backend/database.py:52`, eso es
alrededor de 620 ms, y ahí está prácticamente todo el tiempo que la persona del mostrador
percibe. El trabajo de Python en el medio —comparar tres fechas, sumar días, construir dos
objetos— no llega a un milisegundo sumado. Ésa es, en una sola operación medible, la
conclusión que ordena el sistema entero: [el cuello es la red, nunca
Python](A-11-rendimiento.md#el-cuello-es-la-red-nunca-python).

Tres notas sobre esa tabla.

**La 14 es una carga perezosa y no molesta.** `_nombre_socio(socio)` toca `socio.persona`,
que es una relación declarada en `backend/models.py:339` y que nadie había cargado. Una
sola consulta, una sola vez. Lo que sí sería un problema es esta misma jugada adentro de un
bucle sobre cien socios: ahí se llama [N+1](A0-09-el-orm.md) y es el motivo por el que los
listados de este sistema resuelven las relaciones en lote
([A-11](A-11-rendimiento.md#listado-en-lote)).

**Dos accesos a relaciones NO consultan**, y conviene saber por qué. En la línea 477,
`_a_pago_out(pago)` lee `pago.socio`; en la 478, `_a_membresia_out(membresia)` lee
`membresia.tipo`. Los dos objetos ya están en el mapa de identidad de la sesión —se
cargaron en los viajes 2 y 6—, y una relación de muchos-a-uno hacia una clave primaria se
resuelve mirando ahí antes de consultar
([A0-09](A0-09-el-orm.md#sesión-y-mapa-de-identidad)). Es la misma propiedad que hace que
`socio` de la línea 257 y `pago.socio` de la 477 sean **el mismo objeto de Python**, no dos
copias.

**Los viajes 12 y 13 se pueden discutir.** `db.refresh()` releé la fila completa después
del `COMMIT`. Alcanzaba con los valores que el código ya tenía en memoria; lo que compra es
que todo valor generado por la base —`fecha_pago` tiene un `DEFAULT now()` en
`db/schema.sql:473`— llegue a la respuesta tal como quedó escrito, y no como lo calculó
Python. Dos viajes de ida y vuelta por una garantía de coherencia: es un precio que en este
endpoint se paga y en un listado no se pagaría.

---

## Escala 18 · La conexión, el commit y São Paulo

Todas esas sentencias viajan por **una** conexión, sacada del pool que configura
`backend/database.py:92-113`. Que exista y esté caliente es lo que separa este cobro de uno
que empiece con 825 ms de saludo TLS. Las tres piezas de esa configuración
—`pool_recycle=240` (línea 95), los cuatro `keepalives` de TCP (líneas 105-108) y
`pool_size=10` (línea 96)— están explicadas en `A-11`; acá sólo importa el hecho: cuando el
handler pidió la sesión, ya había una conexión abierta contra Neon esperando.

Y después está la línea 465:

```python
db.commit()
```

Antes de esa línea, los dos INSERT y el UPDATE ya están **en la base**, mandados por los
`flush`, pero dentro de una transacción abierta. Nadie más los ve; si el proceso muere acá,
desaparecen. Después de esa línea existen, son visibles para cualquier otra sesión y
sobreviven a un corte de luz
([A0-07](A0-07-bases-de-datos-relacionales.md#transacción-acid-commit-y-rollback)).

Que el cobro sea **una sola transacción** es lo que el docstring del handler llama "que sea
atómico importa más acá que en ningún otro lado" (`backend/routers/cobros.py:249-251`), y
la razón es simétrica: un `Pago` sin `Membresia` deja al socio pagando sin acceso, y una
`Membresia` sin `Pago` le regala el mes. Cuando además se cobra el abono de actividad, la
`Inscripcion_Actividad` entra en la misma transacción
(`backend/routers/cobros.py:443-444`), y por eso el combo es **un solo pedido** y no dos
encadenados desde la vista (comentario en `CobrosView.tsx:310-317`).

Hay una consecuencia de esto que vale para todo el repo y está anotada en `CLAUDE.md`: como
el `commit` vive **adentro** del handler, envolver una llamada a este endpoint en una
transacción externa y cerrarla con `rollback()` **no revierte nada**. El commit de adentro
ya se llevó también las filas de prueba. Ya pasó una vez, con un escenario de horarios y
turnos que quedó escrito en la base del dueño.

---

## La vuelta

### 18' · La respuesta se arma

`backend/routers/cobros.py:469-486`. Primero el mensaje, en castellano y listo para mostrar:

```python
partes = [f"Cobro registrado: ${precio:,.2f} a {_nombre_socio(socio)}."]
```

Después el objeto de salida, `CobroResponse` (`backend/schemas.py:820-832`), con seis
campos propios más los dos objetos anidados. Tres de esos campos —`promocion`,
`precio_lista` y `descuento` (líneas 830-832)— existen por un motivo que el comentario de
las líneas 827-829 explica: el comprobante tiene que poder mostrar **las tres cifras**, y
con el total solo no se puede reconstruir cuánto se descontó.

El `response_model=CobroResponse` de la línea 236 hace que FastAPI valide y serialice esa
salida: los `date` se convierten a `"2026-12-24"`, los `Decimal` que quedaran a número, y
cualquier campo que el esquema no declare **no sale**. Eso último es una protección real:
si mañana alguien devolviera el objeto `Pago` del ORM en crudo, el esquema recortaría lo que
no corresponde en vez de filtrarlo.

### 9'-7' · Los middlewares, al revés

La respuesta sube por la pila en orden inverso al de la ida. `CORSMiddleware` no le agrega
nada (no hay origen que autorizar). `middleware_csrf` ya devolvió su `call_next` y no toca
la respuesta. Y `cabeceras_de_seguridad` (`backend/main.py:267-277`), que en la ida no hizo
nada, acá hace todo su trabajo: agrega `X-Content-Type-Options`, `X-Frame-Options`,
`Referrer-Policy`, `Permissions-Policy` y una `Content-Security-Policy` de
`default-src 'none'`, que es correcta porque esta API sólo devuelve JSON y videos — no hay
HTML propio que necesite cargar nada. Usa `setdefault` en todas, así que nunca pisa una
cabecera que una respuesta haya puesto a propósito.

### 4' y 3' · El proxy y el `fetch`

Vite recibe el 201 y lo reenvía al navegador tal cual, bajo `localhost:5173`. En el
navegador, la promesa que había quedado suspendida en
`Proyecto - PWA/src/frontend/src/services/api.ts:210` se resuelve, el bucle de eventos
reanuda la función y sigue en la línea 230
([A0-04](A0-04-el-navegador-por-dentro.md#bucle-de-eventos-tarea-y-microtarea-promesa-y-asyncawait)).

```ts
if (respuesta.status === 204) return undefined as T;   // línea 230
let datos: unknown = null;
try { datos = await respuesta.json(); } catch { if (respuesta.ok) return undefined as T; }
if (!respuesta.ok) { ... throw new ServiceError(...) }  // líneas 239-245
return datos as T;                                      // línea 247
```

El `as T` de la línea 247 es el momento exacto en que TypeScript deja de saber de qué está
hablando: `datos` es `unknown`, viene de la red, y esa aserción le pone un nombre de tipo
sin verificar nada. Es la [frontera de confianza del
tipo](A0-05-javascript-y-typescript.md#frontera-de-confianza-del-tipo) cruzada hacia
adentro, y es aceptable precisamente porque del otro lado hubo un esquema que sí validó.

### 2' · El remapeo a la vista

`Proyecto - PWA/src/frontend/src/services/cobrosService.ts:251-274` traduce el `snake_case`
de la API al `camelCase` de la pantalla y aplana lo que hacía falta aplanar. Un solo detalle
merece atención, en la línea 255:

```ts
vencimiento: d.membresia.fecha_vencimiento ?? '',
```

`fecha_vencimiento` es opcional en el esquema (`backend/schemas.py:789`) porque existen
planes sin vencimiento; el service colapsa ese `null` a cadena vacía para que la vista no
tenga que distinguir dos ausencias distintas.

### 1' · El re-render

`CobrosView.tsx:250-265`:

```tsx
.then((resultado) => {
  showSnack(`Cobrado: ${resultado.membresia.plan} hasta el ${formatearFecha(parsearFecha(resultado.membresia.vencimiento))}` + ..., colors.statusOk);
  setIdPromocionElegida('');
  cargarCuenta(socioSeleccionado.idSocio);
})
```

Tres efectos, y cada uno dispara su propio re-render.

**`showSnack`** (`Proyecto - PWA/src/frontend/src/store/uiStore.ts:65-72`) escribe en el
store global y arma un temporizador de cuatro segundos. El componente `Snackbar`
(`Proyecto - PWA/src/frontend/src/components/ui/Snackbar.tsx:9-23`), montado una sola vez en
`App.tsx:84`, está suscrito a ese pedazo del store
([A0-06](A0-06-react.md#store-global-fuera-de-react)), así que se vuelve a ejecutar y ahora
devuelve el cartel en vez de `null`. React compara el árbol nuevo con el viejo y toca
únicamente los nodos que cambiaron
([A0-06](A0-06-react.md#árbol-virtual-y-reconciliación)).

`parsearFecha` (`Proyecto - PWA/src/frontend/src/utils/fechas.ts:28-31`) convierte
`"2026-12-24"` en un `Date` a medianoche **local**, partiendo la cadena a mano en lugar de
pasársela al constructor. No es manía: `new Date("2026-12-24")` se interpreta como UTC y en
Argentina se ve como el 23.

**`setIdPromocionElegida('')`** limpia la promoción, y el comentario de las líneas 258-260
dice por qué: dejarla puesta haría que el siguiente socio que atienda el mostrador se lleve
el descuento sin que nadie lo haya decidido. Como es estado local
([A0-06](A0-06-react.md#props-estado-local-y-re-render)), cambiarlo vuelve a ejecutar
`CobrosView` entera; y como el efecto de las líneas 214-230 depende de
`idPromocionElegida`, ese efecto corre de nuevo, ve la cadena vacía y limpia la vista previa
(líneas 215-218) sin pedir nada a la red.

Ese efecto, además, está escrito **después** de la `const tipoElegido` de la línea 207 y no
junto al resto de los efectos del archivo, y el comentario de las líneas 209-213 explica por
qué: el arreglo de dependencias se evalúa durante el render, así que ponerlo arriba leería
`tipoElegido` antes de su declaración y tiraría un error en tiempo de ejecución que el
compilador no ve ([A0-05](A0-05-javascript-y-typescript.md#zona-muerta-temporal-tdz)). El
mismo cuidado está tomado en el efecto de las líneas 163-172.

**`cargarCuenta`** (`CobrosView.tsx:112-121`) dispara **un segundo recorrido completo**,
esta vez `GET /cobros/socio/{id}` contra `backend/routers/cobros.py:188-229`. Acá se cierra
el círculo del capítulo: ese handler vuelve a llamar a `estado_renovacion` (línea 210) y
ahora devuelve `puede_renovar: false` con el motivo "La cuota está paga hasta el
24/12/2026. Se puede renovar desde el 25/12/2026", porque el cobro que acabamos de seguir
creó el período que la regla protege. Cuando la respuesta llegue, `CobrosView.tsx:486`
dejará de dibujar el botón y `CobrosView.tsx:480-484` mostrará ese texto.

El botón desapareció por la misma regla que casi no lo deja apretar.

Y el `.finally()` de la línea 265 pone `ocupado` en `false`, que es el tercer re-render y la
liberación del botón — si es que todavía existe.

---

## Los finales que no son el feliz

Todo lo anterior describe el 201. Estos son los otros, con la línea que los levanta y qué
ve la persona.

| Código | Qué pasó | Línea que lo levanta | Qué ve quien cobra |
|---|---|---|---|
| **403** | Falta el token CSRF o no coincide | `backend/csrf.py:87-93` | "Token CSRF ausente o inválido. Volvé a iniciar sesión." |
| **401** | Sin token, token inválido o vencido | `backend/security.py:73-77` | Vuelve al login, con el motivo |
| **401** | La cuenta fue desactivada o bloqueada | `backend/security.py:122-123` | Ídem |
| **401** | La cuenta tiene que cambiar la contraseña | `backend/security.py:129-134` | Ídem, con ese mensaje |
| **403** | El rol no tiene `cobrarPagos` | `backend/security.py:209-212` | "No tenés permisos para realizar esta acción." |
| **422** | El cuerpo no valida | `backend/main.py:236-249` | El `msg` del primer error |
| **404** | El socio no existe | `backend/routers/cobros.py:258-259` | "El socio no existe." |
| **409** | Período en curso, pausa o baja programada | `backend/routers/cobros.py:264-266` | El nombre del socio y el motivo redactado |
| **404** | El plan no existe | `backend/routers/cobros.py:269-270` | "El plan no existe." |
| **400** | El plan está dado de baja | `backend/routers/cobros.py:271-275` | "El plan '…' está dado de baja…" |
| **403** | Monto manual sin ser dueño | `backend/routers/cobros.py:283-287` | "Solo el dueño puede cobrar…" |
| **400** | Monto manual **y** promoción | `backend/routers/cobros.py:303-307` | "Elegí una sola cosa…" |
| **404 / 400** | Problemas con la promoción | `backend/routers/cobros.py:310-334` | Cuatro mensajes distintos |
| **409** | Comprobante ya registrado | `backend/routers/cobros.py:342-350` | "Ya se registró un pago con el comprobante…" |
| **0** | No hubo respuesta (red caída, vencimiento) | `Proyecto - PWA/src/frontend/src/services/api.ts:224-227` | "El servidor tardó demasiado" / "No se pudo conectar" |

Todos terminan en el mismo lugar del lado de la vista: `ServiceError`
(`Proyecto - PWA/src/frontend/src/services/api.ts:13-21`) lanzado desde `pedir()`, cazado en
el `.catch()` de `CobrosView.tsx:264` y convertido en texto por `mensajeDeError`
(`api.ts:31-33`), que devuelve el mensaje del backend si es un `ServiceError` y uno genérico
si es cualquier otra cosa — para no filtrar detalles internos a la pantalla.

**El 401 tiene además un camino propio.** En
`Proyecto - PWA/src/frontend/src/services/api.ts:241-244`:

```ts
if (respuesta.status === 401 && !SIN_SESION_PROPIA.includes(ruta.split('?')[0])) {
  avisarSesionCaida?.(mensaje);
}
```

`SIN_SESION_PROPIA` (línea 166) son `/login`, `/cambiar-password` y `/me`: las tres rutas
donde un 401 no significa "se te cayó la sesión". En cualquier otra, se llama al callback
que `App.tsx:73-78` registró, que limpia el store y muestra el motivo en un cartel; después
`ProtectedRoute` redirige al login. El comentario de `api.ts:149-152` explica por qué es un
callback y no una navegación directa: este módulo no sabe de React ni del enrutador, y
atarlo a ellos haría que un service no se pueda usar fuera de una pantalla.

### El 409 es el rechazo interesante

Si esta socia hubiera tenido la cuota paga hasta el 3 de octubre, el recorrido habría muerto
en `backend/routers/cobros.py:264-266`, después de cinco viajes a la base y antes de
escribir una sola fila. Y el mostrador no habría visto un error críptico: habría visto el
nombre de la socia, dos puntos, y "La cuota está paga hasta el 03/10/2026. Se puede renovar
desde el 04/10/2026: no se cobran períodos por adelantado."

Pero lo más probable es que ni siquiera hubiera podido apretar el botón, porque la misma
regla ya había llegado a la pantalla en la lectura previa. El 409 existe para quien llame a
la API sin pasar por la pantalla, para la carrera entre dos recepcionistas cobrándole a la
misma persona, y para la ventana entre que se cargó la pantalla y se apretó el botón. Es la
red de seguridad, no el mecanismo. Ésa es, entera, la idea de **el frontend esconde, el
backend rechaza** ([A-08](A-08-autorizacion.md#el-frontend-esconde-el-backend-rechaza)).

---

## La misma escalera en la app de escritorio

El mismo cobro, desde la PC de recepción, recorre las mismas escalas del backend y unas
distintas del lado del cliente. Vale la pena verlo porque muestra qué escalas son
esenciales y cuáles eran consecuencia del navegador.

| Escala | PWA | Flet |
|---|---|---|
| Vista | `CobrosView.tsx:233-268` · `cobrarMembresiaClick` | `Flet/Proyecto/app/views/cobros.py:760-793` · `_cobrar_membresia()` |
| Capa intermedia | — | `Flet/Proyecto/app/state.py:954-979` · `cobrar_membresia()` |
| Service | `services/cobrosService.ts:222-275` · `cobrar()` | `Flet/Proyecto/app/api_client.py:626-627` · `cobrar()` |
| Cliente HTTP | `services/api.ts:194-247` · `pedir()` | `Flet/Proyecto/app/api_client.py:143-162` · `_pedir()` |
| Sesión | Cookie `httponly` + cabecera CSRF | `Authorization: Bearer` + `X-Client-Type: escritorio` (`api_client.py:90-97`) |
| Proxy | `vite.config.ts:50-64` | — (le pega directo al backend) |
| CSRF | Se exige | **No aplica** (`backend/csrf.py:75-79`) |
| Caché | — | Servir y refrescar, invalidado entero por cada escritura (`api_client.py:366-368`) |

Las dos vistas dicen lo mismo, y no por casualidad: el comentario sobre limpiar la
promoción después de cobrar está en `CobrosView.tsx:258-260` y **palabra por palabra** en
`Flet/Proyecto/app/views/cobros.py:781-783`. Eso es el contrato de [aplicaciones
gemelas](A-03-dos-apps-un-backend.md) funcionando.

La diferencia que más se nota es la última fila. `_post` en
`Flet/Proyecto/app/api_client.py:366-368` es literalmente esto:

```python
def _post(path: str, body: dict | None = None) -> dict:
    limpiar_cache()
    return _pedir("POST", path, body)
```

Cualquier escritura tira el caché **entero**, no la ruta tocada
([A-11](A-11-rendimiento.md#servir-y-refrescar)). Cobrar una cuota cambia el estado de
cuenta del socio, la lista de socios, el panel del mostrador, el tablero y la actividad
reciente; llevar la cuenta de qué invalida qué sería una segunda fuente de verdad que se
desincroniza sola. La PWA no necesita nada de esto porque no cachea: `cargarCuenta` vuelve
a preguntar y listo.

---

## Discrepancias encontradas

Tres, marcadas acá y no corregidas en su archivo original, según la sección 7 de
`PROMPT-ZARPADO.md`.

**1 · `Inscripcion_Actividad.id_membresia` no existe.** Tres comentarios justifican que el
combo membresía + abono viaje en un solo pedido diciendo que
"`Inscripcion_Actividad.id_membresia` es `NOT NULL`":
`Proyecto - PWA/src/frontend/src/services/cobrosService.ts:9-14`,
`backend/schemas.py:751-754` y `Flet/Proyecto/app/state.py:976-978`. Esa columna **no está**
en la tabla: `db/schema.sql:639-647` declara siete columnas y ninguna es `id_membresia`, y
el comentario de la tabla no la menciona. El propio router lo dice al revés y en presente en
`backend/routers/cobros.py:418-421`: *"La inscripción ya NO cuelga de la membresía
(`Inscripcion_Actividad` perdió `id_membresia`): es del socio"*. **Gana el código y el
esquema.** La decisión de mandar un solo pedido sigue siendo correcta, pero por otro motivo,
que el mismo comentario del router explica: las dos filas se crean en la misma transacción y
con la misma vigencia (`backend/routers/cobros.py:439-440`) para que un abono nunca
sobreviva a la cuota que da acceso al gimnasio. Los tres comentarios quedaron viejos.

**2 · `saldar_deudas` es un campo muerto que la PWA sigue mandando.** El service lo incluye
en el cuerpo (`cobrosService.ts:247`) y el esquema lo declara con valor por defecto
(`backend/schemas.py:748`), pero el handler **no lo lee en ninguna línea**: el subsistema de
deudas se retiró junto con la tabla, como registran `backend/models.py:527-530` y
`backend/routers/cobros.py:253-255`. Lo mismo vale para `deudas_saldadas`, que siempre sale
como lista vacía (`backend/routers/cobros.py:480`), y para `deuda_total: 0.0`
(`backend/routers/cobros.py:223`). Se buscó con `grep -rn "saldar_deudas"` sobre `backend/`,
`Proyecto - PWA/src/frontend/src` y `Flet/Proyecto/app`: aparece exactamente dos veces, la
declaración del esquema y el envío de la PWA. La app de escritorio ya no lo manda
(`Flet/Proyecto/app/state.py:970-979`). Es residuo de compatibilidad, y el propio handler lo
dice: los campos se mantienen en la respuesta por las apps, pero vacíos
(`backend/routers/cobros.py:212-216`). No cambia ningún comportamiento.

**3 · El nombre de archivo de este capítulo: resuelto.** Este capítulo se escribió primero
como `A-04-recorrido-completo-de-un-pedido.md`, que no es el nombre que fija el contrato de
vocabulario. Como siete enlaces ya escritos —en `A0-02`, `A0-03` (dos), `A0-05` (dos) y
`A0-12`— apuntaban a `A-04-recorrido-de-un-pedido.md#proxy-api-de-vite`, el archivo se
renombró al nombre del contrato. El ancla `#proxy-api-de-vite` existe y resuelve.

Lo que **no** es una discrepancia: la línea DFD del proceso 46
(`PROCESOS-LOGICOS-REQUERIDOS.md:446-451`) se verificó contra el código y coincide entera.
Declara escrituras en `Membresia`, `Pago` e `Inscripcion_Actividad`, que son exactamente las
tres de las líneas 389, 414 y 443; y declara lecturas de `Usuario`, `Socio`, `Persona`,
`Baja`, `Membresia`, `Tipo_Membresia`, `Promocion`, `Pago` (por `numero_comprobante`),
`Plan_Actividad` y `Actividad`, que son las diez que el recorrido toca —la última,
`Actividad`, en `backend/routers/cobros.py:456`—. Sus rechazos declarados son los once de la
tabla de finales infelices.

---

## Por qué está hecho así

Cerrando con la regla 2.7 aplicada al recorrido completo, no a una escala.

**Qué se optimizaba.** Que **una operación de mostrador tenga un solo camino, y que ese
camino sea el mismo desde las dos aplicaciones**. Se puede verificar: `POST /cobros` es el
único endpoint que crea una `Membresia` por cobro presencial, lo llaman las dos apps con el
mismo cuerpo, y las reglas —el precio, la promoción, el prepago, los dos índices— viven una
sola vez, del lado del servidor.

**Qué restricciones acorralaban.** Cuatro, y cada una dejó su marca en el recorrido. La base
a 44 ms por consulta, que hace que las catorce consultas sean el costo real y el cálculo no
importe. El navegador, que obliga a cookie, CSRF y proxy para que la sesión sea robusta a un
script inyectado. Dos aplicaciones gemelas, que obligan a que toda regla esté del lado del
servidor o haya que escribirla dos veces. Y el mostrador con cola, que fija el presupuesto
de pasos: buscar, elegir plan, confirmar, listo.

**Qué alternativas se descartaron.** Tres, dichas en serio.

*Calcular el monto en el cliente y mandarlo.* Es lo más directo: la pantalla ya conoce el
precio y el descuento, y mandarlos ahorra dos consultas y todo el bloque de promoción del
handler. Se descartó porque convierte el precio en un dato del cliente, y un dato del
cliente es un dato editable: el cobro de $1 sobre una membresía de $30.000 quedaría en la
base indistinguible de uno legítimo. El costo de haberla descartado son las consultas 6 y,
cuando hay promoción, una más.

*Guardar el estado "debe" en una columna de `Socio`.* Evitaría `estado_renovacion` entera y
sus tres consultas. Se descartó por lo mismo que no existe la tabla `Deuda`: un estado
guardado **se vuelve mentira al día siguiente sin que nadie escriba nada**, y habría que
tener un proceso que lo recorra todas las noches y confiar en que corrió
([A-09](A-09-estados-derivados.md)). El costo de haberla descartado son esas tres consultas
en cada lectura de estado de cuenta.

*Dejar que la regla del prepago viva sólo en el handler.* Es lo más económico de escribir y
produce exactamente el error que el dueño no quiere: el 409 llega después de que el
Recepcionista contó la plata. Se descartó, y el costo es que `EstadoCuentaOut` carga tres
campos de más y que la regla se ejecuta dos veces por cobro — una para informar, otra para
rechazar.

**Qué se pagó.** Latencia por seguridad y por coherencia: catorce viajes donde un diseño
descuidado haría ocho. Verbosidad: un cobro toca once archivos. Y duplicación deliberada, la
misma que documentan `backend/permisos.py:7-19` y el contrato de componentes gemelos.

**Cómo se llaman los patrones.** De arriba hacia abajo: **capa anticorrupción** (el
service), **colapsar el origen** (el proxy), **fallar cerrado por defecto** (el CSRF como
middleware), **inyección de dependencias** (las barreras en la firma), **decidir en el
servidor, mostrar en el cliente** (`puede_renovar` y su motivo), **derivar en vez de
almacenar** (el estado del socio), **unidad de trabajo** (una transacción, un `commit`) y
**soft delete** (anular un pago en vez de borrarlo). Los ocho son jugadas conocidas; lo que
hace que este recorrido valga la pena leerlo es que las ocho están en la misma cadena y cada
una tapa un agujero que dejó la anterior.

---

## Con qué se conecta

- **Existe por culpa de…** el [Proxy `/api` de Vite](#proxy-api-de-vite) está para que la
  página y la API sean el mismo sitio y `SameSite=lax` deje viajar la cookie
  ([A0-12](A0-12-sesiones-y-autenticacion.md#cookie-y-sus-atributos)).
- **Es el mismo problema que…** las catorce consultas de este cobro y los 825 ms de una
  conexión nueva son viajes de ida y vuelta, a dos escalas distintas
  ([A-11](A-11-rendimiento.md#base-remota)).
- **Es la misma idea que…** el [Service del frontend](#service-del-frontend) y la matriz de
  permisos triplicada: una definición en un solo lugar, consumida desde varios
  ([A-08](A-08-autorizacion.md#matriz-de-permisos)).
- **Se contradice con…** el `disabled` del botón, el 409 del handler y los dos índices
  únicos de `Membresia` frenan lo mismo desde tres capas, y sólo el último es
  infalsificable ([A0-08](A0-08-sql-indices-y-planes.md#índice-único-parcial)).
- **Existe por culpa de…** el 409 de `estado_renovacion()` existe porque el prepago prohíbe
  dos períodos superpuestos, no porque el cobro esté mal formado
  ([A-02](A-02-prepago-puro.md#sin-cobros-por-adelantado)).
- **Es la misma idea que…** el botón que no se dibuja cuando `puede_renovar` es falso y el
  botón de patologías que se omite en vez de deshabilitarse: la pantalla no ofrece lo que la
  API no va a dar ([A-08](A-08-autorizacion.md#el-frontend-esconde-el-backend-rechaza)).
