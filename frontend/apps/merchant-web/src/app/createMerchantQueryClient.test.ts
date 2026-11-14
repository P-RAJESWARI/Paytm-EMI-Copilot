import { describe, expect, it } from 'vitest';

import { MerchantApiError } from '../shared/api/merchantApiError';
import { createMerchantQueryClient, shouldRetryQuery } from './createMerchantQueryClient';

describe('shouldRetryQuery', () => {
  it('retries a server or network failure once', () => {
    expect(shouldRetryQuery(0, new MerchantApiError(503, 'UNAVAILABLE'))).toBe(true);
    expect(shouldRetryQuery(0, new MerchantApiError(0, 'NETWORK_UNAVAILABLE'))).toBe(true);
    expect(shouldRetryQuery(1, new MerchantApiError(503, 'UNAVAILABLE'))).toBe(false);
  });

  it('never retries an answer the server refused', () => {
    expect(shouldRetryQuery(0, new MerchantApiError(404, 'SALE_NOT_FOUND'))).toBe(false);
    expect(shouldRetryQuery(0, new MerchantApiError(401, 'MERCHANT_AUTHENTICATION_REQUIRED'))).toBe(
      false,
    );
  });

  it('is the retry rule of the app cache, and mutations never retry', () => {
    const defaultOptions = createMerchantQueryClient().getDefaultOptions();

    expect(defaultOptions.queries?.retry).toBe(shouldRetryQuery);
    expect(defaultOptions.mutations?.retry).toBe(false);
  });
});
