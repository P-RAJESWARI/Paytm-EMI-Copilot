import { formatRupeesFromPaise, useLanguagePreference } from '@emi-copilot/shared-i18n';
import { Chip, type ChipTone } from '@emi-copilot/ui-kit';
import { useTranslation } from 'react-i18next';

import { formatCalendarDate } from '../../../shared/formatting/formatCalendarDate';
import type { MoneyDueReport } from '../api/salesReportApi';

export interface MoneyDuePanelContentProps {
  moneyDue: MoneyDueReport;
}

const CHIP_TONE_BY_SETTLEMENT_STATUS: Record<
  MoneyDueReport['batches'][number]['status'],
  ChipTone
> = {
  CLAIM_FILED: 'information',
  WAITING_FOR_BRAND: 'attention',
  NOT_YET_DUE: 'neutral',
};

// The open "Money due from brands" detail (M7): why brands owe money, each batch with its
// estimated date, status and amount, and the reminder that dates are estimates.
export function MoneyDuePanelContent({ moneyDue }: MoneyDuePanelContentProps) {
  const { t } = useTranslation();
  const { selectedLanguage } = useLanguagePreference();
  return (
    <div className="flex flex-col gap-4">
      <p className="text-body text-slate">{t('report.moneyDue.explainer')}</p>
      {moneyDue.batches.length === 0 ? (
        <p className="text-body text-slate">{t('report.moneyDue.noBatches')}</p>
      ) : (
        <ul className="m-0 flex list-none flex-col gap-2 p-0">
          {moneyDue.batches.map((batch) => (
            <li
              key={batch.batchNumber}
              className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-3 rounded-input bg-light-blue p-3"
            >
              <span className="flex flex-col">
                <span className="text-body font-bold text-deep-navy">
                  {t('report.moneyDue.batchName', {
                    batchNumber: batch.batchNumber,
                    count: batch.saleCount,
                  })}
                </span>
                <span className="text-label font-normal text-slate">
                  {t('report.moneyDue.expected', {
                    date: formatCalendarDate(batch.expectedDate, selectedLanguage, 'full'),
                  })}
                </span>
              </span>
              <Chip tone={CHIP_TONE_BY_SETTLEMENT_STATUS[batch.status]}>
                {t(`report.moneyDue.status.${batch.status}`)}
              </Chip>
              <span className="text-lead font-bold tabular-nums text-deep-navy">
                {formatRupeesFromPaise(batch.amountInPaise)}
              </span>
            </li>
          ))}
        </ul>
      )}
      <p className="text-label font-normal text-slate">{t('report.moneyDue.datesAreEstimates')}</p>
    </div>
  );
}
