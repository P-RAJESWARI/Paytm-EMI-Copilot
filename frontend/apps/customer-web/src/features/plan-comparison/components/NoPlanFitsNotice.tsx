import { Button } from '@emi-copilot/ui-kit';
import { useTranslation } from 'react-i18next';

export interface NoPlanFitsNoticeProps {
  /** The budget, already formatted, for example "₹1,800". */
  formattedBudget: string;
  /** Opens C6 for the selected plan; undefined until a plan is selected. */
  onSeeAlternatives: (() => void) | undefined;
}

// C4's "no plan fits" note: every plan is still listed below (DESIGN_SPEC section 7.2), and ways
// to lower the monthly amount open for the plan the customer selects (nothing is picked for them).
export function NoPlanFitsNotice({ formattedBudget, onSeeAlternatives }: NoPlanFitsNoticeProps) {
  const { t } = useTranslation();
  return (
    <section className="flex flex-col gap-2 rounded-card bg-stretching-tint p-4 text-stretching-text">
      <h2 className="text-body font-bold">{t('plans.noFitTitle', { budget: formattedBudget })}</h2>
      <p className="text-body">{t('plans.noFitBody')}</p>
      {onSeeAlternatives === undefined ? (
        <p className="text-body">{t('plans.noFitChooseFirst')}</p>
      ) : (
        <Button variant="secondary" onClick={onSeeAlternatives}>
          {t('plans.noFitLink')}
        </Button>
      )}
    </section>
  );
}
