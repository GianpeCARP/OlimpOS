# A0-03 · HTTP

> **Piso de este capítulo: el paquete viajando.** Bajamos del texto del pedido a los
> bytes exactos que lo componen, y de ahí a cómo esos bytes se entregan al flujo TCP que
> [A0-02](A0-02-como-se-comunican-dos-maquinas.md#tcp-y-el-viaje-de-ida-y-vuelta-rtt) ya
> construyó. Un escalón más abajo —segmentos, IP, el cable— ya lo explicó A0-02 y no se
> vuelve a bajar acá.

Este capítulo define siete cosas: el **pedido y la respuesta** como texto, el **método**
y la idempotencia, el **código de estado**, la **cabecera**, la **falta de estado**, el
**JSON del cuerpo** y el **proxy inverso**. Todo lo que OlimpOS hace entre una pantalla y
la base pasa por acá: no hay ninguna otra forma de que la PWA o la app de escritorio le
hablen al backend.

---

## El problema del que nació

En 1989 Tim Berners-Lee trabajaba en el CERN con un problema de oficina, no de
informática: los documentos técnicos estaban repartidos en máquinas distintas, cada una
con su propio protocolo de acceso, y para leer uno había que saber de antemano en cuál
estaba y con qué programa se bajaba. La propuesta que escribió ese año —y que implementó
entre 1990 y 1991— reducía todo eso a una operación: pedir un documento por su nombre.

El protocolo que salió de ahí, hoy llamado HTTP/0.9, es casi ridículo de simple. El
cliente abre una conexión, escribe **una línea**:

```
GET /hypertext/WWW/TheProject.html
```

y el servidor devuelve el HTML crudo y **cierra la conexión**. No hay versión, no hay
cabeceras, no hay códigos, no hay más método que `GET`. El fin del documento se marca
cerrando el caño: cuando la conexión muere, el archivo terminó.

Eso alcanzó unos años y después se rompió en cuatro lugares a la vez, y cada rotura dejó
una pieza que hoy seguimos usando:

| Lo que se rompió | Lo que agregó |
|---|---|
| No había forma de decir "eso no existe": el error llegaba como un HTML que parecía un documento. | El **código de estado**. |
| No había forma de decir qué tipo de archivo venía, así que no se podían servir imágenes. | Las **cabeceras**, empezando por `Content-Type`. |
| No había forma de mandar datos al servidor, sólo de pedirlos. | Los **métodos** además de `GET`, empezando por `POST`. |
| Cerrar la conexión para marcar el final obligaba a un saludo TCP nuevo por cada imagen de una página. | `Content-Length` y las **conexiones persistentes**. |

HTTP/1.0 (RFC 1945, mayo de 1996) formalizó las tres primeras. HTTP/1.1 (RFC 2068 en
1997, reescrito como RFC 2616 en 1999, y otra vez como RFC 9110–9112 en 2022) agregó la
cuarta, hizo **obligatoria** la cabecera `Host` —sin la cual no se pueden alojar dos
sitios en una misma dirección IP— y dejó las conexiones abiertas por defecto. HTTP/2
(RFC 7540, 2015) y HTTP/3 (RFC 9114, 2022) cambiaron cómo se **codifican** esos mismos
mensajes —marcos binarios, compresión de cabeceras, multiplexación— pero no cambiaron lo
que un pedido *es*: método, ruta, cabeceras y cuerpo.

**OlimpOS habla HTTP/1.1 y nada más.** Eso no es una suposición: el servidor de este
sistema escribe la versión literalmente en cada respuesta, en
`backend/.venv/Lib/site-packages/uvicorn/protocols/http/httptools_impl.py:30-35`
(`_get_status_line`), que arma la primera línea como
`b"HTTP/1.1 " + código + b" " + frase + b"\r\n"`.

---

## Pedido y respuesta HTTP

Un pedido HTTP son **dos bloques de texto** separados por una línea en blanco: una línea
inicial, cero o más cabeceras, la línea en blanco, y el cuerpo. La respuesta tiene
exactamente la misma forma; lo único que cambia es la primera línea. No hay nada más. Si
podés escribir ese texto a mano, podés hablarle a cualquier servidor web del mundo.

> **↓ Capa 1 — el pedido escrito entero.** Salteable si ya lo sabés.

Tomemos un pedido real de este repo: el mostrador cobra una cuota. La pantalla llama a
`cobrar()` en `Proyecto - PWA/src/frontend/src/services/cobrosService.ts:222-248`, que
arma el cuerpo y se lo pasa a `pedir()` de
`Proyecto - PWA/src/frontend/src/services/api.ts:194-248`. Lo que sale del navegador es
este texto, y nada más que este texto:

```http
POST /api/cobros HTTP/1.1
Host: localhost:5173
Content-Type: application/json
X-CSRF-Token: 9tQm3Zx1pK7sVb0LcR2aYh4NfE6uWd8J
Cookie: olimpos_session=eyJhbGciOiJIUzI1NiIs...; olimpos_csrf=9tQm3Zx1pK7sVb0LcR2aYh4NfE6uWd8J
Origin: http://localhost:5173
Accept: */*
Content-Length: 149

{"id_socio":12,"id_tipo_membresia":3,"metodo":"EFECTIVO","id_plan_actividad":null,"numero_comprobante":null,"id_promocion":null,"saldar_deudas":true}
```

Parte por parte:

- **`POST`** es el método. Declara qué se pretende hacer (`#metodo-http-e-idempotencia`).
- **`/api/cobros`** es la ruta, o *path*. Es sólo una parte de la URL: la URL completa es
  `http://localhost:5173/api/cobros`, y el esquema (`http`) más el host y el puerto
  (`localhost:5173`) **no viajan en la línea inicial** —el esquema no viaja en absoluto
  y el host viaja en su propia cabecera `Host`—. Si hubiera parámetros de consulta
  (`?desde=2026-01-01`) irían pegados acá, después de un signo de pregunta.
- **`HTTP/1.1`** es la versión, la que el servidor devuelve en el espejo.
- Las **cabeceras**, una por línea, en formato `Nombre: valor` (`#cabecera-http`).
- La **línea en blanco**, que no es decoración: es el único marcador de que las cabeceras
  terminaron y empieza el cuerpo.
- El **cuerpo**, acá JSON (`#json-como-cuerpo`). Son exactamente 149 bytes, que es lo que
  declara `Content-Length`.

De esas cabeceras, dos las escribe el código de este repo y el resto las pone el
navegador solo:

| Cabecera | Quién la pone |
|---|---|
| `Content-Type: application/json` | `api.ts:197`, siempre, incluso en los `GET` que no llevan cuerpo. |
| `X-CSRF-Token` | `api.ts:203-206`, sólo cuando el método no es `GET`. |
| `Cookie` | El navegador, porque el `fetch` pide `credentials: 'include'` en `api.ts:217`. |
| `Host`, `Origin`, `Content-Length`, `Accept`, `User-Agent`, `Accept-Encoding` | El navegador, sin que nadie se lo pida. |

La app de escritorio arma el mismo pedido con otras cabeceras: sin cookie, con
`X-Client-Type: escritorio` y `Authorization: Bearer <token>`, en
`Flet/Proyecto/app/api_client.py:90-97` (`HEADERS_CLIENTE`, `_headers()`). Es el mismo
protocolo, escrito distinto — por qué son dos formas y no una se explica en
[los dos mecanismos de sesión y `X-Client-Type`](A-07-autenticacion.md#los-dos-mecanismos-de-sesión-y-x-client-type).

La respuesta al pedido de arriba tiene la misma anatomía, con la primera línea invertida:

```http
HTTP/1.1 201 Created
content-type: application/json
content-length: 612
x-content-type-options: nosniff
x-frame-options: DENY
referrer-policy: no-referrer
permissions-policy: camera=(), microphone=(), geolocation=()
content-security-policy: default-src 'none'; frame-ancestors 'none'

{"pago":{"id_pago":88,"id_socio":12,"monto":30000.0,"metodo":"EFECTIVO", ... }}
```

El `201` sale del decorador de la ruta,
`backend/routers/cobros.py:236` (`@router.post("", response_model=CobroResponse,
status_code=status.HTTP_201_CREATED)`). Las cinco cabeceras de seguridad las agrega un
middleware que envuelve todas las respuestas, en `backend/main.py:252-277`
(`cabeceras_de_seguridad`). El `content-type` y el `content-length` los pone la capa de
respuesta de Starlette, en `starlette/responses.py:59-79` de la carpeta `.venv`, que
completa los dos si la aplicación no los escribió.

> **↓ Capa 2 — los bytes exactos: `\r\n`, la línea en blanco y dónde termina el mensaje.**
> Salteable si ya lo sabés.

"Una línea por cabecera" es una descripción cómoda; el byte dice otra cosa. El separador
de línea de HTTP **no es** el salto de línea de Unix. Es **CRLF**: dos bytes, `0x0D`
(retorno de carro) y `0x0A` (avance de línea), heredados de los protocolos de texto de
ARPANET, que a su vez lo heredaron de las teleimpresoras. Un servidor que recibe un
pedido con `\n` solo puede aceptarlo por tolerancia, pero el protocolo pide los dos.

La "línea en blanco" es entonces, literalmente, `\r\n\r\n`: el CRLF que cierra la última
cabecera, seguido de un CRLF que no tiene nada delante. Ese patrón de cuatro bytes es lo
que el servidor busca para saber que las cabeceras se terminaron.

Se puede ver armado byte a byte del lado de la respuesta, en
`uvicorn/protocols/http/httptools_impl.py:486-510`:

```python
content = [STATUS_LINE[status_code]]
for name, value in headers:
    ...
    content.extend([name, b": ", value, b"\r\n"])
...
content.append(b"\r\n")
self.transport.write(b"".join(content))
```

`STATUS_LINE` es un diccionario precalculado al importar el módulo, con las 500 líneas de
estado posibles ya convertidas a bytes (`httptools_impl.py:40`); cada cabecera se escribe
como nombre, `b": "`, valor y CRLF; y el último `content.append(b"\r\n")` es la línea en
blanco. Después de eso, el cuerpo.

**Y acá aparece el problema de fondo.** TCP no entrega mensajes: entrega un flujo de
bytes ordenado y sin costuras. El servidor no recibe "un pedido"; recibe bytes que van
llegando. Nada en TCP le dice dónde termina uno y empieza el siguiente. HTTP tiene que
resolverlo él mismo, y para el cuerpo tiene exactamente dos formas de hacerlo:

1. **`Content-Length`.** "Después de la línea en blanco vienen 149 bytes y ni uno más."
   Exige conocer el largo antes de empezar a escribir.
2. **`Transfer-Encoding: chunked`.** El cuerpo llega en trozos, cada uno precedido por su
   largo en hexadecimal, y un trozo de largo cero marca el final. Sirve cuando el largo
   no se sabe de antemano.

Uvicorn elige entre las dos en `httptools_impl.py:505-509`: si la aplicación no declaró
ninguna de las dos cabeceras, usa `chunked` — salvo que el método sea `HEAD` o el código
sea `204` o `304`, casos en los que **no hay cuerpo** y no hay nada que enmarcar. En
OlimpOS la rama de `chunked` casi nunca se usa, porque las respuestas son JSON completo
en memoria y Starlette ya calculó su largo (`starlette/responses.py:63-73`). Las
respuestas de este sistema van con `Content-Length`.

Las cabeceras, en cambio, no se enmarcan con un largo: se enmarcan con el `\r\n\r\n`.
Por eso un valor de cabecera **no puede contener un salto de línea**, y por eso uvicorn
rechaza con `RuntimeError` cualquier nombre o valor que traiga bytes de control, en
`httptools_impl.py:488-491` contra las expresiones regulares de `httptools_impl.py:28-29`.
Sin ese chequeo, un dato del usuario metido en una cabecera podría cerrar el bloque y
escribir cabeceras propias — el ataque que se llama *response splitting*.

> **↓ Capa 3 — cómo ese texto se convierte en paquetes.** Salteable si ya lo sabés.
> Este es el piso del capítulo.

`self.transport.write(b"".join(content))` no escribe en la red. Escribe en el *transport*
de asyncio, que copia los bytes al buffer de envío del socket en el núcleo del sistema
operativo. De ahí en adelante manda TCP, con las reglas que ya vimos en
[A0-02](A0-02-como-se-comunican-dos-maquinas.md#tcp-y-el-viaje-de-ida-y-vuelta-rtt): el
núcleo corta el flujo en segmentos del tamaño que permita el camino, los numera, los
manda, espera acuse y retransmite los que se perdieron.

Tres consecuencias que importan para leer este repo:

- **El corte en segmentos no respeta el pedido.** Las cabeceras pueden llegar partidas al
  medio de una palabra, y el cuerpo puede empezar en el mismo segmento que la última
  cabecera. Por eso el analizador del servidor es incremental: se le va dando lo que
  llega y él avisa cuando completó cada pieza. En este backend ese analizador es
  `httptools` —un enlace a `llhttp`, el analizador de Node escrito en C—, elegido
  automáticamente porque está instalado, en
  `uvicorn/protocols/http/auto.py:6-15`. Entra por `data_received`
  (`httptools_impl.py:167-171`), que le pasa los bytes crudos al analizador, y sale por
  las devoluciones de llamada `on_message_begin`, `on_url`, `on_header`,
  `on_headers_complete`, `on_body` y `on_message_complete`
  (`httptools_impl.py:219-306`). Ahí es donde el texto deja de ser texto y se convierte
  en un diccionario de Python.
- **Un pedido mal formado se corta antes de existir.** Si el analizador tira
  `HttpParserError`, uvicorn responde 400 y cierra
  (`httptools_impl.py:172-175`). Ese 400 no lo emite ninguna línea de `backend/`: el
  pedido nunca llegó a ser un pedido.
- **La conexión se reusa.** HTTP/1.1 deja el caño abierto por defecto, así que el saludo
  de TCP y el de TLS se pagan una vez y los pedidos siguientes viajan encima. Es la misma
  economía que hace que abrir una conexión nueva a la base cueste 825 ms y reusar una
  cueste 44 (→ [A-11](A-11-rendimiento.md#base-remota)). Del lado del cliente, lo único
  que corta esa espera es un reloj: `AbortSignal.timeout(TIMEOUT_MS)` en `api.ts:218`,
  con `TIMEOUT_MS = 15_000` en `api.ts:182`, y `TIMEOUT = 10` segundos en
  `Flet/Proyecto/app/api_client.py:43`. Sin eso, un servidor que acepta la conexión y no
  contesta deja la promesa colgada para siempre — que es exactamente lo que dejaba la PWA
  clavada en la pantalla de arranque, según el comentario de `api.ts:172-181`.

Piso alcanzado. Los bytes ya son un paquete y el paquete ya es de A0-02.

---

## Método HTTP e idempotencia

El método es la primera palabra de la primera línea, y es **una declaración de
intención**: qué se pretende que pase con el recurso que nombra la ruta. El servidor no
está obligado por el protocolo a respetarla —nada impide escribir un `GET` que borre—,
pero todo lo que está entre el cliente y el servidor sí actúa según lo que el método
promete: los intermediarios guardan en caché los `GET`, los navegadores reintentan solos
un `GET` y no un `POST`, y las defensas que veremos abajo se saltean los métodos que
prometen no tocar nada.

Los cuatro que usa este sistema:

| Método | Qué promete | Cuántas veces aparece en `backend/routers/` |
|---|---|---|
| `GET` | Traer algo sin cambiar nada. | 70 |
| `POST` | Provocar un cambio, sin prometer qué pasa si se repite. | 70 |
| `PUT` | Dejar el recurso en el estado que se manda. | 14 |
| `DELETE` | Que el recurso deje de estar. | 11 |

*(Contados con `grep -o "@router\.\(get\|post\|put\|delete\|patch\)" backend/routers/`.
No hay ni un `PATCH`, ni un `HEAD`, ni un `OPTIONS` declarado a mano.)*

**Idempotente** quiere decir que repetir la operación deja el sistema en el mismo estado
que hacerla una sola vez. Es una propiedad del **estado resultante**, no de la respuesta:
una operación puede ser idempotente y contestar distinto la segunda vez. Por definición
`GET`, `PUT` y `DELETE` lo son, y `POST` no.

Hay tres lugares de este repo donde eso deja de ser teoría.

**El `POST` que no es idempotente, y lo que cuesta.** `POST /cobros`
(`backend/routers/cobros.py:236-241`, `cobrar()`) crea una `Membresia` y un `Pago`. Si el
mismo pedido llega dos veces —un doble click en el mostrador, un reintento del
navegador— se cobra dos veces. Como el método no puede prometer nada, la protección hay
que construirla: el número de comprobante es `UNIQUE` en la base
(`db/schema.sql:494`) y además se chequea antes para dar un mensaje legible, devolviendo
409 en `cobros.py:337-350`; y `Membresia` tiene un índice único sobre
`(id_socio, fecha_inicio)` (`db/schema.sql:1108`) que impide dos períodos que arranquen
el mismo día. El patrón se llama **clave de idempotencia**: el cliente aporta un
identificador del intento y el servidor lo usa para reconocer el repetido.

**El `POST` que sí es idempotente en el estado.** `POST /cobros/pagos/{id_pago}/anular`
(`cobros.py:489-518`, `anular_pago()`) marca el pago `CANCELADO` y cancela la membresía
que habilitaba. Repetirlo no cambia nada más, pero **no calla**: contesta 400 con "Ese
pago ya estaba anulado" (`cobros.py:504-508`). La decisión es deliberada y va en la misma
dirección que el resto del sistema: el estado es idempotente, la respuesta es informativa.
Quien atiende se entera de que el segundo click no hizo nada, en vez de quedarse pensando
que anuló dos cosas.

**El `PUT` que se comporta como un `PATCH`.** `PUT /socios/{id_socio}`
(`backend/routers/socios.py:491-597`, `editar_socio()`) debería, por la semántica del
método, dejar al socio exactamente como dice el cuerpo: lo que no viene, se borra. Hace
lo contrario a propósito. Lee `datos.model_fields_set` en `socios.py:521` y toca
**únicamente los campos que vinieron en el pedido**: ausente se conserva, vacío borra.

> **Ingeniería inversa.** Lo que se estaba optimizando es no perder datos en silencio. La
> restricción que acorralaba: hay dos formularios de socio, uno en cada app, y no piden
> los mismos campos —la PWA no pedía `objetivo` ni `observaciones` y Flet sí—, de modo
> que un `PUT` con semántica de reemplazo hacía que editar el teléfono desde una app
> borrara lo que la otra había cargado, sin error y sin aviso (`socios.py:507-513`). Las
> alternativas eran dos: declarar la ruta como `PATCH`, que es el método hecho para esto
> y habría dejado la semántica limpia; o obligar a los dos formularios a mandar siempre
> los 14 campos. La primera obliga a tocar las dos apps y a mantener dos métodos para una
> pantalla; la segunda deja el mismo agujero, sólo que dependiendo de que nadie se olvide
> un campo al agregar el siguiente. Se eligió quedarse con `PUT` y cambiarle el
> comportamiento. **Lo que se paga es la mentira del método:** el verbo dice "reemplazá"
> y el código hace "fusioná", y eso no lo detecta ningún compilador ni ninguna
> herramienta de HTTP — sólo el comentario de `socios.py:507-513` y este párrafo. La
> idempotencia, en cambio, sobrevive: mandar dos veces el mismo cuerpo parcial deja el
> mismo estado.

Hay una última consecuencia del método, y es de seguridad. `GET`, `HEAD`, `OPTIONS` y
`TRACE` se llaman **métodos seguros** justamente porque prometen no cambiar nada, y el
middleware que protege contra falsificación de pedidos los deja pasar de largo sin
mirarlos: `METODOS_SEGUROS` en `backend/csrf.py:55` y el corte en `csrf.py:71-72`. El
comentario de `csrf.py:52-54` dice en voz alta el contrato que eso implica: *"si algún
día un `GET` escribe en la base, este middleware deja de protegerlo"*. La lista del
cliente es la misma —`api.ts:203` sólo agrega el token cuando el método no es `GET`—, y
el mecanismo de la defensa se explica en
[el token CSRF de doble envío](A0-12-sesiones-y-autenticacion.md#token-csrf-de-doble-envío).

---

## Código de estado

La primera línea de la respuesta lleva un entero de tres dígitos y una frase. La frase es
para las personas y ningún cliente la lee; el número es el contrato. El esquema de tres
dígitos no se inventó para HTTP: ya lo usaban FTP y SMTP, donde una respuesta como `550`
o `250` cumplía la misma función —que un programa pueda decidir sin interpretar texto—.

El primer dígito es la clase, y es lo único que un cliente tiene que entender para no
romperse con un código que no conoce:

| Clase | Significa | Quién tiene el problema |
|---|---|---|
| `1xx` | Informativo, seguí esperando. | nadie |
| `2xx` | Salió bien. | nadie |
| `3xx` | Está en otro lado. | nadie |
| `4xx` | El pedido está mal. | el cliente |
| `5xx` | El pedido estaba bien y el servidor falló. | el servidor |

La frontera entre `4xx` y `5xx` es la más útil de todas y la que más se equivoca: dice de
quién es la culpa. Un 404 le dice al cliente "no insistas con esto"; un 503 le dice "lo
mismo, más tarde, puede funcionar".

> **↓ Capa 2 — el número escrito en la línea de respuesta.** Salteable si ya lo sabés.
> Este es el piso del concepto.

El número no se formatea cuando llega el pedido: está precalculado. En
`uvicorn/protocols/http/httptools_impl.py:30-40`, el servidor construye al importar el
módulo un diccionario con **los 500 códigos posibles**, de 100 a 599, cada uno ya
convertido a la línea de bytes completa:

```python
def _get_status_line(status_code: int) -> bytes:
    try:
        phrase = http.HTTPStatus(status_code).phrase.encode()
    except ValueError:
        phrase = b""
    return b"".join([b"HTTP/1.1 ", str(status_code).encode(), b" ", phrase, b"\r\n"])

STATUS_LINE = {status_code: _get_status_line(status_code) for status_code in range(100, 600)}
```

Un 409 de este sistema es, byte por byte, `HTTP/1.1 409 Conflict\r\n`, y sale de una
búsqueda en ese diccionario en `httptools_impl.py:486`. Los códigos que no tienen frase
estándar salen con la frase vacía y funcionan igual: el cliente lee el número.

### Los códigos que este sistema usa de verdad

Contados sobre las constantes `status.HTTP_*` escritas en `backend/`, sin contar la
carpeta `.venv`:

| Código | Veces | Qué significa acá |
|---|---:|---|
| `404 NOT_FOUND` | 88 | El id no existe, o no existe **para quien pregunta**. |
| `400 BAD_REQUEST` | 60 | El pedido es válido como JSON pero la operación no tiene sentido en este estado. |
| `409 CONFLICT` | 46 | El pedido es correcto y choca con algo que ya está. |
| `201 CREATED` | 38 | Se creó una fila. |
| `403 FORBIDDEN` | 23 | Hay sesión, y esa sesión no puede hacer esto. |
| `204 NO_CONTENT` | 7 | Se hizo, y no hay nada que devolver. |
| `401 UNAUTHORIZED` | 3 | No hay sesión válida. |
| `402 PAYMENT_REQUIRED` | 2 | `backend/routers/portal.py:1390` y `:1398`. |
| `429 TOO_MANY_REQUESTS` | 1 | `backend/routers/auth_router.py:76-80`. |
| `502 BAD_GATEWAY` | 1 | `backend/routers/pagos_online.py:168`. |
| `503 SERVICE_UNAVAILABLE` | 1 | `backend/routers/pagos_online.py:122`. |
| `422` | 1 | El único escrito como número suelto, en `backend/main.py:249`. |

> **⚠ Discrepancia, para documentar y no corregir.** El contrato de vocabulario de esta
> masterclass dice que los códigos de este sistema son nueve: 200, 400, 401, 403, 404,
> 409, 422, 429 y 500. El código emite **doce** distintos, y de esos nueve hay dos que
> nunca aparecen escritos: el `200` es el que FastAPI pone por defecto cuando nadie
> declara otro, y el `500` **no existe en ninguna línea de `backend/`** —es lo que
> devuelve el servidor cuando un endpoint revienta con una excepción que nadie atajó, y
> por eso no se busca grepeando—. Faltan en esa lista el `201`, el `204`, el `402`, el
> `502` y el `503`. Gana el código.

Dos observaciones que se leen en esa tabla y no en ningún comentario. La primera: **el
`409` es el código característico de este sistema**. Cuarenta y seis usos, contra
veintitrés `403`, es el perfil de una aplicación donde la mayoría de los rechazos no son
de permisos sino de reglas de negocio con estado —ya existe, ya está pago, ya está
anulado, todavía no vence—. La segunda: **no hay ni un `3xx`**. Un backend que sólo
devuelve datos no redirige a nadie; quien decide a qué pantalla ir es el enrutado del
lado del cliente, que no pasa por la red.

### El 409 al cobrar por adelantado

`POST /cobros` con un socio que ya tiene un período en curso responde
**409 Conflict**. La línea que lo levanta es `backend/routers/cobros.py:264-266`:

```python
renovacion = estado_renovacion(db, socio.id_socio)
if not renovacion.puede:
    raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                        detail=f"{_nombre_socio(socio)}: {renovacion.motivo}")
```

La decisión de qué se puede cobrar no está ahí: está en `backend/renovacion.py:56-105`
(`estado_renovacion()`), que devuelve una estructura de tres campos —`puede`, `motivo`,
`desde`— y contempla cuatro casos: baja programada (`renovacion.py:61-68`), cuota en
pausa (`renovacion.py:70-78`), membresía sin vencimiento (`renovacion.py:88-93`) y cuota
paga hasta una fecha que todavía no pasó (`renovacion.py:95-103`). El *porqué* de la
regla —quien paga meses adelantados congela el precio— se explica en
[sin cobros por adelantado](A-02-prepago-puro.md#sin-cobros-por-adelantado); lo que
importa acá es **por qué 409 y no otro número**.

Ni 400 ni 403 servirían. El cuerpo del pedido es impecable: el socio existe, el plan
existe, el método de pago es válido, y mandado mañana el mismo pedido idéntico va a
funcionar. No es "el pedido está mal" (400) ni "vos no podés hacer esto" (403): es "esto
choca con el estado actual del recurso", que es la definición exacta del 409. Y como el
conflicto se resuelve solo con el paso del tiempo, el cliente puede decirle a la persona
*cuándo* va a poder — para eso viaja `renovacion.desde` y por eso el mensaje del `detail`
ya trae la fecha armada (`renovacion.py:100-102`).

> **Ingeniería inversa.** El mismo chequeo corre **dos veces**: una para pintar la
> pantalla y otra para rechazar el pedido. La lectura `GET /cobros/socio/{id_socio}`
> devuelve `puede_renovar`, `motivo_no_renovar` y `renovable_desde`
> (`cobros.py:225-229`), y con eso la pantalla **no dibuja el botón**. El 409 de
> `cobros.py:264-266` es la segunda barrera, la que igual está aunque nadie la vea. Lo
> que se optimiza con la primera es no ofrecer algo que va a fallar —el mostrador tiene
> cola y una operación que se rechaza a mitad de camino cuesta más que una que nunca se
> ofreció—; lo que garantiza la segunda es que la regla se cumpla aunque el pedido venga
> de otro lado, del pago en línea o de una consola abierta. La alternativa descartada era
> confiar en la pantalla y no repetir el chequeo: se ahorraba una consulta por lectura y
> se perdía la regla entera, porque el pago en línea llega por otro camino. **Lo que se
> paga es tener la misma regla evaluada en dos momentos distintos**, y el costo se acota
> poniéndola en una sola función que los dos llaman. El patrón se llama **fallar
> cerrado**: la interfaz ayuda, el servidor decide.

### El 404 de la rutina propia

Un socio puede armarse su propia rutina, con `POST /portal/mi-rutina/propia`
(`backend/routers/portal.py:415`). Esa rutina queda con `id_entrenador` en NULL. Si un
entrenador pide `GET /rutinas/{id}` con ese id, la respuesta es **404 Not Found** —la
misma, palabra por palabra, que si el id no existiera—. La línea es
`backend/routers/rutinas.py:230-231`, dentro de `_rutina_del_staff()`
(`rutinas.py:218-232`):

```python
rutina = db.get(Rutina, id_rutina)
if rutina is None or rutina.id_entrenador is None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La rutina no existe.")
```

Fijate en el `or`: **las dos condiciones dan el mismo error y el mismo texto**. Esa
función es el único camino por el que el personal llega a una rutina, y la usan los cinco
endpoints que la necesitan —`rutinas.py:322`, `:395`, `:543`, `:584` y `:602`—, así que no
hay ninguna puerta lateral por la que una rutina propia se filtre.

Lo que interesa acá es el uso del código. En HTTP, 403 y 404 dicen cosas distintas: el
403 dice "existe y no podés", el 404 dice "no hay nada que decirte". **Un 403 es una
confirmación**: el que lo recibe aprendió que ese id apunta a algo real. Devolver 404
borra esa diferencia. La política que decide cuándo corresponde hacerlo, y cómo se aplica
al resto del sistema, se explica en
[aislamiento de lo propio](A-08-autorizacion.md#aislamiento-de-lo-propio); lo que se
define acá es sólo la herramienta: el 404 no significa "el archivo no está en el disco",
significa "para vos, acá no hay recurso".

Hay un segundo 404 en este repo que muestra la misma idea llevada más lejos. La ruta de
acreditación simulada de un pago **no se registra** si el backend no arrancó en modo
simulado: el decorador se llama a mano, adentro de un `if`, en
`backend/routers/pagos_online.py:392-399`. Cuando no está registrada, el pedido no llega
a ningún endpoint y contesta el enrutador de Starlette con un 404 propio
(`starlette/routing.py:640-653`, que bajo FastAPI levanta `HTTPException(404)` y sale como
`{"detail":"Not Found"}`).

> **Ingeniería inversa.** La alternativa obvia era registrar la ruta siempre y que
> adentro chequee la bandera y devuelva 403. Se descartó, y el comentario de
> `pagos_online.py:392-396` dice por qué: una ruta registrada **figura en `/docs` y en
> `/openapi.json`**, o sea que el mapa de la API anuncia que existe un atajo para
> acreditarse un pago sin pagarlo, aunque esté apagado. No registrarla la borra del mapa.
> Lo que se optimiza es no publicar superficie de ataque; lo que se paga es que la ruta
> aparece y desaparece según una variable de entorno, así que dos despliegues del mismo
> código exponen APIs distintas y ningún chequeo estático lo nota. El chequeo interno
> queda igual, como segunda capa.

### El 401 de la sesión caída

**401 Unauthorized** es el código peor nombrado del protocolo: no habla de autorización,
habla de **autenticación** —no sé quién sos—. El que dice "sé quién sos y no podés" es el
403. Este sistema respeta la distinción con precisión: 3 usos de 401, todos en el camino
de validar la sesión, y 23 de 403, todos después.

El 401 se levanta en dos lugares de `backend/security.py`. El primero es una excepción
construida una sola vez y reusada, `_NO_AUTENTICADO` en `security.py:73-77`, que
`obtener_sesion()` (`security.py:80-142`) lanza en los cinco casos en que no hay sesión
utilizable: no vino token, el token no decodifica, el `sub` no es un entero, el usuario no
existe, o está inactivo o bloqueado. **Los cinco devuelven el mismo texto**: "No se pudo
validar la sesión. Iniciá sesión nuevamente."

El segundo es distinto y es el que le da nombre a esta sección: `security.py:129-135`
rechaza con 401 a una cuenta marcada con `debe_cambiar_password`, aunque el token sea
válido y esté en fecha. El caso concreto que lo motiva es alguien que se resetea su propia
contraseña: el token que tiene en la mano deja de servir en el pedido siguiente. La
mecánica de esa bandera se explica en
[contraseña temporal y primer ingreso](A-07-autenticacion.md#contraseña-temporal-y-primer-ingreso).

Los dos llevan una cabecera que casi nunca se mira: `WWW-Authenticate: Bearer`. El
protocolo la exige junto a todo 401 —es la respuesta a "¿y cómo me autentico?"— y nombra
el esquema que el servidor espera. Este sistema la manda; ningún cliente propio la lee.

El retorno completo del 401 termina en la pantalla, y vale seguirlo entero porque es la
única cadena de este capítulo que cruza las dos puntas:

1. El backend responde 401 (`security.py:73-77` o `:129-135`).
2. `pedir()` mira el número en `api.ts:241`, y si es 401 **y la ruta no es una de las tres
   donde un 401 es normal** —`/login`, `/cambiar-password`, `/me`, listadas en
   `api.ts:166`— llama al aviso registrado (`api.ts:242`).
3. Ese aviso lo registró `App.tsx:73-78`: limpia la sesión del almacén y muestra el
   mensaje del backend en un cartel.
4. Igual se lanza el `ServiceError` (`api.ts:244`), así que la pantalla que había pedido
   el dato muestra su error como siempre.

La lista de tres excepciones de `api.ts:166` es el detalle que hace que esto funcione: en
`/login` un 401 significa "usuario o contraseña incorrectos" y en `/me` significa "todavía
no entraste". Sin esa lista, escribir mal la contraseña te expulsaría de una sesión que
nunca empezó.

> **Ingeniería inversa.** Las dos capas de red de este sistema decidieron **hacer del
> número parte del contrato con la pantalla**, no sólo del mensaje. `ServiceError`
> (`api.ts:13-21`) guarda el `status` junto al texto, y `_procesar()` en
> `Flet/Proyecto/app/api_client.py:126-140` devuelve `{"ok": False, "error": ..., "status":
> ...}` con el comentario que lo justifica: hay fallos que la pantalla puede **ofrecer
> reintentar** y otros no, y sin el número la única forma de distinguirlos sería comparar
> el texto del mensaje, que cambia. La alternativa descartada era que la capa de red
> tradujera cada código a un tipo de error propio —`NoAutenticado`, `Conflicto`,
> `NoEncontrado`— y las pantallas no vieran nunca un número. Habría quedado más limpio y
> habría costado mantener un diccionario de doce entradas sincronizado con el backend.
> **Lo que se paga por la decisión tomada es que el código HTTP se volvió una interfaz
> pública entre el backend y las dos apps:** cambiar un 400 por un 409 en un endpoint es
> un cambio que rompe, y no hay compilador ni tipo que lo detecte, porque del otro lado
> `status` es apenas un `number`. La red devuelve números y los números no tienen tipo
> (→ [A0-05](A0-05-javascript-y-typescript.md#frontera-de-confianza-del-tipo)).

---

## Cabecera HTTP

Una cabecera es un metadato de una línea sobre el pedido o la respuesta, escrito
`Nombre: valor`. Es el mecanismo de extensión del protocolo: todo lo que HTTP aprendió a
hacer después de 1991 —tipos de contenido, idiomas, compresión, caché, sesiones,
seguridad— se agregó como cabeceras, sin tocar el formato del mensaje. Por eso `Cookie`,
`Authorization` y `X-Client-Type` viajan por el mismo canal y con la misma sintaxis que
`Content-Length`: para el protocolo son todas lo mismo.

> **↓ Capa 2 — el byte en la línea `Nombre: valor`.** Salteable si ya lo sabés.
> Este es el piso del concepto.

Del lado del servidor una cabecera no es un texto sino **un par de secuencias de bytes**.
En `httptools_impl.py:239-243`, cada cabecera que el analizador completa entra así:

```python
def on_header(self, name: bytes, value: bytes) -> None:
    name = name.lower()
    ...
    self.headers.append((name, value))
```

Dos cosas quedan fijadas en esas cuatro líneas. **El nombre se pasa a minúsculas**, que es
la forma en que este servidor implementa la regla de que los nombres de cabecera no
distinguen mayúsculas: `Content-Type`, `content-type` y `CONTENT-TYPE` llegan al mismo
lugar. Y **el valor no se toca**: queda en bytes crudos, sin decodificar, porque una
cabecera puede traer cualquier cosa que no sea un byte de control.

Esa normalización es lo que hace que el backend pueda leer una cabecera por su nombre sin
preocuparse por cómo la escribió el cliente. En `backend/routers/auth_router.py:114`, el
login declara un parámetro llamado `x_client_type` y FastAPI lo busca en la cabecera
`x-client-type` —convierte el guión bajo en guión y compara en minúsculas—, sin que haya
que escribir el nombre de la cabecera en ningún lado. Lo mismo del otro lado: el
middleware de CSRF pide `request.headers.get("X-CSRF-Token")` en `backend/csrf.py:82` con
la mayúscula puesta, y funciona porque la búsqueda ya normalizó.

Tres usos de cabeceras en este repo, cada uno de una familia distinta:

- **Cabecera que describe el mensaje.** `Content-Type: application/json`, puesta por
  `api.ts:197` y por `JSONResponse` (`starlette/responses.py:172`). Sin ella el receptor
  no sabe cómo interpretar los bytes del cuerpo.
- **Cabecera que lleva la credencial.** `Authorization: Bearer <token>` en
  `Flet/Proyecto/app/api_client.py:96`, y `Cookie`, que el navegador escribe solo. Son
  dos formas de mandar lo mismo, y la diferencia entre "yo la escribo" y "el navegador la
  escribe por mí" es la que genera todo el problema del que se ocupa
  [A0-12](A0-12-sesiones-y-autenticacion.md#cookie-y-sus-atributos). La cabecera espejo
  del servidor es `Set-Cookie`, que se emite en
  `backend/cookies.py:82-101` (`setear_cookies_sesion()`).
- **Cabecera que instruye al navegador.** Las cinco de `backend/main.py:269-276`, puestas
  por un middleware sobre todas las respuestas: `X-Content-Type-Options: nosniff`,
  `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Permissions-Policy` y
  `Content-Security-Policy: default-src 'none'`. No cambian el cuerpo ni el código: le
  dicen al navegador qué **no** puede hacer con la respuesta. La sexta,
  `Strict-Transport-Security`, sólo sale si la sesión ya viaja por HTTPS
  (`main.py:275-276`), porque mandarla sobre HTTP no sirve y un navegador que la recuerde
  rompe el desarrollo en `localhost`.

Son también el canal por el que viaja el único dato que decide qué forma tiene la sesión:
`X-Client-Type: escritorio` en `Flet/Proyecto/app/api_client.py:90`, leído en
`auth_router.py:114` y comparado en `auth_router.py:223`. Que un valor que el cliente
escribe a su antojo elija el mecanismo de autenticación es, visto desde la seguridad, una
cosa distinta de lo que parece desde la comodidad — ese doble ángulo es de
[A-07](A-07-autenticacion.md#los-dos-mecanismos-de-sesión-y-x-client-type) y de la ficha
V-11 de `docs/vulnerabilidades a arreglar.md`.

---

## Sin estado (stateless)

HTTP **no recuerda nada entre un pedido y el siguiente**. Cada pedido llega solo, con todo
lo que hace falta para atenderlo, y cuando la respuesta sale el servidor no conserva nada
que lo vincule con el próximo. No es un descuido de 1991 que después no se pudo arreglar:
es el rasgo que hizo que la Web escalara. Un servidor que no guarda nada por cliente puede
atender a millones de ellos con la misma memoria, puede reiniciarse sin cortarle la sesión
a nadie, y puede multiplicarse por diez poniendo diez máquinas iguales detrás de un
repartidor de carga, porque cualquiera de las diez sabe atender cualquier pedido.

Para servir documentos alcanzaba de sobra. Deja de alcanzar apenas querés que alguien
**inicie sesión**, porque "iniciar sesión" es exactamente la frase "acordate de mí en el
próximo pedido". Toda la maquinaria de cookies, tokens y cabeceras de autenticación de
[A0-12](A0-12-sesiones-y-autenticacion.md#sesión) existe por una sola razón: reconstruir,
en cada pedido, la memoria que el protocolo no tiene. No se le agrega memoria a HTTP; se
le adjunta a cada pedido un dato que permite deducirla.

> **↓ Capa 2 — qué le cuesta a este backend reconstruir esa memoria en cada pedido.**
> Salteable si ya lo sabés. Este es el piso del concepto.

En OlimpOS, "reconstruir la sesión" es una función que corre **antes de cada endpoint
protegido**: `obtener_sesion()` en `backend/security.py:80-142`. En cada pedido, sin
excepción y sin recordar el anterior, hace cinco cosas:

1. Toma el token del encabezado `Authorization` o de la cookie, con prioridad para el
   primero (`security.py:110`).
2. Lo decodifica y verifica su firma (`security.py:114`).
3. Lee de adentro el id del usuario (`security.py:118-121`).
4. **Va a la base a buscar ese usuario** (`security.py:123`).
5. Devuelve una `Sesion` con el usuario, los roles y los ids firmados
   (`security.py:140-142`).

El paso 4 es el interesante, porque es el que no haría falta. El token ya trae la
identidad adentro y está firmado, así que el servidor podría confiar en él y ahorrarse la
consulta. El comentario de `security.py:102-107` explica por qué igual se hace: el token
es inmutable durante ocho horas, y desactivar o bloquear una cuenta tiene que tener efecto
**ya**; sin esa consulta, alguien a quien acaban de dar de baja seguiría operando el resto
de la jornada. Es una lectura por clave primaria contra una base que está a 44 ms
(→ [A-11](A-11-rendimiento.md#base-remota)), pagada en cada pedido de cada persona.

> **Ingeniería inversa.** Lo que se estaba optimizando es que una baja sea inmediata. La
> restricción: la base está lejos y el token no se puede revocar de a uno
> (→ [A0-12](A0-12-sesiones-y-autenticacion.md#caducidad-y-revocación)). Las alternativas
> eran acortar la vida del token a minutos, que castiga a todos para atajar un caso raro y
> obliga a renovarlo, o llevar una lista de tokens revocados, que es memoria del lado del
> servidor y rompe justamente la propiedad que hace simple todo esto. Se eligió pagar una
> consulta por pedido. **El precio es medible y está aceptado:** un viaje más a São Paulo
> en cada pedido, a cambio de que la única palabra final sobre quién puede operar la tenga
> la base y no un papel firmado hace siete horas.

La falta de memoria se ve igual de clara del lado del cliente. La PWA **no guarda nada**
de la identidad: al recargar la página con F5, el navegador tira el árbol entero y la app
arranca sin saber quién es. Lo resuelve preguntando: `GET /me`
(`backend/routers/auth_router.py:265-292`, `sesion_actual()`) devuelve la misma forma que
el login, y `App.tsx:65-67` lo dispara al montar. El motivo es el del comentario de
`auth_router.py:274-276`: si los roles vivieran en el navegador, alcanzaría con editarlos
desde las herramientas del navegador para darse permisos ajenos.

> Ese mismo docstring dice que la PWA guarda el token en `sessionStorage`, y no es así: la
> discrepancia está anotada en
> [los dos mecanismos de este sistema](A0-12-sesiones-y-autenticacion.md#los-dos-mecanismos-de-este-sistema-y-por-qué-son-dos).

---

## JSON como cuerpo

El cuerpo de un pedido HTTP son bytes. El protocolo no dice qué significan: eso lo dice
`Content-Type`. HTTP nació llevando HTML; en los años 2000 la forma habitual de mandar
datos estructurados era XML, con etiquetas de apertura y cierre y un ecosistema entero de
esquemas y transformaciones alrededor. JSON —especificado por Douglas Crockford a
principios de esa década a partir de la sintaxis de literales de JavaScript, estandarizado
después como RFC 8259 y ECMA-404— ganó por dos razones muy concretas: pesa menos porque no
repite el nombre de cada campo al cerrarlo, y en el navegador se convierte en objetos sin
librería, porque **ya es** la sintaxis del lenguaje que ahí corre.

En este sistema las dos apps y el backend hablan JSON y nada más. `api.ts:197` lo declara
en cada pedido, `api.ts:219` serializa el cuerpo con `JSON.stringify`, `api.ts:234` parsea
la respuesta con `respuesta.json()`, y del lado de Python `JSONResponse`
(`starlette/responses.py:172`) declara `media_type = "application/json"`. En la app de
escritorio lo hace la librería de red: `requests.request(..., json=json_body, ...)` en
`Flet/Proyecto/app/api_client.py:150-153` serializa y pone la cabecera sola.

> **↓ Capa 2 — el texto serializado, y qué tipos no sobreviven al viaje.** Salteable si
> ya lo sabés. Este es el piso del concepto.

JSON tiene **seis** tipos y ninguno más: objeto, arreglo, cadena, número, booleano y
`null`. No tiene fecha, no tiene decimal exacto, no tiene entero distinto de flotante, no
tiene bytes. Todo lo que el backend maneja y no está en esa lista **se convierte en otra
cosa** al salir, y hay que reconstruirlo al entrar.

Se ve tocando cualquier esquema de salida. `MembresiaOut`, en
`backend/schemas.py:784-795`, declara:

```python
precio_pactado: float
fecha_inicio: date
fecha_vencimiento: date | None = None
dias_restantes: int | None = None
```

Lo que sale al cable es:

```json
{"precio_pactado": 30000.0, "fecha_inicio": "2026-09-24", "fecha_vencimiento": null, "dias_restantes": 27}
```

Tres pérdidas, una por línea. `fecha_inicio` era un `date` de Python y llega como
**cadena** `"2026-09-24"` (formato ISO 8601): del otro lado es texto, y para volver a ser
fecha alguien tiene que parsearlo. `precio_pactado` era un `Decimal` en la base —columna
monetaria— y viaja como **número flotante**, con todo lo que eso implica para los
centavos. Y `None` se escribe `null`, que en JavaScript llega como `null` y no como
`undefined`, dos valores distintos que el código de la PWA tiene que distinguir.

La reconstrucción del otro lado no es automática ni gratuita: es exactamente el trabajo
del esquema de entrada, que toma el texto y vuelve a fabricar los tipos —y rechaza con
422 lo que no encaje— (→
[A0-10](A0-10-python-del-lado-del-servidor.md#esquema-de-entrada-y-salida-y-el-422)). Del
lado del navegador no hay nada equivalente: `respuesta.json()` devuelve un objeto sin
verificar nada, y el tipo de TypeScript que lo describe es una promesa del programador que
en tiempo de ejecución no existe (→
[A0-05](A0-05-javascript-y-typescript.md#frontera-de-confianza-del-tipo)).

Hay un detalle del formato que en este repo costó un error real. El analizador de JSON de
Python acepta `Infinity` y `NaN`, que **no son JSON válido** —la especificación sólo
admite números finitos— pero que muchas implementaciones toleran. Un cuerpo con
`{"monto_manual": Infinity}` pasaba el parseo, fallaba la validación como corresponde, y
después el servidor no podía serializar el error porque el error incluía el valor
recibido, y el 422 correcto terminaba en un 500. La corrección está en dos lugares: el
manejador de `backend/main.py:236-249` (`errores_de_validacion`), que devuelve sólo dónde
y qué falló, sin copiar el valor; y `allow_inf_nan=False` en el campo, en
`backend/schemas.py:745`.

> **Ingeniería inversa.** Ese manejador recorta el cuerpo del 422 a tres campos —`loc`,
> `msg`, `type`— y descarta el `input` que FastAPI incluye por defecto. Lo que se optimiza
> son dos cosas a la vez: que un tipo no serializable no pueda convertir un 422 en un 500,
> y que el servidor **no le devuelva al cliente lo que el cliente mandó** —por ejemplo,
> una contraseña que no cumplía la regla de largo, que sin este recorte volvería escrita
> en la respuesta—. La alternativa era filtrar sólo los valores problemáticos y conservar
> el resto, que es más trabajo y deja la segunda puerta abierta. **Lo que se paga es
> capacidad de diagnóstico:** un 422 ya no dice qué valor llegó, así que depurar un
> formulario obliga a mirar el pedido en el navegador. El comentario de `main.py:244-247`
> deja constancia de que las dos apps sólo leen `msg`, que es lo que hace aceptable el
> recorte.

---

## Proxy inverso

Un **proxy inverso** es un servidor que recibe pedidos como si fuera el destino, y los
reenvía a otro servidor bajo su propio nombre. Para el cliente no existe: el pedido sale
hacia una dirección y la respuesta vuelve de esa misma dirección, con lo cual **los dos
servidores son, para el navegador, el mismo sitio**. Se llama *inverso* porque el proxy
clásico está del lado del cliente y representa al que pide; este está del lado del
servidor y representa al que responde.

Existe porque HTTP ata muchas cosas al host: la cabecera `Host`, la política de mismo
origen del navegador (→
[A0-04](A0-04-el-navegador-por-dentro.md#origen-y-política-del-mismo-origen)), y las
cookies, que pertenecen a un host y no a un puerto. Dos servicios que en realidad son dos
procesos en dos puertos distintos, puestos detrás de un proxy inverso, dejan de ser dos
sitios y pasan a ser uno.

> **↓ Capa 2 — el pedido reescrito, línea por línea y cabecera por cabecera.** Salteable
> si ya lo sabés. Este es el piso del concepto.

En desarrollo, este repo tiene uno: el servidor de desarrollo de la PWA, configurado en
`Proyecto - PWA/src/frontend/vite.config.ts:50-64`:

```ts
proxy: {
  '/api': {
    target: destinoApi,
    changeOrigin: false,   // conserva el Host, así la cookie queda en localhost
    rewrite: (ruta) => ruta.replace(/^\/api/, ''),
  },
},
```

Tomemos el pedido de cobro del principio de este capítulo y sigámoslo por las dos patas
del proxy. Lo que **el navegador escribe** y manda al puerto 5173:

```http
POST /api/cobros HTTP/1.1
Host: localhost:5173
Content-Type: application/json
X-CSRF-Token: 9tQm3Zx1pK7sVb0LcR2aYh4NfE6uWd8J
Cookie: olimpos_session=...; olimpos_csrf=...
Content-Length: 149
```

Lo que **el proxy escribe** y manda al puerto 8000, abriendo su propia conexión TCP:

```http
POST /cobros HTTP/1.1
Host: localhost:5173
Content-Type: application/json
X-CSRF-Token: 9tQm3Zx1pK7sVb0LcR2aYh4NfE6uWd8J
Cookie: olimpos_session=...; olimpos_csrf=...
Content-Length: 149
connection: keep-alive
x-forwarded-for: ::1
x-forwarded-host: localhost:5173
x-forwarded-proto: http
```

Dos cambios y un agregado, y cada uno sale de una línea de la configuración:

- **La ruta pierde el prefijo.** `/api/cobros` se convierte en `/cobros`, por el `rewrite`
  de `vite.config.ts:61`. El prefijo `/api` **no existe en el backend**: ninguna ruta de
  `backend/routers/` lo declara. Existe sólo para que el proxy sepa qué derivar y qué
  servir como archivo de la aplicación.
- **El `Host` NO cambia.** Eso es lo que hace `changeOrigin: false` en
  `vite.config.ts:58`. Por defecto un proxy reescribe el `Host` con el del destino —para
  que el servidor de atrás se vea a sí mismo con su propio nombre—, y acá se apaga a
  propósito.
- **Aparecen las cabeceras `x-forwarded-*`.** Las agrega el proxy para contar lo que se
  perdió al reenviar: quién era el cliente original, qué host pidió, con qué esquema. Son
  informativas y **las escribe quien reenvía**, así que un servidor que las crea vale lo
  que valga el proxy que las puso. Este backend no confía en ellas: `_ip()` en
  `backend/routers/auth_router.py:69-72` toma la dirección del socket y **no**
  `X-Forwarded-For`, con el comentario que lo dice en una línea — *"la del socket y no
  X-Forwarded-For, que lo escribe el cliente"*.

Del lado de la respuesta el camino es el mismo al revés, y ahí la cabecera que importa es
`Set-Cookie`: el backend la emite para el host que vio, y como el `Host` nunca se tocó,
la cookie queda guardada bajo `localhost`, que es donde la página puede encontrarla.

Por qué este proxy existe —qué se rompía sin él y qué regla de las cookies lo obliga— está
contado en su propia escala del recorrido, en
[el proxy `/api` de Vite](A-04-recorrido-de-un-pedido.md#proxy-api-de-vite), y la regla que
lo justifica es de [A0-12](A0-12-sesiones-y-autenticacion.md#cookie-y-sus-atributos). Lo
que corresponde fijar acá es sólo el mecanismo: **un proxy inverso es un pedido que se
reescribe y se vuelve a mandar**, y todo lo que decide el resultado está en qué líneas y
qué cabeceras cambia al reescribirlo.

La app de escritorio no pasa por acá: le pega directo a
`http://127.0.0.1:8000` (`Flet/Proyecto/app/api_client.py:38`) y sus rutas no llevan
`/api`. Es el mismo backend, dos caminos distintos hasta él.

---

## Con qué se conecta

- **Existe por culpa de…** que HTTP no recuerde nada: toda la maquinaria de sesión está
  para reponer esa memoria en cada pedido
  ([A0-12](A0-12-sesiones-y-autenticacion.md#sesión)).
- **Existe por culpa de…** que `POST` no sea idempotente: el aviso de Mercado Pago puede
  llegar dos veces, así que acreditar tiene que poder repetirse sin cobrar de nuevo
  ([B-05](B-05-cobros-y-pagos.md)).
- **Es el mismo problema que…** el enmarcado del cuerpo y el orden de entrega de TCP:
  saber dónde termina un mensaje dentro de un flujo de bytes que no tiene bordes
  ([A0-02](A0-02-como-se-comunican-dos-maquinas.md#tcp-y-el-viaje-de-ida-y-vuelta-rtt)).
- **Es la misma idea que…** el proxy inverso genérico y el proxy `/api` de Vite: el
  segundo es el primero con tres líneas de configuración
  ([A-04](A-04-recorrido-de-un-pedido.md#proxy-api-de-vite)).
- **Se contradice con…** la semántica de reemplazo total de `PUT` y el `PUT` de socio, que
  sólo toca lo que vino: ganó no borrar datos en silencio
  (`backend/routers/socios.py:491-597` · `editar_socio()`).
- **Se contradice con…** el tipo `status: number` del cliente y el hecho de que el código
  HTTP sea un contrato entre backend y pantallas: el compilador no verifica ni uno de los
  doce valores ([A0-05](A0-05-javascript-y-typescript.md#frontera-de-confianza-del-tipo)).
