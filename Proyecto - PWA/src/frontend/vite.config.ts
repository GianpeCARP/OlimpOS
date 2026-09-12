import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // El backend real. Solo lo usa el proxy de desarrollo de acá abajo: el
  // código de la app NUNCA habla con esta URL directamente.
  const destinoApi = loadEnv(mode, process.cwd(), '').API_PROXY_DESTINO
    ?? 'http://127.0.0.1:8000'

  return {
  // =======================================================================
  // PROXY DE DESARROLLO — /api  ->  el backend FastAPI
  // =======================================================================
  //
  // POR QUÉ EXISTE (y por qué no alcanza con apuntar fetch al backend):
  //
  // La sesión viaja en una cookie. Las cookies pertenecen a un HOST, y se
  // rigen por reglas de "mismo sitio" que no entienden de puertos:
  //
  //   - Página en localhost:5173, API en 127.0.0.1:8000 -> son hosts
  //     distintos. La cookie queda guardada bajo 127.0.0.1 y la página, que
  //     está en localhost, no puede leerla. document.cookie devuelve vacío y
  //     el token CSRF se vuelve inalcanzable.
  //
  //   - Además son sitios distintos, así que SameSite=lax le prohíbe al
  //     navegador mandar la cookie en los fetch. La sesión no llega nunca al
  //     backend y todo responde 401.
  //
  // Con el proxy, el navegador solo ve http://localhost:5173/api/... — mismo
  // origen que la app. La cookie es de localhost, document.cookie la lee, y
  // SameSite queda satisfecho. De paso desaparece CORS por completo, porque
  // ya no hay pedidos cross-origin.
  //
  // Y esto NO es una muleta de desarrollo: en producción la PWA y la API van
  // a estar detrás del mismo dominio (o del mismo reverse proxy), que es
  // exactamente lo que esto simula. El proxy hace que desarrollo se parezca a
  // producción en vez de diferir de ella.
  //
  // La app Flet no pasa por acá: es de escritorio, le pega directo al backend
  // y se autentica con Bearer, que no depende de cookies ni de orígenes.
  server: {
    proxy: {
      '/api': {
        target: destinoApi,
        changeOrigin: false,   // conserva el Host, así la cookie queda en localhost
        // El backend expone /login, no /api/login: el prefijo es solo para
        // que el proxy sepa qué derivar, y se saca antes de reenviar.
        rewrite: (ruta) => ruta.replace(/^\/api/, ''),
      },
    },
  },

  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      // devOptions APAGADO a proposito.
      //
      // Con `enabled: true` el plugin sirve el manifiesto y registra un
      // service worker tambien en desarrollo. Se probo y se volvio atras por
      // dos razones:
      //
      // 1. NO SIRVE PARA NADA sobre HTTP. Chrome y Safari exigen contexto
      //    seguro (HTTPS o localhost) para ofrecer "Instalar app", asi que
      //    abriendo la PWA por la IP de la red —http://192.168.x.x:5173— el
      //    manifiesto se sirve pero la opcion no aparece igual.
      //
      // 2. EL SERVICE WORKER CACHEA, y en desarrollo eso es un problema: un
      //    arreglo de CSS o de JS puede no verse en el telefono porque el SW
      //    devuelve la version vieja, y se termina depurando un bug que ya
      //    estaba resuelto.
      //
      // Para probar la instalacion de verdad, sin exponer nada a internet:
      // Chrome trata `localhost` como contexto seguro aunque sea HTTP, asi
      // que con el celular por USB y port forwarding en chrome://inspect
      // (5173 -> localhost:5173) se abre como http://localhost:5173 y
      // funciona todo. En ese caso, volver a poner `enabled: true` aca.
      //
      // En produccion no hace falta ninguna de las dos cosas: `vite build`
      // genera el manifiesto y el SW siempre.

      manifest: {
        name: 'OlimpOS',
        short_name: 'OlimpOS',
        // Kinetic Carbon, no los colores por defecto de la plantilla.
        //
        // Estaban en violeta (#aa3bff) y blanco, que no existen en la paleta.
        // No es cosmetico: `background_color` es lo que pinta la pantalla de
        // arranque cuando se abre la app instalada, asi que la app dark-only
        // arrancaba con un flash BLANCO antes de dibujar nada. Y `theme_color`
        // tine la barra de estado del celular, que quedaba violeta sobre una
        // app verde y gris.
        //
        // Los dos salen de src/index.css (bloque @theme). Si cambia la paleta,
        // cambian aca — es la misma regla que ata index.css con config.py de
        // Flet: el mismo color vive en varios archivos y hay que moverlos
        // juntos.
        theme_color: '#C6F135',
        background_color: '#15171C',
        display: 'standalone',
        // CUATRO archivos y no dos, y ahi esta el motivo de que el logo se
        // viera chico: antes el MISMO png servia para `any` y para
        // `maskable`.
        //
        // Un icono `maskable` lo recorta el sistema con la forma que quiera
        // (circulo, cuadrado redondeado, gota), asi que su contenido tiene
        // que caber en un circulo del 80% del lado. Para un logo cuadrado eso
        // es 80/raiz(2) = 56% del ancho. Un archivo que cumple esa regla se ve
        // BIEN recortado y RIDICULAMENTE chico cuando el sistema lo usa como
        // icono normal, que es lo que estaba pasando.
        //
        // Separados, cada uno hace lo suyo: los `any` llenan el cuadro al 92%
        // y son transparentes; los `maskable` van al 58% sobre el fondo de la
        // app. Se generan desde el logo original con el script
        // scratchpad/generar_iconos.ps1.
        icons: [
          {
            src: 'icons/icon-192.png',
            sizes: '192x192',
            type: 'image/png',
            purpose: 'any',
          },
          {
            src: 'icons/icon-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any',
          },
          {
            src: 'icons/maskable-192.png',
            sizes: '192x192',
            type: 'image/png',
            purpose: 'maskable',
          },
          {
            src: 'icons/maskable-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
        ],
      },
    }),
  ],
  }
})
