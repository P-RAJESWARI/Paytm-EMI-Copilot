import { formatRupeesFromPaise } from '@emi-copilot/shared-i18n';
import { Card } from '@emi-copilot/ui-kit';
import { useTranslation } from 'react-i18next';

import type { CustomerPlan } from '../../customer-flow';
import { getPlanNameKey } from '../../../shared/plan/planWording';

export interface ComfortPlanHeaderProps {
  plan: Pick<
    CustomerPlan,
    | 'emiType'
    | 'lenderLabel'
    | 'tenureInMonths'
    | 'monthlyInstallmentInPaise'
    | 'extraInTotalInPaise'
  >;
}

// The C5 plan header: name, lender and tenure, then each month and extra in total at one size.
export function ComfortPlanHeader({ plan }: ComfortPlanHeaderProps) {
  const { t } = useTranslation();
  const figures = [
    { label: t('plan.eachMonth'), amountInPaise: plan.monthlyInstallmentInPaise },
    { label: t('plan.extraInTotal'), amountInPaise: plan.extraInTotalInPaise },
  ];
  return (
    <Card className="flex flex-col gap-3">
      <div>
        <p className="text-lead font-bold">{t(getPlanNameKey(plan.emiType))}</p>
        <p className="text-label font-normal text-slate">
          {t('plan.lenderWithTenure', {
            lenderLabel: plan.lenderLabel,
            count: plan.tenureInMonths,
          })}
        </p>
      </div>
      <dl className="grid grid-cols-2 gap-2">
        {figures.map((figure) => (
          <div key={figure.label} className="flex flex-col">
            <dt className="text-label font-normal text-slate">{figure.label}</dt>
            <dd className="text-title tabular-nums text-navy">
              {formatRupeesFromPaise(figure.amountInPaise)}
            </dd>
          </div>
        ))}
      </dl>
    </Card>
  );
}
