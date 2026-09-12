"""
routers/promociones.py
----------------------
Descuentos sobre el precio de lista.

POR QUÉ ESTE ROUTER EXISTIÓ TARDE
=================================
`Promocion` estaba modelada desde el principio y `Membresia.id_promocion` la
referencia, pero ningún endpoint la tocaba: los descuentos existían en el
esquema y no había forma de cargarlos. Era el caso inverso al de
`Consulta_Cruzada` —aquella era una tabla que nadie usaba Y nadie apuntaba, y
por eso se eliminó; ésta la apunta `Membresia`, así que sacarla habría sido
además una migración sobre la tabla de plata.

DOS PERMISOS, Y LA DIFERENCIA ES EL PUNTO
=========================================
    Crear / editar / dar de baja  ->  Accion.GESTION_PROMOCIONES  (solo Dueño)
    Listar                        ->  Seccion.COBROS              (Dueño + Recepcionista)

Definir un descuento es una decisión de negocio; aplicarlo al cobrar es
operativo. El Recepcionista tiene que PODER VER las promos vigentes —si no, no
puede elegir ninguna en el mostrador— pero no inventarlas. Es exactamente el
mismo reparto que ya usa `POST /cobros/tipos-membresia`: el precio de lista lo
define el Dueño y lo cobra el mostrador.

EL DESCUENTO NO SE APLICA ACÁ
=============================
Este router administra el catálogo. Quien lo aplica es `POST /cobros`, que
recibe un `id_promocion` opcional y recalcula el precio con `precio_con_promo`
de abajo. Esa función vive acá y no allá para que haya UNA sola definición de
cuánto descuenta una promoción: si el cálculo estuviera duplicado en el cobro
y en la vista previa, el día que cambie una regla la vista previa mostraría un
número y el cobro registraría otro.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import Dueno, Pago, Promocion, Sede, TipoMembresia
from permisos import Accion, Seccion
from schemas import (
    MensajeResponse, PromocionCrear, PromocionEditar, PromocionOut,
    VistaPreviaDescuento,
)
from security import Sesion, requiere_accion, requiere_seccion

router = APIRouter(prefix="/promociones", tags=["Promociones"])


# =============================================================================
# CÁLCULO
# =============================================================================

def esta_vigente(promo: Promocion, cuando: date | None = None) -> bool:
    """
    Activa Y dentro de la ventana de fechas.

    Son dos cosas distintas y hay que chequear las dos: `activo` es la baja
    lógica —el Dueño la apagó a mano— y las fechas son la vigencia natural.
    Una promo de enero sigue con activo=true en marzo, y cobrarla entonces
    sería regalar plata por un descuido.
    """
    hoy = cuando or date.today()
    return bool(promo.activo) and promo.fecha_inicio <= hoy <= promo.fecha_fin


def etiqueta_de(promo: Promocion) -> str:
    """
    "20% OFF" / "$5.000 OFF", armado en el backend.

    Se manda ya formateado por el mismo motivo que `estado` y `plan` del socio:
    las dos apps lo mostrarían igual, y redactarlo en cada una sería mantener
    el mismo texto en dos lugares.
    """
    if promo.porcentaje_descuento is not None:
        porcentaje = float(promo.porcentaje_descuento)
        # Sin decimales cuando es redondo: "20% OFF" y no "20.0% OFF".
        entero = int(porcentaje)
        texto = str(entero) if porcentaje == entero else f"{porcentaje:g}"
        return f"{texto}% OFF"
    return "sin descuento"


def precio_con_promo(precio_lista: float, promo: Promocion) -> tuple[float, float]:
    """
    Devuelve (descuento, precio_final).

    El piso en cero no es defensivo de más: un monto fijo de $5.000 sobre un
    plan de $3.000 daría -$2.000, y un pago negativo en la tabla de plata es
    peor que un descuento mal cargado. Se cobra $0 y queda registrado como
    pago, que es lo que de verdad pasó.
    """
    if promo.porcentaje_descuento is not None:
        descuento = precio_lista * float(promo.porcentaje_descuento) / 100
    else:
        descuento = 0.0

    descuento = min(round(descuento, 2), precio_lista)
    return descuento, round(precio_lista - descuento, 2)


def _a_salida(promo: Promocion) -> PromocionOut:
    return PromocionOut(
        id_promocion=promo.id_promocion,
        nombre=promo.nombre,
        descripcion=promo.descripcion,
        porcentaje_descuento=(float(promo.porcentaje_descuento)
                              if promo.porcentaje_descuento is not None else None),
        fecha_inicio=promo.fecha_inicio,
        fecha_fin=promo.fecha_fin,
        id_sede=promo.id_sede,
        activo=bool(promo.activo),
        vigente=esta_vigente(promo),
        etiqueta=etiqueta_de(promo),
    )


def _validar(datos: PromocionCrear | PromocionEditar, db: Session,
             id_actual: int | None = None) -> None:
    """
    Lo que Pydantic no puede chequear solo porque necesita la base.

    El nombre se compara SIN distinguir mayúsculas, igual que el catálogo de
    patologías: "Verano 2026" y "verano 2026" son la misma promo, y dejar que
    convivan haría que en el selector del mostrador aparezcan dos entradas
    idénticas y nadie sepa cuál aplicar.
    """
    nombre = datos.nombre.strip()
    consulta = db.query(Promocion).filter(func.lower(Promocion.nombre) == nombre.lower())
    if id_actual is not None:
        consulta = consulta.filter(Promocion.id_promocion != id_actual)
    choca = consulta.first()
    if choca:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una promoción llamada «{choca.nombre}».",
        )

    if datos.id_sede is not None and db.get(Sede, datos.id_sede) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Esa sede no existe.")


# =============================================================================
# LISTAR
# =============================================================================

@router.get("", response_model=list[PromocionOut])
def listar_promociones(
    solo_vigentes: bool = False,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.COBROS)),
):
    """
    El catálogo de descuentos.

    Por defecto devuelve TODAS, incluidas las apagadas y las vencidas: la
    pantalla de administración necesita verlas para poder reactivar una del año
    pasado en vez de volver a cargarla.

    `solo_vigentes=true` es lo que pide el selector del mostrador, que no tiene
    por qué ofrecer una promo de enero en marzo.

    El guard es la SECCIÓN Cobros y no la acción de promociones: el
    Recepcionista tiene que poder elegir una al cobrar. Sin esto, el selector
    del mostrador le daría 403 y la funcionalidad quedaría sólo para el Dueño,
    que es justamente quien menos atiende el mostrador.
    """
    promociones = (db.query(Promocion)
                   .order_by(Promocion.fecha_inicio.desc(),
                             Promocion.id_promocion.desc())
                   .all())
    salida = [_a_salida(p) for p in promociones]
    if solo_vigentes:
        salida = [p for p in salida if p.vigente]
    return salida


@router.get("/{id_promocion}", response_model=PromocionOut)
def obtener_promocion(
    id_promocion: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.COBROS)),
):
    promo = db.get(Promocion, id_promocion)
    if promo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Esa promoción no existe.")
    return _a_salida(promo)


# =============================================================================
# ADMINISTRAR — solo el Dueño
# =============================================================================

def _id_dueno(db: Session, sesion: Sesion) -> int:
    """
    De quién es la promoción.

    `Promocion.id_dueno` es NOT NULL. Se busca el Dueño de la persona logueada
    y no "el primero de la tabla" porque en un gimnasio con dos socios
    fundadores la promo tiene que quedar atribuida a quien la creó. El fallback
    existe igual para el caso raro de que la acción la ejecute alguien con el
    permiso pero sin fila en Dueno: es preferible guardar la promo atribuida al
    titular que rechazar la operación por un problema de datos que el usuario
    no puede resolver desde la pantalla.
    """
    propio = db.query(Dueno).filter(Dueno.id_persona == sesion.id_persona).first()
    if propio:
        return propio.id_dueno

    alguno = db.query(Dueno).order_by(Dueno.id_dueno).first()
    if alguno is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No hay ningún dueño cargado; no se puede crear la promoción.",
        )
    return alguno.id_dueno


@router.post("", response_model=PromocionOut, status_code=status.HTTP_201_CREATED)
def crear_promocion(
    datos: PromocionCrear,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.GESTION_PROMOCIONES)),
):
    """
    Carga un descuento nuevo.

    Se permite crear una promoción con fechas ya pasadas y no es un descuido:
    sirve para registrar una que se acordó verbalmente la semana pasada y hay
    que dejar asentada. Nace `activo=True` pero `vigente` sale en false, y el
    selector del mostrador no la ofrece — que es exactamente el comportamiento
    correcto.
    """
    _validar(datos, db)

    promo = Promocion(
        id_dueno=_id_dueno(db, sesion),
        id_sede=datos.id_sede,
        nombre=datos.nombre.strip(),
        descripcion=datos.descripcion,
        porcentaje_descuento=datos.porcentaje_descuento,
        fecha_inicio=datos.fecha_inicio,
        fecha_fin=datos.fecha_fin,
        activo=True,
    )
    db.add(promo)
    db.commit()
    db.refresh(promo)
    return _a_salida(promo)


@router.put("/{id_promocion}", response_model=PromocionOut)
def editar_promocion(
    id_promocion: int,
    datos: PromocionEditar,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.GESTION_PROMOCIONES)),
):
    """
    Cambia una promoción.

    NO toca las membresías que ya se cobraron con ella, y es deliberado:
    `Membresia.precio_pactado` guarda el monto que se cobró de verdad, no una
    referencia al descuento. Si editar la promo recalculara lo ya cobrado, el
    historial de plata cambiaría solo — que es exactamente lo que el resto de
    este sistema evita (ver el encabezado de cobros.py: "nada se borra").
    """
    promo = db.get(Promocion, id_promocion)
    if promo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Esa promoción no existe.")

    _validar(datos, db, id_actual=id_promocion)

    promo.nombre = datos.nombre.strip()
    promo.descripcion = datos.descripcion
    promo.porcentaje_descuento = datos.porcentaje_descuento
    promo.fecha_inicio = datos.fecha_inicio
    promo.fecha_fin = datos.fecha_fin
    promo.id_sede = datos.id_sede

    db.commit()
    db.refresh(promo)
    return _a_salida(promo)


# Baja e alta lógicas, las dos desde el principio: es la regla del proyecto —
# nunca dejar sólo el camino de ida. Una promo que se apagó por error tiene que
# poder volver sin recargarla a mano, y una del año pasado se reactiva
# cambiándole las fechas en vez de duplicarla.

@router.post("/{id_promocion}/baja", response_model=PromocionOut)
def dar_de_baja(
    id_promocion: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.GESTION_PROMOCIONES)),
):
    """
    La apaga. NO borra la fila.

    Borrarla rompería las membresías que la referencian: `id_promocion` es una
    FK, y un DELETE dejaría cobros apuntando a una promoción inexistente o
    fallaría por la restricción. Además el historial es el que responde "¿por
    qué a este socio le cobramos $24.000 en vez de $30.000?".
    """
    promo = db.get(Promocion, id_promocion)
    if promo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Esa promoción no existe.")
    if not promo.activo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Esa promoción ya estaba dada de baja.")
    promo.activo = False
    db.commit()
    db.refresh(promo)
    return _a_salida(promo)


@router.post("/{id_promocion}/reactivar", response_model=PromocionOut)
def reactivar(
    id_promocion: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.GESTION_PROMOCIONES)),
):
    """
    La vuelve a encender.

    Ojo con lo que NO hace: no le mueve las fechas. Reactivar una promo cuya
    ventana ya pasó la deja activa pero no vigente, así que el mostrador sigue
    sin poder aplicarla. Es a propósito — extender una promoción es cambiarle
    la fecha de fin, una decisión explícita, y no un efecto secundario de
    volver a encenderla.
    """
    promo = db.get(Promocion, id_promocion)
    if promo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Esa promoción no existe.")
    if promo.activo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Esa promoción ya estaba activa.")
    promo.activo = True
    db.commit()
    db.refresh(promo)

    salida = _a_salida(promo)
    if not salida.vigente:
        # Se avisa en vez de fallar: reactivarla es válido, pero si nadie
        # dijera nada el Dueño se iría creyendo que ya se puede aplicar.
        salida.etiqueta = f"{salida.etiqueta} (fuera de fecha)"
    return salida


@router.get("/{id_promocion}/vista-previa", response_model=VistaPreviaDescuento)
def vista_previa(
    id_promocion: int,
    id_tipo_membresia: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_seccion(Seccion.COBROS)),
):
    """
    Cuánto saldría cobrar ese plan con esa promo. No cobra nada.

    Existe para que las dos apps NO calculen el descuento por su cuenta. La
    alternativa era mandarles `porcentaje_descuento` y que cada una hiciera la
    multiplicación, y ahí la fórmula —incluido el piso en cero y el redondeo—
    quedaría escrita en tres lugares. Es el mismo criterio que ya rige el
    `estado` del socio: la regla de negocio se deriva en el servidor.

    Guard por sección COBROS y no por la acción de promociones: quien lo
    necesita es el mostrador, mientras elige.
    """
    promo = db.get(Promocion, id_promocion)
    if promo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Esa promoción no existe.")

    tipo = db.get(TipoMembresia, id_tipo_membresia)
    if tipo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="El plan no existe.")

    precio_lista = float(tipo.precio_actual)
    descuento, final = precio_con_promo(precio_lista, promo)
    return VistaPreviaDescuento(
        precio_lista=precio_lista,
        descuento=descuento,
        precio_final=final,
        promocion=promo.nombre,
    )


@router.get("/{id_promocion}/uso", response_model=MensajeResponse)
def uso_de_la_promocion(
    id_promocion: int,
    db: Session = Depends(get_db),
    sesion: Sesion = Depends(requiere_accion(Accion.GESTION_PROMOCIONES)),
):
    """
    Cuántas membresías se cobraron con ella.

    Existe para poder decidir con datos antes de darla de baja: apagar una que
    usaron 40 socios no es lo mismo que apagar una que no usó nadie.
    """
    promo = db.get(Promocion, id_promocion)
    if promo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Esa promoción no existe.")

    # La promo aplicada vive en el PAGO (Pago.id_promocion), no en la
    # membresía: ahí se movió junto con monto_descuento.
    usos = (db.query(func.count(Pago.id_pago))
            .filter(Pago.id_promocion == id_promocion)
            .scalar()) or 0

    if usos == 0:
        return MensajeResponse(mensaje="Todavía no se aplicó en ningún cobro.")
    if usos == 1:
        return MensajeResponse(mensaje="Se aplicó en 1 cobro.")
    return MensajeResponse(mensaje=f"Se aplicó en {usos} cobros.")
