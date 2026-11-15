// Starts the sales whose QR link the customer tests open: on the counter tablet through the
// merchant UI (when the test also watches M3), or through the merchant API with its own device.
import { randomUUID } from 'node:crypto';

import type { ApiSchemas } from '@emi-copilot/api-client';
import {
  expect,
  test,
  type APIRequestContext,
  type Browser,
  type BrowserContext,
  type Page,
} from '@playwright/test';

import { CUSTOMER_WEB_ORIGIN, MERCHANT_WEB_ORIGIN } from './endToEndSettings';
import { startSaleForProduct } from './merchantScreens';

/** The design sample item (DESIGN_SPEC section 4): ₹22,000 with the three Mock plans. */
export const DEMO_PRODUCT_NAME = 'Example phone, 128 GB';

/** A started sale and the link its QR code holds. */
export interface StartedSale {
  saleId: string;
  customerUrl: string;
}

/** The counter tablet, in its own browser context beside the customer's phone. */
export interface CounterTablet {
  merchantContext: BrowserContext;
  merchantPage: Page;
}

// Fails unless the QR link opens customer-web with the token in the fragment (#t=), as the
// backend's CUSTOMER_WEB_BASE_URL sets it; gives the link.
function readCustomerUrl(sale: ApiSchemas['SaleDetailResponse']): string {
  const customerUrl = sale.qr?.customerUrl;
  if (customerUrl === undefined) throw new Error('The started sale has no QR link.');
  expect(customerUrl.startsWith(`${CUSTOMER_WEB_ORIGIN}/#t=`)).toBe(true);
  return customerUrl;
}

// Opens a tablet-sized browser context on merchant-web, so one test can play shop and customer.
export async function openCounterTablet(browser: Browser): Promise<CounterTablet> {
  const merchantContext = await browser.newContext({
    baseURL: MERCHANT_WEB_ORIGIN,
    viewport: { width: 1024, height: 768 },
    locale: 'en-IN',
    timezoneId: 'Asia/Kolkata',
  });
  return { merchantContext, merchantPage: await merchantContext.newPage() };
}

// M2 to M3 on a paired tablet: starts the sale as the merchant does and reads the QR link from
// the start-sale answer (the QR image holds the same link; the token never reaches the page text).
export async function startSaleOnTheTablet(merchantPage: Page): Promise<StartedSale> {
  const startSaleAnswer = merchantPage.waitForResponse(
    (response) =>
      response.request().method() === 'POST' &&
      new URL(response.url()).pathname === '/api/v1/sales',
  );
  const saleId = await startSaleForProduct(merchantPage, DEMO_PRODUCT_NAME);
  const sale = (await (await startSaleAnswer).json()) as ApiSchemas['SaleDetailResponse'];
  expect(sale.saleId).toBe(saleId);
  return { saleId, customerUrl: readCustomerUrl(sale) };
}

// Starts a sale of the demo item through the merchant API with an Idempotency-Key, for tests that
// do not watch the merchant screens; gives its QR link.
export async function startSaleThroughApi(
  request: APIRequestContext,
  accessToken: string,
): Promise<StartedSale> {
  return test.step(`start an EMI sale for ${DEMO_PRODUCT_NAME} through the API`, async () => {
    const authorization = { Authorization: `Bearer ${accessToken}` };
    const productsResponse = await request.get('/api/v1/products', {
      params: { search: DEMO_PRODUCT_NAME },
      headers: authorization,
    });
    expect(productsResponse.status()).toBe(200);
    const { products } = (await productsResponse.json()) as ApiSchemas['ProductsResponse'];
    const demoProduct = products.find((product) => product.name === DEMO_PRODUCT_NAME);
    if (demoProduct === undefined) throw new Error(`The seed has no "${DEMO_PRODUCT_NAME}".`);
    const saleResponse = await request.post('/api/v1/sales', {
      data: { productId: demoProduct.productId },
      headers: { ...authorization, 'Idempotency-Key': randomUUID() },
    });
    expect(saleResponse.status()).toBe(201);
    const sale = (await saleResponse.json()) as ApiSchemas['SaleDetailResponse'];
    return { saleId: sale.saleId, customerUrl: readCustomerUrl(sale) };
  });
}
