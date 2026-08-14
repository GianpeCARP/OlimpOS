"""
La aritmetica de la extension del congelamiento.

Existe aparte de test_mi_membresia.py porque necesita TOCAR LA BASE: para
probar que reanudar suma los dias REALES y no los pedidos hace falta que haya
pasado tiempo, y esperar dos semanas no es una opcion. Se retrasa la
fecha_inicio con SQL y se reanuda.

Se corre desde backend/ con el backend levantado:

    python pruebas/test_extension_congelamiento.py

Es la unica regla del congelamiento que no se puede verificar por HTTP sola, y
es la que mas plata mueve: si sumara los dias PEDIDOS, alguien pidiendo 90 dias
y volviendo a los dos se llevaria tres meses gratis.
"""
import json
import urllib.error
import urllib.request
from datetime import date, timedelta

from database import SessionLocal
from models import Congelamiento


def pedir(m, p, b=None, tok=None):
    h = {"Content-Type": "application/json", "X-Client-Type": "escritorio"}
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    d = json.dumps(b).encode() if b is not None else None
    r = urllib.request.Request("http://127.0.0.1:8000" + p, data=d, headers=h, method=m)
    try:
        with urllib.request.urlopen(r) as x:
            return x.status, json.loads(x.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


STAFF = pedir("POST", "/login", {"username": "dueno", "password": "Prueba2026!"})[1]["token"]

s, r = pedir("POST", "/socios", {"nombre": "Dani", "apellido": "Test",
    "dni": "42777888", "email": "dani@ejemplo.com", "id_sede": 1,
    "crear_cuenta": True}, tok=STAFF)
ids, user, clave = r["id_socio"], r["username"], r["password_temporal"]

tipos = pedir("GET", "/cobros/tipos-membresia", tok=STAFF)[1]
plan = max(tipos, key=lambda x: x["duracion_dias"])
pedir("POST", "/cobros", {"id_socio": ids,
      "id_tipo_membresia": plan["id_tipo_membresia"], "metodo": "EFECTIVO"}, tok=STAFF)

pedir("POST", "/cambiar-password", {"username": user,
      "password_actual": clave, "password_nueva": "Socio2026!"})
TOK = pedir("POST", "/login", {"username": user, "password": "Socio2026!"})[1]["token"]

s, c = pedir("GET", "/portal/mi-cuota", tok=TOK)
antes = date.fromisoformat(c["fecha_vencimiento"])
print(f"  vencimiento antes:   {antes}")

# Pide 40 dias y se le retrasa el inicio 12 dias, para simular que ya paso ese
# tiempo. Es la unica forma de probar la aritmetica sin esperar dos semanas.
pedir("POST", "/portal/mi-membresia/congelar",
      {"fecha_fin": (date.today() + timedelta(days=40)).isoformat(),
       "motivo": "viaje"}, tok=TOK)

db = SessionLocal()
cong = (db.query(Congelamiento)
        .filter(Congelamiento.id_socio == ids, Congelamiento.estado == "ACTIVO")
        .first())
cong.fecha_inicio = date.today() - timedelta(days=12)
db.commit()
db.close()
print("  pidio 40 dias, lleva 12 congelado")

s, r = pedir("POST", "/portal/mi-membresia/reanudar", {}, tok=TOK)
mensaje = r.get("mensaje")
print(f"  {mensaje}")

s, c = pedir("GET", "/portal/mi-cuota", tok=TOK)
despues = date.fromisoformat(c["fecha_vencimiento"])
print(f"  vencimiento despues: {despues}")
print()

sumados = (despues - antes).days
print(f"  dias sumados al vencimiento: {sumados}   (esperado 12, NO 40)")
print(f"  dias_aplicados que reporta:  {r.get('dias_aplicados')}")

ok = sumados == 12 and r.get("dias_aplicados") == 12
print()
print("  OK  se extendio por los dias REALES, no por los pedidos" if ok
      else f"  MAL  sumo {sumados} en vez de 12")
