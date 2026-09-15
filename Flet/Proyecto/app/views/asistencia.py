# =============================================================================
# views/asistencia.py — Panel de asistencia de recepción
# =============================================================================
# Espejo de AsistenciaView.tsx de la PWA. Dos formas de fichar y una lista:
#   1. Tarjeta RFID: el lector se comporta como un teclado rápido que termina
#      en Enter, así que el campo se mantiene enfocado y se limpia solo — quien
#      atiende no tiene que clickear nada entre socio y socio.
#   2. Carga manual: buscador de socio para el que se olvidó la tarjeta.
#   3. Fichajes del día, del más reciente al más viejo.

import flet as ft
from app.config import Colors, Fonts, Radius, alpha
from app.state import app_state
from app.components.ui import (build_topbar, section_card, primary_button,
                               input_field, search_field, empty_state,
                               divider_row, avatar, show_snack)


class AsistenciaView:
    def __init__(self, page: ft.Page, router):
        self.page   = page
        self.router = router

        # Fichajes de la jornada, tal como los devuelve GET /asistencia/hoy.
        # Los que se registran en esta sesión se insertan al principio con el
        # id y la hora que asignó el backend, no fabricados acá.
        self._fichajes = list(app_state.get_asistencias_hoy())

        self._rfid_ref  = ft.Ref[ft.TextField]()
        self._lista_ref = ft.Ref[ft.Column]()

    # ── Construcción ─────────────────────────────────────────────────────────

    def build(self) -> ft.Column:
        topbar = build_topbar("Panel de asistencia", self._texto_subtitulo())

        cuerpo = ft.Column([
            ft.ResponsiveRow([
                ft.Container(col={"xs": 12, "lg": 6}, content=self._card_rfid()),
                ft.Container(col={"xs": 12, "lg": 6}, content=self._card_manual()),
            ], spacing=16, run_spacing=16),
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

    # ── Fichaje por tarjeta ──────────────────────────────────────────────────

    def _card_rfid(self) -> ft.Control:
        campo = input_field("Código de tarjeta", "Pasá la tarjeta o escribí el código…",
                            icon=ft.Icons.BADGE_ROUNDED, ref=self._rfid_ref)
        # El lector RFID termina la lectura con Enter: on_submit es el disparador
        # natural, sin botón de por medio.
        campo.on_submit = self._fichar_rfid

        return section_card(
            ft.Column([
                campo,
                ft.Text("El campo queda enfocado todo el tiempo: pasar la tarjeta "
                        "alcanza, no hace falta clickear nada.",
                        color=Colors.TEXT_MUTED, size=12, font_family=Fonts.BODY),
            ], spacing=8),
            title="Fichar con tarjeta",
        )

    def _fichar_rfid(self, e=None):
        codigo = (self._rfid_ref.current.value or "").strip()
        if not codigo:
            return

        # El backend resuelve el socio por su codigo_rfid y rechaza con 404 si
        # la tarjeta no corresponde a ninguno.
        resultado = app_state.fichar_rfid(codigo)

        # El campo se limpia y se reenfoca SIEMPRE, salga bien o mal: el lector
        # es un teclado que dispara solo, y si quedara texto viejo el próximo
        # pase lo concatenaría al anterior.
        self._rfid_ref.current.value = ""
        self._rfid_ref.current.focus()
        self._rfid_ref.current.update()

        self._mostrar_resultado(resultado)

    # ── Carga manual ─────────────────────────────────────────────────────────

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
                search_field("Para quien se olvidó la tarjeta…", width=None,
                             on_change=buscar),
                resultados,
            ], spacing=12),
            title="Carga manual",
        )

    def _fila_socio(self, socio: dict) -> ft.Container:
        def registrar(e):
            # Quién lo cargó no se manda: el backend lo saca de la sesión.
            self._mostrar_resultado(app_state.fichar_manual(socio["id"]))

        return ft.Container(
            content=ft.Row([
                ft.Column([
                    ft.Text(socio["nombre"], color=Colors.TEXT_MAIN, size=14,
                            font_family=Fonts.BODY),
                    ft.Text(f"DNI {socio.get('dni') or '—'}", color=Colors.TEXT_MUTED, size=12,
                            font_family=Fonts.BODY),
                ], spacing=1, tight=True, expand=True),
                primary_button("Registrar ingreso", on_click=registrar),
            ], spacing=12),
            padding=ft.Padding.symmetric(vertical=8),
        )

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
                            ft.Text(f["socio"], color=Colors.TEXT_MAIN, size=14,
                                    font_family=Fonts.BODY),
                            ft.Text(f["metodo"], color=Colors.TEXT_MUTED, size=12,
                                    font_family=Fonts.BODY),
                        ], spacing=1, tight=True, expand=True),
                        ft.Text(f["hora"], color=Colors.TEXT_SECONDARY, size=13,
                                font_family=Fonts.MONO),
                    ], spacing=12),
                    padding=ft.Padding.symmetric(vertical=9),
                )
            )
            if i < len(self._fichajes) - 1:
                filas.append(divider_row())
        return filas

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
