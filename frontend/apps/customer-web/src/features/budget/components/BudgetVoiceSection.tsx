import { formatRupeesFromPaise } from '@emi-copilot/shared-i18n';
import { useTranslation } from 'react-i18next';

import { VoiceInputRow, type VoiceRecorderStatus } from '../../voice';
import type { MisheardBudget } from '../hooks/useBudgetVoiceEntry';
import { BudgetMisheardNotice } from './BudgetMisheardNotice';

export interface BudgetVoiceSectionProps {
  recorderStatus: VoiceRecorderStatus;
  misheardBudget: MisheardBudget | undefined;
  onStartRecording: () => void;
  onStopRecording: () => void;
}

// C2's microphone row ("Tap and say the amount") and, after a misheard clip, the fix-it notice.
export function BudgetVoiceSection(props: BudgetVoiceSectionProps) {
  const { t } = useTranslation();
  const heardAmountInPaise = props.misheardBudget?.heardAmountInPaise ?? null;
  return (
    <>
      <VoiceInputRow
        status={props.recorderStatus}
        startLabel={t('budget.microphone')}
        typeInsteadMessage={t('budget.typeInstead')}
        onStartRecording={props.onStartRecording}
        onStopRecording={props.onStopRecording}
      />
      {props.misheardBudget === undefined ? null : (
        <BudgetMisheardNotice
          formattedHeardAmount={
            heardAmountInPaise === null ? undefined : formatRupeesFromPaise(heardAmountInPaise)
          }
          onSayAgain={props.onStartRecording}
        />
      )}
    </>
  );
}
