@echo off
rem =============================================================================
rem Arranca demonio_videos.py en segundo plano, minimizado, con log.
rem
rem Pensado para el servidor: un acceso directo a este archivo en la carpeta de
rem Inicio de Windows (Win+R -> shell:startup) lo levanta solo al iniciar sesion.
rem El log queda en logs\demonio_videos.log (logs/ no se versiona).
rem =============================================================================
cd /d "%~dp0"
if not exist logs mkdir logs
set PYTHONUNBUFFERED=1
start "OlimpOS demonio de videos" /min cmd /c ".venv\Scripts\python.exe demonio_videos.py >> logs\demonio_videos.log 2>&1"
