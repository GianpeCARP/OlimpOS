"""
Pantalla para quien entra a la app de escritorio y no tiene NINGUNA sección.

Hoy el único caso real es el PROFESOR. Tiene cuenta —la necesita para "Mis
clases"—, pero esa pantalla vive en la PWA: en la matriz de permisos de Flet
todas sus secciones están en NINGUNO, a propósito, porque la app de escritorio
es la PC del mostrador y un profesor no atiende el mostrador.

QUÉ PASABA ANTES
----------------
`primera_seccion()` devolvía None y `_load_main_app` caía al Dashboard, que el
profesor tampoco puede ver: entraba bien, el login decía que sí, y quedaba
mirando una pantalla vacía sin ninguna explicación. Parecía la app rota.

No es un error ni un permiso mal puesto, así que no se pinta como tal: se le
dice dónde está su pantalla. El sistema informa, no juzga.

No tiene gemelo en la PWA y no es un olvido: en la PWA el profesor SÍ tiene su
sección, que es justamente la que este cartel le indica.
"""
import flet as ft

from app.config import Colors, Fonts, Radius
from app.state import app_state


class SinSeccionesView:
    """Misma forma que el resto de las vistas (page, router, .build())."""

    def __init__(self, page: ft.Page, router):
        self.page = page
        self.router = router

    def build(self) -> ft.Column:
        nombre = (app_state.get_user_name() or "").strip()
        saludo = f"Hola {nombre}." if nombre else "Hola."

        tarjeta = ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.PHONE_IPHONE_ROUNDED,
                        color=Colors.PRIMARY_VOLT, size=44),
                ft.Container(height=6),
                ft.Text(saludo, color=Colors.TEXT_MAIN, size=20,
                        weight=ft.FontWeight.BOLD, font_family=Fonts.TITLE,
                        text_align=ft.TextAlign.CENTER),
                ft.Text("Tu pantalla está en la app del celular.",
                        color=Colors.TEXT_SECONDARY, size=15,
                        font_family=Fonts.BODY,
                        text_align=ft.TextAlign.CENTER),
                ft.Container(height=10),
                ft.Text(
                    "Esta computadora es la del mostrador: sirve para cobrar, "
                    "fichar y administrar socios. Tus clases, con quiénes se "
                    "anotaron y a qué hora, las ves entrando con el mismo "
                    "usuario y la misma contraseña desde el navegador del "
                    "celular, en OlimpOS.",
                    color=Colors.TEXT_MUTED, size=13, font_family=Fonts.BODY,
                    text_align=ft.TextAlign.CENTER),
                ft.Container(height=14),
                ft.Text("Si creés que te falta un permiso, avisale al dueño.",
                        color=Colors.TEXT_MUTED, size=12,
                        font_family=Fonts.BODY,
                        text_align=ft.TextAlign.CENTER),
            ],
                spacing=4,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            width=520,
            padding=36,
            bgcolor=Colors.BG_CARD,
            border=ft.Border.all(1, Colors.BORDER_IDLE),
            border_radius=Radius.MD,
        )

        # Centrada en el lienzo: no hay barra de título porque no hay sección
        # que titular, y un topbar vacío arriba de un cartel se lee como un
        # error de la app.
        return ft.Column(
            [ft.Row([tarjeta], alignment=ft.MainAxisAlignment.CENTER)],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )
