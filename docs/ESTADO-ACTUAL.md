# OlimpOS — Estado actual

**Foto al 2026-09-30.** Sólo el presente: dónde estamos, qué falta y qué no se
probó. Lo permanente (idea, reglas del negocio, trampas) está en `CLAUDE.md`, y el
historial en git. **Al cerrar algo, se actualiza el punto, no se agrega una tanda.**

---

## Dónde estamos parados

- **Etapa:** las dos apps están completas y conectadas a la API real. El dueño las
  prueba **rol por rol en la PWA** y anota en `A CORREGIR PWA .txt`. Cada arreglo se
  hace en la PWA y se replica en Flet.
- **Probado y resuelto:** todo el rol Dueño.
- **Lista 2.0 del `.txt` (Recepcionista, Profesor, Socio): implementada** salvo lo
  que figura abajo como decisión pendiente. Falta que el dueño la pruebe en pantalla.
- **Base de datos: tiene los datos que el dueño cargó a mano** desde el estado de
  ENTREGA. **No vaciar ni recargar.** Cuentas hoy: `dueno`, `mario.dj`
  (recepcionista), `dami.silberstein` (profesor, todavía con la contraseña temporal)
  y `franco.distillio` (socio: se limpiaron sus pagos online de prueba; le queda el Trimestral cobrado en el mostrador, activo hasta el 15/12/2026). Las contraseñas están en el `.txt` de contraseñas.
- **OJO: la cuenta `dueno` no entra.** Quedó con `debe_cambiar_password` en true (un
  reseteo del 19/09 que no se completó) y la contraseña temporal no está anotada, así
  que `Demo2026!` ya no sirve y el backend rechaza su token. No hay otro dueño que
  pueda resetearla: la salida es reescribirle el hash con `auth.hashear_password`.
  Para probar con permisos de mostrador, `mario.dj` sigue funcionando.
- **Consecuencias para verificar:** las suites no se pueden correr (necesitan la base
  vacía). `pruebas_vistas.py` sólo entra con las cuentas que existan.
- **Backend:** 130 rutas en `/openapi.json`; si da menos, está respondiendo un
  proceso viejo. `check_permisos`: las tres copias coinciden (6 roles).
- **`PROCESOS-LOGICOS-REQUERIDOS.md`** (raíz) tiene los **173 procesos** del sistema en
  notación DFD lineal —167 rutas de la API contadas por operación, más 6 que corren
  solas—, cada uno con qué tablas escribe y cuáles lee, verificado contra las columnas
  de `db/schema.sql`. Es el mejor oráculo del repo para contrastar implementación contra
  especificación, y el esqueleto de la masterclass pendiente.

---

## Lo que falta, en orden

### 1. Hecho pero sin probar en pantalla
- **La habilitación de un profesor se apaga en vez de borrarse** (base, backend). Cierra el
  500 de "un profesor que dictó una clase no se puede dar de baja" y el mismo choque en
  `desasignar_profesor()`. `Profesor_Actividad` suma `activo` (**ya está en `db/schema.sql` y
  aplicado en Neon**; la única fila que había quedó prendida). Sacarlo de una actividad apaga
  la fila y **volver a habilitarlo reactiva esa misma fila**, con su historia; sacarlo dos
  veces da 404. La lista de habilitados de una actividad filtra por los tres flags
  (`ProfesorActividad.activo`, `Profesor.activo`, `Empleado.activo`) y habilitar a alguien
  dado de baja da 409. **La baja del empleado dejó de tocar las habilitaciones**: era
  innecesario —los cuatro lugares que ofrecen profesores ya filtran por `Empleado.activo`— y
  era lo que causaba el 500; de paso, al reactivarlo sus actividades vuelven con él, que antes
  había que reasignar a mano. Probado contra la base real con el escenario completo (profesor,
  actividad, horario y un turno ya dictado), marcado y borrado después: 18 chequeos, conteos
  iguales antes y después. La PWA y Flet **no necesitaron cambios**: el diálogo de asignación ya
  era un interruptor y sigue igual, sólo que ahora funciona siempre. **Falta verlo en pantalla.**
- **Los roles de un empleado se acumulan, y se apagan en vez de borrarse** (base, backend,
  PWA y Flet). Cambiar de rol borraba la fila del rol viejo, que es el destino de claves
  foráneas sin ON DELETE, así que respondía **409 a cualquiera con historial** (un socio a
  cargo, una rutina, un horario). Ahora la fila queda con `activo=false` sosteniendo su
  historial y `roles_de_persona` mira ese flag. Como los subtipos siempre fueron SOLAPADOS,
  de paso un empleado puede tener **varios roles a la vez**: el alta y la edición reciben
  una lista (al menos uno), las dos apps los eligen con **casillas**, y la tarjeta de
  Personal y la fila de Usuarios muestran **todos** (antes Usuarios mostraba sólo el primero
  y a un profesor lo daba como "Sin rol": a Flet le faltaba `profesor` en `ROLE_CONFIG`).
  Sacarle Entrenador **finaliza sus asignaciones activas**, igual que la baja; volver al rol
  reactiva su fila con título y matrícula intactos y NO reabre las asignaciones. Los
  selectores de entrenador, nutricionista y profesor y las validaciones de horario filtran
  por el flag. `_validar_cambio_de_rol()` se borró entero.
  **La columna `activo` ya está en `db/schema.sql` y aplicada en Neon** (las 4 filas que
  había quedaron prendidas). Probado llamando las funciones reales contra la base real con
  datos marcados y borrados después (22 chequeos, conteos iguales antes y después), y el
  árbol de controles de Flet auditado con estado simulado (15 chequeos, incluidas las
  trampas 2 y 8). Compila en las tres capas. **Falta verlo en pantalla, con el backend
  reiniciado** (uvicorn corre sin `--reload`).
- **Baja voluntaria desde el mostrador** (backend): la baja inmediata ahora respeta el tipo,
  así que la voluntaria deja viva la cuenta de acceso y la de mora o administrativa la apaga,
  igual que la baja programada y la del portal. Antes `dar_de_baja()` la apagaba siempre.
  Verificado con la función real sobre SQLite en memoria (6 caminos, los 6 bien; contra el
  código viejo fallan los 2 de voluntaria inmediata). Falta verlo en pantalla, con el backend
  reiniciado.
- **Estado del socio en el Dashboard** (backend): la tarjeta de socios recientes calcula el
  estado con `_estado_socio()`, la misma función que la grilla de Socios. Antes tenía su propia
  regla y mostraba "Vencido" a socios en pausa, sin membresía, dados de baja o con membresía sin
  vencimiento; el más visible era el recién dado de alta, en rojo. Los días de aviso quedaron en
  una sola definición del backend (`socios.py`, el dashboard la importa). Verificado corriendo la
  función real sobre SQLite en memoria (7 casos, todos iguales a la grilla); falta verlo en
  pantalla, **con el backend reiniciado** (uvicorn corre sin `--reload`).
- **Horarios y turnos (PWA + Flet):** en Actividades, el horario semanal (crear con
  profesor, dar de baja, regenerar) y la agenda de 7 días con los anotados de cada
  turno y cancelar. Con un horario cargado deberían aparecer turnos en "Mis clases"
  del profesor, "Mis turnos" del socio y "Próximos turnos" del Dashboard. **La base no
  tiene ningún horario todavía**: hay que cargar uno para verlo.
- **Recepcionista:** entra a Actividades con los mismos permisos que el Dueño; en el
  Dashboard ve los próximos turnos arriba de todo y los cobros en "Actividad
  reciente" (sin la métrica ni el gráfico de ingresos).
- **Alta y edición de socio** con fecha de nacimiento, domicilio y contacto de
  emergencia; botón rojo en la grilla para llamarlo (tel: y WhatsApp).
- **Rutina propia del socio**: el 500 era un resto del nivel retirado (`portal.py`
  leía `datos.nivel`); corregido, falta guardar una desde la pantalla.
- **Mi progreso**: tira de los últimos 7 días contra el objetivo de calorías de la
  dieta (±10%) y barras pintadas por cumplimiento; grasa y masa muscular plegadas
  detrás de "Tengo un estudio de composición corporal".
- **Sin cobros por adelantado** (backend, PWA y Flet): Cobros muestra "se puede renovar
  desde el X" en vez del botón; Recepción de Flet sólo ofrece "Cobrar cuota" cuando se
  puede; "Mi cuota" dice desde cuándo renovar; el combo cuota + abono sólo aparece sin
  cuota vigente. Probado por API (rechazos 409 y los tres casos de la regla). **Ojo: cobrar
  ese combo da 500** (ver hallazgos de B-05).
- **Baja programada** (backend, PWA y Flet): con la cuota paga la baja corre desde el
  día siguiente al vencimiento, se ve "Baja el dd/mm" en la grilla de Socios y en Mi
  cuota, y se puede anular. Probado a nivel base (programar, bloqueo de renovación y
  aplicación al llegar la fecha) en una transacción descartada; falta en pantalla.
  El personal también puede **dar de baja ahora** (al vencer o ahora en el modal de la
  PWA, casilla en Flet; con una baja programada, la adelanta). Probado llamando al
  endpoint en una transacción descartada.
- **Usuarios: los cinco arreglos de B-04** (backend, PWA y Flet). (1) A un **empleado dado de
  baja** no se le crea una cuenta nueva: no aparece entre los candidatos y el alta da 409; se
  reactiva desde Personal (antes entraba con su rol y veía a todos los socios). (2) El **nombre
  de usuario** se guarda y se compara en minúsculas (login, cambio de clave, edición y seeder):
  una cuenta renombrada `Mario.DJ` ya no queda afuera de Flet; renombrar muda la traba por
  intentos. (3) El **mail** de Usuarios pasa por `_email_valido()`, y ese validador corre ANTES
  que `EmailStr` en todos los esquemas (`mode="before"`): el error sale siempre en castellano y
  el mail siempre en minúsculas; y a un empleado no se le puede dejar sin mail ni teléfono. (4)
  El Dueño ya no ve "Desactivar" sobre su propia cuenta, y una cuenta **bloqueada** ofrece
  Desbloquear y Desactivar (antes había que destrabarla para apagarla). (5) **Crear una cuenta**
  abre el panel de entrega con mail y WhatsApp, como el reseteo (la lista de candidatos trae el
  teléfono). Probado por HTTP contra un PostgreSQL descartable y Flet con estado simulado; falta
  en pantalla, **con el backend reiniciado**.
- **Edición y cambio de rol de empleados** (backend, PWA y Flet). Editar con el mismo rol
  **sólo toca los campos que vinieron** (`model_fields_set`, igual que el socio): antes
  editarle el teléfono a un entrenador desde la PWA le borraba título y matrícula, desde
  Flet la especialidad, y a una nutricionista la PWA le mudaba la matrícula al título. La
  PWA manda sólo el campo que muestra, precargado con la columna exacta
  (`detalleEditable()`); Flet suma el campo Especialidad. El cambio de rol revisa todo lo
  que apunta al rol viejo y responde 409 con el motivo en vez de un 500 (ver Menores). Y el
  selector de nutricionistas se recorta a la propia, como el de entrenadores (antes la PWA
  preseleccionaba a otra y la dieta nueva daba 403). Probado con las funciones reales contra
  un PostgreSQL descartable y el diálogo de Flet auditado armándolo con estado simulado;
  falta en pantalla, **con el backend reiniciado**.
- **La baja de un entrenador finaliza sus asignaciones activas** (backend): el socio deja
  de verlo en "Mi entrenador"; las ya finalizadas conservan su fecha y reactivarlo no las
  reabre. Las confirmaciones de baja de Personal (PWA y Flet) lo avisan. Probado con la
  función real contra un PostgreSQL local descartable; falta en pantalla, **con el backend
  reiniciado**.
- **Confirmaciones sin "Auditoría"** (PWA): Personal, Usuarios, Rutinas y Nutrición
  prometían *"queda registrada en Auditoría"* y no hay auditoría. Ahora dicen lo que pasa
  (Rutinas y Nutrición, con el texto de sus gemelas de Flet). Compila.
- **Borrar una cuenta de acceso** (`DELETE /usuarios/{id}`, PWA y Flet): borra sólo la
  cuenta; la persona y su historial quedan y se le puede crear otra.
  `Asistencia.id_registrado_por` pasa a NULL. Nadie borra la propia, sólo un Dueño
  borra la de un Dueño y nunca la última. Compila en las tres capas; sin probar.
- **Los 4 menores de la tanda** (backend, PWA y Flet):
  **Homónimos:** `ProfesorActividadOut` suma `dni` y `legajo`, y la asignación y el
  selector del horario muestran "Legajo X" (o el DNI si no tiene). Verificado por API.
  **Profesor en Flet:** entra y ve `SinSeccionesView` ("tu pantalla está en la app del
  celular"). Hasta el 26/09 el login lo frenaba antes con el mensaje de los socios; ahora
  `ROLES_SIN_SECCIONES_QUE_ENTRAN` (`app/permisos.py`) lo deja pasar y el Socio sigue afuera.
  Y el alta de Flet ya le crea cuenta (mandaba `crear_cuenta = rol != "Profesor"`).
  Verificado armando la carga real con una sesión de profesor simulada; falta en pantalla.
  **Cambiar el profesor de un horario ya creado:** `PUT /actividades/horarios/{id}/profesor`,
  con la misma validación que el alta. Arrastra a los turnos futuros HABILITADOS (de ahí
  sale "Mis clases"); los pasados y los cancelados no se tocan. Probado contra la base
  real con datos marcados, borrados después (ver la trampa del rollback en `CLAUDE.md`).
  **Diálogos de nutrición en Flet:** los cuatro cierran tocando afuera, como sus gemelos
  de la PWA. No se tocó el `modal` de `confirm_dialog`/`form_dialog`, que son compartidos.
  Falta verlo todo en pantalla.
- **"Sin acceso a la app" en la grilla de Socios** (backend, PWA y Flet). Desactivar
  la cuenta desde Usuarios dejaba a Usuarios diciendo "inactivo" y a Socios
  "Activo" de la misma persona, porque son dos banderas (`Usuario.activo` vs
  `Socio.activo`) y ningún panel mostraba la primera. **Decisión del dueño: NO se
  acoplan** —el socio sin app sigue pagando y entrenando, y sigue contando en el
  dashboard— así que `SocioOut` suma `cuenta_activa` y la fila avisa. Probado por
  API prendiendo y apagando la cuenta de `ricky.edit`, que quedó como estaba
  (desactivada). Falta verlo en pantalla.
- **Contactos de emergencia: ahora son VARIOS** (backend, PWA y Flet). La tabla
  `Contacto_Emergencia` siempre fue 1:N pero la app la manejaba con tres campos
  planos y hacía upsert de UNA fila, así que cargar a la madre pisaba a la
  pareja. Ahora tiene CRUD propio, calcado del de teléfonos: uno principal (el
  que sigue saliendo en la grilla y en el botón rojo de llamar), no se repite el
  mismo número, y al borrar el principal asciende el más viejo.
  `EmergenciaModal` de la PWA y el diálogo de Flet pasaron de mostrar un contacto
  a gestionar la lista; el socio gestiona la suya desde "Mi perfil"
  (`MisContactosEmergenciaCard`, que reemplaza los tres campos del formulario).
  **Probado por API** —los dos lados, mostrador y socio, con la base restaurada al
  terminar—. Del diálogo de Flet se auditó el árbol de controles armándolo con el
  estado simulado (los dos contactos, un solo principal, alta, sólo lectura, ficha
  vacía, y las trampas 2 y 8 de Flet): **falta sólo la revisión visual** de las dos
  apps, que es lo único que no cubre ninguna verificación automatizada.
- **README:** ya tiene capturas (dashboard, cobros y el portal del socio en el
  celular) y cómo verlo desde el teléfono. El dueño avisó que **no son definitivas**:
  cuando haya mejores, se reemplazan los archivos de `docs/capturas/`. Falta probar
  el instalador en una máquina limpia.
- **README y `instalar.ps1` en la raíz** (para quien clona el repo). El instalador
  verifica Python 3.11+/Node 20+/git, instala con `winget` lo que falte preguntando
  (`-SinPreguntar` no pregunta, `-SoloVerificar` no toca nada), arma el venv, instala
  las dependencias de los tres proyectos, crea el `.env` con la clave de sesión
  generada y verifica. Probado en modo verificación en esta máquina; **falta probarlo
  en una máquina limpia**, que es donde se ve si instala de verdad. **El README no
  tiene capturas todavía.** OJO: un `.ps1` con acentos tiene que guardarse en UTF-8
  **con BOM** o PowerShell 5.1 lo lee como ANSI y ni siquiera parsea.
- **Objetivo y observaciones del socio en la PWA** (alta y edición): sólo los pedía
  Flet, así que editar desde la PWA los mandaba vacíos y **los borraba**. Ahora están
  en el formulario y, además, el PUT de socio **sólo toca los campos que vinieron en
  el pedido** (`model_fields_set`): un formulario incompleto ya no puede borrar datos
  en silencio; mandar el campo vacío sí lo borra. Probado por API contra la base real
  (parcial, vacío explícito y restauración), falta verlo en pantalla.
- **Sesión caída (401) manda al login** en la PWA: `api.ts` avisa por callback,
  `App.tsx` limpia el store y muestra el motivo del backend, y ProtectedRoute
  redirige. Quedan afuera `/login`, `/cambiar-password` y `/me`, donde un 401 no es
  una sesión caída. Se ve, por ejemplo, al resetearse uno mismo la contraseña.
  Compila; falta verlo en pantalla.
- **Teléfonos con código de país** en los 6 campos de la PWA y los 4 de Flet (alta y
  edición de socio y empleado, contacto de emergencia, agregar teléfono, Mi perfil).
  En Flet, editar un empleado ya precarga el teléfono (antes guardar lo borraba).
- **Mi cuota**: se sacaron "Saldo pendiente" y el bloque de deudas (la tabla Deuda no
  existe, siempre daban 0); ahora avisa "cuota vencida" y muestra el último pago.
- Ventanas de catálogo de ejercicios, armar rutina, armar dieta y registrar comida:
  pantalla completa en el celular, ventana centrada desde tablet.
- Alta de socio con "Cobrar ahora"; el chip "2º de hoy" (ojo: fichar acredita
  reservas); el aviso de cuenta trabada en login y cambio de contraseña.

### 2. Pedido del dueño, sin empezar
- **Recepción en la PWA.** Hoy el panel del mostrador existe sólo en Flet
  (`app/views/recepcion.py`): próximos turnos con quién se anotó y su estado de
  llegada, los vencidos recientes, búsqueda por DNI con la cuota y el próximo turno
  resueltos, y fichar o cobrar sin salir de la pantalla. El dueño lo quiere también en
  la web. **El backend ya está entero** (`GET /recepcion/panel`, `/recepcion/turnos/{id}`
  y `/recepcion/buscar`, sección ASISTENCIA). La PWA consume **uno solo**,
  `/recepcion/turnos/{id}` (`getDetalleTurno` en `turnosService.ts`, usado por
  `AgendaTurnos`); el panel y la búsqueda no los llama nadie todavía. Falta la pantalla:
  ruta nueva, ítem de menú, los servicios de panel y búsqueda, y la matriz de permisos en
  sus tres copias (hoy `RECEPCION` sólo existe en la de Flet).
- **Masterclass del código: Partes A0 y A cerradas, B en curso (B-01 a B-05), C sin escribir.** El dueño quiere
  una explicación completa del código a nivel de cátedra de maestría: conceptos generales
  primero y después, proceso por proceso, qué archivo y qué rango de líneas lo implementa en
  las tres capas. El prompt está en **`PROMPT-ZARPADO.md`** (raíz): cuatro partes —A0
  cimientos, A el sistema, B los 173 procesos, C los 8 subsistemas que no cuelgan de ningún
  endpoint— y el método (cada concepto por el problema que lo originó, bajar hasta un piso
  declarado, volver al código, **una sola explicación por concepto**, conexiones de una línea,
  ingeniería inversa), más la plantilla de cada proceso de B. Los entregables van a
  `docs/masterclass/`.
  **Hecho:** los 26 capítulos de A0 y A, el glosario (`A-98`: 144 conceptos, remisiones y
  32 patrones con nombre), el mapa de conexiones (`A-99`; sus notas de mantenimiento dicen
  qué semillas del contrato se corrigieron), el índice (`00-indice.md`, con la tabla de
  ruteo) y el paso de coherencia de la sección 11 del prompt. **De la Parte B: B-01**
  (Acceso y sesión, 1 a 5), que fija la forma de los demás —la plantilla de cada proceso, las
  tablas cruzadas contra la línea DFD y una nota única sobre el 403 de CSRF, que ninguna
  línea del archivo de procesos nombra—, **B-02** (Socios, 6 a 28), que abre con las piezas
  comunes de la sección y explica V-10, **B-03** (Personal, 29 a 37), que además explica
  qué ve la pantalla con un 500 (proceso 36; lo cita A-04), y **B-04** (Usuarios y cuentas,
  38 a 45), que explica por qué el validador del mail corre antes que `EmailStr` (lo cita B-02), y
  **B-05** (Cobros y pagos, 46 a 51), que se apoya en A-02 y A-04 para no repetir el cobro, y
  **B-06** (Asistencia, 52 a 56), el más corto y el de la decisión de negocio más fuerte —el
  gimnasio no cierra la puerta—, que explica el 201 con `permitido=False` y por qué el "asistió"
  de una reserva no se guarda.
  **Lo que sigue es B-07 (Recepción, 57 a 59)**, y así hasta B-15; después C. Todo capítulo
  de B cierra con su "Con qué se conecta" y agrega sus conexiones nuevas al mapa: **una
  conexión va en los dos lugares, nunca en uno solo**.
  **La masterclass está al día con los dos cambios del 2026-09-29/30** (roles múltiples y la
  habilitación que se apaga). El porqué de los dos vive junto, en **A-10**: la sección
  *"El rol que se apaga"* y, adentro, *"La segunda fila de esa clase, y cómo se cerró"*. Ésa es la
  **fuente única** del concepto y la que cierra con la lección de diseño (cuando un `DELETE` choca
  con una clave foránea, la pregunta es cuántas cosas dice esa fila, no cómo forzar el borrado).
  **B-03** reescribió las piezas comunes y los procesos 29, 30, 35, 36 y 37 —el 35 cambió de
  título, así que su ancla es `#35-editar-un-empleado-y-sus-roles`, y la nota del 500 del profesor
  se borró porque el 500 ya no existe—; **A-05**, **A-06**, **A-07** y **B-04** corrigieron lo que
  decían de más; **A-98** tiene el concepto, su remisión y el patrón (145 conceptos) y **A-99** las
  conexiones nuevas repartidas por tipo (164), con la de la baja del profesor pasada de
  contradicción a causa. Verificado contra la foto de `HEAD`: ningún problema nuevo de anclas,
  rangos ni símbolos.
  **Cómo remapear las citas por línea, que fue lo que más costó.** Hay tres herramientas en el
  scratchpad de esta sesión: una para las citas de prosa, otra para **la columna de líneas de las
  tablas** —que la de prosa no ve, porque ahí el número no va entre comillas invertidas: eran 338
  filas que nunca se habían remapeado— y un verificador que contrasta anclas, rangos y símbolos
  contra una foto de `HEAD` hecha con `git worktree`. La de tablas no mueve una fila si el símbolo
  deja de caer adentro del rango nuevo, y eso es lo que la hace confiable.
  **El orden importa y equivocarse cuesta caro: código → remapear → recién entonces escribir las
  citas nuevas.** Ninguna de las dos es idempotente (comparan contra una referencia), así que una
  cita recién escrita a mano ya es "nueva" y el remapeo la mueve de más. Pasó, y hubo que corregir
  unas quince a mano contra el archivo. Si la referencia ya no es `HEAD` —porque hubo una tanda
  antes en la misma sesión—, se reconstruye el "antes" **revirtiendo los bloques textuales exactos**
  que se insertaron, afirmando cada reversión con `count()==1`; una heurística que adivine dónde
  empieza y termina el bloque erra por una línea y arruina todo el remapeo.
  **Se escriben de a uno y directamente, sin workflows en paralelo:** el dueño lo decidió
  por costo, después de que una corrida de 30 agentes gastara 2,2M tokens y entregara sólo
  el contrato. Los workflows de `.claude/workflows/` quedaron de ese intento: no
  relanzarlos.
  **Herramientas, fuera del repo**, en el scratchpad de la sesión `0ed151dd-…`
  (`%TEMP%/claude/D--OlimpOs/0ed151dd-21e2-452f-8c62-06065f5b0e32/scratchpad`): el
  **contrato de vocabulario** (`CONTRATO-VOCABULARIO.md`: 144 conceptos con un único dueño,
  los nombres de los 52 archivos y los nombres canónicos) y, en `slug/`, los verificadores
  que se corren después de cada capítulo: `anclas.mjs` (anclas contra `github-slugger`),
  `citas.mjs` (cada cita de código), `tablas_b.mjs` (rango y símbolo de cada fila de las
  tablas de B), `rango_simbolo.mjs B-0X-….md` (que el símbolo de cada fila caiga adentro de su
  rango), `coherencia.mjs` (enlaces y encabezados) y los generadores: el glosario
  (`glosario_datos.mjs` + `node glosario_generar.mjs && node glosario_armar.mjs`) y el mapa
  (`mapa_datos.mjs` + `node mapa_generar.mjs && node mapa_armar.mjs`, con los totales
  calculados). Si el scratchpad no está, hay que regenerar el
  contrato antes de escribir. **Anclas:** GitHub las arma **conservando las tildes y la ñ**
  (`#transacción-…`), y un símbolo como `≠` deja doble guion.
  **Lo que depende de cómo PostgreSQL aplica una restricción se corre, no se lee**, en un
  Postgres local descartable: esta máquina tiene PostgreSQL 17 en `D:\PostgreSQL`; `initdb` en
  el scratchpad, un puerto propio, `db/schema.sql`, y las funciones del router llamadas
  directamente con `DATABASE_URL` apuntando ahí **antes** de importar el backend. Nunca Neon, y
  el clúster se borra al terminar. B-03 lo usó para seis hallazgos. B-04 fue más lejos: **por
  HTTP**, con el `TestClient` de FastAPI contra la app real (sin el `with`, no corre el
  arranque). `httpx` no está en el venv y no se instala ahí: vive en
  `pruebas_pg/pylib` del scratchpad de herramientas, sumado AL FINAL de `sys.path`;
  `pruebas_pg/usuarios_http_pg.py` y `usuarios_arreglos_pg.py` son los moldes. Cuando se arregla
  código que la masterclass cita por línea, `pruebas_pg/remapear_citas2.py <copia de antes>`
  recalcula las citas de todos los capítulos (guardar la copia ANTES de editar); las referencias
  en texto plano ("línea 529", "(134-136)") no las toca y hay que buscarlas aparte.
- **Hallazgos de código que salieron escribiendo la masterclass, pendientes de decisión**
  (cada uno quedó explicado en su capítulo como nota marcada; ninguno se tocó):
  - **`gestionDeudas` no protege nada:** está en la matriz en sus tres copias y ningún
    endpoint la exige (0 usos), porque no existe la deuda. Y `ACCIONES_SIN_PANTALLA` de
    `PermisosPanel.tsx` le dice al dueño que `gestionPromociones` y `gestionTurnos` no se
    aplican, cuando se exigen en 8 endpoints cada una. Arreglarlo toca las tres copias de la
    matriz y `check_permisos.py` (A-08).
  - **Los diálogos de Flet nunca salen de `page.overlay`:** `close_dialog()` sólo los oculta,
    así que se acumulan en la PC del mostrador. Flet 0.84 trae `page.show_dialog()`, que sí
    los saca, pero la técnica de auditar diálogos leyendo `page.overlay` depende de la forma
    actual (A0-13).
  - **La PWA no muestra el aviso al fichar:** `registrarAsistenciaManual()`
    (`services/actividadService.ts`) se queda sólo con `asistencia` y descarta `advertencia`,
    `permitido`, `mensaje`, `clase_acreditada` y `turno_perdido`, y `AsistenciaView` saca
    siempre un aviso verde propio. Un socio con la cuota vencida ficha y el mostrador ve verde,
    contra *"se muestra un aviso"* de `CLAUDE.md`. Flet sí lo muestra, en ámbar (A-01).
  - **Menores de B-01:** el largo mínimo de la contraseña nueva responde en inglés
    (*"String should have at least 8 characters"*, lo arma Pydantic), tapado porque las dos
    apps controlan el largo antes. Y la línea DFD del login no nombra su 400 ni su 429.
  - **La PWA registra todas las bajas del mostrador como `ADMINISTRATIVA`**, sin preguntar
    el tipo ni el motivo (`sociosService.ts`, `darDeBajaSocio()`); Flet pregunta los dos, con
    voluntaria por defecto. Como la voluntaria deja viva la cuenta y la administrativa la
    apaga, el socio que se va por su cuenta conserva la app si lo da de baja Flet y la pierde
    si lo da de baja la PWA, que es la referencia (B-02, proceso 13).
  - **Flet sugiere cargar lesiones en `observaciones`** (*"Lesiones, restricciones..."*),
    un campo que el Recepcionista sí ve; la PWA dice lo contrario, *"las lesiones y
    condiciones van en la ficha médica"* (B-02, proceso 7).
  - **El alta que reusa una persona** (un empleado que se hace socio) descarta sin aviso la
    fecha de nacimiento, el domicilio y el contacto de emergencia del formulario, y agrega el
    teléfono como principal sin desmarcar el que tenía: la ficha queda con dos principales.
    Y el comentario del reuso cita "alguien que se dio de baja y vuelve", que en realidad
    recibe un 409: el que vuelve se reactiva (B-02, proceso 7).
  - **La baja inmediata no cierra la pausa en curso:** la membresía se cancela pero su
    `Congelamiento` queda `ACTIVO`, y el portal lo encontraría como pausa vigente si el socio
    se reactiva y paga antes de la fecha de fin de esa pausa (B-02, proceso 13).
  - **Quién entrena a quién:** `CLAUDE.md` dice que lo deciden el Dueño y el Recepcionista;
    el código deja además que el Entrenador se asigne o se suelte a sí mismo (`socios.py`,
    `GESTION_RUTINAS`). Decidir cuál rige y alinear el otro (B-02, proceso 19).
  - **Menores de B-02:** `GET /socios/entrenadores/{id}/socios` no tiene ningún cliente
    (su docstring dice que lo usa el entrenador, y no hay pantalla de "mis socios"); editar
    un teléfono o un contacto no controla el número repetido (hoy inalcanzable: las pantallas
    sólo usan el `PUT` para marcar el principal); vaciar el teléfono en la edición de la
    ficha borra el principal sin ascender a otro.
  - **Menores de B-03:** el `motivo` de la baja de un empleado viaja en el pedido pero no
    lo pide ninguna pantalla ni se guarda; la grilla de personal no carga la cuenta (una
    consulta más por empleado; Profesor y la franja ya se cargan); en Flet el subtítulo cuenta a los de baja como activos, el chip
    dice "Turno —" a quien no es recepcionista, el DNI se puede tipear en la edición y se
    descarta, y un teléfono no se puede quitar; el alta que reusa a un ex socio conserva su
    cuenta aunque esté apagada; reactivar borra la fecha de egreso; el docstring de
    `personal.py` llama "estado válido" a un empleado sin rol, que la base rechaza (ahora sí
    alcanzable con las cuatro filas apagadas, aunque ninguna pantalla lo permite).
  - **La cuenta de un socio dado de baja por mora o administrativa se puede volver a prender
    desde Usuarios** (o crearle una nueva) sin reactivarlo como socio. No se tocó porque
    depende del tipo de baja: la voluntaria le deja la cuenta viva a propósito. Decidir si
    Usuarios tiene que frenar las otras dos (B-04, proceso 45).
  - **Cobrar la cuota junto con un abono de actividad da 500, siempre** (corrido, por HTTP):
    `schemas.py` define DOS clases `InscripcionOut`; la segunda (Actividades, 2026-08-11)
    pisa a la primera para `cobros.py`, que la arma con ocho campos de los catorce que exige.
    No queda nada escrito. Las dos apps ofrecen ese combo. El arreglo es renombrar la primera
    y usarla en `cobros.py` (B-05, proceso 46).
  - **Ninguna pantalla anula un pago**: `anularPago()` (PWA) y `anular_pago()` (Flet) existen
    y no los llama ninguna vista, así que "corregir un cobro", uno de los cuatro casos de la
    caja, sólo se puede por API. Y anular cancela la membresía pero deja ACTIVO el abono de
    actividad cobrado en el mismo pago (corrido) (B-05, proceso 47).
  - **Los planes de membresía no se administran desde ninguna app**: el alta existe en la API
    sin pantalla, y editar el precio o dar de baja un plan no existe en ningún lado. Cambiar
    un precio exige editar la base (B-05, proceso 50).
  - **Un reembolso de Mercado Pago no le quita la membresía al socio** (corrido): el pago
    pasa a `REEMBOLSADO` y la membresía sigue `ACTIVA`; anular en el mostrador sí la cancela.
    Hoy no se manifiesta porque Mercado Pago no está conectado (B-05, proceso 51).
  - **Menores de B-05:** el nombre duplicado de un plan se compara con `ilike` y el `_` hace
    de comodín (corrido: "Pase_libre" choca con "PaseXlibre"); el pago online confirmado sin
    membresía sólo queda en un `print`; las dos apps siguen armando "deudas" que llegan
    vacías; la PWA tiene funciones de Cobros que nadie usa y comentarios viejos (deudas en
    `anularPago`, `id_membresia NOT NULL` en el combo, el selector del alta en
    `listarTiposMembresia`); Flet no filtra los planes dados de baja.
  - **Los procesos 54 y 56 no los llama ninguna pantalla** (B-06): `GET /asistencia/socio/{id}`
    —el historial de ingresos de un socio, que responde "¿viene seguido?"— y
    `POST /asistencia/{id}/salida` —el egreso—. El primero es una pérdida: el lugar natural sería la
    ficha del socio, al lado del botón de contacto de emergencia. El segundo es coherente con su
    propio docstring (*"la mayoría de los gimnasios no controla la salida"*), así que lo que hay que
    decidir es si espera al molinete —como el camino RFID, que sí está anotado como pendiente— o si
    sobra.
  - **El feed de ingresos del día no carga nada por anticipado** (B-06): `_a_asistencia_out()` lee
    `a.socio` y `socio.persona` por cada fila y la consulta no trae ninguna relación: dos consultas
    perezosas por ingreso, el mismo N+1 que ya se cerró en Socios y en Usuarios con `selectinload`.
    Leído, no medido.
  - **Menores de B-04:** el cartel "exclusiva para administradores" lo ve el Recepcionista,
    que usa la sección; el comentario de la PWA que dice "no hay backend de email"
    (`UsuariosView.tsx`); contar los dueños al borrar una cuenta de dueño deriva roles sin
    carga anticipada.

### 3. Menores
- **Contador de repeticiones** (el único que el dueño dejó afuera de la tanda):
  rediseñar el overlay (las líneas verdes del esqueleto son sólo para afinar) y
  seguir ajustando umbrales probando en el celular.

### 4. Grandes, después de la lista
- **Coach con IA (decidido, sin implementar; AVISARLE al dueño antes de arrancar).**
  - Chat a pedido con historial guardado (tabla nueva chica), corriendo en el backend
    con **Claude vía API** (Haiku 4.5, necesita API key). Más adelante se puede migrar
    a un modelo open-weights local con el mismo prompt.
  - **Tool-use sobre los mismos endpoints del socio**, con su token: **propone → el
    socio confirma → aplica**, nunca en silencio.
  - **Nunca manda patologías.** Consentimiento explícito del socio (falta decidir
    dónde se guarda).
  - Control de costo: resumen compacto, ventana acotada y tope por día. De yapa,
    autocompletar macros en el registro de comida (hoy se cargan a mano).
  - **Falta definir con el dueño:** la metodología de entrenamiento y nutrición del
    system prompt.
- **Mercado Pago:** falta el token, el secreto del webhook y una URL pública. No
  depende del código. Hoy corre en modo simulado (`MP_MODO_SIMULADO`).
- **Seguridad:** quedan V-08 (JWT sin revocación) y V-10 (Entrenador y Nutricionista
  leen a todos los socios), que son **a propósito**, y V-11 (`X-Client-Type` elige
  cookie o Bearer), que es endurecimiento pendiente. Ver
  `docs/vulnerabilidades a arreglar.md`.
- **Videos institucionales en la tele** (mismo demonio de videos, otra carpeta).
- **Fichaje con RFID: lo ÚLTIMO de todo**, cuando el dueño compre el lector.
  - **Ya existen** `Socio.codigo_rfid` (única, nullable) y `POST /asistencia/fichar`,
    que acepta `codigo_rfid` y guarda `metodo_registro='RFID'`. **Parece código muerto
    y NO lo es: no limpiarlo.**
  - Falta asignarle el código al socio y que el lector se autentique sin un `Usuario`.
    La idea que se venía eligiendo: una clave de dispositivo en `.env` + un endpoint
    sin sesión. `Asistencia.id_registrado_por` ya admite NULL.
