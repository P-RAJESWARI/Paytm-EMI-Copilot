import { Button } from '@emi-copilot/ui-kit';
import type { ReactNode } from 'react';
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
  /** The Listen control when voice is on and the text has an id; undefined hides it. */
  listenControl?: ReactNode;
  onCheckUnderstanding: () => void;
  onContinue: () => void;
  onBack: () => void;
}

// C7: the plan in plain words with its two numbers, Listen (when voice is on), the "written by
// AI" or "standard plan details" note, the plan recap and "Check my understanding" (C8). If the
// text cannot be fetched, the recap alone carries every number: no error banner and nothing
// missing (DESIGN_SPEC section 7.6).
export function ExplanationScreen({
  plan,
  explanation,
  isLoading,
  listenControl,
  onCheckUnderstanding,
  onContinue,
  onBack,
}: ExplanationScreenProps) {
  const { t } = useTranslation();
  const isWrittenByAi = explanation?.source === 'AI_AUDITED';
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
          {listenControl}
          {explanation === undefined ? null : <ExplanationText explanation={explanation} />}
          <p className="text-label font-normal text-slate">
            {isWrittenByAi ? t('explanation.aiNote') : t('explanation.standardNote')}
          </p>
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
      <Button variant="quiet" className="self-start" onClick={onCheckUnderstanding}>
        {t('explanation.checkUnderstanding')}
      </Button>
    </ScreenLayout>
  );
}
