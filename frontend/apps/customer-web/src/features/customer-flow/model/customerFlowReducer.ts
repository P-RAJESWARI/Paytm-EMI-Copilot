import type {
  BudgetAndComfortAnswers,
  CustomerFlowAction,
  CustomerFlowState,
  PlanAnswers,
} from './customerFlowState';

// Keeps the budget and comfort answers of a later step, dropping the selected plan.
function withoutSelectedPlan(answers: PlanAnswers): BudgetAndComfortAnswers {
  return {
    confirmedBudgetInPaise: answers.confirmedBudgetInPaise,
    comfortCheck: answers.comfortCheck,
  };
}

// Moves one step back the way the customer came; C1, C10 and the session screen stay put.
function goBack(state: CustomerFlowState): CustomerFlowState {
  switch (state.step) {
    case 'budget':
      return { step: 'welcome' };
    case 'comfortConsent':
      return { step: 'budget', previousBudgetInPaise: state.confirmedBudgetInPaise };
    case 'plans':
      return {
        step: 'comfortConsent',
        confirmedBudgetInPaise: state.answers.confirmedBudgetInPaise,
      };
    case 'comfortDetail':
      return {
        step: 'plans',
        answers: state.answers,
        selectedPlan: state.selectedPlan,
        hasShownPlanChanged: false,
      };
    case 'alternatives':
      return {
        step: 'plans',
        answers: withoutSelectedPlan(state.answers),
        selectedPlan: state.answers.selectedPlan,
        hasShownPlanChanged: false,
      };
    case 'explanation':
      return { step: 'alternatives', answers: state.answers };
    case 'teachBack':
      return { step: 'explanation', answers: state.answers };
    case 'consent':
      return { step: 'explanation', answers: state.answers };
    default:
      return state;
  }
}

// Selects a plan on C4, or switches to the longer-tenure plan on C6; elsewhere it does nothing.
function selectPlan(
  state: CustomerFlowState,
  action: Extract<CustomerFlowAction, { type: 'planSelected' }>,
): CustomerFlowState {
  if (state.step === 'plans') return { ...state, selectedPlan: action.plan };
  if (state.step === 'alternatives') {
    return { step: 'alternatives', answers: { ...state.answers, selectedPlan: action.plan } };
  }
  return state;
}

// Opens C5 for a plan that has a comfort result; skipped checks have no detail to show.
function openComfortDetail(
  state: CustomerFlowState,
  action: Extract<CustomerFlowAction, { type: 'comfortDetailOpened' }>,
): CustomerFlowState {
  if (state.step !== 'plans' || action.plan.comfort === null) return state;
  return {
    step: 'comfortDetail',
    answers: state.answers,
    detailPlan: action.plan,
    selectedPlan: state.selectedPlan,
  };
}

// Moves forward from C6, C7, C8 and C9; each move needs the step before it, so no step is
// skipped. C8 is optional: C7 goes to C9 directly or through C8.
function continueForward(
  state: CustomerFlowState,
  action: Extract<
    CustomerFlowAction,
    {
      type: 'continuedToExplanation' | 'teachBackOpened' | 'continuedToConsent' | 'consentRecorded';
    }
  >,
): CustomerFlowState {
  if (action.type === 'continuedToExplanation' && state.step === 'alternatives') {
    return { step: 'explanation', answers: state.answers };
  }
  if (action.type === 'teachBackOpened' && state.step === 'explanation') {
    return { step: 'teachBack', answers: state.answers };
  }
  if (
    action.type === 'continuedToConsent' &&
    (state.step === 'explanation' || state.step === 'teachBack')
  ) {
    return { step: 'consent', answers: state.answers };
  }
  if (action.type === 'consentRecorded' && state.step === 'consent') {
    return { step: 'receipt', answers: state.answers };
  }
  return state;
}

// Pattern: Finite state machine (UI). The customer flow's only transition function: any action
// that does not fit the current step leaves the state unchanged, so screens cannot jump ahead.
export function customerFlowReducer(
  state: CustomerFlowState,
  action: CustomerFlowAction,
): CustomerFlowState {
  switch (action.type) {
    case 'sessionLost':
      return { step: 'sessionUnavailable' };
    case 'wentBack':
      return goBack(state);
    case 'flowStarted':
      return state.step === 'welcome'
        ? { step: 'budget', previousBudgetInPaise: undefined }
        : state;
    case 'budgetConfirmed':
      return state.step === 'budget'
        ? { step: 'comfortConsent', confirmedBudgetInPaise: action.monthlyBudgetInPaise }
        : state;
    case 'comfortCheckAnswered':
      return state.step === 'comfortConsent'
        ? {
            step: 'plans',
            answers: {
              confirmedBudgetInPaise: state.confirmedBudgetInPaise,
              comfortCheck: action.comfortCheck,
            },
            selectedPlan: undefined,
            hasShownPlanChanged: false,
          }
        : state;
    case 'planSelected':
      return selectPlan(state, action);
    case 'comfortDetailOpened':
      return openComfortDetail(state, action);
    case 'continuedToAlternatives':
      return state.step === 'plans' && state.selectedPlan !== undefined
        ? { step: 'alternatives', answers: { ...state.answers, selectedPlan: state.selectedPlan } }
        : state;
    case 'shownPlanChanged':
      return state.step === 'consent'
        ? {
            step: 'plans',
            answers: withoutSelectedPlan(state.answers),
            selectedPlan: undefined,
            hasShownPlanChanged: true,
          }
        : state;
    default:
      return continueForward(state, action);
  }
}
