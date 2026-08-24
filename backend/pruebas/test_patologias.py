"""
Historial medico del socio.

Patologia y Socio_Patologia estaban en el esquema desde el principio y no
tenian modelo ni endpoint: eran dos de las tres tablas sin mapear.

EL CHEQUEO QUE MAS IMPORTA es el 6: el RECEPCIONISTA no puede ver esto. Es la
unica accion donde queda por debajo del Entrenador y del Nutricionista. El
mostrador maneja plata, turnos e ingresos; ninguna tarea suya requiere saber
quien tiene diabetes o una lesion de rodilla.

    python pruebas/test_patologias.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import json
import urllib.error
import urllib.request

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
print("HISTORIAL MEDICO")
print("=" * 74)

STAFF = entrar("dueno", "cambiar-esto-en-el-primer-ingreso", "Prueba2026!")
if not STAFF:
    print("no se pudo entrar"); sys.exit(1)

print("\n0. Un entrenador, un recepcionista y un socio, todos con cuenta")
cuentas = {}
for nombre, dni, rol in [("Tere", "80111000", "Entrenador"),
                         ("Rita", "80222000", "Recepcionista")]:
    s, r = pedir("POST", "/personal", {"nombre": nombre, "apellido": "T", "dni": dni,
        "rol": rol, "id_sede": 1, "crear_cuenta": True}, tok=STAFF)
    cuentas[nombre] = entrar(r["username"], r["password_temporal"], "Clave2026!")

s, r = pedir("POST", "/socios", {"nombre": "Nico", "apellido": "S", "dni": "80333000",
    "email": "nico.s@ejemplo.com", "id_sede": 1, "crear_cuenta": True}, tok=STAFF)
ID_SOCIO = r["id_socio"]
cuentas["Nico"] = entrar(r["username"], r["password_temporal"], "Clave2026!")
print(f"   {list(cuentas)}")
chequear(all(cuentas.values()), "los tres entran")

# ── Catalogo ─────────────────────────────────────────────────────────────────
print("\n1. El entrenador carga el catálogo")
for n, d in [("Asma", "Vía aérea"), ("Hernia de disco", "Lumbar"),
             ("Diabetes tipo 2", None)]:
    s, r = pedir("POST", "/patologias", {"nombre": n, "descripcion": d},
                 tok=cuentas["Tere"])
    print(f"   {s}  {r.get('nombre', r.get('detail'))}")
chequear(s == 201, "cargadas")

print("\n2. Duplicado con otra capitalización")
s, r = pedir("POST", "/patologias", {"nombre": "  asma  "}, tok=cuentas["Tere"])
print(f"   {s}  {r.get('detail')}")
chequear(s == 409, "«asma» y «Asma» son la misma cosa")

s, catalogo = pedir("GET", "/patologias", tok=cuentas["Tere"])
print(f"   catálogo: {[p['nombre'] for p in catalogo]}")
ID_ASMA = next(p["id_patologia"] for p in catalogo if p["nombre"] == "Asma")
ID_HERNIA = next(p["id_patologia"] for p in catalogo if "Hernia" in p["nombre"])

# ── Asignar ──────────────────────────────────────────────────────────────────
print("\n3. El entrenador le registra una hernia con observaciones")
s, r = pedir("POST", f"/socios/{ID_SOCIO}/patologias",
             {"id_patologia": ID_HERNIA, "fecha_diagnostico": "2025-03-10",
              "observaciones": "L4-L5. Evitar peso muerto y sentadilla con barra."},
             tok=cuentas["Tere"])
print(f"   {s}  {r.get('nombre')}: {r.get('observaciones')}")
chequear(s == 201, "registrada")
chequear(r.get("observaciones"), "con las observaciones, que es lo que le sirve")

print("\n4. La misma dos veces")
s, r = pedir("POST", f"/socios/{ID_SOCIO}/patologias",
             {"id_patologia": ID_HERNIA}, tok=cuentas["Tere"])
print(f"   {s}  {r.get('detail')}")
chequear(s == 409, "rechazada con un mensaje que dice qué hacer")

print("\n5. Editar las observaciones (una lesión que mejora)")
s, r = pedir("PUT", f"/socios/{ID_SOCIO}/patologias/{ID_HERNIA}",
             {"id_patologia": ID_HERNIA, "fecha_diagnostico": "2025-03-10",
              "observaciones": "Recuperada. Ya puede cargar peso progresivo."},
             tok=cuentas["Tere"])
print(f"   {s}  {r.get('observaciones')}")
chequear(s == 200 and "Recuperada" in str(r.get("observaciones")), "actualizada")

# ── LO QUE MAS IMPORTA ───────────────────────────────────────────────────────
print("\n6. EL RECEPCIONISTA NO PUEDE VER NADA DE ESTO")
for m, path, cuerpo in [
    ("GET", "/patologias", None),
    ("GET", f"/socios/{ID_SOCIO}/patologias", None),
    ("POST", f"/socios/{ID_SOCIO}/patologias", {"id_patologia": ID_ASMA}),
    ("PUT", f"/socios/{ID_SOCIO}/patologias/{ID_HERNIA}", {"id_patologia": ID_HERNIA}),
    ("DELETE", f"/socios/{ID_SOCIO}/patologias/{ID_HERNIA}", None),
]:
    s, _ = pedir(m, path, cuerpo, tok=cuentas["Rita"])
    print(f"   {s}  {m} {path}")
    chequear(s == 403, f"{m} rechazado")

print("\n7. Pero SI ve al socio en el resto del sistema")
s, socios = pedir("GET", "/socios", tok=cuentas["Rita"])
mio = next((x for x in socios if x["id_socio"] == ID_SOCIO), None)
print(f"   ve a {mio['nombre'] if mio else '?'} en la lista, y su contacto de emergencia")
chequear(mio is not None, "el recepcionista sigue trabajando normal")

# ── El socio y lo suyo ───────────────────────────────────────────────────────
print("\n8. El socio ve LO SUYO desde el portal")
s, mias = pedir("GET", "/portal/mis-patologias", tok=cuentas["Nico"])
print(f"   {s}  {[p['nombre'] for p in mias]}")
chequear(s == 200 and len(mias) == 1, "ve la que le cargó el entrenador")

print("\n9. Y puede LISTAR el catálogo para elegir de ahí")
# Este chequeo faltaba y por eso el agujero vivio hasta que se dibujo la
# pantalla. El paso 10 de aca abajo manda ID_ASMA, pero ese numero salio del
# GET /patologias que hizo TERE en el paso 2: la prueba se lo pasaba al socio
# por una variable de Python. En la app real no hay tal variable — el socio
# tiene que preguntarle el catalogo al backend, y GET /patologias le responde
# 403 porque exige VER_HISTORIAL_MEDICO, que el rol Socio tiene en false como
# todas las acciones. O sea: el endpoint para declarar la propia condicion
# estaba, pero no habia forma de averiguar que id mandarle.
s, cat_socio = pedir("GET", "/portal/catalogo-patologias", tok=cuentas["Nico"])
print(f"   {s}  {[p['nombre'] for p in cat_socio] if s == 200 else cat_socio}")
chequear(s == 200, "el socio ve el catálogo desde el portal")
chequear(s == 200 and len(cat_socio) == len(catalogo),
         "y es el mismo catálogo que ve el entrenador")
chequear(s == 200 and all("id_patologia" in p for p in cat_socio),
         "con los ids, que es lo que necesita para el POST de abajo")

# Y sigue SIN poder entrar por la puerta del personal: lo de arriba es un
# endpoint nuevo del portal, no un permiso aflojado.
s, _ = pedir("GET", "/patologias", tok=cuentas["Nico"])
print(f"   {s}  GET /patologias (la puerta del personal)")
chequear(s == 403, "el catálogo del personal le sigue estando vedado")

print("\n10. Y declara una propia")
s, r = pedir("POST", "/portal/mis-patologias",
             {"id_patologia": ID_ASMA, "observaciones": "Uso inhalador antes de entrenar"},
             tok=cuentas["Nico"])
print(f"   {s}  {r.get('nombre')}: {r.get('observaciones')}")
chequear(s == 201, "el socio carga la suya sin pasar por nadie")

print("\n11. Pero NO puede ver las de otro socio")
s, r = pedir("GET", f"/socios/{ID_SOCIO}/patologias", tok=cuentas["Nico"])
print(f"   {s}  (el endpoint del personal)")
chequear(s == 403, "rechazado: ese endpoint es para ver las de terceros")

print("\n12. Ni inventar una condición fuera del catálogo")
s, r = pedir("POST", "/portal/mis-patologias", {"id_patologia": 9999}, tok=cuentas["Nico"])
print(f"   {s}  {r.get('detail')}")
chequear(s == 404, "sólo del catálogo")

print("\n13. Se saca una")
s, _ = pedir("DELETE", f"/portal/mis-patologias/{ID_ASMA}", tok=cuentas["Nico"])
print(f"   {s}")
chequear(s == 204, "borrada")
s, mias = pedir("GET", "/portal/mis-patologias", tok=cuentas["Nico"])
chequear(len(mias) == 1, "queda sólo la otra")

print("\n14. El entrenador ve el resultado")
s, suyas = pedir("GET", f"/socios/{ID_SOCIO}/patologias", tok=cuentas["Tere"])
for p in suyas:
    print(f"   {p['nombre']:<18} {p['fecha_diagnostico'] or '—'}  {p['observaciones'] or ''}")
chequear(len(suyas) == 1, "coincide con lo que ve el socio")

print("\n" + "=" * 74)
if fallos:
    print(f"FALLARON {len(fallos)}:")
    for f in fallos:
        print("  - " + f)
else:
    print("TODOS LOS CHEQUEOS PASARON")
print("=" * 74)
sys.exit(1 if fallos else 0)
