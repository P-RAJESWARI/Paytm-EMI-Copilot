import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { describe, expect, it } from 'vitest';

import { expectNoAccessibilityViolations } from '@test-support/accessibility';

import { Tabs } from './Tabs';

type SectionId = 'newSale' | 'report' | 'help';

// Holds the selected tab the way a real container would.
function ControlledTabs({ initialTabId = 'newSale' }: { initialTabId?: SectionId }) {
  const [selectedTabId, setSelectedTabId] = useState<SectionId>(initialTabId);
  return (
    <Tabs
      accessibleLabel="Sections"
      selectedTabId={selectedTabId}
      onSelectTab={setSelectedTabId}
      tabs={[
        { id: 'newSale', label: 'New EMI sale', panel: <p>Sale panel</p> },
        { id: 'report', label: 'Sales report', panel: <p>Report panel</p> },
        { id: 'help', label: 'Help', panel: <p>Help panel</p> },
      ]}
    />
  );
}

describe('Tabs', () => {
  it('renders a labelled tablist with the selected tab and its panel', () => {
    render(<ControlledTabs />);

    const selectedTab = screen.getByRole('tab', { name: 'New EMI sale' });

    expect(screen.getByRole('tablist', { name: 'Sections' })).toBeTruthy();
    expect(selectedTab.getAttribute('aria-selected')).toBe('true');
    expect(selectedTab.tabIndex).toBe(0);
    expect(screen.getByRole('tab', { name: 'Sales report' }).tabIndex).toBe(-1);
    expect(screen.getByRole('tabpanel', { name: 'New EMI sale' }).textContent).toBe('Sale panel');
  });

  it('selects a tab on click', async () => {
    render(<ControlledTabs />);

    await userEvent.click(screen.getByRole('tab', { name: 'Sales report' }));

    expect(screen.getByRole('tabpanel', { name: 'Sales report' }).textContent).toBe('Report panel');
  });

  it('moves selection and focus with the arrow keys, wrapping at both ends', async () => {
    render(<ControlledTabs />);
    await userEvent.click(screen.getByRole('tab', { name: 'New EMI sale' }));

    await userEvent.keyboard('{ArrowLeft}');
    expect(document.activeElement).toBe(screen.getByRole('tab', { name: 'Help' }));

    await userEvent.keyboard('{ArrowRight}');
    expect(screen.getByRole('tab', { name: 'New EMI sale' }).getAttribute('aria-selected')).toBe(
      'true',
    );
  });

  it('jumps to the first and last tab with Home and End and ignores other keys', async () => {
    render(<ControlledTabs initialTabId="report" />);
    await userEvent.click(screen.getByRole('tab', { name: 'Sales report' }));

    await userEvent.keyboard('{End}');
    expect(document.activeElement).toBe(screen.getByRole('tab', { name: 'Help' }));

    await userEvent.keyboard('{Home}');
    expect(document.activeElement).toBe(screen.getByRole('tab', { name: 'New EMI sale' }));

    await userEvent.keyboard('a');
    expect(document.activeElement).toBe(screen.getByRole('tab', { name: 'New EMI sale' }));
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<ControlledTabs />);

    await expectNoAccessibilityViolations(container);
  });
});
