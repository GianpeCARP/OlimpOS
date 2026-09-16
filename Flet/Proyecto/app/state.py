# =============================================================================
# state.py — Estado global de la aplicación
# =============================================================================
# Patrón "estado centralizado" (similar a un store). AppState es la única
# fuente de verdad sobre la sesión activa y los datos mostrados en la UI.
# La instancia global `app_state` se importa desde cualquier parte de la app.
#
# Capa intermedia entre las vistas y api_client.py. Las vistas NO saben que
# existe HTTP: piden datos acá y reciben diccionarios listos para dibujar.
# Gemelo de los `services/*.ts` de la PWA.
#
# TODO el estado sale de la API real (FastAPI). No queda ni un dato inventado.
#
# Cuando un pedido falla, los getters devuelven una lista vacía en vez de
# propagar el error: una grilla vacía con su cartel de "todavía no hay nada"
# es mejor que una pantalla que explota porque el backend está apagado.

from datetime import date, datetime, timedelta

from app import api_client, permisos
from app.config import NAV_ITEMS

# Método de pago: el enum del esquema en un lado, la etiqueta que ve el
# usuario en el otro. Los dos sentidos, porque las pantallas muestran
# "Billetera virtual" y el backend espera "BILLETERA_VIRTUAL".
METODO_PAGO_DISPLAY = {
    "EFECTIVO": "Efectivo",
    "DEBITO": "Débito",
    "CREDITO": "Crédito",
    "TRANSFERENCIA": "Transferencia",
    "BILLETERA_VIRTUAL": "Billetera virtual",
}
METODO_PAGO_BACKEND = {v: k for k, v in METODO_PAGO_DISPLAY.items()}


class AppState:
    """Estado centralizado de la aplicación."""

    def __init__(self):
        # ── Sesión de usuario ────────────────────────────────────────────────

        # Indica si hay un usuario autenticado. El router lo consulta como guard.
        self.logged_in: bool = False

        # Datos del usuario actual: username, name, roles, avatar, id_socio.
        # Es None si no hay sesión activa.
        self.current_user: dict | None = None

        # Ruta actualmente activa; permite saber en qué sección está el usuario.
        self.current_route: str = "login"

        # Username que quedó pendiente de cambiar su contraseña. Lo escribe
        # login() cuando la API contesta debe_cambiar_password, y lo lee la
        # pantalla de cambio obligatorio para no volver a pedirlo. En ese
        # momento NO hay sesión ni token: la API negó el acceso a propósito.
        self.username_pendiente_cambio: str | None = None

        # Socio a abrir en Cobros al entrar. Lo escribe el alta de socio con
        # "Cobrar ahora" y lo consume CobrosView en su __init__, que lo vuelve
        # a None. Vive acá y no como argumento de navigate() porque el router
        # sólo recibe la ruta. Gemelo del ?socio=<id> de la PWA.
        self.socio_a_cobrar: int | None = None

    # ── Autenticación ─────────────────────────────────────────────────────────

    def login(self, username: str, password: str) -> dict:
        """
        Autentica contra POST /login.

        Devuelve un diccionario con tres formas posibles, porque el login real
        tiene tres desenlaces y no dos:

            {"ok": False, "mensaje": "..."}      credenciales mal, o red caída
            {"ok": True,  "requiere_cambio": True}   contraseña temporal
            {"ok": True,  "requiere_cambio": False}  sesión abierta

        El caso del medio es el que no existía con los datos mock: la API
        verifica la contraseña, confirma que es correcta, y AUN ASÍ no emite
        token — la cuenta tiene que definir una contraseña propia primero.
        """
        resultado = api_client.login(username, password)

        if not resultado["ok"]:
            return {"ok": False, "mensaje": resultado["error"]}

        datos = resultado["data"]

        if datos.get("debe_cambiar_password"):
            # Se guarda el username, no la contraseña: la pantalla de cambio
            # vuelve a pedir la actual, que es la forma de confirmar que quien
            # está cambiando la clave es quien la conocía.
            self.username_pendiente_cambio = username
            return {"ok": True, "requiere_cambio": True}

        roles = datos.get("roles", [])

        # Las credenciales son válidas, pero esta app es la del PERSONAL.
        #
        # Un socio se autentica perfectamente —su cuenta existe y la
        # contraseña es correcta— y sin este corte entraría a un sidebar vacío
        # y una pantalla en blanco, sin ninguna explicación. Se lo frena acá y
        # se le dice dónde tiene que ir.
        #
        # El token NO se guarda en este caso: si se guardara, la sesión
        # quedaría abierta en el cliente aunque la pantalla dijera que no
        # entró.
        if not permisos.tiene_acceso_a_la_app(roles):
            return {
                "ok": False,
                "mensaje": "Esta aplicación es para el personal del gimnasio. "
                           "Si sos socio, entrá desde la web con estas mismas "
                           "credenciales.",
            }

        api_client.guardar_token(datos["token"])

        persona = datos.get("persona") or {}
        nombre = f"{persona.get('nombre', '')} {persona.get('apellido', '')}".strip()

        self.logged_in = True
        self.current_user = {
            "username": datos["usuario"]["username"],
            "name": nombre or datos["usuario"]["username"],
            # Lista, no string: los roles se acumulan (el dueño que además es
            # socio del gimnasio tiene los dos).
            "roles": roles,
            "avatar": (nombre or "U")[0].upper(),
            "id_socio": datos.get("idSocio"),
            # Para las reglas de FILA propia (nadie se da de baja a sí mismo
            # en Personal). Espejo de `persona.id_persona` del authStore.
            "id_persona": (datos.get("persona") or {}).get("id_persona"),
        }
        self.username_pendiente_cambio = None

        # Traer en paralelo lo que las pantallas van a pedir. No bloquea: la
        # sesion se abre igual y los datos van llegando al cache mientras la
        # persona mira la primera pantalla. Es lo que hace que la primera
        # visita a cada panel tambien sea instantanea y no solo las siguientes.
        api_client.precargar()

        return {"ok": True, "requiere_cambio": False}

    def cambiar_password(self, password_actual: str, password_nueva: str) -> dict:
        """
        Define la contraseña definitiva de la cuenta que quedó pendiente.

        No abre sesión al terminar, a propósito: la persona vuelve al login y
        entra de nuevo. Así el primer uso de la contraseña nueva es un login
        normal y queda probada antes de que nadie dependa de ella.
        """
        if not self.username_pendiente_cambio:
            return {"ok": False,
                    "mensaje": "No hay ninguna cuenta pendiente de cambio de contraseña."}

        resultado = api_client.cambiar_password(
            self.username_pendiente_cambio, password_actual, password_nueva
        )

        if not resultado["ok"]:
            return {"ok": False, "mensaje": resultado["error"]}

        self.username_pendiente_cambio = None
        return {"ok": True}

    def logout(self):
        """
        Cierra la sesión. Limpiar el token es imprescindible: sin eso, la
        sesión siguiente heredaría el del usuario anterior.
        """
        api_client.limpiar_token()
        self.logged_in = False
        self.current_user = None
        self.current_route = "login"
        self.username_pendiente_cambio = None

    # ── Getters de sesión ─────────────────────────────────────────────────────
    # Acceso seguro a los datos del usuario activo, con valores por defecto si
    # no hay sesión (evitan errores de None en las vistas).

    def get_user_name(self) -> str:
        """Nombre para mostrar del usuario activo, o 'Invitado'."""
        if self.current_user:
            return self.current_user.get("name", "Usuario")
        return "Invitado"

    def get_user_id_persona(self) -> int | None:
        if self.current_user:
            return self.current_user.get("id_persona")
        return None

    def get_user_roles(self) -> list[str]:
        """Roles de la sesión activa. Lista vacía si no hay sesión."""
        if self.current_user:
            return self.current_user.get("roles", [])
        return []

    def get_user_role(self) -> str:
        """
        Rol principal, para lo que necesita mostrar UNO solo (el subtítulo del
        sidebar, por ejemplo). Las decisiones de permiso tienen que usar
        get_user_roles(), que no pierde información.
        """
        roles = self.get_user_roles()
        return roles[0] if roles else "guest"

    def get_user_avatar(self) -> str:
        """Inicial del avatar del usuario activo, o 'U'."""
        if self.current_user:
            return self.current_user.get("avatar", "U")
        return "U"

    # ── Permisos ──────────────────────────────────────────────────────────────
    #
    # Reemplazan al viejo is_admin(), que era un booleano provisorio: devolvía
    # True para dueño y recepcionista y False para todos los demás. Con eso no
    # se podía expresar lo que la matriz sí expresa — que un Entrenador LEE
    # Nutrición pero no la gestiona, o que un Recepcionista ve Personal sin
    # poder dar de alta a nadie. Un booleano no tiene forma de decir "puede
    # mirar pero no tocar", así que la app terminaba mostrando todo o nada.
    #
    # Estos métodos son sólo la puerta de entrada a app/permisos.py; la tabla
    # vive ahí y es el espejo de config.ts y de backend/permisos.py.

    def puede_ver(self, seccion: str) -> bool:
        """¿La sesión puede abrir esta sección, aunque sea para mirar?"""
        return permisos.puede_ver(self.get_user_roles(), seccion)

    def puede_editar(self, seccion: str) -> bool:
        """¿Puede además modificar lo que hay adentro?"""
        return permisos.puede_editar(self.get_user_roles(), seccion)

    def puede(self, accion: str) -> bool:
        """¿Puede ejecutar esta acción puntual? (dar de alta, cobrar, ...)"""
        return permisos.puede_accion(self.get_user_roles(), accion)

    def get_user_username(self) -> str:
        """El username de la sesión, para las reglas de FILA de Usuarios."""
        if self.current_user:
            return self.current_user.get("username", "")
        return ""

    def puede_editar_duenos(self) -> bool:
        """
        ¿Esta sesión puede operar sobre la cuenta de un Dueño?

        Sólo un Dueño. Es una regla de FILA y no de sección, así que no vive en
        la matriz de permisos: el Recepcionista tiene Usuarios en TOTAL y la
        acción `gestionUsuarios` en true, y aun así no puede tocar esa cuenta.
        Lo que lo limita es de quién es la fila, y eso la matriz no lo sabe.

        Espejo de `esCuentaDeMayorJerarquia` en config.ts de la PWA, y de
        `_validar_jerarquia` en backend/routers/usuarios.py — que es el que de
        verdad lo impide. Esto sólo decide qué se DIBUJA.
        """
        return permisos.Rol.DUENO in self.get_user_roles()

    def secciones_visibles(self) -> list[str]:
        """Las rutas que esta sesión puede abrir. La usa el sidebar."""
        return [item["route"] for item in NAV_ITEMS
                if permisos.puede_ver(self.get_user_roles(), item["route"])]

    # A qué pantalla mandar a cada rol al entrar, cuando la primera del menú no
    # es la que esa persona realmente usa.
    #
    # El Recepcionista tiene acceso al Dashboard, así que sin esto aterrizaría
    # ahí: un resumen de métricas del negocio que no le sirve para trabajar.
    # Lo que necesita ver apenas abre la app es quién está por llegar. Es la
    # diferencia entre una pantalla que se mira una vez por día y la que se
    # mira todo el día.
    #
    # El Dueño NO está en este mapa a propósito: para él el Dashboard sí es la
    # pantalla correcta — mira el negocio, no el mostrador.
    ATERRIZAJE = {
        permisos.Rol.RECEPCIONISTA: permisos.Routes.RECEPCION,
    }

    def primera_seccion(self) -> str | None:
        """
        A dónde mandar a alguien recién logueado.

        No siempre es el Dashboard: un Entrenador lo tiene en NINGUNO, así que
        aterrizaría en una pantalla que no puede ver. Y un Recepcionista sí lo
        tiene, pero no es donde trabaja — ver ATERRIZAJE.
        """
        visibles = self.secciones_visibles()
        if not visibles:
            return None

        # Si alguno de sus roles tiene un aterrizaje propio y puede verlo,
        # gana ese. Se recorre en el orden de ATERRIZAJE y no en el de los
        # roles: alguien que sea recepcionista Y otra cosa tiene que caer
        # igual en el mostrador.
        for rol, destino in self.ATERRIZAJE.items():
            if rol in self.get_user_roles() and destino in visibles:
                return destino

        return visibles[0]

    # ── Traductores de formato ────────────────────────────────────────────────
    # El backend habla ISO (2026-08-11) porque es lo que ordena y compara bien.
    # Las pantallas muestran dd/mm/aaaa porque es lo que lee una persona. La
    # traducción vive acá y no en cada vista: si mañana se muestra distinto, se
    # cambia en un lugar.

    @staticmethod
    def _fecha(iso: str | None) -> str:
        """'2026-08-11' -> '11/08/2026'. Devuelve '—' si no hay fecha."""
        if not iso:
            return "—"
        try:
            return datetime.strptime(iso[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            return str(iso)

    @staticmethod
    def _hora(iso: str | None) -> str:
        """'2026-08-11T19:42:03' -> '19:42'."""
        if not iso:
            return "—"
        try:
            return datetime.fromisoformat(iso).strftime("%H:%M")
        except (ValueError, TypeError):
            return str(iso)[11:16]

    @staticmethod
    def _hace_cuanto(iso: str | None) -> str:
        """
        Fecha absoluta a texto relativo: 'hace 4 días', 'dentro de 6 días'.

        El backend manda la fecha cruda y no el texto armado a propósito: el
        texto es presentación, y las dos apps lo redactan igual pero cada una
        en su idioma de UI. Mandar "hace 4 días" desde el servidor obligaría a
        que el servidor supiera en qué idioma está la pantalla.
        """
        if not iso:
            return ""
        try:
            momento = datetime.fromisoformat(iso)
        except (ValueError, TypeError):
            return ""

        dias = (momento.date() - datetime.now().date()).days
        if dias == 0:
            return "hoy"
        if dias == 1:
            return "mañana"
        if dias == -1:
            return "ayer"
        if dias > 0:
            return f"dentro de {dias} días"
        return f"hace {abs(dias)} días"

    @staticmethod
    def _datos(resultado: dict, por_defecto):
        """
        Extrae `data` de una respuesta del api_client, o el default si falló.

        Las vistas NO reciben el error: reciben una lista vacía y muestran su
        estado vacío ("Todavía no hay socios cargados"). Es deliberado — una
        grilla que explota porque el backend está apagado es peor que una
        grilla vacía, y la pantalla de login ya avisa cuando no hay conexión.
        """
        return resultado["data"] if resultado.get("ok") else por_defecto

    # ── Socios ────────────────────────────────────────────────────────────────

    def get_socios(self) -> list[dict]:
        """
        Lista de socios para la grilla.

        El `estado` y el `plan` YA VIENEN resueltos del backend: se derivan de
        la membresía vigente, y esa regla —los 7 días de aviso, que "dado de
        baja" gane sobre "vencido"— tiene que valer igual acá, en la PWA y en
        cualquier reporte. Derivarla en cada cliente sería mantenerla en tres
        lugares.
        """
        datos = self._datos(api_client.obtener_socios(), [])
        return [
            {
                "id": s["id_socio"],
                "nombre": f"{s['nombre']} {s['apellido']}".strip(),
                "plan": s.get("plan") or "Sin plan",
                "estado": s.get("estado") or "Sin membresía",
                "vence": self._fecha(s.get("vencimiento")),
                # Igual que en get_personal: estos no se muestran en la grilla,
                # los necesita el formulario de edición para precargarse. Sin
                # ellos, guardar una edición borraría el mail y el teléfono.
                "nombre_pila": s["nombre"],
                "apellido": s["apellido"],
                "dni": s.get("dni", ""),
                "email": s.get("email") or "",
                "telefono": s.get("telefono") or "",
                "objetivo": s.get("objetivo") or "",
                "observaciones": s.get("observaciones") or "",
                # Datos personales y contacto de emergencia (gemelo de
                # SocioListado en sociosService.ts). La fecha se precarga como
                # dd/mm/aaaa, que es como se tipea en el formulario.
                "fecha_nacimiento": self._fecha(s.get("fecha_nacimiento"))
                                    if s.get("fecha_nacimiento") else "",
                "calle": s.get("calle") or "",
                "numero_calle": s.get("numero_calle") or "",
                "localidad": s.get("localidad") or "",
                "emergencia_nombre": s.get("emergencia_nombre") or "",
                "emergencia_telefono": s.get("emergencia_telefono") or "",
                "emergencia_parentesco": s.get("emergencia_parentesco") or "",
                # Baja PROGRAMADA (backend/bajas.py): sigue activo hasta ese día.
                "baja_programada": self._fecha(s.get("baja_programada"))
                                   if s.get("baja_programada") else "",
                "activo": s.get("activo", True),
            }
            for s in datos
        ]

    def editar_socio(self, id_socio: int, datos: dict) -> dict:
        return self._resultado(api_client.editar_socio(id_socio, datos),
                                "Socio actualizado.")

    # ── Personal ──────────────────────────────────────────────────────────────

    def get_personal(self) -> list[dict]:
        """
        Lista de empleados.

        El `rol` no es una columna: el backend lo deriva de en cuál de las
        cuatro tablas hijas de Empleado está la persona. Y `turno` solo existe
        para el Recepcionista, así que para el resto viene vacío — se muestra
        un guion en vez de dejar la celda en blanco.
        """
        datos = self._datos(api_client.obtener_personal(), [])
        return [
            {
                "id": e["id_empleado"],
                "id_persona": e.get("id_persona"),
                "activo": bool(e.get("activo")),
                "nombre": f"{e['nombre']} {e['apellido']}".strip(),
                "rol": e.get("rol") or "Sin asignar",
                "turno": e.get("turno_laboral") or "—",
                "estado": "Activo" if e.get("activo") else "Inactivo",
                # Los de abajo no se muestran en la tarjeta: los necesita el
                # formulario de edición para precargarse. Si no viajaran acá,
                # abrir "Editar" arrancaría con los campos vacíos y guardar
                # borraría el mail y la matrícula de alguien sin querer.
                "nombre_pila": e["nombre"],
                "apellido": e["apellido"],
                "dni": e.get("dni", ""),
                "email": e.get("email") or "",
                # El backend lo devuelve aplanado desde la tabla Telefono. Sin
                # esto, editar un empleado reabría el campo vacío y guardar de
                # nuevo le borraba el teléfono.
                "telefono": e.get("telefono") or "",
                "titulo": e.get("titulo") or "",
                "especialidad": e.get("especialidad") or "",
                "matricula": e.get("matricula") or "",
                "turno_laboral": e.get("turno_laboral") or "",
                "id_franja_laboral": e.get("id_franja_laboral"),
            }
            for e in datos
        ]

    def get_franjas(self) -> list[dict]:
        """
        Catálogo de franjas laborales, para el selector de turno del
        recepcionista. Reemplaza al viejo enum de turnos hardcodeado.
        """
        datos = self._datos(api_client.obtener_franjas(), [])
        return [{"id": f["id_franja_laboral"], "nombre": f["nombre"]} for f in datos]

    # ── Rutinas ───────────────────────────────────────────────────────────────

    def get_rutinas(self) -> list[dict]:
        """
        Catálogo de rutinas.

        `duracion` no existe en el esquema —Rutina solo tiene `objetivo` como
        texto libre— así que se arma a partir de los días por semana. Es la
        misma decisión que tomó la PWA: inventar una columna en la base para
        un dato de presentación habría sido peor.
        """
        datos = self._datos(api_client.obtener_rutinas(), [])
        return [
            {
                "id": r["id_rutina"],
                "nombre": r["nombre"],
                "dias": r.get("dias_por_semana") or 0,
                "duracion": r.get("objetivo") or "—",
                "asignados": r.get("asignados", 0),
                "objetivo": r.get("objetivo") or "",
                "id_entrenador": r.get("id_entrenador"),
                "entrenador": r.get("entrenador") or "—",
                "activo": r.get("activo", True),
                # Lo decide el backend: un Entrenador ve las rutinas de sus
                # colegas pero no las edita, ni las da de baja, ni las asigna.
                "puede_editar": r.get("puede_editar", True),
            }
            for r in datos
        ]

    def get_rutina(self, id_rutina: int) -> dict | None:
        """El detalle, CON la planilla de ejercicios (el listado no la trae)."""
        r = self._datos(api_client.obtener_rutina(id_rutina), None)
        if not r:
            return None
        return {
            "id": r["id_rutina"],
            "nombre": r["nombre"],
            "dias": r.get("dias_por_semana") or 1,
            "objetivo": r.get("objetivo") or "",
            "id_entrenador": r.get("id_entrenador"),
            "entrenador": r.get("entrenador") or "—",
            "asignados": r.get("asignados", 0),
            "activo": r.get("activo", True),
            "puede_editar": r.get("puede_editar", True),
            "ejercicios": [
                {
                    "id_ejercicio": e["id_ejercicio"],
                    "nombre": e["nombre_ejercicio"],
                    "grupo": e.get("grupo_muscular") or "—",
                    "dia": e["dia"],
                    "orden": e["orden"],
                    "series": e.get("series"),
                    "repeticiones": e.get("repeticiones"),
                    "peso": e.get("peso_sugerido"),
                    "descanso": e.get("descanso_segundos"),
                    "observaciones": e.get("observaciones"),
                    "video": e.get("video_local"),
                }
                for e in r.get("ejercicios", [])
            ],
        }

    # ── Nutrición ─────────────────────────────────────────────────────────────

    def get_planes_nutricion(self) -> list[dict]:
        datos = self._datos(api_client.obtener_dietas(), [])
        return [
            {
                "id": d["id_dieta"],
                "nombre": d["nombre"],
                "calorias": d.get("calorias_diarias") or 0,
                "objetivo": d.get("objetivo") or "—",
                "asignados": d.get("asignados", 0),
                "descripcion": d.get("descripcion") or "",
                "id_nutricionista": d.get("id_nutricionista"),
                "nutricionista": d.get("nutricionista") or "—",
                "activo": d.get("activo", True),
                # Lo decide el backend: un Nutricionista ve los planes de sus
                # colegas pero no los edita, ni los da de baja, ni los asigna.
                "puede_editar": d.get("puede_editar", True),
            }
            for d in datos
        ]

    def get_platos(self) -> list[dict]:
        """Catálogo de platos: de acá salen nombre y calorías de cada comida."""
        datos = self._datos(api_client.obtener_catalogo_comidas(), [])
        return [{"id": p["id_catalogo_comida"], "nombre": p["nombre"],
                 "calorias": p.get("calorias"), "descripcion": p.get("descripcion") or ""}
                for p in datos]

    def crear_plato(self, datos: dict) -> dict:
        return self._resultado(api_client.crear_plato(datos), "Plato agregado al catálogo.")

    def editar_usuario(self, id_usuario: int, username: str, email: str | None) -> dict:
        return self._resultado(api_client.editar_usuario(id_usuario, username, email),
                                "Cuenta actualizada.")

    def get_comidas_dieta(self, id_dieta: int) -> list[dict] | None:
        """
        Las comidas reales del plan, ya ordenadas por día y momento (el orden lo
        pone el backend: alfabético pondría Almuerzo antes que Desayuno).
        None si no se pudo traer.
        """
        d = self._datos(api_client.obtener_dieta(id_dieta), None)
        if d is None:
            return None
        return [
            {"dia": c.get("dia"), "momento": c.get("momento") or "",
             "id_catalogo_comida": c.get("id_catalogo_comida"),
             "nombre": c.get("nombre") or "", "descripcion": c.get("descripcion") or "",
             "calorias": c.get("calorias")}
            for c in d.get("comidas", [])
        ]

    def editar_dieta(self, id_dieta: int, datos: dict) -> dict:
        return self._resultado(api_client.editar_dieta(id_dieta, datos), "Plan actualizado.")

    def baja_dieta(self, id_dieta: int) -> dict:
        return self._resultado(api_client.baja_dieta(id_dieta), "Plan dado de baja.")

    def reactivar_dieta(self, id_dieta: int) -> dict:
        return self._resultado(api_client.reactivar_dieta(id_dieta), "Plan reactivado.")

    # ── Dashboard ─────────────────────────────────────────────────────────────

    def get_ingresos_por_periodo(self, escala: str = "dia") -> dict:
        """
        Ingresos agrupados para el gráfico del dashboard (sólo el Dueño).

        Si el pedido falla devuelve una forma vacía y NO None: la vista hace
        cuentas con los puntos (el máximo, la altura de cada barra), y con None
        reventaría al construirse — la trampa 7 del CLAUDE.md.
        """
        datos = self._datos(api_client.obtener_ingresos_por_periodo(escala), None)
        if not datos:
            return {"total": 0, "puntos": []}
        return {
            "total": datos.get("total", 0),
            "puntos": [{"etiqueta": p.get("etiqueta", ""), "monto": p.get("monto", 0)}
                       for p in datos.get("puntos", [])],
        }

    def get_dashboard_stats(self) -> dict:
        """
        Las cuatro métricas de la portada.

        `delta_pct` puede venir None cuando el mes anterior fue cero: dividir
        daría infinito, y mostrar "+100%" al pasar de 0 a 1 socio sería
        inventar un dato. La vista, con None, no dibuja el delta.

        Ojo: `ingresos_mes` llega en 0 para quien no tiene el permiso de ver
        ingresos. El backend devuelve cero en vez de omitir el campo para no
        romper el contrato de la pantalla, que espera las cuatro métricas.
        """
        vacio = {"valor": 0, "delta_pct": None}
        datos = self._datos(api_client.obtener_dashboard_stats(), None)
        if not datos:
            return {k: dict(vacio) for k in
                    ("socios_activos", "ingresos_mes", "clases_hoy", "nuevos_mes")}

        def metrica(clave: str) -> dict:
            m = datos.get(clave) or {}
            return {"valor": m.get("valor", 0), "delta_pct": m.get("deltaPorcentual")}

        return {
            "socios_activos": metrica("sociosActivos"),
            "ingresos_mes": metrica("ingresosMes"),
            "clases_hoy": metrica("clasesHoy"),
            "nuevos_mes": metrica("nuevosMes"),
        }

    def get_socios_recientes(self) -> list[dict]:
        """
        Los últimos socios, para la tarjeta del Dashboard.

        Endpoint DEDICADO y no `get_socios()[:4]`, que es lo que hacía esta
        pantalla: traerse la grilla entera para mostrar cuatro filas costaba un
        pedido de ~0,9s sobre los tres que ya hace el Dashboard, y era el que
        más pesaba en el 1,8s que tardaba en abrir.

        `/dashboard/socios-recientes` ya existía y la PWA ya lo usaba
        (dashboardService.ts). Acá estaba sin usar: otra asimetría entre
        gemelas, no una decisión.
        """
        datos = self._datos(api_client.obtener_socios_recientes(), [])
        return [
            {
                "id": s.get("idSocio"),
                "nombre": s.get("nombre", "—"),
                "plan": s.get("plan", "Sin plan"),
                "estado": s.get("estado", "—"),
            }
            for s in datos
        ]

    def get_actividad_reciente(self) -> list[dict]:
        """
        Feed del dashboard. El backend manda la fecha cruda y acá se convierte
        a "hace 4 días" — ver _hace_cuanto.
        """
        datos = self._datos(api_client.obtener_actividad_reciente(), [])
        return [
            {
                # El backend ya manda el tipo en la forma que la vista usa para
                # elegir el ícono: pago / nuevo_socio / vencimiento. Acá había
                # un diccionario que traducía desde MAYÚSCULAS y no matcheaba
                # nunca, así que todo caía al default y un alta se dibujaba con
                # el ícono de pago. Sin traducción no puede volver a pasar.
                "tipo": e.get("tipo", ""),
                "desc": e.get("descripcion", ""),
                "hora": self._hace_cuanto(e.get("fecha")),
            }
            for e in datos
        ]

    # ── Cobros ────────────────────────────────────────────────────────────────

    def get_tipos_membresia(self) -> list[dict]:
        datos = self._datos(api_client.obtener_tipos_membresia(), [])
        return [
            {
                "id": t["id_tipo_membresia"],
                "nombre": t["nombre"],
                "dias": t["duracion_dias"],
                "precio": t["precio_actual"],
            }
            for t in datos
        ]

    def get_cuenta_socio(self, id_socio: int) -> dict:
        """
        Estado de cuenta: membresía vigente, deudas y últimos pagos.

        `dias_atraso` lo calcula esta capa a partir de la fecha de generación
        de la deuda. Podría venir del backend, pero es puro formato de
        pantalla: el dato real es la fecha, y el "hace 8 días" cambia solo con
        que pase el tiempo.
        """
        vacio = {"plan": "—", "estado": "Sin membresía", "vencimiento": "—",
                 "deudas": [], "total_adeudado": 0, "pagos": [],
                 "puede_renovar": True, "motivo_no_renovar": ""}
        datos = self._datos(api_client.obtener_estado_cuenta(id_socio), None)
        if not datos:
            return vacio

        membresia = datos.get("membresia_actual") or {}
        hoy = datetime.now().date()

        deudas = []
        for d in datos.get("deudas", []):
            atraso = 0
            try:
                generada = datetime.strptime(d["fecha_generacion"][:10], "%Y-%m-%d").date()
                atraso = max(0, (hoy - generada).days)
            except (ValueError, TypeError, KeyError):
                pass
            deudas.append({
                "id": d["id_deuda"],
                "monto": d["monto"],
                "generada": self._fecha(d.get("fecha_generacion")),
                "detalle": d.get("observaciones") or "Cuota adeudada",
                "dias_atraso": atraso,
            })

        return {
            "plan": membresia.get("tipo") or "—",
            # "Al día" / "Con deuda" es lo que decide el backend cruzando
            # membresía vigente Y ausencia de deudas: alguien puede tener la
            # cuota del mes paga y arrastrar una deuda vieja.
            # Prepago puro: sin tabla Deuda, "al día" es tener membresía vigente.
            "estado": "Al día" if datos.get("al_dia") else "Sin cuota vigente",
            # Sin adelantos (backend/renovacion.py): si no se puede cobrar, la
            # pantalla muestra el motivo en vez del botón.
            "puede_renovar": datos.get("puede_renovar", True),
            "motivo_no_renovar": datos.get("motivo_no_renovar") or "",
            "vencimiento": self._fecha(membresia.get("fecha_vencimiento")),
            "deudas": deudas,
            "total_adeudado": datos.get("deuda_total", 0),
            "pagos": [
                {
                    "id": p["id_pago"],
                    "fecha": self._fecha(p.get("fecha_pago")),
                    "monto": p["monto"],
                    "metodo": METODO_PAGO_DISPLAY.get(p.get("metodo"), p.get("metodo", "—")),
                    "estado": p.get("estado", "").capitalize(),
                    "comprobante": p.get("numero_comprobante") or "—",
                }
                for p in datos.get("ultimos_pagos", [])
            ],
        }

    def get_metodos_pago(self) -> list[str]:
        """
        Medios de pago, con la etiqueta que ve el usuario.

        La lista es fija porque es un enum del esquema, no datos: pedirla a la
        API sería un viaje de red para traer algo que no cambia nunca. Lo que
        sí importa es que estas etiquetas se traduzcan de vuelta al valor del
        enum antes de cobrar — para eso está METODO_PAGO_BACKEND.
        """
        return list(METODO_PAGO_DISPLAY.values())

    # ── Asistencia ────────────────────────────────────────────────────────────

    def get_asistencias_hoy(self) -> list[dict]:
        datos = self._datos(api_client.obtener_asistencias_hoy(), [])
        return [
            {
                "id": a["id_asistencia"],
                "socio": a.get("socio", "—"),
                "hora": self._hora(a.get("fecha_hora_ingreso")),
                "metodo": "RFID" if a.get("metodo_registro") == "RFID" else "Manual",
                # Qué número de ingreso del día es: 1 el primero, 2 y 3 los
                # repetidos, que la pantalla marca al lado del nombre.
                "numero": a.get("ingreso_numero"),
            }
            for a in datos
        ]

    # ── Actividades ───────────────────────────────────────────────────────────

    def get_actividades(self) -> list[dict]:
        """
        Catálogo con sus planes y los profesores asignados.

        Los profesores necesitan un pedido por actividad, así que la lista de
        nombres se arma acá. Con tres o cuatro actividades es despreciable; si
        el catálogo creciera mucho, correspondería un endpoint que los traiga
        anidados como ya vienen los planes.
        """
        datos = self._datos(api_client.obtener_actividades(), [])

        salida = []
        for a in datos:
            profesores = self._datos(
                api_client.obtener_profesores_de_actividad(a["id_actividad"]), []
            )
            salida.append({
                "id": a["id_actividad"],
                "nombre": a["nombre"],
                "activa": a.get("activo", True),
                "descripcion": a.get("descripcion") or "",
                "cupo": a.get("cupo_default", 0),
                # La clase suelta es un plan (tipo_limite CLASE_SUELTA): su
                # precio sale de ahí, ya no es una columna de Actividad.
                "precio_suelta": next(
                    (pl["precio"] for pl in a.get("planes", [])
                     if pl.get("tipo_limite") == "CLASE_SUELTA"), 0),
                "horas_cancelacion": a.get("horas_anticipacion_cancelacion", 0),
                # Con ID y nombre, no sólo el nombre: dos profesores pueden
                # llamarse igual —pasa de verdad, hay dos "PEPE SAND" con DNI
                # distinto— y comparar por nombre hacía que asignar a uno
                # marcara al otro como asignado. El id es lo único que los
                # distingue.
                "profesores": [
                    {"id": p["id_profesor"], "nombre": p.get("nombre", "?")}
                    for p in profesores
                ],
                "planes": [
                    {
                        "id": p["id_plan_actividad"],
                        "nombre": p["nombre"],
                        "tipo": p["tipo_limite"],
                        "cantidad": p["cantidad"],
                        "precio": p["precio"],
                        "activo": p.get("activo", True),
                    }
                    for p in a.get("planes", [])
                ],
            })
        return salida

    def get_profesores(self) -> list[dict]:
        datos = self._datos(api_client.obtener_todos_los_profesores(), [])
        return [
            {
                "id": p["id_profesor"],
                "nombre": p.get("nombre", "?"),
                "especialidad": p.get("especialidad") or p.get("titulo") or "—",
            }
            for p in datos
        ]


    # =========================================================================
    # ESCRITURAS
    # =========================================================================
    # Todas devuelven la misma forma, para que las vistas no tengan que
    # distinguir de dónde vino el problema:
    #
    #     {"ok": True,  "mensaje": "...", ...datos}
    #     {"ok": False, "mensaje": "<lo que dijo el backend o la red>"}
    #
    # El mensaje de error viene REDACTADO POR EL BACKEND. No se reescribe acá:
    # es el mismo texto que ve la PWA, y el backend es quien sabe por qué
    # rechazó — "el turno ya está completo (15 lugares)" es más útil que un
    # "no se pudo" armado en el cliente.

    @staticmethod
    def _resultado(respuesta: dict, mensaje_ok: str = "") -> dict:
        """Traduce una respuesta del api_client a la forma que esperan las vistas."""
        if not respuesta.get("ok"):
            return {"ok": False, "mensaje": respuesta.get("error", "No se pudo completar la acción.")}
        datos = respuesta.get("data") or {}
        return {
            "ok": True,
            "mensaje": (datos.get("mensaje") if isinstance(datos, dict) else None) or mensaje_ok,
            "data": datos,
        }

    # ── Asistencia ────────────────────────────────────────────────────────────

    def fichar_manual(self, id_socio: int) -> dict:
        """
        Registra un ingreso. Es la única forma de fichar: el fichaje por
        tarjeta se retiró de las dos apps (ver views/asistencia.py).

        Puede volver ok=True con una `advertencia`: el backend registra el
        ingreso AUNQUE el socio deba o tenga la cuota vencida. Es una decisión
        de negocio — dejar a alguien afuera lo decide una persona en el
        mostrador, no un torniquete — y además, si no se registrara, el
        gimnasio perdería el dato de que esa persona estuvo.

        Lo mismo vale para el ingreso repetido: tampoco se rechaza. Vuelve con
        `numero` en 2, 3… y la pantalla lo marca al lado del nombre.
        """
        return self._fichaje(api_client.fichar_manual(id_socio))

    def deshacer_fichaje(self, id_asistencia: int) -> dict:
        """Borra un ingreso mal cargado. El backend sólo deja los de hoy."""
        return self._resultado(api_client.deshacer_fichaje(id_asistencia),
                               "Ingreso borrado.")

    def _fichaje(self, respuesta: dict) -> dict:
        if not respuesta.get("ok"):
            return {
                "ok": False,
                "mensaje": respuesta.get("error", "No se pudo fichar."),
            }

        datos = respuesta["data"]
        a = datos.get("asistencia", {})
        return {
            "ok": True,
            "mensaje": datos.get("mensaje", ""),
            "advertencia": datos.get("advertencia"),
            "permitido": datos.get("permitido", True),
            "fichaje": {
                "id": a.get("id_asistencia"),
                "socio": a.get("socio", "—"),
                "hora": self._hora(a.get("fecha_hora_ingreso")),
                "metodo": "RFID" if a.get("metodo_registro") == "RFID" else "Manual",
                "numero": a.get("ingreso_numero"),
            },
        }

    # ── Cobros ────────────────────────────────────────────────────────────────

    def cobrar_membresia(self, id_socio: int, id_tipo: int, metodo_display: str,
                          comprobante: str | None = None,
                          id_promocion: int | None = None,
                          id_plan_actividad: int | None = None) -> dict:
        """
        Cobra una membresía.

        NO manda el monto: lo calcula el backend a partir del plan. Si viniera
        de acá, cualquiera con la app abierta podría cobrar $1 una membresía de
        $30.000 — y en la base quedaría un pago perfectamente válido.

        Con `id_promocion` aplica un descuento, y vale lo mismo: viaja el ID,
        nunca el precio ya descontado. El backend busca la promo, verifica que
        esté vigente y recalcula. Mandar el monto final sería el mismo agujero
        con otro nombre.
        """
        return self._resultado(api_client.cobrar({
            "id_socio": id_socio,
            "id_tipo_membresia": id_tipo,
            "metodo": METODO_PAGO_BACKEND.get(metodo_display, "EFECTIVO"),
            "numero_comprobante": comprobante or None,
            "id_promocion": id_promocion,
            # Combo renovar + abono: el backend crea membresía e inscripción en
            # la misma transacción (Inscripcion_Actividad.id_membresia es NOT NULL).
            "id_plan_actividad": id_plan_actividad,
        }))

    def comprar_plan_actividad(self, id_socio: int, id_plan: int,
                                metodo_display: str) -> dict:
        """
        Compra un abono de actividad.

        El backend exige cuota al día, que la membresía cubra el mes entero del
        abono y que el socio no tenga deudas. Si algo falla, el mensaje explica
        cuál de las tres y qué hacer.
        """
        return self._resultado(api_client.comprar_plan_actividad(id_plan, {
            "id_socio": id_socio,
            "metodo": METODO_PAGO_BACKEND.get(metodo_display, "EFECTIVO"),
        }))

    def comprar_clase_suelta(self, id_socio: int, id_turno: int,
                              metodo_display: str) -> dict:
        """Cobra y reserva una clase individual, sin abono previo."""
        return self._resultado(api_client.comprar_clase_suelta(id_turno, {
            "id_socio": id_socio,
            "metodo": METODO_PAGO_BACKEND.get(metodo_display, "EFECTIVO"),
        }))

    def puede_comprar_actividad(self, id_socio: int) -> dict:
        """
        Si el socio está en condiciones de comprar un abono, SIN comprar nada.
        Se consulta ANTES de cobrar: si el abono no va a entrar, hay que
        ofrecer renovar la cuota primero en vez de cobrar y descubrirlo después.
        """
        respuesta = api_client.puede_comprar(id_socio)
        if not respuesta.get("ok"):
            return {"puede": False, "motivo": respuesta.get("error", "")}
        d = respuesta["data"]
        return {"puede": d.get("puede", False), "motivo": d.get("motivo") or ""}

    def anular_pago(self, id_pago: int) -> dict:
        return self._resultado(api_client.anular_pago(id_pago), "Pago anulado.")

    def get_turnos_de_actividad(self, id_actividad: int) -> list[dict]:
        """Turnos habilitados de una actividad, para el selector de clase suelta."""
        datos = self._datos(api_client.obtener_turnos(), [])
        return [
            {
                "id": t["id_turno"],
                "actividad": t.get("actividad", "?"),
                "fecha": self._fecha(t.get("fecha")),
                "hora": (t.get("hora") or "")[:5],
                "libres": t.get("lugares_libres", 0),
                "cupo": t.get("cupo_maximo", 0),
                "profesor": t.get("profesor") or "—",
            }
            for t in datos
            if t.get("id_actividad") == id_actividad and t.get("estado") == "HABILITADO"
        ]

    # ── Actividades (ABM) ─────────────────────────────────────────────────────

    def crear_actividad(self, datos: dict) -> dict:
        # precio_clase_suelta ya no es columna: se materializa como un plan
        # CLASE_SUELTA (cantidad 1) con ese precio.
        precio_suelta = datos.pop("precio_clase_suelta", 0) or 0
        resp = api_client.crear_actividad(datos)
        id_act = (resp.get("data") or {}).get("id_actividad") if resp.get("ok") else None
        if id_act and float(precio_suelta) > 0:
            api_client.crear_plan_actividad(id_act, {
                "nombre": "Clase suelta", "tipo_limite": "CLASE_SUELTA",
                "cantidad": 1, "precio": float(precio_suelta)})
        return self._resultado(resp, "Actividad creada.")

    def editar_actividad(self, id_actividad: int, datos: dict) -> dict:
        # Upsert del plan de clase suelta con el precio del formulario.
        precio_suelta = datos.pop("precio_clase_suelta", None)
        resp = api_client.editar_actividad(id_actividad, datos)
        if resp.get("ok") and precio_suelta is not None:
            planes = (resp.get("data") or {}).get("planes", [])
            suelta = next((pl for pl in planes
                           if pl.get("tipo_limite") == "CLASE_SUELTA"), None)
            cuerpo = {"nombre": "Clase suelta", "tipo_limite": "CLASE_SUELTA",
                      "cantidad": 1, "precio": float(precio_suelta)}
            if suelta:
                cuerpo["nombre"] = suelta.get("nombre", "Clase suelta")
                api_client.editar_plan_actividad(suelta["id_plan_actividad"], cuerpo)
            elif float(precio_suelta) > 0:
                api_client.crear_plan_actividad(id_actividad, cuerpo)
        return self._resultado(resp, "Actividad actualizada.")

    def cambiar_estado_actividad(self, id_actividad: int, activa: bool) -> dict:
        """
        Da de baja o reactiva. Manda el estado DESTINO, no un toggle: con una
        pantalla desactualizada, "dar de baja" sobre algo ya dado de baja lo
        reactivaría.
        """
        return self._resultado(
            api_client.cambiar_estado_actividad(id_actividad, activa),
            "Actividad reactivada." if activa else "Actividad dada de baja.",
        )

    def crear_plan_actividad(self, id_actividad: int, datos: dict) -> dict:
        return self._resultado(api_client.crear_plan_actividad(id_actividad, datos),
                                "Plan creado.")

    def editar_plan_actividad(self, id_plan: int, datos: dict) -> dict:
        return self._resultado(api_client.editar_plan_actividad(id_plan, datos),
                                "Plan actualizado.")

    def cambiar_estado_plan(self, id_plan: int, activo: bool) -> dict:
        return self._resultado(
            api_client.cambiar_estado_plan(id_plan, activo),
            "Plan reactivado." if activo else "Plan dado de baja.",
        )

    def asignar_profesor(self, id_actividad: int, id_profesor: int) -> dict:
        return self._resultado(api_client.asignar_profesor(id_actividad, id_profesor),
                                "Profesor asignado.")

    def desasignar_profesor(self, id_actividad: int, id_profesor: int) -> dict:
        return self._resultado(api_client.desasignar_profesor(id_actividad, id_profesor),
                                "Profesor desasignado.")

    # ── Socios ────────────────────────────────────────────────────────────────

    def alta_socio(self, datos: dict) -> dict:
        """
        Alta por invitación. El backend crea Persona + Teléfono + Socio y, si
        se pidió, la cuenta con una contraseña temporal.

        La contraseña vuelve EN TEXTO PLANO y es la única vez que existe
        legible: en la base solo queda su hash. Quien la reciba la muestra una
        vez y la olvida — no se guarda ni se loguea.
        """
        respuesta = api_client.alta_socio(datos)
        if not respuesta.get("ok"):
            return {"ok": False, "mensaje": respuesta.get("error", "No se pudo dar de alta.")}
        d = respuesta["data"]
        return {
            "ok": True,
            "mensaje": d.get("mensaje", ""),
            "usuario": d.get("username"),
            "password_temporal": d.get("password_temporal"),
            "texto_credenciales": d.get("texto_credenciales"),
            "numero_socio": d.get("numero_socio"),
            # Para "Cobrar ahora": Cobros necesita saber a quién abrir.
            "id_socio": d.get("id_socio"),
            "email_enviado": d.get("email_enviado", False),
        }

    def dar_de_baja_socio(self, id_socio: int, tipo: str = "VOLUNTARIA",
                           motivo: str | None = None, inmediata: bool = False) -> dict:
        return self._resultado(
            api_client.dar_de_baja_socio(id_socio, tipo, motivo, inmediata),
            "Socio dado de baja.")

    def reactivar_socio(self, id_socio: int) -> dict:
        return self._resultado(api_client.reactivar_socio(id_socio), "Socio reactivado.")

    def anular_baja_socio(self, id_socio: int) -> dict:
        return self._resultado(api_client.anular_baja_socio(id_socio), "Se anuló la baja.")

    # ── Teléfonos de la ficha ─────────────────────────────────────────────────

    def get_telefonos_de_socio(self, id_socio: int) -> list[dict]:
        """
        Todos los números del socio, el principal primero (el orden lo decide
        el backend). `SocioOut.telefono` trae sólo el principal, aplanado para
        la grilla; esto es la lista completa.
        """
        datos = self._datos(api_client.telefonos_de_socio(id_socio), [])
        return [{
            "id": t["id_telefono"],
            "numero": t.get("numero", ""),
            # La columna admite null: se muestra como celular, que es el caso
            # común y el único al que se le puede mandar un WhatsApp.
            "tipo": t.get("tipo") or "CELULAR",
            "principal": bool(t.get("principal")),
        } for t in datos]

    def agregar_telefono(self, id_socio: int, numero: str,
                         tipo: str = "CELULAR") -> dict:
        return self._resultado(
            api_client.agregar_telefono(id_socio, {"numero": numero, "tipo": tipo,
                                                   "principal": False}),
            "Teléfono agregado.")

    def marcar_telefono_principal(self, id_socio: int, telefono: dict) -> dict:
        """
        El PUT pide el cuerpo completo, así que se reenvían número y tipo tal
        como están: lo único que cambia es cuál queda marcado.
        """
        return self._resultado(
            api_client.editar_telefono(id_socio, telefono["id"], {
                "numero": telefono["numero"],
                "tipo": telefono["tipo"],
                "principal": True,
            }),
            "Ahora es el teléfono principal.")

    def borrar_telefono(self, id_socio: int, id_telefono: int) -> dict:
        return self._resultado(api_client.borrar_telefono(id_socio, id_telefono),
                               "Teléfono borrado.")

    # ── Personal ──────────────────────────────────────────────────────────────

    def alta_empleado(self, datos: dict) -> dict:
        respuesta = api_client.alta_empleado(datos)
        if not respuesta.get("ok"):
            return {"ok": False, "mensaje": respuesta.get("error", "No se pudo dar de alta.")}
        d = respuesta["data"]
        return {
            "ok": True,
            "mensaje": d.get("mensaje", ""),
            "usuario": d.get("username"),
            "password_temporal": d.get("password_temporal"),
            "legajo": d.get("legajo"),
            # El mensaje ya redactado que recibe el empleado (notificaciones.py).
            # Es el mismo que el backend manda por mail, y la pantalla lo usa
            # para el botón de WhatsApp: así el texto —incluida la advertencia
            # de que la contraseña es de un solo uso— no se reescribe en cada
            # app por su cuenta.
            "texto_credenciales": d.get("texto_credenciales"),
            "email_enviado": d.get("email_enviado", False),
        }

    def get_entrenadores(self) -> list[dict]:
        """
        Entrenadores activos, para el selector del formulario de rutinas.

        Hace falta porque `Rutina.id_entrenador` es NOT NULL y el Dueño —que
        es quien más usa esta pantalla— no es entrenador: sin elegir a alguien
        el backend rechaza la creación. Un entrenador logueado no necesita
        elegir (la rutina queda a su nombre), pero el selector se muestra
        igual y el backend valida que no elija a otro.
        """
        return self._datos(api_client.obtener_entrenadores(), [])

    def get_nutricionistas(self) -> list[dict]:
        """Espejo del anterior, para el formulario de dietas."""
        return self._datos(api_client.obtener_nutricionistas(), [])

    def baja_empleado(self, id_empleado: int, motivo: str | None = None) -> dict:
        return self._resultado(api_client.baja_empleado(id_empleado, motivo),
                                "Empleado dado de baja.")

    def reactivar_empleado(self, id_empleado: int) -> dict:
        return self._resultado(api_client.reactivar_empleado(id_empleado),
                                "Empleado reactivado.")

    def editar_empleado(self, id_empleado: int, datos: dict) -> dict:
        return self._resultado(api_client.editar_empleado(id_empleado, datos),
                                "Empleado actualizado.")

    # ── Rutinas y nutrición ───────────────────────────────────────────────────

    def crear_rutina(self, datos: dict) -> dict:
        return self._resultado(api_client.crear_rutina(datos), "Rutina creada.")

    def asignar_rutina(self, id_rutina: int, id_socio: int) -> dict:
        return self._resultado(api_client.asignar_rutina(id_rutina, id_socio),
                                "Rutina asignada.")

    def editar_rutina(self, id_rutina: int, datos: dict) -> dict:
        return self._resultado(api_client.editar_rutina(id_rutina, datos),
                                "Rutina actualizada.")

    def baja_rutina(self, id_rutina: int) -> dict:
        return self._resultado(api_client.baja_rutina(id_rutina), "Rutina dada de baja.")

    def reactivar_rutina(self, id_rutina: int) -> dict:
        return self._resultado(api_client.reactivar_rutina(id_rutina), "Rutina reactivada.")

    def crear_dieta(self, datos: dict) -> dict:
        return self._resultado(api_client.crear_dieta(datos), "Plan nutricional creado.")

    def asignar_dieta(self, id_dieta: int, id_socio: int) -> dict:
        return self._resultado(api_client.asignar_dieta(id_dieta, id_socio),
                                "Plan asignado.")

    def crear_ejercicio(self, datos: dict) -> dict:
        return self._resultado(api_client.crear_ejercicio(datos), "Ejercicio creado.")

    def get_ejercicios(self) -> list[dict]:
        datos = self._datos(api_client.obtener_ejercicios(), [])
        return [
            {"id": e["id_ejercicio"], "nombre": e["nombre"],
             "grupo": e.get("grupo_muscular", "—"),
             "descripcion": e.get("descripcion") or "",
             "video": e.get("video_local")}
            for e in datos
        ]

    # ── Usuarios ──────────────────────────────────────────────────────────────

    def get_usuarios(self) -> list[dict]:
        datos = self._datos(api_client.obtener_usuarios(), [])
        return [
            {
                "id": u["id_usuario"],
                "usuario": u["username"],
                "email": u.get("email") or "",
                # Para ofrecer las credenciales por WhatsApp al resetear la
                # contraseña de alguien que no dejó mail.
                "telefono": u.get("telefono") or "",
                "nombre": u.get("nombre_completo", "—"),
                "dni": u.get("dni", "—"),
                "roles": u.get("roles", []),
                "rol": (u.get("roles") or ["—"])[0],
                "estado": "Inactivo" if not u.get("activo") else
                          ("Bloqueado" if u.get("bloqueado") else "Activo"),
                "debe_cambiar": u.get("debe_cambiar_password", False),
                "ultimo_acceso": self._fecha(u.get("ultimo_acceso")),
            }
            for u in datos
        ]

    def get_personas_sin_cuenta(self) -> list[dict]:
        datos = self._datos(api_client.obtener_personas_sin_cuenta(), [])
        return [
            {"id": p["id_persona"], "nombre": p.get("nombre_completo", "—"),
             "dni": p.get("dni", "—"), "roles": p.get("roles", [])}
            for p in datos
        ]

    def crear_cuenta(self, id_persona: int) -> dict:
        """
        Crea la cuenta de una persona ya cargada. Devuelve las credenciales
        generadas — el sistema las elige, nunca un administrador: que alguien
        elija la contraseña de otro sería conocerla para siempre.
        """
        respuesta = api_client.crear_cuenta(id_persona)
        if not respuesta.get("ok"):
            return {"ok": False, "mensaje": respuesta.get("error", "No se pudo crear la cuenta.")}
        d = respuesta["data"]
        return {"ok": True, "mensaje": d.get("mensaje", ""),
                "usuario": d.get("username"), "password_temporal": d.get("password_temporal")}

    def resetear_password_usuario(self, id_usuario: int) -> dict:
        respuesta = api_client.resetear_password(id_usuario)
        if not respuesta.get("ok"):
            return {"ok": False, "mensaje": respuesta.get("error", "No se pudo resetear.")}
        d = respuesta["data"]
        return {"ok": True, "mensaje": d.get("mensaje", ""),
                "usuario": d.get("username"), "password_temporal": d.get("password_temporal"),
                # El mensaje ya armado por el backend, el mismo que manda por
                # mail: la vista lo usa para los botones de envío.
                "texto_credenciales": d.get("texto_credenciales"),
                "email_enviado": d.get("email_enviado", False)}

    def desbloquear_usuario(self, id_usuario: int) -> dict:
        return self._resultado(api_client.desbloquear_usuario(id_usuario), "Cuenta desbloqueada.")

    def borrar_cuenta(self, id_usuario: int) -> dict:
        return self._resultado(api_client.borrar_cuenta(id_usuario), "Cuenta borrada.")

    def cambiar_estado_usuario(self, id_usuario: int, activo: bool) -> dict:
        return self._resultado(
            api_client.cambiar_estado_usuario(id_usuario, activo),
            "Cuenta activada." if activo else "Cuenta desactivada.",
        )


    # ── Panel de recepción ────────────────────────────────────────────────────
    #
    # Lo que ve el mostrador. Todo viene ya resuelto del backend —el estado de
    # cada persona, los minutos que faltan, la advertencia de cuota— porque
    # las tres apps tienen que decir exactamente lo mismo: si la pantalla dice
    # que una reserva sigue viva y el molinete dice que venció, el mostrador
    # deja de confiar en la pantalla.

    def get_panel_recepcion(self) -> dict:
        """
        Próximos turnos con sus inscriptos, en un solo pedido.

        Devuelve la forma vacía y no None si falla: el panel se refresca solo
        cada pocos segundos y una pantalla en blanco es preferible a que la
        app se caiga porque el backend se reinició justo en ese instante.
        """
        datos = self._datos(api_client.obtener_panel_recepcion(), {})
        if not datos:
            return {"turnos": [], "vencidos": [], "anotados": 0, "presentes": 0,
                     "hay_datos": False}
        return {
            "turnos": [self._turno_panel(t) for t in datos.get("turnos", [])],
            "vencidos": [self._turno_panel(t) for t in datos.get("vencidos_recientes", [])],
            "anotados": datos.get("total_anotados_hoy", 0),
            "presentes": datos.get("total_presentes_hoy", 0),
            "hay_datos": True,
        }

    def _turno_panel(self, t: dict) -> dict:
        """Un turno del panel, con lo que la vista necesita para pintarlo."""
        faltan = t.get("minutos_para_empezar", 0)
        return {
            "id": t["id_turno"],
            "actividad": t.get("actividad", "—"),
            "hora": str(t.get("hora", ""))[:5],
            "faltan": faltan,
            # El texto ya armado, para que la vista no repita la lógica de
            # pluralizar y de distinguir "en 5 min" de "empezó hace 5 min".
            "cuando": self._cuando(faltan),
            "vence": str(t.get("vence_a", ""))[11:16],
            "cupo": t.get("cupo_maximo", 0),
            "ocupados": t.get("ocupados", 0),
            "en_espera": t.get("en_espera", 0),
            "profesor": t.get("profesor") or "—",
            "sala_abierta": t.get("es_sala_abierta", False),
            "inscriptos": [
                {
                    "id_reserva": i["id_reserva"],
                    "id_socio": i["id_socio"],
                    "nombre": i.get("nombre", "—"),
                    "dni": i.get("dni", "—"),
                    "estado": i.get("estado", "pendiente"),
                    "suelta": i.get("es_clase_suelta", False),
                    "alerta": i.get("alerta"),
                    "puede_cobrar": i.get("puede_cobrar_cuota", True),
                }
                for i in t.get("inscriptos", [])
            ],
        }

    @staticmethod
    def _cuando(minutos: int) -> str:
        """'en 12 min' / 'empieza ahora' / 'empezó hace 8 min'."""
        if minutos > 60:
            horas, resto = divmod(minutos, 60)
            return f"en {horas} h {resto} min" if resto else f"en {horas} h"
        if minutos > 1:
            return f"en {minutos} min"
        if minutos >= -1:
            return "empieza ahora"
        return f"empezó hace {abs(minutos)} min"

    def buscar_socio_por_dni(self, dni: str) -> list[dict]:
        """
        Busca en el mostrador por DNI.

        Por DNI y no por nombre porque la persona tiene el documento en la
        mano: se tipea sin ambigüedad, no tiene acentos y no hay dos socios
        con el mismo. Trae de una la membresía, la deuda y el próximo turno,
        para que una sola búsqueda cierre la conversación.
        """
        datos = self._datos(api_client.buscar_por_dni(dni.strip()), [])
        return [
            {
                "id": s["id_socio"],
                "nombre": s.get("nombre", "—"),
                "dni": s.get("dni", "—"),
                "numero_socio": s.get("numero_socio") or "—",
                "tiene_rfid": s.get("tiene_rfid", False),
                "activo": s.get("activo", True),
                "membresia": s.get("estado_membresia", "—"),
                "vence": self._fecha(s.get("vencimiento")),
                "deuda": s.get("deuda_total", 0),
                "alerta": s.get("alerta"),
                "puede_cobrar": s.get("puede_cobrar_cuota", True),
                "proximo": (self._turno_panel(s["proximo_turno"])
                            if s.get("proximo_turno") else None),
            }
            for s in datos
        ]

    # ── Agenda de turnos (personal) ───────────────────────────────────────────
    #
    # Gemelas de turnosService.ts (getAgenda / getDetalleTurno / cancelarTurno).
    # El panel de Recepción sólo muestra las próximas horas; la agenda muestra
    # los días que vienen, con quién se anotó a cada clase.

    def get_agenda_turnos(self, dias: int = 7) -> list[dict]:
        hoy = date.today()
        datos = self._datos(api_client.obtener_turnos(
            hoy.isoformat(), (hoy + timedelta(days=dias)).isoformat()), [])
        return [
            {
                "id": t["id_turno"],
                "actividad": t.get("actividad", "—"),
                "fecha": t["fecha"],
                "hora": str(t.get("hora", ""))[:5],
                "cupo": t.get("cupo_maximo", 0),
                "reservados": t.get("reservados", 0),
                "cancelado": t.get("estado") == "CANCELADO",
                "profesor": t.get("profesor"),
                "motivo": t.get("motivo_cancelacion"),
            }
            for t in datos
        ]

    def get_detalle_turno(self, id_turno: int) -> dict | None:
        datos = self._datos(api_client.obtener_turno_detalle(id_turno), None)
        return self._turno_panel(datos) if datos else None

    def cancelar_turno(self, id_turno: int, motivo: str = "Cancelada por el gimnasio") -> dict:
        return self._resultado(api_client.cancelar_turno(id_turno, motivo), "Turno cancelado.")

    # ── Horarios semanales ────────────────────────────────────────────────────

    def get_horarios(self) -> list[dict]:
        datos = self._datos(api_client.obtener_horarios(), [])
        return [
            {
                "id": h["id_horario_actividad"],
                "actividad": h.get("actividad", "—"),
                "id_actividad": h.get("id_actividad"),
                "dia": h.get("dia_nombre", "—"),
                "dia_num": h.get("dia_semana", 1),
                "hora": str(h.get("hora", ""))[:5],
                "cupo": h.get("cupo", 0),
                "profesor": h.get("profesor") or "—",
                "activo": h.get("activo", True),
                "turnos_futuros": h.get("turnos_futuros", 0),
            }
            for h in datos
        ]

    def crear_horario(self, datos: dict) -> dict:
        return self._resultado(api_client.crear_horario(datos),
                                "Horario creado. Los turnos ya se generaron.")

    def cambiar_estado_horario(self, id_horario: int, activo: bool) -> dict:
        return self._resultado(
            api_client.cambiar_estado_horario(id_horario, activo),
            "Horario reactivado." if activo else
            # El mensaje decía que los turnos vacíos se cancelaban. NO es
            # cierto con esta llamada: el backend sólo los cancela si se le
            # pide explícitamente (borrar_turnos_futuros), y desde acá no se
            # le pide. Dar de baja un horario significa "no generes más", y
            # los turnos que ya existen siguen en pie — pueden tener gente.
            "Horario dado de baja. Deja de generar turnos nuevos; "
            "los ya generados siguen en pie.",
        )

    def generar_turnos(self) -> dict:
        respuesta = api_client.generar_turnos()
        if not respuesta.get("ok"):
            return {"ok": False, "mensaje": respuesta.get("error", "No se pudieron generar.")}
        return {"ok": True, "mensaje": respuesta["data"].get("mensaje", "Listo.")}

    # ── Entrenador a cargo ────────────────────────────────────────────────────
    #
    # Un socio puede tener VARIOS a la vez —uno de musculación y otro de
    # funcional— y eso es normal, no un error de datos. Es la diferencia con
    # las rutinas y las dietas, que admiten una sola activa.

    def get_entrenadores_de_socio(self, id_socio: int) -> list[dict]:
        """
        Sus entrenadores, con historial.

        Se traen TODOS y no sólo los activos: el historial es el motivo por el
        que esto es una tabla y no una columna. Con la columna vieja,
        reasignar borraba al anterior y nadie podía responder quién lo
        entrenaba antes.
        """
        datos = self._datos(api_client.obtener_entrenadores_de_socio(id_socio), [])
        return [
            {
                "id": a["id_asignacion"],
                "id_entrenador": a["id_entrenador"],
                "entrenador": a.get("entrenador", "—"),
                "especialidad": a.get("especialidad") or "—",
                "desde": self._fecha(a.get("fecha_inicio")),
                "hasta": self._fecha(a.get("fecha_fin")) if a.get("fecha_fin") else None,
                "activa": a.get("estado") == "ACTIVA",
            }
            for a in datos
        ]

    def asignar_entrenador(self, id_socio: int, id_entrenador: int) -> dict:
        return self._resultado(api_client.asignar_entrenador(id_socio, id_entrenador),
                                "Entrenador asignado.")

    def finalizar_entrenador(self, id_asignacion: int) -> dict:
        return self._resultado(
            api_client.finalizar_asignacion_entrenador(id_asignacion),
            "Listo. La asignación queda en el historial, no se borra.",
        )

    # ── Historial médico ──────────────────────────────────────────────────────
    #
    # Es un catálogo y no un campo de texto libre por 1FN: "asma, rodilla
    # operada, hipertensión" en una sola celda no se puede contar ni filtrar, y
    # cada quien lo escribe distinto. Con el catálogo, "cuántos socios tienen
    # asma" es una consulta.
    #
    # Ojo con el campo `observaciones` de Socio, que YA existe en el formulario
    # de alta y dice "Lesiones, restricciones...". No es lo mismo y conviene no
    # confundirlos: aquel es una nota suelta del mostrador, esto es el dato
    # estructurado que el entrenador filtra. Se dejan los dos porque sacar el
    # de Socio rompería fichas ya cargadas.

    def get_catalogo_patologias(self) -> list[dict]:
        """Las condiciones que el gimnasio registra, para el selector."""
        datos = self._datos(api_client.obtener_catalogo_patologias(), [])
        return [
            {
                "id": p["id_patologia"],
                "nombre": p["nombre"],
                "descripcion": p.get("descripcion") or "",
            }
            for p in datos
        ]

    def crear_patologia(self, nombre: str, descripcion: str | None = None) -> dict:
        return self._resultado(
            api_client.crear_patologia(nombre, descripcion),
            "Condición agregada al catálogo.",
        )

    def get_patologias_de_socio(self, id_socio: int) -> list[dict]:
        """
        Las condiciones de un socio.

        Se guarda la fecha DOS veces: `desde` ya formateada para mostrar y
        `fecha_iso` cruda. El diálogo de edición necesita la cruda para
        devolvérsela al backend, y volver a parsear "11/08/2026" para eso sería
        deshacer a mano lo que `_fecha` acaba de hacer.
        """
        datos = self._datos(api_client.obtener_patologias_de_socio(id_socio), [])
        return [
            {
                "id": p["id_patologia"],
                "nombre": p["nombre"],
                "descripcion": p.get("descripcion") or "",
                "desde": self._fecha(p.get("fecha_diagnostico")),
                "fecha_iso": p.get("fecha_diagnostico") or "",
                "observaciones": p.get("observaciones") or "",
            }
            for p in datos
        ]

    def asignar_patologia(self, id_socio: int, id_patologia: int,
                           fecha: str | None = None,
                           observaciones: str | None = None) -> dict:
        return self._resultado(
            api_client.asignar_patologia(id_socio, {
                "id_patologia": id_patologia,
                "fecha_diagnostico": fecha or None,
                "observaciones": observaciones or None,
            }),
            "Condición registrada.",
        )

    def editar_patologia_de_socio(self, id_socio: int, id_patologia: int,
                                   fecha: str | None = None,
                                   observaciones: str | None = None) -> dict:
        """
        Cambia fecha y observaciones. Existe separado del alta porque las
        observaciones cambian más que el diagnóstico —una lesión que mejora,
        una medicación que se ajusta— y borrar para recargar perdería la fecha
        original.
        """
        return self._resultado(
            api_client.editar_patologia_de_socio(id_socio, id_patologia, {
                "id_patologia": id_patologia,
                "fecha_diagnostico": fecha or None,
                "observaciones": observaciones or None,
            }),
            "Condición actualizada.",
        )

    def quitar_patologia(self, id_socio: int, id_patologia: int) -> dict:
        """
        Acá SÍ se borra la fila, a diferencia de casi todo el resto del sistema.
        No es un hecho histórico: es el estado de salud ACTUAL. Una lesión que
        se curó no es "una lesión finalizada" que convenga arrastrar, y guardar
        condiciones médicas viejas de alguien es justamente el tipo de dato que
        no conviene acumular sin motivo.
        """
        return self._resultado(
            api_client.quitar_patologia(id_socio, id_patologia),
            "Condición eliminada de la ficha.",
        )


    # ── Promociones ───────────────────────────────────────────────────────────
    #
    # Descuentos sobre el precio de lista. LISTARLAS pide la sección Cobros
    # (Dueño + Recepcionista, porque el mostrador tiene que poder elegir una);
    # CREARLAS pide la acción GESTION_PROMOCIONES, que solo tiene el Dueño.
    #
    # Ningún método de acá multiplica nada: para saber cuánto sale un plan con
    # una promo está `vista_previa_descuento`, que le pregunta al backend. La
    # fórmula vive en un solo lugar y no en tres.

    def get_promociones(self, solo_vigentes: bool = False) -> list[dict]:
        """
        El catálogo de descuentos.

        Sin filtro trae TODAS, incluidas las apagadas y las vencidas: el panel
        de administración las necesita para reactivar una del año pasado en vez
        de recargarla. `solo_vigentes` es lo que pide el selector del mostrador,
        que no tiene por qué ofrecer una promo de enero en marzo.
        """
        datos = self._datos(api_client.obtener_promociones(solo_vigentes), [])
        return [
            {
                "id": p["id_promocion"],
                "nombre": p["nombre"],
                "descripcion": p.get("descripcion") or "",
                "porcentaje": p.get("porcentaje_descuento"),
                # El monto fijo se eliminó; se deja la clave en None por
                # compatibilidad con la vista, que ya no la usa.
                "monto_fijo": None,
                "desde": self._fecha(p.get("fecha_inicio")),
                "hasta": self._fecha(p.get("fecha_fin")),
                # Crudas además de formateadas: el formulario de edición las
                # necesita en ISO para devolvérselas al backend, y volver a
                # parsear "11/08/2026" sería deshacer a mano lo que _fecha
                # acaba de hacer. Mismo criterio que en las patologías.
                "desde_iso": p.get("fecha_inicio") or "",
                "hasta_iso": p.get("fecha_fin") or "",
                "activo": bool(p.get("activo")),
                # Activa Y en fecha. Son dos cosas distintas y por eso viajan
                # separadas: una promo apagada se arregla reactivándola y una
                # vencida cambiándole las fechas.
                "vigente": bool(p.get("vigente")),
                "etiqueta": p.get("etiqueta") or "",
            }
            for p in datos
        ]

    @staticmethod
    def _cuerpo_promocion(nombre: str, descripcion: str | None,
                           es_porcentaje: bool, valor: float,
                           desde_iso: str, hasta_iso: str) -> dict:
        """
        Arma el cuerpo mandando UNO solo de los dos descuentos.

        El descuento es SIEMPRE porcentual: el monto fijo se eliminó por
        decisión comercial, así que `es_porcentaje` queda por compatibilidad de
        firma pero el cuerpo manda siempre el porcentaje.
        """
        return {
            "nombre": nombre.strip(),
            "descripcion": (descripcion or "").strip() or None,
            "porcentaje_descuento": valor,
            "fecha_inicio": desde_iso,
            "fecha_fin": hasta_iso,
        }

    def crear_promocion(self, nombre: str, descripcion: str | None,
                         es_porcentaje: bool, valor: float,
                         desde_iso: str, hasta_iso: str) -> dict:
        return self._resultado(
            api_client.crear_promocion(self._cuerpo_promocion(
                nombre, descripcion, es_porcentaje, valor, desde_iso, hasta_iso)),
            "Promoción creada.",
        )

    def editar_promocion(self, id_promocion: int, nombre: str,
                          descripcion: str | None, es_porcentaje: bool,
                          valor: float, desde_iso: str, hasta_iso: str) -> dict:
        """
        Edita una promoción.

        NO recalcula lo ya cobrado: Membresia.precio_pactado guarda el monto
        que se cobró de verdad. Si editar la promo cambiara el historial de
        plata, ese historial cambiaría solo — que es exactamente lo que el
        resto del sistema evita.
        """
        return self._resultado(
            api_client.editar_promocion(id_promocion, self._cuerpo_promocion(
                nombre, descripcion, es_porcentaje, valor, desde_iso, hasta_iso)),
            "Promoción actualizada.",
        )

    def dar_de_baja_promocion(self, id_promocion: int) -> dict:
        """
        La apaga. NO borra la fila: la referencian las membresías cobradas con
        ella, y ese historial es el que responde "¿por qué a este socio le
        cobramos $24.000 en vez de $30.000?".
        """
        return self._resultado(api_client.dar_de_baja_promocion(id_promocion),
                                "Promoción dada de baja.")

    def reactivar_promocion(self, id_promocion: int) -> dict:
        """
        La vuelve a encender. Ojo: no le mueve las fechas, así que una vencida
        queda activa pero sigue sin poder aplicarse. Extender una promoción es
        cambiarle la fecha de fin, una decisión explícita, y no un efecto
        secundario de volver a encenderla.
        """
        return self._resultado(api_client.reactivar_promocion(id_promocion),
                                "Promoción reactivada.")

    def uso_de_promocion(self, id_promocion: int) -> str:
        """Cuántas membresías se cobraron con ella. Para decidir antes de apagarla."""
        datos = self._datos(api_client.uso_de_promocion(id_promocion), {})
        return datos.get("mensaje", "") if isinstance(datos, dict) else ""

    def vista_previa_descuento(self, id_promocion: int, id_tipo: int) -> dict | None:
        """
        Cuánto saldría cobrar ese plan con esa promo. No cobra nada.

        Es un viaje al servidor para una multiplicación, y vale la pena: es lo
        que garantiza que el número que ve el mostrador antes de cobrar sea el
        mismo que el backend va a registrar.

        Devuelve None si falla, y la pantalla simplemente no muestra la vista
        previa. No usa `_resultado` porque acá no hay nada que informarle al
        usuario: es una consulta de apoyo, no una acción suya.
        """
        respuesta = api_client.vista_previa_descuento(id_promocion, id_tipo)
        if not respuesta.get("ok"):
            return None
        datos = respuesta.get("data") or {}
        return {
            "lista": float(datos.get("precio_lista", 0)),
            "descuento": float(datos.get("descuento", 0)),
            "final": float(datos.get("precio_final", 0)),
            "promocion": datos.get("promocion", ""),
        }


# ── Instancia global única ─────────────────────────────────────────────────────
# Se crea una sola instancia de AppState al importar este módulo (Singleton).
# Todos los archivos de la app importan `app_state` desde aquí para compartir
# el mismo estado en toda la aplicación.
app_state = AppState()
