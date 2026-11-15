import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { getProblemMessageKey, useCustomerFlow } from '../../customer-flow';
import { BudgetScreen } from '../components/BudgetScreen';
import { useConfirmBudget } from '../hooks/useConfirmBudget';
import {
  convertBudgetDigitsToPaise,
  convertPaiseToBudgetDigits,
  readBudgetDigits,
} from '../model/budgetAmount';

export interface BudgetContainerProps {
  /** The budget confirmed before, when the customer came back to change it. */
  previousBudgetInPaise: number | undefined;
}

// Holds C2's typed amount and the "Correct?" question, and sends the budget only once the
// customer says yes; then the flow moves to the comfort check question.
export function BudgetContainer({ previousBudgetInPaise }: BudgetContainerProps) {
  const { t } = useTranslation();
  const { dispatch } = useCustomerFlow();
  const confirmBudget = useConfirmBudget();
  const [budgetDigits, setBudgetDigits] = useState(() =>
    convertPaiseToBudgetDigits(previousBudgetInPaise),
  );
  const [isConfirming, setIsConfirming] = useState(false);

  // Sends the confirmed amount and moves on when the server has it.
  function handleConfirmBudget() {
    const monthlyBudgetInPaise = convertBudgetDigitsToPaise(budgetDigits);
    confirmBudget.mutate(monthlyBudgetInPaise, {
      onSuccess: () => {
        dispatch({ type: 'budgetConfirmed', monthlyBudgetInPaise });
      },
    });
  }

  return (
    <BudgetScreen
      budgetDigits={budgetDigits}
      onChangeBudgetText={(typedText) => {
        setBudgetDigits(readBudgetDigits(typedText));
        setIsConfirming(false);
        confirmBudget.reset();
      }}
      isConfirming={isConfirming}
      isSaving={confirmBudget.isPending}
      errorMessage={
        confirmBudget.isError ? t(getProblemMessageKey(confirmBudget.error)) : undefined
      }
      onContinue={() => {
        setIsConfirming(true);
      }}
      onEdit={() => {
        setIsConfirming(false);
        confirmBudget.reset();
      }}
      onConfirm={handleConfirmBudget}
      onBack={() => {
        dispatch({ type: 'wentBack' });
      }}
    />
  );
}
