# =============================================================================
# views/nutricion.py — Gestión de planes nutricionales
# =============================================================================
# Gemela de views/nutricion/ de la PWA (NutricionView, PlanCard,
# PlanDetailModal, PlanFormModal, PlatoFormModal) y de AsignarASocioModal:
#   - Resumen calórico: promedio, plan más bajo, más alto, total asignados.
#   - Tarjetas por plan con objetivo, calorías, estado, nutricionista.
#   - Detalle con las comidas reales del plan, por día.
#   - Alta y edición CON el plan alimentario: comidas por día (1 a 7), cada una
#     con momento y un plato del catálogo o texto libre.
#   - Asignar el plan a un socio, baja y reactivación, y alta de platos.
#
# QUIÉN TOCA QUÉ: hace falta la acción `gestionDietas` y además que el plan
# sea editable para esta sesión (`puede_editar`, lo decide el backend): un
# Nutricionista ve los planes de sus colegas pero no los toca. El Entrenador
# llega con lectura y sin ningún botón.

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

# Los mismos momentos que ordena el backend (ORDEN_MOMENTOS en nutricion.py).
MOMENTOS = ["Desayuno", "Media mañana", "Almuerzo", "Merienda", "Cena", "Colación"]
DIAS = list(range(1, 8))
MAX_SOCIOS_LISTA = 50


class NutricionView:
    def __init__(self, page: ft.Page, router):
        self.page   = page
        self.router = router
        self.puede_gestionar = app_state.puede(Accion.GESTION_DIETAS)

    def _gestionable(self, p: dict) -> bool:
        return self.puede_gestionar and p.get("puede_editar", True)

    def build(self) -> ft.Column:
        planes = app_state.get_planes_nutricion()

        topbar = build_topbar(
            "Nutrición",
            f"{len(planes)} planes nutricionales",
            actions=[
                primary_button("Plato", ft.Icons.ADD_ROUNDED,
                               on_click=lambda e: self._open_plato()),
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

        estado = []
        if not p["activo"]:
            estado.append(status_badge("Inactiva"))
        if self._gestionable(p):
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
                    ft.Column([
                        ft.Text(f"{p['asignados']} socios asignados",
                                color=Colors.TEXT_SECONDARY, size=12),
                        ft.Text(p["nutricionista"], color=Colors.TEXT_MUTED, size=11),
                    ], spacing=0, tight=True),
                    ft.Container(expand=True),
                    # "Asignar" también acá, no sólo dentro del detalle.
                    # Asignar es la acción frecuente —ya se sabe qué plan es— y
                    # obligaba a abrir el plan, buscar el botón y volver a
                    # salir. Gemelo de PlanCard.tsx.
                    *([ft.TextButton("Asignar",
                                     style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                                     on_click=lambda e, x=p: self._open_asignar(x))]
                      if self._gestionable(p) else []),
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
        """El plan con sus comidas REALES por día (no un reparto de macros inventado)."""
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
                if (c["dia"] or 0) not in dias:
                    dias.append(c["dia"] or 0)
            for dia in dias:
                filas.append(ft.Text("SIN DÍA ASIGNADO" if dia == 0 else f"DÍA {dia}",
                                     color=Colors.TEXT_MUTED, size=11,
                                     weight=ft.FontWeight.W_600))
                for c in (x for x in comidas if (x["dia"] or 0) == dia):
                    filas.append(ft.Row([
                        ft.Column([
                            *([ft.Text(c["momento"], color=Colors.TEXT_MUTED, size=11)]
                              if c["momento"] else []),
                            ft.Text(c["nombre"], color=Colors.TEXT_PRIMARY, size=13),
                            *([ft.Text(c["descripcion"], color=Colors.TEXT_MUTED, size=11)]
                              if c["descripcion"] else []),
                        ], spacing=0, tight=True, expand=True),
                        *([ft.Text(f"{c['calorias']} kcal", color=Colors.TEXT_SECONDARY,
                                   size=12, font_family=Fonts.MONO)]
                          if c["calorias"] is not None else []),
                    ]))

        acciones = [ft.TextButton("Cerrar", style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                                  on_click=lambda e: close_dialog(self.page, dlg))]
        if self._gestionable(p):
            acciones += [
                ft.TextButton("Asignar", style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                              on_click=lambda e: (close_dialog(self.page, dlg),
                                                  self._open_asignar(p))),
                ft.TextButton("Editar", style=ft.ButtonStyle(color=Colors.ACCENT),
                              on_click=lambda e: (close_dialog(self.page, dlg),
                                                  self._open_form(p))),
            ]

        dlg = ft.AlertDialog(
            # modal=False para que cierre tocando afuera, como su gemelo
            # PlanDetailModal.tsx. Los cuatro diálogos de esta pantalla lo hacen:
            # en la PWA los cuatro cierran así, y que en escritorio no cerraran
            # obligaba a buscar el botón para salir de algo que sólo se vino a mirar.
            #
            # NO se toca el modal de confirm_dialog/form_dialog de components/ui.py:
            # esos son compartidos por TODAS las vistas y varios confirman acciones
            # destructivas, donde cerrar por un click al costado sí es un problema.
            modal=False,
            title=ft.Text(p["nombre"], color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=460, height=460,
                content=ft.Column(filas, spacing=10, scroll=ft.ScrollMode.AUTO),
            ),
            actions=acciones,
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(self.page, dlg)

    # ── Alta / edición con el plan alimentario ────────────────────────────────

    def _open_form(self, plan: dict = None):
        """
        Alta o edición de un plan CON sus comidas por día (PlanFormModal.tsx).

        Cada comida lleva un momento y un plato del catálogo o, si el catálogo
        no lo tiene, texto libre. Al guardar se manda el plan entero: en
        edición el backend reemplaza las comidas anteriores.

        El selector de nutricionista existe porque `Dieta.id_nutricionista` es
        NOT NULL y el Dueño no es nutricionista. A un Nutricionista el backend
        le devuelve sólo a sí mismo en esa lista.
        """
        es_edicion = plan is not None
        nutricionistas = app_state.get_nutricionistas()
        platos = app_state.get_platos()
        plato_por_id = {str(x["id"]): x for x in platos}

        comidas_actuales = app_state.get_comidas_dieta(plan["id"]) if es_edicion else []
        if es_edicion and comidas_actuales is None:
            show_snack(self.page, "No se pudieron cargar las comidas del plan.", Colors.STATUS_DANGER)
            return
        items = [
            {"dia": c["dia"] or 1, "momento": c["momento"] or MOMENTOS[0],
             "plato": str(c["id_catalogo_comida"]) if c["id_catalogo_comida"] else "",
             "texto": "" if c["id_catalogo_comida"] else c["nombre"]}
            for c in (comidas_actuales or [])
        ]
        estado = {"dia": 1}

        nombre_tf = input_field("Nombre del plan", "Ej: Volumen Limpio",
                                icon=ft.Icons.RESTAURANT_MENU_ROUNDED,
                                value=plan["nombre"] if plan else "")
        objetivo_dd = _dropdown(
            "Objetivo", [ft.dropdown.Option(k) for k in OBJETIVO_CONFIG],
            plan["objetivo"] if plan and plan["objetivo"] in OBJETIVO_CONFIG else "Mantenimiento",
            width=220,
        )
        calorias_tf = input_field("Calorías diarias", "Ej: 2400", width=180,
                                  value=str(plan["calorias"]) if plan and plan["calorias"] else "2000")

        opciones_nutri = [ft.dropdown.Option(key=str(x["id"]), text=x["nombre"]) for x in nutricionistas]
        if plan and plan["id_nutricionista"] is not None \
                and not any(x["id"] == plan["id_nutricionista"] for x in nutricionistas):
            # Ya no está activo: se ofrece igual para no reemplazarlo en silencio.
            opciones_nutri.append(ft.dropdown.Option(key=str(plan["id_nutricionista"]),
                                                     text=f"{plan['nutricionista']} (inactivo)"))
        nutri_dd = _dropdown(
            "Nutricionista a cargo", opciones_nutri,
            (str(plan["id_nutricionista"]) if plan and plan["id_nutricionista"] is not None
             else (str(nutricionistas[0]["id"]) if nutricionistas else None)),
        )
        notas_tf = input_field("Notas", "Restricciones, alimentos preferidos...",
                               multiline=True, value=plan["descripcion"] if plan else "")

        chips = ft.Row(spacing=6, wrap=True)
        resumen_dia = ft.Text("", color=Colors.TEXT_MUTED, size=12)
        lista = ft.Column(spacing=8)

        opciones_plato = [ft.dropdown.Option(key="", text="Texto libre…")] + [
            ft.dropdown.Option(key=str(x["id"]),
                               text=f"{x['nombre']} ({x['calorias']} kcal)" if x["calorias"] is not None
                               else x["nombre"])
            for x in platos
        ]

        def render():
            dia = estado["dia"]
            chips.controls = [_chip_dia(d, d == dia, sum(1 for it in items if it["dia"] == d),
                                        lambda e, d=d: elegir_dia(d)) for d in DIAS]
            kcal = sum((plato_por_id.get(it["plato"]) or {}).get("calorias") or 0
                       for it in items if it["dia"] == dia and it["plato"])
            resumen_dia.value = (f"Día {dia}: {kcal} kcal con platos del catálogo" if kcal else "")
            del_dia = [it for it in items if it["dia"] == dia]
            lista.controls = [fila(it) for it in del_dia] or [
                ft.Text(f"El Día {dia} todavía no tiene comidas.", color=Colors.TEXT_MUTED, size=12)
            ]
            self.page.update()

        def elegir_dia(d: int):
            estado["dia"] = d
            render()

        def agregar(e=None):
            usados = sum(1 for it in items if it["dia"] == estado["dia"])
            items.append({"dia": estado["dia"], "momento": MOMENTOS[min(usados, len(MOMENTOS) - 1)],
                          "plato": "", "texto": ""})
            render()

        def quitar(it: dict):
            items.remove(it)
            render()

        def copiar_a_todos(e=None):
            base = [dict(it) for it in items if it["dia"] == estado["dia"]]
            items[:] = [it for it in items if it["dia"] == estado["dia"]] + [
                {**b, "dia": d} for d in DIAS if d != estado["dia"] for b in base
            ]
            show_snack(self.page, f"Día {estado['dia']} copiado a los demás días", Colors.SUCCESS)
            render()

        def fila(it: dict) -> ft.Container:
            def elegir_momento(e, it=it):
                it["momento"] = e.control.value

            def elegir_plato(e, it=it):
                it["plato"] = e.control.value or ""
                render()  # muestra u oculta el campo de texto libre

            def escribir(e, it=it):
                # Sin re-render: se guarda y el foco no se pierde.
                it["texto"] = e.control.value or ""

            momento_dd = ft.Dropdown(
                label="Momento", options=[ft.dropdown.Option(m) for m in MOMENTOS],
                value=it["momento"], width=170, dense=True,
                color=Colors.TEXT_PRIMARY, bgcolor=Colors.BG_CARD,
                border_color=Colors.BORDER, focused_border_color=Colors.ACCENT,
                border_radius=Radius.SM, on_select=elegir_momento,
            )
            plato_dd = ft.Dropdown(
                label="Plato", options=opciones_plato, value=it["plato"], expand=True, dense=True,
                color=Colors.TEXT_PRIMARY, bgcolor=Colors.BG_CARD,
                border_color=Colors.BORDER, focused_border_color=Colors.ACCENT,
                border_radius=Radius.SM, on_select=elegir_plato,
            )
            controles = [
                ft.Row([
                    momento_dd,
                    plato_dd,
                    ft.IconButton(ft.Icons.DELETE_OUTLINE_ROUNDED, icon_size=16,
                                  icon_color=Colors.STATUS_DANGER, tooltip="Quitar",
                                  on_click=lambda e, it=it: quitar(it)),
                ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ]
            if not it["plato"]:
                controles.append(ft.TextField(
                    value=it["texto"], hint_text="Ej: 2 huevos revueltos + tostada integral",
                    max_length=200, dense=True, text_size=13, color=Colors.TEXT_MAIN,
                    hint_style=ft.TextStyle(color=Colors.TEXT_MUTED),
                    bgcolor=Colors.BG_CARD, border_color=Colors.BORDER,
                    focused_border_color=Colors.ACCENT, border_radius=Radius.SM,
                    on_change=escribir,
                ))
            return ft.Container(
                content=ft.Column(controles, spacing=6, tight=True),
                bgcolor=Colors.BG_INPUT, border=ft.Border.all(1, Colors.BORDER),
                border_radius=Radius.MD, padding=ft.Padding.all(10),
            )

        def guardar(e=None):
            nombre = (nombre_tf.value or "").strip()
            if not nombre:
                show_snack(self.page, "El plan necesita un nombre.", Colors.STATUS_DANGER)
                return
            crudo = (calorias_tf.value or "").strip()
            if not crudo.isdigit():
                show_snack(self.page, "Calorías diarias: un número entero.", Colors.STATUS_DANGER)
                return
            incompleta = next((it for it in items if not it["plato"] and not it["texto"].strip()), None)
            if incompleta:
                estado["dia"] = incompleta["dia"]
                render()
                show_snack(self.page, f"Día {incompleta['dia']}: una comida ({incompleta['momento']}) "
                                      "no tiene plato ni descripción.", Colors.STATUS_DANGER)
                return

            datos = {
                "nombre": nombre,
                "objetivo": objetivo_dd.value,
                "calorias_diarias": int(crudo),
                "descripcion": (notas_tf.value or "").strip() or None,
                "id_nutricionista": int(nutri_dd.value) if nutri_dd.value else None,
                "comidas": [
                    {"dia": it["dia"], "momento": it["momento"],
                     "id_catalogo_comida": int(it["plato"]) if it["plato"] else None,
                     "descripcion": None if it["plato"] else it["texto"].strip()[:200]}
                    for it in items
                ],
            }
            resultado = (app_state.editar_dieta(plan["id"], datos) if es_edicion
                         else app_state.crear_dieta(datos))
            if not resultado["ok"]:
                show_snack(self.page, resultado["mensaje"], Colors.STATUS_DANGER)
                return
            close_dialog(self.page, dlg)
            show_snack(self.page, resultado["mensaje"], Colors.SUCCESS)
            self.router.navigate(Routes.NUTRICION)

        dlg = ft.AlertDialog(
            # Cierra tocando afuera (ver el detalle).
            modal=False,
            title=ft.Text("Editar Plan" if es_edicion else "Nuevo Plan Nutricional",
                          color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=640, height=600,
                content=ft.Column([
                    nombre_tf,
                    ft.Row([objetivo_dd, calorias_tf], spacing=12),
                    nutri_dd,
                    notas_tf,
                    ft.Divider(height=1, color=Colors.BORDER),
                    ft.Text("Plan alimentario", color=Colors.TEXT_PRIMARY, size=15,
                            weight=ft.FontWeight.BOLD),
                    chips,
                    resumen_dia,
                    lista,
                    ft.Row([
                        ft.TextButton("Agregar comida", icon=ft.Icons.ADD_ROUNDED,
                                      style=ft.ButtonStyle(color=Colors.ACCENT), on_click=agregar),
                        ft.TextButton("Copiar este día a todos", icon=ft.Icons.COPY_ROUNDED,
                                      style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                                      on_click=copiar_a_todos),
                    ], spacing=8),
                    *([ft.Text("El catálogo de platos está vacío: escribí cada comida como "
                               "texto libre o cargá platos con \"Plato\".",
                               color=Colors.TEXT_MUTED, size=11)] if not platos else []),
                ], spacing=12, scroll=ft.ScrollMode.AUTO),
            ),
            actions=[
                ft.TextButton("Cancelar", style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                              on_click=lambda e: close_dialog(self.page, dlg)),
                ft.TextButton("Guardar" if es_edicion else "Crear Plan",
                              style=ft.ButtonStyle(color=Colors.ACCENT), on_click=guardar),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        render()
        open_dialog(self.page, dlg)

    # ── Asignar a un socio ────────────────────────────────────────────────────

    def _open_asignar(self, p: dict):
        """
        Buscar un socio activo y asignarle el plan. Si ya seguía otro, el
        backend lo FINALIZA (queda en su historial). Gemelo de _open_asignar en
        rutinas.py y de AsignarASocioModal.tsx.
        """
        socios = [s for s in app_state.get_socios() if s.get("activo", True)]
        busqueda = ft.TextField(
            hint_text="Buscar por nombre o DNI…", prefix_icon=ft.Icons.SEARCH_ROUNDED,
            color=Colors.TEXT_MAIN, text_size=13, dense=True,
            hint_style=ft.TextStyle(color=Colors.TEXT_MUTED),
            bgcolor=Colors.BG_INPUT, border_color=Colors.BORDER,
            focused_border_color=Colors.ACCENT, border_radius=Radius.MD,
        )
        lista = ft.Column(spacing=2, height=320, scroll=ft.ScrollMode.AUTO)

        def asignar(s: dict):
            resultado = app_state.asignar_dieta(p["id"], s["id"])
            if not resultado["ok"]:
                show_snack(self.page, resultado["mensaje"], Colors.STATUS_DANGER)
                return
            close_dialog(self.page, dlg)
            show_snack(self.page, f"\"{p['nombre']}\" asignado a {s['nombre']}.", Colors.SUCCESS)
            self.router.navigate(Routes.NUTRICION)

        def render():
            q = (busqueda.value or "").strip().lower()
            filtrados = [s for s in socios
                         if not q or q in s["nombre"].lower() or q in str(s.get("dni", ""))]
            lista.controls = [
                ft.Row([
                    ft.Column([
                        ft.Text(s["nombre"], color=Colors.TEXT_PRIMARY, size=13),
                        ft.Text(f"DNI {s.get('dni') or '—'}", color=Colors.TEXT_MUTED, size=11),
                    ], spacing=0, tight=True, expand=True),
                    ft.TextButton("Asignar", style=ft.ButtonStyle(color=Colors.ACCENT),
                                  on_click=lambda e, s=s: asignar(s)),
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER)
                for s in filtrados[:MAX_SOCIOS_LISTA]
            ] or [ft.Text("Ningún socio activo coincide.", color=Colors.TEXT_MUTED, size=12)]
            self.page.update()

        busqueda.on_change = lambda e: render()
        dlg = ft.AlertDialog(
            # Cierra tocando afuera (ver el detalle).
            modal=False,
            title=ft.Text(f"Asignar \"{p['nombre']}\"", color=Colors.TEXT_PRIMARY,
                          weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=440,
                content=ft.Column([
                    busqueda,
                    ft.Text("Si el socio ya sigue otro plan, se lo finaliza y queda en su historial.",
                            color=Colors.TEXT_MUTED, size=11),
                    lista,
                ], spacing=8, tight=True),
            ),
            actions=[ft.TextButton("Cerrar", style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                                   on_click=lambda e: close_dialog(self.page, dlg))],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        render()
        open_dialog(self.page, dlg)

    # ── Alta de plato ─────────────────────────────────────────────────────────

    def _open_plato(self):
        """Alta de un plato en el catálogo (PlatoFormModal.tsx)."""
        nombre_tf = input_field("Nombre", "Ej: Pollo con arroz integral",
                                icon=ft.Icons.RESTAURANT_ROUNDED)
        calorias_tf = input_field("Calorías (kcal)", "Opcional")
        desc_tf = input_field("Descripción", "Ej: 150 g de pechuga + ensalada", multiline=True)

        def guardar(e=None):
            nombre = (nombre_tf.value or "").strip()
            if not nombre:
                show_snack(self.page, "El plato necesita un nombre.", Colors.STATUS_DANGER)
                return
            crudo = (calorias_tf.value or "").strip()
            if crudo and not crudo.isdigit():
                show_snack(self.page, "Calorías: un número entero.", Colors.STATUS_DANGER)
                return
            resultado = app_state.crear_plato({
                "nombre": nombre, "calorias": int(crudo) if crudo else None,
                "descripcion": (desc_tf.value or "").strip() or None,
            })
            if not resultado["ok"]:
                show_snack(self.page, resultado["mensaje"], Colors.STATUS_DANGER)
                return
            close_dialog(self.page, dlg)
            show_snack(self.page, resultado["mensaje"], Colors.SUCCESS)

        dlg = ft.AlertDialog(
            # Cierra tocando afuera (ver el detalle).
            modal=False,
            title=ft.Text("Nuevo plato", color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(width=420, content=ft.Column(
                [nombre_tf, calorias_tf, desc_tf], spacing=12, tight=True)),
            actions=[
                ft.TextButton("Cancelar", style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                              on_click=lambda e: close_dialog(self.page, dlg)),
                ft.TextButton("Agregar plato", style=ft.ButtonStyle(color=Colors.ACCENT),
                              on_click=guardar),
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


def _dropdown(label: str, options: list, value, width=None) -> ft.Dropdown:
    return ft.Dropdown(
        label=label, options=options, value=value, width=width,
        color=Colors.TEXT_PRIMARY, bgcolor=Colors.BG_INPUT,
        border_color=Colors.BORDER, focused_border_color=Colors.ACCENT,
        border_radius=Radius.MD,
    )


def _chip_dia(dia: int, activo: bool, cantidad: int, on_click) -> ft.Container:
    texto = f"Día {dia}" + (f" ({cantidad})" if cantidad else "")
    return ft.Container(
        content=ft.Text(texto, size=12, weight=ft.FontWeight.W_500,
                        color=Colors.SURFACE_BASE if activo else Colors.TEXT_SECONDARY),
        bgcolor=Colors.PRIMARY_VOLT if activo else Colors.BG_SIDEBAR,
        border_radius=20,
        padding=ft.Padding.symmetric(horizontal=12, vertical=6),
        on_click=on_click,
    )


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
