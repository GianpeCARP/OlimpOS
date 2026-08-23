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
