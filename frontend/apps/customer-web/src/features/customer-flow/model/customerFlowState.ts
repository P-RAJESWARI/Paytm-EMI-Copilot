import type { ComfortCheckResult, CustomerPlan } from '../api/CustomerFlowApi';

/** Every screen the customer flow can show; C8 teach-back is optional between C7 and C9. */
export type CustomerFlowStep =
  | 'welcome'
  | 'budget'
  | 'comfortConsent'
  | 'plans'
  | 'comfortDetail'
  | 'alternatives'
  | 'explanation'
  | 'teachBack'
  | 'consent'
  | 'receipt'
  | 'sessionUnavailable';

/** What the customer has answered once C3 is done: the confirmed budget and the comfort choice. */
export interface BudgetAndComfortAnswers {
  confirmedBudgetInPaise: number;
  comfortCheck: ComfortCheckResult;
}

/** The answers plus the plan the customer selected; every step from C6 on needs all three. */
export interface PlanAnswers extends BudgetAndComfortAnswers {
  selectedPlan: CustomerPlan;
}

// Pattern: Finite state machine (UI). Each step carries exactly the answers it needs, so the
// compiler (and the reducer) make consent unreachable without a confirmed budget and a plan.
export type CustomerFlowState =
  | { step: 'welcome' }
  | { step: 'budget'; previousBudgetInPaise: number | undefined }
  | { step: 'comfortConsent'; confirmedBudgetInPaise: number }
  | {
      step: 'plans';
      answers: BudgetAndComfortAnswers;
      selectedPlan: CustomerPlan | undefined;
      /** True after consent found the figures shown had changed, so C4 says so once. */
      hasShownPlanChanged: boolean;
    }
  | {
      step: 'comfortDetail';
      answers: BudgetAndComfortAnswers;
      detailPlan: CustomerPlan;
      selectedPlan: CustomerPlan | undefined;
    }
  | { step: 'alternatives'; answers: PlanAnswers }
  | { step: 'explanation'; answers: PlanAnswers }
  | { step: 'teachBack'; answers: PlanAnswers }
  | { step: 'consent'; answers: PlanAnswers }
  | { step: 'receipt'; answers: PlanAnswers }
  | { step: 'sessionUnavailable' };

/** Everything the customer (or the server's answer) can do to the flow. */
export type CustomerFlowAction =
  | { type: 'flowStarted' }
  | { type: 'budgetConfirmed'; monthlyBudgetInPaise: number }
  | { type: 'comfortCheckAnswered'; comfortCheck: ComfortCheckResult }
  | { type: 'planSelected'; plan: CustomerPlan }
  | { type: 'comfortDetailOpened'; plan: CustomerPlan }
  | { type: 'continuedToAlternatives' }
  | { type: 'continuedToExplanation' }
  | { type: 'teachBackOpened' }
  | { type: 'continuedToConsent' }
  | { type: 'consentRecorded' }
  | { type: 'shownPlanChanged' }
  | { type: 'wentBack' }
  | { type: 'sessionLost' };

/** Where every customer starts: C1 welcome. */
export const INITIAL_CUSTOMER_FLOW_STATE: CustomerFlowState = { step: 'welcome' };
