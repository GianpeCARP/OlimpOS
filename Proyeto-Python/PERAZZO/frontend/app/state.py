# =============================================================================
# state.py — Estado global de la aplicación, conectado a la API real
# =============================================================================
# A partir de esta revisión, Socio y Empleado ya no llevan sus propios
# datos personales: se leen siempre de Persona (por eso get_socios() y
# get_personal() ya no necesitan "armar" un nombre completo desde dos
# campos separados — el backend ya lo entrega armado).
# El alta de las tres "funciones" (Socio, Empleado, Usuario) ahora se
# orquesta en un único lugar: ver crear_persona_completa(), usada por
# la vista Nueva Persona.

from datetime import datetime

from app import api_client

# ── Traducciones backend (ASCII) ⇄ frontend (español) ────────────────────────

PLAN_DISPLAY = {"BASICO": "Básico", "PREMIUM": "Premium", "ANUAL": "Anual"}
PLAN_BACKEND = {v: k for k, v in PLAN_DISPLAY.items()}

ESTADO_SOCIO_DISPLAY = {"ACTIVO": "Activo", "VENCIDO": "Vencido", "SUSPENDIDO": "Suspendido"}
ESTADO_SOCIO_BACKEND = {v: k for k, v in ESTADO_SOCIO_DISPLAY.items()}

TURNO_LABORAL_DISPLAY = {"MANANA": "Mañana", "TARDE": "Tarde", "NOCHE": "Noche"}
TURNO_LABORAL_BACKEND = {v: k for k, v in TURNO_LABORAL_DISPLAY.items()}

ESTADO_EMPLEADO_DISPLAY = {"ACTIVO": "Activo", "INACTIVO": "Inactivo"}
ESTADO_EMPLEADO_BACKEND = {v: k for k, v in ESTADO_EMPLEADO_DISPLAY.items()}

NIVEL_DISPLAY = {"PRINCIPIANTE": "Principiante", "INTERMEDIO": "Intermedio", "AVANZADO": "Avanzado"}
NIVEL_BACKEND = {v: k for k, v in NIVEL_DISPLAY.items()}

OBJETIVO_DISPLAY = {
    "MASA_MUSCULAR": "Masa muscular", "BAJAR_PESO": "Bajar peso",
    "MANTENIMIENTO": "Mantenimiento", "ALTO_RENDIMIENTO": "Alto rendimiento",
}
OBJETIVO_BACKEND = {v: k for k, v in OBJETIVO_DISPLAY.items()}

DIA_SEMANA_DISPLAY = {
    "LUNES": "Lunes", "MARTES": "Martes", "MIERCOLES": "Miércoles",
    "JUEVES": "Jueves", "VIERNES": "Viernes", "SABADO": "Sábado", "DOMINGO": "Domingo",
}
DIA_SEMANA_BACKEND = {v: k for k, v in DIA_SEMANA_DISPLAY.items()}
DIAS_SEMANA_ORDEN = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

# Roles/funciones — el mismo enum se usa tanto para Empleado.rol como para
# Usuario.rol. "Socio" no es un rol de sistema: se maneja aparte (crea un
# registro en la tabla Socio, no en Empleado).
ROL_DISPLAY = {
    "PROPIETARIO": "Propietario", "ADMIN": "Administrador",
    "ENTRENADOR": "Entrenador", "NUTRICIONISTA": "Nutricionista",
    "RECEPCION": "Recepción",
}
ROL_BACKEND = {v: k for k, v in ROL_DISPLAY.items()}

ROLES_ADMINISTRATIVOS = ("PROPIETARIO", "ADMIN")


def _formatear_fecha(fecha_iso) -> str:
    if not fecha_iso:
        return "-"
    try:
        return datetime.strptime(fecha_iso, "%Y-%m-%d").strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return str(fecha_iso)


class AppState:
    """Estado centralizado de la aplicación, respaldado por la API real."""

    def __init__(self):
        self.logged_in: bool = False
        self.current_user: dict | None = None
        self.current_route: str = "login"
        self.email_pendiente_cambio: str | None = None

    # ── Autenticación ─────────────────────────────────────────────────────────

    def login(self, email: str, password: str) -> dict:
        resultado = api_client.login(email, password)
        if not resultado["ok"]:
            return {"ok": False, "mensaje": resultado["error"]}

        datos = resultado["data"]
        if datos["debe_cambiar_password"]:
            self.email_pendiente_cambio = email
            return {"ok": True, "requiere_cambio": True}

        api_client.guardar_token(datos["access_token"])
        self.logged_in = True
        self.current_user = {"nombre": datos.get("nombre") or "Usuario", "role": datos.get("rol")}
        return {"ok": True, "requiere_cambio": False}

    def cambiar_password(self, password_actual: str, password_nueva: str) -> dict:
        if not self.email_pendiente_cambio:
            return {"ok": False, "mensaje": "No hay una sesión pendiente de cambio de contraseña."}
        resultado = api_client.cambiar_password(self.email_pendiente_cambio, password_actual, password_nueva)
        if not resultado["ok"]:
            return {"ok": False, "mensaje": resultado["error"]}
        self.email_pendiente_cambio = None
        return {"ok": True}

    def logout(self):
        api_client.limpiar_token()
        self.logged_in = False
        self.current_user = None
        self.current_route = "login"

    def get_user_name(self) -> str:
        return self.current_user.get("nombre", "Usuario") if self.current_user else "Invitado"

    def get_user_role(self) -> str:
        return self.current_user.get("role", "guest") if self.current_user else "guest"

    def get_user_avatar(self) -> str:
        nombre = self.get_user_name()
        return nombre[0].upper() if nombre else "U"

    def is_admin(self) -> bool:
        return self.get_user_role() in ROLES_ADMINISTRATIVOS

    # ── Personas (alta unificada) ────────────────────────────────────────────

    def buscar_persona(self, dni: str) -> dict:
        """
        Busca una Persona por DNI. Devuelve, además de sus datos, los
        flags tiene_socio / tiene_empleado / tiene_usuario para que la
        pantalla "Nueva Persona" sepa qué funciones ya tiene y cuáles
        todavía se pueden agregar.
        """
        resultado = api_client.obtener_persona(dni)
        if not resultado["ok"]:
            return {"ok": False, "mensaje": resultado["error"]}
        return {"ok": True, "persona": resultado["data"]}

    def crear_persona_completa(self, persona_existe: bool, dni: str, nombre: str, apellido: str,
                                telefono: str = None, email: str = None, calle: str = None,
                                numero: str = None, localidad: str = None,
                                funcion: str = None, plan_display: str = None,
                                turno_display: str = None,
                                crear_acceso: bool = False, email_acceso: str = None,
                                password_inicial: str = None) -> dict:
        """
        Orquesta el alta unificada, en el orden correcto:
        1. Crea (o no toca, si ya existía) la Persona.
        2. Según la función elegida, crea el Socio o el Empleado.
        3. Si se pidió, crea además el acceso al sistema (Usuario).
        Devuelve {"ok": True} o {"ok": False, "mensaje": "..."} apenas
        falla el primer paso que no se pudo completar.
        """
        if not persona_existe:
            datos_persona = {
                "dni": dni, "nombre": nombre, "apellido": apellido,
                "telefono": telefono or None, "email": email or None,
                "calle": calle or None, "numero": numero or None, "localidad": localidad or None,
            }
            resultado = api_client.crear_persona(datos_persona)
            if not resultado["ok"]:
                return {"ok": False, "mensaje": resultado["error"]}

        if funcion == "SOCIO":
            resultado = api_client.crear_socio({
                "dni": dni,
                "plan": PLAN_BACKEND.get(plan_display, "BASICO"),
                "estado": "ACTIVO",
            })
            if not resultado["ok"]:
                return {"ok": False, "mensaje": resultado["error"]}
        elif funcion:
            resultado = api_client.crear_empleado({
                "dni": dni, "rol": funcion,
                "turno": TURNO_LABORAL_BACKEND.get(turno_display, "MANANA"),
                "estado": "ACTIVO",
            })
            if not resultado["ok"]:
                return {"ok": False, "mensaje": resultado["error"]}

        if crear_acceso:
            resultado = api_client.crear_usuario({
                "dni": dni,
                "email": email_acceso or email,
                "rol": funcion or "RECEPCION",
                "password_inicial": password_inicial,
            })
            if not resultado["ok"]:
                return {"ok": False, "mensaje": resultado["error"]}

        return {"ok": True}

    # ── Usuarios del sistema (solo consulta y modificación) ─────────────────

    def get_usuarios(self) -> list[dict]:
        resultado = api_client.obtener_usuarios()
        if not resultado["ok"]:
            return []
        lista = []
        for u in resultado["data"]:
            lista.append({
                "id": u["id"], "dni": u["dni"], "nombre": u["nombre"],
                "username": u["email"], "role": u["rol"],
                "estado": "Activo" if u["activo"] else "Inactivo",
            })
        return lista

    def actualizar_usuario(self, usuario_id: int, rol: str) -> dict:
        resultado = api_client.actualizar_usuario(usuario_id, {"rol": rol})
        return {"ok": resultado["ok"], "mensaje": resultado.get("error")}

    def resetear_password_usuario(self, usuario_id: int) -> dict:
        resultado = api_client.resetear_password_usuario(usuario_id)
        if not resultado["ok"]:
            return {"ok": False, "mensaje": resultado["error"]}
        return {"ok": True, "mensaje": resultado["data"]["mensaje"],
                "password_temporal": resultado["data"]["password_temporal"]}

    def alternar_estado_usuario(self, usuario_id: int) -> dict:
        resultado = api_client.alternar_estado_usuario(usuario_id)
        return {"ok": resultado["ok"], "mensaje": resultado.get("error")}

    # ── Socios (solo consulta y modificación) ────────────────────────────────

    def get_socios(self) -> list[dict]:
        resultado = api_client.obtener_socios()
        if not resultado["ok"]:
            return []
        lista = []
        for s in resultado["data"]:
            lista.append({
                "dni": s["dni"],
                "nombre": f"{s['nombre']} {s['apellido']}".strip(),
                "plan": PLAN_DISPLAY.get(s["plan"], s["plan"]),
                "estado": ESTADO_SOCIO_DISPLAY.get(s["estado"], s["estado"]),
                "vence": _formatear_fecha(s.get("fecha_vencimiento")),
                "email": s.get("email"), "telefono": s.get("telefono"),
            })
        return lista

    def actualizar_socio(self, dni: str, plan_display: str, estado_display: str) -> dict:
        datos = {
            "plan": PLAN_BACKEND.get(plan_display, "BASICO"),
            "estado": ESTADO_SOCIO_BACKEND.get(estado_display, "ACTIVO"),
        }
        resultado = api_client.actualizar_socio(dni, datos)
        return {"ok": resultado["ok"], "mensaje": resultado.get("error")}

    def eliminar_socio(self, dni: str) -> dict:
        resultado = api_client.eliminar_socio(dni)
        return {"ok": resultado["ok"], "mensaje": resultado.get("error")}

    # ── Personal (solo consulta y modificación) ──────────────────────────────

    def get_personal(self) -> list[dict]:
        resultado = api_client.obtener_personal()
        if not resultado["ok"]:
            return []
        lista = []
        for p in resultado["data"]:
            lista.append({
                "dni": p["dni"],
                "nombre": f"{p['nombre']} {p['apellido']}".strip(),
                "rol": ROL_DISPLAY.get(p["rol"], p["rol"]),
                "turno": TURNO_LABORAL_DISPLAY.get(p["turno"], p["turno"]),
                "estado": ESTADO_EMPLEADO_DISPLAY.get(p["estado"], p["estado"]),
                "email": p.get("email"),
            })
        return lista

    def actualizar_empleado(self, dni: str, rol_display: str, turno_display: str, estado_display: str) -> dict:
        datos = {
            "rol": ROL_BACKEND.get(rol_display, "RECEPCION"),
            "turno": TURNO_LABORAL_BACKEND.get(turno_display, "MANANA"),
            "estado": ESTADO_EMPLEADO_BACKEND.get(estado_display, "ACTIVO"),
        }
        resultado = api_client.actualizar_empleado(dni, datos)
        return {"ok": resultado["ok"], "mensaje": resultado.get("error")}

    # ── Rutinas ───────────────────────────────────────────────────────────────

    def get_rutinas(self) -> list[dict]:
        resultado = api_client.obtener_rutinas()
        if not resultado["ok"]:
            return []
        lista = []
        for r in resultado["data"]:
            lista.append({
                "id": r["id"], "nombre": r["nombre"],
                "nivel": NIVEL_DISPLAY.get(r["nivel"], r["nivel"]),
                "dias": r["dias_por_semana"], "duracion": f"{r['duracion_minutos']} min",
                "asignados": r["asignados"],
            })
        return lista

    def crear_rutina(self, nombre: str, nivel_display: str, dias: int, duracion_minutos: int,
                      descripcion: str = None) -> dict:
        datos = {
            "nombre": nombre, "nivel": NIVEL_BACKEND.get(nivel_display, "PRINCIPIANTE"),
            "dias_por_semana": dias, "duracion_minutos": duracion_minutos, "descripcion": descripcion or None,
        }
        resultado = api_client.crear_rutina(datos)
        return {"ok": resultado["ok"], "mensaje": resultado.get("error")}

    def asignar_rutina(self, rutina_id: int, socio_dni: str) -> dict:
        resultado = api_client.asignar_rutina(rutina_id, socio_dni)
        if not resultado["ok"]:
            return {"ok": False, "mensaje": resultado["error"]}
        return {"ok": True, "mensaje": resultado["data"].get("mensaje", "Rutina asignada.")}

    # ── Nutrición ─────────────────────────────────────────────────────────────

    def get_planes_nutricion(self) -> list[dict]:
        resultado = api_client.obtener_planes_nutricion()
        if not resultado["ok"]:
            return []
        lista = []
        for p in resultado["data"]:
            lista.append({
                "id": p["id"], "nombre": p["nombre"], "calorias": p["calorias"],
                "objetivo": OBJETIVO_DISPLAY.get(p["objetivo"], p["objetivo"]),
                "asignados": p["asignados"],
                "proteinas_g": p.get("proteinas_g"), "carbohidratos_g": p.get("carbohidratos_g"),
                "grasas_g": p.get("grasas_g"),
            })
        return lista

    def crear_plan_nutricion(self, nombre: str, objetivo_display: str, calorias: int,
                              proteinas_g: int = None, carbohidratos_g: int = None,
                              grasas_g: int = None, notas: str = None) -> dict:
        datos = {
            "nombre": nombre, "calorias": calorias,
            "objetivo": OBJETIVO_BACKEND.get(objetivo_display, "MANTENIMIENTO"),
            "proteinas_g": proteinas_g, "carbohidratos_g": carbohidratos_g,
            "grasas_g": grasas_g, "notas": notas or None,
        }
        resultado = api_client.crear_plan_nutricion(datos)
        return {"ok": resultado["ok"], "mensaje": resultado.get("error")}

    def asignar_plan_nutricion(self, plan_id: int, socio_dni: str) -> dict:
        resultado = api_client.asignar_plan_nutricion(plan_id, socio_dni)
        if not resultado["ok"]:
            return {"ok": False, "mensaje": resultado["error"]}
        return {"ok": True, "mensaje": resultado["data"].get("mensaje", "Plan asignado.")}

    # ── Turnos ────────────────────────────────────────────────────────────────

    def get_turnos(self) -> list[dict]:
        resultado = api_client.obtener_turnos()
        if not resultado["ok"]:
            return []
        lista = []
        for t in resultado["data"]:
            lista.append({
                "id": t["id"], "nombre": t["nombre"],
                "dia": DIA_SEMANA_DISPLAY.get(t["dia_semana"], t["dia_semana"]),
                "hora_inicio": t["hora_inicio"], "hora_fin": t["hora_fin"],
                "instructor_dni": t.get("instructor_dni"),
                "instructor": t.get("instructor_nombre") or "Sin asignar",
                "cupo_maximo": t["cupo_maximo"], "inscriptos": t["inscriptos"], "color": t["color"],
            })
        return lista

    def crear_turno(self, nombre: str, dia_display: str, hora_inicio: str, hora_fin: str,
                     instructor_dni: str = None, cupo_maximo: int = 15, color: str = "#FF5722") -> dict:
        datos = {
            "nombre": nombre, "dia_semana": DIA_SEMANA_BACKEND.get(dia_display, "LUNES"),
            "hora_inicio": hora_inicio, "hora_fin": hora_fin,
            "instructor_dni": instructor_dni or None, "cupo_maximo": cupo_maximo, "color": color,
        }
        resultado = api_client.crear_turno(datos)
        return {"ok": resultado["ok"], "mensaje": resultado.get("error")}

    def eliminar_turno(self, turno_id: int) -> dict:
        resultado = api_client.eliminar_turno(turno_id)
        return {"ok": resultado["ok"], "mensaje": resultado.get("error")}

    def inscribir_socio_turno(self, turno_id: int, socio_dni: str) -> dict:
        resultado = api_client.inscribir_socio_turno(turno_id, socio_dni)
        if not resultado["ok"]:
            return {"ok": False, "mensaje": resultado["error"]}
        return {"ok": True, "mensaje": resultado["data"].get("mensaje", "Inscripción realizada.")}

    # ── Dashboard ─────────────────────────────────────────────────────────────

    def get_dashboard_stats(self) -> dict:
        resultado = api_client.obtener_dashboard_stats()
        if not resultado["ok"]:
            vacio = {"valor": "0", "delta": "+0", "tendencia": "up"}
            return {"socios_activos": vacio, "ingresos_mes": vacio, "clases_hoy": vacio, "nuevos_mes": vacio}
        return resultado["data"]

    def get_actividad_reciente(self) -> list[dict]:
        resultado = api_client.obtener_actividad_reciente()
        if not resultado["ok"]:
            return []
        return resultado["data"]


app_state = AppState()
