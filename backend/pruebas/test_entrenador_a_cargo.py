"""
Entrenador a cargo de un socio (Asignacion_Entrenador).

La migracion 003 saco Socio.id_entrenador_a_cargo —una columna de valor unico
para un hecho multiple y cambiante— y creo esta tabla. Hasta ahora ningun
router la usaba: no habia forma de asignarle un entrenador a un socio desde
ninguna de las dos apps.

Lo que mas importa acá es que se permitan VARIOS a la vez. Es la diferencia
deliberada con Asignacion_Rutina y Asignacion_Dieta, que admiten una sola
activa: un socio con uno de musculacion y otro de funcional es normal.

    python pruebas/test_entrenador_a_cargo.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import json
import urllib.error
import urllib.request
from datetime import date

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
print("ENTRENADOR A CARGO")
print("=" * 74)

STAFF = entrar("dueno", "cambiar-esto-en-el-primer-ingreso", "Prueba2026!")
if not STAFF:
    print("no se pudo entrar"); sys.exit(1)

print("\n0. Dos entrenadores y un socio")
entrenadores = {}
for nombre, esp in [("Ana", "Musculación"), ("Beto", "Funcional")]:
    s, r = pedir("POST", "/personal", {
        "nombre": nombre, "apellido": "Entrena", "dni": f"6{nombre}00000"[:8],
        "rol": "Entrenador", "especialidad": esp, "id_sede": 1,
        "crear_cuenta": False}, tok=STAFF)
    entrenadores[nombre] = r.get("id_empleado")
s, lista = pedir("GET", "/personal/entrenadores", tok=STAFF)
print(f"   entrenadores: {[e['nombre'] for e in lista]}")
chequear(len(lista) >= 2, "hay dos entrenadores")
ID_ANA = lista[0]["id"]
ID_BETO = lista[1]["id"]

s, r = pedir("POST", "/socios", {"nombre": "Juan", "apellido": "Socio",
    "dni": "61000111", "email": "juan@ejemplo.com", "id_sede": 1,
    "crear_cuenta": False}, tok=STAFF)
ID_SOCIO = r["id_socio"]
print(f"   socio: Juan (#{ID_SOCIO})")

# ── El caso que la tabla existe para permitir ────────────────────────────────
print("\n1. Se le asigna el de musculación")
s, a1 = pedir("POST", f"/socios/{ID_SOCIO}/entrenadores",
              {"id_entrenador": ID_ANA}, tok=STAFF)
print(f"   {s}  {a1.get('entrenador')} ({a1.get('especialidad')}) desde {a1.get('fecha_inicio')}")
chequear(s == 201, "asignado")

print("\n2. Y TAMBIEN el de funcional, a la vez")
s, a2 = pedir("POST", f"/socios/{ID_SOCIO}/entrenadores",
              {"id_entrenador": ID_BETO}, tok=STAFF)
print(f"   {s}  {a2.get('entrenador')} ({a2.get('especialidad')})")
chequear(s == 201, "DOS entrenadores activos a la vez (esto no lo permitia la columna vieja)")

s, activos = pedir("GET", f"/socios/{ID_SOCIO}/entrenadores?solo_activos=true", tok=STAFF)
print(f"   activos: {[x['entrenador'] for x in activos]}")
chequear(len(activos) == 2, "los dos figuran activos")

print("\n3. Asignar DOS VECES al mismo -> rechazado")
s, r = pedir("POST", f"/socios/{ID_SOCIO}/entrenadores",
             {"id_entrenador": ID_ANA}, tok=STAFF)
print(f"   {s}  {r.get('detail')}")
chequear(s == 409, "no es 'dos entrenadores', es la misma relacion duplicada")

# ── El historial, que es el motivo de la tabla ───────────────────────────────
print("\n4. Se termina la relación con uno")
s, r = pedir("POST", f"/socios/entrenadores/asignaciones/{a1['id_asignacion']}/finalizar",
             tok=STAFF)
print(f"   {s}  {r.get('entrenador')}: {r.get('estado')}, hasta {r.get('fecha_fin')}")
chequear(s == 200 and r.get("estado") == "FINALIZADA", "finalizada")
chequear(r.get("fecha_fin") == date.today().isoformat(), "con su fecha de fin")

print("\n5. LA FILA NO SE BORRO: el historial queda")
s, todos = pedir("GET", f"/socios/{ID_SOCIO}/entrenadores", tok=STAFF)
for x in todos:
    hasta = x["fecha_fin"] or "sigue"
    print(f"   {x['entrenador']:<14} {x['fecha_inicio']} -> {hasta:<12} {x['estado']}")
chequear(len(todos) == 2, "siguen las dos asignaciones")
s, activos = pedir("GET", f"/socios/{ID_SOCIO}/entrenadores?solo_activos=true", tok=STAFF)
chequear(len(activos) == 1, "pero solo una activa")

print("\n6. Finalizar dos veces la misma")
s, r = pedir("POST", f"/socios/entrenadores/asignaciones/{a1['id_asignacion']}/finalizar",
             tok=STAFF)
print(f"   {s}  {r.get('detail')}")
chequear(s == 400, "rechazado")

# ── La vista inversa ─────────────────────────────────────────────────────────
print("\n7. A quiénes entrena Beto (la pregunta que se hace un entrenador)")
s, sus = pedir("GET", f"/socios/entrenadores/{ID_BETO}/socios", tok=STAFF)
print(f"   {[x['nombre'] + ' ' + x['apellido'] for x in sus]}")
chequear(len(sus) == 1, "ve a Juan")

s, sus_ana = pedir("GET", f"/socios/entrenadores/{ID_ANA}/socios", tok=STAFF)
print(f"   Ana (ya no lo entrena): {len(sus_ana)} socio(s)")
chequear(len(sus_ana) == 0, "Ana ya no lo tiene: la finalizada no cuenta")

# ── Validaciones ─────────────────────────────────────────────────────────────
print("\n8. Un socio dado de baja no recibe entrenador")
pedir("POST", f"/socios/{ID_SOCIO}/baja", {"tipo": "VOLUNTARIA"}, tok=STAFF)
s, r = pedir("POST", f"/socios/{ID_SOCIO}/entrenadores",
             {"id_entrenador": ID_ANA}, tok=STAFF)
print(f"   {s}  {r.get('detail')}")
chequear(s == 400, "rechazado con un mensaje que dice qué hacer")
pedir("POST", f"/socios/{ID_SOCIO}/reactivar", tok=STAFF)

print("\n9. Un entrenador que ya no trabaja tampoco")
emp = next(e for e in pedir("GET", "/personal", tok=STAFF)[1]
           if e.get("rol") == "Entrenador")
pedir("POST", f"/personal/{emp['id_empleado']}/baja", {"motivo": "renuncio"}, tok=STAFF)
s, lista2 = pedir("GET", "/personal/entrenadores", tok=STAFF)
print(f"   entrenadores ofrecidos ahora: {[e['nombre'] for e in lista2]}")
chequear(len(lista2) < len(lista), "el selector ya no lo ofrece")

id_baja = ID_ANA if emp["id_empleado"] == entrenadores.get("Ana") else ID_BETO
s, r = pedir("POST", f"/socios/{ID_SOCIO}/entrenadores",
             {"id_entrenador": id_baja}, tok=STAFF)
print(f"   asignarlo igual: {s}  {r.get('detail')}")
chequear(s == 400, "y el backend tampoco lo acepta si se manda a mano")

print("\n10. Socio o entrenador inexistente")
for path, cuerpo in [(f"/socios/9999/entrenadores", {"id_entrenador": ID_BETO}),
                     (f"/socios/{ID_SOCIO}/entrenadores", {"id_entrenador": 9999})]:
    s, r = pedir("POST", path, cuerpo, tok=STAFF)
    print(f"   {s}  {r.get('detail')}")
    chequear(s == 404, "404")

print("\n" + "=" * 74)
if fallos:
    print(f"FALLARON {len(fallos)}:")
    for f in fallos:
        print("  - " + f)
else:
    print("TODOS LOS CHEQUEOS PASARON")
print("=" * 74)
sys.exit(1 if fallos else 0)
