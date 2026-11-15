import { useTranslation } from 'react-i18next';

import { getProblemMessageKey, useCustomerFlow } from '../../customer-flow';
import { ComfortConsentScreen } from '../components/ComfortConsentScreen';
import { useAnswerComfortCheck } from '../hooks/useAnswerComfortCheck';

// Sends the customer's Allow or Skip on C3 and moves to the plans with the server's answer.
export function ComfortConsentContainer() {
  const { t } = useTranslation();
  const { dispatch } = useCustomerFlow();
  const answerComfortCheck = useAnswerComfortCheck();

  // Sends one answer; the plans follow once the server has recorded it.
  function handleAnswer(hasCustomerConsented: boolean) {
    answerComfortCheck.mutate(hasCustomerConsented, {
      onSuccess: (comfortCheck) => {
        dispatch({ type: 'comfortCheckAnswered', comfortCheck });
      },
    });
  }

  return (
    <ComfortConsentScreen
      isSaving={answerComfortCheck.isPending}
      errorMessage={
        answerComfortCheck.isError ? t(getProblemMessageKey(answerComfortCheck.error)) : undefined
      }
      onAllow={() => {
        handleAnswer(true);
      }}
      onSkip={() => {
        handleAnswer(false);
      }}
      onBack={() => {
        dispatch({ type: 'wentBack' });
      }}
    />
  );
}
