import { renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { CustomerApiError } from '../api/customerApiError';
import { useIdempotencyKeyPerIntent } from './useIdempotencyKeyPerIntent';

const WRONG_OTP = new CustomerApiError(422, 'OTP_INCORRECT', { hasProblemBody: true });
const LOST_ANSWER = new CustomerApiError(0, 'NETWORK_UNAVAILABLE');

// Renders the hook and gives its two functions.
function renderKeys() {
  return renderHook(() => useIdempotencyKeyPerIntent()).result.current;
}

describe('useIdempotencyKeyPerIntent', () => {
  it('re-sends the same key for a retry while the outcome is unknown', () => {
    const keys = renderKeys();
    const firstKey = keys.takeIdempotencyKey('offer-a:366667:2200000');

    keys.settleIdempotencyKey(firstKey, LOST_ANSWER);

    expect(firstKey).toMatch(/^[0-9a-f-]{36}$/);
    expect(keys.takeIdempotencyKey('offer-a:366667:2200000')).toBe(firstKey);
  });

  it('starts a new key after a success, a definite problem or another intent', () => {
    const keys = renderKeys();
    const firstKey = keys.takeIdempotencyKey('offer-a');
    keys.settleIdempotencyKey(firstKey, WRONG_OTP);
    const secondKey = keys.takeIdempotencyKey('offer-a');
    keys.settleIdempotencyKey('an-old-key', null);
    keys.settleIdempotencyKey(secondKey, null);

    expect(secondKey).not.toBe(firstKey);
    expect(keys.takeIdempotencyKey('offer-a')).not.toBe(secondKey);
    expect(keys.takeIdempotencyKey('offer-b')).not.toBe(keys.takeIdempotencyKey('offer-a'));
  });
});
