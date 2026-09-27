# A-06 · Los seis roles y cómo se derivan

*Piso del capítulo: las seis cadenas exactas que viajan en el token, y las consultas contadas que cuesta
calcularlas.*

Cada decisión de permisos del sistema empieza con la misma pregunta: **¿qué es esta persona?** ¿Dueño,
recepcionista, socio? En la mayoría de los sistemas la respuesta está escrita en una columna. En OlimpOS no
está escrita en ningún lado: se **calcula**, mirando en qué tablas aparece la persona. Este capítulo explica
qué son los seis roles, por qué son texto y tienen que coincidir letra por letra en tres lugares, y cuánto
cuesta calcularlos, medido.

Por qué el modelo de datos parte a las personas en tablas de subtipo en vez de darles una columna `rol` es
tema de [la tabla subtipo](A-05-modelo-de-datos.md#tabla-subtipo-especialización). Qué puede hacer cada rol
es tema de [la matriz de permisos](A-08-autorizacion.md#matriz-de-permisos). Acá está el eslabón del medio:
de las tablas al rol.

---

## Rol de sesión y los seis roles

### Qué es un rol de sesión

Un **rol de sesión** es la etiqueta que el sistema le pone a una persona cuando inicia sesión, y contra la
que después se evalúan todos sus permisos. No describe la ficha de la persona: describe **qué puede hacer
mientras está conectada**.

### Las seis cadenas

Éste es el piso: los roles son exactamente estos seis textos, en minúsculas, sin tildes ni eñe —`dueno`, como
la tabla `Dueno` de la base—:

```python
DUENO = "dueno"
SOCIO = "socio"
ENTRENADOR = "entrenador"
NUTRICIONISTA = "nutricionista"
RECEPCIONISTA = "recepcionista"
PROFESOR = "profesor"
```

`backend/models.py:34-57`, en la clase `Rol`. Y el docstring de esa clase advierte que no son una columna:
*"NO son una columna de la base. Se derivan"*.

### Por qué tienen que coincidir letra por letra

Los roles son **texto que viaja**. El backend los escribe dentro del token al iniciar sesión (`"roles":
roles`, `backend/auth.py:180`) y los vuelve a leer del token en cada pedido (`backend/security.py:136`). Y
del otro lado, cada una de las dos apps los compara contra su copia de la matriz de permisos para decidir qué
dibujar.

Por eso el mismo juego de seis cadenas existe tres veces:

| Copia | Dónde |
|---|---|
| backend | `Rol` en `backend/models.py:34` |
| PWA | `Roles` en `Proyecto - PWA/src/frontend/src/config.ts:179` |
| Flet | `Rol` en `Flet/Proyecto/app/permisos.py:86` |

Y las tres tienen que coincidir carácter por carácter. El docstring del backend lo dice con la consecuencia:
*"Si divergen, el backend autoriza una cosa y el frontend muestra otra."* Un `"Dueño"` con mayúscula y eñe en
una de las tres copias no produce ningún error: produce un dueño que no ve ninguna sección, porque su rol no
coincide con ninguna fila de la matriz. Es el mismo tipo de falla silenciosa que la de los permisos, y la
controla el mismo verificador, que compara los seis roles de las tres copias
([las tres copias y su verificador](A-08-autorizacion.md#las-tres-copias-y-su-verificador)).

### Dos clases de rol

Los seis no son equivalentes. Cuatro son **roles de gestión**: el dueño, la recepcionista, el entrenador y el
nutricionista entran a secciones donde administran a otros. Los otros dos son **roles de pantalla propia**:
el socio y el profesor sólo ven sus propias cosas, y no entran a ninguna sección de gestión. El docstring de
`Rol.PROFESOR` lo define así (`models.py:54-56`): *"Es un rol de PANTALLA PROPIA, como el Socio: no entra a
ninguna sección de gestión, sólo a 'Mis clases', y ahí ve únicamente los turnos que dicta él."*

### El rol que faltaba

El profesor no siempre tuvo rol. El comentario de `models.py:49-52` cuenta cómo era antes del 2026-09-16, y es
un buen ejemplo de por qué un rol existe:

> *"El Profesor SÍ inicia sesión, desde el 2026-09-16. Antes no, y la nota vieja lo defendía así: 'da clases,
> no usa el sistema'. El resultado real era que el profesor no tenía dónde ver su horario ni quién se anotó a
> su clase — se lo pasaba alguien por WhatsApp o un papel en la pared."*

La lógica de "no usa el sistema, así que no necesita rol" confundía dos cosas: que el profesor no **gestione**
nada no quiere decir que no **necesite ver** nada. El rol de pantalla propia resuelve exactamente eso.

### Nota marcada · un nombre que no existe

El docstring de `Rol` en Flet (`Flet/Proyecto/app/permisos.py:92-93`) dice que sus valores tienen que coincidir
con los de *"models.Rol del backend y con RolUsuario de config.ts"*. En la PWA no hay nada que se llame
`RolUsuario`: la constante es `Roles`. El comentario nombra algo que ya no existe; la regla que enuncia sigue
siendo correcta.

---

## Derivación de roles

### La única autoridad

La función que responde qué es alguien es `roles_de_persona()` (`backend/models.py:1002-1040`), y su docstring
empieza por ahí: *"Esta función es la ÚNICA autoridad sobre 'qué es' alguien."* Lo que hace es mirar, una por
una, en qué tablas de rol aparece la persona:

```python
if persona.dueno is not None:
    roles.append(Rol.DUENO)
if persona.socio is not None:
    roles.append(Rol.SOCIO)
empleado = persona.empleado
if empleado is not None:
    if empleado.entrenador is not None:
        roles.append(Rol.ENTRENADOR)
    if empleado.nutricionista is not None:
        roles.append(Rol.NUTRICIONISTA)
    if empleado.recepcionista is not None:
        roles.append(Rol.RECEPCIONISTA)
    if empleado.profesor is not None:
        roles.append(Rol.PROFESOR)
```

Dos decisiones están en esa forma. Primero, **devuelve una lista y no un valor**, porque los roles se acumulan:
el docstring da el ejemplo del dueño que entrena en su propio gimnasio (`dueno` + `socio`), o el entrenador que
además es socio. Cuando una persona tiene varios roles, la matriz le da el permiso más alto de todos, y un rol
extra nunca le quita nada. Segundo, **una lista vacía** quiere decir que la persona existe pero no tiene ningún
rol que habilite sesión, y el login la rechaza con un 403 en vez de dejarla entrar a un sistema donde no puede
abrir ninguna pantalla.

### Las consultas contadas

Éste es el piso. Cada línea del bloque de arriba lee una relación, y en este repo las relaciones se cargan de
forma perezosa: cada lectura que todavía no se hizo es una consulta a la base
([carga perezosa contra carga ansiosa](A0-09-el-orm.md#carga-perezosa-contra-carga-ansiosa)). Contando las
consultas que emite la función real con los modelos reales, sobre una base en memoria:

| Persona | Consultas | Cuáles |
|---|---|---|
| no es empleado (socio, o dueño y socio) | **3** | dueño, socio, empleado |
| cualquier empleado | **7** | las tres de arriba, más las cuatro tablas de empleado |

Para una persona sola, siete consultas son 300 ms contra Neon. El problema aparece en un listado. El panel de
Usuarios necesita los roles de todas las cuentas, y hacerlo persona por persona repite ese costo en cada fila:

| Listado de 8 personas | Consultas | A 44 ms cada una |
|---|---|---|
| perezoso, persona por persona | **41** | ≈ 1,8 s |
| con `CARGA_DE_ROLES` | **9, fijas** | ≈ 0,4 s |

`CARGA_DE_ROLES` (`backend/routers/usuarios.py:82-93`) es la lista de `selectinload` que trae de una vez las
siete relaciones que la función va a leer, más los teléfonos. Con eso las nueve consultas son siempre nueve,
haya ocho cuentas o cien. El comentario que la precede da el número medido contra la base real antes del
arreglo (`usuarios.py:72`): *"8 cuentas -> 45 consultas -> 2,88s"*, del mismo orden que las 41 de la base en
memoria, que no tiene teléfonos cargados. Por qué selectinload y no un `JOIN`, y lo que el comentario de ese
archivo dice mal sobre eso, está en [carga perezosa contra carga ansiosa](A0-09-el-orm.md#carga-perezosa-contra-carga-ansiosa).

El docstring de `roles_de_persona()` estima que recalcular los roles *"costaría cinco JOINs por pedido"*. Lo
medido es de 3 a 7 consultas según la persona: hoy hay cuatro subtipos de empleado, y cada uno es un viaje más.

### Una vez, en el login

Esa cuenta es la razón de la decisión más importante sobre los roles: **se calculan una sola vez, al iniciar
sesión, y viajan firmados dentro del token**. El docstring de la función lo dice (líneas 1018-1020): se llama
*"UNA vez, en el login, y el resultado se firma dentro del JWT. Recalcularlo en cada request costaría (…) por
pedido para un dato que no cambia durante la sesión."*

Así, un pedido cualquiera no cuesta ninguna consulta para saber qué es quien pregunta: lo lee del token. El
precio de esa decisión, y por qué la baja de una cuenta sí tiene efecto inmediato aunque los roles no, está en
[identidad firmada](A-07-autenticacion.md#identidad-firmada): un cambio de rol no se nota hasta el próximo
ingreso.

### Por qué está hecho así

**Qué se optimiza:** que ninguna pregunta de permisos cueste un viaje a la base.

**Qué alternativas había.** Guardar el rol en una columna: una lectura en vez de siete consultas, pero dos
fuentes de verdad —la columna y las tablas donde la persona aparece— que pueden contradecirse, y una sola
columna para alguien con varios roles; el porqué completo es de
[la tabla subtipo](A-05-modelo-de-datos.md#tabla-subtipo-especialización). Derivar en cada pedido: siempre
exacto, pero con hasta siete viajes por pedido.

**Qué se eligió:** derivar, pero **una vez por sesión**, y guardar el resultado en el token. Es un caso de
[estado derivado](A-09-estados-derivados.md#estado-derivado) con una diferencia: el estado del socio se deriva
en cada lectura porque cambia con el tiempo; el rol no cambia solo, así que se puede derivar una vez y
reutilizar.

**Cómo se llama:** el token funciona como un **caché firmado** de un valor derivado. Caché, porque guarda un
resultado para no recalcularlo; firmado, porque el cliente lo lleva y no lo puede alterar.

---

## Con qué se conecta

- **Existe por culpa de…** [la tabla subtipo](A-05-modelo-de-datos.md#tabla-subtipo-especialización): el rol
  sale de en qué tablas aparece la persona, porque no hay una columna que lo diga.
- **Es la misma idea que…** el [estado derivado](A-09-estados-derivados.md#estado-derivado): el rol se calcula en
  vez de guardarse; la diferencia es que se calcula una vez por sesión y no en cada lectura.
- **Es el mismo problema que…** el [N+1](A0-09-el-orm.md#n1): derivar roles persona por persona son 41 consultas
  para ocho cuentas; en lote, nueve.
- **Es la misma idea que…** la [matriz de permisos](A-08-autorizacion.md#matriz-de-permisos): los seis roles son
  sus filas, y con varios roles gana el permiso más alto.
- **Existe por culpa de…** la [identidad firmada](A-07-autenticacion.md#identidad-firmada): los roles viajan en
  el token, y por eso un cambio de rol exige volver a iniciar sesión.
