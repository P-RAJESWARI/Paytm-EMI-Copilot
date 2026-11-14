import {
  useId,
  useLayoutEffect,
  useRef,
  type ChangeEvent,
  type ClipboardEvent,
  type KeyboardEvent,
} from 'react';

import { digitsTypedIntoBox, extractDigits, replaceDigitsAtPosition } from './pinDigits';

export interface PinInputProps {
  /** Translated visible label, for example "Pairing PIN". */
  label: string;
  /** Translated name for each box, for example (1, 6) gives "PIN digit 1 of 6". */
  digitLabel: (digitPosition: number, digitCount: number) => string;
  /** The digits entered so far (controlled). */
  value: string;
  onChange: (value: string) => void;
  /** Called once when the last digit is entered. */
  onComplete?: ((value: string) => void) | undefined;
  digitCount?: number | undefined;
  /** Shows dots instead of digits; on by default. */
  isMasked?: boolean | undefined;
  /** A calm, translated error shown under the boxes (for example after a wrong PIN). */
  errorMessage?: string | undefined;
  isDisabled?: boolean | undefined;
}

const DEFAULT_DIGIT_COUNT = 6;

// A row of single-digit boxes for a PIN or OTP: numeric keyboard, paste fills every box, masked by default.
export function PinInput({
  label,
  digitLabel,
  value,
  onChange,
  onComplete,
  digitCount = DEFAULT_DIGIT_COUNT,
  isMasked = true,
  errorMessage,
  isDisabled = false,
}: PinInputProps) {
  const errorId = useId();
  const digitInputs = useRef<(HTMLInputElement | null)[]>([]);
  // Focus moves after React renders the new digits, so the focus redirect below sees them.
  const pendingFocusPosition = useRef<number | null>(null);
  const digits = extractDigits(value).slice(0, digitCount);
  const hasError = errorMessage !== undefined;

  // Moves focus to a box, never past the last one.
  function focusDigitBox(position: number) {
    digitInputs.current[Math.min(Math.max(position, 0), digitCount - 1)]?.focus();
  }

  useLayoutEffect(() => {
    if (pendingFocusPosition.current === null) return;
    focusDigitBox(pendingFocusPosition.current);
    pendingFocusPosition.current = null;
  });

  // Reports the new PIN, announces completion once and queues focus for the next empty box.
  function commitDigits(nextDigits: string, nextFocusPosition: number) {
    pendingFocusPosition.current = nextFocusPosition;
    onChange(nextDigits);
    if (nextDigits.length === digitCount && digits.length !== digitCount) onComplete?.(nextDigits);
  }

  // Handles typing, deleting and autofill in one box.
  function handleDigitChange(position: number, event: ChangeEvent<HTMLInputElement>) {
    const typedDigits = digitsTypedIntoBox(event.target.value, digits[position]);
    if (typedDigits === '' && event.target.value !== '') return;
    const nextDigits = replaceDigitsAtPosition(digits, position, typedDigits, digitCount);
    commitDigits(nextDigits, position + typedDigits.length);
  }

  // Fills the boxes from the pasted digits, starting at the box that has focus.
  function handleDigitPaste(position: number, event: ClipboardEvent<HTMLInputElement>) {
    event.preventDefault();
    const pastedDigits = extractDigits(event.clipboardData.getData('text'));
    if (pastedDigits === '') return;
    const nextDigits = (digits.slice(0, position) + pastedDigits).slice(0, digitCount);
    commitDigits(nextDigits, nextDigits.length);
  }

  // Backspace in an empty box clears the box before it; arrow keys move between filled boxes.
  function handleDigitKeyDown(position: number, event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Backspace' && digits[position] === undefined && position > 0) {
      event.preventDefault();
      commitDigits(digits.slice(0, position - 1), position - 1);
    } else if (event.key === 'ArrowLeft') {
      event.preventDefault();
      focusDigitBox(position - 1);
    } else if (event.key === 'ArrowRight') {
      event.preventDefault();
      focusDigitBox(Math.min(position + 1, digits.length));
    }
  }

  return (
    <fieldset className="m-0 flex min-w-0 flex-col gap-2 border-0 p-0" disabled={isDisabled}>
      <legend className="mb-2 p-0 text-body font-semibold text-deep-navy">{label}</legend>
      <div
        className="grid gap-2"
        style={{ gridTemplateColumns: `repeat(${digitCount}, minmax(0, 1fr))` }}
      >
        {Array.from({ length: digitCount }, (_unused, position) => (
          <input
            key={position}
            ref={(element) => {
              digitInputs.current[position] = element;
            }}
            type={isMasked ? 'password' : 'text'}
            inputMode="numeric"
            pattern="[0-9]*"
            autoComplete="off"
            aria-label={digitLabel(position + 1, digitCount)}
            aria-invalid={hasError}
            aria-describedby={hasError ? errorId : undefined}
            value={digits[position] ?? ''}
            onFocus={() => {
              if (position > digits.length) focusDigitBox(digits.length);
            }}
            onChange={(event) => {
              handleDigitChange(position, event);
            }}
            onPaste={(event) => {
              handleDigitPaste(position, event);
            }}
            onKeyDown={(event) => {
              handleDigitKeyDown(position, event);
            }}
            className={`box-border min-h-touch-target-primary w-full min-w-0 rounded-input border-2 bg-white text-center text-title text-navy ${
              hasError
                ? 'border-risky-text'
                : digits[position] === undefined
                  ? 'border-border'
                  : 'border-cyan'
            }`}
          />
        ))}
      </div>
      {hasError ? (
        <p id={errorId} role="alert" className="text-label font-normal text-risky-text">
          {errorMessage}
        </p>
      ) : null}
    </fieldset>
  );
}
