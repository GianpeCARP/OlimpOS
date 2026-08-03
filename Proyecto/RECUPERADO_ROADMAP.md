# OlimpOS — Roadmap de specs

Cada spec sale de un "Área" del DFD Nivel 1. No son una decisión de diseño:
son una traducción directa de los diagramas que ya hiciste.

**Ruta de archivos:** `openspec/specs/<nombre>.spec.md`

---

## Orden de implementación

El orden NO es arbitrario: cada spec necesita que existan las tablas y la
lógica de las anteriores. Seguirlo evita reescribir.

| # | Spec | DFD | Subprocesos a cubrir | Tablas |
|---|---|---|---|---|
| 0 | `sedes` | — (v4) | alta de sede, alta de empleados | Sede, Persona, Empleado, Entrenador, Nutricionista, Recepcionista, Dueno |
| 1 | `auth` | 1.1 | 1.1.1, 1.1.2, 1.1.3 | Persona, Usuario, Telefono, Socio, Baja, Auditoria |
| 2 | `perfil-socio` | 1.2 | 1.2.1, 1.2.2, 1.2.3, 1.2.4 | Persona, Telefono, Socio, Socio_Patologia, Patologia |
| 3 | `cuotas` | 2.1 | 2.1.1, 2.1.2, 2.1.3, 2.1.4 | Tipo_Membresia, Membresia, Pago |
| 4 | `promociones` | 2.2 | 2.2.1, 2.2.2, 2.2.3, 2.2.4 | Promocion, Membresia |
| 5 | `deudas` | 2.3 | 2.3.1, 2.3.2, + job automático | Deuda, Membresia, Pago |
| 6 | `rutinas` | 3.1 | 3.1.1 a 3.1.5 | Ejercicio, Rutina, Rutina_Ejercicio, Asignacion_Rutina |
| 7 | `peso-progreso` | 3.2 | 3.2.1, 3.2.2, 3.2.3 | Registro_Salud, Foto_Progreso |
| 8 | `dietas` | 4.1 | 4.1.1, 4.1.2, 4.1.3, 4.1.4 | Dieta, Comida |
| 9 | `dietas-asignadas` | 4.2 | 4.2.1, 4.2.2 | Asignacion_Dieta |
| 10 | `turnos` | 5.1 | 5.1.1, 5.1.2, 5.1.3 | Turno, Reserva |
| 11 | `asistencia` | 5.2 | 5.2.1, 5.2.2, 5.2.3 | Reserva, Asistencia |
| 12 | `panel-dueno` | 6.1–6.4 | 6.1.1–6.4.2 (solo lectura) | consultas sobre todas |
| 13 | `notificaciones` | — (v4) | avisos de vencimiento, deuda, cumpleaños | Notificacion |

**Total: 14 specs** (0 a 13).

---

## Cómo saber si una spec está completa

No es a ojo. La columna "Subprocesos a cubrir" es la checklist.

Ejemplo con `rutinas`: el DFD Nivel 2 define 3.1.1 (entrenador crea), 3.1.2
(entrenador modifica), 3.1.3 (socio consulta), 3.1.4 (entrenador consulta),
3.1.5 (entrenador elimina). Si la spec tiene cinco casos de uso numerados
con esos IDs, está completa. Si tiene cuatro, te falta uno y sabés
exactamente cuál.

**Regla:** cada caso de uso de la spec lleva entre paréntesis el número del
subproceso del DFD que implementa. Si algún número del DFD no aparece en
ninguna spec, hay un hueco.

---

## Cómo saber si una spec está BIEN

Tres preguntas, en este orden:

1. **¿Declara sus tablas?** Si no las lista, Claude Code va a leer el
   esquema entero y gastar contexto de más.
2. **¿Tiene errores esperados?** Una spec que solo describe el camino feliz
   produce código que se rompe con el primer dato mal cargado.
3. **¿La Definition of Done se verifica corriendo la app?** Si un ítem se
   puede "verificar" leyendo el código, no sirve. Tiene que ser algo que
   pasa o falla al ejecutarlo.

---

## Ciclo de trabajo por spec

```
1. Escribir la spec           (podés pedírmela a mí, en el chat)
2. Abrir terminal:  claude
3. "Leé openspec/specs/X.spec.md y las tablas <lista> de db/schema.sql.
    Implementá la spec. Mostrame el plan antes de escribir código."
4. Revisar el plan, corregir si hace falta, aprobar
5. Correr la app y recorrer la Definition of Done ítem por ítem
6. Marcar Estado: completo
7. Si aprendiste algo que Claude Code debería recordar siempre,
   agregarlo a CLAUDE.md (una línea, no un párrafo)
8. Siguiente spec
```

**No saltear el paso 5.** Una spec "implementada pero no verificada" es una
spec no hecha, y el error se arrastra a todas las que dependen de ella.

---

## Qué NO hacer

- **Escribir las 14 specs antes de programar nada.** Vas a descubrir en la
  spec 3 que la 1 estaba mal planteada, y para entonces escribiste catorce.
  Escribí una, implementala, y recién ahí escribí la siguiente.
- **Pasarle el esquema completo a Claude Code.** Son 33 tablas. Ninguna
  spec necesita más de 8.
- **Cambiar el orden.** `cuotas` antes que `auth` significa pagos de socios
  que no existen todavía.
