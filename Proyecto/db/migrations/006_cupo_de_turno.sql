-- =============================================================================
-- 006 — El cupo de un turno se hace cumplir en la base
-- =============================================================================
-- Hasta acá, el cupo lo controlaba SOLO el código de la aplicación. Se
-- comprobó insertando 5 reservas RESERVADA en un turno de cupo_maximo = 2: la
-- base las aceptó todas sin decir nada.
--
-- Era un agujero desde el esquema original, pero la migración 005 lo volvió
-- más grave: el sentido entero de una lista de espera es "cuando se llena,
-- el que llega después va a la cola". Si nada impide que se llene de más, esa
-- regla depende por completo de que el código cuente bien — y de que nunca
-- haya dos personas reservando el último lugar al mismo tiempo.
--
-- Es el mismo mecanismo que la migración 002 usa para el "empleado colgado":
-- un CONSTRAINT TRIGGER diferido, que se evalúa al confirmar la transacción.
--
-- HONESTIDAD SOBRE LO QUE ESTE TRIGGER SÍ Y NO RESUELVE
--
-- SÍ resuelve, y por completo:
--   - un bug de la aplicación que se olvide de contar,
--   - un INSERT hecho a mano desde el SQL Editor,
--   - un script de importación,
--   - bajarle el cupo a un turno que ya tiene más gente anotada.
--
-- NO resuelve por sí solo la carrera entre dos transacciones simultáneas.
-- Bajo el nivel de aislamiento por defecto de Postgres (READ COMMITTED),
-- dos transacciones que reservan el último lugar a la vez no se ven una a la
-- otra: cada una cuenta 19 sobre 20 y las dos confirman. Diferir el trigger
-- al commit achica muchísimo la ventana pero no la elimina.
--
-- Eso se cierra del lado de la aplicación, y ya está hecho: el endpoint de
-- reservar toma un lock sobre la fila del Turno (SELECT ... FOR UPDATE) antes
-- de contar, así la segunda transacción espera a que la primera termine y
-- cuenta el número real. Ver routers/actividades.py.
--
-- O sea: el lock evita la carrera, el trigger evita todo lo demás. Ninguno de
-- los dos reemplaza al otro y por eso están los dos.
--
-- Es idempotente.
--
-- Aplicar:  SQL Editor de Neon, o  psql ... -f 006_cupo_de_turno.sql
-- Revertir: ver el bloque del final (comentado).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- PRE-VUELO: si ya hay turnos sobrevendidos, avisar antes de crear el trigger.
--
-- El trigger sólo mira escrituras futuras, así que no fallaría al crearse;
-- pero dejar filas que lo violan es peor que no tenerlo — la próxima vez que
-- alguien toque una de esas reservas, el error va a saltar en un lugar que no
-- tiene nada que ver con la causa.
-- -----------------------------------------------------------------------------
DO $$
DECLARE
  v_sobrevendidos int;
BEGIN
  SELECT count(*) INTO v_sobrevendidos
  FROM (
    SELECT r.id_turno
    FROM "Reserva" r
    JOIN "Turno" t ON t.id_turno = r.id_turno
    WHERE r.estado = 'RESERVADA'
    GROUP BY r.id_turno, t.cupo_maximo
    HAVING count(*) > t.cupo_maximo
  ) x;

  IF v_sobrevendidos > 0 THEN
    RAISE EXCEPTION
      E'Hay % turno(s) con mas reservas que cupo. Corregilos antes de aplicar esta migracion:\n'
      '  SELECT r.id_turno, count(*) AS reservadas, t.cupo_maximo\n'
      '  FROM "Reserva" r JOIN "Turno" t ON t.id_turno = r.id_turno\n'
      '  WHERE r.estado = ''RESERVADA''\n'
      '  GROUP BY r.id_turno, t.cupo_maximo HAVING count(*) > t.cupo_maximo;',
      v_sobrevendidos;
  END IF;
END $$;


CREATE OR REPLACE FUNCTION trg_reserva_respeta_cupo()
RETURNS trigger AS $$
DECLARE
  v_cupo      int;
  v_ocupados  int;
  v_actividad text;
BEGIN
  -- EN_ESPERA y las canceladas no ocupan lugar: por definicion la lista de
  -- espera existe para los que NO entraron. Si contaran, el turno se veria
  -- lleno con gente que no tiene lugar y la cola nunca avanzaria.
  IF NEW.estado IS DISTINCT FROM 'RESERVADA' THEN
    RETURN NULL;
  END IF;

  SELECT t.cupo_maximo, a.nombre
    INTO v_cupo, v_actividad
  FROM "Turno" t
  LEFT JOIN "Actividad" a ON a.id_actividad = t.id_actividad
  WHERE t.id_turno = NEW.id_turno;

  -- El turno pudo haberse borrado en la misma transaccion. No es asunto de
  -- este trigger: de eso se ocupa la foreign key.
  IF v_cupo IS NULL THEN
    RETURN NULL;
  END IF;

  SELECT count(*) INTO v_ocupados
  FROM "Reserva"
  WHERE id_turno = NEW.id_turno AND estado = 'RESERVADA';

  IF v_ocupados > v_cupo THEN
    RAISE EXCEPTION
      'El turno % (%) tiene cupo % y ya hay % reservas confirmadas.',
      NEW.id_turno, coalesce(v_actividad, 'sin actividad'), v_cupo, v_ocupados
      USING ERRCODE = 'check_violation';
  END IF;

  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- DEFERRABLE INITIALLY DEFERRED: se evalua al confirmar la transaccion, no
-- fila por fila. Importa para poder mover gente dentro de un mismo turno en
-- una sola transaccion (cancelar a uno y promover a otro, que es exactamente
-- lo que hace la lista de espera) sin que el estado intermedio dispare el
-- error aunque el estado final sea valido.
DROP TRIGGER IF EXISTS trg_reserva_cupo ON "Reserva";
CREATE CONSTRAINT TRIGGER trg_reserva_cupo
  AFTER INSERT OR UPDATE OF estado, id_turno ON "Reserva"
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION trg_reserva_respeta_cupo();

COMMENT ON FUNCTION trg_reserva_respeta_cupo() IS
  'Impide que un turno tenga mas reservas RESERVADA que cupo_maximo. EN_ESPERA no cuenta. No cubre la carrera entre transacciones simultaneas: de eso se ocupa el SELECT ... FOR UPDATE del endpoint de reservar.';


-- -----------------------------------------------------------------------------
-- Bajarle el cupo a un turno que ya tiene mas gente anotada tambien es una
-- forma de sobrevenderlo, y el trigger de arriba no la ve porque mira Reserva,
-- no Turno. Este la cubre.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION trg_turno_cupo_no_menor_a_reservas()
RETURNS trigger AS $$
DECLARE
  v_ocupados int;
BEGIN
  SELECT count(*) INTO v_ocupados
  FROM "Reserva"
  WHERE id_turno = NEW.id_turno AND estado = 'RESERVADA';

  IF v_ocupados > NEW.cupo_maximo THEN
    RAISE EXCEPTION
      'No se puede dejar el cupo del turno % en %: ya hay % personas anotadas.',
      NEW.id_turno, NEW.cupo_maximo, v_ocupados
      USING ERRCODE = 'check_violation';
  END IF;

  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_turno_cupo ON "Turno";
CREATE CONSTRAINT TRIGGER trg_turno_cupo
  AFTER UPDATE OF cupo_maximo ON "Turno"
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION trg_turno_cupo_no_menor_a_reservas();

-- =============================================================================
-- REVERTIR:
--   DROP TRIGGER IF EXISTS trg_turno_cupo ON "Turno";
--   DROP TRIGGER IF EXISTS trg_reserva_cupo ON "Reserva";
--   DROP FUNCTION IF EXISTS trg_turno_cupo_no_menor_a_reservas();
--   DROP FUNCTION IF EXISTS trg_reserva_respeta_cupo();
-- =============================================================================
