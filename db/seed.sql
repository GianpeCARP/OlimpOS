-- =============================================================================
-- OlimpOS — seed.sql
-- =============================================================================
-- FORGE · Datos iniciales · correr DESPUÉS de schema.sql
--
-- -----------------------------------------------------------------------------
-- ES IDEMPOTENTE: se puede correr las veces que haga falta
-- -----------------------------------------------------------------------------
-- Correrlo dos veces no duplica nada ni falla. Se logra de tres maneras:
--
--   · ON CONFLICT DO NOTHING en todo lo que tiene UNIQUE (catálogos, personas
--     por DNI, actividades por nombre).
--   · WHERE NOT EXISTS en lo que no tiene UNIQUE natural pero no debe repetirse
--     (la sede, los turnos de ejemplo).
--   · Referencias resueltas por SELECT contra el nombre o el DNI, nunca con IDs
--     literales. Un id_actividad = 2 escrito a mano se rompe apenas alguien
--     inserta las actividades en otro orden.
--
-- -----------------------------------------------------------------------------
-- BLINDAJE DE SEDE ÚNICA
-- -----------------------------------------------------------------------------
-- El alta de la sede sólo ocurre si TODAVÍA no existe ninguna. Y todas las demás
-- referencias quedan fijadas a una sola fila con
--   (SELECT id_sede FROM "Sede" ORDER BY id_sede LIMIT 1)
-- en lugar de un FROM "Sede" a secas. Así, si algún día hay varias sedes, estos
-- INSERT de ejemplo NO se multiplican por sede.
--
-- -----------------------------------------------------------------------------
-- QUÉ CARGA
-- -----------------------------------------------------------------------------
--   1. Dueño y sede
--   2. Catálogos: actividades, planes, tipos de membresía, franjas laborales,
--      patologías, ejercicios y platos
--   3. Personal de ejemplo: profesora, entrenador, nutricionista, recepcionista
--   4. Turnos de hoy y mañana
--   5. Un socio completo, para poder probar el circuito de punta a punta
-- =============================================================================


-- =============================================================================
-- 1. DUEÑO Y SEDE
-- =============================================================================
-- Cadena de dependencias NOT NULL: Persona -> Dueno -> Sede. Las tres se crean
-- juntas en un solo statement con CTEs encadenadas, y sólo si no hay sede.

WITH nueva_persona AS (
  INSERT INTO "Persona" (dni, apellido, nombre, email)
  SELECT '00000000', 'Admin', 'Dueño', 'dueno@olimpos.local'
  WHERE NOT EXISTS (SELECT 1 FROM "Sede")
  ON CONFLICT (dni) DO NOTHING
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
-- 2. CATÁLOGOS
-- =============================================================================

-- --- 2.1 Actividades ---------------------------------------------------------
-- Musculación es una fila más acá: acceso libre (0 horas de anticipación para
-- cancelar) y sin profesor fijo. El id_entrenador_a_cargo se pone por turno, no
-- por actividad.
INSERT INTO "Actividad" (nombre, descripcion, cupo_default, horas_anticipacion_cancelacion, minutos_tolerancia, activo)
VALUES
  ('Musculación', 'Acceso libre a la sala de musculación y cardio.', 40,  0, 15, true),
  ('Yoga',        'Clase de yoga para todos los niveles.',          20, 12, 10, true),
  ('Boxeo',       'Clase de boxeo recreativo, grupal.',             15, 24, 10, true)
ON CONFLICT (nombre) DO NOTHING;


-- --- 2.2 Planes por actividad ------------------------------------------------
-- Musculación no lleva plan "por semana" con tope bajo: no tendría sentido
-- limitar el acceso libre a poca frecuencia. Sus dos planes son mensuales, con
-- distinta cantidad de clases. Yoga y Boxeo siguen el patrón general.
--
-- La clase suelta es un plan más del catálogo (cantidad = 1), y no una columna
-- precio_clase_suelta en Actividad. Así el sistema de inscripciones la trata
-- igual que a cualquier otro plan, sin lógica aparte.
INSERT INTO "Plan_Actividad" (id_actividad, nombre, tipo_limite, cantidad, precio, activo)
SELECT a.id_actividad, p.nombre, p.tipo_limite, p.cantidad, p.precio, true
FROM (VALUES
  ('Musculación', '12 clases al mes',   'POR_MES'::tipo_limite,      12, 28000.00),
  ('Musculación', '20 clases al mes',   'POR_MES'::tipo_limite,      20, 42000.00),
  ('Musculación', 'Clase suelta',       'CLASE_SUELTA'::tipo_limite,  1,  3500.00),
  ('Yoga',        '2 veces por semana', 'POR_SEMANA'::tipo_limite,    2, 15000.00),
  ('Yoga',        '8 clases al mes',    'POR_MES'::tipo_limite,       8, 26000.00),
  ('Yoga',        'Clase suelta',       'CLASE_SUELTA'::tipo_limite,  1,  4500.00),
  ('Boxeo',       '3 veces por semana', 'POR_SEMANA'::tipo_limite,    3, 20000.00),
  ('Boxeo',       '12 clases al mes',   'POR_MES'::tipo_limite,      12, 45000.00),
  ('Boxeo',       'Clase suelta',       'CLASE_SUELTA'::tipo_limite,  1,  5000.00)
) AS p(actividad, nombre, tipo_limite, cantidad, precio)
JOIN "Actividad" a ON a.nombre = p.actividad
WHERE NOT EXISTS (
  SELECT 1 FROM "Plan_Actividad" pl
  WHERE pl.id_actividad = a.id_actividad AND pl.nombre = p.nombre
);


-- --- 2.3 Tipos de membresía --------------------------------------------------
-- precio_actual es el precio VIGENTE. Cuando un socio contrata, se copia a
-- Membresia.precio_pactado, que es histórico y no cambia si mañana sube.
INSERT INTO "Tipo_Membresia" (nombre, descripcion, duracion_dias, precio_actual, activo)
VALUES
  ('Mensual',    'Acceso por 30 días.',   30,  35000.00, true),
  ('Trimestral', 'Acceso por 90 días.',   90,  95000.00, true),
  ('Anual',      'Acceso por 365 días.', 365, 330000.00, true)
ON CONFLICT (nombre) DO NOTHING;


-- --- 2.4 Franjas laborales ---------------------------------------------------
-- Las usa sólo Recepcionista. Los demás empleados derivan su horario de Turno y
-- Horario_Actividad, así que no la necesitan.
INSERT INTO "Franja_Laboral" (nombre, hora_desde, hora_hasta, activo)
VALUES
  ('Mañana', '06:00', '14:00', true),
  ('Tarde',  '14:00', '22:00', true),
  ('Noche',  '22:00', '06:00', true)
ON CONFLICT (nombre) DO NOTHING;


-- --- 2.5 Patologías ----------------------------------------------------------
-- Catálogo mínimo de las condiciones que importan para autorizar una rutina.
INSERT INTO "Patologia" (nombre, descripcion)
VALUES
  ('Hipertensión',       'Presión arterial elevada. Evitar isometría y Valsalva.'),
  ('Asma',               'Tener presente el inhalador en trabajo aeróbico intenso.'),
  ('Diabetes tipo 2',    'Controlar glucemia antes y después del entrenamiento.'),
  ('Hernia de disco',    'Sin carga axial sobre la columna.'),
  ('Lesión de rodilla',  'Limitar flexión profunda e impacto.'),
  ('Lesión de hombro',   'Evitar press por encima de la cabeza.')
ON CONFLICT (nombre) DO NOTHING;


-- --- 2.6 Ejercicios ----------------------------------------------------------
-- grupo_muscular es varchar libre con índice encima, así que en la práctica
-- funciona como catálogo. Mientras no sea enum, hay que escribirlo SIEMPRE igual:
-- 'Pecho', 'pecho' y 'PECHO' serían tres grupos distintos para la base.
INSERT INTO "Ejercicio" (nombre, grupo_muscular, descripcion, requiere_maquina)
VALUES
  ('Press de banca',      'Pecho',     'Acostado, barra desde el pecho hasta extensión.', true),
  ('Aperturas con mancuernas', 'Pecho', 'Apertura controlada en banco plano.',            false),
  ('Dominadas',           'Espalda',   'Colgado, subir hasta pasar el mentón la barra.',  true),
  ('Remo con barra',      'Espalda',   'Tronco inclinado, barra hacia el abdomen.',       false),
  ('Sentadilla',          'Piernas',   'Barra en trapecios, bajar hasta paralelo.',       false),
  ('Prensa de piernas',   'Piernas',   'Empuje en máquina inclinada.',                    true),
  ('Peso muerto',         'Piernas',   'Levantar desde el piso con espalda neutra.',      false),
  ('Press militar',       'Hombros',   'De pie, barra desde clavículas hacia arriba.',    false),
  ('Curl de bíceps',      'Brazos',    'Flexión de codo con barra o mancuernas.',         false),
  ('Fondos en paralelas', 'Brazos',    'Descenso y empuje en barras paralelas.',          true),
  ('Plancha abdominal',   'Core',      'Isometría en apoyo sobre antebrazos.',            false),
  ('Cinta',               'Cardio',    'Caminata o trote continuo.',                      true)
ON CONFLICT (nombre) DO NOTHING;


-- --- 2.7 Catálogo de comidas -------------------------------------------------
-- Las calorías viven acá porque dependen del PLATO, no de la dieta ni del día en
-- que aparece. Comida las toma de acá y no las repite.
INSERT INTO "Catalogo_Comida" (nombre, descripcion, calorias, activo)
VALUES
  ('Avena con leche y banana',      'Taza de avena, leche descremada, una banana.',  380, true),
  ('Tostadas con palta y huevo',    'Dos tostadas integrales, medio palta, un huevo.', 420, true),
  ('Yogur con granola',             'Yogur natural con granola sin azúcar.',         290, true),
  ('Pechuga de pollo con arroz',    'Pechuga grillada, taza de arroz integral.',     560, true),
  ('Bife con ensalada mixta',       'Bife magro, lechuga, tomate y zanahoria.',      480, true),
  ('Tarta de verduras',             'Porción de tarta casera de acelga y ricota.',   410, true),
  ('Merluza al horno con puré',     'Filet de merluza, puré de calabaza.',           390, true),
  ('Ensalada de atún y garbanzos',  'Atún al natural, garbanzos, cebolla morada.',   450, true),
  ('Batido de proteína',            'Scoop de proteína en agua o leche.',            180, true),
  ('Puñado de frutos secos',        'Almendras y nueces sin sal.',                   210, true),
  ('Fruta de estación',             'Una pieza mediana.',                             90, true)
ON CONFLICT (nombre) DO NOTHING;


-- =============================================================================
-- 3. PERSONAL DE EJEMPLO
-- =============================================================================
-- El alta va SIEMPRE en dos pasos: Empleado y después su subtipo. El blindaje de
-- "empleado sin subtipo" es un CONSTRAINT TRIGGER DIFERIDO, así que valida recién
-- al COMMIT: para ese momento la fila del subtipo ya existe y pasa. Si el trigger
-- fuera inmediato, esto sería imposible sin desactivarlo.

-- --- 3.1 Profesora (clases grupales) -----------------------------------------
WITH nueva_persona AS (
  INSERT INTO "Persona" (dni, apellido, nombre, email)
  VALUES ('28334455', 'Duarte', 'Romina', 'romina.duarte@olimpos.local')
  ON CONFLICT (dni) DO NOTHING
  RETURNING id_persona
),
nuevo_empleado AS (
  INSERT INTO "Empleado" (id_persona, id_sede, legajo, fecha_ingreso, activo)
  SELECT p.id_persona, s.id_sede, 'E-0100', CURRENT_DATE, true
  FROM nueva_persona p,
       (SELECT id_sede FROM "Sede" ORDER BY id_sede LIMIT 1) s
  RETURNING id_empleado
)
INSERT INTO "Profesor" (id_empleado, titulo, especialidad)
SELECT id_empleado, 'Profesora de Yoga', 'Yoga y Boxeo recreativo' FROM nuevo_empleado;

-- Habilitación: la profesora dicta las dos actividades con horario fijo.
-- Musculación queda afuera a propósito: no la dicta nadie.
-- Esta tabla es la que hace cumplir fk_turno_profesor_habilitado.
INSERT INTO "Profesor_Actividad" (id_profesor, id_actividad)
SELECT p.id_profesor, a.id_actividad
FROM "Profesor" p
CROSS JOIN "Actividad" a
WHERE a.nombre IN ('Yoga', 'Boxeo')
ON CONFLICT (id_profesor, id_actividad) DO NOTHING;


-- --- 3.2 Entrenador (rutinas de musculación) ---------------------------------
WITH nueva_persona AS (
  INSERT INTO "Persona" (dni, apellido, nombre, email)
  VALUES ('30112233', 'Sosa', 'Martín', 'martin.sosa@olimpos.local')
  ON CONFLICT (dni) DO NOTHING
  RETURNING id_persona
),
nuevo_empleado AS (
  INSERT INTO "Empleado" (id_persona, id_sede, legajo, fecha_ingreso, activo)
  SELECT p.id_persona, s.id_sede, 'E-0101', CURRENT_DATE, true
  FROM nueva_persona p,
       (SELECT id_sede FROM "Sede" ORDER BY id_sede LIMIT 1) s
  RETURNING id_empleado
)
INSERT INTO "Entrenador" (id_empleado, titulo, especialidad, matricula)
SELECT id_empleado, 'Profesor de Educación Física', 'Musculación e hipertrofia', 'EF-4471'
FROM nuevo_empleado;


-- --- 3.3 Nutricionista -------------------------------------------------------
WITH nueva_persona AS (
  INSERT INTO "Persona" (dni, apellido, nombre, email)
  VALUES ('33445566', 'Ferrari', 'Lucía', 'lucia.ferrari@olimpos.local')
  ON CONFLICT (dni) DO NOTHING
  RETURNING id_persona
),
nuevo_empleado AS (
  INSERT INTO "Empleado" (id_persona, id_sede, legajo, fecha_ingreso, activo)
  SELECT p.id_persona, s.id_sede, 'E-0102', CURRENT_DATE, true
  FROM nueva_persona p,
       (SELECT id_sede FROM "Sede" ORDER BY id_sede LIMIT 1) s
  RETURNING id_empleado
)
INSERT INTO "Nutricionista" (id_empleado, titulo, matricula)
SELECT id_empleado, 'Licenciada en Nutrición', 'MN-19388' FROM nuevo_empleado;


-- --- 3.4 Recepcionista -------------------------------------------------------
-- Es el único subtipo con franja laboral: no produce nada propio, sólo opera el
-- sistema, así que su horario no se puede derivar de ninguna otra tabla.
WITH nueva_persona AS (
  INSERT INTO "Persona" (dni, apellido, nombre, email)
  VALUES ('35667788', 'Gómez', 'Nahuel', 'nahuel.gomez@olimpos.local')
  ON CONFLICT (dni) DO NOTHING
  RETURNING id_persona
),
nuevo_empleado AS (
  INSERT INTO "Empleado" (id_persona, id_sede, legajo, fecha_ingreso, activo)
  SELECT p.id_persona, s.id_sede, 'E-0103', CURRENT_DATE, true
  FROM nueva_persona p,
       (SELECT id_sede FROM "Sede" ORDER BY id_sede LIMIT 1) s
  RETURNING id_empleado
)
INSERT INTO "Recepcionista" (id_empleado, id_franja_laboral)
SELECT e.id_empleado, f.id_franja_laboral
FROM nuevo_empleado e,
     (SELECT id_franja_laboral FROM "Franja_Laboral" WHERE nombre = 'Tarde') f;


-- =============================================================================
-- 4. TURNOS DE EJEMPLO
-- =============================================================================
-- Filas explícitas y pocas a propósito: esto sirve para ver el flujo andando
-- (reservar, cancelar, fichar), no para representar el calendario real. Ese lo
-- carga el dueño desde la pantalla de turnos.
--
-- El profesor sale de Profesor_Actividad y no de "el único profesor que hay". Así
-- Musculación queda en NULL (no la dicta nadie) y el resto con el profesor real,
-- sin asumir cuántos profesores existen. Además, ese profesor está garantizado
-- como habilitado para la actividad por la FK compuesta del schema.

INSERT INTO "Turno" (id_sede, id_actividad, fecha, hora, cupo_maximo, estado, id_profesor)
SELECT
  s.id_sede,
  a.id_actividad,
  t.fecha,
  t.hora,
  a.cupo_default,
  'HABILITADO'::estado_turno,
  (SELECT pa.id_profesor FROM "Profesor_Actividad" pa
    WHERE pa.id_actividad = a.id_actividad LIMIT 1)
FROM (SELECT id_sede FROM "Sede" ORDER BY id_sede LIMIT 1) s
CROSS JOIN (VALUES
  ('Musculación', CURRENT_DATE,     '08:00'::time),
  ('Musculación', CURRENT_DATE + 1, '18:00'::time),
  ('Yoga',        CURRENT_DATE,     '09:00'::time),
  ('Yoga',        CURRENT_DATE + 1, '19:00'::time),
  ('Boxeo',       CURRENT_DATE + 1, '20:00'::time)
) AS t(actividad, fecha, hora)
JOIN "Actividad" a ON a.nombre = t.actividad
WHERE NOT EXISTS (
  SELECT 1 FROM "Turno" x
  WHERE x.id_sede = s.id_sede AND x.id_actividad = a.id_actividad
    AND x.fecha = t.fecha AND x.hora = t.hora
);


-- =============================================================================
-- 5. SOCIO COMPLETO DE PRUEBA
-- =============================================================================
-- Un solo socio, pero con todo el circuito armado: membresía activa, inscripción
-- a una actividad, una medición de salud y una patología. Sirve para probar de
-- punta a punta sin tener que cargar nada a mano.

WITH nueva_persona AS (
  INSERT INTO "Persona" (dni, apellido, nombre, sexo, email, calle, numero_calle, localidad, fecha_nacimiento)
  VALUES ('42556677', 'Ríos', 'Camila', 'F', 'camila.rios@ejemplo.com', 'Av. Libertador', '1450', 'Moreno', '2006-04-18')
  ON CONFLICT (dni) DO NOTHING
  RETURNING id_persona
)
INSERT INTO "Socio" (id_persona, id_sede, numero_socio, codigo_rfid, fecha_alta, objetivo, activo)
SELECT p.id_persona, s.id_sede, 'S-0001', 'RFID-0001', CURRENT_DATE,
       'Tonificar y mejorar resistencia', true
FROM nueva_persona p,
     (SELECT id_sede FROM "Sede" ORDER BY id_sede LIMIT 1) s;

-- --- 5.1 Membresía activa ----------------------------------------------------
-- precio_pactado se COPIA de precio_actual: queda congelado en lo que se cobró
-- hoy, y no cambia si mañana el dueño actualiza la lista.
-- El índice membresia_una_activa_uidx impide que este socio tenga otra ACTIVA.
INSERT INTO "Membresia" (id_socio, id_tipo_membresia, precio_pactado, fecha_inicio, fecha_vencimiento, estado)
SELECT so.id_socio, tm.id_tipo_membresia, tm.precio_actual,
       CURRENT_DATE, CURRENT_DATE + tm.duracion_dias, 'ACTIVA'::estado_membresia
FROM "Socio" so
CROSS JOIN "Tipo_Membresia" tm
WHERE so.numero_socio = 'S-0001' AND tm.nombre = 'Mensual'
  AND NOT EXISTS (
    SELECT 1 FROM "Membresia" m
    WHERE m.id_socio = so.id_socio AND m.estado = 'ACTIVA'
  );

-- --- 5.2 Pago de esa membresía -----------------------------------------------
INSERT INTO "Pago" (id_socio, id_membresia, id_sede, metodo, monto, periodo_desde, periodo_hasta, es_adelanto, estado, numero_comprobante)
SELECT m.id_socio, m.id_membresia, so.id_sede, 'TRANSFERENCIA'::metodo_pago,
       m.precio_pactado, m.fecha_inicio, m.fecha_vencimiento, false,
       'CONFIRMADO'::estado_pago, 'COMP-000001'
FROM "Membresia" m
JOIN "Socio" so ON so.id_socio = m.id_socio
WHERE so.numero_socio = 'S-0001' AND m.estado = 'ACTIVA'
ON CONFLICT (numero_comprobante) DO NOTHING;

-- --- 5.3 Inscripción a Yoga --------------------------------------------------
-- Con esta inscripción el socio puede reservar turnos de Yoga y SÓLO de Yoga:
-- el trigger trg_reserva_coherente rechaza usarla para un turno de Boxeo.
INSERT INTO "Inscripcion_Actividad" (id_socio, id_plan_actividad, precio_pactado, fecha_inicio, fecha_vencimiento, estado)
SELECT so.id_socio, pl.id_plan_actividad, pl.precio,
       CURRENT_DATE, CURRENT_DATE + 30, 'ACTIVA'::estado_inscripcion
FROM "Socio" so
JOIN "Plan_Actividad" pl ON pl.nombre = '8 clases al mes'
JOIN "Actividad" a ON a.id_actividad = pl.id_actividad AND a.nombre = 'Yoga'
WHERE so.numero_socio = 'S-0001'
  AND NOT EXISTS (
    SELECT 1 FROM "Inscripcion_Actividad" i
    WHERE i.id_socio = so.id_socio AND i.id_plan_actividad = pl.id_plan_actividad
  );

-- --- 5.4 Medición de salud ---------------------------------------------------
-- El peso actual del socio NO se guarda en Socio: sale de acá con
--   ORDER BY fecha DESC LIMIT 1
INSERT INTO "Registro_Salud" (id_socio, fecha, peso, altura, grasa_corporal, masa_muscular)
SELECT id_socio, CURRENT_DATE, 58.40, 1.65, 24.10, 41.30
FROM "Socio" WHERE numero_socio = 'S-0001'
ON CONFLICT (id_socio, fecha) DO NOTHING;

-- --- 5.5 Patología declarada -------------------------------------------------
INSERT INTO "Socio_Patologia" (id_socio, id_patologia, fecha_diagnostico, observaciones)
SELECT so.id_socio, pa.id_patologia, CURRENT_DATE - 400,
       'Controlada con inhalador. Avisar antes de trabajo aeróbico intenso.'
FROM "Socio" so
CROSS JOIN "Patologia" pa
WHERE so.numero_socio = 'S-0001' AND pa.nombre = 'Asma'
ON CONFLICT (id_socio, id_patologia) DO NOTHING;


-- =============================================================================
-- FIN DEL SEED
-- =============================================================================
-- Para verificar que quedó todo cargado:
--
--   SELECT 'Actividades', count(*) FROM "Actividad"
--   UNION ALL SELECT 'Planes',      count(*) FROM "Plan_Actividad"
--   UNION ALL SELECT 'Ejercicios',  count(*) FROM "Ejercicio"
--   UNION ALL SELECT 'Platos',      count(*) FROM "Catalogo_Comida"
--   UNION ALL SELECT 'Empleados',   count(*) FROM "Empleado"
--   UNION ALL SELECT 'Turnos',      count(*) FROM "Turno"
--   UNION ALL SELECT 'Socios',      count(*) FROM "Socio";
--
-- Para comprobar que el trigger nuevo funciona, esto TIENE que fallar — usa la
-- inscripción de Yoga del socio S-0001 para reservar el turno de Boxeo:
--
--   INSERT INTO "Reserva" (id_turno, id_socio, id_inscripcion)
--   SELECT t.id_turno, so.id_socio, i.id_inscripcion
--   FROM "Socio" so
--   JOIN "Inscripcion_Actividad" i ON i.id_socio = so.id_socio
--   JOIN "Turno" t ON t.id_actividad = (SELECT id_actividad FROM "Actividad" WHERE nombre = 'Boxeo')
--   WHERE so.numero_socio = 'S-0001' LIMIT 1;
--
-- El error esperado es "Una inscripcion solo sirve para su propia actividad".
-- Como el trigger es DIFERIDO, el error aparece al COMMIT y no al INSERT: si lo
-- probás dentro de un BEGIN, vas a verlo recién cuando cierres la transacción.
-- =============================================================================
