import { describe, expect, it } from 'vitest';

import {
  FIXTURE_CARD_PLAN,
  FIXTURE_CARDLESS_PLAN,
  FIXTURE_COMFORT_CHECK_COMPLETED,
  FIXTURE_COMFORT_CHECK_SKIPPED,
  FIXTURE_NO_COST_PLAN,
} from '../api/fixtureCustomerFlowData';
import { customerFlowReducer } from './customerFlowReducer';
import {
  INITIAL_CUSTOMER_FLOW_STATE,
  type BudgetAndComfortAnswers,
  type CustomerFlowAction,
  type CustomerFlowState,
  type PlanAnswers,
} from './customerFlowState';

const DESIGN_BUDGET_IN_PAISE = 300000;
const ANSWERS: BudgetAndComfortAnswers = {
  confirmedBudgetInPaise: DESIGN_BUDGET_IN_PAISE,
  comfortCheck: FIXTURE_COMFORT_CHECK_COMPLETED,
};
const PLAN_ANSWERS: PlanAnswers = { ...ANSWERS, selectedPlan: FIXTURE_NO_COST_PLAN };

const WELCOME: CustomerFlowState = INITIAL_CUSTOMER_FLOW_STATE;
const BUDGET: CustomerFlowState = { step: 'budget', previousBudgetInPaise: undefined };
const COMFORT_CONSENT: CustomerFlowState = {
  step: 'comfortConsent',
  confirmedBudgetInPaise: DESIGN_BUDGET_IN_PAISE,
};
const PLANS_WITHOUT_SELECTION: CustomerFlowState = {
  step: 'plans',
  answers: ANSWERS,
  selectedPlan: undefined,
  hasShownPlanChanged: false,
};
const PLANS_WITH_SELECTION: CustomerFlowState = {
  ...PLANS_WITHOUT_SELECTION,
  selectedPlan: FIXTURE_NO_COST_PLAN,
};
const COMFORT_DETAIL: CustomerFlowState = {
  step: 'comfortDetail',
  answers: ANSWERS,
  detailPlan: FIXTURE_CARD_PLAN,
  selectedPlan: FIXTURE_NO_COST_PLAN,
};
const ALTERNATIVES: CustomerFlowState = { step: 'alternatives', answers: PLAN_ANSWERS };
const EXPLANATION: CustomerFlowState = { step: 'explanation', answers: PLAN_ANSWERS };
const CONSENT: CustomerFlowState = { step: 'consent', answers: PLAN_ANSWERS };
const RECEIPT: CustomerFlowState = { step: 'receipt', answers: PLAN_ANSWERS };
const SESSION_UNAVAILABLE: CustomerFlowState = { step: 'sessionUnavailable' };

const EVERY_STATE: readonly CustomerFlowState[] = [
  WELCOME,
  BUDGET,
  COMFORT_CONSENT,
  PLANS_WITHOUT_SELECTION,
  PLANS_WITH_SELECTION,
  COMFORT_DETAIL,
  ALTERNATIVES,
  EXPLANATION,
  CONSENT,
  RECEIPT,
  SESSION_UNAVAILABLE,
];

// Applies a list of actions in order, from the welcome screen unless told otherwise.
function applyActions(
  actions: readonly CustomerFlowAction[],
  startState: CustomerFlowState = WELCOME,
): CustomerFlowState {
  return actions.reduce(customerFlowReducer, startState);
}

// Lists the states in which an action is allowed to change anything.
function statesThatAccept(action: CustomerFlowAction): CustomerFlowState[] {
  return EVERY_STATE.filter((state) => customerFlowReducer(state, action) !== state);
}

describe('customerFlowReducer: the happy path', () => {
  it('walks C1, C2, C3, C4, C6, C7, C9 and C10 with every answer carried along', () => {
    const finalState = applyActions([
      { type: 'flowStarted' },
      { type: 'budgetConfirmed', monthlyBudgetInPaise: DESIGN_BUDGET_IN_PAISE },
      { type: 'comfortCheckAnswered', comfortCheck: FIXTURE_COMFORT_CHECK_COMPLETED },
      { type: 'planSelected', plan: FIXTURE_NO_COST_PLAN },
      { type: 'continuedToAlternatives' },
      { type: 'continuedToExplanation' },
      { type: 'continuedToConsent' },
      { type: 'consentRecorded' },
    ]);

    expect(finalState).toEqual(RECEIPT);
  });

  it('starts at the welcome screen', () => {
    expect(INITIAL_CUSTOMER_FLOW_STATE).toEqual({ step: 'welcome' });
  });
});

describe('customerFlowReducer: consent is unreachable without a budget and a plan', () => {
  it.each([
    ['continuedToConsent', { type: 'continuedToConsent' }, [EXPLANATION]],
    ['consentRecorded', { type: 'consentRecorded' }, [CONSENT]],
    ['continuedToExplanation', { type: 'continuedToExplanation' }, [ALTERNATIVES]],
    ['continuedToAlternatives', { type: 'continuedToAlternatives' }, [PLANS_WITH_SELECTION]],
    ['flowStarted', { type: 'flowStarted' }, [WELCOME]],
    ['shownPlanChanged', { type: 'shownPlanChanged' }, [CONSENT]],
  ] as const)('%s changes only the step it belongs to', (_name, action, acceptingStates) => {
    expect(statesThatAccept(action)).toEqual(acceptingStates);
  });

  it('does not leave C4 without a selected plan', () => {
    expect(customerFlowReducer(PLANS_WITHOUT_SELECTION, { type: 'continuedToAlternatives' })).toBe(
      PLANS_WITHOUT_SELECTION,
    );
  });

  it('accepts a budget only on C2 and a comfort answer only on C3', () => {
    const budgetAction = { type: 'budgetConfirmed', monthlyBudgetInPaise: 180000 } as const;
    const comfortAction = {
      type: 'comfortCheckAnswered',
      comfortCheck: FIXTURE_COMFORT_CHECK_SKIPPED,
    } as const;

    expect(statesThatAccept(budgetAction)).toEqual([BUDGET]);
    expect(customerFlowReducer(BUDGET, budgetAction)).toEqual({
      step: 'comfortConsent',
      confirmedBudgetInPaise: 180000,
    });
    expect(statesThatAccept(comfortAction)).toEqual([COMFORT_CONSENT]);
    expect(customerFlowReducer(COMFORT_CONSENT, comfortAction)).toEqual({
      ...PLANS_WITHOUT_SELECTION,
      answers: { ...ANSWERS, comfortCheck: FIXTURE_COMFORT_CHECK_SKIPPED },
    });
  });
});

describe('customerFlowReducer: choosing plans', () => {
  it('selects a plan on C4 and switches the plan on C6 (longer tenure)', () => {
    const selectCardless = { type: 'planSelected', plan: FIXTURE_CARDLESS_PLAN } as const;

    expect(customerFlowReducer(PLANS_WITHOUT_SELECTION, selectCardless)).toEqual({
      ...PLANS_WITHOUT_SELECTION,
      selectedPlan: FIXTURE_CARDLESS_PLAN,
    });
    expect(customerFlowReducer(ALTERNATIVES, selectCardless)).toEqual({
      step: 'alternatives',
      answers: { ...PLAN_ANSWERS, selectedPlan: FIXTURE_CARDLESS_PLAN },
    });
    expect(statesThatAccept(selectCardless)).toEqual([
      PLANS_WITHOUT_SELECTION,
      PLANS_WITH_SELECTION,
      ALTERNATIVES,
    ]);
  });

  it('opens C5 from C4 only for a plan with a comfort result, keeping the selection', () => {
    const openCardDetail = { type: 'comfortDetailOpened', plan: FIXTURE_CARD_PLAN } as const;
    const skippedPlan = { ...FIXTURE_CARD_PLAN, comfort: null };

    expect(customerFlowReducer(PLANS_WITH_SELECTION, openCardDetail)).toEqual(COMFORT_DETAIL);
    expect(
      customerFlowReducer(PLANS_WITH_SELECTION, { type: 'comfortDetailOpened', plan: skippedPlan }),
    ).toBe(PLANS_WITH_SELECTION);
    expect(statesThatAccept(openCardDetail)).toEqual([
      PLANS_WITHOUT_SELECTION,
      PLANS_WITH_SELECTION,
    ]);
  });

  it('sends the customer back to C4 with a notice and no selection when the plan changed', () => {
    expect(customerFlowReducer(CONSENT, { type: 'shownPlanChanged' })).toEqual({
      ...PLANS_WITHOUT_SELECTION,
      hasShownPlanChanged: true,
    });
  });
});

describe('customerFlowReducer: going back', () => {
  it.each([
    ['C2 to C1', BUDGET, WELCOME],
    [
      'C3 to C2 with the budget kept',
      COMFORT_CONSENT,
      { step: 'budget', previousBudgetInPaise: DESIGN_BUDGET_IN_PAISE },
    ],
    ['C4 to C3', PLANS_WITH_SELECTION, COMFORT_CONSENT],
    ['C5 to C4 with the selection kept', COMFORT_DETAIL, PLANS_WITH_SELECTION],
    ['C6 to C4 with the selection kept', ALTERNATIVES, PLANS_WITH_SELECTION],
    ['C7 to C6', EXPLANATION, ALTERNATIVES],
    ['C9 to C7', CONSENT, EXPLANATION],
  ] as const)('goes %s', (_name, fromState, toState) => {
    expect(customerFlowReducer(fromState, { type: 'wentBack' })).toEqual(toState);
  });

  it.each([WELCOME, RECEIPT, SESSION_UNAVAILABLE])(
    'stays on %o, which has no way back',
    (state) => {
      expect(customerFlowReducer(state, { type: 'wentBack' })).toBe(state);
    },
  );
});

describe('customerFlowReducer: a lost session', () => {
  it.each(EVERY_STATE)('ends the flow on the session screen from %o', (state) => {
    expect(customerFlowReducer(state, { type: 'sessionLost' })).toEqual(SESSION_UNAVAILABLE);
  });
});
