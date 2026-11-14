import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { expectNoAccessibilityViolations } from '@test-support/accessibility';

import { Button } from './Button';
import { getButtonClassName } from './getButtonClassName';

describe('Button', () => {
  it('renders a real button of type button that calls onClick', async () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Pair device</Button>);

    const button = screen.getByRole('button', { name: 'Pair device' });
    await userEvent.click(button);

    expect(button.getAttribute('type')).toBe('button');
    expect(handleClick).toHaveBeenCalledOnce();
  });

  it('gives the primary variant a cyan background with a navy label', () => {
    render(<Button>Show QR to customer</Button>);

    const className = screen.getByRole('button').className;

    expect(className).toContain('bg-cyan');
    expect(className).toContain('text-navy');
    expect(className).not.toContain('text-white');
  });

  it('uses the 56 px primary target for the large size and 48 px otherwise', () => {
    render(
      <>
        <Button size="large">Take payment</Button>
        <Button variant="secondary">Back to counter list</Button>
      </>,
    );

    expect(screen.getByRole('button', { name: 'Take payment' }).className).toContain(
      'min-h-touch-target-primary',
    );
    expect(screen.getByRole('button', { name: 'Back to counter list' }).className).toMatch(
      /min-h-touch-target(\s|$)/,
    );
  });

  it('does not call onClick when disabled', async () => {
    const handleClick = vi.fn();
    render(
      <Button disabled onClick={handleClick}>
        Pair device
      </Button>,
    );

    await userEvent.click(screen.getByRole('button'));

    expect(handleClick).not.toHaveBeenCalled();
  });

  it('keeps a caller class name after the style classes', () => {
    render(<Button className="self-start">Refresh status</Button>);

    expect(screen.getByRole('button').className).toMatch(/ self-start$/);
  });

  it('builds full-width quiet classes for links that must look like buttons', () => {
    const className = getButtonClassName({ variant: 'quiet', isFullWidth: true });

    expect(className).toContain('bg-transparent');
    expect(className).toContain('w-full');
  });

  it('has no accessibility violations', async () => {
    const { container } = render(
      <>
        <Button>Primary</Button>
        <Button variant="secondary">Secondary</Button>
        <Button variant="quiet">Quiet</Button>
      </>,
    );

    await expectNoAccessibilityViolations(container);
  });
});
