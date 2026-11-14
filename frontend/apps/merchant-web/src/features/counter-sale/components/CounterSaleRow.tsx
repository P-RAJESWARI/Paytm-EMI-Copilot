import { useLanguagePreference } from '@emi-copilot/shared-i18n';
import { getButtonClassName, StatusChip } from '@emi-copilot/ui-kit';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import { buildShowQrPath, buildTakePaymentPath } from '../../../app/merchantPaths';
import { formatShopTime } from '../../../shared/formatting/formatShopTime';
import { getSaleStatusChipTone } from '../../../shared/saleStatus/saleStatusChipTone';
import type { SaleSummary } from '../api/counterSaleApi';
import { getCounterSaleAction } from '../model/counterSaleAction';

export interface CounterSaleRowProps {
  sale: SaleSummary;
}

// One customer at the counter: product, session code, status chip and the next step, if any.
export function CounterSaleRow({ sale }: CounterSaleRowProps) {
  const { t } = useTranslation();
  const { selectedLanguage } = useLanguagePreference();
  const action = getCounterSaleAction(sale.status);
  const statusLabel =
    sale.status === 'PAID'
      ? t('counterList.paidAt', { time: formatShopTime(sale.statusChangedAt, selectedLanguage) })
      : sale.status === 'CHOOSING'
        ? t('counterList.choosingOnTheirPhone')
        : t(`saleStatus.${sale.status}`);
  const codeForScreenReaders = (
    <span className="sr-only">{t('counterList.forCode', { code: sale.sessionCode })}</span>
  );
  return (
    <li className="flex flex-wrap items-center justify-between gap-3 rounded-card bg-white p-4 shadow-card">
      <div className="flex min-w-0 flex-col gap-1">
        <span className="text-body font-bold text-deep-navy">{sale.productName}</span>
        <span className="text-label font-normal text-slate">
          {t('counterList.sessionCode', { code: sale.sessionCode })}
        </span>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <StatusChip tone={getSaleStatusChipTone(sale.status)} label={statusLabel} />
        {action === 'takePayment' ? (
          <Link to={buildTakePaymentPath(sale.saleId)} className={getButtonClassName()}>
            {t('counterList.takePayment')}
            {codeForScreenReaders}
          </Link>
        ) : null}
        {action === 'showQr' ? (
          <Link
            to={buildShowQrPath(sale.saleId)}
            className={getButtonClassName({ variant: 'secondary' })}
          >
            {t('counterList.showQr')}
            {codeForScreenReaders}
          </Link>
        ) : null}
      </div>
    </li>
  );
}
