# A0-12 · Sesiones y autenticación en la web

**Piso de este capítulo: el byte en la cabecera, y el pedido falso escrito completo.**
Bajamos hasta ver los caracteres exactos que viajan en la línea `Set-Cookie:`, los que
vuelven en la línea `Cookie:`, y el pedido de ataque entero, escrito, tal como lo arma el
navegador de la víctima. Abajo de eso está el paquete TCP, que ya tiene dueño
([TCP y el viaje de ida y vuelta](A0-02-como-se-comunican-dos-maquinas.md#tcp-y-el-viaje-de-ida-y-vuelta-rtt)),
y arriba está la decisión de producto, que es de otro capítulo.

Todo lo que sigue existe por una sola razón, y conviene tenerla a mano: el
[pedido HTTP](A0-03-http.md#pedido-y-respuesta-http) llega solo, sin contexto y
[sin estado](A0-03-http.md#sin-estado-stateless). El servidor abre el sobre, lee un método
y una ruta, y no tiene absolutamente ninguna forma nativa de saber si ese sobre lo mandó la
misma persona que se identificó hace un segundo. Ocho conceptos —cookie, sesión, JWT, token
portador, CSRF, token de doble envío, CORS, caducidad— son ocho capas de parche sobre ese
agujero original, y cada uno se entiende sólo si se sabe qué agujero tapa.

---

## Sesión

**El problema.** HTTP se diseñó para servir documentos: pedís una página, te la dan, la
conversación termina. Nadie necesitaba recordar nada entre un pedido y el siguiente porque
no había nada para recordar. Eso alcanzó hasta el momento exacto en que alguien quiso
hacer algo que dependiera de quién era: un carrito de compras, un panel de administración,
un gimnasio donde el Recepcionista ve la grilla de socios y el Socio no.

A partir de ahí hay una sola pregunta, y es la que define todo el capítulo: **el pedido
número dos tiene que traer consigo alguna prueba de que lo manda la misma persona que
mandó el número uno.** A esa prueba adjunta, y a la memoria que el servidor reconstruye
a partir de ella, se le llama **sesión**.

> **↓ Capa 1 — las dos familias de solución.** Salteable si ya lo sabés.

Sólo hay dos formas de reconstruir esa memoria, y se diferencian por dónde vive el dato:

1. **Sesión del lado del servidor.** El cliente adjunta un identificador opaco —un número
   de ticket sin significado— y el servidor lo busca en una tabla propia donde guardó
   quién es, qué roles tiene y cuándo entró. El identificador no dice nada; todo el
   contenido está del lado del servidor.
2. **Token autocontenido.** El cliente adjunta un paquete que *contiene* la identidad, la
   fecha de emisión y los permisos, más una marca criptográfica que prueba que lo emitió
   el servidor. El servidor no guarda nada: lee el paquete, verifica la marca y confía.

La diferencia práctica se mide en viajes. La primera familia obliga a consultar un almacén
en cada pedido; la segunda no consulta nada. La primera permite borrar una fila y matar la
sesión al instante; la segunda no tiene nada que borrar. Es un intercambio directo entre
**costo por pedido** y **capacidad de revocar**, y cada sistema lo resuelve según dónde le
duele más.

> **↓ Capa 2 — qué es exactamente "el dato que se adjunta".** Salteable si ya lo sabés.

Sea cual sea la familia, ese dato tiene que viajar en algún lugar del pedido, y el pedido
sólo tiene tres lugares posibles: la URL, el cuerpo o una
[cabecera](A0-03-http.md#cabecera-http). La URL queda descartada de entrada —queda escrita
en el historial del navegador, en el `Referer` que se manda al sitio siguiente y en los
registros de cualquier intermediario—. El cuerpo tampoco sirve, porque un `GET` no tiene
cuerpo. Queda la cabecera, y a partir de acá todo el capítulo transcurre ahí.

Dentro de las cabeceras hay dos opciones, y son las dos que usa este sistema: una que el
navegador llena **solo** (`Cookie:`) y otra que el programa llena **a mano**
(`Authorization:`). Todo lo demás —CSRF, `SameSite`, CORS— son consecuencias de esa
palabra: *solo*.

**En este repo.** OlimpOS eligió la segunda familia: token autocontenido, firmado, sin
tabla de sesiones. La emisión está en `backend/auth.py:148-191` · `crear_token_acceso()`
y la validación en `backend/security.py:80-142` · `obtener_sesion()`. Lo que se pagó por
esa elección —no poder revocar— y cómo se compensa está en
[Caducidad y revocación](#caducidad-y-revocación), al final de este capítulo.

---

## Cookie y sus atributos

**El problema y su origen histórico.** En 1994, Lou Montulli estaba escribiendo Netscape
Navigator y necesitaba que un servidor pudiera saber si un visitante ya había estado ahí
—el caso concreto era un carrito de compras—. La idea que implementó es minimalista hasta
la brutalidad: el servidor manda un papelito con la respuesta, el navegador lo guarda, y
el navegador lo vuelve a adjuntar **solo**, en cada pedido siguiente a ese sitio, sin que
nadie se lo pida. Nombre técnico: *magic cookie*, tomado de la jerga de Unix para un dato
opaco que se pasa de un lado a otro sin mirarlo.

Ese mecanismo mínimo se estandarizó recién en 1997 y su versión vigente es RFC 6265, de
2011. **Todos los atributos que vamos a ver —`HttpOnly`, `Secure`, `Domain`, `Path`,
`Max-Age`, `SameSite`— son parches posteriores a agujeros que el mecanismo mínimo dejó
abiertos**, y cada uno se entiende sólo por su agujero. Esa es la forma correcta de
aprenderlos: no como una lista de opciones, sino como una cronología de accidentes.

> **↓ Capa 1 — la respuesta que la crea, byte por byte.**

Cuando `backend/routers/auth_router.py:108-240` · `login()` valida la contraseña y decide
que el cliente es un navegador, llama a `setear_cookies_sesion()`
(`backend/cookies.py:82-101`). Lo único que eso hace es agregar dos líneas de texto a las
cabeceras de la respuesta. Esas dos líneas, con la configuración de desarrollo de este
repo (`COOKIE_SECURE=false`, `COOKIE_SAMESITE=lax`, `JWT_EXPIRACION_MINUTOS=480`, todas en
`backend/.env.example:56-76`), salen así:

```http
HTTP/1.1 200 OK
content-type: application/json
set-cookie: olimpos_session=eyJhbGciOiJIUzI1NiI...; HttpOnly; Max-Age=28800; Path=/; SameSite=lax
set-cookie: olimpos_csrf=7Qk1sV3xZ...; Max-Age=28800; Path=/; SameSite=lax
```

Cuatro hechos mecánicos que se leen directamente de ahí:

- **Una cookie por línea.** No existe forma de mandar dos cookies en una sola línea
  `Set-Cookie`. Por eso hay dos líneas: son dos cookies distintas, emitidas en el mismo
  viaje (`cookies.py:84-92` y `cookies.py:93-101`).
- **El orden de los atributos no importa.** El que parsea separa por `;` y mira el nombre
  de cada pieza. La única pieza posicional es la primera: `nombre=valor`.
- **`28800` no es un invento.** Es `COOKIE_MAX_AGE` de `cookies.py:79`, que lee la misma
  variable de entorno que usa la expiración del token en `backend/auth.py:36`
  (`JWT_EXPIRACION_MINUTOS`, 480 minutos). Están atadas a propósito: una cookie que
  sobreviviera al token sólo lograría que la persona *parezca* con la sesión abierta hasta
  que el primer pedido devuelva 401 (`cookies.py:76-78`).
- **`Secure` no aparece.** Porque `COOKIE_SECURE` es `false` en desarrollo
  (`cookies.py:65`). Es un atributo condicional, no una constante.

> **↓ Capa 2 — dónde la guarda el navegador, y con qué llave.**

El navegador no guarda "una cookie": guarda una fila en un almacén propio, indexada por
una clave compuesta de **(nombre, dominio, ruta)**. En Chrome y Firefox ese almacén es una
base SQLite dentro de la carpeta del perfil del usuario; es un archivo del disco, no
memoria, y por eso una cookie con `Max-Age` sobrevive a cerrar el navegador. Vive en el
perfil, no en la pestaña: dos pestañas del mismo sitio comparten exactamente la misma
cookie, y una ventana de incógnito usa un almacén aparte que se destruye al cerrarla.

Esa clave compuesta explica dos comportamientos que sorprenden:

- **Escribir una cookie con el mismo nombre, dominio y ruta pisa la anterior.** No se
  acumulan. Es lo que hace que un login nuevo reemplace la sesión vieja sin limpiar nada.
- **Si cambia cualquiera de los tres, son dos cookies distintas y conviven.** Es
  exactamente el riesgo que previene `borrar_cookies_sesion()`
  (`backend/cookies.py:104-116`): el borrado se hace mandando otro `Set-Cookie` con el
  mismo nombre y un vencimiento en el pasado, así que si no coincide la ruta se estaría
  borrando una cookie distinta de la que existe, y la vieja sobreviviría — un cierre de
  sesión que no cierra nada.

Los demás atributos no forman parte de la clave, pero igual viajan en el borrado
(`cookies.py:111-116`) por una razón mecánica distinta: **un `Set-Cookie` mal formado se
descarta entero**. Si el borrado saliera con `SameSite=none` sin `Secure`, el navegador lo
tiraría a la basura, y el resultado sería el mismo desastre: la cookie vieja intacta.

> **↓ Capa 3 — el pedido que la devuelve, byte por byte. Este es el piso.**

Acá está el hecho más importante de todo el mecanismo, y el que hace falta entender para
que el resto del capítulo tenga sentido. En el viaje de vuelta, el navegador manda esto:

```http
GET /socios HTTP/1.1
Host: localhost:5173
Cookie: olimpos_session=eyJhbGciOiJIUzI1NiI...; olimpos_csrf=7Qk1sV3xZ...
```

Una sola línea `Cookie:`, con las dos cookies separadas por `; `, y **nada más que
`nombre=valor`**. Ni `HttpOnly`, ni `Max-Age`, ni `Path`, ni `SameSite`. Los atributos son
instrucciones **para el navegador**, no datos para el servidor: le dicen cuándo mandar la
cookie y cuándo no, y después desaparecen. El servidor nunca ve ninguno.

De ahí se siguen dos consecuencias que la gente descubre depurando, y que conviene saber
antes:

- **El servidor no puede saber si una cookie que recibió era `HttpOnly` o `Secure`.** Sólo
  ve texto. Todas las garantías de esos atributos las da el navegador, del otro lado.
- **El servidor no puede saber si la cookie llegó porque la persona hizo click o porque
  otro sitio disparó el pedido.** Para el backend, la línea `Cookie:` es idéntica en los
  dos casos. Eso, exactamente eso, es [CSRF](#csrf).

Dato al margen que explica el prefijo: todo JWT empieza con `eyJ` porque es el base64url
de los dos primeros caracteres de un objeto JSON, `{"`. No es una marca del formato, es
aritmética de la codificación.

> **↓ Capa 4 — los atributos, uno por uno, por el agujero que tapa cada uno.**

**`HttpOnly`** (`cookies.py:88`, Microsoft lo introdujo en Internet Explorer 6 SP1, 2002).
*Agujero:* el mecanismo original dejaba las cookies legibles desde JavaScript vía
`document.cookie`, así que cualquier script inyectado en la página —un XSS— podía leer la
cookie de sesión y mandarla a otro servidor. El atacante se llevaba la sesión y la usaba
después, desde otra máquina, tranquilo. *Parche:* con `HttpOnly`, `document.cookie`
simplemente no la incluye. El XSS sigue pudiendo disparar pedidos desde la página de la
víctima mientras esa página esté abierta, pero no puede **exfiltrar** la sesión. Eso es
justamente lo que dice el docstring de `backend/cookies.py:6-19`, y es el motivo por el
que la PWA de este repo no guarda el token en ningún lado
(`Proyecto - PWA/src/frontend/src/services/api.ts:66-86`).

**`Secure`** (`cookies.py:89`). *Agujero:* sin él, el navegador manda la cookie también
por `http://`, en texto plano; cualquiera en la misma red Wi-Fi la lee y se copia la
sesión entera. *Parche:* con `Secure`, la cookie sale sólo por HTTPS
([TLS](A0-02-como-se-comunican-dos-maquinas.md#tls)). Acá es una
[variable de entorno](A0-01-como-corre-un-programa.md#variable-de-entorno-y-archivo-env)
(`COOKIE_SECURE`, `cookies.py:61-65`) y no una constante porque en desarrollo sobre
`http://localhost` el navegador nunca mandaría una cookie `Secure`, y no habría forma de
iniciar sesión.

**`Max-Age` y `Expires`** (`cookies.py:79`, `cookies.py:86`). *Agujero:* una cookie sin
ninguno de los dos es una *cookie de sesión de navegador*, que muere cuando se cierra el
navegador — y "cuando se cierra el navegador" es un momento que el servidor no controla ni
conoce. *Parche:* `Max-Age` en segundos fija el plazo. Ojo con la asimetría: el plazo lo
hace cumplir el navegador, así que es una comodidad, no una defensa. Quien copie el texto
de la cookie puede seguir usándola después. La defensa de verdad es el `exp` de adentro
del token, que lo verifica el servidor — ver [Caducidad y revocación](#caducidad-y-revocación).

**`Path`** (`cookies.py:91`). *Agujero:* dos aplicaciones distintas bajo el mismo host
compartirían cookies sin quererlo. *Parche:* la cookie se adjunta sólo a los pedidos cuya
ruta empieza con el valor declarado. Acá es `/` porque toda la API es una sola aplicación.
Y no es una frontera de seguridad: cualquier página del mismo host puede escribir una
cookie con cualquier `Path`.

**`Domain`** — y acá lo interesante es lo que **no** está. `setear_cookies_sesion()`
(`cookies.py:84-101`) **no pasa `domain=`**, y eso no es un olvido: una cookie sin
`Domain` es *host-only*, o sea que el navegador la manda **sólo** al host exacto que la
emitió. Si se declarara `Domain=olimpos.local`, la cookie viajaría también a
`cualquier-cosa.olimpos.local`, y bastaría con que un subdominio quedara en manos ajenas
para regalarle la sesión. El navegador impide lo más burdo —un sitio no puede declarar un
`Domain` que no le pertenece, y hay una lista pública de sufijos para que nadie escriba una
cookie para `.com.ar`—, pero entre subdominios hermanos no protege a nadie. Host-only es el
valor más restrictivo, y es el que se eligió por omisión.

**`SameSite`** (`cookies.py:67-74`) es el único atributo que no tapa un agujero de
confidencialidad sino uno de **integridad**, y es tan central que tiene su propia sección:
se explica entero dentro de [CSRF](#csrf), porque fuera de ese ataque no significa nada.

**En este repo, cerrando el descenso.** Las dos cookies son `olimpos_session` y
`olimpos_csrf` (`backend/cookies.py:45` y `:51`). La primera es `httponly=True` y la
segunda `httponly=False`, y esa diferencia de una línea (`cookies.py:88` contra
`cookies.py:97`) es todo el diseño: la sesión no se puede leer y el antídoto sí, porque la
PWA tiene que copiarlo a una cabecera. Del lado del navegador, quien la lee es
`tokenCsrf()` en
`Proyecto - PWA/src/frontend/src/services/api.ts:101-104`, con una expresión regular sobre
`document.cookie` — que nunca va a encontrar `olimpos_session` ahí adentro, y ese es el
punto.

---

## CSRF

**El problema, planteado con precisión.** De la Capa 3 de la sección anterior quedó un
hecho: el navegador adjunta la cookie del sitio destino **según quién sea el destino, no
según quién sea el origen**. No pregunta qué página disparó el pedido. Si el pedido va a
`olimpos.local`, salen las cookies de `olimpos.local`, y punto.

Esto es un caso particular del **problema del diputado confundido**, nombrado por Norm
Hardy en 1988: un componente con más autoridad que vos ejecuta una orden tuya usando *su*
autoridad, no la tuya. Acá el diputado es el navegador de la víctima, que tiene la
autoridad (la cookie) y la usa obedeciendo a quien no debería. El nombre *Cross-Site
Request Forgery* se popularizó a principios de los 2000; también se lo llamó *session
riding*, que describe mejor lo que pasa: el atacante no roba la sesión, **se sube a ella**.

> **↓ Capa 1 — el ataque, paso a paso.**

Escenario: el gimnasio, un martes a la mañana.

1. **La víctima tiene sesión abierta.** El Dueño entró a OlimpOS desde la PC del
   mostrador. En su navegador quedaron las dos cookies de la sección anterior, con
   `Max-Age=28800`: ocho horas de validez, viven en el perfil del navegador, no en la
   pestaña.
2. **La víctima abre otra cosa.** En otra pestaña —o en un mail, o en un link de un grupo—
   abre `https://cupon-gratis.example/`. No cierra OlimpOS; no hace falta cerrarlo, y de
   hecho el ataque necesita que siga abierto. En rigor ni siquiera hace falta la pestaña:
   alcanza con que las cookies existan en el perfil.
3. **Esa página trae un formulario que se manda solo.** El HTML completo es este, y no
   necesita nada más:

   ```html
   <form id="f" method="POST" action="http://olimpos.local/socios/7/baja">
     <input type="hidden" name="motivo" value="x">
   </form>
   <script>document.getElementById('f').submit()</script>
   ```

4. **El navegador obedece.** Ve un formulario que se envía, arma el pedido, mira el destino
   (`olimpos.local`), busca en su almacén las cookies de ese host, las encuentra, las
   adjunta y manda.
5. **El backend lo atiende.** Lee la línea `Cookie:`, valida el token, resuelve la
   identidad del Dueño y ejecuta la baja del socio 7. Nadie apretó nada. Nadie se entera.
   En el registro de la aplicación queda un pedido perfectamente autenticado del Dueño.

Ese es el ataque descripto en el docstring de `backend/csrf.py:7-18`, que trae el mismo
formulario. Vale la pena notar los tres detalles que lo hacen viable: no hace falta
adivinar ninguna contraseña, no hace falta leer nada de OlimpOS, y la víctima no ve nada
(el formulario puede ir en un `iframe` invisible).

> **↓ Capa 2 — el pedido falso, escrito completo. Este es el piso.**

Esto es lo que sale por el cable, sin nada abreviado excepto los valores de las cookies:

```http
POST /socios/7/baja HTTP/1.1
Host: olimpos.local
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ...
Origin: https://cupon-gratis.example
Referer: https://cupon-gratis.example/
Content-Type: application/x-www-form-urlencoded
Content-Length: 8
Cookie: olimpos_session=eyJhbGciOiJIUzI1NiI...; olimpos_csrf=7Qk1sV3xZ...
Connection: keep-alive

motivo=x
```

Leelo línea por línea, porque cada una enseña algo:

- **`Cookie:` está.** Es la línea que hace todo el daño, y es *idéntica* a la que manda la
  aplicación legítima. No hay ninguna marca en el pedido que diga "esto lo disparó otro
  sitio"… salvo dos.
- **`Origin` y `Referer` sí delatan al atacante.** Los navegadores modernos mandan `Origin`
  también en los envíos de formulario entre sitios. Son la pista, y son la base de una
  defensa alternativa que este repo no eligió; volvemos a eso al final del capítulo.
- **`Content-Type: application/x-www-form-urlencoded`.** Un `<form>` de HTML sólo puede
  emitir tres tipos de contenido, y `application/json` no es uno de ellos. Esa limitación
  —que parece un detalle de trivia— es la que decide qué frena y qué no frena el ataque.
- **No hay ninguna cabecera inventada.** Un formulario no puede agregar
  `X-CSRF-Token: loquesea`. Sólo JavaScript puede poner cabeceras arbitrarias, y ahí entra
  a jugar CORS.

> **↓ Capa 3 — qué NO frena esto: CORS no es una defensa contra CSRF.**

Es el malentendido más común del tema y conviene liquidarlo acá, con el pedido de arriba a
la vista. La política del mismo origen
([origen](A0-04-el-navegador-por-dentro.md#origen-y-política-del-mismo-origen)) le prohíbe
a `cupon-gratis.example` **leer** la respuesta de `olimpos.local`. No le prohíbe
**mandarla**. Y en el ataque de arriba al atacante no le importa leer nada: el socio ya
quedó dado de baja. **El daño ocurre en la ida; CORS gobierna la vuelta.**

La variante con `fetch` termina de dejarlo claro. Si el atacante escribe:

```js
fetch('http://olimpos.local/socios/7/baja', {
  method: 'POST',
  credentials: 'include',
  headers: { 'Content-Type': 'text/plain' },
  body: 'x',
});
```

…ese pedido **también sale y también se ejecuta**, porque cumple las condiciones de
*pedido simple* y el navegador no lo consulta con nadie antes de mandarlo. Lo único que
pasa es que la promesa se rechaza al volver, porque la respuesta no trae permiso para ser
leída. El atacante no lee nada y no le importa. Si en cambio pusiera
`Content-Type: application/json` o agregara `X-CSRF-Token`, ahí sí el navegador haría un
[preflight](#cors-y-preflight) y el pedido nunca saldría — pero eso no es una defensa
contra CSRF, es un efecto colateral de haberse salido del conjunto de pedidos simples.

> **↓ Capa 4 — qué le hace `SameSite=lax` a ese pedido exacto.**

`SameSite` lo propuso Google alrededor de 2016 y Chrome lo convirtió en valor por omisión
en 2020, veinte años después de que el ataque tuviera nombre. Es un atributo de la cookie
(`backend/cookies.py:74`) con tres valores posibles, y lo que hace es decirle al navegador
**cuándo no adjuntar la cookie**:

| Valor | Cuándo manda la cookie |
|---|---|
| `strict` | Sólo cuando la página que origina el pedido es del mismo sitio. Nunca en nada que venga de afuera. |
| `lax` | Lo mismo, **más** una excepción: las navegaciones de nivel superior con método seguro. Hacer click en un link externo hacia el sitio sí lleva la cookie. |
| `none` | Siempre, como antes de 2016. El navegador exige que además sea `Secure`. |

Sobre el pedido falso de la Capa 2, con `lax`, el efecto es literal: **la línea `Cookie:`
no aparece**. No es que el backend la rechace; es que nunca llega. El pedido entra sin
credencial, `obtener_sesion()` no encuentra ni cabecera ni cookie
(`backend/security.py:108-110`) y responde
[401](A0-03-http.md#código-de-estado). El socio 7 no se da de baja.

Acá hay que precisar qué significa **"mismo sitio"**, porque no es lo mismo que "mismo
origen" y la diferencia es exactamente lo que hace falta para entender el proxy de este
repo. Un *origen* es la tripla esquema + host + puerto. Un *sitio* es más grueso: es el
dominio registrable (más el esquema). **El puerto no forma parte del sitio.** De ahí:

- `http://localhost:5173` y `http://localhost:8000` → **mismo sitio**, distintos orígenes.
- `http://localhost:5173` y `http://127.0.0.1:8000` → **sitios distintos**, porque
  `localhost` y `127.0.0.1` son dos hosts, por más que apunten a la misma máquina.

El segundo caso es el que rompió este proyecto una vez y está documentado en
`Proyecto - PWA/src/frontend/vite.config.ts:29-36`: con la página en `localhost:5173` y la
API en `127.0.0.1:8000`, `SameSite=lax` le prohíbe al navegador mandar la cookie en los
`fetch`, y **todo responde 401 después de un login exitoso**, sin ningún mensaje que
explique por qué. Encima la cookie CSRF queda guardada bajo `127.0.0.1`, así que
`document.cookie` desde `localhost` devuelve vacío y `tokenCsrf()`
(`api.ts:101-104`) tampoco encuentra nada. Dos fallas simultáneas, ningún síntoma legible.

**En este repo: por eso la página y la API tienen que ser el mismo sitio.** La solución no
fue aflojar `SameSite` sino eliminar el problema: el servidor de desarrollo de Vite
(`Proyecto - PWA/src/frontend/vite.config.ts:50-64`) actúa como
[proxy inverso](A0-03-http.md#proxy-inverso) y reenvía todo lo que empiece con `/api` al
backend, sacándole el prefijo (`vite.config.ts:61`). El navegador ve un único origen,
`http://localhost:5173`, y por lo tanto un único sitio. El cliente HTTP de la PWA apunta a
`/api` relativo y no a una URL absoluta (`api.ts:56`), justamente para que ni siquiera sea
posible equivocarse. Y el comentario de `vite.config.ts:43-46` deja asentado que esto no es
una muleta de desarrollo: en producción la PWA y la API van detrás del mismo dominio, así
que el proxy hace que desarrollo se parezca a producción en vez de diferir de ella.

La app de escritorio no pasa por nada de esto (`vite.config.ts:48-49`): no usa cookies, así
que no tiene sitio ni le importa.

---

## Token CSRF de doble envío

**El problema.** Si `SameSite=lax` ya frena el ataque de la sección anterior, ¿para qué
existe `backend/csrf.py`? Porque `lax` tiene tres grietas, y ninguna es hipotética:

1. **La excepción del propio `lax`.** Las navegaciones de nivel superior con método seguro
   sí llevan la cookie. Si algún día un `GET` de esta API escribiera en la base, `lax` no
   lo protegería. `backend/csrf.py:51-55` lo dice con todas las letras: la lista de métodos
   seguros "descansa en una regla que el resto del código tiene que respetar".
2. **Es una configuración, no una ley.** `COOKIE_SAMESITE` es una variable de entorno
   (`cookies.py:74`). Alguien que la ponga en `none` para resolver un problema de
   integración apaga la defensa entera sin tocar una línea de código.
3. **No todos los navegadores se comportan igual**, y el que atiende el mostrador del
   gimnasio no lo elige el sistema.

La respuesta clásica a eso es **defensa en profundidad**: una segunda cerradura que no
dependa del navegador. El patrón se llama *double submit cookie*.

> **↓ Capa 1 — el mecanismo, y de dónde sale su fuerza.**

En el login se emite, además de la cookie de sesión, **una segunda cookie con un valor
aleatorio** (`backend/csrf.py:58-60` · `generar_token_csrf()`). El cliente legítimo lee esa
cookie y **copia su valor a una cabecera** en cada pedido que modifique algo. El servidor
exige que la cabecera y la cookie coincidan.

La fuerza del patrón está en una asimetría exacta: **el atacante puede hacer que la cookie
se mande, pero no puede leerla.** Mandarla la manda el navegador solo; leerla requiere
ejecutar código en el origen `olimpos.local`, y eso lo impide la política del mismo origen.
Sin poder leer el valor, no puede armar la cabecera. Y si intentara agregar la cabecera a
ciegas, ya no sería un pedido simple: el navegador haría [preflight](#cors-y-preflight) y
el pedido moriría antes de salir.

Notá el detalle contraintuitivo: esta cookie es **deliberadamente legible** por JavaScript
(`httponly=False`, `backend/cookies.py:97`). Eso no la debilita, porque no es un secreto
que proteja nada por sí solo: es una prueba de que quien arma el pedido está corriendo
dentro del origen correcto.

> **↓ Capa 2 — los bytes y la comparación. Este es el piso.**

El valor sale de `secrets.token_urlsafe(32)` (`csrf.py:60`): 32 bytes del generador
criptográfico del sistema operativo, escritos en
[base64url](A0-11-criptografia-aplicada.md#aleatoriedad-criptográfica-y-base64url), lo que
da **43 caracteres** sin relleno. La cabecera se llama `X-CSRF-Token` (`csrf.py:49`).

Pedido legítimo de la PWA, con las dos mitades visibles:

```http
POST /api/socios/7/baja HTTP/1.1
Host: localhost:5173
Content-Type: application/json
X-CSRF-Token: 7Qk1sV3xZ...
Cookie: olimpos_session=eyJhbGciOiJIUzI1NiI...; olimpos_csrf=7Qk1sV3xZ...

{"motivo":"VOLUNTARIA"}
```

La comparación está en `backend/csrf.py:87`, y no usa `==`:

```python
if not cookie_csrf or not header_csrf or not secrets.compare_digest(cookie_csrf, header_csrf):
```

`compare_digest` compara en tiempo constante. La razón está escrita en `csrf.py:84-86`:
comparar cadenas con `==` corta apenas encuentra una diferencia, y esa diferencia de tiempo
—medible, aunque sean microsegundos— permite adivinar el valor carácter por carácter. La
comparación en tiempo constante recorre siempre todo. El mismo cuidado que se toma con las
contraseñas, por la misma clase de ataque
([función hash criptográfica](A0-11-criptografia-aplicada.md#función-hash-criptográfica)).

El fallo es **cerrado**: si falta la cookie, falta la cabecera o no coinciden, se responde
403 sin llegar al endpoint (`csrf.py:88-93`).

> **↓ Capa 3 — el agujero que le queda, dicho en serio.**

El doble envío se apoya en que el atacante no pueda **escribir** cookies en el dominio de
la víctima. Si pudiera —por ejemplo desde un subdominio hermano comprometido, porque las
cookies se comparten por dominio y **no distinguen puerto ni esquema**—, podría fijar la
cookie CSRF a un valor conocido y mandar la misma cabecera, y las dos mitades coincidirían.
Es la diferencia entre el doble envío y un token guardado del lado del servidor por sesión,
que no tiene esa debilidad. Este sistema corre en un servidor local con un solo host, así
que la superficie no existe hoy; conviene saber que existe el día que aparezcan
subdominios.

**En este repo, cerrando el descenso.** La barrera está montada como
[middleware](A0-10-python-del-lado-del-servidor.md#middleware) y no como
[dependencia](A0-10-python-del-lado-del-servidor.md#inyección-de-dependencias), y el
docstring de `backend/csrf.py:64-69` explica por qué en una frase que vale la pena
memorizar: "una dependencia hay que acordarse de ponerla en cada endpoint nuevo, y el día
que alguien se olvide, ese endpoint queda abierto sin que nada avise. Acá la protección es
por defecto y no hay forma de saltearla por descuido." Es el patrón **seguro por omisión**:
la única manera de quedar desprotegido tendría que ser un acto explícito, no un olvido.

El registro del middleware es `backend/main.py:233`. Del lado de la PWA, la cabecera la
arma `pedir()` en `Proyecto - PWA/src/frontend/src/services/api.ts:203-206`, para todo
método que no sea `GET` — la misma lista que protege el backend en `csrf.py:55`, con los
dos extremos escritos a mano y en archivos distintos.

Y hay una simetría elegante en `csrf.py:71-79`: el middleware deja pasar sin chequear nada
los métodos seguros **y** los pedidos que no traen la cookie de sesión. Lo segundo no es un
descuido: sin credencial ambiente no hay CSRF posible, por definición. Es lo que permite
que la app de escritorio, que manda su sesión a mano, no tenga que saber nada de todo esto.

---

## CORS y preflight

**El problema.** La política del mismo origen
([origen](A0-04-el-navegador-por-dentro.md#origen-y-política-del-mismo-origen)) es de 1995
y es tajante: una página de un origen no puede leer datos de otro. Eso protege, pero
también prohíbe cosas legítimas — por ejemplo, exactamente lo que querría hacer una PWA
servida desde `:5173` contra una API que vive en `:8000`. **CORS es la excepción
reglamentada a esa prohibición**: un protocolo por el cual el servidor destino declara qué
orígenes tienen permiso, y el navegador lo hace cumplir.

Conviene fijar de entrada quién manda: **CORS lo hace cumplir el navegador, no el
servidor**. Un `curl`, un script de Python o la app de escritorio ignoran CORS por
completo, porque no hay ninguna página cuyo origen proteger. Por eso CORS no es una barrera
de autorización: es una regla del navegador sobre qué respuestas puede *leer* el código de
una página.

> **↓ Capa 1 — dos categorías de pedido, y por qué.**

El navegador clasifica cada pedido entre sitios en dos:

- **Simple.** Método `GET`, `HEAD` o `POST`, y sólo cabeceras de una lista corta, con
  `Content-Type` limitado a `application/x-www-form-urlencoded`, `multipart/form-data` o
  `text/plain`. Se manda **directamente**, sin pedir permiso, y el navegador decide recién
  al volver si deja leer la respuesta. La categoría existe por compatibilidad histórica:
  son exactamente los pedidos que un `<form>` ya podía generar antes de que CORS existiera,
  así que prohibirlos habría roto la web.
- **Todo lo demás.** `PUT`, `DELETE`, cualquier cabecera inventada, `Content-Type:
  application/json`. Antes de mandar nada, el navegador hace un **preflight**: un pedido
  previo de consulta.

Acá se cierra la afirmación de la sección de CSRF: el ataque de formulario cae en la
primera categoría, y por eso CORS ni se entera.

> **↓ Capa 2 — el preflight, escrito. Este es el piso.**

Supongamos que alguien configura `VITE_API_URL` con la URL absoluta del backend
(`api.ts:56` lo permite) y la PWA deja de pasar por el proxy. El primer `POST` con
`Content-Type: application/json` más `X-CSRF-Token` deja de ser simple, y antes de mandarlo
el navegador emite esto, con método
[`OPTIONS`](A0-03-http.md#método-http-e-idempotencia) y **sin cuerpo y sin cookies**:

```http
OPTIONS /socios/7/baja HTTP/1.1
Host: 127.0.0.1:8000
Origin: http://localhost:5173
Access-Control-Request-Method: POST
Access-Control-Request-Headers: content-type,x-csrf-token
```

`CORSMiddleware` (`backend/main.py:214-227`) lo intercepta y contesta, si el origen está en
la lista:

```http
HTTP/1.1 200 OK
Access-Control-Allow-Origin: http://localhost:5173
Access-Control-Allow-Credentials: true
Access-Control-Allow-Methods: POST
Access-Control-Allow-Headers: content-type,x-csrf-token
Access-Control-Max-Age: <segundos que el navegador puede recordar este permiso>
Vary: Origin
```

Tres cosas que se leen de esa respuesta:

- **`Access-Control-Allow-Origin` devuelve el origen concreto, no un comodín.** Con
  `allow_credentials=True` la especificación **prohíbe** el comodín `*`, y eso está escrito
  en el comentario de `backend/main.py:221-223`: si se permitiera, cualquier página del
  mundo podría hacer pedidos autenticados a esta API desde el navegador de alguien con
  sesión abierta. Por eso la lista se lee del entorno en `_origenes_cors()`
  (`backend/main.py:45-61`), con `CORS_ORIGINS` en `backend/.env.example:56`, y por eso
  `main.py:59-60` imprime un aviso cuando queda vacía.
- **`Vary: Origin` es obligatorio** en cuanto la respuesta depende del origen: sin esa
  línea, un caché intermedio podría guardar la respuesta emitida para un origen y
  entregársela a otro, con el permiso equivocado adentro.
- **El `Max-Age` evita repetir el preflight** por un rato. Sin él, cada escritura costaría
  dos viajes de ida y vuelta en vez de uno — que en un sistema cuya base está lejos es
  justamente lo que no sobra.

Si el origen no está en la lista, la respuesta llega sin `Access-Control-Allow-Origin`, el
navegador aborta y el pedido real **nunca se manda**. Del lado de la PWA eso no se
distingue de un backend caído: `fetch` rechaza, y `pedir()` lo convierte en
`ServiceError(0, 'No se pudo conectar con el servidor')`
(`Proyecto - PWA/src/frontend/src/services/api.ts:221-228`). El comentario de
`api.ts:222-223` lo anota: `fetch` sólo rechaza por fallo de red, CORS o tiempo agotado,
nunca por un código 4xx o 5xx.

**En este repo, cerrando el descenso.** Y ahora la conclusión incómoda, que es lo que hace
interesante a esta sección: **en el flujo normal de desarrollo de OlimpOS, CORS casi no
interviene**. El proxy de `vite.config.ts:55-63` hace que todos los pedidos sean del mismo
origen, y un pedido del mismo origen no tiene preflight ni chequeo de CORS. El
`CORSMiddleware` de `main.py:214-227` está para dos casos concretos: que alguien apunte
`VITE_API_URL` al backend directamente, y el día que la API quede en un host distinto del
de la PWA. Es una barrera montada por si se la necesita, no una pieza del camino feliz — y
la cita de `vite.config.ts:40-41`, "de paso desaparece CORS por completo, porque ya no hay
pedidos cross-origin", es exactamente eso dicho por quien lo escribió.

> **Nota derivada del orden de los middlewares, no observada corriendo.** En
> `backend/main.py`, `CORSMiddleware` se registra en la línea 214, el middleware de CSRF en
> la 233 y el de cabeceras de seguridad en la 252. Starlette apila en orden inverso al de
> registro —el comentario de `main.py:229-232` lo dice—, así que el orden de entrada real es
> cabeceras de seguridad → CSRF → CORS → la ruta. Consecuencia: un rechazo del middleware de
> CSRF (`csrf.py:88-93`) devuelve su 403 **sin pasar de vuelta por `CORSMiddleware`**, así
> que esa respuesta sale sin `Access-Control-Allow-Origin`. En un escenario entre orígenes
> distintos, el navegador escondería el 403 y la PWA mostraría "no se pudo conectar" en vez
> del motivo real. Hoy no ocurre, porque con el proxy todo es del mismo origen; queda
> anotado para el día que deje de serlo.

---

## JWT

**El problema.** Volvamos a las dos familias de la sección [Sesión](#sesión). La sesión del
lado del servidor obliga a una consulta por pedido contra un almacén. Cuando ese almacén
está en otra máquina, del otro lado del continente, esa consulta se paga en milisegundos de
red en **cada pedido de cada pantalla**. La alternativa es que el cliente cargue la
identidad encima, y que el servidor pueda comprobar que no la tocó. Eso es un **token
autocontenido**, y el formato estándar es JWT (*JSON Web Token*, RFC 7519, 2015).

> **↓ Capa 1 — los tres tramos. Este es el piso del concepto.**

Un JWT es una sola cadena de texto ASCII con **exactamente dos puntos** que la parten en
tres tramos:

```
<cabecera>.<cuerpo>.<firma>
```

- **Cabecera.** Un objeto JSON que declara con qué algoritmo se firmó. En este sistema
  siempre `HS256` (`backend/auth.py:35` · `ALGORITMO`).
- **Cuerpo.** Otro objeto JSON con los datos de la sesión. Se los llama *claims*, y algunos
  nombres están estandarizados: `sub` (el sujeto), `iat` (emitido en) y `exp` (vence en).
- **Firma.** El resultado de aplicar
  [HMAC](A0-11-criptografia-aplicada.md#hmac-y-firma-simétrica) sobre los dos primeros
  tramos con la [clave secreta](A0-11-criptografia-aplicada.md#clave-secreta). Cómo se
  calcula y por qué no se puede falsificar sin la clave se explica en A0-11 y no se repite
  acá.

Los tres tramos van en
[base64url](A0-11-criptografia-aplicada.md#aleatoriedad-criptográfica-y-base64url), y el
punto se usa de separador precisamente porque ese alfabeto no lo incluye. El hecho que hay
que llevarse: **base64url es una codificación, no un cifrado.** El cuerpo de un JWT lo lee
cualquiera que tenga el token. No es secreto — es **inalterable**, que es una propiedad
distinta. Un JWT nunca lleva adentro nada que no se pueda mostrar.

> **↓ Capa 2 — el cuerpo del JWT de este sistema, campo por campo.**

`backend/auth.py:176-190` · `crear_token_acceso()` arma este diccionario, y esto es todo lo
que hay adentro de una sesión de OlimpOS:

```python
payload = {
    "sub": str(id_usuario),   # la spec de JWT pide que `sub` sea string
    "username": username,
    "roles": roles,
    "id_socio": id_socio,
    "id_profesor": id_profesor,
    "iat": ahora,
    "exp": ahora + timedelta(minutes=EXPIRACION_MINUTOS),
}
```

Tres decisiones que están escritas al lado, en el propio docstring:

- **`sub` lleva el `id_usuario`, no el `username`** (`auth.py:172-174`). El nombre de acceso
  se puede editar; el identificador no. Un token viejo tiene que seguir apuntando a la misma
  cuenta aunque le hayan cambiado el nombre.
- **Los roles viajan adentro** (`auth.py:165-170`). La alternativa era recalcularlos en cada
  pedido, y eso cuesta varios cruces contra la base por pedido para un dato que no cambia
  mientras dure la sesión. El precio de esta elección está dicho sin adornos en el mismo
  comentario: un cambio de rol no tiene efecto hasta el próximo ingreso.
- **`id_socio` e `id_profesor` viajan firmados** (`auth.py:158-163` y `:182-187`), y por eso
  los endpoints de "mis cosas" no aceptan un identificador por parámetro: no hay número que
  cambiar.

La verificación es una sola línea, `backend/auth.py:202`:

```python
return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITMO])
```

Dos detalles con consecuencias. El parámetro `algorithms` es una **lista blanca**: sin ella,
un atacante podría mandar un token cuya cabecera declare `alg: none` y la librería aceptaría
un token sin firma. Y el `except JWTError` de `auth.py:203-204` devuelve `None` sin
distinguir entre firma inválida, token alterado y token vencido, "porque no conviene decirle
al cliente cuál de los tres fue" — lo mismo que hace el login con los motivos de rechazo.

**En este repo, cerrando el descenso.** El token nace en `backend/auth.py:148-191`, se emite
en `backend/routers/auth_router.py:215-221`, y se valida en cada pedido dentro de
`backend/security.py:112-114`. La clave con la que se firma es `SECRET_KEY`
(`backend/auth.py:28`), leída del `.env`; si falta, el módulo se niega a importarse
(`auth.py:29-33`) — otro caso de fallar cerrado: no hay arranque silencioso con una clave
por omisión.

---

## Token portador y `Authorization`

**El problema.** Todo el aparato anterior —CSRF, `SameSite`, el proxy, CORS— existe por una
sola palabra: el navegador adjunta la cookie **solo**. ¿Y si el cliente no fuera un
navegador? Entonces nada de eso hace falta: el programa pone la credencial a mano, en cada
pedido, y nadie más puede provocar un envío que el programa no haya decidido.

Ese es el esquema *Bearer* — "portador" —, estandarizado en RFC 6750 (2012) como parte de
OAuth 2.0. El nombre es literal y describe el modelo de amenaza: **quien porta el token
es tratado como su dueño**, sin más preguntas. Es un billete al portador, con todo lo bueno
(cero estado, cero ceremonia) y todo lo malo (quien lo copie, entra) que eso implica.

> **↓ Capa 1 — la cabecera, escrita a mano. Este es el piso.**

Una sola línea, con el esquema y un espacio antes del valor:

```http
GET /socios HTTP/1.1
Host: 127.0.0.1:8000
X-Client-Type: escritorio
Authorization: Bearer eyJhbGciOiJIUzI1NiI...
```

En la app de escritorio la arma `_headers()`, `Flet/Proyecto/app/api_client.py:93-97`:

```python
def _headers() -> dict:
    cabeceras = dict(HEADERS_CLIENTE)
    if _token:
        cabeceras["Authorization"] = f"Bearer {_token}"
    return cabeceras
```

Y el token que interpola ahí vive en `_token`, una variable de módulo
(`app/api_client.py:45-49`) que **nunca se escribe en disco**. El comentario explica el
porqué del negocio, no del código: la app corre en la máquina compartida del mostrador del
gimnasio, así que la sesión tiene que morir al cerrar la aplicación. Se guarda en
`app/state.py:133` al entrar y se borra en `app/state.py:188` al salir; el borrado tira
además el caché de lecturas, porque las respuestas guardadas se trajeron con los permisos de
la sesión que se está cerrando (`api_client.py:61-72`).

Compará eso con la cookie: `Max-Age=28800` la deja sobrevivir a cerrar el navegador durante
ocho horas, en un archivo del perfil. Dos clientes, dos duraciones, dos lugares, y la
diferencia no es técnica sino de dónde está parada la máquina.

> **↓ Capa 2 — cómo lo lee el backend, y quién gana.**

Del lado del servidor la cabecera se declara en `backend/security.py:42`:

```python
esquema_token = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)
```

`auto_error=False` (explicado en `security.py:38-41`) hace que la ausencia de la cabecera no
dispare el error genérico de la librería, sino que devuelva `None` y deje que este código
decida — que es lo que permite aceptar **también** la cookie. Y `tokenUrl` es puramente
informativo, para el botón de autorizar de la documentación interactiva: el ingreso real es
un `POST /login` con cuerpo JSON, no el formulario estándar de OAuth 2.

La línea que resuelve el empate es `backend/security.py:108`:

```python
token = token_header or token_cookie
```

La cabecera gana sobre la cookie, y la razón está en `security.py:94-96`: es explícita. Si
alguien se molestó en ponerla, esa es la sesión que quiere usar; la cookie, en cambio, la
manda el navegador sin que nadie lo decida.

**En este repo, cerrando el descenso.** El mismo `obtener_sesion()`
(`backend/security.py:80-142`) atiende a los dos clientes con el mismo código, y después
hace algo que un token autocontenido no obliga a hacer: **relee el `Usuario` de la base en
cada pedido** (`security.py:121-122`). El motivo está en `security.py:102-106`: el token es
inmutable hasta que expira —ocho horas— y desactivar o bloquear una cuenta tiene que tener
efecto ya. Es una consulta por clave primaria, barata, y es la única forma de revocación
que este diseño admite. De eso trata la sección que sigue.

---

## Caducidad y revocación

**El problema, que en realidad son dos.** Que una sesión muera sola por el paso del tiempo y
que se la pueda matar antes de tiempo parecen la misma cosa, y son problemas distintos con
soluciones distintas. La caducidad es fácil: se escribe la fecha adentro del token y se
compara. La revocación es difícil justamente por lo que hace atractivo al token
autocontenido: **no hay ninguna fila que borrar.**

> **↓ Capa 1 — el instante comparado contra el vencimiento. Este es el piso.**

En el momento de emitir, `backend/auth.py:176` toma `datetime.now(timezone.utc)` y
`auth.py:189` escribe `exp = ahora + timedelta(minutes=EXPIRACION_MINUTOS)`, con
`EXPIRACION_MINUTOS = 480` por omisión (`auth.py:36`). Eso queda en el cuerpo del token
como un número de segundos desde 1970, en UTC.

En el momento de verificar, `jwt.decode()` (`auth.py:202`) compara ese número contra el
reloj del servidor, también en UTC. Si el instante actual pasó el vencimiento, lanza y
`decodificar_token()` devuelve `None` (`auth.py:203-204`). `obtener_sesion()` lo traduce en
un 401 (`backend/security.py:112-114`), y ese 401 es exactamente el que la PWA convierte en
una vuelta al ingreso — ver más abajo.

Dos observaciones sobre esa comparación. La primera: se hace **en UTC de las dos puntas**,
sin husos horarios, porque una comparación de instantes con husos mezclados es una fuente
inagotable de sesiones que vencen ocho horas antes o después. La segunda: el que decide es
**el reloj del servidor**. El `Max-Age` de la cookie (`cookies.py:79`) es apenas una
comodidad para que el navegador limpie sola la cookie muerta; si alguien copiara el texto de
la cookie y lo mandara con `curl` al día siguiente, el `Max-Age` no tendría ninguna
participación y el que lo rechazaría sería el `exp`.

> **↓ Capa 2 — revocar es otro problema, y este diseño no lo resuelve.**

Un token autocontenido, por construcción, **es válido hasta que vence**. El servidor no
guardó nada de él, así que no hay nada que invalidar. Cerrar la sesión no cambia eso: el
endpoint `POST /logout` (`backend/routers/auth_router.py:243-262`) sólo manda los dos
`Set-Cookie` de borrado, y su propio docstring lo dice sin vueltas en `auth_router.py:257-259`:
"el JWT en sí sigue siendo válido hasta que expire — así funcionan los tokens sin estado".

Ese endpoint, además, **tiene que existir**: la cookie de sesión es `httponly`, así que
JavaScript no puede borrarla. Sin el viaje al servidor, el "cerrar sesión" de la PWA
limpiaría la pantalla y dejaría la cookie viva en el navegador para el próximo que use esa
máquina (`auth_router.py:248-251`, y lo mismo del lado del cliente en
`Proyecto - PWA/src/frontend/src/services/authService.ts:114-116`).

Con eso planteado, este sistema tiene exactamente **tres** formas de cortar una sesión antes
de que venza, y ninguna es una lista de tokens revocados:

1. **Apagar la cuenta.** `obtener_sesion()` relee el `Usuario` y corta con 401 si no está
   activo o está bloqueado (`backend/security.py:121-123`). Es revocación de grano fino, al
   costo de una consulta por pedido.
2. **Marcar que tiene que cambiar la contraseña.** `security.py:129-134` rechaza cualquier
   token de una cuenta con `debe_cambiar_password` en verdadero, con su propio mensaje. Es
   lo que hace que resetearse la propia contraseña corte la sesión en el acto.
3. **Rotar `SECRET_KEY`.** Todas las firmas emitidas dejan de verificar de golpe. Es
   revocación total, sin grano: mata todas las sesiones de todo el mundo a la vez.

**En este repo, cerrando el descenso.** Del lado de la PWA, ese 401 no puede quedar como un
error cualquiera: quien lo recibe se queda en una pantalla que ya no carga nada, sin
entender que tiene que volver a entrar. El cliente HTTP avisa por una función registrada
(`Proyecto - PWA/src/frontend/src/services/api.ts:154-160` y `:241-243`), y `App.tsx:73-78`
registra qué hacer: limpiar la sesión del almacén y mostrar el motivo que mandó el backend.
Quedan afuera tres rutas donde un 401 **no** significa sesión caída (`api.ts:166`):
`/login`, `/cambiar-password` y `/me`, que son precisamente las que se llaman sin sesión.

---

## Los dos mecanismos de este sistema, y por qué son dos

Hasta acá cada pieza se explicó por separado. Esta sección hace la operación inversa: mirar
el código terminado y reconstruir la decisión que lo produjo.

**Qué se estaba optimizando.** Que la sesión de un navegador no se pueda **robar** —llevar a
otra máquina y usar después— sin pagar por eso una consulta a la base en cada pedido. La
amenaza concreta es XSS: cualquier credencial que JavaScript pueda leer, un script inyectado
también la lee y la manda afuera.

**Qué restricciones acorralaban la decisión.** Un solo backend para dos clientes que no se
parecen en nada: una PWA dentro de un navegador, con todo el modelo de amenazas del
navegador encima, y una aplicación de escritorio en la PC del mostrador, donde no hay
páginas donde inyectar scripts ni "otro sitio" que pueda disparar pedidos. Encima, una base
remota donde cada consulta cuesta caro, lo que descarta cualquier diseño que agregue viajes
por pedido.

**Qué alternativas había, y qué se pierde con cada una.**

- **Un token en el almacenamiento del navegador para la PWA también.** Es lo que este
  proyecto tenía antes; el comentario de `api.ts:72` deja el rastro. Se gana simplicidad
  entera: ni CSRF, ni `SameSite`, ni proxy, ni CORS. Se pierde lo único que importaba: un
  XSS se lleva la sesión.
- **Verificar `Origin` o `Referer` en el backend en vez del token de doble envío.** Las dos
  cabeceras están en el pedido falso de la Capa 2 de [CSRF](#csrf), así que la defensa es
  viable y más barata. Se pierde robustez: son cabeceras que en ciertos casos llegan
  ausentes o recortadas, y una defensa que falla abierto ante una cabecera faltante es peor
  que una que compara dos valores que siempre están.
- **Sesión del lado del servidor, con identificador opaco y tabla.** Resuelve la revocación
  de verdad, que es lo único que este diseño no tiene. Se pierde una consulta por pedido
  contra una base que está lejos, y hay que mantener un almacén de sesiones que hoy no
  existe.
- **Un solo mecanismo para los dos clientes.** Darle cookies a la app de escritorio no
  agrega ninguna seguridad —no hay XSS ni credencial ambiente que proteger— y le suma toda
  la maquinaria del CSRF. `backend/cookies.py:21-34` lo llama por su nombre: sería ceremonia
  sin beneficio.

**Cuál se eligió y qué se pagó.** Se eligió que **cada cliente use el mecanismo que resuelve
sus propias amenazas**, y el resultado son dos transportes para el mismo JWT:

| | PWA (navegador) | Escritorio (Flet) |
|---|---|---|
| Dónde viaja la sesión | cookie `olimpos_session`, `httponly` | cabecera `Authorization: Bearer` |
| Quién la adjunta | el navegador, solo | el programa, a mano |
| Defensa contra XSS | la cookie no se puede leer | no aplica: no hay páginas |
| Defensa contra CSRF | `SameSite=lax` + token de doble envío | no aplica: no hay credencial ambiente |
| Dónde vive | archivo del perfil del navegador, 8 h | variable de módulo, muere con el proceso |
| Qué exige del entorno | que la página y la API sean el mismo sitio | nada |
| Código | `backend/cookies.py`, `backend/csrf.py`, `api.ts:194-248` | `app/api_client.py:93-97` |

El precio de esa elección tiene tres partidas, y las tres son reales:

1. **La PWA no funciona sin que la página y la API sean el mismo sitio.** Es una dependencia
   de despliegue que no se ve en el código de ninguna pantalla, y cuando se rompe se
   manifiesta como 401 después de un ingreso exitoso, sin mensaje. Ya pasó una vez; quedó
   documentado en `api.ts:49-55` y el arreglo fue volver el valor por omisión relativo.
2. **Hace falta un endpoint para cerrar sesión**, porque la cookie `httponly` no la puede
   borrar el cliente (`auth_router.py:243-262`).
3. **No hay revocación real**, sólo las tres salidas de [Caducidad y revocación](#caducidad-y-revocación).

**Los nombres de los patrones**, que son lo que permite reconocer la misma jugada en otro
sistema: **defensa en profundidad** (`SameSite` y el token de doble envío atacan lo mismo
desde dos capas independientes), **fallar cerrado** (`csrf.py:87-93` rechaza cuando falta
cualquiera de las dos mitades; `auth.py:29-33` no arranca sin clave), **seguro por omisión**
(la protección es un middleware, no una dependencia que haya que recordar poner) y **token
al portador** con todo lo que implica.

Quién elige entre los dos transportes, con qué cabecera y qué cuesta que sea el cliente
quien la declara, es materia del capítulo de autenticación del sistema
([los dos mecanismos de sesión y `X-Client-Type`](A-07-autenticacion.md#los-dos-mecanismos-de-sesión-y-x-client-type));
acá alcanza con saber que la decisión se toma en `backend/routers/auth_router.py:223-231` y
que la rama del navegador deja `token` en nulo en la respuesta a propósito
(`auth_router.py:229-231`), porque si el token también viniera en el cuerpo, JavaScript
podría guardarlo y toda la ventaja de la cookie `httponly` se perdería.

> **⚠ Discrepancia entre el código y sus comentarios, anotada y no corregida.** Dos
> comentarios del repo dicen que la PWA guarda el token en `sessionStorage`:
> `backend/routers/auth_router.py:271-272` ("La PWA guarda el token en sessionStorage, pero
> NO los datos de la sesión") y
> `Proyecto - PWA/src/frontend/src/App.tsx:56-57` ("se le pregunta al backend por el token
> que quedó en sessionStorage"). **No es lo que hace el código.** Una búsqueda de
> `sessionStorage` sobre todo `Proyecto - PWA/src/frontend/src` devuelve tres apariciones y
> ninguna guarda la sesión: dos son comentarios —los citados— y la tercera es la mención
> histórica de `api.ts:72`. Los únicos usos de almacenamiento del navegador son
> `utils/colaRegistros.ts` y `views/socio/useCircuito.ts`, que no tienen nada que ver con la
> sesión. Gana el código: **la PWA no guarda el token en ningún lado**, tal como declara
> `api.ts:66-86`. Los dos comentarios quedaron de la implementación anterior, la que
> menciona `api.ts:72`. Lo que sí es exacto en ambos es la otra mitad de la frase: la
> identidad y los roles tampoco se guardan, y se le vuelven a preguntar al backend con
> `GET /me` en cada arranque (`authService.ts:126-135`, llamado desde `App.tsx:65-67`).

---

## Con qué se conecta

- **Existe por culpa de…** el pedido llega sin memoria, y toda la maquinaria de
  [Sesión](#sesión) está para reconstruirla
  ([A0-03](A0-03-http.md#sin-estado-stateless)).
- **Existe por culpa de…** el [token CSRF de doble envío](#token-csrf-de-doble-envío) sólo
  existe porque la [cookie](#cookie-y-sus-atributos) se reenvía sola; la app de escritorio,
  que manda la sesión a mano, no lo necesita.
- **Existe por culpa de…** el proxy `/api` de Vite está para que la página y la API sean el
  mismo sitio y `SameSite=lax` deje viajar la cookie
  ([A-04](A-04-recorrido-de-un-pedido.md#proxy-api-de-vite)).
- **Existe por culpa de…** [CORS y preflight](#cors-y-preflight) es la excepción
  reglamentada a la política del mismo origen
  ([A0-04](A0-04-el-navegador-por-dentro.md#origen-y-política-del-mismo-origen)).
- **Existe por culpa de…** los roles viajan firmados en el [JWT](#jwt) justamente para no
  derivarlos en cada pedido ([A-06](A-06-los-seis-roles.md#derivación-de-roles)).
- **Se contradice con…** la única revocación total que admite un JWT es rotar la
  [clave secreta](A0-11-criptografia-aplicada.md#clave-secreta), y eso mata todas las
  sesiones a la vez: [Caducidad y revocación](#caducidad-y-revocación) es esa contradicción,
  asumida.
