# =============================================================================
# views/rutinas.py — Gestión de rutinas de entrenamiento
# =============================================================================
# Gemela de views/rutinas/ de la PWA (RutinasView, RutinaFormModal,
# RutinaDetailModal, AsignarRutinaModal, EjercicioFormModal).
#
#   - Tarjetas con nivel, días, entrenador y socios asignados.
#   - Detalle con la planilla de ejercicios por día.
#   - Alta y edición CON ejercicios elegidos del catálogo, por día.
#   - Asignar la rutina a un socio, y baja/reactivación.
#   - Alta de ejercicios del catálogo con el link del video tutorial.
#
# QUIÉN TOCA QUÉ: hace falta la acción `gestionRutinas`, y además que la
# rutina sea editable para esta sesión — un Entrenador ve las de sus colegas
# pero no las toca. Lo decide el backend (`puede_editar`) y es el que de
# verdad lo impide; acá sólo se decide qué botones se dibujan.

import flet as ft
from app.config import Colors, Radius, Routes
from app.state import app_state
from app.components.ui import (build_topbar, confirm_dialog, level_badge, primary_button,
                                input_field, show_snack, open_dialog, close_dialog,
                                status_badge)

NIVELES = ["Principiante", "Intermedio", "Avanzado"]

# Tope de socios dibujados en el diálogo de asignar: con cientos, se busca.
MAX_SOCIOS_LISTA = 50


class RutinasView:
    def __init__(self, page: ft.Page, router):
        self.page   = page
        self.router = router
        self.puede_gestionar = app_state.puede("gestionRutinas")

    def build(self) -> ft.Column:
        rutinas = app_state.get_rutinas()

        acciones = []
        if self.puede_gestionar:
            acciones = [
                primary_button("Nuevo Ejercicio", ft.Icons.ADD_ROUNDED,
                               on_click=self._open_form_ejercicio),
                primary_button("Nueva Rutina", ft.Icons.ADD_ROUNDED,
                               on_click=lambda e: self._open_form()),
            ]

        topbar = build_topbar("Rutinas", f"{len(rutinas)} rutinas disponibles",
                              actions=acciones)

        if rutinas:
            contenido = ft.ResponsiveRow(
                [self._rutina_card(r) for r in rutinas],
                spacing=16, run_spacing=16,
            )
        else:
            contenido = ft.Text("Todavía no hay rutinas cargadas.",
                                color=Colors.TEXT_MUTED, size=13)

        return ft.Column([
            topbar,
            ft.Container(
                content=ft.Column([contenido], spacing=0,
                                  scroll=ft.ScrollMode.AUTO, expand=True),
                padding=ft.Padding.all(24),
                expand=True,
            ),
        ], spacing=0, expand=True)

    def _gestionable(self, r: dict) -> bool:
        return self.puede_gestionar and r.get("puede_editar", True)

    # ── Tarjeta ───────────────────────────────────────────────────────────────

    def _rutina_card(self, r: dict) -> ft.Container:
        # Barra de ocupación: número de PRESENTACIÓN (el backend no pone cupo),
        # el mismo que usa la PWA.
        progress = min(r["asignados"] / 20, 1.0)

        botones = [_boton_suave("Ver detalles", lambda e, x=r: self._open_detail(x), Colors.ACCENT)]
        if self._gestionable(r):
            botones += [
                _boton_suave("Editar", lambda e, x=r: self._open_form(x)),
                _boton_suave("Asignar", lambda e, x=r: self._open_asignar(x)),
            ]

        return ft.Container(
            col={"xs": 12, "sm": 6, "md": 4},
            content=ft.Column([
                ft.Row([
                    ft.Container(
                        content=ft.Icon(ft.Icons.FITNESS_CENTER_ROUNDED,
                                        color=Colors.ACCENT, size=22),
                        width=44, height=44, border_radius=12,
                        bgcolor=Colors.ACCENT_GLOW,
                        alignment=ft.Alignment.CENTER,
                    ),
                    ft.Container(expand=True),
                    level_badge(r["nivel"]),
                    *([] if r["activo"] else [status_badge("Inactiva")]),
                ], spacing=6),
                ft.Container(height=14),
                ft.Text(r["nombre"], color=Colors.TEXT_PRIMARY, size=16,
                        weight=ft.FontWeight.BOLD),
                ft.Container(height=8),
                ft.Row([
                    _info_pill(ft.Icons.CALENDAR_TODAY_ROUNDED, f"{r['dias']} días/sem"),
                    _info_pill(ft.Icons.PERSON_ROUNDED, r["entrenador"]),
                ], spacing=8, wrap=True),
                *([ft.Container(height=6),
                   ft.Text(r["objetivo"], color=Colors.TEXT_SECONDARY, size=12)]
                  if r["objetivo"] else []),
                ft.Container(height=14),
                ft.Row([
                    ft.Text("Asignados:", color=Colors.TEXT_MUTED, size=12),
                    ft.Text(f"{r['asignados']} socios", color=Colors.TEXT_SECONDARY,
                            size=12, weight=ft.FontWeight.W_500),
                ], spacing=6),
                ft.Container(height=6),
                ft.ProgressBar(value=progress, bgcolor=Colors.BG_INPUT,
                               color=Colors.ACCENT, height=4, border_radius=2),
                ft.Container(height=14),
                ft.Row(botones, spacing=8, wrap=True),
            ], spacing=0),
            bgcolor=Colors.BG_CARD,
            border_radius=14,
            border=ft.Border.all(1, Colors.BORDER),
            padding=20,
        )

    # ── Detalle ───────────────────────────────────────────────────────────────

    def _open_detail(self, r: dict):
        """La rutina con su planilla de ejercicios por día."""
        detalle = app_state.get_rutina(r["id"])
        if detalle is None:
            show_snack(self.page, "No se pudo cargar la rutina.", Colors.STATUS_DANGER)
            return

        filas = [
            ft.Row([level_badge(r["nivel"]),
                    status_badge("Activa" if detalle["activo"] else "Inactiva")], spacing=6),
            ft.Container(height=12),
            _detail_row("Frecuencia", f"{detalle['dias']} días por semana"),
            _detail_row("Entrenador", detalle["entrenador"]),
            _detail_row("Asignados", f"{detalle['asignados']} socios"),
            _detail_row("Objetivo", detalle["objetivo"] or "Sin especificar"),
            ft.Container(height=12),
        ]

        ejercicios = detalle["ejercicios"]
        if not ejercicios:
            filas.append(ft.Text("Esta rutina todavía no tiene ejercicios.",
                                 color=Colors.TEXT_MUTED, size=13))
        for dia in sorted({e["dia"] for e in ejercicios}):
            filas.append(ft.Text(f"DÍA {dia}", color=Colors.TEXT_MUTED, size=11,
                                 weight=ft.FontWeight.W_600))
            for e in (x for x in ejercicios if x["dia"] == dia):
                filas.append(ft.Column([
                    ft.Text(e["nombre"], color=Colors.TEXT_PRIMARY, size=13),
                    ft.Text(" · ".join(p for p in [e["grupo"], _resumen(e)] if p),
                            color=Colors.TEXT_MUTED, size=11),
                    *([ft.Text(e["observaciones"], color=Colors.STATUS_WARN, size=11)]
                      if e["observaciones"] else []),
                ], spacing=0, tight=True))
            filas.append(ft.Container(height=6))

        acciones = [ft.TextButton("Cerrar", style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                                  on_click=lambda e: close_dialog(self.page, dlg))]
        if self._gestionable(r):
            acciones = [
                ft.TextButton("Reactivar" if not detalle["activo"] else "Dar de baja",
                              style=ft.ButtonStyle(color=Colors.STATUS_DANGER
                                                   if detalle["activo"] else Colors.STATUS_OK),
                              on_click=lambda e: (close_dialog(self.page, dlg),
                                                  self._cambiar_estado(detalle))),
                *acciones,
                ft.TextButton("Asignar", style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                              on_click=lambda e: (close_dialog(self.page, dlg),
                                                  self._open_asignar(r))),
                ft.TextButton("Editar", style=ft.ButtonStyle(color=Colors.ACCENT),
                              on_click=lambda e: (close_dialog(self.page, dlg),
                                                  self._open_form(r))),
            ]

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(detalle["nombre"], color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=460, height=460,
                content=ft.Column(filas, spacing=6, scroll=ft.ScrollMode.AUTO),
            ),
            actions=acciones,
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(self.page, dlg)

    def _cambiar_estado(self, r: dict):
        """Baja con confirmación; reactivar sin, porque es reversible y de bajo riesgo."""
        if not r["activo"]:
            self._aplicar(app_state.reactivar_rutina(r["id"]))
            return
        dlg = confirm_dialog(
            self.page, f"¿Dar de baja \"{r['nombre']}\"?",
            "Deja de ofrecerse para asignar. Los socios que la están siguiendo la terminan.",
            on_confirm=lambda: self._aplicar(app_state.baja_rutina(r["id"])),
            texto_confirmar="Dar de baja",
        )
        open_dialog(self.page, dlg)

    def _aplicar(self, resultado: dict):
        if not resultado["ok"]:
            show_snack(self.page, resultado["mensaje"], Colors.STATUS_DANGER)
            return
        show_snack(self.page, resultado["mensaje"], Colors.SUCCESS)
        self.router.navigate(Routes.RUTINAS)

    # ── Alta / edición con ejercicios ─────────────────────────────────────────

    def _open_form(self, rutina: dict = None):
        """
        Alta o edición de una rutina CON su planilla de ejercicios por día.

        Arriba los datos; abajo las pestañas de días, los ejercicios del día
        elegido (series, reps, peso, descanso, observaciones, orden) y el
        catálogo con buscador para sumar más. Al guardar se manda la planilla
        entera: en edición, el backend reemplaza la anterior por esta.

        El selector de entrenador existe porque `Rutina.id_entrenador` es NOT
        NULL y el Dueño no es entrenador. A un Entrenador el backend le devuelve
        sólo a sí mismo en esa lista.
        """
        es_edicion = rutina is not None
        detalle = app_state.get_rutina(rutina["id"]) if es_edicion else None
        if es_edicion and detalle is None:
            show_snack(self.page, "No se pudo cargar la rutina.", Colors.STATUS_DANGER)
            return

        entrenadores = app_state.get_entrenadores()
        catalogo = app_state.get_ejercicios()

        # La planilla. Los números van como texto: son inputs y se validan al guardar.
        items = [
            {
                "id_ejercicio": e["id_ejercicio"],
                "nombre": e["nombre"],
                "grupo": e["grupo"],
                "dia": e["dia"],
                "series": _texto(e["series"]),
                "repeticiones": e["repeticiones"] or "",
                "peso": _texto(e["peso"]),
                "descanso": _texto(e["descanso"]),
                "observaciones": e["observaciones"] or "",
            }
            for e in (detalle["ejercicios"] if detalle else [])
        ]
        estado = {"dia": 1}

        nombre_tf = input_field("Nombre de la rutina", "Ej: Fuerza Total",
                                icon=ft.Icons.FITNESS_CENTER_ROUNDED,
                                value=detalle["nombre"] if detalle else "")
        nivel_dd = _dropdown(
            "Nivel", [ft.dropdown.Option(n) for n in NIVELES],
            detalle["nivel"] if detalle and detalle["nivel"] in NIVELES else "Principiante",
            width=200,
        )
        dias_tf = input_field("Días por semana", "Entre 1 y 7", width=160,
                              value=str(detalle["dias"]) if detalle else "3")

        opciones_entrenador = [ft.dropdown.Option(key=str(x["id"]), text=x["nombre"])
                               for x in entrenadores]
        if detalle and detalle["id_entrenador"] is not None \
                and not any(x["id"] == detalle["id_entrenador"] for x in entrenadores):
            # Ya no está activo: se ofrece igual para no reemplazarlo en silencio.
            opciones_entrenador.append(ft.dropdown.Option(
                key=str(detalle["id_entrenador"]), text=f"{detalle['entrenador']} (inactivo)"))
        entrenador_dd = _dropdown(
            "Entrenador a cargo", opciones_entrenador,
            str(detalle["id_entrenador"]) if detalle
            else (str(entrenadores[0]["id"]) if entrenadores else None),
        )
        objetivo_tf = input_field("Objetivo", "Ej: Ganancia de fuerza general",
                                  value=detalle["objetivo"] if detalle else "")

        chips = ft.Row(spacing=6, wrap=True)
        lista = ft.Column(spacing=8)
        titulo_catalogo = ft.Text("", color=Colors.TEXT_PRIMARY, size=13,
                                  weight=ft.FontWeight.W_600)
        busqueda_tf = ft.TextField(
            hint_text="Buscar en el catálogo…", prefix_icon=ft.Icons.SEARCH_ROUNDED,
            color=Colors.TEXT_MAIN, text_size=13, dense=True,
            hint_style=ft.TextStyle(color=Colors.TEXT_MUTED),
            bgcolor=Colors.BG_INPUT, border_color=Colors.BORDER,
            focused_border_color=Colors.ACCENT, border_radius=Radius.MD,
        )
        catalogo_col = ft.Column(spacing=2, height=200, scroll=ft.ScrollMode.AUTO)

        def dias() -> int:
            crudo = (dias_tf.value or "").strip()
            return min(7, max(1, int(crudo))) if crudo.isdigit() else 1

        def render_catalogo():
            q = (busqueda_tf.value or "").strip().lower()
            en_dia = {it["id_ejercicio"] for it in items if it["dia"] == estado["dia"]}
            filtrados = [c for c in catalogo
                         if not q or q in c["nombre"].lower() or q in c["grupo"].lower()]
            titulo_catalogo.value = f"Agregar ejercicios al Día {estado['dia']}"
            catalogo_col.controls = [
                ft.Row([
                    ft.Column([
                        ft.Text(c["nombre"], color=Colors.TEXT_PRIMARY, size=13),
                        ft.Text(c["grupo"], color=Colors.TEXT_MUTED, size=11),
                    ], spacing=0, tight=True, expand=True),
                    ft.IconButton(
                        ft.Icons.CHECK_CIRCLE_ROUNDED if c["id"] in en_dia
                        else ft.Icons.ADD_CIRCLE_OUTLINE_ROUNDED,
                        icon_color=Colors.ACCENT if c["id"] in en_dia else Colors.TEXT_MUTED,
                        icon_size=20,
                        tooltip="Quitar del día" if c["id"] in en_dia else "Agregar al día",
                        on_click=lambda e, c=c: alternar(c),
                    ),
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER)
                for c in filtrados
            ] or [ft.Text("No hay ejercicios que coincidan." if catalogo
                          else "El catálogo está vacío: cargá ejercicios con \"Nuevo Ejercicio\".",
                          color=Colors.TEXT_MUTED, size=12)]

        def render():
            n = dias()
            estado["dia"] = min(estado["dia"], n)
            dia = estado["dia"]

            chips.controls = [_chip_dia(d, d == dia,
                                        sum(1 for it in items if it["dia"] == d),
                                        lambda e, d=d: elegir_dia(d))
                              for d in range(1, n + 1)]

            del_dia = [it for it in items if it["dia"] == dia]
            lista.controls = [fila(it, i, len(del_dia)) for i, it in enumerate(del_dia)] or [
                ft.Text(f"El Día {dia} todavía no tiene ejercicios.",
                        color=Colors.TEXT_MUTED, size=12)
            ]
            fuera = sum(1 for it in items if it["dia"] > n)
            if fuera:
                lista.controls.append(ft.Text(
                    f"Hay {fuera} ejercicio(s) en días que quedaron fuera de los {n} días por semana.",
                    color=Colors.STATUS_WARN, size=12))
            render_catalogo()
            self.page.update()

        def elegir_dia(d: int):
            estado["dia"] = d
            render()

        def alternar(c: dict):
            dia = estado["dia"]
            ya = next((it for it in items if it["dia"] == dia and it["id_ejercicio"] == c["id"]), None)
            if ya:
                items.remove(ya)
            else:
                items.append({"id_ejercicio": c["id"], "nombre": c["nombre"], "grupo": c["grupo"],
                              "dia": dia, "series": "", "repeticiones": "", "peso": "",
                              "descanso": "", "observaciones": ""})
            render()

        def mover(it: dict, delta: int):
            i = items.index(it)
            j = i + delta
            while 0 <= j < len(items) and items[j]["dia"] != it["dia"]:
                j += delta
            if 0 <= j < len(items):
                items[i], items[j] = items[j], items[i]
                render()

        def quitar(it: dict):
            items.remove(it)
            render()

        def campo(it: dict, etiqueta: str, clave: str, ancho=None) -> ft.TextField:
            def cambio(e, it=it, clave=clave):
                # Sin re-render: se guarda el valor y el foco no se pierde.
                it[clave] = e.control.value or ""
            return ft.TextField(
                label=etiqueta, value=it[clave], width=ancho, expand=ancho is None,
                dense=True, text_size=13, color=Colors.TEXT_MAIN,
                label_style=ft.TextStyle(color=Colors.TEXT_MUTED, size=12),
                bgcolor=Colors.BG_CARD, border_color=Colors.BORDER,
                focused_border_color=Colors.ACCENT, border_radius=Radius.SM,
                on_change=cambio,
            )

        def fila(it: dict, idx: int, total: int) -> ft.Container:
            return ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Column([
                            ft.Text(f"{idx + 1}. {it['nombre']}", color=Colors.TEXT_PRIMARY,
                                    size=13, weight=ft.FontWeight.W_500),
                            ft.Text(it["grupo"], color=Colors.TEXT_MUTED, size=11),
                        ], spacing=0, tight=True, expand=True),
                        ft.IconButton(ft.Icons.ARROW_UPWARD_ROUNDED, icon_size=16,
                                      icon_color=Colors.TEXT_MUTED, tooltip="Subir",
                                      disabled=idx == 0,
                                      on_click=lambda e, it=it: mover(it, -1)),
                        ft.IconButton(ft.Icons.ARROW_DOWNWARD_ROUNDED, icon_size=16,
                                      icon_color=Colors.TEXT_MUTED, tooltip="Bajar",
                                      disabled=idx == total - 1,
                                      on_click=lambda e, it=it: mover(it, 1)),
                        ft.IconButton(ft.Icons.DELETE_OUTLINE_ROUNDED, icon_size=16,
                                      icon_color=Colors.STATUS_DANGER, tooltip="Quitar",
                                      on_click=lambda e, it=it: quitar(it)),
                    ], spacing=0, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Row([
                        campo(it, "Series", "series", 90),
                        campo(it, "Reps", "repeticiones", 100),
                        campo(it, "Peso (kg)", "peso", 100),
                        campo(it, "Descanso (s)", "descanso", 120),
                    ], spacing=6, wrap=True),
                    ft.Row([campo(it, "Observaciones", "observaciones")]),
                ], spacing=6, tight=True),
                bgcolor=Colors.BG_INPUT,
                border=ft.Border.all(1, Colors.BORDER),
                border_radius=Radius.MD,
                padding=ft.Padding.all(10),
            )

        def guardar(e=None):
            nombre = (nombre_tf.value or "").strip()
            if not nombre:
                show_snack(self.page, "La rutina necesita un nombre.", Colors.STATUS_DANGER)
                return
            crudo = (dias_tf.value or "").strip()
            if not crudo.isdigit() or not 1 <= int(crudo) <= 7:
                show_snack(self.page, "Días por semana: un número entre 1 y 7.", Colors.STATUS_DANGER)
                return
            n = int(crudo)
            if any(it["dia"] > n for it in items):
                show_snack(self.page, "Hay ejercicios en días que quedan fuera de los días por "
                                      "semana. Quitalos o subí los días.", Colors.STATUS_DANGER)
                return
            try:
                ejercicios = _armar_ejercicios(items)
            except ValueError as ex:
                show_snack(self.page, str(ex), Colors.STATUS_DANGER)
                return

            datos = {
                "nombre": nombre,
                "nivel": nivel_dd.value,
                "dias_por_semana": n,
                "objetivo": (objetivo_tf.value or "").strip() or None,
                "id_entrenador": int(entrenador_dd.value) if entrenador_dd.value else None,
                "ejercicios": ejercicios,
            }
            resultado = (app_state.editar_rutina(detalle["id"], datos) if es_edicion
                         else app_state.crear_rutina(datos))
            if not resultado["ok"]:
                show_snack(self.page, resultado["mensaje"], Colors.STATUS_DANGER)
                return
            close_dialog(self.page, dlg)
            show_snack(self.page, resultado["mensaje"], Colors.SUCCESS)
            self.router.navigate(Routes.RUTINAS)

        dias_tf.on_change = lambda e: render()
        busqueda_tf.on_change = lambda e: (render_catalogo(), self.page.update())

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Editar Rutina" if es_edicion else "Nueva Rutina",
                          color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=640, height=600,
                content=ft.Column([
                    nombre_tf,
                    ft.Row([nivel_dd, dias_tf], spacing=12, wrap=True),
                    entrenador_dd,
                    objetivo_tf,
                    ft.Divider(height=1, color=Colors.BORDER),
                    ft.Text("Ejercicios", color=Colors.TEXT_PRIMARY, size=15,
                            weight=ft.FontWeight.BOLD),
                    chips,
                    lista,
                    ft.Divider(height=1, color=Colors.BORDER),
                    titulo_catalogo,
                    busqueda_tf,
                    catalogo_col,
                ], spacing=12, scroll=ft.ScrollMode.AUTO),
            ),
            actions=[
                ft.TextButton("Cancelar",
                              style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                              on_click=lambda e: close_dialog(self.page, dlg)),
                ft.TextButton("Guardar" if es_edicion else "Crear Rutina",
                              style=ft.ButtonStyle(color=Colors.ACCENT),
                              on_click=guardar),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        render()
        open_dialog(self.page, dlg)

    # ── Asignar a un socio ────────────────────────────────────────────────────

    def _open_asignar(self, r: dict):
        """
        Buscar un socio activo y asignarle la rutina. Si ya seguía otra, el
        backend la FINALIZA (queda en su historial) y deja esta.
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
            resultado = app_state.asignar_rutina(r["id"], s["id"])
            if not resultado["ok"]:
                show_snack(self.page, resultado["mensaje"], Colors.STATUS_DANGER)
                return
            close_dialog(self.page, dlg)
            show_snack(self.page, f"\"{r['nombre']}\" asignada a {s['nombre']}.", Colors.SUCCESS)
            self.router.navigate(Routes.RUTINAS)

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
            modal=True,
            title=ft.Text(f"Asignar \"{r['nombre']}\"", color=Colors.TEXT_PRIMARY,
                          weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=440,
                content=ft.Column([
                    busqueda,
                    ft.Text("Si el socio ya sigue otra rutina, se la finaliza y queda en su historial.",
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

    # ── Alta de ejercicio del catálogo ────────────────────────────────────────

    def _open_form_ejercicio(self, e=None):
        """
        Alta de un ejercicio del catálogo, con el link del video tutorial.

        El entrenador sólo pega el link de YouTube (del canal del gimnasio): el
        demonio del servidor lo baja solo y recién ahí el socio ve "Ver
        técnica". Nadie del personal necesita acceso al FTP.
        """
        nombre_tf      = input_field("Nombre", "Ej: Press de banca",
                                     icon=ft.Icons.FITNESS_CENTER_ROUNDED)
        grupo_tf       = input_field("Grupo muscular", "Ej: Pecho",
                                     icon=ft.Icons.ACCESSIBILITY_NEW_ROUNDED)
        descripcion_tf = input_field("Descripción", "Cómo se hace, qué cuidar...",
                                     multiline=True)
        video_tf       = input_field("Video (link de YouTube)",
                                     "https://www.youtube.com/watch?v=...",
                                     icon=ft.Icons.PLAY_CIRCLE_ROUNDED)
        maquina_cb     = ft.Checkbox(label="Requiere máquina", active_color=Colors.ACCENT)

        def guardar(e=None):
            nombre = (nombre_tf.value or "").strip()
            grupo = (grupo_tf.value or "").strip()
            if not nombre or not grupo:
                show_snack(self.page, "El ejercicio necesita nombre y grupo muscular.",
                           Colors.STATUS_DANGER)
                return
            video = (video_tf.value or "").strip() or None
            resultado = app_state.crear_ejercicio({
                "nombre": nombre,
                "grupo_muscular": grupo,
                "descripcion": (descripcion_tf.value or "").strip() or None,
                "url_video": video,
                "requiere_maquina": bool(maquina_cb.value),
            })
            if not resultado["ok"]:
                show_snack(self.page, resultado["mensaje"], Colors.STATUS_DANGER)
                return
            close_dialog(self.page, dlg)
            show_snack(self.page,
                       "Ejercicio creado. El video va a estar disponible en unos minutos."
                       if video else resultado["mensaje"], Colors.SUCCESS)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Nuevo Ejercicio", color=Colors.TEXT_PRIMARY,
                          weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=440,
                content=ft.Column([
                    nombre_tf, grupo_tf, descripcion_tf, video_tf,
                    ft.Text("El video tarda unos minutos en quedar disponible para los socios.",
                            color=Colors.TEXT_MUTED, size=11),
                    maquina_cb,
                ], spacing=12, tight=True),
            ),
            actions=[
                ft.TextButton("Cancelar",
                              style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                              on_click=lambda e: close_dialog(self.page, dlg)),
                ft.TextButton("Crear Ejercicio",
                              style=ft.ButtonStyle(color=Colors.ACCENT),
                              on_click=guardar),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(self.page, dlg)


# =============================================================================
# Helpers
# =============================================================================

def _texto(valor) -> str:
    """Número del backend → texto para un input ("60.0" se muestra "60")."""
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor)


def _numero(valor: str, campo: str, ejercicio: str, entero: bool):
    t = (valor or "").strip().replace(",", ".")
    if not t:
        return None
    try:
        n = float(t)
    except ValueError:
        n = -1
    if n < 0 or (entero and not n.is_integer()):
        raise ValueError(f"{ejercicio}: \"{valor}\" no es un valor válido para {campo}.")
    return int(n) if entero else n


def _armar_ejercicios(items: list[dict]) -> list[dict]:
    """
    La planilla lista para el backend. Gemela de armarEjercicios en
    planillaEjercicios.ts: el orden se numera dentro de cada día según la lista.
    """
    orden_por_dia: dict[int, int] = {}
    salida = []
    for it in sorted(items, key=lambda x: x["dia"]):  # sorted es estable
        orden_por_dia[it["dia"]] = orden_por_dia.get(it["dia"], 0) + 1
        salida.append({
            "id_ejercicio": it["id_ejercicio"],
            "dia": it["dia"],
            "orden": orden_por_dia[it["dia"]],
            "series": _numero(it["series"], "series", it["nombre"], True),
            "repeticiones": it["repeticiones"].strip()[:20] or None,
            "peso_sugerido": _numero(it["peso"], "el peso", it["nombre"], False),
            "descanso_segundos": _numero(it["descanso"], "el descanso", it["nombre"], True),
            "observaciones": it["observaciones"].strip() or None,
        })
    return salida


def _resumen(e: dict) -> str:
    partes = []
    if e["series"] is not None and e["repeticiones"]:
        partes.append(f"{e['series']} × {e['repeticiones']}")
    elif e["series"] is not None:
        partes.append(f"{e['series']} series")
    elif e["repeticiones"]:
        partes.append(e["repeticiones"])
    if e["peso"] is not None:
        partes.append(f"{_texto(e['peso'])} kg")
    if e["descanso"] is not None:
        partes.append(f"{e['descanso']}s desc.")
    return " · ".join(partes)


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


def _boton_suave(texto: str, on_click, color: str = None) -> ft.Container:
    return ft.Container(
        content=ft.Text(texto, color=color or Colors.TEXT_SECONDARY, size=12,
                        weight=ft.FontWeight.W_500),
        on_click=on_click,
        bgcolor=Colors.ACCENT_GLOW if color else Colors.BG_SIDEBAR,
        border_radius=8,
        padding=ft.Padding.symmetric(horizontal=12, vertical=6),
    )


def _info_pill(icon: str, text: str) -> ft.Container:
    """Chip informativo con ícono y texto (frecuencia, entrenador)."""
    return ft.Container(
        content=ft.Row([
            ft.Icon(icon, color=Colors.TEXT_MUTED, size=12),
            ft.Text(text, color=Colors.TEXT_SECONDARY, size=12),
        ], spacing=4, tight=True),
        bgcolor=Colors.BG_SIDEBAR,
        border_radius=20,
        padding=ft.Padding.symmetric(horizontal=10, vertical=4),
    )


def _detail_row(label: str, value: str) -> ft.Row:
    """Fila de detalle: label a la izquierda, valor a la derecha."""
    return ft.Row([
        ft.Text(f"{label}:", color=Colors.TEXT_MUTED, size=13, width=100),
        ft.Text(value, color=Colors.TEXT_PRIMARY, size=13, weight=ft.FontWeight.W_500,
                expand=True),
    ])
