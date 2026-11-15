import { useLanguagePreference } from '@emi-copilot/shared-i18n';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import {
  customerQueryKeys,
  useCustomerFlow,
  useCustomerFlowApi,
  useIdempotencyKeyPerIntent,
  type CustomerPlan,
} from '../../customer-flow';
import { classifyConsentFailure } from '../model/consentFailure';
import { useOtpChallenge } from './useOtpChallenge';

const OTP_DIGIT_COUNT = 6;

// Runs C9: the OTP side plus consent to the exact plan shown, in the language on screen, with one
// Idempotency-Key per intent. A wrong OTP asks again, an expired one offers a new OTP, a changed
// plan re-shows C4 with fresh figures, and an earlier consent opens the receipt.
export function useConsentWithOtp(plan: CustomerPlan) {
  const customerFlowApi = useCustomerFlowApi();
  const { selectedLanguage } = useLanguagePreference();
  const queryClient = useQueryClient();
  const { dispatch } = useCustomerFlow();
  const idempotencyKeys = useIdempotencyKeyPerIntent();
  const otp = useOtpChallenge();
  const consent = useMutation({
    mutationFn: ({ otpDigits, idempotencyKey }: { otpDigits: string; idempotencyKey: string }) =>
      customerFlowApi.giveConsent(
        {
          offerId: plan.offerId,
          shownMonthlyInstallmentInPaise: plan.monthlyInstallmentInPaise,
          shownTotalPayableInPaise: plan.totalPayableInPaise,
          otp: otpDigits,
        },
        idempotencyKey,
        selectedLanguage,
      ),
    onSettled: (_confirmation, error, { idempotencyKey }) => {
      idempotencyKeys.settleIdempotencyKey(idempotencyKey, error);
    },
    onSuccess: () => {
      dispatch({ type: 'consentRecorded' });
    },
    onError: (error) => {
      const failure = classifyConsentFailure(error);
      if (failure.kind === 'otpIncorrect') otp.markOtpIncorrect(failure.attemptsRemaining);
      if (failure.kind === 'otpExpired') otp.markOtpExpired();
      if (failure.kind === 'shownPlanChanged') {
        void queryClient.invalidateQueries({ queryKey: customerQueryKeys.plansRoot() });
        void queryClient.invalidateQueries({ queryKey: customerQueryKeys.alternativesRoot() });
        dispatch({ type: 'shownPlanChanged' });
      }
      if (failure.kind === 'consentAlreadyGiven') dispatch({ type: 'consentRecorded' });
    },
  });
  const consentIntentId = `${plan.offerId}:${plan.monthlyInstallmentInPaise}:${plan.totalPayableInPaise}`;
  return {
    ...otp,
    consent,
    canConfirm:
      otp.otpChallenge !== undefined &&
      otp.otpDigits.length === OTP_DIGIT_COUNT &&
      otp.otpProblem?.kind !== 'expired' &&
      !consent.isPending,
    confirmConsent: () => {
      consent.mutate({
        otpDigits: otp.otpDigits,
        idempotencyKey: idempotencyKeys.takeIdempotencyKey(consentIntentId),
      });
    },
  };
}
