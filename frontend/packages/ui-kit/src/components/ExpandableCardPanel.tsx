import type { ReactNode } from 'react';

export interface ExpandableCardPanelProps {
  /** Must equal the panelId given to the matching ExpandableCardButton. */
  id: string;
  isExpanded: boolean;
  /** Names the region for screen readers, for example "Missed sales detail". */
  accessibleLabel: string;
  children: ReactNode;
}

// The detail region an ExpandableCardButton opens; it stays in the DOM (hidden) so aria-controls always resolves.
export function ExpandableCardPanel({
  id,
  isExpanded,
  accessibleLabel,
  children,
}: ExpandableCardPanelProps) {
  return (
    <section
      id={id}
      aria-label={accessibleLabel}
      hidden={!isExpanded}
      className="rounded-card border-2 border-cyan bg-white p-4 text-deep-navy"
    >
      {isExpanded ? children : null}
    </section>
  );
}
