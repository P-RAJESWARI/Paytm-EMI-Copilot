import { useState } from 'react';

import type { SpeechTranscription } from '../../customer-flow';
import { useVoiceInput, type VoiceRecorder } from '../../voice';
import { convertPaiseToBudgetDigits, readBudgetDigits } from '../model/budgetAmount';

/** After a misheard clip: the amount speech heard (null when none), shown for the customer to fix. */
export interface MisheardBudget {
  heardAmountInPaise: number | null;
}

export interface BudgetVoiceEntry {
  recorder: VoiceRecorder;
  misheardBudget: MisheardBudget | undefined;
  clearMisheardBudget: () => void;
}

// C2 voice entry: records the amount, then prefills the field. A clear amount goes straight to
// "You said ₹X. Correct?"; a likely-misheard or missing one shows the misheard notice instead.
// Either way the customer confirms by tapping; speech never sets the budget.
export function useBudgetVoiceEntry(
  onAmountHeard: (budgetDigits: string, isReadyToConfirm: boolean) => void,
): BudgetVoiceEntry {
  const [misheardBudget, setMisheardBudget] = useState<MisheardBudget | undefined>(undefined);

  // Prefills the field from the transcription and decides between "Correct?" and "misheard".
  function handleTranscribed({ recognisedAmountInPaise, isLikelyMisheard }: SpeechTranscription) {
    if (recognisedAmountInPaise !== null) {
      onAmountHeard(
        readBudgetDigits(convertPaiseToBudgetDigits(recognisedAmountInPaise)),
        !isLikelyMisheard,
      );
    }
    const isClear = recognisedAmountInPaise !== null && !isLikelyMisheard;
    setMisheardBudget(isClear ? undefined : { heardAmountInPaise: recognisedAmountInPaise });
  }

  const recorder = useVoiceInput('BUDGET', handleTranscribed);
  return {
    recorder,
    misheardBudget,
    clearMisheardBudget: () => {
      setMisheardBudget(undefined);
    },
  };
}
