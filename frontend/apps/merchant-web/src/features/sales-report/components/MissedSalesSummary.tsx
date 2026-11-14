import { formatRupeesFromPaise } from '@emi-copilot/shared-i18n';
import { useTranslation } from 'react-i18next';

import type { MissedSalesReport } from '../api/salesReportApi';

export interface MissedSalesSummaryProps {
  missedSales: MissedSalesReport;
}

// The face of the "Missed sales" card (inline text only, as it sits inside a button).
export function MissedSalesSummary({ missedSales }: MissedSalesSummaryProps) {
  const { t } = useTranslation();
  const ceilingInPaise = missedSales.budgetCeilingInPaise;
  let headline: string;
  if (ceilingInPaise === null || missedSales.missedCustomerCount === 0) {
    headline = t('report.missedSales.none');
  } else if (missedSales.isSuppressed || missedSales.missedCustomerCount === null) {
    headline = t('report.missedSales.headlineFew', {
      ceiling: formatRupeesFromPaise(ceilingInPaise),
    });
  } else {
    headline = t('report.missedSales.headline', {
      count: missedSales.missedCustomerCount,
      ceiling: formatRupeesFromPaise(ceilingInPaise),
    });
  }
  return (
    <>
      <span className="text-lead font-bold text-navy">{t('report.missedSales.title')}</span>
      <span className="text-body text-deep-navy">{headline}</span>
    </>
  );
}
