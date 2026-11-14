import { describe, expect, it } from 'vitest';

import {
  formatRupeesFromPaise,
  formatRupeesWithPaiseFromPaise,
  groupDigitsTheIndianWay,
} from './formatRupees';

const INDIAN_GROUPED_RUPEES = /^₹(\d{1,3}|\d{1,2}(,\d{2})*,\d{3})$/;

// A small deterministic generator (linear congruential), so the property cases never change between runs.
function generateAmountsInPaise(count: number): number[] {
  let seed = 20261115;
  return Array.from({ length: count }, () => {
    seed = (seed * 1103515245 + 12345) % 2147483648;
    const magnitude = 10 ** (seed % 12);
    return Math.floor((seed / 2147483648) * magnitude);
  });
}

// Reads a formatted amount back into whole rupees.
function parseWholeRupees(formattedAmount: string): number {
  return Number(formattedAmount.replace('₹', '').replaceAll(',', ''));
}

describe('formatRupeesFromPaise', () => {
  it.each([
    [0, '₹0'],
    [49, '₹0'],
    [50, '₹1'],
    [99, '₹1'],
    [100, '₹1'],
    [110000, '₹1,100'],
    [205000, '₹2,050'],
    [366665, '₹3,667'],
    [366667, '₹3,667'],
    [2200000, '₹22,000'],
    [2460000, '₹24,600'],
    [18400000, '₹1,84,000'],
    [99999950, '₹10,00,000'],
    [1234567890, '₹1,23,45,679'],
  ])('formats %i paise as %s', (amountInPaise, expectedText) => {
    expect(formatRupeesFromPaise(amountInPaise)).toBe(expectedText);
  });

  it('always groups digits the Indian way and rounds half-up to whole rupees', () => {
    for (const amountInPaise of generateAmountsInPaise(500)) {
      const formattedAmount = formatRupeesFromPaise(amountInPaise);

      expect(formattedAmount).toMatch(INDIAN_GROUPED_RUPEES);
      expect(parseWholeRupees(formattedAmount)).toBe(Math.floor((amountInPaise + 50) / 100));
    }
  });

  it.each([
    ['a negative amount', -1],
    ['a fraction of a paisa', 1.5],
    ['not a number', Number.NaN],
    ['infinity', Number.POSITIVE_INFINITY],
    ['an unsafe integer', Number.MAX_SAFE_INTEGER + 1],
  ])('rejects %s', (_description, amountInPaise) => {
    expect(() => formatRupeesFromPaise(amountInPaise)).toThrow(RangeError);
  });
});

describe('formatRupeesWithPaiseFromPaise', () => {
  it.each([
    [0, '₹0.00'],
    [5, '₹0.05'],
    [366667, '₹3,666.67'],
    [366665, '₹3,666.65'],
    [18400000, '₹1,84,000.00'],
  ])('formats %i paise as %s', (amountInPaise, expectedText) => {
    expect(formatRupeesWithPaiseFromPaise(amountInPaise)).toBe(expectedText);
  });

  it('keeps every paisa: the digits read back to the same amount', () => {
    for (const amountInPaise of generateAmountsInPaise(500)) {
      const digitsOnly = formatRupeesWithPaiseFromPaise(amountInPaise).replace(/[₹,.]/g, '');

      expect(Number(digitsOnly)).toBe(amountInPaise);
    }
  });

  it('rejects a negative amount', () => {
    expect(() => formatRupeesWithPaiseFromPaise(-100)).toThrow(RangeError);
  });
});

describe('groupDigitsTheIndianWay', () => {
  it.each([
    [7, '7'],
    [999, '999'],
    [1000, '1,000'],
    [99999, '99,999'],
    [100000, '1,00,000'],
    [10000000, '1,00,00,000'],
  ])('groups %i as %s', (wholeNumber, expectedText) => {
    expect(groupDigitsTheIndianWay(wholeNumber)).toBe(expectedText);
  });
});
