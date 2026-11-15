import { useMutation } from '@tanstack/react-query';

import { useCustomerFlowApi } from '../../customer-flow';

// Sends the customer's own choice on C3: allow the comfort check (consent) or skip it.
export function useAnswerComfortCheck() {
  const customerFlowApi = useCustomerFlowApi();
  return useMutation({
    mutationFn: (hasCustomerConsented: boolean) =>
      customerFlowApi.answerComfortCheck(hasCustomerConsented),
  });
}
