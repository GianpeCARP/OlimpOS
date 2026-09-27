# A-12 · Cómo leer `PROCESOS-LOGICOS-REQUERIDOS.md`

*Piso del capítulo: una línea de proceso completa, desarmada parte por parte.*

`PROCESOS-LOGICOS-REQUERIDOS.md`, en la raíz del repo, describe **todo lo que el sistema hace** en 173 líneas:
una por cada ruta de la API y una por cada proceso que corre solo. Es la especificación contra la que se puede
contrastar el código, y es el esqueleto de la Parte B de esta masterclass, que lo sigue en el mismo orden y con
la misma numeración. Pero está escrito en una notación compacta que, sin una llave, se lee como una fila de
paréntesis. Este capítulo es esa llave.

---

## DFD lineal

### De dónde viene la notación

Un **diagrama de flujo de datos** (DFD) es una de las herramientas clásicas del análisis estructurado de
sistemas, formalizada en los años setenta: dibuja un sistema como **procesos** que transforman datos,
**entidades externas** que los originan o los reciben, y **almacenes** donde los datos quedan guardados, unidos
por flechas que muestran hacia dónde fluye cada cosa.

Un DFD es un dibujo. Este archivo escribe cada proceso del dibujo como **una sola línea de texto**, y eso tiene
una ventaja que un dibujo no tiene: las 173 líneas se pueden buscar, comparar entre versiones y **validar con un
programa**. Eso es un DFD lineal.

### La gramática

La forma de toda línea está en `PROCESOS-LOGICOS-REQUERIDOS.md:13`:

```
(ENTIDAD) -> (ENTRADA) <- (SALIDA) --- (N. NOMBRE) -> (TABLA -- escrito - escrito) <- (TABLA -- leído)
```

Las flechas se leen desde el proceso:

| Parte | Qué dice |
|---|---|
| `(ENTIDAD)` | quién dispara el proceso: uno o más de los seis roles, separados por `/` |
| `-> (ENTRADA)` | los datos que entran al proceso |
| `<- (SALIDA)` | lo que el proceso devuelve, **incluidos los errores** |
| `--- (N. NOMBRE)` | el evento: el número y el nombre del proceso |
| `-> (TABLA -- …)` | cada tabla que el proceso **escribe**, con las columnas que toca |
| `<- (TABLA -- …)` | cada tabla que el proceso **lee** para validar o decidir |

Con una regla de orden (línea 25): *"Las escrituras van siempre antes que las lecturas. Un proceso que no lee nada
lleva `<- ()`."*

### Una línea, parte por parte

> **↓ Capa 1 — el proceso 46 desarmado.** Éste es el piso.

El proceso 46 es el cobro de una cuota en el mostrador, el mismo que sigue escala por escala
[el recorrido de un pedido](A-04-recorrido-de-un-pedido.md). Está en `PROCESOS-LOGICOS-REQUERIDOS.md:446-451`, y
su línea, desarmada:

**Entidad** — `(DUENO / RECEPCIONISTA)`: los dos roles que pueden cobrar. No es una suposición: sale de la matriz
de permisos, que le da la acción de cobrar a esos dos y a nadie más
([matriz de permisos](A-08-autorizacion.md#matriz-de-permisos)).

**Entrada** — `(Datos del cobro)`: un concepto que agrupa todo lo que llega en el pedido —el socio, el plan, el
método de pago, el comprobante, la promoción opcional— sin enumerar cada campo.

**Salida** — el camino feliz, *"Cobro registrado con la membresía nueva y el abono de actividad opcional"*, seguido
de quince motivos de rechazo. Es el tema de la sección siguiente.

**Evento** — `(46. Cobrar una cuota en el mostrador)`.

**Escrituras** — tres tablas, con las columnas que toca cada una:

```
-> (Membresia -- id_socio - id_tipo_membresia - precio_pactado - fecha_inicio - fecha_vencimiento - estado)
-> (Pago -- id_socio - id_membresia - … - es_adelanto - estado - numero_comprobante - id_promocion - monto_descuento)
-> (Inscripcion_Actividad -- id_socio - id_plan_actividad - precio_pactado - fecha_inicio - fecha_vencimiento - estado)
```

**Lecturas** — diez tablas: `Usuario`, `Socio`, `Persona`, `Baja`, `Membresia`, `Tipo_Membresia`, `Promocion`,
`Pago`, `Plan_Actividad` y `Actividad`. Cada una responde una pregunta del cobro. `Baja` responde si hay una baja
programada, que bloquea el cobro. `Membresia` responde si hay un período en curso, que también lo bloquea. Y
`Pago` aparece leída sólo por `numero_comprobante`: es la que detecta un comprobante duplicado.

Esa línea no se aceptó por fe: al escribir el recorrido completo se contrastó con el código del handler, tabla por
tabla, y coincide entera.

### Las seis convenciones

La especificación de la notación no cubría todos los casos, y el archivo declara las seis decisiones que tomó para
cubrirlos (sección que empieza en la línea 30). Conocerlas es lo que permite leer una línea sin malentenderla:

| # | Convención | Línea | Qué evita leer mal |
|---|---|---|---|
| 1 | Una entidad por cada rol que puede disparar el proceso, **sacada de la matriz de permisos** | 34 | que la entidad sea una suposición |
| 2 | La salida **nombra los errores**, no sólo el camino feliz | 40 | ver la mitad del comportamiento |
| 3 | Los atributos que sólo se escriben en un **caso de error** figuran igual | 44 | creer que el login no escribe nada cuando falla |
| 4 | Un proceso **arrastra lo que escriben las funciones que llama** | 48 | que la baja parezca tocar sólo `Socio` |
| 5 | Las **funciones internas no son procesos** | 52 | contar dos veces el mismo flujo |
| 6 | Los nombres son **los de la base**: `Dueno` sin eñe, `Profesor_Actividad` con guion bajo | 57 | nombres que no se encuentran en el esquema |

La cuarta es la que más cambia lo que dice una línea. Dar de baja a un socio parece escribir sólo en `Socio`, pero
llama a `aplicar_baja()`, que cancela sus membresías, sus reservas y quizás su cuenta
([baja programada y baja inmediata](A-10-bajas-logicas.md#baja-programada-y-baja-inmediata)). La línea de la baja
declara las cuatro tablas, aunque el handler no nombre ninguna de las tres últimas.

### La aritmética: 173, 167, 165 y 130

El archivo dice que son **173 procesos: 167 rutas de la API y 6 que corren solos** (línea 6). Y en otros lugares del
proyecto aparecen otros números: `docs/ESTADO-ACTUAL.md` dice que el backend tiene **130 rutas** en `/openapi.json`,
y contando decoradores `@router` en los archivos de rutas salen **165**. Los cuatro números son correctos; miden cosas
distintas. Contando sobre la aplicación real —importando el backend sin levantarlo—:

| Número | Qué cuenta |
|---|---|
| **130** | direcciones distintas (*paths*): lo que lista `/openapi.json` |
| **167** | operaciones, es decir método más dirección: 71 `GET`, 71 `POST`, 14 `PUT`, 11 `DELETE` |
| **165** | decoradores `@router` en el código |
| **173** | las 167 operaciones más 6 procesos automáticos |

De 130 a 167: **37 direcciones atienden dos métodos**. `/socios` recibe `GET` para listar y `POST` para dar de alta,
y cada una es un proceso distinto. 130 + 37 = 167.

De 165 a 167: dos rutas se registran sin decorador, y el archivo lo explica (líneas 69-70): *"`GET /` y `POST
/portal/mi-cuota/pagar/{id_pago}/simular` se registran sin decorador y un grep no las ve"*. Por eso el archivo contó
las rutas desde la aplicación en memoria y no buscando en el texto.

### Cómo se verificó el archivo

La sección de la línea 62 declara tres controles mecánicos sobre las 173 líneas, además de la revisión de cada una
contra el código: **cobertura** —las 167 operaciones tienen su línea—, **nombres** —cada tabla y cada columna mencionada
existe en `db/schema.sql`, y pasan las 173 líneas (línea 72)— y **tablas huérfanas** —las 41 tablas del esquema aparecen
en al menos un proceso (línea 73)—.

El tercero tiene una excepción declarada (línea 90): *"`Sede` y `Franja_Laboral` no las escribe ningún proceso, y está
bien"*. Las carga el estado inicial de la base, y el sistema sólo las lee.

---

## `CONCEPTO_SALIDA` con errores

### La salida que nombra los rechazos

La segunda convención (línea 40) es la que más separa esta notación de un diagrama común: la salida de un proceso
**no es sólo lo que devuelve cuando todo sale bien**. La especificación pide que el proceso abarque "todos los casos
posibles", y el archivo lo toma literalmente.

> **↓ Capa 1 — la salida del proceso 46, completa.** Éste es el piso.

```
<- (Cobro registrado con la membresia nueva y el abono de actividad opcional, o rechazo porque el socio no
existe, por periodo en curso, baja programada o cuota en pausa, porque el plan de membresia o el de actividad no
existe o esta dado de baja, porque la promocion no existe, esta apagada o esta fuera de fecha, porque la promocion
es de otra sede, por comprobante duplicado, por monto manual sin ser dueno, o por mandar monto manual y promocion
a la vez)
```

Un camino feliz y quince rechazos, y cada rechazo termina en un error con su código HTTP. No son quince líneas del
handler: tres de ellos —período en curso, baja programada y cuota en pausa— salen de un mismo 409, que devuelve el
motivo que calcula la regla de renovación. El recorrido de un pedido los ubica en el código en
[los finales que no son el feliz](A-04-recorrido-de-un-pedido.md#los-finales-que-no-son-el-feliz).

### Por qué los errores son la mitad importante

En un sistema de gestión, **las reglas de negocio viven en los rechazos**. "Por período en curso" es la regla de no
cobrar por adelantado ([sin cobros por adelantado](A-02-prepago-puro.md#sin-cobros-por-adelantado)). "Por baja
programada" es la regla de no cobrarle a quien ya avisó que se va. "Por monto manual sin ser dueño" es un permiso.
Un diagrama que mostrara sólo el camino feliz de este proceso diría "se registra un cobro", y no diría ninguna de las
decisiones que hacen que el sistema sea éste y no otro.

### Lo que se escribe sólo cuando algo falla

La tercera convención es la consecuencia de la segunda en el bloque de escrituras. Si un proceso escribe algo
**sólo en un caso de error**, eso también figura. El ejemplo del archivo es el login, proceso 3 (línea 133), que
declara:

```
-> (Usuario -- intentos_fallidos - ultimo_acceso)
```

`ultimo_acceso` se escribe cuando el login sale bien; `intentos_fallidos` sube **cuando falla** (y vuelve a cero cuando sale bien). Sin la convención, la línea
del login ocultaría la escritura más importante que hace: la que alimenta el
[freno de intentos](A-07-autenticacion.md#freno-de-intentos-y-respuesta-indistinguible).

---

## Proceso automático

### El disparador que no es un pedido

Seis de los 173 procesos no cuelgan de ninguna ruta: nadie los pide. Los dispara el arranque del backend, un
temporizador o un proceso aparte. Están al final del archivo, en la sección que empieza en la línea 1328, y cada uno
declara, en lugar de una ruta, **qué lo dispara**:

| # | Proceso | Qué lo dispara |
|---|---|---|
| 168 | Descargar los videos de YouTube que faltan | un proceso aparte, cada 10 minutos |
| 169 | Generar los turnos de las próximas semanas | el arranque del backend (y el botón "Generar turnos") |
| 170 | Mantener despierta la base y disparar el mantenimiento diario | un hilo, cada 120 segundos |
| 171 | Asegurar el dueño inicial con cuenta | el arranque |
| 172 | Preparar la base y el pool | el arranque, una vez, antes del primer pedido |
| 173 | Aplicar las bajas programadas vencidas | el arranque, una vez por día desde el hilo del 170, y al leer socios |

> **↓ Capa 1 — la segunda línea de cada uno.** Éste es el piso.

Donde un proceso normal pone su ruta, uno automático pone su disparador. El 170 (línea 1344):

```
`Automatico — Hilo daemon temporizado, cada 120 segundos, arrancado por el lifespan`
```

Es el [latido](A-11-rendimiento.md#latido), y la tabla muestra por qué ese hilo es tan importante: además de mantener
la base despierta, es el único reloj del sistema, y de él cuelga el 173.

El 172 tiene una salida que vale verificar, porque describe un borde: *"arranque abortado si la base no responde"*. Es
exactamente lo que pasa, y se comprobó arrancando el backend con la base inalcanzable: el arranque se corta al crear
el esquema, antes de llegar al precalentado del pool (la nota está en
[pool de conexiones](A-11-rendimiento.md#pool-de-conexiones)).

### Los dos límites que el formato declara

La notación tiene dos cosas que no puede expresar, y el archivo las declara en vez de esconderlas (sección de la línea
77). Las dos aparecen en los procesos automáticos:

- **Los almacenes que no son tablas.** El proceso 168 escribe videos en una carpeta del disco, y *"que el archivo exista
  es el estado del proceso"* (línea 82). Como la notación sólo admite tablas, la línea del 168 aparece leyendo `Ejercicio`
  y **sin escribir nada**, aunque escribe archivos todo el tiempo. Es el
  [almacén que no es tabla](A-05-modelo-de-datos.md#almacén-que-no-es-tabla).
- **Las entidades externas.** La especificación limita la entidad a los seis roles, pero hay procesos que no dispara
  ninguna persona del gimnasio: el aviso de Mercado Pago, que llega a un webhook, o un temporizador. El archivo pone en
  esos casos **el rol en cuyo beneficio corre el proceso** y lo aclara. Por eso el latido figura como `(DUENO)`: nadie lo
  dispara, pero existe para el sistema del dueño.

Leer una línea sabiendo estos dos límites es lo que evita la conclusión equivocada: que el demonio de videos no hace
nada, o que el dueño tiene que apretar algo cada dos minutos.

---

## Con qué se conecta

- **Es la misma idea que…** [el recorrido de un pedido](A-04-recorrido-de-un-pedido.md): cada línea del archivo es el
  resumen de un recorrido; el recorrido es una línea contada escala por escala.
- **Existe por culpa de…** la [matriz de permisos](A-08-autorizacion.md#matriz-de-permisos): la entidad de cada proceso
  sale de ella, no de una suposición.
- **Existe por culpa de…** el [latido](A-11-rendimiento.md#latido): el único reloj del sistema, del que cuelgan los
  procesos automáticos 170 y 173.
- **Es el mismo problema que…** el [almacén que no es tabla](A-05-modelo-de-datos.md#almacén-que-no-es-tabla): un estado
  que la notación no puede nombrar porque no vive en una fila.
- **Es la misma idea que…** [sin cobros por adelantado](A-02-prepago-puro.md#sin-cobros-por-adelantado): las reglas de
  negocio viven en los rechazos, y por eso la salida los enumera.
