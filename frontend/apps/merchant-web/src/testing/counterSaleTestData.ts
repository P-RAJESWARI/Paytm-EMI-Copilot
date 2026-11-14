import type { ApiSchemas } from '@emi-copilot/api-client';

/** The three M2 catalogue items with their offer counts (plan Q15). */
export const TEST_PRODUCTS: ApiSchemas['CatalogueProductResponse'][] = [
  {
    productId: 'product-128',
    name: 'Example phone, 128 GB',
    listPriceInPaise: 2200000,
    planCount: 3,
    noExtraCostPlanCount: 1,
  },
  {
    productId: 'product-64',
    name: 'Example phone, 64 GB',
    listPriceInPaise: 1800000,
    planCount: 2,
    noExtraCostPlanCount: 1,
  },
  {
    productId: 'product-earbuds',
    name: 'Example earbuds',
    listPriceInPaise: 249900,
    planCount: 1,
    noExtraCostPlanCount: 0,
  },
];
