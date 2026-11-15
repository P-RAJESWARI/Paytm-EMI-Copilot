import type { BandChipTone } from '../components/bandChipTone';

interface BandIconProps {
  tone: BandChipTone;
}

const BAND_ICON_PATHS: Record<BandChipTone, readonly string[]> = {
  // A circled tick: the plan sits comfortably in the month.
  comfortable: ['M12 3a9 9 0 1 1 0 18a9 9 0 0 1 0-18z', 'M8 12.5l2.5 2.5L16 9.5'],
  // A gauge leaning right: the plan stretches the month.
  stretching: ['M4 17a8 8 0 0 1 16 0', 'M12 17l3-5'],
  // A warning triangle: the plan takes a large share of the month.
  risky: ['M12 3l9.5 17h-19z', 'M12 10v4', 'M12 17.5v.5'],
};

// Draws the decorative icon of a comfort band, from the Components mockup; the word beside it carries the meaning.
export function BandIcon({ tone }: BandIconProps) {
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
      data-band-icon={tone}
    >
      {BAND_ICON_PATHS[tone].map((pathData) => (
        <path key={pathData} d={pathData} />
      ))}
    </svg>
  );
}
