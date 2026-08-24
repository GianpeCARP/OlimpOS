import { NavLink, useNavigate } from 'react-router';
import { LogOut } from 'lucide-react';
import { APP_NAME, SIDEBAR_WIDTH, Routes, navItemsPara, puedeVerRuta } from '../../config';
import { useUiStore } from '../../store/uiStore';
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

  const abierto = useUiStore((s) => s.menuAbierto);
  const cerrarMenu = useUiStore((s) => s.cerrarMenu);

  return (
    <aside
      style={{ width: SIDEBAR_WIDTH }}
      // EN MOBILE ES UN CAJON QUE SE DESLIZA, no una columna del layout.
      //
      // Antes era siempre una columna de 260px con shrink-0. En un celular de
      // ~380px eso dejaba ~120px para el contenido: la sidebar se veía bien y
      // la pantalla real quedaba en el 20% del ancho, ilegible. shrink-0 era
      // correcto para escritorio —sin él las etiquetas se apretaban contra
      // los íconos— pero en mobile el problema no es que se encoja: es que no
      // debería ocupar lugar.
      //
      // `fixed` la saca del flujo (no le quita ancho a nadie) y el translate
      // la esconde a la izquierda hasta que alguien la abre. Desde `md` vuelve
      // a ser lo que era: `md:static` la devuelve al flujo y
      // `md:translate-x-0` cancela el desplazamiento.
      className={[
        'fixed inset-y-0 left-0 z-40 flex h-full shrink-0 flex-col justify-between',
        'overflow-y-auto border-r border-border-idle bg-surface-hover',
        'transition-transform duration-200 ease-out',
        abierto ? 'translate-x-0' : '-translate-x-full',
        'md:static md:translate-x-0',
      ].join(' ')}
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
              // Cierra el cajon al elegir una seccion. En escritorio no hace
              // nada (el menu nunca esta "abierto"); en mobile es lo que evita
              // que el menu quede tapando la pantalla recien abierta.
              onClick={cerrarMenu}
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
