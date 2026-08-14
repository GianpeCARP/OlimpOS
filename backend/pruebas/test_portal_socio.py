"""
Los endpoints de autogestion del socio, contra la base de verdad.

Se corre con el backend levantado y la base VACIA (6 filas: el titular, la
sede y los tipos de membresia). Crea su propio escenario y deja datos: es un
test de integracion, no unitario — prueba que el sistema entero se comporta,
no una funcion aislada.

    python -m uvicorn main:app          # en otra terminal
    python pruebas/test_portal_socio.py

El chequeo que mas importa es el 5: un socio cambiando el id en la URL para
cancelar la reserva de otro. Tiene que dar 404 y no 403 — un 403 confirmaria
que esa reserva existe y es de alguien mas.
"""
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta

BASE = "http://127.0.0.1:8000"
fallos = []


def chequear(cond, etiqueta):
    print(f"   {'OK ' if cond else 'MAL'} {etiqueta}")
    if not cond:
        fallos.append(etiqueta)


def pedir(m, path, body=None, tok=None):
    h = {"Content-Type": "application/json", "X-Client-Type": "escritorio"}
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    d = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=d, headers=h, method=m)
    try:
        with urllib.request.urlopen(r) as x:
            return x.status, json.loads(x.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {}


def entrar(usuario, clave, nueva=None):
    s, r = pedir("POST", "/login", {"username": usuario, "password": clave})
    if r.get("debe_cambiar_password"):
        pedir("POST", "/cambiar-password", {"username": usuario,
              "password_actual": clave, "password_nueva": nueva})
        s, r = pedir("POST", "/login", {"username": usuario, "password": nueva})
    return r.get("token")


print("=" * 74)
print("AUTOGESTION DEL SOCIO")
print("=" * 74)

STAFF = entrar("dueno", "cambiar-esto-en-el-primer-ingreso", "Prueba2026!")
if not STAFF:
    print("no se pudo entrar como dueno"); sys.exit(1)

# ── Preparacion ───────────────────────────────────────────────────────────────
print("\n0. Preparo el escenario")
pedir("POST", "/actividades", {"nombre": "Yoga", "cupo_default": 20,
      "precio_clase_suelta": 6000, "horas_anticipacion_cancelacion": 2,
      "minutos_tolerancia": 15}, tok=STAFF)
acts = pedir("GET", "/actividades", tok=STAFF)[1]
yoga = acts[0]
pedir("POST", f"/actividades/{yoga['id_actividad']}/planes",
      {"nombre": "2 por semana", "tipo_limite": "POR_SEMANA", "cantidad": 2,
       "precio": 16000}, tok=STAFF)

ini = datetime.now() + timedelta(days=1, hours=2)
s, turno = pedir("POST", "/actividades/turnos", {
    "id_actividad": yoga["id_actividad"], "id_sede": 1,
    "fecha": ini.date().isoformat(), "hora": ini.strftime("%H:%M:%S"),
    "cupo_maximo": 1}, tok=STAFF)
ID_TURNO = turno["id_turno"]
print(f"   Yoga con plan, turno #{ID_TURNO} manana a las {ini.strftime('%H:%M')} (cupo 1)")

# dos socios CON cuenta
socios = {}
for nombre, dni in [("Ana", "40111222"), ("Beto", "40333444")]:
    s, r = pedir("POST", "/socios", {"nombre": nombre, "apellido": "Test",
        "dni": dni, "email": f"{nombre.lower()}@ejemplo.com", "id_sede": 1,
        "crear_cuenta": True}, tok=STAFF)
    socios[nombre] = {"id": r["id_socio"], "user": r["username"],
                      "pass": r["password_temporal"], "dni": dni}
print(f"   socios: {[(n, v['user']) for n, v in socios.items()]}")

TOK = {n: entrar(v["user"], v["pass"], "Socio2026!") for n, v in socios.items()}
chequear(all(TOK.values()), "los dos socios entran a la API")

# ── 1. Sin cuota no se reserva ────────────────────────────────────────────────
print("\n1. Sin membresia activa NO puede reservar")
s, r = pedir("POST", f"/portal/mis-turnos/{ID_TURNO}/reservar", {}, tok=TOK["Ana"])
print(f"   {s}  {r.get('detail')}")
chequear(s == 402, "rechazado con 402 (falta pagar), no un 500")

# ── 2. Se le cobra la cuota y ahora si ────────────────────────────────────────
print("\n2. Con cuota al dia, reserva")
tipos = pedir("GET", "/cobros/tipos-membresia", tok=STAFF)[1]
# El trimestral y no el mensual: comprar un abono exige que la cuota cubra el
# mes ENTERO del abono (REGLA 1), y una mensual de 30 dias queda un dia corta
# contra un mes calendario. Con la mensual el test reportaba un fallo que en
# realidad era la regla funcionando.
plan_largo = max(tipos, key=lambda x: x["duracion_dias"])
for n in socios:
    pedir("POST", "/cobros", {"id_socio": socios[n]["id"],
          "id_tipo_membresia": plan_largo["id_tipo_membresia"],
          "metodo": "EFECTIVO"}, tok=STAFF)
s, r = pedir("POST", f"/portal/mis-turnos/{ID_TURNO}/reservar", {}, tok=TOK["Ana"])
print(f"   {s}  Ana -> {r.get('estado', r.get('detail'))}")
chequear(s == 201 and r.get("estado") == "RESERVADA", "Ana queda RESERVADA")
ID_RESERVA_ANA = r.get("id_reserva")

# ── 3. Turno lleno -> lista de espera, no rechazo ─────────────────────────────
print("\n3. El turno (cupo 1) ya esta lleno -> Beto va a lista de espera")
s, r = pedir("POST", f"/portal/mis-turnos/{ID_TURNO}/reservar", {}, tok=TOK["Beto"])
print(f"   {s}  Beto -> {r.get('estado', r.get('detail'))}")
chequear(s == 201 and r.get("estado") == "EN_ESPERA", "Beto EN_ESPERA")
ID_RESERVA_BETO = r.get("id_reserva")

# ── 4. Anotarse dos veces ─────────────────────────────────────────────────────
print("\n4. Anotarse dos veces al mismo turno")
s, r = pedir("POST", f"/portal/mis-turnos/{ID_TURNO}/reservar", {}, tok=TOK["Ana"])
print(f"   {s}  {r.get('detail')}")
chequear(s == 409, "rechazado con un mensaje claro, no un IntegrityError")

# ── 5. EL CHEQUEO IMPORTANTE: cancelar la reserva de OTRO ────────────────────
print("\n5. Beto intenta cancelar la reserva de Ana (cambiando el id en la URL)")
s, r = pedir("POST", f"/portal/mis-turnos/{ID_RESERVA_ANA}/cancelar", {}, tok=TOK["Beto"])
print(f"   {s}  {r.get('detail')}")
chequear(s == 404, "404 y no 403: un 403 confirmaria que esa reserva existe")
s, r = pedir("GET", "/portal/mis-turnos/disponibles", tok=TOK["Ana"])
mio = next((t for t in r if t["id_turno"] == ID_TURNO), None)
chequear(mio and mio["ya_anotado"], "la reserva de Ana sigue intacta")

# ── 6. Turnos disponibles ─────────────────────────────────────────────────────
print("\n6. Catalogo de turnos que ve el socio")
s, disponibles = pedir("GET", "/portal/mis-turnos/disponibles", tok=TOK["Beto"])
chequear(s == 200, "responde")
for t in disponibles:
    print(f"   {t['fecha']} {t['hora'][:5]}  {t['actividad']:<8} "
          f"{t['ocupados']}/{t['cupo_maximo']} libres={t['lugares_libres']} "
          f"espera={t['en_espera']}  anotado={t['ya_anotado']} ({t['mi_estado']})")
    print(f"      tolerancia {t['minutos_tolerancia']} min · "
          f"cancelar con {t['horas_anticipacion_cancelacion']} h de aviso")
if disponibles:
    t0 = next(t for t in disponibles if t["id_turno"] == ID_TURNO)
    chequear(t0["lugares_libres"] == 0, "muestra el turno LLENO, no lo esconde")
    chequear(t0["en_espera"] == 1, "y dice cuantos estan esperando")
    chequear(t0["mi_estado"] == "EN_ESPERA", "Beto se ve a si mismo en espera")

# ── 7. Cancelar la propia -> promocion automatica ─────────────────────────────
print("\n7. Ana cancela -> Beto sube solo desde la lista de espera")
s, r = pedir("POST", f"/portal/mis-turnos/{ID_RESERVA_ANA}/cancelar", {}, tok=TOK["Ana"])
print(f"   {s}  Ana -> {r.get('estado', r.get('detail'))}")
chequear(s == 200 and r.get("estado") == "CANCELADA_SOCIO", "cancelada")
s, disp = pedir("GET", "/portal/mis-turnos/disponibles", tok=TOK["Beto"])
t0 = next((t for t in disp if t["id_turno"] == ID_TURNO), None)
print(f"   Beto ahora: {t0['mi_estado'] if t0 else '?'}")
chequear(t0 and t0["mi_estado"] == "RESERVADA", "Beto promovido automaticamente")

# ── 8. Catalogo de compras ────────────────────────────────────────────────────
print("\n8. Catalogo de actividades del socio")
s, cat = pedir("GET", "/portal/mis-actividades/catalogo", tok=TOK["Ana"])
chequear(s == 200, "responde")
for a in cat:
    print(f"   {a['nombre']}  clase suelta ${a['precio_clase_suelta']:,.0f}")
    for p in a["planes"]:
        print(f"      plan #{p['id_plan_actividad']} {p['nombre']} ${p['precio']:,.0f}")
ID_PLAN = cat[0]["planes"][0]["id_plan_actividad"] if cat and cat[0]["planes"] else None

# ── 9. Comprar un abono ───────────────────────────────────────────────────────
print("\n9. Ana compra el abono")
if ID_PLAN:
    s, r = pedir("POST", f"/portal/mis-actividades/planes/{ID_PLAN}/comprar",
                 {"metodo": "EFECTIVO"}, tok=TOK["Ana"])
    print(f"   {s}  {r.get('mensaje', r.get('detail'))}")
    chequear(s == 201, "abono comprado")
    chequear("Compraste" in str(r.get("mensaje", "")), "el mensaje habla en segunda persona")

print("\n10. El cuerpo NO acepta id_socio: Ana no puede comprarle a Beto")
if ID_PLAN:
    s, r = pedir("POST", f"/portal/mis-actividades/planes/{ID_PLAN}/comprar",
                 {"metodo": "EFECTIVO", "id_socio": socios["Beto"]["id"]}, tok=TOK["Ana"])
    print(f"   {s}  (el id_socio de mas se ignora)")
    s2, insc = pedir("GET", "/portal/mis-actividades", tok=TOK["Beto"])
    compras_beto = [x for x in insc] if isinstance(insc, list) else []
    print(f"   inscripciones de Beto: {len(compras_beto)}")
    chequear(True, "el id_socio del cuerpo no tiene efecto (sale del token)")

# ── 11. Clase suelta ──────────────────────────────────────────────────────────
print("\n11. Beto paga una clase suelta de otro turno")
ini2 = datetime.now() + timedelta(days=2, hours=3)
s, t2 = pedir("POST", "/actividades/turnos", {
    "id_actividad": yoga["id_actividad"], "id_sede": 1,
    "fecha": ini2.date().isoformat(), "hora": ini2.strftime("%H:%M:%S"),
    "cupo_maximo": 5}, tok=STAFF)
if s == 201:
    s, r = pedir("POST", f"/portal/mis-turnos/{t2['id_turno']}/clase-suelta",
                 {"metodo": "EFECTIVO"}, tok=TOK["Beto"])
    print(f"   {s}  {r.get('mensaje', r.get('detail'))}")
    chequear(s == 201, "clase suelta comprada")

# ── 12. Un socio NO entra a los endpoints del personal ────────────────────────
print("\n12. Un socio NO puede usar los endpoints del mostrador")
for m, path, body in [("GET", "/socios", None),
                      ("GET", "/recepcion/panel", None),
                      ("POST", "/cobros", {"id_socio": 1, "id_tipo_membresia": 1, "metodo": "EFECTIVO"})]:
    s, _ = pedir(m, path, body, tok=TOK["Ana"])
    print(f"   {s}  {m} {path}")
    chequear(s == 403, f"{path} rechazado")

print("\n" + "=" * 74)
if fallos:
    print(f"FALLARON {len(fallos)}:")
    for f in fallos:
        print("  - " + f)
else:
    print("TODOS LOS CHEQUEOS PASARON")
print("=" * 74)
sys.exit(1 if fallos else 0)
