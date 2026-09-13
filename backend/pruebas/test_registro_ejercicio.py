"""
El registro de una serie que el socio hizo, contada por la camara del circuito.

Se corre con el backend levantado y la base VACIA (6 filas: el titular, la sede
y los tipos de membresia). Crea su propio escenario y deja datos: es un test de
integracion, no unitario.

    python -m uvicorn main:app          # en otra terminal
    python pruebas/test_registro_ejercicio.py

Lo que mas importa:
  - El grano es (socio, ejercicio, fecha): dos series del mismo ejercicio en el
    dia NO crean dos filas, ACUMULAN en una (mismo id, series_hechas sube, las
    reps se agregan, el peso se queda con el MAXIMO).
  - El id_socio sale del token, no del cuerpo: un socio no puede cargarle una
    serie a otro (misma propiedad que /mi-progreso/mediciones).
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
print("REGISTRO DE EJERCICIO (contador con camara)")
print("=" * 74)

STAFF = entrar("dueno", "cambiar-esto-en-el-primer-ingreso", "Prueba2026!")
if not STAFF:
    print("no se pudo entrar como dueno"); sys.exit(1)

# ── Preparacion ───────────────────────────────────────────────────────────────
print("\n0. Preparo el escenario")
s, ej = pedir("POST", "/rutinas/ejercicios", {"nombre": "Sentadilla test",
      "grupo_muscular": "Piernas"}, tok=STAFF)
ID_EJ = ej.get("id_ejercicio")
chequear(s == 201 and ID_EJ, "se crea un ejercicio en el catalogo")

socios = {}
for nombre, dni in [("Ana", "40100100"), ("Beto", "40100200")]:
    s, r = pedir("POST", "/socios", {"nombre": nombre, "apellido": "Test",
        "dni": dni, "email": f"{nombre.lower()}@test.com", "id_sede": 1,
        "crear_cuenta": True}, tok=STAFF)
    socios[nombre] = {"id": r["id_socio"], "user": r["username"],
                      "pass": r["password_temporal"]}
TOK = {n: entrar(v["user"], v["pass"], "Socio2026!") for n, v in socios.items()}
chequear(all(TOK.values()), "los dos socios entran a la API")

RUTA = "/portal/mi-rutina/registro-ejercicio"

# 1. Primera serie del dia: crea la fila ──────────────────────────────────────
print("\n1. Primera serie: crea la fila")
s, r = pedir("POST", RUTA, {"id_ejercicio": ID_EJ, "repeticiones": 10,
             "peso": 40}, tok=TOK["Ana"])
chequear(s == 201, "201 al cargar la primera serie")
chequear(r.get("series_hechas") == 1, "series_hechas = 1")
chequear(r.get("repeticiones_hechas") == "10", "repeticiones_hechas = '10'")
chequear(float(r.get("peso_hecho", 0)) == 40, "peso_hecho = 40")
ID_REG = r.get("id_registro_ejercicio")

# 2. Segunda serie MISMO ejercicio, MISMO dia: acumula en la MISMA fila ────────
print("\n2. Segunda serie del mismo ejercicio: acumula (no crea otra fila)")
s, r = pedir("POST", RUTA, {"id_ejercicio": ID_EJ, "repeticiones": 8,
             "peso": 45}, tok=TOK["Ana"])
chequear(s == 201, "201 al cargar la segunda serie")
chequear(r.get("id_registro_ejercicio") == ID_REG, "es la MISMA fila (mismo id)")
chequear(r.get("series_hechas") == 2, "series_hechas = 2")
chequear(r.get("repeticiones_hechas") == "10,8", "repeticiones_hechas = '10,8'")
chequear(float(r.get("peso_hecho", 0)) == 45, "peso_hecho = MAX = 45")

# 3. Tercera serie con MENOS peso: el maximo del dia no baja ───────────────────
print("\n3. Serie con menos peso: el record del dia no baja")
s, r = pedir("POST", RUTA, {"id_ejercicio": ID_EJ, "repeticiones": 6,
             "peso": 30}, tok=TOK["Ana"])
chequear(r.get("series_hechas") == 3, "series_hechas = 3")
chequear(float(r.get("peso_hecho", 0)) == 45, "peso_hecho sigue en 45 (no baja)")

# 4. El peso es opcional: sin peso, queda 0 y cuenta igual ─────────────────────
print("\n4. Otro socio sin peso: queda 0 y cuenta igual")
s, r = pedir("POST", RUTA, {"id_ejercicio": ID_EJ, "repeticiones": 12},
             tok=TOK["Beto"])
chequear(s == 201, "201 sin mandar peso")
chequear(float(r.get("peso_hecho", -1)) == 0, "peso_hecho = 0 por defecto")
chequear(r.get("id_registro_ejercicio") != ID_REG, "es fila propia de Beto, no la de Ana")

# 5. Ejercicio inexistente: 404 claro, no error de FK en el commit ─────────────
print("\n5. id_ejercicio inventado -> 404")
s, r = pedir("POST", RUTA, {"id_ejercicio": 999999, "repeticiones": 5},
             tok=TOK["Ana"])
chequear(s == 404, "404 con un ejercicio que no existe")

# 6. Reps invalidas: 0 no es una serie ────────────────────────────────────────
print("\n6. repeticiones = 0 -> 422")
s, r = pedir("POST", RUTA, {"id_ejercicio": ID_EJ, "repeticiones": 0},
             tok=TOK["Ana"])
chequear(s == 422, "422 con repeticiones = 0")

# 7. Sin token: 401/403, nadie carga anonimo ──────────────────────────────────
print("\n7. Sin token -> no entra")
s, r = pedir("POST", RUTA, {"id_ejercicio": ID_EJ, "repeticiones": 5})
chequear(s in (401, 403), "sin token no se puede cargar")

print("\n" + "=" * 74)
if fallos:
    print(f"FALLARON {len(fallos)} CHEQUEOS:")
    for f in fallos:
        print(f"   - {f}")
    sys.exit(1)
print("TODOS LOS CHEQUEOS PASARON")
