# Masterclass de OlimpOS

*Índice. Desde acá se llega a los 52 archivos, y la tabla de ruteo dice cuáles podés saltear.*

Esta masterclass explica el código de OlimpOS al nivel de un curso de posgrado, para alguien que
nunca vio el repo. Tiene dos objetivos, y pesan igual: que el lector entienda el sistema hasta el
fondo, sin quedarse con ninguna pregunta del tipo "¿y eso cómo funciona por dentro?", y que después
pueda encontrar cualquier línea de código que implemente cualquier cosa.

| Parte | Qué es | Se organiza por | Estado |
|---|---|---|---|
| **A0 · Cimientos** | Cada tecnología del stack, desde el problema que resolvió hasta el piso donde bajar un escalón más ya no explica nada de este sistema. | Temas, de abajo hacia arriba | escrita |
| **A · El sistema** | Cómo esas piezas forman OlimpOS, y por qué así. | Temas, en orden constructivo | escrita, con [glosario](A-98-glosario.md) y [mapa de conexiones](A-99-mapa-de-conexiones.md) |
| **B · Los 173 procesos** | Cada proceso de `PROCESOS-LOGICOS-REQUERIDOS.md`, con archivo y rango de líneas en las tres capas. | Las 15 secciones de ese archivo | en curso: [B-01](B-01-acceso-y-sesion.md) a [B-05](B-05-cobros-y-pagos.md) escritos |
| **C · Lo que no es un proceso** | El código que no cuelga de ningún endpoint. | Subsistemas | sin escribir |

---

## Por dónde empezar

Tres recorridos, según lo que busques:

- **Nunca viste el repo.** Empezá por [A-01](A-01-que-es-olimpos.md), que no habla de software sino
  del gimnasio, y seguí la Parte A en orden. Cuando un término técnico te frene, el enlace te baja al
  capítulo de A0 que lo explica; la tabla de ruteo de abajo te dice cuáles podés saltear de antemano.
  [A-04](A-04-recorrido-de-un-pedido.md) es el capítulo bisagra: sigue un cobro desde el click hasta
  la base y de vuelta, y todo proceso de la Parte B es una variación de ese recorrido.
- **Buscás dónde está el código de algo.** Buscá el proceso en `PROCESOS-LOGICOS-REQUERIDOS.md`, en
  la raíz del repo, y andá al capítulo de la Parte B de su sección: cada proceso tiene su tabla de
  archivos, líneas y símbolos. Lo que no es un proceso está en la Parte C. Mientras B y C no estén
  escritas, [A-04](A-04-recorrido-de-un-pedido.md) tiene un recorrido completo con archivo y línea
  en cada escala, y [A-12](A-12-como-leer-los-procesos.md) enseña a leer el archivo de procesos.
- **Querés entender por qué algo es como es.** El [mapa de conexiones](A-99-mapa-de-conexiones.md)
  muestra cómo se tocan los conceptos, y su tabla de contradicciones dice qué decisión ganó en cada
  compromiso. El [glosario](A-98-glosario.md) ubica cualquier término por su nombre y reúne los
  patrones de diseño con nombre.

---

## La Parte A0 sin leerla entera

Si podés responder la pregunta de una fila, salteá ese capítulo. Si dudás, leé su primera sección:
cada uno arranca por el problema que resolvió, y en dos párrafos te das cuenta de si ya lo sabés. El
lector decide; el documento no decide por él.

| Capítulo | Salteátelo si podés responder esto |
|---|---|
| [A0-01 · Qué pasa cuando corre un programa](A0-01-como-corre-un-programa.md) | ¿Qué comparten dos hilos de un mismo proceso que dos procesos no, qué ejecuta de verdad el procesador cuando corre Python, y por qué un `.env` no es un mecanismo del sistema operativo? |
| [A0-02 · Cómo se comunican dos máquinas](A0-02-como-se-comunican-dos-maquinas.md) | ¿Por qué un servidor que atiende en `127.0.0.1` no se ve desde el celular, qué le pasa al segundo proceso que quiere el mismo puerto, y cuántos viajes de ida y vuelta cuesta abrir una conexión con TLS? |
| [A0-03 · HTTP](A0-03-http.md) | ¿Podés escribir a mano, línea por línea, un `POST` con sus cabeceras y su cuerpo JSON, y explicar por qué HTTP no recuerda quién sos entre un pedido y el siguiente? |
| [A0-04 · El navegador por dentro](A0-04-el-navegador-por-dentro.md) | ¿Qué corre en el único hilo de una página y en qué orden se vacían tareas y microtareas, qué intercepta un service worker, y por qué `100dvh` y `100vh` no miden lo mismo en un iPhone? |
| [A0-05 · JavaScript y TypeScript](A0-05-javascript-y-typescript.md) | ¿Qué queda de un tipo de TypeScript cuando el código corre, por qué un tipo no te protege de lo que llega por la red, y por qué leer una `const` antes de su línea compila y revienta? |
| [A0-06 · React](A0-06-react.md) | ¿Qué dispara un re-render, qué compara la reconciliación, para qué sirve la `key` de una lista, y en qué momento exacto corre un `useEffect`? |
| [A0-07 · Bases de datos relacionales](A0-07-bases-de-datos-relacionales.md) | ¿Qué garantiza exactamente un `commit`, por qué un `rollback()` de afuera no deshace el `commit()` de adentro, y qué anomalías evita la tercera forma normal? |
| [A0-08 · SQL, índices y planes de consulta](A0-08-sql-indices-y-planes.md) | ¿Por qué Postgres lee páginas y no filas, cuántas comparaciones ahorra un índice B-tree sobre cincuenta mil filas, y cómo garantiza un índice parcial "una sola activa por socio"? |
| [A0-09 · El ORM](A0-09-el-orm.md) | ¿Podés contar, consulta por consulta, lo que emite un bucle que toca una relación con carga perezosa, y decir qué diferencia a `flush` de `commit`? |
| [A0-10 · Python del lado del servidor](A0-10-python-del-lado-del-servidor.md) | ¿Por qué en este backend esperar la red no bloquea y calcular sí, qué hace el GIL, en qué orden corren los middlewares, y de dónde sale un 422? |
| [A0-11 · Criptografía aplicada](A0-11-criptografia-aplicada.md) | ¿Por qué un hash no se puede revertir pero sí se puede romper con un diccionario, qué le agrega HMAC a un hash, y para qué sirve la sal? |
| [A0-12 · Sesiones y autenticación en la web](A0-12-sesiones-y-autenticacion.md) | ¿Podés escribir completo el pedido falso de un ataque CSRF, explicar por qué el token de doble envío lo frena, y por qué un JWT no se puede revocar? |
| [A0-13 · Flutter y Flet](A0-13-flutter-y-flet.md) | ¿Qué cruza el puente entre Python y Flutter cuando se llama a `update()`, y por qué una app de Flutter se ve igual en cualquier sistema? |
| [A0-14 · Visión por computadora en el dispositivo](A0-14-vision-en-el-dispositivo.md) | ¿Podés calcular a mano el ángulo de una rodilla a partir de tres puntos de pose, y explicar por qué contar una repetición necesita dos umbrales y no uno? |

---

## La Parte A

La Parte A es este sistema, y sus decisiones no se deducen de ninguna tecnología: quien no conoce el
repo la lee entera. Quien lo conoce puede usar la misma prueba.

| Capítulo | Salteátelo si podés responder esto |
|---|---|
| [A-01 · Qué es OlimpOS y qué problema resuelve](A-01-que-es-olimpos.md) | ¿Por qué el fichaje no pregunta nada y el cobro sí, y qué hace el sistema cuando ficha un socio con la cuota vencida? |
| [A-02 · El modelo de negocio codificado: prepago puro](A-02-prepago-puro.md) | ¿Por qué no hay tabla de deudas, qué significa entonces "deber", y por qué no se puede pagar el mes que viene? |
| [A-03 · Las dos aplicaciones y el único backend](A-03-dos-apps-un-backend.md) | ¿Por qué hay dos aplicaciones, cuál manda cuando difieren, y por qué la paleta y los permisos están escritos tres veces? |
| [A-04 · El recorrido completo de un pedido](A-04-recorrido-de-un-pedido.md) | ¿Qué pasa, escala por escala y con archivo y línea, entre el click en "Cobrar" y la fila nueva en `Pago`? |
| [A-05 · El modelo de datos](A-05-modelo-de-datos.md) | ¿Por qué no hay una columna `rol`, qué tablas no se pisan nunca, y cómo garantiza la base una sola rutina activa por socio? |
| [A-06 · Los seis roles y cómo se derivan](A-06-los-seis-roles.md) | ¿Cómo sabe el sistema qué es cada persona, cuántas consultas cuesta averiguarlo, y por qué se averigua una sola vez? |
| [A-07 · Autenticación](A-07-autenticacion.md) | ¿Qué lleva adentro el token, por qué la PWA usa una cookie y Flet no, y por qué una cuenta trabada responde igual que una clave equivocada? |
| [A-08 · Autorización](A-08-autorizacion.md) | ¿Dónde está escrito quién puede qué, por qué está escrito tres veces, y por qué la rutina propia de un socio le da 404 al personal y no 403? |
| [A-09 · Estados derivados contra estados guardados](A-09-estados-derivados.md) | ¿Por qué el estado del socio no se guarda, en qué orden se decide, y qué día exacto pasa a "Vencido"? |
| [A-10 · Bajas lógicas y reversibilidad](A-10-bajas-logicas.md) | ¿Qué pasa cuando un socio se da de baja con la cuota paga, y por qué desactivar su cuenta no lo da de baja? |
| [A-11 · Rendimiento contra una base remota](A-11-rendimiento.md) | ¿Por qué una pantalla tarda lo que tarda, qué hace el latido, y por qué optimizar Python no mueve la aguja? |
| [A-12 · Cómo leer `PROCESOS-LOGICOS-REQUERIDOS.md`](A-12-como-leer-los-procesos.md) | ¿Cómo se lee una línea del archivo de procesos, y cuáles son los procesos que no cuelgan de ninguna ruta? |

**Apéndices de la Parte A**

- [A-98 · Glosario](A-98-glosario.md): los 144 conceptos de A0 y A con una línea cada uno y el
  enlace al único lugar que los explica, remisiones desde los nombres con que se los busca, y los
  patrones de diseño con nombre.
- [A-99 · Mapa de conexiones](A-99-mapa-de-conexiones.md): todas las conexiones entre conceptos, por
  tipo —la misma idea, la causa, el mismo problema, la contradicción—, los nudos donde se cruzan más
  hilos, y un índice por concepto.

---

## La Parte B · Los 173 procesos

Mismo orden, misma numeración y mismos títulos que `PROCESOS-LOGICOS-REQUERIDOS.md`: un capítulo
por sección, y en cada uno, cada proceso con su tabla de archivos, líneas y símbolos en la vista de
la PWA, el service, los esquemas, el endpoint, la regla de negocio y la vista de Flet.

| Capítulo | Sección | Procesos |
|---|---|---|
| [B-01](B-01-acceso-y-sesion.md) | Acceso y sesión | 1–5 |
| [B-02](B-02-socios.md) | Socios | 6–28 |
| [B-03](B-03-personal.md) | Personal | 29–37 |
| [B-04](B-04-usuarios-y-cuentas.md) | Usuarios y cuentas de acceso | 38–45 |
| [B-05](B-05-cobros-y-pagos.md) | Cobros y pagos | 46–51 |
| [B-06](B-06-asistencia.md) | Asistencia | 52–56 |
| [B-07](B-07-recepcion.md) | Recepción | 57–59 |
| [B-08](B-08-actividades-turnos-horarios.md) | Actividades, turnos y horarios | 60–87 |
| [B-09](B-09-rutinas.md) | Rutinas | 88–97 |
| [B-10](B-10-nutricion.md) | Nutrición | 98–107 |
| [B-11](B-11-patologias.md) | Patologías | 108–109 |
| [B-12](B-12-promociones.md) | Promociones | 110–117 |
| [B-13](B-13-dashboard.md) | Dashboard | 118–121 |
| [B-14](B-14-portal-del-socio.md) | Portal del socio | 122–167 |
| [B-15](B-15-procesos-automaticos.md) | Procesos automáticos | 168–173 |

## La Parte C · Lo que no es un proceso

| Capítulo | Qué cubre |
|---|---|
| [C-01](C-01-contador-reps.md) | El contador de repeticiones: MediaPipe en el celular, la geometría de los ángulos, los umbrales y la máquina de estados de una repetición. |
| [C-02](C-02-offline-first-cola.md) | La cola de registros sin conexión: qué se encola, cuándo se vacía y qué pasa con un duplicado. |
| [C-03](C-03-graficos-a-mano.md) | Los gráficos dibujados a mano en las dos apps, y la matemática de mapear valores a píxeles. |
| [C-04](C-04-pwa-instalable.md) | La PWA como aplicación instalable: manifiesto, service worker, íconos y las trampas de iOS. |
| [C-05](C-05-capa-de-red.md) | La capa de red de cada app: el 401, el CSRF y el caché de Flet que se tira entero. |
| [C-06](C-06-sistema-de-diseno.md) | El sistema de diseño compartido: la paleta Kinetic Carbon y los componentes gemelos. |
| [C-07](C-07-lanzadores-e-instalador.md) | Los lanzadores y el instalador, y por qué un `.ps1` con acentos va en UTF-8 con BOM. |
| [C-08](C-08-demonio-videos.md) | El demonio de videos: un proceso cuyo estado es la existencia de un archivo. |

Los enlaces de B y C resuelven cuando esos capítulos estén escritos.

---

## Cómo está escrito cada capítulo

Las mismas convenciones en todos los capítulos. Conocerlas ahorra tiempo:

- **La línea que sigue al título declara el piso**: hasta dónde baja el capítulo. Más abajo de
  eso, bajar un escalón ya no explica nada de este sistema.
- **Cada concepto empieza por el problema que vino a resolver**, con su origen histórico cuando lo
  tiene, y recién después dice qué es.
- **"↓ Capa N"** marca cada escalón del descenso. Se puede saltear si ya sabés lo que dice, sin
  perder el hilo.
- **"Por qué está hecho así"** es ingeniería inversa: qué se estaba optimizando, qué restricción
  acorralaba, qué alternativa se descartó, qué se pagó por elegir, y cómo se llama el patrón.
- **"Nota marcada"** señala un lugar donde el código contradice a un documento o a un comentario. Se
  explica lo que hace el código —que es la verdad última— y la discrepancia queda anotada, no
  corregida.
- **"Con qué se conecta"** cierra cada capítulo con líneas sueltas, cada una con su tipo de
  conexión. Todas juntas forman el [mapa](A-99-mapa-de-conexiones.md).
- **Cada concepto se explica una sola vez**, en el capítulo que es su dueño; en el resto se lo nombra
  y se enlaza. Si un enlace te manda a otro capítulo, es porque la explicación vive allá, y no está
  repetida acá.
- **Las citas de código** van como `ruta:líneas` · `símbolo`, con la ruta relativa a la raíz del
  repo. El símbolo va al lado porque los números de línea se corren con la primera edición y el
  nombre no. Al código no se enlaza: se lo cita.
