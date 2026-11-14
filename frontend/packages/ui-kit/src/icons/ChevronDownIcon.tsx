interface ChevronDownIconProps {
  isPointingUp: boolean;
}

// Draws the decorative chevron of an expandable card; it turns over when the card is open.
export function ChevronDownIcon({ isPointingUp }: ChevronDownIconProps) {
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
      className={isPointingUp ? 'rotate-180' : undefined}
    >
      <path d="M6 9l6 6 6-6" />
    </svg>
  );
}
