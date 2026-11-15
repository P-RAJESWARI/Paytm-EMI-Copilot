import { formatRupeesFromPaise } from '@emi-copilot/shared-i18n';
import { Button } from '@emi-copilot/ui-kit';
import { useId, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import { CalmErrorMessage } from '../../../shared/components/CalmErrorMessage';
import { ScreenLayout } from '../../../shared/components/ScreenLayout';
import { ScreenTitle } from '../../../shared/components/ScreenTitle';
import { convertBudgetDigitsToPaise } from '../model/budgetAmount';
import { BudgetConfirmation } from './BudgetConfirmation';

export interface BudgetScreenProps {
  /** Whole-rupee digits typed so far. */
  budgetDigits: string;
  onChangeBudgetText: (typedText: string) => void;
  /** True once Continue asked "Correct?" and before the customer answers. */
  isConfirming: boolean;
  isSaving: boolean;
  /** A calm, translated message when saving failed. */
  errorMessage?: string | undefined;
  onContinue: () => void;
  onEdit: () => void;
  onConfirm: () => void;
  onBack: () => void;
}

/** The form id, so the footer's Continue button submits the amount form. */
const BUDGET_FORM_ID = 'budget-form';

// C2: one large ₹ input per month (typed; the microphone is Layer 4), then "You said ₹X. Correct?".
export function BudgetScreen(props: BudgetScreenProps) {
  const { t } = useTranslation();
  const inputId = useId();
  const hasAmount = props.budgetDigits !== '';
  // Submits the amount form, which only asks for confirmation; nothing is sent yet.
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (hasAmount) props.onContinue();
  }
  return (
    <ScreenLayout
      onBack={props.onBack}
      stepLabel={t('flow.stepOf', { current: 1, total: 4 })}
      footer={
        props.isConfirming ? undefined : (
          <Button
            type="submit"
            form={BUDGET_FORM_ID}
            size="large"
            isFullWidth
            disabled={!hasAmount}
          >
            {t('budget.continue')}
          </Button>
        )
      }
    >
      <div className="flex flex-col gap-2">
        <ScreenTitle>{t('budget.title')}</ScreenTitle>
        <p className="text-body text-slate">{t('budget.help')}</p>
      </div>
      <form id={BUDGET_FORM_ID} onSubmit={handleSubmit} className="flex flex-col gap-2">
        <label htmlFor={inputId} className="text-label text-slate">
          {t('budget.amountLabel')}
        </label>
        <div className="flex items-center gap-2 rounded-card border-2 border-border bg-white px-4 py-3 focus-within:border-cyan">
          <span aria-hidden="true" className="money-figure text-navy">
            ₹
          </span>
          <input
            id={inputId}
            inputMode="numeric"
            autoComplete="off"
            placeholder="0"
            value={props.budgetDigits}
            onChange={(event) => {
              props.onChangeBudgetText(event.target.value);
            }}
            className="money-figure w-full min-w-0 border-0 bg-transparent text-navy outline-none"
          />
          <span className="text-body text-slate">{t('budget.perMonth')}</span>
        </div>
      </form>
      {hasAmount ? null : <p className="text-body text-slate">{t('budget.emptyHint')}</p>}
      {props.isConfirming ? (
        <BudgetConfirmation
          formattedAmount={formatRupeesFromPaise(convertBudgetDigitsToPaise(props.budgetDigits))}
          isSaving={props.isSaving}
          onEdit={props.onEdit}
          onConfirm={props.onConfirm}
        />
      ) : null}
      {props.errorMessage === undefined ? null : (
        <CalmErrorMessage
          message={props.errorMessage}
          retryLabel={t('common.tryAgain')}
          onRetry={props.onConfirm}
        />
      )}
    </ScreenLayout>
  );
}
