"""
routers/rutinas.py
------------------
Catálogo de ejercicios, plantillas de rutina y su asignación a socios.

TRES NIVELES, Y POR QUÉ NO SON UNO SOLO
---------------------------------------
    Ejercicio          'Press de banca' — existe UNA vez en todo el sistema
    Rutina             plantilla que arma un entrenador
    Asignacion_Rutina  qué socio sigue qué rutina, desde cuándo

La tentación es guardar los ejercicios adentro de cada rutina y la rutina
adentro de cada socio. Los dos atajos duelen rápido:

  - Ejercicios embebidos: 'Sentadilla' quedaría escrito distinto en cada
    rutina ('sentadilla', 'Sentadillas', 'Sentadilla libre') y no habría forma
    de responder "¿qué rutinas usan este ejercicio?".

  - Rutinas embebidas en el socio: asignar la misma rutina a quince personas
    la duplicaría quince veces, y corregir una serie obligaría a editarlas
    todas. Con la tabla de asignación, la rutina es una y cada socio tiene sus
    propias fechas.

QUIÉN PUEDE QUÉ
---------------
La sección Rutinas está en TOTAL para Dueño, Recepcionista y Entrenador, y en
LECTURA para el Nutricionista — que necesita ver la rutina de un socio para no
armarle una dieta que la contradiga, pero no tocarla.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import (
    AsignacionRutina, Ejercicio, Empleado, Entrenador, Persona, Rutina,
    RutinaEjercicio, Socio,
)
from permisos import Acceso, Accion, Seccion
from schemas import (
    AsignacionRutinaOut, AsignarRutinaRequest, EjercicioCrear, EjercicioOut,
    RutinaCrear, RutinaEditarRequest, RutinaEjercicioOut, RutinaOut,
)
from security import Sesion, requiere_accion, requiere_seccion

router = APIRouter(prefix="/rutinas", tags=["Rutinas"])


# =============================================================================
# HELPERS
# =============================================================================

def _nombre_entrenador(entrenador: Entrenador | None) -> str:
    """
    Recorre Entrenador -> Empleado -> Persona. Devuelve 'Sin asignar' en vez
    de None porque este texto va directo a la pantalla, y un None se
    renderizaría como 'null' o rompería el layout.
    """
    if entrenador is None or entrenador.empleado is None:
        return "Sin asignar"
    persona = entrenador.empleado.persona
    return persona.nombre_completo if persona else "Sin asignar"


def _entrenador_de_sesion(db: Session, sesion: Sesion) -> Entrenador | None:
    """
    La ficha de Entrenador de quien está logueado, si la tiene.

    El Dueño y el Recepcionista pueden crear rutinas sin ser entrenadores, así
    que esto puede devolver None legítimamente — quien llama decide qué hacer.
    """
    empleado = (
        db.query(Empleado)
        .filter(Empleado.id_persona == sesion.id_persona)
        .first()
    )
    return empleado.entrenador if empleado else None


def _resolver_entrenador(db: Session, sesion: Sesion, id_pedido: int | None) -> Entrenador:
    """
    Decide a nombre de quién queda la rutina.

    La regla, y por qué no es la misma para todos:

      - Si quien pide ES entrenador, la rutina es suya. Mandar el id de otro
        se rechaza con 403: sería crear rutinas a nombre ajeno, y el historial
        de quién armó qué dejaría de significar algo.

      - Si NO es entrenador (Dueño, Recepcionista), tiene que elegir uno.
        `Rutina.id_entrenador` es NOT NULL y ellos no tienen ficha de
        entrenador, así que sin elegir no hay a quién atribuirla. Para ellos
        elegir no es suplantar: es delegar, y tienen el permiso.
    """
    propio = _entrenador_de_sesion(db, sesion)

    if propio is not None:
        if id_pedido is not None and id_pedido != propio.id_entrenador:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No podés crear rutinas a nombre de otro entrenador.",
            )
        return propio

    if id_pedido is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Elegí el entrenador que va a quedar a cargo de la rutina.",
        )

    entrenador = db.get(Entrenador, id_pedido)
    if entrenador is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="El entrenador indicado no existe.")
    if entrenador.empleado is None or not entrenador.empleado.activo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ese entrenador está dado de baja. Elegí uno activo.",
        )
    return entrenador


def _a_rutina_out(rutina: Rutina, con_ejercicios: bool = True) -> RutinaOut:
    ejercicios = []
    if con_ejercicios:
        # Ordenado por día y después por orden: es como se lee la planilla en
        # el gimnasio, y dejarlo al orden de inserción daría una lista
        # arbitraria que el frontend tendría que reordenar.
        for re in sorted(rutina.ejercicios, key=lambda x: (x.dia, x.orden)):
            ejercicios.append(RutinaEjercicioOut(
                id_rutina_ejercicio=re.id_rutina_ejercicio,
                id_ejercicio=re.id_ejercicio,
                nombre_ejercicio=re.ejercicio.nombre if re.ejercicio else "?",
                grupo_muscular=re.ejercicio.grupo_muscular if re.ejercicio else "?",
                dia=re.dia,
                orden=re.orden,
                series=re.series,
                repeticiones=re.repeticiones,
                peso_sugerido=float(re.peso_sugerido) if re.peso_sugerido is not None else None,
                descanso_segundos=re.descanso_segundos,
                observaciones=re.observaciones,
            ))

    # id_entrenador NULL ⟺ rutina propia (crear_rutina siempre resuelve un
    # entrenador real, así que un NULL no puede venir de otro lado). El socio no
    # tiene por qué ver "Sin asignar": lee "Rutina propia".
    es_propia = rutina.id_entrenador is None

    return RutinaOut(
        id_rutina=rutina.id_rutina,
        id_entrenador=rutina.id_entrenador,
        entrenador="Rutina propia" if es_propia else _nombre_entrenador(rutina.entrenador),
        nombre=rutina.nombre,
        objetivo=rutina.objetivo,
        nivel=rutina.nivel,
        dias_por_semana=rutina.dias_por_semana,
        fecha_creacion=rutina.fecha_creacion,
        activo=bool(rutina.activo),
        asignados=sum(1 for a in rutina.asignaciones if a.estado == "ACTIVA"),
        ejercicios=ejercicios,
    )


def _rutina_del_staff(db: Session, id_rutina: int) -> Rutina:
    """
    Trae una rutina que el PERSONAL tiene derecho a ver, o 404.

    Una rutina propia de un socio (id_entrenador NULL) es invisible del lado del
    staff: se devuelve el MISMO 404 que si no existiera, a propósito. Un 403 —o
    cualquier mensaje distinto— confirmaría que el id existe y es de alguien,
    que es justo lo que no tiene que poder saberse desde acá. Así ningún
    endpoint del personal (obtener, asignar, editar, baja, reactivar) puede
    tocar ni enumerar la rutina propia de un socio.
    """
    rutina = db.get(Rutina, id_rutina)
    if rutina is None or rutina.id_entrenador is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La rutina no existe.")
    return rutina


# =============================================================================
# CATÁLOGO DE EJERCICIOS
# =============================================================================
# Va antes de /{id_rutina} para que FastAPI no intente leer "ejercicios" como
# si fuera un id.

@router.get("/ejercicios", response_model=list[EjercicioOut])
def listar_ejercicios(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.RUTINAS)),
):
    return db.query(Ejercicio).order_by(Ejercicio.grupo_muscular, Ejercicio.nombre).all()


@router.post("/ejercicios", response_model=EjercicioOut, status_code=status.HTTP_201_CREATED)
def crear_ejercicio(
    datos: EjercicioCrear,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.GESTION_RUTINAS)),
):
    """
    Agrega un ejercicio al catálogo compartido.

    El nombre es UNIQUE en el esquema: se chequea a mano para dar un mensaje
    claro en vez del error de restricción de PostgreSQL. Y es importante que
    lo sea — dos filas 'Sentadilla' partirían en dos el historial de ese
    ejercicio.
    """
    nombre = datos.nombre.strip()
    if db.query(Ejercicio).filter(Ejercicio.nombre.ilike(nombre)).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un ejercicio llamado '{nombre}'.",
        )

    ejercicio = Ejercicio(
        nombre=nombre,
        grupo_muscular=datos.grupo_muscular.strip(),
        descripcion=datos.descripcion,
        url_video=datos.url_video,
        requiere_maquina=datos.requiere_maquina,
    )
    db.add(ejercicio)
    db.commit()
    db.refresh(ejercicio)
    return ejercicio


# =============================================================================
# RUTINAS
# =============================================================================

@router.get("", response_model=list[RutinaOut])
def listar_rutinas(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.RUTINAS)),
):
    """
    Catálogo de rutinas. Sin los ejercicios: la grilla muestra tarjetas.

    Las rutinas PROPIAS de socios (id_entrenador NULL) NO están: el catálogo es
    lo que un entrenador elige para asignar, y una rutina propia no se le asigna
    a nadie más que a su autor. Que apareciera acá sería, literalmente, ofrecerla
    para asignar a terceros.
    """
    rutinas = (
        db.query(Rutina)
        .filter(Rutina.id_entrenador.isnot(None))
        .order_by(Rutina.id_rutina.desc())
        .all()
    )
    return [_a_rutina_out(r, con_ejercicios=False) for r in rutinas]


@router.get("/{id_rutina}", response_model=RutinaOut)
def obtener_rutina(
    id_rutina: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.RUTINAS)),
):
    """El detalle SÍ trae los ejercicios, ordenados por día y orden."""
    rutina = _rutina_del_staff(db, id_rutina)
    return _a_rutina_out(rutina)


@router.post("", response_model=RutinaOut, status_code=status.HTTP_201_CREATED)
def crear_rutina(
    datos: RutinaCrear,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.GESTION_RUTINAS)),
):
    """
    Crea una rutina con sus ejercicios, en una sola transacción.

    EL AUTOR SALE DE LA SESIÓN, no del cuerpo del pedido. Si viniera como
    parámetro, un entrenador podría crear rutinas a nombre de otro y el
    historial de quién armó qué dejaría de significar algo.

    Para el Dueño y el Recepcionista —que tienen el permiso pero no son
    entrenadores— hay que elegir un entrenador responsable, porque
    `Rutina.id_entrenador` es NOT NULL. Se usa el primero activo: la rutina
    tiene que quedar atribuida a alguien real del plantel.
    """
    entrenador = _resolver_entrenador(db, sesion, datos.id_entrenador)

    rutina = Rutina(
        id_entrenador=entrenador.id_entrenador,
        nombre=datos.nombre.strip(),
        objetivo=datos.objetivo,
        nivel=datos.nivel,
        dias_por_semana=datos.dias_por_semana,
        activo=True,
    )
    db.add(rutina)
    db.flush()

    # Se validan TODOS los ejercicios antes de insertar ninguno: si el tercero
    # no existe, no tiene que quedar una rutina con los dos primeros cargados.
    for item in datos.ejercicios:
        if db.get(Ejercicio, item.id_ejercicio) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El ejercicio con id {item.id_ejercicio} no existe.",
            )

    for item in datos.ejercicios:
        db.add(RutinaEjercicio(
            id_rutina=rutina.id_rutina,
            id_ejercicio=item.id_ejercicio,
            dia=item.dia,
            orden=item.orden,
            series=item.series,
            repeticiones=item.repeticiones,
            peso_sugerido=item.peso_sugerido,
            descanso_segundos=item.descanso_segundos,
            observaciones=item.observaciones,
        ))

    db.commit()
    db.refresh(rutina)
    return _a_rutina_out(rutina)


# =============================================================================
# ASIGNACIÓN A SOCIOS
# =============================================================================

@router.post("/{id_rutina}/asignar", response_model=AsignacionRutinaOut,
             status_code=status.HTTP_201_CREATED)
def asignar_rutina(
    id_rutina: int,
    datos: AsignarRutinaRequest,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.GESTION_RUTINAS)),
):
    """
    Le asigna la rutina a un socio.

    Si el socio ya tenía una rutina ACTIVA, se la FINALIZA en vez de rechazar
    el pedido. Nadie sigue dos rutinas de musculación a la vez, y en el
    mostrador lo que se quiere decir con "asignale esta" es "cambiale la que
    tenía" — hacer que falle obligaría a dar de baja la anterior a mano, y el
    día que alguien se olvide el socio queda con dos.

    La anterior NO se borra: queda como historial, con su estado en FINALIZADA.

    Una rutina propia (id_entrenador NULL) NO se puede asignar por acá: da 404,
    igual que una inexistente. Una rutina propia es de su autor y de nadie más;
    el personal no puede endosársela a otro socio.
    """
    rutina = _rutina_del_staff(db, id_rutina)

    socio = db.get(Socio, datos.id_socio)
    if socio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El socio no existe.")

    hoy = date.today()

    activas = (
        db.query(AsignacionRutina)
        .filter(AsignacionRutina.id_socio == socio.id_socio,
                AsignacionRutina.estado == "ACTIVA")
        .all()
    )
    for anterior in activas:
        if anterior.id_rutina == id_rutina:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{socio.persona.nombre_completo} ya tiene asignada esa rutina.",
            )
        anterior.estado = "FINALIZADA"
        anterior.fecha_fin = hoy

    # El flush NO es opcional desde la migración 009.
    #
    # Esa migración agregó un índice único parcial que impide dos asignaciones
    # ACTIVA por socio. Un índice parcial no puede ser DEFERRABLE en Postgres,
    # así que se evalúa al terminar cada sentencia — y SQLAlchemy ordena su
    # flush poniendo los INSERT ANTES que los UPDATE. Sin esto, la fila nueva
    # entraría mientras la anterior sigue ACTIVA y la base rechazaría una
    # reasignación que es perfectamente válida.
    #
    # Es el mismo tipo de detalle que ya mordió en promover_de_lista_de_espera:
    # la sesión tiene autoflush=False, así que nada llega a la base hasta que
    # se lo pide explícitamente.
    db.flush()

    asignacion = AsignacionRutina(
        id_socio=socio.id_socio,
        id_rutina=id_rutina,
        # id_entrenador ya no vive en la asignación: sale de Rutina.id_entrenador.
        fecha_inicio=datos.fecha_inicio or hoy,
        fecha_fin=datos.fecha_fin,
        estado="ACTIVA",
    )
    db.add(asignacion)
    db.commit()
    db.refresh(asignacion)

    return AsignacionRutinaOut(
        id_asignacion_rutina=asignacion.id_asignacion_rutina,
        id_socio=socio.id_socio,
        socio=socio.persona.nombre_completo,
        id_rutina=id_rutina,
        rutina=rutina.nombre,
        fecha_inicio=asignacion.fecha_inicio,
        fecha_fin=asignacion.fecha_fin,
        estado=asignacion.estado,
    )


@router.get("/asignaciones/socio/{id_socio}", response_model=list[AsignacionRutinaOut])
def rutinas_de_socio(
    id_socio: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.RUTINAS, Acceso.LECTURA)),
):
    """
    Historial de rutinas de un socio, la actual primero.

    Ojo: este endpoint es de la sección de GESTIÓN. El socio consultando SU
    propia rutina va por el portal (`mi-rutina`), que filtra por el id_socio
    firmado en su token y no acepta un id por parámetro — si aceptara uno,
    cualquier socio podría pedir la rutina de otro cambiando un número.

    Las rutinas PROPIAS del socio (id_entrenador NULL) quedan fuera también acá:
    son suyas y no parte del historial que gestiona el personal. El socio las ve
    por su portal; el staff, ni siquiera en el historial de asignaciones.
    """
    asignaciones = (
        db.query(AsignacionRutina)
        .join(Rutina, Rutina.id_rutina == AsignacionRutina.id_rutina)
        .filter(AsignacionRutina.id_socio == id_socio,
                Rutina.id_entrenador.isnot(None))
        .order_by(AsignacionRutina.fecha_inicio.desc())
        .all()
    )
    return [
        AsignacionRutinaOut(
            id_asignacion_rutina=a.id_asignacion_rutina,
            id_socio=a.id_socio,
            socio=a.socio.persona.nombre_completo if a.socio else "?",
            id_rutina=a.id_rutina,
            rutina=a.rutina.nombre if a.rutina else "?",
            fecha_inicio=a.fecha_inicio,
            fecha_fin=a.fecha_fin,
            estado=a.estado,
        )
        for a in asignaciones
    ]


# =============================================================================
# EDICIÓN Y BAJA
# =============================================================================

@router.put("/{id_rutina}", response_model=RutinaOut)
def editar_rutina(
    id_rutina: int,
    datos: RutinaEditarRequest,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.GESTION_RUTINAS)),
):
    """
    Edita los datos de la rutina. Los ejercicios se manejan aparte.

    Cambiar el entrenador a cargo sigue la misma regla que el alta: un
    entrenador no puede pasarle su rutina a otro ni quedarse con la de un
    colega; el Dueño y el Recepcionista sí pueden reasignarla — es lo que hace
    falta cuando alguien se va del gimnasio.
    """
    rutina = _rutina_del_staff(db, id_rutina)

    if datos.id_entrenador is not None and datos.id_entrenador != rutina.id_entrenador:
        rutina.id_entrenador = _resolver_entrenador(db, sesion, datos.id_entrenador).id_entrenador

    rutina.nombre = datos.nombre.strip()
    rutina.objetivo = datos.objetivo
    rutina.nivel = datos.nivel
    rutina.dias_por_semana = datos.dias_por_semana

    db.commit()
    db.refresh(rutina)
    return _a_rutina_out(rutina)


@router.post("/{id_rutina}/baja", response_model=RutinaOut)
def dar_de_baja_rutina(
    id_rutina: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.GESTION_RUTINAS)),
):
    """
    Desactiva una rutina del catálogo. Baja lógica: la fila queda.

    Borrarla rompería las asignaciones históricas —quedarían apuntando a una
    rutina inexistente— y con ellas el registro de qué entrenó cada socio.

    Los socios que la están siguiendo AHORA no se tocan: la rutina desactivada
    deja de ofrecerse para asignaciones nuevas, pero quien ya la tiene la
    termina. Cortársela de un día para el otro dejaría a alguien sin plan de
    entrenamiento sin que nadie lo decidiera.
    """
    rutina = _rutina_del_staff(db, id_rutina)
    if not rutina.activo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Esa rutina ya estaba desactivada.")

    rutina.activo = False
    db.commit()
    db.refresh(rutina)
    return _a_rutina_out(rutina)


@router.post("/{id_rutina}/reactivar", response_model=RutinaOut)
def reactivar_rutina(
    id_rutina: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.GESTION_RUTINAS)),
):
    rutina = _rutina_del_staff(db, id_rutina)
    if rutina.activo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Esa rutina ya estaba activa.")

    rutina.activo = True
    db.commit()
    db.refresh(rutina)
    return _a_rutina_out(rutina)
