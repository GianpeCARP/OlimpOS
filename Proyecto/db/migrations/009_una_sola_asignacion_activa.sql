-- =============================================================================
-- 009 — Una sola rutina y una sola dieta activa por socio
-- =============================================================================
-- La regla existia SOLO en el codigo de los routers: al asignar una rutina
-- nueva, el endpoint finalizaba la anterior. La base no sabia nada.
--
-- Se comprobo insertando dos asignaciones ACTIVA del mismo socio directo por
-- SQL: entraron las dos. El sintoma es peor que el del cupo porque es
-- silencioso — el socio queda con dos rutinas vigentes y el sistema muestra
-- las dos como buenas, sin que nada avise.
--
-- Ademas habia una asimetria: Asignacion_Rutina y Asignacion_Entrenador
-- tenian un indice unico por (socio, item, fecha) y Asignacion_Dieta NO tenia
-- ninguno, asi que la misma dieta se podia asignar dos veces el mismo dia.
--
-- POR QUE ENTRENADOR QUEDA AFUERA DE LA REGLA DE "UNA SOLA ACTIVA"
-- ================================================================
-- Porque ahi varias a la vez es lo CORRECTO, no un error: un socio con uno de
-- musculacion y otro de funcional es normal. Esta documentado en la migracion
-- 003 y es la unica de las tres asignaciones que se comporta asi. Se le
-- agrega igual el indice de (socio, item, fecha) — que ya tenia — pero NO el
-- parcial de una-sola-activa.
--
-- OJO CON EL ORDEN DE LAS ESCRITURAS
-- ==================================
-- Un indice unico PARCIAL no puede ser DEFERRABLE en Postgres (solo los
-- CONSTRAINT pueden, y un constraint no admite WHERE). Asi que se evalua al
-- terminar cada sentencia, no al confirmar la transaccion.
--
-- Eso importa mucho: el endpoint de asignar marca la anterior como FINALIZADA
-- y despues inserta la nueva, pero SQLAlchemy ordena su flush poniendo los
-- INSERT ANTES que los UPDATE. Sin un flush explicito en el medio, la nueva
-- fila entra mientras la vieja sigue ACTIVA y el indice rompe una operacion
-- que en realidad es valida.
--
-- Por eso esta migracion viene junto con un db.flush() en routers/rutinas.py
-- y routers/nutricion.py. Aplicar el SQL sin ese cambio DEJA ROTA la
-- reasignacion.
--
-- Es idempotente.
--
-- Aplicar:  SQL Editor de Neon, o  psql ... -f 009_una_sola_asignacion_activa.sql
-- Revertir: ver el bloque del final (comentado).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- PRE-VUELO: si ya hay socios con dos activas, avisar antes de crear el indice.
-- Sin esto el CREATE INDEX falla con un mensaje de Postgres que no dice cual
-- es la fila culpable.
-- -----------------------------------------------------------------------------
DO $$
DECLARE
  v_rutinas int;
  v_dietas  int;
BEGIN
  SELECT count(*) INTO v_rutinas FROM (
    SELECT id_socio FROM "Asignacion_Rutina" WHERE estado = 'ACTIVA'
    GROUP BY id_socio HAVING count(*) > 1
  ) x;

  SELECT count(*) INTO v_dietas FROM (
    SELECT id_socio FROM "Asignacion_Dieta" WHERE estado = 'ACTIVA'
    GROUP BY id_socio HAVING count(*) > 1
  ) x;

  IF v_rutinas > 0 OR v_dietas > 0 THEN
    RAISE EXCEPTION
      E'Hay socios con mas de una asignacion ACTIVA y el indice no se puede crear:\n'
      '  - con varias rutinas activas: %\n'
      '  - con varias dietas activas:  %\n'
      'Dejales una sola (poniendo las demas en FINALIZADA) y volve a correr esto.\n'
      '  SELECT id_socio, count(*) FROM "Asignacion_Rutina"\n'
      '  WHERE estado = ''ACTIVA'' GROUP BY id_socio HAVING count(*) > 1;',
      v_rutinas, v_dietas;
  END IF;
END $$;


-- -----------------------------------------------------------------------------
-- Una sola ACTIVA por socio.
--
-- El WHERE es lo que hace que esto funcione: sin el, un socio no podria tener
-- mas de UNA asignacion en toda su vida. Lo que se quiere prohibir son dos
-- vigentes al mismo tiempo, no dos a lo largo del tiempo — el historial es el
-- motivo por el que estas tablas existen.
-- -----------------------------------------------------------------------------
CREATE UNIQUE INDEX IF NOT EXISTS asignacion_rutina_una_activa_uidx
  ON "Asignacion_Rutina" ("id_socio")
  WHERE "estado" = 'ACTIVA';

CREATE UNIQUE INDEX IF NOT EXISTS asignacion_dieta_una_activa_uidx
  ON "Asignacion_Dieta" ("id_socio")
  WHERE "estado" = 'ACTIVA';


-- -----------------------------------------------------------------------------
-- El indice que le faltaba a Dieta, para que las tres tablas se comporten
-- igual en lo que si comparten: no repetir el mismo item el mismo dia.
-- -----------------------------------------------------------------------------
CREATE UNIQUE INDEX IF NOT EXISTS asignacion_dieta_socio_dieta_fecha_uidx
  ON "Asignacion_Dieta" ("id_socio", "id_dieta", "fecha_inicio");


COMMENT ON INDEX asignacion_rutina_una_activa_uidx IS
  'Un socio no puede tener dos rutinas vigentes a la vez. El historial (FINALIZADA/CANCELADA) no cuenta: para eso el indice es parcial.';
COMMENT ON INDEX asignacion_dieta_una_activa_uidx IS
  'Idem para dietas. Asignacion_Entrenador NO tiene este indice a proposito: ahi varias a la vez es correcto (musculacion + funcional).';

-- =============================================================================
-- REVERTIR:
--   DROP INDEX IF EXISTS asignacion_dieta_socio_dieta_fecha_uidx;
--   DROP INDEX IF EXISTS asignacion_dieta_una_activa_uidx;
--   DROP INDEX IF EXISTS asignacion_rutina_una_activa_uidx;
-- =============================================================================
