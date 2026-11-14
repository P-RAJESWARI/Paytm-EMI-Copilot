import { formatRupeesFromPaise } from '@emi-copilot/shared-i18n';
import { useId } from 'react';
import { useTranslation } from 'react-i18next';

import type { MissedSalesReport } from '../api/salesReportApi';
import { describeBucketPlans, describeBudgetBucketRange } from '../model/describeBudgetBucket';
import { formatPossiblySuppressedCount } from '../model/reportCounts';

export interface BudgetBucketChartProps {
  missedSales: MissedSalesReport;
}

const TALLEST_BAR_HEIGHT_IN_PIXELS = 104;

// "Monthly budgets customers entered": decorative bars plus a screen-reader table with the same
// API counts; a calm note replaces it when too few told a budget (plan Q3). No ceiling, no legend.
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
    bucket.isSuppressed ? 0 : (bucket.customerCount ?? 0),
  );
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
              {formatPossiblySuppressedCount(t, bucket)}
            </span>
            <span
              className={`block w-full rounded-input ${bucket.isUnderCeiling ? 'bg-orange' : 'bg-steel-blue'}`}
              style={{
                height: `${Math.round(((visibleCounts[bucketIndex] ?? 0) / largestCount) * TALLEST_BAR_HEIGHT_IN_PIXELS)}px`,
              }}
            />
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
              <td>{formatPossiblySuppressedCount(t, bucket)}</td>
              {hasPlansColumn ? <td>{describeBucketPlans(t, bucket).join(', ')}</td> : null}
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
