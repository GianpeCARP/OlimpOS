"""
La dieta PROPIA del socio y el registro de comida (lo que comió).

Se corre con el backend levantado y la base VACIA. Crea su propio escenario.

    python -m uvicorn main:app          # en otra terminal
    python pruebas/test_dieta_propia.py

Espeja test_rutina_propia (dieta propia invisible para el staff, no asignable a
otro, precedencia del nutricionista) y suma el registro de comida por texto
libre con macros manuales.
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
print("DIETA PROPIA + REGISTRO DE COMIDA")
print("=" * 74)

STAFF = entrar("dueno", "cambiar-esto-en-el-primer-ingreso", "Prueba2026!")
if not STAFF:
    print("no se pudo entrar como dueno"); sys.exit(1)

print("\n0. Preparo el escenario")
s, emp = pedir("POST", "/personal", {"nombre": "Nutri", "apellido": "Test",
      "dni": "39500001", "id_sede": 1, "rol": "Nutricionista",
      "crear_cuenta": True}, tok=STAFF)
TOK_NUTRI = entrar(emp["username"], emp["password_temporal"], "Nutri2026!")
chequear(bool(TOK_NUTRI), "el nutricionista entra a la API")

socios = {}
for nombre, dni in [("Ana", "40300100"), ("Beto", "40300200")]:
    s, r = pedir("POST", "/socios", {"nombre": nombre, "apellido": "Test",
        "dni": dni, "email": f"{nombre.lower()}@test.com", "id_sede": 1,
        "crear_cuenta": True}, tok=STAFF)
    socios[nombre] = {"id": r["id_socio"], "user": r["username"], "pass": r["password_temporal"]}
TOK = {n: entrar(v["user"], v["pass"], "Socio2026!") for n, v in socios.items()}
chequear(all(TOK.values()), "los dos socios entran a la API")

CUERPO_PROPIA = {
    "nombre": "Mi dieta de volumen",
    "objetivo": "Subir masa",
    "calorias_diarias": 2800,
    "comidas": [
        {"momento": "Desayuno", "descripcion": "Avena con banana y huevos", "dia": 1},
        {"momento": "Almuerzo", "descripcion": "Pollo con arroz y ensalada", "dia": 1},
    ],
}

# 1. Ana se arma su dieta propia ──────────────────────────────────────────────
print("\n1. Ana crea su dieta propia (texto libre, sin catálogo)")
s, r = pedir("POST", "/portal/mi-dieta/propia", CUERPO_PROPIA, tok=TOK["Ana"])
chequear(s == 201, "201 al crearla")
chequear(r.get("nutricionista") == "Dieta propia", "figura como 'Dieta propia'")
chequear(r.get("es_propia") is True, "es_propia = true")
comidas = r.get("dias", [{}])[0].get("comidas", []) if r.get("dias") else []
chequear(any(c.get("descripcion") == "Avena con banana y huevos" for c in comidas),
         "la comida de texto libre aparece por su descripción")
ID_PROPIA = r.get("id_dieta")

print("\n2. Ana la ve en su portal")
s, r = pedir("GET", "/portal/mi-dieta", tok=TOK["Ana"])
chequear(s == 200 and r and r.get("id_dieta") == ID_PROPIA, "es su dieta activa")

# 3-6. INVISIBLE para el personal ─────────────────────────────────────────────
print("\n3. NO aparece en el catálogo de dietas del staff")
s, cat = pedir("GET", "/nutricion", tok=STAFF)
ids = [d["id_dieta"] for d in cat] if isinstance(cat, list) else []
chequear(ID_PROPIA not in ids, "la dieta propia no está en el catálogo")

print("\n4. Verla por id desde el staff -> 404")
s, r = pedir("GET", f"/nutricion/{ID_PROPIA}", tok=STAFF)
chequear(s == 404, "GET /nutricion/{propia} da 404")

print("\n5. Asignarla a otro socio -> 404")
s, r = pedir("POST", f"/nutricion/{ID_PROPIA}/asignar", {"id_socio": socios["Beto"]["id"]}, tok=STAFF)
chequear(s == 404, "no se puede asignar una dieta propia")

print("\n6. No figura en el historial de asignaciones del staff")
s, hist = pedir("GET", f"/nutricion/asignaciones/socio/{socios['Ana']['id']}", tok=STAFF)
ids_h = [a["id_dieta"] for a in hist] if isinstance(hist, list) else []
chequear(ID_PROPIA not in ids_h, "la propia no está en el historial del staff")

print("\n7. Beto no ve la dieta de Ana")
s, r = pedir("GET", "/portal/mi-dieta", tok=TOK["Beto"])
chequear(r is None, "Beto no hereda la dieta de Ana")

# 8. La del nutricionista tiene precedencia ───────────────────────────────────
print("\n8. Si el socio ya tiene dieta del nutricionista, no puede crear una propia")
s, dstaff = pedir("POST", "/nutricion", {"nombre": "Plan del profe", "comidas": []}, tok=TOK_NUTRI)
chequear(s == 201, "el nutricionista crea una dieta de staff")
s, _ = pedir("POST", f"/nutricion/{dstaff['id_dieta']}/asignar", {"id_socio": socios["Beto"]["id"]}, tok=STAFF)
chequear(s == 201, "el staff se la asigna a Beto")
s, r = pedir("POST", "/portal/mi-dieta/propia", CUERPO_PROPIA, tok=TOK["Beto"])
chequear(s == 409, "Beto NO puede pisar la del nutri con una propia (409)")

# 9. Rehacer reemplaza ────────────────────────────────────────────────────────
print("\n9. Ana rehace su dieta: reemplaza a la vieja")
s, r = pedir("POST", "/portal/mi-dieta/propia",
             {"nombre": "Mi dieta v2", "comidas": [{"momento": "Cena", "descripcion": "Sopa"}]},
             tok=TOK["Ana"])
chequear(s == 201 and r.get("id_dieta") != ID_PROPIA, "creó una dieta propia NUEVA")

print("\n10. Ana elimina su dieta propia")
s, r = pedir("DELETE", "/portal/mi-dieta/propia", tok=TOK["Ana"])
chequear(s == 200, "200 al eliminar")
s, r = pedir("GET", "/portal/mi-dieta", tok=TOK["Ana"])
chequear(r is None, "ya no tiene dieta activa")

print("\n11. Dieta propia sin comidas -> 422")
s, r = pedir("POST", "/portal/mi-dieta/propia", {"nombre": "Vacía", "comidas": []}, tok=TOK["Ana"])
chequear(s == 422, "422 sin comidas")

# ── REGISTRO DE COMIDA ────────────────────────────────────────────────────────
print("\n12. Ana registra lo que comió (texto + macros a mano)")
s, r = pedir("POST", "/portal/mi-dieta/comidas",
             {"comida_ingerida": "Milanesa con puré", "momento": "Almuerzo",
              "calorias_estimadas": 700, "proteinas_g": 40, "carbohidratos_g": 60, "grasas_g": 25},
             tok=TOK["Ana"])
chequear(s == 201, "201 al registrar la comida")
chequear(r.get("comida_ingerida") == "Milanesa con puré", "guardó el texto")
chequear(float(r.get("proteinas_g") or 0) == 40, "guardó las proteínas")

print("\n13. Registra otra sin macros (opcionales)")
s, r = pedir("POST", "/portal/mi-dieta/comidas", {"comida_ingerida": "Una manzana"}, tok=TOK["Ana"])
chequear(s == 201 and r.get("proteinas_g") is None, "201 sin macros (quedan null)")

print("\n14. Las ve en su listado")
s, lista = pedir("GET", "/portal/mi-dieta/comidas", tok=TOK["Ana"])
chequear(isinstance(lista, list) and len(lista) == 2, "aparecen las 2 comidas registradas")

print("\n15. Comida sin texto -> 422")
s, r = pedir("POST", "/portal/mi-dieta/comidas", {"comida_ingerida": ""}, tok=TOK["Ana"])
chequear(s == 422, "422 sin texto")

print("\n16. Beto no ve las comidas de Ana")
s, lista = pedir("GET", "/portal/mi-dieta/comidas", tok=TOK["Beto"])
chequear(isinstance(lista, list) and len(lista) == 0, "el registro de comida es por socio")

print("\n" + "=" * 74)
if fallos:
    print(f"FALLARON {len(fallos)} CHEQUEOS:")
    for f in fallos:
        print(f"   - {f}")
    sys.exit(1)
print("TODOS LOS CHEQUEOS PASARON")
