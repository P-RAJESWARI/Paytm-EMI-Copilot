import type { CustomerPlan } from '../../customer-flow';

// True when the server marked one plan as costing nothing extra and a different plan as having
// the lowest monthly amount: only then is C4's trade-off note true for these plans. The UI reads
// the server's reason codes; it never compares the figures itself.
export function hasMonthlyVersusTotalTradeOff(plans: readonly CustomerPlan[]): boolean {
  const noExtraCostOfferIds = plans
    .filter((plan) => plan.reasonCodes.includes('NO_EXTRA_COST'))
    .map((plan) => plan.offerId);
  return plans.some(
    (plan) =>
      plan.reasonCodes.includes('LOWEST_MONTHLY_AMOUNT') &&
      noExtraCostOfferIds.some((offerId) => offerId !== plan.offerId),
  );
}
