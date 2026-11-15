import { formatRupeesFromPaise } from '@emi-copilot/shared-i18n';
import { useTranslation } from 'react-i18next';

import {
  getProblemMessageKey,
  useCustomerFlow,
  type BudgetAndComfortAnswers,
  type CustomerPlan,
} from '../../customer-flow';
import { CalmErrorMessage } from '../../../shared/components/CalmErrorMessage';
import { LoadingSkeleton } from '../../../shared/components/LoadingSkeleton';
import { PlanComparisonScreen } from '../components/PlanComparisonScreen';
import { PlanList } from '../components/PlanList';
import { usePlanComparison } from '../hooks/usePlanComparison';

export interface PlanComparisonContainerProps {
  answers: BudgetAndComfortAnswers;
  selectedPlan: CustomerPlan | undefined;
  hasShownPlanChanged: boolean;
}

// Fetches C4's plans and shows the four states: a skeleton while loading, a calm retry on error,
// a note when no plan is offered, and the plans; selection and Continue go to the flow reducer.
export function PlanComparisonContainer({
  answers,
  selectedPlan,
  hasShownPlanChanged,
}: PlanComparisonContainerProps) {
  const { t } = useTranslation();
  const { session, dispatch } = useCustomerFlow();
  const plansQuery = usePlanComparison(answers);
  const comparison = plansQuery.data;
  const continueToAlternatives = () => {
    dispatch({ type: 'continuedToAlternatives' });
  };
  let content;
  if (plansQuery.isPending) {
    content = <LoadingSkeleton accessibleLabel={t('plans.loading')} lineCount={6} />;
  } else if (plansQuery.isError) {
    content = (
      <CalmErrorMessage
        message={t(getProblemMessageKey(plansQuery.error))}
        retryLabel={t('common.tryAgain')}
        onRetry={() => void plansQuery.refetch()}
      />
    );
  } else if (comparison === undefined || comparison.plans.length === 0) {
    content = <p className="rounded-card bg-white p-4 text-body">{t('plans.empty')}</p>;
  } else {
    content = (
      <PlanList
        comparison={comparison}
        selectedOfferId={selectedPlan?.offerId}
        onSelectPlan={(plan) => {
          dispatch({ type: 'planSelected', plan });
        }}
        onOpenComfortDetail={(plan) => {
          dispatch({ type: 'comfortDetailOpened', plan });
        }}
        onSeeAlternatives={continueToAlternatives}
      />
    );
  }
  return (
    <PlanComparisonScreen
      productName={session.productName}
      priceInPaise={session.priceInPaise}
      sortNote={
        comparison === undefined
          ? undefined
          : t(
              comparison.hasAnyPlanWithinBudget
                ? 'plans.sortedWithinBudget'
                : 'plans.sortedClosestToBudget',
              {
                budget: formatRupeesFromPaise(comparison.monthlyBudgetInPaise),
              },
            )
      }
      hasShownPlanChanged={hasShownPlanChanged}
      hasSelectedPlan={selectedPlan !== undefined}
      onContinue={continueToAlternatives}
      onBack={() => {
        dispatch({ type: 'wentBack' });
      }}
    >
      {content}
    </PlanComparisonScreen>
  );
}
