# OlimpOS — Documentación definitiva del modelo de datos (v4)

Acompaña a `olimpos_schema_v4.dbml`. **33 tablas.**

---

## Resumen ejecutivo

| Versión | Tablas | Alcance |
|---|---|---|
| Original | 13 | Parcial: faltaban turnos, pagos, deudas, promociones, login |
| v3 | 34 | Cobertura total del DFD |
| **v4** | **33** | Cobertura total del DFD **+ multi-sede, contacto de emergencia, imágenes y notificaciones** |

La v4 agrega cuatro funcionalidades y aun así tiene **una tabla menos** que la v3. No es magia: había redundancia que se podía eliminar sin perder nada.

---

## PARTE 1 — Qué se optimizó y por qué

### Eliminaciones (−4 tablas)

**1. `Rol` + `Usuario_Rol` → eliminadas (−2)**

El rol ahora se **deriva** de en qué tabla de subtipo aparece la persona (`Socio`, `Entrenador`, `Nutricionista`, `Recepcionista`, `Dueno`).

*Motivo real:* había dos fuentes de verdad para el mismo dato. Era posible tener a alguien registrado en `Usuario_Rol` como ENTRENADOR sin fila en `Entrenador` — un estado inválido que la base no podía impedir. Con la derivación, ese error es estructuralmente imposible.

*Costo en velocidad:* la consulta de login pasa de 1 JOIN a 5 LEFT JOIN. Todos sobre índices UNIQUE, es decir búsquedas O(1). En números reales: microsegundos. Nulo.

*Cuándo revertir:* si algún día necesitás permisos granulares (que decidiste dejar fuera), vuelven `Rol` y `Permiso`.

**2. `Metodo_Pago` → convertida a `ENUM metodo_pago` (−1)**

Era una tabla de dos columnas (id, nombre) sin atributos propios y con contenido prácticamente inmutable. Como ENUM ocupa cero tablas y **elimina un JOIN** de la consulta más frecuente del módulo de cobranza.

*Criterio general aplicado:* un catálogo se convierte en ENUM solo si no tiene atributos propios. Por eso `Tipo_Membresia` **no** se convirtió — tiene precio y duración, que cambian.

**3. `Consulta_Rutina_Nutricionista` + `Consulta_Dieta_Entrenador` → `Consulta_Cruzada` (−1)**

Tenían estructura idéntica (quién, qué, cuándo) y propósito idéntico. El consultor apunta ahora a `Empleado` (supertipo), que cubre ambos roles. Requiere un `CHECK` en el SQL de creación para garantizar que cada fila apunte a exactamente una cosa.

### Agregados (+3 tablas)

| Función pedida | Solución | Costo |
|---|---|---|
| Multi-sede | Tabla `Sede` + FK en Empleado, Socio, Turno, Asistencia, Pago, Promocion | +1 tabla |
| Fotos de progreso | Tabla `Foto_Progreso` colgando de `Registro_Salud` | +1 tabla |
| Notificaciones | Tabla `Notificacion` + 2 ENUMs | +1 tabla |
| Foto de perfil | Columna `Persona.url_foto` | **0 tablas** |
| Contacto de emergencia | 3 columnas en `Persona` | **0 tablas** |

**Sobre el contacto de emergencia como columnas:** la regla de negocio es un contacto por persona. Siendo monovaluado, es atómico y cumple 1FN sin necesidad de tabla. Ventaja adicional: viene en el mismo SELECT que la persona, sin JOIN — que es exactamente lo que necesitás en una urgencia. Si algún día se admiten varios, pasa a tabla propia.

**Sobre las imágenes:** en ningún caso se guarda el binario en la base. Se guarda la **ruta** al archivo. Meter imágenes dentro de la tabla infla el tamaño de fila y vuelve lento *cualquier* SELECT sobre esa tabla, aunque no pidas la foto.

### Fusiones que se rechazaron (y por qué)

Optimizar no es minimizar el número por deporte. Estas se evaluaron y se descartaron:

| Fusión posible | Por qué NO |
|---|---|
| `Recepcionista` dentro de `Empleado` | Obligaría a que `Rutina.id_entrenador` apunte a `Empleado`, y la base ya no podría impedir que una rutina quede a cargo de un recepcionista. Se pierde integridad referencial por −1 tabla: mal negocio. |
| `Entrenador` + `Nutricionista` en una tabla `Profesional` | Mismo problema, multiplicado. |
| `Patologia` + `Socio_Patologia` | Violaría 1FN (volvería el campo multivaluado). |
| `Comida` dentro de `Dieta` | Violaría 1FN. |
| `Baja` como columnas en `Socio` | Perdería el historial: un socio puede darse de baja y reinscribirse varias veces. |
| `Reserva` + `Asistencia` | Son hechos distintos: reservar el día vs. entrar físicamente (varias veces por día). |

---

## PARTE 2 — Corrección de 3FN detectada en esta versión

Al incorporar `Sede` apareció una dependencia transitiva nueva:

```
id_empleado → id_sede → id_dueno
```

`Empleado.id_dueno` (que venía de la v3) pasó a ser transitivo, porque el dueño ahora se determina por la sede. **Se eliminó la columna.** El dueño se obtiene con JOIN a `Sede`, y conserva igual el dominio sobre el personal a través de sus sedes.

Es exactamente el caso del Ejercicio 1 de 3FN de tu apunte (`ID_Empleado → ID_Departamento → Nombre_Departamento`).

Se aplicó el mismo criterio preventivo en `Foto_Progreso`: **no** tiene `id_socio` ni `fecha` propios, porque existiría `id_foto → id_registro_salud → id_socio`. Cuelga solo de `Registro_Salud`.

---

## PARTE 3 — Verificación de formas normales

### 1FN — atomicidad
Sin campos multivaluados. Casos resueltos: patologías (tabla), teléfonos (tabla), ejercicios de una rutina (tabla), comidas de una dieta (tabla), fotos de progreso (tabla), nombre/apellido separados, dirección descompuesta.

### 2FN — dependencia de la clave completa
31 de 33 tablas tienen PK simple subrogada → cumplen automáticamente (regla del apunte: con clave simple no existe "parte" de la clave). La única con PK compuesta es `Socio_Patologia` (id_socio, id_patologia), verificada: `fecha_diagnostico` y `observaciones` dependen de ambos. El nombre de la patología no está ahí — estaría dependiendo solo de `id_patologia`.

### 3FN — sin dependencias transitivas
Eliminadas: `Tipo → Precio` (→ `Tipo_Membresia`), `grupo_muscular` en Rutina (→ `Ejercicio`), datos personales repetidos por rol (→ `Persona`), `id_empleado → id_sede → id_dueno` (columna eliminada).

**Excepciones justificadas** (no son violaciones):
- `Membresia.precio_pactado` vs `Tipo_Membresia.precio_actual`: dos hechos distintos (precio histórico pagado vs. precio vigente). No existe la dependencia `Tipo → precio_pactado`.
- `Deuda.monto`: mismo criterio, se congela al generarse.
- `Asistencia.id_sede`: no es transitivo porque `id_reserva` es nullable (ingreso libre sin reserva previa), así que no toda fila puede derivarlo.
- `Notificacion.id_entidad_referida`: referencia sin FK, única concesión del modelo. Una notificación no necesita integridad referencial — si el objeto se borra, el aviso sigue siendo historia válida.

---

## PARTE 4 — Rendimiento

La consigna era "optimizar cantidad de tablas sin perder velocidad". Los índices que lo garantizan:

| Consulta frecuente | Índice que la resuelve |
|---|---|
| Login | UNIQUE en `Usuario.username` + UNIQUE en cada `id_persona` de subtipo |
| Peso actual del socio | `(id_socio, fecha)` en `Registro_Salud` |
| Membresía vigente | `(id_socio, fecha_inicio)` en `Membresia` |
| Job diario de deudas | `(estado, fecha_vencimiento)` en `Membresia` |
| Cupo libre de un día | `(id_turno, estado)` en `Reserva` — cuenta sin leer la tabla |
| Rutina completa ordenada | `(id_rutina, dia, orden)` en `Rutina_Ejercicio` |
| Badge de notificaciones sin leer | `(id_persona, leida)` en `Notificacion` |
| Caja por sede y fecha | `(id_sede, fecha_pago)` en `Pago` |
| Cumpleaños del día | `(fecha_nacimiento)` en `Persona` |

**Principio aplicado:** más tablas normalizadas no significa consultas más lentas si los JOIN caen sobre índices. Lo que sí las hace lentas es un escaneo secuencial sobre una tabla ancha con campos que no se usan — que es justamente lo que se evitó al sacar las imágenes de las filas.

---

## PARTE 5 — Trazabilidad DFD

| Proceso DFD | Tablas | Estado |
|---|---|---|
| 1.1 Área_Accesos | Persona, Usuario, Baja, Auditoria | ✅ |
| 1.2 Área_Dato | Persona, Telefono, Socio | ✅ |
| 2.1 Área_Cuota | Membresia, Tipo_Membresia, Pago | ✅ |
| 2.2 Área_Promoción | Promocion | ✅ |
| 2.3 Área_Deuda | Deuda | ✅ |
| 3.1 Área_Rutina | Rutina, Ejercicio, Rutina_Ejercicio, Asignacion_Rutina | ✅ |
| 3.2 Área_Peso | Registro_Salud, Foto_Progreso | ✅ |
| 4.1 Área_Dietas | Dieta, Comida | ✅ |
| 4.2 Área_DietasAsignadas | Asignacion_Dieta | ✅ |
| 5.1 Área_Turnos | Turno | ✅ |
| 5.2 Área_Asistencia | Reserva, Asistencia | ✅ |
| 6.1–6.4 Área_Consultas | reutiliza todas las anteriores | ✅ |

---

## PARTE 6 — Qué sigue fuera de alcance (por decisión tuya)

Para que quede documentado y no aparezca como sorpresa:

- Contratos / firma digital al inscribirse
- Gestión de caja y arqueo diario
- Recursos humanos (sueldos, licencias, vacaciones) — por eso `Empleado` no tiene columna `salario`
- Permisos granulares por rol — el rol es una etiqueta derivada, no un sistema de permisos

Ninguna de estas ausencias afecta la normalización ni la cobertura de los DFD. Son alcance de producto, no de modelo.

---

## Pendiente técnico

1. El `CHECK` de `Consulta_Cruzada` no se puede expresar en DBML. Al generar el SQL, agregar:
   ```sql
   ALTER TABLE Consulta_Cruzada
   ADD CONSTRAINT chk_una_referencia
   CHECK ( (id_rutina IS NOT NULL) <> (id_dieta IS NOT NULL) );
   ```
2. El job diario de deudas necesita una tarea programada (cron, o `pg_cron` si usás PostgreSQL).
3. Cargar la fila inicial de `Sede` antes de cualquier alta de empleado o socio: es la raíz del modelo.
