# =============================================================================
# views/actividades.py — ABM del catálogo de actividades
# =============================================================================
# Espejo de ActividadesAdminView.tsx de la PWA. Cada actividad se muestra con
# sus planes anidados: un plan suelto ("12 clases al mes") no significa nada sin
# saber de qué actividad es, así que se gestionan juntos en la misma tarjeta.
#
# Desde acá se puede: dar de alta/editar una actividad, darla de baja y
# reactivarla, agregar/editar/dar de baja sus planes, y asignarle profesores.
# Todo el diseño está armado; las escrituras esperan a la API (ver los TODO).

import flet as ft
from app.config import Colors, Fonts, Radius, alpha
from app.state import app_state
from app.components.ui import (build_topbar, section_card, primary_button,
                               secondary_button, icon_action, input_field,
                               select_field, empty_state, divider_row,
                               show_snack, confirm_dialog, form_dialog,
                               open_dialog)


class ActividadesView:
    def __init__(self, page: ft.Page, router):
        self.page   = page
        self.router = router

    # ── Construcción ─────────────────────────────────────────────────────────

    def build(self) -> ft.Column:
        # TODO: GET /api/actividades (sin filtrar por activa: el ABM también
        # tiene que mostrar las dadas de baja para poder reactivarlas)
        actividades = app_state.get_actividades()

        topbar = build_topbar(
            "Actividades",
            f"{len(actividades)} actividades en el catálogo",
            actions=[
                primary_button("Nueva actividad", ft.Icons.ADD_ROUNDED,
                               on_click=lambda e: self._form_actividad()),
            ],
        )

        if not actividades:
            cuerpo = section_card(
                empty_state("Todavía no hay actividades cargadas.",
                            ft.Icons.EVENT_AVAILABLE)
            )
        else:
            cuerpo = ft.ResponsiveRow(
                [self._card_actividad(a) for a in actividades],
                spacing=16, run_spacing=16,
            )

        # Topbar fijo arriba, sólo el contenido scrollea (ver dashboard.py).
        return ft.Column([
            topbar,
            ft.Container(
                content=ft.Column([cuerpo], spacing=0,
                                  scroll=ft.ScrollMode.AUTO, expand=True),
                padding=ft.Padding.all(24),
                expand=True,
            ),
        ], spacing=0, expand=True)

    # ── Tarjeta de actividad ─────────────────────────────────────────────────

    def _card_actividad(self, act: dict) -> ft.Container:
        activa = act["activa"]

        # Encabezado: nombre + estado + acciones
        encabezado = ft.Row([
            ft.Icon(ft.Icons.EVENT_AVAILABLE, color=Colors.PRIMARY_VOLT, size=18),
            ft.Text(act["nombre"], color=Colors.TEXT_MAIN, size=18,
                    weight=ft.FontWeight.W_600, font_family=Fonts.TITLE,
                    expand=True),
            _pill("Activa" if activa else "Inactiva",
                  Colors.STATUS_OK if activa else Colors.TEXT_MUTED),
            icon_action(
                ft.Icons.BLOCK_ROUNDED if activa else ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED,
                "Dar de baja" if activa else "Reactivar",
                on_click=lambda e, a=act: self._baja_actividad(a),
                color_hover=Colors.STATUS_DANGER if activa else Colors.STATUS_OK,
            ),
            icon_action(ft.Icons.EDIT_ROUNDED, "Editar",
                        on_click=lambda e, a=act: self._form_actividad(a)),
        ], spacing=8)

        # Datos de configuración de la actividad
        datos = ft.Row([
            _dato(f"Cupo por turno: {act['cupo']}"),
            _dato(f"Clase suelta: {_moneda(act['precio_suelta'])}"),
            _dato("Cancelación: " + (
                "sin anticipación" if act["horas_cancelacion"] == 0
                else f"{act['horas_cancelacion']}hs antes")),
        ], spacing=16, wrap=True)

        # Profesores asignados
        if act["profesores"]:
            chips = [_pill(p, Colors.TEXT_SECONDARY, con_icono=ft.Icons.PERSON_ROUNDED)
                     for p in act["profesores"]]
        else:
            chips = [ft.Text("Sin profesores asignados", color=Colors.TEXT_MUTED,
                             size=12, font_family=Fonts.BODY)]

        profesores = ft.Row([
            ft.Row(chips, spacing=6, wrap=True, expand=True),
            icon_action(ft.Icons.GROUP_ROUNDED, "Asignar profesores",
                        on_click=lambda e, a=act: self._asignar_profesores(a)),
        ], spacing=8)

        # Planes de la actividad
        if act["planes"]:
            filas_planes = []
            for i, p in enumerate(act["planes"]):
                filas_planes.append(self._fila_plan(act, p))
                if i < len(act["planes"]) - 1:
                    filas_planes.append(divider_row())
        else:
            filas_planes = [ft.Text("Todavía no tiene planes cargados.",
                                    color=Colors.TEXT_MUTED, size=14,
                                    font_family=Fonts.BODY)]

        return ft.Container(
            col={"xs": 12, "md": 6, "xl": 4},
            content=ft.Column([
                encabezado,
                ft.Container(height=6),
                ft.Text(act["descripcion"], color=Colors.TEXT_SECONDARY, size=14,
                        font_family=Fonts.BODY),
                ft.Container(height=10),
                datos,
                ft.Container(height=12),
                divider_row(),
                ft.Container(height=10),
                profesores,
                ft.Container(height=10),
                divider_row(),
                ft.Container(height=6),
                *filas_planes,
                ft.Container(height=10),
                secondary_button("Nuevo plan", ft.Icons.ADD_ROUNDED,
                                 on_click=lambda e, a=act: self._form_plan(a)),
            ], spacing=0),
            bgcolor=Colors.SURFACE_CARD,
            border_radius=Radius.MD,
            border=ft.Border.all(1, Colors.BORDER_IDLE),
            padding=20,
        )

    def _fila_plan(self, act: dict, plan: dict) -> ft.Container:
        etiqueta = (f"{plan['cantidad']} clases/mes" if plan["tipo"] == "POR_MES"
                    else f"{plan['cantidad']}x por semana")
        activo = plan["activo"]

        return ft.Container(
            content=ft.Row([
                ft.Column([
                    ft.Text(plan["nombre"], color=Colors.TEXT_MAIN, size=14,
                            font_family=Fonts.BODY),
                    ft.Text(f"{etiqueta} · {_moneda(plan['precio'])}",
                            color=Colors.TEXT_SECONDARY, size=12,
                            font_family=Fonts.BODY),
                ], spacing=1, tight=True, expand=True),
                _pill("Activa" if activo else "Inactiva",
                      Colors.STATUS_OK if activo else Colors.TEXT_MUTED),
                icon_action(
                    ft.Icons.BLOCK_ROUNDED if activo else ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED,
                    "Dar de baja" if activo else "Reactivar",
                    on_click=lambda e, a=act, p=plan: self._baja_plan(a, p),
                    color_hover=Colors.STATUS_DANGER if activo else Colors.STATUS_OK,
                ),
                icon_action(ft.Icons.EDIT_ROUNDED, "Editar",
                            on_click=lambda e, a=act, p=plan: self._form_plan(a, p)),
            ], spacing=6),
            padding=ft.Padding.symmetric(vertical=9),
        )

    # ── Alta / edición de actividad ──────────────────────────────────────────

    def _form_actividad(self, act: dict = None):
        """Diálogo de alta o edición de una actividad."""
        editando = act is not None

        nombre  = input_field("Nombre", "Ej: Pilates",
                              value=act["nombre"] if editando else "")
        desc    = input_field("Descripción", "Ej: Pilates con reformer",
                              value=act["descripcion"] if editando else "",
                              multiline=True)
        cupo    = input_field("Cupo por turno", "20",
                              value=str(act["cupo"]) if editando else "20")
        precio  = input_field("Precio clase suelta", "3500",
                              value=str(act["precio_suelta"]) if editando else "")
        horas   = input_field("Horas de anticipación para cancelar", "0",
                              value=str(act["horas_cancelacion"]) if editando else "0")

        def guardar():
            # TODO: POST /api/actividades   (alta)
            #       PUT  /api/actividades/{id}  (edición)
            show_snack(self.page,
                       "Actividad actualizada" if editando else "Actividad creada",
                       Colors.STATUS_OK)

        open_dialog(self.page, form_dialog(
            self.page,
            "Editar actividad" if editando else "Nueva actividad",
            [nombre, desc, cupo, precio, horas],
            on_save=guardar,
        ))

    def _baja_actividad(self, act: dict):
        activa = act["activa"]

        def confirmar():
            # TODO: DELETE /api/actividades/{id}      (baja lógica)
            #       POST   /api/actividades/{id}/reactivar
            show_snack(self.page,
                       f"\"{act['nombre']}\" fue {'dada de baja' if activa else 'reactivada'}",
                       Colors.STATUS_OK)

        # Reactivar no pide confirmación en la web: es reversible y de bajo
        # riesgo. Sólo la baja pregunta.
        if not activa:
            confirmar()
            return

        open_dialog(self.page, confirm_dialog(
            self.page,
            f"¿Dar de baja \"{act['nombre']}\"?",
            "Deja de aparecer en el catálogo para compras nuevas. Las "
            "inscripciones ya activas no se ven afectadas.",
            on_confirm=confirmar,
        ))

    # ── Alta / edición de plan ───────────────────────────────────────────────

    def _form_plan(self, act: dict, plan: dict = None):
        editando = plan is not None

        nombre = input_field("Nombre", "Ej: 8 clases al mes",
                             value=plan["nombre"] if editando else "")
        tipo   = select_field("Se factura por",
                              [("POR_MES", "Clases por mes"),
                               ("POR_SEMANA", "Veces por semana")],
                              value=plan["tipo"] if editando else "POR_MES")
        cant   = input_field("Cantidad", "8",
                             value=str(plan["cantidad"]) if editando else "")
        precio = input_field("Precio", "26000",
                             value=str(plan["precio"]) if editando else "")

        def guardar():
            # TODO: POST /api/actividades/{id}/planes   (alta)
            #       PUT  /api/planes/{id}               (edición)
            show_snack(self.page,
                       "Plan actualizado" if editando else "Plan creado",
                       Colors.STATUS_OK)

        open_dialog(self.page, form_dialog(
            self.page,
            "Editar plan" if editando else f"Nuevo plan de {act['nombre']}",
            [nombre, tipo, cant, precio],
            on_save=guardar,
        ))

    def _baja_plan(self, act: dict, plan: dict):
        activo = plan["activo"]

        def confirmar():
            # TODO: DELETE /api/planes/{id}  /  POST /api/planes/{id}/reactivar
            show_snack(self.page,
                       f"\"{plan['nombre']}\" fue {'dado de baja' if activo else 'reactivado'}",
                       Colors.STATUS_OK)

        if not activo:
            confirmar()
            return

        open_dialog(self.page, confirm_dialog(
            self.page,
            f"¿Dar de baja \"{plan['nombre']}\"?",
            "Deja de poder comprarse. Quienes ya lo tengan activo siguen "
            "usándolo hasta que venza.",
            on_confirm=confirmar,
        ))

    # ── Asignación de profesores ─────────────────────────────────────────────

    def _asignar_profesores(self, act: dict):
        """
        Lista de profesores con un toggle por fila. Profesor_Actividad es una
        relación N:M pura: no hay "editar", sólo existe o no existe — por eso
        cada fila se guarda al toque y no hay botón "Guardar" al pie.
        """
        # TODO: GET /api/profesores  +  GET /api/actividades/{id}/profesores
        profesores = app_state.get_profesores()
        asignados  = set(act["profesores"])

        filas = []
        for prof in profesores:
            esta = prof["nombre"] in asignados
            filas.append(self._fila_profesor(act, prof, esta))

        open_dialog(self.page, form_dialog(
            self.page,
            f"Profesores de {act['nombre']}",
            [ft.Text("Tocá un profesor para asignarlo o quitarlo de esta actividad.",
                     color=Colors.TEXT_SECONDARY, size=13, font_family=Fonts.BODY),
             *filas],
            on_save=None,
            texto_guardar="Listo",
        ))

    def _fila_profesor(self, act: dict, prof: dict, asignado: bool) -> ft.Container:
        estado = ft.Text("Asignado" if asignado else "Asignar",
                         color=Colors.PRIMARY_VOLT if asignado else Colors.TEXT_MUTED,
                         size=12, weight=ft.FontWeight.W_500, font_family=Fonts.BODY)

        fila = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.PERSON_ROUNDED,
                        color=Colors.PRIMARY_VOLT if asignado else Colors.TEXT_MUTED,
                        size=16),
                ft.Column([
                    ft.Text(prof["nombre"], color=Colors.TEXT_MAIN, size=14,
                            font_family=Fonts.BODY),
                    ft.Text(prof["especialidad"], color=Colors.TEXT_MUTED, size=12,
                            font_family=Fonts.BODY),
                ], spacing=1, tight=True, expand=True),
                estado,
            ], spacing=10),
            bgcolor=alpha(Colors.PRIMARY_VOLT, 0.08) if asignado else None,
            border=ft.Border.all(1, Colors.PRIMARY_VOLT if asignado else Colors.BORDER_IDLE),
            border_radius=Radius.SM,
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
        )

        def alternar(e):
            # TODO: POST/DELETE /api/actividades/{id}/profesores/{id_profesor}
            nuevo = estado.value == "Asignar"
            estado.value = "Asignado" if nuevo else "Asignar"
            estado.color = Colors.PRIMARY_VOLT if nuevo else Colors.TEXT_MUTED
            fila.bgcolor = alpha(Colors.PRIMARY_VOLT, 0.08) if nuevo else None
            fila.border = ft.Border.all(
                1, Colors.PRIMARY_VOLT if nuevo else Colors.BORDER_IDLE)
            fila.content.controls[0].color = (Colors.PRIMARY_VOLT if nuevo
                                              else Colors.TEXT_MUTED)
            fila.update()

        fila.on_click = alternar
        return fila


# =============================================================================
# HELPERS
# =============================================================================

def _pill(texto: str, color: str, con_icono: str = None) -> ft.Container:
    """Pastilla chiquita de estado o de etiqueta."""
    contenido = []
    if con_icono:
        contenido.append(ft.Icon(con_icono, color=color, size=11))
    contenido.append(ft.Text(texto, color=color, size=12,
                             weight=ft.FontWeight.W_500, font_family=Fonts.BODY))

    return ft.Container(
        content=ft.Row(contenido, spacing=4, tight=True),
        bgcolor=alpha(color, 0.10),
        border_radius=20,
        padding=ft.Padding.symmetric(horizontal=10, vertical=3),
    )


def _dato(texto: str) -> ft.Text:
    """Dato de configuración en gris chico."""
    return ft.Text(texto, color=Colors.TEXT_MUTED, size=12, font_family=Fonts.BODY)


def _moneda(valor) -> str:
    try:
        return f"$ {int(valor):,}".replace(",", ".")
    except (TypeError, ValueError):
        return str(valor)
