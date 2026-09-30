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
la matrícula vacía.

La ventaja concreta: `turno_laboral` solo existe para Recepcionista, y
`matricula` no existe para Profesor. Con una columna `rol` en Empleado
habría que poner las siete columnas en la misma tabla y dejarlas nulas la
mayor parte del tiempo.

SON VARIOS ROLES, Y SE APAGAN EN VEZ DE BORRARSE
------------------------------------------------
Las cuatro hijas son subtipos SOLAPADOS en el esquema desde el primer día
(`schema.sql`): nada impide que la misma persona tenga fila en dos. Lo que
imponía "un rol y uno solo" era esta capa, que leía la primera fila que
encontraba y, al cambiar de rol, BORRABA la vieja.

Borrarla no borraba "el rol": borraba el trabajo hecho en ese rol, porque esa
fila es el destino de claves foráneas sin ON DELETE (Rutina,
Asignacion_Entrenador, Horario_Actividad, Turno, Dieta, Profesor_Actividad).
Postgres rechazaba el DELETE y el cambio de rol respondía 409 para siempre a
cualquiera con un socio a cargo o un horario a su nombre.

Desde el 2026-09-29 la fila no se borra: se apaga (`activo`). Quién es alguien
HOY lo dice ese flag —`roles_de_persona` en models.py— y la fila apagada queda
sosteniendo su historial. Como consecuencia directa, un empleado puede tener
varios roles prendidos a la vez, y por eso la API habla de `roles` y
`detalles` en plural. Un empleado sin ninguna fila prendida es alguien cargado
a quien todavía no se le asignó función; el alta y la edición piden al menos
uno.

EL PROFESOR TAMBIÉN INICIA SESIÓN
---------------------------------
Hasta el 2026-09-16 no tenía rol de sesión y el alta ignoraba `crear_cuenta`.
Desde entonces tiene cuenta como los otros tres, para "Mis clases" en la PWA:
el alta respeta la casilla igual para los cuatro. Ver Rol.PROFESOR (models.py).
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from auth import generar_password_temporal, generar_username, hashear_password
from database import get_db
from models import (
    AsignacionEntrenador, Empleado, Entrenador, FranjaLaboral, Nutricionista,
    Persona, Profesor, Recepcionista, Sede, Telefono, Usuario, rol_activo,
)
from notificaciones import enviar_credenciales
from permisos import Accion, Seccion
from schemas import (
    BajaEmpleadoRequest, DetalleRolOut, EmpleadoAltaRequest, EmpleadoAltaResponse,
    EmpleadoEditarRequest, EmpleadoOut, FranjaLaboralOut, PersonaOut,
    ProfesionalOpcion, RolEmpleado,
)
from routers.nutricion import _nutricionista_de_sesion
from routers.rutinas import _entrenador_de_sesion
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

def _legajo(id_empleado: int) -> str:
    """
    'E-0001'. Mismo formato que ya usa la PWA (proximoLegajo en mockDb.ts).

    Se arma DESPUÉS del insert, con el id que asignó la base: calcularlo antes
    contando empleados daría legajos repetidos si dos altas ocurren a la vez.
    """
    return f"E-{id_empleado:04d}"


def _fila_de_rol(empleado: Empleado, rol: RolEmpleado):
    """
    La fila del subtipo de ese rol, prendida o apagada, o None si nunca existió.

    Hace falta distinguir los dos casos: si existe apagada, un cambio de rol la
    REACTIVA (y la persona recupera su título y su matrícula tal como estaban);
    si no existe, hay que crearla.
    """
    clase, _campos = ESPECIALIDADES[rol]
    return getattr(empleado, clase.__name__.lower(), None)


def _especialidades_de(empleado: Empleado) -> list[tuple[RolEmpleado, object]]:
    """
    Los roles PRENDIDOS de un empleado, con su fila, en el orden de
    ESPECIALIDADES. Lista vacía = cargado sin función todavía.

    Devuelve una lista y no un solo par porque los subtipos de Empleado son
    SOLAPADOS en el esquema (schema.sql): la misma persona puede ser
    entrenadora y profesora a la vez. La versión anterior cortaba en la primera
    fila que encontraba, así que a alguien con dos roles la pantalla le mostraba
    uno solo —el primero del diccionario— y editarlo le borraba el otro.

    Las filas APAGADAS quedan afuera: existen para sostener el historial de un
    rol que la persona ya no cumple (ver Entrenador.activo en models.py).
    """
    prendidos = []
    for rol in ESPECIALIDADES:
        fila = _fila_de_rol(empleado, rol)
        if rol_activo(fila):
            prendidos.append((rol, fila))
    return prendidos


def _telefono_principal(persona) -> str | None:
    """El principal de la persona (o el primero que tenga), o None."""
    telefonos = sorted(persona.telefonos or [],
                       key=lambda t: (not bool(t.principal), t.id_telefono))
    return telefonos[0].numero if telefonos else None


def _a_detalle_out(rol: RolEmpleado, fila) -> DetalleRolOut:
    """Los datos propios de un rol, listos para la pantalla."""
    return DetalleRolOut(
        rol=rol,
        # getattr con default: cada hija tiene solo algunos de estos campos, y
        # pedirle `titulo` a un Recepcionista tiene que dar None, no romper.
        titulo=getattr(fila, "titulo", None),
        especialidad=getattr(fila, "especialidad", None),
        matricula=getattr(fila, "matricula", None),
        # El turno laboral del recepcionista es una FK a Franja_Laboral; se
        # expone su NOMBRE (la franja), no el id.
        turno_laboral=(fila.franja.nombre
                       if rol == RolEmpleado.RECEPCIONISTA and getattr(fila, "franja", None)
                       else None),
        id_franja_laboral=getattr(fila, "id_franja_laboral", None),
    )


def _a_empleado_out(empleado: Empleado) -> EmpleadoOut:
    persona = empleado.persona
    especialidades = _especialidades_de(empleado)

    return EmpleadoOut(
        id_empleado=empleado.id_empleado,
        id_persona=empleado.id_persona,
        id_sede=empleado.id_sede,
        legajo=empleado.legajo,
        fecha_ingreso=empleado.fecha_ingreso,
        fecha_egreso=empleado.fecha_egreso,
        activo=bool(empleado.activo),
        roles=[rol for rol, _fila in especialidades],
        detalles=[_a_detalle_out(rol, fila) for rol, fila in especialidades],
        dni=persona.dni,
        nombre=persona.nombre,
        apellido=persona.apellido,
        email=persona.email,
        telefono=_telefono_principal(persona),
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
    # Misma carga anticipada que en /usuarios y /socios: los roles de un
    # empleado se derivan de cuales de los CUATRO subtipos tienen fila
    # prendida, y con carga perezosa eso eran cuatro consultas por empleado.
    # (El comentario decia "tres" y cargaba tres: faltaba Profesor.)
    # Ver CARGA_DE_ROLES en routers/usuarios.py.
    empleados = (db.query(Empleado)
                 .options(
                     selectinload(Empleado.persona).selectinload(Persona.telefonos),
                     selectinload(Empleado.entrenador),
                     selectinload(Empleado.nutricionista),
                     # Faltaba la del recepcionista y la del profesor: la
                     # franja y el cuarto subtipo se leían con carga perezosa,
                     # dos consultas más por empleado.
                     selectinload(Empleado.recepcionista).selectinload(Recepcionista.franja),
                     selectinload(Empleado.profesor),
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

    # --- 3. Especialidades --------------------------------------------------
    # Acá se materializan los roles: crear la fila en la tabla hija ES
    # asignarle la función. Una fila por rol pedido, y de cada una solo se
    # copian los campos que esa hija tiene. Un entrenador que además es
    # profesor comparte título y especialidad: es la misma persona con el mismo
    # título, guardado dos veces porque son dos tablas.
    for rol in datos.roles:
        clase, campos = ESPECIALIDADES[rol]
        valores = {campo: getattr(datos, campo) for campo in campos}
        db.add(clase(id_empleado=empleado.id_empleado, activo=True, **valores))

    # --- 4. Cuenta ----------------------------------------------------------
    username = None
    password_temporal = None

    # Los CUATRO roles pueden tener cuenta. Hasta el 2026-09-16 el Profesor
    # quedaba afuera: acá se ignoraba `crear_cuenta` y se avisaba por qué. El
    # efecto real era que el profesor no tenía dónde ver su horario ni quién
    # se anotaba a su clase. Ver Rol.PROFESOR en models.py.
    if datos.crear_cuenta:
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

    # "Entrenador y Profesor" y no "Entrenador": con varios roles, nombrar uno
    # solo haría dudar de si los otros se guardaron.
    nombres = [r.value for r in datos.roles]
    quien = nombres[0] if len(nombres) == 1 else ", ".join(nombres[:-1]) + " y " + nombres[-1]

    if password_temporal:
        mensaje = (
            f"{quien} dado de alta (legajo {empleado.legajo}) con usuario "
            f"'{username}'. En el primer ingreso va a tener que cambiar la contraseña."
        )
    elif username:
        mensaje = (
            f"{quien} dado de alta (legajo {empleado.legajo}). "
            f"Ya tenía cuenta ('{username}'), se conserva."
        )
    else:
        mensaje = f"{quien} dado de alta (legajo {empleado.legajo})."

    return EmpleadoAltaResponse(
        id_empleado=empleado.id_empleado,
        legajo=empleado.legajo,
        roles=datos.roles,
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

def _aplicar_roles(db: Session, empleado: Empleado,
                   roles_pedidos: list[RolEmpleado], datos) -> None:
    """
    Deja prendidos exactamente los roles pedidos, sin borrar ninguna fila.

    HASTA EL 2026-09-29 ESTO BORRABA
    --------------------------------
    Cambiar de rol hacía `db.delete(fila_vieja)`, y esa fila es el destino de
    claves foráneas sin ON DELETE: a `Entrenador` apuntan `Rutina`,
    `Asignacion_Entrenador`, `Horario_Actividad` y `Turno`; a `Nutricionista`,
    `Dieta`; a `Profesor`, `Profesor_Actividad` y, por ella, sus horarios y
    turnos. El DELETE fallaba, y para que no llegara a pantalla como un 500
    había una validación que devolvía 409: quien tuviera un socio a cargo o un
    horario a su nombre no podía cambiar de rol NUNCA.

    El arreglo no fue relajar la validación sino dejar de borrar. La fila queda
    con `activo=false` sosteniendo su historial, y quién es alguien HOY lo dice
    ese flag (`roles_de_persona`). Con eso la validación entera sobra: no hay
    nada que se pueda romper, así que no hay nada que frenar.

    Tres caminos por rol:
      · pedido y con fila apagada  → se reactiva, con sus datos como estaban;
      · pedido y sin fila          → se crea;
      · no pedido y prendido       → se apaga, más la limpieza de ese rol.

    `datos` es el pedido (alta o edición) y de él salen los campos propios de
    cada tabla. Se aplica la misma regla que el resto de la edición: un campo
    que no vino en el pedido NO se toca.
    """
    pedidos = set(roles_pedidos)
    prendidos = {rol for rol, _fila in _especialidades_de(empleado)}

    for rol in ESPECIALIDADES:
        clase, campos = ESPECIALIDADES[rol]
        fila = _fila_de_rol(empleado, rol)

        if rol in pedidos:
            if fila is None:
                # Nueva. Acá sí se escriben todos los campos: no hay nada que
                # conservar.
                valores = {campo: getattr(datos, campo) for campo in campos}
                db.add(clase(id_empleado=empleado.id_empleado, activo=True, **valores))
                continue

            fila.activo = True
            # Sólo lo que vino en el pedido, la misma regla que el PUT de socio
            # (editar_socio). Cada app muestra campos distintos —la PWA los del
            # rol, Flet título, especialidad y matrícula—, y con "todos,
            # siempre" cada una borraba en silencio lo que la otra había
            # cargado: editarle el teléfono a una nutricionista desde la PWA le
            # borraba la matrícula. Ausente se conserva; en null, se borra.
            for campo in campos:
                if campo in datos.model_fields_set:
                    setattr(fila, campo, getattr(datos, campo))

        elif rol in prendidos:
            fila.activo = False
            _limpiar_al_apagar(db, rol, fila)


def _limpiar_al_apagar(db: Session, rol: RolEmpleado, fila) -> None:
    """
    Lo que hay que cerrar cuando alguien deja de cumplir un rol.

    Apagar el flag alcanza para que la persona no entre más con ese rol, pero
    no para que desaparezca de las pantallas de los demás: un entrenador que
    pasa a recepción seguía figurando en "Mi entrenador" del socio, que lista
    las asignaciones ACTIVA. Es el mismo cierre que hace la baja del empleado
    (`dar_de_baja_empleado`), por el mismo motivo.

    Se FINALIZA, no se borra: el historial de quién entrenó a quién queda, con
    su fecha de fin. Volver al rol de entrenador NO las reabre — a la vuelta, a
    quién entrena se decide de nuevo, que es lo que el gimnasio haría de
    verdad.

    Los otros tres roles no necesitan nada. El nutricionista: sus dietas
    quedan asignadas y el socio sigue comiendo lo mismo, porque `Asignacion_Dieta`
    ata socio con dieta y no socio con nutricionista. El profesor: sus horarios
    y turnos guardan su `id_profesor` y siguen teniendo responsable; deja de
    aparecer como opción porque los selectores filtran por `activo`. El
    recepcionista no produce nada propio.
    """
    if rol != RolEmpleado.ENTRENADOR:
        return

    (db.query(AsignacionEntrenador)
     .filter(AsignacionEntrenador.id_entrenador == fila.id_entrenador,
             AsignacionEntrenador.estado == "ACTIVA")
     .update({AsignacionEntrenador.estado: "FINALIZADA",
              AsignacionEntrenador.fecha_fin: date.today()},
             synchronize_session=False))


# =============================================================================
# SELECTORES DE PROFESIONALES
# =============================================================================
# Los usan los formularios de Rutinas y Nutrición para elegir a cargo de quién
# queda cada plantilla. Van declarados ANTES que /{id_empleado} o FastAPI
# intentaría leer "entrenadores" como si fuera un id.


def _opciones(db: Session, clase, id_attr: str) -> list[ProfesionalOpcion]:
    """
    Los profesionales de un tipo que siguen cumpliendo ese rol, y cuyo empleado
    está ACTIVO.

    Son DOS filtros distintos y hacen falta los dos. `Empleado.activo` es
    trabajar todavía en el gimnasio; `clase.activo` es cumplir todavía ESE rol
    —una entrenadora que pasó a recepción sigue trabajando acá y no tiene que
    aparecer en el selector de entrenadores—. Ofrecer a cualquiera de los dos
    haría que el formulario permita asignarle trabajo nuevo a alguien que no
    lo va a hacer.
    """
    filas = (
        db.query(clase)
        .join(Empleado, clase.id_empleado == Empleado.id_empleado)
        .filter(Empleado.activo == True,  # noqa: E712
                clase.activo == True)     # noqa: E712
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

    Un Entrenador logueado recibe SÓLO a sí mismo: no puede crear rutinas a
    nombre de otro ni asignarle otro entrenador a un socio (el backend lo
    rechaza igual). Filtrarlo acá hace que los selectores de las dos apps
    dejen de ofrecer algo que después falla, sin tocar ninguna pantalla.
    """
    opciones = _opciones(db, Entrenador, "id_entrenador")
    propio = _entrenador_de_sesion(db, sesion)
    if propio is not None:
        opciones = [o for o in opciones if o.id == propio.id_entrenador]
    return opciones


@router.get("/nutricionistas", response_model=list[ProfesionalOpcion])
def listar_nutricionistas(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.NUTRICION)),
):
    """
    Espejo del anterior, para el formulario de dietas: una Nutricionista
    logueada recibe SÓLO a sí misma, porque el alta de dieta rechaza (403) una
    a nombre de otro. Sin este recorte la PWA le preseleccionaba al primero de
    la lista, y con más de una nutricionista la dieta nueva podía fallar.
    """
    opciones = _opciones(db, Nutricionista, "id_nutricionista")
    propio = _nutricionista_de_sesion(db, sesion)
    if propio is not None:
        opciones = [o for o in opciones if o.id == propio.id_nutricionista]
    return opciones


@router.get("/franjas", response_model=list[FranjaLaboralOut])
def listar_franjas(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.PERSONAL)),
):
    """
    Catálogo de franjas laborales, para el selector de turno del recepcionista
    en el alta/edición de personal. Reemplaza al viejo varchar `turno_laboral`.

    Va ANTES de la ruta /{id_empleado} a propósito: FastAPI resuelve por orden
    de declaración, y si estuviera después leería "franjas" como un id.
    """
    franjas = (db.query(FranjaLaboral)
               .filter(FranjaLaboral.activo.is_(True))
               .order_by(FranjaLaboral.id_franja_laboral)
               .all())
    return [FranjaLaboralOut.model_validate(f) for f in franjas]


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
    Edita un empleado, incluidos sus roles.

    `datos.roles` es el conjunto completo que tiene que quedar prendido. Los
    que falten se crean o se reactivan y los que no vengan se apagan, sin
    borrar ninguna fila — ver `_aplicar_roles`. Ya no hay 409 por cambio de
    rol: nada se borra, así que no hay historial que se pueda romper.
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

    # --- Los roles ----------------------------------------------------------
    _aplicar_roles(db, empleado, datos.roles, datos)

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

    # LAS HABILITACIONES DEL PROFESOR NO SE TOCAN, Y ES A PROPÓSITO
    # -------------------------------------------------------------
    # Hasta el 2026-09-29 acá se BORRABAN las filas de Profesor_Actividad, con
    # un motivo razonable —que no siguiera figurando en "quiénes pueden dictar
    # Yoga"— y dos problemas.
    #
    # El primero: no funcionaba. Esa fila es el destino de las FK compuestas
    # fk_horario_profesor_habilitado y fk_turno_profesor_habilitado, que no
    # miran fechas. Apenas el profesor había dictado una clase, el DELETE
    # fallaba y la baja entera se deshacía con un 500 sin explicación. Todo
    # profesor con un turno a su nombre era imposible de dar de baja.
    #
    # El segundo: era innecesario. Los cuatro lugares que ofrecen profesores ya
    # filtran por Empleado.activo —listar_profesores y listar_todos_los_profesores
    # de actividades.py, las dos validaciones del profesor a cargo de un horario,
    # y asignar_profesor, que además lo rechaza con 409—, así que un empleado de
    # baja ya no figura en ninguna lista sin borrarle nada.
    #
    # Dejarlas en pie tiene además el efecto que el gimnasio espera: cuando la
    # persona vuelve (reactivar_empleado), sus habilitaciones vuelven con ella.
    # Antes había que asignárselas de nuevo actividad por actividad.
    #
    # Sacarlo de UNA actividad sigue siendo una decisión aparte y explícita, y
    # ésa apaga la fila: desasignar_profesor en actividades.py.

    # Si entrenaba socios, deja de estar a cargo de ellos. Sin esto el socio
    # seguía viendo en "Mi entrenador" a alguien que ya no trabaja acá (el
    # portal lista las asignaciones ACTIVA), y la ficha del socio lo seguía
    # dando como su entrenador.
    #
    # Se FINALIZAN, no se borran: es el mismo cierre que finalizar_asignacion
    # en routers/socios.py, y el historial de quién entrenó a quién queda.
    # Reactivar al entrenador NO las reabre: a la vuelta, a quién entrena se
    # decide de nuevo, que es lo que el gimnasio haría de verdad.
    if rol_activo(empleado.entrenador):
        (db.query(AsignacionEntrenador)
         .filter(AsignacionEntrenador.id_entrenador == empleado.entrenador.id_entrenador,
                 AsignacionEntrenador.estado == "ACTIVA")
         .update({AsignacionEntrenador.estado: "FINALIZADA",
                  AsignacionEntrenador.fecha_fin: date.today()},
                 synchronize_session=False))

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
