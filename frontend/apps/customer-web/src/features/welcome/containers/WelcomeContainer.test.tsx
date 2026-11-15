import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it } from 'vitest';

import { expectNoAccessibilityViolations } from '@test-support/accessibility';

import { renderCustomerFlow } from '../../../testing/renderCustomerFlow';

afterEach(() => {
  window.localStorage.clear();
});

describe('C1 welcome', () => {
  it('shows the shop, the item and its price, the data-use line and Start', async () => {
    const { container } = renderCustomerFlow();

    expect(
      await screen.findByRole('heading', { name: 'Pay in EMIs, with every cost shown' }),
    ).toBeTruthy();
    expect(screen.getByText('At Ravi Electronics')).toBeTruthy();
    expect(screen.getByText('Example phone, 128 GB')).toBeTruthy();
    expect(screen.getByText('₹22,000')).toBeTruthy();
    expect(screen.getByText(/The shop cannot see these\./)).toBeTruthy();
    await expectNoAccessibilityViolations(container);
  });

  it('keeps the pinned Start action inside the main landmark', async () => {
    renderCustomerFlow();

    const startButton = await screen.findByRole('button', { name: 'Start' });

    expect(within(screen.getByRole('main')).getByRole('button', { name: 'Start' })).toBe(
      startButton,
    );
  });

  it('switches every string to Tamil from the large choice and remembers it on the device', async () => {
    renderCustomerFlow();

    await screen.findByRole('heading', { name: 'Pay in EMIs, with every cost shown' });
    const languageChoice = screen.getByRole('group', { name: 'Choose your language' });
    const tamilChoice = Array.from(languageChoice.querySelectorAll('button')).find(
      (button) => button.textContent === 'தமிழ்',
    );
    if (tamilChoice === undefined) throw new Error('The Tamil choice is missing');

    await userEvent.click(tamilChoice);

    expect(
      screen.getByRole('heading', { name: 'எல்லா செலவும் தெரிந்து EMI-யில் வாங்குங்கள்' }),
    ).toBeTruthy();
    expect(screen.getByRole('button', { name: 'தொடங்கு' })).toBeTruthy();
    expect(window.localStorage.getItem('emiCopilot.language')).toBe('ta');
    expect(document.documentElement.lang).toBe('ta');
  });

  it('starts the flow on the budget screen', async () => {
    renderCustomerFlow();

    await userEvent.click(await screen.findByRole('button', { name: 'Start' }));

    expect(
      screen.getByRole('heading', { name: 'What monthly amount feels comfortable?' }),
    ).toBeTruthy();
    expect(screen.getByText('Step 1 of 4')).toBeTruthy();
  });
});
