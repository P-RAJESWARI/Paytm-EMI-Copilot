import { formatRupeesFromPaise } from '@emi-copilot/shared-i18n';
import { useTranslation } from 'react-i18next';

import type { CustomerPlan, PlanComparison } from '../../customer-flow';
import { hasMonthlyVersusTotalTradeOff } from '../model/hasMonthlyVersusTotalTradeOff';
import { NoPlanFitsNotice } from './NoPlanFitsNotice';
import { PlanCard } from './PlanCard';

export interface PlanListProps {
  comparison: PlanComparison;
  selectedOfferId: string | undefined;
  onSelectPlan: (plan: CustomerPlan) => void;
  onOpenComfortDetail: (plan: CustomerPlan) => void;
  onSeeAlternatives: () => void;
}

const PLAN_RADIO_GROUP_NAME = 'customer-plan';

// C4's plans in the server's order, every one of them (no plan is ever hidden): the no-fit note
// when nothing is within the budget, the trade-off note when it holds, then one card per plan.
export function PlanList({
  comparison,
  selectedOfferId,
  onSelectPlan,
  onOpenComfortDetail,
  onSeeAlternatives,
}: PlanListProps) {
  const { t } = useTranslation();
  return (
    <>
      {comparison.hasAnyPlanWithinBudget ? null : (
        <NoPlanFitsNotice
          formattedBudget={formatRupeesFromPaise(comparison.monthlyBudgetInPaise)}
          onSeeAlternatives={selectedOfferId === undefined ? undefined : onSeeAlternatives}
        />
      )}
      {comparison.hasAnyPlanWithinBudget && hasMonthlyVersusTotalTradeOff(comparison.plans) ? (
        <p className="rounded-input bg-white p-3 text-body text-ink-muted">{t('plans.tradeOff')}</p>
      ) : null}
      <fieldset className="m-0 flex flex-col gap-4 border-0 p-0">
        <legend className="sr-only">{t('plans.title')}</legend>
        {comparison.plans.map((plan) => (
          <PlanCard
            key={plan.offerId}
            plan={plan}
            radioGroupName={PLAN_RADIO_GROUP_NAME}
            isSelected={plan.offerId === selectedOfferId}
            onSelect={() => {
              onSelectPlan(plan);
            }}
            onOpenComfortDetail={() => {
              onOpenComfortDetail(plan);
            }}
          />
        ))}
      </fieldset>
    </>
  );
}
