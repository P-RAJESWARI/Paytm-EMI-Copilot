import { useCustomerFlow, type CustomerPlan } from '../../customer-flow';
import { ExplanationScreen } from '../components/ExplanationScreen';
import { usePlanExplanation } from '../hooks/usePlanExplanation';

export interface ExplanationContainerProps {
  plan: CustomerPlan;
}

// Fetches C7's explanation of the chosen plan; a failed fetch quietly falls back to the recap.
export function ExplanationContainer({ plan }: ExplanationContainerProps) {
  const { dispatch } = useCustomerFlow();
  const explanationQuery = usePlanExplanation(plan.offerId);
  return (
    <ExplanationScreen
      plan={plan}
      explanation={explanationQuery.data}
      isLoading={explanationQuery.isPending}
      onContinue={() => {
        dispatch({ type: 'continuedToConsent' });
      }}
      onBack={() => {
        dispatch({ type: 'wentBack' });
      }}
    />
  );
}
