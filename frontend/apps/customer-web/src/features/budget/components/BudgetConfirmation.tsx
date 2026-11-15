import { Button } from '@emi-copilot/ui-kit';
import { useTranslation } from 'react-i18next';

export interface BudgetConfirmationProps {
  /** The typed amount, already formatted, for example "₹3,000". */
  formattedAmount: string;
  isSaving: boolean;
  onEdit: () => void;
  onConfirm: () => void;
}

// The C2 confirm line: "You said ₹3,000. Correct?" with Edit and "Yes, correct".
export function BudgetConfirmation({
  formattedAmount,
  isSaving,
  onEdit,
  onConfirm,
}: BudgetConfirmationProps) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-3 rounded-card bg-cyan-tint p-4">
      <p className="text-lead font-semibold text-navy" aria-live="polite">
        {t('budget.confirmQuestion', { amount: formattedAmount })}
      </p>
      <div className="grid grid-cols-2 gap-2">
        <Button variant="secondary" onClick={onEdit} disabled={isSaving}>
          {t('budget.edit')}
        </Button>
        <Button variant="primary" onClick={onConfirm} disabled={isSaving}>
          {t('budget.confirmYes')}
        </Button>
      </div>
    </div>
  );
}
