import { formatRupeesFromPaise } from '@emi-copilot/shared-i18n';
import { useTranslation } from 'react-i18next';

export interface PlanFiguresProps {
  monthlyInstallmentInPaise: number;
  tenureInMonths: number;
  extraInTotalInPaise: number;
  /** The item's price, for "on top of ₹22,000". */
  priceInPaise: number;
}

/** One class for both amounts: rule 7 says monthly and extra in total show at the same size. */
const PLAN_FIGURE_VALUE_CLASS_NAME = 'text-heading font-bold tabular-nums';

// "Each month ₹X for N months" beside "Extra in total ₹Y on top of the price", at the same size
// (CLAUDE.md rule 7, DESIGN_SPEC section 7.1). Every figure comes from the API as given.
export function PlanFigures({
  monthlyInstallmentInPaise,
  tenureInMonths,
  extraInTotalInPaise,
  priceInPaise,
}: PlanFiguresProps) {
  const { t } = useTranslation();
  const hasNoExtra = extraInTotalInPaise === 0;
  return (
    <dl className="grid grid-cols-2 gap-2">
      <div className="flex flex-col rounded-input bg-light-blue px-3 py-2 text-navy">
        <dt className="text-label text-slate">{t('plan.eachMonth')}</dt>
        <dd className={PLAN_FIGURE_VALUE_CLASS_NAME}>
          {formatRupeesFromPaise(monthlyInstallmentInPaise)}
        </dd>
        <dd className="text-caption text-slate">
          {t('plan.forMonths', { count: tenureInMonths })}
        </dd>
      </div>
      <div
        className={`flex flex-col rounded-input px-3 py-2 ${
          hasNoExtra ? 'bg-comfortable-tint text-comfortable-text' : 'bg-light-blue text-navy'
        }`}
      >
        <dt className={`text-label ${hasNoExtra ? '' : 'text-slate'}`}>{t('plan.extraInTotal')}</dt>
        <dd className={PLAN_FIGURE_VALUE_CLASS_NAME}>
          {formatRupeesFromPaise(extraInTotalInPaise)}
        </dd>
        <dd className={`text-caption ${hasNoExtra ? '' : 'text-slate'}`}>
          {t('plan.onTopOfPrice', { price: formatRupeesFromPaise(priceInPaise) })}
        </dd>
      </div>
    </dl>
  );
}
