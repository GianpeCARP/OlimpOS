"""
Generacion automatica de deudas.

Antes de esto NADIE creaba una Deuda nunca: la tabla estaba, el panel mostraba
"Debe $X", /mi-cuota devolvia deuda_total, habia endpoint para pagarla y hasta
un permiso gestionDeudas — y el contador daba cero siempre.

Este test manipula fechas con SQL porque no hay otra forma: para que una cuota
venza hay que esperar un mes.

    python pruebas/test_deudas.py     (con el backend levantado y la base vacia)
"""
import pathlib
import sys

# Los tests viven en pruebas/ pero importan modulos de backend/ (database,
# models). Sin esto, `python pruebas/test_x.py` falla con ModuleNotFoundError
# porque Python solo pone en sys.path el directorio del SCRIPT, no el de
# arriba. Agregarlo aca permite correrlos desde donde sea.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import json
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta

from database import SessionLocal
from deudas import DIAS_DE_GRACIA, generar_deudas
from models import Deuda, Membresia, Socio

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


def entrar(u, c, nueva=None):
    s, r = pedir("POST", "/login", {"username": u, "password": c})
    if r.get("debe_cambiar_password"):
        pedir("POST", "/cambiar-password",
              {"username": u, "password_actual": c, "password_nueva": nueva})
        s, r = pedir("POST", "/login", {"username": u, "password": nueva})
    return r.get("token")


print("=" * 74)
print("DEUDAS AUTOMATICAS")
print("=" * 74)

STAFF = entrar("dueno", "cambiar-esto-en-el-primer-ingreso", "Prueba2026!")
if not STAFF:
    print("no se pudo entrar"); sys.exit(1)

tipos = pedir("GET", "/cobros/tipos-membresia", tok=STAFF)[1]
plan = tipos[0]

print("\n0. Cinco socios con cuota, en situaciones distintas")
socios = {}
for nombre, dni in [("AlDia", "50111000"), ("Vencido", "50222000"),
                    ("Gracia", "50333000"), ("Renovo", "50444000"),
                    ("DeBaja", "50555000")]:
    s, r = pedir("POST", "/socios", {"nombre": nombre, "apellido": "T", "dni": dni,
        "email": f"{nombre.lower()}@ejemplo.com", "id_sede": 1,
        "crear_cuenta": False}, tok=STAFF)
    pedir("POST", "/cobros", {"id_socio": r["id_socio"],
          "id_tipo_membresia": plan["id_tipo_membresia"], "metodo": "EFECTIVO"}, tok=STAFF)
    socios[nombre] = r["id_socio"]
print(f"   {list(socios)}")

hoy = date.today()
db = SessionLocal()


def mover(nombre, dias_vencida):
    """Retrasa el vencimiento de la membresia de alguien."""
    m = (db.query(Membresia)
         .filter(Membresia.id_socio == socios[nombre])
         .order_by(Membresia.id_membresia.desc()).first())
    m.fecha_vencimiento = hoy - timedelta(days=dias_vencida)
    db.commit()


mover("Vencido", 30)
mover("Gracia", 1)                       # vencio ayer: dentro de la gracia
mover("Renovo", 30)
mover("DeBaja", 30)

# Renovo compra otra cuota, asi que la vencida ya no es deuda
pedir("POST", "/cobros", {"id_socio": socios["Renovo"],
      "id_tipo_membresia": plan["id_tipo_membresia"], "metodo": "EFECTIVO"}, tok=STAFF)
# DeBaja se va del gimnasio
pedir("POST", f"/socios/{socios['DeBaja']}/baja",
      {"tipo": "VOLUNTARIA", "motivo": "se muda"}, tok=STAFF)
db.expire_all()

print(f"\n   AlDia    cuota vigente")
print(f"   Vencido  vencio hace 30 dias, no renovo      -> DEBE")
print(f"   Gracia   vencio ayer (gracia = {DIAS_DE_GRACIA} dias)      -> no debe todavia")
print(f"   Renovo   vencio hace 30 pero compro otra     -> no debe")
print(f"   DeBaja   vencio hace 30 pero se dio de baja  -> no debe")

print("\n1. Se generan las deudas")
r = generar_deudas(db)
print(f"   creadas={r['creadas']}  revisadas={r['revisadas']}  ${r['monto_total']:,.2f}")

deudas = {d.id_socio: d for d in db.query(Deuda).all()}
por_nombre = {n: deudas.get(i) for n, i in socios.items()}
for n, d in por_nombre.items():
    print(f"   {n:<9} {'DEBE $' + format(float(d.monto), ',.0f') if d else '—'}")

chequear(por_nombre["Vencido"] is not None, "Vencido tiene deuda")
chequear(por_nombre["AlDia"] is None, "AlDia no")
chequear(por_nombre["Gracia"] is None, f"Gracia tampoco (dentro de los {DIAS_DE_GRACIA} dias)")
chequear(por_nombre["Renovo"] is None, "Renovo tampoco (ya pago otra)")
chequear(por_nombre["DeBaja"] is None, "DeBaja tampoco (ya no es socio)")

print("\n2. La membresia vencida quedo marcada VENCIDA")
m = (db.query(Membresia).filter(Membresia.id_socio == socios["Vencido"])
     .order_by(Membresia.id_membresia.desc()).first())
print(f"   estado: {m.estado}")
chequear(m.estado == "VENCIDA", "no sigue diciendo ACTIVA")

print("\n3. IDEMPOTENCIA: correrlo de nuevo no duplica")
antes = db.query(Deuda).count()
r2 = generar_deudas(db)
despues = db.query(Deuda).count()
print(f"   deudas: {antes} -> {despues}   (creadas={r2['creadas']})")
chequear(antes == despues and r2["creadas"] == 0, "no se duplico ninguna")

print("\n4. El monto es el PACTADO, no el precio de hoy")
d = por_nombre["Vencido"]
chequear(float(d.monto) == float(plan["precio_actual"]),
         f"${float(d.monto):,.0f} = lo que pago en su momento")
chequear(d.generada_automaticamente is True, "marcada como automatica")
print(f"   observaciones: {d.observaciones}")

print("\n5. Ahora el panel del mostrador SI lo ve")
s, res = pedir("GET", f"/recepcion/buscar?dni=50222000", tok=STAFF)
if res:
    print(f"   {res[0]['nombre']}: deuda=${res[0]['deuda_total']:,.0f}  alerta='{res[0]['alerta']}'")
    chequear(res[0]["deuda_total"] > 0, "la deuda aparece en la busqueda por DNI")
    chequear("ebe" in str(res[0]["alerta"]), "y la alerta lo dice")

print("\n6. Un socio PAUSADO no genera deuda")
s, r = pedir("POST", "/socios", {"nombre": "Pausado", "apellido": "T", "dni": "50666000",
    "email": "pausado@ejemplo.com", "id_sede": 1, "crear_cuenta": False}, tok=STAFF)
ids = r["id_socio"]
pedir("POST", "/cobros", {"id_socio": ids,
      "id_tipo_membresia": plan["id_tipo_membresia"], "metodo": "EFECTIVO"}, tok=STAFF)
m = (db.query(Membresia).filter(Membresia.id_socio == ids)
     .order_by(Membresia.id_membresia.desc()).first())
m.fecha_vencimiento = hoy - timedelta(days=30)
m.estado = "SUSPENDIDA"
db.commit()
r3 = generar_deudas(db)
tiene = db.query(Deuda).filter(Deuda.id_socio == ids).first()
print(f"   deuda para el pausado: {'SI' if tiene else 'no'}")
chequear(tiene is None,
         "pausado no debe: aviso que no venia, cobrarle seria al reves")

print("\n7. El endpoint tambien funciona")
s, r = pedir("POST", "/cobros/deudas/generar", tok=STAFF)
print(f"   {s}  {r.get('mensaje')}")
chequear(s == 200, "responde")

db.close()
print("\n" + "=" * 74)
if fallos:
    print(f"FALLARON {len(fallos)}:")
    for f in fallos:
        print("  - " + f)
else:
    print("TODOS LOS CHEQUEOS PASARON")
print("=" * 74)
sys.exit(1 if fallos else 0)
