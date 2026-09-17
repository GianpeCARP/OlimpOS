# =============================================================================
# views/actividades.py — ABM del catálogo de actividades
# =============================================================================
# Espejo de ActividadesAdminView.tsx de la PWA. Cada actividad se muestra con
# sus planes anidados: un plan suelto ("12 clases al mes") no significa nada sin
# saber de qué actividad es, así que se gestionan juntos en la misma tarjeta.
#
# Desde acá se puede: dar de alta/editar una actividad, darla de baja y
# reactivarla, agregar/editar/dar de baja sus planes, y asignarle profesores.
# Todas las acciones escriben contra la API real.

import flet as ft
from app.config import Colors, Fonts, Radius, Routes, alpha
from app.state import app_state
from app.components.agenda_turnos import agenda_turnos
from app.components.ui import (build_topbar, section_card, primary_button,
                               secondary_button, icon_action, input_field,
                               select_field, empty_state, divider_row,
                               show_snack, confirm_dialog, form_dialog,
                               open_dialog, close_dialog)


class ActividadesView:
    def __init__(self, page: ft.Page, router):
        self.page   = page
        self.router = router

    # ── Resultado de una escritura ───────────────────────────────────────────

    def _resolver(self, resultado: dict):
        """
        Muestra lo que contestó el backend y, si escribió, recarga la sección.

        El ABM cambia la grilla entera —una actividad nueva, un plan que
        desaparece del catálogo— así que se vuelve a construir la vista en vez
        de parchear controles sueltos. Es una pantalla de configuración, no el
        panel de recepción: se usa de a ratos y un refresco completo no molesta.
        """
        if not resultado["ok"]:
            show_snack(self.page, resultado["mensaje"], Colors.STATUS_DANGER)
            return
        show_snack(self.page, resultado["mensaje"], Colors.STATUS_OK)
        self.router.navigate(Routes.ACTIVIDADES)

    @staticmethod
    def _entero(campo, por_defecto: int = 0) -> int:
        """
        Lee un campo de texto como número.

        Devuelve el default si está vacío o tiene letras, en vez de reventar:
        el backend valida igual (cupo >= 1, precio >= 0) y su mensaje es más
        útil que un ValueError en la consola.
        """
        try:
            return int(float((campo.value or "").strip().replace(",", ".")))
        except (ValueError, AttributeError):
            return por_defecto

    # ── Construcción ─────────────────────────────────────────────────────────

    def build(self) -> ft.Column:
        # Sin filtrar por activa: el ABM también tiene que mostrar las dadas de
        # baja para poder reactivarlas. El backend devuelve todas.
        actividades = app_state.get_actividades()

        horarios = app_state.get_horarios()

        topbar = build_topbar(
            "Actividades",
            f"{len(actividades)} actividades · {len(horarios)} horarios semanales",
            actions=[
                primary_button("Nuevo horario", ft.Icons.CALENDAR_MONTH_ROUNDED,
                               on_click=lambda e: self._form_horario(actividades)),
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

        # La grilla semanal va ARRIBA del catálogo a propósito. El catálogo
        # dice qué actividades existen; la grilla dice cuándo pasan, que es lo
        # que hace que existan turnos y que alguien pueda reservar. Una
        # actividad sin horario no la ve nadie.
        cuerpo = ft.Column([
            self._grilla_semanal(horarios),
            ft.Container(height=24),
            # Gemela de <AgendaTurnos /> en ActividadesAdminView.tsx: el
            # horario dice cuándo hay clase; la agenda, quién se anotó a cada una.
            agenda_turnos(self.page,
                          on_cambio=lambda: self.router.navigate(Routes.ACTIVIDADES)),
            ft.Container(height=24),
            ft.Text("Catálogo", color=Colors.TEXT_PRIMARY, size=16,
                    weight=ft.FontWeight.BOLD),
            ft.Container(height=12),
            cuerpo,
        ], spacing=0)

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

    # ── Horario semanal ───────────────────────────────────────────────────────
    #
    # De acá salen los turnos. Antes cada Turno se cargaba a mano: si Yoga era
    # lunes y miércoles 19:00, alguien creaba dos filas por semana para
    # siempre, y el día que se olvidaba la clase directamente no existía —
    # nadie podía reservarla y el recepcionista se enteraba cuando llegaba la
    # gente. Acá se declara una vez y el sistema genera las próximas 4 semanas.

    DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

    def _grilla_semanal(self, horarios: list[dict]) -> ft.Container:
        """
        La semana como una grilla de 7 columnas.

        Se muestra así y no como una lista porque el horario de un gimnasio se
        piensa en semana: lo que uno quiere ver de un vistazo es qué días
        están vacíos y a qué hora se pisan dos clases. Una lista ordenada por
        actividad esconde exactamente eso.
        """
        activos = [h for h in horarios if h["activo"]]
        turnos_generados = sum(h["turnos_futuros"] for h in activos)

        encabezado = ft.Row([
            ft.Column([
                ft.Text("Horario semanal", color=Colors.TEXT_PRIMARY, size=16,
                        weight=ft.FontWeight.BOLD),
                ft.Text(
                    f"{turnos_generados} turnos generados hacia adelante"
                    if turnos_generados else
                    "Sin horarios no hay turnos, y sin turnos nadie puede reservar.",
                    color=Colors.TEXT_MUTED, size=12,
                ),
            ], spacing=2, tight=True, expand=True),
            ft.TextButton(
                "Regenerar turnos",
                icon=ft.Icons.AUTORENEW_ROUNDED,
                style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                on_click=lambda e: self._regenerar(),
            ),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER)

        if not activos:
            return section_card(ft.Column([
                encabezado,
                ft.Container(height=16),
                empty_state(
                    "Todavía no hay ningún horario cargado. Mientras no haya "
                    "uno, el panel de Recepción va a estar vacío.",
                    ft.Icons.CALENDAR_MONTH_ROUNDED,
                ),
            ], spacing=0))

        columnas = []
        for indice, dia in enumerate(self.DIAS, start=1):
            # isoweekday: 1 = lunes ... 7 = domingo. Mismo criterio que guarda
            # la base, así que no hay conversión en el medio.
            del_dia = sorted((h for h in activos if h["dia_num"] == indice),
                             key=lambda h: h["hora"])
            columnas.append(ft.Container(
                content=ft.Column([
                    ft.Text(dia.upper(), color=Colors.TEXT_MUTED, size=10,
                            weight=ft.FontWeight.W_600),
                    ft.Container(height=8),
                    *([self._chip_horario(h) for h in del_dia] or [
                        ft.Text("—", color=Colors.TEXT_MUTED, size=12)
                    ]),
                ], spacing=6),
                col={"xs": 12, "sm": 6, "md": 3, "lg": 12 / 7},
                padding=ft.Padding.all(8),
            ))

        return section_card(ft.Column([
            encabezado,
            ft.Container(height=16),
            ft.ResponsiveRow(columnas, spacing=4, run_spacing=8),
        ], spacing=0))

    def _chip_horario(self, h: dict) -> ft.Container:
        """
        Un horario dentro de su día. Click = darlo de baja.

        Muestra cuántos turnos futuros generó: es la única forma de ver de un
        vistazo que la generación automática está corriendo. Un horario activo
        con 0 turnos futuros significa que algo no está funcionando.
        """
        sin_turnos = h["turnos_futuros"] == 0
        color = Colors.STATUS_WARN if sin_turnos else Colors.PRIMARY_VOLT

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(h["hora"], color=color, size=13,
                            weight=ft.FontWeight.BOLD, font_family=Fonts.MONO),
                    ft.Container(expand=True),
                    # Cambiar el profesor SIN rehacer el horario: darlo de baja
                    # y crearlo de nuevo cancela los turnos que ya tenían gente.
                    ft.IconButton(
                        ft.Icons.SCHOOL_ROUNDED, icon_color=Colors.TEXT_MUTED,
                        icon_size=14, tooltip="Cambiar el profesor",
                        on_click=lambda e, x=h: self._cambiar_profesor_horario(x),
                    ),
                    ft.IconButton(
                        ft.Icons.CLOSE_ROUNDED, icon_color=Colors.TEXT_MUTED,
                        icon_size=14, tooltip="Dar de baja este horario",
                        on_click=lambda e, x=h: self._baja_horario(x),
                    ),
                ], spacing=0, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Text(h["actividad"], color=Colors.TEXT_PRIMARY, size=12),
                ft.Text(f"cupo {h['cupo']} · {h['profesor']}",
                        color=Colors.TEXT_MUTED, size=10),
                ft.Text(
                    "sin turnos generados" if sin_turnos
                    else f"{h['turnos_futuros']} turnos",
                    color=Colors.STATUS_WARN if sin_turnos else Colors.TEXT_MUTED,
                    size=10,
                ),
            ], spacing=2, tight=True),
            bgcolor=alpha(color, 0.08),
            border=ft.Border.all(1, alpha(color, 0.3)),
            border_radius=Radius.SM,
            padding=ft.Padding.symmetric(horizontal=8, vertical=6),
        )

    def _form_horario(self, actividades: list[dict]):
        """
        Alta de un horario semanal.

        Al guardar, el backend genera los turnos en el acto. Es deliberado que
        no espere al próximo arranque: quien acaba de cargar "Yoga los lunes
        19:00" espera ver los turnos, y si aparecieran recién mañana pensaría
        que no se guardó y lo cargaría de nuevo.

        El PROFESOR se elige acá (gemelo de HorarioFormModal.tsx): pasa a cada
        turno generado y de ahí sale "Mis clases". Antes no se pedía, y un
        profesor asignado a la actividad igual veía su pantalla vacía. Sólo se
        ofrecen los asignados a esa actividad y, si hay uno solo, viene elegido;
        el cupo arranca en el de la actividad.
        """
        vigentes = [a for a in actividades if a["activa"]]
        if not vigentes:
            show_snack(self.page,
                       "Primero cargá una actividad: el horario es de una actividad.",
                       Colors.STATUS_WARN)
            return

        act_ref = ft.Ref[ft.Dropdown]()
        dia_ref = ft.Ref[ft.Dropdown]()
        hora_ref = ft.Ref[ft.TextField]()
        cupo_ref = ft.Ref[ft.TextField]()
        prof_ref = ft.Ref[ft.Dropdown]()
        sin_profesor = "0"

        def opciones_profesor(actividad: dict) -> tuple[list, str]:
            asignados = actividad["profesores"]
            # La etiqueta lleva legajo o DNI: dos homónimos daban dos opciones
            # idénticas y el profesor del horario pasa a cada turno generado,
            # así que elegir mal se arrastra hasta "Mis clases".
            opciones = [ft.dropdown.Option(key=sin_profesor, text="Sin profesor")] + [
                ft.dropdown.Option(
                    key=str(p["id"]),
                    text=f"{p['nombre']} · {p['senia']}" if p.get("senia") else p["nombre"],
                )
                for p in asignados
            ]
            elegido = str(asignados[0]["id"]) if len(asignados) == 1 else sin_profesor
            return opciones, elegido

        def al_elegir_actividad(e):
            actividad = next((a for a in vigentes if str(a["id"]) == act_ref.current.value), None)
            if actividad is None:
                return
            prof_ref.current.options, prof_ref.current.value = opciones_profesor(actividad)
            cupo_ref.current.value = str(actividad["cupo"])
            prof_ref.current.update()
            cupo_ref.current.update()

        opciones_iniciales, profesor_inicial = opciones_profesor(vigentes[0])

        def guardar():
            hora = (hora_ref.current.value or "").strip() if hora_ref.current else ""
            # Se valida acá antes de salir a la red: "19" o "7:5" son errores
            # que se ven mirando el campo, y no vale gastar un viaje y un
            # mensaje genérico del backend en algo tan evidente.
            partes = hora.split(":")
            if len(partes) != 2 or not all(p.strip().isdigit() for p in partes):
                show_snack(self.page, "La hora va como HH:MM. Ej: 19:00",
                           Colors.STATUS_DANGER)
                return
            h, m = int(partes[0]), int(partes[1])
            if not (0 <= h <= 23 and 0 <= m <= 59):
                show_snack(self.page, f"«{hora}» no es una hora válida.",
                           Colors.STATUS_DANGER)
                return

            cupo = self._entero(cupo_ref.current.value if cupo_ref.current else "", 0)
            if cupo <= 0:
                show_snack(self.page, "El cupo tiene que ser mayor que cero: "
                                      "una clase de cupo 0 no la puede tomar nadie.",
                           Colors.STATUS_DANGER)
                return

            id_profesor = int(prof_ref.current.value or sin_profesor)
            resultado = app_state.crear_horario({
                "id_actividad": int(act_ref.current.value),
                "id_sede": 1,
                "dia_semana": int(dia_ref.current.value),
                "hora": f"{h:02d}:{m:02d}:00",
                "cupo": cupo,
                "id_profesor": id_profesor or None,
            })
            self._resolver(resultado)

        dlg = form_dialog(
            self.page,
            "Nuevo horario semanal",
            [
                ft.Text("Se van a generar los turnos de las próximas 4 semanas, "
                        "y se renuevan solos.",
                        color=Colors.TEXT_MUTED, size=12),
                ft.Container(height=12),
                ft.Dropdown(
                    ref=act_ref, label="Actividad",
                    options=[ft.dropdown.Option(key=str(a["id"]), text=a["nombre"])
                             for a in vigentes],
                    value=str(vigentes[0]["id"]),
                    on_select=al_elegir_actividad,
                    color=Colors.TEXT_PRIMARY, bgcolor=Colors.BG_INPUT,
                    border_color=Colors.BORDER, focused_border_color=Colors.ACCENT,
                    border_radius=Radius.MD,
                ),
                ft.Container(height=12),
                ft.Dropdown(
                    ref=dia_ref, label="Día",
                    options=[ft.dropdown.Option(key=str(i), text=d)
                             for i, d in enumerate(self.DIAS, start=1)],
                    value="1",
                    color=Colors.TEXT_PRIMARY, bgcolor=Colors.BG_INPUT,
                    border_color=Colors.BORDER, focused_border_color=Colors.ACCENT,
                    border_radius=Radius.MD,
                ),
                ft.Container(height=12),
                input_field("Hora (HH:MM)", "Ej: 19:00", ref=hora_ref,
                            icon=ft.Icons.SCHEDULE_ROUNDED),
                ft.Container(height=12),
                input_field("Cupo", "Ej: 20", ref=cupo_ref,
                            icon=ft.Icons.GROUP_ROUNDED,
                            value=str(vigentes[0]["cupo"])),
                ft.Container(height=12),
                ft.Dropdown(
                    ref=prof_ref, label="Profesor",
                    options=opciones_iniciales, value=profesor_inicial,
                    color=Colors.TEXT_PRIMARY, bgcolor=Colors.BG_INPUT,
                    border_color=Colors.BORDER, focused_border_color=Colors.ACCENT,
                    border_radius=Radius.MD,
                ),
            ],
            on_save=guardar,
            texto_guardar="Crear y generar turnos",
        )
        open_dialog(self.page, dlg)

    def _cambiar_profesor_horario(self, h: dict):
        """
        Le cambia (o le saca) el profesor a un horario YA CREADO. Gemelo de
        ProfesorHorarioModal.tsx.

        Antes la única forma era darlo de baja y cargarlo de nuevo, y eso genera
        turnos nuevos dejando cancelados los viejos: corregir un dato
        administrativo le volteaba la clase a los que ya estaban anotados.

        Sólo los profesores ASIGNADOS a esa actividad, que es lo único que el
        backend acepta: ofrecer los demás sería ofrecer un 409.
        """
        actividad = next((a for a in app_state.get_actividades()
                          if a["id"] == h.get("id_actividad")), None)
        asignados = actividad["profesores"] if actividad else []

        sin_profesor = "0"
        prof_ref = ft.Ref[ft.Dropdown]()

        if not asignados:
            cuerpo = ft.Text(
                f"{h['actividad']} no tiene profesores asignados. Asignale uno "
                "desde la tarjeta de la actividad y volvé acá.",
                color=Colors.TEXT_SECONDARY, size=13)
            acciones_extra = []
        else:
            opciones = [ft.dropdown.Option(key=sin_profesor, text="Sin profesor")] + [
                ft.dropdown.Option(
                    key=str(p["id"]),
                    text=f"{p['nombre']} · {p['senia']}" if p.get("senia") else p["nombre"],
                )
                for p in asignados
            ]
            actual = h.get("id_profesor")
            cuerpo = ft.Column([
                ft.Dropdown(
                    ref=prof_ref, label="Profesor", options=opciones,
                    value=str(actual) if actual else sin_profesor,
                    color=Colors.TEXT_PRIMARY, bgcolor=Colors.BG_INPUT,
                    border_color=Colors.BORDER, focused_border_color=Colors.ACCENT,
                    border_radius=10,
                ),
                ft.Container(height=8),
                ft.Text(
                    "El cambio también se aplica a los turnos de hoy en adelante "
                    "que ya estén generados. Los que ya pasaron quedan con el "
                    "profesor que dio esa clase.",
                    color=Colors.TEXT_MUTED, size=11),
            ], spacing=0, tight=True)
            acciones_extra = [ft.TextButton(
                "Guardar", style=ft.ButtonStyle(color=Colors.ACCENT),
                on_click=lambda e: self._guardar_profesor_horario(h, prof_ref,
                                                                  sin_profesor, dlg))]

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Profesor de {h['actividad']} — {h['dia']} {h['hora']}",
                          color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD, size=15),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(content=cuerpo, width=380),
            actions=[*acciones_extra, ft.TextButton(
                "Cerrar", style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                on_click=lambda e: close_dialog(self.page, dlg))],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(self.page, dlg)

    def _guardar_profesor_horario(self, h: dict, prof_ref, sin_profesor: str, dlg):
        elegido = (prof_ref.current.value if prof_ref.current else None) or sin_profesor
        id_profesor = int(elegido)
        resultado = app_state.cambiar_profesor_de_horario(h["id"], id_profesor or None)
        close_dialog(self.page, dlg)
        show_snack(self.page, resultado["mensaje"],
                   Colors.SUCCESS if resultado["ok"] else Colors.STATUS_DANGER)
        if resultado["ok"]:
            self.router.navigate(Routes.ACTIVIDADES)

    def _baja_horario(self, h: dict):
        """
        Da de baja un horario.

        Dar de baja significa "no generes más", NO "borrá lo que ya existe".
        Los turnos futuros ya generados se mantienen TODOS: pueden tener gente
        anotada, y hacerlos desaparecer dejaría reservas apuntando a la nada y
        socios que creen tener clase.

        El backend sabe cancelar los que quedaron vacíos, pero hay que
        pedírselo explícitamente y desde acá no se le pide. Cancelar clases
        futuras es una decisión de quien maneja el gimnasio, no un efecto
        secundario de editar un horario — si quiere sacarlas, las cancela una
        por una y ve cuáles.
        """
        def confirmar():
            self._resolver(app_state.cambiar_estado_horario(h["id"], False))

        dlg = confirm_dialog(
            self.page,
            "Dar de baja el horario",
            f"{h['actividad']} — {h['dia']} {h['hora']}\n\n"
            f"Deja de generar turnos nuevos. Los {h['turnos_futuros']} que ya "
            f"están generados NO se tocan: si querés sacarlos, cancelalos "
            f"desde la grilla de turnos.",
            on_confirm=confirmar,
        )
        open_dialog(self.page, dlg)

    def _regenerar(self):
        """
        Fuerza la generación de turnos.

        El backend ya la corre sola al arrancar y es idempotente, así que este
        botón no puede romper nada. Está para el caso de quien acaba de cargar
        varios horarios y quiere ver el resultado sin reiniciar el servidor.
        """
        resultado = app_state.generar_turnos()
        self._resolver(resultado)

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
            chips = [_pill(p["nombre"], Colors.TEXT_SECONDARY,
                           con_icono=ft.Icons.PERSON_ROUNDED)
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
        # CLASE_SUELTA aparte (igual que etiquetaLimite en la PWA): caía en el
        # else y se leía "1x por semana", como si fuera un abono semanal.
        if plan["tipo"] == "CLASE_SUELTA":
            etiqueta = "Una clase"
        else:
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
            n_cupo = self._entero(cupo, 1)
            # Mismo tope que el backend (ActividadCrear.cupo_default, le=100).
            # Se valida acá también para no gastar un viaje de red en algo que
            # se ve mirando el campo: ningún gimnasio dicta una clase de 500
            # personas, así que un número así es un dedo de más.
            if not 1 <= n_cupo <= 100:
                show_snack(self.page,
                           "El cupo por turno va de 1 a 100.",
                           Colors.STATUS_DANGER)
                return

            datos = {
                "nombre": (nombre.value or "").strip(),
                "descripcion": (desc.value or "").strip() or None,
                "cupo_default": n_cupo,
                "precio_clase_suelta": self._entero(precio, 0),
                "horas_anticipacion_cancelacion": self._entero(horas, 0),
            }
            self._resolver(
                app_state.editar_actividad(act["id"], datos) if editando
                else app_state.crear_actividad(datos)
            )

        open_dialog(self.page, form_dialog(
            self.page,
            "Editar actividad" if editando else "Nueva actividad",
            [nombre, desc, cupo, precio, horas],
            on_save=guardar,
        ))

    def _baja_actividad(self, act: dict):
        activa = act["activa"]

        def confirmar():
            # Se manda el estado DESTINO, no un toggle: con la grilla
            # desactualizada, "dar de baja" sobre algo ya dado de baja lo
            # reactivaría.
            self._resolver(app_state.cambiar_estado_actividad(act["id"], not activa))

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
            tipo_limite = tipo.value or "POR_MES"
            n_cant = self._entero(cant, 1)

            # El tope depende del tipo, igual que en el backend
            # (PlanActividadCrear._cantidad_posible_para_el_tipo): una semana
            # tiene 7 días y un mes 31. "8 clases por semana" no es un plan
            # caro, es un plan IMPOSIBLE — el socio lo paga y nunca puede usar
            # lo que compró, porque no existen tantos días donde gastarlo.
            topes = {"POR_SEMANA": (7, "por semana"),
                     "POR_MES": (31, "por mes"),
                     "CLASE_SUELTA": (1, "de clase suelta")}
            tope, etiqueta = topes.get(tipo_limite, (31, "por mes"))
            if not 1 <= n_cant <= tope:
                show_snack(self.page,
                           f"Un plan {etiqueta} va de 1 a {tope} clase(s).",
                           Colors.STATUS_DANGER)
                return

            datos = {
                "nombre": (nombre.value or "").strip(),
                "tipo_limite": tipo_limite,
                "cantidad": n_cant,
                "precio": self._entero(precio, 0),
            }
            self._resolver(
                app_state.editar_plan_actividad(plan["id"], datos) if editando
                else app_state.crear_plan_actividad(act["id"], datos)
            )

        open_dialog(self.page, form_dialog(
            self.page,
            "Editar plan" if editando else f"Nuevo plan de {act['nombre']}",
            [nombre, tipo, cant, precio],
            on_save=guardar,
        ))

    def _baja_plan(self, act: dict, plan: dict):
        activo = plan["activo"]

        def confirmar():
            self._resolver(app_state.cambiar_estado_plan(plan["id"], not activo))

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
        profesores = app_state.get_profesores()
        # Por ID y no por nombre. Comparando nombres, dos profesores que se
        # llaman igual salían los dos como "Asignado" aunque sólo uno lo
        # estuviera — y tocar a uno parecía afectar al otro. Ver el comentario
        # de get_actividades en state.py.
        asignados = {p["id"] for p in act["profesores"]}

        filas = []
        for prof in profesores:
            filas.append(self._fila_profesor(act, prof, prof["id"] in asignados))

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
                    # Legajo o DNI adelante de la especialidad: sin esto, dos
                    # profesores que se llaman igual se ven idénticos acá.
                    ft.Text(" · ".join(x for x in (prof.get("senia"),
                                                  prof["especialidad"]) if x),
                            color=Colors.TEXT_MUTED, size=12,
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
            """
            Asigna o quita al profesor, y recién después pinta.

            El orden importa: si la fila se pintara primero y el pedido
            fallara, quedaría marcada como asignada sin estarlo — y como este
            diálogo no tiene botón de guardar, nadie se enteraría hasta que
            alguien programara un turno con un profesor que no dicta esa
            actividad. Se escribe, se chequea, y sólo entonces se refleja.
            """
            asignar = estado.value == "Asignar"
            resultado = (app_state.asignar_profesor(act["id"], prof["id"]) if asignar
                         else app_state.desasignar_profesor(act["id"], prof["id"]))

            if not resultado["ok"]:
                show_snack(self.page, resultado["mensaje"], Colors.STATUS_DANGER)
                return

            estado.value = "Asignado" if asignar else "Asignar"
            estado.color = Colors.PRIMARY_VOLT if asignar else Colors.TEXT_MUTED
            fila.bgcolor = alpha(Colors.PRIMARY_VOLT, 0.08) if asignar else None
            fila.border = ft.Border.all(
                1, Colors.PRIMARY_VOLT if asignar else Colors.BORDER_IDLE)
            fila.content.controls[0].color = (Colors.PRIMARY_VOLT if asignar
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
