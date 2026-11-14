import { useId, type ReactNode } from 'react';

import { ExpandableCardButton } from './ExpandableCardButton';
import { ExpandableCardPanel } from './ExpandableCardPanel';

export interface ExpandableCardProps {
  /** The always-visible summary; inline content only, because it sits inside a button. */
  summary: ReactNode;
  /** Controlled, so a parent can keep only one card open (accordion). */
  isExpanded: boolean;
  onToggle: () => void;
  showDetailsLabel: string;
  hideDetailsLabel: string;
  panelAccessibleLabel: string;
  children: ReactNode;
}

// A card that opens in place, with its detail directly below. Use the Button and Panel parts
// separately when the detail must sit elsewhere in the layout (M5 puts it below a grid).
export function ExpandableCard({
  summary,
  isExpanded,
  onToggle,
  showDetailsLabel,
  hideDetailsLabel,
  panelAccessibleLabel,
  children,
}: ExpandableCardProps) {
  const panelId = useId();
  return (
    <div className="flex flex-col gap-3">
      <ExpandableCardButton
        panelId={panelId}
        isExpanded={isExpanded}
        onToggle={onToggle}
        showDetailsLabel={showDetailsLabel}
        hideDetailsLabel={hideDetailsLabel}
      >
        {summary}
      </ExpandableCardButton>
      <ExpandableCardPanel
        id={panelId}
        isExpanded={isExpanded}
        accessibleLabel={panelAccessibleLabel}
      >
        {children}
      </ExpandableCardPanel>
    </div>
  );
}
