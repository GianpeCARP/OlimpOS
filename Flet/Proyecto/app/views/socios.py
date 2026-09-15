# =============================================================================
# views/socios.py — Gestión de socios del gimnasio (CON FILTRADO ACTIVO)
# =============================================================================

import flet as ft
from app.config import Colors, Radius, Routes  # Paleta, radios y rutas
from app.permisos import Accion                # Qué botones se dibujan (espejo de SociosView.tsx)
from app.state import app_state               # Estado global con los datos de socios
# Componentes reutilizables del sistema de diseño
from app.components.ui import (build_topbar, status_badge, primary_button,
                               input_field, show_snack, open_dialog,
                               close_dialog)


class SociosView:
    """
    Vista de gestión de socios con filtrado dinámico en tiempo real
    por términos de búsqueda (input) y por estado (Todos/Activos/Vencidos).
    """

    def __init__(self, page: ft.Page, router):
        self.sort_ascending = True # True = A-Z, False = Z-A
        self.page   = page
        self.router = router
        # Ref al campo de búsqueda — permite leer su valor al filtrar
        self.search_ref = ft.Ref[ft.TextField]()
        # Ref a la Column que contiene la tabla — permite reemplazar su contenido al filtrar
        self.table_ref  = ft.Ref[ft.Column]()
        
        # NUEVO: Guardamos el estado del filtro seleccionado ("Todos", "Activos", "Vencidos")
        self.current_filter = "Todos"
        # NUEVO: Ref para el contenedor de la barra de búsqueda que aloja los chips
        self.search_row_ref = ft.Ref[ft.Row]()

    def build(self) -> ft.Column:
        """Construye y retorna el árbol completo de controles de la vista."""
        socios = app_state.get_socios()  # Obtiene la lista completa de socios

        # Topbar con título, conteo de socios y botón "Nuevo Socio"
        topbar = build_topbar(
            "Socios",
            f"{len(socios)} socios registrados",
            # Espejo de SociosView.tsx: el alta pide la acción altaBajaSocios.
            # Entrenador y Nutricionista ven la grilla (necesitan saber a quién
            # le asignan algo) pero sin ningún botón de gestión.
            actions=[
                primary_button("Nuevo Socio", ft.Icons.PERSON_ADD_ROUNDED,
                               on_click=self._open_form),
            ] if app_state.puede(Accion.ALTA_BAJA_SOCIOS) else []
        )

        # ── Barra de búsqueda + chips de filtro ──────────────────────────────
        # REFACTORIZADO: Metemos los chips adentro de un ft.Row con ref para poder redibujarlos
        search_bar = ft.Container(
            content=ft.Row(
                ref=self.search_row_ref,
                controls=[
                    # Campo de texto con búsqueda en tiempo real (on_change)
                    ft.TextField(
                        ref=self.search_ref,
                        hint_text="Buscar por nombre, plan...",
                        prefix_icon=ft.Icons.SEARCH_ROUNDED,
                        color=Colors.TEXT_PRIMARY,
                        hint_style=ft.TextStyle(color=Colors.TEXT_MUTED),
                        bgcolor=Colors.BG_INPUT,
                        border_color=Colors.BORDER,
                        focused_border_color=Colors.ACCENT,
                        border_radius=10,
                        expand=True,
                        height=44,
                        content_padding=ft.Padding.symmetric(horizontal=16, vertical=10),
                        on_change=self._on_search,  # Se llama en cada keystroke
                    ),
                    # Construimos los chips llamando a la nueva función interna
                    self._build_filter_chip("Todos"),
                    self._build_filter_chip("Activos"),
                    self._build_filter_chip("Vencidos"),
                    
                ], 
                spacing=10
            ),
            padding=ft.Padding.only(bottom=16),
        )

        # ── Tabla de socios ───────────────────────────────────────────────────
        table_content = self._build_table(socios)
        table_col = ft.Column(
            ref=self.table_ref,           # Ref para actualizar al filtrar
            controls=[table_content],     # La tabla es el único hijo inicial
        )

        # ── Ensamblado final ──────────────────────────────────────────────────
        body = ft.Column([
            topbar,
            ft.Container(
                content=ft.Column([
                    search_bar,
                    # Container con borde que envuelve la tabla
                    ft.Container(
                        content=table_col,
                        bgcolor=Colors.BG_CARD,
                        border_radius=14,
                        border=ft.Border.all(1, Colors.BORDER),
                        padding=0,
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    ),
                ], spacing=0, scroll=ft.ScrollMode.AUTO, expand=True),
                padding=ft.Padding.all(24),
                expand=True,
            ),
        ], spacing=0, expand=True)

        return body

    def _build_filter_chip(self, label: str) -> ft.Container:
        """
        NUEVO MÉTODO: Construye un chip de filtro interactivo.
        Determina sus colores basándose en si coincide con el filtro activo global.
        """
        # Chequeamos si este chip en particular es el seleccionado actualmente
        is_active = self.current_filter == label

        def on_chip_click(e):
            # 1. Cambiamos el estado global del filtro al que se clickeó
            self.current_filter = label
            
            # 2. Re-renderizamos la fila de búsqueda para que cambien los colores de los chips
            # Reemplazamos los controles manteniendo el buscador intacto en la posición 0
            search_input = self.search_row_ref.current.controls[0]
            self.search_row_ref.current.controls = [
                search_input,
                self._build_filter_chip("Todos"),
                self._build_filter_chip("Activos"),
                self._build_filter_chip("Vencidos")
            ]
            self.search_row_ref.current.update()

            # 3. Filtramos los datos de la tabla de socios
            self._update_table()

        return ft.Container(
            content=ft.Text(
                label,
                color=Colors.ACCENT if is_active else Colors.TEXT_SECONDARY,
                size=13,
                weight=ft.FontWeight.W_600 if is_active else ft.FontWeight.NORMAL
            ),
            bgcolor=Colors.ACCENT_GLOW if is_active else Colors.BG_INPUT,
            border_radius=20,
            padding=ft.Padding.symmetric(horizontal=14, vertical=8),
            border=ft.Border.all(1, Colors.ACCENT if is_active else Colors.BORDER),
            on_click=on_chip_click, # <-- ACÁ ESTÁ LA MAGIA, ahora responde al click
            
        )

    def _update_table(self):
        """
        Lógica central: filtra por texto, filtra por estado y ordena alfabéticamente.
        """
        # 1. Obtener datos y query de búsqueda
        query = self.search_ref.current.value.lower() if self.search_ref.current else ""
        socios = app_state.get_socios()

        # 2. Aplicar filtros (Búsqueda + Estado)
        filtered = []
        for s in socios:
            matches_search = query in s["nombre"].lower() or query in s["plan"].lower()
            
            matches_status = False
            if self.current_filter == "Todos":
                matches_status = True
            elif self.current_filter == "Activos" and s["estado"].lower() == "activo":
                matches_status = True
            elif self.current_filter == "Vencidos" and s["estado"].lower() == "vencido":
                matches_status = True

            if matches_search and matches_status:
                filtered.append(s)

        # 3. Aplicar Ordenamiento (Aquí usamos la variable que creamos en el init)
        # sort_ascending es True (A-Z) o False (Z-A)
        filtered.sort(key=lambda x: x["nombre"].lower(), reverse=not self.sort_ascending)

        # 4. Actualizar la interfaz
        self.table_ref.current.controls = [self._build_table(filtered)]
        self.table_ref.current.update()

    def _on_search(self, e):
        """Callback de búsqueda en tiempo real (keystroke). Redirige al filtro central."""
        self._update_table()

    def _toggle_sort(self, e):
        # Alternar el sentido del orden
        self.sort_ascending = not self.sort_ascending
        
        # Refrescar la tabla aplicando el nuevo orden
        self._update_table()

    def _build_table(self, socios: list) -> ft.Column:
        header = ft.Container(
            content=ft.Row([
                
                ft.TextButton(
                    content=ft.Row([
                        ft.Text("Nombre", color=Colors.SUCCESS, size=12, weight=ft.FontWeight.W_600),
                        ft.Icon(ft.Icons.SORT, size=14, color=Colors.SUCCESS)
                    ]),
                    on_click=self._toggle_sort, 
                    expand=3,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5))
                ),
                ft.Text("Plan",    color=Colors.SUCCESS, size=12, weight=ft.FontWeight.W_600, expand=2),
                ft.Text("Estado",  color=Colors.SUCCESS, size=12, weight=ft.FontWeight.W_600, expand=2),
                ft.Text("Vence",   color=Colors.SUCCESS, size=12, weight=ft.FontWeight.W_600, expand=2),
                # expand=3 y no 2 como el resto: acá entran hasta cuatro
                # botones y con 2 el último quedaba cortado.
                ft.Text("Acciones", color=Colors.SUCCESS, size=12, weight=ft.FontWeight.W_600, expand=3),
            ]),
            padding=ft.Padding.symmetric(horizontal=20, vertical=14),
            bgcolor=Colors.BG_SIDEBAR,
        )
        

        rows = [header]
        for s in socios:
            rows.append(self._table_row(s))

        return ft.Column(rows, spacing=0)

    def _table_row(self, s: dict) -> ft.Container:
        """Construye una fila de la tabla para un socio específico."""
        initial = s["nombre"][0].upper()

        def on_hover(e: ft.HoverEvent):
            e.control.bgcolor = Colors.BG_INPUT if e.data == "true" else ft.Colors.TRANSPARENT
            e.control.update()

        return ft.Container(
            content=ft.Row([
                ft.Row([
                    ft.Container(
                        content=ft.Text(initial, color=Colors.SURFACE_BASE, size=13, weight=ft.FontWeight.BOLD),
                        width=32, height=32, border_radius=16,
                        bgcolor=Colors.ACCENT, alignment=ft.Alignment.CENTER,
                    ),
                    ft.Text(s["nombre"], color=Colors.TEXT_PRIMARY, size=14),
                ], spacing=10, expand=3),
                ft.Container(content=ft.Text(s["plan"], color=Colors.TEXT_SECONDARY, size=13), expand=2),
                ft.Container(content=status_badge(s["estado"]), expand=2, alignment=ft.Alignment.CENTER_LEFT),
                ft.Text(s["vence"], color=Colors.TEXT_SECONDARY, size=13, expand=2),
                ft.Row([
                    # Editar exige acceso TOTAL a la sección (SocioTableRow.tsx).
                    *([ft.IconButton(ft.Icons.EDIT_ROUNDED, icon_color=Colors.INFO, icon_size=18,
                                     tooltip="Editar",
                                     on_click=lambda e, x=s: self._open_form(e, x))]
                      if app_state.puede_editar(Routes.SOCIOS) else []),
                    ft.IconButton(ft.Icons.FITNESS_CENTER_ROUNDED, icon_color=Colors.PRIMARY_VOLT,
                                  icon_size=18, tooltip="Entrenadores a cargo",
                                  on_click=lambda e, x=s: self._entrenadores(x)),
                    # El botón se OMITE, no se deshabilita, para quien no tenga
                    # la acción. Un botón gris que no responde igual delata que
                    # el socio tiene algo cargado, y el punto de que el
                    # Recepcionista no vea esto es que no se entere.
                    *([ft.IconButton(
                        ft.Icons.MEDICAL_INFORMATION_ROUNDED, icon_color=Colors.INFO,
                        icon_size=18, tooltip="Historial médico",
                        on_click=lambda e, x=s: self._patologias(x),
                    )] if app_state.puede(Accion.VER_HISTORIAL_MEDICO) else []),
                    # Baja o reactivación según cómo esté. El botón de "eliminar"
                    # que había acá prometía algo que el sistema no hace: la baja
                    # es LÓGICA —la fila queda, con su historial de pagos y
                    # asistencias— y se puede deshacer. Un socio dado de baja
                    # muestra el botón de volver a activarlo, no uno de borrar.
                    # Sólo con la acción altaBajaSocios.
                    *([ft.IconButton(ft.Icons.PERSON_OFF_ROUNDED, icon_color=Colors.DANGER,
                                     icon_size=18, tooltip="Dar de baja",
                                     on_click=lambda e, x=s: self._confirmar_baja(x))
                       if s["estado"] != "Dado de baja" else
                       ft.IconButton(ft.Icons.PERSON_ADD_ALT_1_ROUNDED, icon_color=Colors.SUCCESS,
                                     icon_size=18, tooltip="Reactivar",
                                     on_click=lambda e, x=s: self._reactivar(x))]
                      if app_state.puede(Accion.ALTA_BAJA_SOCIOS) else []),
                ], expand=3),
            ]),
            padding=ft.Padding.symmetric(horizontal=20, vertical=12),
            border=ft.Border.only(bottom=ft.BorderSide(1, Colors.BORDER)),
            on_hover=on_hover,
            animate=ft.Animation(120),
        )

    def _open_form(self, e=None, socio: dict = None):
        """
        Abre el modal para crear o editar un socio.

        Dos cambios respecto de la versión con datos de prueba:

        1. Nombre y apellido van SEPARADOS. Persona los guarda en dos columnas
           y el "nombre completo" de un solo campo no se puede partir de forma
           confiable — "Juan Carlos De la Fuente" no se resuelve con un split.

        2. Se fue el selector de "Plan". El plan no es un dato del socio: es
           una Membresía, que se crea cobrándola. Elegirlo en el alta daba a
           entender que el socio quedaba con plan asignado sin haber pagado
           nada, y no quedaba: el alta no tocaba ninguna membresía. En su
           lugar va "Objetivo", que sí es una columna de Socio.
        """
        is_edit = socio is not None

        nombre_ref   = ft.Ref[ft.TextField]()
        apellido_ref = ft.Ref[ft.TextField]()
        dni_ref      = ft.Ref[ft.TextField]()
        email_ref    = ft.Ref[ft.TextField]()
        telefono_ref = ft.Ref[ft.TextField]()
        objetivo_ref = ft.Ref[ft.TextField]()
        obs_ref      = ft.Ref[ft.TextField]()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Editar Socio" if is_edit else "Nuevo Socio",
                          color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=420,
                height=400,
                content=ft.Column([
                    input_field("Nombre", "Ej: Juan", ref=nombre_ref,
                                icon=ft.Icons.PERSON_OUTLINE_ROUNDED,
                                value=socio["nombre_pila"] if is_edit else ""),
                    ft.Container(height=12),
                    input_field("Apellido", "Ej: García", ref=apellido_ref,
                                icon=ft.Icons.PERSON_OUTLINE_ROUNDED,
                                value=socio["apellido"] if is_edit else ""),
                    ft.Container(height=12),
                    # En edición el DNI se muestra pero no se manda: cambiarlo
                    # sería decir que es otra persona, y el backend directamente
                    # no lo acepta en el PUT.
                    input_field("DNI", "Ej: 30123456", ref=dni_ref,
                                icon=ft.Icons.BADGE_OUTLINED,
                                value=socio["dni"] if is_edit else ""),
                    ft.Container(height=12),
                    input_field("Email", "ejemplo@mail.com", ref=email_ref,
                                icon=ft.Icons.EMAIL_OUTLINED,
                                value=socio["email"] if is_edit else ""),
                    ft.Container(height=12),
                    input_field("Teléfono", "Ej: 3415551234", ref=telefono_ref,
                                icon=ft.Icons.PHONE_OUTLINED,
                                value=socio["telefono"] if is_edit else ""),
                    ft.Container(height=12),
                    input_field("Objetivo", "Ej: Bajar de peso", ref=objetivo_ref,
                                icon=ft.Icons.FLAG_OUTLINED,
                                value=socio["objetivo"] if is_edit else ""),
                    ft.Container(height=12),
                    input_field("Observaciones", "Lesiones, restricciones...",
                                ref=obs_ref, multiline=True,
                                value=socio["observaciones"] if is_edit else ""),
                ], spacing=0, tight=True, scroll=ft.ScrollMode.AUTO),
            ),
            actions=[
                ft.TextButton("Cancelar",
                              style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                              on_click=lambda e: close_dialog(self.page, dlg)),
                ft.TextButton("Guardar",
                              style=ft.ButtonStyle(color=Colors.ACCENT),
                              on_click=lambda e: self._save_socio(
                                  dlg,
                                  socio["id"] if is_edit else None,
                                  {"nombre": nombre_ref, "apellido": apellido_ref,
                                   "dni": dni_ref, "email": email_ref,
                                   "telefono": telefono_ref,
                                   "objetivo": objetivo_ref, "observaciones": obs_ref},
                              )),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        open_dialog(self.page, dlg)

    @staticmethod
    def _texto(ref) -> str:
        """Lee un campo aunque todavía no esté montado, sin reventar."""
        return (ref.current.value or "").strip() if ref.current else ""

    def _save_socio(self, dlg, id_socio, refs):
        datos = {campo: self._texto(ref) for campo, ref in refs.items()}

        faltan = [c for c in ("nombre", "apellido") if not datos[c]]
        if id_socio is None and not datos["dni"]:
            faltan.append("dni")
        if faltan:
            show_snack(self.page, "Falta completar: " + ", ".join(faltan),
                       Colors.STATUS_DANGER)
            return

        # Los opcionales van como None y no como "": el backend valida el mail
        # con EmailStr y una cadena vacía no es un mail válido — mandarla haría
        # fallar el alta de alguien que simplemente no dejó mail.
        cuerpo = {
            "nombre": datos["nombre"],
            "apellido": datos["apellido"],
            "email": datos["email"] or None,
            "telefono": datos["telefono"] or None,
            "objetivo": datos["objetivo"] or None,
            "observaciones": datos["observaciones"] or None,
        }

        if id_socio is None:
            cuerpo["dni"] = datos["dni"]
            # id_sede clavado en 1 igual que en la PWA (sociosService.ts): el
            # gimnasio tiene una sola sede y no hay endpoint que las liste.
            cuerpo["id_sede"] = 1
            cuerpo["crear_cuenta"] = True
            resultado = app_state.alta_socio(cuerpo)
        else:
            resultado = app_state.editar_socio(id_socio, cuerpo)

        if not resultado["ok"]:
            show_snack(self.page, resultado["mensaje"], Colors.STATUS_DANGER)
            return

        close_dialog(self.page, dlg)

        if id_socio is None and resultado.get("password_temporal"):
            self._mostrar_credenciales(resultado)
        else:
            show_snack(self.page, resultado["mensaje"], Colors.SUCCESS)

        self.router.navigate(Routes.SOCIOS)

    def _mostrar_credenciales(self, resultado: dict):
        """
        Muestra el número de socio y las credenciales del alta.

        Diálogo y no snack: la contraseña temporal es la única vez que existe
        legible —en la base queda el hash— y un snack se va solo antes de que
        alguien alcance a copiarla.

        `texto_credenciales` viene armado por el backend para mandar por
        WhatsApp cuando el mail no salió, que es la alternativa que contempla
        la consigna.
        """
        texto = resultado.get("texto_credenciales")
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Socio dado de alta",
                          color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=400,
                content=ft.Column([
                    ft.Text(resultado.get("mensaje", ""),
                            color=Colors.TEXT_SECONDARY, size=13),
                    ft.Container(height=12),
                    ft.Text(f"N° de socio: {resultado.get('numero_socio', '—')}",
                            color=Colors.TEXT_PRIMARY, size=13,
                            weight=ft.FontWeight.W_500, selectable=True),
                    ft.Container(height=8),
                    ft.Text(f"Usuario: {resultado.get('usuario', '—')}",
                            color=Colors.TEXT_PRIMARY, size=14,
                            weight=ft.FontWeight.BOLD, selectable=True),
                    ft.Text(f"Contraseña temporal: {resultado.get('password_temporal', '—')}",
                            color=Colors.PRIMARY_VOLT, size=14,
                            weight=ft.FontWeight.BOLD, selectable=True),
                    ft.Container(height=12),
                    ft.Text("Anotala ahora: no se puede volver a ver. "
                            "Se la va a pedir cambiar al entrar por primera vez.",
                            color=Colors.STATUS_WARN, size=12),
                    *([ft.Container(height=12),
                       ft.Text("Mensaje para enviar:", color=Colors.TEXT_MUTED, size=12),
                       ft.Container(
                           content=ft.Text(texto, color=Colors.TEXT_SECONDARY,
                                           size=12, selectable=True),
                           bgcolor=Colors.BG_INPUT,
                           border_radius=8,
                           padding=ft.Padding.all(10),
                       )] if texto else []),
                ], spacing=0, tight=True, scroll=ft.ScrollMode.AUTO),
                height=340,
            ),
            actions=[
                ft.TextButton("Listo",
                              style=ft.ButtonStyle(color=Colors.ACCENT),
                              on_click=lambda e: close_dialog(self.page, dlg)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(self.page, dlg)

    def _confirmar_baja(self, socio: dict):
        """
        Da de baja al socio. Pide el tipo porque no todas las bajas son
        iguales: la voluntaria la pide el socio, la de mora la decide el
        gimnasio, y la administrativa cubre el resto. El backend guarda el
        motivo en la tabla Baja, así que elegir mal deja mal el historial.
        """
        tipo_ref   = ft.Ref[ft.Dropdown]()
        motivo_ref = ft.Ref[ft.TextField]()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Dar de baja",
                          color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=400,
                content=ft.Column([
                    ft.Text(f"Se va a dar de baja a {socio['nombre']}.",
                            color=Colors.TEXT_SECONDARY, size=13),
                    ft.Container(height=8),
                    ft.Text("La ficha NO se borra: queda su historial de pagos y "
                            "asistencias, y se puede reactivar. Se cancela la "
                            "membresía vigente y se desactiva su cuenta.",
                            color=Colors.TEXT_MUTED, size=12),
                    ft.Container(height=14),
                    ft.Dropdown(
                        ref=tipo_ref,
                        label="Tipo de baja",
                        options=[
                            ft.dropdown.Option(key="VOLUNTARIA", text="Voluntaria"),
                            ft.dropdown.Option(key="MORA", text="Por mora"),
                            ft.dropdown.Option(key="ADMINISTRATIVA", text="Administrativa"),
                        ],
                        value="VOLUNTARIA",
                        color=Colors.TEXT_PRIMARY, bgcolor=Colors.BG_INPUT,
                        border_color=Colors.BORDER, focused_border_color=Colors.ACCENT,
                        border_radius=10,
                    ),
                    ft.Container(height=12),
                    input_field("Motivo (opcional)", "Ej: se mudó de ciudad",
                                ref=motivo_ref, multiline=True),
                ], spacing=0, tight=True),
            ),
            actions=[
                ft.TextButton("Cancelar",
                              style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                              on_click=lambda e: close_dialog(self.page, dlg)),
                ft.TextButton("Dar de baja",
                              style=ft.ButtonStyle(color=Colors.DANGER),
                              on_click=lambda e: self._ejecutar_baja(
                                  dlg, socio, tipo_ref, motivo_ref)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(self.page, dlg)

    def _ejecutar_baja(self, dlg, socio, tipo_ref, motivo_ref):
        resultado = app_state.dar_de_baja_socio(
            socio["id"],
            tipo_ref.current.value if tipo_ref.current else "VOLUNTARIA",
            self._texto(motivo_ref) or None,
        )
        if not resultado["ok"]:
            show_snack(self.page, resultado["mensaje"], Colors.STATUS_DANGER)
            return
        close_dialog(self.page, dlg)
        show_snack(self.page, resultado["mensaje"], Colors.SUCCESS)
        self.router.navigate(Routes.SOCIOS)

    def _reactivar(self, socio: dict):
        resultado = app_state.reactivar_socio(socio["id"])
        show_snack(self.page, resultado["mensaje"],
                   Colors.SUCCESS if resultado["ok"] else Colors.STATUS_DANGER)
        if resultado["ok"]:
            self.router.navigate(Routes.SOCIOS)


    # ── Entrenadores a cargo ──────────────────────────────────────────────────

    def _entrenadores(self, socio: dict):
        """
        Quién entrena a este socio.

        Se permiten VARIOS a la vez, y por eso el diálogo es una lista con un
        selector abajo y no un simple desplegable: un socio con uno de
        musculación y otro de funcional es normal, no un error de datos. Es la
        diferencia deliberada con las rutinas y las dietas, que admiten una
        sola activa.

        Se muestran también las FINALIZADAS, en gris. Ese historial es el
        motivo por el que esto es una tabla y no la columna que había antes:
        reasignar borraba al anterior y nadie podía responder quién lo
        entrenaba en marzo.
        """
        asignaciones = app_state.get_entrenadores_de_socio(socio["id"])

        # Asignar y finalizar sólo el Dueño y el Recepcionista. El Entrenador
        # tiene gestionRutinas pero quién entrena a quién no lo decide él: ve
        # la lista sin controles. Espejo de SociosView.tsx.
        roles = app_state.get_user_roles()
        puede_gestionar = (app_state.puede(Accion.GESTION_RUTINAS)
                           and ("dueno" in roles or "recepcionista" in roles))
        disponibles = app_state.get_entrenadores() if puede_gestionar else []

        # Los que ya están a cargo no se vuelven a ofrecer: el backend lo
        # rechaza con un 409 y hacerle elegir algo que va a fallar es hacerle
        # perder el tiempo.
        activos = {a["id_entrenador"] for a in asignaciones if a["activa"]}
        elegibles = [e for e in disponibles if e["id"] not in activos]

        sel_ref = ft.Ref[ft.Dropdown]()

        def asignar(e=None):
            if not sel_ref.current or not sel_ref.current.value:
                return
            self._resolver_dialogo(
                app_state.asignar_entrenador(socio["id"], int(sel_ref.current.value)),
                dlg, socio)

        def finalizar(id_asignacion):
            self._resolver_dialogo(
                app_state.finalizar_entrenador(id_asignacion), dlg, socio)

        filas = []
        for a in asignaciones:
            color = Colors.TEXT_PRIMARY if a["activa"] else Colors.TEXT_MUTED
            periodo = f"desde {a['desde']}" if a["activa"] else f"{a['desde']} — {a['hasta']}"
            filas.append(ft.Row([
                ft.Icon(ft.Icons.FITNESS_CENTER_ROUNDED,
                        color=Colors.PRIMARY_VOLT if a["activa"] else Colors.TEXT_MUTED,
                        size=16),
                ft.Column([
                    ft.Text(a["entrenador"], color=color, size=13),
                    ft.Text(f"{a['especialidad']} · {periodo}",
                            color=Colors.TEXT_MUTED, size=11),
                ], spacing=0, tight=True, expand=True),
                *([ft.IconButton(
                    ft.Icons.CLOSE_ROUNDED, icon_color=Colors.TEXT_MUTED, icon_size=16,
                    tooltip="Terminar la relación (queda en el historial)",
                    on_click=lambda e, i=a["id"]: finalizar(i),
                )] if a["activa"] and puede_gestionar else [] if a["activa"] else [
                    ft.Text("finalizada", color=Colors.TEXT_MUTED, size=11)
                ]),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER))

        if not asignaciones:
            filas.append(ft.Text("Todavía no tiene ningún entrenador asignado.",
                                 color=Colors.TEXT_MUTED, size=12))

        contenido = [
            ft.Text("Puede tener más de uno a la vez —por ejemplo, uno de "
                    "musculación y otro de funcional—.",
                    color=Colors.TEXT_MUTED, size=11),
            ft.Container(height=12),
            *filas,
            ft.Container(height=12),
        ]

        if not puede_gestionar:
            pass
        elif elegibles:
            contenido += [
                ft.Divider(height=1, color=Colors.BORDER),
                ft.Container(height=12),
                ft.Row([
                    ft.Container(
                        content=ft.Dropdown(
                            ref=sel_ref, label="Asignar entrenador",
                            options=[ft.dropdown.Option(key=str(x["id"]), text=x["nombre"])
                                     for x in elegibles],
                            value=str(elegibles[0]["id"]),
                            color=Colors.TEXT_PRIMARY, bgcolor=Colors.BG_INPUT,
                            border_color=Colors.BORDER,
                            focused_border_color=Colors.ACCENT,
                            border_radius=Radius.MD,
                        ),
                        expand=True,
                    ),
                    ft.Container(width=8),
                    ft.TextButton("Asignar",
                                  style=ft.ButtonStyle(color=Colors.ACCENT),
                                  on_click=asignar),
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ]
        elif disponibles:
            contenido.append(ft.Text("Ya tiene a cargo a todos los entrenadores "
                                     "disponibles.", color=Colors.TEXT_MUTED, size=11))
        else:
            contenido.append(ft.Text("No hay entrenadores activos cargados.",
                                     color=Colors.STATUS_WARN, size=11))

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Entrenadores de {socio['nombre']}",
                          color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=440,
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

    def _resolver_dialogo(self, resultado: dict, dlg, socio: dict):
        """
        Muestra el resultado y VUELVE A ABRIR el diálogo con los datos frescos.

        Reabrirlo en vez de cerrarlo es deliberado: asignar entrenadores es una
        tarea que se hace de a varios —se le ponen dos, se le saca uno— y
        cerrar la ventana en cada paso obligaría a volver a buscar al socio en
        la grilla cada vez.
        """
        if not resultado["ok"]:
            show_snack(self.page, resultado["mensaje"], Colors.STATUS_DANGER)
            return
        close_dialog(self.page, dlg)
        show_snack(self.page, resultado["mensaje"], Colors.SUCCESS)
        self._entrenadores(socio)

    # ── Historial médico ──────────────────────────────────────────────────────
    #
    # Esta pantalla no la ve todo el que llega a Socios. El Recepcionista entra
    # a la sección con acceso TOTAL y aun así no tiene VER_HISTORIAL_MEDICO,
    # así que el botón que abre esto ni siquiera se dibuja para él. El guard de
    # verdad está en el backend; el de acá es para no ofrecer algo que va a
    # volver 403.

    def _patologias(self, socio: dict):
        """
        Las condiciones de salud del socio.

        Por qué un catálogo y no el campo "Observaciones" que ya tiene la ficha:
        aquel es texto libre y sirve para una nota suelta, pero "asma, rodilla
        operada, hipertensión" escrito en una celda no se puede filtrar ni
        contar, y cada quien lo escribe distinto. Con el catálogo, "qué socios
        tienen asma" es una consulta. Los dos campos conviven a propósito.

        Las observaciones de CADA condición son lo que de verdad le sirve al
        entrenador y el catálogo no puede saber: "rodilla derecha", "controlada
        con medicación", "evitar impacto". El nombre dice QUÉ tiene; esto dice
        qué hacer al respecto.
        """
        registradas = app_state.get_patologias_de_socio(socio["id"])
        catalogo = app_state.get_catalogo_patologias()

        # Las que ya tiene no se vuelven a ofrecer: el backend responde 409 y
        # hacerle elegir algo que va a fallar es hacerle perder el tiempo.
        # Mismo criterio que en el diálogo de entrenadores.
        ya_tiene = {p["id"] for p in registradas}
        elegibles = [c for c in catalogo if c["id"] not in ya_tiene]

        sel_ref   = ft.Ref[ft.Dropdown]()
        fecha_ref = ft.Ref[ft.TextField]()
        obs_ref   = ft.Ref[ft.TextField]()

        def agregar(e=None):
            if not sel_ref.current or not sel_ref.current.value:
                return
            fecha = self._fecha_iso(self._texto(fecha_ref))
            if fecha is False:
                show_snack(self.page, "La fecha va como dd/mm/aaaa.",
                           Colors.STATUS_DANGER)
                return
            self._resolver_patologias(
                app_state.asignar_patologia(socio["id"], int(sel_ref.current.value),
                                             fecha, self._texto(obs_ref)),
                dlg, socio)

        filas = []
        for p in registradas:
            detalle = p["observaciones"] or p["descripcion"] or "sin observaciones"
            filas.append(ft.Row([
                ft.Icon(ft.Icons.MEDICAL_INFORMATION_ROUNDED,
                        color=Colors.INFO, size=16),
                ft.Column([
                    ft.Text(p["nombre"], color=Colors.TEXT_PRIMARY, size=13),
                    ft.Text(f"desde {p['desde']} · {detalle}",
                            color=Colors.TEXT_MUTED, size=11),
                ], spacing=0, tight=True, expand=True),
                ft.IconButton(
                    ft.Icons.EDIT_ROUNDED, icon_color=Colors.INFO, icon_size=16,
                    tooltip="Editar fecha y observaciones",
                    on_click=lambda e, x=p: self._editar_patologia(socio, x, dlg),
                ),
                ft.IconButton(
                    ft.Icons.CLOSE_ROUNDED, icon_color=Colors.TEXT_MUTED, icon_size=16,
                    tooltip="Quitarla de la ficha",
                    on_click=lambda e, i=p["id"]: self._resolver_patologias(
                        app_state.quitar_patologia(socio["id"], i), dlg, socio),
                ),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER))

        if not registradas:
            filas.append(ft.Text("No tiene ninguna condición registrada.",
                                 color=Colors.TEXT_MUTED, size=12))

        contenido = [
            ft.Text("Lo que hay que tener en cuenta al armarle una rutina o "
                    "una dieta.", color=Colors.TEXT_MUTED, size=11),
            ft.Container(height=12),
            *filas,
            ft.Container(height=12),
            ft.Divider(height=1, color=Colors.BORDER),
            ft.Container(height=12),
        ]

        if elegibles:
            contenido += [
                ft.Dropdown(
                    ref=sel_ref, label="Agregar condición",
                    options=[ft.dropdown.Option(key=str(c["id"]), text=c["nombre"])
                             for c in elegibles],
                    value=str(elegibles[0]["id"]),
                    color=Colors.TEXT_PRIMARY, bgcolor=Colors.BG_INPUT,
                    border_color=Colors.BORDER, focused_border_color=Colors.ACCENT,
                    border_radius=Radius.MD,
                ),
                ft.Container(height=10),
                input_field("Fecha de diagnóstico (opcional)", "dd/mm/aaaa",
                            ref=fecha_ref, icon=ft.Icons.CALENDAR_TODAY_OUTLINED),
                ft.Container(height=10),
                input_field("Observaciones (opcional)",
                            "Ej: rodilla derecha, evitar impacto",
                            ref=obs_ref, multiline=True),
                ft.Container(height=10),
                ft.Row([ft.TextButton("Agregar",
                                       style=ft.ButtonStyle(color=Colors.ACCENT),
                                       on_click=agregar)],
                       alignment=ft.MainAxisAlignment.END),
            ]
        elif catalogo:
            contenido.append(ft.Text("Ya tiene registradas todas las condiciones "
                                     "del catálogo.", color=Colors.TEXT_MUTED, size=11))
        else:
            # Sin esto la pantalla nace muerta: la base entregada viene con el
            # catálogo vacío, y sin una condición cargada no hay nada para
            # elegir ni forma de salir del paso desde acá.
            contenido.append(ft.Text("El catálogo está vacío. Cargá la primera "
                                     "condición con el botón de abajo.",
                                     color=Colors.STATUS_WARN, size=11))

        contenido += [
            ft.Container(height=8),
            ft.Row([
                ft.TextButton(
                    "¿No está en la lista? Agregarla al catálogo",
                    style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                    icon=ft.Icons.ADD_ROUNDED,
                    on_click=lambda e: self._nueva_del_catalogo(socio, dlg),
                ),
            ], alignment=ft.MainAxisAlignment.START),
        ]

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Historial médico de {socio['nombre']}",
                          color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=460,
                height=470,
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

    def _editar_patologia(self, socio: dict, patologia: dict, padre):
        """
        Cambia fecha y observaciones de una condición ya registrada.

        Existe en vez de "borrar y volver a cargar" porque las observaciones
        cambian más seguido que el diagnóstico —una lesión que mejora, una
        medicación que se ajusta— y rehacerla perdería la fecha original.
        """
        close_dialog(self.page, padre)

        fecha_ref = ft.Ref[ft.TextField]()
        obs_ref   = ft.Ref[ft.TextField]()

        def guardar(e=None):
            fecha = self._fecha_iso(self._texto(fecha_ref))
            if fecha is False:
                show_snack(self.page, "La fecha va como dd/mm/aaaa.",
                           Colors.STATUS_DANGER)
                return
            resultado = app_state.editar_patologia_de_socio(
                socio["id"], patologia["id"], fecha, self._texto(obs_ref))
            if not resultado["ok"]:
                show_snack(self.page, resultado["mensaje"], Colors.STATUS_DANGER)
                return
            close_dialog(self.page, dlg)
            show_snack(self.page, resultado["mensaje"], Colors.SUCCESS)
            self._patologias(socio)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(patologia["nombre"],
                          color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=420,
                content=ft.Column([
                    ft.Text("El nombre no se edita acá: sale del catálogo y "
                            "cambiarlo se lo cambiaría a todos los socios que "
                            "lo tengan.", color=Colors.TEXT_MUTED, size=11),
                    ft.Container(height=12),
                    input_field("Fecha de diagnóstico", "dd/mm/aaaa",
                                ref=fecha_ref, icon=ft.Icons.CALENDAR_TODAY_OUTLINED,
                                value=patologia["desde"] if patologia["fecha_iso"] else ""),
                    ft.Container(height=12),
                    input_field("Observaciones",
                                "Ej: rodilla derecha, evitar impacto",
                                ref=obs_ref, multiline=True,
                                value=patologia["observaciones"]),
                ], spacing=0, tight=True),
            ),
            actions=[
                ft.TextButton("Cancelar",
                              style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                              on_click=lambda e: self._volver_a_patologias(dlg, socio)),
                ft.TextButton("Guardar",
                              style=ft.ButtonStyle(color=Colors.ACCENT),
                              on_click=guardar),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(self.page, dlg)

    def _nueva_del_catalogo(self, socio: dict, padre):
        """
        Suma una condición al CATÁLOGO, no a la ficha del socio.

        Son dos pasos y no uno a propósito: el catálogo es compartido por todo
        el gimnasio, y dejar que se cargue al vuelo mientras se completa una
        ficha es exactamente cómo terminan conviviendo "Asma", "asma" y "ASMA"
        —que es lo que el catálogo venía a evitar—. El backend además compara
        sin distinguir mayúsculas y rechaza la repetida.
        """
        close_dialog(self.page, padre)

        nombre_ref = ft.Ref[ft.TextField]()
        desc_ref   = ft.Ref[ft.TextField]()

        def guardar(e=None):
            nombre = self._texto(nombre_ref)
            if len(nombre) < 2:
                show_snack(self.page, "El nombre de la condición es obligatorio.",
                           Colors.STATUS_DANGER)
                return
            resultado = app_state.crear_patologia(nombre, self._texto(desc_ref) or None)
            if not resultado["ok"]:
                show_snack(self.page, resultado["mensaje"], Colors.STATUS_DANGER)
                return
            close_dialog(self.page, dlg)
            show_snack(self.page, resultado["mensaje"], Colors.SUCCESS)
            # Se vuelve al historial del socio, que es de donde vino: ahora la
            # condición nueva aparece en el selector y se la puede asignar.
            self._patologias(socio)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Nueva condición del catálogo",
                          color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=420,
                content=ft.Column([
                    ft.Text("Queda disponible para todos los socios, no sólo "
                            "para este.", color=Colors.TEXT_MUTED, size=11),
                    ft.Container(height=12),
                    input_field("Nombre", "Ej: Asma", ref=nombre_ref,
                                icon=ft.Icons.MEDICAL_INFORMATION_OUTLINED),
                    ft.Container(height=12),
                    input_field("Descripción (opcional)",
                                "Qué implica para el entrenamiento",
                                ref=desc_ref, multiline=True),
                ], spacing=0, tight=True),
            ),
            actions=[
                ft.TextButton("Cancelar",
                              style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                              on_click=lambda e: self._volver_a_patologias(dlg, socio)),
                ft.TextButton("Guardar",
                              style=ft.ButtonStyle(color=Colors.ACCENT),
                              on_click=guardar),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(self.page, dlg)

    def _volver_a_patologias(self, dlg, socio: dict):
        """Cancelar en un sub-diálogo devuelve al historial, no a la grilla."""
        close_dialog(self.page, dlg)
        self._patologias(socio)

    def _resolver_patologias(self, resultado: dict, dlg, socio: dict):
        """
        Igual que `_resolver_dialogo` pero reabriendo el historial médico.

        Se reabre en vez de cerrar por el mismo motivo que en entrenadores:
        cargar condiciones es una tarea de a varias —se agregan dos, se corrige
        una— y cerrar en cada paso obligaría a buscar al socio en la grilla
        cada vez.
        """
        if not resultado["ok"]:
            show_snack(self.page, resultado["mensaje"], Colors.STATUS_DANGER)
            return
        close_dialog(self.page, dlg)
        show_snack(self.page, resultado["mensaje"], Colors.SUCCESS)
        self._patologias(socio)

    @staticmethod
    def _fecha_iso(texto: str):
        """
        'dd/mm/aaaa' -> 'aaaa-mm-dd' para mandarle al backend. Vacío -> None.
        Devuelve False si no se entiende, para poder distinguir "no puso fecha"
        de "puso cualquier cosa" — con None para los dos casos, un error de
        tipeo se guardaría en silencio como si no hubiera escrito nada.

        Se parsea acá y no se usa un DatePicker porque la fecha de diagnóstico
        suele ser vieja e imprecisa ("fue en 2019"), y elegirla en un
        calendario obliga a navegar años hacia atrás para un dato opcional.
        """
        texto = (texto or "").strip()
        if not texto:
            return None
        try:
            dia, mes, anio = texto.split("/")
            return f"{int(anio):04d}-{int(mes):02d}-{int(dia):02d}"
        except (ValueError, AttributeError):
            return False
