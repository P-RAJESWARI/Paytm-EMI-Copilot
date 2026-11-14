import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { expectNoAccessibilityViolations } from '@test-support/accessibility';

import { createControllableEventStream } from '../testing/controllableEventStream';
import {
  bodylessErrorResponse,
  jsonResponse,
  networkFailure,
  problemResponse,
  type FakeRoutes,
  type RecordedRequest,
} from '../testing/fakeMerchantBackend';
import {
  buildTestSaleHandoff,
  buildTestSaleSummary,
  TEST_CARD_PLAN,
} from '../testing/merchantTestData';
import { renderMerchantApp } from '../testing/renderMerchantApp';
import { stubClipboard } from '../testing/stubClipboard';

const PAYMENT_URL = 'https://mock-payments.invalid/pay/mock-link-0123';
const OPEN_LINK = {
  orderId: 'order-1',
  paymentUrl: PAYMENT_URL,
  status: 'AWAITING_PAYMENT' as const,
};
const CREATED_LINK = {
  orderId: 'order-1',
  paymentUrl: PAYMENT_URL,
  amountInPaise: 2200000,
  status: 'AWAITING_PAYMENT' as const,
};

// Renders M4 for sale-4821 with the given hand-off answer.
function renderTakePayment(routes: FakeRoutes = {}) {
  return renderMerchantApp({
    path: '/sale/sale-4821/handoff',
    routes: {
      'GET /api/v1/sales/{saleId}/handoff': () => jsonResponse(buildTestSaleHandoff()),
      ...routes,
    },
  });
}

// The Idempotency-Key of every payment-link request, in order.
function linkRequestKeys(recordedRequests: RecordedRequest[]): (string | null)[] {
  return recordedRequests
    .filter((request) => request.method === 'POST' && request.path.endsWith('/payment-links'))
    .map((request) => request.headers.get('Idempotency-Key'));
}

// Gives the hand-off answer with the link once one was made.
function handoffWithLinkAfterCreation() {
  let hasLink = false;
  return {
    markLinkCreated: () => {
      hasLink = true;
    },
    handoffRoute: () =>
      jsonResponse(buildTestSaleHandoff({ latestPaymentLink: hasLink ? OPEN_LINK : null })),
  };
}

afterEach(() => {
  window.localStorage.clear();
});

describe('M4 take payment', () => {
  it('shows the agreed plan with extra in total and total, the EDC steps and the waiting state', async () => {
    renderTakePayment();

    const planGrid = await screen.findByLabelText('Chosen plan details');
    const valueFor = (label: string) => within(planGrid).getByText(label).nextSibling?.textContent;
    expect(valueFor('Chosen plan')).toBe('No-cost EMI, 6 months');
    expect(valueFor('Product')).toBe('Example phone, 128 GB');
    expect(valueFor('Price')).toBe('₹22,000');
    expect(valueFor('Each month')).toBe('₹3,667');
    expect(valueFor('Extra in total')).toBe('₹0');
    expect(valueFor('Total')).toBe('₹22,000');
    expect(valueFor('Funded by')).toBe('Brand');
    const edcSteps = within(
      screen.getByRole('region', { name: 'On the EDC machine' }),
    ).getAllByRole('listitem');
    expect(edcSteps.map((step) => step.textContent)).toEqual([
      'Choose Brand EMI.',
      'Pick Example phone, 128 GB and 6 months, no-cost.',
      'Check the amount is ₹22,000, then hand it to the customer.',
    ]);
    expect(screen.getByRole('heading', { level: 2, name: 'Waiting for payment' })).toBeTruthy();
    expect(
      screen.getByText(
        'This updates when the server confirms the payment. Don’t hand over the product yet.',
      ),
    ).toBeTruthy();
    expect(screen.queryByRole('button', { name: /mark|paid/i })).toBeNull();
  });

  it('shows the bank EMI steps and a card plan exactly as the API sends them', async () => {
    renderTakePayment({
      'GET /api/v1/sales/{saleId}/handoff': () =>
        jsonResponse(
          buildTestSaleHandoff({
            sale: buildTestSaleSummary({ status: 'READY_TO_PAY', chosenPlan: TEST_CARD_PLAN }),
            edcInstructions: {
              emiProgramme: 'BANK_EMI',
              productName: 'Example phone, 128 GB',
              tenureInMonths: 6,
              isNoExtraCost: false,
              amountInPaise: 2200000,
            },
          }),
        ),
    });

    const edcRegion = await screen.findByRole('region', { name: 'On the EDC machine' });
    const edcSteps = within(edcRegion)
      .getAllByRole('listitem')
      .map((step) => step.textContent);
    expect(edcSteps.slice(0, 2)).toEqual([
      'Choose Bank EMI.',
      'Pick Example phone, 128 GB and 6 months.',
    ]);
    expect(screen.getByText('₹1,100')).toBeTruthy();
    expect(screen.getByText('₹23,100')).toBeTruthy();
    expect(screen.getByText("Your card's bank")).toBeTruthy();
  });

  it('makes a payment link, shows it as a QR code and copies it', async () => {
    const writeText = vi.fn(() => Promise.resolve());
    stubClipboard({ writeText });
    const linkState = handoffWithLinkAfterCreation();
    const { fakeBackend } = renderTakePayment({
      'GET /api/v1/sales/{saleId}/handoff': linkState.handoffRoute,
      'POST /api/v1/sales/{saleId}/payment-links': () => {
        linkState.markLinkCreated();
        return jsonResponse(CREATED_LINK, 201);
      },
    });

    await userEvent.click(await screen.findByRole('button', { name: 'Send payment link' }));

    expect(await screen.findByRole('img', { name: 'Payment link QR code' })).toBeTruthy();
    expect(screen.getByLabelText<HTMLInputElement>('Link to copy').value).toBe(PAYMENT_URL);
    expect(
      screen.getByText(
        'The customer scans this to pay on Paytm. Nothing is sent from this tablet.',
      ),
    ).toBeTruthy();
    expect(
      screen.getByRole<HTMLButtonElement>('button', { name: 'Send payment link' }).disabled,
    ).toBe(true);
    await userEvent.click(screen.getByRole('button', { name: 'Copy link' }));
    expect(writeText).toHaveBeenCalledWith(PAYMENT_URL);
    expect(await screen.findByText('Copied')).toBeTruthy();
    expect(linkRequestKeys(fakeBackend.recordedRequests)[0]).toMatch(/^[0-9a-f-]{36}$/);
  });

  it('says how to copy by hand when this device cannot copy', async () => {
    stubClipboard(undefined);
    renderTakePayment({
      'GET /api/v1/sales/{saleId}/handoff': () =>
        jsonResponse(buildTestSaleHandoff({ latestPaymentLink: OPEN_LINK })),
    });

    await userEvent.click(await screen.findByRole('button', { name: 'Copy link' }));

    expect(
      await screen.findByText(
        'Copying is not available on this device. Select the link above and copy it.',
      ),
    ).toBeTruthy();
  });

  it('says how to copy by hand when the browser refuses to copy', async () => {
    stubClipboard({
      writeText: () => Promise.reject(new DOMException('Denied', 'NotAllowedError')),
    });
    renderTakePayment({
      'GET /api/v1/sales/{saleId}/handoff': () =>
        jsonResponse(buildTestSaleHandoff({ latestPaymentLink: OPEN_LINK })),
    });

    await userEvent.click(await screen.findByRole('button', { name: 'Copy link' }));

    expect(await screen.findByText(/Copying is not available on this device/)).toBeTruthy();
  });

  it.each([
    [
      'a lost answer',
      networkFailure,
      "Could not reach the server. Check the shop's internet connection and try again.",
    ],
    [
      'a server error with no problem body',
      () => bodylessErrorResponse(502),
      'Something did not load. Please try again.',
    ],
  ])(
    're-sends the same Idempotency-Key after %s, so no second link is made',
    async (_case, firstAnswer, message) => {
      let attemptCount = 0;
      const linkState = handoffWithLinkAfterCreation();
      const { fakeBackend } = renderTakePayment({
        'GET /api/v1/sales/{saleId}/handoff': linkState.handoffRoute,
        'POST /api/v1/sales/{saleId}/payment-links': () => {
          attemptCount += 1;
          if (attemptCount === 1) return firstAnswer();
          linkState.markLinkCreated();
          return jsonResponse(CREATED_LINK, 201);
        },
      });

      await userEvent.click(await screen.findByRole('button', { name: 'Send payment link' }));
      expect(await screen.findByText(message)).toBeTruthy();
      await userEvent.click(screen.getByRole('button', { name: 'Send payment link' }));

      expect(await screen.findByRole('img', { name: 'Payment link QR code' })).toBeTruthy();
      const [firstKey, secondKey] = linkRequestKeys(fakeBackend.recordedRequests);
      expect(secondKey).toBe(firstKey);
    },
  );

  it.each([
    [504, 'PAYMENT_GATEWAY_TIMEOUT'],
    [422, 'PAYMENT_LINK_CREATION_FAILED'],
    [409, 'PAYMENT_LINK_OUTCOME_UNKNOWN'],
    [409, 'PAYMENT_LINK_ALREADY_ACTIVE'],
  ])(
    'starts a new Idempotency-Key after a %i %s answer, so the next try is not a replay',
    async (status, problemCode) => {
      let attemptCount = 0;
      const linkState = handoffWithLinkAfterCreation();
      const { fakeBackend } = renderTakePayment({
        'GET /api/v1/sales/{saleId}/handoff': linkState.handoffRoute,
        'POST /api/v1/sales/{saleId}/payment-links': () => {
          attemptCount += 1;
          if (attemptCount === 1) return problemResponse(status, problemCode);
          linkState.markLinkCreated();
          return jsonResponse(CREATED_LINK, 201);
        },
      });

      await userEvent.click(await screen.findByRole('button', { name: 'Send payment link' }));
      expect(await screen.findByRole('alert')).toBeTruthy();
      await userEvent.click(screen.getByRole('button', { name: 'Send payment link' }));

      expect(await screen.findByRole('img', { name: 'Payment link QR code' })).toBeTruthy();
      const [firstKey, secondKey] = linkRequestKeys(fakeBackend.recordedRequests);
      expect(secondKey).toMatch(/^[0-9a-f-]{36}$/);
      expect(secondKey).not.toBe(firstKey);
    },
  );

  it.each([
    [
      'PAYMENT_LINK_ALREADY_ACTIVE',
      'A payment link for this sale is still open. Use that link, or wait for it to finish.',
    ],
    [
      'CHOSEN_PLAN_NO_LONGER_OFFERED',
      'This plan is no longer offered at this price. Ask the customer to choose again on their phone.',
    ],
    ['SALE_STATE_CONFLICT', 'This sale has moved on. The latest status is shown.'],
  ])('explains %s calmly and reads the hand-off again', async (problemCode, message) => {
    const { fakeBackend } = renderTakePayment({
      'POST /api/v1/sales/{saleId}/payment-links': () => problemResponse(409, problemCode),
    });

    await userEvent.click(await screen.findByRole('button', { name: 'Send payment link' }));

    expect(await screen.findByText(message)).toBeTruthy();
    await waitFor(() => {
      expect(
        fakeBackend.recordedRequests.filter((request) => request.path.endsWith('/handoff')).length,
      ).toBe(2);
    });
  });

  it('refreshes the status from the server and shows the confirmed payment', async () => {
    let isPaid = false;
    renderTakePayment({
      'GET /api/v1/sales/{saleId}/handoff': () =>
        jsonResponse(
          buildTestSaleHandoff(
            isPaid ? { paymentStatus: 'PAID', paymentConfirmedAt: '2026-11-15T10:42:00Z' } : {},
          ),
        ),
      'GET /api/v1/sales/{saleId}/payment-status': () => {
        isPaid = true;
        return jsonResponse({ paymentStatus: 'PAID', paymentConfirmedAt: '2026-11-15T10:42:00Z' });
      },
    });

    await userEvent.click(await screen.findByRole('button', { name: 'Refresh status' }));

    expect(await screen.findByRole('heading', { level: 2, name: 'Paid' })).toBeTruthy();
    expect(
      screen.getByText(
        'Confirmed by the server at 4:12 pm. ₹22,000 on no-cost EMI. You can hand over the product.',
      ),
    ).toBeTruthy();
    expect(screen.getAllByRole('link', { name: 'Back to counter list' }).length).toBe(2);
  });

  it('explains a failed status check calmly', async () => {
    renderTakePayment({
      'GET /api/v1/sales/{saleId}/payment-status': () => problemResponse(429, 'RATE_LIMITED'),
    });

    await userEvent.click(await screen.findByRole('button', { name: 'Refresh status' }));

    expect(
      await screen.findByText('Too many requests just now. Please wait a minute and try again.'),
    ).toBeTruthy();
  });

  it('turns to "Paid" live when the server confirms the payment', async () => {
    const eventStream = createControllableEventStream();
    let isPaid = false;
    renderTakePayment({
      'GET /api/v1/sales/{saleId}/handoff': () =>
        jsonResponse(
          buildTestSaleHandoff(isPaid ? { paymentStatus: 'PAID', paymentConfirmedAt: null } : {}),
        ),
      'GET /api/v1/sales/events': () => eventStream.createResponse(),
    });
    await screen.findByRole('heading', { level: 2, name: 'Waiting for payment' });

    isPaid = true;
    eventStream.send(
      'event: sale-status\ndata: {"saleId":"sale-4821","status":"PAID","statusChangedAt":"2026-11-15T10:42:00Z"}\n\n',
    );

    expect(
      await screen.findByText(
        'Confirmed by the server. ₹22,000 on no-cost EMI. You can hand over the product.',
      ),
    ).toBeTruthy();
  });

  it('never says "declined" and makes a new link with a new key on "Try again"', async () => {
    const { fakeBackend } = renderTakePayment({
      'GET /api/v1/sales/{saleId}/handoff': () =>
        jsonResponse(
          buildTestSaleHandoff({
            paymentStatus: 'NOT_COMPLETED',
            latestPaymentLink: { ...OPEN_LINK, status: 'PAYMENT_FAILED' },
          }),
        ),
      'POST /api/v1/sales/{saleId}/payment-links': () => jsonResponse(CREATED_LINK, 201),
    });

    expect(
      await screen.findByRole('heading', { level: 2, name: 'Payment not completed' }),
    ).toBeTruthy();
    expect(
      screen.getByText(
        'Nothing was confirmed. Ask the customer if they want to try again, or send a payment link.',
      ),
    ).toBeTruthy();
    expect(document.body.textContent).not.toMatch(/declined/i);
    expect(screen.queryByRole('img', { name: 'Payment link QR code' })).toBeNull();
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));

    await waitFor(() => {
      expect(linkRequestKeys(fakeBackend.recordedRequests).length).toBe(2);
    });
    const [firstKey, secondKey] = linkRequestKeys(fakeBackend.recordedRequests);
    expect(secondKey).not.toBe(firstKey);
  });

  it('shows the loading state, then says calmly when the customer has not agreed yet', async () => {
    renderTakePayment({
      'GET /api/v1/sales/{saleId}/handoff': () => problemResponse(409, 'SALE_STATE_CONFLICT'),
    });

    expect(screen.getByRole('status', { name: 'Loading the payment details…' })).toBeTruthy();
    expect(
      await screen.findByText(
        'This sale is not ready for payment yet. The customer is still choosing on their phone.',
      ),
    ).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Back to counter list' })).toBeTruthy();
  });

  it('shows a calm message when the hand-off does not load', async () => {
    renderTakePayment({
      'GET /api/v1/sales/{saleId}/handoff': () => problemResponse(404, 'SALE_NOT_FOUND'),
    });

    expect(
      await screen.findByText('We could not find this sale. Go back to the counter list.'),
    ).toBeTruthy();
  });

  it('shows M4 in Tamil', async () => {
    renderTakePayment();
    await screen.findByRole('heading', { level: 2, name: 'Waiting for payment' });

    await userEvent.click(screen.getByRole('button', { name: 'தமிழ்' }));

    expect(
      screen.getByRole('heading', { level: 1, name: 'Paytm-இல் பணம் பெறுங்கள்' }),
    ).toBeTruthy();
    expect(screen.getAllByRole('listitem')[0]?.textContent).toBe(
      'Brand EMI-ஐத் தேர்ந்தெடுக்கவும்.',
    );
  });

  it('has no accessibility violations with an open link and once paid', async () => {
    const { container, unmount } = renderTakePayment({
      'GET /api/v1/sales/{saleId}/handoff': () =>
        jsonResponse(buildTestSaleHandoff({ latestPaymentLink: OPEN_LINK })),
    });
    await screen.findByRole('img', { name: 'Payment link QR code' });
    await expectNoAccessibilityViolations(container);
    unmount();

    const paidRender = renderTakePayment({
      'GET /api/v1/sales/{saleId}/handoff': () =>
        jsonResponse(
          buildTestSaleHandoff({
            paymentStatus: 'PAID',
            paymentConfirmedAt: '2026-11-15T10:42:00Z',
          }),
        ),
    });
    await screen.findByRole('heading', { level: 2, name: 'Paid' });
    await expectNoAccessibilityViolations(paidRender.container);
  });
});
