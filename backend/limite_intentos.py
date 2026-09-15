"""
limite_intentos.py
------------------
Freno contra fuerza bruta y contra el DoS por bloqueo de cuentas (V-02/V-04 de
docs/vulnerabilidades a arreglar.md).

Dos mecanismos, en memoria del proceso:

1. POR IP: demasiados intentos fallidos desde la misma conexión en una ventana
   corta → 429. Frena al que prueba contraseñas en ráfaga, contra una cuenta o
   contra muchas.

2. POR CUENTA: al llegar al tope de fallos, la cuenta queda TRABADA un rato, no
   bloqueada para siempre. Antes el quinto fallo ponía `Usuario.bloqueado=true`
   y desbloquear exigía que otro con permiso lo hiciera (o entrar a Postgres si
   el bloqueado era el único Dueño): un atacante dejaba al gimnasio sin acceso
   administrativo con ~40 pedidos. Ahora lo peor que logra es demorar 15 minutos,
   y el freno por IP le impide sostenerlo.

   `Usuario.bloqueado` sigue existiendo y se respeta: es el bloqueo DECIDIDO por
   una persona (desde Usuarios), no el automático.

POR QUÉ EN MEMORIA Y NO EN LA BASE: no hace falta que sobreviva a un reinicio
(un reinicio que destraba cuentas no le sirve a un atacante) y así no suma una
columna ni una consulta en cada login. Si algún día hay varios procesos detrás
de un balanceador, esto pasa a un almacén compartido (Redis).

LA IP es la del socket (`request.client.host`), no X-Forwarded-For: ese header
lo escribe el cliente y cualquiera lo falsifica para esquivar el freno. Detrás
de un proxy propio (nginx, el de Vite en desarrollo) todo llega desde la misma
IP; por eso el tope por IP es holgado y el que protege cada cuenta es el 2.
"""

import threading
import time

VENTANA_IP_SEG = 10 * 60
MAX_FALLOS_POR_IP = 20
BLOQUEO_CUENTA_SEG = 15 * 60

_candado = threading.Lock()
_fallos_por_ip: dict[str, list[float]] = {}
_trabada_hasta: dict[str, float] = {}


def ip_excedida(ip: str) -> bool:
    """¿Esta IP ya gastó su cupo de fallos en la ventana?"""
    ahora = time.monotonic()
    with _candado:
        recientes = [t for t in _fallos_por_ip.get(ip, []) if ahora - t < VENTANA_IP_SEG]
        if recientes:
            _fallos_por_ip[ip] = recientes
        else:
            _fallos_por_ip.pop(ip, None)
        return len(recientes) >= MAX_FALLOS_POR_IP


def registrar_fallo_ip(ip: str) -> None:
    with _candado:
        _fallos_por_ip.setdefault(ip, []).append(time.monotonic())


def trabar_cuenta(username: str) -> None:
    with _candado:
        _trabada_hasta[username] = time.monotonic() + BLOQUEO_CUENTA_SEG


def cuenta_trabada(username: str) -> bool:
    ahora = time.monotonic()
    with _candado:
        hasta = _trabada_hasta.get(username)
        if hasta is None:
            return False
        if ahora >= hasta:
            _trabada_hasta.pop(username, None)
            return False
        return True


def destrabar(username: str) -> None:
    """Lo usa el desbloqueo manual desde Usuarios."""
    with _candado:
        _trabada_hasta.pop(username, None)
