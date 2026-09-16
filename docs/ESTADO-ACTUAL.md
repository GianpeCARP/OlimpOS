# OlimpOS — Estado actual

**Foto al 2026-09-16.** Sólo el presente: dónde estamos, qué falta y qué no se
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
- **Backend:** 124 rutas en `/openapi.json`; si da menos, está respondiendo un
  proceso viejo. `check_permisos`: las tres copias coinciden (6 roles).

---

## Lo que falta, en orden

### 1. Decidido y sin implementar
- **Borrar una cuenta de acceso** (no a la persona). El dueño eligió "sólo la cuenta":
  se borra la fila de `Usuario`, la persona y su historial quedan, y lo que apunte a
  esa cuenta (por ejemplo `Asistencia.id_registrado_por`) pasa a NULL. Revisar todas
  las FK a `Usuario` antes de codear. Hoy Usuarios sólo da de baja o de alta.

### 2. Hecho pero sin probar en pantalla
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
  **No hay forma de dar de baja YA a alguien con la cuota paga** (una expulsión): si
  hace falta, sumar un "dar de baja ahora" en el diálogo del personal.
- **Teléfonos con código de país** en los 6 campos de la PWA y los 4 de Flet (alta y
  edición de socio y empleado, contacto de emergencia, agregar teléfono, Mi perfil).
  En Flet, editar un empleado ya precarga el teléfono (antes guardar lo borraba).
- **Mi cuota**: se sacaron "Saldo pendiente" y el bloque de deudas (la tabla Deuda no
  existe, siempre daban 0); ahora avisa "cuota vencida" y muestra el último pago.
- Ventanas de catálogo de ejercicios, armar rutina, armar dieta y registrar comida:
  pantalla completa en el celular, ventana centrada desde tablet.
- Alta de socio con "Cobrar ahora"; el chip "2º de hoy" (ojo: fichar acredita
  reservas); el aviso de cuenta trabada en login y cambio de contraseña.

### 3. Menores
- **Profesores homónimos:** dos con el mismo nombre se ven idénticos al asignarlos a
  una actividad. Mostrar DNI o legajo.
- **Flet, Profesor:** al entrar no tiene secciones y cae en una pantalla sin acceso.
  Falta un mensaje que diga que su pantalla está en la PWA.
- **Horario sin profesor:** no hay forma de asignarle o cambiarle el profesor a un
  horario ya creado (hay que darlo de baja y crearlo de nuevo).
- **Flet, detalle de un plan de nutrición:** no cierra tocando afuera (en la PWA sí).
  El `modal=True` es global a los diálogos, así que hay que resolverlo con cuidado.
- **Contador de repeticiones:** rediseñar el overlay (las líneas verdes del esqueleto
  son sólo para afinar) y seguir ajustando umbrales probando en el celular.

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
