# Genera el juego de iconos de la PWA desde el logo original transparente.
#
# POR QUE HACIA FALTA:
#   - El favicon tenia FONDO NEGRO. El logo original es transparente; el fondo
#     se lo agrego el generador que se uso en su momento.
#   - Se veia CHICO porque un mismo archivo servia para purpose "any" y para
#     "maskable". Un icono maskable se recorta a circulo, asi que necesita un
#     margen de seguridad grande, y ese margen es el que lo hacia ver diminuto
#     cuando el sistema lo usaba como icono normal. Van archivos separados.
#
# Sin acentos ni guiones largos a proposito: PowerShell 5.1 lee los .ps1 como
# ANSI y cualquier caracter fuera de ASCII rompe el parseo.

Add-Type -AssemblyName System.Drawing

$SRC     = "D:\OlimpOs\Proyeto-Python\Proyecto\assets\logo-removebg-preview.png"
$DESTINO = "D:\OlimpOs\Proyecto\src\frontend\public\icons"
$FONDO   = [System.Drawing.ColorTranslator]::FromHtml("#15171C")   # surface-base

$origen = [System.Drawing.Bitmap]::FromFile($SRC)

function Nuevo-Icono {
    param(
        [string]$Archivo,
        [int]$Lado,
        [double]$Ocupacion,
        [bool]$ConFondo
    )

    $bmp = New-Object System.Drawing.Bitmap($Lado, $Lado,
        [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.InterpolationMode  = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.SmoothingMode      = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
    $g.PixelOffsetMode    = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
    $g.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality

    if ($ConFondo) { $g.Clear($FONDO) }
    else           { $g.Clear([System.Drawing.Color]::Transparent) }

    # Escala preservando la proporcion: el logo es mas alto que ancho, asi que
    # manda el alto. Estirarlo para llenar el cuadrado lo deformaria.
    $disponible = $Lado * $Ocupacion
    $escala = [Math]::Min($disponible / $origen.Width, $disponible / $origen.Height)
    $w = [int]($origen.Width  * $escala)
    $h = [int]($origen.Height * $escala)
    $x = [int](($Lado - $w) / 2)
    $y = [int](($Lado - $h) / 2)

    $g.DrawImage($origen, $x, $y, $w, $h)
    $g.Dispose()

    $ruta = Join-Path $DESTINO $Archivo
    $bmp.Save($ruta, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()

    $kb = [Math]::Round((Get-Item $ruta).Length / 1KB, 1)
    $fondoTxt = if ($ConFondo) { "fondo oscuro" } else { "TRANSPARENTE" }
    "  {0,-24} {1,4}px  logo {2,3}%  {3,-13} {4} KB" -f $Archivo, $Lado, [int]($Ocupacion*100), $fondoTxt, $kb
}

"Iconos normales (purpose any), el logo llena el cuadro:"
# Transparentes: en la pestana del navegador y en Android se ven sobre el
# fondo del sistema, que puede ser claro u oscuro. Un fondo negro pegado
# quedaria como un cuadrado negro sobre una barra clara.
Nuevo-Icono -Archivo "favicon-196.png" -Lado 196 -Ocupacion 0.96 -ConFondo $false
Nuevo-Icono -Archivo "icon-192.png"    -Lado 192 -Ocupacion 0.92 -ConFondo $false
Nuevo-Icono -Archivo "icon-512.png"    -Lado 512 -Ocupacion 0.92 -ConFondo $false

""
"Icono de iOS, CON fondo porque iOS no respeta la transparencia:"
# Si se le manda un PNG transparente, iOS lo compone sobre NEGRO puro. Mejor
# poner el fondo de la app que dejar que elija el sistema. 78% y no 92%
# porque iOS le redondea las esquinas por su cuenta.
Nuevo-Icono -Archivo "apple-icon-180.png" -Lado 180 -Ocupacion 0.78 -ConFondo $true

""
"Iconos maskable, el sistema los recorta (circulo, cuadrado redondeado...):"
# La zona segura de un maskable es un circulo de 80% del lado. Para que entre
# completo tiene que medir 80/raiz(2) = 56%. Se usa 58%: entra en cualquier
# forma que aplique Android.
Nuevo-Icono -Archivo "maskable-192.png" -Lado 192 -Ocupacion 0.58 -ConFondo $true
Nuevo-Icono -Archivo "maskable-512.png" -Lado 512 -Ocupacion 0.58 -ConFondo $true

$origen.Dispose()
""
"Listo."
