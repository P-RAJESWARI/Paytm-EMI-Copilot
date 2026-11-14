/**
 * Query-key roots shared by the features that show sales. Every per-sale query starts with
 * [SALE_QUERY_KEY_ROOT, saleId], so the live status feed can refresh one sale's data in every
 * feature at once. The counter list lives under the same root.
 */
export const SALE_QUERY_KEY_ROOT = 'sale';

/** The counter list (GET /sales?view=counter). */
export const COUNTER_SALES_QUERY_KEY = [SALE_QUERY_KEY_ROOT, 'counter-list'] as const;

// Gives the key prefix of every query about one sale (detail, hand-off, payment status).
export function buildSaleQueryKeyPrefix(saleId: string): readonly [string, string] {
  return [SALE_QUERY_KEY_ROOT, saleId];
}
