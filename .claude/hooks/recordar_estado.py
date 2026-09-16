"""
Hook Stop de Claude Code: que ninguna sesión termine con código cambiado y
docs/ESTADO-ACTUAL.md sin actualizar.

Por qué existe: CLAUDE.md + ESTADO-ACTUAL.md son lo único que una sesión nueva
(o después de un /clear) sabe del proyecto. Pedirlo por escrito no alcanzaba:
una instrucción se olvida; esto no.

Cómo decide, sin loops y sin molestar de más:
  1. Mira con git qué archivos de CÓDIGO tienen cambios sin commitear
     (modificados o nuevos). Los .md de contexto y las notas no cuentan.
  2. Si ESTADO-ACTUAL.md es más nuevo que el último de esos cambios, pasa.
  3. Si no, frena UNA vez por cada conjunto de cambios: guarda una huella de
     los cambios que ya avisó, y si la sesión decide que no hay nada que
     actualizar y vuelve a terminar, la huella coincide y la deja ir.

Si algo falla (no hay git, no es un repo) no bloquea nada: un hook roto no
puede dejar la sesión trabada.
"""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

# Rutas que NO son código: tocarlas no obliga a actualizar el estado.
NO_CUENTAN = {
    "docs/ESTADO-ACTUAL.md",
    "CLAUDE.md",
    "A CORREGIR PWA .txt",
    "backend/CONTRASEÑAS PARA TESTEO Y ACTUALIZADAS.txt",
}
PREFIJOS_NO_CUENTAN = (".claude/",)

ESTADO = "docs/ESTADO-ACTUAL.md"

MOTIVO = (
    "Hay cambios de código posteriores a la última actualización de "
    "docs/ESTADO-ACTUAL.md. Antes de terminar, actualizalo siguiendo la regla "
    "de CLAUDE.md: es la foto del presente para la próxima sesión (o después "
    "de un /clear). Corregí el punto que cambió (sacá de 'Lo que falta' lo "
    "terminado, sumá lo nuevo pendiente o sin probar), sin agregar historial "
    "ni contradecir CLAUDE.md. Si el cambio altera una regla del negocio, una "
    "decisión o la estructura, corregí también CLAUDE.md. Si de verdad no "
    "cambia nada del estado (un ajuste mínimo), no toques nada y terminá."
)


def _cambios(raiz: Path) -> list[str]:
    salida = subprocess.run(
        ["git", "-C", str(raiz), "status", "--porcelain", "-z",
         "--untracked-files=all"],
        capture_output=True, check=True,
    ).stdout.decode("utf-8", errors="replace")
    rutas = []
    entradas = salida.split("\0")
    i = 0
    while i < len(entradas):
        e = entradas[i]
        i += 1
        if len(e) < 4:
            continue
        codigo, ruta = e[:2], e[3:]
        if codigo[0] in "RC":  # renombre: la entrada siguiente es la ruta vieja
            i += 1
        if "D" in codigo:      # borrado: no hay archivo del que tomar la fecha
            continue
        rutas.append(ruta)
    return rutas


def main() -> None:
    try:
        datos = json.load(sys.stdin)
    except Exception:
        datos = {}

    raiz = Path(os.environ.get("CLAUDE_PROJECT_DIR") or datos.get("cwd") or ".")

    try:
        codigo = [r for r in _cambios(raiz)
                  if r not in NO_CUENTAN and not r.startswith(PREFIJOS_NO_CUENTAN)]
    except Exception:
        return

    if not codigo:
        return

    ultimo_cambio = max((raiz / r).stat().st_mtime for r in codigo
                        if (raiz / r).exists())
    estado = raiz / ESTADO
    if estado.exists() and estado.stat().st_mtime >= ultimo_cambio:
        return

    huella = hashlib.sha256(
        "\n".join(f"{r}:{(raiz / r).stat().st_mtime}" for r in sorted(codigo)
                  if (raiz / r).exists()).encode()
    ).hexdigest()
    visto = raiz / ".claude" / "hooks" / ".estado-avisado"
    if visto.exists() and visto.read_text(encoding="utf-8").strip() == huella:
        return
    visto.write_text(huella, encoding="utf-8")

    # ensure_ascii: la consola de Windows escribe en cp1252 y rompía los acentos;
    # con escapes \uXXXX el JSON llega intacto sea cual sea la codificación.
    print(json.dumps({"decision": "block", "reason": MOTIVO}, ensure_ascii=True))


if __name__ == "__main__":
    main()
