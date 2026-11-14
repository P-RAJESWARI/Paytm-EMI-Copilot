import { describe, expect, it } from 'vitest';

import { LiveStatusReconnectPolicy } from './LiveStatusReconnectPolicy';

describe('LiveStatusReconnectPolicy', () => {
  it('waits longer after each failure in a row and asks for polling from the third', () => {
    const policy = new LiveStatusReconnectPolicy();

    expect(policy.recordFailure()).toEqual({
      reconnectDelayInMilliseconds: 1_000,
      shouldPoll: false,
    });
    expect(policy.recordFailure()).toEqual({
      reconnectDelayInMilliseconds: 2_000,
      shouldPoll: false,
    });
    expect(policy.recordFailure()).toEqual({
      reconnectDelayInMilliseconds: 4_000,
      shouldPoll: true,
    });
  });

  it('needs no catch-up on the first connection, and does after any later one', () => {
    const policy = new LiveStatusReconnectPolicy();

    expect(policy.recordConnected()).toBe(false);
    expect(policy.recordConnected()).toBe(true);
    policy.recordFailure();
    expect(policy.recordConnected()).toBe(true);
    expect(policy.recordFailure()).toEqual({
      reconnectDelayInMilliseconds: 1_000,
      shouldPoll: false,
    });
  });

  it('catches up when the very first connection came only after failures', () => {
    const policy = new LiveStatusReconnectPolicy();
    policy.recordFailure();

    expect(policy.recordConnected()).toBe(true);
  });
});
