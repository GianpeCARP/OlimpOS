# OlimpOS — Backend (FastAPI)

**Un solo backend para las dos apps.** No hay un backend para la PWA y otro
para Flet: hay una sola API y una sola base de datos, y los dos frontends le
pegan por HTTP. Es la norma explícita del profe (`Ingreso y creación de
usuarios.docx`): *"ambas deben conectarse a la misma API y la misma base de
datos"*.

```
                        ┌──→ PWA React      (Proyecto/src/frontend)      navegador
Neon ←── backend/ ←─────┤
  (Postgres)   FastAPI  └──→ App Flet       (Proyeto-Python/Proyecto)    escritorio
```

Toda regla de negocio vive acá. Los frontends esconden lo que un rol no debe
ver (UX); el backend **rechaza** lo que un rol no puede hacer (seguridad).
Nunca solo lo primero.

---

## Puesta en marcha

Desde `D:\OlimpOs\backend`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1     # si PowerShell se queja:
                                 # Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
python -m pip install --upgrade pip
pip install -r requirements.txt

Copy-Item .env.example .env      # y completar DATABASE_URL + JWT_SECRET_KEY

uvicorn main:app --reload
```

API en `http://127.0.0.1:8000`, documentación interactiva en `/docs`.

> El tier gratuito de Neon duerme la base tras un rato sin uso. La primera
> consulta después de una pausa tarda unos segundos mientras se despierta.
> Es normal, no es un error del código.

---

## El esquema de la base

**`Proyecto/db/schema.sql` es la fuente de verdad**, no los modelos de
SQLAlchemy. Son 35 tablas normalizadas hasta 3FN, y el DDL es parte de la
entrega académica (ver `olimpos_schema_v5.dbml` y `Normalización.pdf`).

`models.py` mapea ese esquema; no lo define. `create_all()` se llama en el
lifespan igual que en el proyecto del profe, pero acá funciona como red de
seguridad: sobre una base ya cargada con `schema.sql` no hace nada. El
razonamiento largo está en el docstring de `database.py`.

Para cargar la base por primera vez, en el SQL Editor de Neon:
`schema.sql` primero, `seed.sql` después.

---

## El rol no es una columna

En el esquema, `Usuario` guarda **solo** autenticación (username,
password_hash, intentos_fallidos, bloqueado). No tiene columna `rol`.

El rol se **deriva** de en cuál tabla hija existe fila para esa persona:
`Dueno`, `Entrenador`, `Nutricionista`, `Recepcionista`, `Profesor`, `Socio`.
El login lo resuelve una sola vez y lo mete en el JWT, así el resto de los
endpoints no tienen que recalcularlo en cada request.

El contrato de la API queda idéntico al del proyecto del profe (que sí tiene
la columna); lo que cambia es de dónde sale el dato.

---

## El flujo de contraseña obligatoria

Copiado del proyecto de referencia, es el único camino de alta de credenciales
del sistema — se usa igual para el dueño inicial, para cada usuario nuevo y
para cada reseteo hecho por un admin:

1. La cuenta se crea con `debe_cambiar_password = true`.
2. En `POST /login`, si esa bandera está en true el backend **no emite token**.
   Devuelve solo `{"debe_cambiar_password": true}`.
3. El frontend manda a la pantalla de cambio obligatorio.
4. `POST /cambiar-password` es **público** (el usuario todavía no tiene token)
   pero revalida la contraseña actual antes de aplicar el cambio.
5. Al terminar, vuelve al login. **Hay que ingresar de nuevo**, ahora sí con
   token.

No existe registro público: no hay pantalla ni endpoint de auto-registro. Las
altas las hace siempre el personal, y el sistema genera una contraseña
temporal.

---

## Estructura

```
backend/
├── .env.example        plantilla de configuración (el .env real no se sube)
├── requirements.txt
├── database.py         engine, SessionLocal, get_db
├── models.py           modelos SQLAlchemy que mapean schema.sql   [pendiente]
├── schemas.py          moldes Pydantic de entrada/salida          [pendiente]
├── auth.py             hashing bcrypt + firma de JWT              [pendiente]
├── security.py         obtener_usuario_actual, requiere_permiso   [pendiente]
├── seeder.py           crea el Dueño inicial desde el .env        [pendiente]
├── main.py             app, CORS, lifespan, include_router        [pendiente]
└── routers/            un archivo por tema
```

---

## Nota sobre PERAZZO

`Proyeto-Python/PERAZZO/` es el proyecto de referencia del profesor. Es
**solo lectura**: se consulta y se copian ideas, pero no se trabaja ahí ni se
importa nada desde ahí. Su modelo de dominio es más chico y usa el DNI como
clave primaria; el nuestro no.
