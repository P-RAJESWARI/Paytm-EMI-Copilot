import type { ApiSchemas } from '@emi-copilot/api-client';

// The DESIGN_SPEC section 4 week, as the report endpoints answer it for THIS_WEEK.

export const TEST_FUNNEL_REPORT: ApiSchemas['FunnelReportResponse'] = {
  range: 'THIS_WEEK',
  periodStartDate: '2026-11-09',
  periodEndDate: '2026-11-15',
  stages: [
    { stage: 'STARTED', customerCount: 120, isSuppressed: false },
    { stage: 'BUDGET_TOLD', customerCount: 96, isSuppressed: false },
    { stage: 'PLANS_VIEWED', customerCount: 88, isSuppressed: false },
    { stage: 'AGREED', customerCount: 51, isSuppressed: false },
    { stage: 'PAID', customerCount: 44, isSuppressed: false },
  ],
  biggestDrop: { afterStage: 'PLANS_VIEWED', customerCount: 37, isSuppressed: false },
};

// Builds a funnel where every stage has the given count (0 gives the empty state).
export function buildUniformFunnelReport(
  range: ApiSchemas['ReportingRange'],
  customerCount: number,
): ApiSchemas['FunnelReportResponse'] {
  return {
    ...TEST_FUNNEL_REPORT,
    range,
    stages: TEST_FUNNEL_REPORT.stages.map((stage) => ({ ...stage, customerCount })),
    biggestDrop: null,
  };
}

export const TEST_MISSED_SALES_REPORT: ApiSchemas['MissedSalesReportResponse'] = {
  range: 'THIS_WEEK',
  periodStartDate: '2026-11-09',
  periodEndDate: '2026-11-15',
  missedCustomerCount: 12,
  isSuppressed: false,
  budgetCeilingInPaise: 300000,
  productInsight: {
    productId: 'product-128',
    productName: 'Example phone, 128 GB',
    lowestNoExtraCostMonthlyInPaise: 366667,
    cheapestPlanUnderCeiling: { monthlyInstallmentInPaise: 205000, extraInTotalInPaise: 260000 },
  },
  budgetTotalCustomerCount: 96,
  areBudgetBucketsHidden: false,
  budgetBuckets: [
    {
      lowerBoundInPaise: 0,
      upperBoundInPaise: 250000,
      customerCount: 5,
      isSuppressed: false,
      isUnderCeiling: true,
      plans: [
        {
          planKind: 'STANDARD',
          lenderLabel: 'Demo cardless lender (Mock)',
          monthlyInstallmentInPaise: 205000,
        },
      ],
    },
    {
      lowerBoundInPaise: 250000,
      upperBoundInPaise: 300000,
      customerCount: 7,
      isSuppressed: false,
      isUnderCeiling: true,
      plans: [],
    },
    {
      lowerBoundInPaise: 300000,
      upperBoundInPaise: 350000,
      customerCount: 14,
      isSuppressed: false,
      isUnderCeiling: false,
      plans: [],
    },
    {
      lowerBoundInPaise: 350000,
      upperBoundInPaise: 400000,
      customerCount: 21,
      isSuppressed: false,
      isUnderCeiling: false,
      plans: [
        { planKind: 'NO_COST', lenderLabel: 'Brand', monthlyInstallmentInPaise: 366667 },
        {
          planKind: 'STANDARD',
          lenderLabel: "Your card's bank",
          monthlyInstallmentInPaise: 385000,
        },
      ],
    },
    {
      lowerBoundInPaise: 400000,
      upperBoundInPaise: null,
      customerCount: 49,
      isSuppressed: false,
      isUnderCeiling: false,
      plans: [],
    },
  ],
};

export const TEST_SUGGESTED_ACTIONS: ApiSchemas['SuggestedActionsResponse'] = {
  actions: [
    {
      actionCode: 'ASK_BRAND_FOR_LONGER_NO_COST_PLAN',
      parameters: {
        productId: 'product-128',
        productName: 'Example phone, 128 GB',
        currentNoCostTenureInMonths: 6,
        currentNoCostMonthlyInPaise: 366667,
        suggestedTenures: [
          { tenureInMonths: 9, monthlyInstallmentInPaise: 244444 },
          { tenureInMonths: 12, monthlyInstallmentInPaise: 183333 },
        ],
        missedCustomerCount: 12,
        isMissedCustomerCountSuppressed: false,
        budgetCeilingInPaise: 300000,
      },
    },
    {
      actionCode: 'KEEP_CHEAPER_MODEL_READY',
      parameters: {
        productId: 'product-64',
        productName: 'Example phone, 64 GB',
        listPriceInPaise: 1800000,
        monthlyInstallmentInPaise: 300000,
        tenureInMonths: 6,
      },
    },
  ],
};

export const TEST_MONEY_DUE: ApiSchemas['MoneyDueResponse'] = {
  totalDueInPaise: 18400000,
  nextExpectedDate: '2027-01-13',
  batches: [
    {
      batchNumber: 1,
      saleCount: 18,
      amountInPaise: 7200000,
      expectedDate: '2027-01-13',
      status: 'CLAIM_FILED',
    },
    {
      batchNumber: 2,
      saleCount: 16,
      amountInPaise: 6400000,
      expectedDate: '2027-01-28',
      status: 'WAITING_FOR_BRAND',
    },
    {
      batchNumber: 3,
      saleCount: 10,
      amountInPaise: 4800000,
      expectedDate: '2027-02-12',
      status: 'NOT_YET_DUE',
    },
  ],
};

export const TEST_WEEKLY_MESSAGE: ApiSchemas['WeeklyMessageResponse'] = {
  periodStartDate: '2026-11-09',
  periodEndDate: '2026-11-15',
  source: 'TEMPLATE',
  messages: {
    en: {
      title: 'Your EMI sales, 9 to 15 November',
      paragraphs: [
        '44 of 120 customers bought on EMI. The biggest drop was after seeing the plans.',
        '12 customers wanted under ₹3,000 a month with nothing extra, and no plan fit.',
      ],
    },
    ta: {
      title: 'உங்கள் EMI விற்பனை, 9 முதல் 15 நவம்பர்',
      paragraphs: ['120 வாடிக்கையாளர்களில் 44 பேர் EMI-யில் வாங்கினர்.'],
    },
  },
  isSent: false,
  sentAt: null,
};
