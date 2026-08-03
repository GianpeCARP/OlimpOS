No elijas ninguna de las 3 opciones. El backend se decide después, no ahora
— eso ya estaba definido desde el arranque de este proyecto (ver
contexto_frontend_react.md): "Los datos por ahora son mock. Cada pantalla
debe consumir sus datos desde una capa de servicios separada (services/),
simulando llamadas async (con delay y posibilidad de error), para que el
día de mañana conectar la API real sea cambiar el contenido de esas
funciones y no rehacer componentes."

Dos cosas para que tengas en cuenta y no repitamos este bloqueo:

1. Cuando el backend se implemente, NO va a ser Node/Express. Va a ser
   Python: FastAPI sobre un paquete compartido (olimpos_core) que también
   va a usar una app de escritorio (Flet) para que el sistema funcione
   aunque se corte internet. Esto es una decisión de arquitectura ya
   tomada, no algo a re-abrir. No lo implementes ahora — solo tenelo en
   cuenta para no asumir Node más adelante.

2. Por ahora, seguí así:
   - Creá src/frontend/src/services/authService.ts
   - Ahí van funciones async que simulan las 3 operaciones de
     auth.spec.md (registro, login, baja) con datos hardcodeados,
     delay artificial (ej. 400-600ms) y posibilidad de devolver error
     (ej. DNI/username duplicado, credenciales inválidas), replicando
     los mismos casos de "Errores esperados" que están en auth.spec.md.
   - authStore.ts llama a esas funciones de authService.ts, no datos
     hardcodeados directo en el store.
   - La firma de cada función (parámetros de entrada, forma de la
     respuesta) tiene que ser la que ya usás en types.ts, para que el
     día de mañana cambiar el cuerpo de la función por un fetch real
     no rompa nada del lado de los componentes.

Mostrame el plan de authService.ts antes de escribirlo.
