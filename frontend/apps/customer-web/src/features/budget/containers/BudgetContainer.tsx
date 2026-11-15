import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { getProblemMessageKey, useCustomerFlow } from '../../customer-flow';
import { BudgetScreen } from '../components/BudgetScreen';
import { BudgetVoiceSection } from '../components/BudgetVoiceSection';
import { useBudgetVoiceEntry } from '../hooks/useBudgetVoiceEntry';
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

// Holds C2's typed or spoken amount and the "Correct?" question, and sends the budget only once
// the customer says yes; then the flow moves to the comfort check question.
export function BudgetContainer({ previousBudgetInPaise }: BudgetContainerProps) {
  const { t } = useTranslation();
  const { dispatch, session } = useCustomerFlow();
  const confirmBudget = useConfirmBudget();
  const [budgetDigits, setBudgetDigits] = useState(() =>
    convertPaiseToBudgetDigits(previousBudgetInPaise),
  );
  const [isConfirming, setIsConfirming] = useState(false);
  const voiceEntry = useBudgetVoiceEntry((heardDigits, isReadyToConfirm) => {
    setBudgetDigits(heardDigits);
    setIsConfirming(isReadyToConfirm);
    confirmBudget.reset();
  });

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
        voiceEntry.clearMisheardBudget();
        confirmBudget.reset();
      }}
      isConfirming={isConfirming}
      isSaving={confirmBudget.isPending}
      errorMessage={
        confirmBudget.isError ? t(getProblemMessageKey(confirmBudget.error)) : undefined
      }
      onContinue={() => {
        setIsConfirming(true);
        voiceEntry.clearMisheardBudget();
      }}
      onEdit={() => {
        setIsConfirming(false);
        confirmBudget.reset();
      }}
      onConfirm={handleConfirmBudget}
      onBack={() => {
        dispatch({ type: 'wentBack' });
      }}
      voiceSection={
        session.isVoiceAvailable ? (
          <BudgetVoiceSection
            recorderStatus={voiceEntry.recorder.status}
            misheardBudget={voiceEntry.misheardBudget}
            onStartRecording={voiceEntry.recorder.startRecording}
            onStopRecording={voiceEntry.recorder.stopRecording}
          />
        ) : undefined
      }
    />
  );
}
