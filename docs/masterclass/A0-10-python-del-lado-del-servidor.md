# A0-10 · Python del lado del servidor

> **Piso de este capítulo:** *por qué esperar la red no bloquea y calcular sí.* Bajamos
> desde la firma de un endpoint hasta el candado que el intérprete suelta cuando se
> queda esperando un paquete, y paramos ahí. Un escalón más abajo —cómo el sistema
> operativo despierta un hilo dormido— ya no explica ninguna decisión de OlimpOS.

---

## Por dónde empieza el problema

Un pedido HTTP llega a la máquina donde corre el backend como una tira de bytes sobre una
conexión TCP abierta contra un puerto. Eso es todo lo que hay: ni funciones, ni objetos,
ni "usuario logueado". Del otro lado hay 167 operaciones de API que alguien escribió como
funciones de Python, cada una con su nombre, sus parámetros y su cuerpo.

Ese 167 sale de contar: **165** decoradores `@router.*` en `backend/routers/*.py`, más
`@app.get("/")` en `backend/main.py:327`, más una ruta que se registra sin decorador y sólo
en modo simulado (`backend/routers/pagos_online.py:397-399`, que se explica más abajo). Es
el mismo número que declara `PROCESOS-LOGICOS-REQUERIDOS.md` cuando cuenta *por operación*.
Conviene no confundirlo con las **130** de `docs/ESTADO-ACTUAL.md`: ese otro número cuenta
**rutas distintas** en `/openapi.json`, y una misma ruta con `GET` y `POST` es una sola
entrada ahí y dos operaciones acá.

El hueco entre esas dos cosas es lo que resuelve todo este capítulo. Y lo resuelve tres
veces, porque el hueco tiene tres partes distintas que se suelen confundir en una sola:

1. **Quién lee el socket** y convierte bytes en algo que Python pueda mirar.
2. **Quién decide qué función llamar** y con qué argumentos ya construidos.
3. **Quién decide en qué hilo corre esa función**, y qué pasa mientras esa función está
   parada esperando que São Paulo conteste.

La tercera es la que define el rendimiento de este sistema entero, y es la que casi nadie
mira. Las dos primeras son las que definen cómo se lee el código.

Antes de arrancar, dos datos que van a aparecer todo el tiempo. El backend corre sobre
**Python 3.11.9** (`backend/.venv/pyvenv.cfg:3`) y usa **FastAPI ~0.115** sobre
**uvicorn ~0.32** (`backend/requirements.txt:8-9`). Los archivos de esas dos librerías
están instalados en `backend/.venv/Lib/site-packages/`; no están versionados en el repo,
pero están en el disco de esta máquina y cada línea que se cita de ahí fue abierta y
leída. Cuando una cita apunte al venv, lo digo.

---

## ASGI, uvicorn y el router

> **↓ Capa 1 — cómo un pedido crudo termina siendo una llamada a una función Python.**
> Salteable si ya sabés qué es un servidor ASGI.

### El origen: tres intentos de resolver el mismo hueco

**Primer intento, CGI (1993).** El servidor web recibía un pedido, **lanzaba un proceso
nuevo**, le pasaba el pedido por variables de entorno y leía la respuesta por su salida
estándar. Andaba, y era un desastre: arrancar un intérprete de Python por cada pedido
costaba más que el pedido.

**Segundo intento, WSGI (PEP 333, Phillip J. Eby, 2003).** En vez de un proceso, una
**función**: el servidor importa una vez el módulo de la aplicación y por cada pedido
llama `application(environ, start_response)`. `environ` es un diccionario con el pedido
ya parseado, y la función devuelve el cuerpo. Eso desbloqueó todo el ecosistema Python
web de la década siguiente. Pero WSGI tiene una forma que ya decide una arquitectura: la
función es **síncrona y de una sola vuelta** —se la llama, devuelve, termina—. Un
WebSocket, que vive abierto media hora mandando mensajes en las dos direcciones, no entra
en esa forma. Tampoco entra una respuesta que se va emitiendo de a pedazos.

**Tercer intento, ASGI (Andrew Godwin, salido de Django Channels, ~2016).** Cambia la
firma por tres piezas:

```python
async def app(scope, receive, send): ...
```

- `scope`: un diccionario con lo que **no cambia** durante la conexión — tipo (`http`,
  `websocket`, `lifespan`), método, ruta, cabeceras, IP del cliente.
- `receive`: una función que se **espera** y devuelve el próximo evento entrante (un
  pedazo del cuerpo, un mensaje del WebSocket, el aviso de que se cortó).
- `send`: una función que se **espera** y emite un evento saliente (el bloque de
  cabeceras, después cada pedazo del cuerpo).

Dos diferencias que importan. La función es `async`, así que puede quedar suspendida entre
un `receive` y el siguiente sin ocupar un hilo. Y el cuerpo llega **por eventos**, no
entero de una: por eso el pedido no tiene que caber en memoria antes de empezar a
procesarse.

En OlimpOS eso se ve en un solo lugar, y conviene mirarlo ahora porque es el único caso
donde el cuerpo se lee a mano: `backend/routers/pagos_online.py:316` hace
`cuerpo = await request.json()`. Ese `await` es literalmente esperar a que `receive`
termine de juntar los pedazos del aviso de Mercado Pago. En los otros 165 casos nadie
escribe ese `await` porque lo escribe FastAPI, como vamos a ver.

### Quién es uvicorn

**uvicorn** (Tom Christie, 2018) es un servidor ASGI: abre el socket, escucha el puerto,
habla HTTP, y por cada pedido arma el `scope` y llama a la aplicación. En este repo se lo
arranca así (`README.md:128`, y el instalador imprime lo mismo en `instalar.ps1:383`):

```
cd backend && .venv/Scripts/python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

`main:app` se lee como "importá el módulo `main` y tomá el atributo `app`". Ese atributo
es el objeto creado en `backend/main.py:198-212` · `app = FastAPI(...)`.

> **⚠ Discrepancia entre el código y la operación, anotada y no corregida.** El docstring
> de `backend/main.py:10` dice `uvicorn main:app --reload`. `README.md:128`, `instalar.ps1:383`
> y `CLAUDE.md` dicen lo contrario: se corre **sin** `--reload`. Gana la práctica
> documentada en `CLAUDE.md`, y el docstring quedó viejo. La consecuencia operativa es
> real: sin `--reload`, tocar un archivo de rutas no cambia nada hasta reiniciar, y si el
> puerto 8000 ya está tomado el proceso nuevo muere sin ruido mientras el viejo sigue
> contestando. De ahí la costumbre de contar las rutas publicadas en `/openapi.json` para
> saber cuál de los dos contestó.

### Qué es "el router", concretamente

FastAPI es una capa sobre **Starlette** (también de Tom Christie, 2018), que es quien
implementa ASGI de verdad; FastAPI (Sebastián Ramírez, diciembre de 2018) agrega encima la
validación por anotaciones de tipo y la inyección de dependencias.

El **router** no es una metáfora: es una lista de objetos `Route` en memoria, cada uno con
un patrón de ruta compilado a expresión regular, un conjunto de métodos HTTP y una
función. Cuando llega un pedido, se recorre esa lista buscando la primera entrada cuyo
patrón case con la ruta. Si ninguna casa, 404. Si casa el patrón pero no el método, 405.

Eso de que la tabla se arma **en tiempo de ejecución** no es un detalle. En OlimpOS hay
un caso donde se lo aprovecha a propósito, en `backend/routers/pagos_online.py:397-399`:

```python
if mp.modo_simulado():
    router.post("/portal/mi-cuota/pagar/{id_pago}/simular",
                response_model=MensajeResponse)(simular_acreditacion)
```

La función `simular_acreditacion` está definida siempre
(`backend/routers/pagos_online.py:356-389`), pero **la fila del router sólo se agrega si
el modo simulado está prendido**. Con un token real de Mercado Pago cargado, esa ruta no
existe: no aparece en `/openapi.json`, no aparece en `/docs`, y un pedido a esa URL cae en
el 404 genérico del router, indistinguible de una URL inventada. La alternativa obvia
—registrar la ruta siempre y que adentro lea una bandera— deja la ruta visible en el mapa
público de la API. Los dos chequeos están puestos, igual: el de adentro
(`backend/routers/pagos_online.py:373-374`) quedó como segunda capa.

El armado de la tabla se ve entero en `backend/main.py:288-313`: primero se importan los
quince módulos de `backend/routers/`, y después cada uno se enchufa con
`app.include_router(...)`. El comentario de `backend/main.py:283-286` dice el error que
esto causa cuando falta: el endpoint está escrito, compila, y la API responde 404 como si
nunca se hubiera escrito. Es exactamente el síntoma esperable de una tabla que se llena a
mano.

Al final de todo hay una entrada que no es una función sino una aplicación ASGI entera
montada bajo un prefijo (`backend/main.py:323-324`): `app.mount(RUTA_HTTP, StaticFiles(...))`.
Un `mount` corta el prefijo de la ruta y le pasa el resto a la aplicación hija. Es el
mismo mecanismo con el que ASGI se compone consigo mismo, y va a volver en la capa 2.

---

## `lifespan`

> **↓ Capa 1b — qué corre antes de que exista el primer pedido, y por qué eso necesitó
> una parte del protocolo.** Salteable si ya sabés qué es el `lifespan` de ASGI.

**El problema de origen.** Con WSGI no había ningún lugar donde decir "esto se hace una
vez al arrancar". La costumbre era poner el trabajo al importar el módulo, como efecto
secundario. Eso rompe de tres formas: no hay contraparte para el apagado, el trabajo se
repite por cada proceso trabajador sin que nadie lo coordine, y un archivo de pruebas que
importa el módulo dispara el trabajo sin querer —incluidas las conexiones a la base—.

ASGI le puso nombre: además de `scope["type"] == "http"` y `"websocket"`, existe
`"lifespan"`. El servidor abre esa conversación **una vez**, manda `lifespan.startup`,
espera a que la aplicación conteste que terminó, y recién ahí acepta el primer pedido. Al
apagarse manda `lifespan.shutdown`.

En FastAPI eso se escribe como un generador asíncrono envuelto en `@asynccontextmanager`:
todo lo que está **antes** del `yield` es el arranque, todo lo que está **después** es el
apagado. En este repo es `backend/main.py:124-195` · `lifespan()`, y se lo engancha en la
construcción de la aplicación, en `backend/main.py:205`.

Lo que hace, en el orden en que corre:

| Línea | Qué hace | Por qué antes del primer pedido |
|---|---|---|
| `backend/main.py:142` | `Base.metadata.create_all(bind=engine)` | Red de seguridad: crea sólo las tablas que faltan y nunca modifica una existente, así que contra la base real es una operación nula. La fuente de verdad del esquema es `db/schema.sql`. |
| `backend/main.py:146` | `calentar_pool()` | Abre conexiones ahora para que el primer pedido no pague el saludo contra Neon. |
| `backend/main.py:149` | arranca el hilo del latido | Mantiene vivas esas conexiones mientras el backend esté arriba. |
| `backend/main.py:166` | `aplicar_bajas_vencidas(db)` | Las bajas programadas que ya vencieron. |
| `backend/main.py:170` | `generar_turnos(db)` | Los turnos de las próximas semanas a partir de los horarios. |

Los dos últimos son procesos que no cuelgan de ningún pedido: nadie los pide, se disparan
solos. El `lifespan` es el gancho del que cuelgan, y el comentario de
`backend/main.py:158-162` explica por qué acá y no en un temporizador del sistema
operativo: no hay dónde correr uno, y la operación es **idempotente** —correrla de nuevo
no duplica nada—, así que repetirla en cada arranque es gratis.

El apagado es una sola línea, `backend/main.py:194` · `_latido_activo.set()`, y existe por
un motivo concreto que el comentario de arriba declara: sin eso, el hilo del latido sigue
consultando la base mientras uvicorn intenta cerrar.

**Qué NO hace el `lifespan`, y conviene notarlo:** no abre la conexión a la base. El
motor (`engine`) se construye al **importar** `backend/database.py` (líneas 92-113), que
es efecto secundario de import, justo lo que el `lifespan` vino a evitar. Construir el
motor, sin embargo, no abre ninguna conexión —SQLAlchemy sólo guarda la configuración—,
así que el efecto secundario es inofensivo. Lo que sí abre conexiones es `calentar_pool()`,
y eso sí está adentro del `lifespan`. La división está bien puesta.

---

## Middleware

> **↓ Capa 2 — el pedido antes de llegar al router, y el orden real en que lo tocan.**
> Salteable si ya contaste a mano un anidamiento de middlewares de Starlette.

**El problema de origen.** Hay trabajo que no pertenece a ningún endpoint y sin embargo
tiene que pasar en todos: poner cabeceras de seguridad en cada respuesta, rechazar un
pedido que no trae su token, registrar cuánto tardó. Ponerlo adentro de cada función es
condenarse a que alguien se olvide en la próxima. El comentario de `backend/csrf.py:64-69`
dice exactamente eso: *"una dependencia hay que acordarse de ponerla en cada endpoint
nuevo, y el día que alguien se olvide, ese endpoint queda abierto sin que nada avise"*.

La forma que tomó la solución en el mundo WSGI, y que ASGI heredó igual, sale de que **una
aplicación puede envolver a otra**. Un middleware es una aplicación que recibe el pedido,
hace lo suyo, llama a la aplicación de adentro, y hace lo suyo con la respuesta que vuelve.
Se apilan como cebolla y la última capa de adentro es el router.

En OlimpOS hay tres capas propias, declaradas en este orden en el archivo:

| Orden en el código | Qué es | Dónde |
|---|---|---|
| 1º | `CORSMiddleware` | `backend/main.py:214-227` |
| 2º | `middleware_csrf` | `backend/main.py:233`, implementado en `backend/csrf.py:63-95` |
| 3º | `cabeceras_de_seguridad` | `backend/main.py:252-277` |

### El orden real, contado

Acá está el piso de este concepto, y es contraintuitivo, así que se cuenta paso por paso
con el código de Starlette a la vista (en el venv).

`add_middleware` **no agrega al final de la lista: agrega al principio**
(`starlette/applications.py:123-131`, la línea que importa es `self.user_middleware.insert(0, ...)`).
Entonces, después de las tres registraciones, la lista quedó al revés del código:

```
user_middleware = [cabeceras_de_seguridad, middleware_csrf, CORSMiddleware]
```

Y el armado de la cebolla (`starlette/applications.py:90-99`) hace dos cosas: le agrega
un manejador de errores de servidor adelante y uno de excepciones atrás, y después
**recorre la lista al revés** envolviendo:

```python
app = self.router
for cls, args, kwargs in reversed(middleware):
    app = cls(app, *args, **kwargs)
```

Desenrollando esas dos inversiones, la cebolla terminada queda, de afuera hacia adentro:

```
ServerErrorMiddleware
└── cabeceras_de_seguridad          (3º en el código)
    └── middleware_csrf             (2º en el código)
        └── CORSMiddleware          (1º en el código)
            └── ExceptionMiddleware
                └── el router
```

**Resultado, en una frase: el último middleware registrado es el que toca el pedido
primero y la respuesta último.** Los dos comentarios que el repo tiene al respecto son
correctos, y lo digo porque los verifiqué contra el código de Starlette y no contra sí
mismos: `backend/main.py:229-232` afirma que el CSRF, registrado después del CORS, se
ejecuta **antes** en el pedido entrante; y `backend/main.py:256-258` afirma que
`cabeceras_de_seguridad`, por ir último en el código, **envuelve** a los demás y por eso
también marca los rechazos del CSRF y los preflight de CORS. Las dos afirmaciones caen
exactamente de la doble inversión de arriba.

Esa segunda es la que justifica dónde está puesto. Si `cabeceras_de_seguridad` estuviera
adentro del CSRF, un pedido rechazado por token faltante —que corta en
`backend/csrf.py:87-93` devolviendo un 403 sin llamar a `call_next`— saldría **sin** las
cabeceras de seguridad, porque la capa que las pone nunca se habría ejecutado. Poniéndolo
afuera, toda respuesta que salga del backend pasa por ahí, incluidas las que ningún
endpoint llegó a producir.

Hay un efecto secundario del mismo orden que conviene decir, porque es un modo de fallar
que sólo se ve con la cebolla dibujada: `CORSMiddleware` quedó **adentro** del CSRF. Un
rechazo del CSRF sale sin cabeceras de CORS. Para la PWA eso hoy es inofensivo, porque en
desarrollo la página y la API son el mismo sitio a través del proxy de Vite y CORS no
interviene; pero un cliente que llamara a la API desde otro origen vería ese 403 como un
error de CORS en la consola en vez de leer el mensaje que el backend le mandó.

### Un cuarto interceptor que no es un middleware

`backend/main.py:236-249` registra un manejador de excepciones, no un middleware:
`@app.exception_handler(RequestValidationError)`. Vive en el `ExceptionMiddleware` del
dibujo de arriba —la capa más interna—, y no envuelve el pedido: se activa sólo cuando una
excepción de ese tipo sube desde adentro. Es lo que hace que un cuerpo mal formado
devuelva un 422 propio en vez del de fábrica, y se explica en la capa 4.

---

## Inyección de dependencias

> **↓ Capa 3 — qué se construye antes de llamar a la función, y en qué orden.**
> Salteable si ya sabés qué hace `Depends` y cómo se cachean las dependencias.

**El problema de origen.** Sin esto, una función que necesita una sesión de base y una
identidad autenticada las consigue ella misma: las construye adentro. Eso trae tres
consecuencias, todas visibles en cualquier código viejo. La función queda pegada a cómo se
construyen esas cosas, así que no se puede probar sin levantarlas. La liberación del
recurso queda a cargo de quien la escribió, así que tarde o temprano alguien no cierra algo.
Y —la peor— el chequeo de permisos queda **adentro** del cuerpo, donde es una línea más que
se puede olvidar.

Martin Fowler le puso nombre al patrón inverso en 2004, viniendo del mundo de Java: la
función **declara** lo que necesita y alguien más se lo construye y se lo pasa. Lo que
FastAPI agrega es que la declaración no es un archivo de configuración aparte: es la
**firma de la función**, leída en tiempo de ejecución a partir de las anotaciones de tipo
y de los valores por defecto.

Un endpoint de este repo, entero, para tener algo concreto delante
(`backend/routers/cobros.py:135-148` · `listar_tipos()`):

```python
@router.get("/tipos-membresia", response_model=list[TipoMembresiaOut])
def listar_tipos(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.COBROS)),
):
    tipos = db.query(TipoMembresia).order_by(TipoMembresia.precio_actual).all()
```

Ese cuerpo no abre nada, no cierra nada y no chequea nada. Cuando la primera línea corre,
`db` ya es una sesión abierta y `sesion` ya es una identidad validada con permiso de leer
Cobros. Si algo de eso no se podía cumplir, el cuerpo **no se ejecutó nunca**.

### Cómo se arma el árbol

Al arrancar, FastAPI inspecciona la firma de cada endpoint y arma un árbol: cada parámetro
cuyo valor por defecto es `Depends(f)` se convierte en un nodo, y a `f` se le hace lo
mismo, recursivamente. Para `listar_tipos` el árbol es:

```
listar_tipos
├── db      ← get_db                          (backend/database.py:154-165)
└── sesion  ← requiere_seccion("COBROS")      (backend/security.py:145-171)
            └── obtener_sesion                (backend/security.py:80-142)
                ├── token_header ← esquema_token   (backend/security.py:42)
                ├── token_cookie ← Cookie(alias=COOKIE_SESION)
                └── db           ← get_db          (backend/database.py:154-165)
```

Se resuelve de abajo hacia arriba: nada se llama antes de tener todos sus hijos resueltos.

**Ojo con la rama repetida.** `get_db` aparece dos veces: una directa y otra adentro de
`obtener_sesion`. ¿Se abren dos sesiones y dos transacciones sobre la misma base? No, y el
motivo es un detalle de implementación que cambia el significado de todo el código de
este repo: FastAPI lleva un **caché de dependencias por pedido**
(`fastapi/dependencies/utils.py:631-644`, en el venv), con clave
`(la función, los scopes de seguridad)` (`fastapi/dependencies/models.py:37`). Como `get_db`
es la misma función de módulo en los dos lugares, la clave es la misma y **se resuelve una
sola vez**: el `db` que recibe el endpoint es el mismo objeto que usó `obtener_sesion` para
releer el `Usuario`.

De ahí sale algo que hay que tener presente al leer cualquier endpoint de OlimpOS: hay
**una sesión de ORM y una transacción por pedido**, no una por dependencia.

La misma regla explica un caso que parece igual y no lo es. `requiere_seccion(...)` es una
**fábrica**: cada llamada devuelve una función nueva (`backend/security.py:162`, la
`dependencia` de adentro). Dos endpoints que pidan `requiere_seccion(Seccion.COBROS)` no
comparten nada, porque son dos objetos función distintos; lo que sí comparten, dentro de un
mismo pedido, es `obtener_sesion`, que sí es una función de módulo. El resultado práctico
es el correcto: la validación de la sesión —que incluye una consulta a la base, en
`backend/security.py:121`— ocurre **una vez por pedido**, aunque el endpoint pida dos
barreras distintas.

### Por qué la dependencia es un generador

`get_db` (`backend/database.py:154-165`) no devuelve: **entrega**.

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

Todo lo que está antes del `yield` corre antes del endpoint; lo que está en el `finally`
corre después, **pase lo que pase** —incluida una excepción a mitad del cuerpo—. FastAPI lo
implementa envolviendo el generador en un gestor de contexto y registrándolo en una pila de
salida del pedido (`fastapi/dependencies/utils.py:553-560`, en el venv). Esa pila se
desarma al final en orden inverso, así que la sesión se cierra siempre y el endpoint no
tiene que acordarse.

### Las dos barreras, y por qué son dependencias y no líneas del cuerpo

`backend/security.py` declara tres niveles, y el docstring del archivo (líneas 14-17) dice
la frase que justifica todo el diseño: *"Se declaran como parámetros del endpoint y FastAPI
las resuelve ANTES de ejecutar su cuerpo. Eso significa que un endpoint mal escrito no
puede 'olvidarse' de chequear permisos a mitad de camino"*.

- **`obtener_sesion`** (`backend/security.py:80-142`) responde "¿hay una sesión válida?" y
  corta con 401. Acepta dos transportes —una cabecera `Authorization` o una cookie— y el
  criterio de desempate está en la línea 108: `token = token_header or token_cookie`, la
  cabecera gana. Los dos mecanismos de sesión, y por qué son dos, se explican en
  [sesiones y autenticación](A0-12-sesiones-y-autenticacion.md); acá sólo importa que es
  **una** dependencia y que el resto del sistema recibe su resultado ya resuelto: el objeto
  `Sesion` de `backend/security.py:45-71`.
- **`requiere_seccion(seccion, minimo)`** (`backend/security.py:145-171`) es una fábrica que
  devuelve una dependencia que depende de la anterior y corta con 403 si el nivel no
  alcanza. El valor por defecto de `minimo` es `Acceso.LECTURA`, y el comentario de las
  líneas 158-160 dice el porqué con una precisión que vale copiar: *"que el pedido más
  permisivo sea el default hace que olvidarse escriba de menos, no de más"*.
- **`requiere_accion(accion)`** (`backend/security.py:197-215`) hace lo mismo con una acción
  puntual en vez de una sección.

Las tres funciones que consultan la tabla son `acceso_a_seccion`
(`backend/permisos.py:340-350`), `alcanza` (`backend/permisos.py:353-355`) y
`puede_accion` (`backend/permisos.py:358-361`). Son diccionarios en memoria: ni una
consulta a la base. **Qué dice esa tabla, por qué tiene niveles además de acciones y por
qué vive copiada en tres lenguajes, es el tema de [autorización](A-08-autorizacion.md)**;
acá termina lo que corresponde a este capítulo, que es el mecanismo por el que la barrera
llega a aplicarse antes que el cuerpo.

El uso está medido: sobre los 165 decoradores de ruta de `backend/routers/`, hay **164**
apariciones de `Depends(get_db)` y **155** de `Depends(requiere_...)`. La diferencia no es
descuido: son las rutas sin sesión —el login, el webhook de Mercado Pago— y las que piden
`obtener_sesion` pelado, como `/me` (`backend/routers/auth_router.py:265-266`).

---

## Esquema de entrada y salida, y el 422

> **↓ Capa 4 — qué pasa con el cuerpo del pedido entre que llega como texto y que el
> endpoint lo toca.** Salteable si ya usaste Pydantic v2.

**El problema de origen.** El cuerpo de un pedido llega como [JSON](A0-03-http.md#json-como-cuerpo):
texto. Parsearlo da diccionarios, listas, números y cadenas, y nada más. Los tipos que el
programador escribió del lado del cliente **ya no existen** cuando el pedido cruza el
cable —eso es el [borrado de tipos](A0-05-javascript-y-typescript.md#tipado-estático-y-borrado-de-tipos)—,
así que del lado del servidor no hay más remedio que volver a preguntar qué es cada cosa.
La alternativa, escribir esas preguntas a mano en cada endpoint (`if "monto" not in cuerpo:
...`), produce cientos de líneas que nadie mantiene y mensajes de error distintos en cada
pantalla.

**Pydantic** (Samuel Colvin, 2017) hace eso con la misma jugada que la inyección de
dependencias: usa las anotaciones de tipo **en tiempo de ejecución**. Una clase que hereda
de `BaseModel` declara los campos con su tipo y sus restricciones, y validar es construirla.

El ejemplo de este repo, `backend/schemas.py:730-767` · `CobrarRequest`:

```python
class CobrarRequest(BaseModel):
    id_socio: int
    id_tipo_membresia: int
    metodo: MetodoPago
    monto_manual: float | None = Field(default=None, ge=1, allow_inf_nan=False)
    numero_comprobante: str | None = None
    saldar_deudas: bool = True
    id_plan_actividad: int | None = None
    id_promocion: int | None = None
```

Y el endpoint que lo consume, `backend/routers/cobros.py:236-241` · `cobrar()`, lo declara
como un parámetro más, sin `Depends`: FastAPI sabe que un parámetro cuyo tipo es un
`BaseModel` sale del cuerpo del pedido, y que uno cuyo tipo es un escalar sale de la ruta
o de la cadena de consulta.

Lo interesante de esta clase es lo que **no** declara: no hay campo `monto`. El docstring
de las líneas 729-736 dice por qué: si el monto viniera del cliente, cualquiera con la
consola del navegador abierta podría cobrar $1 una membresía de $30.000, y en la base
quedaría un pago perfectamente válido. El esquema de entrada no es sólo una validación:
es la **declaración de qué se le acepta al cliente**, y todo lo que no está declarado se
descarta antes de que ningún código lo mire.

El `Field(ge=1, allow_inf_nan=False)` de la línea 743 es memoria de dos fallas concretas,
anotadas en el comentario de arriba: con `gt=0` pasaban `0.0001` —que redondeado quedaba un
cobro de $0,00 con la membresía activada— y pasaban `Infinity` y `NaN`, que el parser de
JSON acepta y Postgres rechaza al escribir, convirtiendo lo que debía ser un 422 en un 500.

### El 422, hasta el cuerpo de la respuesta

**422 Unprocessable Entity** no es un invento de FastAPI: viene de WebDAV (RFC 4918,
§11.2), y su definición es exactamente la que hace falta acá —el pedido está **bien
formado sintácticamente** pero es **semánticamente incorrecto**—. Un JSON roto da 400; un
JSON impecable con `monto_manual: 0.5` da 422.

Cuando la construcción del modelo falla, Pydantic junta **todos** los errores (no corta en
el primero) y FastAPI los envuelve en una `RequestValidationError`. Esa excepción sube por
las dependencias hasta el manejador registrado en `backend/main.py:236-249`, que es lo que
determina el cuerpo exacto que se devuelve:

```python
errores = [{"loc": list(e.get("loc", ())), "msg": e.get("msg", ""), "type": e.get("type", "")}
           for e in exc.errors()]
return JSONResponse(status_code=422, content={"detail": errores})
```

Tres campos por error y **nada más**: dónde falló, qué falló y de qué tipo es la falla.
El manejador de fábrica de FastAPI agrega un cuarto, `input`, con el valor que el cliente
mandó. Sacarlo resuelve dos cosas a la vez, según el comentario de las líneas 241-245: ese
valor puede ser `Infinity` o `NaN`, que no se pueden serializar de vuelta a JSON —y ahí el
422 correcto terminaba siendo un 500—, y además evita devolverle al cliente lo que mandó,
que en el caso de una contraseña rechazada por no cumplir la regla significa devolver la
contraseña en la respuesta.

Del otro lado de la función está `response_model`, el esquema de **salida**
(`backend/routers/cobros.py:135`: `response_model=list[TipoMembresiaOut]`). Filtra: lo que
el endpoint devuelva y no esté declarado en el modelo de salida **no sale**. Es la misma
idea que la de entrada, en el otro sentido: un objeto del ORM que arrastra relaciones no
puede filtrar un campo por descuido si el modelo de salida no lo nombra.

---

## Corrutina

> **↓ Capa 5 — qué significa que una función pueda quedarse a mitad de camino.**
> Salteable si ya sabés qué hace `await` en Python.

**El origen, en cuatro pasos de la propia historia de Python.** El nombre *corrutina* es
de Melvin Conway, 1963, y describe una subrutina que puede suspenderse y reanudarse en vez
de correr de una sola vez. Python llegó ahí de a poco: los generadores (PEP 255, 2001)
introdujeron el `yield`, que ya suspende una función y guarda su estado; el PEP 342 (2005)
convirtió `yield` en una expresión que además recibe valores, que es lo que las volvió
corrutinas de verdad; `asyncio` llegó en el PEP 3156 (2012); y la sintaxis `async def` /
`await` que usa este repo es el PEP 492 (Yury Selivanov, 2015), que separó los dos
conceptos para que una corrutina dejara de ser "un generador que además hace otra cosa".

**Qué es, mecánicamente.** Una función declarada `async def` no ejecuta nada cuando se la
llama: devuelve un objeto corrutina, que es su cuerpo empaquetado junto con un lugar donde
guardar en qué línea va. Cada `await` es un **punto de suspensión marcado en el código**:
ahí la función puede devolverle el control a quien la esté manejando, y volver más tarde a
esa misma línea con todas sus variables locales intactas.

Quién la maneja es el **bucle de eventos**, que este capítulo no define: es el mismo
mecanismo de cola y tareas que ya se explicó en
[el navegador por dentro](A0-04-el-navegador-por-dentro.md#bucle-de-eventos-tarea-y-microtarea-promesa-y-asyncawait).
Lo específico de Python acá es una sola cosa, y es la que interesa: **el bucle vive en un
hilo, y ese hilo es uno solo**. Mientras una corrutina está corriendo, ninguna otra corre.
El reparto no es preventivo: una corrutina cede el control **sólo** cuando llega a un
`await` que efectivamente tiene que esperar.

### El hilo de trabajo para las funciones síncronas

Acá aparece la pieza que hace que todo OlimpOS funcione, y que es invisible desde el código
del repo.

Un endpoint `def` —sin `async`— no es una corrutina: no tiene puntos de suspensión y no se
le puede pedir que ceda el control. Si el bucle lo llamara directamente, se quedaría parado
adentro de esa función hasta que terminara, y durante todo ese rato no atendería ningún
otro pedido.

FastAPI resuelve eso mirando la función al arrancar y decidiendo dónde la corre
(`fastapi/routing.py:233`, en el venv):

```python
is_coroutine = asyncio.iscoroutinefunction(dependant.call)
```

y después (`fastapi/routing.py:204-214`):

```python
if is_coroutine:
    return await dependant.call(**values)
else:
    return await run_in_threadpool(dependant.call, **values)
```

`run_in_threadpool` (`starlette/concurrency.py:35-37`) delega en `anyio.to_thread.run_sync`,
que agarra un **hilo de trabajo** de un conjunto reusable y corre ahí la función síncrona,
mientras el bucle de eventos queda libre esperando a que ese hilo avise que terminó. Los
hilos se crean a demanda y se reusan (`anyio/_backends/_asyncio.py:2596-2610`), y la
cantidad simultánea está topeada por un limitador cuyo valor por defecto es **40**
(`anyio/_backends/_asyncio.py:3093-3097`: `limiter = CapacityLimiter(40)`).

Lo mismo vale para las dependencias: una dependencia síncrona normal se manda al mismo
conjunto de hilos (`fastapi/dependencies/utils.py:640`), y una dependencia generadora como
`get_db` se envuelve con `contextmanager_in_threadpool` (`fastapi/dependencies/utils.py:557`).

**En qué queda OlimpOS.** En todo `backend/routers/` hay exactamente **un** `async def` a
nivel de módulo: el webhook de Mercado Pago, en `backend/routers/pagos_online.py:294`. Las
otras **166** operaciones —incluidas `@app.get("/")` de `backend/main.py:327` y la
condicional de `backend/routers/pagos_online.py:356`— son funciones síncronas comunes, y
por lo tanto corren en un hilo de trabajo.

Ese número no es un descuido: es la consecuencia directa de que SQLAlchemy se use en su
modo síncrono (`backend/database.py:117` · `SessionLocal = sessionmaker(...)`). Un
`db.query(...)` bloquea el hilo donde corre hasta que la base conteste. Escribir el
endpoint `async def` y llamar adentro un `db.query()` sería lo peor de los dos mundos: la
función correría en el bucle de eventos y lo dejaría parado los 44 ms de cada consulta.
Dejándolo `def`, FastAPI lo manda a un hilo de trabajo y el bucle sigue atendiendo.

---

## GIL y concurrencia ≠ paralelismo

> **↓ Capa 6 — el candado que hay adentro del intérprete, y qué lo suelta.** Es el piso
> de este capítulo.

**El origen.** CPython administra la memoria contando referencias: cada objeto lleva un
entero con cuántos nombres lo apuntan, y cuando llega a cero se libera. Ese contador se
incrementa y decrementa constantemente, en operaciones que **no son atómicas**. Con dos
hilos tocando el mismo objeto a la vez, dos decrementos simultáneos pueden perderse uno, y
el objeto se libera mientras alguien lo sigue usando —o no se libera nunca—.

Cuando en 1992 se le agregaron hilos a Python, la solución más barata fue un **candado
global**: un solo candado para todo el intérprete, que un hilo tiene que sostener para
ejecutar bytecode. Eso vuelve seguras todas las estructuras internas de una sola vez, sin
tener que poner un candado por objeto. El costo es el que se conoce: **dos hilos de Python
nunca ejecutan bytecode al mismo tiempo**, por más núcleos que tenga la máquina.

El candado se suelta en dos situaciones:

1. **Cada cierto tiempo, por las dudas.** El intérprete le pide al hilo que sostiene el
   candado que lo libere cada tanto para que otro avance. Ese intervalo es el que devuelve
   `sys.getswitchinterval()`, y su valor por defecto en CPython es de 5 ms desde Python 3.2.
   (Dato del intérprete, no de este repo.)
2. **Voluntariamente, alrededor de toda espera de entrada/salida.** Esto es lo que
   importa. Cuando el código llega a una llamada al sistema operativo que va a esperar
   —leer de un socket, escribir en disco—, la extensión en C que la hace **suelta el
   candado antes de esperar y lo vuelve a tomar al volver**. Durante esa espera, otro hilo
   de Python corre.

**La distinción que da nombre a la sección.** *Concurrencia* es atender muchas cosas
intercaladas, avanzando un poco de cada una. *Paralelismo* es hacer dos cosas
literalmente al mismo tiempo, en dos núcleos. Un proceso Python con el GIL puesto tiene
concurrencia hasta donde quiera, y **no tiene paralelismo de cálculo**. Esto no es un
detalle de implementación que va a desaparecer: el PEP 703 (2023) propone poder compilar
CPython sin GIL, es opcional desde 3.13, y el ecosistema recién está adaptándose —se ve,
por ejemplo, en que SQLAlchemy ya consulta si el intérprete lo tiene apagado, en
`sqlalchemy/util/compat.py:46` del venv—. El backend de OlimpOS corre sobre 3.11.9, con el
candado siempre puesto.

### Qué implica en este repo, concretamente

**Primero: los hilos existen y comparten memoria, así que hay que sincronizar a mano.**
El GIL vuelve seguras las estructuras **internas** del intérprete, no las tuyas. Un
`lista.append(x)` no se corrompe, pero una secuencia de *leer, decidir, escribir* sí se
puede intercalar. Por eso `backend/limite_intentos.py:41` declara
`_candado = threading.Lock()` y todas las funciones del módulo trabajan adentro de
`with _candado:` —por ejemplo `ip_excedida()` en las líneas 46-55, que lee la lista de
fallos, la filtra, la reescribe y la compara—. Esos diccionarios viven en memoria del
proceso y los tocan los 40 hilos de trabajo; sin el candado, dos intentos de login
simultáneos pueden dejar el contador mal.

**Segundo: cuando hace falta trabajo de fondo, se usa un hilo, y está justificado.**
`backend/main.py:149` arranca `threading.Thread(target=_latido, name="latido-neon", daemon=True)`.
El comentario de las líneas 78-81 da el motivo en una frase que es exactamente este
capítulo: *"SQLAlchemy acá es SÍNCRONO. Meterlo en el event loop bloquearía el loop entero
durante el RTT (~44 ms) cada dos minutos"*. Que el hilo sea **demonio** significa que no
impide que el proceso termine, así que no hay que cancelarlo para poder apagar —aunque
igual se lo corta explícitamente en `backend/main.py:194`, para que no siga consultando
mientras uvicorn cierra—.

**Tercero: cuando hace falta paralelismo de verdad, se saca del proceso.** El demonio de
videos no es un hilo ni una tarea del backend: es **otro programa**, que se lanza aparte
(`backend/demonio_videos.py:7-8` documenta su propia línea de comandos) y que ni siquiera
corre en la misma máquina —el docstring dice que corre en el servidor FTP—. Bajar y
recodificar video con ffmpeg es trabajo de CPU sostenido; adentro del backend tomaría el
candado y dejaría a todos los pedidos esperando. Afuera, es otro proceso con su propio
GIL, y el sistema operativo lo reparte en otro núcleo. Se comunica con el resto por la base
y por el sistema de archivos, no por memoria compartida.

---

## El piso: por qué esperar la red no bloquea y calcular sí

Acá se junta todo, y se puede decir con números del propio repo.

**Los dos costos de la base**, medidos y anotados en `backend/database.py:52-53`:

```
SELECT 1 en una conexión YA abierta ......  44 ms   <- piso físico (RTT)
Abrir una conexión NUEVA (TLS + auth) .... 825 ms   <- 19x más caro
```

**El costo de la única operación de CPU que está en el camino de un pedido.** El login
verifica la contraseña con bcrypt (`backend/auth.py:60-74` · `verificar_password()`), y las
contraseñas se guardan con `bcrypt.gensalt()` (`backend/auth.py:57`), cuyo factor de costo
por defecto es **12 rondas** (`bcrypt/__init__.pyi:1`, en el venv). Bcrypt está diseñado
para ser lento a propósito —el porqué es tema de
[criptografía aplicada](A0-11-criptografia-aplicada.md#sal-y-hash-lento)—, y un factor 12
son 2¹² = 4096 iteraciones del armado de clave: **decenas a centenas de milisegundos** de
cómputo puro, sin ninguna espera. (Ese orden de magnitud es el propio del algoritmo con ese
factor; **no está medido en esta máquina**, a diferencia de los 44 y los 825 ms, que sí lo
están y están anotados en el código.) El login de `backend/routers/auth_router.py:108-167` lo
paga **siempre**, incluso cuando la cuenta no existe: la línea 161 verifica contra un hash
de relleno construido al importar el módulo (`backend/routers/auth_router.py:66`) para que
un usuario inexistente tarde lo mismo que uno real.

**Ahora la diferencia, escrita como pasa adentro del proceso.**

*Un endpoint esperando la base.* `listar_tipos` corre en un hilo de trabajo. Llega a
`db.query(...)`, que termina en una llamada al sistema operativo para leer del socket
contra São Paulo. La extensión en C **suelta el GIL** antes de esperar. Durante esos 44 ms,
ese hilo no tiene el candado, el bucle de eventos puede atender pedidos nuevos y los otros
hilos de trabajo pueden correr su propio bytecode. El pedido tarda 44 ms, y el proceso no
perdió ni un milisegundo de capacidad. **Diez pedidos así a la vez terminan en el orden de
los 44 ms, no de los 440** —siempre que haya diez conexiones libres en el pool, que es la
otra mitad de esta historia y viene abajo—.

*Un endpoint calculando.* `verificar_password` corre en un hilo de trabajo y entra en las
4096 iteraciones de bcrypt. Eso es bytecode y código nativo **con el candado tomado**,
liberándolo sólo cada 5 ms para que otro hilo avance un poco. No hay ninguna espera de la
que el intérprete se pueda aprovechar: el trabajo tiene que hacerse. **Diez logins
simultáneos se serializan.**

Esa es la frase completa del piso: *esperar* la red devuelve el candado, *calcular* lo
retiene. Y de ahí sale la conclusión que ordena la arquitectura de este backend: mientras
casi todo lo que hace un pedido sea esperar a Neon, un solo proceso Python alcanza y
sobra. El día que apareciera trabajo de CPU sostenido en el camino de un pedido —procesar
video, correr un modelo—, esto dejaría de alcanzar, y por eso ese trabajo está afuera: el
demonio de videos es otro proceso, y el contador de repeticiones corre en el celular del
socio.

### Dos hallazgos que sólo se ven con el piso puesto

**Uno: el único `async def` del repo hace una llamada bloqueante.** El webhook de
`backend/routers/pagos_online.py:294` corre **en el bucle de eventos**, no en un hilo de
trabajo, porque está declarado `async def`. Adentro, la línea 335 llama
`mp.consultar_pago(id_pago_mp)`, que es una función síncrona común y que termina en
`backend/mercadopago.py:181` haciendo
`urllib.request.urlopen(pedido, timeout=TIMEOUT)` con `TIMEOUT = 15`
(`backend/mercadopago.py:79`). Eso es una llamada de red bloqueante ejecutada en el hilo
del bucle. Mientras dure —y puede durar hasta 15 segundos si Mercado Pago no responde—,
**el proceso entero no acepta ningún otro pedido**. Lo mismo vale, en menor escala, para
`_acreditar(db, ...)` de la línea 345, que hace trabajo de base sobre el mismo hilo. El
arreglo canónico es una línea: sacarle el `async` a la firma, y entonces FastAPI lo manda a
un hilo de trabajo como a las otras 166. Lo único que obliga al `async` hoy es el
`await request.json()` de la línea 316 —leer el cuerpo a mano es asíncrono porque el cuerpo
llega por eventos—, y ese cuerpo se puede recibir igual como parámetro declarado, que es lo
que hacen todos los demás endpoints del repo.

*Hoy esto no se manifiesta*, porque el webhook todavía no está en uso: falta la URL pública
y el sistema corre en modo simulado. Queda anotado como lo que es: un modo de fallar que el
código tiene escrito y que va a aparecer el día que el webhook reciba tráfico.

**Dos: el techo real de concurrencia no son 40, son 15.** Hay 40 hilos de trabajo
disponibles, pero el pool de conexiones está configurado con `pool_size=10` y
`max_overflow=5` (`backend/database.py:96-97`): **como máximo 15 conexiones simultáneas
contra Neon**. Como prácticamente todo endpoint pide `Depends(get_db)`, el hilo 16 se queda
esperando una conexión libre, y si no aparece en `pool_timeout=10` segundos
(`backend/database.py:101`) el pedido falla. Los 25 hilos restantes son capacidad que no se
puede usar. Para un gimnasio con un mostrador eso está muy holgado, pero es el número que
hay que mirar el día que algo se ponga lento con carga, y no el 40.

Ese mismo cruce —hilos topeados afuera, conexiones topeadas adentro— tiene un riesgo de
bloqueo mutuo que FastAPI ya previó, y vale verlo porque es el cierre del descenso.
`fastapi/concurrency.py:15-39` (venv) corre el `__exit__` del gestor de contexto —o sea, el
`finally: db.close()` de `backend/database.py:164-165`, que es lo que **devuelve** la
conexión al pool— con un limitador propio de capacidad 1, y no con el limitador compartido
de 40. El comentario de las líneas 19-24 dice el motivo: si cerrar tuviera que esperar un
hilo libre del mismo conjunto, y los 40 hilos estuvieran ocupados esperando una conexión
del pool, nadie liberaría nunca nada. Es exactamente la combinación que tiene este repo, y
está resuelta aguas arriba.

---

## Por qué está hecho así

Ingeniería inversa de la decisión central de este capítulo: **un solo proceso, endpoints
síncronos, ORM síncrono, y el trabajo pesado afuera.**

**Qué se estaba optimizando.** Costo de mantenimiento y claridad de lectura, no
rendimiento. Un endpoint de OlimpOS se lee de arriba a abajo como un procedimiento: buscar
el socio, chequear la regla, escribir, devolver. Nadie tiene que razonar sobre en qué punto
la función cede el control.

**Qué restricciones acorralaban.** La base está a 44 ms y el cuello de todo pedido es ese
viaje, no el cálculo. La carga real es un mostrador, no miles de usuarios simultáneos. Y el
sistema tiene que poder instalarse en el servidor local de un gimnasio, con un comando, sin
un administrador que configure procesos trabajadores ni un balanceador.

**Qué alternativas había, dichas en serio.**

- *SQLAlchemy asíncrono y todos los endpoints `async def`.* Sacaría el conjunto de 40 hilos
  del medio y dejaría todo en el bucle. Se paga con un driver distinto, con que toda
  función que toque la base se vuelva contagiosamente `async`, y con que cualquier llamada
  bloqueante que se cuele —una de `urllib`, sin ir más lejos, como la que ya está en el
  webhook— frene el proceso entero en vez de un solo hilo. Con el cuello en la red y una
  sola sede, no compra nada.
- *Varios procesos trabajadores (`--workers 4`).* Daría paralelismo de CPU real, sorteando
  el GIL por la vía de tener cuatro. Se paga con que `backend/limite_intentos.py` deja de
  funcionar —su estado vive en memoria del proceso y cada trabajador tendría el suyo, así
  que el freno de intentos contaría un quinto de los fallos—, con cuatro pools de
  conexiones contra Neon en vez de uno, y con cuatro hilos de latido. El propio módulo
  anota la salida para ese día, en `backend/limite_intentos.py:25-26`: mover el estado a un
  almacén compartido.
- *Poner el chequeo de permisos adentro del cuerpo de cada endpoint.* Es lo más simple de
  escribir y lo que hace la mayoría de los proyectos chicos. Se paga con que la barrera sea
  una línea que se puede olvidar, y con 155 oportunidades de olvidarla.

**Qué se eligió y qué se pagó.** Se eligió lo síncrono, un proceso, y las barreras en la
firma. El precio está contado arriba y es doble: el techo de 15 consultas simultáneas, y el
hecho de que la única operación de CPU del camino —bcrypt en el login— se serializa. Los
dos precios son irrelevantes para un gimnasio y dejarían de serlo para un sistema con
varias sedes: ese es el escenario en el que esta sección se vuelve a leer, y las dos
alternativas de arriba dejan de ser hipotéticas.

**Los nombres de los patrones**, para reconocer la jugada en otro sistema: *inversión de
control* (la función declara y el marco construye), *fallar cerrado* (la barrera corre
antes que el cuerpo, así que un endpoint incompleto no queda abierto sino roto),
*idempotencia* (el arranque puede repetir `generar_turnos` sin duplicar nada), y
*presupuesto de recursos* (40 hilos, 15 conexiones, 10 segundos de espera: cada tope está
elegido y escrito, no dejado en el valor de fábrica).

---

## Con qué se conecta

- **Existe por culpa de…** el borrado de tipos: el tipo del cliente ya no existe cuando el
  pedido llega, y por eso la validación real y el 422 viven acá ([A0-05](A0-05-javascript-y-typescript.md#tipado-estático-y-borrado-de-tipos)).
- **Existe por culpa de…** el puerto: si el 8000 está tomado, el proceso nuevo muere en
  silencio y contesta el viejo, y por eso se cuentan las rutas publicadas ([A0-02](A0-02-como-se-comunican-dos-maquinas.md#puerto)).
- **Es la misma idea que…** el bucle de eventos del navegador: un hilo y una cola, la misma
  arquitectura a los dos lados del cable ([A0-04](A0-04-el-navegador-por-dentro.md#bucle-de-eventos-tarea-y-microtarea-promesa-y-asyncawait)).
- **Es el mismo problema que…** la sesión del ORM y su transacción: `get_db` es quien fija
  dónde empiezan y dónde terminan, una sola vez por pedido ([A0-09](A0-09-el-orm.md#sesión-y-mapa-de-identidad), [A0-07](A0-07-bases-de-datos-relacionales.md#transacción-acid-commit-y-rollback)).
- **Existe por culpa de…** el GIL: procesar video en el servidor sería justamente el
  trabajo de CPU que este proceso no puede pagar, y por eso la inferencia corre en el
  celular ([A0-14](A0-14-vision-en-el-dispositivo.md#inferencia-en-el-dispositivo)).
- **Se contradice con…** el propio presupuesto: 40 hilos de trabajo contra 15 conexiones de
  base; gana el número chico, y el pool se desarrolla en [A-11](A-11-rendimiento.md#pool-de-conexiones).
