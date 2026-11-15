import {
  FIXTURE_COMFORT_CHECK_COMPLETED,
  FIXTURE_COMFORT_CHECK_SKIPPED,
  FIXTURE_NO_COST_PLAN,
} from '../features/customer-flow/api/fixtureCustomerFlowData';
import type {
  BudgetAndComfortAnswers,
  CustomerFlowState,
  PlanAnswers,
} from '../features/customer-flow';

/** The design answers: ₹3,000 a month and a completed comfort check. */
export const DESIGN_ANSWERS: BudgetAndComfortAnswers = {
  confirmedBudgetInPaise: 300000,
  comfortCheck: FIXTURE_COMFORT_CHECK_COMPLETED,
};

/** The design answers with plan A (no-cost, 6 months) selected. */
export const DESIGN_PLAN_ANSWERS: PlanAnswers = {
  ...DESIGN_ANSWERS,
  selectedPlan: FIXTURE_NO_COST_PLAN,
};

// Gives the C4 state for some answers, with nothing selected.
export function plansStep(
  answers: BudgetAndComfortAnswers = DESIGN_ANSWERS,
  hasShownPlanChanged = false,
): CustomerFlowState {
  return { step: 'plans', answers, selectedPlan: undefined, hasShownPlanChanged };
}

/** C4 after the customer skipped the comfort check. */
export const SKIPPED_ANSWERS: BudgetAndComfortAnswers = {
  confirmedBudgetInPaise: 300000,
  comfortCheck: FIXTURE_COMFORT_CHECK_SKIPPED,
};
