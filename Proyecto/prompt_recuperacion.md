Pará la lista de tareas de Vite/Tailwind/PWA por ahora. Antes hay que arreglar
un problema de ubicación y restaurar archivos.

PASO 1 — Mover el scaffold a donde corresponde:
Los archivos que create-vite generó en la raíz (public/, src/App.tsx,
src/index.css, src/main.tsx, src/assets/, index.html, package.json,
tsconfig*.json, vite.config.ts, .oxlintrc.json, README.md) tienen que
moverse TODOS adentro de src/frontend/, que todavía no existe. Creá esa
carpeta y movelos ahí dentro, manteniendo su estructura relativa intacta
(por ejemplo src/App.tsx → src/frontend/src/App.tsx).

No borres nada más de la raíz al hacer esto. No uses --overwrite ni ninguna
flag destructiva en este paso.

PASO 2 — Confirmame el resultado antes de seguir:
Mostrame el árbol de la raíz del proyecto después de mover, para que yo
verifique que quedó así:

mi-proyecto/
├── CLAUDE.md          (yo lo recreo aparte)
├── .claude/
├── .mcp.json
├── .gitignore
├── docs/
├── db/
├── openspec/specs/
└── src/
    └── frontend/       <- acá adentro todo lo de Vite

No continúes con Tailwind, PWA ni ninguna otra tarea hasta que yo confirme
que el árbol está bien.

PASO 3 — Después de mi confirmación:
Yo voy a pegar el contenido de vuelta para openspec/specs/auth.spec.md,
ROADMAP.md, db/seed.sql y docs/database.md (los recuperé). Vos vas a crear
esos archivos con ese contenido exacto, sin modificarlos.

Para db/schema.sql yo lo voy a generar con pg_dump y pegarlo también.

Recién cuando todo eso esté de vuelta en su lugar, seguimos con las tareas
de Tailwind, PWA, zustand, etc.
