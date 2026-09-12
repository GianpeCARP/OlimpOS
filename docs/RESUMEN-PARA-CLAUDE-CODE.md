# OlimpOS — Resumen para Claude Code

**FORGE · Contexto de negocio + cambios de esta sesión de diseño de base**

`schema.sql` y `seed.sql` ya están actualizados y son la versión definitiva.
Este documento es el resumen de **qué cambió y por qué**, para que el trabajo en
el código (backend, endpoints) se alinee sin tener que releer toda la sesión.

---

## El negocio, en cuatro ideas

**Qué es.** Sistema de gestión para un gimnasio de una sola sede (previsto para
multi-sede, no usado todavía). Vende tres actividades — Musculación, Yoga, Boxeo —
cada una en tres modalidades (semanal, mensual, clase suelta), más la membresía
general que da acceso al lugar.

**Cómo se cobra.** Prepago puro. Sin débito automático. Sin membresía activa no
hay acceso, y por eso **no existe tabla de deudas**: el estado "debe" se deduce.
Perjuicio del gimnasio (cierre, refacción) → se congela la membresía, no se
devuelve plata. Baja voluntaria a mitad de período → se pierde el saldo, sin
compensación. Reembolso solo en casos residuales (cobro duplicado) y siempre
**total**, nunca parcial.

**Nada se borra.** Pagos, bajas, turnos y reservas se marcan (CANCELADO,
REEMBOLSADO, etc.), nunca se eliminan filas.

**El principio rector:** si un dato se puede derivar de otro, no se guarda. Por
eso no hay peso "actual" en Socio (sale de Registro_Salud), no hay estados
ASISTIO/AUSENTE (se deducen de si hay fila en Asistencia), y ahora tampoco hay
contador de clases restantes (se cuenta contando Reserva).

---

## Cambios aplicados en esta sesión

### 1. Ocho columnas de estado pasaron a `NOT NULL`
Un estado nulo se saltaba el control de cupo del trigger de reservas (por lógica
de tres valores, `NULL IS DISTINCT FROM 'RESERVADA'` da verdadero) y además
escapaba de los índices únicos parciales. Afecta: Membresia, Reserva, Pago, Turno,
Inscripcion_Actividad, Asignacion_Rutina, Asignacion_Dieta, Asignacion_Entrenador.

### 2. Una sola membresía ACTIVA por socio
Nuevo índice único parcial `membresia_una_activa_uidx`. Consecuencia directa:
**la renovación anticipada no crea la membresía nueva al cobrar**. Si
`Pago.es_adelanto = true`, el pago queda con `id_membresia = NULL` y el período
cubierto en `periodo_desde`/`periodo_hasta`; la membresía nueva se crea recién
cuando vence la anterior. Si el backend crea la membresía nueva al momento del
pago adelantado, va a chocar contra este índice.

### 3. Promoción: solo descuento porcentual
Se eliminó `Promocion.monto_fijo_descuento`. Cualquier código que maneje
descuentos de monto fijo en promociones queda obsoleto. `Promocion.id_dueno` se
mantuvo (hace falta para promociones sin sede) pero ahora está atado por una FK
compuesta `(id_sede, id_dueno) → Sede` que garantiza coherencia cuando sí hay
sede.

### 4. Comida — el catálogo es obligatorio
`Comida.id_catalogo_comida` es ahora `NOT NULL`. El nutricionista **siempre**
arma la dieta con platos del catálogo. Se eliminaron `Comida.calorias` y
`Comida.descripcion` (redundantes contra `Catalogo_Comida` una vez que el
catálogo dejó de ser opcional).

**Asimetría a tener presente:** `Registro_Comida` (lo que el socio come de
verdad) NO está atado al catálogo — tiene una columna `comida_ingerida` de texto
libre, sin FK. Es deliberado: el socio come lo que quiere, no lo que el
nutricionista catalogó.

### 5. `Inscripcion_Actividad.clases_restantes` eliminada
El consumo se calcula al vuelo contando `Reserva`. Si el backend tenía lógica que
leía o actualizaba ese contador, hay que reemplazarla por un `COUNT` sobre
Reserva filtrado por inscripción y estado.

### 6. Nuevo trigger: `trg_reserva_coherente`
Cierra dos agujeros que antes no tenían ningún control:

- Una inscripción a Yoga permitía reservar un turno de Boxeo (nada ataba la
  actividad de ambas).
- Un socio podía usar la inscripción de otro socio.

Ahora, al insertar o actualizar una `Reserva` con `id_inscripcion` no nulo, se
valida que la actividad de la inscripción coincida con la del turno, y que el
socio de la inscripción coincida con el de la reserva. Si no coincide, la
transacción falla con un mensaje explícito. **Es diferido** (valida al COMMIT).

Si el backend ya hacía esta validación en código, es redundante pero no rompe
nada. Si no la hacía, este trigger es la única barrera y hay que capturar el
error de base de datos en el endpoint de reservas.

### 7. Limpieza menor
Se eliminó un índice redundante (`registro_ejercicio_socio_idx`, prefijo exacto
de otro ya existente). No tiene impacto funcional, solo de rendimiento en
escritura.

---

## Lo que NO cambió (para evitar reprocesar)

- La estructura de Persona → Socio/Empleado y los cuatro subtipos de empleado
  (Entrenador, Profesor, Nutricionista, Recepcionista) sigue igual.
- El sistema de Turno/Horario_Actividad/Reserva sigue igual salvo el trigger
  nuevo del punto 6.
- Rutinas (Rutina → Rutina_Ejercicio → Asignacion_Rutina → Registro_Ejercicio)
  no tuvo cambios.
- Conteo final: **41 tablas, 288 columnas, 66 FK, 13 enums, 8 triggers.**

---

## Contradicciones y pendientes que el backend debería resolver

Esto no se tocó en esta sesión de base de datos, pero es información de negocio
relevante para el código:

1. **`backend/routers/asistencia.py`** tiene un docstring *"EL SISTEMA INFORMA,
   NO JUZGA"* que registra el ingreso igual con la cuota vencida. Contradice la
   política de "sin membresía activa no hay acceso". Hay que decidir cuál rige y
   alinear el código.
2. Si existen endpoints de `/deudas/*`, están huérfanos: no hay tabla `Deuda` en
   este esquema.
3. La regla de congelamientos solapados (quedarse con el de fecha de fin más
   lejana) está documentada en el esquema pero no implementada en ningún lado
   todavía — ni trigger ni backend.

---

**Archivos de referencia completos, si hace falta más detalle:**
`schema.sql`, `seed.sql`, `AUDITORIA-ESTRUCTURAL.md`, `OLIMPOS-GUIA-COMPLETA.md`.
