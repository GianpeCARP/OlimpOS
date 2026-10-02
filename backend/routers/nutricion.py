"""
routers/nutricion.py
--------------------
Dietas y su asignación a socios.

ESPEJO ESTRUCTURAL DE RUTINAS
-----------------------------
    Dieta             plantilla que arma un nutricionista
    Comida            los platos de esa dieta, por día y momento
    Asignacion_Dieta  qué socio sigue qué dieta, desde cuándo

Vale la misma lógica que en rutinas.py: la dieta es una plantilla reutilizable
y la asignación es lo que la conecta con una persona. Asignar la misma dieta a
diez socios no la duplica diez veces.

La diferencia con Rutina es que Comida NO es un catálogo compartido como
Ejercicio: 'pollo con arroz' descripto en una dieta no es la misma entidad que
en otra, porque cambian las cantidades y el contexto. Por eso Comida cuelga
directo de Dieta y se borra con ella (cascade), mientras que un Ejercicio
sobrevive a las rutinas que lo usaban.

QUIÉN PUEDE QUÉ
---------------
TOTAL para Dueño, Recepcionista y Nutricionista. LECTURA para el Entrenador:
puede consultar la dieta de un socio para ver de quién es y no contradecirla
con la rutina, pero no darla de alta ni desligarla. Es la simetría exacta de
lo que pasa en Rutinas con el Nutricionista.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import (
    AsignacionDieta, CatalogoComida, Comida, Dieta, Empleado, Nutricionista, RegistroComida,
    Socio, rol_activo,
)
from permisos import Acceso, Accion, Seccion
from schemas import (
    AsignacionDietaOut, AsignarDietaRequest, CatalogoComidaCrear, CatalogoComidaOut,
    ComidaOut, DietaCrear, DietaEditarRequest, DietaOut,
)
from security import Sesion, requiere_accion, requiere_seccion

router = APIRouter(prefix="/nutricion", tags=["Nutrición"])


# Orden en que se muestran las comidas de un día. Ordenar alfabéticamente
# pondría Almuerzo antes que Desayuno, que no es como se come.
ORDEN_MOMENTOS = {
    "desayuno": 1, "media mañana": 2, "almuerzo": 3,
    "merienda": 4, "media tarde": 5, "cena": 6, "colación": 7,
}


def _clave_orden_comida(comida: Comida) -> tuple:
    momento = (comida.momento or "").strip().lower()
    return (comida.dia or 0, ORDEN_MOMENTOS.get(momento, 99), comida.id_comida)


def _nombre_nutricionista(nutri: Nutricionista | None) -> str:
    """Nutricionista -> Empleado -> Persona. 'Sin asignar' si falta algo."""
    if nutri is None or nutri.empleado is None:
        return "Sin asignar"
    persona = nutri.empleado.persona
    return persona.nombre_completo if persona else "Sin asignar"


def _nutricionista_de_sesion(db: Session, sesion: Sesion) -> Nutricionista | None:
    empleado = (
        db.query(Empleado)
        .filter(Empleado.id_persona == sesion.id_persona)
        .first()
    )
    # Ver el comentario gemelo en _entrenador_de_sesion (rutinas.py): un rol
    # apagado no es rol.
    return (empleado.nutricionista
            if empleado and rol_activo(empleado.nutricionista) else None)


def _resolver_nutricionista(db: Session, sesion: Sesion, id_pedido: int | None) -> Nutricionista:
    """
    Espejo exacto de _resolver_entrenador en rutinas.py: un nutricionista solo
    crea dietas a su nombre; el Dueño y el Recepcionista tienen que elegir a
    cargo de quién queda.
    """
    propio = _nutricionista_de_sesion(db, sesion)

    if propio is not None:
        if id_pedido is not None and id_pedido != propio.id_nutricionista:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No podés crear dietas a nombre de otro nutricionista.",
            )
        return propio

    if id_pedido is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Elegí el nutricionista que va a quedar a cargo de la dieta.",
        )

    nutri = db.get(Nutricionista, id_pedido)
    if nutri is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="El nutricionista indicado no existe.")
    if nutri.empleado is None or not nutri.empleado.activo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ese nutricionista está dado de baja. Elegí uno activo.",
        )
    return nutri


def _puede_editar(propio: Nutricionista | None, dieta: Dieta) -> bool:
    """
    Un Nutricionista sólo toca SUS planes; el Dueño y el Recepcionista, todos.
    Espejo de _puede_editar en rutinas.py.
    """
    return propio is None or dieta.id_nutricionista == propio.id_nutricionista


def _exigir_editable(db: Session, sesion: Sesion, dieta: Dieta) -> None:
    if not _puede_editar(_nutricionista_de_sesion(db, sesion), dieta):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ese plan es de otro nutricionista: podés verlo, no modificarlo.",
        )


def _agregar_comidas(db: Session, id_dieta: int, items) -> None:
    """
    Valida TODOS los platos del catálogo antes de insertar ninguno (si el
    tercero no existe no tiene que quedar medio plan cargado) y después
    inserta. Una comida lleva plato del catálogo o texto libre (ComidaCrear).
    """
    for c in items:
        if c.id_catalogo_comida is not None and db.get(CatalogoComida, c.id_catalogo_comida) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"El plato con id {c.id_catalogo_comida} no existe.")
    for c in items:
        db.add(Comida(
            id_dieta=id_dieta,
            dia=c.dia,
            momento=(c.momento or "").strip() or None,
            id_catalogo_comida=c.id_catalogo_comida,
            descripcion=None if c.id_catalogo_comida is not None else c.descripcion,
        ))


def _a_comida_out(c) -> ComidaOut:
    """
    El nombre/descripción/calorías salen del catálogo si la comida apunta a uno.
    En una dieta propia sin catálogo, el nombre es el texto libre `descripcion`
    de la Comida (sin calorías: eso va en Registro_Comida).
    """
    cat = c.catalogo
    return ComidaOut(
        id_comida=c.id_comida,
        dia=c.dia,
        momento=c.momento,
        id_catalogo_comida=c.id_catalogo_comida,
        nombre=cat.nombre if cat else (c.descripcion or "?"),
        descripcion=cat.descripcion if cat else None,
        calorias=cat.calorias if cat else None,
    )


def _a_dieta_out(dieta: Dieta, con_comidas: bool = True) -> DietaOut:
    comidas = []
    if con_comidas:
        comidas = [_a_comida_out(c)
                   for c in sorted(dieta.comidas, key=_clave_orden_comida)]

    # id_nutricionista NULL ⟺ dieta propia (crear_dieta siempre resuelve uno
    # real). El socio lee "Dieta propia", no "Sin asignar".
    es_propia = dieta.id_nutricionista is None

    return DietaOut(
        id_dieta=dieta.id_dieta,
        id_nutricionista=dieta.id_nutricionista,
        nutricionista="Dieta propia" if es_propia else _nombre_nutricionista(dieta.nutricionista),
        nombre=dieta.nombre,
        objetivo=dieta.objetivo,
        calorias_diarias=dieta.calorias_diarias,
        descripcion=dieta.descripcion,
        fecha_creacion=dieta.fecha_creacion,
        activo=bool(dieta.activo),
        asignados=sum(1 for a in dieta.asignaciones if a.estado == "ACTIVA"),
        comidas=comidas,
    )


def _dieta_del_staff(db: Session, id_dieta: int) -> Dieta:
    """
    Trae una dieta que el PERSONAL tiene derecho a ver, o 404. Una dieta propia
    de un socio (id_nutricionista NULL) es invisible del lado del staff: mismo
    404 que si no existiera, igual que _rutina_del_staff en rutinas.py.
    """
    dieta = db.get(Dieta, id_dieta)
    if dieta is None or dieta.id_nutricionista is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La dieta no existe.")
    return dieta


# =============================================================================
# DIETAS
# =============================================================================

@router.get("/catalogo-comidas", response_model=list[CatalogoComidaOut])
def listar_catalogo_comidas(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.NUTRICION)),
):
    """
    El catálogo de platos con el que el nutricionista arma las dietas. Cada
    Comida de una dieta apunta a uno de estos; el nombre y las calorías salen
    de acá y no se repiten en la Comida.

    Va ANTES de la ruta /{id_dieta} a propósito: FastAPI resuelve por orden de
    declaración, y si estuviera después leería "catalogo-comidas" como un id.
    """
    platos = (db.query(CatalogoComida)
              .filter(CatalogoComida.activo.is_(True))
              .order_by(CatalogoComida.nombre)
              .all())
    return [CatalogoComidaOut.model_validate(p) for p in platos]


@router.post("/catalogo-comidas", response_model=CatalogoComidaOut,
             status_code=status.HTTP_201_CREATED)
def crear_plato(
    datos: CatalogoComidaCrear,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.GESTION_DIETAS)),
):
    """
    Agrega un plato al catálogo. Antes no había forma de cargarlo desde
    ninguna app, y el catálogo es de donde salen nombre y calorías de cada
    comida de un plan.

    El nombre es UNIQUE: se chequea a mano para dar un mensaje claro en vez del
    error de restricción (mismo criterio que crear_ejercicio).
    """
    nombre = datos.nombre.strip()
    if db.query(CatalogoComida).filter(CatalogoComida.nombre.ilike(nombre)).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Ya existe un plato llamado '{nombre}'.")
    plato = CatalogoComida(nombre=nombre, descripcion=(datos.descripcion or "").strip() or None,
                           calorias=datos.calorias, activo=True)
    db.add(plato)
    db.commit()
    db.refresh(plato)
    return CatalogoComidaOut.model_validate(plato)


@router.get("", response_model=list[DietaOut])
def listar_dietas(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.NUTRICION)),
):
    """
    Catálogo. Sin las comidas: la grilla muestra tarjetas con macros.

    Las dietas PROPIAS de socios (id_nutricionista NULL) NO están: el catálogo
    es lo que un nutricionista elige para asignar, y una dieta propia es del
    socio y de nadie más.
    """
    dietas = (
        db.query(Dieta)
        .filter(Dieta.id_nutricionista.isnot(None))
        .order_by(Dieta.id_dieta.desc())
        .all()
    )
    propio = _nutricionista_de_sesion(db, sesion)
    salida = []
    for d in dietas:
        out = _a_dieta_out(d, con_comidas=False)
        out.puede_editar = _puede_editar(propio, d)
        salida.append(out)
    return salida


@router.get("/{id_dieta}", response_model=DietaOut)
def obtener_dieta(
    id_dieta: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.NUTRICION)),
):
    """El detalle trae las comidas ordenadas por día y momento del día."""
    dieta = _dieta_del_staff(db, id_dieta)
    out = _a_dieta_out(dieta)
    out.puede_editar = _puede_editar(_nutricionista_de_sesion(db, sesion), dieta)
    return out


@router.post("", response_model=DietaOut, status_code=status.HTTP_201_CREATED)
def crear_dieta(
    datos: DietaCrear,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.GESTION_DIETAS)),
):
    """
    Crea una dieta con sus comidas, en una transacción.

    A nombre de quién queda lo decide _resolver_nutricionista: si quien crea
    ES nutricionista, la dieta es suya; si no lo es (Dueño, Recepcionista),
    tiene que elegir a cargo de quién queda.
    """
    nutri = _resolver_nutricionista(db, sesion, datos.id_nutricionista)

    dieta = Dieta(
        id_nutricionista=nutri.id_nutricionista,
        nombre=datos.nombre.strip(),
        objetivo=datos.objetivo,
        calorias_diarias=datos.calorias_diarias,
        descripcion=datos.descripcion,
        activo=True,
    )
    db.add(dieta)
    db.flush()

    _agregar_comidas(db, dieta.id_dieta, datos.comidas)

    db.commit()
    db.refresh(dieta)
    return _a_dieta_out(dieta)


# =============================================================================
# ASIGNACIÓN A SOCIOS
# =============================================================================

@router.post("/{id_dieta}/asignar", response_model=AsignacionDietaOut,
             status_code=status.HTTP_201_CREATED)
def asignar_dieta(
    id_dieta: int,
    datos: AsignarDietaRequest,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.GESTION_DIETAS)),
):
    """
    Le asigna la dieta a un socio.

    Igual que con las rutinas: si ya tenía una ACTIVA se la finaliza en vez de
    rechazar el pedido. Nadie sigue dos planes alimentarios a la vez, y la
    anterior queda como historial con estado FINALIZADA, no se borra.

    Una dieta propia (id_nutricionista NULL) NO se puede asignar por acá: 404,
    igual que una inexistente. Es del socio y de nadie más.

    Y un plan DADO DE BAJA tampoco se asigna: ver el 409 de abajo.
    """
    dieta = _dieta_del_staff(db, id_dieta)
    _exigir_editable(db, sesion, dieta)

    # UN PLAN DADO DE BAJA NO SE ASIGNA
    # --------------------------------
    # Gemelo del control de asignar_rutina, y por el mismo motivo: hasta el
    # 2026-09-30 la baja de un plan prometía que "deja de figurar como activo" y
    # nada impedía asignarlo igual, ni acá ni en las tarjetas de las dos apps.
    #
    # 409 y no 400: el pedido está bien formado, lo que choca es el estado del
    # plan. El mensaje dice qué hacer, porque se reactiva desde la misma pantalla.
    if not dieta.activo:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ese plan está dado de baja: reactivalo antes de asignarlo.",
        )

    socio = db.get(Socio, datos.id_socio)
    if socio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El socio no existe.")

    hoy = date.today()

    activas = (
        db.query(AsignacionDieta)
        .filter(AsignacionDieta.id_socio == socio.id_socio,
                AsignacionDieta.estado == "ACTIVA")
        .all()
    )
    for anterior in activas:
        if anterior.id_dieta == id_dieta:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{socio.persona.nombre_completo} ya tiene asignada esa dieta.",
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

    asignacion = AsignacionDieta(
        id_socio=socio.id_socio,
        id_dieta=id_dieta,
        # id_nutricionista ya no vive en la asignación: sale de Dieta.
        fecha_inicio=datos.fecha_inicio or hoy,
        fecha_fin=datos.fecha_fin,
        estado="ACTIVA",
        observaciones=datos.observaciones,
    )
    db.add(asignacion)
    db.commit()
    db.refresh(asignacion)

    return AsignacionDietaOut(
        id_asignacion_dieta=asignacion.id_asignacion_dieta,
        id_socio=socio.id_socio,
        socio=socio.persona.nombre_completo,
        id_dieta=id_dieta,
        dieta=dieta.nombre,
        fecha_inicio=asignacion.fecha_inicio,
        fecha_fin=asignacion.fecha_fin,
        estado=asignacion.estado,
        observaciones=asignacion.observaciones,
    )


@router.get("/asignaciones/socio/{id_socio}", response_model=list[AsignacionDietaOut])
def dietas_de_socio(
    id_socio: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.NUTRICION, Acceso.LECTURA)),
):
    """
    Historial de dietas de un socio, la actual primero.

    Endpoint de GESTIÓN. El socio viendo SU dieta va por el portal
    (`mi-dieta`), que filtra por el id_socio firmado en su token en vez de
    aceptar uno por parámetro — si lo aceptara, cualquier socio podría leer la
    dieta de otro cambiando un número en la URL.

    Las dietas PROPIAS del socio (id_nutricionista NULL) quedan fuera también
    acá: son suyas, no parte del historial que gestiona el personal.
    """
    asignaciones = (
        db.query(AsignacionDieta)
        .join(Dieta, Dieta.id_dieta == AsignacionDieta.id_dieta)
        .filter(AsignacionDieta.id_socio == id_socio,
                Dieta.id_nutricionista.isnot(None))
        .order_by(AsignacionDieta.fecha_inicio.desc())
        .all()
    )
    return [
        AsignacionDietaOut(
            id_asignacion_dieta=a.id_asignacion_dieta,
            id_socio=a.id_socio,
            socio=a.socio.persona.nombre_completo if a.socio else "?",
            id_dieta=a.id_dieta,
            dieta=a.dieta.nombre if a.dieta else "?",
            fecha_inicio=a.fecha_inicio,
            fecha_fin=a.fecha_fin,
            estado=a.estado,
            observaciones=a.observaciones,
        )
        for a in asignaciones
    ]


# =============================================================================
# EDICIÓN Y BAJA
# =============================================================================

@router.put("/{id_dieta}", response_model=DietaOut)
def editar_dieta(
    id_dieta: int,
    datos: DietaEditarRequest,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.GESTION_DIETAS)),
):
    """
    Edita la dieta y, si vienen, REEMPLAZA sus comidas.

    Reemplazar la lista entera es lo que hace el formulario: se reacomoda el
    plan y se guarda cómo quedó. Nada apunta a Comida (Registro_Comida lleva el
    texto de lo comido, no una FK obligatoria al plan), así que borrar y volver
    a insertar no rompe historial. Espejo de editar_rutina.
    """
    dieta = _dieta_del_staff(db, id_dieta)
    _exigir_editable(db, sesion, dieta)

    if datos.id_nutricionista is not None and datos.id_nutricionista != dieta.id_nutricionista:
        nutri = _resolver_nutricionista(db, sesion, datos.id_nutricionista)
        dieta.id_nutricionista = nutri.id_nutricionista

    dieta.nombre = datos.nombre.strip()
    dieta.objetivo = datos.objetivo
    dieta.calorias_diarias = datos.calorias_diarias
    dieta.descripcion = datos.descripcion

    if datos.comidas is not None:
        # Registro_Comida.id_comida apunta a Comida (opcional, sin regla ON
        # DELETE): lo que un socio registró contra una comida del plan viejo
        # conserva su texto y sus macros, sólo pierde el vínculo. Sin esto,
        # borrar las comidas fallaría por la FK apenas alguien hubiera
        # registrado algo.
        ids_viejas = [c.id_comida for c in dieta.comidas]
        if ids_viejas:
            db.query(RegistroComida).filter(RegistroComida.id_comida.in_(ids_viejas)) \
                .update({RegistroComida.id_comida: None}, synchronize_session=False)
        db.query(Comida).filter(Comida.id_dieta == dieta.id_dieta).delete(synchronize_session=False)
        db.flush()
        _agregar_comidas(db, dieta.id_dieta, datos.comidas)

    db.commit()
    db.refresh(dieta)
    db.expire(dieta, ["comidas"])
    return _a_dieta_out(dieta)


@router.post("/{id_dieta}/baja", response_model=DietaOut)
def dar_de_baja_dieta(
    id_dieta: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.GESTION_DIETAS)),
):
    """
    Desactiva una dieta del catálogo. Baja lógica, mismo criterio que rutinas:
    los socios que la están siguiendo la terminan, pero deja de ofrecerse para
    asignaciones nuevas.
    """
    dieta = _dieta_del_staff(db, id_dieta)
    _exigir_editable(db, sesion, dieta)
    if not dieta.activo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Esa dieta ya estaba desactivada.")

    dieta.activo = False
    db.commit()
    db.refresh(dieta)
    return _a_dieta_out(dieta)


@router.post("/{id_dieta}/reactivar", response_model=DietaOut)
def reactivar_dieta(
    id_dieta: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.GESTION_DIETAS)),
):
    dieta = _dieta_del_staff(db, id_dieta)
    _exigir_editable(db, sesion, dieta)
    if dieta.activo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Esa dieta ya estaba activa.")

    dieta.activo = True
    db.commit()
    db.refresh(dieta)
    return _a_dieta_out(dieta)
