import type { ButtonHTMLAttributes, ReactNode } from 'react';

import { getButtonClassName, type ButtonStyleOptions } from './getButtonClassName';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement>, ButtonStyleOptions {
  children: ReactNode;
}

// A real button in the primary (cyan, navy label), secondary or quiet look, 48 or 56 px tall.
export function Button({
  variant,
  size,
  isFullWidth,
  className,
  type = 'button',
  children,
  ...buttonAttributes
}: ButtonProps) {
  const styleClassName = getButtonClassName({ variant, size, isFullWidth });
  return (
    <button
      type={type}
      className={className === undefined ? styleClassName : `${styleClassName} ${className}`}
      {...buttonAttributes}
    >
      {children}
    </button>
  );
}
