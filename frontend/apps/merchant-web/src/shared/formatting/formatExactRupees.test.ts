import { describe, expect, it } from 'vitest';

import { formatExactRupeesFromPaise } from './formatExactRupees';

describe('formatExactRupeesFromPaise', () => {
  it('shows paise whenever the amount has them, never rounding', () => {
    expect(formatExactRupeesFromPaise(12495)).toBe('₹124.95');
    expect(formatExactRupeesFromPaise(262395)).toBe('₹2,623.95');
    expect(formatExactRupeesFromPaise(366667)).toBe('₹3,666.67');
  });

  it('shows whole rupees as the design does when there are no paise', () => {
    expect(formatExactRupeesFromPaise(2200000)).toBe('₹22,000');
    expect(formatExactRupeesFromPaise(0)).toBe('₹0');
  });

  it('refuses an amount that is not whole, non-negative paise', () => {
    expect(() => formatExactRupeesFromPaise(-100)).toThrow(RangeError);
    expect(() => formatExactRupeesFromPaise(12.5)).toThrow(RangeError);
  });
});
