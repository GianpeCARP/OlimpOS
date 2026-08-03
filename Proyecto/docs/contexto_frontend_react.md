# Contexto — OlimpOS Front-end (React PWA)

## Qué es el proyecto
Sistema de gestión completo y profesional para un gimnasio, llamado **OlimpOS**.
Este chat es exclusivamente para **programar el front-end**, en base a lo que
yo vaya pidiendo paso a paso. No inventes pantallas, paneles ni funcionalidad
que no te haya pedido explícitamente.

## Stack definido
- **React + TypeScript + Vite**
- Configurado como **PWA** (instalable, multiplataforma)
- Tailwind para estilos
- React Router para navegación entre paneles

## Reglas de trabajo
- **Esperá mi `design.md`** antes de escribir cualquier pantalla. Ahí defino
  paleta de colores, tipografía y estructura visual (sidebar, layout). No
  definas vos el estilo por tu cuenta.
- Voy a pasarte **los paneles de a uno**, no todos juntos. Armamos el
  proyecto de forma incremental y estructurada: un panel, lo reviso, ajusto,
  y recién ahí pedimos el siguiente.
- El código tiene que quedar **bien comentado y legible**. Soy principiante
  y quiero poder entender y modificar el código yo mismo en el futuro sin
  depender de que me lo expliquen de nuevo. Comentá el *por qué* de las
  decisiones no triviales, no solo el *qué* hace cada línea.
- Los datos por ahora son **mock** (no hay backend conectado todavía). Cada
  pantalla debe consumir sus datos desde una capa de servicios separada
  (`services/`), simulando llamadas async (con delay y posibilidad de
  error), para que el día de mañana conectar la API real sea cambiar el
  contenido de esas funciones y no rehacer componentes.
- Roles del sistema a tener en cuenta cuando arme rutas/paneles: **Socio**,
  **Entrenador**, **Nutricionista**, **Recepcionista**, **Dueño**. La misma
  PWA sirve a todos, con pantallas según rol — no son apps separadas.

## Qué NO hacer en este chat
- No diseñar la paleta de colores ni el layout por tu cuenta — eso ya está
  definido en un `design.md` que te voy a pasar.
- No adelantarte a crear paneles que no pedí.
- No asumir lógica de negocio de base de datos — este chat es solo UI/front,
  la lógica real vive en otro sistema (backend en Python) que no es parte
  de este chat.
