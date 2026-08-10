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
