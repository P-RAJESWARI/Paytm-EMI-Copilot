import type { ApiSchemas, BackendApiClient } from '@emi-copilot/api-client';

import { readApiData } from '../../../shared/api/readApiData';
import { buildSaleQueryKeyPrefix } from '../../../shared/api/saleQueryKeys';

export type SaleHandoff = ApiSchemas['SaleHandoffResponse'];
export type SalePaymentLink = ApiSchemas['SalePaymentLinkResponse'];
export type SalePaymentStatus = ApiSchemas['SalePaymentStatusResponse'];
export type HandoffPaymentStatus = ApiSchemas['HandoffPaymentStatus'];

// Gives the query key of a sale's hand-off; it sits under the sale's live-status prefix, so a
// PAID event refreshes M4 at once.
export function buildSaleHandoffQueryKey(saleId: string): readonly [string, string, string] {
  return [...buildSaleQueryKeyPrefix(saleId), 'handoff'];
}

// Reads the agreed plan, EDC steps, latest link and payment status (GET /sales/{saleId}/handoff).
export function fetchSaleHandoff(
  apiClient: BackendApiClient,
  saleId: string,
): Promise<SaleHandoff> {
  return readApiData(
    apiClient.GET('/api/v1/sales/{saleId}/handoff', { params: { path: { saleId } } }),
  );
}

// Makes a payment link for the agreed plan; the same Idempotency-Key gives the same link back.
export function createSalePaymentLink(
  apiClient: BackendApiClient,
  saleId: string,
  idempotencyKey: string,
): Promise<SalePaymentLink> {
  return readApiData(
    apiClient.POST('/api/v1/sales/{saleId}/payment-links', {
      params: { path: { saleId }, header: { 'Idempotency-Key': idempotencyKey } },
    }),
  );
}

// Asks the server to check the payment with the gateway (GET /sales/{saleId}/payment-status).
export function checkSalePaymentStatus(
  apiClient: BackendApiClient,
  saleId: string,
): Promise<SalePaymentStatus> {
  return readApiData(
    apiClient.GET('/api/v1/sales/{saleId}/payment-status', { params: { path: { saleId } } }),
  );
}
