import { NavLink, useNavigate } from 'react-router';
import { LogOut } from 'lucide-react';
import { APP_NAME, SIDEBAR_WIDTH, Routes, navItemsPara, puedeVerRuta } from '../../config';
import { useAuthStore } from '../../store/authStore';

// Equivalente de build_sidebar + _nav_item (ui.md). El resaltado del ítem
// activo lo resuelve <NavLink> de react-router en vez de la lista manual
// _todos_los_botones que mutaba Flet a mano.
export function Sidebar() {
  const navigate = useNavigate();
  const persona = useAuthStore((s) => s.persona);
  const roles = useAuthStore((s) => s.roles);
  const logout = useAuthStore((s) => s.logout);

  const handleLogout = () => {
    logout();
    navigate(`/${Routes.LOGIN}`);
  };

  // Dos pasos, y los dos hacen falta:
  //
  // 1. navItemsPara elige QUÉ MENÚ va — el del socio o el de gestión. No
  //    son el mismo menú con distintos permisos, son dos productos: el
  //    socio ve "Mi rutina", el entrenador ve "Rutinas". Ninguna entrada se
  //    comparte.
  // 2. puedeVerRuta filtra DENTRO de ese menú, que es lo que distingue a un
  //    Entrenador de un Dueño.
  //
  // Es la misma función que usan ProtectedRoute y el panel de permisos de
  // /usuarios, para que las tres vistas del permiso no puedan divergir.
  const items = navItemsPara(roles).filter((item) => puedeVerRuta(roles, item.route));

  return (
    <aside
      style={{ width: SIDEBAR_WIDTH }}
      // shrink-0: sin esto es un flex item con `width` pero flex-shrink por
      // defecto, así que en pantallas angostas se comprimía y las etiquetas
      // se apretaban contra los íconos. h-full (no h-screen) porque ahora es
      // el contenedor de AppLayout el que fija la altura al viewport.
      className="flex h-full shrink-0 flex-col justify-between overflow-y-auto border-r border-border-idle bg-surface-hover"
    >
      <div>
        <div className="px-6 py-6 font-heading text-2xl font-extrabold text-text-main">
          {APP_NAME}
        </div>
        <nav className="flex flex-col gap-1 px-3">
          {items.map(({ label, icon: Icon, route }) => (
            <NavLink
              key={route}
              to={`/${route}`}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-md px-3 py-2 font-body text-sm transition-colors ${
                  isActive
                    ? 'bg-primary-volt font-semibold text-surface-base'
                    : 'text-text-secondary hover:bg-surface-card hover:text-text-main'
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>
      </div>

      <div className="border-t border-border-idle px-3 py-4">
        {persona && (
          <div className="px-3 pb-2 font-body text-sm text-text-secondary">
            {persona.nombre} {persona.apellido}
          </div>
        )}
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-3 rounded-md px-3 py-2 font-body text-sm text-text-secondary hover:bg-surface-card hover:text-status-danger"
        >
          <LogOut size={18} />
          Cerrar sesión
        </button>
      </div>
    </aside>
  );
}
