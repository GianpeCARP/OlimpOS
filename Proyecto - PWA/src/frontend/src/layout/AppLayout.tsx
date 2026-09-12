import { Outlet } from 'react-router';
import { Sidebar } from '../components/ui/Sidebar';
import { useUiStore } from '../store/uiStore';

// Equivalente de build_main_layout (layout.md): sidebar fija + área de
// contenido dinámica. El Topbar NO va acá — cada vista arma el suyo, tal
// como describe layout.md (content ya incluye su propio topbar).
// Snackbar/ConfirmDialog NO viven acá: LoginView no pasa por este layout,
// así que quedan montados en App.tsx para estar disponibles en toda la app.
//
// h-screen + overflow-hidden en el contenedor, y NO min-h-screen: con
// min-h-screen el div crece con el contenido, así que <main> nunca tenía una
// altura contra la cual desbordar y su `overflow-y-auto` no llegaba a
// activarse nunca. El que scrolleaba era el documento entero, y la sidebar
// —que no es fixed ni sticky en escritorio— se iba con él: bastaba bajar un
// poco en el Dashboard para perder de vista el logo y los primeros ítems de
// navegación. Fijando la altura del contenedor al viewport, el scroll queda
// adentro de <main> y la sidebar se queda quieta.
//
// EN MOBILE la sidebar es un cajón superpuesto (ver Sidebar.tsx) y este
// layout aporta el velo: oscurece el contenido y, sobre todo, da un lugar
// donde tocar para cerrar. Sin él la única forma de cerrar el menú sería
// elegir una sección, y quien lo abrió por error quedaría atrapado.
export function AppLayout() {
  const menuAbierto = useUiStore((s) => s.menuAbierto);
  const cerrarMenu = useUiStore((s) => s.cerrarMenu);

  return (
    // h-full y no h-screen: `h-screen` es `100vh`, que en Safari de iOS
    // incluye la barra de direcciones y deja el final del contenido tapado
    // por ella. La altura real la fija index.css con `100dvh` sobre
    // html/body/#root, y acá simplemente se hereda.
    <div className="flex h-full overflow-hidden bg-surface-base">
      <Sidebar />

      {/* Sólo existe en mobile y sólo con el menú abierto. `md:hidden`
          además de la condición: si la ventana se agranda con el menú
          abierto, el velo no debe quedar tapando la pantalla. */}
      {menuAbierto && (
        <button
          type="button"
          aria-label="Cerrar menú"
          onClick={cerrarMenu}
          className="fixed inset-0 z-30 bg-black/60 md:hidden"
        />
      )}

      {/* min-w-0: sin esto un hijo ancho (una tabla, un texto largo) le
          impone su ancho al flex item y el contenido desborda la pantalla
          en lugar de scrollear dentro de su propio contenedor. */}
      {/* overscroll-contain: cuando este scroll llega al tope, el gesto NO
          sigue de largo hacia el documento. Es la segunda mitad del arreglo
          del pull-to-refresh — la primera está en index.css sobre html/body.
          Van las dos porque el gesto puede nacer acá adentro o afuera. */}
      <main className="min-w-0 flex-1 overflow-y-auto overscroll-contain">
        <Outlet />
      </main>
    </div>
  );
}
