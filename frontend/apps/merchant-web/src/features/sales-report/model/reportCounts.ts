import type { TFunction } from 'i18next';

import { formatCountTheIndianWay } from '../../../shared/formatting/formatCount';
import type { FunnelReport } from '../api/salesReportApi';

/** A count the API may hide: 1 to 4 customers come as isSuppressed with no number (plan Q3). */
export interface PossiblySuppressedCount {
  customerCount: number | null;
  isSuppressed: boolean;
}

// Gives a count as shown: "120", or "fewer than 5" when the API suppressed it.
export function formatPossiblySuppressedCount(
  t: TFunction,
  count: PossiblySuppressedCount,
): string {
  if (count.isSuppressed || count.customerCount === null) return t('report.fewerThanFive');
  return formatCountTheIndianWay(count.customerCount);
}

// True when nobody started an EMI sale in the range, so M5 shows its empty state instead.
export function isFunnelEmpty(funnel: FunnelReport): boolean {
  return funnel.stages.every((stage) => !stage.isSuppressed && stage.customerCount === 0);
}
