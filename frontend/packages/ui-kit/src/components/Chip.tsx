import type { ReactNode } from 'react';

export type ChipTone = 'outline' | 'soft' | 'information' | 'neutral';

/** `pill` for status-like chips, `rounded` (radius 12) for value chips. */
export type ChipShape = 'pill' | 'rounded';

export interface ChipProps {
  children: ReactNode;
  tone?: ChipTone | undefined;
  shape?: ChipShape | undefined;
  /** A decorative icon shown before the text; it must be aria-hidden. */
  icon?: ReactNode;
}

const TONE_CLASS_NAMES: Record<ChipTone, string> = {
  outline: 'border border-border-strong bg-white text-deep-navy',
  soft: 'bg-light-blue text-navy',
  information: 'bg-cyan-tint text-navy',
  neutral: 'bg-grey-tint text-ink-muted',
};

// A small non-interactive label, such as "₹667 above your budget". Never used for comfort bands.
export function Chip({ children, tone = 'outline', shape = 'pill', icon }: ChipProps) {
  const shapeClassName = shape === 'pill' ? 'rounded-pill' : 'rounded-input';
  return (
    <span
      className={`inline-flex min-h-8 items-center gap-2 px-3 text-label ${shapeClassName} ${TONE_CLASS_NAMES[tone]}`}
    >
      {icon}
      {children}
    </span>
  );
}
