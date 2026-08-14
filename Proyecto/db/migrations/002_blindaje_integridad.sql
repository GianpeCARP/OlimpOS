-- =============================================================================
-- 002 — Blindaje de integridad
-- =============================================================================
-- Aplica a una base YA CREADA las tres reglas de integridad que no estaban en
-- el esquema v5 y que ahora también viven en schema.sql (para bases nuevas):
--
--   (A) Ningún "empleado colgado": todo Empleado debe ser al menos uno de sus
--       subtipos (Entrenador / Nutricionista / Recepcionista / Profesor).
--   (B) Turno sin confusión de staff: nunca entrenador Y profesor a la vez, y
--       si hay profesor, tiene que estar habilitado para esa actividad.
--
-- (El tercer punto —"única sede"— es de datos de ejemplo, no de esquema: vive
--  en seed.sql, que ahora es idempotente y fija todas las referencias a una
--  sola sede. No hay nada que migrar acá para eso.)
--
-- Es idempotente: se puede correr más de una vez sin efecto adverso.
--
-- Aplicar:  SQL Editor de Neon, o  psql ... -f 002_blindaje_integridad.sql
-- Revertir: ver el bloque del final (comentado).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- PRE-VUELO: si la base YA tiene datos que violan las reglas nuevas, abortamos
-- con un mensaje claro ANTES de tocar nada. (Los triggers sólo miran escrituras
-- futuras; la FK compuesta, en cambio, fallaría sola al crearse si hubiera un
-- turno inconsistente — así que conviene avisar de antemano y no a los golpes.)
-- -----------------------------------------------------------------------------
DO $$
DECLARE
  v_colgados   int;
  v_dos_staff  int;
  v_prof_mal   int;
BEGIN
  SELECT count(*) INTO v_colgados
  FROM "Empleado" e
  WHERE NOT EXISTS (SELECT 1 FROM "Entrenador"    x WHERE x.id_empleado = e.id_empleado)
    AND NOT EXISTS (SELECT 1 FROM "Nutricionista" x WHERE x.id_empleado = e.id_empleado)
    AND NOT EXISTS (SELECT 1 FROM "Recepcionista" x WHERE x.id_empleado = e.id_empleado)
    AND NOT EXISTS (SELECT 1 FROM "Profesor"      x WHERE x.id_empleado = e.id_empleado);

  SELECT count(*) INTO v_dos_staff
  FROM "Turno"
  WHERE id_entrenador_a_cargo IS NOT NULL AND id_profesor IS NOT NULL;

  SELECT count(*) INTO v_prof_mal
  FROM "Turno" t
  WHERE t.id_profesor IS NOT NULL
    AND NOT EXISTS (
      SELECT 1 FROM "Profesor_Actividad" pa
      WHERE pa.id_profesor = t.id_profesor
        AND pa.id_actividad = t.id_actividad
    );

  IF v_colgados > 0 OR v_dos_staff > 0 OR v_prof_mal > 0 THEN
    RAISE EXCEPTION E'No se puede aplicar el blindaje: hay datos existentes que lo violan.\n'
      '  - Empleados sin subtipo: %\n'
      '  - Turnos con entrenador Y profesor a la vez: %\n'
      '  - Turnos con profesor NO habilitado para la actividad: %\n'
      'Corregí esas filas y volvé a correr esta migración.',
      v_colgados, v_dos_staff, v_prof_mal;
  END IF;
END $$;

-- -----------------------------------------------------------------------------
-- (A) Empleado sin subtipo
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION trg_empleado_debe_tener_subtipo()
RETURNS trigger AS $$
DECLARE
  v_id_empleado int;
  v_existe      boolean;
  v_tiene       boolean;
BEGIN
  IF TG_TABLE_NAME = 'Empleado' THEN
    v_id_empleado := NEW.id_empleado;
  ELSE
    v_id_empleado := OLD.id_empleado;
  END IF;

  SELECT EXISTS(SELECT 1 FROM "Empleado" WHERE id_empleado = v_id_empleado)
    INTO v_existe;
  IF NOT v_existe THEN
    RETURN NULL;
  END IF;

  SELECT
       EXISTS(SELECT 1 FROM "Entrenador"    WHERE id_empleado = v_id_empleado)
    OR EXISTS(SELECT 1 FROM "Nutricionista" WHERE id_empleado = v_id_empleado)
    OR EXISTS(SELECT 1 FROM "Recepcionista" WHERE id_empleado = v_id_empleado)
    OR EXISTS(SELECT 1 FROM "Profesor"      WHERE id_empleado = v_id_empleado)
    INTO v_tiene;

  IF NOT v_tiene THEN
    RAISE EXCEPTION
      'Empleado % no tiene subtipo. Todo empleado debe ser al menos uno de: Entrenador, Nutricionista, Recepcionista o Profesor.',
      v_id_empleado
      USING ERRCODE = 'check_violation';
  END IF;

  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_empleado_completo ON "Empleado";
CREATE CONSTRAINT TRIGGER trg_empleado_completo
  AFTER INSERT ON "Empleado"
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION trg_empleado_debe_tener_subtipo();

DROP TRIGGER IF EXISTS trg_entrenador_no_deja_colgado ON "Entrenador";
CREATE CONSTRAINT TRIGGER trg_entrenador_no_deja_colgado
  AFTER DELETE OR UPDATE OF id_empleado ON "Entrenador"
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION trg_empleado_debe_tener_subtipo();

DROP TRIGGER IF EXISTS trg_nutri_no_deja_colgado ON "Nutricionista";
CREATE CONSTRAINT TRIGGER trg_nutri_no_deja_colgado
  AFTER DELETE OR UPDATE OF id_empleado ON "Nutricionista"
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION trg_empleado_debe_tener_subtipo();

DROP TRIGGER IF EXISTS trg_recep_no_deja_colgado ON "Recepcionista";
CREATE CONSTRAINT TRIGGER trg_recep_no_deja_colgado
  AFTER DELETE OR UPDATE OF id_empleado ON "Recepcionista"
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION trg_empleado_debe_tener_subtipo();

DROP TRIGGER IF EXISTS trg_profesor_no_deja_colgado ON "Profesor";
CREATE CONSTRAINT TRIGGER trg_profesor_no_deja_colgado
  AFTER DELETE OR UPDATE OF id_empleado ON "Profesor"
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION trg_empleado_debe_tener_subtipo();

-- -----------------------------------------------------------------------------
-- (B) Confusión de staff en Turno
-- -----------------------------------------------------------------------------
ALTER TABLE "Turno" DROP CONSTRAINT IF EXISTS chk_turno_un_solo_staff;
ALTER TABLE "Turno" ADD CONSTRAINT chk_turno_un_solo_staff
  CHECK (NOT ("id_entrenador_a_cargo" IS NOT NULL AND "id_profesor" IS NOT NULL));

ALTER TABLE "Turno" DROP CONSTRAINT IF EXISTS fk_turno_profesor_habilitado;
ALTER TABLE "Turno" ADD CONSTRAINT fk_turno_profesor_habilitado
  FOREIGN KEY ("id_profesor", "id_actividad")
  REFERENCES "Profesor_Actividad" ("id_profesor", "id_actividad")
  DEFERRABLE INITIALLY IMMEDIATE;

-- =============================================================================
-- REVERTIR (si hiciera falta):
--   ALTER TABLE "Turno" DROP CONSTRAINT IF EXISTS fk_turno_profesor_habilitado;
--   ALTER TABLE "Turno" DROP CONSTRAINT IF EXISTS chk_turno_un_solo_staff;
--   DROP TRIGGER IF EXISTS trg_profesor_no_deja_colgado  ON "Profesor";
--   DROP TRIGGER IF EXISTS trg_recep_no_deja_colgado     ON "Recepcionista";
--   DROP TRIGGER IF EXISTS trg_nutri_no_deja_colgado     ON "Nutricionista";
--   DROP TRIGGER IF EXISTS trg_entrenador_no_deja_colgado ON "Entrenador";
--   DROP TRIGGER IF EXISTS trg_empleado_completo         ON "Empleado";
--   DROP FUNCTION IF EXISTS trg_empleado_debe_tener_subtipo();
-- =============================================================================
