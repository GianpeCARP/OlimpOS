"""
routers/personal.py
-------------------
Alta y consulta del personal del gimnasio.

EL TIPO DE EMPLEADO NO ES UNA COLUMNA
-------------------------------------
En el esquema, `Empleado` guarda lo que TODO empleado tiene: legajo, sede,
fecha de ingreso. Lo que lo distingue —que sea entrenador o nutricionista—
está dado por en cuál de las cuatro tablas hijas existe su fila:

    Empleado ──┬── Entrenador     (titulo, especialidad, matricula)
               ├── Nutricionista  (titulo, matricula)
               ├── Recepcionista  (turno_laboral)
               └── Profesor       (titulo, especialidad)

Es el mismo criterio que hace que Persona no tenga columna `rol`: en vez de un
campo de texto que hay que mantener sincronizado con la realidad, el tipo se
DERIVA de qué datos existen. Un entrenador sin matrícula es un entrenador con
la matrícula vacía; un empleado sin fila en ninguna hija es alguien cargado a
quien todavía no se le asignó función, que es un estado válido.

La ventaja concreta: `turno_laboral` solo existe para Recepcionista, y
`matricula` no existe para Profesor. Con una columna `rol` en Empleado
habría que poner las siete columnas en la misma tabla y dejarlas nulas la
mayor parte del tiempo.

EL PROFESOR NO INICIA SESIÓN
----------------------------
Es el cuarto tipo y el único sin rol de sesión: da clases, no usa el sistema.
El alta le ignora `crear_cuenta` aunque venga en True — crearle credenciales
sería crear una cuenta que el login rechaza por no tener roles.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from auth import generar_password_temporal, generar_username, hashear_password
from database import get_db
from models import (
    Dieta, Empleado, Entrenador, Nutricionista, Persona, Profesor,
    Recepcionista, Rutina, Sede, Telefono, Usuario,
)
from notificaciones import enviar_credenciales
from permisos import Accion, Seccion
from schemas import (
    BajaEmpleadoRequest, EmpleadoAltaRequest, EmpleadoAltaResponse,
    EmpleadoEditarRequest, EmpleadoOut, PersonaOut, ProfesionalOpcion,
    RolEmpleado,
)
from security import Sesion, requiere_accion, requiere_seccion

router = APIRouter(prefix="/personal", tags=["Personal"])


# Qué clase corresponde a cada rol, y qué campos acepta cada una. Tenerlo como
# tabla evita el if/elif de cuatro ramas repetido en el alta, en la lectura y
# en cada endpoint futuro que necesite lo mismo.
ESPECIALIDADES = {
    RolEmpleado.ENTRENADOR:    (Entrenador,    ("titulo", "especialidad", "matricula")),
    RolEmpleado.NUTRICIONISTA: (Nutricionista, ("titulo", "matricula")),
    RolEmpleado.RECEPCIONISTA: (Recepcionista, ("id_franja_laboral",)),
    RolEmpleado.PROFESOR:      (Profesor,      ("titulo", "especialidad")),
}

# El único que no habilita el ingreso al sistema.
ROLES_SIN_SESION = {RolEmpleado.PROFESOR}


def _legajo(id_empleado: int) -> str:
    """
    'E-0001'. Mismo formato que ya usa la PWA (proximoLegajo en mockDb.ts).

    Se arma DESPUÉS del insert, con el id que asignó la base: calcularlo antes
    contando empleados daría legajos repetidos si dos altas ocurren a la vez.
    """
    return f"E-{id_empleado:04d}"


def _especialidad_de(empleado: Empleado):
    """
    Devuelve (rol, fila) mirando cuál de las cuatro hijas tiene datos, o
    (None, None) si el empleado todavía no tiene función asignada.
    """
    for rol, (clase, _campos) in ESPECIALIDADES.items():
        fila = getattr(empleado, clase.__name__.lower(), None)
        if fila is not None:
            return rol, fila
    return None, None


def _a_empleado_out(empleado: Empleado) -> EmpleadoOut:
    persona = empleado.persona
    rol, fila = _especialidad_de(empleado)

    return EmpleadoOut(
        id_empleado=empleado.id_empleado,
        id_persona=empleado.id_persona,
        id_sede=empleado.id_sede,
        legajo=empleado.legajo,
        fecha_ingreso=empleado.fecha_ingreso,
        fecha_egreso=empleado.fecha_egreso,
        activo=bool(empleado.activo),
        rol=rol,
        # getattr con default: cada hija tiene solo algunos de estos campos, y
        # pedirle `titulo` a un Recepcionista tiene que dar None, no romper.
        titulo=getattr(fila, "titulo", None),
        especialidad=getattr(fila, "especialidad", None),
        matricula=getattr(fila, "matricula", None),
        # El turno laboral del recepcionista ahora es una FK a Franja_Laboral;
        # se expone su NOMBRE (la franja), no el id.
        turno_laboral=(fila.franja.nombre
                       if rol == RolEmpleado.RECEPCIONISTA and getattr(fila, "franja", None)
                       else None),
        id_franja_laboral=getattr(fila, "id_franja_laboral", None),
        dni=persona.dni,
        nombre=persona.nombre,
        apellido=persona.apellido,
        email=persona.email,
        tiene_cuenta=persona.usuario is not None,
    )


@router.get("", response_model=list[EmpleadoOut])
def listar_personal(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.PERSONAL)),
):
    """
    Lista el personal. Alcanza con LECTURA: el Recepcionista ve la grilla pero
    no puede dar de alta ni de baja (eso es exclusivo del Dueño).
    """
    # Misma carga anticipada que en /usuarios y /socios: el rol de un empleado
    # se deriva de cual de los tres subtipos tiene fila, y con carga perezosa
    # eso eran tres consultas por empleado. Ver CARGA_DE_ROLES en
    # routers/usuarios.py.
    empleados = (db.query(Empleado)
                 .options(
                     selectinload(Empleado.persona),
                     selectinload(Empleado.entrenador),
                     selectinload(Empleado.nutricionista),
                     selectinload(Empleado.recepcionista),
                 )
                 .order_by(Empleado.id_empleado)
                 .all())
    return [_a_empleado_out(e) for e in empleados]


@router.post("", response_model=EmpleadoAltaResponse, status_code=status.HTTP_201_CREATED)
def alta_empleado(
    datos: EmpleadoAltaRequest,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.ALTA_BAJA_PERSONAL)),
):
    """
    Da de alta un empleado con su especialidad y, si corresponde, su cuenta.

    Protegido por ALTA_BAJA_PERSONAL, que en la matriz solo tiene el Dueño:
    contratar y desvincular gente es una decisión del negocio, no operativa
    del día a día. El Recepcionista ve la sección pero no puede hacerlo.
    """
    dni = datos.dni.strip()

    if db.get(Sede, datos.id_sede) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La sede indicada no existe.",
        )

    # --- 1. Persona ---------------------------------------------------------
    # Igual que en el alta de socio: si el DNI ya está, se reusa. Un socio del
    # gimnasio al que contratan de entrenador es el caso típico.
    persona = db.query(Persona).filter(Persona.dni == dni).first()

    if persona is None:
        persona = Persona(
            dni=dni,
            nombre=datos.nombre.strip(),
            apellido=datos.apellido.strip(),
            email=datos.email,
            fecha_nacimiento=datos.fecha_nacimiento,
        )
        db.add(persona)
        db.flush()
    elif persona.empleado is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{persona.nombre_completo} ya está registrado como empleado.",
        )

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

    if datos.telefono and datos.telefono.strip():
        db.add(Telefono(
            id_persona=persona.id_persona,
            numero=datos.telefono.strip(),
            tipo="CELULAR",
            principal=True,
        ))

    # --- 2. Empleado --------------------------------------------------------
    empleado = Empleado(
        id_persona=persona.id_persona,
        id_sede=datos.id_sede,
        fecha_ingreso=datos.fecha_ingreso or date.today(),
        activo=True,
    )
    db.add(empleado)
    db.flush()                         # ahora existe id_empleado
    empleado.legajo = _legajo(empleado.id_empleado)

    # --- 3. Especialidad ----------------------------------------------------
    # Acá se materializa el rol: crear la fila en la tabla hija ES asignarle
    # la función. Solo se copian los campos que esa hija tiene.
    clase, campos = ESPECIALIDADES[datos.rol]
    valores = {campo: getattr(datos, campo) for campo in campos}
    db.add(clase(id_empleado=empleado.id_empleado, **valores))

    # --- 4. Cuenta ----------------------------------------------------------
    username = None
    password_temporal = None
    aviso_sin_cuenta = ""

    if datos.rol in ROLES_SIN_SESION:
        # Se ignora crear_cuenta en silencio para el rol, pero se avisa en el
        # mensaje: el operador marcó una casilla y tiene que saber por qué no
        # pasó nada.
        aviso_sin_cuenta = (
            f" Un {datos.rol.value} no inicia sesión en el sistema, "
            "así que no se le creó cuenta."
        )
    elif datos.crear_cuenta:
        if persona.usuario is not None:
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
                debe_cambiar_password=True,
                activo=True,
            ))

    db.commit()
    db.refresh(empleado)
    db.refresh(persona)

    # --- 5. Credenciales ----------------------------------------------------
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
            f"{datos.rol.value} dado de alta (legajo {empleado.legajo}) con usuario "
            f"'{username}'. En el primer ingreso va a tener que cambiar la contraseña."
        )
    elif username:
        mensaje = (
            f"{datos.rol.value} dado de alta (legajo {empleado.legajo}). "
            f"Ya tenía cuenta ('{username}'), se conserva."
        )
    else:
        mensaje = f"{datos.rol.value} dado de alta (legajo {empleado.legajo})." + aviso_sin_cuenta

    return EmpleadoAltaResponse(
        id_empleado=empleado.id_empleado,
        legajo=empleado.legajo,
        rol=datos.rol,
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

def _validar_cambio_de_rol(db: Session, empleado: Empleado, rol_nuevo: RolEmpleado) -> None:
    """
    Frena un cambio de rol que dejaría registros huérfanos.

    Cambiar de rol implica BORRAR la fila de la especialidad actual. Pero esa
    fila es el destino de claves foráneas NOT NULL: `Rutina.id_entrenador` y
    `Dieta.id_nutricionista`. Borrarla con trabajo a su nombre haría fallar el
    DELETE por violación de FK — un error de base de datos incomprensible para
    quien está mirando la pantalla de personal.

    Así que se corta antes, con un mensaje que dice QUÉ hay que reasignar. Es
    la misma regla que aplicaría Postgres, pero explicada.
    """
    rol_actual, fila = _especialidad_de(empleado)
    if rol_actual is None or rol_actual == rol_nuevo:
        return

    if rol_actual == RolEmpleado.ENTRENADOR:
        cuantas = db.query(Rutina).filter(Rutina.id_entrenador == fila.id_entrenador).count()
        if cuantas:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(f"No se puede cambiarle el rol: tiene {cuantas} rutina(s) a su "
                        "nombre. Reasignalas a otro entrenador primero."),
            )

    if rol_actual == RolEmpleado.NUTRICIONISTA:
        cuantas = db.query(Dieta).filter(Dieta.id_nutricionista == fila.id_nutricionista).count()
        if cuantas:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(f"No se puede cambiarle el rol: tiene {cuantas} dieta(s) a su "
                        "nombre. Reasignalas a otro nutricionista primero."),
            )


# =============================================================================
# SELECTORES DE PROFESIONALES
# =============================================================================
# Los usan los formularios de Rutinas y Nutrición para elegir a cargo de quién
# queda cada plantilla. Van declarados ANTES que /{id_empleado} o FastAPI
# intentaría leer "entrenadores" como si fuera un id.


def _opciones(db: Session, clase, id_attr: str) -> list[ProfesionalOpcion]:
    """
    Los profesionales de un tipo cuyo empleado está ACTIVO.

    El filtro por activo importa: ofrecer a alguien que ya no trabaja en el
    gimnasio haría que el formulario permita asignarle trabajo nuevo, y el
    backend lo rechazaría después con un mensaje que el usuario no esperaba.
    """
    filas = (
        db.query(clase)
        .join(Empleado, clase.id_empleado == Empleado.id_empleado)
        .filter(Empleado.activo == True)  # noqa: E712
        .all()
    )
    opciones = []
    for fila in filas:
        persona = fila.empleado.persona if fila.empleado else None
        opciones.append(ProfesionalOpcion(
            id=getattr(fila, id_attr),
            nombre=persona.nombre_completo if persona else "Sin asignar",
        ))
    return sorted(opciones, key=lambda o: o.nombre)


@router.get("/entrenadores", response_model=list[ProfesionalOpcion])
def listar_entrenadores(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.RUTINAS)),
):
    """
    Para el selector del formulario de rutinas. Pide permiso sobre RUTINAS y
    no sobre PERSONAL: quien arma una rutina necesita elegir el entrenador
    aunque no tenga acceso a la ficha de personal.
    """
    return _opciones(db, Entrenador, "id_entrenador")


@router.get("/nutricionistas", response_model=list[ProfesionalOpcion])
def listar_nutricionistas(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.NUTRICION)),
):
    """Espejo del anterior, para el formulario de dietas."""
    return _opciones(db, Nutricionista, "id_nutricionista")


@router.get("/{id_empleado}", response_model=EmpleadoOut)
def obtener_empleado(
    id_empleado: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.PERSONAL)),
):
    empleado = db.get(Empleado, id_empleado)
    if empleado is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="El empleado no existe.")
    return _a_empleado_out(empleado)


@router.put("/{id_empleado}", response_model=EmpleadoOut)
def editar_empleado(
    id_empleado: int,
    datos: EmpleadoEditarRequest,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.ALTA_BAJA_PERSONAL)),
):
    """
    Edita un empleado, incluido su rol.

    El cambio de rol es la parte delicada: borra la fila de la especialidad
    vieja y crea la nueva. Antes de tocar nada se valida que eso no deje
    trabajo huérfano — ver _validar_cambio_de_rol.
    """
    empleado = db.get(Empleado, id_empleado)
    if empleado is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="El empleado no existe.")

    persona = empleado.persona

    if datos.email and datos.email != persona.email:
        choca = (db.query(Persona)
                 .filter(Persona.email == datos.email,
                         Persona.id_persona != persona.id_persona)
                 .first())
        if choca:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Ese email ya está registrado para otra persona.")

    _validar_cambio_de_rol(db, empleado, datos.rol)

    persona.nombre = datos.nombre.strip()
    persona.apellido = datos.apellido.strip()
    persona.email = datos.email

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

    # --- El rol -------------------------------------------------------------
    rol_actual, fila_actual = _especialidad_de(empleado)
    clase, campos = ESPECIALIDADES[datos.rol]

    if rol_actual == datos.rol and fila_actual is not None:
        # Mismo rol: solo se actualizan sus campos propios.
        for campo in campos:
            setattr(fila_actual, campo, getattr(datos, campo))
    else:
        # Cambio de rol: fuera la vieja, adentro la nueva.
        if fila_actual is not None:
            db.delete(fila_actual)
            # flush antes del insert: sin esto SQLAlchemy puede reordenar las
            # operaciones y el UNIQUE de id_empleado chocaría con la fila vieja
            # todavía sin borrar.
            db.flush()
        valores = {campo: getattr(datos, campo) for campo in campos}
        db.add(clase(id_empleado=empleado.id_empleado, **valores))

    db.commit()
    db.refresh(empleado)
    return _a_empleado_out(empleado)


@router.post("/{id_empleado}/baja", response_model=EmpleadoOut)
def dar_de_baja_empleado(
    id_empleado: int,
    datos: BajaEmpleadoRequest,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.ALTA_BAJA_PERSONAL)),
):
    """
    Da de baja a un empleado. Baja lógica: se marca inactivo y se guarda la
    fecha de egreso, nunca se borra la fila.

    La fila del rol queda intacta: alguien dado de baja sigue habiendo sido
    entrenador, y sus rutinas siguen atribuidas a él.

    Y arrastra el acceso: un empleado que ya no trabaja acá no tiene por qué
    seguir entrando al panel. Sin eso la baja sería cosmética —la ficha diría
    "Inactivo" y la persona seguiría iniciando sesión con todos los permisos de
    su rol—, que es el agujero clásico de offboarding.
    """
    empleado = db.get(Empleado, id_empleado)
    if empleado is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="El empleado no existe.")
    if not empleado.activo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{empleado.persona.nombre_completo} ya estaba dado de baja.")

    # Nadie se da de baja a sí mismo: se quedaría sin acceso en el acto, y si
    # era el único con el permiso no habría quien lo revierta.
    if empleado.id_persona == sesion.id_persona:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No podés darte de baja a vos mismo.")

    empleado.activo = False
    empleado.fecha_egreso = date.today()

    if empleado.persona.usuario is not None:
        empleado.persona.usuario.activo = False

    db.commit()
    db.refresh(empleado)
    return _a_empleado_out(empleado)


@router.post("/{id_empleado}/reactivar", response_model=EmpleadoOut)
def reactivar_empleado(
    id_empleado: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.ALTA_BAJA_PERSONAL)),
):
    """Vuelve a activar a un empleado y su cuenta de acceso."""
    empleado = db.get(Empleado, id_empleado)
    if empleado is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="El empleado no existe.")
    if empleado.activo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{empleado.persona.nombre_completo} ya estaba activo.")

    empleado.activo = True
    empleado.fecha_egreso = None
    if empleado.persona.usuario is not None:
        empleado.persona.usuario.activo = True

    db.commit()
    db.refresh(empleado)
    return _a_empleado_out(empleado)
