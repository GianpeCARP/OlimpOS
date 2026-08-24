# Bitácora — de PERAZZO al backend andando

Qué se hizo desde que abrimos la carpeta del profesor, **cómo** y sobre todo
**por qué**. Es el complemento de `GUIA_BACKEND.md`: aquella explica el
sistema terminado, ésta cuenta el recorrido y las decisiones que se tomaron
en el camino.

> **Rama:** todo esto vive en `desarrollo`. `main` quedó en el commit
> `58807cb`, con el backend completo y sin el cableado — es la rama estable.

**Volumen:** 11 commits, 120 archivos, ~19.000 líneas.

---

## 1. Punto de partida: leer PERAZZO

`Proyeto-Python/PERAZZO/` no era documentación suelta: era **un proyecto
funcional completo** del profesor (backend FastAPI + frontend Flet + Neon),
más dos documentos.

**Lo primero fue separar qué copiar de qué no.** Su proyecto tiene 10 tablas;
el nuestro 35. Copiar su modelo de dominio habría sido un retroceso. Lo que
sí había que copiar era **la arquitectura y sus normas de proceso**.

### La contradicción que encontramos

Los dos documentos del profesor **se contradicen** en el punto más importante:

- El `.docx` dice: `personas.usuario_id` → FK a `usuarios`. La persona cuelga
  del usuario.
- Su **código** hace lo contrario: `Persona` es la raíz y `Usuario` cuelga de
  ella.

**Ganó el código**, y el docstring de su propio `models.py` explica por qué:
si la persona dependiera del usuario, habría que crearle cuenta de login a
todo el mundo. Y en un gimnasio real hay socios que pagan en el mostrador y
nunca bajan la app.

### El hallazgo que ahorró trabajo

**La PWA ya implementaba ese patrón, y mejor.** `types.ts` ya tenía `Persona`
como raíz con `Usuario`, `Socio` y `Empleado` colgando, teléfonos en tabla
aparte y roles derivados de las tablas hijas. No hubo que rediseñar nada: solo
construir el backend encima del esquema que ya existía.

---

## 2. Dónde poner el backend

**Corrección de premisa:** la idea inicial era "un backend para la PWA y otro
para Flet". No. Dos backends = la lógica de negocio escrita dos veces, dos
veces los bugs, y datos que se desincronizan.

```
                        ┌──→ PWA React      (navegador)
Neon ←── backend/ ←─────┤
  (Postgres)   FastAPI  └──→ App Flet       (escritorio)
```

`backend/` va en la raíz del monorepo, hermano de los dos frontends, porque no
pertenece a ninguno.

---

## 3. El hueco que bloqueaba todo

Al mapear el esquema apareció el problema: **`Usuario` no tenía la columna
`debe_cambiar_password`**. Sin ella, el mecanismo central del profesor —entrar,
que te nieguen el token, cambiar la clave, volver a entrar— era imposible de
escribir.

Se agregó **en los dos lados**:
- `db/schema.sql` → para bases creadas desde cero
- `db/migrations/001_...sql` → para la de Neon, que ya existía

Correr `schema.sql` sobre una base existente falla con *"table already
exists"*; de ahí que hicieran falta los dos archivos.

**Fue el único cambio de esquema en todo el proyecto.** Una columna, una tabla.

---

## 4. Decisiones donde nos apartamos del profesor

| Él | Nosotros | Por qué |
|---|---|---|
| DNI como clave primaria | `id_persona` sustituta, DNI único aparte | Un DNI mal tipeado se corrige con un `UPDATE` en vez de arrastrar el cambio por diez tablas |
| `create_all()` define el esquema | `schema.sql` manda, los modelos lo mapean | El DDL es parte de la entrega académica; si los modelos lo definieran, podrían divergir del diagrama sin que nadie se entere |
| Columna `rol` en `Usuario` | Rol **derivado** de las tablas de rol | Con una columna, el rol y la realidad pueden contradecirse. Derivándolo es imposible |
| `allow_origins=["*"]` | Lista restringida desde `.env` | Su único frontend es de escritorio y no aplica CORS. Nuestra PWA sí corre en el navegador |
| Token en el cuerpo | Cookie httpOnly + CSRF (web) | Ver sección 6 |

**El rol derivado tiene un costo** —cinco JOINs por request— que se resuelve
calculándolo **una sola vez en el login** y firmándolo dentro del JWT. El
contrato de la API queda idéntico al suyo; lo que cambia es de dónde sale el
dato.

---

## 5. El orden en que se construyó, y por qué ese orden

1. **Auth** — es la puerta de todo lo demás
2. **Socios** (alta por invitación) — el flujo estrella de la consigna
3. **Usuarios** — desbloqueo y reseteo, que hasta ahí se hacían con SQL a mano
4. **Personal** — desbloquea a los siguientes: Rutinas necesita Entrenadores
5. **Rutinas y Nutrición**
6. **Cobros** — sostiene el negocio
7. **Asistencia y Actividades**
8. **Dashboard y portal del socio**
9. **Cableado de la PWA**, sección por sección

El paso 4 antes que el 5 no es casual: no se puede crear una rutina sin un
entrenador a cargo (`id_entrenador` es NOT NULL).

**La seguridad se hizo ANTES de los routers** (paso entre el 3 y el 4), y fue
la decisión de orden más importante: cambiar cómo viaja la sesión después
habría obligado a reescribir cada router.

---

## 6. Seguridad: el pedido de "que sea impenetrable"

### El problema del token en JavaScript

Cualquier token que el código pueda leer, un script inyectado (XSS) también.
La solución es la cookie `httpOnly`: el navegador la manda sola, pero
JavaScript no puede leerla.

### El problema que eso crea

El navegador manda las cookies **siempre**, incluso cuando el pedido lo
origina otro sitio. Eso es **CSRF**. La defensa es el doble envío: una segunda
cookie **legible** que la app copia a un header. Un sitio atacante puede hacer
que el navegador *mande* cookies, pero no puede *leerlas*, así que no puede
armar el header.

### Modo dual — y no es inconsistencia

| Cliente | Mecanismo | Por qué |
|---|---|---|
| PWA (navegador) | cookie httpOnly + CSRF | tiene XSS y CSRF |
| Flet (escritorio) | `Authorization: Bearer` | no es navegador: no tiene ninguno de los dos |

Darle cookies a Flet no agregaría seguridad, solo ceremonia. **Cada cliente
usa lo que resuelve SUS amenazas.**

### El bug que casi se nos pasa

Después de migrar a cookies el login *parecía* andar, pero `GET /me` daba 401
y un F5 deslogueaba. La causa: la página estaba en `localhost` y la API en
`127.0.0.1`. **Para el navegador son hosts distintos**, y la cookie quedaba
guardada bajo uno mientras la página estaba en el otro.

Se resolvió con un **proxy de Vite**: la app le pega a `/api/...` —mismo
origen— y Vite reenvía al backend. No es una muleta: en producción ambos van a
estar bajo el mismo dominio, así que el proxy hace que desarrollo se parezca a
producción.

---

## 7. Reglas de seguridad que salieron de leer los comentarios

`config.ts` documentaba un vector de escalación de privilegios real:

> *"cualquier recepcionista podía reseteársela al Dueño, leer la clave nueva y
> entrar con control total. Escalación de privilegios completa, con tres
> clicks."*
>
> *"⚠️ esto oculta botones, no cierra la puerta. **El backend tiene que
> rechazar la misma operación cuando exista**."*

Ese backend es el que escribimos, así que se portaron las dos reglas de fila:

1. **Nadie fuera del Dueño edita o desactiva su propia cuenta.**
2. **Solo un Dueño opera sobre la cuenta de un Dueño.**

Con una asimetría que no es obvia: resetearse la **propia** contraseña sí se
permite (regla 1 no aplica), pero resetear la de alguien de mayor jerarquía no
(regla 2 sí aplica).

Lo mismo con la auditoría del 2026-08-03, que documentaba que un socio —incluso
dado de baja— veía el DNI de todos los demás. Se cerró con el **portal del
socio**: ningún endpoint de ahí acepta un id por parámetro, todos usan el
`id_socio` firmado en el token.

---

## 8. Reglas de negocio que viven en el backend

| Regla | Por qué del lado del servidor |
|---|---|
| El monto de un cobro sale del plan | Si viniera del cliente, cualquiera cobraría $1 una membresía de $30.000 |
| El cupo de una clase no se supera | Con el chequeo solo en el frontend, bastaría llamar al endpoint directo |
| No se reserva sin saldo en el abono | Ídem |
| Cancelar a último momento no devuelve la clase | Cada actividad define su ventana |
| Nada se borra: se cancela | Un registro contable que desaparece es un agujero en la caja |
| Pagar adelantado no come los días restantes | El período nuevo arranca al vencer el anterior |

Y una que va al revés: **la asistencia se registra aunque el socio deba**. El
sistema informa, no juzga — dejar a alguien afuera es algo que decide una
persona mirando el caso. Además, si no se registrara, el gimnasio perdería el
dato de que esa persona estuvo.

---

## 9. Cómo se verificó

Nada se dio por bueno porque "compila". Cada tanda se probó **contra Neon
real**, con scripts que ejercitan el flujo completo y verifican también los
casos que **tienen que fallar**.

| Tanda | Chequeos |
|---|---|
| Flujo del dueño | 15 |
| Seguridad (cookies + CSRF) | 20 |
| Registro por invitación | 18 |
| Personal, Rutinas, Nutrición | 20 |
| Cobros | 15 |
| Asistencia y Actividades | 19 |
| Dashboard y portal | 21 |

### Dos lecciones de método

**`compileall` no alcanza.** Compila pero no ejecuta, así que un import
faltante pasa desapercibido. Pasó con `EmailStr`: compilaba y el backend no
arrancaba. Desde entonces se verifica con `python -c "import main"`.

**Un proceso no relee los archivos.** Cargó el código al arrancar y se quedó
con esa copia. Hubo un rato perdido "arreglando" cosas que nunca se
ejecutaban porque el proceso viejo seguía respondiendo en el puerto 8000.

### La verificación que se automatizó

`permisos.py` es espejo de `config.ts`, y desincronizarse es **silencioso**:
un color mal copiado se ve, un permiso mal copiado no. Por eso existe
`check_permisos.py`, que compara las **800 celdas** (5 roles × 16 secciones ×
10 acciones) y falla si difieren.

---

## 10. Estado al cierre de esta bitácora

| | |
|---|---|
| Endpoints | **77** |
| Routers | **12** |
| Tablas modeladas | **32 de 35** |
| PWA cableada | 6 de 11 secciones |
| Flet cableado | solo el login |

### Lo que falta

- **PWA**: Actividades (la sección más grande), y las funciones sueltas de
  `personalService` y `membresiaService`
- **Flet**: 21 métodos de `state.py` y 11 vistas — es lo más atrasado
- **Backend**: salud, bajas y patologías (3 tablas)
- **Entrega**: vaciar la base dejando solo el seed

### El bloque que se subestima

El frontend estaba "hecho" en el sentido de que se veía bien, pero cada
pantalla leía de arrays en memoria. Convertir eso son **117 funciones**
(96 en la PWA + 21 en Flet), un volumen comparable al backend entero.

Y no es copiar y pegar: cada una hay que cruzarla contra lo que el endpoint
realmente devuelve. El mock inventó formas de datos que a veces no coinciden
con el esquema real — pasó con `authService`, donde el mock tenía
`usuario.rol` como columna y el backend lo deriva.

---

## 11. Estado al 2026-08-20

Desde el cierre de la sección 10 (commit `631b599`, 2026-08-10) pasaron 24
commits más de cableado real: Actividades completo en las dos apps, Flet
terminó sus escrituras (asistencia, cobros, recepción con refresco solo),
autogestión del socio (turnos, abonos, congelamiento, baja), Mercado Pago en
modo simulado, y las tres tablas que en la sección 10 figuraban como
pendientes (salud, bajas, patologías) ya están.

| | |
|---|---|
| Endpoints | **129** |
| Routers | **14** (+ `auth_router`) |
| Tablas modeladas | **37 de 37** — pero ver "El agujero que apareció" abajo |
| PWA cableada | **11 de 11 secciones** — `mockDb.ts` ya no existe en el repo |
| Flet cableado | **11 de 11 vistas** — las 60 funciones de datos de `state.py` llaman a `api_client`; las 18 restantes son helpers de sesión/formato que no necesitan pegarle a la API |

Verificado leyendo código, no mensajes de commit: conté los `@router.` de
cada archivo de `backend/routers/`, las `class X(Base)` de `models.py`, y en
cada `service/*.ts` de la PWA y cada función de `state.py` si efectivamente
llaman a `pedir()` / `api_client` en vez de devolver algo hardcodeado. No
quedan imports de `mockDb` (el archivo se borró) ni TODOs de mock reales en
las vistas de ninguna de las dos apps — los dos "TODO" que aparecieron en el
grep eran la palabra "todo/todos" en español, no marcadores.

### El agujero que apareció

`Congelamiento` (migración 008) tiene clase en `models.py` pero **no tiene
`CREATE TABLE` en `schema.sql`**. Es exactamente el riesgo que advierte el
comentario de `database.py` sobre mantener las dos copias sincronizadas: la
008 se aplicó a mano contra Neon y a `schema.sql` — a diferencia de las otras
ocho migraciones — nunca se la dobló. Hoy son 37 tablas reales en Neon (se
puede congelar una membresía y el backend lo lee sin problema) pero 36 en el
DDL entregado. Si alguien arranca una base nueva desde `schema.sql` a secas,
le va a faltar esa tabla.

### Lo que falta ahora

- **Backend**: nada de tablas sin cablear. Lo pendiente es todo lo que ya
  usa datos reales pero no se probó contra Mercado Pago real (ver docstring
  de `mercadopago.py`: falta token, URL pública y secreto del webhook).
- **`schema.sql`**: agregar el `CREATE TABLE "Congelamiento"` que falta (ver
  arriba). Es la migración 008 copiada tal cual, no hay que diseñar nada.
- **Entrega**: seguía pendiente en la sección 10 — vaciar la base dejando
  solo el seed — no se volvió a tocar este ítem, sigue abierto.
- **Permisos**: el guard de roles del router de Flet sigue comentado a
  propósito (ver `CLAUDE.md` de la raíz) — no es un olvido, es la matriz de
  `config.ts` la que todavía tiene que reemplazarlo.

---

## 12. Correcciones a la sección 11, y estado al 2026-08-23

La sección 11 se escribió al día siguiente de los últimos commits de
cableado, y en tres puntos quedó desactualizada o dice algo que ya no es
cierto. Se corrige acá en vez de editarla: la bitácora cuenta un recorrido, y
tachar lo que se creía en su momento haría perder justamente eso.

### Tres cosas que la sección 11 da por pendientes y no lo están

**1. El guard de permisos de Flet ya NO está comentado.** La sección 11 dice
que "sigue comentado a propósito" y remite al `CLAUDE.md` de la raíz. Los dos
textos quedaron viejos: el guard está **activo** desde el commit `43379c3`.

Lo que lo bloqueaba era real y estaba bien anotado: el guard viejo era un
`if route == USUARIOS and not is_admin(): return`, un booleano suelto que
además **moría en silencio** — la pantalla no cambiaba y no había forma de
saber si el permiso había fallado o si la app se había colgado. La nota pedía
no descomentarlo hasta que existiera la matriz de verdad.

Esa precondición se cumplió: `Proyeto-Python/Proyecto/app/permisos.py` es
ahora la tercera copia de la matriz (5 roles × 3 niveles), y
`check_permisos.py` verifica que las tres digan lo mismo. Con eso el guard
puede decir algo mejor que "no": muestra un snackbar explicando que el rol no
tiene acceso. El problema nunca fue bloquear, era bloquear sin explicar.

> **Ojo, esto importa para la próxima sesión:** el `CLAUDE.md` de la raíz
> todavía instruye *"No lo 'arregles' descomentándolo"*. Esa instrucción ya
> no aplica y seguirla hoy revertiría código que funciona.

**2. `Congelamiento` ya está en `schema.sql`.** La sección 11 lo describe
como "el agujero que apareció", pero el mismo commit que escribió esa
sección (`436eb82`) lo arregló. El documento se contradice a sí mismo: la
sección lo reporta abierto y el DDL entregado ya lo tiene.

**3. La base ya está vacía.** El ítem "Entrega: vaciar la base dejando solo
el seed" venía arrastrándose desde la sección 10. Hoy Neon tiene **6 filas**:
la Persona y el `Dueno` del titular, la Sede Central, los dos tipos de
membresía y la cuenta `dueno` — que nace con `debe_cambiar_password` en true,
así que el primer ingreso obliga a definir una contraseña propia.

### Una divergencia NUEVA que la sección 11 no podía anticipar

El commit `436eb82` sacó `Consulta_Cruzada` de `schema.sql` con el argumento
de que es una tabla decorativa que ningún modelo referencia. El argumento es
correcto, pero tiene una consecuencia que conviene dejar escrita:

    schema.sql   ->  37 tablas
    Neon         ->  38 tablas  (Consulta_Cruzada sigue ahí)

O sea que el DDL entregado y la base real **ya no coinciden**. No rompe nada
—nadie la usa— pero es exactamente el mismo tipo de deriva que la sección 11
señalaba en el caso inverso con `Congelamiento`, y merece una decisión
explícita: o se borra de Neon, o se vuelve a poner en el DDL. Queda anotado,
no resuelto.

### Lo que la sección 11 no menciona porque todavía no existía

| | |
|---|---|
| Migraciones | **9** (`Proyecto/db/migrations/`) |
| Suites de integración | **8** (`backend/pruebas/`) |
| Endpoints | **129** en 14 routers |
| Tablas modeladas | **37** |

Las suites no son scripts descartables: crean su propio escenario, corren
contra Neon con la base vacía y se guardaron en el repo porque son lo que
encontró casi todos los bugs de esta etapa. Dos de ellas
(`test_extension_congelamiento`, `test_una_sola_activa`) tocan la base
directamente por SQL, porque lo que prueban no se puede verificar por HTTP:
para que una cuota venza hay que esperar un mes, y para probar que la base
frena un INSERT hay que hacer ese INSERT sin pasar por la app.

### La lección que se repitió tres veces

Tres agujeros distintos de esta etapa resultaron ser el mismo problema: **una
regla de negocio que vivía sólo en el código del router, con la base sin
enterarse.**

| Regla | Cómo se descubrió | Dónde vive ahora |
|---|---|---|
| El cupo de un turno | Se metieron 5 reservas en un turno de 2 | `CONSTRAINT TRIGGER` (migración 006) + lock de fila |
| Una sola rutina/dieta activa | Se insertaron 2 activas por SQL | Índice único parcial (migración 009) |
| La deuda de una cuota vencida | `Deuda(` no aparecía en ningún router | Se genera al arrancar (`deudas.py`) |

Los tres se encontraron **corriendo**, no leyendo. Y el patrón del arreglo
también se repitió: la defensa se bajó al esquema, donde no se puede olvidar
de aplicar, en vez de dejarla en un `if` que el próximo endpoint puede no
copiar.

Con una trampa que apareció dos veces y conviene recordar: la sesión de
SQLAlchemy tiene `autoflush=False`, así que **nada llega a la base hasta que
se lo pide explícitamente**. Eso rompió la promoción de la lista de espera
(contaba el cupo antes de que la cancelación estuviera escrita) y casi rompe
la reasignación de rutinas (un índice único parcial no puede ser
`DEFERRABLE`, y SQLAlchemy ordena sus `INSERT` antes que sus `UPDATE`). Las
dos veces la solución fue un `db.flush()` en el lugar exacto.

### Lo que falta ahora

- **Mercado Pago**: es lo único del backend que no se probó contra el
  servicio real. Falta lo que no depende del código y está anotado en
  `backend/.env.example`: un `ACCESS_TOKEN`, el secreto del webhook, y una
  **URL pública** — Mercado Pago no le puede avisar a `127.0.0.1` que un pago
  se acreditó. Mientras tanto hay un modo simulado que permite recorrer el
  flujo entero, y que se niega a activarse si detecta un token real cargado.
- **UI que falta para cosas que el backend ya hace**: patologías no tiene
  pantalla en ninguna de las dos apps, y "entrenador a cargo" sólo la tiene
  en Flet. La PWA no las conoce.
- **`Promocion`**: está modelada y ningún router la usa. Los descuentos
  existen en el esquema y no hay forma de cargarlos.
- **`Consulta_Cruzada`**: la divergencia de arriba.
- **`CLAUDE.md`**: tiene al menos dos afirmaciones vencidas (los permisos y
  las escrituras de Flet marcadas como `TODO`). Conviene actualizarlo antes
  que la bitácora, porque es el archivo que se carga en cada sesión.

---

## 13. Se cerró la lista de la §12 — estado al 2026-08-24

La sección 12 terminaba con cinco pendientes. Cuatro están cerrados; el quinto
sigue esperando algo que no es código.

| Pendiente de la §12 | Estado |
|---|---|
| UI de patologías (no existía en ninguna app) | **cerrado** |
| "Entrenador a cargo" en la PWA (sólo estaba en Flet) | **cerrado** |
| `Promocion` modelada y sin usar | **cerrado** |
| `Consulta_Cruzada`: 37 tablas en el DDL, 38 en Neon | **cerrado** |
| Mercado Pago sin credenciales | **sigue abierto** (no depende del código) |

| | |
|---|---|
| Endpoints | **138** en 15 routers (+ el `GET /` de salud, que va sobre `app`) |
| Tablas | **37** en `models.py`, **37** en `schema.sql`, **37** en Neon |
| Suites de integración | **9** |

### El agujero que sólo se ve cuando dibujás la pantalla

`POST /portal/mis-patologias` existía desde la §11 y estaba bien pensado: el
socio declara sus propias condiciones sin pasar por el mostrador —donde además
el Recepcionista no debería enterarse—. Pero ese endpoint pide un
`id_patologia`, y el catálogo se listaba únicamente en `GET /patologias`, que
exige `VER_HISTORIAL_MEDICO`. El rol Socio tiene **todas** las acciones en
false. Verificado ejecutando, no leyendo:

    puede_accion([SOCIO], VER_HISTORIAL_MEDICO)  ->  False

O sea: el socio podía declarar una condición, pero no había forma de averiguar
qué número mandarle. Un endpoint completo e inusable.

**Por qué no lo detectó la suite.** `test_patologias.py` ya cubría el caso —el
paso 9 hacía que el socio cargara "Asma"— pero le pasaba el `ID_ASMA` que había
leído **el entrenador**, por una variable de Python. En la app real esa variable
no existe. La prueba compartía entre dos sesiones un dato que en producción no
comparten.

La lección no es "la suite estaba mal escrita". Es que **una prueba que arma su
escenario con un solo token no puede detectar un permiso faltante entre dos
roles**: el guard nunca se ejerce porque el dato viaja por el costado. Los tres
agujeros de la §12 aparecieron corriendo; éste apareció recién al intentar
dibujar el selector, que es un paso más adelante que correr.

El arreglo fue `GET /portal/catalogo-patologias`, guardado por
`Seccion.MI_PERFIL`. **No** se le aflojó el permiso a `GET /patologias`, y eso
importa: esa acción no significa "ver la lista de enfermedades que existen",
significa ver el historial médico de OTRA persona, y es la única de la matriz
donde el Recepcionista queda por debajo del Entrenador. Abrirla habría dado de
paso al mostrador exactamente el acceso que el docstring de
`routers/patologias.py` explica en detalle por qué no debe tener.

Y no es la primera vez que el portal necesita republicar un catálogo:
`/portal/mi-cuota/planes` ya existía por lo mismo —duplica
`/cobros/tipos-membresia`, que el socio no puede tocar—. El patrón quedó
establecido: **cuando el portal necesita un catálogo que vive detrás de un
permiso de gestión, se republica recortado; no se afloja el permiso del otro
lado.**

### Tres bugs que sólo se veían haciendo clic

Apareció porque alguien intentó entrar a Flet como recepcionista y la app dijo:

    The application encountered an error: 'NoneType' object is not callable

`_load_main_app` (login.py) arma la pantalla inicial así:

    linea 266:  vista_inicial = router.view_class(inicial)
    linea 267:  initial_content = vista_inicial(page=page, router=router).build()
    ...
    linea 284:  router.setup(content_ref)

Y `setup()` era quien llamaba a `_register_views()`, o sea quien llenaba el mapa
de rutas. **Dieciocho líneas después de usarlo.** El mapa siempre estaba vacío,
`view_class` devolvía `None`, y la línea siguiente hacía `None(page=...)`.

Rompía a los cuatro roles, no sólo al recepcionista — el que reportó fue el
primero en intentarlo:

    dueno          -> dashboard   view_class -> None
    recepcionista  -> recepcion   view_class -> None
    entrenador     -> socios      view_class -> None
    nutricionista  -> socios      view_class -> None

Se podía arreglar subiendo el `setup()` en login.py, pero eso deja la trampa
armada para el próximo. **El problema de fondo era que `setup()` hacía dos cosas
sin relación**: guardar las referencias del layout Y registrar las vistas.
Registrar no necesita ninguna referencia, así que atarlo a ese momento era la
causa. El arreglo es que `view_class` registre al primer uso (con
`_register_views` idempotente), y que `navigate` pase por ahí en vez de leer
`_view_map` directo. Con eso el orden deja de importar y no queda una segunda
forma de romperlo desde otro archivo.

**Lo que esto agrega a la regla del proyecto.** La §12 decía "casi todos los
bugs aparecieron corriendo, no leyendo". Este bug estaba en el camino MÁS
transitado de la app —entrar— y sobrevivió a `compileall`, a nueve suites de
integración y a que la app arrancara sin un solo warning. Porque las suites
prueban el backend por HTTP y no tocan el router de Flet, y **una app que
arranca no es una app en la que se pueda entrar**. La única forma de encontrarlo
era hacer clic en "Ingresar".

Apenas se pudo entrar, el segundo clic —al Dashboard— tiró otro:

    TypeError: '>=' not supported between instances of 'NoneType' and 'int'

`_texto_delta` hacía `delta_pct >= 0`, y el backend manda `delta_pct` en **None**
cuando el mes anterior fue cero. Eso no era un descuido del backend: está
documentado en el docstring de `_delta` (`routers/dashboard.py`) desde que se
escribió, con su razón —dividir daría infinito, y mostrar "+100%" al pasar de 0
a 1 socio sería inventar un dato— y hasta con la conclusión escrita: *"La vista,
con None, no muestra nada, que es lo honesto."*

**El contrato estaba completo; faltaba implementada una de las dos mitades.** Y
la PWA sí la tenía (`textoDelta` en `DashboardView.tsx` devuelve `undefined`), o
sea que era una **asimetría entre gemelas**, no una decisión. Con una base sin
historial —o sea, en cualquier demo— las cuatro métricas vienen en None y el
Dashboard no abría nunca.

Eso motivó buscar el resto de la familia en vez de arreglar de a uno, y apareció
el tercero: **Nutrición** hacía `sum(cals)//len(cals)` sobre la lista de planes.
Sin planes cargados, `ZeroDivisionError` —y `min`/`max` un `ValueError`—, así que
la sección entera no abría para **ningún** rol. Otra vez la PWA ya lo resolvía
(`calorias.length > 0 ? ... : 0`) y la gemela no.

**La herramienta que faltaba.** Los tres tienen la misma forma: revientan al
CONSTRUIR una vista, con datos que el backend devuelve legítimamente. Ni
`compileall` ni las suites pueden verlos —las suites prueban el backend por
HTTP, nunca instancian una vista de Flet— así que se agregó
`Proyeto-Python/Proyecto/pruebas_vistas.py`: entra con cada rol y llama a
`build()` de cada sección que ese rol puede ver. Son 25 combinaciones y tarda
segundos.

No verifica que la pantalla se vea bien; verifica que se pueda **abrir**, que es
justo lo que fallaba. Encontró el de Nutrición sola, y conviene correrla también
**con la base vacía**, que es el escenario donde estos tres se disparan y el que
va a ver cualquiera que arranque el proyecto de cero.


### Y dos que `compileall` y `tsc` dan por buenos

**1. `input_field` usado sin importar, en Flet.** `compileall` compila el
archivo sin quejarse: el nombre sólo se resuelve al ejecutar la función que lo
usa, o sea al abrir el diálogo. Es exactamente lo que el `CLAUDE.md` ya
advertía ("un nombre usado sólo dentro de una función tampoco lo detecta el
import — eso ya mordió dos veces"). Se encontró con un chequeo AST que compara
los nombres cargados contra los importados y los ligados localmente.

**2. Un `useEffect` que leía `tipoElegido` antes de su `const`, en la PWA.**
`tsc` lo da por válido —la referencia es correcta para el compilador— pero el
array de dependencias se evalúa **durante** el render, así que en ejecución era
un `ReferenceError` por TDZ. Se arregló moviendo el efecto después de la
declaración, con un comentario que explica por qué no puede ir arriba con los
demás.

Y una tercera, del entorno y no del código, que costó una corrida entera de
suite con tres fallos falsos: **el backend viejo seguía escuchando en el 8000.**
El `uvicorn` nuevo no pudo tomar el puerto y murió en silencio, así que la suite
corrió contra código anterior al cambio y reportó como roto un endpoint que
estaba bien. Se detectó comparando `openapi.json`: 130 endpoints contra los 131
de entonces. Desde ahí, la regla es **verificar la versión del backend antes de
correr una suite**, no después de leer los fallos.

Las tres, juntas: *"compilar no es correr"* ya estaba anotado. Lo que faltaba
era su continuación — **correr no alcanza si no verificás contra qué corrés, y
que el proceso levante no significa que la pantalla funcione.**

### Dos scripts que faltaban en `pruebas/`

Ninguno es una suite. Se agregaron porque el trabajo de esta etapa los necesitó
de verdad, no por prolijidad.

**`vaciar_base.py`** — deja la base en las 6 filas de entrega. El `CLAUDE.md`
decía desde la §10 que "entre suite y suite hay que vaciar la base" y no decía
cómo: se hacía a mano. A mano significa que cada vez queda un poco distinto —
una corrida a medias deja tres Patologías y dos Empleados, la siguiente suite
choca contra un DNI repetido, y el fallo parece un bug del código que se acaba
de escribir.

Usa `TRUNCATE ... RESTART IDENTITY CASCADE` sobre todas las tablas en UNA sola
sentencia, y las tres cosas son necesarias: `RESTART IDENTITY` porque las suites
imprimen ids y comparar dos corridas es imposible si una arranca en
`id_socio=1` y la otra en 47; `CASCADE` por las 70 foreign keys; y una sola
sentencia porque entre las tablas hay ciclos de FK y truncarlas de a una falla
igual.

**`escenario_demo.py`** — carga 4 empleados, 3 socios, 5 patologías, 3
promociones y un cobro con descuento. Existe porque con la base vacía las
pantallas nuevas **no muestran nada** y no hay forma de ver si quedaron bien.

Se mantiene SEPARADO de las suites a propósito. Una suite que además deje datos
lindos para mirar termina siendo dos cosas a medias, y ninguna suite debería
depender de un escenario que alguien puede editar para que "se vea mejor".

Las contraseñas de esas cuentas están en
`backend/CONTRASEÑAS PARA TESTEO Y ACTUALIZADAS.txt`, junto con dos avisos que
costaron tiempo: que `vaciar_base.py` pisa la contraseña del dueño, y que a los
5 intentos fallidos la cuenta se **bloquea** devolviendo el mismo mensaje que
una contraseña equivocada —a propósito, para no revelar el estado de una cuenta
ajena, pero eso significa que desde afuera no se distingue "me equivoqué" de "ya
está bloqueada".

### `Promocion`: el caso inverso a `Consulta_Cruzada`

La §12 dejó las dos anotadas juntas, pero se resolvieron al revés, y el criterio
es el mismo que la masterclass del modelo de datos ya aplicaba: **una tabla se
justifica por uso o por estructura, nunca por intención.**

`Consulta_Cruzada` no tenía ninguna de las dos: era hoja *y* nadie la usaba. Se
borró de Neon y ahora el DDL y la base coinciden **nombre por nombre** —
comparado por nombre y no por cantidad, que es lo que la §11 no había hecho.

`Promocion` no tenía uso pero **sí** estructura: `Membresia.id_promocion` la
referencia. Borrarla habría sido además una migración sobre la tabla de plata.
Así que se le dio el uso que le faltaba.

**El reparto de permisos es el diseño, no un detalle:**

    Listar, vista previa                  ->  Seccion.COBROS  (Dueño + Recepcionista)
    Crear, editar, baja, reactivar, uso   ->  Accion.GESTION_PROMOCIONES  (solo Dueño)

Definir un descuento es una decisión de negocio; aplicarlo al cobrar es
operativo. Si listar exigiera la acción, el selector del mostrador le daría 403
al Recepcionista y la función quedaría sólo para quien menos atiende el
mostrador. Es el mismo reparto que ya regía la lista de precios
(`POST /cobros/tipos-membresia`).

**El cálculo vive en un solo lugar.** `precio_con_promo` está en
`routers/promociones.py` y `cobros.py` la **importa**. Por eso también existe
`GET /promociones/{id}/vista-previa`: la alternativa era mandarle el porcentaje
a cada app y que multiplicaran, y ahí la fórmula —con su piso en cero y su
redondeo— quedaba escrita en tres lugares. Es lo que garantiza que el número que
el mostrador ve antes de cobrar sea el que el backend registra.

Cuatro decisiones que quedaron en los comentarios:

- **`id_promocion` y `monto_manual` son excluyentes.** No hay respuesta obvia a
  "¿el descuento va sobre el monto manual o sobre el de lista?", y elegir una en
  silencio dejaría cobros que nadie puede explicar seis meses después.
- **`activo` y `vigente` son cosas distintas.** Una promo de enero sigue con
  `activo=true` en marzo. Reactivar una vencida la deja activa pero NO
  aplicable, y el backend lo avisa: extender una promoción es cambiarle la fecha
  de fin, una decisión explícita, no un efecto secundario de encenderla.
- **Editar no recalcula lo ya cobrado.** `precio_pactado` guarda el monto real.
  Mismo criterio que "nada se borra" del encabezado de `cobros.py`.
- **`Membresia` guarda CUÁL promo fue**, además del precio ya descontado. Con el
  precio solo, dentro de seis meses "$24.000 en vez de $30.000" no dice si fue
  un descuento, un error de tipeo o un precio pactado a mano.

### Lo que falta ahora

- **Mercado Pago**: lo único del backend que no se probó contra el servicio
  real, y no depende del código. Falta lo anotado en `backend/.env.example`: un
  `ACCESS_TOKEN`, el secreto del webhook y una **URL pública** — Mercado Pago no
  le puede avisar a `127.0.0.1` que un pago se acreditó. Mientras tanto hay un
  modo simulado que permite recorrer el flujo entero y que se niega a activarse
  si detecta un token real cargado.
- **La base no está en estado de entrega**: tiene el escenario de demo.
  `vaciar_base.py --si` la devuelve a las 6 filas.

---

## 14. Rendimiento: por qué la app se sentía lenta, y qué era en realidad

Esta sección existe porque el reporte fue "cambiar de panel tarda 2 segundos" y
la causa **no era el código de las pantallas ni Python**. Vale la pena escribir
el recorrido completo, porque el instinto —"Python es lento, habrá que
reescribirlo"— apuntaba al lugar equivocado.

### Los cuatro números que explican todo

Medidos contra la base real, no estimados:

    SELECT 1 en una conexión YA abierta ......  44 ms
    Abrir una conexión NUEVA (TLS + auth) .... 825 ms
    GET /socios (6 consultas) ................ 450 ms
    GET /personal ............................ 570 ms

La base está en Neon, región **sa-east-1 (São Paulo)**. Esos 44 ms son el
tiempo de ida y vuelta por cable: es un piso físico y ningún lenguaje lo baja.
Durante toda la request el proceso está **esperando un socket**, no calculando
— por eso reescribir esto en otro lenguaje daría exactamente los mismos 44 ms,
y por eso el GIL tampoco molesta: los hilos que agregamos después esperan red.

La conclusión que ordena todo el trabajo: **lo único que se puede hacer es
preguntar menos veces y no esperar la respuesta.**

### El bug que producía el síntoma exacto

El reporte tenía un detalle que era la pista entera:

> "si cambio de panel rápido carga al toque, pero si espero un rato vuelve la
> tardanza, y a veces aparece de la nada"

`database.py` creaba el engine con `pool_pre_ping=True` y nada más, o sea con
`pool_recycle=-1`: **las conexiones no se reciclan nunca**. Quedan en el pool
hasta que alguien del otro lado las cierra —Neon por inactividad, o el NAT del
router por no ver tráfico—. Cuando eso pasa, `pool_pre_ping` detecta la
conexión muerta y reconecta de forma transparente: la app no falla, pero esa
request paga los 825 ms. Y como cada conexión del pool muere en un momento
distinto, la lentitud aparecía "de la nada".

Tres piezas lo cierran, y cada una tapa un agujero distinto:

| Pieza | Qué evita |
|---|---|
| `pool_recycle=240` | reciclar cuando lo decidimos nosotros (entre requests) y no cuando lo decide la red (en medio de una) |
| keepalives de TCP | que el NAT dé por muerta una conexión ociosa; es el caso peor, porque está "viva" para nosotros y cortada del otro lado |
| latido cada 2 min | que Neon **suspenda el compute** del plan gratuito, cuyo despertar cuesta segundos |

El latido va en un hilo daemon y no en una tarea async: SQLAlchemy acá es
síncrono, y meterlo en el event loop lo bloquearía durante el RTT.

Después de esto los tiempos pasaron de erráticos a **estables** (min ≈ max),
que es la señal de que ya no se reconecta.

### Menos viajes: dos N+1 que costaban más que todo lo demás

**`/usuarios`.** `roles_de_persona()` deriva el rol leyendo SEIS relaciones de
la Persona. Con carga perezosa eso es una consulta por relación **por fila**:

    8 cuentas -> 45 consultas -> 2,88 s

Con `selectinload` bajó a 0,54 s. Con 100 socios habrían sido 600 consultas.

**`/socios`.** Peor todavía: `_a_socio_out` hacía cuatro consultas por socio
(membresía vigente, teléfono principal, `persona.usuario`, `membresia.tipo`).
Se reescribió el listado en lote —número fijo de consultas, sin importar
cuántas filas— y se verificó que devuelve **exactamente lo mismo** comparando
los `model_dump()` de las dos implementaciones:

    uno por uno    14 consultas   0,68 s
    en lote         6 consultas   0,34 s

`_a_socio_out` se conservó para el socio de a uno (alta, edición, baja), donde
cuatro consultas están bien y el código se lee mejor. Los dos caminos comparten
`_estado_socio`, así que una regla de derivación no puede divergir.

### El cambio de arquitectura: la UI no espera a la red

Con todo lo anterior, un panel seguía tardando ~450 ms. La primera respuesta
fue un caché con TTL de 15 segundos, y **fue un error**: producía exactamente
la queja original. Dentro de la ventana era instantáneo; fuera de ella se
pagaban los 450 ms completos. Escondía el problema y encima lo volvía
impredecible — la misma acción tardaba distinto según cuánto habías tardado vos
en hacerla.

Lo que funciona es **servir-y-refrescar** (`stale-while-revalidate`): se
devuelve siempre lo que hay en caché al instante, aunque esté vencido, y si
está vencido se dispara un refresco en segundo plano. La pantalla nunca espera
a la red; en el peor caso muestra datos de hace un minuto y se corrige sola.

Encaja porque los datos de este sistema son de **lectura frecuente y escritura
rara**: la grilla de socios se mira cien veces por cada alta.

Dos detalles que no son opcionales:

- **Cualquier escritura invalida TODO el caché**, no sólo la ruta que tocó.
  Cobrar una membresía cambia `/socios`, `/cobros/socio/{id}`,
  `/dashboard/stats` y `/cobros/deudas` a la vez. Invalidar "sólo lo
  relacionado" exigiría un mapa de dependencias mantenido a mano, y el día que
  alguien agregue un endpoint y se olvide de anotarlo, la pantalla mostraría un
  dato viejo **después de cobrar** — el único momento en que eso es
  inaceptable. Además hay un contador de generación: un refresco en vuelo que
  termina después de una escritura descarta su resultado en vez de resucitar un
  dato viejo.
- **El logout tira el caché.** Las respuestas guardadas se trajeron con los
  permisos de la sesión que se cierra; sin ese borrado, un Recepcionista que
  entrara después del Dueño podría leer del caché algo que a él el backend le
  habría negado.

Y para que la PRIMERA visita también sea instantánea, el login dispara una
**precarga en paralelo** de las doce rutas que las pantallas van a pedir. En
serie serían más de tres segundos; en paralelo, lo que tarde la más lenta.

### El resultado

    seccion         1a vez      2a   tras 35s
    dashboard           9 ms    2 ms     3 ms
    recepcion           1 ms    1 ms     3 ms
    socios              3 ms    1 ms     2 ms
    personal            1 ms    1 ms     2 ms
    usuarios            3 ms    3 ms     4 ms
    TOTAL              19 ms    9 ms    18 ms

Recorrer los nueve paneles pasó de **4175 ms a 19 ms**, y el caso que fallaba
—esperar un rato y volver— también quedó instantáneo.

Recepción es el único con frescura corta (5 s) en vez de 30: es el panel del
mostrador y su valor es estar al día. Abre al instante igual.

### La cuarta copia de la matriz de permisos

Aparte del rendimiento, se encontró que `views/usuarios.py` tenía un
diccionario `PERMISOS_RESUMEN` escrito a mano: una **cuarta** copia de los
permisos, además de `app/permisos.py`, `backend/permisos.py` y `config.ts`.
`check_permisos.py` no la miraba porque no era una matriz sino una lista
suelta. Estaba mal para **los cuatro roles**:

| Rol | Decía | Realidad |
|---|---|---|
| Recepcionista | omitía Usuarios, Rutinas, Nutrición, Personal y Recepción; decía Actividades | tiene las cinco primeras; Actividades no |
| Entrenador | Dashboard, Asistencia, Actividades | ninguna de las tres |
| Nutricionista | Dashboard | no la ve |
| Dueño | faltaba Recepción | la ve |

El comentario viejo decía "si las dos se contradicen, manda el backend". Es
cierto, pero no alcanza: esa tarjeta existe para **explicarle** a alguien qué
puede hacer cada rol, y una explicación equivocada es peor que ninguna — manda
a discutir con la app en vez de leerla.

Ahora se **deriva de la matriz** y marca con `*` las secciones de sólo lectura,
porque "ve Personal" y "puede tocar Personal" no son lo mismo. No hay nada que
sincronizar: el problema se eliminó de raíz en vez de agregarle un chequeo.

### Y las reglas de FILA en Usuarios

La vista de Flet dibujaba los tres botones de acción en **todas** las filas,
incluida la del Dueño —que es la primera de la grilla—. El Recepcionista
apretaba, el backend le devolvía 403 (correctamente: `_validar_jerarquia`) y se
iba con la idea de que no podía modificar nada. Podía: todas las demás.

La PWA ya tenía los dos guards (`esCuentaDeMayorJerarquia`,
`esCuentaPropiaRestringida`). Flet no: otra asimetría entre gemelas. Se copió
la misma decisión, omitiendo los botones y diciendo el motivo en su lugar,
porque una celda vacía se lee como un error de la app.

### Dónde está el límite real

Los 44 ms de RTT siguen ahí; lo que cambió es que nada espera por ellos. Si
alguna vez hace falta que la primera carga tras un arranque en frío también sea
instantánea, la única palanca que queda es **acercar la base**: un Postgres
local en el gimnasio baja el RTT a ~1 ms. Eso ya estaba contemplado desde el
principio — el docstring de `database.py` dice que ese cambio no toca una línea
de código, sólo `DATABASE_URL`.
