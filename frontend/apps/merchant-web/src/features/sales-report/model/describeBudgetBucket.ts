import { formatRupeesFromPaise } from '@emi-copilot/shared-i18n';
import type { TFunction } from 'i18next';

import type { BudgetBucket } from '../api/salesReportApi';

// Names a bucket's range from its API bounds: "Under ₹2,500", "₹2,500 to ₹3,000" or "₹4,000 and above".
export function describeBudgetBucketRange(t: TFunction, bucket: BudgetBucket): string {
  if (bucket.upperBoundInPaise === null) {
    return t('report.budgets.rangeFrom', {
      lower: formatRupeesFromPaise(bucket.lowerBoundInPaise),
    });
  }
  if (bucket.lowerBoundInPaise === 0) {
    return t('report.budgets.rangeUnder', {
      upper: formatRupeesFromPaise(bucket.upperBoundInPaise),
    });
  }
  return t('report.budgets.rangeBetween', {
    lower: formatRupeesFromPaise(bucket.lowerBoundInPaise),
    upper: formatRupeesFromPaise(bucket.upperBoundInPaise),
  });
}

// Names the quoted plans whose monthly amount falls in a bucket, for example "No-cost ₹3,667".
export function describeBucketPlans(t: TFunction, bucket: BudgetBucket): string[] {
  return bucket.plans.map((plan) =>
    plan.planKind === 'NO_COST'
      ? t('report.budgets.noCostPlanTag', {
          monthly: formatRupeesFromPaise(plan.monthlyInstallmentInPaise),
        })
      : t('report.budgets.lenderPlanTag', {
          lender: plan.lenderLabel,
          monthly: formatRupeesFromPaise(plan.monthlyInstallmentInPaise),
        }),
  );
}
