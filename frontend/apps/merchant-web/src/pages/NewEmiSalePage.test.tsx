import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it } from 'vitest';

import { expectNoAccessibilityViolations } from '@test-support/accessibility';

import { createControllableEventStream } from '../testing/controllableEventStream';
import { TEST_PRODUCTS } from '../testing/counterSaleTestData';
import { jsonResponse, problemResponse, type FakeRoutes } from '../testing/fakeMerchantBackend';
import {
  buildTestSaleDetail,
  buildTestSaleSummary,
  TEST_NO_COST_PLAN,
} from '../testing/merchantTestData';
import { renderMerchantApp } from '../testing/renderMerchantApp';

const COUNTER_SALES = [
  buildTestSaleSummary({
    saleId: 'sale-4817',
    sessionCode: '4817',
    productName: 'Example phone, 64 GB',
    status: 'READY_TO_PAY',
    chosenPlan: TEST_NO_COST_PLAN,
  }),
  buildTestSaleSummary({ saleId: 'sale-4821', sessionCode: '4821', status: 'CHOOSING' }),
  buildTestSaleSummary({
    saleId: 'sale-4812',
    sessionCode: '4812',
    productName: 'Example earbuds',
    status: 'PAID',
    statusChangedAt: '2026-11-15T10:10:00Z',
  }),
  buildTestSaleSummary({
    saleId: 'sale-4809',
    sessionCode: '4809',
    status: 'PAYMENT_NOT_COMPLETED',
    chosenPlan: TEST_NO_COST_PLAN,
  }),
];

// Renders M2 with the design catalogue and counter list unless a test replaces a route.
function renderNewEmiSale(routes: FakeRoutes = {}) {
  return renderMerchantApp({
    path: '/sale',
    routes: {
      'GET /api/v1/products': ({ searchParameters }) => {
        const search = (searchParameters.get('search') ?? '').toLowerCase();
        return jsonResponse({
          products: TEST_PRODUCTS.filter((product) => product.name.toLowerCase().includes(search)),
        });
      },
      'GET /api/v1/sales': () => jsonResponse({ sales: COUNTER_SALES }),
      ...routes,
    },
  });
}

afterEach(() => {
  window.localStorage.clear();
});

describe('M2 new EMI sale', () => {
  it('lists products with their offer summary and list price, nothing chosen yet', async () => {
    renderNewEmiSale();

    expect(screen.getByRole('status', { name: 'Loading products…' })).toBeTruthy();
    const productRadio = await screen.findByRole('radio', { name: /Example phone, 128 GB/ });
    expect(productRadio.closest('label')?.textContent).toContain(
      '3 EMI plans, 1 with no extra cost',
    );
    expect(productRadio.closest('label')?.textContent).toContain('₹22,000');
    expect(
      screen.getByRole('radio', { name: /Example earbuds/ }).closest('label')?.textContent,
    ).toContain('1 EMI plan₹2,499');
    expect(screen.getByText('Pick a product to see its price.')).toBeTruthy();
    expect(
      screen.getByRole<HTMLButtonElement>('button', { name: 'Show QR to customer' }).disabled,
    ).toBe(true);
    expect(screen.queryByRole('button', { name: /Scan barcode/ })).toBeNull();
  });

  it('shows the read-only list price at the counter once a product is chosen', async () => {
    renderNewEmiSale();

    await userEvent.click(await screen.findByRole('radio', { name: /Example phone, 64 GB/ }));

    const priceInput = screen.getByLabelText<HTMLInputElement>(
      'Price at counter for Example phone, 64 GB',
    );
    expect(priceInput.value).toBe('₹18,000');
    expect(priceInput.readOnly).toBe(true);
    expect(
      screen.getByRole<HTMLButtonElement>('button', { name: 'Show QR to customer' }).disabled,
    ).toBe(false);
  });

  it('searches the catalogue and says calmly when nothing matches', async () => {
    const { fakeBackend } = renderNewEmiSale();
    await screen.findByRole('radio', { name: /Example earbuds/ });

    await userEvent.type(screen.getByRole('searchbox', { name: 'Search product' }), 'tablet');

    expect(await screen.findByText('No products match “tablet”.')).toBeTruthy();
    expect(
      fakeBackend.recordedRequests.some(
        (request) => request.path === '/api/v1/products?search=tablet',
      ),
    ).toBe(true);
  });

  it('says when the shop has no products at all', async () => {
    renderNewEmiSale({ 'GET /api/v1/products': () => jsonResponse({ products: [] }) });

    expect(await screen.findByText('No products in your list yet.')).toBeTruthy();
  });

  it('offers a retry when the products do not load', async () => {
    let shouldFail = true;
    renderNewEmiSale({
      'GET /api/v1/products': () =>
        shouldFail
          ? problemResponse(500, 'INTERNAL_SERVER_ERROR')
          : jsonResponse({ products: TEST_PRODUCTS }),
    });

    expect(await screen.findByText('Something did not load. Please try again.')).toBeTruthy();
    shouldFail = false;
    await userEvent.click(screen.getAllByRole('button', { name: 'Try again' })[0] ?? document.body);

    expect(await screen.findByRole('radio', { name: /Example phone, 128 GB/ })).toBeTruthy();
  });

  it('starts the sale with one Idempotency-Key per intent, re-sent on retry, and keeps the QR in memory', async () => {
    let startAttemptCount = 0;
    const { fakeBackend, queryClient } = renderNewEmiSale({
      'POST /api/v1/sales': () => {
        startAttemptCount += 1;
        if (startAttemptCount === 1) return problemResponse(500, 'INTERNAL_SERVER_ERROR');
        return jsonResponse(
          buildTestSaleDetail({
            saleId: 'sale-new',
            qr: {
              customerUrl: 'http://localhost:5174/#t=signed',
              expiresAt: '2026-11-15T10:25:00Z',
            },
          }),
          201,
        );
      },
    });
    await userEvent.click(await screen.findByRole('radio', { name: /Example phone, 128 GB/ }));

    await userEvent.click(screen.getByRole('button', { name: 'Show QR to customer' }));
    expect(await screen.findByRole('alert')).toBeTruthy();
    await userEvent.click(screen.getByRole('button', { name: 'Show QR to customer' }));

    await waitFor(() => {
      expect(queryClient.getQueryData(['customer-qr', 'sale-new'])).toEqual({
        customerUrl: 'http://localhost:5174/#t=signed',
        expiresAt: '2026-11-15T10:25:00Z',
      });
    });
    const startRequests = fakeBackend.recordedRequests.filter(
      (request) => request.method === 'POST' && request.path === '/api/v1/sales',
    );
    expect(startRequests.map((request) => request.body)).toEqual([
      { productId: 'product-128' },
      { productId: 'product-128' },
    ]);
    const idempotencyKeys = startRequests.map((request) => request.headers.get('Idempotency-Key'));
    expect(idempotencyKeys[0]).toMatch(/^[0-9a-f-]{36}$/);
    expect(idempotencyKeys[1]).toBe(idempotencyKeys[0]);
    expect(
      queryClient.getQueryData<{ qr: unknown }>(['sale', 'sale-new', 'detail'])?.qr,
    ).toBeNull();
  });

  it('explains calmly when every session code is in use', async () => {
    renderNewEmiSale({
      'POST /api/v1/sales': () => problemResponse(409, 'SESSION_CODES_EXHAUSTED'),
    });
    await userEvent.click(await screen.findByRole('radio', { name: /Example earbuds/ }));

    await userEvent.click(screen.getByRole('button', { name: 'Show QR to customer' }));

    expect(
      await screen.findByText(
        'Many customers are open at the counter right now. Finish one, then try again.',
      ),
    ).toBeTruthy();
  });
});

describe('M2 at the counter now', () => {
  it('shows each customer with code, status and the next step', async () => {
    renderNewEmiSale();

    const counterList = await screen.findByRole('region', { name: 'At the counter now' });
    await within(counterList).findByText('4 customers');
    const rows = within(counterList).getAllByRole('listitem');
    expect(rows[0]?.textContent).toContain('Code 4817');
    expect(within(rows[0] ?? counterList).getByText('Ready to pay')).toBeTruthy();
    expect(
      within(counterList)
        .getByRole('link', { name: 'Take payment, code 4817' })
        .getAttribute('href'),
    ).toBe('/sale/sale-4817/handoff');
    expect(within(rows[1] ?? counterList).getByText('Choosing on their phone')).toBeTruthy();
    expect(
      within(counterList).getByRole('link', { name: 'Show QR, code 4821' }).getAttribute('href'),
    ).toBe('/sale/sale-4821/qr');
    expect(within(rows[2] ?? counterList).getByText('Paid at 3:40 pm')).toBeTruthy();
    expect(within(rows[2] ?? counterList).queryByRole('link')).toBeNull();
    expect(within(counterList).getByRole('link', { name: 'Take payment, code 4809' })).toBeTruthy();
    expect(
      within(counterList).getByText(
        'You see only what the customer chose. Their income and EMIs stay on their phone.',
      ),
    ).toBeTruthy();
  });

  it('says when nobody is at the counter yet', async () => {
    renderNewEmiSale({ 'GET /api/v1/sales': () => jsonResponse({ sales: [] }) });
    expect(
      await screen.findByText(
        'No customers at the counter yet. Start a new EMI sale when someone asks about EMI.',
      ),
    ).toBeTruthy();
    expect(screen.getByText('0 customers')).toBeTruthy();
  });

  it('shows a calm error when the counter list does not load', async () => {
    renderNewEmiSale({ 'GET /api/v1/sales': () => problemResponse(503, 'SERVICE_UNAVAILABLE') });

    const counterList = await screen.findByRole('region', { name: 'At the counter now' });
    expect(
      await within(counterList).findByText('Something did not load. Please try again.'),
    ).toBeTruthy();
    expect(within(counterList).getByRole('button', { name: 'Try again' })).toBeTruthy();
  });

  it('updates a row live when the stream says the customer agreed, without a reload', async () => {
    const eventStream = createControllableEventStream();
    let counterSales = [buildTestSaleSummary({ status: 'CHOOSING' })];
    renderNewEmiSale({
      'GET /api/v1/sales': () => jsonResponse({ sales: counterSales }),
      'GET /api/v1/sales/events': () => eventStream.createResponse(),
    });
    await screen.findByText('Choosing on their phone');

    counterSales = [
      buildTestSaleSummary({ status: 'READY_TO_PAY', chosenPlan: TEST_NO_COST_PLAN }),
    ];
    eventStream.send(
      'event: sale-status\ndata: {"saleId":"sale-4821","status":"READY_TO_PAY","statusChangedAt":"2026-11-15T10:12:00Z"}\n\n',
    );

    expect(await screen.findByRole('link', { name: 'Take payment, code 4821' })).toBeTruthy();
  });

  it('shows M2 in Tamil', async () => {
    renderNewEmiSale();
    await screen.findByRole('radio', { name: /Example phone, 128 GB/ });

    await userEvent.click(screen.getByRole('button', { name: 'தமிழ்' }));

    expect(screen.getByRole('heading', { level: 1, name: 'புதிய EMI விற்பனை' })).toBeTruthy();
    expect(screen.getByText('3 EMI திட்டங்கள், 1 கூடுதல் செலவு இல்லாமல்')).toBeTruthy();
  });

  it('has no accessibility violations with a product chosen and the list loaded', async () => {
    const { container } = renderNewEmiSale();
    await userEvent.click(await screen.findByRole('radio', { name: /Example phone, 128 GB/ }));
    await screen.findByText('4 customers');

    await expectNoAccessibilityViolations(container);
  });
});
