"""
check_permisos.py
-----------------
Compara la matriz de permisos de `permisos.py` (backend) contra la de
`Proyecto/src/frontend/src/config.ts` (PWA) y falla si difieren.

POR QUÉ EXISTE:
permisos.py documenta que es un espejo de config.ts y que desincronizarse es
silencioso. Un comentario que pide "acordate de tocar el otro" es exactamente
el tipo de regla que nadie cumple a los tres meses. Esto la vuelve verificable
en un segundo.

Los dos modos de falla que detecta son asimétricos y los dos son malos:
  - El backend es MÁS restrictivo -> el botón aparece y la API responde 403.
  - El backend es MÁS permisivo   -> la API deja pasar algo que el frontend
                                     creía prohibido. Este es el grave.

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

CONFIG_TS = pathlib.Path("../Proyecto/src/frontend/src/config.ts")


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
    print(f"Comparadas {roles_ts} roles × {secciones} secciones × {acciones} acciones.\n")

    if diferencias:
        print(f"[X] {len(diferencias)} diferencia(s):\n")
        for d in diferencias:
            print(f"    {d}")
        print("\n    Corregí el archivo que esté mal y volvé a correr esto.")
        return 1

    print("[OK] permisos.py y config.ts dicen exactamente lo mismo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
