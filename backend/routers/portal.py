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
    Reserva, Socio, Telefono, Turno,
)
from permisos import Seccion
from schemas import (
    AsignacionDietaOut, AsignacionRutinaOut, AsistenciaOut, DietaOut,
    MiCuotaOut, MiPerfilOut, PagoOut, ReservaOut, RutinaOut,
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
        # `observaciones` del Socio NO se expone: son notas internas del
        # personal sobre el socio, no información para él.
    )


# =============================================================================
# MI RUTINA
# =============================================================================

@router.get("/mi-rutina", response_model=RutinaOut | None)
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

    # Se reusa el armador del router de gestión: la rutina es la misma, lo que
    # cambia es cómo se llega a ella.
    from routers.rutinas import _a_rutina_out
    return _a_rutina_out(asignacion.rutina)


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

@router.get("/mi-dieta", response_model=DietaOut | None)
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

    from routers.nutricion import _a_dieta_out
    return _a_dieta_out(asignacion.dieta)


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
    if membresia:
        plan = membresia.tipo.nombre if membresia.tipo else None
        vence = membresia.fecha_vencimiento
        if vence:
            dias = (vence - hoy).days

    return MiCuotaOut(
        al_dia=bool(membresia) and not deudas and (dias is None or dias >= 0),
        plan=plan,
        fecha_vencimiento=vence,
        dias_restantes=dias,
        deuda_total=float(sum(d.monto for d in deudas)),
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
