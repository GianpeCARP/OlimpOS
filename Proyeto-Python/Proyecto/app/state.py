# =============================================================================
# state.py — Estado global de la aplicación (preparado para backend)
# =============================================================================
# Este módulo implementa el patrón "estado centralizado" (similar a un store).
# AppState es la única fuente de verdad sobre la sesión activa y los datos
# mostrados en la UI. En el futuro, cada método marcado con "TODO" se reemplaza
# con una llamada HTTP real al backend.
# La instancia global `app_state` se importa desde cualquier parte de la app.


class AppState:
    """
    Estado centralizado de la aplicación.
    En el futuro, este módulo se conectará con servicios/API reales.
    """

    def __init__(self):
        # ── Sesión de usuario ────────────────────────────────────────────────

        # Indica si hay un usuario autenticado. El router lo consulta como guard.
        self.logged_in: bool = False

        # Diccionario con los datos del usuario actual (id, username, name, role, avatar).
        # Es None si no hay sesión activa.
        self.current_user: dict | None = None

        # Ruta actualmente activa; permite saber en qué sección está el usuario.
        self.current_route: str = "login"

        # ── Datos mock (reemplazar con llamadas al backend) ──────────────────
        # Lista de usuarios que pueden iniciar sesión en el sistema.
        # Cuando se integre el backend, este bloque se elimina y `login()` hará
        # una petición POST a /api/auth/login.
        self._mock_users = [
            {
                "id": 1,
                "username": "admin",     # Nombre de usuario para el login
                "password": "admin123",  # Contraseña (sin hashear — solo para demo)
                "name": "Administrador", # Nombre a mostrar en la UI
                "role": "admin",         # Rol — controla acceso a secciones
                "avatar": "A",           # Inicial para el avatar circular
            },
            {
                "id": 2,
                "username": "trainer",
                "password": "train123",
                "name": "Carlos Pérez",
                "role": "trainer",       # Rol limitado — no ve la sección Usuarios
                "avatar": "C",
            },
        ]

    # ── Autenticación ─────────────────────────────────────────────────────────

    def login(self, username: str, password: str) -> tuple[bool, str]:
        """
        Intenta autenticar al usuario comparando contra _mock_users.
        TODO: reemplazar con llamada HTTP al backend (POST /api/auth/login).
        Retorna una tupla (éxito: bool, mensaje: str).
        Si el login es exitoso, actualiza logged_in y current_user.
        """
        for user in self._mock_users:
            # Compara usuario y contraseña con cada registro mock
            if user["username"] == username and user["password"] == password:
                self.logged_in   = True   # Marca la sesión como activa
                self.current_user = user  # Guarda el usuario autenticado
                return True, "OK"
        # Si ningún usuario coincidió, retorna fallo con mensaje de error
        return False, "Usuario o contraseña incorrectos"

    def logout(self):
        """
        Cierra la sesión actual limpiando el estado.
        Llama el sidebar (botón de logout) y redirige al login desde router.
        """
        self.logged_in    = False   # Invalida la sesión
        self.current_user = None    # Elimina datos del usuario activo
        self.current_route = "login" # Resetea la ruta activa

    # ── Getters de sesión ─────────────────────────────────────────────────────
    # Estos métodos proveen acceso seguro a los datos del usuario activo,
    # retornando valores por defecto si no hay sesión (evitan errores de None).

    def get_user_name(self) -> str:
        """Retorna el nombre para mostrar del usuario activo, o 'Invitado'."""
        if self.current_user:
            return self.current_user.get("name", "Usuario")
        return "Invitado"

    def get_user_role(self) -> str:
        """Retorna el rol del usuario activo, o 'guest' si no hay sesión."""
        if self.current_user:
            return self.current_user.get("role", "guest")
        return "guest"

    def get_user_avatar(self) -> str:
        """Retorna la inicial del avatar del usuario activo, o 'U'."""
        if self.current_user:
            return self.current_user.get("avatar", "U")
        return "U"

    def is_admin(self) -> bool:
        """Retorna True si el usuario activo tiene el rol 'admin'.
        El router usa este método para proteger la sección de Usuarios."""
        return self.get_user_role() == "admin"

    # ── Datos mock de socios ──────────────────────────────────────────────────

    def get_socios(self) -> list[dict]:
        """
        Retorna la lista de socios del gimnasio.
        TODO: reemplazar con GET /api/socios
        Cada socio tiene: id, nombre, plan, estado y fecha de vencimiento.
        """
        return [
            {"id": 1, "nombre": "Ana García",       "plan": "Premium",  "estado": "Activo",    "vence": "30/06/2025"},
            {"id": 2, "nombre": "Luis Martínez",     "plan": "Básico",   "estado": "Activo",    "vence": "15/05/2025"},
            {"id": 3, "nombre": "Sofía López",       "plan": "Premium",  "estado": "Vencido",   "vence": "01/04/2025"},
            {"id": 4, "nombre": "Marcos Rodríguez",  "plan": "Anual",    "estado": "Activo",    "vence": "10/12/2025"},
            {"id": 5, "nombre": "Valentina Torres",  "plan": "Básico",   "estado": "Suspendido","vence": "20/04/2025"},
            {"id": 6, "nombre": "Diego Fernández",   "plan": "Premium",  "estado": "Activo",    "vence": "28/07/2025"},
        ]

    # ── Datos mock de personal ────────────────────────────────────────────────

    def get_personal(self) -> list[dict]:
        """
        Retorna la lista de empleados del gimnasio.
        TODO: reemplazar con GET /api/personal
        Cada empleado tiene: id, nombre, rol, turno y estado.
        """
        return [
            {"id": 1, "nombre": "Carlos Pérez",    "rol": "Entrenador",     "turno": "Mañana",  "estado": "Activo"},
            {"id": 2, "nombre": "María Gómez",     "rol": "Nutricionista",  "turno": "Tarde",   "estado": "Activo"},
            {"id": 3, "nombre": "Roberto Silva",   "rol": "Recepcionista",  "turno": "Mañana",  "estado": "Activo"},
            {"id": 4, "nombre": "Natalia Cruz",    "rol": "Entrenadora",    "turno": "Noche",   "estado": "Activo"},
        ]

    # ── Datos mock de rutinas ─────────────────────────────────────────────────

    def get_rutinas(self) -> list[dict]:
        """
        Retorna el catálogo de rutinas de entrenamiento.
        TODO: reemplazar con GET /api/rutinas
        Cada rutina tiene: id, nombre, nivel, días por semana, duración y
        cantidad de socios asignados.
        """
        return [
            {"id": 1, "nombre": "Fuerza Total",    "nivel": "Avanzado",     "dias": 5, "duracion": "60 min", "asignados": 12},
            {"id": 2, "nombre": "Cardio Express",  "nivel": "Principiante", "dias": 3, "duracion": "30 min", "asignados": 25},
            {"id": 3, "nombre": "Hipertrofia Pro", "nivel": "Intermedio",   "dias": 4, "duracion": "75 min", "asignados": 8},
            {"id": 4, "nombre": "Full Body",       "nivel": "Principiante", "dias": 3, "duracion": "45 min", "asignados": 30},
            {"id": 5, "nombre": "HIIT Extreme",    "nivel": "Avanzado",     "dias": 4, "duracion": "40 min", "asignados": 15},
        ]

    # ── Datos mock de nutrición ───────────────────────────────────────────────

    def get_planes_nutricion(self) -> list[dict]:
        """
        Retorna los planes nutricionales disponibles.
        TODO: reemplazar con GET /api/nutricion
        Cada plan tiene: id, nombre, calorías diarias, objetivo y socios asignados.
        """
        return [
            {"id": 1, "nombre": "Volumen Limpio",  "calorias": 3200, "objetivo": "Masa muscular",    "asignados": 10},
            {"id": 2, "nombre": "Definición",      "calorias": 1800, "objetivo": "Bajar peso",       "asignados": 18},
            {"id": 3, "nombre": "Mantenimiento",   "calorias": 2400, "objetivo": "Mantenimiento",    "asignados": 22},
            {"id": 4, "nombre": "Rendimiento",     "calorias": 2800, "objetivo": "Alto rendimiento", "asignados": 7},
        ]

    # ── Stats del dashboard ───────────────────────────────────────────────────

    def get_dashboard_stats(self) -> dict:
        """
        Estadísticas principales del dashboard.
        TODO: reemplazar con GET /api/stats

        Cada métrica trae `valor` (el número grande) y `delta_pct` (la
        variación porcentual contra el período anterior). El texto del delta
        NO viene armado desde acá: la vista le pega la comparación que
        corresponde ("vs mes anterior", "vs ayer"), igual que hace
        textoDelta() en DashboardView.tsx de la PWA.
        """
        return {
            "socios_activos": {"valor": 148,       "delta_pct": 80.0},
            "ingresos_mes":   {"valor": 284500,    "delta_pct": -30.7},
            "clases_hoy":     {"valor": 9,         "delta_pct": 20.0},
            "nuevos_mes":     {"valor": 23,        "delta_pct": 33.3},
        }

    # ── Cobros ────────────────────────────────────────────────────────────────
    # Sección espejo de CobrosView.tsx de la PWA: recepción busca un socio, ve
    # su estado de cuenta y le cobra membresía, deuda, plan de actividad o
    # clase suelta.

    def get_tipos_membresia(self) -> list[dict]:
        """
        Planes de membresía que se pueden cobrar.
        TODO: reemplazar con GET /api/tipos-membresia
        """
        return [
            {"id": 1, "nombre": "Mensual Full",     "dias": 30,  "precio": 28000},
            {"id": 2, "nombre": "Mensual Básico",   "dias": 30,  "precio": 19500},
            {"id": 3, "nombre": "Trimestral Full",  "dias": 90,  "precio": 75000},
            {"id": 4, "nombre": "Pase Libre Anual", "dias": 365, "precio": 260000},
        ]

    def get_cuenta_socio(self, id_socio: int) -> dict:
        """
        Estado de cuenta de un socio: su membresía, lo que debe y lo que pagó.
        TODO: reemplazar con GET /api/socios/{id}/cuenta
        """
        return {
            "plan": "Mensual Full",
            "estado": "Por vencer",
            "vencimiento": "11/08/2026",
            "deudas": [
                {"id": 1, "monto": 21600, "generada": "01/07/2026",
                 "detalle": "Cuota mensual del plan anual", "dias_atraso": 8},
            ],
            "total_adeudado": 21600,
            "pagos": [
                {"id": 1, "fecha": "04/08/2026", "monto": 28000, "metodo": "Efectivo",
                 "estado": "Confirmado", "comprobante": "A-000113"},
                {"id": 2, "fecha": "06/07/2026", "monto": 28000, "metodo": "Transferencia",
                 "estado": "Confirmado", "comprobante": "A-000102"},
                {"id": 3, "fecha": "05/06/2026", "monto": 28000, "metodo": "Débito",
                 "estado": "Confirmado", "comprobante": "A-000091"},
            ],
        }

    def get_metodos_pago(self) -> list[str]:
        """Medios de pago aceptados (enum metodo_pago del esquema)."""
        return ["Efectivo", "Débito", "Crédito", "Transferencia", "Billetera virtual"]

    # ── Asistencia ────────────────────────────────────────────────────────────
    # Espejo de AsistenciaView.tsx: fichaje por tarjeta RFID + carga manual.

    def get_asistencias_hoy(self) -> list[dict]:
        """
        Fichajes del día en la sede activa, del más reciente al más viejo.
        TODO: reemplazar con GET /api/asistencias?fecha=hoy
        """
        return [
            {"id": 5, "socio": "Sofía Ledesma",     "hora": "19:42", "metodo": "RFID"},
            {"id": 4, "socio": "Diego Sosa",        "hora": "19:15", "metodo": "RFID"},
            {"id": 3, "socio": "Valentina Ríos",    "hora": "18:58", "metodo": "Manual"},
            {"id": 2, "socio": "Nicolás Paz",       "hora": "18:30", "metodo": "RFID"},
            {"id": 1, "socio": "Federico Arce",     "hora": "17:47", "metodo": "RFID"},
        ]

    # ── Actividades ───────────────────────────────────────────────────────────
    # Espejo de ActividadesAdminView.tsx: ABM del catálogo (actividad + sus
    # planes) y asignación de profesores.

    def get_actividades(self) -> list[dict]:
        """
        Catálogo de actividades con sus planes y profesores asignados.
        TODO: reemplazar con GET /api/actividades
        """
        return [
            {
                "id": 1, "nombre": "Musculación", "activa": True,
                "descripcion": "Acceso libre a la sala de musculación y cardio.",
                "cupo": 40, "precio_suelta": 3500, "horas_cancelacion": 0,
                "profesores": [],
                "planes": [
                    {"id": 1, "nombre": "12 clases al mes", "tipo": "POR_MES",    "cantidad": 12, "precio": 28000, "activo": True},
                    {"id": 2, "nombre": "20 clases al mes", "tipo": "POR_MES",    "cantidad": 20, "precio": 42000, "activo": True},
                ],
            },
            {
                "id": 2, "nombre": "Yoga", "activa": True,
                "descripcion": "Clase de yoga para todos los niveles.",
                "cupo": 20, "precio_suelta": 4500, "horas_cancelacion": 12,
                "profesores": ["Romina Duarte"],
                "planes": [
                    {"id": 3, "nombre": "2 veces por semana", "tipo": "POR_SEMANA", "cantidad": 2, "precio": 15000, "activo": True},
                    {"id": 4, "nombre": "8 clases al mes",    "tipo": "POR_MES",    "cantidad": 8, "precio": 26000, "activo": True},
                ],
            },
            {
                "id": 3, "nombre": "Boxeo", "activa": True,
                "descripcion": "Clase de boxeo recreativo, grupal.",
                "cupo": 15, "precio_suelta": 5000, "horas_cancelacion": 24,
                "profesores": ["Romina Duarte"],
                "planes": [
                    {"id": 5, "nombre": "3 veces por semana", "tipo": "POR_SEMANA", "cantidad": 3,  "precio": 20000, "activo": True},
                    {"id": 6, "nombre": "12 clases al mes",   "tipo": "POR_MES",    "cantidad": 12, "precio": 45000, "activo": True},
                ],
            },
        ]

    def get_profesores(self) -> list[dict]:
        """
        Profesores activos, para el diálogo de asignación.
        TODO: reemplazar con GET /api/profesores
        """
        return [
            {"id": 1, "nombre": "Romina Duarte", "especialidad": "Yoga y Boxeo recreativo"},
            {"id": 2, "nombre": "Bruno Ferrari", "especialidad": "Crossfit y funcional"},
        ]

    def get_actividad_reciente(self) -> list[dict]:
        """
        Retorna las últimas actividades del sistema para el feed del dashboard.
        TODO: reemplazar con GET /api/actividad?limit=5
        Cada actividad tiene: tipo (determina el ícono), descripción y hora relativa.
        """
        # Mismos textos que arma dashboardService.ts en la PWA: los
        # vencimientos se redactan en futuro ("Vence la membresía de…") porque
        # son los que piden una acción, y los pagos en pasado con el monto.
        return [
            {"tipo": "vencimiento", "desc": "Vence la membresía de Julieta Molina",  "hora": "dentro de 6 días"},
            {"tipo": "vencimiento", "desc": "Vence la membresía de Martín Gómez",    "hora": "dentro de 3 días"},
            {"tipo": "pago",        "desc": "Martín Gómez pagó $ 28.000",             "hora": "hace 4 días"},
            {"tipo": "nuevo_socio", "desc": "Sofía Ledesma se dio de alta como socio","hora": "hace 4 días"},
            {"tipo": "pago",        "desc": "Diego Sosa pagó $ 37.500",               "hora": "hace 4 días"},
        ]


# ── Instancia global única ─────────────────────────────────────────────────────
# Se crea una sola instancia de AppState al importar este módulo (Singleton).
# Todos los archivos de la app importan `app_state` desde aquí para compartir
# el mismo estado en toda la aplicación.
app_state = AppState()
