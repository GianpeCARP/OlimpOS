"""
routers/asistencia.py
---------------------
Registro de ingresos al gimnasio: el panel de recepción.

EL SISTEMA INFORMA, NO JUZGA
----------------------------
Cuando alguien ficha con una deuda o la cuota vencida, el ingreso **se
registra igual** y la respuesta trae una advertencia. No se rechaza.

Es una decisión de negocio, no un descuido: dejar a alguien afuera del
gimnasio es algo que decide una persona en el mostrador mirando el caso —
puede ser un socio de años que se atrasó dos días, o alguien que ya avisó que
paga mañana. Un backend que devuelve 403 obliga a que ese criterio no exista.

Y hay una razón de datos además: si el ingreso no se registrara, el gimnasio
perdería el dato de que esa persona estuvo. Después nadie puede responder
"¿cuánta gente entró en marzo?" ni detectar que un moroso viene todos los
días.

RFID O MANUAL
-------------
`metodo_registro` distingue el fichaje con tarjeta del que carga alguien a
mano. Sirve al auditar: un registro MANUAL es una decisión de una persona
concreta —que queda guardada en `id_registrado_por`— y conviene poder
filtrarlos del total.
"""

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Asistencia, Membresia, Socio
from permisos import Acceso, Seccion
from schemas import (
    AsistenciaOut, FicharRequest, FicharResponse, MetodoRegistro,
)
from security import Sesion, requiere_seccion
from turnos import reserva_a_acreditar

router = APIRouter(prefix="/asistencia", tags=["Asistencia"])

# NO HAY TOPE DE INGRESOS POR DÍA, Y ES UNA DECISIÓN
# ---------------------------------------------------
# Acá hubo dos guardas: un anti-duplicado de 5 minutos y un tope de un ingreso
# diario, las dos rechazando con 409 para que el mostrador confirmara el
# ingreso repetido. Se sacaron las dos.
#
# El motivo es el mostrador real: quien atiende NO lee el cartel. Con gente
# haciendo cola, un diálogo de confirmación se acepta sin mirarlo —y entonces
# no frenaba nada— o, peor, deja a un socio parado en la puerta mientras el
# recepcionista descifra qué le está preguntando la pantalla. Negarle el paso a
# alguien con la cuota paga porque el sistema cree que ya entró es exactamente
# lo que evita el resto de este módulo (ver "el sistema informa, no juzga"): la
# regla vale igual para entrar dos veces que para deber plata.
#
# En su lugar, cada ingreso viaja con `ingreso_numero`: qué número de entrada
# del día es para ese socio. El segundo se registra sin preguntar nada y la
# lista lo muestra marcado al lado del nombre. El que pasa diez veces para
# joder queda a la vista de quien quiera mirarlo; el que entrena a la mañana y
# vuelve a la clase de la tarde entra sin que nadie confirme nada.
#
# El conteo del día sigue siendo interpretable, porque el dato está: son pases,
# y `ingreso_numero > 1` dice cuáles de ellos son repetidos.


def _a_asistencia_out(a: Asistencia, ingreso_numero: int | None = None) -> AsistenciaOut:
    socio = a.socio
    persona = socio.persona if socio else None
    return AsistenciaOut(
        id_asistencia=a.id_asistencia,
        id_socio=a.id_socio,
        socio=persona.nombre_completo if persona else "?",
        numero_socio=socio.numero_socio if socio else None,
        fecha_hora_ingreso=a.fecha_hora_ingreso,
        fecha_hora_egreso=a.fecha_hora_egreso,
        metodo_registro=a.metodo_registro,
        ingreso_numero=ingreso_numero,
    )


def _ingresos_del_dia(db: Session, id_socio: int) -> int:
    """Cuántos ingresos lleva hoy ese socio, contando los ya guardados."""
    inicio = datetime.combine(date.today(), datetime.min.time())
    return (
        db.query(Asistencia)
        .filter(Asistencia.id_socio == id_socio,
                Asistencia.fecha_hora_ingreso >= inicio)
        .count()
    )


def _revisar_situacion(db: Session, socio: Socio) -> str | None:
    """
    Devuelve una advertencia si el socio no está en condiciones, o None.

    NUNCA lanza: quien llama registra el ingreso igual. Ver el docstring del
    módulo.
    """
    if not socio.activo:
        return "El socio está dado de baja."

    hoy = date.today()
    vigente = (
        db.query(Membresia)
        .filter(Membresia.id_socio == socio.id_socio, Membresia.estado == "ACTIVA")
        .order_by(Membresia.fecha_inicio.desc())
        .first()
    )

    if vigente is None:
        return "No tiene ninguna membresía activa."

    if vigente.fecha_vencimiento and vigente.fecha_vencimiento < hoy:
        dias = (hoy - vigente.fecha_vencimiento).days
        return f"La cuota venció hace {dias} día(s) ({vigente.fecha_vencimiento})."

    # Ya no hay chequeo de tabla Deuda: se eliminó del esquema. El estado
    # "debe" es derivable, y las dos condiciones de arriba (sin membresía
    # activa / cuota vencida) ya lo cubren enteramente.
    return None


@router.post("/fichar", response_model=FicharResponse, status_code=status.HTTP_201_CREATED)
def fichar(
    datos: FicharRequest,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.ASISTENCIA, Acceso.TOTAL)),
):
    """
    Registra un ingreso, por tarjeta RFID o a mano.

    Devuelve 201 aunque el socio tenga problemas: el campo `permitido` y la
    `advertencia` son lo que le dice al mostrador que mire el caso.
    """
    # Exactamente una de las dos vías. Aceptar ambas dejaría ambiguo a quién
    # se fichó si discreparan.
    if bool(datos.codigo_rfid) == bool(datos.id_socio):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Indicá el código RFID o el id del socio, pero no los dos.",
        )

    if datos.codigo_rfid:
        socio = (db.query(Socio)
                 .filter(Socio.codigo_rfid == datos.codigo_rfid.strip())
                 .first())
        metodo = MetodoRegistro.RFID
        if socio is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Esa tarjeta no está asignada a ningún socio.",
            )
    else:
        socio = db.get(Socio, datos.id_socio)
        metodo = MetodoRegistro.MANUAL
        if socio is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El socio no existe.",
            )

    ahora = datetime.now()

    # Acá iban dos rechazos por ingreso repetido. Ya no: se registra siempre y
    # se informa cuál número de ingreso del día es. Ver el comentario de arriba.
    advertencia = _revisar_situacion(db, socio)

    # A qué clase corresponde este ingreso. Lo resuelve el sistema: el
    # recepcionista no busca a la persona ni tilda nada, pasa la tarjeta y
    # listo. Si llegó tarde, `turno_perdido` explica qué se perdió.
    #
    # Que haya perdido el turno NO impide el ingreso: su cuota le paga el
    # gimnasio igual. Rechazarlo haría que haber reservado lo dejara peor que
    # no haber reservado.
    reserva, turno_perdido = reserva_a_acreditar(db, socio.id_socio, ahora)

    asistencia = Asistencia(
        id_socio=socio.id_socio,
        id_sede=socio.id_sede,
        # Acá se guarda la acreditación de la clase. Es lo único que hace
        # falta: "asistió" no es un estado guardado en Reserva, se deriva de
        # que exista esta fila apuntándole. Ver el docstring de turnos.py.
        id_reserva=reserva.id_reserva if reserva else None,
        fecha_hora_ingreso=ahora,
        metodo_registro=metodo.value,
        # Queda registrado QUIÉN cargó el ingreso. Con RFID no hay una persona
        # detrás, pero sí una sesión abierta en el panel de recepción.
        id_registrado_por=sesion.id_usuario,
    )
    db.add(asistencia)
    db.commit()
    db.refresh(asistencia)

    clase = None
    if reserva is not None:
        turno = reserva.turno
        clase = f"{turno.actividad.nombre} {turno.hora.strftime('%H:%M')}"

    # Se cuenta DESPUÉS del commit, así que la fila recién creada ya entra en
    # el total: el primer ingreso del día da 1.
    ingreso_numero = _ingresos_del_dia(db, socio.id_socio)

    nombre = socio.persona.nombre_completo
    if clase:
        mensaje = f"Ingreso registrado: {nombre}. Acreditado a {clase}."
    else:
        mensaje = f"Ingreso registrado: {nombre}."
    if ingreso_numero > 1:
        mensaje = f"{mensaje} Es su {ingreso_numero}º ingreso de hoy."
    if turno_perdido:
        mensaje = f"{mensaje} {turno_perdido}"
    if advertencia:
        mensaje = f"{mensaje} {advertencia}"

    return FicharResponse(
        asistencia=_a_asistencia_out(asistencia, ingreso_numero),
        permitido=advertencia is None,
        advertencia=advertencia,
        mensaje=mensaje,
        clase_acreditada=clase,
        turno_perdido=turno_perdido,
    )


@router.get("/hoy", response_model=list[AsistenciaOut])
def ingresos_de_hoy(
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.ASISTENCIA)),
):
    """Los ingresos del día, el más reciente primero. Es el feed del panel."""
    inicio = datetime.combine(date.today(), datetime.min.time())
    asistencias = (
        db.query(Asistencia)
        .filter(Asistencia.fecha_hora_ingreso >= inicio)
        .order_by(Asistencia.fecha_hora_ingreso.desc())
        .all()
    )

    # Se numeran los ingresos de cada socio. La lista viene del más reciente al
    # más viejo, así que se recorre al revés: el último es el primero del día.
    # Se cuenta acá y no con una consulta por fila —serían N viajes a São Paulo
    # para un dato que ya está en memoria.
    llevados: dict[int, int] = {}
    numero_de: dict[int, int] = {}
    for a in reversed(asistencias):
        llevados[a.id_socio] = llevados.get(a.id_socio, 0) + 1
        numero_de[a.id_asistencia] = llevados[a.id_socio]

    return [_a_asistencia_out(a, numero_de[a.id_asistencia]) for a in asistencias]


@router.post("/{id_asistencia}/salida", response_model=AsistenciaOut)
def registrar_salida(
    id_asistencia: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.ASISTENCIA, Acceso.TOTAL)),
):
    """
    Marca el egreso.

    Es opcional: la mayoría de los gimnasios no controla la salida, y un
    ingreso sin egreso es un registro válido —significa "entró"—, no un dato
    incompleto.
    """
    asistencia = db.get(Asistencia, id_asistencia)
    if asistencia is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Ese registro de ingreso no existe.")

    if asistencia.fecha_hora_egreso is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Ese ingreso ya tenía la salida registrada.")

    asistencia.fecha_hora_egreso = datetime.now()
    db.commit()
    db.refresh(asistencia)
    return _a_asistencia_out(asistencia)


@router.delete("/{id_asistencia}", status_code=status.HTTP_204_NO_CONTENT)
def deshacer_fichaje(
    id_asistencia: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.ASISTENCIA, Acceso.TOTAL)),
):
    """
    Borra un ingreso mal cargado ("desfichar").

    Acá SÍ se borra la fila, a diferencia de casi todo el resto del sistema,
    porque un ingreso que no ocurrió no es historia que preservar: es un dato
    falso. El caso real es el amigo que pasa la tarjeta por otro, o el ingreso
    cargado al socio equivocado.

    SÓLO ingresos de HOY: corregir el error del momento es operación de
    mostrador; borrar la asistencia de la semana pasada sería reescribir
    estadísticas ya usadas, y para eso no hay botón.
    """
    asistencia = db.get(Asistencia, id_asistencia)
    if asistencia is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Ese registro de ingreso no existe.")

    if asistencia.fecha_hora_ingreso.date() != date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sólo se pueden deshacer los ingresos de hoy.",
        )

    db.delete(asistencia)
    db.commit()


@router.get("/socio/{id_socio}", response_model=list[AsistenciaOut])
def historial_socio(
    id_socio: int,
    limite: int = 30,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.ASISTENCIA)),
):
    """Últimos ingresos de un socio. Sirve para ver su regularidad."""
    asistencias = (
        db.query(Asistencia)
        .filter(Asistencia.id_socio == id_socio)
        .order_by(Asistencia.fecha_hora_ingreso.desc())
        .limit(min(limite, 200))
        .all()
    )
    return [_a_asistencia_out(a) for a in asistencias]
