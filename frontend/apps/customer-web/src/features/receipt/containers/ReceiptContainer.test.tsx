import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { expectNoAccessibilityViolations } from '@test-support/accessibility';

import { CustomerApiError, type ReceiptStatus } from '../../customer-flow';
import { FixtureCustomerFlowApi } from '../../customer-flow/fixture';
import { FIXTURE_OTP } from '../../customer-flow/api/fixtureCustomerFlowData';
import { DESIGN_PLAN_ANSWERS } from '../../../testing/customerFlowTestData';
import { renderCustomerFlow } from '../../../testing/renderCustomerFlow';
import { RECEIPT_POLL_INTERVAL_IN_MILLISECONDS } from '../hooks/useCustomerReceipt';

const RECEIPT_STEP = { step: 'receipt', answers: DESIGN_PLAN_ANSWERS } as const;

// Builds a fixture where consent to plan A is recorded and the receipt moves through `statuses`.
async function fixtureWithConsent(statuses: readonly ReceiptStatus[]) {
  const fixture = new FixtureCustomerFlowApi({ receiptStatuses: statuses });
  await fixture.startSession('preparation-qr-token');
  await fixture.confirmBudget(300000);
  await fixture.answerComfortCheck(true);
  await fixture.requestConsentOtp();
  await fixture.giveConsent(
    {
      offerId: 'mock-offer-no-cost-6m',
      shownMonthlyInstallmentInPaise: 366667,
      shownTotalPayableInPaise: 2200000,
      otp: FIXTURE_OTP,
    },
    'preparation-key',
  );
  return fixture;
}

afterEach(() => {
  window.localStorage.clear();
  vi.useRealTimers();
});

describe('C10 handoff and receipt', () => {
  it('hands off to the shop with the plan, item, reference and cooling-off note', async () => {
    const customerFlowApi = await fixtureWithConsent(['READY_TO_PAY']);
    const { container } = renderCustomerFlow({ customerFlowApi, initialFlowState: RECEIPT_STEP });

    expect(await screen.findByRole('heading', { name: 'Your plan is ready' })).toBeTruthy();
    expect(
      screen.getByText('Show this screen to the shop. The shop completes the payment on Paytm.'),
    ).toBeTruthy();
    const plan = within(screen.getByRole('region', { name: 'Your plan' }));
    expect(plan.getByText('₹3,667')).toBeTruthy();
    expect(plan.getByText('Example phone, 128 GB')).toBeTruthy();
    expect(plan.getByText('EMI-2611-0042')).toBeTruthy();
    expect(screen.getByText(/You can cancel within the cooling-off period\./)).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Back' })).toBeNull();
    expect(screen.getByRole('button', { name: 'Check status' })).toBeTruthy();
    await expectNoAccessibilityViolations(container);
  });

  it('polls while ready or pending and stops once paid', async () => {
    const customerFlowApi = await fixtureWithConsent(['READY_TO_PAY', 'PAYMENT_PENDING', 'PAID']);
    const getReceipt = vi.spyOn(customerFlowApi, 'getReceipt');
    vi.useFakeTimers({ shouldAdvanceTime: true });
    renderCustomerFlow({ customerFlowApi, initialFlowState: RECEIPT_STEP });
    expect(await screen.findByRole('heading', { name: 'Your plan is ready' })).toBeTruthy();

    await vi.advanceTimersByTimeAsync(RECEIPT_POLL_INTERVAL_IN_MILLISECONDS);
    expect(await screen.findByRole('heading', { name: 'Waiting for confirmation' })).toBeTruthy();
    expect(screen.getByText('This can take a few minutes. Please do not pay again.')).toBeTruthy();
    await vi.advanceTimersByTimeAsync(RECEIPT_POLL_INTERVAL_IN_MILLISECONDS);
    expect(await screen.findByRole('heading', { name: 'Your EMI is confirmed' })).toBeTruthy();
    expect(screen.getByText('You pay ₹3,667 a month for 6 months.')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Check status' })).toBeNull();
    const readsWhenPaid = getReceipt.mock.calls.length;
    await vi.advanceTimersByTimeAsync(RECEIPT_POLL_INTERVAL_IN_MILLISECONDS * 3);

    expect(getReceipt.mock.calls.length).toBe(readsWhenPaid);
  });

  it('explains a payment that did not finish without saying "declined", and checks again on request', async () => {
    const customerFlowApi = await fixtureWithConsent(['PAYMENT_NOT_COMPLETED', 'PAID']);
    const { container } = renderCustomerFlow({ customerFlowApi, initialFlowState: RECEIPT_STEP });

    expect(await screen.findByRole('heading', { name: 'Payment not completed' })).toBeTruthy();
    expect(document.body.textContent).not.toMatch(/declin|reject|fail/i);
    await expectNoAccessibilityViolations(container);
    await userEvent.click(screen.getByRole('button', { name: 'Check status' }));

    expect(await screen.findByRole('heading', { name: 'Your EMI is confirmed' })).toBeTruthy();
  });

  it('keeps the chosen language on the receipt', async () => {
    window.localStorage.setItem('emiCopilot.language', 'ta');
    const customerFlowApi = await fixtureWithConsent(['PAID']);

    renderCustomerFlow({ customerFlowApi, initialFlowState: RECEIPT_STEP });

    expect(await screen.findByRole('heading', { name: 'உங்கள் EMI உறுதியானது' })).toBeTruthy();
    expect(screen.getByText('6 மாதங்களுக்கு மாதம் ₹3,667 செலுத்துவீர்கள்.')).toBeTruthy();
    expect(screen.getByText('குறிப்பு எண்')).toBeTruthy();
  });

  it('shows a skeleton while loading and a calm retry on error', async () => {
    const customerFlowApi = await fixtureWithConsent(['READY_TO_PAY']);
    vi.spyOn(customerFlowApi, 'getReceipt')
      .mockRejectedValueOnce(new CustomerApiError(0, 'NETWORK_UNAVAILABLE'))
      .mockReturnValueOnce(new Promise(() => undefined));
    renderCustomerFlow({ customerFlowApi, initialFlowState: RECEIPT_STEP });

    expect((await screen.findByRole('alert')).textContent).toContain(
      'Your phone could not reach us.',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));

    expect(await screen.findByRole('status', { name: 'Getting your receipt' })).toBeTruthy();
  });
});
