import { BudgetContainer } from '../features/budget';
import { ComfortConsentContainer, ComfortDetailContainer } from '../features/comfort-check';
import { SessionUnavailableScreen, useCustomerFlow } from '../features/customer-flow';
import { PlanComparisonContainer } from '../features/plan-comparison';
import { WelcomeContainer } from '../features/welcome';

// Shows the screen of the current flow step (the flow is a state machine, not a router: there is
// no URL to jump ahead with). C6 to C10 join in the next step of Layer 3.
export function CustomerFlowScreens() {
  const { state } = useCustomerFlow();
  switch (state.step) {
    case 'welcome':
      return <WelcomeContainer />;
    case 'budget':
      return <BudgetContainer previousBudgetInPaise={state.previousBudgetInPaise} />;
    case 'comfortConsent':
      return <ComfortConsentContainer />;
    case 'plans':
      return (
        <PlanComparisonContainer
          answers={state.answers}
          selectedPlan={state.selectedPlan}
          hasShownPlanChanged={state.hasShownPlanChanged}
        />
      );
    case 'comfortDetail':
      return (
        <ComfortDetailContainer plan={state.detailPlan} comfortCheck={state.answers.comfortCheck} />
      );
    case 'sessionUnavailable':
      return <SessionUnavailableScreen />;
    default:
      return null;
  }
}
