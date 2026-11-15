import { AlternativesContainer } from '../features/alternatives';
import { BudgetContainer } from '../features/budget';
import { ConsentContainer } from '../features/consent';
import { ComfortConsentContainer, ComfortDetailContainer } from '../features/comfort-check';
import { SessionUnavailableScreen, useCustomerFlow } from '../features/customer-flow';
import { ExplanationContainer } from '../features/explanation';
import { PlanComparisonContainer } from '../features/plan-comparison';
import { ReceiptContainer } from '../features/receipt';
import { WelcomeContainer } from '../features/welcome';

// Shows the screen of the current flow step (the flow is a state machine, not a router: there is
// no URL to jump ahead with).
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
    case 'alternatives':
      // Keyed by the plan, so choosing the longer tenure starts C6 afresh for that plan.
      return (
        <AlternativesContainer key={state.answers.selectedPlan.offerId} answers={state.answers} />
      );
    case 'explanation':
      return <ExplanationContainer plan={state.answers.selectedPlan} />;
    case 'consent':
      return <ConsentContainer plan={state.answers.selectedPlan} />;
    case 'receipt':
      return <ReceiptContainer />;
    case 'sessionUnavailable':
      return <SessionUnavailableScreen />;
  }
}
