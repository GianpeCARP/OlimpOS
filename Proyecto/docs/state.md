# Estructura Lógica — `state.py` (Estado Global de la Aplicación)

Este documento detalla la estructura de programación y variables del archivo `state.py`. Este módulo implementa un patrón de estado centralizado (Store/Singleton) y funciona como la única fuente de verdad sobre la sesión activa y los datos de la interfaz.

## Dependencias e Importaciones
*   No posee dependencias externas (usa la biblioteca estándar de Python).

## Variables Globales (Exportadas)
*   **`app_state`**: Instancia única de la clase `AppState` creada al final del archivo. 
    *   *Razón de creación:* Implementa el patrón Singleton. Todos los demás archivos importan esta variable exacta para compartir el mismo espacio de memoria y estado (por ejemplo, saber si el usuario está logueado desde cualquier vista).

## Clase: `AppState`

### Variables de Instancia (Propiedades)
Inicializadas en `__init__(self)`:
*   **`self.logged_in`**: (Booleano) Indica si hay una sesión activa. Iniciado en `False`.
*   **`self.current_user`**: (Diccionario | None) Almacena los datos del usuario autenticado (`id`, `username`, `name`, `role`, `avatar`). Iniciado en `None`.
*   **`self.current_route`**: (String) Rastrea la sección actual. Iniciado en `"login"`.
*   **`self._mock_users`**: (Lista de diccionarios) Estructura temporal que simula la base de datos de usuarios autorizados.

### Métodos de Autenticación
*   **`login(self, username, password)`**: 
    *   *Propósito:* Validar credenciales. (Actualmente contra `_mock_users`, a futuro mediante API).
    *   *Retorno:* `Tuple[bool, str]` (Estado de éxito y mensaje).
    *   *Mutaciones:* Si es exitoso, cambia `self.logged_in = True` y guarda el objeto usuario en `self.current_user`.
*   **`logout(self)`**:
    *   *Propósito:* Limpiar la sesión.
    *   *Mutaciones:* `self.logged_in = False`, `self.current_user = None`, `self.current_route = "login"`.

### Métodos Getters (Lectura de Sesión)
Proporcionan acceso seguro a los atributos de `current_user`, devolviendo valores por defecto si es `None`:
*   **`get_user_name(self)`**: Retorna `name` o "Invitado".
*   **`get_user_role(self)`**: Retorna `role` o "guest".
*   **`get_user_avatar(self)`**: Retorna `avatar` o "U".
*   **`is_admin(self)`**: Retorna un booleano (True si el rol es "admin"). Usado por el router para proteger rutas.

### Métodos Mock (Proveedores de Datos)
Retornan listas de diccionarios o diccionarios anidados para poblar las vistas. Pensados para ser reemplazados por llamadas HTTP (GET):
*   **`get_socios(self)`**: Estructura requerida: `id`, `nombre`, `plan`, `estado`, `vence`.
*   **`get_personal(self)`**: Estructura requerida: `id`, `nombre`, `rol`, `turno`, `estado`.
*   **`get_rutinas(self)`**: Estructura requerida: `id`, `nombre`, `nivel`, `dias`, `duracion`, `asignados`.
*   **`get_planes_nutricion(self)`**: Estructura requerida: `id`, `nombre`, `calorias`, `objetivo`, `asignados`.
*   **`get_dashboard_stats(self)`**: Retorna diccionario con métricas clave (socios_activos, ingresos_mes, clases_hoy, nuevos_mes), conteniendo a su vez `valor`, `delta` y `tendencia`.
*   **`get_actividad_reciente(self)`**: Estructura requerida: `tipo`, `desc`, `hora`.
