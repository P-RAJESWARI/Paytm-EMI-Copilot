import { formatRupeesFromPaise } from '@emi-copilot/shared-i18n';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import type { MissedSalesReport } from '../api/salesReportApi';
import { describeMissingProductInsight } from '../model/describeMissedSales';
import { BudgetBucketChart } from './BudgetBucketChart';

export interface MissedSalesPanelContentProps {
  missedSales: MissedSalesReport;
  /** The suggested-action text ("Ask the brand for a 9 or 12-month…"), if the API suggested one. */
  suggestedActionText: string | undefined;
  /** The share control, when there is something to share. */
  shareControl: ReactNode;
}

// The open "Missed sales" detail (M6): the product insight, the suggested action with "Share
// with brand rep", and the budget chart. Every amount is an API figure.
export function MissedSalesPanelContent({
  missedSales,
  suggestedActionText,
  shareControl,
}: MissedSalesPanelContentProps) {
  const { t } = useTranslation();
  const insight = missedSales.productInsight;
  const ceilingInPaise = missedSales.budgetCeilingInPaise;
  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-4 md:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
        {insight === null || ceilingInPaise === null ? (
          <p className="text-body text-slate">{describeMissingProductInsight(t, missedSales)}</p>
        ) : (
          <div className="flex flex-col gap-2 text-body text-deep-navy">
            <p className="font-bold">
              {t('report.missedSales.lowestNoCost', {
                productName: insight.productName,
                monthly: formatRupeesFromPaise(insight.lowestNoExtraCostMonthlyInPaise),
              })}
            </p>
            <p>
              {insight.cheapestPlanUnderCeiling === null
                ? t('report.missedSales.noPlanUnderCeiling', {
                    ceiling: formatRupeesFromPaise(ceilingInPaise),
                  })
                : t('report.missedSales.leastExtraUnderCeiling', {
                    ceiling: formatRupeesFromPaise(ceilingInPaise),
                    extra: formatRupeesFromPaise(
                      insight.cheapestPlanUnderCeiling.extraInTotalInPaise,
                    ),
                  })}
            </p>
          </div>
        )}
        {suggestedActionText === undefined ? null : (
          <div className="flex flex-col gap-2 rounded-card bg-light-blue p-4">
            <p className="text-label text-slate">{t('report.missedSales.suggestedAction')}</p>
            <p className="text-body font-bold text-deep-navy">{suggestedActionText}</p>
            {shareControl}
          </div>
        )}
      </div>
      <BudgetBucketChart missedSales={missedSales} />
    </div>
  );
}
