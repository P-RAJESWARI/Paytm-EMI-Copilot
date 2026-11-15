import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { expectNoAccessibilityViolations } from '@test-support/accessibility';

import { CustomerApiError } from '../../customer-flow';
import { FixtureCustomerFlowApi } from '../../customer-flow/fixture';
import { renderCustomerFlow } from '../../../testing/renderCustomerFlow';

const COMFORT_CONSENT_STEP = { step: 'comfortConsent', confirmedBudgetInPaise: 300000 } as const;

// Builds a fixture whose budget is already confirmed, as C2 left it.
async function fixtureWithBudget(): Promise<FixtureCustomerFlowApi> {
  const fixture = new FixtureCustomerFlowApi();
  await fixture.startSession('preparation-qr-token');
  await fixture.confirmBudget(300000);
  return fixture;
}

afterEach(() => {
  window.localStorage.clear();
});

describe('C3 comfort check consent', () => {
  it('says what is read, that the shop cannot see it and that it is advice only', async () => {
    const { container } = renderCustomerFlow({ initialFlowState: COMFORT_CONSENT_STEP });

    expect(
      await screen.findByRole('heading', { name: 'Check if a plan fits your month?' }),
    ).toBeTruthy();
    expect(screen.getAllByRole('listitem').map((item) => item.textContent)).toEqual([
      'Average money coming in each month',
      'EMIs you already pay',
    ]);
    expect(screen.getByText('The shop cannot see this information.')).toBeTruthy();
    expect(
      screen.getByText('This is advice to help you choose. It is not a loan decision.'),
    ).toBeTruthy();
    expect(screen.getByText('Step 2 of 4')).toBeTruthy();
    await expectNoAccessibilityViolations(container);
  });

  it('runs the check on Allow and shows the plans with bands', async () => {
    renderCustomerFlow({
      customerFlowApi: await fixtureWithBudget(),
      initialFlowState: COMFORT_CONSENT_STEP,
    });

    await userEvent.click(await screen.findByRole('button', { name: 'Allow' }));

    expect(await screen.findByRole('heading', { name: 'Your EMI options' })).toBeTruthy();
    expect((await screen.findAllByText('Stretching')).length).toBe(2);
  });

  it('skips the check and still shows every plan, without bands', async () => {
    renderCustomerFlow({
      customerFlowApi: await fixtureWithBudget(),
      initialFlowState: COMFORT_CONSENT_STEP,
    });

    await userEvent.click(
      await screen.findByRole('button', { name: /Skip\s*You can still compare all plans/ }),
    );

    expect(await screen.findAllByRole('radio')).toHaveLength(3);
    expect(screen.queryByText(/Comfortable|Stretching|Risky/)).toBeNull();
  });

  it('shows a calm error when the answer could not be sent, and goes back to C2', async () => {
    const customerFlowApi = await fixtureWithBudget();
    vi.spyOn(customerFlowApi, 'answerComfortCheck').mockRejectedValueOnce(
      new CustomerApiError(500, 'INTERNAL_SERVER_ERROR', { hasProblemBody: true }),
    );
    renderCustomerFlow({ customerFlowApi, initialFlowState: COMFORT_CONSENT_STEP });

    await userEvent.click(await screen.findByRole('button', { name: 'Allow' }));

    expect((await screen.findByRole('alert')).textContent).toBe(
      'Something did not load. Please try again.',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Back' }));
    expect(screen.getByRole('textbox', { name: 'Monthly amount' })).toHaveProperty('value', '3000');
  });

  it('reads in Tamil', async () => {
    window.localStorage.setItem('emiCopilot.language', 'ta');

    renderCustomerFlow({ initialFlowState: COMFORT_CONSENT_STEP });

    expect(await screen.findByText('இந்தத் தகவலை கடை பார்க்க முடியாது.')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'அனுமதி' })).toBeTruthy();
  });
});
