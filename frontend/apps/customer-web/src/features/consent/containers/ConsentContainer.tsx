import { useTranslation } from 'react-i18next';

import {
  CustomerApiError,
  getProblemMessageKey,
  useCustomerFlow,
  type CustomerPlan,
} from '../../customer-flow';
import { ConsentScreen } from '../components/ConsentScreen';
import { OtpEntry } from '../components/OtpEntry';
import { useConsentWithOtp } from '../hooks/useConsentWithOtp';
import { classifyConsentFailure } from '../model/consentFailure';

export interface ConsentContainerProps {
  plan: CustomerPlan;
}

// Connects C9 to the OTP and consent calls; the customer's own OTP and Confirm are the human
// gate (CLAUDE.md rule 9). Only a failure the OTP block does not explain shows a general message.
export function ConsentContainer({ plan }: ConsentContainerProps) {
  const { t } = useTranslation();
  const { dispatch } = useCustomerFlow();
  const consentFlow = useConsentWithOtp(plan);
  const { otpRequest, consent } = consentFlow;
  // A "wait, then ask again" answer is explained by the resend countdown, not by a message.
  const isOtpWaitAnswer =
    otpRequest.error instanceof CustomerApiError &&
    otpRequest.error.retryAfterInSeconds !== undefined;
  return (
    <ConsentScreen
      plan={plan}
      otpEntry={
        <OtpEntry
          otpChallenge={consentFlow.otpChallenge}
          otpDigits={consentFlow.otpDigits}
          otpProblem={consentFlow.otpProblem}
          secondsUntilResend={consentFlow.secondsUntilResend}
          isRequestingOtp={otpRequest.isPending}
          requestErrorMessage={
            otpRequest.isError && !isOtpWaitAnswer
              ? t(getProblemMessageKey(otpRequest.error))
              : undefined
          }
          onChangeOtpDigits={consentFlow.changeOtpDigits}
          onRequestOtp={consentFlow.requestOtp}
        />
      }
      canConfirm={consentFlow.canConfirm}
      consentErrorMessage={
        consent.isError && classifyConsentFailure(consent.error).kind === 'other'
          ? t(getProblemMessageKey(consent.error))
          : undefined
      }
      onConfirm={consentFlow.confirmConsent}
      onBack={() => {
        dispatch({ type: 'wentBack' });
      }}
    />
  );
}
