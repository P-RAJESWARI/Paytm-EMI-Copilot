import { Button } from '@emi-copilot/ui-kit';
import { useTranslation } from 'react-i18next';

export interface BudgetMisheardNoticeProps {
  /** What speech heard, already formatted ("₹30,000"), or undefined when no amount was caught. */
  formattedHeardAmount: string | undefined;
  onSayAgain: () => void;
}

// C2's misheard state: what we heard, how to fix it by typing, and "Say it again". The amount
// above stays editable; nothing is sent until the customer confirms.
export function BudgetMisheardNotice({
  formattedHeardAmount,
  onSayAgain,
}: BudgetMisheardNoticeProps) {
  const { t } = useTranslation();
  return (
    <div
      aria-live="polite"
      className="flex flex-col gap-2 rounded-card border border-border-strong bg-white p-4"
    >
      <p className="text-lead font-bold text-deep-navy">
        {formattedHeardAmount === undefined
          ? t('budget.noAmountHeard')
          : t('budget.misheard', { amount: formattedHeardAmount })}
      </p>
      <p className="text-body text-slate">{t('budget.misheardFix')}</p>
      <Button variant="secondary" className="self-start" onClick={onSayAgain}>
        {t('budget.sayAgain')}
      </Button>
    </div>
  );
}
