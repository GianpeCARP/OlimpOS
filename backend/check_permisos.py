"""
check_permisos.py
-----------------
Compara las TRES copias de la matriz de permisos y falla si difieren:

    backend  ->  backend/permisos.py           (este directorio)
    PWA      ->  Proyecto/src/frontend/src/config.ts
    Flet     ->  Proyeto-Python/Proyecto/app/permisos.py

POR QUÉ EXISTE:
permisos.py documenta que es un espejo de config.ts y que desincronizarse es
silencioso. Un comentario que pide "acordate de tocar el otro" es exactamente
el tipo de regla que nadie cumple a los tres meses. Esto la vuelve verificable
en un segundo.

Los dos modos de falla que detecta son asimétricos y los dos son malos:
  - El backend es MÁS restrictivo -> el botón aparece y la API responde 403.
  - El backend es MÁS permisivo   -> la API deja pasar algo que el frontend
                                     creía prohibido. Este es el grave.

La copia de Flet tiene una diferencia LEGÍTIMA que este script contempla: no
declara las siete secciones del portal del socio (mi-perfil, mi-rutina, ...)
porque esas pantallas son de la PWA y la app de escritorio no las tiene. Se
comparan sólo las secciones que Flet sí declara; lo que se exige es que donde
las tres hablen de lo mismo, digan lo mismo.

Uso:
    cd backend
    python check_permisos.py        # exit 0 si coinciden, 1 si no

No es un parser de TypeScript: aprovecha que el bloque PERMISOS de config.ts
tiene un formato muy regular. Si alguien lo reescribe con otra forma, este
script se va a quejar de que no encuentra algo — que también es una señal
útil, no un falso positivo silencioso.
"""

import pathlib
import re
import sys

from permisos import PERMISOS as PY_PERMISOS

_RANGO = {"ninguno": 0, "lectura": 1, "total": 2}

CONFIG_TS = pathlib.Path("../Proyecto/src/frontend/src/config.ts")
FLET_DIR = pathlib.Path("../Proyeto-Python/Proyecto")

# Secciones que existen SOLO en la app de escritorio, mapeadas a la seccion
# del backend que en realidad protege sus endpoints.
#
# "recepcion" es el panel del mostrador: una VISTA sobre datos de asistencia,
# no un area nueva de permisos. Sus endpoints (/recepcion/*) estan protegidos
# con Seccion.ASISTENCIA. Por eso no figura en el backend ni en la PWA, y por
# eso lo que se verifica no es que exista alla, sino que su nivel en Flet
# nunca supere al de la seccion que realmente la protege: si lo superara, un
# rol veria el panel en el menu y recibiria 403 al abrirlo.
SOLO_FLET = {"recepcion": "asistencia"}


def matriz_de_flet() -> dict[str, dict] | None:
    """
    Importa app/permisos.py del proyecto Flet.

    Se importa de verdad en vez de parsearlo —como sí hay que hacer con
    config.ts— porque es Python: si el archivo tiene un error de sintaxis o
    una constante mal escrita, el import lo dice con precisión y este script
    no tiene que adivinar nada.
    """
    if not (FLET_DIR / "app" / "permisos.py").exists():
        return None
    sys.path.insert(0, str(FLET_DIR.resolve()))
    try:
        from app.permisos import PERMISOS as FLET_PERMISOS
        return FLET_PERMISOS
    finally:
        sys.path.pop(0)


def rutas_de_config_py() -> dict[str, str]:
    """
    Los valores de `Routes` en el config.py de Flet.

    app/permisos.py repite esos strings en vez de importarlos (config.py hace
    `import flet` y esto correría sin Flet instalado). Se leen textualmente
    para confirmar que la copia sigue coincidiendo: si alguien renombra una
    ruta y no toca la matriz, los permisos quedarían apuntando a secciones que
    ya no existen y TODO caería en "sin acceso", en silencio.
    """
    texto = (FLET_DIR / "app" / "config.py").read_text(encoding="utf-8")
    m = re.search(r"class Routes:(.*?)(?:\n\n|\nclass )", texto, re.DOTALL)
    if not m:
        return {}
    return dict(re.findall(r"(\w+)\s*=\s*\"([^\"]*)\"", m.group(1)))


# =============================================================================
# PARSEO DE config.ts
# =============================================================================

def _sin_comentarios(texto: str) -> str:
    """Saca los // ... para que no ensucien las expresiones regulares."""
    return re.sub(r"//[^\n]*", "", texto)


def _bloque(texto: str, desde: int) -> str:
    """
    Devuelve el contenido entre la primera '{' a partir de `desde` y su llave
    de cierre, contando anidamiento. Hace falta contar porque los bloques de
    PERMISOS tienen objetos adentro de objetos.
    """
    inicio = texto.index("{", desde)
    nivel = 0
    for i in range(inicio, len(texto)):
        if texto[i] == "{":
            nivel += 1
        elif texto[i] == "}":
            nivel -= 1
            if nivel == 0:
                return texto[inicio + 1:i]
    raise ValueError("Bloque sin cerrar en config.ts")


def _constantes(texto: str, nombre: str) -> dict[str, str]:
    """Parsea `export const NOMBRE = { CLAVE: 'valor', ... }`."""
    m = re.search(rf"const {nombre}\s*=\s*", texto)
    if not m:
        raise ValueError(f"No encontré `const {nombre}` en config.ts")
    cuerpo = _bloque(texto, m.end())
    return dict(re.findall(r"(\w+)\s*:\s*'([^']*)'", cuerpo))


def _secciones(cuerpo: str, routes: dict, spreads: dict) -> dict[str, str]:
    """Parsea un bloque `secciones: { [Routes.X]: Acceso.Y, ...SPREAD }`."""
    resultado: dict[str, str] = {}
    for nombre_spread in re.findall(r"\.\.\.(\w+)", cuerpo):
        resultado.update(spreads[nombre_spread])
    for ruta, nivel in re.findall(r"\[Routes\.(\w+)\]\s*:\s*Acceso\.(\w+)", cuerpo):
        resultado[routes[ruta]] = nivel.lower()
    return resultado


def _acciones(cuerpo: str) -> dict[str, bool]:
    """Parsea un bloque `acciones: { nombreAccion: true, ... }`."""
    return {n: v == "true" for n, v in re.findall(r"(\w+)\s*:\s*(true|false)", cuerpo)}


def matriz_de_config_ts() -> dict[str, dict]:
    texto = _sin_comentarios(CONFIG_TS.read_text(encoding="utf-8"))

    routes = _constantes(texto, "Routes")
    roles = _constantes(texto, "Roles")

    # Los dos objetos que PERMISOS expande con `...`
    spreads = {}
    for nombre in ("SIN_ACCESO_A_PORTAL_SOCIO", "SIN_ACCESO_A_ADMIN"):
        m = re.search(rf"const {nombre}\s*=\s*", texto)
        cuerpo = _bloque(texto, m.end())
        spreads[nombre] = {
            routes[r]: n.lower()
            for r, n in re.findall(r"\[Routes\.(\w+)\]\s*:\s*Acceso\.(\w+)", cuerpo)
        }

    m = re.search(r"export const PERMISOS\s*:", texto)
    if not m:
        raise ValueError("No encontré `export const PERMISOS` en config.ts")
    cuerpo_permisos = _bloque(texto, m.end())

    matriz: dict[str, dict] = {}
    for m_rol in re.finditer(r"\[Roles\.(\w+)\]\s*:\s*\{", cuerpo_permisos):
        rol = roles[m_rol.group(1)]
        cuerpo_rol = _bloque(cuerpo_permisos, m_rol.end() - 1)

        m_sec = re.search(r"secciones\s*:\s*", cuerpo_rol)
        m_acc = re.search(r"acciones\s*:\s*", cuerpo_rol)
        matriz[rol] = {
            "secciones": _secciones(_bloque(cuerpo_rol, m_sec.end()), routes, spreads),
            "acciones": _acciones(_bloque(cuerpo_rol, m_acc.end())),
        }

    return matriz


# =============================================================================
# COMPARACIÓN
# =============================================================================

def main() -> int:
    if not CONFIG_TS.exists():
        print(f"[X] No encontré {CONFIG_TS.resolve()}")
        return 1

    ts = matriz_de_config_ts()
    diferencias: list[str] = []

    solo_py = set(PY_PERMISOS) - set(ts)
    solo_ts = set(ts) - set(PY_PERMISOS)
    for rol in sorted(solo_py):
        diferencias.append(f"rol '{rol}' está en permisos.py pero no en config.ts")
    for rol in sorted(solo_ts):
        diferencias.append(f"rol '{rol}' está en config.ts pero no en permisos.py")

    for rol in sorted(set(PY_PERMISOS) & set(ts)):
        for clave in ("secciones", "acciones"):
            py, tsx = PY_PERMISOS[rol][clave], ts[rol][clave]
            for nombre in sorted(set(py) | set(tsx)):
                a, b = py.get(nombre, "<falta>"), tsx.get(nombre, "<falta>")
                if a != b:
                    diferencias.append(
                        f"{rol}.{clave}.{nombre}:  permisos.py={a!r}  config.ts={b!r}"
                    )

    roles_ts = len(ts)
    secciones = len(next(iter(ts.values()))["secciones"]) if ts else 0
    acciones = len(next(iter(ts.values()))["acciones"]) if ts else 0
    print(f"backend vs PWA:  {roles_ts} roles x {secciones} secciones x {acciones} acciones.")

    # ── Tercer espejo: la app de escritorio ──────────────────────────────────
    flet = matriz_de_flet()
    if flet is None:
        diferencias.append(
            "no encontré app/permisos.py del proyecto Flet — "
            "si se movió, actualizá FLET_DIR en este script"
        )
    else:
        for rol in sorted(set(flet) - set(PY_PERMISOS)):
            diferencias.append(f"rol '{rol}' está en el permisos.py de Flet pero no en el del backend")
        for rol in sorted(set(PY_PERMISOS) - set(flet)):
            diferencias.append(f"rol '{rol}' está en el backend pero no en el permisos.py de Flet")

        celdas = 0
        for rol in sorted(set(PY_PERMISOS) & set(flet)):
            # Secciones: sólo las que Flet declara. Las siete del portal del
            # socio no están ahí a propósito — son pantallas de la PWA.
            py_sec, fl_sec = PY_PERMISOS[rol]["secciones"], flet[rol]["secciones"]
            for seccion in sorted(fl_sec):
                if seccion in SOLO_FLET:
                    continue
                celdas += 1
                a, b = py_sec.get(seccion, "<falta>"), fl_sec[seccion]
                if a != b:
                    diferencias.append(f"{rol}.secciones.{seccion}:  backend={a!r}  Flet={b!r}")

            # Acciones: acá sí se exigen todas. Una acción que Flet no conozca
            # es una que sus vistas nunca van a chequear.
            py_acc, fl_acc = PY_PERMISOS[rol]["acciones"], flet[rol]["acciones"]
            for accion in sorted(set(py_acc) | set(fl_acc)):
                celdas += 1
                a, b = py_acc.get(accion, "<falta>"), fl_acc.get(accion, "<falta>")
                if a != b:
                    diferencias.append(f"{rol}.acciones.{accion}:  backend={a!r}  Flet={b!r}")

        print(f"backend vs Flet: {len(flet)} roles, {celdas} celdas comparadas.")

        # Las pantallas que solo existen en Flet: se controla que no prometan
        # mas acceso del que da la seccion del backend que las protege.
        for rol in sorted(set(PY_PERMISOS) & set(flet)):
            for seccion, respaldo in SOLO_FLET.items():
                nivel_flet = flet[rol]["secciones"].get(seccion, "ninguno")
                nivel_real = PY_PERMISOS[rol]["secciones"].get(respaldo, "ninguno")
                if _RANGO[nivel_flet] > _RANGO[nivel_real]:
                    diferencias.append(
                        f"{rol}: Flet da '{nivel_flet}' en {seccion}, pero el "
                        f"backend solo da '{nivel_real}' en {respaldo} — la "
                        f"pantalla apareceria en el menu y contestaria 403"
                    )
        print(f"Flet-only: {len(SOLO_FLET)} pantalla(s) contrastadas contra su seccion real.")

        # Y que los nombres de sección que usa la matriz de Flet sigan siendo
        # los de su config.py. Sin esto, renombrar una ruta dejaría la matriz
        # apuntando a secciones inexistentes y TODO caería en "sin acceso".
        rutas = rutas_de_config_py()
        if not rutas:
            diferencias.append("no pude leer `class Routes` de app/config.py del Flet")
        else:
            valores = set(rutas.values())
            usadas = set()
            for permisos_rol in flet.values():
                usadas |= set(permisos_rol["secciones"])
            huerfanas = usadas - valores
            if huerfanas:
                diferencias.append(
                    f"la matriz de Flet usa secciones que no están en su "
                    f"Routes: {sorted(huerfanas)}"
                )
            else:
                print(f"Flet: las {len(usadas)} secciones de la matriz existen en Routes.")

    print()

    if diferencias:
        print(f"[X] {len(diferencias)} diferencia(s):\n")
        for d in diferencias:
            print(f"    {d}")
        print("\n    Corregí el archivo que esté mal y volvé a correr esto.")
        return 1

    print("[OK] las tres copias dicen exactamente lo mismo.")
    return 0


if __name__ == "__main__":
    # El try NO es decorativo: sin él, una excepción acá adentro imprimía el
    # traceback y el proceso terminaba con código 0 igual, así que el script
    # "pasaba" sin haber comparado nada. Un verificador que falla en silencio
    # es peor que no tenerlo.
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        print(f"\n[X] El verificador no pudo correr: {type(e).__name__}: {e}")
        sys.exit(2)
