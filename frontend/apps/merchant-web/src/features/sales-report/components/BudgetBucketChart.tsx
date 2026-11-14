import { formatRupeesFromPaise } from '@emi-copilot/shared-i18n';
import { useId } from 'react';
import { useTranslation } from 'react-i18next';

import type { MissedSalesReport } from '../api/salesReportApi';
import { describeBucketPlans, describeBudgetBucketRange } from '../model/describeBudgetBucket';
import {
  formatBudgetBucketCount,
  formatPossiblySuppressedCount,
  isBudgetBucketCountHidden,
} from '../model/reportCounts';

export interface BudgetBucketChartProps {
  missedSales: MissedSalesReport;
}

const TALLEST_BAR_HEIGHT_IN_PIXELS = 104;

// Every hidden bucket draws the same short dashed stub, so its bar never hints at its size.
const HIDDEN_BAR_CLASS_NAMES =
  'block h-2 w-full rounded-input border border-dashed border-border-strong bg-grey-tint';

// "Monthly budgets customers entered": decorative bars plus a screen-reader table with the same
// API counts; a hidden bucket reads "Hidden" (it may hold 5 or more) with a privacy note; a calm
// note replaces the chart when too few told a budget (plan Q3). No ceiling, no legend.
export function BudgetBucketChart({ missedSales }: BudgetBucketChartProps) {
  const { t } = useTranslation();
  const headingId = useId();
  if (missedSales.areBudgetBucketsHidden) {
    return (
      <p className="rounded-input bg-light-blue p-3 text-body text-slate">
        {t('report.budgets.hidden')}
      </p>
    );
  }
  const buckets = missedSales.budgetBuckets;
  const visibleCounts = buckets.map((bucket) =>
    isBudgetBucketCountHidden(bucket) ? 0 : (bucket.customerCount ?? 0),
  );
  const hasHiddenBucket = buckets.some(isBudgetBucketCountHidden);
  const largestCount = Math.max(1, ...visibleCounts);
  const ceiling =
    missedSales.budgetCeilingInPaise === null
      ? undefined
      : formatRupeesFromPaise(missedSales.budgetCeilingInPaise);
  const hasPlansColumn = buckets.some((bucket) => bucket.plans.length > 0);
  const totalText = formatPossiblySuppressedCount(t, {
    customerCount: missedSales.budgetTotalCustomerCount,
    isSuppressed: missedSales.budgetTotalCustomerCount === null,
  });
  return (
    <section aria-labelledby={headingId} className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 id={headingId} className="text-body font-bold text-navy">
          {t('report.budgets.title', { total: totalText })}
        </h3>
        {ceiling === undefined ? null : (
          <p aria-hidden="true" className="flex gap-3 text-label font-normal text-slate">
            <span className="flex items-center gap-1">
              <span className="size-3 rounded-pill bg-orange" />
              {t('report.budgets.legendUnder', { ceiling })}
            </span>
            <span className="flex items-center gap-1">
              <span className="size-3 rounded-pill bg-steel-blue" />
              {t('report.budgets.legendFrom', { ceiling })}
            </span>
          </p>
        )}
      </div>
      <div aria-hidden="true" className="grid grid-cols-5 items-end gap-2">
        {buckets.map((bucket, bucketIndex) => (
          <div key={bucket.lowerBoundInPaise} className="flex flex-col items-center gap-1">
            <span className="text-label tabular-nums text-deep-navy">
              {formatBudgetBucketCount(t, bucket)}
            </span>
            {isBudgetBucketCountHidden(bucket) ? (
              <span className={HIDDEN_BAR_CLASS_NAMES} />
            ) : (
              <span
                className={`block w-full rounded-input ${bucket.isUnderCeiling ? 'bg-orange' : 'bg-steel-blue'}`}
                style={{
                  height: `${Math.round(((visibleCounts[bucketIndex] ?? 0) / largestCount) * TALLEST_BAR_HEIGHT_IN_PIXELS)}px`,
                }}
              />
            )}
            <span className="text-center text-caption text-slate">
              {describeBudgetBucketRange(t, bucket)}
            </span>
            <span className="text-center text-caption text-ink-muted">
              {describeBucketPlans(t, bucket).join(', ')}
            </span>
          </div>
        ))}
      </div>
      <table className="sr-only">
        <caption>{t('report.budgets.title', { total: totalText })}</caption>
        <thead>
          <tr>
            <th scope="col">{t('report.budgets.columnRange')}</th>
            <th scope="col">{t('report.budgets.columnCustomers')}</th>
            {hasPlansColumn ? <th scope="col">{t('report.budgets.columnPlans')}</th> : null}
          </tr>
        </thead>
        <tbody>
          {buckets.map((bucket) => (
            <tr key={bucket.lowerBoundInPaise}>
              <th scope="row">{describeBudgetBucketRange(t, bucket)}</th>
              <td>{formatBudgetBucketCount(t, bucket)}</td>
              {hasPlansColumn ? <td>{describeBucketPlans(t, bucket).join(', ')}</td> : null}
            </tr>
          ))}
        </tbody>
      </table>
      {hasHiddenBucket ? (
        <p className="text-label font-normal text-slate">{t('report.budgets.hiddenBucketsNote')}</p>
      ) : null}
    </section>
  );
}
