"""
pruebas_vistas.py — construye TODAS las vistas con CADA rol, sin ventana.

    python pruebas_vistas.py            # usa las cuentas del escenario de demo
    python pruebas_vistas.py --solo dueno

POR QUE EXISTE
==============
Dos bugs de esta clase llegaron hasta la demo, y ninguno de los chequeos que ya
tenia el proyecto podia verlos:

  1. `router.view_class()` devolvia None porque el mapa de rutas se registraba
     18 lineas mas abajo. Rompia el login de los CUATRO roles.
  2. El Dashboard hacia `delta_pct >= 0` con un delta que el backend manda en
     None cuando no hay mes anterior. Reventaba en la primera demo, siempre.

Los dos sobrevivieron a `compileall`, a las 9 suites de integracion y a que la
app arrancara sin un solo warning. Porque las suites prueban el BACKEND por
HTTP: nunca instancian una vista de Flet. Y `compileall` no ejecuta.

Lo que faltaba era esto: llamar a `build()` de cada vista con una sesion real de
cada rol, contra el backend de verdad. No verifica que la pantalla se vea bien
—para eso hay que abrirla— pero si que se pueda ABRIR, que es justo lo que
fallaba.

NO ES UNA SUITE DE INTEGRACION y no va en `backend/pruebas/`: no escribe nada,
no arma escenario y no necesita la base vacia. Al contrario, conviene correrla
sobre el escenario de demo, que es donde hay datos que hacen entrar a las ramas
interesantes.
"""
import sys
import traceback

RAIZ = "D:/OlimpOs/Proyeto-Python/Proyecto"
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import flet as ft

from app import api_client
from app.router import Router
from app.state import app_state

# Las cuentas del escenario de demo (pruebas/escenario_demo.py del backend).
CUENTAS = [
    ("dueno", "dueno 1234"),
    ("rita.lopez", "Demo2026!"),
    ("ana.gomez", "Demo2026!"),
    ("caro.diaz", "Demo2026!"),
]


class PageFalsa:
    """Lo mínimo que necesitan las vistas para construirse."""

    def __init__(self):
        self.controls = []
        self.overlay = []

    def update(self, *a, **k):
        pass

    def add(self, *a, **k):
        pass

    def open(self, *a, **k):
        pass

    def close(self, *a, **k):
        pass


def probar_rol(usuario: str, clave: str) -> list[str]:
    """Entra, y construye cada seccion que ese rol pueda ver."""
    fallos = []

    api_client.limpiar_token()
    resultado = app_state.login(usuario, clave)
    if not resultado.get("ok"):
        return [f"{usuario}: no pudo entrar — {resultado.get('mensaje')}"]
    if resultado.get("requiere_cambio"):
        return [f"{usuario}: la cuenta pide cambiar la contraseña; ajustá CUENTAS"]

    roles = app_state.get_user_roles()
    router = Router(PageFalsa())

    # El mismo camino que usa login.py para armar la pantalla inicial. Si esto
    # devuelve None, es el bug del mapa de rutas otra vez.
    inicial = app_state.primera_seccion()
    if router.view_class(inicial) is None:
        fallos.append(f"{usuario}: view_class({inicial!r}) es None "
                      f"— el mapa de rutas no se registró")

    print(f"\n  {usuario}  (roles: {', '.join(roles)})  aterriza en {inicial!r}")

    for ruta in app_state.secciones_visibles():
        clase = router.view_class(ruta)
        if clase is None:
            print(f"     FALLA  {ruta:<14} sin clase de vista en el mapa")
            fallos.append(f"{usuario} / {ruta}: sin clase de vista")
            continue

        app_state.current_route = ruta
        try:
            clase(page=PageFalsa(), router=router).build()
            print(f"     OK     {ruta}")
        except Exception as e:
            print(f"     FALLA  {ruta:<14} {type(e).__name__}: {e}")
            traceback.print_exc(limit=3)
            fallos.append(f"{usuario} / {ruta}: {type(e).__name__}: {e}")

    return fallos


def main() -> int:
    solo = None
    if "--solo" in sys.argv:
        solo = sys.argv[sys.argv.index("--solo") + 1]

    estado = api_client.estado_api()
    if not estado.get("ok"):
        print(f"No hay backend: {estado.get('error')}")
        print("Levantalo con: .venv/Scripts/python.exe -m uvicorn main:app "
              "--host 127.0.0.1 --port 8000   (desde backend/)")
        return 1

    print("=" * 74)
    print("CONSTRUCCION DE VISTAS POR ROL")
    print("=" * 74)

    todos = []
    for usuario, clave in CUENTAS:
        if solo and usuario != solo:
            continue
        todos += probar_rol(usuario, clave)
        app_state.logout()

    print("\n" + "=" * 74)
    if todos:
        print(f"FALLARON {len(todos)}:")
        for f in todos:
            print("  - " + f)
    else:
        print("TODAS LAS VISTAS SE CONSTRUYEN CON TODOS LOS ROLES")
    print("=" * 74)
    return 1 if todos else 0


if __name__ == "__main__":
    sys.exit(main())
