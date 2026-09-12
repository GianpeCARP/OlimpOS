# OlimpOS — Sistema de Gestión de Gimnasios

Sistema frontend modular desarrollado con **Flet** y **Python** (programación estructurada).

---

## 🚀 Instalación y ejecución

```bash
# 1. Crear entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate      # Linux / macOS
venv\Scripts\activate         # Windows

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Ejecutar
python main.py
```

---

## 🔑 Credenciales de demo

| Usuario   | Contraseña  | Rol           |
|-----------|-------------|---------------|
| admin     | admin123    | Administrador |
| trainer   | train123    | Entrenador    |

---

## 📁 Estructura del proyecto

```
gymapp/
│
├── main.py                    # Punto de entrada
├── requirements.txt
│
└── app/
    ├── config.py              # Configuración global (colores, rutas, constantes)
    ├── state.py               # Estado global (datos mock → reemplazar con API)
    ├── router.py              # Navegación centralizada
    │
    ├── components/
    │   ├── ui.py              # Componentes reutilizables (sidebar, topbar, cards...)
    │   └── layout.py          # Shell principal (sidebar + contenido)
    │
    └── views/
        ├── login.py           # Pantalla de login
        ├── dashboard.py       # Dashboard con estadísticas
        ├── socios.py          # Gestión de socios
        ├── personal.py        # Gestión del personal
        ├── rutinas.py         # Rutinas de entrenamiento
        ├── nutricion.py       # Planes nutricionales
        └── usuarios.py        # Gestión de usuarios del sistema (admin)
```

---

## 🏗️ Preparado para backend

Cada método de datos en `app/state.py` está marcado con un comentario `TODO` indicando
el endpoint REST correspondiente:

```python
def get_socios(self) -> list[dict]:
    """TODO: GET /api/socios"""
    # Reemplazar con: return http_client.get("/api/socios")

def login(self, username, password):
    """TODO: POST /api/auth/login"""
    # Reemplazar con: return http_client.post("/api/auth/login", {...})
```

Para conectar el backend, solo hay que:
1. Crear un cliente HTTP (httpx, requests, etc.) en `app/services/api_client.py`
2. Reemplazar los métodos mock en `state.py` con las llamadas reales
3. El resto del sistema no necesita cambios

---

## 🎨 Sistema de diseño

- **Paleta**: Dark theme con naranja eléctrico (`#FF5722`) como acento
- **Tipografía**: Bebas Neue (títulos) + DM Sans (cuerpo)
- **Componentes**: Todos en `app/components/ui.py` — reutilizables en cualquier vista

---

## 🔒 Sistema de roles

| Rol       | Dashboard | Socios | Personal | Rutinas | Nutrición | Usuarios |
|-----------|:---------:|:------:|:--------:|:-------:|:---------:|:--------:|
| admin     | ✅        | ✅     | ✅       | ✅      | ✅        | ✅       |
| trainer   | ✅        | ✅     | ❌       | ✅      | ❌        | ❌       |
| nutri     | ✅        | ✅     | ❌       | ❌      | ✅        | ❌       |
| staff     | ✅        | ✅     | ❌       | ❌      | ❌        | ❌       |

Los guards de rol están implementados en `app/router.py`.
# gymapp
