# A-07 · Autenticación

*Piso del capítulo: la línea de código que acepta o rechaza a una persona.*

Los mecanismos genéricos ya están explicados: cómo se firma un token en
[criptografía aplicada](A0-11-criptografia-aplicada.md), y qué es una cookie, un token
CSRF y un token portador en [sesiones y autenticación](A0-12-sesiones-y-autenticacion.md).
Este capítulo no los repite. Cuenta **cómo los usa este sistema**, siguiendo la vida de
una cuenta de acceso desde que nace hasta que opera en cada pedido, y se detiene en las
cinco decisiones que hacen que OlimpOS autentique distinto de un sistema cualquiera.

El recorrido tiene este orden, y cada sección es una etapa:

```
alta en el mostrador → contraseña temporal → primer ingreso → cambio de clave
  → login (con sus frenos) → token con la identidad firmada → cada pedido
```

---

## No existe "Registrarse"

### La decisión

En la mayoría de los sistemas web, una cuenta nace cuando alguien completa un formulario.
En OlimpOS **no hay formulario**: no existe ninguna ruta que cree una cuenta de acceso a
pedido de quien la va a usar. `CLAUDE.md` lo dice con la contundencia de las decisiones
que ya se discutieron: *"No hay 'Registrarse', ni siquiera pagando"*.

### La ruta que no está

Este es el piso de la sección, y es una ausencia. El router de autenticación,
`backend/routers/auth_router.py`, tiene exactamente cuatro rutas:

| Ruta | Qué hace |
|---|---|
| `POST /login` | abre una sesión |
| `POST /logout` | la cierra |
| `GET /me` | devuelve la sesión vigente |
| `POST /cambiar-password` | cambia la clave de una cuenta que ya existe |

Ninguna crea una cuenta. Las únicas líneas de todo el backend que insertan un `Usuario` están
en las dos altas del personal: la de socios (`backend/routers/socios.py`, dentro de
`alta_socio()`) y la de empleados (`backend/routers/personal.py`). Y la especificación
confirma lo mismo desde el otro lado: entre los 173 procesos de
`PROCESOS-LOGICOS-REQUERIDOS.md`, la sección "Acceso y sesión" son cinco procesos, y
ninguno es un registro. (Las dos rutas del portal que contienen "registro" en el nombre son
`/mi-rutina/registro-ejercicio`: el registro de series de una rutina, no de una cuenta.)

### Por qué está hecho así

**Qué se optimiza:** que cada cuenta corresponda a una persona que el gimnasio dio de alta
en el mostrador. En un gimnasio, tener acceso significa ser socio o ser del personal, y las
dos cosas las decide la administración, no quien quiere entrar.

**Qué alternativas se descartaron:** el registro abierto, por supuesto. Pero también el
registro atado a un pago: *"ni siquiera pagando"* descarta explícitamente que pagar una
cuota online dé acceso por sí solo. El pago es una consecuencia de ser socio, no la puerta
para serlo.

**Qué se pagó:** dos cosas. Toda alta la hace una persona del personal, y la contraseña
inicial hay que **entregarla**, porque quien la va a usar no la eligió. Resolver esa entrega
es el tema de la sección siguiente.

**Lo que se gana de yapa:** todo lo que un registro abierto obliga a construir y que este
sistema no tiene: verificar el mail, frenar cuentas falsas, limpiar cuentas abandonadas.

---

## Contraseña temporal y primer ingreso

### El problema

Si la cuenta la crea el personal, alguien tiene que elegir la primera contraseña. Si la
elige el recepcionista, la conocen dos personas, y probablemente sea débil: con una cola
adelante, lo que se tipea es `Gimnasio1`. Si la elige el sistema, hay que entregarla, y la
persona tiene que poder reemplazarla por una propia.

La solución de OlimpOS tiene cuatro piezas, y cada una tapa un agujero de la anterior.

### 1 · La cuenta nace marcada

El alta genera el nombre de usuario y la contraseña, guarda **sólo el hash** y marca la
cuenta con `debe_cambiar_password=True`. En el alta de socio es el bloque de
`backend/routers/socios.py:406-432`, con un comentario que resume el diseño: *"El corazón del
flujo: la cuenta nace exigiendo el cambio. El primer login verifica esta contraseña pero NO
emite token"*.

La contraseña la genera `generar_password_temporal()`: 96 bits aleatorios de la fuente
criptográfica del sistema. Por qué eso la vuelve inmune a un diccionario, y por qué son 96 y
no los 72 que decía un comentario, está en
[aleatoriedad criptográfica y base64url](A0-11-criptografia-aplicada.md#aleatoriedad-criptográfica-y-base64url).

### 2 · Se muestra una sola vez, porque no hay otra forma

La contraseña sale del backend **una única vez**: en la respuesta del alta
(`password_temporal=password_temporal` en `backend/routers/personal.py:359`, y lo mismo en
el alta de socio). No hay ninguna columna que la guarde en texto: ni `db/schema.sql` ni
`backend/models.py` tienen un campo así, sólo `password_hash`.

Por eso "se muestra una sola vez" no es una regla que alguien tenga que respetar: **es
imposible mostrarla de nuevo**, porque el sistema no la tiene. Lo que guarda es un hash, y
[un hash no se lee, se reemplaza](A0-11-criptografia-aplicada.md#ataque-de-diccionario).

Como esa única vez es la oportunidad de entregarla, la PWA la muestra en
`PanelCredenciales` (`Proyecto - PWA/src/frontend/src/components/PanelCredenciales.tsx`) con
botones para mandarla por mail o por WhatsApp. El de mail abre el redactor de Gmail y no un
`mailto:`, porque las PCs del gimnasio no tienen cliente de correo instalado.

### 3 · El primer login no da sesión

Con la contraseña temporal correcta, el login **no emite token**. Responde
`{"debe_cambiar_password": true}` y nada más (`backend/routers/auth_router.py:181-184`).

El orden de las comprobaciones es deliberado, y el comentario de las líneas 173-176 lo
explica: la marca se revisa **después** de validar la contraseña —*"para no revelar el estado
de una cuenta ajena"*— y **antes** de emitir el token. Si se revisara antes, cualquiera que
tipeara un usuario ajeno con una contraseña inventada sabría si esa cuenta está esperando su
primer ingreso.

### 4 · El cambio de clave, y por qué tampoco da sesión

`POST /cambiar-password` (`auth_router.py:292-338`) es **público**: no pide sesión, porque
quien lo usa todavía no puede tenerla. Pide la contraseña actual y la nueva, rechaza con 400
si son iguales, guarda el hash nuevo y baja la marca.

Y **no emite token**, a propósito. El docstring lo justifica en una línea (298-302): la
persona *"tiene que ingresar de nuevo: este endpoint no emite token a propósito, para que el
primer uso de la contraseña nueva sea un login normal y quede probada"*. Si el cambio abriera
sesión directamente, alguien podría cambiar la clave, seguir usando el sistema ocho horas y
descubrir al día siguiente que la tipeó mal.

### La bandera que rechaza el token

La marca `debe_cambiar_password` no sólo corta el primer login. `obtener_sesion()`, la función
que valida la sesión en **cada** pedido, la revisa de nuevo (`backend/security.py:125-134`):

```python
if usuario.debe_cambiar_password:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Tenés que cambiar tu contraseña antes de seguir usando el sistema.",
        ...
```

Ése es el piso de la sección: una bandera en una fila, que convierte en inútil **cualquier**
token de esa cuenta, aunque sea válido, esté firmado y no haya vencido. El comentario de las
líneas 125-128 dice para qué: *"Un token emitido antes de un reseteo de contraseña no debe
seguir sirviendo"*.

Esa línea es la que hace cierta una regla de `CLAUDE.md` que se ve rara a primera vista:
**resetearse la propia contraseña corta la sesión.** El reseteo prende la marca, el siguiente
pedido la encuentra, y la sesión muere con un 401 que la PWA traduce en volver al login con
el motivo. No hace falta ninguna lista de sesiones revocadas: alcanza con que la bandera se
lea en cada pedido, y se lee porque el usuario se relee siempre (ver
[identidad firmada](#identidad-firmada)).

Y también explica el único caso del que la aplicación no puede salir. Si el único Dueño se
resetea la clave y pierde la temporal, nadie puede resetearlo desde la app —sólo un Dueño
opera sobre un Dueño— y la salida es reescribirle el hash en la base. Es exactamente lo que
`docs/ESTADO-ACTUAL.md` registra hoy sobre la cuenta `dueno`.

---

## Freno de intentos y respuesta indistinguible

### El problema de origen

La pantalla de login es una puerta que cualquiera puede golpear. El
[ataque de diccionario](A0-11-criptografia-aplicada.md#ataque-de-diccionario) contra una
base robada se frena con un hash lento; contra la pantalla de login, donde el atacante prueba
de a una contraseña por pedido, hace falta otra cosa: **limitar cuántas veces se puede
probar**.

El primer intento de este sistema hacía lo obvio, y lo obvio era un agujero. El docstring de
`backend/limite_intentos.py:13-18` lo cuenta: el quinto fallo ponía `Usuario.bloqueado=true`
**para siempre**, y desbloquear exigía que otra persona con permiso lo hiciera. Un atacante
no necesitaba adivinar nada: *"dejaba al gimnasio sin acceso administrativo con ~40
pedidos"* —cinco fallos contra cada cuenta del personal—. Una defensa contra fuerza bruta se
había convertido en una herramienta de **denegación de servicio**. Es la vulnerabilidad que
`docs/vulnerabilidades a arreglar.md` anota como V-02.

### Los dos frenos

La versión actual reemplaza el bloqueo permanente por dos frenos que se complementan:

| Freno | Umbral | Consecuencia | Dónde se cuenta |
|---|---|---|---|
| **Por cuenta** | 5 fallos seguidos | la cuenta queda **trabada 15 minutos** | contador en la base, traba en memoria |
| **Por IP** | 20 fallos en 10 minutos | **429**, desde esa conexión | todo en memoria |

Las constantes: `MAX_INTENTOS_FALLIDOS = 5` (`backend/routers/auth_router.py:49`),
`BLOQUEO_CUENTA_SEG = 15 * 60`, `MAX_FALLOS_POR_IP = 20` y `VENTANA_IP_SEG = 10 * 60`
(`backend/limite_intentos.py:37-39`).

Ahora lo peor que logra un atacante contra una cuenta es demorarla 15 minutos, y el freno por
IP le impide sostenerlo: después de 20 fallos deja de poder probar.

> **↓ Capa 1 — el contador en la base y la traba en memoria.** Este es el piso.

La combinación es menos obvia de lo que parece. `_registrar_intento_fallido()`
(`auth_router.py:83-100`) hace esto:

```python
limite.registrar_fallo_ip(ip)
usuario.intentos_fallidos = (usuario.intentos_fallidos or 0) + 1
if usuario.intentos_fallidos >= MAX_INTENTOS_FALLIDOS:
    limite.trabar_cuenta(usuario.username)
    usuario.intentos_fallidos = 0
db.commit()
```

El contador de la cuenta vive en la **columna** `Usuario.intentos_fallidos`. La traba vive en
un **diccionario en memoria** (`_trabada_hasta`, `limite_intentos.py:43`) que guarda, para
cada usuario trabado, el momento hasta el que lo está.

El `db.commit()` del final es la línea más importante, y el docstring (líneas 92-93) dice
por qué: *"El contador se guarda con commit aunque la request termine en 401: si se perdiera
al hacer rollback, el freno nunca llegaría a dispararse"*. El endpoint va a terminar con un
error, y un error normalmente descarta lo que el pedido cambió. Si el contador se descartara
con él, cada fallo arrancaría de cero y el quinto nunca llegaría. Confirmar antes de fallar
es la forma de que el fallo deje rastro. La diferencia entre mandar y confirmar está en
[`flush` contra `commit`](A0-09-el-orm.md#flush-contra-commit).

¿Por qué la traba en memoria y no en otra columna? `limite_intentos.py:23-26` lo explica:
*"no hace falta que sobreviva a un reinicio (un reinicio que destraba cuentas no le sirve a un
atacante) y así no suma una columna ni una consulta en cada login"*. Y deja anotado el día en
que eso cambia: con varios procesos detrás de un balanceador, cada uno tendría su propio
diccionario, y la traba tendría que pasar a un almacén compartido.

Los tiempos se miden con `time.monotonic()` y no con la hora del reloj. El reloj del sistema
puede saltar —un ajuste de hora por red lo mueve para adelante o para atrás—, y una traba
calculada contra él podría durar horas o ninguna. El reloj monotónico sólo avanza: mide
duraciones, no horas del día.

### La IP que no se puede falsificar

La IP se toma del socket (`request.client.host`, `auth_router.py:69-72`), **no** de la
cabecera `X-Forwarded-For`. `limite_intentos.py:28-31` explica las dos caras de esa elección.
La cabecera la escribe el cliente, así que un atacante la cambiaría en cada pedido y el freno
por IP no lo frenaría nunca. Pero la del socket tiene su propio límite: detrás de un proxy
propio —el de Vite en desarrollo, un nginx en producción— **todos** los pedidos llegan desde
la misma IP, la del proxy. Por eso el tope por IP es holgado (20) y el que de verdad protege
cada cuenta es el freno por cuenta. En desarrollo todo llega desde `127.0.0.1`.

### Cuatro motivos, una sola respuesta

Hay cinco razones por las que un login puede fallar: la cuenta no existe, está inactiva, está
bloqueada a mano, está trabada, o la contraseña está mal. Las cuatro primeras las junta
`_cuenta_no_disponible()` (`auth_router.py:103-105`), y **las cinco** terminan en el mismo
lugar: `_rechazar()`, que devuelve un 401 con un único texto,

```python
CREDENCIALES_INVALIDAS = "Usuario o contraseña incorrectos"
```

(`auth_router.py:46-47`, con el comentario *"Un solo texto para los cuatro motivos posibles
de rechazo"*).

La razón es que cualquier diferencia en la respuesta es información para el atacante. Si
"el usuario no existe" respondiera distinto que "contraseña incorrecta", la pantalla de login
serviría para averiguar qué nombres de usuario son válidos, y el ataque se concentraría en
esos. Si "cuenta trabada" respondiera distinto, el atacante sabría cuándo su ráfaga surtió
efecto.

El costo lo paga la persona legítima: con la cuenta trabada, ve "contraseña incorrecta"
aunque escriba la correcta. Las salidas son esperar los 15 minutos, pedir "Desbloquear" en
Usuarios (que llama a `destrabar()`, `limite_intentos.py:80-83`), resetear la contraseña o
reiniciar el backend, que vacía el diccionario. Mientras está trabada, los intentos nuevos no
tocan el contador de la cuenta —`_cuenta_no_disponible()` corta antes—, así que insistir no
alarga la traba.

> **↓ Capa 2 — indistinguible también en el tiempo.**

Un mensaje idéntico no alcanza, y el repo lo aprendió: es la vulnerabilidad V-03. Cuando la
cuenta existe, el login corre bcrypt para verificar la contraseña, y eso tarda lo que se midió
en [sal y hash lento](A0-11-criptografia-aplicada.md#sal-y-hash-lento): unos 171 ms. Cuando la
cuenta no existe, no hay hash contra el cual verificar, y la respuesta vuelve casi al
instante. El texto era el mismo, pero **el reloj delataba qué usuarios existían**.

La corrección está en `auth_router.py:63-66`:

```python
# V-03: el mensaje era único pero el TIEMPO delataba qué usuarios existen —
# bcrypt (~200 ms) sólo corría si la cuenta existía. Con un usuario inexistente
# se verifica igual contra este hash, así las dos respuestas tardan lo mismo.
_HASH_DE_RELLENO = hashear_password("relleno-para-igualar-tiempos")
```

y en la línea 157, donde se usa: con una cuenta no disponible, se verifica igual la
contraseña tipeada contra ese hash de relleno, sabiendo que va a fallar, sólo para gastar el
mismo tiempo. Es un bcrypt que no sirve para nada salvo para ser indistinguible.

### El mismo contador, en el cambio de clave

`cambiar-password` es público y pide la contraseña actual, así que es otra puerta para probar
contraseñas. Por eso aplica exactamente las mismas defensas, con las mismas funciones:
`_frenar_si_excede()`, `_cuenta_no_disponible()`, el hash de relleno y
`_registrar_intento_fallido()` (`auth_router.py:307-323`). El comentario de las líneas
312-315 da el motivo: *"Este endpoint es público, así que si respondiera distinto se
convertiría en un detector de usuarios válidos"*.

La consecuencia es la regla de `CLAUDE.md` que dice que **los fallos de "contraseña actual" al
cambiarla suman al mismo contador** que los del login: son la misma columna, incrementada por
la misma función.

---

## Identidad firmada

### El ataque

El portal del socio muestra "Mi cuota", "Mis turnos", "Mi rutina". La forma ingenua de
construirlo es que la pantalla mande el número de socio y el backend devuelva sus datos:

```
GET /portal/mi-cuota?id_socio=7
```

Y el ataque es cambiar el 7 por un 8. Si el backend no verifica que el socio 8 sea quien
pregunta, devuelve los pagos de otra persona. Tiene nombre: **referencia directa insegura a un
objeto** (IDOR, por sus siglas en inglés), y es una de las fallas más comunes de la web. No
requiere ninguna herramienta, sólo editar un número en la barra de direcciones.

### La defensa: el id no viene del cliente

En OlimpOS, **ningún endpoint de "mis cosas" acepta un id de socio o de profesor por
parámetro**. El id sale de la sesión, y la sesión es un JWT **firmado** en el login. El
formato de ese token y sus campos, uno por uno, están en
[JWT](A0-12-sesiones-y-autenticacion.md#jwt); por qué nadie puede alterar un campo sin
invalidar la firma, en
[HMAC y firma simétrica](A0-11-criptografia-aplicada.md#hmac-y-firma-simétrica). Lo que importa
acá es la consecuencia: el `id_socio` que llega al backend es el que el backend mismo puso al
iniciar sesión, y no hay forma de cambiarlo sin romper el token.

> **↓ Capa 1 — el campo dentro del token, y la única puerta.** Este es el piso.

En el login se resuelven los dos ids una sola vez (`auth_router.py:196-205`): el `id_socio`
buscando la ficha de socio de la persona, y el `id_profesor` navegando persona → empleado →
profesor. Van al token, y de ahí a la `Sesion` que `obtener_sesion()` arma en cada pedido
(`security.py:140-142`).

Del lado de los endpoints, el portal tiene **una sola puerta** a los datos del socio,
`_mi_socio()` (`backend/routers/portal.py:90`), y el docstring la define exactamente así:
*"El Socio de la sesión activa. Es la única puerta de entrada a los datos de este router"*.
Aparece 42 veces en ese archivo. Toma la sesión, no un parámetro:

```python
if sesion.id_socio is None:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                        detail="Tu cuenta no está asociada a una ficha de socio.")
socio = db.get(Socio, sesion.id_socio)
```

"Mis clases" del profesor tiene su gemela en las líneas siguientes, a partir de
`sesion.id_profesor` (`portal.py:126-138`), y el filtro de la agenda lo dice sin vueltas en la
línea 207: *"El filtro es `Turno.id_profesor == sesion.id_profesor`"*.

Dos detalles del diseño de esa puerta. El rechazo es **403 y no 404**: el docstring explica
que no es que el recurso no exista, es que quien pregunta no es socio —un empleado que no
entrena en el gimnasio cae ahí—. Y hay un segundo rechazo para un caso raro pero real: *"el
token trae un id que ya no existe: le borraron la ficha con la sesión abierta"*.

El documento de vulnerabilidades cierra el tema desde el lado de la verificación: lista el
IDOR entre los vectores que se probaron y resultaron sólidos.

### Por qué se resuelve una vez y se relee siempre

Hay dos decisiones que parecen contradecirse y no lo hacen.

**Los ids y los roles se resuelven una vez, en el login**, y viajan en el token. El docstring
de `crear_token_acceso()` (`backend/auth.py:158-170`) da el porqué: recalcular los roles en
cada pedido *"costaría cinco JOINs por pedido para un dato que no cambia mientras dura la
sesión"*. Con la base a 44 ms por viaje, eso no es un detalle
([base remota](A-11-rendimiento.md#base-remota)).

**Pero el usuario se relee de la base en cada pedido.** `obtener_sesion()` hace
`db.get(Usuario, id_usuario)` siempre (`security.py:121`), y el docstring (líneas 102-106)
explica por qué, si el token ya trae la identidad: *"el token es inmutable hasta que expira (8
horas) y hace falta que desactivar o bloquear una cuenta tenga efecto YA. Sin esta consulta,
alguien a quien le acaban de dar de baja seguiría operando el resto de la jornada"*.

La conciliación es qué dato se lee de dónde. Lo que **no cambia** durante una sesión —quién
sos, qué rol tenés— viene del token, gratis. Lo que **puede cambiar** y tiene que tener efecto
inmediato —si tu cuenta sigue activa, si está bloqueada, si tenés que cambiar la clave— se lee
de la base, una consulta por clave primaria. El costo de la primera mitad está en
`auth.py:168-170`: *"un cambio de rol no tiene efecto hasta el próximo login"*. Y como el JWT
no se puede revocar ([caducidad y revocación](A0-12-sesiones-y-autenticacion.md#caducidad-y-revocación)),
releer el usuario es el mecanismo que le da al sistema una revocación de hecho, cuenta por
cuenta.

### Nota marcada · el ejemplo del profesor sin rol

El login rechaza con 403 a una cuenta sin ningún rol, y el comentario que lo acompaña da un
ejemplo (`auth_router.py:188`): *"Cuenta sin ningún rol de sesión (por ejemplo, la de un
Profesor)"*.

**Ese ejemplo quedó viejo.** El docstring de `roles_de_persona()` en `backend/models.py` dice
que el Profesor *"desde el 2026-09-16 SÍ tiene rol"*, y hoy un profesor entra a la PWA a ver
"Mis clases". El rechazo por falta de rol sigue existiendo y sigue siendo correcto para una
cuenta cuya persona no es socio, ni empleado, ni dueño. Lo que no aplica más es el ejemplo.
Gana el código. Cómo se derivan los roles es tema de [los seis roles](A-06-los-seis-roles.md).

---

## Los dos mecanismos de sesión y `X-Client-Type`

Por qué este sistema usa dos transportes para el mismo token —cookie `httponly` con token
CSRF en la PWA, token portador en Flet—, qué amenaza resuelve cada uno y qué se descartó,
está explicado entero en
[los dos mecanismos de este sistema](A0-12-sesiones-y-autenticacion.md#los-dos-mecanismos-de-este-sistema-y-por-qué-son-dos).
Esa sección delega a ésta una pregunta concreta: **quién elige el transporte, con qué
cabecera, y qué cuesta que sea el cliente quien lo declara.**

### Dos cabeceras, dos trabajos

`CLAUDE.md` lo resume en una frase: *"Flet manda `X-Client-Type: escritorio` y recibe un token
Bearer. El header gana sobre la cookie."* La frase es cierta, pero comprime dos cabeceras
distintas en una, y conviene separarlas porque trabajan en momentos diferentes.

**`X-Client-Type` se mira una sola vez: en el login.** Decide **por dónde sale** el token que
se acaba de emitir. `auth_router.py:220-228`:

```python
es_escritorio = (x_client_type or "").strip().lower() == CLIENTE_ESCRITORIO

if es_escritorio:
    token_en_cuerpo = token
else:
    setear_cookies_sesion(respuesta, token=token, csrf=generar_token_csrf())
    # None y no el token: que el navegador no pueda leerlo es todo el
    # punto de la cookie httponly.
    token_en_cuerpo = None
```

Con `escritorio`, el token viaja en el cuerpo de la respuesta y Flet lo guarda. Con cualquier
otra cosa —o sin cabecera—, el token viaja en una cookie que JavaScript no puede leer, y el
cuerpo lo trae en nulo.

**`Authorization: Bearer` se mira en cada pedido.** Es la que decide **qué token se usa**.
`obtener_sesion()` no consulta `X-Client-Type` en ningún momento. Resuelve el token así
(`security.py:108`):

```python
token = token_header or token_cookie
```

Ésa es la línea que hace "ganar" al header: si llegó un `Authorization: Bearer`, se usa ése;
sólo si no llegó, se busca la cookie. El docstring (líneas 94-96) da el criterio: *"El header
tiene prioridad porque es explícito: si alguien se molestó en ponerlo, esa es la sesión que
quiere usar. La cookie, en cambio, la manda el navegador sola."*

> **↓ Capa 1 — la cabecera que decide cuál gana.** Este es el piso.

Con las dos separadas, el recorrido de cada cliente queda exacto:

| Momento | PWA | Flet |
|---|---|---|
| Login | sin `X-Client-Type` → recibe cookies, cuerpo con `token: null` | `X-Client-Type: escritorio` → recibe el token en el cuerpo |
| Cada pedido | el navegador adjunta la cookie sola; no hay `Authorization` | adjunta `Authorization: Bearer <token>` a mano |
| En `security.py:108` | `token_header` vacío → usa `token_cookie` | `token_header` presente → lo usa y la cookie no importa |

### Por qué está hecho así, y su costo: V-11

**Qué se eligió:** que el cliente **declare** qué es. No hay otra forma práctica de que el
servidor lo sepa. Un servidor no puede distinguir con certeza un navegador de otro programa:
todo lo que llega en un pedido —incluida la cabecera `User-Agent`— lo escribe el cliente.

**Qué se paga:** la protección de la cookie `httponly` es **opcional para quien la pide**.
Cualquier cliente que tenga usuario y contraseña puede hacer login con `X-Client-Type:
escritorio` y recibir el token en el cuerpo, donde es legible. No es una puerta abierta
—para pedirlo hace falta la contraseña—, pero es una defensa que el cliente puede apagar.

Es exactamente lo que el documento de vulnerabilidades anota como **V-11**, clasificada como
endurecimiento pendiente y no como vulnerabilidad: *"El header `X-Client-Type` (elegido por el
cliente) decide cookie-httponly vs token-en-cuerpo"*. Queda pendiente, con el costo a la vista.

**Cómo se llama:** una declaración del cliente cruzando una **frontera de confianza**. Todo
lo que viene del otro lado de esa frontera es información, no garantía; el diseño es correcto
mientras ninguna decisión de seguridad **dependa sólo** de ella. En este sistema no depende:
sin contraseña válida, `X-Client-Type` no sirve para nada.

---

## Con qué se conecta

- **Es la misma idea que…** `compare_digest`
  ([HMAC y firma simétrica](A0-11-criptografia-aplicada.md#hmac-y-firma-simétrica)): el hash
  de relleno hace con el login lo que `compare_digest` hace con una firma, no filtrar un
  secreto por el reloj.
- **Es el mismo problema que…** el
  [ataque de diccionario](A0-11-criptografia-aplicada.md#ataque-de-diccionario): probar
  contraseñas, en línea contra esta pantalla y sin conexión contra una base robada; acá lo
  frena el contador, allá el hash lento.
- **Existe por culpa de…** que el JWT no se puede revocar
  ([caducidad y revocación](A0-12-sesiones-y-autenticacion.md#caducidad-y-revocación)):
  releer el usuario en cada pedido es lo que hace que dar de baja o resetear una clave corte
  la sesión en el acto.
- **Se contradice con…** la [base remota](A-11-rendimiento.md#base-remota): releer el usuario
  cuesta un viaje por pedido en el sistema que cuenta viajes; ganó la baja inmediata sobre los
  44 ms.
- **Es la misma idea que…** la [autorización](A-08-autorizacion.md): la identidad firmada
  dice *quién* pregunta; la matriz de permisos, *qué* puede pedir.
- **Existe por culpa de…** [`flush` contra `commit`](A0-09-el-orm.md#flush-contra-commit): el
  contador de fallos se confirma antes del 401, porque un error descarta lo no confirmado.
