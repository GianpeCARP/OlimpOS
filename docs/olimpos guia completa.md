# OlimpOS — Guía completa de la base de datos

**FORGE · Documento de estudio · Todo lo que hay que saber**

Este documento está escrito para que alguien que nunca tocó una base de datos pueda
leerlo de principio a fin y terminar entendiendo tanto los conceptos generales como
este sistema en particular. Las primeras secciones enseñan; las del medio describen;
las últimas sirven de referencia.

**Estado del sistema:** 41 tablas · 288 columnas · 66 claves foráneas · 13 tipos
enumerados · 11 restricciones de rango · 34 índices (4 parciales) · 4 funciones y
8 disparadores. PostgreSQL 14 o superior.

---

# ÍNDICE

**Parte I — Conceptos**
1. Qué es una base de datos relacional
2. Tablas, filas y columnas
3. Claves primarias
4. Claves foráneas
5. Tipos de dato y tipos enumerados
6. Restricciones
7. Índices
8. Disparadores
9. Transacciones
10. El principio del dato derivado

**Parte II — Normalización**
11. El problema que resuelve
12. Primera forma normal
13. Segunda forma normal
14. Tercera forma normal
15. Cuándo repetir está bien
16. Más allá de la tercera

**Parte III — El negocio**
17. Qué vende el gimnasio
18. El personal
19. La política de dinero
20. Los cuatro criterios de diseño

**Parte IV — Las 41 tablas**
21. Personas y roles
22. El socio
23. El dinero
24. Actividades y turnos
25. Rutinas
26. Dietas

**Parte V — Las reglas**
27. Restricciones de rango
28. Índices únicos parciales
29. Los cuatro disparadores
30. Claves foráneas compuestas

**Parte VI — Referencia**
31. Decisiones tomadas y por qué
32. Lo que quedó abierto
33. Preguntas de defensa oral
34. Glosario

---

# PARTE I — CONCEPTOS

## 1. Qué es una base de datos relacional

Una base de datos es un lugar donde se guarda información de forma organizada. La
palabra **relacional** describe cómo se organiza: la información se reparte en
tablas separadas que se conectan entre sí, en lugar de amontonarse en un solo lugar.

El modelo relacional lo formuló **Edgar F. Codd** en 1970, trabajando en IBM. Su
idea central era que los datos debían poder consultarse por su contenido y no por
la ubicación física donde estaban guardados, y que la estructura debía poder
cambiarse sin reescribir todos los programas que la usaban.

El motor que usa OlimpOS se llama **PostgreSQL**. Es el programa que efectivamente
guarda los datos y hace cumplir las reglas. El lenguaje para hablarle se llama
**SQL**.

**Por qué separar en tablas.** Supongamos que se guardara todo junto: una sola
planilla gigante con el socio, su membresía, sus pagos y sus reservas. Cada vez que
el socio reserva un turno habría que repetir su nombre, su documento y su
dirección. Con cincuenta reservas, cincuenta copias de sus datos. Si se muda, hay
que corregir las cincuenta, y si una falla, el sistema queda mintiendo.

Separando en tablas, los datos del socio están una sola vez y todo lo demás
apunta hacia ellos.

## 2. Tablas, filas y columnas

Una **tabla** representa una clase de cosa: los socios, los pagos, los turnos. Se
parece a una hoja de cálculo pero con reglas que se cumplen siempre.

- Las **columnas** son los campos. En `Socio`: número de socio, código de acceso,
  fecha de alta, objetivo.
- Las **filas** son los casos concretos. Una fila por socio.

Cada columna tiene un **tipo** declarado, y la base rechaza cualquier dato que no
lo respete. No se puede escribir texto donde va una fecha. Una hoja de cálculo lo
permitiría y nadie se enteraría hasta que algo fallara meses después.

Una columna también puede declararse **obligatoria** (`NOT NULL`). Si lo es, no se
puede guardar una fila que la deje vacía.

## 3. Claves primarias

La **clave primaria** identifica a cada fila sin ambigüedad. En `Socio` es
`id_socio`: un número que no se repite nunca y que la base genera automáticamente
cada vez que se inserta una fila.

**Por qué no usar el DNI, que también es único.** Porque un DNI puede estar mal
cargado y hay que corregirlo. Si fuera la clave primaria, corregirlo obligaría a
corregir todos los lugares del sistema que lo mencionan. Un identificador interno
no significa nada fuera del sistema, así que nunca hay razón para cambiarlo.

En la jerga, un identificador inventado como éste se llama **clave subrogada**, y
un dato del mundo real que también podría identificar la fila —como el DNI— se
llama **clave candidata natural**. La práctica habitual es usar la subrogada como
clave primaria y proteger la natural con una regla de unicidad, que es exactamente
lo que hace OlimpOS con `dni`, `numero_socio`, `codigo_rfid` y `legajo`.

Una clave primaria también puede estar formada por **dos columnas juntas**. En
`Socio_Patologia` la clave es la combinación de socio y patología: ningún socio
puede tener la misma patología registrada dos veces, pero sí puede tener varias
distintas.

## 4. Claves foráneas

Es el mecanismo que conecta dos tablas. La tabla `Membresia` tiene una columna
`id_socio` que no guarda el nombre del socio sino su identificador. Para saber de
quién es la membresía, la base va a buscar esa fila a `Socio`.

Lo importante es la **garantía**: si alguien intenta crear una membresía de un
socio que no existe, la base rechaza la operación. Es imposible que quede una
membresía huérfana. Esta propiedad se llama **integridad referencial** y es una de
las razones principales para usar una base de datos en vez de archivos sueltos.

**Sobre el borrado.** Una clave foránea puede configurarse para que, al borrar la
fila referenciada, arrastre a las que la señalan. En OlimpOS **ninguna** está
configurada así, y es deliberado: la política del sistema es que nada se borra. Un
pago se marca como cancelado o reembolsado, nunca se elimina. Al no declarar
comportamiento de borrado, rige el que trae el estándar por omisión, que es impedir
el borrado si hay filas que dependen de esa. Esa omisión es la defensa de la
política.

**Todas son diferibles.** Significa que la verificación puede posponerse hasta el
final de la operación completa. Hace falta porque dar de alta un empleado son dos
pasos —crear el empleado y después su especialidad— y en el instante intermedio la
regla estaría técnicamente incumplida.

## 5. Tipos de dato y tipos enumerados

Los tipos que usa OlimpOS:

| Tipo | Para qué | Ejemplo |
|---|---|---|
| `integer` | Números enteros | Cantidad de series |
| `numeric(10,2)` | Números con decimales exactos | Un precio: 10 dígitos, 2 decimales |
| `varchar(n)` | Texto con largo máximo | Un nombre, hasta 100 caracteres |
| `text` | Texto sin límite | Observaciones |
| `date` | Una fecha | Fecha de alta |
| `time` | Una hora | Hora del turno |
| `timestamp` | Fecha y hora juntas | Momento exacto del pago |
| `boolean` | Verdadero o falso | Si está activo |

**Por qué los precios no usan el tipo de números decimales corriente.** El tipo
habitual para decimales en informática guarda aproximaciones, no valores exactos. En
dinero eso produce diferencias de centavos que se acumulan. `numeric` guarda el
valor exacto, cuesta un poco más de rendimiento y es lo correcto para plata.

**Tipos enumerados.** Algunas columnas sólo admiten unos pocos valores. Un tipo
enumerado declara esa lista de antemano y rechaza cualquier otro valor. Sin esto,
alguien escribiría «Confirmado», otro «CONFIRMADO» y un tercero con un error de
tipeo, y para la base serían tres estados distintos.

Los trece de OlimpOS:

| Nombre | Valores |
|---|---|
| `estado_asignacion` | ACTIVA, FINALIZADA, CANCELADA |
| `estado_congelamiento` | ACTIVO, FINALIZADO, CANCELADO |
| `estado_inscripcion` | ACTIVA, VENCIDA, CANCELADA |
| `estado_membresia` | ACTIVA, VENCIDA, SUSPENDIDA, CANCELADA |
| `estado_pago` | CONFIRMADO, PENDIENTE, CANCELADO, REEMBOLSADO |
| `estado_reserva` | RESERVADA, EN_ESPERA, CANCELADA_SOCIO, CANCELADA_GIMNASIO |
| `estado_turno` | HABILITADO, CANCELADO |
| `metodo_pago` | EFECTIVO, DEBITO, CREDITO, TRANSFERENCIA, BILLETERA_VIRTUAL |
| `metodo_registro` | RFID, MANUAL |
| `origen_congelamiento` | SOCIO, GIMNASIO |
| `tipo_baja` | VOLUNTARIA, MORA, ADMINISTRATIVA |
| `tipo_limite` | POR_SEMANA, POR_MES, CLASE_SUELTA |
| `tipo_telefono` | CELULAR, FIJO |

## 6. Restricciones

Una **restricción** es una condición que todo dato debe cumplir para poder
guardarse. La base la verifica sola, venga el dato de donde venga.

Podrían escribirse en el programa, pero ahí dependen de que ningún programador se
olvide. En la base se cumplen siempre.

Las que usa OlimpOS son de rango y de coherencia interna de la fila: que un
descuento esté entre 0 y 100, que una fecha de fin no sea anterior a la de inicio,
que un turno no tenga profesor y entrenador a cargo al mismo tiempo.

**Su limitación.** Una restricción sólo puede mirar la fila que se está
escribiendo. No puede contar filas de otra tabla. Para eso hacen falta
disparadores.

## 7. Índices

Sin índice, buscar una fila obliga a recorrer la tabla entera. Con índice, la base
salta directo, igual que uno busca una palabra en el índice de un libro en vez de
leer todas las páginas.

La estructura habitual se llama **árbol B** (B-tree) y tiene una propiedad que
conviene conocer: se puede recorrer por sus **columnas iniciales**. Un índice
sobre socio, ejercicio y fecha sirve también para buscar sólo por socio, o por
socio y ejercicio. Por eso un índice sobre socio y ejercicio a secas sería
redundante si ya existe el de tres columnas: no aporta nada y hace más lenta cada
escritura. En OlimpOS había uno así y se eliminó.

**Índices únicos.** Además de acelerar, un índice puede prohibir repeticiones. Es
la forma de decir «esto no puede pasar dos veces».

**Índices parciales.** Un índice puede aplicarse sólo a las filas que cumplen una
condición. Es lo que permite decir «una sola membresía **activa** por socio» sin
decir «una sola membresía en toda su vida». Ver la sección 28.

**El costo.** Los índices no son gratis: ocupan espacio y hacen más lenta cada
escritura, porque hay que actualizarlos. Se ponen donde hacen falta, no en todas
partes.

## 8. Disparadores

Un **disparador** (trigger) es un pedazo de código que la base ejecuta sola cada
vez que alguien escribe en cierta tabla, y que puede rechazar la operación.

Existe para las reglas que una restricción no puede expresar, porque necesitan
mirar otras tablas. Para saber si un turno está lleno hay que contar sus reservas,
y eso está en otra tabla.

**Diferidos.** Los cuatro de OlimpOS revisan al final de la operación completa y no
en cada paso intermedio. Sin eso sería imposible dar de alta un empleado, y
tampoco se podría cancelar una reserva y promover a alguien de la lista de espera
en un solo movimiento.

## 9. Transacciones

Una **transacción** agrupa varias operaciones en una sola unidad: o se completan
todas, o no se completa ninguna.

Es lo que impide que una operación quede a medias. Al cortar un congelamiento y
empezar otro, si el sistema fallara entre ambos pasos, el socio quedaría sin
compensación. Dentro de una transacción eso no puede pasar: si el segundo paso
falla, el primero se deshace.

## 10. El principio del dato derivado

Es la idea que más decisiones explica en este sistema, así que conviene entenderla
bien.

> **Si un dato se puede calcular a partir de otros, no se guarda: se calcula.**

El peso actual de un socio no es una columna de `Socio`. Sale de buscar en
`Registro_Salud` la medición más reciente:

```sql
SELECT peso FROM "Registro_Salud"
WHERE id_socio = 42
ORDER BY fecha DESC LIMIT 1;
```

**Por qué no guardarlo igual, por comodidad.** Porque existirían dos versiones del
mismo dato. Tarde o temprano alguien actualiza una y se olvida de la otra, y a
partir de ahí el sistema tiene dos respuestas para la misma pregunta y ninguna
forma de saber cuál es la buena.

Aplicaciones concretas en OlimpOS:

- No hay estados «asistió» o «ausente»: se deducen de si hay o no una fila en
  `Asistencia`.
- No hay tabla de deudas: si no hay membresía activa, el socio debe.
- No hay contador de clases restantes: se cuentan las reservas.

**La excepción.** Un dato que *parece* derivado a veces no lo es. Las calorías
diarias de una dieta parecían la suma de sus comidas, pero son el objetivo que
pauta el nutricionista. Que la suma real difiera del objetivo es información
válida, no un error. Sólo se puede distinguir preguntándole a quien conoce el
negocio.

---

# PARTE II — NORMALIZACIÓN

## 11. El problema que resuelve

El enemigo se llama **redundancia**: el mismo dato guardado en dos lugares.

El daño no es el espacio ocupado. Es que un día alguien actualiza uno y se olvida
del otro. A partir de ahí el sistema tiene dos respuestas para la misma pregunta.

Las reglas para evitarlo se llaman **formas normales**. Las formuló Codd en los
años setenta, y la tercera la refinó junto con Raymond Boyce. Se aplican en orden:
cada una supone que la anterior ya se cumple.

## 12. Primera forma normal

**Cada casilla guarda un solo valor.** Nada de listas apretadas dentro de una
celda.

**Mal:** una columna `patologias` con el texto «asma, hipertensión».

**Bien:** una tabla `Socio_Patologia` con una fila por cada patología.

**Por qué importa.** Con el texto apretado es imposible preguntar cuántos socios
tienen asma sin ponerse a buscar dentro de las cadenas de texto. Basta un espacio
de más o una mayúscula para que dos escrituras del mismo valor sean distintas. Y no
hay forma de garantizar que la patología escrita exista realmente.

**Dónde se aplica en OlimpOS:** `Telefono`, `Contacto_Emergencia`,
`Socio_Patologia`, `Rutina_Ejercicio` y `Comida` existen todas por esta razón. Y
en `Persona` el domicilio está descompuesto en calle, número y localidad en vez de
ser un solo texto.

## 13. Segunda forma normal

**Ningún dato puede depender de sólo una parte de una clave compuesta.** Sólo
aplica a tablas cuya clave primaria tiene dos o más columnas.

En `Socio_Patologia` la clave es socio más patología:

- `fecha_diagnostico` depende de las dos cosas juntas. Correcto.
- La descripción de qué es el asma dependería sólo de la patología. Por eso vive
  en `Patologia` y no acá.

**Qué pasaría si estuviera acá.** La descripción del asma se repetiría idéntica en
cada socio asmático. Corregir una errata obligaría a corregir todas las copias.

## 14. Tercera forma normal

**Ningún dato puede depender de otro dato que tampoco sea clave.** Se llama
**dependencia transitiva** y es la más difícil de ver.

Si `A` determina `B`, y `B` determina `C`, entonces guardar `C` junto a `A` es una
dependencia transitiva.

**Mal:** guardar en `Membresia` el nombre y la duración del tipo de membresía. El
nombre no depende de esta membresía en particular: depende del tipo. La cadena es
membresía → tipo → nombre.

**Bien:** guardar sólo cuál es el tipo. El nombre y la duración viven en
`Tipo_Membresia`.

**Qué pasaría si estuviera copiado.** El día que el dueño le cambia el nombre al
plan, habría que corregir miles de filas. Basta que falle una para que el sistema
quede inconsistente.

**Otro caso, en `Empleado`.** El empleado tiene sede, y la sede tiene dueño. El
dueño **no** se guarda en `Empleado`: se obtiene siguiendo la conexión.

## 15. Cuándo repetir está bien

No toda repetición es un error. Hay dos casos legítimos, y distinguirlos es lo que
separa aplicar las reglas de entenderlas.

### Caso 1 — Son dos hechos distintos

`Membresia.precio_pactado` repite un número que también está en
`Tipo_Membresia.precio_actual`. Y no es redundancia.

Uno es **lo que se cobra hoy**. El otro es **lo que se le cobró a esa persona ese
día**. Que se separen no es un error: es exactamente el punto. Si el precio sube,
el registro viejo tiene que seguir diciendo lo que realmente se pagó.

Lo mismo pasa con `Inscripcion_Actividad.precio_pactado` y con
`Pago.monto_descuento`. Este último guarda los pesos efectivamente descontados en
lugar de recalcularlos, porque la promoción puede cambiar o vencer después y hay
que poder reconstruir qué se cobró ese día.

**Cómo distinguirlo:** preguntarse si los dos valores *pueden* separarse
legítimamente. Si sí, son dos hechos y no hay redundancia. Si separarse sería un
error, hay redundancia.

### Caso 2 — Redundancia controlada por restricción

A veces se repite un dato a propósito y se le pide a la base que impida que las
copias se contradigan.

`Promocion` guarda quién es el dueño, aunque también podría deducirse de la sede.
Se conserva porque las promociones que valen para todas las sedes no tienen sede
de la cual deducirlo. Para que no se desincronice, una clave foránea compuesta
obliga a que coincidan cuando sí hay sede.

> **La regla que conviene retener: la redundancia controlada por una restricción
> no es redundancia. La redundancia libre sí lo es.**

Lo que la tercera forma normal prohíbe es la repetición que *puede* desincronizarse.
Si la base garantiza que las dos copias nunca divergen, el peligro no existe.

## 16. Más allá de la tercera

La tercera forma normal no elimina absolutamente toda la redundancia posible.

Quedan casos poco frecuentes, que aparecen cuando hay varias claves candidatas
superpuestas, y que sólo resuelve la **forma normal de Boyce-Codd**. Más allá
todavía están la cuarta y la quinta, que atienden anomalías más exóticas y que casi
ningún sistema real persigue.

Para un sistema de gestión, llegar a la tercera es el objetivo razonable y es lo
que se exige habitualmente.

---

# PARTE III — EL NEGOCIO

## 17. Qué vende el gimnasio

Tres actividades: **musculación**, **yoga** y **boxeo**. Las tres se venden bajo el
mismo modelo, con tres modalidades cada una: por semana, por mes o clase suelta.

Además está la **membresía**, que es lo que da acceso al lugar. Son cosas
distintas: la membresía es el permiso general, la inscripción es la compra de una
actividad concreta.

El cliente modelo es un gimnasio de **una sola sede**. El esquema soporta varias,
pero eso es previsión y no un requerimiento actual.

## 18. El personal

Dos roles que hacen cosas distintas y no se mezclan:

- **Entrenador** — arma rutinas de musculación y hace seguimiento personalizado.
- **Profesor** — dicta las clases grupales con horario fijo.

Una misma persona puede ser las dos cosas. En la jerga se dice que son **subtipos
solapados**. Hay además nutricionistas y recepcionistas; el recepcionista no
produce nada propio, sólo opera el sistema.

## 19. La política de dinero

Es donde más se discutió, así que conviene tenerlo claro.

**Prepago.** Se paga y se entra. No hay débito automático ni suscripción
recurrente: los cobros online son puntuales, uno por vez.

**Cuando el gimnasio es el responsable del perjuicio** —cierra por refacción,
corta el servicio— **no se devuelve dinero: se congela la membresía** y el
vencimiento se extiende. El socio recibe los días que pagó, sólo que más tarde. Por
eso el congelamiento distingue si lo pidió el socio o lo impuso el gimnasio.

**Cuando el socio se da de baja a mitad de período**, pierde el saldo. Es política
comercial, no una limitación del sistema.

**La devolución de dinero queda para lo residual**: casos donde no hay servicio que
extender, típicamente un cobro duplicado. Y ahí es siempre **total**. No existen
reembolsos parciales, por diseño.

**Consecuencia directa: no hay tabla de deudas.** Si no hay membresía activa, el
socio no tiene acceso. El estado «debe» es derivable.

**Nada se borra.** Los pagos se marcan cancelados o reembolsados, nunca se
eliminan. Vale para casi todo el modelo.

**Renovación anticipada.** Si el socio paga el mes siguiente antes de que venza el
actual, la membresía nueva no nace al cobrar: nace cuando vence la anterior. Así
nunca hay dos activas al mismo tiempo. El pago queda registrado con el período que
cubre y se vincula a la membresía cuando ésta se crea.

## 20. Los cuatro criterios de diseño

Todo el esquema se explica con estas cuatro reglas.

**1. No guardar lo que se puede derivar.** Ver la sección 10.

**2. Las decisiones de negocio van como datos, no como constantes en el código.**
Si el dueño tiene que llamar a un programador para cambiar algo suyo, el dato está
mal ubicado. Por eso la tolerancia de llegada y las horas de anticipación son
columnas de `Actividad`, y los precios son filas de `Plan_Actividad`.

**3. Menos tablas es mejor, pero no menos de las necesarias.** Una tabla se
justifica si hay atributos exclusivos de un subconjunto de filas, si el hecho es
múltiple, si el pasado importa, si es una relación de muchos a muchos, si es
catálogo, o si es un evento. Si nada de eso aplica, alcanza con un tipo enumerado
o una columna.

**4. Las restricciones de base se reservan para el daño irreversible.** Lo que se
puede corregir cambiando un identificador vive en el programa.

---

# PARTE IV — LAS 41 TABLAS

## 21. Personas y roles (12 tablas)

Todo el que aparece en el sistema es primero una **persona**. Recién después se
convierte en socio, empleado o dueño. Es lo que se llama una relación de
**supertipo y subtipo**.

**La ventaja:** los datos comunes se escriben una sola vez. Si un entrenador
además se asocia al gimnasio, no hay dos fichas con su nombre: hay una persona con
dos roles.

### Persona
El supertipo. Documento, apellido, nombre, correo, domicilio descompuesto, fecha de
nacimiento. Los teléfonos y contactos de emergencia no están acá porque son
múltiples.

### Telefono · Contacto_Emergencia
Existen por primera forma normal: una persona puede tener varios de cada uno.

Hay una asimetría deliberada: el teléfono del contacto de emergencia va como
columna, mientras que los de la persona viven en tabla aparte. Se justifica porque
el contacto de emergencia no es una persona del sistema, es un dato de contacto
externo.

### Usuario
Credenciales de acceso. **No tiene columna de rol**: el rol se deduce de en qué
subtipo aparece la persona. Guardarlo sería una segunda fuente de verdad.

### Dueno · Sede
La sede es la raíz organizativa. Tiene una regla de unicidad sobre la combinación
de sede y dueño que parece extraña, porque la sede ya es única por sí sola. Hace
falta para poder declarar la clave foránea compuesta que usa `Promocion`.

### Empleado y sus cuatro subtipos
`Entrenador`, `Profesor`, `Nutricionista`, `Recepcionista`. Son **solapados**: una
persona puede tener varias de esas filas.

Un disparador garantiza que todo empleado sea al menos uno de los cuatro. Es
diferido, porque el alta ocurre en dos pasos.

### Franja_Laboral
Horarios de trabajo. La usa **sólo** el recepcionista: los demás derivan su horario
de los turnos y horarios de actividad.

## 22. El socio (5 tablas propias)

`Socio` es el centro del modelo: **trece tablas lo referencian directamente**. Tiene
pocas tablas propias precisamente porque casi todo lo que le pasa vive en otros
bloques.

### Socio
Número de socio, código de acceso, fecha de alta, objetivo. **No guarda el peso
actual**: sale de `Registro_Salud`.

### Patologia · Socio_Patologia
Catálogo y vínculo. El vínculo tiene clave compuesta y guarda la fecha de
diagnóstico y observaciones.

### Baja
Es un **hecho con fecha**, no un simple indicador de sí o no, porque un socio puede
reinscribirse.

*Punto débil conocido:* existe la baja pero no hay un hecho «alta» simétrico. La
fecha de alta es una sola columna, así que si el socio se va y vuelve, la fecha de
reinscripción no tiene dónde vivir.

### Registro_Salud
Histórico de mediciones: peso, altura, grasa corporal, masa muscular. Un índice
único impide dos mediciones el mismo día pero conserva toda la progresión.

*Sobre la altura:* podría parecer redundante, ya que la altura de un adulto no
cambia. Se conserva porque **el gimnasio acepta menores**, y en un adolescente sí
cambia entre mediciones.

## 23. El dinero (5 tablas)

### Tipo_Membresia
Catálogo: mensual, trimestral, anual. Con duración en días y precio vigente.
Separado de `Membresia` por tercera forma normal.

### Membresia
El permiso de acceso de un socio, con fechas y precio pactado. Un índice único
parcial impide que un socio tenga dos activas a la vez.

### Congelamiento
Pausas de membresía. `fecha_fin` es lo previsto y `fecha_reanudacion` lo efectivo,
porque al reanudar se extiende el vencimiento por los días **realmente**
congelados.

El campo `origen` distingue si lo pidió el socio o lo impuso el gimnasio. Se
mantiene porque los días impuestos por el gimnasio no deberían contar contra un
eventual tope anual de congelamiento voluntario: sería cobrarle al socio un cierre
que no fue culpa suya.

### Pago
Cada cobro. Nunca se borra. Guarda el monto descontado en lugar de recalcularlo.

*Punto débil conocido:* la columna del socio es deducible a través de la membresía
o la inscripción, y nada garantiza hoy que coincidan.

### Promocion
Descuentos porcentuales, con vigencia. Si no tiene sede, vale para todas.

## 24. Actividades y turnos (8 tablas)

Este bloque va de lo general a lo concreto:

```
Actividad          "yoga"
  Plan_Actividad   "yoga, 8 clases al mes, $26.000"
  Horario_Actividad "yoga los martes a las 19"
    Turno          "la clase del martes 12 a las 19"
```

Y del lado del socio:

```
Inscripcion_Actividad   lo que compró
  Reserva               su lugar en un turno concreto
    Asistencia          que efectivamente entró
```

### Actividad
Catálogo de lo reservable. **Musculación es una fila más**, no un caso especial.
Sus particularidades son datos: cero horas de anticipación para cancelar, porque es
acceso libre, y turnos que pueden no tener nadie a cargo.

Las horas de anticipación y los minutos de tolerancia son **columnas y no
constantes del programa**, por el criterio 2.

### Plan_Actividad
Formatos de venta. No se unifica con `Actividad`: unificarlas repetiría los
atributos de la actividad en cada plan y dejaría al turno sin saber a qué fila
apuntar.

La clase suelta es un plan más del catálogo, con cantidad uno. Así el sistema la
trata igual que a cualquier otro plan.

### Profesor_Actividad
Qué profesor está habilitado para dictar qué actividad. Es una relación de muchos a
muchos pura. Sirve de destino a las claves foráneas compuestas que garantizan que
nadie quede a cargo de una actividad para la que no está habilitado.

### Horario_Actividad
La plantilla semanal. El programa genera los turnos a partir de acá.

### Turno
La instancia concreta. La hora es sólo de llegada: no hay hora de fin.

Tiene dos columnas de personal a cargo, una para profesor y otra para entrenador,
que no pueden estar ambas a la vez. Que ambas estén vacías **sí** es válido: es una
sala de acceso libre.

### Inscripcion_Actividad
Lo que el socio compró. El contador de clases restantes fue eliminado: se calcula
contando reservas.

### Reserva
El lugar del socio en un turno. Si no tiene inscripción, es clase suelta.

Los que están en lista de espera **no ocupan lugar**, por definición: la lista de
espera existe para los que no entraron. Si contaran, el turno se vería lleno con
gente sin lugar y la cola nunca avanzaría.

### Asistencia
Ingresos y egresos. No hay estados de asistió o ausente: se deducen de si hay fila.

## 25. Rutinas (6 tablas)

Acá aparece la idea que estructura este bloque y el siguiente: **plantilla contra
realidad**.

```
Rutina              la plantilla que escribe el entrenador
  Rutina_Ejercicio  qué ejercicios, series y peso sugerido
Asignacion_Rutina   a qué socio se le asignó y desde cuándo
Registro_Ejercicio  qué levantó realmente, con fecha
```

### Ejercicio
Catálogo. El grupo muscular depende del ejercicio, no de la rutina donde aparece.

### Rutina · Rutina_Ejercicio
La plantilla. Se escribe una vez y se asigna a varios socios. **No es personalizada
por persona**, y eso tiene consecuencias en todo el modelo.

### Asignacion_Rutina
Historiza el vínculo. Un índice único parcial impide dos rutinas vigentes a la vez,
pero permite todo el historial.

### Registro_Ejercicio
El peso efectivamente levantado. **No puede ir en la plantilla**: si dos socios
siguen la misma rutina comparten la misma fila, así que un peso ahí no tendría
dueño. Y haría falta una fecha, porque el mismo socio levanta distinto cada semana.

### Asignacion_Entrenador
A diferencia de rutinas y dietas, **no** tiene regla de «una sola activa». Un socio
sí puede tener varios entrenadores a la vez. No es un olvido.

## 26. Dietas (5 tablas)

Estructuralmente gemelo del anterior:

```
Dieta              la plantilla que escribe el nutricionista
  Comida           qué plato en qué día y momento
Asignacion_Dieta   a qué socio y desde cuándo
Registro_Comida    qué comió realmente, con fecha
```

### Catalogo_Comida
Platos con sus calorías. Las calorías viven acá porque dependen del **plato**, no
de la dieta ni del día en que aparece.

### Dieta
La plantilla. Su columna de calorías diarias es el **objetivo pautado**, no la suma
de las comidas.

### Comida
Qué plato en qué día. El plato **siempre** sale del catálogo. Por eso esta tabla no
repite ni el nombre ni las calorías.

### Asignacion_Dieta
Entidad asociativa historizada. No es una relación de muchos a muchos pura porque
tiene atributos propios: vigencia, estado y observaciones.

### Registro_Comida
Lo que el socio realmente comió, en texto libre, más las calorías que él estima
haber ingerido.

**Asimetría deliberada:** la plantilla está restringida al catálogo pero el
registro es libre. El nutricionista sólo puede pautar platos conocidos; el socio
come lo que se le antoja y hay que poder anotarlo igual. Un modelo que lo obligara
a comer sólo del catálogo estaría mintiendo.

*Consecuencia a tener presente:* sin vínculo al catálogo no se pueden cruzar
calorías reales automáticamente ni sacar estadísticas de platos más consumidos.

---

# PARTE V — LAS REGLAS

## 27. Restricciones de rango

| Nombre | Qué exige |
|---|---|
| `chk_actividad_tolerancia` | La tolerancia está entre 0 y 180 minutos |
| `chk_congelamiento_rango` | La fecha de fin no es anterior a la de inicio |
| `chk_horario_cupo` | El cupo es mayor que cero |
| `chk_horario_dia_semana` | El día está entre 1 y 7 |
| `chk_horario_un_solo_staff` | No hay profesor y entrenador a la vez |
| `chk_horario_vigencia` | La vigencia no termina antes de empezar |
| `chk_pago_adelanto_periodo` | Un pago adelantado declara qué período cubre |
| `chk_promocion_porcentaje` | El descuento está entre 0 y 100 |
| `chk_promocion_vigencia` | La promoción no termina antes de empezar |
| `chk_registro_comida_que_comio` | El registro dice qué se comió |
| `chk_registro_ejercicio_peso` | El peso levantado no es negativo |
| `chk_turno_un_solo_staff` | No hay profesor y entrenador a la vez |

## 28. Índices únicos parciales

Son cuatro y todos siguen el mismo patrón:

```sql
CREATE UNIQUE INDEX membresia_una_activa_uidx
    ON "Membresia" (id_socio)
    WHERE (estado = 'ACTIVA');
```

**La cláusula final es lo que lo hace utilizable.** Sin ella, la regla diría que un
socio tuvo una sola membresía en toda su vida, lo cual es absurdo porque cada
renovación es una fila nueva. Con ella dice lo correcto: una sola vigente a la vez,
y el historial no estorba.

Los cuatro: una membresía activa por socio, un congelamiento activo por membresía,
una rutina activa por socio, una dieta activa por socio.

> **Un detalle que casi rompe todo.** Estos índices sólo miran las filas que
> cumplen la condición. Una fila con el estado vacío no la cumple, así que quedaba
> fuera del índice y podía convivir con una activa.
>
> Peor: el disparador que controla el cupo empieza preguntando si el estado es
> distinto de «reservada», y en la lógica de tres valores que usan las bases de
> datos, un valor vacío es distinto de todo. Una reserva sin estado se salteaba la
> validación **y** tampoco se contaba después: entraba sin control y dejaba entrar a
> las demás.
>
> Se corrigió obligando a que las ocho columnas de estado tengan siempre un valor.

## 29. Los cuatro disparadores

### Ningún empleado sin especialidad
Todo empleado debe ser al menos profesor, entrenador, nutricionista o
recepcionista. Diferido, porque el alta ocurre en dos pasos.

### No se vende más allá del cupo
Antes de aceptar una reserva se cuentan las existentes. Los de lista de espera no
cuentan. Diferido, para permitir cancelar y promover en una sola operación.

### No se baja el cupo por debajo de lo vendido
Si hay quince anotados, no se puede dejar el turno en diez.

### La inscripción tiene que corresponder
Cierra dos agujeros: que una inscripción a yoga sirviera para reservar boxeo, y que
un socio consumiera la inscripción de otro.

*Limitación conocida:* vive en `Reserva`, así que sólo actúa cuando se escribe una
reserva. Si alguien cambiara la actividad de un plan que ya tiene reservas hechas,
esas reservas quedarían mal y nada lo detectaría. Una clave foránea compuesta lo
habría cubierto, porque las claves foráneas se verifican también desde el lado
referenciado. Se aceptó el costo para no agregar columnas.

## 30. Claves foráneas compuestas

Son dos y usan un mecanismo que conviene entender porque parece magia.

El estándar SQL define que, cuando **alguna columna** de una clave foránea
compuesta está vacía, la restricción **no se verifica**. Se llama `MATCH SIMPLE` y
es el comportamiento por omisión.

### Profesor habilitado
`Turno` y `Horario_Actividad` apuntan con dos columnas juntas —profesor y
actividad— a la tabla de habilitaciones. Si el profesor está vacío, porque es
musculación o sala libre, la regla se desactiva sola.

### Dueño de la promoción
`Promocion` apunta con sede y dueño juntos a `Sede`. Como el dueño es obligatorio,
la única que puede faltar es la sede, y la regla se parte sola en dos ramas sin
escribir ninguna lógica condicional:

- **Con sede** → se valida que el dueño sea efectivamente el de esa sede.
- **Sin sede** (promoción global) → la restricción se desactiva sola.

---

# PARTE VI — REFERENCIA

## 31. Decisiones tomadas y por qué

| Decisión | Razón |
|---|---|
| Musculación es una actividad más | Todo el sistema de turnos funciona igual para las tres sin duplicar lógica |
| `Actividad` y `Plan_Actividad` no se unifican | Unificarlas repetiría los atributos de la actividad en cada plan |
| El progreso real va en tablas aparte | Las plantillas se comparten; un dato de un socio pisaría al de otro |
| No hay tabla de deudas | Sin membresía activa no hay acceso: «debe» es derivable |
| No hay reembolsos parciales | Política comercial |
| Una sola membresía activa por socio | El congelamiento cuelga de ella; dos activas romperían la lógica |
| Una inscripción sirve sólo para su actividad | Resuelto con disparador, sin tocar la tabla |
| Las promociones son porcentuales | Se eliminó el descuento de monto fijo |
| El catálogo de comidas es obligatorio | Permitió eliminar dos columnas redundantes |
| Se eliminó el contador de clases restantes | Se calcula contando reservas |
| Las dos columnas de personal del turno no se unifican | Se probó y se revirtió |
| La habilitación del personal se valida en el programa | Criterio del daño reversible |

### Columnas eliminadas y por qué

- **`Promocion.monto_fijo_descuento`** — el caso de negocio dejó de existir.
- **`Comida.calorias` y `Comida.descripcion`** — al volverse obligatorio el
  catálogo, pasaron de redundancia parcial a total.
- **`Inscripcion_Actividad.clases_restantes`** — derivable, y con dos criterios
  opuestos conviviendo en la misma columna.

> **El patrón:** ninguna de las cuatro cayó por análisis técnico. Cayeron porque se
> cerró una decisión de negocio y un caso de uso dejó de existir. El análisis señala
> dónde mirar; lo que borra es la definición.
>
> **La regla:** sólo se borra lo que es redundante en el cien por ciento de las
> filas. Lo que sobra en algunas y hace falta en otras no se borra, se restringe.
> Confundir esas dos cosas es la forma más común de perder datos por normalizar de
> más.

## 32. Lo que quedó abierto

**1. El programa contradice la política de cobro.** Hay código que registra el
ingreso aunque la cuota esté vencida y sólo devuelve una advertencia. Describe un
modelo de fiado y contradice la regla de que sin membresía activa no hay acceso. Es
la contradicción más importante que queda.

**2. Congelamientos que se superponen.** La regla está definida pero no
implementada: hay que quedarse con el que termina más tarde, cortando el anterior
sin borrarlo para que los días vividos se acrediten.

**3. Cómo reconocer una actividad de acceso libre.** Hoy el programa lo distingue
por el nombre «Musculación», lo cual es frágil.

**4. Pagos online y derecho de arrepentimiento.** Las compras a distancia tienen en
Argentina un régimen de arrepentimiento con plazo legal. No es una cuestión técnica
ni una opinión: hay que verificarlo con quien corresponda antes de escribir en los
términos que no hay devoluciones.

**5. Faltan restricciones de rango.** Ningún precio exige ser no negativo. Varias
tablas no tienen ninguna verificación.

**6. Cuatro columnas siguen siendo texto libre** y deberían ser listas cerradas: el
sexo en `Persona`, el nivel en `Rutina`, el momento en `Comida` y el grupo muscular
en `Ejercicio`. Este último **tiene un índice encima**, lo cual prueba que se filtra
por él: es un catálogo que no se declaró como tal.

**7. Multi-sede.** El modelo lo soporta pero el negocio no lo usa. Si se abriera
una segunda sucursal habría que revisar las columnas de sede en `Asistencia` y
`Pago`, que hoy son deducibles del socio y dejarían de serlo.

## 33. Preguntas de defensa oral

**¿Por qué 41 tablas y no menos?**
Cada tabla se justifica con uno de seis criterios: atributos exclusivos de un
subconjunto, hecho múltiple, historial, relación de muchos a muchos, catálogo, o
evento. Ninguna existe sin razón.

**¿Está en tercera forma normal?**
Sí. Las repeticiones que quedan son de dos clases legítimas: valores históricos
congelados, que son hechos distintos del valor vigente, y redundancia controlada por
restricción, donde la base impide que las copias diverjan.

**¿Por qué el peso del socio no está en `Socio`?**
Porque es derivable de la última medición. Guardarlo crearía una segunda fuente de
verdad que se puede desincronizar.

**¿Por qué no hay tabla de deudas?**
Porque el sistema es prepago. Sin membresía activa no hay acceso, así que «debe» se
deduce y no necesita fila propia.

**¿Por qué el precio aparece dos veces?**
No es el mismo dato. Uno es el precio vigente, el otro es lo que se le cobró a esa
persona ese día. Si el precio sube, el registro viejo tiene que seguir diciendo la
verdad.

**¿Por qué musculación no es un caso especial?**
Porque tratarla como una fila más permite que todo el sistema de turnos, reservas e
inscripciones funcione igual para las tres actividades sin duplicar lógica. Sus
particularidades se expresan como datos.

**¿Por qué algunas reglas son disparadores y no restricciones?**
Porque una restricción sólo puede mirar la fila que se está escribiendo. Contar
reservas para saber si un turno está lleno exige consultar otra tabla.

**¿Por qué los disparadores son diferidos?**
Porque validan al final de la operación completa y no en cada paso. Sin eso sería
imposible dar de alta un empleado, que se crea en dos pasos, ni cancelar y promover
de la lista de espera en un solo movimiento.

**¿Por qué las claves foráneas no borran en cascada?**
Porque nada se borra. Los pagos se marcan cancelados o reembolsados. Al no declarar
comportamiento de borrado rige el que impide borrar, y esa omisión es deliberada.

## 34. Glosario

**Árbol B** — Estructura de un índice. Puede recorrerse por sus columnas
iniciales, y de ahí que un índice de tres columnas sirva también para buscar por
las dos primeras.

**Clave candidata** — Cualquier columna o combinación que podría identificar la
fila. El DNI lo es, aunque no sea la clave primaria.

**Clave foránea** — Columna que apunta a la clave primaria de otra tabla. La base
garantiza que la fila apuntada exista.

**Clave primaria** — Columna que identifica cada fila sin ambigüedad.

**Clave subrogada** — Identificador inventado, sin significado fuera del sistema.
Se prefiere como clave primaria porque nunca hay razón para cambiarlo.

**Dato derivado** — El que se puede calcular a partir de otros. No se guarda.

**Dependencia funcional** — Cuando el valor de una columna queda determinado por el
de otra.

**Dependencia transitiva** — Cuando un dato depende de otro que tampoco es clave.
Es lo que prohíbe la tercera forma normal.

**Diferido** — Restricción o disparador que verifica al final de la operación
completa y no en cada paso.

**Entidad asociativa** — Tabla que vincula otras dos pero tiene atributos propios.
No es una relación de muchos a muchos pura.

**Índice parcial** — Índice que sólo cubre las filas que cumplen una condición.

**Integridad referencial** — Garantía de que ninguna clave foránea apunta a una
fila inexistente.

**Lógica de tres valores** — En bases de datos, una comparación puede dar
verdadero, falso o desconocido, porque existe el valor vacío. Es la razón por la
que un estado vacío se salteaba el control de cupo.

**MATCH SIMPLE** — Comportamiento por omisión de las claves foráneas compuestas:
si alguna columna está vacía, la restricción no se verifica.

**Normalización** — Conjunto de reglas para eliminar la redundancia.

**Nulo** — Ausencia de valor. No es cero ni cadena vacía: es «no se sabe».

**Redundancia** — El mismo dato en dos lugares. Peligrosa cuando las copias pueden
divergir.

**Relación de muchos a muchos** — Cuando cada fila de una tabla puede vincularse con
varias de otra y viceversa. Requiere una tabla intermedia.

**Restricción** — Condición que todo dato debe cumplir.

**Subtipos solapados** — Cuando una misma fila del supertipo puede pertenecer a
varios subtipos a la vez. Es el caso de profesor y entrenador.

**Supertipo y subtipo** — Cuando una entidad general se especializa. `Persona` es
supertipo de `Socio` y `Empleado`.

**Transacción** — Grupo de operaciones que se completan todas o ninguna.

**Tipo enumerado** — Lista cerrada de valores admitidos para una columna.

---

**FORGE · OlimpOS** — Proyecto académico de séptimo año.
