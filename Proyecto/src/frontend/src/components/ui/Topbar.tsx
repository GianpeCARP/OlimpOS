import type { ReactNode } from 'react';
import { TOPBAR_HEIGHT } from '../../config';

// Equivalente de build_topbar (ui.md). No vive en AppLayout: según
// layout.md cada vista arma la suya como parte de su propio contenido.
interface TopbarProps {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}

export function Topbar({ title, subtitle, actions }: TopbarProps) {
  return (
    <header
      style={{ height: TOPBAR_HEIGHT }}
      className="flex items-center justify-between border-b border-border-idle px-8"
    >
      <div>
        <h1 className="font-heading text-2xl font-bold text-text-main">{title}</h1>
        {subtitle && (
          <p className="font-body text-sm text-text-secondary">{subtitle}</p>
        )}
      </div>
      {actions && <div className="flex items-center gap-3">{actions}</div>}
    </header>
  );
}
