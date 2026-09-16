# OlimpOS — Estado actual

**Foto al 2026-09-16.** Sólo el presente: dónde estamos, qué falta y qué no se
probó. Lo permanente (idea, reglas del negocio, trampas) está en `CLAUDE.md`, y el
historial en git. **Al cerrar algo, se actualiza el punto, no se agrega una tanda.**

---

## Dónde estamos parados

- **Etapa:** las dos apps están completas y conectadas a la API real. El dueño las
  prueba **rol por rol en la PWA** y anota en `A CORREGIR PWA .txt`. Cada arreglo se
  hace en la PWA y se replica en Flet.
- **Probado y resuelto:** todo el rol Dueño (Socios, Cobros, Asistencia, Personal,
  Rutinas, Nutrición, Actividades, Usuarios y Dashboard).
- **Abierto:** la sección **"OBSERVACIONES NUEVAS 2.0"** del `.txt` (Recepcionista,
  Profesor y Socio). **No se empezó.** Resumen en "Lo que falta".
- **Base de datos: tiene los datos que el dueño cargó a mano** desde el estado de
  ENTREGA. **No vaciar ni recargar.** Cuentas hoy: `dueno`, `mario.dj`
  (recepcionista), `dami.silberstein` (profesor, todavía con la contraseña temporal)
  y `franco.distillio` (socio). Las contraseñas están en el `.txt` de contraseñas.
- **Consecuencias para verificar:** las suites no se pueden correr (necesitan la base
  vacía). `pruebas_vistas.py` sólo entra con las cuentas que existan.
- **Backend:** 124 rutas en `/openapi.json`; si da menos, está respondiendo un
  proceso viejo. `check_permisos`: las tres copias coinciden (6 roles).

---

## Lo que falta, en orden

### 1. Lista 2.0 del dueño (`A CORREGIR PWA .txt`, leer el texto completo)

**Lo que el dueño marcó como lo más importante:**
- **Turnos y reservas visibles para todos los roles.** Hoy sólo el socio los ve. El
  personal no tiene dónde ver quién reservó qué horario.
- **El Recepcionista tiene que poder gestionar Actividades** igual que el Dueño (toca
  la matriz de permisos: las tres copias).
- **Profesor, "Mis clases" vacío:** `dami.silberstein` está asignado a una actividad y
  hay un socio con clase suelta comprada, pero no ve nada. Probablemente no hay
  `Turno` generado con su `id_profesor`: investigar.
- **Socio, "Mis turnos" vacío** después de comprar la clase suelta. Tampoco le aparece
  el turno para anotarse.

**Recepcionista, Dashboard:**
- Mostrar primero los turnos próximos.
- Que vea los cobros en "Actividad reciente".
- Dueño y Recepcionista: mostrar entre paréntesis qué se pagó al lado del monto.

**Socio:**
- **Error 500 al guardar la rutina propia.** La dieta propia sí guarda.
- **Fecha de nacimiento y domicilio:** que se carguen en el alta de socio (Dueño y
  Recepcionista), no al cobrar. El socio no los edita.
- **Los modales del catálogo de ejercicios, de "Armar mi rutina", de "Armar mi dieta"
  y de "Cargar mi plato" ocupan todo el ancho:** tienen que ser una ventana chica como
  las demás, para todos los roles.
- **"Mi progreso":** mostrar si cada día se cumplió el objetivo de la dieta, que sea
  lindo e intuitivo.
- **"Mi progreso":** el campo de masa muscular por día no tiene sentido (nadie se hace
  un estudio diario). Repensarlo.
- **Pregunta sin contestar:** en "Mi cuota", ¿cuándo aparece el saldo como pendiente?
- **Revisar al final:** en algún momento "Mi cuota" mostró un valor de plan
  equivocado. Ahora está bien.

**General:**
- **Contacto de emergencia del socio:** Dueño y Recepcionista tienen que poder
  llamarlo.
- **Teléfonos:** ¿hace falta el código de país para extranjeros? Si se agrega, va en
  **todos** los campos de teléfono. Es una pregunta del dueño: proponer antes de
  hacer.

### 2. Decidido y sin implementar
- **Borrar una cuenta de acceso** (no a la persona). El dueño eligió "sólo la cuenta":
  se borra la fila de `Usuario`, la persona y su historial quedan, y lo que apunte a
  esa cuenta (por ejemplo `Asistencia.id_registrado_por`) pasa a NULL. Revisar todas
  las FK a `Usuario` antes de codear. Hoy Usuarios sólo da de baja o de alta.

### 3. Hecho pero sin probar en pantalla
- Alta de socio con "Cobrar ahora" (Cobros tiene que abrir con el socio ya elegido),
  en las dos apps.
- Que el Recepcionista **no** vea el gráfico ni la métrica de ingresos.
- El chip "2º de hoy" fichando dos veces al mismo socio (ojo: fichar acredita
  reservas).
- El aviso de cuenta trabada en el login y en el cambio de contraseña (PWA y Flet).

### 4. Menores
- **Profesores homónimos:** dos con el mismo nombre se ven idénticos al asignarlos a
  una actividad. Mostrar DNI o legajo.
- **Flet, Profesor:** al entrar no tiene secciones y cae en una pantalla sin acceso.
  Falta un mensaje que diga que su pantalla está en la PWA.
- **Flet, detalle de un plan de nutrición:** no cierra tocando afuera (en la PWA sí).
  El `modal=True` es global a los diálogos, así que hay que resolverlo con cuidado.
- **Contador de repeticiones:** rediseñar el overlay (las líneas verdes del esqueleto
  son sólo para afinar) y seguir ajustando umbrales probando en el celular.

### 5. Grandes, después de la lista
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
