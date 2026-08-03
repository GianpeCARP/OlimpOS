-- Seed inicial de OlimpOS
-- Orden: Persona -> Dueno -> Sede (cadena de dependencias NOT NULL)
-- NOTA: si ya corriste esto antes y la Sede ya existe en tu base
-- (verificar con SELECT * FROM "Sede";), NO hace falta correrlo de nuevo.

WITH nueva_persona AS (
  INSERT INTO "Persona" (dni, apellido, nombre, email)
  VALUES ('00000000', 'Admin', 'Dueño', 'dueno@olimpos.local')
  RETURNING id_persona
),
nuevo_dueno AS (
  INSERT INTO "Dueno" (id_persona, porcentaje_participacion)
  SELECT id_persona, 100.00 FROM nueva_persona
  RETURNING id_dueno
)
INSERT INTO "Sede" (id_dueno, nombre, localidad, abierto_24hs, activo)
SELECT id_dueno, 'Sede Central', 'Moreno', true, true FROM nuevo_dueno;
