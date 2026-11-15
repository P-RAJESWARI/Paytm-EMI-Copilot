import { useLanguagePreference } from '@emi-copilot/shared-i18n';
import { useMutation } from '@tanstack/react-query';

import { useCustomerFlowApi } from '../../customer-flow';

// Sends the customer's own-words answer for the plan in their current language (C8); the server
// compares it with the plan's figures, and the result is advice only.
export function useCheckTeachBack(offerId: string) {
  const customerFlowApi = useCustomerFlowApi();
  const { selectedLanguage } = useLanguagePreference();
  return useMutation({
    mutationFn: (answerText: string) =>
      customerFlowApi.checkTeachBack(offerId, answerText, selectedLanguage),
  });
}
