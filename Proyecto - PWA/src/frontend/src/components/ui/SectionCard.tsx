import type { ReactNode } from 'react';

// Equivalente de section_card (ui.md).
interface SectionCardProps {
  title?: string;
  padding?: string;
  children: ReactNode;
}

export function SectionCard({ title, padding = 'p-5', children }: SectionCardProps) {
  return (
    <section className={`rounded-lg border border-border-idle bg-surface-card ${padding}`}>
      {title && (
        <h2 className="mb-3 font-heading text-lg font-semibold text-text-main">{title}</h2>
      )}
      {children}
    </section>
  );
}
