No uses el placeholder SVG. Tengo el logo real de OlimpOS.

Voy a copiar el archivo logoGYM.png a
src/frontend/src/assets/logoGYM.png ahora mismo.

Cuando confirme que está ahí, hacé esto:

1. Instalá pwa-asset-generator como devDependency:
   npm install -D pwa-asset-generator
   (corriendo desde src/frontend, con pwd confirmado antes)

2. Ejecutalo apuntando al logo real para generar automáticamente los PNGs
   en los tamaños que pide el manifest (192x192, 512x512, y la versión
   maskable), guardándolos en public/icons/:

   npx pwa-asset-generator src/assets/logo-source.png public/icons
     --icon-only --favicon --type png --padding "10%"

3. Actualizá la config de VitePWA en vite.config.ts para que el manifest
   apunte a esos íconos generados en public/icons/ en vez del placeholder
   SVG (192x192 como "any", 512x512 como "any", y la versión maskable con
   purpose: "maskable").

4. Seguí con lo que ya tenías planeado: no tocar index.html a mano (el
   plugin inyecta el link al manifest solo), y verificar con npm run build
   que compile y genere dist/manifest.webmanifest + sw.js correctamente.

Mostrame qué archivos generó en public/icons/ antes de dar el paso por
terminado.
