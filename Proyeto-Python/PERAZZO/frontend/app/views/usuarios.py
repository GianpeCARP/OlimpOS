# =============================================================================
# views/usuarios.py — Consulta y modificación de usuarios del sistema
# =============================================================================
# El alta de un usuario nuevo se hace desde "Nueva Persona" (que primero
# carga los datos personales y, si corresponde, crea el acceso). Esta
# pantalla es solo para ver el listado, cambiar el rol, resetear la
# contraseña o activar/desactivar una cuenta existente. Solo la ven
# Propietario y Administradores (guard en router.py).

import flet as ft
from app.config import Colors, Routes
from app.state import app_state
from app.components.ui import (build_topbar, status_badge, primary_button,
                                show_snack, open_dialog, close_dialog)

# Roles tal como los devuelve la API (ver models.RolEnum del backend).
ROLE_CONFIG = {
    "PROPIETARIO":   ("Propietario",   Colors.ACCENT,   "#FF572220", ft.Icons.SHIELD_ROUNDED),
    "ADMIN":         ("Administrador", Colors.ACCENT,   "#FF572220", ft.Icons.ADMIN_PANEL_SETTINGS_ROUNDED),
    "ENTRENADOR":    ("Entrenador",    Colors.SUCCESS,  "#22C55E20", ft.Icons.FITNESS_CENTER_ROUNDED),
    "RECEPCION":     ("Recepción",     Colors.INFO,     "#3B82F620", ft.Icons.SUPPORT_AGENT_ROUNDED),
    "NUTRICIONISTA": ("Nutricionista", Colors.WARNING,  "#F59E0B20", ft.Icons.RESTAURANT_MENU_ROUNDED),
}


class UsuariosView:
    def __init__(self, page: ft.Page, router):
        self.page = page
        self.router = router
        self.tabla_ref = ft.Ref[ft.Column]()
        self._usuarios: list = []

    def build(self) -> ft.Column:
        self._usuarios = app_state.get_usuarios()

        topbar = build_topbar(
            "Usuarios",
            "Gestión de accesos al sistema",
            actions=[
                primary_button("Nueva Persona", ft.Icons.PERSON_ADD_ROUNDED,
                               on_click=lambda e: self.router.navigate(Routes.ALTA)),
            ]
        )

        admin_banner = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.SHIELD_ROUNDED, color=Colors.ACCENT, size=18),
                ft.Text("Esta sección es exclusiva para Propietario y Administradores.",
                        color=Colors.TEXT_SECONDARY, size=13),
            ], spacing=10),
            bgcolor=Colors.ACCENT_GLOW,
            border=ft.Border.all(1, Colors.ACCENT),
            border_radius=10,
            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
        )

        tabla = ft.Column(ref=self.tabla_ref, controls=[self._build_tabla()])

        table_container = ft.Container(
            content=tabla,
            bgcolor=Colors.BG_CARD,
            border_radius=14,
            border=ft.Border.all(1, Colors.BORDER),
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        )

        permisos_card = ft.Container(
            content=ft.Column([
                ft.Text("Roles Disponibles", color=Colors.TEXT_PRIMARY, size=15,
                        weight=ft.FontWeight.BOLD),
                ft.Container(height=12),
                *[_perms_row(rol, cfg) for rol, cfg in ROLE_CONFIG.items()],
            ], spacing=8),
            bgcolor=Colors.BG_CARD,
            border_radius=14,
            border=ft.Border.all(1, Colors.BORDER),
            padding=20,
        )

        body = ft.Column([
            topbar,
            ft.Container(
                content=ft.Column([
                    admin_banner,
                    ft.Container(height=20),
                    table_container,
                    ft.Container(height=20),
                    permisos_card,
                ], spacing=0),
                padding=ft.Padding.all(24),
                expand=True,
            ),
        ], spacing=0, expand=True, scroll=ft.ScrollMode.AUTO)

        return body

    def _refrescar(self):
        self._usuarios = app_state.get_usuarios()
        self.tabla_ref.current.controls = [self._build_tabla()]
        self.tabla_ref.current.update()

    def _build_tabla(self) -> ft.Column:
        filas = [_table_header()]
        if not self._usuarios:
            filas.append(ft.Container(
                content=ft.Text("No hay usuarios cargados.", color=Colors.TEXT_MUTED, size=13),
                padding=ft.Padding.symmetric(horizontal=20, vertical=20),
            ))
        filas += [self._user_row(u) for u in self._usuarios]
        return ft.Column(filas, spacing=0)

    def _user_row(self, u: dict) -> ft.Container:
        role_label, role_color, role_bg, role_icon = ROLE_CONFIG.get(
            u["role"], ("Desconocido", Colors.TEXT_MUTED, Colors.BG_INPUT, ft.Icons.PERSON_ROUNDED)
        )
        initial = u["nombre"][0].upper() if u["nombre"] else "?"

        def on_hover(e: ft.HoverEvent):
            e.control.bgcolor = Colors.BG_INPUT if e.data == "true" else ft.Colors.TRANSPARENT
            e.control.update()

        return ft.Container(
            content=ft.Row([
                ft.Row([
                    ft.Container(
                        content=ft.Text(initial, color=Colors.WHITE, size=13,
                                        weight=ft.FontWeight.BOLD),
                        width=32, height=32, border_radius=16,
                        bgcolor=role_color, alignment=ft.Alignment.CENTER,
                    ),
                    ft.Column([
                        ft.Text(u["nombre"], color=Colors.TEXT_PRIMARY, size=14),
                        ft.Text(f"{u['username']} · DNI {u['dni']}",
                                color=Colors.TEXT_MUTED, size=11),
                    ], spacing=1, tight=True),
                ], spacing=10, expand=3),
                ft.Container(
                    content=ft.Row([
                        ft.Container(
                            content=ft.Icon(role_icon, color=role_color, size=14),
                            width=24, height=24, border_radius=6,
                            bgcolor=role_bg, alignment=ft.Alignment.CENTER,
                        ),
                        ft.Text(role_label, color=Colors.TEXT_SECONDARY, size=13),
                    ], spacing=8),
                    expand=2,
                ),
                ft.Container(content=status_badge(u["estado"]), expand=2,
                             alignment=ft.Alignment.CENTER_LEFT),
                ft.Row([
                    ft.IconButton(ft.Icons.EDIT_ROUNDED, icon_color=Colors.INFO,
                                  icon_size=18, tooltip="Cambiar rol",
                                  on_click=lambda e, x=u: self._open_editar_rol(x)),
                    ft.IconButton(ft.Icons.KEY_ROUNDED, icon_color=Colors.WARNING,
                                  icon_size=18, tooltip="Resetear contraseña",
                                  on_click=lambda e, x=u: self._reset_password(x)),
                    ft.IconButton(
                        ft.Icons.BLOCK_ROUNDED if u["estado"] == "Activo" else ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED,
                        icon_color=Colors.DANGER if u["estado"] == "Activo" else Colors.SUCCESS,
                        icon_size=18,
                        tooltip="Desactivar" if u["estado"] == "Activo" else "Activar",
                        on_click=lambda e, x=u: self._toggle_estado(x),
                    ),
                ], expand=2),
            ]),
            padding=ft.Padding.symmetric(horizontal=20, vertical=12),
            border=ft.Border.only(bottom=ft.BorderSide(1, Colors.BORDER)),
            on_hover=on_hover,
            animate=ft.Animation(120),
        )

    # ---------------------------------------------------------------------
    # Cambio de rol, reseteo de contraseña, activar/desactivar
    # ---------------------------------------------------------------------

    def _open_editar_rol(self, u: dict):
        """
        Edita solo el rol de la cuenta. El nombre/apellido ya no se editan
        acá: para corregirlos hay que editar la Persona (fuera del alcance
        de este diálogo rápido).
        """
        rol_ref = ft.Ref[ft.Dropdown]()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Editar rol de {u['nombre']}",
                          color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=380,
                content=ft.Dropdown(
                    ref=rol_ref,
                    label="Rol del sistema",
                    options=[ft.dropdown.Option(key=k, text=v[0]) for k, v in ROLE_CONFIG.items()],
                    value=u["role"],
                    color=Colors.TEXT_PRIMARY, bgcolor=Colors.BG_INPUT,
                    border_color=Colors.BORDER, focused_border_color=Colors.ACCENT,
                    border_radius=10,
                ),
            ),
            actions=[
                ft.TextButton("Cancelar", style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                              on_click=lambda e: close_dialog(self.page, dlg)),
                ft.TextButton("Guardar", style=ft.ButtonStyle(color=Colors.ACCENT),
                              on_click=lambda e: self._guardar_rol(dlg, u, rol_ref)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(self.page, dlg)

    def _guardar_rol(self, dlg, u, rol_ref):
        resultado = app_state.actualizar_usuario(u["id"], rol_ref.current.value)
        close_dialog(self.page, dlg)

        if resultado["ok"]:
            show_snack(self.page, "Rol actualizado correctamente ✓", Colors.SUCCESS)
            self._refrescar()
        else:
            show_snack(self.page, resultado["mensaje"] or "No se pudo actualizar el rol", Colors.DANGER)

    def _reset_password(self, u: dict):
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Resetear Contraseña",
                          color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Text(
                f"Se va a generar una contraseña temporal para {u['nombre']}.\n"
                "El usuario deberá cambiarla en su próximo ingreso.",
                color=Colors.TEXT_SECONDARY, size=13,
            ),
            actions=[
                ft.TextButton("Cancelar", style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                              on_click=lambda e: close_dialog(self.page, dlg)),
                ft.TextButton("Confirmar", style=ft.ButtonStyle(color=Colors.WARNING),
                              on_click=lambda e: self._confirmar_reset(dlg, u)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(self.page, dlg)

    def _confirmar_reset(self, dlg, u: dict):
        close_dialog(self.page, dlg)
        resultado = app_state.resetear_password_usuario(u["id"])

        if not resultado["ok"]:
            show_snack(self.page, resultado["mensaje"] or "No se pudo resetear la contraseña", Colors.DANGER)
            return

        password_temporal = resultado["password_temporal"]
        info_dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Contraseña temporal generada",
                          color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Column([
                ft.Text(f"Comunicale esta contraseña a {u['nombre']}:",
                        color=Colors.TEXT_SECONDARY, size=13),
                ft.Container(height=8),
                ft.Container(
                    content=ft.Text(password_temporal, color=Colors.ACCENT, size=18,
                                    weight=ft.FontWeight.BOLD, selectable=True),
                    bgcolor=Colors.BG_INPUT, border_radius=8,
                    padding=ft.Padding.symmetric(horizontal=16, vertical=12),
                ),
            ], tight=True),
            actions=[
                ft.TextButton("Cerrar", style=ft.ButtonStyle(color=Colors.ACCENT),
                              on_click=lambda e: close_dialog(self.page, info_dlg)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(self.page, info_dlg)

    def _toggle_estado(self, u: dict):
        resultado = app_state.alternar_estado_usuario(u["id"])
        if resultado["ok"]:
            nuevo_estado = "activado" if u["estado"] == "Inactivo" else "desactivado"
            show_snack(self.page, f"Usuario {u['nombre']} {nuevo_estado}", Colors.WARNING)
            self._refrescar()
        else:
            show_snack(self.page, resultado["mensaje"] or "No se pudo cambiar el estado", Colors.DANGER)


def _table_header() -> ft.Container:
    return ft.Container(
        content=ft.Row([
            ft.Text("Usuario",   color=Colors.TEXT_MUTED, size=12,
                    weight=ft.FontWeight.W_600, expand=3),
            ft.Text("Rol",      color=Colors.TEXT_MUTED, size=12,
                    weight=ft.FontWeight.W_600, expand=2),
            ft.Text("Estado",   color=Colors.TEXT_MUTED, size=12,
                    weight=ft.FontWeight.W_600, expand=2),
            ft.Text("Acciones", color=Colors.TEXT_MUTED, size=12,
                    weight=ft.FontWeight.W_600, expand=2),
        ]),
        padding=ft.Padding.symmetric(horizontal=20, vertical=14),
        bgcolor=Colors.BG_SIDEBAR,
    )


def _perms_row(rol: str, cfg: tuple) -> ft.Container:
    label, color, bg, icon = cfg
    PERMS = {
        "PROPIETARIO":   ["Dashboard", "Socios", "Personal", "Rutinas", "Nutrición", "Turnos", "Usuarios"],
        "ADMIN":         ["Dashboard", "Socios", "Personal", "Rutinas", "Nutrición", "Turnos", "Usuarios"],
        "ENTRENADOR":    ["Dashboard", "Socios", "Rutinas", "Turnos"],
        "NUTRICIONISTA": ["Dashboard", "Socios", "Nutrición"],
        "RECEPCION":     ["Dashboard", "Socios", "Turnos"],
    }
    perms = PERMS.get(rol, [])
    return ft.Container(
        content=ft.Row([
            ft.Container(
                content=ft.Icon(icon, color=color, size=16),
                width=30, height=30, border_radius=8,
                bgcolor=bg, alignment=ft.Alignment.CENTER,
            ),
            ft.Text(label, color=Colors.TEXT_PRIMARY, size=13,
                    weight=ft.FontWeight.W_500, width=120),
            ft.Row([
                ft.Container(
                    content=ft.Text(p, color=Colors.TEXT_SECONDARY, size=11),
                    bgcolor=Colors.BG_SIDEBAR, border_radius=20,
                    padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                )
                for p in perms
            ], spacing=4, wrap=True),
        ], spacing=10),
        padding=ft.Padding.symmetric(vertical=6),
        border=ft.Border.only(bottom=ft.BorderSide(1, Colors.BORDER)),
    )
