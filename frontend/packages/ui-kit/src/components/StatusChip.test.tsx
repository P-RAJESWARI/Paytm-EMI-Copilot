import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { expectNoAccessibilityViolations } from '@test-support/accessibility';

import { StatusChip } from './StatusChip';
import type { StatusChipTone } from './statusChipTone';

const EVERY_TONE: readonly StatusChipTone[] = [
  'choosing',
  'ready',
  'paid',
  'notCompleted',
  'expired',
  'neutral',
];

describe('StatusChip', () => {
  it.each(EVERY_TONE)('shows a decorative icon and the word for the %s tone', (tone) => {
    render(<StatusChip tone={tone} label={`Label for ${tone}`} />);

    const chip = screen.getByText(`Label for ${tone}`);
    const icon = chip.querySelector('svg');

    expect(icon?.getAttribute('aria-hidden')).toBe('true');
    expect(icon?.getAttribute('data-status-icon')).toBe(tone);
  });

  it('gives every tone its own icon, so colour is never the only difference', () => {
    const { container } = render(
      <>
        {EVERY_TONE.map((tone) => (
          <StatusChip key={tone} tone={tone} label={tone} />
        ))}
      </>,
    );

    const iconDrawings = Array.from(container.querySelectorAll('svg')).map(
      (icon) => icon.innerHTML,
    );

    expect(new Set(iconDrawings).size).toBe(EVERY_TONE.length);
  });

  it('uses the status tokens for colour', () => {
    render(<StatusChip tone="ready" label="Ready to pay" />);

    const className = screen.getByText('Ready to pay').className;

    expect(className).toContain('bg-status-ready-tint');
    expect(className).toContain('text-status-ready-text');
  });

  it('has no accessibility violations', async () => {
    const { container } = render(
      <>
        {EVERY_TONE.map((tone) => (
          <StatusChip key={tone} tone={tone} label={tone} />
        ))}
      </>,
    );

    await expectNoAccessibilityViolations(container);
  });
});
