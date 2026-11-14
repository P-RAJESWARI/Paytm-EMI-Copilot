export type ButtonVariant = 'primary' | 'secondary' | 'quiet';

/** `standard` is the 48 px minimum touch target; `large` is the 56 px primary action. */
export type ButtonSize = 'standard' | 'large';

export interface ButtonStyleOptions {
  variant?: ButtonVariant | undefined;
  size?: ButtonSize | undefined;
  isFullWidth?: boolean | undefined;
}

const VARIANT_CLASS_NAMES: Record<ButtonVariant, string> = {
  // Cyan buttons always carry navy labels; white on cyan fails contrast.
  primary: 'bg-cyan text-navy font-bold',
  secondary: 'border border-border-strong bg-white text-navy font-semibold',
  quiet: 'bg-transparent text-navy font-semibold underline-offset-4 hover:underline',
};

const SIZE_CLASS_NAMES: Record<ButtonSize, string> = {
  standard: 'min-h-touch-target text-body',
  large: 'min-h-touch-target-primary text-lead',
};

// Builds the button classes so a router link can look exactly like a Button.
export function getButtonClassName({
  variant = 'primary',
  size = 'standard',
  isFullWidth = false,
}: ButtonStyleOptions = {}): string {
  return [
    'inline-flex items-center justify-center gap-2 rounded-button px-4 text-center no-underline',
    'disabled:cursor-not-allowed disabled:opacity-60',
    VARIANT_CLASS_NAMES[variant],
    SIZE_CLASS_NAMES[size],
    isFullWidth ? 'w-full' : '',
  ]
    .filter((className) => className !== '')
    .join(' ');
}
