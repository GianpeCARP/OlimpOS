-- =============================================================================
-- 007 — Horario_Actividad tambien puede llevar entrenador
-- =============================================================================
-- Turno tiene DOS campos de staff, id_entrenador_a_cargo e id_profesor, con un
-- CHECK (migracion 002) que impide que vengan los dos a la vez.
-- Horario_Actividad, creado en la 005, quedo con uno solo: id_profesor.
--
-- La consecuencia: un turno generado a partir de un horario NUNCA puede tener
-- entrenador. Como id_actividad es generico, nada impide declarar el horario
-- semanal de Musculacion —donde el staff que corresponde es un entrenador, no
-- un profesor de clase— y el campo para decirlo directamente no existe. Se
-- crean los turnos, pero sin nadie a cargo y sin forma de asignarlo desde el
-- horario.
--
-- Fue un descuido de la 005, no una decision: la tabla se penso mirando Yoga y
-- Boxeo. Se corrige dandole a Horario_Actividad exactamente la misma forma que
-- Turno, incluida la regla de "uno u otro, no los dos".
--
-- Es idempotente.
--
-- Aplicar:  SQL Editor de Neon, o  psql ... -f 007_horario_con_entrenador.sql
-- Revertir: ver el bloque del final (comentado).
-- =============================================================================

ALTER TABLE "Horario_Actividad"
  ADD COLUMN IF NOT EXISTS "id_entrenador_a_cargo" int;

ALTER TABLE "Horario_Actividad" DROP CONSTRAINT IF EXISTS "Horario_Actividad_id_entrenador_a_cargo_fkey";
ALTER TABLE "Horario_Actividad" ADD FOREIGN KEY ("id_entrenador_a_cargo")
  REFERENCES "Entrenador" ("id_entrenador") DEFERRABLE INITIALLY IMMEDIATE;

-- Misma regla que chk_turno_un_solo_staff. Que ambos sean NULL sigue siendo
-- valido: es la sala abierta, que no tiene a nadie a cargo.
ALTER TABLE "Horario_Actividad" DROP CONSTRAINT IF EXISTS chk_horario_un_solo_staff;
ALTER TABLE "Horario_Actividad" ADD CONSTRAINT chk_horario_un_solo_staff
  CHECK (NOT ("id_entrenador_a_cargo" IS NOT NULL AND "id_profesor" IS NOT NULL));

COMMENT ON COLUMN "Horario_Actividad"."id_entrenador_a_cargo" IS
  'Entrenador a cargo, para horarios de sala. Excluyente con id_profesor, igual que en Turno.';

-- =============================================================================
-- REVERTIR:
--   ALTER TABLE "Horario_Actividad" DROP CONSTRAINT IF EXISTS chk_horario_un_solo_staff;
--   ALTER TABLE "Horario_Actividad" DROP COLUMN IF EXISTS "id_entrenador_a_cargo";
-- =============================================================================
