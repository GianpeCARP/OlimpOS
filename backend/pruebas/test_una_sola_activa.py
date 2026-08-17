"""
Una sola rutina y una sola dieta activa por socio (migracion 009).

La regla existia SOLO en el codigo de los routers. Se comprobo insertando dos
asignaciones ACTIVA del mismo socio por SQL: entraron las dos, y el sintoma es
silencioso — el socio queda con dos rutinas vigentes y el sistema muestra las
dos como buenas.

LOS DOS CHEQUEOS QUE IMPORTAN, y son opuestos:

  1. Que la BASE frene dos activas, aunque el insert no pase por la app.
  2. Que la REASIGNACION NORMAL siga funcionando. Un indice unico parcial no
     puede ser DEFERRABLE, y SQLAlchemy ordena sus INSERT antes que sus
     UPDATE: sin un flush explicito en el router, esta migracion romperia una
     operacion valida. El chequeo 2 es el que detecta eso.

    python pruebas/test_una_sola_activa.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import json
import urllib.error
import urllib.request

import sqlalchemy.exc
from sqlalchemy import text

from database import engine

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
            cuerpo = x.read()
            return x.status, (json.loads(cuerpo) if cuerpo else None)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {}


def entrar(u, c, nueva=None):
    s, r = pedir("POST", "/login", {"username": u, "password": c})
    if r.get("debe_cambiar_password"):
        pedir("POST", "/cambiar-password",
              {"username": u, "password_actual": c, "password_nueva": nueva})
        s, r = pedir("POST", "/login", {"username": u, "password": nueva})
    return r.get("token")


print("=" * 74)
print("UNA SOLA ASIGNACION ACTIVA")
print("=" * 74)

STAFF = entrar("dueno", "cambiar-esto-en-el-primer-ingreso", "Prueba2026!")
if not STAFF:
    print("no se pudo entrar"); sys.exit(1)

print("\n0. Un entrenador, un socio y dos rutinas")
s, r = pedir("POST", "/personal", {"nombre": "Vera", "apellido": "E", "dni": "90111000",
    "rol": "Entrenador", "id_sede": 1, "crear_cuenta": False}, tok=STAFF)
s, ents = pedir("GET", "/personal/entrenadores", tok=STAFF)
ID_ENT = ents[0]["id"]

s, r = pedir("POST", "/socios", {"nombre": "Lu", "apellido": "S", "dni": "90222000",
    "email": "lu@ejemplo.com", "id_sede": 1, "crear_cuenta": False}, tok=STAFF)
ID_SOCIO = r["id_socio"]

rutinas = []
for n in ["Fuerza A", "Fuerza B"]:
    s, r = pedir("POST", "/rutinas", {"nombre": n, "nivel": "Intermedio",
        "dias_por_semana": 3, "id_entrenador": ID_ENT}, tok=STAFF)
    rutinas.append(r["id_rutina"])
print(f"   rutinas: {rutinas}")

# ── CHEQUEO 2 PRIMERO: que no haya roto lo que funcionaba ────────────────────
print("\n1. Asignar la primera")
s, r = pedir("POST", f"/rutinas/{rutinas[0]}/asignar", {"id_socio": ID_SOCIO}, tok=STAFF)
print(f"   {s}  {r.get('rutina', r.get('detail'))}")
chequear(s == 201, "asignada")

print("\n2. REASIGNAR: la nueva entra y la anterior se finaliza SOLA")
print("   (es el caso que el indice podria haber roto)")
s, r = pedir("POST", f"/rutinas/{rutinas[1]}/asignar", {"id_socio": ID_SOCIO}, tok=STAFF)
print(f"   {s}  {r.get('rutina', r.get('detail'))}")
chequear(s == 201, "la reasignacion sigue funcionando")

with engine.connect() as c:
    filas = c.execute(text('''
        SELECT id_rutina, estado, fecha_fin FROM "Asignacion_Rutina"
        WHERE id_socio = :s ORDER BY id_asignacion_rutina'''), {"s": ID_SOCIO}).all()
for f in filas:
    print(f"      rutina {f[0]}: {f[1]}{'  hasta ' + str(f[2]) if f[2] else ''}")
activas = [f for f in filas if f[1] == "ACTIVA"]
chequear(len(activas) == 1, "queda UNA activa")
chequear(len(filas) == 2, "y la anterior sigue en el historial, no se borro")

print("\n3. La misma rutina otra vez")
s, r = pedir("POST", f"/rutinas/{rutinas[1]}/asignar", {"id_socio": ID_SOCIO}, tok=STAFF)
print(f"   {s}  {r.get('detail')}")
chequear(s == 409, "rechazada con mensaje claro")

# ── CHEQUEO 1: que la base lo frene aunque no pase por la app ────────────────
print("\n4. LO NUEVO: dos ACTIVAS insertadas por SQL, sin pasar por la app")
try:
    with engine.begin() as c:
        c.execute(text('''INSERT INTO "Asignacion_Rutina"
            (id_socio, id_rutina, fecha_inicio, estado)
            VALUES (:s, :r, CURRENT_DATE - 1, 'ACTIVA')'''),
            {"s": ID_SOCIO, "r": rutinas[0]})
    print("   ACEPTADO — la base dejo pasar dos activas")
    chequear(False, "la base frena dos activas")
except sqlalchemy.exc.IntegrityError as e:
    print(f"   RECHAZADO: {str(e.orig).splitlines()[0][:70]}")
    chequear(True, "la base frena dos activas")

print("\n5. Y el historial sigue permitido (dos FINALIZADAS del mismo socio)")
try:
    with engine.begin() as c:
        c.execute(text('''INSERT INTO "Asignacion_Rutina"
            (id_socio, id_rutina, fecha_inicio, estado)
            VALUES (:s, :r, CURRENT_DATE - 30, 'FINALIZADA')'''),
            {"s": ID_SOCIO, "r": rutinas[0]})
    print("   ACEPTADO")
    chequear(True, "el indice es PARCIAL: no bloquea el historial")
except sqlalchemy.exc.IntegrityError as e:
    print(f"   RECHAZADO: {str(e.orig).splitlines()[0][:70]}")
    chequear(False, "el indice es PARCIAL: no bloquea el historial")

# ── Dietas: lo mismo ─────────────────────────────────────────────────────────
print("\n6. Dietas: mismo comportamiento")
s, r = pedir("POST", "/personal", {"nombre": "Nadia", "apellido": "N", "dni": "90333000",
    "rol": "Nutricionista", "id_sede": 1, "crear_cuenta": False}, tok=STAFF)
s, nutris = pedir("GET", "/personal/nutricionistas", tok=STAFF)
dietas = []
for n in ["Volumen", "Definicion"]:
    s, r = pedir("POST", "/nutricion", {"nombre": n, "objetivo": "Masa muscular",
        "calorias_diarias": 2500, "id_nutricionista": nutris[0]["id"]}, tok=STAFF)
    dietas.append(r["id_dieta"])

s, r = pedir("POST", f"/nutricion/{dietas[0]}/asignar", {"id_socio": ID_SOCIO}, tok=STAFF)
chequear(s == 201, "primera dieta asignada")
s, r = pedir("POST", f"/nutricion/{dietas[1]}/asignar", {"id_socio": ID_SOCIO}, tok=STAFF)
print(f"   reasignar: {s}  {r.get('dieta', r.get('detail'))}")
chequear(s == 201, "la reasignacion de dieta tambien funciona")

with engine.connect() as c:
    n = c.execute(text('''SELECT count(*) FROM "Asignacion_Dieta"
        WHERE id_socio = :s AND estado = 'ACTIVA' '''), {"s": ID_SOCIO}).scalar()
print(f"   dietas activas: {n}")
chequear(n == 1, "una sola")

# ── Entrenador queda afuera de la regla, a proposito ─────────────────────────
print("\n7. ENTRENADOR sigue admitiendo VARIOS a la vez (es lo correcto ahi)")
s, r = pedir("POST", "/personal", {"nombre": "Otro", "apellido": "E", "dni": "90444000",
    "rol": "Entrenador", "id_sede": 1, "crear_cuenta": False}, tok=STAFF)
s, ents = pedir("GET", "/personal/entrenadores", tok=STAFF)
for e in ents[:2]:
    s, r = pedir("POST", f"/socios/{ID_SOCIO}/entrenadores",
                 {"id_entrenador": e["id"]}, tok=STAFF)
s, act = pedir("GET", f"/socios/{ID_SOCIO}/entrenadores?solo_activos=true", tok=STAFF)
print(f"   entrenadores activos: {[x['entrenador'] for x in act]}")
chequear(len(act) == 2, "dos a la vez, sin que la base se queje")

print("\n" + "=" * 74)
if fallos:
    print(f"FALLARON {len(fallos)}:")
    for f in fallos:
        print("  - " + f)
else:
    print("TODOS LOS CHEQUEOS PASARON")
print("=" * 74)
sys.exit(1 if fallos else 0)
