# A0-11 · Criptografía aplicada

*Piso del capítulo: las compuertas lógicas. Es el único capítulo de la masterclass que
baja hasta ahí, y lo hace usando el vocabulario de
[instrucción de máquina y compuerta lógica](A0-01-como-corre-un-programa.md#instrucción-de-máquina-y-compuerta-lógica)
sin volver a definirlo.*

Todo lo que este sistema tiene de seguridad descansa en tres promesas, y las tres son
criptográficas:

1. Una contraseña guardada en la base **no se puede leer**, ni siquiera con acceso total a
   la base.
2. Una sesión firmada **no se puede falsificar**: nadie puede editar su propio `id_socio`
   para ver los datos de otro.
3. Un token generado por el sistema **no se puede adivinar**.

Este capítulo explica por qué esas tres promesas se cumplen, bajando hasta el punto donde
dejan de ser promesas y pasan a ser física. Es el capítulo donde el descenso llega de
verdad al fondo, y corresponde: la irreversibilidad de un hash no se entiende a medias. O
se ve por qué un circuito concreto no se puede correr al revés, o se la acepta como un
acto de fe, y una masterclass no pide actos de fe.

---

## Función hash criptográfica

### El problema de origen

Hace falta una operación que tome **cualquier cosa** —una contraseña de ocho letras, un
archivo de un gigabyte— y devuelva una **huella de tamaño fijo**, con tres garantías:

1. **Resistencia a la preimagen.** Dada una huella, es inviable encontrar una entrada que
   la produzca. No se puede ir para atrás.
2. **Resistencia a la segunda preimagen.** Dada una entrada, es inviable encontrar *otra*
   con la misma huella. No se puede reemplazar un mensaje por otro que "pese igual".
3. **Resistencia a colisiones.** Es inviable encontrar *dos entradas cualesquiera* con la
   misma huella, aunque el atacante elija las dos.

Y dos propiedades que no son garantías sino condiciones de uso: es **determinista** —la
misma entrada da siempre la misma salida, si no no serviría para comparar— y es **rápida**
de calcular en el sentido hacia adelante.

"Inviable" tiene un significado preciso y no es "imposible": significa que el mejor ataque
conocido cuesta más trabajo que el que la humanidad puede hacer. Para una huella de 256
bits, adivinar a ciegas una preimagen requiere del orden de 2²⁵⁶ intentos, un número con
78 cifras. Las colisiones son más baratas por la paradoja del cumpleaños —alcanza con 2¹²⁸
intentos, porque se buscan dos coincidencias cualesquiera y no una en particular— y aun
así 2¹²⁸ es un número de 39 cifras.

### De dónde viene, y qué se rompió

La historia de las funciones hash es una historia de roturas, y conviene conocerla porque
explica por qué este sistema usa las que usa:

| Función | Año | Qué le pasó |
|---|---|---|
| MD5 | 1991 (Rivest) | colisiones prácticas publicadas en 2004 (Wang y otros): se generan en segundos |
| SHA-1 | 1995 | primera colisión pública en 2017 (*SHAttered*, Google y el CWI de Ámsterdam) |
| **SHA-256** | principios de los 2000 (estándar FIPS 180-2 del NIST) | **sin ataque práctico conocido** |

Una función hash rota no se vuelve inútil de un día para otro, pero sí se vuelve inservible
para lo que importa acá: si alguien puede fabricar dos mensajes con la misma huella, puede
presentar uno como si fuera el otro. Por eso el estándar actual es SHA-256, y por eso la
cabecera del JWT de este sistema dice `HS256`.

### La propiedad que se ve: el efecto avalancha

Las tres garantías son negativas —dicen qué *no* se puede hacer— y por eso no se pueden
mostrar. Pero tienen una consecuencia visible, que es la mejor forma de convencerse de que
la función mezcla de verdad:

```
sha256("gimnasio") = 8980bb138a902563d58546679d5c0f04f5fd4f51be633859710c9956d24a5f35
sha256("gimnasiO") = 128ab5d4333979273c4c05f59ea34b411e90183dc74a47e2b51b8481e73e3f7e
```

Las dos entradas difieren en **un solo bit**: la `o` minúscula y la `O` mayúscula son
`0x6F` y `0x4F` en ASCII, y difieren sólo en el bit de valor 32. Las dos salidas difieren
en **132 de sus 256 bits: el 51,6 %.** Es lo que se espera de dos números elegidos al azar,
y ahí está el punto: un bit de diferencia en la entrada produce una salida que no se
parece en nada a la otra.

Eso es el **efecto avalancha**, y es la razón práctica por la que un hash sirve de huella.
Si cambiar un bit de la entrada cambiara pocos bits de la salida, se podría ir ajustando la
entrada de a poco hasta acercarse a una huella objetivo, como quien juega a "frío o
caliente". Con avalancha no hay caliente: cada intento está tan lejos como cualquier otro.

(Los dos hashes se calcularon con `hashlib.sha256` de Python, el mismo módulo que usa el
backend.)

### Vuelta al repo

SHA-256 aparece en OlimpOS en tres lugares, y en ninguno se usa sola:

- **Adentro de cada JWT**, como la función de hash de HMAC-SHA256: `ALGORITMO = "HS256"`
  (`backend/auth.py:35`).
- **Adentro de la verificación del webhook de Mercado Pago**: `hashlib.sha256` pasado a
  `hmac.new()` (`backend/mercadopago.py:300-304`).
- **Como salida de emergencia documentada** para contraseñas de más de 72 bytes:
  *"la solución estándar es pasar la contraseña por SHA-256 antes de bcrypt, no subir este
  número"* (`backend/auth.py:41-42`). Hoy no se usa; está escrito para que nadie resuelva
  mal el problema el día que aparezca.

Que no se use nunca sola es deliberado, y las dos secciones que siguen explican por qué:
un hash solo no alcanza ni para firmar ni para guardar contraseñas.

---

## SHA-256

*Esta sección es el descenso completo. Si ya sabés cómo funciona una función de
compresión, saltá a [HMAC](#hmac-y-firma-simétrica).*

### El problema de diseño

La función tiene que aceptar entradas de cualquier largo, pero un circuito tiene un ancho
fijo. La solución, que se llama **construcción de Merkle–Damgård** por sus dos autores
(1979-1989), es partir la entrada en bloques del mismo tamaño y procesarlos **en cadena**:
hay un estado interno de 256 bits, cada bloque se mezcla con ese estado para producir el
estado siguiente, y la huella final es el estado después del último bloque.

```
estado₀ ──┐          ┌── estado₁ ──┐          ┌── estado₂ ─── …  ─── huella
          ├─ mezclar ┤             ├─ mezclar ┤
bloque₁ ──┘          └             bloque₂ ──┘
```

La pieza que se repite —`mezclar`, que toma 256 bits de estado y 512 bits de bloque y
devuelve 256 bits— se llama **función de compresión**, y es donde vive toda la seguridad.
El resto es contabilidad.

Retené un dato de este diagrama porque va a volver en la sección de HMAC: **la huella es
literalmente el estado interno después del último bloque.** No hay ningún paso final que
lo oculte.

> **↓ Capa 1 — el relleno y los bloques.**

Un bloque de SHA-256 son 512 bits (64 bytes). Como la entrada rara vez mide un múltiplo
exacto de eso, se rellena con una regla fija:

1. Se agrega un bit `1`.
2. Se agregan bits `0` hasta que el largo quede 64 bits por debajo de un múltiplo de 512.
3. Se agregan esos 64 bits finales con **el largo original de la entrada**, en binario.

La palabra `gimnasio` son 8 bytes = 64 bits. Relleno: `1`, 383 ceros, y el número 64
escrito en 64 bits. Total: 64 + 1 + 383 + 64 = 512. Un solo bloque.

Poner el largo al final no es un detalle: impide que dos entradas de largos distintos
terminen con el mismo relleno.

> **↓ Capa 2 — el estado y las constantes.**

El estado son **ocho palabras de 32 bits**, llamadas `a` a `h`. Arrancan con valores fijos:
los primeros 32 bits de la parte fraccionaria de las raíces cuadradas de los primeros ocho
números primos. La primera, la de √2, es `0x6a09e667`.

Hay además 64 constantes de ronda, `K₀` a `K₆₃`, sacadas del mismo modo de las raíces
**cúbicas** de los primeros 64 primos. `K₀` es `0x428a2f98`.

¿Por qué raíces de primos y no números cualesquiera? Porque cualquier constante elegida
por el diseñador podría esconder una debilidad que sólo el diseñador conoce. Tomarlas de
un cálculo que cualquiera puede repetir demuestra que no fueron elegidas a propósito. Se
llaman constantes *"nothing up my sleeve"* —"nada en la manga", como el mago que muestra
las manos vacías— y SHA-256 las necesita especialmente porque la diseñó la NSA.

> **↓ Capa 3 — una ronda.**

La función de compresión aplica **64 rondas** sobre el estado. Antes, expande los 16
palabras del bloque a 64, una por ronda (`W₀` a `W₆₃`): las primeras 16 son el bloque tal
cual, y cada una de las siguientes mezcla cuatro anteriores:

```
Wₜ = σ₁(Wₜ₋₂) + Wₜ₋₇ + σ₀(Wₜ₋₁₅) + Wₜ₋₁₆
```

Cada ronda hace esto, con todas las sumas **módulo 2³²**:

```
T₁ = h + Σ₁(e) + Ch(e, f, g) + Kₜ + Wₜ
T₂ = Σ₀(a) + Maj(a, b, c)

h ← g      d ← c
g ← f      c ← b
f ← e      b ← a
e ← d + T₁ a ← T₁ + T₂
```

Seis de las ocho palabras sólo **se corren un lugar**, y dos —`a` y `e`— reciben todo lo
nuevo. Es un registro que avanza, y en cada paso dos de sus casillas se recalculan con la
mezcla de todas.

Las cuatro funciones auxiliares son el corazón:

| Función | Definición | Qué hace, bit por bit |
|---|---|---|
| `Ch(e, f, g)` | `(e ∧ f) ⊕ (¬e ∧ g)` | *elegir*: donde `e` vale 1 toma el bit de `f`, donde vale 0 el de `g` |
| `Maj(a, b, c)` | `(a ∧ b) ⊕ (a ∧ c) ⊕ (b ∧ c)` | *mayoría*: vale 1 si al menos dos de los tres bits valen 1 |
| `Σ₀(a)` | `ROTR²(a) ⊕ ROTR¹³(a) ⊕ ROTR²²(a)` | mezcla cada bit de `a` con otros dos alejados |
| `Σ₁(e)` | `ROTR⁶(e) ⊕ ROTR¹¹(e) ⊕ ROTR²⁵(e)` | lo mismo con otras distancias |

`ROTRⁿ` es rotar la palabra `n` lugares a la derecha: los bits que salen por un extremo
entran por el otro. `σ₀` y `σ₁`, las de la expansión, son iguales en espíritu, con
distancias 7/18 y 17/19, más un corrimiento que sí descarta bits.

Después de las 64 rondas, cada palabra del estado se suma a la que había antes de
empezar, y esas ocho palabras concatenadas son los 256 bits de la huella.

> **↓ Capa 4 — la ronda, en compuertas.** Este es el piso.

Ahora cada operación de la ronda se reduce a las
[compuertas lógicas](A0-01-como-corre-un-programa.md#instrucción-de-máquina-y-compuerta-lógica).
Una palabra de 32 bits son 32 cables, y cada operación dice qué se hace en cada cable.

**Rotar cuesta cero compuertas.** Esta es la sorpresa del descenso. Una rotación no
calcula nada: en un circuito, `ROTR⁶` es **conectar el cable `i` de la entrada con el cable
`i+6` de la salida** (módulo 32). Es cableado, no lógica. En un procesador de propósito
general sí cuesta una instrucción, pero en un chip diseñado para SHA-256 —como los que se
usan para minar bitcoin, que calculan este mismo algoritmo— las rotaciones son gratis.

**XOR cuesta una compuerta por bit.** `ROTR² ⊕ ROTR¹³ ⊕ ROTR²²` son tres versiones del
mismo número con los cables cruzados de tres formas, entrando a dos filas de 32 compuertas
XOR. Eso es `Σ₀` entera: 64 compuertas y un poco de cableado.

**`Ch` es un selector de dos entradas por bit.** Por cada uno de los 32 bits, una
compuerta NOT sobre `e`, dos compuertas AND (`e ∧ f` y `¬e ∧ g`) y una que junta los dos
resultados. Como los dos términos nunca valen 1 a la vez —uno lleva `e` y el otro `¬e`—,
esa última puede ser OR o XOR indistintamente. Es exactamente el circuito que en
electrónica se llama **multiplexor**: `e` es la llave que elige.

**`Maj` son tres AND y dos XOR por bit**, directo de su fórmula.

**La suma módulo 2³² son 32 sumadores completos en fila.** El sumador de un bit que
describe A0-01 —un XOR para el resultado, un AND para el acarreo— necesita, para poder
encadenarse, una versión que además reciba el acarreo del bit anterior: el **sumador
completo**, que son dos XOR, dos AND y un OR. Se ponen 32 en fila, con el acarreo de cada
uno entrando al siguiente.

Y acá está la segunda sorpresa: **"módulo 2³²" tampoco cuesta nada.** Sumar módulo 2³²
significa descartar lo que no entra en 32 bits, y lo que no entra es exactamente el
acarreo que sale del último sumador. En el circuito, "módulo 2³²" es **no conectar ese
último cable a ningún lado.**

La ronda entera, entonces, es: cableado cruzado, filas de XOR, algunos AND y NOT, y cuatro
sumadores de 32 bits en cascada para armar `T₁`. Sesenta y cuatro veces.

> **↓ Capa 5 — por qué no se puede correr al revés.** Esta es la respuesta a la pregunta
> que justifica todo el capítulo.

Mirá las operaciones de la capa 4 y separalas en dos grupos.

**El XOR y la rotación son lineales.** En un sentido algebraico preciso: si pensás cada
bit como un número que sólo vale 0 o 1, y el XOR como la suma de esos números sin
acarreo, entonces rotar y hacer XOR son operaciones que se pueden escribir como un sistema
de ecuaciones lineales. Y un sistema de ecuaciones lineales **se resuelve**: el método de
eliminación de Gauss, el mismo de la secundaria, lo despeja mecánicamente, sin importar
cuántas rondas se hayan aplicado. Una función hecha sólo de rotaciones y XOR sería
**perfectamente reversible**, por más compleja que pareciera.

**El AND y el acarreo no son lineales.** `e ∧ f` no se puede escribir como una suma sin
acarreo de `e` y `f`: es un producto. Y el acarreo de una suma depende de los bits de
abajo de una forma que tampoco es lineal. Estos son los únicos ingredientes que rompen la
linealidad, y están puestos a propósito en tres lugares: `Ch`, `Maj` y las sumas módulo
2³².

Esa es la irreversibilidad, bajada a su mecanismo: **cada ronda mete productos de bits
dentro de sumas de bits, y después de 64 rondas las ecuaciones que habría que resolver
para volver atrás tienen grado tan alto que no hay método conocido más rápido que probar.**
No es que nadie encontró todavía la forma de invertir SHA-256 por falta de ingenio. Es que
la estructura de la función hace que invertirla sea, en el mejor caso conocido, el mismo
problema que adivinar.

Y por eso las dos operaciones que el diseño hace gratis —rotar y reducir módulo 2³²—
están ahí: son las que **esparcen** la no-linealidad. Un AND mezcla dos bits vecinos; la
rotación siguiente los manda lejos, y la ronda siguiente los mezcla con otros. Después de
unas pocas rondas cada bit de salida depende de todos los de entrada, que es lo que se vio
en el experimento de la avalancha.

### Vuelta al repo

En este repo nadie implementa SHA-256: se usa `hashlib.sha256` de la biblioteca estándar
de Python (`backend/mercadopago.py:303`) y la implementación que trae python-jose para
`HS256`. Implementar primitivas criptográficas a mano es el error clásico de seguridad, y
el repo no lo comete.

Lo que sí hace el repo es **elegir** SHA-256, y ahora esa elección se puede leer entera:
es la función que ningún ataque conocido rompió, y la que resiste por la razón de la capa
5, no por oscuridad.

---

## HMAC y firma simétrica

### El problema de origen

El JWT de este sistema lleva el `id_socio` adentro
([A0-12 lo describe campo por campo](A0-12-sesiones-y-autenticacion.md#jwt)). Si alguien
pudiera editarlo —cambiar `"id_socio": 7` por `"id_socio": 8`— vería los datos de otra
persona. Hace falta una marca pegada al mensaje que cumpla dos cosas:

- **Integridad:** si alguien toca un solo bit del mensaje, la marca deja de coincidir.
- **Autenticidad:** sólo quien tiene un secreto puede producir una marca válida.

Un hash solo cumple la primera y no la segunda: cualquiera puede calcular
`sha256(mensaje)`, así que un atacante edita el mensaje y recalcula la huella. Falta meter
un secreto en la cuenta.

### La idea ingenua, y por qué está rota

Lo primero que se le ocurre a cualquiera es `sha256(clave ‖ mensaje)` —la clave pegada
adelante del mensaje, y hashear todo junto—. Nadie sin la clave puede calcularlo. Parece
suficiente.

**Está roto, y la razón está en el diagrama de Merkle–Damgård.** Acordate: la huella *es*
el estado interno después del último bloque. Entonces un atacante que tiene
`sha256(clave ‖ mensaje)` tiene el estado de la función en ese punto, sin conocer la
clave. Puede cargar ese estado, **seguir hasheando** bloques nuevos que él elige, y
obtener la huella válida de `clave ‖ mensaje ‖ relleno ‖ lo_que_quiera`. Firmó un mensaje
más largo sin saber el secreto.

Se llama **ataque de extensión de largo**, y no es teórico: afectó a sistemas reales de
firma de pedidos a APIs. Que SHA-256 sea una buena función hash no alcanza: la forma de
usarla también tiene que ser correcta.

### HMAC

La respuesta es **HMAC**, publicada por Bellare, Canetti y Krawczyk en 1996 y estandarizada
como RFC 2104 al año siguiente. Tiene dos pasadas de hash:

```
HMAC(K, m) = H( (K′ ⊕ opad) ‖ H( (K′ ⊕ ipad) ‖ m ) )
```

> **↓ Capa 1 — cada pieza de la fórmula.**

- **`K′`** es la clave llevada exactamente al tamaño del bloque de la función: 64 bytes
  para SHA-256. Si la clave es más corta, se completa con ceros. **Si es más larga, primero
  se la hashea** y se usan esos 32 bytes.
- **`ipad`** es el byte `0x36` repetido 64 veces, y **`opad`** es `0x5C` repetido 64 veces.
  Son dos constantes distintas cualesquiera: lo que importa es que la clave entra a las
  dos pasadas **transformada de dos formas diferentes**.
- **La pasada interna** hashea la clave transformada seguida del mensaje. Su resultado ya
  depende del secreto, pero todavía es vulnerable a la extensión.
- **La pasada externa** vuelve a hashear ese resultado junto con la clave transformada de
  la otra forma. Y esto cierra el ataque: el atacante nunca ve el estado interno de la
  pasada interna, sólo el hash de un hash. No tiene de dónde continuar.

> **↓ Capa 2 — la clave de este sistema, adentro de la fórmula.**

La clave del JWT se genera, según el instructivo de `backend/auth.py:31-32`, con
`secrets.token_urlsafe(64)`: 64 bytes aleatorios escritos como
[86 caracteres de base64url](#aleatoriedad-criptográfica-y-base64url). Ochenta y seis
bytes es más que el bloque de 64, así que HMAC **la hashea primero** y trabaja con los 32
bytes resultantes. La clave efectiva del sistema son 256 bits, que es exactamente lo que
el diseño de HMAC-SHA256 da por óptimo: más largo no agrega seguridad, porque la pasada
lo comprime igual.

### Cómo se verifica una marca, y el ataque por reloj

Verificar un HMAC es **recalcularlo y comparar**. No hay otra forma: la función no se
invierte, así que quien recibe el mensaje con la marca calcula la marca que debería tener
y mira si coinciden.

Esa comparación tiene una trampa. Comparar dos textos con `==` los recorre carácter por
carácter y **corta en la primera diferencia**. Una marca que coincide en los primeros diez
caracteres tarda un poco más en rechazarse que una que difiere en el primero. Esa
diferencia es de nanosegundos, pero es medible con suficientes intentos, y un atacante
paciente puede adivinar la marca **un carácter por vez**, mirando cuál de sus intentos
tarda más. El secreto se filtra por el reloj.

La solución es comparar en **tiempo constante**: recorrer siempre todo, sin cortar. En este
repo aparece tres veces, las tres explícitas:

- **La firma del JWT:** python-jose 3.3.0 recalcula la firma y la compara con
  `hmac.compare_digest(sig, self.sign(msg))` (`jose/backends/native.py:69`, dentro del
  entorno virtual). Es lo que corre cuando `decodificar_token()` llama a `jwt.decode()`
  (`backend/auth.py:202`).
- **El token CSRF**, con la trampa explicada en el propio comentario: *"comparar strings
  con == corta apenas encuentra una diferencia, y ese tiempo distinto permite adivinar el
  token carácter por carácter"* (`backend/csrf.py:84-87`).
- **La firma de Mercado Pago**: `hmac.compare_digest(esperada, firma)`
  (`backend/mercadopago.py:305`), con la misma justificación en el docstring (líneas
  280-281).

### Vuelta al repo: el mismo mecanismo, dos relaciones de confianza

HMAC aparece en dos lugares del sistema, y lo interesante es que **la confianza está
repartida al revés en uno y en otro**.

**En el JWT, el sistema se firma a sí mismo.** `crear_token_acceso()` firma con
`jwt.encode(payload, SECRET_KEY, algorithm=ALGORITMO)` (`backend/auth.py:191`) y
`decodificar_token()` verifica con la misma clave (`auth.py:202`), llamado desde el
control de sesión en `backend/security.py:112`. La clave nunca sale del backend: el mismo
proceso firma al hacer login y verifica en cada pedido siguiente.

**En el webhook de Mercado Pago, firma un tercero y el sistema sólo verifica.**
`verificar_firma()` (`backend/mercadopago.py:270-305`) arma el texto que Mercado Pago
firmó —`id:{data_id};request-id:{x_request_id};ts:{ts};`, línea 299— calcula el HMAC con
el secreto compartido `MP_WEBHOOK_SECRET` y lo compara con el que llegó en la cabecera
`x-signature`. El problema que resuelve está en el docstring (líneas 274-276): la URL del
webhook es pública, y sin esta verificación *"acreditar cuotas gratis sería cuestión de
adivinar un número"*.

Y la decisión de qué hacer sin secreto es la correcta: **rechazar todo**
(`mercadopago.py:283-287`). *"Preferir rechazar todo antes que aceptar todo. Un webhook
sin verificar es una puerta abierta."* El patrón se llama **fallar cerrado**, y vuelve a
aparecer en la [clave secreta](#clave-secreta).

### Por qué está hecho así

**Qué se eligió:** firma simétrica —la misma clave firma y verifica— en lugar de firma
asimétrica, donde una clave privada firma y una pública verifica (el JWT lo permite con
`RS256`).

**Qué la justifica:** en el JWT un solo servicio firma y ese mismo servicio verifica.
Nadie más necesita comprobar los tokens, así que no hay a quién darle una clave pública.

**Qué se paga:** cualquiera que pueda verificar también puede firmar, porque tiene la misma
clave. Eso obliga a que la clave no salga nunca del backend, y hace que filtrarla sea
catastrófico: no permite leer sesiones, permite **fabricarlas**.

En el webhook la elección no fue de este sistema sino de Mercado Pago, y por la misma
lógica: es un secreto que se comparte con un solo destinatario.

---

## Sal y hash lento

### El problema de origen

La base tiene que poder responder "¿esta contraseña es la de esta persona?" sin guardar la
contraseña. Cada solución que se probó históricamente abrió el agujero que explica la
siguiente:

1. **Guardarlas en texto plano.** Quien lee la base, lee las contraseñas. Pasó miles de
   veces; la filtración más citada es la de RockYou en 2009, que dejó al descubierto unos
   32 millones de cuentas en texto plano.
2. **Guardar su hash, con una función rápida** (MD5, SHA-1). Ya no se leen: hay que
   calcular. Pero como la función es determinista, `sha256("123456")` da siempre lo mismo
   en todas las bases del mundo, y alguien puede **calcular una vez** el hash de millones de
   contraseñas comunes y guardarlos en una tabla. Después, romper una base robada es buscar
   en la tabla. Esas tablas precalculadas existen y se comparten; las más compactas se
   llaman *rainbow tables*.
3. **Agregar una sal.** Un valor aleatorio distinto para cada contraseña, que se hashea
   junto con ella. Ahora `123456` con la sal de una persona y `123456` con la sal de otra
   dan hashes distintos, y una tabla precalculada no sirve: habría que calcular una por
   cada sal posible. **La sal mata el trabajo compartido.**
4. **Pero la sal no alcanza.** No hace más lento el ataque contra *una* contraseña: el
   atacante que quiere romper una cuenta concreta ve su sal —la sal no es secreta— y se
   pone a probar. Con una función rápida, prueba millones por segundo. Falta que cada
   intento cueste caro.

### El hash lento

La respuesta es una función **deliberadamente cara**, y con un costo **ajustable** para
que siga siendo cara a medida que el hardware mejora. La que usa este sistema es
**bcrypt**, publicada por Niels Provos y David Mazières en 1999 (*"A Future-Adaptable
Password Scheme"*: el título ya dice que el punto es poder encarecerla con el tiempo).

bcrypt está construida sobre el cifrador Blowfish, y aprovecha su parte más cara: la
preparación de la clave, que llena cuatro tablas internas de 256 entradas de 32 bits —4 KB
de estado— con un proceso que hay que repetir. bcrypt repite esa preparación **2^costo
veces**. Cada punto más de costo duplica el tiempo.

> **↓ Capa 1 — la anatomía de un hash guardado.**

Esto es un hash real generado con la misma función que usa el backend, sobre una
contraseña de ejemplo:

```
$2b$12$O6WKte3cLlkFUaCd3AHyG.LVyyRH0vUlB4WKd2yr2RIXU5LT3ah6G
└┬─┘└┬┘└─────────┬──────────┘└──────────────┬───────────────┘
 │   │           │                          │
 │   │           │                          └ el hash: 31 caracteres
 │   │           └ la sal: 22 caracteres (128 bits aleatorios)
 │   └ el costo: 12, o sea 2¹² = 4.096 repeticiones
 └ la versión del algoritmo
```

Sesenta caracteres en total, que es lo que ocupa la columna `password_hash` de la tabla
`Usuario` por cada cuenta.

Fijate que **la sal va adentro del hash**. No hay una columna aparte para ella. Y ese
detalle es lo que hace funcionar la verificación: para comprobar una contraseña,
`verificar_password()` vuelve a hashear lo que la persona escribió **con la misma sal y
el mismo costo, que lee del hash guardado**, y compara (`backend/auth.py:60-74`). Su
docstring lo dice sin vueltas: *"Nunca se 'desencripta' el hash guardado: se vuelve a
hashear lo que la persona escribió (…) Por eso ni siquiera con acceso directo a la base se
pueden leer las contraseñas"* (líneas 62-65).

Los caracteres de la sal y del hash usan el mismo principio que
[base64url](#aleatoriedad-criptográfica-y-base64url) —seis bits por carácter— con un
alfabeto propio de bcrypt, que incluye `.` y `/`. Por eso la sal del ejemplo termina en
punto.

> **↓ Capa 2 — cuánto cuesta, medido en esta máquina.**

`bcrypt.gensalt()` sin argumentos elige costo 12 (el `$2b$12$` del ejemplo). Medido con la
biblioteca `bcrypt` del entorno virtual del backend:

| Función | Tiempo por hash | Hashes por segundo, un núcleo |
|---|---|---|
| SHA-256 (desde Python) | 367 nanosegundos | 2,73 millones |
| bcrypt, costo 12 | 171 milisegundos | 5,8 |

**bcrypt es 467.000 veces más lento.** Ese número es el argumento entero, y la sección
siguiente lo convierte en tiempo de ataque.

Los 171 ms los paga el sistema una vez por login, y es un precio que nadie percibe:
iniciar sesión ya cuesta varios viajes a São Paulo
([base remota](A-11-rendimiento.md#base-remota)). El atacante, en cambio, los paga
**por cada intento**.

> **↓ Capa 3 — el límite de 72 bytes.**

bcrypt sólo mira los primeros **72 bytes** de la contraseña. No es un límite de esta
biblioteca: es del algoritmo. El backend lo hace explícito en vez de esconderlo
(`backend/auth.py:38-48`): `_a_bytes()` codifica la contraseña a UTF-8 y la recorta a 72
bytes antes de hashear, porque una librería que *"lance una excepción con una contraseña
larga pero legítima"* es peor que un recorte documentado.

Son 72 **bytes**, no 72 caracteres, y la diferencia importa en castellano: una `ñ` o una
`á` ocupan dos bytes en UTF-8. Cómo un carácter se convierte en uno o varios bytes está en
[codificación](A0-01-como-corre-un-programa.md#codificación-de-caracteres-a-bytes-y-el-intérprete-que-adivina-mal).

### El hash corrupto es una contraseña incorrecta

`verificar_password()` devuelve `False` —y no una excepción— si el hash guardado está
dañado o tiene un formato que bcrypt no reconoce (`backend/auth.py:67-74`). El
razonamiento: *"para quien llama, un hash ilegible y una contraseña incorrecta son el mismo
caso — no entra"*. Es fallar cerrado otra vez, aplicado a un dato que llega mal de la base.

### Por qué está hecho así

**Qué se optimiza:** que una base robada no sirva para nada durante el tiempo que haga
falta para que las personas cambien sus contraseñas.

**Qué alternativa se descartó:** Passlib, la biblioteca que envuelve bcrypt y que usa medio
ecosistema de Python. El docstring de `backend/auth.py:9-14` explica por qué: está sin
mantenimiento desde 2020, es incompatible con bcrypt 4.1 en adelante, y la combinación
produce un error engañoso —*"password cannot be longer than 72 bytes"*— que aparece con
contraseñas de cualquier largo *"y manda a depurar en la dirección equivocada"*.

**Qué se paga:** 171 ms de CPU por login, y un límite de 72 bytes por contraseña.

**Nota sobre la irreversibilidad de bcrypt:** no se apoya en SHA-256 sino en Blowfish,
así que el descenso a compuertas de la sección anterior no la explica literalmente. El
argumento es el mismo —mezcla no lineal repetida hasta que invertirla equivale a probar—
aplicado a otra función. No se desarrolla otra vez: el mecanismo ya está en la capa 5 de
[SHA-256](#sha-256).

---

## Ataque de diccionario

### El problema de origen

La fuerza bruta pura —probar todas las contraseñas posibles— es inútil contra una
contraseña decente: ocho caracteres alfanuméricos ya son 218 billones de combinaciones.
El ataque real aprovecha otra cosa: **las personas no eligen contraseñas al azar.** Eligen
`123456`, el nombre del perro, `gimnasio2024`. Y esas elecciones son sorprendentemente
repetidas.

Un **diccionario** es la lista de las contraseñas que la gente realmente usa, ordenada por
frecuencia. La filtración de RockYou, al estar en texto plano, se convirtió en el
diccionario canónico: unos **14 millones de contraseñas distintas**, elegidas por personas
reales. Probar esa lista entera contra un hash robado encuentra una proporción enorme de
contraseñas reales.

### Los números, con lo medido acá

Con las velocidades de la tabla anterior, probar el diccionario completo contra **un solo
hash**, en **un solo núcleo**:

| Si las contraseñas se guardaran con… | Tiempo para los 14 millones |
|---|---|
| SHA-256 | **5,1 segundos** |
| bcrypt, costo 12 | **27,9 días** |

Y eso es contra una cuenta. **La sal multiplica por la cantidad de cuentas**: cada una
tiene su sal, así que cada una exige su propia pasada completa del diccionario. Sin sal,
una sola pasada rompe la base entera de una vez.

Dos precisiones para no engañarse con estos números:

**Un atacante serio no usa Python ni un núcleo.** Usa placas de video, que calculan
funciones como SHA-256 varios órdenes de magnitud más rápido que este Python. Con ese
hardware, el diccionario contra SHA-256 no tarda segundos: tarda una fracción. Pero bcrypt
fue diseñado contra justamente eso: sus 4 KB de tablas se consultan en un orden
impredecible en cada paso, y las placas de video son malas para ese patrón de acceso a
memoria. La ventaja que obtiene el atacante con una GPU es mucho menor contra bcrypt que
contra SHA-256. (Esto es un orden de magnitud publicado, no algo medido en esta máquina.)

**Lo que importa es la relación, no el número absoluto.** Cualquiera sea el hardware, el
atacante que enfrenta bcrypt costo 12 hace del orden de cien mil a un millón de veces
menos intentos por segundo que contra un hash rápido. Y como el costo se puede subir, esa
relación se puede mantener aunque el hardware mejore: es el *future-adaptable* del título
de 1999.

### El ataque que el hash lento no frena

El hash lento protege contra el **ataque sin conexión**: alguien se llevó la base y prueba
en su propia máquina, sin límite de intentos. No sirve contra el **ataque en línea**:
alguien que prueba contraseñas directamente en la pantalla de login. Ahí cada intento
cuesta un viaje de red, y el sistema tiene otro mecanismo, completamente distinto, que
traba la cuenta a los 5 fallos: el
[freno de intentos](A-07-autenticacion.md#freno-de-intentos-y-respuesta-indistinguible).

Son dos defensas para dos amenazas, y ninguna reemplaza a la otra.

### El ataque que el diccionario no puede hacer

Los diccionarios sólo funcionan contra contraseñas **elegidas por personas**. Contra una
contraseña generada al azar no hay lista que ayude: sólo queda la fuerza bruta sobre el
espacio completo.

Por eso el sistema **genera** la contraseña temporal del alta en lugar de dejar que el
personal del mostrador tipee una
([contraseña temporal y primer ingreso](A-07-autenticacion.md#contraseña-temporal-y-primer-ingreso)):
un recepcionista con cola adelante escribiría `Gimnasio1`, y esa contraseña estaría en el
diccionario del atacante antes que en la base. La generada son 96 bits aleatorios (la
sección siguiente cuenta por qué 96 y no 72): 2⁹⁶ posibilidades, un número de 29 cifras.

### Vuelta al repo: un hash no se lee, se reemplaza

Todo lo anterior tiene una consecuencia operativa que en este proyecto ya ocurrió.

Como el hash no se invierte, **nadie puede recuperar una contraseña**: ni el personal, ni
el dueño, ni quien administra la base. Si una persona la pierde, la única salida es
fabricarle una nueva y **reemplazar** el hash guardado.

Dentro de la aplicación eso lo hace el reseteo de contraseña. Pero hay un caso donde la
aplicación no alcanza: si el único Dueño pierde su propia clave temporal, no hay otro
Dueño que pueda resetearla, porque sólo un Dueño opera sobre un Dueño. La salida está
documentada en `CLAUDE.md` y en `docs/ESTADO-ACTUAL.md`: generar un hash nuevo con
`auth.hashear_password` (`backend/auth.py:55-57`) y escribirlo directamente en la columna
`password_hash`. El comando exacto está guardado en `docs/comando para hashear.txt`:

```
.venv/Scripts/python.exe -c "from auth import hashear_password; print(hashear_password('...'))"
```

No es una puerta trasera: es la consecuencia lógica de que el hash no se pueda leer.
Quien tiene acceso de escritura a la base siempre pudo reemplazar un hash; lo que nunca
pudo es leerlo.

---

## Aleatoriedad criptográfica y base64url

### El problema de origen

La contraseña temporal, el token CSRF y la clave del JWT tienen que ser **impredecibles**.
Y "aleatorio" en programación significa dos cosas muy distintas.

El módulo `random` de Python usa un generador llamado **Mersenne Twister**, diseñado para
simulaciones: rápido, con muy buenas propiedades estadísticas y **completamente
predecible**. Su estado interno son 624 números de 32 bits, y cada salida es una
transformación reversible de ese estado. Quien observe 624 salidas consecutivas puede
reconstruir el estado entero y **calcular todas las salidas futuras**. Para una simulación
no importa. Para una contraseña es una catástrofe: quien vea suficientes contraseñas
temporales podría predecir la próxima.

El módulo `secrets` usa otra fuente: la que el sistema operativo prepara específicamente
para criptografía, alimentada con eventos que un atacante no controla —tiempos de
interrupciones de hardware, ruido de dispositivos— y construida para que ver sus salidas
no revele las siguientes. En Windows, Python la toma de la API criptográfica del sistema.

La elección está escrita en `backend/auth.py:94-97`, con el ataque incluido:
*"`secrets` y no `random`: random usa un generador predecible pensado para simulaciones,
y con unas pocas salidas se puede reconstruir su estado interno y adivinar las
siguientes."*

### base64url: cómo se escribe un byte aleatorio

Lo que devuelve la fuente del sistema operativo son **bytes**: valores de 0 a 255,
muchos de los cuales no son caracteres imprimibles. Para poner eso en una cookie, una
cabecera HTTP o una contraseña que alguien tiene que tipear, hace falta escribirlo con
caracteres seguros.

> **↓ Capa 1 — de 8 bits a 6.**

La idea de base64 es reagrupar los bits. Tres bytes son 24 bits; 24 bits se pueden partir
en **cuatro grupos de 6**. Y 6 bits son 64 valores posibles, que se pueden representar con
un alfabeto de 64 caracteres seguros:

```
tres bytes:     01100111 01101001 01101101         ("gim")
en grupos de 6: 011001 110110 100101 101101
índices:          25     54     37     45
caracteres:        Z      2      l      t
```

`A-Z` son los índices 0 a 25, `a-z` del 26 al 51, `0-9` del 52 al 61. Los dos últimos
índices, 62 y 63, son los que distinguen las variantes: el base64 original usa `+` y `/`.

> **↓ Capa 2 — por qué "url".**

`+` y `/` tienen significado dentro de una URL —`/` separa tramos de ruta, `+` puede
leerse como espacio— y el base64 original además completa con `=` al final, que en una
URL separa clave de valor. **base64url** reemplaza `+` por `-` y `/` por `_`, y omite el
relleno. El resultado se puede poner en una URL, una cookie o una cabecera sin escaparlo.

Y porque ese alfabeto no incluye el punto, el JWT puede usar `.` para separar sus tres
tramos, como [explica A0-12](A0-12-sesiones-y-autenticacion.md#jwt).

> **↓ Capa 3 — la aritmética, y por qué importa.**

Cada 3 bytes se convierten en 4 caracteres. Sin relleno, `n` bytes dan `⌈4n/3⌉`
caracteres. Los tres usos de este repo, medidos:

| Llamada | Bytes aleatorios | Bits | Caracteres | Dónde |
|---|---|---|---|---|
| `secrets.token_urlsafe(12)` | 12 | 96 | **16** | contraseña temporal, `backend/auth.py:99` |
| `secrets.token_urlsafe(32)` | 32 | 256 | **43** | token CSRF, `backend/csrf.py:60` |
| `secrets.token_urlsafe(64)` | 64 | 512 | **86** | generador de la clave del JWT, `backend/auth.py:32` |

**El argumento de `token_urlsafe` es la cantidad de bytes, no de caracteres.** Esa
confusión es tan fácil de cometer que el propio repo la cometió, como se ve más abajo.

Hay un cuarto uso de la misma fuente, sin base64: `secrets.randbelow(10000)` en
`generar_username()` (`backend/auth.py:134`), para el caso casi imposible de un nombre sin
un solo carácter alfanumérico. Ahí la impredecibilidad no importa, pero usar la misma
fuente en todo el módulo evita que alguien copie el patrón equivocado.

### La confusión entre bytes y caracteres, ya cometida una vez

Este repo cometió exactamente ese error, y conviene verlo porque es el que cualquiera
comete. El comentario original sobre `LARGO_PASSWORD_TEMPORAL` decía *"12 caracteres de
token_urlsafe ≈ 72 bits de entropía"*. La cuenta era coherente consigo misma —12
caracteres × 6 bits = 72 bits— pero partía de una premisa falsa: `token_urlsafe(12)` no
produce 12 caracteres sino **12 bytes, que se escriben con 16 caracteres y suman 96
bits.** Una salida real de esa llamada es `e9nCJaRDT7_j37op`, dieciséis caracteres.

Había dos formas de resolverlo: bajar a `token_urlsafe(9)`, que da exactamente 12
caracteres y 72 bits, o dejar el código y corregir el comentario. El dueño eligió la
segunda: se conservan los 96 bits a cambio de dictar cuatro caracteres más por teléfono.
El comentario actual (`backend/auth.py:84-86`) lo dice así: *"12 BYTES aleatorios, no
caracteres: 96 bits, que token_urlsafe escribe con 16 caracteres de base64url"*.

El nombre de la constante, `LARGO_PASSWORD_TEMPORAL`, sigue sugiriendo un largo en
caracteres. Por eso el comentario arranca con "BYTES" en mayúsculas: es la palabra que
evita que el próximo que lo lea cometa el mismo error.

---

## Clave secreta

### El problema de origen

Todo lo anterior mueve la seguridad del sistema a **un solo lugar**. HMAC no es secreto,
SHA-256 no es secreto, el formato del JWT no es secreto. Lo único secreto es la clave. Si
la clave se filtra, cualquiera puede fabricar un JWT con el `id_socio` y los roles que
quiera, y el backend lo va a aceptar como auténtico, porque lo es.

Esto no es un defecto del diseño: es **el** diseño. Tiene un nombre, el principio de
Kerckhoffs (1883): un sistema criptográfico tiene que ser seguro aunque el atacante
conozca todo menos la clave. La consecuencia práctica es que la seguridad deja de depender
de mantener escondido el código —cosa que un repo en GitHub no puede hacer— y pasa a
depender de guardar un solo valor.

### La clave de este sistema

`backend/auth.py:28-33`:

```python
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "Falta JWT_SECRET_KEY en el .env. Generá una con: "
        'python -c "import secrets; print(secrets.token_urlsafe(64))"'
    )
```

Tres decisiones en seis líneas:

**Vive en el entorno, no en el código.** Se lee de
[una variable de entorno](A0-01-como-corre-un-programa.md#variable-de-entorno-y-archivo-env),
que se carga del `backend/.env`. Ese archivo nunca se commitea, y es uno de los dos `.env`
del repo que existen separados a propósito: el del frontend nunca lleva nada privado
porque sus variables terminan copiadas adentro del código que baja el navegador.

**Sin clave, el backend no arranca.** El `raise` está al nivel del módulo, así que falla
en el momento en que alguien importa `auth`, antes de levantar ninguna ruta. Es fallar
cerrado en su versión más estricta: un backend sin clave no podría firmar sesiones, y uno
que arrancara con una clave vacía o por defecto las firmaría con un secreto que cualquiera
conoce.

**El mensaje de error dice cómo generarla.** Con 64 bytes de la fuente criptográfica:
512 bits, [86 caracteres](#aleatoriedad-criptográfica-y-base64url). El instalador
`instalar.ps1` la genera solo al crear el `.env`, así que nadie tiene que inventarla.

### El byte que, si cambia, invalida todo

Por el [efecto avalancha](#la-propiedad-que-se-ve-el-efecto-avalancha), cambiar **un solo
bit** de la clave cambia la firma de todo mensaje en la mitad de sus bits. Así que rotar la
clave —reemplazarla por otra— tiene un efecto inmediato y total: **toda sesión abierta
deja de verificar**, de todas las personas, en el mismo instante.

Eso la vuelve la única herramienta de revocación que tiene el sistema. El JWT no se puede
anular de a uno, porque el servidor no guarda una lista de sesiones: es la decisión que
`docs/vulnerabilidades a arreglar.md` anota como V-08, y que se explica en
[caducidad y revocación](A0-12-sesiones-y-autenticacion.md#caducidad-y-revocación). Si
hiciera falta cortar la sesión de alguien que se sabe comprometido, rotar la clave lo
logra, al precio de cortarle la sesión a todos los demás también. Todo o nada.

### La segunda clave

`MP_WEBHOOK_SECRET` es el otro secreto del sistema, y se comporta distinto por una sola
razón: **se comparte con un tercero.** Mercado Pago la tiene, porque la usa para firmar sus
avisos. Rotarla no corta ninguna sesión, pero exige cambiarla de los dos lados a la vez;
si no, el backend empieza a rechazar todos los pagos, que es exactamente lo que el fallar
cerrado de `mercadopago.py:283-287` promete hacer.

### Por qué está hecho así

**Qué se optimiza:** que el código pueda ser público —y lo es, está en GitHub— sin que eso
comprometa nada.

**Qué se paga:** un punto único de falla. Toda la seguridad de las sesiones vale lo que
valga el cuidado con un archivo `.env`.

**Cómo se llama:** el principio de Kerckhoffs para la clave, y fallar cerrado para la
falta de clave.

---

## Con qué se conecta

- **Es el mismo problema que…** el
  [freno de intentos](A-07-autenticacion.md#freno-de-intentos-y-respuesta-indistinguible):
  probar contraseñas, en línea contra la pantalla de login y sin conexión contra una base
  robada; cada uno tiene su defensa.
- **Es la misma idea que…** la
  [respuesta indistinguible](A-07-autenticacion.md#freno-de-intentos-y-respuesta-indistinguible)
  de una cuenta trabada: `compare_digest` no filtra el secreto por el reloj, y el mensaje
  idéntico no filtra el estado de la cuenta por el texto.
- **Existe por culpa de…** la [identidad firmada](A-07-autenticacion.md#identidad-firmada):
  sin HMAC, el `id_socio` que viaja en el JWT se podría editar.
- **Se contradice con…** `calentar_pool()` de [rendimiento](A-11-rendimiento.md#pool-de-conexiones),
  que nunca frena el arranque, mientras que la falta de clave sí lo frena. La regla que
  concilia las dos es la gravedad: un pool frío es un login lento; una clave ausente es un
  sistema sin seguridad.
- **Existe por culpa de…** la
  [codificación](A0-01-como-corre-un-programa.md#codificación-de-caracteres-a-bytes-y-el-intérprete-que-adivina-mal):
  el límite de bcrypt es de 72 bytes, y una `ñ` ocupa dos.
- **Es la misma idea que…** el [token CSRF](A0-12-sesiones-y-autenticacion.md#token-csrf-de-doble-envío)
  y la contraseña temporal: bytes de la fuente del sistema operativo, escritos en
  base64url.
