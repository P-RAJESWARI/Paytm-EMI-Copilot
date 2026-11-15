import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { useResendCountdown } from './useResendCountdown';

afterEach(() => {
  vi.useRealTimers();
});

describe('useResendCountdown', () => {
  it('is zero before any OTP, then counts down once a second to zero', () => {
    vi.useFakeTimers();
    vi.setSystemTime(Date.parse('2026-11-15T09:30:00Z'));
    const { result } = renderHook(() => useResendCountdown());

    expect(result.current.secondsUntilResend).toBe(0);
    act(() => {
      result.current.countDownTo(Date.parse('2026-11-15T09:30:30Z'));
    });
    expect(result.current.secondsUntilResend).toBe(30);
    act(() => {
      vi.advanceTimersByTime(6000);
    });
    expect(result.current.secondsUntilResend).toBe(24);
    act(() => {
      vi.advanceTimersByTime(40000);
    });
    expect(result.current.secondsUntilResend).toBe(0);
    expect(vi.getTimerCount()).toBe(0);
  });
});
