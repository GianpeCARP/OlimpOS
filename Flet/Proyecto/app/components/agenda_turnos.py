# =============================================================================
# components/agenda_turnos.py — Los próximos turnos con quién se anotó
# =============================================================================
# Gemelo de components/AgendaTurnos.tsx de la PWA. Lo usan Actividades (la
# agenda de la semana, con cancelar) y el Dashboard (`compacto`: sólo lo que
# está por pasar).
#
# Faltaba en las dos apps: el socio veía sus turnos y el profesor los suyos,
# pero el Dueño no tenía dónde ver "mañana a las 19 hay Yoga con 8 anotados, y
# son estos". Recepción muestra las próximas horas; esto, los próximos días.
#
# La lista de anotados se pide al EXPANDIR un turno, no con la agenda: una
# semana puede tener decenas de turnos y bajar todas sus reservas para mirar
# una sola sería pagar decenas de consultas por nada.

from datetime import date, datetime, timedelta

import flet as ft

from app.config import Colors, Fonts, Radius, alpha
from app.permisos import Accion
from app.state import app_state
from app.components.ui import (section_card, empty_state, show_snack,
                               confirm_dialog, open_dialog)

# Mismos rótulos y colores que utils/estadoInscripto.ts y que el panel de
# Recepción: el mismo estado no puede decir dos cosas según quién mire.
ESTADO_INSCRIPTO = {
    "pendiente": ("Falta llegar", Colors.TEXT_SECONDARY),
    "asistio":   ("Presente",     Colors.STATUS_OK),
    "ausente":   ("No llegó",     Colors.STATUS_DANGER),
    "en_espera": ("En espera",    Colors.STATUS_WARN),
    "cancelada": ("Canceló",      Colors.TEXT_MUTED),
}

MAX_COMPACTO = 6            # turnos como máximo en el dashboard
MINUTOS_EN_CURSO = 60       # un turno sigue a la vista esta cantidad después de empezar

_DIAS_CORTOS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]


def _fecha_corta(iso: str) -> str:
    """'lun 16/09', igual que fechaCortaConDia de la PWA."""
    d = date.fromisoformat(iso)
    return f"{_DIAS_CORTOS[d.weekday()]} {d.day:02d}/{d.month:02d}"


def agenda_turnos(page: ft.Page, dias: int = 7, compacto: bool = False,
                  on_cambio=None) -> ft.Container:
    """
    Arma la agenda. `on_cambio` se llama después de cancelar un turno, para
    que la vista que la contiene se reconstruya.
    """
    turnos = app_state.get_agenda_turnos(dias)
    puede_cancelar = app_state.puede(Accion.GESTION_TURNOS) and not compacto

    if compacto:
        ahora = datetime.now()
        turnos = [
            t for t in turnos
            if not t["cancelado"]
            and datetime.fromisoformat(f"{t['fecha']}T{t['hora']}")
            >= ahora - timedelta(minutes=MINUTOS_EN_CURSO)
        ][:MAX_COMPACTO]

    titulo = "Próximos turnos" if compacto else f"Turnos de los próximos {dias} días"

    if not turnos:
        return section_card(empty_state(
            "No hay turnos por delante. Salen del horario semanal de cada "
            "actividad (sección Actividades).",
            ft.Icons.EVENT_BUSY_ROUNDED,
        ), title=titulo)

    bloques: list[ft.Control] = []
    fecha_actual = None
    for t in turnos:
        if t["fecha"] != fecha_actual:
            fecha_actual = t["fecha"]
            bloques.append(ft.Container(
                content=ft.Text(_fecha_corta(fecha_actual).upper(), color=Colors.TEXT_MUTED,
                                size=10, weight=ft.FontWeight.W_600),
                padding=ft.Padding.only(top=8, bottom=4),
            ))
        bloques.append(_fila_turno(page, t, puede_cancelar, on_cambio))

    return section_card(ft.Column(bloques, spacing=4, tight=True), title=titulo)


def _fila_turno(page: ft.Page, t: dict, puede_cancelar: bool, on_cambio) -> ft.Container:
    detalle = ft.Column(spacing=2, tight=True, visible=False)
    flecha = ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, color=Colors.TEXT_MUTED, size=16)

    def alternar(e):
        abrir = not detalle.visible
        detalle.visible = abrir
        flecha.icon = (ft.Icons.EXPAND_MORE_ROUNDED if abrir
                       else ft.Icons.CHEVRON_RIGHT_ROUNDED)
        if abrir and not detalle.controls:
            datos = app_state.get_detalle_turno(t["id"])
            detalle.controls = _lista_inscriptos(datos)
        page.update()

    def cancelar(e):
        def confirmar():
            resultado = app_state.cancelar_turno(t["id"])
            show_snack(page, resultado["mensaje"],
                       Colors.STATUS_OK if resultado["ok"] else Colors.STATUS_DANGER)
            if resultado["ok"] and on_cambio:
                on_cambio()

        anotados = (f"Hay {t['reservados']} anotado(s). Se les cancela la reserva "
                    "y la clase se les devuelve." if t["reservados"] else
                    "No hay nadie anotado.")
        open_dialog(page, confirm_dialog(
            page, f"¿Cancelar {t['actividad']} del {_fecha_corta(t['fecha'])} a las {t['hora']}?",
            anotados, on_confirm=confirmar))

    subtitulo = (t["motivo"] or "Cancelado") if t["cancelado"] else (t["profesor"] or "Sin profesor")

    fila = ft.Row([
        ft.Container(
            content=ft.Row([
                flecha,
                ft.Text(t["hora"], color=Colors.PRIMARY_VOLT, size=13,
                        weight=ft.FontWeight.BOLD, font_family=Fonts.MONO, width=48),
                ft.Column([
                    ft.Text(t["actividad"],
                            color=Colors.TEXT_MUTED if t["cancelado"] else Colors.TEXT_MAIN,
                            size=13, no_wrap=True,
                            style=ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH)
                            if t["cancelado"] else None),
                    ft.Text(subtitulo, color=Colors.TEXT_MUTED, size=11, no_wrap=True),
                ], spacing=0, tight=True, expand=True),
                ft.Row([
                    ft.Icon(ft.Icons.GROUP_ROUNDED, color=Colors.TEXT_SECONDARY, size=14),
                    ft.Text(f"{t['reservados']}/{t['cupo']}", color=Colors.TEXT_SECONDARY, size=12),
                ], spacing=4, tight=True),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            on_click=alternar,
            expand=True,
        ),
        *([ft.IconButton(ft.Icons.BLOCK_ROUNDED, icon_color=Colors.TEXT_MUTED, icon_size=16,
                         tooltip="Cancelar este turno", on_click=cancelar)]
          if puede_cancelar and not t["cancelado"] else []),
    ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    return ft.Container(
        content=ft.Column([
            fila,
            ft.Container(content=detalle, padding=ft.Padding.only(left=34, top=4, bottom=4)),
        ], spacing=0, tight=True),
        border=ft.Border.all(1, Colors.BORDER_IDLE),
        border_radius=Radius.SM,
        bgcolor=alpha(Colors.SURFACE_BASE, 0.4),
        padding=ft.Padding.symmetric(horizontal=10, vertical=6),
    )


def _lista_inscriptos(datos: dict | None) -> list[ft.Control]:
    if datos is None:
        return [ft.Text("No se pudo traer la lista de anotados.",
                        color=Colors.STATUS_DANGER, size=12)]
    if not datos["inscriptos"]:
        return [ft.Text("Todavía no se anotó nadie.", color=Colors.TEXT_MUTED, size=12)]

    filas = []
    for i in datos["inscriptos"]:
        etiqueta, color = ESTADO_INSCRIPTO.get(i["estado"], ("—", Colors.TEXT_MUTED))
        nombre = ft.Row([
            ft.Text(i["nombre"], color=Colors.TEXT_MAIN, size=13, no_wrap=True),
            *([ft.Text("clase suelta", color=Colors.TEXT_MUTED, size=10)] if i["suelta"] else []),
        ], spacing=8, tight=True)
        columna = [nombre]
        if i.get("alerta"):
            columna.append(ft.Text(i["alerta"], color=Colors.STATUS_WARN, size=11))
        filas.append(ft.Row([
            ft.Column(columna, spacing=0, tight=True, expand=True),
            ft.Text(etiqueta, color=color, size=12),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER))
    return filas
