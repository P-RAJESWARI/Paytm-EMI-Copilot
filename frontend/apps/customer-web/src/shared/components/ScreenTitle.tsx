import { useEffect, useRef } from 'react';

export interface ScreenTitleProps {
  children: string;
}

// The screen's one h1. It takes focus when the screen appears, so screen-reader and keyboard users
// start each step at its title instead of wherever the last button was.
export function ScreenTitle({ children }: ScreenTitleProps) {
  const headingElement = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    headingElement.current?.focus();
  }, []);
  return (
    <h1 ref={headingElement} tabIndex={-1} className="text-heading text-navy outline-none">
      {children}
    </h1>
  );
}
