import { useTranslation } from 'react-i18next';

import type { MissedSalesReport } from '../api/salesReportApi';
import { describeMissedSalesHeadline } from '../model/describeMissedSales';

export interface MissedSalesSummaryProps {
  missedSales: MissedSalesReport;
}

// The face of the "Missed sales" card (inline text only, as it sits inside a button).
export function MissedSalesSummary({ missedSales }: MissedSalesSummaryProps) {
  const { t } = useTranslation();
  return (
    <>
      <span className="text-lead font-bold text-navy">{t('report.missedSales.title')}</span>
      <span className="text-body text-deep-navy">
        {describeMissedSalesHeadline(t, missedSales)}
      </span>
    </>
  );
}
