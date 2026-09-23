# OlimpOS — Procesos lógicos requeridos

Un proceso por cada unidad de trabajo del sistema, en el formato lineal de DFD de
`lógico requerido spec.md`.

**Son 173 procesos: 167 rutas de la API (todas) y 6 procesos que corren solos.**

---

## Cómo se lee una línea

```
(ENTIDAD) -> (ENTRADA) <- (SALIDA) --- (N. NOMBRE) -> (TABLA -- escrito - escrito) <- (TABLA -- leído)
```

| Parte | Qué dice |
|---|---|
| `(ENTIDAD)` | Quién lo dispara. Sólo los 6 roles del sistema. |
| `-> (ENTRADA)` | Los datos que entran, agrupados bajo un concepto. |
| `<- (SALIDA)` | Lo que el sistema devuelve, **abarcando el éxito y los errores**. |
| `--- (N. NOMBRE)` | El evento lógico. Cubre todos los subcasos del proceso. |
| `-> (TABLA -- ...)` | Una tabla que el proceso **escribe**, con todos los atributos que toca en cualquier subcaso. |
| `<- (TABLA -- ...)` | Una tabla que el proceso **lee** para validar o decidir. |

Las escrituras van siempre antes que las lecturas. Un proceso que no lee nada lleva `<- ()`.
Un proceso que no escribe nada no lleva ningún bloque `->` de tabla.

---

## Convenciones que tomé

La spec no las cubre, así que las decidí y las dejo explícitas:

1. **Una entidad por rol que puede disparar el proceso.** Cuando varios roles pueden
   ejecutarlo, van separados por `/`. Sale de la matriz de permisos de `backend/permisos.py`,
   no de una suposición: un endpoint con `requiere_seccion(SOCIOS)` lo cumplen los cuatro
   roles que tienen esa sección, y uno con `requiere_accion(ALTA_BAJA_SOCIOS)` sólo Dueño y
   Recepcionista.

2. **El `CONCEPTO_SALIDA` nombra los errores, no sólo el camino feliz.** La spec pide que el
   proceso abarque "todos los casos posibles", así que un alta de socio dice también
   "rechazo por DNI ya registrado", y el login dice "acceso denegado y cuenta trabada".

3. **Los atributos de los subcasos de error van igual en el bloque de escritura.** El ejemplo
   de la spec lo pide con `intentos_fallidos`: se escribe **sólo** cuando la contraseña
   falla, y aun así figura.

4. **Un proceso arrastra lo que escriben las funciones que llama.** Dar de baja a un socio
   ejecuta `bajas.aplicar_baja()`, que toca `Socio`, `Membresia`, `Reserva` y `Usuario`:
   esas cuatro tablas van en la línea de la baja aunque el router no las mencione.

5. **Las funciones internas no son procesos.** `_estado_socio`, `_membresia_vigente`,
   `reserva_a_acreditar`, el middleware de CSRF o el de CORS no se disparan solos: corren
   adentro de otro proceso, y sus lecturas ya están contadas ahí. Listarlas aparte mostraría
   el mismo flujo dos veces.

6. **Los nombres son los de la base**, no los del código Python ni los del schema de la API.
   `Dueno` sin ñ, `Profesor_Actividad` con guión bajo, `porcentaje_descuento` entero.

---

## Cómo se verificó

Cada línea la escribió un agente leyendo el archivo completo y siguiendo las funciones que
el endpoint llama a otros módulos; después otro agente la revisó contra el mismo código
buscando tablas y atributos faltantes. Sobre eso corrí tres controles mecánicos:

- **Cobertura:** las rutas salen de la aplicación FastAPI en memoria, no de un grep de
  decoradores. Por eso son 167 y no 165: `GET /` y `POST /portal/mi-cuota/pagar/{id_pago}/simular`
  se registran sin decorador y un grep no las ve. Las 167 tienen línea.
- **Nombres:** un validador compara cada tabla y cada atributo de cada línea contra las
  columnas reales de `db/schema.sql`. Las 173 líneas pasan.
- **Tablas huérfanas:** las 41 tablas del esquema aparecen en al menos un proceso.

---

## Dos cosas que este formato no puede expresar

Las anoto porque son flujos reales del sistema que no vas a encontrar en ninguna línea:

- **Los almacenes que no son tablas.** El proceso que baja los videos de YouTube escribe
  archivos en `VIDEOS_DIR`, y que el archivo exista *es* el estado del proceso (por eso no hay
  columna que lo marque). En la notación sólo entran tablas, así que ese proceso aparece
  leyendo `Ejercicio` y sin escribir nada.
- **Las entidades externas.** El servidor de mail (las credenciales que se mandan al dar de
  alta) y Mercado Pago (que es quien dispara `POST /webhooks/mercadopago`) son entidades
  externas del DFD, pero la spec restringe `(ENTIDAD)` a los 6 roles. En el webhook puse el
  rol beneficiario y lo aclaro acá.

**`Sede` y `Franja_Laboral` no las escribe ningún proceso, y está bien:** vienen cargadas en
el estado de ENTREGA de la base y el backend sólo las lee. La única ruta de franjas
(`GET /personal/franjas`) es de consulta.

---

## Indice

- **Acceso y sesion** — procesos 1 a 5 (5)
- **Socios** — procesos 6 a 28 (23)
- **Personal** — procesos 29 a 37 (9)
- **Usuarios y cuentas de acceso** — procesos 38 a 45 (8)
- **Cobros y pagos** — procesos 46 a 51 (6)
- **Asistencia** — procesos 52 a 56 (5)
- **Recepcion** — procesos 57 a 59 (3)
- **Actividades, turnos y horarios** — procesos 60 a 87 (28)
- **Rutinas** — procesos 88 a 97 (10)
- **Nutricion** — procesos 98 a 107 (10)
- **Patologias** — procesos 108 a 109 (2)
- **Promociones** — procesos 110 a 117 (8)
- **Dashboard** — procesos 118 a 121 (4)
- **Portal del socio** — procesos 122 a 167 (46)
- **Procesos automaticos** — procesos 168 a 173 (6)

---


## Acceso y sesion

**1. Chequear que la API responde**  
`GET /`

```
(DUENO / RECEPCIONISTA / ENTRENADOR / NUTRICIONISTA / PROFESOR / SOCIO) -> (Pedido de chequeo) <- (Confirmacion de que la API esta viva) --- (1. Chequear que la API responde) <- ()
```

**2. Cambiar la contrasena**  
`POST /cambiar-password`

```
(DUENO / RECEPCIONISTA / ENTRENADOR / NUTRICIONISTA / PROFESOR / SOCIO) -> (Credenciales y contrasena nueva) <- (Contrasena actualizada, rechazo por credenciales invalidas, contrasena nueva igual a la anterior, contrasena debil o demasiados intentos) --- (2. Cambiar la contrasena) -> (Usuario -- password_hash - debe_cambiar_password - intentos_fallidos) <- (Usuario -- username - password_hash - activo - bloqueado - intentos_fallidos)
```

**3. Iniciar sesion**  
`POST /login`

```
(DUENO / RECEPCIONISTA / ENTRENADOR / NUTRICIONISTA / PROFESOR / SOCIO) -> (Credenciales) <- (Sesion iniciada, cambio de contrasena obligatorio, acceso denegado, cuenta trabada o cuenta sin perfil) --- (3. Iniciar sesion) -> (Usuario -- intentos_fallidos - ultimo_acceso) <- (Usuario -- id_usuario - username - password_hash - activo - bloqueado - debe_cambiar_password - intentos_fallidos - id_persona) <- (Persona -- id_persona - nombre - apellido - dni - email - fecha_nacimiento - activo) <- (Dueno -- id_persona) <- (Socio -- id_socio - id_persona) <- (Empleado -- id_empleado - id_persona) <- (Entrenador -- id_empleado) <- (Nutricionista -- id_empleado) <- (Recepcionista -- id_empleado) <- (Profesor -- id_profesor - id_empleado)
```

**4. Cerrar sesion**  
`POST /logout`

```
(DUENO / RECEPCIONISTA / ENTRENADOR / NUTRICIONISTA / PROFESOR / SOCIO) -> (Pedido de cierre de sesion) <- (Sesion cerrada y cookies borradas) --- (4. Cerrar sesion) <- ()
```

**5. Recuperar la sesion vigente**  
`GET /me`

```
(DUENO / RECEPCIONISTA / ENTRENADOR / NUTRICIONISTA / PROFESOR / SOCIO) -> (Pedido de consulta) <- (Identidad y roles de la sesion, o sesion invalida) --- (5. Recuperar la sesion vigente) <- (Usuario -- id_usuario - id_persona - username - ultimo_acceso - activo - bloqueado - debe_cambiar_password) <- (Persona -- id_persona - nombre - apellido - dni - email - fecha_nacimiento - activo)
```


## Socios

**6. Listar socios y aplicar las bajas programadas vencidas**  
`GET /socios`

```
(DUENO / RECEPCIONISTA / ENTRENADOR / NUTRICIONISTA) -> (Pedido de consulta) <- (Grilla de socios con estado, plan, vencimiento y baja programada derivados, aviso de cuenta sin acceso, o acceso denegado) --- (6. Listar socios y aplicar las bajas programadas vencidas) -> (Baja -- pendiente) -> (Socio -- activo) -> (Membresia -- estado) -> (Reserva -- estado - fecha_cancelacion) -> (Usuario -- activo) <- (Socio -- id_socio - id_persona - id_sede - numero_socio - fecha_alta - objetivo - observaciones - activo) <- (Persona -- id_persona - dni - nombre - apellido - email - fecha_nacimiento - calle - numero_calle - localidad) <- (Telefono -- id_telefono - id_persona - numero - principal) <- (Contacto_Emergencia -- id_contacto_emergencia - id_persona - nombre - telefono - parentesco - principal) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password) <- (Membresia -- id_membresia - id_socio - id_tipo_membresia - fecha_inicio - fecha_vencimiento - estado) <- (Tipo_Membresia -- id_tipo_membresia - nombre) <- (Baja -- id_baja - id_socio - fecha_baja - tipo - pendiente) <- (Reserva -- id_reserva - id_turno - id_socio - estado - fecha_reserva) <- (Turno -- id_turno - fecha - cupo_maximo - estado)
```

**7. Dar de alta un socio con su cuenta de acceso y credenciales temporales**  
`POST /socios`

```
(DUENO / RECEPCIONISTA) -> (Datos del socio) <- (Socio dado de alta con usuario y contrasena temporal de un solo uso -enviada por mail o entregada a mano-, socio dado de alta reusando una cuenta existente, socio dado de alta sin cuenta, o rechazo por sede inexistente, persona ya registrada como socio o email duplicado) --- (7. Dar de alta un socio con su cuenta de acceso y credenciales temporales) -> (Persona -- dni - nombre - apellido - email - sexo - fecha_nacimiento - calle - numero_calle - localidad) -> (Contacto_Emergencia -- id_persona - nombre - telefono - parentesco - principal) -> (Telefono -- id_persona - numero - tipo - principal) -> (Socio -- id_persona - id_sede - numero_socio - fecha_alta - objetivo - observaciones - activo) -> (Usuario -- id_persona - username - password_hash - debe_cambiar_password - activo) <- (Sede -- id_sede) <- (Persona -- id_persona - dni - nombre - apellido - email - fecha_nacimiento - activo) <- (Socio -- id_socio - id_persona - numero_socio) <- (Usuario -- id_usuario - id_persona - username - activo - bloqueado - debe_cambiar_password)
```

**8. Finalizar la asignacion de un entrenador conservando el historial**  
`POST /socios/entrenadores/asignaciones/{id_asignacion}/finalizar`

```
(DUENO / RECEPCIONISTA / ENTRENADOR) -> (id_asignacion) <- (Asignacion finalizada con su fecha de fin, asignacion inexistente, asignacion de otro entrenador o asignacion ya finalizada) --- (8. Finalizar la asignacion de un entrenador conservando el historial) -> (Asignacion_Entrenador -- estado - fecha_fin) <- (Asignacion_Entrenador -- id_asignacion_entrenador - id_socio - id_entrenador - fecha_inicio - fecha_fin - estado) <- (Empleado -- id_empleado - id_persona) <- (Entrenador -- id_entrenador - id_empleado - especialidad) <- (Persona -- id_persona - nombre - apellido) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**9. Listar los socios que entrena un entrenador**  
`GET /socios/entrenadores/{id_entrenador}/socios`

```
(DUENO / RECEPCIONISTA / ENTRENADOR / NUTRICIONISTA) -> (id_entrenador) <- (Grilla de los socios activos a cargo de ese entrenador, o entrenador inexistente) --- (9. Listar los socios que entrena un entrenador) <- (Entrenador -- id_entrenador) <- (Asignacion_Entrenador -- id_asignacion_entrenador - id_socio - id_entrenador - estado) <- (Socio -- id_socio - id_persona - id_sede - numero_socio - fecha_alta - objetivo - observaciones - activo) <- (Persona -- id_persona - dni - nombre - apellido - email - fecha_nacimiento - calle - numero_calle - localidad) <- (Telefono -- id_telefono - id_persona - numero - principal) <- (Contacto_Emergencia -- id_contacto_emergencia - id_persona - nombre - telefono - parentesco - principal) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password) <- (Membresia -- id_membresia - id_socio - id_tipo_membresia - fecha_inicio - fecha_vencimiento - estado) <- (Tipo_Membresia -- id_tipo_membresia - nombre) <- (Baja -- id_baja - id_socio - fecha_baja - pendiente)
```

**10. Consultar la ficha de un socio**  
`GET /socios/{id_socio}`

```
(DUENO / RECEPCIONISTA / ENTRENADOR / NUTRICIONISTA) -> (id_socio) <- (Ficha del socio con estado, plan y vencimiento derivados, o socio inexistente) --- (10. Consultar la ficha de un socio) <- (Socio -- id_socio - id_persona - id_sede - numero_socio - fecha_alta - objetivo - observaciones - activo) <- (Persona -- id_persona - dni - nombre - apellido - email - fecha_nacimiento - calle - numero_calle - localidad) <- (Telefono -- id_telefono - id_persona - numero - principal) <- (Contacto_Emergencia -- id_contacto_emergencia - id_persona - nombre - telefono - parentesco - principal) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password) <- (Membresia -- id_membresia - id_socio - id_tipo_membresia - fecha_inicio - fecha_vencimiento - estado) <- (Tipo_Membresia -- id_tipo_membresia - nombre) <- (Baja -- id_baja - id_socio - fecha_baja - pendiente)
```

**11. Editar la ficha de un socio**  
`PUT /socios/{id_socio}`

```
(DUENO / RECEPCIONISTA) -> (Datos editados del socio) <- (Ficha actualizada, telefono principal borrado si se vacio el campo, socio inexistente, email ya registrado para otra persona o contacto de emergencia sin nombre y telefono) --- (11. Editar la ficha de un socio) -> (Persona -- nombre - apellido - email - fecha_nacimiento - calle - numero_calle - localidad) -> (Socio -- objetivo - observaciones) -> (Contacto_Emergencia -- id_persona - nombre - telefono - parentesco - principal) -> (Telefono -- id_telefono - id_persona - numero - tipo - principal) <- (Socio -- id_socio - id_persona - id_sede - numero_socio - fecha_alta - objetivo - observaciones - activo) <- (Persona -- id_persona - dni - nombre - apellido - email - fecha_nacimiento - calle - numero_calle - localidad) <- (Telefono -- id_telefono - id_persona - numero - tipo - principal) <- (Contacto_Emergencia -- id_contacto_emergencia - id_persona - nombre - telefono - parentesco - principal) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password) <- (Membresia -- id_membresia - id_socio - id_tipo_membresia - fecha_inicio - fecha_vencimiento - estado) <- (Tipo_Membresia -- id_tipo_membresia - nombre) <- (Baja -- id_baja - id_socio - fecha_baja - pendiente)
```

**12. Anular una baja programada que todavia no ocurrio**  
`POST /socios/{id_socio}/anular-baja`

```
(DUENO / RECEPCIONISTA) -> (id_socio) <- (Baja programada anulada y socio que sigue activo, socio inexistente o socio sin baja programada) --- (12. Anular una baja programada que todavia no ocurrio) -> (Baja -- id_baja - id_socio - fecha_baja - tipo - motivo - pendiente) <- (Socio -- id_socio - id_persona - id_sede - numero_socio - fecha_alta - objetivo - observaciones - activo) <- (Persona -- id_persona - dni - nombre - apellido - email - fecha_nacimiento - calle - numero_calle - localidad) <- (Baja -- id_baja - id_socio - fecha_baja - pendiente) <- (Telefono -- id_telefono - id_persona - numero - principal) <- (Contacto_Emergencia -- id_contacto_emergencia - id_persona - nombre - telefono - parentesco - principal) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password) <- (Membresia -- id_membresia - id_socio - id_tipo_membresia - fecha_inicio - fecha_vencimiento - estado) <- (Tipo_Membresia -- id_tipo_membresia - nombre)
```

**13. Dar de baja a un socio, programada al vencer el periodo pago o inmediata**  
`POST /socios/{id_socio}/baja`

```
(DUENO / RECEPCIONISTA) -> (Datos de la baja) <- (Baja programada para el dia siguiente al vencimiento, baja aplicada hoy con reservas canceladas y cuenta desactivada, socio inexistente, o rechazo porque el socio ya estaba de baja o ya tenia la baja programada) --- (13. Dar de baja a un socio, programada al vencer el periodo pago o inmediata) -> (Baja -- id_socio - fecha_baja - tipo - motivo - pendiente) -> (Congelamiento -- estado - fecha_reanudacion) -> (Membresia -- fecha_vencimiento - estado) -> (Socio -- activo) -> (Reserva -- estado - fecha_cancelacion) -> (Usuario -- activo) <- (Socio -- id_socio - id_persona - id_sede - numero_socio - fecha_alta - objetivo - observaciones - activo) <- (Persona -- id_persona - dni - nombre - apellido - email - fecha_nacimiento - calle - numero_calle - localidad) <- (Baja -- id_baja - id_socio - fecha_baja - tipo - motivo - pendiente) <- (Congelamiento -- id_congelamiento - id_membresia - fecha_inicio - fecha_fin - estado) <- (Membresia -- id_membresia - id_socio - id_tipo_membresia - fecha_inicio - fecha_vencimiento - estado) <- (Tipo_Membresia -- id_tipo_membresia - nombre) <- (Reserva -- id_reserva - id_turno - id_socio - estado - fecha_reserva) <- (Turno -- id_turno - fecha - cupo_maximo - estado) <- (Telefono -- id_telefono - id_persona - numero - principal) <- (Contacto_Emergencia -- id_contacto_emergencia - id_persona - nombre - telefono - parentesco - principal) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**14. Consultar a quien avisar en una emergencia**  
`GET /socios/{id_socio}/contactos-emergencia`

```
(DUENO / RECEPCIONISTA / ENTRENADOR / NUTRICIONISTA) -> (id_socio) <- (Contactos de emergencia del socio ordenados con el principal primero, o socio inexistente) --- (14. Consultar a quien avisar en una emergencia) <- (Socio -- id_socio - id_persona) <- (Contacto_Emergencia -- id_contacto_emergencia - id_persona - nombre - telefono - parentesco - principal) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**15. Agregar un contacto de emergencia a la ficha**  
`POST /socios/{id_socio}/contactos-emergencia`

```
(DUENO / RECEPCIONISTA) -> (Datos del contacto de emergencia) <- (Contacto agregado -principal si es el primero o si se pidio-, socio inexistente o numero ya cargado como contacto) --- (15. Agregar un contacto de emergencia a la ficha) -> (Contacto_Emergencia -- id_persona - nombre - telefono - parentesco - principal) <- (Socio -- id_socio - id_persona) <- (Contacto_Emergencia -- id_contacto_emergencia - id_persona - nombre - telefono - parentesco - principal) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**16. Editar un contacto de emergencia y elegir cual es el principal**  
`PUT /socios/{id_socio}/contactos-emergencia/{id_contacto}`

```
(DUENO / RECEPCIONISTA) -> (Datos del contacto de emergencia) <- (Contacto actualizado y principal reasignado, socio inexistente o contacto que no es de esta ficha) --- (16. Editar un contacto de emergencia y elegir cual es el principal) -> (Contacto_Emergencia -- nombre - telefono - parentesco - principal) <- (Socio -- id_socio - id_persona) <- (Contacto_Emergencia -- id_contacto_emergencia - id_persona - nombre - telefono - parentesco - principal) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**17. Sacar un contacto de emergencia de la ficha y ascender el principal si hacia falta**  
`DELETE /socios/{id_socio}/contactos-emergencia/{id_contacto}`

```
(DUENO / RECEPCIONISTA) -> (id_contacto) <- (Contacto borrado y principal reasignado al mas viejo, socio inexistente o contacto que no es de esta ficha) --- (17. Sacar un contacto de emergencia de la ficha y ascender el principal si hacia falta) -> (Contacto_Emergencia -- id_contacto_emergencia - id_persona - nombre - telefono - parentesco - principal) <- (Socio -- id_socio - id_persona) <- (Contacto_Emergencia -- id_contacto_emergencia - id_persona - nombre - telefono - parentesco - principal) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**18. Consultar los entrenadores a cargo de un socio con su historial**  
`GET /socios/{id_socio}/entrenadores`

```
(DUENO / RECEPCIONISTA / ENTRENADOR / NUTRICIONISTA) -> (id_socio) <- (Historial de entrenadores del socio, solo los activos si se pide, o socio inexistente) --- (18. Consultar los entrenadores a cargo de un socio con su historial) <- (Socio -- id_socio) <- (Asignacion_Entrenador -- id_asignacion_entrenador - id_socio - id_entrenador - fecha_inicio - fecha_fin - estado) <- (Entrenador -- id_entrenador - id_empleado - especialidad) <- (Empleado -- id_empleado - id_persona) <- (Persona -- id_persona - nombre - apellido) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**19. Asignarle un entrenador a cargo a un socio**  
`POST /socios/{id_socio}/entrenadores`

```
(DUENO / RECEPCIONISTA / ENTRENADOR) -> (Datos de la asignacion) <- (Entrenador asignado o asignacion reactivada, socio o entrenador inexistente, socio dado de baja, entrenador que ya no trabaja, intento de asignar a otro entrenador, o entrenador ya a cargo de ese socio) --- (19. Asignarle un entrenador a cargo a un socio) -> (Asignacion_Entrenador -- id_socio - id_entrenador - fecha_inicio - fecha_fin - estado) <- (Socio -- id_socio - activo) <- (Empleado -- id_empleado - id_persona - activo) <- (Entrenador -- id_entrenador - id_empleado - especialidad) <- (Persona -- id_persona - nombre - apellido) <- (Asignacion_Entrenador -- id_asignacion_entrenador - id_socio - id_entrenador - fecha_inicio - fecha_fin - estado) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**20. Consultar el historial medico de un socio**  
`GET /socios/{id_socio}/patologias`

```
(DUENO / ENTRENADOR / NUTRICIONISTA) -> (id_socio) <- (Historial medico del socio o socio inexistente) --- (20. Consultar el historial medico de un socio) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password - id_persona) <- (Socio -- id_socio) <- (Socio_Patologia -- id_socio - id_patologia - fecha_diagnostico - observaciones) <- (Patologia -- id_patologia - nombre - descripcion)
```

**21. Registrarle una patologia a un socio**  
`POST /socios/{id_socio}/patologias`

```
(DUENO / ENTRENADOR / NUTRICIONISTA) -> (Condicion del socio) <- (Condicion registrada, socio inexistente, patologia fuera del catalogo, ya registrada o fecha de diagnostico futura) --- (21. Registrarle una patologia a un socio) -> (Socio_Patologia -- id_socio - id_patologia - fecha_diagnostico - observaciones) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password - id_persona) <- (Socio -- id_socio) <- (Patologia -- id_patologia - nombre - descripcion) <- (Socio_Patologia -- id_socio - id_patologia)
```

**22. Editar la patologia registrada de un socio**  
`PUT /socios/{id_socio}/patologias/{id_patologia}`

```
(DUENO / ENTRENADOR / NUTRICIONISTA) -> (Condicion del socio) <- (Observaciones actualizadas, registro inexistente o fecha de diagnostico futura) --- (22. Editar la patologia registrada de un socio) -> (Socio_Patologia -- fecha_diagnostico - observaciones) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password - id_persona) <- (Socio_Patologia -- id_socio - id_patologia - fecha_diagnostico - observaciones) <- (Patologia -- id_patologia - nombre - descripcion)
```

**23. Quitarle una patologia a un socio**  
`DELETE /socios/{id_socio}/patologias/{id_patologia}`

```
(DUENO / ENTRENADOR / NUTRICIONISTA) -> (Condicion a quitar) <- (Condicion eliminada del historial o registro inexistente) --- (23. Quitarle una patologia a un socio) -> (Socio_Patologia -- id_socio - id_patologia - fecha_diagnostico - observaciones) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password - id_persona) <- (Socio_Patologia -- id_socio - id_patologia)
```

**24. Reactivar a un socio dado de baja y devolverle el acceso a la app**  
`POST /socios/{id_socio}/reactivar`

```
(DUENO / RECEPCIONISTA) -> (id_socio) <- (Socio reactivado sin membresia y con la cuenta de acceso devuelta, socio inexistente o socio que ya estaba activo) --- (24. Reactivar a un socio dado de baja y devolverle el acceso a la app) -> (Socio -- activo) -> (Usuario -- activo) <- (Socio -- id_socio - id_persona - id_sede - numero_socio - fecha_alta - objetivo - observaciones - activo) <- (Persona -- id_persona - dni - nombre - apellido - email - fecha_nacimiento - calle - numero_calle - localidad) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password) <- (Telefono -- id_telefono - id_persona - numero - principal) <- (Contacto_Emergencia -- id_contacto_emergencia - id_persona - nombre - telefono - parentesco - principal) <- (Membresia -- id_membresia - id_socio - id_tipo_membresia - fecha_inicio - fecha_vencimiento - estado) <- (Tipo_Membresia -- id_tipo_membresia - nombre) <- (Baja -- id_baja - id_socio - fecha_baja - pendiente)
```

**25. Listar los telefonos de la ficha de un socio**  
`GET /socios/{id_socio}/telefonos`

```
(DUENO / RECEPCIONISTA / ENTRENADOR / NUTRICIONISTA) -> (id_socio) <- (Telefonos de la ficha ordenados con el principal primero, o socio inexistente) --- (25. Listar los telefonos de la ficha de un socio) <- (Socio -- id_socio - id_persona) <- (Telefono -- id_telefono - id_persona - numero - tipo - principal) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**26. Agregar un telefono a la ficha de un socio**  
`POST /socios/{id_socio}/telefonos`

```
(DUENO / RECEPCIONISTA) -> (Datos del telefono) <- (Telefono agregado -principal si es el primero o si se pidio-, socio inexistente o numero ya cargado) --- (26. Agregar un telefono a la ficha de un socio) -> (Telefono -- id_persona - numero - tipo - principal) <- (Socio -- id_socio - id_persona) <- (Telefono -- id_telefono - id_persona - numero - principal) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**27. Editar un telefono de la ficha y elegir cual es el principal**  
`PUT /socios/{id_socio}/telefonos/{id_telefono}`

```
(DUENO / RECEPCIONISTA) -> (Datos del telefono) <- (Telefono actualizado y principal reasignado, socio inexistente o telefono que no es de esta ficha) --- (27. Editar un telefono de la ficha y elegir cual es el principal) -> (Telefono -- numero - tipo - principal) <- (Socio -- id_socio - id_persona) <- (Telefono -- id_telefono - id_persona - numero - tipo - principal) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**28. Sacar un telefono de la ficha y ascender el principal si hacia falta**  
`DELETE /socios/{id_socio}/telefonos/{id_telefono}`

```
(DUENO / RECEPCIONISTA) -> (id_telefono) <- (Telefono borrado y principal reasignado al mas viejo, socio inexistente o telefono que no es de esta ficha) --- (28. Sacar un telefono de la ficha y ascender el principal si hacia falta) -> (Telefono -- id_telefono - id_persona - numero - tipo - principal) <- (Socio -- id_socio - id_persona) <- (Telefono -- id_telefono - id_persona - numero - principal) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```


## Personal

**29. Listar el personal**  
`GET /personal`

```
(DUENO / RECEPCIONISTA) -> (Pedido de consulta) <- (Listado del personal con su rol derivado, telefono principal y si tiene cuenta, o acceso denegado) --- (29. Listar el personal) <- (Empleado -- id_empleado - id_persona - id_sede - legajo - fecha_ingreso - fecha_egreso - activo) <- (Persona -- id_persona - dni - nombre - apellido - email) <- (Telefono -- id_telefono - id_persona - numero - principal) <- (Entrenador -- id_empleado - titulo - especialidad - matricula) <- (Nutricionista -- id_empleado - titulo - matricula) <- (Recepcionista -- id_empleado - id_franja_laboral) <- (Profesor -- id_empleado - titulo - especialidad) <- (Franja_Laboral -- id_franja_laboral - nombre) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**30. Dar de alta un empleado**  
`POST /personal`

```
(DUENO) -> (Datos del empleado) <- (Empleado dado de alta con legajo y, segun el caso, credenciales temporales de un solo uso, la cuenta que ya tenia conservada o ninguna cuenta; o sede inexistente, persona ya registrada como empleado, email duplicado o empleado sin email ni telefono) --- (30. Dar de alta un empleado) -> (Persona -- dni - nombre - apellido - email - fecha_nacimiento) -> (Telefono -- id_persona - numero - tipo - principal) -> (Empleado -- id_persona - id_sede - fecha_ingreso - activo - legajo) -> (Entrenador -- id_empleado - titulo - especialidad - matricula) -> (Nutricionista -- id_empleado - titulo - matricula) -> (Recepcionista -- id_empleado - id_franja_laboral) -> (Profesor -- id_empleado - titulo - especialidad) -> (Usuario -- id_persona - username - password_hash - debe_cambiar_password - activo) <- (Sede -- id_sede) <- (Persona -- id_persona - dni - nombre - apellido - email - fecha_nacimiento - activo) <- (Empleado -- id_persona) <- (Usuario -- id_usuario - id_persona - username - activo - bloqueado - debe_cambiar_password)
```

**31. Listar los entrenadores disponibles**  
`GET /personal/entrenadores`

```
(DUENO / RECEPCIONISTA / ENTRENADOR / NUTRICIONISTA) -> (Pedido de consulta) <- (Entrenadores con empleado activo para el selector, reducido a el mismo si quien pide es entrenador, o acceso denegado) --- (31. Listar los entrenadores disponibles) <- (Entrenador -- id_entrenador - id_empleado) <- (Empleado -- id_empleado - id_persona - activo) <- (Persona -- id_persona - nombre - apellido) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**32. Listar el catalogo de franjas laborales**  
`GET /personal/franjas`

```
(DUENO / RECEPCIONISTA) -> (Pedido de consulta) <- (Catalogo de franjas laborales activas o acceso denegado) --- (32. Listar el catalogo de franjas laborales) <- (Franja_Laboral -- id_franja_laboral - nombre - hora_desde - hora_hasta - activo) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**33. Listar los nutricionistas disponibles**  
`GET /personal/nutricionistas`

```
(DUENO / RECEPCIONISTA / ENTRENADOR / NUTRICIONISTA) -> (Pedido de consulta) <- (Nutricionistas con empleado activo para el selector o acceso denegado) --- (33. Listar los nutricionistas disponibles) <- (Nutricionista -- id_nutricionista - id_empleado) <- (Empleado -- id_empleado - id_persona - activo) <- (Persona -- id_persona - nombre - apellido) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**34. Consultar la ficha de un empleado**  
`GET /personal/{id_empleado}`

```
(DUENO / RECEPCIONISTA) -> (id_empleado) <- (Ficha del empleado con su rol y telefono principal, o empleado inexistente) --- (34. Consultar la ficha de un empleado) <- (Empleado -- id_empleado - id_persona - id_sede - legajo - fecha_ingreso - fecha_egreso - activo) <- (Persona -- id_persona - dni - nombre - apellido - email) <- (Telefono -- id_telefono - id_persona - numero - principal) <- (Entrenador -- id_empleado - titulo - especialidad - matricula) <- (Nutricionista -- id_empleado - titulo - matricula) <- (Recepcionista -- id_empleado - id_franja_laboral) <- (Profesor -- id_empleado - titulo - especialidad) <- (Franja_Laboral -- id_franja_laboral - nombre) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**35. Editar un empleado y su rol**  
`PUT /personal/{id_empleado}`

```
(DUENO) -> (Datos del empleado) <- (Empleado actualizado; o empleado inexistente, email ya usado por otra persona, cambio de rol bloqueado por tener rutinas o dietas a su nombre, o cambio de rol desde profesor que falla al borrar su ficha por tener actividades, horarios o turnos a su nombre) --- (35. Editar un empleado y su rol) -> (Persona -- nombre - apellido - email) -> (Telefono -- id_persona - numero - tipo - principal) -> (Entrenador -- id_empleado - titulo - especialidad - matricula) -> (Nutricionista -- id_empleado - titulo - matricula) -> (Recepcionista -- id_empleado - id_franja_laboral) -> (Profesor -- id_empleado - titulo - especialidad) <- (Empleado -- id_empleado - id_persona - id_sede - legajo - fecha_ingreso - fecha_egreso - activo) <- (Persona -- id_persona - dni - nombre - apellido - email) <- (Telefono -- id_telefono - id_persona - numero - principal) <- (Entrenador -- id_entrenador - id_empleado - titulo - especialidad - matricula) <- (Nutricionista -- id_nutricionista - id_empleado - titulo - matricula) <- (Recepcionista -- id_empleado - id_franja_laboral) <- (Profesor -- id_empleado - titulo - especialidad) <- (Rutina -- id_rutina - id_entrenador) <- (Dieta -- id_dieta - id_nutricionista) <- (Franja_Laboral -- id_franja_laboral - nombre) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**36. Dar de baja a un empleado**  
`POST /personal/{id_empleado}/baja`

```
(DUENO) -> (Datos de la baja del empleado) <- (Empleado dado de baja con su cuenta desactivada y sus actividades desasignadas; o empleado inexistente, ya estaba de baja o baja de si mismo rechazada) --- (36. Dar de baja a un empleado) -> (Empleado -- activo - fecha_egreso) -> (Usuario -- activo) -> (Profesor_Actividad -- id_profesor - id_actividad) <- (Empleado -- id_empleado - id_persona - id_sede - legajo - fecha_ingreso - fecha_egreso - activo) <- (Persona -- id_persona - dni - nombre - apellido - email) <- (Telefono -- id_telefono - id_persona - numero - principal) <- (Profesor -- id_profesor - id_empleado - titulo - especialidad) <- (Entrenador -- id_empleado - titulo - especialidad - matricula) <- (Nutricionista -- id_empleado - titulo - matricula) <- (Recepcionista -- id_empleado - id_franja_laboral) <- (Franja_Laboral -- id_franja_laboral - nombre) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**37. Reactivar a un empleado**  
`POST /personal/{id_empleado}/reactivar`

```
(DUENO) -> (id_empleado) <- (Empleado reactivado con su acceso devuelto, empleado inexistente o ya estaba activo) --- (37. Reactivar a un empleado) -> (Empleado -- activo - fecha_egreso) -> (Usuario -- activo) <- (Empleado -- id_empleado - id_persona - id_sede - legajo - fecha_ingreso - fecha_egreso - activo) <- (Persona -- id_persona - dni - nombre - apellido - email) <- (Telefono -- id_telefono - id_persona - numero - principal) <- (Entrenador -- id_empleado - titulo - especialidad - matricula) <- (Nutricionista -- id_empleado - titulo - matricula) <- (Recepcionista -- id_empleado - id_franja_laboral) <- (Profesor -- id_empleado - titulo - especialidad) <- (Franja_Laboral -- id_franja_laboral - nombre) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```


## Usuarios y cuentas de acceso

**38. Listar las cuentas de acceso**  
`GET /usuarios`

```
(DUENO / RECEPCIONISTA) -> (Pedido de consulta) <- (Listado de cuentas con sus roles derivados, su estado y su bloqueo, o acceso denegado) --- (38. Listar las cuentas de acceso) <- (Usuario -- id_usuario - id_persona - username - activo - bloqueado - debe_cambiar_password - ultimo_acceso) <- (Persona -- id_persona - dni - nombre - apellido - email) <- (Telefono -- id_telefono - id_persona - numero - principal) <- (Dueno -- id_dueno - id_persona) <- (Socio -- id_socio - id_persona) <- (Empleado -- id_empleado - id_persona) <- (Entrenador -- id_entrenador - id_empleado) <- (Nutricionista -- id_nutricionista - id_empleado) <- (Recepcionista -- id_recepcionista - id_empleado) <- (Profesor -- id_profesor - id_empleado)
```

**39. Crear la cuenta de acceso de una persona ya cargada**  
`POST /usuarios`

```
(DUENO / RECEPCIONISTA) -> (id_persona) <- (Cuenta creada con credenciales temporales de un solo uso; o persona inexistente, ya tenia cuenta, sin ningun rol que habilite el acceso o cuenta de dueno creada por quien no es dueno) --- (39. Crear la cuenta de acceso de una persona ya cargada) -> (Usuario -- id_persona - username - password_hash - debe_cambiar_password - activo) <- (Persona -- id_persona - nombre - apellido - email) <- (Usuario -- id_usuario - id_persona - username - activo - bloqueado - debe_cambiar_password) <- (Dueno -- id_dueno - id_persona) <- (Socio -- id_socio - id_persona) <- (Empleado -- id_empleado - id_persona) <- (Entrenador -- id_entrenador - id_empleado) <- (Nutricionista -- id_nutricionista - id_empleado) <- (Recepcionista -- id_recepcionista - id_empleado) <- (Profesor -- id_profesor - id_empleado)
```

**40. Listar las personas sin cuenta de acceso**  
`GET /usuarios/personas-sin-cuenta`

```
(DUENO / RECEPCIONISTA) -> (Pedido de consulta) <- (Personas con algun rol de sesion y todavia sin cuenta, o acceso denegado) --- (40. Listar las personas sin cuenta de acceso) <- (Persona -- id_persona - dni - nombre - apellido - email) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password) <- (Dueno -- id_dueno - id_persona) <- (Socio -- id_socio - id_persona) <- (Empleado -- id_empleado - id_persona) <- (Entrenador -- id_entrenador - id_empleado) <- (Nutricionista -- id_nutricionista - id_empleado) <- (Recepcionista -- id_recepcionista - id_empleado) <- (Profesor -- id_profesor - id_empleado) <- (Telefono -- id_telefono - id_persona - numero - principal)
```

**41. Editar el usuario y el email de una cuenta**  
`PUT /usuarios/{id_usuario}`

```
(DUENO / RECEPCIONISTA) -> (Datos de la cuenta) <- (Cuenta actualizada; o cuenta inexistente, cuenta propia de alguien que no es dueno, cuenta de un dueno, nombre de usuario vacio, nombre de usuario ya en uso o email ya registrado para otra persona) --- (41. Editar el usuario y el email de una cuenta) -> (Usuario -- username) -> (Persona -- email) <- (Usuario -- id_usuario - id_persona - username - activo - bloqueado - debe_cambiar_password - ultimo_acceso) <- (Persona -- id_persona - dni - nombre - apellido - email) <- (Telefono -- id_telefono - id_persona - numero - principal) <- (Dueno -- id_dueno - id_persona) <- (Socio -- id_socio - id_persona) <- (Empleado -- id_empleado - id_persona) <- (Entrenador -- id_entrenador - id_empleado) <- (Nutricionista -- id_nutricionista - id_empleado) <- (Recepcionista -- id_recepcionista - id_empleado) <- (Profesor -- id_profesor - id_empleado)
```

**42. Borrar una cuenta de acceso**  
`DELETE /usuarios/{id_usuario}`

```
(DUENO / RECEPCIONISTA) -> (id_usuario) <- (Cuenta borrada y sus fichajes manuales desvinculados, quedando la persona y su historial; o cuenta inexistente, cuenta propia, cuenta de un dueno, ultima cuenta de dueno del sistema o acceso denegado) --- (42. Borrar una cuenta de acceso) -> (Asistencia -- id_registrado_por) -> (Usuario -- id_usuario - id_persona - username - password_hash - debe_cambiar_password - ultimo_acceso - intentos_fallidos - bloqueado - activo) <- (Usuario -- id_usuario - id_persona - username - activo - bloqueado - debe_cambiar_password) <- (Persona -- id_persona - nombre - apellido) <- (Dueno -- id_dueno - id_persona) <- (Socio -- id_socio - id_persona) <- (Empleado -- id_empleado - id_persona) <- (Entrenador -- id_entrenador - id_empleado) <- (Nutricionista -- id_nutricionista - id_empleado) <- (Recepcionista -- id_recepcionista - id_empleado) <- (Profesor -- id_profesor - id_empleado) <- (Asistencia -- id_asistencia - id_registrado_por)
```

**43. Desbloquear una cuenta sin tocar su contrasena**  
`POST /usuarios/{id_usuario}/desbloquear`

```
(DUENO / RECEPCIONISTA) -> (id_usuario) <- (Cuenta desbloqueada con su contrasena intacta; o cuenta inexistente, cuenta de un dueno o cuenta que no estaba bloqueada) --- (43. Desbloquear una cuenta sin tocar su contrasena) -> (Usuario -- bloqueado - intentos_fallidos) <- (Usuario -- id_usuario - id_persona - username - activo - bloqueado - intentos_fallidos - debe_cambiar_password - ultimo_acceso) <- (Persona -- id_persona - dni - nombre - apellido - email) <- (Telefono -- id_telefono - id_persona - numero - principal) <- (Dueno -- id_dueno - id_persona) <- (Socio -- id_socio - id_persona) <- (Empleado -- id_empleado - id_persona) <- (Entrenador -- id_entrenador - id_empleado) <- (Nutricionista -- id_nutricionista - id_empleado) <- (Recepcionista -- id_recepcionista - id_empleado) <- (Profesor -- id_profesor - id_empleado)
```

**44. Resetear la contrasena de una cuenta**  
`POST /usuarios/{id_usuario}/resetear-password`

```
(DUENO / RECEPCIONISTA) -> (id_usuario) <- (Contrasena temporal generada, cambio obligatorio activado y cuenta desbloqueada; o cuenta inexistente, cuenta de un dueno o acceso denegado) --- (44. Resetear la contrasena de una cuenta) -> (Usuario -- password_hash - debe_cambiar_password - bloqueado - intentos_fallidos) <- (Usuario -- id_usuario - id_persona - username - activo - bloqueado - debe_cambiar_password) <- (Persona -- id_persona - nombre - apellido - email) <- (Dueno -- id_dueno - id_persona) <- (Socio -- id_socio - id_persona) <- (Empleado -- id_empleado - id_persona) <- (Entrenador -- id_entrenador - id_empleado) <- (Nutricionista -- id_nutricionista - id_empleado) <- (Recepcionista -- id_recepcionista - id_empleado) <- (Profesor -- id_profesor - id_empleado)
```

**45. Activar o desactivar una cuenta de acceso**  
`POST /usuarios/{id_usuario}/toggle-estado`

```
(DUENO / RECEPCIONISTA) -> (Estado destino de la cuenta) <- (Cuenta activada o desactivada y desbloqueada; o cuenta inexistente, cuenta propia, cuenta de un dueno o persona dada de baja como empleado) --- (45. Activar o desactivar una cuenta de acceso) -> (Usuario -- activo - bloqueado - intentos_fallidos) <- (Usuario -- id_usuario - id_persona - username - activo - bloqueado - debe_cambiar_password - ultimo_acceso) <- (Persona -- id_persona - dni - nombre - apellido - email) <- (Telefono -- id_telefono - id_persona - numero - principal) <- (Empleado -- id_empleado - id_persona - activo) <- (Dueno -- id_dueno - id_persona) <- (Socio -- id_socio - id_persona) <- (Entrenador -- id_entrenador - id_empleado) <- (Nutricionista -- id_nutricionista - id_empleado) <- (Recepcionista -- id_recepcionista - id_empleado) <- (Profesor -- id_profesor - id_empleado)
```


## Cobros y pagos

**46. Cobrar una cuota en el mostrador**  
`POST /cobros`

```
(DUENO / RECEPCIONISTA) -> (Datos del cobro) <- (Cobro registrado con la membresia nueva y el abono de actividad opcional, o rechazo porque el socio no existe, por periodo en curso, baja programada o cuota en pausa, porque el plan de membresia o el de actividad no existe o esta dado de baja, porque la promocion no existe, esta apagada o esta fuera de fecha, porque la promocion es de otra sede, por comprobante duplicado, por monto manual sin ser dueno, o por mandar monto manual y promocion a la vez) --- (46. Cobrar una cuota en el mostrador) -> (Membresia -- id_socio - id_tipo_membresia - precio_pactado - fecha_inicio - fecha_vencimiento - estado) -> (Pago -- id_socio - id_membresia - id_tipo_membresia - id_inscripcion - id_sede - metodo - monto - fecha_pago - periodo_desde - periodo_hasta - es_adelanto - estado - numero_comprobante - id_promocion - monto_descuento) -> (Inscripcion_Actividad -- id_socio - id_plan_actividad - precio_pactado - fecha_inicio - fecha_vencimiento - estado) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password - id_persona) <- (Socio -- id_socio - id_persona - id_sede) <- (Persona -- nombre - apellido) <- (Baja -- id_socio - fecha_baja - pendiente) <- (Membresia -- id_membresia - id_socio - estado - fecha_inicio - fecha_vencimiento) <- (Tipo_Membresia -- id_tipo_membresia - nombre - duracion_dias - precio_actual - activo) <- (Promocion -- id_promocion - nombre - porcentaje_descuento - fecha_inicio - fecha_fin - activo - id_sede) <- (Pago -- numero_comprobante) <- (Plan_Actividad -- id_plan_actividad - id_actividad - nombre - tipo_limite - cantidad - precio - activo) <- (Actividad -- nombre)
```

**47. Anular un pago**  
`POST /cobros/pagos/{id_pago}/anular`

```
(DUENO / RECEPCIONISTA) -> (id_pago) <- (Pago anulado y la membresia que habilitaba cancelada, o el pago no existe o ya estaba anulado) --- (47. Anular un pago) -> (Pago -- estado - fecha_cancelacion) -> (Membresia -- estado) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password - id_persona) <- (Pago -- id_pago - id_socio - id_membresia - monto - metodo - fecha_pago - periodo_desde - periodo_hasta - estado - numero_comprobante) <- (Membresia -- id_membresia - estado) <- (Socio -- id_socio - id_persona) <- (Persona -- nombre - apellido)
```

**48. Consultar el estado de cuenta de un socio**  
`GET /cobros/socio/{id_socio}`

```
(DUENO / RECEPCIONISTA) -> (id_socio) <- (Estado de cuenta con la membresia vigente, los ultimos 5 pagos y desde cuando se puede renovar, o el socio no existe) --- (48. Consultar el estado de cuenta de un socio) -> (Membresia -- estado) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password - id_persona) <- (Socio -- id_socio - id_persona - numero_socio) <- (Persona -- nombre - apellido) <- (Membresia -- id_membresia - id_socio - id_tipo_membresia - precio_pactado - fecha_inicio - fecha_vencimiento - estado) <- (Tipo_Membresia -- nombre) <- (Pago -- id_pago - id_socio - monto - metodo - fecha_pago - periodo_desde - periodo_hasta - estado - numero_comprobante) <- (Baja -- id_socio - fecha_baja - pendiente)
```

**49. Listar los planes de membresia**  
`GET /cobros/tipos-membresia`

```
(DUENO / RECEPCIONISTA) -> (Pedido de consulta) <- (Catalogo de planes de membresia ordenado por precio, o acceso denegado) --- (49. Listar los planes de membresia) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password - id_persona) <- (Tipo_Membresia -- id_tipo_membresia - nombre - descripcion - duracion_dias - precio_actual - activo)
```

**50. Crear un plan de membresia**  
`POST /cobros/tipos-membresia`

```
(DUENO) -> (Datos del plan de membresia) <- (Plan creado, nombre duplicado o accion no permitida) --- (50. Crear un plan de membresia) -> (Tipo_Membresia -- nombre - descripcion - duracion_dias - precio_actual - activo) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password - id_persona) <- (Tipo_Membresia -- id_tipo_membresia - nombre)
```

**51. Acreditar el aviso de pago de Mercado Pago**  
`POST /webhooks/mercadopago`

```
(SOCIO) -> (Aviso de pago de Mercado Pago) <- (Pago acreditado con su membresia, pago confirmado sin membresia por tener un periodo en curso o baja programada, pago cancelado, o aviso descartado por firma invalida, duplicado, monto que no coincide, consulta fallida o pago inexistente) --- (51. Acreditar el aviso de pago de Mercado Pago) -> (Pago -- estado - numero_comprobante - fecha_cancelacion - id_membresia) -> (Membresia -- id_socio - id_tipo_membresia - precio_pactado - fecha_inicio - fecha_vencimiento - estado) <- (Pago -- id_pago - id_socio - monto - estado - numero_comprobante - id_membresia - id_tipo_membresia) <- (Tipo_Membresia -- id_tipo_membresia - duracion_dias - precio_actual - activo) <- (Membresia -- id_socio - estado - fecha_inicio - fecha_vencimiento) <- (Baja -- id_socio - pendiente - fecha_baja)
```


## Asistencia

**52. Fichar el ingreso de un socio**  
`POST /asistencia/fichar`

```
(DUENO / RECEPCIONISTA) -> (Datos del fichaje) <- (Ingreso registrado con la clase acreditada, con aviso de turno perdido, de cuota vencida o de socio dado de baja, o rechazo por identificacion ambigua, tarjeta no asignada o socio inexistente) --- (52. Fichar el ingreso de un socio) -> (Asistencia -- id_socio - id_sede - id_reserva - fecha_hora_ingreso - metodo_registro - id_registrado_por) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password - id_persona) <- (Socio -- id_socio - id_persona - id_sede - codigo_rfid - numero_socio - activo) <- (Persona -- nombre - apellido) <- (Membresia -- id_socio - estado - fecha_inicio - fecha_vencimiento) <- (Reserva -- id_reserva - id_socio - id_turno - estado) <- (Turno -- id_turno - id_actividad - fecha - hora - estado) <- (Actividad -- id_actividad - nombre - minutos_tolerancia) <- (Asistencia -- id_asistencia - id_socio - id_reserva - fecha_hora_ingreso)
```

**53. Consultar los ingresos del dia**  
`GET /asistencia/hoy`

```
(DUENO / RECEPCIONISTA) -> (Pedido de consulta) <- (Lista de los ingresos del dia, del mas reciente al mas viejo y numerados por socio, o acceso denegado) --- (53. Consultar los ingresos del dia) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password - id_persona) <- (Asistencia -- id_asistencia - id_socio - fecha_hora_ingreso - fecha_hora_egreso - metodo_registro) <- (Socio -- id_socio - id_persona - numero_socio) <- (Persona -- nombre - apellido)
```

**54. Consultar el historial de ingresos de un socio**  
`GET /asistencia/socio/{id_socio}`

```
(DUENO / RECEPCIONISTA) -> (Pedido de historial de un socio) <- (Ultimos ingresos del socio, del mas reciente al mas viejo, tantos como pida el limite de 30 por defecto y nunca mas de 200, lista vacia si nunca ficho, o acceso denegado) --- (54. Consultar el historial de ingresos de un socio) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password - id_persona) <- (Asistencia -- id_asistencia - id_socio - fecha_hora_ingreso - fecha_hora_egreso - metodo_registro) <- (Socio -- id_socio - id_persona - numero_socio) <- (Persona -- nombre - apellido)
```

**55. Deshacer un fichaje del dia**  
`DELETE /asistencia/{id_asistencia}`

```
(DUENO / RECEPCIONISTA) -> (id_asistencia) <- (Ingreso borrado, o el ingreso no existe o no es de hoy) --- (55. Deshacer un fichaje del dia) -> (Asistencia -- id_asistencia - id_socio - id_sede - id_reserva - fecha_hora_ingreso - fecha_hora_egreso - metodo_registro - id_registrado_por) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password - id_persona) <- (Asistencia -- id_asistencia - fecha_hora_ingreso)
```

**56. Registrar el egreso de un ingreso**  
`POST /asistencia/{id_asistencia}/salida`

```
(DUENO / RECEPCIONISTA) -> (id_asistencia) <- (Egreso registrado, o el ingreso no existe o ya tenia la salida cargada) --- (56. Registrar el egreso de un ingreso) -> (Asistencia -- fecha_hora_egreso) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password - id_persona) <- (Asistencia -- id_asistencia - id_socio - fecha_hora_ingreso - fecha_hora_egreso - metodo_registro) <- (Socio -- id_socio - id_persona - numero_socio) <- (Persona -- nombre - apellido)
```


## Recepcion

**57. Buscar un socio por DNI en el mostrador**  
`GET /recepcion/buscar`

```
(DUENO / RECEPCIONISTA) -> (dni) <- (Hasta 10 socios con su estado de cuota, su alerta, si se le puede cobrar la cuota y su proximo turno; lista vacia si ningun DNI coincide, o rechazo si el DNI tiene menos de 2 caracteres, o acceso denegado) --- (57. Buscar un socio por DNI en el mostrador) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password - id_persona) <- (Socio -- id_socio - id_persona - numero_socio - codigo_rfid - activo) <- (Persona -- id_persona - dni - nombre - apellido) <- (Membresia -- id_socio - estado - fecha_vencimiento) <- (Baja -- id_socio - fecha_baja - pendiente) <- (Reserva -- id_reserva - id_turno - id_socio - estado - fecha_reserva) <- (Turno -- id_turno - id_actividad - fecha - hora - estado - cupo_maximo - id_profesor) <- (Actividad -- id_actividad - nombre - minutos_tolerancia) <- (Asistencia -- id_asistencia - id_reserva) <- (Profesor -- id_profesor - id_empleado) <- (Empleado -- id_empleado - id_persona)
```

**58. Abrir el panel de recepcion**  
`GET /recepcion/panel`

```
(DUENO / RECEPCIONISTA) -> (Pedido de consulta) <- (Panel con los turnos proximos, los vencidos recientes, los anotados de cada turno con su estado y su alerta, y los totales del dia; listas vacias y totales en cero si no hay turnos en la ventana, o acceso denegado) --- (58. Abrir el panel de recepcion) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password - id_persona) <- (Turno -- id_turno - id_actividad - fecha - hora - estado - cupo_maximo - id_profesor) <- (Actividad -- id_actividad - nombre - minutos_tolerancia) <- (Reserva -- id_reserva - id_turno - id_socio - id_inscripcion - estado - fecha_reserva) <- (Asistencia -- id_asistencia - id_reserva - fecha_hora_ingreso) <- (Socio -- id_socio - id_persona - activo) <- (Persona -- nombre - apellido - dni) <- (Membresia -- id_socio - estado - fecha_vencimiento) <- (Baja -- id_socio - fecha_baja - pendiente) <- (Profesor -- id_profesor - id_empleado) <- (Empleado -- id_empleado - id_persona)
```

**59. Ver el detalle de un turno del panel**  
`GET /recepcion/turnos/{id_turno}`

```
(DUENO / RECEPCIONISTA) -> (id_turno) <- (El turno con su lista completa de anotados, incluida la sala abierta, o el turno no existe) --- (59. Ver el detalle de un turno del panel) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password - id_persona) <- (Turno -- id_turno - id_actividad - fecha - hora - estado - cupo_maximo - id_profesor) <- (Actividad -- id_actividad - nombre - minutos_tolerancia) <- (Reserva -- id_reserva - id_turno - id_socio - id_inscripcion - estado - fecha_reserva) <- (Asistencia -- id_asistencia - id_reserva) <- (Socio -- id_socio - id_persona - activo) <- (Persona -- nombre - apellido - dni) <- (Membresia -- id_socio - estado - fecha_vencimiento) <- (Baja -- id_socio - fecha_baja - pendiente) <- (Profesor -- id_profesor - id_empleado) <- (Empleado -- id_empleado - id_persona)
```


## Actividades, turnos y horarios

**60. Consultar el catalogo de actividades**  
`GET /actividades`

```
(DUENO / RECEPCIONISTA) -> (Pedido de consulta) <- (Catalogo de actividades con sus abonos o acceso denegado) --- (60. Consultar el catalogo de actividades) <- (Actividad -- id_actividad - nombre - descripcion - cupo_default - horas_anticipacion_cancelacion - minutos_tolerancia - activo) <- (Plan_Actividad -- id_plan_actividad - id_actividad - nombre - tipo_limite - cantidad - precio - activo)
```

**61. Dar de alta una actividad**  
`POST /actividades`

```
(DUENO / RECEPCIONISTA) -> (Datos de la actividad) <- (Actividad creada o nombre duplicado) --- (61. Dar de alta una actividad) -> (Actividad -- nombre - descripcion - cupo_default - horas_anticipacion_cancelacion - minutos_tolerancia - activo) <- (Actividad -- id_actividad - nombre) <- (Plan_Actividad -- id_plan_actividad - id_actividad - nombre - tipo_limite - cantidad - precio - activo)
```

**62. Listar los horarios semanales de las actividades**  
`GET /actividades/horarios`

```
(DUENO / RECEPCIONISTA) -> (Pedido de consulta) <- (Grilla semanal de horarios con su profesor y cuantos turnos futuros tiene cada uno) --- (62. Listar los horarios semanales de las actividades) <- (Horario_Actividad -- id_horario_actividad - id_sede - id_actividad - dia_semana - hora - cupo - id_profesor - vigente_desde - vigente_hasta - activo) <- (Actividad -- id_actividad - nombre) <- (Profesor -- id_profesor - id_empleado) <- (Empleado -- id_empleado - id_persona) <- (Persona -- id_persona - nombre - apellido) <- (Turno -- id_turno - id_horario_actividad - fecha - estado)
```

**63. Cargar el horario semanal de una actividad y generar sus turnos**  
`POST /actividades/horarios`

```
(DUENO / RECEPCIONISTA) -> (Datos del horario semanal) <- (Horario creado con sus turnos de las proximas 4 semanas, o rechazo por actividad inexistente, profesor no asignado o dado de baja, u horario repetido) --- (63. Cargar el horario semanal de una actividad y generar sus turnos) -> (Horario_Actividad -- id_sede - id_actividad - dia_semana - hora - cupo - id_profesor - vigente_desde - vigente_hasta - activo) -> (Turno -- id_sede - id_actividad - fecha - hora - cupo_maximo - estado - id_profesor - id_entrenador_a_cargo - id_horario_actividad) <- (Actividad -- id_actividad - nombre) <- (Profesor_Actividad -- id_profesor - id_actividad) <- (Profesor -- id_profesor - id_empleado) <- (Empleado -- id_empleado - activo - id_persona) <- (Horario_Actividad -- id_horario_actividad - id_sede - id_actividad - dia_semana - hora - cupo - id_profesor - id_entrenador_a_cargo - vigente_desde - vigente_hasta - activo) <- (Turno -- id_turno - id_sede - id_actividad - fecha - hora) <- (Persona -- id_persona - nombre - apellido)
```

**64. Activar o desactivar un horario semanal**  
`POST /actividades/horarios/{id_horario}/estado`

```
(DUENO / RECEPCIONISTA) -> (id_horario, activo y si cancela los turnos futuros) <- (Horario activado o desactivado, con sus turnos futuros sin anotados cancelados, u horario inexistente) --- (64. Activar o desactivar un horario semanal) -> (Horario_Actividad -- activo) -> (Turno -- estado - motivo_cancelacion) <- (Horario_Actividad -- id_horario_actividad - id_sede - id_actividad - dia_semana - hora - cupo - id_profesor - vigente_desde - vigente_hasta - activo) <- (Turno -- id_turno - id_horario_actividad - fecha - estado) <- (Reserva -- id_reserva - id_turno - estado) <- (Actividad -- id_actividad - nombre) <- (Profesor -- id_profesor - id_empleado) <- (Empleado -- id_empleado - id_persona) <- (Persona -- id_persona - nombre - apellido)
```

**65. Cambiar o sacar el profesor de un horario ya creado**  
`PUT /actividades/horarios/{id_horario}/profesor`

```
(DUENO / RECEPCIONISTA) -> (id_horario e id_profesor) <- (Profesor del horario cambiado o sacado y arrastrado a los turnos futuros, horario inexistente, profesor no habilitado para la actividad, o sin cambios) --- (65. Cambiar o sacar el profesor de un horario ya creado) -> (Horario_Actividad -- id_profesor) -> (Turno -- id_profesor) <- (Horario_Actividad -- id_horario_actividad - id_actividad - id_sede - dia_semana - hora - cupo - id_profesor - vigente_desde - vigente_hasta - activo) <- (Profesor_Actividad -- id_profesor - id_actividad) <- (Profesor -- id_profesor - id_empleado) <- (Empleado -- id_empleado - activo - id_persona) <- (Actividad -- id_actividad - nombre) <- (Turno -- id_turno - id_horario_actividad - fecha - estado) <- (Persona -- id_persona - nombre - apellido)
```

**66. Consultar los abonos de actividad de un socio**  
`GET /actividades/inscripciones/socio/{id_socio}`

```
(DUENO / RECEPCIONISTA) -> (id_socio) <- (Abonos de actividad del socio con sus clases restantes, o lista vacia) --- (66. Consultar los abonos de actividad de un socio) <- (Inscripcion_Actividad -- id_inscripcion - id_socio - id_plan_actividad - precio_pactado - fecha_inicio - fecha_vencimiento - estado) <- (Plan_Actividad -- id_plan_actividad - id_actividad - nombre - tipo_limite - cantidad) <- (Actividad -- id_actividad - nombre) <- (Socio -- id_socio - id_persona) <- (Persona -- id_persona - nombre - apellido) <- (Reserva -- id_reserva - id_inscripcion - estado)
```

**67. Cancelar un abono de actividad y sus clases futuras**  
`POST /actividades/inscripciones/{id_inscripcion}/cancelar`

```
(DUENO / RECEPCIONISTA) -> (id_inscripcion) <- (Abono cancelado junto con sus reservas futuras, inscripcion inexistente o ya cancelada) --- (67. Cancelar un abono de actividad y sus clases futuras) -> (Inscripcion_Actividad -- estado) -> (Reserva -- estado - fecha_cancelacion) <- (Inscripcion_Actividad -- id_inscripcion - id_socio - id_plan_actividad - precio_pactado - fecha_inicio - fecha_vencimiento - estado) <- (Reserva -- id_reserva - id_inscripcion - id_turno - estado) <- (Turno -- id_turno - fecha) <- (Plan_Actividad -- id_plan_actividad - id_actividad - nombre - tipo_limite - cantidad) <- (Actividad -- id_actividad - nombre) <- (Socio -- id_socio - id_persona) <- (Persona -- id_persona - nombre - apellido)
```

**68. Editar un abono de actividad**  
`PUT /actividades/planes/{id_plan}`

```
(DUENO / RECEPCIONISTA) -> (Datos del abono) <- (Abono editado, abono inexistente o cantidad imposible para el tipo de limite) --- (68. Editar un abono de actividad) -> (Plan_Actividad -- nombre - tipo_limite - cantidad - precio) <- (Plan_Actividad -- id_plan_actividad - id_actividad)
```

**69. Cobrar un abono de actividad a un socio**  
`POST /actividades/planes/{id_plan}/comprar`

```
(DUENO / RECEPCIONISTA) -> (Compra del abono de actividad) <- (Abono comprado con su pago, o rechazo por plan inexistente, plan o actividad dados de baja, socio inexistente, sin membresia activa o cuota vencida, abono duplicado, o cuota que no cubre el mes del abono) --- (69. Cobrar un abono de actividad a un socio) -> (Inscripcion_Actividad -- id_socio - id_plan_actividad - precio_pactado - fecha_inicio - fecha_vencimiento - estado) -> (Pago -- id_socio - id_inscripcion - id_sede - metodo - monto - fecha_pago - periodo_desde - periodo_hasta - estado) <- (Plan_Actividad -- id_plan_actividad - id_actividad - nombre - tipo_limite - cantidad - precio - activo) <- (Actividad -- id_actividad - nombre - activo) <- (Socio -- id_socio - id_persona - id_sede) <- (Persona -- id_persona - nombre - apellido) <- (Membresia -- id_socio - estado - fecha_vencimiento) <- (Inscripcion_Actividad -- id_inscripcion - id_socio - id_plan_actividad - estado - fecha_vencimiento) <- (Reserva -- id_reserva - id_inscripcion - estado)
```

**70. Dar de baja o reactivar un abono de actividad**  
`POST /actividades/planes/{id_plan}/toggle-estado`

```
(DUENO / RECEPCIONISTA) -> (id_plan y estado deseado) <- (Abono dado de baja o reactivado, o abono inexistente) --- (70. Dar de baja o reactivar un abono de actividad) -> (Plan_Actividad -- activo) <- (Plan_Actividad -- id_plan_actividad - id_actividad - nombre - tipo_limite - cantidad - precio - activo)
```

**71. Consultar el plantel de profesores**  
`GET /actividades/profesores`

```
(DUENO / RECEPCIONISTA) -> (Pedido de consulta) <- (Profesores activos del plantel o acceso denegado) --- (71. Consultar el plantel de profesores) <- (Profesor -- id_profesor - id_empleado - titulo - especialidad) <- (Empleado -- id_empleado - id_persona - legajo - activo) <- (Persona -- nombre - apellido - dni)
```

**72. Cancelar la reserva de un socio y promover la lista de espera**  
`POST /actividades/reservas/{id_reserva}/cancelar`

```
(DUENO / RECEPCIONISTA) -> (id_reserva) <- (Reserva cancelada con el primero de la lista de espera promovido y avisado, o rechazo por reserva inexistente o ya cancelada) --- (72. Cancelar la reserva de un socio y promover la lista de espera) -> (Reserva -- estado - fecha_cancelacion) <- (Reserva -- id_reserva - id_turno - id_socio - id_inscripcion - estado - fecha_reserva) <- (Turno -- id_turno - estado - fecha - hora - cupo_maximo - id_actividad) <- (Actividad -- id_actividad - nombre - horas_anticipacion_cancelacion) <- (Socio -- id_socio - id_persona) <- (Persona -- nombre - apellido - email) <- (Inscripcion_Actividad -- id_inscripcion - id_plan_actividad) <- (Plan_Actividad -- id_plan_actividad - tipo_limite - cantidad)
```

**73. Chequear si un socio puede comprar un abono de actividad hoy**  
`GET /actividades/socio/{id_socio}/puede-comprar`

```
(DUENO / RECEPCIONISTA) -> (id_socio) <- (Si puede comprar un abono hoy, con el motivo y las fechas de vencimiento, o socio inexistente) --- (73. Chequear si un socio puede comprar un abono de actividad hoy) <- (Socio -- id_socio) <- (Membresia -- id_socio - estado - fecha_vencimiento)
```

**74. Ver la agenda de turnos de los proximos dias**  
`GET /actividades/turnos`

```
(DUENO / RECEPCIONISTA) -> (Rango de fechas desde y hasta) <- (Agenda de turnos del rango con su ocupacion, lugares libres, profesor y motivo de cancelacion) --- (74. Ver la agenda de turnos de los proximos dias) <- (Turno -- id_turno - id_actividad - fecha - hora - cupo_maximo - estado - motivo_cancelacion - id_profesor) <- (Reserva -- id_reserva - id_turno - estado) <- (Actividad -- id_actividad - nombre) <- (Profesor -- id_profesor - id_empleado) <- (Empleado -- id_empleado - id_persona) <- (Persona -- id_persona - nombre - apellido)
```

**75. Programar una clase**  
`POST /actividades/turnos`

```
(DUENO / RECEPCIONISTA) -> (Datos del turno) <- (Clase programada, o rechazo por actividad, sede o profesor inexistente o por fecha pasada) --- (75. Programar una clase) -> (Turno -- id_sede - id_actividad - fecha - hora - cupo_maximo - id_profesor - estado) <- (Actividad -- id_actividad - nombre - cupo_default) <- (Sede -- id_sede) <- (Profesor -- id_profesor - id_empleado) <- (Empleado -- id_empleado - id_persona) <- (Persona -- nombre - apellido) <- (Reserva -- id_turno - estado)
```

**76. Generar los turnos que falten a partir de los horarios**  
`POST /actividades/turnos/generar`

```
(DUENO / RECEPCIONISTA) -> (dias a generar) <- (Turnos creados hasta la fecha tope, o aviso de que ya estaban todos generados o de que no hay horarios cargados) --- (76. Generar los turnos que falten a partir de los horarios) -> (Turno -- id_sede - id_actividad - fecha - hora - cupo_maximo - estado - id_profesor - id_entrenador_a_cargo - id_horario_actividad) <- (Horario_Actividad -- id_horario_actividad - id_sede - id_actividad - dia_semana - hora - cupo - id_profesor - id_entrenador_a_cargo - vigente_desde - vigente_hasta - activo) <- (Turno -- id_turno - id_sede - id_actividad - fecha - hora)
```

**77. Cancelar una clase programada**  
`POST /actividades/turnos/{id_turno}/cancelar`

```
(DUENO / RECEPCIONISTA) -> (id_turno y motivo) <- (Clase cancelada con sus reservas RESERVADA devueltas como CANCELADA_GIMNASIO y las EN_ESPERA sin tocar, o rechazo por turno inexistente o ya cancelado) --- (77. Cancelar una clase programada) -> (Turno -- estado - motivo_cancelacion) -> (Reserva -- estado - fecha_cancelacion) <- (Turno -- id_turno - estado - fecha - hora - cupo_maximo - id_actividad - id_profesor) <- (Reserva -- id_reserva - id_turno - estado) <- (Actividad -- id_actividad - nombre) <- (Profesor -- id_profesor - id_empleado) <- (Empleado -- id_empleado - id_persona) <- (Persona -- nombre - apellido)
```

**78. Cobrar y anotar una clase suelta sin abono**  
`POST /actividades/turnos/{id_turno}/clase-suelta`

```
(DUENO / RECEPCIONISTA) -> (Compra de una clase suelta) <- (Clase suelta cobrada y el socio anotado al turno, o rechazo por turno inexistente o cancelado, socio inexistente, sin membresia activa o cuota vencida, socio ya anotado, clase completa, o actividad sin plan de clase suelta cargado) --- (78. Cobrar y anotar una clase suelta sin abono) -> (Pago -- id_socio - id_sede - metodo - monto - fecha_pago - periodo_desde - periodo_hasta - estado) -> (Reserva -- id_turno - id_socio - id_pago - fecha_reserva - estado) <- (Turno -- id_turno - id_actividad - id_sede - fecha - hora - cupo_maximo - estado) <- (Socio -- id_socio - id_persona - id_sede) <- (Persona -- id_persona - nombre - apellido) <- (Membresia -- id_socio - estado - fecha_vencimiento) <- (Reserva -- id_reserva - id_turno - id_socio - estado) <- (Plan_Actividad -- id_plan_actividad - id_actividad - tipo_limite - precio - activo) <- (Actividad -- id_actividad - nombre)
```

**79. Anotar a un socio en una clase**  
`POST /actividades/turnos/{id_turno}/reservar`

```
(DUENO / RECEPCIONISTA) -> (Datos de la reserva) <- (Socio anotado, anotado en lista de espera, o rechazo por turno inexistente o cancelado, socio inexistente, socio ya anotado, socio con una reserva previa en ese mismo turno por el indice unico de Reserva, sin abono activo o sin clases disponibles) --- (79. Anotar a un socio en una clase) -> (Reserva -- id_turno - id_socio - id_inscripcion - fecha_reserva - estado) -> (Inscripcion_Actividad -- estado) <- (Turno -- id_turno - estado - cupo_maximo - id_actividad - fecha - hora) <- (Reserva -- id_reserva - id_turno - id_socio - id_inscripcion - estado) <- (Socio -- id_socio - id_persona) <- (Persona -- nombre - apellido) <- (Actividad -- id_actividad - nombre) <- (Inscripcion_Actividad -- id_inscripcion - id_socio - id_plan_actividad - estado - fecha_vencimiento) <- (Plan_Actividad -- id_plan_actividad - id_actividad - nombre - tipo_limite - cantidad)
```

**80. Consultar los anotados de una clase**  
`GET /actividades/turnos/{id_turno}/reservas`

```
(DUENO / RECEPCIONISTA) -> (id_turno) <- (Lista de anotados a la clase, turno inexistente o acceso denegado) --- (80. Consultar los anotados de una clase) <- (Turno -- id_turno - id_actividad - fecha - hora) <- (Reserva -- id_reserva - id_turno - id_socio - id_inscripcion - estado) <- (Socio -- id_socio - id_persona) <- (Persona -- nombre - apellido) <- (Actividad -- id_actividad - nombre)
```

**81. Editar una actividad**  
`PUT /actividades/{id_actividad}`

```
(DUENO / RECEPCIONISTA) -> (Datos de la actividad) <- (Actividad editada, actividad inexistente o nombre duplicado) --- (81. Editar una actividad) -> (Actividad -- nombre - descripcion - cupo_default - horas_anticipacion_cancelacion - minutos_tolerancia) <- (Actividad -- id_actividad - nombre) <- (Plan_Actividad -- id_plan_actividad - id_actividad - nombre - tipo_limite - cantidad - precio - activo)
```

**82. Consultar los abonos de una actividad**  
`GET /actividades/{id_actividad}/planes`

```
(DUENO / RECEPCIONISTA) -> (id_actividad) <- (Abonos de la actividad ordenados por precio o actividad inexistente) --- (82. Consultar los abonos de una actividad) <- (Actividad -- id_actividad) <- (Plan_Actividad -- id_plan_actividad - id_actividad - nombre - tipo_limite - cantidad - precio - activo)
```

**83. Dar de alta un abono de actividad**  
`POST /actividades/{id_actividad}/planes`

```
(DUENO / RECEPCIONISTA) -> (Datos del abono) <- (Abono creado, actividad inexistente o cantidad imposible para el tipo de limite) --- (83. Dar de alta un abono de actividad) -> (Plan_Actividad -- id_actividad - nombre - tipo_limite - cantidad - precio - activo) <- (Actividad -- id_actividad)
```

**84. Listar los profesores habilitados de una actividad**  
`GET /actividades/{id_actividad}/profesores`

```
(DUENO / RECEPCIONISTA) -> (id_actividad) <- (Lista de profesores habilitados para esa actividad o actividad inexistente) --- (84. Listar los profesores habilitados de una actividad) <- (Actividad -- id_actividad - nombre) <- (Profesor_Actividad -- id_profesor - id_actividad) <- (Profesor -- id_profesor - id_empleado - titulo - especialidad) <- (Empleado -- id_empleado - id_persona - legajo) <- (Persona -- id_persona - nombre - apellido - dni)
```

**85. Habilitar a un profesor para dictar una actividad**  
`POST /actividades/{id_actividad}/profesores/{id_profesor}`

```
(DUENO / RECEPCIONISTA) -> (Actividad y profesor a vincular) <- (Profesor habilitado para la actividad, actividad o profesor inexistente, o profesor ya asignado) --- (85. Habilitar a un profesor para dictar una actividad) -> (Profesor_Actividad -- id_profesor - id_actividad) <- (Actividad -- id_actividad - nombre) <- (Profesor -- id_profesor - id_empleado - titulo - especialidad) <- (Profesor_Actividad -- id_profesor - id_actividad) <- (Empleado -- id_empleado - id_persona - legajo) <- (Persona -- id_persona - nombre - apellido - dni)
```

**86. Quitarle a un profesor la habilitacion para una actividad**  
`DELETE /actividades/{id_actividad}/profesores/{id_profesor}`

```
(DUENO / RECEPCIONISTA) -> (Actividad y profesor a desvincular) <- (Profesor desasignado de la actividad o no estaba asignado) --- (86. Quitarle a un profesor la habilitacion para una actividad) -> (Profesor_Actividad -- id_profesor - id_actividad) <- (Profesor_Actividad -- id_profesor - id_actividad)
```

**87. Dar de baja o reactivar una actividad**  
`POST /actividades/{id_actividad}/toggle-estado`

```
(DUENO / RECEPCIONISTA) -> (id_actividad y estado deseado) <- (Actividad dada de baja con sus turnos HABILITADOS de hoy en adelante cancelados y sus reservas RESERVADA devueltas como CANCELADA_GIMNASIO, actividad reactivada sin tocar turnos, o actividad inexistente) --- (87. Dar de baja o reactivar una actividad) -> (Actividad -- activo) -> (Turno -- estado - motivo_cancelacion) -> (Reserva -- estado - fecha_cancelacion) <- (Actividad -- id_actividad - nombre - activo) <- (Turno -- id_turno - id_actividad - fecha - estado) <- (Reserva -- id_reserva - id_turno - estado) <- (Plan_Actividad -- id_plan_actividad - id_actividad - nombre - tipo_limite - cantidad - precio - activo)
```


## Rutinas

**88. Consultar el catalogo de rutinas**  
`GET /rutinas`

```
(DUENO / RECEPCIONISTA / ENTRENADOR / NUTRICIONISTA) -> (Pedido de consulta) <- (Catalogo de rutinas con el permiso de edicion de cada una, o acceso denegado) --- (88. Consultar el catalogo de rutinas) <- (Rutina -- id_rutina - id_entrenador - nombre - objetivo - dias_por_semana - fecha_creacion - activo) <- (Asignacion_Rutina -- id_rutina - estado) <- (Entrenador -- id_entrenador - id_empleado) <- (Empleado -- id_empleado - id_persona) <- (Persona -- id_persona - nombre - apellido) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**89. Crear una rutina del catalogo con sus ejercicios**  
`POST /rutinas`

```
(DUENO / RECEPCIONISTA / ENTRENADOR) -> (Datos de la rutina) <- (Rutina creada con sus ejercicios, entrenador no elegido, rutina a nombre de otro entrenador, entrenador inexistente o dado de baja, o ejercicio inexistente) --- (89. Crear una rutina del catalogo con sus ejercicios) -> (Rutina -- id_rutina - id_entrenador - nombre - objetivo - dias_por_semana - activo - fecha_creacion) -> (Rutina_Ejercicio -- id_rutina_ejercicio - id_rutina - id_ejercicio - dia - orden - series - repeticiones - peso_sugerido - descanso_segundos - observaciones) <- (Empleado -- id_empleado - id_persona - activo) <- (Entrenador -- id_entrenador - id_empleado) <- (Ejercicio -- id_ejercicio - nombre - grupo_muscular - url_video) <- (Persona -- id_persona - nombre - apellido) <- (Asignacion_Rutina -- id_rutina - estado) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**90. Consultar el historial de rutinas de un socio**  
`GET /rutinas/asignaciones/socio/{id_socio}`

```
(DUENO / RECEPCIONISTA / ENTRENADOR / NUTRICIONISTA) -> (id_socio) <- (Historial de rutinas que el personal le asigno al socio, sin las rutinas propias del socio, lista vacia si no tiene ninguna, o acceso denegado) --- (90. Consultar el historial de rutinas de un socio) <- (Asignacion_Rutina -- id_asignacion_rutina - id_socio - id_rutina - fecha_inicio - fecha_fin - estado) <- (Rutina -- id_rutina - id_entrenador - nombre) <- (Socio -- id_socio - id_persona) <- (Persona -- id_persona - nombre - apellido) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**91. Consultar el catalogo de ejercicios**  
`GET /rutinas/ejercicios`

```
(DUENO / RECEPCIONISTA / ENTRENADOR / NUTRICIONISTA) -> (Pedido de consulta) <- (Catalogo de ejercicios o acceso denegado) --- (91. Consultar el catalogo de ejercicios) <- (Ejercicio -- id_ejercicio - nombre - grupo_muscular - descripcion - url_video - requiere_maquina) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**92. Dar de alta un ejercicio en el catalogo**  
`POST /rutinas/ejercicios`

```
(DUENO / RECEPCIONISTA / ENTRENADOR) -> (Datos del ejercicio) <- (Ejercicio agregado al catalogo, nombre duplicado o link que no es de YouTube) --- (92. Dar de alta un ejercicio en el catalogo) -> (Ejercicio -- id_ejercicio - nombre - grupo_muscular - descripcion - url_video - requiere_maquina) <- (Ejercicio -- id_ejercicio - nombre) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**93. Consultar el detalle de una rutina**  
`GET /rutinas/{id_rutina}`

```
(DUENO / RECEPCIONISTA / ENTRENADOR / NUTRICIONISTA) -> (id_rutina) <- (Detalle de la rutina con sus ejercicios y el permiso de edicion de quien consulta, rutina inexistente, rutina propia de un socio tratada como inexistente, o acceso denegado) --- (93. Consultar el detalle de una rutina) <- (Rutina -- id_rutina - id_entrenador - nombre - objetivo - dias_por_semana - fecha_creacion - activo) <- (Rutina_Ejercicio -- id_rutina_ejercicio - id_rutina - id_ejercicio - dia - orden - series - repeticiones - peso_sugerido - descanso_segundos - observaciones) <- (Ejercicio -- id_ejercicio - nombre - grupo_muscular - url_video) <- (Asignacion_Rutina -- id_rutina - estado) <- (Entrenador -- id_entrenador - id_empleado) <- (Empleado -- id_empleado - id_persona) <- (Persona -- id_persona - nombre - apellido) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**94. Editar una rutina y reemplazar sus ejercicios**  
`PUT /rutinas/{id_rutina}`

```
(DUENO / RECEPCIONISTA / ENTRENADOR) -> (Datos editados de la rutina) <- (Rutina actualizada con sus ejercicios reemplazados en bloque, rutina inexistente o propia de un socio, rutina de otro entrenador, entrenador ajeno / inexistente / dado de baja, ejercicio inexistente, o dias por semana fuera de 1 a 7) --- (94. Editar una rutina y reemplazar sus ejercicios) -> (Rutina -- id_entrenador - nombre - objetivo - dias_por_semana) -> (Rutina_Ejercicio -- id_rutina_ejercicio - id_rutina - id_ejercicio - dia - orden - series - repeticiones - peso_sugerido - descanso_segundos - observaciones) <- (Rutina -- id_rutina - id_entrenador - nombre - objetivo - dias_por_semana - fecha_creacion - activo) <- (Empleado -- id_empleado - id_persona - activo) <- (Entrenador -- id_entrenador - id_empleado) <- (Ejercicio -- id_ejercicio - nombre - grupo_muscular - url_video) <- (Persona -- id_persona - nombre - apellido) <- (Asignacion_Rutina -- id_rutina - estado) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**95. Asignar una rutina a un socio y finalizar la que tenia**  
`POST /rutinas/{id_rutina}/asignar`

```
(DUENO / RECEPCIONISTA / ENTRENADOR) -> (Asignacion de rutina a un socio) <- (Rutina asignada y la anterior finalizada, rutina inexistente o propia del socio, rutina de otro entrenador, socio inexistente, o rutina que el socio ya tenia asignada) --- (95. Asignar una rutina a un socio y finalizar la que tenia) -> (Asignacion_Rutina -- id_asignacion_rutina - id_socio - id_rutina - fecha_inicio - fecha_fin - estado) <- (Rutina -- id_rutina - id_entrenador - nombre) <- (Empleado -- id_empleado - id_persona) <- (Entrenador -- id_entrenador - id_empleado) <- (Socio -- id_socio - id_persona) <- (Persona -- id_persona - nombre - apellido) <- (Asignacion_Rutina -- id_asignacion_rutina - id_socio - id_rutina - estado) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**96. POST /rutinas/{id_rutina}/baja**  
`POST /rutinas/{id_rutina}/baja`

```
(DUENO / RECEPCIONISTA / ENTRENADOR) -> (id_rutina) <- (Rutina desactivada del catalogo sin tocar a los socios que la siguen, rutina inexistente, rutina propia de un socio tratada como inexistente, rutina de otro entrenador, o rutina que ya estaba desactivada) --- (96. Dar de baja una rutina del catalogo) -> (Rutina -- activo) <- (Rutina -- id_rutina - id_entrenador - nombre - objetivo - dias_por_semana - fecha_creacion - activo) <- (Rutina_Ejercicio -- id_rutina_ejercicio - id_rutina - id_ejercicio - dia - orden - series - repeticiones - peso_sugerido - descanso_segundos - observaciones) <- (Ejercicio -- id_ejercicio - nombre - grupo_muscular - url_video) <- (Asignacion_Rutina -- id_rutina - estado) <- (Entrenador -- id_entrenador - id_empleado) <- (Empleado -- id_empleado - id_persona) <- (Persona -- id_persona - nombre - apellido) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**97. POST /rutinas/{id_rutina}/reactivar**  
`POST /rutinas/{id_rutina}/reactivar`

```
(DUENO / RECEPCIONISTA / ENTRENADOR) -> (id_rutina) <- (Rutina reactivada y de nuevo disponible para asignar, rutina inexistente, rutina propia de un socio tratada como inexistente, rutina de otro entrenador, o rutina que ya estaba activa) --- (97. Reactivar una rutina del catalogo) -> (Rutina -- activo) <- (Rutina -- id_rutina - id_entrenador - nombre - objetivo - dias_por_semana - fecha_creacion - activo) <- (Rutina_Ejercicio -- id_rutina_ejercicio - id_rutina - id_ejercicio - dia - orden - series - repeticiones - peso_sugerido - descanso_segundos - observaciones) <- (Ejercicio -- id_ejercicio - nombre - grupo_muscular - url_video) <- (Asignacion_Rutina -- id_rutina - estado) <- (Entrenador -- id_entrenador - id_empleado) <- (Empleado -- id_empleado - id_persona) <- (Persona -- id_persona - nombre - apellido) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```


## Nutricion

**98. Consultar el catalogo de dietas**  
`GET /nutricion`

```
(DUENO / RECEPCIONISTA / ENTRENADOR / NUTRICIONISTA) -> (Pedido de consulta) <- (Catalogo de dietas con el permiso de edicion de cada una, o acceso denegado) --- (98. Consultar el catalogo de dietas) <- (Dieta -- id_dieta - id_nutricionista - nombre - objetivo - calorias_diarias - descripcion - fecha_creacion - activo) <- (Asignacion_Dieta -- id_dieta - estado) <- (Nutricionista -- id_nutricionista - id_empleado) <- (Empleado -- id_empleado - id_persona) <- (Persona -- id_persona - nombre - apellido) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**99. Crear una dieta del catalogo con sus comidas**  
`POST /nutricion`

```
(DUENO / RECEPCIONISTA / NUTRICIONISTA) -> (Datos de la dieta) <- (Dieta creada con sus comidas, nutricionista no elegido, dieta a nombre de otro nutricionista, nutricionista inexistente o dado de baja, plato inexistente o comida sin plato ni descripcion) --- (99. Crear una dieta del catalogo con sus comidas) -> (Dieta -- id_dieta - id_nutricionista - nombre - objetivo - calorias_diarias - descripcion - activo - fecha_creacion) -> (Comida -- id_comida - id_dieta - dia - momento - id_catalogo_comida - descripcion) <- (Empleado -- id_empleado - id_persona - activo) <- (Nutricionista -- id_nutricionista - id_empleado) <- (Catalogo_Comida -- id_catalogo_comida - nombre - descripcion - calorias) <- (Persona -- id_persona - nombre - apellido) <- (Asignacion_Dieta -- id_dieta - estado) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**100. Consultar el historial de dietas de un socio**  
`GET /nutricion/asignaciones/socio/{id_socio}`

```
(DUENO / RECEPCIONISTA / ENTRENADOR / NUTRICIONISTA) -> (id_socio) <- (Historial de dietas que el personal le asigno al socio, sin las dietas propias del socio, lista vacia si no tiene ninguna, o acceso denegado) --- (100. Consultar el historial de dietas de un socio) <- (Asignacion_Dieta -- id_asignacion_dieta - id_socio - id_dieta - fecha_inicio - fecha_fin - estado - observaciones) <- (Dieta -- id_dieta - id_nutricionista - nombre) <- (Socio -- id_socio - id_persona) <- (Persona -- id_persona - nombre - apellido) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**101. Consultar el catalogo de platos**  
`GET /nutricion/catalogo-comidas`

```
(DUENO / RECEPCIONISTA / ENTRENADOR / NUTRICIONISTA) -> (Pedido de consulta) <- (Catalogo de platos activos o acceso denegado) --- (101. Consultar el catalogo de platos) <- (Catalogo_Comida -- id_catalogo_comida - nombre - descripcion - calorias - activo) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**102. Dar de alta un plato en el catalogo de comidas**  
`POST /nutricion/catalogo-comidas`

```
(DUENO / RECEPCIONISTA / NUTRICIONISTA) -> (Datos del plato) <- (Plato agregado al catalogo o nombre duplicado) --- (102. Dar de alta un plato en el catalogo de comidas) -> (Catalogo_Comida -- id_catalogo_comida - nombre - descripcion - calorias - activo) <- (Catalogo_Comida -- id_catalogo_comida - nombre) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**103. Consultar el detalle de una dieta**  
`GET /nutricion/{id_dieta}`

```
(DUENO / RECEPCIONISTA / ENTRENADOR / NUTRICIONISTA) -> (id_dieta) <- (Detalle de la dieta con sus comidas ordenadas por dia y momento y el permiso de edicion de quien consulta, dieta inexistente, dieta propia de un socio tratada como inexistente, o acceso denegado) --- (103. Consultar el detalle de una dieta) <- (Dieta -- id_dieta - id_nutricionista - nombre - objetivo - calorias_diarias - descripcion - fecha_creacion - activo) <- (Comida -- id_comida - id_dieta - dia - momento - id_catalogo_comida - descripcion) <- (Catalogo_Comida -- id_catalogo_comida - nombre - descripcion - calorias) <- (Asignacion_Dieta -- id_dieta - estado) <- (Nutricionista -- id_nutricionista - id_empleado) <- (Empleado -- id_empleado - id_persona) <- (Persona -- id_persona - nombre - apellido) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**104. Editar una dieta y reemplazar sus comidas**  
`PUT /nutricion/{id_dieta}`

```
(DUENO / RECEPCIONISTA / NUTRICIONISTA) -> (Datos editados de la dieta) <- (Dieta actualizada con sus comidas reemplazadas en bloque y los registros de comida del socio desvinculados, dieta inexistente o propia de un socio, dieta de otro nutricionista, nutricionista ajeno / inexistente / dado de baja, plato inexistente, o comida sin plato del catalogo ni descripcion) --- (104. Editar una dieta y reemplazar sus comidas) -> (Dieta -- id_nutricionista - nombre - objetivo - calorias_diarias - descripcion) -> (Comida -- id_comida - id_dieta - dia - momento - id_catalogo_comida - descripcion) -> (Registro_Comida -- id_comida) <- (Dieta -- id_dieta - id_nutricionista - nombre - objetivo - calorias_diarias - descripcion - fecha_creacion - activo) <- (Comida -- id_comida - id_dieta) <- (Catalogo_Comida -- id_catalogo_comida - nombre - descripcion - calorias) <- (Empleado -- id_empleado - id_persona - activo) <- (Nutricionista -- id_nutricionista - id_empleado) <- (Persona -- id_persona - nombre - apellido) <- (Asignacion_Dieta -- id_dieta - estado) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**105. Asignar una dieta a un socio y finalizar la que tenia**  
`POST /nutricion/{id_dieta}/asignar`

```
(DUENO / RECEPCIONISTA / NUTRICIONISTA) -> (Asignacion de dieta a un socio) <- (Dieta asignada y la anterior finalizada, dieta inexistente o propia del socio, dieta de otro nutricionista, socio inexistente, o dieta que el socio ya tenia asignada) --- (105. Asignar una dieta a un socio y finalizar la que tenia) -> (Asignacion_Dieta -- id_asignacion_dieta - id_socio - id_dieta - fecha_inicio - fecha_fin - estado - observaciones) <- (Dieta -- id_dieta - id_nutricionista - nombre) <- (Empleado -- id_empleado - id_persona) <- (Nutricionista -- id_nutricionista - id_empleado) <- (Socio -- id_socio - id_persona) <- (Persona -- id_persona - nombre - apellido) <- (Asignacion_Dieta -- id_asignacion_dieta - id_socio - id_dieta - estado) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**106. POST /nutricion/{id_dieta}/baja**  
`POST /nutricion/{id_dieta}/baja`

```
(DUENO / RECEPCIONISTA / NUTRICIONISTA) -> (id_dieta) <- (Dieta desactivada del catalogo sin cortarsela a los socios que la siguen, dieta inexistente, dieta propia de un socio tratada como inexistente, dieta de otro nutricionista, o dieta que ya estaba desactivada) --- (106. Dar de baja una dieta del catalogo) -> (Dieta -- activo) <- (Dieta -- id_dieta - id_nutricionista - nombre - objetivo - calorias_diarias - descripcion - fecha_creacion - activo) <- (Comida -- id_comida - id_dieta - dia - momento - id_catalogo_comida - descripcion) <- (Catalogo_Comida -- id_catalogo_comida - nombre - descripcion - calorias) <- (Asignacion_Dieta -- id_dieta - estado) <- (Nutricionista -- id_nutricionista - id_empleado) <- (Empleado -- id_empleado - id_persona) <- (Persona -- id_persona - nombre - apellido) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```

**107. POST /nutricion/{id_dieta}/reactivar**  
`POST /nutricion/{id_dieta}/reactivar`

```
(DUENO / RECEPCIONISTA / NUTRICIONISTA) -> (id_dieta) <- (Dieta reactivada y de nuevo disponible para asignar, dieta inexistente, dieta propia de un socio tratada como inexistente, dieta de otro nutricionista, o dieta que ya estaba activa) --- (107. Reactivar una dieta del catalogo) -> (Dieta -- activo) <- (Dieta -- id_dieta - id_nutricionista - nombre - objetivo - calorias_diarias - descripcion - fecha_creacion - activo) <- (Comida -- id_comida - id_dieta - dia - momento - id_catalogo_comida - descripcion) <- (Catalogo_Comida -- id_catalogo_comida - nombre - descripcion - calorias) <- (Asignacion_Dieta -- id_dieta - estado) <- (Nutricionista -- id_nutricionista - id_empleado) <- (Empleado -- id_empleado - id_persona) <- (Persona -- id_persona - nombre - apellido) <- (Usuario -- id_usuario - id_persona - activo - bloqueado - debe_cambiar_password)
```


## Patologias

**108. Listar el catalogo de patologias**  
`GET /patologias`

```
(DUENO / ENTRENADOR / NUTRICIONISTA) -> (Pedido de consulta) <- (Catalogo de patologias o acceso denegado) --- (108. Listar el catalogo de patologias) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password - id_persona) <- (Patologia -- id_patologia - nombre - descripcion)
```

**109. Crear una patologia en el catalogo**  
`POST /patologias`

```
(DUENO / ENTRENADOR / NUTRICIONISTA) -> (Datos de la patologia) <- (Patologia agregada al catalogo o nombre duplicado) --- (109. Crear una patologia en el catalogo) -> (Patologia -- nombre - descripcion) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password - id_persona) <- (Patologia -- id_patologia - nombre)
```


## Promociones

**110. Listar promociones**  
`GET /promociones`

```
(DUENO / RECEPCIONISTA) -> (Filtro de promociones) <- (Catalogo de promociones con vigencia y etiqueta, o acceso denegado) --- (110. Listar promociones) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password - id_persona) <- (Promocion -- id_promocion - nombre - descripcion - porcentaje_descuento - fecha_inicio - fecha_fin - id_sede - activo)
```

**111. Crear una promocion**  
`POST /promociones`

```
(DUENO) -> (Datos de la promocion) <- (Promocion creada, nombre duplicado, sede inexistente, ventana de fechas invalida, porcentaje fuera de rango o ningun dueno cargado) --- (111. Crear una promocion) -> (Promocion -- id_dueno - id_sede - nombre - descripcion - porcentaje_descuento - fecha_inicio - fecha_fin - activo) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password - id_persona) <- (Promocion -- id_promocion - nombre) <- (Sede -- id_sede) <- (Dueno -- id_dueno - id_persona)
```

**112. Consultar una promocion**  
`GET /promociones/{id_promocion}`

```
(DUENO / RECEPCIONISTA) -> (id_promocion) <- (Promocion encontrada o promocion inexistente) --- (112. Consultar una promocion) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password - id_persona) <- (Promocion -- id_promocion - nombre - descripcion - porcentaje_descuento - fecha_inicio - fecha_fin - id_sede - activo)
```

**113. Editar una promocion**  
`PUT /promociones/{id_promocion}`

```
(DUENO) -> (Datos de la promocion) <- (Promocion actualizada, promocion inexistente, nombre duplicado, sede inexistente, ventana de fechas invalida o porcentaje fuera de rango) --- (113. Editar una promocion) -> (Promocion -- nombre - descripcion - porcentaje_descuento - fecha_inicio - fecha_fin - id_sede) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password - id_persona) <- (Promocion -- id_promocion - nombre - activo - fecha_inicio - fecha_fin - porcentaje_descuento - descripcion - id_sede) <- (Sede -- id_sede)
```

**114. Dar de baja una promocion**  
`POST /promociones/{id_promocion}/baja`

```
(DUENO) -> (id_promocion) <- (Promocion dada de baja, promocion inexistente o ya estaba dada de baja) --- (114. Dar de baja una promocion) -> (Promocion -- activo) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password - id_persona) <- (Promocion -- id_promocion - activo - nombre - descripcion - porcentaje_descuento - fecha_inicio - fecha_fin - id_sede)
```

**115. Reactivar una promocion**  
`POST /promociones/{id_promocion}/reactivar`

```
(DUENO) -> (id_promocion) <- (Promocion reactivada, reactivada pero fuera de fecha, promocion inexistente o ya estaba activa) --- (115. Reactivar una promocion) -> (Promocion -- activo) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password - id_persona) <- (Promocion -- id_promocion - activo - nombre - descripcion - porcentaje_descuento - fecha_inicio - fecha_fin - id_sede)
```

**116. Consultar el uso de una promocion**  
`GET /promociones/{id_promocion}/uso`

```
(DUENO) -> (id_promocion) <- (Cantidad de cobros en los que se aplico o promocion inexistente) --- (116. Consultar el uso de una promocion) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password - id_persona) <- (Promocion -- id_promocion) <- (Pago -- id_pago - id_promocion)
```

**117. Simular el precio de un plan con una promocion**  
`GET /promociones/{id_promocion}/vista-previa`

```
(DUENO / RECEPCIONISTA) -> (Promocion y plan a simular) <- (Precio de lista, descuento y precio final, o promocion o plan inexistente) --- (117. Simular el precio de un plan con una promocion) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password - id_persona) <- (Promocion -- id_promocion - nombre - porcentaje_descuento) <- (Tipo_Membresia -- id_tipo_membresia - precio_actual)
```


## Dashboard

**118. Consultar la actividad reciente**  
`GET /dashboard/actividad`

```
(DUENO / RECEPCIONISTA) -> (Pedido de consulta) <- (Feed de pagos, altas de socios y vencimientos proximos, o acceso denegado por sesion invalida, cuenta desactivada o seccion no permitida) --- (118. Consultar la actividad reciente) <- (Pago -- id_pago - id_socio - id_membresia - id_inscripcion - monto - estado - fecha_pago) <- (Socio -- id_socio - id_persona - fecha_alta) <- (Persona -- nombre - apellido) <- (Membresia -- id_membresia - id_socio - id_tipo_membresia - estado - fecha_vencimiento) <- (Tipo_Membresia -- nombre) <- (Inscripcion_Actividad -- id_inscripcion - id_plan_actividad) <- (Plan_Actividad -- id_actividad - nombre - tipo_limite) <- (Actividad -- nombre) <- (Reserva -- id_pago - id_turno) <- (Turno -- id_turno - id_actividad) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password)
```

**119. Consultar los ingresos por periodo**  
`GET /dashboard/ingresos`

```
(DUENO) -> (escala) <- (Serie de ingresos por dia, mes o anio, o acceso denegado) --- (119. Consultar los ingresos por periodo) <- (Pago -- monto - estado - fecha_pago) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password)
```

**120. Consultar las ultimas altas de socios con su estado de cuota**  
`GET /dashboard/socios-recientes`

```
(DUENO / RECEPCIONISTA) -> (Pedido de consulta) <- (Ultimas altas con su plan y su estado de cuota, con "Sin plan" y "Vencido" para quien no tiene membresia activa, o acceso denegado por sesion invalida, cuenta desactivada o seccion no permitida) --- (120. Consultar las ultimas altas de socios con su estado de cuota) <- (Socio -- id_socio - id_persona) <- (Persona -- nombre - apellido) <- (Membresia -- id_socio - id_tipo_membresia - estado - fecha_vencimiento) <- (Tipo_Membresia -- nombre) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password)
```

**121. Consultar las metricas del tablero**  
`GET /dashboard/stats`

```
(DUENO / RECEPCIONISTA) -> (Pedido de consulta) <- (Las cuatro metricas del mes con su variacion, con los ingresos en cero para quien no puede verlos, o acceso denegado por sesion invalida, cuenta desactivada o seccion no permitida) --- (121. Consultar las metricas del tablero) <- (Socio -- id_socio - activo - fecha_alta) <- (Pago -- monto - estado - fecha_pago) <- (Turno -- id_turno - fecha - estado) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password)
```


## Portal del socio

**122. Consultar el catalogo de condiciones medicas desde el portal**  
`GET /portal/catalogo-patologias`

```
(SOCIO) -> (Pedido de consulta) <- (Catalogo de condiciones medicas para elegir) --- (122. Consultar el catalogo de condiciones medicas desde el portal) <- (Patologia -- id_patologia - nombre - descripcion)
```

**123. Consultar mi cuota y aplicar las bajas programadas vencidas**  
`GET /portal/mi-cuota`

```
(SOCIO) -> (Pedido de consulta) <- (Estado de la cuota con el plan, el vencimiento, los ultimos pagos, la baja programada y desde cuando se puede renovar; y si habia una baja programada cuya fecha ya llego, el socio queda dado de baja) --- (123. Consultar mi cuota y aplicar las bajas programadas vencidas) -> (Baja -- pendiente) -> (Socio -- activo) -> (Membresia -- estado) -> (Reserva -- estado - fecha_cancelacion) -> (Usuario -- activo) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password - id_persona) <- (Baja -- id_baja - id_socio - fecha_baja - tipo - pendiente) <- (Socio -- id_socio - id_persona - activo) <- (Persona -- id_persona - nombre - apellido) <- (Membresia -- id_membresia - id_socio - id_tipo_membresia - estado - fecha_inicio - fecha_vencimiento - precio_pactado) <- (Tipo_Membresia -- id_tipo_membresia - nombre) <- (Pago -- id_pago - id_socio - monto - metodo - fecha_pago - periodo_desde - periodo_hasta - estado - numero_comprobante) <- (Reserva -- id_reserva - id_turno - id_socio - estado - fecha_reserva) <- (Turno -- id_turno - fecha - estado - cupo_maximo)
```

**124. Iniciar el pago online de la cuota**  
`POST /portal/mi-cuota/pagar`

```
(SOCIO) -> (id_tipo_membresia) <- (Checkout creado, sesion sin ficha de socio, renovacion bloqueada por periodo en curso o baja programada, plan inexistente o dado de baja, pago online deshabilitado, o Pago dejado en CANCELADO por fallo de la pasarela) --- (124. Iniciar el pago online de la cuota) -> (Pago -- id_socio - id_tipo_membresia - id_sede - metodo - monto - fecha_pago - estado - fecha_cancelacion) <- (Socio -- id_socio - id_sede - id_persona) <- (Persona -- nombre - apellido - email) <- (Tipo_Membresia -- id_tipo_membresia - nombre - precio_actual - activo) <- (Membresia -- id_socio - estado - fecha_vencimiento) <- (Baja -- id_socio - pendiente - fecha_baja) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password)
```

**125. Simular la acreditacion de un pago online**  
`POST /portal/mi-cuota/pagar/{id_pago}/simular`

```
(SOCIO) -> (Pago a simular y resultado) <- (Pago acreditado con su membresia, pago cancelado, pago confirmado sin membresia por tener un periodo en curso, pago ajeno o inexistente, sesion sin ficha de socio, o ruta inexistente fuera del modo simulado) --- (125. Simular la acreditacion de un pago online) -> (Pago -- estado - numero_comprobante - fecha_cancelacion - id_membresia) -> (Membresia -- id_socio - id_tipo_membresia - precio_pactado - fecha_inicio - fecha_vencimiento - estado) <- (Pago -- id_pago - id_socio - monto - estado - numero_comprobante - id_membresia - id_tipo_membresia) <- (Socio -- id_socio) <- (Tipo_Membresia -- id_tipo_membresia - duracion_dias - precio_actual - activo) <- (Membresia -- id_socio - estado - fecha_inicio - fecha_vencimiento) <- (Baja -- id_socio - pendiente - fecha_baja) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password)
```

**126. Listar los planes que el socio puede comprar**  
`GET /portal/mi-cuota/planes`

```
(SOCIO) -> (Pedido de consulta) <- (Planes activos con su precio, ficha de socio inexistente o seccion no permitida) --- (126. Listar los planes que el socio puede comprar) <- (Socio -- id_socio) <- (Tipo_Membresia -- id_tipo_membresia - nombre - descripcion - duracion_dias - precio_actual - activo) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password)
```

**127. Consultar mi dieta activa**  
`GET /portal/mi-dieta`

```
(SOCIO) -> (Pedido de consulta) <- (Su plan alimentario vigente con las comidas agrupadas por dia y las calorias de cada dia, vacio si no tiene, o acceso denegado si la cuenta no esta asociada a una ficha de socio) --- (127. Consultar mi dieta activa) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password) <- (Socio -- id_socio) <- (Asignacion_Dieta -- id_asignacion_dieta - id_socio - id_dieta - fecha_inicio - estado - observaciones) <- (Dieta -- id_dieta - id_nutricionista - nombre - objetivo - calorias_diarias - descripcion - activo) <- (Comida -- id_comida - id_dieta - dia - momento - descripcion - id_catalogo_comida) <- (Catalogo_Comida -- id_catalogo_comida - nombre - calorias) <- (Nutricionista -- id_nutricionista - id_empleado) <- (Empleado -- id_empleado - id_persona) <- (Persona -- id_persona - nombre - apellido)
```

**128. Consultar mi registro de comidas**  
`GET /portal/mi-dieta/comidas`

```
(SOCIO) -> (dias) <- (Lo que registro haber comido en los ultimos dias, de lo mas nuevo a lo mas viejo, o acceso denegado si la cuenta no esta asociada a una ficha de socio) --- (128. Consultar mi registro de comidas) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password) <- (Socio -- id_socio) <- (Registro_Comida -- id_registro_comida - id_socio - fecha - momento - comida_ingerida - calorias_estimadas - proteinas_g - carbohidratos_g - grasas_g)
```

**129. Registrar una comida que comi**  
`POST /portal/mi-dieta/comidas`

```
(SOCIO) -> (Datos de la comida ingerida) <- (Comida registrada en mi historial, o acceso denegado si la cuenta no esta asociada a una ficha de socio) --- (129. Registrar una comida que comi) -> (Registro_Comida -- id_socio - fecha - comida_ingerida - momento - calorias_estimadas - proteinas_g - carbohidratos_g - grasas_g) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password) <- (Socio -- id_socio)
```

**130. Consultar mi historial de dietas**  
`GET /portal/mi-dieta/historial`

```
(SOCIO) -> (Pedido de consulta) <- (Listado de las dietas que siguio con las observaciones del nutricionista, o acceso denegado si la cuenta no esta asociada a una ficha de socio) --- (130. Consultar mi historial de dietas) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password) <- (Socio -- id_socio - id_persona) <- (Persona -- id_persona - nombre - apellido) <- (Asignacion_Dieta -- id_asignacion_dieta - id_socio - id_dieta - fecha_inicio - fecha_fin - estado - observaciones) <- (Dieta -- id_dieta - nombre)
```

**131. Crear mi dieta propia**  
`POST /portal/mi-dieta/propia`

```
(SOCIO) -> (Datos de la dieta propia) <- (Dieta propia creada y activa reemplazando a la propia anterior, o rechazo si la activa es la del nutricionista) --- (131. Crear mi dieta propia) -> (Dieta -- id_dieta - id_nutricionista - nombre - objetivo - calorias_diarias - descripcion - activo) -> (Comida -- id_dieta - dia - momento - id_catalogo_comida - descripcion) -> (Asignacion_Dieta -- id_socio - id_dieta - fecha_inicio - fecha_fin - estado) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password) <- (Socio -- id_socio) <- (Asignacion_Dieta -- id_asignacion_dieta - id_socio - id_dieta - fecha_inicio - estado - observaciones) <- (Dieta -- id_dieta - id_nutricionista - nombre - objetivo - calorias_diarias - descripcion - activo) <- (Comida -- id_comida - id_dieta - dia - momento - descripcion - id_catalogo_comida)
```

**132. Eliminar mi dieta propia**  
`DELETE /portal/mi-dieta/propia`

```
(SOCIO) -> (Pedido de baja de mi dieta propia) <- (Dieta propia retirada y pasada a historial, o no encontrada si no tiene una propia activa) --- (132. Eliminar mi dieta propia) -> (Asignacion_Dieta -- estado - fecha_fin) -> (Dieta -- activo) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password) <- (Socio -- id_socio) <- (Asignacion_Dieta -- id_asignacion_dieta - id_socio - id_dieta - estado) <- (Dieta -- id_dieta - id_nutricionista)
```

**133. Consultar quien me entrena**  
`GET /portal/mi-entrenador`

```
(SOCIO) -> (Pedido de consulta) <- (Listado de mis entrenadores vigentes, o cuenta sin ficha de socio) --- (133. Consultar quien me entrena) <- (Socio -- id_socio) <- (Asignacion_Entrenador -- id_asignacion_entrenador - id_socio - id_entrenador - fecha_inicio - fecha_fin - estado) <- (Entrenador -- id_entrenador - id_empleado - especialidad) <- (Empleado -- id_empleado - id_persona) <- (Persona -- id_persona - nombre - apellido)
```

**134. Darse de baja el socio**  
`POST /portal/mi-membresia/baja`

```
(SOCIO) -> (Pedido de baja propia) <- (Baja programada para el dia siguiente al vencimiento, baja aplicada en el acto, o rechazo por socio ya dado de baja, baja ya pedida o cuenta sin ficha de socio) --- (134. Darse de baja el socio) -> (Baja -- id_socio - fecha_baja - tipo - motivo - pendiente) -> (Socio -- activo) -> (Membresia -- estado - fecha_vencimiento) -> (Congelamiento -- estado - fecha_reanudacion) -> (Reserva -- estado - fecha_cancelacion) <- (Socio -- id_socio - activo) <- (Baja -- id_socio - pendiente - fecha_baja) <- (Congelamiento -- id_congelamiento - id_membresia - estado - fecha_inicio - fecha_fin) <- (Membresia -- id_membresia - id_socio - estado - fecha_vencimiento) <- (Reserva -- id_reserva - id_socio - id_turno - estado - fecha_reserva) <- (Turno -- id_turno - fecha - estado - cupo_maximo)
```

**135. Anular la baja programada**  
`DELETE /portal/mi-membresia/baja`

```
(SOCIO) -> (Pedido de anulacion de baja) <- (Baja anulada, aviso de que no hay ninguna programada, o cuenta sin ficha de socio) --- (135. Anular la baja programada) -> (Baja -- id_baja - id_socio - fecha_baja - tipo - motivo - pendiente) <- (Socio -- id_socio) <- (Baja -- id_socio - pendiente - fecha_baja)
```

**136. Consultar mis pausas de membresia**  
`GET /portal/mi-membresia/congelamientos`

```
(SOCIO) -> (Pedido de consulta) <- (Historial de pausas, cerrando automaticamente la que ya vencio y sumando sus dias al vencimiento, o acceso denegado por no tener ficha de socio) --- (136. Consultar mis pausas de membresia) -> (Congelamiento -- estado - fecha_reanudacion) -> (Membresia -- fecha_vencimiento - estado) <- (Socio -- id_socio) <- (Congelamiento -- id_congelamiento - id_membresia - fecha_inicio - fecha_fin - fecha_reanudacion - motivo - estado) <- (Membresia -- id_membresia - id_socio - fecha_vencimiento - estado)
```

**137. Congelar mi membresia**  
`POST /portal/mi-membresia/congelar`

```
(SOCIO) -> (Pedido de pausa) <- (Membresia pausada, o rechazo por pausa ya vigente, sin membresia activa, cuota vencida, fecha de inicio hacia atras, duracion menor a 7 o mayor a 90 dias, o tope de 90 dias congelados en los ultimos 365) --- (137. Congelar mi membresia) -> (Congelamiento -- id_membresia - fecha_inicio - fecha_fin - motivo - estado - fecha_reanudacion) -> (Membresia -- estado - fecha_vencimiento) <- (Socio -- id_socio) <- (Membresia -- id_membresia - id_socio - estado - fecha_vencimiento) <- (Congelamiento -- id_congelamiento - id_membresia - estado - origen - fecha_inicio - fecha_fin - fecha_reanudacion)
```

**138. Reanudar mi membresia pausada**  
`POST /portal/mi-membresia/reanudar`

```
(SOCIO) -> (Pedido de reanudacion) <- (Membresia reactivada con los dias realmente pausados sumados al vencimiento, o rechazo por no tener ninguna pausa activa) --- (138. Reanudar mi membresia pausada) -> (Congelamiento -- estado - fecha_reanudacion) -> (Membresia -- fecha_vencimiento - estado) <- (Socio -- id_socio) <- (Congelamiento -- id_congelamiento - id_membresia - estado - fecha_inicio - fecha_fin) <- (Membresia -- id_membresia - id_socio - fecha_vencimiento - estado)
```

**139. Consultar mi perfil**  
`GET /portal/mi-perfil`

```
(SOCIO) -> (Pedido de consulta) <- (Ficha propia con el estado de su membresia, o acceso denegado si la cuenta no esta asociada a una ficha de socio) --- (139. Consultar mi perfil) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password) <- (Socio -- id_socio - id_persona - id_sede - numero_socio - fecha_alta - objetivo) <- (Persona -- id_persona - dni - nombre - apellido - email - fecha_nacimiento - calle - numero_calle - localidad) <- (Telefono -- id_persona - numero - principal) <- (Contacto_Emergencia -- id_persona - id_contacto_emergencia - nombre - telefono - parentesco - principal) <- (Membresia -- id_socio - estado - fecha_vencimiento - id_tipo_membresia) <- (Tipo_Membresia -- id_tipo_membresia - nombre) <- (Sede -- id_sede - nombre)
```

**140. Editar mi perfil**  
`PUT /portal/mi-perfil`

```
(SOCIO) -> (Datos de contacto del socio) <- (Perfil actualizado o rechazo porque el email ya esta registrado para otra persona) --- (140. Editar mi perfil) -> (Persona -- email) -> (Contacto_Emergencia -- id_persona - nombre - telefono - parentesco - principal) -> (Telefono -- id_persona - numero - tipo - principal) <- (Socio -- id_socio - id_persona - id_sede - numero_socio - fecha_alta - objetivo) <- (Persona -- id_persona - dni - nombre - apellido - email - fecha_nacimiento - calle - numero_calle - localidad) <- (Contacto_Emergencia -- id_contacto_emergencia - id_persona - principal - nombre - telefono - parentesco) <- (Telefono -- id_telefono - id_persona - principal - numero) <- (Membresia -- id_socio - estado - fecha_vencimiento - id_tipo_membresia) <- (Tipo_Membresia -- nombre) <- (Sede -- nombre)
```

**141. Consultar mi progreso corporal**  
`GET /portal/mi-progreso`

```
(SOCIO) -> (Pedido de consulta) <- (Serie de mediciones con peso actual, variacion, grasa, altura y si ya cargo hoy, o acceso denegado) --- (141. Consultar mi progreso corporal) <- (Socio -- id_socio) <- (Registro_Salud -- id_registro_salud - id_socio - fecha - peso - altura - grasa_corporal - masa_muscular - observaciones)
```

**142. Consultar mis asistencias**  
`GET /portal/mi-progreso/asistencias`

```
(SOCIO) -> (Pedido de consulta) <- (Historial de mis ultimos ingresos al gimnasio o acceso denegado por no tener ficha de socio) --- (142. Consultar mis asistencias) <- (Socio -- id_socio - id_persona - numero_socio) <- (Persona -- nombre - apellido) <- (Asistencia -- id_asistencia - id_socio - fecha_hora_ingreso - fecha_hora_egreso - metodo_registro)
```

**143. Cargar mi medicion del dia**  
`POST /portal/mi-progreso/mediciones`

```
(SOCIO) -> (Medicion corporal) <- (Medicion del dia registrada o rechazo porque ya cargo una hoy) --- (143. Cargar mi medicion del dia) -> (Registro_Salud -- id_socio - fecha - peso - altura - grasa_corporal - masa_muscular - observaciones) <- (Socio -- id_socio) <- (Registro_Salud -- id_registro_salud - id_socio - fecha)
```

**144. Consultar mi rutina activa**  
`GET /portal/mi-rutina`

```
(SOCIO) -> (Pedido de consulta) <- (Su rutina activa con los ejercicios, vacio si todavia no tiene ninguna, o acceso denegado si la cuenta no esta asociada a una ficha de socio) --- (144. Consultar mi rutina activa) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password) <- (Socio -- id_socio) <- (Asignacion_Rutina -- id_asignacion_rutina - id_socio - id_rutina - fecha_inicio - estado) <- (Rutina -- id_rutina - id_entrenador - nombre - objetivo - dias_por_semana - fecha_creacion - activo) <- (Rutina_Ejercicio -- id_rutina_ejercicio - id_rutina - id_ejercicio - dia - orden - series - repeticiones - peso_sugerido - descanso_segundos - observaciones) <- (Ejercicio -- id_ejercicio - nombre - grupo_muscular - url_video) <- (Entrenador -- id_entrenador - id_empleado) <- (Empleado -- id_empleado - id_persona) <- (Persona -- id_persona - nombre - apellido)
```

**145. Consultar el catalogo de ejercicios para armar mi rutina**  
`GET /portal/mi-rutina/ejercicios`

```
(SOCIO) -> (Pedido de consulta) <- (Catalogo completo de ejercicios ordenado por grupo muscular, o acceso denegado si el rol no tiene la seccion) --- (145. Consultar el catalogo de ejercicios para armar mi rutina) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password) <- (Ejercicio -- id_ejercicio - nombre - grupo_muscular - descripcion - url_video - requiere_maquina)
```

**146. Consultar mi historial de rutinas**  
`GET /portal/mi-rutina/historial`

```
(SOCIO) -> (Pedido de consulta) <- (Listado de las rutinas que siguio, de la mas nueva a la mas vieja, o acceso denegado si la cuenta no esta asociada a una ficha de socio) --- (146. Consultar mi historial de rutinas) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password) <- (Socio -- id_socio - id_persona) <- (Persona -- id_persona - nombre - apellido) <- (Asignacion_Rutina -- id_asignacion_rutina - id_socio - id_rutina - fecha_inicio - fecha_fin - estado) <- (Rutina -- id_rutina - nombre)
```

**147. Crear mi rutina propia**  
`POST /portal/mi-rutina/propia`

```
(SOCIO) -> (Datos de la rutina propia) <- (Rutina propia creada y activa reemplazando a la propia anterior, rechazo si la activa es la del entrenador, o ejercicio inexistente) --- (147. Crear mi rutina propia) -> (Rutina -- id_rutina - id_entrenador - nombre - objetivo - dias_por_semana - activo) -> (Rutina_Ejercicio -- id_rutina - id_ejercicio - dia - orden - series - repeticiones - peso_sugerido - descanso_segundos - observaciones) -> (Asignacion_Rutina -- id_socio - id_rutina - fecha_inicio - fecha_fin - estado) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password) <- (Socio -- id_socio) <- (Asignacion_Rutina -- id_asignacion_rutina - id_socio - id_rutina - fecha_inicio - estado) <- (Rutina -- id_rutina - id_entrenador - nombre - objetivo - dias_por_semana - fecha_creacion - activo) <- (Ejercicio -- id_ejercicio - nombre - grupo_muscular - url_video) <- (Rutina_Ejercicio -- id_rutina_ejercicio - id_rutina - id_ejercicio - dia - orden - series - repeticiones - peso_sugerido - descanso_segundos - observaciones)
```

**148. Eliminar mi rutina propia**  
`DELETE /portal/mi-rutina/propia`

```
(SOCIO) -> (Pedido de baja de mi rutina propia) <- (Rutina propia retirada y pasada a historial, o no encontrada si no tiene una propia activa) --- (148. Eliminar mi rutina propia) -> (Asignacion_Rutina -- estado - fecha_fin) -> (Rutina -- activo) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password) <- (Socio -- id_socio) <- (Asignacion_Rutina -- id_asignacion_rutina - id_socio - id_rutina - estado) <- (Rutina -- id_rutina - id_entrenador)
```

**149. Consultar mi registro de ejercicios**  
`GET /portal/mi-rutina/registro-ejercicio`

```
(SOCIO) -> (dias) <- (Series registradas con el nombre del ejercicio resuelto, o acceso denegado) --- (149. Consultar mi registro de ejercicios) <- (Socio -- id_socio) <- (Registro_Ejercicio -- id_registro_ejercicio - id_socio - id_ejercicio - fecha - peso_hecho - series_hechas - repeticiones_hechas) <- (Ejercicio -- id_ejercicio - nombre)
```

**150. Registrar una serie de ejercicio**  
`POST /portal/mi-rutina/registro-ejercicio`

```
(SOCIO) -> (Serie realizada) <- (Serie acumulada en el registro del dia o rechazo porque el ejercicio no existe) --- (150. Registrar una serie de ejercicio) -> (Registro_Ejercicio -- id_socio - id_ejercicio - fecha - peso_hecho - series_hechas - repeticiones_hechas - observaciones) <- (Socio -- id_socio) <- (Ejercicio -- id_ejercicio) <- (Registro_Ejercicio -- id_registro_ejercicio - id_socio - id_ejercicio - fecha - peso_hecho - series_hechas - repeticiones_hechas)
```

**151. Consultar mis actividades reservadas**  
`GET /portal/mis-actividades`

```
(SOCIO) -> (Pedido de consulta) <- (Las clases futuras a las que esta anotado con las clases que le quedan del abono, o acceso denegado si la cuenta no esta asociada a una ficha de socio) --- (151. Consultar mis actividades reservadas) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password) <- (Socio -- id_socio - id_persona) <- (Persona -- id_persona - nombre - apellido) <- (Reserva -- id_reserva - id_turno - id_socio - id_inscripcion - estado) <- (Turno -- id_turno - id_actividad - fecha - hora) <- (Actividad -- id_actividad - nombre) <- (Inscripcion_Actividad -- id_inscripcion - id_plan_actividad) <- (Plan_Actividad -- id_plan_actividad - tipo_limite - cantidad)
```

**152. Consultar el catalogo de actividades**  
`GET /portal/mis-actividades/catalogo`

```
(SOCIO) -> (Pedido de consulta) <- (Catalogo de actividades activas con sus planes y precios vigentes) --- (152. Consultar el catalogo de actividades) <- (Actividad -- id_actividad - nombre - descripcion - cupo_default - horas_anticipacion_cancelacion - minutos_tolerancia - activo) <- (Plan_Actividad -- id_plan_actividad - id_actividad - nombre - tipo_limite - cantidad - precio - activo)
```

**153. Consultar mis abonos de actividades**  
`GET /portal/mis-actividades/inscripciones`

```
(SOCIO) -> (Pedido de consulta) <- (Listado de mis abonos vigentes y vencidos con las clases restantes, o cuenta sin ficha de socio) --- (153. Consultar mis abonos de actividades) <- (Socio -- id_socio - id_persona) <- (Persona -- id_persona - nombre - apellido) <- (Inscripcion_Actividad -- id_inscripcion - id_socio - id_plan_actividad - precio_pactado - fecha_inicio - fecha_vencimiento - estado) <- (Plan_Actividad -- id_plan_actividad - id_actividad - nombre - tipo_limite - cantidad) <- (Actividad -- id_actividad - nombre) <- (Reserva -- id_reserva - id_inscripcion - estado)
```

**154. Cancelar mi abono de actividad**  
`POST /portal/mis-actividades/inscripciones/{id_inscripcion}/cancelar`

```
(SOCIO) -> (id_inscripcion) <- (Abono cancelado con sus reservas futuras, abono inexistente o ajeno, abono ya cancelado, o cuenta sin ficha de socio) --- (154. Cancelar mi abono de actividad) -> (Inscripcion_Actividad -- estado) -> (Reserva -- estado - fecha_cancelacion) <- (Socio -- id_socio - id_persona) <- (Persona -- id_persona - nombre - apellido) <- (Inscripcion_Actividad -- id_inscripcion - id_socio - id_plan_actividad - precio_pactado - fecha_inicio - fecha_vencimiento - estado) <- (Plan_Actividad -- id_plan_actividad - id_actividad - nombre - tipo_limite - cantidad) <- (Actividad -- id_actividad - nombre) <- (Reserva -- id_reserva - id_inscripcion - id_turno - estado) <- (Turno -- id_turno - fecha)
```

**155. Comprar mi abono de actividad**  
`POST /portal/mis-actividades/planes/{id_plan}/comprar`

```
(SOCIO) -> (Compra de abono) <- (Abono comprado con su pago confirmado, o rechazo por plan inexistente o dado de baja, actividad discontinuada, cuota no al dia, abono duplicado de ese mismo plan o cuota que no cubre el mes entero del abono) --- (155. Comprar mi abono de actividad) -> (Inscripcion_Actividad -- id_socio - id_plan_actividad - precio_pactado - fecha_inicio - fecha_vencimiento - estado) -> (Pago -- id_socio - id_inscripcion - id_sede - metodo - monto - fecha_pago - periodo_desde - periodo_hasta - estado) <- (Socio -- id_socio - id_persona - id_sede) <- (Persona -- nombre - apellido) <- (Plan_Actividad -- id_plan_actividad - id_actividad - nombre - tipo_limite - cantidad - precio - activo) <- (Actividad -- id_actividad - nombre - activo) <- (Membresia -- id_socio - estado - fecha_vencimiento) <- (Inscripcion_Actividad -- id_inscripcion - id_socio - id_plan_actividad - estado - fecha_vencimiento - precio_pactado - fecha_inicio) <- (Reserva -- id_reserva - id_inscripcion - estado)
```

**156. Consultar mis clases del profesor**  
`GET /portal/mis-clases`

```
(PROFESOR) -> (dias) <- (Agenda de sus clases con los anotados de cada turno, o acceso denegado si la cuenta no esta asociada a una ficha de profesor) --- (156. Consultar mis clases del profesor) <- (Usuario -- id_usuario - activo - bloqueado - debe_cambiar_password) <- (Profesor -- id_profesor - id_empleado) <- (Empleado -- id_empleado - id_persona) <- (Persona -- id_persona - nombre - apellido - dni) <- (Turno -- id_turno - id_profesor - id_actividad - fecha - hora - cupo_maximo - estado) <- (Actividad -- id_actividad - nombre - minutos_tolerancia) <- (Reserva -- id_reserva - id_turno - id_socio - id_inscripcion - estado - fecha_reserva) <- (Asistencia -- id_reserva) <- (Socio -- id_socio - id_persona - activo) <- (Membresia -- id_socio - estado - fecha_vencimiento) <- (Baja -- id_socio - pendiente - fecha_baja)
```

**157. Consultar mis contactos de emergencia**  
`GET /portal/mis-contactos-emergencia`

```
(SOCIO) -> (Pedido de consulta) <- (Listado de mis contactos de emergencia con el principal primero, o cuenta sin ficha de socio) --- (157. Consultar mis contactos de emergencia) <- (Socio -- id_socio - id_persona) <- (Persona -- id_persona) <- (Contacto_Emergencia -- id_contacto_emergencia - id_persona - nombre - telefono - parentesco - principal)
```

**158. Agregar un contacto de emergencia propio**  
`POST /portal/mis-contactos-emergencia`

```
(SOCIO) -> (Datos del contacto de emergencia) <- (Contacto agregado, marcado principal si es el primero o si lo pidieron, numero ya cargado, datos invalidos o cuenta sin ficha de socio) --- (158. Agregar un contacto de emergencia propio) -> (Contacto_Emergencia -- id_persona - nombre - telefono - parentesco - principal) <- (Socio -- id_socio - id_persona) <- (Persona -- id_persona) <- (Contacto_Emergencia -- id_contacto_emergencia - id_persona - telefono - principal)
```

**159. Editar un contacto de emergencia propio**  
`PUT /portal/mis-contactos-emergencia/{id_contacto}`

```
(SOCIO) -> (Datos del contacto de emergencia) <- (Contacto actualizado, contacto ajeno o inexistente, datos invalidos o cuenta sin ficha de socio) --- (159. Editar un contacto de emergencia propio) -> (Contacto_Emergencia -- nombre - telefono - parentesco - principal) <- (Socio -- id_socio - id_persona) <- (Persona -- id_persona) <- (Contacto_Emergencia -- id_contacto_emergencia - id_persona - principal)
```

**160. Borrar un contacto de emergencia propio**  
`DELETE /portal/mis-contactos-emergencia/{id_contacto}`

```
(SOCIO) -> (id_contacto_emergencia) <- (Contacto borrado y ascenso del mas viejo a principal, contacto ajeno o inexistente, o cuenta sin ficha de socio) --- (160. Borrar un contacto de emergencia propio) -> (Contacto_Emergencia -- id_contacto_emergencia - id_persona - nombre - telefono - parentesco - principal) <- (Socio -- id_socio - id_persona) <- (Persona -- id_persona) <- (Contacto_Emergencia -- id_contacto_emergencia - id_persona - principal)
```

**161. Consultar mis condiciones medicas**  
`GET /portal/mis-patologias`

```
(SOCIO) -> (Pedido de consulta) <- (Listado de mis condiciones medicas declaradas con sus observaciones, o cuenta sin ficha de socio) --- (161. Consultar mis condiciones medicas) <- (Socio -- id_socio) <- (Socio_Patologia -- id_socio - id_patologia - fecha_diagnostico - observaciones) <- (Patologia -- id_patologia - nombre - descripcion)
```

**162. Declarar una condicion medica propia**  
`POST /portal/mis-patologias`

```
(SOCIO) -> (Condicion medica a declarar) <- (Condicion registrada, condicion fuera del catalogo, condicion ya declarada, fecha de diagnostico futura o cuenta sin ficha de socio) --- (162. Declarar una condicion medica propia) -> (Socio_Patologia -- id_socio - id_patologia - fecha_diagnostico - observaciones) <- (Socio -- id_socio) <- (Patologia -- id_patologia - nombre - descripcion) <- (Socio_Patologia -- id_socio - id_patologia)
```

**163. Quitar una condicion medica propia**  
`DELETE /portal/mis-patologias/{id_patologia}`

```
(SOCIO) -> (id_patologia) <- (Condicion quitada, no la tenia registrada, o cuenta sin ficha de socio) --- (163. Quitar una condicion medica propia) -> (Socio_Patologia -- id_socio - id_patologia - fecha_diagnostico - observaciones) <- (Socio -- id_socio) <- (Socio_Patologia -- id_socio - id_patologia)
```

**164. Consultar las clases disponibles para anotarme**  
`GET /portal/mis-turnos/disponibles`

```
(SOCIO) -> (dias) <- (Listado de clases habilitadas con cupo, lugares libres, gente en espera y el estado de mi propia reserva, o acceso denegado por no tener ficha de socio) --- (164. Consultar las clases disponibles para anotarme) <- (Socio -- id_socio) <- (Turno -- id_turno - id_actividad - id_profesor - fecha - hora - cupo_maximo - estado) <- (Actividad -- id_actividad - nombre - minutos_tolerancia - horas_anticipacion_cancelacion) <- (Reserva -- id_reserva - id_turno - id_socio - estado) <- (Profesor -- id_profesor - id_empleado) <- (Empleado -- id_empleado - id_persona) <- (Persona -- nombre - apellido)
```

**165. Cancelar mi reserva y promover la lista de espera**  
`POST /portal/mis-turnos/{id_reserva}/cancelar`

```
(SOCIO) -> (id_reserva) <- (Reserva cancelada y, si libero lugar, el primero de la lista de espera promovido y avisado por mail; o rechazo por reserva inexistente, ajena o ya cancelada) --- (165. Cancelar mi reserva y promover la lista de espera) -> (Reserva -- estado - fecha_cancelacion) <- (Reserva -- id_reserva - id_turno - id_socio - id_inscripcion - estado - fecha_reserva) <- (Socio -- id_socio - id_persona) <- (Persona -- nombre - apellido - email) <- (Turno -- id_turno - id_actividad - fecha - hora - cupo_maximo - estado) <- (Actividad -- id_actividad - nombre - horas_anticipacion_cancelacion) <- (Inscripcion_Actividad -- id_inscripcion - id_plan_actividad) <- (Plan_Actividad -- id_plan_actividad - tipo_limite - cantidad)
```

**166. Comprar mi clase suelta**  
`POST /portal/mis-turnos/{id_turno}/clase-suelta`

```
(SOCIO) -> (Compra de clase suelta) <- (Clase suelta pagada y lugar reservado, o rechazo por turno inexistente o cancelado, cuota no al dia, socio ya anotado, cupo completo o actividad sin plan de clase suelta cargado) --- (166. Comprar mi clase suelta) -> (Pago -- id_socio - id_sede - metodo - monto - fecha_pago - periodo_desde - periodo_hasta - estado) -> (Reserva -- id_turno - id_socio - id_pago - fecha_reserva - estado) <- (Socio -- id_socio - id_persona - id_sede) <- (Persona -- nombre - apellido) <- (Turno -- id_turno - id_actividad - fecha - hora - cupo_maximo - estado) <- (Actividad -- id_actividad - nombre) <- (Reserva -- id_reserva - id_turno - id_socio - estado) <- (Membresia -- id_socio - estado - fecha_vencimiento) <- (Plan_Actividad -- id_plan_actividad - id_actividad - tipo_limite - precio - activo)
```

**167. Reservar mi lugar en una clase**  
`POST /portal/mis-turnos/{id_turno}/reservar`

```
(SOCIO) -> (id_turno) <- (Reserva confirmada, lugar en lista de espera, o rechazo por clase inexistente, cancelada, ya empezada, socio ya anotado, membresia en pausa, sin membresia o cuota que vence antes de la clase) --- (167. Reservar mi lugar en una clase) -> (Reserva -- id_turno - id_socio - fecha_reserva - estado) <- (Socio -- id_socio - id_persona) <- (Persona -- nombre - apellido) <- (Turno -- id_turno - id_actividad - fecha - hora - cupo_maximo - estado) <- (Actividad -- id_actividad - nombre) <- (Reserva -- id_reserva - id_turno - id_socio - estado) <- (Membresia -- id_socio - estado - fecha_vencimiento)
```


## Procesos automaticos

**168. Descargar los videos de YouTube que les faltan a los ejercicios**  
`Automatico — Proceso aparte en el servidor FTP, pasada cada VIDEOS_INTERVALO_MIN minutos (10 por defecto) o una sola con --una-vez`

```
(ENTRENADOR) -> (Pasada del demonio) <- (Videos nuevos descargados al disco, omitidos por no ser del canal oficial, o reintentados en la proxima pasada si el link o la base fallaron) --- (168. Descargar los videos de YouTube que les faltan a los ejercicios) <- (Ejercicio -- url_video)
```

**169. Generar los turnos de las proximas semanas desde los horarios**  
`Automatico — Arranque del backend (turnos.generar_turnos desde el lifespan); el mismo proceso lo dispara el boton Generar turnos de Actividades`

```
(DUENO / RECEPCIONISTA) -> (Ventana de dias a generar) <- (Turnos creados hasta 4 semanas adelante, o ninguno si no hay horarios activos o ya existian todos) --- (169. Generar los turnos de las proximas semanas desde los horarios) -> (Turno -- id_sede - id_actividad - fecha - hora - cupo_maximo - estado - id_profesor - id_entrenador_a_cargo - id_horario_actividad) <- (Horario_Actividad -- id_horario_actividad - id_sede - id_actividad - dia_semana - hora - cupo - id_profesor - id_entrenador_a_cargo - vigente_desde - vigente_hasta - activo) <- (Turno -- id_sede - id_actividad - fecha - hora)
```

**170. Mantener despierto el compute de Neon y disparar el mantenimiento diario**  
`Automatico — Hilo daemon temporizado, cada 120 segundos, arrancado por el lifespan`

```
(DUENO) -> (Temporizador de 2 minutos) <- (Conexion viva, mantenimiento diario disparado o latido perdido en silencio) --- (170. Mantener despierto el compute de Neon y disparar el mantenimiento diario) <- ()
```

**171. Asegurar el dueno inicial con cuenta de acceso**  
`Automatico — Arranque del backend (seeder.ejecutar_seeder, llamado desde el lifespan)`

```
(DUENO) -> (Datos del dueno inicial del .env) <- (Dueno con cuenta creado con cambio de contrasena obligatorio, rol corregido, username ya tomado o seeding omitido por falta de .env) --- (171. Asegurar el dueno inicial con cuenta de acceso) -> (Persona -- dni - nombre - apellido - email) -> (Dueno -- id_persona - porcentaje_participacion) -> (Usuario -- id_persona - username - password_hash - debe_cambiar_password - activo) <- (Usuario -- id_usuario - username - id_persona) <- (Persona -- id_persona - dni - nombre - apellido) <- (Dueno -- id_persona) <- (Sede -- id_sede)
```

**172. Preparar la base y el pool al arrancar**  
`Automatico — Arranque del backend (main.lifespan, corre una vez antes del primer pedido)`

```
(DUENO) -> (Arranque del backend) <- (Esquema verificado, pool caliente, hilo de latido en marcha, seeder y mantenimiento encadenados y aviso de modo simulado; o arranque abortado si la base no responde) --- (172. Preparar la base y el pool al arrancar y encadenar el seeder, las bajas vencidas y la generacion de turnos) <- ()
```

**173. Aplicar las bajas programadas que ya vencieron**  
`Automatico — Arranque del backend, una vez por dia desde el hilo de latido y al leer socios (listado del personal y portal del socio)`

```
(DUENO / RECEPCIONISTA / SOCIO) -> (Fecha de hoy) <- (Socios dados de baja al llegar la fecha programada, con las reservas futuras canceladas, los lugares liberados promovidos de la lista de espera y la cuenta de acceso desactivada si la baja fue por mora o administrativa; o ninguna baja vencida) --- (173. Aplicar las bajas programadas que ya vencieron) -> (Baja -- pendiente) -> (Socio -- activo) -> (Membresia -- estado) -> (Reserva -- estado - fecha_cancelacion) -> (Usuario -- activo) <- (Baja -- id_baja - id_socio - fecha_baja - pendiente - tipo) <- (Socio -- id_socio - id_persona - activo) <- (Membresia -- id_membresia - id_socio - estado) <- (Reserva -- id_reserva - id_socio - id_turno - estado) <- (Turno -- id_turno - fecha - estado - cupo_maximo) <- (Persona -- id_persona) <- (Usuario -- id_usuario - id_persona - activo)
```


---

## Resumen

| | |
|---|---|
| Procesos totales | **173** |
| Rutas de la API cubiertas | 167 de 167 |
| Procesos que corren solos | 6 |
| Tablas del esquema referenciadas | 41 de 41 |
| Líneas que pasan la validación de nombres | 173 de 173 |

Las tablas que más se escriben son `Usuario`, `Reserva` y `Membresia`; las que más se leen,
`Usuario`, `Persona` y `Socio` — consecuencia de que casi todo proceso valida la sesión y
resuelve a qué persona pertenece lo que se pide.
