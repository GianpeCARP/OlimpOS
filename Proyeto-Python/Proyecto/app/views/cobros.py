# =============================================================================
# views/cobros.py — Cobros de recepción
# =============================================================================
# Espejo de CobrosView.tsx de la PWA. El flujo es el mismo:
#   1. Recepción busca un socio por nombre o DNI
#   2. Ve su estado de cuenta (deudas, membresía, historial de pagos)
#   3. Le cobra: renovación de membresía, deuda pendiente, plan de actividad
#      o clase suelta — todo con un único selector de método de pago arriba
#
# Todas las acciones escriben contra la API real.
#
# El Dueño tiene además el botón "Promociones" en el topbar: los descuentos se
# administran acá porque acá es donde se aplican, y no en una sección propia
# —eso obligaría a sumar una entrada a las TRES copias de la matriz de permisos
# para una pantalla que usa un solo rol.

import flet as ft
from app.config import Colors, Fonts, Radius, alpha
from app.permisos import Accion
from app.state import app_state
from app.components.ui import (build_topbar, section_card, status_badge,
                               primary_button, secondary_button, search_field,
                               select_field, input_field, empty_state,
                               divider_row, avatar,
                               show_snack, confirm_dialog, open_dialog, close_dialog)


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

        # Promoción elegida para el cobro. None = a precio de lista.
        self._promo_elegida = None
        # Ref al renglón que muestra lista / descuento / final. Se actualiza
        # solo, sin reconstruir el bloque entero: rearmar la tarjeta en cada
        # cambio del desplegable haría parpadear el resto de la pantalla.
        self._previa_ref = ft.Ref[ft.Text]()

    # ── Construcción ─────────────────────────────────────────────────────────

    def build(self) -> ft.Column:
        # El botón sólo existe para quien tenga GESTION_PROMOCIONES, que en la
        # matriz es únicamente el Dueño. El Recepcionista SÍ ve el desplegable
        # de promociones al cobrar —lo necesita— pero no esta pantalla, que es
        # donde se inventan. El guard de verdad está en el backend; el de acá
        # es para no ofrecer algo que va a volver 403.
        acciones = []
        if app_state.puede(Accion.GESTION_PROMOCIONES):
            acciones.append(primary_button(
                "Promociones", ft.Icons.LOCAL_OFFER_ROUNDED,
                on_click=self._abrir_promociones,
            ))
        topbar = build_topbar("Cobros", self._subtitulo(), actions=acciones)

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

            # Filtrado en memoria sobre la lista que ya vino: son decenas de
            # socios, no miles, y un endpoint de búsqueda por cada tecla sería
            # un pedido por letra tipeada.
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

        # Solo las VIGENTES: el mostrador no tiene por qué poder elegir una de
        # enero en marzo. El backend igual la rechazaría, pero ofrecerla y
        # después negarla es hacerle perder el tiempo a quien está cobrando.
        promos = app_state.get_promociones(solo_vigentes=True)
        self._promo_elegida = None

        def elegir_tipo(e):
            self._tipo_elegido = next(
                (t for t in tipos if str(t["id"]) == e.control.value), actual
            )
            self._refrescar_previa()

        def elegir_promo(e):
            valor = e.control.value
            self._promo_elegida = next(
                (p for p in promos if str(p["id"]) == valor), None
            )
            self._refrescar_previa()

        controles = [
            ft.Text(f"Plan actual: {cuenta['plan']} · vence el {cuenta['vencimiento']}",
                    color=Colors.TEXT_SECONDARY, size=14, font_family=Fonts.BODY),
            ft.Container(height=10),
        ]

        fila = [
            select_field(
                "Plan a cobrar",
                [(t["id"], f"{t['nombre']} — {_moneda(t['precio'])}") for t in tipos],
                value=str(actual["id"]), width=300, on_change=elegir_tipo,
            ),
        ]

        # El desplegable solo aparece si hay alguna vigente: uno vacío que dice
        # "Sin promoción" y no ofrece nada más es ruido en la pantalla que más
        # se usa del sistema.
        if promos:
            fila.append(select_field(
                "Promoción",
                # La opción vacía va primera y es la que queda seleccionada:
                # sin ella no habría forma de VOLVER a precio de lista después
                # de haber elegido una.
                [("", "Sin promoción")]
                + [(p["id"], f"{p['nombre']} — {p['etiqueta']}") for p in promos],
                value="", width=280, on_change=elegir_promo,
            ))

        fila.append(primary_button("Cobrar renovación", on_click=self._cobrar_membresia))
        controles.append(ft.Row(fila, spacing=12,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER))

        # Las tres cifras, no solo la final: quien cobra tiene que poder
        # decirle al socio cuánto era y cuánto se le descontó.
        controles += [
            ft.Container(height=8),
            ft.Text("", ref=self._previa_ref, color=Colors.PRIMARY_VOLT, size=13,
                    font_family=Fonts.BODY, visible=False),
        ]

        return section_card(ft.Column(controles, spacing=0), title="Membresía")

    def _refrescar_previa(self):
        """
        Consulta cuánto saldría y lo muestra. NO multiplica nada acá.

        El descuento lo calcula el backend (`/promociones/{id}/vista-previa`), y
        es a propósito: si esta pantalla hiciera la cuenta, la fórmula —con su
        piso en cero y su redondeo— quedaría escrita en tres lugares (acá, en la
        PWA y en el backend) y el día que cambie una regla, la vista previa
        mostraría un número y el cobro registraría otro.
        """
        renglon = self._previa_ref.current
        if renglon is None:
            return

        if not self._promo_elegida or not self._tipo_elegido:
            renglon.visible = False
            renglon.update()
            return

        previa = app_state.vista_previa_descuento(
            self._promo_elegida["id"], self._tipo_elegido["id"])
        if previa is None:
            renglon.visible = False
            renglon.update()
            return

        renglon.value = (
            f"{_moneda(previa['lista'])}  →  {_moneda(previa['final'])}"
            f"   (ahorra {_moneda(previa['descuento'])} con «{previa['promocion']}»)"
        )
        renglon.visible = True
        renglon.update()

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
    # Cada una confirma primero y después llama a la API. El monto NUNCA viaja
    # en el pedido: se manda el plan y el backend busca su precio. Si el monto
    # viniera de acá, cualquiera con la app abierta podría cobrar $1 una
    # membresía de $30.000 y en la base quedaría un pago perfectamente válido.

    def _resolver(self, resultado: dict):
        """
        Muestra el resultado y refresca la ficha si la operación escribió algo.

        El texto del error lo redacta el BACKEND: "no tiene la cuota al día",
        "el turno ya está completo (15 lugares)". Reescribirlo acá lo volvería
        genérico justo cuando más precisión hace falta — el mostrador necesita
        saber qué hacer, no que algo falló.
        """
        if not resultado["ok"]:
            show_snack(self.page, resultado["mensaje"], Colors.STATUS_DANGER)
            return
        show_snack(self.page, resultado["mensaje"], Colors.STATUS_OK)
        # Se relee la cuenta del socio: un cobro cambia su estado, su
        # vencimiento y su lista de pagos, y dejar la pantalla con los datos
        # viejos invita a cobrar dos veces.
        self._refrescar()

    def _cobrar_deuda(self, deuda: dict):
        """
        Saldar una deuda suelta.

        Hoy pasa por el mismo cobro de membresía, que ya salda las deudas
        pendientes del socio como parte de la operación (saldar_deudas=True en
        el backend). Un endpoint dedicado sólo para deudas todavía no existe:
        cuando exista, esta función lo llama y el resto de la pantalla no se
        entera.
        """
        def confirmar():
            show_snack(
                self.page,
                "Las deudas se saldan al cobrar la próxima membresía. "
                "Cobrale el plan y se cancelan solas.",
                Colors.STATUS_WARN,
            )

        open_dialog(self.page, confirm_dialog(
            self.page,
            f"¿Cobrar deuda de {_moneda(deuda['monto'])}?",
            "Al cobrar la próxima membresía, esta deuda se salda "
            "automáticamente con ese mismo pago.",
            on_confirm=confirmar, texto_confirmar="Entendido",
        ))


    # ── Promociones ───────────────────────────────────────────────────────────
    #
    # Administración de descuentos. Gemelo de PromocionesPanel.tsx en la PWA.
    #
    # Vive dentro de Cobros y no en su propia sección del menú porque las
    # secciones no son una decisión de esta pantalla: son las entradas de la
    # matriz de permisos, y la matriz está copiada en TRES lugares
    # (app/permisos.py, backend/permisos.py y config.ts de la PWA). Sumar una
    # sección para un panel que usa un solo rol obligaría a tocar las tres y a
    # que check_permisos.py las siga viendo iguales. Cobros ya es donde se
    # aplica el descuento; el catálogo va al lado.

    def _abrir_promociones(self, e=None):
        """Lista todas: las apagadas y las vencidas también."""
        promos = app_state.get_promociones()

        filas = []
        for promo in promos:
            # Tres estados y no dos: "vigente", "dada de baja" y "activa pero
            # fuera de fecha" son distintos, y el tercero es el que confunde si
            # no se lo nombra.
            if not promo["activo"]:
                estado, color_estado = "dada de baja", Colors.TEXT_MUTED
            elif not promo["vigente"]:
                estado, color_estado = "fuera de fecha", Colors.STATUS_WARN
            else:
                estado, color_estado = "vigente", Colors.SUCCESS

            color_nombre = (Colors.TEXT_PRIMARY if promo["vigente"]
                            else Colors.TEXT_MUTED)

            filas.append(ft.Row([
                ft.Icon(ft.Icons.LOCAL_OFFER_ROUNDED,
                        color=Colors.PRIMARY_VOLT if promo["vigente"] else Colors.TEXT_MUTED,
                        size=16),
                ft.Column([
                    ft.Row([
                        ft.Text(promo["nombre"], color=color_nombre, size=13),
                        ft.Text(promo["etiqueta"], color=Colors.PRIMARY_VOLT, size=12),
                        ft.Text(estado, color=color_estado, size=11),
                    ], spacing=8),
                    ft.Text(f"{promo['desde']} — {promo['hasta']}"
                            + (f" · {promo['descripcion']}" if promo["descripcion"] else ""),
                            color=Colors.TEXT_MUTED, size=11),
                ], spacing=0, tight=True, expand=True),
                ft.IconButton(
                    ft.Icons.EDIT_ROUNDED, icon_color=Colors.INFO, icon_size=16,
                    tooltip="Editar",
                    on_click=lambda e, x=promo: self._form_promocion(dlg, x),
                ),
                ft.IconButton(
                    ft.Icons.POWER_SETTINGS_NEW_ROUNDED,
                    icon_color=Colors.DANGER if promo["activo"] else Colors.SUCCESS,
                    icon_size=16,
                    tooltip="Dar de baja" if promo["activo"] else "Reactivar",
                    on_click=lambda e, x=promo: self._alternar_promocion(dlg, x),
                ),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER))

        if not promos:
            filas.append(ft.Text("Todavía no hay ninguna promoción cargada.",
                                 color=Colors.TEXT_MUTED, size=12))

        contenido = [
            ft.Text("Descuentos sobre el precio de lista. El mostrador puede "
                    "elegirlos al cobrar, pero sólo vos podés crearlos.",
                    color=Colors.TEXT_MUTED, size=11),
            ft.Container(height=12),
            *filas,
            ft.Container(height=12),
            ft.Divider(height=1, color=Colors.BORDER),
            ft.Container(height=8),
            ft.Row([
                ft.TextButton("Nueva promoción",
                              icon=ft.Icons.ADD_ROUNDED,
                              style=ft.ButtonStyle(color=Colors.ACCENT),
                              on_click=lambda e: self._form_promocion(dlg, None)),
            ]),
        ]

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Promociones", color=Colors.TEXT_PRIMARY,
                          weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=560, height=440,
                content=ft.Column(contenido, spacing=8, tight=True,
                                  scroll=ft.ScrollMode.AUTO),
            ),
            actions=[
                ft.TextButton("Cerrar",
                              style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                              on_click=lambda e: close_dialog(self.page, dlg)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(self.page, dlg)

    def _form_promocion(self, padre, promo: dict | None):
        """
        Alta y edición, el mismo formulario. `promo` en None = alta.

        UN selector de tipo y UN campo de valor, en vez de dos campos sueltos:
        el backend rechaza que vengan los dos descuentos cargados, y con dos
        inputs la única forma de respetarlo sería confiar en que el usuario deje
        uno vacío.
        """
        close_dialog(self.page, padre)

        es_edicion = promo is not None
        es_porcentaje = (promo["porcentaje"] is not None) if es_edicion else True

        nombre_ref = ft.Ref[ft.TextField]()
        desc_ref   = ft.Ref[ft.TextField]()
        tipo_ref   = ft.Ref[ft.Dropdown]()
        valor_ref  = ft.Ref[ft.TextField]()
        desde_ref  = ft.Ref[ft.TextField]()
        hasta_ref  = ft.Ref[ft.TextField]()

        valor_inicial = ""
        if es_edicion:
            crudo = promo["porcentaje"] if es_porcentaje else promo["monto_fijo"]
            if crudo is not None:
                numero = float(crudo)
                # Sin el .0 cuando es redondo: el campo dice "20", no "20.0".
                valor_inicial = str(int(numero) if numero == int(numero) else numero)

        def guardar(e=None):
            nombre = self._texto_de(nombre_ref)
            if len(nombre) < 2:
                show_snack(self.page, "La promoción necesita un nombre.",
                           Colors.STATUS_DANGER)
                return

            try:
                valor = float(self._texto_de(valor_ref).replace(",", "."))
            except ValueError:
                show_snack(self.page, "El descuento tiene que ser un número.",
                           Colors.STATUS_DANGER)
                return
            if valor <= 0:
                show_snack(self.page, "El descuento tiene que ser mayor que cero.",
                           Colors.STATUS_DANGER)
                return

            porcentaje = (tipo_ref.current.value == "porcentaje"
                          if tipo_ref.current else True)
            if porcentaje and valor > 100:
                show_snack(self.page, "Un porcentaje no puede pasar de 100.",
                           Colors.STATUS_DANGER)
                return

            desde = self._fecha_iso_promo(self._texto_de(desde_ref))
            hasta = self._fecha_iso_promo(self._texto_de(hasta_ref))
            if not desde or not hasta:
                show_snack(self.page, "Las fechas van como dd/mm/aaaa.",
                           Colors.STATUS_DANGER)
                return
            if hasta < desde:
                show_snack(self.page, "La promoción no puede terminar antes de empezar.",
                           Colors.STATUS_DANGER)
                return

            descripcion = self._texto_de(desc_ref) or None
            if es_edicion:
                resultado = app_state.editar_promocion(
                    promo["id"], nombre, descripcion, porcentaje, valor, desde, hasta)
            else:
                resultado = app_state.crear_promocion(
                    nombre, descripcion, porcentaje, valor, desde, hasta)

            if not resultado["ok"]:
                show_snack(self.page, resultado["mensaje"], Colors.STATUS_DANGER)
                return
            close_dialog(self.page, dlg)
            show_snack(self.page, resultado["mensaje"], Colors.SUCCESS)
            self._abrir_promociones()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Editar promoción" if es_edicion else "Nueva promoción",
                          color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=440, height=420,
                content=ft.Column([
                    input_field("Nombre", "Ej: Verano 2026", ref=nombre_ref,
                                icon=ft.Icons.LOCAL_OFFER_OUTLINED,
                                value=promo["nombre"] if es_edicion else ""),
                    ft.Container(height=12),
                    input_field("Descripción (opcional)", "Ej: 20% en planes mensuales",
                                ref=desc_ref, multiline=True,
                                value=promo["descripcion"] if es_edicion else ""),
                    ft.Container(height=12),
                    select_field("Tipo de descuento",
                                 [("porcentaje", "Porcentaje (%)"),
                                  ("fijo", "Monto fijo ($)")],
                                 ref=tipo_ref,
                                 value="porcentaje" if es_porcentaje else "fijo"),
                    ft.Container(height=12),
                    input_field("Descuento", "Ej: 20", ref=valor_ref,
                                icon=ft.Icons.PERCENT_ROUNDED, value=valor_inicial),
                    ft.Container(height=12),
                    input_field("Desde", "dd/mm/aaaa", ref=desde_ref,
                                icon=ft.Icons.CALENDAR_TODAY_OUTLINED,
                                value=promo["desde"] if es_edicion else ""),
                    ft.Container(height=12),
                    input_field("Hasta", "dd/mm/aaaa", ref=hasta_ref,
                                icon=ft.Icons.CALENDAR_TODAY_OUTLINED,
                                value=promo["hasta"] if es_edicion else ""),
                ], spacing=0, tight=True, scroll=ft.ScrollMode.AUTO),
            ),
            actions=[
                ft.TextButton("Cancelar",
                              style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                              on_click=lambda e: self._volver_a_promociones(dlg)),
                ft.TextButton("Guardar",
                              style=ft.ButtonStyle(color=Colors.ACCENT),
                              on_click=guardar),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(self.page, dlg)

    def _alternar_promocion(self, padre, promo: dict):
        """Apaga o enciende. Los dos caminos, siempre."""
        if not promo["activo"]:
            resultado = app_state.reactivar_promocion(promo["id"])
            if not resultado["ok"]:
                show_snack(self.page, resultado["mensaje"], Colors.STATUS_DANGER)
                return
            # Reactivar NO le mueve las fechas: una vencida queda activa pero
            # sigue sin poder aplicarse, y si nadie lo dijera el Dueño se iría
            # creyendo que ya se puede usar.
            datos = resultado.get("data") or {}
            if datos.get("vigente") is False:
                show_snack(self.page,
                           f"«{promo['nombre']}» quedó activa, pero fuera de fecha: "
                           "cambiale las fechas para poder aplicarla.",
                           Colors.STATUS_WARN)
            else:
                show_snack(self.page, resultado["mensaje"], Colors.SUCCESS)
            close_dialog(self.page, padre)
            self._abrir_promociones()
            return

        # Se consulta el uso ANTES de preguntar: apagar una que usaron 40 socios
        # no es lo mismo que apagar una que no usó nadie, y quien decide tiene
        # que verlo en el mismo diálogo donde confirma.
        uso = app_state.uso_de_promocion(promo["id"])

        def confirmar():
            resultado = app_state.dar_de_baja_promocion(promo["id"])
            show_snack(self.page, resultado["mensaje"],
                       Colors.SUCCESS if resultado["ok"] else Colors.STATUS_DANGER)
            if resultado["ok"]:
                self._abrir_promociones()

        close_dialog(self.page, padre)
        open_dialog(self.page, confirm_dialog(
            self.page,
            f"¿Dar de baja «{promo['nombre']}»?",
            f"{uso} La promoción deja de poder aplicarse, pero la fila NO se "
            "borra: la referencian las membresías que ya se cobraron con ella.",
            on_confirm=confirmar, texto_confirmar="Dar de baja",
        ))

    def _volver_a_promociones(self, dlg):
        """Cancelar en el formulario devuelve al listado, no a la pantalla."""
        close_dialog(self.page, dlg)
        self._abrir_promociones()

    @staticmethod
    def _texto_de(ref) -> str:
        """Lee un campo aunque todavía no esté montado, sin reventar."""
        return (ref.current.value or "").strip() if ref.current else ""

    @staticmethod
    def _fecha_iso_promo(texto: str) -> str | None:
        """
        'dd/mm/aaaa' -> 'aaaa-mm-dd'. None si no se entiende.

        Se escribe a mano y no con un DatePicker por el mismo motivo que la
        fecha de diagnóstico en el historial médico: son fechas que quien las
        carga ya conoce, y navegar un calendario para tipear algo que se sabe de
        memoria es más lento. Acá, además, las dos fechas van juntas y un
        calendario obligaría a abrir dos.
        """
        texto = (texto or "").strip()
        if not texto:
            return None
        try:
            dia, mes, anio = texto.split("/")
            return f"{int(anio):04d}-{int(mes):02d}-{int(dia):02d}"
        except (ValueError, AttributeError):
            return None

    def _cobrar_membresia(self, e=None):
        tipo = self._tipo_elegido
        promo = self._promo_elegida

        # El monto del diálogo sale de la vista previa cuando hay promo:
        # mostrar el precio de lista y después cobrar otro sería pedir una
        # confirmación sobre una cifra que no es la que se va a registrar.
        previa = (app_state.vista_previa_descuento(promo["id"], tipo["id"])
                  if promo else None)
        a_cobrar = previa["final"] if previa else tipo["precio"]
        detalle_promo = (
            f" Incluye «{previa['promocion']}»: {_moneda(previa['descuento'])} "
            f"de descuento sobre {_moneda(previa['lista'])}."
            if previa else ""
        )

        def confirmar():
            resultado = app_state.cobrar_membresia(
                self._socio["id"], tipo["id"], self._metodo,
                id_promocion=promo["id"] if promo else None,
            )
            # La promo se limpia después de cobrar: dejarla puesta haría que el
            # siguiente socio que atienda el mostrador se lleve el descuento sin
            # que nadie lo haya decidido.
            self._promo_elegida = None
            self._resolver(resultado)

        open_dialog(self.page, confirm_dialog(
            self.page,
            f"¿Cobrar \"{tipo['nombre']}\"?",
            f"Se cobran {_moneda(a_cobrar)} en {self._metodo}.{detalle_promo} "
            f"Se suma a partir del vencimiento actual, sin perder los días ya pagados.",
            on_confirm=confirmar, texto_confirmar="Cobrar",
        ))

    def _cobrar_plan(self, actividad: dict, plan: dict):
        def confirmar():
            self._resolver(app_state.comprar_plan_actividad(
                self._socio["id"], plan["id"], self._metodo,
            ))

        open_dialog(self.page, confirm_dialog(
            self.page,
            f"¿Cobrar \"{plan['nombre']}\"?",
            f"Se cobran {_moneda(plan['precio'])} en {self._metodo}.",
            on_confirm=confirmar, texto_confirmar="Cobrar",
        ))

    def _cobrar_clase_suelta(self, actividad: dict):
        """
        Cobra una clase individual, sin abono.

        A diferencia de los otros tres cobros, éste necesita elegir A QUÉ
        CLASE: una clase suelta es una reserva concreta de un turno con fecha y
        hora, no un abono abierto. Por eso el diálogo lista los turnos
        disponibles en vez de confirmar directo.

        Los turnos llenos se muestran igual pero deshabilitados: esconderlos
        haría parecer que la clase no existe, cuando lo que pasa es que ya no
        entra nadie más.
        """
        turnos = app_state.get_turnos_de_actividad(actividad["id"])

        if not turnos:
            show_snack(
                self.page,
                f"No hay clases de {actividad['nombre']} programadas. "
                "Cargá un turno primero en la sección Actividades.",
                Colors.STATUS_WARN,
            )
            return

        dlg = ft.AlertDialog(modal=True)

        def cobrar(id_turno: int):
            def accion(e):
                close_dialog(self.page, dlg)
                self._resolver(app_state.comprar_clase_suelta(
                    self._socio["id"], id_turno, self._metodo,
                ))
            return accion

        filas = []
        for i, turno in enumerate(turnos):
            lleno = turno["libres"] <= 0
            filas.append(ft.Row([
                ft.Column([
                    ft.Text(f"{turno['fecha']} · {turno['hora']}",
                            color=Colors.TEXT_MAIN, size=14, font_family=Fonts.BODY),
                    ft.Text(f"{turno['profesor']} · {turno['libres']}/{turno['cupo']} lugares",
                            color=Colors.STATUS_DANGER if lleno else Colors.TEXT_MUTED,
                            size=12, font_family=Fonts.BODY),
                ], spacing=1, tight=True, expand=True),
                primary_button("Completo" if lleno else "Cobrar",
                               on_click=None if lleno else cobrar(turno["id"])),
            ], spacing=12))
            if i < len(turnos) - 1:
                filas.append(divider_row())

        dlg.title = ft.Text(f"Clase suelta de {actividad['nombre']}",
                            color=Colors.TEXT_MAIN, font_family=Fonts.TITLE)
        dlg.content = ft.Column([
            ft.Text(f"Se cobran {_moneda(actividad['precio_suelta'])} en {self._metodo}. "
                    "Elegí a qué clase se anota.",
                    color=Colors.TEXT_SECONDARY, size=13, font_family=Fonts.BODY),
            ft.Container(height=8),
            ft.Column(filas, spacing=0, scroll=ft.ScrollMode.AUTO),
        ], spacing=0, tight=True, width=460, height=340)
        dlg.actions = [
            secondary_button("Cancelar", on_click=lambda e: close_dialog(self.page, dlg)),
        ]
        dlg.bgcolor = Colors.SURFACE_CARD

        open_dialog(self.page, dlg)


def _moneda(valor) -> str:
    """Formatea un número como precio argentino: $ 28.000"""
    try:
        return f"$ {int(valor):,}".replace(",", ".")
    except (TypeError, ValueError):
        return str(valor)
