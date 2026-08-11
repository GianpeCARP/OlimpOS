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

from datetime import datetime

from app import api_client

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

        api_client.guardar_token(datos["token"])

        persona = datos.get("persona") or {}
        nombre = f"{persona.get('nombre', '')} {persona.get('apellido', '')}".strip()

        self.logged_in = True
        self.current_user = {
            "username": datos["usuario"]["username"],
            "name": nombre or datos["usuario"]["username"],
            # Lista, no string: los roles se acumulan (el dueño que además es
            # socio del gimnasio tiene los dos).
            "roles": datos.get("roles", []),
            "avatar": (nombre or "U")[0].upper(),
            "id_socio": datos.get("idSocio"),
        }
        self.username_pendiente_cambio = None
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

    def is_admin(self) -> bool:
        """
        True si la sesión puede administrar el sistema.

        Provisorio: es el reemplazo mínimo del chequeo anterior contra el rol
        'admin', que ya no existe — los roles ahora son los cinco reales
        ('dueno', 'recepcionista', 'entrenador', 'nutricionista', 'socio').
        Lo correcto es evaluar la matriz de permisos por sección, igual que
        hace la PWA con PERMISOS de config.ts y el backend con permisos.py.
        TODO: portar esa matriz a Flet y reemplazar este método.
        """
        return any(rol in ("dueno", "recepcionista") for rol in self.get_user_roles())

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
            }
            for s in datos
        ]

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
                "nombre": f"{e['nombre']} {e['apellido']}".strip(),
                "rol": e.get("rol") or "Sin asignar",
                "turno": e.get("turno_laboral") or "—",
                "estado": "Activo" if e.get("activo") else "Inactivo",
            }
            for e in datos
        ]

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
                "nivel": r.get("nivel") or "Sin nivel",
                "dias": r.get("dias_por_semana") or 0,
                "duracion": r.get("objetivo") or "—",
                "asignados": r.get("asignados", 0),
            }
            for r in datos
        ]

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
            }
            for d in datos
        ]

    # ── Dashboard ─────────────────────────────────────────────────────────────

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
                 "deudas": [], "total_adeudado": 0, "pagos": []}
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
            "estado": "Al día" if datos.get("al_dia") else "Con deuda",
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
                "precio_suelta": a.get("precio_clase_suelta", 0),
                "horas_cancelacion": a.get("horas_anticipacion_cancelacion", 0),
                "profesores": [p.get("nombre", "?") for p in profesores],
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

    def fichar_rfid(self, codigo: str) -> dict:
        """
        Ficha por tarjeta.

        Puede volver ok=True con una `advertencia`: el backend registra el
        ingreso AUNQUE el socio deba o tenga la cuota vencida. Es una decisión
        de negocio — dejar a alguien afuera lo decide una persona en el
        mostrador, no un torniquete — y además, si no se registrara, el
        gimnasio perdería el dato de que esa persona estuvo.
        """
        return self._fichaje(api_client.fichar_rfid(codigo))

    def fichar_manual(self, id_socio: int) -> dict:
        """Carga manual, para quien se olvidó la tarjeta."""
        return self._fichaje(api_client.fichar_manual(id_socio))

    def _fichaje(self, respuesta: dict) -> dict:
        if not respuesta.get("ok"):
            return {"ok": False, "mensaje": respuesta.get("error", "No se pudo fichar.")}

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
            },
        }

    # ── Cobros ────────────────────────────────────────────────────────────────

    def cobrar_membresia(self, id_socio: int, id_tipo: int, metodo_display: str,
                          comprobante: str | None = None) -> dict:
        """
        Cobra una membresía.

        NO manda el monto: lo calcula el backend a partir del plan. Si viniera
        de acá, cualquiera con la app abierta podría cobrar $1 una membresía de
        $30.000 — y en la base quedaría un pago perfectamente válido.
        """
        return self._resultado(api_client.cobrar({
            "id_socio": id_socio,
            "id_tipo_membresia": id_tipo,
            "metodo": METODO_PAGO_BACKEND.get(metodo_display, "EFECTIVO"),
            "numero_comprobante": comprobante or None,
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
        return self._resultado(api_client.crear_actividad(datos), "Actividad creada.")

    def editar_actividad(self, id_actividad: int, datos: dict) -> dict:
        return self._resultado(api_client.editar_actividad(id_actividad, datos),
                                "Actividad actualizada.")

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
        }

    def dar_de_baja_socio(self, id_socio: int, tipo: str = "VOLUNTARIA",
                           motivo: str | None = None) -> dict:
        return self._resultado(api_client.dar_de_baja_socio(id_socio, tipo, motivo),
                                "Socio dado de baja.")

    def reactivar_socio(self, id_socio: int) -> dict:
        return self._resultado(api_client.reactivar_socio(id_socio), "Socio reactivado.")

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
        }

    # ── Rutinas y nutrición ───────────────────────────────────────────────────

    def crear_rutina(self, datos: dict) -> dict:
        return self._resultado(api_client.crear_rutina(datos), "Rutina creada.")

    def asignar_rutina(self, id_rutina: int, id_socio: int) -> dict:
        return self._resultado(api_client.asignar_rutina(id_rutina, id_socio),
                                "Rutina asignada.")

    def crear_dieta(self, datos: dict) -> dict:
        return self._resultado(api_client.crear_dieta(datos), "Plan nutricional creado.")

    def asignar_dieta(self, id_dieta: int, id_socio: int) -> dict:
        return self._resultado(api_client.asignar_dieta(id_dieta, id_socio),
                                "Plan asignado.")

    def get_ejercicios(self) -> list[dict]:
        datos = self._datos(api_client.obtener_ejercicios(), [])
        return [
            {"id": e["id_ejercicio"], "nombre": e["nombre"],
             "grupo": e.get("grupo_muscular", "—")}
            for e in datos
        ]

    # ── Usuarios ──────────────────────────────────────────────────────────────

    def get_usuarios(self) -> list[dict]:
        datos = self._datos(api_client.obtener_usuarios(), [])
        return [
            {
                "id": u["id_usuario"],
                "usuario": u["username"],
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
                "usuario": d.get("username"), "password_temporal": d.get("password_temporal")}

    def desbloquear_usuario(self, id_usuario: int) -> dict:
        return self._resultado(api_client.desbloquear_usuario(id_usuario), "Cuenta desbloqueada.")

    def cambiar_estado_usuario(self, id_usuario: int) -> dict:
        return self._resultado(api_client.cambiar_estado_usuario(id_usuario),
                                "Estado de la cuenta actualizado.")


# ── Instancia global única ─────────────────────────────────────────────────────
# Se crea una sola instancia de AppState al importar este módulo (Singleton).
# Todos los archivos de la app importan `app_state` desde aquí para compartir
# el mismo estado en toda la aplicación.
app_state = AppState()
