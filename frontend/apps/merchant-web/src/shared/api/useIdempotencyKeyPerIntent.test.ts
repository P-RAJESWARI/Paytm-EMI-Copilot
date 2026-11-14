import { renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { MerchantApiError } from './merchantApiError';
import { useIdempotencyKeyPerIntent } from './useIdempotencyKeyPerIntent';

const DEFINITE_PROBLEM = new MerchantApiError(409, 'PAYMENT_LINK_OUTCOME_UNKNOWN', undefined, true);
const LOST_ANSWER = new MerchantApiError(0, 'NETWORK_UNAVAILABLE');

// Renders the hook and gives its two functions.
function renderKeys() {
  return renderHook(() => useIdempotencyKeyPerIntent()).result.current;
}

describe('useIdempotencyKeyPerIntent', () => {
  it('re-sends the same key for a retry of the same intent while the outcome is unknown', () => {
    const keys = renderKeys();
    const firstKey = keys.takeIdempotencyKey('product-128');

    keys.settleIdempotencyKey(firstKey, LOST_ANSWER);

    expect(firstKey).toMatch(/^[0-9a-f-]{36}$/);
    expect(keys.takeIdempotencyKey('product-128')).toBe(firstKey);
  });

  it('starts a new key after a success or any definite problem answer', () => {
    const keys = renderKeys();
    const firstKey = keys.takeIdempotencyKey('sale-1');
    keys.settleIdempotencyKey(firstKey, DEFINITE_PROBLEM);
    const secondKey = keys.takeIdempotencyKey('sale-1');
    keys.settleIdempotencyKey(secondKey, null);

    expect(secondKey).not.toBe(firstKey);
    expect(keys.takeIdempotencyKey('sale-1')).not.toBe(secondKey);
  });

  it('starts a new key for another intent or a new intent, and ignores an old key settling', () => {
    const keys = renderKeys();
    const firstKey = keys.takeIdempotencyKey('product-128');
    const otherProductKey = keys.takeIdempotencyKey('product-64');
    keys.settleIdempotencyKey(firstKey, null);

    expect(otherProductKey).not.toBe(firstKey);
    expect(keys.takeIdempotencyKey('product-64')).toBe(otherProductKey);
    expect(keys.takeIdempotencyKey('product-64', true)).not.toBe(otherProductKey);
  });
});
