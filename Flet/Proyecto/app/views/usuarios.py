# =============================================================================
# views/usuarios.py — Gestión de usuarios del sistema
# =============================================================================
import flet as ft
from app import permisos
from app.config import Colors, NAV_ITEMS, Routes, alpha
from app.state import app_state
from app.components.ui import (build_topbar, status_badge, primary_button, input_field,
                                show_snack, open_dialog, close_dialog)
from app.contacto import ASUNTO_CREDENCIALES, link_mail, link_whatsapp

# rol → (etiqueta, color, fondo translúcido, ícono)
#
# Las CLAVES son los roles que devuelve el backend, no las etiquetas que se
# muestran. Antes eran "admin"/"trainer"/"staff"/"nutri", que no existen en
# ningún lado del sistema: el backend deriva el rol de en qué tabla está la
# persona (Dueno, Entrenador, ...) y devuelve esos nombres. Con las claves
# viejas TODA fila caía en el default y salía como "Desconocido" en gris.
ROLE_CONFIG = {
    "dueno":         ("Dueño",         Colors.PRIMARY_VOLT, alpha(Colors.PRIMARY_VOLT, 0.10), ft.Icons.SHIELD_ROUNDED),
    "entrenador":    ("Entrenador",    Colors.STATUS_OK,    alpha(Colors.STATUS_OK, 0.10),    ft.Icons.FITNESS_CENTER_ROUNDED),
    "recepcionista": ("Recepción",     Colors.ACCENT_CORAL, alpha(Colors.ACCENT_CORAL, 0.10), ft.Icons.SUPPORT_AGENT_ROUNDED),
    "nutricionista": ("Nutricionista", Colors.STATUS_WARN,  alpha(Colors.STATUS_WARN, 0.10),  ft.Icons.RESTAURANT_MENU_ROUNDED),
    "socio":         ("Socio",         Colors.INFO,         alpha(Colors.INFO, 0.10),         ft.Icons.PERSON_ROUNDED),
}

# Secciones que ve cada rol, para la tarjeta informativa de abajo.
#
# SE CALCULA DESDE LA MATRIZ. Antes era un diccionario escrito a mano —una
# CUARTA copia de los permisos, además de app/permisos.py, backend/permisos.py
# y config.ts de la PWA— y estaba mal para los CUATRO roles:
#
#     Recepcionista : decía que veía Actividades (no la ve) y NO mencionaba
#                     Usuarios, Rutinas, Nutrición, Personal ni Recepción
#                     (las ve todas). Era la contradicción más visible: la
#                     pantalla de Usuarios describía permisos que la propia
#                     app no respetaba.
#     Entrenador    : decía Dashboard, Asistencia y Actividades. Ninguna.
#     Nutricionista : decía Dashboard. No la ve.
#     Dueño         : no mencionaba Recepción.
#
# El comentario viejo decía "si las dos se contradicen, manda el backend". Es
# cierto, pero no alcanza: la tarjeta existe para EXPLICARLE a alguien qué
# puede hacer cada rol, y una explicación equivocada es peor que ninguna —
# manda a discutir con la app en vez de leerla.
#
# `check_permisos.py` compara las TRES copias de la matriz entre sí; a esta
# cuarta no la miraba nadie, porque no era una matriz sino una lista suelta.
# Derivarla elimina el problema de raíz: no hay nada que sincronizar.
def _secciones_de(rol: str) -> list[str]:
    """
    Las secciones que ve un rol, leídas de la matriz.

    Marca las de sólo lectura con un asterisco: el Recepcionista "ve Personal"
    y el Entrenador también "ve Socios", pero ninguno de los dos puede tocar
    nada ahí, y una lista que no distingue los dos casos vuelve a explicar mal.
    """
    salida = []
    for item in NAV_ITEMS:
        nivel = permisos.acceso_a_seccion([rol], item["route"])
        if nivel == permisos.Acceso.NINGUNO:
            continue
        salida.append(item["label"] + ("*" if nivel == permisos.Acceso.LECTURA else ""))
    return salida


# El Socio no aparece en NAV_ITEMS —esta app es la del personal— así que su
# resumen se escribe aparte. No es una excepción a la regla de arriba: es que
# sus secciones no existen en este menú.
PERMISOS_RESUMEN = {
    rol: _secciones_de(rol)
    for rol in ("dueno", "recepcionista", "entrenador", "nutricionista")
}
PERMISOS_RESUMEN["socio"] = ["Portal del socio (usa la web, no esta app)"]


class UsuariosView:
    def __init__(self, page: ft.Page, router):
        self.page   = page
        self.router = router

    def build(self) -> ft.Column:
        usuarios = app_state.get_usuarios()

        topbar = build_topbar(
            "Usuarios",
            "Gestión de accesos al sistema",
            # Espejo de UsuariosView.tsx: crear cuentas pide gestionUsuarios.
            actions=[
                primary_button("Nueva Cuenta", ft.Icons.PERSON_ADD_ROUNDED,
                               on_click=self._open_form),
            ] if app_state.puede(permisos.Accion.GESTION_USUARIOS) else []
        )

        # ── Banner de advertencia ────────────────────────────────────────────
        admin_banner = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.SHIELD_ROUNDED, color=Colors.ACCENT, size=18),
                ft.Text("Esta sección es exclusiva para administradores del sistema.",
                        color=Colors.TEXT_SECONDARY, size=13),
            ], spacing=10),
            bgcolor=Colors.ACCENT_GLOW,
            border=ft.Border.all(1, Colors.ACCENT),
            border_radius=10,
            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
        )

        # ── Tabla de usuarios ─────────────────────────────────────────────────
        filas = ([self._user_row(u) for u in usuarios] if usuarios else [
            ft.Container(
                content=ft.Text("No hay cuentas para mostrar.",
                                color=Colors.TEXT_MUTED, size=13),
                padding=ft.Padding.all(24),
                alignment=ft.Alignment.CENTER,
            )
        ])

        table = ft.Container(
            content=ft.Column([
                _table_header(),
                *filas,
            ], spacing=0),
            bgcolor=Colors.BG_CARD,
            border_radius=14,
            border=ft.Border.all(1, Colors.BORDER),
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
            border=ft.Border.all(1, Colors.BORDER),
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
                ], spacing=0, scroll=ft.ScrollMode.AUTO, expand=True),
                padding=ft.Padding.all(24),
                expand=True,
            ),
        ], spacing=0, expand=True)

        return body

    def _user_row(self, u: dict) -> ft.Container:
        role_label, role_color, role_bg, role_icon = ROLE_CONFIG.get(
            u["rol"], ("Sin rol", Colors.TEXT_MUTED, Colors.BG_INPUT, ft.Icons.PERSON_ROUNDED)
        )
        # El nombre puede venir vacío; la inicial se saca del usuario en ese caso
        # para no reventar con un IndexError sobre una cadena vacía.
        etiqueta = u["nombre"] if u["nombre"] not in ("", "—") else u["usuario"]
        initial  = etiqueta[0].upper() if etiqueta else "?"
        activo   = u["estado"] == "Activo"
        bloqueado = u["estado"] == "Bloqueado"

        def on_hover(e: ft.HoverEvent):
            e.control.bgcolor = Colors.BG_INPUT if e.data == "true" else ft.Colors.TRANSPARENT
            e.control.update()

        # ── Las dos reglas de FILA ────────────────────────────────────────
        #
        # No son de sección: el Recepcionista tiene Usuarios en TOTAL y la
        # acción `gestionUsuarios` en true, así que llega acá con permiso para
        # operar. Lo que lo limita es SOBRE QUÉ FILA, y eso no lo puede decir
        # la matriz de permisos — depende de a quién pertenece la cuenta.
        #
        # Las dos las aplica el backend (`_validar_jerarquia` y
        # `_validar_no_es_propia` en routers/usuarios.py) y las dos estaban
        # implementadas en la PWA (`esCuentaDeMayorJerarquia` /
        # `esCuentaPropiaRestringida` en config.ts). Acá NO estaban: la vista
        # dibujaba los tres botones en todas las filas, incluida la del Dueño,
        # y como esa es la PRIMERA de la grilla, el Recepcionista apretaba,
        # recibía un 403 y se iba con la idea de que no podía modificar NADA.
        # Podía: todas las demás.
        #
        # Se OMITEN los botones en vez de deshabilitarlos, igual que en el
        # historial médico: uno gris que no responde no explica por qué.

        # Regla 2 — jerarquía: sólo un Dueño opera sobre la cuenta de un Dueño.
        # Incluye el reseteo, que es justamente el vector de escalación:
        # mostrarle la contraseña temporal del Dueño a un rol inferior le
        # entrega la cuenta entera.
        es_cuenta_protegida = ("dueno" in u.get("roles", [])
                               and not app_state.puede_editar_duenos())

        # Regla 1 — nadie fuera del Dueño se toca a sí mismo. Resetearse la
        # propia contraseña SÍ está permitido (no hay riesgo y es útil), así
        # que esta regla no aplica al botón de la llave.
        es_cuenta_propia = (u.get("usuario") == app_state.get_user_username()
                            and not app_state.puede_editar_duenos())

        # Sin la acción gestionUsuarios la fila es de sólo lectura, sin ningún
        # botón (UsuarioRow.tsx: puedeGestionar).
        puede_gestionar = app_state.puede(permisos.Accion.GESTION_USUARIOS)

        acciones = []

        # Editar usuario y email: fuera de la cuenta propia y de la de un Dueño
        # para un rol inferior (UsuarioRow.tsx: puedeEditarOCambiarEstado).
        if puede_gestionar and not es_cuenta_protegida and not es_cuenta_propia:
            acciones.append(
                ft.IconButton(ft.Icons.EDIT_ROUNDED, icon_color=Colors.INFO,
                              icon_size=18, tooltip="Editar",
                              on_click=lambda e, x=u: self._editar(x))
            )

        if puede_gestionar and not es_cuenta_protegida:
            acciones.append(
                ft.IconButton(ft.Icons.KEY_ROUNDED, icon_color=Colors.WARNING,
                              icon_size=18, tooltip="Resetear contraseña",
                              on_click=lambda e, x=u: self._reset_password(x))
            )

        # El botón de desbloquear sólo aparece si la cuenta está bloqueada. No
        # es una preferencia estética: desbloquear una cuenta que no lo está no
        # hace nada, y tenerlo siempre a la vista invita a apretarlo pensando
        # que "arregla" un problema distinto (una cuenta desactivada, por
        # ejemplo, que se arregla con el botón de al lado).
        if puede_gestionar and bloqueado and not es_cuenta_protegida and not es_cuenta_propia:
            acciones.append(
                ft.IconButton(ft.Icons.LOCK_OPEN_ROUNDED, icon_color=Colors.INFO,
                              icon_size=18, tooltip="Desbloquear",
                              on_click=lambda e, x=u: self._desbloquear(x))
            )

        if puede_gestionar and not es_cuenta_protegida and not es_cuenta_propia:
            acciones.append(
                ft.IconButton(
                    ft.Icons.BLOCK_ROUNDED if activo else ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED,
                    icon_color=Colors.DANGER if activo else Colors.SUCCESS,
                    icon_size=18,
                    tooltip="Desactivar" if activo else "Activar",
                    on_click=lambda e, x=u: self._cambiar_estado(x),
                )
            )

        # Sin botones queda una celda vacía y eso se lee como un error de la
        # app. Se dice por qué, que es la diferencia entre "no se puede" y
        # "algo se rompió".
        if not acciones and puede_gestionar:
            motivo =("Sólo un dueño" if es_cuenta_protegida else "Tu propia cuenta")
            acciones.append(
                ft.Text(motivo, color=Colors.TEXT_MUTED, size=11,
                        tooltip=("Sólo un dueño puede operar sobre la cuenta de "
                                 "un dueño." if es_cuenta_protegida else
                                 "Nadie modifica el estado de su propia cuenta: "
                                 "quedarías afuera del sistema."))
            )

        # Aviso de que todavía no cambió la contraseña inicial. Es informativo
        # y aparece al lado del estado porque es exactamente eso: un estado
        # intermedio entre "cuenta creada" y "cuenta en uso".
        marca_pendiente = ([
            ft.Container(
                content=ft.Text("Clave sin cambiar", color=Colors.STATUS_WARN, size=10),
                bgcolor=alpha(Colors.STATUS_WARN, 0.12),
                border_radius=6,
                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
            )
        ] if u.get("debe_cambiar") else [])

        return ft.Container(
            content=ft.Row([
                ft.Row([
                    ft.Container(
                        content=ft.Text(initial, color=Colors.SURFACE_BASE, size=13,
                                        weight=ft.FontWeight.BOLD),
                        width=32, height=32, border_radius=16,
                        bgcolor=role_color, alignment=ft.Alignment.CENTER,
                    ),
                    ft.Column([
                        ft.Text(etiqueta, color=Colors.TEXT_PRIMARY, size=14),
                        ft.Text(f"@{u['usuario']}", color=Colors.TEXT_MUTED, size=11),
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
                ft.Container(
                    content=ft.Row([status_badge(u["estado"]), *marca_pendiente],
                                   spacing=6, wrap=True),
                    expand=2,
                    alignment=ft.Alignment.CENTER_LEFT,
                ),
                ft.Row(acciones, expand=2),
            ]),
            padding=ft.Padding.symmetric(horizontal=20, vertical=12),
            border=ft.Border.only(bottom=ft.BorderSide(1, Colors.BORDER)),
            on_hover=on_hover,
            animate=ft.Animation(120),
        )

    # ── Acciones ──────────────────────────────────────────────────────────────

    def _open_form(self, e=None):
        """
        Da acceso al sistema a una persona que ya está cargada.

        El formulario cambió de raíz: antes pedía usuario, rol y contraseña
        inicial. Ninguno de los tres se manda ahora.

          - El USUARIO lo arma el backend a partir del nombre.
          - El ROL no es un dato de la cuenta: sale de en qué tabla está la
            persona (Socio, Entrenador, ...). Elegirlo acá habría sido
            inventar un segundo lugar donde vive el rol, con el problema de
            siempre: cuál de los dos gana cuando no coinciden.
          - La CONTRASEÑA la genera el sistema. Que un administrador elija la
            contraseña de otro es peor que una temporal: la conocería para
            siempre, y el dueño de la cuenta no tendría forma de saberlo.

        Por eso lo único que se elige es la persona.
        """
        personas = app_state.get_personas_sin_cuenta()

        if not personas:
            # Mismo texto que UsuarioFormModal.tsx. El viejo ("todas las
            # personas cargadas ya tienen cuenta") era cierto pero no decía
            # dónde se crea una persona, y con la base recién entregada se
            # leía como un error.
            show_snack(self.page,
                       "No hay nadie a quien darle acceso: todas las personas "
                       "cargadas ya tienen cuenta. Las cuentas se crean al dar "
                       "de alta en Socios o Personal.",
                       Colors.INFO)
            return

        persona_ref = ft.Ref[ft.Dropdown]()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Nueva Cuenta de Acceso",
                          color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=420,
                content=ft.Column([
                    ft.Text("Sólo aparecen las personas ya cargadas que todavía "
                            "no tienen acceso al sistema.",
                            color=Colors.TEXT_SECONDARY, size=13),
                    ft.Container(height=14),
                    ft.Dropdown(
                        ref=persona_ref,
                        label="Persona",
                        options=[
                            ft.dropdown.Option(
                                key=str(p["id"]),
                                text=f"{p['nombre']} — DNI {p['dni']}"
                                     + (f" ({', '.join(p['roles'])})" if p["roles"] else ""),
                            )
                            for p in personas
                        ],
                        value=str(personas[0]["id"]),
                        color=Colors.TEXT_PRIMARY, bgcolor=Colors.BG_INPUT,
                        border_color=Colors.BORDER, focused_border_color=Colors.ACCENT,
                        border_radius=10,
                    ),
                    ft.Container(height=12),
                    ft.Row([
                        ft.Icon(ft.Icons.INFO_OUTLINE_ROUNDED,
                                color=Colors.TEXT_MUTED, size=14),
                        ft.Text("El sistema genera usuario y contraseña temporal.\n"
                                "Se muestran una sola vez.",
                                color=Colors.TEXT_MUTED, size=12),
                    ], spacing=6),
                ], spacing=0, tight=True),
            ),
            actions=[
                ft.TextButton("Cancelar",
                              style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                              on_click=lambda e: close_dialog(self.page, dlg)),
                ft.TextButton("Crear cuenta",
                              style=ft.ButtonStyle(color=Colors.ACCENT),
                              on_click=lambda e: self._crear_cuenta(dlg, persona_ref)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(self.page, dlg)

    def _crear_cuenta(self, dlg, persona_ref):
        elegida = persona_ref.current.value if persona_ref.current else None
        if not elegida:
            show_snack(self.page, "Elegí una persona.", Colors.STATUS_DANGER)
            return

        resultado = app_state.crear_cuenta(int(elegida))
        if not resultado["ok"]:
            show_snack(self.page, resultado["mensaje"], Colors.STATUS_DANGER)
            return

        close_dialog(self.page, dlg)
        self._mostrar_credenciales("Cuenta creada", resultado)

    def _editar(self, u: dict):
        """
        Cambia el nombre de usuario y el email (UsuarioFormModal.tsx en edición).

        NO cambia el rol: se deriva de las tablas donde está la persona, así
        que "cambiarlo" acá sería mentir. Para eso se edita su ficha en Personal.
        """
        usuario_tf = input_field("Usuario", "nombre.apellido", icon=ft.Icons.PERSON_ROUNDED,
                                 value=u.get("usuario", ""))
        email_tf = input_field("Email", "correo@ejemplo.com", icon=ft.Icons.EMAIL_OUTLINED,
                               value=u.get("email", ""))

        def guardar(e=None):
            username = (usuario_tf.value or "").strip()
            if not username:
                show_snack(self.page, "El usuario no puede quedar vacío.", Colors.STATUS_DANGER)
                return
            resultado = app_state.editar_usuario(u["id"], username,
                                                 (email_tf.value or "").strip() or None)
            if not resultado["ok"]:
                show_snack(self.page, resultado["mensaje"], Colors.STATUS_DANGER)
                return
            close_dialog(self.page, dlg)
            show_snack(self.page, resultado["mensaje"], Colors.SUCCESS)
            self.router.navigate(Routes.USUARIOS)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Editar cuenta de {u.get('nombre', '')}", color=Colors.TEXT_PRIMARY,
                          weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(width=420, content=ft.Column([
                usuario_tf, email_tf,
                ft.Text("El rol no se cambia acá: sale de la ficha de la persona.",
                        color=Colors.TEXT_MUTED, size=11),
            ], spacing=12, tight=True)),
            actions=[
                ft.TextButton("Cancelar", style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                              on_click=lambda e: close_dialog(self.page, dlg)),
                ft.TextButton("Guardar", style=ft.ButtonStyle(color=Colors.ACCENT), on_click=guardar),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(self.page, dlg)

    def _reset_password(self, u: dict):
        """
        Resetea la contraseña. Pide confirmación antes porque el reseteo deja
        la cuenta afuera: la contraseña vieja deja de servir en el acto, así
        que apretarlo por error a la persona equivocada la desconecta hasta
        que alguien le dicte la nueva.
        """
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Resetear Contraseña",
                          color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=380,
                content=ft.Column([
                    ft.Text(f"Se va a generar una contraseña temporal para "
                            f"@{u['usuario']}.",
                            color=Colors.TEXT_SECONDARY, size=13),
                    ft.Container(height=8),
                    ft.Text("La contraseña actual deja de funcionar de inmediato "
                            "y habrá que dictarle la nueva.",
                            color=Colors.STATUS_WARN, size=12),
                ], spacing=0, tight=True),
            ),
            actions=[
                ft.TextButton("Cancelar",
                              style=ft.ButtonStyle(color=Colors.TEXT_SECONDARY),
                              on_click=lambda e: close_dialog(self.page, dlg)),
                ft.TextButton("Resetear",
                              style=ft.ButtonStyle(color=Colors.WARNING),
                              on_click=lambda e: self._confirmar_reset(dlg, u)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        open_dialog(self.page, dlg)

    def _confirmar_reset(self, dlg, u: dict):
        resultado = app_state.resetear_password_usuario(u["id"])
        if not resultado["ok"]:
            show_snack(self.page, resultado["mensaje"], Colors.STATUS_DANGER)
            return
        close_dialog(self.page, dlg)
        # El mail y el teléfono salen de la fila de la tabla: el endpoint de
        # reseteo devuelve las credenciales, no a dónde mandarlas.
        self._mostrar_credenciales("Contraseña reseteada", resultado,
                                   email=u.get("email", ""),
                                   telefono=u.get("telefono", ""))

    def _desbloquear(self, u: dict):
        resultado = app_state.desbloquear_usuario(u["id"])
        show_snack(self.page, resultado["mensaje"],
                   Colors.SUCCESS if resultado["ok"] else Colors.STATUS_DANGER)
        if resultado["ok"]:
            self.router.navigate(Routes.USUARIOS)

    def _cambiar_estado(self, u: dict):
        """
        Activa o desactiva la cuenta.

        Se manda el estado DESTINO y no un "invertí lo que haya": desactivar
        una cuenta es la única forma de cortar una sesión en curso, y si dos
        personas desactivan la misma cuenta comprometida a la vez, un toggle
        haría que el segundo click la reactive.
        """
        destino = u["estado"] != "Activo"
        resultado = app_state.cambiar_estado_usuario(u["id"], destino)
        show_snack(self.page, resultado["mensaje"],
                   Colors.SUCCESS if resultado["ok"] else Colors.STATUS_DANGER)
        if resultado["ok"]:
            self.router.navigate(Routes.USUARIOS)

    def _mostrar_credenciales(self, titulo: str, resultado: dict,
                              email: str = "", telefono: str = ""):
        """
        Muestra usuario y contraseña temporal, y ofrece MANDARLAS.

        Va en un diálogo con botón y no en un snack que se va solo: en la base
        queda únicamente el hash, así que esta es la única vez que la
        contraseña existe legible. Si se pierde, hay que resetearla de nuevo.

        Los botones de envío son los mismos que el alta de personal
        (personal.py): abren el mail o el WhatsApp con el mensaje ya escrito.
        Antes el reseteo sólo mostraba la clave y había que pasarla a mano.
        Gemelo de PanelCredenciales.tsx.
        """
        texto = resultado.get("texto_credenciales") or (
            f"Usuario: {resultado.get('usuario', '—')} — "
            f"Contraseña temporal: {resultado.get('password_temporal', '—')}")

        # El mail primero cuando existe; si sólo dejó teléfono, WhatsApp es la
        # única vía. Misma regla que el alta y que el botón "Contactar".
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
            title=ft.Text(titulo, color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.BG_CARD,
            content=ft.Container(
                width=380,
                content=ft.Column([
                    ft.Text(resultado.get("mensaje", ""),
                            color=Colors.TEXT_SECONDARY, size=13),
                    ft.Container(height=12),
                    ft.Text(f"Usuario: {resultado.get('usuario', '—')}",
                            color=Colors.TEXT_PRIMARY, size=14,
                            weight=ft.FontWeight.BOLD, selectable=True),
                    ft.Text(f"Contraseña temporal: {resultado.get('password_temporal', '—')}",
                            color=Colors.PRIMARY_VOLT, size=14,
                            weight=ft.FontWeight.BOLD, selectable=True),
                    ft.Container(height=12),
                    ft.Text("Anotala ahora: no se puede volver a ver. "
                            "Se la va a pedir cambiar al entrar.",
                            color=Colors.STATUS_WARN, size=12),
                ], spacing=0, tight=True),
            ),
            actions=[
                *envios,
                ft.TextButton("Listo",
                              style=ft.ButtonStyle(color=Colors.ACCENT),
                              on_click=lambda e: (close_dialog(self.page, dlg),
                                                  self.router.navigate(Routes.USUARIOS))),
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
        padding=ft.Padding.symmetric(horizontal=20, vertical=14),
        bgcolor=Colors.BG_SIDEBAR,
    )


def _perms_row(rol: str, cfg: tuple) -> ft.Container:
    label, color, bg, icon = cfg
    perms = PERMISOS_RESUMEN.get(rol, [])
    return ft.Container(
        content=ft.Row([
            ft.Container(
                content=ft.Icon(icon, color=color, size=16),
                width=30, height=30, border_radius=8,
                bgcolor=bg, alignment=ft.Alignment.CENTER,
            ),
            ft.Column([
                ft.Text(label, color=Colors.TEXT_PRIMARY, size=13,
                        weight=ft.FontWeight.W_500),
                ft.Text(", ".join(perms), color=Colors.TEXT_MUTED, size=11),
            ], spacing=2, tight=True, expand=True),
        ], spacing=12),
        padding=ft.Padding.symmetric(vertical=6),
    )
