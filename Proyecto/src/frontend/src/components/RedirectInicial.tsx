import { Navigate } from 'react-router';
import { useAuthStore } from '../store/authStore';
import { Routes, rutaInicialPara } from '../config';

/**
 * A dónde mandar a alguien que entró a "/" o a una URL inexistente.
 *
 * Antes las dos cosas apuntaban fijo a `/dashboard`, pero eso deja de
 * funcionar con permisos por rol: un Entrenador no ve el Dashboard, así que
 * ese redirect lo mandaba a una ruta que ProtectedRoute rebota — un ciclo.
 * Acá se resuelve contra la matriz de permisos.
 */
export function RedirectInicial() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const roles = useAuthStore((s) => s.roles);

  if (!isAuthenticated) {
    return <Navigate to={`/${Routes.LOGIN}`} replace />;
  }
  return <Navigate to={`/${rutaInicialPara(roles)}`} replace />;
}
