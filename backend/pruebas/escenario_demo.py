"""
Carga un escenario chico para MIRAR las pantallas, no para probarlas.

    .venv/Scripts/python.exe pruebas/escenario_demo.py

Complementa a vaciar_base.py: aquel deja la base en 6 filas, con lo cual las
pantallas nuevas no muestran nada —no hay socios, no hay entrenadores, el
catalogo de patologias esta vacio— y no se puede ver si quedaron bien. Este
script llena lo minimo para recorrerlas.

NO reemplaza a las suites. Las suites verifican; esto solo carga datos. Se
mantienen separados a proposito: una suite que ademas deje datos lindos para
mirar termina siendo dos cosas a medias, y ninguna suite deberia depender de
un escenario que alguien puede editar para que "se vea mejor".

Todas las cuentas quedan con contrasenas FIJAS y anotadas, distinto del alta
normal —que genera una temporal al azar y obliga a cambiarla— porque el punto
es poder entrar sin buscar nada. Estan en:

    backend/CONTRASEÑAS PARA TESTEO Y ACTUALIZADAS.txt

Corre contra el backend levantado en 127.0.0.1:8000 y espera la base recien
vaciada. Si encuentra datos, avisa y no hace nada: cargar dos veces choca con
los DNI repetidos y deja todo a medias.
"""
import json
import pathlib
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

BASE = "http://127.0.0.1:8000"

# La del dueño después de vaciar. Si ya la cambiaste, ajustá acá.
DUENO_CLAVE = "cambiar-esto-en-el-primer-ingreso"
CLAVE_DEMO = "Demo2026!"


def pedir(metodo, path, cuerpo=None, tok=None):
    cabeceras = {"Content-Type": "application/json", "X-Client-Type": "escritorio"}
    if tok:
        cabeceras["Authorization"] = f"Bearer {tok}"
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(BASE + path, data=datos, headers=cabeceras, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            crudo = r.read()
            return r.status, (json.loads(crudo) if crudo else None)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {}
    except urllib.error.URLError:
        print(f"No hay backend en {BASE}. Levantalo primero.")
        sys.exit(1)


def entrar(usuario, clave, nueva=None):
    """Login, resolviendo el cambio obligatorio si la cuenta lo pide."""
    s, r = pedir("POST", "/login", {"username": usuario, "password": clave})
    if isinstance(r, dict) and r.get("debe_cambiar_password"):
        pedir("POST", "/cambiar-password",
              {"username": usuario, "password_actual": clave, "password_nueva": nueva})
        s, r = pedir("POST", "/login", {"username": usuario, "password": nueva})
    return r.get("token") if isinstance(r, dict) else None


print("=" * 74)
print("ESCENARIO DE DEMO")
print("=" * 74)

STAFF = entrar("dueno", DUENO_CLAVE, CLAVE_DEMO)
if not STAFF:
    print(f"\nNo pude entrar como 'dueno' con «{DUENO_CLAVE}».")
    print("Corré primero: .venv/Scripts/python.exe pruebas/vaciar_base.py --si")
    print("(o ajustá DUENO_CLAVE arriba si ya la cambiaste)")
    sys.exit(1)

s, socios = pedir("GET", "/socios", tok=STAFF)
if socios:
    print(f"\nLa base ya tiene {len(socios)} socio(s). Este script espera la base vacía:")
    print("cargar dos veces choca con los DNI repetidos y deja todo a medias.")
    print("Vaciá primero con: .venv/Scripts/python.exe pruebas/vaciar_base.py --si")
    sys.exit(1)

anotar = []

# --- Franjas laborales (catálogo) -------------------------------------------
# No hay endpoint de alta de franjas (son catálogo, vienen del seed) y la base
# vacía no las trae, así que se siembran por SQL para que el selector de turno
# del recepcionista tenga opciones en la demo. Se captura la de "Tarde" para
# asignársela a Rita.
print("\n0. Franjas laborales")
id_franja_tarde = None
try:
    from database import SessionLocal  # type: ignore
    from sqlalchemy import text
    _db = SessionLocal()
    for _n, _d, _h in [("Mañana", "06:00", "14:00"),
                       ("Tarde", "14:00", "22:00"),
                       ("Noche", "22:00", "06:00")]:
        _db.execute(text(
            'INSERT INTO "Franja_Laboral" (nombre, hora_desde, hora_hasta, activo) '
            "VALUES (:n, :d, :h, true) ON CONFLICT (nombre) DO NOTHING"),
            {"n": _n, "d": _d, "h": _h})
    _db.commit()
    id_franja_tarde = _db.execute(
        text('SELECT id_franja_laboral FROM "Franja_Laboral" WHERE nombre = :n'),
        {"n": "Tarde"}).scalar()
    _db.close()
    print(f"   3 franjas cargadas (Tarde = id {id_franja_tarde})")
except Exception as e:  # noqa: BLE001
    print(f"   (no se pudieron cargar franjas: {e}) — la recepcionista queda sin turno")

# --- Personal ---------------------------------------------------------------
print("\n1. Personal")
personal = [
    ("Ana", "Gomez", "30111222", "Entrenador", {"especialidad": "Musculación"}),
    ("Beto", "Ruiz", "30111333", "Entrenador", {"especialidad": "Funcional"}),
    ("Caro", "Diaz", "30111444", "Nutricionista", {"titulo": "Lic. en Nutrición"}),
    # La franja laboral es una FK a Franja_Laboral: se le asigna "Tarde" si se
    # pudieron sembrar las franjas (id_franja_laboral es nullable si no).
    ("Rita", "Lopez", "30111555", "Recepcionista",
     {"id_franja_laboral": id_franja_tarde} if id_franja_tarde else {}),
]
for nombre, apellido, dni, rol, extra in personal:
    cuerpo = {"nombre": nombre, "apellido": apellido, "dni": dni, "rol": rol,
              "id_sede": 1, "crear_cuenta": True, **extra}
    s, r = pedir("POST", "/personal", cuerpo, tok=STAFF)
    if s != 201:
        print(f"   {s}  {nombre}: {r.get('detail')}")
        continue
    usuario = r["username"]
    entrar(usuario, r["password_temporal"], CLAVE_DEMO)
    anotar.append((usuario, CLAVE_DEMO, rol))
    print(f"   {nombre} {apellido} ({rol}) -> {usuario}")

# --- Socios -----------------------------------------------------------------
print("\n2. Socios")
socios_demo = [
    ("Juan", "Perez", "40222111", "juan.perez@ejemplo.com", "Bajar de peso"),
    ("Lucia", "Marino", "40222222", "lucia.marino@ejemplo.com", "Ganar masa muscular"),
    ("Nico", "Sosa", "40222333", "nico.sosa@ejemplo.com", "Rehabilitación de rodilla"),
]
ids_socios = {}
for nombre, apellido, dni, email, objetivo in socios_demo:
    s, r = pedir("POST", "/socios", {
        "nombre": nombre, "apellido": apellido, "dni": dni, "email": email,
        "objetivo": objetivo, "id_sede": 1, "crear_cuenta": True}, tok=STAFF)
    if s != 201:
        print(f"   {s}  {nombre}: {r.get('detail')}")
        continue
    ids_socios[nombre] = r["id_socio"]
    usuario = r["username"]
    entrar(usuario, r["password_temporal"], CLAVE_DEMO)
    anotar.append((usuario, CLAVE_DEMO, "Socio"))
    print(f"   {nombre} {apellido} (#{r['id_socio']}) -> {usuario}")

# --- Entrenador a cargo -----------------------------------------------------
# Juan queda con DOS a la vez, que es el caso que la tabla existe para
# permitir y el que hay que poder ver en pantalla. Lucia con uno solo.
print("\n3. Entrenadores a cargo")
s, entrenadores = pedir("GET", "/personal/entrenadores", tok=STAFF)
por_nombre = {e["nombre"].split()[0]: e["id"] for e in entrenadores}

# Nico tambien lleva uno: sin entrenador a cargo, la card "Tu entrenador" de
# su portal directamente no se dibuja —es lo correcto, pero entonces no hay
# forma de mirarla desde una cuenta de socio.
for socio, quienes in [("Juan", ["Ana", "Beto"]), ("Lucia", ["Ana"]), ("Nico", ["Beto"])]:
    for quien in quienes:
        if socio not in ids_socios or quien not in por_nombre:
            continue
        s, r = pedir("POST", f"/socios/{ids_socios[socio]}/entrenadores",
                     {"id_entrenador": por_nombre[quien]}, tok=STAFF)
        print(f"   {socio} <- {quien}: {s}")

# Una finalizada, para que se vea el historial en gris del modal del personal
# (y para comprobar que el socio NO la ve en su portal).
if "Lucia" in ids_socios and "Beto" in por_nombre:
    id_lucia = ids_socios["Lucia"]
    pedir("POST", f"/socios/{id_lucia}/entrenadores",
          {"id_entrenador": por_nombre["Beto"]}, tok=STAFF)
    s, asignaciones = pedir("GET", f"/socios/{id_lucia}/entrenadores", tok=STAFF)
    for a in asignaciones:
        if a["id_entrenador"] == por_nombre["Beto"]:
            pedir("POST", f"/socios/entrenadores/asignaciones/{a['id_asignacion']}/finalizar",
                  tok=STAFF)
            print(f"   Lucia <- Beto: finalizada (queda en el historial)")
            break

# --- Historial médico -------------------------------------------------------
# Lo carga el dueño y no un entrenador —que seria lo realista— porque es el
# unico token que este script tiene a mano en este punto. Da igual para el
# resultado: los dos roles tienen VER_HISTORIAL_MEDICO. El que NO la tiene es
# el Recepcionista, y eso se comprueba entrando como rita.lopez.
print("\n4. Historial médico")
catalogo = [
    ("Asma", "Vía aérea. Evitar alta intensidad sostenida sin control."),
    ("Hipertensión", "Controlar la presión antes y después del esfuerzo."),
    ("Hernia de disco", "Lumbar. Evitar carga axial."),
    ("Celiaquía", "Sin TACC. Afecta el plan nutricional, no el entrenamiento."),
    ("Diabetes tipo 2", None),
]
for nombre, desc in catalogo:
    s, r = pedir("POST", "/patologias", {"nombre": nombre, "descripcion": desc}, tok=STAFF)
    print(f"   catálogo: {nombre} ({s})")

s, cat = pedir("GET", "/patologias", tok=STAFF)
ids_pat = {p["nombre"]: p["id_patologia"] for p in cat}

asignaciones_pat = [
    ("Nico", "Hernia de disco", "2025-03-10", "L4-L5. Evitar peso muerto y sentadilla con barra."),
    ("Nico", "Asma", "2019-06-01", "Usa inhalador antes de entrenar."),
    ("Juan", "Hipertensión", "2024-11-20", "Controlada con medicación."),
    ("Lucia", "Celiaquía", None, "Sin TACC, estricto."),
]
for socio, patologia, fecha, obs in asignaciones_pat:
    if socio not in ids_socios or patologia not in ids_pat:
        continue
    s, r = pedir("POST", f"/socios/{ids_socios[socio]}/patologias", {
        "id_patologia": ids_pat[patologia], "fecha_diagnostico": fecha,
        "observaciones": obs}, tok=STAFF)
    print(f"   {socio}: {patologia} ({s})")

# --- Rutina -----------------------------------------------------------------
# Sin esto el CIRCUITO no se puede ni mirar: es la funcion estrella del portal
# del socio y necesita una rutina con ejercicios para tener algo que recorrer.
#
# Los valores estan elegidos para que el circuito se vea INTERESANTE, no para
# que sea un plan de entrenamiento realista:
#   - Distinta cantidad de series por ejercicio (2, 3 y 4), asi se ven los
#     puntitos de progreso cambiar.
#   - Descansos cortos (30-45s), para no tener que esperar dos minutos
#     mirando el contador mientras se prueba.
#   - Uno con observaciones, que en el circuito sale en amarillo.
#   - DOS dias, para que se vea que cada uno arranca su propio circuito.
print("\n5. Rutina y ejercicios")

ejercicios_base = [
    ("Sentadilla con barra", "Piernas", True),
    ("Prensa 45", "Piernas", True),
    ("Peso muerto rumano", "Piernas", False),
    ("Press banca", "Pecho", True),
    ("Aperturas con mancuernas", "Pecho", False),
    ("Remo con barra", "Espalda", False),
    ("Dominadas asistidas", "Espalda", True),
    ("Press militar", "Hombros", False),
]
ids_ejercicios = {}
for nombre, grupo, maquina in ejercicios_base:
    s, r = pedir("POST", "/rutinas/ejercicios", {
        "nombre": nombre, "grupo_muscular": grupo,
        "requiere_maquina": maquina}, tok=STAFF)
    if s == 201:
        ids_ejercicios[nombre] = r["id_ejercicio"]
print(f"   {len(ids_ejercicios)} ejercicios en el catalogo")

# El dueno no es entrenador, asi que Rutina.id_entrenador —que es NOT NULL—
# hay que mandarlo explicito. Para el, elegir el entrenador a cargo no es
# suplantar a nadie: es delegar. Lo explica RutinaCrear en schemas.py.
id_ana = por_nombre.get("Ana")

plan = [
    # (ejercicio, dia, orden, series, reps, peso, descanso, observaciones)
    ("Sentadilla con barra", 1, 1, 4, "8-10", 40.0, 45, None),
    ("Prensa 45",            1, 2, 3, "12",   80.0, 30, None),
    ("Peso muerto rumano",   1, 3, 3, "10-12", 30.0, 45,
     "Espalda recta. Si sentis tiron lumbar, bajá el peso."),
    ("Press banca",          2, 1, 4, "8",    35.0, 45, None),
    ("Aperturas con mancuernas", 2, 2, 3, "12", 10.0, 30, None),
    ("Remo con barra",       2, 3, 3, "10",   30.0, 40, None),
    ("Press militar",        2, 4, 2, "10-12", 20.0, 40, None),
]
ejercicios_rutina = []
for nombre, dia_n, orden, series, reps, peso, descanso, obs in plan:
    if nombre not in ids_ejercicios:
        continue
    ejercicios_rutina.append({
        "id_ejercicio": ids_ejercicios[nombre],
        "dia": dia_n, "orden": orden, "series": series,
        "repeticiones": reps, "peso_sugerido": peso,
        "descanso_segundos": descanso, "observaciones": obs,
    })

s, rutina = pedir("POST", "/rutinas", {
    "nombre": "Full body 2 dias",
    "objetivo": "Fuerza general",
    "nivel": "INTERMEDIO",
    "dias_por_semana": 2,
    "id_entrenador": id_ana,
    "ejercicios": ejercicios_rutina,
}, tok=STAFF)

if s == 201:
    print(f"   rutina '{rutina['nombre']}' con {len(ejercicios_rutina)} ejercicios en 2 dias")
    # A los tres socios: cualquiera sirve para probar el circuito, y asi no
    # hay que acordarse de con cual entrar.
    for nombre_socio, id_socio in ids_socios.items():
        s2, _ = pedir("POST", f"/rutinas/{rutina['id_rutina']}/asignar",
                      {"id_socio": id_socio}, tok=STAFF)
        print(f"   asignada a {nombre_socio}: {s2}")
else:
    print(f"   {s}  {rutina.get('detail')}")


# --- Promociones ------------------------------------------------------------
# Las tres combinaciones que la pantalla tiene que poder mostrar distinto:
# vigente, activa-pero-fuera-de-fecha, y dada de baja. La del medio es la que
# confunde si no se la nombra, asi que conviene tenerla cargada para mirarla.
print("\n6. Promociones")
HOY = date.today()
promos = [
    ("Verano 2026", "20% en planes mensuales", {"porcentaje_descuento": 20},
     HOY - timedelta(days=10), HOY + timedelta(days=60), "vigente"),
    ("Traé un amigo", "Descuento por referido", {"porcentaje_descuento": 15},
     HOY - timedelta(days=5), HOY + timedelta(days=30), "vigente"),
    ("Black Friday 2025", "La del año pasado", {"porcentaje_descuento": 50},
     HOY - timedelta(days=300), HOY - timedelta(days=270), "fuera de fecha"),
]
ids_promos = {}
for nombre, desc, descuento, desde, hasta, esperado in promos:
    s, r = pedir("POST", "/promociones", {
        "nombre": nombre, "descripcion": desc,
        "fecha_inicio": desde.isoformat(), "fecha_fin": hasta.isoformat(),
        **descuento}, tok=STAFF)
    if s != 201:
        print(f"   {s}  {nombre}: {r.get('detail')}")
        continue
    ids_promos[nombre] = r["id_promocion"]
    estado = "vigente" if r["vigente"] else ("dada de baja" if not r["activo"]
                                              else "fuera de fecha")
    print(f"   {nombre:<20} {r['etiqueta']:<12} {estado}")

# Una apagada a mano, para ver el tercer estado.
if "Black Friday 2025" in ids_promos:
    pedir("POST", f"/promociones/{ids_promos['Black Friday 2025']}/baja", tok=STAFF)
    print("   Black Friday 2025 -> dada de baja (tercer estado)")

# --- Un cobro CON descuento -------------------------------------------------
# Sin esto no hay ninguna membresia que muestre un precio distinto al de lista,
# y el "por que a este socio le cobramos 24.000 en vez de 30.000" no se puede
# ver en pantalla.
print("\n7. Un cobro con promoción aplicada")
s, planes = pedir("GET", "/cobros/tipos-membresia", tok=STAFF)
plan_mensual = next((p for p in planes if p["duracion_dias"] == 30), planes[0] if planes else None)
if plan_mensual and "Juan" in ids_socios and "Verano 2026" in ids_promos:
    s, cobro = pedir("POST", "/cobros", {
        "id_socio": ids_socios["Juan"],
        "id_tipo_membresia": plan_mensual["id_tipo_membresia"],
        "metodo": "EFECTIVO",
        "id_promocion": ids_promos["Verano 2026"],
    }, tok=STAFF)
    if s == 201:
        print(f"   Juan: {cobro['precio_lista']:,.0f} -> {cobro['total']:,.0f}"
              f"  (descuento {cobro['descuento']:,.0f} por «{cobro['promocion']}»)"
              .replace(",", "."))
    else:
        print(f"   {s}  {cobro.get('detail')}")

# --- Resumen ----------------------------------------------------------------
print("\n" + "=" * 74)
print("CUENTAS (anotalas en CONTRASEÑAS PARA TESTEO Y ACTUALIZADAS.txt)")
print("=" * 74)
print(f"{'USUARIO':<22} {'CONTRASEÑA':<14} ROL")
print(f"{'dueno':<22} {CLAVE_DEMO:<14} Dueño")
for usuario, clave, rol in anotar:
    print(f"{usuario:<22} {clave:<14} {rol}")
print()
print("Qué mirar:")
print("  Socios -> botón de pesa (Entrenadores): Juan tiene DOS a la vez;")
print("            Lucia tiene uno activo y otro finalizado, en gris.")
print("  Socios -> botón de estetoscopio (Historial médico): Nico tiene dos")
print("            condiciones. Con la cuenta de Rita (Recepcionista) ese")
print("            botón NO aparece — es el punto de la acción.")
print("  Portal del socio (entrá como Nico): Mi perfil -> 'Tu salud';")
print("            Mi rutina -> 'Tu entrenador'.")
print("  Cobros -> botón 'Promociones' (Flet) / panel plegado (PWA): tres")
print("            estados distintos cargados a propósito — vigente, fuera de")
print("            fecha y dada de baja. Con rita.lopez el botón NO aparece,")
print("            pero SÍ el desplegable de promociones al cobrar.")
print("  Cobros -> elegí a Juan y una promoción: aparece el renglón con las")
print("            tres cifras (lista, final y cuánto ahorra).")
print("  Portal -> Mi rutina -> 'Comenzar entrenamiento': el CIRCUITO, a")
print("            pantalla completa. Los descansos son de 30-45s para no")
print("            tener que esperar mientras se prueba.")
print("=" * 74)
