-- =============================================================================
-- 004 — Tolerancia de llegada por actividad
-- =============================================================================
-- Agrega Actividad.minutos_tolerancia: cuántos minutos después de la hora del
-- turno se sigue aceptando la llegada. Pasado ese margen el turno se da por
-- perdido y la tarjeta no lo valida.
--
-- POR QUÉ EN Actividad Y NO UNA CONSTANTE:
-- La tolerancia no es la misma para todo. A una clase de Yoga de 45 minutos
-- llegar 20 tarde es no ir; a la sala de musculación, que está abierta toda
-- la tarde, el concepto casi no aplica. Como constante en el código, el día
-- que se quiera que Boxeo sea más estricto que Musculación hay que tocar el
-- backend y volver a desplegarlo — una decisión de negocio que termina
-- necesitando un programador. Como columna, la cambia el dueño desde la
-- pantalla de Actividades.
--
-- POR QUÉ NO SE AGREGAN ESTADOS 'ASISTIO' / 'AUSENTE' A estado_reserva:
-- Porque los dos son DERIVABLES de lo que ya está guardado, y guardarlos
-- sería peor:
--
--   asistió  ->  existe una fila en Asistencia con id_reserva = esta reserva
--   ausente  ->  ya pasó hora + minutos_tolerancia y no existe esa fila
--
-- Persistirlos obligaría a un proceso que corra solo marcando ausentes cada
-- tanto. Ese proceso se puede caer, atrasar, o correr dos veces, y mientras
-- tanto el panel muestra como "pendiente" un turno que venció hace una hora.
-- Derivándolos no hay nada que pueda desincronizarse: si el reloj avanza, la
-- respuesta cambia sola. La única fuente de verdad sigue siendo cuándo era el
-- turno y si hay o no un registro de entrada.
--
-- El default de 15 aplica también a las actividades que ya existen. Es un
-- valor de arranque, no una regla: se ajusta por actividad desde la app.
--
-- Este cambio ya está incorporado a schema.sql. Este archivo existe para las
-- bases creadas ANTES (como la de Neon).
--
-- Es idempotente.
--
-- Aplicar:  SQL Editor de Neon, o  psql ... -f 004_tolerancia_de_turno.sql
-- Revertir: ver el bloque del final (comentado).
-- =============================================================================

ALTER TABLE "Actividad"
  ADD COLUMN IF NOT EXISTS "minutos_tolerancia" int NOT NULL DEFAULT 15;

-- Que no se pueda cargar una tolerancia absurda. El techo de 180 es
-- deliberadamente holgado: existe para atajar el dedo que escribe 1500
-- queriendo 15, no para discutir cuánto es razonable.
ALTER TABLE "Actividad" DROP CONSTRAINT IF EXISTS chk_actividad_tolerancia;
ALTER TABLE "Actividad" ADD CONSTRAINT chk_actividad_tolerancia
  CHECK ("minutos_tolerancia" >= 0 AND "minutos_tolerancia" <= 180);

COMMENT ON COLUMN "Actividad"."minutos_tolerancia" IS
  'Minutos despues de la hora del turno en que todavia se acepta la llegada. Pasado ese margen la reserva se considera ausente y la tarjeta no valida ese turno.';

-- -----------------------------------------------------------------------------
-- Índice para el panel de próximos turnos del recepcionista.
--
-- Esa pantalla hace siempre la misma consulta —los turnos habilitados de hoy
-- ordenados por hora— y se refresca sola cada pocos segundos. Sin índice es un
-- scan de toda la tabla cada vez; con turnos de un año es la consulta más
-- repetida del sistema.
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS turno_fecha_hora_estado_idx
  ON "Turno" ("fecha", "hora", "estado");

-- El panel resuelve, para cada reserva, si ya hay una entrada registrada.
-- Sin esto es un scan de Asistencia por cada fila mostrada.
CREATE INDEX IF NOT EXISTS asistencia_reserva_idx
  ON "Asistencia" ("id_reserva")
  WHERE "id_reserva" IS NOT NULL;

-- =============================================================================
-- REVERTIR:
--   DROP INDEX IF EXISTS asistencia_reserva_idx;
--   DROP INDEX IF EXISTS turno_fecha_hora_estado_idx;
--   ALTER TABLE "Actividad" DROP CONSTRAINT IF EXISTS chk_actividad_tolerancia;
--   ALTER TABLE "Actividad" DROP COLUMN IF EXISTS "minutos_tolerancia";
-- =============================================================================
