"""
routers/usuarios.py
-------------------
Gestión de las cuentas de acceso: crearlas para gente ya cargada, resetear
contraseñas, desbloquear tras los intentos fallidos y activar/desactivar.

DOS REGLAS DE FILA, Y POR QUÉ NO ALCANZA LA MATRIZ DE PERMISOS
--------------------------------------------------------------
La matriz de permisos.py decide cosas del tipo "¿este rol entra a la sección
Usuarios?" o "¿puede gestionar usuarios?". Pero acá hacen falta dos reglas que
la matriz no puede expresar, porque no dependen del rol de quien pide sino de
QUÉ FILA está tocando:

1. NADIE fuera del Dueño puede editar SU PROPIA cuenta, y NADIE —tampoco el
   Dueño— puede desactivarla ni borrarla. Editarse sin que nadie lo vea venir
   es el riesgo de un rol inferior; el Dueño queda exento por ser la autoridad
   última. Desactivarse o borrarse deja afuera a cualquiera, y a un Dueño
   único, al sistema sin salida (ver alternar_estado y borrar_cuenta).

   Resetearse la contraseña propia SÍ está permitido: no hay riesgo en eso, y
   es lo que deja hacer cualquier sistema real.

2. SOLO UN DUEÑO PUEDE OPERAR SOBRE LA CUENTA DE UN DUEÑO.
   Esta es la importante. El Recepcionista tiene `gestionUsuarios` en true, y
   sin noción de jerarquía podía tocar la fila del Dueño. El peor botón no es
   "desactivar" —que ya sería dejar al dueño afuera de su gimnasio— sino
   "resetear contraseña": genera una clave temporal y se la MUESTRA a quien
   apretó el botón. Cualquier recepcionista podía reseteársela al Dueño, leer
   la clave nueva y entrar con control total. Escalación de privilegios
   completa, con tres clicks y sin herramientas.

   Por eso acá el reseteo SÍ entra en la restricción, al revés que en la
   regla 1.

Las dos están escritas también en el frontend (esCuentaPropiaRestringida y
esCuentaDeMayorJerarquia en config.ts), pero ahí solo esconden botones. El
comentario de config.ts lo dice con todas las letras: "el backend tiene que
rechazar la misma operación cuando exista". Este archivo es esa promesa
cumplida.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from auth import generar_password_temporal, generar_username, hashear_password
from database import get_db
from models import Asistencia, Empleado, Persona, Rol, Usuario, roles_de_persona
from notificaciones import enviar_credenciales
from permisos import Accion, Seccion
from schemas import (
    CredencialesResponse, MensajeResponse, PersonaSinCuentaOut, UsuarioAdminOut,
    UsuarioCrearRequest, UsuarioEditarRequest,
)
from security import Sesion, requiere_accion, requiere_seccion

router = APIRouter(prefix="/usuarios", tags=["Usuarios del sistema"])


# =============================================================================
# HELPERS
# =============================================================================

# =============================================================================
# CARGA ANTICIPADA DE LOS ROLES
# =============================================================================
#
# `roles_de_persona()` deriva los roles leyendo SEIS relaciones de la Persona
# (dueno, socio, empleado, y de empleado sus tres subtipos). Con carga perezosa
# eso es una consulta por relacion POR FILA: el listado de 8 cuentas hacia 45
# consultas a Neon y tardaba 2,1 segundos. Con 100 socios serian 600.
#
# Medido, no estimado: 8 cuentas -> 45 consultas -> 2,88s. Cada viaje a Neon
# cuesta ~40ms de red, asi que el problema no es la base, es la cantidad de
# idas y vueltas.
#
# `selectinload` las trae en un puñado de consultas extra con `IN (...)`, sin
# importar cuantas filas haya. Se elige sobre `joinedload` porque son
# relaciones uno-a-uno en cadena y el JOIN multiple duplicaria filas.
#
# OJO: esto hay que repetirlo en CADA listado que llame a roles_de_persona.
# Hoy son tres: /usuarios, /socios y /personal.
CARGA_DE_ROLES = (
    selectinload(Persona.dueno),
    selectinload(Persona.socio),
    selectinload(Persona.empleado).selectinload(Empleado.entrenador),
    selectinload(Persona.empleado).selectinload(Empleado.nutricionista),
    selectinload(Persona.empleado).selectinload(Empleado.recepcionista),
    selectinload(Persona.empleado).selectinload(Empleado.profesor),
    # Los teléfonos entran acá por el mismo motivo que todo lo de arriba: el
    # panel necesita uno para ofrecer "mandar las credenciales por WhatsApp",
    # y sin esta línea sería una consulta MÁS por cada fila de la tabla.
    selectinload(Persona.telefonos),
)


def _a_usuario_out(usuario: Usuario) -> UsuarioAdminOut:
    # "Bloqueado" en pantalla cubre los dos casos: el bloqueo manual (columna)
    # y la traba temporal por intentos fallidos (limite_intentos.py). Si la
    # traba no se viera, nadie sabría que hay algo que desbloquear.
    import limite_intentos
    persona = usuario.persona
    bloqueado = bool(usuario.bloqueado) or limite_intentos.cuenta_trabada(usuario.username)
    return UsuarioAdminOut(
        id_usuario=usuario.id_usuario,
        id_persona=usuario.id_persona,
        username=usuario.username,
        dni=persona.dni,
        nombre_completo=persona.nombre_completo,
        email=persona.email,
        telefono=_telefono_principal(persona),
        roles=roles_de_persona(persona),
        activo=bool(usuario.activo),
        bloqueado=bloqueado,
        debe_cambiar_password=bool(usuario.debe_cambiar_password),
        ultimo_acceso=usuario.ultimo_acceso,
    )


def _telefono_principal(persona: Persona) -> str | None:
    """
    El principal, o el primero que haya. Lo usa el panel para ofrecer mandar
    las credenciales por WhatsApp cuando la persona no dejó mail.
    """
    return next((t.numero for t in persona.telefonos if t.principal),
                next((t.numero for t in persona.telefonos), None))


def _empleado_dado_de_baja(persona: Persona | None) -> bool:
    """
    ¿Esta persona fue empleada y está dada de baja?

    `roles_de_persona` mira que EXISTA la fila del subtipo, no que el empleado
    siga activo: un entrenador dado de baja sigue devolviendo "entrenador".
    Por eso cada camino de este router que da acceso tiene que preguntarlo
    aparte. Sin esto, crear una cuenta NUEVA le devolvía la entrada —con los
    permisos de su rol— a alguien que ya no trabaja acá: el mismo agujero de
    offboarding que alternar_estado cierra para la cuenta vieja.

    El acceso de un empleado se justifica en el puesto (la baja de personal
    apaga la cuenta siempre), así que la vuelta se da desde Personal.
    """
    return (persona is not None and persona.empleado is not None
            and not persona.empleado.activo)


def _rechazar_empleado_dado_de_baja(persona: Persona) -> None:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=(
            f"{persona.nombre_completo} está dado de baja como empleado. "
            "Reactivalo desde Personal: ahí se le devuelve el acceso junto "
            "con el puesto."
        ),
    )


def _buscar_usuario(db: Session, id_usuario: int) -> Usuario:
    usuario = db.get(Usuario, id_usuario)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La cuenta indicada no existe.",
        )
    return usuario


def _validar_jerarquia(sesion: Sesion, objetivo: Usuario) -> None:
    """
    Regla 2: solo un Dueño opera sobre la cuenta de un Dueño.

    Se aplica a TODAS las operaciones de este router, incluido el reseteo de
    contraseña, porque el reseteo es justamente el vector de escalación.
    """
    if Rol.DUENO in sesion.roles:
        return  # un Dueño puede con todo

    if Rol.DUENO in roles_de_persona(objetivo.persona):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un dueño puede operar sobre la cuenta de un dueño.",
        )


def _validar_no_es_propia(sesion: Sesion, objetivo: Usuario) -> None:
    """
    Regla 1: nadie fuera del Dueño se edita ni se desactiva a sí mismo.

    NO se llama desde el reseteo de contraseña — ver el docstring del módulo.
    """
    if Rol.DUENO in sesion.roles:
        return

    if objetivo.id_usuario == sesion.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No podés modificar el estado de tu propia cuenta.",
        )


# =============================================================================
# CONSULTA
# =============================================================================

@router.get("", response_model=list[UsuarioAdminOut])
def listar_usuarios(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.USUARIOS)),
):
    """
    Lista todas las cuentas del sistema, con su estado y sus roles.

    La carga anticipada no es una optimizacion prematura: sin ella este
    endpoint hacia 45 consultas para 8 cuentas (ver CARGA_DE_ROLES arriba).
    """
    usuarios = (db.query(Usuario)
                .options(selectinload(Usuario.persona).options(*CARGA_DE_ROLES))
                .order_by(Usuario.id_usuario)
                .all())
    return [_a_usuario_out(u) for u in usuarios]


@router.get("/personas-sin-cuenta", response_model=list[PersonaSinCuentaOut])
def listar_personas_sin_cuenta(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.USUARIOS)),
):
    """
    Personas que podrían tener cuenta pero todavía no la tienen.

    Filtra por rol y no solo por "no tiene Usuario": alguien sin ningún rol de
    sesión no puede usar el sistema aunque se le creara la cuenta, porque el
    login rechaza a quien no tiene roles. Ofrecerlo como candidato sería
    ofrecer crear una cuenta inútil. Y deja afuera al empleado dado de baja,
    que crear_cuenta rechaza: ofrecerlo sería ofrecer lo que después falla.

    Va ANTES de la ruta /{id_usuario} a propósito: FastAPI resuelve las rutas
    en el orden en que se declaran, y si estuviera después intentaría leer
    "personas-sin-cuenta" como si fuera un id y respondería un error de
    validación.
    """
    personas = (db.query(Persona)
                .options(*CARGA_DE_ROLES)
                .filter(Persona.usuario == None)  # noqa: E711
                .all())

    salida = []
    for p in personas:
        roles = roles_de_persona(p)
        if not roles or _empleado_dado_de_baja(p):
            continue
        salida.append(PersonaSinCuentaOut(
            id_persona=p.id_persona,
            dni=p.dni,
            nombre_completo=p.nombre_completo,
            email=p.email,
            # Para ofrecer las credenciales por WhatsApp apenas se crea la
            # cuenta, igual que el alta de socio y de personal.
            telefono=_telefono_principal(p),
            roles=roles,
        ))
    return salida


# =============================================================================
# ALTA DE CUENTA
# =============================================================================

@router.post("", response_model=CredencialesResponse, status_code=status.HTTP_201_CREATED)
def crear_cuenta(
    datos: UsuarioCrearRequest,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.GESTION_USUARIOS)),
):
    """
    Crea la cuenta de acceso de una Persona que ya está cargada.

    Es el mismo mecanismo que usa el alta de socio, pero para el caso en que
    la persona ya existe: un empleado cargado hace meses al que recién ahora
    se le da acceso, o alguien a quien se le borró la cuenta.

    NO recibe contraseña: la genera el sistema y la cuenta nace con
    debe_cambiar_password. Que un administrador elija la contraseña de otro
    sería peor — la conocería para siempre.
    """
    persona = db.get(Persona, datos.id_persona)
    if persona is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe una persona con ese id.",
        )

    if persona.usuario is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{persona.nombre_completo} ya tiene una cuenta ('{persona.usuario.username}').",
        )

    if _empleado_dado_de_baja(persona):
        _rechazar_empleado_dado_de_baja(persona)

    roles = roles_de_persona(persona)
    if not roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"{persona.nombre_completo} no tiene ningún perfil que habilite el "
                "acceso (no es socio, ni dueño, ni empleado con rol de sesión). "
                "La cuenta no podría entrar a ninguna sección."
            ),
        )

    # Crear la cuenta de un Dueño es, de hecho, crear un administrador. Solo
    # otro Dueño puede hacerlo — misma lógica que la regla 2.
    if Rol.DUENO in roles and Rol.DUENO not in sesion.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un dueño puede crear la cuenta de otro dueño.",
        )

    def username_tomado(candidato: str) -> bool:
        return db.query(Usuario).filter(Usuario.username == candidato).first() is not None

    username = generar_username(persona.nombre, persona.apellido, username_tomado)
    password_temporal = generar_password_temporal()

    db.add(Usuario(
        id_persona=persona.id_persona,
        username=username,
        password_hash=hashear_password(password_temporal),
        debe_cambiar_password=True,
        activo=True,
    ))
    db.commit()

    # Después del commit: si el mail fallara antes, la persona recibiría
    # credenciales de una cuenta que no llegó a existir.
    envio = enviar_credenciales(persona.email, persona.nombre, username, password_temporal)

    return CredencialesResponse(
        username=username,
        password_temporal=password_temporal,
        mensaje=(
            f"Cuenta creada para {persona.nombre_completo}. En el primer ingreso "
            "el sistema le va a pedir que cambie la contraseña."
        ),
        email_enviado=envio.enviado,
        detalle_envio=envio.detalle,
        texto_credenciales=envio.texto,
    )


# =============================================================================
# OPERACIONES SOBRE UNA CUENTA
# =============================================================================

@router.post("/{id_usuario}/resetear-password", response_model=CredencialesResponse)
def resetear_password(
    id_usuario: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.GESTION_USUARIOS)),
):
    """
    Genera una contraseña temporal nueva y obliga a cambiarla en el próximo
    ingreso. Es lo que se hace cuando alguien se olvidó la suya.

    Reutiliza exactamente el mismo mecanismo que el alta: la bandera
    debe_cambiar_password vuelve a True y el login deja de emitir token hasta
    que la persona defina una propia. Un solo camino para los tres casos
    (dueño inicial, cuenta nueva, olvido) es lo que hace que no haya un
    segundo flujo de contraseñas que mantener.

    De paso desbloquea la cuenta: si alguien llegó a los 5 intentos fallidos
    es, casi siempre, porque no se acordaba la contraseña — que es justo lo
    que este endpoint resuelve. Dejarla bloqueada obligaría a llamar dos veces.
    """
    usuario = _buscar_usuario(db, id_usuario)
    # Sin _validar_no_es_propia: resetearse la propia contraseña es inofensivo.
    _validar_jerarquia(sesion, usuario)

    password_temporal = generar_password_temporal()
    usuario.password_hash = hashear_password(password_temporal)
    usuario.debe_cambiar_password = True
    usuario.bloqueado = False
    usuario.intentos_fallidos = 0
    # También la traba temporal por intentos fallidos (limite_intentos.py):
    # si no, el reseteo parecería no andar durante 15 minutos.
    import limite_intentos
    limite_intentos.destrabar(usuario.username)
    db.commit()

    envio = enviar_credenciales(
        usuario.persona.email, usuario.persona.nombre,
        usuario.username, password_temporal,
    )

    return CredencialesResponse(
        username=usuario.username,
        password_temporal=password_temporal,
        mensaje=(
            f"Contraseña reseteada para {usuario.persona.nombre_completo}. "
            "En el próximo ingreso va a tener que cambiarla."
        ),
        email_enviado=envio.enviado,
        detalle_envio=envio.detalle,
        texto_credenciales=envio.texto,
    )


@router.post("/{id_usuario}/desbloquear", response_model=UsuarioAdminOut)
def desbloquear(
    id_usuario: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.GESTION_USUARIOS)),
):
    """
    Levanta el bloqueo por intentos fallidos, SIN tocar la contraseña.

    Distinto de resetear: acá la persona sí se acuerda su clave y el bloqueo
    fue un accidente (tecleó mal, tenía el Bloq Mayús). Cambiarle la
    contraseña en ese caso sería molestarla al pedo.
    """
    usuario = _buscar_usuario(db, id_usuario)
    _validar_jerarquia(sesion, usuario)

    import limite_intentos
    if (not usuario.bloqueado and (usuario.intentos_fallidos or 0) == 0
            and not limite_intentos.cuenta_trabada(usuario.username)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esa cuenta no está bloqueada.",
        )

    usuario.bloqueado = False
    usuario.intentos_fallidos = 0
    # "Desbloquear" también levanta la traba temporal por intentos fallidos
    # (limite_intentos.py), que es el bloqueo automático desde V-02.
    import limite_intentos
    limite_intentos.destrabar(usuario.username)
    db.commit()
    db.refresh(usuario)
    return _a_usuario_out(usuario)


@router.post("/{id_usuario}/toggle-estado", response_model=UsuarioAdminOut)
def alternar_estado(
    id_usuario: int,
    activo: bool | None = None,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.GESTION_USUARIOS)),
):
    """
    Activa o desactiva una cuenta.

    Desactivar es la ÚNICA forma de revocar una sesión en el acto: el JWT no
    se puede invalidar antes de que expire, pero obtener_sesion relee el
    Usuario en cada request y corta apenas ve `activo = false`. Por eso este
    endpoint es la herramienta real ante un problema de seguridad, no el
    /logout.

    No se borra la fila: la cuenta desactivada conserva su historial y se
    puede reactivar. Es el mismo criterio de baja lógica que usa el resto del
    sistema.

    `activo` es opcional y dice a qué estado ir. Sin él el endpoint invierte
    el que haya, que es lo que pide un switch de pantalla, pero eso convierte
    una pantalla desactualizada en un peligro: si dos personas desactivan la
    misma cuenta comprometida a la vez, el segundo pedido la REACTIVA. Cuando
    el que llama sabe qué quiere —y desactivar por seguridad siempre lo
    sabe— manda el destino y el resultado deja de depender del orden.
    """
    usuario = _buscar_usuario(db, id_usuario)
    _validar_no_es_propia(sesion, usuario)
    _validar_jerarquia(sesion, usuario)

    # Nadie se desactiva a sí mismo, NI SIQUIERA EL DUEÑO.
    #
    # _validar_no_es_propia exime al Dueño porque para editarse los datos no
    # hay problema, pero desactivarse es otra cosa: deja el sistema sin salida.
    # Un Dueño que se desactiva no puede volver a entrar, y por la regla 2
    # —solo un Dueño opera sobre la cuenta de un Dueño— ningún otro usuario
    # puede reactivarlo. Con un solo Dueño cargado, que es el caso normal, el
    # sistema queda inutilizable y hay que arreglarlo entrando a la base a
    # mano. Se descubrió haciéndolo: un click dejó la instalación sin acceso.
    if usuario.id_usuario == sesion.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No podés desactivar tu propia cuenta: quedarías afuera del "
                   "sistema sin poder volver a entrar.",
        )

    destino = (not bool(usuario.activo)) if activo is None else activo

    # NO se reactiva la cuenta de alguien dado de baja como empleado.
    #
    # Son dos banderas distintas —`Empleado.activo` y `Usuario.activo`— y cada
    # panel tocaba la suya sin mirar la otra, así que podían contradecirse. En
    # la base había un empleado dado de baja CON LA CUENTA ACTIVA: alguien que
    # ya no trabaja acá y podía seguir entrando con todos los permisos de su
    # rol. Es justo el agujero de offboarding que la baja dice evitar.
    #
    # La baja de personal apaga las dos (ver dar_de_baja_empleado). Lo que
    # faltaba era este lado: la vuelta se da desde Personal con "Reactivar",
    # que devuelve el puesto y el acceso juntos — que es el orden correcto,
    # porque el acceso se justifica en el puesto y no al revés.
    if destino and not usuario.activo and _empleado_dado_de_baja(usuario.persona):
        _rechazar_empleado_dado_de_baja(usuario.persona)

    usuario.activo = destino
    if usuario.activo:
        # Reactivar y dejarla bloqueada sería reactivarla a medias.
        usuario.bloqueado = False
        usuario.intentos_fallidos = 0
        import limite_intentos
        limite_intentos.destrabar(usuario.username)
    db.commit()
    db.refresh(usuario)
    return _a_usuario_out(usuario)


@router.delete("/{id_usuario}", response_model=MensajeResponse)
def borrar_cuenta(
    id_usuario: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.GESTION_USUARIOS)),
):
    """
    Borra la CUENTA DE ACCESO, no a la persona. Decisión del dueño (2026-09-16):
    "sólo la cuenta".

    Desactivar sigue siendo lo normal (reversible, conserva la fila). Borrar
    existe para la cuenta que no tendría que existir: creada por error, de una
    persona que no va a volver a usar el sistema, o para empezar de cero con un
    usuario nuevo. La Persona, su ficha de socio o empleado y todo su historial
    quedan; la persona vuelve a aparecer en "personas sin cuenta" y se le puede
    crear otra.

    Lo único que apunta a Usuario es `Asistencia.id_registrado_por` (quién fichó
    a alguien a mano): pasa a NULL, que el modelo ya admite — es lo mismo que un
    ingreso registrado por el lector, sin persona detrás. Las sesiones abiertas
    de esa cuenta mueren solas: obtener_sesion relee el Usuario en cada pedido.

    Reglas de fila (más estrictas que desactivar, porque no tiene vuelta):
      - Nadie borra SU PROPIA cuenta, ni siquiera el Dueño.
      - Sólo un Dueño borra la cuenta de un Dueño, y nunca la ÚLTIMA: el sistema
        quedaría sin nadie que pueda administrarlo.
    """
    usuario = _buscar_usuario(db, id_usuario)
    _validar_jerarquia(sesion, usuario)

    if usuario.id_usuario == sesion.id_usuario:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="No podés borrar tu propia cuenta.")

    persona = usuario.persona
    if persona is not None and Rol.DUENO in roles_de_persona(persona):
        otras = [u for u in db.query(Usuario).filter(Usuario.id_usuario != usuario.id_usuario).all()
                 if u.persona is not None and Rol.DUENO in roles_de_persona(u.persona)]
        if not otras:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Es la única cuenta de un dueño: borrarla dejaría el sistema sin administrador.")

    nombre = persona.nombre_completo if persona else usuario.username
    (db.query(Asistencia)
     .filter(Asistencia.id_registrado_por == usuario.id_usuario)
     .update({Asistencia.id_registrado_por: None}, synchronize_session=False))
    import limite_intentos
    limite_intentos.destrabar(usuario.username)
    db.delete(usuario)
    db.commit()
    return MensajeResponse(
        mensaje=f"Se borró la cuenta de {nombre}. Su ficha y su historial quedan; "
                "si hace falta, se le puede crear una cuenta nueva.")


@router.put("/{id_usuario}", response_model=UsuarioAdminOut)
def editar_usuario(
    id_usuario: int,
    datos: UsuarioEditarRequest,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.GESTION_USUARIOS)),
):
    """
    Cambia el nombre de usuario y el email de contacto.

    NO cambia el rol: el rol se deriva de las tablas donde la persona aparece
    (Socio, Entrenador, Dueno...), así que "cambiarlo" acá sería mentir. Para
    que alguien pase de recepcionista a entrenador se edita su ficha de
    PERSONAL, y su rol de sesión cambia solo.

    NO cambia la contraseña: para eso está resetear-password, que genera una
    temporal y obliga a definir una propia. Que un admin pueda escribir la
    contraseña de otro significaría que la conoce.

    Las dos reglas de fila aplican: nadie fuera del Dueño edita su propia
    cuenta, y solo un Dueño toca la cuenta de un Dueño.
    """
    usuario = _buscar_usuario(db, id_usuario)
    _validar_no_es_propia(sesion, usuario)
    _validar_jerarquia(sesion, usuario)

    # En minúsculas, como los que genera el sistema y como los compara el
    # login. Antes se guardaba tal cual: una cuenta renombrada "Mario.DJ"
    # entraba por la PWA y no por Flet, que manda el usuario en minúsculas.
    username = datos.username.strip().lower()
    if not username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="El nombre de usuario es obligatorio.")

    # UNIQUE en el esquema: se chequea a mano para dar un mensaje claro en vez
    # del error de restricción de PostgreSQL.
    tomado = (db.query(Usuario)
              .filter(Usuario.username == username, Usuario.id_usuario != id_usuario)
              .first())
    if tomado:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"El usuario '{username}' ya está en uso.")

    if datos.email and datos.email != usuario.persona.email:
        choca = (db.query(Persona)
                 .filter(Persona.email == datos.email,
                         Persona.id_persona != usuario.id_persona)
                 .first())
        if choca:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Ese email ya está registrado para otra persona.")

    # La misma regla que el alta y la edición de personal: un empleado sin
    # mail NI teléfono no se puede contactar. Sin esto, vaciarle el mail desde
    # acá salteaba la regla que su propio formulario hace cumplir.
    if (not datos.email and usuario.persona.empleado is not None
            and not usuario.persona.telefonos):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cargá un email o un teléfono: hace falta para contactarlo.")

    # La traba por intentos fallidos se guarda por nombre de usuario: al
    # renombrar, se muda con la cuenta. Si se quedara en el nombre viejo,
    # renombrar una cuenta trabada la destrabaría.
    if username != usuario.username:
        import limite_intentos
        limite_intentos.renombrar(usuario.username, username)

    usuario.username = username
    usuario.persona.email = datos.email

    db.commit()
    db.refresh(usuario)
    return _a_usuario_out(usuario)
