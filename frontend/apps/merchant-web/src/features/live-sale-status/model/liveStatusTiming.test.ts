import { describe, expect, it } from 'vitest';

import { getReconnectDelayInMilliseconds } from './liveStatusTiming';

describe('getReconnectDelayInMilliseconds', () => {
  it('doubles from one second and stops growing at thirty seconds', () => {
    expect([0, 1, 2, 3, 4, 5, 6, 10].map(getReconnectDelayInMilliseconds)).toEqual([
      1_000, 1_000, 2_000, 4_000, 8_000, 16_000, 30_000, 30_000,
    ]);
  });
});
