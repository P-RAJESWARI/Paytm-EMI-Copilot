import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { expectNoAccessibilityViolations } from '@test-support/accessibility';

import { SegmentedControl } from './SegmentedControl';

const PERIOD_OPTIONS = [
  { value: 'TODAY', label: 'Today' },
  { value: 'THIS_WEEK', label: 'This week' },
  { value: 'THIS_MONTH', label: 'This month' },
] as const;

describe('SegmentedControl', () => {
  it('marks only the selected option as pressed', () => {
    render(
      <SegmentedControl
        accessibleLabel="Period"
        options={PERIOD_OPTIONS}
        selectedValue="THIS_WEEK"
        onSelectValue={vi.fn()}
      />,
    );

    const pressedStates = screen
      .getAllByRole('button')
      .map((button) => button.getAttribute('aria-pressed'));

    expect(screen.getByRole('group', { name: 'Period' })).toBeTruthy();
    expect(pressedStates).toEqual(['false', 'true', 'false']);
  });

  it('reports the chosen value', async () => {
    const handleSelectValue = vi.fn();
    render(
      <SegmentedControl
        accessibleLabel="Period"
        options={PERIOD_OPTIONS}
        selectedValue="THIS_WEEK"
        onSelectValue={handleSelectValue}
      />,
    );

    await userEvent.click(screen.getByRole('button', { name: 'This month' }));

    expect(handleSelectValue).toHaveBeenCalledWith('THIS_MONTH');
  });

  it('has no accessibility violations', async () => {
    const { container } = render(
      <SegmentedControl
        accessibleLabel="Period"
        options={PERIOD_OPTIONS}
        selectedValue="TODAY"
        onSelectValue={vi.fn()}
      />,
    );

    await expectNoAccessibilityViolations(container);
  });
});
