import { describe, expect, it } from 'vitest';

import {
  convertBudgetDigitsToPaise,
  convertPaiseToBudgetDigits,
  readBudgetDigits,
} from './budgetAmount';

describe('budget amount', () => {
  it('keeps whole-rupee digits only, without leading zeros, up to seven digits', () => {
    expect(readBudgetDigits('₹3,000')).toBe('3000');
    expect(readBudgetDigits('0030')).toBe('30');
    expect(readBudgetDigits('000')).toBe('');
    expect(readBudgetDigits('123456789')).toBe('1234567');
    expect(readBudgetDigits('3000.50')).toBe('300050');
  });

  it('converts rupees to integer paise and back', () => {
    expect(convertBudgetDigitsToPaise('3000')).toBe(300000);
    expect(convertPaiseToBudgetDigits(180000)).toBe('1800');
    expect(convertPaiseToBudgetDigits(undefined)).toBe('');
  });
});
