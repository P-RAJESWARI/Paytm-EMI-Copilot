import { Button } from '@emi-copilot/ui-kit';
import { useTranslation } from 'react-i18next';

import type { CustomerPlan, PlanExplanation } from '../../customer-flow';
import { LoadingSkeleton } from '../../../shared/components/LoadingSkeleton';
import { ScreenLayout } from '../../../shared/components/ScreenLayout';
import { ScreenTitle } from '../../../shared/components/ScreenTitle';
import { PlanSummary } from '../../../shared/plan/PlanSummary';
import { ExplanationText } from './ExplanationText';

export interface ExplanationScreenProps {
  plan: CustomerPlan;
  /** The explanation, or undefined while it loads or when it could not be fetched. */
  explanation: PlanExplanation | undefined;
  isLoading: boolean;
  onContinue: () => void;
  onBack: () => void;
}

// C7: the plan in plain words with its two numbers, the "standard plan details" note and the plan
// recap. If the text cannot be fetched, the recap alone carries every number: no error banner and
// nothing missing (DESIGN_SPEC section 7.6). No audio and no teach-back until Layer 4.
export function ExplanationScreen({
  plan,
  explanation,
  isLoading,
  onContinue,
  onBack,
}: ExplanationScreenProps) {
  const { t } = useTranslation();
  return (
    <ScreenLayout
      onBack={onBack}
      stepLabel={t('flow.stepOf', { current: 4, total: 4 })}
      footer={
        <Button size="large" isFullWidth onClick={onContinue}>
          {t('explanation.continue')}
        </Button>
      }
    >
      <ScreenTitle>{t('explanation.title')}</ScreenTitle>
      {isLoading ? (
        <LoadingSkeleton accessibleLabel={t('explanation.loading')} lineCount={4} />
      ) : (
        <>
          {explanation === undefined ? null : <ExplanationText explanation={explanation} />}
          <p className="text-label font-normal text-slate">{t('explanation.standardNote')}</p>
        </>
      )}
      <PlanSummary
        heading={t('explanation.recapTitle')}
        emiType={plan.emiType}
        lenderLabel={plan.lenderLabel}
        tenureInMonths={plan.tenureInMonths}
        monthlyInstallmentInPaise={plan.monthlyInstallmentInPaise}
        extraInTotalInPaise={plan.extraInTotalInPaise}
        totalPayableInPaise={plan.totalPayableInPaise}
      />
    </ScreenLayout>
  );
}
