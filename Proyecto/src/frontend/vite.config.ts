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
      manifest: {
        name: 'OlimpOS',
        short_name: 'OlimpOS',
        theme_color: '#aa3bff',
        background_color: '#ffffff',
        display: 'standalone',
        icons: [
          {
            src: 'icons/manifest-icon-192.maskable.png',
            sizes: '192x192',
            type: 'image/png',
            purpose: 'any',
          },
          {
            src: 'icons/manifest-icon-192.maskable.png',
            sizes: '192x192',
            type: 'image/png',
            purpose: 'maskable',
          },
          {
            src: 'icons/manifest-icon-512.maskable.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any',
          },
          {
            src: 'icons/manifest-icon-512.maskable.png',
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
