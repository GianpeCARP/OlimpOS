# Spec: auth

> **Origen:** DFD Nivel 1 — Proceso 1.1 Área_Accesos
> **Estado:** pendiente
> **Depende de:** `sedes`

---

## 1. Alcance

Registro, inicio de sesión y baja de socios. Es la primera rebanada vertical
del sistema: al terminarla, un socio debe poder crearse una cuenta, entrar y
darse de baja, contra la base de datos real.

**Fuera de alcance de esta spec:** recuperación de contraseña, edición de
perfil (va en `perfil-socio`), alta de empleados (va en `sedes`).

---

## 2. Tablas que toca

Solo estas. No leer el resto del esquema.

| Tabla | Uso |
|---|---|
| `Sede` | lectura — el socio se asocia a una sede |
| `Persona` | escritura — datos personales |
| `Usuario` | escritura — credenciales |
| `Telefono` | escritura — teléfonos del socio |
| `Socio` | escritura — alta como socio |
| `Baja` | escritura — registro de baja |
| `Auditoria` | escritura — log de LOGIN, ALTA, BAJA |

**Invariantes que no se pueden romper:**
- `Persona.dni` y `Persona.email` son UNIQUE. Validar antes de insertar.
- El rol NO se guarda: se deriva de en qué subtipo aparece la persona.
- Darse de baja NO borra el socio. Inserta fila en `Baja` y pone
  `Socio.activo = false`.
- Nunca guardar la contraseña en texto plano. Solo `password_hash`.

---

## 3. Casos de uso

### 3.1 — Registro de socio  *(DFD 1.1.1)*

**Entrada:** dni, apellido, nombre, email, fecha_nacimiento, teléfono,
sede, username, password.

**Flujo:**
1. Validar que el DNI no exista en `Persona`.
2. Validar que el email no exista en `Persona`.
3. Validar que el username no exista en `Usuario`.
4. Validar formato de email y que la contraseña tenga mínimo 8 caracteres.
5. En **una sola transacción**: INSERT en `Persona` → `Usuario` →
   `Telefono` → `Socio`.
6. INSERT en `Auditoria` con accion = 'ALTA'.
7. Devolver el socio creado (sin el hash).

**Errores esperados:**
| Situación | Respuesta |
|---|---|
| DNI ya registrado | 409 — "Ya existe una persona con ese DNI" |
| Email ya registrado | 409 — "Ese email ya está en uso" |
| Username ocupado | 409 — "Ese nombre de usuario no está disponible" |
| Contraseña corta | 400 — "La contraseña debe tener al menos 8 caracteres" |
| Sede inexistente | 400 |

### 3.2 — Inicio de sesión  *(DFD 1.1.2)*

**Entrada:** username, password.

**Flujo:**
1. Buscar `Usuario` por username.
2. Si no existe o `activo = false` o `bloqueado = true` → rechazar.
3. Comparar el hash. Si no coincide: incrementar `intentos_fallidos`.
   Al llegar a 5, poner `bloqueado = true`.
4. Si coincide: resetear `intentos_fallidos` a 0, actualizar `ultimo_acceso`.
5. Resolver los roles con los 5 LEFT JOIN documentados en el esquema.
6. INSERT en `Auditoria` con accion = 'LOGIN'.
7. Devolver token de sesión + roles.

**Regla de seguridad:** ante usuario inexistente y contraseña incorrecta,
devolver **el mismo mensaje genérico**. No revelar cuál de los dos falló.

### 3.3 — Baja de socio  *(DFD 1.1.3)*

**Entrada:** id_socio, tipo de baja, motivo.

**Flujo:**
1. Verificar que el socio esté activo.
2. INSERT en `Baja` con fecha, tipo y motivo.
3. UPDATE `Socio.activo = false` y `Usuario.activo = false`.
4. **NO** borrar ninguna fila.
5. INSERT en `Auditoria` con accion = 'BAJA'.

**Nota:** un socio dado de baja puede reinscribirse después. Por eso `Baja`
es una tabla con historial y no un booleano.

---

## 4. Definition of Done

La spec está terminada cuando **todos** estos puntos se verifican corriendo
la app contra la base real, no leyendo el código:

- [ ] Un socio nuevo se registra y aparece en las 4 tablas
- [ ] Registrar dos veces el mismo DNI devuelve 409 y no deja datos a medias
- [ ] El login válido devuelve token y los roles correctos
- [ ] El login inválido no dice si falló el usuario o la contraseña
- [ ] A los 5 intentos fallidos la cuenta queda bloqueada
- [ ] La baja deja el socio inactivo pero **la fila sigue existiendo**
- [ ] Hay filas en `Auditoria` para ALTA, LOGIN y BAJA
- [ ] Las contraseñas en la base están hasheadas (verificar con un SELECT)

---

## 5. Cómo pedirle esto a Claude Code

```
Leé openspec/specs/auth.spec.md y las tablas Sede, Persona, Usuario,
Telefono, Socio, Baja y Auditoria de db/schema.sql.

Implementá los tres casos de uso. Antes de escribir código mostrame
el plan y qué archivos vas a crear.

No leas el resto del esquema, no hace falta.
```

Al terminar, recorrer la checklist del punto 4 uno por uno. Recién cuando
todos pasan, marcar **Estado: completo** arriba y pasar a `perfil-socio`.
