# OlimpOS — Guía del backend

Qué pidió el profesor, qué se construyó y **por qué cada decisión**. Está
escrita para poder explicar el sistema en una defensa oral sin haber
memorizado código.

---

## 1. La consigna, en una frase

> Un solo backend en FastAPI, con la base en Neon, que alimente a las **dos**
> aplicaciones (la PWA de los socios y la app de escritorio del personal), con
> el alta de usuarios controlada por el gimnasio.

El material del profesor son dos documentos y un proyecto de referencia
(`Proyeto-Python/PERAZZO/`, **solo lectura**):

| Documento | Tema |
|---|---|
| `Ingreso y creación de usuarios.docx` | Modelo de datos, bootstrapping, alta de usuarios |
| `Manual OlimpOS.docx` | Arquitectura: routers, capas, HTTP/JSON |

---

## 2. Las ocho normas del profesor, y cómo se cumplen

### 2.1. Un solo backend para las dos apps

> *"Aunque tengamos dos aplicaciones frontend distintas, ambas deben
> conectarse a la misma API y la misma base de datos."*

```
                        ┌──→ PWA React      (navegador)
Neon ←── backend/ ←─────┤
  (Postgres)   FastAPI  └──→ App Flet       (escritorio)
```

**Por qué importa:** si hubiera un backend por app, la lógica de negocio
estaría escrita dos veces. Dos veces los bugs, y datos que se desincronizan.
El Capítulo 1 del manual lo explica con la analogía de la cocina y los dos
salones: una cocina puede servir a varios salones sin cambiar las recetas.

### 2.2. Separar autenticación de datos personales

Es el punto que más se pregunta. **Son tres niveles:**

| Tabla | Qué guarda |
|---|---|
| `Usuario` | **Solo acceso**: username, password_hash, intentos_fallidos, bloqueado |
| `Persona` | Datos personales: nombre, DNI, dirección, contacto de emergencia |
| `Socio` / `Empleado` / `Dueno` | Lo propio de cada función |

`Usuario` **no tiene ni un dato personal**. Se llama *Separación de
Responsabilidades*.

**Por qué:** la tabla que se consulta en cada login queda chica y rápida. Y
sobre todo, permite que las tres cosas existan por separado:

- Un socio que paga en el mostrador y **nunca baja la app** → tiene `Persona`
  y `Socio`, no tiene `Usuario`.
- Un empleado sin acceso al sistema → `Persona` y `Empleado`, sin `Usuario`.
- Una persona que es **socia y entrenadora a la vez** → una sola `Persona`,
  con filas en `Socio` y en `Empleado`. **Sus datos no se duplican.**

**Desvío deliberado del profesor:** en su código, el DNI es la clave primaria
de todo. Acá la clave es `id_persona` (sustituta) y el DNI es único aparte.
Motivo: un DNI mal tipeado se corrige con un `UPDATE` de una columna, en vez
de arrastrar el cambio por las diez tablas que lo referencian.

### 2.3. El rol no es una columna

En el proyecto del profesor, `Usuario` tiene una columna `rol`. Acá **no
existe**: el rol se *deriva* de en qué tablas aparece la persona.

```
¿Hay fila en Dueno?          → rol "dueno"
¿Hay fila en Socio?          → rol "socio"
¿Hay fila en Entrenador?     → rol "entrenador"
...
```

Lo hace `roles_de_persona()` en `models.py`.

**Por qué:** con una columna, el rol y la realidad pueden contradecirse — dice
`ENTRENADOR` pero no hay ninguna fila en `Entrenador`. Derivándolo, esa
contradicción es imposible.

**Devuelve una lista, no un string**, porque los roles se acumulan: el dueño
que además entrena tiene `['dueno', 'socio']`.

**El costo, y cómo se resuelve:** derivar en cada request costaría cinco JOINs
por pedido. Se resuelve **una sola vez en el login** y el resultado viaja
firmado dentro del token. El contrato de la API queda idéntico al del profesor
(devuelve `roles`); lo que cambia es de dónde sale el dato.

> **Caso especial:** un **Profesor** es empleado pero **no tiene rol de
> sesión** — da clases, no usa el sistema. El alta no le crea cuenta aunque se
> pida, y avisa por qué.

### 2.4. Bootstrapping: el sistema se configura solo

> *"El sistema debe ser lo suficientemente inteligente para configurarse a sí
> mismo y permitir la entrada del propietario sin intervención de un
> programador."*

Al arrancar (`lifespan` en `main.py`):

1. `Base.metadata.create_all()` — crea tablas que falten.
2. `ejecutar_seeder()` — se asegura de que exista un dueño con cuenta.

El seeder es **idempotente**: si ya hay un dueño con cuenta, no hace nada. Por
eso puede correr en cada arranque sin condicionales.

**Detalle fino:** la pregunta no es *"¿hay algún usuario?"* sino *"¿hay algún
**dueño con cuenta**?"*. Podría haber diez recepcionistas y seguir sin haber
nadie capaz de administrar el sistema.

**Desvío:** el profesor crea las tablas desde los modelos. Acá manda
`Proyecto/db/schema.sql` (35 tablas, normalizadas a 3FN, parte de la entrega
académica) y los modelos lo *mapean*. Si los modelos definieran el esquema,
podrían divergir del diagrama entregado sin que nadie se entere.

### 2.5. Credenciales iniciales en `.env`

> *"Nunca hardcodees un usuario como admin@gym.com y clave '12345'. Si el
> código fuente se filtra, cualquier persona tendría la llave maestra."*

Todo lo sensible vive en `backend/.env`, que **no se sube** (lo bloquea el
`.gitignore`). El repo tiene `.env.example`, que documenta **qué** variables
hacen falta sin filtrar **ninguna**.

### 2.6. El cambio de contraseña obligatorio

**Es el mecanismo que más se pregunta.** Los pasos:

1. La cuenta nace con `debe_cambiar_password = true`.
2. En `POST /login`, si esa bandera está en `true`, el backend verifica la
   contraseña y **NO emite token**. Devuelve solo
   `{"debe_cambiar_password": true}`.
3. El frontend manda a la pantalla de cambio.
4. `POST /cambiar-password` es **público** —quien lo necesita todavía no tiene
   token— pero revalida la contraseña actual antes de aplicar el cambio.
5. Al terminar vuelve al login. **Hay que ingresar de nuevo.**

**La clave conceptual:** el backend confirma que la contraseña es correcta y
*aun así* se niega a abrir la sesión. No es el frontend el que "decide"
mostrar otra pantalla — es que no hay sesión que mostrar.

**Por qué re-loguearse en vez de entrar directo:** así el primer uso de la
contraseña nueva es un login normal y queda probada antes de que nadie dependa
de ella.

**Un solo mecanismo para tres casos:** el dueño inicial (seeder), cada cuenta
nueva creada por el personal, y cada reseteo hecho por un admin. Un solo
camino significa un solo flujo que mantener.

> Para implementarlo hubo que **agregar la columna `debe_cambiar_password`** a
> `Usuario`: el esquema v5 no la tenía. Está en `schema.sql` (para bases
> nuevas) y en `db/migrations/001_...sql` (para la de Neon, que ya existía).

### 2.7. Registro por invitación — sin botón "Registrarse"

> *"La regla de oro para sistemas internos de administración es que no debe
> existir un botón 'Registrarse' en la pantalla de inicio."*

El flujo que pide la consigna:

1. La persona llega al mostrador y paga.
2. El personal la carga → el backend crea todo y **genera** usuario y
   contraseña temporal.
3. Se le entregan (dictadas, por mail o WhatsApp).
4. Primer ingreso → obligada a cambiarla.

**Por qué es mejor que el auto-registro** (el documento lo justifica):
- **Evita trabajo doble.** El personal ya tiene que cargar al socio al cobrar.
- **Seguridad.** Solo entra quien realmente pagó.
- **Experiencia.** El socio recibe un servicio llave en mano.

Se eliminó de la PWA: la pantalla `RegistroView`, la ruta `/registro`, la
constante `Routes.REGISTRO` y la acción del store. **Sacar solo el link no
alcanzaba** — dejando la ruta viva, escribir `/registro` en la barra seguía
abriendo la pantalla.

El alta ocurre en **una sola transacción**: `Persona → Teléfono → Socio →
Usuario`. Si falla el último paso se deshace todo. En un mostrador con gente
esperando, media alta a medio hacer es peor que ninguna.

### 2.8. Doble barrera de permisos

> *"El Frontend cuida la experiencia, ocultando lo que no corresponde ver; el
> Backend cuida la integridad, rechazando lo que no está permitido hacer, sin
> importar de dónde venga el pedido."* (Cap. 6.4)

- **Frontend** → esconde botones y secciones. Es **UX**.
- **Backend** → rechaza con **403**. Es **seguridad**.

Cualquiera con las devtools abiertas puede alterar el estado del navegador y
hacer aparecer un botón. Cuando lo apriete, el backend lo frena.

---

## 3. Lo que se hizo más allá de la consigna

| | Profesor | Este proyecto |
|---|---|---|
| Tablas | 10 | **35** |
| Roles | enum plano | matriz 5 roles × 16 secciones × 10 acciones |
| Auth web | token en el cuerpo | **cookie httpOnly + CSRF** |
| Cobros, Asistencia, Actividades | ❌ | parcial |

Los frontends ya tenían construidas pantallas (Cobros, Asistencia,
Actividades) que el alcance del profesor no cubre. Sin esos routers, esas
pantallas quedarían con datos falsos para siempre.

### 3.1. La matriz de permisos

Tres niveles y no dos: `NINGUNO`, `LECTURA`, `TOTAL`.

**Por qué hacen falta los tres:** un Entrenador tiene que poder **consultar**
la dieta de un socio (para no contradecirla con la rutina) sin poder
gestionarla. Eso no es ni acceso total ni acceso nulo.

Y las **acciones** van aparte de las secciones: el Recepcionista entra a
Personal (LECTURA) pero no puede dar de alta a nadie. Son dos permisos
distintos sobre la misma pantalla.

`permisos.py` es **espejo** de `config.ts` de la PWA. Como desincronizarse es
silencioso (un color mal copiado se ve, un permiso mal copiado no), hay un
verificador: **`python check_permisos.py`** compara las 800 celdas y falla si
difieren.

### 3.2. Seguridad web: cookie httpOnly + CSRF

**El problema del token en JavaScript:** cualquier token que el código pueda
leer, un script inyectado (XSS) también puede leerlo y mandárselo a otro
servidor.

**La solución:** la sesión viaja en una cookie `httpOnly` — el navegador la
manda sola, pero JavaScript **no puede leerla**. Ni un XSS se la lleva.

**El problema que eso crea:** el navegador manda las cookies *siempre*,
incluso cuando el pedido lo origina otro sitio. Eso es **CSRF**: una web
maliciosa hace un POST a OlimpOS y el navegador adjunta tu sesión.

**La defensa (doble envío):** además de la cookie de sesión se emite una
cookie CSRF **legible**. La app la lee y la copia al header `X-CSRF-Token`. El
sitio atacante puede hacer que el navegador *mande* cookies, pero no puede
*leerlas* (política de mismo origen), así que no puede armar el header.

**Modo dual, y no es inconsistencia:**

| Cliente | Mecanismo | Por qué |
|---|---|---|
| PWA (navegador) | cookie httpOnly + CSRF | tiene XSS y CSRF |
| Flet (escritorio) | `Authorization: Bearer` | no es navegador: no tiene ninguno de los dos |

Flet declara `X-Client-Type: escritorio` y recibe el token en el cuerpo.
Darle cookies no agregaría seguridad, solo ceremonia.

### 3.3. El proxy de Vite

**Síntoma:** después de migrar a cookies, el login parecía funcionar pero un
F5 deslogueaba, y `/me` daba 401.

**Causa:** la página estaba en `localhost:5173` y la API en `127.0.0.1:8000`.
Son la misma máquina pero **para el navegador son hosts distintos**. La cookie
quedaba guardada bajo `127.0.0.1` y la página, en `localhost`, no la veía.
Encima `SameSite=lax` le prohibía mandarla entre sitios distintos.

**Solución:** un proxy en `vite.config.ts`. La app le pega a `/api/...` —mismo
origen— y Vite reenvía al backend. La cookie es de `localhost`, todo funciona,
y CORS desaparece porque ya no hay pedidos cross-origin.

**No es una muleta:** en producción la PWA y la API van a estar bajo el mismo
dominio. El proxy hace que desarrollo se parezca a producción.

### 3.4. Reglas de fila en Usuarios

Dos reglas que la matriz **no puede** expresar, porque no dependen del rol de
quien pide sino de **qué fila** toca:

1. **Nadie fuera del Dueño edita o desactiva su propia cuenta.** Si no, alguien
   puede desactivarse sin que nadie lo vea venir.
2. **Solo un Dueño opera sobre la cuenta de un Dueño.** Sin esto, un
   recepcionista podía resetearle la contraseña al dueño, **leer la clave
   generada en pantalla** y entrar con control total. Escalación de privilegios
   con tres clicks.

**Asimetría importante:** resetearse la *propia* contraseña **sí** se permite
(regla 1 no aplica) — es lo que hace cualquier sistema real. Pero resetear la
de alguien de mayor jerarquía **no** (regla 2 sí aplica).

### 3.5. Reglas de negocio en Cobros

- **El monto lo calcula el backend.** El pedido manda el *plan*, no el precio.
  Si viniera del cliente, cualquiera cobraría $1 una membresía de $30.000.
- **Nada se borra.** Anular un pago le pone `CANCELADO` + fecha. Un registro
  contable que desaparece es un agujero en la caja.
- **Pagar por adelantado no come los días restantes**: el período nuevo
  arranca cuando vence el anterior.
- **El comprobante es único** — frena el doble click.
- **"Al día" son dos condiciones**: membresía vigente **y** sin deudas.

---

## 4. Arquitectura en capas

```
Vista        →  Estado      →  Cliente HTTP   →  Backend
(dibuja)        (traduce)      (habla HTTP)      (decide)
```

| Capa | PWA | Flet |
|---|---|---|
| Vista | `views/*.tsx` | `app/views/*.py` |
| Estado | `store/*.ts` | `app/state.py` |
| HTTP | `services/api.ts` | `app/api_client.py` |

**La regla:** ninguna vista sabe que existe HTTP. Pide datos a la capa de
estado y recibe algo listo para dibujar.

**Por qué:** el día que cambie la URL de la API —y va a cambiar— se toca **un
archivo**, no las diez pantallas.

### El backend por dentro

```
backend/
├── main.py            app, CORS, middleware CSRF, lifespan, routers
├── database.py        engine, sesión por request
├── models.py          las tablas como clases + roles_de_persona()
├── schemas.py         qué entra y qué sale de la API
├── auth.py            bcrypt + JWT + generación de credenciales
├── security.py        obtener_sesion, requiere_seccion, requiere_accion
├── permisos.py        la matriz (espejo de config.ts)
├── cookies.py         cookies de sesión
├── csrf.py            middleware anti-CSRF
├── notificaciones.py  envío de credenciales por mail
├── seeder.py          bootstrapping del dueño
└── routers/           un archivo por tema
```

**`models` vs `schemas`:** `models` describe cómo se **guarda**; `schemas`
describe cómo **viaja**. El caso que lo explica solo: `Usuario` tiene
`password_hash`, y ese campo **no está declarado** en ningún schema de salida.
Como no existe en el molde, no puede filtrarse ni por olvido.

**`Depends`:** el mecanismo de FastAPI que resuelve cosas *antes* de ejecutar
el endpoint. Al escribir `sesion: Sesion = Depends(requiere_seccion(...))`, la
barrera ya está aplicada — un endpoint no puede "olvidarse" de chequear
permisos a mitad de camino.

**Por qué el CSRF es middleware y no dependencia:** una dependencia hay que
acordarse de ponerla en cada endpoint nuevo. Un middleware protege **todo por
defecto** y no hay forma de saltearlo por descuido.

---

## 5. Endpoints (33)

| Router | Endpoints |
|---|---|
| **auth** | `POST /login`, `POST /cambiar-password`, `POST /logout`, `GET /me` |
| **socios** | `GET /socios`, `POST /socios` (alta por invitación) |
| **personal** | `GET /personal`, `POST /personal` |
| **rutinas** | catálogo de ejercicios, CRUD de rutinas, asignación |
| **nutricion** | dietas, comidas, asignación |
| **cobros** | planes, estado de cuenta, cobrar, anular, deudas |
| **usuarios** | listar, crear cuenta, resetear, desbloquear, activar |

---

## 6. Cómo levantar todo

**Terminal 1 — backend:**
```powershell
cd D:\OlimpOs\backend
.\.venv\Scripts\Activate.ps1
uvicorn main:app --reload
```

**Terminal 2 — PWA:**
```powershell
cd D:\OlimpOs\Proyecto\src\frontend
npm run dev
```

Entrar por **`http://localhost:5173`** — siempre `localhost`, nunca
`127.0.0.1`, o las cookies dejan de funcionar.

Documentación interactiva de la API: `http://127.0.0.1:8000/docs`

### Dos cosas que hacen perder tiempo

**Un proceso no relee los archivos.** Carga el código al arrancar y se queda
con esa copia. Si editás el backend sin reiniciarlo, seguís ejecutando lo
viejo. `--reload` lo hace solo, pero a veces falla.

**Dos procesos no pueden usar el mismo puerto.** Si el 8000 está ocupado por
uno viejo, el nuevo muere y sigue contestando el anterior — con código
desactualizado. Para verlo y matarlo:

```powershell
netstat -ano | findstr ":8000"
taskkill /PID <numero> /F
```

---

## 7. Verificaciones

```powershell
python -c "import main"      # ejecuta: detecta imports faltantes
python check_db.py           # conexión a Neon + esquema
python check_permisos.py     # la matriz vs config.ts
```

> `compileall` **no alcanza**: compila pero no ejecuta, así que un import
> faltante pasa desapercibido. Pasó con `EmailStr`.

---

## 8. Lo que falta

- Routers de **Asistencia**, **Actividades** y **Dashboard**
- **Portal del socio** (7 pantallas con datos propios)
- Conectar las pantallas de gestión de Flet y la PWA a estos endpoints
- Vaciar la base para la entrega final

---

## 9. Las cinco ideas para la defensa oral

1. **Una API, dos frontends.** Toda regla de negocio vive en el servidor.
2. **`Usuario` guarda solo credenciales.** Los datos personales están en
   `Persona`, y las funciones (socio, empleado) en sus propias tablas.
3. **El rol se deriva, no se guarda.** Se resuelve en el login y viaja firmado
   en el token.
4. **Toda cuenta nace con contraseña temporal.** El login la verifica y aun así
   niega el token hasta que la persona defina la suya.
5. **El frontend esconde, el backend rechaza.** Los permisos están en los dos
   lados, pero solo uno es la barrera real.
