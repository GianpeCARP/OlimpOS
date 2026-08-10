# =============================================================================
# views/alta_persona.py — Alta unificada de personas
# =============================================================================
# Reemplaza los tres formularios de alta que antes vivían repartidos en
# Socios, Personal y Usuarios. Acá se cargan los datos personales UNA
# sola vez, se elige la función (Socio / Entrenador / Nutricionista /
# Recepción / Administrador / Propietario) y, si corresponde, se le crea
# el acceso al sistema — todo en un único guardado.
#
# Las secciones Socios, Personal y Usuarios pasan a ser de solo consulta
# y modificación: ya no tienen botón de alta propio.

import flet as ft
from app.config import Colors
from app.state import app_state, PLAN_DISPLAY, TURNO_LABORAL_DISPLAY, ROL_DISPLAY
from app.components.ui import build_topbar, input_field, show_snack

FUNCION_OPTIONS = [("SOCIO", "Socio")] + list(ROL_DISPLAY.items())


class AltaPersonaView:
    def __init__(self, page: ft.Page, router):
        self.page = page
        self.router = router

        # Refs de los campos de datos personales
        self.dni_ref = ft.Ref[ft.TextField]()
        self.nombre_ref = ft.Ref[ft.TextField]()
        self.apellido_ref = ft.Ref[ft.TextField]()
        self.telefono_ref = ft.Ref[ft.TextField]()
        self.email_ref = ft.Ref[ft.TextField]()
        self.calle_ref = ft.Ref[ft.TextField]()
        self.numero_ref = ft.Ref[ft.TextField]()
        self.localidad_ref = ft.Ref[ft.TextField]()

        # Refs de la función elegida y sus campos específicos
        self.funcion_ref = ft.Ref[ft.Dropdown]()
        self.plan_ref = ft.Ref[ft.Dropdown]()
        self.turno_ref = ft.Ref[ft.Dropdown]()

        # Refs del acceso al sistema (opcional)
        self.crear_acceso_ref = ft.Ref[ft.Checkbox]()
        self.email_acceso_ref = ft.Ref[ft.TextField]()
        self.password_ref = ft.Ref[ft.TextField]()

        # Refs de las zonas que se reconstruyen dinámicamente
        self.form_ref = ft.Ref[ft.Column]()
        self.especifico_ref = ft.Ref[ft.Column]()
        self.acceso_ref = ft.Ref[ft.Column]()
        self.estado_ref = ft.Ref[ft.Text]()

        # Contexto de la búsqueda actual
        self.contexto = {
            "dni": None, "persona_existe": False,
            "tiene_socio": False, "tiene_empleado": False, "tiene_usuario": False,
        }

    def build(self) -> ft.Column:
        topbar = build_topbar("Nueva Persona",
                               "Cargá los datos personales y, si corresponde, su acceso al sistema")

        card = ft.Container(
            content=ft.Column(ref=self.form_ref, controls=self._paso_busqueda(), spacing=0),
            bgcolor=Colors.BG_CARD,
            border_radius=14,
            border=ft.Border.all(1, Colors.BORDER),
            padding=28,
            width=560,
        )

        body = ft.Column([
            topbar,
            ft.Container(content=card, padding=ft.Padding.all(24)),
        ], spacing=0, expand=True, scroll=ft.ScrollMode.AUTO)

        return body

    # ---------------------------------------------------------------------
    # Paso 1: buscar por DNI
    # ---------------------------------------------------------------------

    def _paso_busqueda(self) -> list:
        return [
            ft.Text("Paso 1 — Documento", color=Colors.TEXT_PRIMARY, size=15, weight=ft.FontWeight.BOLD),
            ft.Container(height=12),
            ft.Row([
                ft.Container(
                    content=input_field("DNI", "Ej: 30123456", icon=ft.Icons.BADGE_OUTLINED, ref=self.dni_ref),
                    expand=True,
                ),
                ft.Container(width=12),
                ft.ElevatedButton(
                    "Buscar", icon=ft.Icons.SEARCH_ROUNDED,
                    bgcolor=Colors.ACCENT, color=Colors.WHITE,
                    on_click=self._al_buscar,
                    height=48,
                ),
            ], vertical_alignment=ft.CrossAxisAlignment.END),
            ft.Container(height=8),
            ft.Text(
                "Si la persona ya está cargada (por ejemplo, ya es socia o empleada), "
                "se reutilizan sus datos y solo se agrega la función nueva que elijas.",
                color=Colors.TEXT_MUTED, size=12,
            ),
        ]

    def _al_buscar(self, e):
        dni = (self.dni_ref.current.value or "").strip()
        if not dni:
            show_snack(self.page, "Ingresá un DNI para buscar", Colors.DANGER)
            return

        resultado = app_state.buscar_persona(dni)
        self.contexto["dni"] = dni

        if resultado["ok"]:
            persona = resultado["persona"]
            self.contexto.update({
                "persona_existe": True,
                "tiene_socio": persona["tiene_socio"],
                "tiene_empleado": persona["tiene_empleado"],
                "tiene_usuario": persona["tiene_usuario"],
            })
            self._mostrar_formulario(persona)
        else:
            self.contexto.update({
                "persona_existe": False, "tiene_socio": False,
                "tiene_empleado": False, "tiene_usuario": False,
            })
            self._mostrar_formulario(None)

    # ---------------------------------------------------------------------
    # Paso 2: datos personales + función + acceso
    # ---------------------------------------------------------------------

    def _mostrar_formulario(self, persona: dict | None):
        controles = [
            ft.Row([
                ft.Icon(ft.Icons.BADGE_ROUNDED, color=Colors.TEXT_MUTED, size=14),
                ft.Text(f"DNI: {self.contexto['dni']}", color=Colors.TEXT_SECONDARY, size=13),
                ft.Container(expand=True),
                ft.TextButton("Buscar otro DNI", icon=ft.Icons.REFRESH_ROUNDED,
                              style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                              on_click=self._reiniciar),
            ]),
            ft.Container(height=8),
        ]

        if persona:
            controles.append(ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color=Colors.SUCCESS, size=16),
                    ft.Text(f"Persona ya registrada: {persona['nombre']} {persona['apellido']}",
                            color=Colors.TEXT_SECONDARY, size=13),
                ], spacing=8),
                bgcolor=Colors.BG_INPUT, border_radius=8,
                padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            ))
            controles.append(ft.Container(height=16))

        controles += [
            ft.Text("Paso 2 — Datos personales", color=Colors.TEXT_PRIMARY, size=15, weight=ft.FontWeight.BOLD),
            ft.Container(height=12),
            input_field("Nombre", "Ej: Juan", icon=ft.Icons.PERSON_OUTLINE_ROUNDED, ref=self.nombre_ref),
            ft.Container(height=12),
            input_field("Apellido", "Ej: García", icon=ft.Icons.PERSON_OUTLINE_ROUNDED, ref=self.apellido_ref),
            ft.Container(height=12),
            input_field("Teléfono", "Opcional", icon=ft.Icons.PHONE_OUTLINED, ref=self.telefono_ref),
            ft.Container(height=12),
            input_field("Email de contacto", "Opcional", icon=ft.Icons.EMAIL_OUTLINED, ref=self.email_ref),
            ft.Container(height=12),
            ft.Row([
                input_field("Calle", "Opcional", width=220, ref=self.calle_ref),
                ft.Container(width=8),
                input_field("Número", "Opcional", width=140, ref=self.numero_ref),
            ]),
            ft.Container(height=12),
            input_field("Localidad", "Opcional", icon=ft.Icons.LOCATION_ON_OUTLINED, ref=self.localidad_ref),
            ft.Container(height=20),
            ft.Divider(color=Colors.BORDER, height=1),
            ft.Container(height=16),
            ft.Text("Paso 3 — Función", color=Colors.TEXT_PRIMARY, size=15, weight=ft.FontWeight.BOLD),
            ft.Container(height=12),
            ft.Dropdown(
                ref=self.funcion_ref,
                label="¿Qué función cumple esta persona?",
                options=[
                    ft.dropdown.Option(key=k, text=self._label_funcion(k, v))
                    for k, v in FUNCION_OPTIONS
                ],
                value=self._funcion_por_defecto(),
                color=Colors.TEXT_PRIMARY, bgcolor=Colors.BG_INPUT,
                border_color=Colors.BORDER, focused_border_color=Colors.ACCENT,
                border_radius=10,
                on_select=self._al_cambiar_funcion,
            ),
            ft.Container(height=12),
            ft.Column(ref=self.especifico_ref, controls=self._campos_especificos(self._funcion_por_defecto())),
            ft.Container(height=20),
            ft.Divider(color=Colors.BORDER, height=1),
            ft.Container(height=16),
            ft.Column(ref=self.acceso_ref, controls=self._seccion_acceso(persona)),
            ft.Container(height=8),
            ft.Text(ref=self.estado_ref, value="", color=Colors.DANGER, size=12),
            ft.Container(height=16),
            ft.Container(
                content=ft.Row([
                    ft.Text("Guardar", color=Colors.WHITE, size=15, weight=ft.FontWeight.W_600),
                ], alignment=ft.MainAxisAlignment.CENTER),
                bgcolor=Colors.ACCENT, border_radius=10, height=48,
                on_click=self._guardar,
            ),
        ]

        self.form_ref.current.controls = controles
        self.form_ref.current.update()

        if persona:
            self.nombre_ref.current.value = persona["nombre"]
            self.apellido_ref.current.value = persona["apellido"]
            self.telefono_ref.current.value = persona.get("telefono") or ""
            self.email_ref.current.value = persona.get("email") or ""
            self.calle_ref.current.value = persona.get("calle") or ""
            self.numero_ref.current.value = persona.get("numero") or ""
            self.localidad_ref.current.value = persona.get("localidad") or ""
            self.form_ref.current.update()

    def _label_funcion(self, key: str, label: str) -> str:
        """Marca en el propio texto de la opción si esa función ya existe para esta persona."""
        if key == "SOCIO" and self.contexto["tiene_socio"]:
            return f"{label} (ya es socio)"
        if key != "SOCIO" and self.contexto["tiene_empleado"]:
            return f"{label} (ya tiene ficha de personal)"
        return label

    def _funcion_por_defecto(self) -> str:
        if not self.contexto["tiene_socio"]:
            return "SOCIO"
        return "ENTRENADOR"

    def _al_cambiar_funcion(self, e):
        funcion = self.funcion_ref.current.value
        self.especifico_ref.current.controls = self._campos_especificos(funcion)
        self.especifico_ref.current.update()
        self.acceso_ref.current.controls = self._seccion_acceso(None, funcion_actual=funcion)
        self.acceso_ref.current.update()

    def _campos_especificos(self, funcion: str) -> list:
        if funcion == "SOCIO":
            return [
                ft.Dropdown(
                    ref=self.plan_ref,
                    label="Plan",
                    options=[ft.dropdown.Option(v) for v in PLAN_DISPLAY.values()],
                    value="Básico",
                    color=Colors.TEXT_PRIMARY, bgcolor=Colors.BG_INPUT,
                    border_color=Colors.BORDER, focused_border_color=Colors.ACCENT,
                    border_radius=10,
                ),
            ]
        return [
            ft.Dropdown(
                ref=self.turno_ref,
                label="Turno de trabajo",
                options=[ft.dropdown.Option(v) for v in TURNO_LABORAL_DISPLAY.values()],
                value="Mañana",
                color=Colors.TEXT_PRIMARY, bgcolor=Colors.BG_INPUT,
                border_color=Colors.BORDER, focused_border_color=Colors.ACCENT,
                border_radius=10,
            ),
        ]

    def _seccion_acceso(self, persona: dict | None, funcion_actual: str = None) -> list:
        """
        Sección de "Crear acceso al sistema". Solo la ve un Propietario o
        Administrador (el backend igual la rechazaría para cualquier otro
        rol, pero no tiene sentido mostrarla si no se va a poder usar).
        Si la persona ya tiene usuario, se muestra un aviso en vez del
        formulario de acceso.
        """
        if not app_state.is_admin():
            return []

        if self.contexto["tiene_usuario"]:
            return [
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.INFO_OUTLINE_ROUNDED, color=Colors.WARNING, size=16),
                        ft.Text("Esta persona ya tiene una cuenta de acceso creada.",
                                color=Colors.WARNING, size=13),
                    ], spacing=8),
                    bgcolor="#F59E0B20", border_radius=8,
                    padding=ft.Padding.symmetric(horizontal=12, vertical=10),
                ),
            ]

        funcion = funcion_actual or self.funcion_ref.current.value if self.funcion_ref.current else "SOCIO"
        marcado_por_defecto = funcion != "SOCIO"

        return [
            ft.Text("Paso 4 — Acceso al sistema (opcional)", color=Colors.TEXT_PRIMARY, size=15,
                    weight=ft.FontWeight.BOLD),
            ft.Container(height=8),
            ft.Checkbox(
                ref=self.crear_acceso_ref,
                label="Crear acceso al sistema para esta persona",
                value=marcado_por_defecto,
                active_color=Colors.ACCENT,
                on_change=self._al_toggle_acceso,
            ),
            ft.Container(height=8),
            ft.Column(
                controls=self._campos_acceso() if marcado_por_defecto else [],
            ),
        ]

    def _al_toggle_acceso(self, e):
        # Reconstruye toda la sección de acceso para mostrar/ocultar los campos
        self.acceso_ref.current.controls = self._seccion_acceso(
            None, funcion_actual=self.funcion_ref.current.value,
        )
        # Vuelve a marcar el checkbox como estaba (la reconstrucción de arriba
        # lo resetea al valor "por defecto"; acá se respeta lo que el usuario
        # tildó manualmente).
        if self.crear_acceso_ref.current:
            self.crear_acceso_ref.current.value = e.control.value
        self.acceso_ref.current.update()

    def _campos_acceso(self) -> list:
        email_sugerido = (self.email_ref.current.value or "") if self.email_ref.current else ""
        return [
            input_field("Email de acceso", "usuario@gimnasio.com",
                        icon=ft.Icons.ALTERNATE_EMAIL_ROUNDED, ref=self.email_acceso_ref),
            ft.Container(height=12),
            input_field("Contraseña inicial", "••••••••", password=True,
                        icon=ft.Icons.LOCK_OUTLINE_ROUNDED, ref=self.password_ref),
            ft.Container(height=8),
            ft.Row([
                ft.Icon(ft.Icons.INFO_OUTLINE_ROUNDED, color=Colors.TEXT_MUTED, size=14),
                ft.Text("Deberá cambiar esta contraseña en su primer ingreso.",
                        color=Colors.TEXT_MUTED, size=12),
            ], spacing=6),
        ]

    # ---------------------------------------------------------------------
    # Guardar
    # ---------------------------------------------------------------------

    def _guardar(self, e):
        nombre = (self.nombre_ref.current.value or "").strip()
        apellido = (self.apellido_ref.current.value or "").strip()

        if not self.contexto["persona_existe"] and (not nombre or not apellido):
            self._mostrar_error("Nombre y apellido son obligatorios.")
            return

        funcion = self.funcion_ref.current.value
        ya_tiene_esa_funcion = (
            (funcion == "SOCIO" and self.contexto["tiene_socio"]) or
            (funcion != "SOCIO" and self.contexto["tiene_empleado"])
        )

        plan_display = self.plan_ref.current.value if self.plan_ref.current else None
        turno_display = self.turno_ref.current.value if self.turno_ref.current else None

        crear_acceso = bool(self.crear_acceso_ref.current and self.crear_acceso_ref.current.value)
        email_acceso = (self.email_acceso_ref.current.value or "").strip() if self.email_acceso_ref.current else ""
        password_inicial = self.password_ref.current.value if self.password_ref.current else ""

        if crear_acceso and (not email_acceso or not password_inicial):
            self._mostrar_error("Para crear el acceso hacen falta el email y la contraseña inicial.")
            return

        resultado = app_state.crear_persona_completa(
            persona_existe=self.contexto["persona_existe"],
            dni=self.contexto["dni"],
            nombre=nombre, apellido=apellido,
            telefono=self.telefono_ref.current.value,
            email=self.email_ref.current.value,
            calle=self.calle_ref.current.value,
            numero=self.numero_ref.current.value,
            localidad=self.localidad_ref.current.value,
            funcion=None if ya_tiene_esa_funcion else funcion,
            plan_display=plan_display,
            turno_display=turno_display,
            crear_acceso=crear_acceso and not self.contexto["tiene_usuario"],
            email_acceso=email_acceso,
            password_inicial=password_inicial,
        )

        if resultado["ok"]:
            show_snack(self.page, "Persona guardada correctamente ✓", Colors.SUCCESS)
            self._reiniciar(None)
        else:
            self._mostrar_error(resultado["mensaje"] or "No se pudo guardar.")

    def _mostrar_error(self, texto: str):
        show_snack(self.page, texto, Colors.DANGER)

    def _reiniciar(self, e):
        self.contexto = {
            "dni": None, "persona_existe": False,
            "tiene_socio": False, "tiene_empleado": False, "tiene_usuario": False,
        }
        self.form_ref.current.controls = self._paso_busqueda()
        self.form_ref.current.update()
