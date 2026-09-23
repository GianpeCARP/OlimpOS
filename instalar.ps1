<#
=============================================================================
 instalar.ps1 — deja OlimpOS listo para correr en una máquina nueva
=============================================================================
 Uso (desde la raíz del repo, en PowerShell):

     .\instalar.ps1                # pregunta antes de instalar cada cosa
     .\instalar.ps1 -SinPreguntar  # instala todo lo que falte sin preguntar
     .\instalar.ps1 -SoloVerificar # no instala nada: sólo dice qué falta

 QUÉ HACE, EN ORDEN
   1. Verifica Python 3.11+, Node 20+ y git.
   2. Instala con winget lo que falte (preguntando, salvo -SinPreguntar).
   3. Crea el entorno virtual del backend e instala sus dependencias.
   4. Instala las dependencias de la app de escritorio (Flet).
   5. Instala las de la PWA con `npm ci`, que respeta el package-lock.
   6. Prepara backend\.env a partir del ejemplo y genera la clave de sesión.
   7. Comprueba que quedó bien y dice qué falta hacer a mano.

 ES IDEMPOTENTE: correrlo dos veces no rompe nada ni reinstala de gusto.

 LO QUE NO PUEDE HACER, Y NO ES UN OLVIDO: completar los SECRETOS. La cadena
 de conexión a la base no está en el repo (ni tiene que estar), así que la
 pide o la deja marcada para que la completes. Sin ella el backend no arranca.
#>

[CmdletBinding()]
param(
    # No preguntar nada: instalar todo lo que falte.
    [switch]$SinPreguntar,
    # Sólo informar qué falta, sin tocar la máquina.
    [switch]$SoloVerificar
)

$ErrorActionPreference = "Stop"

# La raíz sale de la ubicación del script y no del directorio actual: así
# funciona igual llamándolo desde cualquier lado, y el repo vive en D: en una
# máquina y en E: en otra.
$Raiz    = $PSScriptRoot
$Backend = Join-Path $Raiz "backend"
$Flet    = Join-Path $Raiz "Flet\Proyecto"
$Pwa     = Join-Path $Raiz "Proyecto - PWA\src\frontend"

$PythonMinimo = [version]"3.11"
$NodeMinimo   = [version]"20.0"

$Pendientes = New-Object System.Collections.Generic.List[string]

# --------------------------------------------------------------------------
# Salida
# --------------------------------------------------------------------------

function Titulo($texto) {
    Write-Host ""
    Write-Host "== $texto" -ForegroundColor Cyan
}
function Bien($texto)  { Write-Host "   OK    $texto" -ForegroundColor Green }
function Aviso($texto) { Write-Host "   AVISO $texto" -ForegroundColor Yellow }
function Error_($texto){ Write-Host "   ERROR $texto" -ForegroundColor Red }

function Confirmar($pregunta) {
    if ($SoloVerificar) { return $false }
    if ($SinPreguntar)  { return $true }
    $r = Read-Host "   $pregunta [S/n]"
    return ($r -eq "" -or $r -match '^[sSyY]')
}

# --------------------------------------------------------------------------
# Herramientas del sistema
# --------------------------------------------------------------------------

function Hay-Comando($nombre) {
    $cmd = Get-Command $nombre -ErrorAction SilentlyContinue
    return ($null -ne $cmd)
}

<#
 Tras instalar con winget, el PATH del proceso actual sigue siendo el viejo y
 `python`/`node` "no existen" hasta abrir otra terminal. Se relee del registro
 para poder seguir en la misma corrida.
#>
function Refrescar-Path {
    $maquina = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $usuario = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$maquina;$usuario"
}

function Instalar-Con-Winget($id, $nombre) {
    if (-not (Hay-Comando "winget")) {
        Error_ "Falta $nombre y no hay winget para instalarlo."
        $Pendientes.Add("Instalar $nombre a mano (winget no está disponible en esta máquina).")
        return $false
    }
    if (-not (Confirmar "¿Instalo $nombre con winget?")) {
        $Pendientes.Add("Instalar $nombre.")
        return $false
    }
    Write-Host "   Instalando $nombre (puede pedir permiso de administrador)..."
    # --silent evita los asistentes gráficos; --accept-* evita que se quede
    # esperando un "sí" que nadie ve cuando esto corre dentro de otro script.
    winget install --id $id --exact --silent `
        --accept-package-agreements --accept-source-agreements
    Refrescar-Path
    return $true
}

# --------------------------------------------------------------------------
# Python
# --------------------------------------------------------------------------

<#
 Devuelve el ejecutable de Python a usar, o $null. Se prefiere `py -3.11` (el
 lanzador de Windows) porque en una máquina con varias versiones es la única
 forma de pedir una puntual; si no está, se mira `python`.
#>
function Buscar-Python {
    if (Hay-Comando "py") {
        try {
            $v = (& py -3.11 -c "import platform; print(platform.python_version())" 2>$null)
            if ($LASTEXITCODE -eq 0 -and $v) { return @{ Cmd = "py"; Args = @("-3.11"); Version = [version]$v } }
        } catch { }
    }
    if (Hay-Comando "python") {
        try {
            $v = (& python -c "import platform; print(platform.python_version())" 2>$null)
            if ($LASTEXITCODE -eq 0 -and $v) { return @{ Cmd = "python"; Args = @(); Version = [version]$v } }
        } catch { }
    }
    return $null
}

function Asegurar-Python {
    Titulo "Python 3.11 o superior"
    $py = Buscar-Python
    if ($py -and $py.Version -ge $PythonMinimo) {
        Bien "Python $($py.Version) encontrado."
        return $py
    }
    if ($py) { Aviso "Python $($py.Version) es viejo: hace falta $PythonMinimo o superior." }
    else     { Aviso "No se encontró Python." }

    if (Instalar-Con-Winget "Python.Python.3.11" "Python 3.11") {
        $py = Buscar-Python
        if ($py -and $py.Version -ge $PythonMinimo) {
            Bien "Python $($py.Version) instalado."
            return $py
        }
        Aviso "Python quedó instalado pero no aparece en esta terminal. Cerrala y abrí otra."
        $Pendientes.Add("Volver a correr el instalador en una terminal nueva (para que tome Python).")
    }
    return $null
}

# --------------------------------------------------------------------------
# Node
# --------------------------------------------------------------------------

function Version-Node {
    if (-not (Hay-Comando "node")) { return $null }
    try {
        $v = (& node --version) -replace '^v', ''   # node imprime "v20.11.1"
        return [version]$v
    } catch { return $null }
}

function Asegurar-Node {
    Titulo "Node.js 20 o superior"
    $v = Version-Node
    if ($v -and $v -ge $NodeMinimo) {
        Bien "Node $v encontrado."
        return $true
    }
    if ($v) { Aviso "Node $v es viejo: hace falta $NodeMinimo o superior." }
    else    { Aviso "No se encontró Node." }

    if (Instalar-Con-Winget "OpenJS.NodeJS.LTS" "Node.js LTS") {
        $v = Version-Node
        if ($v -and $v -ge $NodeMinimo) {
            Bien "Node $v instalado."
            return $true
        }
        Aviso "Node quedó instalado pero no aparece en esta terminal. Cerrala y abrí otra."
        $Pendientes.Add("Volver a correr el instalador en una terminal nueva (para que tome Node).")
    }
    return $false
}

# --------------------------------------------------------------------------
# Dependencias de cada proyecto
# --------------------------------------------------------------------------

function Instalar-Backend($py) {
    Titulo "Backend (FastAPI)"
    if (-not $py) { Aviso "Sin Python no se puede preparar el backend."; return $null }

    $venvPython = Join-Path $Backend ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        Bien "El entorno virtual ya existe."
    } else {
        if ($SoloVerificar) { Aviso "Falta crear el entorno virtual."; return $null }
        Write-Host "   Creando el entorno virtual..."
        & $py.Cmd @($py.Args + @("-m", "venv", (Join-Path $Backend ".venv")))
        if (-not (Test-Path $venvPython)) { Error_ "No se pudo crear el entorno virtual."; return $null }
        Bien "Entorno virtual creado."
    }

    if ($SoloVerificar) { return $venvPython }

    Write-Host "   Instalando dependencias (puede tardar unos minutos)..."
    & $venvPython -m pip install --upgrade pip --quiet
    & $venvPython -m pip install -r (Join-Path $Backend "requirements.txt") --quiet
    if ($LASTEXITCODE -ne 0) { Error_ "Falló la instalación de dependencias del backend."; return $null }
    Bien "Dependencias del backend instaladas."
    return $venvPython
}

<#
 Flet usa el Python GLOBAL y no un entorno virtual propio: así está documentado
 en CLAUDE.md, donde la app se corre con `python main.py` y `python
 pruebas_vistas.py`. Cambiarlo obligaría a cambiar también esos comandos.
#>
function Instalar-Flet($py) {
    Titulo "App de escritorio (Flet)"
    if (-not $py) { Aviso "Sin Python no se pueden instalar las dependencias de Flet."; return }
    if ($SoloVerificar) {
        & $py.Cmd @($py.Args + @("-c", "import flet")) *> $null
        if ($LASTEXITCODE -eq 0) { Bien "Flet ya está instalado." }
        else { Aviso "Falta instalar las dependencias de Flet." }
        return
    }
    Write-Host "   Instalando dependencias..."
    & $py.Cmd @($py.Args + @("-m", "pip", "install", "-r", (Join-Path $Flet "requirements.txt"), "--quiet"))
    if ($LASTEXITCODE -ne 0) { Error_ "Falló la instalación de dependencias de Flet."; return }
    Bien "Dependencias de Flet instaladas."
}

function Instalar-Pwa($hayNode) {
    Titulo "PWA (React + Vite)"
    if (-not $hayNode) { Aviso "Sin Node no se pueden instalar las dependencias de la PWA."; return }
    if ($SoloVerificar) {
        if (Test-Path (Join-Path $Pwa "node_modules")) { Bien "node_modules ya está." }
        else { Aviso "Falta instalar las dependencias de la PWA." }
        return
    }
    Push-Location $Pwa
    try {
        Write-Host "   Instalando dependencias (npm ci, respeta el package-lock)..."
        npm ci --silent
        if ($LASTEXITCODE -ne 0) {
            Aviso "npm ci falló; se prueba con npm install."
            npm install --silent
        }
        if ($LASTEXITCODE -ne 0) { Error_ "Falló la instalación de dependencias de la PWA."; return }
        Bien "Dependencias de la PWA instaladas."
    } finally {
        Pop-Location
    }
}

# --------------------------------------------------------------------------
# Configuración (.env)
# --------------------------------------------------------------------------

function Preparar-Env($venvPython) {
    Titulo "Configuración del backend (.env)"
    $envPath     = Join-Path $Backend ".env"
    $ejemploPath = Join-Path $Backend ".env.example"

    if (Test-Path $envPath) {
        Bien "backend\.env ya existe: no se toca."
        return
    }
    if ($SoloVerificar) { Aviso "Falta crear backend\.env (copiar de .env.example)."; return }

    Copy-Item $ejemploPath $envPath
    $contenido = Get-Content $envPath -Raw

    # La clave de sesión se genera SOLA: es un secreto que nadie tiene que
    # elegir a mano, y dejar la de ejemplo sería dejar la puerta abierta.
    if ($venvPython) {
        $clave = & $venvPython -c "import secrets; print(secrets.token_urlsafe(64))"
        if ($clave) {
            $contenido = $contenido -replace 'JWT_SECRET_KEY=.*', "JWT_SECRET_KEY=$clave"
            Bien "Clave de sesión generada."
        }
    }

    # La cadena de conexión NO se puede adivinar: o la pega la persona, o queda
    # marcada para completarla antes de arrancar.
    if (-not $SinPreguntar) {
        Write-Host "   Pegá la cadena de conexión de la base (Neon o Postgres local)."
        Write-Host "   Enter para dejarla en blanco y completarla después." -ForegroundColor DarkGray
        $url = Read-Host "   DATABASE_URL"
        if ($url) {
            $contenido = $contenido -replace 'DATABASE_URL=.*', "DATABASE_URL=$url"
            Bien "Cadena de conexión guardada."
        }
    }

    Set-Content -Path $envPath -Value $contenido -Encoding UTF8 -NoNewline
    if ($contenido -match 'DATABASE_URL=postgresql://usuario:password@') {
        Aviso "backend\.env quedó con la cadena de conexión de ejemplo."
        $Pendientes.Add("Completar DATABASE_URL en backend\.env con la cadena real de la base.")
    }
}

# --------------------------------------------------------------------------
# Verificación final
# --------------------------------------------------------------------------

function Verificar($venvPython, $hayNode) {
    Titulo "Verificación"

    if ($venvPython -and (Test-Path $venvPython)) {
        Push-Location $Backend
        try {
            & $venvPython -c "import main" *> $null
            if ($LASTEXITCODE -eq 0) { Bien "El backend importa sin errores." }
            else {
                Error_ "El backend no importa. Probá: .venv\Scripts\python.exe -c ""import main"""
                $Pendientes.Add("Revisar por qué no importa el backend.")
            }

            $envPath = Join-Path $Backend ".env"
            $tieneUrl = (Test-Path $envPath) -and -not ((Get-Content $envPath -Raw) -match 'DATABASE_URL=postgresql://usuario:password@')
            if ($tieneUrl) {
                & $venvPython check_db.py *> $null
                if ($LASTEXITCODE -eq 0) { Bien "Conecta con la base." }
                else {
                    Aviso "No conecta con la base. Probá: .venv\Scripts\python.exe check_db.py"
                    $Pendientes.Add("Revisar la conexión a la base (DATABASE_URL).")
                }
            } else {
                Aviso "Sin cadena de conexión no se puede probar la base."
            }
        } finally { Pop-Location }
    }

    if ($hayNode -and (Test-Path (Join-Path $Pwa "node_modules"))) {
        Push-Location $Pwa
        try {
            npx tsc --noEmit -p tsconfig.app.json
            if ($LASTEXITCODE -eq 0) { Bien "La PWA compila sin errores de tipos." }
            else {
                Error_ "La PWA no compila. Probá: npx tsc --noEmit -p tsconfig.app.json"
                $Pendientes.Add("Revisar los errores de compilación de la PWA.")
            }
        } finally { Pop-Location }
    }
}

# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

Write-Host ""
Write-Host "OlimpOS — instalación" -ForegroundColor White
if ($SoloVerificar) { Write-Host "(modo verificación: no se instala nada)" -ForegroundColor DarkGray }

if (-not (Hay-Comando "git")) {
    Titulo "git"
    Aviso "No se encontró git. No hace falta para correr el sistema, pero sí para actualizarlo."
    Instalar-Con-Winget "Git.Git" "git" | Out-Null
}

$py      = Asegurar-Python
$hayNode = Asegurar-Node

$venvPython = Instalar-Backend $py
Instalar-Flet $py
Instalar-Pwa $hayNode
Preparar-Env $venvPython
Verificar $venvPython $hayNode

Titulo "Listo"
if ($Pendientes.Count -gt 0) {
    Write-Host "   Queda pendiente:" -ForegroundColor Yellow
    foreach ($p in $Pendientes) { Write-Host "     - $p" -ForegroundColor Yellow }
    Write-Host ""
}
Write-Host "   Para arrancar:" -ForegroundColor White
Write-Host "     Backend:  cd backend;  .venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000"
Write-Host "     PWA:      cd 'Proyecto - PWA\src\frontend';  npm run dev        (http://localhost:5173)"
Write-Host "     Flet:     cd Flet\Proyecto;  python main.py"
Write-Host ""
Write-Host "   La primera cuenta sale de DUENO_INICIAL_* del .env y el sistema"
Write-Host "   te obliga a cambiarle la contraseña en el primer ingreso."
Write-Host ""

if ($Pendientes.Count -gt 0) { exit 1 }
exit 0
