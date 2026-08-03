Necesito implementar permisos granulares por rol de PERSONAL (dueño,
recepcionista, entrenador, nutricionista) — distinto del portal de socio
que ya armamos. Esto va sobre las rutas /admin/* que ya existen.

## La matriz de permisos (derivada del DFD, confirmada, no la cambies)

| Acción                          | Dueño | Recepcionista | Entrenador | Nutricionista |
|----------------------------------|-------|----------------|------------|-----------------|
| Alta/baja de socios               | Sí    | Sí             | No         | No              |
| Alta/baja de personal             | Sí    | No (ni él mismo)| No        | No              |
| Alta/modif/baja de rutinas         | No    | No             | Sí         | No              |
| Alta/modif/baja de dietas          | No    | No             | No         | Sí              |
| Cobrar/consultar pagos             | Sí    | Sí             | No         | No              |
| Crear/modif/eliminar promociones   | Sí    | No             | No         | No              |
| Modificar/eliminar deudas          | Sí    | No             | No         | No              |
| Gestionar turnos (habilitar/cancelar)| Sí  | Sí             | No         | No              |
| Consultas globales (panel dueño)   | Sí    | Parcial (operativo)| No     | No              |

Caso especial importante: el Recepcionista puede hacer casi todo lo
operativo, PERO nunca puede dar de alta ni de baja SU PROPIO registro de
empleado (ni el de nadie más — alta/baja de personal es exclusivo del
Dueño). Esto no es un permiso de sección, es una regla a nivel de fila:
un Recepcionista no puede ejecutar la acción de baja/alta sobre su propio
id_persona, aunque tenga acceso a la pantalla.

## Cómo implementarlo (no es solo esconder botones)

1. Extendé el sistema de permisos que ya existe en config.ts (el que
   describía PERMS en usuarios.md: admin/trainer/nutri/staff) para que
   sea una tabla de PERMISOS POR ACCIÓN, no solo por sección visible.
   Ejemplo de forma:

   const PERMISOS = {
     dueno: { altaBajaSocios: true, altaBajaPersonal: true, gestionRutinas: false, ... },
     recepcionista: { altaBajaSocios: true, altaBajaPersonal: false, ... },
     entrenador: { altaBajaSocios: false, gestionRutinas: true, ... },
     nutricionista: { altaBajaSocios: false, gestionDietas: true, ... },
   }

2. Los botones de acción (crear rutina, eliminar socio, etc.) en cada
   vista tienen que consultar este objeto según el rol del usuario
   logueado, y ocultarse/deshabilitarse si no corresponde — no alcanza
   con que la ruta esté protegida, la ACCIÓN puntual también se valida.

3. Para el caso especial del Recepcionista: en la vista de Personal
   (personal.md), el botón de eliminar/dar de baja tiene que comparar
   el id_persona de la fila contra el id_persona del usuario logueado.
   Si coinciden Y el rol es recepcionista, ese botón puntual se oculta
   o deshabilita, aunque el resto de los botones de esa misma pantalla
   sigan activos.

4. Actualizá la tabla "Permisos por Rol" que ya existe en usuarios.md
   para reflejar esta matriz completa (no solo qué secciones ve cada
   rol, sino qué acciones puede ejecutar dentro de cada una).

## Recordatorio de seguridad (ya lo hablamos, lo repito para que no se pierda)

Esto es UX — organiza qué ve y qué puede clickear cada rol en el frontend.
No es la barrera de seguridad real. Cuando conectemos el backend en
Python, cada una de estas acciones tiene que revalidarse del lado del
servidor con la misma matriz, porque el frontend siempre se puede
manipular. Dejá un comentario en el código señalando esto donde
corresponda, para que quede claro que esto no reemplaza la validación
de backend.

Mostrame el plan antes de tocar código.
