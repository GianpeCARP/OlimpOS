"""
Promociones: descuentos sobre el precio de lista.

`Promocion` estaba modelada desde el principio y `Membresia.id_promocion` la
referencia, pero ningun endpoint la tocaba: los descuentos existian en el
esquema y no habia forma de cargarlos.

LO QUE MAS IMPORTA ACA son dos cosas:

  - El paso 4: el RECEPCIONISTA puede LISTAR promociones pero no crearlas.
    Definir un descuento es una decision de negocio; aplicarlo al cobrar es
    operativo. Si no pudiera listarlas, el selector del mostrador le daria 403
    y la funcion quedaria solo para el Dueno, que es quien menos atiende.

  - El paso 7: el descuento lo calcula el BACKEND. El cliente manda un
    id_promocion, nunca un monto. Es la misma regla que rige todo cobros.py.

    python pruebas/test_promociones.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import json
import urllib.error
import urllib.request
from datetime import date, timedelta

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


HOY = date.today()
AYER = HOY - timedelta(days=1)
MANANA = HOY + timedelta(days=1)


def iso(d):
    return d.isoformat()


print("=" * 74)
print("PROMOCIONES")
print("=" * 74)

STAFF = entrar("dueno", "cambiar-esto-en-el-primer-ingreso", "Prueba2026!")
if not STAFF:
    print("no se pudo entrar"); sys.exit(1)

print("\n0. Un recepcionista, un socio y un plar de $30.000")
s, r = pedir("POST", "/personal", {"nombre": "Rita", "apellido": "Mostrador",
    "dni": "70111000", "rol": "Recepcionista", "id_sede": 1,
    "crear_cuenta": True}, tok=STAFF)
TOK_RITA = entrar(r["username"], r["password_temporal"], "Clave2026!")

s, r = pedir("POST", "/socios", {"nombre": "Juan", "apellido": "Promo",
    "dni": "70222000", "id_sede": 1, "crear_cuenta": False}, tok=STAFF)
ID_SOCIO = r["id_socio"]

s, planes = pedir("GET", "/cobros/tipos-membresia", tok=STAFF)
PLAN = next(p for p in planes if float(p["precio_actual"]) == 30000)
ID_PLAN = PLAN["id_tipo_membresia"]
print(f"   plan '{PLAN['nombre']}' a ${PLAN['precio_actual']:,.0f}".replace(",", "."))
chequear(bool(TOK_RITA) and ID_SOCIO, "escenario armado")

# -- Alta --------------------------------------------------------------------
print("\n1. El dueno carga las promociones")
s, promo20 = pedir("POST", "/promociones", {
    "nombre": "Verano 2026", "descripcion": "20% en planes mensuales",
    "porcentaje_descuento": 20, "fecha_inicio": iso(AYER), "fecha_fin": iso(MANANA),
}, tok=STAFF)
print(f"   {s}  {promo20.get('nombre')}  {promo20.get('etiqueta')}")
chequear(s == 201, "creada")
chequear(promo20.get("etiqueta") == "20% OFF", "la etiqueta la arma el backend")
chequear(promo20.get("vigente") is True, "sale vigente")
ID_20 = promo20["id_promocion"]

# El monto fijo se eliminó por decisión comercial: TODA promo es porcentual.
# Esta segunda promo (antes de monto fijo) ahora también es un porcentaje.
s, promo30 = pedir("POST", "/promociones", {
    "nombre": "Traé un amigo", "porcentaje_descuento": 30,
    "fecha_inicio": iso(AYER), "fecha_fin": iso(MANANA),
}, tok=STAFF)
print(f"   {s}  {promo30.get('nombre')}  {promo30.get('etiqueta')}")
chequear(s == 201 and promo30.get("etiqueta") == "30% OFF", "segunda promo porcentual")
ID_FIJA = promo30["id_promocion"]

print("\n2. Una VENCIDA (para el paso 8)")
s, vencida = pedir("POST", "/promociones", {
    "nombre": "Black Friday 2025", "porcentaje_descuento": 50,
    "fecha_inicio": iso(AYER - timedelta(days=30)), "fecha_fin": iso(AYER),
}, tok=STAFF)
print(f"   {s}  activo={vencida.get('activo')}  vigente={vencida.get('vigente')}")
chequear(s == 201, "se puede cargar una con fechas pasadas")
chequear(vencida.get("activo") is True and vencida.get("vigente") is False,
         "activa pero NO vigente: son dos cosas distintas")
ID_VENCIDA = vencida["id_promocion"]

# -- Validaciones ------------------------------------------------------------
print("\n3. Lo que NO se acepta")
casos = [
    # (Ya no existe "los dos descuentos" ni "sin descuento con monto fijo":
    # el descuento es siempre porcentual y obligatorio. "sin porcentaje" cae
    # igual, por ser un campo requerido.)
    ("sin ningun descuento",
     {"nombre": "Vacia", "fecha_inicio": iso(HOY), "fecha_fin": iso(MANANA)}),
    ("termina antes de empezar",
     {"nombre": "Invertida", "porcentaje_descuento": 10,
      "fecha_inicio": iso(MANANA), "fecha_fin": iso(AYER)}),
    ("porcentaje mayor a 100",
     {"nombre": "Imposible", "porcentaje_descuento": 150,
      "fecha_inicio": iso(HOY), "fecha_fin": iso(MANANA)}),
    ("nombre repetido con otra capitalizacion",
     {"nombre": "  verano 2026  ", "porcentaje_descuento": 5,
      "fecha_inicio": iso(HOY), "fecha_fin": iso(MANANA)}),
]
for etiqueta, cuerpo in casos:
    s, r = pedir("POST", "/promociones", cuerpo, tok=STAFF)
    detalle = r.get("detail")
    if isinstance(detalle, list):
        detalle = detalle[0].get("msg", "")
    print(f"   {s}  {etiqueta}")
    chequear(s in (409, 422), f"rechazado: {etiqueta}")

# -- LO QUE MAS IMPORTA (1) --------------------------------------------------
print("\n4. EL RECEPCIONISTA LAS VE PERO NO LAS CREA")
s, lista = pedir("GET", "/promociones", tok=TOK_RITA)
print(f"   GET  -> {s}  ({len(lista) if s == 200 else lista} promos)")
chequear(s == 200, "puede listarlas: las necesita para cobrar")

s, vig = pedir("GET", "/promociones?solo_vigentes=true", tok=TOK_RITA)
print(f"   vigentes -> {[p['nombre'] for p in vig]}")
chequear(s == 200 and ID_VENCIDA not in [p["id_promocion"] for p in vig],
         "el selector del mostrador no ofrece la vencida")

for metodo, path, cuerpo in [
    ("POST", "/promociones", {"nombre": "Mia", "porcentaje_descuento": 90,
                               "fecha_inicio": iso(HOY), "fecha_fin": iso(MANANA)}),
    ("PUT", f"/promociones/{ID_20}", {"nombre": "Verano 2026",
                                       "porcentaje_descuento": 99,
                                       "fecha_inicio": iso(HOY), "fecha_fin": iso(MANANA)}),
    ("POST", f"/promociones/{ID_20}/baja", None),
]:
    s, _ = pedir(metodo, path, cuerpo, tok=TOK_RITA)
    print(f"   {s}  {metodo} {path}")
    chequear(s == 403, f"{metodo} rechazado: no puede inventar descuentos")

# -- Vista previa ------------------------------------------------------------
print("\n5. Vista previa: cuanto saldria, sin cobrar nada")
s, previa = pedir("GET", f"/promociones/{ID_20}/vista-previa?id_tipo_membresia={ID_PLAN}",
                  tok=TOK_RITA)
print(f"   {s}  lista={previa.get('precio_lista')}  desc={previa.get('descuento')}  "
      f"final={previa.get('precio_final')}")
chequear(s == 200, "el mostrador puede consultarla")
chequear(previa.get("precio_final") == 24000, "20% de 30.000 -> 24.000")

# ID_FIJA ahora es una promo del 30% (el monto fijo se eliminó): 30% de 30.000.
s, previa_30 = pedir("GET", f"/promociones/{ID_FIJA}/vista-previa?id_tipo_membresia={ID_PLAN}",
                     tok=TOK_RITA)
chequear(previa_30.get("precio_final") == 21000, "30% de 30.000 -> 21.000")

print("\n6. Y NO cobro nada (era solo una consulta)")
s, cuenta = pedir("GET", f"/cobros/socio/{ID_SOCIO}", tok=STAFF)
chequear(len(cuenta.get("ultimos_pagos", [])) == 0, "no se registro ningun pago")

# -- LO QUE MAS IMPORTA (2) --------------------------------------------------
print("\n7. EL COBRO APLICA EL DESCUENTO, Y LO CALCULA EL BACKEND")
s, cobro = pedir("POST", "/cobros", {
    "id_socio": ID_SOCIO, "id_tipo_membresia": ID_PLAN,
    "metodo": "EFECTIVO", "id_promocion": ID_20,
}, tok=TOK_RITA)
print(f"   {s}  total={cobro.get('total')}  lista={cobro.get('precio_lista')}  "
      f"desc={cobro.get('descuento')}  promo={cobro.get('promocion')}")
chequear(s == 201, "cobrado")
chequear(cobro.get("total") == 24000, "cobro 24.000 y no 30.000")
chequear(cobro.get("descuento") == 6000, "informa cuanto descontó")
chequear(cobro.get("promocion") == "Verano 2026", "y con cual promo")

print("\n   La membresia guarda CUAL promo fue")
s, cuenta = pedir("GET", f"/cobros/socio/{ID_SOCIO}", tok=STAFF)
membresia = cuenta.get("membresia_actual") or {}
print(f"   precio_pactado={membresia.get('precio_pactado')}")
chequear(float(membresia.get("precio_pactado", 0)) == 24000,
         "el precio pactado quedo con el descuento")

# -- Lo que el cobro rechaza -------------------------------------------------
print("\n8. Una promo VENCIDA no se puede aplicar")
s, r = pedir("POST", "/cobros", {
    "id_socio": ID_SOCIO, "id_tipo_membresia": ID_PLAN,
    "metodo": "EFECTIVO", "id_promocion": ID_VENCIDA,
}, tok=TOK_RITA)
print(f"   {s}  {r.get('detail')}")
chequear(s == 400, "rechazada con el motivo y las fechas")

print("\n9. Promocion y monto manual a la vez -> rechazado")
s, r = pedir("POST", "/cobros", {
    "id_socio": ID_SOCIO, "id_tipo_membresia": ID_PLAN, "metodo": "EFECTIVO",
    "id_promocion": ID_20, "monto_manual": 1000,
}, tok=STAFF)
print(f"   {s}  {r.get('detail')}")
chequear(s == 400, "son dos formas distintas de apartarse del precio de lista")

print("\n10. Una promo inexistente")
s, r = pedir("POST", "/cobros", {
    "id_socio": ID_SOCIO, "id_tipo_membresia": ID_PLAN,
    "metodo": "EFECTIVO", "id_promocion": 9999,
}, tok=TOK_RITA)
print(f"   {s}  {r.get('detail')}")
chequear(s == 404, "404")

# -- Baja y reactivacion -----------------------------------------------------
print("\n11. Cuantas veces se uso (para decidir antes de apagarla)")
s, uso = pedir("GET", f"/promociones/{ID_20}/uso", tok=STAFF)
print(f"   {s}  {uso.get('mensaje')}")
chequear(s == 200 and "1" in str(uso.get("mensaje")), "informa el uso")

print("\n12. Se da de baja, y NO se borra la fila")
s, r = pedir("POST", f"/promociones/{ID_20}/baja", tok=STAFF)
print(f"   {s}  activo={r.get('activo')}  vigente={r.get('vigente')}")
chequear(s == 200 and r.get("activo") is False, "apagada")
chequear(r.get("vigente") is False, "y por lo tanto no vigente")

s, r = pedir("GET", f"/promociones/{ID_20}", tok=STAFF)
chequear(s == 200, "la fila sigue existiendo: la referencia una membresia cobrada")

s, r = pedir("POST", "/cobros", {
    "id_socio": ID_SOCIO, "id_tipo_membresia": ID_PLAN,
    "metodo": "EFECTIVO", "id_promocion": ID_20,
}, tok=TOK_RITA)
print(f"   aplicarla ahora: {s}  {r.get('detail')}")
chequear(s == 400, "apagada, ya no se puede aplicar")

print("\n13. Y se puede volver a encender (los dos caminos, siempre)")
s, r = pedir("POST", f"/promociones/{ID_20}/reactivar", tok=STAFF)
print(f"   {s}  activo={r.get('activo')}  vigente={r.get('vigente')}")
chequear(s == 200 and r.get("activo") is True, "reactivada")
chequear(r.get("vigente") is True, "y vuelve a estar vigente")

s, r = pedir("POST", f"/promociones/{ID_20}/reactivar", tok=STAFF)
chequear(s == 400, "reactivar dos veces -> rechazado")

print("\n14. Reactivar una VENCIDA la deja activa pero NO aplicable")
pedir("POST", f"/promociones/{ID_VENCIDA}/baja", tok=STAFF)
s, r = pedir("POST", f"/promociones/{ID_VENCIDA}/reactivar", tok=STAFF)
print(f"   {s}  activo={r.get('activo')}  vigente={r.get('vigente')}  "
      f"etiqueta='{r.get('etiqueta')}'")
chequear(r.get("activo") is True and r.get("vigente") is False,
         "encenderla no le mueve las fechas")
chequear("fuera de fecha" in str(r.get("etiqueta")), "y el aviso lo dice")

print("\n15. Editar: cambiar el porcentaje actualiza la etiqueta")
s, r = pedir("PUT", f"/promociones/{ID_FIJA}", {
    "nombre": "Traé un amigo", "porcentaje_descuento": 15,
    "fecha_inicio": iso(AYER), "fecha_fin": iso(MANANA),
}, tok=STAFF)
print(f"   {s}  pct={r.get('porcentaje_descuento')}")
chequear(s == 200, "editada")
chequear(float(r.get("porcentaje_descuento")) == 15, "el porcentaje quedó en 15")
chequear(r.get("etiqueta") == "15% OFF", "y la etiqueta acompaña")

print("\n16. Editar NO recalcula lo ya cobrado")
s, cuenta = pedir("GET", f"/cobros/socio/{ID_SOCIO}", tok=STAFF)
membresia = cuenta.get("membresia_actual") or {}
chequear(float(membresia.get("precio_pactado", 0)) == 24000,
         "la membresia sigue en 24.000: el historial de plata no cambia solo")

print("\n" + "=" * 74)
if fallos:
    print(f"FALLARON {len(fallos)}:")
    for f in fallos:
        print("  - " + f)
else:
    print("TODOS LOS CHEQUEOS PASARON")
print("=" * 74)
sys.exit(1 if fallos else 0)
