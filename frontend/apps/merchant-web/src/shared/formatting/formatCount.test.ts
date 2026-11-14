import { describe, expect, it } from 'vitest';

import { formatCountTheIndianWay } from './formatCount';

describe('formatCountTheIndianWay', () => {
  it('groups a count the Indian way', () => {
    expect(formatCountTheIndianWay(0)).toBe('0');
    expect(formatCountTheIndianWay(120)).toBe('120');
    expect(formatCountTheIndianWay(120000)).toBe('1,20,000');
  });

  it('refuses a count that is negative or not whole, naming a count in the error', () => {
    expect(() => formatCountTheIndianWay(-1)).toThrow(
      'A count must be a non-negative safe integer.',
    );
    expect(() => formatCountTheIndianWay(2.5)).toThrow(
      'A count must be a non-negative safe integer.',
    );
    expect(() => formatCountTheIndianWay(Number.NaN)).toThrow(RangeError);
  });
});
