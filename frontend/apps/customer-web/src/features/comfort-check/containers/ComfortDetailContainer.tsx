import { useCustomerFlow, type ComfortCheckResult, type CustomerPlan } from '../../customer-flow';
import { ComfortDetailScreen } from '../components/ComfortDetailScreen';

export interface ComfortDetailContainerProps {
  plan: CustomerPlan;
  comfortCheck: ComfortCheckResult;
}

// Shows C5 for the plan opened from C4; back returns to the plans with the selection kept.
// The reducer opens C5 only for a plan with a comfort result, so a missing one shows nothing.
export function ComfortDetailContainer({ plan, comfortCheck }: ComfortDetailContainerProps) {
  const { dispatch } = useCustomerFlow();
  const { comfort } = plan;
  if (comfort === null) return null;
  return (
    <ComfortDetailScreen
      plan={{ ...plan, comfort }}
      comfortCheck={comfortCheck}
      onBack={() => {
        dispatch({ type: 'wentBack' });
      }}
    />
  );
}
