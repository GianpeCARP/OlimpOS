# OlimpOS — Estado actual

**Foto al 2026-09-17.** Sólo el presente: dónde estamos, qué falta y qué no se
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
- **Consecuencias para verificar:** las suites no se pueden correr (necesitan la base
  vacía). `pruebas_vistas.py` sólo entra con las cuentas que existan.
- **Backend:** 130 rutas en `/openapi.json`; si da menos, está respondiendo un
  proceso viejo. `check_permisos`: las tres copias coinciden (6 roles).

---

## Lo que falta, en orden

### 1. Hecho pero sin probar en pantalla
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
  cuota vigente. Probado por API (rechazos 409 y los tres casos de la regla).
- **Baja programada** (backend, PWA y Flet): con la cuota paga la baja corre desde el
  día siguiente al vencimiento, se ve "Baja el dd/mm" en la grilla de Socios y en Mi
  cuota, y se puede anular. Probado a nivel base (programar, bloqueo de renovación y
  aplicación al llegar la fecha) en una transacción descartada; falta en pantalla.
  El personal también puede **dar de baja ahora** (al vencer o ahora en el modal de la
  PWA, casilla en Flet; con una baja programada, la adelanta). Probado llamando al
  endpoint en una transacción descartada.
- **Borrar una cuenta de acceso** (`DELETE /usuarios/{id}`, PWA y Flet): borra sólo la
  cuenta; la persona y su historial quedan y se le puede crear otra.
  `Asistencia.id_registrado_por` pasa a NULL. Nadie borra la propia, sólo un Dueño
  borra la de un Dueño y nunca la última. Compila en las tres capas; sin probar.
- **Los 4 menores de la tanda** (backend, PWA y Flet):
  **Homónimos:** `ProfesorActividadOut` suma `dni` y `legajo`, y la asignación y el
  selector del horario muestran "Legajo X" (o el DNI si no tiene). Verificado por API.
  **Profesor en Flet:** entraba y caía en el Dashboard que no puede ver, porque
  `primera_seccion()` da None y el fallback lo mandaba igual; ahora le sale
  `SinSeccionesView` diciéndole que su pantalla está en la PWA.
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
- **Teléfonos con código de país** en los 6 campos de la PWA y los 4 de Flet (alta y
  edición de socio y empleado, contacto de emergencia, agregar teléfono, Mi perfil).
  En Flet, editar un empleado ya precarga el teléfono (antes guardar lo borraba).
- **Mi cuota**: se sacaron "Saldo pendiente" y el bloque de deudas (la tabla Deuda no
  existe, siempre daban 0); ahora avisa "cuota vencida" y muestra el último pago.
- Ventanas de catálogo de ejercicios, armar rutina, armar dieta y registrar comida:
  pantalla completa en el celular, ventana centrada desde tablet.
- Alta de socio con "Cobrar ahora"; el chip "2º de hoy" (ojo: fichar acredita
  reservas); el aviso de cuenta trabada en login y cambio de contraseña.

### 2. Menores
- **Contador de repeticiones** (el único que el dueño dejó afuera de la tanda):
  rediseñar el overlay (las líneas verdes del esqueleto son sólo para afinar) y
  seguir ajustando umbrales probando en el celular.

### 3. Grandes, después de la lista
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
