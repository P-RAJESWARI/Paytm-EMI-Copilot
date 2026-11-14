import type { TFunction } from 'i18next';

import { formatCountTheIndianWay } from '../../../shared/formatting/formatCount';
import type { BudgetBucket, FunnelReport } from '../api/salesReportApi';

/** A count the API may hide: funnel stages, the missed count and the budget total come as
 * isSuppressed with no number when they hold 1 to 4 customers (plan Q3). */
export interface PossiblySuppressedCount {
  customerCount: number | null;
  isSuppressed: boolean;
}

// Gives a funnel, missed or budget-total count as shown: "120", or "fewer than 5" when suppressed.
// Not for budget buckets: see formatBudgetBucketCount.
export function formatPossiblySuppressedCount(
  t: TFunction,
  count: PossiblySuppressedCount,
): string {
  if (count.isSuppressed || count.customerCount === null) return t('report.fewerThanFive');
  return formatCountTheIndianWay(count.customerCount);
}

// True when the API hid a budget bucket's count, whatever its size.
export function isBudgetBucketCountHidden(bucket: BudgetBucket): boolean {
  return bucket.isSuppressed || bucket.customerCount === null;
}

// Gives a budget bucket count as shown: "14", or "hidden" when suppressed. A hidden bucket may hold
// 5 or more (the API hides a second bucket beside a lone small one), so it never says "fewer than 5".
export function formatBudgetBucketCount(t: TFunction, bucket: BudgetBucket): string {
  if (bucket.isSuppressed || bucket.customerCount === null) return t('report.budgets.hiddenCount');
  return formatCountTheIndianWay(bucket.customerCount);
}

// True when nobody started an EMI sale in the range, so M5 shows its empty state instead.
export function isFunnelEmpty(funnel: FunnelReport): boolean {
  return funnel.stages.every((stage) => !stage.isSuppressed && stage.customerCount === 0);
}
