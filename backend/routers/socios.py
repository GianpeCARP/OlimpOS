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
from models import Baja, Membresia, Persona, Sede, Socio, Telefono, Usuario
from notificaciones import enviar_credenciales
from permisos import Accion, Seccion
from schemas import (
    BajaRequest, PersonaOut, SocioAltaRequest, SocioAltaResponse,
    SocioEditarRequest, SocioOut,
)
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


# Días antes del vencimiento en que un socio pasa a "Por vencer". Mismo valor
# que DIAS_AVISO_VENCIMIENTO en la PWA (membresiaService.ts) y en el dashboard.
DIAS_AVISO_VENCIMIENTO = 7

# Los seis estados posibles. Espejo de `EstadoSocio` en config.ts — los valores
# viajan en castellano porque son literalmente el texto de la píldora.
ESTADO_ACTIVO = "Activo"
ESTADO_POR_VENCER = "Por vencer"
ESTADO_VENCIDO = "Vencido"
ESTADO_SUSPENDIDO = "Suspendido"
ESTADO_SIN_MEMBRESIA = "Sin membresía"
ESTADO_DE_BAJA = "Dado de baja"


def _membresia_vigente(db: Session, id_socio: int) -> Membresia | None:
    """La membresía más reciente del socio, cualquiera sea su estado."""
    return (
        db.query(Membresia)
        .filter(Membresia.id_socio == id_socio)
        .order_by(Membresia.fecha_inicio.desc(), Membresia.id_membresia.desc())
        .first()
    )


def _estado_socio(socio: Socio, membresia: Membresia | None) -> str:
    """
    Deriva el estado que muestra la tabla.

    Es el port exacto de `estadoDeSocio` en membresiaService.ts. Vive en el
    backend y no en cada frontend porque si no habría que mantener la misma
    regla en tres lugares — y el día que se cambien los 7 días de aviso, en
    dos de los tres se olvidaría.

    El orden de los chequeos importa: "dado de baja" gana sobre cualquier
    estado de membresía. Alguien de baja con la cuota paga sigue estando de
    baja.
    """
    if not socio.activo:
        return ESTADO_DE_BAJA
    if membresia is None:
        return ESTADO_SIN_MEMBRESIA
    if membresia.estado == "SUSPENDIDA":
        return ESTADO_SUSPENDIDO
    if membresia.estado in ("VENCIDA", "CANCELADA"):
        return ESTADO_VENCIDO

    # ACTIVA: sin fecha de vencimiento cubre siempre, así que no puede estar
    # "por vencer" — no hay fecha contra la cual calcularlo.
    if membresia.fecha_vencimiento is None:
        return ESTADO_ACTIVO

    dias = (membresia.fecha_vencimiento - date.today()).days
    if dias < 0:
        return ESTADO_VENCIDO
    if dias <= DIAS_AVISO_VENCIMIENTO:
        return ESTADO_POR_VENCER
    return ESTADO_ACTIVO


def _telefono_principal(db: Session, id_persona: int) -> str | None:
    """El marcado como principal, o el primero que haya."""
    telefono = (
        db.query(Telefono)
        .filter(Telefono.id_persona == id_persona)
        .order_by(Telefono.principal.desc(), Telefono.id_telefono)
        .first()
    )
    return telefono.numero if telefono else None


def _a_socio_out(db: Session, socio: Socio) -> SocioOut:
    persona = socio.persona
    membresia = _membresia_vigente(db, socio.id_socio)

    return SocioOut(
        id_socio=socio.id_socio,
        id_persona=socio.id_persona,
        id_sede=socio.id_sede,
        numero_socio=socio.numero_socio,
        fecha_alta=socio.fecha_alta,
        objetivo=socio.objetivo,
        observaciones=socio.observaciones,
        activo=bool(socio.activo),
        dni=persona.dni,
        nombre=persona.nombre,
        apellido=persona.apellido,
        email=persona.email,
        telefono=_telefono_principal(db, persona.id_persona),
        tiene_cuenta=persona.usuario is not None,
        id_tipo_membresia=membresia.id_tipo_membresia if membresia else None,
        plan=(membresia.tipo.nombre if membresia and membresia.tipo else "Sin plan"),
        estado=_estado_socio(socio, membresia),
        vencimiento=membresia.fecha_vencimiento if membresia else None,
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
    return [_a_socio_out(db, s) for s in socios]


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


# =============================================================================
# EDICIÓN Y BAJA
# =============================================================================

@router.get("/{id_socio}", response_model=SocioOut)
def obtener_socio(
    id_socio: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.SOCIOS)),
):
    socio = db.get(Socio, id_socio)
    if socio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El socio no existe.")
    return _a_socio_out(db, socio)


@router.put("/{id_socio}", response_model=SocioOut)
def editar_socio(
    id_socio: int,
    datos: SocioEditarRequest,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.ALTA_BAJA_SOCIOS)),
):
    """
    Edita los datos de un socio.

    Toca DOS tablas: nombre, apellido y email viven en Persona; objetivo y
    observaciones en Socio. Que el formulario sea uno solo y las tablas dos es
    exactamente el punto de la separación — los datos personales no se
    duplican por cada función que la persona cumple.

    El DNI no se puede cambiar: sería decir que es otra persona.
    """
    socio = db.get(Socio, id_socio)
    if socio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El socio no existe.")

    persona = socio.persona

    if datos.email and datos.email != persona.email:
        choca = (db.query(Persona)
                 .filter(Persona.email == datos.email,
                         Persona.id_persona != persona.id_persona)
                 .first())
        if choca:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Ese email ya está registrado para otra persona.")

    persona.nombre = datos.nombre.strip()
    persona.apellido = datos.apellido.strip()
    persona.email = datos.email
    socio.objetivo = datos.objetivo
    socio.observaciones = datos.observaciones

    # El teléfono vive en su propia tabla: se actualiza el principal o se crea
    # uno si la persona no tenía ninguno cargado.
    if datos.telefono is not None:
        numero = datos.telefono.strip()
        principal = (db.query(Telefono)
                     .filter(Telefono.id_persona == persona.id_persona)
                     .order_by(Telefono.principal.desc(), Telefono.id_telefono)
                     .first())
        if numero:
            if principal:
                principal.numero = numero
            else:
                db.add(Telefono(id_persona=persona.id_persona, numero=numero,
                                tipo="CELULAR", principal=True))
        elif principal:
            db.delete(principal)

    db.commit()
    db.refresh(socio)
    return _a_socio_out(db, socio)


@router.post("/{id_socio}/baja", response_model=SocioOut)
def dar_de_baja(
    id_socio: int,
    datos: BajaRequest,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.ALTA_BAJA_SOCIOS)),
):
    """
    Da de baja a un socio. Baja LÓGICA: la fila no se borra.

    Borrarla arrastraría con ella su historial de pagos, asistencias y
    rutinas — y esos datos siguen siendo del gimnasio aunque la persona se
    haya ido. Además impediría reactivarla si vuelve.

    Se registra en la tabla Baja con su motivo, y se cancela la membresía
    vigente: dejarla activa haría que un socio de baja siguiera figurando al
    día en los listados de cobros.

    La cuenta de acceso también se desactiva. Es lo que cierra el agujero que
    encontró la auditoría del 2026-08-03: un socio dado de baja seguía
    pudiendo entrar a la app.
    """
    socio = db.get(Socio, id_socio)
    if socio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El socio no existe.")
    if not socio.activo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"{socio.persona.nombre_completo} ya estaba dado de baja.")

    hoy = date.today()
    socio.activo = False

    db.add(Baja(
        id_socio=socio.id_socio,
        fecha_baja=hoy,
        tipo=datos.tipo.value,
        motivo=datos.motivo,
    ))

    membresia = _membresia_vigente(db, socio.id_socio)
    if membresia and membresia.estado == "ACTIVA":
        membresia.estado = "CANCELADA"

    if socio.persona.usuario is not None:
        socio.persona.usuario.activo = False

    db.commit()
    db.refresh(socio)
    return _a_socio_out(db, socio)


@router.post("/{id_socio}/reactivar", response_model=SocioOut)
def reactivar(
    id_socio: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.ALTA_BAJA_SOCIOS)),
):
    """
    Reactiva a un socio que había vuelto.

    NO se le devuelve la membresía: vuelve como "Sin membresía" y hay que
    cobrarle de nuevo. Reactivar la vieja le regalaría los días que pasaron
    mientras estuvo de baja.

    El historial de Baja se conserva: es el registro de que se fue y volvió.
    """
    socio = db.get(Socio, id_socio)
    if socio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El socio no existe.")
    if socio.activo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"{socio.persona.nombre_completo} ya estaba activo.")

    socio.activo = True
    if socio.persona.usuario is not None:
        socio.persona.usuario.activo = True

    db.commit()
    db.refresh(socio)
    return _a_socio_out(db, socio)
