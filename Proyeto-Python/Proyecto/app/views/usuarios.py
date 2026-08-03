# =============================================================================
# views/usuarios.py — Gestión de usuarios del sistema (solo admin)
# =============================================================================
import flet as ft
from app.config import Colors
from app.state import app_state
from app.components.ui import (build_topbar, status_badge, primary_button,
                                input_field, show_snack, open_dialog, close_dialog)

ROLE_CONFIG = {
    "admin":   ("Administrador", Colors.ACCENT,   "#FF572220", ft.Icons.SHIELD_ROUNDED),
    "trainer": ("Entrenador",    Colors.SUCCESS,  "#22C55E20", ft.Icons.FITNESS_CENTER_ROUNDED),
    "staff":   ("Recepción",     Colors.INFO,     "#3B82F620", ft.Icons.SUPPORT_AGENT_ROUNDED),
    "nutri":   ("Nutricionista", Colors.WARNING,  "#F59E0B20", ft.Icons.RESTAURANT_MENU_ROUNDED),
}

# Datos mock de usuarios del sistema
_MOCK_SYSTEM_USERS = [
    {"id": 1, "nombre": "Administrador",  "username": "admin",   "role": "admin",   "estado": "Activo"},
    {"id": 2, "nombre": "Carlos Pérez",   "username": "trainer", "role": "trainer", "estado": "Activo"},
    {"id": 3, "nombre": "Roberto Silva",  "username": "rsilva",  "role": "staff",   "estado": "Activo"},
    {"id": 4, "nombre": "María Gómez",    "username": "mgomez",  "role": "nutri",   "estado": "Inactivo"},
]


class UsuariosView:
    def __init__(self, page: ft.Page, router):
        self.page   = page
        self.router = router

    def build(self) -> ft.Column:
        usuarios = _MOCK_SYSTEM_USERS

        topbar = build_topbar(
            "Usuarios",
            "Gestión de accesos al sistema",
            actions=[
                primary_button("Nuevo Usuario", ft.Icons.PERSON_ADD_ROUNDED,
                               on_click=self._open_form),
            ]
        )

        # ── Banner de advertencia (solo admin) ───────────────────────────────
        admin_banner = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.SHIELD_ROUNDED, color=Colors.ACCENT, size=18),
                ft.Text("Esta sección es exclusiva para administradores del sistema.",
                        color=Colors.TEXT_SECONDARY, size=13),
            ], spacing=10),
            bgcolor=Colors.ACCENT_GLOW,
            border=ft.border.all(1, Colors.ACCENT),
            border_radius=10,
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
        )

        # ── Tabla de usuarios ─────────────────────────────────────────────────
        table = ft.Container(
            content=ft.Column([
                _table_header(),
                *[self._user_row(u) for u in usuarios],
            ], spacing=0),
            bgcolor=Colors.BG_CARD,
            border_radius=14,
            border=ft.border.all(1, Colors.BORDER),
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        )

        # ── Permisos por rol ──────────────────────────────────────────────────
        permisos_card = ft.Container(
            content=ft.Column([
                ft.Text("Permisos por Rol", color=Colors.TEXT_PRIMARY, size=15,
                        weight=ft.FontWeight.BOLD),
                ft.Container(height=12),
                *[_perms_row(rol, cfg) for rol, cfg in ROLE_CONFIG.items()],
            ], spacing=8),
            bgcolor=Colors.BG_CARD,
            border_radius=14,
            border=ft.border.all(1, Colors.BORDER),
            padding=20,
        )

        body = ft.Column([
            topbar,
            ft.Container(
                content=ft.Column([
                    admin_banner,
                    ft.Container(height=20),
                    table,
                    ft.Container(height=20),
                    permisos_card,
                ], spacing=0),
                padding=ft.padding.all(24),
                expand=True,
            ),
        ], spacing=0, expand=True, scroll=ft.ScrollMode.AUTO)

        return body

    def _user_row(self, u: dict) -> ft.Container:
        role_label, role_color, role_bg, role_icon = ROLE_CONFIG.get(
            u["role"], ("Desconocido", Colors.TEXT_MUTED, Colors.BG_INPUT, ft.Icons.PERSON_ROUNDED)
        )
        initial = u["nombre"][0].upper()

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
                        ft.Text(f"@{u['username']}", color=Colors.TEXT_MUTED, size=11),
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
                             alignment=ft.Alignment.CENTER_LEFT,
                ),
                ft.Row([
                    ft.IconButton(ft.Icons.EDIT_ROUNDED, icon_color=Colors.INFO,
                                  icon_size=18, tooltip="Editar usuario",
                                  on_click=lambda e, x=u: self._open_form(e, x)),
                    ft.IconButton(ft.Icons.KEY_ROUNDED, icon_color=Colors.WARNING,
                                  icon_size=18, tooltip="Resetear contraseña",
                                  on_click=lambda e, x=u: self._reset_password(x)),
                    ft.IconButton(
                        ft.Icons.BLOCK_ROUNDED if u["estado"] == "Activo" else ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED,
                        icon_color=Colors.DANGER if u["estado"] == "Activo" else Colors.SUCCESS,
                        icon_size=18,
                        tooltip="Desactivar" if u["estado"] == "Activo" else "Activar",
                        on_click=lambda e, x=u: show_snack(
                            self.page,
                            f"Usuario {x['nombre']} {'desactivado' if x['estado'] == 'Activo' else 'activado'}",
                            Colors.WARNING
                        ),
                    ),
                ], expand=2),
            ]),
            padding=ft.padding.symmetric(horizontal=20, vertical=12),
            border=ft.border.only(bottom=ft.BorderSide(1, Colors.BORDER)),
            on_hover=on_hover,
            animate=ft.Animation(120),
        )

    def _open_form(self, e=None, usuario: dict = None):
        is_edit = usuario is not None
        nombre_ref = ft.Ref[ft.TextField]()
        user_ref   = ft.Ref[ft.TextField]()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Editar Usuario" if is_edit else "Nuevo Usuario",
                          color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=440,
                content=ft.Column([
                    input_field("Nombre completo", "Ej: Juan García",
                                icon=ft.Icons.PERSON_OUTLINE_ROUNDED, ref=nombre_ref),
                    ft.Container(height=12),
                    input_field("Nombre de usuario", "juan_garcia",
                                icon=ft.Icons.ALTERNATE_EMAIL_ROUNDED, ref=user_ref),
                    ft.Container(height=12),
                    ft.Dropdown(
                        label="Rol del sistema",
                        options=[
                            ft.dropdown.Option("admin",   "Administrador"),
                            ft.dropdown.Option("trainer", "Entrenador"),
                            ft.dropdown.Option("nutri",   "Nutricionista"),
                            ft.dropdown.Option("staff",   "Recepción"),
                        ],
                        value=usuario["role"] if is_edit else "staff",
                        color=Colors.TEXT_PRIMARY, bgcolor=Colors.BG_INPUT,
                        border_color=Colors.BORDER, focused_border_color=Colors.ACCENT,
                        border_radius=10,
                    ),
                    ft.Container(height=12),
                    input_field("Email", "usuario@gimnasio.com",
                                icon=ft.Icons.EMAIL_OUTLINED),
                    ft.Container(height=12),
                    *([] if is_edit else [
                        input_field("Contraseña inicial", "••••••••",
                                    password=True, icon=ft.Icons.LOCK_OUTLINE_ROUNDED),
                        ft.Container(height=8),
                        ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.Icons.INFO_OUTLINE_ROUNDED,
                                        color=Colors.TEXT_MUTED, size=14),
                                ft.Text("El usuario deberá cambiar su contraseña al primer login.",
                                        color=Colors.TEXT_MUTED, size=12),
                            ], spacing=6),
                        ),
                    ]),
                ], spacing=0, tight=True),
            ),
            actions=[
                ft.TextButton("Cancelar",
                              style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                              on_click=lambda e: close_dialog(self.page, dlg)),
                ft.TextButton("Guardar",
                              style=ft.ButtonStyle(color=Colors.ACCENT),
                              on_click=lambda e: self._save(dlg)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        if is_edit:
            if nombre_ref.current:
                nombre_ref.current.value = usuario["nombre"]
            if user_ref.current:
                user_ref.current.value = usuario["username"]

        open_dialog(self.page, dlg)

    def _save(self, dlg):
        """TODO: POST/PUT /api/usuarios"""
        close_dialog(self.page, dlg)
        show_snack(self.page, "Usuario guardado correctamente ✓", Colors.SUCCESS)

    def _reset_password(self, u: dict):
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Resetear Contraseña",
                          color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Text(
                f"Se enviará un enlace de reseteo a {u['nombre']}.\n"
                "El usuario deberá crear una nueva contraseña.",
                color=Colors.TEXT_SECONDARY, size=13,
            ),
            actions=[
                ft.TextButton("Cancelar",
                              style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                              on_click=lambda e: close_dialog(self.page, dlg)),
                ft.TextButton("Confirmar",
                              style=ft.ButtonStyle(color=Colors.WARNING),
                              on_click=lambda e: (
                                  close_dialog(self.page, dlg),
                                  show_snack(self.page, f"Reseteo enviado a {u['nombre']}",
                                             Colors.WARNING)
                              )),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(self.page, dlg)


def _table_header() -> ft.Container:
    return ft.Container(
        content=ft.Row([
            ft.Text("Usuario",  color=Colors.TEXT_MUTED, size=12,
                    weight=ft.FontWeight.W_600, expand=3),
            ft.Text("Rol",     color=Colors.TEXT_MUTED, size=12,
                    weight=ft.FontWeight.W_600, expand=2),
            ft.Text("Estado",  color=Colors.TEXT_MUTED, size=12,
                    weight=ft.FontWeight.W_600, expand=2),
            ft.Text("Acciones",color=Colors.TEXT_MUTED, size=12,
                    weight=ft.FontWeight.W_600, expand=2),
        ]),
        padding=ft.padding.symmetric(horizontal=20, vertical=14),
        bgcolor=Colors.BG_SIDEBAR,
    )


def _perms_row(rol: str, cfg: tuple) -> ft.Container:
    label, color, bg, icon = cfg
    PERMS = {
        "admin":   ["Dashboard", "Socios", "Personal", "Rutinas", "Nutrición", "Usuarios"],
        "trainer": ["Dashboard", "Socios", "Rutinas"],
        "nutri":   ["Dashboard", "Socios", "Nutrición"],
        "staff":   ["Dashboard", "Socios"],
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
                    padding=ft.padding.symmetric(horizontal=8, vertical=3),
                )
                for p in perms
            ], spacing=4, wrap=True),
        ], spacing=10),
        padding=ft.padding.symmetric(vertical=6),
        border=ft.border.only(bottom=ft.BorderSide(1, Colors.BORDER)),
    )
