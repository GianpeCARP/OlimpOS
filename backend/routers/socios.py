"""
routers/socios.py
-----------------
Alta y consulta de socios.

EL ALTA POR INVITACIÓN
----------------------
Es el flujo que pide la consigna, y su idea central es que el control de quién
entra al sistema lo tiene siempre la administración del gimnasio:

  1. La persona llega al mostrador, paga, y el personal carga sus datos.
  2. El backend crea Persona + Teléfono + Socio y, si corresponde, la cuenta,
     generando una contraseña temporal que nadie eligió.
  3. Esas credenciales se le entregan (dictadas, por mail o por WhatsApp).
  4. En el primer ingreso el sistema la obliga a definir su propia contraseña.

Por eso NO existe un "Registrarse" en ninguna de las dos apps: sólo entra
quien el gimnasio dio de alta. Además evita el trabajo doble — el personal ya
tiene que cargar al socio cuando cobra, y si el socio se registrara por su
cuenta habría que buscar esa cuenta y enlazarla con el pago.

ORDEN DE INSERCIÓN
------------------
No es arbitrario, lo impone el esquema: todo cuelga de Persona.

    Persona  ->  Telefono
             ->  Socio
             ->  Usuario

Y todo ocurre en UNA transacción. Si algo falla a mitad de camino, no queda
una Persona sin ficha ni una ficha sin cuenta.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth import generar_password_temporal, generar_username, hashear_password
from database import get_db
from models import Persona, Sede, Socio, Telefono, Usuario
from notificaciones import enviar_credenciales
from permisos import Accion, Seccion
from schemas import PersonaOut, SocioAltaRequest, SocioAltaResponse, SocioOut
from security import Sesion, requiere_accion, requiere_seccion

router = APIRouter(prefix="/socios", tags=["Socios"])


def _numero_socio(id_socio: int) -> str:
    """
    'S-0001'. Mismo formato que ya usa la PWA (proximoNumeroSocio en
    mockDb.ts) — cambiarlo obligaría a reescribir las pantallas que lo
    muestran y rompería la continuidad con los socios ya cargados.

    Se arma DESPUÉS del insert, a partir del id que asignó la base: calcularlo
    antes (contando socios, por ejemplo) daría números repetidos si dos altas
    ocurren a la vez.
    """
    return f"S-{id_socio:04d}"


def _a_socio_out(socio: Socio) -> SocioOut:
    persona = socio.persona
    return SocioOut(
        id_socio=socio.id_socio,
        id_persona=socio.id_persona,
        id_sede=socio.id_sede,
        numero_socio=socio.numero_socio,
        fecha_alta=socio.fecha_alta,
        objetivo=socio.objetivo,
        activo=bool(socio.activo),
        dni=persona.dni,
        nombre=persona.nombre,
        apellido=persona.apellido,
        email=persona.email,
        tiene_cuenta=persona.usuario is not None,
    )


@router.get("", response_model=list[SocioOut])
def listar_socios(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.SOCIOS)),
):
    """
    Lista los socios. Alcanza con acceso de LECTURA a la sección: un
    Entrenador necesita ver a quién le asigna una rutina.
    """
    socios = db.query(Socio).order_by(Socio.id_socio.desc()).all()
    return [_a_socio_out(s) for s in socios]


@router.post("", response_model=SocioAltaResponse, status_code=status.HTTP_201_CREATED)
def alta_socio(
    datos: SocioAltaRequest,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.ALTA_BAJA_SOCIOS)),
):
    """
    Da de alta un socio y, opcionalmente, su cuenta de acceso.

    Protegido por la ACCIÓN y no sólo por la sección: un Entrenador entra a
    Socios (lectura) pero no puede dar de alta a nadie. Hoy sólo el Dueño y
    el Recepcionista tienen esta acción en la matriz.
    """
    dni = datos.dni.strip()

    # --- Sede ---------------------------------------------------------------
    # Se valida primero porque es la única condición que no depende de los
    # datos de la persona: si la sede no existe, no tiene sentido seguir.
    if db.get(Sede, datos.id_sede) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La sede indicada no existe.",
        )

    # --- 1. Persona ---------------------------------------------------------
    # Si el DNI ya está cargado se REUSA en vez de fallar. Es un caso real:
    # un empleado del gimnasio que se hace socio, o alguien que se dio de baja
    # y vuelve. Duplicar la Persona rompería el UNIQUE del DNI y, peor,
    # partiría en dos el historial de esa persona.
    persona = db.query(Persona).filter(Persona.dni == dni).first()

    if persona is None:
        persona = Persona(
            dni=dni,
            nombre=datos.nombre.strip(),
            apellido=datos.apellido.strip(),
            email=datos.email,
            sexo=datos.sexo,
            fecha_nacimiento=datos.fecha_nacimiento,
            calle=datos.calle,
            numero_calle=datos.numero_calle,
            localidad=datos.localidad,
            emergencia_nombre=datos.emergencia_nombre,
            emergencia_telefono=datos.emergencia_telefono,
            emergencia_parentesco=datos.emergencia_parentesco,
        )
        db.add(persona)
        # flush y no commit: manda el INSERT para que la base asigne el
        # id_persona, pero deja la transacción abierta. Si algo falla más
        # abajo, se deshace todo junto.
        db.flush()
    elif persona.socio is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{persona.nombre_completo} ya está registrado como socio.",
        )

    # El email es UNIQUE en Persona: chequearlo a mano permite un mensaje
    # claro en vez del error de restricción de PostgreSQL.
    if datos.email:
        choca = (
            db.query(Persona)
            .filter(Persona.email == datos.email, Persona.id_persona != persona.id_persona)
            .first()
        )
        if choca:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ese email ya está registrado para otra persona.",
            )

    # --- 2. Teléfono --------------------------------------------------------
    # Tabla aparte y no columna: una persona puede tener celular y fijo. El
    # primero que se carga queda como principal.
    if datos.telefono and datos.telefono.strip():
        db.add(Telefono(
            id_persona=persona.id_persona,
            numero=datos.telefono.strip(),
            tipo="CELULAR",
            principal=True,
        ))

    # --- 3. Socio -----------------------------------------------------------
    socio = Socio(
        id_persona=persona.id_persona,
        id_sede=datos.id_sede,
        fecha_alta=date.today(),
        objetivo=datos.objetivo,
        observaciones=datos.observaciones,
        activo=True,
    )
    db.add(socio)
    db.flush()                       # ahora sí existe id_socio
    socio.numero_socio = _numero_socio(socio.id_socio)

    # --- 4. Cuenta de acceso (opcional) -------------------------------------
    username = None
    password_temporal = None

    if datos.crear_cuenta:
        if persona.usuario is not None:
            # Ya tenía cuenta (era empleado, por ejemplo). No se le crea otra
            # ni se le pisa la contraseña: sigue entrando con la que conoce, y
            # ahora además va a ver las pantallas de socio, porque los roles
            # se derivan de las tablas y acaba de aparecer en Socio.
            username = persona.usuario.username
        else:
            def username_tomado(candidato: str) -> bool:
                return db.query(Usuario).filter(Usuario.username == candidato).first() is not None

            username = generar_username(persona.nombre, persona.apellido, username_tomado)
            password_temporal = generar_password_temporal()

            db.add(Usuario(
                id_persona=persona.id_persona,
                username=username,
                password_hash=hashear_password(password_temporal),
                # El corazón del flujo: la cuenta nace exigiendo el cambio.
                # El primer login verifica esta contraseña pero NO emite token.
                debe_cambiar_password=True,
                activo=True,
            ))

    db.commit()
    db.refresh(socio)
    db.refresh(persona)

    # --- 5. Envío de credenciales -------------------------------------------
    # Va DESPUÉS del commit, nunca antes: si se mandara el mail primero y la
    # transacción fallara, la persona recibiría credenciales de una cuenta que
    # no existe. Y como enviar_credenciales() no lanza nunca, un problema de
    # correo no puede tumbar un alta que ya está guardada.
    envio = None
    if password_temporal:
        envio = enviar_credenciales(
            email_destino=persona.email,
            nombre=persona.nombre,
            username=username,
            password_temporal=password_temporal,
        )

    if password_temporal:
        mensaje = (
            f"Socio dado de alta con usuario '{username}'. "
            f"En el primer ingreso el sistema le va a pedir que cambie la contraseña."
        )
    elif username:
        mensaje = f"Socio dado de alta. Ya tenía cuenta ('{username}'), se conserva."
    else:
        mensaje = "Socio dado de alta, sin cuenta de acceso."

    return SocioAltaResponse(
        id_socio=socio.id_socio,
        numero_socio=socio.numero_socio,
        persona=PersonaOut.model_validate(persona),
        username=username,
        password_temporal=password_temporal,
        mensaje=mensaje,
        email_enviado=bool(envio and envio.enviado),
        detalle_envio=envio.detalle if envio else None,
        texto_credenciales=envio.texto if envio else None,
    )
