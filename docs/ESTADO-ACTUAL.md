# OlimpOS — Estado actual

**Foto al 2026-10-01.** Sólo el presente: dónde estamos, qué falta y qué no se
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
- **La cuenta `dueno` entra** (el dueño la usó en Flet el 2026-10-02). Si su contraseña
  cambió desde la última vez que se anotó, va al `.txt` de contraseñas.
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
- **Una rutina o un plan dados de baja ya no se pueden asignar** (backend, PWA y Flet). Era el
  hallazgo más grueso de B-09: las dos pantallas y los dos docstrings prometían que la rutina
  desactivada *"deja de ofrecerse para asignar"* y **nadie lo hacía cumplir** —`asignar_rutina()` no
  miraba `rutina.activo`, la tarjeta de la PWA dibujaba "Asignar" con sólo tener el permiso, y el
  diálogo de Flet lo ofrecía al lado de "Reactivar"—, así que la baja hacía una sola cosa: pintar el
  chip "Inactiva". **Nutrición tenía el defecto calcado** y se arregló igual, porque es el mismo
  código escrito dos veces. Ahora el endpoint contesta **409** con el mensaje que dice qué hacer
  (*"reactivala antes de asignarla"*) y las **cuatro** pantallas esconden el botón: la tarjeta y el
  detalle de Rutinas y los de Nutrición, con un `_asignable()` único por vista en Flet. **Editar sigue
  permitido** con la rutina de baja —se la corrige y después se la reactiva—, que es lo único que se
  quería conservar. **La regla quedó escrita en `CLAUDE.md`** (Entrenamiento y actividades), porque el
  409 y el botón escondido parecen redundantes y no lo son: sacar el 409 reabre el agujero.
  Probado llamando a las dos funciones reales contra SQLite en memoria (8 chequeos:
  409, nada escrito, y los activos siguen andando) y auditando el árbol de controles de Flet con estado
  simulado (16 chequeos, las cuatro pantallas). Compila en las tres capas (`import main`, `compileall`,
  `tsc -p tsconfig.app.json`, `oxlint`). **Falta verlo en pantalla, con el backend reiniciado**
  (uvicorn corre sin `--reload`).
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
- **Masterclass del código: Partes A0 y A cerradas, B en curso (B-01 a B-10), C sin escribir.** El dueño quiere
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
  de una reserva no se guarda; **B-07** (Recepción, 57 a 59), donde el corte de la API no sigue a
  las entidades sino a una pantalla, y lo que eso compra no es velocidad sino **una sola foto del
  instante**; y **B-08** (Actividades, 60 a 87), el más grande hasta ahora: las cinco entidades, las
  tres reglas del módulo, el saldo que se cuenta en vez de guardarse, y el pasaje del lock de
  `reservar()` —por qué una restricción de integridad NO es un control de concurrencia y por eso
  están el lock y el disparador—; y **B-09** (Rutinas, 88 a 97), el de los tres niveles
  —`Ejercicio`, `Rutina`, `Asignacion_Rutina`— y el que más hallazgos sacó CORRIENDO el código:
  el `flush` que no hace falta, el costo medido de los tres listados y el 500 del (día, orden)
  repetido. Es el primer capítulo verificado con **SQLite en memoria** llamando a las funciones
  reales del router, que es la técnica que SÍ corre en esta máquina (acá no hay PostgreSQL local
  ni `httpx`: el clúster descartable y el `TestClient` son de la otra PC). Sirve para lo que no
  depende del motor —el orden de las sentencias que emite SQLAlchemy, el número de consultas, un
  índice único parcial—; los costos en ms siguen siendo de Neon y se dicen como tales. Los
  guiones quedaron en el scratchpad de la sesión: `b09_flush.py`, `b09_consultas.py`,
  `b09_menores.py` y `b09_expire.py`.
  Y **B-10** (Nutrición, 98 a 107), que es el espejo de Rutinas y por eso **no repite nada**: abre con
  la tabla de correspondencias proceso a proceso y los nueve mecanismos que se heredan de B-09, y sólo
  explica las **cuatro diferencias**. La grande es el proceso 104: `Registro_Comida` SÍ apunta a
  `Comida`, así que el `PUT` tiene que desvincular lo que el socio registró antes de borrar las comidas
  —y el docstring de esa misma función dice que *"nada apunta a Comida"*, porque se copió de
  `editar_rutina`, donde es verdad—. Corrido con `PRAGMA foreign_keys=ON`, que es lo que hizo falta para
  probar una clave foránea en SQLite (y obliga a darle un `Dueno` de verdad a la `Sede` de prueba).
  **Lo que sigue es B-11 (Patologías, 108 a 109)**, que son dos procesos y debería ser el capítulo más
  corto de la Parte B. Y así hasta B-15; después C. Todo capítulo
  de B cierra con su "Con qué se conecta" y agrega sus conexiones nuevas al mapa: **una
  conexión va en los dos lugares, nunca en uno solo**.
  **A0-08 se corrigió con lo que salió corriendo B-09:** daba por bueno el comentario del `flush` de
  `asignar_rutina` ("SQLAlchemy emite los INSERT antes que los UPDATE") y es al revés. Ahora explica que
  lo que se paga por no poder diferir un índice parcial no es esa línea sino que **ningún camino puede
  pasar por un estado intermedio con dos ACTIVA**, y que el camino de hoy no la necesita por el orden que
  eligió el ORM, no por diseño. B-09 remite ahí en vez de explicarlo dos veces, y el paso 2 de
  `test_una_sola_activa.py` quedó anotado por lo que de verdad prueba (que la reasignación funcione, no
  que esa línea haga falta).
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
  **Cómo remapear las citas por línea, que fue lo que más costó.** Hay tres herramientas (dónde
  están en cada PC, más abajo): una para las citas de prosa, otra para **la columna de líneas de las
  tablas** —que la de prosa no ve, porque ahí el número no va entre comillas invertidas: eran 338
  filas que nunca se habían remapeado— y un verificador de anclas, rangos y símbolos. La de tablas
  no mueve una fila si el símbolo deja de caer adentro del rango nuevo, y eso es lo que la hace
  confiable.
  **El verificador da TODO BIEN sobre la masterclass entera**, y llegar ahí obligó a arreglarlo dos
  veces: GitHub **conserva los guiones bajos** de un identificador (`#precio_pactado-contra-…`) y
  **deja doble guion** donde borró un símbolo (`## Escala 16 · La regla` → `#escala-16--la-regla`),
  así que un slug que los colapse inventa 40 anclas rotas que no existen. Y un `localhost:5173` no
  es una cita de línea. Con eso corregido quedaron 9 problemas **reales**, todos del mismo tipo: una
  cita de continuación (`` `:123` ``) hereda el último archivo NOMBRADO, y si la última fila de la
  tabla "dónde vive el código" nombra otro archivo, la cita apunta al equivocado. Se arreglaron los
  9 —en A0-06, B-01 y B-02— nombrando el archivo en la primera cita de cada bloque; dos de B-01
  apuntaban además al bloque equivocado. **Regla para el próximo capítulo: la primera cita de prosa
  después de cada tabla nombra su archivo.** B-09 la violó cinco veces y las cinco las encontró el
  verificador: **correrlo no es opcional, es lo que hace cumplir la regla.**
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
  **Herramientas en ESTA PC (E:), fuera del repo**, en el scratchpad de la sesión `d0e15dcc-…`:
  `C:\Users\gianl\AppData\Local\Temp\claude\E--OlimpOS-OlimpOS\d0e15dcc-aaed-4191-8f35-fd7381df34de\scratchpad`.
  Son Python y se corren con el venv del backend: **`verificar.py`** (anclas, rangos de línea y
  símbolos de las tablas de B; tiene que dar TODO BIEN después de cada capítulo), **`remapear.py`**
  (citas de prosa: en `TOCADOS` van los archivos de código que se editaron y en `CONTEXTO` todos los
  que la masterclass cita, para que un `` `:N` `` suelto sepa a qué archivo pertenece; compara contra
  `HEAD`, así que se corre ANTES de commitear el código) y **`remapear_tablas.py`** (la columna de
  líneas, sobre todos los archivos). Los moldes de prueba también están ahí: `b09_flush.py`,
  `b09_consultas.py`, `b10_nutricion.py` y `arreglo_baja.py` (SQLite en memoria con los modelos
  reales), `auditar_asignar.py` (árbol de controles de Flet) y `a99_b10.py` (sumar conexiones a
  A-99 con su índice). Una sesión nueva tiene OTRO scratchpad: estas herramientas siguen en ese
  directorio y se copian de ahí. **Están en `%TEMP%`: si Windows limpia los temporales, se pierden.**
  **Herramientas en la OTRA PC (D:)**, en el scratchpad de la sesión `0ed151dd-…`
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
  **Trampa de Flet 0.84 al auditar un diálogo:** el label de un `ft.TextButton("Asignar")` NO vive en
  `.text` (que queda en `None`) sino en `.content`, y ahí es un **str pelado**, no un `Control`. Un
  recorrido del árbol que sólo junte `ft.Text` no ve ningún botón de un `AlertDialog` y da todos los
  chequeos de presencia por fallados — parece un bug del código y es del recorrido. El auditor tiene
  que juntar también los `str` de `.content` (y de `.tooltip`).
  **Lo que depende de cómo PostgreSQL aplica una restricción se corre, no se lee.** En ESTA PC (E:)
  no hay PostgreSQL ni `httpx`, así que se corre contra **SQLite en memoria** con los modelos y las
  funciones reales del router (B-09 y B-10): sirve para el orden de las sentencias, el número de
  consultas, un índice único parcial y —con `PRAGMA foreign_keys=ON`— una clave foránea; dos
  artefactos del motor: `server_default=func.now()` no entra en una columna `Date` (se le saca el
  default o se pasa la fecha) y con las FK prendidas la `Sede` necesita su `Dueno`. Lo que depende
  de Postgres de verdad (un disparador, un lock) va a la otra PC, que tiene un Postgres local
  descartable: PostgreSQL 17 en `D:\PostgreSQL`; `initdb` en
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
  - **La alerta del panel de recepción hace dos consultas por anotado** (B-07): `_alerta_de_socio()`
    y `estado_renovacion()` se llaman dentro del bucle de inscriptos, que es exactamente lo que el
    docstring de la alerta dice estar evitando —lo que se ahorró es la latencia de red de cada una,
    no la consulta—. Con veinte anotados son cuarenta consultas, y el panel se refresca cada diez
    segundos. El remedio ya está en el mismo archivo: `reservas_con_asistencia()` trae el conjunto
    en una consulta y la función pura lo recibe por parámetro.
  - **`deuda_total` de la búsqueda por DNI viaja siempre en cero** (B-07), y la ficha de Flet lo
    muestra. Es el mismo resto de la tabla `Deuda` que B-05 encontró en las dos apps.
  - **`crear_turno()` no valida que el profesor esté habilitado** (B-08, proceso 75), a diferencia de
    `crear_horario()`, que sí. La clave compuesta `fk_turno_profesor_habilitado` lo ataja igual, así
    que el resultado es un 500 sin mensaje en vez de un 409 explicado. Mismo patrón que el 500 de la
    baja del profesor, ya resuelto. Leído, no corrido.
  - **`puede_comprar()` promete reusar las condiciones de `comprar_plan()` y las tiene escritas dos
    veces** (B-08, proceso 73): la consulta de membresía, la comparación con hoy y `_sumar_un_mes()`
    aparecen en los dos. Lo que garantiza la promesa es que alguien se acuerde de tocar los dos. El
    molde de cómo hacerlo bien está al lado: `estado_renovacion()` en `renovacion.py`. Y hay un
    `motivo` inalcanzable —*"Tiene una deuda pendiente"*— detrás de un `if` que en ese punto ya sabe
    que la cuota está al día.
  - **Dar de baja una actividad no resuelve los abonos vigentes de esa actividad** (B-08, proceso
    87): cancela sus turnos futuros y las reservas, pero la inscripción sigue ACTIVA hasta su fecha.
    Es coherente con no reembolsar en silencio, y a la vez deja al mostrador sin ningún aviso de que
    ese abono hay que resolverlo. No está anotado en el código.
  - **El rechazo de la clase suelta cuando el turno está completo es la única decisión del módulo de
    Actividades sin su porqué escrito** (B-08, proceso 78): `reservar()` manda a lista de espera y la
    clase suelta responde 409. La asimetría tiene sentido —se está cobrando— pero no está argumentada.
  - **`listar_reservas()` nombra un usuario que no puede usarlo** (B-08, proceso 80): el docstring
    dice *"es la lista que usa el profesor"* y pide la sección Actividades, que el Profesor tiene en
    NINGUNO. Y devuelve sólo las RESERVADA, así que desde ahí no se ve quién está en lista de espera.
  - **El `ilike` del nombre de una actividad acepta comodines** (B-08, proceso 61): `Yoga_suave`
    choca con `YogaXsuave`. Es el mismo defecto que B-05 corrió en el nombre de un plan de membresía.
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
  - **`Rutina.id_entrenador` NO es NOT NULL, y cinco comentarios dicen que sí** (B-09): es nullable
    a propósito desde que existen las rutinas propias del socio, y la frase *"es NOT NULL"* quedó en
    `rutinas.py`, `schemas.py`, `RutinaFormModal.tsx`, `Flet/.../views/rutinas.py` y
    `Flet/.../state.py`. La regla que justifica —el Dueño tiene que elegir un entrenador— sigue
    siendo correcta por otro motivo: una rutina del catálogo sin entrenador sería indistinguible de
    una propia de un socio y, por lo tanto, invisible para quien la acaba de crear.
  - **El `db.flush()` de `asignar_rutina()` no hace falta y su comentario dice lo contrario de lo que
    pasa** (B-09, proceso 95; **corrido**). Doce líneas afirman que SQLAlchemy emite los `INSERT`
    antes que los `UPDATE`: emite los `UPDATE` primero (`persistence.py`, `save_obj()`), y la misma
    función con esa línea borrada reasigna igual de bien contra un índice único parcial. Es un viaje
    a São Paulo —44 ms— en cada asignación, que no evita nada. El precedente que cita,
    `promover_de_lista_de_espera()`, SÍ lo necesita, porque ahí lo que sigue al `flush` es una
    **lectura**. Pariente del mismo tipo: el `db.expire(rutina, ["ejercicios"])` de `editar_rutina()`
    tampoco hace falta, porque la sesión usa `expire_on_commit` por defecto (corrido con y sin).
  - **Los seis listados de Rutinas y Nutrición son N+1, y está medido** (B-09, B-10): el catálogo
    cuesta **2 + N + 3·P** consultas, con `N` plantillas y `P` profesionales distintos entre ellas —11
    para 6 rutinas del mismo entrenador, **26** si cada una tiene el suyo—, así que **el costo depende
    de los datos**: lo que ahorra hoy es el mapa de identidad de la sesión, no una carga anticipada. El
    detalle cuesta una consulta por ejercicio (y en Nutrición una por comida, para traerle el plato), y
    el historial de un socio pide por fila una `Rutina`/`Dieta` que su propio `JOIN` ya trajo —el `JOIN`
    está para el `WHERE`, no llena la relación—. Es el mismo `selectinload` que falta en el feed de
    ingresos de B-06.
  - **El docstring de `editar_dieta()` dice que nada apunta a `Comida`, y algo apunta** (B-10, proceso
    104; **corrido**). `Registro_Comida.id_comida` es una FK a `Comida`, así que antes de borrar las
    comidas viejas el endpoint tiene que ponerla en `NULL` —y lo hace, en cuatro líneas bien
    comentadas—, pero el docstring de arriba afirma lo contrario porque se copió de `editar_rutina`,
    donde la frase sí es verdad. Corrido con `PRAGMA foreign_keys=ON`: tal cual está anda y el registro
    conserva su texto y sus macros; sin esas líneas la FK lo frena con un 500; y **sin ningún registro
    cargado pasa igual**, que es por qué un defecto así puede vivir mucho tiempo. Lo que no está anotado
    en ningún lado es la consecuencia de producto: el registro desvinculado **pierde contra qué comida se
    comparaba**, así que después de editar un plan no se puede reconstruir hacia atrás la comparación
    plan contra realidad.
  - **El `activo` de un plato del catálogo no se puede apagar desde ninguna app** (B-10, procesos 101 y
    102): `listar_catalogo_comidas()` filtra por ese flag y el alta lo pone en `True`, y no existe
    ningún endpoint que lo baje. Un plato cargado mal se queda en el catálogo para siempre, salvo
    editando la base. Mismo caso que los planes de membresía de B-05.
  - **`Asignacion_Dieta.observaciones` no lo manda ninguna app** (B-10, proceso 105): es la única
    columna que `Asignacion_Dieta` tiene y `Asignacion_Rutina` no, el endpoint la guarda, y las dos
    pantallas mandan sólo `id_socio`. Sólo se puede cargar por API.
  - **El `PUT` de dieta puede borrar en silencio, igual que el de rutina** (B-10, proceso 104):
    `objetivo`, `calorias_diarias` y `descripcion` tienen default `None` y se asignan sin preguntar — y
    uno de ellos es el objetivo calórico contra el que "Mi progreso" compara. Hoy inalcanzable (las dos
    apps mandan los cinco campos), igual que su gemelo.
  - **El comodín del `ilike` va por la cuarta copia** (B-10, proceso 102; corrido): `Pollo_arroz` choca
    con `PolloXarroz` en el catálogo de platos, como ya pasaba con el plan de membresía (B-05), la
    actividad (B-08) y el ejercicio (B-09). Es el mismo arreglo de una línea en cuatro archivos.
  - **Una comida con plato del catálogo Y descripción pierde la descripción sin aviso** (B-10, proceso
    99): `_agregar_comidas()` guarda `None` en `descripcion` cuando hay plato, que es correcto —el texto
    saldría del catálogo— pero el 422 del esquema sólo exige "al menos uno", no "exactamente uno".
  - **El historial de rutinas de un socio no lo llama ninguna pantalla** (B-09, proceso 90): la
    pregunta que contesta —*"¿qué viene entrenando?"*— es la de la ficha del socio. Tercer caso de la
    misma forma, con el historial de ingresos (B-06) y `GET /socios/entrenadores/{id}/socios` (B-02).
  - **Dos ejercicios en el mismo (día, orden) dan 500** (B-09, procesos 89 y 94; **corrido**):
    `Rutina_Ejercicio` tiene un índice único sobre `(id_rutina, dia, orden)` y `_validar_ejercicios()`
    sólo mira que cada ejercicio exista. Hoy sólo se alcanza por API, porque las dos apps derivan el
    `orden`. Mismo patrón que el 500 de `crear_turno()` de B-08.
  - **El `PUT` de rutina todavía puede borrar en silencio** (B-09, proceso 94): `objetivo` y
    `dias_por_semana` tienen default `None` y el endpoint los asigna sin preguntar, o sea el problema
    que se arregló en el `PUT` de socio y en el de empleado con `model_fields_set`. Hoy inalcanzable
    —las dos apps mandan siempre los cuatro campos—; lo hereda cualquier cliente nuevo.
  - **Menores de B-09:** el nombre de un ejercicio se compara con `ilike` y el `_` hace de comodín
    (corrido: `Press_banca` choca con `PressXbanca`), que es la **tercera** copia del mismo defecto
    después del plan de membresía (B-05) y la actividad (B-08); `AsignarRutinaRequest` acepta
    `fecha_fin` sin compararla con `fecha_inicio` y ninguna pantalla la manda; el comentario de la PWA
    dice *"Sólo el Entrenador gestiona rutinas"* y la acción la tienen también el Dueño y el
    Recepcionista; y en el archivo de procesos los títulos **96 y 97 son su propia ruta** en vez de un
    nombre (el nombre está adentro de la línea DFD, y es el que usa el capítulo).
  - **Flet quedó atrás de la PWA en Rutinas** (B-09): no tiene el botón de **ver** el catálogo de
    ejercicios —que en la PWA va antes que el de agregar, justamente para no cargar dos veces el mismo
    ejercicio—, no tiene buscador ni chips por días por semana, y la baja y la reactivación viven
    adentro del diálogo de detalle en vez de la tarjeta. Además `get_rutinas()` arma una clave
    `duracion` que ninguna vista lee, y `_numero()` acepta `nan` en el peso donde la PWA lo rechaza
    con `Number.isFinite` (corrido).
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
