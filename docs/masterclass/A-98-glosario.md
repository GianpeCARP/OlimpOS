# A-98 · Glosario

*Apéndice de la Parte A. No tiene piso, porque no explica nada: nombra y remite.*

Cada fila es un concepto definido a fondo en la Parte A0 o en la Parte A, con una línea para
reconocerlo y el enlace al único lugar que lo explica. La línea es un recordatorio, no una
explicación: si no alcanza, el enlace lleva a la sección donde el concepto arranca por el problema
que vino a resolver y baja hasta su piso. Ése es el único lugar donde está explicado, y este glosario
no le agrega nada.

Son **144 conceptos**, cada uno con un solo capítulo dueño. Hay además dos cosas que no son
conceptos:

- **Remisiones**, en cursiva y con una flecha: el nombre con que alguien suele buscar algo —*ACID*,
  *IDOR*, *`SameSite`*, *409*— apuntando al concepto que lo contiene. No definen nada.
- **Patrones con nombre**, al final: las jugadas de diseño que los capítulos identifican en sus
  "Cómo se llama", para reconocer la misma jugada cuando reaparece en otro lugar del sistema.

El orden es alfabético sin contar los artículos del principio —"El mostrador con cola" está en la
M—, las tildes ni el formato de código. Para recorrer las relaciones entre conceptos en vez de sus
nombres está el [mapa de conexiones](A-99-mapa-de-conexiones.md); para decidir qué leer, la tabla de
ruteo del [índice](00-indice.md).

**Ir a:** [0–9](#números) · [A](#a) · [B](#b) · [C](#c) · [D](#d) · [E](#e) · [F](#f) · [G](#g) · [H](#h) · [I](#i) · [J](#j) · [K](#k) · [L](#l) · [M](#m) · [N](#n) · [O](#o) · [P](#p) · [R](#r) · [S](#s) · [T](#t) · [U](#u) · [V](#v) · [W](#w) · [X](#x) · [Z](#z) · [Patrones con nombre](#patrones-con-nombre)

## Números

| Término | Qué es | Capítulo |
|---|---|---|
| *401* | → [el 401 de la sesión caída](A0-03-http.md#el-401-de-la-sesión-caída) | A0-03 |
| *403 contra 404* | → [Aislamiento de lo propio](A-08-autorizacion.md#aislamiento-de-lo-propio) | A-08 |
| *409* | → [Sin cobros por adelantado](A-02-prepago-puro.md#sin-cobros-por-adelantado) | A-02 |
| *422* | → [Esquema de entrada y salida, y el 422](A0-10-python-del-lado-del-servidor.md#esquema-de-entrada-y-salida-y-el-422) | A0-10 |
| *429* | → [Freno de intentos y respuesta indistinguible](A-07-autenticacion.md#freno-de-intentos-y-respuesta-indistinguible) | A-07 |

## A

| Término | Qué es | Capítulo |
|---|---|---|
| *ACID* | → [Transacción, ACID, commit y rollback](A0-07-bases-de-datos-relacionales.md#transacción-acid-commit-y-rollback) | A0-07 |
| [Aislamiento de lo propio](A-08-autorizacion.md#aislamiento-de-lo-propio) | Lo del socio se pide sin id, y lo que se armó solo es invisible para el personal: responde 404 y no 403, porque un 403 confirmaría que existe. | A-08 |
| [Aleatoriedad criptográfica y base64url](A0-11-criptografia-aplicada.md#aleatoriedad-criptográfica-y-base64url) | Un valor impredecible, sacado del generador del sistema operativo (`secrets`, no `random`), y su escritura en caracteres aptos para una URL o una cabecera. | A0-11 |
| [Almacén que no es tabla](A-05-modelo-de-datos.md#almacén-que-no-es-tabla) | Estado que no vive en ninguna fila: que el archivo del video exista en el disco es que está descargado, y no hay columna que lo diga. | A-05 |
| [Almacenamiento del navegador](A0-04-el-navegador-por-dentro.md#almacenamiento-del-navegador) | `localStorage`, `sessionStorage` e IndexedDB: lo que la página guarda en el dispositivo, atado a su origen y sin viajar nunca al servidor. | A0-04 |
| [Ángulo entre tres puntos](A0-14-vision-en-el-dispositivo.md#ángulo-entre-tres-puntos) | Dos vectores, su producto escalar, sus módulos y el arcocoseno: la cuenta que convierte tres puntos en el ángulo de una articulación. | A0-14 |
| [Aplicación gemela y componente gemelo](A-03-dos-apps-un-backend.md#aplicación-gemela-y-componente-gemelo) | La PWA es la referencia y Flet su gemela: todo arreglo se replica en la misma tanda, y cada componente de Flet nombra en un comentario su `.tsx` gemelo. | A-03 |
| [Árbol virtual y reconciliación](A0-06-react.md#árbol-virtual-y-reconciliación) | La descripción en memoria de lo que debería verse, y el algoritmo que la compara con la anterior para tocar lo mínimo del DOM real. | A0-06 |
| [ASGI, uvicorn y el router](A0-10-python-del-lado-del-servidor.md#asgi-uvicorn-y-el-router) | El contrato entre servidor y aplicación Python, el proceso que escucha el puerto, y la tabla que asocia método y ruta con una función. | A0-10 |
| [Asignación con estado](A-05-modelo-de-datos.md#asignación-con-estado) | `Asignacion_Rutina` y `Asignacion_Dieta` guardan todo el historial con su `estado`, y un índice único parcial garantiza una sola `ACTIVA` por socio. | A-05 |
| [`assets_dir` y modo web](A0-13-flutter-y-flet.md#assets_dir-y-modo-web) | La carpeta de donde Flet toma sus archivos estáticos, y lo que cambia cuando en vez de abrir una ventana sirve una página. | A0-13 |
| *`async`/`await`* | → [Bucle de eventos, tarea y microtarea, promesa y `async`/`await`](A0-04-el-navegador-por-dentro.md#bucle-de-eventos-tarea-y-microtarea-promesa-y-asyncawait) | A0-04 |
| [Ataque de diccionario](A0-11-criptografia-aplicada.md#ataque-de-diccionario) | Probar contra un hash robado las contraseñas que la gente de verdad usa, en orden de frecuencia: el ataque que define cuánta lentitud hace falta. | A0-11 |

## B

| Término | Qué es | Capítulo |
|---|---|---|
| [Baja lógica (soft delete)](A-10-bajas-logicas.md#baja-lógica-soft-delete) | Nada se borra: se marca. La baja es un hecho con fecha y tipo, porque los pagos siguen siendo del gimnasio y la persona puede volver. | A-10 |
| [Baja programada y baja inmediata](A-10-bajas-logicas.md#baja-programada-y-baja-inmediata) | Con cuota vigente la baja se agenda para el día siguiente al vencimiento y se puede anular; "dar de baja ahora" corta hoy, pierde los días pagos y adelanta una programada. | A-10 |
| [Base remota](A-11-rendimiento.md#base-remota) | La base vive en Neon, en São Paulo: 44 ms por consulta y 825 ms por conexión nueva, y eso reordena todas las decisiones de rendimiento. | A-11 |
| *Bearer* | → [Token portador y `Authorization`](A0-12-sesiones-y-autenticacion.md#token-portador-y-authorization) | A0-12 |
| *Borrado de tipos* | → [Tipado estático y borrado de tipos](A0-05-javascript-y-typescript.md#tipado-estático-y-borrado-de-tipos) | A0-05 |
| [Borrado real de la cuenta](A-10-bajas-logicas.md#borrado-real-de-la-cuenta) | Borrar un `Usuario` borra sólo la credencial: la persona y su historial quedan. Nadie borra la propia, sólo un dueño borra la de otro dueño, y nunca la última. | A-10 |
| [Bucle de eventos, tarea y microtarea, promesa y `async`/`await`](A0-04-el-navegador-por-dentro.md#bucle-de-eventos-tarea-y-microtarea-promesa-y-asyncawait) | El único hilo de la página, que ejecuta de a una tarea y vacía las microtareas entre tarea y tarea; la promesa es el valor que llega después y reanuda la función suspendida. | A0-04 |
| *Bytecode* | → [Intérprete, bytecode y compilación al vuelo](A0-01-como-corre-un-programa.md#intérprete-bytecode-y-compilación-al-vuelo) | A0-01 |

## C

| Término | Qué es | Capítulo |
|---|---|---|
| [Cabecera HTTP](A0-03-http.md#cabecera-http) | Un metadato de una línea, `Nombre: valor`, sobre el pedido o la respuesta; es el canal de `Cookie`, `Authorization`, `X-CSRF-Token` y `X-Client-Type`. | A0-03 |
| *Caché de Flet* | → [Servir y refrescar](A-11-rendimiento.md#servir-y-refrescar) | A-11 |
| [Caducidad y revocación](A0-12-sesiones-y-autenticacion.md#caducidad-y-revocación) | Que una sesión muera sola por tiempo —fácil: una fecha adentro del token— y el problema aparte de matarla antes de que venza. | A0-12 |
| [La caja y sus cuatro casos](A-02-prepago-puro.md#la-caja-y-sus-cuatro-casos) | El cobro en el mostrador existe para el efectivo, el socio que no usa la app, el pago que entró por fuera y la corrección de un cobro; es una regla de uso, no de código. | A-02 |
| [Canvas de Flutter](A0-13-flutter-y-flet.md#canvas-de-flutter) | Flutter no usa controles del sistema: pinta él mismo cada píxel, y por eso la app de escritorio puede verse casi igual que la PWA. | A0-13 |
| [Las capas del recorrido](A-04-recorrido-de-un-pedido.md#las-capas-del-recorrido) | Vista → service → red → proxy → middlewares → permisos → handler → esquema → ORM → base, y la vuelta: todo proceso de la Parte B es una variación de este camino. | A-04 |
| [Carga perezosa contra carga ansiosa](A0-09-el-orm.md#carga-perezosa-contra-carga-ansiosa) | Traer una relación recién al tocarla, o traerla por adelantado junto con el listado; `selectinload` es la segunda, en una consulta aparte y en lote. | A0-09 |
| [Catálogo contra observación](A-05-modelo-de-datos.md#catálogo-contra-observación) | `Patologia` dice qué condiciones existen; `Socio_Patologia`, cuál tiene cada socio y qué hacer con ella. | A-05 |
| [Cierre (closure)](A0-05-javascript-y-typescript.md#cierre-closure) | Una función que se lleva el entorno donde fue escrita; es lo que permite que un manejador o un hook usen valores de un render que ya terminó. | A0-05 |
| [Clase suelta y abono de actividad](A-02-prepago-puro.md#clase-suelta-y-abono-de-actividad) | Las dos formas de vender actividad aparte de la cuota; la clase suelta es un `Plan_Actividad` con `tipo_limite = CLASE_SUELTA`, y las clases restantes se cuentan, no se guardan. | A-02 |
| [Clave foránea y acción referencial](A0-07-bases-de-datos-relacionales.md#clave-foránea-y-acción-referencial) | La columna que apunta a la clave primaria de otra tabla, y lo que la base hace con el hijo cuando muere el padre: `CASCADE`, `SET NULL` o rechazo. | A0-07 |
| [Clave (`key`) de lista](A0-06-react.md#clave-key-de-lista) | La identidad de cada hijo de una lista, para que la reconciliación empareje por identidad y no por posición. | A0-06 |
| [Clave primaria e identidad generada](A0-07-bases-de-datos-relacionales.md#clave-primaria-e-identidad-generada) | La columna que identifica cada fila sin ambigüedad; en 40 de las 41 tablas es un entero que la base genera al insertar (`GENERATED BY DEFAULT AS IDENTITY`). | A0-07 |
| [Clave secreta](A0-11-criptografia-aplicada.md#clave-secreta) | El único dato que separa a quien puede firmar de quien no; rotarla invalida de golpe todas las firmas emitidas. | A0-11 |
| [Código de estado](A0-03-http.md#código-de-estado) | El entero de tres dígitos que clasifica la respuesta; el backend emite doce distintos, y el `409` —una regla de negocio con estado— es el característico de este sistema. | A0-03 |
| *Commit* | → [Transacción, ACID, commit y rollback](A0-07-bases-de-datos-relacionales.md#transacción-acid-commit-y-rollback) · [`flush` contra `commit`](A0-09-el-orm.md#flush-contra-commit) | A0-07, A0-09 |
| [Componente y JSX](A0-06-react.md#componente-y-jsx) | Una función que recibe datos y devuelve una descripción de pantalla; JSX es sintaxis que se convierte en llamadas a funciones y desaparece al compilar. | A0-06 |
| *Compuerta lógica* | → [Instrucción de máquina y compuerta lógica](A0-01-como-corre-un-programa.md#instrucción-de-máquina-y-compuerta-lógica) | A0-01 |
| [`CONCEPTO_SALIDA` con errores](A-12-como-leer-los-procesos.md#concepto_salida-con-errores) | La salida de cada proceso declara el camino feliz y también todos sus rechazos: un alta dice además "rechazo por DNI ya registrado". | A-12 |
| *Contador de repeticiones* | → [Máquina de estados con umbral](A0-14-vision-en-el-dispositivo.md#máquina-de-estados-con-umbral) · [Inferencia en el dispositivo](A0-14-vision-en-el-dispositivo.md#inferencia-en-el-dispositivo) | A0-14 |
| [Contraseña temporal y primer ingreso](A-07-autenticacion.md#contraseña-temporal-y-primer-ingreso) | La cuenta nace con una clave generada que se muestra una sola vez; hasta que la persona elige la suya, el login no da sesión y el backend rechaza sus tokens. | A-07 |
| [Control de Flet, `update()` y `page.overlay`](A0-13-flutter-y-flet.md#control-de-flet-update-y-pageoverlay) | El objeto Python gemelo de cada widget, la llamada que le manda al cliente sólo la diferencia, y la capa donde viven los diálogos. | A0-13 |
| [Cookie y sus atributos](A0-12-sesiones-y-autenticacion.md#cookie-y-sus-atributos) | El dato que el servidor manda con `Set-Cookie` y el navegador reenvía solo; `HttpOnly`, `Secure`, `SameSite`, dominio y vencimiento tapan agujeros de ese mecanismo mínimo. | A0-12 |
| [Corrutina](A0-10-python-del-lado-del-servidor.md#corrutina) | Una función que puede suspenderse a mitad de camino y devolverle el control al bucle sin perder su estado. | A0-10 |
| [CORS y preflight](A0-12-sesiones-y-autenticacion.md#cors-y-preflight) | La excepción reglamentada a la política del mismo origen, que hace cumplir el navegador, y el pedido `OPTIONS` previo que exige a los pedidos que no son simples. | A0-12 |
| [CSRF](A0-12-sesiones-y-autenticacion.md#csrf) | El ataque que aprovecha que la cookie se reenvía sola: otro sitio dispara un pedido y el navegador lo autentica sin que nadie se entere. | A0-12 |
| [CSS utilitario y viewport móvil](A0-04-el-navegador-por-dentro.md#css-utilitario-y-viewport-móvil) | Clases de una sola declaración (`flex`, `px-4`) que se generan sólo si se usan, y las unidades del viewport: en iOS `dvh` sigue a la barra de Safari y `vh` no. | A0-04 |
| [El cuello es la red, nunca Python](A-11-rendimiento.md#el-cuello-es-la-red-nunca-python) | La conclusión sobre rendimiento: en este sistema optimizar cálculo no mueve la aguja; ahorrar viajes a la base, sí. | A-11 |

## D

| Término | Qué es | Capítulo |
|---|---|---|
| *Deber* | → [Membresía vigente y qué significa "deber"](A-02-prepago-puro.md#membresía-vigente-y-qué-significa-deber) | A-02 |
| [Derivación de roles](A-06-los-seis-roles.md#derivación-de-roles) | Los roles se calculan mirando en qué tablas subtipo aparece la persona, se acumulan, y se derivan una sola vez, en el login, para no repetir esas consultas en cada pedido. | A-06 |
| *Deuda* | → [Prepago puro](A-02-prepago-puro.md#prepago-puro) | A-02 |
| [DFD lineal](A-12-como-leer-los-procesos.md#dfd-lineal) | La notación de una línea por proceso de `PROCESOS-LOGICOS-REQUERIDOS.md`: entidad, entrada, salida, evento, tablas escritas y tablas leídas, en ese orden. | A-12 |
| *Diputado confundido* | → [CSRF](A0-12-sesiones-y-autenticacion.md#csrf) | A0-12 |
| [DOM](A0-04-el-navegador-por-dentro.md#dom) | El árbol de objetos que el navegador arma a partir del HTML y que el código de la página puede leer y modificar. | A0-04 |
| [Dos aplicaciones, un backend](A-03-dos-apps-un-backend.md#dos-aplicaciones-un-backend) | La PWA para el socio y el personal, la app de escritorio para la PC del mostrador, y las dos contra la misma API, que es la única que decide. | A-03 |
| [Las dos banderas](A-10-bajas-logicas.md#las-dos-banderas) | `Usuario.activo` es poder entrar a la app; `Socio.activo`, ser socio del gimnasio. Están desacopladas a propósito, y la grilla avisa "Sin acceso a la app". | A-10 |
| [Los dos mecanismos de sesión y `X-Client-Type`](A-07-autenticacion.md#los-dos-mecanismos-de-sesión-y-x-client-type) | La PWA recibe el token en una cookie `httponly` con token CSRF y Flet lo recibe como token portador; `X-Client-Type` elige en el login, y en cada pedido el portador gana sobre la cookie. | A-07 |
| *Double submit cookie* | → [Token CSRF de doble envío](A0-12-sesiones-y-autenticacion.md#token-csrf-de-doble-envío) | A0-12 |
| [Duplicación deliberada](A-03-dos-apps-un-backend.md#duplicación-deliberada) | La paleta y la matriz de permisos viven copiadas en cada capa porque compartirlas exigiría un paso de compilación; lleva verificador la copia cuya falla no se ve. | A-03 |
| *`dvh`* | → [CSS utilitario y viewport móvil](A0-04-el-navegador-por-dentro.md#css-utilitario-y-viewport-móvil) | A0-04 |

## E

| Término | Qué es | Capítulo |
|---|---|---|
| [Efecto y arreglo de dependencias](A0-06-react.md#efecto-y-arreglo-de-dependencias) | Trabajo impuro —pedir datos, prender la cámara— que corre después del render y no durante, con la lista de valores que decide si vuelve a correr. | A0-06 |
| [Empaquetador y servidor de desarrollo](A0-05-javascript-y-typescript.md#empaquetador-y-servidor-de-desarrollo) | Vite: en desarrollo sirve los módulos de a uno y además reenvía pedidos a la API; para producción los junta en un paquete. | A0-05 |
| *En pausa* | → [Los seis estados del socio y su precedencia](A-09-estados-derivados.md#los-seis-estados-del-socio-y-su-precedencia) | A-09 |
| [Enrutado del lado del cliente](A0-06-react.md#enrutado-del-lado-del-cliente) | Cambiar de pantalla reescribiendo la URL y el árbol, sin pedirle al servidor un documento nuevo. | A0-06 |
| *Especialización* | → [Tabla subtipo (especialización)](A-05-modelo-de-datos.md#tabla-subtipo-especialización) | A-05 |
| [Esquema de entrada y salida, y el 422](A0-10-python-del-lado-del-servidor.md#esquema-de-entrada-y-salida-y-el-422) | La clase que declara qué se acepta y qué se devuelve, la validación que corre antes del endpoint, y el 422 que sale cuando el cuerpo no encaja. | A0-10 |
| [Estado derivado](A-09-estados-derivados.md#estado-derivado) | Un valor que se calcula en cada lectura en vez de guardarse, porque guardado se vuelve mentira al día siguiente sin que nadie escriba nada. | A-09 |
| [Estado guardado](A-09-estados-derivados.md#estado-guardado) | Lo que sí se persiste: nueve tablas llevan una columna `estado` con su enumerado, porque su valor es una decisión tomada y no un cálculo. | A-09 |
| *Event loop* | → [Bucle de eventos, tarea y microtarea, promesa y `async`/`await`](A0-04-el-navegador-por-dentro.md#bucle-de-eventos-tarea-y-microtarea-promesa-y-asyncawait) | A0-04 |
| *Extensión de largo (ataque)* | → [la idea ingenua, y por qué está rota](A0-11-criptografia-aplicada.md#la-idea-ingenua-y-por-qué-está-rota) | A0-11 |

## F

| Término | Qué es | Capítulo |
|---|---|---|
| *FastAPI* | → [ASGI, uvicorn y el router](A0-10-python-del-lado-del-servidor.md#asgi-uvicorn-y-el-router) | A0-10 |
| [`fetch`](A0-04-el-navegador-por-dentro.md#fetch) | La función que arma un pedido HTTP desde la página y devuelve una promesa que se resuelve al llegar las cabeceras; decide sola si adjunta las cookies. | A0-04 |
| *Flet* | → [Puente Python ↔ Flutter](A0-13-flutter-y-flet.md#puente-python--flutter) · [Control de Flet, `update()` y `page.overlay`](A0-13-flutter-y-flet.md#control-de-flet-update-y-pageoverlay) | A0-13 |
| [`flush` contra `commit`](A0-09-el-orm.md#flush-contra-commit) | Mandar a la base las escrituras pendientes sin confirmarlas, contra confirmarlas: lo primero todavía se puede revertir, lo segundo no. | A0-09 |
| [Fotograma y tensor](A0-14-vision-en-el-dispositivo.md#fotograma-y-tensor) | La imagen como matriz de píxeles, y el arreglo de números en punto flotante, con una forma declarada, con que la consume el modelo. | A0-14 |
| [Freno de intentos y respuesta indistinguible](A-07-autenticacion.md#freno-de-intentos-y-respuesta-indistinguible) | Cinco fallos traban la cuenta 15 minutos y veinte desde una IP en 10 minutos dan 429; trabada responde igual que una clave equivocada, a propósito. | A-07 |
| [El frontend esconde, el backend rechaza](A-08-autorizacion.md#el-frontend-esconde-el-backend-rechaza) | La copia de la matriz del frontend decide qué se dibuja; la del backend, qué se ejecuta. Esconder un botón es claridad, no seguridad. | A-08 |
| [Frontera de confianza del tipo](A0-05-javascript-y-typescript.md#frontera-de-confianza-del-tipo) | En el borde —la red, un archivo, lo que tipea alguien— un tipo es una declaración de intenciones y no una verificación; por eso lo que entra se valida en el servidor. | A0-05 |
| [Función hash criptográfica](A0-11-criptografia-aplicada.md#función-hash-criptográfica) | Convierte cualquier entrada en una huella de largo fijo: determinista, rápida e inviable de revertir o de hacer chocar. | A0-11 |

## G

| Término | Qué es | Capítulo |
|---|---|---|
| [GIL y concurrencia ≠ paralelismo](A0-10-python-del-lado-del-servidor.md#gil-y-concurrencia--paralelismo) | El candado que deja a un solo hilo ejecutando bytecode de Python a la vez, y la diferencia entre atender muchas cosas y hacerlas a la vez. | A0-10 |
| [Gráfico dibujado a mano](A-03-dos-apps-un-backend.md#gráfico-dibujado-a-mano) | Sin librería de gráficos en ninguna de las dos apps: cada barra es un rectángulo cuya altura sale de una transformación lineal del valor. | A-03 |

## H

| Término | Qué es | Capítulo |
|---|---|---|
| *Hash* | → [Función hash criptográfica](A0-11-criptografia-aplicada.md#función-hash-criptográfica) | A0-11 |
| [Hilo (y hilo demonio)](A0-01-como-corre-un-programa.md#hilo-y-hilo-demonio) | Una línea de ejecución dentro de un proceso, con su propia pila y la memoria compartida con los demás hilos; el demonio es el que no impide que el proceso termine. | A0-01 |
| [HMAC y firma simétrica](A0-11-criptografia-aplicada.md#hmac-y-firma-simétrica) | Hashear el mensaje junto con una clave secreta, en dos pasadas, de modo que sólo quien tiene la clave puede producir o verificar la marca. | A0-11 |
| *`HttpOnly`* | → [Cookie y sus atributos](A0-12-sesiones-y-autenticacion.md#cookie-y-sus-atributos) | A0-12 |

## I

| Término | Qué es | Capítulo |
|---|---|---|
| *Idempotencia* | → [Método HTTP e idempotencia](A0-03-http.md#método-http-e-idempotencia) | A0-03 |
| [Identidad firmada](A-07-autenticacion.md#identidad-firmada) | `id_socio` e `id_profesor` viajan firmados adentro del token: los endpoints de "mis cosas" no aceptan un id por parámetro, y nadie ve lo de otro cambiando un número. | A-07 |
| *IDOR* | → [Identidad firmada](A-07-autenticacion.md#identidad-firmada) | A-07 |
| [Índice B-tree](A0-08-sql-indices-y-planes.md#índice-b-tree) | El árbol balanceado que convierte una búsqueda lineal en logarítmica, al costo de mantenerlo en cada escritura. | A0-08 |
| [Índice único parcial](A0-08-sql-indices-y-planes.md#índice-único-parcial) | Un índice único que cubre sólo las filas que cumplen una condición: así la base garantiza "una sola ACTIVA por socio" sin tocar el historial. | A0-08 |
| [Inferencia en el dispositivo](A0-14-vision-en-el-dispositivo.md#inferencia-en-el-dispositivo) | Correr el modelo en el teléfono en vez de mandar el video a un servidor: cambia de golpe la latencia, el costo y la privacidad. | A0-14 |
| [Instrucción de máquina y compuerta lógica](A0-01-como-corre-un-programa.md#instrucción-de-máquina-y-compuerta-lógica) | La operación mínima que sabe hacer el procesador —sumar, copiar, comparar, saltar— y las compuertas que la ejecutan: el piso donde la abstracción toca el silicio, nombrado una sola vez. | A0-01 |
| [Intérprete, bytecode y compilación al vuelo](A0-01-como-corre-un-programa.md#intérprete-bytecode-y-compilación-al-vuelo) | Cómo un texto fuente termina siendo instrucciones: se traduce a un código intermedio que ejecuta un intérprete y que el motor, si le conviene, compila a instrucciones nativas. | A0-01 |
| [Inyección de dependencias](A0-10-python-del-lado-del-servidor.md#inyección-de-dependencias) | La función declara en su firma lo que necesita y el framework se lo construye antes de llamarla: ahí se enganchan la sesión de base y el chequeo de permisos. | A0-10 |

## J

| Término | Qué es | Capítulo |
|---|---|---|
| *JIT* | → [Intérprete, bytecode y compilación al vuelo](A0-01-como-corre-un-programa.md#intérprete-bytecode-y-compilación-al-vuelo) | A0-01 |
| [JSON como cuerpo](A0-03-http.md#json-como-cuerpo) | El formato de texto en que hablan las dos apps y el backend; se serializa al salir y se parsea al entrar, y en el camino se pierden los tipos. | A0-03 |
| [JWT](A0-12-sesiones-y-autenticacion.md#jwt) | Un token autocontenido de tres tramos, `cabecera.cuerpo.firma`: el servidor no guarda nada, verifica la firma y lee el contenido. | A0-12 |

## K

| Término | Qué es | Capítulo |
|---|---|---|
| *Kinetic Carbon* | → [Duplicación deliberada](A-03-dos-apps-un-backend.md#duplicación-deliberada) | A-03 |

## L

| Término | Qué es | Capítulo |
|---|---|---|
| *Landmark* | → [Punto clave (landmark)](A0-14-vision-en-el-dispositivo.md#punto-clave-landmark) | A0-14 |
| [Latido](A-11-rendimiento.md#latido) | Un `SELECT 1` cada dos minutos para que Neon no suspenda la base; de paso es el gancho del mantenimiento diario. | A-11 |
| [`lifespan`](A0-10-python-del-lado-del-servidor.md#lifespan) | El gancho de arranque y apagado de la aplicación: corre antes del primer pedido, y de ahí cuelgan los procesos que corren solos. | A0-10 |
| [Listado en lote](A-11-rendimiento.md#listado-en-lote) | Resolver todo lo que un listado necesita en un número fijo de consultas, en vez de una o varias por fila. | A-11 |
| [Log append-only](A-05-modelo-de-datos.md#log-append-only) | Las tablas `Registro_*`: se agrega una fila por hecho y ninguna de un día pasado se modifica, porque el historial es el dato. | A-05 |
| [Loopback contra IP de la LAN](A0-02-como-se-comunican-dos-maquinas.md#loopback-contra-ip-de-la-lan) | `127.0.0.1` nunca sale de la máquina; la IP de la LAN sí, y por eso el túnel público para probar en el celular tiene que apuntar a la segunda. | A0-02 |

## M

| Término | Qué es | Capítulo |
|---|---|---|
| *Mapa de identidad* | → [Sesión y mapa de identidad](A0-09-el-orm.md#sesión-y-mapa-de-identidad) | A0-09 |
| [Mapeo objeto-relacional y relación](A0-09-el-orm.md#mapeo-objeto-relacional-y-relación) | Una clase por tabla, un atributo por columna, y atributos de relación que convierten la clave foránea en un objeto. | A0-09 |
| [Máquina de estados con umbral](A0-14-vision-en-el-dispositivo.md#máquina-de-estados-con-umbral) | Contar una repetición es reconocer una secuencia de estados separados por dos umbrales con banda muerta, no comparar contra un número. | A0-14 |
| [Matriz de permisos](A-08-autorizacion.md#matriz-de-permisos) | La tabla rol × sección que es la única fuente sobre quién puede qué; los permisos que se muestran en pantalla se derivan de ella, nunca se escriben a mano. | A-08 |
| *MediaPipe* | → [Modelo entrenado e inferencia](A0-14-vision-en-el-dispositivo.md#modelo-entrenado-e-inferencia) | A0-14 |
| [Membresía vigente y qué significa "deber"](A-02-prepago-puro.md#membresía-vigente-y-qué-significa-deber) | Vigente es una `Membresia` `ACTIVA` cuyo período cubre el día de hoy; "deber" es no tenerla: una ausencia, no un saldo. | A-02 |
| *Mercado Pago* | → [Método de pago](A-02-prepago-puro.md#método-de-pago) · [Sin renovación automática](A-02-prepago-puro.md#sin-renovación-automática) | A-02 |
| [Método de pago](A-02-prepago-puro.md#método-de-pago) | Cómo paga la persona, no qué empresa procesa el pago: `BILLETERA_VIRTUAL` y `TRANSFERENCIA` son distintos porque se concilian en lugares distintos. | A-02 |
| [Método HTTP e idempotencia](A0-03-http.md#método-http-e-idempotencia) | `GET`, `POST`, `PUT` y `DELETE` como declaración de intención; idempotente es la operación que, repetida, deja el mismo estado que hecha una vez. | A0-03 |
| [Middleware](A0-10-python-del-lado-del-servidor.md#middleware) | Código que envuelve a todos los pedidos; el orden en que se registra y el orden en que corre no son el mismo. | A0-10 |
| [Modelo entrenado e inferencia](A0-14-vision-en-el-dispositivo.md#modelo-entrenado-e-inferencia) | El archivo de pesos, y el acto de pasarle una entrada y leer la salida; entrenar e inferir son dos cosas distintas, y acá sólo pasa la segunda. | A0-14 |
| [El mostrador con cola](A-01-que-es-olimpos.md#el-mostrador-con-cola) | La restricción de diseño que explica la mitad del sistema: la única persona con gente esperando es la que más veces toca la pantalla, así que cada paso y cada pregunta se pagan multiplicados. | A-01 |
| [Motor de JavaScript](A0-05-javascript-y-typescript.md#motor-de-javascript) | Lo que ejecuta el código en el navegador: parsea el fuente, lo pasa a bytecode y compila al vuelo las partes que más se usan. | A0-05 |
| [Motor de render y canvas](A0-04-el-navegador-por-dentro.md#motor-de-render-y-canvas) | La cadena que convierte el árbol y los estilos en cajas, capas y píxeles; el canvas es la superficie donde se dibuja a mano, sin nodos. | A0-04 |

## N

| Término | Qué es | Capítulo |
|---|---|---|
| [N+1](A0-09-el-orm.md#n1) | Una consulta para la lista y una más por cada elemento: el costo de la carga perezosa dentro de un bucle. | A0-09 |
| *Nada muerto en pantalla* | → [nada muerto en pantalla](A-01-que-es-olimpos.md#nada-muerto-en-pantalla) | A-01 |
| *Neon* | → [Base remota](A-11-rendimiento.md#base-remota) | A-11 |
| [No existe "Registrarse"](A-07-autenticacion.md#no-existe-registrarse) | Ninguna ruta crea una cuenta a pedido de quien la va a usar: la cuenta nace del alta que hace el personal, ni siquiera pagando. | A-07 |
| [Normalización (3FN)](A0-07-bases-de-datos-relacionales.md#normalización-3fn) | Guardar cada hecho una sola vez; un dato que parece repetido no la viola si registra dos hechos distintos. | A0-07 |

## O

| Término | Qué es | Capítulo |
|---|---|---|
| [OlimpOS](A-01-que-es-olimpos.md#olimpos) | El sistema de gestión de un gimnasio de una sola sede: dos aplicaciones contra un único backend, pensado para correr en servidores locales. | A-01 |
| [Omitir en vez de deshabilitar](A-08-autorizacion.md#omitir-en-vez-de-deshabilitar) | Un control prohibido no se dibuja, en vez de mostrarse gris: un botón gris ya delata que hay algo cargado. | A-08 |
| [Origen y política del mismo origen](A0-04-el-navegador-por-dentro.md#origen-y-política-del-mismo-origen) | La tripla esquema, host y puerto que define un sitio, y la regla que impide que el código de un origen lea lo de otro. | A0-04 |

## P

| Término | Qué es | Capítulo |
|---|---|---|
| [Página de 8 KB](A0-08-sql-indices-y-planes.md#página-de-8-kb) | La unidad física de lectura y escritura de Postgres: no se lee una fila, se lee la página de 8192 bytes que la contiene. | A0-08 |
| [Paquete, dirección IP y DNS](A0-02-como-se-comunican-dos-maquinas.md#paquete-dirección-ip-y-dns) | La unidad que viaja por la red, con su dirección de origen y de destino en la cabecera; el DNS es el paso previo que convierte un nombre en esa dirección. | A0-02 |
| [Pedido y respuesta HTTP](A0-03-http.md#pedido-y-respuesta-http) | Dos bloques de texto plano —línea inicial, cabeceras, línea en blanco, cuerpo— que viajan por una conexión TCP. | A0-03 |
| [Plan de consulta y planificador](A0-08-sql-indices-y-planes.md#plan-de-consulta-y-planificador) | El árbol de pasos que la base elige para responder una consulta, comparando costos estimados; el escaneo secuencial no siempre es el camino malo. | A0-08 |
| [Pool de conexiones](A-11-rendimiento.md#pool-de-conexiones) | Conexiones abiertas una vez y prestadas a cada pedido, recicladas antes de que el proveedor las corte, con verificación previa y `keepalives` de TCP para que ninguna llegue muerta. | A-11 |
| [`precio_pactado` contra `precio_actual`](A-02-prepago-puro.md#precio_pactado-contra-precio_actual) | Lo que costó un período cuando se vendió y lo que cuesta el plan hoy son dos hechos distintos: guardarlos por separado no viola la 3FN. | A-02 |
| [Prepago puro](A-02-prepago-puro.md#prepago-puro) | El gimnasio cobra antes de dar el servicio: no hay tabla `Deuda` porque no hay deuda que registrar. | A-02 |
| [Proceso automático](A-12-como-leer-los-procesos.md#proceso-automático) | Los seis procesos que no cuelgan de ninguna ruta: los dispara el arranque del backend, un temporizador o un proceso aparte. | A-12 |
| [Proceso y espacio de direcciones](A0-01-como-corre-un-programa.md#proceso-y-espacio-de-direcciones) | Un programa cargado en memoria con su propio mapa de direcciones, su pila y su montón; el sistema operativo no deja que un proceso lea la memoria de otro. | A0-01 |
| *Promesa* | → [Bucle de eventos, tarea y microtarea, promesa y `async`/`await`](A0-04-el-navegador-por-dentro.md#bucle-de-eventos-tarea-y-microtarea-promesa-y-asyncawait) | A0-04 |
| [Promoción porcentual](A-02-prepago-puro.md#promoción-porcentual) | El único descuento del sistema, guardado en el `Pago`; tiene que estar vigente el día que arranca el período cobrado, no el día que se cobra. | A-02 |
| [Props, estado local y re-render](A0-06-react.md#props-estado-local-y-re-render) | Los datos que bajan del padre, lo que el componente recuerda entre una llamada y la siguiente, y la regla de que cambiar el estado vuelve a ejecutar la función. | A0-06 |
| [Proxy `/api` de Vite](A-04-recorrido-de-un-pedido.md#proxy-api-de-vite) | La escala que en desarrollo hace que la página y la API sean el mismo sitio, que es lo que exige `SameSite=lax` para que la cookie viaje. | A-04 |
| [Proxy inverso](A0-03-http.md#proxy-inverso) | Un servidor que recibe el pedido como si fuera el destino y lo reenvía a otro bajo su propio nombre, así que para el navegador los dos son el mismo sitio. | A0-03 |
| [Puente Python ↔ Flutter](A0-13-flutter-y-flet.md#puente-python--flutter) | Flet son dos programas —un cliente de Flutter ya compilado y el proceso de Python con la app— que se hablan por un canal de mensajes. | A0-13 |
| [Puerto](A0-02-como-se-comunican-dos-maquinas.md#puerto) | El número de 16 bits que reparte entre varios procesos los paquetes que llegan a una misma IP; dos no pueden escuchar el mismo, y el segundo muere. | A0-02 |
| [Punto clave (landmark)](A0-14-vision-en-el-dispositivo.md#punto-clave-landmark) | Cada uno de los 33 puntos de pose que devuelve el modelo, siempre con el mismo índice para la misma articulación. | A0-14 |
| *PWA* | → [las tres piezas, nombradas](A-01-que-es-olimpos.md#las-tres-piezas-nombradas) · [Dos aplicaciones, un backend](A-03-dos-apps-un-backend.md#dos-aplicaciones-un-backend) | A-01, A-03 |
| *Pydantic* | → [Esquema de entrada y salida, y el 422](A0-10-python-del-lado-del-servidor.md#esquema-de-entrada-y-salida-y-el-422) | A0-10 |

## R

| Término | Qué es | Capítulo |
|---|---|---|
| [Recepción (panel del mostrador)](A-03-dos-apps-un-backend.md#recepción-panel-del-mostrador) | La pantalla que resuelve el mostrador sin buscar nada; hoy existe sólo en Flet, con el backend ya entero, y está pendiente en la PWA. | A-03 |
| [Regla resuelta en el backend](A-09-estados-derivados.md#regla-resuelta-en-el-backend) | Las pantallas reciben la decisión ya tomada y su motivo en vez de recalcular la regla, así que ninguna ofrece un botón que la API va a rechazar. | A-09 |
| [Restricción y tipo enumerado](A0-07-bases-de-datos-relacionales.md#restricción-y-tipo-enumerado) | `NOT NULL`, `UNIQUE`, `CHECK` y los `ENUM` de Postgres: reglas que la base hace cumplir en cada escritura, aunque el código se equivoque. | A0-07 |
| *RFID* | → [muerto en pantalla no es muerto en el código](A-01-que-es-olimpos.md#muerto-en-pantalla-no-es-muerto-en-el-código) | A-01 |
| [Rol de sesión y los seis roles](A-06-los-seis-roles.md#rol-de-sesión-y-los-seis-roles) | `dueno`, `recepcionista`, `entrenador`, `nutricionista`, `profesor` y `socio`: las etiquetas que viajan en el token y contra las que se evalúan los permisos. | A-06 |
| *Rollback* | → [Transacción, ACID, commit y rollback](A0-07-bases-de-datos-relacionales.md#transacción-acid-commit-y-rollback) | A0-07 |

## S

| Término | Qué es | Capítulo |
|---|---|---|
| [Sal y hash lento](A0-11-criptografia-aplicada.md#sal-y-hash-lento) | Un valor único por contraseña que inutiliza las tablas precalculadas, y un algoritmo caro a propósito que vuelve inviable probar de a millones. | A0-11 |
| *`SameSite`* | → [Cookie y sus atributos](A0-12-sesiones-y-autenticacion.md#cookie-y-sus-atributos) | A0-12 |
| [Sección con nivel y acción suelta](A-08-autorizacion.md#sección-con-nivel-y-acción-suelta) | Cada sección tiene nivel `NINGUNO`, `LECTURA` o `TOTAL` —hacen falta los tres—, y aparte hay acciones puntuales que se chequean por separado. | A-08 |
| [Los seis estados del socio y su precedencia](A-09-estados-derivados.md#los-seis-estados-del-socio-y-su-precedencia) | Dado de baja > Sin membresía > Suspendido > Vencido > Por vencer (0 a 7 días) > Activo, en ese orden; el portal dice "En pausa" donde la grilla dice "Suspendido". | A-09 |
| *`selectinload`* | → [Carga perezosa contra carga ansiosa](A0-09-el-orm.md#carga-perezosa-contra-carga-ansiosa) | A0-09 |
| [Service del frontend](A-04-recorrido-de-un-pedido.md#service-del-frontend) | La capa que traduce una intención de pantalla en un pedido HTTP y la respuesta en datos de vista; ninguna pantalla llama a la red por su cuenta. | A-04 |
| [Service worker](A0-04-el-navegador-por-dentro.md#service-worker) | Un programa que corre en el navegador en un hilo aparte, sobrevive a la pestaña e intercepta cada `fetch` del sitio: lo que hace instalable a la PWA. | A0-04 |
| [Servir y refrescar](A-11-rendimiento.md#servir-y-refrescar) | El cliente de Flet devuelve al instante lo que tiene guardado, aunque esté vencido, y refresca por detrás; cualquier escritura y el cierre de sesión tiran el caché entero. | A-11 |
| [Sesión](A0-12-sesiones-y-autenticacion.md#sesión) | La memoria que HTTP no tiene, reconstruida en cada pedido a partir de una prueba que el cliente adjunta. | A0-12 |
| [Sesión y mapa de identidad](A0-09-el-orm.md#sesión-y-mapa-de-identidad) | La unidad de trabajo del ORM: acumula los cambios, los traduce al final en el SQL mínimo y garantiza que una fila sea un solo objeto mientras dure. | A0-09 |
| [SHA-256](A0-11-criptografia-aplicada.md#sha-256) | El algoritmo concreto: bloques de 512 bits encadenados y 64 rondas de XOR, rotaciones y sumas sobre cada uno, bajado hasta la compuerta. | A0-11 |
| [Sin cobros por adelantado](A-02-prepago-puro.md#sin-cobros-por-adelantado) | Con un período en curso no se cobra otro, en ningún canal, porque quien paga meses adelantados congela el precio; `Pago.es_adelanto` queda siempre en false. | A-02 |
| [Sin estado (stateless)](A0-03-http.md#sin-estado-stateless) | HTTP no recuerda nada entre un pedido y el siguiente: la propiedad que lo hizo escalar y el problema del que nacen la cookie y el token. | A0-03 |
| [Sin renovación automática](A-02-prepago-puro.md#sin-renovación-automática) | Cada período se cobra a mano o con un checkout de pago único, nunca con una suscripción; si el socio no paga, la cuota vence y ahí termina. | A-02 |
| [El sistema informa, no juzga](A-01-que-es-olimpos.md#el-sistema-informa-no-juzga) | Ante un caso irregular el sistema avisa y deja seguir, porque decide quien tiene la información; su par es "nada muerto en pantalla": lo que no funciona hoy, se saca. | A-01 |
| *Soft delete* | → [Baja lógica (soft delete)](A-10-bajas-logicas.md#baja-lógica-soft-delete) | A-10 |
| [SQL, JOIN y agregación](A0-08-sql-indices-y-planes.md#sql-join-y-agregación) | El lenguaje declarativo con que se pide qué filas, cruzadas con cuáles y resumidas cómo (`COUNT`, `SUM`, `GROUP BY`), dejándole el cómo a la base. | A0-08 |
| *SQLAlchemy* | → [Mapeo objeto-relacional y relación](A0-09-el-orm.md#mapeo-objeto-relacional-y-relación) | A0-09 |
| [Store global fuera de React](A0-06-react.md#store-global-fuera-de-react) | Estado compartido que vive afuera del árbol y avisa a los componentes suscritos; en la PWA, `authStore` y `uiStore`. | A0-06 |
| *Suspendido* | → [Los seis estados del socio y su precedencia](A-09-estados-derivados.md#los-seis-estados-del-socio-y-su-precedencia) | A-09 |

## T

| Término | Qué es | Capítulo |
|---|---|---|
| [Tabla subtipo (especialización)](A-05-modelo-de-datos.md#tabla-subtipo-especialización) | Qué es una persona se modela con la existencia de una fila en una tabla hija —`Socio`, `Empleado`, `Entrenador`…—, no con una columna `rol`. | A-05 |
| [Tabla, fila, columna y cardinalidad](A0-07-bases-de-datos-relacionales.md#tabla-fila-columna-y-cardinalidad) | Filas sin orden con la misma forma, y las relaciones entre tablas: 1:N con una clave foránea del lado N, N:M con una tabla puente. | A0-07 |
| *Tailwind* | → [CSS utilitario y viewport móvil](A0-04-el-navegador-por-dentro.md#css-utilitario-y-viewport-móvil) | A0-04 |
| [TCP y el viaje de ida y vuelta (RTT)](A0-02-como-se-comunican-dos-maquinas.md#tcp-y-el-viaje-de-ida-y-vuelta-rtt) | El protocolo que garantiza orden y entrega con acuses y retransmisiones, y su costo en tiempo: un RTT es lo que tarda un paquete en ir y volver. | A0-02 |
| *TDZ* | → [Zona muerta temporal (TDZ)](A0-05-javascript-y-typescript.md#zona-muerta-temporal-tdz) | A0-05 |
| [Tipado estático y borrado de tipos](A0-05-javascript-y-typescript.md#tipado-estático-y-borrado-de-tipos) | TypeScript chequea los tipos antes de correr y después los borra: en tiempo de ejecución no queda ni un byte de ellos. | A0-05 |
| [Tipo de baja y el acople de la cuenta](A-10-bajas-logicas.md#tipo-de-baja-y-el-acople-de-la-cuenta) | `VOLUNTARIA` deja viva la cuenta de acceso; `MORA` y `ADMINISTRATIVA` la apagan. Reactivar al socio la devuelve. | A-10 |
| [TLS](A0-02-como-se-comunican-dos-maquinas.md#tls) | El canal cifrado que se monta entre TCP y HTTP, con su propio saludo previo, que suma viajes de ida y vuelta antes del primer byte útil. | A0-02 |
| [Token CSRF de doble envío](A0-12-sesiones-y-autenticacion.md#token-csrf-de-doble-envío) | La defensa: un valor que viaja a la vez en una cookie y en una cabecera, porque el atacante puede hacer que la cookie se mande pero no puede leerla. | A0-12 |
| [Token portador y `Authorization`](A0-12-sesiones-y-autenticacion.md#token-portador-y-authorization) | La sesión que el cliente pone a mano en cada pedido, en `Authorization: Bearer …`, en vez de dejar que el navegador la adjunte solo. | A0-12 |
| [Transacción, ACID, commit y rollback](A0-07-bases-de-datos-relacionales.md#transacción-acid-commit-y-rollback) | Un grupo de escrituras que ocurre entero o no ocurre, y qué garantiza confirmarlo; incluye por qué un `rollback()` de afuera no deshace un `commit()` de adentro. | A0-07 |
| [Las tres copias y su verificador](A-08-autorizacion.md#las-tres-copias-y-su-verificador) | La matriz vive en el backend, la PWA y Flet; como un permiso mal copiado no se ve, `backend/check_permisos.py` compara las tres. | A-08 |

## U

| Término | Qué es | Capítulo |
|---|---|---|
| *Unidad de trabajo* | → [Sesión y mapa de identidad](A0-09-el-orm.md#sesión-y-mapa-de-identidad) | A0-09 |
| *Uvicorn* | → [ASGI, uvicorn y el router](A0-10-python-del-lado-del-servidor.md#asgi-uvicorn-y-el-router) | A0-10 |

## V

| Término | Qué es | Capítulo |
|---|---|---|
| *V-08* | → [Caducidad y revocación](A0-12-sesiones-y-autenticacion.md#caducidad-y-revocación) | A0-12 |
| *V-10* | → [V-10: el Entrenador y el Nutricionista ven a todos los socios](B-02-socios.md#v-10-el-entrenador-y-el-nutricionista-ven-a-todos-los-socios) | B-02 |
| *V-11* | → [su costo: V-11](A-07-autenticacion.md#por-qué-está-hecho-así-y-su-costo-v-11) | A-07 |
| [Variable de entorno y archivo `.env`](A0-01-como-corre-un-programa.md#variable-de-entorno-y-archivo-env) | Pares nombre-valor que un proceso hereda al arrancar; el `.env` es un archivo de texto que alguien carga en ese entorno, no un mecanismo del sistema operativo. | A0-01 |
| [Vencido el día siguiente](A-09-estados-derivados.md#vencido-el-día-siguiente) | El socio queda vencido el día después de la fecha de vencimiento, no ese mismo día. | A-09 |
| *Vite* | → [Empaquetador y servidor de desarrollo](A0-05-javascript-y-typescript.md#empaquetador-y-servidor-de-desarrollo) | A0-05 |

## W

| Término | Qué es | Capítulo |
|---|---|---|
| [Widget y árbol de widgets](A0-13-flutter-y-flet.md#widget-y-árbol-de-widgets) | La descripción inmutable de un pedazo de pantalla en Flutter, y el árbol que la compone: la idea de React, fuera del navegador. | A0-13 |

## X

| Término | Qué es | Capítulo |
|---|---|---|
| *`X-Client-Type`* | → [Los dos mecanismos de sesión y `X-Client-Type`](A-07-autenticacion.md#los-dos-mecanismos-de-sesión-y-x-client-type) | A-07 |

## Z

| Término | Qué es | Capítulo |
|---|---|---|
| [Zona muerta temporal (TDZ)](A0-05-javascript-y-typescript.md#zona-muerta-temporal-tdz) | El tramo entre que un `let` o un `const` entra en alcance y se inicializa: leerlo ahí compila y lanza una excepción al correr. | A0-05 |

---

## Patrones con nombre

Un patrón no es un concepto de este sistema: es una jugada de diseño conocida, con nombre, que los
capítulos identifican al hacer ingeniería inversa del código. Ponerle el nombre es lo que permite
reconocerla la próxima vez, en este repo o en otro. La última columna lleva a donde cada uno se ve
aplicado, y los que tienen más de un enlace son los que más enseñan: *fallar cerrado* aparece en la
base, en la sesión y en el contador de repeticiones; *derivar en vez de almacenar*, en la plata, en
los estados y en los índices. *Fallar abierto* aparece una sola vez, y a propósito: es la puerta del
gimnasio.

| Patrón | La jugada | Dónde se ve |
|---|---|---|
| **Atar el servicio a la interfaz más chica que alcance** | Escuchar sólo en la interfaz que el uso necesita: el backend atiende en `127.0.0.1` y no en la red. | [A0-02](A0-02-como-se-comunican-dos-maquinas.md#por-qué-el-backend-está-atado-a-127001-y-qué-se-paga-por-eso) |
| **Backend for frontend (un endpoint por pantalla)** | El endpoint devuelve junto todo lo que una pantalla muestra, en vez de obligarla a juntarlo de varios endpoints por entidad. | [A-01](A-01-que-es-olimpos.md#menos-pasos-y-más-completo) |
| **Caché firmado** | Guardar en el token un valor derivado para no recalcularlo, firmado para que el cliente que lo lleva no lo pueda alterar. | [A-06](A-06-los-seis-roles.md#derivación-de-roles) |
| **Capa anticorrupción** | Adentro del service vive el vocabulario de la API y afuera el de la pantalla; ninguno se filtra al otro. | [A-04](A-04-recorrido-de-un-pedido.md#service-del-frontend) |
| **Clave de idempotencia** | El cliente manda un identificador del intento y el servidor lo usa para reconocer el pedido repetido. | [A0-03](A0-03-http.md#método-http-e-idempotencia) |
| **Colapsar el origen** | En vez de negociar permisos entre dos sitios, hacer que sean uno. | [A-04](A-04-recorrido-de-un-pedido.md#proxy-api-de-vite) |
| **Configuración de solución con referencias de proyecto** | Un `tsconfig` raíz que sólo indexa proyectos y no compila nada: por eso `tsc` se corre con `-p`. | [A0-05](A0-05-javascript-y-typescript.md#el-chequeo-que-siempre-da-ok-por-qué-tsc-va-con--p-tsconfigappjson) |
| **Confirmar sólo lo que no se deshace** | La pregunta se pone antes de una escritura que no tiene vuelta atrás, como un cobro, y en ningún otro lado. | [A-04](A-04-recorrido-de-un-pedido.md#el-diálogo-y-por-qué-confirmar-acá-no-es-una-molestia) |
| **Decidir en el servidor, mostrar en el cliente** | El backend manda la decisión junto con su motivo (`puede_renovar`) y la pantalla sólo la muestra. | [A-04](A-04-recorrido-de-un-pedido.md#escala-16--la-regla-de-negocio) · [A-09](A-09-estados-derivados.md#regla-resuelta-en-el-backend) |
| **Defensa en profundidad** | Dos defensas independientes contra el mismo ataque, para que la caída de una no alcance: `SameSite` y el token de doble envío. | [A0-12](A0-12-sesiones-y-autenticacion.md#los-dos-mecanismos-de-este-sistema-y-por-qué-son-dos) |
| **Derivar en vez de almacenar** | Calcular en cada lectura lo que, guardado, se volvería falso con el paso del tiempo. | [A-09](A-09-estados-derivados.md#estado-derivado) · [A-02](A-02-prepago-puro.md#prepago-puro) · [A0-08](A0-08-sql-indices-y-planes.md#por-qué-está-hecho-así) |
| **Deshacer en vez de confirmar** | Dejar hacer y ofrecer volver atrás, en vez de preguntar antes a alguien que no va a leer la pregunta. | [A-01](A-01-que-es-olimpos.md#el-cartel-que-nadie-lee) |
| **Diseñar para la latencia** | Contar viajes de ida y vuelta antes que cálculo; el error que evita es la falacia de la latencia cero. | [A-11](A-11-rendimiento.md#base-remota) |
| **Fallar abierto** | Ante la duda, dejar pasar y registrar el hecho: es la regla de la puerta del gimnasio. | [A-01](A-01-que-es-olimpos.md#el-sistema-informa-no-juzga) |
| **Fallar cerrado** | Ante la duda, rechazar: la base al borrar un padre con hijos, el CSRF sin su token, el arranque sin clave, el contador que no reconoce el movimiento. | [A0-07](A0-07-bases-de-datos-relacionales.md#clave-foránea-y-acción-referencial) · [A0-12](A0-12-sesiones-y-autenticacion.md#los-dos-mecanismos-de-este-sistema-y-por-qué-son-dos) · [A-04](A-04-recorrido-de-un-pedido.md#escala-8--el-middleware-de-csrf) · [A0-14](A0-14-vision-en-el-dispositivo.md#por-qué-está-hecho-así) |
| **Frontera de confianza** | Lo que llega del otro lado es información, no garantía: ninguna decisión de seguridad puede depender sólo de eso. | [A0-05](A0-05-javascript-y-typescript.md#frontera-de-confianza-del-tipo) · [A-07](A-07-autenticacion.md#por-qué-está-hecho-así-y-su-costo-v-11) |
| **Histéresis (disparador de Schmitt)** | Dos umbrales con una banda muerta entre ellos, para que una señal que tiembla no cruce la línea de más. | [A0-14](A0-14-vision-en-el-dispositivo.md#máquina-de-estados-con-umbral) |
| **Implementación de referencia** | Una implementación manda y la otra se corrige para parecerse; si difieren, no se discute cuál tiene razón. | [A-03](A-03-dos-apps-un-backend.md#aplicación-gemela-y-componente-gemelo) |
| **Invariante** | Una propiedad que el sistema garantiza siempre: un solo período en curso por socio, y que contiene hoy. | [A-02](A-02-prepago-puro.md#sin-cobros-por-adelantado) |
| **Inversión de control** | La función declara lo que necesita y el framework lo construye y se lo pasa. | [A0-10](A0-10-python-del-lado-del-servidor.md#inyección-de-dependencias) |
| **Mapeador de datos** | Una capa que traduce entre objetos y filas para que ni unos ni otras sepan de la otra forma; uno de los patrones de Fowler que implementa SQLAlchemy. | [A0-09](A0-09-el-orm.md#mapeo-objeto-relacional-y-relación) |
| **Mover el trabajo al borde** | Calcular donde está el dato cuando el dato es grande y el resultado chico: 30 cuadros por segundo contra cuatro números. | [A0-04](A0-04-el-navegador-por-dentro.md#por-qué-el-contador-de-repeticiones-corre-acá-y-no-en-el-backend) · [A0-14](A0-14-vision-en-el-dispositivo.md#inferencia-en-el-dispositivo) |
| **Poner la restricción en la capa más baja que pueda sostenerla** | Si la base puede garantizar una regla, la garantiza la base, porque es la única capa por la que pasan todos los caminos. | [A0-08](A0-08-sql-indices-y-planes.md#por-qué-está-hecho-así) |
| **Pooling (agrupamiento de recursos)** | Pagar una vez algo caro y reusarlo: las conexiones en el pool, las respuestas en el caché de Flet. | [A-11](A-11-rendimiento.md#pool-de-conexiones) |
| **Presupuesto de recursos** | Cada tope elegido y escrito —hilos, conexiones, segundos de espera—, no dejado en el valor de fábrica. | [A0-10](A0-10-python-del-lado-del-servidor.md#por-qué-está-hecho-así) |
| **Principio de Kerckhoffs** | Un sistema tiene que seguir siendo seguro aunque el atacante conozca todo menos la clave. | [A0-11](A0-11-criptografia-aplicada.md#clave-secreta) |
| **Renderizado declarativo con representación intermedia barata** | Describir la pantalla entera para cada estado y comparar una copia liviana en vez de tocar la estructura cara. | [A0-06](A0-06-react.md#por-qué-está-hecho-así) |
| **Seguro por omisión** | La protección ya está puesta sin que nadie tenga que acordarse de ponerla: el CSRF es un middleware y no una dependencia. | [A0-12](A0-12-sesiones-y-autenticacion.md#los-dos-mecanismos-de-este-sistema-y-por-qué-son-dos) |
| **Stale-while-revalidate e invalidación por generación** | Servir lo guardado aunque esté vencido mientras se refresca por detrás, y descartar el refresco que llega tarde. | [A-11](A-11-rendimiento.md#servir-y-refrescar) |
| **Validar dos veces, decidir una** | La interfaz ayuda a no equivocarse y la capa de abajo decide; el orden importa. | [A0-07](A0-07-bases-de-datos-relacionales.md#restricción-y-tipo-enumerado) |
| **Verificar la identidad de quien responde** | No alcanza con que alguien conteste: hay que saber que contestó el proceso nuevo, y por eso se cuentan las rutas publicadas. | [A0-02](A0-02-como-se-comunican-dos-maquinas.md#por-qué-el-puerto-8000-ocupado-hace-que-el-proceso-nuevo-muera-en-silencio) |
| **YAGNI** | No construir lo que todavía no hace falta; acá se aplica a la pantalla y no al backend, donde una pieza con fecha puede esperar. | [A-01](A-01-que-es-olimpos.md#nada-muerto-en-pantalla) |

---

## Cómo se mantiene

- **Un concepto entra acá sólo si ya tiene dueño**: un encabezado propio en su capítulo, cuyo texto
  es exactamente el nombre de la primera columna. De ese texto sale el ancla del enlace, así que
  renombrar el encabezado obliga a corregir la fila.
- **La línea sigue al capítulo, no al revés.** Si el capítulo cambia lo que dice, se corrige la
  línea; si la línea dice algo que el capítulo no, sobra la línea.
- **Una remisión no define nada.** Si hace falta explicar algo para que la remisión se entienda, lo
  que falta es un concepto con su lugar propio, no una remisión más larga.
