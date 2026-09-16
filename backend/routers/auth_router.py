"""
routers/auth_router.py
----------------------
Los dos únicos endpoints públicos de toda la API: POST /login y
POST /cambiar-password. Todo lo demás exige un token.

Que /cambiar-password sea público no es un descuido: quien tiene que usarlo
todavía NO tiene sesión — el login se la negó justamente porque su contraseña
es temporal. Si exigiera token, la cuenta quedaría en un punto muerto del que
no se puede salir. La compensación es que el endpoint revalida la contraseña
actual antes de aplicar el cambio, así que saber un username no alcanza para
nada.

Reglas de seguridad que vienen de auth.spec.md 3.2 y que ya implementaba el
mock de la PWA (services/authService.ts) — se replican acá porque el mock se
va a borrar y estas reglas tienen que sobrevivir del lado del servidor:

  - Un ÚNICO mensaje de error para usuario inexistente, inactivo, bloqueado o
    contraseña incorrecta. Distinguirlos le confirmaría a un atacante qué
    usuarios existen. Y el mismo TIEMPO: ver _HASH_DE_RELLENO.
  - Cinco intentos fallidos y la cuenta queda trabada 15 minutos, más un tope
    de fallos por IP. Ver limite_intentos.py (V-02/V-03/V-04 de
    docs/vulnerabilidades a arreglar.md).
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

import limite_intentos as limite
from auth import crear_token_acceso, hashear_password, verificar_password
from cookies import borrar_cookies_sesion, setear_cookies_sesion
from csrf import generar_token_csrf
from database import get_db
from models import Socio, Usuario, roles_de_persona
from schemas import (
    CambiarPasswordRequest, LoginRequest, LoginResponse, MensajeResponse,
    PersonaOut, UsuarioOut,
)
from security import Sesion, obtener_sesion

router = APIRouter(tags=["Autenticación"])


# Un solo texto para los cuatro motivos posibles de rechazo. Ver el docstring.
CREDENCIALES_INVALIDAS = "Usuario o contraseña incorrectos"

MAX_INTENTOS_FALLIDOS = 5

# Valor del header X-Client-Type con el que un cliente declara que NO es un
# navegador. Hoy lo manda la app Flet.
CLIENTE_ESCRITORIO = "escritorio"


def _rechazar() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=CREDENCIALES_INVALIDAS,
    )


# V-03: el mensaje era único pero el TIEMPO delataba qué usuarios existen —
# bcrypt (~200 ms) sólo corría si la cuenta existía. Con un usuario inexistente
# se verifica igual contra este hash, así las dos respuestas tardan lo mismo.
_HASH_DE_RELLENO = hashear_password("relleno-para-igualar-tiempos")


def _ip(request: Request) -> str:
    # La del socket y no X-Forwarded-For, que lo escribe el cliente. Ver
    # limite_intentos.py.
    return request.client.host if request.client else "desconocida"


def _frenar_si_excede(ip: str) -> None:
    if limite.ip_excedida(ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos fallidos. Esperá unos minutos y volvé a intentar.",
        )


def _registrar_intento_fallido(db: Session, usuario: Usuario, ip: str) -> None:
    """
    Suma un intento fallido y, al llegar al tope, traba la cuenta 15 minutos.

    Antes la BLOQUEABA para siempre (`bloqueado=true`), y eso era el DoS de
    V-02: cinco contraseñas mal y el único Dueño quedaba afuera hasta que
    alguien tocara la base. Ahora se traba un rato y el contador vuelve a cero.
    `Usuario.bloqueado` queda para el bloqueo que decide una persona.

    El contador se guarda con commit aunque la request termine en 401: si se
    perdiera al hacer rollback, el freno nunca llegaría a dispararse.
    """
    limite.registrar_fallo_ip(ip)
    usuario.intentos_fallidos = (usuario.intentos_fallidos or 0) + 1
    if usuario.intentos_fallidos >= MAX_INTENTOS_FALLIDOS:
        limite.trabar_cuenta(usuario.username)
        usuario.intentos_fallidos = 0
    db.commit()


def _cuenta_no_disponible(usuario: Usuario | None, username: str) -> bool:
    return (usuario is None or not usuario.activo or usuario.bloqueado
            or limite.cuenta_trabada(username))


@router.post("/login", response_model=LoginResponse)
def login(
    datos: LoginRequest,
    respuesta: Response,
    request: Request,
    db: Session = Depends(get_db),
    x_client_type: str | None = Header(default=None),
):
    """
    Inicia sesión.

    Devuelve una de dos formas (ver LoginResponse):
      - `{"debe_cambiar_password": true}` y nada más, si la cuenta todavía
        tiene su contraseña temporal. Se verificó la contraseña, pero NO se
        emite token.
      - La sesión completa, si el ingreso es normal.

    CÓMO VIAJA LA SESIÓN, según quién pregunte (header `X-Client-Type`):

      - Sin ese header (o distinto de "escritorio") se asume NAVEGADOR: la
        sesión se entrega en una cookie httponly y el campo `token` de la
        respuesta viene en null. Es a propósito — si el token también viniera
        en el cuerpo, JavaScript podría leerlo y guardarlo, y toda la ventaja
        de la cookie httponly se perdería. Junto con la sesión va la cookie
        CSRF, que la PWA sí lee.

      - Con `X-Client-Type: escritorio` (la app Flet) el token viaja en el
        cuerpo y no se setea ninguna cookie. Flet no es un navegador: no tiene
        el problema del XSS ni el del CSRF, y guardar el token en memoria le
        alcanza.
    """
    username = datos.username.strip()

    # Se corta antes de tocar la base. Sin esto, un formulario vacío devuelve
    # "usuario o contraseña incorrectos", que confunde: el problema no es que
    # los datos estén mal, es que faltan. No revela nada — todavía no se
    # consultó ningún usuario.
    if not username or not datos.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Completá usuario y contraseña",
        )

    ip = _ip(request)
    _frenar_si_excede(ip)

    usuario = db.query(Usuario).filter(Usuario.username == username).first()

    if _cuenta_no_disponible(usuario, username):
        verificar_password(datos.password, _HASH_DE_RELLENO)  # mismo tiempo (V-03)
        limite.registrar_fallo_ip(ip)
        raise _rechazar()

    if not verificar_password(datos.password, usuario.password_hash):
        _registrar_intento_fallido(db, usuario, ip)
        raise _rechazar()

    # --- Contraseña correcta ------------------------------------------------

    persona = usuario.persona
    if persona is None:
        # No debería pasar: id_persona es NOT NULL y tiene FK. Si pasa, la base
        # está inconsistente y lo seguro es no abrir sesión.
        raise _rechazar()

    # El corte del flujo de contraseña temporal. Va DESPUÉS de validar la
    # contraseña —para no revelar el estado de una cuenta ajena— y ANTES de
    # emitir el token. El contador de intentos se limpia igual: la persona
    # demostró conocer su clave.
    if usuario.debe_cambiar_password:
        usuario.intentos_fallidos = 0
        db.commit()
        return LoginResponse(debe_cambiar_password=True)

    roles = roles_de_persona(persona)
    if not roles:
        # Cuenta sin ningún rol de sesión (por ejemplo, la de un Profesor).
        # Dejarla entrar la llevaría a un sistema donde no puede abrir ni una
        # sección: mejor un rechazo claro que una pantalla vacía.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu cuenta no tiene ningún perfil asignado. Hablá con el gimnasio.",
        )

    socio = db.query(Socio).filter(Socio.id_persona == persona.id_persona).first()
    id_socio = socio.id_socio if socio else None

    # Lo mismo para el profesor: "Mis clases" filtra por este id, así que va
    # firmado en el token y no se resuelve en cada endpoint. Se navega desde
    # la persona porque Profesor cuelga de Empleado, no de Persona.
    empleado = persona.empleado
    id_profesor = (empleado.profesor.id_profesor
                   if empleado is not None and empleado.profesor is not None
                   else None)

    usuario.intentos_fallidos = 0
    usuario.ultimo_acceso = datetime.now(timezone.utc)
    db.commit()
    db.refresh(usuario)

    token = crear_token_acceso(
        id_usuario=usuario.id_usuario,
        username=usuario.username,
        roles=roles,
        id_socio=id_socio,
        id_profesor=id_profesor,
    )

    es_escritorio = (x_client_type or "").strip().lower() == CLIENTE_ESCRITORIO

    if es_escritorio:
        token_en_cuerpo = token
    else:
        setear_cookies_sesion(respuesta, token=token, csrf=generar_token_csrf())
        # None y no el token: que el navegador no pueda leerlo es todo el
        # punto de la cookie httponly.
        token_en_cuerpo = None

    return LoginResponse(
        debe_cambiar_password=False,
        token=token_en_cuerpo,
        usuario=UsuarioOut.model_validate(usuario),
        persona=PersonaOut.model_validate(persona),
        roles=roles,
        idSocio=id_socio,
    )


@router.post("/logout", response_model=MensajeResponse)
def logout(respuesta: Response):
    """
    Cierra la sesión borrando las cookies.

    Hace falta un endpoint —y no alcanza con que el frontend olvide el token—
    porque una cookie httponly no la puede borrar JavaScript. Sin esto, el
    "logout" de la PWA dejaría la cookie viva en el navegador y la sesión
    seguiría abierta para cualquiera que use esa máquina después.

    No exige sesión válida a propósito: si el token ya venció igual hay que
    poder limpiar las cookies. Sí pasa por el middleware CSRF (es un POST con
    cookie), así que nadie puede desloguearte desde otro sitio.

    Nota: el JWT en sí sigue siendo válido hasta que expire — así funcionan
    los tokens sin estado. Para revocar de verdad hay que desactivar la cuenta
    (`Usuario.activo = false`), que obtener_sesion chequea en cada pedido.
    """
    borrar_cookies_sesion(respuesta)
    return MensajeResponse(mensaje="Sesión cerrada.")


@router.get("/me", response_model=LoginResponse)
def sesion_actual(sesion: Sesion = Depends(obtener_sesion)):
    """
    Devuelve la sesión que corresponde al token del header, con la misma forma
    que /login (menos el token, que el cliente ya tiene).

    Existe para que un frontend web pueda sobrevivir a un F5. La PWA guarda el
    token en sessionStorage, pero NO los datos de la sesión: al recargar, la
    página vuelve a arrancar en blanco y le pregunta a la API quién es. Así el
    backend sigue siendo la única fuente de verdad sobre la identidad y los
    roles — si guardáramos eso en el navegador, alguien podría editarlo desde
    las devtools y darse permisos que no tiene.

    Los roles salen del token (firmado), igual que en cualquier otro endpoint.
    Que el token siga siendo válido lo verificó `obtener_sesion`, que además
    relee el Usuario de la base: una cuenta desactivada después de emitido el
    token no puede rehidratar nada.
    """
    persona = sesion.usuario.persona

    return LoginResponse(
        debe_cambiar_password=False,
        token=None,
        usuario=UsuarioOut.model_validate(sesion.usuario),
        persona=PersonaOut.model_validate(persona),
        roles=sesion.roles,
        idSocio=sesion.id_socio,
    )


@router.post("/cambiar-password", response_model=MensajeResponse)
def cambiar_password(datos: CambiarPasswordRequest, request: Request,
                     db: Session = Depends(get_db)):
    """
    Define una contraseña nueva, validando siempre la actual.

    Sirve para los tres casos que comparten el mismo mecanismo: el primer
    ingreso del dueño, el primer ingreso de cualquier cuenta creada por el
    personal, y el reingreso después de que un admin resetee la clave.

    Al terminar, `debe_cambiar_password` queda en false y la persona vuelve a
    la pantalla de login. Tiene que ingresar de nuevo: este endpoint no emite
    token a propósito, para que el primer uso de la contraseña nueva sea un
    login normal y quede probada.
    """
    username = datos.username.strip()
    ip = _ip(request)
    _frenar_si_excede(ip)
    usuario = db.query(Usuario).filter(Usuario.username == username).first()

    # Mismo trato que en el login: no se distingue entre cuenta inexistente y
    # contraseña equivocada, ni por el mensaje ni por el tiempo. Este endpoint
    # es público, así que si respondiera distinto se convertiría en un
    # detector de usuarios válidos.
    if _cuenta_no_disponible(usuario, username):
        verificar_password(datos.password_actual, _HASH_DE_RELLENO)
        limite.registrar_fallo_ip(ip)
        raise _rechazar()

    if not verificar_password(datos.password_actual, usuario.password_hash):
        _registrar_intento_fallido(db, usuario, ip)
        raise _rechazar()

    if verificar_password(datos.password_nueva, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña nueva tiene que ser distinta de la actual.",
        )

    usuario.password_hash = hashear_password(datos.password_nueva)
    usuario.debe_cambiar_password = False
    usuario.intentos_fallidos = 0
    db.commit()

    return MensajeResponse(
        mensaje="Contraseña actualizada. Ya podés iniciar sesión con la nueva."
    )
