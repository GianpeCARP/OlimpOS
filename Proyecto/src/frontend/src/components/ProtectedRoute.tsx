import { Navigate, Outlet } from 'react-router';
import { useAuthStore } from '../store/authStore';
import { Routes, puedeVerRuta, rutaInicialPara, type SeccionPrivada } from '../config';

// Guards de router.md portados a wrappers de ruta (URLs reales, no el
// singleton de Flet).
//
// Antes esto tenía un flag `requireAdmin` que sólo cubría /usuarios. Ahora
// cada ruta declara qué sección es, y el permiso sale de la matriz de
// config.ts — la misma que usa el Sidebar para ocultar el link. Así no
// puede pasar que el link esté oculto pero la URL siga abierta.
//
// ⚠️ Esto es UX, no seguridad: cualquiera puede editar el store desde las
// devtools y entrar igual. La barrera real va del lado del backend.
interface ProtectedRouteProps {
  /** Sin sección: sólo exige estar logueado (es el guard de todo el layout). */
  seccion?: SeccionPrivada;
}

export function ProtectedRoute({ seccion }: ProtectedRouteProps) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const roles = useAuthStore((s) => s.roles);

  if (!isAuthenticated) {
    return <Navigate to={`/${Routes.LOGIN}`} replace />;
  }

  // router.md "cancela la navegación silenciosamente" no tiene sentido con
  // URLs reales (dejaría la pantalla en blanco) — acá se redirige a la
  // primera sección que el rol sí pueda ver, que no siempre es el
  // dashboard: un Entrenador no lo tiene habilitado.
  if (seccion && !puedeVerRuta(roles, seccion)) {
    return <Navigate to={`/${rutaInicialPara(roles)}`} replace />;
  }

  return <Outlet />;
}
