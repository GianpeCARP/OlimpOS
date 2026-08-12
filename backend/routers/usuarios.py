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

1. NADIE fuera del Dueño puede editar ni desactivar SU PROPIA cuenta.
   Si no, alguien puede desactivarse o cambiarse el usuario a sí mismo sin
   que nadie lo vea venir. El Dueño queda exento por ser la autoridad última
   del sistema.

   Resetearse la contraseña propia SÍ está permitido: no hay riesgo en eso, y
   es lo que deja hacer cualquier sistema real. La restricción es sobre editar
   y sobre desactivar.

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
from sqlalchemy.orm import Session

from auth import generar_password_temporal, generar_username, hashear_password
from database import get_db
from models import Persona, Rol, Usuario, roles_de_persona
from notificaciones import enviar_credenciales
from permisos import Accion, Seccion
from schemas import (
    CredencialesResponse, PersonaSinCuentaOut, UsuarioAdminOut,
    UsuarioCrearRequest, UsuarioEditarRequest,
)
from security import Sesion, requiere_accion, requiere_seccion

router = APIRouter(prefix="/usuarios", tags=["Usuarios del sistema"])


# =============================================================================
# HELPERS
# =============================================================================

def _a_usuario_out(usuario: Usuario) -> UsuarioAdminOut:
    persona = usuario.persona
    return UsuarioAdminOut(
        id_usuario=usuario.id_usuario,
        id_persona=usuario.id_persona,
        username=usuario.username,
        dni=persona.dni,
        nombre_completo=persona.nombre_completo,
        email=persona.email,
        roles=roles_de_persona(persona),
        activo=bool(usuario.activo),
        bloqueado=bool(usuario.bloqueado),
        debe_cambiar_password=bool(usuario.debe_cambiar_password),
        ultimo_acceso=usuario.ultimo_acceso,
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
    """Lista todas las cuentas del sistema, con su estado y sus roles."""
    usuarios = db.query(Usuario).order_by(Usuario.id_usuario).all()
    return [_a_usuario_out(u) for u in usuarios]


@router.get("/personas-sin-cuenta", response_model=list[PersonaSinCuentaOut])
def listar_personas_sin_cuenta(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.USUARIOS)),
):
    """
    Personas que podrían tener cuenta pero todavía no la tienen.

    Filtra por rol y no solo por "no tiene Usuario": alguien sin ningún rol de
    sesión —un Profesor, por ejemplo— no puede usar el sistema aunque se le
    creara la cuenta, porque el login rechaza a quien no tiene roles. Ofrecerlo
    como candidato sería ofrecer crear una cuenta inútil.

    Va ANTES de la ruta /{id_usuario} a propósito: FastAPI resuelve las rutas
    en el orden en que se declaran, y si estuviera después intentaría leer
    "personas-sin-cuenta" como si fuera un id y respondería un error de
    validación.
    """
    personas = db.query(Persona).filter(Persona.usuario == None).all()  # noqa: E711

    salida = []
    for p in personas:
        roles = roles_de_persona(p)
        if not roles:
            continue
        salida.append(PersonaSinCuentaOut(
            id_persona=p.id_persona,
            dni=p.dni,
            nombre_completo=p.nombre_completo,
            email=p.email,
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

    if not usuario.bloqueado and (usuario.intentos_fallidos or 0) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esa cuenta no está bloqueada.",
        )

    usuario.bloqueado = False
    usuario.intentos_fallidos = 0
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

    usuario.activo = (not bool(usuario.activo)) if activo is None else activo
    if usuario.activo:
        # Reactivar y dejarla bloqueada sería reactivarla a medias.
        usuario.bloqueado = False
        usuario.intentos_fallidos = 0
    db.commit()
    db.refresh(usuario)
    return _a_usuario_out(usuario)


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

    username = datos.username.strip()
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

    usuario.username = username
    usuario.persona.email = datos.email

    db.commit()
    db.refresh(usuario)
    return _a_usuario_out(usuario)
