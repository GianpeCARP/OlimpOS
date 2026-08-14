"""
notificaciones.py
-----------------
Envío de las credenciales iniciales por email (paso 3 del registro por
invitación: "el sistema le envía automáticamente un mensaje al cliente").

REGLA DE ORO DE ESTE MÓDULO: NUNCA ROMPE EL ALTA
------------------------------------------------
Cuando el personal termina de dar de alta a un socio, la persona ya está
creada en la base y las credenciales ya existen. Si en ese momento fallara el
envío del mail y esa falla se propagara como error, el frontend mostraría "no
se pudo dar de alta" cuando en realidad SÍ se dio de alta — y el operador
volvería a intentar, chocando con un 409 de DNI duplicado y sin entender nada.

Por eso todas las funciones de acá devuelven un resultado y jamás lanzan. El
peor caso es "no se envió, dictáselas vos", que es exactamente lo que se hacía
antes de que existiera el mail.

SI NO HAY SMTP CONFIGURADO
--------------------------
El módulo no se rompe ni se queja: informa que no está configurado y devuelve
el texto del mensaje ya armado, para que el personal lo copie y lo mande por
WhatsApp. Eso hace que el sistema sea usable desde el día uno, sin depender de
tener un servidor de correo andando.
"""

import os
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USUARIO = os.getenv("SMTP_USUARIO", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_DESDE = os.getenv("SMTP_DESDE", "").strip() or SMTP_USUARIO
SMTP_TIMEOUT = int(os.getenv("SMTP_TIMEOUT", "10"))

NOMBRE_GIMNASIO = os.getenv("NOMBRE_GIMNASIO", "OlimpOS")


@dataclass
class ResultadoEnvio:
    """
    Qué pasó con el mensaje.

    `texto` viene SIEMPRE, se haya enviado o no. Es lo que permite que el
    frontend muestre "copiá esto y mandáselo por WhatsApp" cuando el mail no
    salió, en vez de dejar al operador sin nada.
    """
    enviado: bool
    detalle: str
    texto: str


def smtp_configurado() -> bool:
    return bool(SMTP_HOST and SMTP_DESDE)


def _armar_texto(nombre: str, username: str, password_temporal: str) -> str:
    """
    El mensaje que recibe la persona. Sirve igual para mail o para pegar en un
    WhatsApp, por eso es texto plano sin formato.

    Dice explícitamente que la contraseña es de un solo uso: si no se aclara,
    la gente la anota y la usa como definitiva, que es justo lo que el flujo
    de cambio obligatorio quiere evitar.
    """
    return (
        f"¡Hola {nombre}! Te damos la bienvenida a {NOMBRE_GIMNASIO}.\n"
        f"\n"
        f"Ya podés entrar al sistema con estos datos:\n"
        f"\n"
        f"    Usuario:    {username}\n"
        f"    Contraseña: {password_temporal}\n"
        f"\n"
        f"Esa contraseña es provisoria y de un solo uso: la primera vez que "
        f"entres, el sistema te va a pedir que definas una propia.\n"
        f"\n"
        f"No compartas estos datos con nadie.\n"
    )


def enviar_credenciales(
    email_destino: str | None,
    nombre: str,
    username: str,
    password_temporal: str,
) -> ResultadoEnvio:
    """
    Manda las credenciales por mail. Nunca lanza — ver el docstring del módulo.
    """
    texto = _armar_texto(nombre, username, password_temporal)

    if not email_destino:
        return ResultadoEnvio(
            enviado=False,
            detalle="La persona no tiene email cargado. Entregale las credenciales a mano.",
            texto=texto,
        )

    if not smtp_configurado():
        return ResultadoEnvio(
            enviado=False,
            detalle=(
                "No hay servidor de correo configurado (falta SMTP_HOST en el .env). "
                "Copiá el mensaje y mandáselo por WhatsApp."
            ),
            texto=texto,
        )

    mensaje = EmailMessage()
    mensaje["Subject"] = f"Tus credenciales de {NOMBRE_GIMNASIO}"
    mensaje["From"] = SMTP_DESDE
    mensaje["To"] = email_destino
    mensaje.set_content(texto)

    try:
        # STARTTLS: se abre en claro y se cifra antes de mandar nada. Es lo que
        # esperan Gmail, Outlook y la mayoría en el puerto 587. El 465 en
        # cambio arranca cifrado de entrada (SMTP_SSL), por eso se distingue.
        if SMTP_PORT == 465:
            contexto = ssl.create_default_context()
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT,
                                   context=contexto) as servidor:
                if SMTP_USUARIO:
                    servidor.login(SMTP_USUARIO, SMTP_PASSWORD)
                servidor.send_message(mensaje)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT) as servidor:
                servidor.starttls(context=ssl.create_default_context())
                if SMTP_USUARIO:
                    servidor.login(SMTP_USUARIO, SMTP_PASSWORD)
                servidor.send_message(mensaje)

    except smtplib.SMTPAuthenticationError:
        return ResultadoEnvio(
            enviado=False,
            detalle=("El servidor de correo rechazó las credenciales SMTP. "
                     "Revisá SMTP_USUARIO y SMTP_PASSWORD en el .env."),
            texto=texto,
        )
    except (smtplib.SMTPException, OSError) as e:
        # OSError cubre lo que no es SMTP: host inalcanzable, DNS que no
        # resuelve, timeout. Un except amplio es correcto acá justamente
        # porque la política del módulo es no romper el alta pase lo que pase.
        return ResultadoEnvio(
            enviado=False,
            detalle=f"No se pudo enviar el mail ({type(e).__name__}). Entregalas a mano.",
            texto=texto,
        )

    return ResultadoEnvio(
        enviado=True,
        detalle=f"Credenciales enviadas por mail a {email_destino}.",
        texto=texto,
    )


def _enviar(email_destino: str | None, asunto: str, texto: str) -> ResultadoEnvio:
    """
    El envío en crudo, sin armar el cuerpo. Nunca lanza.

    Se extrajo de enviar_credenciales cuando apareció el segundo tipo de
    aviso: el cuerpo cambia según el caso, pero abrir el SMTP, elegir entre
    STARTTLS y SSL y tragarse los errores es siempre igual.
    """
    if not email_destino:
        return ResultadoEnvio(False, "La persona no tiene email cargado.", texto)
    if not smtp_configurado():
        return ResultadoEnvio(
            False,
            "No hay servidor de correo configurado (falta SMTP_HOST en el .env).",
            texto,
        )

    mensaje = EmailMessage()
    mensaje["Subject"] = asunto
    mensaje["From"] = SMTP_DESDE
    mensaje["To"] = email_destino
    mensaje.set_content(texto)

    try:
        if SMTP_PORT == 465:
            contexto = ssl.create_default_context()
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT,
                                   context=contexto) as servidor:
                if SMTP_USUARIO:
                    servidor.login(SMTP_USUARIO, SMTP_PASSWORD)
                servidor.send_message(mensaje)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT) as servidor:
                servidor.starttls(context=ssl.create_default_context())
                if SMTP_USUARIO:
                    servidor.login(SMTP_USUARIO, SMTP_PASSWORD)
                servidor.send_message(mensaje)
    except Exception as e:  # noqa: BLE001
        # Se traga TODO a propósito: ver el docstring del módulo. Que no salga
        # un mail no puede tumbar la operación que lo disparó.
        return ResultadoEnvio(False, f"No se pudo enviar el mail: {e}", texto)

    return ResultadoEnvio(True, f"Mensaje enviado a {email_destino}.", texto)


def notificar_promocion_lista_espera(reserva, turno, actividad) -> ResultadoEnvio:
    """
    Le avisa a quien estaba en lista de espera que le quedó lugar.

    Es la mitad del valor de la lista de espera: un lugar que se libera y
    nadie sabe es un lugar que sigue vacío. Sin este aviso, el socio tendría
    que estar mirando la app por las dudas — justo lo que la lista de espera
    venía a evitar.

    Como todo en este módulo, nunca lanza: si el mail no sale, la promoción ya
    quedó hecha igual y el texto vuelve para poder mandarlo por WhatsApp.
    """
    persona = reserva.socio.persona
    texto = (
        f"Hola {persona.nombre},\n\n"
        f"Se liberó un lugar en {actividad.nombre} del "
        f"{turno.fecha.strftime('%d/%m/%Y')} a las {turno.hora.strftime('%H:%M')}, "
        f"y como estabas en lista de espera, tu lugar ya está confirmado.\n\n"
        f"No hace falta que hagas nada. Si no vas a poder ir, cancelá desde la "
        f"app así el lugar queda para otra persona.\n\n"
        f"Nos vemos,\n{NOMBRE_GIMNASIO}"
    )
    return _enviar(persona.email, f"Te quedó lugar en {actividad.nombre}", texto)
