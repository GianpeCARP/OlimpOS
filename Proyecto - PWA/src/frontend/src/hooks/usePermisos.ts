// Acceso a la matriz de permisos desde los componentes. Es un envoltorio
// fino sobre las funciones de config.ts: lo único que agrega es leer los
// roles de la sesión, para que cada vista no tenga que repetir el
// `useAuthStore((s) => s.roles)`.
//
// ⚠️ Recordatorio: esto decide qué se DIBUJA, no qué se permite. Un usuario
// con devtools puede forzar el store y ver cualquier botón. La validación
// real va en el backend (ver el bloque de PERMISOS en config.ts).

import {
  accesoASeccion,
  esCuentaPropiaRestringida,
  puedeAccion,
  type AccesoValue,
  type AccionesRol,
  type SeccionPrivada,
} from '../config';
import { useAuthStore } from '../store/authStore';

/** True si el rol de la sesión puede ejecutar esa acción puntual. */
export function usePuedeAccion(accion: keyof AccionesRol): boolean {
  const roles = useAuthStore((s) => s.roles);
  return puedeAccion(roles, accion);
}

/** Nivel de acceso de la sesión a una sección: NINGUNO / LECTURA / TOTAL. */
export function useAccesoSeccion(seccion: SeccionPrivada): AccesoValue {
  const roles = useAuthStore((s) => s.roles);
  return accesoASeccion(roles, seccion);
}

/**
 * True si la fila de Usuario con ese id ES la cuenta de quien está
 * logueado y por eso no se puede editar/dar de baja desde el panel de
 * Usuarios — ver esCuentaPropiaRestringida en config.ts.
 */
export function useEsCuentaPropiaRestringida(idUsuarioFila: number): boolean {
  const roles = useAuthStore((s) => s.roles);
  const idUsuarioActor = useAuthStore((s) => s.usuario?.id_usuario);
  return esCuentaPropiaRestringida(roles, idUsuarioFila, idUsuarioActor);
}
