import { getButtonClassName, StatusChip } from '@emi-copilot/ui-kit';
import { useId } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import { buildTakePaymentPath, MERCHANT_PATHS } from '../../../app/merchantPaths';
import { ChosenPlanFigures } from '../../../shared/plan/ChosenPlanFigures';
import { getSaleStatusChipTone } from '../../../shared/saleStatus/saleStatusChipTone';
import type { SaleDetail } from '../api/counterSaleApi';
import { getCounterSaleAction } from '../model/counterSaleAction';

export interface SaleStatusCardProps {
  sale: SaleDetail;
}

// M3's status card: the status chip, what it means for the merchant, and once agreed the plan
// (each month, extra in total, total) with "Take payment". Never the customer's steps or data.
export function SaleStatusCard({ sale }: SaleStatusCardProps) {
  const { t } = useTranslation();
  const headingId = useId();
  const action = getCounterSaleAction(sale.status);
  const hasEnded = sale.status === 'PAID' || sale.status === 'EXPIRED';
  return (
    <section
      aria-labelledby={headingId}
      aria-live="polite"
      className={`flex flex-col gap-3 rounded-card border-2 bg-white p-6 shadow-card ${
        action === 'takePayment' ? 'border-green' : 'border-white'
      }`}
    >
      <StatusChip
        tone={getSaleStatusChipTone(sale.status)}
        label={t(`saleStatus.${sale.status}`)}
      />
      <h2 id={headingId} className="text-title text-navy">
        {t(`showQr.status.${sale.status}.title`)}
      </h2>
      <p className="text-body text-slate">{t(`showQr.status.${sale.status}.body`)}</p>
      {action === 'takePayment' && sale.chosenPlan !== null ? (
        <div className="flex flex-col gap-4 rounded-card bg-light-blue p-4">
          <ChosenPlanFigures plan={sale.chosenPlan} />
          <Link
            to={buildTakePaymentPath(sale.saleId)}
            className={getButtonClassName({ size: 'large', isFullWidth: true })}
          >
            {t('showQr.takePayment')}
          </Link>
        </div>
      ) : null}
      {hasEnded ? (
        <Link
          to={MERCHANT_PATHS.newEmiSale}
          className={getButtonClassName({ variant: 'secondary' })}
        >
          {t('showQr.backToCounterList')}
        </Link>
      ) : null}
    </section>
  );
}
