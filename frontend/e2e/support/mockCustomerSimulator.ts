// Plays the customer's phone through the backend's labelled MockCustomerSimulator endpoints, with
// a bearer token of its own (the browser's token lives only in the page's memory).
import type { ApiSchemas } from '@emi-copilot/api-client';
import { expect, type APIRequestContext } from '@playwright/test';

import { DEMO_SHOP_ID, readDemoShopPin } from './endToEndSettings';

/** The Mock gateway's no-cost 6-month offer on the 128 GB phone (₹3,667 a month, ₹0 extra). */
export const MOCK_NO_COST_SIX_MONTH_OFFER_ID = 'mock-offer-no-cost-6m';

// Pairs a second device for the demo shop through the API and gives its bearer token.
export async function pairDeviceThroughApi(request: APIRequestContext): Promise<string> {
  const response = await request.post('/api/v1/merchants/pairing', {
    data: { shopId: DEMO_SHOP_ID, pin: readDemoShopPin() },
  });
  expect(response.status()).toBe(201);
  const pairing = (await response.json()) as ApiSchemas['DevicePairingResponse'];
  return pairing.accessToken;
}

// Agrees the given offer on the sale, as the customer's consent will in Layer 3.
export async function agreeToPlanAsTheCustomer(
  request: APIRequestContext,
  accessToken: string,
  saleId: string,
  offerId: string,
): Promise<void> {
  const response = await request.post(
    `/api/v1/mock-customer-simulator/sales/${encodeURIComponent(saleId)}/agreed-plan`,
    { data: { offerId }, headers: { Authorization: `Bearer ${accessToken}` } },
  );
  expect(response.status()).toBe(200);
}

// Reads the order id of the payment link the merchant made for the sale on M4.
export async function readLatestPaymentLinkOrderId(
  request: APIRequestContext,
  accessToken: string,
  saleId: string,
): Promise<string> {
  const response = await request.get(`/api/v1/sales/${encodeURIComponent(saleId)}/handoff`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  expect(response.status()).toBe(200);
  const handoff = (await response.json()) as ApiSchemas['SaleHandoffResponse'];
  if (handoff.latestPaymentLink === null) {
    throw new Error('The sale has no payment link yet; "Send payment link" must come first.');
  }
  return handoff.latestPaymentLink.orderId;
}

// Pays the Mock payment link as the customer; the Mock's signed report then marks the sale paid.
export async function completePaymentAsTheCustomer(
  request: APIRequestContext,
  accessToken: string,
  orderId: string,
): Promise<void> {
  const response = await request.post(
    `/api/v1/mock-customer-simulator/payments/${encodeURIComponent(orderId)}/completed`,
    { headers: { Authorization: `Bearer ${accessToken}` } },
  );
  expect(response.status()).toBe(202);
}
