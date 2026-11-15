import { formatRupeesFromPaise } from '@emi-copilot/shared-i18n';
import { Card } from '@emi-copilot/ui-kit';
import { useId } from 'react';
import { useTranslation } from 'react-i18next';

import type { BasePlanResponse } from '../../customer-flow';
import { formatPercentFromBasisPoints } from '../../../shared/formatting/formatPercentFromBasisPoints';
import { getPlanNameKey } from '../../../shared/plan/planWording';

export interface BasePlanCardProps {
  basePlan: BasePlanResponse;
  monthlyBudgetInPaise: number;
}

// C6's "Plan you are looking at": name and tenure, each month and extra in total, then its band
// and share (after a completed check) and how it sits against the budget, all as the API said.
export function BasePlanCard({ basePlan, monthlyBudgetInPaise }: BasePlanCardProps) {
  const { t } = useTranslation();
  const headingId = useId();
  const budget = formatRupeesFromPaise(monthlyBudgetInPaise);
  const bandLine =
    basePlan.comfort === null
      ? ''
      : `${t('alternatives.bandShare', {
          band: t(`comfortBand.${basePlan.comfort.band}`),
          percent: formatPercentFromBasisPoints(basePlan.comfort.comfortRatioInBasisPoints),
        })} `;
  const budgetLine = basePlan.isWithinBudget
    ? t('alternatives.withinYourBudget', { budget })
    : t('alternatives.aboveYourBudget', {
        amount: formatRupeesFromPaise(basePlan.amountAboveBudgetInPaise),
        budget,
      });
  return (
    <Card as="section" surface="flat" aria-labelledby={headingId} className="flex flex-col gap-2">
      <h2 id={headingId} className="text-label text-slate">
        {t('alternatives.yourPlan')}
      </h2>
      <p className="text-lead font-bold">
        {t('plan.nameWithTenure', {
          planName: t(getPlanNameKey(basePlan.emiType)),
          count: basePlan.tenureInMonths,
        })}
      </p>
      <p className="flex flex-wrap gap-x-4 text-body tabular-nums">
        <span>
          {t('plan.eachMonth')}{' '}
          <strong>{formatRupeesFromPaise(basePlan.monthlyInstallmentInPaise)}</strong>
        </span>
        <span>
          {t('plan.extraInTotal')}{' '}
          <strong>{formatRupeesFromPaise(basePlan.extraInTotalInPaise)}</strong>
        </span>
      </p>
      <p className="text-label font-normal text-ink-muted">{`${bandLine}${budgetLine}`}</p>
    </Card>
  );
}
