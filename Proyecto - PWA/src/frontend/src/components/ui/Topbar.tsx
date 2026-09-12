import type { ReactNode } from 'react';
import { Menu } from 'lucide-react';
import { TOPBAR_HEIGHT } from '../../config';
import { useUiStore } from '../../store/uiStore';

// Equivalente de build_topbar (ui.md). No vive en AppLayout: según
// layout.md cada vista arma la suya como parte de su propio contenido.
//
// EL BOTON DE MENU SOLO EXISTE EN MOBILE (`md:hidden`). En pantallas grandes
// la sidebar esta siempre a la vista y un boton para abrirla no significaria
// nada.
//
// Va acá y no flotando sobre el contenido porque el Topbar ya es la franja
// superior de todas las vistas: un boton fijo por encima taparia el titulo
// justo en las pantallas mas angostas, que son las que lo necesitan.
interface TopbarProps {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}

export function Topbar({ title, subtitle, actions }: TopbarProps) {
  const abrirMenu = useUiStore((s) => s.abrirMenu);

  return (
    <header
      style={{ height: TOPBAR_HEIGHT }}
      // px-4 en mobile y px-8 desde md: 32px de padding a cada lado en una
      // pantalla de 380 se comen el 17% del ancho util.
      className="flex items-center justify-between gap-3 border-b border-border-idle px-4 md:px-8"
    >
      <div className="flex min-w-0 items-center gap-3">
        <button
          type="button"
          onClick={abrirMenu}
          aria-label="Abrir menú"
          className="-ml-1 shrink-0 rounded-md p-2 text-text-secondary hover:bg-surface-hover hover:text-text-main md:hidden"
        >
          <Menu size={22} />
        </button>
        <div className="min-w-0">
          {/* truncate: un titulo largo en mobile empujaba las acciones fuera
              de la pantalla en vez de cortarse. */}
          <h1 className="truncate font-heading text-xl font-bold text-text-main md:text-2xl">
            {title}
          </h1>
          {subtitle && (
            <p className="truncate font-body text-xs text-text-secondary md:text-sm">
              {subtitle}
            </p>
          )}
        </div>
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2 md:gap-3">{actions}</div>}
    </header>
  );
}
