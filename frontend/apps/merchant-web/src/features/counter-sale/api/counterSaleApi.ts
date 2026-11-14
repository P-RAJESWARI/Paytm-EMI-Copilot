import type { ApiSchemas, BackendApiClient } from '@emi-copilot/api-client';

import { readApiData } from '../../../shared/api/readApiData';
import { buildSaleQueryKeyPrefix } from '../../../shared/api/saleQueryKeys';

export type CatalogueProduct = ApiSchemas['CatalogueProductResponse'];
export type SaleSummary = ApiSchemas['SaleSummaryResponse'];
export type SaleDetail = ApiSchemas['SaleDetailResponse'];
export type CustomerQr = ApiSchemas['CustomerQrResponse'];

// Gives the query key of the product list for one search text.
export function buildProductsQueryKey(searchText: string): readonly [string, string] {
  return ['products', searchText];
}

// Gives the query key of one sale's detail; it sits under the sale's live-status prefix.
export function buildSaleDetailQueryKey(saleId: string): readonly [string, string, string] {
  return [...buildSaleQueryKeyPrefix(saleId), 'detail'];
}

// Gives the query key of the QR code issued for a sale. It is deliberately outside the sale's
// live-status prefix: a status change must never issue a new QR code by refetching.
export function buildCustomerQrQueryKey(saleId: string): readonly [string, string] {
  return ['customer-qr', saleId];
}

// Reads the shop's products matching the search text (GET /products?search=).
export async function fetchProducts(
  apiClient: BackendApiClient,
  searchText: string,
): Promise<CatalogueProduct[]> {
  const trimmedSearchText = searchText.trim();
  const productsResponse = await readApiData(
    apiClient.GET('/api/v1/products', {
      params: { query: trimmedSearchText === '' ? {} : { search: trimmedSearchText } },
    }),
  );
  return productsResponse.products;
}

// Reads today's sales at the counter, newest first (GET /sales?view=counter).
export async function fetchCounterSales(apiClient: BackendApiClient): Promise<SaleSummary[]> {
  const counterSalesResponse = await readApiData(
    apiClient.GET('/api/v1/sales', { params: { query: { view: 'counter' } } }),
  );
  return counterSalesResponse.sales;
}

// Starts a sale at the product's list price; the same Idempotency-Key gives the same sale back.
export function startSale(
  apiClient: BackendApiClient,
  productId: string,
  idempotencyKey: string,
): Promise<SaleDetail> {
  return readApiData(
    apiClient.POST('/api/v1/sales', {
      params: { header: { 'Idempotency-Key': idempotencyKey } },
      body: { productId },
    }),
  );
}

// Reads one of the shop's sales (GET /sales/{saleId}).
export function fetchSaleDetail(apiClient: BackendApiClient, saleId: string): Promise<SaleDetail> {
  return readApiData(apiClient.GET('/api/v1/sales/{saleId}', { params: { path: { saleId } } }));
}

// Issues a fresh QR code for a CHOOSING sale and voids the old one (POST /sales/{saleId}/qr-tokens).
export function issueCustomerQr(apiClient: BackendApiClient, saleId: string): Promise<CustomerQr> {
  return readApiData(
    apiClient.POST('/api/v1/sales/{saleId}/qr-tokens', { params: { path: { saleId } } }),
  );
}
