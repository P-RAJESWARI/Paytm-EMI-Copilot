import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { expectNoAccessibilityViolations } from '@test-support/accessibility';

import { CustomerApiError } from '../../customer-flow';
import { FixtureCustomerFlowApi } from '../../customer-flow/fixture';
import { renderCustomerFlow } from '../../../testing/renderCustomerFlow';

const BUDGET_STEP = { step: 'budget', previousBudgetInPaise: undefined } as const;

afterEach(() => {
  window.localStorage.clear();
});

describe('C2 budget', () => {
  it('starts empty with a hint and Continue disabled', async () => {
    const { container } = renderCustomerFlow({ initialFlowState: BUDGET_STEP });

    expect(await screen.findByRole('textbox', { name: 'Monthly amount' })).toHaveProperty(
      'value',
      '',
    );
    expect(screen.getByText('Type an amount or tap the microphone to continue.')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Continue' })).toHaveProperty('disabled', true);
    await expectNoAccessibilityViolations(container);
  });

  it('asks "You said ₹3,000. Correct?" and sends nothing until the customer says yes', async () => {
    const customerFlowApi = new FixtureCustomerFlowApi();
    const confirmBudget = vi.spyOn(customerFlowApi, 'confirmBudget');
    const { container } = renderCustomerFlow({ customerFlowApi, initialFlowState: BUDGET_STEP });

    await userEvent.type(await screen.findByRole('textbox', { name: 'Monthly amount' }), '₹3,000');
    await userEvent.click(screen.getByRole('button', { name: 'Continue' }));

    expect(screen.getByText('You said ₹3,000. Correct?')).toBeTruthy();
    expect(confirmBudget).not.toHaveBeenCalled();
    await expectNoAccessibilityViolations(container);
    await userEvent.click(screen.getByRole('button', { name: 'Yes, correct' }));

    expect(confirmBudget).toHaveBeenCalledWith(300000);
    expect(
      await screen.findByRole('heading', { name: 'Check if a plan fits your month?' }),
    ).toBeTruthy();
  });

  it('lets the customer edit the amount instead of confirming it', async () => {
    renderCustomerFlow({ initialFlowState: BUDGET_STEP });
    const amountInput = await screen.findByRole('textbox', { name: 'Monthly amount' });
    await userEvent.type(amountInput, '30000{Enter}');

    expect(screen.getByText('You said ₹30,000. Correct?')).toBeTruthy();
    await userEvent.click(screen.getByRole('button', { name: 'Edit' }));
    await userEvent.clear(amountInput);
    await userEvent.type(amountInput, '3000');

    expect(screen.queryByText(/Correct\?/)).toBeNull();
    expect(amountInput).toHaveProperty('value', '3000');
  });

  it('shows a calm error with a retry when the budget could not be saved', async () => {
    const customerFlowApi = new FixtureCustomerFlowApi();
    vi.spyOn(customerFlowApi, 'confirmBudget').mockRejectedValueOnce(
      new CustomerApiError(0, 'NETWORK_UNAVAILABLE'),
    );
    renderCustomerFlow({ customerFlowApi, initialFlowState: BUDGET_STEP });
    await userEvent.type(
      await screen.findByRole('textbox', { name: 'Monthly amount' }),
      '3000{Enter}',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Yes, correct' }));

    expect((await screen.findByRole('alert')).textContent).toContain(
      'Your phone could not reach us.',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));

    expect(
      await screen.findByRole('heading', { name: 'Check if a plan fits your month?' }),
    ).toBeTruthy();
  });

  it('shows the budget again when the customer comes back, and goes back to C1', async () => {
    renderCustomerFlow({ initialFlowState: { step: 'budget', previousBudgetInPaise: 180000 } });

    expect(await screen.findByRole('textbox', { name: 'Monthly amount' })).toHaveProperty(
      'value',
      '1800',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Back' }));

    expect(screen.getByRole('button', { name: 'Start' })).toBeTruthy();
  });
});
