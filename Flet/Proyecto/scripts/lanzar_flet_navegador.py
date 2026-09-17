"""
Lanza la app Flet en el NAVEGADOR, sin tocar main.py.

main.py llama ft.run(main, assets_dir="assets"), que abre una ventana nativa
imposible de screenshotear. Este envoltorio reusa la misma funcion main() y
solo cambia como se muestra: mismo codigo, otra vista.

DOS TRAMPAS QUE ESTE ARCHIVO YA PAGO
====================================

1. NO puede llamarse flet_web.py. Flet, para servir por HTTP, hace
   `from flet_web.fastapi... import ...`, y como el directorio del script va
   primero en sys.path, Python importaba ESTE archivo en vez del paquete de
   Flet y reventaba con "asyncio.run() cannot be called from a running event
   loop".

2. assets_dir tiene que ser ABSOLUTO. Flet resuelve la ruta relativa contra el
   directorio del script que llama a ft.run() —no contra el cwd, aunque se
   haga os.chdir()—. Con "assets" a secas buscaba en la carpeta de este
   envoltorio, no encontraba nada, y servia el index.html para CUALQUIER ruta:
   el logo del sidebar devolvia 200 con 3775 bytes de HTML en vez del PNG, y
   en pantalla quedaba el recuadro verde vacio. Cuesta verlo porque no da 404.
"""
import os
import sys

# La raiz se deriva de DONDE ESTA este archivo (scripts/ cuelga de ella), no
# de una ruta clavada: el repo vive en D: en una maquina y en E: en la otra,
# y con la ruta fija el lanzador solo arrancaba en una de las dos.
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)

import flet as ft
from main import main

ASSETS = os.path.join(RAIZ, "assets")
if not os.path.isdir(ASSETS):
    raise SystemExit(f"No existe {ASSETS}; el logo del sidebar no va a cargar.")

ft.run(main, view=ft.AppView.WEB_BROWSER, port=8551, assets_dir=ASSETS)
