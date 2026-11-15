import { formatRupeesFromPaise } from '@emi-copilot/shared-i18n';
import { Button } from '@emi-copilot/ui-kit';
import { useTranslation } from 'react-i18next';

import type { CustomerReceipt } from '../../customer-flow';
import { ScreenTitle } from '../../../shared/components/ScreenTitle';
import { PlanSummary } from '../../../shared/plan/PlanSummary';
import { ReceiptStatusIcon } from './ReceiptStatusIcon';

export interface ReceiptScreenProps {
  receipt: CustomerReceipt;
  isRefreshing: boolean;
  onCheckStatus: () => void;
}

// C10's content: the status (handoff, confirmed, pending or not completed) with its next step,
// the consented plan with the item and reference, the cooling-off note, and "Check status"
// while the shop's payment can still change. Never "declined".
export function ReceiptScreen({ receipt, isRefreshing, onCheckStatus }: ReceiptScreenProps) {
  const { t } = useTranslation();
  const { plan, status } = receipt;
  const extraRows = [
    { label: t('receipt.product'), value: plan.productName },
    { label: t('receipt.reference'), value: receipt.reference },
  ];
  return (
    <>
      <div className="flex flex-col items-center gap-3 text-center" aria-live="polite">
        <ReceiptStatusIcon status={status} />
        <ScreenTitle>{t(`receipt.status.${status}.title`)}</ScreenTitle>
        <p className="text-body text-slate">
          {t(`receipt.status.${status}.body`, {
            amount: formatRupeesFromPaise(plan.regularInstallmentInPaise),
            count: plan.tenureInMonths,
          })}
        </p>
      </div>
      <PlanSummary
        heading={t('receipt.planHeading')}
        emiType={plan.emiType}
        lenderLabel={plan.lenderLabel}
        tenureInMonths={plan.tenureInMonths}
        monthlyInstallmentInPaise={plan.regularInstallmentInPaise}
        extraInTotalInPaise={plan.extraInTotalInPaise}
        totalPayableInPaise={plan.totalPayableInPaise}
      >
        {extraRows.map((row) => (
          <div key={row.label} className="flex justify-between gap-2 border-t border-border pt-2">
            <dt className="text-slate">{row.label}</dt>
            <dd className="font-bold">{row.value}</dd>
          </div>
        ))}
      </PlanSummary>
      <p className="rounded-input bg-cyan-tint p-3 text-body text-navy">
        {t('receipt.coolingOff')}
      </p>
      {status === 'PAID' ? null : (
        <Button variant="secondary" size="large" onClick={onCheckStatus} disabled={isRefreshing}>
          {t('receipt.checkStatus')}
        </Button>
      )}
    </>
  );
}
