import { formatRupeesFromPaise } from '@emi-copilot/shared-i18n';
import type { TFunction } from 'i18next';

import type { MissedSalesReport } from '../api/salesReportApi';

// True when the API hid the missed count (1 to 4 customers) and every figure derived from it.
function isMissedCountSuppressed(missedSales: MissedSalesReport): boolean {
  return missedSales.isSuppressed || missedSales.missedCustomerCount === null;
}

// Writes the "Missed sales" headline from the API figures: none, "fewer than 5" or the count,
// with the budget ceiling only when the API sent one.
export function describeMissedSalesHeadline(t: TFunction, missedSales: MissedSalesReport): string {
  const ceilingInPaise = missedSales.budgetCeilingInPaise;
  const ceiling = ceilingInPaise === null ? undefined : formatRupeesFromPaise(ceilingInPaise);
  if (isMissedCountSuppressed(missedSales)) {
    return ceiling === undefined
      ? t('report.missedSales.headlineFewWithoutCeiling')
      : t('report.missedSales.headlineFew', { ceiling });
  }
  const count = missedSales.missedCustomerCount ?? 0;
  if (count === 0) return t('report.missedSales.none');
  return ceiling === undefined
    ? t('report.missedSales.headlineWithoutCeiling', { count })
    : t('report.missedSales.headline', { count, ceiling });
}

// Says why the detail names no product: nothing was missed, too few to show, or no single product.
export function describeMissingProductInsight(
  t: TFunction,
  missedSales: MissedSalesReport,
): string {
  if (isMissedCountSuppressed(missedSales)) return t('report.missedSales.detailHidden');
  if (missedSales.missedCustomerCount === 0) return t('report.missedSales.none');
  return t('report.missedSales.noInsight');
}
