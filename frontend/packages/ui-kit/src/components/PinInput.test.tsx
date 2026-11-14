import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';

import { expectNoAccessibilityViolations } from '@test-support/accessibility';

import { PinInput } from './PinInput';

interface PinInputHarnessProps {
  onComplete?: (value: string) => void;
  errorMessage?: string;
  isMasked?: boolean;
}

// Holds the PIN in state the way the pairing container will.
function PinInputHarness({ onComplete, errorMessage, isMasked }: PinInputHarnessProps) {
  const [pin, setPin] = useState('');
  return (
    <>
      <PinInput
        label="Pairing PIN"
        digitLabel={(position, count) => `PIN digit ${position} of ${count}`}
        value={pin}
        onChange={setPin}
        onComplete={onComplete}
        errorMessage={errorMessage}
        isMasked={isMasked}
      />
      <output aria-label="Entered PIN">{pin}</output>
    </>
  );
}

// Gives the box for a 1-based digit position.
function digitBox(position: number): HTMLInputElement {
  const box = screen.getByLabelText(`PIN digit ${position} of 6`);
  if (!(box instanceof HTMLInputElement)) throw new Error('Expected an input element');
  return box;
}

// Reads the PIN the harness holds.
function enteredPin(): string {
  return screen.getByLabelText('Entered PIN').textContent;
}

describe('PinInput', () => {
  it('renders six masked numeric boxes inside a labelled group', () => {
    render(<PinInputHarness />);

    expect(screen.getByRole('group', { name: 'Pairing PIN' })).toBeTruthy();
    for (let position = 1; position <= 6; position += 1) {
      expect(digitBox(position).type).toBe('password');
      expect(digitBox(position).inputMode).toBe('numeric');
    }
  });

  it('moves to the next box while typing and reports completion once', async () => {
    const handleComplete = vi.fn();
    render(<PinInputHarness onComplete={handleComplete} />);

    await userEvent.click(digitBox(1));
    await userEvent.keyboard('482193');

    expect(enteredPin()).toBe('482193');
    expect(handleComplete).toHaveBeenCalledExactlyOnceWith('482193');
    expect(document.activeElement).toBe(digitBox(6));
  });

  it('ignores letters and redirects focus from a later box to the first empty one', async () => {
    render(<PinInputHarness isMasked={false} />);

    await userEvent.click(digitBox(4));
    expect(document.activeElement).toBe(digitBox(1));

    await userEvent.keyboard('a7');

    expect(enteredPin()).toBe('7');
    expect(digitBox(1).value).toBe('7');
  });

  it('fills every box from a pasted PIN, keeping only digits', async () => {
    render(<PinInputHarness />);

    await userEvent.click(digitBox(1));
    await userEvent.paste('48 21-93');

    expect(enteredPin()).toBe('482193');
  });

  it('ignores a paste with no digits', async () => {
    render(<PinInputHarness />);

    await userEvent.click(digitBox(1));
    await userEvent.paste('no digits');

    expect(enteredPin()).toBe('');
  });

  it('clears the previous digit on Backspace in an empty box', async () => {
    render(<PinInputHarness />);

    await userEvent.click(digitBox(1));
    await userEvent.keyboard('482');
    await userEvent.keyboard('{Backspace}');

    expect(enteredPin()).toBe('48');
    expect(document.activeElement).toBe(digitBox(3));
  });

  it('replaces a digit typed over and deletes a cleared box', () => {
    render(<PinInputHarness isMasked={false} />);
    fireEvent.change(digitBox(1), { target: { value: '123' } });

    fireEvent.change(digitBox(2), { target: { value: '29' } });
    expect(enteredPin()).toBe('193');

    fireEvent.change(digitBox(1), { target: { value: '' } });
    expect(enteredPin()).toBe('93');
  });

  it('moves between filled boxes with the arrow keys', async () => {
    render(<PinInputHarness />);
    await userEvent.click(digitBox(1));
    await userEvent.keyboard('48');

    await userEvent.keyboard('{ArrowLeft}');
    expect(document.activeElement).toBe(digitBox(2));

    await userEvent.keyboard('{ArrowRight}{ArrowRight}');
    expect(document.activeElement).toBe(digitBox(3));
  });

  it('shows a calm error tied to every box', () => {
    render(<PinInputHarness errorMessage="That PIN did not match. Try again." />);

    const error = screen.getByRole('alert');

    expect(error.textContent).toBe('That PIN did not match. Try again.');
    expect(digitBox(1).getAttribute('aria-invalid')).toBe('true');
    expect(digitBox(6).getAttribute('aria-describedby')).toBe(error.id);
  });

  it('has no accessibility violations, with or without an error', async () => {
    const { container, rerender } = render(<PinInputHarness />);
    await expectNoAccessibilityViolations(container);

    rerender(<PinInputHarness errorMessage="That PIN did not match." />);
    await expectNoAccessibilityViolations(container);
  });
});
