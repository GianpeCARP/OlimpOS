# =============================================================================
# views/asistencia.py — Panel de asistencia de recepción
# =============================================================================
# Espejo de AsistenciaView.tsx de la PWA. Una forma de fichar y una lista:
#   1. Carga manual: se busca al socio por nombre o DNI y se registra su
#      ingreso.
#   2. Fichajes del día, del más reciente al más viejo, cada uno con la opción
#      de deshacerlo.
#
# SE RETIRÓ EL FICHAJE CON TARJETA
# --------------------------------
# Había una tarjeta "Fichar con tarjeta" con un campo que se automantenía
# enfocado, pensada para un lector RFID —que funciona como un teclado rápido
# terminado en Enter—. El gimnasio no usa lector, así que ocupaba media
# pantalla del mostrador sin hacer nada. Los ingresos históricos con
# metodo_registro='RFID' siguen en la base y la lista los distingue por el
# ícono: lo que se sacó es la forma de crear nuevos, no el dato viejo.
#
# PERO EL CAMINO RFID DEL BACKEND QUEDA A PROPÓSITO. Lo que se sacó fue el campo
# de texto, que no era un lector. El fichaje con tarjeta va a volver como aparato
# físico en la puerta, cuando se compre el sensor. Por eso `Socio.codigo_rfid` y
# el `codigo_rfid` de POST /asistencia/fichar siguen ahí aunque hoy nada los use:
# parecen código muerto y no lo son. Ver "Lo que FALTA" en
# docs/ESTADO-ACTUAL.md antes de limpiarlos.
#
# EL INGRESO REPETIDO SE MARCA, NO SE FRENA
# -----------------------------------------
# Antes, el segundo ingreso del día abría un diálogo de confirmación. Se sacó:
# quien atiende el mostrador no lee el cartel —con gente en la cola lo acepta
# sin mirarlo, o deja al socio parado en la puerta—. Ahora se registra siempre
# y la lista muestra un chip "2º de hoy" al lado del nombre. El dato sigue
# estando para quien quiera mirar el caso; lo que no hay es una pantalla
# pidiéndole permiso a alguien que está apurado.

import flet as ft
from app.config import Colors, Fonts, Radius, alpha
from app.state import app_state
from app.components.ui import (build_topbar, section_card, primary_button,
                               search_field, empty_state, divider_row,
                               show_snack, confirm_dialog, open_dialog)


class AsistenciaView:
    def __init__(self, page: ft.Page, router):
        self.page   = page
        self.router = router

        # Fichajes de la jornada, tal como los devuelve GET /asistencia/hoy.
        # Los que se registran en esta sesión se insertan al principio con el
        # id y la hora que asignó el backend, no fabricados acá.
        self._fichajes = list(app_state.get_asistencias_hoy())

        self._lista_ref = ft.Ref[ft.Column]()

    # ── Construcción ─────────────────────────────────────────────────────────

    def build(self) -> ft.Column:
        topbar = build_topbar("Panel de asistencia", self._texto_subtitulo())

        cuerpo = ft.Column([
            self._card_manual(),
            ft.Container(height=16),
            self._card_fichajes(),
        ], spacing=0)

        # Topbar fijo arriba, sólo el contenido scrollea (ver dashboard.py).
        cuerpo.scroll = ft.ScrollMode.AUTO
        cuerpo.expand = True

        return ft.Column([
            topbar,
            ft.Container(content=cuerpo, padding=ft.Padding.all(24), expand=True),
        ], spacing=0, expand=True)

    def _texto_subtitulo(self) -> str:
        n = len(self._fichajes)
        return f"{n} ingreso{'' if n == 1 else 's'} hoy"

    # ── Registrar un ingreso ─────────────────────────────────────────────────

    def _card_manual(self) -> ft.Control:
        resultados = ft.Column([], spacing=0)

        def buscar(e):
            texto = (e.control.value or "").strip().lower()
            resultados.controls.clear()

            if not texto:
                resultados.update()
                return

            # El filtrado es en memoria sobre la lista que ya vino: son
            # decenas de socios, no miles, y un endpoint de búsqueda por cada
            # tecla sería un pedido por letra tipeada.
            # Por nombre O DNI y sólo activos, igual que AsistenciaView.tsx.
            encontrados = [
                s for s in app_state.get_socios()
                if s.get("activo", True)
                and (texto in s["nombre"].lower() or texto in str(s.get("dni", "")))
            ][:6]

            if not encontrados:
                resultados.controls.append(
                    empty_state("Ningún socio activo coincide.", ft.Icons.SEARCH_ROUNDED)
                )
            else:
                for s in encontrados:
                    resultados.controls.append(self._fila_socio(s))
            resultados.update()

        return section_card(
            ft.Column([
                search_field("Nombre o DNI del socio…", width=None,
                             on_change=buscar),
                resultados,
            ], spacing=12),
            title="Registrar ingreso",
        )

    def _fila_socio(self, socio: dict) -> ft.Container:
        return ft.Container(
            content=ft.Row([
                ft.Column([
                    ft.Text(socio["nombre"], color=Colors.TEXT_MAIN, size=14,
                            font_family=Fonts.BODY),
                    ft.Text(f"DNI {socio.get('dni') or '—'}", color=Colors.TEXT_MUTED, size=12,
                            font_family=Fonts.BODY),
                ], spacing=1, tight=True, expand=True),
                primary_button("Registrar ingreso",
                               on_click=lambda e, s=socio: self._registrar(s)),
            ], spacing=12),
            padding=ft.Padding.symmetric(vertical=8),
        )

    def _registrar(self, socio: dict):
        # Quién lo cargó no se manda: el backend lo saca de la sesión.
        # El ingreso repetido tampoco se pregunta: se registra y se marca en la
        # lista (ver el encabezado y routers/asistencia.py).
        self._mostrar_resultado(app_state.fichar_manual(socio["id"]))

    # ── Lista de fichajes ────────────────────────────────────────────────────

    def _card_fichajes(self) -> ft.Control:
        return section_card(
            ft.Column(self._filas_fichajes(), spacing=0, ref=self._lista_ref),
            title="Fichajes de hoy",
        )

    def _filas_fichajes(self) -> list:
        if not self._fichajes:
            return [empty_state("Todavía no hay ingresos registrados hoy.",
                                ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED)]

        filas = []
        for i, f in enumerate(self._fichajes):
            # Los ingresos viejos cargados con lector siguen en la base: el
            # ícono los distingue de los manuales.
            es_rfid = f["metodo"] == "RFID"
            filas.append(
                ft.Container(
                    content=ft.Row([
                        ft.Container(
                            content=ft.Icon(
                                ft.Icons.BADGE_ROUNDED if es_rfid else ft.Icons.EDIT_ROUNDED,
                                color=Colors.PRIMARY_VOLT if es_rfid else Colors.TEXT_MUTED,
                                size=16),
                            width=32, height=32, border_radius=Radius.SM,
                            bgcolor=alpha(Colors.PRIMARY_VOLT, 0.10) if es_rfid
                                    else Colors.SURFACE_HOVER,
                            alignment=ft.Alignment.CENTER,
                        ),
                        ft.Column([
                            self._nombre_con_chip(f),
                            ft.Text(f["metodo"], color=Colors.TEXT_MUTED, size=12,
                                    font_family=Fonts.BODY),
                        ], spacing=1, tight=True, expand=True),
                        ft.Text(f["hora"], color=Colors.TEXT_SECONDARY, size=13,
                                font_family=Fonts.MONO),
                        ft.IconButton(
                            ft.Icons.DELETE_OUTLINE_ROUNDED,
                            icon_color=Colors.TEXT_MUTED, icon_size=16,
                            tooltip="Deshacer este ingreso",
                            on_click=lambda e, x=f: self._pedir_deshacer(x),
                        ),
                    ], spacing=12),
                    padding=ft.Padding.symmetric(vertical=9),
                )
            )
            if i < len(self._fichajes) - 1:
                filas.append(divider_row())
        return filas

    def _nombre_con_chip(self, f: dict) -> ft.Control:
        """
        El nombre y, si ya había fichado hoy, un chip con el número de ingreso.

        Es lo que reemplazó al tope de un ingreso por día: el mostrador no
        frena a nadie, pero ve que esta es la segunda o la tercera vez. Gemelo
        del chip de AsistenciaView.tsx.
        """
        controles = [ft.Text(f["socio"], color=Colors.TEXT_MAIN, size=14,
                             font_family=Fonts.BODY)]

        # El backend no lo manda en los listados viejos cacheados: si no está,
        # se asume el primero y no se marca nada.
        numero = f.get("numero") or 1
        if numero > 1:
            controles.append(ft.Container(
                content=ft.Text(f"{numero}º de hoy", color=Colors.STATUS_WARN,
                                size=11, font_family=Fonts.BODY),
                bgcolor=Colors.SURFACE_HOVER,
                border_radius=Radius.SM,
                padding=ft.Padding.symmetric(horizontal=6, vertical=1),
                tooltip="Ya había fichado antes hoy",
            ))

        return ft.Row(controles, spacing=6, tight=True)

    # ── Deshacer un ingreso ──────────────────────────────────────────────────

    def _pedir_deshacer(self, f: dict):
        open_dialog(self.page, confirm_dialog(
            self.page, "¿Borrar este ingreso?",
            f"Se elimina el ingreso de {f['socio']} de las {f['hora']}. Es para el "
            "ingreso que no ocurrió —alguien que fichó por otro, o el socio "
            "equivocado—: desaparece de la lista y deja de contar en el total "
            "del día.",
            on_confirm=lambda: self._deshacer(f),
            texto_confirmar="Borrar",
        ))

    def _deshacer(self, f: dict):
        resultado = app_state.deshacer_fichaje(f["id"])
        if not resultado["ok"]:
            show_snack(self.page, resultado["mensaje"], Colors.STATUS_DANGER)
            return

        self._fichajes = [x for x in self._fichajes if x["id"] != f["id"]]
        if self._lista_ref.current:
            self._lista_ref.current.controls = self._filas_fichajes()
            self._lista_ref.current.update()
        show_snack(self.page, resultado["mensaje"], Colors.STATUS_OK)

    # ── Resultado de un fichaje ──────────────────────────────────────────────

    def _mostrar_resultado(self, resultado: dict):
        """
        Refleja en pantalla lo que contestó el backend.

        Tres desenlaces, no dos: además de "salió" y "falló" existe "se
        registró PERO hay algo que mirar" — el socio debe, o tiene la cuota
        vencida. En ese caso el ingreso SÍ queda guardado y se avisa en
        amarillo: dejar a alguien afuera del gimnasio lo decide una persona en
        el mostrador, no el sistema.
        """
        if not resultado["ok"]:
            show_snack(self.page, resultado["mensaje"], Colors.STATUS_DANGER)
            return

        fichaje = resultado.get("fichaje")
        if fichaje:
            # Se inserta el que devolvió el backend, con SU id y SU hora, en vez
            # de fabricar uno acá: si se inventara el id, el próximo refresco
            # traería la fila real y quedaría duplicada en pantalla.
            self._fichajes.insert(0, fichaje)
            if self._lista_ref.current:
                self._lista_ref.current.controls = self._filas_fichajes()
                self._lista_ref.current.update()
            # El contador del subtítulo ("N ingresos hoy") NO se refresca acá:
            # build_topbar recibe un string, no una referencia, así que no hay
            # nada a lo que apuntar. Se actualiza al volver a entrar a la
            # sección. Dejar un update que no puede funcionar sería peor que
            # esta limitación anotada.

        advertencia = resultado.get("advertencia")
        color = Colors.STATUS_WARN if advertencia else Colors.STATUS_OK
        show_snack(self.page, resultado["mensaje"], color)
