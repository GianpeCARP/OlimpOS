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
        Retorna las estadísticas principales del dashboard.
        TODO: reemplazar con GET /api/stats
        Cada métrica tiene: valor (lo que se muestra grande), delta (variación
        respecto al período anterior) y tendencia ('up' o 'down').
        """
        return {
            "socios_activos": {"valor": 148,        "delta": "+12", "tendencia": "up"},
            "ingresos_mes":   {"valor": "$284.500",  "delta": "+8%", "tendencia": "up"},
            "clases_hoy":     {"valor": 9,           "delta": "-1",  "tendencia": "down"},
            "nuevos_mes":     {"valor": 23,          "delta": "+5",  "tendencia": "up"},
        }

    def get_actividad_reciente(self) -> list[dict]:
        """
        Retorna las últimas actividades del sistema para el feed del dashboard.
        TODO: reemplazar con GET /api/actividad?limit=5
        Cada actividad tiene: tipo (determina el ícono), descripción y hora relativa.
        """
        return [
            {"tipo": "nuevo_socio", "desc": "Ana García se registró al plan Premium",  "hora": "Hace 5 min"},
            {"tipo": "pago",        "desc": "Luis Martínez renovó su membresía",       "hora": "Hace 23 min"},
            {"tipo": "rutina",      "desc": "Rutina HIIT Extreme asignada a 3 socios", "hora": "Hace 1 hora"},
            {"tipo": "vencimiento", "desc": "Sofía López - membresía vencida",          "hora": "Hace 2 horas"},
            {"tipo": "nuevo_socio", "desc": "Diego Fernández inició plan Anual",        "hora": "Hace 3 horas"},
        ]


# ── Instancia global única ─────────────────────────────────────────────────────
# Se crea una sola instancia de AppState al importar este módulo (Singleton).
# Todos los archivos de la app importan `app_state` desde aquí para compartir
# el mismo estado en toda la aplicación.
app_state = AppState()
