import { groupDigitsTheIndianWay } from '@emi-copilot/shared-i18n';

// Gives a count of customers or sales with Indian digit grouping ("1,20,000"); refuses anything
// that is not a whole, non-negative number with an error that names a count, not paise.
export function formatCountTheIndianWay(count: number): string {
  if (!Number.isSafeInteger(count) || count < 0) {
    throw new RangeError('A count must be a non-negative safe integer.');
  }
  return groupDigitsTheIndianWay(count);
}
