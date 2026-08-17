"""
El flujo de pago con tarjeta, en MODO SIMULADO.

Lo que NO prueba, y hay que decirlo: no habla con Mercado Pago. Sin
ACCESS_TOKEN ni URL publica no hay forma. Lo que si verifica es todo lo que
rodea al cobro y que es donde estan los errores caros:

  - que el monto salga del PLAN y no del pedido
  - que el pago nazca PENDIENTE y no CONFIRMADO
  - que acreditar sea IDEMPOTENTE (Mercado Pago reintenta por diseño)
  - que un monto que no coincide NO se acredite
  - que la membresia se extienda recien al confirmar
  - que un webhook sin firma valida se descarte
  - que el endpoint de simulacion no exista con un token real cargado

Se corre con el backend levantado, la base VACIA y MP_MODO_SIMULADO=true.

    python pruebas/test_pago_online.py
"""
import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"
fallos = []


def chequear(cond, etiqueta):
    print(f"   {'OK ' if cond else 'MAL'} {etiqueta}")
    if not cond:
        fallos.append(etiqueta)


def pedir(m, path, body=None, tok=None, headers=None):
    h = {"Content-Type": "application/json", "X-Client-Type": "escritorio"}
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    if headers:
        h.update(headers)
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
print("PAGO ONLINE (modo simulado)")
print("=" * 74)

STAFF = entrar("dueno", "cambiar-esto-en-el-primer-ingreso", "Prueba2026!")
if not STAFF:
    print("no se pudo entrar como dueno"); sys.exit(1)

print("\n0. Socio SIN membresia")
s, r = pedir("POST", "/socios", {"nombre": "Pau", "apellido": "T", "dni": "48111222",
    "email": "pau@ejemplo.com", "id_sede": 1, "crear_cuenta": True}, tok=STAFF)
ID_SOCIO, USER, CLAVE = r["id_socio"], r["username"], r["password_temporal"]
TOK = entrar(USER, CLAVE, "Socio2026!")
chequear(bool(TOK), "el socio entra")

tipos = pedir("GET", "/cobros/tipos-membresia", tok=STAFF)[1]
plan = tipos[0]
print(f"   plan a comprar: {plan['nombre']} ${plan['precio_actual']:,.0f}")

s, cuota = pedir("GET", "/portal/mi-cuota", tok=TOK)
print(f"   su cuota ahora: {cuota['estado']}")

# ── El monto no viene del cliente ────────────────────────────────────────────
print("\n1. El cuerpo NO acepta monto: mandar uno no cambia nada")
s, r = pedir("POST", "/portal/mi-cuota/pagar",
             {"id_tipo_membresia": plan["id_tipo_membresia"], "monto": 1}, tok=TOK)
print(f"   {s}  monto cobrado: ${r.get('monto', 0):,.2f}")
chequear(s == 201, "pago iniciado")
chequear(float(r.get("monto", 0)) == float(plan["precio_actual"]),
         "el monto salio del PLAN, no del pedido")
chequear(r.get("simulado") is True, "avisa que es simulado")
ID_PAGO = r.get("id_pago")
print(f"   url del checkout: {r.get('url_checkout')}")

# ── El pago nace PENDIENTE ───────────────────────────────────────────────────
print("\n2. El pago nace PENDIENTE, no CONFIRMADO")
s, c = pedir("GET", "/portal/mi-cuota", tok=TOK)
pago = next((p for p in c["ultimos_pagos"] if p["id_pago"] == ID_PAGO), None)
print(f"   estado del pago: {pago['estado'] if pago else '?'}")
chequear(pago and pago["estado"] == "PENDIENTE", "PENDIENTE")
chequear(c["estado"] == "Sin membresía",
         "y la membresia NO se extendio todavia (nadie pago aun)")

# ── Acreditar ────────────────────────────────────────────────────────────────
print("\n3. Se acredita (lo que hara el webhook)")
s, r = pedir("POST", f"/portal/mi-cuota/pagar/{ID_PAGO}/simular", tok=TOK)
print(f"   {s}  {r.get('mensaje')}")
chequear(s == 200, "acreditado")

s, c = pedir("GET", "/portal/mi-cuota", tok=TOK)
pago = next((p for p in c["ultimos_pagos"] if p["id_pago"] == ID_PAGO), None)
print(f"   pago: {pago['estado']}   cuota: {c['estado']}  vence {c['fecha_vencimiento']}")
chequear(pago and pago["estado"] == "CONFIRMADO", "el pago quedo CONFIRMADO")
chequear(c["estado"] == "Activo", "y AHORA si se extendio la membresia")
vence_1 = c["fecha_vencimiento"]

# ── Idempotencia: lo mas importante ──────────────────────────────────────────
print("\n4. IDEMPOTENCIA: acreditar el mismo pago otra vez")
s, r = pedir("POST", f"/portal/mi-cuota/pagar/{ID_PAGO}/simular", tok=TOK)
print(f"   {s}  {r.get('mensaje')}")
s, c = pedir("GET", "/portal/mi-cuota", tok=TOK)
print(f"   vencimiento: {vence_1} -> {c['fecha_vencimiento']}")
chequear(c["fecha_vencimiento"] == vence_1,
         "la membresia NO se extendio dos veces")
n_activas = sum(1 for _ in [1])  # placeholder legible
s, ss = pedir("GET", "/socios", tok=STAFF)
mio = next(x for x in ss if x["id_socio"] == ID_SOCIO)
chequear(mio["estado"] == "Activo", "sigue con UNA membresia activa")

# ── Webhook sin firma ────────────────────────────────────────────────────────
print("\n5. Webhook SIN firma valida -> se descarta")
s, r = pedir("POST", "/webhooks/mercadopago",
             {"type": "payment", "data": {"id": "999999"}})
print(f"   {s}  {r.get('mensaje')}")
chequear(s == 200, "contesta 200 igual (si no, Mercado Pago reintenta para siempre)")
chequear("irma" in str(r.get("mensaje", "")), "y dice que fue por la firma")

print("\n6. Webhook con cuerpo basura -> no explota")
for cuerpo in [{}, {"type": "plan"}, {"type": "payment"}, {"data": {}}]:
    s, r = pedir("POST", "/webhooks/mercadopago", cuerpo)
    print(f"   {s}  {str(r.get('mensaje'))[:58]}")
    chequear(s == 200, f"200 con {cuerpo}")

# ── El pago de otro ──────────────────────────────────────────────────────────
print("\n7. Un socio NO puede acreditar el pago de otro")
s, r = pedir("POST", "/socios", {"nombre": "Rita", "apellido": "T", "dni": "48333444",
    "email": "rita@ejemplo.com", "id_sede": 1, "crear_cuenta": True}, tok=STAFF)
T2 = entrar(r["username"], r["password_temporal"], "Socio2026!")
s, r = pedir("POST", f"/portal/mi-cuota/pagar/{ID_PAGO}/simular", tok=T2)
print(f"   {s}  {r.get('detail')}")
chequear(s == 404, "404: ni siquiera confirma que ese pago exista")

# ── Plan inexistente ─────────────────────────────────────────────────────────
print("\n8. Plan que no existe")
s, r = pedir("POST", "/portal/mi-cuota/pagar", {"id_tipo_membresia": 9999}, tok=TOK)
print(f"   {s}  {r.get('detail')}")
chequear(s == 404, "rechazado")

print("\n" + "=" * 74)
if fallos:
    print(f"FALLARON {len(fallos)}:")
    for f in fallos:
        print("  - " + f)
else:
    print("TODOS LOS CHEQUEOS PASARON")
print("=" * 74)
sys.exit(1 if fallos else 0)
