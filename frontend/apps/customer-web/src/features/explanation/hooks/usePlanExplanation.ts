import { useLanguagePreference } from '@emi-copilot/shared-i18n';
import { useQuery } from '@tanstack/react-query';

import { customerQueryKeys, useCustomerFlowApi } from '../../customer-flow';

// Fetches the plain-language explanation of the chosen plan in the customer's current language;
// switching the language fetches that language's text (the numbers stay the API's).
export function usePlanExplanation(offerId: string) {
  const customerFlowApi = useCustomerFlowApi();
  const { selectedLanguage } = useLanguagePreference();
  return useQuery({
    queryKey: customerQueryKeys.explanation(offerId, selectedLanguage),
    queryFn: () => customerFlowApi.explainPlan(offerId, selectedLanguage),
    staleTime: Infinity,
  });
}
