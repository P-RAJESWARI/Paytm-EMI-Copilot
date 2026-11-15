import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { expectNoAccessibilityViolations } from '@test-support/accessibility';

import { BandChip } from './BandChip';
import type { BandChipTone } from './bandChipTone';

const EVERY_TONE: readonly BandChipTone[] = ['comfortable', 'stretching', 'risky'];

describe('BandChip', () => {
  it.each(EVERY_TONE)('shows a decorative icon and the word for the %s band', (tone) => {
    render(<BandChip tone={tone} label={`Word for ${tone}`} />);

    const chip = screen.getByText(`Word for ${tone}`);
    const icon = chip.querySelector('svg');

    expect(icon?.getAttribute('aria-hidden')).toBe('true');
    expect(icon?.getAttribute('data-band-icon')).toBe(tone);
  });

  it('gives every band its own icon, so colour is never the only difference', () => {
    const { container } = render(
      <>
        {EVERY_TONE.map((tone) => (
          <BandChip key={tone} tone={tone} label={tone} />
        ))}
      </>,
    );

    const iconDrawings = Array.from(container.querySelectorAll('svg')).map(
      (icon) => icon.innerHTML,
    );

    expect(new Set(iconDrawings).size).toBe(EVERY_TONE.length);
  });

  it('uses the text-safe band tokens and shows an optional detail after the word', () => {
    render(<BandChip tone="risky" label="Risky" detail="59.3%" />);

    const chip = screen.getByText('Risky');

    expect(chip.className).toContain('bg-risky-tint');
    expect(chip.className).toContain('text-risky-text');
    expect(chip.textContent).toBe('Risky 59.3%');
  });

  it('has no accessibility violations', async () => {
    const { container } = render(
      <>
        {EVERY_TONE.map((tone) => (
          <BandChip key={tone} tone={tone} label={tone} detail="38.9%" />
        ))}
      </>,
    );

    await expectNoAccessibilityViolations(container);
  });
});
