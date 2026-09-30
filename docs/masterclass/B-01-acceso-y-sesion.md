# B-01 · Acceso y sesión

*Procesos 1 a 5. Piso del capítulo: la línea que implementa cada paso, en las tres capas.*

Los cinco procesos de esta sección son la puerta del sistema: comprobar que la API está viva,
cambiar una contraseña, iniciar sesión, cerrarla y recuperarla después de un F5. Ninguno de ellos
decide nada del gimnasio, pero sin ellos no se llega a ninguna otra pantalla.

Casi todo el porqué ya está explicado: el diseño de la autenticación en
[A-07](A-07-autenticacion.md), los mecanismos de la web —cookie, token, CSRF— en
[A0-12](A0-12-sesiones-y-autenticacion.md), y el camino completo de un pedido en
[A-04](A-04-recorrido-de-un-pedido.md). Este capítulo no lo repite: sigue el código de cada proceso
en el orden en que corre, con archivo y línea en cada paso, y enlaza la explicación donde vive.
Lo que agrega es lo que sólo se ve mirando proceso por proceso: qué tablas toca de verdad cada uno
contra lo que declara `PROCESOS-LOGICOS-REQUERIDOS.md`, y qué pasa en cada rechazo.

Una aclaración que vale para los cinco: la línea DFD pone como entidad a los seis roles, pero
**ninguna de estas rutas exige una sesión para entrar** —salvo `/me`, que existe justamente para
validarla—. La notación sólo admite roles como entidad
([las seis convenciones](A-12-como-leer-los-procesos.md#las-seis-convenciones)), y quien llega a
estas rutas todavía no es nadie para el sistema.

---

## Los cinco procesos

### 1. Chequear que la API responde

`GET /` · sin sesión

**Qué resuelve.** Saber si hay un backend escuchando, sin credenciales de por medio.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | — (no existe en la PWA) | | |
| Service PWA | — (no existe en la PWA) | | |
| Esquemas | — (devuelve un diccionario literal) | | |
| Endpoint | `backend/main.py` | 327-330 | `estado()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 411-413 | `estado_api()` |
| Quién lo llama | `Flet/Proyecto/pruebas_vistas.py` | 120-125 | `main()` |

Ninguna pantalla lo usa, y está bien: es una herramienta de verificación, no una función del
producto. Su único cliente es la prueba que construye las vistas de Flet con cada rol.

**Cómo funciona.** `estado()` devuelve `{"status": "ok", "app": "OlimpOS API"}` con un 200 y nada
más. No declara dependencias, así que no pide sesión ni abre una conexión a la base; su docstring
lo dice en una línea: *"No toca la base"* (`main.py:329`). Se registra con `@app.get` sobre la
aplicación y no con el decorador de un router, así que no la ve un conteo de las rutas de
`backend/routers/`: es una de las dos por las que ese conteo da 165 y no 167
([la aritmética del archivo](A-12-como-leer-los-procesos.md#la-aritmética-173-167-165-y-130)).

`pruebas_vistas.py` la llama antes de construir nada (`:120`). Si no hay respuesta, imprime cómo
levantar el backend y termina con código 1 (`:121-125`).

**Qué escribe y qué lee.** La línea DFD declara `<- ()`: no lee nada. El código coincide: no hay una
sola consulta.

**Por qué está hecho así.** Responde "alguien atiende en el puerto", y nada más. No toca la base, así
que con Neon dormida contesta "ok" igual; y no dice qué versión del código atiende, así que el
proceso viejo que quedó escuchando en el 8000 también contesta "ok". Para lo segundo el repo usa
otra cosa: cuenta las rutas de `/openapi.json`, que cambian con el código
([verificar la identidad de quien responde](A0-02-como-se-comunican-dos-maquinas.md#por-qué-el-puerto-8000-ocupado-hace-que-el-proceso-nuevo-muera-en-silencio)).
Es la diferencia que la industria llama *chequeo de vida* contra *chequeo de disponibilidad*:
este endpoint es del primer tipo.

Un detalle del cliente: `estado_api()` pasa por `_get()` (`api_client.py:270`), que guarda la
respuesta en el caché de [servir y refrescar](A-11-rendimiento.md#servir-y-refrescar). Un chequeo de
salud cacheado podría decir "ok" de un backend que ya se cayó. No pasa porque se llama una sola vez,
al arrancar un proceso nuevo, con el caché vacío.

**Qué pasa cuando sale mal.** El endpoint no tiene rechazos propios. Si el backend no está, no hay
respuesta: el cliente de Flet devuelve `ok` en falso con el error de conexión, y
`pruebas_vistas.py` imprime *"No hay backend: …"* (`:122`).

---

### 2. Cambiar la contraseña

`POST /cambiar-password` · sin sesión

**Qué resuelve.** Que una cuenta con contraseña temporal —recién creada, o reseteada— defina la
suya. Hasta que lo hace no puede iniciar sesión.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/CambiarPasswordView.tsx` | 29-144 | `CambiarPasswordView` |
| Store PWA | `Proyecto - PWA/src/frontend/src/store/authStore.ts` | 137-150 | `cambiarPassword` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/authService.ts` | 144-158 | `cambiarPassword()` |
| Esquemas | `backend/schemas.py` | 103-142 | `_PASSWORDS_COMUNES`, `CambiarPasswordRequest` |
| Validación (422) | `backend/main.py` | 236-249 | `errores_de_validacion()` |
| Endpoint | `backend/routers/auth_router.py` | 295-341 | `cambiar_password()` |
| Freno de intentos | `backend/routers/auth_router.py` | 63-105 | `_HASH_DE_RELLENO`, `_ip()`, `_frenar_si_excede()`, `_registrar_intento_fallido()`, `_cuenta_no_disponible()` |
| Freno de intentos | `backend/limite_intentos.py` | 46-77 | `ip_excedida()`, `registrar_fallo_ip()`, `trabar_cuenta()`, `cuenta_trabada()` |
| Hash | `backend/auth.py` | 55-74 | `hashear_password()`, `verificar_password()` |
| Vista Flet | `Flet/Proyecto/app/views/login.py` | 165-260 | `show_cambiar_password()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 161-181 | `cambiar_password()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 397-408 | `cambiar_password()` |

**Cómo funciona.**

1. **La pantalla sabe de quién es la cuenta sin preguntarlo.** Al contestar el login que la clave
   es temporal, el store guarda el nombre de usuario (`authStore.ts:115-117`) y la vista lo toma de
   ahí (`CambiarPasswordView.tsx:37`). Quien entra a la ruta sin haber pasado por el login no tiene
   ese nombre, y la vista lo devuelve al login en vez de mostrar un formulario que va a fallar
   (`:43-45`). Flet guarda lo mismo en `state.username_pendiente_cambio` (`state.py:110`).
2. **Dos controles locales**, que coincidan las dos nuevas y que tengan al menos 8 caracteres
   (`CambiarPasswordView.tsx:53-63`; en Flet, `login.py:183-195`, que además exige los tres
   campos). Son comodidad, no seguridad: ahorran un viaje, y el backend los vuelve a hacer
   ([el frontend esconde, el backend rechaza](A-08-autorizacion.md#el-frontend-esconde-el-backend-rechaza)).
3. **El pedido** sale por el cliente de cada app (`authService.ts:149-156`,
   `api_client.py:404-408`). Como no hay cookie de sesión, el middleware de CSRF lo deja pasar sin
   pedir token (`backend/csrf.py:74-79`).
4. **El esquema rechaza antes que el endpoint.** `password_nueva` exige 8 caracteres
   (`schemas.py:120`), y `_password_razonable()` (`:122-142`) pide letras y números, que no sea de
   las más usadas y que no pase de 72 bytes, el límite de bcrypt
   ([sal y hash lento](A0-11-criptografia-aplicada.md#sal-y-hash-lento)). Cualquier falla sale como
   422 antes de ejecutar una línea del endpoint
   ([esquema de entrada y el 422](A0-10-python-del-lado-del-servidor.md#esquema-de-entrada-y-salida-y-el-422)),
   y `errores_de_validacion()` le saca a la respuesta el valor recibido (`main.py:239-245`): el
   servidor no le devuelve a nadie la contraseña que rechazó.
5. **El endpoint** (`auth_router.py:310-337`) aplica las mismas defensas que el login, con las
   mismas funciones ([el mismo contador](A-07-autenticacion.md#el-mismo-contador-en-el-cambio-de-clave)):
   - toma la IP del socket y corta con 429 si ya gastó su cupo (`:311-312`);
   - busca la cuenta (`:313`); si no existe, está inactiva, bloqueada o trabada, gasta el tiempo de
     un bcrypt contra el hash de relleno y responde el 401 genérico (`:319-322`);
   - si la contraseña actual no coincide, suma un fallo al mismo contador del login y responde el
     mismo 401 (`:324-326`);
   - si la nueva es igual a la actual, 400 (`:328-332`). Esa comparación no puede hacerse en texto:
     la actual no está guardada en ningún lado, así que se verifica la nueva contra el hash, como si
     fuera un intento de login;
   - guarda el hash nuevo, baja la marca de temporal y pone el contador en cero, en una sola
     confirmación (`:334-337`).
6. **La respuesta es un mensaje, sin sesión**
   ([por qué tampoco da sesión](A-07-autenticacion.md#4--el-cambio-de-clave-y-por-qué-tampoco-da-sesión)).
   La PWA avisa y vuelve al login (`CambiarPasswordView.tsx:70-71`); Flet vuelve a armar la
   pantalla de login (`login.py:202-203`).

**Qué escribe y qué lee.**

| Tabla | Atributo | Escribe o lee | Línea |
|---|---|---|---|
| `Usuario` | `username` | lee | `auth_router.py:313` |
| `Usuario` | `activo`, `bloqueado` | lee | `auth_router.py:104` (`_cuenta_no_disponible()`) |
| `Usuario` | `password_hash` | lee | `auth_router.py:324` y `:328` |
| `Usuario` | `password_hash` | escribe | `auth_router.py:334` |
| `Usuario` | `debe_cambiar_password` | escribe | `auth_router.py:335` |
| `Usuario` | `intentos_fallidos` | lee y escribe | `auth_router.py:96-99` (en un fallo) y `:336` (en el éxito) |

Coincide con la línea DFD. Un detalle que la línea deja ver: `debe_cambiar_password` se escribe pero
**no se lee**. El endpoint no exige que la cuenta esté marcada, así que cualquiera que sepa su
contraseña actual puede cambiarla por acá. Ninguna pantalla lo ofrece para una cuenta normal: las
dos apps sólo llegan a esta ruta desde el login con clave temporal.

**Por qué está hecho así.** El endpoint es **público porque quien lo necesita no puede tener sesión**:
el login se la negó justamente por tener la clave temporal, y si pidiera token la cuenta quedaría en
un punto muerto (`auth_router.py:7-12`). Lo que compensa esa apertura es que vuelve a pedir la
contraseña actual con todas las defensas del login: el nombre de usuario viaja en el cuerpo, escrito
por el cliente, y no da nada por sí solo.

El precio se paga en cálculo, y es el único lugar del sistema donde eso importa. Un cambio exitoso
corre bcrypt **tres veces** —verificar la actual, comparar la nueva contra el hash y hashear la
nueva—, a unos 171 ms cada una: medio segundo de CPU en un sistema donde
[el cuello es la red](A-11-rendimiento.md#el-cuello-es-la-red-nunca-python). No traba a nadie más
porque el endpoint es una función común y no una corrutina: FastAPI la corre en un
[hilo de trabajo](A0-10-python-del-lado-del-servidor.md#el-hilo-de-trabajo-para-las-funciones-síncronas).

**Cómo se llama:** *reautenticación*. En vez de confiar en una sesión, la operación sensible vuelve a
pedir el secreto.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| Más de 20 fallos desde esa IP en 10 minutos | 429 | *"Demasiados intentos fallidos. Esperá unos minutos y volvé a intentar."* | `auth_router.py:75-80`, llamado en `:312` |
| Cuenta inexistente, inactiva, bloqueada o trabada | 401 | *"Usuario o contraseña incorrectos"* | `auth_router.py:319-322` (`_rechazar()`, `:56-60`) |
| Contraseña actual equivocada | 401 | el mismo | `auth_router.py:324-326` |
| La nueva es igual a la actual | 400 | *"La contraseña nueva tiene que ser distinta de la actual."* | `auth_router.py:328-332` |
| Menos de 8 caracteres | 422 | *"String should have at least 8 characters"* | `schemas.py:120` |
| Sin letras o sin números | 422 | *"La contraseña tiene que tener letras y números."* | `schemas.py:133-135` |
| Una de las más usadas | 422 | *"Esa contraseña es de las más usadas. Elegí otra."* | `schemas.py:136-138` |
| Más de 72 bytes | 422 | *"La contraseña no puede superar los 72 caracteres."* | `schemas.py:139-141` |

Dos detalles de la tabla. El mensaje del largo mínimo es el único del sistema que sale en inglés:
lo arma Pydantic solo, porque `min_length` no lleva mensaje propio. No se ve en la práctica porque
las dos apps controlan el largo antes de mandar. Y el último mensaje dice "caracteres" donde el
límite es de bytes: con eñes o tildes entran menos de 72.

La salida de la línea DFD —*"rechazo por credenciales invalidas, contrasena nueva igual a la
anterior, contrasena debil o demasiados intentos"*— cubre las ocho filas.

---

### 3. Iniciar sesión

`POST /login` · sin sesión

**Qué resuelve.** Convertir un usuario y una contraseña en una sesión —una cookie en la PWA, un token
en Flet— o avisar que falta definir la contraseña.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/views/LoginView.tsx` | 24-122 | `LoginView` |
| Store PWA | `Proyecto - PWA/src/frontend/src/store/authStore.ts` | 107-135 | `login` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/authService.ts` | 57-104 | `LoginResultado`, `login()` |
| Esquemas | `backend/schemas.py` | 33-38 y 149-202 | `LoginRequest`; `PersonaOut`, `UsuarioOut`, `LoginResponse` |
| Endpoint | `backend/routers/auth_router.py` | 108-240 | `login()` |
| Freno de intentos | `backend/routers/auth_router.py` | 63-105 | `_HASH_DE_RELLENO`, `_ip()`, `_frenar_si_excede()`, `_registrar_intento_fallido()`, `_cuenta_no_disponible()` |
| Freno de intentos | `backend/limite_intentos.py` | 46-77 | `ip_excedida()`, `registrar_fallo_ip()`, `trabar_cuenta()`, `cuenta_trabada()` |
| Roles | `backend/models.py` | 1035-1082 | `roles_de_persona()` |
| Token | `backend/auth.py` | 148-191 | `crear_token_acceso()` |
| Cookies | `backend/cookies.py` y `backend/csrf.py` | 82-101 y 58-60 | `setear_cookies_sesion()`, `generar_token_csrf()` |
| Vista Flet | `Flet/Proyecto/app/views/login.py` | 29-145 y 267-318 | `show_login()`, `_load_main_app()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 84-159 | `login()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 90-97 y 385-394 | `HEADERS_CLIENTE`, `_headers()`, `login()` |
| Acceso a Flet | `Flet/Proyecto/app/permisos.py` | 324-339 y 390-403 | `ROLES_CON_ACCESO`, `ROLES_SIN_SECCIONES_QUE_ENTRAN`, `tiene_acceso_a_la_app()` |

**Cómo funciona.**

Del lado de la PWA:

1. El envío del formulario (`LoginView.tsx:42-63`) llama al store, y el store al service.
2. El service corta los campos vacíos antes de salir a la red (`authService.ts:80-82`) y manda el
   pedido sin ninguna cabecera especial (`:84-87`): para el backend, no declarar el cliente es ser un
   navegador.
3. La respuesta tiene dos formas, y el tipo obliga a distinguirlas: `LoginResultado` es una unión
   discriminada por `debeCambiarPassword` (`authService.ts:57-63`), así que TypeScript no deja leer
   los roles sin haber preguntado antes si hay sesión.
4. Si la clave es temporal, el store guarda sólo el nombre de usuario (`authStore.ts:115-117`) y la
   vista navega al cambio de contraseña (`LoginView.tsx:53-56`). Si hay sesión, el store guarda la
   identidad (`authStore.ts:120-130`) y la vista navega a la primera pantalla del rol
   (`LoginView.tsx:59`, con `rutaInicialPara()` de `config.ts:943-947`).
5. Cualquier error se muestra debajo de los campos, con el aviso de la traba de 15 minutos
   (`LoginView.tsx:96-105`). El aviso aparece ante cualquier error y no dice cuántos intentos
   quedan: decirlo confirmaría que el usuario existe (`config.ts:166-169`).

Del lado de Flet, el mismo recorrido: `handle_login()` (`login.py:37-71`) valida los campos
(`:42-46`) y llama a `state.login()` (`state.py:84-159`), que manda el pedido con
`X-Client-Type: escritorio` (`api_client.py:90-97`). Con la clave temporal guarda el usuario
pendiente (`state.py:106-111`); con sesión guarda el token (`:133`), arma el usuario activo
(`:138-150`), lanza la precarga del caché (`:157`) y la vista construye la aplicación
(`login.py:267-318`).

En el backend, `login()` (`auth_router.py:108-240`) hace, en orden:

1. **Campos vacíos → 400** (`:139-153`), antes de tocar la base.
2. **IP del socket → 429** si ya gastó su cupo (`:155-156`;
   [la IP que no se puede falsificar](A-07-autenticacion.md#la-ip-que-no-se-puede-falsificar)).
3. **Busca la cuenta** por nombre de usuario (`:158`).
4. **Cuenta no disponible → 401 genérico**, con el hash de relleno para igualar el tiempo
   (`:160-163`; [cuatro motivos, una sola respuesta](A-07-autenticacion.md#cuatro-motivos-una-sola-respuesta)).
5. **Contraseña incorrecta → suma un fallo, confirma y 401** (`:165-167`). Confirmar antes de fallar
   es lo que hace que el fallo cuente ([los dos frenos](A-07-autenticacion.md#los-dos-frenos)).
6. **Cuenta sin persona → 401** (`:171-175`). No debería pasar, porque la columna es obligatoria y
   tiene clave foránea: es una defensa ante una base inconsistente.
7. **Clave temporal → contador en cero y la respuesta sin sesión** (`:181-184`;
   [el primer login no da sesión](A-07-autenticacion.md#3--el-primer-login-no-da-sesión)).
8. **Roles** (`:186-194`), derivados de las tablas subtipo
   ([derivación de roles](A-06-los-seis-roles.md#derivación-de-roles)). Sin ninguno, 403.
9. **Los ids que viajan firmados**: el del socio con una consulta (`:196-197`) y el del profesor
   navegando desde la persona (`:202-208`) ([identidad firmada](A-07-autenticacion.md#identidad-firmada)).
10. **Contador en cero y último acceso**, confirmados (`:210-213`).
11. **El token** (`:215-221`): un [JWT](A0-12-sesiones-y-autenticacion.md#jwt) firmado con
    [HMAC](A0-11-criptografia-aplicada.md#hmac-y-firma-simétrica), que lleva el usuario, los roles
    y los dos ids (`auth.py:176-191`).
12. **Por dónde viaja** (`:216-224`): con `X-Client-Type: escritorio`, en el cuerpo; sin esa
    cabecera, en dos cookies —la de sesión, `httponly`, y la del token CSRF— y el campo `token` del
    cuerpo sale en `null` ([los dos mecanismos](A-07-autenticacion.md#los-dos-mecanismos-de-sesión-y-x-client-type)).
13. **La respuesta** (`:226-233`), con la cuenta sin el hash —`UsuarioOut` no lo declara, y ésa es la
    única razón por la que no puede filtrarse (`schemas.py:161-165`)—, la persona, los roles y el id
    de socio.

**Qué escribe y qué lee.**

| Tabla | Atributo | Escribe o lee | Línea |
|---|---|---|---|
| `Usuario` | `username` | lee | `auth_router.py:158` |
| `Usuario` | `activo`, `bloqueado` | lee | `auth_router.py:104` |
| `Usuario` | `password_hash` | lee | `auth_router.py:165` |
| `Usuario` | `debe_cambiar_password` | lee | `auth_router.py:181` |
| `Usuario` | `id_persona`, `id_usuario` | lee | `auth_router.py:171` y `:216` |
| `Usuario` | `intentos_fallidos` | lee y escribe | `auth_router.py:96-99` (sube en un fallo), `:182` y `:210` (vuelve a cero) |
| `Usuario` | `ultimo_acceso` | escribe | `auth_router.py:211` |
| `Persona` | `id_persona`, `nombre`, `apellido`, `dni`, `email`, `fecha_nacimiento`, `activo` | lee | `auth_router.py:171` y `:237` (`PersonaOut`, `schemas.py:149-158`) |
| `Dueno`, `Socio`, `Empleado`, `Entrenador`, `Nutricionista`, `Recepcionista`, `Profesor` | la existencia de la fila | lee | `models.py:1035-1082` (`roles_de_persona()`), más `auth_router.py:196` (`Socio`) y `:202-208` (`Profesor`) |

Las tablas y los atributos coinciden con la línea DFD. La salida, no del todo: la línea declara
*"Sesion iniciada, cambio de contrasena obligatorio, acceso denegado, cuenta trabada o cuenta sin
perfil"*, y el código tiene dos rechazos que no nombra: **el 400 de campos vacíos** (`:149-153`) y
**el 429 por IP** (`:156`). El proceso 2 sí declara su 429 (*"demasiados intentos"*). Es un
hallazgo contra el archivo de procesos, no contra el código.

**Por qué está hecho así.** El diseño de fondo está en [A-07](A-07-autenticacion.md), y este proceso
lo ejecuta entero. Lo que se ve mejor desde acá es cómo las dos apps tratan **los tres desenlaces**.
Un login no sale bien o mal: puede salir bien, salir mal, o salir bien sin abrir sesión. El backend
lo modela en una sola respuesta 200 con una bandera, en vez de inventar un código de error para el
tercer caso (`schemas.py:189-191`). La PWA lo convierte en un tipo que obliga a mirar la bandera
(`authService.ts:57-63`), el store lo documenta como *"Tres desenlaces y no dos"*
(`authStore.ts:47-48`), y Flet devuelve tres formas de diccionario (`state.py:88-93`). Nadie puede
tratar "falta la contraseña" como si fuera un error, ni como si fuera una sesión.

**Cómo se llama:** una *unión discriminada*: un tipo con varias formas y un campo que dice cuál es.

**Quién entra a Flet, y el Profesor que entra sin secciones.** Para el backend, el Profesor es un rol
como cualquier otro: `roles_de_persona()` lo agrega (`models.py:1080-1080`), el login le da sesión y
el token lo lleva. La app de escritorio filtra después, del lado del cliente: `state.login()` sólo
guarda el token si `tiene_acceso_a_la_app()` da verdadero (`state.py:125-131`). Entra quien tenga
algún rol de `ROLES_CON_ACCESO` —los que tienen al menos una sección distinta de NINGUNO en la
matriz de Flet, calculados de la matriz (`permisos.py:324-327`)— **o** algún rol de
`ROLES_SIN_SECCIONES_QUE_ENTRAN` (`permisos.py:329-339`), que hoy es sólo el Profesor. El
Profesor tiene sus diez secciones en NINGUNO (`permisos.py:314-317`): su pantalla, "Mis clases",
está en la PWA. Dos caminos, entonces:

- **El Socio** queda afuera, con un mensaje escrito para él: *"Esta aplicación es para el personal
  del gimnasio. Si sos socio, entrá desde la web con estas mismas credenciales."* Su portal entero
  está en la web.
- **El Profesor** entra, y como no tiene ninguna sección, `primera_seccion()` da `None` y la carga
  de la app le muestra `SinSeccionesView` en vez de una sección (`Flet/Proyecto/app/views/login.py:286-294`):
  *"Tu pantalla está en la app del celular"*, con el sidebar reducido al logo, su nombre y "Cerrar
  sesión". Corriendo la carga real con una sesión de profesor simulada, eso es exactamente lo que
  queda en la página; y `tiene_acceso_a_la_app()` da `True` para `["profesor"]` y `False` para
  `["socio"]`.

La excepción está escrita como un conjunto con nombre y no como un `if rol == "profesor"` en el
login porque dice una regla: entra el personal aunque no tenga nada que hacer acá, y no entra el
socio. Hasta el 2026-09-26, `ROLES_CON_ACCESO` era la única condición, y el Profesor recibía el
mensaje del socio; `SinSeccionesView` existía para él y no la alcanzaba nadie.

**El usuario, en minúsculas.** El backend pasa a minúsculas el nombre que llega (`auth_router.py:139-143`)
antes de buscarlo (`:158`), y así se guardan todos: los que genera el sistema (`_sin_tildes()`,
`auth.py:102-112`), el del dueño inicial (`seeder.py:46-47`) y los que se renombran desde Usuarios
([B-04, proceso 41](B-04-usuarios-y-cuentas.md#41-editar-el-usuario-y-el-email-de-una-cuenta)). Flet
lo pasa a minúsculas también del lado del cliente (`login.py:38`), y la PWA sólo recorta los espacios
(`limpiar()`, `services/validacion.ts:6-8`); desde el 2026-09-26 da igual. Antes el backend comparaba el
nombre tal cual, y una cuenta con una mayúscula entraba por la PWA y no por Flet.

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| Usuario o contraseña vacíos | 400 | *"Completá usuario y contraseña"* | `auth_router.py:149-153` (y antes, en `authService.ts:80-82` y `login.py:42-46`) |
| Más de 20 fallos desde esa IP en 10 minutos | 429 | *"Demasiados intentos fallidos. Esperá unos minutos y volvé a intentar."* | `auth_router.py:156` |
| Cuenta inexistente, inactiva, bloqueada o trabada | 401 | *"Usuario o contraseña incorrectos"* | `auth_router.py:160-163` |
| Contraseña incorrecta | 401 | el mismo | `auth_router.py:165-167` |
| La cuenta no tiene persona | 401 | el mismo | `auth_router.py:172-175` |
| Ningún rol de sesión | 403 | *"Tu cuenta no tiene ningún perfil asignado. Hablá con el gimnasio."* | `auth_router.py:187-194` (su comentario pone de ejemplo al Profesor, que ya es un rol: [nota del ejemplo](A-07-autenticacion.md#nota-marcada--el-ejemplo-del-profesor-sin-rol)) |
| En Flet, un rol sin secciones en la app | — (el backend respondió 200) | *"Esta aplicación es para el personal del gimnasio…"* | `state.py:125-131` |

---

### 4. Cerrar sesión

`POST /logout` · sin sesión obligatoria

**Qué resuelve.** Borrar del navegador las dos cookies de la sesión, que JavaScript no puede borrar.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/components/ui/Sidebar.tsx` | 16-19 | `handleLogout` |
| Store PWA | `Proyecto - PWA/src/frontend/src/store/authStore.ts` | 166-202 | `sesionPerdida`, `logout` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/authService.ts` | 114-116 | `logout()` |
| Endpoint | `backend/routers/auth_router.py` | 243-262 | `logout()` |
| Cookies | `backend/cookies.py` | 104-116 | `borrar_cookies_sesion()` |
| Vista Flet | `Flet/Proyecto/app/components/ui.py` | 78-82 | `handle_logout()` |
| Estado Flet | `Flet/Proyecto/app/state.py` | 183-192 | `logout()` |
| Cliente Flet | `Flet/Proyecto/app/api_client.py` | 61-72 | `limpiar_token()` — no llama al endpoint |

**Cómo funciona.**

En la PWA, el botón llama a `logout()` sin esperarlo y navega al login en el mismo momento
(`Sidebar.tsx:17-18`). El store sí espera al service (`authStore.ts:188`), y después limpia la
identidad (`:194-201`). El pedido lleva el token CSRF en la cabecera, como todo pedido que no es
`GET` (`api.ts:203-206`), y lo necesita: como hay cookie de sesión, el middleware exige que cabecera
y cookie coincidan (`csrf.py:74-93`). Por eso nadie puede cerrarte la sesión desde otro sitio
(`auth_router.py:254-255`).

El endpoint no pide sesión válida —si el token ya venció, igual hay que poder limpiar las cookies—,
llama a `borrar_cookies_sesion()` y contesta un mensaje (`auth_router.py:261-262`). Cómo se borra
una cookie, y por qué la ruta tiene que coincidir con la del alta, está en
[cookie y sus atributos](A0-12-sesiones-y-autenticacion.md#cookie-y-sus-atributos).

El mismo endpoint tiene un segundo cliente: cuando un pedido cualquiera vuelve con 401,
`sesionPerdida()` lo llama para borrar las cookies (`authStore.ts:166-180`), disparado desde
`App.tsx:73-78`.

En Flet no hay pedido. El botón (`ui.py:78-82`) llama a `state.logout()`, que suelta el token y tira
el caché entero (`api_client.py:61-72`;
[lo que escribe invalida todo](A-11-rendimiento.md#lo-que-escribe-invalida-todo)), y vuelve a la
pantalla de login. No hace falta más: `/logout` sólo borra cookies, y Flet no tiene ninguna.

**Qué escribe y qué lee.** La línea DFD declara `<- ()`, y el código coincide: el endpoint no toca
ninguna tabla. Lo único que cambia es el almacén de cookies del navegador.

**Por qué está hecho así.** El endpoint existe porque la cookie es `httponly`: sin el servidor, cerrar
sesión limpiaría la pantalla y dejaría la cookie viva para el próximo que use esa máquina. Y no
revoca nada: el token sigue siendo válido hasta que vence
([caducidad y revocación](A0-12-sesiones-y-autenticacion.md#caducidad-y-revocación)).

Lo que se ve acá es que el cierre es **optimista**: la pantalla se va antes de que el servidor
confirme, y si el servidor no contesta, el store se limpia igual (`authStore.ts:189-193`). Se eligió
no dejar a nadie "adentro" por un fallo de red. El precio es que, en ese caso, la cookie queda viva
hasta su vencimiento, que es el mismo del token: 480 minutos (`cookies.py:79`).

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| Cookie de sesión presente sin el token CSRF que coincida | 403 | *"Token CSRF ausente o inválido. Volvé a iniciar sesión."* | `backend/csrf.py:87-93` |
| El servidor no contesta | — | ninguno: el store se limpia igual | `authStore.ts:189-193` |

---

### 5. Recuperar la sesión vigente

`GET /me` · una sesión válida

**Qué resuelve.** Que un F5 no cierre la sesión en la PWA: la página arranca en blanco y le pregunta
al backend quién es.

**Dónde vive el código**

| Capa | Archivo | Líneas | Símbolo |
|---|---|---|---|
| Vista PWA | `Proyecto - PWA/src/frontend/src/App.tsx` | 55-80 | `App` (el efecto que rehidrata, 65-67, y la espera, 80) |
| Store PWA | `Proyecto - PWA/src/frontend/src/store/authStore.ts` | 78-105 | `isRehidratando`, `rehidratar` |
| Cliente PWA | `Proyecto - PWA/src/frontend/src/services/api.ts` | 101-116 y 166 | `tokenCsrf()`, `haySesion()`, `SIN_SESION_PROPIA` |
| Service PWA | `Proyecto - PWA/src/frontend/src/services/authService.ts` | 126-135 | `sesionActual()` |
| Sesión | `backend/security.py` | 80-142 | `obtener_sesion()` |
| Endpoint | `backend/routers/auth_router.py` | 265-292 | `sesion_actual()` |
| Esquemas | `backend/schemas.py` | 149-202 | `PersonaOut`, `UsuarioOut`, `LoginResponse` |
| Vista Flet | — (no existe en Flet) | | |

Que no exista en Flet es correcto: la app de escritorio no se recarga. El token vive en la memoria del
proceso y la sesión termina cuando se cierra la ventana.

**Cómo funciona.**

1. **Antes de preguntar, una pista.** El store arranca en "rehidratando" sólo si hay cookies
   (`authStore.ts:79`). Como la de sesión es `httponly`, `haySesion()` mira la otra, la del token
   CSRF, que se emite y se borra junto con ella (`api.ts:106-116`). Mientras tanto, `App.tsx` no
   monta el enrutador (`:80`): si lo montara, la
   [ruta protegida](A-08-autorizacion.md#el-frontend-esconde-el-backend-rechaza) vería "sin sesión" y
   mandaría al login antes de que llegue la respuesta.
2. **El pedido** sale al montar la aplicación (`App.tsx:65-67`), y el navegador adjunta la cookie.
3. **`obtener_sesion()`** (`security.py:80-142`) toma el token de la cabecera o de la cookie
   (`:108`), verifica firma y vencimiento (`:112`), relee la cuenta de la base (`:121-123`) y rechaza
   la que tiene que cambiar la clave (`:129-134`). Por qué se relee la cuenta en cada pedido está en
   [identidad firmada](A-07-autenticacion.md#por-qué-se-resuelve-una-vez-y-se-relee-siempre).
4. **`sesion_actual()`** arma la misma forma que el login, sin token (`auth_router.py:283-292`): la
   cuenta y la persona salen de la base, **los roles y el id de socio salen del token** (`:290-291`).
5. **La vuelta.** Con sesión, el store guarda la identidad (`authStore.ts:87-95`). Sin sesión,
   marca "no autenticado" sin mostrar ningún error (`:96-104`), porque nadie hizo nada mal. `/me`
   está en la lista de rutas donde un 401 no es una sesión caída (`api.ts:162-166`), así que ese
   rechazo no dispara el cierre de `sesionPerdida()`.

**Qué escribe y qué lee.**

| Tabla | Atributo | Escribe o lee | Línea |
|---|---|---|---|
| `Usuario` | `activo`, `bloqueado`, `debe_cambiar_password` | lee | `security.py:122` y `:129` |
| `Usuario` | `id_usuario`, `id_persona`, `username`, `ultimo_acceso`, `activo` | lee | `auth_router.py:288` (`UsuarioOut`) |
| `Persona` | `id_persona`, `nombre`, `apellido`, `dni`, `email`, `fecha_nacimiento`, `activo` | lee | `auth_router.py:283` y `:289` (`PersonaOut`) |

Coincide con la línea DFD, y lo que la línea no dice también es exacto: **no lee ninguna tabla de
rol**, porque los roles salen del token. Son dos consultas contra la base —la cuenta por clave
primaria y la persona al tocar la relación—, unos 90 ms contra Neon
([base remota](A-11-rendimiento.md#base-remota)).

**Por qué está hecho así.** La identidad no se guarda en el navegador: se le pregunta al backend en
cada arranque. Si los roles vivieran en el almacenamiento de la página, alcanzaría con editarlos
desde las herramientas del navegador para ver secciones ajenas (`api.ts:83-86`). Se paga con un pedido
por cada carga de la página y la pantalla de espera que lo acompaña; se gana que el backend siga
siendo la única fuente sobre quién es cada uno. El docstring de este endpoint todavía dice que la
PWA guarda el token en `sessionStorage`, y no es así: está anotado en
[los dos mecanismos de este sistema](A0-12-sesiones-y-autenticacion.md#los-dos-mecanismos-de-este-sistema-y-por-qué-son-dos).

**Qué pasa cuando sale mal.**

| Caso | Código | Mensaje | Dónde |
|---|---|---|---|
| No hay cookie ni cabecera | 401 | *"No se pudo validar la sesión. Iniciá sesión nuevamente."* | `security.py:109-110` |
| Token alterado o vencido, o sin un id válido | 401 | el mismo | `security.py:112-119` |
| La cuenta no existe, está inactiva o bloqueada | 401 | el mismo | `security.py:121-123` |
| La cuenta tiene que cambiar la clave | 401 | *"Tenés que cambiar tu contraseña antes de seguir usando el sistema."* | `security.py:129-134` |
| El token no trae una lista de roles | 401 | el genérico | `security.py:136-138` |

En la PWA, los cinco terminan igual: sin mensaje, en la pantalla de login (`authStore.ts:96-104`).

---

## Nota marcada · el 403 de CSRF no figura en ninguna salida

Todo pedido que no es de lectura y lleva la cookie de sesión pasa por el middleware de CSRF, que
responde 403 si la cabecera no coincide con la cookie (`backend/csrf.py:87-93`). En esta sección
alcanza a los procesos 2, 3 y 4 cuando hay cookies de una sesión anterior, y fuera de ella a cada
proceso que escribe desde la PWA.

Ninguna línea de `PROCESOS-LOGICOS-REQUERIDOS.md` nombra ese rechazo. El archivo trata al middleware
como función interna (convención 5): sus lecturas cuentan dentro del proceso que lo atraviesa. Pero
la convención 2 pide que la salida nombre los errores, y éste es un error que el usuario puede ver.
Es un límite de cómo se aplicaron las dos convenciones juntas, no un defecto del código, y vale para
todos los capítulos de la Parte B: se anota una sola vez, acá.

---

## Con qué se conecta

- **Es la misma idea que…** [el sistema informa, no juzga](A-01-que-es-olimpos.md#el-sistema-informa-no-juzga):
  el login con clave temporal es un tercer desenlace entre "salió" y "falló", como el ingreso con la
  cuota vencida, y las dos apps lo modelan para que nadie lo trate como error.
- **Se contradice con…** [el cuello es la red, nunca Python](A-11-rendimiento.md#el-cuello-es-la-red-nunca-python):
  cambiar la clave corre tres bcrypt, medio segundo de cálculo puro; ganó el
  [hash lento](A0-11-criptografia-aplicada.md#sal-y-hash-lento), que está para ser caro.
- **Es el mismo problema que…** el [puerto](A0-02-como-se-comunican-dos-maquinas.md#puerto) tomado por
  el proceso viejo: `GET /` contesta "ok" desde cualquier proceso que escuche, y por eso no sirve para
  saber cuál atiende.
