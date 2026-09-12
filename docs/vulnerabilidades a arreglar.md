# Vulnerabilidades a arreglar — OlimpOS

Auditoría de seguridad del sistema completo: **backend** (FastAPI + Neon),
**PWA** (React) y **app de escritorio** (Flet). Combina análisis **estático**
(lectura de código) con análisis **dinámico** (ataques reales contra el backend
corriendo en `127.0.0.1:8000`, base en estado *demo*).

> **Alcance y método.** Cada hallazgo dice cómo se verificó (`estático` /
> `dinámico`) y trae la reproducción. Todo ataque dinámico se lanzó con un
> harness propio (`urllib` + `python-jose`) autenticándose como cada uno de los
> cinco roles. **Nada de lo listado está resuelto acá**: este archivo sólo
> anota. Las medidas de infraestructura "de siempre" (HTTPS, Neon, cabeceras)
> están en su propia sección al final.

> **Fecha:** 2026-08-28 · **Backend auditado:** 138 endpoints en 15 routers ·
> **Estado de la base durante las pruebas:** demo (~70 filas).

---

## Resumen ejecutivo

| # | Severidad | Hallazgo | Verificación |
|---|---|---|---|
| V-01 | 🔴 Crítica (condicional) | Membresía gratis: un socio autoconfirma su propio pago en modo simulado | dinámico |
| V-02 | 🟠 Alta | Sin rate-limiting + bloqueo por 5 intentos + usernames enumerables y derivables = DoS por bloqueo de cuentas | dinámico + estático |
| V-03 | 🟡 Media | Enumeración de usuarios por canal lateral de **tiempo** (bcrypt) | dinámico |
| V-04 | 🟡 Media | `/cambiar-password` (público) también incrementa el contador de bloqueo | estático |
| V-05 | 🟡 Media-baja | Montos `Infinity`/`NaN` → HTTP 500 sin sanear | dinámico |
| V-06 | 🟢 Baja | Cobro de `$0,00` aceptable vía `monto_manual` diminuto | dinámico |
| V-07 | 🟢 Baja | Promoción de monto fijo sin tope superior | dinámico |
| V-08 | 🟢 Baja | Sin revocación de JWT: token robado vale hasta 8 h, `logout` no lo invalida | estático |
| V-09 | 🟢 Baja | Política de contraseñas débil (mín. 8, sin complejidad ni chequeo de filtradas) | estático |
| V-10 | 🟢 Baja / diseño | Entrenador y Nutricionista leen el historial médico y el DNI de **todos** los socios, no sólo de los suyos | dinámico |
| V-11 | 🔵 Endurecimiento | El header `X-Client-Type` (elegido por el cliente) decide cookie-httponly vs token-en-cuerpo | estático |

Y una sección aparte de **medidas de infraestructura obvias** (HTTPS, cabeceras,
`/docs` público, Neon, etc.).

> **Lo que se probó y resultó SÓLIDO** está documentado al final, en
> "Superficie verificada como robusta". Importa tanto como la lista de arriba:
> dice qué vectores clásicos ya no hace falta re-auditar (forja de JWT, IDOR,
> escalada de privilegios, CSRF, CORS, inyección SQL, mass-assignment).

---

## 🔴 V-01 — Membresía gratis: el socio autoconfirma su propio pago (modo simulado)

- **Dónde:** `backend/routers/pagos_online.py` → `POST /portal/mi-cuota/pagar/{id_pago}/simular`
- **Verificación:** **dinámica** — reproducida de punta a punta.
- **Severidad:** Crítica **si** se despliega con `MP_MODO_SIMULADO=true`. En la
  instancia auditada **está activo ahora mismo** (`modo_simulado=True`,
  `MP_ACCESS_TOKEN` vacío).

**Qué pasa.** El endpoint de simulación existe para desarrollar sin cuenta de
Mercado Pago: acredita un pago "a mano". Sólo valida que el pago **sea del socio
que llama** — y eso lo cumple el propio socio con sus propios pagos. Así, sin
tocar Mercado Pago ni pagar un centavo, un socio:

1. `POST /portal/mi-cuota/pagar` → crea su propio `Pago` en `PENDIENTE`.
2. `POST /portal/mi-cuota/pagar/{id}/simular?aprobado=true` → lo marca
   `CONFIRMADO` y **le extiende la membresía**.

**Reproducción (token de `juan.perez`, socio):**

```
POST /portal/mi-cuota/pagar        {"id_tipo_membresia":1}
  -> 201  {"id_pago": 2, "monto": 30000.0, "simulado": true, ...}
POST /portal/mi-cuota/pagar/2/simular?aprobado=true
  -> 200  {"mensaje": "[SIMULADO] Pago 2 -> CONFIRMADO."}
GET  /portal/mi-cuota
  -> 200  {"tiene_membresia": true, "estado": "Activo",
           "fecha_vencimiento": "2026-10-27", ...}   <- membresía extendida sin pagar
```

**Por qué es grave y a la vez está semi-contenido.** El módulo `mercadopago.py`
se niega a activar el modo simulado si hay un `MP_ACCESS_TOKEN` real cargado
(`modo_simulado() = _simulado_pedido() and not MP_ACCESS_TOKEN`). O sea: **toda
la protección en producción depende de una sola variable de entorno**. El día
que alguien despliegue con la bandera puesta (o sin token), todos los socios
tienen membresías gratis. El endpoint no debería existir en un binario de
producción, no sólo apagarse por configuración.

**Nota adicional (estático):** el flujo del webhook real (`/webhooks/mercadopago`)
está **bien** diseñado —relee monto y estado con el token propio, verifica firma
HMAC, es idempotente por `numero_comprobante UNIQUE`—. El problema es
exclusivamente el atajo de simulación.

---

## 🟠 V-02 — DoS por bloqueo de cuentas: sin rate-limiting, con usernames enumerables y predecibles

- **Dónde:** `backend/routers/auth_router.py` (`login`, `_registrar_intento_fallido`,
  `MAX_INTENTOS_FALLIDOS = 5`), `backend/auth.py` (`generar_username`).
- **Verificación:** **dinámica** (ausencia de rate-limit) + **estática** (lógica de bloqueo y derivación de usernames).
- **Severidad:** Alta.

**Las tres piezas que, juntas, arman el ataque:**

1. **No hay ningún límite de tasa por IP.** 20 intentos de login en 3,77 s, todos
   procesados, **ningún 429**:
   ```
   20 intentos a un usuario inexistente -> {401: 20}   (sin 429)
   ```
2. **A los 5 intentos fallidos la cuenta se bloquea** (`bloqueado = True`).
3. **Los usernames son enumerables** (ver V-03, canal de tiempo) **y
   derivables**: `generar_username()` produce `nombre.apellido`
   determinísticamente. Conociendo el nombre de un empleado (ingeniería social,
   redes, la propia web del gimnasio) se adivina su usuario.

**Consecuencia.** Un atacante manda 5 contraseñas incorrectas por cuenta y
**bloquea a todo el personal**, incluido el **único Dueño**. La recuperación no
tiene camino desde la app: hay que entrar a la base a mano
(`UPDATE "Usuario" SET bloqueado=false ...`, documentado en las notas de
testeo). Es decir: **una persona externa puede dejar al gimnasio sin acceso
administrativo con ~40 requests**, y el desbloqueo exige acceso a Postgres.

**Reproducción del hueco de rate-limit** (`audit/timing_rate.py`, bloque A). No
se ejecutó el bloqueo real contra cuentas de la demo para no dejarlas
inutilizables; el vector se deduce del código de bloqueo + la ausencia de 429 +
la derivación determinística del username.

---

## 🟡 V-03 — Enumeración de usuarios por canal lateral de tiempo

- **Dónde:** `backend/routers/auth_router.py` → `login()` (y `cambiar_password()`).
- **Verificación:** **dinámica** — medido.
- **Severidad:** Media.

El código se esfuerza —bien— en devolver **un único mensaje** ("Usuario o
contraseña incorrectos") para usuario inexistente, inactivo, bloqueado o
contraseña mala, justamente *"para no revelar el estado de una cuenta ajena"*.
Pero el **tiempo de respuesta lo delata**: `verificar_password()` (bcrypt, ~200 ms)
sólo corre **si el usuario existe**. Si no existe, corta antes.

**Medición (mediana de varias muestras):**

```
usuario INEXISTENTE + password cualquiera :  178 ms   (no llega a bcrypt)
usuario EXISTE       + password incorrecta :  413 ms   (corre bcrypt)
ratio ≈ 2,3x  -> distinguible sin ambigüedad
```

Con eso, un atacante enumera qué usuarios existen a pesar del mensaje unificado
—y alimenta directamente el V-02—. La defensa del "mensaje único" queda anulada
por el tiempo. *(Dirección de arreglo, sin implementar: correr un bcrypt "dummy"
contra un hash fijo cuando el usuario no existe, para igualar los tiempos.)*

---

## 🟡 V-04 — `/cambiar-password` (público) también puede bloquear cuentas

- **Dónde:** `backend/routers/auth_router.py` → `cambiar_password()` llama a
  `_registrar_intento_fallido()`.
- **Verificación:** **estática**.
- **Severidad:** Media (amplía la superficie de V-02).

`/cambiar-password` es público (tiene que serlo: quien lo usa todavía no tiene
token). Ante `password_actual` incorrecta, incrementa `intentos_fallidos` igual
que el login. Así el atacante tiene **un segundo endpoint** para gastar el cupo
de bloqueo de cualquier cuenta, sin siquiera pasar por `/login`. Mismo mensaje
único, mismo canal de tiempo (bcrypt), misma falta de rate-limit.

---

## 🟡 V-05 — Montos `Infinity` / `NaN` provocan HTTP 500

- **Dónde:** `backend/routers/cobros.py` (validación de `CobrarRequest.monto_manual`).
- **Verificación:** **dinámica**.
- **Severidad:** Media-baja (robustez / DoS puntual).

`monto_manual` usa `Field(gt=0)`, que **no** atrapa `Infinity` (`inf > 0` es
`True`) ni `NaN`. El JSON de Python acepta los literales no estándar `Infinity`
y `NaN`, que pasan la validación y revientan más abajo (probablemente al escribir
un `NUMERIC` en Postgres):

```
POST /cobros  {"...","monto_manual": 1e309}   -> 500 Internal Server Error
POST /cobros  {"...","monto_manual": NaN}     -> 500 Internal Server Error
```

No filtra traza al cliente (bien: sólo "Internal Server Error"), pero es entrada
no saneada que llega hasta la base y tira la request. *(Dirección: rechazar
`inf`/`nan` en el schema con un validador `math.isfinite`.)*

---

## 🟢 V-06 — Cobro de `$0,00` aceptable vía `monto_manual` diminuto

- **Dónde:** `backend/routers/cobros.py`.
- **Verificación:** **dinámica**.
- **Severidad:** Baja (lógica de negocio).

`monto_manual = 0.0001` pasa `gt=0` y, al redondear a dos decimales, queda un
pago de **`$0,00`** perfectamente registrado y una membresía activada:

```
POST /cobros  {"...","monto_manual": 0.0001}  -> 201  {"pago": {"monto": 0.0, ...}}
```

Requiere el permiso de Dueño (ver V-06-bis abajo), así que no es escalable por un
socio, pero deja un cobro contable de cero que "parece" cobrado. *(Dirección: un
piso realista, p. ej. `ge=1`, o redondear-luego-validar.)*

**V-06-bis (control que SÍ funciona):** un Recepcionista **no** puede usar
`monto_manual` — el backend responde `403 "Solo el dueño puede cobrar un monto
distinto al del plan"`. Verificado dinámicamente. Bien.

---

## 🟢 V-07 — Promoción de monto fijo sin tope superior

- **Dónde:** `backend/schemas.py` → `PromocionBase.monto_fijo_descuento = Field(gt=0)`.
- **Verificación:** **dinámica**.
- **Severidad:** Baja.

```
POST /promociones {"...","monto_fijo_descuento": 99999999}  -> 201 (creada)
```

No hay tope; un descuento fijo mayor que cualquier plan deja el precio en `$0`
(el cálculo tiene piso en cero, así que **no** produce montos negativos —eso está
bien—). Sólo la gestiona el Dueño. Riesgo bajo, pero conviene un límite de
cordura. *(El `porcentaje_descuento` sí está acotado: `gt=0, le=100`, verificado
—150 y −10 dan 422.)*

---

## 🟢 V-08 — Sin revocación de JWT: el token vive hasta expirar

- **Dónde:** `backend/auth.py` (JWT sin `jti`), `backend/routers/auth_router.py` → `logout()`.
- **Verificación:** **estática** (es el modelo sin estado, documentado en el código).
- **Severidad:** Baja (compromiso de diseño, ya asumido).

El JWT es sin estado y dura 8 h. `logout()` sólo borra las cookies; **el token
en sí sigue válido**. No hay lista de revocación (`jti`/blocklist). La única
forma de cortar una sesión en el acto es **desactivar la cuenta**
(`Usuario.activo = false`), que `obtener_sesion` sí chequea en cada request
(verificado: relee el usuario de la base). Consecuencia: un token filtrado —por
ejemplo el `Bearer` de Flet viajando por HTTP en la LAN, ver sección de
infraestructura— es reutilizable hasta 8 h desde otra máquina y no hay botón que
lo mate salvo desactivar a la persona. Está anotado como *trade-off* en los
docstrings; se lista para que la decisión sea consciente.

---

## 🟢 V-09 — Política de contraseñas débil

- **Dónde:** `backend/schemas.py` → `CambiarPasswordRequest.password_nueva = Field(min_length=8)`.
- **Verificación:** **estática**.
- **Severidad:** Baja.

La única regla es **mínimo 8 caracteres** + "distinta de la actual". No hay
complejidad, ni longitud máxima razonable, ni chequeo contra contraseñas
comunes/filtradas. `password123` o `12345678` son aceptadas. Sumado a la falta
de rate-limit (V-02), habilita adivinación dirigida. Además, bcrypt **trunca a
72 bytes** (documentado en `auth.py`): dos contraseñas que compartan los
primeros 72 bytes son equivalentes (irrelevante en la práctica, se anota por
completitud).

---

## 🟢 V-10 — Entrenador y Nutricionista ven el historial médico y el DNI de TODOS los socios

- **Dónde:** `backend/permisos.py` (matriz), `routers/patologias.py`, `routers/socios.py`.
- **Verificación:** **dinámica**.
- **Severidad:** Baja / decisión de diseño — se anota para revisitar a escala.

El permiso es **por sección**, no acotado a "los socios a cargo". Verificado:
`ana.gomez` (entrenadora de Juan y Lucía) lee la patología de **Nico**, que no es
su alumno:

```
entren GET /socios/3/patologias  -> 200  [{"nombre":"Asma", "observaciones":"Usa inhalador..."}]
entren GET /socios              -> 200  [ ... DNI de todos los socios ... ]
```

Para un gimnasio chico es una decisión explícita y documentada (una rodilla
operada cambia la rutina; el Recepcionista, en cambio, **no** tiene la acción, lo
cual está bien y se verificó: `403`). Pero es dato médico sensible + PII (DNI)
accesible a **cualquier** entrenador/nutricionista, sin vínculo con el socio. A
escala (varias sedes, decenas de profesores) conviene acotar por asignación.

---

## 🔵 V-11 — El cliente elige su propio nivel de protección (`X-Client-Type`)

- **Dónde:** `backend/routers/auth_router.py` → `login()`.
- **Verificación:** **estática**.
- **Severidad:** Endurecimiento (no explotable directo hoy).

Que la sesión viaje como **cookie httponly** (segura contra XSS) o como **token
en el cuerpo** (legible por JS) lo decide un header que **manda el cliente**:
`X-Client-Type: escritorio`. La PWA nunca lo manda, así que hoy funciona; pero el
*mecanismo de seguridad se elige del lado del cliente*, no por política del
servidor. Si mañana el mismo origen web necesitara pedir el token en cuerpo por
error, o si un flujo de login malicioso lo forzara, se degrada la protección
httponly. *(Dirección: decidir el transporte por configuración de servidor / por
`Origin`, no por un header arbitrario.)*

---

# Superficie verificada como ROBUSTA (probado y pasó)

Esto se atacó activamente y **resistió**. Vale documentarlo: son los vectores que
no hace falta re-auditar.

| Vector | Prueba | Resultado |
|---|---|---|
| **Forja de JWT — `alg:none`** | Token `{"alg":"none"}` con `roles:["dueno"]` | `401` — rechazado |
| **Forja de JWT — secreto débil** | Firma con 10 secretos triviales (`secret`, `changeme`, `olimpos`, el default del `.env`…) | Ninguno entra |
| **JWT — manipular `roles`/`id_socio`/`sub`** | Reescribir el payload conservando la firma vieja | `401` — firma inválida |
| **Secreto JWT** | Entropía del `JWT_SECRET_KEY` | 86 chars, alta entropía, **no** default |
| **IDOR (lectura)** | `juan` pide `/socios/2`, `/cobros/socio/2`, `/socios/2/patologias`… | `403`/`404` en todos |
| **IDOR (escritura)** | `juan` cancela reservas/inscripciones/pagos ajenos por id | `404` (chequeo de propiedad — responde 404, no 403, para no confirmar existencia) |
| **Escalada de privilegios** | `recepcionista` resetea/desactiva/edita al **Dueño** | `403 "Solo un dueño puede operar sobre la cuenta de un dueño"` |
| **Regla de fila propia** | `recepcionista` se auto-desactiva | `403` |
| **Acciones sin permiso** | `recep` crea personal/promoción/tipo-membresía; `entren`/`nutri` fuera de su carril | `403` en todos |
| **CSRF** | POST con cookie de sesión, sin header / con header falso | `403` en ambos; con header correcto `200` |
| **CORS** | `Origin: http://evil.com` y `null` | **No** se refleja `Access-Control-Allow-Origin`; preflight de `evil.com` → `400` |
| **Webhook MP** | POST sin firma / con firma basura | Descartado (`"Firma inválida"`), no acredita |
| **Mass-assignment** | `juan` edita su perfil mandando `activo`, `id_socio`, `numero_socio`, `dni`, `objetivo` | Ignorados; nada cambió |
| **Inyección SQL** | `username = '; DROP TABLE "Usuario";--` y variantes | Tratado como literal (`401`); ORM parametrizado |
| **Path params** | `/socios/-1`, `/socios/99999999999999999999`, `/usuarios/abc`, traversal `/../` | `404`/`422`, sin fuga |
| **Congelamiento** | Pedir 3000 días / fecha pasada | `400` (tope de 90 días y mínimo de 7, del lado del servidor) |
| **Matriz de permisos** | `check_permisos.py` (3 copias: backend / Flet / config.ts) | Idénticas, exit 0 |
| **Secretos en git / bundle** | `git ls-files`, historial, `dist/`, `import.meta.env` | Ninguno filtrado; `.gitignore` correcto; sólo `VITE_API_URL=/api` llega al cliente |
| **Token en Flet** | Almacenamiento del `Bearer` | Sólo en variable de módulo, nunca a disco; `requests` con verificación TLS por defecto |
| **XSS en la PWA** | `dangerouslySetInnerHTML`, `innerHTML`, `eval` | No se usan en ningún lado |

---

# Medidas de seguridad "obvias" para web y entornos grandes

Cosas que **no** son bugs del código sino de **despliegue/infraestructura**, y
que hay que tener siempre presentes al llevar una app a la web y a un entorno
serio. Varias ya están anotadas en el propio código como pendientes de
producción.

### Transporte y red

- [ ] **HTTPS/TLS obligatorio.** Hoy backend en `http://127.0.0.1:8000` y Flet le
      pega por HTTP. Sobre la red, el `Authorization: Bearer` de Flet y las
      cookies de la PWA viajan **en texto plano**: cualquiera en el mismo WiFi
      los lee. En producción: TLS en todo, y la PWA + API bajo el **mismo
      dominio** (el proxy de Vite ya simula eso en dev).
- [ ] **`COOKIE_SECURE=true` en producción.** Hoy `false` (correcto para
      `http://localhost`, peligroso si se sube así). Sin `Secure`, la cookie de
      sesión se manda también por HTTP.
- [ ] **`SameSite`**: hoy `lax` (razonable). Evaluar `strict` según el flujo de
      links externos.

### Cabeceras de seguridad (hoy: **ninguna**)

Verificado dinámicamente — la respuesta sólo trae `content-type` y
`server: uvicorn`. Faltan:

- [ ] `Strict-Transport-Security` (HSTS)
- [ ] `Content-Security-Policy` (defensa en profundidad contra XSS)
- [ ] `X-Content-Type-Options: nosniff`
- [ ] `X-Frame-Options: DENY` / `frame-ancestors` (anti-clickjacking)
- [ ] `Referrer-Policy`
- [ ] `Permissions-Policy`
- [ ] Ocultar `Server: uvicorn` (divulga el software).

### Superficie expuesta

- [ ] **`/docs`, `/redoc` y `/openapi.json` son públicos** (verificado: 200 sin
      auth). Exponen el mapa completo de 138 endpoints a cualquiera. En
      producción: apagarlos o dejarlos detrás de autenticación.
- [ ] **Rate-limiting / WAF** en el borde (nginx, Cloudflare, slowapi…): hoy no
      hay ninguno (ver V-02).

### Base de datos (Neon)

- [ ] **`sslmode=require` ya está** en la cadena de conexión (bien: Neon rechaza
      conexiones sin cifrar).
- [ ] **Una sola credencial `neondb_owner`** para todo. En un entorno grande:
      usuario de aplicación con permisos mínimos (no `owner`), y separar
      lectura/escritura si aplica.
- [ ] **Rotación de credenciales** y del `JWT_SECRET_KEY` (rotarlo invalida todas
      las sesiones — tenerlo previsto).
- [ ] **Backups y punto de recuperación**: verificar la política de Neon; no hay
      evidencia en el repo de una estrategia de restore.
- [ ] **La base está en São Paulo (sa-east-1).** No es seguridad, pero el RTT de
      44 ms y el arranque en frío de 825 ms son relevantes para disponibilidad;
      la palanca (Postgres local) ya está contemplada en `database.py`.

### Operación / secretos

- [ ] **Gestión de secretos** fuera del `.env` en archivo plano para producción
      (vault, secrets manager). Hoy el `.env` está bien fuera de git, pero un
      `.env` en disco en el servidor sigue siendo un archivo a proteger.
- [ ] **SMTP y Mercado Pago**: cuando se carguen credenciales reales, que sea por
      el gestor de secretos, no en el `.env`.
- [ ] **Logs**: revisar que no se loguee PII ni el cuerpo de pagos. Hoy el
      webhook imprime a stdout el id de pago y el resultado (aceptable, pero
      revisar antes de centralizar logs).
- [ ] **Modo simulado de MP fuera del build de producción** (ver V-01): que la
      seguridad no dependa de una bandera de entorno.

---

## Anexo — Artefactos de prueba dejados en la base demo

Durante la auditoría dinámica se escribieron datos en la base *demo* que conviene
saber que están ahí (las pruebas de lectura y de escritura-bloqueada no dejan
rastro; estas sí):

- **`juan.perez`**: se le extendió la membresía sin pagar (prueba V-01, pago id 2,
  vence 2026-10-27) y quedó un cobro de `$0,00` (prueba V-06, pago id 3). Su
  contacto y su patología (Hipertensión) **se restauraron** al estado original.
- **Promoción "hack"** (id 4, monto fijo 99.999.999) creada en la prueba V-07.

Para volver la demo a un estado limpio: `pruebas/vaciar_base.py --si` y luego
`pruebas/escenario_demo.py` (desde `backend/`).

---

## Cómo se reprodujo (harness)

Los scripts de ataque quedaron en el scratchpad de la sesión
(`.../scratchpad/audit/`): `harness.py` (cliente + login por rol),
`jwt_attacks.py`, `idor.py`, `privesc.py`, `web_attacks.py` (CSRF/CORS/webhook),
`timing_rate.py`, `input_attacks.py`. Todos corren con el Python del venv del
backend (`backend/.venv/Scripts/python.exe`) contra el backend levantado.
