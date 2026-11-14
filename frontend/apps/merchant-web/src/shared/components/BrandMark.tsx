export interface BrandMarkProps {
  /** Pixel size of the square mark. */
  size: number;
}

// The product's own decorative mark (not a Paytm asset): a white tile with a cyan arc and dot.
export function BrandMark({ size }: BrandMarkProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 28 28" aria-hidden="true" focusable="false">
      <rect width="28" height="28" rx="8" className="fill-white" />
      <path
        d="M7.5 19c1.8-6.5 11.2-6.5 13 0"
        className="stroke-cyan"
        strokeWidth="3"
        fill="none"
        strokeLinecap="round"
      />
      <circle cx="14" cy="10.5" r="2.6" className="fill-cyan" />
    </svg>
  );
}
