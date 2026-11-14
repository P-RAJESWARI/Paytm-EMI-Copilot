import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it } from 'vitest';

import { TEST_PRODUCTS } from '../testing/counterSaleTestData';
import { jsonResponse } from '../testing/fakeMerchantBackend';
import {
  buildTestSaleDetail,
  buildTestSaleHandoff,
  buildTestSaleSummary,
  TEST_CARD_PLAN,
  TEST_NO_COST_PLAN,
} from '../testing/merchantTestData';
import { renderMerchantApp } from '../testing/renderMerchantApp';

/** Words that would reveal a customer's finances, comfort check or progress (rule 6), in English and Tamil. */
const CUSTOMER_PRIVATE_WORDS =
  /income|EMIs you already pay|existing EMI|comfort|ratio|basis point|Comfortable|Stretching|Risky|budget|approved|declined|rejected|eligible|scanned|step|வருமான|வசதியானது|சிரமம்|அதிக சுமை|பட்ஜெட்/i;

const ROUTES = {
  'GET /api/v1/products': () => jsonResponse({ products: TEST_PRODUCTS }),
  'GET /api/v1/sales': () =>
    jsonResponse({
      sales: [
        buildTestSaleSummary({
          saleId: 'sale-1',
          status: 'READY_TO_PAY',
          chosenPlan: TEST_CARD_PLAN,
        }),
        buildTestSaleSummary({ saleId: 'sale-2', sessionCode: '4822', status: 'CHOOSING' }),
        buildTestSaleSummary({ saleId: 'sale-3', sessionCode: '4823', status: 'PAID' }),
      ],
    }),
  'GET /api/v1/sales/{saleId}': () =>
    jsonResponse(buildTestSaleDetail({ status: 'READY_TO_PAY', chosenPlan: TEST_NO_COST_PLAN })),
  'GET /api/v1/sales/{saleId}/handoff': () => jsonResponse(buildTestSaleHandoff()),
};

// Gives the visible text of the page without the one note that reassures about privacy.
function readScreenTextWithoutPrivacyNote(): string {
  const pageCopy = document.body.cloneNode(true) as HTMLElement;
  pageCopy.querySelectorAll('[data-privacy-note]').forEach((privacyNote) => {
    privacyNote.remove();
  });
  return pageCopy.textContent;
}

afterEach(() => {
  window.localStorage.clear();
});

describe('merchant screens show no customer finances or progress', () => {
  it.each([
    ['M2 new EMI sale', '/sale', 'Take payment, code 4821'],
    ['M3 show QR', '/sale/sale-1/qr', 'Take payment'],
    ['M4 take payment', '/sale/sale-1/handoff', 'Refresh status'],
  ])('%s, in English and Tamil', async (_screenName, path, readyControlName) => {
    renderMerchantApp({ path, routes: ROUTES });
    await screen.findAllByRole(path === '/sale/sale-1/handoff' ? 'button' : 'link', {
      name: readyControlName,
    });
    expect(readScreenTextWithoutPrivacyNote()).not.toMatch(CUSTOMER_PRIVATE_WORDS);

    await userEvent.click(screen.getByRole('button', { name: 'தமிழ்' }));

    expect(readScreenTextWithoutPrivacyNote()).not.toMatch(CUSTOMER_PRIVATE_WORDS);
  });
});
