import { Outlet } from 'react-router';
import { Sidebar } from '../components/ui/Sidebar';

// Equivalente de build_main_layout (layout.md): sidebar fija + área de
// contenido dinámica. El Topbar NO va acá — cada vista arma el suyo, tal
// como describe layout.md (content ya incluye su propio topbar).
// Snackbar/ConfirmDialog NO viven acá: LoginView no pasa por este layout,
// así que quedan montados en App.tsx para estar disponibles en toda la app.
// h-screen + overflow-hidden en el contenedor, y NO min-h-screen: con
// min-h-screen el div crece con el contenido, así que <main> nunca tenía una
// altura contra la cual desbordar y su `overflow-y-auto` no llegaba a
// activarse nunca. El que scrolleaba era el documento entero, y la sidebar
// —que no es fixed ni sticky— se iba con él: bastaba bajar un poco en el
// Dashboard para perder de vista el logo y los primeros ítems de navegación.
// Fijando la altura del contenedor al viewport, el scroll queda adentro de
// <main> y la sidebar se queda quieta, que es lo que layout.md describe
// ("sidebar fija + área de contenido dinámica").
export function AppLayout() {
  return (
    <div className="flex h-screen overflow-hidden bg-surface-base">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
