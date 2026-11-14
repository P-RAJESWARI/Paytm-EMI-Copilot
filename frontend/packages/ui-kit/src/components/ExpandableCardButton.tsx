import type { ReactNode } from 'react';

import { ChevronDownIcon } from '../icons/ChevronDownIcon';

export interface ExpandableCardButtonProps {
  /** The id of the ExpandableCardPanel this button opens. */
  panelId: string;
  isExpanded: boolean;
  onToggle: () => void;
  /** The card's summary. Use inline content only (span, strong), because it sits inside a button. */
  children: ReactNode;
  /** Translated "See details". */
  showDetailsLabel: string;
  /** Translated "Hide details". */
  hideDetailsLabel: string;
}

// The clickable face of an expandable card: a real button with aria-expanded and aria-controls.
export function ExpandableCardButton({
  panelId,
  isExpanded,
  onToggle,
  children,
  showDetailsLabel,
  hideDetailsLabel,
}: ExpandableCardButtonProps) {
  return (
    <button
      type="button"
      aria-expanded={isExpanded}
      aria-controls={panelId}
      onClick={onToggle}
      className={`flex w-full min-h-touch-target flex-col items-start gap-2 rounded-card border-2 bg-white px-4 py-4 text-left text-deep-navy ${
        isExpanded ? 'border-cyan' : 'border-border'
      }`}
    >
      {children}
      <span className="inline-flex items-center gap-2 text-label font-bold text-navy">
        {isExpanded ? hideDetailsLabel : showDetailsLabel}
        <ChevronDownIcon isPointingUp={isExpanded} />
      </span>
    </button>
  );
}
