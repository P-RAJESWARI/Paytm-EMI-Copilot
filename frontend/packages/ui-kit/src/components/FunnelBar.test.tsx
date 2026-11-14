import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { expectNoAccessibilityViolations } from '@test-support/accessibility';

import { FunnelBar } from './FunnelBar';

// Reads the inline width of the rendered bar fill.
function renderedBarWidth(): string {
  return screen.getByTestId('funnel-bar-fill').style.width;
}

describe('FunnelBar', () => {
  it('shows the stage label and the count text', () => {
    render(<FunnelBar label="Saw the plans" valueText="88" value={88} maximumValue={120} />);

    expect(screen.getByText('Saw the plans')).toBeTruthy();
    expect(screen.getByText('88')).toBeTruthy();
  });

  it('scales the bar to the share of the maximum', () => {
    render(<FunnelBar label="Told a budget" valueText="96" value={96} maximumValue={120} />);

    expect(renderedBarWidth()).toBe('80%');
  });

  it.each([
    { case: 'a zero maximum', value: 5, maximumValue: 0, expectedWidth: '0%' },
    { case: 'a negative value', value: -3, maximumValue: 120, expectedWidth: '0%' },
    { case: 'a value above the maximum', value: 150, maximumValue: 120, expectedWidth: '100%' },
  ])('clamps the bar for $case', ({ value, maximumValue, expectedWidth }) => {
    render(<FunnelBar label="Stage" valueText="x" value={value} maximumValue={maximumValue} />);

    expect(renderedBarWidth()).toBe(expectedWidth);
  });

  it('colours the success tone green and hides the bar from screen readers', () => {
    render(<FunnelBar label="Paid" valueText="44" value={44} maximumValue={120} tone="success" />);

    const fill = screen.getByTestId('funnel-bar-fill');

    expect(fill.className).toContain('bg-green');
    expect(fill.parentElement?.getAttribute('aria-hidden')).toBe('true');
  });

  it('has no accessibility violations', async () => {
    const { container } = render(
      <FunnelBar label="Started" valueText="120" value={120} maximumValue={120} />,
    );

    await expectNoAccessibilityViolations(container);
  });
});
