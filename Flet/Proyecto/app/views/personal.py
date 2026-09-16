# =============================================================================
# views/personal.py — Gestión del personal del gimnasio
# =============================================================================
# Esta vista muestra el equipo de empleados en formato de tarjetas (cards).
# Cada card incluye: avatar, nombre, rol, turno y botones de acción.
# Permite agregar nuevos empleados o editar los existentes mediante un modal.

import flet as ft
from app.config import Colors, Routes, alpha
from app.permisos import Accion
from app.state import app_state
from app.components.ui import (build_topbar, confirm_dialog, status_badge, primary_button,
                                input_field, show_snack, open_dialog, close_dialog)
from app.contacto import limpiar_telefono, link_mail, link_whatsapp

# Asunto del mail de credenciales. Igual que en EmpleadoFormModal.tsx.
ASUNTO_CREDENCIALES = "Tus datos de acceso a OlimpOS"

# Mapa turno → (color de texto, color de fondo translúcido)
#
# Mismos tres colores que StaffCard.tsx de la PWA. Kinetic Carbon no tiene azul
# ni violeta —eran de la paleta anterior—, así que Tarde y Noche usan los dos
# acentos que sí existen. El fondo se deriva del color con alpha() para que
# nunca vuelva a quedar un texto de un color sobre un fondo de otro.
TURNO_COLORS = {
    "Mañana": (Colors.STATUS_WARN,   alpha(Colors.STATUS_WARN, 0.12)),   # Amarillo
    "Tarde":  (Colors.ACCENT_CORAL,  alpha(Colors.ACCENT_CORAL, 0.12)),  # Coral
    "Noche":  (Colors.PRIMARY_VOLT,  alpha(Colors.PRIMARY_VOLT, 0.12)),  # Volt
}


# Mapa rol → ícono de Material Design correspondiente
# Los cuatro roles de empleado que acepta el backend (RolEmpleado en
# schemas.py). "Administrativo" que figuraba antes en el Dropdown no existe
# como tabla: elegirlo hacía fallar el alta con un 422 sin explicación.
# Profesor sí existe pero NO usa el sistema — da clases y no tiene cuenta.
ROLES_EMPLEADO = ["Entrenador", "Nutricionista", "Recepcionista", "Profesor"]


ROL_ICONS = {
    "Entrenador":    ft.Icons.FITNESS_CENTER_ROUNDED,
    #"Entrenadora":   ft.Icons.FITNESS_CENTER_ROUNDED,
    "Nutricionista": ft.Icons.RESTAURANT_MENU_ROUNDED,
    "Recepcionista": ft.Icons.SUPPORT_AGENT_ROUNDED,
    "Profesor":      ft.Icons.SPORTS_ROUNDED,
}


class PersonalView:
    def __init__(self, page: ft.Page, router):
        self.page   = page
        self.router = router
        # Espejo de PersonalView.tsx: el Recepcionista tiene la sección en
        # LECTURA — ve a todos (necesita saber quién trabaja hoy) pero no
        # edita ni da de alta/baja. Eso es del Dueño.
        self.puede_editar = app_state.puede_editar(Routes.PERSONAL)
        self.puede_alta_baja = app_state.puede(Accion.ALTA_BAJA_PERSONAL)

    def build(self) -> ft.Column:
        """Construye la vista con topbar y grilla de tarjetas de personal."""
        personal = app_state.get_personal()  # Lista de empleados del estado global

        topbar = build_topbar(
            "Personal",
            f"{len(personal)} empleados activos",
            actions=[
                primary_button("Agregar Empleado", ft.Icons.BADGE_ROUNDED,
                               on_click=self._open_form),
            ] if self.puede_alta_baja else []
        )

        # ResponsiveRow adapta la cantidad de columnas al ancho de la ventana:
        # xs (mobile): 1 columna, sm (tablet): 2 columnas, md: 3, lg: 4
        cards = ft.ResponsiveRow(
            [self._staff_card(p) for p in personal],
            spacing=16, run_spacing=16,
        )

        body = ft.Column([
            topbar,
            ft.Container(
                content=ft.Column([cards], spacing=0,
                                  scroll=ft.ScrollMode.AUTO, expand=True),
                padding=ft.Padding.all(24),
                expand=True,
            ),
        ], spacing=0, expand=True)

        return body

    def _staff_card(self, p: dict) -> ft.Container:
        """
        Construye la tarjeta de un empleado individual.
        Layout vertical: avatar + estado | nombre | rol | chip de turno | acciones
        """
        initial   = p["nombre"][0].upper()  # Inicial para el avatar
        turno_c, turno_bg = TURNO_COLORS.get(p["turno"], (Colors.TEXT_SECONDARY, Colors.BG_INPUT))
        rol_icon  = ROL_ICONS.get(p["rol"], ft.Icons.PERSON_ROUNDED)

        # Regla de FILA: nadie se da de baja a sí mismo aunque tenga el permiso
        # (se dejaría afuera de un click). Misma regla que PersonalView.tsx.
        puede_baja = (self.puede_alta_baja
                      and p.get("id_persona") != app_state.get_user_id_persona())
        estado_accion = []
        if puede_baja:
            estado_accion.append(ft.IconButton(
                ft.Icons.PERSON_OFF_ROUNDED if p["activo"] else ft.Icons.RESTART_ALT_ROUNDED,
                icon_color=Colors.TEXT_MUTED, icon_size=16,
                tooltip="Dar de baja" if p["activo"] else "Reactivar",
                on_click=lambda e, x=p: self._cambiar_estado(x),
            ))

        # "Contactar" abre el mail o, si la persona sólo dejó teléfono, el
        # WhatsApp. El mail gana cuando están los dos: queda guardado y
        # buscable, mientras que un WhatsApp se pierde en la conversación.
        # Misma regla que StaffCard.tsx.
        #
        # Desde que el alta exige una de las dos vías, un empleado nuevo
        # siempre tiene a dónde; el estado apagado queda para las fichas
        # viejas, y es la señal de que a esa persona hay que completarle el
        # contacto.
        email    = p.get("email") or ""
        telefono = p.get("telefono") or ""
        if email:
            destino, icono, tip = (link_mail(email), ft.Icons.EMAIL_OUTLINED,
                                   f"Escribir a {email}")
        elif telefono:
            destino, icono, tip = (link_whatsapp(telefono), ft.Icons.CHAT_OUTLINED,
                                   f"WhatsApp a {telefono}")
        else:
            destino, icono, tip = (None, ft.Icons.EMAIL_OUTLINED,
                                   "Sin email ni teléfono cargados")

        contactar = ft.Container(
            content=ft.Row([
                ft.Icon(icono, color=Colors.TEXT_SECONDARY, size=14),
                ft.Text("Contactar", color=Colors.TEXT_SECONDARY, size=12),
            ], spacing=4),
            bgcolor=Colors.BG_SIDEBAR, border_radius=8,
            padding=ft.Padding.symmetric(horizontal=10, vertical=6),
            on_click=(lambda e, u=destino: self.page.launch_url(u)) if destino else None,
            tooltip=tip,
            opacity=1 if destino else 0.4,
        )

        return ft.Container(
            # col define el ancho responsivo de la tarjeta en el ResponsiveRow
            col={"xs": 12, "sm": 6, "md": 4, "lg": 3},
            content=ft.Column([
                # Fila superior: avatar + badge de estado
                ft.Row([
                    ft.Container(
                        content=ft.Text(initial, color=Colors.SURFACE_BASE, size=20,
                                        weight=ft.FontWeight.BOLD),
                        width=52, height=52, border_radius=26,
                        bgcolor=Colors.ACCENT, alignment=ft.Alignment.CENTER,
                    ),
                    ft.Container(expand=True),
                    status_badge(p["estado"]),  # Badge Activo/Inactivo
                    *estado_accion,
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Container(height=12),
                # Nombre del empleado
                ft.Text(p["nombre"], color=Colors.TEXT_PRIMARY, size=15,
                        weight=ft.FontWeight.BOLD),
                # Rol con ícono correspondiente
                ft.Row([
                    ft.Icon(rol_icon, color=Colors.TEXT_SECONDARY, size=14),
                    ft.Text(p["rol"], color=Colors.TEXT_SECONDARY, size=13),
                ], spacing=4),
                ft.Container(height=12),
                # Chip de turno coloreado según horario (Mañana/Tarde/Noche)
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.SCHEDULE_ROUNDED, color=turno_c, size=14),
                        ft.Text(f"Turno {p['turno']}", color=turno_c, size=12,
                                weight=ft.FontWeight.W_500),
                    ], spacing=6),
                    bgcolor=turno_bg,
                    border_radius=20,
                    padding=ft.Padding.symmetric(horizontal=10, vertical=5),
                ),
                ft.Container(height=16),
                # Botones de acción: Editar (sólo con acceso TOTAL) y Contactar.
                # Con lectura queda únicamente Contactar: el Recepcionista
                # necesita poder escribirle a un compañero, no editarle la ficha.
                ft.Row([
                    *([ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.EDIT_ROUNDED, color=Colors.INFO, size=14),
                            ft.Text("Editar", color=Colors.INFO, size=12),
                        ], spacing=4),
                        # x=p captura la variable por valor en el lambda (evita closure bug)
                        on_click=lambda e, x=p: self._open_form(e, x),
                        bgcolor=alpha(Colors.PRIMARY_VOLT, 0.10), border_radius=8,
                        padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                    )] if self.puede_editar else []),
                    contactar,
                ], spacing=8),
            ], spacing=4),
            bgcolor=Colors.BG_CARD,
            border_radius=14,
            border=ft.Border.all(1, Colors.BORDER),
            padding=20,
        )

    def _open_form(self, e=None, empleado: dict = None):
        """
        Abre el modal de crear/editar empleado.

        El formulario pide más datos que antes porque el alta real crea TRES
        filas —Persona, Empleado y la tabla de su especialidad— y Persona no
        acepta una persona sin DNI ni apellido. El "nombre completo" de un
        solo campo que había acá no se podía partir en dos de forma confiable
        ("María de los Ángeles Del Valle" no se resuelve con un split), así
        que nombre y apellido van separados desde el formulario.

        Los campos de especialidad (título, matrícula, turno) se muestran
        todos y el backend ignora los que no apliquen al rol elegido. Es la
        misma decisión que está documentada en EmpleadoAltaRequest: un
        formulario que manda siempre los mismos campos es más simple —y
        rompe menos— que uno que se rearma solo cada vez que cambia un
        Dropdown.
        """
        is_edit = empleado is not None

        nombre_ref    = ft.Ref[ft.TextField]()
        apellido_ref  = ft.Ref[ft.TextField]()
        dni_ref       = ft.Ref[ft.TextField]()
        email_ref     = ft.Ref[ft.TextField]()
        telefono_ref  = ft.Ref[ft.TextField]()
        titulo_ref    = ft.Ref[ft.TextField]()
        matricula_ref = ft.Ref[ft.TextField]()
        rol_ref       = ft.Ref[ft.Dropdown]()
        turno_ref     = ft.Ref[ft.Dropdown]()

        # El rol que llega del backend puede ser "Sin asignar" (un Empleado
        # cargado sin fila de especialidad todavía). Ese valor no existe como
        # opción del Dropdown, y asignárselo lo dejaría en blanco, así que se
        # cae a Entrenador.
        rol_actual = empleado["rol"] if is_edit else "Entrenador"
        if rol_actual not in ROLES_EMPLEADO:
            rol_actual = "Entrenador"

        # El turno del recepcionista ahora es una FK a Franja_Laboral: se
        # ofrecen las franjas reales (catálogo), no un enum hardcodeado.
        franjas = app_state.get_franjas()
        franja_sel = str(empleado.get("id_franja_laboral")) if is_edit and empleado.get("id_franja_laboral") else None

        def _dropdown(label, opciones, valor, ref):
            return ft.Dropdown(
                ref=ref,
                label=label,
                options=[ft.dropdown.Option(o) for o in opciones],
                value=valor,
                color=Colors.TEXT_PRIMARY, bgcolor=Colors.BG_INPUT,
                border_color=Colors.BORDER, focused_border_color=Colors.ACCENT,
                border_radius=10,
            )

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Editar Empleado" if is_edit else "Nuevo Empleado",
                          color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=420,
                # El alto tope + scroll es por el formulario largo: sin esto el
                # diálogo crece hasta pasarse de la ventana y los botones
                # Guardar/Cancelar quedan fuera de la pantalla.
                height=430,
                content=ft.Column([
                    input_field("Nombre", "Ej: María", ref=nombre_ref,
                                icon=ft.Icons.PERSON_OUTLINE_ROUNDED,
                                value=empleado["nombre_pila"] if is_edit else ""),
                    ft.Container(height=12),
                    input_field("Apellido", "Ej: González", ref=apellido_ref,
                                icon=ft.Icons.PERSON_OUTLINE_ROUNDED,
                                value=empleado["apellido"] if is_edit else ""),
                    ft.Container(height=12),
                    # El DNI identifica a la Persona y no se edita desde acá:
                    # cambiarlo sería otra persona, no la misma corregida.
                    input_field("DNI", "Ej: 30123456", ref=dni_ref,
                                icon=ft.Icons.BADGE_OUTLINED,
                                value=empleado["dni"] if is_edit else ""),
                    ft.Container(height=12),
                    _dropdown("Rol", ROLES_EMPLEADO, rol_actual, rol_ref),
                    ft.Container(height=12),
                    ft.Dropdown(
                        ref=turno_ref,
                        label="Turno / franja (solo Recepcionista)",
                        options=[ft.dropdown.Option(key=str(f["id"]), text=f["nombre"])
                                 for f in franjas],
                        value=franja_sel,
                        color=Colors.TEXT_PRIMARY, bgcolor=Colors.BG_INPUT,
                        border_color=Colors.BORDER, focused_border_color=Colors.ACCENT,
                        border_radius=10,
                    ),
                    ft.Container(height=12),
                    input_field("Email", "empleado@gimnasio.com", ref=email_ref,
                                icon=ft.Icons.EMAIL_OUTLINED,
                                value=empleado["email"] if is_edit else ""),
                    ft.Container(height=12),
                    input_field("Teléfono", "Ej: 3415551234", ref=telefono_ref,
                                icon=ft.Icons.PHONE_OUTLINED),
                    ft.Container(height=12),
                    input_field("Título", "Ej: Profesor de Educación Física",
                                ref=titulo_ref, icon=ft.Icons.SCHOOL_OUTLINED,
                                value=empleado["titulo"] if is_edit else ""),
                    ft.Container(height=12),
                    input_field("Matrícula", "Ej: MN 12345", ref=matricula_ref,
                                icon=ft.Icons.VERIFIED_OUTLINED,
                                value=empleado["matricula"] if is_edit else ""),
                ], spacing=0, tight=True, scroll=ft.ScrollMode.AUTO),
            ),
            actions=[
                ft.TextButton("Cancelar",
                              style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                              on_click=lambda e: close_dialog(self.page, dlg)),
                ft.TextButton("Guardar",
                              style=ft.ButtonStyle(color=Colors.ACCENT),
                              on_click=lambda e: self._save(
                                  dlg,
                                  empleado["id"] if is_edit else None,
                                  {"nombre": nombre_ref, "apellido": apellido_ref,
                                   "dni": dni_ref, "email": email_ref,
                                   "telefono": telefono_ref, "titulo": titulo_ref,
                                   "matricula": matricula_ref},
                                  rol_ref, turno_ref,
                              )),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        open_dialog(self.page, dlg)

    def _cambiar_estado(self, p: dict):
        """Baja con confirmación; reactivar sin, porque es reversible."""
        def aplicar(resultado: dict):
            if not resultado["ok"]:
                show_snack(self.page, resultado["mensaje"], Colors.STATUS_DANGER)
                return
            show_snack(self.page, resultado["mensaje"], Colors.SUCCESS)
            self.router.navigate(Routes.PERSONAL)

        if not p["activo"]:
            aplicar(app_state.reactivar_empleado(p["id"]))
            return
        open_dialog(self.page, confirm_dialog(
            self.page, f"¿Dar de baja a {p['nombre']}?",
            "Deja de figurar como activo y su cuenta de acceso se desactiva. "
            "Se puede reactivar.",
            on_confirm=lambda: aplicar(app_state.baja_empleado(p["id"])),
            texto_confirmar="Dar de baja",
        ))

    @staticmethod
    def _texto(ref) -> str:
        """Lee un campo aunque todavía no esté montado, sin reventar."""
        return (ref.current.value or "").strip() if ref.current else ""

    def _save(self, dlg, id_empleado, refs, rol_ref, turno_ref):
        """
        Da de alta o edita el empleado.

        Nombre, apellido y DNI se validan acá antes de salir a la red. No es
        para reemplazar la validación del backend —esa manda— sino para no
        gastar un viaje y un error genérico en algo que se ve mirando el
        formulario.
        """
        datos = {campo: self._texto(ref) for campo, ref in refs.items()}
        rol   = rol_ref.current.value if rol_ref.current else "Entrenador"

        faltan = [c for c in ("nombre", "apellido", "dni") if not datos[c]]
        if faltan:
            show_snack(self.page,
                       "Falta completar: " + ", ".join(faltan),
                       Colors.STATUS_DANGER)
            return

        # Mail o teléfono, al menos uno. El backend lo exige igual —es la
        # regla, no una comodidad de esta pantalla— pero avisar acá evita el
        # viaje y señala el problema con el formulario todavía a la vista: un
        # empleado al que nadie sabe cómo contactar no sirve de nada.
        if not datos["email"] and not datos["telefono"]:
            show_snack(self.page,
                       "Cargá un email o un teléfono: sin una de las dos vías "
                       "no hay forma de contactarlo.",
                       Colors.STATUS_DANGER)
            return

        if datos["telefono"] and limpiar_telefono(datos["telefono"]) != datos["telefono"]:
            show_snack(self.page,
                       "El teléfono sólo puede tener números, espacios y los "
                       "signos + ( ) -.",
                       Colors.STATUS_DANGER)
            return

        cuerpo = {
            "dni": datos["dni"],
            "nombre": datos["nombre"],
            "apellido": datos["apellido"],
            # Los opcionales van como None y no como "": el backend los valida
            # con EmailStr, y una cadena vacía no es un mail válido — mandarla
            # haría fallar el alta de alguien que simplemente no dejó mail.
            "email": datos["email"] or None,
            "telefono": datos["telefono"] or None,
            "rol": rol,
            "titulo": datos["titulo"] or None,
            "matricula": datos["matricula"] or None,
            # El turno es ahora una FK: se manda el id de la franja elegida.
            "id_franja_laboral": (
                int(turno_ref.current.value)
                if turno_ref.current and turno_ref.current.value else None),
        }

        if id_empleado is None:
            # id_sede clavado en 1 igual que en la PWA (sociosService.ts y
            # personalService.ts): el gimnasio tiene una sola sede y no hay
            # endpoint que las liste. El día que haya una segunda, esto y sus
            # dos gemelos de la PWA son los tres lugares a tocar.
            cuerpo["id_sede"] = 1
            # Un Profesor no usa el sistema; el router le fuerza esto a False
            # igual, pero mandarlo bien deja claro qué se está pidiendo.
            cuerpo["crear_cuenta"] = rol != "Profesor"
            resultado = app_state.alta_empleado(cuerpo)
        else:
            resultado = app_state.editar_empleado(id_empleado, cuerpo)

        if not resultado["ok"]:
            show_snack(self.page, resultado["mensaje"], Colors.STATUS_DANGER)
            return

        close_dialog(self.page, dlg)

        # En el alta el backend puede devolver credenciales. Se muestran una
        # sola vez: en la base queda el hash y no hay forma de volver a leerlas.
        if id_empleado is None and resultado.get("password_temporal"):
            self._mostrar_credenciales(resultado, datos["email"], datos["telefono"])
        else:
            show_snack(self.page, resultado["mensaje"], Colors.SUCCESS)

        self.router.navigate(Routes.PERSONAL)

    def _mostrar_credenciales(self, resultado: dict, email: str = "", telefono: str = ""):
        """
        Entrega las credenciales del empleado recién dado de alta.

        Va en un diálogo y no en un snack a propósito: el snack se va solo a
        los pocos segundos y esta contraseña no se puede volver a consultar
        —la base guarda el hash—, así que si se pierde hay que resetearla.

        Y además de mostrarlas, las MANDA: los botones abren el mail o el
        WhatsApp con el mensaje ya escrito. Hasta acá el alta terminaba con
        alguien copiando una contraseña a mano para pasarla por otro lado.

        El texto lo arma el BACKEND (`texto_credenciales`, de
        notificaciones.py), el mismo que manda por mail: así el empleado lee
        lo mismo por donde le llegue, y la advertencia de que la contraseña es
        de un solo uso no depende de que cada pantalla se acuerde de ponerla.
        """
        legajo = resultado.get("legajo")
        texto = resultado.get("texto_credenciales") or (
            f"Usuario: {resultado.get('usuario', '—')} — "
            f"Contraseña temporal: {resultado['password_temporal']}")

        # El mail primero cuando existe; si sólo dejó teléfono, WhatsApp es la
        # única vía. Misma regla que el botón "Contactar" de la tarjeta.
        envios = []
        if email:
            envios.append(ft.TextButton(
                "Enviar por mail",
                style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                on_click=lambda e: self.page.launch_url(
                    link_mail(email, ASUNTO_CREDENCIALES, texto)),
            ))
        if telefono:
            envios.append(ft.TextButton(
                "Enviar por WhatsApp",
                style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                on_click=lambda e: self.page.launch_url(
                    link_whatsapp(telefono, texto)),
            ))
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Empleado dado de alta",
                          color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=380,
                content=ft.Column([
                    ft.Text(resultado["mensaje"], color=Colors.TEXT_SECONDARY, size=13),
                    ft.Container(height=12),
                    *([ft.Text(f"Legajo: {legajo}", color=Colors.TEXT_PRIMARY,
                               size=13, weight=ft.FontWeight.W_500)] if legajo else []),
                    ft.Container(height=8),
                    ft.Text(f"Usuario: {resultado.get('usuario', '—')}",
                            color=Colors.TEXT_PRIMARY, size=14,
                            weight=ft.FontWeight.BOLD),
                    ft.Text(f"Contraseña temporal: {resultado['password_temporal']}",
                            color=Colors.PRIMARY_VOLT, size=14,
                            weight=ft.FontWeight.BOLD, selectable=True),
                    ft.Container(height=12),
                    *([ft.Text(f"Ya se le envió un mail a {email} con estos datos.",
                               color=Colors.STATUS_OK, size=12)]
                      if resultado.get("email_enviado") else []),
                    ft.Text("No se puede volver a ver: en la base queda sólo el "
                            "hash. Mandásela ahora. El empleado deberá cambiarla "
                            "al entrar por primera vez.",
                            color=Colors.STATUS_WARN, size=12),
                ], spacing=0, tight=True),
            ),
            actions=[
                *envios,
                ft.TextButton("Listo",
                              style=ft.ButtonStyle(color=Colors.ACCENT),
                              on_click=lambda e: close_dialog(self.page, dlg)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(self.page, dlg)
