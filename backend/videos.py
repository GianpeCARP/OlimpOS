"""
videos.py
---------
Videos tutoriales de los ejercicios: dónde viven y cómo se nombran.

El recorrido completo:
    1. El entrenador crea un ejercicio y pega un link de YouTube (url_video).
    2. demonio_videos.py —corriendo en el servidor FTP— baja cada link que
       todavía no tenga archivo, a VIDEOS_DIR.
    3. El backend sirve esa carpeta en /videos, y el socio lo ve con "Ver técnica".

El entrenador nunca toca el servidor: sólo carga el link.

POR QUÉ EL ARCHIVO SE LLAMA COMO EL ID DE YOUTUBE (y no como el ejercicio)
--------------------------------------------------------------------------
Así "¿ya se bajó?" es mirar si el archivo existe, sin columnas de estado en la
base. Y si el entrenador cambia el link, el id cambia, el archivo nuevo no
existe y el demonio lo baja solo. El nombre del ejercicio no sirve: tiene
tildes y espacios, y puede cambiar.

POR QUÉ SE SIRVE POR HTTP Y NO SE LINKEA EL FTP
-----------------------------------------------
Los navegadores no reproducen ftp://. El FTP es donde se guardan; lo que ve
el socio es la misma carpeta servida por el backend.
"""

import os
import re
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Por defecto, /videos en la raíz del repo (al lado de backend/). En el
# servidor real se apunta al directorio del FTP con VIDEOS_DIR.
VIDEOS_DIR = Path(
    os.getenv("VIDEOS_DIR") or Path(__file__).resolve().parent.parent / "videos"
)

# Ruta HTTP donde main.py monta la carpeta.
RUTA_HTTP = "/videos"

# Los ids de YouTube son 11 caracteres de este alfabeto. Cubre los formatos
# que se pegan en la práctica: watch?v=, youtu.be/, shorts/ y embed/.
_PATRON_ID = re.compile(
    r"(?:youtube\.com/(?:watch\?(?:.*&)?v=|shorts/|embed/|live/)|youtu\.be/)"
    r"([A-Za-z0-9_-]{11})"
)


def id_youtube(url: str | None) -> str | None:
    """El id del video de un link de YouTube, o None si no es uno."""
    if not url:
        return None
    m = _PATRON_ID.search(url)
    return m.group(1) if m else None


def archivo_de(url: str | None) -> Path | None:
    """Dónde queda (o va a quedar) el archivo de ese link."""
    vid = id_youtube(url)
    return VIDEOS_DIR / f"{vid}.mp4" if vid else None


def video_local(url: str | None) -> str | None:
    """
    La ruta HTTP del video si YA está descargado, o None.

    None mientras el demonio no lo bajó: el socio ve el ejercicio igual, sólo
    que sin el botón de "Ver técnica".
    """
    archivo = archivo_de(url)
    if archivo is None or not archivo.is_file():
        return None
    return f"{RUTA_HTTP}/{archivo.name}"
