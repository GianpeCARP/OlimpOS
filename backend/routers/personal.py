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
from sqlalchemy.orm import Session

from auth import generar_password_temporal, generar_username, hashear_password
from database import get_db
from models import (
    Empleado, Entrenador, Nutricionista, Persona, Profesor, Recepcionista,
    Sede, Telefono, Usuario,
)
from notificaciones import enviar_credenciales
from permisos import Accion, Seccion
from schemas import (
    EmpleadoAltaRequest, EmpleadoAltaResponse, EmpleadoOut, PersonaOut, RolEmpleado,
)
from security import Sesion, requiere_accion, requiere_seccion

router = APIRouter(prefix="/personal", tags=["Personal"])


# Qué clase corresponde a cada rol, y qué campos acepta cada una. Tenerlo como
# tabla evita el if/elif de cuatro ramas repetido en el alta, en la lectura y
# en cada endpoint futuro que necesite lo mismo.
ESPECIALIDADES = {
    RolEmpleado.ENTRENADOR:    (Entrenador,    ("titulo", "especialidad", "matricula")),
    RolEmpleado.NUTRICIONISTA: (Nutricionista, ("titulo", "matricula")),
    RolEmpleado.RECEPCIONISTA: (Recepcionista, ("turno_laboral",)),
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
        # pedirle `turno_laboral` a un Entrenador tiene que dar None, no romper.
        titulo=getattr(fila, "titulo", None),
        especialidad=getattr(fila, "especialidad", None),
        matricula=getattr(fila, "matricula", None),
        turno_laboral=getattr(fila, "turno_laboral", None),
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
    empleados = db.query(Empleado).order_by(Empleado.id_empleado).all()
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
