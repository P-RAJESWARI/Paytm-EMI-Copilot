import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it } from 'vitest';

import { expectNoAccessibilityViolations } from '@test-support/accessibility';

import { createControllableEventStream } from '../testing/controllableEventStream';
import { TEST_PRODUCTS } from '../testing/counterSaleTestData';
import { jsonResponse, problemResponse, type FakeRoutes } from '../testing/fakeMerchantBackend';
import {
  buildTestSaleDetail,
  TEST_CARD_PLAN,
  TEST_NO_COST_PLAN,
} from '../testing/merchantTestData';
import { renderMerchantApp } from '../testing/renderMerchantApp';

const FUTURE_EXPIRY = '2099-11-15T10:25:00Z';
const PAST_EXPIRY = '2020-11-15T10:25:00Z';

// Renders M3 for sale-4821, answering GET /sales/{saleId} with the given sale.
function renderShowQr(sale = buildTestSaleDetail(), routes: FakeRoutes = {}) {
  return renderMerchantApp({
    path: '/sale/sale-4821/qr',
    routes: {
      'GET /api/v1/sales/{saleId}': () => jsonResponse(sale),
      'POST /api/v1/sales/{saleId}/qr-tokens': () =>
        jsonResponse(
          { customerUrl: 'http://localhost:5174/#t=fresh', expiresAt: FUTURE_EXPIRY },
          201,
        ),
      ...routes,
    },
  });
}

// Counts the QR codes issued so far.
function countQrIssues(recordedRequests: { method: string; path: string }[]): number {
  return recordedRequests.filter(
    (request) => request.method === 'POST' && request.path.endsWith('/qr-tokens'),
  ).length;
}

afterEach(() => {
  window.localStorage.clear();
});

describe('M3 show QR to customer', () => {
  it('opens from "Show QR to customer" with the QR from the start answer, issuing no other', async () => {
    const { fakeBackend, router } = renderMerchantApp({
      path: '/sale',
      routes: {
        'GET /api/v1/products': () => jsonResponse({ products: TEST_PRODUCTS }),
        'GET /api/v1/sales': () => jsonResponse({ sales: [] }),
        'POST /api/v1/sales': () =>
          jsonResponse(
            buildTestSaleDetail({
              qr: { customerUrl: 'http://localhost:5174/#t=start', expiresAt: FUTURE_EXPIRY },
            }),
            201,
          ),
        'GET /api/v1/sales/{saleId}': () => jsonResponse(buildTestSaleDetail()),
      },
    });
    await userEvent.click(await screen.findByRole('radio', { name: /Example phone, 128 GB/ }));

    await userEvent.click(screen.getByRole('button', { name: 'Show QR to customer' }));

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Show this QR to the customer' }),
    ).toBeTruthy();
    expect(router.state.location.pathname).toBe('/sale/sale-4821/qr');
    expect(screen.getByRole('img', { name: 'Session QR code 4821' })).toBeTruthy();
    expect(screen.getByText('Opens on their phone. No app needed.')).toBeTruthy();
    expect(screen.getByText('Example phone, 128 GB, ₹22,000. Code 4821.')).toBeTruthy();
    expect(countQrIssues(fakeBackend.recordedRequests)).toBe(0);
  });

  it('issues a QR once when opened from the counter list and starts at "Choosing"', async () => {
    const { fakeBackend } = renderShowQr();

    expect(await screen.findByRole('img', { name: 'Session QR code 4821' })).toBeTruthy();
    expect(
      screen.getByRole('heading', {
        level: 2,
        name: 'The customer is choosing a plan on their phone',
      }),
    ).toBeTruthy();
    expect(screen.getByText('Nothing for you to do yet. Let them take their time.')).toBeTruthy();
    expect(screen.getByText(/You can serve other customers meanwhile/)).toBeTruthy();
    expect(screen.queryByText(/Not scanned yet/)).toBeNull();
    expect(countQrIssues(fakeBackend.recordedRequests)).toBe(1);
  });

  it('shows the agreed plan with monthly, extra in total and total, and "Take payment"', async () => {
    const { fakeBackend } = renderShowQr(
      buildTestSaleDetail({ status: 'READY_TO_PAY', chosenPlan: TEST_NO_COST_PLAN }),
    );

    const statusCard = await screen.findByRole('region', { name: 'The customer agreed to a plan' });
    expect(within(statusCard).getByText('Ready to pay')).toBeTruthy();
    expect(within(statusCard).getByText('No-cost EMI, 6 months')).toBeTruthy();
    expect(within(statusCard).getByText('Each month').nextSibling?.textContent).toBe('₹3,667');
    expect(within(statusCard).getByText('Extra in total').nextSibling?.textContent).toBe('₹0');
    expect(within(statusCard).getByText('Total').nextSibling?.textContent).toBe('₹22,000');
    expect(
      within(statusCard).getByRole('link', { name: 'Take payment' }).getAttribute('href'),
    ).toBe('/sale/sale-4821/handoff');
    expect(screen.getByText('This sale no longer needs a QR code.')).toBeTruthy();
    expect(countQrIssues(fakeBackend.recordedRequests)).toBe(0);
  });

  it('shows a card plan with its extra cost and total exactly as the API sends them', async () => {
    renderShowQr(
      buildTestSaleDetail({ status: 'PAYMENT_NOT_COMPLETED', chosenPlan: TEST_CARD_PLAN }),
    );

    const statusCard = await screen.findByRole('region', { name: 'The payment was not completed' });
    expect(within(statusCard).getByText('EMI, 6 months')).toBeTruthy();
    expect(within(statusCard).getByText('₹3,850')).toBeTruthy();
    expect(within(statusCard).getByText('₹1,100')).toBeTruthy();
    expect(within(statusCard).getByText('₹23,100')).toBeTruthy();
  });

  it('turns "Choosing" into "Ready to pay" live, without issuing another QR', async () => {
    const eventStream = createControllableEventStream();
    let sale = buildTestSaleDetail();
    const { fakeBackend } = renderShowQr(undefined, {
      'GET /api/v1/sales/{saleId}': () => jsonResponse(sale),
      'GET /api/v1/sales/events': () => eventStream.createResponse(),
    });
    await screen.findByRole('img', { name: 'Session QR code 4821' });

    sale = buildTestSaleDetail({ status: 'READY_TO_PAY', chosenPlan: TEST_NO_COST_PLAN });
    eventStream.send(
      'event: sale-status\ndata: {"saleId":"sale-4821","status":"READY_TO_PAY","statusChangedAt":"2026-11-15T10:12:00Z"}\n\n',
    );

    expect(await screen.findByRole('link', { name: 'Take payment' })).toBeTruthy();
    expect(countQrIssues(fakeBackend.recordedRequests)).toBe(1);
  });

  it('offers a new QR once the old one expires while the customer is still choosing', async () => {
    let issuedCount = 0;
    renderShowQr(undefined, {
      'POST /api/v1/sales/{saleId}/qr-tokens': () => {
        issuedCount += 1;
        return jsonResponse(
          {
            customerUrl: `http://localhost:5174/#t=${issuedCount}`,
            expiresAt: issuedCount === 1 ? PAST_EXPIRY : FUTURE_EXPIRY,
          },
          201,
        );
      },
    });

    expect(
      await screen.findByText(
        'This QR code has expired. Show a new one if the customer still needs to scan.',
      ),
    ).toBeTruthy();
    await userEvent.click(screen.getByRole('button', { name: 'Show a new QR' }));

    expect(await screen.findByRole('img', { name: 'Session QR code 4821' })).toBeTruthy();
    expect(issuedCount).toBe(2);
  });

  it('explains calmly when a QR cannot be issued and lets the merchant try again', async () => {
    let shouldFail = true;
    renderShowQr(undefined, {
      'POST /api/v1/sales/{saleId}/qr-tokens': () =>
        shouldFail
          ? problemResponse(409, 'SALE_STATE_CONFLICT')
          : jsonResponse(
              { customerUrl: 'http://localhost:5174/#t=x', expiresAt: FUTURE_EXPIRY },
              201,
            ),
    });

    expect(
      await screen.findByText('This sale has moved on. The latest status is shown.'),
    ).toBeTruthy();
    shouldFail = false;
    await userEvent.click(screen.getByRole('button', { name: 'Show a new QR' }));

    expect(await screen.findByRole('img', { name: 'Session QR code 4821' })).toBeTruthy();
  });

  it('says calmly when the session ended or the sale is paid, with a way back', async () => {
    renderShowQr(buildTestSaleDetail({ status: 'EXPIRED' }));

    expect(
      await screen.findByRole('heading', { level: 2, name: 'This session has ended' }),
    ).toBeTruthy();
    expect(screen.getAllByRole('link', { name: 'Back to counter list' }).length).toBe(2);
  });

  it('shows the paid state', async () => {
    renderShowQr(buildTestSaleDetail({ status: 'PAID', chosenPlan: TEST_NO_COST_PLAN }));

    expect(
      await screen.findByText('The payment is confirmed. You can hand over the product.'),
    ).toBeTruthy();
    expect(screen.queryByRole('link', { name: 'Take payment' })).toBeNull();
  });

  it('shows the loading state, then a calm message for a sale that is not found', async () => {
    renderShowQr(undefined, {
      'GET /api/v1/sales/{saleId}': () => problemResponse(404, 'SALE_NOT_FOUND'),
    });

    expect(screen.getByRole('status', { name: 'Loading the sale…' })).toBeTruthy();
    expect(
      await screen.findByText('We could not find this sale. Go back to the counter list.'),
    ).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Back to counter list' }).getAttribute('href')).toBe(
      '/sale',
    );
  });

  it('shows M3 in Tamil', async () => {
    renderShowQr(buildTestSaleDetail({ status: 'READY_TO_PAY', chosenPlan: TEST_NO_COST_PLAN }));
    await screen.findByText('No-cost EMI, 6 months');

    await userEvent.click(screen.getByRole('button', { name: 'தமிழ்' }));

    expect(
      screen.getByRole('heading', { level: 1, name: 'இந்த QR-ஐ வாடிக்கையாளருக்குக் காட்டுங்கள்' }),
    ).toBeTruthy();
    expect(screen.getByText('கட்டணமில்லா EMI, 6 மாதங்கள்')).toBeTruthy();
  });

  it('has no accessibility violations while choosing and once ready to pay', async () => {
    const { container, unmount } = renderShowQr();
    await screen.findByRole('img', { name: 'Session QR code 4821' });
    await expectNoAccessibilityViolations(container);
    unmount();

    const readyRender = renderShowQr(
      buildTestSaleDetail({ status: 'READY_TO_PAY', chosenPlan: TEST_NO_COST_PLAN }),
    );
    await screen.findByRole('link', { name: 'Take payment' });
    await expectNoAccessibilityViolations(readyRender.container);
  });
});
