# =============================================================================
# views/nutricion.py — Gestión de planes nutricionales
# =============================================================================
# Gemela de views/nutricion/ de la PWA (NutricionView, PlanCard,
# PlanDetailModal, PlanFormModal):
#   - Resumen calórico: promedio, plan más bajo, más alto, total asignados.
#   - Tarjetas por plan con objetivo, calorías, estado y asignados.
#   - Detalle con las comidas REALES del plan, por día.
#   - Alta, edición, baja y reactivación — sólo con la acción `gestionDietas`.
#
# QUIÉN TOCA QUÉ: igual que la PWA. El Entrenador llega hasta acá con lectura
# (para ver qué dieta tiene un socio) pero sin ningún botón de gestión.

import flet as ft
from app.config import Colors, Fonts, Radius, Routes, alpha
from app.permisos import Accion
from app.state import app_state
from app.components.ui import (build_topbar, confirm_dialog, primary_button, input_field,
                                show_snack, open_dialog, close_dialog, status_badge)

# objetivo → (color de texto, fondo translúcido, ícono de tendencia).
# Mismos colores que CONFIG_OBJETIVO de PlanCard.tsx.
OBJETIVO_CONFIG = {
    "Masa muscular":    (Colors.STATUS_OK,     alpha(Colors.STATUS_OK, 0.10),     ft.Icons.TRENDING_UP_ROUNDED),
    "Bajar peso":       (Colors.STATUS_DANGER, alpha(Colors.STATUS_DANGER, 0.10), ft.Icons.TRENDING_DOWN_ROUNDED),
    "Mantenimiento":    (Colors.PRIMARY_VOLT,  alpha(Colors.PRIMARY_VOLT, 0.10),  ft.Icons.TRENDING_FLAT_ROUNDED),
    "Alto rendimiento": (Colors.STATUS_WARN,   alpha(Colors.STATUS_WARN, 0.10),   ft.Icons.BOLT_ROUNDED),
}
CONFIG_POR_DEFECTO = (Colors.TEXT_MUTED, alpha(Colors.TEXT_MUTED, 0.10), ft.Icons.RESTAURANT_MENU_ROUNDED)


class NutricionView:
    def __init__(self, page: ft.Page, router):
        self.page   = page
        self.router = router
        # Sólo el Nutricionista (y el Dueño) gestionan dietas. Ver NutricionView.tsx.
        self.puede_gestionar = app_state.puede(Accion.GESTION_DIETAS)

    def build(self) -> ft.Column:
        planes = app_state.get_planes_nutricion()

        topbar = build_topbar(
            "Nutrición",
            f"{len(planes)} planes nutricionales",
            actions=[
                primary_button("Nuevo Plan", ft.Icons.ADD_ROUNDED,
                               on_click=lambda e: self._open_form()),
            ] if self.puede_gestionar else [],
        )

        # LOS GUARDAS DE LISTA VACÍA NO SON PARANOIA: sin planes cargados
        # `sum(cals)//len(cals)` tiraba ZeroDivisionError y `min`/`max` un
        # ValueError, y la pantalla no abría para NINGÚN rol (lo encontró
        # pruebas_vistas.py). Se muestra 0, igual que la PWA.
        cals = [p["calorias"] for p in planes if p["calorias"]]
        promedio = sum(cals) // len(cals) if cals else 0
        minimo = min(cals) if cals else 0
        maximo = max(cals) if cals else 0
        summary = ft.Container(
            content=ft.Row([
                _cal_stat("Promedio Cal.",  f"{promedio} kcal",
                          ft.Icons.LOCAL_FIRE_DEPARTMENT_ROUNDED, Colors.ACCENT_CORAL),
                _cal_stat("Plan más bajo",  f"{minimo} kcal",
                          ft.Icons.TRENDING_DOWN_ROUNDED, Colors.STATUS_OK),
                _cal_stat("Plan más alto",  f"{maximo} kcal",
                          ft.Icons.TRENDING_UP_ROUNDED, Colors.STATUS_WARN),
                _cal_stat("Total asignados", f"{sum(p['asignados'] for p in planes)}",
                          ft.Icons.GROUP_ROUNDED, Colors.PRIMARY_VOLT),
            ], spacing=16),
            padding=ft.Padding.only(bottom=20),
        )

        if planes:
            cards = ft.ResponsiveRow([self._plan_card(p) for p in planes],
                                     spacing=16, run_spacing=16)
        else:
            cards = ft.Text("Todavía no hay planes nutricionales cargados.",
                            color=Colors.TEXT_MUTED, size=13)

        # Topbar fijo arriba, sólo el contenido scrollea (ver dashboard.py).
        return ft.Column([
            topbar,
            ft.Container(
                content=ft.Column([summary, cards], spacing=0,
                                  scroll=ft.ScrollMode.AUTO, expand=True),
                padding=ft.Padding.all(24),
                expand=True,
            ),
        ], spacing=0, expand=True)

    # ── Tarjeta ───────────────────────────────────────────────────────────────

    def _plan_card(self, p: dict) -> ft.Container:
        color, bg, icon = OBJETIVO_CONFIG.get(p["objetivo"], CONFIG_POR_DEFECTO)

        # Un solo botón que cambia según el estado (PlanCard.tsx). Sin la
        # acción no se dibuja ninguno.
        estado = []
        if not p["activo"]:
            estado.append(status_badge("Inactiva"))
        if self.puede_gestionar:
            estado.append(ft.IconButton(
                ft.Icons.RESTART_ALT_ROUNDED if not p["activo"] else ft.Icons.BLOCK_ROUNDED,
                icon_color=Colors.TEXT_MUTED, icon_size=16,
                tooltip="Reactivar" if not p["activo"] else "Dar de baja",
                on_click=lambda e, x=p: self._cambiar_estado(x),
            ))

        return ft.Container(
            col={"xs": 12, "sm": 6},
            content=ft.Column([
                ft.Row([
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(icon, color=color, size=14),
                            ft.Text(p["objetivo"], color=color, size=11,
                                    weight=ft.FontWeight.W_600),
                        ], spacing=6, tight=True),
                        bgcolor=bg, border_radius=20,
                        padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                    ),
                    ft.Container(expand=True),
                    *estado,
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Container(height=12),
                ft.Text(p["nombre"], color=Colors.TEXT_PRIMARY, size=17,
                        weight=ft.FontWeight.BOLD),
                ft.Container(height=6),
                *([ft.Row([
                    ft.Text(str(p["calorias"]), color=Colors.TEXT_PRIMARY, size=28,
                            weight=ft.FontWeight.BOLD, font_family=Fonts.MONO),
                    ft.Text("kcal/día", color=Colors.TEXT_MUTED, size=14),
                ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.END)]
                  if p["calorias"] else []),
                ft.Container(height=12),
                ft.Divider(color=Colors.BORDER, height=1),
                ft.Container(height=10),
                ft.Row([
                    ft.Text(f"{p['asignados']} socios asignados",
                            color=Colors.TEXT_SECONDARY, size=12),
                    ft.Container(expand=True),
                    ft.TextButton("Ver plan", style=ft.ButtonStyle(color=Colors.ACCENT),
                                  on_click=lambda e, x=p: self._open_detail(x)),
                ]),
            ], spacing=0),
            bgcolor=Colors.BG_CARD,
            border_radius=14,
            border=ft.Border.all(1, Colors.BORDER),
            padding=20,
        )

    # ── Detalle ───────────────────────────────────────────────────────────────

    def _open_detail(self, p: dict):
        """
        El plan con sus comidas REALES por día. La versión anterior mostraba
        un 30/50/20 de macros fijo que no salía de ningún dato (Dieta no tiene
        macros); la PWA ya lo había reemplazado por esto.
        """
        color, bg, icon = OBJETIVO_CONFIG.get(p["objetivo"], CONFIG_POR_DEFECTO)
        comidas = app_state.get_comidas_dieta(p["id"])

        filas = [
            ft.Row([
                ft.Container(
                    content=ft.Row([ft.Icon(icon, color=color, size=14),
                                    ft.Text(p["objetivo"], color=color, size=12,
                                            weight=ft.FontWeight.W_600)],
                                   spacing=6, tight=True),
                    bgcolor=bg, border_radius=20,
                    padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                ),
                status_badge("Activa" if p["activo"] else "Inactiva"),
            ], spacing=8),
        ]
        if p["calorias"]:
            filas.append(ft.Row([
                ft.Text(str(p["calorias"]), color=Colors.TEXT_PRIMARY, size=34,
                        weight=ft.FontWeight.BOLD, font_family=Fonts.MONO),
                ft.Text("kcal/día", color=Colors.TEXT_MUTED, size=14),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.END))
        if p["descripcion"]:
            filas.append(ft.Text(p["descripcion"], color=Colors.TEXT_SECONDARY, size=13))
        filas += [
            ft.Text(f"Nutricionista: {p['nutricionista']}   ·   Asignados: {p['asignados']} socios",
                    color=Colors.TEXT_SECONDARY, size=13),
            ft.Divider(height=1, color=Colors.BORDER),
            ft.Text("Plan alimentario", color=Colors.TEXT_PRIMARY, size=14,
                    weight=ft.FontWeight.BOLD),
        ]

        if comidas is None:
            filas.append(ft.Text("No se pudieron cargar las comidas.",
                                 color=Colors.STATUS_DANGER, size=13))
        elif not comidas:
            filas.append(ft.Text("Todavía no hay comidas cargadas para este plan.",
                                 color=Colors.TEXT_MUTED, size=13))
        else:
            dias: list[int] = []
            for c in comidas:
                dia = c["dia"] or 0
                if dia not in dias:
                    dias.append(dia)
            for dia in dias:
                filas.append(ft.Text("SIN DÍA ASIGNADO" if dia == 0 else f"DÍA {dia}",
                                     color=Colors.TEXT_MUTED, size=11,
                                     weight=ft.FontWeight.W_600))
                for c in (x for x in comidas if (x["dia"] or 0) == dia):
                    filas.append(ft.Row([
                        ft.Column([
                            *([ft.Text(c["momento"], color=Colors.TEXT_MUTED, size=11)]
                              if c["momento"] else []),
                            ft.Text(c["descripcion"] or c["nombre"],
                                    color=Colors.TEXT_PRIMARY, size=13),
                        ], spacing=0, tight=True, expand=True),
                        *([ft.Text(f"{c['calorias']} kcal", color=Colors.TEXT_SECONDARY,
                                   size=12, font_family=Fonts.MONO)]
                          if c["calorias"] is not None else []),
                    ]))

        acciones = [ft.TextButton("Cerrar", style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                                  on_click=lambda e: close_dialog(self.page, dlg))]
        if self.puede_gestionar:
            acciones.append(ft.TextButton(
                "Editar", style=ft.ButtonStyle(color=Colors.ACCENT),
                on_click=lambda e: (close_dialog(self.page, dlg), self._open_form(p))))

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(p["nombre"], color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=460,
                content=ft.Column(filas, spacing=10, tight=True, scroll=ft.ScrollMode.AUTO),
            ),
            actions=acciones,
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(self.page, dlg)

    # ── Alta / edición ────────────────────────────────────────────────────────

    def _open_form(self, plan: dict = None):
        """
        Alta o edición de un plan (PlanFormModal.tsx).

        El selector de nutricionista responde a lo mismo que el de entrenador
        en rutinas: `Dieta.id_nutricionista` es NOT NULL y el Dueño no es
        nutricionista, así que tiene que elegir a quién queda atribuida.
        """
        es_edicion = plan is not None
        nutricionistas = app_state.get_nutricionistas()

        nombre_tf = input_field("Nombre del plan", "Ej: Volumen Limpio",
                                icon=ft.Icons.RESTAURANT_MENU_ROUNDED,
                                value=plan["nombre"] if plan else "")
        objetivo_dd = ft.Dropdown(
            label="Objetivo",
            options=[ft.dropdown.Option(k) for k in OBJETIVO_CONFIG],
            value=plan["objetivo"] if plan and plan["objetivo"] in OBJETIVO_CONFIG else "Mantenimiento",
            color=Colors.TEXT_PRIMARY, bgcolor=Colors.BG_INPUT,
            border_color=Colors.BORDER, focused_border_color=Colors.ACCENT,
            border_radius=Radius.MD,
        )
        calorias_tf = input_field("Calorías diarias (kcal)", "Ej: 2400",
                                  icon=ft.Icons.LOCAL_FIRE_DEPARTMENT_ROUNDED,
                                  value=str(plan["calorias"]) if plan and plan["calorias"] else "")

        opciones = [ft.dropdown.Option(key=str(x["id"]), text=x["nombre"]) for x in nutricionistas]
        if plan and plan["id_nutricionista"] is not None \
                and not any(x["id"] == plan["id_nutricionista"] for x in nutricionistas):
            # Ya no está activo: se ofrece igual para no reemplazarlo en silencio.
            opciones.append(ft.dropdown.Option(key=str(plan["id_nutricionista"]),
                                               text=f"{plan['nutricionista']} (inactivo)"))
        nutri_dd = ft.Dropdown(
            label="Nutricionista a cargo", options=opciones,
            value=(str(plan["id_nutricionista"]) if plan and plan["id_nutricionista"] is not None
                   else (str(nutricionistas[0]["id"]) if nutricionistas else None)),
            color=Colors.TEXT_PRIMARY, bgcolor=Colors.BG_INPUT,
            border_color=Colors.BORDER, focused_border_color=Colors.ACCENT,
            border_radius=Radius.MD,
        )
        # Va a `descripcion`, la única columna de texto libre que tiene Dieta.
        notas_tf = input_field("Notas", "Restricciones, alimentos preferidos...",
                               multiline=True, value=plan["descripcion"] if plan else "")

        def guardar(e=None):
            nombre = (nombre_tf.value or "").strip()
            if not nombre:
                show_snack(self.page, "El plan necesita un nombre.", Colors.STATUS_DANGER)
                return
            crudo = (calorias_tf.value or "").strip()
            if not crudo.isdigit():
                show_snack(self.page, "Calorías diarias: un número entero.", Colors.STATUS_DANGER)
                return
            datos = {
                "nombre": nombre,
                "objetivo": objetivo_dd.value,
                "calorias_diarias": int(crudo),
                "descripcion": (notas_tf.value or "").strip() or None,
                "id_nutricionista": int(nutri_dd.value) if nutri_dd.value else None,
            }
            if es_edicion:
                resultado = app_state.editar_dieta(plan["id"], datos)
            else:
                resultado = app_state.crear_dieta({**datos, "comidas": []})
            if not resultado["ok"]:
                show_snack(self.page, resultado["mensaje"], Colors.STATUS_DANGER)
                return
            close_dialog(self.page, dlg)
            show_snack(self.page, resultado["mensaje"], Colors.SUCCESS)
            self.router.navigate(Routes.NUTRICION)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Editar Plan" if es_edicion else "Nuevo Plan Nutricional",
                          color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=440,
                content=ft.Column([nombre_tf, objetivo_dd, calorias_tf, nutri_dd, notas_tf],
                                  spacing=12, tight=True),
            ),
            actions=[
                ft.TextButton("Cancelar", style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                              on_click=lambda e: close_dialog(self.page, dlg)),
                ft.TextButton("Guardar" if es_edicion else "Crear Plan",
                              style=ft.ButtonStyle(color=Colors.ACCENT), on_click=guardar),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(self.page, dlg)

    # ── Baja / reactivación ───────────────────────────────────────────────────

    def _cambiar_estado(self, p: dict):
        """Baja con confirmación; reactivar sin, porque es reversible."""
        if not p["activo"]:
            self._aplicar(app_state.reactivar_dieta(p["id"]))
            return
        dlg = confirm_dialog(
            self.page, f"¿Dar de baja \"{p['nombre']}\"?",
            "El plan deja de figurar como activo. Los socios que lo siguen lo terminan.",
            on_confirm=lambda: self._aplicar(app_state.baja_dieta(p["id"])),
            texto_confirmar="Dar de baja",
        )
        open_dialog(self.page, dlg)

    def _aplicar(self, resultado: dict):
        if not resultado["ok"]:
            show_snack(self.page, resultado["mensaje"], Colors.STATUS_DANGER)
            return
        show_snack(self.page, resultado["mensaje"], Colors.SUCCESS)
        self.router.navigate(Routes.NUTRICION)


def _cal_stat(label: str, value: str, icon: str, color: str) -> ft.Container:
    """Tarjeta de estadística del resumen (el StatCard de la PWA)."""
    return ft.Container(
        content=ft.Column([
            ft.Container(
                content=ft.Icon(icon, color=color, size=18),
                width=36, height=36, border_radius=10,
                bgcolor=alpha(color, 0.12), alignment=ft.Alignment.CENTER,
            ),
            ft.Text(value, color=Colors.TEXT_PRIMARY, size=16,
                    weight=ft.FontWeight.BOLD),
            ft.Text(label, color=Colors.TEXT_SECONDARY, size=12),
        ], spacing=4),
        bgcolor=Colors.BG_CARD,
        border_radius=12,
        border=ft.Border.all(1, Colors.BORDER),
        padding=16,
        expand=True,
    )
