import { formatRupeesFromPaise } from '@emi-copilot/shared-i18n';
import { useTranslation } from 'react-i18next';

import { formatExactRupeesFromPaise } from '../../../shared/formatting/formatExactRupees';
import { getPlanNameKey } from '../../../shared/plan/planName';
import type { SaleHandoff } from '../api/paymentHandoffApi';

export interface HandoffPlanGridProps {
  sale: SaleHandoff['sale'];
}

// M4's plan table: chosen plan, product, price, each month, extra in total, total and who funds
// it (plan Q8 adds extra and total). Figures come from the API exactly as the customer saw them.
export function HandoffPlanGrid({ sale }: HandoffPlanGridProps) {
  const { t } = useTranslation();
  const plan = sale.chosenPlan;
  const rows = [
    { label: t('handoff.product'), value: sale.productName },
    { label: t('handoff.price'), value: formatExactRupeesFromPaise(sale.priceInPaise) },
  ];
  if (plan !== null) {
    rows.unshift({
      label: t('handoff.chosenPlan'),
      value: t('plan.nameWithTenure', {
        planName: t(getPlanNameKey(plan.planKind)),
        count: plan.tenureInMonths,
      }),
    });
    rows.push(
      { label: t('plan.eachMonth'), value: formatRupeesFromPaise(plan.monthlyInstallmentInPaise) },
      {
        label: t('plan.extraInTotal'),
        value: formatExactRupeesFromPaise(plan.extraInTotalInPaise),
      },
      { label: t('plan.total'), value: formatExactRupeesFromPaise(plan.totalPayableInPaise) },
      { label: t('plan.fundedBy'), value: plan.lenderLabel },
    );
  }
  return (
    <dl
      aria-label={t('handoff.planGridLabel')}
      className="m-0 grid grid-cols-2 gap-4 rounded-card bg-white p-6 shadow-card"
    >
      {rows.map((row) => (
        <div key={row.label} className="flex flex-col gap-1">
          <dt className="text-label font-normal text-slate">{row.label}</dt>
          <dd className="m-0 text-lead font-bold tabular-nums text-deep-navy">{row.value}</dd>
        </div>
      ))}
    </dl>
  );
}
