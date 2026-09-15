"""
demonio_videos.py
-----------------
Baja a VIDEOS_DIR los videos de YouTube que los entrenadores cargaron en los
ejercicios y que todavía no estén descargados. Corre en el servidor FTP.

    .venv/Scripts/python.exe demonio_videos.py            # queda corriendo
    .venv/Scripts/python.exe demonio_videos.py --una-vez  # una pasada y sale

"Ya descargado" = existe VIDEOS_DIR/<id de youtube>.mp4 (ver videos.py). No
hay estado en la base: si una descarga falla, la próxima pasada la reintenta.

Necesita ffmpeg en el PATH: YouTube da el video y el audio por separado por
encima de 360p, y ffmpeg es el que los junta en un solo mp4.
"""

import os
import shutil
import sys
import time

import yt_dlp
from dotenv import load_dotenv

from database import SessionLocal
from models import Ejercicio
from videos import VIDEOS_DIR, archivo_de, id_youtube

load_dotenv()

MINUTOS_ENTRE_PASADAS = int(os.getenv("VIDEOS_INTERVALO_MIN", "10"))

# El canal oficial del gimnasio: "@handle", la URL del canal o su id (UC...).
# Vacío = se acepta cualquier video de YouTube.
CANAL = os.getenv("VIDEOS_CANAL_YOUTUBE", "").strip()

# Se baja a una subcarpeta y se mueve al terminar: así /videos nunca sirve un
# archivo a medio bajar, que el socio vería cortado.
CARPETA_TEMPORAL = VIDEOS_DIR / ".descargando"

OPCIONES_YTDLP = {
    # mp4 con H.264 + AAC, hasta 720p: es lo que reproduce cualquier celular,
    # iPhone incluido (Safari no reproduce VP9/webm en todas las versiones).
    "format": (
        "bv*[height<=720][vcodec^=avc1]+ba[ext=m4a]"
        "/b[height<=720][ext=mp4]/b[ext=mp4]"
    ),
    "merge_output_format": "mp4",
    "outtmpl": str(CARPETA_TEMPORAL / "%(id)s.%(ext)s"),
    "noplaylist": True,
    "quiet": True,
    "noprogress": True,
    "no_warnings": True,
}


def _ultimo_tramo(valor: str | None) -> str:
    """'https://www.youtube.com/@Gym/' -> '@gym'. Para comparar canales."""
    return (valor or "").rstrip("/").split("/")[-1].lower()


def es_del_canal(info: dict) -> bool:
    if not CANAL:
        return True
    buscado = _ultimo_tramo(CANAL)
    del_video = {
        _ultimo_tramo(info.get(campo))
        for campo in ("channel_id", "channel_url", "uploader_id", "uploader_url")
    }
    return buscado in del_video


def links_pendientes() -> list[str]:
    """Los links cargados en ejercicios cuyo archivo todavía no existe."""
    db = SessionLocal()
    try:
        filas = db.query(Ejercicio.url_video).filter(Ejercicio.url_video.isnot(None)).all()
    finally:
        db.close()

    pendientes, vistos = [], set()
    for (url,) in filas:
        vid = id_youtube(url)
        # Dos ejercicios con el mismo video: se baja una sola vez.
        if vid and vid not in vistos and not archivo_de(url).is_file():
            vistos.add(vid)
            pendientes.append(url)
    return pendientes


def descargar(url: str) -> None:
    vid = id_youtube(url)
    CARPETA_TEMPORAL.mkdir(parents=True, exist_ok=True)
    # Restos de un intento anterior que se cortó.
    for resto in CARPETA_TEMPORAL.glob(f"{vid}.*"):
        resto.unlink(missing_ok=True)

    with yt_dlp.YoutubeDL(OPCIONES_YTDLP) as ydl:
        info = ydl.extract_info(url, download=False)
        if not es_del_canal(info):
            print(f"  omitido {vid}: no es del canal {CANAL} "
                  f"(es de {info.get('channel') or '?'})")
            return
        ydl.process_ie_result(info, download=True)

    bajado = CARPETA_TEMPORAL / f"{vid}.mp4"
    if not bajado.is_file():
        raise RuntimeError("yt-dlp terminó pero no dejó el mp4 (¿falta ffmpeg?)")
    shutil.move(str(bajado), str(VIDEOS_DIR / f"{vid}.mp4"))
    print(f"  listo {vid}.mp4")


def pasada() -> None:
    try:
        pendientes = links_pendientes()
    except Exception as e:  # noqa: BLE001
        # Base caída o sin red: se reintenta en la próxima pasada.
        print(f"No se pudo leer la base: {e}")
        return

    if pendientes:
        print(f"{len(pendientes)} video(s) para descargar")
    for url in pendientes:
        try:
            descargar(url)
        except Exception as e:  # noqa: BLE001
            # Un link roto no frena a los demás; se reintenta la próxima pasada.
            print(f"  falló {url}: {e}")


def main() -> None:
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    if shutil.which("ffmpeg") is None:
        print("AVISO: ffmpeg no está en el PATH; los videos pueden no descargarse.")
    print(f"Demonio de videos -> {VIDEOS_DIR}  (canal: {CANAL or 'cualquiera'})")

    if "--una-vez" in sys.argv:
        pasada()
        return

    while True:
        pasada()
        time.sleep(MINUTOS_ENTRE_PASADAS * 60)


if __name__ == "__main__":
    main()
