import { formatRupeesFromPaise } from '@emi-copilot/shared-i18n';
import { Card } from '@emi-copilot/ui-kit';
import { useId, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import type { EmiType } from '../../features/customer-flow';
import { getPlanNameKey } from './planWording';

export interface PlanSummaryProps {
  /** Translated heading, for example "Plan you chose". */
  heading: string;
  emiType: EmiType;
  lenderLabel: string;
  tenureInMonths: number;
  monthlyInstallmentInPaise: number;
  extraInTotalInPaise: number;
  totalPayableInPaise: number;
  /** Extra rows after the total, such as the receipt reference. */
  children?: ReactNode;
}

/** One class for both headline amounts: monthly and extra in total at the same size (rule 7). */
const HEADLINE_AMOUNT_CLASS_NAME = 'text-title tabular-nums text-navy';

// The chosen plan in one card (C7 recap, C9 summary, C10 receipt): name and lender, each month and
// extra in total at the same size, then tenure and total. Every figure comes from the API.
export function PlanSummary(props: PlanSummaryProps) {
  const { t } = useTranslation();
  const headingId = useId();
  const headlineAmounts = [
    { label: t('plan.eachMonth'), inPaise: props.monthlyInstallmentInPaise },
    { label: t('plan.extraInTotal'), inPaise: props.extraInTotalInPaise },
  ];
  const rows = [
    { label: t('plan.tenure'), value: t('plan.tenureMonths', { count: props.tenureInMonths }) },
    { label: t('plan.total'), value: formatRupeesFromPaise(props.totalPayableInPaise) },
  ];
  return (
    <Card as="section" aria-labelledby={headingId} className="flex flex-col gap-3">
      <h2 id={headingId} className="text-label text-slate">
        {props.heading}
      </h2>
      <div>
        <p className="text-lead font-bold">{t(getPlanNameKey(props.emiType))}</p>
        <p className="text-label font-normal text-slate">
          {t('plan.lenderWithTenure', {
            lenderLabel: props.lenderLabel,
            count: props.tenureInMonths,
          })}
        </p>
      </div>
      <dl className="grid grid-cols-2 gap-2">
        {headlineAmounts.map((amount) => (
          <div key={amount.label} className="flex flex-col">
            <dt className="text-label font-normal text-slate">{amount.label}</dt>
            <dd className={HEADLINE_AMOUNT_CLASS_NAME}>{formatRupeesFromPaise(amount.inPaise)}</dd>
          </div>
        ))}
      </dl>
      <dl className="flex flex-col gap-2 text-body">
        {rows.map((row) => (
          <div key={row.label} className="flex justify-between gap-2 border-t border-border pt-2">
            <dt className="text-slate">{row.label}</dt>
            <dd className="font-bold tabular-nums">{row.value}</dd>
          </div>
        ))}
        {props.children}
      </dl>
    </Card>
  );
}
