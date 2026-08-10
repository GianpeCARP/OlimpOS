"""
routers/portal.py
-----------------
El portal del socio: las siete pantallas donde ve SUS propios datos.

LA REGLA QUE JUSTIFICA QUE ESTO SEA UN ROUTER APARTE
-----------------------------------------------------
Ningún endpoint de acá acepta un id de socio por parámetro. Todos usan
`sesion.id_socio`, que viene FIRMADO dentro del token.

La diferencia parece menor y es la más importante del archivo:

    GET /rutinas/asignaciones/socio/7   ← gestión: el staff pide la de otro
    GET /portal/mi-rutina               ← portal: solo puede ser la propia

Si el portal aceptara un id, cualquier socio podría leer la ficha médica, la
dieta o el estado de cuenta de otro cambiando un número en la URL. Con el id
en el token eso es imposible: el cliente no puede alterarlo sin invalidar la
firma.

Es exactamente lo que documenta el comentario de `LoginResultado.idSocio` en
la PWA: *"si cada pantalla hiciera la traversal persona -> socio por su
cuenta, alcanzaría con que una sola se olvidara de filtrar para que empiece a
mostrar datos de otro"*. Centralizarlo acá hace que ese olvido no sea
posible.

POR QUÉ NO SE REUSAN LOS ENDPOINTS DE GESTIÓN
---------------------------------------------
Se podría haber hecho que `/socios/{id}` devuelva la ficha y que un guard
verifique que el id coincide con el de la sesión. Se descartó por dos motivos:

  1. El guard habría que acordarse de ponerlo en cada endpoint nuevo. Acá la
     imposibilidad es estructural: no hay parámetro que manipular.
  2. El socio no necesita los mismos datos que el staff. Su ficha no lleva
     observaciones internas ni el legajo de quien lo atendió.

La auditoría del 2026-08-03 documentó qué pasaba sin esta separación: un
socio —incluso uno dado de baja— entraba y veía el DNI de todos los demás
socios y el legajo del personal.
"""

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import (
    AsignacionDieta, AsignacionRutina, Asistencia, Deuda, Membresia, Pago,
    Persona, RegistroSalud, Reserva, Socio, Telefono, Turno,
)
from permisos import Seccion
from schemas import (
    AsignacionDietaOut, AsignacionRutinaOut, AsistenciaOut, DietaOut,
    MedicionCrear, MedicionOut, MiComidaOut, MiCuotaOut, MiDeudaOut,
    MiDiaDeDietaOut, MiDietaOut, MiRutinaOut,
    MiPerfilEditarRequest, MiPerfilOut,
    MiProgresoOut, PagoOut, ReservaOut, RutinaOut,
)
from security import Sesion, requiere_seccion

router = APIRouter(prefix="/portal", tags=["Portal del socio"])

ULTIMOS_PAGOS = 10
ULTIMAS_ASISTENCIAS = 30


def _mi_socio(db: Session, sesion: Sesion) -> Socio:
    """
    El Socio de la sesión activa. Es la única puerta de entrada a los datos de
    este router.

    Falla con 403 —no 404— cuando la sesión no tiene id_socio: no es que el
    recurso no exista, es que quien pregunta no es socio. Un miembro del staff
    que no entrena en el gimnasio cae acá, y el mensaje se lo explica.
    """
    if sesion.id_socio is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu cuenta no está asociada a una ficha de socio.",
        )

    socio = db.get(Socio, sesion.id_socio)
    if socio is None:
        # El token trae un id que ya no existe: le borraron la ficha con la
        # sesión abierta. Se corta como si no fuera socio.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu ficha de socio ya no está disponible.",
        )
    return socio


def _armar_domicilio(persona) -> str | None:
    """
    "Av. Victorica 1450, Moreno". Saltea lo que falte sin dejar comas sueltas.

    Se arma en el servidor porque las tres pantallas que muestran un domicilio
    harían la misma cuenta, y una de ellas terminaría con ", Moreno" o
    "Av. Victorica," el día que falte un dato.
    """
    linea = " ".join(p for p in (persona.calle, persona.numero_calle) if p).strip()
    partes = [p for p in (linea, persona.localidad) if p]
    return ", ".join(partes) if partes else None


def _resumen_membresia(membresia) -> tuple[str, str, date | None]:
    """
    (plan, estado, vencimiento) de la membresía vigente.

    El estado sale con el mismo criterio que la sección Socios: 7 días de
    aviso antes de vencer. Se manda el texto ya resuelto para que la píldora
    no tenga que derivar la regla por su cuenta.
    """
    if membresia is None:
        return "Sin plan", "Sin membresía", None

    plan = membresia.tipo.nombre if membresia.tipo else "Sin plan"
    vence = membresia.fecha_vencimiento

    if vence is None:
        return plan, "Activo", None

    dias = (vence - date.today()).days
    if dias < 0:
        estado = "Vencido"
    elif dias <= 7:
        estado = "Por vencer"
    else:
        estado = "Activo"
    return plan, estado, vence


# =============================================================================
# MI PERFIL
# =============================================================================

@router.get("/mi-perfil", response_model=MiPerfilOut)
def mi_perfil(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.MI_PERFIL)),
):
    """Los datos propios del socio."""
    socio = _mi_socio(db, sesion)
    persona = socio.persona

    telefono = (
        db.query(Telefono)
        .filter(Telefono.id_persona == persona.id_persona)
        .order_by(Telefono.principal.desc())
        .first()
    )

    membresia = (
        db.query(Membresia)
        .filter(Membresia.id_socio == socio.id_socio, Membresia.estado == "ACTIVA")
        .order_by(Membresia.fecha_vencimiento.desc())
        .first()
    )
    plan, estado, vence = _resumen_membresia(membresia)

    return MiPerfilOut(
        id_socio=socio.id_socio,
        numero_socio=socio.numero_socio,
        dni=persona.dni,
        nombre=persona.nombre,
        apellido=persona.apellido,
        email=persona.email,
        telefono=telefono.numero if telefono else None,
        fecha_nacimiento=persona.fecha_nacimiento,
        fecha_alta=socio.fecha_alta,
        objetivo=socio.objetivo,
        sede=socio.sede.nombre if socio.sede else None,
        emergencia_nombre=persona.emergencia_nombre,
        emergencia_telefono=persona.emergencia_telefono,
        emergencia_parentesco=persona.emergencia_parentesco,
        domicilio=_armar_domicilio(persona),
        plan=plan,
        estado=estado,
        vencimiento=vence,
        # `observaciones` del Socio NO se expone: son notas internas del
        # personal sobre el socio, no información para él.
    )


# =============================================================================
# MI RUTINA
# =============================================================================

@router.get("/mi-rutina", response_model=MiRutinaOut | None)
def mi_rutina(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.MI_RUTINA)),
):
    """
    La rutina que está siguiendo ahora, con sus ejercicios.

    Devuelve None —no 404— si no tiene ninguna asignada. No tener rutina es un
    estado normal de un socio recién anotado, no un error: la vista muestra
    "todavía no tenés rutina asignada" en vez de una pantalla de error.
    """
    socio = _mi_socio(db, sesion)

    asignacion = (
        db.query(AsignacionRutina)
        .filter(AsignacionRutina.id_socio == socio.id_socio,
                AsignacionRutina.estado == "ACTIVA")
        .order_by(AsignacionRutina.fecha_inicio.desc())
        .first()
    )
    if asignacion is None or asignacion.rutina is None:
        return None

    # Se reusa el armador del router de gestión para los ejercicios —la rutina
    # es la misma— y se le suma lo que solo existe en la asignación.
    from routers.rutinas import _a_rutina_out
    base = _a_rutina_out(asignacion.rutina)

    return MiRutinaOut(
        id_rutina=base.id_rutina,
        nombre=base.nombre,
        nivel=base.nivel,
        objetivo=base.objetivo,
        dias_por_semana=base.dias_por_semana,
        entrenador=base.entrenador,
        # La rutina se dio de baja del catálogo pero la asignación sigue
        # activa: el socio la termina. La vista lo avisa.
        rutina_de_baja=not base.activo,
        fecha_inicio=asignacion.fecha_inicio,
        ejercicios=base.ejercicios,
    )


@router.get("/mi-rutina/historial", response_model=list[AsignacionRutinaOut])
def mi_historial_rutinas(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.MI_RUTINA)),
):
    """Las rutinas que siguió antes."""
    socio = _mi_socio(db, sesion)
    asignaciones = (
        db.query(AsignacionRutina)
        .filter(AsignacionRutina.id_socio == socio.id_socio)
        .order_by(AsignacionRutina.fecha_inicio.desc())
        .all()
    )
    return [
        AsignacionRutinaOut(
            id_asignacion_rutina=a.id_asignacion_rutina,
            id_socio=a.id_socio,
            socio=socio.persona.nombre_completo,
            id_rutina=a.id_rutina,
            rutina=a.rutina.nombre if a.rutina else "?",
            fecha_inicio=a.fecha_inicio,
            fecha_fin=a.fecha_fin,
            estado=a.estado,
        )
        for a in asignaciones
    ]


# =============================================================================
# MI DIETA
# =============================================================================

@router.get("/mi-dieta", response_model=MiDietaOut | None)
def mi_dieta(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.MI_DIETA)),
):
    """El plan alimentario vigente, con sus comidas. None si no tiene."""
    socio = _mi_socio(db, sesion)

    asignacion = (
        db.query(AsignacionDieta)
        .filter(AsignacionDieta.id_socio == socio.id_socio,
                AsignacionDieta.estado == "ACTIVA")
        .order_by(AsignacionDieta.fecha_inicio.desc())
        .first()
    )
    if asignacion is None or asignacion.dieta is None:
        return None

    dieta = asignacion.dieta

    from routers.nutricion import _clave_orden_comida, _nombre_nutricionista

    # Agrupadas por día, en el orden del día (Desayuno -> Almuerzo -> Cena).
    dias: list[MiDiaDeDietaOut] = []
    for c in sorted(dieta.comidas, key=_clave_orden_comida):
        numero = c.dia or 0
        grupo = next((g for g in dias if g.dia == numero), None)
        if grupo is None:
            grupo = MiDiaDeDietaOut(dia=numero, comidas=[], calorias_del_dia=None)
            dias.append(grupo)
        grupo.comidas.append(MiComidaOut(
            id_comida=c.id_comida, momento=c.momento,
            descripcion=c.descripcion, calorias=c.calorias,
        ))

    for grupo in dias:
        con_calorias = [c.calorias for c in grupo.comidas if c.calorias is not None]
        # None y no 0 cuando ninguna comida tiene calorías cargadas: un cero
        # diría "este día no se come nada", que es distinto de "no se sabe".
        grupo.calorias_del_dia = sum(con_calorias) if con_calorias else None

    return MiDietaOut(
        id_dieta=dieta.id_dieta,
        nombre=dieta.nombre,
        objetivo=dieta.objetivo,
        calorias_diarias=dieta.calorias_diarias,
        descripcion=dieta.descripcion,
        nutricionista=_nombre_nutricionista(dieta.nutricionista),
        dieta_de_baja=not bool(dieta.activo),
        # Estos dos vienen de la ASIGNACIÓN, no de la plantilla: son propios
        # del vínculo entre esta dieta y esta persona.
        fecha_inicio=asignacion.fecha_inicio,
        observaciones=asignacion.observaciones,
        dias=dias,
    )


@router.get("/mi-dieta/historial", response_model=list[AsignacionDietaOut])
def mi_historial_dietas(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.MI_DIETA)),
):
    socio = _mi_socio(db, sesion)
    asignaciones = (
        db.query(AsignacionDieta)
        .filter(AsignacionDieta.id_socio == socio.id_socio)
        .order_by(AsignacionDieta.fecha_inicio.desc())
        .all()
    )
    return [
        AsignacionDietaOut(
            id_asignacion_dieta=a.id_asignacion_dieta,
            id_socio=a.id_socio,
            socio=socio.persona.nombre_completo,
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
# MI CUOTA
# =============================================================================

@router.get("/mi-cuota", response_model=MiCuotaOut)
def mi_cuota(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.MI_CUOTA)),
):
    """
    Estado de la cuota y últimos pagos.

    Es el espejo de `/cobros/socio/{id}` pero SIN el id: el socio ve lo suyo y
    solo lo suyo. Tampoco ve el detalle de las deudas —solo el total— porque
    las observaciones de una deuda son notas internas del mostrador.
    """
    socio = _mi_socio(db, sesion)
    hoy = date.today()

    membresia = (
        db.query(Membresia)
        .filter(Membresia.id_socio == socio.id_socio, Membresia.estado == "ACTIVA")
        .order_by(Membresia.fecha_vencimiento.desc())
        .first()
    )

    deudas = (
        db.query(Deuda)
        .filter(Deuda.id_socio == socio.id_socio, Deuda.estado == "PENDIENTE")
        .all()
    )

    pagos = (
        db.query(Pago)
        .filter(Pago.id_socio == socio.id_socio, Pago.estado == "CONFIRMADO")
        .order_by(Pago.fecha_pago.desc())
        .limit(ULTIMOS_PAGOS)
        .all()
    )

    dias = None
    vence = None
    plan = None
    precio = None
    inicio = None
    if membresia:
        plan = membresia.tipo.nombre if membresia.tipo else None
        vence = membresia.fecha_vencimiento
        precio = float(membresia.precio_pactado)
        inicio = membresia.fecha_inicio
        if vence:
            dias = (vence - hoy).days

    # Mismo criterio que la sección Socios: se manda el texto ya resuelto para
    # que la píldora no derive la regla por su cuenta.
    if membresia is None:
        estado = "Sin membresía"
    elif dias is None:
        estado = "Activo"
    elif dias < 0:
        estado = "Vencido"
    elif dias <= 7:
        estado = "Por vencer"
    else:
        estado = "Activo"

    return MiCuotaOut(
        tiene_membresia=membresia is not None,
        al_dia=bool(membresia) and not deudas and (dias is None or dias >= 0),
        plan=plan,
        estado=estado,
        precio_pactado=precio,
        fecha_inicio=inicio,
        fecha_vencimiento=vence,
        dias_restantes=dias,
        deuda_total=float(sum(d.monto for d in deudas)),
        deudas=[
            MiDeudaOut(
                id_deuda=d.id_deuda,
                monto=float(d.monto),
                fecha_generacion=d.fecha_generacion,
                fecha_vencimiento=d.fecha_vencimiento,
                # Positivo = días que lleva vencida. Se calcula contra la fecha
                # del servidor, igual que los días restantes de la membresía.
                dias_de_atraso=(
                    (hoy - d.fecha_vencimiento).days if d.fecha_vencimiento else 0
                ),
                observaciones=d.observaciones,
            )
            for d in deudas
        ],
        ultimos_pagos=[
            PagoOut(
                id_pago=p.id_pago, id_socio=p.id_socio,
                socio=socio.persona.nombre_completo, monto=float(p.monto),
                metodo=p.metodo, fecha_pago=p.fecha_pago,
                periodo_desde=p.periodo_desde, periodo_hasta=p.periodo_hasta,
                estado=p.estado, numero_comprobante=p.numero_comprobante,
            )
            for p in pagos
        ],
    )


# =============================================================================
# MIS ACTIVIDADES
# =============================================================================

@router.get("/mis-actividades", response_model=list[ReservaOut])
def mis_reservas(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.MIS_ACTIVIDADES)),
):
    """
    Las clases a las que está anotado, de la más próxima a la más lejana.

    Solo las futuras y activas: lo que el socio necesita saber es a qué tiene
    que ir, no a qué fue el mes pasado.
    """
    socio = _mi_socio(db, sesion)
    hoy = date.today()

    reservas = (
        db.query(Reserva)
        .join(Turno, Reserva.id_turno == Turno.id_turno)
        .filter(Reserva.id_socio == socio.id_socio,
                Reserva.estado == "RESERVADA",
                Turno.fecha >= hoy)
        .order_by(Turno.fecha, Turno.hora)
        .all()
    )

    return [
        ReservaOut(
            id_reserva=r.id_reserva,
            id_turno=r.id_turno,
            id_socio=r.id_socio,
            socio=socio.persona.nombre_completo,
            actividad=r.turno.actividad.nombre if r.turno and r.turno.actividad else "?",
            fecha=r.turno.fecha,
            hora=r.turno.hora,
            estado=r.estado,
            es_clase_suelta=bool(r.es_clase_suelta),
            clases_restantes=(r.inscripcion.clases_restantes if r.inscripcion else None),
        )
        for r in reservas
    ]


# =============================================================================
# MI PROGRESO
# =============================================================================

@router.get("/mi-progreso/asistencias", response_model=list[AsistenciaOut])
def mis_asistencias(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.MI_PROGRESO)),
):
    """
    Sus últimos ingresos al gimnasio. Es la base del gráfico de regularidad:
    cuántas veces vino por semana.
    """
    socio = _mi_socio(db, sesion)
    asistencias = (
        db.query(Asistencia)
        .filter(Asistencia.id_socio == socio.id_socio)
        .order_by(Asistencia.fecha_hora_ingreso.desc())
        .limit(ULTIMAS_ASISTENCIAS)
        .all()
    )
    return [
        AsistenciaOut(
            id_asistencia=a.id_asistencia,
            id_socio=a.id_socio,
            socio=socio.persona.nombre_completo,
            numero_socio=socio.numero_socio,
            fecha_hora_ingreso=a.fecha_hora_ingreso,
            fecha_hora_egreso=a.fecha_hora_egreso,
            metodo_registro=a.metodo_registro,
        )
        for a in asistencias
    ]


@router.put("/mi-perfil", response_model=MiPerfilOut)
def editar_mi_perfil(
    datos: MiPerfilEditarRequest,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.MI_PERFIL)),
):
    """
    El socio edita su propio contacto.

    Solo email, teléfono y contacto de emergencia. NO el DNI, ni el nombre, ni
    la sede: eso lo administra el gimnasio y dejar que el socio lo cambie
    permitiría, por ejemplo, editarse el DNI para figurar como otra persona.

    Tampoco el objetivo ni las observaciones: el objetivo lo acuerda con su
    entrenador, y las observaciones son notas internas del personal sobre él.
    """
    socio = _mi_socio(db, sesion)
    persona = socio.persona

    if datos.email and datos.email != persona.email:
        choca = (db.query(Persona)
                 .filter(Persona.email == datos.email,
                         Persona.id_persona != persona.id_persona)
                 .first())
        if choca:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Ese email ya está registrado para otra persona.")
        persona.email = datos.email
    elif datos.email is None:
        persona.email = None

    persona.emergencia_nombre = datos.emergencia_nombre
    persona.emergencia_telefono = datos.emergencia_telefono
    persona.emergencia_parentesco = datos.emergencia_parentesco

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
    return mi_perfil(db=db, sesion=sesion)


# =============================================================================
# MI PROGRESO — mediciones
# =============================================================================

@router.get("/mi-progreso", response_model=MiProgresoOut)
def mi_progreso(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.MI_PROGRESO)),
):
    """
    La serie de mediciones más los números del encabezado.

    Los resúmenes (peso actual, variación, altura) los calcula el servidor
    aunque el cliente tenga la serie completa: son la misma cuenta hecha en un
    solo lugar. Si cada pantalla la hiciera por su cuenta —el gráfico, la
    tarjeta de resumen, un futuro informe— tres implementaciones podrían
    discrepar en el redondeo.
    """
    socio = _mi_socio(db, sesion)

    mediciones = (
        db.query(RegistroSalud)
        .filter(RegistroSalud.id_socio == socio.id_socio)
        .order_by(RegistroSalud.fecha)
        .all()
    )

    salida = [MedicionOut.model_validate(m) for m in mediciones]

    peso_actual = None
    variacion = None
    grasa_actual = None
    altura = None

    if mediciones:
        ultima = mediciones[-1]
        peso_actual = float(ultima.peso) if ultima.peso is not None else None
        grasa_actual = float(ultima.grasa_corporal) if ultima.grasa_corporal is not None else None

        # La altura puede no venir en la última medición: se busca la más
        # reciente que la tenga. Es un dato que casi no cambia y que el socio
        # suele cargar una sola vez.
        for m in reversed(mediciones):
            if m.altura is not None:
                altura = float(m.altura)
                break

        primera = mediciones[0]
        if peso_actual is not None and primera.peso is not None:
            variacion = round(peso_actual - float(primera.peso), 2)

    ya_cargo_hoy = any(m.fecha == date.today() for m in mediciones)

    return MiProgresoOut(
        mediciones=salida,
        peso_actual=peso_actual,
        variacion_peso=variacion,
        grasa_actual=grasa_actual,
        altura=altura,
        ya_cargo_hoy=ya_cargo_hoy,
    )


@router.post("/mi-progreso/mediciones", response_model=MedicionOut,
             status_code=status.HTTP_201_CREATED)
def cargar_medicion(
    datos: MedicionCrear,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.MI_PROGRESO)),
):
    """
    Carga la medición de hoy.

    Es UNA por día y la del día NO se pisa en silencio: si ya cargó, se
    rechaza y se explica. Sobrescribir le borraría al socio un dato que él
    mismo cargó, sin avisarle — y la serie perdería el registro de que ese día
    midió otra cosa.
    """
    socio = _mi_socio(db, sesion)
    hoy = date.today()

    ya = (db.query(RegistroSalud)
          .filter(RegistroSalud.id_socio == socio.id_socio, RegistroSalud.fecha == hoy)
          .first())
    if ya:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya cargaste una medición hoy. La próxima la podés cargar mañana.",
        )

    medicion = RegistroSalud(
        id_socio=socio.id_socio,
        fecha=hoy,
        peso=datos.peso,
        altura=datos.altura,
        grasa_corporal=datos.grasa_corporal,
        masa_muscular=datos.masa_muscular,
        observaciones=datos.observaciones,
    )
    db.add(medicion)
    db.commit()
    db.refresh(medicion)
    return MedicionOut.model_validate(medicion)
