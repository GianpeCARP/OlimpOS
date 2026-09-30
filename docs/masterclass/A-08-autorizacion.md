# A-08 · Autorización

*Piso del capítulo: la línea que levanta el 403.*

[Autenticación](A-07-autenticacion.md) responde **quién** pregunta: la identidad sale de un
token firmado y el usuario se relee en cada pedido. Este capítulo responde la pregunta
siguiente, **qué puede pedir**. Son dos problemas distintos y conviene no mezclarlos: un
socio perfectamente autenticado no puede ver la facturación, y un recepcionista con su
sesión en regla no puede abrir el historial médico de nadie.

Todo lo que este sistema decide sobre permisos sale de **una sola tabla**, copiada en tres
lugares y controlada por un verificador. El capítulo explica esa tabla, cómo se consulta,
por qué está triplicada, y los tres principios que la aplican: el frontend esconde y el
backend rechaza, un control prohibido se omite en vez de deshabilitarse, y lo que es de una
sola persona no se ve desde afuera.

---

## Matriz de permisos

### El problema de origen

Con seis roles y una veintena de pantallas, la forma ingenua de controlar el acceso es
escribir la regla adentro de cada endpoint:

```python
if "dueno" in roles or "recepcionista" in roles:
    ...
```

Funciona, y no escala. Las reglas quedan repartidas en cientos de líneas, nadie puede leer
de una vez qué puede hacer un entrenador, y cambiar un permiso obliga a buscar cada lugar
donde se lo nombró —y rezar por no olvidar ninguno—.

La respuesta es separar **la regla** de **quien la aplica**. Las reglas van en una tabla de
datos: para cada rol, qué nivel tiene en cada sección y qué acciones puede ejecutar. Los
endpoints ya no deciden: preguntan a la tabla. Es el control de acceso basado en roles
(RBAC), que la literatura de seguridad formalizó a principios de los noventa, y cuya idea
central es exactamente ésta: los permisos se le dan al rol, y la persona los hereda por
tener el rol.

### La tabla, escrita

Éste es el piso del concepto. La tabla vive en `PERMISOS`, en `backend/permisos.py:168`, y
esto es lo que dice, **generado corriendo el código** y no copiado a mano. Las nueve
secciones de administración, con `T` para acceso total, `L` para sólo lectura y `-` para
ninguno:

| Rol | dashboard | socios | personal | rutinas | nutrición | usuarios | asistencia | actividades | cobros |
|---|---|---|---|---|---|---|---|---|---|
| dueño | T | T | T | T | T | T | T | T | T |
| recepcionista | T | T | **L** | T | T | T | T | T | T |
| entrenador | - | L | - | T | L | - | - | - | - |
| nutricionista | - | L | - | L | T | - | - | - | - |
| socio | - | - | - | - | - | - | - | - | - |
| profesor | - | - | - | - | - | - | - | - | - |

Y las once acciones sueltas (`x` habilitada):

| Acción | dueño | recep. | entren. | nutric. | socio | prof. |
|---|---|---|---|---|---|---|
| `altaBajaSocios` | x | x | | | | |
| `altaBajaPersonal` | x | | | | | |
| `gestionRutinas` | x | x | x | | | |
| `gestionDietas` | x | x | | x | | |
| `gestionUsuarios` | x | x | | | | |
| `verIngresos` | x | | | | | |
| `cobrarPagos` | x | x | | | | |
| `gestionPromociones` | x | | | | | |
| `gestionDeudas` | x | | | | | |
| `gestionTurnos` | x | x | | | | |
| `verHistorialMedico` | x | | x | x | | |

Además hay ocho secciones propias —`mi-perfil`, `mi-rutina`, `mis-actividades`,
`mi-progreso`, `mi-dieta`, `mi-cuota`, `mis-turnos`, `mis-clases`—: el socio tiene acceso
total a las siete primeras y el profesor lectura a la última. Ningún rol del personal tiene
acceso a ninguna.

Varias reglas del negocio de `CLAUDE.md` están ahí, legibles de un vistazo: la recepcionista
tiene `TOTAL` en actividades y `gestionTurnos` —*"Actividades la gestionan el Dueño y el
Recepcionista con los mismos permisos"*—; la facturación (`verIngresos`) es sólo del dueño;
quién entrena a quién (`gestionRutinas`) lo deciden el dueño y la recepcionista.

### Una persona con varios roles

Una persona puede tener más de un rol: el dueño que además entrena en su gimnasio es `dueno` y
`socio` a la vez. `acceso_a_seccion()` (`backend/permisos.py:340`) resuelve eso quedándose con
el **nivel más alto** entre todos sus roles, y el comentario que la precede lo dice como
principio (línea 338): *"tener un rol extra nunca puede quitar permisos"*. Lo mismo hace
`puede_accion()` (línea 358): la acción está permitida si **alguno** de los roles la habilita.

### Los permisos en pantalla se derivan

`CLAUDE.md` tiene una regla corta sobre esto: *"Para mostrar permisos en pantalla,
derivarlos: nunca escribirlos a mano"*. El panel de Usuarios de la PWA, que le muestra al
dueño qué puede hacer cada rol, arma su grilla leyendo la matriz. Si alguien cambia un
permiso, la grilla cambia sola.

La regla existe porque cualquier descripción de los permisos escrita a mano es una **cuarta
copia** de la matriz que nadie verifica, y se desincroniza en silencio. El propio repo tiene
el ejemplo.

### Nota marcada · la parte del panel escrita a mano

`PermisosPanel.tsx` deriva la grilla, salvo una lista: `ACCIONES_SIN_PANTALLA`
(`Proyecto - PWA/src/frontend/src/views/usuarios/PermisosPanel.tsx:56-67`), que muestra tres
acciones aparte, con este comentario:

> *"Acciones que ya están en la matriz pero todavía no tienen panel construido. Se listan aparte
> para no dar a entender que hoy se están aplicando: no hay pantalla de promociones, deudas
> independientes ni turnos."*

Contando en el backend cuántas veces se exige cada una:

| Acción | Endpoints que la exigen | Lo que dice el panel |
|---|---|---|
| `gestionPromociones` | **8** (`routers/promociones.py`) | que no se aplica |
| `gestionTurnos` | **8** (`routers/actividades.py`) | que no se aplica |
| `gestionDeudas` | **0** | que "todavía" no tiene pantalla |

El comentario quedó viejo para las tres, cada una a su manera. Promociones y turnos **se
aplican hoy** en dieciséis endpoints, y el panel le dice al dueño lo contrario. Y
`gestionDeudas` no protege nada: ningún endpoint la consulta, y no la va a consultar nunca,
porque en este sistema **no existe la deuda** —es prepago puro, y *"Debe"* significa *"no tiene
membresía vigente"*—. No es una acción pendiente de construir sino una que sobrevivió a la
decisión que la volvió innecesaria.

Es exactamente el caso que la regla de derivar existe para prevenir: la única parte del panel
que miente es la única parte escrita a mano. Queda anotada como discrepancia para una tanda de
código, porque corregirla toca la matriz en sus tres copias.

---

## Sección con nivel y acción suelta

### Por qué tres niveles y no dos

La matriz no dice "puede o no puede entrar a Rutinas": dice **con qué nivel**. El docstring
de `Acceso` (`backend/permisos.py:36-41`) justifica los tres con un caso concreto:
*"un Entrenador tiene que poder CONSULTAR la dieta de un socio (para saber de quién es) sin
poder gestionarla. Eso no es ni acceso total ni acceso nulo."*

Con dos niveles, al entrenador habría que darle Nutrición entera —y podría editar dietas que no
son suyas— o sacársela —y trabajaría a ciegas—. El nivel intermedio existe para ese caso, y el
mismo patrón se repite en la tabla: la nutricionista tiene lectura sobre Rutinas por la razón
simétrica.

> **↓ Capa 1 — la comparación contra la jerarquía.** Este es el piso del concepto.

Los niveles se comparan como números. `backend/permisos.py:49`:

```python
_JERARQUIA = {Acceso.NINGUNO: 0, Acceso.LECTURA: 1, Acceso.TOTAL: 2}
```

y `alcanza()` (línea 353) pregunta si un nivel es **al menos** el mínimo pedido:
`_JERARQUIA[nivel] >= _JERARQUIA[minimo]`. Por eso `TOTAL` alcanza donde se pide `LECTURA`, y
nunca al revés.

### La acción suelta: además, no en lugar de

Hay decisiones que no entran en "nivel sobre una sección". El caso que las justifica está en el
docstring de `requiere_accion()` (`backend/security.py:197`): la recepcionista **entra** a
Personal —tiene lectura, necesita ver quién trabaja— pero **no puede dar de alta** a nadie. Un
nivel no alcanza para expresar eso, así que la matriz tiene acciones puntuales, como
`altaBajaPersonal`. Y el docstring precisa que la acción va *"ADEMÁS del permiso de sección, no
en lugar de él. (…) Proteger solo la ruta lo dejaría crear empleados; proteger solo la acción
lo dejaría ver una pantalla que no le corresponde."*

Hay una tercera fábrica para el caso de dos pantallas que leen lo mismo por motivos distintos,
`requiere_alguna_seccion()` (`security.py:174`). Su docstring cuenta el caso que la motivó: el
catálogo de actividades es de la sección Actividades, pero Cobros tiene que leerlo para cobrar
un abono, y había momentos en que el mostrador tenía Cobros sin Actividades. Con la regla a
secas, *"el mostrador no podía cobrar actividades en ninguna de las dos apps"*.

### Por qué está hecho así: el valor por defecto

`requiere_seccion()` (`security.py:145`) pide `LECTURA` si nadie especifica otra cosa:

```python
def requiere_seccion(seccion: str, minimo: str = Acceso.LECTURA):
```

El docstring lo justifica por frecuencia: *"El default es LECTURA porque es lo que necesita
cualquier GET, que son la mayoría. Las escrituras piden TOTAL explícitamente"*. La consecuencia
de ese diseño es que **olvidarse de pedir `TOTAL` en un endpoint que escribe lo deja abierto a
cualquiera con lectura**. Es un valor por defecto que falla abierto: el error no rompe nada
visible, amplía un permiso.

La pregunta que importa es si eso ocurre hoy, y se contesta contando. Recorriendo todos los
endpoints de escritura del backend (`POST`, `PUT`, `PATCH`, `DELETE`) con el analizador
sintáctico de Python:

| Cómo se protegen | Cuántos |
|---|---|
| con una acción puntual (`requiere_accion`) | 56 |
| con sección y `TOTAL` explícito | 12 |
| con sección **sin** `TOTAL` | **23** |
| sin sesión, a propósito (`login`, `logout`, `cambiar-password`) | 3 |

Las 23 que dependen del valor por defecto son **todas del portal del socio** —las rutas
`mi-…`— más `iniciar_pago`, que también pide `MI_CUOTA`. Y la tabla de arriba dice por qué hoy
no es un agujero: **el único rol que tiene acceso a las secciones `mi-` es el socio, y lo tiene
en `TOTAL`**; además, cada una de esas rutas pasa por `_mi_socio()`, que la restringe a los datos
de quien pregunta ([identidad firmada](A-07-autenticacion.md#identidad-firmada)).

Lo que queda es un **riesgo latente**, no un defecto: si mañana alguien le diera a un rol del
personal lectura sobre una sección `mi-` —por ejemplo, para que un entrenador consulte la rutina
propia de un socio—, esas 23 escrituras quedarían habilitadas para ese rol sin que nada avise. La
alternativa, que el valor por defecto fuera `TOTAL`, falla cerrado: olvidarse de bajar el mínimo
en un `GET` rompe una pantalla, y eso se ve en la primera prueba.

---

## Las tres copias y su verificador

### Por qué hay tres

La matriz existe tres veces: en `backend/permisos.py`, en el `config.ts` de la PWA y en
`Flet/Proyecto/app/permisos.py`. El docstring de la copia del backend (líneas 10-13) explica
por qué: *"los tres consumidores (PWA, Flet, backend) necesitan la tabla en su propio lenguaje,
y no hay forma de compartirla en tiempo de ejecución sin agregar un paso de build"*. Es la
misma duplicación deliberada que la paleta de colores entre las dos apps.

Y señala la diferencia que obliga a tratarla distinto (líneas 15-19): *"un color mal copiado
salta a la vista, un permiso mal copiado no. Los síntomas son asimétricos y silenciosos — el
botón aparece pero la API responde 403, o peor, la API deja pasar algo que el frontend creía
prohibido."*

### El verificador

> **↓ Capa 1 — la comparación que corre el chequeo.** Este es el piso del concepto.

`backend/check_permisos.py` compara las tres copias celda por celda, y cada copia se lee de una
forma distinta, elegida por el lenguaje en que está:

- **La del backend** se importa: `from permisos import PERMISOS`.
- **La de Flet** también se importa, *"de verdad en vez de parsearlo"* (líneas 64-66): como es
  Python, un error de sintaxis o una constante mal escrita aparece en el `import` con precisión.
- **La de la PWA** está en TypeScript, y el verificador **no tiene un analizador de TypeScript**.
  Lo que hace es aprovechar que el bloque `PERMISOS` de `config.ts` tiene una forma muy regular y
  extraerlo con expresiones regulares (líneas 97-165): saca los comentarios, encuentra el bloque
  contando llaves, y lee secciones y acciones rol por rol, incluidas las que se arman con `...`
  a partir de otra constante.

La salida, corrida al empezar esta masterclass:

```
backend vs PWA:  6 roles x 17 secciones x 11 acciones.
backend vs Flet: 6 roles, 120 celdas comparadas.
Flet-only: 1 pantalla(s) contrastadas contra su seccion real.
Flet: las 10 secciones de la matriz existen en Routes.

[OK] las tres copias dicen exactamente lo mismo.
```

La línea *"Flet-only"* es la pantalla de Recepción, que hoy existe sólo en la app de escritorio.

### Por qué está hecho así

**Qué se eligió:** duplicar y verificar, en lugar de generar las copias desde una fuente única.

**Qué se descartó:** un paso de compilación que escriba `config.ts` y `app/permisos.py` a partir
del archivo del backend. Resolvería la duplicación, al precio de agregar una herramienta que hay
que correr antes de cada cambio, y que sin correrla deja las copias viejas exactamente igual que
hoy. Hay una tercera opción que el docstring no menciona: que el backend **sirva** la matriz —ya
responde `GET /me` con los roles de la sesión—. Eliminaría las copias de los clientes en tiempo de
ejecución, pero haría que qué pantallas existen dependa de una respuesta de red.

**Qué se paga:** tres archivos que hay que tocar juntos, y un verificador que sólo protege si
alguien lo corre.

Un detalle menor: los docstrings de `permisos.py:7` y de `check_permisos.py:7-8` todavía nombran
las carpetas con sus nombres viejos (`Proyecto/src/frontend/…` y `Proyeto-Python/…`). La ruta que
el verificador usa de verdad, en `check_permisos.py:45`, es la correcta.

---

## El frontend esconde, el backend rechaza

### La idea central

El docstring de `backend/permisos.py:21-26` la llama *"la idea central de todo el proyecto"*:

> *"la copia de config.ts es UX (decide qué se dibuja), esta copia es SEGURIDAD (decide qué se
> ejecuta). El frontend esconde; el backend rechaza. Alguien con las devtools abiertas puede
> alterar el store de la PWA y hacer aparecer cualquier botón — y cuando lo apriete, esta tabla
> es la que lo frena."*

Todo lo que corre en el navegador está bajo el control de quien usa el navegador. Las
herramientas de desarrollo permiten cambiar el estado de la aplicación, forzar un rol en el
almacén de la sesión, o directamente mandar el pedido HTTP a mano sin pasar por ninguna pantalla.
Por eso **ocultar un botón nunca es una medida de seguridad**: es una medida de claridad, para que
nadie vea opciones que no puede usar. La seguridad es la otra copia, la que corre en una máquina
que el usuario no controla.

La PWA lo recuerda del lado del cliente, en `hooks/usePermisos.ts:6-8`: *"esto decide qué se
DIBUJA, no qué se permite. Un usuario con devtools puede forzar el store y ver cualquier botón. La
validación real va en el backend"*. Y lo mismo aplica a `ProtectedRoute`, como ya se dejó dicho en
[enrutado del lado del cliente](A0-06-react.md#enrutado-del-lado-del-cliente).

### Las dos mitades, en espejo

Cada lado tiene las mismas dos funciones, en su lenguaje:

| Pregunta | Backend (`permisos.py`) | PWA (`config.ts`, vía `hooks/usePermisos.ts`) |
|---|---|---|
| ¿qué nivel tengo en esta sección? | `acceso_a_seccion()` | `accesoASeccion()` → `useAccesoSeccion()` |
| ¿puedo hacer esta acción? | `puede_accion()` | `puedeAccion()` → `usePuedeAccion()` |

Los ganchos de la PWA son, en palabras de su propio archivo, *"un envoltorio fino"*: lo único que
agregan es leer los roles del almacén de la sesión.

> **↓ Capa 1 — la línea que levanta el 403.** Este es el piso del capítulo.

Del lado del backend, cada permiso es una **dependencia** de FastAPI, que corre antes del cuerpo
del endpoint. La de las acciones, `requiere_accion()` (`backend/security.py:197-214`):

```python
def dependencia(sesion: Sesion = Depends(obtener_sesion)) -> Sesion:
    if not puede_accion(sesion.roles, accion):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tenés permisos para realizar esta acción.",
        )
    return sesion
```

La línea 210 es la frontera: si la matriz no habilita la acción, el endpoint **no llega a
ejecutarse**. `requiere_seccion()` hace lo mismo en la línea 166, y `requiere_alguna_seccion()`
en la 189. En qué punto del recorrido de un pedido corre esta dependencia —después de validar la
sesión y antes del handler— está en
[la escala 14 del recorrido](A-04-recorrido-de-un-pedido.md#escala-14--la-dependencia-de-permisos).

Y la dependencia de permisos **depende** de `obtener_sesion()`: primero se sabe quién pregunta,
después qué puede. Las dos preguntas, en el orden en que las responde el código.

---

## Omitir en vez de deshabilitar

### La regla, y lo que un botón gris dice

`CLAUDE.md` la formula para el historial médico: *"El Recepcionista no lo ve, y el botón se
**omite** (no se deshabilita) para no delatar que hay algo cargado."*

El motivo es que **un control deshabilitado es información**. Si la grilla de socios mostrara un
botón gris de "historial médico" sólo en las filas que tienen algo cargado, la recepcionista
sabría, sin abrir nada, qué socios tienen una condición médica registrada. Y aunque el botón
estuviera gris en todas las filas, seguiría diciendo que ese dato existe y que alguien decidió no
mostrárselo. Omitirlo en todas las filas no dice nada: para quien no tiene el permiso, la función
no existe.

### El botón que no se dibuja

Éste es el piso. En `Proyecto - PWA/src/frontend/src/views/socios/SocioTableRow.tsx:152`:

```tsx
{puedeVerHistorialMedico && (
```

No hay un `disabled`: el botón simplemente no entra en el árbol. El valor lo calcula la grilla
derivándolo de la matriz, `usePuedeAccion('verHistorialMedico')`
(`views/socios/SociosView.tsx:83`).

El docstring de la propiedad (`SocioTableRow.tsx:18-24`) cuenta por qué esta acción no se puede
deducir del nivel de sección: *"el Recepcionista tiene Socios en TOTAL y esta acción en false, y
el Entrenador está justo al revés —Socios en LECTURA y la acción en true—. Es la única de la
matriz donde el mostrador queda por debajo del Entrenador."* En la tabla de arriba se ve igual.

Y como ocultar nunca alcanza, el backend exige la misma acción en los endpoints de patologías:
`requiere_accion(Accion.VER_HISTORIAL_MEDICO)` aparece 7 veces en
`backend/routers/patologias.py`. Una recepcionista que armara el pedido a mano recibiría un 403.

---

## Aislamiento de lo propio

### Dos rechazos, dos códigos

El sistema rechaza el acceso a datos ajenos de dos formas distintas, y la diferencia es
deliberada.

**Cuando la respuesta sólo habla de quien pregunta, es 403.** El portal del socio rechaza a un
empleado que no entrena en el gimnasio con *"Tu cuenta no está asociada a una ficha de socio"*
(`_mi_socio()`, `backend/routers/portal.py:90`, detallado en
[identidad firmada](A-07-autenticacion.md#identidad-firmada)). Ese 403 no revela nada que el
empleado no sepa: que él no es socio.

**Cuando un 403 confirmaría que algo ajeno existe, es 404.** Un socio puede armarse su propia
rutina y su propia dieta, sin entrenador ni nutricionista —se reconocen porque `id_entrenador`
o `id_nutricionista` quedan en `NULL`—, y `CLAUDE.md` dice que son *"invisibles para el
personal"*.

### El 404 en vez del 403

Éste es el piso. `_rutina_del_staff()` (`backend/routers/rutinas.py:218-232`) es la única puerta
por la que el personal accede a una rutina, y rechaza la propia de un socio **con exactamente el
mismo 404 que si no existiera**:

```python
rutina = db.get(Rutina, id_rutina)
if rutina is None or rutina.id_entrenador is None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La rutina no existe.")
```

El docstring explica el porqué con precisión: *"Un 403 —o cualquier mensaje distinto— confirmaría
que el id existe y es de alguien, que es justo lo que no tiene que poder saberse desde acá. Así
ningún endpoint del personal (obtener, asignar, editar, baja, reactivar) puede tocar ni enumerar
la rutina propia de un socio."* Con un 403, alguien del personal podría recorrer los ids de uno en
uno y distinguir "no existe" de "existe pero es privada", y contar cuántos socios se arman su
propia rutina. Con el mismo 404 para los dos casos, no hay nada que distinguir.

Las dietas tienen la función gemela, `_dieta_del_staff()` (`backend/routers/nutricion.py:196`),
con la misma condición sobre `id_nutricionista`.

El principio que sale de las dos secciones es corto: **403 cuando el rechazo sólo habla de quien
pregunta; 404 cuando un 403 confirmaría que existe algo privado de otro.** Es la misma lógica que
hace que el login responda igual para un usuario inexistente que para una contraseña equivocada.

### Lo propio también del lado del cliente

El aislamiento no termina en el backend. La app de escritorio guarda respuestas en un caché, y al
cerrar sesión lo vacía entero: las respuestas guardadas son de la persona anterior, y la siguiente
no tiene por qué verlas ni un instante. Cómo funciona ese caché está en
[servir y refrescar](A-11-rendimiento.md#servir-y-refrescar).

---

## Con qué se conecta

- **Es la misma idea que…** la [identidad firmada](A-07-autenticacion.md#identidad-firmada): la
  identidad dice *quién* pregunta; la matriz, *qué* puede pedir; y el código las responde en ese
  orden.
- **Es la misma idea que…** la
  [respuesta indistinguible](A-07-autenticacion.md#freno-de-intentos-y-respuesta-indistinguible):
  el 404 de la rutina propia no revela que existe, como el login no revela qué usuarios existen.
- **Se contradice con…** fallar cerrado ([clave secreta](A0-11-criptografia-aplicada.md#clave-secreta)):
  el backend no arranca sin clave, pero `requiere_seccion()` pide lectura por defecto y un olvido
  amplía un permiso en vez de romper algo.
- **Es la misma idea que…** la paleta duplicada entre las dos apps
  ([las dos aplicaciones](A-03-dos-apps-un-backend.md)): duplicar a propósito; lo que cambia es
  que el color mal copiado se ve y el permiso no, y por eso sólo la matriz tiene verificador.
- **Existe por culpa de…** la invalidación total del caché de Flet
  ([servir y refrescar](A-11-rendimiento.md#servir-y-refrescar)): lo guardado es de la persona
  anterior, y se tira al cerrar sesión.
