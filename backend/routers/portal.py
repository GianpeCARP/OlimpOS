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

from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Actividad, AsignacionDieta, AsignacionEntrenador, AsignacionRutina, Asistencia, Baja, Congelamiento, ContactoEmergencia, InscripcionActividad, Membresia, Pago, Patologia, Persona, RegistroSalud, Reserva, Socio, SocioPatologia, Telefono, Turno,
)
from permisos import Seccion
from schemas import (
    ActividadOut, AsignacionDietaOut, AsignacionEntrenadorOut, AsignacionRutinaOut, AsignarPatologiaRequest, AsistenciaOut, BajaPropiaRequest, ClaseSueltaResponse, ComprarClaseSueltaRequest, ComprarMiPlanRequest, ComprarPlanRequest, ComprarPlanResponse, CongelamientoOut, CongelarRequest, DietaOut, InscripcionOut, MedicionCrear, MedicionOut, MensajeResponse, MiComidaOut, MiCuotaOut, MiDiaDeDietaOut, MiDietaOut, MiPerfilEditarRequest, MiPerfilOut, MiProgresoOut, MiRutinaOut, PagoOut, PatologiaDeSocioOut, PatologiaOut, ReservaOut, RutinaOut, TurnoDisponibleOut,
)
from notificaciones import notificar_promocion_lista_espera
from turnos import ocupacion, promover_de_lista_de_espera
from security import Sesion, requiere_seccion
# El saldo del abono se deriva contando Reserva; la fórmula vive en el router
# de actividades y se importa para no duplicarla.
from routers.actividades import clases_restantes_de

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

    # La pausa gana sobre el cálculo de días, y tiene que decirlo ANTES de
    # mirar el vencimiento: mientras está congelada el reloj no corre, así
    # que "faltan 90 días" o "por vencer" serían igual de engañosos. Sin
    # esto, Mi perfil decía "Activo" mientras Mi cuota decía "En pausa" —
    # dos pantallas del mismo socio contándole cosas distintas.
    if membresia.estado == "SUSPENDIDA":
        return plan, "En pausa", vence

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

    emergencia = (
        db.query(ContactoEmergencia)
        .filter(ContactoEmergencia.id_persona == persona.id_persona)
        .order_by(ContactoEmergencia.principal.desc(), ContactoEmergencia.id_contacto_emergencia)
        .first()
    )

    # ACTIVA o SUSPENDIDA. Congelar deja la membresía en SUSPENDIDA para que
    # el fichaje y las reservas la rechacen, pero sigue siendo su membresía:
    # buscando sólo la ACTIVA, alguien que pausó su cuota veía su perfil como
    # si no tuviera ninguna.
    membresia = (
        db.query(Membresia)
        .filter(Membresia.id_socio == socio.id_socio,
                Membresia.estado.in_(["ACTIVA", "SUSPENDIDA"]))
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
        # El contacto de emergencia ya no vive inline en Persona: está en
        # Contacto_Emergencia (multivaluado). Para el perfil se muestra el
        # principal (o el primero que haya).
        emergencia_nombre=emergencia.nombre if emergencia else None,
        emergencia_telefono=emergencia.telefono if emergencia else None,
        emergencia_parentesco=emergencia.parentesco if emergencia else None,
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
        # ACTIVA o SUSPENDIDA. Incluir la suspendida NO es un descuido:
        # congelar la deja en SUSPENDIDA para que el fichaje y las reservas la
        # rechacen, pero para ESTA pantalla sigue existiendo. Buscando sólo la
        # ACTIVA, un socio que pausaba su cuota abría "Mi cuota" y leía "Sin
        # membresía" con el vencimiento en blanco — como si no tuviera nada,
        # en vez de como si estuviera de pausa.
        .filter(Membresia.id_socio == socio.id_socio,
                Membresia.estado.in_(["ACTIVA", "SUSPENDIDA"]))
        .order_by(Membresia.fecha_vencimiento.desc())
        .first()
    )

    pagos = (
        db.query(Pago)
        # Los PENDIENTE también, no sólo los confirmados.
        #
        # Con pago online un cobro puede quedar pendiente mientras Mercado
        # Pago lo procesa. Filtrando sólo CONFIRMADO, el socio pagaba con
        # tarjeta, volvía a la app y su historial no mostraba nada — sin forma
        # de saber si había salido. Ver un pago "Pendiente" es exactamente la
        # información que necesita para no pagar dos veces.
        #
        # Los CANCELADO quedan afuera a propósito: un pago rechazado no es
        # historial de nada, es ruido que preocupa sin motivo.
        .filter(Pago.id_socio == socio.id_socio,
                Pago.estado.in_(["CONFIRMADO", "PENDIENTE"]))
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
    elif membresia.estado == "SUSPENDIDA":
        # Gana sobre el cálculo de días: mientras está en pausa, cuántos días
        # faltan para el vencimiento es información engañosa — el reloj no
        # está corriendo. Lo que importa es que está pausada.
        estado = "En pausa"
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
        # "Al día" es tener membresía vigente sin vencer. No hay tabla Deuda:
        # el estado "debe" es derivable de esto mismo.
        al_dia=bool(membresia) and (dias is None or dias >= 0),
        plan=plan,
        estado=estado,
        precio_pactado=precio,
        fecha_inicio=inicio,
        fecha_vencimiento=vence,
        dias_restantes=dias,
        deuda_total=0.0,
        deudas=[],
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
            es_clase_suelta=(r.id_inscripcion is None),
            clases_restantes=clases_restantes_de(db, r.inscripcion),
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

    # Contacto de emergencia: ahora vive en Contacto_Emergencia. Se hace
    # upsert del principal. Si el socio manda nombre y teléfono, se crea o
    # actualiza esa fila; si limpia el nombre, no borramos el histórico.
    if datos.emergencia_nombre or datos.emergencia_telefono:
        emergencia = (db.query(ContactoEmergencia)
                      .filter(ContactoEmergencia.id_persona == persona.id_persona)
                      .order_by(ContactoEmergencia.principal.desc(),
                                ContactoEmergencia.id_contacto_emergencia)
                      .first())
        if emergencia is None:
            emergencia = ContactoEmergencia(id_persona=persona.id_persona,
                                            nombre=datos.emergencia_nombre or "",
                                            telefono=datos.emergencia_telefono or "",
                                            principal=True)
            db.add(emergencia)
        else:
            emergencia.nombre = datos.emergencia_nombre or emergencia.nombre
            emergencia.telefono = datos.emergencia_telefono or emergencia.telefono
        emergencia.parentesco = datos.emergencia_parentesco

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


def _a_reserva_out(db, reserva, turno) -> ReservaOut:
    """
    Arma la respuesta de una reserva del socio.

    Existe acá y no se reusa la de /actividades porque aquella arma el nombre
    del socio para que el mostrador sepa a quién anotó. Acá el socio ES quien
    pide: repetirle su propio nombre no aporta nada, y armarlo obliga a
    navegar Reserva -> Socio -> Persona en cada respuesta.
    """
    actividad = turno.actividad
    return ReservaOut(
        id_reserva=reserva.id_reserva,
        id_turno=turno.id_turno,
        id_socio=reserva.id_socio,
        socio=reserva.socio.persona.nombre_completo,
        actividad=actividad.nombre if actividad else "—",
        fecha=turno.fecha,
        hora=turno.hora,
        estado=reserva.estado,
        es_clase_suelta=(reserva.id_inscripcion is None),
        clases_restantes=clases_restantes_de(db, reserva.inscripcion),
    )

# =============================================================================
# AUTOGESTIÓN DE TURNOS
# =============================================================================
#
# El socio se anota y se baja solo. Es lo que más veces por semana le evitaba
# ir al mostrador: reservar una clase no requiere que nadie lo atienda.
#
# LA REGLA DE ORO DE TODO ESTE ARCHIVO, que acá importa más que en ningún otro
# lado: `id_socio` NUNCA viene del cuerpo del pedido. Sale de `sesion.id_socio`,
# que viaja firmado dentro del token. Los endpoints equivalentes de
# /actividades sí lo reciben —los usa el personal para operar sobre terceros—
# y por eso están protegidos con acciones que un socio no tiene. Si acá se
# aceptara un id, cualquier socio podría anotar o bajar a otro.

@router.post("/mis-turnos/{id_turno}/reservar", response_model=ReservaOut,
             status_code=status.HTTP_201_CREATED)
def reservar_mi_turno(
    id_turno: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.MIS_TURNOS)),
):
    """
    Anota al socio de la sesión en una clase.

    Si el turno está completo NO falla: queda en lista de espera, y cuando
    alguien cancele el sistema lo promueve solo y le avisa. Esa es toda la
    diferencia entre tener que estar mirando la app por las dudas y no tener
    que hacer nada.
    """
    socio = _mi_socio(db, sesion)

    # with_for_update(): mismo lock que el endpoint del personal. Sin esto,
    # dos socios reservando el último lugar al mismo tiempo no se ven entre sí
    # —bajo READ COMMITTED cada uno ve la base como estaba al empezar— y los
    # dos entran. Acá importa más que en el mostrador: en el mostrador reserva
    # una persona por vez; en la app, veinte a la vez apenas se abre el cupo.
    turno = (db.query(Turno)
             .filter(Turno.id_turno == id_turno)
             .with_for_update()
             .first())
    if turno is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Esa clase no existe.")
    if turno.estado == "CANCELADO":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Esa clase está cancelada.")

    inicio = datetime.combine(turno.fecha, turno.hora)
    if inicio < datetime.now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esa clase ya empezó. Buscá una de las próximas.",
        )

    # Una sola reserva por socio y turno. El índice único de la base también lo
    # impide, pero un IntegrityError le llegaría al socio como un error genérico
    # de servidor en vez de explicarle que ya estaba anotado.
    ya = (db.query(Reserva)
          .filter(Reserva.id_turno == id_turno,
                  Reserva.id_socio == socio.id_socio,
                  Reserva.estado.in_(["RESERVADA", "EN_ESPERA"]))
          .first())
    if ya:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=("Ya estás anotado en esa clase."
                    if ya.estado == "RESERVADA"
                    else "Ya estás en la lista de espera de esa clase."),
        )

    # Cuota al día. Se valida acá y no sólo al entrar al gimnasio porque
    # ocupar un lugar es tomar algo que otro socio podría usar: si después no
    # puede entrar, el lugar se desperdició.
    membresia = (db.query(Membresia)
                 .filter(Membresia.id_socio == socio.id_socio,
                         Membresia.estado == "ACTIVA")
                 .order_by(Membresia.fecha_vencimiento.desc())
                 .first())
    if membresia is None:
        # Distinguir "no tiene" de "está en pausa" no es cosmético: decirle
        # "renovala" a alguien que congeló su cuota lo haría PAGAR DE NUEVO
        # una membresía que ya tiene. Lo que necesita es reanudarla, y es
        # gratis.
        pausada = (db.query(Membresia)
                   .filter(Membresia.id_socio == socio.id_socio,
                           Membresia.estado == "SUSPENDIDA")
                   .first())
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=("Tu membresía está en pausa. Reanudala desde Mi cuota para "
                    "poder reservar — no hace falta que pagues de nuevo."
                    if pausada else
                    "No tenés una membresía activa. Renovala para poder reservar."),
        )
    if membresia.fecha_vencimiento and membresia.fecha_vencimiento < turno.fecha:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(f"Tu cuota vence el "
                    f"{membresia.fecha_vencimiento.strftime('%d/%m/%Y')} y esa "
                    f"clase es después. Renovala y reservá de nuevo."),
        )

    en_espera = ocupacion(db, id_turno) >= turno.cupo_maximo

    reserva = Reserva(
        id_turno=id_turno,
        id_socio=socio.id_socio,
        # Sin id_inscripcion: esta reserva del portal no descuenta de ningún
        # abono (igual que antes, cuando es_clase_suelta=False no consumía).
        fecha_reserva=datetime.now(),
        estado="EN_ESPERA" if en_espera else "RESERVADA",
    )
    db.add(reserva)
    db.commit()
    db.refresh(reserva)

    return _a_reserva_out(db, reserva, turno)


@router.post("/mis-turnos/{id_reserva}/cancelar", response_model=ReservaOut)
def cancelar_mi_turno(
    id_reserva: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.MIS_TURNOS)),
):
    """
    Baja al socio de una clase.

    Se verifica que la reserva SEA SUYA. Sin ese chequeo, cambiar el número en
    la URL bajaría a cualquier otro socio de su clase — el mismo agujero que
    la auditoría del 2026-08-03 cerró para las lecturas, que acá sería peor
    porque además modifica.

    Cancelar libera el lugar y dispara la promoción de la lista de espera en
    la misma transacción: el que estaba primero entra sin que nadie haga nada.
    """
    reserva = db.get(Reserva, id_reserva)
    if reserva is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Esa reserva no existe.")

    socio = _mi_socio(db, sesion)
    if reserva.id_socio != socio.id_socio:
        # 404 y no 403: un 403 confirmaría que esa reserva existe y es de otro.
        # No hay motivo para que un socio pueda averiguar eso probando números.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Esa reserva no existe.")

    if reserva.estado not in ("RESERVADA", "EN_ESPERA"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Esa reserva ya estaba cancelada.")

    estaba_en_espera = reserva.estado == "EN_ESPERA"
    turno = reserva.turno
    actividad = turno.actividad

    # La anticipación que exige la actividad. Cancelar sobre la hora deja un
    # lugar que ya nadie va a poder usar, así que si tenía abono pierde la
    # clase igual. La regla es de la actividad y no global: avisar con 2 horas
    # puede estar bien para spinning y ser poco para una clase personalizada.
    horas_de_aviso = (datetime.combine(turno.fecha, turno.hora)
                      - datetime.now()).total_seconds() / 3600
    a_tiempo = horas_de_aviso >= (actividad.horas_anticipacion_cancelacion or 0)

    reserva.estado = "CANCELADA_SOCIO"
    reserva.fecha_cancelacion = datetime.now()

    # El saldo del abono se cuenta contando Reserva: al cancelar, esta reserva
    # deja de contar y la clase se libera sola. `a_tiempo` se conserva para la
    # lista de espera y el criterio de devolución, no para tocar un contador.

    promovido = None
    if not estaba_en_espera:
        promovido = promover_de_lista_de_espera(db, turno.id_turno)

    db.commit()
    db.refresh(reserva)

    if promovido is not None:
        db.refresh(promovido)
        notificar_promocion_lista_espera(promovido, turno, actividad)

    return _a_reserva_out(db, reserva, turno)


@router.get("/mis-turnos/disponibles", response_model=list[TurnoDisponibleOut])
def turnos_disponibles(
    dias: int = 14,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.MIS_TURNOS)),
):
    """
    Las clases a las que el socio se puede anotar.

    Devuelve también las LLENAS, marcadas como tales y con cuántos hay
    esperando. Esconderlas sería peor: el socio no sabría que existe la clase,
    y la lista de espera —que es justamente para eso— no la usaría nadie.

    Se marca `ya_anotado` para que la app pueda mostrar "cancelar" en vez de
    "reservar" sin tener que cruzar dos listas del lado del cliente.
    """
    socio = _mi_socio(db, sesion)
    ahora = datetime.now()
    hasta = ahora.date() + timedelta(days=dias)

    filas = (db.query(Turno, Actividad)
             .join(Actividad, Actividad.id_actividad == Turno.id_actividad)
             .filter(Turno.fecha >= ahora.date(),
                     Turno.fecha <= hasta,
                     Turno.estado == "HABILITADO")
             .order_by(Turno.fecha, Turno.hora)
             .all())

    # Las reservas propias, de una sola consulta: preguntarlo por turno serían
    # tantas consultas como clases haya en dos semanas.
    mias = {
        r.id_turno: r
        for r in db.query(Reserva).filter(
            Reserva.id_socio == socio.id_socio,
            Reserva.estado.in_(["RESERVADA", "EN_ESPERA"]),
        ).all()
    }

    salida = []
    for turno, actividad in filas:
        if datetime.combine(turno.fecha, turno.hora) < ahora:
            continue
        ocupados = ocupacion(db, turno.id_turno)
        propia = mias.get(turno.id_turno)
        salida.append(TurnoDisponibleOut(
            id_turno=turno.id_turno,
            actividad=actividad.nombre,
            fecha=turno.fecha,
            hora=turno.hora,
            cupo_maximo=turno.cupo_maximo,
            ocupados=ocupados,
            lugares_libres=max(0, turno.cupo_maximo - ocupados),
            en_espera=(db.query(func.count(Reserva.id_reserva))
                       .filter(Reserva.id_turno == turno.id_turno,
                               Reserva.estado == "EN_ESPERA")
                       .scalar()) or 0,
            profesor=(turno.profesor.empleado.persona.nombre_completo
                      if turno.profesor else None),
            minutos_tolerancia=actividad.minutos_tolerancia,
            horas_anticipacion_cancelacion=actividad.horas_anticipacion_cancelacion,
            ya_anotado=propia is not None,
            mi_estado=(propia.estado if propia else None),
            id_mi_reserva=(propia.id_reserva if propia else None),
        ))
    return salida


# =============================================================================
# LOS MENSAJES, SEGÚN QUIÉN LOS LEE
# =============================================================================
#
# Los endpoints de /actividades redactan para el MOSTRADOR: hablan del socio
# en tercera persona ("Ana Test compró 2 por semana") y le dan órdenes al
# operador ("Renovale la cuota primero"). Está bien: ahí quien lee es alguien
# que opera sobre la ficha de otra persona.
#
# Cuando el que lee es el socio, esos mismos textos se leen mal. Ve su propio
# nombre en tercera persona, como si el sistema le estuviera hablando a
# alguien más, y recibe instrucciones dirigidas a otro. Es chico y es
# exactamente lo que hace que una app se sienta ajena.
#
# Se resuelve traduciendo ACÁ y no cambiando los endpoints originales: las
# REGLAS se comparten (esa fue la decisión al delegar), los TEXTOS no tienen
# por qué. Y así el mostrador sigue leyendo lo suyo sin enterarse.
#
# La traducción es una lista explícita y no una regex general sobre el nombre:
# reemplazar el nombre a ciegas produce frases rotas ("de Ana Test" -> "de
# vos"), y una lista corta que cubre los casos reales es más honesta que un
# reemplazo mágico que a veces acierta.

def _para_el_socio(texto: str, nombre: str) -> str:
    """
    Reescribe en segunda persona un mensaje redactado para el mostrador.

    Si no reconoce el patrón devuelve el texto tal cual. Es deliberado: un
    mensaje en tercera persona se lee raro, pero un mensaje mutilado por una
    sustitución que salió mal se lee peor — y podría cambiarle el sentido.
    """
    if not texto:
        return texto

    reemplazos = [
        (f"La membresía de {nombre} vence", "Tu cuota vence"),
        (f"La membresía de {nombre}", "Tu cuota"),
        (f"{nombre} ya tiene", "Ya tenés"),
        (f"{nombre} no tiene", "No tenés"),
        (f"{nombre} tiene", "Tenés"),
        (f"{nombre} compró", "Compraste"),
        (f"{nombre} ya está", "Ya estás"),
        (f"{nombre} está", "Estás"),
        (f"a {nombre}", "a vos"),
        # Va antes que el genérico: después de "Tu cuota vence el X", decir
        # "Renová tu cuota" repite el sujeto. "Renovala" ya se entiende.
        ("Renovale la cuota primero", "Renovala primero"),
        ("Renovale la cuota", "Renová tu cuota"),
        ("Renovale", "Renová"),
        ("Cobrale", "Pagá"),
        ("Regularizá su deuda", "Regularizá tu deuda"),
        ("su deuda", "tu deuda"),
        ("su cuota", "tu cuota"),
        ("Extendele", "Extendé"),
    ]
    for viejo, nuevo in reemplazos:
        texto = texto.replace(viejo, nuevo)
    return texto


def _traducir_error(e: HTTPException, nombre: str) -> HTTPException:
    """El mismo rechazo, redactado para quien lo va a leer."""
    if isinstance(e.detail, str):
        return HTTPException(status_code=e.status_code,
                             detail=_para_el_socio(e.detail, nombre))
    return e

# =============================================================================
# COMPRAS DEL SOCIO
# =============================================================================
#
# Comprar un abono o una clase suelta sin pasar por el mostrador.
#
# ESTOS ENDPOINTS NO REIMPLEMENTAN LAS REGLAS: llaman a los del personal.
#
# Comprar un abono valida cosas que costaron trabajo y que están documentadas
# en /actividades: que la membresía cubra el mes entero del abono (REGLA 1),
# que el socio no tenga deudas (REGLA 8), que el plan esté activo, y el cálculo
# de vencimiento con meses calendario y no de 30 días. Copiar todo eso acá
# significaría dos versiones de las mismas reglas, y en algún momento una de
# las dos se corrige y la otra no — con el resultado de que el socio puede
# comprar desde la app algo que el mostrador le rechazaría, o al revés.
#
# Lo único que cambia entre las dos puertas es DE DÓNDE SALE EL id_socio: del
# cuerpo cuando lo opera el personal (que actúa sobre terceros), del token
# firmado cuando lo hace el socio. Esa diferencia es exactamente la que
# justifica que sean dos endpoints y no uno con un parámetro opcional: un
# id_socio opcional en el endpoint del personal sería un id_socio que un socio
# podría mandar.

@router.post("/mis-actividades/planes/{id_plan}/comprar",
             response_model=ComprarPlanResponse,
             status_code=status.HTTP_201_CREATED)
def comprar_mi_plan(
    id_plan: int,
    datos: ComprarMiPlanRequest,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.MIS_ACTIVIDADES)),
):
    """
    El socio compra un abono para sí mismo.

    Si el backend rechaza —cuota que no cubre el mes, una deuda—, el mensaje
    de error ya explica cuál de las reglas falló y qué hacer. Ese texto está
    escrito para que lo lea el socio, no para que un programador lo depure.
    """
    from routers.actividades import comprar_plan

    socio = _mi_socio(db, sesion)
    nombre = socio.persona.nombre_completo
    try:
        salida = comprar_plan(
            id_plan=id_plan,
            datos=ComprarPlanRequest(id_socio=socio.id_socio, metodo=datos.metodo),
            db=db,
            sesion=sesion,
        )
    except HTTPException as e:
        raise _traducir_error(e, nombre) from e

    salida.mensaje = _para_el_socio(salida.mensaje, nombre)
    return salida


@router.post("/mis-turnos/{id_turno}/clase-suelta",
             response_model=ClaseSueltaResponse,
             status_code=status.HTTP_201_CREATED)
def comprar_mi_clase_suelta(
    id_turno: int,
    datos: ComprarMiPlanRequest,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.MIS_TURNOS)),
):
    """
    El socio paga una clase suelta y queda reservado en ese turno.

    Es la salida para quien no quiere un abono: viene una vez, paga esa vez.
    Sin esto, alguien que quiere probar una clase de Boxeo tiene que ir al
    mostrador — que es justo lo que este portal viene a evitar.
    """
    from routers.actividades import comprar_clase_suelta

    socio = _mi_socio(db, sesion)
    nombre = socio.persona.nombre_completo
    try:
        salida = comprar_clase_suelta(
            id_turno=id_turno,
            datos=ComprarClaseSueltaRequest(id_socio=socio.id_socio,
                                            metodo=datos.metodo),
            db=db,
            sesion=sesion,
        )
    except HTTPException as e:
        raise _traducir_error(e, nombre) from e

    salida.mensaje = _para_el_socio(salida.mensaje, nombre)
    return salida


@router.get("/mis-actividades/catalogo", response_model=list[ActividadOut])
def catalogo_para_el_socio(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.MIS_ACTIVIDADES)),
):
    """
    Las actividades con sus planes y precios, para que el socio elija.

    Sólo las ACTIVAS y sólo con sus planes activos: el catálogo del personal
    muestra también las dadas de baja para poder reactivarlas, y ofrecerle al
    socio comprar un plan discontinuado terminaría en un rechazo que no
    entendería.
    """
    actividades = (db.query(Actividad)
                   .filter(Actividad.activo.is_(True))
                   .order_by(Actividad.nombre)
                   .all())

    from routers.actividades import _a_actividad_out
    salida = []
    for a in actividades:
        out = _a_actividad_out(a)
        out.planes = [p for p in out.planes if p.activo]
        salida.append(out)
    return salida


def _dias_aplicados(c) -> int | None:
    """
    Días REALES que sumó (o va a sumar) un congelamiento. Ya no es una columna:
    se deriva de (fecha_reanudacion - fecha_inicio). None mientras sigue ACTIVO
    —todavía no se sabe cuántos van a ser—.
    """
    if c.fecha_reanudacion is None:
        return None
    return max(0, (c.fecha_reanudacion - c.fecha_inicio).days)


def _a_congelamiento_out(c) -> CongelamientoOut:
    """`dias_pedidos` va calculado: es lo que el socio pidió, no lo que usó."""
    return CongelamientoOut(
        id_congelamiento=c.id_congelamiento,
        fecha_inicio=c.fecha_inicio,
        fecha_fin=c.fecha_fin,
        fecha_reanudacion=c.fecha_reanudacion,
        dias_aplicados=_dias_aplicados(c),
        dias_pedidos=(c.fecha_fin - c.fecha_inicio).days,
        motivo=c.motivo,
        estado=c.estado,
    )

# =============================================================================
# MI MEMBRESÍA — congelar, reanudar, darse de baja
# =============================================================================

# Los topes del congelamiento. Están acá y no en la base porque son política
# comercial, no integridad: el día que el dueño quiera permitir 120 días al
# año, esto es lo que cambia. Ponerlos como CHECK obligaría a una migración
# para una decisión de negocio.
DIAS_MINIMO_CONGELAMIENTO = 7      # menos que una semana no vale la burocracia
DIAS_MAXIMO_POR_VEZ = 90

# El tope acumulado y la ventana en la que se mide.
#
# LA VENTANA ES MÓVIL —los últimos 365 días— Y NO EL AÑO CALENDARIO, y ese
# cambio cierra un agujero real. Con año calendario, alguien que congelaba el
# 1 de diciembre consumía el cupo de ESE año; el 2 de enero el contador
# arrancaba de cero y podía pedir otros 90. Resultado: 180 días corridos
# congelado, sin romper ninguna regla.
#
# El 31 de diciembre no significa nada para el negocio: lo que el gimnasio
# quiere limitar es cuánto tiempo puede estar pausado alguien en un período
# razonable, y eso no se reinicia porque cambie el almanaque.
#
# El costo de esto para el gimnasio es concreto: 90 días de pausa son 3
# renovaciones menos al año (9 en vez de 12), o sea un 25% menos de
# facturación de ese socio. Se acepta porque la alternativa a congelar no es
# "sigue pagando sin venir", es que se dé de baja — y ahí se pierde el 100%.
DIAS_MAXIMO_EN_VENTANA = 90
VENTANA_CONGELAMIENTO_DIAS = 365


def _dias_congelados_en_ventana(db: Session, id_socio: int, hoy: date) -> int:
    """
    Días ya consumidos en los últimos VENTANA_CONGELAMIENTO_DIAS.

    Cuenta `dias_aplicados` —los días REALES que se sumaron al vencimiento— y
    no los pedidos. Alguien que pidió 30 y volvió a los 10 gastó 10 de su
    cupo, no 30: sería injusto cobrarle días que no usó.

    Sólo mira los FINALIZADO. Los ACTIVO no se cuentan porque todavía no se
    sabe cuántos días van a ser —eso se decide al reanudar— y además no hacen
    falta: no se puede pedir una pausa nueva teniendo una activa, así que
    nunca hay una sin contar al momento de validar.

    Vive en una función y no dentro del endpoint para que la regla exista en
    UN solo lugar: la valida el POST de congelar y la puede consultar
    cualquier pantalla que quiera mostrar el saldo.
    """
    desde = hoy - timedelta(days=VENTANA_CONGELAMIENTO_DIAS)
    # dias_aplicados ya no es una columna: se deriva de las fechas, así que la
    # suma se hace en Python. Además sólo cuentan los de origen SOCIO: los que
    # impuso el gimnasio (cierre, refacción) NO gastan el cupo voluntario.
    congelamientos = (
        db.query(Congelamiento)
        .join(Membresia, Congelamiento.id_membresia == Membresia.id_membresia)
        .filter(Membresia.id_socio == id_socio,
                Congelamiento.estado == "FINALIZADO",
                Congelamiento.origen == "SOCIO",
                Congelamiento.fecha_inicio >= desde)
        .all()
    )
    return sum((_dias_aplicados(c) or 0) for c in congelamientos)


def _congelamiento_vigente(db: Session, id_socio: int) -> Congelamiento | None:
    """
    El congelamiento activo, si lo hay — y lo cierra si ya se le pasó la fecha.

    Un congelamiento que llega a su fecha_fin sin que nadie lo reanude se
    cierra SOLO, acá, al leerlo. Es la misma idea que el estado derivado de
    las reservas: si hiciera falta un proceso corriendo aparte para cerrarlos,
    ese proceso se cae o se atrasa y el socio queda congelado para siempre sin
    que nadie se entere.
    """
    activo = (db.query(Congelamiento)
              .join(Membresia, Congelamiento.id_membresia == Membresia.id_membresia)
              .filter(Membresia.id_socio == id_socio,
                      Congelamiento.estado == "ACTIVO")
              .first())
    if activo is None:
        return None

    if activo.fecha_fin < date.today():
        _reanudar(db, activo, hasta=activo.fecha_fin)
        db.commit()
        return None
    return activo


def _reanudar(db: Session, congelamiento: Congelamiento, hasta: date) -> int:
    """
    Cierra el congelamiento y le suma los días a la membresía.

    Devuelve los días aplicados. NO hace commit: quien llama decide cuándo,
    porque la extensión del vencimiento y el cierre del congelamiento tienen
    que pasar juntos o ninguno — si se separaran, un fallo en el medio dejaría
    días regalados o días perdidos.
    """
    dias = (hasta - congelamiento.fecha_inicio).days
    dias = max(0, dias)

    membresia = congelamiento.membresia
    if membresia is not None and membresia.fecha_vencimiento and dias:
        membresia.fecha_vencimiento = membresia.fecha_vencimiento + timedelta(days=dias)
    if membresia is not None and membresia.estado == "SUSPENDIDA":
        membresia.estado = "ACTIVA"

    congelamiento.estado = "FINALIZADO"
    congelamiento.fecha_reanudacion = hasta
    # dias_aplicados ya no se guarda: queda derivado de (fecha_reanudacion -
    # fecha_inicio). Ver _dias_aplicados.
    return dias


@router.get("/mi-membresia/congelamientos", response_model=list[CongelamientoOut])
def mis_congelamientos(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.MI_CUOTA)),
):
    """
    El historial de pausas del socio.

    OJO: devuelve la LISTA, no el saldo. El docstring viejo decía que también
    daba "cuántos días le quedan disponibles este año" y no era cierto — la
    respuesta siempre fue una lista de CongelamientoOut. Se corrige el texto
    en vez de agregar el campo para no cambiarle la forma a la respuesta, que
    ya consumen las dos apps.

    Si en algún momento hace falta mostrar el saldo, la cuenta ya está hecha
    en `_dias_congelados_en_ventana`: hay que exponerla, no reimplementarla en
    el cliente. Sumar la lista del lado de la app repetiría la regla del tope
    en tres lugares y el día que cambie de 90 a 120, dos se olvidan.
    """
    socio = _mi_socio(db, sesion)
    _congelamiento_vigente(db, socio.id_socio)   # cierra el vencido, si hay

    # Congelamiento cuelga de la membresía (ya no tiene id_socio): se llega al
    # socio por join con Membresia.
    congelamientos = (db.query(Congelamiento)
                      .join(Membresia, Congelamiento.id_membresia == Membresia.id_membresia)
                      .filter(Membresia.id_socio == socio.id_socio)
                      .order_by(Congelamiento.fecha_inicio.desc())
                      .all())
    return [_a_congelamiento_out(c) for c in congelamientos]


@router.post("/mi-membresia/congelar", response_model=CongelamientoOut,
             status_code=status.HTTP_201_CREATED)
def congelar_mi_membresia(
    datos: CongelarRequest,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.MI_CUOTA)),
):
    """
    Pausa la membresía. Los días pagados no se pierden: se corren.

    El socio pagó un mes y tiene que recibir un mes de gimnasio. Si se va tres
    semanas de viaje, esas tres semanas se le suman al vencimiento cuando
    vuelve — no cuando se va, porque hasta que no vuelve no se sabe cuántas
    fueron en serio.
    """
    socio = _mi_socio(db, sesion)
    hoy = date.today()

    if _congelamiento_vigente(db, socio.id_socio) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tu membresía ya está congelada. Reanudala antes de pedir otra pausa.",
        )

    membresia = (db.query(Membresia)
                 .filter(Membresia.id_socio == socio.id_socio,
                         Membresia.estado == "ACTIVA")
                 .order_by(Membresia.fecha_vencimiento.desc())
                 .first())
    if membresia is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No tenés una membresía activa para congelar.",
        )
    if membresia.fecha_vencimiento and membresia.fecha_vencimiento < hoy:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=("Tu cuota está vencida. Congelar sirve para no perder días "
                    "pagados, y no te quedan: renovala primero."),
        )

    inicio = datos.fecha_inicio or hoy
    if inicio < hoy:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede congelar hacia atrás. Elegí desde hoy en adelante.",
        )

    dias = (datos.fecha_fin - inicio).days
    if dias < DIAS_MINIMO_CONGELAMIENTO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La pausa mínima es de {DIAS_MINIMO_CONGELAMIENTO} días.",
        )
    if dias > DIAS_MAXIMO_POR_VEZ:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La pausa máxima es de {DIAS_MAXIMO_POR_VEZ} días por vez.",
        )

    # El tope mira los días ya USADOS en los últimos 12 meses más los que se
    # están pidiendo ahora. Ver el comentario de VENTANA_CONGELAMIENTO_DIAS:
    # la ventana es móvil justamente para que no se pueda encadenar diciembre
    # con enero y estar 180 días seguidos en pausa.
    usados = _dias_congelados_en_ventana(db, socio.id_socio, hoy)
    if usados + dias > DIAS_MAXIMO_EN_VENTANA:
        restantes = max(0, DIAS_MAXIMO_EN_VENTANA - usados)
        # Se dice DESDE CUÁNDO se cuenta, no sólo el número. Sin eso, alguien
        # que congeló en marzo y en noviembre recibe un "ya usaste 90" que le
        # parece un error del sistema: en su cabeza esas pausas son de "años"
        # distintos.
        desde = hoy - timedelta(days=VENTANA_CONGELAMIENTO_DIAS)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(f"En los últimos 12 meses (desde el "
                    f"{desde.strftime('%d/%m/%Y')}) ya congelaste {usados} días, "
                    f"y el máximo son {DIAS_MAXIMO_EN_VENTANA}. "
                    + (f"Te quedan {restantes}."
                       if restantes else
                       "No te queda ninguno; el cupo se va liberando a medida "
                       "que las pausas viejas cumplen el año.")),
        )

    congelamiento = Congelamiento(
        # Cuelga de la membresía, no del socio (id_socio se eliminó). origen
        # queda en 'SOCIO' por defecto: esta pausa la pide el socio.
        id_membresia=membresia.id_membresia,
        fecha_inicio=inicio,
        fecha_fin=datos.fecha_fin,
        motivo=datos.motivo,
        estado="ACTIVO",
    )
    db.add(congelamiento)

    # La membresía queda SUSPENDIDA, no cancelada. La diferencia importa: el
    # panel de recepción y el fichaje miran `estado == 'ACTIVA'`, así que
    # mientras esté congelada no va a poder reservar ni se le va a acreditar
    # una clase — que es exactamente lo que significa estar de pausa.
    if inicio <= hoy:
        membresia.estado = "SUSPENDIDA"

    db.commit()
    db.refresh(congelamiento)
    return _a_congelamiento_out(congelamiento)


@router.post("/mi-membresia/reanudar", response_model=CongelamientoOut)
def reanudar_mi_membresia(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.MI_CUOTA)),
):
    """
    Vuelve antes de tiempo. Se le suman SOLO los días que estuvo pausado.

    Alguien que pidió 30 días y vuelve a los 10 recupera 10, no 30. Por eso la
    extensión se calcula acá y no al congelar.
    """
    socio = _mi_socio(db, sesion)
    congelamiento = _congelamiento_vigente(db, socio.id_socio)
    if congelamiento is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="No tenés ninguna pausa activa.")

    dias = _reanudar(db, congelamiento, hasta=date.today())
    db.commit()
    db.refresh(congelamiento)

    salida = _a_congelamiento_out(congelamiento)
    salida.mensaje = (f"Listo, tu membresía vuelve a estar activa. Se te "
                      f"sumaron {dias} día(s) al vencimiento.")
    return salida


@router.post("/mi-membresia/baja", response_model=MensajeResponse)
def darme_de_baja(
    datos: BajaPropiaRequest,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.MI_CUOTA)),
):
    """
    El socio se da de baja solo.

    NO se reusa el endpoint del personal, y es la única vez en este archivo
    que no se delega. El motivo es concreto: /socios/{id}/baja DESACTIVA LA
    CUENTA DE ACCESO. Para el mostrador tiene sentido —dar de baja a alguien
    incluye cortarle el acceso— pero aplicado a uno mismo es una trampa: el
    socio apretaría "darme de baja", perdería la sesión en el acto, y no
    podría volver a entrar ni para ver su historial de pagos o para
    reinscribirse. Quedaría dependiendo del mostrador justamente en el momento
    en que decidió dejar de depender del mostrador.
    (Es el mismo agujero que el Dueño desactivándose a sí mismo, que ya
    apareció una vez en este proyecto y hubo que arreglar entrando a la base.)

    Así que acá: se da de baja la ficha, se cancela la membresía, se registra
    el motivo — y la CUENTA QUEDA VIVA.
    """
    socio = _mi_socio(db, sesion)

    if not socio.activo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Ya estás dado de baja.")

    hoy = date.today()

    # Si estaba congelada, se cierra la pausa primero. Dejar un congelamiento
    # ACTIVO colgando de una membresía cancelada haría que el índice único de
    # "un solo activo por socio" bloquee una futura reinscripción.
    vigente = _congelamiento_vigente(db, socio.id_socio)
    if vigente is not None:
        vigente.estado = "CANCELADO"
        vigente.fecha_reanudacion = hoy

    socio.activo = False
    db.add(Baja(
        id_socio=socio.id_socio,
        fecha_baja=hoy,
        tipo="VOLUNTARIA",
        motivo=datos.motivo,
    ))

    membresia = (db.query(Membresia)
                 .filter(Membresia.id_socio == socio.id_socio,
                         Membresia.estado.in_(["ACTIVA", "SUSPENDIDA"]))
                 .first())
    if membresia is not None:
        membresia.estado = "CANCELADA"

    # Las reservas futuras se cancelan y liberan su lugar. Dejarlas ocupando
    # cupo de clases a las que ya no va sería quitarle el lugar a otro socio.
    futuras = (db.query(Reserva)
               .join(Turno, Turno.id_turno == Reserva.id_turno)
               .filter(Reserva.id_socio == socio.id_socio,
                       Reserva.estado.in_(["RESERVADA", "EN_ESPERA"]),
                       Turno.fecha >= hoy)
               .all())
    turnos_liberados = []
    for r in futuras:
        if r.estado == "RESERVADA":
            turnos_liberados.append(r.id_turno)
        r.estado = "CANCELADA_SOCIO"
        r.fecha_cancelacion = datetime.now()

    db.flush()
    for id_turno in turnos_liberados:
        promover_de_lista_de_espera(db, id_turno)

    db.commit()

    return MensajeResponse(mensaje=(
        "Listo, ya estás dado de baja. Tu cuenta sigue activa: podés entrar "
        "cuando quieras a ver tu historial, y si volvés no hace falta que "
        "te den de alta de nuevo."
    ))


@router.get("/mis-actividades/inscripciones", response_model=list[InscripcionOut])
def mis_inscripciones(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.MIS_ACTIVIDADES)),
):
    """
    Los abonos que el socio compró, vigentes y vencidos.

    El equivalente del personal —/actividades/inscripciones/socio/{id}— recibe
    el id en la URL y está protegido con permisos de mostrador. Con ese, un
    socio veía 403; y si el permiso se aflojara, cambiar el número de la URL
    le mostraría los abonos de cualquier otro.
    """
    socio = _mi_socio(db, sesion)
    from routers.actividades import _a_inscripcion_out

    inscripciones = (db.query(InscripcionActividad)
                     .filter(InscripcionActividad.id_socio == socio.id_socio)
                     .order_by(InscripcionActividad.id_inscripcion.desc())
                     .all())
    return [_a_inscripcion_out(db, i) for i in inscripciones]


@router.post("/mis-actividades/inscripciones/{id_inscripcion}/cancelar",
             response_model=InscripcionOut)
def cancelar_mi_inscripcion(
    id_inscripcion: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.MIS_ACTIVIDADES)),
):
    """
    Da de baja un abono propio.

    Se verifica que la inscripción SEA SUYA antes de delegar, y si no lo es
    responde 404 y no 403: un 403 confirmaría que existe y es de otro. Es la
    misma regla que en cancelar un turno.
    """
    inscripcion = db.get(InscripcionActividad, id_inscripcion)
    if inscripcion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Ese abono no existe.")

    socio = _mi_socio(db, sesion)
    if inscripcion.id_socio != socio.id_socio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Ese abono no existe.")

    from routers.actividades import cancelar_inscripcion
    nombre = socio.persona.nombre_completo
    try:
        salida = cancelar_inscripcion(id_inscripcion=id_inscripcion, db=db, sesion=sesion)
    except HTTPException as e:
        raise _traducir_error(e, nombre) from e
    return salida


@router.get("/mi-entrenador", response_model=list[AsignacionEntrenadorOut])
def mis_entrenadores(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.MI_RUTINA)),
):
    """
    Quién lo entrena. Sólo los vigentes.

    A diferencia del endpoint del personal, acá NO se devuelve el historial: al
    socio le interesa a quién preguntarle hoy, no quién lo entrenaba en marzo.
    Ese dato es del gimnasio —sirve para auditar y para que un entrenador
    nuevo se ponga al día— y no aporta nada en la app de quien entrena.

    Va bajo la sección MI_RUTINA y no una propia: el entrenador a cargo es
    parte de la misma pregunta que "cuál es mi rutina", y crear una sección
    sólo para esto obligaría a sumarla a las tres copias de la matriz de
    permisos para una pantalla que no existe.
    """
    socio = _mi_socio(db, sesion)
    from routers.socios import _a_asignacion_out

    asignaciones = (db.query(AsignacionEntrenador)
                    .filter(AsignacionEntrenador.id_socio == socio.id_socio,
                            AsignacionEntrenador.estado == "ACTIVA")
                    .order_by(AsignacionEntrenador.fecha_inicio)
                    .all())
    return [_a_asignacion_out(a) for a in asignaciones]


# =============================================================================
# MIS CONDICIONES DE SALUD
# =============================================================================
#
# El socio ve y administra las suyas. NO usa Accion.VER_HISTORIAL_MEDICO —esa
# es para ver las de OTROS, y el socio no la tiene— sino su propia sección.
# Es la misma distinción de siempre en este archivo: mirar la ficha ajena y
# mirar la propia son permisos distintos.
#
# Que el socio pueda CARGARLAS es deliberado y va en la dirección de que se
# maneje solo: "soy asmático" es algo que él sabe y el gimnasio necesita, y
# obligarlo a ir al mostrador a contarlo —donde además el recepcionista no
# debería enterarse— sería exactamente al revés.

@router.get("/catalogo-patologias", response_model=list[PatologiaOut])
def catalogo_para_el_socio(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.MI_PERFIL)),
):
    """
    El catálogo, para que el socio pueda elegir de la lista.

    Existe porque sin esto el POST de acá abajo es inusable: pide un
    `id_patologia` que tiene que salir del catálogo, y el catálogo se lista en
    `GET /patologias`, que exige `VER_HISTORIAL_MEDICO` — una acción que el
    Socio tiene en False como todas las demás. O sea que el endpoint para
    declarar la propia condición estaba, pero no había forma de averiguar qué
    número mandarle. El agujero no se ve leyendo el router de patologías ni el
    del portal por separado: aparece recién al intentar dibujar la pantalla.

    Duplicar el listado acá en vez de aflojarle el permiso a `GET /patologias`
    es deliberado. Esa acción NO significa "ver la lista de enfermedades que
    existen": significa ver el historial médico de OTRA persona, y es la única
    donde el Recepcionista queda por debajo del Entrenador. Abrirla para que
    entre el socio le daría de paso al mostrador el acceso que el router de
    patologías explica en detalle por qué no debe tener.

    Lo que se devuelve acá no es de nadie: son nombres de condiciones, las
    mismas que están en cualquier formulario de aptitud física. Ninguna fila
    dice qué socio tiene qué.

    No es la primera vez que hace falta esto en este mismo archivo:
    `/portal/mi-cuota/planes` existe por lo mismo —duplica el listado de
    `/cobros/tipos-membresia`, que el socio no puede tocar porque la sección
    COBROS la tiene en NINGUNO—. El patrón ya está establecido: cuando el
    portal necesita un catálogo que vive detrás de un permiso de gestión, se
    republica acá recortado, no se afloja el permiso del otro lado.
    """
    patologias = db.query(Patologia).order_by(Patologia.nombre).all()
    return [PatologiaOut(id_patologia=p.id_patologia, nombre=p.nombre,
                          descripcion=p.descripcion)
            for p in patologias]


@router.get("/mis-patologias", response_model=list[PatologiaDeSocioOut])
def mis_patologias(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.MI_PERFIL)),
):
    """Sus condiciones registradas."""
    socio = _mi_socio(db, sesion)
    from routers.patologias import _a_salida

    filas = (db.query(SocioPatologia)
             .filter(SocioPatologia.id_socio == socio.id_socio)
             .all())
    return sorted((_a_salida(f) for f in filas), key=lambda x: x.nombre)


@router.post("/mis-patologias", response_model=PatologiaDeSocioOut,
             status_code=status.HTTP_201_CREATED)
def agregar_mi_patologia(
    datos: AsignarPatologiaRequest,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.MI_PERFIL)),
):
    """
    Declara una condición propia.

    Sólo del catálogo: no se acepta texto libre. Si alguien tiene algo que no
    está en la lista, lo carga un entrenador o un nutricionista al catálogo
    primero. Dejar escribir libremente rompería el catálogo con veinte formas
    de escribir "asma" y volvería inútil poder contar cuántos socios la
    tienen — que es todo el motivo de que sea una tabla y no un varchar.
    """
    socio = _mi_socio(db, sesion)
    from routers.patologias import _a_salida

    patologia = db.get(Patologia, datos.id_patologia)
    if patologia is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=("Esa condición no está en la lista. Pedile a tu entrenador "
                    "o al nutricionista que la agregue."),
        )

    if db.get(SocioPatologia, (socio.id_socio, datos.id_patologia)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya tenés «{patologia.nombre}» registrada.",
        )

    sp = SocioPatologia(
        id_socio=socio.id_socio,
        id_patologia=datos.id_patologia,
        fecha_diagnostico=datos.fecha_diagnostico,
        observaciones=datos.observaciones,
    )
    db.add(sp)
    db.commit()
    db.refresh(sp)
    return _a_salida(sp)


@router.delete("/mis-patologias/{id_patologia}", status_code=status.HTTP_204_NO_CONTENT)
def quitar_mi_patologia(
    id_patologia: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.MI_PERFIL)),
):
    """
    Se saca una condición.

    Se busca por la clave compuesta CON SU id_socio, así que no hay forma de
    borrarle una a otro cambiando el número en la URL: la fila (otro_socio,
    esa_patologia) simplemente no aparece en esta consulta.
    """
    socio = _mi_socio(db, sesion)
    sp = db.get(SocioPatologia, (socio.id_socio, id_patologia))
    if sp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="No tenés esa condición registrada.")
    db.delete(sp)
    db.commit()
