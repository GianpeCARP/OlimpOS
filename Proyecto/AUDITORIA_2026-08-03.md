# Auditoría completa OlimpOS — 2026-08-03

Recorrido panel por panel con los 5 roles (socio, dueño, entrenador,
nutricionista, recepcionista) sobre `localhost:5173`, más lectura completa
de `src/frontend/src`. `tsc --noEmit` y `oxlint` pasaban limpios **antes y
después** de los cambios: ninguno de los bugs de abajo era detectable por
tipos ni por lint, todos salieron de ejecutar la app.

**Nada fue borrado.** Al final está la lista de lo que queda pendiente y de
lo que habría que sacar cuando exista el backend.

---

## Lo que funciona bien (verificado, no asumido)

- **Matriz de permisos**: los 4 roles de staff ven exactamente las secciones
  y los botones que declara `PERMISOS`. Entrenador y Nutricionista son
  espejo correcto uno del otro (gestión de lo suyo, lectura de lo del otro).
- **Guard de rutas**: entrar por URL a una sección prohibida redirige a la
  primera sección visible del rol, y una URL inexistente también. Probado
  con navegación client-side en los 5 roles, sin ningún ciclo de redirect.
- **Bloqueo por intentos fallidos**: al 5.º intento la cuenta queda
  bloqueada, la contraseña correcta deja de funcionar, el badge pasa a
  "Bloqueado" y el desbloqueo desde /usuarios la devuelve a la vida.
- **Registro público**: valida DNI duplicado, email duplicado, username
  duplicado y contraseña corta, con el mensaje correcto en cada caso. El
  alta impacta en el dashboard y en /socios de inmediato.
- **Soft-delete de ida y vuelta** en socios, personal, rutinas y dietas.
- **Cálculos del dashboard**: los números se derivan de las tablas, no están
  escritos a mano, y son coherentes entre tarjetas.

---

## Bugs encontrados y corregidos

### 1. 🔴 Renovación de membresía gratis al editar un socio vencido

**Reproducción**: /socios → Camila Ruiz (`Vencido`, vence 29-jul) → lápiz →
**Guardar sin tocar nada** → queda `Activo`, vence 02-sept.

El `<select>` de plan se precarga con `socio.idTipoMembresia`, que sale de
la membresía vencida. Guardar mandaba ese mismo id a `aplicarPlan`, que al
ver que la membresía no estaba `ACTIVA` creaba una nueva de 30 días. O sea:
corregir un teléfono le regalaba un mes al socio, sin pago registrado. Con
10 socios pasa desapercibido; con 300 es un agujero de facturación.

**Fix** (`sociosService.ts`): si el plan pedido es el mismo que el de la
membresía no vigente, no se toca nada. Renovar es una acción con cobro, no
un efecto secundario de editar datos de contacto. Cambiar a un plan
*distinto* sigue funcionando igual (verificado: Camila → Trimestral Full →
`Activo` 01-nov).

### 2. 🔴 Cambiar el rol de un empleado dejaba rutinas y dietas huérfanas

**Reproducción**: /personal → Sergio Bustos (Entrenador, 2 rutinas) → rol
Recepcionista → Guardar. Sus rutinas pasaban a "Entrenador: **Sin
asignar**", y el formulario de edición ofrecía "Sin asignar (inactivo)".

`asignarRol` hacía `splice` de la fila `Entrenador`, pero esa fila es el
destino de `Rutina.id_entrenador`, que es **NOT NULL y FK** en
`db/schema.sql`. Contra el Postgres real el DELETE fallaría; en el mock
quedaban punteros colgados. Lo mismo con `Nutricionista` → `Dieta`.

**Fix** (`personalService.ts`): `validarCambioDeRol` corta antes de tocar
nada — *"No se puede cambiar el rol: tiene 2 rutina(s) a su nombre.
Reasignalas a otro entrenador primero."* Es la misma regla que aplicaría la
base.

### 3. 🔴 El rol de sesión quedaba desfasado del rol de la ficha

**Reproducción**: cambiar a alguien de rol en /personal → /usuarios seguía
mostrando el rol viejo, y esa persona entraba con los permisos viejos.

`Usuario.rol` es la copia que el mock guarda del rol derivado, y nadie la
refrescaba. Contradice el invariante documentado ("el rol se deriva, nunca
se elige a mano").

**Fix**: `sincronizarRolDeUsuario` se llama después de `asignarRol`.
Verificado: Carla Bianchi Recepcionista → Entrenador, y su cuenta pasa a
Entrenador en el mismo momento.

### 4. 🔴 Un empleado dado de baja seguía entrando al sistema

**Reproducción**: dar de baja a Carla Bianchi → login con
`recepcion_demo` / `Recepcion1234` → **entra igual**, con todos los permisos
de recepcionista.

La baja de socio sí apagaba el `Usuario` (`authService.darDeBaja`); la de
empleado no. La baja era puramente cosmética: la ficha decía "Inactivo" y la
persona seguía trabajando en el sistema. Es el agujero clásico de
offboarding, y acá era peor porque el personal tiene más permisos que un
socio.

**Fix**: `darDeBajaEmpleado` apaga la cuenta y `reactivarEmpleado` la
devuelve, simétrico a socios.

### 5. 🔴 Escalación de privilegios: Recepcionista → Dueño en 3 clicks

**El más grave.** Reproducción completa, sin devtools:

1. Entrar como `recepcion_demo`.
2. /usuarios → fila **Dueño Admin** → 🔑 Resetear contraseña → Confirmar.
3. La app muestra en pantalla: *"Nueva contraseña temporal para Dueño Admin:
   2DDED0AE"*.
4. Cerrar sesión, entrar como `dueno_demo` / `2DDED0AE` → **control total**.

`gestionUsuarios: true` no tenía ninguna noción de jerarquía, así que la
tabla le dibujaba los tres botones sobre la fila del Dueño. Y el reseteo no
pasaba por `esCuentaPropiaRestringida` (a propósito, para poder resetearse la
propia) — pero eso lo dejaba abierto sobre *cualquier* cuenta, incluida la
del dueño. También podía desactivarlo y dejarlo afuera de su propio gimnasio.

**Fix** (`config.ts` + `UsuarioRow.tsx`): `esCuentaDeMayorJerarquia` — sólo
un Dueño opera sobre la cuenta de un Dueño, y acá el reseteo **sí** entra en
la restricción porque es justamente el vector. Verificado: la fila del Dueño
ahora no tiene ningún botón para la recepcionista.

### 6. 🟠 Un socio dado de baja podía volver a entrar desde /usuarios

**Reproducción**: dar de baja a Socio Demo (su cuenta pasa a `Inactivo`,
correcto) → /usuarios → botón "Activar" → la cuenta vuelve a `Activo`
mientras el socio sigue `Dado de baja` → **entra a la app**.

La baja cascadeaba bien de socio a cuenta, pero la reactivación de la cuenta
no miraba el estado del socio.

**Fix**: `activarUsuario` rechaza si la persona no es socio ni empleado
activo — *"Esa persona está dada de baja como socio o empleado. Reactivala
primero en su panel."*

### 7. 🟠 La sidebar se iba de pantalla al scrollear

`AppLayout` usaba `min-h-screen`, así que el div crecía con el contenido y
el `overflow-y-auto` de `<main>` no llegaba a activarse nunca: scrolleaba el
documento entero y la sidebar —que no es `fixed` ni `sticky`— se iba con él.
Bastaba bajar un poco en el Dashboard para perder el logo y los primeros
ítems de navegación. Contradice `layout.md` ("sidebar fija").

**Fix**: `h-screen overflow-hidden` en el contenedor + `shrink-0 h-full` en
la sidebar. Verificado: `document.scrollY` queda en 0 y el scroll ocurre
dentro de `<main>`.

### 8. 🟠 La contraseña temporal desaparecía antes de poder anotarla

El reseteo genera una clave que **no queda guardada en ningún lado
consultable**, y se mostraba en un snackbar que se cierra solo a los 4
segundos. Si no llegabas a copiarla, la cuenta quedaba con una contraseña
que no sabía nadie y había que resetear de nuevo.

**Fix**: `SNACK_PERSISTENTE` en `uiStore` — ese mensaje puntual se queda
hasta que lo cierren a mano. Verificado a los 9 segundos.

### 9. 🟡 Crash latente en las tarjetas de Nutrición

`CONFIG_OBJETIVO[plan.objetivo]` sin fallback: `Dieta.objetivo` es un
`varchar(100)` libre, así que un valor fuera de los 4 del enum devolvía
`undefined` y el destructuring reventaba la tarjeta entera con un TypeError.
Hoy no pasa porque el formulario sólo ofrece los 4, pero cualquier fila
cargada a mano o un import lo dispara.

**Fix**: `?? CONFIG_POR_DEFECTO`, igual que ya hacen `StatusBadge` y
`LevelBadge`.

### 10. 🟡 Mensajes con género fijo

*"Carla Bianchi fue **dado** de baja"*, *"... fue **reactivado**"*. `Persona`
no tiene el sexo cargado en casi ninguna fila, así que el participio en
masculino le erraba a la mitad de la gente.

**Fix**: forma impersonal — *"Se dio de baja a Carla Bianchi"*, *"Se
reactivó a ..."*, *"Se desbloqueó la cuenta de ..."*. Correcta para
cualquier persona sin necesitar el dato.

### 11. 🟡 Botón sin chequeo de permiso en el Dashboard

El "Nuevo socio" del topbar era el único botón de toda la app que no pasaba
por la matriz. Hoy no rompe nada (los 3 roles que ven el Dashboard tienen
`altaBajaSocios`), pero quedaba como trampa para el próximo rol.

**Fix**: gateado con `usePuedeAccion('altaBajaSocios')`.

### 12. 🟡 Promesa sin `.catch()` en el alta de usuarios

`listarPersonasSinUsuario()` sin manejo de error dejaba `candidatos` en
`null` para siempre: selector vacío, "Guardar" deshabilitado, sin explicación
y con un unhandled rejection en consola.

**Fix**: `.catch()` que muestra el error y cae al estado de "no hay
candidatos".

### 13. 🟡 Comentarios que mentían

`Snackbar.tsx` y `ConfirmDialog.tsx` decían "se monta una vez en AppLayout".
Se montan en `App.tsx`, y hay una razón (login/registro no pasan por el
layout). Corregido en los dos.

---

## Pendientes — NO tocados, requieren tu decisión

### A. 🔴 La sesión no persiste: F5 te desloguea

`authStore` vive sólo en memoria. Recargar la página, o pegar una URL en la
barra, te devuelve al login. Durante esta auditoría tuve que navegar
exclusivamente por el sidebar para no perder la sesión.

No lo toqué porque la decisión es tuya y tiene implicancias de seguridad:
`localStorage` (sobrevive al cierre del navegador, más expuesto a XSS) vs
`sessionStorage` (se pierde al cerrar la pestaña, más seguro). Con el backend
real esto cambia igual: el token debería viajar en una cookie `httpOnly`.

### B. 🔴 El Socio sigue viendo el panel de administración

Ya está documentado como decisión consciente, pero ahora está **verificado
lo grave que es**: un socio dado de baja entró y vio la lista completa de
socios con DNI, el legajo del personal, y tenía botones para dar de alta y
baja a otros socios. Es el pendiente de mayor impacto real.

### C. 🟠 Sin navegación mobile

La sidebar es de 260px fijos, siempre visible, sin hamburguesa ni drawer. En
un teléfono de 390px se come dos tercios de la pantalla. No hay ningún
`hidden md:*` ni breakpoint que la maneje. Las vistas internas sí son
responsivas (las grillas colapsan bien); lo que falta es el patrón de
navegación. No lo inventé porque es una decisión de diseño, no un bug
puntual.

### D. 🟠 Sin scoping por propietario

Cualquier entrenador puede editar y dar de baja las rutinas de *cualquier*
otro entrenador; lo mismo entre nutricionistas y dietas. La matriz dice
"gestión de rutinas: sí" sin distinguir "las mías" de "las de todos". Puede
ser intencional en un gimnasio chico — pero hoy no está decidido, está
simplemente ausente.

### E. 🟡 "Asignar" existe en Rutinas y no en Nutrición

`RutinaCard` tiene el botón "Asignar" (stub con snack de "próximamente");
`PlanCard` no tiene nada equivalente. Asimetría entre dos vistas que en todo
lo demás son espejo. Cuando se construya la pantalla de asignación conviene
hacer las dos juntas.

### F. 🟡 Detalles menores

- La columna **"ACCIONES"** se sigue dibujando vacía en /socios cuando el rol
  es de sólo lectura (Entrenador/Nutricionista).
- El Dashboard del Recepcionista muestra 3 tarjetas en una grilla de 4
  columnas: queda un hueco a la derecha en pantallas anchas.
- `TipoActividad` declara `'rutina'` en `dashboardService.ts` pero ese
  evento nunca se genera (no hay feed de asignaciones todavía). Está
  documentado como intencional; lo dejo anotado para que no se olvide.

---

## Para borrar cuando exista el backend (no borré nada)

- `services/mockDb.ts` entero.
- El cuerpo de cada función de `services/*.ts` (las firmas públicas quedan).
- `UsuarioMock.rol` — cuando el rol sea una tabla real, `sincronizarRolDeUsuario`
  (que agregué en el fix 3) deja de hacer falta: el rol se derivaría en la query.
- `password_hash` en texto plano del mock.

---

## ⚠️ Lo más importante de todo

Los fixes 5, 4, 6 y 2 tapan agujeros **en el frontend**, que es donde se
dibujan los botones — **no donde se decide**. Cualquiera con las devtools
abiertas puede forzar el store y volver a ejecutar todas esas acciones.

Cuando exista FastAPI, **cada una** de estas reglas tiene que revalidarse
server-side:

| Regla | Dónde está hoy |
|---|---|
| Jerarquía: sólo un Dueño opera sobre un Dueño | `esCuentaDeMayorJerarquia` |
| Nadie se edita ni se da de baja a sí mismo | `esCuentaPropiaRestringida` |
| No cambiar de rol con rutinas/dietas a cargo | `validarCambioDeRol` |
| La baja apaga el acceso | `darDeBajaEmpleado` / `darDeBaja` |
| No reactivar la cuenta de alguien dado de baja | `activarUsuario` |
| Renovar ≠ editar | `aplicarPlan` |
| Matriz de secciones y acciones por rol | `PERMISOS` en `config.ts` |

La tabla `PERMISOS` sirve como especificación para escribir esos guards.
No los reemplaza.
