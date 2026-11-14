import type { HTMLAttributes, ReactNode } from 'react';

/** `raised` white with the soft shadow, `flat` white, `soft` light blue, `navy` for insight cards. */
export type CardSurface = 'raised' | 'flat' | 'soft' | 'navy';

export type CardPadding = 'standard' | 'roomy';

export type CardElement = 'div' | 'section' | 'article' | 'aside';

export interface CardProps extends HTMLAttributes<HTMLElement> {
  children: ReactNode;
  surface?: CardSurface | undefined;
  padding?: CardPadding | undefined;
  /** Draws the 2 px cyan border used for the selected or open card. */
  isHighlighted?: boolean | undefined;
  as?: CardElement | undefined;
}

const SURFACE_CLASS_NAMES: Record<CardSurface, string> = {
  raised: 'bg-white text-deep-navy shadow-card',
  flat: 'bg-white text-deep-navy',
  soft: 'bg-light-blue text-deep-navy',
  navy: 'bg-navy text-white',
};

const PADDING_CLASS_NAMES: Record<CardPadding, string> = {
  standard: 'p-4',
  roomy: 'p-6',
};

// A radius-16 container in one of the four mockup surfaces; layout inside is up to the caller.
export function Card({
  children,
  surface = 'raised',
  padding = 'standard',
  isHighlighted = false,
  as: Element = 'div',
  className,
  ...elementAttributes
}: CardProps) {
  const classNames = [
    'rounded-card',
    SURFACE_CLASS_NAMES[surface],
    PADDING_CLASS_NAMES[padding],
    isHighlighted ? 'border-2 border-cyan' : '',
    className ?? '',
  ].filter((name) => name !== '');
  return (
    <Element className={classNames.join(' ')} {...elementAttributes}>
      {children}
    </Element>
  );
}
