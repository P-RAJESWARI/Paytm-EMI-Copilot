import type { StatusChipTone } from '../components/statusChipTone';

interface StatusIconProps {
  tone: StatusChipTone;
}

const STROKE_ICON_PATHS: Record<StatusChipTone, readonly string[]> = {
  // A phone: the customer is choosing on their own phone.
  choosing: ['M8 3h8a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1H8a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z', 'M11 18h2'],
  // An arrow into a circle: the next step (payment) can start.
  ready: ['M12 3a9 9 0 1 1 0 18a9 9 0 0 1 0-18z', 'M8 12h8', 'M13 8.5l3.5 3.5-3.5 3.5'],
  // A plain tick, deliberately unlike the circled tick of the Comfortable band.
  paid: ['M5 12.5l4.5 4.5L19 7.5'],
  // An "i" in a circle: calm, no cross, never reads as "declined".
  notCompleted: ['M12 3a9 9 0 1 1 0 18a9 9 0 0 1 0-18z', 'M12 11v5', 'M12 8v.01'],
  // An hourglass: time ran out.
  expired: ['M7 3h10', 'M7 21h10', 'M8 3c0 5 8 5 8 9s-8 4-8 9', 'M16 3c0 5-8 5-8 9s8 4 8 9'],
  // A small dot for statuses with no special meaning.
  neutral: ['M12 9.5a2.5 2.5 0 1 1 0 5a2.5 2.5 0 0 1 0-5z'],
};

// Draws the decorative icon that goes with each status chip tone; the word beside it carries the meaning.
export function StatusIcon({ tone }: StatusIconProps) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.4"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      data-status-icon={tone}
    >
      {STROKE_ICON_PATHS[tone].map((pathData) => (
        <path key={pathData} d={pathData} />
      ))}
    </svg>
  );
}
