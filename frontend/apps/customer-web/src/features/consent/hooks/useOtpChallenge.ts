import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';

import { CustomerApiError, useCustomerFlowApi, type OtpChallenge } from '../../customer-flow';
import { useResendCountdown } from './useResendCountdown';

const MILLISECONDS_PER_SECOND = 1000;

/** What is wrong with the OTP the customer typed, as C9 says it. */
export type OtpProblem =
  { kind: 'incorrect'; attemptsRemaining: number | undefined } | { kind: 'expired' };

// Holds C9's OTP side: the sent challenge, the typed digits, what is wrong with them, and the
// resend wait (from resendAvailableAt, or from Retry-After when the server says "not yet").
export function useOtpChallenge() {
  const customerFlowApi = useCustomerFlowApi();
  const resendCountdown = useResendCountdown();
  const [otpChallenge, setOtpChallenge] = useState<OtpChallenge | undefined>(undefined);
  const [otpDigits, setOtpDigits] = useState('');
  const [otpProblem, setOtpProblem] = useState<OtpProblem | undefined>(undefined);
  const otpRequest = useMutation({
    mutationFn: () => customerFlowApi.requestConsentOtp(),
    onSuccess: (challenge) => {
      setOtpChallenge(challenge);
      setOtpDigits('');
      setOtpProblem(undefined);
      resendCountdown.countDownTo(Date.parse(challenge.resendAvailableAt));
    },
    onError: (error) => {
      if (error instanceof CustomerApiError && error.retryAfterInSeconds !== undefined) {
        resendCountdown.countDownTo(
          Date.now() + error.retryAfterInSeconds * MILLISECONDS_PER_SECOND,
        );
      }
    },
  });
  return {
    otpChallenge,
    otpDigits,
    otpProblem,
    otpRequest,
    secondsUntilResend: resendCountdown.secondsUntilResend,
    requestOtp: () => {
      otpRequest.mutate();
    },
    changeOtpDigits: (digits: string) => {
      setOtpDigits(digits);
      if (otpProblem?.kind === 'incorrect') setOtpProblem(undefined);
    },
    markOtpIncorrect: (attemptsRemaining: number | undefined) => {
      setOtpDigits('');
      setOtpProblem({ kind: 'incorrect', attemptsRemaining });
    },
    markOtpExpired: () => {
      setOtpProblem({ kind: 'expired' });
    },
  };
}
