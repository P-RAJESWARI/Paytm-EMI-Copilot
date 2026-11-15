import type {
  BasePlanResponse,
  ComfortCheckResponse,
  ConsentedPlanResponse,
  CustomerPlanResponse,
  CustomerPlansResponse,
  CustomerSessionResponse,
  PlanAlternativesResponse,
  PlanExplanationResponse,
} from './customerContractTypes';

// The DESIGN_SPEC section 4 sample, copied from the Phase 3A contract examples (which the engines
// computed), so the fixture and the real API agree. ADR 0020: a ₹4,000 down payment gives ₹3,000
// a month at 3,667 bp, never the mockup's ₹2,999 / 36.6%.

/** The session as screens see it: sample shop, item and session code 4821. */
export const FIXTURE_CUSTOMER_SESSION: Omit<CustomerSessionResponse, 'sessionToken'> = {
  customerSessionId: 'fixture-customer-session-4821',
  sessionCode: '4821',
  shopName: 'Ravi Electronics',
  productName: 'Example phone, 128 GB',
  priceInPaise: 2200000,
  expiresAt: '2026-11-15T10:00:00Z',
  isVoiceAvailable: true,
};

/** The QR exchange answer on the wire: the session plus its (fake) token. */
export const FIXTURE_SESSION: CustomerSessionResponse = {
  ...FIXTURE_CUSTOMER_SESSION,
  sessionToken: 'fixture-session-token',
};

/** The synthetic standard profile: inflow ₹30,000, existing EMIs ₹8,000 (labelled synthetic). */
export const FIXTURE_COMFORT_CHECK_COMPLETED: ComfortCheckResponse = {
  status: 'COMPLETED',
  isSyntheticData: true,
  monthlyInflowInPaise: 3000000,
  existingEmisInPaise: 800000,
};

export const FIXTURE_COMFORT_CHECK_SKIPPED: ComfortCheckResponse = {
  status: 'SKIPPED',
  isSyntheticData: true,
  monthlyInflowInPaise: null,
  existingEmisInPaise: null,
};

/** Plan C: cardless, 12 months, ₹2,050 a month, ₹2,600 extra; 3,350 bp (Comfortable). */
export const FIXTURE_CARDLESS_PLAN: CustomerPlanResponse = {
  position: 1,
  offerId: 'mock-offer-cardless-12m',
  lenderLabel: 'Demo cardless lender (Mock)',
  emiType: 'STANDARD',
  tenureInMonths: 12,
  monthlyInstallmentInPaise: 205000,
  lastInstallmentInPaise: 205000,
  extraInTotalInPaise: 260000,
  totalPayableInPaise: 2460000,
  priceInPaise: 2200000,
  isWithinBudget: true,
  amountAboveBudgetInPaise: 0,
  reasonCodes: ['WITHIN_BUDGET', 'LOWEST_MONTHLY_AMOUNT'],
  comfort: {
    band: 'COMFORTABLE',
    comfortRatioInBasisPoints: 3350,
    planShareInBasisPoints: 683,
    existingEmisShareInBasisPoints: 2667,
  },
};

/** Plan A: no-cost, 6 months, ₹3,667 a month, ₹0 extra, funded by Brand; 3,889 bp (Stretching). */
export const FIXTURE_NO_COST_PLAN: CustomerPlanResponse = {
  position: 2,
  offerId: 'mock-offer-no-cost-6m',
  lenderLabel: 'Brand',
  emiType: 'NO_COST',
  tenureInMonths: 6,
  monthlyInstallmentInPaise: 366667,
  lastInstallmentInPaise: 366665,
  extraInTotalInPaise: 0,
  totalPayableInPaise: 2200000,
  priceInPaise: 2200000,
  isWithinBudget: false,
  amountAboveBudgetInPaise: 66667,
  reasonCodes: ['ABOVE_BUDGET', 'NO_EXTRA_COST', 'LOWEST_EXTRA_IN_TOTAL'],
  comfort: {
    band: 'STRETCHING',
    comfortRatioInBasisPoints: 3889,
    planShareInBasisPoints: 1222,
    existingEmisShareInBasisPoints: 2667,
  },
};

/** Plan B: card, 6 months, ₹3,850 a month, ₹1,100 extra; 3,950 bp (Stretching). */
export const FIXTURE_CARD_PLAN: CustomerPlanResponse = {
  position: 3,
  offerId: 'mock-offer-card-6m',
  lenderLabel: "Your card's bank",
  emiType: 'STANDARD',
  tenureInMonths: 6,
  monthlyInstallmentInPaise: 385000,
  lastInstallmentInPaise: 385000,
  extraInTotalInPaise: 110000,
  totalPayableInPaise: 2310000,
  priceInPaise: 2200000,
  isWithinBudget: false,
  amountAboveBudgetInPaise: 85000,
  reasonCodes: ['ABOVE_BUDGET'],
  comfort: {
    band: 'STRETCHING',
    comfortRatioInBasisPoints: 3950,
    planShareInBasisPoints: 1283,
    existingEmisShareInBasisPoints: 2667,
  },
};

/** The ranking at the design budget of ₹3,000 with the comfort check done. */
export const FIXTURE_PLANS_AT_DESIGN_BUDGET: CustomerPlansResponse = {
  monthlyBudgetInPaise: 300000,
  hasAnyPlanWithinBudget: true,
  hasComfortCheck: true,
  plans: [FIXTURE_CARDLESS_PLAN, FIXTURE_NO_COST_PLAN, FIXTURE_CARD_PLAN],
};

/** The "no plan fits" ranking at ₹1,800: every plan stays listed, each above the budget. */
export const FIXTURE_PLANS_WHEN_NOTHING_FITS: CustomerPlansResponse = {
  monthlyBudgetInPaise: 180000,
  hasAnyPlanWithinBudget: false,
  hasComfortCheck: true,
  plans: [
    {
      ...FIXTURE_CARDLESS_PLAN,
      isWithinBudget: false,
      amountAboveBudgetInPaise: 25000,
      reasonCodes: ['ABOVE_BUDGET', 'LOWEST_MONTHLY_AMOUNT'],
    },
    { ...FIXTURE_NO_COST_PLAN, amountAboveBudgetInPaise: 186667 },
    { ...FIXTURE_CARD_PLAN, amountAboveBudgetInPaise: 205000 },
  ],
};

// Gives a C4 plan as the alternatives answer's base plan (the same figures, no rank or reasons).
export function toFixtureBasePlan(plan: CustomerPlanResponse): BasePlanResponse {
  return {
    offerId: plan.offerId,
    lenderLabel: plan.lenderLabel,
    emiType: plan.emiType,
    tenureInMonths: plan.tenureInMonths,
    monthlyInstallmentInPaise: plan.monthlyInstallmentInPaise,
    lastInstallmentInPaise: plan.lastInstallmentInPaise,
    extraInTotalInPaise: plan.extraInTotalInPaise,
    totalPayableInPaise: plan.totalPayableInPaise,
    priceInPaise: plan.priceInPaise,
    isWithinBudget: plan.isWithinBudget,
    amountAboveBudgetInPaise: plan.amountAboveBudgetInPaise,
    comfort: plan.comfort,
  };
}

/** The C6 answer for plan A at ₹3,000: down payment, longer tenure and cheaper model. */
export const FIXTURE_ALTERNATIVES_FOR_NO_COST_PLAN: PlanAlternativesResponse = {
  basePlan: toFixtureBasePlan(FIXTURE_NO_COST_PLAN),
  hasLowerMonthlyAlternative: true,
  alternatives: [
    {
      kind: 'DOWN_PAYMENT',
      offerId: 'mock-offer-no-cost-6m',
      tenureInMonths: 6,
      downPaymentInPaise: 400000,
      financedAmountInPaise: 1800000,
      productId: null,
      productName: null,
      priceInPaise: 2200000,
      monthlyInstallmentInPaise: 300000,
      previousMonthlyInstallmentInPaise: 366667,
      extraInTotalInPaise: 0,
      totalPayableInPaise: 1800000,
      isLowerMonthlyAmount: true,
      isWithinBudget: true,
      comfort: {
        band: 'STRETCHING',
        comfortRatioInBasisPoints: 3667,
        planShareInBasisPoints: 1000,
        existingEmisShareInBasisPoints: 2667,
      },
    },
    {
      kind: 'LONGER_TENURE',
      offerId: 'mock-offer-cardless-12m',
      tenureInMonths: 12,
      downPaymentInPaise: 0,
      financedAmountInPaise: 2200000,
      productId: null,
      productName: null,
      priceInPaise: 2200000,
      monthlyInstallmentInPaise: 205000,
      previousMonthlyInstallmentInPaise: 366667,
      extraInTotalInPaise: 260000,
      totalPayableInPaise: 2460000,
      isLowerMonthlyAmount: true,
      isWithinBudget: true,
      comfort: FIXTURE_CARDLESS_PLAN.comfort,
    },
    {
      kind: 'CHEAPER_MODEL',
      offerId: 'mock-offer-no-cost-6m',
      tenureInMonths: 6,
      downPaymentInPaise: 0,
      financedAmountInPaise: 1800000,
      productId: 'stub-product-phone-64gb',
      productName: 'Example phone, 64 GB',
      priceInPaise: 1800000,
      monthlyInstallmentInPaise: 300000,
      previousMonthlyInstallmentInPaise: 366667,
      extraInTotalInPaise: 0,
      totalPayableInPaise: 1800000,
      isLowerMonthlyAmount: true,
      isWithinBudget: true,
      comfort: {
        band: 'STRETCHING',
        comfortRatioInBasisPoints: 3667,
        planShareInBasisPoints: 1000,
        existingEmisShareInBasisPoints: 2667,
      },
    },
  ],
};

/** The fixed demo OTP the fixture accepts (never a real code). */
export const FIXTURE_OTP = '123456';

/** The receipt reference from the design sample. */
export const FIXTURE_RECEIPT_REFERENCE = 'EMI-2611-0042';

// Gives the consented plan snapshot of a C4 plan, as the server stores it for the sample item.
export function buildFixtureConsentedPlan(plan: CustomerPlanResponse): ConsentedPlanResponse {
  return {
    offerId: plan.offerId,
    lenderLabel: plan.lenderLabel,
    emiType: plan.emiType,
    tenureInMonths: plan.tenureInMonths,
    regularInstallmentInPaise: plan.monthlyInstallmentInPaise,
    lastInstallmentInPaise: plan.lastInstallmentInPaise,
    extraInTotalInPaise: plan.extraInTotalInPaise,
    totalPayableInPaise: plan.totalPayableInPaise,
    priceInPaise: plan.priceInPaise,
    productId: 'stub-product-phone-128gb',
    productName: FIXTURE_SESSION.productName,
    downPaymentInPaise: 0,
    financedAmountInPaise: plan.priceInPaise,
  };
}

/** Template explanations of the three sample plans, as the server's template would write them. */
export const FIXTURE_EXPLANATION_TEXTS: Record<string, Record<'en' | 'ta', string>> = {
  'mock-offer-no-cost-6m': {
    en: 'No-cost EMI from Brand: you pay ₹3,667 each month for 6 months. You pay ₹0 extra in total, so you pay ₹22,000 in all, the same as the price.',
    ta: 'Brand வழங்கும் கட்டணமில்லா EMI: 6 மாதங்களுக்கு ஒவ்வொரு மாதமும் ₹3,667 செலுத்துவீர்கள். மொத்தக் கூடுதல் ₹0, எனவே மொத்தம் ₹22,000, விலைக்குச் சமம்.',
  },
  'mock-offer-card-6m': {
    en: "EMI from Your card's bank: you pay ₹3,850 each month for 6 months. You pay ₹1,100 extra in total, so you pay ₹23,100 in all.",
    ta: "Your card's bank வழங்கும் EMI: 6 மாதங்களுக்கு ஒவ்வொரு மாதமும் ₹3,850 செலுத்துவீர்கள். மொத்தக் கூடுதல் ₹1,100, எனவே மொத்தம் ₹23,100.",
  },
  'mock-offer-cardless-12m': {
    en: 'EMI from Demo cardless lender (Mock): you pay ₹2,050 each month for 12 months. You pay ₹2,600 extra in total, so you pay ₹24,600 in all.',
    ta: 'Demo cardless lender (Mock) வழங்கும் EMI: 12 மாதங்களுக்கு ஒவ்வொரு மாதமும் ₹2,050 செலுத்துவீர்கள். மொத்தக் கூடுதல் ₹2,600, எனவே மொத்தம் ₹24,600.',
  },
};

/** The fixture's one explanation id, so C7 can offer Listen against the fixture too. */
export const FIXTURE_EXPLANATION_ID = 'fixture-explanation-1';

// Gives the explanation of one sample plan in the asked language, labelled as audited AI text so
// the fixture shows the Layer 4 note (the words are the template's; the figures are the plan's).
export function buildFixtureExplanation(
  plan: CustomerPlanResponse,
  language: 'en' | 'ta',
): PlanExplanationResponse {
  const texts = FIXTURE_EXPLANATION_TEXTS[plan.offerId];
  return {
    explanationId: FIXTURE_EXPLANATION_ID,
    text: texts === undefined ? '' : texts[language],
    language,
    source: 'AI_AUDITED',
    highlightedAmounts: [
      { kind: 'MONTHLY_INSTALLMENT', amountInPaise: plan.monthlyInstallmentInPaise },
      { kind: 'EXTRA_IN_TOTAL', amountInPaise: plan.extraInTotalInPaise },
    ],
  };
}
