# Levantar OlimpOS en otra computadora

Todo lo que hace falta para pasar de un `git clone` a las tres apps
funcionando. Escrito para la máquina nueva: acá no se asume que quede nada de
la anterior.

> **La base NO se migra.** Es Neon (PostgreSQL en la nube), así que desde
> cualquier máquina vas a ver exactamente los mismos datos. Lo único que viaja
> a mano es la cadena de conexión.

---

## 1. Lo único que NO está en el repo

Dos archivos `.env`, y están ignorados a propósito. El del backend tiene la
contraseña de la base adentro; subirlo sería publicar la llave junto con la
puerta.

| Archivo | Qué tiene | Cómo lo conseguís |
|---|---|---|
| `backend/.env` | `DATABASE_URL` (Neon + contraseña), `JWT_SECRET_KEY`, `DUENO_INICIAL_*`, `CORS_ORIGINS`, SMTP, `MP_*` | **Copialo a mano** de la máquina vieja |
| `Proyecto/src/frontend/.env` | `VITE_API_URL` y `API_PROXY_DESTINO` — **sin secretos** | Copiá `.env.example` de al lado |

Los tres `.env.example` (backend, PWA y Flet) **sí** están en el repo: sirven
de referencia de qué variable va en cada uno.

**Dos que importan más que el resto:**

- **`JWT_SECRET_KEY` tiene que ser LA MISMA** en las dos máquinas. Si cambia,
  todos los tokens emitidos antes dejan de validar y las sesiones abiertas se
  caen. No es un problema de seguridad, pero desconcierta: el login anda y
  cualquier pantalla responde 401.
- **`CORS_ORIGINS`** tiene que incluir el origen desde el que se abre la PWA.
  Si la IP de red de la máquina nueva es otra, hay que agregarla. Ojo: para
  el uso normal (`localhost:5173`) no hace falta tocar nada, porque la PWA
  habla con el backend a través del proxy de Vite y nunca hace un pedido
  cross-origin. Ver el comentario largo de `vite.config.ts`.

---

## 2. Qué tiene que estar instalado

Lo que se está usando hoy, verificado:

| | Versión |
|---|---|
| Python | **3.11.9** |
| Node | **24.18.0** |
| npm | **11.16.0** |

No hace falta clavar esas versiones exactas, pero Python tiene que ser 3.10 o
más: el código usa `str | None` en las anotaciones y eso no compila en 3.9.

---

## 3. Los pasos

```bash
git clone https://github.com/GianpeCARP/OlimpOS.git
cd OlimpOS
```

### Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
# copiá acá tu backend/.env ANTES de seguir
.venv/Scripts/python.exe -c "import main"      # compila Y ejecuta
```

> **Usá SIEMPRE el Python del venv, no el global.** El global no tiene las
> dependencias y tira errores que parecen bugs del proyecto.

Para levantarlo:

```bash
.venv/Scripts/python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Al arrancar precalienta el pool de conexiones y lanza un latido cada 2
minutos contra Neon. Los dos son a propósito — ver la §14 de la bitácora.

### PWA (el portal del socio y el panel del personal)

```bash
cd Proyecto/src/frontend
npm install
cp .env.example .env        # no tiene secretos
npm run dev
```

Queda en `http://localhost:5173`.

### App de escritorio (Flet, para el personal)

```bash
cd Proyeto-Python/Proyecto
pip install -r requirements.txt      # flet 0.84.0, requests, python-dotenv
python main.py
```

Abre una ventana nativa. Necesita el backend levantado.

---

## 4. Comprobar que quedó bien

```bash
cd backend
.venv/Scripts/python.exe check_permisos.py    # las 3 copias de la matriz
```

Las **9 suites de integración** corren contra Neon de verdad y necesitan **la
base vacía**. Entre suite y suite hay que vaciarla, o la anterior le deja
datos a la siguiente y fallan por el escenario y no por un bug:

```bash
.venv/Scripts/python.exe pruebas/vaciar_base.py --si
.venv/Scripts/python.exe pruebas/test_promociones.py
```

> **Antes de correr una suite, fijate contra QUÉ backend estás corriendo.** Un
> `uvicorn` que no pudo tomar el puerto 8000 muere en silencio y el proceso
> viejo sigue atendiendo. Una corrida entera dio tres fallos falsos por eso:
> ```bash
> curl -s http://127.0.0.1:8000/openapi.json | .venv/Scripts/python.exe -c "import json,sys; print(len(json.load(sys.stdin)['paths']))"
> ```

Para la app Flet, `compileall` **no alcanza** (aprueba un nombre sin importar
y una división por cero que sólo pasan al abrir la pantalla):

```bash
cd Proyeto-Python/Proyecto
python pruebas_vistas.py     # build() de cada vista con cada rol
```

Para la PWA:

```bash
cd Proyecto/src/frontend
npx tsc --noEmit -p tsconfig.app.json   # SIN -p no compila nada y siempre da OK
npx oxlint src/
```

---

## 5. Datos para poder ver algo

Después de un `vaciar_base.py` la base queda en **6 filas** y las pantallas no
muestran nada. Para recorrerlas:

```bash
.venv/Scripts/python.exe pruebas/escenario_demo.py
```

Carga 4 empleados, 3 socios, patologías, promociones y un cobro con descuento.
Las contraseñas están en `backend/CONTRASEÑAS PARA TESTEO Y ACTUALIZADAS.txt`.

> Ese script le deja al `dueno` la contraseña `Demo2026!`, porque entra con la
> inicial del `.env` y la cambia. El archivo de contraseñas explica cómo
> devolverla.

---

## 6. Verlo desde el celular

La PWA se puede abrir desde un teléfono en la misma red. Hacen falta tres
cosas:

**1. Vite escuchando en la red** (por defecto sólo escucha en localhost):

```bash
npx vite --host 0.0.0.0 --port 5173
```

**2. La IP de la máquina:**

```powershell
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' }
```

**3. El firewall.** Windows bloquea todo lo entrante en redes marcadas como
Públicas. Una regla acotada al puerto y a la red local:

```powershell
New-NetFirewallRule -DisplayName "OlimpOS PWA (Vite 5173) - red local" `
  -Direction Inbound -Protocol TCP -LocalPort 5173 `
  -RemoteAddress LocalSubnet -Action Allow -Profile Any
```

Después, en el celular: `http://<IP>:5173`.

**No hace falta abrir el puerto 8000 ni tocar CORS**: la PWA habla con el
backend por el proxy de Vite, así que para el navegador del teléfono todo es
el mismo origen.

### Instalar la PWA como app

No va a aparecer "Instalar app" sobre HTTP: los navegadores exigen contexto
seguro. La salida sin instalar nada ni exponer la red es que el celular la vea
como `localhost`, que sí cuenta como seguro:

1. Celular por USB, con **Depuración USB** activada.
2. En Chrome de la compu: `chrome://inspect/#devices` → **Port forwarding** →
   `5173` → `localhost:5173`.
3. En el celular: `http://localhost:5173`.

Para eso hay que poner `devOptions: { enabled: true }` en el bloque `VitePWA`
de `vite.config.ts`, que está apagado a propósito — ver el comentario ahí.

---

## 7. El proyecto Flet vive en DOS repos

- Monorepo (las dos apps) → `github.com/GianpeCARP/OlimpOS`
- Sólo el Flet → `github.com/GianpeCARP/Proyecto`

En la máquina nueva, `Proyeto-Python/Proyecto` llega **como parte del
monorepo**, sin el `.git.repo-viejo-backup` que tenía la vieja. Con eso
alcanza para trabajar. Si además querés pushear al repo separado desde ahí,
hay que clonarlo aparte — el `CLAUDE.md` explica el mecanismo con
`GIT_DIR`/`GIT_WORK_TREE`.

---

## 8. Cosas que ya costaron tiempo

- **`compileall` compila pero no ejecuta.** Un import faltante pasa el chequeo
  y revienta al arrancar. Un nombre usado sólo dentro de una función tampoco
  lo detecta el import: eso mordió tres veces.
- **Correr no alcanza si no verificás contra qué corrés** (el backend viejo en
  el 8000).
- **Que el proceso levante no significa que la pantalla funcione.** Tres bugs
  llegaron a una demo por eso; para eso existe `pruebas_vistas.py`.
- **A los 5 intentos fallidos la cuenta se bloquea**, y el mensaje es idéntico
  al de contraseña equivocada (a propósito). Si el login falla y estás seguro
  de la clave, mirá la fila:
  `SELECT username, bloqueado, intentos_fallidos FROM "Usuario";`
- **`npx tsc --noEmit` sin `-p`** no compila nada y siempre da OK.
- **La paleta está duplicada** entre `index.css` (PWA) y `config.py` (Flet).
  Si tocás una, tocá la otra.

El detalle fino de cada decisión está en `backend/BITACORA.md`. El resumen que
conviene leer primero es el `CLAUDE.md` de la raíz.
