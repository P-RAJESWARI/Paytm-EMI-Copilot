import type { ApiSchemas } from '@emi-copilot/api-client';

import type { MerchantSession } from '../shared/session/merchantSessionContext';

/** The DESIGN_SPEC section 4 shop. */
export const TEST_MERCHANT_PROFILE: ApiSchemas['MerchantProfileResponse'] = {
  merchantId: 'merchant-1',
  shopId: 'RAVI-0193',
  shopName: 'Ravi Electronics',
  deviceLabel: 'Counter tablet 1',
};

export const TEST_ACCESS_TOKEN = 'test-access-token';

export const TEST_MERCHANT_SESSION: MerchantSession = {
  accessToken: TEST_ACCESS_TOKEN,
  merchant: TEST_MERCHANT_PROFILE,
};

/** Plan A from DESIGN_SPEC section 4: no-cost, 6 months, ₹3,667 a month, ₹0 extra. */
export const TEST_NO_COST_PLAN: ApiSchemas['ChosenPlanResponse'] = {
  offerId: 'mock-offer-no-cost-6m',
  planKind: 'NO_COST',
  lenderLabel: 'Brand',
  tenureInMonths: 6,
  monthlyInstallmentInPaise: 366667,
  extraInTotalInPaise: 0,
  totalPayableInPaise: 2200000,
};

/** Plan B from DESIGN_SPEC section 4: card EMI, 6 months, ₹3,850 a month, ₹1,100 extra. */
export const TEST_CARD_PLAN: ApiSchemas['ChosenPlanResponse'] = {
  offerId: 'mock-offer-card-6m',
  planKind: 'STANDARD',
  lenderLabel: "Your card's bank",
  tenureInMonths: 6,
  monthlyInstallmentInPaise: 385000,
  extraInTotalInPaise: 110000,
  totalPayableInPaise: 2310000,
};

// Builds a counter-list sale with the design's 128 GB phone, overridable per test.
export function buildTestSaleSummary(
  overrides: Partial<ApiSchemas['SaleSummaryResponse']> = {},
): ApiSchemas['SaleSummaryResponse'] {
  return {
    saleId: 'sale-4821',
    sessionCode: '4821',
    productName: 'Example phone, 128 GB',
    priceInPaise: 2200000,
    status: 'CHOOSING',
    statusChangedAt: '2026-11-15T10:10:00Z',
    chosenPlan: null,
    ...overrides,
  };
}

// Builds a sale detail (GET /sales/{saleId}) from a summary, with no QR unless one is given.
export function buildTestSaleDetail(
  overrides: Partial<ApiSchemas['SaleDetailResponse']> = {},
): ApiSchemas['SaleDetailResponse'] {
  return {
    ...buildTestSaleSummary(),
    productId: 'product-128',
    startedAt: '2026-11-15T10:10:00Z',
    qr: null,
    ...overrides,
  };
}
