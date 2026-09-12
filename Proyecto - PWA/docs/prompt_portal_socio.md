Portal del SOCIO — versión detallada. Refuerza el prompt anterior con foco en SIMPLICIDAD y REUTILIZACIÓN. La regla que manda acá es: no construir nada nuevo si ya existe algo que sirve.

=========================================================================== PRINCIPIO GENERAL: el socio es la parte MÁS SIMPLE del sistema

El personal GESTIONA (crea, edita, borra, ve listas de todos). El socio solo CONSULTA lo suyo y hace 2 o 3 acciones puntuales. Por eso sus vistas son más simples que las de admin: casi todo es solo-lectura. No le agregues tablas de gestión, ni botones de alta/baja de nada que no sea reservar o cancelar un turno y cargar su propio peso.

=========================================================================== REUTILIZAR, NO CREAR — usá estos componentes que YA existen (de ui.md)
build_topbar → el encabezado de cada vista de socio (título + saludo)
section_card → contenedor de cada bloque de info
stat_card → para números destacados (días de racha, peso actual, días para vencer la cuota)
status_badge → estado de la cuota (al día / vencida)
level_badge → nivel de la rutina asignada
progress bar → progreso físico, % de la meta
primary_button → las pocas acciones (reservar turno, guardar peso)
input_field → carga de peso, edición de datos de contacto
AppLayout+Outlet → el shell ya existe; solo se le pasa SOCIO_NAV_ITEMS

Si para una vista de socio sentís que falta un componente, avisame ANTES de crearlo — casi siempre hay uno existente que sirve con un pequeño ajuste.

=========================================================================== LAS 6 VISTAS — qué muestra cada una y qué reutiliza

Todas son SOLO LECTURA salvo donde diga explícitamente "acción".

--- 1. Mi Perfil --- Datos personales del socio + su contacto de emergencia.

section_card con sus datos (nombre, dni, email, teléfono, sede, plan)
Acción única permitida: editar SUS datos de contacto (email, teléfono, contacto de emergencia). Usa input_field. NO puede cambiar dni, sede, ni su plan.
Servicio: getMiPerfil(idSocio)

--- 2. Mi Rutina --- La rutina que le asignó su entrenador. Solo lectura total.

Reutiliza la MISMA card de rutina que ya existe en la vista de rutinas del admin (level_badge, pills de días/duración) — pero sin botones de editar/asignar/eliminar. Es la misma card en modo lectura.
Lista de ejercicios por día (de Rutina_Ejercicio): ejercicio, series, reps, descanso.
Si no tiene rutina asignada: estado vacío amable ("Todavía no tenés una rutina asignada. Tu entrenador te va a asignar una pronto.")
Servicio: getMiRutina(idSocio) → null si no tiene

--- 3. Mi Progreso --- Su historial de peso/medidas. Único lugar donde el socio CARGA datos.

stat_card con peso actual y variación desde el inicio
La barra de progreso / gráfico simple de evolución (reutiliza el patrón de barras que ya está en el dashboard)
Acción: cargar una nueva medición (peso, opcionalmente grasa/medidas). Usa input_field + primary_button. Recordá la regla del negocio: una medición por día (el back valida, acá solo el form).
Servicio: getMiProgreso(idSocio) + guardarMedicion(idSocio, datos)

--- 4. Mi Dieta --- El plan que le asignó su nutricionista. Solo lectura total.

Reutiliza la card de dieta del admin (objetivo, calorías) en modo lectura
Lista de comidas por momento del día (de la tabla Comida)
Estado vacío si no tiene dieta asignada
Servicio: getMiDieta(idSocio) → null si no tiene

--- 5. Mi Cuota --- Estado de su membresía y pagos. Solo lectura.

stat_card con "próximo vencimiento" y status_badge (al día / vencida)
Si tiene deuda: mostrarla clara pero sin botón de pago (el pago lo cobra recepción; el socio solo ve que debe). Un mensaje tipo "Acercate a recepción para regularizar."
Historial de pagos en una lista simple (fecha, monto, método, estado)
Servicio: getMiCuota(idSocio) → membresía vigente + deudas + historial

--- 6. Mis Turnos --- Reserva de turnos del día y sus asistencias. Acá SÍ hay acciones.

Ver los días/turnos disponibles con cupo (de la tabla Turno + conteo de Reservas)
Acción: reservar el turno de un día (primary_button)
Acción: cancelar una reserva propia
Lista de sus asistencias pasadas (solo lectura)
Servicios: getMisTurnos(idSocio), reservarTurno(idSocio, fecha), cancelarTurno(idSocio, idReserva)
=========================================================================== REGLA DE DATOS (la más importante, ya estaba en el prompt anterior)

TODO servicio de socio recibe idSocio (que ya está en authStore tras el login) y devuelve ÚNICAMENTE datos de ESE socio. Nunca una lista completa de otros. socioService.ts separado de authService.ts.

=========================================================================== CÓMO TRABAJARLO

Una vista por vez, empezando por Mi Perfil. Mostrame el plan de Mi Perfil antes de escribir código. Cuando la apruebe, seguimos con las otras 5 de a una. En el plan de cada vista, decime EXPLÍCITAMENTE qué componentes existentes vas a reutilizar y si necesitás crear alguno nuevo (y por qué).