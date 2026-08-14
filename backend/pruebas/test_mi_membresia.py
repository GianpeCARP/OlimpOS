"""
Congelamiento y baja propia, contra la base de verdad.

Se corre con el backend levantado y la base VACIA.

    python -m uvicorn main:app          # en otra terminal
    python pruebas/test_mi_membresia.py

Lo que mas importa acá es el chequeo final: darse de baja NO tiene que
desactivar la cuenta. Si la desactivara, el socio apretaria el boton, perderia
la sesion en el acto y no podria volver a entrar ni para ver su historial —
quedaria dependiendo del mostrador justo cuando decidio dejar de depender de
el. (Es el mismo agujero que el Dueño desactivandose a si mismo, que ya
aparecio en este proyecto y hubo que arreglar entrando a la base a mano.)
"""
import json
import sys
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
print("CONGELAR Y DARSE DE BAJA")
print("=" * 74)

STAFF = entrar("dueno", "cambiar-esto-en-el-primer-ingreso", "Prueba2026!")
if not STAFF:
    print("no se pudo entrar como dueno"); sys.exit(1)

print("\n0. Socio con cuota al dia")
s, r = pedir("POST", "/socios", {"nombre": "Caro", "apellido": "Test",
    "dni": "41555666", "email": "caro@ejemplo.com", "id_sede": 1,
    "crear_cuenta": True}, tok=STAFF)
ID_SOCIO, USER, CLAVE = r["id_socio"], r["username"], r["password_temporal"]
tipos = pedir("GET", "/cobros/tipos-membresia", tok=STAFF)[1]
plan = max(tipos, key=lambda x: x["duracion_dias"])
pedir("POST", "/cobros", {"id_socio": ID_SOCIO,
      "id_tipo_membresia": plan["id_tipo_membresia"], "metodo": "EFECTIVO"}, tok=STAFF)
TOK = entrar(USER, CLAVE, "Socio2026!")
chequear(bool(TOK), "el socio entra")

s, cuota = pedir("GET", "/portal/mi-cuota", tok=TOK)
vence_antes = cuota.get("fecha_vencimiento")
print(f"   vence: {vence_antes}")

# ── Validaciones ──────────────────────────────────────────────────────────────
print("\n1. Pausa demasiado corta")
s, r = pedir("POST", "/portal/mi-membresia/congelar",
             {"fecha_fin": (date.today() + timedelta(days=3)).isoformat()}, tok=TOK)
print(f"   {s}  {r.get('detail')}")
chequear(s == 400, "rechazada")

print("\n2. Congelar hacia atras")
s, r = pedir("POST", "/portal/mi-membresia/congelar",
             {"fecha_inicio": (date.today() - timedelta(days=5)).isoformat(),
              "fecha_fin": (date.today() + timedelta(days=20)).isoformat()}, tok=TOK)
print(f"   {s}  {r.get('detail')}")
chequear(s == 400, "rechazada")

print("\n3. Mas dias que el tope anual")
s, r = pedir("POST", "/portal/mi-membresia/congelar",
             {"fecha_fin": (date.today() + timedelta(days=200)).isoformat()}, tok=TOK)
print(f"   {s}  {r.get('detail')}")
chequear(s == 400, "rechazada")

# ── El caso feliz ─────────────────────────────────────────────────────────────
print("\n4. Congela 30 dias por viaje")
s, cong = pedir("POST", "/portal/mi-membresia/congelar",
                {"fecha_fin": (date.today() + timedelta(days=30)).isoformat(),
                 "motivo": "Viaje"}, tok=TOK)
print(f"   {s}  pidio {cong.get('dias_pedidos')} dias, estado={cong.get('estado')}")
chequear(s == 201 and cong.get("estado") == "ACTIVO", "congelada")

print("\n5. Congelada NO puede reservar (la membresia queda SUSPENDIDA)")
s, acts = pedir("GET", "/actividades", tok=STAFF)
if not acts:
    pedir("POST", "/actividades", {"nombre": "Yoga", "cupo_default": 10,
          "precio_clase_suelta": 5000, "horas_anticipacion_cancelacion": 2,
          "minutos_tolerancia": 15}, tok=STAFF)
    acts = pedir("GET", "/actividades", tok=STAFF)[1]
ini = date.today() + timedelta(days=2)
s, turno = pedir("POST", "/actividades/turnos", {
    "id_actividad": acts[0]["id_actividad"], "id_sede": 1,
    "fecha": ini.isoformat(), "hora": "19:00:00", "cupo_maximo": 5}, tok=STAFF)
s, r = pedir("POST", f"/portal/mis-turnos/{turno['id_turno']}/reservar", {}, tok=TOK)
print(f"   {s}  {r.get('detail')}")
chequear(s == 402, "no puede reservar mientras esta de pausa")

print("\n6. Pedir otra pausa estando congelado")
s, r = pedir("POST", "/portal/mi-membresia/congelar",
             {"fecha_fin": (date.today() + timedelta(days=10)).isoformat()}, tok=TOK)
print(f"   {s}  {r.get('detail')}")
chequear(s == 409, "rechazada")

# ── Reanudar antes ────────────────────────────────────────────────────────────
print("\n7. Vuelve HOY: se le suman los dias reales, no los 30 pedidos")
s, r = pedir("POST", "/portal/mi-membresia/reanudar", {}, tok=TOK)
print(f"   {s}  {r.get('mensaje')}")
chequear(s == 200, "reanudada")
chequear(r.get("dias_aplicados") == 0,
         "volvio el mismo dia -> 0 dias sumados, no 30")

s, cuota = pedir("GET", "/portal/mi-cuota", tok=TOK)
print(f"   vencimiento: {vence_antes} -> {cuota.get('vencimiento')}")
chequear(cuota.get("fecha_vencimiento") == vence_antes,
         "el vencimiento no se movio (no estuvo dias congelado)")

print("\n8. Ya reanudada, vuelve a poder reservar")
s, r = pedir("POST", f"/portal/mis-turnos/{turno['id_turno']}/reservar", {}, tok=TOK)
print(f"   {s}  {r.get('estado', r.get('detail'))}")
chequear(s == 201, "reserva de nuevo")

print("\n9. El historial queda")
s, hist = pedir("GET", "/portal/mi-membresia/congelamientos", tok=TOK)
for c in hist:
    print(f"   {c['fecha_inicio']} -> {c['fecha_fin']}  pedidos={c['dias_pedidos']} "
          f"aplicados={c['dias_aplicados']}  {c['estado']}  {c['motivo']}")
chequear(len(hist) == 1 and hist[0]["estado"] == "FINALIZADO", "una pausa finalizada")

# ── Baja propia ───────────────────────────────────────────────────────────────
print("\n10. Se da de baja")
s, r = pedir("POST", "/portal/mi-membresia/baja", {"motivo": "Me mudo"}, tok=TOK)
print(f"   {s}  {r.get('mensaje', r.get('detail'))}")
chequear(s == 200, "dado de baja")

print("\n11. LO IMPORTANTE: la cuenta NO se desactivo")
nuevo_token = entrar(USER, "Socio2026!")
print(f"   vuelve a entrar: {bool(nuevo_token)}")
chequear(bool(nuevo_token), "puede volver a entrar despues de darse de baja")
if nuevo_token:
    s, perfil = pedir("GET", "/portal/mi-perfil", tok=nuevo_token)
    print(f"   y ve su perfil: {s}")
    chequear(s == 200, "accede a su historial")

print("\n12. Su reserva futura se libero")
s, reservas = pedir("GET", f"/actividades/turnos/{turno['id_turno']}/reservas", tok=STAFF)
activas = [x for x in reservas if x["estado"] == "RESERVADA"]
print(f"   reservas activas en el turno: {len(activas)}")
chequear(len(activas) == 0, "el lugar quedo libre para otro socio")

print("\n13. Darse de baja dos veces")
s, r = pedir("POST", "/portal/mi-membresia/baja", {}, tok=nuevo_token)
print(f"   {s}  {r.get('detail')}")
chequear(s == 400, "rechazado")

print("\n" + "=" * 74)
if fallos:
    print(f"FALLARON {len(fallos)}:")
    for f in fallos:
        print("  - " + f)
else:
    print("TODOS LOS CHEQUEOS PASARON")
print("=" * 74)
sys.exit(1 if fallos else 0)
