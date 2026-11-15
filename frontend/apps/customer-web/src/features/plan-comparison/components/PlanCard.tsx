import { formatRupeesFromPaise } from '@emi-copilot/shared-i18n';
import { Button, Card, Chip } from '@emi-copilot/ui-kit';
import { useTranslation } from 'react-i18next';

import type { CustomerPlan } from '../../customer-flow';
import { PlanBandChip } from '../../../shared/plan/PlanBandChip';
import { PlanFigures } from '../../../shared/plan/PlanFigures';
import { getPlanNameKey } from '../../../shared/plan/planWording';

export interface PlanCardProps {
  plan: CustomerPlan;
  /** The radio group's name; one group per screen. */
  radioGroupName: string;
  isSelected: boolean;
  onSelect: () => void;
  onOpenComfortDetail: () => void;
}

// One C4 plan card: a real radio with the plan name and lender line, monthly and extra in total
// at the same size, the band (only after a completed check), the budget fit, the total and the
// comfort detail link. Every figure and the band come from the API.
export function PlanCard({
  plan,
  radioGroupName,
  isSelected,
  onSelect,
  onOpenComfortDetail,
}: PlanCardProps) {
  const { t } = useTranslation();
  const planName = t(getPlanNameKey(plan.emiType));
  return (
    <Card as="article" isHighlighted={isSelected} className="flex flex-col gap-3">
      <label className="flex min-h-touch-target cursor-pointer items-center justify-between gap-3">
        <span className="flex flex-col">
          <span className="text-lead font-bold">{planName}</span>{' '}
          <span className="text-label font-normal text-slate">
            {t('plan.lenderWithTenure', {
              lenderLabel: plan.lenderLabel,
              count: plan.tenureInMonths,
            })}
          </span>
        </span>
        <input
          type="radio"
          name={radioGroupName}
          value={plan.offerId}
          checked={isSelected}
          onChange={onSelect}
          className="h-6 w-6 shrink-0 accent-cyan"
        />
      </label>
      <PlanFigures
        monthlyInstallmentInPaise={plan.monthlyInstallmentInPaise}
        tenureInMonths={plan.tenureInMonths}
        extraInTotalInPaise={plan.extraInTotalInPaise}
        priceInPaise={plan.priceInPaise}
      />
      <div className="flex flex-wrap gap-2">
        {plan.comfort === null ? null : <PlanBandChip comfort={plan.comfort} />}
        <Chip>
          {plan.isWithinBudget
            ? t('plan.withinBudget')
            : t('plan.aboveBudget', {
                amount: formatRupeesFromPaise(plan.amountAboveBudgetInPaise),
              })}
        </Chip>
      </div>
      <div className="flex items-center justify-between gap-2">
        <p className="text-label font-normal tabular-nums text-slate">
          {t('plan.totalInAll', { amount: formatRupeesFromPaise(plan.totalPayableInPaise) })}
        </p>
        {plan.comfort === null ? null : (
          <Button
            variant="quiet"
            onClick={onOpenComfortDetail}
            aria-label={t('plans.comfortDetailFor', {
              planName: t('plan.nameWithTenure', { planName, count: plan.tenureInMonths }),
            })}
          >
            {t('plans.comfortDetail')}
          </Button>
        )}
      </div>
    </Card>
  );
}
