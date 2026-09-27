# A-03 · Las dos aplicaciones y el único backend

*Piso del capítulo: las dos carpetas, la única API, y el comentario que une a cada pieza con su
gemela.*

OlimpOS es un producto con **dos caras** y **un solo cerebro**. Una aplicación web que el socio
lleva en el celular y el personal abre en cualquier navegador; una aplicación de escritorio para la
PC del mostrador; y detrás de las dos, una única API con una única base. Este capítulo explica esa
forma, la regla que obliga a las dos caras a parecerse, y lo que esa regla cuesta: todo lo que se
comparte entre ellas vive copiado, y hay que decidir cómo se mantienen de acuerdo las copias.

Cómo funciona cada app por dentro está en otros capítulos: la PWA en
[React](A0-06-react.md) y [el navegador por dentro](A0-04-el-navegador-por-dentro.md), la de
escritorio en [Flutter y Flet](A0-13-flutter-y-flet.md). Acá se trata la relación entre ellas.

---

## Dos aplicaciones, un backend

### Dos lugares de uso

El gimnasio tiene dos situaciones de uso que no se parecen: **el mostrador**, donde una sola persona
resuelve siempre las mismas tareas con la fila delante, y **todo lo demás**, donde cada uno usa el
sistema a su ritmo y casi siempre desde un celular. Quién está en cada una, con qué aparato y con
cuánta gente esperando, está en [OlimpOS](A-01-que-es-olimpos.md#olimpos).

Para cada situación hay una aplicación. La **PWA** (`Proyecto - PWA/src/frontend`) sirve a los seis
roles desde el navegador o instalada en el celular. La **app de escritorio** (`Flet/Proyecto`) está
pensada para la PC de recepción, para el recepcionista y el dueño.

### La única API

> **↓ Capa 1 — las dos carpetas y la única API.** Éste es el piso.

Medido sobre el árbol del repo: la PWA son 126 archivos `.ts` y `.tsx` con unas 26.700 líneas; la app
de escritorio, 28 archivos Python con unas 12.800. Las dos hablan con **la misma** API de FastAPI, en
`backend/`, que expone 130 rutas —167 si se cuenta cada método por separado—. No hay un backend para
cada app, ni un endpoint duplicado "para Flet".

Esa unicidad es lo que hace que el sistema sea uno solo. Todas las reglas que deciden plata, estados y
permisos viven en el backend: que no se cobra por adelantado, cuándo un socio está vencido, quién puede
ver el historial médico. Si hubiera dos backends, cada regla estaría escrita dos veces, y ya se vio en
[el dashboard que derivaba por su cuenta](A-09-estados-derivados.md#el-dashboard-que-derivaba-por-su-cuenta)
lo que pasa cuando una regla vive en dos lugares: se contradice. Con un backend, las dos apps pueden
verse distintas, pero no pueden **decir** cosas distintas sobre el mismo socio, porque la respuesta sale
del mismo lugar.

Hay una sola diferencia en cómo las dos apps le hablan al backend, y es de transporte, no de reglas: la
PWA viaja con una cookie y un token CSRF, y Flet con un token en una cabecera. Por qué son dos
mecanismos está en
[los dos mecanismos de este sistema](A0-12-sesiones-y-autenticacion.md#los-dos-mecanismos-de-este-sistema-y-por-qué-son-dos),
y cómo el backend distingue a cada cliente, en
[los dos mecanismos de sesión](A-07-autenticacion.md#los-dos-mecanismos-de-sesión-y-x-client-type).

### Una app para el mostrador, y por qué no está escrito

Una pregunta razonable es por qué el mostrador tiene una aplicación aparte, si la PC de recepción podría
abrir la PWA en un navegador. **El repo no lo dice**: el README describe la división —*"una app web para
los socios y una app de escritorio para el mostrador"*— sin justificarla. Lo que sí se puede leer en el
código es qué obtiene la app de escritorio por ser una aplicación y no una página:

- **Está escrita en Python**, el mismo lenguaje que el backend.
- **No necesita la maquinaria de la sesión del navegador**: sin cookie no hay CSRF que defender, ni proxy
  que ponga la página y la API en el mismo sitio.
- **Tiene un caché propio** que sirve al instante y refresca por detrás
  ([servir y refrescar](A-11-rendimiento.md#servir-y-refrescar)), pensado para quien cambia de pantalla
  cien veces por día.

Y tiene su precio, que es todo el resto de este capítulo: dos aplicaciones que tienen que parecerse.

Un detalle de la división: la app de escritorio usa **la misma matriz de permisos** que la PWA, con los
seis roles (lo verifica el chequeo de las tres copias). Un entrenador podría abrirla y vería sus
secciones. El profesor no tiene ninguna sección en Flet: entra, y la app le dice que su pantalla
está en la PWA; el socio, en cambio, queda afuera en el login. Por qué los dos se tratan distinto
está en [iniciar sesión](B-01-acceso-y-sesion.md#3-iniciar-sesión).

---

## Aplicación gemela y componente gemelo

### La regla

`CLAUDE.md` la escribe como la primera decisión de la arquitectura: *"La PWA es la referencia y Flet es
su gemela. Si difieren, la que está bien es la PWA. Todo arreglo de la PWA se replica en Flet en la misma
tanda, porque el dueño prueba en la PWA y da por hecho que Flet quedó igual."*

La razón está en la última frase, y es de proceso, no de tecnología. El dueño prueba una de las dos, y la
otra la da por buena. Si un arreglo se hiciera sólo en la PWA, el sistema quedaría con un error que nadie
va a ver hasta que alguien lo use en el mostrador. La regla convierte esa suposición del dueño en verdad:
lo que se prueba en la PWA vale para Flet porque se hizo en las dos.

"Referencia" tiene un sentido preciso: si las dos difieren, no se discute cuál tiene razón. Gana la PWA,
y Flet se corrige para parecerse.

### El comentario que nombra al gemelo

> **↓ Capa 1 — cómo se mantiene cada par.** Éste es el piso.

La regla no queda en la memoria de nadie: está escrita en el código. `Flet/Proyecto/app/components/ui.py`,
el archivo con los componentes visuales de la app de escritorio, abre con una tabla de correspondencias
(líneas 11-16):

```python
#   build_sidebar   ↔ Sidebar.tsx        primary_button ↔ PrimaryButton.tsx
#   build_topbar    ↔ Topbar.tsx         input_field    ↔ InputField.tsx
#   stat_card       ↔ StatCard.tsx       section_card   ↔ SectionCard.tsx
#   status_badge    ↔ StatusBadge.tsx
#   filter_chip     ↔ FilterChip.tsx     show_snack     ↔ Snackbar.tsx
#   confirm_dialog  ↔ ConfirmDialog.tsx
```

Y cada función repite su gemelo en el docstring: *"Espejo de Sidebar.tsx"*, *"Espejo de StatCard.tsx"*.
En el archivo hay 23 funciones y 20 menciones de un componente `.tsx`. Quien toca `stat_card` sabe, sin
buscar, qué archivo de la PWA tiene que mirar.

La regla funciona en las dos direcciones, y el mismo archivo lo muestra con algo que ya no está. Las
líneas 339-343 guardan el hueco de un componente borrado:

> *"Acá vivía level_badge (Principiante/Intermedio/Avanzado). Se retiró el 2026-09-16 junto con su gemelo
> LevelBadge.tsx: el nivel era una etiqueta ambigua —el 'intermedio' de uno es el 'avanzado' de otro— y
> filtrar por ella no servía."*

"Junto con su gemelo": se borraron los dos en la misma tanda. Y el comentario se quedó para que nadie lo
vuelva a agregar sin saber por qué se fue.

La correspondencia no es sólo de componentes: llega a las fórmulas. El gráfico de ingresos de Flet lleva,
al lado de su cálculo, *"Mismo criterio que ALTURA_MINIMA en la PWA"* (ver
[gráfico dibujado a mano](#gráfico-dibujado-a-mano)).

### Las dos asimetrías

El gemelo no es una copia completa, y hay dos diferencias que no son errores:

- **El portal del socio no existe en Flet, y está bien.** Son 23 archivos de `views/socio/` en la PWA
  —la rutina, la dieta, la cuota, el contador de repeticiones— que en Flet no tienen equivalente. La app
  de escritorio es la PC del mostrador; el socio no se sienta ahí.
- **Recepción existe sólo en Flet, y es un pendiente.** Es la sección
  [siguiente](#recepción-panel-del-mostrador).

### Por qué está hecho así

**Qué se optimiza:** que las dos apps se comporten igual, sin que el dueño tenga que probar las dos.

**Qué restringe:** son dos lenguajes. TypeScript en un navegador y Python manejando Flutter no pueden
compartir un componente: no hay código que se pueda usar en las dos.

**Qué alternativa se descartó:** dejar que cada app evolucione por su lado, y aceptar que difieran.

**Qué se paga:** cada cambio se hace dos veces, y la segunda es la que más fácil se olvida. Y hay una parte
que ninguna prueba automática verifica: cómo se ve un diálogo de Flet, que hay que mirar en el navegador con
el lanzador web.

**Cómo se llama:** una **implementación de referencia** con su réplica. El patrón existe donde hay que tener
el mismo comportamiento en dos lenguajes que no comparten código.

---

## Duplicación deliberada

### El concepto

Hay datos que las dos apps y el backend necesitan idénticos —los colores, los permisos—, y sólo hay dos
formas de tenerlos en tres lugares: **compartir** una única copia, o **copiarlos** en cada uno. Compartir en
tiempo de ejecución entre TypeScript, Python y una API exigiría un paso de compilación que genere las copias,
o una consulta de red para obtenerlas. El sistema eligió copiar, a sabiendas. Eso es la duplicación
deliberada: no un descuido, sino una copia con un plan para que no se desincronice.

### La paleta: tres copias de cada color

El acento volt del sistema, `#C6F135`, está escrito tres veces:

| Copia | Dónde | Para qué |
|---|---|---|
| `--color-primary-volt: #C6F135;` | `Proyecto - PWA/src/frontend/src/index.css:8` | las clases de Tailwind, como `bg-primary-volt` |
| `primaryVolt: '#C6F135',` | `Proyecto - PWA/src/frontend/src/config.ts:38` | el código TypeScript que necesita el valor |
| `PRIMARY_VOLT = "#C6F135"` | `Flet/Proyecto/app/config.py:53` | la app de escritorio |

Dos de las tres copias son de **la misma** aplicación, y hay una razón mecánica. Una clase de CSS pinta un
elemento, pero no entrega el color como un valor que el código pueda usar. Cuando el código necesita el
color en sí —para pasárselo a un ícono, o para armar un color translúcido—, necesita el texto del hexadecimal.
Se ve en el mismo archivo: la píldora de estado toma sus colores de `config.ts` (`colors.statusOk`), mientras
el gráfico de ingresos pinta sus barras con una clase (`bg-primary-volt/70`).

### El chequeo que la mantiene sincronizada

> **↓ Capa 1 — el control, proporcional a cuán callada es la falla.** Éste es el piso.

Copiar a propósito sólo es seguro si algo detecta cuándo las copias dejan de coincidir. Y el sistema no
controla igual sus dos duplicaciones, a propósito:

- **La matriz de permisos tiene un verificador**, `backend/check_permisos.py`, que compara las tres copias
  celda por celda. Cómo funciona está en
  [las tres copias y su verificador](A-08-autorizacion.md#las-tres-copias-y-su-verificador).
- **La paleta no tiene ninguno.** No hay en el repo un script que compare colores.

La diferencia no es un olvido. La da el docstring de la matriz: un color mal copiado *"salta a la vista"* y
un permiso mal copiado no. Si el volt de Flet quedara con un dígito de más, la primera persona que abra la
app lo ve. Si un permiso quedara distinto en el backend, nada en pantalla lo muestra hasta que alguien
aprieta un botón y recibe un 403, o peor, hasta que la API deja pasar algo que la pantalla creía prohibido.
**El control se pone donde la falla es silenciosa.**

La misma lógica aplica a los pares más chicos que el mapa del repo registra entre las dos apps: el campo de
teléfono con país (`TelefonoField` en la PWA, `telefono_field` en Flet), o los enlaces a mail y WhatsApp
(`utils/contacto.ts` y `app/contacto.py`).

---

## Gráfico dibujado a mano

### Por qué no hay librería

Ninguna de las dos apps usa una librería de gráficos: el `package.json` de la PWA no tiene ninguna, y Flet
0.84 no trae una. La segunda razón fuerza la primera. Si la PWA dibujara con una librería y Flet a mano, el
mismo gráfico tendría dos aspectos, y la regla de las gemelas no se podría cumplir. Así que los dos se dibujan
a mano: barras hechas con rectángulos cuyas alturas se calculan.

### La fórmula que mapea valor a coordenada

> **↓ Capa 1 — la cuenta.** Éste es el piso.

El gráfico de ingresos del dashboard en la PWA (`views/dashboard/IngresosChart.tsx:99-100`) calcula la altura
de cada barra como porcentaje del alto del gráfico:

```ts
const alto =
  p.monto <= 0 ? 0 : ALTURA_MINIMA + (p.monto / maximo) * (100 - ALTURA_MINIMA);
```

Y su gemelo de Flet (`Flet/Proyecto/app/views/dashboard.py:250-251`) hace la misma cuenta en píxeles:

```python
alto = 0 if p["monto"] <= 0 else int(
    ALTO_GRAFICO * (0.04 + 0.96 * p["monto"] / maximo))
```

Es una **transformación lineal** con tres partes:

1. `monto / maximo` lleva cada valor a una fracción entre 0 y 1: el día que más se cobró vale 1.
2. Esa fracción se estira sobre el 96 % del alto, **empezando en el 4 %**. `ALTURA_MINIMA = 4` en la PWA
   (`IngresosChart.tsx:37`), `0.04` en Flet. El comentario de la PWA (línea 36) dice por qué: *"Que un día
   chico no desaparezca del todo al lado de uno grande."*
3. Un día sin cobros es cero: sin barra, ni la mínima.

Con números. Si el máximo del período es $100.000 y el alto de Flet es `ALTO_GRAFICO = 150` píxeles
(`dashboard.py:34`):

| Día | Fracción | Alto en la PWA | Alto en Flet |
|---|---|---|---|
| $100.000 | 1 | 100 % | 150 px |
| $50.000 | 0,5 | 4 + 0,5 × 96 = 52 % | 150 × 0,52 = 78 px |
| $1.000 | 0,01 | ≈ 5 % | 150 × 0,0496 = 7 px |
| $0 | — | 0 | 0 |

Sin la altura mínima, el día de $1.000 sería el 1 %: un píxel y medio en Flet, una línea que no se ve. El 4 %
existe para que un día flojo siga pareciendo un día con cobros.

### El `1` que evita la división por cero

El máximo se calcula con un detalle: `Math.max(...montos, 1)` en la PWA (`IngresosChart.tsx:60`) y
`max(montos + [1])` en Flet (`dashboard.py:241`). Ese `1` agregado a la lista es el que impide que el máximo
sea cero.

Y el máximo es cero exactamente en el caso que `CLAUDE.md` manda probar: **la base vacía**. En el estado de
entrega no hay ningún pago, todos los montos son cero, y dividir por un máximo de cero daría alturas sin valor
en la PWA y un error en Flet, que dejaría la pantalla sin construir. Es una de las *"divisiones por cero"* que
la trampa 7 de Flet señala; acá está resuelta en una sola cifra.

Cada gráfico hecho a mano de las dos apps, con su matemática completa, está en
[los gráficos dibujados a mano](C-03-graficos-a-mano.md).

---

## Recepción (panel del mostrador)

### La pantalla que resuelve el mostrador

`Flet/Proyecto/app/views/recepcion.py` es la pantalla que el recepcionista ve al entrar, y su docstring
(líneas 4-10) dice cuál es la regla que la ordena: *"el recepcionista NO debería tener que buscar nada. Los
turnos llegan ordenados por cercanía, cada persona anotada trae al lado lo que hay que decirle cuando aparezca
(…) y el fichaje resuelve solo a qué clase corresponde el ingreso."* Se vuelve a pedir sola cada diez segundos
(`SEGUNDOS_REFRESCO = 10`, línea 30), para que un ingreso aparezca sin que nadie apriete nada.

### La pantalla que hoy existe en una sola app

> **↓ Capa 1 — dónde está hecha y dónde falta.** Éste es el piso.

Es la única pantalla del sistema que existe en Flet y no en la PWA, y lo que falta para tenerla en la PWA se
puede medir capa por capa:

| Capa | Estado |
|---|---|
| Backend | **completo**: `GET /recepcion/panel`, `/recepcion/turnos/{id}` y `/recepcion/buscar` (`backend/routers/recepcion.py:175`, `247` y `308`), las tres protegidas por la sección Asistencia |
| Servicios de la PWA | uno de tres: `/recepcion/turnos/{id}` lo usa `getDetalleTurno()` (`services/turnosService.ts`), que llama la agenda de turnos; el panel y la búsqueda no los llama nadie |
| Pantalla, ruta y menú de la PWA | no existen |
| Matriz de permisos | la sección `RECEPCION` está sólo en la copia de Flet (`Flet/Proyecto/app/permisos.py:51`) |

El último punto explica un renglón que se vio en el verificador de permisos: *"Flet-only: 1 pantalla(s)
contrastadas contra su seccion real"*. La pantalla de Recepción es de Flet, pero sus datos los protege la
sección **Asistencia** del backend, que sí está en las tres copias. El verificador comprueba que el acceso a la
pantalla coincida con el acceso a la sección que de verdad protege sus datos.

`CLAUDE.md` registra el cambio de estado de esta pantalla: era *"única excepción"* a la regla de las gemelas, y
*"el dueño pidió que también esté en la PWA, así que dejó de ser una excepción y pasó a ser un pendiente"*.

### Nota marcada · el porqué que quedó en el docstring

El docstring de `recepcion.py` (líneas 12-13) todavía justifica la excepción: *"No tiene gemelo en la PWA: es
una pantalla del personal, y los socios no la ven."*

El argumento no se sostiene y la decisión ya cambió. Que sea una pantalla del personal no la aleja de la PWA,
porque la PWA **también** la usa el personal: el dueño trabaja en ella, y la recepcionista puede abrirla. Y el
dueño ya pidió la pantalla en la PWA. El mismo docstring menciona *"deuda"* entre lo que hay que avisarle a un
socio, en un sistema que no tiene deudas ([prepago puro](A-02-prepago-puro.md#prepago-puro)). Gana la decisión
vigente: es un pendiente.

---

## Con qué se conecta

- **Es la misma idea que…** la [regla resuelta en el backend](A-09-estados-derivados.md#regla-resuelta-en-el-backend):
  un solo backend para que las dos apps no puedan decir cosas distintas del mismo socio.
- **Es la misma idea que…** [las tres copias de la matriz](A-08-autorizacion.md#las-tres-copias-y-su-verificador):
  una duplicación deliberada; la matriz lleva verificador y la paleta no, porque su falla es la silenciosa.
- **Existe por culpa de…** el [canvas de Flutter](A0-13-flutter-y-flet.md#canvas-de-flutter): sólo un motor que
  pinta cada píxel permite que las dos apps se vean casi iguales.
- **Es el mismo problema que…** [el dashboard que derivaba por su cuenta](A-09-estados-derivados.md#el-dashboard-que-derivaba-por-su-cuenta):
  lo que se escribe dos veces, sin un control, termina diciendo dos cosas.
- **Existe por culpa de…** los [dos mecanismos de sesión](A-07-autenticacion.md#los-dos-mecanismos-de-sesión-y-x-client-type):
  dos clientes distintos, dos formas de llevar la misma sesión.
