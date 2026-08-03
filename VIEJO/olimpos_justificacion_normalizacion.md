# OlimpOS — Justificación de normalización

Documento de respaldo del esquema `olimpos_schema_v3.dbml`.
Criterio aplicado: **1FN, 2FN y 3FN** según el apunte de la materia.

> *"Cada columna debe depender de la clave (1FN), de toda la clave (2FN) y nada más que de la clave (3FN)."*

---

## 1. Primera Forma Normal (1FN)

**Requisito:** todos los atributos atómicos, sin grupos repetitivos, con clave primaria definida.

| Problema detectado en el modelo original | Solución aplicada |
|---|---|
| `Planilla_Salud.Patologia varchar(250)` — se guardaba `"diabetes, hipertensión, hernia"` en una celda | Tablas `Patologia` (catálogo) + `Socio_Patologia` (relación) |
| `Nombre varchar(100)` con nombre y apellido juntos | `Persona.nombre` + `Persona.apellido` separados |
| `Direccion varchar(150)` sin descomponer | `calle`, `numero_calle`, `localidad` |
| Un socio con varios teléfonos no tenía dónde guardarlos | Tabla `Telefono` (1:N con `Persona`) |
| `Rutina` sin forma de listar ejercicios | Tabla `Rutina_Ejercicio` (una fila por ejercicio) |
| `Dieta` sin forma de listar comidas | Tabla `Comida` (una fila por comida) |

**Nota sobre teléfonos:** es exactamente el Ejercicio 1 y el Ejercicio 8 del apunte. La solución es la misma que propone el material: tabla independiente con una fila por número.

**Nota sobre `email`:** se dejó como campo único en `Persona` porque la regla de negocio define un solo email por persona (es la identidad de login). Si se admitieran varios, habría que aplicar el mismo tratamiento que a los teléfonos.

Todas las tablas tienen clave primaria definida (subrogada `int increment` o compuesta explícita).

---

## 2. Segunda Forma Normal (2FN)

**Requisito:** estar en 1FN + todo atributo no clave debe depender de la clave **completa**.

Según el apunte, *"si una tabla ya está en 1FN y su clave primaria es simple, entonces automáticamente está en 2FN"*. En el esquema, **31 de las 33 tablas usan PK simple subrogada**, por lo que cumplen 2FN de forma automática.

Solo dos tablas tienen clave compuesta, y ambas se verificaron:

### `Usuario_Rol` — PK (id_usuario, id_rol)
| Atributo | ¿De qué depende? | ¿Cumple? |
|---|---|---|
| `fecha_asignacion` | De ESE usuario recibiendo ESE rol | Sí — depende de la clave completa |

No hay dependencias parciales: el nombre del rol vive en `Rol`, el nombre del usuario vive en `Persona`.

### `Socio_Patologia` — PK (id_socio, id_patologia)
| Atributo | ¿De qué depende? | ¿Cumple? |
|---|---|---|
| `fecha_diagnostico` | De ESE socio con ESA patología | Sí |
| `observaciones` | De la combinación específica | Sí |

El nombre de la patología **no está acá** (estaría dependiendo solo de `id_patologia` → dependencia parcial). Vive en `Patologia`.

---

## 3. Tercera Forma Normal (3FN)

**Requisito:** estar en 2FN + sin dependencias transitivas (ningún atributo no clave depende de otro atributo no clave).

### Dependencias transitivas eliminadas

| Dependencia transitiva | Dónde estaba | Descomposición |
|---|---|---|
| `id_membresia → Tipo → Precio` | `Membresia` | `Tipo_Membresia (id, nombre, precio_actual)` + FK en `Membresia` |
| `id_rutina → id_ejercicio → grupo_muscular` | `Rutina.Grupo_muscular` | `Ejercicio (id, nombre, grupo_muscular)` |
| `id_pago → metodo_pago → (datos del método)` | `Membresia.Metodo_pago` | `Metodo_Pago (id, nombre)` + FK en `Pago` |
| `id_entrenador → DNI, Nombre, Email, Dirección` (repetidos en 4 tablas) | Recepcionista / Entrenador / Nutricionista / Cliente | Supertipo `Persona` + subtipos con atributos propios |

Este último es el caso más importante. En el modelo original, si un entrenador cambiaba de dirección y además era nutricionista, había que actualizar dos filas en dos tablas distintas — la **anomalía de modificación** descrita en la página 2 del apunte.

### Denormalizaciones deliberadas (y por qué no violan 3FN)

Hay dos campos que a primera vista parecen dependencias transitivas pero no lo son:

**`Membresia.precio_pactado`** — existiendo `Tipo_Membresia.precio_actual`, parecería redundante. No lo es: son **dos hechos distintos**. `precio_actual` es cuánto vale el plan hoy; `precio_pactado` es cuánto pagó ESE socio cuando compró. Si mañana la cuota sube de $15.000 a $18.000, las membresías ya vendidas deben conservar su precio. No hay dependencia funcional `Tipo → precio_pactado`.

**`Deuda.monto`** — mismo razonamiento. El monto adeudado se congela al generarse la deuda.

---

## 4. Decisiones que NO son de normalización

Estas decisiones son de **modelado de requerimientos**, no de formas normales. Se documentan aparte para evitar confusiones.

### Historial vs. sobreescritura

Se descartó el diseño 1:1 con borrado de la fila anterior (`Membresia`, `Planilla_Salud`, `Plan_Nutricional`) por producir **anomalía de borrado**: al eliminar el registro anterior se pierde información que el sistema necesita conservar.

| Entidad | Consecuencia de borrar | Diseño adoptado |
|---|---|---|
| Peso / medidas | Se pierde la progresión física del socio, que es el producto principal del gimnasio | `Registro_Salud` 1:N con `UNIQUE (id_socio, fecha)` |
| Membresía | Se pierde el historial de cuotas y su vínculo con los pagos | `Membresia` 1:N con `UNIQUE (id_socio, fecha_inicio)` |
| Dieta / Rutina | Se pierde qué le indicó el profesional y cuándo | `Asignacion_*` con `fecha_inicio` / `fecha_fin` / `estado` |

**El requisito de "un solo valor vigente a la vez" se cumple igual**, pero mediante restricciones y consultas en lugar de borrado:

```sql
-- Peso actual del socio
SELECT peso, fecha FROM Registro_Salud
WHERE id_socio = ? ORDER BY fecha DESC LIMIT 1;

-- Membresía vigente
SELECT * FROM Membresia
WHERE id_socio = ? AND estado = 'ACTIVA'
  AND CURRENT_DATE BETWEEN fecha_inicio AND fecha_vencimiento;

-- Rutina activa
SELECT * FROM Asignacion_Rutina
WHERE id_socio = ? AND estado = 'ACTIVA';
```

### Borrado lógico

Ninguna entidad con valor histórico se borra físicamente:

- `Pago` → `estado = 'CANCELADO'`
- `Socio` → registro en `Baja` + `activo = false`
- `Rutina`, `Dieta`, `Promocion` → `activo = false`

Motivo: el DFD Nivel 2 define procesos de consulta histórica (6.1 Área_Pagos, 6.3.2 Consulta bajas, 6.4.2 Consulta cancelados) que quedarían sin datos. En el caso de los pagos hay además una razón contable.

---

## 5. Cobertura de los DFD

| Proceso DFD | Tablas que lo soportan |
|---|---|
| 1.1 Área_Accesos | `Persona`, `Usuario`, `Rol`, `Usuario_Rol`, `Baja`, `Auditoria` |
| 1.2 Área_Dato | `Persona`, `Telefono`, `Socio`, `Auditoria` |
| 2.1 Área_Cuota | `Membresia`, `Tipo_Membresia`, `Pago`, `Metodo_Pago` |
| 2.2 Área_Promoción | `Promocion` |
| 2.3 Área_Deuda | `Deuda` |
| 3.1 Área_Rutina | `Rutina`, `Ejercicio`, `Rutina_Ejercicio`, `Asignacion_Rutina` |
| 3.2 Área_Peso | `Registro_Salud` |
| 4.1 Área_Dietas | `Dieta`, `Comida` |
| 4.2 Área_DietasAsignadas | `Asignacion_Dieta` |
| 5.1 Área_Turnos | `Turno` |
| 5.2 Área_Asistencia | `Reserva`, `Asistencia` |
| 6.1 Área_Pagos | `Pago`, `Deuda`, `Promocion` |
| 6.2 Área_R/P/D | `Rutina`, `Registro_Salud`, `Dieta` |
| 6.3 Área_Usuario | `Persona`, `Socio`, `Baja` |
| 6.4 Área_Turnos | `Turno`, `Reserva`, `Asistencia` |

---

## 6. Pendiente

- **DFD Nivel 3**: no bloquea el modelo de datos. Los niveles 0–2 alcanzan para definir entidades y relaciones; el nivel 3 detalla lógica de procesos, que se traduce en código de la aplicación, no en tablas nuevas.
- **Job de generación de deudas**: definido en las notas de la tabla `Deuda`. Requiere una tarea programada diaria.
- **Definir si los turnos incorporarán clases con horario fijo**: hoy el modelo es de acceso libre 24 hs (un `Turno` = un día). Si se agregan clases, se documenta el cambio en las notas de la tabla.
