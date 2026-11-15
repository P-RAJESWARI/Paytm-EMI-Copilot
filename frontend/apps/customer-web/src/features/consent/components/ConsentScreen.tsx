import { Button } from '@emi-copilot/ui-kit';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import type { CustomerPlan } from '../../customer-flow';
import { CalmErrorMessage } from '../../../shared/components/CalmErrorMessage';
import { ScreenLayout } from '../../../shared/components/ScreenLayout';
import { ScreenTitle } from '../../../shared/components/ScreenTitle';
import { PlanSummary } from '../../../shared/plan/PlanSummary';

export interface ConsentScreenProps {
  plan: CustomerPlan;
  /** The OTP block. */
  otpEntry: ReactNode;
  canConfirm: boolean;
  /** A calm, translated message when consent failed for a reason other than the OTP. */
  consentErrorMessage: string | undefined;
  onConfirm: () => void;
  onBack: () => void;
}

// C9: the plan summary (monthly, extra in total, tenure, total), the OTP, the cooling-off note
// (placeholder wording until the lender confirms it), the agreement line and Confirm.
export function ConsentScreen({
  plan,
  otpEntry,
  canConfirm,
  consentErrorMessage,
  onConfirm,
  onBack,
}: ConsentScreenProps) {
  const { t } = useTranslation();
  return (
    <ScreenLayout
      onBack={onBack}
      stepLabel={t('flow.confirmStep')}
      footer={
        <Button size="large" isFullWidth onClick={onConfirm} disabled={!canConfirm}>
          {t('consent.confirm')}
        </Button>
      }
    >
      <ScreenTitle>{t('consent.title')}</ScreenTitle>
      <PlanSummary
        heading={t('consent.summaryHeading')}
        emiType={plan.emiType}
        lenderLabel={plan.lenderLabel}
        tenureInMonths={plan.tenureInMonths}
        monthlyInstallmentInPaise={plan.monthlyInstallmentInPaise}
        extraInTotalInPaise={plan.extraInTotalInPaise}
        totalPayableInPaise={plan.totalPayableInPaise}
      />
      {otpEntry}
      <p className="rounded-input bg-cyan-tint p-3 text-body text-navy">
        {t('consent.coolingOff')}
      </p>
      <p className="text-label font-normal text-ink-muted">{t('consent.agreement')}</p>
      {consentErrorMessage === undefined ? null : (
        <CalmErrorMessage message={consentErrorMessage} />
      )}
    </ScreenLayout>
  );
}
