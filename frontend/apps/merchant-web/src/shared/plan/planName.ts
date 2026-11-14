import type { ApiSchemas } from '@emi-copilot/api-client';

export type PlanKind = ApiSchemas['EmiType'];

const PLAN_NAME_KEY_BY_KIND: Record<PlanKind, string> = {
  NO_COST: 'plan.name.NO_COST',
  STANDARD: 'plan.name.STANDARD',
};

// Gives the translation key of a plan's plain name ("No-cost EMI" or "EMI") from its kind.
export function getPlanNameKey(planKind: PlanKind): string {
  return PLAN_NAME_KEY_BY_KIND[planKind];
}
