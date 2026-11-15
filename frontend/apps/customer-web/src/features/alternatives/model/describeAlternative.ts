import { formatRupeesFromPaise } from '@emi-copilot/shared-i18n';
import type { TFunction } from 'i18next';

import type { BasePlanResponse, CustomerPlan, PlanAlternative } from '../../customer-flow';
import { getPlanNameKey } from '../../../shared/plan/planWording';

/** The translated name and note of one C6 alternative. */
export interface AlternativeDescription {
  name: string;
  note: string;
}

// Words one alternative for C6 from the server's figures: the down payment on the same plan, the
// longer-tenure plan by its own name, or the cheaper model with its price. Wording only.
export function describeAlternative(
  alternative: PlanAlternative,
  basePlan: BasePlanResponse,
  longerTenurePlan: CustomerPlan | undefined,
  translate: TFunction,
): AlternativeDescription {
  const basePlanName = translate(getPlanNameKey(basePlan.emiType));
  const basePlanNameWithTenure = translate('plan.nameWithTenure', {
    planName: basePlanName,
    count: alternative.tenureInMonths,
  });
  if (alternative.kind === 'DOWN_PAYMENT') {
    return {
      name: translate('alternatives.downPaymentName', {
        planName: basePlanNameWithTenure,
        amount: formatRupeesFromPaise(alternative.downPaymentInPaise),
      }),
      note: translate('alternatives.downPaymentNote', {
        downPayment: formatRupeesFromPaise(alternative.downPaymentInPaise),
        monthly: formatRupeesFromPaise(alternative.monthlyInstallmentInPaise),
      }),
    };
  }
  if (alternative.kind === 'CHEAPER_MODEL') {
    return {
      name: translate('alternatives.cheaperModelName', {
        productName: alternative.productName ?? '',
        price: formatRupeesFromPaise(alternative.priceInPaise),
      }),
      note: translate('alternatives.cheaperModelNote', { planName: basePlanNameWithTenure }),
    };
  }
  const longerPlanName =
    longerTenurePlan === undefined
      ? translate('alternatives.chip.LONGER_TENURE')
      : translate(getPlanNameKey(longerTenurePlan.emiType));
  return {
    name: translate('plan.nameWithTenure', {
      planName: longerPlanName,
      count: alternative.tenureInMonths,
    }),
    note: translate('alternatives.longerTenureNote', {
      extra: formatRupeesFromPaise(alternative.extraInTotalInPaise),
    }),
  };
}
