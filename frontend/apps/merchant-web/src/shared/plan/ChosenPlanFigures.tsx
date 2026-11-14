import type { ApiSchemas } from '@emi-copilot/api-client';
import { formatRupeesFromPaise } from '@emi-copilot/shared-i18n';
import { useTranslation } from 'react-i18next';

import { formatExactRupeesFromPaise } from '../formatting/formatExactRupees';
import { getPlanNameKey } from './planName';

export interface ChosenPlanFiguresProps {
  plan: ApiSchemas['ChosenPlanResponse'];
}

// The agreed plan as the customer saw it: name and tenure, then each month, extra in total and
// total at the same size (plan Q8). Every figure comes from the API; nothing is worked out here.
export function ChosenPlanFigures({ plan }: ChosenPlanFiguresProps) {
  const { t } = useTranslation();
  const figures = [
    { label: t('plan.eachMonth'), value: formatRupeesFromPaise(plan.monthlyInstallmentInPaise) },
    { label: t('plan.extraInTotal'), value: formatExactRupeesFromPaise(plan.extraInTotalInPaise) },
    { label: t('plan.total'), value: formatExactRupeesFromPaise(plan.totalPayableInPaise) },
  ];
  return (
    <div className="flex flex-col gap-3">
      <p className="text-body font-bold text-navy">
        {t('plan.nameWithTenure', {
          planName: t(getPlanNameKey(plan.planKind)),
          count: plan.tenureInMonths,
        })}
      </p>
      <dl className="grid grid-cols-3 gap-3">
        {figures.map((figure) => (
          <div key={figure.label} className="flex flex-col gap-1">
            <dt className="text-label font-normal text-slate">{figure.label}</dt>
            <dd className="text-lead font-bold tabular-nums text-deep-navy">{figure.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
