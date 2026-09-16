# OlimpOS — Estado actual y próximos pasos

**Última actualización: 2026-09-15.** Este archivo es el "arranque rápido": cómo
funciona el negocio, cómo estamos trabajando, qué está hecho HOY, qué falta, y las
decisiones que no se deducen del código. Es el equivalente versionado de la memoria
de Claude Code (que es local a cada máquina y NO viaja con el repo). Si arrancás en
otra computadora —o después de un `/clear`— leé esto + `CLAUDE.md` y ya sabés dónde
estamos, sin que nadie tenga que volver a explicarlo.

### Índice

| Dónde | Qué contesta |
|---|---|
| **[Cómo se maneja el negocio](#cómo-se-maneja-el-negocio)** (acá) | Cómo funciona el gimnasio: quién cobra qué y por qué, cuándo un socio está "vencido", qué decide una persona y qué decide el sistema. **Leer esto antes de proponer cambios de producto.** |
| **[Cómo estamos trabajando](#cómo-estamos-trabajando)** (acá) | El método actual (el dueño prueba panel por panel y anota hallazgos), las reglas vigentes de la sesión y qué NO hay que hacer. |
| **[Lo que YA está hecho](#lo-que-ya-está-hecho-y-dónde-vive)** (acá) | Features terminadas y en qué archivo vive cada una. |
| **[Lo que FALTA](#lo-que-falta--próximos-pasos)** (acá) | Próximos pasos, empezando por el coach con IA. |
| **`CLAUDE.md`** (raíz) | Contexto técnico permanente: stack, paleta, performance, trampas de Flet/PWA, reglas de git, estados de la base, comandos de verificación. |
| **`docs/RESUMEN-PARA-CLAUDE-CODE.md`** | Por qué el esquema es como es (reset a 41 tablas). |
| **`docs/olimpos_schema_actual.dbml`** | El esquema de hoy, para abrir en dbdiagram. Verificado contra Neon y contra `db/schema.sql`. |

---

## Cómo se maneja el negocio

Las reglas de abajo son **decisiones del dueño del gimnasio**, no detalles de
implementación. Varias parecen bugs si no se conocen, y ya se discutieron: antes de
"arreglar" alguna, leerla acá.

### El dinero es prepago, y "deber" no se guarda

- **No existe una tabla `Deuda`.** El sistema es prepago puro: se paga y se activa una
  membresía con fecha de vencimiento. Que alguien "deba" es simplemente **no tener
  membresía vigente**, y se deriva en el momento.
- **El estado del socio tampoco se guarda**: se calcula cada vez (`_estado_socio` en
  `routers/socios.py`, espejado en `membresiaService.ts`). El orden importa y es este:
  1. Si está dado de baja → **De baja** (gana sobre todo: alguien de baja con la cuota
     paga sigue estando de baja).
  2. Sin ninguna membresía → **Sin membresía**.
  3. Membresía `SUSPENDIDA` → **Suspendido**. `VENCIDA` o `CANCELADA` → **Vencido**.
  4. Activa, mirando los días hasta el vencimiento: negativo → **Vencido**; de 0 a 7 →
     **Por vencer**; más de 7 → **Activo**.
- O sea: **un socio queda "vencido" al día siguiente de su fecha de vencimiento**, y los
  7 días previos aparece como "Por vencer" para que el mostrador lo llame antes
  (`DIAS_AVISO_VENCIMIENTO = 7`, el mismo valor en tres lugares).

### Quién cobra, y por qué existe la caja si el socio paga solo

El socio paga desde su celular (transferencia, tarjeta, billetera). **El panel de Cobros
no existe para duplicar eso**, existe para los cuatro casos que la app no cubre:

1. **Efectivo** — el único método que no tiene otra vía.
2. El socio que **no usa la app** (y los hay).
3. El pago que **entró por fuera** y hay que registrar para que la membresía se active.
4. **Corregir** un cobro mal cargado.

Lo mismo vale para vender una **clase suelta** desde el mostrador: tiene sentido en
efectivo o para quien no usa la app; el resto lo hace el socio desde su perfil.

### Métodos de pago: describen cómo paga la persona, no el proveedor

El enum es `EFECTIVO / DEBITO / CREDITO / TRANSFERENCIA / BILLETERA_VIRTUAL`.

- **`BILLETERA_VIRTUAL` no es lo mismo que `TRANSFERENCIA`**, aunque las dos "lleguen
  por internet": una transferencia bancaria se concilia en el resumen del banco y una
  billetera en el panel de la billetera. Son dos lugares distintos donde buscar la plata.
- El pago online del socio se guarda como `BILLETERA_VIRTUAL` **a propósito**, y no se
  agregó un valor "MERCADO_PAGO": el enum describe **cómo paga la persona**, no con qué
  pasarela lo procesamos. Si mañana se cambia de proveedor, el método del socio es el mismo.

### Promociones

- Son **sólo porcentuales** y viven en el **`Pago`** (`id_promocion` + `monto_descuento`),
  no en la membresía: el descuento es un hecho de ESE cobro.
- **Tienen que estar vigentes el día en que arranca el período que se cobra, no hoy.**
  Renovando por adelantado, el período nuevo empieza al día siguiente del vencimiento
  actual: aplicar una promo que para entonces ya no existe es regalar plata de un mes en
  el que la promoción no corre.
- Permisos repartidos a propósito: **listar** pide la sección Cobros (para poder elegir
  una al cobrar), pero **crear/editar/dar de baja** pide `gestionPromociones`, que sólo
  tiene el Dueño.

### Asistencia: el sistema informa, no juzga

- Alguien con deuda o cuota vencida **ficha igual** y la respuesta trae una advertencia.
  Dejar a una persona afuera del gimnasio lo decide alguien en el mostrador mirando el
  caso, no un torniquete. Además, si no se registrara, el gimnasio perdería el dato de
  que esa persona estuvo.
- **No hay tope de ingresos por día**, y el repetido tampoco se pregunta: se registra y
  se marca. Cada fichaje trae `ingreso_numero` (1 el primero del día, 2 y 3 los
  repetidos) y la lista muestra un chip "2º de hoy" al lado del nombre, en las dos apps.
  Hubo un tope de un ingreso diario y un anti-duplicado de 5 minutos, los dos con
  confirmación del mostrador: se sacaron porque **quien atiende no lee el cartel** —con
  gente en la cola lo acepta sin mirarlo, o deja al socio parado en la puerta mientras
  descifra qué le pregunta la pantalla—. Frenar a alguien con la cuota paga porque el
  sistema cree que ya entró es lo mismo que frenarlo por deber: el sistema informa, no
  juzga. El conteo del día sigue siendo interpretable porque el dato está — son pases, y
  `ingreso_numero > 1` dice cuáles son repetidos.
- **Desfichar** (borrar un ingreso) existe para el ingreso que no ocurrió —alguien que
  fichó por otro, o el socio equivocado— y **sólo sobre los de hoy**: corregir el error
  del momento es trabajo de mostrador; reescribir la asistencia de la semana pasada, no.
- **El fichaje con tarjeta va a existir, pero como aparato físico.** Lo que se retiró de
  las dos apps fue el *campo de texto* para tipear el código, que no era un lector: un
  RFID de verdad es un sensor en la puerta que lee la tarjeta y le pega solo al sistema.
  Está **pendiente de comprar el lector** (ver "Lo que FALTA"), así que hoy no hay forma
  de fichar con tarjeta. Los ingresos históricos con `metodo_registro='RFID'` siguen en
  la base y las listas los distinguen por el ícono.

### Historial médico: por qué hay un catálogo

- El catálogo compartido existe para que **"qué socios tienen asma" sea una consulta** y
  no leer observaciones a mano. Con texto libre convivirían "Asma", "asma" y "ASMA".
- Por eso son dos cosas y conviven: el **nombre** sale del catálogo y dice QUÉ tiene; las
  **observaciones** son por socio y dicen QUÉ HACER ("rodilla derecha", "evitar impacto").
- **El Recepcionista NO lo ve**, y es la única acción donde queda por debajo del
  Entrenador. El botón se **omite**, no se deshabilita: uno gris que no responde igual
  delataría que el socio tiene algo cargado.
- La fecha de diagnóstico **no puede ser futura**.

### Personas, contacto y accesos

- **No hay "Registrarse".** Sólo entra quien el gimnasio da de alta: se cargan los datos,
  el sistema genera una contraseña temporal que nadie eligió, se le entrega, y en el
  primer ingreso la persona define la suya. El control de quién entra lo tiene siempre la
  administración.
- **Un empleado necesita mail o teléfono** (al menos uno): un empleado al que nadie sabe
  cómo contactar no sirve. Desde el alta se le pueden mandar las credenciales por mail o
  WhatsApp con el mensaje ya escrito, en vez de copiar la contraseña a mano.
- **El botón de mail abre el redactor de GMAIL, no el programa de correo de la máquina**,
  y parece un bug si no se sabe. Antes era un `mailto:`, que necesita un cliente de correo
  asociado en esa PC — y las del gimnasio no lo tienen, así que el botón no hacía nada.
  (Peor: en la ficha de personal iba con `target="_blank"` y dejaba una pestaña muerta
  mostrando el "mailto:…".) El precio de la decisión es que ata el botón a Gmail: hay que
  estar logueado en Google en ese navegador. Vive en `utils/contacto.ts` y su gemelo
  `app/contacto.py`; WhatsApp no cambió.
- **Un socio tiene VARIOS teléfonos** (celular, casa, trabajo) con **uno principal**, que
  es el que muestra la ficha y al que se llama primero. La tabla siempre fue así.
- **Las bajas son lógicas y reversibles** (socios y empleados): la fila queda con su
  historial de pagos y asistencias, y siempre existe el camino de vuelta.

### Entrenamiento

- Un socio puede tener **varios entrenadores a la vez** (uno de musculación y otro de
  funcional es normal, no un error de datos) y las asignaciones finalizadas quedan como
  historial.
- **Quién entrena a quién lo deciden el Dueño y el Recepcionista**, no el Entrenador. Él
  ve la lista sin controles.
- **Un Entrenador sólo toca SUS rutinas**, y un Nutricionista sus dietas.
- El socio puede además **armarse su propia rutina y su propia dieta** sin entrenador, y
  eso es **invisible para el personal** (ver más abajo).

### Actividades

- **Clase suelta = un `Plan_Actividad` con `tipo_limite=CLASE_SUELTA`**, no una columna de
  precio en la actividad.
- Las **clases restantes no se guardan**: se cuentan las `Reserva`. Cancelar libera la
  clase por el simple hecho de dejar de contar.

---

## Cómo estamos trabajando

**El método actual (2026-09-15):** el dueño está **probando el sistema panel por panel
con cuentas reales**, empezando por el rol Dueño, y anota los hallazgos en
`A CORREGIR PWA .txt` (en la raíz). Yo los arreglo en el orden del archivo y **replico
cada arreglo en Flet**, porque casi todo lo que aparece probando la PWA aplica igual allá.

Reglas vigentes mientras dure esta etapa:

- **NO vaciar ni recargar la base.** Está en modo DEMO y el dueño tiene datos de prueba
  a medio hacer. Nada de `vaciar_base.py --si` ni `escenario_demo.py` sin que lo pida.
  Si hace falta probar un endpoint contra la base real, el script tiene que **restaurar
  lo que tocó** (hay un ejemplo de eso en la tanda de teléfonos).
- **La PWA es la referencia y Flet la copia.** Si las dos difieren, la que está bien es
  la PWA — salvo Recepción, que no tiene gemela.
- **No commitear por cuenta propia.** El dueño decide qué entra. Cuando pida commitear:
  rutas explícitas, **nunca `git add -A`**.
- **Toda cuenta nueva se anota** en `backend/CONTRASEÑAS PARA TESTEO Y ACTUALIZADAS.txt`:
  la contraseña temporal se muestra UNA sola vez.
- **Reiniciar el backend después de tocar rutas.** El `uvicorn` no corre con `--reload`:
  si agregás un endpoint y no reiniciás, la API vieja sigue atendiendo y parece que el
  código no funciona. Se verifica mirando las rutas registradas en `/openapi.json`.

**Estado de la lista:** `A CORREGIR PWA .txt` está **terminado hasta donde llega el
texto** (paneles Socio, Cobros, Asistencia y Personal del rol Dueño). Faltan los paneles
que el dueño todavía no probó.

---

## Lo que YA está hecho (y dónde vive)

### 1. Contador de repeticiones con cámara (PWA, sólo celular)
- Pose con **MediaPipe BlazePose** (`@mediapipe/tasks-vision`) corriendo ENTERO en
  el dispositivo (el video nunca sale del teléfono). Modelo + WASM **bundleados**
  en `Proyecto - PWA/src/frontend/public/mediapipe/` (no CDN; ~40MB en el repo).
- Lógica pura en `views/socio/logicaReps.ts`: 15 movimientos, ángulos 3D, máquina
  de estados con histéresis, filtro One-Euro, medición de **ambos lados** del
  cuerpo, gracia al empezar + anti-rebote. Componente `views/socio/ContadorReps.tsx`.
- **Objetivo de reps + pitido**: el socio dice cuántas quiere y el celu pita al llegar.
- Elegir el ejercicio del **catálogo** (modo suelto) → agrupado por músculo, con buscador.
- Guarda la serie (con peso) en `Registro_Ejercicio`, **offline-first**: cuenta sin
  internet y encola el guardado (`utils/colaRegistros.ts`), reintenta al reconectar.
- Se ofrece sólo en celular (`utils/dispositivo.ts`) y como MODO (no ruta) de Mi rutina
  y del circuito.
- **PENDIENTE (#4):** rediseñar el overlay para producción (las "líneas verdes" del
  esqueleto son feas para el producto final; se dejan mientras se afina el tracking).
- **PENDIENTE:** seguir afinando umbrales de algunos movimientos probando en el celu.

### 2. Rutina propia del socio (sin entrenador)
- `Rutina.id_entrenador` es **NULLABLE**: `NULL` = rutina propia. El dueño se DERIVA
  de `Asignacion_Rutina` (no hay columna nueva). Espejo en `models.py` + `db/schema.sql`.
- **Invisible para el staff**: helper `_rutina_del_staff` en `routers/rutinas.py`
  devuelve 404 a las propias; listar/obtener/asignar/editar/baja las excluyen; el
  historial del staff también.
- Endpoints self-scoped en `routers/portal.py`: `POST/DELETE /portal/mi-rutina/propia`
  (autoasignada; 409 si hay rutina del entrenador; reemplaza la propia anterior),
  `GET /portal/mi-rutina/ejercicios` (catálogo). Campo `es_propia` en la respuesta.
- Frontend: `views/socio/ArmarMiRutina.tsx` + integración en `MiRutinaView.tsx`.
- Suite: `backend/pruebas/test_rutina_propia.py`.

### 3. Dieta propia + registro de comida
- **Espejo de la rutina propia**: `Dieta.id_nutricionista` NULLABLE (`NULL` = dieta
  propia), invisible para el staff (`_dieta_del_staff` en `routers/nutricion.py`),
  la del nutricionista tiene precedencia (409). `POST/DELETE /portal/mi-dieta/propia`.
- Las comidas del plan propio son de **texto libre** (`Comida.descripcion`), porque
  `Comida.id_catalogo_comida` ahora es nullable y el catálogo del gimnasio suele
  estar vacío. Frontend: `views/socio/ArmarMiDieta.tsx`.
- **Registrar comida** (`Registro_Comida`): `GET/POST /portal/mi-dieta/comidas`. Texto
  obligatorio; macros (kcal/proteínas/carbos/grasas) y momento **opcionales, a mano**.
  Frontend: `views/socio/RegistrarComida.tsx`. La IA los va a poder autocompletar
  (ver coach IA), pero NO es obligatorio.
- Suite: `backend/pruebas/test_dieta_propia.py`.

### 4. Tablero de progreso (Mi progreso)
- `views/socio/MiProgresoView.tsx` (ya tenía el peso corporal) + `views/socio/ProgresoExtra.tsx`
  con dos secciones nuevas: **Nutrición** (kcal/proteína promedio + barras por día) y
  **Fuerza** (sparkline del peso levantado por ejercicio + delta). Gráficos hand-rolled,
  **sin librería** (decisión del proyecto: 40kB no se justifican).
- Backend: `GET /portal/mi-rutina/registro-ejercicio`.

### 5. Videos de técnica
- El entrenador carga el **link de YouTube** del canal del gimnasio al crear un ejercicio
  (PWA "+ Ejercicio" y Flet "Nuevo Ejercicio"). Nunca toca el servidor.
- `backend/demonio_videos.py` (yt-dlp + ffmpeg) baja cada link que no tenga archivo a
  `VIDEOS_DIR` (vacío = `/videos` en la raíz), y descarta links de otro canal
  (`VIDEOS_CANAL_YOUTUBE`, hoy `@JulienLEPRETRE` para probar). Se arranca con
  `backend/iniciar_demonio_videos.cmd` (acceso directo en `shell:startup`); log en `backend/logs/`.
- El archivo se llama `<id de youtube>.mp4`: "ya bajado" = el archivo existe, sin columnas nuevas.
  El backend sirve la carpeta en `/videos` y agrega `video_local` a los ejercicios (None hasta
  que el demonio lo baja). Los navegadores no reproducen ftp://: por eso va por HTTP.
- Socio: botón **"Ver técnica"** en Mi rutina, en el circuito y en el catálogo.
- Pendiente para el final: videos institucionales en la tele (mismo demonio, otra carpeta).

### 6. Rutinas completas del personal (PWA y Flet)
- Alta/edición **con ejercicios del catálogo por día** (series, reps, peso, descanso,
  observaciones, orden), detalle con la planilla, asignar a un socio, baja/reactivación.
  `PUT /rutinas/{id}` con `ejercicios` REEMPLAZA la planilla (nada apunta a Rutina_Ejercicio).
- Editor compartido en la PWA: `views/rutinas/EditorEjercicios.tsx` + `planillaEjercicios.ts`,
  que usan también `ArmarMiRutina` (socio) — varios días, peso, y "Rehacer" precargado.
- Socio: "Ejercicios del gimnasio" (`CatalogoEjercicios.tsx`), el catálogo para mirar suelto.
- "Comenzar entrenamiento" (circuito) **sólo en celular**, igual que el contador.

### 7. Nutrición completa (PWA y Flet) — commit `1028a21`
- **Comidas por día** dentro del plan, asignar el plan a un socio, y **catálogo de platos**
  (`Catalogo_Comida`) para no escribir el mismo plato distinto cada vez.
- `puede_editar` por nutricionista: cada uno toca lo suyo, igual que las rutinas.
- `PUT /nutricion/{id}` reemplaza las comidas; antes anula `Registro_Comida.id_comida`
  para no arrastrar filas que apuntan a comidas que dejaron de existir.

### 8. Permisos: la PWA es la referencia, Flet se iguala
- Un **Entrenador sólo toca SUS rutinas** (`puede_editar` en `RutinaOut`; 403 si no).
- El Entrenador **no asigna entrenadores** a socios: lo deciden Dueño y Recepcionista
  (UI oculta en las dos apps; el backend además le impide tocar asignaciones ajenas).
- Flet estaba con permisos "dados vuelta" (botones de gestión para roles de lectura) en Socios y
  Nutrición; se igualó a la PWA. Nutrición en Flet sumó editar/baja/reactivación y comidas reales.
- Quién usa qué: el Entrenador y el socio usan la **PWA**; Flet corre en la PC de **recepción**.
- La matriz vive en **tres** archivos (`backend/permisos.py`, `app/permisos.py`, `config.ts`) y
  `check_permisos.py` verifica que digan lo mismo. Si necesitás mostrar permisos en pantalla,
  **derivalos**; no los escribas a mano (ya apareció una cuarta copia mal hecha).

### 9. Tanda de correcciones del 2026-09-15 — commiteada (`3d4df15`)
Salió de `A CORREGIR PWA .txt`, probando como Dueño. Está verificada (`tsc`, `oxlint`,
`compileall`, `pruebas_vistas.py` y un smoke test de los endpoints nuevos) y **entró a git
el 2026-09-16** en el commit `3d4df15`, empujado a `origin/desarrollo` — junto con lo del
fichaje sin tope, porque varios archivos son los mismos y no se podían separar limpio.
Quedaron deliberadamente AFUERA del commit los dos archivos sueltos de la raíz
(`A CORREGIR PWA .txt` y `VIDEOS-DESCARGA-AUTOMATICA.md`): siguen sin trackear.

- **Teléfonos múltiples del socio** — `GET/POST/PUT/DELETE /socios/{id}/telefonos`, más el
  botón de teléfono en cada fila de la grilla, en las dos apps. Detecta el mismo número
  escrito distinto, el primero queda principal solo, y si borrás el principal asciende otro.
  Van por endpoints propios y **no** como un campo más del PUT de la ficha: agregar un
  número no es editar la ficha entera.
- **Promoción vencida al renovar** — se valida contra el inicio del período nuevo.
- **Asistencia** — se retiró el fichaje con tarjeta y se agregó deshacer. El tope de un
  ingreso por día con confirmación del mostrador se agregó y **se volvió a sacar el
  2026-09-16** (ver arriba): quedó el chip con el número de ingreso del día.
- **Personal** — el teléfono vuelve en el listado (por eso al reeditar salía vacío y
  guardar lo borraba), "Contactar" abre mail o WhatsApp, contacto obligatorio, y el alta
  ofrece mandar las credenciales en vez de que alguien las copie a mano.
- **Validaciones** — teléfono sin letras (filtrado mientras se tipea, en las dos apps),
  email con dominio real y normalizado a minúsculas, fecha de diagnóstico no futura
  (backend + tope en los cuatro campos de fecha).
- **Un 500 real**: reasignar un entrenador que ya lo había sido el mismo día chocaba con
  el único `(id_socio, id_entrenador, fecha_inicio)`; ahora reactiva la asignación.
- **`ConfirmDialog` a `z-[70]`**: los paneles son `z-50` y se montan después, así que el
  cartel de confirmación quedaba detrás de la ficha.
- **Sin probar de punta a punta**: el chip del ingreso repetido sólo se ejercitó por el
  camino que no escribe. **Fichar acredita reservas y eso no se revierte borrando la
  asistencia**, así que no se ficharon socios reales; conviene probarlo en pantalla.

---

### 10. El Profesor tiene cuenta y ve sus clases — 2026-09-16, commiteado en `desarrollo`

Antes no la tenía, y estaba escrito en seis lugares como decisión ("da clases, no
usa el sistema"). El efecto real era que el profesor se enteraba de su horario por
WhatsApp y, para saber quién se había anotado, tenía que preguntarle al mostrador.
El endpoint que lista los inscriptos existía desde siempre —su docstring dice "es la
lista que usa el profesor"— y no lo llamaba ninguna pantalla.

- **No tocó la base.** Cero DDL: el rol se DERIVA del subtipo (`Usuario` no tiene
  columna de rol, y la tabla `Profesor` ya existía). Todo fue código de aplicación.
- `Rol.PROFESOR` en `models.py` + `roles_de_persona()`; el alta de `personal.py` ya
  no lo saltea (se eliminó `ROLES_SIN_SESION`).
- **`id_profesor` viaja firmado en el JWT**, igual que `id_socio` y por el mismo
  motivo: `/portal/mis-clases` filtra por él y no acepta ningún id por parámetro,
  así que un profesor no puede ver las clases de otro.
- **Es un rol de PANTALLA PROPIA, no de gestión**: las nueve secciones del staff en
  NINGUNO, y `MIS_CLASES` en LECTURA. Mira su clase; cancelar un turno sigue siendo
  del gimnasio. En Flet queda sin acceso a propósito — su pantalla vive en la PWA y
  el login de escritorio lo manda a la web.
- **Reusa `_a_turno_de_panel`** del panel de recepción en vez de armar otra forma
  del mismo dato: el profesor ve exactamente lo que ve el mostrador.
- Frontend: `services/profesorService.ts` + `views/profesor/MisClasesView.tsx`.
- Verificado: `check_permisos` OK (6 roles × 17 secciones × 11 acciones en las tres
  copias), `tsc`, `oxlint`, `import main`, `compileall`.
- **Falta probarlo con un Profesor real**: el escenario de demo no tiene ninguno, así
  que hay que dar uno de alta y asignarle un horario para verlo en pantalla.

---

### 11. Tanda del 2026-09-16 (segunda lista del dueño) — commiteada en `desarrollo`

Salió de las observaciones nuevas de `A CORREGIR PWA .txt` (Rutinas, Nutrición,
Actividades, Usuarios). Verificado: `tsc`, `oxlint`, `check_permisos`, `import main`,
`compileall`, chequeo AST y `pruebas_vistas.py`, todo en verde.

- **El bug de asignar profesores eran DOS cosas distintas**, y conviene separarlas:
  1. **Argumentos invertidos en la PWA.** `ProfesorAsignacionModal` llamaba
     `asignarProfesorAActividad(idProfesor, idActividad)` contra una firma
     `(idActividad, idProfesor)`. Como los dos son `number`, **TypeScript no podía
     verlo**: la URL salía cruzada y el backend contestaba "el profesor no existe",
     "X ya está asignado" nombrando a otro, o "no está asignado" al querer sacarlo.
     Ahora los ids van en un OBJETO (`VinculoProfesorActividad`), así invertirlos es
     error de compilación. Flet no tenía este bug.
  2. **Hay DOS empleados "PEPE SAND"** (DNI distintos, alta legítima). Flet comparaba
     los asignados **por nombre**, así que los dos salían "Asignado". Ahora compara
     por id. **PENDIENTE**: en pantalla siguen viéndose idénticos — falta mostrar un
     dato que los distinga (legajo o DNI) en la lista de asignación.
- **El "PEPE fantasma" de Usuarios no era un dato corrupto**: ninguno de los dos PEPE
  tenía fila en `Usuario`, porque eran Profesores y hasta esta misma tanda el alta se
  negaba a crearles cuenta. Con el rol Profesor (sección 10) deja de pasar.
- **Agujero de offboarding, encontrado de paso y grave**: `Empleado.activo` y
  `Usuario.activo` son dos banderas y cada panel tocaba la suya. En la base había un
  empleado **dado de baja con la cuenta ACTIVA** (podía iniciar sesión). Ahora
  `toggle-estado` de Usuarios **se niega a reactivar** la cuenta de alguien dado de
  baja y manda a hacerlo desde Personal, que devuelve puesto y acceso juntos.
- **Dar de baja un empleado ahora lo DESASIGNA** de sus actividades
  (`Profesor_Actividad`). Los turnos ya programados no se tocan: guardan su propio
  `id_profesor` y borrarlos dejaría clases sin responsable.
- **Topes en Actividades**, en backend y en las dos apps: 7 clases/semana, 31/mes, 1
  para clase suelta, y cupo por turno de 1 a 100. "8 por semana" no es un plan caro,
  es un plan imposible: el socio lo paga y nunca puede usarlo.
- **Se retiró el NIVEL de rutina** (Principiante/Intermedio/Avanzado) de las tres
  capas y se reemplazó el filtro por **días por semana (1 a 7)**, que ya estaba
  guardado. **NO toca la base**: la columna `Rutina.nivel` queda nullable y sin usar —
  borrarla sería un cambio de esquema por un dato de presentación.
- **Rutinas: botón "Ejercicios"** para ver el catálogo antes de cargar uno repetido.
  Reusa `CatalogoEjercicios`, que ya existía para el socio.
- **Nutrición**: botón "Asignar" en la tarjeta (antes había que abrir el plan) en las
  dos apps, y el detalle de la PWA cierra tocando afuera.
- **Usuarios: resetear contraseña abre el MISMO panel que el alta** (usuario, clave, y
  botones de mail/WhatsApp/copiar). Antes mostraba la clave en un snack persistente y
  había que copiarla a mano. El panel se extrajo a `components/PanelCredenciales.tsx`
  y ahora lo usan las dos pantallas; `UsuarioAdminOut` sumó `telefono` (con su
  `selectinload`, para no reintroducir el N+1 que documenta `CARGA_DE_ROLES`).
  **En Flet se había quedado sin replicar** y el dueño lo encontró probando: el diálogo
  de reseteo sólo tenía "Listo". Ahora tiene los mismos botones que el alta, y
  `ASUNTO_CREDENCIALES` vive en `app/contacto.py` (una sola copia para alta y reseteo).
  Ojo al probarlo: las cuentas del demo sin mail ni teléfono (`ana.gomez`,
  `beto.ruiz`, `rita.lopez`) no muestran botones de envío, y es correcto — no hay a
  dónde mandar nada.

**Queda pendiente de esta tanda** (necesita decisión del dueño, ver más abajo): los
datos YA rotos en la base —PATO TORANZO dado de baja sigue asignado a Yoga, y la
cuenta de `dasda adasa` sigue activa— porque los arreglos de arriba valen para las
bajas de acá en adelante, no para las que ya ocurrieron.

---

## Modelo de datos: "registros" vs "planes" (importante, no se ve en el código)

- **Registros** (`Registro_Comida`, `Registro_Ejercicio`, `Registro_Salud`): son un
  **log append-only por fecha**. NO se pisan ni se actualizan: cada carga es una fila
  nueva con su `fecha`. Los viejos quedan para siempre (alimentan los gráficos). NO
  hay "activo": el actual es el de fecha más reciente. Granos: `Registro_Comida` varias
  por día; `Registro_Ejercicio` único `(socio, ejercicio, fecha)` → una por día que se
  ACUMULA si contás dos series; `Registro_Salud` único `(socio, fecha)`.
- **Planes** (`Asignacion_Rutina`, `Asignacion_Dieta`): ahí SÍ hay "actual". Tienen
  `estado` + un **índice único parcial** `una_activa` (`WHERE estado='ACTIVA'`) →
  una sola activa por socio. Al rehacer la propia, la vieja pasa a `FINALIZADA`
  (historial) y la nueva queda `ACTIVA`. La base sabe cuál es la actual por el estado.

---

## Lo que FALTA / próximos pasos

### Coach con IA (LLM) — DECIDIDO, no implementado
El siguiente gran paso. Diseño acordado con el dueño:
- **Chatbot a pedido** (no automático), con **historial guardado** (tabla nueva chica).
- Corre en el **backend** llamando a una **API externa** = **Claude (Anthropic API)**,
  modelo **Haiku 4.5** para el chat común (barato).
- **Tool-use / function calling**: si el socio dice "aplicá este cambio", el LLM
  modifica su rutina/dieta llamando a los MISMOS endpoints self-scoped (con el token
  del socio → no puede tocar nada ajeno). Regla: **propone → el socio confirma → aplica**,
  nunca en silencio.
- **NUNCA** manda datos médicos (patologías) al tercero. Sólo peso/reps/comidas.
- **Consentimiento explícito** del socio (dónde guardarlo, a definir — se propuso un flag por socio).
- Control de costo: resumen compacto de datos por llamada, ventana de chat acotada, tope por día.
- De yapa: **autocompletar de macros** por texto en el registro de comida.
- El "cerebro" del coach NO se entrena: se hace con un **system prompt rico**
  (metodología, reglas, tono, seguridad) + los datos reales del socio + tools + (opcional) RAG.

**Decisión de infraestructura (2026-09-14):** por ahora **"la fácil" = alquilar Claude
vía API (con API key de Anthropic)** — necesita la key (secreto, como el token de
Mercado Pago pendiente); sin ella el código queda listo pero no responde. CONTEXTO: es
un **proyecto escolar con presupuesto ilimitado** y previsto para **servidores locales**,
así que más adelante se puede migrar a un **modelo open-weights auto-hospedado** (Llama/
Qwen/etc.) sin API key — reusando el mismo system prompt y la misma lógica. Tampoco ahí
se entrena desde cero: se bajan pesos ya entrenados y se hace prompting/fine-tuning.

**PENDIENTE de definir con el dueño antes de codear:** la metodología/criterio de
entrenamiento y nutrición que va en el system prompt (estándar sólido vs. material propio),
y dónde persistir el consentimiento.

### Otros pendientes
- **Terminar `A CORREGIR PWA .txt`** — faltan los paneles que el dueño todavía no probó,
  y probar en pantalla el chip del ingreso repetido (fichar dos veces al mismo socio).
- **#4 overlay del contador** (sacar líneas verdes) — cuando el tracking esté redondo.
- **Mercado Pago** — falta el token, el secreto del webhook y una URL pública. No depende
  del código.
- **Seguridad** — **V-01 a V-07 y V-09 están resueltas** (modo simulado que no se
  registra en producción, traba de 15 min + 429 por IP, bcrypt de relleno, montos
  `Infinity`/`NaN`, política de contraseñas). Quedan tres, y dos son **a propósito**:
  **V-08** (JWT sin revocación: revocar = desactivar la cuenta) y **V-10**
  (Entrenador y Nutricionista leen a todos los socios) son decisiones de diseño;
  **V-11** (el header `X-Client-Type`, que lo elige el cliente, decide si el token va
  en cookie httponly o en el cuerpo) es endurecimiento pendiente de verdad.
  Detalle en `docs/vulnerabilidades a arreglar.md`.
- **Videos en la tele** — lo último de lo último.
- **Fichaje con tarjeta RFID (lector físico)** — **el último de todos**, y no depende del
  código: primero se compra el lector (es barato) y recién ahí se programa, que con el
  aparato en la mano es corto. Decisión del dueño del 2026-09-16: la tarjeta SÍ tiene que
  existir; lo que se sacó de las apps fue el campo de texto, que no era un lector.
  Estado al pausarlo, para no volver a investigarlo desde cero:
  - **Ya existe** la columna `Socio.codigo_rfid` (varchar(50) UNIQUE, nullable) en Neon,
    en `db/schema.sql`, en `models.py` y en `types.ts`. Y `POST /asistencia/fichar` ya
    acepta `codigo_rfid`, resuelve el socio y guarda `metodo_registro='RFID'`.
  - **OJO: eso parece código muerto y NO lo es.** La columna está huérfana (nada le
    escribe un valor) y ninguna pantalla manda `codigo_rfid`, así que la tentación de
    "limpiarlos" es alta. No se tocan: son la mitad ya hecha de esta feature.
  - **Falta** (a) asignarle el código a un socio — hoy nada lo escribe, y `recepcion.py`
    sólo lo lee como el booleano `tiene_rfid`; y (b) que el aparato pueda autenticarse:
    `security.py` tiene tres capas y las tres terminan en un JWT de un `Usuario` real, así
    que un lector colgado en la puerta no entra. A favor: `Asistencia.id_registrado_por`
    ya es nullable, o sea que un ingreso sin ninguna persona detrás es válido en el modelo.
  - **Camino que se venía eligiendo, sin cerrar**: una clave de dispositivo en el `.env`
    (como el token de Mercado Pago) y un endpoint que no pida sesión de usuario. Quedó sin
    decidir cómo simular el lector mientras no esté el hardware — probablemente ni haga
    falta si el aparato llega antes.

---

## Cómo correr y probar

Comandos completos en `CLAUDE.md`. Lo esencial:

- **Backend** (desde `backend/`, SIEMPRE el Python del venv):
  `.venv/Scripts/python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000`
  **No corre con `--reload`:** si tocás rutas, reiniciá o la API vieja te contesta.
- **Suites**: son **11** en `backend/pruebas/` (backend levantado + base VACÍA;
  vaciar entre una y otra con `pruebas/vaciar_base.py --si`, regenerar el demo con
  `pruebas/escenario_demo.py`). `test_deudas.py` **ya no existe** — probaba la tabla
  `Deuda`, que se eliminó. **OJO: mientras el dueño esté probando, NO se vacía la base.**
- **PWA** (desde `Proyecto - PWA/src/frontend`): `npx tsc --noEmit -p tsconfig.app.json`
  y `npx oxlint src/` (los dos tienen que dar 0).
- **Flet** (desde `Flet/Proyecto`): `python -m compileall -q app main.py` **y**
  `python pruebas_vistas.py` (construye cada vista con cada rol; necesita el backend
  levantado y las cuentas del demo).
- **Probar contra la base real sin romper nada:** un script que guarde el estado, haga
  el ida y vuelta y **restaure** (ejemplo: el smoke test de teléfonos). Las suites se
  autentican con `POST /login` + header `X-Client-Type: escritorio` y `Authorization:
  Bearer <token>`, sin CSRF.
- **Probar en el celu (iPhone sin cable):** Vite en HTTPS LAN + túnel de cloudflared:
  1. `VITE_HTTPS=1 npm run dev` (desde el frontend) → HTTPS en :5173.
  2. `cloudflared tunnel --url https://localhost:5173 --no-tls-verify` → da una URL pública `*.trycloudflare.com`.
  3. Abrir esa URL en el celu. El frontend pega a `/api`, que Vite proxea al backend :8000.
  El firewall de Windows (perfil "Public") bloquea el acceso directo por IP, por eso el túnel.
  **El túnel expone todo públicamente: cerralo al terminar.**

---

## Trampas y reglas que ya costaron (resumen; el detalle en CLAUDE.md)

- **Git:** stagear SIEMPRE rutas explícitas, **nunca `git add -A`/`commit -a`** (se
  llevan el `.git.repo-viejo-backup` del sub-repo Flet y archivos sin decidir). Nunca
  commitear `.env` reales. Las credenciales de testeo van SÓLO en
  `backend/CONTRASEÑAS PARA TESTEO Y ACTUALIZADAS.txt`. Los 40MB de `public/mediapipe`
  ya están en la historia (necesarios para que el contador ande en otra máquina).
- **Base de datos:** `db/schema.sql` y Neon coinciden nombre por nombre. Las migraciones
  de esta tanda ya se aplicaron a Neon a mano (Rutina/Dieta/Comida nullables +
  `Comida.descripcion` + `Registro_Comida` con `momento` y macros). Si reconstruís desde
  `db/schema.sql`, ya está todo.
- **Dos estados de la base:** ENTREGA (6 filas) y DEMO (~70). Ver en cuál estás con
  `pruebas/vaciar_base.py` (sin `--si` sólo informa). Credenciales demo: todas `Demo2026!`.
- **Casi todos los bugs aparecen CORRIENDO, no leyendo.** `tsc`/`oxlint`/`compileall`
  no bastan; hay que ejecutar la vista/endpoint con datos reales.
- **Flet: `pruebas_vistas.py` tampoco alcanza para los diálogos.** Un `ft.Row(wrap=True)` con
  `TextField` adentro no se dibuja en Flet 0.84 y deja un bloque GRIS enorme; sólo se vio
  abriéndolo en el navegador (`ft.AppView.WEB_BROWSER`; con `view=None` no sirve HTTP).
- **Login en ráfaga:** 5 fallos traban la cuenta 15 minutos y 20 por IP en 10 minutos dan
  429 — y todo llega desde 127.0.0.1. Reiniciar el backend limpia las dos cosas.
