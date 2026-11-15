import { useCustomerFlow, type CustomerPlan } from '../../customer-flow';
import { ExplanationScreen } from '../components/ExplanationScreen';
import { usePlanExplanation } from '../hooks/usePlanExplanation';
import { ListenContainer } from './ListenContainer';

export interface ExplanationContainerProps {
  plan: CustomerPlan;
}

// Fetches C7's explanation of the chosen plan; a failed fetch quietly falls back to the recap.
// Listen shows only when voice is on for this phone and the text has an id to speak.
export function ExplanationContainer({ plan }: ExplanationContainerProps) {
  const { dispatch, session } = useCustomerFlow();
  const explanationQuery = usePlanExplanation(plan.offerId);
  const explanationId = explanationQuery.data?.explanationId ?? '';
  const canListen = session.isVoiceAvailable && explanationId !== '';
  return (
    <ExplanationScreen
      plan={plan}
      explanation={explanationQuery.data}
      isLoading={explanationQuery.isPending}
      listenControl={
        canListen ? (
          <ListenContainer key={explanationId} explanationId={explanationId} />
        ) : undefined
      }
      onCheckUnderstanding={() => {
        dispatch({ type: 'teachBackOpened' });
      }}
      onContinue={() => {
        dispatch({ type: 'continuedToConsent' });
      }}
      onBack={() => {
        dispatch({ type: 'wentBack' });
      }}
    />
  );
}
