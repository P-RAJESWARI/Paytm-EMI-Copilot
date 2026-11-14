import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { expectNoAccessibilityViolations } from '@test-support/accessibility';

import { Chip } from './Chip';

describe('Chip', () => {
  it('shows its text with an outline pill by default', () => {
    render(<Chip>₹667 above your budget</Chip>);

    const chip = screen.getByText('₹667 above your budget');

    expect(chip.className).toContain('border-border-strong');
    expect(chip.className).toContain('rounded-pill');
  });

  it('supports the rounded shape, other tones and a decorative icon', () => {
    render(
      <Chip tone="information" shape="rounded" icon={<svg aria-hidden="true" data-testid="icon" />}>
        Claim filed
      </Chip>,
    );

    const chip = screen.getByText('Claim filed');

    expect(chip.className).toContain('rounded-input');
    expect(chip.className).toContain('bg-cyan-tint');
    expect(screen.getByTestId('icon').getAttribute('aria-hidden')).toBe('true');
  });

  it('uses the orange tint for the attention tone', () => {
    render(<Chip tone="attention">Waiting for brand</Chip>);

    expect(screen.getByText('Waiting for brand').className).toContain(
      'bg-stretching-tint text-stretching-text',
    );
  });

  it('has no accessibility violations', async () => {
    const { container } = render(
      <>
        <Chip tone="soft">Soft</Chip>
        <Chip tone="neutral">Neutral</Chip>
        <Chip tone="attention">Attention</Chip>
      </>,
    );

    await expectNoAccessibilityViolations(container);
  });
});
