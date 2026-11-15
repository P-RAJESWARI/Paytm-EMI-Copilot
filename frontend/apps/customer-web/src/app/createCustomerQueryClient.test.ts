import { describe, expect, it } from 'vitest';

import { CustomerApiError } from '../features/customer-flow';
import { createCustomerQueryClient, shouldRetryQuery } from './createCustomerQueryClient';

describe('createCustomerQueryClient', () => {
  it('retries a read once after a network or server failure, never after a 4xx', () => {
    expect(shouldRetryQuery(0, new CustomerApiError(0, 'NETWORK_UNAVAILABLE'))).toBe(true);
    expect(shouldRetryQuery(0, new CustomerApiError(502, 'PAYMENT_GATEWAY_UNAVAILABLE'))).toBe(
      true,
    );
    expect(shouldRetryQuery(1, new CustomerApiError(502, 'PAYMENT_GATEWAY_UNAVAILABLE'))).toBe(
      false,
    );
    expect(shouldRetryQuery(0, new CustomerApiError(409, 'BUDGET_NOT_CONFIRMED'))).toBe(false);
  });

  it('never retries mutations and never refetches on focus', () => {
    const defaults = createCustomerQueryClient().getDefaultOptions();

    expect(defaults.mutations?.retry).toBe(false);
    expect(defaults.queries?.refetchOnWindowFocus).toBe(false);
  });
});
