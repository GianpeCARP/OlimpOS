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
from sqlalchemy.orm import Session, selectinload

from auth import generar_password_temporal, generar_username, hashear_password
from database import get_db
from models import (
    AsignacionEntrenador, Baja, ContactoEmergencia, Entrenador, Membresia,
    Persona, Sede, Socio, Telefono, Usuario,
)
from notificaciones import enviar_credenciales
from permisos import Accion, Seccion
from schemas import (
    AsignacionEntrenadorOut, AsignarEntrenadorRequest, BajaRequest, PersonaOut,
    SocioAltaRequest, SocioAltaResponse, SocioEditarRequest, SocioOut,
    TelefonoOut, TelefonoRequest,
)
from routers.rutinas import _entrenador_de_sesion
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


def _listar_socios_en_lote(db: Session, consulta) -> list[SocioOut]:
    """
    Arma la grilla de socios con un numero FIJO de consultas.

    POR QUE NO SE REUSA _a_socio_out EN UN BUCLE
    ============================================
    Porque hace CUATRO consultas por socio: la membresia vigente, el telefono
    principal, `persona.usuario` y `membresia.tipo`. Con 3 socios eran 14
    consultas y 1,4 segundos; con 100 socios serian ~400 y la pantalla tardaria
    medio minuto. Y el costo no es la base: es la RED. Neon esta remoto y cada
    ida y vuelta cuesta ~50ms, asi que lo unico que importa es cuantas veces se
    pregunta, no que tan pesada es cada pregunta.

    Aca se pregunta cinco veces en total, sin importar cuantas filas haya:
    socios, personas (con telefonos y usuario), y membresias (con su tipo).

    `_a_socio_out` se queda para el socio de a UNO —alta, edicion, baja— donde
    cuatro consultas estan bien y el codigo se lee mejor. Los dos caminos
    tienen que dar lo MISMO: si cambia una regla de derivacion (el estado, el
    plan), va en `_estado_socio`, que los dos llaman.
    """
    socios = (consulta
              .options(
                  # Solo relaciones que EXISTEN. Se verificaron con
                  # sqlalchemy.inspect(Socio).relationships: la primera version
                  # de esto invento `Socio.membresias`, el endpoint devolvia 500
                  # y —como Flet traduce el error a una lista vacia— la grilla
                  # se veia "vacia pero funcionando", que es peor que un error.
                  selectinload(Socio.persona).selectinload(Persona.telefonos),
                  selectinload(Socio.persona).selectinload(Persona.usuario),
              )
              .all())
    if not socios:
        return []

    ids = [s.id_socio for s in socios]

    # TODAS las membresias de esos socios en una sola consulta, ya ordenadas
    # igual que en `_membresia_vigente`. Al recorrerlas se queda la PRIMERA de
    # cada socio, que por ese orden es la vigente: mismo criterio, una consulta.
    vigentes: dict[int, Membresia] = {}
    filas = (db.query(Membresia)
             .options(selectinload(Membresia.tipo))
             .filter(Membresia.id_socio.in_(ids))
             .order_by(Membresia.fecha_inicio.desc(),
                       Membresia.id_membresia.desc())
             .all())
    for m in filas:
        vigentes.setdefault(m.id_socio, m)

    salida = []
    for socio in socios:
        persona = socio.persona
        membresia = vigentes.get(socio.id_socio)

        # El principal, o el primero que haya — mismo orden que
        # `_telefono_principal`, pero sobre la lista ya cargada.
        telefonos = sorted(persona.telefonos,
                           key=lambda x: (not bool(x.principal), x.id_telefono))
        telefono = telefonos[0].numero if telefonos else None

        salida.append(SocioOut(
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
            telefono=telefono,
            tiene_cuenta=persona.usuario is not None,
            id_tipo_membresia=membresia.id_tipo_membresia if membresia else None,
            plan=(membresia.tipo.nombre if membresia and membresia.tipo else "Sin plan"),
            estado=_estado_socio(socio, membresia),
            vencimiento=membresia.fecha_vencimiento if membresia else None,
        ))
    return salida


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
    return _listar_socios_en_lote(db, db.query(Socio).order_by(Socio.id_socio.desc()))


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
        )
        db.add(persona)
        # flush y no commit: manda el INSERT para que la base asigne el
        # id_persona, pero deja la transacción abierta. Si algo falla más
        # abajo, se deshace todo junto.
        db.flush()

        # El contacto de emergencia ya no es columna de Persona: si vino en el
        # alta, se crea su fila en Contacto_Emergencia (el principal).
        if datos.emergencia_nombre or datos.emergencia_telefono:
            db.add(ContactoEmergencia(
                id_persona=persona.id_persona,
                nombre=datos.emergencia_nombre or "",
                telefono=datos.emergencia_telefono or "",
                parentesco=datos.emergencia_parentesco,
                principal=True,
            ))
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


# =============================================================================
# TELÉFONOS DE LA FICHA
# =============================================================================
#
# POR QUÉ ENDPOINTS APARTE Y NO UN CAMPO MÁS DEL PUT
# --------------------------------------------------
# `Telefono` es una tabla desde el primer día, justamente porque una persona
# tiene varios números —el celular, el de la casa, el del trabajo—. Pero la API
# la venía tratando como si fuera una columna: el PUT de la ficha manda UN
# `telefono` y el router le pisaba el principal. La tabla estaba bien modelada
# y la ficha no la aprovechaba.
#
# Van separados del PUT porque agregar un número no es editar la ficha: pasa en
# otro momento —el socio dicta un segundo número en el mostrador— y no tiene
# por qué arrastrar nombre, email y objetivo en el mismo pedido, que es como se
# pisan datos sin querer.
#
# El permiso es el MISMO que el de editar la ficha, no uno nuevo: quien puede
# corregirle el nombre a un socio puede cargarle un teléfono.
# =============================================================================


def _socio_o_404(db: Session, id_socio: int) -> Socio:
    socio = db.get(Socio, id_socio)
    if socio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="El socio no existe.")
    return socio


def _telefonos_ordenados(db: Session, id_persona: int) -> list[Telefono]:
    """El principal primero, después por antigüedad. Mismo orden en toda la app."""
    return (db.query(Telefono)
            .filter(Telefono.id_persona == id_persona)
            .order_by(Telefono.principal.desc(), Telefono.id_telefono)
            .all())


def _digitos(numero: str) -> str:
    """
    Sólo los dígitos, para comparar dos números escritos distinto.

    "341 555-1234" y "3415551234" son el mismo teléfono, y sin normalizar la
    ficha terminaba con varias filas que llaman al mismo lado.
    """
    return "".join(c for c in (numero or "") if c.isdigit())


def _telefono_de(db: Session, id_persona: int, id_telefono: int) -> Telefono:
    telefono = db.get(Telefono, id_telefono)
    if telefono is None or telefono.id_persona != id_persona:
        # 404 y no 403 a propósito: que exista un teléfono con ese id pero de
        # otra persona no es información que le corresponda a quien está
        # mirando ESTA ficha.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Ese teléfono no está en la ficha de este socio.")
    return telefono


def _desmarcar_principales(db: Session, id_persona: int) -> None:
    """
    Deja a todos en no-principal. Se llama antes de marcar el nuevo.

    Tener dos principales es lo mismo que no tener ninguno: el listado de
    socios muestra "el primero que aparezca" y pasaría a ser impredecible cuál.
    """
    for t in db.query(Telefono).filter(Telefono.id_persona == id_persona,
                                       Telefono.principal.is_(True)).all():
        t.principal = False


@router.get("/{id_socio}/telefonos", response_model=list[TelefonoOut])
def telefonos_del_socio(
    id_socio: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.SOCIOS)),
):
    socio = _socio_o_404(db, id_socio)
    return [TelefonoOut.model_validate(t)
            for t in _telefonos_ordenados(db, socio.id_persona)]


@router.post("/{id_socio}/telefonos", response_model=TelefonoOut,
             status_code=status.HTTP_201_CREATED)
def agregar_telefono(
    id_socio: int,
    datos: TelefonoRequest,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.ALTA_BAJA_SOCIOS)),
):
    socio = _socio_o_404(db, id_socio)

    existentes = _telefonos_ordenados(db, socio.id_persona)

    # El mismo número dos veces no es un teléfono más: es el mismo.
    if any(_digitos(t.numero) == _digitos(datos.numero) for t in existentes):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Ese número ya está cargado en la ficha.")

    # El primero es principal sí o sí, lo haya pedido o no quien lo carga: una
    # ficha con teléfonos donde ninguno es el principal no muestra ninguno.
    principal = datos.principal or not existentes
    if principal:
        _desmarcar_principales(db, socio.id_persona)

    telefono = Telefono(id_persona=socio.id_persona, numero=datos.numero,
                        tipo=datos.tipo, principal=principal)
    db.add(telefono)
    db.commit()
    db.refresh(telefono)
    return TelefonoOut.model_validate(telefono)


@router.put("/{id_socio}/telefonos/{id_telefono}", response_model=TelefonoOut)
def editar_telefono(
    id_socio: int,
    id_telefono: int,
    datos: TelefonoRequest,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.ALTA_BAJA_SOCIOS)),
):
    socio = _socio_o_404(db, id_socio)
    telefono = _telefono_de(db, socio.id_persona, id_telefono)

    if datos.principal and not telefono.principal:
        _desmarcar_principales(db, socio.id_persona)
        telefono.principal = True
    elif not datos.principal and telefono.principal:
        # Desmarcar el principal a secas dejaría la ficha sin ninguno. Se
        # ignora el pedido: para cambiar cuál es el principal, se marca el
        # OTRO — que es lo que la persona quiere hacer en realidad.
        pass

    telefono.numero = datos.numero
    telefono.tipo = datos.tipo
    db.commit()
    db.refresh(telefono)
    return TelefonoOut.model_validate(telefono)


@router.delete("/{id_socio}/telefonos/{id_telefono}",
               status_code=status.HTTP_204_NO_CONTENT)
def borrar_telefono(
    id_socio: int,
    id_telefono: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.ALTA_BAJA_SOCIOS)),
):
    """
    Saca un número de la ficha.

    Acá se BORRA la fila, a diferencia de la baja de un socio: un teléfono
    equivocado o que ya no existe no es historia que preservar, es un dato
    falso que hace perder llamadas.
    """
    socio = _socio_o_404(db, id_socio)
    telefono = _telefono_de(db, socio.id_persona, id_telefono)
    era_principal = bool(telefono.principal)

    db.delete(telefono)
    db.flush()

    # Si se fue el principal y quedan otros, asciende el más viejo. Sin esto la
    # ficha diría "sin teléfono" teniendo dos cargados.
    if era_principal:
        quedan = _telefonos_ordenados(db, socio.id_persona)
        if quedan:
            quedan[0].principal = True

    db.commit()


# =============================================================================
# ENTRENADOR A CARGO
# =============================================================================
#
# Quién entrena a quién. Vive en Asignacion_Entrenador desde la migración 003,
# que sacó la vieja columna Socio.id_entrenador_a_cargo.
#
# Esa columna cometía el mismo error que Telefono ya evitaba: meter en un
# campo de valor único un hecho que en la realidad es MÚLTIPLE —un socio puede
# tener a la vez uno de musculación y otro de funcional— y CAMBIANTE, porque
# reasignarlo pisaba el valor anterior y el historial se perdía.
#
# La migración se hizo, la tabla quedó, y hasta ahora ningún router la usaba:
# no había forma de asignarle un entrenador a un socio desde ninguna de las
# dos apps. Esto lo cierra.
#
# QUIÉN PUEDE: la acción GESTION_RUTINAS, no ALTA_BAJA_SOCIOS. Asignar un
# entrenador no es un dato administrativo del socio, es una decisión de
# entrenamiento — y con GESTION_RUTINAS la tienen el Dueño, el Recepcionista
# y el propio Entrenador, que es quien toma un cliente nuevo.
#
# PERO un Entrenador sólo decide por SÍ MISMO: puede tomar un socio o
# soltarlo, no ponerle ni sacarle a otro entrenador. Eso es del Dueño y del
# Recepcionista. Es la misma regla que _resolver_entrenador aplica a las
# rutinas ("no a nombre de otro"). Antes no estaba y un entrenador podía
# asignarle a un socio cualquier colega.

def _a_asignacion_out(a: AsignacionEntrenador) -> AsignacionEntrenadorOut:
    entrenador = a.entrenador
    persona = (entrenador.empleado.persona
               if entrenador and entrenador.empleado else None)
    return AsignacionEntrenadorOut(
        id_asignacion=a.id_asignacion_entrenador,
        id_socio=a.id_socio,
        id_entrenador=a.id_entrenador,
        entrenador=persona.nombre_completo if persona else "?",
        especialidad=entrenador.especialidad if entrenador else None,
        fecha_inicio=a.fecha_inicio,
        fecha_fin=a.fecha_fin,
        estado=a.estado,
    )


@router.get("/{id_socio}/entrenadores", response_model=list[AsignacionEntrenadorOut])
def entrenadores_del_socio(
    id_socio: int,
    solo_activos: bool = False,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.SOCIOS)),
):
    """
    Los entrenadores de un socio, con historial.

    Por defecto devuelve TODOS, incluidos los que ya no lo entrenan. Ese
    historial es el motivo por el que existe la tabla: con la columna vieja,
    reasignar borraba al anterior y nadie podía responder "¿quién lo entrenaba
    en marzo?".

    `solo_activos` para cuando lo que se quiere es la foto de hoy.
    """
    if db.get(Socio, id_socio) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="El socio no existe.")

    consulta = (db.query(AsignacionEntrenador)
                .filter(AsignacionEntrenador.id_socio == id_socio))
    if solo_activos:
        consulta = consulta.filter(AsignacionEntrenador.estado == "ACTIVA")

    asignaciones = consulta.order_by(
        AsignacionEntrenador.fecha_inicio.desc(),
        AsignacionEntrenador.id_asignacion_entrenador.desc(),
    ).all()
    return [_a_asignacion_out(a) for a in asignaciones]


@router.post("/{id_socio}/entrenadores", response_model=AsignacionEntrenadorOut,
             status_code=status.HTTP_201_CREATED)
def asignar_entrenador(
    id_socio: int,
    datos: AsignarEntrenadorRequest,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.GESTION_RUTINAS)),
):
    """
    Le pone un entrenador a cargo.

    SE PERMITEN VARIOS A LA VEZ, y es la diferencia deliberada con
    Asignacion_Rutina y Asignacion_Dieta, que admiten una sola activa. Un
    socio con uno de musculación y otro de funcional es normal, no un error
    de datos — está documentado en la migración 003 y el índice único de la
    tabla lo refleja: es por (socio, entrenador, fecha_inicio), no por socio.

    Lo que sí se impide es asignar DOS VECES al mismo entrenador: eso no es
    "dos entrenadores", es la misma relación duplicada, y después nadie sabría
    cuál de las dos filas finalizar.
    """
    socio = db.get(Socio, id_socio)
    if socio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="El socio no existe.")
    if not socio.activo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=("Ese socio está dado de baja. Reactivalo antes de "
                    "asignarle un entrenador."),
        )

    propio = _entrenador_de_sesion(db, sesion)
    if propio is not None and datos.id_entrenador != propio.id_entrenador:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sólo podés asignarte a vos mismo como entrenador.",
        )

    entrenador = db.get(Entrenador, datos.id_entrenador)
    if entrenador is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Ese entrenador no existe.")
    if entrenador.empleado is None or not entrenador.empleado.activo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=("Ese entrenador ya no trabaja en el gimnasio. "
                    "Elegí uno activo."),
        )

    ya = (db.query(AsignacionEntrenador)
          .filter(AsignacionEntrenador.id_socio == id_socio,
                  AsignacionEntrenador.id_entrenador == datos.id_entrenador,
                  AsignacionEntrenador.estado == "ACTIVA")
          .first())
    if ya:
        nombre = (entrenador.empleado.persona.nombre_completo
                  if entrenador.empleado else "Ese entrenador")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{nombre} ya está a cargo de este socio.",
        )

    inicio = datos.fecha_inicio or date.today()

    # VOLVER A TOMAR AL SOCIO EL MISMO DÍA QUE SE LO SOLTÓ.
    #
    # El índice único es (socio, entrenador, fecha_inicio), así que insertar
    # una fila nueva con la misma fecha que una FINALIZADA reventaba con un
    # IntegrityError -> 500. Pasa con sólo apretar dos botones: se finaliza la
    # asignación y se la vuelve a crear en el día, que es exactamente el caso
    # "me equivoqué de botón". Se reactiva la fila que ya existe.
    misma_fecha = (db.query(AsignacionEntrenador)
                   .filter(AsignacionEntrenador.id_socio == id_socio,
                           AsignacionEntrenador.id_entrenador == datos.id_entrenador,
                           AsignacionEntrenador.fecha_inicio == inicio)
                   .first())
    if misma_fecha is not None:
        misma_fecha.estado = "ACTIVA"
        misma_fecha.fecha_fin = None
        db.commit()
        db.refresh(misma_fecha)
        return _a_asignacion_out(misma_fecha)

    asignacion = AsignacionEntrenador(
        id_socio=id_socio,
        id_entrenador=datos.id_entrenador,
        fecha_inicio=inicio,
        estado="ACTIVA",
    )
    db.add(asignacion)
    db.commit()
    db.refresh(asignacion)
    return _a_asignacion_out(asignacion)


@router.post("/entrenadores/asignaciones/{id_asignacion}/finalizar",
             response_model=AsignacionEntrenadorOut)
def finalizar_asignacion(
    id_asignacion: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.GESTION_RUTINAS)),
):
    """
    Termina la relación. NO borra la fila.

    Es el mismo criterio de baja lógica que el resto del sistema: la
    asignación finalizada queda con su fecha_fin y sigue explicando quién
    entrenaba a quién en ese período. Borrarla dejaría un hueco en el
    historial justo donde el historial es el motivo de que la tabla exista.

    La ruta va con el prefijo /entrenadores/asignaciones y no bajo
    /{id_socio}/... a propósito: el id de la asignación ya identifica al socio,
    y pedir los dos permitiría mandar una combinación inconsistente.
    """
    asignacion = db.get(AsignacionEntrenador, id_asignacion)
    if asignacion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Esa asignación no existe.")
    propio = _entrenador_de_sesion(db, sesion)
    if propio is not None and asignacion.id_entrenador != propio.id_entrenador:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sólo podés terminar tus propias asignaciones.",
        )
    if asignacion.estado != "ACTIVA":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Esa asignación ya estaba finalizada.")

    asignacion.estado = "FINALIZADA"
    asignacion.fecha_fin = date.today()
    db.commit()
    db.refresh(asignacion)
    return _a_asignacion_out(asignacion)


@router.get("/entrenadores/{id_entrenador}/socios", response_model=list[SocioOut])
def socios_del_entrenador(
    id_entrenador: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.SOCIOS)),
):
    """
    A quiénes entrena. Es la vista inversa, y es la que usa el entrenador.

    Existe porque la pregunta que se hace un entrenador al llegar no es "¿quién
    entrena a Juan?" sino "¿a quiénes tengo yo?". Resolverla desde el otro
    endpoint obligaría a traerse todos los socios y filtrar en el cliente.
    """
    if db.get(Entrenador, id_entrenador) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Ese entrenador no existe.")

    socios = (db.query(Socio)
              .join(AsignacionEntrenador,
                    AsignacionEntrenador.id_socio == Socio.id_socio)
              .filter(AsignacionEntrenador.id_entrenador == id_entrenador,
                      AsignacionEntrenador.estado == "ACTIVA",
                      Socio.activo.is_(True))
              .all())
    # Mismo camino en lote que /socios: son las dos grillas del sistema.
    return _listar_socios_en_lote(db, db.query(Socio).filter(
        Socio.id_socio.in_([s.id_socio for s in socios])))
