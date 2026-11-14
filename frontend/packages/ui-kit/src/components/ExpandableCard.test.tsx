import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { describe, expect, it } from 'vitest';

import { expectNoAccessibilityViolations } from '@test-support/accessibility';

import { ExpandableCard } from './ExpandableCard';

type OpenCard = 'missedSales' | 'moneyDue' | 'none';

// Two cards where opening one closes the other, as on the M5 sales report.
function AccordionOfTwoCards() {
  const [openCard, setOpenCard] = useState<OpenCard>('none');
  const toggle = (card: OpenCard) => {
    setOpenCard((current) => (current === card ? 'none' : card));
  };
  return (
    <>
      <ExpandableCard
        summary={<span>Missed sales</span>}
        isExpanded={openCard === 'missedSales'}
        onToggle={() => {
          toggle('missedSales');
        }}
        showDetailsLabel="See details"
        hideDetailsLabel="Hide details"
        panelAccessibleLabel="Missed sales detail"
      >
        <p>12 customers wanted under ₹3,000</p>
      </ExpandableCard>
      <ExpandableCard
        summary={<span>Money due from brands</span>}
        isExpanded={openCard === 'moneyDue'}
        onToggle={() => {
          toggle('moneyDue');
        }}
        showDetailsLabel="See details"
        hideDetailsLabel="Hide details"
        panelAccessibleLabel="Money due detail"
      >
        <p>Batch 1</p>
      </ExpandableCard>
    </>
  );
}

describe('ExpandableCard', () => {
  it('starts collapsed with a button whose aria-controls points at the hidden panel', () => {
    render(<AccordionOfTwoCards />);

    const button = screen.getByRole('button', { name: /Missed sales/ });
    const panelId = button.getAttribute('aria-controls') ?? '';

    expect(button.getAttribute('aria-expanded')).toBe('false');
    expect(button.textContent).toContain('See details');
    expect(document.getElementById(panelId)?.hidden).toBe(true);
    expect(screen.queryByText('12 customers wanted under ₹3,000')).toBeNull();
  });

  it('opens in place and shows the hide label', async () => {
    render(<AccordionOfTwoCards />);

    await userEvent.click(screen.getByRole('button', { name: /Missed sales/ }));

    const button = screen.getByRole('button', { name: /Missed sales/ });
    expect(button.getAttribute('aria-expanded')).toBe('true');
    expect(button.textContent).toContain('Hide details');
    expect(screen.getByRole('region', { name: 'Missed sales detail' }).textContent).toBe(
      '12 customers wanted under ₹3,000',
    );
  });

  it('keeps only one card open when used as an accordion', async () => {
    render(<AccordionOfTwoCards />);

    await userEvent.click(screen.getByRole('button', { name: /Missed sales/ }));
    await userEvent.click(screen.getByRole('button', { name: /Money due/ }));

    expect(screen.getByRole('button', { name: /Missed sales/ }).getAttribute('aria-expanded')).toBe(
      'false',
    );
    expect(screen.getByRole('region', { name: 'Money due detail' }).textContent).toBe('Batch 1');
  });

  it('closes again on a second press', async () => {
    render(<AccordionOfTwoCards />);
    const button = screen.getByRole('button', { name: /Money due/ });

    await userEvent.click(button);
    await userEvent.click(button);

    expect(button.getAttribute('aria-expanded')).toBe('false');
  });

  it('has no accessibility violations when collapsed or expanded', async () => {
    const { container } = render(<AccordionOfTwoCards />);
    await expectNoAccessibilityViolations(container);

    await userEvent.click(screen.getByRole('button', { name: /Missed sales/ }));
    await expectNoAccessibilityViolations(container);
  });
});
