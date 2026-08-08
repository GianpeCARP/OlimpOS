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

-- =============================================================================
-- Actividades (extensión — especificacion_definitiva_actividades.md, Fase 1.12)
-- NOTA: si ya corriste esto antes (verificar con SELECT * FROM "Actividad";),
-- no hace falta correrlo de nuevo.
-- =============================================================================

-- --- Catálogo de actividades ---
-- Musculación es una fila más acá (acceso libre, sin profesor fijo:
-- id_entrenador_a_cargo se pone por turno, no por actividad).
INSERT INTO "Actividad" (nombre, descripcion, cupo_default, precio_clase_suelta, horas_anticipacion_cancelacion, activo)
VALUES
  ('Musculación', 'Acceso libre a la sala de musculación y cardio.', 40, 3500.00, 0, true),
  ('Yoga', 'Clase de yoga para todos los niveles.', 20, 4500.00, 12, true),
  ('Boxeo', 'Clase de boxeo recreativo, grupal.', 15, 5000.00, 24, true);

-- --- Planes por actividad (uno POR_SEMANA, uno POR_MES cada una) ---
-- Musculación no lleva plan "por semana" con tope bajo (no tendría sentido
-- limitar el acceso libre a poca frecuencia): sus dos planes son mensuales,
-- con distinta cantidad de clases. Yoga y Boxeo siguen el patrón pedido.
WITH act AS (SELECT id_actividad, nombre FROM "Actividad")
INSERT INTO "Plan_Actividad" (id_actividad, nombre, tipo_limite, cantidad, precio, activo)
SELECT id_actividad, plan.nombre, plan.tipo_limite, plan.cantidad, plan.precio, true
FROM act
JOIN (VALUES
  ('Musculación', '12 clases al mes', 'POR_MES'::tipo_limite, 12, 28000.00),
  ('Musculación', '20 clases al mes', 'POR_MES'::tipo_limite, 20, 42000.00),
  ('Yoga',        '2 veces por semana', 'POR_SEMANA'::tipo_limite, 2, 15000.00),
  ('Yoga',        '8 clases al mes', 'POR_MES'::tipo_limite, 8, 26000.00),
  ('Boxeo',       '3 veces por semana', 'POR_SEMANA'::tipo_limite, 3, 20000.00),
  ('Boxeo',       '12 clases al mes', 'POR_MES'::tipo_limite, 12, 45000.00)
) AS plan(actividad, nombre, tipo_limite, cantidad, precio)
  ON plan.actividad = act.nombre;

-- --- Profesor de ejemplo (distinto de Entrenador) ---
WITH nueva_persona AS (
  INSERT INTO "Persona" (dni, apellido, nombre, email)
  VALUES ('28334455', 'Duarte', 'Romina', 'romina.duarte@olimpos.local')
  RETURNING id_persona
),
nuevo_empleado AS (
  INSERT INTO "Empleado" (id_persona, id_sede, legajo, fecha_ingreso, activo)
  SELECT p.id_persona, s.id_sede, 'E-0100', CURRENT_DATE, true
  FROM nueva_persona p, "Sede" s
  RETURNING id_empleado
)
INSERT INTO "Profesor" (id_empleado, titulo, especialidad)
SELECT id_empleado, 'Profesora de Yoga', 'Yoga y Boxeo recreativo' FROM nuevo_empleado;

-- El profesor de ejemplo dicta las dos actividades con horario fijo.
INSERT INTO "Profesor_Actividad" (id_profesor, id_actividad)
SELECT p.id_profesor, a.id_actividad
FROM "Profesor" p
CROSS JOIN "Actividad" a
WHERE a.nombre IN ('Yoga', 'Boxeo');

-- --- Turnos de ejemplo: hoy y mañana ---
-- Filas explícitas y pocas a propósito: esto es para ver el flujo andando
-- (reservar, cancelar, fichar), no el calendario real del gimnasio — eso lo
-- carga el dueño desde /turnos cuando exista esa pantalla (Fase 4).
INSERT INTO "Turno" (id_sede, id_actividad, fecha, hora, cupo_maximo, estado, id_profesor)
SELECT
  s.id_sede,
  a.id_actividad,
  t.fecha,
  t.hora,
  a.cupo_default,
  'HABILITADO'::estado_turno,
  -- Sale de Profesor_Actividad, no de "el único profesor que hay": así
  -- Musculación queda en NULL (nadie la dicta) y el resto con el profesor
  -- real, sin asumir cuántos profesores existen.
  (SELECT pa.id_profesor FROM "Profesor_Actividad" pa WHERE pa.id_actividad = a.id_actividad LIMIT 1)
FROM "Sede" s
CROSS JOIN (VALUES
  ('Musculación', CURRENT_DATE,     '08:00'::time),
  ('Musculación', CURRENT_DATE + 1, '18:00'::time),
  ('Yoga',        CURRENT_DATE,     '09:00'::time),
  ('Yoga',        CURRENT_DATE + 1, '19:00'::time),
  ('Boxeo',       CURRENT_DATE + 1, '20:00'::time)
) AS t(actividad, fecha, hora)
JOIN "Actividad" a ON a.nombre = t.actividad;
