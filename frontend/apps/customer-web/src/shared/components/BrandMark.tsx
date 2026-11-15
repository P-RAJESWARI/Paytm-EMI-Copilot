// The product's own decorative mark from the C1 and C10 mockups (not a Paytm asset): a navy tile
// with a cyan arc and dot.
export function BrandMark() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" aria-hidden="true" focusable="false">
      <rect width="28" height="28" rx="8" className="fill-navy" />
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
