# =============================================================================
# views/cobros.py — Cobros de recepción
# =============================================================================
# Espejo de CobrosView.tsx de la PWA. El flujo es el mismo:
#   1. Recepción busca un socio por nombre o DNI
#   2. Ve su estado de cuenta (deudas, membresía, historial de pagos)
#   3. Le cobra: renovación de membresía, deuda pendiente, plan de actividad
#      o clase suelta — todo con un único selector de método de pago arriba
#
# Los botones de cobrar todavía no mueven plata: muestran el diálogo de
# confirmación con el detalle correcto y avisan por snackbar. La operación real
# entra cuando exista la API (cada acción tiene marcado su endpoint con TODO).

import flet as ft
from app.config import Colors, Fonts, Radius, alpha
from app.state import app_state
from app.components.ui import (build_topbar, section_card, status_badge,
                               primary_button, secondary_button, search_field,
                               select_field, empty_state, divider_row, avatar,
                               show_snack, confirm_dialog, open_dialog)


class CobrosView:
    def __init__(self, page: ft.Page, router):
        self.page   = page
        self.router = router

        # Socio sobre el que se está cobrando. None = todavía no eligió a nadie.
        self._socio = None
        # Método de pago compartido por todas las acciones de esta visita.
        self._metodo = app_state.get_metodos_pago()[0]

        # Referencia al panel que se reemplaza al elegir/cambiar de socio, para
        # no tener que reconstruir la vista entera desde el router.
        self._panel_ref = ft.Ref[ft.Column]()

    # ── Construcción ─────────────────────────────────────────────────────────

    def build(self) -> ft.Column:
        topbar = build_topbar("Cobros", self._subtitulo())

        # El subtítulo del topbar es el segundo Text de la columna izquierda.
        # Se guarda la referencia para poder cambiarlo al elegir socio sin
        # reconstruir toda la pantalla.
        self._subtitulo_ctrl = topbar.content.controls[0].controls[1]

        # Topbar fijo arriba y sólo el contenido scrollea. El scroll NO va en
        # la Column exterior: con un hijo expand adentro, Flet centra todo
        # verticalmente cuando el contenido no llena la pantalla.
        return ft.Column([
            topbar,
            ft.Container(
                content=ft.Column([self._panel()], ref=self._panel_ref,
                                  spacing=0, scroll=ft.ScrollMode.AUTO,
                                  expand=True),
                padding=ft.Padding.all(24),
                expand=True,
            ),
        ], spacing=0, expand=True)

    def _subtitulo(self) -> str:
        return self._socio["nombre"] if self._socio else "Buscá un socio para empezar"

    def _panel(self) -> ft.Control:
        """Buscador si no hay socio elegido; estado de cuenta si lo hay."""
        return self._panel_cuenta() if self._socio else self._panel_busqueda()

    def _refrescar(self):
        """Vuelve a pintar el panel central sin tocar el resto de la pantalla."""
        if self._panel_ref.current:
            # Se reemplazan los hijos, no el contenedor: así la Column
            # scrolleable (y su scroll) sobrevive al cambio de socio.
            self._panel_ref.current.controls = [self._panel()]
            self._panel_ref.current.update()

        # El nombre del socio también vive en el topbar.
        if getattr(self, "_subtitulo_ctrl", None) is not None:
            self._subtitulo_ctrl.value = self._subtitulo()
            self._subtitulo_ctrl.update()

    # ── Paso 1: buscar socio ─────────────────────────────────────────────────

    def _panel_busqueda(self) -> ft.Control:
        resultados = ft.Column([], spacing=0)

        def buscar(e):
            texto = (e.control.value or "").strip().lower()
            resultados.controls.clear()

            if not texto:
                resultados.update()
                return

            # TODO: GET /api/socios?q={texto}
            encontrados = [
                s for s in app_state.get_socios()
                if texto in s["nombre"].lower()
            ][:6]

            if not encontrados:
                resultados.controls.append(
                    empty_state("Ningún socio coincide con la búsqueda.",
                                ft.Icons.SEARCH_ROUNDED)
                )
            else:
                for s in encontrados:
                    resultados.controls.append(self._fila_resultado(s))
            resultados.update()

        return section_card(
            ft.Column([
                search_field("Buscar por nombre o DNI…", width=None, on_change=buscar),
                resultados,
            ], spacing=12),
            title="Buscar socio",
        )

    def _fila_resultado(self, socio: dict) -> ft.Container:
        def elegir(e):
            self._socio = socio
            self._refrescar()

        fila = ft.Container(
            content=ft.Row([
                avatar(socio["nombre"], size=36),
                ft.Column([
                    ft.Text(socio["nombre"], color=Colors.TEXT_MAIN, size=14,
                            font_family=Fonts.BODY),
                    ft.Text(socio["plan"], color=Colors.TEXT_MUTED, size=12,
                            font_family=Fonts.BODY),
                ], spacing=1, tight=True, expand=True),
                status_badge(socio["estado"]),
            ], spacing=12),
            padding=ft.Padding.symmetric(horizontal=8, vertical=10),
            border_radius=Radius.SM,
            on_click=elegir,
            animate=ft.Animation(120),
        )

        def on_hover(e: ft.HoverEvent):
            fila.bgcolor = Colors.SURFACE_HOVER if str(e.data).lower() == "true" else None
            fila.update()

        fila.on_hover = on_hover
        return fila

    # ── Paso 2: estado de cuenta y cobro ─────────────────────────────────────

    def _panel_cuenta(self) -> ft.Control:
        cuenta = app_state.get_cuenta_socio(self._socio["id"])

        bloques = [
            self._ficha_socio(cuenta),
        ]

        # Las deudas van primero: mientras haya una pendiente, la regla de
        # negocio de la web bloquea comprar planes y clases sueltas.
        if cuenta["total_adeudado"] > 0:
            bloques.append(ft.Container(height=16))
            bloques.append(self._bloque_deudas(cuenta))

        bloques += [
            ft.Container(height=16),
            self._bloque_membresia(cuenta),
            ft.Container(height=16),
            self._bloque_actividades(),
            ft.Container(height=16),
            self._bloque_historial(cuenta),
        ]

        return ft.Column(bloques, spacing=0)

    def _ficha_socio(self, cuenta: dict) -> ft.Control:
        def cambiar(e):
            self._socio = None
            self._refrescar()

        return section_card(
            ft.Column([
                ft.Row([
                    avatar(self._socio["nombre"], size=44),
                    ft.Column([
                        ft.Text(self._socio["nombre"], color=Colors.TEXT_MAIN,
                                size=18, weight=ft.FontWeight.W_600,
                                font_family=Fonts.TITLE),
                        ft.Text(f"{cuenta['plan']} · vence el {cuenta['vencimiento']}",
                                color=Colors.TEXT_SECONDARY, size=14,
                                font_family=Fonts.BODY),
                    ], spacing=1, tight=True, expand=True),
                    status_badge(cuenta["estado"]),
                    secondary_button("Cambiar socio", on_click=cambiar),
                ], spacing=14),
                # El hueco es de 18 y no de 6 porque la etiqueta flotante del
                # desplegable ("Método de pago") se dibuja por encima del
                # campo y con menos aire se montaba sobre la fila del socio.
                ft.Container(height=18),
                # Un solo selector de método para toda la visita del socio: en
                # recepción se cobran varias cosas seguidas casi siempre con el
                # mismo medio.
                ft.Row([
                    select_field("Método de pago", app_state.get_metodos_pago(),
                                 value=self._metodo, width=260,
                                 on_change=self._cambiar_metodo),
                ]),
            ], spacing=0),
        )

    def _cambiar_metodo(self, e):
        self._metodo = e.control.value

    def _bloque_deudas(self, cuenta: dict) -> ft.Control:
        filas = [
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.WARNING_ROUNDED, color=Colors.STATUS_DANGER, size=18),
                    ft.Text("Tiene que regularizar la deuda antes de comprar planes "
                            "o clases sueltas.",
                            color=Colors.STATUS_DANGER, size=14, font_family=Fonts.BODY),
                ], spacing=10),
                bgcolor=alpha(Colors.STATUS_DANGER, 0.10),
                border_radius=Radius.SM,
                padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            ),
            ft.Container(height=12),
        ]

        for d in cuenta["deudas"]:
            filas.append(
                ft.Container(
                    content=ft.Row([
                        ft.Column([
                            ft.Text(_moneda(d["monto"]), color=Colors.TEXT_MAIN,
                                    size=15, weight=ft.FontWeight.W_600,
                                    font_family=Fonts.MONO),
                            ft.Text(
                                f"Generada el {d['generada']} · {d['dias_atraso']} días "
                                f"de atraso · {d['detalle']}",
                                color=Colors.TEXT_MUTED, size=12, font_family=Fonts.BODY),
                        ], spacing=2, tight=True, expand=True),
                        primary_button("Cobrar",
                                       on_click=lambda e, x=d: self._cobrar_deuda(x)),
                    ], spacing=12),
                    padding=ft.Padding.symmetric(vertical=10),
                )
            )

        return section_card(ft.Column(filas, spacing=0), title="Deudas pendientes")

    def _bloque_membresia(self, cuenta: dict) -> ft.Control:
        tipos = app_state.get_tipos_membresia()
        # El plan a cobrar arranca en el que el socio ya tiene: lo más habitual
        # es renovar el mismo.
        actual = next((t for t in tipos if t["nombre"] == cuenta["plan"]), tipos[0])
        self._tipo_elegido = actual

        def elegir_tipo(e):
            self._tipo_elegido = next(
                (t for t in tipos if str(t["id"]) == e.control.value), actual
            )

        return section_card(
            ft.Column([
                ft.Text(f"Plan actual: {cuenta['plan']} · vence el {cuenta['vencimiento']}",
                        color=Colors.TEXT_SECONDARY, size=14, font_family=Fonts.BODY),
                ft.Container(height=10),
                ft.Row([
                    select_field(
                        "Plan a cobrar",
                        [(t["id"], f"{t['nombre']} — {_moneda(t['precio'])}") for t in tipos],
                        value=str(actual["id"]), width=300, on_change=elegir_tipo,
                    ),
                    primary_button("Cobrar renovación", on_click=self._cobrar_membresia),
                ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ], spacing=0),
            title="Membresía",
        )

    def _bloque_actividades(self) -> ft.Control:
        tarjetas = []
        for act in app_state.get_actividades():
            if not act["activa"]:
                continue

            planes = [
                ft.Container(
                    content=ft.Row([
                        ft.Column([
                            ft.Text(p["nombre"], color=Colors.TEXT_MAIN, size=14,
                                    font_family=Fonts.BODY),
                            ft.Text(_moneda(p["precio"]), color=Colors.TEXT_SECONDARY,
                                    size=12, font_family=Fonts.MONO),
                        ], spacing=1, tight=True, expand=True),
                        primary_button("Cobrar",
                                       on_click=lambda e, a=act, x=p: self._cobrar_plan(a, x)),
                    ], spacing=10),
                    padding=ft.Padding.symmetric(vertical=8),
                )
                for p in act["planes"] if p["activo"]
            ]

            tarjetas.append(
                ft.Container(
                    col={"xs": 12, "md": 6, "xl": 4},
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.EVENT_AVAILABLE, color=Colors.PRIMARY_VOLT, size=18),
                            ft.Text(act["nombre"], color=Colors.TEXT_MAIN, size=18,
                                    weight=ft.FontWeight.W_600, font_family=Fonts.TITLE),
                        ], spacing=8),
                        ft.Container(height=8),
                        *planes,
                        ft.Container(height=6),
                        secondary_button(
                            f"Clase suelta ({_moneda(act['precio_suelta'])})",
                            icon=ft.Icons.ADD_ROUNDED,
                            on_click=lambda e, a=act: self._cobrar_clase_suelta(a),
                        ),
                    ], spacing=0),
                    bgcolor=Colors.SURFACE_CARD,
                    border_radius=Radius.MD,
                    border=ft.Border.all(1, Colors.BORDER_IDLE),
                    padding=20,
                )
            )

        return ft.Column([
            ft.Text("Actividades", color=Colors.TEXT_MAIN, size=18,
                    weight=ft.FontWeight.W_600, font_family=Fonts.TITLE),
            ft.Container(height=12),
            ft.ResponsiveRow(tarjetas, spacing=16, run_spacing=16),
        ], spacing=0)

    def _bloque_historial(self, cuenta: dict) -> ft.Control:
        if not cuenta["pagos"]:
            return section_card(empty_state("Todavía no tiene pagos registrados."),
                                title="Historial de pagos")

        filas = []
        for i, p in enumerate(cuenta["pagos"]):
            filas.append(
                ft.Container(
                    content=ft.Row([
                        ft.Column([
                            ft.Text(_moneda(p["monto"]), color=Colors.TEXT_MAIN, size=14,
                                    font_family=Fonts.MONO),
                            ft.Text(f"{p['fecha']} · {p['metodo']} · Comp. {p['comprobante']}",
                                    color=Colors.TEXT_MUTED, size=12, font_family=Fonts.BODY),
                        ], spacing=1, tight=True, expand=True),
                        status_badge(p["estado"]),
                    ], spacing=12),
                    padding=ft.Padding.symmetric(vertical=10),
                )
            )
            if i < len(cuenta["pagos"]) - 1:
                filas.append(divider_row())

        return section_card(ft.Column(filas, spacing=0), title="Historial de pagos")

    # ── Acciones de cobro ────────────────────────────────────────────────────
    # Ninguna escribe todavía: abren el diálogo con el detalle exacto y avisan.
    # Cuando exista FastAPI, el on_confirm de cada una llama a su endpoint.

    def _cobrar_deuda(self, deuda: dict):
        def confirmar():
            # TODO: POST /api/deudas/{id}/pagar  {metodo}
            show_snack(self.page,
                       f"Deuda de {_moneda(deuda['monto'])} cobrada en {self._metodo}",
                       Colors.STATUS_OK)

        open_dialog(self.page, confirm_dialog(
            self.page,
            f"¿Cobrar deuda de {_moneda(deuda['monto'])}?",
            f"Se registra como pagada en {self._metodo}.",
            on_confirm=confirmar, texto_confirmar="Cobrar",
        ))

    def _cobrar_membresia(self, e=None):
        tipo = self._tipo_elegido

        def confirmar():
            # TODO: POST /api/membresias  {id_socio, id_tipo, metodo}
            show_snack(self.page,
                       f"Cobrado: {tipo['nombre']} en {self._metodo}",
                       Colors.STATUS_OK)

        open_dialog(self.page, confirm_dialog(
            self.page,
            f"¿Cobrar \"{tipo['nombre']}\"?",
            f"Se cobran {_moneda(tipo['precio'])} en {self._metodo}. Se suma a partir "
            f"del vencimiento actual, sin perder los días ya pagados.",
            on_confirm=confirmar, texto_confirmar="Cobrar",
        ))

    def _cobrar_plan(self, actividad: dict, plan: dict):
        def confirmar():
            # TODO: POST /api/inscripciones  {id_socio, id_plan, metodo}
            show_snack(self.page, f"Cobrado: {plan['nombre']} de {actividad['nombre']}",
                       Colors.STATUS_OK)

        open_dialog(self.page, confirm_dialog(
            self.page,
            f"¿Cobrar \"{plan['nombre']}\"?",
            f"Se cobran {_moneda(plan['precio'])} en {self._metodo}.",
            on_confirm=confirmar, texto_confirmar="Cobrar",
        ))

    def _cobrar_clase_suelta(self, actividad: dict):
        def confirmar():
            # TODO: POST /api/reservas/clase-suelta  {id_socio, id_turno, metodo}
            show_snack(self.page, f"Clase suelta de {actividad['nombre']} cobrada",
                       Colors.STATUS_OK)

        open_dialog(self.page, confirm_dialog(
            self.page,
            f"¿Cobrar clase suelta de {actividad['nombre']}?",
            f"Se cobran {_moneda(actividad['precio_suelta'])} en {self._metodo}, "
            f"sin necesitar ningún plan.",
            on_confirm=confirmar, texto_confirmar="Cobrar",
        ))


def _moneda(valor) -> str:
    """Formatea un número como precio argentino: $ 28.000"""
    try:
        return f"$ {int(valor):,}".replace(",", ".")
    except (TypeError, ValueError):
        return str(valor)
