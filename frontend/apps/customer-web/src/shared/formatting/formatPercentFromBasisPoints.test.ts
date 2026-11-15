import { describe, expect, it } from 'vitest';

import { formatPercentFromBasisPoints } from './formatPercentFromBasisPoints';

describe('formatPercentFromBasisPoints', () => {
  it.each([
    [3889, '38.9%'],
    [3950, '39.5%'],
    [3350, '33.5%'],
    [3667, '36.7%'],
    [2667, '26.7%'],
    [5925, '59.3%'],
    [4000, '40%'],
    [3500, '35%'],
    [683, '6.8%'],
    [0, '0%'],
    [9996, '100%'],
  ])('shows %i basis points as %s', (basisPoints, expectedText) => {
    expect(formatPercentFromBasisPoints(basisPoints)).toBe(expectedText);
  });

  it('refuses a value that is not whole basis points', () => {
    expect(() => formatPercentFromBasisPoints(38.9)).toThrow(RangeError);
    expect(() => formatPercentFromBasisPoints(-1)).toThrow(RangeError);
  });
});
