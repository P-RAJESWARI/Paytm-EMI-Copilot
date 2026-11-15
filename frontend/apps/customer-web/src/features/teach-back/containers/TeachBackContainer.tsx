import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { useCustomerFlow, type CustomerPlan } from '../../customer-flow';
import { useVoiceInput, VoiceInputRow } from '../../voice';
import { MAXIMUM_ANSWER_LENGTH, TeachBackScreen } from '../components/TeachBackScreen';
import { useCheckTeachBack } from '../hooks/useCheckTeachBack';

export interface TeachBackContainerProps {
  plan: CustomerPlan;
}

// Holds C8's answer (typed, or filled from the microphone's transcript), checks it with the
// server and moves on: Continue and Skip go to consent, "Explain it again" back to C7.
export function TeachBackContainer({ plan }: TeachBackContainerProps) {
  const { t } = useTranslation();
  const { dispatch, session } = useCustomerFlow();
  const [answerText, setAnswerText] = useState('');
  const teachBackCheck = useCheckTeachBack(plan.offerId);
  const recorder = useVoiceInput('TEACH_BACK', ({ transcript }) => {
    setAnswerText(transcript.slice(0, MAXIMUM_ANSWER_LENGTH));
    teachBackCheck.reset();
  });
  return (
    <TeachBackScreen
      plan={plan}
      answerText={answerText}
      onChangeAnswerText={(typedText) => {
        setAnswerText(typedText);
        teachBackCheck.reset();
      }}
      voiceSection={
        session.isVoiceAvailable ? (
          <VoiceInputRow
            status={recorder.status}
            startLabel={t('teachBack.microphone')}
            typeInsteadMessage={t('teachBack.typeInstead')}
            onStartRecording={recorder.startRecording}
            onStopRecording={recorder.stopRecording}
          />
        ) : undefined
      }
      isChecking={teachBackCheck.isPending}
      outcome={teachBackCheck.data}
      hasCheckFailed={teachBackCheck.isError}
      onCheck={() => {
        teachBackCheck.mutate(answerText.trim());
      }}
      onExplainAgain={() => {
        dispatch({ type: 'wentBack' });
      }}
      onContinue={() => {
        dispatch({ type: 'continuedToConsent' });
      }}
      onBack={() => {
        dispatch({ type: 'wentBack' });
      }}
    />
  );
}
