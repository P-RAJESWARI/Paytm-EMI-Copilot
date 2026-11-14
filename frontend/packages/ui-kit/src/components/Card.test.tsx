import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { expectNoAccessibilityViolations } from '@test-support/accessibility';

import { Card } from './Card';

describe('Card', () => {
  it('renders a raised white card with standard padding by default', () => {
    render(<Card>At the counter now</Card>);

    const card = screen.getByText('At the counter now');

    expect(card.tagName).toBe('DIV');
    expect(card.className).toContain('shadow-card');
    expect(card.className).toContain('p-4');
  });

  it('renders as a labelled section with the navy surface, roomy padding and highlight', () => {
    render(
      <Card
        as="section"
        aria-label="This week in short"
        surface="navy"
        padding="roomy"
        isHighlighted
      >
        Summary
      </Card>,
    );

    const card = screen.getByRole('region', { name: 'This week in short' });

    expect(card.className).toContain('bg-navy');
    expect(card.className).toContain('p-6');
    expect(card.className).toContain('border-cyan');
  });

  it('appends a caller class name', () => {
    render(
      <Card surface="soft" className="flex-1">
        Soft
      </Card>,
    );

    expect(screen.getByText('Soft').className).toMatch(/bg-light-blue.* flex-1$/);
  });

  it('has no accessibility violations', async () => {
    const { container } = render(
      <Card as="article" surface="flat">
        Flat
      </Card>,
    );

    await expectNoAccessibilityViolations(container);
  });
});
