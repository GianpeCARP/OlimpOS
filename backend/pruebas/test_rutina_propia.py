"""
La rutina PROPIA del socio: se la arma él, es suya y de nadie más.

Se corre con el backend levantado y la base VACIA. Crea su propio escenario.

    python -m uvicorn main:app          # en otra terminal
    python pruebas/test_rutina_propia.py

Lo que más importa (el pedido explícito del dueño del proyecto):
  - Una rutina propia (id_entrenador NULL) es INVISIBLE para el personal: no
    aparece en el catálogo, verla/asignarla por id da 404, y ni siquiera figura
    en el historial de asignaciones que ve el staff.
  - No se le puede asignar a NADIE: se autoasigna a su autor al crearla.
  - Un socio no ve la rutina propia de otro.
  - La del entrenador tiene precedencia: si el socio ya tiene una asignada por
    su profe, no puede pisarla con una propia.
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
print("RUTINA PROPIA DEL SOCIO")
print("=" * 74)

STAFF = entrar("dueno", "cambiar-esto-en-el-primer-ingreso", "Prueba2026!")
if not STAFF:
    print("no se pudo entrar como dueno"); sys.exit(1)

# ── Preparacion ───────────────────────────────────────────────────────────────
print("\n0. Preparo el escenario")
s, ej1 = pedir("POST", "/rutinas/ejercicios",
               {"nombre": "Sentadilla propia", "grupo_muscular": "Piernas"}, tok=STAFF)
s, ej2 = pedir("POST", "/rutinas/ejercicios",
               {"nombre": "Curl propio", "grupo_muscular": "Brazos"}, tok=STAFF)
EJ1, EJ2 = ej1["id_ejercicio"], ej2["id_ejercicio"]
chequear(bool(EJ1 and EJ2), "hay dos ejercicios en el catalogo")

# Un entrenador de verdad, para poder armar una rutina de STAFF mas adelante.
s, emp = pedir("POST", "/personal", {"nombre": "Ent", "apellido": "Renador",
      "dni": "39000001", "id_sede": 1, "rol": "Entrenador",
      "crear_cuenta": True}, tok=STAFF)
TOK_ENT = entrar(emp["username"], emp["password_temporal"], "Ent2026!")
chequear(bool(TOK_ENT), "el entrenador entra a la API")

socios = {}
for nombre, dni in [("Ana", "40200100"), ("Beto", "40200200")]:
    s, r = pedir("POST", "/socios", {"nombre": nombre, "apellido": "Test",
        "dni": dni, "email": f"{nombre.lower()}@test.com", "id_sede": 1,
        "crear_cuenta": True}, tok=STAFF)
    socios[nombre] = {"id": r["id_socio"], "user": r["username"],
                      "pass": r["password_temporal"]}
TOK = {n: entrar(v["user"], v["pass"], "Socio2026!") for n, v in socios.items()}
chequear(all(TOK.values()), "los dos socios entran a la API")

CUERPO_PROPIA = {
    "nombre": "Mi rutina de fuerza",
    "objetivo": "Ponerme fuerte",
    "ejercicios": [
        {"id_ejercicio": EJ1, "dia": 1, "orden": 1, "series": 4, "repeticiones": "8-10"},
        {"id_ejercicio": EJ2, "dia": 1, "orden": 2, "series": 3, "repeticiones": "12"},
    ],
}

# 1. Ana se arma su rutina propia ─────────────────────────────────────────────
print("\n1. Ana crea su rutina propia")
s, r = pedir("POST", "/portal/mi-rutina/propia", CUERPO_PROPIA, tok=TOK["Ana"])
chequear(s == 201, "201 al crearla")
chequear(r.get("entrenador") == "Rutina propia", "figura como 'Rutina propia'")
chequear(len(r.get("ejercicios", [])) == 2, "quedaron los 2 ejercicios")
ID_PROPIA = r.get("id_rutina")

print("\n2. Ana la ve en su portal")
s, r = pedir("GET", "/portal/mi-rutina", tok=TOK["Ana"])
chequear(s == 200 and r and r.get("id_rutina") == ID_PROPIA, "es su rutina activa")

# 3-6. INVISIBLE para el personal ─────────────────────────────────────────────
print("\n3. NO aparece en el catalogo de rutinas del staff")
s, cat = pedir("GET", "/rutinas", tok=STAFF)
ids_catalogo = [x["id_rutina"] for x in cat] if isinstance(cat, list) else []
chequear(ID_PROPIA not in ids_catalogo, "la rutina propia no esta en el catalogo")

print("\n4. Verla por id desde el staff -> 404 (como si no existiera)")
s, r = pedir("GET", f"/rutinas/{ID_PROPIA}", tok=STAFF)
chequear(s == 404, "GET /rutinas/{propia} da 404")

print("\n5. Asignarla a otro socio -> 404 (no se puede)")
s, r = pedir("POST", f"/rutinas/{ID_PROPIA}/asignar",
             {"id_socio": socios["Beto"]["id"]}, tok=STAFF)
chequear(s == 404, "no se puede asignar una rutina propia")

print("\n6. No figura en el historial de asignaciones que ve el staff")
s, hist = pedir("GET", f"/rutinas/asignaciones/socio/{socios['Ana']['id']}", tok=STAFF)
ids_hist = [a["id_rutina"] for a in hist] if isinstance(hist, list) else []
chequear(ID_PROPIA not in ids_hist, "la propia no esta en el historial del staff")

print("\n7. Beto no ve la rutina de Ana")
s, r = pedir("GET", "/portal/mi-rutina", tok=TOK["Beto"])
chequear(r is None, "Beto no tiene rutina (no hereda la de Ana)")

# 8. La del entrenador tiene precedencia ──────────────────────────────────────
print("\n8. Si el socio ya tiene rutina del entrenador, no puede crear una propia")
s, rut_staff = pedir("POST", "/rutinas", {"nombre": "Plan del profe",
      "ejercicios": [{"id_ejercicio": EJ1, "dia": 1, "orden": 1, "series": 5,
                      "repeticiones": "5"}]}, tok=TOK_ENT)
chequear(s == 201, "el entrenador crea una rutina de staff")
s, _ = pedir("POST", f"/rutinas/{rut_staff['id_rutina']}/asignar",
             {"id_socio": socios["Beto"]["id"]}, tok=STAFF)
chequear(s == 201, "el staff se la asigna a Beto")
s, r = pedir("POST", "/portal/mi-rutina/propia", CUERPO_PROPIA, tok=TOK["Beto"])
chequear(s == 409, "Beto NO puede pisar la del profe con una propia (409)")

# 9. Rehacer la propia la reemplaza ───────────────────────────────────────────
print("\n9. Ana rehace su rutina: la nueva reemplaza a la vieja")
s, r = pedir("POST", "/portal/mi-rutina/propia",
             {"nombre": "Mi rutina v2",
              "ejercicios": [{"id_ejercicio": EJ2, "dia": 1, "orden": 1,
                              "series": 3, "repeticiones": "15"}]}, tok=TOK["Ana"])
chequear(s == 201 and r.get("id_rutina") != ID_PROPIA, "creo una rutina propia NUEVA")
s, hist = pedir("GET", "/portal/mi-rutina/historial", tok=TOK["Ana"])
vieja = next((a for a in hist if a["id_rutina"] == ID_PROPIA), None)
chequear(vieja is not None and vieja["estado"] == "FINALIZADA", "la vieja quedo FINALIZADA")

# 10. Eliminarla ──────────────────────────────────────────────────────────────
print("\n10. Ana elimina su rutina propia")
s, r = pedir("DELETE", "/portal/mi-rutina/propia", tok=TOK["Ana"])
chequear(s == 200, "200 al eliminar")
s, r = pedir("GET", "/portal/mi-rutina", tok=TOK["Ana"])
chequear(r is None, "ya no tiene rutina activa")

# 11. Sin ejercicios no se puede ──────────────────────────────────────────────
print("\n11. Una rutina propia sin ejercicios -> 422")
s, r = pedir("POST", "/portal/mi-rutina/propia",
             {"nombre": "Vacia", "ejercicios": []}, tok=TOK["Ana"])
chequear(s == 422, "422 sin ejercicios")

print("\n" + "=" * 74)
if fallos:
    print(f"FALLARON {len(fallos)} CHEQUEOS:")
    for f in fallos:
        print(f"   - {f}")
    sys.exit(1)
print("TODOS LOS CHEQUEOS PASARON")
