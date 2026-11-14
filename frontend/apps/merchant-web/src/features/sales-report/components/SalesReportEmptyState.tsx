import { getButtonClassName } from '@emi-copilot/ui-kit';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import { MERCHANT_PATHS } from '../../../app/merchantPaths';
import type { ReportingRange } from '../api/salesReportApi';

export interface SalesReportEmptyStateProps {
  range: ReportingRange;
}

// M5's empty state: no EMI sales in the period yet, and the way to start one.
export function SalesReportEmptyState({ range }: SalesReportEmptyStateProps) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col items-center gap-3 rounded-card bg-white p-8 text-center shadow-card">
      <h2 className="text-title text-navy">{t(`report.empty.title.${range}`)}</h2>
      <p className="max-w-110 text-body text-slate">{t('report.empty.body')}</p>
      <Link to={MERCHANT_PATHS.newEmiSale} className={getButtonClassName({ size: 'large' })}>
        {t('shell.newEmiSale')}
      </Link>
    </div>
  );
}
