import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import {
  getProblemMessageKey,
  useCustomerFlow,
  usePlanComparison,
  type AlternativeKind,
  type PlanAnswers,
} from '../../customer-flow';
import { CalmErrorMessage } from '../../../shared/components/CalmErrorMessage';
import { LoadingSkeleton } from '../../../shared/components/LoadingSkeleton';
import { AlternativeChips } from '../components/AlternativeChips';
import { AlternativeDetail } from '../components/AlternativeDetail';
import { AlternativesScreen } from '../components/AlternativesScreen';
import { BasePlanCard } from '../components/BasePlanCard';
import { usePlanAlternatives } from '../hooks/usePlanAlternatives';
import { describeAlternative } from '../model/describeAlternative';

export interface AlternativesContainerProps {
  answers: PlanAnswers;
}

// Fetches C6's alternatives for the selected plan and shows them; only a longer tenure (another
// offer on the same item, from C4's list) can be chosen here, the others need the shop.
export function AlternativesContainer({ answers }: AlternativesContainerProps) {
  const { t } = useTranslation();
  const { dispatch } = useCustomerFlow();
  const [selectedKind, setSelectedKind] = useState<AlternativeKind | undefined>(undefined);
  const { selectedPlan, confirmedBudgetInPaise } = answers;
  const alternativesQuery = usePlanAlternatives(selectedPlan.offerId, confirmedBudgetInPaise);
  const plansQuery = usePlanComparison(answers);
  let content;
  if (alternativesQuery.isPending) {
    content = <LoadingSkeleton accessibleLabel={t('alternatives.loading')} lineCount={5} />;
  } else if (alternativesQuery.isError) {
    content = (
      <CalmErrorMessage
        message={t(getProblemMessageKey(alternativesQuery.error))}
        retryLabel={t('common.tryAgain')}
        onRetry={() => void alternativesQuery.refetch()}
      />
    );
  } else {
    const { basePlan, alternatives, hasLowerMonthlyAlternative } = alternativesQuery.data;
    const selectedAlternative = alternatives.find(
      (alternative) => alternative.kind === selectedKind,
    );
    const longerTenurePlan = plansQuery.data?.plans.find(
      (plan) =>
        selectedAlternative?.kind === 'LONGER_TENURE' &&
        plan.offerId === selectedAlternative.offerId,
    );
    content = (
      <>
        <BasePlanCard basePlan={basePlan} monthlyBudgetInPaise={confirmedBudgetInPaise} />
        {hasLowerMonthlyAlternative ? null : (
          <p className="rounded-input bg-white p-3 text-body">{t('alternatives.nothingBetter')}</p>
        )}
        <AlternativeChips
          alternatives={alternatives}
          selectedKind={selectedKind}
          onToggleKind={(kind) => {
            setSelectedKind(kind === selectedKind ? undefined : kind);
          }}
        />
        {selectedAlternative === undefined ? null : (
          <AlternativeDetail
            alternative={selectedAlternative}
            {...describeAlternative(selectedAlternative, basePlan, longerTenurePlan, t)}
            onChoose={
              longerTenurePlan === undefined
                ? undefined
                : () => {
                    dispatch({ type: 'planSelected', plan: longerTenurePlan });
                  }
            }
          />
        )}
      </>
    );
  }
  return (
    <AlternativesScreen
      onContinue={() => {
        dispatch({ type: 'continuedToExplanation' });
      }}
      onBack={() => {
        dispatch({ type: 'wentBack' });
      }}
    >
      {content}
    </AlternativesScreen>
  );
}
