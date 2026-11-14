import { formatRupeesFromPaise, useLanguagePreference } from '@emi-copilot/shared-i18n';
import { useTranslation } from 'react-i18next';

import { formatCalendarDate } from '../../../shared/formatting/formatCalendarDate';
import type { MoneyDueReport } from '../api/salesReportApi';

export interface MoneyDueSummaryProps {
  moneyDue: MoneyDueReport;
}

// The face of the "Money due from brands" card: the total and the next expected payment date.
export function MoneyDueSummary({ moneyDue }: MoneyDueSummaryProps) {
  const { t } = useTranslation();
  const { selectedLanguage } = useLanguagePreference();
  return (
    <>
      <span className="text-lead font-bold text-navy">{t('report.moneyDue.title')}</span>
      <span className="money-figure text-deep-navy">
        {formatRupeesFromPaise(moneyDue.totalDueInPaise)}
      </span>
      <span className="text-body text-slate">
        {moneyDue.nextExpectedDate === null
          ? t('report.moneyDue.nothingDue')
          : t('report.moneyDue.nextPayment', {
              date: formatCalendarDate(moneyDue.nextExpectedDate, selectedLanguage, 'dayAndMonth'),
            })}
      </span>
    </>
  );
}
