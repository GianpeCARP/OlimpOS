# =============================================================================
# views/recepcion.py — El panel del mostrador
# =============================================================================
# Lo primero que ve un recepcionista al entrar, y lo único que necesita mirar
# durante el día.
#
# La regla que ordena toda esta pantalla: el recepcionista NO debería tener
# que buscar nada. Los turnos llegan ordenados por cercanía, cada persona
# anotada trae al lado lo que hay que decirle cuando aparezca (cuota vencida,
# deuda), y el fichaje resuelve solo a qué clase corresponde el ingreso.
#
# No tiene gemelo en la PWA: es una pantalla del personal, y los socios no la
# ven. Es la única vista de esta app que no espeja un .tsx.

import threading
import time

import flet as ft
from app.config import Colors, Fonts, Radius, Routes, alpha
from app.state import app_state
from app.components.ui import (build_topbar, input_field, primary_button,
                                show_snack, open_dialog, close_dialog)

# Cada cuánto se vuelve a pedir el panel.
#
# Diez segundos: suficiente para que un ingreso aparezca antes de que la
# persona termine de guardar la tarjeta, y lo bastante espaciado como para que
# sean seis pedidos por minuto desde una sola máquina — nada.
SEGUNDOS_REFRESCO = 10

# estado derivado → (etiqueta, color, ícono)
#
# Los estados NO salen de una columna: el backend los deriva de si hay un
# ingreso registrado contra la reserva y de si ya pasó la tolerancia. Por eso
# no hay forma de que la pantalla muestre "pendiente" en un turno que venció
# hace una hora — si el reloj avanza, la respuesta cambia sola.
ESTADO_CONFIG = {
    "pendiente": ("Falta llegar", Colors.TEXT_SECONDARY, ft.Icons.SCHEDULE_ROUNDED),
    "asistio":   ("Presente",     Colors.STATUS_OK,      ft.Icons.CHECK_CIRCLE_ROUNDED),
    "ausente":   ("No llegó",     Colors.STATUS_DANGER,  ft.Icons.CANCEL_ROUNDED),
    "en_espera": ("En espera",    Colors.STATUS_WARN,    ft.Icons.HOURGLASS_EMPTY_ROUNDED),
    "cancelada": ("Canceló",      Colors.TEXT_MUTED,     ft.Icons.REMOVE_CIRCLE_OUTLINE_ROUNDED),
}


class RecepcionView:
    # Cada refresco que arranca se queda con este número. Si el recepcionista
    # entra y sale de la sección varias veces quedarían varios hilos vivos
    # pisándose entre sí; con el contador, sólo el último tiene la posta y los
    # anteriores se dan cuenta de que ya no son y terminan solos.
    #
    # Es de CLASE y no de instancia a propósito: el router crea una vista nueva
    # en cada navegación, así que un contador por instancia siempre valdría lo
    # mismo y no distinguiría nada.
    _generacion = 0

    def __init__(self, page: ft.Page, router):
        self.page = page
        self.router = router
        self.resultados_ref = ft.Ref[ft.Column]()
        self.dni_ref = ft.Ref[ft.TextField]()
        # Sólo esta parte se rearma en cada refresco. El buscador NO: si se
        # redibujara, borraría el DNI a medio tipear cada diez segundos.
        self.vivo_ref = ft.Ref[ft.Column]()

    # ── Armado ────────────────────────────────────────────────────────────────

    def build(self) -> ft.Column:
        panel = app_state.get_panel_recepcion()

        topbar = build_topbar(
            "Recepción",
            "Próximos turnos y control de ingreso",
            actions=[
                primary_button("Actualizar", ft.Icons.REFRESH_ROUNDED,
                               on_click=lambda e: self.router.navigate(Routes.RECEPCION)),
            ],
        )

        if not panel["hay_datos"]:
            cuerpo = _cartel(
                ft.Icons.CLOUD_OFF_ROUNDED,
                "No se pudo consultar el panel",
                "Revisá que el backend esté corriendo y volvé a intentar.",
                Colors.STATUS_DANGER,
            )
        else:
            cuerpo = ft.Column([
                self._buscador(),
                ft.Container(height=20),
                # Lo único que se rearma solo. Queda en su propia Column con
                # ref para poder reemplazar sus hijos sin tocar el buscador ni
                # perder la posición del scroll.
                ft.Column(ref=self.vivo_ref, controls=self._contenido_vivo(panel),
                          spacing=0),
            ], spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)
            self._arrancar_refresco()

        # El scroll va en la Column INTERNA, nunca en esta de afuera: con
        # expand=True y scroll en la exterior, Flet centra todo verticalmente y
        # la pantalla arranca con un hueco enorme arriba.
        return ft.Column([
            topbar,
            ft.Container(content=cuerpo, padding=ft.Padding.all(24), expand=True),
        ], spacing=0, expand=True)

    def _contenido_vivo(self, panel: dict) -> list:
        """El resumen y los turnos: lo que cambia solo."""
        return [
            self._resumen(panel),
            ft.Container(height=20),
            self._lista_de_turnos(panel),
        ]

    # ── Refresco automático ───────────────────────────────────────────────────

    def _arrancar_refresco(self):
        """
        Vuelve a pedir el panel cada pocos segundos, en un hilo aparte.

        Por qué polling y no WebSocket: esta pantalla cambia sola CON EL RELOJ.
        "en 9 min" pasa a "en 8 min" sin que ocurra nada en el servidor, así
        que hace falta un timer exista o no una conexión push. Y si el timer
        va a estar corriendo igual, volver a pedir el panel cuesta un GET. Un
        WebSocket sumaría ciclo de vida de conexión, reconexión y broadcast en
        el backend para ganar unos segundos que en un mostrador nadie percibe.

        El hilo es daemon: si alguien cierra la ventana, no queda vivo
        impidiendo que el proceso termine.
        """
        RecepcionView._generacion += 1
        mia = RecepcionView._generacion

        def bucle():
            while True:
                time.sleep(SEGUNDOS_REFRESCO)

                # Tres motivos para terminar, y los tres importan:
                #   - se navegó a otra sección (el panel ya no está en pantalla)
                #   - se cerró la sesión
                #   - arrancó un refresco más nuevo y este quedó viejo
                if (RecepcionView._generacion != mia
                        or not app_state.logged_in
                        or app_state.current_route != Routes.RECEPCION):
                    return

                try:
                    panel = app_state.get_panel_recepcion()
                    if not panel["hay_datos"]:
                        # El backend se cayó. Se deja lo último que se mostró
                        # en vez de vaciar la pantalla: datos de hace diez
                        # segundos son más útiles que una pantalla en blanco,
                        # y el mostrador sigue trabajando.
                        continue
                    destino = self.vivo_ref.current
                    if destino is None:
                        return
                    destino.controls = self._contenido_vivo(panel)
                    destino.update()
                except Exception:  # noqa: BLE001
                    # Nunca dejar que este hilo tire la app: corre de fondo y
                    # nadie lo está mirando. Si algo falla, se espera al
                    # próximo ciclo — el de arriba ya cubre el caso normal
                    # (backend caído) y esto es la red por si acaso.
                    continue

        threading.Thread(target=bucle, daemon=True).start()

    # ── Buscador por DNI ──────────────────────────────────────────────────────

    def _buscador(self) -> ft.Container:
        """
        Búsqueda por DNI, no por nombre.

        En el mostrador la persona TIENE el documento en la mano: se tipea sin
        ambigüedad, no tiene acentos y no hay dos socios con el mismo. Buscar
        "gonzalez" devuelve cuatro personas y obliga a preguntar cuál; el DNI
        devuelve una. Acepta los últimos dígitos, que es como la gente los
        dicta.
        """
        campo = input_field(
            "Buscar por DNI", "Ej: 30123456 o los últimos 4",
            icon=ft.Icons.BADGE_OUTLINED, ref=self.dni_ref,
        )
        # on_submit además del botón: en un mostrador se tipea y se aprieta
        # Enter sin soltar el teclado.
        campo.on_submit = lambda e: self._buscar()

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Container(content=campo, expand=True),
                    ft.Container(width=12),
                    primary_button("Buscar", ft.Icons.SEARCH_ROUNDED,
                                   on_click=lambda e: self._buscar()),
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Column(ref=self.resultados_ref, spacing=8),
            ], spacing=12),
            bgcolor=Colors.BG_CARD,
            border=ft.Border.all(1, Colors.BORDER),
            border_radius=Radius.LG,
            padding=20,
        )

    def _buscar(self, e=None):
        dni = (self.dni_ref.current.value or "").strip() if self.dni_ref.current else ""
        contenedor = self.resultados_ref.current
        if contenedor is None:
            return

        if len(dni) < 2:
            contenedor.controls = [
                ft.Text("Escribí al menos 2 dígitos del DNI.",
                        color=Colors.TEXT_MUTED, size=12)
            ]
            contenedor.update()
            return

        encontrados = app_state.buscar_socio_por_dni(dni)
        if not encontrados:
            contenedor.controls = [
                ft.Text(f"Ningún socio con un DNI que contenga «{dni}».",
                        color=Colors.STATUS_WARN, size=13)
            ]
        else:
            contenedor.controls = [self._ficha(s) for s in encontrados]
        contenedor.update()

    def _ficha(self, s: dict) -> ft.Container:
        """
        El resultado de la búsqueda, con todo lo que se iba a preguntar después.

        Membresía, deuda y próximo turno vienen en la misma respuesta a
        propósito: una sola búsqueda tiene que cerrar la conversación, no abrir
        tres pantallas más.
        """
        color_mem = {
            "Activa": Colors.STATUS_OK,
            "Vencida": Colors.STATUS_DANGER,
            "Sin membresía": Colors.TEXT_MUTED,
        }.get(s["membresia"], Colors.TEXT_SECONDARY)

        filas = [
            ft.Row([
                ft.Text(s["nombre"], color=Colors.TEXT_PRIMARY, size=15,
                        weight=ft.FontWeight.BOLD),
                ft.Text(f"DNI {s['dni']}", color=Colors.TEXT_MUTED, size=12,
                        font_family=Fonts.MONO),
                ft.Text(f"N° {s['numero_socio']}", color=Colors.TEXT_MUTED, size=12),
                ft.Container(
                    content=ft.Text(s["membresia"], color=color_mem, size=11,
                                    weight=ft.FontWeight.W_500),
                    bgcolor=alpha(color_mem, 0.12), border_radius=20,
                    padding=ft.Padding.symmetric(horizontal=10, vertical=3),
                ),
            ], spacing=12, wrap=True),
        ]

        if s["alerta"]:
            filas.append(ft.Row([
                ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=Colors.STATUS_WARN, size=14),
                ft.Text(s["alerta"], color=Colors.STATUS_WARN, size=12),
            ], spacing=6))

        if s["proximo"]:
            p = s["proximo"]
            filas.append(ft.Row([
                ft.Icon(ft.Icons.EVENT_AVAILABLE_ROUNDED, color=Colors.INFO, size=14),
                ft.Text(f"Próximo turno: {p['actividad']} {p['hora']} ({p['cuando']})",
                        color=Colors.TEXT_SECONDARY, size=12),
            ], spacing=6))
        else:
            filas.append(ft.Text("Sin turnos reservados.",
                                 color=Colors.TEXT_MUTED, size=12))

        # Fichar desde acá y no desde otra pantalla: la persona ya está
        # identificada, pedirle que el operador la busque de nuevo en Asistencia
        # sería hacerle repetir el trabajo que acaba de hacer.
        filas.append(ft.Row([
            primary_button("Registrar ingreso", ft.Icons.LOGIN_ROUNDED,
                           on_click=lambda e, x=s: self._fichar(x)),
        ]))

        return ft.Container(
            content=ft.Column(filas, spacing=8),
            bgcolor=Colors.BG_INPUT,
            border=ft.Border.all(1, Colors.BORDER),
            border_radius=Radius.MD,
            padding=14,
        )

    def _fichar(self, socio: dict):
        """
        Registra el ingreso. El sistema resuelve solo a qué clase corresponde.

        El recepcionista no elige el turno ni tilda nada: si la persona tenía
        una reserva vigente, el backend se la acredita; si se le pasó la
        tolerancia, avisa cuál perdió. En los dos casos el ingreso queda
        registrado — perder la clase no es motivo para no dejar entrar a
        alguien con la cuota paga.
        """
        r = app_state.fichar_manual(socio["id"])
        if not r["ok"]:
            show_snack(self.page, r["mensaje"], Colors.STATUS_DANGER)
            return
        # Verde si no hubo objeciones, ámbar si entró con advertencia (deuda,
        # cuota vencida). Nunca rojo: el ingreso SE registró igual.
        color = Colors.SUCCESS if r.get("permitido", True) else Colors.STATUS_WARN
        show_snack(self.page, r["mensaje"], color)
        self.router.navigate(Routes.RECEPCION)

    # ── Resumen del día ───────────────────────────────────────────────────────

    def _resumen(self, panel: dict) -> ft.Row:
        return ft.Row([
            _tarjeta("Anotados hoy", str(panel["anotados"]),
                     ft.Icons.EVENT_NOTE_ROUNDED, Colors.INFO),
            _tarjeta("Ya ingresaron", str(panel["presentes"]),
                     ft.Icons.HOW_TO_REG_ROUNDED, Colors.STATUS_OK),
            _tarjeta("Turnos activos", str(len(panel["turnos"])),
                     ft.Icons.SCHEDULE_ROUNDED, Colors.PRIMARY_VOLT),
        ], spacing=16)

    # ── Turnos ────────────────────────────────────────────────────────────────

    def _lista_de_turnos(self, panel: dict) -> ft.Column:
        bloques = [
            ft.Text("Próximos turnos", color=Colors.TEXT_PRIMARY, size=16,
                    weight=ft.FontWeight.BOLD),
            ft.Container(height=12),
        ]

        if not panel["turnos"]:
            bloques.append(_cartel(
                ft.Icons.EVENT_BUSY_ROUNDED,
                "No hay turnos en las próximas horas",
                "Los turnos se generan solos a partir del horario semanal de "
                "cada actividad. Si esto está vacío, todavía no hay horarios "
                "cargados en Actividades.",
                Colors.TEXT_MUTED,
            ))
        else:
            for t in panel["turnos"]:
                bloques.append(self._turno(t))
                bloques.append(ft.Container(height=12))

        # Los vencidos van aparte y NO se pueden marcar. Están sólo para que el
        # mostrador pueda explicar el reclamo de alguien que llegó tarde: sin
        # esto, el turno simplemente desaparece y nadie entiende por qué.
        if panel["vencidos"]:
            bloques += [
                ft.Container(height=12),
                ft.Row([
                    ft.Icon(ft.Icons.HISTORY_ROUNDED, color=Colors.TEXT_MUTED, size=16),
                    ft.Text("Vencidos hace poco", color=Colors.TEXT_MUTED, size=14,
                            weight=ft.FontWeight.W_600),
                ], spacing=8),
                ft.Text("Ya no se pueden marcar. Se muestran para poder explicar "
                        "por qué no figuran arriba.",
                        color=Colors.TEXT_MUTED, size=11),
                ft.Container(height=8),
            ]
            for t in panel["vencidos"]:
                bloques.append(self._turno(t, vencido=True))
                bloques.append(ft.Container(height=12))

        return ft.Column(bloques, spacing=0)

    def _turno(self, t: dict, vencido: bool = False) -> ft.Container:
        borde = Colors.STATUS_DANGER if vencido else (
            Colors.PRIMARY_VOLT if t["faltan"] <= 15 else Colors.BORDER
        )

        encabezado = ft.Row([
            ft.Container(
                content=ft.Text(t["hora"], color=Colors.TEXT_PRIMARY, size=16,
                                weight=ft.FontWeight.BOLD, font_family=Fonts.MONO),
                bgcolor=Colors.BG_INPUT, border_radius=Radius.SM,
                padding=ft.Padding.symmetric(horizontal=10, vertical=6),
            ),
            ft.Column([
                ft.Text(t["actividad"], color=Colors.TEXT_PRIMARY, size=15,
                        weight=ft.FontWeight.BOLD),
                ft.Text(f"{t['cuando']} · prof. {t['profesor']}",
                        color=Colors.TEXT_MUTED, size=11),
            ], spacing=1, tight=True, expand=True),
            ft.Column([
                ft.Text(f"{t['ocupados']}/{t['cupo']}", color=Colors.TEXT_PRIMARY,
                        size=14, weight=ft.FontWeight.BOLD, font_family=Fonts.MONO),
                ft.Text("anotados", color=Colors.TEXT_MUTED, size=10),
            ], spacing=0, tight=True,
               horizontal_alignment=ft.CrossAxisAlignment.END),
            *([ft.Container(
                content=ft.Text(f"{t['en_espera']} en espera",
                                color=Colors.STATUS_WARN, size=11),
                bgcolor=alpha(Colors.STATUS_WARN, 0.12), border_radius=20,
                padding=ft.Padding.symmetric(horizontal=10, vertical=4),
            )] if t["en_espera"] else []),
            ft.Text(f"vence {t['vence']}", color=Colors.TEXT_MUTED, size=11),
        ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        cuerpo = [encabezado]

        # La sala abierta se colapsa: 40 nombres taparían las clases de 15, que
        # es donde el cupo importa de verdad. Se expande pidiendo ese turno.
        if t["sala_abierta"]:
            cuerpo += [
                ft.Container(height=8),
                ft.Row([
                    ft.Icon(ft.Icons.FITNESS_CENTER_ROUNDED,
                            color=Colors.TEXT_MUTED, size=14),
                    ft.Text(f"Sala abierta — {t['ocupados']} anotados. "
                            "No se listan uno por uno.",
                            color=Colors.TEXT_MUTED, size=12),
                ], spacing=6),
            ]
        elif t["inscriptos"]:
            cuerpo.append(ft.Container(height=10))
            cuerpo.append(ft.Divider(height=1, color=Colors.BORDER))
            cuerpo.append(ft.Container(height=8))
            for i in t["inscriptos"]:
                cuerpo.append(self._inscripto(i, vencido))
        else:
            cuerpo += [
                ft.Container(height=8),
                ft.Text("Nadie anotado todavía.", color=Colors.TEXT_MUTED, size=12),
            ]

        return ft.Container(
            content=ft.Column(cuerpo, spacing=0),
            bgcolor=Colors.BG_CARD,
            border=ft.Border.all(1, borde),
            border_radius=Radius.LG,
            padding=16,
        )

    def _inscripto(self, i: dict, vencido: bool) -> ft.Container:
        etiqueta, color, icono = ESTADO_CONFIG.get(
            i["estado"], ("—", Colors.TEXT_MUTED, ft.Icons.HELP_OUTLINE_ROUNDED)
        )

        # El botón de marcar sólo aparece donde tiene sentido: alguien que
        # todavía puede llegar. Mostrarlo en un ausente o en un turno vencido
        # invitaría a apretarlo para "arreglar" algo que el sistema ya decidió.
        puede_marcarse = (not vencido) and i["estado"] == "pendiente"

        return ft.Container(
            content=ft.Row([
                ft.Icon(icono, color=color, size=16),
                ft.Column([
                    ft.Text(i["nombre"], color=Colors.TEXT_PRIMARY, size=13),
                    ft.Text(f"DNI {i['dni']}", color=Colors.TEXT_MUTED, size=10,
                            font_family=Fonts.MONO),
                ], spacing=0, tight=True, expand=True),
                *([ft.Container(
                    content=ft.Text("Clase suelta", color=Colors.INFO, size=10),
                    bgcolor=alpha(Colors.INFO, 0.12), border_radius=20,
                    padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                )] if i["suelta"] else []),
                *([ft.Row([
                    ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED,
                            color=Colors.STATUS_WARN, size=13),
                    ft.Text(i["alerta"], color=Colors.STATUS_WARN, size=11),
                ], spacing=4)] if i["alerta"] else []),
                ft.Text(etiqueta, color=color, size=12, weight=ft.FontWeight.W_500),
                *([ft.IconButton(
                    ft.Icons.HOW_TO_REG_ROUNDED, icon_color=Colors.PRIMARY_VOLT,
                    icon_size=18, tooltip="Registrar ingreso",
                    on_click=lambda e, x=i: self._fichar({"id": x["id_socio"]}),
                )] if puede_marcarse else []),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding.symmetric(vertical=6),
        )


# =============================================================================
# AUXILIARES
# =============================================================================

def _tarjeta(label: str, valor: str, icono: str, color: str) -> ft.Container:
    return ft.Container(
        content=ft.Row([
            ft.Container(
                content=ft.Icon(icono, color=color, size=20),
                width=42, height=42, border_radius=Radius.MD,
                bgcolor=alpha(color, 0.12), alignment=ft.Alignment.CENTER,
            ),
            ft.Column([
                ft.Text(valor, color=Colors.TEXT_PRIMARY, size=22,
                        weight=ft.FontWeight.BOLD, font_family=Fonts.MONO),
                ft.Text(label, color=Colors.TEXT_MUTED, size=11),
            ], spacing=0, tight=True),
        ], spacing=12),
        bgcolor=Colors.BG_CARD,
        border=ft.Border.all(1, Colors.BORDER),
        border_radius=Radius.LG,
        padding=16,
        expand=True,
    )


def _cartel(icono: str, titulo: str, detalle: str, color: str) -> ft.Container:
    """Estado vacío o de error. Dice qué pasó y qué hacer, no sólo que no hay nada."""
    return ft.Container(
        content=ft.Column([
            ft.Icon(icono, color=color, size=36),
            ft.Container(height=10),
            ft.Text(titulo, color=Colors.TEXT_PRIMARY, size=15,
                    weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
            ft.Container(height=6),
            ft.Text(detalle, color=Colors.TEXT_MUTED, size=12,
                    text_align=ft.TextAlign.CENTER),
        ], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor=Colors.BG_CARD,
        border=ft.Border.all(1, Colors.BORDER),
        border_radius=Radius.LG,
        padding=40,
        alignment=ft.Alignment.CENTER,
    )
